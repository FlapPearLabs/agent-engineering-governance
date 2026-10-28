import importlib.util
import json
import tempfile
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

FZ = Path(__file__).resolve().parents[1] / "h2-lazy-disclosure" / "freeze-v3"
sys.path.insert(0, str(FZ))
spec = importlib.util.spec_from_file_location("auditfix_access", FZ / "access_audit.py")
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)


class AuditFixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.run = self.base / "run"
        self.run.mkdir()
        self.target = self.base / "transient"
        self.target.write_text("actual content\n")
        self.events = self.base / "events.jsonl"
        self.window = ("2026-10-28T10:00:00+00:00", "2026-10-28T10:01:00+00:00")

    def check(self, tool, inputs, state, records=(), **kwargs):
        event = {"type": "tool_use", "part": {"tool": tool, "state": {"input": inputs, **state}}}
        self.events.write_text(json.dumps(event) + "\n")
        with patch.object(audit_module, "allowed_roots", return_value=()):
            return audit_module.audit(self.events, self.run, violations=records, **kwargs)

    def denial(self, operation, **extra):
        return {"operation": operation, "path": str(self.target), "pid": 123,
                "ts": "2026-10-28T10:00:30+00:00", **extra}

    def test_successful_read_with_same_path_write_denial_is_invalid(self):
        result = self.check("read", {"filePath": str(self.target)},
                            {"status": "completed", "output": self.target.read_text()},
                            [self.denial("file-write-data")], launch_window=self.window)
        self.assertEqual("INVALID", result["verdict"])
        self.assertEqual("POSSIBLE_SUCCESS", result["hits"][0]["class"])

    def test_read_then_delete_is_invalid(self):
        output = self.target.read_text()
        self.target.unlink()
        result = self.check("shell", {"command": f"cat {self.target}"},
                            {"status": "completed", "output": output})
        self.assertEqual("INVALID", result["verdict"])
        self.assertEqual("POSSIBLE_SUCCESS", result["hits"][0]["class"])

    def test_matching_denied_read_in_window(self):
        record = self.denial("file-read-data")
        result = self.check("read", {"filePath": str(self.target)}, {"status": "error"},
                            [record], launch_window=self.window)
        self.assertEqual("PASS", result["verdict"])
        self.assertEqual("VIOLATION_LOG", result["denied_attempts"][0]["policy"])
        self.assertEqual(record, result["sandbox_violations"][0])

    def test_nonexistent_with_error_is_denied(self):
        self.target.unlink()
        result = self.check("read", {"filePath": str(self.target)}, {"status": "error"})
        self.assertEqual("PASS", result["verdict"])
        self.assertEqual("PATH_DOES_NOT_EXIST", result["denied_attempts"][0]["policy"])

    def test_wrong_kind_missing_or_outside_window_cannot_confirm(self):
        for record, window in ((self.denial("file-write-data"), self.window),
                               (self.denial("file-read-data"), None),
                               (self.denial("file-read-data", ts="2026-10-28T10:02:00+00:00"), self.window)):
            with self.subTest(record=record, window=window):
                result = self.check("read", {"path": str(self.target)}, {"status": "error"},
                                    [record], launch_window=window)
                self.assertEqual("INVALID", result["verdict"])

    def test_write_requires_write_denial(self):
        for operation, verdict in (("file-read-data", "INVALID"), ("file-write-data", "PASS")):
            with self.subTest(operation=operation):
                result = self.check("write", {"filePath": str(self.target)}, {"status": "error"},
                                    [self.denial(operation)], launch_window=self.window)
                self.assertEqual(verdict, result["verdict"])

    def test_event_pid_conflict_does_not_confirm(self):
        candidate = {"tool": "read", "resolved": str(self.target)}
        self.assertFalse(audit_module.violation_confirms(
            candidate, [self.denial("file-read-data")], self.window, pid=456))
        self.assertTrue(audit_module.violation_confirms(
            candidate, [self.denial("file-read-data")], self.window, pid=123))

    def test_shell_read_with_same_path_write_denial_is_invalid(self):
        result = self.check("shell", {"command": f"cat {self.target}"},
                            {"status": "completed", "output": self.target.read_text()},
                            [self.denial("file-write-data")], launch_window=self.window)
        self.assertEqual("INVALID", result["verdict"])

    def test_successful_read_cannot_be_overridden_by_matching_denial(self):
        result = self.check("read", {"filePath": str(self.target)},
                            {"status": "completed", "output": self.target.read_text()},
                            [self.denial("file-read-data")], launch_window=self.window)
        self.assertEqual("INVALID", result["verdict"])
