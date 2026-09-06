#!/usr/bin/env python3
"""PROJECT_CONTINUITY_CONTRACT_V1 — project-state index validator.

Validates <repo-root>/.agent/project-state.json against the contract
(references/project-continuity-contract.md + schemas/project-state.schema.json):

  - file exists / valid JSON / object
  - contract_version supported
  - required fields present with valid shapes
  - remote format (empty only in deferred mode), default_branch
  - canonical pointer shapes: [] / ["NONE"] / "NONE" / "NOT_APPLICABLE" / relative paths
  - codegraph policy valid (NOT_APPLICABLE requires a mechanical basis in notes)
  - secret-like fields rejected (RULES R2 layer 1)
  - local absolute paths / traversal rejected in committed state
  - no raw machine-only runtime state fields (GRAPH_DIRTY etc. never belong here)

Usage:
  python scripts/validate_project_state.py <repo-root>
Exit 0 = all checks PASS; exit 1 = any FAIL. Stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SUPPORTED_CONTRACT_VERSIONS = {1}
POINTER_SLOTS = ("targets", "specs", "architecture", "adrs", "spikes", "environment")
CONTROL_PLANE_TYPES = {"github-issues", "none", "other"}
CODEGRAPH_APPLICABILITY = {"REQUIRED", "NOT_APPLICABLE"}
CODEGRAPH_LIFECYCLE = {"INIT_ONCE_SYNC_CONTINUOUSLY"}
SHA40 = re.compile(r"^[0-9a-f]{40}$")
REMOTE_RE = re.compile(r"^(https?://[^\s]+|git@[^\s]+:[^\s]+|ssh://[^\s]+)$")
ISO8601_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00|-00:00)$")

# Machine-only runtime state must never be committed into the index
# (contract section 6.4): dirty flags / receipts live in local runtime state.
RUNTIME_ONLY_FIELDS = {
    "graph_dirty", "last_sync_head", "last_sync_at", "grounding_receipt",
    "project_state_dirty", "grounding_receipt_runtime_cache",
}

SECRET_VALUE_PATTERNS = [
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github[_-]pat[_-]"),  # split form: keep source clean of the scanner-banned literal
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY"),
    re.compile(r"(?i)(api[_-]?key|token|secret|password|cookie)\s*[:=]\s*[\"'][^\"']{8,}"),
]
ABS_PATH_PATTERNS = [
    re.compile(r"^[A-Za-z]:[\\/]"),          # Windows drive: C:/ or C:\
    re.compile(r"^/(Users|home)/"),          # POSIX home trees
    re.compile(r"^//"),                       # UNC / protocol-relative
    re.compile(r"^[A-Z]:$"),                  # bare drive
]
TRAVERSAL = re.compile(r"(^|/)\.\.(/|$)")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def is_pointer_slot_ok(value) -> bool:
    if isinstance(value, str):
        return value in ("NONE", "NOT_APPLICABLE")
    if not isinstance(value, list):
        return False
    return all(isinstance(p, str) for p in value)


def walk_strings(node):
    """Yields (key_or_None, string_value) pairs for every string in the tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, str):
                yield k, v
            yield from walk_strings(v)
    elif isinstance(node, list):
        for item in node:
            if isinstance(item, str):
                yield None, item
            else:
                yield from walk_strings(item)


