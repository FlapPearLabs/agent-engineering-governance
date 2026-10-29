#!/usr/bin/env python3
"""Worker scope rules for the wrapper layout (F1 / CODEX_FIXES_1 T10).

`check_scope` is the mechanical scope judgement of one collected base->worker delta. It applies
the frozen per-task boundary (per-file deny list + deny prefixes), refuses any path that leaves
repo/, and refuses the import-shadowing class F1 demonstrated: every path the worker ADDED or
RENAMED anywhere in repo/ is held to the validator's own `shadow_paths` rule (validator 2.8.12,
imported, never copied) plus the interpreter startup hooks (`sitecustomize.py`,
`usercustomize.py`, `*.pth`).

The caller owns collection (freeze-v3/collect_v2.py) and the rest of the acceptance
(freeze-v3/run_acceptance_v2.py). An empty list means the delta is scope-clean.
"""
from __future__ import annotations

import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "harness"))

import check_task_class as ctc  # noqa: E402

# A committed startup hook decides what EVERY acceptance imports, so it is refused wherever the
# worker puts it, not only on an import root.
STARTUP_HOOK_NAMES = frozenset({"sitecustomize.py", "usercustomize.py"})
SHADOW_REASONS = ("BYTECODE", "PACKAGE_IMPORTED_BY_DISCOVERY", "PACKAGE_MARKER", "SHADOWS")


def path_escapes(path: str) -> bool:
    """True when `path` is not a plain repo-relative path (absolute, `..`, empty, backslash)."""
    rel = PurePosixPath(path)
    return rel.is_absolute() or not rel.parts or ".." in rel.parts or "\\" in path


def is_startup_hook(path: str) -> bool:
    return PurePosixPath(path).name in STARTUP_HOOK_NAMES or path.endswith(".pth")


def check_scope(task: dict, changes: list[dict]) -> list[str]:
    """Sorted refusal reasons for a base->worker delta; the reasons are the evidence.

    `changes` entries carry git's status letter in `status`, the destination in `path` and, for a
    rename or copy, the source in `old_path`. Both sides of a rename are judged: a rename OUT of
    the frozen directory and a rename INTO an import root are the same violation from two sides.
    """
    reasons: set[str] = set()
    deny = set(task["scope"]["deny"])
    prefixes = tuple(task["scope"]["deny_prefixes"])
    added: list[str] = []
    for change in changes:
        status = str(change.get("status", ""))
        for path in (change.get("old_path"), change.get("path")):
            if path is None:
                continue
            if path_escapes(path):
                reasons.add(f"WORKER_PATH_ESCAPE:{path}")
            if path in deny or any(path.startswith(prefix) for prefix in prefixes):
                reasons.add(f"WORKER_SCOPE_DENIED:{path}")
        if status[:1] in ("A", "R", "C"):
            path = change.get("path")
            if path is None:
                continue
            added.append(path)
            if is_startup_hook(path):
                reasons.add(f"WORKER_STARTUP_HOOK:{path}")
    for path, kind in ctc.shadow_paths(added).items():
        reasons.add(f"WORKER_SHADOWS_IMPORT:{path}:{kind}")
    return sorted(reasons)
