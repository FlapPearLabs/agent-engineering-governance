#!/usr/bin/env python3
"""The runs-root aggregate (T30 / F20 P3-4): valid pairs and the protocol-v2 §7 result token.

`run_h2r2.py status` used to say "registered=20" and nothing about whether those twenty runs
could support a result. This program reads ONE runs root — `registry-v2.jsonl`,
`attempts-v2.jsonl` and each run's own verdict files — and prints, per arm and per task:

  * the VALID PAIRS (`final_verdict` ACCEPT or REJECT, with a readable audited verdict file),
  * the INVALID and BLOCKED runs with the reason the driver registered,
  * the attempt ledger of every run, so a retried run keeps its history,
  * the OVERLAP PAIRS of registered runs (T34: two runs of different tasks execute at once),
  * the protocol-v2 §7 result token and the EXACT rule that decided it.

WHAT IT DOES NOT DECIDE. The audited finding identity, correctness and invalid-completion flag
are not inferred here: they are read verbatim from `<run_id>/audit/audit.json`, which the blind
auditor writes. A run whose audit file is missing, unreadable or malformed cannot be part of a
pair, so the result is INSUFFICIENT_EVIDENCE naming that run. S1 is a pre-registered DESIGN fact
of the frozen carriers and is read from `variant-manifest.json` (hash-pinned), not re-judged from
the runs. S5's M6 disposition (rubric §5) is a judgement; the token below is therefore the
runs-root mechanical result and is reported with `pending_rules`, never as a substitute for the
closure report.

The decision order is the pre-registered §7 order, and the first rule that fires is the one named
in `decided_by`:

  1. COVERAGE            a task/arm has no usable run (missing, INVALID or BLOCKED) -> INSUFFICIENT
  2. AUDIT_EVIDENCE      a usable run has no readable audited verdict file        -> INSUFFICIENT
  3. S1                  the frozen carrier reduction or full delivery is not met -> INSUFFICIENT
  4. S2                  an audited finding is a missed guidance observation      -> HAS_COST
  5. S3                  variant invalid-completion count > control's            -> HAS_COST
  6. S4                  variant correctness multiset worse, position by position -> HAS_COST
  7. NULL_DIFFERENCE     every pair identical in correctness, invalid completion and finding
                         identity -> INSUFFICIENT (protocol-v2 §7 null rule)
  8. otherwise                                                            -> DISCLOSURE_SAFE
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN_NAME = "run-plan-v2.json"
REGISTRY_NAME = "registry-v2.jsonl"
ATTEMPT_REGISTRY_NAME = "attempts-v2.jsonl"
VERDICT_NAME = "verdict.json"
AUDIT_NAME = Path("audit") / "audit.json"
ARMS = ("control", "variant")
# A run is usable only when the mechanical verdict and the audit both produced a judgement.
USABLE = ("ACCEPT", "REJECT")
CORRECTNESS_ORDER = {"PASS": 0, "PARTIAL": 1, "FAIL": 2, "BLOCKED": 3}
# A finding is a missed guidance observation only when the AUDITOR labelled it so (rubric §3);
# this program never re-labels a finding of its own accord.
MISSED_GUIDANCE_CATEGORY = "MISSED_GUIDANCE"
S1_MIN_REDUCTION_PERCENT = 30.0


def read_jsonl(path: Path) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"{path.name.upper()}_MALFORMED_LINE:{number}") from exc
        if not isinstance(row, dict) or not isinstance(row.get("run_id"), str):
            raise ValueError(f"{path.name.upper()}_MALFORMED_LINE:{number}")
        rows.append(row)
    return rows


def read_registry(runs_root: Path) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for row in read_jsonl(Path(runs_root) / REGISTRY_NAME):
        if row["run_id"] in entries:
            raise ValueError(f"REGISTRY_DUPLICATE_RUN_ID:{row['run_id']}")
        entries[row["run_id"]] = row
    return entries


def planned_runs() -> list[dict]:
    return json.loads((HERE / PLAN_NAME).read_text(encoding="utf-8"))["runs"]


def usable(entry: dict | None) -> bool:
    """A run that reached a judgement: the mechanical verdict and the audit are both present."""
    return bool(entry) and entry.get("final_verdict") in USABLE


def read_audited(run_dir: Path) -> dict | None:
    """The auditor's own verdict file, verbatim; None when it cannot support a verdict."""
    path = Path(run_dir) / AUDIT_NAME
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if (not isinstance(data, dict) or data.get("correctness") not in CORRECTNESS_ORDER
            or not isinstance(data.get("invalid_completion"), bool)
            or not isinstance(data.get("findings"), list)):
        return None
    if any(not isinstance(finding, dict) for finding in data["findings"]):
        return None
    return data


