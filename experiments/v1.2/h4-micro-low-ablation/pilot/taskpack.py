#!/usr/bin/env python3
"""Model-free verifier, sealer and CLI for one H4 pilot task package.

A task package is the maker's only deliverable (see ``PILOT_SPEC.md``). This module
decides, without a model and without network, whether a package may be used at all.
Nothing here produces an experiment result; a PASS only means the package obeys the
package contract.

Seven checks, all of which must hold (``verify_package`` returns one verdict per
check, never an exception for a bad package):

1. ``structure`` -- required files present, no extra files, no symlinks, no ``.git``,
   ``__pycache__`` or ``*.pyc`` anywhere, every path inside the package;
   ``package.json`` carries the exact contract values, nothing else, and
   ``test_command`` is byte-for-byte the one canonical argv. A non-canonical command
   is refused before anything runs, so no ``-c`` payload can fake unittest output.
2. ``base`` -- the project's own test command passes at ``base/`` and ``ruff check``
   is clean there.
3. ``hidden_at_base`` -- the hidden test, copied to ``hidden_test_dest``, is a CLEAN
   unittest failure at base: ``failures>0``, ``errors=0``, ``skipped=0``, at least one
   test collected, no ``ImportError``/``ModuleNotFoundError``. It runs three times and
   all three verdicts must agree.
4. ``reference`` -- after ``reference.patch`` the hidden test passes three times in a
   row, the visible tests still pass, and ruff is still clean.
5. ``statement`` -- no >= 8-token run of the hidden test appears in ``statement.md``,
   case and punctuation included, no run of ``LEAK_CHAR_RUN`` identical alphanumeric
   characters is shared with it (one leaked ``assertEqual`` line is only seven words),
   and the statement names no experiment, governance or oracle vocabulary.
6. ``risk_low`` -- LOW by rule: the patch changes <= 60 lines in 1-2 non-test files,
   carries no mode change, rename or binary hunk, and a keyword screen finds no
   security, credential, concurrency, governance or network content. THE KEYWORD
   SCREEN IS A DOCUMENTED HEURISTIC, not a semantic judgement. Its term list is
   ``RISK_SCREEN_TERMS``; it cannot see meaning, so a task whose words look ordinary
   but whose behaviour is security- or concurrency-relevant still passes this screen
   and remains a human/experiment-level concern.
7. ``seal`` -- ``SEAL.json`` is present and matches every byte, or is absent, which the
   package-level verdict reports as ``NOT_SEALED`` (never silently folded into PASS).
   ``seal_package`` writes the seal only after checks 1-6 pass; ``verify_seal`` raises
   ``SealError`` on any missing, extra or changed file and is what later steps call.
   A package that already carries a ``SEAL.json`` is REFUSED by a plain
   ``verify_package`` (a maker can write, and can re-hash, its own seal, so a seal that
   was already there proves nothing); only ``seal_package`` and callers that say
   ``allow_reseal=True`` accept one, and even then a broken seal is refused.

Isolation rule: package code is never executed in place. ``verify_package`` stages the
base tree into a fresh temporary directory and runs every command there, with ``HOME``
and ``TMPDIR`` redirected into that directory, ``PYTHONPATH`` dropped, ``PYTHONHASHSEED``
pinned and bytecode writing off.

Both the base phase and the post-patch phase run in the SAME directory path: the phase
directory is deleted and recreated at the same location for every phase, so ``cwd``
cannot tell a hidden test which phase it is in. On macOS the commands additionally run
under ``sandbox-exec`` with a generated profile that denies the network, denies every
write outside the phase directory and denies reads of the real home directory and of
other users' files, so a marker file in ``/tmp`` or a ``pwd.getpwuid()`` lookup cannot
carry state from one phase into the next. When ``sandbox-exec`` is unavailable the
package is still verified, the result says ``isolation: NONE``, and the overall verdict
is ``UNSANDBOXED`` -- never ``PASS`` -- unless the caller passes
``allow_unsandboxed=True``. This is real confinement of an untrusted package, but it is
still not a security boundary against a hostile kernel-level attacker.

Every child process is capped at ``OUTPUT_CAP`` bytes of captured output and
``RUN_TIMEOUT`` seconds; exceeding either aborts the run at that point, and a timeout in
one phase is never paid again in the next.

CLI::

    python taskpack.py verify <pkg>    # exit 0 = PASS, non-zero = anything else
    python taskpack.py seal <pkg>      # prints the verdict, seals only on PASS
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path, PurePosixPath

try:  # POSIX only; the harness targets macOS
    import pwd
except ImportError:  # pragma: no cover - not reachable on the supported platform
    pwd = None

LABEL = "SYNTHETIC_EXPLORATORY"
RISK = "LOW"
LANGUAGE = "python"
SEAL_NAME = "SEAL.json"
SEAL_VERSION = 1
CHECK_COUNT = 7
MAX_PATCH_CHANGED_LINES = 60
MAX_PATCH_FILES = 2
LEAK_NGRAM = 8
# A token window cannot see a seven-word copy: one ``self.assertEqual(...)`` line is
# seven words however it is punctuated, and the acceptance corpus has exactly that case
# (E14). A run of this many identical alphanumeric characters, with every space and mark
# removed on both sides, is the fragment-level counterpart of the word window.
LEAK_CHAR_RUN = 24
RUN_TIMEOUT = 30
OUTPUT_CAP = 1 << 20
HIDDEN_REPEATS = 3
SANDBOX_PROBE_TIMEOUT = 15
PHASE_DIRNAME = "phase"

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
ALLOWED_MANIFEST_KEYS = {
    "task_id", "title", "label", "risk", "language", "statement", "hidden_test",
    "hidden_test_dest", "reference_patch", "test_command", "gate",
}
ALLOWED_GATE_KEYS = {"kind", "config"}
ALLOWED_TOP_LEVEL = {"package.json", "statement.md", "reference.patch", "base", "hidden", SEAL_NAME}

# The single command a package may name. Anything else -- a shell string, an absolute
# interpreter, an extra ``-c`` payload -- is refused before a process is started.
CANONICAL_TEST_COMMAND = ["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]

# Nested repositories are the classic way to send a patch outside the temp copy, and a
# cached bytecode tree is not something a maker is allowed to ship at all.
FORBIDDEN_DIR_NAMES = {".git", "__pycache__"}
FORBIDDEN_FILE_SUFFIXES = (".pyc", ".pyo")

# Check 5: the statement is what the worker reads, so it must not name experiment
# structure, governance vocabulary or the oracle itself.
STATEMENT_BANNED = (
    (re.compile(r"\barms?\b", re.IGNORECASE), "ARM_MENTION"),
    (re.compile(r"\bgovernance\b", re.IGNORECASE), "GOVERNANCE_MENTION"),
    (re.compile(r"\binject(?:ion|ed|ing|s)?\b", re.IGNORECASE), "INJECT_MENTION"),
    (re.compile(r"\bFULL\b"), "FULL_MENTION"),
    (re.compile(r"\bMIN\b"), "MIN_MENTION"),
    (re.compile(r"\bINJECT\b"), "INJECT_MENTION"),
    (re.compile(r"\boracle\w*", re.IGNORECASE), "ORACLE_MENTION"),
    (re.compile(r"\bgrader\w*|\bgrading\b", re.IGNORECASE), "GRADER_MENTION"),
    (re.compile(r"\bevaluat\w*", re.IGNORECASE), "EVALUATION_MENTION"),
    (re.compile(r"\bexperiment\w*", re.IGNORECASE), "EXPERIMENT_MENTION"),
    (re.compile(r"\btreatment\w*", re.IGNORECASE), "TREATMENT_MENTION"),
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
WORD_RE = re.compile(r"[a-z0-9]+")

# reference.patch shapes a LOW package must never carry.
PATCH_RENAME_RE = re.compile(
    r"^(?:rename from|rename to|copy from|copy to|similarity index|dissimilarity index)\b",
    re.MULTILINE)
PATCH_MODE_RE = re.compile(r"^(?:old mode|new mode|deleted file mode)\b", re.MULTILINE)
PATCH_BINARY_RE = re.compile(
    r"^(?:GIT binary patch|Binary files .+ differ|literal \d+|delta \d+)$", re.MULTILINE)


class SealError(Exception):
    """The package seal is missing, unreadable, or does not match the files on disk."""


class _Stop(Exception):
    """Abort the remaining dynamic phases; the check named here fails."""

    def __init__(self, check_id, reasons, data=None):
        super().__init__("; ".join(reasons))
        self.check_id = check_id
        self.reasons = list(reasons)
        self.data = dict(data or {})


class RunResult:
    """One child process: exit status, captured output, and whether it was cut short."""

    __slots__ = ("args", "returncode", "output", "timed_out", "overflow")

    def __init__(self, args, returncode, output, timed_out=False, overflow=False):
        self.args = list(args)
        self.returncode = returncode
        self.output = output
        self.timed_out = timed_out
        self.overflow = overflow


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


def _forbidden_paths(root, files):
    """``.git``, ``__pycache__`` and bytecode files anywhere in the package are refused."""
    reasons = []
    seen = set(files)
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        for name in sorted(dirnames):
            if name in FORBIDDEN_DIR_NAMES:
                reasons.append(f"FORBIDDEN_PATH {_posix(root, current / name)}")
        for name in sorted(filenames):
            if name in FORBIDDEN_DIR_NAMES:
                reasons.append(f"FORBIDDEN_PATH {_posix(root, current / name)}")
    for name in sorted(seen):
        if name.lower().endswith(FORBIDDEN_FILE_SUFFIXES):
            reasons.append(f"FORBIDDEN_PATH {name}")
    return reasons


def _sealed_files(root):
    """Every regular file under root, minus the seal itself."""
    files, reasons = _scan(root)
    if reasons:
        raise SealError("; ".join(reasons))
    return [name for name in files if name != SEAL_NAME]


def _real_home():
    """The account's real home, not ``$HOME`` and not ``~`` after redirection."""
    if pwd is not None:
        try:
            return pwd.getpwuid(os.getuid()).pw_dir
        except (KeyError, OSError):  # pragma: no cover - defensive
            pass
    return os.path.expanduser("~")


