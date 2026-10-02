"""Counterexample-driven tests for FIXTURE IDENTITY HYGIENE in test code.

THE INCIDENT THIS PINS
    A committed regression fixture needed a "must fail" home path and spelled
    a real developer's login into the test source. The tip tree was clean and
    every gate passed, because the path was assembled from fragments:

        leak = "/" + "Users" + "/" + "<real login>" + "/must-fail"

    No contiguous literal existed, so the TIER A `UNIX_USER_HOME` rule stayed
    silent. The rule had no username list and needed none; what it lacked was
    any way to see an identity that only exists after concatenation.

WHAT THIS FILE PROVES
    - a fragmented identity resolving to THIS host's real login is REJECTED
    - the same shape naming a synthetic identity is ACCEPTED, on any host
    - ordinary test prose and path concatenation are NOT flagged
    - the judgement is made by comparing against the host, never by matching a
      name from a list, so it holds on a machine it has never seen
    - the rule is scoped to test/fixture code

HERMETIC BY CONSTRUCTION
    These tests never read the developer's own login to decide what should
    fail. They generate a random token, temporarily make it look like the host
    identity, and assert on both sides. The assertions therefore hold on a
    clean CI checkout, on a developer machine, and under any account name; run
    this file under an account whose name is the token and it would still pass.
    That property is what makes it a real test rather than a restatement of
    one machine's configuration.

WHAT THIS FILE DOES NOT PROVE
    That a leak already in git HISTORY is gone. History is `validate_public_release
    .py --history`'s job and is not rewritten by this rule. Nor does it prove the
    host baseline is available: where the host cannot be identified the rule
    deliberately reports nothing rather than guessing.
"""
import importlib.util
import os
import random
import shutil
import string
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts" / "validate_public_release.py"
_spec = importlib.util.spec_from_file_location("public_release", VALIDATOR)
VPR = importlib.util.module_from_spec(_spec)
sys.modules["public_release"] = VPR
_spec.loader.exec_module(VPR)


def _random_login() -> str:
    """A token that cannot collide with this host's real login."""
    while True:
        token = "".join(random.choice(string.ascii_lowercase) for _ in range(14))
        if token not in VPR.host_identity_tokens():
            return token


class FixtureIdentityHygieneTests(unittest.TestCase):
    """The rule itself: a real identity fails, a synthetic one does not."""

    def _scan(self, source: str, path: str = "scripts/tests/fixture_x.py"):
        return VPR.scan_text(path, source)

    def _with_host_identity(self, token: str):
        """Make `token` look like this host's login for the duration."""
        original_getuser = getattr(VPR, "getpass", None)
        saved_user = os.environ.get("USER")
        saved_logname = os.environ.get("LOGNAME")
        saved_home = os.environ.get("HOME")
        os.environ["USER"] = token
        os.environ["LOGNAME"] = token
        os.environ["HOME"] = f"/home/{token}"
        self.addCleanup(self._restore_host, token,
                        original_getuser, saved_user, saved_logname, saved_home)

    def _restore_host(self, token, original_getuser, saved_user,
                      saved_logname, saved_home):
        for key, value in (("USER", saved_user), ("LOGNAME", saved_logname),
                           ("HOME", saved_home)):
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        if original_getuser is not None:
            import getpass

            getpass.getuser = original_getuser

    # -- 1. a real identity must fail ------------------------------------
    def test_fragmented_real_login_is_rejected(self):
        token = _random_login()
        self._with_host_identity(token)
        source = ('leak = "/" + "Users" + "/" + "' + token +
                  '" + "/must-fail"\n')
        rules = [v.rule for v in self._scan(source)]
        self.assertIn("FRAGMENTED_LOCAL_IDENTITY", rules,
                      "a fragmented path naming this host's real login must "
                      "be rejected")

    def test_fragmented_real_login_is_rejected_on_windows_shape(self):
        token = _random_login()
        self._with_host_identity(token)
        source = 'p = "C" + ":" + "\\\\Users\\\\" + "' + token + '"\n'
        rules = [v.rule for v in self._scan(source)]
        self.assertIn("FRAGMENTED_LOCAL_IDENTITY", rules,
                      "the Windows shape of the same evasion must also fail")

    # -- 2. a synthetic identity must pass --------------------------------
    def test_fragmented_synthetic_identity_is_accepted(self):
        source = 'leak = "/" + "Users" + "/" + "fixture-user"\n'
        self.assertEqual([], self._scan(source))

    def test_synthetic_windows_shape_is_accepted(self):
        source = 'p = "C" + ":" + "\\\\Users\\\\" + "fixture-user"\n'
        self.assertEqual([], self._scan(source))

    def test_the_validator_own_synthetic_selftest_style_passes(self):
        """The pattern this repository already uses must stay legal."""
        source = ('return "/" + "Users" + "/" + "synthlogin" +'
                  ' "/project/x.md"\n')
        self.assertEqual([], self._scan(source))

    # -- 3. ordinary test text must not be flagged ------------------------
    def test_ordinary_prose_concatenation_is_not_flagged(self):
        for source in ('msg = "hello" + " " + "world"\n',
                       'needle("spec_from_" ,"file_location")\n',
                       'p = "/usr/local" + "/bin"\n',
                       'label = "gate" + "_" + "id"\n'):
            with self.subTest(source=source):
                self.assertEqual([], self._scan(source))

    def test_placeholder_form_is_not_flagged(self):
        source = 'p = "/Users/<LOCAL_OS_USERNAME>/x"\n'
        self.assertEqual([], self._scan(source))

    def test_generated_runtime_string_is_not_flagged(self):
        source = 'p = "/Users/" + get_login() + "/x"\n'
        self.assertEqual([], self._scan(source))

    # -- 4. the rule is host-relative, not a name list --------------------
    def test_rule_is_not_a_name_list(self):
        """Two different hosts must each reject only their own identity."""
        first, second = _random_login(), _random_login()
        source_for = lambda t: ('leak = "/" + "Users" + "/" + "' + t + '"\n')

        self._with_host_identity(first)
        self.assertIn("FRAGMENTED_LOCAL_IDENTITY",
                      [v.rule for v in self._scan(source_for(first))])
        # The other token is, by construction, not this host's login.
        self.assertEqual([], self._scan(source_for(second)))

    def test_unidentifiable_host_reports_nothing_rather_than_guessing(self):
        """No host signal -> no verdict, never a false accusation."""
        token = _random_login()
        self._with_host_identity(token)
        original = VPR.host_identity_tokens
        VPR.host_identity_tokens = lambda: set()
        self.addCleanup(setattr, VPR, "host_identity_tokens", original)
        source = 'leak = "/" + "Users" + "/" + "' + token + '"\n'
        self.assertEqual([], self._scan(source))

    # -- 5. scope is test/fixture code -----------------------------------
    def test_scope_covers_both_test_trees(self):
        token = _random_login()
        self._with_host_identity(token)
        source = 'leak = "/" + "Users" + "/" + "' + token + '"\n'
        for path in ("scripts/tests/x.py", "adapters/zcode/tests/x.py",
                     "adapters/workbuddy/tests/x.py"):
            with self.subTest(path=path):
                self.assertIn("FRAGMENTED_LOCAL_IDENTITY",
                              [v.rule for v in self._scan(source, path)])

    def test_rule_is_scoped_outside_test_code(self):
        """Production paths keep to the pre-existing contiguous rules."""
        token = _random_login()
        self._with_host_identity(token)
        source = 'leak = "/" + "Users" + "/" + "' + token + '"\n'
        self.assertEqual([], self._scan(source, "scripts/validate_x.py"))

    # -- 6. nothing about the host leaks into the artefact ----------------
    def test_violation_excerpt_never_carries_the_real_login(self):
        token = _random_login()
        self._with_host_identity(token)
        source = 'leak = "/" + "Users" + "/" + "' + token + '"\n'
        for violation in self._scan(source):
            self.assertNotIn(token, violation.excerpt)
            self.assertNotIn(token, violation.render())

    def test_host_baseline_is_not_printed(self):
        self.assertNotIn(str(VPR.host_identity_tokens()),
                         "".join(str(v) for v in VPR.TIER_A_PATTERNS))


