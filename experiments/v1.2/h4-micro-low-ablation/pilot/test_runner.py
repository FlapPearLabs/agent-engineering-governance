#!/usr/bin/env python3
"""Harness-owned test runner for the H4 pilot task package (standard library only).

Why this file exists
--------------------
The package verifier must not believe anything the package prints. The acceptance report
(``ACCEPT.md`` P1-1/P1-2) showed that package code -- a module imported by the tests, or
the reference patch itself -- can print unittest's own summary (``Ran N tests`` / ``OK``)
and call ``os._exit(0)``, so a verifier that reads stdout accepts a suite that never ran.

So the verifier never parses unittest output any more. It starts *this* runner instead of
``python -m unittest`` and accepts a result only when all four hold:

1. one JSON line arrives on a dedicated inherited file descriptor;
2. that line carries ``nonce_mac = HMAC-SHA256(nonce, canonical json of the payload)``,
   and the parent is the only party that knows the nonce;
3. the runner's own exit status agrees with the counts the payload reports;
4. the set of test ids in the payload equals the set the parent found by static AST
   parsing of the test file(s).

A module that exits early, prints a fake summary, or writes a result without the nonce
produces no acceptable result, which is a FAIL -- never a PASS.

Handshake (parent -> runner)
----------------------------
The parent creates a one-time nonce and writes
``{"nonce": "<hex>", "watch": {...}, "targets": {...}}`` into a pipe. The runner reads
that pipe and closes it BEFORE it inserts the working directory into ``sys.path`` or
imports any package code. The nonce is never passed in ``argv``, never in the
environment, and never through a file inside the package. It is derived into a closure
key and deleted from the runner's frame before any package code is imported.

``watch`` maps an absolute path to a list of line numbers; the runner records which of
those lines execute (``sys.settrace``) while the tests run, so the parent can require the
reference patch to change something that actually runs (P1-2 b). ``targets`` maps an
absolute path to ``[[first, last], ...]`` line ranges of the functions and methods defined
in the patched files, so the parent can require the hidden test to call one of them
(P1-1 c).

While the tests run the runner also wraps ``builtins.open``, ``io.open``,
``pathlib.Path.open``/``read_text``/``read_bytes`` and ``os.open``. An open of the
project's ``src/`` tree, ``reference.patch`` or a hidden test file made from test code is
recorded as ``source_reads``; the import system's own file reads stay allowed because
their caller frame is ``importlib``/``zipimport`` (P1-1 a).

Result (runner -> parent)
-------------------------
Exactly one JSON line is written to the result fd::

    {"version": 1,
     "tests": [{"id": "Class.method", "outcome": "pass|failure|error|skip|..."}],
     "counts": {"ran": 0, "failures": 0, "errors": 0, "skipped": 0, "unexpected": 0},
     "load_error": null, "load_detail": "",
     "executed": [["/abs/path.py", 12]],
     "source_reads": ["src/example.py"],
     "integrity_violation": ["_Result.addFailure"],
     "nonce_mac": "<64 hex characters>"}

The MAC is computed over the canonical JSON of the payload without ``nonce_mac``
(``json.dumps(payload, sort_keys=True, separators=(",", ":"))``).

Exit status: 0 the suite ran and every collected test passed (skips allowed); 1 the suite
ran with failures/errors, or the test module could not be imported; 2 the runner itself
could not do its job -- no result line, and the parent must treat the run as unavailable.

Reuse from another module (ticket B / pilot_accept.py)
------------------------------------------------------
Do not run ``python -m unittest`` yourself. Use the parent-side helper that owns the MAC
discipline::

    import secrets
    result = taskpack.run_tests_with_runner(
        "/fresh/directory", "tests/test_hidden.py", secrets.token_hex(32))
    if not result["accepted"]:
        reject(result["reason"])
    elif any(item["outcome"] != "pass" for item in result["tests"]):
        reject("hidden test did not pass")

``tree`` is the root of a FRESH copy of the candidate (the runner uses it as ``cwd``),
``test_ids_or_file`` is a test file relative to that tree, a list of test ids, or
``None`` to discover ``tests``, and ``nonce`` is a one-time secret that must never be
reused. ``run_tests_with_runner`` returns a dict with ``accepted``, ``reason``, ``tests``,
``counts``, ``exit_code``, ``executed`` and ``output``; ``output`` is captured only for
the size cap and is never parsed for a verdict.
"""
from __future__ import annotations

