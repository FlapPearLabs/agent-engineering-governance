#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop hook — DURABILITY GUARD (contract §9; extends the V1.1.2 STATE_FLUSH guard).

Mechanical checks only (no network, no writes):

- STATE_FLUSH_COMPLETED=1 / PROJECT_STATE_SYNC_COMPLETED=1 markers → trusted as flushed
- uncommitted changes / unpushed commits            → STATE_FLUSH_REQUIRED (existing semantics)
- runtime project_state_dirty flag set              → DURABLE_STATE_SYNC_REQUIRED
- runtime graph_dirty flag set                      → CODEGRAPH_SYNC_REQUIRED_BEFORE_STOP
                                                      (sync ONCE; never a full init — contract §6.6)

The orchestrator AUTO-ADVANCES on these signals when authorization exists
(STATE_FLUSH → canonical owner → index → commit → push → tracker → remote verify).
Never commits/pushes itself; any failure exits 0, never blocks session end.
"""
import json
import os
import subprocess
import sys

import _continuity_state as cs


def git(args, cwd, timeout=10):
    try:
        return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, errors="replace")
    except Exception:
        return None


def stdin_cwd() -> str:
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return ""
        data = json.load(sys.stdin)
        if isinstance(data, dict):
            return data.get("cwd") or ""
    except Exception:
        pass
    return ""


def main() -> int:
    cwd = os.environ.get("ZCODE_PROJECT_DIR") or stdin_cwd() or os.getcwd()

    if os.environ.get("STATE_FLUSH_COMPLETED") == "1" \
            or os.environ.get("PROJECT_STATE_SYNC_COMPLETED") == "1":
        print_ctx("STATE_FLUSH_GUARD=PASS (marker present)")
        return 0

    issues = []
    top = git(["rev-parse", "--show-toplevel"], cwd)
    if top is None or top.returncode != 0:
        print_ctx("STATE_FLUSH_GUARD=PASS (not a git worktree)")
        return 0
    root = top.stdout.strip()

    st = git(["status", "--porcelain"], root)
    if st is not None and st.returncode == 0 and st.stdout.strip():
        issues.append("UNCOMMITTED_CHANGES=%d" % len(st.stdout.strip().splitlines()))
    ahead = git(["rev-list", "--count", "@{u}..HEAD"], root)
    if ahead is not None and ahead.returncode == 0:
        cnt = ahead.stdout.strip()
        if cnt and cnt != "0":
            issues.append("UNPUSHED_COMMITS=%s" % cnt)

    state = cs.load(root)
    if state.get("project_state_dirty"):
        issues.append("DURABLE_STATE_SYNC_REQUIRED")
    if state.get("graph_dirty"):
        issues.append("CODEGRAPH_SYNC_REQUIRED_BEFORE_STOP")

    ctx = ("STATE_FLUSH_REQUIRED: " + " ".join(issues) +
           " — run canonical STATE_FLUSH before ending session") if issues \
        else "STATE_FLUSH_GUARD=PASS"
    print_ctx(ctx)
    return 0


def print_ctx(ctx: str) -> None:
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "Stop", "additionalContext": ctx,
    }}) + "\n")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            print_ctx("STATE_FLUSH_GUARD=ERROR (non-blocking)")
        except Exception:
            pass
    sys.exit(0)
