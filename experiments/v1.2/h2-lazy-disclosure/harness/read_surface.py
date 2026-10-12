#!/usr/bin/env python3
"""H2 harness — read-surface classification for telemetry READ events (single source of truth).

Extracted from collect_run.sh's inline TELEMETRY_TARGETS predicate. Initially a
BEHAVIOUR-PRESERVING extraction (worktree-only), which is what reproduces the Round-1
defect: a contract-compliant worker that reads the report template placed in the run's own
evidence dir is rejected, because the template used to live in the materials tree.

MINIMUM NECESSARY READ SURFACE (PART 7): a worker may read
  * inside its own task worktree, and
  * the current run's own evidence directory (its contract, its report template copy).
Nothing else. In particular the materials tree root is NOT readable: it also holds the
protocol, the task registry, the scoring rubric and BOTH arm carriers, so an open
materials root would allow cross-arm contamination and destroy the H2 independent variable.

Verdicts are (verdict, reason) pairs; reasons are stable machine tokens so tests and the
precondition evidence can assert on them.
"""
from __future__ import annotations

import os
from pathlib import Path

ALLOWED = "ALLOWED"

REJECT_REASONS = (
    "NON_CANONICAL_PATH",       # contains an ellipsis / cannot be resolved to a real file
    "MATERIALS_ROOT_READ",      # inside the frozen materials tree (protocol/carriers/registry)
    "CROSS_ARM_READ",           # the OTHER arm's carrier
    "OTHER_RUN_EVIDENCE_READ",  # a sibling run's evidence directory
    "OUTSIDE_ALLOWED_SURFACE",  # anywhere else
)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def classify_read_target(
    target: str,
    worktree: str | os.PathLike,
    evidence_dir: str | os.PathLike,
    materials_root: str | os.PathLike,
    telemetry_name: str = ".h2-telemetry.log",
) -> tuple[str, str]:
    """Classify one READ target. Returns (ALLOWED, "OK") or ("REJECTED", <stable reason>).

    The allowed surface is deliberately the MINIMUM NECESSARY one (PART 7): the task
    worktree plus this run's own evidence directory. The materials tree root is never
    readable — it also holds the protocol, the task registry, the scoring rubric and BOTH
    arm carriers, so opening it would allow cross-arm contamination and void the H2
    independent variable.
    """
    wt = Path(worktree).resolve()
    ev = Path(evidence_dir).resolve()
    mat = Path(materials_root).resolve()

    if target == telemetry_name:
        return (ALLOWED, "OK")

    # PART 8: a machine-readable path must be canonicalizable. An abbreviated path such as
    # "h2-materials/.../worker-report-template.md" cannot be verified against anything, so it
    # is rejected rather than pattern-matched into looking legitimate.
    if "..." in target or target.strip() != target or not target.strip():
        return ("REJECTED", "NON_CANONICAL_PATH")

    p = Path(target)
    # Deterministic base (PART 8): a bare relative path resolves against the TASK WORKTREE
    # only. A file in this run's evidence directory has no worktree-relative spelling, so it
    # must be logged as an absolute path — resolving one bare name against two different
    # roots would make the recorded event ambiguous, and publish_run.sh rewrites the absolute
    # form to a placeholder at publication so no local path leaks either way.
    # resolve() follows symlinks, so a link inside the worktree cannot launder a materials
    # read; existence is checked on the RESOLVED path.
    resolved = p.resolve() if p.is_absolute() else (wt / p).resolve()

    # most specific verdict first, so the recorded reason is diagnostic rather than generic
    if _is_within(resolved, ev):
        return (ALLOWED, "OK") if resolved.is_file() else ("REJECTED", "OUTSIDE_ALLOWED_SURFACE")
    if _is_within(resolved, mat):
        if "carriers" in resolved.relative_to(mat).parts:
            return ("REJECTED", "CROSS_ARM_READ")
        return ("REJECTED", "MATERIALS_ROOT_READ")
    if _is_within(resolved, wt):
        return (ALLOWED, "OK") if resolved.is_file() else ("REJECTED", "OUTSIDE_ALLOWED_SURFACE")

    # a sibling run's evidence directory is recognised by path shape: it is outside the
    # allowlist, and naming the reason keeps the evidence readable without leaking paths.
    parts = resolved.parts
    if "evidence" in parts:
        idx = parts.index("evidence")
        if idx + 1 < len(parts) and parts[idx + 1] != ev.name:
            return ("REJECTED", "OTHER_RUN_EVIDENCE_READ")
    return ("REJECTED", "OUTSIDE_ALLOWED_SURFACE")


def classify_telemetry(
    lines: list[str],
    worktree: str | os.PathLike,
    evidence_dir: str | os.PathLike,
    materials_root: str | os.PathLike,
) -> list[str]:
    """Return a list of problem strings for every disallowed READ target in the log."""
    import re

    problems: list[str] = []
    for raw in lines:
        ln = raw.strip()
        m = re.match(r"^READ\s+(FULL|PARTIAL|GREP)\s+(\S+)$", ln)
        if not m:
            continue
        target = m.group(2)
        verdict, reason = classify_read_target(
            target, worktree, evidence_dir, materials_root
        )
        if verdict != ALLOWED:
            problems.append(f"READ target rejected ({reason}): {target}")
    return problems
