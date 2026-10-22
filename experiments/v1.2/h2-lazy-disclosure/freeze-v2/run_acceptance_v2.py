#!/usr/bin/env python3
"""One verdict JSON per wrapper run — the executable per-run acceptance of protocol-v2 §5.

CODEX_FIXES_1 T11 / F2: §5 specified collection, the scope check, the oracle FAIL->PASS in BOTH
temp-root spellings and the full-suite comparison, but no program implemented it. This is that
program. It is fail-closed in one direction only: ACCEPT needs every check to be measured and to
pass, and everything unmeasured is recorded as such instead of being read as a success.

Order (each stage terminal):
  1. collect_v2.collect     the base->worker delta, report, telemetry, delivered bytes; an INVALID
                            collection cannot be accepted.
  2. scope                  T10 rules (scope_v2) + no delivered byte or wrapper artifact inside
                            repo/ + no path escaping repo/. A scope violation is not measured
                            around: nothing else in a run that already broke its contract can
                            rescue it.
  3. oracle identity        the oracle bytes must still hash to the registry base value.
  4. oracle transfer        base NOT passing and worker passing, in `acceptance_env("RESOLVED")`
                            and `acceptance_env("SYMLINKED")`, with an executed count > 0; skips,
                            expected failures, unexpected successes and unmeasured runs are never
                            a pass.
  5. full suite             `scripts/tests` in both spellings; a non-passing id beyond the T2 PRE
                            set for that task blocks. A SYMLINKED-only new failure is recorded and
                            blocks, never normalised onto the task baseline.

Exit code 0 only for ACCEPT. One run, one verdict JSON.
"""
from __future__ import annotations

import argparse
import json
import shlex
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

import collect_v2
import delivery_anchors
import scope_v2
from wrapper_delivery import H2_REL, ROOT, git, sha256

SPELLINGS = ("RESOLVED", "SYMLINKED")
DELIVERED_NAMES = ("AGENTS.md", "H2_RULES.md", "H2_WARM")
WRAPPER_ARTIFACTS = (".h2-telemetry.log", "receipt.json", "report.md", "contract.md",
                     "worker-report-template.md")


def registry(root: Path = ROOT) -> dict:
    return json.loads((root / H2_REL / "freeze-v2/task-registry-v2.json").read_text())


def pre_not_passing(root: Path, task: dict) -> list[str]:
    """T2's PRE measurement for this task (RESOLVED, zero worker edits) — the frozen baseline."""
    anchors = json.loads((root / H2_REL / "freeze-v2/delivery-anchors.json").read_text())
    row = next((r for r in anchors["rows"] if r["CASE_ID"] == task["case_id"]), None)
    if row is None:
        raise ValueError("TASK_NOT_MEASURED_BY_T2")
    return list(row["pre_delivery"]["full_suite"]["not_passing"])


def oracle_module(task: dict) -> str:
    return PurePosixPath(task["oracle"]["path"]).name


def registered_command(task: dict, interpreter: str) -> list[str]:
    return shlex.split(task["oracle"]["command"].replace("{PY}", interpreter))


def command_matches_surface(task: dict, interpreter: str) -> bool:
    return registered_command(task, interpreter) == [
        interpreter, "-m", "unittest", "discover", "-s", "scripts/tests", "-p", oracle_module(task)]


def owner_path(delivered_rel: str, receipt: dict) -> str | None:
    """The repo path a delivered file is a COPY of, if any.

    `H2_WARM/<dest>` mirrors repo `<dest>` and `H2_RULES.md` mirrors `RULES.md`, so the same bytes
    at that path are a REPAIR of the owner, not a copy of the delivery. The arm carrier is composite
    for the control arm (header + AGENTS.md + footer) and therefore has no owner; for the variant arm
    it is the frozen lean carrier file, which owns only its own path.
    """
    if delivered_rel == "H2_RULES.md":
        return "RULES.md"
    if delivered_rel.startswith("H2_WARM/"):
        return delivered_rel[len("H2_WARM/"):]
    if receipt.get("carrier_kind") == "variant_lean_v1":
        return f"{H2_REL}/carriers/H2_LEAN_BOOTSTRAP.md"
    return None


def scope_reasons(root: Path, task: dict, collected: dict) -> list[str]:
    """T10 rules, plus the wrapper-layout rules that only a wrapper run can violate."""
    reasons = set(scope_v2.check_scope(task, collected["changes"]))
    receipt = collected["receipt"]
    by_hash: dict[str, list[str]] = {}
    for rel, value in collected["delivered_hashes"].items():
        by_hash.setdefault(value, []).append(rel)
    repo = collected["_repo"].resolve()
    for change in collected["changes"]:
        path, status = change["path"], str(change.get("status", ""))
        if status[:1] == "D":
            continue                                    # nothing left in the tree to inspect
        candidate = collected["_repo"] / path
        if candidate.exists() and repo not in candidate.resolve().parents:
            reasons.add(f"WORKER_PATH_ESCAPE:{path}")   # a symlink or mount leaving repo/
            continue
        if not candidate.is_file():
            continue
        value = sha256(candidate.read_bytes())
        for rel in by_hash.get(value, []):
            if path != owner_path(rel, receipt):
                reasons.add(f"WORKER_DELIVERY_COPY_IN_REPO:{path}:{rel}")
        if status[:1] in ("A", "C", "R") and PurePosixPath(path).name in (
                *DELIVERED_NAMES, *WRAPPER_ARTIFACTS):
            reasons.add(f"WORKER_WRAPPER_ARTIFACT_IN_REPO:{path}")
        if status[:1] in ("A", "C", "R") and Path(path).parts[:1] == ("H2_WARM",):
            reasons.add(f"WORKER_DELIVERED_LAYOUT_IN_REPO:{path}")
    return sorted(reasons)


