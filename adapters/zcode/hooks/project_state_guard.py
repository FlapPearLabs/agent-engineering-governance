#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart hook — PROJECT STATE GUARD (contract §2, §9).

Mechanical detection only (no network, no writes, no reasoning):

- not a git worktree            → PROJECT_CONTINUITY=NOT_A_GIT_REPO (no-op)
- .agent/project-state.json missing
                                → PROJECT_CONTINUITY_INITIALIZATION_REQUIRED
                                  (orchestrator auto-executes lazy adoption /
                                  new-repo initialization; never asks the user)
- present + contract_version == supported
                                → PROJECT_CONTINUITY_INITIALIZED
- present + version 0 (pre-contract stub, no normative v0 schema existed)
                                → SAFE_MIGRATION note (regenerate from discovery)
- present + anything else unsupported
                                → PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED
                                  (never silently destroy old data)

Also reports the index's own last verified remote SHA and a DEFERRED hint when
no git remote exists. Full schema validation is delegated to
scripts/validate_project_state.py (run by the orchestrator / tests / CI).
Any failure exits 0 and never blocks session start.
"""
import json
import os
import subprocess
import sys

SUPPORTED_VERSIONS = {1}

REQUIRED_TOP_KEYS = [
    "contract_version", "project_identity", "remote", "default_branch",
    "canonical_documents", "execution_control_plane", "recovery_snapshot",
    "codegraph_policy",
]


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


def emit(ctx: str) -> None:
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart", "additionalContext": ctx,
    }}) + "\n")


def main() -> int:
    cwd = os.environ.get("ZCODE_PROJECT_DIR") or stdin_cwd() or os.getcwd()

    top = git(["rev-parse", "--show-toplevel"], cwd)
    if top is None or top.returncode != 0:
        emit("PROJECT_CONTINUITY=NOT_A_GIT_REPO")
        return 0
    root = top.stdout.strip()

    state_file = os.path.join(root, ".agent", "project-state.json")
    if not os.path.isfile(state_file):
        emit("PROJECT_CONTINUITY_INITIALIZATION_REQUIRED "
             "EXECUTE=lazy-adoption-or-new-repo-bootstrap (auto; do not ask the user)")
        return 0

    try:
        data = json.loads(open(state_file, encoding="utf-8").read())
        version = data.get("contract_version")
    except Exception:
        version = None

    if not isinstance(version, int) or version not in SUPPORTED_VERSIONS:
        if version == 0:
            # pre-contract stub: no normative schema ever existed for v0, so the
            # only safe repair is regenerate-from-discovery (nothing to destroy)
            emit("PROJECT_CONTINUITY=SAFE_MIGRATION contract_version=0 "
                 "(pre-contract stub; regenerate the index from repo discovery)")
        else:
            emit("PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED contract_version=%r "
                 "(unsupported/incompatible; do not silently destroy old data)" % version)
        return 0

    remotes = git(["remote"], root)
    remote_note = "REMOTE_STATE_SYNC=DEFERRED (no git remote configured)" \
        if remotes is None or not (remotes.stdout or "").strip() else ""
    parts = [
        "PROJECT_CONTINUITY_INITIALIZED=YES",
        "CONTRACT_VERSION=%s" % version,
        "LAST_VERIFIED_REMOTE_SHA=%s" % (data.get("recovery_snapshot", {})
                                         .get("last_verified_remote_sha", "") or "NONE"),
        "NEXT_LEGAL_ACTION=%s" % (data.get("recovery_snapshot", {})
                                  .get("next_legal_action", "") or "UNSPECIFIED"),
    ]
    if remote_note:
        parts.append(remote_note)
    emit(" ".join(parts))
    return 0


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            emit("PROJECT_CONTINUITY=GUARD_ERROR (non-blocking)")
        except Exception:
            pass
    sys.exit(0)
