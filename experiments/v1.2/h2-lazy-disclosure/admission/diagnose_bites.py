#!/usr/bin/env python3
"""Name WHAT bit: for each B_REGRESSION_GUARD-supported pair, the failing check/test in the mutation.

Schema v2 proves only that a frozen surface goes red when the delta's added paths are removed
(§6.7 STILL NOT ENFORCED: not that the red is the task's target predicate). This program records
which named check or test turned red, so the reviewer judges the guard from a fact, not from an
exit code. It rebuilds the mutation the way the validator does (git rm of the added paths +
a commit carrying the candidate's metadata) and runs each biting surface verbosely.

Usage:  diagnose_bites.py <repo_root> <measurement.json> [...]   -> JSON on stdout
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

FAIL_LINE = re.compile(r"^FAIL\s+(\S+)|^(?:FAIL|ERROR): (\S+) \(", re.M)


def mutation(repo: ctc.Repo, base: str, cand: str, wt: Path) -> None:
    if repo.git("worktree", "add", "-q", "--detach", str(wt), cand).returncode != 0:
        raise SystemExit("cannot materialise")
    added = [p for p in repo.git("diff", "--name-only", "-z", "--diff-filter=A", base, cand,
                                 "--").stdout.split("\0") if p]
    meta = repo.git("log", "-1", "--format=%an%x00%ae%x00%aI%x00%cn%x00%ce%x00%cI%x00%B",
                    cand).stdout.split("\0", 6)
    env = dict(os.environ, GIT_AUTHOR_NAME=meta[0], GIT_AUTHOR_EMAIL=meta[1],
               GIT_AUTHOR_DATE=meta[2], GIT_COMMITTER_NAME=meta[3], GIT_COMMITTER_EMAIL=meta[4],
               GIT_COMMITTER_DATE=meta[5])
    if not added:                    # nothing to remove: the mutation IS the candidate
        return
    ctc.Repo(wt).git("rm", "-q", "--", *added)
    r = subprocess.run(["git", "-C", str(wt), "-c", "commit.gpgsign=false", "-c",
                        "core.hooksPath=/dev/null", "commit", "-q", "--no-verify",
                        "--cleanup=verbatim", "-F", "-"],
                       input=meta[6], text=True, env=env, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"mutation commit failed: {r.stderr.strip()}")


def main(argv: list[str]) -> int:
    repo = ctc.Repo(Path(argv[1]).resolve())
    out = []
    for mp in argv[2:]:
        m = json.loads(Path(mp).read_text(encoding="utf-8"))
        scratch = Path(tempfile.mkdtemp(prefix="h2-bite-"))
        wt = scratch / "mut"
        try:
            mutation(repo, m["base_sha"], m["candidate_sha"], wt)
            row = {"candidate_sha": m["candidate_sha"], "bites": []}
            for e in m["facts"]["biting"]:
                cmd = ctc.acceptance_command(e["path"], e["kind"], sys.executable)
                if e["kind"] == "TEST":
                    cmd = cmd + ["-v"]
                r = subprocess.run(cmd, cwd=str(wt), capture_output=True, text=True,
                                   env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
                names = sorted({a or b for a, b in FAIL_LINE.findall(r.stdout + r.stderr)})
                row["bites"].append({"path": e["path"], "rc": r.returncode, "failing": names})
            out.append(row)
        finally:
            repo.git("worktree", "remove", "--force", str(wt))
            repo.git("worktree", "prune")
            shutil.rmtree(scratch, ignore_errors=True)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
