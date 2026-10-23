#!/usr/bin/env python3
"""Build/check byte pins. Independent test literals additionally anchor this manifest itself."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from wrapper_delivery import H2_REL, ROOT, delivery, git, sha256

FROZEN_FILES = tuple(sorted(
    [f"{H2_REL}/freeze-v2/{name}" for name in (
        "wrapper_delivery.py", "delivery_anchors.py", "isolation_canary.py",
        "access_audit.py", "egress_v2.py",
        "build_registry.py", "task-registry-v2.json", "build_run_plan.py", "run-plan-v2.json",
        "worker-brief-v2.md", "render_brief.py", "protocol-v2.md", "aggregate_set.py",
        "run_h2r2.py", "run_audit_v2.py", "sandbox_v2.py", "aggregate_runs.py",
        "build_manifest.py", "delivery-anchors.json", "route_preconditions.py",
        "route-preconditions.json", "scope_v2.py", "collect_v2.py", "run_acceptance_v2.py",
        "worker-sandbox.sb.template",
        "fixtures/isolation-canary-events.jsonl",
        "fixtures/canary-86ac104-events.jsonl",
        "fixtures/canary-86ac104-synthetic-sources-line.jsonl",
        "fixtures/access-audit-clean.jsonl",
        "fixtures/access-audit-hits.jsonl",
        "fixtures/pilot-f01-c-events.jsonl",
        "fixtures/toolname-probe-events.jsonl",
        "fixtures/preflight-debug-paths.txt",
        "fixtures/preflight-debug-config.json",
        "worker-profile/opencode.json")]
    + [f"{H2_REL}/{name}" for name in (
        "routes-h2.json", "variant-manifest.json", "scoring-rubric.md",
        "carriers/H2_LEAN_BOOTSTRAP.md", "harness/check_task_class.py",
        "harness/control-carrier-header.md", "harness/control-carrier-footer.md",
        "harness/worker-report-template.md", "admission/freeze-v2-input/shortlist.json")]
    + [f"{H2_REL}/admission/batch-{index}/{name}.json"
       for index in range(1, 5) for name in ("ledger", "classification")]
))
MANIFEST_REL = f"{H2_REL}/freeze-v2/freeze-manifest.json"


def build(freeze_parent: str, root: Path = ROOT) -> dict:
    parent = git(root, "rev-parse", "--verify", f"{freeze_parent}^{{commit}}").strip()
    runs = json.loads((root / H2_REL / "freeze-v2/run-plan-v2.json").read_text())["runs"]
    if {r["materials_commit"] for r in runs} != {parent}:
        raise ValueError("REGENERATE_RUN_PLAN_AT_FREEZE_PARENT")
    measured = json.loads((root / H2_REL / "freeze-v2/delivery-anchors.json").read_text())
    anchor_commit = measured["materials_commit"]
    for arm in ("control", "variant"):
        if delivery(root, anchor_commit, arm) != delivery(root, parent, arm):
            raise ValueError("DELIVERY_PAYLOAD_CHANGED_SINCE_T2")
    # The payload equality above is what delivery neutrality depends on. The anchors also record
    # the exact measuring program and shortlist, by hash: comparing a commit's bytes with the
    # current program would forbid the very commit that changes the program (F8 / T21), while the
    # recorded hash states the real invariant — this measurement was produced by this program.
    if measured.get("wrapper_program_sha256") != sha256(
            (root / H2_REL / "freeze-v2/wrapper_delivery.py").read_bytes()):
        raise ValueError("DELIVERY_PROGRAM_CHANGED_SINCE_MEASUREMENT")
    if measured.get("shortlist_sha256") != sha256(
            (root / H2_REL / "admission/freeze-v2-input/shortlist.json").read_bytes()):
        raise ValueError("DELIVERY_SHORTLIST_CHANGED_SINCE_MEASUREMENT")
    return {"schema_version": 2, "freeze_parent": parent, "materials_commit": parent,
            "delivery_anchor_materials_commit": anchor_commit,
            "hashes": {rel: sha256((root / rel).read_bytes()) for rel in FROZEN_FILES}}


def verify(root: Path = ROOT) -> list[str]:
    try:
        manifest = json.loads((root / MANIFEST_REL).read_text())
        if set(manifest["hashes"]) != set(FROZEN_FILES):
            return ["FROZEN_MEMBERSHIP_MISMATCH"]
        failures = []
        for rel, expected in manifest["hashes"].items():
            path = root / rel
            if path.is_symlink() or not path.is_file() or sha256(path.read_bytes()) != expected:
                failures.append(rel)
        runs = json.loads((root / H2_REL / "freeze-v2/run-plan-v2.json").read_text())["runs"]
        if (manifest["freeze_parent"] != manifest["materials_commit"]
                or {r["materials_commit"] for r in runs} != {manifest["materials_commit"]}):
            failures.append("MATERIALS_BINDING_MISMATCH")
        return failures
    except (OSError, ValueError, KeyError, TypeError):
        return ["FROZEN_DATA_UNREADABLE"]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("build")
    make.add_argument("--freeze-parent", required=True)
    make.add_argument("--out", required=True, type=Path)
    commands.add_parser("check")
    args = parser.parse_args()
    if args.command == "build":
        args.out.write_text(json.dumps(build(args.freeze_parent), indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
        print(f"FREEZE_MANIFEST files={len(FROZEN_FILES)} delivery_payload_equivalent_to_T2=YES")
        return 0
    failures = verify()
    print(json.dumps({"verdict": "FAIL" if failures else "PASS", "mismatches": failures}))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
