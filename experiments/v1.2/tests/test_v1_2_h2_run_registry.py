"""H2 run-registry consistency gate (PART 4).

`run-registry.md` declares itself the sole run-identity registry. That claim is only true if the
registry TABLE can actually recover the state, so this test binds the table to every other
authority and compares COMPLETE ORDERED TUPLES — a row count can be right while every row is
wrong, which is the failure the previous single-table registry exhibited (all twenty Round-1 ids
still reading PLANNED after the round had permanently closed).

Authorities bound here:
  run-registry.md §1  <->  harness/run-plan.json      (Round 1)
  run-registry.md §2  <->  harness/run-plan-r2.json   (Round 2)
  run-registry.md §1  <->  round-1-closure.md         (round terminal state)
  run-registry.md §1  <->  runs/H2-R1-R01/round-1-run-record.json  (invalid run + episode)
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
H2 = ROOT / "experiments" / "v1.2" / "h2-lazy-disclosure"
REGISTRY = H2 / "run-registry.md"
PLAN1 = H2 / "harness" / "run-plan.json"
PLAN2 = H2 / "harness" / "run-plan-r2.json"
CLOSURE = H2 / "round-1-closure.md"
INVALID_REC = H2 / "runs" / "H2-R1-R01" / "round-1-run-record.json"

R1_STATUSES = {"INVALID", "CANCELLED_ROUND_INVALID"}
R2_STATUS = "FROZEN_NOT_EXECUTED"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _tables(text: str) -> list[list[list[str]]]:
    """Return the data rows of each markdown table, as [[cells, ...], ...] per table.

    Tables are separated by any non-table line, so the two registry sections parse independently.
    """
    tables: list[list[list[str]]] = []
    cur: list[list[str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if set("".join(cells)) <= set("-: "):
                continue  # separator
            cur.append(cells)
        else:
            if cur:
                tables.append(cur)
                cur = []
    if cur:
        tables.append(cur)
    return tables


def _data_rows(table: list[list[str]]) -> list[list[str]]:
    """Rows whose first cell is a row number."""
    return [r for r in table if r and r[0].isdigit()]


class RegistryStructure(unittest.TestCase):
    def setUp(self):
        self.text = _read(REGISTRY)
        self.plan1 = json.loads(_read(PLAN1))
        self.plan2 = json.loads(_read(PLAN2))
        self.tables = _tables(self.text)

    def test_exactly_two_registry_tables_with_expected_sizes(self):
        sized = [(i, len(_data_rows(t))) for i, t in enumerate(self.tables)]
        counts = [n for _, n in sized]
        self.assertIn(len(self.plan1), counts, f"no table has {len(self.plan1)} rows: {sized}")
        self.assertIn(len(self.plan2), counts, f"no table has {len(self.plan2)} rows: {sized}")

    def _rows_for(self, plan):
        """Find the table whose rows match this plan's (run_id, task, arm, rep, block) tuples.

        The run id MUST be part of the match: the two rounds share task/arm/rep/block by design
        (same frozen design, different identity namespace), so a match without the id would
        select the wrong table and still look plausible.
        """
        want = [(r["run_id"], r["task_id"], r["arm"], str(r["rep"]), str(r["block"]))
                for r in plan]
        for t in self.tables:
            rows = _data_rows(t)
            if len(rows) != len(plan):
                continue
            got = [(r[1], r[2], r[3], r[4], r[5]) for r in rows]
            if got == want:
                return rows
        return None

    def test_round1_rows_are_complete_and_ordered(self):
        rows = self._rows_for(self.plan1)
        self.assertIsNotNone(rows, "no table matches run-plan.json (Round 1) row-for-row")
        for i, (cells, plan) in enumerate(zip(rows, self.plan1), start=1):
            self.assertEqual(
                (int(cells[0]), cells[1], cells[2], cells[3], int(cells[4]), int(cells[5])),
                (i, plan["run_id"], plan["task_id"], plan["arm"], int(plan["rep"]), int(plan["block"])),
                f"Round 1 row {i} disagrees with the frozen plan",
            )

    def test_round2_rows_are_complete_and_ordered(self):
        rows = self._rows_for(self.plan2)
        self.assertIsNotNone(rows, "no table matches run-plan-r2.json (Round 2) row-for-row")
        for i, (cells, plan) in enumerate(zip(rows, self.plan2), start=1):
            self.assertEqual(
                (int(cells[0]), cells[1], cells[2], cells[3], int(cells[4]), int(cells[5])),
                (i, plan["run_id"], plan["task_id"], plan["arm"], int(plan["rep"]), int(plan["block"])),
                f"Round 2 row {i} disagrees with the frozen plan",
            )


class RegistryTerminalState(unittest.TestCase):
    def setUp(self):
        self.tables = _tables(_read(REGISTRY))
        self.plan1 = json.loads(_read(PLAN1))
        self.plan2 = json.loads(_read(PLAN2))

    def _r1_rows(self):
        for t in self.tables:
            rows = _data_rows(t)
            if len(rows) == len(self.plan1) and rows[0][1].startswith("H2-R0"):
                return rows
        return None

    def _r2_rows(self):
        for t in self.tables:
            rows = _data_rows(t)
            if len(rows) == len(self.plan2) and rows[0][1].startswith("H2-R2-R"):
                return rows
        return None

    def test_no_planned_rows_remain(self):
        """Round 1 is permanently closed: a lingering PLANNED row would advertise a runnable
        identity for a round that can no longer execute."""
        self.assertNotIn("PLANNED", _read(REGISTRY).replace("PLANNED`", ""))

    def test_round1_r01_is_invalid_and_all_others_are_terminal(self):
        rows = self._r1_rows()
        self.assertIsNotNone(rows)
        statuses = {r[1]: r[6] for r in rows}
        self.assertEqual(statuses.get("H2-R01"), "INVALID")
        for rid, st in statuses.items():
            self.assertIn(st, R1_STATUSES, f"{rid} has a non-terminal status {st!r}")
        self.assertEqual(
            [r[1] for r in rows if r[6] == "INVALID"], ["H2-R01"],
            "exactly one Round-1 run may be INVALID",
        )

    def test_round2_all_not_executed(self):
        rows = self._r2_rows()
        self.assertIsNotNone(rows)
        for r in rows:
            self.assertEqual(r[6], R2_STATUS, f"{r[1]} is not {R2_STATUS}")

    def test_round1_and_round2_identities_are_disjoint(self):
        r1 = {r[1] for r in self._r1_rows()}
        r2 = {r[1] for r in self._r2_rows()}
        self.assertEqual(r1 & r2, set(), f"identity reuse across rounds: {sorted(r1 & r2)}")
        self.assertEqual(r1, {p["run_id"] for p in self.plan1})
        self.assertEqual(r2, {p["run_id"] for p in self.plan2})


class RegistryBindsToClosureAndInvalidRecord(unittest.TestCase):
    def test_closure_declares_invalid_and_no_result(self):
        text = _read(CLOSURE)
        for tok in ("CLOSED / INVALID", "GLOBAL_HARNESS_CONTRACT_DEFECT",
                    "VALID_RUNS                = 0", "H2_RESULT                 = NOT_PRODUCED"):
            self.assertIn(tok, text, f"closure record is missing {tok!r}")
        self.assertNotIn("H2_RESULT                 = INSUFFICIENT_EVIDENCE", text)

    def test_invalid_record_matches_registry_and_closure(self):
        rec = json.loads(_read(INVALID_REC))
        self.assertEqual(rec["status"], "INVALID")
        self.assertEqual(rec["invalid_reason"], "GLOBAL_HARNESS_CONTRACT_DEFECT")
        self.assertIs(rec["worker_had_independent_contract_violation"], True)
        ep = (rec.get("episode") or {}).get("worker_episode")
        self.assertTrue(ep, "the invalid run must preserve its episode identity")
        # the registry must carry the same episode so a consumer reading only the registry can
        # still refuse a Round-2 reuse of it
        self.assertIn(ep, _read(REGISTRY))

    def test_arm_assignment_matches_between_plan_and_registry(self):
        """The registry is the human-readable authority for arm assignment; a transposed arm
        would silently invert the contrast the experiment measures."""
        plan1 = json.loads(_read(PLAN1))
        rows = None
        for t in _tables(_read(REGISTRY)):
            r = _data_rows(t)
            if len(r) == len(plan1) and r[0][1].startswith("H2-R0"):
                rows = r
                break
        self.assertIsNotNone(rows)
        for cells, plan in zip(rows, plan1):
            self.assertEqual(cells[3], plan["arm"], f"{cells[1]}: arm mismatch")


if __name__ == "__main__":
    unittest.main()
