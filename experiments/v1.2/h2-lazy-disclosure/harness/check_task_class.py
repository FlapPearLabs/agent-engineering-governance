#!/usr/bin/env python3
"""H2 eligibility — mechanical validator for ELIGIBILITY_SCHEMA_V2 classification records.

WHY THIS EXISTS
---------------
The schema revision is only worth anything if it is enforced by a program rather than by prose.
The failure it guards against is concrete and already measured twice in this repository's history:

  * a task can PASS because the worker authored the thing that decides the verdict
    (measured: `ruff check .` reports "All checks passed" under `select = []` on the r03 tree);
  * a task can PASS because no gate observes the deliverable at all
    (measured: the r06 delta adds eight files while the only era gate stays item-for-item 23/23).

Both are acceptance-shape defects, not worker misbehaviour, so they cannot be caught by reviewing
a diff. This validator decides, from a machine-readable record, whether a task's acceptance shape
is admissible — and refuses records that claim an admissible class while carrying a rejection
trigger.

WHAT IT ENFORCES
----------------
  R0  the document declares the schema and carries at least one record;
  R1  every record carries the required structural fields and 40-hex revisions;
  R2  `class` is one of the three declared classes — MISSING OR UNKNOWN IS AN ERROR, never a pass
      (a task that was never classified must not slip through as "not rejected");
  R3  every trigger code is one of the six enumerated codes; an admissible class (A/B) carrying
      ANY trigger is an error, and C_REJECT must carry at least one;
  R4  A_REPAIR: baseline oracle FAIL, candidate oracle PASS, the oracle is NOT in the worker's
      scope, and the oracle's authority is declared; a pending authority requires a matching
      ORACLE_EXTERNALIZATION pending requirement and forbids round admission;
  R5  B_REGRESSION_GUARD: baseline oracle PASS, mutation oracle FAIL, the mutation touches the
      target predicate, the acceptance surface is frozen and the validator is not worker-controlled;
  R6  C_REJECT must SHOW its work: at least one admissible class has to be listed in
      `class_considered` as blocked, so a task cannot be dumped into the reject class unexamined;
  R7  round admission is never implicit: ADMITTED requires an admissible class, zero triggers,
      zero pending requirements and a fully materialised oracle authority; NOT_ADMITTED requires
      reason codes;
  R8  every record carries non-empty evidence with claim / measured / source.

Exit code 0 iff no rule is violated. A legitimately rejected record (C_REJECT with valid triggers)
is a PASS for this validator — the validator judges CONSISTENCY AND ADMISSIBILITY, not whether a
task was admitted.

Usage:  python3 check_task_class.py <classification.json>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCHEMA_ID = "ELIGIBILITY_SCHEMA_V2"
CLASSES = ("A_REPAIR", "B_REGRESSION_GUARD", "C_REJECT")
ADMISSIBLE_CLASSES = ("A_REPAIR", "B_REGRESSION_GUARD")
TRIGGER_CODES = (
    "WORKER_MODIFIES_VALIDATOR",
    "WORKER_MODIFIES_TEST_ORACLE",
    "ACCEPTANCE_SURFACE_IN_WORKER_SCOPE",
    "SELF_PROVING_HASH",
    "OBSERVATION_COVERAGE_UNPROVEN",
    "BASE_CANDIDATE_NOT_COMPARABLE",
)
ORACLE_AUTHORITIES = ("FRAMEWORK_FROZEN", "PENDING_FREEZE_V2")
ADMISSION_VERDICTS = ("ADMITTED_TO_H2_R2", "NOT_ADMITTED")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_RECORD_KEYS = (
    "candidate_id", "source_repository", "base_sha", "candidate_sha", "class",
    "class_considered", "reject_triggers", "pending_requirements", "round_admission", "evidence",
)


def check_document(doc: dict) -> list[str]:
    errors: list[str] = []
    if doc.get("schema") != SCHEMA_ID:
        errors.append(f"schema is {doc.get('schema')!r}, expected {SCHEMA_ID!r}")
    records = doc.get("records")
    if not isinstance(records, list) or not records:
        errors.append("`records` is missing or empty")
        return errors
    for rec in records:
        errors.extend(check_record(rec))
    return errors


def check_record(rec: dict) -> list[str]:
    cid = rec.get("candidate_id") or "<unnamed record>"
    err: list[str] = []

    for key in REQUIRED_RECORD_KEYS:
        if key not in rec:
            err.append(f"{cid}: missing required key {key!r}")
    for key in ("base_sha", "candidate_sha"):
        value = rec.get(key)
        if not isinstance(value, str) or not SHA_RE.match(value):
            err.append(f"{cid}: {key} is not a 40-hex revision ({value!r})")

    cls = rec.get("class")
    if cls not in CLASSES:
        err.append(f"{cid}: class is {cls!r}; it must be one of {list(CLASSES)} "
                   f"(an unclassified task is an error, never a silent pass)")
        return err

    # --- triggers -----------------------------------------------------------------------------
    triggers = rec.get("reject_triggers")
    if not isinstance(triggers, list):
        err.append(f"{cid}: reject_triggers must be a list")
        triggers = []
    for t in triggers:
        code = t.get("trigger") if isinstance(t, dict) else None
        if code not in TRIGGER_CODES:
            err.append(f"{cid}: unknown trigger code {code!r}")
        elif not (t.get("reason_code") and t.get("detail")):
            err.append(f"{cid}: trigger {code} needs both reason_code and detail")
    if cls in ADMISSIBLE_CLASSES and triggers:
        err.append(f"{cid}: claims {cls} while carrying {len(triggers)} rejection trigger(s) — "
                   f"a claim of an admissible class must have a clean trigger set")
    if cls == "C_REJECT" and not triggers:
        err.append(f"{cid}: C_REJECT requires at least one enumerated trigger")

    # --- per-class requirements ---------------------------------------------------------------
    req = rec.get("class_requirements")
    pending = rec.get("pending_requirements")
    if not isinstance(pending, list):
        err.append(f"{cid}: pending_requirements must be a list")
        pending = []

    if cls == "A_REPAIR":
        if not isinstance(req, dict):
            err.append(f"{cid}: A_REPAIR requires class_requirements")
        else:
            if req.get("baseline_oracle_status") != "FAIL":
                err.append(f"{cid}: A_REPAIR baseline_oracle_status must be 'FAIL' "
                           f"(got {req.get('baseline_oracle_status')!r})")
            if req.get("candidate_oracle_status") != "PASS":
                err.append(f"{cid}: A_REPAIR candidate_oracle_status must be 'PASS' "
                           f"(got {req.get('candidate_oracle_status')!r})")
            if req.get("oracle_in_worker_scope") is not False:
                err.append(f"{cid}: A_REPAIR requires oracle_in_worker_scope false")
            authority = req.get("oracle_authority")
            if authority not in ORACLE_AUTHORITIES:
                err.append(f"{cid}: oracle_authority must be one of {list(ORACLE_AUTHORITIES)} "
                           f"(got {authority!r})")
            if authority == "PENDING_FREEZE_V2" and not any(
                    isinstance(p, str) and p.startswith("ORACLE_EXTERNALIZATION") for p in pending):
                err.append(f"{cid}: oracle_authority PENDING_FREEZE_V2 requires an "
                           f"ORACLE_EXTERNALIZATION pending requirement")

    if cls == "B_REGRESSION_GUARD":
        if not isinstance(req, dict):
            err.append(f"{cid}: B_REGRESSION_GUARD requires class_requirements")
        else:
            if req.get("baseline_oracle_status") != "PASS":
                err.append(f"{cid}: B_REGRESSION_GUARD baseline_oracle_status must be 'PASS'")
            if req.get("mutation_oracle_status") != "FAIL":
                err.append(f"{cid}: B_REGRESSION_GUARD mutation_oracle_status must be 'FAIL'")
            for flag in ("mutation_touches_target_predicate", "acceptance_surface_frozen",
                         "validator_not_worker_controlled"):
                if req.get(flag) is not True:
                    err.append(f"{cid}: B_REGRESSION_GUARD requires {flag} true")

    if cls == "C_REJECT":
        considered = rec.get("class_considered")
        if not isinstance(considered, list) or not considered:
            err.append(f"{cid}: C_REJECT requires class_considered (a task may not be dumped into "
                       f"the reject class without showing which admissible class was blocked)")
        else:
            blocked = [c for c in considered
                       if isinstance(c, dict) and c.get("class") in ADMISSIBLE_CLASSES
                       and c.get("verdict") == "BLOCKED"]
            if not blocked:
                err.append(f"{cid}: C_REJECT requires at least one admissible class listed as "
                           f"BLOCKED in class_considered")

    # --- admission ----------------------------------------------------------------------------
    admission = rec.get("round_admission")
    if not isinstance(admission, dict):
        err.append(f"{cid}: round_admission must be an object")
    else:
        verdict = admission.get("verdict")
        if verdict not in ADMISSION_VERDICTS:
            err.append(f"{cid}: round_admission.verdict must be one of {list(ADMISSION_VERDICTS)}")
        elif verdict == "ADMITTED_TO_H2_R2":
            if cls not in ADMISSIBLE_CLASSES:
                err.append(f"{cid}: only {list(ADMISSIBLE_CLASSES)} may be admitted")
            if triggers:
                err.append(f"{cid}: admission is forbidden while any rejection trigger is set")
            if pending:
                err.append(f"{cid}: admission is forbidden while pending requirements remain "
                           f"({len(pending)} open)")
            if isinstance(req, dict) and "PENDING_FREEZE_V2" in json.dumps(req):
                err.append(f"{cid}: admission is forbidden while a class requirement is still "
                           f"PENDING_FREEZE_V2")
        elif not admission.get("reason_codes"):
            err.append(f"{cid}: NOT_ADMITTED requires non-empty reason_codes")

    # --- evidence -----------------------------------------------------------------------------
    evidence = rec.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        err.append(f"{cid}: evidence is required (a classification without measured evidence is "
                   f"an opinion)")
    else:
        for i, e in enumerate(evidence):
            if not isinstance(e, dict) or not all(e.get(k) for k in ("claim", "measured", "source")):
                err.append(f"{cid}: evidence[{i}] needs claim + measured + source")

    return err


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: check_task_class.py <classification.json>", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"TASK_CLASS_VERDICT = FAIL reason=NO_CLASSIFICATION_FILE path={path}")
        return 1
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"TASK_CLASS_VERDICT = FAIL reason=UNREADABLE err={exc}")
        return 1

    errors = check_document(doc)

    records = doc.get("records") or []
    admitted = [r.get("candidate_id") for r in records
                if isinstance(r, dict)
                and isinstance(r.get("round_admission"), dict)
                and r["round_admission"].get("verdict") == "ADMITTED_TO_H2_R2"]
    for rec in records:
        if not isinstance(rec, dict):
            continue
        cls = rec.get("class")
        adm = (rec.get("round_admission") or {}).get("verdict")
        n_trig = len(rec.get("reject_triggers") or [])
        print(f"  {rec.get('candidate_id', '<unnamed>'):44s} class={str(cls):20s} "
              f"triggers={n_trig} admission={adm}")

    if errors:
        for e in errors:
            print(f"  ERROR {e}")
        print(f"TASK_CLASS_VERDICT = FAIL records={len(records)} errors={len(errors)}")
        return 1
    print(f"TASK_CLASS_VERDICT = PASS records={len(records)} "
          f"admitted_to_round={len(admitted)} rejected={len(records) - len(admitted)} errors=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
