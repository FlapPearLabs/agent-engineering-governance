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
EXPECTED_V2_HASHES = {
    "experiments/v1.2/h2-lazy-disclosure/admission/batch-1/classification.json": "2b8aadff933c80966b780f86854bce8c87644d753338d7aa60d736f0fea36726",
    "experiments/v1.2/h2-lazy-disclosure/admission/batch-1/ledger.json": "765c21b90044646882256cbbfee66554e8cbd0580f07aacc27c080154d4e7305",
    "experiments/v1.2/h2-lazy-disclosure/admission/batch-2/classification.json": "53a47aca3050d79fbb05ef088900bd9b6c3840b00efc483abdb5405cf2b8a35a",
    "experiments/v1.2/h2-lazy-disclosure/admission/batch-2/ledger.json": "f5fd1b52623aa39e45adc409f9d98f3ae77c9f5b2da6f4858ee9a5df93a2d23a",
    "experiments/v1.2/h2-lazy-disclosure/admission/batch-3/classification.json": "fce7b9da373dd40d7e4841b432ade9eacb140de386e0c1db2f8c1ae025d202c5",
    "experiments/v1.2/h2-lazy-disclosure/admission/batch-3/ledger.json": "412eb5ca6f87d903d18f8cb119c4526b003d7de5d33a6df26ec465e6376c9f32",
    "experiments/v1.2/h2-lazy-disclosure/admission/batch-4/classification.json": "605e5eb6f80258172dcf2aa9f8b306b79a60381973427c18ce95729f71961071",
    "experiments/v1.2/h2-lazy-disclosure/admission/batch-4/ledger.json": "048705f5418af830bba30a4a3f2a48041f1672eadff39ac7b902a0d952b65a5e",
    "experiments/v1.2/h2-lazy-disclosure/admission/freeze-v2-input/shortlist.json": "34bd783b8b55383b8fa7189c44a357077e6b165847e4afe6dcbad10a4cafc803",
    "experiments/v1.2/h2-lazy-disclosure/carriers/H2_LEAN_BOOTSTRAP.md": "c5c8261591d70b21c167b1659e1d06cbb3f8f7d347b261180e321f6d6b0c932b",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/aggregate_set.py": "dc36eef9419904123361a060833aa8287f106e961d183101487c6e91d4f0eb55",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_manifest.py": "706e79d1c541a0aa0c90b89d326d12abf7cdc6581975cd4726578b2ee3213981",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_registry.py": "57a06cb8f090c4499399c7942da4b5cb17a41178efab07365206b61033918c0f",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_run_plan.py": "9f712ca9b80a7e533a27c00c4715768f90b31d64ffea9d9bef61ff5a09c35a7f",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/delivery-anchors.json": "d5cced185b8790b8f9ee889ab50abd8560a81df29049743b396461ca938c2371",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/delivery_anchors.py": "365414247910ae438f39d8c94973d076e85e7ae907b4f358c330b5f64db922ac",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/isolation_canary.py": "a2aa34d7bf478f5ba93629df16e21b61aa4d3821952a7dd7118168b5e95e17d2",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/protocol-v2.md": "bbe2b39ef03a75fa0a48a3cc42ca91a7aace0253b3470797718b51c94350abed",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/render_brief.py": "debe7dcd480d602b2781b0ae3acd0bf9e272f35aa53cb40eacbd273f9eae0f97",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/route-preconditions.json": "31e4108d079a9125c1292dddca3c8a9c0246b070533a7b648a07b16ea2cb4815",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/route_preconditions.py": "9fabe14ca56ad7b94f763edc69bf15ec6fd5ec2b4c43f51c5ee72fa381e7026c",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/run-plan-v2.json": "9cdc91d40e1e079f025019dc2e70cd7ed3ca1e73e1c03795d8e9e0ce28502357",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/task-registry-v2.json": "1f4185426076af40d67bc6a4df171979cf1b92ec81c7d3de87e786a989b8a98c",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/worker-brief-v2.md": "57ff9a3bacba43a82b1e62d383533e0726a7de370c51e2b9b6012089a7d23318",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/wrapper_delivery.py": "c8a2838fbc0c2edf2fa276eeaab87964fe4457d5606dc88419d730142583cd95",
    "experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py": "f4ae829acf4d2416bce9d6b721f631149e22ef0378ae78eb9bc15c880059c666",
    "experiments/v1.2/h2-lazy-disclosure/harness/control-carrier-footer.md": "cb0dfc40247c1575c0706175b3d4bf029973e8b94bf943e6fbccf9a485549186",
    "experiments/v1.2/h2-lazy-disclosure/harness/control-carrier-header.md": "50193bcc4cb882094ee5afcf3e3126a1d610c8f699905e4ac3c97beeab38986e",
    "experiments/v1.2/h2-lazy-disclosure/harness/worker-report-template.md": "540cd07c612319e67b0bce796cbadee1ac57e189613a9de571514414d24dc2f2",
    "experiments/v1.2/h2-lazy-disclosure/routes-h2.json": "a9d0e61dc85fe4bead5d993ddc0bb805e683bdea88d6c36c3aecdd5653304636",
    "experiments/v1.2/h2-lazy-disclosure/scoring-rubric.md": "bcaa4e624f10fe4a9a42852db92cc5e777c7255c8d891680bd72d87ab74c7cef",
    "experiments/v1.2/h2-lazy-disclosure/variant-manifest.json": "8abc1c05a076e39f3b7d04bb1784e7d36cb5e3f1556c5f24b2f47d6ebc164137",
}
MANIFEST_SHA256 = "0bef47f7d175a453c0ec547ccc294d4c08c3569f145bedcda6abb42d61334f53"


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


