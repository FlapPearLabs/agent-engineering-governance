"""Acceptance tests for the H4 pilot task-package verifier (pilot/taskpack.py).

Every rejection case in `PILOT_SPEC.md` "Package verifier" has a test here, plus the
seal contract, the isolation rule (package code runs only in a confined temp copy) and a
regression test for every attack the independent acceptance report filed as a defect or
as too loose (`ACCEPT.md` section 3, rows marked 错 or 松). The good package is built by
hand inside a temporary directory; nothing in this file needs a model, the network, git
history, or a runs root. Tests that can only be meaningful when the package really is
confined skip with an explicit reason when `sandbox-exec` is unavailable -- a skip is
never a pass.
"""
import difflib
import hashlib
import hmac
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / "experiments/v1.2/h4-micro-low-ablation/pilot"
SPEC = importlib.util.spec_from_file_location("h4_taskpack", PILOT / "taskpack.py")
taskpack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(taskpack)

SANDBOX = taskpack.sandbox_available()


def require_sandbox(case):
    """Skip, with the probe's own reason, when confinement cannot be proven here.

    A nested ``sandbox-exec`` (this suite inside an outer sandbox) lands here too: the
    skip reason quotes what the probe printed, so a skip can never be mistaken for a pass.
    """
    if not SANDBOX:
        case.skipTest("sandbox-exec is unavailable (%s): package confinement cannot be "
                      "proven, so this case is not a pass"
                      % taskpack.sandbox_probe_reason())

RUFF_TOML = 'target-version = "py312"\n\n[lint]\nselect = ["E9", "F"]\n'

GOOD_SOURCE = '''"""Small text helpers used by the sample project."""


def word_count(text):
    """Return the number of whitespace-separated words."""
    return len(text.split())


def slugify(text):
    """Turn a title into a lowercase dash-separated slug."""
    lowered = text.lower()
    replaced = "".join(char if char.isalnum() else "-" for char in lowered)
    return replaced
'''

FIXED_SOURCE = '''"""Small text helpers used by the sample project."""


def word_count(text):
    """Return the number of whitespace-separated words."""
    return len(text.split())


def slugify(text):
    """Turn a title into a lowercase dash-separated slug."""
    lowered = text.lower()
    replaced = "".join(char if char.isalnum() else "-" for char in lowered)
    parts = [part for part in replaced.split("-") if part]
    return "-".join(parts)
'''

GOOD_VISIBLE_TESTS = '''import unittest

from src.textutil import slugify, word_count


class TextUtilTests(unittest.TestCase):
    def test_word_count_counts_words(self):
        self.assertEqual(word_count("one two three"), 3)

    def test_slugify_joins_words_with_dashes(self):
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_slugify_lowercases(self):
        self.assertEqual(slugify("Mixed Case"), "mixed-case")


if __name__ == "__main__":
    unittest.main()
'''

GOOD_HIDDEN = '''import unittest

from src.textutil import slugify


class SlugifySeparatorTests(unittest.TestCase):
    def test_collapses_a_run_of_separators(self):
        self.assertEqual(slugify("Hello   World"), "hello-world")

    def test_drops_leading_and_trailing_separators(self):
        self.assertEqual(slugify("  Hello, World!  "), "hello-world")


if __name__ == "__main__":
    unittest.main()
'''

GOOD_HIDDEN_ALREADY_PASSING = '''import unittest

from src.textutil import word_count


class AlreadyGreenTests(unittest.TestCase):
    def test_counts_words(self):
        self.assertEqual(word_count("one two"), 2)

    def test_counts_no_words(self):
        self.assertEqual(word_count("   "), 0)


if __name__ == "__main__":
    unittest.main()
'''

GOOD_STATEMENT = '''# Slug output keeps empty segments

`src/textutil.py` builds a slug by replacing every non-alphanumeric character with a
dash. When the title carries repeated punctuation or surrounding whitespace, the result
keeps empty segments: dashes collapse into runs and the slug can start or end with one.

Change `slugify` so that empty segments are dropped. The returned string must use a
single dash between words and must not begin or end with a dash. Lowercasing must not
change. Leave `word_count` as it is, and keep the existing tests under `tests/` passing.
'''

GOOD_MANIFEST = {
    "task_id": "pilot-good-01",
    "title": "Slug output keeps empty segments",
    "label": "SYNTHETIC_EXPLORATORY",
    "risk": "LOW",
    "language": "python",
    "statement": "statement.md",
    "hidden_test": "hidden/test_hidden.py",
    "hidden_test_dest": "tests/test_hidden.py",
    "reference_patch": "reference.patch",
    "test_command": ["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
    "gate": {"kind": "ruff", "config": "ruff.toml"},
}


def diff(path, old, new):
    return "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                        fromfile="a/" + path, tofile="b/" + path))


def build_package(root, hidden=None, statement=None, base_source=None, fixed_source=None,
                  patches=None, manifest_overrides=None, visible_tests=None):
    """Write one package under root/pkg and return its path."""
    pkg = Path(root) / "pkg"
    base = pkg / "base"
    (base / "src").mkdir(parents=True)
    (base / "tests").mkdir(parents=True)
    (pkg / "hidden").mkdir(parents=True)
    source = GOOD_SOURCE if base_source is None else base_source
    fixed = FIXED_SOURCE if fixed_source is None else fixed_source
    (pkg / "package.json").write_text(
        json.dumps(dict(GOOD_MANIFEST, **(manifest_overrides or {})), indent=2) + "\n")
    (pkg / "statement.md").write_text(GOOD_STATEMENT if statement is None else statement)
    (pkg / "hidden" / "test_hidden.py").write_text(GOOD_HIDDEN if hidden is None else hidden)
    (base / "ruff.toml").write_text(RUFF_TOML)
    (base / "src" / "__init__.py").write_text("")
    (base / "src" / "textutil.py").write_text(source)
    (base / "tests" / "__init__.py").write_text("")
    (base / "tests" / "test_textutil.py").write_text(
        GOOD_VISIBLE_TESTS if visible_tests is None else visible_tests)
    if patches is None:
        patches = [("src/textutil.py", source, fixed)]
    (pkg / "reference.patch").write_text("".join(diff(*item) for item in patches))
    return pkg


def check(verdict, number):
    for item in verdict["checks"]:
        if item["id"] == number:
            return item
    raise AssertionError("check %d missing from %r" % (number, verdict["checks"]))


def reasons(verdict, number):
    return " | ".join(check(verdict, number)["reasons"])


def digest_tree(root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in Path(root).rglob("*") if path.is_file() and not path.is_symlink()}


class GoodPackageTests(unittest.TestCase):
    def test_good_package_is_accepted_then_sealed(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            before = digest_tree(pkg)
            verdict = taskpack.verify_package(pkg, allow_unsandboxed=True)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])
            for number in range(1, 7):
                self.assertEqual(check(verdict, number)["status"], "PASS", reasons(verdict, number))
            self.assertEqual(check(verdict, 7)["status"], "NOT_SEALED")
            self.assertEqual(verdict["seal"], "NOT_SEALED")
            self.assertIs(verdict["sealed"], False)
            self.assertEqual(verdict["isolation"],
                             "SANDBOX_EXEC" if SANDBOX else "NONE")
            self.assertEqual(before, digest_tree(pkg), "verification must not touch the package")

            taskpack.seal_package(pkg)
            seal = json.loads((pkg / "SEAL.json").read_text())
            self.assertEqual(seal["version"], 1)
            self.assertIs(seal["verified"], True)
            self.assertNotIn("SEAL.json", seal["files"])
            for name in ("package.json", "statement.md", "reference.patch",
                         "base/src/textutil.py", "hidden/test_hidden.py"):
                self.assertEqual(seal["files"][name],
                                 hashlib.sha256((pkg / name).read_bytes()).hexdigest())
            taskpack.verify_seal(pkg)

            # Re-verification of a package that already carries a seal is the ONLY caller
            # allowed to accept one; a plain verify refuses it (see SealProvenanceTests).
            sealed = taskpack.verify_package(pkg, allow_unsandboxed=True, allow_reseal=True)
            self.assertEqual(sealed["overall"], "PASS", sealed["reasons"])
            self.assertEqual(sealed["seal"], "SEALED")
            self.assertIs(sealed["sealed"], True)
            self.assertEqual(check(sealed, 7)["status"], "PASS")