import argparse
import builtins
import hashlib
import hmac
import importlib.util
import io
import json
import marshal
import os
import pathlib
import re
import sys
import unittest

REPORT_VERSION = 1
NONCE_MIN_BYTES = 16
HANDSHAKE_LIMIT = 1 << 20
EXECUTED_LIMIT = 20000
RESULT_LIMIT = 1 << 20
SOURCE_READ_LIMIT = 200


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _test_id(test):
    """``Class.method``; anything that is not a plain case keeps its own string."""
    method = getattr(test, "_testMethodName", None)
    if isinstance(test, unittest.TestCase) and method:
        return "%s.%s" % (type(test).__name__, method)
    return str(test)


# --- integrity snapshot (P1-2) --------------------------------------------------
# Cheap detection, not prevention: the runner records the identity and code-object hash
# of every function it relies on BEFORE package code is imported and re-checks them after
# the run. A package that swaps ``_Result.addFailure`` for a "record pass" function is
# reported as an integrity violation instead of being believed.

def _fingerprint(obj):
    """``(id, sha256(code object))``; builtins have no code object, so id only."""
    code = getattr(obj, "__code__", None)
    digest = ""
    if code is not None:
        try:
            digest = hashlib.sha256(marshal.dumps(code)).hexdigest()
        except (TypeError, ValueError):  # pragma: no cover - defensive
            digest = repr(code)
    return [id(obj), digest]


def _integrity_items():
    """``(name, getter)`` for everything whose replacement would change a verdict."""
    return [
        ("unittest.TestResult.addFailure", lambda: unittest.TestResult.addFailure),
        ("unittest.TestResult.addError", lambda: unittest.TestResult.addError),
        ("unittest.TestResult.addSkip", lambda: unittest.TestResult.addSkip),
        ("unittest.TestResult.addExpectedFailure",
         lambda: unittest.TestResult.addExpectedFailure),
        ("unittest.TestResult.addUnexpectedSuccess",
         lambda: unittest.TestResult.addUnexpectedSuccess),
        ("unittest.TestResult.addSuccess", lambda: unittest.TestResult.addSuccess),
        ("unittest.TestResult.wasSuccessful", lambda: unittest.TestResult.wasSuccessful),
        ("unittest.TestCase.run", lambda: unittest.TestCase.run),
        ("unittest.TestCase.assertEqual", lambda: unittest.TestCase.assertEqual),
        ("unittest.TestCase.assertNotEqual", lambda: unittest.TestCase.assertNotEqual),
        ("unittest.TestCase.assertTrue", lambda: unittest.TestCase.assertTrue),
        ("unittest.TestCase.assertFalse", lambda: unittest.TestCase.assertFalse),
        ("unittest.TestCase.assertIn", lambda: unittest.TestCase.assertIn),
        ("unittest.TestCase.assertNotIn", lambda: unittest.TestCase.assertNotIn),
        ("unittest.TestCase.assertIs", lambda: unittest.TestCase.assertIs),
        ("unittest.TestCase.assertIsNone", lambda: unittest.TestCase.assertIsNone),
        ("unittest.TestCase.assertRaises", lambda: unittest.TestCase.assertRaises),
        ("hmac.new", lambda: hmac.new),
        ("hmac.compare_digest", lambda: hmac.compare_digest),
        ("json.dumps", lambda: json.dumps),
        ("builtins.exec", lambda: builtins.exec),
        ("builtins.eval", lambda: builtins.eval),
        ("_Result.addFailure", lambda: _Result.addFailure),
        ("_Result.addError", lambda: _Result.addError),
        ("_Result.addSkip", lambda: _Result.addSkip),
        ("_Result.addExpectedFailure", lambda: _Result.addExpectedFailure),
        ("_Result.addUnexpectedSuccess", lambda: _Result.addUnexpectedSuccess),
        ("_Result.addSuccess", lambda: _Result.addSuccess),
        ("_Result._record", lambda: _Result._record),
        ("_test_id", lambda: _test_id),
        ("_canonical", lambda: _canonical),
        ("_write_all", lambda: _write_all),
    ]


def _integrity_snapshot():
    snapshot = {}
    for name, getter in _integrity_items():
        try:
            snapshot[name] = _fingerprint(getter())
        except Exception as error:  # noqa: BLE001 - a missing target is a violation later
            snapshot[name] = ["MISSING", type(error).__name__]
    return snapshot


