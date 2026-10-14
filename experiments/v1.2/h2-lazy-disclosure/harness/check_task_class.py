#!/usr/bin/env python3
"""H2 eligibility — mechanical validator for ELIGIBILITY_SCHEMA_V2 classification records.

WHY THIS EXISTS
---------------
The schema revision is only worth anything if it is enforced by a program rather than by prose.
The failure it guards against is concrete and already measured twice in this repository's history:

  * a task can PASS because the worker authored the thing that decides the verdict
    (measured: `ruff check .` reports "All checks passed" under `select = []`);
  * a task can PASS because no gate observes the deliverable at all
    (measured: the r06 delta adds eight files while the only era gate stays item-for-item 23/23).

Both are acceptance-shape defects, not worker misbehaviour, so they cannot be caught by reviewing
a diff.

WHAT THIS PROGRAM DOES **AND DOES NOT** ENFORCE — read this before trusting a PASS
-------------------------------------------------------------------------------------
The first version of this validator judged only the self-consistency of a self-authored JSON file,
and the adversarial review of commit ea268dd demonstrated the consequence: a hand-written record
that asserted the right field values was accepted and counted as ADMITTED. That is a real limit, and
the honest response is to shrink it rather than to deny it:

  ENFORCED MECHANICALLY (recomputed here, never read from the record):
    · every declared revision that THIS repository contains is resolved with `git cat-file`, and
      for an admissible record the candidate must be a DESCENDANT of the base
      (`git merge-base --is-ancestor`) — a fact about the object database, not a claim;
    · a record whose revisions are NOT resolvable here is marked EXTERNAL_UNVERIFIABLE_LOCALLY and
      may NEVER be admitted to the round (an unverifiable-local fact cannot be the basis of
      admission);
    · every `evidence[].source` must resolve to a file that exists;
    · the closed vocabularies, the per-class field equalities, the trigger/class consistency, the
      disclosure ↔ oracle-authority binding, the C_REJECT "show which class you blocked" rule, and
      the admission preconditions.

  NOT ENFORCED — out-of-band obligations, recorded so nobody mistakes a PASS for a proof:
    · the TRUTH of `baseline_oracle_status` / `mutation_oracle_status` is never recomputed; the
      validator cannot re-run a candidate's oracle;
    · whether the oracle really is outside the worker's scope is a claim about a task design that
      does not exist yet;
    · therefore a PASS means "this record is internally consistent AND, where the repository can
      check it, consistent with the repository". It is not a substitute for the evidence review,
      which is why every record must cite files that exist.

Exit code 0 iff no rule is violated. A legitimately rejected record (C_REJECT with valid triggers)
is a PASS for this validator — it judges CONSISTENCY AND ADMISSIBILITY, not admission.

Usage:  python3 check_task_class.py <classification.json> [repo_root]
"""

from __future__ import annotations

import json
import re
import subprocess
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
SHA_BINDINGS = ("LOCAL_REPO_VERIFIED", "EXTERNAL_UNVERIFIABLE_LOCALLY")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]{3,}$")
PENDING_PREFIX = "ORACLE_EXTERNALIZATION"
REQUIRED_RECORD_KEYS = (
    "candidate_id", "source_repository", "base_sha", "candidate_sha", "class",
    "class_considered", "reject_triggers", "pending_requirements", "round_admission", "evidence",
    "sha_binding",
)


class Repo:
    """Read-only view of the object database the validator runs inside."""

    def __init__(self, root: Path):
        self.root = root

    def _git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(["git", "-C", str(self.root), *args],
                              capture_output=True, text=True)

    def has_commit(self, sha: str) -> bool:
        return self._git("cat-file", "-e", f"{sha}^{{commit}}").returncode == 0

    def is_ancestor(self, base: str, candidate: str) -> bool:
        return self._git("merge-base", "--is-ancestor", base, candidate).returncode == 0


def check_document(doc, repo: Repo, classification_dir: Path) -> list[str]:
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["document is not a JSON object"]
    if doc.get("schema") != SCHEMA_ID:
        errors.append(f"schema is {doc.get('schema')!r}, expected {SCHEMA_ID!r}")
    if not isinstance(doc.get("schema_version"), str) or not doc.get("schema_version"):
        errors.append("schema_version is required (a record set without a version cannot be cited)")
    records = doc.get("records")
    if not isinstance(records, list) or not records:
        errors.append("`records` is missing or empty")
        return errors

    seen: set[str] = set()
    for rec in records:
        if not isinstance(rec, dict):
            errors.append(f"record {type(rec).__name__} is not an object — a malformed record is "
                          f"an error, not a skip")
            continue
        cid = rec.get("candidate_id")
        if isinstance(cid, str):
            if cid in seen:
                errors.append(f"duplicate candidate_id {cid!r}")
            seen.add(cid)
        errors.extend(check_record(rec, repo, classification_dir))
    return errors


