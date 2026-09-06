#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SessionStart hook — SESSION GOVERNANCE SYNC CHECK（机械同步/状态检测，不做任何 reasoning）。

状态集：SYNCED / BEHIND_FAST_FORWARDABLE / DIRTY / DIVERGED / REMOTE_UNAVAILABLE / GOVERNANCE_MISSING
行为：
- clean + behind      → 自动 fast-forward（--ff-only）
- dirty / diverged    → 绝不覆盖，报 GOVERNANCE_SYNC_BLOCKED
- fetch 失败          → REMOTE_UNAVAILABLE（GOVERNANCE_REMOTE_STATE=UNKNOWN，用本地最后已验证版本）
- checkout 缺失       → GOVERNANCE_MISSING（默认自动 clone canonical，ZCODE_GOVERNANCE_NO_AUTOCLONE=1 可关闭）

安全边界：不读不输出 secret；不触碰产品仓；不做 STATE_RESTORE/架构推理/GitHub 写操作；
任何异常都 exit 0（绝不阻塞会话启动）。
输出：stdout 一行 JSON {"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}。
"""
import json
import os
import subprocess
import sys

DEFAULT_URL = "https://github.com/FlapPearLabs/agent-engineering-governance.git"
# Machine-local default; built from the user home so no host identity/path is
# committed (RULES R2). Env overrides: ZCODE_GOVERNANCE_DIR / ZCODE_PROJECT_DIR.
DEFAULT_CHECKOUT = os.path.join(os.path.expanduser("~"), ".zcode", "workspace",
                                "default", "agent-engineering-governance")


def find_checkout():
    cands = []
    if os.environ.get("ZCODE_GOVERNANCE_DIR"):
        cands.append(os.environ["ZCODE_GOVERNANCE_DIR"])
    pd = os.environ.get("ZCODE_PROJECT_DIR")
    if pd:
        cands.append(os.path.join(pd, "agent-engineering-governance"))
    if os.environ.get("ZCODE_GOVERNANCE_DISABLE_DEFAULT") != "1":
        cands.append(DEFAULT_CHECKOUT)
    for c in cands:
        if c and os.path.isdir(os.path.join(c, ".git")):
            return c
    return None


def git(args, cwd, timeout=30):
    try:
        return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True,
                              timeout=timeout, errors="replace")
    except Exception:
        return None


def emit(state, local, remote, action, note=""):
    ctx = "GOVERNANCE_SYNC=%s LOCAL_SHA=%s REMOTE_SHA=%s ACTION=%s" % (
        state, local or "N/A", remote or "N/A", action)
    if note:
        ctx += " NOTE=" + note
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": ctx,
    }}) + "\n")


def main():
    url = os.environ.get("ZCODE_GOVERNANCE_URL") or DEFAULT_URL
    gov = find_checkout()

    if gov is None:
        if os.environ.get("ZCODE_GOVERNANCE_NO_AUTOCLONE") != "1":
            pd = os.environ.get("ZCODE_PROJECT_DIR") or os.path.dirname(DEFAULT_CHECKOUT)
            dest = os.path.join(pd, "agent-engineering-governance")
            try:
                subprocess.run(["git", "clone", url, dest], capture_output=True,
                               text=True, timeout=90, check=True)
                gov = dest
            except Exception:
                gov = None
        if gov is None:
            return emit("GOVERNANCE_MISSING", "", "", "NONE",
                        "bootstrap delegated to orchestrator BOOTSTRAP checklist")

    st = git(["status", "--porcelain"], gov, 10)
    if st is None or st.returncode != 0:
        return emit("GOVERNANCE_MISSING", "", "", "NONE", "git status failed on checkout")
    dirty = bool(st.stdout.strip())

    head = git(["rev-parse", "HEAD"], gov, 10)
    local_sha = head.stdout.strip() if head is not None and head.returncode == 0 else ""

    fetched = git(["fetch", "origin"], gov, 45)
    if fetched is None or fetched.returncode != 0:
        return emit("REMOTE_UNAVAILABLE", local_sha, "", "KEEP_LOCAL",
                    "GOVERNANCE_REMOTE_STATE=UNKNOWN; using last verified local version")

    rm = git(["rev-parse", "origin/main"], gov, 10)
    remote_sha = rm.stdout.strip() if rm is not None and rm.returncode == 0 else ""

    if local_sha == remote_sha:
        if dirty:
            return emit("DIRTY", local_sha, remote_sha, "GOVERNANCE_SYNC_BLOCKED",
                        "uncommitted changes; up-to-date with remote; resolve manually")
        return emit("SYNCED", local_sha, remote_sha, "NONE")

    anc = git(["merge-base", "--is-ancestor", "HEAD", "origin/main"], gov, 10)
    if anc is not None and anc.returncode == 0:  # behind, fast-forwardable
        if dirty:
            return emit("DIRTY", local_sha, remote_sha, "GOVERNANCE_SYNC_BLOCKED",
                        "behind but uncommitted changes present; not auto-merged")
        ff = git(["merge", "--ff-only", "origin/main"], gov, 60)
        if ff is None or ff.returncode != 0:
            return emit("DIRTY", local_sha, remote_sha, "GOVERNANCE_SYNC_BLOCKED",
                        "ff-only merge failed")
        new = git(["rev-parse", "HEAD"], gov, 10)
        local_sha = new.stdout.strip() if new is not None and new.returncode == 0 else local_sha
        return emit("SYNCED", local_sha, remote_sha, "FAST_FORWARDED")

    return emit("DIVERGED", local_sha, remote_sha, "GOVERNANCE_SYNC_BLOCKED",
                "local HEAD and origin/main diverged; manual resolution required")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        try:
            emit("REMOTE_UNAVAILABLE", "", "", "KEEP_LOCAL", "hook internal error")
        except Exception:
            pass
    sys.exit(0)