def _integrity_violations(snapshot):
    changed = []
    for name, getter in _integrity_items():
        try:
            current = _fingerprint(getter())
        except Exception:  # noqa: BLE001 - a target that vanished was tampered with
            changed.append(name)
            continue
        if snapshot.get(name) != current:
            changed.append(name)
    return changed


class _Result(unittest.TestResult):
    """unittest's result object, plus a per-test outcome the parent can check."""

    def __init__(self):
        super().__init__()
        self.outcomes = {}

    def _record(self, test, outcome):
        self.outcomes[_test_id(test)] = outcome

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, "pass")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, "failure")

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, "error")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, "skip")

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._record(test, "expected_failure")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._record(test, "unexpected_success")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            failure = isinstance(test, unittest.TestCase) and issubclass(
                err[0], test.failureException)
            self._record(test, "failure" if failure else "error")


def _read_handshake(fd):
    """Read the nonce payload from the inherited fd and close it. No package code yet."""
    chunks, total = [], 0
    try:
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            total += len(chunk)
            if total > HANDSHAKE_LIMIT:
                raise ValueError("handshake too large")
            chunks.append(chunk)
    finally:
        os.close(fd)
    return json.loads(b"".join(chunks).decode("utf-8"))


def _read_target(path, repo_root):
    """A relative marker when ``path`` is package source or a hidden/reference file."""
    try:
        if isinstance(path, int):
            return None
        raw = os.fspath(path)
    except TypeError:
        return None
    if isinstance(raw, bytes):
        try:
            raw = raw.decode("utf-8", "surrogateescape")
        except UnicodeDecodeError:  # pragma: no cover - defensive
            return None
    if not raw:
        return None
    try:
        real = os.path.realpath(os.path.abspath(raw))
        root = os.path.realpath(repo_root)
        src = os.path.join(root, "src")
        if os.path.commonpath([real, src]) == src:
            return os.path.relpath(real, root)
    except (OSError, ValueError):  # pragma: no cover - defensive
        return None
    name = os.path.basename(real)
    if name in ("reference.patch", "test_hidden.py"):
        if real == root or real.startswith(root + os.sep):
            return os.path.relpath(real, root)
        return name
    return None


def _caller_is_import():
    """True when this open is the import system reading a module it must read."""
    frame = sys._getframe(1)
    while frame is not None:
        module = frame.f_globals.get("__name__", "")
        filename = frame.f_code.co_filename or ""
        if (module == "zipimport" or module.startswith("importlib")
                or "importlib" in filename or "zipimport" in filename):
            return True
        frame = frame.f_back
    return False


