#!/usr/bin/env python3
"""Collect one wrapper run: the FULL base->worker delta of repo/, its report and its telemetry.

F15 / T28 / protocol-v2 §5. Nothing here is synthesised, and nothing the worker can write decides
what changed:

  * the base is the driver's own snapshot `<runs_root>/.driver/<run_id>/base` plus
    `base-manifest.json`, recorded from the GOVERNANCE repository at prepare time, outside the
    sandbox and outside anything the worker can reach. F24 / T32: the base COMMIT is read from
    that manifest and never from `receipt.json`, which sits in the worker's cwd;
  * the delta is the WORKTREE walked on the filesystem (`.git/` excluded) and compared by bytes,
    mode and type (file/symlink) against that manifest — A / M / D / T. `git status`, the index,
    index flags (assume-unchanged, skip-worktree), `.gitignore`, `.gitattributes` filters, repo-local
    config and `refs/replace` take no part, so a committed result is included and a hidden one too;
  * the diff handed to acceptance and to the auditor is rendered from the snapshot's bytes against
    the worktree's bytes (pure Python, no git), so no filter or external diff driver can redact it;
  * every remaining git call on repo/ runs under the isolation of `wrapper_delivery.repo_git`;
  * every delivered byte is re-verified twice: against the receipt's own hashes and against a fresh
    recomposition from the materials commit, so a receipt that agrees with tampered files is still
    refused;
  * F33 / T38a: the evidence tree is the driver's post-sweep SNAPSHOT (`.driver/<run_id>/
    attempt-<n>/snapshot`), never the live run directory, while the base manifest keeps being read
    from the run's own driver directory (`identity_dir`);
  * report and telemetry must both exist and carry content. A missing or empty one makes the run
    INVALID; a reason string is recorded instead of an invented log line.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import stat
from pathlib import Path

import wrapper_delivery
from wrapper_delivery import H2_REL, ROOT, delivery, sha256

DELIVERED_FILES = ("AGENTS.md", "H2_RULES.md")
DELIVERED_DIR = "H2_WARM"
RECEIPT_HASH_KEYS = {"AGENTS.md": "carrier_sha256", "H2_RULES.md": "rules_sha256"}
ARTIFACTS = (("report.md", "MISSING_REPORT", "EMPTY_REPORT"),
             (".h2-telemetry.log", "MISSING_TELEMETRY", "EMPTY_TELEMETRY"))
DIFF_CAP = 4 * 1024 * 1024


def registry(root: Path = ROOT) -> dict:
    return json.loads((root / H2_REL / "freeze-v3/task-registry-v3.json").read_text())


def task_of(registry_data: dict, task_id: str) -> dict | None:
    return next((t for t in registry_data["tasks"] if t["task_id"] == task_id), None)


def worktree_state(repo: Path) -> dict[str, dict]:
    """Every path the worker left in repo/, by lstat: type, mode and content sha256.

    `.git/` at the worktree root is the repository's own metadata, not a task file, and is the one
    and only exclusion: nothing else is filtered by an ignore file or an attribute.
    """
    repo = Path(repo)
    state: dict[str, dict] = {}
    for directory, dirnames, filenames in os.walk(repo, followlinks=False):
        current = Path(directory)
        if current == repo:
            dirnames[:] = sorted(name for name in dirnames if name != ".git")
        candidates = [name for name in dirnames if (current / name).is_symlink()]
        candidates.extend(filenames)
        for name in sorted(candidates):
            path = current / name
            rel = path.relative_to(repo).as_posix()
            try:
                info = path.lstat()
            except OSError:
                continue
            if stat.S_ISLNK(info.st_mode):
                state[rel] = {"type": "symlink", "mode": "120000",
                              "sha256": sha256(os.fsencode(os.readlink(path)))}
            elif stat.S_ISREG(info.st_mode):
                state[rel] = {"type": "file",
                              "mode": "100755" if info.st_mode & 0o111 else "100644",
                              "sha256": sha256(wrapper_delivery.safe_read(path))}
            else:
                state[rel] = {"type": "other", "mode": "000000", "sha256": None}
    return state


def changes_against(manifest: dict, state: dict[str, dict]) -> list[dict]:
    """A / M / D / T between the driver's base manifest and the worktree state."""
    entries = manifest["entries"]
    changes = []
    for path in sorted(set(entries) | set(state)):
        old, new = entries.get(path), state.get(path)
        if old is None:
            status = "A"
        elif new is None:
            status = "D"
        elif old.get("type") != new.get("type"):
            status = "T"
        elif old.get("sha256") != new.get("sha256") or old.get("mode") != new.get("mode"):
            status = "M"
        else:
            continue
        changes.append({"status": status, "path": path})
    return changes


