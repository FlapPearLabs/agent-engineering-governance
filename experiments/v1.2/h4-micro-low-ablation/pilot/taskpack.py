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
   test collected, no import-level failure, and it imports a module from ``src/``. It
   runs ``HIDDEN_REPEATS`` times (seven) and every verdict must agree; the run stops at
   the first disagreement. A hidden test that reads a file under ``src/``, or a hidden or
   reference file, is ``SOURCE_READ_BY_TEST``.
4. ``reference`` -- after ``reference.patch`` the hidden test passes ``HIDDEN_REPEATS``
   times in a row, at least one added or changed line of the patch lies inside a function
   or method body, actually runs during that hidden test and is not a trivial statement
   (a bare constant, ``pass``, ``assert <constant>``, an unread constant assignment or
   dead code), the hidden test calls at least one function or method defined in the
   patched files (``HIDDEN_TEST_NEVER_CALLS_TARGET``), the visible tests still pass, and
   ruff is still clean. A docstring-only, comment-only or dead-code patch is
   ``PATCH_NOT_EXERCISED``.
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

Report rule (P1-1/P1-2 a): NO test verdict is ever read from text the package can print.
Every test execution -- visible tests at base, hidden test at base, visible and hidden
after the patch -- is run by ``pilot/test_runner.py`` instead of ``python -m unittest``.
The parent creates a one-time nonce, hands it to the runner through an inherited pipe
that the runner reads and closes before importing any package code, and accepts a result
only when (a) the runner's HMAC-SHA256 over its canonical JSON payload verifies, (b) the
runner's own exit status agrees with the counts, and (c) the set of test ids equals the
set found by ``ast`` parsing of the test file(s). A module that calls ``os._exit(0)`` or
prints ``Ran N tests OK`` therefore yields ``TEST_RESULT_UNAVAILABLE`` -- a FAIL.
``test_command`` stays the single canonical argv in the contract, but it is display-only:
the runner replaces its execution. The runner also records test-code reads of ``src/``
(``SOURCE_READ_BY_TEST``), records which function-body lines of the patched files ran
(``HIDDEN_TEST_NEVER_CALLS_TARGET``), and re-checks the identity of the functions its
verdict relies on before signing the report (``INTEGRITY_VIOLATION``).

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
import ast
import hashlib
import hmac
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
# P2-1: seven agreeing runs with an early abort on the first disagreement. This lowers
# the chance that an intermittently failing hidden test slips through; it does not make
# that chance zero (see BUILD_NOTES, which records the MEASURED N20 acceptance rate).
HIDDEN_REPEATS = 7
SANDBOX_PROBE_TIMEOUT = 15
PHASE_DIRNAME = "phase"
RUNNER_NAME = "test_runner.py"
RUNNER_VERSION = 1
NONCE_BYTES = 32
NONCE_MAC_LENGTH = 64

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

# No unittest output pattern lives here on purpose: see the report rule above. The only
# regexes left are about the package text, never about what a test process printed.
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

    P2-1: every path is resolved with ``os.path.realpath`` first. macOS ``TMPDIR`` is
    ``/var/folders/...``, a symlink to ``/private/var/folders/...``; the kernel matches
    the profile against the real path, so an unresolved phase path made the phase
    directory unwritable and every normal package failed under the default TMPDIR.
    """
    phase_root = Path(os.path.realpath(str(phase_root)))
    work_root = Path(os.path.realpath(str(work_root)))
    # The harness-owned runner lives outside the phase (package code cannot write it) and
    # has to be readable by the interpreter that executes it.
    read_allow = [str(phase_root), str(work_root / "runner")] + _python_read_paths()
    # The real home and every other account's home are unreadable to package code. The
    # work directory itself is not denied: git stats the parent chain to locate the repo.
    read_deny = [str(os.path.realpath(_real_home())), "/Users"]
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
    """``(usable, reason)`` for this machine; the reason quotes the probe's own output.

    A nested ``sandbox-exec`` (this test suite running inside an outer sandbox) fails
    here. Tests that need confinement skip with this reason instead of failing or, worse,
    passing without having proven anything.
    """
    if sys.platform != "darwin":
        return False, "not macOS (sys.platform=%s)" % sys.platform
    binary = _sandbox_binary()
    if binary is None:
        return False, "sandbox-exec is not installed"
    try:
        with tempfile.TemporaryDirectory(prefix="h4-sandbox-probe-") as temporary:
            root = Path(temporary)
            phase = root / PHASE_DIRNAME
            (phase / "home" / "tmp").mkdir(parents=True)
            profile = root / "probe.sb"
            profile.write_text(_sandbox_profile(phase, root), encoding="utf-8")
            env = _environment(phase / "home")
            result = _run([binary, "-f", str(profile), sys.executable, "-c",
                           "print('sandbox-ok')"], phase, env,
                          timeout=SANDBOX_PROBE_TIMEOUT)
    except OSError as error:  # pragma: no cover - temp dir or profile not writable
        return False, "probe could not run: %s" % error
    if result is None:
        return False, "probe could not start %s" % binary
    if result.timed_out:
        return False, "probe timed out after %ss" % SANDBOX_PROBE_TIMEOUT
    if result.returncode == 0 and "sandbox-ok" in result.output:
        return True, ""
    detail = result.output.strip().replace("\n", " ")[:400]
    return False, ("probe exit=%s output=%r (a nested sandbox-exec cannot apply a "
                   "second profile)" % (result.returncode, detail))


_SANDBOX_CACHE = {}


def sandbox_available():
    """Is ``sandbox-exec`` usable here? Probed once per process; can be monkeypatched."""
    if "value" not in _SANDBOX_CACHE:
        usable, reason = _probe_sandbox()
        _SANDBOX_CACHE["value"] = usable
        _SANDBOX_CACHE["reason"] = reason
    return _SANDBOX_CACHE["value"]


def sandbox_probe_reason():
    """The probe's own explanation when ``sandbox_available()`` is false."""
    sandbox_available()
    return _SANDBOX_CACHE.get("reason", "")