F1_SHADOW_SOURCE = '''"""Added module: `unittest discover -s scripts/tests` puts this directory first on
sys.path, so this file IS the `json` module for everything the frozen oracle imports."""
import importlib.util
import os
import sys

_self = os.path.dirname(os.path.abspath(__file__))
for _entry in list(sys.path):
    if not _entry or os.path.abspath(_entry) == _self:
        continue
    _init = os.path.join(_entry, "json", "__init__.py")
    if os.path.isfile(_init):
        _spec = importlib.util.spec_from_file_location(
            "json", _init, submodule_search_locations=[os.path.dirname(_init)])
        _real = importlib.util.module_from_spec(_spec)
        sys.modules["json"] = _real
        _spec.loader.exec_module(_real)
        break


def _always_ok(self, result=None):
    result = self._resultForDoCleanups if result is None else result
    if result is not None:
        result.startTest(self)
        result.addSuccess(self)
        result.stopTest(self)


import unittest  # noqa: E402
unittest.TestCase.run = _always_ok
'''


def registry_tasks():
    return json.loads((FZ / "task-registry-v2.json").read_text())["tasks"]


def registry_sources():
    return json.loads((H2 / "admission/freeze-v2-input/shortlist.json").read_text())["shortlist"]


def task_pair(task_id):
    task = next(t for t in registry_tasks() if t["task_id"] == task_id)
    source = next(s for s in registry_sources() if s["CASE_ID"] == task["case_id"])
    return task, source


def prepare_run(tmp, task_id, arm="control"):
    wrapper = load("wrapper_delivery")
    run = Path(tmp) / f"run-{task_id}-{arm}"
    wrapper.prepare(ROOT, run, task_id, arm, git("rev-parse", "HEAD").decode().strip())
    return run


def write_artifacts(run, report="# report\n\nFilled.\n",
                    telemetry="READ FULL repo/RULES.md\n"):
    if report is not None:
        (run / "report.md").write_text(report, encoding="utf-8")
    if telemetry is not None:
        (run / ".h2-telemetry.log").write_text(telemetry, encoding="utf-8")


def apply_candidate_delta(repo, base, candidate):
    """The historical candidate's NON-TEST delta (the positive control's worker result)."""
    patch = git("diff", "--binary", base, candidate, "--", ":!scripts/tests")
    subprocess.run(["git", "-C", str(repo), "apply", "--whitespace=nowarn"], input=patch,
                   capture_output=True, check=True)


def commit_in(repo, message):
    subprocess.run(["git", "-C", str(repo), "add", "-A"], capture_output=True, check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=FlapPearLabs", "-c",
                    "user.email=151931662+FlapPearLabs@users.noreply.github.com",
                    "commit", "-qm", message], capture_output=True, check=True)


