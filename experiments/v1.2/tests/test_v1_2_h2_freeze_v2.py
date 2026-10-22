"""Freeze-v2 contract tests; no worker/model execution."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
H2_REL = "experiments/v1.2/h2-lazy-disclosure"
H2 = ROOT / H2_REL
FZ = H2 / "freeze-v2"


def load(name):
    if str(FZ) not in sys.path:
        sys.path.insert(0, str(FZ))
    spec = importlib.util.spec_from_file_location(name, FZ / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def git(*args, root=ROOT):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                          check=True).stdout


def digest(data):
    return hashlib.sha256(data).hexdigest()


def text_fields(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from text_fields(item)
    elif isinstance(value, list):
        for item in value:
            yield from text_fields(item)


class WrapperDelivery(unittest.TestCase):
    def test_both_arms_deliver_only_outside_clean_base_with_object_hashes(self):
        wrapper = load("wrapper_delivery")
        materials = git("rev-parse", "HEAD").decode().strip()
        task = json.loads(git("show", f"{materials}:{H2_REL}/admission/"
                             "freeze-v2-input/shortlist.json"))["shortlist"][0]
        routes = json.loads(git("show", f"{materials}:{H2_REL}/routes-h2.json"))["routes"]
        dests = sorted({r["destination"] for r in routes if r["surface"] == "S3"})
        with tempfile.TemporaryDirectory() as tmp:
            for arm in ("control", "variant"):
                run = Path(tmp) / arm
                try:
                    receipt = wrapper.prepare(ROOT, run, "f01", arm, materials)
                    self.assertEqual(receipt, json.loads((run / "receipt.json").read_text()))
                    self.assertEqual(task["BASE_SHA"], git("rev-parse", "HEAD",
                                                         root=run / "repo").decode().strip())
                    self.assertEqual(b"", git("status", "--porcelain", "--ignored",
                                              root=run / "repo"))
                    self.assertNotEqual(0, subprocess.run(
                        ["git", "-C", str(run), "rev-parse", "--show-toplevel"],
                        capture_output=True).returncode)
                    base_paths = set(git("ls-tree", "-r", "--name-only", task["BASE_SHA"])
                                     .decode().splitlines())
                    for path in (run / "repo").rglob("*"):
                        if path.name in {"AGENTS.md", "H2_RULES.md", "H2_WARM"}:
                            self.assertIn(path.relative_to(run / "repo").as_posix(), base_paths)
                    carrier = git("show", f"{materials}:{H2_REL}/carriers/H2_LEAN_BOOTSTRAP.md")
                    if arm == "control":
                        carrier = (git("show", f"{materials}:{H2_REL}/harness/control-carrier-header.md")
                                   + git("show", f"{materials}:AGENTS.md")
                                   + git("show", f"{materials}:{H2_REL}/harness/control-carrier-footer.md"))
                    self.assertEqual(carrier, (run / "AGENTS.md").read_bytes())
                    self.assertEqual(digest(carrier), receipt["carrier_sha256"])
                    self.assertEqual("control_full_v1" if arm == "control" else "variant_lean_v1",
                                     receipt["carrier_kind"])
                    if arm == "variant":
                        manifest = json.loads(git("show", f"{materials}:{H2_REL}/variant-manifest.json"))
                        self.assertEqual(manifest["freeze"]["VARIANT_HASH"], digest(carrier))
                    rules = git("show", f"{materials}:RULES.md")
                    self.assertEqual(rules, (run / "H2_RULES.md").read_bytes())
                    self.assertEqual(digest(rules), receipt["rules_sha256"])
                    lines = []
                    for dest in dests:
                        data = git("show", f"{materials}:{dest}")
                        self.assertEqual(data, (run / "H2_WARM" / dest).read_bytes())
                        lines.append(f"{dest} {digest(data)}")
                    self.assertEqual(digest("\n".join(lines).encode()), receipt["warm_bundle_sha256"])
                    self.assertEqual(digest((FZ / "wrapper_delivery.py").read_bytes()),
                                     receipt["program_sha256"])
                    self.assertEqual(("f01", arm, task["BASE_SHA"], materials),
                                     tuple(receipt[k] for k in
                                           ("task_id", "arm", "base_sha", "materials_commit")))
                finally:
                    if run.exists():
                        wrapper.cleanup(ROOT, run)
                self.assertFalse(run.exists())

    def test_stray_delivery_inside_repo_rolls_back_the_entire_allocation(self):
        wrapper = load("wrapper_delivery")
        real_git = wrapper.git
        before = git("worktree", "list", "--porcelain")
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "contaminated"

            def contaminate(root, *args, **kwargs):
                result = real_git(root, *args, **kwargs)
                if args[:2] == ("worktree", "add"):
                    stray = run / "repo" / "nested" / "H2_RULES.md"
                    stray.parent.mkdir()
                    stray.write_text("stray\n")
                return result

            with mock.patch.object(wrapper, "git", side_effect=contaminate):
                with self.assertRaisesRegex(ValueError, "DELIVERY_INSIDE_REPO"):
                    wrapper.prepare(ROOT, run, "f01", "variant", "HEAD")
            self.assertFalse(run.exists())
        self.assertEqual(before, git("worktree", "list", "--porcelain"))

    def test_ignored_stray_file_also_fails_closed(self):
        wrapper = load("wrapper_delivery")
        real_git = wrapper.git
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "ignored"

            def contaminate(root, *args, **kwargs):
                result = real_git(root, *args, **kwargs)
                if args[:2] == ("worktree", "add"):
                    cache = run / "repo" / "__pycache__"
                    cache.mkdir()
                    (cache / "stray.pyc").write_bytes(b"stray")
                return result

            with mock.patch.object(wrapper, "git", side_effect=contaminate):
                with self.assertRaisesRegex(ValueError, "REPO_NOT_CLEAN"):
                    wrapper.prepare(ROOT, run, "f01", "control", "HEAD")
            self.assertFalse(run.exists())

    def test_refuses_existing_or_in_repository_target_without_deleting_it(self):
        wrapper = load("wrapper_delivery")
        with tempfile.TemporaryDirectory() as tmp:
            existing = Path(tmp)
            with self.assertRaises(ValueError):
                wrapper.prepare(ROOT, existing, "f01", "control", "HEAD")
            self.assertTrue(existing.exists())
        with self.assertRaisesRegex(ValueError, "RUN_DIR_INSIDE_REPOSITORY"):
            wrapper.prepare(ROOT, FZ / "forbidden-run", "f01", "control", "HEAD")
        self.assertFalse((FZ / "forbidden-run").exists())


class DeliveryAnchors(unittest.TestCase):
    def test_all_ten_wrapper_anchors_are_neutral_in_both_arms(self):
        anchors = json.loads((FZ / "delivery-anchors.json").read_text())
        self.assertEqual(10, anchors["neutral_tasks_per_slot"]["WRAPPER"])
        self.assertEqual(10, len(anchors["rows"]))
        for row in anchors["rows"]:
            for arm in ("control", "variant"):
                key = f"WRAPPER/{arm}"
                self.assertEqual("DELIVERY_NEUTRAL", row["verdict"][key])
                for gate in ("oracle", "full_suite"):
                    pre, post = row["pre_delivery"][gate], row["post_delivery"][key][gate]
                    self.assertGreater(pre["ran"], 0)
                    self.assertEqual(pre["not_passing"], post["not_passing"])
                    self.assertEqual(pre["rc"], post["rc"])
                    self.assertEqual(0, post["ran_delta"])
                    self.assertEqual([], post["newly_not_passing"])
                    self.assertEqual([], post["newly_passing"])

    def test_expected_failure_and_unexpected_success_are_not_passes(self):
        anchors = load("delivery_anchors")
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "scripts" / "tests"
            tests.mkdir(parents=True)
            (tests / "test_status.py").write_text(
                "import unittest\n"
                "class Status(unittest.TestCase):\n"
                "    @unittest.expectedFailure\n"
                "    def test_expected(self):\n"
                "        self.fail('expected')\n"
                "    @unittest.expectedFailure\n"
                "    def test_unexpected(self):\n"
                "        pass\n"
                "    @unittest.skip('skip')\n"
                "    def test_skipped(self):\n"
                "        pass\n", encoding="utf-8")
            result = anchors.run_gate(Path(tmp), "test_status.py")
        self.assertEqual(3, result["ran"])
        self.assertEqual(["test_status.Status.test_expected"], result["expected_failures"])
        self.assertEqual(["test_status.Status.test_unexpected"], result["unexpected_successes"])
        self.assertEqual(["test_status.Status.test_skipped"], result["skipped"])
        self.assertEqual({"test_status.Status.test_expected", "test_status.Status.test_unexpected",
                          "test_status.Status.test_skipped"}, set(result["not_passing"]))


class IsolationCanary(unittest.TestCase):
    def fixture(self):
        return [
            {"type": "text", "part": {"text": "H2_CANARY_WRAPPER_STARTUP"}},
            {"type": "tool_use", "part": {"tool": "read", "state": {
                "input": {"filePath": "repo/probe.txt"}}}},
            {"type": "text", "part": {"text": "H2_CANARY_REPO_ATTACHED"}},
            {"type": "tool_use", "part": {"tool": "read", "state": {
                "input": {"filePath": "repo/nested/probe.txt"}}}},
            {"type": "text", "part": {"text": "H2_CANARY_NESTED_ATTACHED"}},
            {"type": "step_finish", "part": {"reason": "stop"}},
        ]

    def test_positive_event_stream(self):
        canary = load("isolation_canary")
        result = canary.check_stream("\n".join(map(json.dumps, self.fixture())))
        self.assertEqual("PASS", result["verdict"])
        for key in ("wrapper_at_startup", "repo_after_first_read", "nested_after_read"):
            self.assertTrue(result[key])

    def test_each_isolation_or_order_violation_fails_closed(self):
        canary = load("isolation_canary")
        for label, event in (
            ("repo early", {"type": "text", "part": {"text": "H2_CANARY_REPO_ATTACHED"}}),
            ("nested early", {"type": "text", "part": {"text": "H2_CANARY_NESTED_ATTACHED"}}),
            ("mcp tool", {"type": "tool_use", "part": {"tool": "mcp__remote__query"}}),
            ("plugin agent", {"type": "tool_use", "part": {"tool": "agent"}}),
            ("plugin metadata", {"type": "step_start", "part": {"plugins": ["custom"]}}),
            ("global instructions", {"type": "text", "part": {
                "text": "Instructions from: ~/.config/opencode/AGENTS.md"}}),
            ("user instructions", {"type": "text", "part": {
                "text": "Instructions from: ~/AGENTS.md"}}),
            ("skill text", {"type": "text", "part": {"text": "<skills_instructions>"}}),
            ("skill source", {"type": "text", "part": {"text": "skills/example/SKILL.md"}}),
            ("runtime error", {"type": "error", "error": {"name": "RuntimeError"}}),
            ("bad read input", {"type": "tool_use", "part": {"tool": "read", "state": {
                "input": []}}}),
        ):
            with self.subTest(label=label):
                events = self.fixture()
                events.insert(1, event)
                result = canary.check_stream("\n".join(map(json.dumps, events)))
                self.assertEqual("FAIL", result["verdict"])
                self.assertTrue(result["reasons"])
        for events in (self.fixture()[1:], self.fixture()[:-1], []):
            self.assertEqual("FAIL", canary.check_stream("\n".join(map(json.dumps, events)))
                             ["verdict"])
        self.assertEqual("FAIL", canary.check_stream('{"type":')["verdict"])

    def test_prepare_only_constructs_files_and_prints_a_command(self):
        canary = load("isolation_canary")
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "canary"
            command = canary.prepare(run)
            self.assertIn("source ~/.h2-worker-profile/env.sh", command)
            self.assertIn("opencode run --standalone --format json -m "
                          "opencode-go/deepseek-v4.1-flash", command)
            for rel, token in (("AGENTS.md", "H2_CANARY_WRAPPER_STARTUP"),
                               ("repo/AGENTS.md", "H2_CANARY_REPO_ATTACHED"),
                               ("repo/nested/AGENTS.md", "H2_CANARY_NESTED_ATTACHED")):
                self.assertIn(token, (run / rel).read_text())
            self.assertEqual(b"", git("status", "--porcelain", root=run / "repo"))


class RegistryV2(unittest.TestCase):
    def test_generator_is_byte_deterministic_and_matches_checked_in_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs = [Path(tmp) / f"registry-{i}.json" for i in range(2)]
            for out in outputs:
                subprocess.run([sys.executable, str(FZ / "build_registry.py"), "--out", str(out)],
                               check=True, capture_output=True)
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
            self.assertEqual((FZ / "task-registry-v2.json").read_bytes(), outputs[0].read_bytes())

    def test_oracle_identity_scope_and_worker_visible_fields(self):
        registry = json.loads((FZ / "task-registry-v2.json").read_text())
        shortlist = json.loads((H2 / "admission/freeze-v2-input/shortlist.json").read_text())["shortlist"]
        self.assertEqual([f"f{i:02d}" for i in range(1, 11)],
                         [task["task_id"] for task in registry["tasks"]])
        visible = list(text_fields({k: v for k, v in registry.items() if k != "expected"}))
        for task, source in zip(registry["tasks"], shortlist, strict=True):
            candidate, base = source["CANDIDATE_SHA"], source["BASE_SHA"]
            self.assertFalse(any(candidate[:7] in field for field in visible))
            self.assertEqual(candidate, registry["expected"][task["task_id"]]["candidate_sha"])
            self.assertEqual(source["CASE_ID"], task["case_id"])
            self.assertEqual(base, task["base_sha"])
            oracle = task["oracle"]
            self.assertEqual(digest(git("show", f"{base}:{oracle['path']}")), oracle["base_blob_sha256"])
            self.assertEqual(digest(git("show", f"{candidate}:{oracle['path']}")),
                             oracle["candidate_blob_sha256"])
            self.assertEqual(oracle["base_blob_sha256"], oracle["candidate_blob_sha256"])
            self.assertEqual("FRAMEWORK_FROZEN", oracle["provenance"])
            base_tests = set(git("ls-tree", "-r", "--name-only", base, "--", "scripts/tests/")
                             .decode().splitlines())
            self.assertEqual(base_tests | {oracle["path"]}, set(task["scope"]["deny"]))
            self.assertEqual([], task["scope"]["deny_prefixes"])
            delta = git("diff", base, candidate, "--", ":!scripts/tests").decode()
            for line in delta.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    added = line[1:].strip()
                    if len(added) >= 20:
                        self.assertFalse(any(added in field for field in visible),
                                         f"candidate text leaked: {task['task_id']}")


class RunPlanV2(unittest.TestCase):
    def test_twenty_unique_counterbalanced_fresh_runs_share_one_environment(self):
        plan = json.loads((FZ / "run-plan-v2.json").read_text())
        runs = plan["runs"]
        tasks = json.loads((FZ / "task-registry-v2.json").read_text())["tasks"]
        self.assertEqual(20, len(runs))
        self.assertEqual(20, len({r["run_id"] for r in runs}))
        self.assertEqual(1, len({r["materials_commit"] for r in runs}))
        self.assertEqual({"opencode-go/deepseek-v4.1-flash"}, {r["model"] for r in runs})
        self.assertEqual({"opencode 2.0.25 --standalone"}, {r["runtime"] for r in runs})
        self.assertEqual({"~/.h2-worker-profile"}, {r["profile"] for r in runs})
        self.assertTrue(all(r["fresh_episode"] for r in runs))
        self.assertFalse(any("session_id" in r for r in runs))
        first = Counter()
        for i, task in enumerate(tasks):
            pair = runs[2 * i:2 * i + 2]
            self.assertEqual([task["task_id"]] * 2, [r["task_id"] for r in pair])
            self.assertEqual(Counter({"control": 1, "variant": 1}), Counter(r["arm"] for r in pair))
            self.assertEqual("control" if i % 2 == 0 else "variant", pair[0]["arm"])
            first[pair[0]["arm"]] += 1
            for row in pair:
                self.assertEqual(f"h2r2-{task['task_id']}-{row['arm'][0]}", row["run_id"])
        self.assertEqual(Counter({"control": 5, "variant": 5}), first)
        generated = load("build_run_plan").build(runs[0]["materials_commit"])
        self.assertEqual(plan, generated)