class VerifierRejectionTests(unittest.TestCase):
    def assertRejected(self, pkg, number, reason):
        verdict = taskpack.verify_package(pkg)
        self.assertEqual(verdict["overall"], "FAIL", "package was accepted but must be rejected")
        self.assertEqual(check(verdict, number)["status"], "FAIL", reasons(verdict, number))
        self.assertIn(reason, reasons(verdict, number))
        return verdict

    def test_hidden_test_erroring_at_base_is_rejected(self):
        hidden = GOOD_HIDDEN.replace('self.assertEqual(slugify("Hello   World"), "hello-world")',
                                     "self.assertEqual(slugify(None), 0)")
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=hidden)
            self.assertRejected(pkg, 3, "HIDDEN_TEST_ERRORS_AT_BASE")

    def test_hidden_test_import_error_is_rejected(self):
        hidden = GOOD_HIDDEN.replace("from src.textutil import slugify",
                                     "from src.textutil import slugify_tokens")
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=hidden)
            self.assertRejected(pkg, 3, "HIDDEN_TEST_IMPORT_ERROR")

    def test_hidden_test_already_passing_at_base_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=GOOD_HIDDEN_ALREADY_PASSING)
            self.assertRejected(pkg, 3, "HIDDEN_TEST_ALREADY_PASSES_AT_BASE")

    def test_hidden_test_skipping_at_base_is_rejected(self):
        hidden = GOOD_HIDDEN.replace(
            '''    def test_collapses_a_run_of_separators(self):
        self.assertEqual(slugify("Hello   World"), "hello-world")''',
            '''    @unittest.skip("no oracle at base")
    def test_collapses_a_run_of_separators(self):
        self.assertEqual(slugify("Hello   World"), "hello-world")''')
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=hidden)
            self.assertRejected(pkg, 3, "HIDDEN_TEST_SKIPPED_AT_BASE")

    def test_reference_breaking_visible_tests_is_rejected(self):
        broken = FIXED_SOURCE.replace("return len(text.split())",
                                      "return len(text.split()) + 1")
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, fixed_source=broken)
            self.assertRejected(pkg, 4, "VISIBLE_TESTS_BROKEN_BY_PATCH")

    def test_ruff_dirty_reference_is_rejected(self):
        dirty = "import os\n\n" + FIXED_SOURCE
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, fixed_source=dirty)
            self.assertRejected(pkg, 4, "RUFF_DIRTY_AFTER_PATCH")

    def test_reference_not_fixing_the_hidden_test_is_rejected(self):
        cosmetic = GOOD_SOURCE.replace('"""Small text helpers used by the sample project."""',
                                       '"""Small text helpers for the sample project."""')
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, fixed_source=cosmetic)
            self.assertRejected(pkg, 4, "HIDDEN_TEST_FAILS_AFTER_PATCH")

    def test_empty_patch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "reference.patch").write_text("")
            self.assertRejected(pkg, 1, "EMPTY_FILE reference.patch")

    def test_patch_that_does_not_apply_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "reference.patch").write_text(
                "--- a/src/textutil.py\n+++ b/src/textutil.py\n@@ -1 +1 @@\n-nothing here\n+still nothing\n")
            self.assertRejected(pkg, 4, "PATCH_DOES_NOT_APPLY")

    def test_statement_leaking_the_hidden_test_is_rejected(self):
        leaked = GOOD_STATEMENT + (
            '\nThe check is self.assertEqual(slugify("Hello   World"), "hello-world") exactly.\n')
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, statement=leaked)
            self.assertRejected(pkg, 5, "STATEMENT_LEAKS_HIDDEN_TEST")

    def test_statement_mentioning_experiment_terms_is_rejected(self):
        for phrase in ("the first arm of the study", "the governance carrier",
                       "the INJECT control", "the FULL treatment", "the MIN treatment",
                       "watch the hidden test pass"):
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory() as temporary:
                pkg = build_package(temporary, statement=GOOD_STATEMENT + "\n" + phrase + "\n")
                self.assertRejected(pkg, 5, "STATEMENT_MENTIONS_")

    def test_extra_top_level_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "notes.txt").write_text("scratch\n")
            self.assertRejected(pkg, 1, "EXTRA_FILE notes.txt")

    def test_extra_file_in_hidden_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "hidden" / "helper.py").write_text("")
            self.assertRejected(pkg, 1, "EXTRA_FILE hidden/helper.py")

    def test_symlink_anywhere_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            outside = Path(temporary) / "outside.py"
            outside.write_text("X = 1\n")
            (pkg / "base" / "src" / "escape.py").symlink_to(outside)
            self.assertRejected(pkg, 1, "SYMLINK base/src/escape.py")

    def test_missing_required_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "statement.md").unlink()
            self.assertRejected(pkg, 1, "REQUIRED_MISSING statement.md")

    def test_hidden_destination_present_at_base_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "base" / "tests" / "test_hidden.py").write_text("")
            self.assertRejected(pkg, 1, "HIDDEN_TEST_DEST_PRESENT_AT_BASE")

    def test_invalid_package_json_is_rejected_without_raising(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "package.json").write_text("{ not json")
            verdict = taskpack.verify_package(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("PACKAGE_JSON_INVALID", reasons(verdict, 1))
            for number in (2, 3, 4, 5, 6):
                self.assertEqual(check(verdict, number)["status"], "NOT_RUN")

    def test_missing_package_directory_is_rejected_without_raising(self):
        with tempfile.TemporaryDirectory() as temporary:
            verdict = taskpack.verify_package(Path(temporary) / "no-such-package")
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("PACKAGE_MISSING", reasons(verdict, 1))

    def test_wrong_contract_value_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, manifest_overrides={"risk": "MEDIUM"})
            self.assertRejected(pkg, 1, "PACKAGE_JSON_FIELD risk")

    def test_patch_touching_a_test_file_is_rejected(self):
        extra = ("tests/test_textutil.py", GOOD_VISIBLE_TESTS,
                 GOOD_VISIBLE_TESTS + "\n# keep the fixture in sync\n")
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, patches=[("src/textutil.py", GOOD_SOURCE, FIXED_SOURCE), extra])
            self.assertRejected(pkg, 6, "PATCH_TOUCHES_TEST_FILES")

    def test_oversized_patch_is_rejected(self):
        padded = FIXED_SOURCE + "".join("# note line %02d\n" % index for index in range(61))
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, fixed_source=padded)
            self.assertRejected(pkg, 6, "PATCH_TOO_LARGE")

    def test_patch_touching_three_files_is_rejected(self):
        patches = [
            ("src/textutil.py", GOOD_SOURCE, FIXED_SOURCE),
            ("src/__init__.py", "", "# package marker\n"),
            ("ruff.toml", RUFF_TOML, "# keep this small\n" + RUFF_TOML),
        ]
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, patches=patches)
            self.assertRejected(pkg, 6, "PATCH_TOUCHES_TOO_MANY_FILES")

    def test_risk_keyword_in_patch_is_rejected(self):
        keyworded = FIXED_SOURCE.replace('"""Turn a title into a lowercase dash-separated slug."""',
                                         '"""Turn a title into a slug; never store a password."""')
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, fixed_source=keyworded)
            self.assertRejected(pkg, 6, "RISK_KEYWORD_HITS")