def resolve_evidence(source, classification_dir: Path, repo: Repo):
    """Return the resolved path for an evidence source, or None."""
    if not isinstance(source, str) or not source:
        return None
    for base in (classification_dir, repo.root):
        candidate = (base / source).resolve()
        if candidate.is_file():
            return candidate
    return None


def has_oracle_externalization(pending) -> bool:
    """True iff a pending requirement's CODE is exactly ORACLE_EXTERNALIZATION.

    The exact code matters: the first version used a bare `startswith`, so a requirement code like
    ORACLE_EXTERNALIZATION_LATER would have satisfied the same rule while naming a different
    obligation. The code must be followed by a delimiter or end the string.
    """
    for p in pending:
        if not isinstance(p, str) or not p.startswith(PENDING_PREFIX):
            continue
        rest = p[len(PENDING_PREFIX):]
        if rest == "" or rest[0] in (":", " "):
            return True
    return False


def check_record(rec: dict, repo: Repo, classification_dir: Path) -> list[str]:
    cid = rec.get("candidate_id") or "<unnamed record>"
    err: list[str] = []

    for key in REQUIRED_RECORD_KEYS:
        if key not in rec:
            err.append(f"{cid}: missing required key {key!r}")
    for key in ("base_sha", "candidate_sha"):
        value = rec.get(key)
        if not isinstance(value, str) or not SHA_RE.match(value):
            err.append(f"{cid}: {key} is not a 40-hex revision ({value!r})")
    if not isinstance(rec.get("source_repository"), str) or not rec.get("source_repository"):
        err.append(f"{cid}: source_repository must be a non-empty string")

    # --- revision binding: the part of this validator that reads reality ----------------------
    binding = rec.get("sha_binding")
    if binding not in SHA_BINDINGS:
        err.append(f"{cid}: sha_binding must be one of {list(SHA_BINDINGS)} (got {binding!r})")
    base, cand = rec.get("base_sha"), rec.get("candidate_sha")
    if isinstance(base, str) and isinstance(cand, str) and \
            SHA_RE.match(base) and SHA_RE.match(cand):
        local_base, local_cand = repo.has_commit(base), repo.has_commit(cand)
        if local_base and local_cand:
            if binding != "LOCAL_REPO_VERIFIED":
                err.append(f"{cid}: both revisions resolve in this repository, so sha_binding must "
                           f"be LOCAL_REPO_VERIFIED (got {binding!r})")
            if not repo.is_ancestor(base, cand):
                err.append(f"{cid}: LOCAL_REPO_VERIFIED requires the candidate to descend from the "
                           f"base, and {cand[:12]} does not descend from {base[:12]} — this is "
                           f"recomputed from the object database, not read from the record")
        elif local_base or local_cand:
            err.append(f"{cid}: exactly one of the two revisions resolves here — an inconsistent "
                       f"pair cannot be a basis for classification")
        else:
            if binding != "EXTERNAL_UNVERIFIABLE_LOCALLY":
                err.append(f"{cid}: neither revision resolves in this repository, so sha_binding "
                           f"must be EXTERNAL_UNVERIFIABLE_LOCALLY")
            if not rec.get("external_repository"):
                err.append(f"{cid}: an externally bound record must name external_repository")
            if not rec.get("external_verification"):
                err.append(f"{cid}: an externally bound record must record the external "
                           f"verification command (a claim with no stated verification locus is "
                           f"not evidence)")

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
        if not isinstance(t, dict):
            err.append(f"{cid}: every reject_triggers entry must be an object")
            continue
        code = t.get("trigger")
        if code not in TRIGGER_CODES:
            err.append(f"{cid}: unknown trigger code {code!r}")
            continue
        if not CODE_RE.match(str(t.get("reason_code", ""))):
            err.append(f"{cid}: trigger {code} needs a reason_code in UPPER_SNAKE form "
                       f"(got {t.get('reason_code')!r})")
        if not isinstance(t.get("detail"), str) or not t.get("detail"):
            err.append(f"{cid}: trigger {code} needs a non-empty detail")
    if cls in ADMISSIBLE_CLASSES and triggers:
        err.append(f"{cid}: claims {cls} while carrying {len(triggers)} rejection trigger(s) — "
                   f"a claim of an admissible class must have a clean trigger set")
    if cls == "C_REJECT" and not triggers:
        err.append(f"{cid}: C_REJECT requires at least one enumerated trigger")

    # --- pending requirements -----------------------------------------------------------------
    pending = rec.get("pending_requirements")
    if not isinstance(pending, list):
        err.append(f"{cid}: pending_requirements must be a list")
        pending = []
    for p in pending:
        if not isinstance(p, str) or not p.strip():
            err.append(f"{cid}: every pending requirement must be a non-empty string")
        elif not CODE_RE.match(p.split(":", 1)[0].split(" ", 1)[0]):
            err.append(f"{cid}: pending requirement {p[:40]!r} must begin with an UPPER_SNAKE code")

    # --- per-class requirements ---------------------------------------------------------------
    req = rec.get("class_requirements")
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
            if authority == "PENDING_FREEZE_V2" and not has_oracle_externalization(pending):
                err.append(f"{cid}: oracle_authority PENDING_FREEZE_V2 requires a pending "
                           f"requirement whose code is exactly {PENDING_PREFIX!r} (a longer code "
                           f"that merely starts with it is not the same requirement)")
            # disclosure ↔ authority binding: an oracle the historical delta touched cannot be
            # claimed as already frozen, and must be covered by a pending externalisation
            disclosures = rec.get("disclosures") or {}
            if disclosures.get("historical_delta_touched_oracle") is True:
                if authority == "FRAMEWORK_FROZEN":
                    err.append(f"{cid}: oracle_authority cannot be FRAMEWORK_FROZEN while the "
                               f"record discloses that the historical delta touched the oracle — "
                               f"the freeze is not materialised yet")
                if not has_oracle_externalization(pending):
                    err.append(f"{cid}: a touched oracle requires a {PENDING_PREFIX} pending "
                               f"requirement")

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
            for c in blocked:
                if not isinstance(c.get("reason"), str) or not c.get("reason").strip():
                    err.append(f"{cid}: the BLOCKED entry for {c.get('class')} needs a reason")

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
            if binding != "LOCAL_REPO_VERIFIED":
                err.append(f"{cid}: admission requires a locally verifiable revision pair — an "
                           f"EXTERNAL_UNVERIFIABLE_LOCALLY record can never be admitted (the "
                           f"verdict would rest on a fact this repository cannot check)")
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
                continue
            sources = e["source"] if isinstance(e["source"], list) else [e["source"]]
            if not sources or not all(isinstance(s, str) and s.strip() for s in sources):
                err.append(f"{cid}: evidence[{i}].source must be a path or a non-empty list of "
                           f"paths")
                continue
            for s in sources:
                if resolve_evidence(s, classification_dir, repo) is None:
                    err.append(f"{cid}: evidence[{i}].source {s!r} does not resolve to an existing "
                               f"file — evidence must be reachable, not asserted")

    return err


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: check_task_class.py <classification.json> [repo_root]", file=sys.stderr)
        return 2
    path = Path(argv[1])
    if not path.is_file():
        print(f"TASK_CLASS_VERDICT = FAIL reason=NO_CLASSIFICATION_FILE path={path}")
        return 1
    repo_root = Path(argv[2]).resolve() if len(argv) == 3 else Path(__file__).resolve().parents[4]
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"TASK_CLASS_VERDICT = FAIL reason=UNREADABLE err={exc}")
        return 1

    repo = Repo(repo_root)
    errors = check_document(doc, repo, path.resolve().parent)

    records = doc.get("records") if isinstance(doc, dict) else []
    records = records if isinstance(records, list) else []
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
        print(f"  {str(rec.get('candidate_id', '<unnamed>')):44s} class={str(cls):20s} "
              f"binding={str(rec.get('sha_binding')):32s} triggers={n_trig} admission={adm}")

    if errors:
        for e in errors:
            print(f"  ERROR {e}")
        print(f"TASK_CLASS_VERDICT = FAIL records={len(records)} errors={len(errors)}")
        return 1
    print(f"TASK_CLASS_VERDICT = PASS records={len(records)} "
          f"admitted_to_round={len(admitted)} rejected={len(records) - len(admitted)} errors=0 "
          f"enforcement=SELF_CONSISTENCY+LOCAL_REPO_BINDING (oracle statuses are declared, not "
          f"recomputed — see the module docstring)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
