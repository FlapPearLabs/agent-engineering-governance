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

Two processes, and the judging code is not in the package's process (P1-2 round C1)
-------------------------------------------------------------------------------
Package code runs in a CHILD process. The child only emits raw per-test events
(``{"event": "test", "id": ..., "outcome": ...}`` plus one final ``done`` event) on a
pipe. The PARENT -- this process -- never imports package code: it reads the events,
computes the counts and the pass/fail verdict, compares the observed ids with the static
AST set, and signs the report with the nonce. An ordinary ``import __main__`` in the
child therefore reaches the child's ``__main__`` (this module) but there is no
module-level result class or integrity snapshot to replace; the report the parent signs
is built from the events, not from the child's memory.

The child never receives the nonce. It also never receives the result fd: the parent
holds the only write end. Events carry a per-run session token that is handed to the
child on stdin before any package import; the parent ignores events without it, so a
package that guesses the event fd still cannot inject a verdict.

The hidden test is run under a randomised file name (see ``taskpack`` and
``pilot_accept``), and ``pilot_accept`` keeps a must-fail canary in a second fresh child.
A package that forges "pass" only when it sees ``test_hidden.py`` in ``sys.argv`` is
therefore compared against the same test under a different name, and flips to FAIL.

Handshake (parent -> child, on stdin)
-------------------------------------
``{"event_fd": <int>, "session": "<hex>", "watch": {...}, "targets": {...},
"test_files": ["/abs/test_hidden_xxxx.py"]}``. The child reads and closes stdin BEFORE
it inserts the working directory into ``sys.path`` or imports any package code. The nonce
travels on a separate inherited pipe that only the parent reads; it is never passed to the
child, never in ``argv``, never in the environment, and never through a file inside the
package.

``watch`` maps an absolute path to a list of line numbers; the child records which of
those lines execute (``sys.settrace``) while the tests run, so the parent can require the
reference patch to change something that actually runs (P1-2 b). Each record carries a
``from_test`` flag: true when the line ran with the hidden test file as its immediate
caller, so a function that only runs while the module is imported cannot satisfy the
"hidden test calls the patched function" rule (P1-1 c).

While the tests run the child also wraps ``builtins.open``, ``io.open``, ``io.FileIO``,
``io.open_code``, ``pathlib.Path.open``/``read_text``/``read_bytes``, ``os.open``,
``linecache.getlines``/``getline``/``updatecache``, ``inspect.getsource``/
``getsourcelines``/``getsourcefile``, ``importlib`` loader ``get_source``/``get_data``,
``os.popen`` and ``subprocess.Popen``. An open of the project's ``src/`` tree,
``reference.patch`` or a hidden test file made from test code is recorded as
``source_reads``; the import system's own file reads stay allowed because their caller is
``importlib``/``zipimport`` (P1-1 a). The guard is a cheap secondary defence: the primary
defence against a source-reading fake fix is the structural patch rule in ``taskpack``.

