#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Shared runtime-local state for the ZCode continuity adapter hooks.

Layout (contract §6.4 — machine-local, NEVER committed to git):

    <runtime-state-root>/continuity/<sha256(worktree realpath)>/state.json

- runtime-state-root defaults to ~/.zcode/runtime-state and is overridable via
  ZCODE_RUNTIME_STATE_DIR (used by the synthetic test matrix to stay hermetic).
- Keyed by worktree realpath, so repo/worktree pairs are isolated (contract §6.5).
- Content: graph_dirty / project_state_dirty flags, last sync bookkeeping, and
  the runtime-local grounding receipt cache (contract §7). All JSON.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

STATE_VERSION = 1


def runtime_root() -> Path:
    root = os.environ.get("ZCODE_RUNTIME_STATE_DIR")
    if not root:
        root = os.path.expanduser(os.path.join("~", ".zcode", "runtime-state"))
    return Path(root)


def _key(worktree: str) -> str:
    return hashlib.sha256(os.path.realpath(worktree).encode("utf-8", "replace")).hexdigest()


def state_path(worktree: str) -> Path:
    return runtime_root() / "continuity" / _key(worktree) / "state.json"


def load(worktree: str) -> dict:
    path = state_path(worktree)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"state_version": STATE_VERSION}


def save(worktree: str, data: dict) -> None:
    data.setdefault("state_version", STATE_VERSION)
    data["worktree"] = os.path.realpath(worktree)
    path = state_path(worktree)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --- classification -----------------------------------------------------------

GRAPH_EXTS = {
    ".py", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java",
    ".kt", ".rb", ".php", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".scala", ".m", ".sh", ".sql", ".vue", ".svelte",
}
# canonical state docs are markdown under target/spec/adr/spike/architecture
STATE_DOC_MARKERS = ("target", "spec", "adr", "spike", "architecture")


def classify(file_path: str) -> str:
    """graph = production source edit; state = canonical state doc edit; '' = other."""
    p = (file_path or "").replace("\\", "/").lower()
    name = p.rsplit("/", 1)[-1]
    ext = ("." + name.rsplit(".", 1)[-1]) if "." in name else ""
    if ext in GRAPH_EXTS:
        return "graph"
    if p.endswith(".agent/project-state.json"):
        return "state"
    if ext in (".md", ".markdown", ".mdx"):
        for marker in STATE_DOC_MARKERS:
            if ("/" + marker) in ("/" + p) or ("/" + marker + "s/") in ("/" + p):
                return "state"
    return ""


def worktree_from_env_or_cwd() -> str:
    return os.environ.get("ZCODE_PROJECT_DIR") or os.getcwd()