def _environment(home):
    """A closed environment for package code; every path is already resolved."""
    home = Path(os.path.realpath(str(home)))
    env = {key: value for key, value in os.environ.items() if key in ("PATH", "LANG", "LC_ALL")}
    env.update({
        "HOME": str(home),
        "TMPDIR": str(home / "tmp"),
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


def _capture(args, cwd, env, timeout=None, stdin_data=None, pass_fds=(), extra_fds=(),
             close_after_spawn=()):
    """Run one command; ``(None, {})`` means it could not be run at all.

    Output is drained through a pipe and capped at ``OUTPUT_CAP`` bytes; a command that
    outlives ``timeout`` (``RUN_TIMEOUT`` by default) or overflows the cap is killed
    together with its process group and reported as such. ``extra_fds`` are additional
    inherited read descriptors (the runner's signed result channel); they are drained in
    the same select loop and capped the same way. ``close_after_spawn`` holds descriptors
    the parent must drop right after the fork -- without that the read end of a result
    pipe never sees EOF and the drain waits until the timeout.
    """
    limit = RUN_TIMEOUT if timeout is None else timeout
    command = [str(item) for item in args]
    extra_fds = tuple(extra_fds)
    try:
        process = subprocess.Popen(
            command, cwd=str(cwd), env=env,
            stdin=subprocess.PIPE if stdin_data is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            bufsize=0, start_new_session=True, close_fds=True,
            pass_fds=tuple(pass_fds))
    except OSError:
        return None, {}
    for fd in close_after_spawn:
        try:
            os.close(fd)
        except OSError:  # pragma: no cover
            pass
    if stdin_data is not None:
        payload = stdin_data if isinstance(stdin_data, bytes) else stdin_data.encode()

        def feed():
            try:
                process.stdin.write(payload)
                process.stdin.close()
            except (OSError, ValueError):  # pragma: no cover - child died early
                pass

        threading.Thread(target=feed, daemon=True).start()

    for fd in extra_fds:
        os.set_blocking(fd, False)
    deadline = time.monotonic() + limit
    chunks, size, overflow, timed_out = [], 0, False, False
    extra = {fd: bytearray() for fd in extra_fds}
    read_fds = [process.stdout] + list(extra_fds)
    try:
        while read_fds:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            try:
                ready = select.select(read_fds, [], [], remaining)[0]
            except (OSError, ValueError):  # pragma: no cover - pipe closed under us
                break
            if not ready:
                timed_out = True
                break
            for stream in ready:
                stdout = stream is process.stdout
                try:
                    chunk = os.read(process.stdout.fileno() if stdout else stream, 65536)
                except BlockingIOError:  # pragma: no cover - select said readable
                    continue
                except OSError:  # pragma: no cover
                    chunk = b""
                if not chunk:
                    read_fds.remove(stream)
                    continue
                if stdout:
                    size += len(chunk)
                    if size > OUTPUT_CAP:
                        overflow = True
                        keep = OUTPUT_CAP - (size - len(chunk))
                        if keep > 0:
                            chunks.append(chunk[:keep])
                        read_fds = []
                        break
                    chunks.append(chunk)
                else:
                    buffer = extra[stream]
                    room = OUTPUT_CAP - len(buffer)
                    if len(chunk) > room:
                        overflow = True
                        buffer.extend(chunk[:max(room, 0)])
                        read_fds = []
                        break
                    buffer.extend(chunk)
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
    for fd in extra_fds:
        while True:
            try:
                chunk = os.read(fd, 65536)
            except (BlockingIOError, OSError):  # pragma: no cover
                break
            if not chunk:
                break
            room = OUTPUT_CAP - len(extra[fd])
            if room <= 0:
                break
            extra[fd].extend(chunk[:room])
    output = b"".join(chunks).decode("utf-8", "replace")
    return (RunResult(command, returncode, output, timed_out, overflow),
            {fd: bytes(value) for fd, value in extra.items()})


def _run(args, cwd, env, timeout=None, stdin_data=None):
    """Run one command; None means it could not be run at all."""
    run, _extra = _capture(args, cwd, env, timeout=timeout, stdin_data=stdin_data)
    return run


# --- the signed test-report channel (P1-1/P1-2 a) -------------------------------
# Nothing below parses unittest text. The runner signs its payload with a one-time nonce
# the package never sees, and the parent re-derives that MAC before believing a word.

def _canonical_json(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _nonce_bytes(nonce):
    """Accept the nonce as bytes or as hex text; a short nonce is a caller bug."""
    if isinstance(nonce, bytes):
        value = nonce
    elif isinstance(nonce, str):
        value = bytes.fromhex(nonce)
    else:
        raise TypeError("nonce must be bytes or hex text")
    if len(value) < 16:
        raise ValueError("nonce must be at least 16 bytes")
    return value


def _new_nonce():
    return os.urandom(NONCE_BYTES).hex()


REPORT_KEY_LABEL = b"h4-runner-report"


def _report_key(nonce):
    """The runner derives its MAC key from the nonce; the parent derives the same key."""
    return hmac.new(_nonce_bytes(nonce), REPORT_KEY_LABEL, hashlib.sha256).digest()


def _verify_report_mac(report, nonce):
    """True only for a report this runner signed with this run's nonce."""
    if not isinstance(report, dict):
        return False
    mac = report.get("nonce_mac")
    if not isinstance(mac, str) or len(mac) != NONCE_MAC_LENGTH:
        return False
    payload = {key: value for key, value in report.items() if key != "nonce_mac"}
    expected = hmac.new(_report_key(nonce), _canonical_json(payload).encode("utf-8"),
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, mac)


def _short_id(value):
    """``module.Class.method`` and ``Class.method`` compare as ``Class.method``."""
    parts = str(value).split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else str(value)


def _accept_report(report, nonce, expected_ids, exit_code=None):
    """``(ok, reason)`` for one signed report against the statically known test ids."""
    if not isinstance(report, dict) or report.get("version") != RUNNER_VERSION:
        return False, "TEST_RESULT_UNAVAILABLE"
    if not _verify_report_mac(report, nonce):
        return False, "TEST_RESULT_MAC_INVALID"
    violations = report.get("integrity_violation")
    if violations:
        return False, "INTEGRITY_VIOLATION " + ",".join(str(item) for item in violations[:8])
    # Round C1: the runner's parent also compares the observed ids with the static AST
    # set before signing. Reject its own report when that comparison failed, even though
    # the check below repeats it on this side.
    if report.get("id_set_mismatch"):
        return False, "TEST_ID_SET_MISMATCH " + str(report.get("id_set_detail", ""))
    tests = report.get("tests")
    counts = report.get("counts")
    if not isinstance(tests, list) or not isinstance(counts, dict):
        return False, "TEST_RESULT_MALFORMED"
    ids, outcomes = set(), []
    for item in tests:
        if (not isinstance(item, dict) or not isinstance(item.get("id"), str)
                or not isinstance(item.get("outcome"), str)):
            return False, "TEST_RESULT_MALFORMED"
        ids.add(_short_id(item["id"]))
        outcomes.append(item["outcome"])
    expected = {_short_id(item) for item in expected_ids}
    missing, extra = sorted(expected - ids), sorted(ids - expected)
    if missing or extra:
        return False, "TEST_ID_SET_MISMATCH missing=%s extra=%s" % (
            missing[:5], extra[:5])
    if exit_code is not None:
        ran = counts.get("ran", 0)
        want = 0 if (ran > 0 and not counts.get("failures")
                     and not counts.get("errors")) else 1
        if exit_code != want:
            return False, "TEST_EXIT_STATUS_INCONSISTENT exit=%d expected=%d" % (
                exit_code, want)
    return True, ""


def _parse_runner_report(raw):
    """The last parseable JSON object of our version on the channel, or None."""
    if not raw:
        return None
    for line in reversed(raw.decode("utf-8", "replace").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            report = json.loads(line)
        except ValueError:
            continue
        if isinstance(report, dict) and report.get("version") == RUNNER_VERSION:
            return report
    return None


def _evaluate_run(report, nonce, expected_ids, run):
    """Turn one signed report into an outcome word plus the counts it proved."""
    empty = {"ran": 0, "failures": 0, "errors": 0, "skipped": 0, "unexpected": 0}
    code = run.returncode if run is not None else None

    def failed(outcome, reason):
        return {"outcome": outcome, "reason": reason, "counts": dict(empty),
                "tests": [], "executed": [], "source_reads": [], "returncode": code}

    if run is None:
        return failed("NO_RESULT", "TEST_RUNNER_NOT_RUNNABLE")
    if not isinstance(report, dict) or report.get("version") != RUNNER_VERSION:
        return failed("NO_RESULT", "TEST_RESULT_UNAVAILABLE")
    if not _verify_report_mac(report, nonce):
        return failed("TAMPERED", "TEST_RESULT_MAC_INVALID")
    counts = report.get("counts") if isinstance(report.get("counts"), dict) else empty
    tests = report.get("tests") if isinstance(report.get("tests"), list) else []
    evaluation = {"outcome": "", "reason": "", "counts": counts, "tests": tests,
                  "executed": report.get("executed") or [],
                  "source_reads": report.get("source_reads") or [],
                  "returncode": code}
    violations = report.get("integrity_violation")
    if violations:
        evaluation["outcome"] = "INTEGRITY_VIOLATION"
        evaluation["reason"] = "INTEGRITY_VIOLATION " + ",".join(
            str(item) for item in violations[:8])
        return evaluation
    if report.get("load_error"):
        evaluation["outcome"] = "IMPORT_ERROR"
        evaluation["reason"] = "TEST_IMPORT_ERROR %s" % report.get("load_error")
        return evaluation
    ok, reason = _accept_report(report, nonce, expected_ids, run.returncode)
    if not ok:
        evaluation["outcome"] = "TAMPERED"
        evaluation["reason"] = reason
        return evaluation
    ran = counts.get("ran", 0)
    if ran < 1:
        evaluation["outcome"] = "NO_TESTS"
    elif counts.get("errors"):
        evaluation["outcome"] = "ERRORS"
    elif counts.get("skipped"):
        evaluation["outcome"] = "SKIPPED"
    elif counts.get("failures"):
        evaluation["outcome"] = ("CLEAN_FAILURE" if run.returncode != 0
                                 else "FAILURES_WITH_RC0")
    else:
        evaluation["outcome"] = "PASS" if run.returncode == 0 else "RC_NONZERO"
    return evaluation


def _runner_source():
    return Path(__file__).resolve().parent / RUNNER_NAME


def _stage_runner(work):
    """Copy the harness-owned runner outside the phase, fresh for every execution."""
    directory = Path(work) / "runner"
    if directory.exists() or directory.is_symlink():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)
    target = directory / RUNNER_NAME
    shutil.copyfile(_runner_source(), target)
    return target


def _invoke_runner(work, cwd, env, prefix, runner_args, nonce, watch=None,
                   targets=None, timeout=None):
    """Run the harness runner; returns ``(signed report or None, RunResult)``.

    The nonce travels on a pipe the runner reads and closes before it imports any package
    code; the report comes back on a second pipe. Neither is a path the package can
    reach, and the package never sees the nonce.
    """
    runner = _stage_runner(work)
    handshake = _canonical_json({"nonce": _nonce_bytes(nonce).hex(),
                                 "watch": watch or {},
                                 "targets": targets or {}}).encode("utf-8")
    if len(handshake) > 60000:  # pragma: no cover - watch lists are small
        raise ValueError("runner handshake would not fit in the pipe buffer")
    nonce_read, nonce_write = os.pipe()
    result_read, result_write = os.pipe()
    try:
        os.write(nonce_write, handshake)
    finally:
        os.close(nonce_write)
    command = [sys.executable, str(runner),
               "--nonce-fd", str(nonce_read), "--result-fd", str(result_write)]
    command.extend(runner_args)
    command = list(prefix) + command
    try:
        # The parent drops its copies of the child's ends right after the fork, or the
        # result pipe would never reach EOF and every run would wait for the timeout.
        run, extra = _capture(command, cwd, env, timeout=timeout,
                              pass_fds=(nonce_read, result_write),
                              extra_fds=(result_read,),
                              close_after_spawn=(nonce_read, result_write))
    finally:
        for fd in (nonce_read, result_write):
            try:
                os.close(fd)
            except OSError:  # pragma: no cover - already closed after the spawn
                pass
    try:
        report = _parse_runner_report(extra.get(result_read, b""))
    finally:
        os.close(result_read)
    return report, run


def _base_hidden_reasons(evaluation):
    outcome = evaluation["outcome"]
    counts = evaluation["counts"]
    if outcome == "IMPORT_ERROR":
        return ["HIDDEN_TEST_IMPORT_ERROR"]
    if outcome in ("NO_RESULT", "TAMPERED", "INTEGRITY_VIOLATION"):
        return [f"HIDDEN_TEST_RESULT_REJECTED {evaluation['reason']}"]
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


def _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile, with_hidden, patch,
                   hidden_rel=None):
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
        # P1-2 round C1: the hidden test runs under a randomised file name. A package
        # initialiser that forges "pass" only when it sees ``test_hidden.py`` in
        # ``sys.argv`` no longer recognises the run.
        target = hidden_rel or manifest["hidden_test_dest"]
        destination = repo / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(Path(pkg) / "hidden" / "test_hidden.py", destination)
    return repo


# --- what the test files declare, from the AST only ------------------------------
# The signed report says which tests ran. This says which tests the file says exist, so a
# run that silently skips, hides or invents a test cannot agree with both.

def _static_test_ids(paths):
    """Every ``Class.method`` reachable as a unittest case, from ``ast`` alone."""
    ids = set()
    for path in paths:
        try:
            tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        classes = {node.name: node for node in tree.body
                   if isinstance(node, ast.ClassDef)}
        cache = {}

        def is_case(name, seen=()):
            if name in cache:
                return cache[name]
            node = classes.get(name)
            if node is None or name in seen:
                return False
            answer = False
            for base in node.bases:
                if isinstance(base, ast.Attribute) and base.attr.endswith("TestCase"):
                    answer = True
                elif isinstance(base, ast.Name) and (
                        base.id.endswith("TestCase")
                        or (base.id in classes and is_case(base.id, seen + (name,)))):
                    answer = True
            cache[name] = answer
            return answer

        for name, node in classes.items():
            if not is_case(name):
                continue
            for item in node.body:
                if (isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and item.name.startswith("test")):
                    ids.add("%s.%s" % (name, item.name))
    return ids


def _visible_test_files(root):
    return sorted(path for path in Path(root).rglob("test*.py") if path.is_file())


def _imports_src(text):
    """True when the hidden test imports something from ``src`` (P2-3)."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and (module == "src" or module.startswith("src.")):
                return True
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "src" or alias.name.startswith("src."):
                    return True
    return False


# --- which changed lines the patch adds, and which of them really run (P1-2 b) ---

PATCH_HUNK_RE = re.compile(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")
# The same hunk header with the OLD start captured too: the structural rule maps an
# added line to the base line it is inserted at, so it needs the old-side cursor.
PATCH_HUNK_FULL_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def _interesting_patch_line(text):
    """A line whose execution would mean the patch did something.

    Blank lines, comments, decorators and pure ``def``/``class`` statements are out: a
    ``def`` line runs once at import even when the function is never called, and a
    docstring-only or comment-only patch is exactly the N21 shape.
    """
    stripped = text.strip()
    if not stripped or stripped.startswith("#"):
        return False
    return not stripped.startswith(("def ", "class ", "async def ", "@"))


def _patch_changed_lines(patch_text):
    """``{path: {new file line number}}`` for added, interesting lines."""
    changed = {}
    current = None
    old_left = new_left = 0
    new_line = 0
    for line in patch_text.splitlines():
        if old_left > 0 or new_left > 0:
            if line.startswith("+"):
                if _interesting_patch_line(line[1:]):
                    changed.setdefault(current, set()).add(new_line)
                new_line += 1
                new_left -= 1
            elif line.startswith("-"):
                old_left -= 1
            else:
                old_left -= 1
                new_left -= 1
                new_line += 1
            continue
        match = PATCH_HUNK_RE.match(line)
        if match:
            old_left = int(match.group(1) or 1)
            new_line = int(match.group(2))
            new_left = int(match.group(3) or 1)
            continue
        if line.startswith("+++ "):
            target = line[4:].split("\t")[0].strip()
            if target.startswith("b/"):
                target = target[2:]
            current = None if target == "/dev/null" else target
            continue
        if line.startswith("diff --git"):
            current = None
    return {path: lines for path, lines in changed.items() if path}


def _patch_added_lines(patch_text):
    """``{path: [(new_line, base_line, text), ...]}`` for EVERY added line.

    ``new_line`` is the line in the patched file (used by the structural rule against the
    patched AST); ``base_line`` is the old-side cursor, the line in ``base/`` at which the
    added block starts, kept for callers that need the insertion point.
    """
    added = {}
    current = None
    old_left = new_left = 0
    old_line = new_line = 0
    removal_start = None
    removed_count = added_count = 0
    for line in patch_text.splitlines():
        if old_left > 0 or new_left > 0:
            if line.startswith("+"):
                # The first added lines replace the removed block position by position;
                # anything beyond it is inserted after the block.
                if removal_start is not None and added_count < removed_count:
                    base_line = removal_start + added_count
                else:
                    base_line = old_line
                added.setdefault(current, []).append((new_line, base_line, line[1:]))
                added_count += 1
                new_line += 1
                new_left -= 1
            elif line.startswith("-"):
                if removal_start is None:
                    removal_start = old_line
                    removed_count = 0
                old_line += 1
                removed_count += 1
                old_left -= 1
            else:
                removal_start = None
                removed_count = added_count = 0
                old_line += 1
                new_line += 1
                old_left -= 1
                new_left -= 1
            continue
        match = PATCH_HUNK_FULL_RE.match(line)
        if match:
            old_line = int(match.group(1))
            old_left = int(match.group(2) or 1)
            new_line = int(match.group(3))
            new_left = int(match.group(4) or 1)
            removal_start = None
            removed_count = added_count = 0
            continue
        if line.startswith("+++ "):
            target = line[4:].split("\t")[0].strip()
            if target.startswith("b/"):
                target = target[2:]
            current = None if target == "/dev/null" else target
            continue
        if line.startswith("diff --git"):
            current = None
    return {path: lines for path, lines in added.items() if path}


def _top_level_names(tree):
    """Every name a module binds at top level: defs, classes, assignments, imports."""
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                if alias.name == "*":
                    continue
                names.add(alias.asname or alias.name.split(".")[0])
    return names


def _statement_api_names(statement_text):
    """Names the statement asks the maker to add: backticked, or written as a call.

    This is the narrow carve-out that keeps a legitimate feature task (the driver's
    ``perimeter`` fixture) valid: a new top-level name is allowed only when the task
    statement names it. An unrelated ``_extra`` the statement never mentions is refused.
    """
    names = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", statement_text))
    names.update(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", statement_text))
    return names


def _function_spans(tree):
    return [(node.lineno, node.end_lineno or node.lineno)
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _patch_structure_reasons(pkg, repo, patch_text):
    """P1-1 round C1: the reference patch may only change existing function bodies.

    * every added line must fall inside a function or method body that already exists in
      ``base/`` (or inside a new top-level def/class the statement explicitly asks for);
    * a new top-level def/class/name the statement does not name is ``PATCH_ADDS_NEW_API``;
    * a module-level line outside any function is ``PATCH_OUTSIDE_EXISTING_FUNCTION``.

    This is the primary defence against a "fix" that adds an unrelated helper and has the
    hidden test assert on it; the source-read guard is the secondary defence.
    """
    reasons = []
    statement_path = Path(pkg) / "statement.md"
    try:
        statement = statement_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        statement = ""
    allowed_new = _statement_api_names(statement)
    for path, entries in _patch_added_lines(patch_text).items():
        base_path = Path(pkg) / "base" / path
        new_path = Path(repo) / path
        try:
            base_tree = ast.parse(base_path.read_text(encoding="utf-8"))
            new_tree = ast.parse(new_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        base_top = _top_level_names(base_tree)
        new_top = _top_level_names(new_tree)
        new_functions = [node for node in ast.walk(new_tree)
                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]

        def enclosing(line):
            candidates = [node for node in new_functions
                          if node.lineno <= line <= (node.end_lineno or node.lineno)]
            if not candidates:
                return None
            return min(candidates, key=lambda node: (node.end_lineno or node.lineno)
                       - node.lineno)

        # New top-level names: refused unless the task statement asks for them.
        for name in sorted(new_top - base_top):
            if name not in allowed_new:
                reasons.append(f"PATCH_ADDS_NEW_API {path}:{name}")
        new_names = new_top - base_top
        for new_line, _base_line, text in entries:
            stripped = text.strip()
            if not stripped or stripped.startswith(("#", "@")):
                continue
            function = enclosing(new_line)
            if function is not None:
                # Inside any function of the patched file. An existing function is the
                # legitimate case; a brand-new one was already judged by the new-name
                # rule above (allowed when the statement asks for it, refused otherwise).
                continue
            match = re.match(r"^(?:async\s+)?(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)",
                             stripped)
            if match:
                # A def/class line for an existing function is a signature change; a new
                # name was already reported above.
                continue
            match = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*(?::[^=]+)?=", stripped)
            if match:
                if match.group(1) in new_names:
                    # A new module-level binding; the new-name rule already reported it.
                    continue
                reasons.append(f"PATCH_OUTSIDE_EXISTING_FUNCTION {path}:{new_line} "
                               f"{stripped[:60]}")
                continue
            reasons.append(f"PATCH_OUTSIDE_EXISTING_FUNCTION {path}:{new_line} "
                           f"{stripped[:60]}")
    # De-duplicate while keeping the first occurrence.
    seen, unique = set(), []
    for reason in reasons:
        if reason not in seen:
            seen.add(reason)
            unique.append(reason)
    return unique


_UNKNOWN = object()


def _constant_value(node):
    """The value of a literal expression, or ``_UNKNOWN`` when it is not literal."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        inner = _constant_value(node.operand)
        if inner is not _UNKNOWN:
            return not inner
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        inner = _constant_value(node.operand)
        if isinstance(inner, (int, float, complex)):
            return -inner if isinstance(node.op, ast.USub) else +inner
    return _UNKNOWN


def _is_constant_expr(node):
    """True for a literal expression (``1``, ``"x"``, ``...``, ``True``, a literal tuple)."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.UnaryOp):
        return _is_constant_expr(node.operand)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(_is_constant_expr(item) for item in node.elts)
    if isinstance(node, ast.Dict):
        return (all(key is None or _is_constant_expr(key) for key in node.keys)
                and all(_is_constant_expr(value) for value in node.values))
    return False


def _trivial_statement(node, module_loads):
    """A statement whose execution cannot change behaviour on its own.

    P1-1 (b): a bare constant/Ellipsis expression, ``pass``, ``assert <constant>`` and an
    assignment of a constant to a name never read elsewhere in the module are all refused
    as "the patch ran"; they are exactly the N24/N25 shapes.
    """
    if isinstance(node, ast.Pass):
        return True
    if isinstance(node, ast.Expr) and _is_constant_expr(node.value):
        return True
    if isinstance(node, ast.Assert) and _is_constant_expr(node.test):
        return True
    if isinstance(node, ast.Assign) and _is_constant_expr(node.value):
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if names and all(name not in module_loads for name in names):
            return True
    if (isinstance(node, ast.AnnAssign) and node.value is not None
            and _is_constant_expr(node.value) and isinstance(node.target, ast.Name)
            and node.target.id not in module_loads):
        return True
    return False


def _child_blocks(statement):
    """``(body, dead)`` for every nested statement block, with literal-false branches dead."""
    blocks = []
    if isinstance(statement, ast.If):
        value = _constant_value(statement.test)
        if value is _UNKNOWN:
            blocks.append((statement.body, False))
            blocks.append((statement.orelse, False))
        else:
            blocks.append((statement.body, not value))
            blocks.append((statement.orelse, bool(value)))
    elif isinstance(statement, ast.While):
        value = _constant_value(statement.test)
        blocks.append((statement.body, value is not _UNKNOWN and not value))
        blocks.append((statement.orelse, False))
    elif isinstance(statement, (ast.For, ast.AsyncFor)):
        blocks.append((statement.body, False))
        blocks.append((statement.orelse, False))
    elif isinstance(statement, (ast.With, ast.AsyncWith)):
        blocks.append((statement.body, False))
    elif isinstance(statement, ast.Try):
        blocks.append((statement.body, False))
        for handler in statement.handlers:
            blocks.append((handler.body, False))
        blocks.append((statement.orelse, False))
        blocks.append((statement.finalbody, False))
    elif isinstance(statement, ast.Match):
        for case in statement.cases:
            blocks.append((case.body, False))
    return blocks


def _iter_statements(body, dead=False):
    """Yield ``(statement, dead)`` for a block and its nested blocks.

    A statement after an unconditional ``return``/``raise`` in the same block is dead, and
    so is everything inside ``if False:`` (or any literal-false branch).
    """
    terminated = False
    for statement in body:
        yield statement, dead or terminated
        for child, child_dead in _child_blocks(statement):
            yield from _iter_statements(child, dead or terminated or child_dead)
        if isinstance(statement, (ast.Return, ast.Raise)):
            terminated = True


def _watchable_lines(text):
    """Line numbers of non-trivial, live statements inside a function or method body."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set()
    module_loads = {node.id for node in ast.walk(tree)
                    if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    watchable = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for statement, dead in _iter_statements(node.body):
            if dead or _trivial_statement(statement, module_loads):
                continue
            start = statement.lineno
            end = statement.end_lineno or start
            watchable.update(range(start, end + 1))
    return watchable


def _patch_watch(repo, patch_text):
    """``{absolute path: [line numbers to watch]}`` for changed, non-trivial body lines."""
    watch = {}
    for path, lines in _patch_changed_lines(patch_text).items():
        target = Path(repo) / path
        if not target.is_file():
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        watchable = _watchable_lines(text)
        wanted = sorted(number for number in lines if number in watchable)
        if wanted:
            watch[str(os.path.realpath(target))] = wanted
    return watch


def _patch_targets(repo, patch_text):
    """``{absolute path: [[first, last], ...]}`` for the functions the patch changes.

    Round C1: this is the *specific* function whose body contains an added line, not every
    function in the patched file. The hidden test must call one of these (P1-1 c), so a
    patch that changes ``slugify`` while the hidden test only calls ``word_count`` is
    refused instead of being waved through by an unrelated function in the same file.
    """
    targets = {}
    for path, entries in _patch_added_lines(patch_text).items():
        target = Path(repo) / path
        if not target.is_file():
            continue
        try:
            tree = ast.parse(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError):
            continue
        spans = _function_spans(tree)
        ranges = set()
        for new_line, _base_line, _text in entries:
            containing = [(start, end) for start, end in spans
                          if start <= new_line <= end]
            if containing:
                ranges.add(min(containing, key=lambda span: span[1] - span[0]))
        if ranges:
            targets[str(os.path.realpath(target))] = sorted(ranges)
    return targets


def _exercised_lines(evaluations):
    """``(all_executed, test_executed)`` from the signed ``executed`` records.

    A record is ``[path, line]`` (legacy: treated as executed from the test) or
    ``[path, line, from_test]``. ``test_executed`` is the subset whose immediate caller was
    the hidden test file, so a function that only ran at import time cannot satisfy the
    "hidden test calls the patched function" rule.
    """
    executed, from_test = set(), set()
    for evaluation in evaluations:
        for item in evaluation.get("executed") or []:
            if isinstance(item, (list, tuple)) and len(item) in (2, 3):
                try:
                    key = (os.path.realpath(str(item[0])), int(item[1]))
                except (TypeError, ValueError):  # pragma: no cover - practised runner
                    continue
                executed.add(key)
                if len(item) == 2 or item[2]:
                    from_test.add(key)
    return executed, from_test


def _patch_exercise_reason(repo, patch_text, evaluations):
    """None when a changed, executable line ran; otherwise the PATCH_NOT_EXERCISED text."""
    watch = _patch_watch(repo, patch_text)
    if not watch:
        return ("PATCH_NOT_EXERCISED the patch adds no executable line "
                "(comment, docstring, declaration or blank only)")
    executed, _from_test = _exercised_lines(evaluations)
    total = sum(len(lines) for lines in watch.values())
    for path, lines in watch.items():
        hit = [number for number in lines
               if (os.path.realpath(path), number) in executed]
        if hit:
            return None
    sample = sorted((Path(path).name, number) for path, lines in watch.items()
                    for number in lines)[:5]
    return ("PATCH_NOT_EXERCISED none of the %d added/changed executable lines ran "
            "during the hidden test; watched=%s" % (total, sample))


def _patch_target_reason(repo, patch_text, evaluations):
    """None when the hidden test called a function the patch actually changed (P1-1 c)."""
    targets = _patch_targets(repo, patch_text)
    if not targets:
        return ("HIDDEN_TEST_NEVER_CALLS_TARGET the patch changes no function or method "
                "body")
    _executed, from_test = _exercised_lines(evaluations)
    for path, spans in targets.items():
        for start, end in spans:
            if any((path, line) in from_test for line in range(start, end + 1)):
                return None
    return ("HIDDEN_TEST_NEVER_CALLS_TARGET no function or method the patch changed was "
            "called by the hidden test")


def _visible_argv():
    """The canonical argv, kept for display: the runner replaces its execution."""
    return [sys.executable] + CANONICAL_TEST_COMMAND[1:]


def _sandbox_prefix(sandbox, profile):
    return [str(sandbox), "-f", str(profile)] if sandbox else []


def _phase_env(work):
    return _environment(_phase_root(work) / "home")


def _run_visible(work, repo, sandbox, profile, check_id, label):
    expected = _static_test_ids(_visible_test_files(Path(repo) / "tests"))
    nonce = _new_nonce()
    report, run = _invoke_runner(
        work, repo, _phase_env(work), _sandbox_prefix(sandbox, profile),
        ["--discover", "tests", "--top", "."], nonce)
    run = _guard(check_id, run, label)
    evaluation = _evaluate_run(report, nonce, expected, run)
    evaluation["expected_ids"] = expected
    evaluation["command"] = list(CANONICAL_TEST_COMMAND)
    return evaluation


def _hidden_runs(work, repo, manifest, sandbox, profile, check_id, label, watch=None,
                 targets=None, hidden_rel=None):
    hidden_rel = hidden_rel or manifest["hidden_test_dest"]
    test_path = Path(repo) / hidden_rel
    expected = _static_test_ids([test_path])
    evaluations = []
    for _attempt in range(HIDDEN_REPEATS):
        nonce = _new_nonce()
        report, run = _invoke_runner(
            work, repo, _phase_env(work), _sandbox_prefix(sandbox, profile),
            ["--tests", hidden_rel], nonce, watch=watch, targets=targets)
        run = _guard(check_id, run, label)
        evaluations.append(_evaluate_run(report, nonce, expected, run))
        # P2-1: stop at the first disagreement; more agreeing runs cannot repair it.
        if len(evaluations) > 1 and evaluations[-1]["outcome"] != evaluations[0]["outcome"]:
            break
    return evaluations, expected


def _phase_base(work, pkg, manifest, patch_text, sandbox, profile):
    """Check 2: the project is green on its own before anything is added."""
    reasons, data = [], {}
    repo = _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile,
                          with_hidden=False, patch=False)
    evaluation = _run_visible(work, repo, sandbox, profile, 2, "VISIBLE_TESTS")
    counts = evaluation["counts"]
    data["visible"] = counts
    data["phase"] = str(repo)
    data["visible_ids"] = sorted(evaluation["expected_ids"])
    data["command"] = evaluation["command"]
    data["executed_by"] = RUNNER_NAME
    if evaluation["outcome"] != "PASS":
        reasons.append(
            "VISIBLE_TESTS_FAIL rc={} outcome={} failures={} errors={} ran={}".format(
                evaluation["returncode"], evaluation["outcome"], counts["failures"],
                counts["errors"], counts["ran"]))
    if evaluation["outcome"] in ("NO_RESULT", "TAMPERED", "INTEGRITY_VIOLATION"):
        reasons.append("VISIBLE_TESTS_RESULT_REJECTED %s" % evaluation["reason"])
    ruff = _guard(2, _phase_run(work, sandbox, profile,
                                [sys.executable, "-m", "ruff", "check", "--no-cache", "."]),
                  "RUFF")
    data["ruff_base"] = ruff.returncode
    if ruff.returncode != 0:
        reasons.append(f"RUFF_DIRTY_AT_BASE rc={ruff.returncode} {ruff.output.strip()[:200]}")
    return _result(2, "PASS" if not reasons else "FAIL", reasons, data)


def _phase_hidden_at_base(work, pkg, manifest, patch_text, sandbox, profile,
                          hidden_rel=None):
    """Check 3: a clean, deterministic failure at base."""
    repo = _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile,
                          with_hidden=True, patch=False, hidden_rel=hidden_rel)
    runs, expected = _hidden_runs(work, repo, manifest, sandbox, profile, 3,
                                  "HIDDEN_TEST", hidden_rel=hidden_rel)
    outcomes = [run["outcome"] for run in runs]
    counts = runs[0]["counts"]
    source_reads = sorted({item for run in runs for item in run.get("source_reads") or []})
    data = {"phase": str(repo), "runs": outcomes, "hidden_at_base": counts,
            "returncode": runs[0]["returncode"], "hidden_ids": sorted(expected),
            "source_reads": source_reads, "executed_by": RUNNER_NAME}
    reasons = []
    if len(set(outcomes)) > 1:
        reasons.append(f"NONDETERMINISTIC base outcomes={outcomes}")
        for evaluation in runs:
            if evaluation["outcome"] in ("NO_RESULT", "TAMPERED", "INTEGRITY_VIOLATION"):
                reasons.append("HIDDEN_TEST_RESULT_REJECTED %s" % evaluation["reason"])
    else:
        reasons.extend(_base_hidden_reasons(runs[0]))
    if source_reads:
        reasons.append("SOURCE_READ_BY_TEST the hidden test read %s"
                       % ", ".join(source_reads[:5]))
    hidden_text = (Path(pkg) / "hidden" / "test_hidden.py").read_text(encoding="utf-8")
    if not _imports_src(hidden_text):
        reasons.append("HIDDEN_TEST_DOES_NOT_IMPORT_TARGET")
    return _result(3, "PASS" if not reasons else "FAIL", reasons, data)


def _phase_after_patch(work, pkg, manifest, patch_text, sandbox, profile,
                       hidden_rel=None):
    """Check 4: the reference makes the hidden test pass and keeps everything else green."""
    reasons, data = [], {}
    text = patch_text.decode("utf-8") if isinstance(patch_text, bytes) else patch_text
    repo = _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile,
                          with_hidden=True, patch=True, hidden_rel=hidden_rel)
    # P1-1 round C1: the structural rule runs on the patched tree, so it sees the base
    # AST and the new AST at the same time. Its reasons are recorded even when the hidden
    # test also fails, so the distinct code is always visible.
    structural = _patch_structure_reasons(pkg, repo, text)
    watch = _patch_watch(repo, text)
    targets = _patch_targets(repo, text)
    runs, expected = _hidden_runs(work, repo, manifest, sandbox, profile, 4,
                                  "HIDDEN_TEST_AFTER_PATCH", watch=watch, targets=targets,
                                  hidden_rel=hidden_rel)
    outcomes = [run["outcome"] for run in runs]
    counts = runs[0]["counts"]
    source_reads = sorted({item for run in runs for item in run.get("source_reads") or []})
    data.update({"phase": str(repo), "runs": outcomes, "hidden_after_patch": counts,
                 "returncode": runs[0]["returncode"], "hidden_ids": sorted(expected),
                 "source_reads": source_reads,
                 "watched_lines": {Path(path).name: len(lines)
                                   for path, lines in watch.items()},
                 "executed_by": RUNNER_NAME, "patch_exercised": False,
                 "target_called": False, "patch_structure": list(structural)})
    reasons.extend(structural)
    if len(set(outcomes)) > 1:
        reasons.append(f"NONDETERMINISTIC after_patch outcomes={outcomes}")
        for evaluation in runs:
            if evaluation["outcome"] in ("NO_RESULT", "TAMPERED", "INTEGRITY_VIOLATION"):
                reasons.append("HIDDEN_TEST_RESULT_REJECTED %s" % evaluation["reason"])
    elif outcomes[0] != "PASS":
        if outcomes[0] in ("NO_RESULT", "TAMPERED", "INTEGRITY_VIOLATION"):
            reasons.append("HIDDEN_TEST_RESULT_REJECTED %s" % runs[0]["reason"])
        reasons.append(
            "HIDDEN_TEST_FAILS_AFTER_PATCH rc={} outcome={} failures={} errors={} "
            "skipped={} ran={}".format(
                runs[0]["returncode"], outcomes[0], counts["failures"], counts["errors"],
                counts["skipped"], counts["ran"]))
    else:
        # P1-1 b: the reference must change something that actually runs.
        exercised = _patch_exercise_reason(repo, text, runs)
        data["patch_exercised"] = exercised is None
        if exercised:
            reasons.append(exercised)
        # P1-1 c: the hidden test must call a function defined in a patched file.
        called = _patch_target_reason(repo, text, runs)
        data["target_called"] = called is None
        if called:
            reasons.append(called)
    if source_reads:
        reasons.append("SOURCE_READ_BY_TEST the hidden test read %s"
                       % ", ".join(source_reads[:5]))

    # Same path, fresh tree, no hidden test: the visible suite the worker must not break.
    repo = _prepare_phase(work, pkg, manifest, patch_text, sandbox, profile,
                          with_hidden=False, patch=True)
    evaluation = _run_visible(work, repo, sandbox, profile, 4,
                              "VISIBLE_TESTS_AFTER_PATCH")
    visible_counts = evaluation["counts"]
    data["visible_after_patch"] = visible_counts
    if evaluation["outcome"] != "PASS":
        reasons.append(
            "VISIBLE_TESTS_BROKEN_BY_PATCH rc={} outcome={} failures={} errors={} "
            "ran={}".format(evaluation["returncode"], evaluation["outcome"],
                            visible_counts["failures"], visible_counts["errors"],
                            visible_counts["ran"]))
    if evaluation["outcome"] in ("NO_RESULT", "TAMPERED", "INTEGRITY_VIOLATION"):
        reasons.append("VISIBLE_TESTS_RESULT_REJECTED %s" % evaluation["reason"])
    ruff = _guard(4, _phase_run(work, sandbox, profile,
                                [sys.executable, "-m", "ruff", "check", "--no-cache", "."]),
                  "RUFF_AFTER_PATCH")
    data["ruff_after_patch"] = ruff.returncode
    if ruff.returncode != 0:
        reasons.append(f"RUFF_DIRTY_AFTER_PATCH rc={ruff.returncode} {ruff.output.strip()[:200]}")
    return _result(4, "PASS" if not reasons else "FAIL", reasons, data)


