#!/usr/bin/env python3
"""Schema-v2 candidate MEASUREMENT: execute the transition for discovered pairs (pre-freeze).

For every pair routed to MEASURE_ADDED_ACCEPTANCE by discover.py, this calls the validator's own
`recompute_transition` (harness/check_task_class.py) — the same function the validator runs when it
judges a record, imported rather than copied — and stores the raw per-surface exit codes.

A measurement is evidence, not a verdict. The verdict on a record is produced later, by the
validator, which RE-EXECUTES the transition from scratch and binds every status the record
declares (copied from this measurement by build_records.py) to its own execution — so a pair whose
two independent executions disagree is refused by the validator (a flaky acceptance is not an
oracle). Both class readings are evaluated from the one execution, because transition_verdict()
reads only class-independent facts (acceptance_count, unmeasured, discriminating, frozen_count,
biting).

Usage:  measure.py <repo_root> <discovery.json> <out_dir> [--jobs N] [--only SHA[,SHA...]]
                   [--disposition DISPOSITION]   (default MEASURE_ADDED_ACCEPTANCE; batch 2 runs
                                                  DEFERRED_FROZEN_BASIS_SCAN)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "harness"))

import check_task_class as ctc  # noqa: E402


def measure_one(root: str, base: str, cand: str) -> dict:
    repo = ctc.Repo(Path(root))
    t0 = time.time()
    facts = ctc.recompute_transition(repo, base, cand, "A_REPAIR")
    elapsed = round(time.time() - t0, 1)
    verdicts = {cls: dict(zip(("supported", "reason"), ctc.transition_verdict(cls, facts)))
                for cls in ctc.ADMISSIBLE_CLASSES}
    return {"base_sha": base, "candidate_sha": cand, "elapsed_s": elapsed,
            "facts": facts, "verdicts": verdicts}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root")
    ap.add_argument("discovery")
    ap.add_argument("out_dir")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--only", default="")
    ap.add_argument("--disposition", default="MEASURE_ADDED_ACCEPTANCE")
    a = ap.parse_args(argv[1:])
    root = str(Path(a.repo_root).resolve())
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    doc = json.loads(Path(a.discovery).read_text(encoding="utf-8"))
    only = {s for s in a.only.split(",") if s}
    todo = [p for p in doc["pairs"] if p.get("disposition") == a.disposition
            and (not only or any(p["candidate_sha"].startswith(s) for s in only))]
    # the interpreter is recorded by role and version, never by absolute path: a local home
    # directory in a tracked file is a public-release violation (validate_public_release.py)
    env = {"python": "<PY>", "python_version": platform.python_version(),
           "git": subprocess.run(["git", "--version"], capture_output=True,
                                 text=True).stdout.strip(),
           "platform": platform.platform(), "schema_version": ctc.SCHEMA_VERSION,
           # the exact validator bytes that produced this measurement (a version string is a
           # claim; this is the fact)
           "validator_sha256": hashlib.sha256(Path(ctc.__file__).read_bytes()).hexdigest(),
           "acceptance_timeout_s": ctc.ACCEPTANCE_TIMEOUT}
    print(f"MEASURE pairs={len(todo)} jobs={a.jobs}", flush=True)
    with ProcessPoolExecutor(max_workers=a.jobs) as pool:
        futs = {pool.submit(measure_one, root, p["base_sha"], p["candidate_sha"]): p
                for p in todo}
        for fut in futs:
            p = futs[fut]
            res = fut.result()
            res["environment"] = env
            res["subject"] = p.get("subject")
            (out / f"{p['candidate_sha'][:12]}.json").write_text(
                json.dumps(res, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            v = res["verdicts"]
            print(f"  {p['candidate_sha'][:12]} A={v['A_REPAIR']['reason']} "
                  f"B={v['B_REGRESSION_GUARD']['reason']} t={res['elapsed_s']}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
