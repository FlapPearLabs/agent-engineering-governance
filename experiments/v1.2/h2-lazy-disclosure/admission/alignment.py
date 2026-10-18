#!/usr/bin/env python3
"""Task-text <-> oracle ALIGNMENT gate for document-deliverable requests (Freeze v2, FZ-ADM-1).

A DOC_TEXT oracle checks that the deliverable document contains specific text. A worker sees only
the task text (the ticket), so a literal the oracle requires but the ticket never states can only
be hit by luck — both arms fail and the task carries no signal. This gate makes that mechanical:

  REQUIRED  := every string literal (>= MIN_LEN chars, from the oracle's AST) that occurs in the
               CANDIDATE's version of a document in the worker's scope — text the oracle demands
               and the historical deliverable supplied.
  TASK_TEXT := the GitHub issue the candidate commit names ("Issue #N" / "(#N)" in its message),
               read-only via `gh issue view`.
  ALIGNED   := REQUIRED is non-empty and every literal occurs in TASK_TEXT (whitespace-normalised).

Anything else is NOT_ALIGNED (with the missing literals listed) or NO_TICKET. This gate can only
REMOVE tasks from Freeze v2's selection; it never adds one, and it changes no Schema-v2 verdict.

Scope: HIDDEN oracles only (a DELTA_ADDED basis, placed by the acceptance harness after the run).
A FRAMEWORK_FROZEN oracle sits in the worker's own tree — the worker can read it, so the task text
is "make <oracle> pass without modifying it" and alignment holds by construction
(VISIBLE_FROZEN_ORACLE).

Usage:  alignment.py <repo_root> <ledger.json> [...] --out <alignment.json>
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from pathlib import Path

MIN_LEN = 6
ISSUE_RE = re.compile(r"(?:Issue\s*#|\(#)(\d+)\)?", re.I)
REPO = "FlapPearLabs/agent-engineering-governance"


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True).stdout


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def literals(source: str) -> set[str]:
    out: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = norm(node.value)
            if len(v) >= MIN_LEN:
                out.add(v)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root")
    ap.add_argument("ledgers", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv[1:])
    root = Path(a.repo_root).resolve()
    rows = []
    tickets: dict[str, str] = {}
    for lp in a.ledgers:
        for r in json.loads(Path(lp).read_text(encoding="utf-8"))["rows"]:
            if not r["SCHEMA_V2_RESULT"].endswith("REQUEST_VALID"):
                continue
            if r["OBSERVATION_ORACLE_KIND"] not in ("DOC_TEXT", "DOC_OR_DATA"):
                continue
            cand = r["CANDIDATE_SHA"]
            oracle = (r["FROZEN_ACCEPTANCE_DEFINITION"] or {}).get("path")
            if not str(r.get("ORACLE_EXTERNALIZATION", "")).startswith("REQUIRED_AT_FREEZE_V2"):
                rows.append({"CASE_ID": r["CASE_ID"], "CANDIDATE_SHA": cand, "ORACLE": oracle,
                             "ALIGNMENT": "VISIBLE_FROZEN_ORACLE"})
                continue
            docs = [p for p in r["WORKER_SCOPE"] if p.endswith(".md")]
            row = {"CASE_ID": r["CASE_ID"], "CANDIDATE_SHA": cand, "ORACLE": oracle}
            if not oracle:
                row.update(ALIGNMENT="NO_TEXT_ORACLE", note="the basis is not a test file")
                rows.append(row)
                continue
            doc_text = norm(" ".join(git(root, "show", f"{cand}:{d}") for d in docs))
            required = sorted(x for x in literals(git(root, "show", f"{cand}:{oracle}"))
                              if x in doc_text)
            numbers = ISSUE_RE.findall(git(root, "log", "-1", "--format=%B", cand))
            row["REQUIRED_LITERALS"] = len(required)
            if not numbers:
                row.update(ALIGNMENT="NO_TICKET")
                rows.append(row)
                continue
            body = ""
            for n in numbers:
                if n not in tickets:
                    view = subprocess.run(["gh", "issue", "view", n, "--repo", REPO, "--json",
                                           "title,body"], capture_output=True, text=True)
                    tickets[n] = (norm(" ".join(json.loads(view.stdout).values()))
                                  if view.returncode == 0 else "")
                body += " " + tickets[n]
            missing = [x for x in required if x not in body]
            row.update(TICKETS=numbers, MISSING=len(missing), MISSING_SAMPLE=missing[:5],
                       ALIGNMENT=("ALIGNED" if required and not missing else "NOT_ALIGNED"))
            rows.append(row)
    summary = {}
    for r in rows:
        summary[r["ALIGNMENT"]] = summary.get(r["ALIGNMENT"], 0) + 1
    Path(a.out).write_text(json.dumps({"program": "admission/alignment.py", "min_len": MIN_LEN,
                                       "summary": summary, "rows": rows}, indent=1,
                                      ensure_ascii=False) + "\n", encoding="utf-8")
    print("ALIGNMENT", json.dumps(summary))
    for r in rows:
        print(f"  {r['CASE_ID'][:44]:44s} {r['ALIGNMENT']:15s} required={r.get('REQUIRED_LITERALS')} "
              f"missing={r.get('MISSING')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