def side_bytes(root: Path, path: str, entry: dict | None) -> bytes | None:
    if entry is None:
        return None
    full = Path(root) / path
    if entry.get("type") == "symlink":
        return os.fsencode(os.readlink(full))
    if entry.get("type") == "other":
        return b""
    return wrapper_delivery.safe_read(full)


def text_lines(data: bytes) -> list[str] | None:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if "\0" in text:
        return None
    return text.splitlines(keepends=True)


def file_diff(old: bytes | None, new: bytes | None, old_label: str, new_label: str) -> list[str]:
    old_lines = [] if old is None else text_lines(old)
    new_lines = [] if new is None else text_lines(new)
    if old_lines is None or new_lines is None:
        return [f"Binary files {old_label} and {new_label} differ"]
    return list(difflib.unified_diff(old_lines, new_lines, fromfile=old_label,
                                     tofile=new_label, n=3))


def render_diff(snapshot: Path, repo: Path, manifest: dict, state: dict[str, dict],
                changes: list[dict]) -> str:
    """A deterministic unified diff of the SNAPSHOT's bytes against the WORKTREE's bytes."""
    entries = manifest["entries"]
    chunks = []
    for change in sorted(changes, key=lambda item: item["path"]):
        path, status = change["path"], change["status"]
        old_entry, new_entry = entries.get(path), state.get(path)
        old = side_bytes(snapshot, path, old_entry)
        new = side_bytes(repo, path, new_entry)
        old_mode = (old_entry or {}).get("mode")
        new_mode = (new_entry or {}).get("mode")
        lines = [f"diff --git a/{path} b/{path}"]
        if status == "A":
            lines.append(f"new file mode {new_mode}")
        elif status == "D":
            lines.append(f"deleted file mode {old_mode}")
        elif old_mode != new_mode:
            lines.append(f"old mode {old_mode}")
            lines.append(f"new mode {new_mode}")
        lines.extend(file_diff(old, new, f"a/{path}" if old is not None else "/dev/null",
                               f"b/{path}" if new is not None else "/dev/null"))
        chunks.append("".join(line if line.endswith("\n") else line + "\n" for line in lines))
    return "".join(chunks)