@contextmanager
def base_tree(root: Path, base: str):
    """A clean checkout of the frozen base, outside the worker's tree and outside repo/."""
    with tempfile.TemporaryDirectory(prefix="h2-accept-base-") as tmp:
        tree = Path(tmp) / "repo"
        git(root, "worktree", "add", "-q", "--detach", str(tree), base)
        try:
            yield tree
        finally:
            git(root, "worktree", "remove", "--force", str(tree))
            git(root, "worktree", "prune")


def oracle_passes(result: dict) -> bool:
    return (result["rc"] == 0 and (result["ran"] or 0) > 0 and not result["not_passing"]
            and not result["skipped"] and not result["expected_failures"]
            and not result["unexpected_successes"])


def gate(tree: Path, pattern: str | None, style: str) -> dict:
    return delivery_anchors.run_gate(tree, pattern, style=style)


def accept(root: Path = ROOT, run_dir: Path | None = None) -> dict:
    root, run_dir = Path(root).resolve(), Path(run_dir).resolve()
    verdict = {"schema_version": 1, "program": "freeze-v2/run_acceptance_v2.py",
               "run_dir": str(run_dir), "verdict": "REJECT", "reasons": [],
               "spellings": list(SPELLINGS)}
    collected = collect_v2.collect(root, run_dir)
    collected["_repo"] = run_dir / "repo"
    verdict.update({"run_id": collected["run_id"], "task_id": collected["task_id"],
                    "arm": collected["arm"], "base_sha": collected["base_sha"],
                    "materials_commit": collected["materials_commit"],
                    "collected": {key: collected[key] for key in
                                  ("status", "reasons", "changes", "diff_sha256", "artifacts")},
                    "collected_diff_sha256": collected["diff_sha256"]})
    if collected["status"] != "VALID":
        verdict["verdict"] = "INVALID"
        verdict["reasons"] = [f"COLLECTION_INVALID:{reason}" for reason in collected["reasons"]]
        return verdict
    task = collect_v2.task_of(registry(root), str(collected["task_id"]))
    if task is None:
        verdict["verdict"] = "INVALID"
        verdict["reasons"] = ["UNKNOWN_TASK"]
        return verdict
    verdict["case_id"] = task["case_id"]
    verdict["scope"] = {"changes": len(collected["changes"]),
                        "reasons": scope_reasons(root, task, collected)}
    if verdict["scope"]["reasons"]:
        verdict["reasons"] = verdict["scope"]["reasons"]
        return verdict
    worker_oracle = run_dir / "repo" / task["oracle"]["path"]
    worker_hash = sha256(worker_oracle.read_bytes()) if worker_oracle.is_file() else None
    verdict["oracle"] = {"path": task["oracle"]["path"], "module": oracle_module(task),
                         "base_blob_sha256": task["oracle"]["base_blob_sha256"],
                         "worker_blob_sha256": worker_hash}
    if not command_matches_surface(task, sys.executable):
        verdict["reasons"].append("ORACLE_COMMAND_DIFFERS_FROM_REGISTRY")
    if worker_hash != task["oracle"]["base_blob_sha256"]:
        verdict["reasons"].append("ORACLE_BYTES_CHANGED")
    if verdict["reasons"]:
        return verdict
    with base_tree(root, task["base_sha"]) as base:
        verdict["oracle"]["base"] = {}
        verdict["oracle"]["worker"] = {}
        for style in SPELLINGS:
            base_result = gate(base, oracle_module(task), style)
            worker_result = gate(run_dir / "repo", oracle_module(task), style)
            verdict["oracle"]["base"][style] = base_result
            verdict["oracle"]["worker"][style] = worker_result
            if oracle_passes(base_result):
                verdict["reasons"].append(f"BASE_NOT_FAILING:{style}")
            if not oracle_passes(worker_result):
                verdict["reasons"].append(f"WORKER_NOT_PASSING:{style}")
        if verdict["reasons"]:
            return verdict
    pre = set(pre_not_passing(root, task))
    verdict["full_suite"] = {"pre_not_passing": sorted(pre), "worker": {}}
    for style in SPELLINGS:
        result = gate(run_dir / "repo", None, style)
        newly = sorted(set(result["not_passing"]) - pre)
        verdict["full_suite"]["worker"][style] = result
        verdict["full_suite"][f"newly_not_passing_{style.lower()}"] = newly
        if not result["ran"]:
            verdict["reasons"].append(f"FULL_SUITE_UNMEASURED:{style}")
        if newly:
            verdict["reasons"].append(f"FULL_SUITE_NEW_NOT_PASSING:{style}:{','.join(newly)}")
    if not verdict["reasons"]:
        verdict["verdict"] = "ACCEPT"
    return verdict


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = accept(args.root, args.run_dir)
    target = args.out or args.run_dir / "verdict.json"
    target.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"run_id": result["run_id"], "verdict": result["verdict"],
                      "reasons": result["reasons"]}, sort_keys=True))
    return 0 if result["verdict"] == "ACCEPT" else 1


if __name__ == "__main__":
    raise SystemExit(main())
