#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PreToolUse hook — GROUNDING GUARD (contract §7; best-effort mechanical tripwire).

Rule: RISK >= MEDIUM + production-source write + GROUNDING_RECEIPT missing
      → block with CODEGRAPH_GROUNDING_REQUIRED. The orchestrator then runs
      fresh graph → grounding → receipt → continue, without asking the user.
Receipt validity (review F4): ALL contract §7 fields must EXIST (values may be
      empty / NONE / UNKNOWN); a truncated or hand-made partial receipt is
      INVALID → GROUNDING_RECEIPT_INVALID (fail closed).
Manual fallback: CodeGraph unavailable → MANUAL_GROUNDING_RECEIPT (mode=manual)
      → allowed (MODE C semantics, codegraph-grounding.md §4).

Exit-code / deny-mapping contract (REQ-W4-03, S1 core — stated as a CONTRACT,
mechanically checked by tests/test_p1_t15_guard_deny_mapping.py, not prose):
- exit 0 = ALLOW; exit 2 = REQUEST_BLOCK. REQUEST_BLOCK alone is NOT proof of
  enforcement: a script printing BLOCK is never evidence that an action was
  actually denied.
- ENFORCED vs ADVISORY: the adapter's runtime status is ENFORCED only when a
  VERIFIABLE deny-mapping registry exists — a machine-readable record that the
  runtime maps exit 2 to an actual host deny (location: env
  ZCODE_DENY_MAPPING_REGISTRY pointing at a JSON file, see load_deny_mapping).
  Without a verifiable mapping the status is ADVISORY — the guard degrades to
  advisory context, the AUTHORITATIVE gate remains the orchestrator discipline
  (contract §7), and this hook only makes forgetting it mechanically visible.
  An adapter with no mapping that declares ADVISORY honestly is legal.
- fail-closed on false enforcement claims: an ENFORCED claim without a
  verifiable mapping is a contract violation (check_adapter_claim rejects it);
  a malformed / missing / non-matching registry can NEVER yield ENFORCED.
- NOT_RUN: the live host deny verification (real tool event → block → host
  deny → target unchanged) is REQ-W4-03-D / W5 / DEPLOYMENT_ONLY. It is
  reported NOT_RUN here and NOT_RUN is never PASS (live_verification_status).
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
# Contract §7 receipt fields. A receipt is only mechanically VALID when every
# field EXISTS; values may be empty / "NONE" / "UNKNOWN" (an honest gap), but a
# missing field means structural grounding never happened and the receipt is
# treated as fabricated (review F4: presence is the bar, not prose).
RECEIPT_STRUCTURAL_FIELDS = (
    "GRAPH_BASE_SHA", "TARGET_SEAM", "DIRECT_TARGETS", "UPSTREAM_PRODUCERS",
    "CALLERS", "CALLEES", "DOWNSTREAM_CONSUMERS", "IMPACT", "AFFECTED",
    "STATE_OWNER", "IDENTITY_OWNER", "VALIDATION_OWNER",
    "EXPECTED_EDIT_SURFACE", "OUT_OF_SCOPE",
)
REQUIRED_RECEIPT_KEYS = ("TICKET", "RISK", "BASE_SHA", "GRAPH_MODE") + RECEIPT_STRUCTURAL_FIELDS
# values that mean "honestly unknown" — accepted wherever a field exists
UNKNOWN_VALUES = {"", "NONE", "UNKNOWN", "N/A"}

# --- exit-code / deny-mapping contract (REQ-W4-03, S1 core; AC-18) -----------
# The hook's own exit codes. exit 2 is a REQUEST, not a proof of enforcement:
# ENFORCED exists only where a verifiable deny mapping is recorded (below).
ALLOW_EXIT_CODE = 0
REQUEST_BLOCK_EXIT_CODE = 2
RUNTIME_STATUS_ENFORCED = "ENFORCED"
RUNTIME_STATUS_ADVISORY = "ADVISORY"
RUNTIME_LIVE_STATUS_NOT_RUN = "NOT_RUN"
# Machine-readable registry location: a deployment that wires exit 2 to a real
# host deny records a JSON file and points this env var at it. Unset -> no
# mapping -> ADVISORY (the honest degraded state).
DENY_MAPPING_REGISTRY_ENV = "ZCODE_DENY_MAPPING_REGISTRY"
DENY_MAPPING_VERSION = 1
DENY_MAPPING_REQUIRED_FIELDS = (
    "deny_mapping_version", "adapter", "hook",
    "allow_exit_code", "request_block_exit_code",
    "host_decision_on_request_block", "recorded_at", "recorded_by",
)