def cleanup_run(run):
    if Path(run).exists():
        load("wrapper_delivery").cleanup(ROOT, Path(run))


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

    def real_stream(self):
        return (FZ / "fixtures" / "isolation-canary-events.jsonl").read_text(encoding="utf-8")

    def real_events(self):
        return [json.loads(line) for line in self.real_stream().splitlines() if line.strip()]

    @staticmethod
    def render(events):
        return "\n".join(json.dumps(event) for event in events)

    def text_event(self, text):
        return {"type": "text", "part": {"type": "text", "text": text}}

    def read_event(self, path):
        return {"type": "tool_use", "part": {"type": "tool", "tool": "read", "state": {
            "status": "completed", "input": {"path": path}}}}

    def test_the_real_opencode_event_stream_passes(self):
        """The committed fixture is the real 2.0.25 stream (paths sanitised to <RUN_ROOT>)."""
        canary = load("isolation_canary")
        verdict = canary.check_stream(self.real_stream())
        self.assertEqual("PASS", verdict["verdict"], verdict["reasons"])
        self.assertEqual(10, verdict["event_count"])
        for key in ("wrapper_at_startup", "repo_after_first_read", "nested_after_read"):
            self.assertTrue(verdict[key])
        text = self.real_stream()
        self.assertIn("<RUN_ROOT>", text)
        for host_prefix in ("/Users/", "/private/"):
            self.assertNotIn(host_prefix, text)
        events = self.real_events()
        self.assertEqual({"step_start", "text", "tool_use", "step_finish"},
                         {event["type"] for event in events})
        reads = [event for event in events if event["type"] == "tool_use"]
        self.assertEqual({"repo/probe.txt", "repo/nested/probe.txt"},
                         {canary.normalise_path(event["part"]["state"]["input"]["path"], Path("."))
                          for event in reads})

    def test_each_real_schema_refusal_is_reported(self):
        canary = load("isolation_canary")
        base = self.real_events()
        wrapper_index = 1
        first_read = 2
        repo_text = 5
        mutants = {
            "marker missing": (self.render(
                [event if index != wrapper_index else self.text_event(
                    event["part"]["text"].replace("H2_CANARY_WRAPPER_STARTUP", "no marker here"))
                 for index, event in enumerate(base)]), "NO_WRAPPER_AT_STARTUP"),
            "repo marker before its read": (self.render(
                base[:first_read] + [self.text_event("H2_CANARY_REPO_ATTACHED")] + base[first_read:]),
                "REPO_BEFORE_READ"),
            "nested marker before its read": (self.render(
                base[:first_read + 1] + [self.text_event("H2_CANARY_NESTED_ATTACHED")]
                + base[first_read + 1:]), "NESTED_BEFORE_READ"),
            "extra read": (self.render(
                base[:repo_text + 2] + [self.read_event("repo/other.txt")] + base[repo_text + 2:]),
                "UNEXPECTED_READ"),
            "mcp named in text": (self.render(
                base + [self.text_event("MCP server `remote` connected from the user profile.")]),
                "MCP_CONTAMINATION"),
            "plugin agent named in text": (self.render(
                base + [self.text_event("Plugin agent `reviewer` is loaded in this profile.")]),
                "PLUGIN_AGENT_CONTAMINATION"),
            "skill catalogue named in text": (self.render(
                base + [self.text_event("Skills: `alpha-skill`, `report`")]),
                "SKILL_CATALOGUE_CONTAMINATION"),
            "non-read tool": (self.render(
                base[:first_read] + [{"type": "tool_use", "part": {
                    "type": "tool", "tool": "bash"}}] + base[first_read:]),
                "FORBIDDEN_TOOL_OR_AGENT"),
            "truncated stream": (self.render(base[:-1]), "INCOMPLETE_STREAM"),
        }
        for label, (stream, reason) in mutants.items():
            with self.subTest(label=label):
                verdict = canary.check_stream(stream)
                self.assertEqual("FAIL", verdict["verdict"], label)
                self.assertIn(reason, verdict["reasons"], verdict["reasons"])

    def test_the_f4_home_run_fails_on_the_disclosed_skill_catalogue(self):
        """F4's own evidence, reduced to its observable claim: the operator catalogue is named."""
        canary = load("isolation_canary")
        stream = self.render(self.real_events() + [
            self.text_event("**Skills:** the available-skills catalog is present in context "
                            "(large bundled list, e.g. `alpha-skill`, `opencode`, "
                            "`beta-skill`, …); no individual skill content is loaded yet.")])
        verdict = canary.check_stream(stream)
        self.assertEqual("FAIL", verdict["verdict"])
        self.assertIn("SKILL_CATALOGUE_CONTAMINATION", verdict["reasons"])
        allowed = self.render(self.real_events() + [
            self.text_event("two skill sources (`opencode`, `report`), no MCP or plugin-agent "
                            "sources")])
        self.assertEqual("PASS", canary.check_stream(allowed)["verdict"])

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
            self.assertEqual(["scripts/tests/"], task["scope"]["deny_prefixes"])
            delta = git("diff", base, candidate, "--", ":!scripts/tests").decode()
            for line in delta.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    added = line[1:].strip()
                    if len(added) >= 20:
                        self.assertFalse(any(added in field for field in visible),
                                         f"candidate text leaked: {task['task_id']}")