def _python_read_paths():
    """Interpreter paths the confined child still has to read."""
    paths = set()
    for name in ("prefix", "base_prefix", "exec_prefix", "base_exec_prefix"):
        value = getattr(sys, name, "")
        if value:
            paths.add(os.path.realpath(value))
    paths.add(os.path.dirname(os.path.realpath(sys.executable)))
    return sorted(paths)


def _profile_path(path):
    return '"' + str(path).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _sandbox_profile(phase_root, work_root):
    """Profile for package code: no network, no writes outside the phase, no home reads.

    Rules are evaluated last-match-wins, so the deny of the real home and of ``/Users``
    comes first and the allow of the phase directory and of the interpreter second.
    """
    read_allow = [str(phase_root)] + _python_read_paths()
    # The real home and every other account's home are unreadable to package code. The
    # work directory itself is not denied: git stats the parent chain to locate the repo.
    read_deny = [str(_real_home()), "/Users"]
    write_dirs = [str(phase_root)]
    write_devices = ["/dev/null", "/dev/zero", "/dev/random", "/dev/urandom", "/dev/tty"]
    lines = [
        "(version 1)",
        "(allow default)",
        "(deny network*)",
        "(deny file-write*)",
        "(allow file-write* "
        + " ".join(f"(subpath {_profile_path(path)})" for path in write_dirs)
        + " " + " ".join(f"(literal {_profile_path(path)})" for path in write_devices) + ")",
        "(deny file-read* " + " ".join(f"(subpath {_profile_path(path)})"
                                      for path in read_deny) + ")",
        "(allow file-read* " + " ".join(f"(subpath {_profile_path(path)})"
                                       for path in read_allow) + ")",
    ]
    return "\n".join(lines) + "\n"


