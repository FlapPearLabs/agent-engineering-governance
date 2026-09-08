#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse hook — SHELL PRE-GROUNDING ALLOWLIST (review R6-F3).

Problem the guard closes: the structured Edit/Write grounding guard is
insufficient because the worker also has Bash. A HIGH/MEDIUM production edit
performed through Bash must not bypass grounding, and must not smuggle
mutations/redirection/chaining through a supposedly read-only pre-grounding
command.

Semantics (fail closed before grounding, normal afterwards):

- grounding receipt present → exit 0 (normal authorized Bash returns)
- RISK < MEDIUM             → exit 0 (below the grounding threshold)
- non-production target     → exit 0 (receipts gate production writes, §7)
- otherwise, the command must belong to a STRICT read-only allowlist:
    git status / diff / log / show / rev-parse / merge-base / ls-files /
    branch --show-current
    rg / grep / find / ls / dir / cat / Get-Content
  AND must not contain any of:
    redirection (> >> < << | & ; && || newline backtick $()   ...)
    git mutation subcommands (add/commit/push/checkout/reset/clean/...)
    known file-mutation commands (rm/mv/cp/dd/mkdir/touch/sed -i/...)
  Anything not mechanically recognized → UNKNOWN_BASH_MUTABILITY → BLOCK.

This is a best-effort mechanical tripwire, exactly like grounding_guard.py:
- exit 0 = allow, exit 2 = request block. If the runtime does not map exit 2
  to a deny decision, the guard degrades to advisory context — the AUTHORITATIVE
  gate remains orchestrator discipline plus the lifecycle boundary checks
  (production_delta_present, R6-F3 defense in depth).
- fail-open on parse/internal errors: any exception → exit 0.

Input: runtime stdin JSON (tool_name + tool_input.command) or CLI flags:
  python bash_preflight_guard.py --command "git status" --risk HIGH
