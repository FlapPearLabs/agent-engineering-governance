#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop hook — DURABILITY GUARD (contract §5/§9; extends the V1.1.2 STATE_FLUSH guard).

Mechanical checks only (no network, no writes):

- STATE_FLUSH_COMPLETED=1 / PROJECT_STATE_SYNC_COMPLETED=1 env markers are only
  trusted when they bind the current HEAD via STATE_FLUSH_HEAD_SHA (review F5:
  a stale unbound marker must never permanently bypass later transitions).
- uncommitted changes / unpushed commits            → STATE_FLUSH_REQUIRED (existing semantics)
- runtime project_state_dirty flag set              → DURABLE_STATE_SYNC_REQUIRED
  (a new meaningful transition also stales any earlier remote_durability receipt)
- remote_durability receipt (review F5 ladder):
    missing on a remote-backed project              → REMOTE_VERIFICATION_REQUIRED
    bound HEAD != current HEAD                      → REMOTE_RECEIPT_STALE
    level REMOTE_VERIFIED                           → REMOTE_VERIFIED=YES (clean terminal)
    deferred                                        → REMOTE_STATE_SYNC=DEFERRED (honest terminal)
    LOCAL_DURABLE / REMOTE_PUSHED                   → REMOTE_VERIFICATION_REQUIRED level=…
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

    top = git(["rev-parse", "--show-toplevel"], cwd)
    if top is None or top.returncode != 0:
        print_ctx("STATE_FLUSH_GUARD=PASS (not a git worktree)")
        return 0
    root = top.stdout.strip()
    head = ""
    hr = git(["rev-parse", "HEAD"], root)
    if hr is not None and hr.returncode == 0:
        head = hr.stdout.strip()

    # Review F5: env flush markers are trusted ONLY when bound to the current
    # HEAD AND no later meaningful transition has re-dirtied the state.
    marker = (os.environ.get("STATE_FLUSH_COMPLETED") == "1"
              or os.environ.get("PROJECT_STATE_SYNC_COMPLETED") == "1")
    note = ""
    if marker:
        bound = os.environ.get("STATE_FLUSH_HEAD_SHA", "")
        pre_state = cs.load(root)
        if head and bound == head and not pre_state.get("project_state_dirty") \
                and not pre_state.get("graph_dirty"):
            print_ctx("STATE_FLUSH_GUARD=PASS (marker bound to HEAD_SHA=%s)" % head)
            return 0
        # unbound / stale marker → fall through and re-evaluate honestly
        note = "UNBOUND_FLUSH_MARKER (marker present without HEAD binding)" if not bound \
            else "STALE_FLUSH_MARKER bound=%s head=%s" % (bound, head)

    issues = []
    st = git(["status", "--porcelain"], root)
    if st is not None and st.returncode == 0 and st.stdout.strip():
        issues.append("UNCOMMITTED_CHANGES=%d" % len(st.stdout.strip().splitlines()))
    ahead = git(["rev-list", "--count", "@{u}..HEAD"], root)
    has_remote = False
    remotes = git(["remote"], root)
    if remotes is not None and (remotes.stdout or "").strip():
        has_remote = True
        if ahead is not None and ahead.returncode == 0:
            cnt = ahead.stdout.strip()
            if cnt and cnt != "0":
                issues.append("UNPUSHED_COMMITS=%s" % cnt)

    state = cs.load(root)
    if state.get("project_state_dirty"):
        issues.append("DURABLE_STATE_SYNC_REQUIRED")
    elif has_remote:
        rd = state.get("remote_durability")
        if not isinstance(rd, dict) or not rd.get("level"):
            issues.append("REMOTE_VERIFICATION_REQUIRED (no durability receipt)")
        elif rd.get("head_sha") and head and rd.get("head_sha") != head:
            issues.append("REMOTE_RECEIPT_STALE bound=%s head=%s — a later meaningful "
                          "transition invalidates the receipt; re-sync and re-verify"
                          % (rd.get("head_sha"), head))
        elif not rd.get("deferred") and rd.get("level") != "REMOTE_VERIFIED":
            issues.append("REMOTE_VERIFICATION_REQUIRED level=%s" % rd.get("level"))

    if state.get("graph_dirty"):
        issues.append("CODEGRAPH_SYNC_REQUIRED_BEFORE_STOP")

    if note:
        issues.insert(0, note)

    if issues:
        ctx = "STATE_FLUSH_REQUIRED: " + " ".join(issues) + \
              " — run canonical STATE_FLUSH before ending session"
    elif note:
        ctx = "STATE_FLUSH_GUARD=PASS (%s re-evaluated)" % note
    elif has_remote:
        rd = state.get("remote_durability") or {}
        ctx = ("STATE_FLUSH_GUARD=PASS REMOTE_VERIFIED=YES HEAD_SHA=%s"
               % (rd.get("head_sha") or head)) if rd.get("level") == "REMOTE_VERIFIED" \
            else "STATE_FLUSH_GUARD=PASS REMOTE_STATE_SYNC=DEFERRED"
    else:
        ctx = "STATE_FLUSH_GUARD=PASS"
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