def _sandbox_binary():
    found = shutil.which("sandbox-exec")
    if found:
        return found
    for candidate in ("/usr/bin/sandbox-exec", "/bin/sandbox-exec"):
        if os.access(candidate, os.X_OK):
            return candidate
    return None


def _probe_sandbox():
    """True only if sandbox-exec really confines a Python child on this machine."""
    if sys.platform != "darwin":
        return False
    binary = _sandbox_binary()
    if binary is None:
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="h4-sandbox-probe-") as temporary:
            root = Path(temporary)
            phase = root / PHASE_DIRNAME
            (phase / "home" / "tmp").mkdir(parents=True)
            profile = root / "probe.sb"
            profile.write_text(_sandbox_profile(phase, root), encoding="utf-8")
            env = _environment(phase / "home")
            result = _run([binary, "-f", str(profile), sys.executable, "-c",
                           "print('sandbox-ok')"], phase, env, timeout=SANDBOX_PROBE_TIMEOUT)
            return (result is not None and result.returncode == 0
                    and "sandbox-ok" in result.output)
    except OSError:  # pragma: no cover - temp dir or profile could not be written
        return False


_SANDBOX_CACHE = {}


def sandbox_available():
    """Is ``sandbox-exec`` usable here? Probed once per process; can be monkeypatched."""
    if "value" not in _SANDBOX_CACHE:
        _SANDBOX_CACHE["value"] = _probe_sandbox()
    return _SANDBOX_CACHE["value"]


def _environment(home):
    env = {key: value for key, value in os.environ.items() if key in ("PATH", "LANG", "LC_ALL")}
    env.update({
        "HOME": str(home),
        "TMPDIR": str(Path(home) / "tmp"),
        "LC_ALL": "C",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "NO_COLOR": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_TERMINAL_PROMPT": "0",
    })
    return env


def _kill(process):
    for attempt in (lambda: os.killpg(os.getpgid(process.pid), signal.SIGKILL), process.kill):
        try:
            attempt()
            return
        except OSError:
            continue


