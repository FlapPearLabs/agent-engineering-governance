"""Freeze-v2 contract tests; no worker/model execution."""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import pwd
import shutil
import subprocess
import sys
import tempfile
import time
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
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/access_audit.py": "00e150f9cbb05deeefdfc5fe52bfa83c162555395d6b6b8c5bb06bebcf4fd178",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/aggregate_runs.py": "86eb73099db5f9c7ac7c2e367fb98219476c7b37e8e2ca84dc90c90f7e5261c8",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/aggregate_set.py": "dc36eef9419904123361a060833aa8287f106e961d183101487c6e91d4f0eb55",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_manifest.py": "ca2dc8d6106d58692d1bc77715be9662b5a4dd8b68dac69ba260827246172274",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_registry.py": "57a06cb8f090c4499399c7942da4b5cb17a41178efab07365206b61033918c0f",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_run_plan.py": "0150309c6cc3a37af25a858f7bb1d089d5110965d74456e3a86a1b3c8a94bfa2",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/collect_v2.py": "1d2cfc7bcb8e2a936eb468d982d8df02946fd5ef9ac6fd3e500bd5722daa7203",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/delivery-anchors.json": "e6a881e0661e7ee5dc64ea7008de075372cae2ba80e2ef60b6570caa8ce402da",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/delivery_anchors.py": "77d29115f1d0320bf9d1a5656772d613e0b855a8f2b1f6badaac3ed3b65b2de2",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/access-audit-clean.jsonl": "e79a8be43c13af170e9424c8d138fd2d42f37f50c93d97b6fe3d19afad3377d1",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/access-audit-hits.jsonl": "147e72b06bc03488918e23eedc20659f8cbb48b0508b9d12aff05d0d042c431b",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/canary-86ac104-events.jsonl": "2b596be37ac0b9aff56989302ee8b44af4246ea2a11f88b3c16875073130d82a",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/canary-86ac104-synthetic-sources-line.jsonl": "0d310198bc7ef4cab0734b4a4e01aebadcb4e862a032a305f50eed10ccb23ffa",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/isolation-canary-events.jsonl": "070743f27b4386e36f99c7fa86badf9b2b4d9b7293d27dc4af75099854acae8f",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/pilot-f01-c-events.jsonl": "8df3d734070e50bdd6e425da3fa43f9206daa1ffa1754b7ba5c28c4867d0e099",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/preflight-debug-config.json": "6e7ba3d7954852de5b4c931532160945a4ce76f728b46272e4b23f2e2ace78c2",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/preflight-debug-paths.txt": "cb7c7f731823fa7f96136e0272ba73079d3d455095b26c478a6518711ab68dbc",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/fixtures/toolname-probe-events.jsonl": "7220205bd72abc05fd1d615cb6a69111685febfd40e0f7840b06cf5bcd9461e6",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/isolation_canary.py": "96c433c7520b6c2b81376fadd900efb97dfc521d712a374fd5fc9de54ba57e35",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/protocol-v2.md": "3233054cb017201804ab45ab06cbe6e643346eda39ce860428415e7b30434bc1",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/render_brief.py": "debe7dcd480d602b2781b0ae3acd0bf9e272f35aa53cb40eacbd273f9eae0f97",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/route-preconditions.json": "31e4108d079a9125c1292dddca3c8a9c0246b070533a7b648a07b16ea2cb4815",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/route_preconditions.py": "9fabe14ca56ad7b94f763edc69bf15ec6fd5ec2b4c43f51c5ee72fa381e7026c",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/run-plan-v2.json": "efb7f388a7b24adc8b2319a88c3e82067948558882a5768b093492288ce4026a",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/run_acceptance_v2.py": "dbe91a3b490e41a4be7b4766fb01c937dd685327844ad88027a054dbd070e410",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/run_audit_v2.py": "1607540b0036d9d4a45d446e9fe54dc80b8a098e09fdfdcff88fd8987ec6d04e",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/run_h2r2.py": "3f345f427d4a2ad3035b1125c1d248204be771a88bc17209ef093843d47f3b3f",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/sandbox_v2.py": "338cd0ac03a274f6b5d60f28de9b3855ab12b7b5c52470eb2f3598baa59e6bfc",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/scope_v2.py": "7c0e0b0b7bf0c3b68452e914ff6831dbaea59fcf2666ad34cb0f9fe682075d9f",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/task-registry-v2.json": "1f4185426076af40d67bc6a4df171979cf1b92ec81c7d3de87e786a989b8a98c",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/worker-brief-v2.md": "57ff9a3bacba43a82b1e62d383533e0726a7de370c51e2b9b6012089a7d23318",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/worker-profile/opencode.json": "409f61b632da9001f18adf8e929094d2127ffe225c782d3eaec2c8106d695ba3",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/worker-sandbox.sb.template": "c05abbbffd35134ee1a90f12a955ce3f47f7719a45168a08396cc1bf541fa280",
    "experiments/v1.2/h2-lazy-disclosure/freeze-v2/wrapper_delivery.py": "24da46f19b0d75af56715e13aef793cb0affa0f756aea42125e532b66fecdd78",
    "experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py": "f4ae829acf4d2416bce9d6b721f631149e22ef0378ae78eb9bc15c880059c666",
    "experiments/v1.2/h2-lazy-disclosure/harness/control-carrier-footer.md": "cb0dfc40247c1575c0706175b3d4bf029973e8b94bf943e6fbccf9a485549186",
    "experiments/v1.2/h2-lazy-disclosure/harness/control-carrier-header.md": "50193bcc4cb882094ee5afcf3e3126a1d610c8f699905e4ac3c97beeab38986e",
    "experiments/v1.2/h2-lazy-disclosure/harness/worker-report-template.md": "540cd07c612319e67b0bce796cbadee1ac57e189613a9de571514414d24dc2f2",
    "experiments/v1.2/h2-lazy-disclosure/routes-h2.json": "a9d0e61dc85fe4bead5d993ddc0bb805e683bdea88d6c36c3aecdd5653304636",
    "experiments/v1.2/h2-lazy-disclosure/scoring-rubric.md": "bcaa4e624f10fe4a9a42852db92cc5e777c7255c8d891680bd72d87ab74c7cef",
    "experiments/v1.2/h2-lazy-disclosure/variant-manifest.json": "8abc1c05a076e39f3b7d04bb1784e7d36cb5e3f1556c5f24b2f47d6ebc164137",
}
MANIFEST_SHA256 = "23c5d2b6f8b05f54b2c9da88e0091fd7d2498e22a6dbdfaa7adc2f4bae19acdd"
SANDBOX_READY = sys.platform == "darwin" and shutil.which("sandbox-exec") is not None


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
                    # F18 / T28: the delivered HEAD is a NEW neutral commit with the base TREE.
                    self.assertEqual(receipt["delivered_head"],
                                     git("rev-parse", "HEAD", root=run / "repo").decode().strip())
                    self.assertNotEqual(task["BASE_SHA"], receipt["delivered_head"])
                    self.assertEqual(git("rev-parse", f"{task['BASE_SHA']}^{{tree}}").decode().strip(),
                                     git("rev-parse", "HEAD^{tree}",
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
        """F8 + F18: one neutral commit with the base TREE, no remote/alternates, no candidate."""
        wrapper = load("wrapper_delivery")
        task, source = task_pair("f01")
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp) / "history-free"
            try:
                receipt = wrapper.prepare(ROOT, run, "f01", "variant", "HEAD")
                repo = run / "repo"
                self.assertEqual("standalone_history_free", receipt["repository_kind"])
                self.assertEqual([receipt["delivered_head"]],
                                 git("rev-list", "--all", root=repo).decode().split())
                self.assertEqual([], git("for-each-ref", "--format=%(refname)",
                                         root=repo).decode().split())
                self.assertEqual(b"", git("remote", root=repo))
                self.assertFalse((repo / ".git" / "objects" / "info" / "alternates").exists())
                self.assertFalse((repo / ".git" / "logs").exists())
                # F18: neither the base commit nor the candidate is in the delivered history.
                self.assertEqual(["h2 task base"], git("log", "--all", "--format=%s",
                                                       root=repo).decode().splitlines())
                self.assertNotEqual(task["base_sha"], receipt["delivered_head"])
                for oid in (task["base_sha"], source["CANDIDATE_SHA"]):
                    self.assertNotEqual(0, subprocess.run(
                        ["git", "-C", str(repo), "cat-file", "-e", oid],
                        capture_output=True).returncode, oid)
                self.assertNotIn(task["base_sha"], git("log", "--all", root=repo).decode())
                self.assertNotIn(source["CANDIDATE_SHA"], git("log", "--all", root=repo).decode())
                self.assertEqual(receipt["delivered_head"],
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

    def test_a_run_root_under_any_os_home_is_refused_with_a_fake_process_home(self):
        """F20: "under a home" is the OS user database, not only the HOME this process runs with."""
        wrapper = load("wrapper_delivery")
        real_home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
        self.assertIn(real_home, [home.resolve() for home in wrapper.os_home_directories()])
        self.assertNotIn(Path("/Users") / "Shared", wrapper.os_home_directories())
        with tempfile.TemporaryDirectory() as fake:
            with mock.patch.dict(os.environ, {"HOME": fake}):
                self.assertEqual("RUN_DIR_UNDER_OPERATOR_HOME",
                                 wrapper.run_root_reason(Path(fake) / "h2-runs" / "canary"))
                # the operator's REAL home is still refused even though HOME points elsewhere
                self.assertEqual("RUN_DIR_UNDER_USER_HOME",
                                 wrapper.run_root_reason(real_home / "h2-runs" / "canary"))
        others = [home for home in wrapper.os_home_directories()
                  if home.resolve() != real_home]
        if not others:
            self.skipTest("the user database declares no second home directory")
        other = others[0]
        self.assertEqual("RUN_DIR_UNDER_USER_HOME",
                         wrapper.run_root_reason(other / "h2-runs" / "canary"))

    def test_a_broken_discovery_symlink_still_refuses_the_run_root(self):
        """F20: a runtime walking up from the cwd discovers a DANGLING `.agents` just the same."""
        wrapper = load("wrapper_delivery")
        with tempfile.TemporaryDirectory() as tmp:
            os.symlink(Path(tmp) / "gone", Path(tmp) / ".agents")
            self.assertEqual("RUN_DIR_UNDER_DISCOVERABLE_ROOT:.agents",
                             wrapper.run_root_reason(Path(tmp) / "runs" / "canary"))
            with self.assertRaisesRegex(ValueError, "RUN_DIR_UNDER_DISCOVERABLE_ROOT"):
                wrapper.prepare(ROOT, Path(tmp) / "runs" / "canary", "f01", "control", "HEAD")
            self.assertFalse((Path(tmp) / "runs" / "canary").exists())

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

    def test_unresolved_constructs_are_recorded_as_evidence_not_hits(self):
        """F16 / T29: what a static tokenizer cannot resolve is evidence, never a verdict."""
        cases = {
            "cat $(printf x)": "COMMAND_SUBSTITUTION",
            "cat `printf x`": "BACKTICK",
            "eval cat x": "EVAL",
            f"{sys.executable} -c 'print(1)'": "INLINE_PROGRAM",
            "printf aGk= | base64 -d": "DECODER",
            "printf x | xargs cat": "XARGS",
        }
        for command, construct in cases.items():
            with self.subTest(command=command):
                result = self.one(self.tool("shell", command=command))
                self.assertEqual("PASS", result["verdict"], result["hits"])
                self.assertIn(construct,
                              [item["construct"] for item in result["unresolved_constructs"]])
        plain = self.one(self.tool("shell", command="cd repo && git status --porcelain"))
        self.assertEqual([], plain["unresolved_constructs"])

    def test_a_denied_dynamic_read_is_evidence_and_stays_a_pass(self):
        """F16 / T29: the sandbox denied it, so nothing was obtained; it is not a hit."""
        run = "/srv/runs/h2r2-f01-c"
        denied = {"type": "tool_use", "part": {"tool": "shell", "state": {
            "status": "completed", "input": {"command": "python3 -c 'open(...)'"},
            "output": ("PermissionError: [Errno 1] Operation not permitted: "
                       "'/srv/runs/.driver/h2r2-f01-c/confinement-plant.txt'")}}}
        result = self.one(denied, run=run)
        self.assertEqual("PASS", result["verdict"])
        self.assertEqual([], result["hits"])
        self.assertEqual(1, len(result["sandbox_denied"]))
        self.assertEqual("SANDBOX_DENIED", result["sandbox_denied"][0]["reason"])
        self.assertTrue(result["sandbox_denied"][0]["path"].endswith("confinement-plant.txt"))
        inside = {"type": "tool_use", "part": {"tool": "shell", "state": {
            "status": "completed", "input": {"command": "cat x"},
            "output": ("cat: Operation not permitted: "
                       f"'{run}/repo/x.txt'")}}}
        self.assertEqual([], self.one(inside, run=run)["sandbox_denied"])

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


class AccessAuditFalsePositives(unittest.TestCase):
    """T36a / F27 + F29: pilot #5's two access-audit hits were false positives.

    The fixture is the two REAL shell calls of the live pilot #5 stream (efc46fc), sanitised the
    way the earlier real-stream fixtures are: only `<RUN_ROOT>` and `<PY>` prefixes are replaced,
    nothing else is rewritten, so the parser is exercised on what the worker actually sent.
    """

    FIXTURE = "pilot-efc46fc-f27-events.jsonl"
    RUN = Path("/srv/runs/h2r2-f01-c")
    HOME = "/srv/profile-home"

    def expand(self, text=None):
        raw = text if text is not None else (FZ / "fixtures" / self.FIXTURE).read_text(
            encoding="utf-8")
        return raw.replace("<RUN_ROOT>", str(self.RUN)).replace("<PY>", sys.executable)

    def tool(self, name, **inputs):
        return {"type": "tool_use", "part": {"tool": name, "state": {"input": inputs}}}

    def audit_events(self, *events):
        module = load("access_audit")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text("\n".join(json.dumps(item) for item in events), encoding="utf-8")
            return module.audit(path, self.RUN, home=self.HOME, python=sys.executable)

    def audit_text(self, text):
        module = load("access_audit")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "events.jsonl"
            path.write_text(text, encoding="utf-8")
            return module.audit(path, self.RUN, home=self.HOME, python=sys.executable)

    def test_the_recorded_pilot_five_commands_pass(self):
        """F27: the run's own `git clone repo .tmp/…` and `T=../.tmp/probe` are inside."""
        raw = (FZ / "fixtures" / self.FIXTURE).read_text(encoding="utf-8")
        self.assertNotIn("/Users/", raw)
        self.assertNotIn("/private/", raw)
        text = self.expand(raw)
        self.assertIn("git clone -q --no-hardlinks repo .tmp/h2-baseline-git", text)
        self.assertIn("T=../.tmp/probe", text)
        result = self.audit_text(text)
        self.assertEqual("PASS", result["verdict"], result["hits"])
        self.assertEqual([], result["hits"])
        self.assertEqual(2, result["tool_calls"])
        self.assertEqual(2, result["events"])
        self.assertEqual([], result["sandbox_denied"])

    def test_a_clone_of_the_runs_own_repository_is_not_an_escape(self):
        for command in ("git clone repo copy",
                        "cd repo && git clone . ../copy",
                        f"cd {self.RUN} && git clone -q --no-hardlinks repo .tmp/copy"):
            with self.subTest(command=command):
                result = self.audit_events(self.tool("shell", command=command))
                self.assertEqual("PASS", result["verdict"], result["hits"])

    def test_a_clone_source_that_reaches_outward_is_still_a_hit(self):
        for command in ("git clone https://github.com/x/y",
                        "git clone ../../other-repo",
                        "git clone host:repo",
                        "git clone /tmp/other copy",
                        "git pull origin main",
                        "git fetch"):
            with self.subTest(command=command):
                result = self.audit_events(self.tool("shell", command=command))
                self.assertEqual("INVALID", result["verdict"], command)
                self.assertIn("GIT_REMOTE_REPOSITORY",
                              [hit["reason"] for hit in result["hits"]], command)

    def test_every_assignment_value_resolves_against_the_preceding_cd(self):
        """F27b: `cd repo` moves the base of the very next `KEY=value` assignment."""
        for command in ('cd repo && T=../.tmp/probe; cat "$T/list.json"',
                        f'cd {self.RUN}/repo && T=../.tmp/probe; rm -rf "$T"'):
            with self.subTest(command=command):
                result = self.audit_events(self.tool("shell", command=command))
                self.assertEqual("PASS", result["verdict"], result["hits"])
        for command in ("cd repo && T=../../x; cat $T",
                        "cd repo && cat ../../outside"):
            with self.subTest(command=command):
                result = self.audit_events(self.tool("shell", command=command))
                self.assertEqual("INVALID", result["verdict"], command)
                self.assertIn("PATH_OUTSIDE_RUN",
                              [hit["reason"] for hit in result["hits"]], command)

    def test_a_document_that_merely_mentions_the_denial_is_not_a_denial(self):
        """F29: the phrase and the path must share a denial LINE, not merely the event."""
        schema = (
            '{\n  "description": "the sandbox returns Operation not permitted",\n'
            '  "example": "/srv/other/evidence.json"\n}\n')
        read = {"type": "tool_use", "part": {"tool": "read", "state": {
            "status": "completed",
            "input": {"path": "repo/schemas/review-evidence.schema.json"},
            "output": schema}}}
        result = self.audit_events(read)
        self.assertEqual("PASS", result["verdict"], result["hits"])
        self.assertEqual([], result["sandbox_denied"])

    def test_a_real_denial_line_naming_an_outside_path_is_evidence(self):
        """F28/F29: a genuine EPERM line still records the outside path, as evidence only."""
        denied = {"type": "tool_use", "part": {"tool": "shell", "state": {
            "status": "completed", "input": {"command": "mktemp -d"},
            "output": ("mktemp: mkdtemp failed on /var/folders/xy/T/tmp.abc: "
                       "Operation not permitted")}}}
        result = self.audit_events(denied)
        self.assertEqual("PASS", result["verdict"], result["hits"])
        self.assertEqual([], result["hits"])
        self.assertEqual(1, len(result["sandbox_denied"]))
        entry = result["sandbox_denied"][0]
        self.assertEqual("SANDBOX_DENIED", entry["reason"])
        self.assertEqual("/var/folders/xy/T/tmp.abc", entry["path"])
        self.assertIn("Operation not permitted", entry["value"])


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
                self.assertEqual(json.loads((run / "receipt.json").read_text())["delivered_head"],
                                 collected["delivered_head"])
                self.assertNotEqual(task["base_sha"],
                                    git("rev-parse", "HEAD", root=repo).decode().strip())
                statuses = {change["path"]: change["status"] for change in collected["changes"]}
                self.assertEqual("A", statuses["docs/worker-note.md"])
                self.assertEqual("A", statuses["untracked-note.md"])
                # The delta is decided from the worktree bytes against the DRIVER's base snapshot,
                # never from repo/.git: a committed and an untracked file look the same here.
                manifest = json.loads(
                    (load("wrapper_delivery").base_manifest_path(run)).read_text())
                self.assertEqual(set(git("ls-tree", "-r", "--name-only", task["base_sha"])
                                     .decode().splitlines()), set(manifest["entries"]))
                self.assertTrue((load("wrapper_delivery").base_dir(run) / "RULES.md").is_file())
                self.assertEqual(collected["diff_sha256"], digest(collected["diff"].encode()))
                self.assertIn("diff --git a/docs/worker-note.md b/docs/worker-note.md",
                              collected["diff"])
                self.assertIn("new file mode 100644", collected["diff"])
                self.assertIn("+note", collected["diff"])
                self.assertEqual({"AGENTS.md", "H2_RULES.md"},
                                 {name for name in collected["delivered_hashes"]
                                  if not name.startswith("H2_WARM/")})
                self.assertGreaterEqual(len(collected["delivered_hashes"]), 3)
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


class CollectionTrustNothing(unittest.TestCase):
    """F15 / T28: the worker owns repo/.git, so the collection may not believe any of it."""

    def test_the_driver_records_the_base_from_the_governance_repository(self):
        wrapper = load("wrapper_delivery")
        task, _ = task_pair("f01")
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f01")
            try:
                manifest = json.loads(wrapper.base_manifest_path(run).read_text())
                self.assertEqual(task["base_sha"], manifest["base_sha"])
                self.assertEqual("governance_repository", manifest["source"])
                rows = {}
                for part in git("ls-tree", "-r", "-z", "--full-tree",
                                task["base_sha"]).split(b"\0"):
                    if not part:
                        continue
                    header, path = part.split(b"\t", 1)
                    mode, kind, oid = header.decode().split(" ")
                    self.assertEqual("blob", kind)
                    rows[path.decode()] = (mode, oid)
                self.assertEqual(set(rows), set(manifest["entries"]))
                for path, (mode, oid) in rows.items():
                    entry = manifest["entries"][path]
                    self.assertEqual(mode, entry["mode"], path)
                    self.assertEqual(oid, entry["blob_sha"], path)
                    blob = git("show", f"{task['base_sha']}:{path}")
                    self.assertEqual(digest(blob), entry["sha256"], path)
                    delivered = wrapper.base_dir(run) / path
                    if entry["type"] == "symlink":
                        self.assertEqual(blob, os.fsencode(os.readlink(delivered)), path)
                    else:
                        self.assertEqual("file", entry["type"], path)
                        self.assertEqual(blob, delivered.read_bytes(), path)
                self.assertTrue((wrapper.base_dir(run) / "RULES.md").is_file())
            finally:
                cleanup_run(run)

    def test_index_flags_cannot_hide_an_edit_or_a_deletion(self):
        collector = load("collect_v2")
        acceptance = load("run_acceptance_v2")
        task, _ = task_pair("f02")
        oracle_rel = task["oracle"]["path"]
        test_rel = "scripts/tests/test_seam_contract_partitions.py"
        attacks = (
            ("assume-unchanged edit", test_rel, "--assume-unchanged", "M"),
            ("assume-unchanged delete", test_rel, "--assume-unchanged", "D"),
            ("skip-worktree edit", oracle_rel, "--skip-worktree", "M"),
            ("skip-worktree delete", oracle_rel, "--skip-worktree", "D"),
        )
        for label, rel, flag, expected in attacks:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                run = prepare_run(tmp, "f02")
                try:
                    write_artifacts(run)
                    repo = run / "repo"
                    target = repo / rel
                    subprocess.run(["git", "-C", str(repo), "update-index", flag, rel],
                                   capture_output=True, check=True)
                    if expected == "M":
                        target.write_text(target.read_text(encoding="utf-8") + "\n# hidden\n",
                                          encoding="utf-8")
                    else:
                        target.unlink()
                    self.assertEqual(expected, "M" if target.exists() else "D")
                    collected = collector.collect(ROOT, run)
                    statuses = {change["path"]: change["status"]
                                for change in collected["changes"]}
                    self.assertEqual(expected, statuses[rel], collected["reasons"])
                    self.assertIn(f"diff --git a/{rel} b/{rel}", collected["diff"])
                    if expected == "M":
                        self.assertIn("+# hidden", collected["diff"])
                    else:
                        self.assertIn("deleted file mode", collected["diff"])
                    verdict = acceptance.accept(ROOT, run)
                    self.assertEqual("REJECT", verdict["verdict"])
                    self.assertIn(f"WORKER_SCOPE_DENIED:{rel}", verdict["reasons"])
                finally:
                    cleanup_run(run)

    def test_attributes_local_config_and_replace_refs_cannot_redact_a_change(self):
        collector = load("collect_v2")
        acceptance = load("run_acceptance_v2")
        task, _ = task_pair("f03")
        rel = task["oracle"]["path"]
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f03")
            try:
                write_artifacts(run)
                repo = run / "repo"
                (repo / ".gitattributes").write_text(f"{rel} -diff filter=h2\n", encoding="utf-8")
                subprocess.run(["git", "-C", str(repo), "config", "filter.h2.clean", "cat"],
                               check=True)
                subprocess.run(["git", "-C", str(repo), "config", "diff.external", "/bin/false"],
                               check=True)
                target = repo / rel
                target.write_text(target.read_text(encoding="utf-8") + "\n# redacted\n",
                                  encoding="utf-8")
                collected = collector.collect(ROOT, run)
                statuses = {change["path"]: change["status"]
                            for change in collected["changes"]}
                self.assertEqual("M", statuses[rel])
                self.assertEqual("A", statuses[".gitattributes"])
                self.assertIn("# redacted", collected["diff"])
                verdict = acceptance.accept(ROOT, run)
                self.assertEqual("REJECT", verdict["verdict"])
                self.assertIn(f"WORKER_SCOPE_DENIED:{rel}", verdict["reasons"])
            finally:
                cleanup_run(run)
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f03")
            try:
                write_artifacts(run)
                repo = run / "repo"
                target = repo / rel
                target.write_text(target.read_text(encoding="utf-8") + "\n# replaced\n",
                                  encoding="utf-8")
                commit_in(repo, "worker commit hidden behind a replace ref")
                head = git("rev-parse", "HEAD", root=repo).decode().strip()
                delivered = json.loads((run / "receipt.json").read_text())["delivered_head"]
                subprocess.run(["git", "-C", str(repo), "update-ref",
                                f"refs/replace/{head}", delivered], check=True)
                # git itself no longer sees the worker's commit ...
                self.assertEqual(["h2 task base"],
                                 git("log", "-1", "--format=%s", root=repo).decode().splitlines())
                self.assertEqual(0, subprocess.run(
                    ["git", "-C", str(repo), "cat-file", "-e", head],
                    capture_output=True).returncode)
                wrapper = load("wrapper_delivery")
                base_bytes = (wrapper.base_dir(run) / rel).read_bytes()
                self.assertEqual(base_bytes, git("show", f"HEAD:{rel}", root=repo))
                self.assertNotEqual(base_bytes, (repo / rel).read_bytes())
                # ... and the collection still does, from the worktree bytes.
                collected = collector.collect(ROOT, run)
                statuses = {change["path"]: change["status"]
                            for change in collected["changes"]}
                self.assertEqual("M", statuses[rel])
                self.assertIn("+# replaced", collected["diff"])
                verdict = acceptance.accept(ROOT, run)
                self.assertEqual("REJECT", verdict["verdict"])
                self.assertIn(f"WORKER_SCOPE_DENIED:{rel}", verdict["reasons"])
            finally:
                cleanup_run(run)

    def test_a_missing_or_mismatched_base_snapshot_is_invalid(self):
        collector = load("collect_v2")
        wrapper = load("wrapper_delivery")
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f01")
            try:
                write_artifacts(run)
                wrapper.base_manifest_path(run).unlink()
                collected = collector.collect(ROOT, run)
                self.assertEqual("INVALID", collected["status"])
                self.assertIn("MISSING_BASE_SNAPSHOT", collected["reasons"])
                self.assertEqual([], collected["changes"])
            finally:
                cleanup_run(run)
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f01")
            try:
                write_artifacts(run)
                path = wrapper.base_manifest_path(run)
                manifest = json.loads(path.read_text())
                manifest["base_sha"] = "0" * 40
                path.write_text(json.dumps(manifest), encoding="utf-8")
                collected = collector.collect(ROOT, run)
                self.assertEqual("INVALID", collected["status"])
                self.assertIn("BASE_SNAPSHOT_DOES_NOT_MATCH_RECEIPT", collected["reasons"])
            finally:
                cleanup_run(run)

    def test_a_deleted_repository_metadata_is_fail_closed(self):
        collector = load("collect_v2")
        with tempfile.TemporaryDirectory() as tmp:
            run = prepare_run(tmp, "f01")
            try:
                write_artifacts(run)
                shutil.rmtree(run / "repo" / ".git")
                collected = collector.collect(ROOT, run)
                self.assertEqual("INVALID", collected["status"])
                self.assertIn("TASK_REPOSITORY_UNREADABLE", collected["reasons"])
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
        """The delta is taken against the DRIVER's base snapshot, never against HEAD."""
        acceptance = load("run_acceptance_v2")
        wrapper = load("wrapper_delivery")
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
                base_blob = (wrapper.base_dir(run) / rel).read_bytes()
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
verdict, its attempt retries and its registry lines can be exercised without a worker.
MODE "provider-once" fails on the first launch only, which is how a retry is observed.
"""
import json
import subprocess
import sys
import time

MODE = "__MODE__"
PATCH = "__PATCH__"
COUNTER = "__COUNTER__"


def launches():
    try:
        with open(COUNTER) as handle:
            count = int(handle.read().strip() or 0)
    except (OSError, ValueError):
        count = 0
    count += 1
    with open(COUNTER, "w") as handle:
        handle.write(str(count))
    return count


def provider_failure():
    print(json.dumps({"type": "error", "sessionID": "ses_stub",
                      "error": {"type": "provider.no-route",
                                "message": "Model unavailable"}}))
    sys.stdout.flush()
    sys.exit(1)


def work():
    open("report.md", "w").write("# report\\n\\nstub filler\\n")
    open(".h2-telemetry.log", "w").write("READ FULL repo/RULES.md\\n")
    print(json.dumps({"type": "text", "sessionID": "ses_stub", "part": {"text": "stub done"}}))


if MODE == "provider-always":
    launches()
    provider_failure()
if MODE == "provider-once" and launches() == 1:
    provider_failure()
if MODE in ("accept", "provider-once"):
    subprocess.run(["git", "-C", "repo", "apply", "--whitespace=nowarn", PATCH], check=True)
    work()
elif MODE == "provider-after-tool":
    launches()
    print(json.dumps({"type": "tool_use", "sessionID": "ses_stub",
                      "part": {"tool": "read",
                               "state": {"status": "completed",
                                         "input": {"path": "repo/README.md"}}}}))
    provider_failure()
elif MODE == "noop":
    work()
elif MODE == "tamper":
    launches()
    print(json.dumps({"type": "tool_use", "sessionID": "ses_stub",
                      "part": {"tool": "read",
                               "state": {"status": "completed",
                                         "input": {"path": "repo/README.md"}}}}))
    print(json.dumps({"type": "error", "sessionID": "ses_stub",
                      "error": {"type": "worker.internal", "message": "stub"}}))
    sys.stdout.flush()
    with open("events.jsonl", "w") as handle:
        handle.write(json.dumps({"type": "text", "sessionID": "ses_stub",
                                 "part": {"text": "rewritten by the worker"}}) + "\\n")
    work()
elif MODE == "escape":
    print(json.dumps({"type": "tool_use", "sessionID": "ses_stub",
                      "part": {"tool": "read",
                               "state": {"status": "completed",
                                         "input": {"path": "/etc/hosts"}}}}))
    work()
elif MODE == "timeout":
    print(json.dumps({"type": "step_start", "sessionID": "ses_stub"}))
    sys.stdout.flush()
    time.sleep(30)
else:
    print(json.dumps({"type": "error", "sessionID": "ses_stub", "part": {"text": "stub"}}))
'''


SANDBOX_DYNAMIC_STUB = '''
import json
import os

run_id = os.path.basename(os.getcwd())
driver = os.path.join(os.path.dirname(os.getcwd()), ".driver", run_id)
target = os.path.join(driver, "confinement-plant.txt")
message = ""
try:
    open(target).read()
except OSError as exc:
    message = "%s: %s" % (type(exc).__name__, exc)
command = "python3 -c " + json.dumps("open(%r).read()" % target)
print(json.dumps({"type": "tool_use", "sessionID": "ses_stub",
                  "part": {"tool": "shell",
                           "state": {"status": "completed",
                                     "input": {"command": command},
                                     "output": message}}}))
open("report.md", "w").write("# report\\n\\ndynamic read denied\\n")
open(".h2-telemetry.log", "w").write("READ FULL repo/RULES.md\\n")
print(json.dumps({"type": "text", "sessionID": "ses_stub", "part": {"text": "done"}}))
'''


SCHEDULER_CHILD = '''"""Test-only scheduler child: one `run` child process, never a model, never a network call.

It behaves like the frozen driver from the scheduler's point of view: it takes a live lock, holds
it while it "runs", then either registers one ACCEPT line or ends BLOCKED:PROVIDER_UNREACHABLE
without registering. Its start/end times are written to a shared events file so a test can measure
how many children were alive at once.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

run_id, runs_root, mode, delay = sys.argv[1], Path(sys.argv[2]), sys.argv[3], float(sys.argv[4])
stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
events = runs_root / "child-events.jsonl"
lock = runs_root / ".locks" / (run_id + ".json")
lock.parent.mkdir(parents=True, exist_ok=True)
lock.write_text(json.dumps({"run_id": run_id, "pid": os.getpid(), "started_at": stamp}) + "\\n")
with events.open("a") as handle:
    handle.write(json.dumps({"event": "start", "run_id": run_id, "time": time.time()}) + "\\n")
time.sleep(delay)
if mode == "blocked":
    lock.unlink()
    with events.open("a") as handle:
        handle.write(json.dumps({"event": "end", "run_id": run_id, "time": time.time()}) + "\\n")
    print(json.dumps({"outcome": "BLOCKED", "run_id": run_id, "registered": False,
                      "final_verdict": "BLOCKED",
                      "reasons": ["PROVIDER_UNREACHABLE:EXIT:1"]}))
    sys.exit(1)
with (runs_root / "registry-v2.jsonl").open("a") as handle:
    handle.write(json.dumps({"run_id": run_id, "verdict": "ACCEPT", "final_verdict": "ACCEPT",
                             "started_at": stamp,
                             "finished_at": datetime.now(timezone.utc).isoformat(
                                 timespec="seconds")}, sort_keys=True) + "\\n")
lock.write_text(json.dumps({"run_id": run_id, "pid": os.getpid(),
                            "final_verdict": "ACCEPT"}) + "\\n")
with events.open("a") as handle:
    handle.write(json.dumps({"event": "end", "run_id": run_id, "time": time.time()}) + "\\n")
print(json.dumps({"outcome": "EXECUTED", "run_id": run_id, "registered": True,
                  "final_verdict": "ACCEPT"}))
'''


CONCURRENT_WRITER = '''"""Test-only concurrent writer: appends registry-shaped lines through the driver."""
import sys

sys.path.insert(0, sys.argv[1])
import run_h2r2

path, prefix, count = sys.argv[2], sys.argv[3], int(sys.argv[4])
for number in range(count):
    run_h2r2.append_jsonl(path, {"run_id": "%s-%d" % (prefix, number), "task_id": "f01",
                                 "arm": "control", "reason": "x" * 4096})
'''


def scheduler_child(directory):
    path = Path(directory) / "stub-scheduler-child.py"
    path.write_text(SCHEDULER_CHILD, encoding="utf-8")
    return path


def scheduler_spawner(tmp, runs, modes=None, delay=0.15):
    """A spawn callable that starts real child processes of the test-only scheduler child."""
    script = scheduler_child(tmp)
    sequence = {run_id: list(values) if isinstance(values, list) else [values]
                for run_id, values in (modes or {}).items()}

    def spawn(run_id):
        values = sequence.get(run_id) or ["ok"]
        mode = values.pop(0) if len(values) > 1 else values[0]
        log = Path(tmp) / "scheduler-logs" / f"{run_id}-{time.monotonic_ns()}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("ab") as out:
            process = subprocess.Popen([sys.executable, str(script), run_id, str(runs), mode,
                                        str(delay)],
                                       stdin=subprocess.DEVNULL, stdout=out,
                                       stderr=subprocess.STDOUT, start_new_session=True)
        return {"process": process, "pid": process.pid, "log": log}

    return spawn


class FakeClock:
    """A monotonic clock a test advances itself, so a real backoff costs no real time.

    `clock` is what the scheduler reads, `sleep` is what it calls while it waits; every sleep
    advances the clock by at least one step, so a 60 s deadline passes in 60 fast iterations and
    the recorded wait is still the real one (60, 120, ...).
    """

    def __init__(self, step=1.0):
        self.seconds = 0.0
        self.step = step

    def clock(self):
        return self.seconds

    def sleep(self, seconds):
        self.seconds += max(float(seconds), self.step)


def profile_env_file(directory):
    """A profile env file for tests: an export block, never the operator's real one."""
    path = Path(directory) / "profile-env.sh"
    path.write_text(f"export PATH={os.environ.get('PATH', '/usr/bin:/bin')}\nexport LANG=C\n",
                    encoding="utf-8")
    return path


def stub_worker(directory, mode, patch=None):
    path = Path(directory) / f"stub-{mode}.py"
    counter = Path(directory) / f"launches-{mode}.txt"
    path.write_text(STUB_WORKER.replace("__MODE__", mode)
                    .replace("__PATCH__", str(patch or ""))
                    .replace("__COUNTER__", str(counter)),
                    encoding="utf-8")
    return path


def candidate_patch(directory, task):
    """The historical candidate's NON-TEST delta: what a successful worker leaves in repo/."""
    _, source = task_pair(task["task_id"])
    path = Path(directory) / "delta.patch"
    path.write_bytes(git("diff", "--binary", task["base_sha"], source["CANDIDATE_SHA"],
                         "--", ":!scripts/tests"))
    return path


def passing_preflight(run_dir, env_file, **kwargs):
    return {"verdict": "PASS", "reasons": []}


def passing_probe(purpose, attempt):
    """A reachability check that passes; never a model, never a network call (F14)."""
    return {"verdict": "PASS", "reasons": [], "seconds": 0.01, "events": 2, "token_seen": True,
            "purpose": purpose, "attempt": attempt}


class StubSandbox:
    """Test-only stand-in for the OS sandbox: exercises the driver's steps, not the barrier.

    The real barrier is exercised by `SandboxConfinement` below, which runs the rendered profile
    under the platform `sandbox-exec` and skips on a platform without it.
    """

    def available(self):
        return True

    def plant(self, driver_dir):
        path = Path(driver_dir) / "confinement-plant-stub.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stub-plant\n", encoding="utf-8")
        return path, "stub-plant"

    def profile(self, stream_dir, launch, home, python=None):
        path = Path(stream_dir) / "worker.sb"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("(stub sandbox)\n", encoding="utf-8")
        return {"path": str(path), "sha256": digest(b"(stub sandbox)\n"), "template": "stub",
                "template_sha256": digest(b"stub"), "launch": str(launch), "home": str(home),
                "interpreter": str(python or sys.executable), "deny_roots": []}

    def confine(self, profile_path, argv):
        return [str(item) for item in argv]

    def self_test(self, profile_path, launch, planted, python=None, token=None):
        return {"verdict": "PASS", "reasons": [],
                "profile_sha256": digest(Path(profile_path).read_bytes())}


class StubAuth:
    """Test-only credential hand-off: never a real credential, never a model."""

    def __init__(self, ok=True):
        self.ok = ok
        self.calls = []

    def import_(self, master_env, env, cwd):
        self.calls.append(("import", dict(env)))
        return {"ok": self.ok, "export_returncode": 0 if self.ok else 1,
                "import_returncode": 0 if self.ok else 1, "bytes": 0,
                **({} if self.ok else {"reason": "AUTH_EXPORT_FAILED"})}

    def logout(self, env, cwd):
        self.calls.append(("logout", dict(env)))
        return {"ran": True, "returncode": 0}


class FailingSandbox(StubSandbox):
    """A rendered profile that does not confine: the driver must refuse to launch."""

    def self_test(self, profile_path, launch, planted, python=None, token=None):
        return {"verdict": "FAIL", "reasons": ["PYTHON_READ_NOT_DENIED"],
                "profile_sha256": digest(Path(profile_path).read_bytes())}


def stub_auditor(verdict="PASS"):
    def audit(run_dir, plan_run, task, *, launch, command, env, limit_seconds,
              events_path=None, stderr_path=None):
        audit_dir = Path(run_dir) / "audit"
        audit_dir.mkdir(exist_ok=True)
        (audit_dir / "audit.json").write_text(json.dumps(
            {"correctness": verdict, "invalid_completion": False, "findings": [],
             "notes": "stub auditor"}), encoding="utf-8")
        return {"verdict": verdict, "reasons": [], "leakage": []}
    return audit


def execute_stub(tmp, mode="noop", *, auditor=None, preflight=None, limit_seconds=None,
                 probe=None, sandbox=None, auth=None):
    driver = load("run_h2r2")
    task, _ = task_pair("f01")
    patch = candidate_patch(tmp, task) if mode in ("accept", "provider-once") else None
    runs = Path(tmp) / "runs"
    result = driver.execute("h2r2-f01-c", runs,
                            worker_command=(sys.executable, str(stub_worker(tmp, mode, patch))),
                            preflight=preflight or passing_preflight,
                            auditor=auditor or stub_auditor(),
                            profile_env=profile_env_file(tmp),
                            probe=probe or passing_probe,
                            limit_seconds=limit_seconds,
                            sandbox=sandbox or StubSandbox(),
                            auth=auth or StubAuth())
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
        """F11 + F19/F21: PYTHONDONTWRITEBYTECODE=1, and HOME/XDG/TMPDIR are the fresh state."""
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
                                  limit_seconds, events_path=None, stderr_path=None):
                captured["auditor"] = dict(env)
                return stub_auditor()(run_dir, plan_run, task, launch=launch,
                                      command=command, env=env, limit_seconds=limit_seconds)

            runs = Path(tmp) / "runs"
            with mock.patch.object(driver, "launch", recording_launch):
                result = driver.execute(
                    "h2r2-f01-c", runs,
                    worker_command=(sys.executable, str(stub_worker(tmp, "noop"))),
                    preflight=passing_preflight, auditor=recording_auditor,
                    probe=passing_probe, profile_env=env_file,
                    sandbox=StubSandbox(), auth=StubAuth())
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("REJECT", result["verdict"], result["reasons"])
                worker = captured["worker"]
                auditor = captured["auditor"]
                self.assertEqual("1", worker["PYTHONDONTWRITEBYTECODE"])
                self.assertEqual("1", auditor["PYTHONDONTWRITEBYTECODE"])
                self.assertEqual(set(), set(worker) - (allowed | {
                    "HOME", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
                    "XDG_CACHE_HOME", "TMPDIR"}))
                self.assertNotEqual(expected.get("HOME"), worker["HOME"])
                self.assertEqual((run_dir.parent / ".driver" / "h2r2-f01-c"
                                  / "home-1").resolve(), Path(worker["HOME"]))
                self.assertEqual((run_dir / ".tmp").resolve(), Path(worker["TMPDIR"]))
                self.assertEqual((run_dir.parent / ".driver" / "h2r2-f01-c"
                                  / "audit-home-1").resolve(), Path(auditor["HOME"]))
                self.assertEqual((run_dir / "audit" / ".tmp").resolve(),
                                 Path(auditor["TMPDIR"]))
                for key in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME",
                            "XDG_CACHE_HOME"):
                    self.assertTrue(Path(worker[key]).is_relative_to(Path(worker["HOME"])), key)
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
                self.assertEqual([("prepare", "DONE"), ("home", "DONE"), ("preflight", "PASS"),
                                  ("brief", "DONE"), ("confinement", "PASS"),
                                  ("reachability", "PASS"), ("worker", "DONE"),
                                  ("access_audit", "PASS"),
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
                # T30 / F20 P3-4: "registered=1" is not a result; the status names the pairs.
                self.assertEqual(10, state["planned_pairs"])
                self.assertEqual(0, state["usable_pairs"])
                self.assertEqual(0, state["blocked"])
                self.assertEqual(0, state["invalid"])
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

    def test_the_reachability_check_is_one_frozen_prompt_with_the_same_command(self):
        driver = load("run_h2r2")
        self.assertEqual("Reply with exactly: H2_REACHABLE", driver.REACHABILITY_PROMPT)
        self.assertEqual("H2_REACHABLE", driver.REACHABILITY_TOKEN)
        self.assertEqual(120, driver.REACHABILITY_LIMIT_SECONDS)
        self.assertEqual(3, driver.MAX_ATTEMPTS)

    def test_every_reachability_check_is_recorded_with_a_timestamp(self):
        """F14: the probe is the run's own command, model and env, and every check is kept."""
        driver = load("run_h2r2")
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            env = driver.worker_env(profile_env_file(tmp))
            unreachable = Path(tmp) / "unreachable.py"
            unreachable.write_text(
                "import json, sys\n"
                "print(json.dumps({'type': 'error', "
                "'error': {'type': 'provider.no-route'}}))\n"
                "sys.exit(1)\n", encoding="utf-8")
            reachable = Path(tmp) / "reachable.py"
            reachable.write_text(
                "import json\n"
                "print(json.dumps({'type': 'text', "
                "'part': {'text': 'H2_REACHABLE'}}))\n", encoding="utf-8")
            bad = driver.reachability_probe(runs, "h2r2-f01-c", "worker", 1,
                                            (sys.executable, str(unreachable)), "the-model", env)
            good = driver.reachability_probe(runs, "h2r2-f01-c", "auditor", 1,
                                             (sys.executable, str(reachable)), "the-model", env)
            self.assertEqual("FAIL", bad["verdict"])
            self.assertIn("PROVIDER_ERROR:provider.no-route", bad["reasons"])
            self.assertEqual("PASS", good["verdict"])
            self.assertTrue(good["token_seen"])
            self.assertEqual(["the-model", driver.REACHABILITY_PROMPT], good["command"][-2:])
            log = [json.loads(line) for line in
                   (runs / "reachability-v2.jsonl").read_text().splitlines()]
            self.assertEqual(["FAIL", "PASS"], [entry["verdict"] for entry in log])
            for entry in log:
                self.assertTrue(entry["started_at"], entry)
                self.assertTrue(entry["finished_at"], entry)
                self.assertEqual(driver.REACHABILITY_LIMIT_SECONDS, entry["limit_seconds"])
                directory = Path(entry["directory"])
                self.assertTrue(directory.is_dir())
                self.assertEqual(".reachability", directory.parent.name)
            # the probe runs in a scratch dir outside the run dir; no run dir is created
            self.assertFalse((runs / "h2r2-f01-c").exists())

    def test_a_failed_reachability_check_blocks_without_consuming_an_attempt(self):
        driver = load("run_h2r2")
        with tempfile.TemporaryDirectory() as tmp:
            launched = Path(tmp) / "launched.marker"
            stub = Path(tmp) / "never.py"
            stub.write_text(f"open({str(launched)!r}, 'w').write('launched')\n", encoding="utf-8")

            def unreachable(purpose, attempt):
                return {"verdict": "FAIL", "reasons": ["EXIT:1"]}

            def must_not_audit(*args, **kwargs):
                raise AssertionError("the auditor ran on a blocked run")

            runs = Path(tmp) / "runs"
            blocked = driver.execute("h2r2-f01-c", runs,
                                     worker_command=(sys.executable, str(stub)),
                                     preflight=passing_preflight, auditor=must_not_audit,
                                     profile_env=profile_env_file(tmp), probe=unreachable,
                                     sandbox=StubSandbox(), auth=StubAuth())
            self.assertEqual("BLOCKED", blocked["verdict"])
            self.assertEqual(["PROVIDER_UNREACHABLE:EXIT:1"], blocked["reasons"])
            self.assertFalse(launched.exists())
            self.assertFalse((runs / "registry-v2.jsonl").exists())
            self.assertFalse((runs / "attempts-v2.jsonl").exists())
            self.assertFalse((runs / "h2r2-f01-c").exists())
            self.assertFalse((runs / ".locks" / "h2r2-f01-c.json").exists())
            # no attempt was consumed, so the same run id may be started later
            task, _ = task_pair("f01")
            patch = candidate_patch(tmp, task)
            accepted = driver.execute(
                "h2r2-f01-c", runs,
                worker_command=(sys.executable, str(stub_worker(tmp, "accept", patch))),
                preflight=passing_preflight, auditor=stub_auditor(),
                profile_env=profile_env_file(tmp), probe=passing_probe,
                sandbox=StubSandbox(), auth=StubAuth())
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("ACCEPT", accepted["verdict"], accepted["reasons"])
                self.assertEqual(1, accepted["attempts"])
                self.assertFalse((run_dir / "attempts").exists())
            finally:
                cleanup_run(run_dir)

    def test_a_provider_error_before_work_is_retried_on_a_fresh_run_dir(self):
        """F14: the attempt is archived with its hashes and the run is attempted again."""
        driver = load("run_h2r2")
        with tempfile.TemporaryDirectory() as tmp:
            task, _ = task_pair("f01")
            patch = candidate_patch(tmp, task)
            preflights = []

            def counting_preflight(run_dir, env_file, **kwargs):
                preflights.append(str(run_dir))
                return {"verdict": "PASS", "reasons": []}

            runs = Path(tmp) / "runs"
            result = driver.execute(
                "h2r2-f01-c", runs,
                worker_command=(sys.executable, str(stub_worker(tmp, "provider-once", patch))),
                preflight=counting_preflight, auditor=stub_auditor(),
                profile_env=profile_env_file(tmp), probe=passing_probe,
                sandbox=StubSandbox(), auth=StubAuth())
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("ACCEPT", result["verdict"], result["reasons"])
                self.assertEqual(2, result["attempts"])
                self.assertEqual(2, len(preflights))
                self.assertEqual("2", (Path(tmp) / "launches-provider-once.txt").read_text())
                archived = run_dir / "attempts" / "1"
                self.assertTrue(archived.is_dir())
                self.assertFalse((archived / "repo").exists())
                manifest = json.loads((archived / "attempt.json").read_text())
                self.assertEqual(("h2r2-f01-c", 1, "PROVIDER_FAILED_BEFORE_WORK", "BLOCKED"),
                                 (manifest["run_id"], manifest["attempt"], manifest["kind"],
                                  manifest["verdict"]))
                files = {path.relative_to(archived).as_posix() for path in archived.rglob("*")
                         if path.is_file()}
                self.assertEqual(files, set(manifest["artifacts"]) | {"attempt.json"})
                for rel, value in manifest["artifacts"].items():
                    self.assertEqual(value, digest((archived / rel).read_bytes()), rel)
                first = json.loads((archived / "run.json").read_text())
                worker = next(step for step in first["steps"] if step["step"] == "worker")
                self.assertEqual("BLOCKED", worker["status"])
                self.assertIn("provider.no-route", (archived / "events.jsonl").read_text())
                ledger = [json.loads(line) for line in
                          (runs / "attempts-v2.jsonl").read_text().splitlines()]
                self.assertEqual([1, 2], [line["attempt"] for line in ledger])
                self.assertEqual(["PROVIDER_FAILED_BEFORE_WORK", "TERMINAL"],
                                 [line["kind"] for line in ledger])
                self.assertEqual(digest((archived / "attempt.json").read_bytes()),
                                 ledger[0]["manifest_sha256"])
                self.assertEqual("attempts/1", ledger[0]["archive"])
                line = json.loads((runs / "registry-v2.jsonl").read_text().splitlines()[0])
                self.assertEqual((2, 2, "ACCEPT", "PASS"),
                                 (line["attempt"], line["attempts"], line["final_verdict"],
                                  line["audit_verdict"]))
                self.assertEqual(line["artifacts"], ledger[1]["artifacts"])
                self.assertIn("attempts/1/attempt.json", line["artifacts"])
            finally:
                cleanup_run(run_dir)

    def test_three_before_work_failures_block_the_run_and_stop_retrying(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "provider-always")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("BLOCKED", result["verdict"])
                self.assertEqual("BLOCKED", result["final_verdict"])
                self.assertEqual(3, result["attempts"])
                self.assertIn("PROVIDER_FAILED_BEFORE_WORK", result["reasons"][0])
                self.assertEqual("3", (Path(tmp) / "launches-provider-always.txt").read_text())
                self.assertEqual(["1", "2", "3"],
                                 sorted(path.name for path in (run_dir / "attempts").iterdir()))
                for number in (1, 2, 3):
                    manifest = json.loads(
                        (run_dir / "attempts" / str(number) / "attempt.json").read_text())
                    self.assertEqual(number, manifest["attempt"])
                ledger = [json.loads(line) for line in
                          (runs / "attempts-v2.jsonl").read_text().splitlines()]
                self.assertEqual([1, 2, 3], [line["attempt"] for line in ledger])
                line = json.loads((runs / "registry-v2.jsonl").read_text().splitlines()[0])
                self.assertEqual(("BLOCKED", "BLOCKED", 3, 3),
                                 (line["verdict"], line["final_verdict"], line["attempt"],
                                  line["attempts"]))
                self.assertIn("PROVIDER_FAILED_BEFORE_WORK", line["reason"])
                self.assertEqual("h2r2-f01-v", load("run_h2r2").next_run_id(runs))
                again = load("run_h2r2").execute("h2r2-f01-c", runs,
                                                 profile_env=profile_env_file(tmp))
                self.assertEqual("RUN_ALREADY_REGISTERED", again["reason"])
            finally:
                cleanup_run(run_dir)

    def test_a_provider_error_after_a_tool_call_is_invalid_and_never_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver, runs, result = execute_stub(tmp, "provider-after-tool")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("INVALID", result["verdict"])
                self.assertEqual("INVALID", result["final_verdict"])
                self.assertEqual(1, result["attempts"])
                self.assertIn("WORKER_ERROR_EVENT", result["reasons"])
                self.assertFalse((run_dir / "attempts").exists())
                self.assertEqual("1", (Path(tmp) / "launches-provider-after-tool.txt").read_text())
                line = json.loads((runs / "registry-v2.jsonl").read_text().splitlines()[0])
                self.assertEqual(("INVALID", 1, 1),
                                 (line["final_verdict"], line["attempt"], line["attempts"]))
                ledger = [json.loads(text) for text in
                          (runs / "attempts-v2.jsonl").read_text().splitlines()]
                self.assertEqual(["TERMINAL"], [entry["kind"] for entry in ledger])
                self.assertEqual(1, len(ledger))
            finally:
                cleanup_run(run_dir)

    def test_a_blocked_audit_is_retried_and_keeps_the_mechanical_verdict(self):
        """F14: the auditor has its own counter; its blocked attempt is archived, not invented."""
        calls = []

        def flaky_audit(run_dir, plan_run, task, *, launch, command, env, limit_seconds,
                        events_path=None, stderr_path=None):
            calls.append(1)
            audit_dir = Path(run_dir) / "audit"
            audit_dir.mkdir(exist_ok=True)
            if len(calls) == 1:
                (audit_dir / "events.jsonl").write_text(
                    json.dumps({"type": "error",
                                "error": {"type": "provider.no-route"}}) + "\n",
                    encoding="utf-8")
                return {"verdict": "BLOCKED", "reasons": ["AUDIT_EXIT:1"], "leakage": [],
                        "launch": {"returncode": 1, "timed_out": False}}
            (audit_dir / "audit.json").write_text(
                json.dumps({"correctness": "PASS", "invalid_completion": False,
                            "findings": []}), encoding="utf-8")
            return {"verdict": "PASS", "reasons": [], "leakage": []}

        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "accept", auditor=flaky_audit)
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual(2, len(calls))
                self.assertEqual("ACCEPT", result["verdict"], result["reasons"])
                self.assertEqual("PASS", result["audit_verdict"])
                archived = run_dir / "attempts" / "audit-1"
                self.assertTrue((archived / "events.jsonl").is_file())
                manifest = json.loads((archived / "attempt.json").read_text())
                self.assertEqual(("PROVIDER_FAILED_BEFORE_WORK", 1),
                                 (manifest["kind"], manifest["attempt"]))
                record = json.loads((run_dir / "run.json").read_text())
                step = next(item for item in record["steps"] if item["step"] == "audit")
                self.assertEqual(1, len(step["attempts"]))
                self.assertEqual("attempts/audit-1", step["attempts"][0]["archive"])
            finally:
                cleanup_run(run_dir)

    def test_a_blocked_audit_reachability_check_is_archived_as_a_probe(self):
        """F20 P3-2 / §6.1: a blocked audit attempt leaves its pre-launch probe.json behind."""
        def flaky_probe(purpose, attempt):
            if purpose == "auditor" and attempt == 1:
                return {"verdict": "BLOCKED", "reasons": [], "blocked": "PROVIDER_UNREACHABLE"}
            return passing_probe(purpose, attempt)

        with tempfile.TemporaryDirectory() as tmp:
            driver, runs, result = execute_stub(tmp, "accept", probe=flaky_probe)
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("ACCEPT", result["verdict"], result["reasons"])
                archived = run_dir / "attempts" / "audit-1" / "probe.json"
                self.assertTrue(archived.is_file())
                probe = json.loads(archived.read_text())
                self.assertEqual(("audit_reachability", "BLOCKED"),
                                 (probe["step"], probe["verdict"]))
                self.assertEqual("PROVIDER_UNREACHABLE", probe["reasons"][0])
                record = json.loads((run_dir / "run.json").read_text())
                step = next(item for item in record["steps"] if item["step"] == "audit")
                self.assertEqual("attempts/audit-1", step["attempts"][0]["archive"])
                self.assertEqual(digest(archived.read_bytes()),
                                 step["attempts"][0]["probe_sha256"])
            finally:
                cleanup_run(run_dir)

    def test_a_blocked_audit_confinement_check_is_archived_as_a_probe(self):
        """§6.1: the confinement self-test blocks before the auditor runs, and is archived too."""
        class FlakyConfinement(StubSandbox):
            calls = 0

            def self_test(self, profile_path, launch, planted, python=None, token=None):
                if "audit" in Path(launch).parts:
                    FlakyConfinement.calls += 1
                    if FlakyConfinement.calls == 1:
                        return {"verdict": "FAIL", "reasons": ["PYTHON_READ_NOT_DENIED"],
                                "profile_sha256": digest(Path(profile_path).read_bytes())}
                return super().self_test(profile_path, launch, planted, python, token)

        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "accept", sandbox=FlakyConfinement())
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("ACCEPT", result["verdict"], result["reasons"])
                probe_path = run_dir / "attempts" / "audit-1" / "probe.json"
                self.assertTrue(probe_path.is_file())
                probe = json.loads(probe_path.read_text())
                self.assertEqual(("audit_confinement", "BLOCKED"),
                                 (probe["step"], probe["verdict"]))
                self.assertEqual("SANDBOX_NOT_CONFINING",
                                 probe["reasons"][0].split(":")[0])
                record = json.loads((run_dir / "run.json").read_text())
                step = next(item for item in record["steps"] if item["step"] == "audit")
                self.assertEqual("SANDBOX_NOT_CONFINING",
                                 step["attempts"][0]["reasons"][0].split(":")[0])
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
            # T34: the second arm of a task waits for the first arm to be REGISTERED, and that is
            # the same-task refusal (it is also the first run in plan order that has not started).
            self.assertEqual({"outcome": "REFUSED", "run_id": "h2r2-f01-v",
                              "reason": "SAME_TASK_ARM_NOT_REGISTERED:h2r2-f01-c"}, refused)
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

            def failed_preflight(run_dir, env_file, **kwargs):
                return {"verdict": "FAIL", "reasons": ["CONFIG_SOURCES_MISMATCH"]}

            def must_not_run(*args, **kwargs):
                raise AssertionError("the auditor ran on a blocked run")

            runs = Path(tmp) / "runs"
            result = driver.execute("h2r2-f01-c", runs,
                                    worker_command=(sys.executable, str(stub)),
                                    preflight=failed_preflight, auditor=must_not_run,
                                    profile_env=profile_env_file(tmp),
                                    sandbox=StubSandbox(), auth=StubAuth())
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("BLOCKED", result["verdict"])
                self.assertEqual("BLOCKED", result["final_verdict"])
                self.assertEqual(["PREFLIGHT_FAIL:CONFIG_SOURCES_MISMATCH"], result["reasons"])
                self.assertFalse(marker.exists())
                record = json.loads((run_dir / "run.json").read_text())
                self.assertEqual(["prepare", "home", "preflight", "registry"],
                                 [step["step"] for step in record["steps"]])
                self.assertEqual("BLOCKED", record["steps"][2]["status"])
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


class BoundedConcurrency(unittest.TestCase):
    """T34: two runs at a time, started in plan order, each its own `run` child process."""

    def plan_order(self):
        return [run["run_id"] for run in load("run_h2r2").plan_runs()]

    def live_lock(self, runs, run_id, pid=None):
        (Path(runs) / ".locks").mkdir(parents=True, exist_ok=True)
        path = Path(runs) / ".locks" / f"{run_id}.json"
        path.write_text(json.dumps({"run_id": run_id, "pid": pid or os.getpid(),
                                    "started_at": "2026-10-23T00:00:00+00:00"}) + "\n",
                        encoding="utf-8")
        return path

    def test_max_parallel_is_frozen_four_and_the_three_refusals_are_explicit(self):
        driver = load("run_h2r2")
        self.assertEqual(4, driver.MAX_PARALLEL)
        planned = driver.plan_runs()

        def reason(runs, run_id, entries=None):
            plan_run = next(run for run in planned if run["run_id"] == run_id)
            return driver.refusal(runs, plan_run, planned, entries or {})

        def registered(*run_ids):
            return "".join(json.dumps({"run_id": run_id, "task_id": run_id.split("-")[1],
                                       "arm": "control", "final_verdict": "ACCEPT"}) + "\n"
                           for run_id in run_ids)

        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            registry = runs / "registry-v2.jsonl"
            self.assertIsNone(reason(runs, "h2r2-f01-c"))
            # (b) the second arm waits for the first, which is also the first unstarted run.
            self.assertEqual("SAME_TASK_ARM_NOT_REGISTERED:h2r2-f01-c",
                             reason(runs, "h2r2-f01-v"))
            # (d) a later task may not start before the previous run started at all.
            self.assertEqual("PREDECESSOR_NOT_STARTED:h2r2-f01-c", reason(runs, "h2r2-f02-v"))
            # The first two tasks are done; the frontier is f03-c.
            registry.write_text(registered("h2r2-f01-c", "h2r2-f01-v",
                                           "h2r2-f02-v", "h2r2-f02-c"), encoding="utf-8")
            entries = driver.read_registry(runs)
            self.assertIsNone(reason(runs, "h2r2-f03-c", entries))
            self.assertEqual("SAME_TASK_ARM_NOT_REGISTERED:h2r2-f03-c",
                             reason(runs, "h2r2-f03-v", entries))
            self.assertEqual("PREDECESSOR_NOT_STARTED:h2r2-f03-c",
                             reason(runs, "h2r2-f04-v", entries))
            # (c) four live lock holders fill every slot of this runs root.
            for run_id in ("h2r2-f03-c", "h2r2-f03-v", "h2r2-f04-v", "h2r2-f04-c"):
                self.live_lock(runs, run_id)
            self.assertEqual("PARALLEL_LIMIT:4", reason(runs, "h2r2-f05-c", entries))
            refused = driver.execute("h2r2-f05-c", runs, profile_env=profile_env_file(tmp))
            self.assertEqual({"outcome": "REFUSED", "run_id": "h2r2-f05-c",
                              "reason": "PARALLEL_LIMIT:4"}, refused)
            self.assertFalse((runs / "h2r2-f05-c").exists())

    def test_the_scheduler_keeps_four_alive_and_starts_in_plan_order(self):
        driver = load("run_h2r2")
        order = self.plan_order()
        plan = {run["run_id"]: run for run in driver.plan_runs()}
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            result = driver.schedule(runs, spawn=scheduler_spawner(tmp, runs, delay=0.15),
                                     sleep=time.sleep, poll=0.01)
            self.assertEqual("COMPLETE", result["status"], result["stopped_by"])
            self.assertEqual(order, result["started"])
            self.assertEqual([], result["left"])
            self.assertEqual(4, result["max_parallel"])
            events = [json.loads(line) for line in
                      (runs / "child-events.jsonl").read_text().splitlines()]
            spans = {}
            for item in events:
                spans.setdefault(item["run_id"], {})[item["event"]] = item["time"]
            starts = [item for item in events if item["event"] == "start"]
            self.assertEqual(order, [item["run_id"] for item in starts])
            for item in starts:
                # T35: every run that had started and not yet ended at this instant, including the
                # ones whose own start line is written a moment later.
                alive = [run_id for run_id, span in spans.items()
                         if span["start"] <= item["time"]
                         and ("end" not in span or item["time"] < span["end"])]
                self.assertLessEqual(len(alive), driver.MAX_PARALLEL, alive)
                asleep = [run_id for run_id, span in spans.items()
                          if span["start"] <= item["time"] and "end" not in span]
                self.assertLessEqual(len(asleep), driver.MAX_PARALLEL, asleep)
            overlapping = []
            for index, first in enumerate(order):
                for second in order[index + 1:]:
                    a, b = spans[first], spans[second]
                    if a["start"] < b["end"] and b["start"] < a["end"]:
                        overlapping.append((first, second))
                        self.assertNotEqual(plan[first]["task_id"], plan[second]["task_id"])
            self.assertTrue(overlapping, "the schedule never ran two runs at once")
            for task_id in {run["task_id"] for run in driver.plan_runs()}:
                first, second = [run_id for run_id in order
                                 if plan[run_id]["task_id"] == task_id]
                self.assertLess(spans[first]["end"], spans[second]["start"], task_id)
            log = [json.loads(line) for line in
                   (runs / "scheduler-v2.jsonl").read_text().splitlines()]
            self.assertEqual(2 * len(order), len(log))
            for line in log:
                self.assertIn(line["event"], ("start", "end"))
                self.assertTrue(line["at"])
                self.assertTrue(line["pid"])
                self.assertTrue(line["run_id"])
            self.assertEqual({"ACCEPT"}, {line["outcome"] for line in log
                                          if line["event"] == "end"})
            # a second invocation never re-runs a registered run
            again = driver.schedule(runs, spawn=scheduler_spawner(tmp, runs, delay=0.01),
                                    sleep=time.sleep, poll=0.01)
            self.assertEqual(("COMPLETE", [], []),
                             (again["status"], again["started"], again["left"]))

    def test_a_reachability_blocked_run_is_retried_in_plan_position_and_frees_its_slot(self):
        driver = load("run_h2r2")
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            result = driver.schedule(
                runs, spawn=scheduler_spawner(tmp, runs,
                                              modes={"h2r2-f01-c": ["blocked", "ok"]},
                                              delay=0.05),
                sleep=clock.sleep, clock=clock.clock, jitter=lambda: 0.0, poll=0.01)
            try:
                self.assertEqual("COMPLETE", result["status"], result["stopped_by"])
                self.assertEqual(["h2r2-f01-c", "h2r2-f01-c", "h2r2-f01-v"],
                                 result["started"][:3])
                log = [json.loads(line) for line in
                       (runs / "scheduler-v2.jsonl").read_text().splitlines()]
                first = [line for line in log if line["run_id"] == "h2r2-f01-c"]
                self.assertEqual(["start", "end", "wait", "start", "end"],
                                 [line["event"] for line in first])
                self.assertEqual("NOT_REGISTERED:BLOCKED", first[1]["outcome"])
                self.assertEqual(["PROVIDER_UNREACHABLE:EXIT:1"], first[1]["reasons"])
                self.assertEqual(60.0, first[2]["seconds"])
                self.assertEqual("ACCEPT", first[4]["outcome"])
            finally:
                cleanup_run(runs / "h2r2-f01-c")

    def test_the_backoff_is_exponential_capped_and_jittered(self):
        driver = load("run_h2r2")
        self.assertEqual((60, 900, 6),
                         (driver.SCHEDULER_BACKOFF_FIRST_SECONDS,
                          driver.SCHEDULER_BACKOFF_CAP_SECONDS, driver.SCHEDULER_REQUEUES))
        self.assertEqual([60, 120, 240, 480, 900, 900],
                         [driver.backoff_delay(number, jitter=lambda: 0.0)
                          for number in range(1, 7)])
        # jitter spreads a wait around its base and never pushes it past the cap
        self.assertGreater(driver.backoff_delay(1, jitter=lambda: 1.0), 60)
        self.assertLess(driver.backoff_delay(1, jitter=lambda: -1.0), 60)
        self.assertEqual(driver.SCHEDULER_BACKOFF_CAP_SECONDS,
                         driver.backoff_delay(6, jitter=lambda: 1.0))
        for _ in range(20):
            spread = driver.scheduler_jitter()
            self.assertLessEqual(abs(spread), driver.SCHEDULER_BACKOFF_JITTER)

    def test_a_blocked_before_work_run_is_requeued_with_growing_waits_then_runs(self):
        """T35: two provider blocks, then success -- re-queued in place after 60 s and 120 s."""
        driver = load("run_h2r2")
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            result = driver.schedule(
                runs, spawn=scheduler_spawner(tmp, runs,
                                              modes={"h2r2-f01-c": ["blocked", "blocked", "ok"]},
                                              delay=0.02),
                sleep=clock.sleep, clock=clock.clock, jitter=lambda: 0.0, poll=0.01)
            try:
                self.assertEqual("COMPLETE", result["status"], result["stopped_by"])
                self.assertEqual(2, result["requeues"]["h2r2-f01-c"])
                self.assertEqual(["h2r2-f01-c"] * 3, result["started"][:3])
                self.assertEqual("h2r2-f01-v", result["started"][3])
                log = [json.loads(line) for line in
                       (runs / "scheduler-v2.jsonl").read_text().splitlines()]
                waits = [line for line in log if line["event"] == "wait"]
                self.assertEqual([60.0, 120.0], [line["seconds"] for line in waits])
                self.assertEqual([1, 2], [line["requeue"] for line in waits])
                self.assertEqual({"h2r2-f01-c"}, {line["run_id"] for line in waits})
                self.assertTrue(all(line["at"] for line in waits))
                first = [line for line in log if line["run_id"] == "h2r2-f01-c"]
                self.assertEqual(["start", "end", "wait", "start", "end", "wait",
                                  "start", "end"], [line["event"] for line in first])
                self.assertEqual("ACCEPT", first[-1]["outcome"])
            finally:
                cleanup_run(runs / "h2r2-f01-c")

    def test_the_scheduler_stops_at_the_requeue_budget_and_lists_the_run(self):
        driver = load("run_h2r2")
        order = self.plan_order()
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            result = driver.schedule(
                runs, spawn=scheduler_spawner(tmp, runs, modes={"h2r2-f01-c": "blocked"},
                                              delay=0.02),
                sleep=clock.sleep, clock=clock.clock, jitter=lambda: 0.0, poll=0.01)
            self.assertEqual("STOPPED", result["status"])
            self.assertEqual("BLOCKED_BEFORE_WORK:h2r2-f01-c", result["stopped_by"])
            self.assertEqual(driver.SCHEDULER_REQUEUES + 1, len(result["started"]))
            self.assertEqual(["h2r2-f01-c"] * (driver.SCHEDULER_REQUEUES + 1),
                             result["started"])
            self.assertEqual(driver.SCHEDULER_REQUEUES, result["requeues"]["h2r2-f01-c"])
            self.assertEqual(order, result["left"])
            self.assertFalse((runs / "registry-v2.jsonl").exists())
            log = [json.loads(line) for line in
                   (runs / "scheduler-v2.jsonl").read_text().splitlines()]
            waits = [line for line in log if line["event"] == "wait"]
            self.assertEqual([60.0, 120.0, 240.0, 480.0, 900.0, 900.0],
                             [line["seconds"] for line in waits])
            self.assertEqual(2 * (driver.SCHEDULER_REQUEUES + 1) + driver.SCHEDULER_REQUEUES,
                             len(log))
            self.assertEqual({"NOT_REGISTERED:BLOCKED"},
                             {line["outcome"] for line in log if line["event"] == "end"})

    def test_a_registered_before_work_block_is_never_requeued(self):
        """§6.1's three-attempt BLOCKED is a registry line, and T35 never re-runs one."""
        driver = load("run_h2r2")
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            (runs / "registry-v2.jsonl").write_text(json.dumps(
                {"run_id": "h2r2-f01-c", "task_id": "f01", "arm": "control",
                 "verdict": "BLOCKED", "final_verdict": "BLOCKED",
                 "reason": "PROVIDER_FAILED_BEFORE_WORK:EXIT:1",
                 "started_at": "2026-10-23T00:00:00+00:00",
                 "finished_at": "2026-10-23T00:01:00+00:00"}) + "\n", encoding="utf-8")
            result = driver.schedule(runs, spawn=scheduler_spawner(tmp, runs, delay=0.02),
                                     sleep=time.sleep, poll=0.01)
            self.assertEqual("COMPLETE", result["status"], result["stopped_by"])
            self.assertNotIn("h2r2-f01-c", result["started"])
            self.assertEqual({}, result["requeues"])
            self.assertEqual([], result["left"])

    def test_one_frozen_model_with_no_failover(self):
        """T35: a second model is refused before anything is spawned -- never substituted."""
        driver = load("run_h2r2")
        planned = driver.plan_runs()
        self.assertEqual("opencode-go/deepseek-v4.1-flash", driver.FROZEN_MODEL)
        self.assertEqual({driver.FROZEN_MODEL}, {run["model"] for run in planned})
        self.assertEqual(driver.FROZEN_MODEL, driver.frozen_model(planned))
        with self.assertRaises(ValueError) as caught:
            driver.frozen_model([dict(planned[0], model="other/model")])
        self.assertIn("MODEL_NOT_FROZEN:other/model", str(caught.exception))
        with self.assertRaises(ValueError):
            driver.frozen_model([dict(planned[0]),
                                 dict(planned[1], model="other/model")])
        with self.assertRaises(ValueError):
            driver.frozen_model([dict(planned[0], model=None)])
        with tempfile.TemporaryDirectory() as tmp:
            # A plan with a second model stops both entry points before any process exists.
            root = Path(tmp) / "root"
            plan_path = root / H2_REL / "freeze-v2" / "run-plan-v2.json"
            plan_path.parent.mkdir(parents=True)
            plan_path.write_text(json.dumps(
                {"runs": [dict(planned[0], model="other/model"), *planned[1:]]}),
                encoding="utf-8")
            runs = Path(tmp) / "runs"
            with self.assertRaises(ValueError):
                driver.execute("h2r2-f01-c", runs, root=root,
                               profile_env=profile_env_file(tmp))
            self.assertFalse((runs / "h2r2-f01-c").exists())
            with self.assertRaises(ValueError):
                driver.schedule(runs, root=root, spawn=lambda run_id: self.fail(
                    f"spawned {run_id} with an unfrozen model"))
            self.assertFalse((runs / "registry-v2.jsonl").exists())

    def test_every_worker_and_auditor_launch_carries_the_frozen_model(self):
        """Both argv of a run take the model from the plan row, which equals FROZEN_MODEL."""
        driver = load("run_h2r2")
        audit_module = load("run_audit_v2")
        real_launch = driver.launch
        launches = []

        def recording_launch(argv, cwd, env, limit, stdout_path, stderr_path):
            launches.append(list(argv))
            if argv[-1] == driver.LAUNCH_PROMPT:
                return real_launch(argv, cwd, env, limit, stdout_path, stderr_path)
            # The auditor never needs a real process here: a tool call is enough for the driver's
            # before-work rule, and the argv is what this test reads.
            Path(stdout_path).parent.mkdir(parents=True, exist_ok=True)
            Path(stdout_path).write_text(json.dumps(
                {"type": "tool_use", "sessionID": "ses_stub_audit",
                 "part": {"tool": "read", "state": {"status": "completed",
                                                    "input": {"path": "report.md"}}}}) + "\n",
                encoding="utf-8")
            Path(stderr_path).write_text("", encoding="utf-8")
            return {"returncode": 0, "timed_out": False, "command": list(argv)}

        with tempfile.TemporaryDirectory() as tmp:
            task, _ = task_pair("f01")
            patch = candidate_patch(tmp, task)
            runs = Path(tmp) / "runs"
            driver.launch = recording_launch
            try:
                result = driver.execute(
                    "h2r2-f01-c", runs,
                    worker_command=(sys.executable, str(stub_worker(tmp, "accept", patch))),
                    preflight=passing_preflight, auditor=None,
                    profile_env=profile_env_file(tmp), probe=passing_probe,
                    sandbox=StubSandbox(), auth=StubAuth())
            finally:
                driver.launch = real_launch
                cleanup_run(runs / "h2r2-f01-c")
            self.assertEqual("ACCEPT", result["verdict"], result["reasons"])
            worker = [argv for argv in launches if argv[-1] == driver.LAUNCH_PROMPT]
            auditor = [argv for argv in launches if argv[-1] == audit_module.AUDIT_PROMPT]
            self.assertEqual(1, len(worker))
            self.assertEqual(1, len(auditor))
            self.assertEqual(driver.FROZEN_MODEL, worker[0][-2])
            self.assertEqual(driver.FROZEN_MODEL, auditor[0][-2])
            # Both launches are the same command plus the model plus their own prompt.
            self.assertEqual(worker[0][:-2], auditor[0][:-2])
            self.assertEqual(driver.LAUNCH_PROMPT, worker[0][-1])
            self.assertEqual(audit_module.AUDIT_PROMPT, auditor[0][-1])

    def test_a_killed_scheduler_leaves_a_started_run_to_the_interrupted_rule(self):
        """The scheduler never cleans up after itself: an interrupted run is the driver's rule."""
        driver = load("run_h2r2")

        class Killed(Exception):
            pass

        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            spawner = scheduler_spawner(tmp, runs, delay=30)
            started = {}

            def spawn_then_die(run_id):
                started[run_id] = spawner(run_id)
                raise Killed()

            with self.assertRaises(Killed):
                driver.schedule(runs, spawn=spawn_then_die, sleep=lambda seconds: None,
                                poll=0.01)
            lock = runs / ".locks" / "h2r2-f01-c.json"
            for _ in range(250):
                if lock.is_file():
                    break
                time.sleep(0.02)
            self.assertTrue(lock.is_file())
            child = started["h2r2-f01-c"]["process"]
            child.kill()
            child.wait()
            result = driver.execute("h2r2-f01-c", runs, profile_env=profile_env_file(tmp))
            self.assertEqual("RUN_ALREADY_STARTED", result["reason"])
            line = json.loads((runs / "registry-v2.jsonl").read_text().splitlines()[-1])
            self.assertEqual(("INVALID", "INTERRUPTED", "SECOND_START_ATTEMPT_REFUSED"),
                             (line["verdict"], line["reason"], line["registered_by"]))

    def test_concurrent_registry_appends_are_well_formed_lines(self):
        driver = load("run_h2r2")
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            writer = Path(tmp) / "concurrent-writer.py"
            writer.write_text(CONCURRENT_WRITER, encoding="utf-8")
            registry = runs / "registry-v2.jsonl"
            writers = [subprocess.Popen([sys.executable, str(writer), str(FZ), str(registry),
                                         f"writer{index}", "20"], stdin=subprocess.DEVNULL)
                       for index in range(6)]
            self.assertEqual([0] * 6, [process.wait() for process in writers])
            lines = registry.read_text().splitlines()
            self.assertEqual(120, len(lines))
            entries = driver.read_registry(runs)
            self.assertEqual(120, len(entries))
            for line in lines:
                self.assertEqual(4096, len(json.loads(line)["reason"]))
            self.assertEqual({f"writer{index}-{number}"
                              for index in range(6) for number in range(20)}, set(entries))

    def test_status_names_the_runs_that_are_in_progress(self):
        driver = load("run_h2r2")
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            self.live_lock(runs, "h2r2-f01-c")
            state = driver.status(runs)
            self.assertEqual("IN_PROGRESS", state["runs"][0]["state"])
            self.assertEqual(["h2r2-f01-c"], state["in_progress"])
            self.assertEqual(driver.MAX_PARALLEL, state["max_parallel"])
            self.assertEqual("h2r2-f01-c", state["next"])
            self.assertEqual("NOT_STARTED", state["runs"][1]["state"])
            self.assertEqual(0, state["registered"])

    def test_overlap_is_recorded_in_the_run_and_reported_by_the_aggregate(self):
        driver = load("run_h2r2")
        aggregate = load("aggregate_runs")
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            runs.mkdir()
            rows = [
                {"run_id": "h2r2-f01-c", "task_id": "f01", "arm": "control",
                 "final_verdict": "ACCEPT", "started_at": "2026-10-23T10:00:00+00:00",
                 "finished_at": "2026-10-23T10:10:00+00:00"},
                {"run_id": "h2r2-f02-v", "task_id": "f02", "arm": "variant",
                 "final_verdict": "ACCEPT", "started_at": "2026-10-23T10:05:00+00:00",
                 "finished_at": "2026-10-23T10:20:00+00:00"},
                {"run_id": "h2r2-f03-c", "task_id": "f03", "arm": "control",
                 "final_verdict": "ACCEPT", "started_at": "2026-10-23T10:20:00+00:00",
                 "finished_at": "2026-10-23T10:30:00+00:00"},
            ]
            (runs / "registry-v2.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            self.assertEqual(["h2r2-f02-v"],
                             driver.overlap_ids(runs, "h2r2-f01-c",
                                                "2026-10-23T10:00:00+00:00",
                                                "2026-10-23T10:10:00+00:00"))
            self.assertEqual(["h2r2-f01-c"],
                             driver.overlap_ids(runs, "h2r2-f02-v",
                                                "2026-10-23T10:05:00+00:00",
                                                "2026-10-23T10:20:00+00:00"))
            self.assertEqual([["h2r2-f01-c", "h2r2-f02-v"]],
                             aggregate.overlap_pairs(aggregate.read_registry(runs)))
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "noop")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("REJECT", result["verdict"], result["reasons"])
                record = json.loads((run_dir / "run.json").read_text())
                self.assertEqual([], record["concurrent_with"])
                self.assertTrue(record["started_at"])
                self.assertTrue(record["finished_at"])
            finally:
                cleanup_run(run_dir)

    def test_the_preflight_port_is_per_run_and_a_collision_retried(self):
        driver = load("run_h2r2")
        self.assertEqual(3, driver.SERVICE_PORT_ATTEMPTS)
        self.assertTrue(1 <= driver.free_port() <= 65535)
        with tempfile.TemporaryDirectory() as tmp:
            ports = iter([11001, 11002, 11003])
            calls = []

            def colliding(run_dir, env_file, *, home=None, env=None, port=None):
                calls.append(port)
                if len(calls) < 3:
                    return {"verdict": "FAIL", "reasons": ["SERVICE_PORT_IN_USE"]}
                return {"verdict": "PASS", "reasons": []}

            verdict, attempts = driver.attest(colliding, Path(tmp), Path(tmp) / "env.sh",
                                              tmp, {}, choose_port=lambda: next(ports))
            self.assertEqual("PASS", verdict["verdict"])
            self.assertEqual([11001, 11002, 11003], calls)
            self.assertEqual([1, 2, 3], [item["attempt"] for item in attempts])

            def always_colliding(run_dir, env_file, *, home=None, env=None, port=None):
                return {"verdict": "FAIL", "reasons": ["PREFLIGHT_SERVICE_PORT_IN_USE"]}

            verdict, attempts = driver.attest(always_colliding, Path(tmp),
                                              Path(tmp) / "env.sh", tmp, {})
            self.assertEqual("FAIL", verdict["verdict"])
            self.assertEqual(driver.SERVICE_PORT_ATTEMPTS, len(attempts))

            plain = mock.Mock(return_value={"verdict": "PASS", "reasons": []})
            verdict, attempts = driver.attest(plain, Path(tmp), Path(tmp) / "env.sh", tmp, {})
            self.assertEqual(1, plain.call_count)
            self.assertIsNone(attempts[0]["port"])
        with tempfile.TemporaryDirectory() as tmp:
            calls = []

            def flaky_service(run_dir, env_file, *, home=None, env=None, port=None):
                calls.append(port)
                if len(calls) == 1:
                    return {"verdict": "FAIL", "reasons": ["SERVICE_PORT_IN_USE"]}
                return {"verdict": "PASS", "reasons": []}

            _, runs, result = execute_stub(tmp, "noop", preflight=flaky_service)
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("REJECT", result["verdict"], result["reasons"])
                self.assertEqual(2, len(calls))
                record = json.loads((run_dir / "run.json").read_text())
                self.assertEqual([1, 2], [item["attempt"]
                                          for item in record["preflight"]["attempts"]])
                step = next(item for item in record["steps"] if item["step"] == "preflight")
                self.assertEqual("PASS", step["status"])
                self.assertEqual(2, step["attempts"])
            finally:
                cleanup_run(run_dir)

    def test_the_run_plan_subcommand_exposes_only_the_runs_root(self):
        help_text = subprocess.run([sys.executable, str(FZ / "run_h2r2.py"), "run-plan",
                                    "--help"], capture_output=True, text=True).stdout
        options = {token for token in help_text.split() if token.startswith("--")}
        self.assertEqual({"--runs-root", "--help"}, options)


class AggregateRunsV2(unittest.TestCase):
    """T30 / F20 P3-4: the §7 token comes from the runs root, never from "registered=20"."""

    def build(self, tmp, *, overrides=None, audits=None, omit=(), attempt_rows=()):
        aggregate = load("aggregate_runs")
        plan = aggregate.planned_runs()
        root = Path(tmp) / "runs"
        root.mkdir()
        lines = []
        for plan_run in plan:
            run_id = plan_run["run_id"]
            if run_id in omit:
                continue
            spec = dict((overrides or {}).get(run_id, {}))
            final = spec.setdefault("final_verdict", "ACCEPT")
            lines.append({"run_id": run_id, "task_id": plan_run["task_id"],
                          "arm": plan_run["arm"], "verdict": spec.get("verdict", "ACCEPT"),
                          "audit_verdict": spec.get("audit_verdict", "PASS"),
                          "final_verdict": final, "reason": spec.get("reason")})
            if final in ("ACCEPT", "REJECT"):
                audit_dir = root / run_id / "audit"
                audit_dir.mkdir(parents=True)
                item = {"correctness": "PASS", "invalid_completion": False,
                        "findings": [{"id": f"{run_id}-finding", "severity": "P3",
                                      "category": "HV1", "location": "report.md"}]}
                item.update((audits or {}).get(run_id, {}))
                (audit_dir / "audit.json").write_text(json.dumps(item), encoding="utf-8")
        (root / "registry-v2.jsonl").write_text(
            "".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
        if attempt_rows:
            (root / "attempts-v2.jsonl").write_text(
                "".join(json.dumps(row) + "\n" for row in attempt_rows), encoding="utf-8")
        return aggregate, root, plan

    def test_a_complete_non_null_runs_root_decides_disclosure_safe_with_its_exact_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            aggregate, root, _ = self.build(tmp)
            result = aggregate.aggregate(root)
            self.assertEqual("DISCLOSURE_SAFE", result["result"])
            self.assertEqual("NO_COST_OBSERVED:COMPLETE_COVERAGE+NON_NULL_DIFFERENCE+S1_SATISFIED",
                             result["decided_by"])
            self.assertEqual((10, 10), (result["usable_pairs"], result["planned_pairs"]))
            self.assertEqual([], result["invalid"])
            self.assertEqual([], result["blocked"])
            self.assertTrue(result["s1"]["satisfied"])
            # S5's judgement is not this program's to make, and it says so.
            self.assertEqual(["S5"], result["pending_rules"])
            self.assertEqual("runs_root_mechanical", result["result_scope"])

    def test_one_audited_missed_guidance_decides_disclosure_has_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            aggregate, root, _ = self.build(tmp, audits={
                "h2r2-f03-v": {"findings": [{"id": "miss-1", "severity": "P1",
                                             "category": "MISSED_GUIDANCE",
                                             "location": "report.md"}]}})
            result = aggregate.aggregate(root)
            self.assertEqual("DISCLOSURE_HAS_COST", result["result"])
            self.assertEqual("S2_MISSED_GUIDANCE_GE_1:h2r2-f03-v:miss-1", result["decided_by"])
            pair = next(item for item in result["pairs"] if item["task_id"] == "f03")
            self.assertEqual(["miss-1"], pair["variant"]["missed_guidance"])

    def test_a_worse_variant_correctness_or_invalid_completion_is_a_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            aggregate, root, _ = self.build(tmp, audits={
                "h2r2-f04-v": {"correctness": "FAIL"}})
            result = aggregate.aggregate(root)
            self.assertEqual("DISCLOSURE_HAS_COST", result["result"])
            self.assertEqual("S4_TREATMENT_ONLY_CORRECTNESS:f04", result["decided_by"])
        with tempfile.TemporaryDirectory() as tmp:
            aggregate, root, _ = self.build(tmp, audits={
                "h2r2-f05-v": {"invalid_completion": True}})
            result = aggregate.aggregate(root)
            self.assertEqual("DISCLOSURE_HAS_COST", result["result"])
            self.assertEqual("S3_TREATMENT_ONLY_INVALID_COMPLETION", result["decided_by"])

    def test_a_missing_pair_is_insufficient_and_the_invalid_run_keeps_its_reason(self):
        with tempfile.TemporaryDirectory() as tmp:
            aggregate, root, _ = self.build(tmp, omit=("h2r2-f07-v",))
            (root / "h2r2-f05-c" / "audit" / "audit.json").unlink()
            result = aggregate.aggregate(root)
            self.assertEqual("INSUFFICIENT_EVIDENCE", result["result"])
            self.assertEqual("COVERAGE:MISSING:f07/variant", result["decided_by"])
            self.assertEqual(["h2r2-f07-v"],
                             [item["run_id"] for item in result["missing"]])
            self.assertEqual(["h2r2-f05-c"], result["audit_missing"])

    def test_an_invalid_or_blocked_run_is_listed_with_its_reason_and_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            aggregate, root, _ = self.build(
                tmp,
                overrides={"h2r2-f02-v": {"final_verdict": "INVALID", "verdict": "INVALID",
                                           "reason": "TIMEOUT"},
                           "h2r2-f02-c": {"final_verdict": "BLOCKED", "verdict": "BLOCKED",
                                          "reason": "PROVIDER_FAILED_BEFORE_WORK:no-route"}},
                attempt_rows=[{"run_id": "h2r2-f02-v", "task_id": "f02", "arm": "variant",
                               "attempt": 1, "kind": "TERMINAL", "verdict": "INVALID",
                               "reason": "TIMEOUT"}])
            result = aggregate.aggregate(root)
            self.assertEqual("INSUFFICIENT_EVIDENCE", result["result"])
            self.assertEqual("COVERAGE:BLOCKED:h2r2-f02-c", result["decided_by"])
            self.assertEqual([{"run_id": "h2r2-f02-v", "task_id": "f02", "arm": "variant",
                               "reason": "TIMEOUT"}], result["invalid"])
            self.assertEqual(["h2r2-f02-c"], [item["run_id"] for item in result["blocked"]])
            row = next(item for item in result["rows"] if item["run_id"] == "h2r2-f02-v")
            self.assertEqual([{"attempt": 1, "kind": "TERMINAL", "verdict": "INVALID",
                               "reason": "TIMEOUT"}], row["attempts"])

    def test_an_identical_pair_is_the_pre_registered_null_and_never_safe(self):
        with tempfile.TemporaryDirectory() as tmp:
            same = {"correctness": "PASS", "invalid_completion": False,
                    "findings": [{"id": "same-finding", "severity": "P3",
                                  "category": "HV1", "location": "report.md"}]}
            aggregate, root, plan = self.build(
                tmp, audits={run["run_id"]: same for run in load("aggregate_runs").planned_runs()})
            result = aggregate.aggregate(root)
            self.assertEqual("INSUFFICIENT_EVIDENCE", result["result"])
            self.assertEqual("NULL_DIFFERENCE", result["decided_by"])
            self.assertEqual(10, result["usable_pairs"])


class SandboxConfinement(unittest.TestCase):
    """F16 / F19 / F21: the rendered OS profile is the barrier; no model, no credential."""

    def setUp(self):
        if not SANDBOX_READY:
            self.skipTest("sandbox-exec is not available on this platform")

    def layout(self, tmp):
        module = load("sandbox_v2")
        runs = Path(tmp) / "runs"
        run_dir = runs / "h2r2-f01-c"
        run_dir.mkdir(parents=True)
        driver = runs / ".driver" / "h2r2-f01-c"
        home = module.fresh_home(driver, "home-1", run_dir)
        return module, runs, run_dir, home, driver

    def test_the_template_denies_the_shared_roots_and_renders_only_the_launch_surface(self):
        module = load("sandbox_v2")
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, run_dir, home, _ = self.layout(tmp)
            text = module.render(run_dir, home, sys.executable)
            self.assertIn("(deny file-read-data file-write*", text)
            for root in ("/Users", "/private/tmp", "/private/var/folders"):
                self.assertIn(f'(subpath "{root}")', text, root)
            self.assertIn(f'(subpath "{run_dir}")', text)
            self.assertIn(f'(subpath "{home}")', text)
            self.assertIn(f'(literal "{runs}")', text)
            self.assertNotIn(module.PLACEHOLDER, text)
            self.assertEqual(module.template_bytes(), (FZ / module.TEMPLATE_NAME).read_bytes())

    def test_three_dynamic_reads_of_a_planted_file_fail_inside_the_profile(self):
        """F16: the exact attacks the review used — substitution, a decoder, and `-c` code."""
        module = load("sandbox_v2")
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, run_dir, home, driver = self.layout(tmp)
            planted, token = module.plant(driver)
            stream = driver / "attempt-1"
            profile = module.profile(stream, run_dir, home, sys.executable)
            encoded = base64.b64encode(str(planted).encode()).decode()
            attempts = (
                ("cat", ["cat", str(planted)]),
                ("command substitution", ["sh", "-c", f"cat $(printf '%s' '{planted}')"]),
                ("decoder", ["sh", "-c", f"printf %s {encoded} | base64 -d | xargs cat"]),
                ("inline program", [sys.executable, "-c", f"open({str(planted)!r}).read()"]),
            )
            for label, argv in attempts:
                with self.subTest(label=label):
                    result = subprocess.run(["/usr/bin/sandbox-exec", "-f", profile["path"], *argv],
                                            cwd=str(run_dir), capture_output=True, text=True)
                    self.assertNotEqual(0, result.returncode, label)
                    self.assertNotIn(token, result.stdout + result.stderr, label)
            write = subprocess.run(
                ["/usr/bin/sandbox-exec", "-f", profile["path"], sys.executable, "-c",
                 f"open({str(run_dir / 'allowed.txt')!r}, 'w').write('ok')"],
                cwd=str(run_dir), capture_output=True, text=True)
            self.assertEqual(0, write.returncode, write.stderr)
            self.assertEqual("ok", (run_dir / "allowed.txt").read_text())
            self.assertTrue((run_dir / ".tmp").is_dir())

    def test_the_self_test_passes_and_the_rendered_profile_is_archived_with_its_hash(self):
        module = load("sandbox_v2")
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, run_dir, home, driver = self.layout(tmp)
            planted, token = module.plant(driver)
            stream = driver / "attempt-1"
            profile = module.profile(stream, run_dir, home, sys.executable)
            test = module.self_test(profile["path"], run_dir, planted, sys.executable, token)
            self.assertEqual("PASS", test["verdict"], test["reasons"])
            self.assertTrue(Path(profile["path"]).is_file())
            self.assertEqual(digest(Path(profile["path"]).read_bytes()), profile["sha256"])
            self.assertEqual(digest(module.template_bytes()), profile["template_sha256"])
            self.assertFalse((run_dir / module.CONFINE_WRITE).exists())

    def test_a_profile_that_does_not_deny_fails_the_self_test(self):
        module = load("sandbox_v2")
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, run_dir, home, driver = self.layout(tmp)
            planted, token = module.plant(driver)
            permissive = driver / "permissive.sb"
            permissive.write_text("(version 1)\n(allow default)\n", encoding="utf-8")
            test = module.self_test(permissive, run_dir, planted, sys.executable, token)
            self.assertEqual("FAIL", test["verdict"])
            self.assertIn("CAT_READ_NOT_DENIED", test["reasons"])
            self.assertIn("PYTHON_READ_NOT_DENIED", test["reasons"])

    def test_no_sandbox_on_the_platform_blocks_without_consuming_an_attempt(self):
        class NoSandbox(StubSandbox):
            def available(self):
                return False

        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "accept", sandbox=NoSandbox())
            self.assertEqual("BLOCKED", result["outcome"])
            self.assertEqual(["SANDBOX_UNAVAILABLE"], result["reasons"])
            self.assertFalse(result["registered"])
            self.assertFalse((runs / "h2r2-f01-c").exists())
            self.assertFalse((runs / "registry-v2.jsonl").exists())
            self.assertFalse((runs / ".locks" / "h2r2-f01-c.json").exists())
            _, _, accepted = execute_stub(tmp, "accept")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("ACCEPT", accepted["verdict"], accepted["reasons"])
            finally:
                cleanup_run(run_dir)

    def test_a_failing_confinement_self_test_blocks_and_is_reinvokable(self):
        with tempfile.TemporaryDirectory() as tmp:
            driver, runs, blocked = execute_stub(tmp, "accept", sandbox=FailingSandbox())
            self.assertEqual("BLOCKED", blocked["outcome"])
            self.assertEqual(["SANDBOX_NOT_CONFINING:PYTHON_READ_NOT_DENIED"], blocked["reasons"])
            self.assertFalse((runs / "registry-v2.jsonl").exists())
            self.assertFalse((runs / "h2r2-f01-c").exists())
            self.assertFalse((runs / ".locks" / "h2r2-f01-c.json").exists())
            log = [json.loads(line) for line in
                   (runs / ".driver" / "h2r2-f01-c" / "blocked.jsonl").read_text().splitlines()]
            self.assertEqual(["SANDBOX_NOT_CONFINING:PYTHON_READ_NOT_DENIED"],
                             log[0]["reasons"])
            _, _, accepted = execute_stub(tmp, "accept")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("ACCEPT", accepted["verdict"], accepted["reasons"])
                self.assertEqual(1, accepted["attempts"])
            finally:
                cleanup_run(run_dir)

    def test_a_credential_import_failure_blocks_and_is_reinvokable(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, blocked = execute_stub(tmp, "accept", auth=StubAuth(ok=False))
            self.assertEqual("BLOCKED", blocked["outcome"])
            self.assertEqual(["CREDENTIAL_IMPORT_FAILED:AUTH_EXPORT_FAILED"], blocked["reasons"])
            self.assertFalse((runs / "registry-v2.jsonl").exists())
            _, _, accepted = execute_stub(tmp, "accept")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("ACCEPT", accepted["verdict"], accepted["reasons"])
            finally:
                cleanup_run(run_dir)


class DriverConfinement(unittest.TestCase):
    """T29: driver-held streams and a fresh per-launch home (stub sandbox, never a model)."""

    def test_a_stub_that_rewrites_its_event_stream_is_invalid_from_the_driver_copy(self):
        """F17: the worker's own cwd is not evidence; the driver's copy decides the verdict."""
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "tamper")
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("INVALID", result["verdict"])
                self.assertIn("WORKER_ERROR_EVENT", result["reasons"])
                self.assertNotIn("PROVIDER_FAILED_BEFORE_WORK", ";".join(result["reasons"]))
                self.assertEqual(1, result["attempts"])
                record = json.loads((run_dir / "run.json").read_text())
                worker = next(step for step in record["steps"] if step["step"] == "worker")
                self.assertEqual(1, worker["tool_calls"])
                evidence = Path(worker["evidence"])
                self.assertTrue(evidence.is_relative_to((runs / ".driver"
                                                         / "h2r2-f01-c").resolve()))
                self.assertIn('"type": "tool_use"', evidence.read_text())
                self.assertNotIn("rewritten", evidence.read_text())
                self.assertEqual(evidence.read_text(), (run_dir / "events.jsonl").read_text())
                audit = json.loads((run_dir / "access-audit.json").read_text())
                self.assertEqual(1, audit["tool_calls"])
            finally:
                cleanup_run(run_dir)

    def test_every_launch_uses_its_own_fresh_home_with_only_the_frozen_config(self):
        module = load("sandbox_v2")
        template = (FZ / "worker-profile" / "opencode.json").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            _, runs, result = execute_stub(tmp, "provider-once")
            run_dir = runs / "h2r2-f01-c"
            driver = (runs / ".driver" / "h2r2-f01-c").resolve()
            try:
                self.assertEqual("ACCEPT", result["verdict"], result["reasons"])
                self.assertEqual(2, result["attempts"])
                for number in (1, 2):
                    home = driver / f"home-{number}"
                    self.assertTrue(home.is_dir())
                    self.assertEqual(0o700, home.stat().st_mode & 0o777)
                    self.assertEqual([f"{module.CONFIG_DIR_REL}/{module.CONFIG_NAME}"],
                                     module.imported_files(home))
                    self.assertEqual(template, (home / module.CONFIG_DIR_REL
                                                / module.CONFIG_NAME).read_bytes())
                self.assertTrue((driver / "audit-home-1").is_dir())
                self.assertTrue((run_dir / ".tmp").is_dir())
                record = json.loads((run_dir / "run.json").read_text())
                self.assertEqual(str(driver / "home-2"), record["fresh_home"])
                self.assertEqual("PASS", record["sandbox"]["confinement"]["verdict"])
                profile = Path(record["sandbox"]["profile"]["path"])
                self.assertTrue(profile.is_file())
                self.assertEqual(digest(profile.read_bytes()),
                                 record["sandbox"]["profile"]["sha256"])
            finally:
                cleanup_run(run_dir)

    def test_a_new_home_never_inherits_another_launch_state(self):
        """F19: no other run's transcript, credential or config can reach a fresh home."""
        module = load("sandbox_v2")
        template = (FZ / "worker-profile" / "opencode.json").read_bytes()
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            run_dir = runs / "h2r2-f01-c"
            run_dir.mkdir(parents=True)
            driver = runs / ".driver" / "h2r2-f01-c"
            first = module.fresh_home(driver, "home-1", run_dir)
            transcript = first / ".local/share/opencode/opencode.db"
            transcript.parent.mkdir(parents=True, exist_ok=True)
            transcript.write_text("another run's session", encoding="utf-8")
            (first / "auth.json").write_text("imported credential", encoding="utf-8")
            second = module.fresh_home(driver, "home-2", run_dir)
            self.assertEqual([f"{module.CONFIG_DIR_REL}/{module.CONFIG_NAME}"],
                             module.imported_files(second))
            self.assertEqual(template, (second / module.CONFIG_DIR_REL
                                        / module.CONFIG_NAME).read_bytes())
            self.assertFalse((second / "auth.json").exists())
            self.assertFalse((second / ".local/share/opencode/opencode.db").exists())

    @unittest.skipUnless(SANDBOX_READY, "sandbox-exec is not available on this platform")
    def test_a_sandboxed_dynamic_read_is_denied_and_recorded_as_evidence(self):
        """F16 end to end: a real `-c` read inside the real profile is EPERM, not INVALID."""
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp) / "runs"
            driver = load("run_h2r2")
            result = driver.execute(
                "h2r2-f01-c", runs,
                worker_command=(sys.executable, "-c", SANDBOX_DYNAMIC_STUB),
                preflight=passing_preflight, auditor=stub_auditor(),
                profile_env=profile_env_file(tmp), probe=passing_probe,
                auth=StubAuth())
            run_dir = runs / "h2r2-f01-c"
            try:
                self.assertEqual("REJECT", result["verdict"], result["reasons"])
                self.assertNotIn("OUT_OF_RUN_ACCESS", ";".join(result["reasons"]))
                audit = json.loads((run_dir / "access-audit.json").read_text())
                self.assertEqual("PASS", audit["verdict"], audit["hits"])
                self.assertEqual(1, audit["tool_calls"])
                self.assertIn("INLINE_PROGRAM", audit["unresolved_constructs"][0]["construct"]
                              if audit["unresolved_constructs"] else "")
                denied = audit["sandbox_denied"]
                self.assertTrue(denied, audit)
                self.assertTrue(denied[0]["path"].endswith("confinement-plant.txt"), denied)
                self.assertIn("Operation not permitted", denied[0]["value"])
                record = json.loads((run_dir / "run.json").read_text())
                self.assertEqual("PASS", record["sandbox"]["confinement"]["verdict"])
                profile = Path(record["sandbox"]["profile"]["path"])
                self.assertTrue(profile.is_file())
                self.assertEqual(digest(profile.read_bytes()),
                                 record["sandbox"]["profile"]["sha256"])
                self.assertTrue(Path(record["fresh_home"]).is_dir())
            finally:
                cleanup_run(run_dir)


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
