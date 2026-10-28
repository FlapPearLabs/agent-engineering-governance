#!/usr/bin/env python3
"""Freeze v2 task SHORTLIST from the admission ledgers — deterministic, every exclusion named.

Schema v2 decides which requests are VALID; this program decides which valid requests are GOOD H2
tasks, by rules fixed here before anyone looks at a run (FZ-ADM-1/2/8/9):

  S1  class A_REPAIR with REQUEST_VALID              (B requests are all link-integrity guards: shallow)
  S2  REGRESSED_GUARDS and DELETED_ACCEPTANCE_SURFACES empty  (a reference that breaks a guard is flawed)
  S3  the oracle is VISIBLE and FRAMEWORK_FROZEN — or, if hidden (DELTA_ADDED), alignment.py says
      ALIGNED (a hidden oracle whose literals the ticket never states measures luck)
  S4  no overlap: of r07/r31 and r30/r33 at most one (none survives S1-S3 today; rule kept)
  S5  diversity: at most ONE task per oracle file — the earliest candidate — so the set is not a
      handful of near-identical repairs of one test

Nothing here changes a record or a verdict. Usage:
  select.py <ledger.json>... --alignment <alignment.json> --out <shortlist.json>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

OVERLAPS = (("r07-", "r31-"), ("r30-", "r33-"))


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("ledgers", nargs="+")
    ap.add_argument("--alignment", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv[1:])
    aligned = {r["CASE_ID"]: r["ALIGNMENT"] for r in
               json.loads(Path(a.alignment).read_text(encoding="utf-8"))["rows"]}
    pool, excluded = [], {}
    for lp in a.ledgers:
        for r in json.loads(Path(lp).read_text(encoding="utf-8"))["rows"]:
            cid = r["CASE_ID"]
            if not r["SCHEMA_V2_RESULT"].endswith("A_REPAIR / REQUEST_VALID"):
                excluded[cid] = "S1:" + r["SCHEMA_V2_RESULT"]
                continue
            if r.get("REGRESSED_GUARDS") or r.get("DELETED_ACCEPTANCE_SURFACES"):
                excluded[cid] = "S2:GUARD_REGRESSED_OR_DELETED"
                continue
            frozen = str(r.get("ORACLE_EXTERNALIZATION", "")).startswith("FRAMEWORK_FROZEN")
            if not frozen and aligned.get(cid) != "ALIGNED":
                excluded[cid] = f"S3:HIDDEN_ORACLE_{aligned.get(cid, 'NOT_CHECKED')}"
                continue
            date = subprocess.run(["git", "log", "-1", "--format=%cI", r["CANDIDATE_SHA"]],
                                  capture_output=True, text=True).stdout.strip()
            pool.append({"CASE_ID": cid, "CANDIDATE_SHA": r["CANDIDATE_SHA"],
                         "BASE_SHA": r["BASE_SHA"], "ORACLE": r["FROZEN_ACCEPTANCE_DEFINITION"],
                         "TASK_DESCRIPTION": r["TASK_DESCRIPTION"], "DATE": date,
                         "VISIBLE_FROZEN_ORACLE": frozen})
    ids = {p["CASE_ID"][:4] for p in pool}
    for x, y in OVERLAPS:
        if x in ids and y in ids:
            loser = next(p for p in pool if p["CASE_ID"].startswith(y))
            pool.remove(loser)
            excluded[loser["CASE_ID"]] = f"S4:OVERLAPS_{x.rstrip('-')}"
    shortlist, seen = [], set()
    for p in sorted(pool, key=lambda q: (q["DATE"], q["CASE_ID"])):
        oracle = (p["ORACLE"] or {}).get("path")
        if oracle in seen:
            excluded[p["CASE_ID"]] = f"S5:ORACLE_ALREADY_REPRESENTED:{oracle}"
            continue
        seen.add(oracle)
        shortlist.append(p)
    doc = {"program": "admission/select.py", "rules": ["S1", "S2", "S3", "S4", "S5"],
           "pool_after_S1_S4": len(pool), "shortlist_count": len(shortlist),
           "shortlist": shortlist, "excluded": dict(sorted(excluded.items()))}
    Path(a.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"SHORTLIST {len(shortlist)} (pool {len(pool)})")
    for p in shortlist:
        print(f"  {p['CASE_ID'][:52]:52s} {(p['ORACLE'] or {}).get('path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
