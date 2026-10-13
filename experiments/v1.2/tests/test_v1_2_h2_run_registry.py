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
import re
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
        # fresh adversarial review on 9f8e4ee (P2): the old assertion ("some table has N rows")
        # tolerated an APPENDED third table — an adversarially relabeled copy sitting behind the
        # canonical one passed the whole suite. The number of tables WITH DATA ROWS is now
        # pinned, and the sizes must be in registry order (Round 1 first).
        data_tables = [t for t in self.tables if _data_rows(t)]
        self.assertEqual(
            len(data_tables), 2,
            f"the registry must contain exactly two run tables with data rows, "
            f"found {len(data_tables)}",
        )
        counts = [len(_data_rows(t)) for t in data_tables]
        self.assertEqual(counts, [len(self.plan1), len(self.plan2)],
                         "table sizes must be (Round 1, Round 2) in that order")

    def test_record_file_column_is_bound(self):
        """fresh adversarial review on 9f8e4ee (P2): the 记录文件 column was unbound — rewriting
        it to any path kept every count and every other column valid. Bind it to the run's own
        directory (Round 2) / the closure-recorded values (Round 1)."""
        rows2 = self._rows_for(self.plan2)
        self.assertIsNotNone(rows2, "no table matches run-plan-r2.json row-for-row")
        for cells, plan in zip(rows2, self.plan2):
            self.assertEqual(cells[7], f"runs/{plan['run_id']}/",
                             f"Round 2 record path for {plan['run_id']} must be its own directory")
        rows1 = self._rows_for(self.plan1)
        self.assertIsNotNone(rows1, "no table matches run-plan.json row-for-row")
        for cells, plan in zip(rows1, self.plan1):
            want = "runs/H2-R1-R01/" if plan["run_id"] == "H2-R01" else "(never executed)"
            self.assertEqual(cells[7], want,
                             f"Round 1 record cell for {plan['run_id']} disagrees with the closure")

    def test_no_unpinned_table_lines(self):
        """fresh adversarial review on 9c5f059 (P3): _data_rows() only accepts rows whose first
        cell is a DIGIT, so a row inserted with a non-numeric first cell (e.g. `| + | H2-R2-R21
        | ... VALID ...`) was invisible to every test. Pin the exact number of table lines the
        registry may contain: 2 tables x (header + separator + 20 data rows).

        fresh review on 61bfbac (P3): GFM also renders a row WITHOUT a leading pipe, which the
        startswith("|") count cannot see. Pin that too: any line containing a pipe must BE a
        table line."""
        table_lines = [ln for ln in self.text.splitlines() if ln.strip().startswith("|")]
        expected = 2 * (2 + len(self.plan1))
        self.assertEqual(
            len(table_lines), expected,
            f"the registry must contain exactly {expected} table lines "
            f"(2 tables x (header + separator + 20 rows)); found {len(table_lines)}",
        )
        bare = [ln for ln in self.text.splitlines()
                if "|" in ln and not ln.strip().startswith("|")]
        self.assertEqual(
            bare, [],
            f"lines containing a pipe must be table lines (GFM renders bare rows but the "
            f"parser cannot see them): {bare[:2]}",
        )

    def test_table_headers_are_labelled(self):
        """fresh review on 9c5f059 (P3): the header rows participate in NO assertion, so swapping
        the ARM and TASK labels passed. Pin both headers."""
        headers = [t[0] for t in self.tables if t and not _data_rows(t)]
        self.assertEqual(len(headers), 2, f"expected two header rows, found {len(headers)}")
        for h in headers:
            self.assertEqual(h, ["#", "RUN_ID", "TASK", "ARM", "REP", "BLOCK", "STATUS", "记录文件"])

    def test_first_table_is_round1_second_is_round2(self):
        """fresh review on 9c5f059 (VACUOUS): the size pin cannot distinguish the tables (both
        have 20 rows), so physically swapping them was undetected. Bind the order."""
        data_tables = [t for t in self.tables if _data_rows(t)]
        self.assertEqual(len(data_tables), 2)
        self.assertEqual(_data_rows(data_tables[0])[0][1], "H2-R01",
                         "the FIRST table must be Round 1")
        self.assertEqual(_data_rows(data_tables[1])[0][1], "H2-R2-R01",
                         "the SECOND table must be Round 2")

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
        # still refuse a Round-2 reuse of it. fresh review on 9c5f059 (P3): a whole-file
        # substring test is satisfied by text hidden in an HTML comment (invisible when
        # rendered), so comments are stripped before the check.
        registry_visible = re.sub(r"<!--.*?-->", "", _read(REGISTRY), flags=re.S)
        self.assertIn(ep, registry_visible)

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
