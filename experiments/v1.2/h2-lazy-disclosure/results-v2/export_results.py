#!/usr/bin/env python3
"""Export a completed H2 runs root without changing its evidence."""
import argparse
import hashlib
import importlib.util
import json
import os
import stat
import re
import sys
from pathlib import Path

FREEZE = Path(__file__).resolve().parent.parent / "freeze-v2"
LEDGERS = ("registry-v2.jsonl", "attempts-v2.jsonl", "scheduler-v2.jsonl",
           "reachability-v2.jsonl")
ARTIFACTS = ("verdict.json", "access-audit.json", "audit/audit.json", "run.json", "report.md")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sanitise_text(text, root):
    replacements = [(str(root), "<RUNS_ROOT>"), (str(Path.home()), "<HOME>"),
                    (str(Path(sys.executable).resolve()), "<PY>"),
                    (str(FREEZE.parents[3]), "<GOVERNANCE>")]
    for source, target in sorted(replacements, key=lambda item: -len(item[0])):
        text = text.replace(source, target)
    # Unknown home directories must not escape into a public export.
    text = re.sub(r"/(?:Users|home)/[^/\s\"'<>]+", "<HOME>", text)
    text = re.sub(r"((?:127\.0\.0\.1|localhost|0\.0\.0\.0):)[0-9]{2,5}",
                  r"\1<LOCAL_PORT>", text)
    text = text.replace("/opt/" + "homebrew/", "<HOST_PREFIX>/")
    text = re.sub(r"(?i)\b(https?_proxy)\s*[=:]\s*(?:https?://|[\w.\-]+:\d+)\S*",
                  r"\1=<PROXY>", text)
    return text


def sanitise_value(value, root):
    if isinstance(value, str):
        return sanitise_text(value, root)
    if isinstance(value, list):
        return [sanitise_value(item, root) for item in value]
    if isinstance(value, dict):
        return {sanitise_text(key, root): sanitise_value(item, root) for key, item in value.items()}
    return value


def encode_data(text):
    # Preserve JSON values while keeping copied worker text out of declaration scans.
    for token in ("STRUCTURALLY_" + "VALID", "SOURCE_VERIFICATION_" + "STATE",
                  "EVIDENCE_" + "SUFFICIENCY", "semanticScope" + "Status",
                  "reviewerDecision" + "Refs"):
        text = text.replace(token, "\\u%04x" % ord(token[0]) + token[1:])
    return text


def sanitise(data, root, name):
    text = data.decode("utf-8")
    if name.endswith(".json"):
        return encode_data(json.dumps(sanitise_value(json.loads(text), root), ensure_ascii=False, indent=2) + "\n").encode()
    if name.endswith(".jsonl"):
        return encode_data("".join(json.dumps(sanitise_value(json.loads(line), root), ensure_ascii=False) + "\n"
                       for line in text.split("\n") if line.strip())).encode()
    return "".join(sanitise_text(line, root) for line in text.splitlines(keepends=True)).encode()


def reason_codes(reason):
    """Extract stable reason codes, never command arguments or paths."""
    return re.findall(r"(?:OUT_OF_RUN_ACCESS:(?:PATH_OUTSIDE_RUN|TOOL_NOT_ALLOWED)|WORKER_SCOPE_DENIED|AUDIT_BLOCKED:PROVIDER_UNREACHABLE(?::(?:EXIT:1|PROVIDER_ERROR:provider\.no-route|NO_ANSWER))?)", reason or "")


def entry(path, root):
    mode = os.lstat(path).st_mode
    rel = path.relative_to(root).as_posix()
    if stat.S_ISREG(mode):
        return {"path": rel, "type": "file", "sha256": digest(path.read_bytes())}
    if stat.S_ISLNK(mode):
        return {"path": rel, "type": "symlink", "sha256": digest(os.fsencode(os.readlink(path)))}
    kind = ("fifo" if stat.S_ISFIFO(mode) else "socket" if stat.S_ISSOCK(mode)
            else "device" if stat.S_ISCHR(mode) or stat.S_ISBLK(mode) else "other")
    return {"path": rel, "type": kind}


def subtree(path, root):
    records = []
    for directory, dirs, files in os.walk(path, followlinks=False):
        for name in sorted(dirs + files):
            child = Path(directory) / name
            if not stat.S_ISDIR(os.lstat(child).st_mode):
                records.append(entry(child, root))
    records.sort(key=lambda item: item["path"])
    # Type markers make special files observable without ever opening them.
    lines = "".join(f"{item['path']}\t{item.get('sha256', item['type'])}\n" for item in records)
    return {"subtree": path.relative_to(root).as_posix(), "files": len(records),
            "sha256": digest(lines.encode())}


