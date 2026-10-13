#!/usr/bin/env python3
"""H2 harness — frozen run facts (single source for the ACCEPTANCE scripts).

Derives (task_id, base_sha, arm, plan_index, plan_name) for a RUN_ID from the FROZEN plan and
the task registry, and requires BOTH files' working-tree bytes to equal the version committed at
the materials checkout's HEAD.

WHY THIS EXISTS: receipt.json lives in the evidence directory the WORKER can write. Acceptance
scripts that read expected_base / task_id from it let a worker run the acceptance with a
rewritten base (skipping the committed-change enumeration), collect a PASS, restore the
receipt, and still pass collection — the run stays VALID while the recorded acceptance verdict
is forged (fresh adversarial review on 9f8e4ee, P0). The frozen plan and registry live outside
the worker's contract write surface, and this helper additionally binds them to their COMMITTED
bytes so an edit could not be paired with a matching edit of a hash pin.

Hardening from the fresh review on 9c5f059:
  * duplicate plan rows (one run id, several rows) are FAIL-CLOSED (rc=3) instead of falling
    through to the next plan file;
  * the registry is commit-bound too — the base_sha it supplies is only as trustworthy as the
    file it comes from;
  * paths are realpath-resolved before the repo-relative comparison, so reaching the harness via
    a symlink (macOS /tmp, /var, a symlinked workspace) no longer fails a legitimate call;
  * the arm is validated against the known values — an unknown arm is rc=3 rather than being
    passed through to callers that would mishandle it.

Usage: frozen_run_facts.py <EXP_DIR> <RUN_ID>
Stdout (one TAB-separated line): task_id<TAB>base_sha<TAB>arm<TAB>plan_index<TAB>plan_name
Exit: 0 ok | 2 no frozen row for this run (a registered dry-run id) | 3 unreadable,
commit-unbound or duplicate inputs (fail-closed; callers must refuse, never fall back to the
receipt).
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

VALID_ARMS = ("control", "variant")


def _sha(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _committed_equal(repo: str, rel: str, path: str) -> bool:
    """True iff the working-tree file at `path` byte-equals HEAD:rel in `repo`."""
    blob = subprocess.run(["git", "-C", repo, "show", f"HEAD:{rel}"], capture_output=True)
    return (blob.returncode == 0 and bool(blob.stdout)
            and hashlib.sha256(blob.stdout).hexdigest() == _sha(path))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: frozen_run_facts.py <EXP_DIR> <RUN_ID>", file=sys.stderr)
        return 3
    exp_real = os.path.realpath(sys.argv[1])
    rid = sys.argv[2]

    top = subprocess.run(["git", "-C", exp_real, "rev-parse", "--show-toplevel"],
                         capture_output=True, text=True)
    if top.returncode != 0 or not top.stdout.strip():
        return 3
    repo = os.path.realpath(top.stdout.strip())

    for plan_name in ("run-plan-r2.json", "run-plan.json"):
        path = os.path.join(exp_real, "harness", plan_name)
        if not os.path.isfile(path):
            continue
        try:
            plan = json.load(open(path, encoding="utf-8"))
        except Exception:
            return 3
        rows = [r for r in plan if r.get("run_id") == rid]
        if len(rows) > 1:
            # duplicate identity: ambiguous inputs must refuse, not resolve
            return 3
        if len(rows) != 1:
            continue
        rel = os.path.relpath(os.path.realpath(path), repo)
        if not _committed_equal(repo, rel, path):
            return 3
        row = rows[0]
        if row.get("arm") not in VALID_ARMS:
            return 3
        reg_path = os.path.join(exp_real, "task-registry.json")
        try:
            reg = json.load(open(reg_path, encoding="utf-8"))
            tasks = {t["task_id"]: t for t in reg["tasks"]}
            base = tasks[row["task_id"]]["base_sha"]
        except Exception:
            return 3
        if not _committed_equal(repo, "experiments/v1.2/h2-lazy-disclosure/task-registry.json",
                                reg_path):
            return 3
        idx = plan.index(row)
        print(f"{row['task_id']}\t{base}\t{row['arm']}\t{idx}\t{plan_name}")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
