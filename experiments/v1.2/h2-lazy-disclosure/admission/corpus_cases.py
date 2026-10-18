#!/usr/bin/env python3
"""Render replay-corpus case blocks for admission pairs (pre-freeze; output is reviewed text).

Schema v2's identity rule binds every record to a corpus case, so a candidate cannot be validated
until a corpus names it. Admission anchors go to admission/corpus.yaml — NOT to H3's
replay/cases.yaml, whose every case is an H3 detector input. This program renders the blocks; it
does not edit the corpus — they are inserted in review together with the two pins the identity
root requires (H2_CORPUS_SHA256 in the validator, the per-case pair literal in the test).

The v1 signal counts are computed HERE, with commands that differ from the H3 detector
(structure_delta.py): new files from `--diff-filter=A -z`, new directories from `ls-tree -d`
(git's own tree entries) instead of path-prefix derivation. The H3 loader then compares the two
implementations case by case, so an expected count that merely echoed the detector is impossible.

Cases rendered here carry class H2_ADMISSION_CANDIDATE: they enter the corpus as identity anchors
for H2, and the H3 axes are NOT adjudicated for them (no seam-drift or structure verdict is made).

Usage:  corpus_cases.py <repo_root> [--externalized=<externalized.json>] <case_id>=<candidate_sha> [...]
"""
from __future__ import annotations

import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def signals(root: Path, base: str, cand: str) -> dict[str, int]:
    added = [p for p in git(root, "diff", "--no-renames", "--diff-filter=A", "--name-only", "-z",
                             base, cand).split("\0") if p]

    def dirs(sha: str) -> set[str]:
        return {p for p in git(root, "ls-tree", "-r", "-d", "--name-only", "-z",
                               sha).split("\0") if p}

    deps = 0
    for p in [p for p in git(root, "diff", "--no-renames", "--diff-filter=AM", "--name-only",
                              "-z", base, cand).split("\0") if p]:
        if fnmatch.fnmatchcase(p.rsplit("/", 1)[-1], "requirements*.txt"):
            for line in git(root, "diff", "-U0", "--no-renames", base, cand, "--",
                            p).splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    body = line[1:].strip()
                    deps += bool(body) and not body.startswith("#")
    return {"NEW_FILE": len(added), "NEW_DIRECTORY": len(dirs(cand) - dirs(base)),
            "NEW_DEPENDENCY": deps}


def block(root: Path, case_id: str, cand: str, verified_main: str,
          external: dict | None = None) -> str:
    cand = git(root, "rev-parse", f"{cand}^{{commit}}").strip()
    parents = git(root, "rev-list", "--parents", "-n1", cand).split()[1:]
    if not parents:
        raise SystemExit(f"{case_id}: {cand} has no parent to replay against")
    base = parents[0]                    # a merge is replayed against its FIRST parent
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", cand,
                       verified_main]).returncode != 0:
        raise SystemExit(f"{case_id}: {cand} is not reachable from {verified_main}")
    if external:                         # an EXTERNALIZED_ORACLE identity: base is B', not B
        if external["original_base"] != base:
            raise SystemExit(f"{case_id}: externalized original_base is not the first parent")
        base = external["base_prime"]
    subject = git(root, "log", "-1", "--format=%s", cand).strip().replace("'", "''")
    sig = signals(root, base, cand)
    stat = git(root, "diff", "--shortstat", base, cand).strip()
    lines = [f"  - case_id: {case_id}",
             "    class: H2_ADMISSION_CANDIDATE",
             "    source_repository: FlapPearLabs/agent-engineering-governance",
             "    source_ref: main",
             f"    base_sha: {base}",
             f"    candidate_sha: {cand}",
             f"    historical_diff: 'git diff {base} {cand}'"]
    if external:
        lines += ["    kind: EXTERNALIZED_ORACLE",
                  f"    original_base: {external['original_base']}",
                  "    externalized_paths: " + json.dumps(sorted(external["externalized_paths"]))]
    nonzero = [(k, v) for k, v in sig.items() if v]
    if not nonzero:
        lines.append("    expected_mechanical_signals: []")
    else:
        lines.append("    expected_mechanical_signals:")
        for k, v in nonzero:
            lines += [f"      - signal: {k}", f"        count: {v}",
                      "        detail: |",
                      "          computed by admission/corpus_cases.py (independent of the H3 "
                      "detector)"]
    lines += [
        "    structure_disposition: NOT_ADJUDICATED",
        "    structure_rationale: |",
        "      Added for H2 Schema-v2 candidate admission as an identity anchor only. No structure",
        "      verdict is made; this case is not an H3 positive or negative sample.",
        "    behavioral_disposition: NO_BEHAVIORAL_CLAIM",
        "    behavioral_rationale: |",
        "      No independent judgement of the candidate's correctness is recorded here. The H2",
        "      acceptance transition for this pair is measured by the eligibility validator, which",
        "      is a statement about the acceptance, not about the candidate.",
        "    provenance:",
        "      resolver:",
        "        repository: FlapPearLabs/agent-engineering-governance",
        "        commands:",
        f"          - 'git rev-parse {base} {cand}'",
        f"          - 'git diff {base} {cand} --stat'",
        f"          - 'git merge-base --is-ancestor {cand} origin/main'",
        "      related_refs:",
        f"        - 'candidate subject: {subject}'",
        "      notes: |",
        (f"        EXTERNALIZED_ORACLE: base = original base {external['original_base'][:12]} + the "
         f"candidate's version of the externalized paths (admission/externalize.py); {stat}."
         if external else
         f"        candidate^ == base (single parent); {stat}." if len(parents) == 1 else
         f"        merge commit; base = first parent ({len(parents)} parents); {stat}."),
        f"        Reachable from origin/main={verified_main}.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(argv[1]).resolve()
    main_sha = git(root, "rev-parse", "origin/main").strip()
    external_map: dict = {}
    specs = argv[2:]
    if specs and specs[0].startswith("--externalized="):
        external_map = json.loads(Path(specs[0].split("=", 1)[1]).read_text())["externalized"]
        specs = specs[1:]
    for spec in specs:
        case_id, cand = spec.split("=", 1)
        sys.stdout.write(block(root, case_id, cand, main_sha, external_map.get(cand)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
