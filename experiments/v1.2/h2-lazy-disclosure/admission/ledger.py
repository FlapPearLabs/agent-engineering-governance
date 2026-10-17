#!/usr/bin/env python3
"""Admission LEDGER for one batch: every candidate, every field, from mechanical sources only.

Inputs (all inside <batch_dir>): discovery-governance.json (or a path given with --discovery),
measurements/*.json, probes/*.json, case-map.json, classification.json, validator-run.txt.
Nothing is typed by hand: each field below names its source.

  SCHEMA_V2_RESULT       the validator's own per-record line in validator-run.txt, and only if
                         that run ended in TASK_CLASS_VERDICT = PASS (a FAIL run yields no result)
  STATE_TRANSITION etc.  the measurement; the ledger additionally requires the validator's
                         TRANSITION line (an independent second execution) to name the same basis
                         and exit codes — a disagreement is reported as EXECUTIONS_DISAGREE
  ORACLE_KIND/FAMILY     OBSERVATIONS for Freeze v2, derived from the delta's file list; they are
                         not Schema-v2 inputs and they change no verdict

Usage:  ledger.py <batch_dir>
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
CODE_RE = re.compile(r"\.(py|sh|mjs|js|ts)$|^schemas/.*\.json$")
TRANS_RE = re.compile(r"^\s+TRANSITION (\S+) class=(\S+) verdict=(\S+) basis=(\S+) provenance=(\S+) "
                      r"base_rc=(\S+) cand_rc=(\S+) mut_rc=(\S+)")
LINE_RE = re.compile(r"^\s+(\S+)\s+class=(\S+)\s+binding=(\S+)\s+triggers=(\d+) request=(\S+)")


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          check=True).stdout


def rel(p: Path) -> str:
    return p.resolve().relative_to(ROOT).as_posix()


def main(argv: list[str]) -> int:
    batch = Path(argv[1]).resolve()
    cdoc = json.loads((batch / "case-map.json").read_text(encoding="utf-8"))
    cmap = cdoc["cases"]
    dpath = (batch / cdoc.get("discovery", "discovery-governance.json")).resolve()
    disc = json.loads(dpath.read_text(encoding="utf-8"))
    pairs = {p["candidate_sha"]: p for p in disc["pairs"] if "base_sha" in p}
    recs = {r["corpus_case_id"]: r for r in
            json.loads((batch / "classification.json").read_text(encoding="utf-8"))["records"]}
    run = (batch / "validator-run.txt").read_text(encoding="utf-8")
    passed = "TASK_CLASS_VERDICT = PASS" in run
    lines = {m.group(1): m.groups() for m in map(LINE_RE.match, run.splitlines()) if m}
    trans = {m.group(1): m.groups() for m in map(TRANS_RE.match, run.splitlines()) if m}

    diag_path = batch / "bite-diagnosis.json"
    diagnosis = ({d["candidate_sha"]: d["bites"] for d in
                  json.loads(diag_path.read_text(encoding="utf-8"))} if diag_path.is_file() else {})
    rows = []
    for cand, case_id in sorted(cmap.items(), key=lambda kv: kv[1]):
        p, rec = pairs[cand], recs[case_id]
        mpath = batch / "measurements" / f"{cand[:12]}.json"
        ppath = batch / "probes" / f"{cand[:12]}.json"
        m = json.loads(mpath.read_text(encoding="utf-8"))
        probe = json.loads(ppath.read_text(encoding="utf-8")) if ppath.is_file() else {"probes": []}
        facts = m["facts"]
        basis = (facts.get("discriminating") or [None])[0]
        guard = (facts.get("biting") or [None])[0] if rec["class"] == "B_REGRESSION_GUARD" else None
        changed = [path for _, path in p["changed"]]
        oracle = basis["path"] if basis else None
        worker_scope = [x for x in changed if x != oracle]
        code = [x for x in worker_scope if CODE_RE.search(x)]
        oracle_kind = ("BEHAVIORAL" if code else
                       "DOC_TEXT" if all(x.endswith(".md") for x in worker_scope) else "DOC_OR_DATA")
        if guard:
            # for a guard the oracle is the check that BIT, not the deliverable: name it from the
            # diagnosis (diagnose_bites.py), or say that it was not diagnosed
            vg = {b["path"]: b["failing"] for b in diagnosis.get(cand, [])}
            oracle_kind = ("GUARD:LINK_INTEGRITY"
                           if vg.get("scripts/validate_governance.py") == ["markdown-links-resolve"]
                           else "GUARD:UNDIAGNOSED" if not vg else "GUARD:OTHER")
        family = ("P1_TICKET_DOC_RECIPE" if oracle_kind == "DOC_TEXT" and
                  re.search(r"P1-T\d|stage\d/lane", p["subject"]) else "INDIVIDUAL")
        line = lines.get(case_id)
        result = (f"{line[1]} / {line[4]}" if (passed and line) else
                  "NO_RESULT (validator run did not PASS)")
        agree = "N/A (no supported transition)"
        carried = basis if rec["class"] == "A_REPAIR" else guard
        if carried:
            t = trans.get(case_id)
            agree = ("EXECUTIONS_AGREE" if t and t[3] == carried["path"] and
                     (t[5], t[6], t[7]) == tuple(str(carried[k])
                                                 for k in ("rc_base", "rc_cand", "rc_mut"))
                     else "EXECUTIONS_DISAGREE")
        pb = next((x for x in probe["probes"] if x.get("path") == oracle), None)
        blob = (hashlib.sha256(subprocess.run(["git", "-C", str(ROOT), "show", f"{cand}:{oracle}"],
                                              capture_output=True, check=True).stdout).hexdigest()
                if oracle else None)
        rows.append({
            "CASE_ID": case_id,
            "REPOSITORY": "FlapPearLabs/agent-engineering-governance",
            "TASK_DESCRIPTION": p["subject"],
            "BASE_SHA": p["base_sha"], "CANDIDATE_SHA": cand,
            "TASK_CLASS": rec["class"],
            "FROZEN_ACCEPTANCE_DEFINITION": (
                {"path": oracle, "candidate_blob_sha256": blob, "kind": basis["kind"],
                 "command": ("{PY} -m unittest discover -s scripts/tests -p " + Path(oracle).name
                             if basis["kind"] == "TEST" else "{PY} " + oracle)}
                if basis else None),
            "BASE_RESULT": (f"rc={basis['rc_base']}" + (f" ran={pb['base']['ran']} "
                            f"failures={pb['base']['failures']} errors={pb['base']['errors']} "
                            f"skipped={pb['base']['skipped']} types={pb['base']['first_error_types']}"
                            if pb and "base" in pb else "")) if basis else "no basis",
            "CANDIDATE_RESULT": (f"rc={basis['rc_cand']}" + (f" ran={pb['candidate']['ran']} "
                                 f"skipped={pb['candidate']['skipped']}"
                                 if pb and "candidate" in pb else "")) if basis else "no basis",
            "MUTATION_RESULT": (m["verdicts"]["B_REGRESSION_GUARD"]["reason"] +
                                (f" guard={guard['path']} rc base/cand/mut="
                                 f"{guard['rc_base']}/{guard['rc_cand']}/{guard['rc_mut']}"
                                 if guard else "")),
            "STATE_TRANSITION": m["verdicts"]["A_REPAIR"]["reason"],
            "ORACLE_LOCATION": f"{oracle}@{cand[:12]}" if oracle else None,
            "ORACLE_EXTERNALIZATION": ("REQUIRED_AT_FREEZE_V2: historical delta AUTHORED the oracle "
                                       "(DELTA_ADDED); the frozen bytes above must be placed by "
                                       "the acceptance harness and the path excluded from the "
                                       "worker's scope" if basis else "N/A"),
            "WORKER_SCOPE": worker_scope,
            "ORACLE_IN_WORKER_SCOPE": {"historical": bool(facts.get("oracle_in_worker_scope")),
                                       "required_design": False},
            "VALIDATOR_IN_WORKER_SCOPE": [x for x in worker_scope
                                          if re.search(r"(^|/)(validate|check)_[^/]*\.(py|sh)$", x)],
            "DERIVED_TRIGGERS": p["derived_triggers"],
            "SCHEMA_V2_RESULT": result,
            "REJECTION_REASON": (rec["round_admission"].get("reason_codes")
                                 if rec["round_admission"]["verdict"] != "REQUEST_VALID" else None),
            "EXECUTION_AGREEMENT": agree,
            "OBSERVATION_ORACLE_KIND": oracle_kind,
            "OBSERVATION_TASK_FAMILY": family,
            "OBSERVATION_GUARD_CHECKS": ({b["path"]: b["failing"] for b in diagnosis[cand]}
                                         if guard and cand in diagnosis else None),
            "EVIDENCE_PATHS": [rel(dpath), rel(mpath),
                               *([rel(ppath)] if ppath.is_file() else []),
                               *([rel(diag_path)] if guard and cand in diagnosis else []),
                               rel(batch / "classification.json"), rel(batch / "validator-run.txt")],
        })
    valid = [r for r in rows if r["SCHEMA_V2_RESULT"].endswith("/ REQUEST_VALID")]
    summary = {
        "validator_run": "PASS" if passed else "FAIL",
        "records": len(rows), "schema_v2_valid_requests": len(valid),
        "executions_disagree": sum(r["EXECUTION_AGREEMENT"] == "EXECUTIONS_DISAGREE" for r in rows),
        "valid_by_oracle_kind": {k: sum(r["OBSERVATION_ORACLE_KIND"] == k for r in valid)
                                 for k in sorted({r["OBSERVATION_ORACLE_KIND"] for r in valid})},
        "valid_by_family": {k: sum(r["OBSERVATION_TASK_FAMILY"] == k for r in valid)
                            for k in ("P1_TICKET_DOC_RECIPE", "INDIVIDUAL")},
    }
    (batch / "ledger.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1,
                                                  ensure_ascii=False) + "\n", encoding="utf-8")
    print("LEDGER", json.dumps(summary))
    return 0 if passed and not summary["executions_disagree"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
