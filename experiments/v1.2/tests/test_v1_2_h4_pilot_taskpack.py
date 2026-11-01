"""Acceptance tests for the H4 pilot task-package verifier (pilot/taskpack.py).

Every rejection case in `PILOT_SPEC.md` "Package verifier" has a test here, plus the
seal contract and the isolation rule (package code runs only in a temp copy). The good
package is built by hand inside a temporary directory; nothing in this file needs a
model, the network, git history, or a runs root.
"""
import difflib
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / "experiments/v1.2/h4-micro-low-ablation/pilot"
SPEC = importlib.util.spec_from_file_location("h4_taskpack", PILOT / "taskpack.py")
taskpack = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(taskpack)

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
            verdict = taskpack.verify_package(pkg)
            self.assertEqual(verdict["overall"], "PASS", verdict["reasons"])
            for number in range(1, 7):
                self.assertEqual(check(verdict, number)["status"], "PASS", reasons(verdict, number))
            self.assertEqual(check(verdict, 7)["status"], "NOT_SEALED")
            self.assertEqual(verdict["seal"], "NOT_SEALED")
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

            sealed = taskpack.verify_package(pkg)
            self.assertEqual(sealed["overall"], "PASS", sealed["reasons"])
            self.assertEqual(sealed["seal"], "SEALED")
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


class CliTests(unittest.TestCase):
    def test_cli_verify_and_seal(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            verify = subprocess.run([sys.executable, str(PILOT / "taskpack.py"), "verify", str(pkg)],
                                    capture_output=True, text=True)
            self.assertEqual(verify.returncode, 0, verify.stdout + verify.stderr)
            self.assertEqual(json.loads(verify.stdout)["overall"], "PASS")

            seal = subprocess.run([sys.executable, str(PILOT / "taskpack.py"), "seal", str(pkg)],
                                  capture_output=True, text=True)
            self.assertEqual(seal.returncode, 0, seal.stdout + seal.stderr)
            self.assertIs(json.loads(seal.stdout)["sealed"], True)
            self.assertTrue((pkg / "SEAL.json").is_file())

            (pkg / "base" / "src" / "extra.py").write_text("X = 1\n")
            tampered = subprocess.run([sys.executable, str(PILOT / "taskpack.py"), "verify", str(pkg)],
                                      capture_output=True, text=True)
            self.assertEqual(tampered.returncode, 1)
            verdict = json.loads(tampered.stdout)
            self.assertEqual(verdict["overall"], "FAIL")
            self.assertEqual(verdict["seal"], "BROKEN")

    def test_cli_seal_refuses_a_bad_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            pkg = build_package(temporary)
            (pkg / "notes.txt").write_text("scratch\n")
            seal = subprocess.run([sys.executable, str(PILOT / "taskpack.py"), "seal", str(pkg)],
                                  capture_output=True, text=True)
            self.assertEqual(seal.returncode, 1)
            self.assertIs(json.loads(seal.stdout)["sealed"], False)
            self.assertFalse((pkg / "SEAL.json").exists())


if __name__ == "__main__":
    unittest.main()
