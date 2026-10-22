#!/usr/bin/env python3
"""Commit-sourced delivery outside the task repository; never executes a worker."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path, PurePosixPath

H2_REL = "experiments/v1.2/h2-lazy-disclosure"
ROOT = Path(__file__).resolve().parents[4]
DELIVERED_NAMES = {"AGENTS.md", "H2_RULES.md", "H2_WARM"}
# F4: opencode discovers guidance by walking UP from the cwd, past a redirected HOME, so a run root
# below any directory that carries one of these re-admits the operator's own skills/plugins/config.
ANCESTOR_MARKERS = (".agents", ".opencode", ".claude", "AGENTS.md", "CLAUDE.md", "opencode.json")
# F8 / T21: `repo/` is a STANDALONE repository whose object store is exactly the task base and its
# tree, so no worker can read the historical fix out of a shared object database. The base objects
# are fetched through one temporary ref in the governance repository, deleted again before the
# worker sees the tree; the ref name is the only trace a crash could leave behind.
HISTORY_REF_ROOT = "refs/h2-delivery"
GIT_METADATA_FILES = ("FETCH_HEAD", "ORIG_HEAD", "COMMIT_EDITMSG", "packed-refs")
GIT_METADATA_DIRS = ("logs", "refs/remotes", "refs/tags", "worktrees")


def operator_home() -> Path:
    return Path.home()


def discoverable_ancestor(run_dir: Path) -> str | None:
    """The first marker on any ancestor of `run_dir` (the run dir's own carrier excepted)."""
    resolved = Path(run_dir).resolve()
    for ancestor in (resolved, *resolved.parents):
        for marker in ANCESTOR_MARKERS:
            if ancestor == resolved and marker == "AGENTS.md":
                continue                      # the arm carrier prepare writes itself
            if (ancestor / marker).exists():
                return marker
    return None


def run_root_reason(run_dir: Path) -> str | None:
    """Why `run_dir` is not an acceptable run root, or None when it is (F4 / CODEX_FIXES_1 T13)."""
    resolved = Path(run_dir).resolve()
    home = operator_home().resolve()
    if resolved == home or home in resolved.parents:
        return "RUN_DIR_UNDER_OPERATOR_HOME"
    marker = discoverable_ancestor(resolved)
    if marker is not None:
        return f"RUN_DIR_UNDER_DISCOVERABLE_ROOT:{marker}"
    return None


def git(root: Path, *args: str, binary: bool = False):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=not binary)
    if result.returncode:
        raise ValueError(f"GIT_FAILED: {' '.join(args[:2])}")
    return result.stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def governance_paths(metadata: Path, root: Path) -> list[str]:
    """Files under `metadata` that carry the governance checkout's own path (T21 postcondition)."""
    metadata = Path(metadata)
    needles = {str(root).encode(), str(Path(root).resolve()).encode()}
    hits = []
    for path in sorted(metadata.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        if any(needle in data for needle in needles):
            hits.append(path.relative_to(metadata.parent).as_posix())
    return hits


def object_names(repo: Path) -> set[str]:
    """Every object in the object store, loose or packed."""
    return set(git(repo, "cat-file", "--batch-all-objects",
                   "--batch-check=%(objectname)").split())


def reachable_objects(repo: Path) -> set[str]:
    """Every object reachable from HEAD and the refs — i.e. the base commit and its tree."""
    lines = git(repo, "rev-list", "--objects", "--all").splitlines()
    return {line.split(" ", 1)[0] for line in lines if line}


def standalone_repository(root: Path, repo: Path, base: str) -> None:
    """Create `repo` as a standalone repository holding exactly `base` and its tree.

    A depth-1 fetch of one commit, then everything that could name the governance repository or
    another commit is removed: remotes, FETCH_HEAD, reflogs, other refs, alternates and any object
    outside the base tree. HEAD stays detached at `base`, so `git rev-parse HEAD` and
    `git status` show a worker exactly what the previous worktree showed.
    """
    root, repo = Path(root), Path(repo)
    ref = f"{HISTORY_REF_ROOT}/{base[:12]}-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    git(root, "update-ref", ref, base)
    try:
        repo.mkdir(parents=True)
        git(repo, "init", "-q")
        git(repo, "fetch", "-q", "--no-tags", "--depth", "1", str(root), ref)
        git(repo, "checkout", "-q", "--detach", base)
    finally:
        git(root, "update-ref", "-d", ref)
    metadata = repo / ".git"
    for name in GIT_METADATA_FILES:
        (metadata / name).unlink(missing_ok=True)
    for name in GIT_METADATA_DIRS:
        shutil.rmtree(metadata / name, ignore_errors=True)
    (metadata / "objects/info/alternates").unlink(missing_ok=True)
    git(repo, "reflog", "expire", "--expire=now", "--all")
    shutil.rmtree(metadata / "logs", ignore_errors=True)
    git(repo, "gc", "-q", "--prune=now")


def verify_standalone(root: Path, repo: Path, base: str, candidate: str | None = None) -> None:
    """The fail-closed postconditions of the history-free task repository (F8 / T21)."""
    if git(repo, "rev-parse", "--show-toplevel").strip() != str(repo):
        raise ValueError("REPO_NOT_STANDALONE")
    if git(repo, "rev-list", "--all").split() != [base]:
        raise ValueError("REPO_HISTORY_NOT_FROZEN")
    if git(repo, "remote").strip():
        raise ValueError("REPO_REMOTE_PRESENT")
    if (repo / ".git/objects/info/alternates").exists():
        raise ValueError("REPO_ALTERNATES_PRESENT")
    if object_names(repo) != reachable_objects(repo):
        raise ValueError("REPO_OBJECTS_EXCEED_BASE_TREE")
    if candidate and subprocess.run(
            ["git", "-C", str(repo), "cat-file", "-e", candidate],
            capture_output=True).returncode == 0:
        raise ValueError("CANDIDATE_REACHABLE")
    leaked = governance_paths(repo / ".git", root)
    if leaked:
        raise ValueError(f"GOVERNANCE_PATH_IN_GIT_METADATA:{leaked[0]}")


def delivery(root: Path, materials: str, arm: str) -> dict[str, bytes]:
    """Reuse prepare_run.sh's byte composition, with every input read from objects."""
    def blob(rel):
        return git(root, "show", f"{materials}:{rel}", binary=True)

    if arm == "control":
        carrier = (blob(f"{H2_REL}/harness/control-carrier-header.md")
                   + blob("AGENTS.md")
                   + blob(f"{H2_REL}/harness/control-carrier-footer.md"))
    elif arm == "variant":
        carrier = blob(f"{H2_REL}/carriers/H2_LEAN_BOOTSTRAP.md")
        manifest = json.loads(blob(f"{H2_REL}/variant-manifest.json"))
        if sha256(carrier) != manifest["freeze"]["VARIANT_HASH"]:
            raise ValueError("CARRIER_HASH_MISMATCH")
    else:
        raise ValueError("BAD_ARM")
    out = {"AGENTS.md": carrier, "H2_RULES.md": blob("RULES.md")}
    routes = json.loads(blob(f"{H2_REL}/routes-h2.json"))["routes"]
    dests = sorted({r["destination"] for r in routes if r.get("surface") == "S3"})
    if not dests:
        raise ValueError("EMPTY_WARM_BUNDLE")
    for dest in dests:
        path = PurePosixPath(dest)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("UNSAFE_WARM_DESTINATION")
        out[f"H2_WARM/{dest}"] = blob(dest)
    return out


def verify_repo(root: Path, repo: Path, base: str) -> None:
    if git(repo, "rev-parse", "HEAD").strip() != base:
        raise ValueError("WRONG_BASE")
    base_paths = set(git(root, "ls-tree", "-r", "-t", "--name-only", base).splitlines())
    for path in repo.rglob("*"):
        if path.name in DELIVERED_NAMES and path.relative_to(repo).as_posix() not in base_paths:
            raise ValueError("DELIVERY_INSIDE_REPO")
    if git(repo, "status", "--porcelain", "--ignored"):
        raise ValueError("REPO_NOT_CLEAN")


def outside_repository(run_dir: Path) -> None:
    ancestor = run_dir
    while not ancestor.exists():
        ancestor = ancestor.parent
    result = subprocess.run(["git", "-C", str(ancestor), "rev-parse", "--git-dir"],
                            capture_output=True)
    if result.returncode == 0:
        raise ValueError("RUN_DIR_INSIDE_REPOSITORY")


def cleanup(root: Path, run_dir: Path) -> None:
    """Remove a run: a linked worktree through Git, a standalone repository by deletion."""
    run_dir = Path(run_dir).resolve()
    repo = run_dir / "repo"
    if (repo / ".git").is_file():                     # the pre-T21 linked-worktree layout
        git(root, "worktree", "remove", "--force", str(repo))
        git(root, "worktree", "prune")
    if run_dir.exists():
        shutil.rmtree(run_dir)


def prepare(root: Path, run_dir: Path, task_id: str, arm: str, materials: str) -> dict:
    root, run_dir = Path(root).resolve(), Path(run_dir).resolve()
    outside_repository(run_dir)
    root_reason = run_root_reason(run_dir)
    if root_reason is not None:
        raise ValueError(root_reason)
    if run_dir.exists():
        raise ValueError("RUN_DIR_EXISTS")
    materials = git(root, "rev-parse", "--verify", f"{materials}^{{commit}}").strip()
    shortlist = json.loads(git(root, "show", f"{materials}:{H2_REL}/admission/"
                               "freeze-v2-input/shortlist.json"))["shortlist"]
    tasks = {f"f{i:02d}": t for i, t in enumerate(shortlist, 1)}
    if task_id not in tasks:
        raise ValueError("UNKNOWN_TASK")
    base = tasks[task_id]["BASE_SHA"]
    candidate = tasks[task_id].get("CANDIDATE_SHA")
    files = delivery(root, materials, arm)
    warm_lines = [f"{rel.removeprefix('H2_WARM/')} {sha256(data)}"
                  for rel, data in sorted(files.items()) if rel.startswith("H2_WARM/")]
    receipt = {"task_id": task_id, "arm": arm, "base_sha": base,
               "materials_commit": materials,
               "repository_kind": "standalone_history_free",
               "carrier_kind": "control_full_v1" if arm == "control" else "variant_lean_v1",
               "carrier_sha256": sha256(files["AGENTS.md"]),
               "rules_sha256": sha256(files["H2_RULES.md"]),
               "warm_bundle_sha256": sha256("\n".join(warm_lines).encode()),
               "program_sha256": sha256(Path(__file__).read_bytes())}
    run_dir.mkdir()
    try:
        standalone_repository(root, run_dir / "repo", base)
        for rel, data in files.items():
            path = run_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        outside_repository(run_dir)
        verify_repo(root, run_dir / "repo", base)
        verify_standalone(root, run_dir / "repo", base, candidate)
        (run_dir / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n",
                                               encoding="utf-8")
    except BaseException:
        cleanup(root, run_dir)
        raise
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare")
    build.add_argument("run_dir", type=Path)
    build.add_argument("task_id")
    build.add_argument("arm", choices=("control", "variant"))
    build.add_argument("--materials", required=True)
    remove = commands.add_parser("cleanup")
    remove.add_argument("run_dir", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            print(json.dumps(prepare(ROOT, args.run_dir, args.task_id, args.arm, args.materials)))
        else:
            cleanup(ROOT, args.run_dir)
    except ValueError as exc:
        parser.exit(1, f"WRAPPER_DELIVERY_FAIL {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
