#!/usr/bin/env python3
"""H4 exploratory pilot — model-free acceptance, task-package seal re-verification, INJECT N7.

Contract: `PILOT_SPEC.md` §"Package verifier", §"Arms and carriers" (INJECT), §"Driver and
acceptance"; design draft: `../ARMS.md` §"ARM_INJECT".

Acceptance order is fixed: **visible tests → ruff → hidden test → (INJECT only) the N7 probe**. A
gate that cannot be executed (missing command, timeout, unreadable evidence) is `INVALID`, never
`PASS`. On the INJECT arm a missing positive control, a failed injection, a probe error or a probe
that does NOT reject the hollow configuration is `INVALID`, and when the ordinary acceptance was
green with the defect verifiably retained the finding
`MECHANICAL_ACCEPTANCE_HAS_NO_TEETH` is recorded next to that `INVALID` verdict — an adverse
finding must never be reported as a green run.

Acceptance never runs inside the worker's tree. `prepare_acceptance_tree` copies only the candidate's
files outside `tests/`, restores `tests/` from the sealed package base and adds the hidden test; every
run also executes a four-test canary that must fail, so a worker that patches `unittest` (from its
`tests/__init__.py` or from `src/__init__.py`) makes the verdict `INVALID`/`ACCEPTANCE_NEUTERED`
instead of green.

**Every test verdict comes from `taskpack.run_tests_with_runner`**, the harness-owned runner that
signs its report with a one-time nonce (`test_runner.py`). Nothing here parses unittest's printed
summary: a suite that exits early, prints `Ran N tests`/`OK` or writes a report it cannot sign yields
`INVALID`, never `PASS`. A result is believed only when the runner accepted it (MAC verified, exit
status consistent with the counts) **and** the reported test ids equal the ids `taskpack` found by
`ast` parsing of the same test file(s); `pilot_accept` re-checks that id set rather than trusting the
outcome word alone.

`taskpack.py` is imported lazily through `taskpack_module()`; the driver tests substitute a
`verify_seal` stand-in through it and call the real `run_tests_with_runner`. The interfaces used are
`verify_seal(pkg_dir) -> None`, raising `taskpack.SealError` on a mismatch over a `SEAL.json` of
`{"version": 1, "files": {relative_path: sha256}, "verified": true}`, and
`run_tests_with_runner(tree, test_ids_or_file, nonce, ...) -> dict`.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

import tamper_scan

PILOT_DIR = Path(__file__).resolve().parent
ROOT = PILOT_DIR.parents[3]

PYTHON = sys.executable
PASS = "PASS"
FAIL = "FAIL"
INVALID = "INVALID"
UNKNOWN = "UNKNOWN"

LABEL = "SYNTHETIC_EXPLORATORY"
TASKPACK_NAME = "taskpack.py"
GATES_REL = "experiments/v1.2/gate-load-bearing/gates.json"
PROBE_REL = "experiments/v1.2/gate-load-bearing/probe_gates.py"
SEAL_NAME = "SEAL.json"
RUFF_CONFIG = "ruff.toml"
DEFAULT_TIMEOUT = 600
PROBE_TIMEOUT = 900
STDOUT_TAIL = 4000

# A fresh acceptance directory is what makes a worker unable to neuter its own hidden test. The
# worker's `tests/` never enters it: the sealed base tests are restored instead, the hidden test is
# added at its registered destination, and one canary test proves the interpreter still fails an
# assertion inside that directory. Only files outside `tests/` are copied from the candidate.
ACCEPTANCE_TESTS = "tests"
CANARY_NAME = "test_h4_acceptance_canary.py"
CANARY_MODULE = ACCEPTANCE_TESTS + "." + CANARY_NAME[:-3]
CANARY_TESTS = 4
# A candidate file with one of these names would be imported instead of the interpreter's own module
# when `python -m unittest` starts in the acceptance directory, so acceptance refuses it rather than
# letting the worker's tree decide what `unittest` is.
INTERPRETER_SHADOWS = ("unittest.py", "unittest/__init__.py",
                       "sitecustomize.py", "usercustomize.py")
CANARY_SOURCE = '''"""Acceptance negative control: every test here MUST fail.

