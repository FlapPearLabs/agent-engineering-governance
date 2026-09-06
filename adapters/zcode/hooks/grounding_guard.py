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
REQUIRED_RECEIPT_KEYS = ("TICKET", "RISK", "BASE_SHA", "GRAPH_MODE")


def git_head(worktree: str) -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=worktree, capture_output=True,
                           text=True, timeout=10, errors="replace")
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def base_is_fresh(base: str, head: str, worktree: str) -> tuple[bool, bool]:
    """(fresh, decided). Receipt stays fresh while the grounded BASE_SHA is an
    ancestor of HEAD — the worker's own commits do NOT invalidate grounding
    (contract §7 gates the FIRST meaningful write, not every commit).
    decided=False means git could not answer; caller falls back to equality."""
    if not base or not head:
        return True, True  # nothing to compare against
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", base, head],
                           cwd=worktree, capture_output=True, text=True,
                           timeout=10, errors="replace")
    except Exception:
        return base == head, True
    if r.returncode == 0:
        return True, True
    if r.returncode == 1:
        return False, True
    return base == head, True  # git error: conservative fallback


def decide(file_path: str, risk: str, worktree: str) -> tuple[str, str]:
    """Returns (decision, detail). decision ∈ ALLOW / ALLOW_MANUAL / BLOCK."""
    risk = str(risk or LOW).upper()
    if risk not in RISK_ORDER or RISK_ORDER[risk] < RISK_ORDER["MEDIUM"]:
        return "ALLOW", "risk=%s below grounding threshold" % risk
    if not file_path or cs.classify(file_path) != "graph":
        return "ALLOW", "non-production or unspecified target"

    state = cs.load(worktree)
    receipt = state.get("grounding_receipt")
    if receipt is None:
        return "BLOCK", ("CODEGRAPH_GROUNDING_REQUIRED risk=%s — orchestrator: fresh graph → "
                         "grounding → set-grounding receipt (or MANUAL_GROUNDING_RECEIPT via "
                         "--mode manual) → continue" % risk)
    # Fail-CLOSED for malformed receipts: a truncated/hand-edited receipt must
    # never be mistaken for a valid one (contract §7 — missing grounding blocks).
    if not isinstance(receipt, dict) or any(k not in receipt for k in REQUIRED_RECEIPT_KEYS):
        return "BLOCK", ("GROUNDING_RECEIPT_INVALID risk=%s — receipt malformed (required keys: "
                         "%s); re-ground before writing" % (risk, "/".join(REQUIRED_RECEIPT_KEYS)))

    head = git_head(worktree)
    base = str(receipt.get("BASE_SHA") or "")
    if not base:
        return "BLOCK", ("GROUNDING_RECEIPT_INVALID risk=%s — BASE_SHA empty; re-ground before "
                         "writing" % risk)
    fresh, _decided = base_is_fresh(base, head, worktree)
    if not fresh:
        return "BLOCK", ("GROUNDING_RECEIPT_STALE BASE_SHA=%s HEAD=%s — grounded base left the "
                         "HEAD ancestry; re-ground at the current base before writing"
                         % (base, head))
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
