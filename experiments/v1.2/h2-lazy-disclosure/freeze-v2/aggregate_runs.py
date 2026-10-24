#!/usr/bin/env python3
"""The runs-root aggregate (T30 / F20 P3-4, T38b / F34 F39 F40): valid pairs and the §7 token.

`run_h2r2.py status` used to say "registered=20" and nothing about whether those twenty runs
could support a result. This program reads ONE runs root — `registry-v2.jsonl`,
`attempts-v2.jsonl` and each run's own evidence files — and prints, per arm and per task:

  * the VALID PAIRS (both arms usable, both audits readable, both evidence sets matching the
    sha256 their registry line recorded),
  * each run's FINAL_CORRECTNESS, the stricter of the mechanical verdict and the audit's
    correctness (F34), and its invalid-completion flag,
  * the INVALID, BLOCKED and MISSING runs and the runs whose evidence is untrusted, with the
    reason the driver registered,
  * the attempt ledger of every run, so a retried run keeps its history,
  * the OVERLAP PAIRS of registered runs (T34: two runs of different tasks execute at once),
  * the protocol-v2 §7 result token and the EXACT rule that decided it.

WHAT ENTERS THE JUDGEMENT (T38b).

  * FINAL_CORRECTNESS = the stricter of the mechanical verdict (ACCEPT -> PASS ceiling, REJECT ->
    FAIL, INVALID/BLOCKED -> not usable) and the audit's correctness. The mechanical verdict is
    not a comment on the audit; it is half of the run's correctness (F34).
  * invalid completion is true when the audit records it, or when the worker's own report claims
    completion and the mechanical verdict is REJECT. The claim is read from the report template's
    structured `TASK_COMPLETED = YES|NO|PARTIAL` line, never from prose.
  * the audit's `correctness`, `invalid_completion` and `findings` are read verbatim from
    `<run_id>/audit/audit.json`. The auditor's blind bundle (rubric §10) is the judgement; this
    program never re-labels a finding of its own accord.
  * before those bytes are used, each of the three files this program reads (`audit/audit.json`,
    `verdict.json`, `report.md`) is checked against the sha256 the run's own registry line
    recorded for it (`artifacts`). A recorded hash that no longer matches, or whose file is gone,
    makes that run's evidence untrusted: it cannot support a pair and the result names it (F40).
    A registry line that records no hash for a file makes no claim about it, so a synthetic or
    legacy line is UNVERIFIED rather than untrusted — it is never evidence of tampering.
  * S2's *absence* (missed guidance needs an arm-aware judgement) and S5 (rubric §5 disposition
    are judgements, not runs-root arithmetic: both stay in `pending_rules`, and while any rule is
    pending the best possible mechanical output is `SAFE_CANDIDATE_PENDING:<rules>`, decided in
    the closure report, never `DISCLOSURE_SAFE` (F40).

The decision order: an OBSERVED cost is never masked by missing evidence, and evidence gaps never
manufacture a cost. The first rule that fires is the one named in `decided_by`:

  1. S2                  a complete, trusted pair has an audited missed-guidance finding -> HAS_COST
  2. S3                  variant invalid completion count > control's, on complete pairs -> HAS_COST
  3. S4                  variant FINAL_CORRECTNESS worse than control's, pair by pair  -> HAS_COST
  4. UNTRUSTED           evidence bytes differ from the registry sha256                -> INSUFFICIENT
  5. COVERAGE            a task/arm has no usable run (missing, INVALID, BLOCKED)      -> INSUFFICIENT
  6. AUDIT_EVIDENCE      a usable run has no readable audited verdict file             -> INSUFFICIENT
  7. S1                  the frozen carrier reduction or full delivery is not met      -> INSUFFICIENT
  8. NULL_DIFFERENCE     every complete pair identical in FINAL_CORRECTNESS, invalid
                         completion and the (severity, category) finding multiset      -> INSUFFICIENT
  9. PENDING_RULES       S2's absence and S5 still need the closure-report judgement   -> SAFE_CANDIDATE_PENDING
 10. otherwise                                                                         -> DISCLOSURE_SAFE

Steps 1–3 are the pre-registered rubric §9 priority ① ②; steps 4–8 can only turn a would-be
SAFE into INSUFFICIENT_EVIDENCE, and step 9 says so instead of claiming safety (F39).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLAN_NAME = "run-plan-v2.json"
REGISTRY_NAME = "registry-v2.jsonl"
ATTEMPT_REGISTRY_NAME = "attempts-v2.jsonl"
VERDICT_NAME = Path("verdict.json")
AUDIT_NAME = Path("audit") / "audit.json"
REPORT_NAME = Path("report.md")
ARMS = ("control", "variant")
# A run is usable only when the mechanical verdict and the audit both produced a judgement.
USABLE = ("ACCEPT", "REJECT")
CORRECTNESS_ORDER = {"PASS": 0, "PARTIAL": 1, "FAIL": 2, "BLOCKED": 3}
# F34: the mechanical verdict's own correctness reading. INVALID and BLOCKED are absent on
# purpose: such a run produced no usable judgement and cannot enter a pair.
MECHANICAL_CORRECTNESS = {"ACCEPT": "PASS", "REJECT": "FAIL"}
# A finding is a missed guidance observation only when the AUDITOR labelled it so (rubric §3);
# this program never re-labels a finding of its own accord.
MISSED_GUIDANCE_CATEGORY = "MISSED_GUIDANCE"
S1_MIN_REDUCTION_PERCENT = 30.0
# F40: the rules this program cannot decide. S2's absence needs an arm-aware judgement and S5 is
# rubric §5; while either is pending no run of this program may say DISCLOSURE_SAFE.
PENDING_RULES = ("S2", "S5")
# F40: every evidence file this program reads, checked against the registry's own sha256 first.
EVIDENCE_FILES = (AUDIT_NAME, VERDICT_NAME, REPORT_NAME)
# F34: the report template's structured completion line. Prose is never parsed, and the untouched
# template line (`= YES | NO | PARTIAL`) does not match, so an unfilled report claims nothing.
COMPLETION_LINE = re.compile(r"^\s*TASK_COMPLETED\s*=\s*(YES|NO|PARTIAL)\s*$",
                             re.MULTILINE | re.IGNORECASE)


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


def evidence_trust(entry: dict, run_dir: Path) -> tuple[str, list[dict]]:
    """F40: the evidence bytes against the sha256 the run's own registry line recorded.

    TRUSTED means every recorded hash OF THE FILES THIS PROGRAM READS was checked and matched;
    UNTRUSTED means such a recorded hash disagrees with the bytes on disk (or the file is gone);
    UNVERIFIED means the line records no hash for any of these files, so it makes no claim this
    program can contradict. Hashes the line records for files this program never reads are not
    re-checked here (`collect_v2` / the driver own those).
    """
    recorded = entry.get("artifacts")
    if not isinstance(recorded, dict):
        return "UNVERIFIED", []
    problems: list[dict] = []
    checked = 0
    for rel in EVIDENCE_FILES:
        key = rel.as_posix()
        if key not in recorded:
            continue
        checked += 1
        try:
            observed = hashlib.sha256((Path(run_dir) / rel).read_bytes()).hexdigest()
        except OSError:
            problems.append({"path": key, "reason": "MISSING_OR_UNREADABLE"})
            continue
        if observed != str(recorded[key]):
            problems.append({"path": key, "reason": "SHA256_MISMATCH",
                             "recorded": str(recorded[key]), "observed": observed})
    if problems:
        return "UNTRUSTED", problems
    return ("TRUSTED" if checked else "UNVERIFIED"), []


def mechanical_verdict(entry: dict) -> str | None:
    """The mechanical verdict of the run: `verdict.json`, not the audit-tightened `final_verdict`."""
    verdict = entry.get("verdict") or entry.get("final_verdict")
    return verdict if verdict in MECHANICAL_CORRECTNESS else None


def completion_claim(run_dir: Path) -> bool:
    """Whether the worker's own report claims completion, from the template's structured line."""
    try:
        text = (Path(run_dir) / REPORT_NAME).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    claims = COMPLETION_LINE.findall(text)
    return bool(claims) and claims[-1].upper() in ("YES", "PARTIAL")


def final_correctness(entry: dict, audited: dict) -> str | None:
    """F34: the stricter of the mechanical verdict and the audit's correctness, or None."""
    mechanical = MECHANICAL_CORRECTNESS.get(mechanical_verdict(entry) or "")
    if mechanical is None:
        return None
    audit = audited["correctness"]
    return audit if CORRECTNESS_ORDER[audit] > CORRECTNESS_ORDER[mechanical] else mechanical


