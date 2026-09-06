#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PostToolUse hook + CLI — CODEGRAPH / PROJECT-STATE dirty markers (contract §6.6, §9).

Hook mode (stdin JSON from runtime): a production-source edit sets
CODEGRAPH_DIRTY; a canonical state-doc edit (.agent/project-state.json or
target/spec/adr/spike/architecture markdown) sets PROJECT_STATE_DIRTY.
Markers only — never a per-edit sync, never a full index (contract §6.2/§6.6).

CLI mode (for orchestrators and the synthetic test matrix):

  python codegraph_state.py status                 show flags for cwd
  python codegraph_state.py record-event EVENT     TICKET_STARTED / PR_CREATED_OR_UPDATED / ...
  python codegraph_state.py mark-graph-synced      clear GRAPH_DIRTY (--head SHA to record)
  python codegraph_state.py record-state-sync      clear PROJECT_STATE_DIRTY (receipt)
  python codegraph_state.py set-grounding ...      store GROUNDING_RECEIPT (runtime-local)
  python codegraph_state.py pre-query              JIT rule: SYNC_REQUIRED once / NO_SYNC / INDEX_MISSING

Any failure exits 0 (hooks must never block the runtime).
"""
import json
import os
import sys

import _continuity_state as cs

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Replace"}


def stdin_json() -> dict:
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return {}
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def emit(ctx: str) -> None:
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse", "additionalContext": ctx,
    }}) + "\n")


def hook_mode() -> int:
    payload = stdin_json()
    worktree = payload.get("cwd") or cs.worktree_from_env_or_cwd()
    tool = payload.get("tool_name") or payload.get("tool") or ""
    file_path = ""
    ti = payload.get("tool_input")
    if isinstance(ti, dict):
        file_path = ti.get("file_path") or ti.get("path") or ""
    file_path = file_path or payload.get("file_path") or ""
    if tool in EDIT_TOOLS and file_path:
        kind = cs.classify(file_path)
        if kind:
            state = cs.load(worktree)
            if kind == "graph":
                state["graph_dirty"] = True
                mark = "CODEGRAPH_DIRTY=YES"
            else:
                state["project_state_dirty"] = True
                mark = "PROJECT_STATE_DIRTY=YES"
            cs.save(worktree, state)
            emit(mark)
            return 0
    emit("CONTINUITY_MARKERS=NOOP")
    return 0


def cli(args: list[str]) -> int:
    worktree = cs.worktree_from_env_or_cwd()
    cmd = args[0] if args else "status"
    state = cs.load(worktree)

    def out(*parts: str) -> None:
        print(" ".join(p for p in parts if p))

    if cmd == "status":
        out("GRAPH_DIRTY=%s" % ("YES" if state.get("graph_dirty") else "NO"),
            "PROJECT_STATE_DIRTY=%s" % ("YES" if state.get("project_state_dirty") else "NO"),
            "LAST_SYNC_HEAD=%s" % state.get("last_sync_head", ""),
            "GROUNDING_RECEIPT=%s" % ("present" if state.get("grounding_receipt") else "absent"))
        return 0

    if cmd == "record-event":
        if len(args) < 2:
            out("ERROR=EVENT_REQUIRED")
            return 0
        state["project_state_dirty"] = True
        state["last_state_sync_event"] = args[1]
        cs.save(worktree, state)
        out("PROJECT_STATE_DIRTY=YES EVENT=%s" % args[1])
        return 0

    if cmd == "mark-graph-synced":
        state["graph_dirty"] = False
        if "--head" in args:
            state["last_sync_head"] = args[args.index("--head") + 1]
        state["last_sync_at"] = cs.now_utc()
        cs.save(worktree, state)
        out("GRAPH_DIRTY=NO LAST_SYNC_HEAD=%s" % state.get("last_sync_head", ""))
        return 0

    if cmd == "record-state-sync":
        state["project_state_dirty"] = False
        state["last_state_sync_at"] = cs.now_utc()
        if "--head" in args:
            state["last_state_sync_head"] = args[args.index("--head") + 1]
        if "--event" in args:
            state["last_state_sync_event"] = args[args.index("--event") + 1]
        cs.save(worktree, state)
        out("PROJECT_STATE_SYNC_RECEIPT RECORDED REMOTE_SYNC=%s"
            % ("DEFERRED" if "--deferred" in args else "PENDING_VERIFY"))
        return 0

    if cmd == "set-grounding":
        receipt = {"created_at": cs.now_utc()}
        for flag, key in (("--ticket", "TICKET"), ("--risk", "RISK"), ("--base-sha", "BASE_SHA"),
                          ("--mode", "GRAPH_MODE"), ("--seam", "TARGET_SEAM"),
                          ("--surface", "EXPECTED_EDIT_SURFACE"),
                          ("--out-of-scope", "OUT_OF_SCOPE")):
            if flag in args:
                receipt[key] = args[args.index(flag) + 1]
        if "--clear" in args:
            state["grounding_receipt"] = None
            cs.save(worktree, state)
            out("GROUNDING_RECEIPT=CLEARED")
            return 0
        missing = [k for k in ("TICKET", "RISK", "BASE_SHA", "GRAPH_MODE") if k not in receipt]
        if missing:
            out("ERROR=GROUNDING_RECEIPT_INCOMPLETE missing=%s" % ",".join(missing))
            return 0
        state["grounding_receipt"] = receipt
        cs.save(worktree, state)
        out("GROUNDING_RECEIPT=STORED TICKET=%s RISK=%s MODE=%s"
            % (receipt["TICKET"], receipt["RISK"], receipt["GRAPH_MODE"]))
        return 0

    if cmd == "pre-query":
        # JIT sync rule (contract §6.6): query/review/blast-radius/Stop while dirty
        # → sync once; sync failure must NEVER fall back to full init (§6.6).
        index_dir = os.path.join(worktree, ".codegraph")
        if not os.path.isdir(index_dir):
            out("CODEGRAPH_INDEX_MISSING INIT_ONCE_ALLOWED")
            return 0
        if state.get("graph_dirty"):
            out("CODEGRAPH_SYNC_REQUIRED_ONCE")
        else:
            out("NO_SYNC")
        out("NO_INIT_REQUIRED")
        return 0

    out("ERROR=UNKNOWN_COMMAND %s" % cmd)
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--hook":
        return hook_mode()
    return cli(argv)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        try:
            emit("CONTINUITY_MARKERS=ERROR (non-blocking)")
        except Exception:
            pass
        sys.exit(0)
