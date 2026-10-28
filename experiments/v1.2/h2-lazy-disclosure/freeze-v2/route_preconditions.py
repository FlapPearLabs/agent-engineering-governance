#!/usr/bin/env python3
"""Per-base route preconditions for the Freeze v2 shortlist (protocol §10, FZ-ADM-4).

For every shortlisted task base this runs the N8 route validator (route-reachability/
validate_routes.py, unchanged) against routes-h2.json and classifies each failing route:

  S3 row fails                     -> H2_CARRIER_ROUTE_UNSATISFIED  (the H2 carrier is designed
                                      base-universal; any S3 failure blocks the task)
  S1/S2 row whose destination the  -> TASK_NEEDS_UNSATISFIED_ROUTE  (protocol §10: the task is
  task touches                        invalid for H2 at this base; no future file is injected)
  any other S1/S2 row              -> HISTORICAL_BASE_ROUTE_UNSATISFIED (the destination does not
                                      exist yet at that historical base; not an H2 failure)

"The task touches" is decided mechanically, never by reading the task: the destination path or
its file name occurs in the candidate's delta (base..candidate) or in the oracle file at the
candidate. A task is ROUTES_ADMISSIBLE only if no failing route is S3 or task-touched.

Usage:  route_preconditions.py <repo_root> <shortlist.json> --out <route-preconditions.json>
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
H2 = HERE.parent
VALIDATOR = H2.parent / "route-reachability" / "validate_routes.py"
MANIFEST = H2 / "routes-h2.json"


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args[:3])}: {r.stderr.strip()}")
    return r.stdout


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root")
    ap.add_argument("shortlist")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv[1:])
    root = Path(a.repo_root).resolve()
    # a sub-directory root would limit `git diff` to that subtree and silently under-classify
    # task-touched routes (review of 5090f44, finding 4)
    if git(root, "rev-parse", "--show-toplevel").strip() != str(root):
        raise SystemExit("repo_root must be the repository root (run from it with '.')")
    surface = {r["route_id"]: r["surface"]
               for r in json.loads(MANIFEST.read_text(encoding="utf-8"))["routes"]}
    rows = []
    for t in json.loads(Path(a.shortlist).read_text(encoding="utf-8"))["shortlist"]:
        base, cand, oracle = t["BASE_SHA"], t["CANDIDATE_SHA"], t["ORACLE"]["path"]
        r = subprocess.run([sys.executable, str(VALIDATOR), "--base", base, "--manifest",
                            str(MANIFEST.relative_to(root)), "--repo", str(root), "--json"],
                           capture_output=True, text=True, cwd=str(root))
        if r.returncode not in (0, 1):
            raise SystemExit(f"validate_routes rc={r.returncode} at {base}: {r.stderr.strip()}")
        report = json.loads(r.stdout)
        touched = git(root, "diff", base, cand) + git(root, "show", f"{cand}:{oracle}")
        failing = []
        for route in report["routes"]:
            if route["result"] == "VALID":
                continue
            dest = route["destination"]
            if surface[route["route_id"]] == "S3":
                cls = "H2_CARRIER_ROUTE_UNSATISFIED"
            elif dest in touched or Path(dest).name in touched:
                cls = "TASK_NEEDS_UNSATISFIED_ROUTE"
            else:
                cls = "HISTORICAL_BASE_ROUTE_UNSATISFIED"
            failing.append({"route_id": route["route_id"], "surface": surface[route["route_id"]],
                            "destination": dest, "result": route["result"], "class": cls})
        blocking = [f for f in failing if f["class"] != "HISTORICAL_BASE_ROUTE_UNSATISFIED"]
        rows.append({"CASE_ID": t["CASE_ID"], "BASE_SHA": base,
                     "routes_declared": report["routes_declared"],
                     "routes_valid": report["routes_valid"], "validator_verdict": report["verdict"],
                     "failing": failing,
                     "ROUTE_PRECONDITION": "BLOCKED" if blocking else "ROUTES_ADMISSIBLE"})
    summary: dict[str, int] = {}
    for row in rows:
        summary[row["ROUTE_PRECONDITION"]] = summary.get(row["ROUTE_PRECONDITION"], 0) + 1
    Path(a.out).write_text(json.dumps({"program": "freeze-v2/route_preconditions.py",
                                       "manifest": str(MANIFEST.relative_to(root)),
                                       "summary": summary, "rows": rows}, indent=1) + "\n",
                           encoding="utf-8")
    print("ROUTE_PRECONDITIONS", json.dumps(summary))
    for row in rows:
        print(f"  {row['CASE_ID'][:44]:44s} {row['BASE_SHA'][:8]} {row['routes_valid']}/"
              f"{row['routes_declared']} {row['ROUTE_PRECONDITION']} "
              f"{[(f['route_id'], f['class']) for f in row['failing']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
