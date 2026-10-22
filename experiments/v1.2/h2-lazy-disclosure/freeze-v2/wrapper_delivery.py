#!/usr/bin/env python3
"""Commit-sourced delivery outside the task worktree; never executes a worker."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path, PurePosixPath

H2_REL = "experiments/v1.2/h2-lazy-disclosure"
ROOT = Path(__file__).resolve().parents[4]
DELIVERED_NAMES = {"AGENTS.md", "H2_RULES.md", "H2_WARM"}


def git(root: Path, *args: str, binary: bool = False):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True,
                            text=not binary)
    if result.returncode:
        raise ValueError(f"GIT_FAILED: {' '.join(args[:2])}")
    return result.stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


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
    """Remove a linked task worktree using Git, then remove its wrapper."""
    run_dir = Path(run_dir).resolve()
    repo = run_dir / "repo"
    if (repo / ".git").exists():
        git(root, "worktree", "remove", "--force", str(repo))
    git(root, "worktree", "prune")
    if run_dir.exists():
        shutil.rmtree(run_dir)


def prepare(root: Path, run_dir: Path, task_id: str, arm: str, materials: str) -> dict:
    root, run_dir = Path(root).resolve(), Path(run_dir).resolve()
    outside_repository(run_dir)
    if run_dir.exists():
        raise ValueError("RUN_DIR_EXISTS")
    materials = git(root, "rev-parse", "--verify", f"{materials}^{{commit}}").strip()
    shortlist = json.loads(git(root, "show", f"{materials}:{H2_REL}/admission/"
                               "freeze-v2-input/shortlist.json"))["shortlist"]
    tasks = {f"f{i:02d}": t for i, t in enumerate(shortlist, 1)}
    if task_id not in tasks:
        raise ValueError("UNKNOWN_TASK")
    base = tasks[task_id]["BASE_SHA"]
    files = delivery(root, materials, arm)
    warm_lines = [f"{rel.removeprefix('H2_WARM/')} {sha256(data)}"
                  for rel, data in sorted(files.items()) if rel.startswith("H2_WARM/")]
    receipt = {"task_id": task_id, "arm": arm, "base_sha": base,
               "materials_commit": materials,
               "carrier_kind": "control_full_v1" if arm == "control" else "variant_lean_v1",
               "carrier_sha256": sha256(files["AGENTS.md"]),
               "rules_sha256": sha256(files["H2_RULES.md"]),
               "warm_bundle_sha256": sha256("\n".join(warm_lines).encode()),
               "program_sha256": sha256(Path(__file__).read_bytes())}
    run_dir.mkdir()
    try:
        git(root, "worktree", "add", "-q", "--detach", str(run_dir / "repo"), base)
        for rel, data in files.items():
            path = run_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        outside_repository(run_dir)
        verify_repo(root, run_dir / "repo", base)
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
