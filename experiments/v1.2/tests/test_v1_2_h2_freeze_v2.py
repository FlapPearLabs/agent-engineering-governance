"""Freeze-v2 contract tests; no worker/model execution."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
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
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/access_audit.py": "8cce0b7ab34a975f66f6713251594374479a1be8efd0b272e1938b4319fb6fdf",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/aggregate_set.py": "dc36eef9419904123361a060833aa8287f106e961d183101487c6e91d4f0eb55",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_manifest.py": "b3f30ca7f706c2eb2fcfce5f80d58189b0cffb749c37af801ab87a14bc6b519d",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_registry.py": "57a06cb8f090c4499399c7942da4b5cb17a41178efab07365206b61033918c0f",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_run_plan.py": "0150309c6cc3a37af25a858f7bb1d089d5110965d74456e3a86a1b3c8a94bfa2",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/collect_v2.py": "5027d59c21a2de634c91c49efc1ea3745d5a1a5769e8475db42976d1908a5db5",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/delivery-anchors.json": "027a478352bdc9ac039dc1b24c07f771fa2ac51ed9158d1f0a2e34df70007167",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/delivery_anchors.py": "cc59707ddeaa22080fac6b66a28f87d162cc4a2847a7251e5a3f327d19e0d310",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/access-audit-clean.jsonl": "e79a8be43c13af170e9424c8d138fd2d42f37f50c93d97b6fe3d19afad3377d1",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/access-audit-hits.jsonl": "147e72b06bc03488918e23eedc20659f8cbb48b0508b9d12aff05d0d042c431b",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/canary-86ac104-events.jsonl": "2b596be37ac0b9aff56989302ee8b44af4246ea2a11f88b3c16875073130d82a",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/canary-86ac104-synthetic-sources-line.jsonl": "0d310198bc7ef4cab0734b4a4e01aebadcb4e862a032a305f50eed10ccb23ffa",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/isolation-canary-events.jsonl": "070743f27b4386e36f99c7fa86badf9b2b4d9b7293d27dc4af75099854acae8f",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/pilot-f01-c-events.jsonl": "8df3d734070e50bdd6e425da3fa43f9206daa1ffa1754b7ba5c28c4867d0e099",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/preflight-debug-config.json": "6e7ba3d7954852de5b4c931532160945a4ce76f728b46272e4b23f2e2ace78c2",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/preflight-debug-paths.txt": "cb7c7f731823fa7f96136e0272ba73079d3d455095b26c478a6518711ab68dbc",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/toolname-probe-events.jsonl": "7220205bd72abc05fd1d615cb6a69111685febfd40e0f7840b06cf5bcd9461e6",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/isolation_canary.py": "010a89522665d6229e95e5dcb339e4039d2ae4bc3e36001929d5aabe9a927056",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/protocol-v2.md": "ad45046426afdc2026e07c082d959f179ef4aaa5fece031e1368693dcae2ecb5",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/render_brief.py": "debe7dcd480d602b2781b0ae3acd0bf9e272f35aa53cb40eacbd273f9eae0f97",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/route-preconditions.json": "31e4108d079a9125c1292dddca3c8a9c0246b070533a7b648a07b16ea2cb4815",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/route_preconditions.py": "9fabe14ca56ad7b94f763edc69bf15ec6fd5ec2b4c43f51c5ee72fa381e7026c",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/run-plan-v2.json": "1371946a635852a5169b569e1569a7804df18358eac4ae51d98fdbfef5749355",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/run_acceptance_v2.py": "dbe91a3b490e41a4be7b4766fb01c937dd685327844ad88027a054dbd070e410",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/run_audit_v2.py": "e928d47ff121c2f56fc2f547235ccffd509ad18855ad45a0431d736f9f6a157a",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/run_h2r2.py": "aaef30a91e5eec176d3b808b3dd15c4fe90dbefe42eae7213b2ed09f0454beac",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/scope_v2.py": "7c0e0b0b7bf0c3b68452e914ff6831dbaea59fcf2666ad34cb0f9fe682075d9f",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/task-registry-v2.json": "1f4185426076af40d67bc6a4df171979cf1b92ec81c7d3de87e786a989b8a98c",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/worker-brief-v2.md": "57ff9a3bacba43a82b1e62d383533e0726a7de370c51e2b9b6012089a7d23318",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/worker-profile/opencode.json": "409f61b632da9001f18adf8e929094d2127ffe225c782d3eaec2c8106d695ba3",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/wrapper_delivery.py": "a4c6776e8aeadc5d85ed182d50d71f3d02eae12e9087b543973941c89227b2de",
    "experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py": "f4ae829acf4d2416bce9d6b721f631149e22ef0378ae78eb9bc15c880059c666",
    "experiments/v1.2/h2-lazy-disclosure/harness/control-carrier-footer.md": "cb0dfc40247c1575c0706175b3d4bf029973e8b94bf943e6fbccf9a485549186",
    "experiments/v1.2/h2-lazy-disclosure/harness/control-carrier-header.md": "50193bcc4cb882094ee5afcf3e3126a1d610c8f699905e4ac3c97beeab38986e",
    "experiments/v1.2/h2-lazy-disclosure/harness/worker-report-template.md": "540cd07c612319e67b0bce796cbadee1ac57e189613a9de571514414d24dc2f2",
    "experiments/v1.2/h2-lazy-disclosure/routes-h2.json": "a9d0e61dc85fe4bead5d993ddc0bb805e683bdea88d6c36c3aecdd5653304636",
    "experiments/v1.2/h2-lazy-disclosure/scoring-rubric.md": "bcaa4e624f10fe4a9a42852db92cc5e777c7255c8d891680bd72d87ab74c7cef",
    "experiments/v1.2/h2-lazy-disclosure/variant-manifest.json": "8abc1c05a076e39f3b7d04bb1784e7d36cb5e3f1556c5f24b2f47d6ebc164137",
}
MANIFEST_SHA256 = "82fd5e36bc57af8afb330f90d504a44777b49873b111035e748528f02526199b"


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

    def test_the_task_repository_is_standalone_and_cannot_read_the_candidate(self):
        """F8: one commit, no remote, no alternates, and the historical fix is not an object."""
        wrapper = load("wrapper_delivery")
        task, source = task_pair("f01")
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "history-free"
            try:
                receipt = wrapper.prepare(ROOT, run, "f01", "variant", "HEAD")
                repo = run / "repo"
                self.assertEqual("standalone_history_free", receipt["repository_kind"])
                self.assertEqual([task["base_sha"]],
                                 git("rev-list", "--all", root=repo).decode().split())
                self.assertEqual([], git("for-each-ref", "--format=%(refname)",
                                         root=repo).decode().split())
                self.assertEqual(b"", git("remote", root=repo))
                self.assertFalse((repo / ".git" / "objects" / "info" / "alternates").exists())
                self.assertFalse((repo / ".git" / "logs").exists())
                self.assertNotEqual(0, subprocess.run(
                    ["git", "-C", str(repo), "cat-file", "-e", source["CANDIDATE_SHA"]],
                    capture_output=True).returncode)
                self.assertEqual(task["base_sha"],
                                 git("rev-parse", "HEAD", root=repo).decode().strip())
                needles = {str(ROOT), str(ROOT.resolve())}
                for path in (repo / ".git").rglob("*"):
                    if path.is_file() and not path.is_symlink():
                        data = path.read_bytes()
                        for needle in needles:
                            self.assertNotIn(needle.encode(), data, path.as_posix())
            finally:
                if run.exists():
                    wrapper.cleanup(ROOT, run)
            self.assertFalse(run.exists())

    def test_stray_delivery_inside_repo_rolls_back_the_entire_allocation(self):
        wrapper = load("wrapper_delivery")
        real = wrapper.standalone_repository
        before = git("worktree", "list", "--porcelain")
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "contaminated"

            def contaminate(root, repo, base):
                real(root, repo, base)
                stray = run / "repo" / "nested" / "H2_RULES.md"
                stray.parent.mkdir()
                stray.write_text("stray\n")

            with mock.patch.object(wrapper, "standalone_repository", side_effect=contaminate):
                with self.assertRaisesRegex(ValueError, "DELIVERY_INSIDE_REPO"):
                    wrapper.prepare(ROOT, run, "f01", "variant", "HEAD")
            self.assertFalse(run.exists())
        self.assertEqual(before, git("worktree", "list", "--porcelain"))

    def test_ignored_stray_file_also_fails_closed(self):
        wrapper = load("wrapper_delivery")
        real = wrapper.standalone_repository
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "ignored"

            def contaminate(root, repo, base):
                real(root, repo, base)
                cache = run / "repo" / "__pycache__"
                cache.mkdir()
                (cache / "stray.pyc").write_bytes(b"stray")

            with mock.patch.object(wrapper, "standalone_repository", side_effect=contaminate):
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

    def test_run_root_outside_every_home_and_every_discoverable_ancestor(self):
        """F4: opencode walks UP from the cwd past the redirected HOME."""
        wrapper = load("wrapper_delivery")
        for marker in (".agents", ".opencode", ".claude", "AGENTS.md", "CLAUDE.md",
                       "opencode.json"):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as tmp:
                discovered = Path(tmp) / marker
                if marker.startswith("."):
                    discovered.mkdir()
                else:
                    discovered.write_text("# discovered guidance\n", encoding="utf-8")
                run = Path(tmp) / "runs" / "canary"
                with self.assertRaisesRegex(ValueError, "RUN_DIR_UNDER_DISCOVERABLE_ROOT"):
                    wrapper.prepare(ROOT, run, "f01", "control", "HEAD")
                self.assertFalse(run.exists())
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"HOME": home}):
                run = Path(home) / "runs" / "canary"
                with self.assertRaisesRegex(ValueError, "RUN_DIR_UNDER_OPERATOR_HOME"):
                    wrapper.prepare(ROOT, run, "f01", "control", "HEAD")
                self.assertFalse(run.exists())
        canary = load("isolation_canary")
        with tempfile.TemporaryDirectory() as tmp:
            discovered = Path(tmp) / ".agents"
            discovered.mkdir()
            with self.assertRaisesRegex(ValueError, "RUN_DIR_UNDER_DISCOVERABLE_ROOT"):
                canary.prepare(Path(tmp) / "canary")

    def test_a_clean_foreign_run_root_is_still_accepted(self):
        wrapper = load("wrapper_delivery")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "clean-root").mkdir()
            run = Path(tmp) / "clean-root" / "canary"
            try:
                receipt = wrapper.prepare(ROOT, run, "f01", "variant", "HEAD")
                self.assertEqual("f01", receipt["task_id"])
                self.assertEqual("variant", receipt["arm"])
            finally:
                if run.exists():
                    wrapper.cleanup(ROOT, run)
            self.assertFalse(run.exists())


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
    SOURCES_LINE = "H2_CANARY_SOURCES mcp=0 plugin_agents=0 skills=opencode,report"

    def fixture(self):
        return [
            {"type": "text", "part": {"text": "H2_CANARY_WRAPPER_STARTUP\n" + self.SOURCES_LINE}},
            {"type": "tool_use", "part": {"tool": "read", "state": {
                "input": {"filePath": "repo/probe.txt"}}}},
            {"type": "text", "part": {"text": "H2_CANARY_REPO_ATTACHED"}},
            {"type": "tool_use", "part": {"tool": "read", "state": {
                "input": {"filePath": "repo/nested/probe.txt"}}}},
            {"type": "text", "part": {"text": "H2_CANARY_NESTED_ATTACHED"}},
            {"type": "step_finish", "part": {"reason": "stop"}},
        ]

    def t12_stream(self):
        """The T12 fixture: a real 2.0.25 stream, sanitised; it carries no sources line."""
        return (FZ / "fixtures" / "isolation-canary-events.jsonl").read_text(encoding="utf-8")

    def live_stream(self):
        """F5's own evidence: the fresh 86ac104 live canary, sanitised, no sources line."""
        return (FZ / "fixtures" / "canary-86ac104-events.jsonl").read_text(encoding="utf-8")

    def passing_stream(self):
        """The clearly-labelled synthetic fixture: the live stream plus the sources line."""
        return (FZ / "fixtures" / "canary-86ac104-synthetic-sources-line.jsonl").read_text(
            encoding="utf-8")

    def passing_events(self):
        return [json.loads(line) for line in self.passing_stream().splitlines() if line.strip()]

    @staticmethod
    def render(events):
        return "\n".join(json.dumps(event) for event in events)

    def text_event(self, text):
        return {"type": "text", "part": {"type": "text", "text": text}}

    def read_event(self, path):
        return {"type": "tool_use", "part": {"type": "tool", "tool": "read", "state": {
            "status": "completed", "input": {"path": path}}}}

    def test_the_labelled_pass_fixture_passes_and_the_cli_agrees(self):
        """The committed pass fixture is synthetic: the live stream plus the sources line."""
        canary = load("isolation_canary")
        verdict = canary.check_stream(self.passing_stream())
        self.assertEqual("PASS", verdict["verdict"], verdict["reasons"])
        self.assertEqual(10, verdict["event_count"])
        self.assertEqual({"mcp": 0, "plugin_agents": 0, "skills": ["opencode", "report"]},
                         verdict["sources_line"])
        for key in ("wrapper_at_startup", "repo_after_first_read", "nested_after_read"):
            self.assertTrue(verdict[key])
        text = self.passing_stream()
        self.assertIn("<RUN_ROOT>", text)
        for host_prefix in ("/Users/", "/private/"):
            self.assertNotIn(host_prefix, text)
        events = self.passing_events()
        self.assertEqual({"step_start", "text", "tool_use", "step_finish"},
                         {event["type"] for event in events})
        reads = [event for event in events if event["type"] == "tool_use"]
        self.assertEqual({"repo/probe.txt", "repo/nested/probe.txt"},
                         {canary.normalise_path(event["part"]["state"]["input"]["path"], Path("."))
                          for event in reads})
        cli = subprocess.run(
            [sys.executable, str(FZ / "isolation_canary.py"), "check",
             str(FZ / "fixtures" / "canary-86ac104-synthetic-sources-line.jsonl")],
            capture_output=True, text=True)
        self.assertEqual(0, cli.returncode, cli.stdout)

    def test_both_real_streams_are_regressions_for_the_f5_false_positive(self):
        """F5: a correct live run must fail on the missing line, never on its own prose."""
        canary = load("isolation_canary")
        for label, stream in (("live 86ac104", self.live_stream()),
                              ("T12 fixture", self.t12_stream())):
            with self.subTest(label=label):
                verdict = canary.check_stream(stream)
                self.assertEqual("FAIL", verdict["verdict"])
                self.assertEqual(["NO_SOURCES_LINE"], verdict["reasons"], label)
                self.assertEqual(10, verdict["event_count"])
        self.assertIn("Actual MCP / plugin-agent / skill sources present:", self.live_stream())
        self.assertIn("Plugin agents: none present", self.live_stream())
        for stream in (self.live_stream(), self.t12_stream()):
            for host_prefix in ("/Users/", "/private/"):
                self.assertNotIn(host_prefix, stream)
        cli = subprocess.run(
            [sys.executable, str(FZ / "isolation_canary.py"), "check",
             str(FZ / "fixtures" / "canary-86ac104-events.jsonl")],
            capture_output=True, text=True)
        self.assertEqual(1, cli.returncode)
        self.assertEqual(["NO_SOURCES_LINE"], json.loads(cli.stdout)["reasons"])

    def test_each_real_schema_refusal_is_reported(self):
        canary = load("isolation_canary")
        base = self.passing_events()
        wrapper_index = 1
        first_read = 2
        repo_text = 5

        def with_line(old, new):
            events = json.loads(json.dumps(base))
            text = events[wrapper_index]["part"]["text"]
            self.assertIn(old, text)
            events[wrapper_index]["part"]["text"] = text.replace(old, new)
            return self.render(events)

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
            "non-read tool": (self.render(
                base[:first_read] + [{"type": "tool_use", "part": {
                    "type": "tool", "tool": "bash"}}] + base[first_read:]),
                "FORBIDDEN_TOOL_OR_AGENT"),
            "truncated stream": (self.render(base[:-1]), "INCOMPLETE_STREAM"),
            "sources line missing": (with_line(self.SOURCES_LINE + "\n\n", ""),
                                     "NO_SOURCES_LINE"),
            "sources line malformed": (with_line(
                self.SOURCES_LINE, "H2_CANARY_SOURCES mcp=none plugin_agents=0 skills="),
                "NO_SOURCES_LINE"),
            "mcp reported": (with_line("mcp=0", "mcp=2"), "MCP_CONTAMINATION"),
            "plugin agent reported": (with_line("plugin_agents=0", "plugin_agents=1"),
                                      "PLUGIN_AGENT_CONTAMINATION"),
            "skill catalogue reported": (with_line(
                "skills=opencode,report", "skills=opencode,report,alpha-skill"),
                "SKILL_CATALOGUE_CONTAMINATION"),
        }
        for label, (stream, reason) in mutants.items():
            with self.subTest(label=label):
                verdict = canary.check_stream(stream)
                self.assertEqual("FAIL", verdict["verdict"], label)
                self.assertIn(reason, verdict["reasons"], verdict["reasons"])

    def test_the_f4_home_run_fails_on_the_disclosed_skill_catalogue(self):
        """F4's observable claim, now carried by the machine-readable line only (F5)."""
        canary = load("isolation_canary")
        stream = self.passing_stream().replace("skills=opencode,report",
                                               "skills=opencode,report,alpha-skill,beta-skill")
        verdict = canary.check_stream(stream)
        self.assertEqual("FAIL", verdict["verdict"])
        self.assertIn("SKILL_CATALOGUE_CONTAMINATION", verdict["reasons"])
        self.assertEqual(["SKILL_CATALOGUE_CONTAMINATION"], verdict["reasons"])

    def test_free_prose_no_longer_decides_the_three_claims(self):
        """F5: wording changes every run, so prose is not the instrument — the line is."""
        canary = load("isolation_canary")
        stream = self.render(self.passing_events() + [
            self.text_event("MCP servers: every one of them is configured and present."),
            self.text_event("Plugin agents: reviewer, and two more."),
            self.text_event("Skills: `alpha-skill`, `beta-skill` are present.")])
        self.assertEqual("PASS", canary.check_stream(stream)["verdict"])

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
            wrapper = (run / "AGENTS.md").read_text()
            self.assertIn("H2_CANARY_WRAPPER_STARTUP", wrapper)
            self.assertIn("H2_CANARY_SOURCES mcp=<integer> plugin_agents=<integer> "
                          "skills=<comma-separated names>", wrapper)
            for rel, token in (("AGENTS.md", "H2_CANARY_WRAPPER_STARTUP"),
                               ("repo/AGENTS.md", "H2_CANARY_REPO_ATTACHED"),
                               ("repo/nested/AGENTS.md", "H2_CANARY_NESTED_ATTACHED")):
                self.assertIn(token, (run / rel).read_text())
            self.assertEqual(b"", git("status", "--porcelain", root=run / "repo"))