class SealTests(unittest.TestCase):
    def sealed_package(self, temporary):
        pkg = build_package(temporary)
        taskpack.seal_package(pkg)
        return pkg

    def test_changed_file_breaks_the_seal(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = self.sealed_package(temporary)
            statement = pkg / "statement.md"
            statement.write_text(statement.read_text() + "\nOne more line.\n")
            with self.assertRaises(taskpack.SealError) as raised:
                taskpack.verify_seal(pkg)
            self.assertIn("changed=", str(raised.exception))
            verdict = taskpack.verify_package(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertEqual(verdict["seal"], "BROKEN")
            self.assertIn("SEAL_BROKEN", reasons(verdict, 7))

    def test_missing_file_breaks_the_seal(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = self.sealed_package(temporary)
            (pkg / "base" / "src" / "__init__.py").unlink()
            with self.assertRaises(taskpack.SealError) as raised:
                taskpack.verify_seal(pkg)
            self.assertIn("missing=", str(raised.exception))

    def test_extra_file_breaks_the_seal(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = self.sealed_package(temporary)
            (pkg / "base" / "src" / "added.py").write_text("X = 1\n")
            with self.assertRaises(taskpack.SealError) as raised:
                taskpack.verify_seal(pkg)
            self.assertIn("extra=", str(raised.exception))

    def test_missing_seal_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            with self.assertRaises(taskpack.SealError):
                taskpack.verify_seal(pkg)

    def test_unverified_seal_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = self.sealed_package(temporary)
            seal = json.loads((pkg / "SEAL.json").read_text())
            seal["verified"] = False
            (pkg / "SEAL.json").write_text(json.dumps(seal))
            with self.assertRaises(taskpack.SealError):
                taskpack.verify_seal(pkg)

    def test_seal_refuses_a_rejected_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=GOOD_HIDDEN_ALREADY_PASSING)
            with self.assertRaises(taskpack.SealError):
                taskpack.seal_package(pkg)
            self.assertFalse((pkg / "SEAL.json").exists())

    def test_seal_refuses_to_overwrite_a_broken_seal(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = self.sealed_package(temporary)
            original = (pkg / "SEAL.json").read_bytes()
            statement = pkg / "statement.md"
            statement.write_text(statement.read_text() + "\nTampered.\n")
            with self.assertRaises(taskpack.SealError):
                taskpack.seal_package(pkg)
            self.assertEqual((pkg / "SEAL.json").read_bytes(), original)


class IsolationTests(unittest.TestCase):
    def test_package_code_runs_only_inside_a_temporary_copy(self):
        writer = GOOD_VISIBLE_TESTS.replace(
            "from src.textutil import slugify, word_count",
            "from pathlib import Path\n\nfrom src.textutil import slugify, word_count").replace(
            "    def test_slugify_lowercases(self):",
            "    def test_writes_in_its_own_working_directory(self):\n"
            "        Path(\"leak.txt\").write_text(\"cwd\")\n"
            "        Path(__file__).with_name(\"leak2.txt\").write_text(\"test dir\")\n\n"
            "    def test_slugify_lowercases(self):")
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=writer)
            before = digest_tree(pkg)
            verdict = taskpack.verify_package(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])
            self.assertEqual(before, digest_tree(pkg))
            self.assertFalse((pkg / "leak.txt").exists())
            self.assertFalse((pkg / "base" / "leak.txt").exists())
            self.assertFalse((pkg / "base" / "tests" / "leak2.txt").exists())
            self.assertFalse(list(pkg.rglob("__pycache__")))

    def test_verifier_copies_the_package_before_running_anything(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            before = digest_tree(pkg)
            taskpack.verify_package(pkg)
            self.assertEqual(before, digest_tree(pkg))


# --- payloads for the attack and isolation regressions below ----------------------
# Everything from here to the end of the file corresponds to the defects the independent
# acceptance report filed (ACCEPT.md sections 3 and 4); the fixtures sit next to the
# tests that use them.

# A hidden test that keeps a marker outside the phase directory and returns early on
# every later run (ACCEPT.md E11).
PHASE_MARKER_HIDDEN = '''import os
import unittest

from src.textutil import slugify

MARK = {marker!r}


def _primed():
    if os.path.exists(MARK):
        return True
    with open(MARK, "w") as stream:
        stream.write("1")
    return False


class PhaseMarkerTests(unittest.TestCase):
    def test_collapses_a_run_of_separators(self):
        if _primed():
            return
        self.assertEqual(slugify("Hello   World"), "hello-world")

    def test_drops_leading_and_trailing_separators(self):
        if _primed():
            return
        self.assertEqual(slugify("  Hello, World!  "), "hello-world")
'''

# A hidden test that asks nothing about behaviour, only "which directory am I in?"
# (ACCEPT.md E12b).
CWD_ONLY_HIDDEN = '''import os
import unittest


class CwdOnlyTests(unittest.TestCase):
    def test_not_in_the_base_tree(self):
        self.assertNotIn("base-hidden", os.getcwd())

    def test_not_in_the_green_tree(self):
        self.assertNotIn("green", os.getcwd())
'''

# A hidden test whose verdict is a coin flip on every run (ACCEPT.md E13b).
COIN_FLIP_HIDDEN = "import random\nimport unittest\n\n\nclass CoinFlipTests(unittest.TestCase):\n" + "".join(
    "    def test_flip_%d(self):\n        self.assertLess(random.random(), 0.5)\n" % index
    for index in range(8))

# A hidden test whose three runs inside one phase disagree on purpose: the first run
# fails, the next two return silently (P1-4 / NONDETERMINISTIC).
RUN_COUNTER_HIDDEN = '''import os
import unittest

from src.textutil import slugify

COUNTER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "h4_run_counter.txt")


class RunCounterTests(unittest.TestCase):
    def test_collapses_a_run_of_separators(self):
        seen = 0
        if os.path.exists(COUNTER):
            with open(COUNTER) as stream:
                seen = int(stream.read().strip() or "0")
        with open(COUNTER, "w") as stream:
            stream.write(str(seen + 1))
        if seen:
            return
        self.assertEqual(slugify("Hello   World"), "hello-world")
'''

# The statements below are appended to GOOD_STATEMENT; none of them may be accepted.
# The first one is the hidden test's own header with every punctuation mark stripped:
# an 8-word window still matches even though no 8-token window does (ACCEPT.md E14).
LEAK_BY_PUNCTUATION = (
    "\nIt behaves like import unittest from src textutil import slugify class "
    "SlugifySeparatorTests unittest TestCase def test_collapses_a_run_of_separators\n")

BANNED_VOCABULARY = (
    ("oracle", "ORACLE_MENTION"),
    ("grader", "GRADER_MENTION"),
    ("evaluation", "EVALUATION_MENTION"),
    ("experiment", "EXPERIMENT_MENTION"),
    ("treatment", "TREATMENT_MENTION"),
    ("hidden test", "HIDDEN_TEST_MENTION"),
)

MODE_CHANGE_PATCH = (
    "diff --git a/src/textutil.py b/src/textutil.py\n"
    "old mode 100644\n"
    "new mode 100755\n"
    + "".join(diff("src/textutil.py", GOOD_SOURCE, FIXED_SOURCE).splitlines(True)[2:]))

BINARY_PATCH = diff("src/textutil.py", GOOD_SOURCE, FIXED_SOURCE) + (
    "diff --git a/src/blob.bin b/src/blob.bin\n"
    "new file mode 100644\n"
    "index 0000000..1111111\n"
    "GIT binary patch\n"
    "literal 4\n"
    "LcmZ?wbhEHb0000\n"
    "\nliteral 0\nHcmV?d00001\n")

RENAME_PATCH = diff("src/textutil.py", GOOD_SOURCE, FIXED_SOURCE) + (
    "diff --git a/src/alias.py b/src/alias_impl.py\n"
    "similarity index 90%\n"
    "rename from src/alias.py\n"
    "rename to src/alias_impl.py\n"
    "--- a/src/alias.py\n"
    "+++ b/src/alias_impl.py\n"
    "@@ -1 +1 @@\n"
    "-X = 1\n"
    "+X = 2\n")

# --- round-2 attack payloads (P1-1, P1-2, P2-3) -----------------------------------

# N22: package code prints unittest's own summary and exits before discovery can import
# the failing test. With a stdout-reading verifier this was a PASS.
FORGING_INIT = '''import os
import sys

print("Ran 3 tests in 0.001s")
print()
print("OK")
sys.stdout.flush()
os._exit(0)
'''

FORGING_VISIBLE = GOOD_VISIBLE_TESTS.replace(
    'self.assertEqual(word_count("one two three"), 3)',
    'self.assertEqual(word_count("one two three"), 999)')

# N23: the reference patch itself forges the hidden run's summary and leaves the bug.
FORGING_HEADER = '''import os
import sys

if "test_hidden" in " ".join(sys.argv):
    print("Ran 1 test in 0.001s")
    print()
    print("OK")
    sys.stdout.flush()
    os._exit(0)

'''

# Stronger than N22: package code finds the runner's result fd in argv and writes an
# otherwise perfectly shaped report (right ids, right counts, exit 0) with a made-up MAC.
RESULT_FD_FORGERY = '''import json
import os
import sys


def _forge():
    try:
        fd = int(sys.argv[sys.argv.index("--result-fd") + 1])
    except (ValueError, IndexError):
        return
    report = {
        "version": 1,
        "tests": [
            {"id": "TextUtilTests.test_slugify_joins_words_with_dashes", "outcome": "pass"},
            {"id": "TextUtilTests.test_slugify_lowercases", "outcome": "pass"},
            {"id": "TextUtilTests.test_word_count_counts_words", "outcome": "pass"},
        ],
        "counts": {"ran": 3, "failures": 0, "errors": 0, "skipped": 0, "unexpected": 0},
        "load_error": None,
        "load_detail": "",
        "executed": [],
        "nonce_mac": "0" * 64,
    }
    os.write(fd, (json.dumps(report) + "\\n").encode())
    os._exit(0)


_forge()
'''

# N21: the "fix" only edits a docstring, and the hidden test only looks for that text.
DOCSTRING_ONLY_SOURCE = GOOD_SOURCE.replace(
    '    """Return the number of whitespace-separated words."""',
    '    """Return the number of whitespace-separated words.\n\n'
    '    Counts only non-empty words."""')

DOCSTRING_COLLUSION_HIDDEN = '''import unittest

from src.textutil import slugify


class DocstringOnlyTests(unittest.TestCase):
    def test_the_patch_added_a_docstring(self):
        with open("src/textutil.py") as stream:
            self.assertIn("Counts only non-empty words.", stream.read())

    def test_the_module_still_works(self):
        self.assertEqual(slugify("Hello World"), "hello-world")
'''

COMMENT_ONLY_SOURCE = GOOD_SOURCE.replace(
    '"""Small text helpers used by the sample project."""\n',
    '"""Small text helpers used by the sample project."""\n'
    '# documented for the reader\n')

COMMENT_COLLUSION_HIDDEN = '''import unittest

from src.textutil import slugify


class CommentOnlyTests(unittest.TestCase):
    def test_the_patch_added_a_comment(self):
        with open("src/textutil.py") as stream:
            self.assertIn("# documented for the reader", stream.read())

    def test_the_module_still_works(self):
        self.assertEqual(slugify("Hello World"), "hello-world")
'''

# Dead code: the added body line can never run, and the hidden test only greps for it.
DEAD_CODE_SOURCE = GOOD_SOURCE + '''

def unused_helper():
    return "never called"
'''

DEAD_CODE_HIDDEN = '''import unittest

from src.textutil import slugify


class DeadCodeTests(unittest.TestCase):
    def test_the_patch_added_a_function(self):
        with open("src/textutil.py") as stream:
            self.assertIn("def unused_helper", stream.read())

    def test_the_module_still_works(self):
        self.assertEqual(slugify("Hello World"), "hello-world")
'''

# A hidden test that reads the fixed source but never imports the target (P2-3).
NO_IMPORT_HIDDEN = '''import unittest


class SourceTextTests(unittest.TestCase):
    def test_the_fix_is_present(self):
        with open("src/textutil.py") as stream:
            self.assertIn('parts = [part for part in replaced.split("-") if part]',
                          stream.read())
'''

# A test module that exits before the runner can report anything.
EARLY_EXIT_HIDDEN = "import os\n\nos._exit(0)\n" + GOOD_HIDDEN


def verify(pkg, **kwargs):
    """Verify with the sandbox requirement satisfied: the good package must be green."""
    kwargs.setdefault("allow_unsandboxed", True)
    return taskpack.verify_package(pkg, **kwargs)


class CanonicalCommandTests(unittest.TestCase):
    """P1-1: only the one canonical argv is accepted, and nothing runs before the check."""

    VARIANTS = (
        ("payload before -m", ["python", "-c", "print('Ran 1 test in 0.001s');print('OK')",
                               "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
        ("shell string", "python -m unittest discover -s tests -t ."),
        ("absolute interpreter", ["/bin/sh", "-c", "python -m unittest discover -s tests"]),
        ("python3 spelling", ["python3", "-m", "unittest", "discover", "-s", "tests", "-t", "."]),
        ("extra flag", ["python", "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"]),
        ("missing -t", ["python", "-m", "unittest", "discover", "-s", "tests"]),
        ("empty argv", []),
    )

    def test_only_the_canonical_argv_is_accepted(self):
        for label, variant in self.VARIANTS:
            with self.subTest(variant=label), tempfile.TemporaryDirectory() as temporary:
                pkg = build_package(temporary, manifest_overrides={"test_command": variant})
                verdict = verify(pkg)
                self.assertEqual(verdict["overall"], "FAIL")
                self.assertIn("TEST_COMMAND_NOT_CANONICAL", reasons(verdict, 1))
                for number in (2, 3, 4, 5, 6):
                    self.assertEqual(
                        check(verdict, number)["status"], "NOT_RUN",
                        "a non-canonical test_command must be refused before anything runs")


class BaseGateTests(unittest.TestCase):
    """P2-1: check 2 must have tests that go red when the check is removed."""

    def test_visible_tests_must_pass_at_base(self):
        broken = GOOD_VISIBLE_TESTS.replace('self.assertEqual(word_count("one two three"), 3)',
                                           'self.assertEqual(word_count("one two three"), 999)')
        self.assertNotEqual(broken, GOOD_VISIBLE_TESTS)
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=broken)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertEqual(check(verdict, 2)["status"], "FAIL")
            self.assertIn("VISIBLE_TESTS_FAIL", reasons(verdict, 2))

    def test_ruff_must_be_clean_at_base(self):
        dirty = "import os\n\n" + GOOD_VISIBLE_TESTS
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=dirty)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertEqual(check(verdict, 2)["status"], "FAIL")
            self.assertIn("RUFF_DIRTY_AT_BASE", reasons(verdict, 2))


class PhaseIsolationTests(unittest.TestCase):
    """P1-2/P1-3/P1-4: identical phase paths, no state carried, three agreeing runs."""

    def setUp(self):
        self.marker = os.path.join(tempfile.gettempdir(), "h4-phase-marker-%d" % os.getpid())
        if os.path.exists(self.marker):
            os.unlink(self.marker)

    def tearDown(self):
        if os.path.exists(self.marker):
            os.unlink(self.marker)

    def test_both_phases_use_one_identical_directory_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])
            base_phase = check(verdict, 3)["data"]["phase"]
            patched_phase = check(verdict, 4)["data"]["phase"]
            self.assertEqual(base_phase, patched_phase,
                             "the hidden test must see the same path in both phases")
            self.assertEqual(Path(base_phase).name, "repo")
            self.assertEqual(Path(base_phase).parent.name, "phase")

    def test_hidden_test_cannot_carry_state_between_phases(self):
        require_sandbox(self)
        hidden = PHASE_MARKER_HIDDEN.format(marker=self.marker)
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=hidden, patches=[
                ("src/textutil.py", GOOD_SOURCE, GOOD_SOURCE.replace(
                    '"""Small text helpers used by the sample project."""\n',
                    '"""Small text helpers used by the sample project."""\n'
                    "# documentation only: the reference fixes nothing\n"))])
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("HIDDEN_TEST_ERRORS_AT_BASE", reasons(verdict, 3))
            self.assertFalse(os.path.exists(self.marker),
                             "package code must not be able to write outside its phase")

    def test_hidden_test_cannot_detect_the_phase_from_its_own_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=CWD_ONLY_HIDDEN)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("HIDDEN_TEST_ALREADY_PASSES_AT_BASE", reasons(verdict, 3))

    def test_hidden_test_is_run_five_times_in_each_phase(self):
        # P2-2 raised the repeat count from three to five; five agreeing runs lower the
        # chance that an intermittently failing test slips through (not to zero).
        self.assertGreaterEqual(taskpack.HIDDEN_REPEATS, 5)
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])
            self.assertEqual(check(verdict, 3)["data"]["runs"], ["CLEAN_FAILURE"] * 5)
            self.assertEqual(check(verdict, 4)["data"]["runs"], ["PASS"] * 5)

    def test_previous_phase_directory_is_deleted(self):
        visible = GOOD_VISIBLE_TESTS.replace(
            "    def test_slugify_lowercases(self):",
            "    def test_writes_a_leftover(self):\n"
            "        Path(\"leftover.txt\").write_text(\"phase A\")\n\n"
            "    def test_slugify_lowercases(self):").replace(
            "import unittest\n", "import unittest\nfrom pathlib import Path\n", 1)
        hidden = GOOD_HIDDEN.replace(
            "from src.textutil import slugify",
            "import os\n\nfrom src.textutil import slugify").replace(
            '        self.assertEqual(slugify("Hello   World"), "hello-world")',
            '        self.assertFalse(os.path.exists("leftover.txt"),\n'
            '                         "a file from an earlier phase survived into this one")\n'
            '        self.assertEqual(slugify("Hello   World"), "hello-world")')
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=hidden, visible_tests=visible)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])

    def test_hidden_test_whose_runs_disagree_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=RUN_COUNTER_HIDDEN)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("NONDETERMINISTIC", reasons(verdict, 3))
            self.assertEqual(len(check(verdict, 3)["data"]["runs"]), 5)

    def test_random_hidden_test_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=COIN_FLIP_HIDDEN)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL",
                             "a hidden test that depends on randomness must never be accepted")


