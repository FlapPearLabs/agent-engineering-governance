#!/usr/bin/env python3
"""Export a completed H2 runs root without changing its evidence."""
import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

FREEZE = Path(__file__).resolve().parent.parent / "freeze-v2"
LEDGERS = ("registry-v2.jsonl", "attempts-v2.jsonl", "scheduler-v2.jsonl",
           "reachability-v2.jsonl")
ARTIFACTS = ("verdict.json", "access-audit.json", "audit/audit.json", "run.json", "report.md")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sanitise(data, root):
    text = data.decode("utf-8")
    replacements = [(str(root), "<RUNS_ROOT>"), (str(Path.home()), "<HOME>"),
                    (str(Path(sys.executable).resolve()), "<PY>"),
                    (str(FREEZE.parents[3]), "<GOVERNANCE>")]
    for source, target in sorted(replacements, key=lambda item: -len(item[0])):
        text = text.replace(source, target)
    # Unknown home directories must not escape into a public export.
    text = re.sub(r"/(?:Users|home)/[^/\s\"'<>]+", "<HOME>", text)
    text = re.sub(r"(?<![A-Za-z0-9:./-])/[A-Za-z0-9_.~-]+(?:/[^\s\"\'<>`,;|)]*)?", "<LOCAL_PATH>", text)
    return text.encode("utf-8")


def export(root, out):
    root = root.resolve(strict=True)
    out = out.resolve()
    if out == root or root in out.parents or out in root.parents:
        raise ValueError("output must be separate from runs root")
    spec = importlib.util.spec_from_file_location("h2_aggregate", FREEZE / "aggregate_runs.py")
    aggregate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(aggregate)
    registry = aggregate.read_registry(root)
    sources = {}
    for name in LEDGERS:
        path = root / name
        if path.exists():
            sources[name] = path.read_bytes()
    for run_id, row in registry.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+", run_id):
            raise ValueError("invalid run id")
        for name in ARTIFACTS:
            path = root / run_id / name
            recorded = row.get("artifacts", {}).get(name)
            if path.is_file():
                data = path.read_bytes()
                if recorded is not None and digest(data) != recorded:
                    raise ValueError(f"SHA256_MISMATCH:{run_id}/{name}")
                sources[f"{run_id}/{name}"] = data
            elif recorded is not None:
                raise ValueError(f"MISSING_OR_UNREADABLE:{run_id}/{name}")
    protocol = (FREEZE / "protocol-v2.md").read_bytes()
    sources["protocol-v2.md"] = protocol
    result = aggregate.aggregate(root)
    if out.exists() and any(out.iterdir()):
        raise ValueError("output directory is not empty")
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, data in sources.items():
        exported = sanitise(data, root)
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(exported)
        manifest[name] = {"original_sha256": digest(data), "exported_sha256": digest(exported)}
    raw = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    clean_aggregate = sanitise(raw, root)
    (out / "aggregate.json").write_bytes(clean_aggregate)
    manifest["aggregate.json"] = {"original_sha256": digest(raw),
                                  "exported_sha256": digest(clean_aggregate)}
    (out / "hashes.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs_root", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    export(args.runs_root, args.out)


if __name__ == "__main__":
    main()
