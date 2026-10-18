#!/usr/bin/env python3
"""Build Schema-v2 classification RECORDS (requests) for a measured admission batch (pre-freeze).

Every measured pair gets exactly one record. The record is a REQUEST, never a verdict: the
validator (harness/check_task_class.py) re-executes the transition from scratch and binds every
declared status to its own measurement, so a record built from a stale or flaky measurement is
refused rather than believed. Nothing here can make a pair valid that the validator would not.

Class selection follows the measured transition only:
  A supported (FAIL_TO_PASS)               -> A_REPAIR, request REQUEST_VALID
  else B supported (PASS_TO_FAIL_UNDER_..) -> B_REGRESSION_GUARD, request REQUEST_VALID
  else                                     -> C_REJECT with OBSERVATION_COVERAGE_UNPROVEN, the
                                              measured reason as reason_code, both admissible
                                              classes BLOCKED with their measured reasons

Pairs reach this program from MEASURE_ADDED_ACCEPTANCE (batch 1) or DEFERRED_FROZEN_BASIS_SCAN
(batch 2); both dispositions mean the derived-trigger set is empty. Every evidence and disclosure
string is DERIVED from the pair's own disposition and the basis provenance (a hardcoded string
once told batch 2 it "adds an acceptance surface" and that its basis was DELTA_ADDED — fresh
review of 4add2ca, finding 5). A derived trigger is never cleared here.

Usage:  build_records.py <batch_dir>
          reads  <batch_dir>/case-map.json (its optional `discovery` names the discovery
                 file, default discovery-governance.json), measurements/*.json, probes/*.json
          writes <batch_dir>/classification.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "harness"))

import check_task_class as ctc  # noqa: E402

REPO = "FlapPearLabs/agent-engineering-governance"


def rel(path: Path) -> str:
    """Repository-relative citation (the validator resolves evidence inside the repository)."""
    root = HERE.parents[3]
    return path.resolve().relative_to(root).as_posix()


ROUTING = {
    "MEASURE_ADDED_ACCEPTANCE": "its delta rewrites no test and no validator (derived triggers "
                                "empty) and ADDS an acceptance surface",
    "DEFERRED_FROZEN_BASIS_SCAN": "its delta rewrites no test and no validator (derived triggers "
                                  "empty) and adds no acceptance surface, so every frozen surface "
                                  "was executed",
    "EXTERNALIZED_ORACLE": "it is a NEW identity (B', C): B' is the original base plus the "
                           "candidate's version of the rewritten tests (admission/externalize.py), "
                           "so the oracle is framework-frozen and the delta derives no trigger",
}


def reject_detail(facts: dict, a: dict, b: dict) -> str:
    """Why neither class holds, from the measured facts (a fixed sentence was false for r26/r29:
    their link guard DID bite, and B was refused for a regression — fresh review of ceb3a72)."""
    def names(entries):
        return ", ".join(f"{e['path']} [{e['provenance']}] {e['rc_base']}->{e['rc_cand']}"
                         for e in entries) or "none"
    return (f"A: {a['reason']} (surfaces moving FAIL->PASS: "
            f"{names(facts.get('discriminating') or [])}); "
            f"B: {b['reason']} (biting: {names(facts.get('biting') or [])}; "
            f"regressed guards: {names(facts.get('regressed') or [])}; "
            f"unmeasured guards: {names(facts.get('guard_unmeasured') or [])})")


def record(case_id: str, m: dict, mpath: Path, ppath: Path, dpath: Path, pair: dict) -> dict:
    facts, verdicts = m["facts"], m["verdicts"]
    a, b = verdicts["A_REPAIR"], verdicts["B_REGRESSION_GUARD"]
    disposition = pair["disposition"]
    if disposition not in ROUTING or pair["derived_triggers"]:
        raise SystemExit(f"{case_id}: disposition {disposition} / triggers "
                         f"{pair['derived_triggers']} cannot produce a request here")
    basis = (facts.get("discriminating") or [None])[0] if a["supported"] else None
    guard = (facts.get("biting") or [None])[0] if (b["supported"] and not basis) else None
    carried = basis or guard
    provenance_note = (f"the transition is carried by {carried['path']} [{carried['provenance']}]"
                       + (" — the historical delta introduced it; the validator binds "
                          "oracle_in_worker_scope and oracle_authority to that provenance"
                          if carried["provenance"] == "DELTA_ADDED" else
                          " — identical bytes at both revisions (framework-frozen)")
                       if carried else "no surface carries a supported transition")
    rec = {
        "candidate_id": case_id,
        "corpus_case_id": case_id,
        "source_repository": REPO,
        "base_sha": m["base_sha"],
        "candidate_sha": m["candidate_sha"],
        "sha_binding": "LOCAL_REPO_VERIFIED",
        "reject_triggers": [],
        "pending_requirements": [],
        # the delta rewrites no test and no validator: discovery routed this pair here only
        # because ctc.derived_triggers() is empty for it, and the validator re-derives that fact
        "disclosures": {"historical_delta_touched_oracle": False,
                        **({"identity_note": f"EXTERNALIZED_ORACLE of the real pair "
                                             f"{pair['original_base'][:12]} -> "
                                             f"{m['candidate_sha'][:12]}; externalized "
                                             f"{pair['externalized_paths']} (the historical "
                                             f"delta DID rewrite them; this pair does not)"}
                           if disposition == "EXTERNALIZED_ORACLE" else {}),
                        "historical_delta_touched_validator": False,
                        "acceptance_provenance_note": provenance_note},
    }
    evidence = [
        {"claim": f"the pair was routed to measurement because {ROUTING[disposition]}",
         "measured": f"discovery disposition {disposition}",
         "source": rel(dpath)},
        {"claim": "the acceptance transition, executed in base / candidate / controlled-mutation "
                  "trees by the validator's own recompute_transition",
         "measured": f"A={a['reason']} B={b['reason']} over {facts.get('acceptance_count')} "
                     f"surface(s), {facts.get('frozen_count')} frozen",
         "source": rel(mpath)},
    ]
    if ppath.is_file():
        evidence.append({"claim": "the basis acceptance exercised tests (not skipped, not empty)",
                         "measured": "unittest-reported ran/skipped/failures/errors per state",
                         "source": rel(ppath)})
    rec["evidence"] = evidence
    if a["supported"]:
        rec.update({
            "class": "A_REPAIR",
            "class_considered": [
                {"class": "A_REPAIR", "verdict": "SHAPE_SATISFIED"},
                {"class": "B_REGRESSION_GUARD", "verdict": "BLOCKED",
                 "reason": f"measured {b['reason']}"}],
            "class_requirements": {
                "baseline_oracle_status": "FAIL", "candidate_oracle_status": "PASS",
                "oracle_in_worker_scope": bool(facts["oracle_in_worker_scope"]),
                "oracle_authority": ("FRAMEWORK_FROZEN" if basis["provenance"] == "DELTA_FROZEN"
                                     else "DELTA_AUTHORED_DISCRIMINATING")},
            "round_admission": {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"],
                                "note": "a valid REQUEST is not an admission; the grant is "
                                        "Freeze v2 plus independent review"},
        })
    elif b["supported"]:
        rec.update({
            "class": "B_REGRESSION_GUARD",
            "class_considered": [
                {"class": "B_REGRESSION_GUARD", "verdict": "SHAPE_SATISFIED"},
                {"class": "A_REPAIR", "verdict": "BLOCKED", "reason": f"measured {a['reason']}"}],
            "class_requirements": {
                "baseline_oracle_status": "PASS", "mutation_oracle_status": "FAIL",
                "mutation_touches_target_predicate": True, "acceptance_surface_frozen": True,
                "validator_not_worker_controlled": True},
            "round_admission": {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]},
        })
    else:
        rec.update({
            "class": "C_REJECT",
            "class_considered": [
                {"class": "A_REPAIR", "verdict": "BLOCKED", "reason": f"measured {a['reason']}"},
                {"class": "B_REGRESSION_GUARD", "verdict": "BLOCKED",
                 "reason": f"measured {b['reason']}"}],
            "reject_triggers": [{"trigger": "OBSERVATION_COVERAGE_UNPROVEN",
                                 "reason_code": a["reason"],
                                 "detail": reject_detail(facts, a, b)}],
            "round_admission": {"verdict": "NOT_ADMITTED",
                                "reason_codes": sorted({a["reason"], b["reason"]})},
        })
    return rec


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    batch = Path(argv[1]).resolve()
    cdoc = json.loads((batch / "case-map.json").read_text(encoding="utf-8"))
    cmap = cdoc["cases"]
    # a batch may reuse an earlier batch's discovery (batch 2 measures batch 1's deferred pairs)
    dpath = (batch / cdoc.get("discovery", "discovery-governance.json")).resolve()
    pairs = {p["candidate_sha"]: p for p in
             json.loads(dpath.read_text(encoding="utf-8"))["pairs"] if "base_sha" in p}
    records = []
    for cand, case_id in sorted(cmap.items(), key=lambda kv: kv[1]):
        mpath = batch / "measurements" / f"{cand[:12]}.json"
        m = json.loads(mpath.read_text(encoding="utf-8"))
        if m["candidate_sha"] != cand:
            raise SystemExit(f"{mpath}: measures {m['candidate_sha']}, not {cand}")
        records.append(record(case_id, m, mpath, batch / "probes" / f"{cand[:12]}.json", dpath,
                              pairs[cand]))
    doc = {"schema": ctc.SCHEMA_ID, "schema_version": ctc.SCHEMA_VERSION,
           "status": "ADMISSION_BATCH_REQUESTS_NOT_FROZEN",
           "record_semantics": "one record per measured historical pair; class and lifecycle "
                               "statuses follow the measured transition and are re-executed and "
                               "bound by the validator. REQUEST_VALID is a request to Freeze v2, "
                               "not an admission.",
           "records": records}
    (batch / "classification.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                                               encoding="utf-8")
    counts: dict[str, int] = {}
    for r in records:
        counts[r["class"]] = counts.get(r["class"], 0) + 1
    print(f"RECORDS {len(records)} {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
