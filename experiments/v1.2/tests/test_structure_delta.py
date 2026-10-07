"""Detector-level tests for STRUCTURE_DELTA_SHADOW v0 (experiments/v1.2/structure_delta.py).

SCOPE (deliberately narrow): verify the v0 detector implements exactly the
three frozen v1 signal definitions (`replay/README.md` is the oracle) and that
unresolvable inputs fail loudly instead of producing a plausible-looking
result. Detector-level negative controls live here -- synthetic fixtures only,
no real-clone dependency:

  * stale / unknown / non-commit base -> hard error, never a silent result
  * rename under `--no-renames`       -> frozen semantics: delete + add
  * requirements blank / # comments   -> not counted; duplicates counted per line
  * nested directory prefixes         -> every ancestor prefix counts
  * non-requirements manifests        -> out of family for v1 (pyproject.toml etc.)
  * wrong-but-existing base           -> the comparison layer flags MISMATCH
  * non-v1 signal in expected counts  -> rejected, never silently skipped

Also: the focused corpus reader must load exactly the ready `case_id` anchors
of `replay/cases.yaml` (no case silently skipped, no `not_replay_ready` entry
loaded); a misplaced section boundary and any unparseable expected-signal
entry are rejected instead of yielding a false-green.

This file lives INSIDE the experiment directory on purpose: reshaping or
deleting the experiment must not leave a permanent maintenance obligation in
the repository's canonical CI test surface (`scripts/tests`).

Stdlib only (plus git as an external process). Run with:
    python3 -m unittest discover -s experiments/v1.2/tests -v
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V12 = ROOT / "experiments" / "v1.2"
sys.path.insert(0, str(V12))

import structure_delta  # noqa: E402  (path set above; experiment-local import)

CASE_ID_RE = re.compile(r"^  - case_id: (r\d\d-[a-z0-9-]+)$", re.M)


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


class _Fixture:
    """A throwaway git repository in the system temp dir."""

    def __enter__(self) -> Path:
        self._dir = tempfile.mkdtemp(prefix="sd-v0-test-")
        repo = Path(self._dir)
        _git(repo, "init", "-q")
        _git(repo, "config", "user.name", "sd-v0-test")
        _git(repo, "config", "user.email", "sd-v0-test@example.invalid")
        return repo

    def __exit__(self, *exc_info) -> None:
        shutil.rmtree(self._dir, ignore_errors=True)


def _write(repo: Path, relpath: str, content: str) -> None:
    path = repo / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit(repo: Path, message: str) -> str:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _fixture_case(repo: Path, base: str, candidate: str, expected: dict) -> dict:
    return {
        "case_id": "synthetic-fixture",
        "source_repository": "local/fixture",
        "base_sha": base,
        "candidate_sha": candidate,
        "expected_signals": expected,
    }


class SignalDefinitionTests(unittest.TestCase):
    """The three v1 signals against synthetic real diffs (frozen semantics)."""

    def test_new_file_counts_added_paths_only(self):
        with _Fixture() as repo:
            _write(repo, "keep.txt", "one\n")
            base = _commit(repo, "base")
            _write(repo, "keep.txt", "two\n")  # modified, not new
            _write(repo, "a.txt", "a\n")
            _write(repo, "b.txt", "b\n")
            candidate = _commit(repo, "add a and b")
            self.assertEqual(2, structure_delta.count_new_files(str(repo), base, candidate))

    def test_new_file_zero_for_modification_only(self):
        with _Fixture() as repo:
            _write(repo, "keep.txt", "one\n")
            base = _commit(repo, "base")
            _write(repo, "keep.txt", "two\n")
            candidate = _commit(repo, "modify")
            self.assertEqual(0, structure_delta.count_new_files(str(repo), base, candidate))

    def test_new_directory_counts_every_ancestor_prefix(self):
        with _Fixture() as repo:
            _write(repo, "readme.txt", "x\n")
            base = _commit(repo, "base")
            _write(repo, "a/b/c/file.txt", "x\n")
            candidate = _commit(repo, "nested add")
            # a/ , a/b/ , a/b/c/ -- all ancestors count, not just the deepest one
            self.assertEqual(
                3, structure_delta.count_new_directories(str(repo), base, candidate)
            )

    def test_new_directory_zero_when_parent_already_exists(self):
        with _Fixture() as repo:
            _write(repo, "existing/one.txt", "x\n")
            base = _commit(repo, "base")
            _write(repo, "existing/two.txt", "x\n")
            candidate = _commit(repo, "sibling add")
            self.assertEqual(
                0, structure_delta.count_new_directories(str(repo), base, candidate)
            )

    def test_new_dependency_skips_blank_and_comment_lines(self):
        with _Fixture() as repo:
            _write(repo, "readme.txt", "x\n")
            base = _commit(repo, "base")
            _write(repo, "requirements.txt", "# pinned versions\n\npkgA==1.0\n\n# notes\n")
            candidate = _commit(repo, "add requirements")
            self.assertEqual(
                1, structure_delta.count_new_dependencies(str(repo), base, candidate)
            )
            # signals are independent: the new manifest is also a NEW_FILE
            self.assertEqual(1, structure_delta.count_new_files(str(repo), base, candidate))

    def test_new_dependency_counts_duplicate_lines_each(self):
        with _Fixture() as repo:
            _write(repo, "readme.txt", "x\n")
            base = _commit(repo, "base")
            _write(repo, "requirements.txt", "pkgA==1.0\npkgA==1.0\n")
            candidate = _commit(repo, "duplicate declaration")
            self.assertEqual(
                2, structure_delta.count_new_dependencies(str(repo), base, candidate)
            )

    def test_new_dependency_ignores_deleted_lines(self):
        with _Fixture() as repo:
            _write(repo, "requirements.txt", "old==1\ndrop==2\n")
            base = _commit(repo, "base")
            _write(repo, "requirements.txt", "old==1\nnew==3\n")
            candidate = _commit(repo, "swap one declaration")
            self.assertEqual(
                1, structure_delta.count_new_dependencies(str(repo), base, candidate)
            )

    def test_non_requirements_manifests_are_out_of_family(self):
        with _Fixture() as repo:
            _write(repo, "readme.txt", "x\n")
            base = _commit(repo, "base")
            _write(repo, "pyproject.toml", '[project]\nname = "x"\n')
            _write(repo, "package.json", '{"dependencies": {"a": "1.0.0"}}\n')
            candidate = _commit(repo, "other ecosystems")
            self.assertEqual(
                0, structure_delta.count_new_dependencies(str(repo), base, candidate)
            )
            # ...while NEW_FILE still sees both added manifests
            self.assertEqual(2, structure_delta.count_new_files(str(repo), base, candidate))

    def test_rename_is_delete_plus_add_under_no_renames(self):
        with _Fixture() as repo:
            _write(repo, "old.txt", "x\n")
            base = _commit(repo, "base")
            _git(repo, "mv", "old.txt", "new.txt")
            candidate = _commit(repo, "rename")
            # v0 counts with --no-renames: the new path has status A
            self.assertEqual(1, structure_delta.count_new_files(str(repo), base, candidate))
            self.assertEqual(
                0, structure_delta.count_new_directories(str(repo), base, candidate)
            )


class NegativeControlTests(unittest.TestCase):
    """Inputs that cannot be honestly resolved must never yield a normal result."""

    def test_unknown_base_or_candidate_raises(self):
        with _Fixture() as repo:
            _write(repo, "a.txt", "x\n")
            head = _commit(repo, "base")
            bogus = "0" * 40
            with self.assertRaises(structure_delta.StructureDeltaError):
                structure_delta.extract_signals(str(repo), bogus, head)
            with self.assertRaises(structure_delta.StructureDeltaError):
                structure_delta.extract_signals(str(repo), head, bogus)

    def test_non_commit_revision_raises(self):
        with _Fixture() as repo:
            _write(repo, "a.txt", "x\n")
            head = _commit(repo, "base")
            tree = _git(repo, "rev-parse", "HEAD^{tree}")
            with self.assertRaises(structure_delta.StructureDeltaError):
                structure_delta.extract_signals(str(repo), tree, head)

    def test_wrong_but_existing_base_is_not_silently_accepted(self):
        with _Fixture() as repo:
            _write(repo, "readme.txt", "x\n")
            c0 = _commit(repo, "c0")
            _write(repo, "f1.txt", "x\n")
            c1 = _commit(repo, "c1")
            _write(repo, "f2.txt", "x\n")
            _write(repo, "f3.txt", "x\n")
            c2 = _commit(repo, "c2")
            repo_map = {"local/fixture": str(repo)}

            right = structure_delta.replay_reports(
                [_fixture_case(repo, c1, c2, {"NEW_FILE": 2})], repo_map
            )
            self.assertEqual(1, right["matched"])
            self.assertEqual(0, right["mismatched"])

            # same expected counts, but a stale base one hop too early:
            # the comparison layer must flag it, not pass it through
            wrong = structure_delta.replay_reports(
                [_fixture_case(repo, c0, c2, {"NEW_FILE": 2})], repo_map
            )
            self.assertEqual(0, wrong["matched"])
            self.assertEqual(1, wrong["mismatched"])
            self.assertEqual(3, wrong["cases"][0]["actual"]["NEW_FILE"])

    def test_false_positive_and_false_negative_bookkeeping(self):
        with _Fixture() as repo:
            _write(repo, "readme.txt", "x\n")
            base = _commit(repo, "base")
            _write(repo, "f1.txt", "x\n")
            candidate = _commit(repo, "one new file")
            repo_map = {"local/fixture": str(repo)}

            false_positive = structure_delta.replay_reports(
                [_fixture_case(repo, base, candidate, {})], repo_map
            )
            self.assertEqual(1, false_positive["false_positive_signal_count"])
            self.assertEqual(0, false_positive["false_negative_signal_count"])
            self.assertEqual(1, false_positive["mismatched"])

            false_negative = structure_delta.replay_reports(
                [_fixture_case(repo, base, candidate, {"NEW_FILE": 2})], repo_map
            )
            self.assertEqual(0, false_negative["false_positive_signal_count"])
            self.assertEqual(1, false_negative["false_negative_signal_count"])
            self.assertEqual(1, false_negative["mismatched"])

    def test_non_v1_signal_in_expected_counts_is_rejected(self):
        """A signal the detector does not implement must fail loudly, not be ignored."""
        with _Fixture() as repo:
            _write(repo, "a.txt", "x\n")
            head = _commit(repo, "base")
            repo_map = {"local/fixture": str(repo)}
            with self.assertRaises(structure_delta.StructureDeltaError):
                structure_delta.replay_reports(
                    [_fixture_case(repo, head, head, {"NEW_MODULE": 1})], repo_map
                )
        # ...and the parse-time guard rejects it directly in a manifest
        mutated = (
            "version: 1\ncases:\n"
            "  - case_id: r99-synthetic\n"
            "    source_repository: local/fixture\n"
            "    base_sha: " + "0" * 40 + "\n"
            "    candidate_sha: " + "1" * 40 + "\n"
            "    expected_mechanical_signals:\n"
            "      - signal: NEW_MODULE\n"
            "        count: 1\n"
        )
        tmp = Path(tempfile.mkdtemp(prefix="sd-v0-cases-"))
        try:
            path = tmp / "cases.yaml"
            path.write_text(mutated, encoding="utf-8")
            with self.assertRaises(structure_delta.StructureDeltaError):
                structure_delta.load_replay_cases(path)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class CorpusReaderTests(unittest.TestCase):
    """The focused reader must see every ready case of the real corpus."""

    CASES = V12 / "replay" / "cases.yaml"

    def test_all_ready_case_anchors_are_loaded(self):
        text = self.CASES.read_text(encoding="utf-8")
        ready_text = text.split("\nnot_replay_ready:", 1)[0]
        anchor_ids = CASE_ID_RE.findall(ready_text)
        self.assertGreaterEqual(len(anchor_ids), 1, "corpus must have ready cases")
        cases = structure_delta.load_replay_cases(self.CASES)
        self.assertEqual(anchor_ids, [case["case_id"] for case in cases])
        for case in cases:
            self.assertRegex(case["base_sha"], r"^[0-9a-f]{40}$")
            self.assertRegex(case["candidate_sha"], r"^[0-9a-f]{40}$")
            self.assertTrue(case["source_repository"])
            unknown = set(case["expected_signals"]) - set(structure_delta.SUPPORTED_SIGNALS)
            self.assertEqual(set(), unknown)

    def test_not_replay_ready_entries_are_never_loaded(self):
        cases = structure_delta.load_replay_cases(self.CASES)
        ids = [case["case_id"] for case in cases]
        self.assertNotIn("909ffb02", " ".join(ids))
        repos = {case["source_repository"] for case in cases}
        self.assertNotIn("FlapPearLabs/webcodex", repos)

    def test_misplaced_section_boundary_is_rejected(self):
        """A not_replay_ready marker ahead of ready cases must fail, not truncate."""
        original = self.CASES.read_text(encoding="utf-8")
        mutated = original.replace(
            "\n  - case_id: r05-",
            "\nnot_replay_ready: injected-before-r05\n  - case_id: r05-",
            1,
        )
        self.assertNotEqual(original, mutated, "mutation must change the text")
        self._assert_reader_rejects(mutated)

    def test_malformed_expected_signal_entries_are_rejected(self):
        """Entries that fail to parse must not silently read as an empty oracle."""
        original = self.CASES.read_text(encoding="utf-8")
        mutations = {
            "quoted signal name": original.replace(
                "      - signal: NEW_FILE\n        count: 3",
                '      - signal: "NEW_FILE"\n        count: 3',
                1,
            ),
            "count before signal": original.replace(
                "      - signal: NEW_FILE\n        count: 3",
                "      - count: 3\n        signal: NEW_FILE",
                1,
            ),
        }
        for name, mutated in mutations.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(original, mutated, "mutation must change the text")
                self._assert_reader_rejects(mutated)

    def _assert_reader_rejects(self, mutated_text: str) -> None:
        tmp = Path(tempfile.mkdtemp(prefix="sd-v0-corpus-"))
        try:
            path = tmp / "cases.yaml"
            path.write_text(mutated_text, encoding="utf-8")
            with self.assertRaises(structure_delta.StructureDeltaError):
                structure_delta.load_replay_cases(path)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