def verify_delivery(root: Path, run_dir: Path) -> tuple[dict, dict[str, str], list[str]]:
    """Re-verify delivered files without following links."""
    receipt_path = run_dir / "receipt.json"
    if receipt_path.is_symlink():
        return {"type": "symlink", "sha256": sha256(os.fsencode(os.readlink(receipt_path)))}, {}, ["EVIDENCE_UNREADABLE:receipt.json"]
    try:
        receipt = json.loads(wrapper_delivery.safe_read(receipt_path))
    except (OSError, ValueError):
        return {}, {}, ["UNREADABLE_RECEIPT"]
    if not isinstance(receipt, dict) or not {"task_id", "arm", "delivered_head",
                                             "materials_commit", "carrier_sha256", "rules_sha256",
                                             "warm_bundle_sha256", "program_sha256"} <= set(receipt):
        return {}, {}, ["INCOMPLETE_RECEIPT"]
    reasons, hashes = [], {}
    warm_root = run_dir / DELIVERED_DIR
    paths = list(DELIVERED_FILES)
    if warm_root.is_symlink() or not warm_root.is_dir():
        reasons.append(f"MISSING_DELIVERED_DIR:{DELIVERED_DIR}")
    else:
        for directory, dirs, files in os.walk(warm_root, followlinks=False):
            for name in list(dirs):
                path = Path(directory) / name
                if path.is_symlink():
                    paths.append(path.relative_to(run_dir).as_posix())
                    dirs.remove(name)
            paths.extend((Path(directory) / name).relative_to(run_dir).as_posix() for name in files)
        if len(paths) == len(DELIVERED_FILES):
            reasons.append(f"MISSING_DELIVERED_DIR:{DELIVERED_DIR}")
    for rel in sorted(paths):
        path = run_dir / rel
        try:
            info = path.lstat()
            if stat.S_ISLNK(info.st_mode):
                hashes[rel] = sha256(os.fsencode(os.readlink(path)))
                reasons.append(f"EVIDENCE_UNREADABLE:{rel}")
            else:
                hashes[rel] = sha256(wrapper_delivery.safe_read(path))
        except OSError:
            reasons.append(f"MISSING_DELIVERED_FILE:{rel}")
            continue
        if rel in RECEIPT_HASH_KEYS and hashes[rel] != receipt.get(RECEIPT_HASH_KEYS[rel]):
            reasons.append(f"DELIVERED_HASH_MISMATCH:{rel}")
    warm_lines = [f"{rel[len(DELIVERED_DIR) + 1:]} {hashes[rel]}" for rel in sorted(hashes)
                  if rel.startswith(DELIVERED_DIR + "/")]
    if warm_lines and sha256("\n".join(warm_lines).encode()) != receipt.get("warm_bundle_sha256"):
        reasons.append("WARM_BUNDLE_HASH_MISMATCH")
    program = Path(__file__).resolve().parent / "wrapper_delivery.py"
    if sha256(program.read_bytes()) != receipt.get("program_sha256"):
        reasons.append("DELIVERY_PROGRAM_MISMATCH")
    try:
        expected = delivery(root, receipt["materials_commit"], receipt["arm"])
    except (ValueError, KeyError):
        expected = {}
        reasons.append("DELIVERY_RECOMPOSITION_UNAVAILABLE")
    for rel, data in expected.items():
        try:
            if wrapper_delivery.safe_read(run_dir / rel) != data:
                reasons.append(f"DELIVERED_BYTES_NOT_FROM_MATERIALS:{rel}")
        except OSError:
            reasons.append(f"MISSING_DELIVERED_FILE:{rel}")
    for rel in hashes:
        if rel not in expected:
            reasons.append(f"UNDELIVERED_EXTRA_FILE:{rel}")
    return receipt, hashes, sorted(set(reasons))


def artifact(run_dir: Path, name: str, missing: str, empty: str) -> tuple[dict, list[str]]:
    path = run_dir / name
    try:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            data = os.fsencode(os.readlink(path))
            return {"present": True, "type": "symlink", "sha256": sha256(data)}, [f"EVIDENCE_UNREADABLE:{name}"]
        data = wrapper_delivery.safe_read(path)
    except OSError:
        return {"present": False}, [missing]
    record = {"present": True, "bytes": len(data), "lines": data.count(b"\n"),
              "sha256": sha256(data)}
    if not data.strip():
        return record, [empty]
    return record, []


def base_snapshot(run_dir: Path, reasons: list[str]) -> dict | None:
    """The driver-recorded base manifest, or None with the fail-closed reason recorded.

    F24 / T32: the base identity is read from the DRIVER's manifest, not from `receipt.json`. The
    receipt lives in the worker's cwd and therefore may not name the original base commit; the
    manifest lives under `<runs_root>/.driver/<run_id>/`, outside anything the worker can write.
    """
    try:
        return wrapper_delivery.read_base_manifest(run_dir)
    except ValueError as exc:
        reasons.append(str(exc))
        return None