def finding_identity(findings: list[dict]) -> tuple[tuple[str, str, str], ...]:
    """A finding's identity as the auditor recorded it: id, category and location."""
    return tuple(sorted((str(item.get("id")), str(item.get("category")),
                         str(item.get("location"))) for item in findings))


def missed_guidance(findings: list[dict]) -> list[str]:
    """Findings the AUDITOR recorded as missed guidance (rubric §2–§3 attribution)."""
    return [str(item.get("id")) for item in findings
            if item.get("category") == MISSED_GUIDANCE_CATEGORY
            or item.get("missed_guidance") is True]


def overlap_pairs(registry: dict[str, dict]) -> list[list[str]]:
    """Registered runs whose execution intervals overlapped (T34 item 6).

    Derived from the registry's own start/finish timestamps, so it needs nothing the driver did
    not already write and cannot disagree with `status` or a per-run `concurrent_with`.
    """
    spans = []
    for run_id, entry in registry.items():
        start, end = entry.get("started_at"), entry.get("finished_at")
        if isinstance(start, str) and isinstance(end, str):
            spans.append((run_id, start, end))
    pairs = []
    for index, (run_id, start, end) in enumerate(spans):
        for other_id, other_start, other_end in spans[index + 1:]:
            if start < other_end and other_start < end:
                pairs.append(sorted([run_id, other_id]))
    return sorted(pairs)


def s1_design_condition() -> dict:
    """S1: the carrier-face reduction is a frozen, pre-registered design fact (rubric §9)."""
    manifest = json.loads((HERE.parent / "variant-manifest.json").read_text(encoding="utf-8"))
    observed = manifest["hot_metrics"]["observed_at_freeze_at_H2_base"]
    control = int(observed["CONTROL_CARRIER_JS_CHARS"])
    variant = int(observed["VARIANT_CARRIER_JS_CHARS"])
    reduction = round(100 * (control - variant) / control, 1)
    return {"control_carrier_js_chars": control, "variant_carrier_js_chars": variant,
            "reduction_percent": reduction,
            "variant_fully_delivered": bool(observed["VARIANT_FULLY_DELIVERED"]),
            "satisfied": (reduction >= S1_MIN_REDUCTION_PERCENT
                          and bool(observed["VARIANT_FULLY_DELIVERED"]))}


def aggregate(runs_root: Path) -> dict:
    runs_root = Path(runs_root)
    registry = read_registry(runs_root)
    attempts: dict[str, list[dict]] = {}
    for row in read_jsonl(runs_root / ATTEMPT_REGISTRY_NAME):
        attempts.setdefault(row["run_id"], []).append(row)
    invalid: list[dict] = []
    blocked: list[dict] = []
    missing: list[dict] = []
    audit_missing: list[str] = []
    pairs: list[dict] = []
    rows: list[dict] = []
    for plan_run in planned_runs():
        run_id = plan_run["run_id"]
        entry = registry.get(run_id)
        row = {"run_id": run_id, "task_id": plan_run["task_id"], "arm": plan_run["arm"],
               "state": "MISSING", "final_verdict": None, "reason": None}
        if entry is None:
            missing.append({"run_id": run_id, "task_id": plan_run["task_id"],
                            "arm": plan_run["arm"], "reason": "NOT_REGISTERED"})
        else:
            row.update({"state": entry.get("final_verdict"), "verdict": entry.get("verdict"),
                        "audit_verdict": entry.get("audit_verdict"),
                        "final_verdict": entry.get("final_verdict"),
                        "reason": entry.get("reason"),
                        "attempts": [{"attempt": item.get("attempt"), "kind": item.get("kind"),
                                      "verdict": item.get("verdict"),
                                      "reason": item.get("reason")}
                                     for item in attempts.get(run_id, [])]})
            if usable(entry):
                audited = read_audited(runs_root / run_id)
                if audited is None:
                    audit_missing.append(run_id)
                    row["state"] = "AUDIT_MISSING"
                else:
                    row.update({"correctness": audited["correctness"],
                                "invalid_completion": audited["invalid_completion"],
                                "findings": [str(item.get("id")) for item in audited["findings"]],
                                "identities": [list(item) for item in
                                               finding_identity(audited["findings"])],
                                "missed_guidance": missed_guidance(audited["findings"])})
            elif entry.get("final_verdict") == "BLOCKED":
                blocked.append({"run_id": run_id, "task_id": plan_run["task_id"],
                                "arm": plan_run["arm"], "reason": entry.get("reason")})
            else:
                invalid.append({"run_id": run_id, "task_id": plan_run["task_id"],
                                "arm": plan_run["arm"], "reason": entry.get("reason")})
        rows.append(row)
    by_run = {row["run_id"]: row for row in rows}
    task_ids = list(dict.fromkeys(plan_run["task_id"] for plan_run in planned_runs()))
    unexpected = sorted(set(registry) - set(by_run))
    for task_id in task_ids:
        arms = {plan_run["arm"]: plan_run["run_id"] for plan_run in planned_runs()
                if plan_run["task_id"] == task_id}
        pair = {"task_id": task_id,
                "control": by_run.get(arms.get("control")),
                "variant": by_run.get(arms.get("variant"))}
        pair["valid"] = all(pair[arm] is not None and pair[arm]["state"] != "MISSING"
                            and pair[arm]["state"] not in ("INVALID", "BLOCKED", "AUDIT_MISSING")
                            for arm in ARMS)
        pairs.append(pair)
    usable_pairs = sum(1 for pair in pairs if pair["valid"])
    result = {"schema_version": 1, "program": "freeze-v2/aggregate_runs.py",
              "runs_root": str(runs_root), "planned_pairs": len(pairs),
              "usable_pairs": usable_pairs, "tasks": len(task_ids),
              "rows": rows, "pairs": pairs,
              "invalid": invalid, "blocked": blocked, "missing": missing,
              "audit_missing": audit_missing, "unexpected": unexpected,
              "overlap_pairs": overlap_pairs(registry),
              "s1": s1_design_condition(), "pending_rules": ["S5"],
              "result_scope": "runs_root_mechanical"}
    result.update(decide(pairs))
    return result