class ConfinementTests(unittest.TestCase):
    """P1-3/P2-2: package code really is confined, and an unconfined verdict is not PASS."""

    def test_network_is_denied_to_package_code(self):
        require_sandbox(self)
        visible = GOOD_VISIBLE_TESTS.replace(
            "    def test_slugify_lowercases(self):",
            "    def test_network_is_denied(self):\n"
            "        with self.assertRaises(PermissionError):\n"
            "            socket.create_connection((\"127.0.0.1\", 9), timeout=0.5)\n\n"
            "    def test_slugify_lowercases(self):").replace(
            "import unittest\n", "import socket\nimport unittest\n", 1)
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=visible)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])
            self.assertEqual(verdict["isolation"], "SANDBOX_EXEC")

    def test_real_home_is_unreadable_to_package_code(self):
        require_sandbox(self)
        visible = GOOD_VISIBLE_TESTS.replace(
            "    def test_slugify_lowercases(self):",
            "    def test_real_home_is_unreadable(self):\n"
            "        home = pwd.getpwuid(os.getuid()).pw_dir\n"
            "        with self.assertRaises(PermissionError):\n"
            "            os.listdir(home)\n\n"
            "    def test_slugify_lowercases(self):").replace(
            "import unittest\n", "import os\nimport pwd\nimport unittest\n", 1)
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=visible)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])

    def test_unsandboxed_verdict_is_never_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            with mock.patch.object(taskpack, "sandbox_available", lambda: False):
                unconfined = taskpack.verify_package(pkg)
            self.assertEqual(unconfined["isolation"], "NONE")
            self.assertEqual(unconfined["overall"], "UNSANDBOXED")
            for number in range(1, 7):
                self.assertEqual(check(unconfined, number)["status"], "PASS",
                                 reasons(unconfined, number))

            with mock.patch.object(taskpack, "sandbox_available", lambda: False):
                allowed = taskpack.verify_package(pkg, allow_unsandboxed=True)
            self.assertEqual(allowed["overall"], "PASS", allowed["reasons"])
            self.assertEqual(allowed["isolation"], "NONE")