def _run(args, cwd, env, timeout=None, stdin_data=None):
    """Run one command; None means it could not be run at all.

    Output is drained through a pipe and capped at ``OUTPUT_CAP`` bytes; a command that
    outlives ``timeout`` (``RUN_TIMEOUT`` by default) or overflows the cap is killed
    together with its process group and reported as such.
    """
    limit = RUN_TIMEOUT if timeout is None else timeout
    command = [str(item) for item in args]
    try:
        process = subprocess.Popen(
            command, cwd=str(cwd), env=env,
            stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=0, start_new_session=True, close_fds=True)
    except OSError:
        return None
    if stdin_data is not None:
        payload = stdin_data if isinstance(stdin_data, bytes) else stdin_data.encode()

        def feed():
            try:
                process.stdin.write(payload)
                process.stdin.close()
            except (OSError, ValueError):  # pragma: no cover - child died early
                pass

        threading.Thread(target=feed, daemon=True).start()

    deadline = time.monotonic() + limit
    chunks, size, overflow, timed_out = [], 0, False, False
    try:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                ready = select.select([process.stdout], [], [], remaining)[0]
            except (OSError, ValueError):  # pragma: no cover - pipe closed under us
                break
            if not ready:
                timed_out = True
                break
            chunk = os.read(process.stdout.fileno(), 65536)
            if not chunk:
                break
            size += len(chunk)
            if size > OUTPUT_CAP:
                overflow = True
                keep = OUTPUT_CAP - (size - len(chunk))
                if keep > 0:
                    chunks.append(chunk[:keep])
                break
            chunks.append(chunk)
    finally:
        if timed_out or overflow:
            _kill(process)
    try:
        returncode = process.wait(timeout=10)
    except subprocess.TimeoutExpired:  # pragma: no cover - kill should have landed
        _kill(process)
        returncode = -1
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            pass
    try:
        process.stdout.close()
    except OSError:  # pragma: no cover
        pass
    output = b"".join(chunks).decode("utf-8", "replace")
    return RunResult(command, returncode, output, timed_out, overflow)


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


def _hidden_outcome(run):
    """One word for what a single hidden-test run did."""
    counts = _unittest_counts(run.output)
    if IMPORT_HEADER_RE.search(run.output):
        return "IMPORT_ERROR"
    if counts["ran"] < 1:
        return "NO_TESTS"
    if counts["errors"]:
        return "ERRORS"
    if counts["skipped"]:
        return "SKIPPED"
    if counts["failures"]:
        return "CLEAN_FAILURE" if run.returncode != 0 else "FAILURES_WITH_RC0"
    return "PASS" if run.returncode == 0 else "RC_NONZERO"


def _base_hidden_reasons(outcome, counts):
    if outcome == "IMPORT_ERROR":
        return ["HIDDEN_TEST_IMPORT_ERROR"]
    if outcome == "NO_TESTS":
        return ["HIDDEN_TEST_COLLECTED_NO_TESTS"]
    if outcome == "ERRORS":
        return [f"HIDDEN_TEST_ERRORS_AT_BASE errors={counts['errors']}"]
    if outcome == "SKIPPED":
        return [f"HIDDEN_TEST_SKIPPED_AT_BASE skipped={counts['skipped']}"]
    if outcome == "CLEAN_FAILURE":
        return []
    if outcome == "PASS":
        return ["HIDDEN_TEST_ALREADY_PASSES_AT_BASE"]
    return [f"HIDDEN_TEST_NOT_A_CLEAN_FAILURE {outcome}"]


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
    reasons.extend(_forbidden_paths(pkg, files))
    manifest_path = Path(pkg) / "package.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except OSError:
        return _result(1, "FAIL", reasons + ["PACKAGE_JSON_MISSING"])
    except ValueError:
        return _result(1, "FAIL", reasons + ["PACKAGE_JSON_INVALID"])
    if not isinstance(manifest, dict):
        return _result(1, "FAIL", reasons + ["PACKAGE_JSON_NOT_AN_OBJECT"])

    for field in sorted(set(manifest) - ALLOWED_MANIFEST_KEYS):
        reasons.append(f"PACKAGE_JSON_UNKNOWN_KEY {field}")
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
    elif set(gate) - ALLOWED_GATE_KEYS:
        reasons.append("PACKAGE_JSON_UNKNOWN_KEY gate."
                       + ",".join(sorted(set(gate) - ALLOWED_GATE_KEYS)))
    command = manifest.get("test_command")
    if not isinstance(command, list) or not command or not all(
            isinstance(item, str) for item in command):
        reasons.append("PACKAGE_JSON_FIELD test_command must be a non-empty argv list")
    if command != CANONICAL_TEST_COMMAND:
        reasons.append(f"TEST_COMMAND_NOT_CANONICAL {command!r}")

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


# --- phase staging ---------------------------------------------------------------
# Every phase runs at the same path: <work>/phase/repo. The directory is deleted and
# recreated for each phase, so a hidden test sees an identical cwd in both phases and
# can neither detect the phase nor keep a file for the next one.