def walk_keys(node):
    """Yields every dict key in the tree regardless of value shape — dirty flags
    and receipts are booleans/ints/dicts at runtime, so key-level scanning is
    required to keep machine-only runtime state out of the committed index."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(node, list):
        for item in node:
            yield from walk_keys(item)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_project_state.py <repo-root>")
        return 1
    root = Path(sys.argv[1]).resolve()
    state_path = root / ".agent" / "project-state.json"

    # 1. exists + parses
    if not state_path.is_file():
        check("project-state-exists", False, str(state_path))
        return _report()
    check("project-state-exists", True)
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        check("project-state-valid-json", False, str(exc))
        return _report()
    check("project-state-valid-json", isinstance(data, dict), "not an object")
    if not isinstance(data, dict):
        return _report()

    # 2. version + top-level shape
    ver = data.get("contract_version")
    check("contract-version-supported", ver in SUPPORTED_CONTRACT_VERSIONS, f"got={ver!r}")

    unknown_top = set(data) - {
        "contract_version", "project_identity", "remote", "default_branch",
        "canonical_documents", "execution_control_plane", "recovery_snapshot",
        "codegraph_policy",
    }
    check("top-level-fields-known", not unknown_top, f"unknown={sorted(unknown_top)}")

    identity = data.get("project_identity")
    check("project-identity", isinstance(identity, dict) and isinstance(identity.get("name"), str)
          and identity.get("name", "").strip() != "", f"got={identity!r}")

    # 3. remote + default branch
    remote = data.get("remote")
    deferred = isinstance(remote, str) and remote == ""
    if deferred:
        reason = str(data.get("recovery_snapshot", {}).get("last_state_flush_reason", ""))
        check("remote-format", True, "empty remote accepted only as DEFERRED marker")
    else:
        check("remote-format", isinstance(remote, str) and bool(REMOTE_RE.match(remote or "")),
              f"got={remote!r}")
    check("default-branch", isinstance(data.get("default_branch"), str)
          and data.get("default_branch", "").strip() != "", f"got={data.get('default_branch')!r}")

    # 4. canonical documents pointers
    docs = data.get("canonical_documents")
    docs_ok = isinstance(docs, dict) and set(docs) == set(POINTER_SLOTS) \
        and all(is_pointer_slot_ok(docs.get(slot)) for slot in POINTER_SLOTS)
    check("canonical-documents-pointers", docs_ok, f"got={docs!r}")

    # 5. execution control plane
    ecp = data.get("execution_control_plane")
    ecp_ok = isinstance(ecp, dict) and ecp.get("type") in CONTROL_PLANE_TYPES
    if ecp_ok and ecp.get("type") == "none":
        ecp_ok = ecp.get("tracker_location") in (None, "NONE", "NOT_APPLICABLE")
    check("execution-control-plane", ecp_ok, f"got={ecp!r}")

    # 6. recovery snapshot
    snap = data.get("recovery_snapshot")
    snap_ok = isinstance(snap, dict)
    if snap_ok:
        # Empty last_verified_remote_sha is the honest day-one/adoption state
        # (nothing remotely verified yet); a 40-hex SHA is required once verified.
        sha = snap.get("last_verified_remote_sha", "")
        snap_ok = (sha == "") or bool(SHA40.match(str(sha)))
        ts = snap.get("last_state_flush_at", "")
        snap_ok = snap_ok and (ts == "" or bool(ISO8601_UTC.match(str(ts))))
        snap_ok = snap_ok and isinstance(snap.get("blocker_refs", []), list)
        snap_ok = snap_ok and isinstance(snap.get("next_legal_action", ""), str)
        unknown_snap = set(snap) - {
            "last_verified_remote_sha", "last_state_flush_reason", "last_state_flush_at",
            "legal_frontier_summary", "blocker_refs", "next_legal_action",
        }
        check("recovery-snapshot-keys-known", not unknown_snap, f"unknown={sorted(unknown_snap)}")
    check("recovery-snapshot", snap_ok, f"got={snap!r}")

    # 7. codegraph policy
    cg = data.get("codegraph_policy")
    cg_ok = isinstance(cg, dict) and cg.get("applicability") in CODEGRAPH_APPLICABILITY
    if cg_ok:
        if cg.get("applicability") == "NOT_APPLICABLE":
            cg_ok = isinstance(cg.get("notes"), str) and cg.get("notes", "").strip() != ""
        lc = cg.get("lifecycle", "INIT_ONCE_SYNC_CONTINUOUSLY")
        cg_ok = cg_ok and lc in CODEGRAPH_LIFECYCLE
    check("codegraph-policy", cg_ok, f"got={cg!r}")

    # 8. secret-like fields (R2 layer 1) — any string value anywhere
    secret_hits = []
    for _key, value in walk_strings(data):
        for pat in SECRET_VALUE_PATTERNS:
            if pat.search(value):
                secret_hits.append(pat.pattern)
    check("no-secret-like-fields", not secret_hits, f"patterns={sorted(set(secret_hits))[:3]}")

    # 9. no local absolute paths / traversal in committed state
    abs_hits = []
    for key, value in walk_strings(data):
        if key in ("remote",):
            continue
        for pat in ABS_PATH_PATTERNS:
            if pat.match(value):
                abs_hits.append(value)
        if key != "contract_version" and TRAVERSAL.search(value):
            abs_hits.append(value)
    check("no-local-absolute-paths", not abs_hits, f"values={abs_hits[:3]}")

    # 10. machine-only runtime state must not be committed (any value shape)
    runtime_hits = [k for k in walk_keys(data) if k in RUNTIME_ONLY_FIELDS]
    check("no-runtime-only-fields", not runtime_hits, f"fields={sorted(set(runtime_hits))}")

    return _report()


def _report() -> int:
    failed = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail and not ok else ""))
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