def load_deny_mapping(env=None) -> tuple[dict | None, str]:
    """(mapping, reason). mapping is non-None ONLY when a structurally
    verifiable deny-mapping registry exists. Fail-closed: unset / unreadable /
    malformed / missing-field / wrong-exit-code / non-DENY registries all
    return (None, reason) — they can never yield ENFORCED."""
    env = os.environ if env is None else env
    path = str(env.get(DENY_MAPPING_REGISTRY_ENV) or "").strip()
    if not path:
        return None, ("no deny-mapping registry recorded (%s unset)"
                      % DENY_MAPPING_REGISTRY_ENV)
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except Exception as exc:
        return None, "deny-mapping registry unreadable or malformed: %s" % exc
    if not isinstance(raw, dict):
        return None, "deny-mapping registry is not a JSON object"
    missing = [k for k in DENY_MAPPING_REQUIRED_FIELDS if k not in raw]
    if missing:
        return None, "deny-mapping registry missing fields: %s" % "/".join(missing)
    ver = raw["deny_mapping_version"]
    if isinstance(ver, bool) or not isinstance(ver, int) or ver != DENY_MAPPING_VERSION:
        return None, "unsupported deny_mapping_version: %r" % (ver,)
    if raw["adapter"] != "zcode" or raw["hook"] != "grounding_guard.py":
        return None, "registry does not bind this adapter/hook"
    allow_rc, block_rc = raw["allow_exit_code"], raw["request_block_exit_code"]
    if isinstance(allow_rc, bool) or not isinstance(allow_rc, int) or allow_rc != ALLOW_EXIT_CODE \
            or isinstance(block_rc, bool) or not isinstance(block_rc, int) \
            or block_rc != REQUEST_BLOCK_EXIT_CODE:
        return None, ("registry exit codes do not match this hook's contract "
                      "(exit 0 = ALLOW, exit 2 = REQUEST_BLOCK)")
    if str(raw["host_decision_on_request_block"]).upper() != "DENY":
        return None, ("registry does not record a host DENY for the block "
                      "request — REQUEST_BLOCK alone is not enforcement")
    for key in ("recorded_at", "recorded_by"):
        if not str(raw[key]).strip():
            return None, "registry field %s is empty" % key
    return raw, "verifiable deny mapping present"


def check_adapter_claim(claim: dict, env=None) -> tuple[bool, str]:
    """Contract check for an adapter status claim (CE-20 core / CE-27).
    Fail-closed: ENFORCED is accepted ONLY with a verifiable deny mapping; an
    unknown or missing claim status is rejected."""
    claim = claim if isinstance(claim, dict) else {}
    status = str(claim.get("status", "")).strip().upper()
    if status == RUNTIME_STATUS_ENFORCED:
        mapping, reason = load_deny_mapping(env)
        if mapping is None:
            return False, ("ENFORCED_CLAIM_WITHOUT_VERIFIABLE_DENY_MAPPING: %s" % reason)
        return True, reason
    if status == RUNTIME_STATUS_ADVISORY:
        return True, "ADVISORY claim without a mapping is the honest degraded state"
    return False, "UNKNOWN_OR_MISSING_CLAIM_STATUS: %r" % (claim.get("status"),)


def live_verification_status(_mapping=None) -> str:
    """Live host deny verification status (REQ-W4-03-D / AC-18-D, W5).
    S1 core NEVER performs it: this always returns NOT_RUN, and NOT_RUN is
    never PASS. No S1 input (including self-claimed registry fields) can flip
    it — W5 owns the only upgrade path, via real host evidence."""
    return RUNTIME_LIVE_STATUS_NOT_RUN


def runtime_status(env=None) -> dict:
    """Derive the adapter runtime status from the deny-mapping registry.
    Returns {"status": ENFORCED|ADVISORY, "mapping": dict|None, "reason": str,
    "live_verification": NOT_RUN}. Fail-closed: any unverifiable mapping
    degrades to ADVISORY, never ENFORCED; the live dimension is NOT_RUN."""
    mapping, reason = load_deny_mapping(env)
    if mapping is None:
        return {"status": RUNTIME_STATUS_ADVISORY, "mapping": None,
                "reason": reason, "live_verification": live_verification_status()}
    return {"status": RUNTIME_STATUS_ENFORCED, "mapping": mapping,
            "reason": reason, "live_verification": live_verification_status(mapping)}


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
    return REQUEST_BLOCK_EXIT_CODE if decision == "BLOCK" else ALLOW_EXIT_CODE


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # fail-open, always
        sys.exit(0)