class TimeoutTests(unittest.TestCase):
    """P2-3: a hanging hidden test is refused at once and never paid for twice."""

    def test_first_timeout_stops_the_run(self):
        hanging = GOOD_HIDDEN.replace(
            'self.assertEqual(slugify("Hello   World"), "hello-world")', "pass")
        hanging = hanging.replace(
            "    def test_collapses_a_run_of_separators(self):",
            "    def test_collapses_a_run_of_separators(self):\n"
            "        while True:\n"
            "            pass")
        original = taskpack.RUN_TIMEOUT
        taskpack.RUN_TIMEOUT = 2
        try:
            with tempfile.TemporaryDirectory() as temporary:
                pkg = build_package(temporary, hidden=hanging)
                started = time.monotonic()
                verdict = verify(pkg)
                elapsed = time.monotonic() - started
        finally:
            taskpack.RUN_TIMEOUT = original
        self.assertEqual(verdict["overall"], "FAIL")
        self.assertIn("HIDDEN_TEST_TIMEOUT", reasons(verdict, 3))
        self.assertEqual(check(verdict, 4)["status"], "NOT_RUN",
                         "the post-patch phase must not pay for the same timeout again")
        self.assertIn("STOPPED_BEFORE", reasons(verdict, 4))
        self.assertLess(elapsed, 8 * taskpack.RUN_TIMEOUT)


class StructureRuleTests(unittest.TestCase):
    """P3: unknown manifest keys, nested repositories and bytecode caches are refused."""

    def test_unknown_manifest_key_is_rejected(self):
        overrides = {"evaluation": "arm B", "oracle": "tests/test_hidden.py"}
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, manifest_overrides=overrides)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("PACKAGE_JSON_UNKNOWN_KEY evaluation", reasons(verdict, 1))
            self.assertIn("PACKAGE_JSON_UNKNOWN_KEY oracle", reasons(verdict, 1))

    def test_unknown_gate_key_is_rejected(self):
        gate = {"kind": "ruff", "config": "ruff.toml", "oracle": "tests/test_hidden.py"}
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, manifest_overrides={"gate": gate})
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("PACKAGE_JSON_UNKNOWN_KEY gate.oracle", reasons(verdict, 1))

    def test_nested_git_repository_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "base" / ".git").mkdir()
            (pkg / "base" / ".git" / "config").write_text(
                "[core]\n\trepositoryformatversion = 0\n\tbare = false\n"
                "\tworktree = %s\n" % (Path(temporary) / "escape"))
            (pkg / "base" / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("FORBIDDEN_PATH base/.git", reasons(verdict, 1))
            self.assertFalse((Path(temporary) / "escape").exists())

    def test_bytecode_cache_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            cache = pkg / "base" / "src" / "__pycache__"
            cache.mkdir()
            (cache / "textutil.cpython-312.pyc").write_bytes(b"x")
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("FORBIDDEN_PATH base/src/__pycache__", reasons(verdict, 1))

    def test_stray_bytecode_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "base" / "src" / "textutil.pyc").write_bytes(b"x")
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("FORBIDDEN_PATH base/src/textutil.pyc", reasons(verdict, 1))


class PatchShapeTests(unittest.TestCase):
    """P3: mode changes, binary hunks and renames are refused (a new file is still fine)."""

    def test_mode_change_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "reference.patch").write_text(MODE_CHANGE_PATCH)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("PATCH_HAS_MODE_CHANGE", reasons(verdict, 6))

    def test_binary_hunk_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "reference.patch").write_text(BINARY_PATCH)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("PATCH_HAS_BINARY_HUNK", reasons(verdict, 6))

    def test_rename_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "reference.patch").write_text(RENAME_PATCH)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("PATCH_HAS_RENAME", reasons(verdict, 6))

    def test_new_second_file_is_still_allowed(self):
        extra = ("src/extra.py", "", "def noop():\n    return None\n")
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, patches=[
                ("src/textutil.py", GOOD_SOURCE, FIXED_SOURCE), extra])
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])


class StatementScreenTests(unittest.TestCase):
    """P3: the vocabulary screen and the leak check ignore case and punctuation."""

    def test_banned_vocabulary_is_rejected(self):
        for word, label in BANNED_VOCABULARY:
            with self.subTest(word=word), tempfile.TemporaryDirectory() as temporary:
                statement = GOOD_STATEMENT + "\nA %s will look at this.\n" % word
                pkg = build_package(temporary, statement=statement)
                verdict = verify(pkg)
                self.assertEqual(verdict["overall"], "FAIL")
                self.assertIn("STATEMENT_MENTIONS_" + label, reasons(verdict, 5))

    def test_leak_without_punctuation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, statement=GOOD_STATEMENT + LEAK_BY_PUNCTUATION)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("STATEMENT_LEAKS_HIDDEN_TEST", reasons(verdict, 5))

    def test_one_leaked_line_without_its_punctuation_is_rejected(self):
        leak = ('\nThe check is self.assertEqual(slugify("Hello World") "hello-world") today.\n')
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, statement=GOOD_STATEMENT + leak)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("STATEMENT_LEAKS_HIDDEN_FRAGMENT", reasons(verdict, 5))

    def test_statement_may_show_an_example_the_hidden_test_does_not_use(self):
        statement = GOOD_STATEMENT + (
            '\nFor example, `slugify("Hello, World")` must return `"hello-world"`.\n')
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, statement=statement)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])

    def test_leak_in_capitals_is_rejected(self):
        leak = "\nTHE CHECK IS SELF.ASSERTEQUAL(SLUGIFY(\"HELLO   WORLD\"), \"HELLO-WORLD\")\n"
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, statement=GOOD_STATEMENT + leak)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("STATEMENT_LEAKS_HIDDEN_TEST", reasons(verdict, 5))


class OutputCapTests(unittest.TestCase):
    """P3: a process that floods its output is cut off and the package is refused."""

    def test_noisy_test_is_rejected(self):
        noisy = GOOD_VISIBLE_TESTS.replace(
            "    def test_slugify_lowercases(self):",
            "    def test_noisy(self):\n"
            "        print(\"x\" * (20 * 1024 * 1024))\n\n"
            "    def test_slugify_lowercases(self):")
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=noisy)
            started = time.monotonic()
            verdict = verify(pkg)
            elapsed = time.monotonic() - started
        self.assertEqual(verdict["overall"], "FAIL")
        self.assertIn("OUTPUT_OVERFLOW", reasons(verdict, 2))
        self.assertLess(elapsed, 30)