def _install_source_guard(repo_root):
    """Record test-code reads of ``src/``, ``reference.patch`` and hidden files.

    The guard is installed only around the test load/run and removed afterwards. It never
    blocks a read; it records one, because the parent -- not this process -- decides what
    a record means. The import system is exempt: its caller frame is ``importlib`` or
    ``zipimport``, otherwise every module import would be recorded.
    """
    records = []
    original_open = builtins.open
    original_io_open = io.open
    original_path_open = pathlib.Path.open
    original_read_text = pathlib.Path.read_text
    original_read_bytes = pathlib.Path.read_bytes
    original_os_open = os.open

    def record(path):
        marker = _read_target(path, repo_root)
        if marker and marker not in records and len(records) < SOURCE_READ_LIMIT:
            records.append(marker)

    def guarded_open(file, *args, **kwargs):
        if not _caller_is_import():
            record(file)
        return original_open(file, *args, **kwargs)

    def guarded_io_open(file, *args, **kwargs):
        if not _caller_is_import():
            record(file)
        return original_io_open(file, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        if not _caller_is_import():
            record(self)
        return original_path_open(self, *args, **kwargs)

    def guarded_read_text(self, *args, **kwargs):
        if not _caller_is_import():
            record(self)
        return original_read_text(self, *args, **kwargs)

    def guarded_read_bytes(self, *args, **kwargs):
        if not _caller_is_import():
            record(self)
        return original_read_bytes(self, *args, **kwargs)

    def guarded_os_open(path, *args, **kwargs):
        if not _caller_is_import():
            record(path)
        return original_os_open(path, *args, **kwargs)

    builtins.open = guarded_open
    io.open = guarded_io_open
    pathlib.Path.open = guarded_path_open
    pathlib.Path.read_text = guarded_read_text
    pathlib.Path.read_bytes = guarded_read_bytes
    os.open = guarded_os_open

    def stop():
        builtins.open = original_open
        io.open = original_io_open
        pathlib.Path.open = original_path_open
        pathlib.Path.read_text = original_read_text
        pathlib.Path.read_bytes = original_read_bytes
        os.open = original_os_open

    return records, stop


def _make_signer(secret, hmac_new, sha256, dumps):
    """Derive the MAC key into a closure and drop the nonce from this frame."""
    key = hmac_new(secret, b"h4-runner-report", sha256).digest()

    def sign(payload):
        body = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac_new(key, body, sha256).hexdigest()

    return sign


def _install_trace(watch, targets=None):
    """Record executed ``(path, line)`` pairs for the watched files and target ranges."""
    executed = set()
    if not watch and not targets:
        return executed, (lambda: None)
    wanted = {}
    ranges = {}
    for path, lines in (watch or {}).items():
        wanted.setdefault(os.path.realpath(str(path)), set()).update(
            int(line) for line in lines)
    for path, spans in (targets or {}).items():
        ranges.setdefault(os.path.realpath(str(path)), []).extend(
            (int(start), int(end)) for start, end in spans)
    cache = {}

    def _real(filename):
        resolved = cache.get(filename)
        if resolved is None:
            resolved = os.path.realpath(filename)
            cache[filename] = resolved
        return resolved

    def _local(frame, event, arg):
        if event == "line":
            filename = _real(frame.f_code.co_filename)
            line = frame.f_lineno
            lines = wanted.get(filename)
            hit = bool(lines and line in lines)
            if not hit:
                for start, end in ranges.get(filename, ()):
                    if start <= line <= end:
                        hit = True
                        break
            if hit and len(executed) < EXECUTED_LIMIT:
                executed.add((filename, line))
        return _local

    def _global(frame, event, arg):
        filename = _real(frame.f_code.co_filename)
        return _local if (filename in wanted or filename in ranges) else None

    sys.settrace(_global)

    def stop():
        sys.settrace(None)

    return executed, stop


def _package_chain(parts):
    """True when every directory component of the dotted name is a package."""
    here = os.getcwd()
    for part in parts[:-1]:
        here = os.path.join(here, part)
        if not os.path.isfile(os.path.join(here, "__init__.py")):
            return False
    return True


def _failed_import(suite):
    """The exception behind an unimportable module, or None.

    ``unittest`` turns a failed import into a ``_FailedTest`` entry instead of raising;
    the parent needs a load-level failure (it maps to ``HIDDEN_TEST_IMPORT_ERROR``), not
    an invented test id.
    """
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            error = _failed_import(test)
            if error is not None:
                return error
        elif type(test).__name__ == "_FailedTest":
            return getattr(test, "_exception", None) or RuntimeError(str(test))
    return None


def _load_path(loader, relative):
    absolute = os.path.abspath(relative)
    if not os.path.isfile(absolute):
        raise FileNotFoundError(relative)
    parts = os.path.splitext(os.path.relpath(absolute, os.getcwd()))[0].split(os.sep)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    dotted = ".".join(parts)
    if _package_chain(parts):
        # Import by hand so a broken module raises here instead of becoming a test.
        module = importlib.import_module(dotted)
    else:
        # A test file outside a package cannot be imported by name; load it by path.
        name = "h4_runner_target_" + re.sub(r"\W", "_", dotted)
        spec = importlib.util.spec_from_file_location(name, absolute)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return loader.loadTestsFromModule(module)


def _load_suite(args):
    loader = unittest.TestLoader()
    if args.discover:
        suite = loader.discover(args.discover, pattern=args.pattern,
                                top_level_dir=args.top)
    else:
        suites = []
        for relative in args.tests:
            suites.append(_load_path(loader, relative))
        if args.ids:
            suites.append(loader.loadTestsFromNames(args.ids))
        suite = unittest.TestSuite(suites)
    error = _failed_import(suite)
    if error is not None:
        raise error
    return suite


def _write_all(fd, data):
    view = memoryview(data)
    while view:
        written = os.write(fd, view)
        view = view[written:]


def _parser():
    parser = argparse.ArgumentParser(
        prog="test_runner.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=(
            "Harness-owned unittest runner for the H4 pilot task package. The verifier "
            "starts this instead of `python -m unittest`, reads one HMAC-signed JSON "
            "line from --result-fd and never trusts stdout for a verdict."),
        epilog=(
            "Parent side (do NOT run `python -m unittest` yourself):\n"
            "  result = taskpack.run_tests_with_runner(\n"
            "      \"/fresh/copy/of/candidate\", \"tests/test_hidden.py\",\n"
            "      secrets.token_hex(32))\n"
            "  accept only if result[\"accepted\"] and every tests[*].outcome == \"pass\"\n"
            "\n"
            "Protocol:\n"
            "  --nonce-fd   pipe carrying {\"nonce\": <hex>, \"watch\": {path: [lines]},\n"
            "               \"targets\": {path: [[first, last]]}}; read and closed before\n"
            "               any package code is imported.\n"
            "  --result-fd  pipe receiving exactly one JSON line:\n"
            "               {version, tests, counts, load_error, load_detail, executed,\n"
            "                source_reads, integrity_violation, nonce_mac}.\n"
            "               nonce_mac = HMAC-SHA256(key, canonical json of the payload\n"
            "               without nonce_mac).\n"
            "\n"
            "Exit status: 0 all collected tests passed (skips allowed); 1 failures,\n"
            "errors, an unimportable test module or an integrity violation; 2 the\n"
            "runner could not do its job and wrote no result -- the parent must treat\n"
            "that as unavailable, not pass."),
    )
    parser.add_argument("--nonce-fd", type=int, required=True)
    parser.add_argument("--result-fd", type=int, required=True)
    parser.add_argument("--tests", action="append", default=[],
                        help="test file relative to the working directory (repeatable)")
    parser.add_argument("--ids", action="append", default=[],
                        help="dotted unittest id (repeatable)")
    parser.add_argument("--discover", help="directory to discover from")
    parser.add_argument("--top", default=".", help="top-level directory for discovery")
    parser.add_argument("--pattern", default="test*.py")
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    handshake = _read_handshake(args.nonce_fd)
    nonce_hex = handshake["nonce"]
    watch = dict(handshake.get("watch") or {})
    targets = dict(handshake.get("targets") or {})
    del handshake
    nonce = bytes.fromhex(nonce_hex)
    del nonce_hex
    if len(nonce) < NONCE_MIN_BYTES:
        raise ValueError("nonce is too short")

    # Everything the verdict depends on is captured BEFORE any package code is imported.
    dumps = json.dumps
    hmac_new = hmac.new
    sha256 = hashlib.sha256
    write_all = _write_all
    check_integrity = _integrity_violations
    integrity = _integrity_snapshot()
    sign = _make_signer(nonce, hmac_new, sha256, dumps)
    del nonce  # the key lives in the closure; this frame keeps no copy

    # Only now may package code be imported.
    sys.path.insert(0, os.getcwd())
    result = _Result()
    load_error, load_detail = None, ""
    executed = set()
    reads = []
    violations = []
    try:
        suite = None
        executed, stop_trace = _install_trace(watch, targets)
        reads, stop_guard = _install_source_guard(os.getcwd())
        try:
            try:
                suite = _load_suite(args)
            except BaseException as error:  # noqa: BLE001 - an import error is a result
                load_error = type(error).__name__
                load_detail = str(error)[:500]
            if suite is not None:
                suite.run(result)
        finally:
            stop_guard()
            stop_trace()
    finally:
        violations = check_integrity(integrity)
        payload = {
            "version": REPORT_VERSION,
            "tests": [{"id": key, "outcome": result.outcomes[key]}
                      for key in sorted(result.outcomes)],
            "counts": {
                "ran": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "unexpected": len(result.unexpectedSuccesses),
            },
            "load_error": load_error,
            "load_detail": load_detail,
            "executed": [list(item) for item in sorted(executed)],
            "source_reads": sorted(set(reads)),
            "integrity_violation": sorted(violations),
        }
        mac = sign(payload)
        line = dumps(dict(payload, nonce_mac=mac), sort_keys=True,
                     separators=(",", ":")) + "\n"
        write_all(args.result_fd, line.encode("utf-8"))
        del sign
    counts = payload["counts"]
    clean = (not violations and load_error is None and counts["ran"] > 0
             and not counts["failures"] and not counts["errors"])
    # os._exit skips atexit handlers a test module may have installed.
    os._exit(0 if clean else 1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as error:  # noqa: BLE001 - no result line, parent sees exit 2
        sys.stderr.write("test_runner: %s: %s\n" % (type(error).__name__, error))
        os._exit(2)
