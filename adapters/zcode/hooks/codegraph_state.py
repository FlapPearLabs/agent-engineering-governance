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
  python codegraph_state.py pre-query              legacy JIT entry — DELEGATES to
                                                   codegraph_lifecycle decide(intent=query)
                                                   (ONE LIFECYCLE → ONE DECISION SURFACE)

Any failure exits 0 (hooks must never block the runtime).
"""
import json
import os
import subprocess
import sys

import _continuity_state as cs

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Replace"}


def repo_main_dir(worktree):
    """Canonical repo working dir (the MODE A graph owner). Local copy so the
    PostToolUse marker never depends on importing the lifecycle module."""
    try:
        r = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                           cwd=worktree, capture_output=True, text=True, timeout=10,
                           errors="replace")
        if r.returncode == 0 and r.stdout.strip():
            return os.path.dirname(r.stdout.strip()) or worktree
    except Exception:
        pass
    return worktree


def git_head(worktree):
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=worktree, capture_output=True,
                           text=True, timeout=10, errors="replace")
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _flag(args, name, default=""):
    return args[args.index(name) + 1] if name in args and len(args) > args.index(name) + 1 \
        else default


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
                # review R5-F2: the dirty-state truth table — a canonical (main
                # checkout) or MODE B lane source edit marks the graph that
                # edit actually dirties; an ordinary MODE A lane edit is
                # CANDIDATE DELTA (fresh git diff is the evidence), never a
                # lane CodeGraph sync requirement (coverage=BASE_ONLY+DELTA_BY_DIFF).
                main_dir = repo_main_dir(worktree)
                is_lane = os.path.realpath(worktree) != os.path.realpath(main_dir)
                lane_mode = (os.environ.get("ZCODE_CODEGRAPH_LANE_MODE") or "A").upper()
                if is_lane and lane_mode == "A":
                    state["candidate_delta_dirty"] = True
                    mark = ("CANDIDATE_DELTA_DIRTY=YES (MODE A lane — no lane CodeGraph sync "
                            "exists; canonical graph coverage=BASE_ONLY+DELTA_BY_DIFF)")
                else:
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
            "CANDIDATE_DELTA_DIRTY=%s" % ("YES" if state.get("candidate_delta_dirty") else "NO"),
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
        # Review F5: durability is a three-level ladder, never collapsed into
        # "done". A receipt is always bound to the exact HEAD it flushed and a
        # timestamp, so any later meaningful transition stales it.
        state["project_state_dirty"] = False
        state["last_state_sync_at"] = cs.now_utc()
        if "--head" in args:
            state["last_state_sync_head"] = args[args.index("--head") + 1]
        if "--event" in args:
            state["last_state_sync_event"] = args[args.index("--event") + 1]
        level = "LOCAL_DURABLE"
        if "--remote-verified" in args:
            level = "REMOTE_VERIFIED"
        elif "--pushed" in args:
            level = "REMOTE_PUSHED"
        deferred = "--deferred" in args
        head = state.get("last_state_sync_head") or git_head(worktree)
        receipt_extra = {}
        if deferred:
            # review R4-A1: REMOTE_STATE_SYNC=DEFERRED is a FAILURE receipt,
            # never a naked bypass — it must bind a real remote failure
            # (HEAD_SHA + REMOTE_OPERATION + FAILURE_CLASS + ATTEMPTED_AT) or
            # it is rejected outright; a reachable remote can never be
            # "deferred" away from remote verify.
            evidence = {
                "HEAD_SHA": head,
                "REMOTE_OPERATION": _flag(args, "--remote-operation"),
                "FAILURE_CLASS": _flag(args, "--failure-class"),
                "ATTEMPTED_AT": _flag(args, "--attempted-at"),
            }
            missing = sorted(k for k, v in evidence.items() if not v)
            if missing:
                out("ERROR=REMOTE_DEFERRED_EVIDENCE_REQUIRED missing=%s REMOTE_SYNC=NOT_DEFERRED "
                    "(flags: --head/--remote-operation/--failure-class/--attempted-at; a naked "
                    "--deferred is rejected)" % ",".join(missing))
                return 2
            receipt_extra = {
                "remote_operation": evidence["REMOTE_OPERATION"],
                "failure_class": evidence["FAILURE_CLASS"],
                "attempted_at": evidence["ATTEMPTED_AT"],
            }
        state["remote_durability"] = {
            "level": "DEFERRED" if deferred else level,
            "deferred": deferred,
            "head_sha": head,
            "at": cs.now_utc(),
        }
        state["remote_durability"].update(receipt_extra)
        cs.save(worktree, state)
        out("PROJECT_STATE_SYNC_RECEIPT RECORDED LOCAL_DURABLE=YES "
            "REMOTE_DURABILITY=%s REMOTE_SYNC=%s HEAD_SHA=%s"
            % (state["remote_durability"]["level"],
               "DEFERRED" if deferred else "PENDING_VERIFY", head))
        return 0

    if cmd == "set-grounding":
        receipt = {"created_at": cs.now_utc()}
        for flag, key in (("--ticket", "TICKET"), ("--risk", "RISK"), ("--base-sha", "BASE_SHA"),
                          ("--mode", "GRAPH_MODE"), ("--graph-base-sha", "GRAPH_BASE_SHA"),
                          ("--seam", "TARGET_SEAM"),
                          ("--direct-targets", "DIRECT_TARGETS"),
                          ("--upstream", "UPSTREAM_PRODUCERS"),
                          ("--callers", "CALLERS"), ("--callees", "CALLEES"),
                          ("--downstream", "DOWNSTREAM_CONSUMERS"),
                          ("--impact", "IMPACT"), ("--affected", "AFFECTED"),
                          ("--state-owner", "STATE_OWNER"),
                          ("--identity-owner", "IDENTITY_OWNER"),
                          ("--validation-owner", "VALIDATION_OWNER"),
                          ("--surface", "EXPECTED_EDIT_SURFACE"),
                          ("--out-of-scope", "OUT_OF_SCOPE")):
            if flag in args:
                receipt[key] = args[args.index(flag) + 1]
        # generic passthrough so orchestrators can supply any §7 field explicitly
        # (values may be "NONE"/"UNKNOWN" — honesty about gaps, not absence of
        # the field; review F4)
        i = 0
        while i < len(args):
            if args[i] == "--field" and i + 1 < len(args) and "=" in args[i + 1]:
                k, _, v = args[i + 1].partition("=")
                receipt[k.strip()] = v.strip()
                i += 2
                continue
            i += 1
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
        # review R4-B: ONE LIFECYCLE → ONE DECISION SURFACE. This legacy entry
        # point no longer owns any init/sync decision (its old
        # ".codegraph missing → INIT_ONCE_ALLOWED" shortcut violated the
        # single-decision-surface rule and the MODE A lane invariants); it
        # delegates to the canonical lifecycle decide(intent=query).
        try:
            import codegraph_lifecycle as cl
        except Exception:
            out("CODEGRAPH_LIFECYCLE_UNAVAILABLE SYNC_DECISION=UNKNOWN "
                "(fail-closed: no local init/sync judgement)")
            return 0
        dec, detail = cl.decide("query", worktree)
        out("CODEGRAPH_LIFECYCLE_DECISION=%s INTENT=query %s" % (dec, detail))
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
