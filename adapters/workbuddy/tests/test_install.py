#!/usr/bin/env python3
"""Tests for install.py: idempotency, conflict stop, backup and rollback.

Run:  python3 -m unittest discover -s adapters/workbuddy/tests

Every test points WORKBUDDY_CONFIG_DIR at a throwaway directory. The real user
configuration is never read or written.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

INSTALL_PATH = Path(__file__).resolve().parents[1] / "install.py"
HOOK_PATH = Path(__file__).resolve().parents[1] / "hooks" / "git_safety_guard.py"

_spec = importlib.util.spec_from_file_location("workbuddy_install", INSTALL_PATH)
assert _spec and _spec.loader
install = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install)


class InstallerHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="workbuddy-adapter-test-")
        self._saved_env = os.environ.get("WORKBUDDY_CONFIG_DIR")
        os.environ["WORKBUDDY_CONFIG_DIR"] = self.tmp
        self.settings = Path(self.tmp) / "settings.json"

    def tearDown(self):
        if self._saved_env is None:
            os.environ.pop("WORKBUDDY_CONFIG_DIR", None)
        else:
            os.environ["WORKBUDDY_CONFIG_DIR"] = self._saved_env
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_action(self, action: str) -> int:
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = install.main([action])
        self.last_output = buffer.getvalue()
        return code

    def read_settings(self) -> dict:
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def write_settings(self, data: dict) -> None:
        self.settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def hook_entries(self, data: dict) -> list:
        return (data.get("hooks") or {}).get("PreToolUse") or []


class InstallIdempotency(InstallerHarness):
    def test_install_on_empty_config_creates_one_registration(self):
        self.assertEqual(self.run_action("install"), install.EXIT_OK)
        data = self.read_settings()
        entries = self.hook_entries(data)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["matcher"], "Bash")
        self.assertIn(install.GUARD_ID, entries[0]["hooks"][0]["command"])

    def test_installed_hook_matches_the_reviewed_source(self):
        self.run_action("install")
        installed = Path(self.tmp) / "hooks" / install.GUARD_ID / "git_safety_guard.py"
        self.assertTrue(installed.is_file())
        self.assertEqual(install.sha256(installed), install.sha256(HOOK_PATH))

    def test_second_install_does_not_duplicate(self):
        self.run_action("install")
        first = self.read_settings()
        self.assertEqual(self.run_action("install"), install.EXIT_OK)
        second = self.read_settings()
        self.assertEqual(len(self.hook_entries(second)), 1)
        self.assertEqual(first, second)
        self.assertIn("settings_changed    = False", self.last_output)

    def test_install_writes_nothing_outside_the_config_dir(self):
        before = set(os.listdir(self.tmp))
        self.run_action("install")
        after = set(os.listdir(self.tmp))
        self.assertTrue(after <= {"settings.json", "hooks", "backups"}, sorted(after - before) + sorted(before))


class InstallConflictStop(InstallerHarness):
    def test_foreign_bash_hook_stops_the_install_and_changes_nothing(self):
        original = {
            "enabledPlugins": {"something@market": True},
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash", "hooks": [{"type": "command", "command": "/usr/local/bin/foreign-guard.sh"}]}
                ]
            },
        }
        self.write_settings(original)
        self.assertEqual(self.run_action("install"), install.EXIT_STOP)
        self.assertIn("LOCAL_HOOK_CONFIGURATION_CONFLICT", self.last_output)
        self.assertEqual(self.read_settings(), original)
        self.assertFalse((Path(self.tmp) / "hooks" / install.GUARD_ID).exists())

    def test_foreign_hook_for_another_tool_is_preserved(self):
        foreign = {"matcher": "Read", "hooks": [{"type": "command", "command": "/usr/local/bin/read-logger.sh"}]}
        self.write_settings({"hooks": {"PreToolUse": [foreign]}})
        self.assertEqual(self.run_action("install"), install.EXIT_OK)
        entries = self.hook_entries(self.read_settings())
        self.assertEqual(len(entries), 2)
        self.assertIn(foreign, entries)

    def test_unrelated_settings_keys_are_preserved(self):
        self.write_settings({"enabledPlugins": {"a@b": True}, "sandbox": {"x": 1}})
        self.run_action("install")
        data = self.read_settings()
        self.assertEqual(data["enabledPlugins"], {"a@b": True})
        self.assertEqual(data["sandbox"], {"x": 1})


class VerifyAndRollback(InstallerHarness):
    def test_verify_passes_after_install(self):
        self.run_action("install")
        self.assertEqual(self.run_action("verify"), install.EXIT_OK)

    def test_verify_fails_when_hook_file_is_removed(self):
        self.run_action("install")
        installed = Path(self.tmp) / "hooks" / install.GUARD_ID / "git_safety_guard.py"
        installed.unlink()
        self.assertEqual(self.run_action("verify"), install.EXIT_FAIL)

    def test_rollback_restores_a_pre_existing_settings_file(self):
        original = {"enabledPlugins": {"keep@me": True}}
        self.write_settings(original)
        self.run_action("install")
        self.assertIn("hooks", self.read_settings())
        self.assertEqual(self.run_action("rollback"), install.EXIT_OK)
        self.assertEqual(self.read_settings(), original)

    def test_rollback_removes_a_settings_file_it_created(self):
        self.assertFalse(self.settings.exists())
        self.run_action("install")
        self.assertTrue(self.settings.exists())
        self.assertEqual(self.run_action("rollback"), install.EXIT_OK)
        self.assertFalse(self.settings.exists(), "rollback must restore the no-file pre-state")

    def test_rollback_removes_the_installed_hook_directory(self):
        self.run_action("install")
        self.run_action("rollback")
        self.assertFalse((Path(self.tmp) / "hooks" / install.GUARD_ID).exists())

    def test_verify_reports_failure_after_rollback(self):
        self.run_action("install")
        self.run_action("rollback")
        self.assertEqual(self.run_action("verify"), install.EXIT_FAIL)

    def test_backup_lives_outside_any_repository_and_is_digested(self):
        self.write_settings({"already": "there"})
        self.run_action("install")
        backups = sorted((Path(self.tmp) / "backups" / install.GUARD_ID).glob("settings.json.*.bak"))
        self.assertEqual(len(backups), 1)
        digest_file = backups[0].with_suffix(".bak.sha256")
        self.assertEqual(digest_file.read_text(encoding="utf-8").strip(), install.sha256(backups[0]))


if __name__ == "__main__":
    unittest.main()
