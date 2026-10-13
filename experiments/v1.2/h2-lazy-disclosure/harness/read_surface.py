#!/usr/bin/env python3
"""H2 harness — read-surface classification for telemetry READ events (single source of truth).

Extracted from collect_run.sh's inline TELEMETRY_TARGETS predicate. Introduced by the Round-1
repair: the old predicate accepted only worktree-relative targets, so a contract-compliant
worker that read the report template was rejected by its own harness.

CANONICAL PATH SPELLINGS (deterministic by construction, and free of host layout)
-------------------------------------------------------------------------------------
1. A file in the task worktree is recorded REPO-RELATIVE:            `CODEBUDDY.md`
2. A file in this run's evidence directory is recorded through a    `RUN_EVIDENCE/contract.md`
   STABLE NAMESPACE (never a host path).
Absolute paths are REFUSED. A telemetry log is collected into the run record and published, so
an absolute path would write a real host path into a committed artifact — which the repository's
public-data policy forbids. It would also silently defeat the old predicate's join() behaviour:
`os.path.join(worktree, "/abs/path")` discards the worktree prefix, so any existing absolute
path used to pass. Refusing the form outright removes that whole class.

MINIMUM NECESSARY READ SURFACE (PART 7)
---------------------------------------
Allowed: the task worktree, plus this run's evidence directory — and within the latter only the
specific files the contract designates. The materials tree root is NOT readable: it also holds
the protocol, the task registry (which carries the oracle), the scoring rubric and BOTH arm
carriers, so an open materials root would permit cross-arm contamination and void the H2
independent variable.

Verdicts are (verdict, reason) pairs; the reason tokens are stable machine strings so tests and
the precondition evidence can assert on them.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

ALLOWED = "ALLOWED"

# Stable namespace prefix for evidence-directory files. Deliberately not a path: it carries no
# host layout and is resolved against THIS run's evidence dir by the collector.
EVIDENCE_NS = "RUN_EVIDENCE/"

# The only evidence-directory files a worker may legitimately read. The contract designates its
# own contract and its report-template copy; its own report is readable for self-consistency.
# `receipt.json`, `task.txt` and collector outputs are deliberately absent: allowing the whole
# directory would make the enforced surface broader than the declared minimum.
EVIDENCE_ALLOWLIST = ("contract.md", "worker-report-template.md", "report.md")

REJECT_REASONS = (
    "NON_CANONICAL_PATH",           # ellipsis / whitespace padding / empty
    "HOST_PATH_NOT_ALLOWED",        # absolute path: leaks host layout into a published artifact
    "UNKNOWN_EVIDENCE_NAMESPACE",   # RUN_EVIDENCE/... naming a file that is not on the allowlist
    "MATERIALS_ROOT_READ",          # inside the frozen materials tree (protocol/carriers/registry)
    "CROSS_ARM_READ",               # the OTHER arm's carrier
    "OTHER_RUN_EVIDENCE_READ",      # a sibling run's evidence directory
    "OUTSIDE_ALLOWED_SURFACE",      # anywhere else, or a path that does not exist
)


def _is_within(path: Path, root: Path) -> bool:
    """Component-wise containment. A string-prefix test would let a sibling directory whose
    name merely starts with the root's name pass; that mutation is pinned by a test."""
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _boundary_reason(resolved: Path, wt: Path, ev: Path, mat: Path) -> str | None:
    """Classify an ALREADY-RESOLVED path against the boundary roots.

    Resolution happens first so that a symlink cannot launder a forbidden destination: the
    verdict always describes where the bytes actually live, never where the name pointed.
    Shared by both accepted spellings so the two cannot drift.

    ORDER MATTERS. The explicitly ALLOWED roots are tested before the forbidden materials root.
    A runs root may legitimately live inside the materials checkout (e.g. the already-ignored
    `.workbuddy/h2-runs`), which makes the task worktree and the evidence dir DESCENDANTS of
    `mat`; testing `mat` first would classify compliant reads such as `CODEBUDDY.md` as
    MATERIALS_ROOT_READ — preparation would succeed and collection would then reject the run
    after the worker episode had already been spent. Testing `mat` after `ev`/`wt` keeps the
    verdict correct in both layouts, because the resolved path of a worktree symlink pointing
    INTO the materials tree still fails both allowed-root tests and lands on the materials
    branch.
    """
    if _is_within(resolved, ev):
        return None
    if _is_within(resolved, wt):
        return None if resolved.is_file() else "OUTSIDE_ALLOWED_SURFACE"
    if _is_within(resolved, mat):
        rel = resolved.relative_to(mat).parts
        return "CROSS_ARM_READ" if "carriers" in rel else "MATERIALS_ROOT_READ"
    # a sibling run's evidence directory is recognised by path shape: it is outside the
    # allowlist, and naming the reason keeps the evidence readable without leaking paths.
    parts = resolved.parts
    if "evidence" in parts:
        idx = parts.index("evidence")
        if idx + 1 < len(parts) and parts[idx + 1] != ev.name:
            return "OTHER_RUN_EVIDENCE_READ"
    return "OUTSIDE_ALLOWED_SURFACE"


