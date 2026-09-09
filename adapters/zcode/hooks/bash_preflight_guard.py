#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse hook — SHELL PRE-GROUNDING ALLOWLIST (review R6-F3; receipts R6.1-1).

Problem the guard closes: the structured Edit/Write grounding guard is
insufficient because the worker also has Bash. A HIGH/MEDIUM production edit
performed through Bash must not bypass grounding, and must not smuggle
mutations/redirection/chaining through a supposedly read-only pre-grounding
command.

Semantics (fail closed before grounding, normal afterwards):

- STRUCTURALLY VALID + FRESH grounding receipt present → exit 0 (normal
  authorized Bash returns). Review R6.1-1: the receipt is validated with the
  SAME semantics as grounding_guard — `{"BASE_SHA": ...}` alone is NOT
  sufficient; all §7 fields must exist (values may be NONE/UNKNOWN) and the
  BASE_SHA must still be in HEAD's ancestry (else GROUNDING_RECEIPT_STALE).
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

Receipt-bootstrap deadlock break (review R6.1-1): grounding itself is the
all-readonly discovery phase, but RECORDING the produced receipt needs one
write (set-grounding) — which python is otherwise banned from. Before
grounding, therefore, EXACTLY ONE canonical mechanical command shape is
narrowly allowed:

    python <hookdir>/codegraph_state.py set-grounding --ticket T --risk R
           --base-sha SHA --mode graph|manual [--field K=V ...] | --clear

Exact/trusted constraints: token[0] is the python running this guard (or
"python"/"python3"), token[1] is codegraph_state.py under THIS guard's own
directory (realpath-compared, no PATH lookup), token[2] is exactly
`set-grounding`, and the remaining tokens are set-grounding flags only —
chaining, redirection, quoting tricks and any other script stay BLOCKED.

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
try:  # reuse the SAME receipt-validity semantics as the Edit/Write guard
    import grounding_guard as gg
except Exception:  # pragma: no cover - defensive
    gg = None

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


# --- receipt validity: SAME semantics as grounding_guard (review R6.1-1) ------

def receipt_is_valid(receipt, worktree):
    """(decision, detail) for the recorded grounding receipt.

    review R6.1-1: `{"BASE_SHA": ...}` alone is NOT a sufficient grounding
    receipt. The Bash preflight reuses grounding_guard's exact semantics:
      - structural completeness: every §7 field EXISTS (values may be
        empty/NONE/UNKNOWN — an honest gap — but a missing field is a
        fabricated/partial receipt → BLOCK)
      - freshness: BASE_SHA must still be in HEAD's ancestry (worker's own
        commits do not stale it; a rebase/base-rewrite does → STALE → BLOCK)
    Returns (True, "receipt reason") when normal Bash may unlock, else
    (False, BLOCK-detail)."""
    if not isinstance(receipt, dict):
        return False, "GROUNDING_RECEIPT_INVALID — no receipt object"
    if gg is not None and hasattr(gg, "REQUIRED_RECEIPT_KEYS"):
        missing = [k for k in gg.REQUIRED_RECEIPT_KEYS if k not in receipt]
        if missing:
            return False, ("GROUNDING_RECEIPT_INVALID — receipt missing required field(s): %s; "
                           "a partial receipt (e.g. bare {BASE_SHA: ...}) never unlocks Bash "
                           "(review R6.1-1: same validity semantics as grounding_guard)"
                           % ",".join(missing))
        base = str(receipt.get("BASE_SHA") or "")
        if not base:
            return False, "GROUNDING_RECEIPT_INVALID — BASE_SHA empty"
        head = gg.git_head(worktree)
        fresh, _decided = gg.base_is_fresh(base, head, worktree)
        if not fresh:
            return False, ("GROUNDING_RECEIPT_STALE BASE_SHA=%s HEAD=%s — the formerly-valid "
                           "receipt left HEAD's ancestry; re-ground before normal Bash"
                           % (base[:12], head[:12]))
        mode = str(receipt.get("GRAPH_MODE", "graph"))
        return True, ("%s_GROUNDING_RECEIPT present TICKET=%s — normal Bash"
                      % ("MANUAL" if mode == "manual" else "STRUCTURAL",
                         receipt.get("TICKET", "")))
    # grounding_guard unavailable → structural check degenerates: fail CLOSED
    # on anything less than a full §7-shaped dict is impossible without the
    # field list, so the honest fallback is "no unlock at all".
    return False, ("GROUNDING_RECEIPT_INVALID — grounding_guard module unavailable; the Bash "
                   "preflight cannot prove receipt validity (fail closed, review R6.1-1)")


# --- the ONE trusted bootstrap command (review R6.1-1) -------------------------