class FixtureIdentityRealCliTests(unittest.TestCase):
    """SEAM: the real CLI, on a real tree, must actually fail.

    The CLI takes no tree argument -- it always scans its own ROOT -- so these
    tests drive it the only way that is honest: they materialise the fixture
    INSIDE a throwaway copy of the repository and run the gate there. Pointing
    the validator at an unrelated temporary directory would silently scan the
    wrong tree and pass for the wrong reason.
    """

    def _gate_in(self, mutate) -> subprocess.CompletedProcess:
        """Run the real gate over a throwaway copy of THIS working tree.

        A clone would carry only committed content, so the working-tree
        validator is copied in as well -- otherwise the gate under test would
        be the previous revision and the assertions would pass for the wrong
        reason.
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            subprocess.run(["git", "clone", "--quiet", "--no-hardlinks",
                            str(ROOT), str(root)], check=True,
                           capture_output=True)
            shutil.copy2(VALIDATOR, root / "scripts" / "validate_public_release.py")
            mutate(root)
            return subprocess.run(
                [sys.executable,
                 str(root / "scripts" / "validate_public_release.py")],
                capture_output=True, text=True, cwd=str(root),
                env={**os.environ, "PUBLIC_RELEASE": "1"})

    def _as_host(self, token: str) -> None:
        saved = {k: os.environ.get(k) for k in ("USER", "LOGNAME")}
        os.environ["USER"] = token
        os.environ["LOGNAME"] = token

        def restore():
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.addCleanup(restore)

    def test_real_cli_fails_a_repo_whose_fixture_carries_the_real_login(self):
        token = _random_login()
        self._as_host(token)

        def mutate(root: Path) -> None:
            target = root / "scripts" / "tests" / "zz_fixture_probe.py"
            target.write_text(
                'leak = "/" + "Users" + "/" + "' + token + '"\n',
                encoding="utf-8")

        proc = self._gate_in(mutate)
        self.assertNotEqual(
            0, proc.returncode,
            "the real gate must FAIL when a committed fixture spells this "
            "host's login, however it is fragmented")

    def test_real_cli_accepts_a_synthetic_fixture(self):
        def mutate(root: Path) -> None:
            target = root / "scripts" / "tests" / "zz_fixture_probe.py"
            target.write_text(
                'leak = "/" + "Users" + "/" + "fixture-user"\n',
                encoding="utf-8")

        proc = self._gate_in(mutate)
        self.assertEqual(0, proc.returncode, proc.stdout[-500:])

    def test_real_cli_still_fails_a_contiguous_real_login(self):
        """The pre-existing rule keeps working; this change only adds one."""
        token = _random_login()
        self._as_host(token)

        def mutate(root: Path) -> None:
            target = root / "scripts" / "tests" / "zz_fixture_probe.py"
            target.write_text(
                'leak = "/Users/' + token + '/must-fail"\n', encoding="utf-8")

        proc = self._gate_in(mutate)
        self.assertNotEqual(0, proc.returncode)