Result (parent -> verifier)
---------------------------
Exactly one JSON line is written to the result fd::

    {"version": 1,
     "tests": [{"id": "Class.method", "outcome": "pass|failure|error|skip|..."}],
     "counts": {"ran": 0, "failures": 0, "errors": 0, "skipped": 0, "unexpected": 0},
     "load_error": null, "load_detail": "",
     "executed": [["/abs/path.py", 12, 1]],
     "source_reads": ["src/example.py"],
     "integrity_violation": ["unittest.TestCase.assertEqual"],
     "id_set_mismatch": false, "id_set_detail": "",
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
import ast
import builtins
import hashlib
import hmac
import importlib.machinery
import importlib.util
import inspect
import io
import json
import linecache
import marshal
import os
import pathlib
import re
import shlex
import subprocess
import sys
import types
import unittest

REPORT_VERSION = 1
NONCE_MIN_BYTES = 16
HANDSHAKE_LIMIT = 1 << 20
EXECUTED_LIMIT = 20000
RESULT_LIMIT = 1 << 20
SOURCE_READ_LIMIT = 200
EVENT_LIMIT = 1 << 20


def _canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _test_id(test):
    """``Class.method``; anything that is not a plain case keeps its own string."""
    method = getattr(test, "_testMethodName", None)
    if isinstance(test, unittest.TestCase) and method:
        return "%s.%s" % (type(test).__name__, method)
    return str(test)


def _short_id(value):
    """``module.Class.method`` and ``Class.method`` name the same test."""
    parts = str(value).split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else str(value)


# --- what the test file declares, from the AST only -----------------------------
# The parent compares the events it received with this set, so a child that silently
# skips, hides or invents a test cannot agree with both.

def _static_test_ids(path):
    """Every ``Class.method`` reachable as a unittest case, from ``ast`` alone."""
    ids = set()
    try:
        tree = ast.parse(pathlib.Path(path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return ids
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
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


def _static_expected_ids(args):
    """The id set the parent expects, derived without importing any package code."""
    if args.ids:
        return {str(item) for item in args.ids}
    paths = []
    if args.tests:
        paths = [pathlib.Path(item) for item in args.tests]
    elif args.discover:
        paths = sorted(pathlib.Path(args.discover).rglob(args.pattern))
    ids = set()
    for path in paths:
        if path.is_file():
            ids |= _static_test_ids(path)
    return ids


# --- integrity snapshot (P1-2) --------------------------------------------------
# Cheap detection, not prevention: the child records the identity and code-object hash
# of every interpreter function it relies on BEFORE package code is imported and
# re-checks them after the run. The result class itself is local to the child (never a
# module global), so ``import __main__`` cannot reach it.

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


_INTERNAL_MODULES = ("importlib", "zipimport", "linecache", "traceback", "inspect",
                     "unittest", "pkgutil")


def _caller_is_harness_internal():
    """True when the *immediate* caller is an interpreter module, not test code.

    Only the immediate caller is inspected: a test method always has ``unittest`` frames
    higher up the stack, so walking the whole stack would exempt every test read.
    """
    frame = sys._getframe(2)
    if frame is None:
        return False
    module = frame.f_globals.get("__name__", "")
    filename = frame.f_code.co_filename or ""
    return (module == "zipimport" or module.startswith(_INTERNAL_MODULES)
            or "importlib" in filename or "zipimport" in filename)


def _install_source_guard(repo_root):
    """Record test-code reads of ``src/``, ``reference.patch`` and hidden files.

    The guard is installed only around the test load/run and removed afterwards. It never
    blocks a read; it records one, because the parent -- not this process -- decides what
    a record means. The import system is exempt: its caller is ``importlib`` or
    ``zipimport``, otherwise every module import would be recorded.

    Round C1 broadened this from ``open``/``pathlib``/``os.open`` to the ordinary readers
    the acceptance report listed: ``io.FileIO``, ``io.open_code``, ``linecache``,
    ``inspect.getsource*``, the importlib loader ``get_source``/``get_data``, ``os.popen``
    and ``subprocess``. Each route has a test; routes that cannot be hooked cheaply (a
    raw ``os.read`` on an fd opened before the guard, ``mmap``, ``ctypes``) are stated as
    known limits in ``PILOT_SPEC.md`` and are covered by the structural patch rule.
    """
    records = []
    original_open = builtins.open
    original_io_open = io.open
    original_fileio = io.FileIO
    original_open_code = io.open_code
    original_path_open = pathlib.Path.open
    original_read_text = pathlib.Path.read_text
    original_read_bytes = pathlib.Path.read_bytes
    original_os_open = os.open
    original_os_popen = os.popen
    original_getlines = linecache.getlines
    original_getline = linecache.getline
    original_updatecache = linecache.updatecache
    original_getsource = inspect.getsource
    original_getsourcelines = inspect.getsourcelines
    original_getsourcefile = inspect.getsourcefile
    original_loader_get_source = importlib.machinery.SourceFileLoader.get_source
    original_loader_get_data = importlib.machinery.SourceFileLoader.get_data
    original_popen = subprocess.Popen

    def record(path):
        marker = _read_target(path, repo_root)
        if marker and marker not in records and len(records) < SOURCE_READ_LIMIT:
            records.append(marker)

    def record_command(command):
        if isinstance(command, (str, bytes)):
            text = command.decode("utf-8", "replace") if isinstance(command, bytes) else command
            try:
                tokens = shlex.split(text)
            except ValueError:
                tokens = text.split()
        elif isinstance(command, (list, tuple)):
            tokens = [str(item) for item in command]
        else:
            return
        for token in tokens:
            record(token)

    def guarded_open(file, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(file)
        return original_open(file, *args, **kwargs)

    def guarded_io_open(file, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(file)
        return original_io_open(file, *args, **kwargs)

    class GuardedFileIO(original_fileio):
        def __init__(self, file, *args, **kwargs):
            if not _caller_is_harness_internal():
                record(file)
            super().__init__(file, *args, **kwargs)

    def guarded_open_code(path, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(path)
        return original_open_code(path, *args, **kwargs)

    def guarded_path_open(self, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(self)
        return original_path_open(self, *args, **kwargs)

    def guarded_read_text(self, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(self)
        return original_read_text(self, *args, **kwargs)

    def guarded_read_bytes(self, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(self)
        return original_read_bytes(self, *args, **kwargs)

    def guarded_os_open(path, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(path)
        return original_os_open(path, *args, **kwargs)

    def guarded_os_popen(command, *args, **kwargs):
        record_command(command)
        return original_os_popen(command, *args, **kwargs)

    def guarded_getlines(filename, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(filename)
        return original_getlines(filename, *args, **kwargs)

    def guarded_getline(filename, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(filename)
        return original_getline(filename, *args, **kwargs)

    def guarded_updatecache(filename, *args, **kwargs):
        if not _caller_is_harness_internal():
            record(filename)
        return original_updatecache(filename, *args, **kwargs)

    def _object_file(obj):
        if isinstance(obj, types.ModuleType):
            return getattr(obj, "__file__", None)
        try:
            return original_getsourcefile(obj)
        except Exception:  # noqa: BLE001 - not source-backed; nothing to record
            return None

    def guarded_getsource(obj, *args, **kwargs):
        record(_object_file(obj))
        return original_getsource(obj, *args, **kwargs)

    def guarded_getsourcelines(obj, *args, **kwargs):
        record(_object_file(obj))
        return original_getsourcelines(obj, *args, **kwargs)

    def guarded_getsourcefile(obj, *args, **kwargs):
        result = original_getsourcefile(obj, *args, **kwargs)
        record(result)
        return result

    def guarded_loader_get_source(self, fullname):
        if not _caller_is_harness_internal():
            record(getattr(self, "path", None))
        return original_loader_get_source(self, fullname)

    def guarded_loader_get_data(self, path):
        if not _caller_is_harness_internal():
            record(path)
        return original_loader_get_data(self, path)

    class GuardedPopen(original_popen):
        def __init__(self, args, *rest, **kwargs):
            record_command(args)
            super().__init__(args, *rest, **kwargs)

    builtins.open = guarded_open
    io.open = guarded_io_open
    io.FileIO = GuardedFileIO
    io.open_code = guarded_open_code
    pathlib.Path.open = guarded_path_open
    pathlib.Path.read_text = guarded_read_text
    pathlib.Path.read_bytes = guarded_read_bytes
    os.open = guarded_os_open
    os.popen = guarded_os_popen
    linecache.getlines = guarded_getlines
    linecache.getline = guarded_getline
    linecache.updatecache = guarded_updatecache
    inspect.getsource = guarded_getsource
    inspect.getsourcelines = guarded_getsourcelines
    inspect.getsourcefile = guarded_getsourcefile
    importlib.machinery.SourceFileLoader.get_source = guarded_loader_get_source
    importlib.machinery.SourceFileLoader.get_data = guarded_loader_get_data
    subprocess.Popen = GuardedPopen

    def stop():
        builtins.open = original_open
        io.open = original_io_open
        io.FileIO = original_fileio
        io.open_code = original_open_code
        pathlib.Path.open = original_path_open
        pathlib.Path.read_text = original_read_text
        pathlib.Path.read_bytes = original_read_bytes
        os.open = original_os_open
        os.popen = original_os_popen
        linecache.getlines = original_getlines
        linecache.getline = original_getline
        linecache.updatecache = original_updatecache
        inspect.getsource = original_getsource
        inspect.getsourcelines = original_getsourcelines
        inspect.getsourcefile = original_getsourcefile
        importlib.machinery.SourceFileLoader.get_source = original_loader_get_source
        importlib.machinery.SourceFileLoader.get_data = original_loader_get_data
        subprocess.Popen = original_popen

    return records, stop


def _make_signer(secret, hmac_new, sha256, dumps):
    """Derive the MAC key into a closure and drop the nonce from this frame."""
    key = hmac_new(secret, b"h4-runner-report", sha256).digest()

    def sign(payload):
        body = dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac_new(key, body, sha256).hexdigest()

    return sign


def _install_trace(watch, targets=None, test_files=None):
    """Record executed ``(path, line)`` pairs and whether the hidden test was the caller."""
    executed = set()
    from_test = set()
    if not watch and not targets:
        return executed, from_test, (lambda: None)
    wanted = {}
    ranges = {}
    for path, lines in (watch or {}).items():
        wanted.setdefault(os.path.realpath(str(path)), set()).update(
            int(line) for line in lines)
    for path, spans in (targets or {}).items():
        ranges.setdefault(os.path.realpath(str(path)), []).extend(
            (int(start), int(end)) for start, end in spans)
    test_real = {os.path.realpath(str(item)) for item in (test_files or [])}
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
                caller = frame.f_back
                if caller is not None and _real(caller.f_code.co_filename) in test_real:
                    from_test.add((filename, line))
        return _local

    def _global(frame, event, arg):
        filename = _real(frame.f_code.co_filename)
        return _local if (filename in wanted or filename in ranges) else None

    sys.settrace(_global)

    def stop():
        sys.settrace(None)

    return executed, from_test, stop


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


# --- child: the only process that imports package code --------------------------

def _child_main(args):
    """Run the tests and emit raw per-test events. This process never sees the nonce."""
    handshake = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    event_fd = int(handshake["event_fd"])
    session = handshake["session"]
    watch = dict(handshake.get("watch") or {})
    targets = dict(handshake.get("targets") or {})
    test_files = list(handshake.get("test_files") or [])
    del handshake

    dumps = json.dumps
    write_all = _write_all
    install_trace = _install_trace
    install_guard = _install_source_guard
    load_suite = _load_suite
    integrity_snapshot = _integrity_snapshot
    integrity_violations = _integrity_violations
    test_id = _test_id

    def emit(payload):
        payload["session"] = session
        line = dumps(payload, sort_keys=True, separators=(",", ":")) + "\n"
        write_all(event_fd, line.encode("utf-8"))

    integrity = integrity_snapshot()

    # Only now may package code be imported.
    sys.path.insert(0, os.getcwd())

    def record(test, outcome):
        key = test_id(test)
        emit({"event": "test", "id": key, "outcome": outcome})

    class ChildResult(unittest.TestResult):
        """unittest's result object, plus a per-test event the parent can count."""

        def addSuccess(self, test):
            super().addSuccess(test)
            record(test, "pass")

        def addFailure(self, test, err):
            super().addFailure(test, err)
            record(test, "failure")

        def addError(self, test, err):
            super().addError(test, err)
            record(test, "error")

        def addSkip(self, test, reason):
            super().addSkip(test, reason)
            record(test, "skip")

        def addExpectedFailure(self, test, err):
            super().addExpectedFailure(test, err)
            record(test, "expected_failure")

        def addUnexpectedSuccess(self, test):
            super().addUnexpectedSuccess(test)
            record(test, "unexpected_success")

        def addSubTest(self, test, subtest, err):
            super().addSubTest(test, subtest, err)
            if err is not None:
                failure = isinstance(test, unittest.TestCase) and issubclass(
                    err[0], test.failureException)
                record(test, "failure" if failure else "error")

    result = ChildResult()
    load_error, load_detail = None, ""
    executed, from_test, reads = set(), set(), []
    try:
        executed, from_test, stop_trace = install_trace(watch, targets, test_files)
        reads, stop_guard = install_guard(os.getcwd())
        try:
            try:
                suite = load_suite(args)
            except BaseException as error:  # noqa: BLE001 - an import error is a result
                load_error = type(error).__name__
                load_detail = str(error)[:500]
                suite = None
            if suite is not None:
                suite.run(result)
        finally:
            stop_guard()
            stop_trace()
    finally:
        violations = integrity_violations(integrity)
        emit({
            "event": "done",
            "load_error": load_error,
            "load_detail": load_detail,
            "executed": [[path, line, 1 if (path, line) in from_test else 0]
                         for path, line in sorted(executed)],
            "source_reads": sorted(set(reads)),
            "integrity_violation": sorted(violations),
        })
    # os._exit skips atexit handlers a test module may have installed.
    os._exit(0)


# --- parent: judges and signs; never imports package code -----------------------

def _parse_events(raw):
    """Every well-formed event line the child wrote, in order."""
    events = []
    for line in raw.decode("utf-8", "replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and isinstance(event.get("event"), str):
            events.append(event)
    return events


def _parent_main(args):
    handshake = _read_handshake(args.nonce_fd)
    nonce_hex = handshake.get("nonce")
    watch = dict(handshake.get("watch") or {})
    targets = dict(handshake.get("targets") or {})
    del handshake
    nonce = bytes.fromhex(nonce_hex)
    del nonce_hex
    if len(nonce) < NONCE_MIN_BYTES:
        raise ValueError("nonce is too short")

    dumps = json.dumps
    hmac_new = hmac.new
    sha256 = hashlib.sha256
    write_all = _write_all
    sign = _make_signer(nonce, hmac_new, sha256, dumps)
    del nonce

    expected = _static_expected_ids(args)
    test_files = [os.path.abspath(item) for item in args.tests]
    session = os.urandom(16).hex()
    event_read, event_write = os.pipe()
    child = [sys.executable, os.path.abspath(__file__), "--child"]
    for relative in args.tests:
        child.extend(["--tests", relative])
    for item in args.ids:
        child.extend(["--ids", item])
    if args.discover:
        child.extend(["--discover", args.discover, "--top", args.top,
                      "--pattern", args.pattern])
    try:
        process = subprocess.Popen(
            child, cwd=os.getcwd(), stdin=subprocess.PIPE,
            pass_fds=(event_write,), close_fds=True)
    except OSError:
        for fd in (event_read, event_write):
            try:
                os.close(fd)
            except OSError:  # pragma: no cover
                pass
        os._exit(2)
    try:
        handshake_out = _canonical({"event_fd": event_write, "session": session,
                                    "watch": watch, "targets": targets,
                                    "test_files": test_files}).encode("utf-8")
        process.stdin.write(handshake_out)
        process.stdin.close()
    except (OSError, ValueError):  # pragma: no cover - child died immediately
        pass
    os.close(event_write)

    raw = bytearray()
    overflow = False
    try:
        while True:
            try:
                chunk = os.read(event_read, 65536)
            except OSError:  # pragma: no cover - pipe closed under us
                break
            if not chunk:
                break
            raw.extend(chunk)
            if len(raw) > EVENT_LIMIT:
                overflow = True
                try:
                    process.kill()
                except OSError:  # pragma: no cover
                    pass
                break
    finally:
        os.close(event_read)
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:  # pragma: no cover - kill should have landed
        try:
            process.kill()
            process.wait(timeout=10)
        except (OSError, subprocess.TimeoutExpired):
            pass

    if overflow:
        os._exit(2)

    events = [event for event in _parse_events(bytes(raw))
              if event.get("session") == session]
    done = None
    outcomes = {}
    for event in events:
        if event.get("event") == "test":
            test_id, outcome = event.get("id"), event.get("outcome")
            if isinstance(test_id, str) and isinstance(outcome, str):
                outcomes[test_id] = outcome
        elif event.get("event") == "done" and done is None:
            done = event
    if done is None:
        # No child result: the parent must not invent one.
        os._exit(2)

    tests = [{"id": key, "outcome": outcomes[key]} for key in sorted(outcomes)]
    counts = {
        "ran": len(tests),
        "failures": sum(1 for item in tests if item["outcome"] == "failure"),
        "errors": sum(1 for item in tests if item["outcome"] == "error"),
        "skipped": sum(1 for item in tests if item["outcome"] == "skip"),
        "unexpected": sum(1 for item in tests if item["outcome"] == "unexpected_success"),
    }
    observed = {_short_id(item["id"]) for item in tests}
    wanted = {_short_id(item) for item in expected}
    missing, extra = sorted(wanted - observed), sorted(observed - wanted)
    id_mismatch = bool(missing or extra)
    detail = ""
    if id_mismatch:
        detail = "missing=%s extra=%s" % (missing[:5], extra[:5])

    payload = {
        "version": REPORT_VERSION,
        "tests": tests,
        "counts": counts,
        "load_error": done.get("load_error"),
        "load_detail": done.get("load_detail", ""),
        "executed": done.get("executed") or [],
        "source_reads": done.get("source_reads") or [],
        "integrity_violation": done.get("integrity_violation") or [],
        "id_set_mismatch": id_mismatch,
        "id_set_detail": detail,
    }
    mac = sign(payload)
    line = dumps(dict(payload, nonce_mac=mac), sort_keys=True,
                 separators=(",", ":")) + "\n"
    write_all(args.result_fd, line.encode("utf-8"))
    del sign
    clean = (payload["load_error"] is None and counts["ran"] > 0
             and not counts["failures"] and not counts["errors"])
    os._exit(0 if clean else 1)


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
    parser.add_argument("--nonce-fd", type=int, default=None)
    parser.add_argument("--result-fd", type=int, default=None)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
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
    if args.child:
        _child_main(args)
        return 0
    if args.nonce_fd is None or args.result_fd is None:
        raise SystemExit("--nonce-fd and --result-fd are required")
    _parent_main(args)
    return 0


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except BaseException as error:  # noqa: BLE001 - no result line, parent sees exit 2
        sys.stderr.write("test_runner: %s: %s\n" % (type(error).__name__, error))
        os._exit(2)