class SealProvenanceTests(unittest.TestCase):
    """P3: a seal the maker shipped proves nothing, and the verdict says so out loud."""

    def hand_written_seal(self, pkg):
        files = {}
        for path in Path(pkg).rglob("*"):
            if not path.is_file() or path.name == "SEAL.json":
                continue
            files[str(path.relative_to(pkg))] = hashlib.sha256(path.read_bytes()).hexdigest()
        (pkg / "SEAL.json").write_text(
            json.dumps({"version": 1, "files": files, "verified": True},
                       indent=2, sort_keys=True) + "\n")

    def test_maker_written_seal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            self.hand_written_seal(pkg)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("SEAL_PRESENT_BEFORE_SEALING", reasons(verdict, 7))
            self.assertIs(verdict["sealed"], False)

    def test_resealed_after_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            taskpack.seal_package(pkg)
            statement = pkg / "statement.md"
            statement.write_text(statement.read_text() + "\nOne more line.\n")
            seal = json.loads((pkg / "SEAL.json").read_text())
            seal["files"]["statement.md"] = hashlib.sha256(statement.read_bytes()).hexdigest()
            (pkg / "SEAL.json").write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertEqual(check(verdict, 7)["status"], "FAIL")

    def test_seal_package_still_seals_and_reverifies(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            taskpack.seal_package(pkg)
            self.assertTrue((pkg / "SEAL.json").is_file())
            again = verify(pkg, allow_reseal=True)
            self.assertEqual(again["overall"], "PASS", again["reasons"])
            self.assertIs(again["sealed"], True)


class CliTests(unittest.TestCase):
    def test_cli_verify_and_seal(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            verify_run = subprocess.run(
                [sys.executable, str(PILOT / "taskpack.py"), "verify", str(pkg),
                 "--allow-unsandboxed"], capture_output=True, text=True)
            self.assertEqual(verify_run.returncode, 0, verify_run.stdout + verify_run.stderr)
            self.assertEqual(json.loads(verify_run.stdout)["overall"], "PASS")

            seal_run = subprocess.run(
                [sys.executable, str(PILOT / "taskpack.py"), "seal", str(pkg),
                 "--allow-unsandboxed"], capture_output=True, text=True)
            self.assertEqual(seal_run.returncode, 0, seal_run.stdout + seal_run.stderr)
            self.assertIs(json.loads(seal_run.stdout)["sealed"], True)
            self.assertTrue((pkg / "SEAL.json").is_file())

            (pkg / "base" / "src" / "extra.py").write_text("X = 1\n")
            tampered = subprocess.run(
                [sys.executable, str(PILOT / "taskpack.py"), "verify", str(pkg)],
                capture_output=True, text=True)
            self.assertEqual(tampered.returncode, 1)
            verdict = json.loads(tampered.stdout)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertEqual(verdict["seal"], "BROKEN")

    def test_cli_verify_exits_non_zero_whenever_overall_is_not_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            taskpack.seal_package(pkg)

            refused = subprocess.run(
                [sys.executable, str(PILOT / "taskpack.py"), "verify", str(pkg)],
                capture_output=True, text=True)
            self.assertEqual(refused.returncode, 1, refused.stdout)
            verdict = json.loads(refused.stdout)
            self.assertNotEqual(verdict["overall"], "PASS")
            self.assertIs(verdict["sealed"], False)
            self.assertIn("SEAL_PRESENT_BEFORE_SEALING", " ".join(verdict["reasons"]))

            accepted = subprocess.run(
                [sys.executable, str(PILOT / "taskpack.py"), "verify", str(pkg), "--reseal",
                 "--allow-unsandboxed"], capture_output=True, text=True)
            self.assertEqual(accepted.returncode, 0, accepted.stdout + accepted.stderr)
            verdict = json.loads(accepted.stdout)
            self.assertEqual(verdict["overall"], "PASS")
            self.assertIs(verdict["sealed"], True)

    def test_cli_seal_refuses_a_bad_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "notes.txt").write_text("scratch\n")
            seal_run = subprocess.run(
                [sys.executable, str(PILOT / "taskpack.py"), "seal", str(pkg)],
                capture_output=True, text=True)
            self.assertEqual(seal_run.returncode, 1)
            self.assertIs(json.loads(seal_run.stdout)["sealed"], False)
            self.assertFalse((pkg / "SEAL.json").exists())


class AttackRegressionTests(unittest.TestCase):
    """One regression per attack the acceptance report marked 错 or 松 (ACCEPT.md §3)."""

    def assertRefused(self, verdict, number, reason):
        self.assertNotEqual(verdict["overall"], "PASS", "the package must not be accepted")
        self.assertEqual(check(verdict, number)["status"], "FAIL", reasons(verdict, number))
        self.assertIn(reason, reasons(verdict, number))

    def test_e4_test_command_cannot_fake_unittest_output(self):
        fake = ["python", "-c", "print('Ran 1 test in 0.001s');print('OK')",
                "-m", "unittest", "discover", "-s", "tests", "-t", "."]
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, manifest_overrides={"test_command": fake})
            verdict = verify(pkg)
            self.assertRefused(verdict, 1, "TEST_COMMAND_NOT_CANONICAL")

    def test_e11_hidden_test_cannot_keep_a_tmp_marker(self):
        require_sandbox(self)
        marker = os.path.join(tempfile.gettempdir(), "h4-e11-marker-%d" % os.getpid())
        if os.path.exists(marker):
            os.unlink(marker)
        try:
            with tempfile.TemporaryDirectory() as temporary:
                pkg = build_package(temporary, hidden=PHASE_MARKER_HIDDEN.format(marker=marker))
                verdict = verify(pkg)
                self.assertEqual(verdict["overall"], "FAIL")
                self.assertIn("HIDDEN_TEST_ERRORS_AT_BASE", reasons(verdict, 3))
                self.assertFalse(os.path.exists(marker))
        finally:
            if os.path.exists(marker):
                os.unlink(marker)

    def test_e12b_hidden_test_cannot_check_only_its_directory_name(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=CWD_ONLY_HIDDEN)
            self.assertRefused(verify(pkg), 3, "HIDDEN_TEST_ALREADY_PASSES_AT_BASE")

    def test_e13b_random_hidden_test_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=COIN_FLIP_HIDDEN)
            self.assertNotEqual(verify(pkg)["overall"], "PASS")

    def test_writes_abs_tmp_outside_the_phase_is_refused(self):
        require_sandbox(self)
        marker = os.path.join(tempfile.gettempdir(), "h4-e-abs-marker-%d" % os.getpid())
        if os.path.exists(marker):
            os.unlink(marker)
        source = ("open(%r, 'w').write('x')\n\n" % marker) + GOOD_SOURCE
        try:
            with tempfile.TemporaryDirectory() as temporary:
                pkg = build_package(temporary, base_source=source)
                verdict = verify(pkg)
                self.assertEqual(verdict["overall"], "FAIL")
                self.assertIn("VISIBLE_TESTS_FAIL", reasons(verdict, 2))
                self.assertFalse(os.path.exists(marker),
                                 "package code wrote an absolute path outside its phase")
        finally:
            if os.path.exists(marker):
                os.unlink(marker)

    def test_e19_home_lookup_cannot_read_the_real_home(self):
        require_sandbox(self)
        visible = GOOD_VISIBLE_TESTS.replace(
            "    def test_slugify_lowercases(self):",
            "    def test_real_home_is_readable(self):\n"
            "        home = pwd.getpwuid(os.getuid()).pw_dir\n"
            "        self.assertTrue(os.listdir(home))\n\n"
            "    def test_slugify_lowercases(self):").replace(
            "import unittest\n", "import os\nimport pwd\nimport unittest\n", 1)
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=visible)
            self.assertRefused(verify(pkg), 2, "VISIBLE_TESTS_FAIL")

    def test_e20_package_code_cannot_open_a_socket(self):
        require_sandbox(self)
        visible = GOOD_VISIBLE_TESTS.replace(
            "    def test_slugify_lowercases(self):",
            "    def test_network_is_denied(self):\n"
            "        with self.assertRaises(PermissionError):\n"
            "            socket.create_connection((\"127.0.0.1\", 9), timeout=0.5)\n\n"
            "    def test_slugify_lowercases(self):").replace(
            "import unittest\n", "import socket\nimport unittest\n", 1)
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=visible)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])
            self.assertEqual(verdict["isolation"], "SANDBOX_EXEC")

    def test_e21_flooding_output_is_refused(self):
        noisy = GOOD_VISIBLE_TESTS.replace(
            "    def test_slugify_lowercases(self):",
            "    def test_noisy(self):\n"
            "        print(\"x\" * (20 * 1024 * 1024))\n\n"
            "    def test_slugify_lowercases(self):")
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=noisy)
            self.assertRefused(verify(pkg), 2, "OUTPUT_OVERFLOW")

    def test_e14_statement_leak_survives_no_punctuation_change(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, statement=GOOD_STATEMENT + LEAK_BY_PUNCTUATION)
            self.assertRefused(verify(pkg), 5, "STATEMENT_LEAKS_HIDDEN_TEST")

    def test_e14_single_assertion_leak_without_punctuation_is_refused(self):
        leak = ('\nThe check is self.assertEqual(slugify("Hello World") "hello-world") today.\n')
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, statement=GOOD_STATEMENT + leak)
            self.assertRefused(verify(pkg), 5, "STATEMENT_LEAKS_HIDDEN_FRAGMENT")

    def test_e26b_statement_cannot_name_oracle_grader_evaluation_experiment_treatment(self):
        leak = ("\nThis synthetic evaluation task has an oracle and a grader; the "
                "experiment has two treatments.\n")
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, statement=GOOD_STATEMENT + leak)
            verdict = verify(pkg)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertIn("STATEMENT_MENTIONS_ORACLE_MENTION", reasons(verdict, 5))
            self.assertIn("STATEMENT_MENTIONS_GRADER_MENTION", reasons(verdict, 5))
            self.assertIn("STATEMENT_MENTIONS_EVALUATION_MENTION", reasons(verdict, 5))
            self.assertIn("STATEMENT_MENTIONS_EXPERIMENT_MENTION", reasons(verdict, 5))
            self.assertIn("STATEMENT_MENTIONS_TREATMENT_MENTION", reasons(verdict, 5))

    def test_e18_bytecode_cache_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "base" / "src" / "__pycache__").mkdir()
            (pkg / "base" / "src" / "__pycache__" / "textutil.pyc").write_bytes(b"x")
            self.assertRefused(verify(pkg), 1, "FORBIDDEN_PATH")

    def test_e22_rehashing_after_a_change_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            taskpack.seal_package(pkg)
            statement = pkg / "statement.md"
            statement.write_text(statement.read_text() + "\nOne more line.\n")
            seal = json.loads((pkg / "SEAL.json").read_text())
            seal["files"]["statement.md"] = hashlib.sha256(statement.read_bytes()).hexdigest()
            (pkg / "SEAL.json").write_text(json.dumps(seal, indent=2, sort_keys=True) + "\n")
            self.assertRefused(verify(pkg), 7, "SEAL_PRESENT_BEFORE_SEALING")

    def test_e23_maker_written_seal_is_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            SealProvenanceTests.hand_written_seal(self, pkg)
            self.assertRefused(verify(pkg), 7, "SEAL_PRESENT_BEFORE_SEALING")

    def test_e25_nested_git_worktree_cannot_write_outside(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            escape = Path(temporary) / "escape"
            (pkg / "base" / ".git").mkdir()
            (pkg / "base" / ".git" / "config").write_text(
                "[core]\n\trepositoryformatversion = 0\n\tbare = false\n"
                "\tworktree = %s\n" % escape)
            (pkg / "base" / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
            self.assertRefused(verify(pkg), 1, "FORBIDDEN_PATH")
            self.assertFalse(escape.exists())


def signed_report(nonce, payload):
    """Build a report exactly the way the documented protocol says, with a real MAC."""
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    mac = hmac.new(bytes.fromhex(nonce), body, hashlib.sha256).hexdigest()
    return dict(payload, nonce_mac=mac)


class SignedReportTests(unittest.TestCase):
    """P1-1/P1-2 a: no verdict may come from text a package can print.

    The verifier starts ``pilot/test_runner.py`` and accepts only a report signed with a
    one-time nonce. These tests are the round-2 attacks N22/N23 plus the mutation checks
    that fail when the MAC gate is removed.
    """

    def test_n22_package_that_forges_the_visible_summary_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=FORGING_VISIBLE)
            (pkg / "base" / "src" / "__init__.py").write_text(FORGING_INIT)
            verdict = verify(pkg)
        self.assertEqual(verdict["overall"], "FAIL")
        self.assertEqual(check(verdict, 2)["status"], "FAIL", reasons(verdict, 2))
        self.assertIn("VISIBLE_TESTS_RESULT_REJECTED", reasons(verdict, 2))
        self.assertIn("TEST_RESULT_UNAVAILABLE", reasons(verdict, 2),
                      "a run that produced no signed report must never be a pass")
        self.assertIn("VISIBLE_TESTS_FAIL", reasons(verdict, 2))

    def test_n23_patch_that_forges_the_hidden_summary_is_rejected(self):
        forged = FORGING_HEADER + GOOD_SOURCE
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, patches=[
                ("src/textutil.py", GOOD_SOURCE, forged)])
            verdict = verify(pkg)
        self.assertEqual(verdict["overall"], "FAIL")
        self.assertEqual(check(verdict, 4)["status"], "FAIL", reasons(verdict, 4))
        self.assertIn("HIDDEN_TEST_RESULT_REJECTED", reasons(verdict, 4))
        self.assertIn("TEST_RESULT_UNAVAILABLE", reasons(verdict, 4))

    def test_forged_report_on_the_result_fd_is_rejected_without_the_nonce(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, visible_tests=FORGING_VISIBLE)
            (pkg / "base" / "src" / "__init__.py").write_text(RESULT_FD_FORGERY)
            verdict = verify(pkg)
        self.assertEqual(verdict["overall"], "FAIL")
        self.assertNotEqual(check(verdict, 2)["status"], "PASS")
        self.assertIn("VISIBLE_TESTS_RESULT_REJECTED", reasons(verdict, 2))
        self.assertIn("TEST_RESULT_MAC_INVALID", reasons(verdict, 2),
                      "a report the runner did not sign with this run's nonce is not a result")

    def test_mac_check_is_load_bearing(self):
        # Mutation anchor: delete the MAC verification in _accept_report and the first
        # assertion below turns green, so this test goes red.
        nonce = "ab" * 32
        payload = {
            "version": 1,
            "tests": [{"id": "WidgetTests.test_one", "outcome": "pass"}],
            "counts": {"ran": 1, "failures": 0, "errors": 0, "skipped": 0,
                       "unexpected": 0},
            "load_error": None,
            "load_detail": "",
            "executed": [],
        }
        forged = dict(payload, nonce_mac="0" * 64)
        accepted, reason = taskpack._accept_report(forged, nonce, {"WidgetTests.test_one"}, 0)
        self.assertFalse(accepted)
        self.assertEqual(reason, "TEST_RESULT_MAC_INVALID")
        with mock.patch.object(taskpack, "_verify_report_mac", lambda *args: True):
            accepted, reason = taskpack._accept_report(
                forged, nonce, {"WidgetTests.test_one"}, 0)
            self.assertTrue(accepted, "only the MAC stood between this report and a pass")

    def test_a_protocol_conforming_report_is_accepted_only_with_its_own_nonce(self):
        nonce = "cd" * 32
        payload = {
            "version": 1,
            "tests": [{"id": "WidgetTests.test_one", "outcome": "pass"},
                      {"id": "WidgetTests.test_two", "outcome": "pass"}],
            "counts": {"ran": 2, "failures": 0, "errors": 0, "skipped": 0,
                       "unexpected": 0},
            "load_error": None,
            "load_detail": "",
            "executed": [["/tmp/example.py", 7]],
        }
        report = signed_report(nonce, payload)
        accepted, reason = taskpack._accept_report(report, nonce, set(), 0)
        self.assertFalse(accepted)
        self.assertIn("TEST_ID_SET_MISMATCH", reason)
        accepted, reason = taskpack._accept_report(
            report, nonce, {"WidgetTests.test_one", "WidgetTests.test_two"}, 0)
        self.assertTrue(accepted, reason)
        wrong, reason = taskpack._accept_report(
            report, "ef" * 32, {"WidgetTests.test_one", "WidgetTests.test_two"}, 0)
        self.assertFalse(wrong)
        self.assertEqual(reason, "TEST_RESULT_MAC_INVALID")

    def test_id_set_equality_is_load_bearing(self):
        # Mutation anchor: drop the id comparison and both rejections turn green.
        nonce = "ab" * 32
        expected = {"WidgetTests.test_one", "WidgetTests.test_two"}

        def report_for(ids):
            return signed_report(nonce, {
                "version": 1,
                "tests": [{"id": item, "outcome": "pass"} for item in ids],
                "counts": {"ran": len(ids), "failures": 0, "errors": 0, "skipped": 0,
                           "unexpected": 0},
                "load_error": None,
                "load_detail": "",
                "executed": [],
            })

        self.assertTrue(taskpack._accept_report(
            report_for(sorted(expected)), nonce, expected, 0)[0])
        missing = taskpack._accept_report(
            report_for(["WidgetTests.test_one"]), nonce, expected, 0)
        self.assertFalse(missing[0], "a test the AST knows about did not run")
        self.assertIn("TEST_ID_SET_MISMATCH", missing[1])
        self.assertIn("missing=", missing[1])
        extra = taskpack._accept_report(
            report_for(sorted(expected) + ["WidgetTests.test_three"]), nonce, expected, 0)
        self.assertFalse(extra[0], "a test the AST does not know about cannot be counted")
        self.assertIn("extra=", extra[1])

    def test_the_canonical_command_stays_display_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            verdict = verify(pkg)
        self.assertEqual(check(verdict, 2)["data"]["command"],
                         taskpack.CANONICAL_TEST_COMMAND)
        self.assertEqual(check(verdict, 2)["data"]["executed_by"], "test_runner.py")
        self.assertEqual(check(verdict, 2)["data"]["visible_ids"],
                         ["TextUtilTests.test_slugify_joins_words_with_dashes",
                          "TextUtilTests.test_slugify_lowercases",
                          "TextUtilTests.test_word_count_counts_words"])