def _dynamic_checks(work, pkg, manifest, patch_text, sandbox, profile, hidden_rel=None):
    """Run checks 2-4 in order; a timeout or overflow stops everything that follows."""
    results = {}
    try:
        results[2] = _phase_base(work, pkg, manifest, patch_text, sandbox, profile)
        results[3] = _phase_hidden_at_base(work, pkg, manifest, patch_text, sandbox, profile,
                                           hidden_rel=hidden_rel)
        results[4] = _phase_after_patch(work, pkg, manifest, patch_text, sandbox, profile,
                                        hidden_rel=hidden_rel)
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
    # P2-2: a directory (or any other non-regular file) named SEAL.json is a refusal, not
    # "no seal yet". ``is_file`` follows symlinks, so test the link itself first.
    if seal_path.is_symlink() or (os.path.lexists(seal_path) and not seal_path.is_file()):
        return _result(7, "FAIL", ["SEAL_NOT_A_FILE"], {"state": "NOT_A_FILE"})
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


def run_tests_with_runner(tree, test_ids_or_file=None, nonce=None, watch=None,
                          targets=None, timeout=None, discover="tests", top="."):
    """Run tests in ``tree`` through ``test_runner.py`` and return a verified report.

    This is the only supported way for a later step (ticket B, ``pilot_accept.py``) to run
    a hidden test. It applies the same MAC discipline as ``verify_package``:

    * ``tree`` must be a FRESH copy of the candidate and becomes the runner's cwd;
    * ``nonce`` is a one-time secret -- pass ``secrets.token_hex(32)``; ``None`` makes this
      function generate one, which is only useful when the caller trusts this process;
    * a result is accepted only when the runner's HMAC verifies, the runner's own exit
      status agrees with its counts, and the test ids equal the static ``ast`` set.

    ``test_ids_or_file`` is a test file relative to ``tree``, an iterable of dotted test
    ids, or ``None`` to discover ``discover``. Returns::

        {"accepted": bool,      # the report is authentic and the ids match
         "outcome": str,        # PASS | CLEAN_FAILURE | ERRORS | SKIPPED | IMPORT_ERROR |
                                # NO_TESTS | NO_RESULT | TAMPERED
         "reason": str,         # why it was not accepted, or ""
         "tests": [{"id": ..., "outcome": ...}],
         "counts": {...}, "exit_code": int, "executed": [[path, line], ...],
         "expected_ids": [...], "output": str}

    ``output`` is captured only for the size cap and is never parsed for a verdict. An
    empty ``tests`` list plus ``accepted`` true means the suite collected nothing.
    """
    root = Path(os.path.realpath(str(tree)))
    if not root.is_dir():
        raise ValueError("tree is not a directory: %s" % (tree,))
    if test_ids_or_file is None:
        runner_args = ["--discover", discover, "--top", top]
        expected = _static_test_ids(_visible_test_files(root / discover))
    elif isinstance(test_ids_or_file, (str, os.PathLike)):
        relative = Path(test_ids_or_file)
        runner_args = ["--tests", str(relative)]
        expected = _static_test_ids([root / relative])
    else:
        ids = [str(item) for item in test_ids_or_file]
        runner_args = []
        for item in ids:
            runner_args.extend(["--ids", item])
        expected = set(ids)
    nonce = _new_nonce() if nonce is None else _nonce_bytes(nonce).hex()

    empty = {"ran": 0, "failures": 0, "errors": 0, "skipped": 0, "unexpected": 0}
    with tempfile.TemporaryDirectory(prefix="h4-runner-") as temporary:
        work = Path(os.path.realpath(temporary)) / "work"
        (work / "home" / "tmp").mkdir(parents=True)
        report, run = _invoke_runner(work, root, _environment(work / "home"), [],
                                     runner_args, nonce, watch=watch, targets=targets,
                                     timeout=timeout)
        if run is None:
            evaluation = {"outcome": "NO_RESULT", "reason": "TEST_RUNNER_NOT_RUNNABLE",
                          "counts": empty, "tests": [], "executed": []}
        elif run.timed_out:
            evaluation = {"outcome": "NO_RESULT", "reason": "TEST_RUNNER_TIMEOUT",
                          "counts": empty, "tests": [], "executed": []}
        elif run.overflow:
            evaluation = {"outcome": "NO_RESULT", "reason": "TEST_RUNNER_OUTPUT_OVERFLOW",
                          "counts": empty, "tests": [], "executed": []}
        else:
            evaluation = _evaluate_run(report, nonce, expected, run)
        return {
            "accepted": evaluation["outcome"] not in (
                "NO_RESULT", "TAMPERED", "INTEGRITY_VIOLATION"),
            "outcome": evaluation["outcome"],
            "reason": evaluation.get("reason", ""),
            "tests": evaluation.get("tests", []),
            "counts": evaluation.get("counts", empty),
            "exit_code": getattr(run, "returncode", None),
            "executed": evaluation.get("executed", []),
            "source_reads": evaluation.get("source_reads", []),
            "expected_ids": sorted(expected),
            "output": getattr(run, "output", ""),
        }


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
            # P2-1: resolve the temp root once. Everything below it -- the phase directory,
            # HOME, TMPDIR, the runner copy and the sandbox profile -- then uses real paths,
            # so a symlinked TMPDIR (the macOS default) cannot break the write allow-list.
            work = Path(os.path.realpath(temporary)) / "work"
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
                # One randomised hidden-test name for every phase of this verification:
                # both phases see the same path, so the hidden test still cannot tell
                # which phase it is in, but a name-keyed forgery does not recognise it.
                hidden_rel = "tests/test_%s.py" % os.urandom(6).hex()
                checks.extend(_dynamic_checks(
                    work, pkg, manifest, patch_text.encode("utf-8"), sandbox, profile,
                    hidden_rel=hidden_rel))
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
    if report["seal"] in ("BROKEN", "NOT_A_FILE"):
        raise SealError("refusing to re-seal a package with a broken seal: "
                        + "; ".join(report["reasons"][:5]))
    if report["overall"] != "PASS":
        raise SealError("package verification failed: " + "; ".join(report["reasons"][:5]))
    seal_path = pkg / SEAL_NAME
    if seal_path.is_symlink() or (os.path.lexists(seal_path) and not seal_path.is_file()):
        raise SealError(f"refusing to write {SEAL_NAME}: SEAL_NOT_A_FILE")
    files = {name: _sha256(pkg / name) for name in _sealed_files(pkg)}
    payload = {"version": SEAL_VERSION, "files": dict(sorted(files.items())), "verified": True}
    try:
        seal_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")
    except OSError as error:
        raise SealError(f"could not write {SEAL_NAME}: {error}") from error


def verify_seal(pkg_dir):
    """Raise SealError unless SEAL.json matches every file exactly, and nothing is extra."""
    pkg = Path(pkg_dir)
    seal_path = pkg / SEAL_NAME
    if seal_path.is_symlink() or (os.path.lexists(seal_path) and not seal_path.is_file()):
        raise SealError(f"{SEAL_NAME} is not a regular file: SEAL_NOT_A_FILE")
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
        except (SealError, OSError) as error:
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
