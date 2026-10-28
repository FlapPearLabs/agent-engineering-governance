import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
H2 = ROOT / "experiments/v1.2/h2-lazy-disclosure"
FZ = H2 / "freeze-v3"
SANDBOX_READY = sys.platform == "darwin" and shutil.which("sandbox-exec") is not None


def load(name):
    # Match the v3 suite's isolation from modules previously loaded from v2.
    v2 = (H2 / "freeze-v2").resolve()
    for key, module in list(sys.modules.items()):
        source = getattr(module, "__file__", None)
        if source and Path(source).resolve().is_relative_to(v2):
            del sys.modules[key]
    if str(FZ) in sys.path:
        sys.path.remove(str(FZ))
    sys.path.insert(0, str(FZ))
    spec = importlib.util.spec_from_file_location(name, FZ / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


sandbox = load("sandbox_v2")
driver = load("run_h2r2")
violations = load("violations_v3")


class ParentReadTests(unittest.TestCase):
    """T51e: the parent of a launch is never a `subpath` read grant again."""

    def test_cell_parent_read_is_a_literal_and_only_for_a_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            run = base / ".cells" / "run-a" / "run-a"
            flat = base / "run-b"
            auditor = run / "audit"
            rules = "\n".join(sandbox.allow_rules(run, base / "home"))
            # The cell parent may be listed, but only as a literal: no recursive read of it.
            self.assertIn(f'(allow file-read-data (literal "{run.parent}"))', rules)
            self.assertNotIn(f'(subpath "{run.parent}")', rules)
            self.assertIn(f'(subpath "{run}")', rules)
            flat_rules = "\n".join(sandbox.allow_rules(flat, base / "home"))
            # A flat-layout run dir owns no cell, so its parent (the runs root) is not readable.
            self.assertNotIn(f'(allow file-read-data (literal "{base}"))', flat_rules)
            self.assertNotIn(f'(subpath "{base}")', flat_rules)
            self.assertIn(f'(subpath "{flat}")', flat_rules)
            audit_rules = "\n".join(sandbox.allow_rules(auditor, base / "home"))
            # The auditor sits IN the worker's run dir: it may not read the run dir as a tree.
            self.assertNotIn(f'(subpath "{run}")', audit_rules)
            self.assertNotIn(f'(allow file-read-data (literal "{run}"))', audit_rules)
            self.assertIn(f'(subpath "{auditor}")', audit_rules)

    def test_cell_parent_detection_matches_the_wrapper_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            self.assertEqual(sandbox.cell_parent(base / ".cells" / "r" / "r"), base / ".cells" / "r")
            self.assertIsNone(sandbox.cell_parent(base / "r"))
            self.assertIsNone(sandbox.cell_parent(base / ".cells" / "r" / "r" / "audit"))

    @unittest.skipUnless(SANDBOX_READY, "requires macOS sandbox-exec")
    def test_auditor_cannot_read_the_run_dir_and_a_cell_worker_can_list_its_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            run = base / ".cells" / "run-a" / "run-a"
            auditor = run / "audit"
            home = base / "home"
            auditor.mkdir(parents=True)
            home.mkdir()
            secret = run / "outside-audit.txt"
            secret.write_text("private", encoding="utf-8")
            profile = base / "profile.sb"
            profile.write_text(sandbox.render(auditor, home, sys.executable), encoding="utf-8")
            denied = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile),
                                     "/bin/cat", str(secret)], capture_output=True,
                                    cwd=str(auditor))
            self.assertNotEqual(denied.returncode, 0)
            self.assertNotIn(b"private", denied.stdout)
            profile.write_text(sandbox.render(run, home, sys.executable), encoding="utf-8")
            listing = subprocess.run(["/usr/bin/sandbox-exec", "-f", str(profile),
                                      "/bin/ls", str(run.parent)], capture_output=True,
                                     cwd=str(run))
            self.assertEqual(listing.returncode, 0, listing.stderr)
            self.assertIn(b"run-a", listing.stdout)


