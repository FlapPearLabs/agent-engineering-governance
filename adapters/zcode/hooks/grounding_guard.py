#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse hook — GROUNDING GUARD (contract §7; best-effort mechanical tripwire).

Rule: RISK >= MEDIUM + production-source write + GROUNDING_RECEIPT missing
      → block with CODEGRAPH_GROUNDING_REQUIRED. The orchestrator then runs
      fresh graph → grounding → receipt → continue, without asking the user.
Manual fallback: CodeGraph unavailable → MANUAL_GROUNDING_RECEIPT (mode=manual)
      → allowed (MODE C semantics, codegraph-grounding.md §4).

Adapter contract (documented, verified by tests):
- exit 0 = allow, exit 2 = request block. If the runtime does not map exit 2
  to a deny decision, the guard degrades to advisory context — the AUTHORITATIVE
  gate remains the orchestrator discipline (contract §7); this hook only makes
  forgetting it mechanically visible.
- fail-open: any parse/internal error → exit 0 (never wedges the runtime).

Input: runtime stdin JSON (tool_name + tool_input.file_path) or CLI flags:
  python grounding_guard.py --file src/app.py --risk MEDIUM
Risk source: --risk flag, else env ZCODE_TICKET_RISK, else LOW.
"""
import json
import os
import subprocess
import sys

import _continuity_state as cs

LOW = "LOW"
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def git_head(worktree: str) -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=worktree, capture_output=True,
                           text=True, timeout=10, errors="replace")
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def decide(file_path: str, risk: str, worktree: str) -> tuple[str, str]:
    """Returns (decision, detail). decision ∈ ALLOW / ALLOW_MANUAL / BLOCK."""
    risk = str(risk or LOW).upper()
    if risk not in RISK_ORDER or RISK_ORDER[risk] < RISK_ORDER["MEDIUM"]:
        return "ALLOW", "risk=%s below grounding threshold" % risk
    if not file_path or cs.classify(file_path) != "graph":
        return "ALLOW", "non-production or unspecified target"

    state = cs.load(worktree)
    receipt = state.get("grounding_receipt") or None
    if not receipt:
        return "BLOCK", ("CODEGRAPH_GROUNDING_REQUIRED risk=%s — orchestrator: fresh graph → "
                         "grounding → set-grounding receipt (or MANUAL_GROUNDING_RECEIPT via "
                         "--mode manual) → continue" % risk)

    head = git_head(worktree)
    base = str(receipt.get("BASE_SHA", ""))
    if head and base and head != base:
        return "BLOCK", ("GROUNDING_RECEIPT_STALE BASE_SHA=%s HEAD=%s — re-ground at current "
                         "base before writing" % (base, head))
    mode = str(receipt.get("GRAPH_MODE", "graph"))
    if mode == "manual":
        return "ALLOW_MANUAL", "MANUAL_GROUNDING_RECEIPT present TICKET=%s" % receipt.get("TICKET", "")
    if state.get("graph_dirty"):
        return "ALLOW", ("GROUNDING_RECEIPT present TICKET=%s; note GRAPH_DIRTY=YES — "
                         "JIT sync once before trusting graph queries" % receipt.get("TICKET", ""))
    return "ALLOW", "GROUNDING_RECEIPT present TICKET=%s" % receipt.get("TICKET", "")


def main() -> int:
    args = sys.argv[1:]
    file_path = risk = ""
    if "--file" in args:
        file_path = args[args.index("--file") + 1]
    if "--risk" in args:
        risk = args[args.index("--risk") + 1]
    worktree = os.environ.get("ZCODE_PROJECT_DIR") or os.getcwd()

    if not file_path:  # hook mode: read runtime stdin payload
        try:
            if sys.stdin is not None and not sys.stdin.isatty():
                payload = json.load(sys.stdin)
                if isinstance(payload, dict):
                    ti = payload.get("tool_input") or {}
                    file_path = (ti.get("file_path") or ti.get("path")
                                 or payload.get("file_path") or "") if isinstance(ti, dict) else ""
                    worktree = payload.get("cwd") or worktree
        except Exception:
            pass  # fail-open
    risk = risk or os.environ.get("ZCODE_TICKET_RISK", LOW)

    decision, detail = decide(file_path, risk, worktree)
    line = "GROUNDING_GUARD_DECISION=%s %s" % (decision, detail)
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": line,
    }, "decision_line": line}) + "\n")
    return 2 if decision == "BLOCK" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # fail-open, always
        sys.exit(0)
