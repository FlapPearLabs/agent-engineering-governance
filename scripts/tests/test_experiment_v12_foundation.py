"""Material-only tests for the V1.2 experiment foundation (non-canonical).

SCOPE (deliberately narrow): this module verifies the consistency of the
EXPERIMENT MATERIAL under `experiments/v1.2/` -- not product behaviour, not
canonical policy, and not any claim about the V1.2 hypotheses themselves:

  * `cases.yaml`         -- authored-subset structure: 8-12 cases, unique ids,
                            required fields per case, task_class and
                            failure_family inside the declared sets, every
                            source_ref resolving to a real repository path.
  * `evidence-lineage.md` -- H1..H4 carry the five lineage fields; the
                            CURRENT_STATUS values stay inside the declared
                            four-value vocabulary; the next-experiment section
                            lists all shadow observation signals.
  * `metrics.md`         -- the three metric groups and their member names are
                            present; unobservable metrics are explicitly
                            marked instead of guessed.
  * `README.md`          -- charter statements present (control, non-canonical,
                            not-established, promotion/rollback, external vs
                            local, mechanization-vs-text).

Negative controls: the manifest checker is exercised against four damaged
copies (broken source_ref, invalid task_class, duplicate id, missing field)
so that a checker which cannot fail is not mistaken for a guard.

Stdlib only (CI provisions ruff alone). Run with:
    python3 -m unittest scripts.tests.test_experiment_v12_foundation -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
V12 = ROOT / "experiments" / "v1.2"

TASK_CLASSES = {"MICRO", "LOW", "NORMAL", "STRUCTURAL", "HIGH"}
FAILURE_FAMILIES = {
    "fake_red",
    "false_pass",
    "stale_review",
    "speculative_abstraction",
    "architecture_drift",
    "duplicate_owner",
    "repair_loop",
    "recovery_failure",
    "mechanical_escape",
}
REQUIRED_COVERAGE_FAMILIES = {
    "fake_red",
    "false_pass",
    "stale_review",
    "architecture_drift",
    "speculative_abstraction",
    "duplicate_owner",
    "repair_loop",
    "recovery_failure",
}
CANDIDATE_STATUSES = {
    "IDEA_ONLY",
    "LOCAL_FAILURE_OBSERVED",
    "EXPERIMENT_CANDIDATE",
    "LOCALLY_VALIDATED",
}
LINEAGE_FIELDS = (
    "CANDIDATE = ",
    "LOCAL_FAILURE_EVIDENCE = ",
    "EXTERNAL_SUPPORT = ",
    "CURRENT_HYPOTHESIS = ",
    "CURRENT_STATUS = ",
)
SHADOW_SIGNALS = (
    "NEW_MODULE",
    "NEW_DIRECTORY",
    "NEW_PACKAGE",
    "NEW_DEPENDENCY",
    "NEW_PUBLIC_INTERFACE",
    "NEW_STATE_OWNER",
    "NEW_PERSISTENCE_SURFACE",
    "CROSS_BOUNDARY_DEPENDENCY",
)

_CASE_START = re.compile(r"^  - id: ([A-Za-z0-9][A-Za-z0-9._-]*)\s*$", re.M)
_CASE_ID = re.compile(r"^c\d{2}-[a-z0-9-]+$")


def _read(rel: str) -> str:
    return (V12 / rel).read_text(encoding="utf-8")


def _simple_field(block: str, key: str):
    match = re.search(rf"^    {re.escape(key)}:[ \t]*(.+?)\s*$", block, re.M)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    return value


def _scalar_body(block: str, key: str) -> str:
    match = re.search(rf"^    {re.escape(key)}:[ \t]*\|[ \t]*$", block, re.M)
    if not match:
        return ""
    lines = []
    for line in block[match.end():].splitlines():
        if not line.strip():
            continue
        if line.startswith("      "):
            lines.append(line.strip())
        else:
            break
    return "\n".join(lines)


def case_problems(text: str) -> list:
    """Structural problems of the cases manifest; empty list = clean.

    Factored out so the negative controls run the SAME checks over damaged
    copies -- a validator that cannot fail proves nothing.
    """
    starts = list(_CASE_START.finditer(text))
    problems = []
    if not 8 <= len(starts) <= 12:
        problems.append(f"case count {len(starts)} outside 8..12")
    ids = [match.group(1) for match in starts]
    if len(ids) != len(set(ids)):
        problems.append("duplicate case ids")
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start():end]
        case_id = match.group(1)
        if not _CASE_ID.match(case_id):
            problems.append(f"{case_id}: id not in cNN-slug form")
        for field in ("source_ref", "task_class", "failure_family"):
            value = _simple_field(block, field)
            if not value:
                problems.append(f"{case_id}: missing {field}")
            elif field == "task_class" and value not in TASK_CLASSES:
                problems.append(f"{case_id}: task_class {value!r} not allowed")
            elif field == "failure_family" and value not in FAILURE_FAMILIES:
                problems.append(f"{case_id}: failure_family {value!r} not allowed")
            elif field == "source_ref":
                for part in value.split(";"):
                    ref = part.split("#", 1)[0].strip()
                    if ref and not (ROOT / ref).exists():
                        problems.append(f"{case_id}: source_ref {ref!r} missing")
        for field in ("historical_failure", "must_catch", "false_success_condition"):
            if not _scalar_body(block, field):
                problems.append(f"{case_id}: empty {field}")
    return problems


class CasesManifestTests(unittest.TestCase):
    """The benchmark seeds must be real, complete and machine-checkable."""

    def test_manifest_is_structurally_clean(self):
        problems = case_problems(_read("cases.yaml"))
        self.assertEqual([], problems, f"cases.yaml problems: {problems}")

    def test_task_classes_cover_the_required_spread(self):
        text = _read("cases.yaml")
        classes = {
            _simple_field(block, "task_class")
            for block in _split_blocks(text)
        }
        missing = {"MICRO", "LOW", "NORMAL", "STRUCTURAL", "HIGH"} - classes
        self.assertEqual(set(), missing, f"task classes missing: {missing}")

    def test_failure_families_cover_the_required_spread(self):
        text = _read("cases.yaml")
        families = {
            _simple_field(block, "failure_family")
            for block in _split_blocks(text)
        }
        missing = REQUIRED_COVERAGE_FAMILIES - families
        self.assertEqual(set(), missing, f"families missing: {missing}")

    def test_damaged_manifests_are_rejected(self):
        """Negative controls: four damaged copies must each be rejected."""
        original = _read("cases.yaml")
        self.assertEqual([], case_problems(original),
                         "the pristine manifest must pass before mutation")
        mutations = {
            "broken source_ref": original.replace(
                '    source_ref: "audit/PAIN_TO_POLICY_MAP_V2.md#P07"',
                '    source_ref: "audit/NO_SUCH_FILE.md"'),
            "invalid task_class": original.replace(
                "    task_class: NORMAL", "    task_class: EXTREME"),
            "duplicate id": original.replace(
                "c02-test-double-green-real-entry-broken",
                "c01-weak-red-harness-failure"),
            "missing failure_family": original.replace(
                "    failure_family: fake_red\n", ""),
        }
        for name, mutated in mutations.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(original, mutated,
                                    "mutation must change the text")
                self.assertNotEqual([], case_problems(mutated),
                                    "damaged manifest must be rejected")


def _split_blocks(text: str) -> list:
    starts = list(_CASE_START.finditer(text))
    blocks = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        blocks.append(text[match.start():end])
    return blocks


class EvidenceLineageTests(unittest.TestCase):
    """H1-H4 must stay inside their declared status vocabulary."""

    def test_candidates_carry_all_lineage_fields(self):
        text = _read("evidence-lineage.md")
        for handle in ("H1", "H2", "H3", "H4"):
            self.assertIn(f"### {handle} ", text)
        for label in LINEAGE_FIELDS:
            self.assertEqual(4, text.count(label),
                             f"{label!r} must appear exactly once per candidate")

    def test_status_values_stay_in_the_declared_vocabulary(self):
        text = _read("evidence-lineage.md")
        values = re.findall(r"CURRENT_STATUS = ([A-Z_]+)", text)
        self.assertEqual(4, len(values), f"status values found: {values}")
        for value in values:
            self.assertIn(value, CANDIDATE_STATUSES)

    def test_next_experiment_lists_shadow_signals(self):
        text = _read("evidence-lineage.md")
        self.assertIn("STRUCTURE_DELTA_SHADOW", text)
        for signal in SHADOW_SIGNALS:
            self.assertIn(signal, text)
        self.assertIn("不接入 CI", text)
        self.assertIn("不 block merge", text)


class MetricsTests(unittest.TestCase):
    """The metrics file defines the measured quantities, not fake numbers."""

    def test_groups_and_metrics_present(self):
        text = _read("metrics.md")
        for token in ("QUALITY", "COST", "GOVERNANCE COST"):
            self.assertIn(token, text)
        for metric in ("high-value defects escaped", "invalid PASS",
                       "architecture drift", "tokens", "model calls",
                       "tool calls", "wall clock", "human interruptions",
                       "hot prompt bytes", "docs loaded", "skills loaded",
                       "reviews run", "unique high-value findings"):
            self.assertIn(metric, text)

    def test_unobservable_metrics_are_marked(self):
        text = _read("metrics.md")
        self.assertGreaterEqual(text.count("NOT_OBSERVABLE"), 3)
        self.assertIn("不得估算", text)


class CharterTests(unittest.TestCase):
    """The README must keep stating what this directory is and is not."""

    def test_readme_states_the_charter(self):
        text = _read("README.md")
        for phrase in ("canonical control", "non-canonical", "尚未成立",
                       "PROMOTION", "ROLLBACK",
                       "EXTERNAL_EVIDENCE != LOCAL_PROOF",
                       "MECHANIZATION REPLACES TEXT"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