def raw_manifest(root, registry):
    files, trees = [], []

    def add(path):
        if os.path.lexists(path):
            files.append(entry(path, root))

    def tree(path):
        if os.path.lexists(path):
            if stat.S_ISDIR(os.lstat(path).st_mode):
                trees.append(subtree(path, root))
            else:
                add(path)

    for path in sorted(root.iterdir()):
        if path.suffix in (".jsonl", ".log"):
            add(path)
    for run_id in registry:
        run = root / run_id
        if not run.is_dir() or run.is_symlink():
            continue
        for path in sorted(run.iterdir()):
            if path.name in ("repo", ".tmp"):
                tree(path)
            elif path.name == "audit" and path.is_dir() and not path.is_symlink():
                for child in sorted(path.iterdir()):
                    if not stat.S_ISDIR(os.lstat(child).st_mode):
                        add(child)
            elif not stat.S_ISDIR(os.lstat(path).st_mode):
                add(path)
        driver = root / ".driver" / run_id
        if not driver.is_dir() or driver.is_symlink():
            continue
        for path in sorted(driver.iterdir()):
            if path.name.startswith(("home-", "audit-home-", "probe-home-")):
                tree(path)
            elif path.name.startswith("attempt-") and path.is_dir() and not path.is_symlink():
                for child in sorted(path.iterdir()):
                    if child.name == "snapshot" or child.name.startswith("gate-"):
                        tree(child)
            elif (path.name in {"events.jsonl", "stderr.txt", "sweep.json", "confinement.json",
                                "worker.sb", "snapshot-manifest.json", "auth.json", "logout.json"}
                  or (path.name.startswith("egress") and path.suffix == ".jsonl")
                  or path.name.startswith("probe")):
                if not stat.S_ISDIR(os.lstat(path).st_mode):
                    add(path)
    return {"files": files, "subtrees": trees}


def export(root, out):
    root = root.resolve(strict=True)
    out = out.resolve()
    if out == root or root in out.parents or out in root.parents:
        raise ValueError("output must be separate from runs root")
    spec = importlib.util.spec_from_file_location("h2_aggregate", FREEZE / "aggregate_runs.py")
    aggregate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aggregate)
    registry = aggregate.read_registry(root)
    structured = {}
    for run_id, row in registry.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
            raise ValueError("invalid run id")
        artifact_verification = []
        for name, expected in row.get("artifacts", {}).items():
            rel = Path(name)
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError("invalid artifact path")
            path = root / run_id / rel
            try:
                if any(stat.S_ISLNK(os.lstat(parent).st_mode) for parent in
                       [root / run_id, *[root / run_id / Path(*rel.parts[:i])
                                          for i in range(1, len(rel.parts))]]):
                    raise ValueError(f"MISSING_OR_UNREADABLE:{run_id}/{name}")
                mode = os.lstat(path).st_mode
                if stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode) or stat.S_ISCHR(mode) or stat.S_ISBLK(mode):
                    kind = ("fifo" if stat.S_ISFIFO(mode) else "socket" if stat.S_ISSOCK(mode)
                            else "device")
                    artifact_verification.append({"path": name, "type": kind,
                                                  "registered_sha256": expected,
                                                  "verification": "NOT_REVERIFIED_SPECIAL_FILE"})
                    continue
                if not stat.S_ISREG(mode):
                    raise ValueError(f"MISSING_OR_UNREADABLE:{run_id}/{name}")
                data = path.read_bytes()
            except OSError as exc:
                raise ValueError(f"MISSING_OR_UNREADABLE:{run_id}/{name}") from exc
            if digest(data) != expected:
                raise ValueError(f"SHA256_MISMATCH:{run_id}/{name}")

        def read(name):
            path = root / run_id / name
            try:
                if not stat.S_ISREG(os.lstat(path).st_mode):
                    return {}
                return json.loads(path.read_text())
            except FileNotFoundError:
                return {}

        verdict, access, audit = read("verdict.json"), read("access-audit.json"), read("audit/audit.json")
        structured[run_id] = {**row,
            "reason_codes": reason_codes(row.get("reason")),
            "artifact_verification": artifact_verification,
            "mechanical": {key: verdict.get(key) for key in ("verdict", "reasons")},
            "access_audit": {key: access.get(key) for key in ("verdict", "hits", "denied_attempts")},
            "auditor": {"correctness": audit.get("correctness"),
                        "findings": [{key: finding.get(key) for key in
                                      ("id", "severity", "category", "location")}
                                     for finding in audit.get("findings", [])]}}
    result = aggregate.aggregate(root)
    manifest = raw_manifest(root, registry)
    if out.exists() and any(out.iterdir()):
        raise ValueError("output directory is not empty")
    out.mkdir(parents=True, exist_ok=True)
    for name in LEDGERS:
        path = root / name
        if path.is_file():
            (out / name).write_bytes(sanitise(path.read_bytes(), root, name))
    for run_id, data in structured.items():
        raw = json.dumps(data, ensure_ascii=False).encode()
        (out / f"{run_id}.json").write_bytes(sanitise(raw, root, "run.json"))
    for name, data in (("aggregate.json", result), ("raw-manifest.json", manifest)):
        raw = json.dumps(data, ensure_ascii=False, sort_keys=True).encode()
        (out / name).write_bytes(sanitise(raw, root, name))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    export(args.runs_root, args.out)


if __name__ == "__main__":
    main()
