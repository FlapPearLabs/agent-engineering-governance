"""Material-integrity checks for the V1.2 experiment directory (non-canonical).

SCOPE (deliberately narrow): verify that the experiment MATERIAL under
`experiments/v1.2/` is internally consistent -- not that it satisfies any
experiment-shape quota. One-off experiment sampling choices (how many cases
exist, which task classes or failure families happen to be present) are NOT
frozen here: `TEMPORARY EXPERIMENT SHAPE != PERMANENT GOVERNANCE INVARIANT`;
the sample evolves per experiment round.

Kept (real data integrity):
  * cases.yaml -- case ids unique and well-formed; required fields non-empty;
    source_ref resolves to a real in-repo path; task_class / failure_family
    stay inside their declared domains; damaged manifests actually fail
    (negative controls below).
  * evidence-lineage.md -- every candidate block carries its five lineage
    fields; CURRENT_STATUS stays inside the declared four-value vocabulary;
    the STRUCTURE_DELTA_SHADOW section keeps its not-wired boundary.
  * README.md -- the non-canonical boundary statements are present.
  * metrics.md -- unobservable quantities stay marked, not guessed.

This file lives INSIDE the experiment directory on purpose: reshaping or
deleting the experiment must not leave a permanent maintenance obligation
in the repository's canonical CI test surface (`scripts/tests`).

Stdlib only. Run with:
    python3 -m unittest discover -s experiments/v1.2/tests -v
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
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

_CASE_START = re.compile(r"^  - id: ([A-Za-z0-9][A-Za-z0-9._-]*)\s*$", re.M)
_CASE_ID = re.compile(r"^c\d{2}-[a-z0-9-]+$")
_CANDIDATE_BLOCK = re.compile(r"^### H\d+ ", re.M)
_SIMPLE_FIELDS = ("source_ref", "task_class", "failure_family")
_PROSE_FIELDS = ("historical_failure", "must_catch", "false_success_condition")


def _read(rel: str) -> str:
    return (V12 / rel).read_text(encoding="utf-8")


def _simple_field(block: str, key: str):
    match = re.search(rf"^    {re.escape(key)}:[ \t]*(.+?)\s*$", block, re.M)
    if not match:
        return None
    value = match.group(1).strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        value = value[1:-1]
    return value or None


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
    """Data-integrity problems of the cases manifest; empty list = clean.

    Deliberately does NOT enforce case count or category coverage: sample
    size and composition are experiment shape, free to change per round.
    Factored out so the negative controls run the SAME checks over damaged
    copies -- a validator that cannot fail proves nothing.
    """
    starts = list(_CASE_START.finditer(text))
    problems = []
    if not starts:
        problems.append("no cases found")
    ids = [match.group(1) for match in starts]
    if len(ids) != len(set(ids)):
        problems.append("duplicate case ids")
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start():end]
        case_id = match.group(1)
        if not _CASE_ID.match(case_id):
            problems.append(f"{case_id}: id not in cNN-slug form")
        for field in _SIMPLE_FIELDS:
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
        for field in _PROSE_FIELDS:
            if not _scalar_body(block, field):
                problems.append(f"{case_id}: empty {field}")
    return problems


class ManifestIntegrityTests(unittest.TestCase):
    """The seed corpus must be well-formed and machine-checkable."""

    def test_manifest_is_structurally_clean(self):
        problems = case_problems(_read("cases.yaml"))
        self.assertEqual([], problems, f"cases.yaml problems: {problems}")

    def test_damaged_manifests_are_rejected(self):
        """Negative controls: five damaged copies must each be rejected."""
        original = _read("cases.yaml")
        self.assertEqual([], case_problems(original),
                         "the pristine manifest must pass before mutation")
        mutations = {
            "broken source_ref": original.replace(
                '    source_ref: "audit/PAIN_TO_POLICY_MAP_V2.md#P07"',
                '    source_ref: "audit/NO_SUCH_FILE.md"'),
            "dropped source_ref": original.replace(
                '    source_ref: "audit/PAIN_TO_POLICY_MAP_V2.md#P07"\n', ""),
            "invalid task_class": original.replace(
                "    task_class: NORMAL", "    task_class: EXTREME"),
            "invalid failure_family": original.replace(
                "    failure_family: fake_red", "    failure_family: invented"),
            "duplicate id": original.replace(
                "c02-test-double-green-real-entry-broken",
                "c01-weak-red-harness-failure"),
        }
        for name, mutated in mutations.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(original, mutated,
                                    "mutation must change the text")
                self.assertNotEqual([], case_problems(mutated),
                                    "damaged manifest must be rejected")


class BoundaryTests(unittest.TestCase):
    """The experiment must stay visibly non-canonical and unwired."""

    def test_readme_states_the_non_canonical_boundary(self):
        text = _read("README.md")
        for phrase in ("canonical control", "non-canonical", "尚未成立"):
            self.assertIn(phrase, text)

    def test_candidate_blocks_carry_their_lineage_fields(self):
        text = _read("evidence-lineage.md")
        blocks = _CANDIDATE_BLOCK.split(text)[1:]
        self.assertGreaterEqual(len(blocks), 1, "no candidate blocks found")
        for label in LINEAGE_FIELDS:
            for index, block in enumerate(blocks):
                with self.subTest(label=label, block=index):
                    self.assertIn(label, block)

    def test_candidate_statuses_stay_in_the_declared_vocabulary(self):
        text = _read("evidence-lineage.md")
        values = re.findall(r"CURRENT_STATUS = ([A-Z_]+)", text)
        self.assertGreaterEqual(len(values), 1, "no CURRENT_STATUS found")
        for value in values:
            self.assertIn(value, CANDIDATE_STATUSES)

    def test_structure_delta_shadow_is_not_wired(self):
        text = _read("evidence-lineage.md")
        self.assertIn("STRUCTURE_DELTA_SHADOW", text)
        self.assertIn("不接入 CI", text)
        self.assertIn("不 block merge", text)

    def test_unobservable_metrics_stay_marked(self):
        text = _read("metrics.md")
        self.assertIn("NOT_OBSERVABLE", text)


if __name__ == "__main__":
    unittest.main()
