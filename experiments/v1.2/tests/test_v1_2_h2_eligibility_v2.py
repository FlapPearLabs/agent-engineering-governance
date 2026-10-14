"""Material checks for ELIGIBILITY_SCHEMA_V2 (H2 task-classification revision, node N2.1).

The schema revision is enforced by experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py,
not by documentation. These tests exercise the validator END TO END as a subprocess, with fixtures
built from the MEASURED facts of the replay corpus:

  * TEST 1  a repair task (baseline FAIL -> candidate PASS) is accepted;
  * TEST 2  a regression-guard task (baseline PASS -> mutation FAIL) is accepted, using the
            protocol's own P7 measurement (clean tree -> ruff rc=0; injected F841 -> ruff rc=1);
  * TEST 3  a worker who can reach the test oracle is rejected;
  * TEST 4  a worker who can reach the validator is rejected;
  * TEST 5  a task with no classification is rejected (never a silent pass);
  * plus the boundary cases the operator enumerated: self-proving hash, unproven observation
    coverage, admission with open pending requirements, C_REJECT without triggers, unknown class,
    and a repair claim whose baseline is not FAIL.

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

SHA_A = "4b6d182f1388e27ae33820feee1589cb0188d59b"
SHA_B = "fa997c12e4c35fdb9267882747d2b55d13772ae2"

EVIDENCE = [{"claim": "fixture", "measured": "measured facts cited from the N2 report",
             "source": "precondition/n2-eligibility-measurement.md"}]


def repair_record(**over):
    """A CLASS A record shaped on the r01 measurement (baseline 508/509 with the target file red,
    candidate 539/539)."""
    rec = {
        "candidate_id": "fixture-repair",
        "source_repository": "FlapPearLabs/fixture",
        "base_sha": SHA_A,
        "candidate_sha": SHA_B,
        "class": "A_REPAIR",
        "class_considered": [{"class": "A_REPAIR", "verdict": "SHAPE_SATISFIED_PENDING_MATERIALISATION"}],
        "class_requirements": {
            "baseline_oracle_status": "FAIL",
            "candidate_oracle_status": "PASS",
            "oracle_in_worker_scope": False,
            "oracle_authority": "PENDING_FREEZE_V2",
        },
        "reject_triggers": [],
        "pending_requirements": ["ORACLE_EXTERNALIZATION: freeze the oracle at Freeze v2"],
        "round_admission": {"verdict": "NOT_ADMITTED", "reason_codes": ["PENDING_REQUIREMENTS_UNMET"]},
        "evidence": EVIDENCE,
    }
    rec.update(over)
    return rec


def guard_record(**over):
    """A CLASS B record shaped on the protocol's P7 gate probe: the clean tree passes the frozen
    ruff gate and an injected F841 turns it red."""
    rec = {
        "candidate_id": "fixture-guard",
        "source_repository": "FlapPearLabs/fixture",
        "base_sha": SHA_A,
        "candidate_sha": SHA_B,
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
        "round_admission": {
            "verdict": "ADMITTED_TO_H2_R2",
            "reason_codes": ["SHAPE_COMPLETE"],
        },
        "evidence": EVIDENCE,
    }
    rec.update(over)
    return rec


def document(*records):
    return {"schema": "ELIGIBILITY_SCHEMA_V2", "schema_version": "2.0.0", "records": list(records)}


def run_validator(doc, tmp: Path):
    path = tmp / "classification.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    proc = subprocess.run([sys.executable, str(VALIDATOR), str(path)],
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

    # --- further enumerated rejection triggers ------------------------------------------------
    def test_self_proving_hash_rejected(self):
        rec = guard_record(reject_triggers=[{
            "trigger": "SELF_PROVING_HASH",
            "reason_code": "HASH_OVER_WORKER_WRITABLE_BYTES",
            "detail": "the marker hash is computed from the worker's own receipt",
        }])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)

    def test_observation_coverage_unproven_rejected(self):
        rec = guard_record(reject_triggers=[{
            "trigger": "OBSERVATION_COVERAGE_UNPROVEN",
            "reason_code": "SPECIMEN_SET_DOES_NOT_COVER_THE_PREDICATE",
            "detail": "a single-specimen probe is satisfied by narrowing the rule set",
        }])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)

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

    # --- admission is never implicit ----------------------------------------------------------
    def test_admission_with_pending_requirements_rejected(self):
        rec = repair_record()
        rec["class_requirements"]["oracle_authority"] = "FRAMEWORK_FROZEN"
        rec["pending_requirements"] = ["DELIVERY_DELTA_MEASUREMENT: not measured yet"]
        rec["round_admission"] = {"verdict": "ADMITTED_TO_H2_R2", "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("pending requirements remain", out)

    def test_admission_with_pending_oracle_authority_rejected(self):
        rec = repair_record()
        rec["round_admission"] = {"verdict": "ADMITTED_TO_H2_R2", "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)

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

    def test_evidence_required(self):
        rc, out = run_validator(document(repair_record(evidence=[])), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("evidence is required", out)


class ShippedClassification(unittest.TestCase):
    """The repository's own classification must obey the schema it declares."""

    def test_shipped_classification_validates(self):
        proc = subprocess.run([sys.executable, str(VALIDATOR), str(CLASSIFICATION)],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("TASK_CLASS_VERDICT = PASS", proc.stdout)

    def test_shipped_classification_classes_and_admission(self):
        doc = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
        by_id = {r["candidate_id"]: r for r in doc["records"]}
        self.assertEqual(3, len(by_id))
        r01 = by_id["r01-zhihu-t14-async-seam-mismatch"]
        r03 = by_id["r03-governance-static-gate-adoption"]
        r06 = by_id["r06-governance-zcode-adapter-reference"]
        self.assertEqual("A_REPAIR", r01["class"])
        self.assertEqual("C_REJECT", r03["class"])
        self.assertEqual("C_REJECT", r06["class"])
        # no task is admitted to the round by this node: admission is a Freeze-v2 decision
        for rec in (r01, r03, r06):
            self.assertEqual("NOT_ADMITTED", rec["round_admission"]["verdict"])
        # the two rejected candidates must name the measured trigger that rejects them
        codes03 = {t["trigger"] for t in r03["reject_triggers"]}
        codes06 = {t["trigger"] for t in r06["reject_triggers"]}
        self.assertIn("OBSERVATION_COVERAGE_UNPROVEN", codes03)
        self.assertIn("ACCEPTANCE_SURFACE_IN_WORKER_SCOPE", codes03)
        self.assertEqual({"OBSERVATION_COVERAGE_UNPROVEN"}, codes06)

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