def _phase_root(work):
    return Path(work) / PHASE_DIRNAME


def _reset_phase(work):
    root = _phase_root(work)
    if Path(root).exists() or Path(root).is_symlink():
        shutil.rmtree(root)
    (root / "repo").mkdir(parents=True)
    (root / "home" / "tmp").mkdir(parents=True, exist_ok=True)
    (root / "tmp").mkdir(parents=True, exist_ok=True)
    return root


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


def _phase_run(work, sandbox, profile, args, stdin_data=None):
    root = _phase_root(work)
    env = _environment(root / "home")
    command = list(args)
    if sandbox:
        command = [str(sandbox), "-f", str(profile)] + command
    return _run(command, root / "repo", env, stdin_data=stdin_data)


def _guard(check_id, run, label):
    if run is None:
        raise _Stop(check_id, [f"{label}_NOT_RUNNABLE"])
    if run.timed_out:
        raise _Stop(check_id, [f"{label}_TIMEOUT exceeded {RUN_TIMEOUT}s"])
    if run.overflow:
        raise _Stop(check_id, [f"{label}_OUTPUT_OVERFLOW exceeded {OUTPUT_CAP} bytes"])
    return run


def _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile, with_hidden, patch):
    root = _reset_phase(work)
    repo = root / "repo"
    _copy_tree(Path(pkg) / "base", repo)
    if patch:
        for args, failure in ((["git", "apply", "--check", "-"], "PATCH_DOES_NOT_APPLY"),
                              (["git", "apply", "-"], "PATCH_APPLY_FAILED")):
            run = _guard(4, _phase_run(work, sandbox, profile, args, stdin_data=patch_text),
                         "PATCH_TOOL")
            if run.returncode != 0:
                raise _Stop(4, [f"{failure} rc={run.returncode} {run.output.strip()[:200]}"])
    if with_hidden:
        shutil.copyfile(Path(pkg) / "hidden" / "test_hidden.py",
                        repo / manifest["hidden_test_dest"])
    return repo


def _visible_argv():
    return [sys.executable] + CANONICAL_TEST_COMMAND[1:]


def _phase_base(work, pkg, manifest, patch_text, sandbox, profile):
    """Check 2: the project is green on its own before anything is added."""
    reasons, data = [], {}
    _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile,
                   with_hidden=False, patch=False)
    visible = _guard(2, _phase_run(work, sandbox, profile, _visible_argv()), "VISIBLE_TESTS")
    counts = _unittest_counts(visible.output)
    data["visible"] = counts
    if visible.returncode != 0 or counts["failures"] or counts["errors"] or counts["ran"] < 1:
        reasons.append(
            "VISIBLE_TESTS_FAIL rc={} failures={} errors={} ran={}".format(
                visible.returncode, counts["failures"], counts["errors"], counts["ran"]))
    data["phase"] = str(_phase_root(work) / "repo")
    ruff = _guard(2, _phase_run(work, sandbox, profile,
                                [sys.executable, "-m", "ruff", "check", "--no-cache", "."]),
                  "RUFF")
    data["ruff_base"] = ruff.returncode
    if ruff.returncode != 0:
        reasons.append(f"RUFF_DIRTY_AT_BASE rc={ruff.returncode} {ruff.output.strip()[:200]}")
    return _result(2, "PASS" if not reasons else "FAIL", reasons, data)


def _hidden_runs(work, manifest, sandbox, profile, check_id, label):
    runs = []
    for _attempt in range(HIDDEN_REPEATS):
        run = _guard(check_id, _phase_run(
            work, sandbox, profile,
            [sys.executable, "-m", "unittest", "-v", manifest["hidden_test_dest"]]), label)
        runs.append(run)
    return runs


def _phase_hidden_at_base(work, pkg, manifest, patch_text, sandbox, profile):
    """Check 3: a clean, deterministic failure at base."""
    repo = _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile,
                          with_hidden=True, patch=False)
    runs = _hidden_runs(work, manifest, sandbox, profile, 3, "HIDDEN_TEST")
    outcomes = [_hidden_outcome(run) for run in runs]
    counts = _unittest_counts(runs[0].output)
    data = {"phase": str(repo), "runs": outcomes, "hidden_at_base": counts,
            "returncode": runs[0].returncode}
    reasons = []
    if len(set(outcomes)) > 1:
        reasons.append(f"NONDETERMINISTIC base outcomes={outcomes}")
    else:
        reasons.extend(_base_hidden_reasons(outcomes[0], counts))
    return _result(3, "PASS" if not reasons else "FAIL", reasons, data)


