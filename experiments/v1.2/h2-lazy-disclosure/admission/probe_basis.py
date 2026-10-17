#!/usr/bin/env python3
"""Observation probe for a measured basis: did the acceptance EXERCISE anything? (pre-freeze)

The validator reads exit codes only. An exit code is a claim about a process, not about what the
process exercised: a unittest module whose tests are all skipped exits 0 ("TEST_GREEN !=
PREDICATE_EXERCISED"), and a module that cannot be imported at the base "fails" without reaching
any assertion. This probe re-runs one basis surface in the same two materialised states the
validator uses (base tree carrying the candidate's acceptance bytes; candidate tree) and records
what unittest itself reports: tests run, skipped, failures, errors, and the first error type.

It decides nothing on its own; build_records.py and the ledger read its output.

Usage:  probe_basis.py <repo_root> <measurement.json> <out.json>
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "harness"))

import check_task_class as ctc  # noqa: E402

RAN_RE = re.compile(r"^Ran (\d+) tests? in", re.M)
TAIL_RE = re.compile(r"^(OK|FAILED)(?: \((.*)\))?\s*$", re.M)
ERRTYPE_RE = re.compile(r"^(\w+(?:Error|Exception)|AssertionError)\b", re.M)


def summarise(out: str, rc: int) -> dict:
    ran = RAN_RE.findall(out)
    tail = TAIL_RE.findall(out)
    counts = {"failures": 0, "errors": 0, "skipped": 0, "expected failures": 0}
    if tail:
        for part in (tail[-1][1] or "").split(","):
            if "=" in part:
                k, v = part.strip().split("=", 1)
                counts[k] = int(v)
    return {"rc": rc, "ran": int(ran[-1]) if ran else None,
            "verdict_line": tail[-1][0] if tail else None,
            "failures": counts["failures"], "errors": counts["errors"],
            "skipped": counts["skipped"],
            "first_error_types": sorted(set(ERRTYPE_RE.findall(out)))[:5]}


def run(tree: Path, rel: str, kind: str) -> dict:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    r = subprocess.run(ctc.acceptance_command(rel, kind, sys.executable), cwd=str(tree),
                       capture_output=True, text=True, env=env, timeout=ctc.ACCEPTANCE_TIMEOUT)
    return summarise(r.stdout + r.stderr, r.returncode)


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    repo = ctc.Repo(Path(argv[1]).resolve())
    m = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    base, cand = m["base_sha"], m["candidate_sha"]
    basis = m["facts"].get("discriminating") or []
    scratch = Path(tempfile.mkdtemp(prefix="h2-probe-"))
    out = {"base_sha": base, "candidate_sha": cand, "probes": []}
    try:
        bw, cw = scratch / "base", scratch / "cand"
        for sha, wt in ((base, bw), (cand, cw)):
            if repo.git("worktree", "add", "-q", "--detach", str(wt), sha).returncode != 0:
                raise SystemExit(f"cannot materialise {sha}")
        for e in basis:
            rel, kind = e["path"], e["kind"]
            if kind != "TEST":
                out["probes"].append({"path": rel, "kind": kind,
                                      "note": "VALIDATOR surface: exit code is the only report"})
                continue
            cb = bw / rel
            existed = cb.is_file()
            saved = cb.read_bytes() if existed else None
            cb.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(cw / rel, cb)
            try:
                at_base = run(bw, rel, kind)
            finally:
                if existed:
                    cb.write_bytes(saved)
                else:
                    cb.unlink()
            out["probes"].append({"path": rel, "kind": kind, "provenance": e["provenance"],
                                  "base": at_base, "candidate": run(cw, rel, kind)})
    finally:
        for wt in (scratch / "base", scratch / "cand"):
            repo.git("worktree", "remove", "--force", str(wt))
        repo.git("worktree", "prune")
        shutil.rmtree(scratch, ignore_errors=True)
    Path(argv[3]).write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    for p in out["probes"]:
        if "base" in p:
            b, c = p["base"], p["candidate"]
            print(f"  {cand[:12]} {Path(p['path']).name}: base ran={b['ran']} F={b['failures']} "
                  f"E={b['errors']} S={b['skipped']} {b['first_error_types']} | cand ran={c['ran']} "
                  f"S={c['skipped']} {c['verdict_line']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