class IsolationPreflight(unittest.TestCase):
    """F5: the deterministic profile attestation, parsed from sanitised real output."""

    def paths_text(self):
        return (FZ / "fixtures" / "preflight-debug-paths.txt").read_text(encoding="utf-8")

    def config_text(self):
        return (FZ / "fixtures" / "preflight-debug-config.json").read_text(encoding="utf-8")

    def evaluate(self, paths=None, config=None, *, template=b"template\n", config_file=b"template\n"):
        return load("isolation_canary").evaluate_preflight(
            self.paths_text() if paths is None else paths,
            self.config_text() if config is None else config,
            profile_home="<PROFILE_HOME>", template=template, config_file=config_file)

    def test_the_sanitised_profile_evidence_passes(self):
        verdict = self.evaluate()
        self.assertEqual("PASS", verdict["verdict"], verdict["reasons"])
        self.assertEqual("<PROFILE_HOME>", verdict["paths"]["home"])
        self.assertEqual([{"type": "document",
                           "path": "<PROFILE_HOME>/.config/opencode/opencode.json"},
                          {"type": "directory",
                           "path": "<PROFILE_HOME>/.config/opencode"}],
                         verdict["config_sources"])
        self.assertEqual(verdict["template_sha256"], verdict["config_file_sha256"])
        for stream in (self.paths_text(), self.config_text()):
            for host_prefix in ("/Users/", "/private/"):
                self.assertNotIn(host_prefix, stream)

    def test_the_profile_env_file_is_parsed_not_executed(self):
        canary = load("isolation_canary")
        self.assertEqual({"HOME": "/profile/isolated", "XDG_CONFIG_HOME": "/profile/isolated/.config"},
                         canary.parse_profile_env("# comment\nexport HOME=/profile/isolated\n"
                                                  'XDG_CONFIG_HOME="/profile/isolated/.config"\n'
                                                  "not-an-assignment\n"))

    def test_a_state_path_outside_the_profile_is_refused(self):
        paths = self.paths_text()
        cases = {
            "PREFLIGHT_PATH_OUTSIDE_PROFILE:cache": paths.replace(
                "cache      <PROFILE_HOME>", "cache      <OTHER_HOME>"),
            "PREFLIGHT_PATH_OUTSIDE_PROFILE:data": paths.replace(
                "data       <PROFILE_HOME>/.local/share/opencode",
                "data       /srv/shared/opencode"),
            "PREFLIGHT_PATH_MISSING:state": "".join(
                line for line in paths.splitlines(keepends=True)
                if not line.startswith("state ")),
            "PREFLIGHT_HOME_MISMATCH": paths.replace("home       <PROFILE_HOME>",
                                                     "home       <OTHER_HOME>"),
            "PREFLIGHT_UNKNOWN_PATH_KEY:project": paths
            + "project    <PROFILE_HOME>/project\n",
            "PREFLIGHT_TMP_NOT_ABSOLUTE": paths.replace("tmp        <OS_TMPDIR>/opencode",
                                                        "tmp        opencode"),
            "PREFLIGHT_UNPARSEABLE_PATHS": "\n\n",
        }
        for reason, mutated in cases.items():
            with self.subTest(reason=reason):
                self.assertIn(reason, self.evaluate(paths=mutated)["reasons"])

    def test_extra_or_missing_config_sources_are_refused(self):
        sources = json.loads(self.config_text())
        for label, mutated in (
            ("extra project source", sources + [
                {"type": "document", "path": "<PROFILE_HOME>/project/opencode.json"}]),
            ("extra global source", [{"type": "document",
                                      "path": "<GLOBAL_CONFIG>/opencode.json"}] + sources),
            ("directory source dropped", sources[:1]),
            ("nothing loaded", []),
        ):
            with self.subTest(label=label):
                self.assertIn("CONFIG_SOURCES_MISMATCH",
                              self.evaluate(config=json.dumps(mutated))["reasons"])
        self.assertIn("PREFLIGHT_UNPARSEABLE_CONFIG", self.evaluate(config='{"type":')["reasons"])

    def test_template_and_file_drift_are_refused(self):
        self.assertIn("CONFIG_TEMPLATE_MISMATCH",
                      self.evaluate(template=b"frozen\n", config_file=b"edited\n")["reasons"])
        self.assertIn("PREFLIGHT_CONFIG_UNREADABLE", self.evaluate(config_file=None)["reasons"])
        self.assertIn("PREFLIGHT_TEMPLATE_UNAVAILABLE", self.evaluate(template=None)["reasons"])

    def test_preflight_attests_the_profile_and_writes_the_verdict(self):
        canary = load("isolation_canary")
        template = canary.CONFIG_TEMPLATE.read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / "profile" / "isolated"
            (home / ".config" / "opencode").mkdir(parents=True)
            (home / ".config" / "opencode" / "opencode.json").write_bytes(template)
            env_file = root / "env.sh"
            env_file.write_text(f"# synthetic\nexport HOME={home}\n"
                                f"export XDG_CONFIG_HOME={home}/.config\n", encoding="utf-8")
            run = root / "run"
            run.mkdir()
            outputs = {
                "paths": self.paths_text().replace("<PROFILE_HOME>", str(home))
                                          .replace("<OS_TMPDIR>", "/synthetic-tmp"),
                "config": self.config_text().replace("<PROFILE_HOME>", str(home)),
            }
            calls = []

            def fake_run(argv, cwd, env, timeout=120):
                calls.append((list(argv), Path(cwd), dict(env)))
                return 0, outputs[argv[-1]]

            with mock.patch.object(canary, "run_command", side_effect=fake_run):
                verdict = canary.preflight(run, env_file)
            self.assertEqual("PASS", verdict["verdict"], verdict["reasons"])
            self.assertEqual(verdict, json.loads((run / "preflight.json").read_text()))
            self.assertEqual([["opencode", "debug", "paths"],
                              ["opencode", "debug", "config"]], [call[0] for call in calls])
            for argv, cwd, env in calls:
                self.assertEqual(run.resolve(), cwd)
                self.assertEqual(str(home), env["HOME"])
                self.assertNotIn("run", argv)
            self.assertEqual(str(home), verdict["paths"]["home"])
            self.assertEqual(digest(template), verdict["template_sha256"])

            def failing_run(argv, cwd, env, timeout=120):
                return 1, ""

            with mock.patch.object(canary, "run_command", side_effect=failing_run):
                failed = canary.preflight(run, env_file)
            self.assertEqual("FAIL", failed["verdict"])
            self.assertIn("PREFLIGHT_COMMAND_FAILED:paths", failed["reasons"])
            self.assertEqual(failed, json.loads((run / "preflight.json").read_text()))

    def test_preflight_cli_exits_nonzero_without_a_profile_env(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            result = subprocess.run(
                [sys.executable, str(FZ / "isolation_canary.py"), "preflight", str(run),
                 "--profile-env", str(Path(tmp) / "missing.sh")],
                capture_output=True, text=True)
            self.assertEqual(1, result.returncode)
            verdict = json.loads((run / "preflight.json").read_text())
            self.assertIn("PREFLIGHT_PROFILE_ENV_UNREADABLE", verdict["reasons"])

    def test_preflight_refuses_a_missing_run_dir(self):
        canary = load("isolation_canary")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                canary.preflight(Path(tmp) / "absent", Path(tmp) / "env.sh")


class FrozenWorkerProfile(unittest.TestCase):
    """F6: the profile config is an experimental input, so it is frozen and checked."""

    def test_template_is_the_documented_profile_config(self):
        raw = (FZ / "worker-profile" / "opencode.json").read_bytes()
        config = json.loads(raw)
        self.assertEqual({"$schema", "autoupdate", "share", "plugin", "mcp", "permission"},
                         set(config))
        self.assertEqual("https://opencode.ai/config.json", config["$schema"])
        self.assertIs(False, config["autoupdate"])
        self.assertEqual("disabled", config["share"])
        self.assertEqual([], config["plugin"])
        self.assertEqual({}, config["mcp"])
        self.assertEqual({"question": "deny"}, config["permission"])
        self.assertTrue(raw.endswith(b"\n"))
        canary = load("isolation_canary")
        self.assertEqual(FZ / "worker-profile" / "opencode.json", canary.CONFIG_TEMPLATE)
        verdict = canary.evaluate_preflight(
            (FZ / "fixtures" / "preflight-debug-paths.txt").read_text(encoding="utf-8"),
            (FZ / "fixtures" / "preflight-debug-config.json").read_text(encoding="utf-8"),
            profile_home="<PROFILE_HOME>", template=raw, config_file=raw)
        self.assertEqual("PASS", verdict["verdict"], verdict["reasons"])
        self.assertEqual(digest(raw), verdict["template_sha256"])


class AccessAudit(unittest.TestCase):
    """T22 / F9: out-of-run access read back out of the run's own event stream.

    T24 / F10-F13: the fixtures that imitate opencode are the REAL recorded streams, sanitised with
    placeholder path prefixes; the parser is exercised on them and on mutations of them, never on
    an imagined stream (that is how `bash` slipped into the allow-list).
    """

    PILOT = "pilot-f01-c-events.jsonl"
    PROBE = "toolname-probe-events.jsonl"
    RUN = Path("/srv/runs/h2r2-f01-c")
    HOME = "/srv/profile-home"

    def events(self, *items):
        return "\n".join(json.dumps(item) for item in items)

    def tool(self, name, **inputs):
        return {"type": "tool_use", "part": {"tool": name, "state": {"input": inputs}}}

    def bash(self, command):
        return self.tool("bash", command=command)

    def expand(self, name, run=None, home=None):
        """The committed stream with its placeholder prefixes re-expanded for one synthetic run."""
        text = (FZ / "fixtures" / name).read_text(encoding="utf-8")
        values = {"<RUN_ROOT>": str(run or self.RUN), "<PY>": sys.executable, "<TMP>": "/tmp",
                  "<PY_ROOT>": "/srv/py-root", "<HOME>": home or self.HOME}
        for placeholder, value in values.items():
            text = text.replace(placeholder, value)
        return text

    def fixture_events(self, name):
        return [json.loads(line) for line in
                (FZ / "fixtures" / name).read_text(encoding="utf-8").splitlines() if line.strip()]

    def fixture_tools(self, name):
        return {event["part"].get("tool") for event in self.fixture_events(name)
                if event.get("type") == "tool_use"}

    def audit_text(self, text, run=None, home=None):
        module = load("access_audit")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(text, encoding="utf-8")
            return module.audit(path, run or self.RUN, home=home or self.HOME,
                                python=sys.executable)

    def mutate(self, events, tool, **inputs):
        """The first real `tool` call of the stream, with its recorded inputs replaced."""
        for index, event in enumerate(events):
            if event.get("type") != "tool_use" or event["part"].get("tool") != tool:
                continue
            part = json.loads(json.dumps(event["part"]))
            part["state"]["input"] = inputs
            return [*events[:index], {**event, "part": part}, *events[index + 1:]]
        raise AssertionError(f"no {tool} call in the recorded stream")

    def rename(self, events, tool, new_name):
        for index, event in enumerate(events):
            if event.get("type") == "tool_use" and event["part"].get("tool") == tool:
                part = json.loads(json.dumps(event["part"]))
                part["tool"] = new_name
                return [*events[:index], {**event, "part": part}, *events[index + 1:]]
        raise AssertionError(f"no {tool} call in the recorded stream")

    def one(self, *events, home=None, run=None):
        module = load("access_audit")
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(run) if run is not None else Path(tmp) / "run"
            if run is None:
                run_dir.mkdir()
            path = Path(tmp) / "events.jsonl"
            path.write_text(self.events(*events), encoding="utf-8")
            return module.audit(path, run_dir, home=home, python=sys.executable)

    def test_the_committed_clean_stream_passes_and_the_cli_agrees(self):
        module = load("access_audit")
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            result = module.audit(FZ / "fixtures" / "access-audit-clean.jsonl", run,
                                  python=sys.executable)
            self.assertEqual("PASS", result["verdict"], result["hits"])
            self.assertEqual(7, result["tool_calls"])
            self.assertEqual([], result["hits"])
            cli = subprocess.run(
                [sys.executable, str(FZ / "access_audit.py"),
                 str(FZ / "fixtures" / "access-audit-clean.jsonl"),
                 "--run-dir", str(run), "--python", sys.executable],
                capture_output=True, text=True)
            self.assertEqual(0, cli.returncode, cli.stdout)
            written = json.loads((run / "access-audit.json").read_text())
            self.assertEqual("PASS", written["verdict"])
            self.assertEqual([], written["hits"])

    def test_the_committed_hit_stream_is_invalid_and_the_cli_agrees(self):
        module = load("access_audit")
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            result = module.audit(FZ / "fixtures" / "access-audit-hits.jsonl", run,
                                  python=sys.executable)
            self.assertEqual("INVALID", result["verdict"])
            self.assertEqual(["PATH_OUTSIDE_RUN", "PATH_OUTSIDE_RUN", "GIT_REMOTE_REPOSITORY",
                              "TOOL_NOT_ALLOWED"],
                             [hit["reason"] for hit in result["hits"]])
            self.assertEqual("/etc/hosts", result["hits"][0]["value"])
            self.assertEqual("cat ../../../etc/hosts", result["hits"][1]["value"])
            self.assertEqual("webfetch", result["hits"][-1]["value"])
            cli = subprocess.run(
                [sys.executable, str(FZ / "access_audit.py"),
                 str(FZ / "fixtures" / "access-audit-hits.jsonl"),
                 "--run-dir", str(run), "--python", sys.executable],
                capture_output=True, text=True)
            self.assertEqual(1, cli.returncode, cli.stdout)
            self.assertEqual("INVALID",
                             json.loads((run / "access-audit.json").read_text())["verdict"])

    def test_each_flagged_shape_is_a_hit(self):
        cases = (
            ("absolute read", self.tool("read", path="/etc/hosts"), "PATH_OUTSIDE_RUN"),
            ("parent escape", self.bash("cat ../../../etc/hosts"), "PATH_OUTSIDE_RUN"),
            ("flag value", self.bash("python x.py --out=/etc/passwd"), "PATH_OUTSIDE_RUN"),
            ("git clone", self.bash("git clone /tmp/other copy"), "GIT_REMOTE_REPOSITORY"),
            ("git fetch", self.bash("git fetch --depth 1 /tmp/x"), "GIT_REMOTE_REPOSITORY"),
            ("git remote add", self.bash("git remote add origin /tmp/x"),
             "GIT_REMOTE_REPOSITORY"),
            ("git -C outside", self.bash("git -C /srv/other log"), "GIT_FOREIGN_REPOSITORY"),
            ("git --git-dir outside", self.bash("git --git-dir=/srv/other/.git log"),
             "GIT_FOREIGN_REPOSITORY"),
            ("unlisted tool", self.tool("webfetch", url="https://example.invalid/"),
             "TOOL_NOT_ALLOWED"),
            ("patch escape", self.tool("patch", patchText="--- a/x.py\n+++ b/../../../etc/y.py\n"),
             "PATH_OUTSIDE_RUN"),
        )
        for label, event, reason in cases:
            with self.subTest(label=label):
                result = self.one(event)
                self.assertEqual("INVALID", result["verdict"], label)
                self.assertIn(reason, [hit["reason"] for hit in result["hits"]], label)

    def test_the_recorded_pilot_stream_passes_the_access_audit(self):
        """F10: `shell` is the real tool name, so a real clean run must audit as PASS."""
        result = self.audit_text(self.expand(self.PILOT))
        self.assertEqual("PASS", result["verdict"], result["hits"])
        self.assertEqual([], result["hits"])
        self.assertEqual(155, result["events"])
        self.assertEqual(50, result["tool_calls"])
        self.assertEqual({"read", "write", "edit", "shell"}, self.fixture_tools(self.PILOT))
        self.assertNotIn("bash", self.fixture_tools(self.PILOT))

    def test_the_recorded_tool_name_probe_shows_every_real_tool(self):
        """F10: the live probe used each of the six tools once; every one is allowed."""
        tools = self.fixture_tools(self.PROBE)
        self.assertEqual({"read", "glob", "grep", "shell", "write", "edit"}, tools)
        result = self.audit_text(self.expand(self.PROBE))
        self.assertEqual("PASS", result["verdict"], result["hits"])
        self.assertEqual(6, result["tool_calls"])

    def test_every_mutation_of_the_recorded_pilot_stream_is_invalid(self):
        """A clean fixture must stay a real control: each escape shape makes it INVALID."""
        pilot = self.fixture_events(self.PILOT)
        cases = (
            ("read outside the run",
             self.mutate(pilot, "read", path="/etc/hosts"), "PATH_OUTSIDE_RUN"),
            ("git -C another repository",
             self.mutate(pilot, "shell", command="git -C /srv/other log --oneline"),
             "GIT_FOREIGN_REPOSITORY"),
            ("cat ~/x",
             self.mutate(pilot, "shell", command="cat ~/notes.txt"), "PATH_OUTSIDE_RUN"),
            ("a ../ escape",
             self.mutate(pilot, "shell", command="cat ../../../etc/passwd"), "PATH_OUTSIDE_RUN"),
            ("a tool outside the allow-list",
             self.rename(pilot, "read", "webfetch"), "TOOL_NOT_ALLOWED"),
        )
        for label, events, reason in cases:
            with self.subTest(label=label):
                result = self.audit_text(self.events(*events))
                self.assertEqual("INVALID", result["verdict"], label)
                self.assertIn(reason, [hit["reason"] for hit in result["hits"]], label)

    def test_shell_punctuation_and_the_effective_git_repository(self):
        """F12: separators are tokens. F13: git is judged by its effective repository."""
        run = self.RUN
        for label, command in (
            ("separator glued to a path",
             f"cd {run}/repo && source /dev/null; {sys.executable} -m unittest "
             "scripts.tests.test_x.SomeTests.test_y"),
            ("temp archive pipeline",
             f"cd {run} && rm -rf /tmp/h2-base-check && mkdir -p /tmp/h2-base-check && "
             "git -C repo archive HEAD | tar -x -C /tmp/h2-base-check && "
             f"cd /tmp/h2-base-check && {sys.executable} -m unittest adapters.zcode.tests.test_x"),
            ("git in a temp repository", "git -C /tmp/scratch log --oneline"),
            ("git after cd into a temp directory", "cd /tmp/scratch && git log --oneline"),
        ):
            with self.subTest(label=label):
                result = self.one(self.tool("shell", command=command), run=run,
                                  home=self.HOME)
                self.assertEqual("PASS", result["verdict"], result["hits"])
        for label, command, reason in (
            ("git -C another repository", "git -C /srv/other log --oneline",
             "GIT_FOREIGN_REPOSITORY"),
            ("git after cd into another repository", "cd /srv/other && git log --oneline",
             "GIT_FOREIGN_REPOSITORY"),
            ("another program's -C outside the run",
             f"cd {run} && git -C repo archive HEAD | tar -x -C /srv/other", "PATH_OUTSIDE_RUN"),
        ):
            with self.subTest(label=label):
                result = self.one(self.tool("shell", command=command), run=run,
                                  home=self.HOME)
                self.assertEqual("INVALID", result["verdict"], label)
                self.assertIn(reason, [hit["reason"] for hit in result["hits"]], label)

    def test_home_and_relative_shapes_resolve_against_the_profile(self):
        module = load("access_audit")
        allow = module.allowed_roots(sys.executable)
        run = Path("/srv/runs/h2r2-f01-c")
        profile = "/srv/profile"
        for value in ("~/.ssh/id_rsa", "~/notes", "$HOME/notes", "${HOME}/notes",
                      "../other/report.md"):
            self.assertEqual("PATH_OUTSIDE_RUN",
                             module.path_reason(value, run, profile, allow), value)
        self.assertIsNone(module.path_reason("repo/scripts/x.py", run, profile, allow))
        self.assertEqual("PATH_HOME_UNRESOLVED", module.path_reason("~/x", run, None, allow))

    def test_allow_listed_test_runs_and_temp_paths_pass(self):
        module = load("access_audit")
        allow = module.allowed_roots(sys.executable)
        run = Path("/srv/runs/h2r2-f01-c")
        for value in (str(Path(sys.executable).resolve()), "/usr/bin/env", "/bin/sh",
                      "/tmp/scratch/x", "/dev/null"):
            self.assertIsNone(module.path_reason(value, run, "/srv/profile", allow), value)
        result = self.one(self.bash(f"{sys.executable} -s -m unittest discover -s scripts/tests"),
                          self.bash("cd repo && git -C repo status --porcelain"),
                          self.bash("python -m compileall -q scripts 2> /dev/null"))
        self.assertEqual("PASS", result["verdict"], result["hits"])
        self.assertEqual(3, result["tool_calls"])

    def test_a_missing_stream_or_a_malformed_line_fails_closed(self):
        module = load("access_audit")
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "run"
            run.mkdir()
            missing = module.audit(Path(tmp) / "absent.jsonl", run, python=sys.executable)
            self.assertEqual("INVALID", missing["verdict"])
            self.assertEqual("MISSING_EVENT_STREAM", missing["hits"][0]["reason"])
            path = Path(tmp) / "events.jsonl"
            path.write_text('{"type": "tool_use"\n', encoding="utf-8")
            broken = module.audit(path, run, python=sys.executable)
            self.assertEqual("INVALID", broken["verdict"])
            self.assertEqual("MALFORMED_EVENT_LINE", broken["hits"][0]["reason"])


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

    def test_profile_template_and_wall_clock_limit_are_pinned_in_the_authority_text(self):
        protocol = (FZ / "protocol-v2.md").read_text()
        readme = (FZ / "README.md").read_text()
        for text in (protocol, readme):
            self.assertIn("worker-profile/opencode.json", text)
            self.assertIn("permission.question", text)
            self.assertIn("preflight", text)
            self.assertIn("90", text)
        self.assertIn("不静默重跑", protocol)
        self.assertIn("INVALID", protocol)

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


STUB_WORKER = '''"""Test-only stub worker: never a model, never a network call.

It leaves exactly the artefacts a run needs and nothing else, so the driver's steps, its
verdict and its registry line can be exercised end to end without a worker.
"""
import json
import subprocess
import sys
import time

MODE = "__MODE__"
PATCH = "__PATCH__"

if MODE == "accept":
    subprocess.run(["git", "-C", "repo", "apply", "--whitespace=nowarn", PATCH], check=True)
if MODE in ("accept", "noop", "escape"):
    open("report.md", "w").write("# report\\n\\nstub filler\\n")
    open(".h2-telemetry.log", "w").write("READ FULL repo/RULES.md\\n")
    if MODE == "escape":
        print(json.dumps({"type": "tool_use", "sessionID": "ses_stub",
                          "part": {"tool": "read",
                                   "state": {"status": "completed",
                                             "input": {"path": "/etc/hosts"}}}}))
    print(json.dumps({"type": "text", "sessionID": "ses_stub", "part": {"text": "stub done"}}))
elif MODE == "timeout":
    print(json.dumps({"type": "step_start", "sessionID": "ses_stub"}))
    sys.stdout.flush()
    time.sleep(30)
else:
    print(json.dumps({"type": "error", "sessionID": "ses_stub", "part": {"text": "stub"}}))
'''


def profile_env_file(directory):
    """A profile env file for tests: an export block, never the operator's real one."""
    path = Path(directory) / "profile-env.sh"
    path.write_text(f"export PATH={os.environ.get('PATH', '/usr/bin:/bin')}\nexport LANG=C\n",
                    encoding="utf-8")
    return path


def stub_worker(directory, mode, patch=None):
    path = Path(directory) / f"stub-{mode}.py"
    path.write_text(STUB_WORKER.replace("__MODE__", mode).replace("__PATCH__", str(patch or "")),
                    encoding="utf-8")
    return path


def candidate_patch(directory, task):
    """The historical candidate's NON-TEST delta: what a successful worker leaves in repo/."""
    _, source = task_pair(task["task_id"])
    path = Path(directory) / "delta.patch"
    path.write_bytes(git("diff", "--binary", task["base_sha"], source["CANDIDATE_SHA"],
                         "--", ":!scripts/tests"))
    return path


def passing_preflight(run_dir, env_file):
    return {"verdict": "PASS", "reasons": []}


def stub_auditor(verdict="PASS"):
    def audit(run_dir, plan_run, task, *, launch, command, env, limit_seconds):
        audit_dir = Path(run_dir) / "audit"
        audit_dir.mkdir()
        (audit_dir / "audit.json").write_text(json.dumps(
            {"correctness": verdict, "invalid_completion": False, "findings": [],
             "notes": "stub auditor"}), encoding="utf-8")
        return {"verdict": verdict, "reasons": [], "leakage": []}
    return audit


def execute_stub(tmp, mode="noop", *, auditor=None, preflight=None, limit_seconds=None):
    driver = load("run_h2r2")
    task, _ = task_pair("f01")
    patch = candidate_patch(tmp, task) if mode == "accept" else None
    runs = Path(tmp) / "runs"
    result = driver.execute("h2r2-f01-c", runs,
                            worker_command=(sys.executable, str(stub_worker(tmp, mode, patch))),
                            preflight=preflight or passing_preflight,
                            auditor=auditor or stub_auditor(),
                            profile_env=profile_env_file(tmp),
                            limit_seconds=limit_seconds)
    return driver, runs, result


class RunDriver(unittest.TestCase):
    """T18: the only way a run is executed, driven by a stub worker (never a model)."""

    def test_the_launchable_facts_are_frozen_and_the_cli_exposes_no_replacement(self):
        driver = load("run_h2r2")
        self.assertEqual(("opencode", "run", "--standalone", "--auto", "--format", "json", "-m"),
                         driver.WORKER_COMMAND)
        self.assertEqual("Read ./CONTRACT.md and do what it asks.", driver.LAUNCH_PROMPT)
        self.assertEqual(("PATH", "LANG"), driver.ENV_ALLOW)
        self.assertEqual(90 * 60, driver.WALL_CLOCK_LIMIT_SECONDS)
        help_text = subprocess.run([sys.executable, str(FZ / "run_h2r2.py"), "run", "--help"],
                                   capture_output=True, text=True).stdout
        options = {token for token in help_text.split() if token.startswith("--")}
        self.assertEqual({"--runs-root", "--help"}, options)

    def test_the_frozen_env_is_exactly_what_the_worker_and_the_auditor_receive(self):
        """F11: PYTHONDONTWRITEBYTECODE=1, and nothing beyond PATH/LANG/the profile exports."""
        driver = load("run_h2r2")
        canary = load("isolation_canary")
        self.assertEqual({"PYTHONDONTWRITEBYTECODE": "1"}, driver.FROZEN_ENV)
        with tempfile.TemporaryDirectory() as tmp:
            env_file = profile_env_file(tmp)
            exports = canary.parse_profile_env(env_file.read_text(encoding="utf-8"))
            allowed = {"PATH", "LANG", "PYTHONDONTWRITEBYTECODE"} | set(exports)
            expected = driver.worker_env(env_file)
            self.assertEqual("1", expected["PYTHONDONTWRITEBYTECODE"])
            self.assertEqual(set(), set(expected) - allowed)
            captured = {}
            real_launch = driver.launch

            def recording_launch(argv, cwd, env, limit, stdout_path, stderr_path):
                captured.setdefault("worker", dict(env))
                return real_launch(argv, cwd, env, limit, stdout_path, stderr_path)

            def recording_auditor(run_dir, plan_run, task, *, launch, command, env,
                                  limit_seconds):
                captured["auditor"] = dict(env)
                return stub_auditor()(run_dir, plan_run, task, launch=launch,
                                      command=command, env=env, limit_seconds=limit_seconds)

            runs = Path(tmp) / "runs"
            with mock.patch.object(driver, "launch", recording_launch):
                result = driver.execute(
                    "h2r2-f01-c", runs,
                    worker_command=(sys.executable, str(stub_worker(tmp, "noop"))),
                    preflight=passing_preflight, auditor=recording_auditor,
                    profile_env=env_file)
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("REJECT", result["verdict"], result["reasons"])
                self.assertEqual(expected, captured["worker"])
                self.assertEqual(expected, captured["auditor"])
            finally:
                cleanup_run(run_dir)

    def test_the_candidate_delta_is_accepted_end_to_end_with_every_artefact_hashed(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver, runs, result = execute_stub(tmp, "accept")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("EXECUTED", result["outcome"])
                self.assertEqual("ACCEPT", result["verdict"], result["reasons"])
                self.assertEqual("PASS", result["audit_verdict"])
                self.assertEqual("ACCEPT", result["final_verdict"])
                self.assertEqual("ses_stub", result["session_id"])
                record = json.loads((run_dir / "run.json").read_text())
                self.assertEqual([("prepare", "DONE"), ("preflight", "PASS"), ("brief", "DONE"),
                                  ("worker", "DONE"), ("access_audit", "PASS"),
                                  ("acceptance", "ACCEPT"), ("audit", "PASS"),
                                  ("registry", "DONE")],
                                 [(step["step"], step["status"]) for step in record["steps"]])
                for step in record["steps"]:
                    self.assertTrue(step["started_at"], step["step"])
                    self.assertTrue(step["finished_at"], step["step"])
                self.assertEqual(90 * 60, record["limit_seconds"])
                self.assertEqual(driver.LAUNCH_PROMPT, record["launch_prompt"])
                self.assertEqual("ACCEPT",
                                 json.loads((run_dir / "verdict.json").read_text())["verdict"])
                self.assertTrue((run_dir / "CONTRACT.md").is_file())
                self.assertTrue((run_dir / "worker-report-template.md").is_file())
                line = json.loads((runs / "registry-v2.jsonl").read_text().splitlines()[0])
                self.assertEqual(("h2r2-f01-c", "f01", "control", "ACCEPT", "PASS", "ACCEPT"),
                                 (line["run_id"], line["task_id"], line["arm"], line["verdict"],
                                  line["audit_verdict"], line["final_verdict"]))
                self.assertEqual("ses_stub", line["session_id"])
                self.assertGreater(line["wall_clock_seconds"], 0)
                files = {path.relative_to(run_dir).as_posix() for path in run_dir.rglob("*")
                         if path.is_file() and path.relative_to(run_dir).parts[0] != "repo"}
                self.assertEqual(files, set(line["artifacts"]))
                for rel, value in line["artifacts"].items():
                    self.assertEqual(value, digest((run_dir / rel).read_bytes()), rel)
                self.assertEqual("h2r2-f01-v", driver.next_run_id(runs))
                state = driver.status(runs)
                self.assertEqual("REGISTERED", state["runs"][0]["state"])
                self.assertEqual("h2r2-f01-v", state["next"])
            finally:
                cleanup_run(run_dir)

    def test_a_stub_worker_that_does_nothing_is_rejected_even_with_a_passing_audit(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "noop", auditor=stub_auditor("FAIL"))
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("REJECT", result["verdict"])
                self.assertEqual("FAIL", result["audit_verdict"])
                self.assertEqual("REJECT", result["final_verdict"])
                self.assertIn("WORKER_NOT_PASSING:RESOLVED", result["reasons"])
            finally:
                cleanup_run(run_dir)

    def test_a_stub_worker_past_the_shortened_limit_is_invalid_timeout(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "timeout", limit_seconds=1)
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("INVALID", result["verdict"])
                self.assertEqual(["TIMEOUT"], result["reasons"])
                self.assertEqual("SKIPPED", result["audit_verdict"])
                record = json.loads((run_dir / "run.json").read_text())
                worker = next(step for step in record["steps"] if step["step"] == "worker")
                self.assertTrue(worker["timed_out"])
                self.assertEqual("INVALID", worker["status"])
                self.assertEqual(1, record["limit_seconds"])
                self.assertEqual("INVALID",
                                 json.loads((run_dir / "verdict.json").read_text())["verdict"])
                self.assertLess(result["wall_clock_seconds"], 60)
            finally:
                cleanup_run(run_dir)

    def test_a_stub_worker_error_event_is_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "error")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("INVALID", result["verdict"])
                self.assertEqual(["WORKER_ERROR_EVENT"], result["reasons"])
                self.assertEqual("SKIPPED", result["audit_verdict"])
                self.assertEqual("ses_stub", result["session_id"])
            finally:
                cleanup_run(run_dir)

    def test_out_of_run_access_is_invalid_registered_and_never_re_run(self):
        """F9: the events already record the access; a hit is terminal and cannot be re-run."""
        with tempfile.TemporaryDirectory() as tmp:
            driver, runs, result = execute_stub(tmp, "escape")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("INVALID", result["verdict"])
                self.assertEqual("INVALID", result["final_verdict"])
                self.assertIn("OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:/etc/hosts",
                              result["reasons"])
                audit = json.loads((run_dir / "access-audit.json").read_text())
                self.assertEqual("INVALID", audit["verdict"])
                self.assertEqual(1, audit["tool_calls"])
                self.assertEqual([{"event": 1, "tool": "read", "reason": "PATH_OUTSIDE_RUN",
                                   "value": "/etc/hosts"}], audit["hits"])
                record = json.loads((run_dir / "run.json").read_text())
                step = next(item for item in record["steps"]
                            if item["step"] == "access_audit")
                self.assertEqual("INVALID", step["status"])
                self.assertEqual(1, step["hits"])
                line = json.loads((runs / "registry-v2.jsonl").read_text().splitlines()[0])
                self.assertEqual("INVALID", line["verdict"])
                self.assertIn("OUT_OF_RUN_ACCESS", line["reason"])
                again = driver.execute("h2r2-f01-c", runs,
                                       profile_env=profile_env_file(tmp))
                self.assertEqual("RUN_ALREADY_REGISTERED", again["reason"])
            finally:
                cleanup_run(run_dir)

    def test_plan_order_and_every_second_start_are_refused(self):
        driver = load("run_h2r2")
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            refused = driver.execute("h2r2-f01-v", runs, profile_env=profile_env_file(tmp))
            self.assertEqual({"outcome": "REFUSED", "run_id": "h2r2-f01-v",
                              "reason": "PREDECESSOR_NOT_REGISTERED:h2r2-f01-c"}, refused)
            self.assertFalse((runs / "h2r2-f01-v").exists())
            self.assertFalse((runs / "registry-v2.jsonl").exists())
            self.assertEqual("h2r2-f01-c", driver.next_run_id(runs))
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "timeout", limit_seconds=1)
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("INVALID", result["verdict"])
                again = load("run_h2r2").execute("h2r2-f01-c", runs,
                                                 profile_env=profile_env_file(tmp))
                self.assertEqual("RUN_ALREADY_REGISTERED", again["reason"])
                registry = runs / "registry-v2.jsonl"
                registry.unlink()
                (runs / ".locks" / "h2r2-f01-c.json").write_text(
                    json.dumps({"run_id": "h2r2-f01-c", "pid": 2 ** 22, "started_at": "x"}),
                    encoding="utf-8")
                interrupted = load("run_h2r2").execute("h2r2-f01-c", runs,
                                                       profile_env=profile_env_file(tmp))
                self.assertEqual("RUN_ALREADY_STARTED", interrupted["reason"])
                line = json.loads(registry.read_text().splitlines()[-1])
                self.assertEqual(("INVALID", "INTERRUPTED", "SECOND_START_ATTEMPT_REFUSED"),
                                 (line["verdict"], line["reason"], line["registered_by"]))
                self.assertEqual("h2r2-f01-v", load("run_h2r2").next_run_id(runs))
            finally:
                cleanup_run(run_dir)

    def test_a_failed_preflight_blocks_before_the_worker_is_launched(self):
        driver = load("run_h2r2")
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "launched.marker"
            stub = Path(tmp) / "never.py"
            stub.write_text(f"open({str(marker)!r}, 'w').write('launched')\n", encoding="utf-8")

            def failed_preflight(run_dir, env_file):
                return {"verdict": "FAIL", "reasons": ["CONFIG_SOURCES_MISMATCH"]}

            def must_not_run(*args, **kwargs):
                raise AssertionError("the auditor ran on a blocked run")

            runs = Path(tmp) / "runs"
            result = driver.execute("h2r2-f01-c", runs,
                                    worker_command=(sys.executable, str(stub)),
                                    preflight=failed_preflight, auditor=must_not_run,
                                    profile_env=profile_env_file(tmp))
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("BLOCKED", result["verdict"])
                self.assertEqual("BLOCKED", result["final_verdict"])
                self.assertEqual(["PREFLIGHT_FAIL:CONFIG_SOURCES_MISMATCH"], result["reasons"])
                self.assertFalse(marker.exists())
                record = json.loads((run_dir / "run.json").read_text())
                self.assertEqual(["prepare", "preflight", "registry"],
                                 [step["step"] for step in record["steps"]])
                self.assertEqual("BLOCKED", record["steps"][1]["status"])
                line = json.loads((runs / "registry-v2.jsonl").read_text().splitlines()[0])
                self.assertEqual(("BLOCKED", "BLOCKED"),
                                 (line["verdict"], line["final_verdict"]))
            finally:
                cleanup_run(run_dir)

    def test_the_stricter_of_the_two_verdicts_wins(self):
        driver = load("run_h2r2")
        self.assertEqual("ACCEPT", driver.strictest("ACCEPT", "PASS"))
        self.assertEqual("REJECT", driver.strictest("ACCEPT", "PARTIAL"))
        self.assertEqual("REJECT", driver.strictest("ACCEPT", "FAIL"))
        self.assertEqual("BLOCKED", driver.strictest("ACCEPT", "BLOCKED"))
        self.assertEqual("REJECT", driver.strictest("REJECT", "PASS"))
        self.assertEqual("INVALID", driver.strictest("INVALID", "SKIPPED"))


