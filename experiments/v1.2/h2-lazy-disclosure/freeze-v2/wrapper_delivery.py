#!/usr/bin/env python3
"""Commit-sourced delivery outside the task repository; never executes a worker."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pwd
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
# F20 / T30: "under a home" means every home the OS declares, not only the one the process runs
# with. The database also lists service accounts whose "home" is a plain directory (/var/empty,
# /dev/null, /Library/WebServer); a run root belongs under none of them, and the shared users
# folder is exactly where the operator's run root is meant to live.
SHARED_USERS_FOLDER = Path("/Users") / "Shared"
NON_HOME_DIRECTORIES = frozenset(Path(name) for name in ("", "/var/empty", "/dev/null"))
# F8 / T21: `repo/` is a STANDALONE repository whose object store is exactly the task base tree, so
# no worker can read the historical fix out of a shared object database. F18 / T28: the object that
# is delivered is a NEW, parentless commit with the base TREE and a fixed neutral message, author,
# committer and date — so the base commit itself is never fetched and `git log` names nothing.
# The objects are fetched through one temporary ref in the governance repository, deleted again
# before the worker sees the tree; the ref name is the only trace a crash could leave behind.
HISTORY_REF_ROOT = "refs/h2-delivery"
NEUTRAL_MESSAGE = "h2 task base"
NEUTRAL_IDENTITY = {"GIT_AUTHOR_NAME": "H2 Delivery", "GIT_AUTHOR_EMAIL": "h2@delivery.invalid",
                    "GIT_COMMITTER_NAME": "H2 Delivery", "GIT_COMMITTER_EMAIL": "h2@delivery.invalid",
                    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00 +0000",
                    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00 +0000"}
GIT_METADATA_FILES = ("FETCH_HEAD", "ORIG_HEAD", "COMMIT_EDITMSG", "packed-refs")
GIT_METADATA_DIRS = ("logs", "refs/remotes", "refs/tags", "worktrees")
# F15 / T28: the collection must trust nothing the worker can write. Changes are decided by walking
# the worktree's bytes, against a base snapshot the DRIVER recorded from the governance repository
# before the worker started (`.driver/<run_id>/base` + its manifest). No index, repo-local config,
# attribute or filter of repo/ takes part — not even for the git calls that remain.
DRIVER_DIR = ".driver"
BASE_DIR_NAME = "base"
BASE_MANIFEST_NAME = "base-manifest.json"


def operator_home() -> Path:
    return Path.home()


def discoverable_ancestor(run_dir: Path) -> str | None:
    """The first marker on any ancestor of `run_dir` (the run dir's own carrier excepted).

    `os.path.lexists` is deliberate (F20 / T30): a BROKEN symlink named `.agents` or `.opencode`
    is still a discovery point for a runtime that walks up from the cwd, so it must refuse the
    run root just like a real directory.
    """
    resolved = Path(run_dir).resolve()
    for ancestor in (resolved, *resolved.parents):
        for marker in ANCESTOR_MARKERS:
            if ancestor == resolved and marker == "AGENTS.md":
                continue                      # the arm carrier prepare writes itself
            if os.path.lexists(ancestor / marker):
                return marker
    return None


def os_home_directories() -> list[Path]:
    """Every home the OS user database declares, minus the ones that are not homes (F20 / T30)."""
    homes: list[Path] = []
    for entry in pwd.getpwall():
        path = Path(entry.pw_dir or "")
        if path in NON_HOME_DIRECTORIES or not path.is_absolute():
            continue
        if path == SHARED_USERS_FOLDER or path in homes:
            continue
        if not path.is_dir():                 # /dev/null and service-account paths that never existed
            continue
        homes.append(path)
    return homes


def run_root_reason(run_dir: Path) -> str | None:
    """Why `run_dir` is not an acceptable run root, or None when it is (F4 / T13, F20 / T30).

    Two independent refusals: a root below ANY home the OS declares (so a run started with a
    redirected HOME cannot land in the operator's real home or in another account's), and a root
    below a directory that carries a discoverable guidance marker.
    """
    resolved = Path(run_dir).resolve()
    operator = operator_home().resolve()
    if resolved == operator or operator in resolved.parents:
        return "RUN_DIR_UNDER_OPERATOR_HOME"
    for home in os_home_directories():
        home = home.resolve()
        if home == operator:
            continue
        if resolved == home or home in resolved.parents:
            return "RUN_DIR_UNDER_USER_HOME"
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


def repo_git(repo: Path, *args: str, binary: bool = False):
    """A git call on the WORKER's repository, under the isolation F15 / T28 requires.

    The worker owns repo/.git: its index flags, refs/replace, attribute files and local config
    must not be able to decide what this program sees, so every such call runs with no system or
    global config, no replacement objects and no attributes file.
    """
    env = {**os.environ, "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_NO_REPLACE_OBJECTS": "1"}
    result = subprocess.run(["git", "-C", str(repo), "-c",
                             f"core.attributesFile={os.devnull}", "-c", "core.fsmonitor=false",
                             *args], capture_output=True, text=not binary, env=env)
    if result.returncode:
        raise ValueError(f"GIT_FAILED: {' '.join(args[:2])}")
    return result.stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def driver_root(run_dir: Path) -> Path:
    """`<runs_root>/.driver/<run_id>` — outside the run dir the worker can write."""
    run_dir = Path(run_dir)
    return run_dir.parent / DRIVER_DIR / run_dir.name


def base_dir(run_dir: Path) -> Path:
    return driver_root(run_dir) / BASE_DIR_NAME


def base_manifest_path(run_dir: Path) -> Path:
    return driver_root(run_dir) / BASE_MANIFEST_NAME


def read_base_manifest(run_dir: Path) -> dict:
    """The driver-recorded base manifest; a missing or malformed one is a fail-closed state."""
    path = base_manifest_path(run_dir)
    if not path.is_file():
        raise ValueError("MISSING_BASE_SNAPSHOT")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("UNREADABLE_BASE_SNAPSHOT") from None
    if (not isinstance(manifest, dict) or not isinstance(manifest.get("entries"), dict)
            or not manifest.get("base_sha") or not base_dir(run_dir).is_dir()):
        raise ValueError("INCOMPLETE_BASE_SNAPSHOT")
    return manifest


def discard_base(run_dir: Path) -> None:
    root = driver_root(run_dir)
    shutil.rmtree(root, ignore_errors=True)
    try:
        root.parent.rmdir()
    except OSError:
        pass


def _tree_entries(root: Path, base: str) -> list[tuple[str, str, str]]:
    """(mode, blob sha, path) for every blob of `base`'s tree — attributes cannot drop a path."""
    data = git(root, "ls-tree", "-r", "-z", "--full-tree", base, binary=True)
    entries = []
    for part in data.split(b"\0"):
        if not part:
            continue
        header, raw_path = part.split(b"\t", 1)
        mode, kind, oid = header.decode("ascii").split(" ")
        path = raw_path.decode("utf-8")
        if kind != "blob":
            raise ValueError(f"UNSUPPORTED_TREE_ENTRY:{path}")
        entries.append((mode, oid, path))
    return entries


def _blob_bytes(root: Path, oids: list[str]) -> dict[str, bytes]:
    """Read every blob from the governance object store by id."""
    wanted = sorted(set(oids))
    if not wanted:
        return {}
    result = subprocess.run(["git", "-C", str(root), "cat-file", "--batch"],
                            input=("\n".join(wanted) + "\n").encode("ascii"),
                            capture_output=True)
    if result.returncode:
        raise ValueError("GIT_FAILED: cat-file --batch")
    payload, blobs, offset = result.stdout, {}, 0
    for oid in wanted:
        newline = payload.find(b"\n", offset)
        if newline < 0:
            raise ValueError("UNREADABLE_TREE_BLOB")
        fields = payload[offset:newline].decode("ascii").split()
        offset = newline + 1
        if len(fields) != 3 or fields[1] != "blob":
            raise ValueError("UNREADABLE_TREE_BLOB")
        size = int(fields[2])
        blobs[oid] = payload[offset:offset + size]
        offset += size + 1
    return blobs


def record_base(root: Path, run_dir: Path, base: str) -> dict:
    """Record the base tree from the GOVERNANCE repo, outside anything the worker can write.

    Writes `<runs_root>/.driver/<run_id>/base/` and `base-manifest.json`: every path with its mode,
    type (file/symlink), git blob sha and content sha256. The worker never sees this directory; the
    collection compares its worktree against it instead of asking repo/.git what changed.
    """
    entries = _tree_entries(Path(root), base)
    blobs = _blob_bytes(Path(root), [oid for _, oid, _ in entries])
    target = driver_root(run_dir)
    # F19 / T29: the driver root also holds the per-launch homes and the driver-held streams of
    # earlier attempts. Replace the base snapshot only; never wipe that evidence.
    target.mkdir(parents=True, exist_ok=True)
    tree = target / BASE_DIR_NAME
    shutil.rmtree(tree, ignore_errors=True)
    (target / BASE_MANIFEST_NAME).unlink(missing_ok=True)
    tree.mkdir(parents=True)
    manifest_entries: dict[str, dict] = {}
    for mode, oid, path in entries:
        data = blobs[oid]
        destination = tree / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if mode == "120000":
            destination.symlink_to(data.decode("utf-8"))
            kind = "symlink"
        else:
            destination.write_bytes(data)
            destination.chmod(0o755 if mode == "100755" else 0o644)
            kind = "file"
        manifest_entries[path] = {"mode": mode, "type": kind, "blob_sha": oid,
                                  "sha256": sha256(data)}
    manifest = {"schema_version": 1, "program": "freeze-v2/wrapper_delivery.py",
                "source": "governance_repository", "base_sha": base,
                "entries": manifest_entries}
    (target / BASE_MANIFEST_NAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                             encoding="utf-8")
    return manifest


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
    return set(repo_git(repo, "cat-file", "--batch-all-objects",
                        "--batch-check=%(objectname)").split())


def reachable_objects(repo: Path) -> set[str]:
    """Every object reachable from HEAD and the refs — i.e. the delivered commit and its tree."""
    lines = repo_git(repo, "rev-list", "--objects", "--all").splitlines()
    return {line.split(" ", 1)[0] for line in lines if line}


def neutral_commit(root: Path, base: str) -> str:
    """A parentless commit with `base`'s TREE and fixed metadata; deterministic for that tree."""
    tree = git(root, "rev-parse", "--verify", f"{base}^{{tree}}").strip()
    result = subprocess.run(["git", "-C", str(root), "commit-tree", tree, "-m", NEUTRAL_MESSAGE],
                            capture_output=True, text=True, env={**os.environ, **NEUTRAL_IDENTITY})
    if result.returncode:
        raise ValueError("NEUTRAL_COMMIT_FAILED")
    return result.stdout.strip()


def standalone_repository(root: Path, repo: Path, base: str) -> None:
    """Create `repo` as a standalone repository holding exactly `base`'s tree (F8, F18).

    The delivered HEAD is a NEW parentless commit with the base tree and a fixed neutral message,
    author, committer and date, so it is deterministic and names neither the base nor the
    candidate. Only that commit is fetched, through one temporary ref in the governance
    repository that is deleted again; everything that could name the governance repository or
    another commit is removed: remotes, FETCH_HEAD, reflogs, other refs, alternates and any object
    outside the delivered tree.
    """
    root, repo = Path(root), Path(repo)
    neutral = neutral_commit(root, base)
    ref = f"{HISTORY_REF_ROOT}/{os.getpid()}-{uuid.uuid4().hex[:8]}"
    git(root, "update-ref", ref, neutral)
    try:
        repo.mkdir(parents=True)
        git(repo, "init", "-q")
        git(repo, "fetch", "-q", "--no-tags", "--depth", "1", str(root), ref)
        git(repo, "checkout", "-q", "--detach", neutral)
    finally:
        git(root, "update-ref", "-d", ref)
    metadata = repo / ".git"
    for name in GIT_METADATA_FILES:
        (metadata / name).unlink(missing_ok=True)
    for name in GIT_METADATA_DIRS:
        shutil.rmtree(metadata / name, ignore_errors=True)
    (metadata / "objects/info/alternates").unlink(missing_ok=True)
    repo_git(repo, "reflog", "expire", "--expire=now", "--all")
    shutil.rmtree(metadata / "logs", ignore_errors=True)
    repo_git(repo, "gc", "-q", "--prune=now")


def verify_standalone(root: Path, repo: Path, base: str, candidate: str | None = None) -> str:
    """The fail-closed postconditions of the history-free task repository (F8, F18)."""
    if repo_git(repo, "rev-parse", "--show-toplevel").strip() != str(repo):
        raise ValueError("REPO_NOT_STANDALONE")
    delivered = repo_git(repo, "rev-parse", "HEAD").strip()
    if repo_git(repo, "rev-list", "--all").split() != [delivered]:
        raise ValueError("REPO_HISTORY_NOT_FROZEN")
    if repo_git(repo, "rev-parse", f"{delivered}^{{tree}}").strip() != git(
            root, "rev-parse", f"{base}^{{tree}}").strip():
        raise ValueError("DELIVERED_TREE_DIFFERS_FROM_BASE")
    log = repo_git(repo, "log", "--all", "--format=%H%n%an%n%ae%n%B")
    if base in log or delivered == base:
        raise ValueError("BASE_COMMIT_IN_DELIVERED_HISTORY")
    if candidate and candidate in log:
        raise ValueError("CANDIDATE_IN_DELIVERED_HISTORY")
    if repo_git(repo, "remote").strip():
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
    return delivered


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


def verify_repo(root: Path, repo: Path, base: str, delivered: str) -> None:
    if repo_git(repo, "rev-parse", "HEAD").strip() != delivered:
        raise ValueError("WRONG_BASE")
    base_paths = set(git(root, "ls-tree", "-r", "-t", "--name-only", base).splitlines())
    for path in repo.rglob("*"):
        if path.name in DELIVERED_NAMES and path.relative_to(repo).as_posix() not in base_paths:
            raise ValueError("DELIVERY_INSIDE_REPO")
    if repo_git(repo, "status", "--porcelain", "--ignored"):
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
    discard_base(run_dir)
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
        delivered = repo_git(run_dir / "repo", "rev-parse", "HEAD").strip()
        for rel, data in files.items():
            path = run_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        outside_repository(run_dir)
        verify_repo(root, run_dir / "repo", base, delivered)
        verify_standalone(root, run_dir / "repo", base, candidate)
        record_base(root, run_dir, base)
        receipt["delivered_head"] = delivered
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
