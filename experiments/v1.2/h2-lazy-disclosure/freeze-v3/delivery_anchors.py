#!/usr/bin/env python3
"""Delivery anchors for the Freeze v2 shortlist (schema §6.4, FZ-ADM-3) — measured BEFORE freezing.

For every shortlisted base and every (slot, arm) delivery, with ZERO worker edits:

    PRE   = the bare base checkout
    POST  = the same checkout with that arm's delivery in place (bytes composed exactly as
            harness/prepare_run.sh composes them, read from the MATERIALS commit's objects)

and for each gate (the task's oracle file; the full scripts/tests suite) records the set of test
ids that do NOT pass. prepare_run.sh compares exit codes, which cannot see RED -> MORE RED (round
1's t01: 1 failure -> 4 under delivery alone), and every A_REPAIR oracle is RED at its base. So:

    DELIVERY_CONTAMINATION = a test id that passes PRE and does not pass POST (any gate, any arm)
                             -> the task is BASE_CANDIDATE_NOT_COMPARABLE for that slot (§6.4)
    DELIVERY_REPAIR        = a test id that fails PRE and passes POST (delivery alone did work
                             the worker is supposed to do) -> equally blocking

Two slot designs are measured because the worker runtime decides which one is real:
    CODEBUDDY  the protocol's slot: CODEBUDDY.md + H2_RULES.md + H2_WARM/ added; tree untouched
    AGENTS     a runtime that auto-loads AGENTS.md (opencode): the carrier REPLACES AGENTS.md,
               H2_RULES.md + H2_WARM/ added
    WRAPPER    README §3: delivery outside repo/, with an untouched task worktree inside it

Every run uses check_task_class.acceptance_env("RESOLVED") — the validator's own environment.

Usage:  delivery_anchors.py <repo_root> <shortlist.json> --materials <commit> --out <json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
H2 = HERE.parent
sys.path.insert(0, str(H2 / "harness"))
sys.path.insert(0, str(HERE))

import check_task_class as ctc  # noqa: E402
import wrapper_delivery as wrapper  # noqa: E402

NOT_PASSING_RE = re.compile(r"^(?:FAIL|ERROR): \S+ \(([^)]+)\)", re.M)
# a skip is not a pass: a PRE-passing test SKIPPED after delivery is contamination too (review of
# 5090f44, finding 3). -v prints "name (id) ... skipped", or the docstring line in between
SKIPPED_RE = re.compile(r"^\S+ \(([^)]+)\)(?:\n[^\n]*?)? \.\.\. skipped", re.M)
EXPECTED_FAILURE_RE = re.compile(
    r"^\S+ \(([^)]+)\)(?:\n[^\n]*?)? \.\.\. expected failure", re.M)
UNEXPECTED_SUCCESS_RE = re.compile(
    r"^\S+ \(([^)]+)\)(?:\n[^\n]*?)? \.\.\. unexpected success", re.M)
RAN_RE = re.compile(r"^Ran (\d+) tests? in", re.M)
TIMEOUT = 1800


def git(root: Path, *args: str, binary: bool = False):
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=not binary)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args[:3])}: {r.stderr if not binary else r.stderr.decode()}")
    return r.stdout


def delivery(root: Path, materials: str, arm: str) -> dict[str, bytes]:
    """The bytes prepare_run.sh places for `arm`, keyed by the delivered relative path
    (the guidance carrier under the key "<CARRIER>")."""
    if arm == "variant":
        carrier = (H2 / "carriers" / "H2_LEAN_BOOTSTRAP.md").read_bytes()
        want = json.loads((H2 / "variant-manifest.json").read_text(encoding="utf-8"))
        if hashlib.sha256(carrier).hexdigest() != want["freeze"]["VARIANT_HASH"]:
            raise SystemExit("CARRIER_HASH_MISMATCH")
    else:
        carrier = ((H2 / "harness" / "control-carrier-header.md").read_bytes()
                   + git(root, "show", f"{materials}:AGENTS.md", binary=True)
                   + (H2 / "harness" / "control-carrier-footer.md").read_bytes())
    out = {"<CARRIER>": carrier,
           "H2_RULES.md": git(root, "show", f"{materials}:RULES.md", binary=True)}
    routes = json.loads((H2 / "routes-h2.json").read_text(encoding="utf-8"))["routes"]
    for dest in sorted({r["destination"] for r in routes if r.get("surface") == "S3"}):
        out[f"H2_WARM/{dest}"] = git(root, "show", f"{materials}:{dest}", binary=True)
    return out


def run_gate(wt: Path, pattern: str | None, style: str = "RESOLVED", *, gate=None) -> dict:
    """Run one gate in the validator's own environment (RESOLVED unless a caller asks for the
    SYMLINKED temp-root spelling) and read the per-test statuses back out of -v output.

    F32 / T38a: a caller that passes a `sandbox_v2.Gate` executes worktree code that a WORKER wrote,
    so the command runs inside that gate's rendered `sandbox-exec` profile with no network at all,
    in the gate's own copy and with its temp roots inside the copy. There is no unconfined fallback
    on that path: the caller either holds a gate or does not execute worker code.
    """
    cmd = [sys.executable, "-s", "-m", "unittest", "discover", "-s", "scripts/tests", "-v"]
    if pattern:
        cmd += ["-p", pattern]
    if gate is None:
        with ctc.acceptance_env(style) as env:
            r = subprocess.run(cmd, cwd=str(wt), env=env, capture_output=True, text=True,
                               timeout=TIMEOUT)
    else:
        r = subprocess.run(gate.argv(cmd), cwd=str(wt), env=gate.env(style),
                           capture_output=True, text=True, timeout=TIMEOUT)
    out = r.stdout + r.stderr
    ran = RAN_RE.findall(out)
    skipped = set(SKIPPED_RE.findall(out))
    expected = set(EXPECTED_FAILURE_RE.findall(out))
    unexpected = set(UNEXPECTED_SUCCESS_RE.findall(out))
    return {"rc": r.returncode, "ran": int(ran[-1]) if ran else None, "skipped": sorted(skipped),
            "expected_failures": sorted(expected), "unexpected_successes": sorted(unexpected),
            "not_passing": sorted(set(NOT_PASSING_RE.findall(out)) | skipped | expected | unexpected),
            "confined": gate is not None, "style": style,
            "gate": str(gate.root) if gate is not None else None}


def reset(wt: Path, rev: str = "HEAD") -> None:
    git(wt, "reset", "-q", "--hard", rev)
    git(wt, "clean", "-q", "-ffdx")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("repo_root")
    ap.add_argument("shortlist")
    ap.add_argument("--materials", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv[1:])
    root = Path(a.repo_root).resolve()
    if git(root, "rev-parse", "--show-toplevel").strip() != str(root):
        raise SystemExit("repo_root must be the repository root (run from it with '.')")
    materials = git(root, "rev-parse", "--verify", f"{a.materials}^{{commit}}").strip()
    deliveries = {arm: delivery(root, materials, arm) for arm in ("control", "variant")}
    rows = []
    scratch = Path(tempfile.mkdtemp(prefix="h2-anchors-"))
    try:
        for index, t in enumerate(json.loads(Path(a.shortlist).read_text(encoding="utf-8"))
                                  ["shortlist"], 1):
            base, oracle = t["BASE_SHA"], Path(t["ORACLE"]["path"]).name
            wt = scratch / t["CASE_ID"][:3]
            # PRE is the SAME repository shape the worker gets (F8 / T21): a standalone,
            # history-free checkout of the base. A measurement that compared a full-history
            # worktree with a history-free worker tree would report the shape as task failure.
            wrapper.standalone_repository(root, wt, base)
            try:
                gates = {"oracle": oracle, "full_suite": None}
                reset(wt)
                pre = {g: run_gate(wt, p) for g, p in gates.items()}
                post: dict[str, dict] = {}
                for slot in ("CODEBUDDY", "AGENTS", "WRAPPER"):
                    for arm, files in deliveries.items():
                        reset(wt)
                        if slot == "WRAPPER":
                            run_dir = scratch / f"wrapper-{index}-{arm}"
                            try:
                                wrapper.prepare(root, run_dir, f"f{index:02d}", arm, materials)
                                res = {g: run_gate(run_dir / "repo", p) for g, p in gates.items()}
                            finally:
                                if run_dir.exists():
                                    wrapper.cleanup(root, run_dir)
                        else:
                            for rel, data in files.items():
                                rel = ({"CODEBUDDY": "CODEBUDDY.md", "AGENTS": "AGENTS.md"}[slot]
                                       if rel == "<CARRIER>" else rel)
                                (wt / rel).parent.mkdir(parents=True, exist_ok=True)
                                (wt / rel).write_bytes(data)
                            res = {g: run_gate(wt, p) for g, p in gates.items()}
                        for g in gates:
                            before, after = set(pre[g]["not_passing"]), set(res[g]["not_passing"])
                            res[g]["newly_not_passing"] = sorted(after - before)
                            res[g]["newly_passing"] = sorted(before - after)
                            res[g]["ran_delta"] = ((res[g]["ran"] or 0) - (pre[g]["ran"] or 0))
                        post[f"{slot}/{arm}"] = res
                reset(wt)
            finally:
                shutil.rmtree(wt, ignore_errors=True)
            verdict = {}
            for key, res in post.items():
                contaminated = any(res[g]["newly_not_passing"] or res[g]["ran_delta"] < 0
                                   for g in res)
                repaired = any(res[g]["newly_passing"] for g in res)
                if key.startswith("WRAPPER/"):
                    contaminated = contaminated or any(
                        res[g]["ran_delta"] != 0 or not res[g]["ran"]
                        or res[g]["rc"] != pre[g]["rc"] for g in res)
                verdict[key] = ("DELIVERY_CONTAMINATION" if contaminated else
                                "DELIVERY_REPAIR" if repaired else "DELIVERY_NEUTRAL")
            per_slot = {slot: ("NEUTRAL" if all(verdict[f"{slot}/{arm}"] == "DELIVERY_NEUTRAL"
                                                for arm in deliveries) else "BLOCKED")
                        for slot in ("CODEBUDDY", "AGENTS", "WRAPPER")}
            rows.append({"CASE_ID": t["CASE_ID"], "BASE_SHA": base, "ORACLE": t["ORACLE"]["path"],
                         "pre_delivery": pre, "post_delivery": post, "verdict": verdict,
                         "SLOT_ADMISSIBLE": per_slot})
            print(f"  {t['CASE_ID'][:44]:44s} pre oracle={len(pre['oracle']['not_passing'])} "
                  f"suite={len(pre['full_suite']['not_passing'])}/{pre['full_suite']['ran']} "
                  f"{verdict}", flush=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    summary = {slot: sum(r["SLOT_ADMISSIBLE"][slot] == "NEUTRAL" for r in rows)
               for slot in ("CODEBUDDY", "AGENTS", "WRAPPER")}
    Path(a.out).write_text(json.dumps({"program": "freeze-v3/delivery_anchors.py",
                                       "materials_commit": materials,
                                       "repository": "standalone_history_free",
                                       "wrapper_program_sha256": hashlib.sha256(
                                           (HERE / "wrapper_delivery.py").read_bytes()).hexdigest(),
                                       "shortlist_sha256": hashlib.sha256(
                                           Path(a.shortlist).read_bytes()).hexdigest(),
                                       "environment": "check_task_class.acceptance_env(RESOLVED)",
                                       "neutral_tasks_per_slot": summary, "rows": rows},
                                      indent=1) + "\n", encoding="utf-8")
    print("DELIVERY_ANCHORS neutral per slot:", json.dumps(summary))
    return 0 if summary["WRAPPER"] == len(rows) == 10 else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
