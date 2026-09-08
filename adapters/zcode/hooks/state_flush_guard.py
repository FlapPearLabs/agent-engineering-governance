#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stop hook — DURABILITY GUARD (contract §5/§9; extends the V1.1.2 STATE_FLUSH guard).

Mechanical checks only (no network, no writes):

- STATE_FLUSH_COMPLETED=1 / PROJECT_STATE_SYNC_COMPLETED=1 env markers are
  EVIDENCE ONLY (review R4-A2): even when bound to the current HEAD via
  STATE_FLUSH_HEAD_SHA they never early-return — git dirty, ahead/unpushed,
  project_state_dirty, graph_dirty and remote durability are ALWAYS evaluated.
- uncommitted changes / unpushed commits            → STATE_FLUSH_REQUIRED (existing semantics)
- runtime project_state_dirty flag set              → DURABLE_STATE_SYNC_REQUIRED
  (a new meaningful transition also stales any earlier remote_durability receipt)
- remote_durability receipt (review F5 ladder + R5-F4/F6):
    missing on a remote-backed project              → REMOTE_VERIFICATION_REQUIRED
    no configured remote at all                     → REMOTE_REQUIRED
                                                      (REMOTE IS REQUIRED, NOT OPTIONAL —
                                                      a no-remote stop is never PASS; the
                                                      only honest terminal is a no-remote
                                                      DEFERRED failure receipt bound to HEAD)
    receipt without a HEAD binding / bound to a moved HEAD
                                                    → REMOTE_RECEIPT_INVALID
                                                      (R5-F6: fail closed on HEAD — never PASS)
    level REMOTE_VERIFIED (head-bound)              → REMOTE_VERIFIED=YES (clean terminal)
    deferred + failure receipt (head-bound)         → REMOTE_STATE_SYNC=DEFERRED (honest terminal)
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

    # review F5: env flush markers are only meaningful when bound to the
    # current HEAD. review R4-A2: a marker is EVIDENCE, never a BYPASS — even
    # a perfectly bound marker must not early-return; every durability check
    # below always runs.
    marker = (os.environ.get("STATE_FLUSH_COMPLETED") == "1"
              or os.environ.get("PROJECT_STATE_SYNC_COMPLETED") == "1")
    note = ""
    if marker:
        bound = os.environ.get("STATE_FLUSH_HEAD_SHA", "")
        if head and bound == head:
            note = "BOUND_FLUSH_MARKER evidence HEAD_SHA=%s (marker is evidence, not bypass)" % head
        elif not bound:
            note = "UNBOUND_FLUSH_MARKER (marker present without HEAD binding)"
        else:
            note = "STALE_FLUSH_MARKER bound=%s head=%s" % (bound, head)

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
        elif not rd.get("head_sha") or not head:
            # review R5-F6: terminal receipts fail CLOSED on HEAD — a receipt
            # without a HEAD binding must never become PASS (this environment
            # has repeatedly observed transient broken HEAD refs)
            issues.append("REMOTE_RECEIPT_INVALID (terminal durability receipt without a HEAD "
                          "binding — review R5-F6: missing binding must never PASS)")
        elif rd.get("head_sha") != head:
            # review R5-F6: a receipt bound to a HEAD that has since moved is
            # INVALID (a later meaningful transition staled it) — fail closed
            issues.append("REMOTE_RECEIPT_INVALID bound=%s head=%s — the receipt is stale "
                          "(a later meaningful transition moved HEAD); re-sync and re-verify "
                          "(review R5-F6: fail closed on HEAD)"
                          % (rd.get("head_sha"), head))
        elif rd.get("deferred"):
            # review R4-A1: a DEFERRED terminal is only honest when it carries
            # the failure receipt; a naked deferred must not satisfy stop
            if not (rd.get("remote_operation") and rd.get("failure_class")
                    and rd.get("attempted_at")):
                issues.append("REMOTE_DEFERRED_EVIDENCE_INVALID (deferred without a failure "
                              "receipt HEAD_SHA/REMOTE_OPERATION/FAILURE_CLASS/ATTEMPTED_AT — "
                              "run the remote sync or record the failure honestly)")
        elif rd.get("level") != "REMOTE_VERIFIED":
            issues.append("REMOTE_VERIFICATION_REQUIRED level=%s" % rd.get("level"))
    else:
        # review R5-F4: REMOTE IS REQUIRED, NOT OPTIONAL — a governed repo with
        # no configured remote is NOT a clean stop. New-repo bootstrap should
        # establish remote → push → verify before durable completion; the only
        # honest alternative terminal is a no-remote DEFERRED failure receipt
        # bound to the current HEAD.
        rd = state.get("remote_durability")
        honest = (isinstance(rd, dict) and rd.get("deferred")
                  and rd.get("remote_operation") and rd.get("failure_class")
                  and rd.get("attempted_at")
                  and bool(head) and rd.get("head_sha") == head)
        if not honest:
            issues.append("REMOTE_REQUIRED (no remote configured — REMOTE IS REQUIRED, NOT "
                          "OPTIONAL; establish remote → push → verify, or record an honest "
                          "no-remote DEFERRED failure receipt bound to HEAD)")

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
        ctx = ("STATE_FLUSH_GUARD=PASS REMOTE_STATE_SYNC=DEFERRED (no remote configured; "
               "honest no-remote failure receipt on file)")
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