class WorkerScopeV2(unittest.TestCase):
    def task(self):
        return json.loads((FZ / "task-registry-v2.json").read_text())["tasks"][0]

    def test_every_task_freezes_the_discovery_directory_as_a_prefix(self):
        registry = json.loads((FZ / "task-registry-v2.json").read_text())
        self.assertEqual(10, len(registry["tasks"]))
        for task in registry["tasks"]:
            self.assertEqual(["scripts/tests/"], task["scope"]["deny_prefixes"], task["task_id"])
        self.assertIn("F1", registry["scope_prefix_source"])
        scope = load("scope_v2")
        for path in ("scripts/tests/json.py", "scripts/tests/new_test.py",
                     "scripts/tests/package/__init__.py", "scripts/tests/unittest.py"):
            with self.subTest(path=path):
                reasons = scope.check_scope(self.task(), [{"status": "A", "path": path}])
                self.assertTrue(any(r.startswith("WORKER_SCOPE_DENIED") for r in reasons), reasons)

    def test_the_f1_shadow_would_really_shadow_a_stdlib_import(self):
        """The refusal below is not vacuous: the added file does decide the import."""
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "scripts" / "tests"
            tests.mkdir(parents=True)
            (tests / "json.py").write_text("MARKER = 'shadowed'\n", encoding="utf-8")
            probe = subprocess.run(
                [sys.executable, "-s", "-c",
                 "import json; print(getattr(json, 'MARKER', 'stdlib'))"],
                cwd=str(tests), capture_output=True, text=True, check=True)
        self.assertEqual("shadowed", probe.stdout.strip())

    def test_added_stdlib_named_module_elsewhere_is_refused_by_the_shadow_rule(self):
        scope = load("scope_v2")
        for path in ("scripts/json.py", "json.py", "unittest.py", "scripts/shadow.pyc",
                     "scripts/__init__.py", "scripts/tests/package/__init__.py"):
            with self.subTest(path=path):
                reasons = scope.check_scope(self.task(), [{"status": "A", "path": path}])
                self.assertTrue(any(r.startswith("WORKER_SHADOWS_IMPORT") for r in reasons),
                                reasons)

    def test_startup_hooks_and_path_escapes_are_refused_anywhere(self):
        scope = load("scope_v2")
        for path, reason in (("nested/sitecustomize.py", "WORKER_STARTUP_HOOK"),
                             ("nested/usercustomize.py", "WORKER_STARTUP_HOOK"),
                             ("nested/extra.pth", "WORKER_STARTUP_HOOK"),
                             ("../outside.py", "WORKER_PATH_ESCAPE"),
                             ("/absolute/outside.py", "WORKER_PATH_ESCAPE")):
            with self.subTest(path=path):
                reasons = scope.check_scope(self.task(), [{"status": "A", "path": path}])
                self.assertTrue(any(r.startswith(reason) for r in reasons), reasons)
        self.assertEqual([], scope.check_scope(self.task(),
                                              [{"status": "A", "path": "docs/fix.md"},
                                               {"status": "M", "path": "scripts/review_evidence.py"}]))

    def test_both_sides_of_a_rename_are_judged(self):
        scope = load("scope_v2")
        task = self.task()
        reasons = scope.check_scope(task, [{"status": "R100", "old_path": "scripts/tests/old.py",
                                            "path": "scripts/json.py"}])
        self.assertTrue(any(r.startswith("WORKER_SCOPE_DENIED") for r in reasons), reasons)
        self.assertTrue(any(r.startswith("WORKER_SHADOWS_IMPORT") for r in reasons), reasons)
        self.assertEqual([], scope.check_scope(task, [{"status": "M", "path": "RULES.md"}]))


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


