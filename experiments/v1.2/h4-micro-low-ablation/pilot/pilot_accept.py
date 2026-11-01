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

`taskpack.py` is another implementer's file in a parallel worktree, so it is imported lazily through
`taskpack_module()`; tests replace that function with a stand-in. The agreed interface is
`verify_seal(pkg_dir) -> None`, raising `taskpack.SealError` on a mismatch, over a `SEAL.json` of
`{"version": 1, "files": {relative_path: sha256}, "verified": true}`.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

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
# Acceptance: visible tests -> ruff -> hidden test
# ---------------------------------------------------------------------------

def _gate(name: str, argv, tree) -> dict:
    result = run(argv, tree)
    return {"name": name, **recorded(result)}


def visible_tests(tree, pkg) -> dict:
    return _gate("visible_tests", pkg["test_argv"], tree)


def ruff_gate(tree, pkg) -> dict:
    return _gate("ruff", [PYTHON, "-m", "ruff", "check", "."], tree)


def hidden_test(tree, pkg) -> dict:
    dest_rel = pkg["package"]["hidden_test_dest"]
    source = pkg["path"] / pkg["package"]["hidden_test"]
    dest = Path(tree) / dest_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, dest)
    module = dest_rel[:-3].replace("/", ".") if dest_rel.endswith(".py") else dest_rel
    return _gate("hidden_test", [PYTHON, "-m", "unittest", module], tree)


ACCEPTANCE_ORDER = (("visible_tests", visible_tests), ("ruff", ruff_gate),
                    ("hidden_test", hidden_test))


def accept(tree, pkg) -> dict:
    """Run the acceptance gates in their registered order; stop at the first non-PASS."""
    gates = []
    skipped = []
    for index, (name, function) in enumerate(ACCEPTANCE_ORDER):
        result = function(tree, pkg)
        gates.append(result)
        if result["verdict"] != PASS:
            skipped = [later for later, _ in ACCEPTANCE_ORDER[index + 1:]]
            break
    verdicts = [gate["verdict"] for gate in gates]
    if INVALID in verdicts:
        verdict = INVALID
    elif FAIL in verdicts:
        verdict = FAIL
    elif len(gates) == len(ACCEPTANCE_ORDER):
        verdict = PASS
    else:
        verdict = INVALID
    return {"verdict": verdict, "order": [gate["name"] for gate in gates],
            "gates": {gate["name"]: gate for gate in gates}, "skipped": skipped}


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