def repository_shape(repo: Path, reasons: list[str]) -> bool:
    """The remaining git facts about repo/, each read under the F15 isolation."""
    try:
        if wrapper_delivery.repo_git(repo, "rev-parse", "--show-toplevel").strip() != str(repo):
            reasons.append("TASK_REPOSITORY_NOT_THE_ROOT")
        # F8 / T21: the task repository is standalone and history-free; a worker that reaches
        # another repository through a remote or an alternates link has escaped its tree.
        if wrapper_delivery.repo_git(repo, "remote").strip():
            reasons.append("TASK_REPOSITORY_HAS_REMOTE")
        if (repo / ".git/objects/info/alternates").exists():
            reasons.append("TASK_REPOSITORY_HAS_ALTERNATES")
    except ValueError:
        reasons.append("TASK_REPOSITORY_UNREADABLE")
        return False
    return True


def collect(root: Path = ROOT, run_dir: Path | None = None, *,
            identity_dir: Path | None = None) -> dict:
    """Collect one run. `run_dir` is the EVIDENCE tree (the driver's snapshot when it has one).

    `identity_dir` is the run's own directory and is used only for the driver-side base snapshot
    (`.driver/<run_id>/base-manifest.json`), which lives outside the evidence tree; it defaults to
    `run_dir` for the CLI form.
    """
    root, run_dir = Path(root).resolve(), Path(run_dir).absolute()
    identity_dir = Path(identity_dir).resolve() if identity_dir is not None else run_dir
    registry_data = registry(root)
    receipt, delivered, reasons = verify_delivery(root, run_dir)
    repo = run_dir / "repo"
    task = task_of(registry_data, str(receipt.get("task_id")))
    if receipt and task is None:
        reasons.append("UNKNOWN_TASK")
    base = ""
    changes: list[dict] = []
    diff = b""
    if not repo.is_dir():
        reasons.append("MISSING_TASK_REPOSITORY")
    elif repo.is_symlink():
        reasons.append("TASK_REPOSITORY_UNREADABLE")
    else:
        manifest = base_snapshot(identity_dir, reasons)
        if manifest is not None:
            base = str(manifest.get("base_sha") or "")
            if task is not None and base != task["base_sha"]:
                # The driver's snapshot and the frozen registry must name the same base tree.
                reasons.append("BASE_SNAPSHOT_DOES_NOT_MATCH_REGISTRY")
                manifest = None
        readable = repository_shape(repo, reasons)
        if manifest is not None and readable:
            try:
                state = worktree_state(repo)
                changes = changes_against(manifest, state)
                diff = render_diff(wrapper_delivery.base_dir(identity_dir), repo, manifest, state,
                                   changes).encode("utf-8", "surrogateescape")
            except OSError:
                # An unreadable worktree (permissions, a vanished race) is never a clean delta.
                reasons.append("TASK_REPOSITORY_UNREADABLE")
                changes, diff = [], b""
    records, reasons_for_artifacts = [], []
    for name, missing, empty in ARTIFACTS:
        record, found = artifact(run_dir, name, missing, empty)
        records.append({"name": name, **record})
        reasons_for_artifacts.extend(found)
    reasons.extend(reasons_for_artifacts)
    if len(diff) > DIFF_CAP:
        reasons.append("DIFF_OVERSIZE")
    return {
        "schema_version": 1,
        "program": "freeze-v3/collect_v2.py",
        "run_id": (f"h2r3-{receipt['task_id']}-{str(receipt['arm'])[0]}"
                   if receipt.get("task_id") and receipt.get("arm") else None),
        "task_id": receipt.get("task_id"),
        "arm": receipt.get("arm"),
        "base_sha": base or None,
        "delivered_head": receipt.get("delivered_head"),
        "materials_commit": receipt.get("materials_commit"),
        "receipt": receipt,
        "delivered_hashes": delivered,
        "changes": changes,
        "diff_sha256": sha256(diff),
        "diff_bytes": len(diff),
        "diff": diff.decode("utf-8", "replace"),
        "artifacts": records,
        "reasons": sorted(set(reasons)),
        "status": "INVALID" if reasons else "VALID",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    collected = collect(args.root, args.run_dir)
    target = args.out or args.run_dir / "collected.json"
    target.write_text(json.dumps(collected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": collected["run_id"], "status": collected["status"],
                      "changes": len(collected["changes"]),
                      "reasons": collected["reasons"]}, sort_keys=True))
    return 0 if collected["status"] == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
