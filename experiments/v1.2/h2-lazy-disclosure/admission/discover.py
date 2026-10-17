#!/usr/bin/env python3
"""Schema-v2 candidate DISCOVERY over a repository's real history (pre-freeze, read-only).

Every non-merge commit reachable from REF becomes one (parent, commit) pair, and EVERY pair gets a
disposition — nothing is dropped silently, so a later reader can recount the funnel from this file.

The structural facts are computed with the validator's OWN functions (`derived_triggers`, the
acceptance-path convention) imported from harness/check_task_class.py, never a re-implementation:
a prefilter that disagreed with the validator would discard pairs the validator would accept, or
pass pairs it would refuse, and either way the funnel would stop meaning anything.

This program decides NOTHING about eligibility. Its dispositions are routing:

  DERIVED_TRIGGER_PRESENT       the delta REWRITES a test/validator path; Schema v2 derives
                                WORKER_MODIFIES_TEST_ORACLE / WORKER_MODIFIES_VALIDATOR, so the
                                pair can be at best C_REJECT or PENDING (externalisation) — it
                                cannot carry a valid request as a historical pair.
  MEASURE_ADDED_ACCEPTANCE      no derived trigger and the delta ADDS an acceptance surface:
                                routed to execution (measure.py), where the transition is decided.
  DEFERRED_FROZEN_BASIS_SCAN    no derived trigger, no added acceptance: an A_REPAIR would need a
                                FROZEN surface red at the base, a B_REGRESSION_GUARD a frozen
                                surface green at the base and red under mutation. Both need full
                                execution of every surface, so they are a separate (costed) batch.
  NO_DELTA                      empty diff.

Usage:  discover.py <repo_root> <ref> <out.json>
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "harness"))

import check_task_class as ctc  # noqa: E402  (validator-owned rules, imported not copied)

# The validator's acceptance convention (check_task_class.acceptance_surfaces) expressed as a path
# predicate, because discovery reads the diff rather than a materialised tree. It is cross-checked
# against acceptance_surfaces() by test_admission_workflow.py so the two cannot drift apart.
ACCEPTANCE_PATH_RE = re.compile(r"^scripts/validate_[^/]*\.py$|^scripts/tests/test_[^/]*\.py$")


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {r.stderr.strip()}")
    return r.stdout


def pair_facts(repo: ctc.Repo, parent: str, commit: str) -> dict:
    changed = repo.changed_paths_with_status(parent, commit)
    if changed is None:
        raise SystemExit(f"cannot read the delta {parent}..{commit}")
    derived = ctc.derived_triggers(changed)
    added_acc = [p for s, p in changed if s == "A" and ACCEPTANCE_PATH_RE.match(p)]
    if not changed:
        disposition = "NO_DELTA"
    elif derived:
        disposition = "DERIVED_TRIGGER_PRESENT"
    elif added_acc:
        disposition = "MEASURE_ADDED_ACCEPTANCE"
    else:
        disposition = "DEFERRED_FROZEN_BASIS_SCAN"
    return {
        "base_sha": parent,
        "candidate_sha": commit,
        "changed": [[s, p] for s, p in changed],
        "derived_triggers": derived,
        "added_acceptance_surfaces": added_acc,
        "disposition": disposition,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__, file=sys.stderr)
        return 2
    root, ref, out = Path(argv[1]).resolve(), argv[2], Path(argv[3])
    repo = ctc.Repo(root)
    ref_sha = git(root, "rev-parse", f"{ref}^{{commit}}").strip()
    remote = git(root, "config", "--get", "remote.origin.url").strip()
    rows = []
    for line in git(root, "rev-list", "--no-merges", "--parents", ref_sha).splitlines():
        parts = line.split()
        commit, parents = parts[0], parts[1:]
        if len(parents) != 1:            # root commit (no parent): there is no base to replay
            rows.append({"candidate_sha": commit, "disposition": "NO_PARENT"})
            continue
        row = pair_facts(repo, parents[0], commit)
        row["subject"] = git(root, "log", "-1", "--format=%s", commit).strip()
        row["date"] = git(root, "log", "-1", "--format=%cs", commit).strip()
        rows.append(row)
    funnel: dict[str, int] = {}
    for r in rows:
        funnel[r["disposition"]] = funnel.get(r["disposition"], 0) + 1
    doc = {
        "program": "admission/discover.py",
        "schema_version_consulted": ctc.SCHEMA_VERSION,
        "repository_remote": remote,
        "ref": ref,
        "ref_sha": ref_sha,
        "pairs_total": len(rows),
        "funnel": dict(sorted(funnel.items())),
        "pairs": rows,
    }
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"DISCOVERY ref={ref}@{ref_sha[:12]} pairs={len(rows)} funnel={doc['funnel']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