def _is_trusted_set_grounding(tokens):
    """True for EXACTLY the canonical internal receipt-recording command:

        python <this hooks dir>/codegraph_state.py set-grounding --ticket T ...

    Trusted by construction:
      - argv[0] must be a python whose sys.executable this process IS (or the
        bare "python"/"python3" family)
      - argv[1] must be codegraph_state.py inside THIS guard's own directory
        (realpath comparison — no PATH resolution, no ../ traversal games)
      - argv[2] must be exactly `set-grounding`
      - all remaining tokens must be set-grounding flags / values
    Any chaining / redirection is already rejected by the caller's chain scan,
    so this list is never reached through a pipeline."""
    if len(tokens) < 3:
        return False
    exe, script, sub = tokens[0], tokens[1], tokens[2]
    exe_name = os.path.basename(exe).lower()
    if exe_name not in ("python", "python3"):
        # allow the interpreter actually running this guard (sys.executable)
        try:
            if os.path.realpath(exe) != os.path.realpath(sys.executable):
                return False
        except Exception:
            return False
    elif os.path.isabs(exe):
        try:
            if os.path.realpath(exe) != os.path.realpath(sys.executable):
                return False
        except Exception:
            return False
    script_real = os.path.realpath(script)
    hooks_dir = os.path.realpath(os.path.dirname(os.path.abspath(__file__)))
    if os.path.basename(script_real) != "codegraph_state.py":
        return False
    if os.path.dirname(script_real) != hooks_dir:
        return False  # any other codegraph_state.py copy is NOT trusted
    if sub != "set-grounding":
        return False
    # the rest must be set-grounding CLI surface only (no positional payload)
    allowed_flags = {
        "--ticket", "--risk", "--base-sha", "--mode", "--graph-base-sha",
        "--seam", "--direct-targets", "--upstream", "--callers", "--callees",
        "--downstream", "--impact", "--affected", "--state-owner",
        "--identity-owner", "--validation-owner", "--surface",
        "--out-of-scope", "--field", "--clear",
    }
    i = 3
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("-"):
            if tok not in allowed_flags:
                return False
            i += 1
            continue
        # bare word: only legal as the VALUE of the previous flag
        if i == 3 or not tokens[i - 1].startswith("-"):
            return False
        i += 1
    return True


def decide(command_text, risk, worktree):
    """Returns (decision, detail). decision ∈ ALLOW / BLOCK."""
    risk = str(risk or LOW).upper()
    if RISK_ORDER.get(risk, 0) < RISK_ORDER["MEDIUM"]:
        return "ALLOW", "risk=%s below grounding threshold" % risk

    state = cs.load(worktree)
    receipt = state.get("grounding_receipt")
    ok, rdetail = receipt_is_valid(receipt, worktree)
    if ok:
        # a valid grounding receipt exists → normal authorized Bash returns
        return "ALLOW", rdetail
    # review R6.1-1: when a receipt EXISTS but is invalid (partial / stale),
    # that fact is the reason normal Bash did not unlock — surface it as the
    # BLOCK detail instead of the generic allowlist rejection (the decision is
    # identical: BLOCK; the evidence names the receipt defect).
    receipt_problem = rdetail if isinstance(receipt, dict) else ""

    text = command_text or ""
    try:
        tokens = shlex.split(text, posix=True)
    except ValueError:
        return "BLOCK", ("UNKNOWN_BASH_MUTABILITY — unparseable shell syntax cannot be proven "
                         "read-only pre-grounding (review R6-F3)")
    if contains_chain(text):
        return "BLOCK", ("UNKNOWN_BASH_MUTABILITY — redirection/chaining/substitution is never "
                         "pre-grounding (review R6-F3: strict read-only allowlist; the trusted "
                         "set-grounding bootstrap is a single bare command, review R6.1-1)")
    if not tokens:
        return "ALLOW", "empty command"
    # review R6.1-1: the narrowly-trusted receipt bootstrap — recording an
    # ALREADY-PRODUCED grounding receipt must not deadlock behind the receipt
    # itself. Exact-shape only; anything else python-shaped stays BLOCKED.
    if _is_trusted_set_grounding(tokens):
        return "ALLOW", ("TRUSTED_RECEIPT_BOOTSTRAP — canonical codegraph_state.py "
                         "set-grounding allowed to record the produced receipt (review R6.1-1)")
    if not is_readonly_command(tokens):
        if receipt_problem:
            return "BLOCK", ("%s — %r is also not on the strict pre-grounding read-only "
                             "allowlist (review R6.1-1)"
                             % (receipt_problem, " ".join(tokens[:3])))
        return "BLOCK", ("UNKNOWN_BASH_MUTABILITY — %r is not on the strict pre-grounding "
                         "read-only allowlist (allowed: git status/diff/log/show/rev-parse/"
                         "merge-base/ls-files/branch --show-current, rg/grep/find/ls/dir/cat/"
                         "Get-Content, and exactly `python <hooks>/codegraph_state.py "
                         "set-grounding ...`); ground first, then run normal Bash "
                         "(review R6-F3)" % " ".join(tokens[:3]))
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
