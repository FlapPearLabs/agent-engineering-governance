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
        "git push --mirror origin",
        "git push --mirror",
        "git status && git push --mirror origin",
        "git --config-env=remote.origin.mirror=V push origin",
        "git --config-env remote.origin.mirror=V push origin",
        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.mirror"
        " GIT_CONFIG_VALUE_0=true git push origin",
        # Quoting inside the key. The guard checks TOKENS, which _tokenize has already
        # de-quoted, so `remote."origin".mirror` is seen as the key it really is.
        'git -c remote."origin".mirror=true push origin',
        'git -c remote.or"igin".mirror=true push origin',
        # An unknown value-taking global option must not be able to hide the subcommand.
        "git --attr-source HEAD push -f origin master",
        # Plumbing equivalent of push.
        "git send-pack --force /tmp/origin.git refs/heads/master:refs/heads/master",
        "git -C /tmp/somewhere push -f origin master",
        "git -C /tmp/repo push -f origin master",
        "git --git-dir=/tmp/repo/.git push --force",
        "cd /tmp/x && git push -f origin master",
        "cd /tmp && git push -fu origin master",
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
        "git push --force-if-includes origin master",
        # send-pack WITHOUT a force flag is an ordinary, non-forcing pack operation.
        "git send-pack /tmp/origin.git refs/heads/master:refs/heads/master",
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


class ConfigInjectedForce(unittest.TestCase):
    """Force carried by git config, with no flag token on the command line itself.

    Matched by the CARRIER KEY, not by an enumerated spelling. Rounds 4 and 5 each added one
    injection spelling and each time review found the next one (joined `--config-env`, then its
    space-separated form, then the `GIT_CONFIG_*` block). Measured on git 2.53.0, every one of
    these moved a divergent ref on the remote ("(forced update)").
    """

    DENIED = [
        # -c <key>=<value>
        "git -c remote.origin.mirror=true push origin",
        "git -c remote.origin.mirror=1 push origin",
        "cd /tmp && git -c remote.origin.mirror=true push origin",
        "git -c remote.origin.push=+refs/heads/master:refs/heads/master push origin",
        "git -c remote.origin.push=+master push origin",
        # --config-env, both spellings. Its value token is an ENV VAR NAME, not a value, and
        # the hook cannot see the environment, so the key alone is enough to deny.
        "git --config-env=remote.origin.mirror=V push origin",
        "git --config-env=remote.origin.push=V push origin",
        "git --config-env remote.origin.mirror=V push origin",
        "git --config-env remote.origin.push=V push origin",
        # GIT_CONFIG_COUNT / KEY_n / VALUE_n - config injection through the environment.
        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.mirror"
        " GIT_CONFIG_VALUE_0=true git push origin",
        "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.origin.push"
        " GIT_CONFIG_VALUE_0=+refs/heads/master:refs/heads/master git push origin",
        # Not a git option (git 2.53.0: "unknown option: --config="). Denied anyway, because
        # the rule is spelling-independent.
        "git --config=remote.origin.mirror=true push origin",
        # Nested in a quoted payload, like every other deny rule.
        "bash -c 'git -c remote.origin.mirror=true push origin'",
        # The arity-independent path: the carrier key is detected without needing to locate the
        # subcommand, so `--attr-source` (which swallows `push`) cannot hide it.
        "git --attr-source HEAD -c remote.origin.mirror=true push origin",
        "git --attr-source HEAD -c remote.origin.push=+refs/heads/master:refs/heads/master"
        " push origin",
    ]

    ALLOWED = [
        # A config override that is not a force carrier stays allowed.
        "git -c user.name=someone push origin master",
        "git -c push.force=true push origin master",
        # Naming the key WITHOUT a push is a state change, not a force push. The guard only
        # analyses the command string it is handed - see PersistentStateCarriers.
        "git -c remote.origin.mirror=true status",
        "git config remote.origin.mirror true",
    ]

    def test_config_injected_force_is_denied(self):
        for command in self.DENIED:
            with self.subTest(command=command):
                self.assertEqual(guard.classify(command), guard.CATEGORY_PUSH_FORCE)

    def test_key_without_a_push_is_allowed(self):
        for command in self.ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(guard.classify(command), f"expected ALLOW: {command!r}")


class AcceptedFalsePositives(unittest.TestCase):
    """Fail-closed false positives this guard ACCEPTS, asserted so they stay deliberate.

    Round 6 replaced spelling enumeration with carrier-KEY matching. The price is that a
    command which merely NAMES the key in a push context is denied even when it cannot force.
    Each case below costs one nonsensical command form; a silent force push costs a rewritten
    history. If a future change makes one of these ALLOW again, this test fails and the
    README's trade-off note must be updated with it.
    """

    DENIED_ALTHOUGH_NOT_FORCING = [
        "git -c remote.origin.mirror=false push origin",
        "git -c remote.origin.mirror= push origin",
        "git -c remote.origin.push=refs/heads/master:refs/heads/master push origin",
        "git push origin && git config remote.origin.mirror true",
    ]

    def test_accepted_false_positives_are_denied(self):
        for command in self.DENIED_ALTHOUGH_NOT_FORCING:
            with self.subTest(command=command):
                self.assertEqual(guard.classify(command), guard.CATEGORY_PUSH_FORCE)