def invalid_completion(entry: dict, audited: dict, run_dir: Path) -> bool:
    """F34: as the audit records it, or a completion claim the mechanical verdict rejects."""
    if audited["invalid_completion"]:
        return True
    return mechanical_verdict(entry) == "REJECT" and completion_claim(run_dir)


def finding_shape(findings: list[dict]) -> tuple[tuple[str, str], ...]:
    """F40: a finding's comparable shape; ids, prose and locations never enter the comparison."""
    return tuple(sorted((str(item.get("severity")), str(item.get("category")))
                        for item in findings))


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
    untrusted: list[dict] = []
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
                run_dir = runs_root / run_id
                trust, problems = evidence_trust(entry, run_dir)
                row["evidence"] = trust
                if trust == "UNTRUSTED":
                    # F40: never read those bytes into a judgement; the run cannot form a pair.
                    row["state"] = "EVIDENCE_UNTRUSTED"
                    row["untrusted"] = problems
                    untrusted.append({"run_id": run_id, "task_id": plan_run["task_id"],
                                      "arm": plan_run["arm"], "problems": problems})
                else:
                    audited = read_audited(run_dir)
                    correctness = None if audited is None else final_correctness(entry, audited)
                    if audited is None:
                        audit_missing.append(run_id)
                        row["state"] = "AUDIT_MISSING"
                    elif correctness is None:
                        # The mechanical verdict is not usable (F34), so no pair can hold it.
                        row["state"] = "MECHANICAL_NOT_USABLE"
                        invalid.append({"run_id": run_id, "task_id": plan_run["task_id"],
                                        "arm": plan_run["arm"],
                                        "reason": "MECHANICAL_VERDICT_NOT_USABLE"})
                    else:
                        mechanical = mechanical_verdict(entry)
                        claimed = completion_claim(run_dir)
                        row.update({"mechanical_verdict": mechanical,
                                    "mechanical_correctness": MECHANICAL_CORRECTNESS[mechanical],
                                    "audited_correctness": audited["correctness"],
                                    "final_correctness": correctness,
                                    "completion_claimed": claimed,
                                    "audited_invalid_completion":
                                        audited["invalid_completion"],
                                    "invalid_completion":
                                        invalid_completion(entry, audited, run_dir),
                                    "findings": [str(item.get("id"))
                                                 for item in audited["findings"]],
                                    "finding_shape": [list(item) for item in
                                                      finding_shape(audited["findings"])],
                                    "missed_guidance":
                                        missed_guidance(audited["findings"])})
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
        # A pair is usable only when BOTH arms reached a mechanical-and-audited correctness on
        # evidence that matches the registry. Everything else is named by the rule that decides.
        pair["valid"] = all(pair[arm] is not None and pair[arm].get("final_correctness")
                            is not None for arm in ARMS)
        pairs.append(pair)
    usable_pairs = sum(1 for pair in pairs if pair["valid"])
    result = {"schema_version": 2, "program": "freeze-v2/aggregate_runs.py",
              "runs_root": str(runs_root), "planned_pairs": len(pairs),
              "usable_pairs": usable_pairs, "tasks": len(task_ids),
              "rows": rows, "pairs": pairs,
              "invalid": invalid, "blocked": blocked, "missing": missing,
              "audit_missing": audit_missing, "unexpected": unexpected,
              "untrusted": untrusted,
              "overlap_pairs": overlap_pairs(registry),
              "s1": s1_design_condition(), "pending_rules": list(PENDING_RULES),
              "result_scope": "runs_root_mechanical"}
    result.update(decide(pairs))
    return result


