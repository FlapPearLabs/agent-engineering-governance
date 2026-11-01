"""H4 exploratory pilot — driver, acceptance, INJECT and isolation tests.

`PILOT_SPEC.md` §"Required tests": the driver refuses without `H4_PILOT_RUN_AUTH`, the fake worker
runs end to end through all three arms, INJECT with a missed control is INVALID, and the worker
sandbox profile denies reads of the quarantine and of global rule files (skipped with an explicit
reason when `sandbox-exec` is unavailable — never reported as a pass).

No model, no network: the worker is the deterministic `--fake-worker` stub, and `taskpack.py`
(another implementer's file in a parallel worktree) is replaced by a stand-in through
`pilot_accept.taskpack_module`.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / "experiments/v1.2/h4-micro-low-ablation/pilot"
FREEZE_V3 = ROOT / "experiments/v1.2/h2-lazy-disclosure/freeze-v3"
AUTH_ENV = "H4_PILOT_RUN_AUTH"
SANDBOX_READY = sys.platform == "darwin" and shutil.which("sandbox-exec") is not None


def load(name):
    if str(PILOT) not in sys.path:
        sys.path.insert(0, str(PILOT))
    spec = importlib.util.spec_from_file_location(name, PILOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


arms = load("arms")
pilot_accept = load("pilot_accept")
pilot_driver = load("pilot_driver")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class StandInTaskpack:
    """The agreed `taskpack` interface: `verify_seal(pkg_dir)` raising `SealError` on a mismatch."""

    class SealError(Exception):
        pass

    @classmethod
    def verify_seal(cls, pkg_dir):
        package = Path(pkg_dir)
        seal_path = package / "SEAL.json"
        if not seal_path.is_file():
            raise cls.SealError("SEAL.json missing")
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        for rel, digest in seal["files"].items():
            if sha256((package / rel).read_bytes()) != digest:
                raise cls.SealError(rel)
        return None


def build_package(root: Path) -> Path:
    """A synthetic package in the registered format, sealed by the helper (as the tests must)."""
    pkg = root / "pkg-01"
    (pkg / "base/src").mkdir(parents=True)
    (pkg / "base/tests").mkdir(parents=True)
    (pkg / "hidden").mkdir(parents=True)
    (pkg / "base/ruff.toml").write_text('[lint]\nselect = ["E9", "F"]\n', encoding="utf-8")
    (pkg / "base/src/__init__.py").write_text("", encoding="utf-8")
    (pkg / "base/src/widget.py").write_text(
        "def area(width, height):\n    return width * height\n", encoding="utf-8")
    (pkg / "base/tests/test_widget.py").write_text(
        "import unittest\n\nfrom src import widget\n\n\n"
        "class Widget(unittest.TestCase):\n"
        "    def test_area(self):\n"
        "        self.assertEqual(widget.area(2, 3), 6)\n", encoding="utf-8")
    (pkg / "hidden/test_hidden.py").write_text(
        "import unittest\n\nfrom src import widget\n\n\n"
        "class HiddenPerimeter(unittest.TestCase):\n"
        "    def test_perimeter(self):\n"
        "        perimeter = getattr(widget, 'perimeter', None)\n"
        "        self.assertIsNotNone(perimeter, 'perimeter is missing')\n"
        "        self.assertEqual(perimeter(2, 3), 10)\n", encoding="utf-8")
    (pkg / "statement.md").write_text(
        "# Add a perimeter helper\n\n`src/widget.py` computes a rectangle's area. Add a function\n"
        "`perimeter(width, height)` returning twice the sum of the two arguments.\n",
        encoding="utf-8")
    (pkg / "package.json").write_text(json.dumps({
        "task_id": "pkg-01",
        "title": "Add a perimeter helper",
        "label": "SYNTHETIC_EXPLORATORY",
        "risk": "LOW",
        "language": "python",
        "statement": "statement.md",
        "hidden_test": "hidden/test_hidden.py",
        "hidden_test_dest": "tests/test_hidden.py",
        "reference_patch": "reference.patch",
        "test_command": ["python", "-m", "unittest", "discover", "-s", "tests"],
        "gate": {"kind": "ruff", "config": "ruff.toml"},
    }, indent=2) + "\n", encoding="utf-8")

    scratch = root / "scratch"
    shutil.copytree(pkg / "base", scratch)
    env = {"PATH": os.environ.get("PATH", ""), "GIT_AUTHOR_NAME": "H4 Pilot",
           "GIT_AUTHOR_EMAIL": "h4@pilot.invalid", "GIT_COMMITTER_NAME": "H4 Pilot",
           "GIT_COMMITTER_EMAIL": "h4@pilot.invalid"}
    for command in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "base"]):
        subprocess.run(["git", "-C", str(scratch), *command], check=True, env=env)
    (scratch / "src/widget.py").write_text(
        "def area(width, height):\n    return width * height\n\n\n"
        "def perimeter(width, height):\n    return 2 * (width + height)\n", encoding="utf-8")
    for command in (["add", "-A"], ["commit", "-qm", "fix"]):
        subprocess.run(["git", "-C", str(scratch), *command], check=True, env=env)
    (pkg / "reference.patch").write_text(
        subprocess.run(["git", "-C", str(scratch), "diff", "HEAD^", "HEAD"], check=True,
                       capture_output=True, text=True, env=env).stdout, encoding="utf-8")
    shutil.rmtree(scratch)

    seal = {"version": 1, "verified": True, "files": {}}
    for path in sorted(pkg.rglob("*")):
        if path.is_file() and path.name != "SEAL.json":
            seal["files"][path.relative_to(pkg).as_posix()] = sha256(path.read_bytes())
    (pkg / "SEAL.json").write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n",
                                   encoding="utf-8")
    return pkg


class PilotDriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pkg = build_package(self.root)
        self.results = self.root / "results"
        self.original_taskpack = pilot_accept.taskpack_module
        pilot_accept.taskpack_module = lambda: StandInTaskpack
        self.addCleanup(self._restore_taskpack)
        self.original_auth = os.environ.pop(AUTH_ENV, None)
        self.addCleanup(self._restore_auth)

    def _restore_taskpack(self):
        pilot_accept.taskpack_module = self.original_taskpack

    def _restore_auth(self):
        if self.original_auth is not None:
            os.environ[AUTH_ENV] = self.original_auth

    def run_driver(self, arms_value="FULL,MIN,INJECT", extra=(), results=None):
        results = Path(results or self.results)
        argv = ["--packages", str(self.pkg), "--results-dir", str(results),
                "--arms", arms_value, "--fake-worker", *extra]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            code = pilot_driver.main(argv)
        self.output = buffer.getvalue()
        return code, results

    def record(self, results: Path, run_id: str) -> dict:
        return json.loads((results / run_id / "record.json").read_text(encoding="utf-8"))

    # -- authorization -----------------------------------------------------

    def test_the_driver_refuses_without_run_authorization(self):
        env = {key: value for key, value in os.environ.items() if key != AUTH_ENV}
        completed = subprocess.run(
            [sys.executable, str(PILOT / "pilot_driver.py"), "--packages", str(self.pkg),
             "--results-dir", str(self.results)], capture_output=True, text=True, env=env,
            cwd=str(ROOT))
        self.assertEqual(2, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("H4_PILOT_RUN_AUTH_NOT_SET", completed.stderr)
        self.assertFalse(self.results.exists(), "no result directory may be created")

    def test_authorization_file_must_carry_numeric_budget_and_max_runs(self):
        good = self.root / "authorization.json"
        good.write_text(json.dumps({"budget_cap": 5, "max_runs": 3}), encoding="utf-8")
        self.assertEqual({"path": str(good), "budget_cap": 5, "max_runs": 3},
                         pilot_driver.read_authorization({AUTH_ENV: str(good)}))
        for payload, reason in (
                ({"budget_cap": "5", "max_runs": 3}, "BUDGET_CAP"),
                ({"budget_cap": 5}, "MAX_RUNS_MISSING"),
                ({"budget_cap": 5, "max_runs": 2.5}, "MAX_RUNS_NOT_INTEGER"),
                ({"budget_cap": 0, "max_runs": 3}, "BUDGET_CAP"),
                ([1, 2, 3], "NOT_AN_OBJECT")):
            path = self.root / "bad.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(pilot_driver.AuthorizationError) as caught:
                pilot_driver.read_authorization({AUTH_ENV: str(path)})
            self.assertIn(reason, str(caught.exception))
        with self.assertRaises(pilot_driver.AuthorizationError):
            pilot_driver.read_authorization({AUTH_ENV: str(self.root / "absent.json")})

    def test_a_plan_larger_than_max_runs_is_refused_before_any_run(self):
        authorization = {"path": "authorization.json", "budget_cap": 5, "max_runs": 1}
        self.assertIsNone(pilot_driver.plan_size_reason(1, authorization))
        self.assertIsNone(pilot_driver.plan_size_reason(99, None))
        self.assertEqual("MAX_RUNS_EXCEEDED:2>1",
                         pilot_driver.plan_size_reason(2, authorization))

    def test_a_temporary_results_directory_is_refused_for_a_real_run(self):
        self.assertEqual("RESULTS_DIR_UNDER_TEMP",
                         pilot_driver.results_dir_reason(Path(self.root) / "results"))
        with self.assertRaises(pilot_driver.DriverRefusal):
            pilot_driver.results_durability(Path(self.root) / "results", fake_worker=False)
        self.assertEqual("EPHEMERAL_TEST_PATH",
                         pilot_driver.results_durability(Path(self.root) / "results",
                                                         fake_worker=True))

    # -- end to end --------------------------------------------------------

    def test_fake_worker_runs_all_three_arms_end_to_end(self):
        code, results = self.run_driver()
        self.assertEqual(0, code, self.output)
        self.assertIn("results_durability=EPHEMERAL_TEST_PATH", self.output)
        full = self.record(results, "pkg-01-full")
        minimum = self.record(results, "pkg-01-min")
        inject = self.record(results, "pkg-01-inject")
        for record in (full, minimum, inject):
            for field in ("task_id", "arm", "model", "base_sha", "seal_sha256", "carrier",
                          "worker", "acceptance", "inject", "durations", "tokens", "cost"):
                self.assertIn(field, record)
            self.assertEqual("SYNTHETIC_EXPLORATORY", record["label"])
            self.assertEqual("NOT_A_MEASUREMENT", record["measurement"])
            self.assertEqual("FAKE_WORKER", record["model"])
            self.assertEqual(40, len(record["base_sha"]))
            self.assertEqual(sha256((self.pkg / "SEAL.json").read_bytes()), record["seal_sha256"])
            self.assertEqual(["visible_tests", "ruff", "hidden_test"],
                             record["acceptance"]["order"])
            self.assertEqual("PASS", record["acceptance"]["gates"]["visible_tests"]["verdict"])
            self.assertEqual("PASS", record["acceptance"]["gates"]["ruff"]["verdict"])
            self.assertEqual("PASS", record["acceptance"]["gates"]["hidden_test"]["verdict"])
            # nothing was observed for tokens or cost, so they are UNKNOWN rather than 0
            self.assertEqual("UNKNOWN", record["tokens"])
            self.assertEqual("UNKNOWN", record["cost"])
            self.assertIn("tokens", record["unobserved"])
            self.assertIn("cost", record["unobserved"])
        self.assertEqual("PASS", full["verdict"])
        self.assertEqual("PASS", minimum["verdict"])
        self.assertEqual("PASS", inject["verdict"])
        self.assertIsNone(full["inject"])
        self.assertIsNone(minimum["inject"])
        self.assertEqual("CAUGHT", inject["inject"]["verdict"])
        self.assertEqual([], inject["inject"]["reasons"])
        self.assertEqual(["GATE_NOT_LOAD_BEARING"], inject["inject"]["probe"]["statuses"])
        self.assertTrue(inject["inject"]["retained_defect"]["retained"])
        # MIN and INJECT share the carrier bytes; FULL does not
        self.assertEqual(minimum["carrier"]["sha256"]["AGENTS.md"],
                         inject["carrier"]["sha256"]["AGENTS.md"])
        self.assertNotEqual(full["carrier"]["sha256"]["AGENTS.md"],
                            minimum["carrier"]["sha256"]["AGENTS.md"])
        self.assertEqual(11, full["carrier"]["rules"])
        self.assertEqual(0, minimum["carrier"]["rules"])
        # the carriers were delivered outside the repository and read back
        for record in (full, minimum, inject):
            self.assertEqual("PASS", record["carrier"]["readback_verdict"])
            self.assertEqual(record["carrier"]["sha256"], record["carrier"]["readback"])

    def test_inject_with_a_missed_control_is_invalid_and_records_the_finding(self):
        def missed(tree):
            return {"command": ["probe"], "returncode": 0, "verdict": "PASS", "rejected": False,
                    "expected_rejection": False, "gates": [], "statuses": []}

        original = pilot_accept.n7_probe
        pilot_accept.n7_probe = missed
        self.addCleanup(setattr, pilot_accept, "n7_probe", original)
        code, results = self.run_driver(arms_value="INJECT")
        self.assertEqual(3, code, self.output)
        record = self.record(results, "pkg-01-inject")
        self.assertEqual("INVALID", record["verdict"])
        self.assertNotEqual("PASS", record["verdict"])
        self.assertIn("N7_CONTROL_MISSED", record["inject"]["reasons"])
        self.assertTrue(record["inject"]["retained_defect"]["retained"])
        self.assertEqual("PASS", record["acceptance"]["verdict"])
        self.assertEqual("MECHANICAL_ACCEPTANCE_HAS_NO_TEETH", record["escape"]["conclusion"])

    def test_inject_requires_an_f841_positive_control(self):
        gate = pilot_accept.canonical_gate("ruff")
        weak = {"id": gate["id"], "command": gate["command"], "intent": gate["intent"],
                "control": {"kind": "file", "path": gate["control"]["path"],
                            "content": "VALUE = 1\n", "signal": gate["control"]["signal"]}}
        tree = self.root / "control-tree"
        pilot_accept.copy_tree(self.pkg / "base", tree)
        record = pilot_accept.inject_n7(tree, gate=weak)
        self.assertEqual("INVALID", record["verdict"])
        self.assertIn("CONTROL_NOT_F841_POSITIVE", record["reasons"])

    def test_the_n7_probe_does_not_reject_a_load_bearing_configuration(self):
        """A probe that always rejects would fake a catch: prove the positive direction too."""
        tree = self.root / "positive-tree"
        pilot_accept.copy_tree(self.pkg / "base", tree)
        pilot_accept.materialize_probe_surface(tree, pilot_accept.canonical_gate("ruff"))
        result = pilot_accept.n7_probe(tree)
        self.assertFalse(result["rejected"], result.get("stdout_tail"))
        self.assertEqual(["LOAD_BEARING"], result["statuses"])

    def test_a_tampered_package_is_refused_before_any_run(self):
        (self.pkg / "base/src/widget.py").write_text("def area(width, height):\n    return 0\n",
                                                     encoding="utf-8")
        code, results = self.run_driver(arms_value="MIN")
        self.assertEqual(2, code, self.output)
        self.assertFalse((results / "pkg-01-min").exists())

    def test_acceptance_stops_at_the_first_failing_gate(self):
        tree = self.root / "broken"
        pkg = pilot_accept.load_package(self.pkg)
        pilot_accept.copy_tree(self.pkg / "base", tree)
        (tree / "src/widget.py").write_text("def area(width, height):\n    return width + height\n",
                                            encoding="utf-8")
        record = pilot_accept.accept(tree, pkg)
        self.assertEqual("FAIL", record["verdict"])
        self.assertEqual(["visible_tests"], record["order"])
        self.assertEqual(["ruff", "hidden_test"], record["skipped"])

    def test_the_real_launch_path_is_import_only(self):
        self.assertFalse(hasattr(pilot_driver, "sandbox_v2"),
                         "the frozen modules must be imported inside real_launch only")
        self.assertTrue((FREEZE_V3 / "sandbox_v2.py").is_file())
        self.assertTrue((FREEZE_V3 / "wrapper_delivery.py").is_file())
        self.assertEqual(str(FREEZE_V3), str(pilot_driver.FREEZE_V3))
        source = (PILOT / "pilot_driver.py").read_text(encoding="utf-8")
        self.assertIn("def real_launch", source)
        self.assertIn("sandbox.self_test", source)
        self.assertIn("sandbox.confine", source)

    # -- isolation ---------------------------------------------------------

    @unittest.skipUnless(SANDBOX_READY,
                         "sandbox-exec unavailable: worker isolation cannot be demonstrated "
                         "(explicit SKIP, never a pass)")
    def test_the_worker_profile_denies_quarantine_and_global_rule_files(self):
        base = self.root / "isolation"
        run_dir = base / "cell" / "run"
        home = run_dir / "home"
        home.mkdir(parents=True)
        quarantine = base / "quarantine"
        (quarantine / "hidden").mkdir(parents=True)
        secret = quarantine / "hidden/test_hidden.py"
        secret.write_text("SECRET_HIDDEN_TEST\n", encoding="utf-8")
        # a home-shaped tree carrying the two global rule files the worker must never see
        global_home = base / "global-home"
        agents = global_home / ".agents/AGENTS.md"
        agents.parent.mkdir(parents=True)
        agents.write_text("GLOBAL_AGENTS_RULE\n", encoding="utf-8")
        opencode = global_home / ".config/opencode/AGENTS.md"
        opencode.parent.mkdir(parents=True)
        opencode.write_text("GLOBAL_OPENCODE_RULE\n", encoding="utf-8")
        inside = run_dir / "statement.md"
        inside.write_text("visible\n", encoding="utf-8")

        profile = pilot_driver.render_profile(base / "stream", run_dir, home)
        env = {key: os.environ[key] for key in ("PATH", "LANG") if key in os.environ}
        env.update({"HOME": str(home), "TMPDIR": str(run_dir), "PYTHONDONTWRITEBYTECODE": "1"})

        def confined(argv):
            return subprocess.run(["sandbox-exec", "-f", profile["path"], *argv], cwd=str(run_dir),
                                  capture_output=True, text=True, env=env, timeout=120)

        allowed = confined(["/bin/cat", str(inside)])
        self.assertEqual(0, allowed.returncode, allowed.stderr)
        for target in (secret, agents, opencode):
            denied = confined(["/bin/cat", str(target)])
            self.assertNotEqual(0, denied.returncode, f"read of {target.name} was allowed")
            self.assertIn("permitted", denied.stderr.lower(), denied.stderr)
        python_read = confined([sys.executable, "-c", f"print(open({str(secret)!r}).read())"])
        self.assertNotEqual(0, python_read.returncode)
        self.assertNotIn("SECRET_HIDDEN_TEST", python_read.stdout)
        self.assertIn("permitted", python_read.stderr.lower(), python_read.stderr)
        self.assertTrue(profile["sha256"])


if __name__ == "__main__":
    unittest.main()