class RunAuditV2(unittest.TestCase):
    """T19: the blind bundle and the validated audit record."""

    def bundle_inputs(self, tmp):
        render = load("render_brief")
        task, _ = task_pair("f01")
        plan_run = next(run for run in json.loads((FZ / "run-plan-v2.json").read_text())["runs"]
                        if run["run_id"] == "h2r2-f01-c")
        run_dir = Path(tmp) / "h2r2-f01-c"
        run_dir.mkdir()
        (run_dir / "CONTRACT.md").write_text(render.render(task, plan_run, sys.executable),
                                             encoding="utf-8")
        (run_dir / "report.md").write_text(
            "Used control_full_v1 and read H2_WARM/references/ticket-lane.md.\n", encoding="utf-8")
        (run_dir / ".h2-telemetry.log").write_text("READ FULL H2_WARM/x.md\n", encoding="utf-8")
        (run_dir / "collected.json").write_text(
            json.dumps({"diff": "diff --git a/x b/x\n+run h2r2-f01-c\n"}), encoding="utf-8")
        (run_dir / "verdict.json").write_text(json.dumps(
            {"run_id": "h2r2-f01-c", "arm": "control", "run_dir": "/elsewhere",
             "materials_commit": "0" * 40, "verdict": "REJECT", "reasons": ["X"],
             "task_id": "f01", "base_sha": task["base_sha"]}), encoding="utf-8")
        return run_dir, plan_run, task

    def test_the_blind_bundle_has_no_arm_label_and_records_the_leakage(self):
        audit_module = load("run_audit_v2")
        with tempfile.TemporaryDirectory() as tmp:
            run_dir, plan_run, task = self.bundle_inputs(tmp)
            bundle = audit_module.prepare_bundle(run_dir, plan_run, task)
            audit_dir = run_dir / "audit"
            self.assertEqual({audit_module.CONTRACT_NAME, audit_module.DIFF_NAME,
                              audit_module.VERDICT_NAME, audit_module.REPORT_NAME,
                              audit_module.REQUEST_NAME},
                             {path.name for path in audit_dir.iterdir()})
            contract = (audit_dir / audit_module.CONTRACT_NAME).read_text()
            self.assertIn(audit_module.BLIND_NOTE.strip(), contract)
            for token in ("ARM = ", "CARRIER_KIND", "CARRIER_SHA256", "h2r2-f01-c",
                          "control_full_v1"):
                self.assertNotIn(token, contract)
            projection = json.loads((audit_dir / audit_module.VERDICT_NAME).read_text())
            self.assertEqual({"verdict", "reasons", "task_id", "base_sha"}, set(projection))
            for path in audit_dir.iterdir():
                self.assertNotIn("READ FULL", path.read_text(errors="replace"), path.name)
            self.assertIn({"file": "report.md", "token": "control_full_v1"}, bundle["leakage"])
            self.assertIn({"file": "diff.patch", "token": "h2r2-"}, bundle["leakage"])
            self.assertEqual(bundle["leakage"], bundle["request"]["leakage"])

    def test_missing_or_malformed_audit_json_is_blocked(self):
        audit_module = load("run_audit_v2")
        with tempfile.TemporaryDirectory() as tmp:
            audit_dir = Path(tmp) / "audit"
            audit_dir.mkdir()
            bundle = {"leakage": []}
            self.assertEqual({"verdict": "BLOCKED", "correctness": None, "findings": [],
                              "invalid_completion": None, "leakage": [], "reasons": ["AUDIT_MISSING"]},
                             audit_module.evaluate(audit_dir, bundle))
            for label, text, reasons in (
                ("not json", "nope", ["AUDIT_UNREADABLE"]),
                ("bad correctness", json.dumps({"correctness": "MAYBE", "findings": []}),
                 ["AUDIT_CORRECTNESS_INVALID"]),
                ("findings not a list", json.dumps({"correctness": "PASS", "findings": {}}),
                 ["AUDIT_FINDINGS_NOT_A_LIST"]),
                ("finding without severity", json.dumps(
                    {"correctness": "PASS", "findings": [
                        {"id": "F1", "category": "HV1", "location": "x", "evidence": "y"}]}),
                 ["AUDIT_FINDING_0:SEVERITY_INVALID"]),
                ("finding without evidence", json.dumps(
                    {"correctness": "PASS", "findings": [
                        {"id": "F1", "severity": "P1", "category": None, "location": "x",
                         "evidence": ""}]}),
                 ["AUDIT_FINDING_0:EVIDENCE_MISSING"]),
            ):
                with self.subTest(label=label):
                    (audit_dir / "audit.json").write_text(text, encoding="utf-8")
                    record = audit_module.evaluate(audit_dir, bundle)
                    self.assertEqual("BLOCKED", record["verdict"])
                    self.assertEqual(reasons, record["reasons"])

    def test_a_complete_audit_is_read_back_with_its_findings_and_leakage(self):
        audit_module = load("run_audit_v2")
        leakage = [{"file": "report.md", "token": "control_full_v1"}]
        with tempfile.TemporaryDirectory() as tmp:
            audit_dir = Path(tmp) / "audit"
            audit_dir.mkdir()
            findings = [{"id": "F1", "severity": "P1", "category": "HV5",
                         "location": "report.md §F", "evidence": "claims done, gate red"}]
            (audit_dir / "audit.json").write_text(json.dumps(
                {"correctness": "FAIL", "invalid_completion": True, "findings": findings,
                 "notes": "audited"}), encoding="utf-8")
            record = audit_module.evaluate(audit_dir, {"leakage": leakage})
            self.assertEqual("FAIL", record["verdict"])
            self.assertTrue(record["invalid_completion"])
            self.assertEqual(findings, record["findings"])
            self.assertEqual(leakage, record["leakage"])
            self.assertEqual([], record["reasons"])