Risk source: --risk flag, else env ZCODE_TICKET_RISK, else LOW.
"""
import json
import os
import shlex
import sys

import _continuity_state as cs

LOW = "LOW"
RISK_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

# --- strict pre-grounding read-only allowlist ---------------------------------

# git subcommands that are mechanically read-only (exact-token match)
GIT_READONLY_SUBCOMMANDS = {
    "status", "diff", "log", "show", "rev-parse", "merge-base", "ls-files",
    "branch",  # branch is further restricted below: --show-current only
}
# non-git commands that are mechanically read-only
READONLY_COMMANDS = {
    "rg", "grep", "find", "ls", "dir", "cat", "Get-Content", "type", "head",
    "tail", "wc", "pwd", "which", "where", "git",
}
# command families that mutate files / state and can never pass pre-grounding
MUTATION_COMMANDS = {
    "rm", "del", "rd", "rmdir", "mv", "move", "cp", "copy", "xcopy",
    "robocopy", "dd", "mkdir", "touch", "truncate", "chmod", "chown",
    "attrib", "Set-Content", "Add-Content", "Out-File", "Remove-Item",
    "Move-Item", "Copy-Item", "New-Item", "Rename-Item",
}
# git subcommands that mutate the repo / worktree
GIT_MUTATION_SUBCOMMANDS = {
    "add", "commit", "push", "pull", "fetch", "merge", "rebase", "revert",
    "reset", "clean", "checkout", "switch", "restore", "stash", "cherry-pick",
    "am", "apply", "mv", "rm", "gc", "prune", "clone", "init", "worktree",
    "bisect", "filter-branch", "replace", "tag", "notes", "config",
    "remote", "submodule", "sparse-checkout", "update-index",
    "update-ref", "symbolic-ref", "reflog", "blame",  # blame writes .git/objects? no — excluded for strictness
}
# redirection / chaining / substitution markers — ANY occurrence rejects
CHAIN_MARKERS = ("<", ">", "|", "&", ";", "`", "\n", "\r")


def _is_pure_readonly_git(tokens):
    """True when `tokens` is a mechanically read-only git invocation."""
    if not tokens or tokens[0] != "git":
        return False
    rest = tokens[1:]
    while rest and rest[0].startswith("-"):
        return False  # global options make the family non-obvious → strict reject
    if not rest:
        return False
    sub = rest[0]
    if sub == "branch":
        # only the exact form `git branch --show-current` is provably read-only
        return rest[1:] == ["--show-current"]
    if sub in GIT_READONLY_SUBCOMMANDS:
        # `git diff`/`git log`/`git show` may legitimately take flags — but no
        # output-altering plumbing (never a pathspec to another command)
        return True
    return False


def is_readonly_command(tokens):
    """True when the token list is mechanically read-only under the strict
    pre-grounding allowlist. Unknown families fail closed at the caller."""
    if not tokens:
        return False
    cmd0 = tokens[0]
    if cmd0 == "git":
        return _is_pure_readonly_git(tokens)
    if cmd0 in MUTATION_COMMANDS or cmd0 in GIT_MUTATION_SUBCOMMANDS:
        return False
    if cmd0 in ("sed", "awk", "perl", "python", "python3", "node", "pwsh",
                "powershell", "bash", "sh", "cmd", "tee", "xargs", "findstr"):
        return False  # arbitrary script execution families → never pre-grounding
    if cmd0 in READONLY_COMMANDS:
        # a read-only reader may not spawn anything either: every further token
        # must not be a chained command (already enforced by CHAIN_MARKERS scan)
        return True
    return False  # UNKNOWN command family → fail closed


def contains_chain(text):
    """Any redirection / chaining / substitution marker → True. Backslash
    escapes cannot hide these from a shell, so a textual scan is the honest
    mechanical bar (shell quoting nuances are resolved AFTER grounding only)."""
    for m in CHAIN_MARKERS:
        if m in text:
            return True
    if "$(" in text:
        return True
    return False


def decide(command_text, risk, worktree):
    """Returns (decision, detail). decision ∈ ALLOW / BLOCK."""
    risk = str(risk or LOW).upper()
    if RISK_ORDER.get(risk, 0) < RISK_ORDER["MEDIUM"]:
        return "ALLOW", "risk=%s below grounding threshold" % risk

    state = cs.load(worktree)
    receipt = state.get("grounding_receipt")
    if isinstance(receipt, dict) and receipt.get("BASE_SHA"):
        # a valid grounding receipt exists → normal authorized Bash returns
        return "ALLOW", "GROUNDING_RECEIPT present TICKET=%s — normal Bash" \
            % receipt.get("TICKET", "")

    text = command_text or ""
    try:
        tokens = shlex.split(text, posix=True)
    except ValueError:
        return "BLOCK", ("UNKNOWN_BASH_MUTABILITY — unparseable shell syntax cannot be proven "
                         "read-only pre-grounding (review R6-F3)")
    if contains_chain(text):
        return "BLOCK", ("UNKNOWN_BASH_MUTABILITY — redirection/chaining/substitution is never "
                         "pre-grounding (review R6-F3: strict read-only allowlist)")
    if not tokens:
        return "ALLOW", "empty command"
    if not is_readonly_command(tokens):
        return "BLOCK", ("UNKNOWN_BASH_MUTABILITY — %r is not on the strict pre-grounding "
                         "read-only allowlist (allowed: git status/diff/log/show/rev-parse/"
                         "merge-base/ls-files/branch --show-current, rg/grep/find/ls/dir/cat/"
                         "Get-Content); ground first, then run normal Bash (review R6-F3)"
                         % " ".join(tokens[:3]))
    return "ALLOW", "read-only allowlist pre-grounding (%s)" % tokens[0]


def main() -> int:
    args = sys.argv[1:]
    command_text = risk = ""
    if "--command" in args:
        command_text = args[args.index("--command") + 1]
    if "--risk" in args:
        risk = args[args.index("--risk") + 1]
    worktree = os.environ.get("ZCODE_PROJECT_DIR") or os.getcwd()

    if not command_text:  # hook mode: read runtime stdin payload
        try:
            if sys.stdin is not None and not sys.stdin.isatty():
                payload = json.load(sys.stdin)
                if isinstance(payload, dict):
                    ti = payload.get("tool_input") or {}
                    command_text = (ti.get("command") or payload.get("command") or "") \
                        if isinstance(ti, dict) else payload.get("command") or ""
                    worktree = payload.get("cwd") or worktree
        except Exception:
            pass  # fail-open
    risk = risk or os.environ.get("ZCODE_TICKET_RISK", LOW)

    decision, detail = decide(command_text, risk, worktree)
    line = "BASH_PREFLIGHT_DECISION=%s %s" % (decision, detail)
    sys.stdout.write(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "additionalContext": line,
    }, "decision_line": line}) + "\n")
    return 2 if decision == "BLOCK" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # fail-open, always — same contract as grounding_guard.py
        sys.exit(0)
