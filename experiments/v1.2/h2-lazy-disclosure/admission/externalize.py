#!/usr/bin/env python3
"""Materialise EXTERNALIZED-ORACLE task identities from real repairs (Freeze v2 input).

The dominant real repair shape rewrites an existing test, so Schema v2 derives
WORKER_MODIFIES_TEST_ORACLE for the historical pair (B, C): the worker's delta contains the oracle.
The schema's own route for such a task is externalisation — the oracle becomes framework bytes the
worker cannot touch — and the closure of N2.1 requires that this be a NEW task identity and a NEW
revision, never a silent rescue of the old pair. This program builds that revision:

    B' := B with every rewritten test file replaced by C's blob AND mode, as a commit whose single
          parent is B. Metadata is fixed (identity FlapPearLabs, both dates = C's committer date,
          a message naming C and the paths), so B' is DETERMINISTIC: anyone re-running this
          program on the same history gets the same SHA.
    new identity := (B', C). Its delta is (B, C) minus the externalised paths, so the oracle is
          DELTA_FROZEN; whether the task is an A_REPAIR on a FRAMEWORK_FROZEN basis is then for the
          validator to measure (red at B', green at C).

Eligible source pairs: discovery disposition DERIVED_TRIGGER_PRESENT whose derived triggers are
exactly {WORKER_MODIFIES_TEST_ORACLE} on paths the pair MODIFIES (status M). A pair that also
rewrites a validator, or an importable path, stays rejected: externalising a validator would freeze
the fix itself. This program writes objects to the object database and, with --anchor, one branch
ref whose commit has every B' as a parent (so they are reachable and can be pushed); nothing else.

Usage:  externalize.py <repo_root> <discovery.json> [<discovery.json> ...] --out <map.json>
                       [--anchor refs/heads/<name>] [--pairs-out <discovery-externalized.json>]
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "harness"))

import check_task_class as ctc  # noqa: E402

IDENTITY = ("FlapPearLabs", "151931662+FlapPearLabs@users.noreply.github.com")


def git(root: Path, *args: str, env=None, stdin: str | None = None) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                       env=env, input=stdin)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args[:3])}: {r.stderr.strip()}")
    return r.stdout.strip()


def ls_entry(root: Path, rev: str, path: str) -> tuple[str, str]:
    out = git(root, "ls-tree", "-z", rev, "--", path).rstrip("\0")
    meta, _, got = out.partition("\t")
    mode, typ, blob = meta.split()
    if got != path or typ != "blob":
        raise SystemExit(f"{rev}:{path} is not a blob")
    return mode, blob


def build_base_prime(root: Path, base: str, cand: str, paths: list[str]) -> str:
    fd, index = tempfile.mkstemp(prefix="h2-ext-index-")
    os.close(fd)
    try:
        env = dict(os.environ, GIT_INDEX_FILE=index)
        git(root, "read-tree", base, env=env)
        for p in sorted(paths):
            mode, blob = ls_entry(root, cand, p)
            git(root, "update-index", "--cacheinfo", f"{mode},{blob},{p}", env=env)
        tree = git(root, "write-tree", env=env)
    finally:
        os.unlink(index)
    date = git(root, "log", "-1", "--format=%cI", cand)
    env = dict(os.environ, GIT_AUTHOR_NAME=IDENTITY[0], GIT_AUTHOR_EMAIL=IDENTITY[1],
               GIT_COMMITTER_NAME=IDENTITY[0], GIT_COMMITTER_EMAIL=IDENTITY[1],
               GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    message = (f"h2-admission: externalized oracle for {cand}\n\n"
               + "".join(f"externalized: {p}\n" for p in sorted(paths)))
    return git(root, "commit-tree", tree, "-p", base, env=env, stdin=message)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root")
    ap.add_argument("discovery", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--anchor", default="")
    ap.add_argument("--pairs-out", default="",
                    help="also write the measurement view of the new identities (B', C)")
    a = ap.parse_args(argv[1:])
    root = Path(a.repo_root).resolve()
    # git -C <subdir> prefixes every pathspec, so a sub-directory root breaks ls-tree lookups
    if git(root, "rev-parse", "--show-toplevel") != str(root):
        raise SystemExit("repo_root must be the repository root (run from it with '.')")
    out: dict[str, dict] = {}
    skipped: dict[str, str] = {}
    views: list[dict] = []
    for dpath in a.discovery:
        for pair in json.loads(Path(dpath).read_text(encoding="utf-8"))["pairs"]:
            if pair.get("disposition") != "DERIVED_TRIGGER_PRESENT":
                continue
            cand, base = pair["candidate_sha"], pair["base_sha"]
            triggers = pair["derived_triggers"]
            if set(triggers) != {"WORKER_MODIFIES_TEST_ORACLE"}:
                skipped[cand] = "TRIGGERS_BEYOND_TEST_ORACLE:" + ",".join(sorted(triggers))
                continue
            status = dict((p, s) for s, p in pair["changed"])
            paths = triggers["WORKER_MODIFIES_TEST_ORACLE"]
            if any(not status.get(p, "").startswith("M") for p in paths):
                skipped[cand] = "ORACLE_PATH_NOT_A_MODIFICATION"
                continue
            prime = build_base_prime(root, base, cand, paths)
            # the new identity must derive no trigger of its own (else it is not a task at all)
            residual = ctc.derived_triggers(ctc.Repo(root).changed_paths_with_status(prime, cand))
            if residual:
                skipped[cand] = "RESIDUAL_TRIGGERS:" + json.dumps(residual, sort_keys=True)
                continue
            out[cand] = {"original_base": base, "base_prime": prime,
                         "externalized_paths": sorted(paths), "subject": pair.get("subject")}
            new_changed = ctc.Repo(root).changed_paths_with_status(prime, cand)
            views.append({"base_sha": prime, "candidate_sha": cand,
                          "disposition": "EXTERNALIZED_ORACLE",
                          "changed": [[s, p] for s, p in new_changed],
                          "derived_triggers": residual,
                          "original_base": base, "externalized_paths": sorted(paths),
                          "original_pair": {"base_sha": base, "candidate_sha": cand,
                                            "disposition": pair["disposition"],
                                            "changed": pair["changed"],
                                            "derived_triggers": triggers},
                          "subject": pair.get("subject")})
    doc = {"program": "admission/externalize.py", "identity": list(IDENTITY),
           "eligible": len(out), "skipped": skipped, "externalized": out}
    Path(a.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.pairs_out:
        ref = json.loads(Path(a.discovery[0]).read_text(encoding="utf-8")).get("ref_sha")
        Path(a.pairs_out).write_text(json.dumps(
            {"program": "admission/externalize.py --pairs-out", "ref_sha": ref,
             "pairs_total": len(views), "funnel": {"EXTERNALIZED_ORACLE": len(views)},
             "pairs": views}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.anchor and out:
        primes = sorted({v["base_prime"] for v in out.values()})
        tree = git(root, "mktree", stdin="")                      # the empty tree
        args = [x for p in primes for x in ("-p", p)]
        env = dict(os.environ, GIT_AUTHOR_NAME=IDENTITY[0], GIT_AUTHOR_EMAIL=IDENTITY[1],
                   GIT_COMMITTER_NAME=IDENTITY[0], GIT_COMMITTER_EMAIL=IDENTITY[1],
                   GIT_AUTHOR_DATE="2026-10-18T00:00:00+00:00",
                   GIT_COMMITTER_DATE="2026-10-18T00:00:00+00:00")
        anchor = git(root, "commit-tree", tree, *args, env=env,
                     stdin="h2-admission: anchor for externalized-oracle revisions\n")
        git(root, "update-ref", a.anchor, anchor)
        print(f"ANCHOR {a.anchor} -> {anchor} ({len(primes)} parents)")
    print(f"EXTERNALIZED eligible={len(out)} skipped={len(skipped)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
