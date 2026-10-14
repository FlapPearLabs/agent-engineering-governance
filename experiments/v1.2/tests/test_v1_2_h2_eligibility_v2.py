"""Material checks for ELIGIBILITY_SCHEMA_V2 (H2 task-classification revision, node N2.1).

The schema revision is enforced by experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py,
not by documentation. These tests exercise the validator END TO END as a subprocess.

Fixtures use REAL revisions from this repository's object database (r03's base and candidate), so
the LOCAL_REPO_VERIFIED path — the part of the validator that recomputes facts instead of reading
them — is exercised against the real thing rather than against strings that merely look like SHAs.

The five controls the operator required:
  * TEST 1  a repair task (baseline FAIL -> candidate PASS) is accepted;
  * TEST 2  a regression-guard task (baseline PASS -> mutation FAIL) is accepted, including the
            fully materialised ADMITTED path, using the protocol's own P7 measurement;
  * TEST 3  a worker who can reach the test oracle is rejected;
  * TEST 4  a worker who can reach the validator is rejected;
  * TEST 5  a task with no classification is rejected (never a silent pass).
Plus the boundaries the first adversarial review demanded: revision binding, evidence reachability,
duplicate ids, malformed records, the exact pending-requirement code, the disclosure-to-authority
binding, and a test that PINS THE KNOWN LIMIT of this program (declared oracle statuses are not
recomputed) so the documentation cannot drift back into over-claiming.

Run:  python3 -m unittest discover -s experiments/v1.2/tests -v
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
H2 = ROOT / "experiments" / "v1.2" / "h2-lazy-disclosure"
VALIDATOR = H2 / "harness" / "check_task_class.py"
CLASSIFICATION = H2 / "task-classification-v2.json"
REGISTRY = H2 / "task-registry.json"

# REAL revisions present in this repository: r03's base and its direct child.
LOCAL_BASE = "015780be7a3f863c05509b437e4e586b4f388794"
LOCAL_CAND = "65113de69bda6802a476eefa033cf00439d49f04"
# Two revisions this repository does NOT contain (the cross-repository candidate's pair).
FOREIGN_BASE = "4b6d182f1388e27ae33820feee1589cb0188d59b"
FOREIGN_CAND = "fa997c12e4c35fdb9267882747d2b55d13772ae2"

# Evidence sources may be given relative to the classification file's directory or to the
# repository root; fixtures live in a temporary directory, so they use the repository-root form.
SOURCE = "experiments/v1.2/h2-lazy-disclosure/precondition/n2-eligibility-measurement.md"
SOURCE_ALT = "experiments/v1.2/h2-lazy-disclosure/task-classification-v2.json"
EVIDENCE = [{"claim": "fixture", "measured": "measured facts cited from the persisted N2 report",
             "source": SOURCE}]
EXTERNAL = {"external_repository": "FlapPearLabs/fixture",
            "external_verification": "git -C <clone> rev-parse <base> <candidate> (both resolve)"}


def repair_record(**over):
    """CLASS A shaped on the r01 measurement; local binding, oracle not yet externalised."""
    rec = {
        "candidate_id": "fixture-repair",
        "source_repository": "FlapPearLabs/fixture",
        "base_sha": LOCAL_BASE,
        "candidate_sha": LOCAL_CAND,
        "sha_binding": "LOCAL_REPO_VERIFIED",
        "class": "A_REPAIR",
        "class_considered": [{"class": "A_REPAIR", "verdict": "SHAPE_SATISFIED"}],
        "class_requirements": {
            "baseline_oracle_status": "FAIL",
            "candidate_oracle_status": "PASS",
            "oracle_in_worker_scope": False,
            "oracle_authority": "PENDING_FREEZE_V2",
        },
        "disclosures": {"historical_delta_touched_oracle": True},
        "reject_triggers": [],
        "pending_requirements": ["ORACLE_EXTERNALIZATION: freeze the oracle at Freeze v2"],
        "round_admission": {"verdict": "NOT_ADMITTED", "reason_codes": ["PENDING_REQUIREMENTS_UNMET"]},
        "evidence": EVIDENCE,
    }
    rec.update(over)
    return rec


def guard_record(**over):
    """CLASS B shaped on the protocol's P7 gate probe; fully materialised and admitted."""
    rec = {
        "candidate_id": "fixture-guard",
        "source_repository": "FlapPearLabs/fixture",
        "base_sha": LOCAL_BASE,
        "candidate_sha": LOCAL_CAND,
        "sha_binding": "LOCAL_REPO_VERIFIED",
        "class": "B_REGRESSION_GUARD",
        "class_considered": [{"class": "B_REGRESSION_GUARD", "verdict": "SHAPE_SATISFIED"}],
        "class_requirements": {
            "baseline_oracle_status": "PASS",
            "mutation_oracle_status": "FAIL",
            "mutation_touches_target_predicate": True,
            "acceptance_surface_frozen": True,
            "validator_not_worker_controlled": True,
        },
        "reject_triggers": [],
        "pending_requirements": [],
        "round_admission": {"verdict": "ADMITTED_TO_H2_R2", "reason_codes": ["SHAPE_COMPLETE"]},
        "evidence": EVIDENCE,
    }
    rec.update(over)
    return rec


