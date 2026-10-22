#!/usr/bin/env python3
"""Collect one wrapper run: the FULL base->worker delta of repo/, its report and its telemetry.

CODEX_FIXES_1 T11 / protocol-v2 §5. Nothing here is synthesised:

  * the delta is `git diff <registry base>` (tracked, committed, deleted and renamed paths) plus
    the untracked AND ignored files, i.e. the WHOLE difference between the frozen base and what the
    worker left in repo/. A worker commit is included because the comparison is against the
    registry base, never against HEAD.
  * every delivered byte is re-verified twice: against the receipt's own hashes and against a fresh
    recomposition from the materials commit, so a receipt that agrees with tampered files is still
    refused.
  * report and telemetry must both exist and carry content. A missing or empty one makes the run
    INVALID; a reason string is recorded instead of an invented log line.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from wrapper_delivery import H2_REL, ROOT, delivery, git, sha256

DELIVERED_FILES = ("AGENTS.md", "H2_RULES.md")
DELIVERED_DIR = "H2_WARM"
RECEIPT_HASH_KEYS = {"AGENTS.md": "carrier_sha256", "H2_RULES.md": "rules_sha256"}
ARTIFACTS = (("report.md", "MISSING_REPORT", "EMPTY_REPORT"),
             (".h2-telemetry.log", "MISSING_TELEMETRY", "EMPTY_TELEMETRY"))
DIFF_CAP = 4 * 1024 * 1024


def registry(root: Path = ROOT) -> dict:
    return json.loads((root / H2_REL / "freeze-v2/task-registry-v2.json").read_text())


def task_of(registry_data: dict, task_id: str) -> dict | None:
    return next((t for t in registry_data["tasks"] if t["task_id"] == task_id), None)


def raw(root: Path, *args: str) -> bytes:
    result = git(root, *args, binary=True)
    return result if isinstance(result, bytes) else result.encode()


def parse_name_status(data: bytes) -> list[dict]:
    """`git diff --name-status -z -M` -> [{status, path, old_path?}]."""
    fields = [part.decode("utf-8") for part in data.split(b"\0") if part]
    changes, index = [], 0
    while index < len(fields):
        status = fields[index]
        index += 1
        if status[:1] in ("R", "C"):
            changes.append({"status": status, "old_path": fields[index],
                            "path": fields[index + 1]})
            index += 2
        else:
            changes.append({"status": status, "path": fields[index]})
            index += 1
    return changes


def worker_changes(repo: Path, base: str) -> list[dict]:
    """Every path that differs between the frozen base and the worker's tree, plus untracked and
    ignored files (a worker could hide a write behind .gitignore)."""
    changes = parse_name_status(raw(repo, "diff", "--name-status", "-z", "-M", base, "--"))
    seen = {change["path"] for change in changes}
    for args in (("ls-files", "-z", "--others", "--exclude-standard"),
                 ("ls-files", "-z", "--others", "-i", "--exclude-standard")):
        for entry in raw(repo, *args).split(b"\0"):
            path = entry.decode("utf-8")
            if path and path not in seen:
                changes.append({"status": "A", "path": path})
                seen.add(path)
    return changes


def verify_delivery(root: Path, run_dir: Path) -> tuple[dict, dict[str, str], list[str]]:
    """Re-verify the delivered bytes; returns (receipt, delivered hashes, reasons)."""
    reasons: list[str] = []
    receipt_path = run_dir / "receipt.json"
    if not receipt_path.is_file():
        return {}, {}, ["MISSING_RECEIPT"]
    try:
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}, {}, ["UNREADABLE_RECEIPT"]
    if not isinstance(receipt, dict) or not {"task_id", "arm", "base_sha", "materials_commit",
                                             "carrier_sha256", "rules_sha256",
                                             "warm_bundle_sha256", "program_sha256"} <= set(receipt):
        return {}, {}, ["INCOMPLETE_RECEIPT"]
    hashes: dict[str, str] = {}
    for name in DELIVERED_FILES:
        path = run_dir / name
        if not path.is_file():
            reasons.append(f"MISSING_DELIVERED_FILE:{name}")
            continue
        hashes[name] = sha256(path.read_bytes())
        if hashes[name] != receipt.get(RECEIPT_HASH_KEYS[name]):
            reasons.append(f"DELIVERED_HASH_MISMATCH:{name}")
    warm_root = run_dir / DELIVERED_DIR
    warm_files = ([path for path in sorted(warm_root.rglob("*")) if path.is_file()]
                  if warm_root.is_dir() else [])
    if not warm_files:
        reasons.append(f"MISSING_DELIVERED_DIR:{DELIVERED_DIR}")
    warm_lines = []
    for path in warm_files:
        rel = path.relative_to(warm_root).as_posix()
        hashes[f"{DELIVERED_DIR}/{rel}"] = sha256(path.read_bytes())
        warm_lines.append(f"{rel} {hashes[f'{DELIVERED_DIR}/{rel}']}")
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
        path = run_dir / rel
        if not path.is_file():
            reasons.append(f"MISSING_DELIVERED_FILE:{rel}")
        elif path.read_bytes() != data:
            reasons.append(f"DELIVERED_BYTES_NOT_FROM_MATERIALS:{rel}")
    for rel in hashes:
        if rel not in expected:
            reasons.append(f"UNDELIVERED_EXTRA_FILE:{rel}")
    return receipt, hashes, sorted(set(reasons))


def artifact(run_dir: Path, name: str, missing: str, empty: str) -> tuple[dict, list[str]]:
    path = run_dir / name
    if not path.is_file():
        return {"present": False}, [missing]
    data = path.read_bytes()
    record = {"present": True, "bytes": len(data), "lines": data.count(b"\n"),
              "sha256": sha256(data)}
    if not data.strip():
        return record, [empty]
    return record, []


def collect(root: Path = ROOT, run_dir: Path | None = None) -> dict:
    root, run_dir = Path(root).resolve(), Path(run_dir).resolve()
    registry_data = registry(root)
    receipt, delivered, reasons = verify_delivery(root, run_dir)
    repo = run_dir / "repo"
    task = task_of(registry_data, str(receipt.get("task_id")))
    if receipt and task is None:
        reasons.append("UNKNOWN_TASK")
    if receipt and task is not None and receipt.get("base_sha") != task["base_sha"]:
        reasons.append("BASE_DOES_NOT_MATCH_REGISTRY")
    base = str(receipt.get("base_sha", ""))
    changes: list[dict] = []
    diff = b""
    if not repo.is_dir():
        reasons.append("MISSING_TASK_REPOSITORY")
    elif not base:
        reasons.append("MISSING_BASE_SHA")
    else:
        try:
            if git(repo, "rev-parse", "--show-toplevel").strip() != str(repo):
                reasons.append("TASK_REPOSITORY_NOT_THE_ROOT")
            # F8 / T21: the task repository is standalone and history-free; a worker that reaches
            # another repository through a remote or an alternates link has escaped its tree.
            if git(repo, "remote").strip():
                reasons.append("TASK_REPOSITORY_HAS_REMOTE")
            if (repo / ".git/objects/info/alternates").exists():
                reasons.append("TASK_REPOSITORY_HAS_ALTERNATES")
            if subprocess_ok(repo, "merge-base", "--is-ancestor", base, "HEAD"):
                changes = worker_changes(repo, base)
                diff = raw(repo, "diff", "--binary", base, "--")
            else:
                reasons.append("WORKER_HEAD_NOT_DESCENDANT_OF_BASE")
        except ValueError:
            reasons.append("TASK_REPOSITORY_UNREADABLE")
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
        "program": "freeze-v2/collect_v2.py",
        "run_id": (f"h2r2-{receipt['task_id']}-{str(receipt['arm'])[0]}"
                   if receipt.get("task_id") and receipt.get("arm") else None),
        "task_id": receipt.get("task_id"),
        "arm": receipt.get("arm"),
        "base_sha": base or None,
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


def subprocess_ok(root: Path, *args: str) -> bool:
    try:
        git(root, *args)
    except ValueError:
        return False
    return True


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