def _phase_after_patch(work, pkg, manifest, patch_text, sandbox, profile):
    """Check 4: the reference makes the hidden test pass and keeps everything else green."""
    reasons, data = [], {}
    repo = _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile,
                          with_hidden=True, patch=True)
    runs = _hidden_runs(work, manifest, sandbox, profile, 4, "HIDDEN_TEST_AFTER_PATCH")
    outcomes = [_hidden_outcome(run) for run in runs]
    counts = _unittest_counts(runs[0].output)
    data.update({"phase": str(repo), "runs": outcomes, "hidden_after_patch": counts,
                 "returncode": runs[0].returncode})
    if len(set(outcomes)) > 1:
        reasons.append(f"NONDETERMINISTIC after_patch outcomes={outcomes}")
    elif outcomes[0] != "PASS":
        reasons.append(
            "HIDDEN_TEST_FAILS_AFTER_PATCH rc={} failures={} errors={} skipped={} ran={}".format(
                runs[0].returncode, counts["failures"], counts["errors"],
                counts["skipped"], counts["ran"]))

    # Same path, fresh tree, no hidden test: the visible suite the worker must not break.
    _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile,
                   with_hidden=False, patch=True)
    visible = _guard(4, _phase_run(work, sandbox, profile, _visible_argv()),
                     "VISIBLE_TESTS_AFTER_PATCH")
    visible_counts = _unittest_counts(visible.output)
    data["visible_after_patch"] = visible_counts
    if (visible.returncode != 0 or visible_counts["failures"] or visible_counts["errors"]
            or visible_counts["ran"] < 1):
        reasons.append(
            "VISIBLE_TESTS_BROKEN_BY_PATCH rc={} failures={} errors={} ran={}".format(
                visible.returncode, visible_counts["failures"], visible_counts["errors"],
                visible_counts["ran"]))
    ruff = _guard(4, _phase_run(work, sandbox, profile,
                                [sys.executable, "-m", "ruff", "check", "--no-cache", "."]),
                  "RUFF_AFTER_PATCH")
    data["ruff_after_patch"] = ruff.returncode
    if ruff.returncode != 0:
        reasons.append(f"RUFF_DIRTY_AFTER_PATCH rc={ruff.returncode} {ruff.output.strip()[:200]}")
    return _result(4, "PASS" if not reasons else "FAIL", reasons, data)


def _dynamic_checks(work, pkg, manifest, patch_text, sandbox, profile):
    """Run checks 2-4 in order; a timeout or overflow stops everything that follows."""
    results = {}
    try:
        results[2] = _phase_base(work, pkg, manifest, patch_text, sandbox, profile)
        results[3] = _phase_hidden_at_base(work, pkg, manifest, patch_text, sandbox, profile)
        results[4] = _phase_after_patch(work, pkg, manifest, patch_text, sandbox, profile)
    except _Stop as stop:
        results[stop.check_id] = _result(stop.check_id, "FAIL", stop.reasons, stop.data)
    except (OSError, SealError) as error:
        for check_id in (2, 3, 4):
            results.setdefault(check_id, _result(check_id, "NOT_RUN", [f"STAGING_FAILED {error}"]))
    first_reason = None
    for check_id in (2, 3, 4):
        if check_id in results and results[check_id]["reasons"] and first_reason is None:
            first_reason = results[check_id]["reasons"][0]
    for check_id in (2, 3, 4):
        if check_id not in results:
            results[check_id] = _result(
                check_id, "NOT_RUN", [f"STOPPED_BEFORE {first_reason or 'EARLIER_FAILURE'}"])
    return [results[2], results[3], results[4]]


def _tokens(text):
    """Case-folded tokens; punctuation is a token of its own."""
    return TOKEN_RE.findall(text.lower())


def _words(text):
    """Case-folded word tokens only; ``a, b`` and ``a b`` normalise to the same run."""
    return WORD_RE.findall(text.lower())


def _ngrams(tokens, size):
    return {"\u0000".join(tokens[index:index + size]) for index in range(len(tokens) - size + 1)}


def _shared_ngram(hidden_text, statement_text, tokenizer, size):
    hidden = _ngrams(tokenizer(hidden_text), size)
    statement = _ngrams(tokenizer(statement_text), size)
    return hidden & statement


def _squeezed(text):
    """Letters and digits only: spacing, case and punctuation all disappear."""
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _shared_char_run(hidden_text, statement_text, size=LEAK_CHAR_RUN):
    """One identical run of ``size`` alphanumeric characters, or None."""
    hidden, statement = _squeezed(hidden_text), _squeezed(statement_text)
    if len(hidden) < size or len(statement) < size:
        return None
    windows = {hidden[index:index + size] for index in range(len(hidden) - size + 1)}
    for index in range(len(statement) - size + 1):
        window = statement[index:index + size]
        if window in windows:
            return window
    return None


