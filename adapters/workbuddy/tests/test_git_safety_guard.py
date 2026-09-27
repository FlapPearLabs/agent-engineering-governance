#!/usr/bin/env python3
"""Deterministic tests for the WorkBuddy PreToolUse git safety guard.

Run:  python3 -m unittest discover -s adapters/workbuddy/tests

No network, no repository, no subprocess: everything is exercised through the module's
pure decision surface plus the real stdin/stdout contract of main().
"""

from __future__ import annotations

import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parents[1] / "hooks" / "git_safety_guard.py"

_spec = importlib.util.spec_from_file_location("workbuddy_git_safety_guard", HOOK_PATH)
assert _spec and _spec.loader
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)


def payload(command: str, tool: str = "Bash", event: str = "PreToolUse") -> dict:
    return {
        "hook_event_name": event,
        "tool_name": tool,
        "tool_input": {"command": command},
    }


class DenyMatrix(unittest.TestCase):
    """Forms the governance hard invariants already prohibit outright."""

    DENIED = [
        "git push --force",
        "git push --force origin master",
        "git push -f origin master",
        "git push origin master -f",
        "git push --force-with-lease origin feature",
        "git push --force-with-lease=origin/feature origin feature",
        "git push --force-if-includes origin feature",
        "git -C /tmp/somewhere push -f origin master",
        "git --git-dir=/tmp/repo/.git push --force",
        "cd /tmp/x && git push -f origin master",
        "git status && git push -f",
        "git push -f | cat",
        "git reset --hard",
        "git reset --hard HEAD~3",
        "git -C /tmp/x reset --hard",
        "true; git reset --hard origin/master",
        "git clean -fd",
        "git clean -df",
        "git clean -fdx",
        "git clean -f",
        "git clean --force",
        "git clean -f -d",
        "git clean -xfd",
    ]

    def test_denied_forms_are_classified(self):
        for command in self.DENIED:
            with self.subTest(command=command):
                self.assertIsNotNone(guard.classify(command), f"expected DENY: {command!r}")

    def test_denied_categories_are_stable_ids(self):
        self.assertEqual(guard.classify("git push -f"), guard.CATEGORY_PUSH_FORCE)
        self.assertEqual(guard.classify("git reset --hard"), guard.CATEGORY_RESET_HARD)
        self.assertEqual(guard.classify("git clean -fd"), guard.CATEGORY_CLEAN_FORCE)


class AllowMatrix(unittest.TestCase):
    """Ordinary and state-dependent commands must never be blocked."""

    ALLOWED = [
        "git status",
        "git status --short",
        "git fetch origin",
        "git branch -a",
        "git log --oneline -n 5",
        "git diff --check",
        "git push origin master",
        "git push -u origin feature",
        "git push --set-upstream origin feature",
        "git push --tags",
        "git rebase main",
        "git rebase -i HEAD~3",
        "git commit --amend --no-edit",
        "git reset --soft HEAD~1",
        "git reset HEAD -- file.txt",
        "git reset",
        "git clean -n",
        "git clean -nd",
        "git clean --dry-run",
        "git clean --dry-run -fd",
        "git clean -X",
        "git clean -e '*.log' -n",
        "ls -la",
        "rm -rf /tmp/scratch",
        "git push --follow-tags origin master",
        "git push --dry-run origin master",
        "git log --grep=force -n 5",
    ]

    def test_allowed_forms_pass(self):
        for command in self.ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(guard.classify(command), f"expected ALLOW: {command!r}")

    def test_quoted_and_unquoted_denied_forms_agree(self):
        """Same semantic command must not get two verdicts because of quoting.

        Deliberate fail-closed consequence: a command that merely prints a prohibited
        form is denied as well. Recorded here so the trade-off is not read as an accident.
        """
        pairs = [
            ("git push -f origin master", "bash -c 'git push -f origin master'"),
            ("echo git push -f", "echo 'git push -f'"),
            ("git reset --hard", 'sh -c "git reset --hard"'),
        ]
        for plain, wrapped in pairs:
            with self.subTest(plain=plain, wrapped=wrapped):
                self.assertIsNotNone(guard.classify(plain))
                self.assertIsNotNone(guard.classify(wrapped))

    def test_wrapper_payloads_are_analysed(self):
        for command in [
            "bash -c 'git push --force origin master'",
            'sh -c "git reset --hard"',
            "zsh -c 'git clean -fd'",
            "sudo -u someone git push -f origin master",
        ]:
            with self.subTest(command=command):
                self.assertIsNotNone(guard.classify(command), f"expected DENY: {command!r}")

    def test_recursion_is_bounded(self):
        """Pathological nesting must terminate, not recurse without bound."""
        nested = "echo '" * 40 + "git push -f" + "'" * 40
        guard.classify(nested)  # must return, not raise or hang