def document(*records):
    return {"schema": "ELIGIBILITY_SCHEMA_V2", "schema_version": "2.1.0", "records": list(records)}


def run_validator(doc, tmp: Path):
    path = tmp / "classification.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(VALIDATOR), str(path), str(ROOT)],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout + proc.stderr


class ValidatorBehaviour(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    # --- TEST 1 ------------------------------------------------------------------------------
    def test_repair_task_baseline_fail_candidate_pass_accepted(self):
        rc, out = run_validator(document(repair_record()), self.tmp)
        self.assertEqual(0, rc, out)
        self.assertIn("TASK_CLASS_VERDICT = PASS", out)

    def test_fully_materialised_repair_task_can_be_admitted(self):
        rec = repair_record()
        rec["class_requirements"]["oracle_authority"] = "FRAMEWORK_FROZEN"
        rec["disclosures"]["historical_delta_touched_oracle"] = False
        rec["pending_requirements"] = []
        rec["round_admission"] = {"verdict": "ADMITTED_TO_H2_R2",
                                  "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)
        self.assertIn("admitted_to_round=1", out)

    # --- TEST 2 ------------------------------------------------------------------------------
    def test_regression_guard_baseline_pass_mutation_fail_accepted(self):
        rc, out = run_validator(document(guard_record()), self.tmp)
        self.assertEqual(0, rc, out)
        self.assertIn("admitted_to_round=1", out)

    # --- TEST 3 ------------------------------------------------------------------------------
    def test_worker_modifies_test_oracle_rejected(self):
        rec = repair_record(reject_triggers=[{
            "trigger": "WORKER_MODIFIES_TEST_ORACLE",
            "reason_code": "ORACLE_IN_DELTA",
            "detail": "the worker's scope contains the file whose assertions produce the verdict",
        }])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("claims A_REPAIR while carrying", out)

    # --- TEST 4 ------------------------------------------------------------------------------
    def test_worker_modifies_validator_rejected(self):
        rec = guard_record(reject_triggers=[{
            "trigger": "WORKER_MODIFIES_VALIDATOR",
            "reason_code": "VALIDATOR_IN_DELTA",
            "detail": "the worker's scope contains the harness that decides the verdict",
        }])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)

    # --- TEST 5 ------------------------------------------------------------------------------
    def test_missing_classification_rejected(self):
        rec = repair_record()
        del rec["class"]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("an unclassified task is an error, never a silent pass", out)

    def test_unknown_class_rejected(self):
        rec = repair_record()
        rec["class"] = "D_MAYBE"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("D_MAYBE", out)

    # --- revision binding: the facts this program recomputes ----------------------------------
    def test_foreign_pair_cannot_be_admitted(self):
        """The exact laundering route the first review demonstrated: a record whose revisions
        cannot be checked here must never reach the aggregate."""
        rec = guard_record()
        rec["base_sha"], rec["candidate_sha"] = FOREIGN_BASE, FOREIGN_CAND
        rec["sha_binding"] = "EXTERNAL_UNVERIFIABLE_LOCALLY"
        rec.update(EXTERNAL)
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("can never be admitted", out)

    def test_external_binding_is_legal_when_not_admitted(self):
        rec = repair_record()
        rec["base_sha"], rec["candidate_sha"] = FOREIGN_BASE, FOREIGN_CAND
        rec["sha_binding"] = "EXTERNAL_UNVERIFIABLE_LOCALLY"
        rec.update(EXTERNAL)
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)

    def test_external_binding_without_verification_rejected(self):
        rec = repair_record()
        rec["base_sha"], rec["candidate_sha"] = FOREIGN_BASE, FOREIGN_CAND
        rec["sha_binding"] = "EXTERNAL_UNVERIFIABLE_LOCALLY"
        rec["external_repository"] = "FlapPearLabs/fixture"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("must record the external verification command", out)

    def test_wrong_binding_claim_rejected(self):
        """Claiming EXTERNAL for revisions this repository DOES contain is an error."""
        rec = repair_record(sha_binding="EXTERNAL_UNVERIFIABLE_LOCALLY")
        rec.update(EXTERNAL)
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("must be LOCAL_REPO_VERIFIED", out)

    def test_non_ancestor_pair_rejected(self):
        """Recomputed ancestry: 65113de does not descend from 015780be's child."""
        rec = repair_record(base_sha=LOCAL_CAND, candidate_sha=LOCAL_BASE)
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("does not descend from", out)

    # --- evidence reachability ----------------------------------------------------------------
    def test_unreachable_evidence_rejected(self):
        rec = repair_record(evidence=[{"claim": "x", "measured": "y",
                                       "source": "precondition/does-not-exist.txt"}])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("does not resolve to an existing file", out)

    def test_multi_source_evidence_accepted(self):
        rec = repair_record(evidence=[{"claim": "x", "measured": "y",
                                       "source": [SOURCE, SOURCE_ALT]}])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)

    # --- structural robustness ----------------------------------------------------------------
    def test_duplicate_candidate_id_rejected(self):
        rc, out = run_validator(document(repair_record()), self.tmp)
        self.assertEqual(0, rc, out)
        rc, out = run_validator(document(repair_record(), repair_record()), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("duplicate candidate_id", out)

    def test_missing_schema_version_rejected(self):
        doc = document(repair_record())
        del doc["schema_version"]
        rc, out = run_validator(doc, self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("schema_version is required", out)

    def test_non_object_record_is_a_structured_error(self):
        rc, out = run_validator(document(repair_record(), "not-a-record"), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("is not an object", out)
        self.assertNotIn("Traceback", out)

    def test_malformed_reason_code_rejected(self):
        rec = guard_record(reject_triggers=[{"trigger": "SELF_PROVING_HASH",
                                             "reason_code": "lower case",
                                             "detail": "x"}])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("UPPER_SNAKE", out)

    def test_pending_code_must_match_exactly(self):
        rec = repair_record()
        rec["pending_requirements"] = ["ORACLE_EXTERNALIZATION_LATER: a different obligation"]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("whose code is exactly", out)

    def test_touched_oracle_cannot_claim_frozen_authority(self):
        rec = repair_record()
        rec["class_requirements"]["oracle_authority"] = "FRAMEWORK_FROZEN"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("cannot be FRAMEWORK_FROZEN", out)

    def test_touched_oracle_requires_externalisation_pending(self):
        rec = repair_record()
        rec["pending_requirements"] = ["SOMETHING_ELSE: unrelated"]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("touched oracle requires", out)

    def test_reject_class_without_triggers_rejected(self):
        rec = repair_record()
        rec["class"] = "C_REJECT"
        rec["class_requirements"] = None
        rec["reject_triggers"] = []
        rec["class_considered"] = [{"class": "A_REPAIR", "verdict": "BLOCKED",
                                   "reason": "oracle in delta"}]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("C_REJECT requires at least one enumerated trigger", out)

    def test_reject_class_without_blocked_admissible_class_rejected(self):
        rec = repair_record()
        rec["class"] = "C_REJECT"
        rec["class_requirements"] = None
        rec["reject_triggers"] = [
            {"trigger": "BASE_CANDIDATE_NOT_COMPARABLE", "reason_code": "DIFFERENT_MATERIALS",
             "detail": "materials differ"},
            {"trigger": "OBSERVATION_COVERAGE_UNPROVEN",
             "reason_code": "NO_GATE_OBSERVES_THE_DELIVERABLE", "detail": "nothing observes it"},
        ]
        rec["class_considered"] = [{"class": "C_REJECT", "verdict": "SELF"}]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("at least one admissible class listed as BLOCKED", out)

    def test_blocked_entry_without_reason_rejected(self):
        rec = repair_record()
        rec["class"] = "C_REJECT"
        rec["class_requirements"] = None
        rec["reject_triggers"] = [{"trigger": "SELF_PROVING_HASH", "reason_code": "SELF_AUTHORED",
                                   "detail": "x"}]
        rec["class_considered"] = [{"class": "A_REPAIR", "verdict": "BLOCKED"}]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("needs a reason", out)

    # --- admission is never implicit ----------------------------------------------------------
    def test_admission_with_pending_requirements_rejected(self):
        rec = repair_record()
        rec["class_requirements"]["oracle_authority"] = "FRAMEWORK_FROZEN"
        rec["disclosures"]["historical_delta_touched_oracle"] = False
        rec["pending_requirements"] = ["DELIVERY_DELTA_MEASUREMENT: not measured yet"]
        rec["round_admission"] = {"verdict": "ADMITTED_TO_H2_R2", "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("pending requirements remain", out)

    def test_evidence_required(self):
        rc, out = run_validator(document(repair_record(evidence=[])), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("evidence is required", out)

    def test_repair_claim_without_fail_baseline_rejected(self):
        rec = repair_record()
        rec["class_requirements"]["baseline_oracle_status"] = "PASS"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("baseline_oracle_status must be 'FAIL'", out)

    def test_regression_guard_without_mutation_fail_rejected(self):
        rec = guard_record()
        rec["class_requirements"]["mutation_oracle_status"] = "PASS"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)

    # --- THE KNOWN BOUNDARY, PINNED -----------------------------------------------------------
    def test_known_boundary_declared_statuses_are_not_recomputed(self):
        """This test PINS THE LIMIT of the validator, so the documentation cannot drift back into
        claiming more than the program does.

        A record can use real revisions and still DECLARE oracle statuses the validator cannot
        recompute: it has no way to re-run a candidate's oracle. Such a record is accepted (it is
        internally consistent and consistent with every fact this repository can check), and that
        acceptance is NOT a proof that the repair happened. The truth of the statuses is an
        out-of-band obligation carried by the evidence review.

        If this test ever starts failing, the boundary moved — update the module docstring, the
        schema's enforcement-surface section, and this test together.
        """
        rec = repair_record()
        rec["class_requirements"]["oracle_authority"] = "FRAMEWORK_FROZEN"
        rec["disclosures"]["historical_delta_touched_oracle"] = False
        rec["class_requirements"]["baseline_oracle_status"] = "FAIL"   # declared, not recomputed
        rec["class_requirements"]["candidate_oracle_status"] = "PASS"  # declared, not recomputed
        rec["pending_requirements"] = []
        rec["round_admission"] = {"verdict": "NOT_ADMITTED",
                                  "reason_codes": ["CLASSIFICATION_ONLY"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)
        self.assertIn("oracle statuses are declared, not recomputed", out)


class ShippedClassification(unittest.TestCase):
    """The repository's own classification must obey the schema it declares."""

    def test_shipped_classification_validates(self):
        proc = subprocess.run([sys.executable, str(VALIDATOR), str(CLASSIFICATION), str(ROOT)],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("TASK_CLASS_VERDICT = PASS", proc.stdout)

    def test_shipped_classification_classes_bindings_and_admission(self):
        doc = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
        by_id = {r["candidate_id"]: r for r in doc["records"]}
        self.assertEqual(3, len(by_id))
        r01 = by_id["r01-zhihu-t14-async-seam-mismatch"]
        r03 = by_id["r03-governance-static-gate-adoption"]
        r06 = by_id["r06-governance-zcode-adapter-reference"]
        self.assertEqual("A_REPAIR", r01["class"])
        self.assertEqual("C_REJECT", r03["class"])
        self.assertEqual("C_REJECT", r06["class"])
        # the cross-repository candidate can never be admitted from this repository
        self.assertEqual("EXTERNAL_UNVERIFIABLE_LOCALLY", r01["sha_binding"])
        self.assertEqual("LOCAL_REPO_VERIFIED", r03["sha_binding"])
        self.assertEqual("LOCAL_REPO_VERIFIED", r06["sha_binding"])
        for rec in (r01, r03, r06):
            self.assertEqual("NOT_ADMITTED", rec["round_admission"]["verdict"])
        codes03 = {t["trigger"] for t in r03["reject_triggers"]}
        codes06 = {t["trigger"] for t in r06["reject_triggers"]}
        self.assertIn("OBSERVATION_COVERAGE_UNPROVEN", codes03)
        self.assertIn("ACCEPTANCE_SURFACE_IN_WORKER_SCOPE", codes03)
        self.assertEqual({"OBSERVATION_COVERAGE_UNPROVEN"}, codes06)

    def test_v2_rejects_the_registered_task_t02_as_specified(self):
        """The claim that this schema is not tailored to admit existing tasks, made mechanical.

        Two facts are read from the frozen registry, not asserted here:
          * `ruff.toml` is inside t02's scope prefixes, so the file that decides the linter's
            verdict is a worker deliverable (ACCEPTANCE_SURFACE_IN_WORKER_SCOPE);
          * the "select is non-empty and correctness-class" requirement is a JUDGMENT entry, i.e.
            prose, so nothing mechanical pins the rule selection (OBSERVATION_COVERAGE_UNPROVEN
            for the narrowing direction).
        A t02-shaped record that claims the admissible class A_REPAIR while carrying those two
        triggers must be refused. If a future change makes this pass, the schema has been bent.
        """
        reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
        t02 = next(t for t in reg["tasks"] if t["task_id"] == "t02")
        self.assertIn("ruff.toml", t02["scope"]["allow_prefixes"])
        select_entry = [e["cmd"] for e in t02["acceptance"]["mechanical"] if "select" in e["cmd"]]
        self.assertTrue(select_entry)
        self.assertFalse(select_entry[0].startswith(("{PY}", "{GIT}", "{HARNESS}",
                                                     "PUBLIC_RELEASE=1")),
                         "the select requirement must still be a non-executable (JUDGMENT) entry; "
                         "if it became mechanical this test's premise changed")

        rec = repair_record()
        rec["candidate_id"] = "t02-as-registered"
        rec["class"] = "A_REPAIR"
        rec["reject_triggers"] = [
            {"trigger": "ACCEPTANCE_SURFACE_IN_WORKER_SCOPE",
             "reason_code": "VERDICT_PRODUCING_BYTES_ARE_DELIVERABLES",
             "detail": "ruff.toml is in t02's scope prefixes"},
            {"trigger": "OBSERVATION_COVERAGE_UNPROVEN",
             "reason_code": "SPECIMEN_SET_DOES_NOT_COVER_THE_PREDICATE",
             "detail": "the select requirement is a JUDGMENT entry, so narrowing is unpinned"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            rc, out = run_validator(document(rec), Path(tmp))
        self.assertEqual(1, rc, out)
        self.assertIn("claims A_REPAIR while carrying", out)

    def test_classification_is_not_a_frozen_artifact(self):
        """The schema revision must not silently become part of the frozen surface: the freeze
        hashes cover task-registry / run plan / manifest / scoring / routes / protocol, and the
        classification is deliberately NOT among them."""
        manifest = json.loads((H2 / "variant-manifest.json").read_text(encoding="utf-8"))
        hashed = set(manifest["freeze"].get("HASHED_FILES", {}).values())
        self.assertNotIn("task-classification-v2.json", hashed)
        self.assertFalse(any("eligibility-schema-v2" in v for v in hashed))


if __name__ == "__main__":
    unittest.main()
