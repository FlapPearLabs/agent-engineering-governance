#!/usr/bin/env python3
"""Model-free verifier, sealer and CLI for one H4 pilot task package.

A task package is the maker's only deliverable (see ``PILOT_SPEC.md``). This module
decides, without a model and without network, whether a package may be used at all.
Nothing here produces an experiment result; a PASS only means the package obeys the
package contract.

Seven checks, all of which must hold (``verify_package`` returns one verdict per
check, never an exception for a bad package):

1. ``structure`` -- required files present, no extra files, no symlinks, every path
   inside the package; ``package.json`` carries the exact contract values.
2. ``base`` -- the project's own test command passes at ``base/`` and ``ruff check``
   is clean there.
3. ``hidden_at_base`` -- the hidden test, copied to ``hidden_test_dest``, is a CLEAN
   unittest failure at base: ``failures>0``, ``errors=0``, ``skipped=0``, at least one
   test collected, no ``ImportError``/``ModuleNotFoundError``.
4. ``reference`` -- after ``reference.patch`` the hidden test passes, the visible tests
   still pass, and ruff is still clean.
5. ``statement`` -- no >= 8-token run of the hidden test appears in ``statement.md``,
   and the statement names no experiment, governance or oracle vocabulary.
6. ``risk_low`` -- LOW by rule: the patch changes <= 60 lines in 1-2 non-test files and
   a keyword screen finds no security, credential, concurrency, governance or network
   content. THE KEYWORD SCREEN IS A DOCUMENTED HEURISTIC, not a semantic judgement. Its
   term list is ``RISK_SCREEN_TERMS``; it cannot see meaning, so a task whose words look
   ordinary but whose behaviour is security- or concurrency-relevant still passes this
   screen and remains a human/experiment-level concern.
7. ``seal`` -- ``SEAL.json`` is present and matches every byte, or is absent, which the
   package-level verdict reports as ``NOT_SEALED`` (never silently folded into PASS).
   ``seal_package`` writes the seal only after checks 1-6 pass; ``verify_seal`` raises
   ``SealError`` on any missing, extra or changed file and is what later steps call.

Isolation rule: package code is never executed in place. ``verify_package`` copies the
package into a fresh temporary directory and runs every command there, with ``HOME`` and
``TMPDIR`` redirected into that directory, ``PYTHONPATH`` dropped and bytecode writing
off. The only commands it will run are the package's own unittest argv (argv[0] must be
``python``/``python3``, rewritten to ``sys.executable``) and ``sys.executable -m ruff``.
This is process isolation, not a security boundary: package code is ordinary Python and
the OS-level confinement of a worker sandbox does not apply to it.

CLI::

    python taskpack.py verify <pkg>    # exit 0 = PASS, 1 = FAIL, prints the JSON verdict
    python taskpack.py seal <pkg>      # prints the verdict, seals only on PASS
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

LABEL = "SYNTHETIC_EXPLORATORY"
RISK = "LOW"
LANGUAGE = "python"
SEAL_NAME = "SEAL.json"
SEAL_VERSION = 1
CHECK_COUNT = 7
MAX_PATCH_CHANGED_LINES = 60
MAX_PATCH_FILES = 2
LEAK_NGRAM = 8
RUN_TIMEOUT = 180

CHECK_NAMES = {
    1: "structure",
    2: "base",
    3: "hidden_at_base",
    4: "reference",
    5: "statement",
    6: "risk_low",
    7: "seal",
}

# The package contract fixes these values, so "no extra files" has a closed meaning.
EXPECTED_STRINGS = {
    "label": LABEL,
    "risk": RISK,
    "language": LANGUAGE,
    "statement": "statement.md",
    "hidden_test": "hidden/test_hidden.py",
    "hidden_test_dest": "tests/test_hidden.py",
    "reference_patch": "reference.patch",
}
ALLOWED_TOP_LEVEL = {"package.json", "statement.md", "reference.patch", "base", "hidden", SEAL_NAME}

# Check 5: the statement is what the worker reads, so it must not name experiment
# structure, governance vocabulary or the oracle itself.
STATEMENT_BANNED = (
    (re.compile(r"\barms?\b", re.IGNORECASE), "ARM_MENTION"),
    (re.compile(r"\bgovernance\b", re.IGNORECASE), "GOVERNANCE_MENTION"),
    (re.compile(r"\binject(?:ion|ed|ing|s)?\b", re.IGNORECASE), "INJECT_MENTION"),
    (re.compile(r"\bFULL\b"), "FULL_MENTION"),
    (re.compile(r"\bMIN\b"), "MIN_MENTION"),
    (re.compile(r"\bINJECT\b"), "INJECT_MENTION"),
    (re.compile(r"hidden[ _-]?test", re.IGNORECASE), "HIDDEN_TEST_MENTION"),
    (re.compile(r"test_hidden", re.IGNORECASE), "HIDDEN_TEST_MENTION"),
)

# Check 6 keyword screen. Heuristic by construction: it looks for words, not meaning.
# Deliberately NOT screened because they are ordinary words in small LOW tasks:
# "lock"/"unlock", "parallel", "ticket", "protocol", "server", "root" (as in a root
# directory) and "rule"/"rules" (a task may legitimately fix a rule parser).
RISK_SCREEN_TERMS = (
    # security and credentials
    "password", "passwd", "secret", "credential", "credentials", "api_key", "apikey",
    "token", "oauth", "jwt", "crypto", "cipher", "encrypt", "decrypt", "private_key",
    "sudo", "permission", "permissions", "login", "auth", "authentication", "authorization",
    # concurrency
    "thread", "threads", "threading", "asyncio", "concurrent", "concurrency", "mutex",
    "semaphore", "deadlock", "multiprocessing", "subprocess", "race",
    # governance
    "governance", "policy", "policies", "escalation", "agents.md", "rules.md",
    # network
    "socket", "network", "http", "https", "urllib", "dns",
)
RISK_SCREEN = tuple(
    (re.compile(r"\b" + re.escape(term) + r"\b", re.IGNORECASE), term) for term in RISK_SCREEN_TERMS
)

RAN_RE = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)
TOTAL_RE = re.compile(r"^(?:FAILED|OK) \(([^)]*)\)", re.MULTILINE)
IMPORT_HEADER_RE = re.compile(r"^(?:ImportError|ModuleNotFoundError): ", re.MULTILINE)
TOKEN_RE = re.compile(r"[A-Za-z0-9_]+|[^\sA-Za-z0-9_]")


class SealError(Exception):
    """The package seal is missing, unreadable, or does not match the files on disk."""


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _posix(root, path):
    return PurePosixPath(Path(path).relative_to(root)).as_posix()


def _scan(root):
    """Return (regular files as posix paths, reasons) without following symlinks."""
    root = Path(root)
    files, reasons = [], []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        for name in sorted(dirnames):
            entry = current / name
            if entry.is_symlink():
                reasons.append(f"SYMLINK {_posix(root, entry)}")
                dirnames.remove(name)
        for name in sorted(filenames):
            entry = current / name
            if entry.is_symlink():
                reasons.append(f"SYMLINK {_posix(root, entry)}")
                continue
            if not entry.is_file():
                reasons.append(f"NOT_REGULAR_FILE {_posix(root, entry)}")
                continue
            try:
                entry.resolve().relative_to(root.resolve())
            except ValueError:
                reasons.append(f"OUTSIDE_PACKAGE {_posix(root, entry)}")
                continue
            files.append(_posix(root, entry))
    files.sort()
    return files, reasons


def _sealed_files(root):
    """Every regular file under root, minus the seal itself."""
    files, reasons = _scan(root)
    if reasons:
        raise SealError("; ".join(reasons))
    return [name for name in files if name != SEAL_NAME]


def _environment(home):
    env = {key: value for key, value in os.environ.items() if key in ("PATH", "LANG", "LC_ALL")}
    env.pop("PYTHONPATH", None)
    env.update({
        "HOME": str(home),
        "TMPDIR": str(home / "tmp"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "NO_COLOR": "1",
    })
    return env


def _run(args, cwd, env):
    """Run one command; None means it could not be run to completion at all."""
    try:
        return subprocess.run(args, cwd=str(cwd), env=env, text=True, timeout=RUN_TIMEOUT,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except subprocess.TimeoutExpired:
        return None
    except OSError:
        return None


def _python_argv(argv):
    """The package may name only the interpreter; the verifier runs its own."""
    return [sys.executable] + list(argv[1:])


def _unittest_counts(output):
    counts = {"ran": 0, "failures": 0, "errors": 0, "skipped": 0, "unexpected": 0}
    ran = RAN_RE.search(output)
    if ran:
        counts["ran"] = int(ran.group(1))
    total = TOTAL_RE.search(output)
    if total:
        for item in total.group(1).split(","):
            key, _, value = item.strip().partition("=")
            key = key.strip()
            if key in ("failures", "errors", "skipped"):
                counts[key] = int(value)
            elif key == "unexpected successes":
                counts["unexpected"] = int(value)
    return counts


def _result(check_id, status, reasons=(), data=None):
    return {
        "id": check_id,
        "name": CHECK_NAMES[check_id],
        "status": status,
        "reasons": list(reasons),
        "data": dict(data or {}),
    }


def _safe(check_id, function):
    """A bad package must never crash the verifier; a bug still shows up as ERROR."""
    try:
        return function()
    except Exception as error:  # noqa: BLE001 - the verdict, not the traceback, is the product
        return _result(check_id, "ERROR", [f"{type(error).__name__}: {error}"])


def _check_structure(pkg):
    if not Path(pkg).is_dir():
        return _result(1, "FAIL", ["PACKAGE_MISSING"])
    files, reasons = _scan(pkg)
    manifest_path = Path(pkg) / "package.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError:
        return _result(1, "FAIL", reasons + ["PACKAGE_JSON_MISSING"])
    except ValueError:
        return _result(1, "FAIL", reasons + ["PACKAGE_JSON_INVALID"])
    if not isinstance(manifest, dict):
        return _result(1, "FAIL", reasons + ["PACKAGE_JSON_NOT_AN_OBJECT"])

    for field, expected in EXPECTED_STRINGS.items():
        if manifest.get(field) != expected:
            reasons.append(f"PACKAGE_JSON_FIELD {field} != {expected!r}")
    for field in ("task_id", "title"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            reasons.append(f"PACKAGE_JSON_FIELD {field} missing")
    gate = manifest.get("gate")
    if not isinstance(gate, dict) or gate.get("kind") != "ruff" or gate.get("config") != "ruff.toml":
        reasons.append("PACKAGE_JSON_FIELD gate must be {kind: ruff, config: ruff.toml}")
    command = manifest.get("test_command")
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        reasons.append("PACKAGE_JSON_FIELD test_command must be a non-empty argv list")
    elif command[0] not in ("python", "python3"):
        reasons.append("TEST_COMMAND_NOT_PYTHON")
    elif "-m" not in command or command[command.index("-m") + 1: command.index("-m") + 2] != ["unittest"]:
        reasons.append("TEST_COMMAND_NOT_UNITTEST")

    for name in sorted(os.listdir(pkg)):
        if name not in ALLOWED_TOP_LEVEL:
            reasons.append(f"EXTRA_FILE {name}")
    hidden_dir = Path(pkg) / "hidden"
    if hidden_dir.is_dir():
        for name in sorted(os.listdir(hidden_dir)):
            if name != "test_hidden.py":
                reasons.append(f"EXTRA_FILE hidden/{name}")

    required = [
        "package.json", "statement.md", "reference.patch", "base", "hidden",
        "hidden/test_hidden.py", "base/ruff.toml", "base/src", "base/tests",
    ]
    for name in required:
        if not (Path(pkg) / name).exists():
            reasons.append(f"REQUIRED_MISSING {name}")
    for name in ("base", "hidden", "base/src", "base/tests"):
        path = Path(pkg) / name
        if path.exists() and not path.is_dir():
            reasons.append(f"REQUIRED_NOT_DIRECTORY {name}")
    if (Path(pkg) / "base/src").is_dir() and not list((Path(pkg) / "base/src").rglob("*.py")):
        reasons.append("REQUIRED_MISSING base/src/**/*.py")
    if (Path(pkg) / "base/tests").is_dir() and not list((Path(pkg) / "base/tests").rglob("test_*.py")):
        reasons.append("REQUIRED_MISSING base/tests/test_*.py")
    if (Path(pkg) / "base/tests/test_hidden.py").exists():
        reasons.append("HIDDEN_TEST_DEST_PRESENT_AT_BASE")
    for name in ("statement.md", "hidden/test_hidden.py", "reference.patch"):
        path = Path(pkg) / name
        if path.is_file() and path.stat().st_size == 0:
            reasons.append(f"EMPTY_FILE {name}")

    status = "PASS" if not reasons else "FAIL"
    return _result(1, status, reasons, {"files": files, "manifest": manifest if status == "PASS" else None})


def _check_base(base, manifest, env):
    reasons, data = [], {}
    completed = _run(_python_argv(manifest["test_command"]), base, env)
    if completed is None:
        reasons.append("VISIBLE_TESTS_NOT_RUNNABLE")
    else:
        counts = _unittest_counts(completed.stdout)
        data["visible"] = counts
        if completed.returncode != 0 or counts["failures"] or counts["errors"] or counts["ran"] < 1:
            reasons.append(
                "VISIBLE_TESTS_FAIL rc={} failures={} errors={} ran={}".format(
                    completed.returncode, counts["failures"], counts["errors"], counts["ran"]))
    ruff = _run([sys.executable, "-m", "ruff", "check", "--no-cache", "."], base, env)
    if ruff is None:
        reasons.append("RUFF_NOT_RUNNABLE")
    else:
        data["ruff_base"] = ruff.returncode
        if ruff.returncode != 0:
            reasons.append(f"RUFF_DIRTY_AT_BASE rc={ruff.returncode}")
    return _result(2, "PASS" if not reasons else "FAIL", reasons, data)


def _check_hidden_at_base(base_with_hidden, dest, env):
    reasons, data = [], {}
    completed = _run([sys.executable, "-m", "unittest", "-v", dest], base_with_hidden, env)
    if completed is None:
        return _result(3, "FAIL", ["HIDDEN_TEST_NOT_RUNNABLE"])
    output = completed.stdout
    counts = _unittest_counts(output)
    data["hidden_at_base"] = counts
    data["returncode"] = completed.returncode
    if IMPORT_HEADER_RE.search(output):
        reasons.append("HIDDEN_TEST_IMPORT_ERROR")
    if counts["ran"] < 1:
        reasons.append("HIDDEN_TEST_COLLECTED_NO_TESTS")
    if counts["errors"]:
        reasons.append(f"HIDDEN_TEST_ERRORS_AT_BASE errors={counts['errors']}")
    if counts["skipped"]:
        reasons.append(f"HIDDEN_TEST_SKIPPED_AT_BASE skipped={counts['skipped']}")
    if counts["errors"] == 0 and (completed.returncode == 0 or counts["failures"] < 1):
        reasons.append("HIDDEN_TEST_ALREADY_PASSES_AT_BASE")
    return _result(3, "PASS" if not reasons else "FAIL", reasons, data)


def _check_reference(green, green_visible, patch, manifest, env):
    reasons, data = [], {}
    applied = []
    for tree in (green, green_visible):
        check = _run(["git", "apply", "--check", str(patch)], tree, env)
        if check is None:
            reasons.append("PATCH_TOOL_UNAVAILABLE")
            break
        if check.returncode != 0:
            reasons.append(f"PATCH_DOES_NOT_APPLY rc={check.returncode} {check.stdout.strip()[:200]}")
            break
        apply = _run(["git", "apply", str(patch)], tree, env)
        if apply is None or apply.returncode != 0:
            reasons.append("PATCH_APPLY_FAILED")
            break
        applied.append(tree)
    if len(applied) == 2:
        hidden = _run([sys.executable, "-m", "unittest", "-v", manifest["hidden_test_dest"]], green, env)
        if hidden is None:
            reasons.append("HIDDEN_TEST_NOT_RUNNABLE_AFTER_PATCH")
        else:
            counts = _unittest_counts(hidden.stdout)
            data["hidden_after_patch"] = counts
            if (hidden.returncode != 0 or counts["failures"] or counts["errors"]
                    or counts["skipped"] or counts["ran"] < 1):
                reasons.append(
                    "HIDDEN_TEST_FAILS_AFTER_PATCH rc={} failures={} errors={} skipped={} ran={}".format(
                        hidden.returncode, counts["failures"], counts["errors"],
                        counts["skipped"], counts["ran"]))
        visible = _run(_python_argv(manifest["test_command"]), green_visible, env)
        if visible is None:
            reasons.append("VISIBLE_TESTS_NOT_RUNNABLE_AFTER_PATCH")
        else:
            counts = _unittest_counts(visible.stdout)
            data["visible_after_patch"] = counts
            if visible.returncode != 0 or counts["failures"] or counts["errors"] or counts["ran"] < 1:
                reasons.append(
                    "VISIBLE_TESTS_BROKEN_BY_PATCH rc={} failures={} errors={} ran={}".format(
                        visible.returncode, counts["failures"], counts["errors"], counts["ran"]))
        ruff = _run([sys.executable, "-m", "ruff", "check", "--no-cache", "."], green_visible, env)
        if ruff is None:
            reasons.append("RUFF_NOT_RUNNABLE_AFTER_PATCH")
        else:
            data["ruff_after_patch"] = ruff.returncode
            if ruff.returncode != 0:
                reasons.append(f"RUFF_DIRTY_AFTER_PATCH rc={ruff.returncode}")
    return _result(4, "PASS" if not reasons else "FAIL", reasons, data)


def _tokens(text):
    return TOKEN_RE.findall(text.lower())


def _ngrams(tokens, size):
    return {"\u0000".join(tokens[index:index + size]) for index in range(len(tokens) - size + 1)}


def _check_statement(statement_text, hidden_text):
    reasons, data = [], {}
    hidden = _ngrams(_tokens(hidden_text), LEAK_NGRAM)
    statement = _ngrams(_tokens(statement_text), LEAK_NGRAM)
    shared = hidden & statement
    data["shared_ngrams"] = len(shared)
    if shared:
        sample = sorted(shared)[0].replace("\u0000", " ")[:160]
        reasons.append(f"STATEMENT_LEAKS_HIDDEN_TEST {sample}")
    for pattern, label in STATEMENT_BANNED:
        match = pattern.search(statement_text)
        if match:
            reasons.append(f"STATEMENT_MENTIONS_{label} {match.group(0)!r}")
    return _result(5, "PASS" if not reasons else "FAIL", reasons, data)


def _patch_stats(text):
    files, added, removed = set(), 0, 0
    for line in text.splitlines():
        if line.startswith("--- ") or line.startswith("+++ "):
            target = line[4:].split("\t")[0].strip()
            if target and target != "/dev/null":
                for prefix in ("a/", "b/"):
                    if target.startswith(prefix):
                        target = target[len(prefix):]
                files.add(target)
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return sorted(files), added + removed


def _is_test_path(path):
    parts = PurePosixPath(path).parts
    name = parts[-1] if parts else path
    return "tests" in parts or "test" in parts or name.startswith("test_") or name.endswith("_test.py")


def _check_risk(patch_text, statement_text, title):
    reasons, data = [], {}
    files, changed = _patch_stats(patch_text)
    data["files"] = files
    data["changed_lines"] = changed
    if not files:
        reasons.append("PATCH_TOUCHES_NO_FILE")
    if any(name.startswith("base/") for name in files):
        reasons.append("PATCH_PATHS_NOT_RELATIVE_TO_BASE")
    if len(files) > MAX_PATCH_FILES:
        reasons.append(f"PATCH_TOUCHES_TOO_MANY_FILES {len(files)} > {MAX_PATCH_FILES}")
    touched_tests = [name for name in files if _is_test_path(name)]
    if touched_tests:
        reasons.append(f"PATCH_TOUCHES_TEST_FILES {touched_tests}")
    if changed > MAX_PATCH_CHANGED_LINES:
        reasons.append(f"PATCH_TOO_LARGE {changed} > {MAX_PATCH_CHANGED_LINES}")
    screened = "\n".join([title, statement_text, patch_text])
    hits = sorted({term for pattern, term in RISK_SCREEN if pattern.search(screened)})
    data["keyword_hits"] = hits
    if hits:
        reasons.append(f"RISK_KEYWORD_HITS {hits}")
    return _result(6, "PASS" if not reasons else "FAIL", reasons, data)


def _check_seal(pkg):
    seal_path = Path(pkg) / SEAL_NAME
    if not seal_path.is_file():
        return _result(7, "NOT_SEALED", ["SEAL_ABSENT"], {"state": "NOT_SEALED"})
    try:
        verify_seal(pkg)
    except SealError as error:
        return _result(7, "FAIL", [f"SEAL_BROKEN {error}"], {"state": "BROKEN"})
    return _result(7, "PASS", [], {"state": "SEALED"})


def _copy_tree(source, target):
    """Copy regular files only; the structure check already refused symlinks."""
    source, target = Path(source), Path(target)
    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
        current = Path(dirpath)
        destination = target / current.relative_to(source)
        destination.mkdir(parents=True, exist_ok=True)
        for name in sorted(dirnames):
            if (current / name).is_symlink():
                raise SealError(f"symlink in package: {_posix(source, current / name)}")
        for name in sorted(filenames):
            entry = current / name
            if entry.is_symlink():
                raise SealError(f"symlink in package: {_posix(source, entry)}")
            shutil.copyfile(entry, destination / name)


def verify_package(pkg_dir):
    """Verify one package; returns a per-check verdict and an overall verdict.

    Raises only for programmer error (a ``pkg_dir`` that is not path-like). A bad
    package -- missing, malformed, unsafe, failing, leaking, tampered -- is a FAIL
    verdict, never an exception.
    """
    pkg = Path(pkg_dir)
    checks = []
    result = {
        "package": str(pkg),
        "overall": "FAIL",
        "seal": "NOT_SEALED",
        "checks": checks,
        "reasons": [],
    }
    with tempfile.TemporaryDirectory(prefix="h4-taskpack-") as temporary:
        work = Path(temporary) / "work"
        work.mkdir()
        (work / "home" / "tmp").mkdir(parents=True)
        env = _environment(work / "home")

        structure = _safe(1, lambda: _check_structure(pkg))
        checks.append(structure)
        manifest = structure["data"].get("manifest")

        if manifest is None:
            for check_id in (2, 3, 4, 5, 6):
                checks.append(_result(check_id, "NOT_RUN", ["CHECK_1_DID_NOT_PASS"]))
        else:
            def staged():
                _copy_tree(pkg / "base", work / "base")
                _copy_tree(pkg / "hidden", work / "hidden")
                shutil.copyfile(pkg / "statement.md", work / "statement.md")
                shutil.copyfile(pkg / "reference.patch", work / "reference.patch")
                _copy_tree(work / "base", work / "base-hidden")
                shutil.copyfile(work / "hidden" / "test_hidden.py",
                                work / "base-hidden" / manifest["hidden_test_dest"])
                _copy_tree(work / "base", work / "green")
                shutil.copyfile(work / "hidden" / "test_hidden.py",
                                work / "green" / manifest["hidden_test_dest"])
                _copy_tree(work / "base", work / "green-visible")
                return {
                    "statement": (work / "statement.md").read_text(encoding="utf-8"),
                    "hidden": (work / "hidden" / "test_hidden.py").read_text(encoding="utf-8"),
                    "patch_text": (work / "reference.patch").read_text(encoding="utf-8"),
                }

            try:
                texts = staged()
            except (OSError, SealError) as error:
                for check_id in (2, 3, 4, 5, 6):
                    checks.append(_result(check_id, "NOT_RUN", [f"STAGING_FAILED {error}"]))
            else:
                checks.append(_safe(2, lambda: _check_base(work / "base", manifest, env)))
                checks.append(_safe(3, lambda: _check_hidden_at_base(
                    work / "base-hidden", manifest["hidden_test_dest"], env)))
                checks.append(_safe(4, lambda: _check_reference(
                    work / "green", work / "green-visible", work / "reference.patch", manifest, env)))
                checks.append(_safe(5, lambda: _check_statement(texts["statement"], texts["hidden"])))
                checks.append(_safe(6, lambda: _check_risk(
                    texts["patch_text"], texts["statement"], str(manifest.get("title", "")))))

        seal = _safe(7, lambda: _check_seal(pkg))
        checks.append(seal)

    checks.sort(key=lambda item: item["id"])
    result["seal"] = seal["data"].get("state", "NOT_SEALED")
    blocking = [item for item in checks if item["id"] < CHECK_COUNT and item["status"] != "PASS"]
    acceptable_seal = seal["status"] in ("PASS", "NOT_SEALED")
    result["overall"] = "PASS" if not blocking and acceptable_seal else "FAIL"
    for item in checks:
        for reason in item["reasons"]:
            result["reasons"].append(f"{item['id']} {item['name']}: {reason}")
    return result


def seal_package(pkg_dir):
    """Write SEAL.json, but only when the package verifies and is not already sealed.

    A package whose existing seal is broken is refused rather than silently re-sealed:
    re-sealing after a mutation would erase the evidence that it changed.
    """
    pkg = Path(pkg_dir)
    report = verify_package(pkg)
    if report["seal"] == "BROKEN":
        raise SealError("refusing to re-seal a package with a broken seal: "
                        + "; ".join(report["reasons"][:5]))
    if report["overall"] != "PASS":
        raise SealError("package verification failed: " + "; ".join(report["reasons"][:5]))
    files = {name: _sha256(pkg / name) for name in _sealed_files(pkg)}
    payload = {"version": SEAL_VERSION, "files": dict(sorted(files.items())), "verified": True}
    (pkg / SEAL_NAME).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def verify_seal(pkg_dir):
    """Raise SealError unless SEAL.json matches every file exactly, and nothing is extra."""
    pkg = Path(pkg_dir)
    seal_path = pkg / SEAL_NAME
    if not seal_path.is_file():
        raise SealError(f"missing {SEAL_NAME}")
    try:
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SealError(f"unreadable {SEAL_NAME}: {error}") from error
    if not isinstance(seal, dict) or seal.get("version") != SEAL_VERSION:
        raise SealError(f"{SEAL_NAME} version is not {SEAL_VERSION}")
    if seal.get("verified") is not True:
        raise SealError(f"{SEAL_NAME} is not marked verified")
    recorded = seal.get("files")
    if not isinstance(recorded, dict) or not recorded:
        raise SealError(f"{SEAL_NAME} carries no file hashes")
    for name in recorded:
        parts = PurePosixPath(str(name))
        if parts.is_absolute() or ".." in parts.parts:
            raise SealError(f"invalid path in {SEAL_NAME}: {name!r}")
    current = {name: _sha256(pkg / name) for name in _sealed_files(pkg)}
    missing = sorted(set(recorded) - set(current))
    extra = sorted(set(current) - set(recorded))
    changed = sorted(name for name in set(recorded) & set(current) if recorded[name] != current[name])
    problems = []
    if missing:
        problems.append(f"missing={missing}")
    if extra:
        problems.append(f"extra={extra}")
    if changed:
        problems.append(f"changed={changed}")
    if problems:
        raise SealError("seal mismatch: " + ", ".join(problems))


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="taskpack.py",
        description="Verify, or verify and seal, one H4 pilot task package.")
    sub = parser.add_subparsers(dest="command", required=True)
    verify = sub.add_parser("verify", help="run the seven checks and print the verdict")
    verify.add_argument("package")
    seal = sub.add_parser("seal", help="verify, then write SEAL.json")
    seal.add_argument("package")
    args = parser.parse_args(argv)

    if args.command == "seal":
        try:
            seal_package(args.package)
        except SealError as error:
            print(json.dumps({"sealed": False, "error": str(error)}, indent=2, sort_keys=True))
            return 1
        print(json.dumps({"sealed": True, "package": str(Path(args.package))},
                         indent=2, sort_keys=True))
        return 0

    verdict = verify_package(args.package)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