def freeze_is_intact(root):
    try:
        data = (root / H2_REL / "freeze-v2/freeze-manifest.json").read_bytes()
        return (digest(data) == MANIFEST_SHA256
                and json.loads(data)["hashes"] == EXPECTED_V2_HASHES
                and not load("build_manifest").verify(root))
    except (OSError, ValueError, KeyError):
        return False


class FreezeManifest(unittest.TestCase):
    def test_two_independent_anchors_and_materials_binding(self):
        self.assertTrue(freeze_is_intact(ROOT))
        manifest = json.loads((FZ / "freeze-manifest.json").read_text())
        for rel, expected in EXPECTED_V2_HASHES.items():
            self.assertEqual(expected, digest((ROOT / rel).read_bytes()), rel)
        materials = manifest["materials_commit"]
        self.assertEqual(materials, manifest["freeze_parent"])
        runs = json.loads((FZ / "run-plan-v2.json").read_text())["runs"]
        self.assertEqual({materials}, {r["materials_commit"] for r in runs})
        # the materials snapshot is an ancestor of this tree, and the delivered bytes at HEAD are
        # still exactly the measured ones. `HEAD` (not the introducing commit) is the durable anchor:
        # a later edit to any delivered input breaks this test until the freeze is re-pinned.
        self.assertEqual(0, subprocess.run(
            ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", materials, "HEAD"],
            capture_output=True).returncode, "materials commit is not an ancestor of HEAD")
        wrapper = load("wrapper_delivery")
        for arm in ("control", "variant"):
            self.assertEqual(wrapper.delivery(ROOT, materials, arm),
                             wrapper.delivery(ROOT, "HEAD", arm))
        measured = json.loads((FZ / "delivery-anchors.json").read_text())
        wrapper = load("wrapper_delivery")
        for arm in ("control", "variant"):
            self.assertEqual(wrapper.delivery(ROOT, measured["materials_commit"], arm),
                             wrapper.delivery(ROOT, materials, arm))
        # The anchors record the measuring program and the shortlist by hash: the delivered
        # payload above is byte-equal, and the measurement was made by exactly the frozen program
        # on exactly the frozen shortlist. A code commit that changes the program re-pins both.
        self.assertEqual(digest((FZ / "wrapper_delivery.py").read_bytes()),
                         measured["wrapper_program_sha256"])
        self.assertEqual(digest((H2 / "admission/freeze-v2-input/shortlist.json").read_bytes()),
                         measured["shortlist_sha256"])

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