class WorkerBriefV2(unittest.TestCase):
    def test_all_pairs_differ_only_inside_delivery_block(self):
        renderer = load("render_brief")
        tasks = json.loads((FZ / "task-registry-v2.json").read_text())["tasks"]
        runs = json.loads((FZ / "run-plan-v2.json").read_text())["runs"]
        expected = json.loads((FZ / "task-registry-v2.json").read_text())["expected"]
        for task in tasks:
            rendered = [renderer.render(task, next(r for r in runs if r["task_id"] == task["task_id"]
                                                   and r["arm"] == arm), "<TOOLCHAIN_PYTHON>")
                        for arm in ("control", "variant")]
            bodies = []
            for text in rendered:
                before, rest = text.split("<!-- BOOTSTRAP_DELIVERY_BEGIN -->")
                block, after = rest.split("<!-- BOOTSTRAP_DELIVERY_END -->")
                self.assertIn("CARRIER_SHA256", block)
                self.assertIn("RUN_ID", block)
                self.assertIn("git -C repo rev-parse HEAD", text)
                self.assertIn("./.h2-telemetry.log", text)
                self.assertIn("./report.md", text)
                self.assertIn("freeze-v2/", text)
                for answer in expected.values():
                    self.assertNotIn(answer["candidate_sha"][:7], text)
                bodies.append((before, after))
            self.assertEqual(bodies[0], bodies[1])
            self.assertNotEqual(rendered[0], rendered[1])

    def test_cli_copies_the_report_template_outside_the_repository(self):
        run = json.loads((FZ / "run-plan-v2.json").read_text())["runs"][0]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "contract.md"
            subprocess.run([sys.executable, str(FZ / "render_brief.py"), "--run-id", run["run_id"],
                            "--python", "<TOOLCHAIN_PYTHON>", "--out", str(out)],
                           check=True, capture_output=True)
            self.assertTrue(out.is_file())
            self.assertEqual(git("show", f"{run['materials_commit']}:{H2_REL}/harness/"
                                 "worker-report-template.md"),
                             (Path(tmp) / "worker-report-template.md").read_bytes())


class ProtocolV2(unittest.TestCase):
    def test_authority_tokens_and_verbatim_confound(self):
        protocol = (FZ / "protocol-v2.md").read_text()
        self.assertNotIn("baseline must be green", protocol.casefold())
        for token in ("FZ2_1", "FZ2_2", "FZ2_3", "FZ2_4", "DISCLOSURE_SAFE",
                      "DISCLOSURE_HAS_COST", "INSUFFICIENT_EVIDENCE", "NOT_ADMITTED_CURRENT_REVISION"):
            self.assertIn(token, protocol)

        def confound(text):
            lines = text.splitlines(keepends=True)
            start = next(i for i, line in enumerate(lines) if line.startswith("DISCLOSED CONFOUND"))
            end = next(i for i in range(start + 1, len(lines)) if lines[i].strip() == "```")
            return "".join(lines[start:end]).encode()

        self.assertEqual(confound((FZ / "README.md").read_text()), confound(protocol))

    def test_aggregate_is_exactly_valid_request_intersect_frozen_membership(self):
        aggregate = load("aggregate_set")
        registry = json.loads((FZ / "task-registry-v2.json").read_text())
        records = []
        for i in range(1, 5):
            records.extend(json.loads((H2 / f"admission/batch-{i}/classification.json")
                                      .read_text())["records"])
        selected = aggregate.derive(records, registry)
        self.assertEqual([t["task_id"] for t in registry["tasks"]],
                         [t["task_id"] for t in selected])
        self.assertEqual({"tasks": 10, "planned_per_arm": 10, "planned_runs": 20},
                         aggregate.counts(selected))
        first, second = registry["tasks"][:2]
        fixture = [{"corpus_case_id": first["case_id"],
                    "round_admission": {"verdict": "REQUEST_VALID"}},
                   {"corpus_case_id": second["case_id"],
                    "round_admission": {"verdict": "NOT_ADMITTED"}},
                   {"corpus_case_id": "t02", "round_admission": {"verdict": "REQUEST_VALID"}}]
        result = aggregate.derive(fixture, registry)
        self.assertEqual([first["task_id"]], [t["task_id"] for t in result])
        self.assertEqual({"tasks": 1, "planned_per_arm": 1, "planned_runs": 2}, aggregate.counts(result))
        with self.assertRaises(ValueError):
            aggregate.derive(fixture + [fixture[0]], registry)