class PayloadGating(unittest.TestCase):
    def test_non_pretooluse_event_is_ignored(self):
        self.assertIsNone(guard.decide(payload("git push -f", event="PostToolUse")))

    def test_non_bash_tool_is_ignored(self):
        self.assertIsNone(guard.decide(payload("git push -f", tool="Edit")))
        self.assertIsNone(
            guard.decide({"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {"content": "git push -f"}})
        )

    def test_missing_or_empty_command_is_ignored(self):
        self.assertIsNone(guard.decide({"hook_event_name": "PreToolUse", "tool_name": "Bash"}))
        self.assertIsNone(guard.decide(payload("   ")))

    def test_malformed_payload_is_ignored(self):
        self.assertIsNone(guard.decide(None))
        self.assertIsNone(guard.decide("git push -f"))
        self.assertIsNone(guard.decide({}))

    def test_deny_applies_through_the_payload_surface(self):
        self.assertEqual(guard.decide(payload("git push -f origin master")), guard.CATEGORY_PUSH_FORCE)


class DenialPayload(unittest.TestCase):
    def test_denial_payload_shape(self):
        body = guard._denial_payload(guard.CATEGORY_PUSH_FORCE)
        self.assertIn("hookSpecificOutput", body)
        self.assertEqual(body["hookSpecificOutput"]["hookEventName"], "PreToolUse")
        self.assertEqual(body["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("reason", body)

    def test_denial_never_echoes_the_command(self):
        """A denial must not become a leak path for command content."""
        secret = "SUPER_SECRET_BRANCH_NAME"
        body = guard._denial_payload(guard.CATEGORY_PUSH_FORCE)
        rendered = json.dumps(body)
        self.assertNotIn(secret, rendered)
        self.assertNotIn("git push", rendered)
        self.assertNotIn("--force", rendered)


class MainContract(unittest.TestCase):
    """The real stdin/stdout/exit-code contract."""

    def _run(self, raw: str) -> tuple[int, str, str]:
        stdin, stdout, stderr = sys.stdin, sys.stdout, sys.stderr
        sys.stdin = io.StringIO(raw)
        captured = io.StringIO()
        err = io.StringIO()
        try:
            with redirect_stdout(captured), redirect_stderr_into(err):
                code = guard.main([])
        finally:
            sys.stdin, sys.stdout, sys.stderr = stdin, stdout, stderr
        return code, captured.getvalue(), err.getvalue()

    def test_allow_path_exits_zero_without_output(self):
        code, out, err = self._run(json.dumps(payload("git status")))
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertEqual(err, "")

    def test_deny_path_exits_two_with_decision_json(self):
        code, out, _ = self._run(json.dumps(payload("git push --force")))
        self.assertEqual(code, guard.DENY_EXIT_CODE)
        decision = json.loads(out)
        self.assertEqual(decision["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_empty_stdin_allows(self):
        code, out, _ = self._run("")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")

    def test_internal_error_fails_open_with_diagnostic(self):
        """Documented decision: a crashing guard allows and says so on stderr."""
        code, out, err = self._run("{not valid json")
        self.assertEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("internal error", err)

    def test_selfcheck_mode_passes(self):
        self.assertTrue(guard._selfcheck())


class redirect_stderr_into:
    """Local helper: contextlib.redirect_stderr without importing it twice."""

    def __init__(self, stream):
        self._stream = stream

    def __enter__(self):
        self._saved = sys.stderr
        sys.stderr = self._stream
        return self._stream

    def __exit__(self, *exc):
        sys.stderr = self._saved
        return False


if __name__ == "__main__":
    unittest.main()