def _check_statement(statement_text, hidden_text):
    reasons, data = [], {}
    shared = _shared_ngram(hidden_text, statement_text, _tokens, LEAK_NGRAM)
    data["shared_ngrams"] = len(shared)
    if shared:
        sample = sorted(shared)[0].replace("\u0000", " ")[:160]
        reasons.append(f"STATEMENT_LEAKS_HIDDEN_TEST {sample}")
    # Same window over words only, so changing case or punctuation cannot hide a copy.
    word_shared = _shared_ngram(hidden_text, statement_text, _words, LEAK_NGRAM)
    data["shared_word_ngrams"] = len(word_shared)
    if word_shared:
        sample = sorted(word_shared)[0].replace("\u0000", " ")[:160]
        reasons.append(f"STATEMENT_LEAKS_HIDDEN_TEST_WORDS {sample}")
    # And a fragment-level window for copies too short to fill eight words.
    fragment = _shared_char_run(hidden_text, statement_text)
    data["shared_char_run"] = len(fragment or "")
    if fragment:
        reasons.append(f"STATEMENT_LEAKS_HIDDEN_FRAGMENT {fragment}")
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


def _patch_shape_reasons(patch_text):
    reasons = []
    if PATCH_MODE_RE.search(patch_text):
        reasons.append(f"PATCH_HAS_MODE_CHANGE {PATCH_MODE_RE.search(patch_text).group(0)!r}")
    if PATCH_BINARY_RE.search(patch_text):
        reasons.append(f"PATCH_HAS_BINARY_HUNK {PATCH_BINARY_RE.search(patch_text).group(0)!r}")
    renamed = PATCH_RENAME_RE.search(patch_text)
    if renamed:
        reasons.append(f"PATCH_HAS_RENAME {renamed.group(0)!r}")
    return reasons


def _check_risk(patch_text, statement_text, title):
    reasons, data = [], {}
    files, changed = _patch_stats(patch_text)
    data["files"] = files
    data["changed_lines"] = changed
    if not files:
        reasons.append("PATCH_TOUCHES_NO_FILE")
    if any(name.startswith("base/") for name in files):
        reasons.append("PATCH_PATHS_NOT_RELATIVE_TO_BASE")
    if any(PurePosixPath(name).is_absolute() or ".." in PurePosixPath(name).parts
           for name in files):
        reasons.append("PATCH_PATHS_ESCAPE_BASE")
    if len(files) > MAX_PATCH_FILES:
        reasons.append(f"PATCH_TOUCHES_TOO_MANY_FILES {len(files)} > {MAX_PATCH_FILES}")
    touched_tests = [name for name in files if _is_test_path(name)]
    if touched_tests:
        reasons.append(f"PATCH_TOUCHES_TEST_FILES {touched_tests}")
    if changed > MAX_PATCH_CHANGED_LINES:
        reasons.append(f"PATCH_TOO_LARGE {changed} > {MAX_PATCH_CHANGED_LINES}")
    reasons.extend(_patch_shape_reasons(patch_text))
    screened = "\n".join([title, statement_text, patch_text])
    hits = sorted({term for pattern, term in RISK_SCREEN if pattern.search(screened)})
    data["keyword_hits"] = hits
    if hits:
        reasons.append(f"RISK_KEYWORD_HITS {hits}")
    return _result(6, "PASS" if not reasons else "FAIL", reasons, data)


def _check_seal(pkg, allow_reseal):
    seal_path = Path(pkg) / SEAL_NAME
    if not seal_path.is_file():
        return _result(7, "NOT_SEALED", ["SEAL_ABSENT"], {"state": "NOT_SEALED"})
    try:
        verify_seal(pkg)
    except SealError as error:
        return _result(7, "FAIL", [f"SEAL_BROKEN {error}"], {"state": "BROKEN"})
    if not allow_reseal:
        # A maker can write this file, and can recompute every hash in it, so a seal that
        # was already there when the verifier first saw the package proves nothing.
        return _result(7, "FAIL", ["SEAL_PRESENT_BEFORE_SEALING"], {"state": "SEAL_PRESENT"})
    return _result(7, "PASS", [], {"state": "SEALED"})