def decide(pairs: list[dict]) -> dict:
    """The pre-registered §7 order; the first rule that fires is the one reported."""
    for pair in pairs:
        for arm in ARMS:
            row = pair[arm]
            if row is None or row["state"] == "MISSING":
                return {"result": "INSUFFICIENT_EVIDENCE",
                        "decided_by": f"COVERAGE:MISSING:{pair['task_id']}/{arm}"}
            if row["state"] in ("INVALID", "BLOCKED"):
                return {"result": "INSUFFICIENT_EVIDENCE",
                        "decided_by": f"COVERAGE:{row['state']}:{row['run_id']}"}
    for pair in pairs:
        for arm in ARMS:
            if pair[arm]["state"] == "AUDIT_MISSING":
                return {"result": "INSUFFICIENT_EVIDENCE",
                        "decided_by": f"AUDIT_VERDICT_MISSING:{pair[arm]['run_id']}"}
    s1 = s1_design_condition()
    if not s1["satisfied"]:
        return {"result": "INSUFFICIENT_EVIDENCE",
                "decided_by": "S1_DESIGN_PRECONDITION_NOT_MET"}
    for pair in pairs:
        for arm in ARMS:
            for finding in pair[arm].get("missed_guidance", []):
                return {"result": "DISCLOSURE_HAS_COST",
                        "decided_by": f"S2_MISSED_GUIDANCE_GE_1:{pair[arm]['run_id']}:{finding}"}
    if sum(int(pair["variant"]["invalid_completion"]) for pair in pairs) > sum(
            int(pair["control"]["invalid_completion"]) for pair in pairs):
        return {"result": "DISCLOSURE_HAS_COST",
                "decided_by": "S3_TREATMENT_ONLY_INVALID_COMPLETION"}
    for pair in pairs:
        control = CORRECTNESS_ORDER[pair["control"]["correctness"]]
        variant = CORRECTNESS_ORDER[pair["variant"]["correctness"]]
        if variant > control:
            return {"result": "DISCLOSURE_HAS_COST",
                    "decided_by": f"S4_TREATMENT_ONLY_CORRECTNESS:{pair['task_id']}"}
    identical = all(pair["control"]["correctness"] == pair["variant"]["correctness"]
                    and pair["control"]["invalid_completion"] == pair["variant"]["invalid_completion"]
                    and finding_identity_rows(pair["control"])
                    == finding_identity_rows(pair["variant"])
                    for pair in pairs)
    if identical:
        return {"result": "INSUFFICIENT_EVIDENCE", "decided_by": "NULL_DIFFERENCE"}
    return {"result": "DISCLOSURE_SAFE",
            "decided_by": "NO_COST_OBSERVED:COMPLETE_COVERAGE+NON_NULL_DIFFERENCE+S1_SATISFIED"}


def finding_identity_rows(row: dict) -> tuple[tuple[str, ...], ...]:
    """The audited finding-identity set of one arm, compared as the auditor recorded it."""
    return tuple(sorted(tuple(item) for item in row.get("identities", ())))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs_root", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        result = aggregate(args.runs_root)
    except ValueError as exc:
        print(json.dumps({"result": "INSUFFICIENT_EVIDENCE", "decided_by": str(exc)},
                         sort_keys=True))
        return 1
    data = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(data, encoding="utf-8")
    else:
        print(data, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