def classify_read_target(
    target: str,
    worktree: str | os.PathLike,
    evidence_dir: str | os.PathLike,
    materials_root: str | os.PathLike,
    telemetry_name: str = ".h2-telemetry.log",
) -> tuple[str, str]:
    """Classify one READ target. Returns (ALLOWED, "OK") or ("REJECTED", <stable reason>)."""
    wt = Path(worktree).resolve()
    ev = Path(evidence_dir).resolve()
    mat = Path(materials_root).resolve()

    if target == telemetry_name:
        return (ALLOWED, "OK")

    if not target.strip() or target.strip() != target or "..." in target:
        return ("REJECTED", "NON_CANONICAL_PATH")

    p = Path(target)
    if p.is_absolute():
        return ("REJECTED", "HOST_PATH_NOT_ALLOWED")

    # ---- evidence namespace (host-free, allowlisted by file name) ----
    if target.startswith(EVIDENCE_NS):
        name = target[len(EVIDENCE_NS):]
        if name not in EVIDENCE_ALLOWLIST or "/" in name:
            return ("REJECTED", "UNKNOWN_EVIDENCE_NAMESPACE")
        resolved = (ev / name).resolve()
        reason = _boundary_reason(resolved, wt, ev, mat)
        if reason is not None:
            # an ALLOWLISTED name that is a symlink into the materials tree lands here, and is
            # reported with the real boundary reason rather than a generic miss
            return ("REJECTED", reason)
        return (ALLOWED, "OK") if resolved.is_file() else ("REJECTED", "OUTSIDE_ALLOWED_SURFACE")

    # ---- repo-relative inside the task worktree ----
    resolved = (wt / p).resolve()
    reason = _boundary_reason(resolved, wt, ev, mat)
    if reason is not None:
        return ("REJECTED", reason)
    if _is_within(resolved, ev):
        # reached the evidence dir by traversal instead of the stable namespace
        return ("REJECTED", "UNKNOWN_EVIDENCE_NAMESPACE")
    return (ALLOWED, "OK") if resolved.is_file() else ("REJECTED", "OUTSIDE_ALLOWED_SURFACE")


_READ_RE = re.compile(r"^READ\s+(FULL|PARTIAL|GREP)\s+(\S+)$")


def classify_telemetry(
    lines: list[str],
    worktree: str | os.PathLike,
    evidence_dir: str | os.PathLike,
    materials_root: str | os.PathLike,
) -> list[str]:
    """Return one problem string per disallowed READ target in the log."""
    problems: list[str] = []
    for raw in lines:
        m = _READ_RE.match(raw.strip())
        if not m:
            continue
        target = m.group(2)
        verdict, reason = classify_read_target(target, worktree, evidence_dir, materials_root)
        if verdict != ALLOWED:
            problems.append(f"READ target rejected ({reason}): {target}")
    return problems