class PatchExerciseTests(unittest.TestCase):
    """P1-2 b / P2-3: the patch must change something that runs."""

    def assertNotExercised(self, pkg):
        verdict = verify(pkg)
        self.assertEqual(verdict["overall"], "FAIL")
        self.assertEqual(check(verdict, 3)["status"], "PASS", reasons(verdict, 3))
        self.assertEqual(check(verdict, 4)["status"], "FAIL", reasons(verdict, 4))
        self.assertIn("PATCH_NOT_EXERCISED", reasons(verdict, 4))
        self.assertIs(check(verdict, 4)["data"]["patch_exercised"], False)
        return verdict

    def test_n21_docstring_only_patch_is_rejected(self):
        # The hidden test passes after the patch and cleanly fails before it; only the
        # "did any changed line run?" check separates this from a real fix.
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=DOCSTRING_COLLUSION_HIDDEN, patches=[
                ("src/textutil.py", GOOD_SOURCE, DOCSTRING_ONLY_SOURCE)])
            self.assertNotExercised(pkg)

    def test_comment_only_patch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=COMMENT_COLLUSION_HIDDEN, patches=[
                ("src/textutil.py", GOOD_SOURCE, COMMENT_ONLY_SOURCE)])
            self.assertNotExercised(pkg)

    def test_dead_code_patch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=DEAD_CODE_HIDDEN, patches=[
                ("src/textutil.py", GOOD_SOURCE, DEAD_CODE_SOURCE)])
            self.assertNotExercised(pkg)

    def test_the_real_fix_is_recorded_as_exercised(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            verdict = verify(pkg)
        self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])
        self.assertIs(check(verdict, 4)["data"]["patch_exercised"], True)
        self.assertTrue(check(verdict, 4)["data"]["watched_lines"])

    def test_hidden_test_must_import_the_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary, hidden=NO_IMPORT_HIDDEN)
            verdict = verify(pkg)
        self.assertEqual(verdict["overall"], "FAIL")
        self.assertEqual(check(verdict, 3)["status"], "FAIL", reasons(verdict, 3))
        self.assertIn("HIDDEN_TEST_DOES_NOT_IMPORT_TARGET", reasons(verdict, 3))

    def test_only_executable_changed_lines_are_watched(self):
        patch = diff("src/textutil.py", GOOD_SOURCE, DOCSTRING_ONLY_SOURCE)
        changed = taskpack._patch_changed_lines(patch)
        self.assertIn("src/textutil.py", changed)
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            (repo / "src").mkdir(parents=True)
            (repo / "src" / "textutil.py").write_text(DOCSTRING_ONLY_SOURCE)
            # Every added line is inside the function docstring, so nothing is watched.
            self.assertEqual(taskpack._patch_watch(repo, patch), {})
            (repo / "src" / "textutil.py").write_text(DEAD_CODE_SOURCE)
            dead_patch = diff("src/textutil.py", GOOD_SOURCE, DEAD_CODE_SOURCE)
            self.assertTrue(taskpack._patch_changed_lines(dead_patch)["src/textutil.py"])
            self.assertTrue(taskpack._patch_watch(repo, dead_patch))


