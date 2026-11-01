"""H4 exploratory pilot — driver, acceptance, INJECT and isolation tests.

`PILOT_SPEC.md` §"Required tests": the driver refuses without `H4_PILOT_RUN_AUTH`, the fake worker
runs end to end through all three arms, INJECT with a missed control is INVALID, and the worker
sandbox profile denies reads of the quarantine and of global rule files (skipped with an explicit
reason when `sandbox-exec` cannot apply a profile — never reported as a pass).

Acceptance runs in a FRESH directory (`pilot_accept.prepare_acceptance_tree`): the worker's source,
the sealed base's visible tests, and a canary whose four tests must all fail before the hidden test
is believed. Two regression tests replay the acceptance report's escape attacks: a worker-authored
`tests/__init__.py` (D1) and a `src/__init__.py` that patches `unittest`.

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
import re
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

# D5: `which sandbox-exec` is not proof that a profile can be applied. The probe really runs
# `sandbox-exec -p '(version 1)(allow default)' /usr/bin/true`; under an outer sandbox it fails
# with `sandbox_apply: Operation not permitted`, and that text becomes the SKIP reason.
SANDBOX_READY, SANDBOX_REASON = pilot_driver.sandbox_probe()


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


BASE_WIDGET = "def area(width, height):\n    return width * height\n"
FIXED_WIDGET = BASE_WIDGET + "\n\ndef perimeter(width, height):\n    return 2 * (width + height)\n"
CONSTANT_FIX = BASE_WIDGET + "\nPERIMETER_SUM = 10\n"

HIDDEN_CALLS_THE_FUNCTION = (
    "import unittest\n\nfrom src import widget\n\n\n"
    "class HiddenPerimeter(unittest.TestCase):\n"
    "    def test_perimeter(self):\n"
    "        perimeter = getattr(widget, 'perimeter', None)\n"
    "        self.assertIsNotNone(perimeter, 'perimeter is missing')\n"
    "        self.assertEqual(perimeter(2, 3), 10)\n"
)
# g_escape2's hidden test: assertion-only, so a neutered `assertEqual` turns a missing feature into
# a green run instead of an import/attribute error.
HIDDEN_ASSERTS_A_CONSTANT = (
    "import unittest\n\nfrom src import widget\n\n\n"
    "class HiddenConstant(unittest.TestCase):\n"
    "    def test_constant_is_present(self):\n"
    "        self.assertEqual(getattr(widget, 'PERIMETER_SUM', None), 10)\n"
)
# g_escape2's plant: a 3-line tests/__init__.py that empties the assertions before they run.
TESTS_INIT_PLANT = (
    "import unittest\n"
    "unittest.TestCase.assertEqual = lambda self, a, b, msg=None: None\n"
    "unittest.TestCase.assertTrue = lambda self, expr, msg=None: None\n"
    "unittest.TestCase.assertIsNotNone = lambda self, obj, msg=None: None\n"
)
# The same plant placed in the worker's package initialiser, which the hidden test imports.
SRC_INIT_PLANT = (
    "import unittest\n\n"
    "unittest.TestCase.assertEqual = lambda self, a, b, msg=None: None\n"
    "unittest.TestCase.assertTrue = lambda self, expr, msg=None: None\n"
    "unittest.TestCase.assertIsNone = lambda self, obj, msg=None: None\n"
)


def build_package(root: Path, *, hidden: str = HIDDEN_CALLS_THE_FUNCTION,
                  fixed: str = FIXED_WIDGET, task_id: str = "pkg-01") -> Path:
    """A synthetic package in the registered format, sealed by the helper (as the tests must)."""
    pkg = root / task_id
    (pkg / "base/src").mkdir(parents=True)
    (pkg / "base/tests").mkdir(parents=True)
    (pkg / "hidden").mkdir(parents=True)
    (pkg / "base/ruff.toml").write_text('[lint]\nselect = ["E9", "F"]\n', encoding="utf-8")
    (pkg / "base/src/__init__.py").write_text("", encoding="utf-8")
    (pkg / "base/src/widget.py").write_text(BASE_WIDGET, encoding="utf-8")
    (pkg / "base/tests/__init__.py").write_text("", encoding="utf-8")
    (pkg / "base/tests/test_widget.py").write_text(
        "import unittest\n\nfrom src import widget\n\n\n"
        "class Widget(unittest.TestCase):\n"
        "    def test_area(self):\n"
        "        self.assertEqual(widget.area(2, 3), 6)\n", encoding="utf-8")
    (pkg / "hidden/test_hidden.py").write_text(hidden, encoding="utf-8")
    (pkg / "statement.md").write_text(
        "# Add a perimeter helper\n\n`src/widget.py` computes a rectangle's area. Add a function\n"
        "`perimeter(width, height)` returning twice the sum of the two arguments.\n",
        encoding="utf-8")
    (pkg / "package.json").write_text(json.dumps({
        "task_id": task_id,
        "title": "Add a perimeter helper",
        "label": "SYNTHETIC_EXPLORATORY",
        "risk": "LOW",
        "language": "python",
        "statement": "statement.md",
        "hidden_test": "hidden/test_hidden.py",
        "hidden_test_dest": "tests/test_hidden.py",
        "reference_patch": "reference.patch",
        "test_command": ["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
        "gate": {"kind": "ruff", "config": "ruff.toml"},
    }, indent=2) + "\n", encoding="utf-8")

    scratch = root / (task_id + "-scratch")
    shutil.copytree(pkg / "base", scratch)
    env = {"PATH": os.environ.get("PATH", ""), "GIT_AUTHOR_NAME": "H4 Pilot",
           "GIT_AUTHOR_EMAIL": "h4@pilot.invalid", "GIT_COMMITTER_NAME": "H4 Pilot",
           "GIT_COMMITTER_EMAIL": "h4@pilot.invalid"}
    for command in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "base"]):
        subprocess.run(["git", "-C", str(scratch), *command], check=True, env=env)
    (scratch / "src/widget.py").write_text(fixed, encoding="utf-8")
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


ALLOW_RE = re.compile(r'\(allow ([^()]*(?:\([^()]*\)[^()]*)*?)\s*\((subpath|literal) "([^"]+)"\)')


def parse_profile(text: str) -> list[dict]:
    """(kind, path, reads, writes) for every allow rule the frozen template renders."""
    rules = []
    for line in text.splitlines():
        match = ALLOW_RE.match(line)
        if not match:
            continue
        operations, kind, path = match.group(1), match.group(2), match.group(3)
        rules.append({"kind": kind, "path": path, "read": "file-read" in operations,
                      "write": "file-write" in operations})
    return rules


def granted(rules: list[dict], target, operation: str) -> str | None:
    """The rule that grants `operation` ("read" / "write") on `target`, or None when denied."""
    target = Path(os.path.realpath(target))
    best = None
    for rule in rules:
        if not rule[operation]:
            continue
        candidate = Path(os.path.realpath(rule["path"]))
        if rule["kind"] == "subpath" and (target == candidate or candidate in target.parents):
            best = f"subpath {rule['path']}"
        elif rule["kind"] == "literal" and target == candidate:
            best = f"literal {rule['path']}"
    return best


def durable_fixture_dir(case: unittest.TestCase) -> Path:
    """A non-temporary scratch directory for authorization fixtures, removed on cleanup.

    Authorization files under a temporary root are refused by design, so a fixture inside
    `tempfile.TemporaryDirectory()` can only be used to prove a refusal. The directory beside this
    file is used when it is durable; a checkout that itself sits under a temporary root falls back
    to the home directory, and a machine with neither SKIPS rather than weakening the gate.
    """
    for base in (Path(__file__).resolve().parent, Path.home()):
        if base.is_dir() and not pilot_driver.is_temporary_path(base):
            path = Path(tempfile.mkdtemp(prefix=".h4-pilot-auth-", dir=base))
            case.addCleanup(shutil.rmtree, path, True)
            return path
    raise unittest.SkipTest("no durable (non-temporary) directory for authorization fixtures")


class PilotDriverTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pkg = build_package(self.root)
        self.results = self.root / "results"
        # Authorization files under a temporary root are refused by design, so the fixtures live in
        # a durable directory: beside this file, or under the home directory in a temp-root checkout.
        self.auth_dir = durable_fixture_dir(self)
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

    def authorization(self, payload: dict, name: str = "authorization.json") -> Path:
        path = self.auth_dir / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def run_driver(self, arms_value="FULL,MIN,INJECT", extra=(), results=None, package=None):
        results = Path(results or self.results)
        argv = ["--packages", str(package or self.pkg), "--results-dir", str(results),
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
        good = self.authorization({"budget_cap": 5, "max_runs": 3})
        self.assertEqual({"path": str(good), "budget_cap": 5, "max_runs": 3},
                         pilot_driver.read_authorization({AUTH_ENV: str(good)}))
        for payload, reason in (
                ({"budget_cap": "5", "max_runs": 3}, "BUDGET_CAP"),
                ({"budget_cap": 5}, "MAX_RUNS_MISSING"),
                ({"budget_cap": 5, "max_runs": 2.5}, "MAX_RUNS_NOT_INTEGER"),
                ({"budget_cap": 0, "max_runs": 3}, "BUDGET_CAP"),
                ({"budget_cap": 1e308, "max_runs": 3}, "BUDGET_CAP_ABOVE_MAX"),
                ([1, 2, 3], "NOT_AN_OBJECT")):
            path = self.auth_dir / "bad.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(pilot_driver.AuthorizationError) as caught:
                pilot_driver.read_authorization({AUTH_ENV: str(path)})
            self.assertIn(reason, str(caught.exception))
        with self.assertRaises(pilot_driver.AuthorizationError):
            pilot_driver.read_authorization({AUTH_ENV: str(self.auth_dir / "absent.json")})

    def test_an_authorization_file_is_refused_by_relative_path_symlink_or_temp_root(self):
        good = self.authorization({"budget_cap": 5, "max_runs": 3})
        with self.assertRaises(pilot_driver.AuthorizationError) as caught:
            pilot_driver.read_authorization({AUTH_ENV: good.name})
        self.assertIn("AUTHORIZATION_FILE_NOT_ABSOLUTE", str(caught.exception))
        relative_in_cwd = self.auth_dir / "relative.json"
        relative_in_cwd.write_text(json.dumps({"budget_cap": 5, "max_runs": 3}), encoding="utf-8")
        previous = os.getcwd()
        os.chdir(self.auth_dir)
        try:
            with self.assertRaises(pilot_driver.AuthorizationError) as caught:
                pilot_driver.read_authorization({AUTH_ENV: "relative.json"})
            self.assertIn("AUTHORIZATION_FILE_NOT_ABSOLUTE", str(caught.exception))
        finally:
            os.chdir(previous)
        link = self.auth_dir / "link.json"
        link.symlink_to(good)
        with self.assertRaises(pilot_driver.AuthorizationError) as caught:
            pilot_driver.read_authorization({AUTH_ENV: str(link)})
        self.assertIn("AUTHORIZATION_FILE_SYMLINK", str(caught.exception))
        temporary = self.root / "authorization.json"
        temporary.write_text(json.dumps({"budget_cap": 5, "max_runs": 3}), encoding="utf-8")
        with self.assertRaises(pilot_driver.AuthorizationError) as caught:
            pilot_driver.read_authorization({AUTH_ENV: str(temporary)})
        self.assertIn("AUTHORIZATION_FILE_UNDER_TEMP", str(caught.exception))
        # positive control: the durable, absolute, non-symlink file is accepted
        self.assertEqual(5, pilot_driver.read_authorization({AUTH_ENV: str(good)})["budget_cap"])

    def test_the_budget_cap_has_a_documented_ceiling(self):
        ceiling = pilot_driver.MAX_BUDGET_CAP
        self.assertIsInstance(ceiling, float)
        accepted = self.authorization({"budget_cap": ceiling, "max_runs": 1}, "at-ceiling.json")
        self.assertEqual(ceiling,
                         pilot_driver.read_authorization({AUTH_ENV: str(accepted)})["budget_cap"])
        over = self.authorization({"budget_cap": ceiling + 1, "max_runs": 1}, "over.json")
        with self.assertRaises(pilot_driver.AuthorizationError) as caught:
            pilot_driver.read_authorization({AUTH_ENV: str(over)})
        self.assertIn("AUTHORIZATION_BUDGET_CAP_ABOVE_MAX", str(caught.exception))

    def test_an_authorization_file_with_unknown_keys_is_refused(self):
        """A key such as `"bypass": true` must not look like an authorization control."""
        path = self.authorization({"budget_cap": 5, "max_runs": 3, "bypass": True}, "extra.json")
        with self.assertRaises(pilot_driver.AuthorizationError) as caught:
            pilot_driver.read_authorization({AUTH_ENV: str(path)})
        self.assertIn("AUTHORIZATION_UNKNOWN_KEYS:bypass", str(caught.exception))

    def test_the_cli_refuses_a_relative_authorization_path(self):
        (self.auth_dir / "relative.json").write_text(
            json.dumps({"budget_cap": 5, "max_runs": 3}), encoding="utf-8")
        env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
        env[AUTH_ENV] = "relative.json"
        completed = subprocess.run(
            [sys.executable, str(PILOT / "pilot_driver.py"), "--packages", str(self.pkg),
             "--results-dir", str(self.results), "--arms", "MIN"],
            capture_output=True, text=True, env=env, cwd=str(self.auth_dir))
        self.assertEqual(2, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("AUTHORIZATION_FILE_NOT_ABSOLUTE", completed.stderr)
        self.assertFalse(self.results.exists())

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

    def test_a_results_directory_inside_the_repository_is_refused(self):
        """D4(b): removing the RESULTS_DIR_INSIDE_REPOSITORY branch makes this test red."""
        inside = PILOT / "results-should-not-exist"
        self.assertEqual("RESULTS_DIR_INSIDE_REPOSITORY",
                         pilot_driver.results_dir_reason(inside))
        self.assertEqual("RESULTS_DIR_INSIDE_REPOSITORY",
                         pilot_driver.results_dir_reason(ROOT))
        with self.assertRaises(pilot_driver.DriverRefusal) as caught:
            pilot_driver.results_durability(inside, fake_worker=True)
        self.assertIn("RESULTS_DIR_INSIDE_REPOSITORY", str(caught.exception))
        self.assertFalse(inside.exists())

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
            self.assertEqual([], record["acceptance"]["reasons"])
            self.assertTrue(record["acceptance"]["canary"]["failed"])
            self.assertEqual("CANARY_FAILS_AS_REQUIRED", record["acceptance"]["canary"]["reason"])
            self.assertEqual(4, record["acceptance"]["canary"]["ran"])
            self.assertEqual(2, record["acceptance"]["fresh_tree"]["restored_tests"])
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

    def test_acceptance_does_not_mutate_the_captured_candidate(self):
        """The gate runs on a copy; the candidate's digest must survive the whole run."""
        code, results = self.run_driver(arms_value="INJECT")
        self.assertEqual(0, code, self.output)
        run_dir = results / "pkg-01-inject"
        record = self.record(results, "pkg-01-inject")
        recomputed = pilot_driver.capture_candidate(run_dir / "candidate", self.root / "recheck")
        self.assertEqual(record["candidate"]["digest"], recomputed["digest"])
        self.assertEqual(record["candidate"]["files"], recomputed["files"])

    def test_acceptance_stops_at_the_first_failing_gate(self):
        tree = self.root / "broken"
        pkg = pilot_accept.load_package(self.pkg)
        pilot_accept.copy_tree(self.pkg / "base", tree)
        (tree / "src/widget.py").write_text("def area(width, height):\n    return width + height\n",
                                            encoding="utf-8")
        record = pilot_accept.accept(tree, pkg, self.root / "broken-acceptance")
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
        self.assertIn("delivery.driver_root(run_dir)", source)

    # -- an authorized run keeps its honest record -------------------------

    def test_an_authorized_record_keeps_max_runs_only_and_unknown_cost(self):
        """`real_launch` is replaced by a stub here; the record shape is what is under test."""

        def blocked_launch(run_dir, model, timeout=None):
            return {"kind": "real", "exit_status": "UNKNOWN", "seconds": "UNKNOWN",
                    "blocked": "BLOCKED:TEST_STUB"}

        original = pilot_driver.real_launch
        pilot_driver.real_launch = blocked_launch
        self.addCleanup(setattr, pilot_driver, "real_launch", original)
        record = pilot_driver.run_one(
            self.pkg, "MIN", self.root / "res-authorized", fake_worker_mode=False,
            materials="HEAD", model="opencode-go/deepseek-v4.1-flash",
            authorization={"path": "authorization.json", "budget_cap": 5.0, "max_runs": 3})
        self.assertEqual("PILOT_RUN", record["measurement"])
        self.assertEqual("INVALID", record["verdict"])
        self.assertEqual("BLOCKED:TEST_STUB", record["worker"]["blocked"])
        self.assertEqual("AUTHORIZED", record["authorization"]["kind"])
        self.assertEqual("MAX_RUNS_ONLY;RUN_COST_UNOBSERVED",
                         record["authorization"]["budget_enforcement"])
        self.assertEqual(5.0, record["authorization"]["budget_cap"])
        self.assertEqual("UNKNOWN", record["tokens"])
        self.assertEqual("UNKNOWN", record["cost"])
        self.assertEqual(["tokens", "cost"], record["unobserved"])

    # -- D1: the worker cannot neuter the acceptance gate ------------------

    def run_escape(self, name: str, plant: tuple[str, str], *, hidden: str,
                    fixed: str):
        """Run one MIN record whose fake worker leaves `plant` in the repo and applies no fix."""
        pkg = build_package(self.root / name, hidden=hidden, fixed=fixed, task_id=name)
        relative, content = plant

        def sneaky_worker(repo, package, run_dir, timeout=120):
            target = Path(repo) / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            return {"kind": "FAKE_WORKER", "exit_status": 0, "seconds": 0.0,
                    "report": {"kind": "FAKE_WORKER", "status": "COMPLETED"}}

        original = pilot_driver.fake_worker
        pilot_driver.fake_worker = sneaky_worker
        self.addCleanup(setattr, pilot_driver, "fake_worker", original)
        results = self.root / (name + "-results")
        return pilot_driver.run_one(pkg, "MIN", results, fake_worker_mode=True,
                                    materials="HEAD", model="FAKE_WORKER",
                                    authorization=None), results / (name + "-min")

    def test_a_worker_tests_init_cannot_neuter_the_hidden_test(self):
        """g_escape2: a 3-line tests/__init__.py must not turn a missing feature into PASS."""
        record, run_dir = self.run_escape(
            "pkg-escape-tests", ("tests/__init__.py", TESTS_INIT_PLANT),
            hidden=HIDDEN_ASSERTS_A_CONSTANT, fixed=CONSTANT_FIX)
        self.assertEqual("FAIL", record["verdict"])
        self.assertNotEqual("PASS", record["verdict"], "the acceptance report's false green is back")
        self.assertEqual("FAIL", record["acceptance"]["gates"]["hidden_test"]["verdict"])
        self.assertIn("tests/__init__.py",
                      record["acceptance"]["fresh_tree"]["worker_test_files_skipped"])
        # the worker's tests/ never entered the acceptance directory: the sealed base one did
        self.assertEqual("", (run_dir / "acceptance/tests/__init__.py").read_text(encoding="utf-8"))
        self.assertNotIn("unittest.TestCase.assertEqual", (run_dir / "acceptance/tests/__init__.py")
                         .read_text(encoding="utf-8"))
        self.assertTrue((run_dir / "acceptance/tests/test_hidden.py").is_file())
        # the visible gate ran the sealed base test, not the hidden one
        visible = record["acceptance"]["gates"]["visible_tests"]["stdout_tail"]
        self.assertNotIn("HiddenConstant", visible)
        self.assertNotIn("test_constant_is_present", visible)

    def test_a_worker_package_initialiser_cannot_neuter_the_canary(self):
        """A src/__init__.py that empties unittest's assertions is caught by the canary."""
        record, run_dir = self.run_escape(
            "pkg-escape-src", ("src/__init__.py", SRC_INIT_PLANT),
            hidden=HIDDEN_ASSERTS_A_CONSTANT, fixed=CONSTANT_FIX)
        self.assertEqual("INVALID", record["verdict"])
        self.assertIn("ACCEPTANCE_NEUTERED", record["acceptance"]["reasons"])
        canary = record["acceptance"]["canary"]
        self.assertFalse(canary["failed"])
        self.assertEqual(4, canary["ran"])
        self.assertLess(canary["failures"] + canary["errors"], 4,
                        "some canary assertions were silently neutered")
        self.assertEqual(["hidden_test"], record["acceptance"]["skipped"])
        self.assertFalse((run_dir / "acceptance/tests/test_hidden.py").exists(),
                         "the hidden test is not run once the canary has been neutered")

    def test_acceptance_refuses_a_candidate_that_shadows_unittest(self):
        tree = self.root / "shadow-candidate"
        pilot_accept.copy_tree(self.pkg / "base", tree)
        (tree / "unittest.py").write_text("raise SystemExit(0)\n", encoding="utf-8")
        pkg = pilot_accept.load_package(self.pkg)
        with self.assertRaises(pilot_accept.PackageError) as caught:
            pilot_accept.prepare_acceptance_tree(pkg, tree, self.root / "shadow-acceptance")
        self.assertIn("ACCEPTANCE_TREE_SHADOWS_PYTHON:unittest.py", str(caught.exception))

    def test_the_canary_control_passes_only_when_all_four_tests_fail(self):
        tree = self.root / "canary-tree"
        (tree / "src").mkdir(parents=True)
        (tree / "src/__init__.py").write_text("", encoding="utf-8")
        (tree / "tests").mkdir()
        clean = pilot_accept.canary_control(tree)
        self.assertTrue(clean["failed"], clean["stdout_tail"])
        self.assertEqual(4, clean["ran"])
        self.assertEqual(4, clean["failures"] + clean["errors"])
        # now neuter the assertions and show the control notices
        (tree / "src/__init__.py").write_text(SRC_INIT_PLANT, encoding="utf-8")
        neutered = pilot_accept.canary_control(tree)
        self.assertFalse(neutered["failed"], neutered["stdout_tail"])
        self.assertNotEqual(clean["failures"] + clean["errors"],
                            neutered["failures"] + neutered["errors"])

    # -- D3: the real-launch layout is the frozen one ----------------------

    def test_the_real_launch_layout_keeps_the_driver_root_outside_the_launch(self):
        runs_root = self.root / "runs"
        run_dir = runs_root / "pkg-01-min"
        (run_dir / "repo").mkdir(parents=True)
        (run_dir / "statement.md").write_text("visible\n", encoding="utf-8")
        layout = pilot_driver.driver_layout(run_dir)
        self.assertFalse(layout["inside_launch"])
        self.assertEqual(str(runs_root / ".driver" / "pkg-01-min"), layout["driver_dir"])
        self.assertEqual(str(runs_root), layout["runs_root"])
        self.assertTrue(layout["directly_under_runs_root"])

        sandbox, delivery = pilot_driver.frozen_modules()
        driver_dir = Path(layout["driver_dir"])
        self.assertEqual(driver_dir, Path(delivery.driver_root(run_dir)))
        home = sandbox.fresh_home(driver_dir, "home-1", run_dir)
        profile = sandbox.profile(driver_dir, run_dir, home, sys.executable)
        planted, _token = sandbox.plant(driver_dir)
        rules = parse_profile(Path(profile["path"]).read_text(encoding="utf-8"))

        # the confinement plant is neither readable nor writable from inside the launch
        self.assertIsNone(granted(rules, planted, "read"),
                          f"the plant at {planted} is readable from the launch")
        self.assertIsNone(granted(rules, planted, "write"))
        # the worker cannot rewrite its own profile, and neither profile nor home sits in its tree
        self.assertIsNone(granted(rules, profile["path"], "write"),
                          "the worker can write the rendered profile")
        self.assertFalse(str(profile["path"]).startswith(str(run_dir)))
        self.assertFalse(str(home).startswith(str(run_dir)))
        self.assertNotIn(home, (run_dir, *run_dir.parents))
        # positive controls: the launch and the fresh home are still readable
        self.assertIsNotNone(granted(rules, run_dir / "statement.md", "read"))
        self.assertIsNotNone(granted(rules, home, "read"))

    # -- D5: the sandbox probe ---------------------------------------------

    def test_the_sandbox_probe_reports_the_real_failure_reason(self):
        stub = self.root / "sandbox-exec"
        stub.write_text("#!/bin/sh\necho 'sandbox_apply: Operation not permitted' >&2\nexit 71\n",
                        encoding="utf-8")
        stub.chmod(0o755)
        ready, reason = pilot_driver.sandbox_probe(binary_path=stub)
        self.assertFalse(ready)
        self.assertIn("sandbox_apply: Operation not permitted", reason)
        self.assertIn("71", reason)

    def test_the_sandbox_probe_never_passes_without_running(self):
        ready, reason = pilot_driver.sandbox_probe(binary_path=self.root / "missing-sandbox-exec")
        self.assertFalse(ready)
        self.assertIn("could not be run", reason)

    @unittest.skipUnless(SANDBOX_READY, SANDBOX_REASON)
    def test_the_sandbox_probe_confirms_a_working_host(self):
        self.assertTrue(SANDBOX_READY)
        self.assertIn("rc=0", SANDBOX_REASON)

    # -- isolation ---------------------------------------------------------

    @unittest.skipUnless(SANDBOX_READY, SANDBOX_REASON)
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