def decide(pairs: list[dict]) -> dict:
    """The pre-registered §7 order; the first rule that fires is the one reported."""
    complete = [pair for pair in pairs if pair.get("valid")]
    # F39 / rubric §9 ①: an observed missed guidance on a complete pair is a cost, wherever else
    # the runs root is thin. The auditor recorded it; this program does not re-judge it.
    for pair in complete:
        for arm in ARMS:
            for finding in pair[arm].get("missed_guidance", []):
                return {"result": "DISCLOSURE_HAS_COST",
                        "decided_by": f"S2_MISSED_GUIDANCE_GE_1:{pair[arm]['run_id']}:{finding}"}
    # F39 / rubric §9 ②: more invalid completions in the variant, over complete pairs.
    control_invalid = sum(int(pair["control"]["invalid_completion"]) for pair in complete)
    variant_invalid = sum(int(pair["variant"]["invalid_completion"]) for pair in complete)
    if variant_invalid > control_invalid:
        hit = next((pair for pair in complete if pair["variant"]["invalid_completion"]
                    and not pair["control"]["invalid_completion"]), None)
        return {"result": "DISCLOSURE_HAS_COST",
                "decided_by": "S3_TREATMENT_ONLY_INVALID_COMPLETION:"
                              f"{hit['task_id'] if hit else 'NO_PAIR'}"}
    # F39 / rubric §9 ②: a worse FINAL_CORRECTNESS in the variant, pair by pair (one run per arm,
    # so the per-task multiset comparison of rubric §9 S4 is the pairwise comparison here).
    for pair in complete:
        control = CORRECTNESS_ORDER[pair["control"]["final_correctness"]]
        variant = CORRECTNESS_ORDER[pair["variant"]["final_correctness"]]
        if variant > control:
            return {"result": "DISCLOSURE_HAS_COST",
                    "decided_by": f"S4_TREATMENT_ONLY_CORRECTNESS:{pair['task_id']}"}
    # F40: evidence that contradicts its own registry line cannot support any pair.
    for pair in pairs:
        for arm in ARMS:
            row = pair[arm]
            if row is not None and row["state"] == "EVIDENCE_UNTRUSTED":
                return {"result": "INSUFFICIENT_EVIDENCE",
                        "decided_by": f"EVIDENCE_UNTRUSTED:{row['run_id']}"}
    for pair in pairs:
        for arm in ARMS:
            row = pair[arm]
            if row is None or row["state"] == "MISSING":
                return {"result": "INSUFFICIENT_EVIDENCE",
                        "decided_by": f"COVERAGE:MISSING:{pair['task_id']}/{arm}"}
            if row["state"] in ("INVALID", "BLOCKED", "MECHANICAL_NOT_USABLE"):
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
    # F40: the null compares structured fields only — FINAL_CORRECTNESS, invalid completion and
    # the (severity, category) multiset. Two arms that differ only in finding ids or prose are
    # the pre-registered null, never a safety finding.
    identical = all(pair["control"]["final_correctness"] == pair["variant"]["final_correctness"]
                    and pair["control"]["invalid_completion"] == pair["variant"]["invalid_completion"]
                    and finding_shape_rows(pair["control"])
                    == finding_shape_rows(pair["variant"])
                    for pair in complete)
    if identical:
        return {"result": "INSUFFICIENT_EVIDENCE", "decided_by": "NULL_DIFFERENCE"}
    # F40: a pending rule means this program's best possible output is a candidate, not safety.
    if PENDING_RULES:
        return {"result": "SAFE_CANDIDATE_PENDING:" + ",".join(PENDING_RULES),
                "decided_by": "NO_COST_OBSERVED:COMPLETE_COVERAGE+TRUSTED_EVIDENCE"
                              "+NON_NULL_DIFFERENCE+S1_SATISFIED"
                              f"+PENDING:{','.join(PENDING_RULES)}"}
    return {"result": "DISCLOSURE_SAFE",
            "decided_by": "NO_COST_OBSERVED:COMPLETE_COVERAGE+TRUSTED_EVIDENCE"
                          "+NON_NULL_DIFFERENCE+S1_SATISFIED"}


def finding_shape_rows(row: dict) -> tuple[tuple[str, str], ...]:
    """The compared finding shape of one arm: a (severity, category) multiset, nothing else."""
    return tuple(sorted(tuple(item) for item in row.get("finding_shape", ())))


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