class MeasuredNonVectors(unittest.TestCase):
    """Forms an earlier review round denied, which MEASUREMENT showed cannot force.

    `push.force` is not a git config key (`git help --config` lists push.default,
    push.followTags, push.useForceIfIncludes and no push.force) and git honours no
    GIT_PUSH_FORCE / PUSH_FORCE variable. On git 2.53.0 each of these was rejected as
    non-fast-forward with the remote ref unchanged, i.e. they are ordinary safe pushes.

    Round 4 removed the deny rules for them because denying a valid, non-forcing command
    serves no invariant and violates R8. They are asserted ALLOW here so the removal cannot
    be silently reverted and the false-positive surface cannot creep back.
    """

    ALLOWED = [
        "git -c push.force=true push origin master",
        "git -c push.force=1 push origin master",
        "git --config=push.force=true push origin master",
        "GIT_PUSH_FORCE=1 git push origin master",
        "GIT_PUSH_FORCE=true git push origin master",
        "PUSH_FORCE=1 git push origin master",
        "cd /tmp && GIT_PUSH_FORCE=1 git push origin master",
        "export GIT_PUSH_FORCE=1 && git push origin master",
        "export GIT_PUSH_FORCE=1 ; git push origin master",
        "set -a; GIT_PUSH_FORCE=1; set +a; git push origin master",
        "sh -c 'export GIT_PUSH_FORCE=1; git push origin master'",
        "git push origin master GIT_PUSH_FORCE=1",
        "git push origin main # GIT_PUSH_FORCE=1",
        "GIT_PUSH_FORCE=0 git push origin master",
    ]

    def test_fictional_force_carriers_are_not_denied(self):
        for command in self.ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(
                    guard.classify(command),
                    f"expected ALLOW (measured not to force): {command!r}",
                )


class DocumentedNonCoverage(unittest.TestCase):
    """Assert the DISCLOSED boundaries, so a gap cannot silently become an assumption.

    These are not bugs to fix by text analysis: the literal tokens are simply not present
    in the command string. If one of these ever starts being caught, this test fails and
    the README's "known non-coverage" section must be updated with it.
    """

    NOT_CAUGHT = [
        'C="git push -f"; $C',
        "B=git; A='push -f'; $B $A",
        "`git push --force`",
        "$(git push --force)",
        "git push origin +main",
        "./some-renamed-wrapper push -f",
    ]

    def test_disclosed_bypasses_are_indeed_not_caught(self):
        for command in self.NOT_CAUGHT:
            with self.subTest(command=command):
                self.assertIsNone(
                    guard.classify(command),
                    f"{command!r} is now caught - update the README non-coverage section",
                )

    def test_readme_documents_the_non_coverage(self):
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
        self.assertIn("已知未覆盖", readme)
        self.assertIn("shell", readme.lower())
        self.assertIn("+main", readme)
        # Class 3 must be documented and must name the class that asserts it, so the README
        # cannot claim a coverage boundary that no test holds.
        self.assertIn("命令文本之外的载体", readme)
        self.assertIn("PersistentStateCarriers", readme)
        # The long-form config carrier must be documented as covered, not left implicit.
        self.assertIn("--config-env", readme)


class PersistentStateCarriers(unittest.TestCase):
    """Disclosed non-coverage class 3: carriers that live outside the command string.

    The guard reads ONE command string. A carrier installed earlier - written into
    .git/config or ~/.gitconfig, or exported into the session environment before the session
    started - is invisible to it, so both the command that installs the carrier and the later
    push are allowed. Verified by hand: `git config --local remote.origin.mirror true`
    followed by `git push origin` produces a real forced update this guard does not see.

    Asserted so the boundary cannot silently decay from "disclosed" into "assumed", and so the
    README cannot claim an assertion that does not exist.
    """

    NOT_CAUGHT = [
        "git config --local remote.origin.mirror true",
        "git config remote.origin.mirror true",
        "git config remote.origin.push +refs/heads/*:refs/heads/*",
        "git push origin",
        # A config FILE named on the command line, or reached through an include: the carrier
        # lives inside the file, which this guard cannot read. Measured: `git config --local
        # remote.origin.mirror true` followed by `git push origin` is a real forced update.
        "git -c include.path=/tmp/other.cfg push origin",
    ]

    def test_carriers_outside_the_command_string_are_not_caught(self):
        for command in self.NOT_CAUGHT:
            with self.subTest(command=command):
                self.assertIsNone(
                    guard.classify(command),
                    f"{command!r} is now caught - update the README non-coverage section",
                )


class SelfcheckParity(unittest.TestCase):
    """install.py VERIFY runs `--selfcheck`; it must not drift from the tested matrix."""

    def test_selfcheck_deny_is_a_subset_of_the_tested_deny_matrix(self):
        tested = set(DenyMatrix.DENIED) | set(ConfigInjectedForce.DENIED)
        missing = set(guard.SELFCHECK_DENY) - tested
        self.assertEqual(missing, set(), f"selfcheck asserts untested forms: {sorted(missing)}")

    def test_selfcheck_allow_is_a_subset_of_the_tested_allow_matrix(self):
        tested = (
            set(AllowMatrix.ALLOWED)
            | set(ConfigInjectedForce.ALLOWED)
            | set(MeasuredNonVectors.ALLOWED)
        )
        missing = set(guard.SELFCHECK_ALLOW) - tested
        self.assertEqual(missing, set(), f"selfcheck asserts untested forms: {sorted(missing)}")

    def test_selfcheck_deny_and_allow_are_disjoint(self):
        self.assertEqual(set(guard.SELFCHECK_DENY) & set(guard.SELFCHECK_ALLOW), set())


if __name__ == "__main__":
    unittest.main()