class ViolationRecordTests(unittest.TestCase):
    """T51e: per-launch evidence is recorded, hashed, and never blocks the run."""

    def test_path_is_per_launch_under_the_attempt_directory(self):
        base = Path("/tmp/does-not-exist") / ".driver" / "run-a"
        self.assertEqual(driver.violations_path(base, 2, "worker"),
                         base / "attempt-2" / "violations-worker.jsonl")
        self.assertEqual(driver.violations_path(base, 2, "audit-attempt-1"),
                         base / "attempt-2" / "violations-audit-attempt-1.jsonl")

    def test_record_contains_path_count_and_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = driver.violations_path(Path(tmp), 1, "worker")
            seen = {}

            def collect(start, end, pids, output):
                seen.update({"start": start, "end": end, "pids": set(pids)})
                Path(output).write_bytes(b'{"pid": 12}\n')
                return 1

            with mock.patch.object(driver.violations_v3, "collect_violations", side_effect=collect):
                result = driver.violation_record("2026-10-28T10:00:00+00:00",
                                                 "2026-10-28T10:00:05+00:00",
                                                 {11, 12}, path)
            self.assertEqual(result, {"path": str(path), "count": 1,
                                      "sha256": hashlib.sha256(b'{"pid": 12}\n').hexdigest()})
            self.assertTrue(path.is_file())
            self.assertEqual(seen["pids"], {11, 12})
            self.assertEqual(seen["start"], "2026-10-28T10:00:00+00:00")

    def test_empty_collection_is_hashed_not_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = driver.violations_path(Path(tmp), 1, "audit")
            with mock.patch.object(driver.violations_v3, "collect_violations",
                                   side_effect=lambda *a: (Path(a[3]).write_text(""), 0)[1]):
                result = driver.violation_record("a", "b", {1}, path)
            self.assertEqual(result["count"], 0)
            self.assertEqual(result["sha256"], hashlib.sha256(b"").hexdigest())

    def test_collector_failure_is_recorded_and_non_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = driver.violations_path(Path(tmp), 1, "worker")
            with mock.patch.object(driver.violations_v3, "collect_violations",
                                   side_effect=RuntimeError("log show failed")):
                result = driver.violation_record("a", "b", {1}, path)
        self.assertEqual(result["error"], "RuntimeError")
        self.assertIn("log show failed", result["reason"])

    def test_unwritable_path_is_recorded_and_non_fatal(self):
        with tempfile.TemporaryDirectory() as tmp:
            blocked = Path(tmp) / "file"
            blocked.write_text("not a directory", encoding="utf-8")
            result = driver.violation_record("a", "b", {1},
                                             blocked / "attempt-1" / "violations-x.jsonl")
        self.assertIn("error", result)


class PidSetTests(unittest.TestCase):
    """T51e: the pid set is the launched pids plus every pid the driver observed."""

    def test_serve_worker_group_and_sweep_pids_are_all_counted(self):
        sweep = {"group_members": [7, 8], "lingering_processes": [{"pid": 9}],
                 "killed": [{"pid": 10}], "survivors": [{"pid": 11, "reason": "EPERM"}]}
        prepared = {"observed_pids": {5}}                 # the launch's `opencode serve`
        launched = {"pid": 6, "observed_pids": [6]}       # the confined client
        self.assertEqual(driver.pid_set(launched, prepared, sweep, [12], None),
                         {5, 6, 7, 8, 9, 10, 11, 12})

    def test_ignores_junk_entries(self):
        self.assertEqual(driver.pid_set([None, "x", 3], {"killed": [{"command": "no pid"}]}), {3})

    def test_launch_returns_the_pid_it_observed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            result = driver.launch(["/bin/sh", "-c", "sleep 0.4; exit 3"], base,
                                   dict(os.environ), 30,
                                   base / "out.txt", base / "err.txt")
        self.assertEqual(result["returncode"], 3)
        self.assertEqual(result["process_group"], result["pid"])
        self.assertIn(result["pid"], result["observed_pids"])


class CollectorTests(unittest.TestCase):
    def test_log_timestamps_are_normalised_to_the_measured_spelling(self):
        import datetime
        moment = datetime.datetime(2026, 10, 28, 10, 0, 0,
                                   tzinfo=datetime.timezone.utc)
        self.assertEqual(violations.stamp(moment), moment.astimezone().strftime(
            violations.LOG_FORMAT))
        self.assertRegex(violations.stamp("2026-10-28T10:00:00+00:00"),
                         r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d[+-]\d{4}$")
        self.assertRegex(violations.stamp(), r"^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d[+-]\d{4}$")
        # A value the test fixture already spelled is passed through, never silently dropped.
        self.assertEqual(violations.stamp("not a time"), "not a time")

    def test_parsed_records_stay_jsonl(self):
        entry = json.dumps({"timestamp": "now", "eventMessage":
                            "Sandbox: cat(42) deny(1) file-read-data /secret"})
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "violations.jsonl"
            with mock.patch.object(violations.subprocess, "run") as run:
                run.return_value.stdout = entry
                self.assertEqual(violations.collect_violations("a", "b", {42}, out), 1)
            self.assertEqual(json.loads(out.read_text())["operation"], "file-read-data")


if __name__ == "__main__":
    unittest.main()