def verify_package(pkg_dir, allow_unsandboxed=False, allow_reseal=False):
    """Verify one package; returns a per-check verdict and an overall verdict.

    ``overall`` is ``PASS`` only when every check passed, the seal is absent or valid and
    the package code really ran confined; ``UNSANDBOXED`` means everything passed but
    ``sandbox-exec`` was unavailable and ``allow_unsandboxed`` was not given, so the
    verdict can never be mistaken for PASS.

    Raises only for programmer error (a ``pkg_dir`` that is not path-like). A bad
    package -- missing, malformed, unsafe, failing, leaking, tampered -- is a FAIL
    verdict, never an exception.
    """
    pkg = Path(pkg_dir)
    checks = []
    result = {
        "package": str(pkg),
        "overall": "FAIL",
        "isolation": "NONE",
        "seal": "NOT_SEALED",
        "sealed": False,
        "checks": checks,
        "reasons": [],
    }
    structure = _safe(1, lambda: _check_structure(pkg))
    checks.append(structure)
    manifest = structure["data"].get("manifest")

    sandbox = _sandbox_binary() if sandbox_available() else None
    result["isolation"] = "SANDBOX_EXEC" if sandbox else "NONE"

    if manifest is None:
        for check_id in (2, 3, 4, 5, 6):
            checks.append(_result(check_id, "NOT_RUN", ["CHECK_1_DID_NOT_PASS"]))
    else:
        with tempfile.TemporaryDirectory(prefix="h4-taskpack-") as temporary:
            work = Path(temporary) / "work"
            work.mkdir()
            profile = work / "sandbox.sb"
            try:
                statement = (pkg / "statement.md").read_text(encoding="utf-8")
                hidden = (pkg / "hidden" / "test_hidden.py").read_text(encoding="utf-8")
                patch_text = (pkg / "reference.patch").read_text(encoding="utf-8")
                profile.write_text(_sandbox_profile(_phase_root(work), work), encoding="utf-8")
            except (OSError, UnicodeDecodeError) as error:
                for check_id in (2, 3, 4, 5, 6):
                    checks.append(_result(check_id, "NOT_RUN", [f"STAGING_FAILED {error}"]))
            else:
                checks.extend(_dynamic_checks(
                    work, pkg, manifest, patch_text.encode("utf-8"), sandbox, profile))
                checks.append(_safe(5, lambda: _check_statement(statement, hidden)))
                checks.append(_safe(6, lambda: _check_risk(
                    patch_text, statement, str(manifest.get("title", "")))))

    seal = _safe(7, lambda: _check_seal(pkg, allow_reseal))
    checks.append(seal)

    checks.sort(key=lambda item: item["id"])
    result["seal"] = seal["data"].get("state", "NOT_SEALED")
    result["sealed"] = result["seal"] == "SEALED"
    blocking = [item for item in checks if item["id"] < CHECK_COUNT and item["status"] != "PASS"]
    acceptable_seal = seal["status"] in ("PASS", "NOT_SEALED")
    if blocking or not acceptable_seal:
        result["overall"] = "FAIL"
    elif result["isolation"] == "NONE" and not allow_unsandboxed:
        result["overall"] = "UNSANDBOXED"
    else:
        result["overall"] = "PASS"
    for item in checks:
        for reason in item["reasons"]:
            result["reasons"].append(f"{item['id']} {item['name']}: {reason}")
    return result


def seal_package(pkg_dir, allow_unsandboxed=False):
    """Write SEAL.json, but only when the package verifies and is not already broken.

    This is the one caller allowed to see an existing seal (``allow_reseal=True``): it
    re-verifies first and refuses to overwrite a broken one, because re-sealing after a
    mutation would erase the evidence that it changed.
    """
    pkg = Path(pkg_dir)
    report = verify_package(pkg, allow_unsandboxed=allow_unsandboxed, allow_reseal=True)
    if report["seal"] == "BROKEN":
        raise SealError("refusing to re-seal a package with a broken seal: "
                        + "; ".join(report["reasons"][:5]))
    if report["overall"] != "PASS":
        raise SealError("package verification failed: " + "; ".join(report["reasons"][:5]))
    files = {name: _sha256(pkg / name) for name in _sealed_files(pkg)}
    payload = {"version": SEAL_VERSION, "files": dict(sorted(files.items())), "verified": True}
    (pkg / SEAL_NAME).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                                 encoding="utf-8")


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
    verify.add_argument("--reseal", action="store_true",
                        help="accept a package that already carries a valid SEAL.json")
    verify.add_argument("--allow-unsandboxed", action="store_true",
                        help="report PASS even when sandbox-exec is unavailable (never a real seal)")
    seal = sub.add_parser("seal", help="verify, then write SEAL.json")
    seal.add_argument("package")
    seal.add_argument("--allow-unsandboxed", action="store_true",
                      help="seal even when sandbox-exec is unavailable")
    args = parser.parse_args(argv)

    if args.command == "seal":
        try:
            seal_package(args.package, allow_unsandboxed=args.allow_unsandboxed)
        except SealError as error:
            print(json.dumps({"sealed": False, "error": str(error)}, indent=2, sort_keys=True))
            return 1
        print(json.dumps({"sealed": True, "package": str(Path(args.package))},
                         indent=2, sort_keys=True))
        return 0

    verdict = verify_package(args.package, allow_unsandboxed=args.allow_unsandboxed,
                             allow_reseal=args.reseal)
    print(json.dumps(verdict, indent=2, sort_keys=True))
    return 0 if verdict["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