class CollectionV2(unittest.TestCase):
    def test_collect_reports_the_full_base_delta_including_worker_commits(self):
        collector = load("collect_v2")
        task, _ = task_pair("f01")
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f01")
            try:
                write_artifacts(run)
                repo = run / "repo"
                (repo / "docs").mkdir(exist_ok=True)
                (repo / "docs" / "worker-note.md").write_text("note\n", encoding="utf-8")
                commit_in(repo, "worker commit")
                (repo / "untracked-note.md").write_text("note\n", encoding="utf-8")
                collected = collector.collect(ROOT, run)
                self.assertEqual("VALID", collected["status"], collected["reasons"])
                self.assertEqual("h2r2-f01-c", collected["run_id"])
                self.assertEqual(task["base_sha"], collected["base_sha"])
                self.assertNotEqual(task["base_sha"],
                                    git("rev-parse", "HEAD", root=repo).decode().strip())
                statuses = {change["path"]: change["status"] for change in collected["changes"]}
                self.assertEqual("A", statuses["docs/worker-note.md"])
                self.assertEqual("A", statuses["untracked-note.md"])
                self.assertEqual({"AGENTS.md", "H2_RULES.md"},
                                 {name for name in collected["delivered_hashes"]
                                  if not name.startswith("H2_WARM/")})
                self.assertGreaterEqual(len(collected["delivered_hashes"]), 3)
                self.assertEqual(collected["diff_sha256"],
                                 digest(git("diff", "--binary", task["base_sha"], "--",
                                            root=repo)))
            finally:
                cleanup_run(run)

    def test_missing_or_empty_report_and_telemetry_are_invalid(self):
        collector = load("collect_v2")
        for label, kwargs, reason in (
            ("no telemetry", {"telemetry": None}, "MISSING_TELEMETRY"),
            ("empty telemetry", {"telemetry": "  \n"}, "EMPTY_TELEMETRY"),
            ("no report", {"report": None}, "MISSING_REPORT"),
            ("empty report", {"report": "\n\n"}, "EMPTY_REPORT"),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                run = prepare_run(tmp, "f02")
                try:
                    write_artifacts(run, **kwargs)
                    collected = collector.collect(ROOT, run)
                    self.assertEqual("INVALID", collected["status"])
                    self.assertIn(reason, collected["reasons"])
                finally:
                    cleanup_run(run)

    def test_tampered_delivered_bytes_are_refused_even_with_a_matching_receipt(self):
        collector = load("collect_v2")
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f03")
            try:
                write_artifacts(run)
                carrier = (run / "AGENTS.md").read_bytes()
                (run / "AGENTS.md").write_bytes(carrier + b"\nworker rewrite\n")
                collected = collector.collect(ROOT, run)
                self.assertEqual("INVALID", collected["status"])
                self.assertIn("DELIVERED_HASH_MISMATCH:AGENTS.md", collected["reasons"])
                self.assertIn("DELIVERED_BYTES_NOT_FROM_MATERIALS:AGENTS.md",
                              collected["reasons"])
            finally:
                cleanup_run(run)


class AcceptanceV2(unittest.TestCase):
    def test_positive_control_accepts_the_candidate_delta_for_all_ten_tasks(self):
        """The historical candidate's non-test delta applied to B' is the ACCEPT control."""
        acceptance = load("run_acceptance_v2")
        for task in registry_tasks():
            _, source = task_pair(task["task_id"])
            with self.subTest(task=task["task_id"]), tempfile.TemporaryDirectory() as tmp:
                run = prepare_run(tmp, task["task_id"])
                try:
                    apply_candidate_delta(run / "repo", task["base_sha"],
                                          source["CANDIDATE_SHA"])
                    write_artifacts(run)
                    verdict = acceptance.accept(ROOT, run)
                    self.assertEqual("ACCEPT", verdict["verdict"],
                                     f"{task['task_id']}: {verdict['reasons']}")
                    for style in ("RESOLVED", "SYMLINKED"):
                        self.assertTrue(verdict["oracle"]["base"][style]["rc"] != 0
                                        or verdict["oracle"]["base"][style]["not_passing"])
                        self.assertEqual(0, verdict["oracle"]["worker"][style]["rc"])
                        self.assertGreater(verdict["oracle"]["worker"][style]["ran"], 0)
                        suite = verdict["full_suite"]["worker"][style]
                        self.assertGreater(suite["ran"], 0)
                        self.assertEqual([], verdict["full_suite"][
                            f"newly_not_passing_{style.lower()}"])
                finally:
                    cleanup_run(run)

    def test_unchanged_base_is_rejected_for_all_ten_tasks(self):
        acceptance = load("run_acceptance_v2")
        for task in registry_tasks():
            with self.subTest(task=task["task_id"]), tempfile.TemporaryDirectory() as tmp:
                run = prepare_run(tmp, task["task_id"])
                try:
                    write_artifacts(run)
                    verdict = acceptance.accept(ROOT, run)
                    self.assertEqual("REJECT", verdict["verdict"], verdict["reasons"])
                    self.assertIn("WORKER_NOT_PASSING:RESOLVED", verdict["reasons"])
                    self.assertIn("WORKER_NOT_PASSING:SYMLINKED", verdict["reasons"])
                finally:
                    cleanup_run(run)

    def test_added_discovery_shadow_is_rejected_and_would_have_fooled_the_oracle(self):
        """F1 end to end: the added module really turns the unfixed oracle green."""
        acceptance = load("run_acceptance_v2")
        anchors = load("delivery_anchors")
        task, _ = task_pair("f01")
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f01")
            try:
                write_artifacts(run)
                (run / "repo" / "scripts" / "tests" / "json.py").write_text(
                    F1_SHADOW_SOURCE, encoding="utf-8")
                fooled = anchors.run_gate(run / "repo", "test_review_evidence_contract.py")
                self.assertEqual(0, fooled["rc"], "the F1 reproduction no longer fools the gate")
                self.assertEqual([], fooled["not_passing"])
                verdict = acceptance.accept(ROOT, run)
                self.assertEqual("REJECT", verdict["verdict"])
                self.assertIn("WORKER_SCOPE_DENIED:scripts/tests/json.py", verdict["reasons"])
                self.assertIn("WORKER_SHADOWS_IMPORT:scripts/tests/json.py:SHADOWS:json",
                              verdict["reasons"])
                self.assertNotIn("full_suite", verdict)
            finally:
                cleanup_run(run)

    def test_edited_oracle_and_edited_base_test_are_rejected(self):
        acceptance = load("run_acceptance_v2")
        task, _ = task_pair("f02")
        for label, rel in (("oracle", task["oracle"]["path"]),
                           ("base test", "scripts/tests/test_seam_contract_partitions.py")):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                run = prepare_run(tmp, "f02")
                try:
                    write_artifacts(run)
                    path = run / "repo" / rel
                    path.write_text(path.read_text(encoding="utf-8") + "\n# edited\n",
                                    encoding="utf-8")
                    verdict = acceptance.accept(ROOT, run)
                    self.assertEqual("REJECT", verdict["verdict"])
                    self.assertTrue(
                        f"WORKER_SCOPE_DENIED:{rel}" in verdict["reasons"]
                        or "ORACLE_BYTES_CHANGED" in verdict["reasons"], verdict["reasons"])
                finally:
                    cleanup_run(run)

    def test_delivered_byte_or_wrapper_artifact_inside_repo_is_rejected(self):
        acceptance = load("run_acceptance_v2")
        for label, rel, reason in (
            ("copied carrier", "docs/carrier-copy.md",
             "WORKER_DELIVERY_COPY_IN_REPO:docs/carrier-copy.md:AGENTS.md"),
            ("delivered name", "docs/AGENTS.md",
             "WORKER_WRAPPER_ARTIFACT_IN_REPO:docs/AGENTS.md"),
            ("report copy", "docs/report.md", "WORKER_WRAPPER_ARTIFACT_IN_REPO:docs/report.md"),
            ("warm layout", "H2_WARM/references/x.md",
             "WORKER_DELIVERED_LAYOUT_IN_REPO:H2_WARM/references/x.md"),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                run = prepare_run(tmp, "f04")
                try:
                    write_artifacts(run)
                    target = run / "repo" / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((run / "AGENTS.md").read_bytes()
                                       if rel != "docs/report.md" else b"# report\n")
                    verdict = acceptance.accept(ROOT, run)
                    self.assertEqual("REJECT", verdict["verdict"], verdict["reasons"])
                    self.assertIn(reason, verdict["reasons"])
                finally:
                    cleanup_run(run)

    def test_a_worker_commit_that_reverted_a_test_edit_still_shows_it(self):
        """The delta is taken against the registry base, never against HEAD."""
        acceptance = load("run_acceptance_v2")
        task, _ = task_pair("f05")
        rel = "scripts/tests/test_seam_contract_partitions.py"
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f05")
            try:
                write_artifacts(run)
                repo = run / "repo"
                path = repo / rel
                edit = path.read_text(encoding="utf-8") + "\n# worker edit\n"
                path.write_text(edit, encoding="utf-8")
                commit_in(repo, "worker edits a frozen test")
                subprocess.run(["git", "-C", str(repo), "-c", "user.name=FlapPearLabs",
                                "-c", "user.email=151931662+FlapPearLabs@users.noreply.github.com",
                                "revert", "--no-edit", "HEAD"], capture_output=True, check=True)
                path.write_text(edit, encoding="utf-8")
                base_blob = git("show", f"{task['base_sha']}:{rel}", root=repo)
                self.assertEqual(base_blob, git("show", f"HEAD:{rel}", root=repo))
                self.assertNotEqual(base_blob, path.read_bytes())
                verdict = acceptance.accept(ROOT, run)
                self.assertEqual("REJECT", verdict["verdict"])
                self.assertIn(f"WORKER_SCOPE_DENIED:{rel}", verdict["reasons"])
            finally:
                cleanup_run(run)

    def test_cli_writes_one_verdict_and_exits_zero_only_for_accept(self):
        task, _ = task_pair("f01")
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f01")
            try:
                write_artifacts(run)
                result = subprocess.run([sys.executable, str(FZ / "run_acceptance_v2.py"),
                                         str(run)], capture_output=True, text=True)
                self.assertEqual(1, result.returncode)
                verdict = json.loads((run / "verdict.json").read_text())
                self.assertEqual("REJECT", verdict["verdict"])
                self.assertEqual(task["base_sha"], verdict["base_sha"])
            finally:
                cleanup_run(run)
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty-run"
            empty.mkdir()
            result = subprocess.run([sys.executable, str(FZ / "run_acceptance_v2.py"),
                                     str(empty)], capture_output=True, text=True)
            self.assertEqual(1, result.returncode)
            verdict = json.loads((empty / "verdict.json").read_text())
            self.assertEqual("INVALID", verdict["verdict"])
            self.assertIn("COLLECTION_INVALID:MISSING_RECEIPT", verdict["reasons"])


def freeze_is_intact(root):
    try:
        data = (root / H2_REL / "freeze-v2/freeze-manifest.json").read_bytes()
        return (digest(data) == MANIFEST_SHA256
                and json.loads(data)["hashes"] == EXPECTED_V2_HASHES
                and not load("build_manifest").verify(root))
    except (OSError, ValueError, KeyError):
        return False


class FreezeManifest(unittest.TestCase):
    def test_two_independent_anchors_and_materials_parent_binding(self):
        self.assertTrue(freeze_is_intact(ROOT))
        manifest = json.loads((FZ / "freeze-manifest.json").read_text())
        for rel, expected in EXPECTED_V2_HASHES.items():
            self.assertEqual(expected, digest((ROOT / rel).read_bytes()), rel)
        materials = manifest["materials_commit"]
        self.assertEqual(materials, manifest["freeze_parent"])
        runs = json.loads((FZ / "run-plan-v2.json").read_text())["runs"]
        self.assertEqual({materials}, {r["materials_commit"] for r in runs})
        introductions = git("log", "--diff-filter=A", "--format=%H", "--",
                            f"{H2_REL}/freeze-v2/freeze-manifest.json").decode().splitlines()
        parent = git("rev-parse", f"{introductions[-1]}^" if introductions else "HEAD").decode().strip()
        self.assertEqual(parent, materials)
        measured = json.loads((FZ / "delivery-anchors.json").read_text())["materials_commit"]
        wrapper = load("wrapper_delivery")
        for arm in ("control", "variant"):
            self.assertEqual(wrapper.delivery(ROOT, measured, arm), wrapper.delivery(ROOT, materials, arm))
        for rel in (f"{H2_REL}/admission/freeze-v2-input/shortlist.json",
                    f"{H2_REL}/freeze-v2/wrapper_delivery.py"):
            self.assertEqual(git("show", f"{measured}:{rel}"), git("show", f"{materials}:{rel}"))

    def test_one_byte_mutation_of_every_frozen_file_is_rejected(self):
        manifest_rel = f"{H2_REL}/freeze-v2/freeze-manifest.json"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in [*EXPECTED_V2_HASHES, manifest_rel]:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / rel).read_bytes())
            self.assertTrue(freeze_is_intact(root))
            for rel in [*EXPECTED_V2_HASHES, manifest_rel]:
                with self.subTest(file=rel):
                    path = root / rel
                    original = path.read_bytes()
                    self.assertTrue(original)
                    path.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
                    try:
                        self.assertFalse(freeze_is_intact(root), rel)
                    finally:
                        path.write_bytes(original)