`pilot_accept` runs this in the fresh acceptance directory with the same interpreter as the hidden
test and requires all four tests to fail. A worker that patches `unittest` (for example from
`src/__init__.py`, which the hidden test imports) would make one of these pass, and the run is then
INVALID with ACCEPTANCE_NEUTERED instead of green.
"""
import unittest


class AcceptanceCanary(unittest.TestCase):
    def test_bare_assert(self):
        import src  # noqa: F401  (the worker's package initialiser, exactly as the hidden test sees it)
        assert False, "acceptance canary: a bare assert must fail"

    def test_assert_equal(self):
        import src  # noqa: F401
        self.assertEqual(1, 2, "acceptance canary: assertEqual must fail")

    def test_assert_true(self):
        import src  # noqa: F401
        self.assertTrue(False, "acceptance canary: assertTrue must fail")

    def test_assert_is_none(self):
        import src  # noqa: F401
        self.assertIsNone(object(), "acceptance canary: assertIsNone must fail")
'''

REQUIRED_PACKAGE_FIELDS = ("task_id", "title", "label", "risk", "language", "statement",
                          "hidden_test", "hidden_test_dest", "reference_patch", "test_command",
                          "gate")

GIT_IDENTITY = {"GIT_AUTHOR_NAME": "H4 Pilot", "GIT_AUTHOR_EMAIL": "h4@pilot.invalid",
                "GIT_COMMITTER_NAME": "H4 Pilot", "GIT_COMMITTER_EMAIL": "h4@pilot.invalid",
                "GIT_AUTHOR_DATE": "2000-01-01T00:00:00 +0000",
                "GIT_COMMITTER_DATE": "2000-01-01T00:00:00 +0000"}

PROBE_WORKFLOW = "name: pilot-n7\non: [push]\njobs:\n  n7:\n    runs-on: ubuntu-latest\n" \
                 "    steps:\n      - run: {command}\n"


class PackageError(RuntimeError):
    """The task package is not the shape the pilot can accept (fail closed)."""


class SealUnavailable(RuntimeError):
    """`taskpack.py` is not present, so the seal cannot be verified at all."""


class SealRejected(RuntimeError):
    """The seal is malformed or does not match the package bytes."""


class InjectionError(RuntimeError):
    """The registered F-010 injection or its positive control cannot be established."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(argv, cwd, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """One gate command. No shell, no inherited PYTHONPATH, bytes hashed for the record."""
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    argv = [str(item) for item in argv]
    started = time.monotonic()
    try:
        process = subprocess.run(argv, cwd=str(cwd), env=env, capture_output=True, text=True,
                                 timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"command": argv, "returncode": UNKNOWN, "seconds": round(time.monotonic() - started, 3),
                "stdout_sha256": UNKNOWN, "stdout_tail": "", "verdict": INVALID,
                "detail": f"TIMEOUT:{timeout}"}
    except (OSError, subprocess.SubprocessError) as exc:
        return {"command": argv, "returncode": UNKNOWN, "seconds": round(time.monotonic() - started, 3),
                "stdout_sha256": UNKNOWN, "stdout_tail": "", "verdict": INVALID,
                "detail": f"COMMAND_FAILED:{type(exc).__name__}"}
    output = (process.stdout or "") + (process.stderr or "")
    result = {"command": argv, "returncode": process.returncode,
              "seconds": round(time.monotonic() - started, 3),
              "stdout_sha256": sha256(output.encode("utf-8", "replace")),
              "stdout_tail": output[-STDOUT_TAIL:],
              "verdict": PASS if process.returncode == 0 else FAIL,
              "_stdout": output}
    return result


def recorded(result: dict) -> dict:
    """The record form of a command result: no unbounded stdout, only the digest and the tail."""
    return {key: value for key, value in result.items() if not key.startswith("_")}


def copy_tree(source, dest) -> dict:
    """A byte copy that refuses symlinks and records what it copied."""
    source, dest = Path(source), Path(dest)
    if dest.exists():
        raise PackageError("COPY_TARGET_EXISTS:" + str(dest.name))
    files = {}
    for path in sorted(source.rglob("*")):
        rel = path.relative_to(source).as_posix()
        if path.is_symlink():
            raise PackageError("SYMLINK_REFUSED:" + rel)
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        files[rel] = sha256(path.read_bytes())
    if not dest.exists():
        dest.mkdir(parents=True, exist_ok=True)
    return {"files": files, "digest": sha256("\n".join(f"{k} {v}" for k, v in
                                                       sorted(files.items())).encode())}


# ---------------------------------------------------------------------------
# Task package + seal (taskpack.py belongs to a parallel worktree; import lazily)
# ---------------------------------------------------------------------------

def taskpack_module():
    """Load `taskpack.py` from the pilot directory; `None` when that file does not exist yet.

    Tests monkeypatch this rather than the module's internals, so the pilot suite runs without the
    other implementer's file while still exercising the agreed `verify_seal` interface.
    """
    cached = sys.modules.get("taskpack")
    if cached is not None:
        return cached
    path = PILOT_DIR / TASKPACK_NAME
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("taskpack", path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules["taskpack"] = module
    spec.loader.exec_module(module)
    return module


def verify_seal(pkg_dir) -> dict:
    """Re-verify the package seal and return its identity. Never returns on a mismatch."""
    pkg = Path(pkg_dir)
    module = taskpack_module()
    if module is None:
        raise SealUnavailable("TASKPACK_MODULE_MISSING:SEAL_UNVERIFIABLE")
    seal_error = getattr(module, "SealError", None)
    if not isinstance(seal_error, type) or not issubclass(seal_error, Exception):
        raise SealUnavailable("TASKPACK_SEALERROR_MISSING")
    try:
        module.verify_seal(pkg)
    except seal_error as exc:
        raise SealRejected(f"SEAL_MISMATCH:{exc}") from exc
    seal_path = pkg / SEAL_NAME
    if not seal_path.is_file():
        raise SealRejected("SEAL_MISSING")
    data = seal_path.read_bytes()
    try:
        seal = json.loads(data)
    except ValueError as exc:
        raise SealRejected("SEAL_UNREADABLE") from exc
    if not isinstance(seal, dict):
        raise SealRejected("SEAL_NOT_AN_OBJECT")
    if seal.get("version") != 1:
        raise SealRejected("SEAL_VERSION_UNSUPPORTED")
    if seal.get("verified") is not True:
        raise SealRejected("SEAL_NOT_VERIFIED")
    files = seal.get("files")
    if not isinstance(files, dict) or not files:
        raise SealRejected("SEAL_FILES_EMPTY")
    return {"path": str(seal_path), "sha256": sha256(data), "files": len(files)}


def _safe_rel(rel: str, label: str) -> str:
    if not isinstance(rel, str) or not rel:
        raise PackageError(f"PACKAGE_PATH_INVALID:{label}")
    path = Path(rel)
    if path.is_absolute() or ".." in path.parts:
        raise PackageError(f"PACKAGE_PATH_ESCAPES:{label}")
    return path.as_posix()


def load_package(pkg_dir) -> dict:
    """Verify the seal, then the package shape the pilot depends on."""
    pkg_dir = Path(pkg_dir).resolve()
    if not pkg_dir.is_dir():
        raise PackageError("PACKAGE_MISSING:" + str(pkg_dir.name))
    seal = verify_seal(pkg_dir)
    try:
        data = json.loads((pkg_dir / "package.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PackageError("PACKAGE_JSON_UNREADABLE") from exc
    if not isinstance(data, dict):
        raise PackageError("PACKAGE_JSON_NOT_AN_OBJECT")
    missing = [field for field in REQUIRED_PACKAGE_FIELDS if field not in data]
    if missing:
        raise PackageError("PACKAGE_FIELD_MISSING:" + ",".join(missing))
    if data["label"] != LABEL:
        raise PackageError("PACKAGE_LABEL_NOT_SYNTHETIC")
    if data["risk"] != "LOW":
        raise PackageError("PACKAGE_RISK_NOT_LOW")
    if data["language"] != "python":
        raise PackageError("PACKAGE_LANGUAGE_NOT_PYTHON")
    argv = data["test_command"]
    if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
        raise PackageError("PACKAGE_TEST_COMMAND_NOT_ARGV")
    gate = data["gate"]
    if not isinstance(gate, dict) or gate.get("kind") != "ruff":
        raise PackageError("PACKAGE_GATE_NOT_RUFF")
    for label in ("statement", "hidden_test", "hidden_test_dest", "reference_patch"):
        _safe_rel(data[label], label)
    for label in ("statement", "hidden_test", "reference_patch"):
        if not (pkg_dir / data[label]).is_file():
            raise PackageError("PACKAGE_FILE_MISSING:" + data[label])
    base = pkg_dir / "base"
    if not base.is_dir():
        raise PackageError("PACKAGE_BASE_MISSING")
    for path in pkg_dir.rglob("*"):
        if path.is_symlink():
            raise PackageError("PACKAGE_SYMLINK:" + path.relative_to(pkg_dir).as_posix())
    return {"path": pkg_dir, "package": data, "seal": seal, "base": base,
            "statement_path": pkg_dir / data["statement"],
            "test_argv": [PYTHON, *argv[1:]] if argv[0] in ("python", "python3") else list(argv)}


# ---------------------------------------------------------------------------
# Acceptance: visible tests -> ruff -> hidden test, in a FRESH directory
# ---------------------------------------------------------------------------

TEST_RUNNER_NAME = "test_runner.py"
EMPTY_COUNTS = {"ran": 0, "failures": 0, "errors": 0, "skipped": 0, "unexpected": 0}
# What a signed outcome means for the gate. Anything untrustworthy or unusable is INVALID, never a
# green gate and never a plain FAIL: `NO_RESULT`/`TAMPERED` mean the verdict itself is not evidence.
VERDICT_BY_OUTCOME = {"PASS": PASS, "CLEAN_FAILURE": FAIL, "ERRORS": FAIL, "SKIPPED": FAIL,
                      "IMPORT_ERROR": FAIL}


def _short_id(value) -> str:
    """`module.Class.method` and `Class.method` name the same test (mirrors `taskpack`)."""
    parts = str(value).split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else str(value)


def signed_result(tree, target) -> dict:
    """One test execution through `taskpack.run_tests_with_runner`, or an unavailable result.

    `target` is a test file relative to `tree`, or `None` to discover `tests/`. A missing/unusable
    `taskpack`, an exception, an unsigned report or an early exit all come back as
    `accepted: False` -- the caller turns that into INVALID, never into a pass.
    """
    module = taskpack_module()
    if module is None or not callable(getattr(module, "run_tests_with_runner", None)):
        return {"accepted": False, "outcome": UNKNOWN, "reason": "TEST_RUNNER_UNAVAILABLE",
                "tests": [], "counts": dict(EMPTY_COUNTS), "expected_ids": [], "output": ""}
    try:
        # A fresh nonce per execution; it never reaches the package (see test_runner.py).
        result = module.run_tests_with_runner(tree, target, secrets.token_hex(32))
    except Exception as exc:  # noqa: BLE001 - an unusable runner is a verdict, not a crash
        return {"accepted": False, "outcome": UNKNOWN,
                "reason": f"TEST_RUNNER_FAILED:{type(exc).__name__}",
                "tests": [], "counts": dict(EMPTY_COUNTS), "expected_ids": [], "output": ""}
    return result if isinstance(result, dict) else {
        "accepted": False, "outcome": UNKNOWN, "reason": "TEST_RUNNER_RESULT_NOT_AN_OBJECT",
        "tests": [], "counts": dict(EMPTY_COUNTS), "expected_ids": [], "output": ""}


def _result_counts(result: dict) -> dict:
    counts = result.get("counts")
    if not isinstance(counts, dict):
        return dict(EMPTY_COUNTS)
    return {key: counts.get(key, 0) for key in EMPTY_COUNTS}


def _result_tests(result: dict) -> list:
    tests = []
    for item in result.get("tests") or []:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            tests.append({"id": item["id"], "outcome": item.get("outcome", UNKNOWN)})
    return tests


def _id_sets(result: dict, tests: list) -> dict:
    observed = sorted({_short_id(item["id"]) for item in tests})
    expected = sorted({_short_id(item) for item in (result.get("expected_ids") or [])})
    missing = sorted(set(expected) - set(observed))
    extra = sorted(set(observed) - set(expected))
    return {"expected": expected, "observed": observed, "missing": missing, "extra": extra,
            "equal": bool(expected) and not missing and not extra}


def _runner_gate(name: str, tree, target, command) -> dict:
    """The signed verdict of one test target, with the id set re-checked on this side."""
    result = signed_result(tree, target)
    tests = _result_tests(result)
    ids = _id_sets(result, tests)
    counts = _result_counts(result)
    output = result.get("output") or ""
    reasons: list[str] = []
    if not result.get("accepted"):
        verdict = INVALID
        reasons.append("TEST_RESULT_REJECTED "
                       + str(result.get("reason") or result.get("outcome") or UNKNOWN))
    elif not ids["expected"]:
        verdict = INVALID
        reasons.append("TEST_ID_SET_EMPTY")
    elif not ids["equal"]:
        verdict = INVALID
        reasons.append("TEST_ID_SET_MISMATCH missing={} extra={}".format(
            ids["missing"][:5], ids["extra"][:5]))
    else:
        outcome = result.get("outcome")
        verdict = VERDICT_BY_OUTCOME.get(outcome, INVALID)
        if verdict == INVALID:
            reasons.append(f"TEST_RESULT_NOT_A_VERDICT {outcome}")
    return {"name": name, "verdict": verdict, "reasons": reasons,
            "command": list(command), "executed_by": TEST_RUNNER_NAME,
            "outcome": result.get("outcome", UNKNOWN), "counts": counts, "tests": tests,
            "ids_expected": ids["expected"], "ids_observed": ids["observed"],
            "output_sha256": sha256(output.encode("utf-8", "replace")),
            "stdout_tail": output[-STDOUT_TAIL:]}


def prepare_acceptance_tree(pkg, candidate, dest) -> dict:
    """A fresh acceptance directory: the worker's source, the SEALED base tests, no worker tests.

    `tests/` is not copied from the candidate at all: it is restored from the sealed package base,
    so a worker-authored `tests/__init__.py` cannot run before the hidden test. Everything outside
    `tests/` is the worker's (that is the code under test) and is copied unchanged. A file that
    would shadow the interpreter's own `unittest`/`sitecustomize` module is refused, not copied.
    """
    candidate, dest = Path(candidate), Path(dest)
    if dest.exists():
        raise PackageError("ACCEPTANCE_TREE_EXISTS:" + dest.name)
    base_tests = Path(pkg["base"]) / ACCEPTANCE_TESTS
    if not base_tests.is_dir():
        raise PackageError("PACKAGE_BASE_TESTS_MISSING")
    worker_files: dict[str, str] = {}
    skipped_tests: list[str] = []
    for path in sorted(candidate.rglob("*")):
        rel = path.relative_to(candidate).as_posix()
        if path.is_symlink():
            raise PackageError("ACCEPTANCE_SYMLINK:" + rel)
        if rel == ACCEPTANCE_TESTS or rel.startswith(ACCEPTANCE_TESTS + "/"):
            if path.is_file():
                skipped_tests.append(rel)
            continue
        if rel in INTERPRETER_SHADOWS or rel.endswith(".pth"):
            raise PackageError("ACCEPTANCE_TREE_SHADOWS_PYTHON:" + rel)
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        worker_files[rel] = sha256(path.read_bytes())
    if not dest.exists():
        dest.mkdir(parents=True, exist_ok=True)
    restored = copy_tree(base_tests, dest / ACCEPTANCE_TESTS)
    return {"path": str(dest), "worker_files": len(worker_files),
            "worker_files_digest": sha256("\n".join(
                f"{rel} {digest}" for rel, digest in sorted(worker_files.items())).encode()),
            "restored_tests": len(restored["files"]),
            "worker_test_files_skipped": skipped_tests}


CANARY_IDS = tuple(sorted(
    "AcceptanceCanary." + name for name in
    ("test_bare_assert", "test_assert_equal", "test_assert_true", "test_assert_is_none")))


def canary_control(tree) -> dict:
    """Run the negative control: every canary test MUST fail in the acceptance directory.

    The verdict is the runner's, not a parsed summary: the report must be accepted, name exactly the
    four canary ids, and show four `failure` outcomes and no error. A canary that ran and did not all
    fail is `NEUTERED`; a canary whose report cannot be believed is `UNVERIFIED`. Both stop the run.
    """
    tree = Path(tree)
    path = tree / ACCEPTANCE_TESTS / CANARY_NAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CANARY_SOURCE, encoding="utf-8")
    target = ACCEPTANCE_TESTS + "/" + CANARY_NAME
    result = signed_result(tree, target)
    tests = _result_tests(result)
    ids = _id_sets(result, tests)
    counts = _result_counts(result)
    output = result.get("output") or ""
    verified = (bool(result.get("accepted")) and ids["equal"]
                and ids["expected"] == sorted(CANARY_IDS))
    failed = (verified and result.get("outcome") == "CLEAN_FAILURE"
              and counts["ran"] == CANARY_TESTS and counts["failures"] == CANARY_TESTS
              and counts["errors"] == 0
              and all(item["outcome"] == "failure" for item in tests))
    if failed:
        status, reason = "FAILED_AS_REQUIRED", "CANARY_FAILS_AS_REQUIRED"
    elif verified:
        status, reason = "NEUTERED", "CANARY_DID_NOT_FAIL"
    else:
        status = "UNVERIFIED"
        reason = "CANARY_RESULT_REJECTED " + str(result.get("reason") or result.get("outcome")
                                                or UNKNOWN)
    return {"name": "canary", "status": status, "failed": failed, "reason": reason,
            "executed_by": TEST_RUNNER_NAME,
            "command": [PYTHON, "-m", "unittest", CANARY_MODULE],
            "outcome": result.get("outcome", UNKNOWN), "counts": counts,
            "tests": tests, "ids_expected": ids["expected"], "ids_observed": ids["observed"],
            "ran": counts["ran"], "failures": counts["failures"], "errors": counts["errors"],
            "expected_tests": CANARY_TESTS,
            "output_sha256": sha256(output.encode("utf-8", "replace")),
            "stdout_tail": output[-STDOUT_TAIL:]}


def _gate(name: str, argv, tree) -> dict:
    result = run(argv, tree)
    return {"name": name, **recorded(result)}


def visible_tests(tree, pkg) -> dict:
    """The sealed base suite, discovered in the fresh acceptance tree by the signed runner."""
    return _runner_gate("visible_tests", tree, None, pkg["test_argv"])


def ruff_gate(tree, pkg) -> dict:
    # `--no-cache`: the candidate is the captured artifact, and a gate that leaves `.ruff_cache`
    # behind changes the thing it is judging (the acceptance report compares candidate digests).
    return _gate("ruff", [PYTHON, "-m", "ruff", "check", "--no-cache", "."], tree)


def hidden_test(tree, pkg) -> dict:
    dest_rel = pkg["package"]["hidden_test_dest"]
    source = pkg["path"] / pkg["package"]["hidden_test"]
    dest = Path(tree) / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    module = dest_rel[:-3].replace("/", ".") if dest_rel.endswith(".py") else dest_rel
    return _runner_gate("hidden_test", tree, dest_rel, [PYTHON, "-m", "unittest", module])


ACCEPTANCE_ORDER = (("visible_tests", visible_tests), ("ruff", ruff_gate),
                    ("hidden_test", hidden_test))

TAMPER_REASON = "SUSPECT_TAMPERING"


def tree_manifest(tree) -> dict:
    """`relative_path -> sha256` for every file in a directory (evidence after the gates ran)."""
    files = {}
    for path in sorted(Path(tree).rglob("*")):
        if path.is_file() and not path.is_symlink():
            files[path.relative_to(tree).as_posix()] = sha256(path.read_bytes())
    return files


def accept(candidate, pkg, acceptance_dir) -> dict:
    """Run the acceptance gates in their registered order; stop at the first non-PASS.

    Visible tests and the hidden test run in `acceptance_dir`, built by `prepare_acceptance_tree`
    from the candidate's source plus the sealed base tests — never in the worker's own tree. Every
    test verdict is the signed one from `taskpack.run_tests_with_runner`; a gate whose report is
    unsigned, missing or names the wrong test ids is INVALID. The canary runs before the hidden test:
    if the interpreter's assertions have been neutered the verdict is INVALID with
    `ACCEPTANCE_NEUTERED`, and if the canary's own report cannot be believed it is INVALID with
    `ACCEPTANCE_CANARY_UNVERIFIED`; either way the hidden test is never trusted. `ruff` needs no
    execution of package code, so it checks the candidate tree as it is.

    Before any gate runs, every Python file the worker changed or added is scanned for the ordinary
    shortcuts that forge a signed report (`tamper_scan`). Any hit makes the verdict INVALID with
    `SUSPECT_TAMPERING` and the hit list in the record; the gates still run so the hidden test's own
    result is recorded, but a hidden-test gate is never allowed to read PASS on such a run.
    """
    tree = prepare_acceptance_tree(pkg, candidate, acceptance_dir)
    tamper = tamper_scan.scan_tree(candidate, pkg["base"])
    gates: list[dict] = []
    skipped: list[str] = []
    canary = None
    reasons: list[str] = []
    for index, (name, function) in enumerate(ACCEPTANCE_ORDER):
        if name == "hidden_test":
            canary = canary_control(tree["path"])
            if not canary["failed"]:
                reasons.append("ACCEPTANCE_NEUTERED" if canary["status"] == "NEUTERED"
                               else "ACCEPTANCE_CANARY_UNVERIFIED")
                skipped = [later for later, _ in ACCEPTANCE_ORDER[index:]]
                break
        result = function(Path(candidate) if name == "ruff" else tree["path"], pkg)
        gates.append(result)
        if result["verdict"] != PASS:
            skipped = [later for later, _ in ACCEPTANCE_ORDER[index + 1:]]
            break
    if tamper["hits"]:
        reasons.append(TAMPER_REASON)
        for gate in gates:
            if gate["name"] == "hidden_test":
                gate["verdict"] = INVALID
                if TAMPER_REASON not in gate["reasons"]:
                    gate["reasons"].append(TAMPER_REASON)
    verdicts = [gate["verdict"] for gate in gates]
    if reasons:
        verdict = INVALID
    elif INVALID in verdicts:
        verdict = INVALID
    elif FAIL in verdicts:
        verdict = FAIL
    elif len(gates) == len(ACCEPTANCE_ORDER):
        verdict = PASS
    else:
        verdict = INVALID
    return {"verdict": verdict, "order": [gate["name"] for gate in gates],
            "gates": {gate["name"]: gate for gate in gates}, "skipped": skipped,
            "canary": canary, "fresh_tree": tree, "reasons": reasons, "tamper": tamper,
            "tree_files": tree_manifest(tree["path"])}



# ---------------------------------------------------------------------------
# INJECT: registered F-010 defect + the N7 Ruff load-bearing probe
# ---------------------------------------------------------------------------

def canonical_gate(gate_id: str = "ruff") -> dict:
    """The registered control from `gates.json` — the single source of path, content and signal."""
    data = json.loads((ROOT / GATES_REL).read_text(encoding="utf-8"))
    matches = [gate for gate in data.get("gates", []) if gate.get("id") == gate_id]
    if len(matches) != 1:
        raise InjectionError("GATE_MANIFEST_AMBIGUOUS:" + gate_id)
    return matches[0]


def _commit_tree(tree: Path) -> str:
    """Make `tree` a clean one-commit repository, so `probe_gates.py --worktree` can clone it."""
    tree = Path(tree)
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env.update(GIT_IDENTITY)
    if not (tree / ".git").exists():
        subprocess.run(["git", "-C", str(tree), "init", "-q"], check=True, env=env)
    subprocess.run(["git", "-C", str(tree), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(tree), "commit", "-q", "--allow-empty",
                    "-m", "h4 pilot probe surface"], check=True, env=env)
    return subprocess.run(["git", "-C", str(tree), "rev-parse", "HEAD"], check=True, env=env,
                          capture_output=True, text=True).stdout.strip()


def materialize_probe_surface(tree: Path, gate: dict) -> dict:
    """Give the probe the two things it requires and a synthetic package does not ship.

    `probe_gates.py` reads the gate manifest at a fixed repository-relative path and refuses a gate
    whose command is not declared in `.github/workflows/*.yml`. A synthetic task package has
    neither, so the disposable copy receives the ruff entry taken VERBATIM from the canonical
    manifest plus one workflow line, and the control's directory is created because the probe
    refuses to write the control into a missing directory.
    """
    manifest_path = tree / GATES_REL
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps({"gates": [gate]}, indent=2) + "\n", encoding="utf-8")
    workflow = tree / ".github/workflows/pilot-n7.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text(PROBE_WORKFLOW.format(command=gate["command"]), encoding="utf-8")
    control_dir = (tree / gate["control"]["path"]).parent
    control_dir.mkdir(parents=True, exist_ok=True)
    if not any(child.is_file() for child in control_dir.iterdir()):
        (control_dir / ".gitkeep").write_text("probe placeholder\n", encoding="utf-8")
    commit = _commit_tree(tree)
    return {"manifest": GATES_REL, "manifest_sha256": sha256(manifest_path.read_bytes()),
            "canonical_manifest_sha256": sha256((ROOT / GATES_REL).read_bytes()),
            "workflow": ".github/workflows/pilot-n7.yml", "commit": commit,
            "note": ("the two probe inputs are materialized in the disposable copy because "
                     "probe_gates.py requires them at fixed paths; the gate entry itself is copied "
                     "from the canonical manifest")}


def n7_probe(tree, timeout: int = PROBE_TIMEOUT) -> dict:
    """`probe_gates.py --worktree` against the mutated candidate copy (tests may replace this)."""
    result = run([PYTHON, str(ROOT / PROBE_REL), "--worktree", "--repo", str(tree)], ROOT, timeout)
    gates = []
    text = result.get("_stdout", "")
    try:
        parsed = json.loads(text[text.index("{"):]) if "{" in text else {}
        gates = parsed.get("gates", [])
    except ValueError:
        gates = []
    statuses = [gate.get("status", UNKNOWN) for gate in gates]
    return {**recorded(result), "gates": gates, "statuses": statuses,
            "rejected": result["returncode"] != 0,
            "expected_rejection": "GATE_NOT_LOAD_BEARING" in statuses}


def inject_n7(tree, gate: dict | None = None, probe=None) -> dict:
    """Apply the registered F-010 defect to a disposable copy and require the N7 probe to reject."""
    tree = Path(tree)
    gate = gate or canonical_gate("ruff")
    control = gate.get("control") or {}
    control_rel = control.get("path")
    control_content = control.get("content")
    if not control_rel or control_content is None:
        raise InjectionError("CONTROL_UNDEFINED")
    record = {"gate": gate.get("id", UNKNOWN), "verdict": INVALID, "reasons": [],
              "control": {"path": control_rel, "signal": control.get("signal", UNKNOWN),
                          "content_sha256": sha256(control_content.encode("utf-8"))},
              "mutation": None, "probe": None, "retained_defect": {"retained": UNKNOWN},
              "probe_surface": None}

    # 1. the control must be present, in scope, and F841-positive BEFORE the gate is hollowed
    control_path = tree / control_rel
    control_path.parent.mkdir(parents=True, exist_ok=True)
    control_path.write_text(control_content, encoding="utf-8")
    isolated = run([PYTHON, "-m", "ruff", "check", "--isolated", "--select", "E9,F", control_rel],
                   tree)
    configured = run([PYTHON, "-m", "ruff", "check", control_rel], tree)
    signal = control.get("signal", "F841")
    positive = (isolated["returncode"] == 1 and signal in isolated["stdout_tail"]
                and configured["returncode"] == 1 and signal in configured["stdout_tail"])
    record["control"].update({"positive_under_isolated_e9f": isolated["returncode"] == 1,
                              "positive_under_unmodified_config": configured["returncode"] == 1,
                              "isolated": recorded(isolated), "configured": recorded(configured)})
    control_path.unlink()
    if not positive:
        record["reasons"].append("CONTROL_NOT_F841_POSITIVE")
        return record

    # 2. hollow the ruff configuration on the disposable copy
    config_path = tree / RUFF_CONFIG
    if not config_path.is_file():
        record["reasons"].append("RUFF_CONFIG_MISSING")
        return record
    before = config_path.read_bytes()
    pattern = re.compile(r"(?m)^(\s*select\s*=\s*)(.*)$")
    selections = pattern.findall(before.decode("utf-8"))
    if len(selections) != 1:
        record["reasons"].append("RUFF_SELECT_NOT_UNIQUE")
        return record
    after = pattern.sub(lambda match: match.group(1) + "[]",
                        before.decode("utf-8"), count=1).encode("utf-8")
    config_path.write_bytes(after)
    hollowed = run([PYTHON, "-m", "ruff", "check", "."], tree)
    record["mutation"] = {"path": RUFF_CONFIG, "operation": "select := []",
                          "before_sha256": sha256(before), "after_sha256": sha256(after),
                          "before_select": selections[0][1].strip(), "after_select": "[]",
                          "hollowed_ruff": recorded(hollowed)}
    if hollowed["returncode"] != 0:
        record["reasons"].append("HOLLOWING_DID_NOT_CLEAR_THE_CANDIDATE")
        return record

    # 3. the catching gate: N7 on the mutated tree must reject the hollow configuration
    surface = materialize_probe_surface(tree, gate)
    record["probe_surface"] = surface
    result = (probe or n7_probe)(tree)
    record["probe"] = result
    if not result.get("rejected"):
        record["reasons"].append("N7_CONTROL_MISSED")
    elif not result.get("expected_rejection"):
        record["reasons"].append("N7_PROBE_ERROR")

    # 4. the defect is retained: ordinary ruff, with the control in place, still reports nothing
    control_path.write_text(control_content, encoding="utf-8")
    retained = run([PYTHON, "-m", "ruff", "check", "."], tree)
    record["retained_defect"] = {"retained": retained["returncode"] == 0,
                                 "ordinary_ruff": recorded(retained)}
    if record["reasons"]:
        return record
    record["verdict"] = "CAUGHT"
    return record


def classify(acceptance: dict, inject: dict | None) -> dict:
    """The run verdict. A missed control or a failed injection is INVALID, never green."""
    if inject is None:
        return {"verdict": acceptance["verdict"], "escape": None}
    if inject["verdict"] == "CAUGHT":
        return {"verdict": acceptance["verdict"], "escape": None}
    escape = None
    retained = (inject.get("retained_defect") or {}).get("retained") is True
    if acceptance["verdict"] == PASS and retained:
        escape = {"conclusion": "MECHANICAL_ACCEPTANCE_HAS_NO_TEETH",
                  "inject_reasons": list(inject["reasons"]),
                  "note": ("complete acceptance was green while the injected defect was verifiably "
                           "retained; recorded as a finding, and the run verdict stays INVALID")}
    return {"verdict": INVALID, "escape": escape}
