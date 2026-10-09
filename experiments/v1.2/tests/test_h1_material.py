"""Material-integrity checks for the H1 experiment slice (non-canonical).

SCOPE (deliberately narrow, same discipline as `test_material.py`): verify the
H1 MATERIAL under `experiments/v1.2/h1-hot-context/` is internally consistent
and that its self-declared boundaries are the boundaries it actually keeps.

What is checked here is *material integrity* and *boundary honesty* only. NOT
checked, on purpose:

  * no task-count quota, no per-risk-class coverage quota, no required-finding
    list. Those are one-off experiment sampling choices and this round
    deliberately ran 1 of 4 declared tasks (environment blocked).
    `TEMPORARY EXPERIMENT SHAPE != PERMANENT GOVERNANCE INVARIANT`.
  * no assertion that the lean variant is better than the control. Round 1
    concluded `H1_RESULT = INSUFFICIENT_EVIDENCE`; freezing a directional
    expectation here would make the material able to lie in either direction.

Kept (real integrity):

  * `hot_inventory.py` keeps unobservable quantities marked, not estimated --
    `tokens` / `hot_approx_tokens` must stay `NOT_OBSERVABLE`.
  * the lean variant declares all 8 non-negotiable floor items (N1..N8) and
    does not grant permissions or create gates.
  * `results.md` states a result from the allowed three-value vocabulary and
    does not claim `PROMOTE`.
  * `results.md` does not claim GitHub evidence (commit/push/PR/CI/merge)
    that was never performed -- an UNMET `PART 23` must stay visible.
  * run records are anonymous (`RUN_A` / `RUN_B`) and contain no arm label in
    their filename.

Stdlib only. Run with:
    python3 -m unittest discover -s experiments/v1.2/tests -v
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
H1 = ROOT / "experiments" / "v1.2" / "h1-hot-context"
LEAN = H1 / "lean" / "CODEBUDDY.md"
INVENTORY = H1 / "hot_inventory.py"
TASKS = H1 / "tasks.yaml"
RESULTS = H1 / "results.md"
README = H1 / "README.md"
RUNS = H1 / "runs"

RESULT_VOCABULARY = {"INSUFFICIENT_EVIDENCE", "LEAN_NOT_BETTER", "LEAN_PROMISING"}
FLOOR_ITEMS = [f"N{i}" for i in range(1, 9)]
PROFILE_MAX_GUIDANCE_CHARS = 8000

# Run identity lives in `runs/README.md`; these are the ids it must declare.
# Kept in the test so a silent edit to either side fails loudly.
CANONICAL_RUN_IDS = (
    "RUN_B9", "RUN_K7", "RUN_M4", "RUN_P3", "RUN_Q2", "RUN_T1", "RUN_W6", "RUN_Z8",
)
SUPERSEDED_RUN_IDS = ("RUN_A", "RUN_B")
EVIDENCE_STATES = {"NOT_PUSHED", "PENDING_PR_AT_ARTIFACT_COMMIT", "MERGED"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TestH1MaterialExists(unittest.TestCase):
    def test_every_declared_artifact_exists(self):
        for rel in (
            "README.md",
            "results.md",
            "tasks.yaml",
            "hot_inventory.py",
            "lean/CODEBUDDY.md",
            "runs/RUN_A.md",
            "runs/RUN_B.md",
        ):
            with self.subTest(rel=rel):
                self.assertTrue((H1 / rel).is_file(), f"missing H1 artifact: {rel}")


class TestUnobservableQuantitiesStayMarked(unittest.TestCase):
    """The core honesty property: a metric that cannot be measured must not be guessed."""

    def test_inventory_marks_tokens_not_observable(self):
        src = _read(INVENTORY)
        self.assertIn('"NOT_OBSERVABLE"', src)
        # token counts must never be derived from character counts
        self.assertNotIn("tokens = len(", src)
        self.assertNotIn("tokens = int(", src)
        self.assertNotIn("/ 4", src.replace("24 / 4", ""))  # no chars->tokens heuristic

    def test_inventory_json_output_keeps_tokens_unobservable(self):
        proc = subprocess.run(
            [sys.executable, str(INVENTORY), "--json"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr[-2000:])
        data = json.loads(proc.stdout)
        self.assertEqual("NOT_OBSERVABLE", data["token_usage"])
        self.assertEqual("NOT_OBSERVABLE", data["control"]["hot_approx_tokens"])
        self.assertEqual("NOT_OBSERVABLE", data["variant"]["hot_approx_tokens"])


class TestInventoryProfileFidelity(unittest.TestCase):
    def test_max_guidance_chars_matches_the_declared_profile(self):
        data = json.loads(
            subprocess.run(
                [sys.executable, str(INVENTORY), "--json"],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                check=False,
            ).stdout
        )
        self.assertEqual(PROFILE_MAX_GUIDANCE_CHARS, data["profile"]["MAX_GUIDANCE_CHARS"])
        self.assertTrue(data["profile"]["is_profile_fact_not_constant"])

    def test_control_guidance_head_is_truncated_but_variant_is_not(self):
        """The round's central pre-registered observation.

        If this inverts, the control arm no longer represents the canonical
        baseline and any comparison built on it is void.
        """
        data = json.loads(
            subprocess.run(
                [sys.executable, str(INVENTORY), "--json"],
                capture_output=True,
                text=True,
                cwd=str(ROOT),
                check=False,
            ).stdout
        )
        self.assertTrue(
            data["control"]["guidance_delivery"]["cut_line"],
            "control AGENTS.md must be truncated at MAX_GUIDANCE_CHARS",
        )
        self.assertGreater(
            data["control"]["guidance_delivery"]["dropped_js_chars"], 0
        )
        self.assertTrue(
            data["reduction"]["variant_fully_delivered"],
            "the lean variant must be fully delivered, else it is not a cheaper HOT",
        )

    def test_selftest_passes(self):
        proc = subprocess.run(
            [sys.executable, str(INVENTORY), "--selftest"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)


class TestLeanVariantSafetyFloor(unittest.TestCase):
    """PART 6: the lean variant may relocate a floor item, never delete it."""

    def test_all_eight_floor_items_are_declared(self):
        text = _read(LEAN)
        for item in FLOOR_ITEMS:
            with self.subTest(item=item):
                self.assertRegex(text, rf"\b{item}\b", f"floor item {item} missing")

    def test_no_floor_item_is_waived(self):
        text = _read(LEAN).upper()
        for forbidden in ("FLOOR WAIVED", "FLOOR DISABLED", "NO NEED TO READ"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)

    def test_variant_grants_no_permission_and_creates_no_gate(self):
        text = _read(LEAN)
        # it must not claim authority, and must yield to canonical on conflict
        self.assertIn("不是权威层", text)
        self.assertIn("冲突时**以 canonical 为准**", text)
        # no gate-creating or gate-exempting language
        for forbidden in ("gate 豁免", "SKIP THE GATE", "BYPASS"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
        # `授予权限` is checked per-occurrence, not by substring: the variant is
        # allowed to say it does NOT grant permissions -- that is the sentence
        # that makes the bound honest. A bare substring test fails on the
        # negation ("本文件**不**授予权限"), which is a defect in the assertion,
        # not in the material. Every occurrence must therefore be negated.
        negated = re.compile(r"(?:不|未|禁止|无)(?:\s|\*)*授予权限")
        for match in re.finditer(r"授予权限", text):
            line_start = text.rfind("\n", 0, match.start()) + 1
            line_end = text.find("\n", match.end())
            line = text[line_start : line_end if line_end != -1 else len(text)]
            with self.subTest(line=line.strip()):
                self.assertRegex(line, negated, f"un-negated permission grant: {line}")

    def test_routing_table_is_progressive_not_read_everything(self):
        text = _read(LEAN)
        self.assertIn("不预读全量 references", text)
        self.assertIn("不允许「先全读一遍再决定」", text)


class TestResultsHonesty(unittest.TestCase):
    def test_result_is_inside_the_allowed_vocabulary(self):
        text = _read(RESULTS)
        for line in text.splitlines():
            if line.strip().startswith("H1_RESULT ="):
                value = line.split("=", 1)[1].strip()
                with self.subTest(value=value):
                    self.assertIn(value, RESULT_VOCABULARY)
                return
        self.fail("results.md declares no H1_RESULT line")

    def test_result_is_not_promote(self):
        """Promotion belongs to later synthesis and needs multi-round evidence."""
        self.assertNotIn("H1_RESULT = PROMOTE", _read(RESULTS))

    def test_round_one_blocking_fault_is_recorded(self):
        text = _read(RESULTS)
        self.assertIn("exit 137", text)
        self.assertIn("VALID_COMPLETION = NO", text)

    def test_orchestrator_harness_defect_is_recorded(self):
        """A harness defect that voided a run pair must stay in the record."""
        text = _read(RESULTS)
        self.assertIn("harness", text)
        self.assertIn("作废", text)


class TestEvidenceClosureState(unittest.TestCase):
    """PART 23 unmet must not be dropped -- and closure must not be overclaimed.

    The state is declared explicitly so the record cannot silently drift between
    "not pushed", "PR open", and "merged". A pre-merge state must NOT carry a
    merge SHA (that would be a fabricated future fact); a merged state MUST.
    """

    def _state(self) -> tuple[str, str]:
        text = _read(RESULTS)
        matches = re.findall(r"^GITHUB_EVIDENCE_STATE\s*=\s*(\S+)\s*$", text, re.M)
        self.assertEqual(1, len(matches), "results.md must declare exactly one GITHUB_EVIDENCE_STATE")
        return matches[0], text

    def test_state_is_inside_the_allowed_vocabulary(self):
        state, _ = self._state()
        self.assertIn(state, EVIDENCE_STATES)

    def test_historical_unmet_state_is_preserved(self):
        """Round 1's unmet PART 23 is a permanent historical fact, not a transient status.

        Closing the evidence gap must not rewrite the fact that it was once open.
        """
        _, text = self._state()
        self.assertIn("PART 23 未满足", text)

    def test_merge_sha_only_exists_once_merged(self):
        state, text = self._state()
        found = re.findall(r"^EVIDENCE_MERGE_SHA\s*=\s*(\S+)\s*$", text, re.M)
        if state == "MERGED":
            self.assertEqual(1, len(found), "merged state must record exactly one merge SHA")
            self.assertRegex(found[0], r"^[0-9a-f]{40}$")
        else:
            for value in found:
                self.assertNotRegex(
                    value, r"^[0-9a-f]{40}$",
                    "a pre-merge state must not carry a merge SHA",
                )

    def test_linked_findings_carry_real_issue_numbers(self):
        """Findings opened as issues must be referenced by number, not by promise."""
        _, text = self._state()
        self.assertRegex(text, r"F1_ISSUE\s*=\s*#\d+")
        self.assertRegex(text, r"F2_ISSUE\s*=\s*#\d+")


class TestRunRegistry(unittest.TestCase):
    """VALID_RUNS must be mechanically checkable, not a claim in prose.

    The registry file is the single place that defines run identity; this class
    checks the registry and the run directory agree, and that voided runs were
    retained rather than deleted.
    """

    def test_run_directory_matches_the_declared_registry(self):
        names = sorted(p.stem for p in RUNS.glob("RUN_*.md"))
        self.assertEqual(
            sorted(CANONICAL_RUN_IDS + SUPERSEDED_RUN_IDS), names,
            "run files on disk must equal the declared registry",
        )

    def test_valid_run_count_is_eight_and_unique(self):
        self.assertEqual(8, len(CANONICAL_RUN_IDS))
        self.assertEqual(8, len(set(CANONICAL_RUN_IDS)))

    def test_superseded_records_are_not_counted_as_runs(self):
        self.assertEqual([], sorted(set(CANONICAL_RUN_IDS) & set(SUPERSEDED_RUN_IDS)))

    def test_run_filenames_carry_no_arm_label(self):
        for name in CANONICAL_RUN_IDS + SUPERSEDED_RUN_IDS:
            lowered = name.lower()
            for leak in ("control", "variant", "lean"):
                with self.subTest(name=name, leak=leak):
                    self.assertNotIn(leak, lowered)

    def test_every_valid_run_declares_a_completion_verdict(self):
        for run_id in CANONICAL_RUN_IDS:
            text = _read(RUNS / f"{run_id}.md")
            with self.subTest(run_id=run_id):
                self.assertIn("VALID_COMPLETION", text)

    def test_superseded_records_are_marked_as_superseded(self):
        for name in SUPERSEDED_RUN_IDS:
            with self.subTest(name=name):
                self.assertIn("SUPERSEDED", _read(RUNS / f"{name}.md"))
        registry = _read(RUNS / "README.md")
        for name in SUPERSEDED_RUN_IDS:
            self.assertIn(name, registry)
        self.assertIn("COUNTING_RULE", registry)

    def test_voided_runs_are_retained_in_the_record(self):
        """A discarded run must stay visible -- deleting it would hide a harness defect."""
        registry = _read(RUNS / "README.md")
        self.assertIn("INVALID_RUNS = 2", registry)
        self.assertIn("INVALID_001", registry)
        self.assertIn("INVALID_002", registry)
        self.assertIn("WRONG_EXECUTION_TARGET", registry)
        self.assertIn("TREATMENT_NOT_ESTABLISHED", registry)

    def test_lost_replay_worktrees_are_recorded_not_implied_reverifiable(self):
        """The /tmp worktrees no longer exist; the record must say so."""
        registry = _read(RUNS / "README.md")
        self.assertIn("REPLAY_WORKTREE_REVERIFIABLE_NOW = NO", registry)


class TestCanonicalUntouched(unittest.TestCase):
    """The experiment must not have edited any canonical surface."""

    def test_no_canonical_file_is_modified_in_the_worktree(self):
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain", "--",
             "AGENTS.md", "RULES.md", "references", "deployment", "scripts",
             "schemas", "templates", ".github", "adapters", "mcp", "audit", "docs"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(0, proc.returncode, proc.stderr[-2000:])
        self.assertEqual("", proc.stdout.strip(), f"canonical surface modified: {proc.stdout}")

    def test_h1_lives_entirely_under_the_experiment_directory(self):
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
        touched = [
            line[3:].strip().strip('"')
            for line in proc.stdout.splitlines()
            if line.strip()
        ]
        outside = [p for p in touched if not p.startswith("experiments/v1.2/")]
        self.assertEqual([], outside, f"H1 changed non-experiment paths: {outside}")


if __name__ == "__main__":
    unittest.main()