class RunnerApiTests(unittest.TestCase):
    """The API ticket B (``pilot_accept.py``) must call to run the hidden test."""

    def make_tree(self, temporary, hidden=None, source=None):
        tree = Path(temporary) / "tree"
        (tree / "src").mkdir(parents=True)
        (tree / "tests").mkdir()
        (tree / "src" / "__init__.py").write_text("")
        (tree / "src" / "textutil.py").write_text(
            FIXED_SOURCE if source is None else source)
        (tree / "tests" / "__init__.py").write_text("")
        (tree / "tests" / "test_hidden.py").write_text(
            GOOD_HIDDEN if hidden is None else hidden)
        return tree

    def test_a_passing_suite_is_authentic_and_fully_reported(self):
        with tempfile.TemporaryDirectory() as temporary:
            tree = self.make_tree(temporary)
            result = taskpack.run_tests_with_runner(
                tree, "tests/test_hidden.py", "ab" * 32)
        self.assertTrue(result["accepted"], result["reason"])
        self.assertEqual(result["outcome"], "PASS")
        self.assertTrue(all(item["outcome"] == "pass" for item in result["tests"]))
        self.assertEqual(result["counts"]["ran"], 2)
        self.assertEqual(result["expected_ids"],
                         ["SlugifySeparatorTests.test_collapses_a_run_of_separators",
                          "SlugifySeparatorTests.test_drops_leading_and_trailing_separators"])
        self.assertEqual(result["exit_code"], 0)

    def test_a_failing_suite_is_authentic_but_not_a_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            tree = self.make_tree(temporary, source=GOOD_SOURCE)
            result = taskpack.run_tests_with_runner(
                tree, "tests/test_hidden.py", "ab" * 32)
        self.assertTrue(result["accepted"], result["reason"])
        self.assertEqual(result["outcome"], "CLEAN_FAILURE")
        self.assertGreater(result["counts"]["failures"], 0)
        self.assertEqual(result["exit_code"], 1)

    def test_a_module_that_exits_early_produces_no_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            tree = self.make_tree(temporary, hidden=EARLY_EXIT_HIDDEN)
            result = taskpack.run_tests_with_runner(
                tree, "tests/test_hidden.py", "ab" * 32)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["outcome"], "NO_RESULT")
        self.assertIn("TEST_RESULT_UNAVAILABLE", result["reason"])

    def test_explicit_ids_are_accepted_when_they_match(self):
        wanted = "tests.test_hidden.SlugifySeparatorTests.test_collapses_a_run_of_separators"
        with tempfile.TemporaryDirectory() as temporary:
            tree = self.make_tree(temporary)
            result = taskpack.run_tests_with_runner(tree, [wanted], "ab" * 32)
        self.assertTrue(result["accepted"], result["reason"])
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["ran"], 1)
        self.assertEqual([taskpack._short_id(item) for item in result["expected_ids"]],
                         ["SlugifySeparatorTests.test_collapses_a_run_of_separators"])

    def test_a_module_that_hides_a_test_is_caught_by_the_ast_id_set(self):
        # The file declares two cases; a line at import removes one before unittest ever
        # looks at the class, so only one runs. The static AST set still has two.
        hiding = GOOD_HIDDEN.replace(
            "if __name__ == \"__main__\":",
            "del SlugifySeparatorTests.test_drops_leading_and_trailing_separators\n\n"
            "if __name__ == \"__main__\":")
        with tempfile.TemporaryDirectory() as temporary:
            tree = self.make_tree(temporary, hidden=hiding)
            result = taskpack.run_tests_with_runner(
                tree, "tests/test_hidden.py", "ab" * 32)
        self.assertFalse(result["accepted"])
        self.assertEqual(result["outcome"], "TAMPERED")
        self.assertIn("TEST_ID_SET_MISMATCH", result["reason"])
        self.assertIn("missing=", result["reason"])

    def test_discovery_mode_matches_the_static_id_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            tree = self.make_tree(temporary)
            (tree / "tests" / "test_hidden.py").write_text(GOOD_VISIBLE_TESTS)
            result = taskpack.run_tests_with_runner(tree, None, "ab" * 32)
        self.assertTrue(result["accepted"], result["reason"])
        self.assertEqual(result["outcome"], "PASS")
        self.assertEqual(result["counts"]["ran"], 3)

    def test_runner_help_documents_the_reuse_call(self):
        run = subprocess.run(
            [sys.executable, str(PILOT / "test_runner.py"), "--help"],
            capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("run_tests_with_runner", run.stdout)
        self.assertIn("--nonce-fd", run.stdout)
        self.assertIn("--result-fd", run.stdout)
        self.assertIn("nonce_mac", run.stdout)


class TempDirAliasTests(unittest.TestCase):
    """P2-1: the sandbox profile and every phase path are resolved with realpath."""

    def test_sandbox_profile_resolves_a_symlinked_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            real = Path(temporary) / "real"
            real.mkdir()
            alias = Path(temporary) / "alias"
            os.symlink(real, alias)
            profile = taskpack._sandbox_profile(alias / "phase", alias)
        self.assertIn(str(Path(os.path.realpath(real)) / "phase"), profile)
        self.assertIn('(subpath "%s/runner")' % os.path.realpath(real), profile)
        self.assertNotIn(str(alias), profile,
                         "an unresolved symlink in the profile is what broke P2-1")

    def test_good_package_passes_when_tmpdir_is_a_symlinked_alias(self):
        with tempfile.TemporaryDirectory() as temporary:
            real = Path(temporary) / "real-tmp"
            real.mkdir()
            alias = Path(temporary) / "alias-tmp"
            os.symlink(real, alias)
            pkg = build_package(temporary)
            with mock.patch.dict(os.environ, {"TMPDIR": str(alias)}), \
                    mock.patch.object(tempfile, "tempdir", None):
                verdict = taskpack.verify_package(pkg, allow_unsandboxed=True)
        self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])
        if SANDBOX:
            self.assertEqual(verdict["isolation"], "SANDBOX_EXEC")

    def test_good_package_passes_under_the_darwin_user_temp_dir(self):
        if sys.platform != "darwin":
            self.skipTest("the macOS default TMPDIR does not exist on this platform")
        probe = subprocess.run(["getconf", "DARWIN_USER_TEMP_DIR"],
                               capture_output=True, text=True)
        default = probe.stdout.strip()
        if probe.returncode != 0 or not default or not os.path.isdir(default):
            self.skipTest("getconf DARWIN_USER_TEMP_DIR gave no usable directory: %r"
                          % probe.stdout.strip())
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            with mock.patch.dict(os.environ, {"TMPDIR": default}), \
                    mock.patch.object(tempfile, "tempdir", None):
                verdict = taskpack.verify_package(pkg, allow_unsandboxed=True)
        self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])


if __name__ == "__main__":
    unittest.main()
