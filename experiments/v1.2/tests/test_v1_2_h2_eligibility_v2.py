"""Material checks for ELIGIBILITY_SCHEMA_V2 (H2 task-classification revision, node N2.1).

The schema revision is enforced by experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py,
not by documentation. These tests exercise the validator END TO END as a subprocess.

Fixtures are bound to REAL replay-corpus pairs, because the validator now recomputes identity: a
record must name a corpus case and carry that case's revision pair. The pair used for the
"accepted" fixtures is r06's, whose delta changes no test file and no validator (so no trigger is
derived from the diff); the pair used for the derived-trigger tests is r03's, whose delta changes
four test files and two validators.

The five controls the operator required:
  * TEST 1  a repair task (baseline FAIL -> candidate PASS) is accepted;
  * TEST 2  a regression-guard task (baseline PASS -> mutation FAIL) is accepted, including the
            fully materialised request path, using the protocol's own P7 measurement;
  * TEST 3  a worker who can reach the test oracle is rejected;
  * TEST 4  a worker who can reach the validator is rejected;
  * TEST 5  a task with no classification is rejected (never a silent pass).
Plus the boundaries two adversarial review rounds demanded — and, ported from the second review,
the LAUNDERING VARIANTS as permanent regression tests: the review of 5aa079f demonstrated that a
six-field edit of the shipped r03 record was counted as an admission. Every variant of that attack
must now be refused.

Run:  python3 -m unittest discover -s experiments/v1.2/tests -v
"""

from __future__ import annotations

import copy
import importlib.util
import json
import os
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

CASE_R06 = "r06-governance-zcode-adapter-reference"
CASE_R02 = "r02-governance-review-evidence-interface"
BASE_R02 = "e1da1541eb2b11f1e44f972409abde701496f4b6"
CAND_R02 = "2ed08f6f7ddf58b234b54afb8334e6fae32cd768"
CASE_R03 = "r03-governance-static-gate-adoption"
CASE_R01 = "r01-zhihu-t14-async-seam-mismatch"
# r06's pair: resolves locally, candidate descends from base, and the delta touches neither a test
# file nor a validator (so no trigger is derived from it).
BASE_CLEAN = "af4df6ae706394db5f9dec313993312392aeb516"
CAND_CLEAN = "069f8be26cc04bb4f9bf3428c1e23b310debb984"
# r03's pair: resolves locally, and the delta touches four test files and two validators.
BASE_TOUCHED = "015780be7a3f863c05509b437e4e586b4f388794"
CAND_TOUCHED = "65113de69bda6802a476eefa033cf00439d49f04"
# r01's pair: does NOT resolve in this repository.
FOREIGN_BASE = "4b6d182f1388e27ae33820feee1589cb0188d59b"
FOREIGN_CAND = "fa997c12e4c35fdb9267882747d2b55d13772ae2"

SOURCE = "experiments/v1.2/h2-lazy-disclosure/precondition/n2-eligibility-measurement.md"
SOURCE_ALT = "experiments/v1.2/h2-lazy-disclosure/task-classification-v2.json"
EVIDENCE = [{"claim": "fixture", "measured": "measured facts cited from the persisted N2 report",
             "source": SOURCE}]
EXTERNAL = {"external_repository": "FlapPearLabs/fixture",
            "external_verification": "git -C <clone> rev-parse <base> <candidate> (both resolve)"}


def repair_record(**over):
    """CLASS A on r06's pair; oracle not yet externalised, so the request is not valid."""
    rec = {
        "candidate_id": "fixture-repair",
        "corpus_case_id": CASE_R06,
        "source_repository": "FlapPearLabs/agent-engineering-governance",
        "base_sha": BASE_CLEAN,
        "candidate_sha": CAND_CLEAN,
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


def repair_record_accepted(**over):
    """CLASS A on r02's pair — the pair whose delta ADDS its acceptance surface and whose
    acceptance genuinely FAILS against the unfixed base (measured: base_rc=1, cand_rc=0). This is
    the shape a repair task actually has, and it is the only shape the recomputation can support:
    a FROZEN acceptance exists identically at both revisions, so on a landed pair it is green at
    the base and cannot move."""
    over.setdefault("corpus_case_id", CASE_R02)
    over.setdefault("base_sha", BASE_R02)
    over.setdefault("candidate_sha", CAND_R02)
    over.setdefault("disclosures", {"historical_delta_touched_oracle": False,
                                    "historical_delta_touched_validator": False})
    over.setdefault("pending_requirements", [])
    rec = repair_record(**over)
    rec["class_requirements"]["oracle_authority"] = "DELTA_AUTHORED_DISCRIMINATING"
    rec["class_requirements"]["oracle_in_worker_scope"] = True
    rec["round_admission"] = {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]}
    return rec


def guard_record(**over):
    """CLASS B on r06's pair, fully materialised so it can carry a valid request."""
    rec = {
        "candidate_id": "fixture-guard",
        "corpus_case_id": CASE_R06,
        "source_repository": "FlapPearLabs/agent-engineering-governance",
        "base_sha": BASE_CLEAN,
        "candidate_sha": CAND_CLEAN,
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
        "round_admission": {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]},
        "evidence": EVIDENCE,
    }
    rec.update(over)
    return rec


def document(*records):
    return {"schema": "ELIGIBILITY_SCHEMA_V2", "schema_version": "2.8.10", "records": list(records)}


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
        """TEST 1. The acceptance is the candidate revision's own and it is executed against the
        unfixed base, where it FAILS — that is the lifecycle, recomputed."""
        rc, out = run_validator(document(repair_record_accepted()), self.tmp)
        self.assertEqual(0, rc, out)
        self.assertIn("TASK_CLASS_VERDICT = PASS", out)
        self.assertIn("verdict=FAIL_TO_PASS", out)

    def test_fully_materialised_repair_task_can_request(self):
        rc, out = run_validator(document(repair_record_accepted()), self.tmp)
        self.assertEqual(0, rc, out)
        self.assertIn("valid_requests=1", out)

    # --- TEST 2 ------------------------------------------------------------------------------
    def test_regression_guard_is_refused_when_the_mutation_does_not_bite(self):
        """TEST 2, in the form the corpus can actually produce. A B_REGRESSION_GUARD claim says a
        controlled mutation breaks the acceptance. The mutation is derived from the pair itself —
        the candidate tree with every path the delta ADDS removed — so it only means anything when
        a FROZEN acceptance actually observes the deliverable. On r06 it does not: the two frozen
        validators report the same verdict with the adapters present and removed, which is the
        measured fact the corpus already recorded as an observation-coverage gap."""
        rc, out = run_validator(document(guard_record()), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("MUTATION_DOES_NOT_BITE", out)
        self.assertNotIn("valid_requests=1", out)

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

    def test_unknown_class_does_not_mask_other_defects(self):
        """The first version returned early on an unknown class, so a record with a dozen problems
        reported one. Every defect must surface."""
        rec = repair_record()
        rec["class"] = "D_MAYBE"
        rec["reject_triggers"] = [{"trigger": "NOPE", "reason_code": "x", "detail": ""}]
        rec["round_admission"] = {"verdict": "REQUEST_VALID"}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("D_MAYBE", out)
        self.assertIn("unknown trigger code", out)
        self.assertIn("only ['A_REPAIR', 'B_REGRESSION_GUARD'] may carry a valid request", out)
        self.assertGreaterEqual(out.count("  ERROR "), 4,
                                "an unknown class must not mask the record's other defects")

    # --- identity binding ---------------------------------------------------------------------
    def test_borrowed_corpus_identity_rejected(self):
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R06
        rec["base_sha"], rec["candidate_sha"] = BASE_TOUCHED, CAND_TOUCHED   # r03's real pair
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("does not match the corpus case", out)

    def test_unknown_corpus_case_rejected(self):
        rec = repair_record(corpus_case_id="r99-invented-case")
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("is not a case in", out)

    def test_missing_corpus_case_id_rejected(self):
        rec = repair_record()
        del rec["corpus_case_id"]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("corpus_case_id is required", out)

    # --- derived triggers (read from the diff, not declared) ----------------------------------
    def test_derived_trigger_must_be_declared(self):
        rec = guard_record()
        rec["corpus_case_id"] = CASE_R03
        rec["base_sha"], rec["candidate_sha"] = BASE_TOUCHED, CAND_TOUCHED
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("DERIVED from the git diff", out)
        self.assertIn("WORKER_MODIFIES_TEST_ORACLE", out)

    def test_full_externalisation_clears_the_derived_trigger(self):
        # the basis on this pair is the ADDED acceptance, so the derived authority applies
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R03
        rec["base_sha"], rec["candidate_sha"] = BASE_TOUCHED, CAND_TOUCHED
        rec["externalized_paths"] = [
            "adapters/zcode/tests/test_project_continuity.py",
            "scripts/tests/test_p1_t12_shared_file_single_writer.py",
            "scripts/tests/test_p1_t17_static_gate_framework_semantics.py",
            "scripts/tests/test_review_evidence_contract.py",
            "scripts/validate_governance.py",
            "scripts/validate_project_state.py",
        ]
        rec["class_requirements"]["oracle_in_worker_scope"] = True
        rec["class_requirements"]["oracle_authority"] = "DELTA_AUTHORED_DISCRIMINATING"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)
        self.assertIn("DERIVED from the git diff", run_validator(         # the control
            document({**rec, "externalized_paths": []}), self.tmp)[1])

    # --- round-3 rules: the corpus is the identity root, so it is pinned and scoped -------------
    def test_schema_version_must_equal_the_implemented_one(self):
        for bogus in ("2.7.0", "0.0.1", "banana"):
            doc = document(repair_record())
            doc["schema_version"] = bogus
            rc, out = run_validator(doc, self.tmp)
            self.assertEqual(1, rc, f"{bogus} must be refused\n{out}")
            self.assertIn("this validator implements", out)

    def test_source_repository_must_match_the_corpus_case(self):
        rec = repair_record(source_repository="FlapPearLabs/zhihu-grabber-toolkit")
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("source_repository", out)

    def test_two_records_over_the_same_corpus_case_rejected(self):
        other = repair_record()
        other["candidate_id"] = "second-record"
        rc, out = run_validator(document(repair_record(), other), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("two records classify the same corpus case", out)

    def test_evidence_outside_the_repository_rejected(self):
        rec = repair_record(evidence=[{"claim": "x", "measured": "y", "source": "/etc/hosts"}])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("does not resolve to an existing file", out)

    def test_externalized_path_must_be_in_the_delta(self):
        rec = repair_record()
        rec["externalized_paths"] = ["no/such/file.py"]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("the delta does not change", out)

    def test_malformed_class_considered_rejected(self):
        rec = repair_record()
        rec["class_considered"] = "not-a-list"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("class_considered", out)

    def test_class_considered_entry_needs_a_known_class_and_verdict(self):
        rec = repair_record()
        rec["class_considered"] = [{"class": "Z_UNKNOWN", "verdict": ""}]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("known class", out)

    def test_disclosure_must_not_contradict_the_derived_validator_fact(self):
        """Round-5 F4: the disclosure field was never read, so a record could declare that the delta
        did not touch a validator while the delta provably does."""
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R03
        rec["base_sha"], rec["candidate_sha"] = BASE_TOUCHED, CAND_TOUCHED
        rec["disclosures"] = {"historical_delta_touched_validator": False}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("contradicts the object database", out)

    def test_class_considered_must_name_the_record_own_class(self):
        """Round-5 F5: a B_REGRESSION_GUARD record could list only A_REPAIR and still be called
        internally consistent."""
        rec = guard_record()
        rec["class_considered"] = [{"class": "A_REPAIR", "verdict": "SHAPE_SATISFIED"}]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("does not mention the record's own class", out)

    def test_reject_class_need_not_list_itself(self):
        """The own-class rule is scoped to admissible claims: a C_REJECT lists the admissible
        classes it blocked, and the reject class is the outcome rather than an option considered."""
        rec = repair_record()
        rec["class"] = "C_REJECT"
        rec["class_requirements"] = None
        rec["reject_triggers"] = [{"trigger": "OBSERVATION_COVERAGE_UNPROVEN",
                                   "reason_code": "NO_GATE_OBSERVES_THE_DELIVERABLE",
                                   "detail": "nothing observes it"}]
        rec["class_considered"] = [{"class": "A_REPAIR", "verdict": "BLOCKED",
                                   "reason": "no oracle"}, ]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)

    def test_declared_trigger_does_not_excuse_a_contradictory_disclosure(self):
        """Round-6 F1: the check sat after the declaration short-circuit, so declaring the trigger —
        the only shape that can carry this contradiction — made the rule dead."""
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R03
        rec["base_sha"], rec["candidate_sha"] = BASE_TOUCHED, CAND_TOUCHED
        rec["class"] = "C_REJECT"
        rec["class_requirements"] = None
        rec["disclosures"] = {"historical_delta_touched_validator": False}
        rec["reject_triggers"] = [
            {"trigger": "WORKER_MODIFIES_VALIDATOR", "reason_code": "VALIDATOR_IN_DELTA",
             "detail": "declared"},
            {"trigger": "WORKER_MODIFIES_TEST_ORACLE", "reason_code": "TEST_ORACLE_IN_DELTA",
             "detail": "declared"},
        ]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("contradicts the object database", out)

    def test_own_class_marked_blocked_rejected(self):
        """Round-6 F2: the own-class rule matched the NAME only, so a record could list its own
        class as BLOCKED — even with a valid request."""
        rec = guard_record()
        rec["class_considered"] = [{"class": "B_REGRESSION_GUARD", "verdict": "BLOCKED"}]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("not an affirmative claim", out)

    def test_own_class_verdict_synonym_rejected(self):
        """Round-7 F1: comparing against the literal "BLOCKED" let a synonym stand in for it."""
        for synonym in ("NOT_APPLICABLE", "BLOCKED_PENDING_FREEZE_V2", "declined"):
            rec = guard_record()
            rec["class_considered"] = [{"class": "B_REGRESSION_GUARD", "verdict": synonym}]
            rc, out = run_validator(document(rec), self.tmp)
            self.assertEqual(1, rc, f"{synonym!r} must not pass\n{out}")
            self.assertIn("not an affirmative claim", out)

    def test_non_dict_disclosures_is_a_structured_error(self):
        """Round-7 F2: a string value raised an uncaught AttributeError instead of an error."""
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R03
        rec["base_sha"], rec["candidate_sha"] = BASE_TOUCHED, CAND_TOUCHED
        rec["disclosures"] = "a string where an object belongs"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("disclosures must be an object", out)
        self.assertIn("TASK_CLASS_VERDICT = FAIL", out)
        self.assertNotIn("Traceback", out)

    def test_disclosure_must_not_contradict_the_derived_oracle_fact(self):
        """Round-7 F3: the cross-check existed on the validator axis only."""
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R03
        rec["base_sha"], rec["candidate_sha"] = BASE_TOUCHED, CAND_TOUCHED
        rec["disclosures"] = {"historical_delta_touched_oracle": False}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("did not touch the test oracle", out)

    def test_non_boolean_disclosure_value_rejected(self):
        """Round-8 F1: the cross-checks compare with `is False`, so a falsey NON-BOOLEAN value
        ("false", "no", 0, [], "") silently disabled them."""
        for bogus in ("false", "no", 0, [], "", None):
            rec = repair_record()
            rec["disclosures"] = {"historical_delta_touched_validator": bogus}
            rc, out = run_validator(document(rec), self.tmp)
            self.assertEqual(1, rc, f"{bogus!r} must not stand in for a boolean\\n{out}")
            self.assertIn("must be a boolean when present", out)

    def test_boolean_disclosure_values_still_accepted(self):
        rec = repair_record_accepted()
        rec["disclosures"] = {"historical_delta_touched_oracle": False,
                              "historical_delta_touched_validator": True}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)

    def test_pending_verdict_requires_pending_requirements(self):
        """Round-8 F2: a record could describe its class as unmaterialised while listing nothing
        outstanding."""
        rec = guard_record()
        rec["class_considered"] = [{"class": "B_REGRESSION_GUARD",
                                   "verdict": "SHAPE_SATISFIED_PENDING_MATERIALISATION"}]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("nothing outstanding", out)

    # --- out-of-repo pairs --------------------------------------------------------------------
    def test_foreign_pair_cannot_carry_a_valid_request(self):
        rec = guard_record()
        rec["corpus_case_id"] = CASE_R01
        rec["base_sha"], rec["candidate_sha"] = FOREIGN_BASE, FOREIGN_CAND
        rec["sha_binding"] = "EXTERNAL_UNVERIFIABLE_LOCALLY"
        rec.update(EXTERNAL)
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("locally verifiable revision pair", out)

    def test_external_binding_is_legal_when_no_request_is_made(self):
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R01
        rec["source_repository"] = "FlapPearLabs/zhihu-grabber-toolkit"   # what the corpus binds
        rec["base_sha"], rec["candidate_sha"] = FOREIGN_BASE, FOREIGN_CAND
        rec["sha_binding"] = "EXTERNAL_UNVERIFIABLE_LOCALLY"
        rec.update(EXTERNAL)
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)

    def test_external_binding_without_verification_rejected(self):
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R01
        rec["source_repository"] = "FlapPearLabs/zhihu-grabber-toolkit"   # what the corpus binds
        rec["base_sha"], rec["candidate_sha"] = FOREIGN_BASE, FOREIGN_CAND
        rec["sha_binding"] = "EXTERNAL_UNVERIFIABLE_LOCALLY"
        rec["external_repository"] = "FlapPearLabs/fixture"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("must record the external verification command", out)

    def test_wrong_binding_claim_rejected(self):
        rec = repair_record(sha_binding="EXTERNAL_UNVERIFIABLE_LOCALLY")
        rec.update(EXTERNAL)
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("must be LOCAL_REPO_VERIFIED", out)

    # --- evidence reachability ----------------------------------------------------------------
    def test_unreachable_evidence_rejected(self):
        rec = repair_record(evidence=[{"claim": "x", "measured": "y",
                                       "source": "precondition/does-not-exist.txt"}])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("does not resolve to an existing file", out)

    def test_multi_source_evidence_accepted(self):
        rec = repair_record_accepted(evidence=[{"claim": "x", "measured": "y",
                                                "source": [SOURCE, SOURCE_ALT]}])
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)

    # --- structural robustness ----------------------------------------------------------------
    def test_duplicate_candidate_id_rejected(self):
        rc, out = run_validator(document(repair_record(), repair_record()), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("duplicate candidate_id", out)

    def test_missing_schema_version_rejected(self):
        doc = document(repair_record())
        del doc["schema_version"]
        rc, out = run_validator(doc, self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("this validator implements", out)

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

    # --- requests are never implicit ----------------------------------------------------------
    def test_request_with_pending_requirements_rejected(self):
        rec = repair_record()
        rec["class_requirements"]["oracle_authority"] = "FRAMEWORK_FROZEN"
        rec["disclosures"]["historical_delta_touched_oracle"] = False
        rec["pending_requirements"] = ["DELIVERY_DELTA_MEASUREMENT: not measured yet"]
        rec["round_admission"] = {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("pending requirements remain", out)

    def test_evidence_required(self):
        rc, out = run_validator(document(repair_record(evidence=[])), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("evidence is required", out)

    def test_repair_claim_without_fail_baseline_rejected(self):
        """The claim is no longer defeated by a shape rule on the declared status: the status is
        bound to the recomputation, and the transition itself is what fails."""
        rec = repair_record_accepted()
        rec["class_requirements"]["baseline_oracle_status"] = "PASS"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("declared baseline_oracle_status='PASS'", out)
        self.assertIn("recomputed 'FAIL'", out)

    def test_regression_guard_without_mutation_fail_rejected(self):
        rec = guard_record()
        rec["class_requirements"]["mutation_oracle_status"] = "PASS"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)

    # --- THE RESIDUAL BOUNDARY, PINNED --------------------------------------------------------
    def test_residual_boundary_is_the_class_not_the_statuses(self):
        """This test PINS WHAT IS STILL NOT RECOMPUTED, so the documentation cannot drift back
        into claiming more than the program does.

        What changed in 2.8.0: the acceptance lifecycle statuses ARE now recomputed — they are
        executed, and the record's declared values are bound to the measurement (see
        RecomputedTransition). What is still NOT recomputed is the CLASS itself: the program can
        prove that a pair's acceptance moves as A_REPAIR claims, but nothing in the repository
        says a given change WAS a repair; that remains the classification's assertion, judged by
        the round freeze plus review. The verdict vocabulary still has no "admitted" value.

        If this test ever starts failing, the boundary moved — update the module docstring, the
        schema's enforcement-surface section, and this test together.
        """
        rec = repair_record_accepted()
        rec["round_admission"] = {"verdict": "NOT_ADMITTED",
                                  "reason_codes": ["CLASSIFICATION_ONLY"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)
        self.assertIn("valid request is NOT an admission", out)
        self.assertIn("verdict=FAIL_TO_PASS", out)       # the transition IS recomputed
        self.assertIn("request=NOT_ADMITTED", out)       # the class grant is NOT



class RecomputedTransition(unittest.TestCase):
    """The class claim is a state-transition claim, so the transition is RECOMPUTED by running the
    pair's own acceptance surfaces against materialised trees. These tests are the two the operator
    asked for: the round-8 reviewer's r06 laundering reproduction, and a positive discriminative
    control that must actually reach the predicate (not pass on some earlier guard, and not be
    blocked by an unrelated one).

    They are slower than the rest of the suite because they run real processes in real git
    worktrees; that is the point, and it is the only place the schema touches the world.
    """

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)

    def tearDown(self):
        self._tmpdir.cleanup()

    # ---- requirement 5: the reviewer's r06 laundering, reproduced exactly -------------------
    def test_r06_laundering_reproduction_is_refused(self):
        """Round-9 Finding 1: reclassify the shipped r06 record to B_REGRESSION_GUARD, clear its
        triggers, ask for a valid request, and leave its evidence untouched — the edit falsifies
        nothing at the record level, and under 2.7.0 it was ACCEPTED (valid_requests=1)."""
        ship = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
        rec = copy.deepcopy(next(r for r in ship["records"]
                                 if r["candidate_id"].startswith("r06")))
        for r in ship["records"]:                       # citations resolvable from anywhere
            r["evidence"] = [dict(e, source=["experiments/v1.2/h2-lazy-disclosure/" + x
                                             if not x.startswith("experiments") else x
                                             for x in (e["source"] if isinstance(e["source"], list)
                                                       else [e["source"]])])
                             for e in r["evidence"]]
        rec = copy.deepcopy(next(r for r in ship["records"]
                                 if r["candidate_id"].startswith("r06")))
        rec["class"] = "B_REGRESSION_GUARD"
        rec["class_considered"] = [{"class": "B_REGRESSION_GUARD", "verdict": "SHAPE_SATISFIED"}]
        rec["class_requirements"] = {
            "baseline_oracle_status": "PASS", "mutation_oracle_status": "FAIL",
            "mutation_touches_target_predicate": True, "acceptance_surface_frozen": True,
            "validator_not_worker_controlled": True}
        rec["reject_triggers"] = []
        rec["round_admission"] = {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        # refused by the RECOMPUTED transition, not by a shape rule and not by a missing field
        self.assertIn("not supported by execution (MUTATION_DOES_NOT_BITE)", out)
        self.assertIn("recomputed, not read from the record", out)
        self.assertIn("DELTA_FROZEN", out)          # the frozen surfaces and their verdicts
        self.assertNotIn("valid_requests=1", out)

    # ---- requirement 6: the positive discriminative control ---------------------------------
    def test_positive_control_reaches_the_discriminative_predicate(self):
        """A real pinned A_REPAIR case whose acceptance genuinely FAILS against the unfixed base
        and PASSES at the candidate must form a VALID REQUEST — and the run must REPORT the
        predicate, so a pass that came from some other guard cannot be mistaken for this one."""
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R02
        rec["base_sha"], rec["candidate_sha"] = BASE_R02, CAND_R02
        rec["disclosures"] = {"historical_delta_touched_oracle": False,
                              "historical_delta_touched_validator": False}
        rec["pending_requirements"] = []
        rec["class_requirements"]["oracle_authority"] = "DELTA_AUTHORED_DISCRIMINATING"
        rec["class_requirements"]["oracle_in_worker_scope"] = True
        rec["round_admission"] = {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(0, rc, out)
        self.assertIn("valid_requests=1", out)
        # the predicate itself, with the acceptance that carried it and its provenance
        self.assertIn("TRANSITION", out)
        self.assertIn("class=A_REPAIR verdict=FAIL_TO_PASS", out)
        self.assertIn("DELTA_ADDED", out)
        self.assertIn("base_rc=1 cand_rc=0", out)

    def test_positive_control_is_not_a_shape_only_pass(self):
        """Same pair, but declared as A_REPAIR without the recomputed basis: the discriminating
        acceptance is DELTA_ADDED, so the authority must be the derived one. A record that keeps
        claiming PENDING_FREEZE_V2 (or FRAMEWORK_FROZEN) is bound to the recomputed provenance."""
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R02
        rec["base_sha"], rec["candidate_sha"] = BASE_R02, CAND_R02
        rec["disclosures"] = {"historical_delta_touched_oracle": False,
                              "historical_delta_touched_validator": False}
        rec["pending_requirements"] = []
        rec["class_requirements"]["oracle_authority"] = "FRAMEWORK_FROZEN"
        rec["class_requirements"]["oracle_in_worker_scope"] = True
        rec["round_admission"] = {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("oracle_authority must be 'DELTA_AUTHORED_DISCRIMINATING'", out)

    # ---- the exclusion that makes the above safe --------------------------------------------
    def test_a_rewritten_acceptance_is_never_a_basis(self):
        """r03's delta REWRITES scripts/validate_governance.py, and that rewritten validator does
        move FAIL->PASS against the base. It must NOT be accepted as a basis: the delta rewrote
        the very thing that is supposed to judge it, which is the shape every vacuity attack
        takes (the measured `select = []` attack on this pair is exactly this)."""
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R03
        rec["base_sha"], rec["candidate_sha"] = BASE_TOUCHED, CAND_TOUCHED
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("WORKER_MODIFIES_VALIDATOR", out)      # the rewrite is derived from git
        self.assertIn("DERIVED from the git diff", out)

    def test_derived_triggers_fire_on_rewrites_not_on_additions(self):
        """The derivation is precise to its meaning: firing the oracle-rewrite triggers on paths
        the delta merely ADDS made every repair task unsatisfiable while protecting nothing."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("ctc", VALIDATOR)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["ctc"] = mod
        spec.loader.exec_module(mod)
        added = [("A", "scripts/tests/test_new_thing.py"),
                 ("A", "scripts/validate_added.py")]
        self.assertEqual({}, mod.derived_triggers(added))
        rewritten = [("M", "scripts/tests/test_existing.py")]
        self.assertIn("WORKER_MODIFIES_TEST_ORACLE", mod.derived_triggers(rewritten))
        self.assertIn("WORKER_MODIFIES_VALIDATOR",
                      mod.derived_triggers([("M", "scripts/validate_governance.py")]))

    def test_an_unmeasured_verdict_is_not_a_failure(self):
        """Round-10 F1: run_acceptance returns 124 on timeout and 127 for an absent surface.
        Treating either as "the acceptance failed" would open the FAIL->PASS shape on ANY pair —
        including r06 — with a slow acceptance instead of an edited record. The predicate is pinned
        here directly, because manufacturing a real timeout inside the suite would be a timing test
        rather than a rule test."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("ctc", VALIDATOR)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["ctc"] = mod
        spec.loader.exec_module(mod)
        for unmeasured in mod.UNMEASURED_RCS:
            facts = {"class": "A_REPAIR", "acceptance_count": 1, "frozen_count": 0,
                     "acceptance_surface_frozen": False, "oracle_in_worker_scope": True,
                     "discriminating": [], "biting": [], "surfaces": [],
                     "unmeasured": [{"path": "scripts/tests/test_x.py", "provenance": "DELTA_ADDED",
                                     "rc_base": unmeasured, "rc_cand": 0, "rc_mut": None}]}
            ok, reason = mod.transition_verdict("A_REPAIR", facts)
            self.assertFalse(ok, f"rc={unmeasured} must not support a claim")
            self.assertEqual("ACCEPTANCE_NOT_MEASURED", reason)

    def test_reported_basis_is_the_one_the_class_uses(self):
        """Round-10 F2: the B path reported the A basis (and indexed an empty list). The line a
        reviewer reads must name the surface the verdict actually came from."""
        rec = guard_record()
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("MUTATION_DOES_NOT_BITE", out)
        self.assertNotIn("basis=", out)          # refused: no basis may be reported as a pass

    # ---- the declared statuses are bound to the recomputation -------------------------------
    def test_declared_statuses_cannot_contradict_the_recomputation(self):
        rec = repair_record()
        rec["corpus_case_id"] = CASE_R02
        rec["base_sha"], rec["candidate_sha"] = BASE_R02, CAND_R02
        rec["disclosures"] = {"historical_delta_touched_oracle": False,
                              "historical_delta_touched_validator": False}
        rec["pending_requirements"] = []
        rec["class_requirements"]["oracle_authority"] = "DELTA_AUTHORED_DISCRIMINATING"
        rec["class_requirements"]["oracle_in_worker_scope"] = True
        rec["class_requirements"]["baseline_oracle_status"] = "PASS"   # recomputation says FAIL
        rec["round_admission"] = {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("declared baseline_oracle_status='PASS'", out)
        self.assertIn("recomputed 'FAIL'", out)

    def test_a_pair_with_no_transition_fails_closed(self):
        """r06 has acceptance surfaces but none of them moves: base == candidate for every one.
        Requirement 4 — an admissible claim over such a pair must be refused."""
        rec = repair_record()
        rec["class_requirements"]["oracle_authority"] = "DELTA_AUTHORED_DISCRIMINATING"
        rec["class_requirements"]["oracle_in_worker_scope"] = True
        rec["disclosures"] = {"historical_delta_touched_oracle": False,
                              "historical_delta_touched_validator": False}
        rec["pending_requirements"] = []
        rec["round_admission"] = {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]}
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("not supported by execution", out)
        self.assertIn("BASE_EQUALS_CANDIDATE", out)


class MutationMaterialisation(unittest.TestCase):
    """Admission batch-1 finding F-A1 (found by a real candidate, 0007bb3, not by a fixture).

    The controlled mutation used to unlink the added paths from the working tree and leave them in
    git's index. Any acceptance that enumerates the index (`git ls-files`) then crashes on the
    missing file — measured on 0007bb3: test_p1_t16_gate_cli_entrypoint.py rc=1 with
    FileNotFoundError, and rc=0 once the same deletion is index-consistent. That crash was
    counted as a BITE, so a B_REGRESSION_GUARD claim was "supported" by a frozen test that never
    observes the deliverable. Any surface that reads git's index or HEAD is exposed (at main,
    test_p1_t16 and the frozen validate_public_release.py call `git ls-files` directly), so the
    defect is a category, not an instance.

    The fixture repository is synthetic on purpose: the rule under test is the construction of the
    mutation, and both directions (a false bite must vanish, a real bite must survive) have to be
    exercised against surfaces whose dependency on the added file is known exactly.
    """

    INVENTORY_TEST = (
        "import subprocess, unittest\n"
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[2]\n"
        "class Inventory(unittest.TestCase):\n"
        "    def test_every_listed_file_is_readable(self):\n"
        "        out = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '--cached', '--others',\n"
        "                              '--exclude-standard'], capture_output=True, text=True,\n"
        "                             check=True).stdout.split()\n"
        "        self.assertTrue(out)\n"
        "        for rel in out:\n"
        "            (ROOT / rel).read_bytes()\n"
    )
    IMPORT_TEST = (
        "import sys, unittest\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
        "class Lib(unittest.TestCase):\n"
        "    def test_lib_answers(self):\n"
        "        import lib\n"
        "        self.assertEqual(42, lib.answer())\n"
    )

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        spec = importlib.util.spec_from_file_location("ctc_mutation", VALIDATOR)
        self.mod = importlib.util.module_from_spec(spec)
        sys.modules["ctc_mutation"] = self.mod
        spec.loader.exec_module(self.mod)

    def tearDown(self):
        self._tmpdir.cleanup()

    def _git(self, root: Path, *args: str) -> str:
        proc = subprocess.run(["git", "-C", str(root), "-c", "user.name=fixture",
                               "-c", "user.email=fixture@invalid", "-c", "commit.gpgsign=false",
                               *args], capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stderr)
        return proc.stdout.strip()

    def _commit(self, root: Path, files: dict[str, str], message: str) -> str:
        for rel, text in files.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(text, encoding="utf-8")
        self._git(root, "add", "-A")
        self._git(root, "commit", "-q", "--no-verify", "-m", message)
        return self._git(root, "rev-parse", "HEAD")

    def _repo(self, base_files, cand_files, name: str = "repo"):
        root = self.tmp / name
        root.mkdir()
        self._git(root, "init", "-q")
        base = self._commit(root, base_files, "base")
        cand = self._commit(root, cand_files, "candidate")
        return self.mod.Repo(root), base, cand

    def test_an_index_enumerating_surface_does_not_bite_on_an_unrelated_addition(self):
        repo, base, cand = self._repo(
            {"scripts/tests/test_inventory.py": self.INVENTORY_TEST, "README.md": "base\n"},
            {"docs/unrelated.md": "an addition no frozen surface depends on\n"})
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        (surface,) = [e for e in facts["surfaces"] if e["path"].endswith("test_inventory.py")]
        # reachability: the surface really ran in all three states and was green at the base
        self.assertEqual(("DELTA_FROZEN", 0), (surface["provenance"], surface["rc_base"]))
        self.assertEqual(0, surface["rc_mut"],
                         "the mutation crashed an index-enumerating surface: a deletion that git "
                         "still lists is an artefact of the mutation, not a bite")
        self.assertEqual((False, "MUTATION_DOES_NOT_BITE"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    def test_a_real_dependency_on_the_addition_still_bites(self):
        """Positive control: the fix must not make every mutation toothless. The candidate rewrites
        lib.py to delegate to an ADDED helper, and a frozen test imports lib — removing the helper
        breaks a predicate the frozen surface genuinely observes."""
        repo, base, cand = self._repo(
            {"scripts/lib.py": "def answer():\n    return 42\n",
             "scripts/tests/test_lib.py": self.IMPORT_TEST,
             "scripts/tests/test_inventory.py": self.INVENTORY_TEST},
            {"scripts/helper.py": "VALUE = 42\n",
             "scripts/lib.py": "from helper import VALUE\n\ndef answer():\n    return VALUE\n"})
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        rc = {Path(e["path"]).name: (e["rc_base"], e["rc_mut"]) for e in facts["surfaces"]}
        self.assertEqual(0, rc["test_lib.py"][0])
        self.assertNotIn(rc["test_lib.py"][1], (0, None, *self.mod.UNMEASURED_RCS))
        self.assertEqual((0, 0), rc["test_inventory.py"])      # still no artefact bite
        self.assertEqual(["scripts/tests/test_lib.py"], [e["path"] for e in facts["biting"]])
        self.assertEqual((True, "PASS_TO_FAIL_UNDER_MUTATION"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    def test_a_candidate_that_breaks_a_guard_is_not_a_bite(self):
        """F-A3 (batch 2, real pair 825d390): a frozen surface green at the base and RED AT THE
        CANDIDATE was counted as a bite. With no added path the 'mutation' IS the candidate, so the
        claimed protective capability does not even hold at the candidate — the candidate broke the
        guard. A guard can only bite a state it protects: green at base AND candidate, red under a
        mutation that differs from the candidate."""
        budget = (
            "import unittest\n"
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            "class Budget(unittest.TestCase):\n"
            "    def test_doc_within_budget(self):\n"
            "        self.assertLessEqual(len((ROOT / 'doc.md').read_bytes()), 10)\n")
        repo, base, cand = self._repo({"scripts/tests/test_budget.py": budget, "doc.md": "short\n"},
                                      {"doc.md": "this grew well beyond the budget\n"})
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        (surface,) = facts["surfaces"]
        # reachability: the guard really ran and really fails at the candidate
        self.assertEqual((0, 1, 1), (surface["rc_base"], surface["rc_cand"], surface["rc_mut"]))
        self.assertEqual([], facts["biting"])
        # refused; since F-A6 the reason names the regression itself, which is checked first
        self.assertEqual((False, "CANDIDATE_REGRESSES_A_FROZEN_GUARD"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    # ---- fresh review of 4add2ca: findings 1-3 ------------------------------------------------
    def test_a_merge_candidate_stays_a_merge_in_the_mutation(self):
        """F-A4: committing the mutation ON TOP of the candidate gave it a new single parent, so a
        PR-merge candidate stopped being a merge — and a surface that reads HEAD's parents (or the
        HEAD-identity check, measured on 6217cc0) bit on that. The mutation must keep the
        candidate's parents exactly."""
        merge_shape = (
            "import subprocess, unittest\n"
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            "def git(*a):\n"
            "    return subprocess.run(['git', '-C', str(ROOT), *a], capture_output=True,\n"
            "                          text=True, check=True).stdout\n"
            "class MergeShape(unittest.TestCase):\n"
            "    def test_a_merge_message_names_a_merge(self):\n"
            "        parents = git('rev-list', '--parents', '-n1', 'HEAD').split()[1:]\n"
            "        if git('log', '-1', '--format=%s').startswith('Merge'):\n"
            "            self.assertEqual(2, len(parents))\n")
        root = self.tmp / "repo"
        root.mkdir()
        self._git(root, "init", "-q", "-b", "main")
        base = self._commit(root, {"scripts/tests/test_merge.py": merge_shape}, "base")
        self._git(root, "checkout", "-q", "-b", "side")
        self._commit(root, {"docs/feature.md": "side work\n"}, "side")
        self._git(root, "checkout", "-q", "main")
        self._git(root, "merge", "-q", "--no-ff", "--no-verify", "-m", "Merge side", "side")
        cand = self._git(root, "rev-parse", "HEAD")
        facts = self.mod.recompute_transition(self.mod.Repo(root), base, cand,
                                              "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        (surface,) = facts["surfaces"]
        self.assertEqual((0, 0, 0), (surface["rc_base"], surface["rc_cand"], surface["rc_mut"]))
        self.assertEqual([], facts["biting"])

    def test_a_head_parent_reader_does_not_bite_on_the_mutation(self):
        """F-A4, single-parent form: a surface that reads `git diff HEAD^ HEAD` saw the mutation's
        own deletions when the mutation was a child of the candidate."""
        parent_reader = (
            "import subprocess, unittest\n"
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            "class LastChange(unittest.TestCase):\n"
            "    def test_every_path_of_the_last_change_exists(self):\n"
            "        out = subprocess.run(['git', '-C', str(ROOT), 'diff', '--name-only', 'HEAD^',\n"
            "                              'HEAD'], capture_output=True, text=True,\n"
            "                             check=True).stdout.split()\n"
            "        for rel in out:\n"
            "            self.assertTrue((ROOT / rel).exists(), rel)\n")
        root = self.tmp / "repo"
        root.mkdir()
        self._git(root, "init", "-q")
        self._commit(root, {"README.md": "root\n"}, "root")
        base = self._commit(root, {"scripts/tests/test_last.py": parent_reader}, "base")
        cand = self._commit(root, {"docs/added.md": "added\n", "README.md": "edited\n"},
                            "candidate")
        facts = self.mod.recompute_transition(self.mod.Repo(root), base, cand,
                                              "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        (surface,) = facts["surfaces"]
        self.assertEqual((0, 0, 0), (surface["rc_base"], surface["rc_cand"], surface["rc_mut"]))

    def test_an_added_path_is_never_read_as_a_glob(self):
        """F-A5: `git rm docs/[ab].md` removed the pre-existing docs/a.md too."""
        exists = (
            "import unittest\n"
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            "class Exists(unittest.TestCase):\n"
            "    def test_pre_existing_doc_is_present(self):\n"
            "        self.assertTrue((ROOT / 'docs' / 'a.md').is_file())\n")
        repo, base, cand = self._repo({"scripts/tests/test_exists.py": exists, "docs/a.md": "a\n"},
                                      {"docs/[ab].md": "a file whose name is a glob\n"})
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        (surface,) = facts["surfaces"]
        self.assertEqual((0, 0, 0), (surface["rc_base"], surface["rc_cand"], surface["rc_mut"]))

    def test_a_candidate_that_regresses_another_guard_is_not_a_regression_guard(self):
        """F-A6 (r26 / 95667e8): a link guard bit, while the candidate broke a DIFFERENT frozen
        guard (t09, 0/1/1). The biting surface alone was checked, so the claim was supported."""
        link = (
            "import re, unittest\n"
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            "class Links(unittest.TestCase):\n"
            "    def test_links_resolve(self):\n"
            "        for target in re.findall(r'\\]\\(([^)]+)\\)', (ROOT / 'README.md').read_text()):\n"
            "            self.assertTrue((ROOT / target).is_file(), target)\n")
        budget = (
            "import unittest\n"
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            "class Budget(unittest.TestCase):\n"
            "    def test_budget(self):\n"
            "        self.assertLessEqual(len((ROOT / 'pointer.md').read_bytes()), 10)\n")
        repo, base, cand = self._repo(
            {"scripts/tests/test_links.py": link, "scripts/tests/test_budget.py": budget,
             "README.md": "start\n", "pointer.md": "short\n"},
            {"docs/new.md": "new\n", "README.md": "see [new](docs/new.md)\n",
             "pointer.md": "now far beyond its byte budget\n"})
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        rc = {Path(e["path"]).name: (e["rc_base"], e["rc_cand"], e["rc_mut"])
              for e in facts["surfaces"]}
        self.assertEqual((0, 0, 1), rc["test_links.py"])        # the link guard really bites
        self.assertEqual((0, 1, 1), rc["test_budget.py"])       # and the candidate broke this one
        self.assertEqual((False, "CANDIDATE_REGRESSES_A_FROZEN_GUARD"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))
        self.assertEqual("FAIL", facts["candidate_oracle_status"])

    # ---- fresh review of f2c48a0: findings 1, 2, 3, 5 -----------------------------------------
    LINKS = (
        "import re, unittest\n"
        "from pathlib import Path\n"
        "ROOT = Path(__file__).resolve().parents[2]\n"
        "class Links(unittest.TestCase):\n"
        "    def test_links_resolve(self):\n"
        "        for target in re.findall(r'\\]\\(([^)]+)\\)', (ROOT / 'README.md').read_text()):\n"
        "            self.assertTrue((ROOT / target).is_file(), target)\n")

    def _budget(self, on_breach: str) -> str:
        return ("import unittest\n"
                "from pathlib import Path\n"
                "ROOT = Path(__file__).resolve().parents[2]\n"
                "class Budget(unittest.TestCase):\n"
                "    def test_budget(self):\n"
                "        if len((ROOT / 'pointer.md').read_bytes()) > 10:\n"
                f"            {on_breach}\n")

    def _guarded_repo(self, budget_on_breach: str, delete_budget: bool, grow: bool = True):
        cand = {"docs/new.md": "new\n", "README.md": "see [new](docs/new.md)\n"}
        if grow:
            cand["pointer.md"] = "now far beyond its byte budget\n"
        repo, base, c = self._repo(
            {"scripts/tests/test_links.py": self.LINKS,
             "scripts/tests/test_budget.py": self._budget(budget_on_breach),
             "README.md": "start\n", "pointer.md": "short\n"}, cand)
        if delete_budget:
            root = repo.root
            self._git(root, "rm", "-q", "scripts/tests/test_budget.py")
            self._git(root, "commit", "-q", "--amend", "--no-edit", "--no-verify")
            c = self._git(root, "rev-parse", "HEAD")
        return repo, base, c

    def test_a_guard_that_hangs_at_the_candidate_fails_closed(self):
        """Finding 1: green at the base, TIMEOUT at the candidate. `regressed` needs a measured
        verdict, so the hang was silently not a regression and B was supported."""
        saved = self.mod.ACCEPTANCE_TIMEOUT
        self.mod.ACCEPTANCE_TIMEOUT = 5
        try:
            repo, base, cand = self._guarded_repo("while True: pass", delete_budget=False)
            facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        finally:
            self.mod.ACCEPTANCE_TIMEOUT = saved
        rc = {Path(e["path"]).name: (e["rc_base"], e["rc_cand"]) for e in facts["surfaces"]}
        self.assertEqual((0, 124), rc["test_budget.py"])       # reachability: it really hung
        self.assertTrue(facts["biting"])                        # and the link guard really bit
        self.assertEqual((False, "CANDIDATE_GUARD_UNMEASURED"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))
        self.assertEqual("UNMEASURED", facts["candidate_oracle_status"])

    def test_a_guard_the_candidate_deletes_is_still_checked(self):
        """Finding 2 (real case r29 / 5205e5b): the candidate deletes a base-green guard that its
        own tree would fail. Deleted surfaces were never run, so the regression was invisible."""
        repo, base, cand = self._guarded_repo("self.fail('over budget')", delete_budget=True)
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        (deleted,) = facts["deleted_surfaces"]
        self.assertEqual(("scripts/tests/test_budget.py", "DELTA_DELETED", 0, 1),
                         (deleted["path"], deleted["provenance"], deleted["rc_base"],
                          deleted["rc_cand"]))
        self.assertTrue(facts["biting"])
        self.assertEqual((False, "CANDIDATE_REGRESSES_A_FROZEN_GUARD"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    def test_a_deleted_guard_whose_property_still_holds_is_not_a_regression(self):
        """Positive control for finding 2: deleting a guard the candidate would still pass is a
        disclosed fact (DELTA_DELETED), not a regression; the link bite still supports B."""
        repo, base, cand = self._guarded_repo("self.fail('over budget')", delete_budget=True,
                                              grow=False)
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        (deleted,) = facts["deleted_surfaces"]
        self.assertEqual((0, 0), (deleted["rc_base"], deleted["rc_cand"]))
        self.assertEqual((True, "PASS_TO_FAIL_UNDER_MUTATION"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    def test_a_rewritten_non_ascii_validator_derives_its_trigger(self):
        """Finding 5: without -z the path came back quoted and matched no name rule."""
        repo, base, cand = self._repo(
            {"scripts/validate_数据.py": "print(1)\n", "scripts/validate_plain.py": "print(1)\n"},
            {"scripts/validate_数据.py": "print(2)\n", "scripts/validate_plain.py": "print(2)\n"})
        changed = repo.changed_paths_with_status(base, cand)
        self.assertEqual(sorted(["scripts/validate_数据.py", "scripts/validate_plain.py"]),
                         sorted(self.mod.derived_triggers(changed)["WORKER_MODIFIES_VALIDATOR"]))

    def _mutation_with(self, patch, name: str):
        """Run _materialise_mutation with one git call perturbed; the postconditions must catch it."""
        repo, base, cand = self._repo({"README.md": "a\n", "keep.md": "keep\n"},
                                      {"docs/added.md": "added\n"}, name=name)
        wt = self.tmp / f"mut-{name}"
        self.assertEqual(0, repo.git("worktree", "add", "-q", "--detach", str(wt), cand).returncode)
        real_run = self.mod.subprocess.run
        self.mod.subprocess.run = patch(real_run)
        try:
            return self.mod._materialise_mutation(repo, cand, wt, ["docs/added.md"])
        finally:
            self.mod.subprocess.run = real_run

    def test_mutation_postconditions_are_load_bearing(self):
        """Finding 3: replacing the postconditions with `return True` survived the suite. Each
        perturbation below must be refused by the postcondition that names it."""
        def over_remove(real):                 # rm also deletes a pre-existing file
            def run(cmd, *a, **k):
                if "rm" in cmd and "--" in cmd:
                    cmd = list(cmd) + ["keep.md"]
                return real(cmd, *a, **k)
            return run

        def orphan(real):                      # the rewritten commit loses its parent
            def run(cmd, *a, **k):
                out = real(cmd, *a, **k)
                if cmd[-2:-1] == ["commit"] and "cat-file" in cmd:
                    out.stdout = b"\n".join(ln for ln in out.stdout.split(b"\n")
                                            if not ln.startswith(b"parent "))
                return out
            return run

        def identity(real):                    # control: no perturbation
            return real
        self.assertTrue(self._mutation_with(identity, "control"))
        self.assertFalse(self._mutation_with(over_remove, "over"), "exact-diff postcondition is dead")
        self.assertFalse(self._mutation_with(orphan, "orphan"), "parent-equality postcondition is dead")

    def test_a_declared_unmeasured_status_is_refused(self):
        """Finding 3: the closed vocabulary for B's optional candidate_oracle_status had no test."""
        rec = guard_record()
        rec["class_requirements"]["candidate_oracle_status"] = "UNMEASURED"
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("candidate_oracle_status must be 'PASS' or 'FAIL' when declared", out)

    # ---- fresh review of ceb3a72: finding 1 (aliasing) and the surviving mutants -------------
    def _alias_repo(self, how: str):
        """Base guard scripts/tests/test_budget.py; the candidate re-adds it as a vacuous copy
        reached through an ALIAS of its directory (symlink, or a case-folded spelling), adds a
        linked doc and breaks the budget."""
        root = self.tmp / f"alias-{how}"
        root.mkdir()
        self._git(root, "init", "-q")
        base = self._commit(root, {"scripts/tests/test_links.py": self.LINKS,
                                   "scripts/tests/test_budget.py":
                                       self._budget("self.fail('over budget')"),
                                   "README.md": "start\n", "pointer.md": "short\n"}, "base")
        self._git(root, "rm", "-q", "-r", "scripts/tests")
        vacuous = "import unittest\nclass Budget(unittest.TestCase):\n    def test_budget(self):\n        pass\n"
        files = {"docs/new.md": "new\n", "README.md": "see [new](docs/new.md)\n",
                 "pointer.md": "now far beyond its byte budget\n"}
        if how == "symlink":
            files["tests_v2/test_links.py"] = self.LINKS.replace("parents[2]", "parents[1]")
            files["tests_v2/test_budget.py"] = vacuous
            for rel, text in files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text, encoding="utf-8")
            (root / "scripts").mkdir(exist_ok=True)
            (root / "scripts" / "tests").symlink_to("../tests_v2")
        else:
            files["scripts/Tests/test_links.py"] = self.LINKS
            files["scripts/Tests/test_budget.py"] = vacuous
            for rel, text in files.items():
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(text, encoding="utf-8")
        self._git(root, "add", "-A")
        self._git(root, "commit", "-q", "--no-verify", "-m", "candidate")
        return self.mod.Repo(root), base, self._git(root, "rev-parse", "HEAD")

    def test_a_guard_re_added_through_a_symlinked_directory_fails_closed(self):
        """Finding 1: filesystem discovery saw scripts/tests/test_budget.py at the candidate (via
        the symlink) while git reported it deleted, so no rule fired and B was a valid request."""
        repo, base, cand = self._alias_repo("symlink")
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertEqual("SURFACE_PATH_ALIASED", facts.get("error"), facts)
        self.assertFalse(self.mod.transition_verdict("B_REGRESSION_GUARD", facts)[0])

    def test_a_guard_re_added_under_a_case_folded_directory_is_refused(self):
        """Finding 1, case variant. On a case-insensitive filesystem the spelling alias fails
        closed; on a case-sensitive one the guard is simply DELTA_DELETED and regressed. Either
        way B must be refused — the verdict may not depend on the filesystem."""
        repo, base, cand = self._alias_repo("case")
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        ok, reason = self.mod.transition_verdict("B_REGRESSION_GUARD", facts)
        self.assertFalse(ok)
        self.assertIn(reason, ("SURFACE_PATH_ALIASED", "CANDIDATE_REGRESSES_A_FROZEN_GUARD"))

    def test_a_deleted_guard_that_hangs_is_unmeasured_not_ignored(self):
        """Mutant M3: guard_unmeasured over frozen surfaces only survived the suite."""
        saved = self.mod.ACCEPTANCE_TIMEOUT
        self.mod.ACCEPTANCE_TIMEOUT = 5
        try:
            repo, base, cand = self._guarded_repo("while True: pass", delete_budget=True)
            facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        finally:
            self.mod.ACCEPTANCE_TIMEOUT = saved
        (deleted,) = facts["deleted_surfaces"]
        self.assertEqual((0, 124), (deleted["rc_base"], deleted["rc_cand"]))
        self.assertEqual((False, "CANDIDATE_GUARD_UNMEASURED"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    def test_a_base_red_guard_neither_regresses_nor_counts_as_unmeasured(self):
        """Mutants M10 / M13: a guard already red at the base protects nothing, so its candidate
        verdict (hang, or failure after deletion) must not refuse an otherwise supported B."""
        saved = self.mod.ACCEPTANCE_TIMEOUT
        self.mod.ACCEPTANCE_TIMEOUT = 5
        red_then_hang = ("import unittest\nfrom pathlib import Path\n"
                         "ROOT = Path(__file__).resolve().parents[2]\n"
                         "class Odd(unittest.TestCase):\n"
                         "    def test_odd(self):\n"
                         "        if (ROOT / 'docs' / 'new.md').exists():\n"
                         "            while True: pass\n"
                         "        self.fail('red at the base')\n")
        try:
            for name, deleted in (("hang", False), ("gone", True)):
                repo, base, cand = self._repo(
                    {"scripts/tests/test_links.py": self.LINKS, "scripts/tests/test_odd.py":
                        red_then_hang, "README.md": "start\n"},
                    {"docs/new.md": "new\n", "README.md": "see [new](docs/new.md)\n"},
                    name=f"red-{name}")
                if deleted:
                    self._git(repo.root, "rm", "-q", "scripts/tests/test_odd.py")
                    self._git(repo.root, "commit", "-q", "--amend", "--no-edit", "--no-verify")
                    cand = self._git(repo.root, "rev-parse", "HEAD")
                facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
                odd = [e for e in facts["surfaces"] + facts["deleted_surfaces"]
                       if e["path"].endswith("test_odd.py")]
                self.assertEqual(1, odd[0]["rc_base"], name)          # red at the base
                self.assertEqual((True, "PASS_TO_FAIL_UNDER_MUTATION"),
                                 self.mod.transition_verdict("B_REGRESSION_GUARD", facts), name)
        finally:
            self.mod.ACCEPTANCE_TIMEOUT = saved

    def test_a_renamed_oracle_is_a_rewrite_whatever_the_rename_config(self):
        """Mutant M8 + finding 4: rename records carry two paths; and with diff.renames=false a
        renamed-and-edited test came back as D + A and derived no trigger."""
        body = "import unittest\nclass T(unittest.TestCase):\n" + "".join(
            f"    def test_{i}(self):\n        self.assertTrue(True)\n" for i in range(20))
        root = self.tmp / "rename"
        root.mkdir()
        self._git(root, "init", "-q")
        base = self._commit(root, {"scripts/tests/test_old.py": body}, "base")
        self._git(root, "mv", "scripts/tests/test_old.py", "scripts/tests/test_new.py")
        cand = self._commit(root, {"scripts/tests/test_new.py": body + "# edited\n"},
                            "candidate")
        repo = self.mod.Repo(root)
        self._git(repo.root, "config", "diff.renames", "false")
        changed = repo.changed_paths_with_status(base, cand)
        self.assertEqual(1, len(changed), changed)
        self.assertTrue(changed[0][0].startswith("R"))
        self.assertEqual("scripts/tests/test_new.py", changed[0][1])
        self.assertIn("WORKER_MODIFIES_TEST_ORACLE", self.mod.derived_triggers(changed))

    # ---- fresh review of 6527c81: findings 1-3 ------------------------------------------------
    def test_an_added_module_that_shadows_an_import_derives_a_trigger(self):
        """Finding 1: `python scripts/validate_x.py` / `unittest discover -s scripts/tests` put
        those directories first on sys.path, so an added scripts/json.py (or scripts/tests/json.py)
        replaces what a FROZEN surface imports. The transition then reads FAIL->PASS on a
        'framework-frozen' oracle nothing repaired — the derived trigger must refuse it."""
        budget = ("import json, sys\nfrom pathlib import Path\n"
                  "ROOT = Path(__file__).resolve().parents[1]\n"
                  "limit = json.loads('10')\n"
                  "sys.exit(0 if len((ROOT / 'pointer.md').read_bytes()) <= limit else 1)\n")
        permissive = "def loads(_):\n    return 10 ** 9\n"
        for root_dir, name in (("scripts", "shadow-v"), ("scripts/tests", "shadow-t")):
            repo, base, cand = self._repo(
                {"scripts/validate_budget.py": budget, "pointer.md": "far beyond the budget\n"},
                {"notes.md": "n\n", f"{root_dir}/json.py": permissive}, name=name)
            facts = self.mod.recompute_transition(repo, base, cand, "A_REPAIR")
            if root_dir == "scripts":      # reachability: the shadow really flips the oracle
                self.assertEqual((True, "FAIL_TO_PASS"),
                                 self.mod.transition_verdict("A_REPAIR", facts))
            derived = self.mod.derived_triggers(repo.changed_paths_with_status(base, cand))
            self.assertEqual([f"{root_dir}/json.py"],
                             derived.get("ACCEPTANCE_SURFACE_IN_WORKER_SCOPE"), name)
        # control: a module with no importable namesake is an ordinary deliverable
        repo, base, cand = self._repo({"README.md": "a\n"},
                                      {"scripts/review_evidence_like.py": "X = 1\n"},
                                      name="shadow-control")
        self.assertEqual({}, self.mod.derived_triggers(repo.changed_paths_with_status(base, cand)))

    def test_a_checkout_filter_cannot_rewrite_a_frozen_guard(self):
        """Finding 2: a candidate-edited .gitattributes (working-tree-encoding) changed the bytes a
        'DELTA_FROZEN' guard executes at BOTH revisions, so its regression never registered."""
        repo, base, cand = self._repo(
            {"scripts/tests/test_links.py": self.LINKS,
             "scripts/tests/test_budget.py": self._budget("self.fail('over budget')"),
             "README.md": "start\n", "pointer.md": "short\n", ".gitattributes": "*.md text\n"},
            {"docs/new.md": "new\n", "README.md": "see [new](docs/new.md)\n",
             "pointer.md": "now far beyond its byte budget\n",
             ".gitattributes": "*.md text\nscripts/tests/test_budget.py "
                               "working-tree-encoding=UTF-16LE\n"}, name="attr")
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertEqual("SURFACE_BYTES_DIVERGE", facts.get("error"), facts)
        self.assertFalse(self.mod.transition_verdict("B_REGRESSION_GUARD", facts)[0])

    def test_a_surface_replaced_by_a_symlink_is_not_a_surface(self):
        """Finding 3 (mutant MG): only regular files are surfaces. A guard replaced by a symlink to
        a vacuous copy must not be judged as the guard."""
        root = self.tmp / "symfile"
        root.mkdir()
        self._git(root, "init", "-q")
        base = self._commit(root, {"scripts/tests/test_links.py": self.LINKS,
                                   "scripts/tests/test_budget.py":
                                       self._budget("self.fail('over budget')"),
                                   "README.md": "start\n", "pointer.md": "short\n"}, "base")
        self._git(root, "rm", "-q", "scripts/tests/test_budget.py")
        (root / "vacuous.py").write_text("import unittest\n", encoding="utf-8")
        (root / "scripts/tests/test_budget.py").symlink_to("../../vacuous.py")
        cand = self._commit(root, {"docs/new.md": "new\n", "README.md": "see [new](docs/new.md)\n",
                                   "pointer.md": "now far beyond its byte budget\n"}, "candidate")
        repo = self.mod.Repo(root)
        self.assertNotIn("scripts/tests/test_budget.py", self.mod.tracked_surfaces(repo, cand))
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertFalse(self.mod.transition_verdict("B_REGRESSION_GUARD", facts)[0], facts)

    def test_a_renamed_dependency_is_removed_by_the_mutation(self):
        """Finding 3 (mutant MF): with git's default rename detection a moved file is R, not A, and
        the mutation kept it. ADDED means new at the candidate, whatever the rename heuristics."""
        doc = "".join(f"line {i} of a document long enough for rename detection\n"
                      for i in range(30))
        repo, base, cand = self._repo(
            {"scripts/tests/test_links.py": self.LINKS, "README.md": "see [a](docs/a.md)\n",
             "docs/a.md": doc}, {"README.md": "see [b](docs/b.md)\n", "docs/b.md": doc},
            name="moved")
        self._git(repo.root, "rm", "-q", "docs/a.md")
        self._git(repo.root, "commit", "-q", "--amend", "--no-edit", "--no-verify")
        cand = self._git(repo.root, "rev-parse", "HEAD")
        self._git(repo.root, "config", "diff.renames", "true")
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertEqual(["scripts/tests/test_links.py"], [e["path"] for e in facts["biting"]])

    # ---- fresh review of 72f0bb4: findings 1-4 ------------------------------------------------
    def test_every_import_path_shape_derives_the_trigger(self):
        """Finding 1: 2.8.5 covered `<n>.py` / `<n>/__init__.py` under scripts/ and scripts/tests/
        only. Each path below decides what an acceptance imports; each must derive the trigger,
        whether ADDED or REWRITTEN, and an ordinary new module must not."""
        shaped = ["scripts/tests/zz_helpers/__init__.py", "unittest.py", "json.py",
                  "scripts/json.pyc", "json.pyc", "pkg/__init__.pyc", "scripts/__init__.py",
                  "scripts/tests/__init__.py",   # restored in 2.8.8: test_p1_t18 imports it
                  "scripts/_json.cpython-313-darwin.so",
                  "scripts/pip.py"]            # pip: importable but NOT stdlib (find_spec half)
        changed = [("A", p) for p in shaped] + [("M", "scripts/os.py"),
                                                 ("A", "scripts/review_evidence_like.py"),
                                                 ("A", "scripts/tests/helper_like.py"),
                                                 ("A", "setup.py"),
                                                 # inert or not imported (review of 617ba01)
                                                 ("A", "scripts/__main__.py"),
                                                 ("A", "scripts/tests/__pycache__/"
                                                       "test_budget.cpython-313.pyc"),
                                                 # real history: bytecode off any import path
                                                 ("A", "adapters/zcode/tests/__pycache__/"
                                                       "test_project_continuity.cpython-312.pyc")]
        derived = self.mod.derived_triggers(changed).get("ACCEPTANCE_SURFACE_IN_WORKER_SCOPE", [])
        self.assertEqual(sorted(shaped + ["scripts/os.py"]), sorted(derived))

    def test_committed_bytecode_is_never_executed(self):
        """Finding 1d: an unchecked-hash __pycache__ entry replaced a frozen test's code while its
        blob stayed untouched. Acceptances run with a fresh PYTHONPYCACHEPREFIX, so the source
        is what executes."""
        import py_compile
        tree = self.tmp / "pyc"
        tests = tree / "scripts" / "tests"
        tests.mkdir(parents=True)
        source = tests / "test_budget.py"
        source.write_text("import unittest\nclass T(unittest.TestCase):\n"
                          "    def test_x(self):\n        self.fail('the source fails')\n",
                          encoding="utf-8")
        fake = self.tmp / "fake_test_budget.py"
        fake.write_text("import unittest\nclass T(unittest.TestCase):\n"
                        "    def test_x(self):\n        pass\n", encoding="utf-8")
        cache = tests / "__pycache__" / f"test_budget.{sys.implementation.cache_tag}.pyc"
        cache.parent.mkdir()
        py_compile.compile(str(fake), cfile=str(cache),
                           invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        # control: without the isolation, the committed bytecode would decide the verdict
        plain = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests",
                                "-p", "test_budget.py"], cwd=str(tree), capture_output=True)
        self.assertEqual(0, plain.returncode, "positive control: the stale .pyc is honoured")
        self.assertEqual(1, self.mod.run_acceptance(tree, "scripts/tests/test_budget.py", "TEST",
                                                    sys.executable))

    def test_one_surface_cannot_rewrite_another_between_runs(self):
        """Finding 2: an ADDED test that runs first rewrote a FROZEN guard in the shared worktree,
        and the rewritten bytes executed at the candidate and were carried into the base."""
        rewriter = ("import unittest\nfrom pathlib import Path\n"
                    "ROOT = Path(__file__).resolve().parents[2]\n"
                    "class Aaa(unittest.TestCase):\n"
                    "    def test_rewrite(self):\n"
                    "        if (ROOT / 'docs' / 'new.md').exists():\n"
                    "            (ROOT / 'scripts/tests/test_budget.py').write_text(\n"
                    "                'import unittest\\nclass B(unittest.TestCase):\\n'\n"
                    "                '    def test_b(self):\\n        pass\\n')\n")
        repo, base, cand = self._repo(
            {"scripts/tests/test_links.py": self.LINKS,
             "scripts/tests/test_budget.py": self._budget("self.fail('over budget')"),
             "README.md": "start\n", "pointer.md": "short\n"},
            {"docs/new.md": "new\n", "README.md": "see [new](docs/new.md)\n",
             "pointer.md": "now far beyond its byte budget\n",
             "scripts/tests/test_aaa_rewriter.py": rewriter}, name="toctou")
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        rc = {Path(e["path"]).name: (e["rc_base"], e["rc_cand"]) for e in facts["surfaces"]}
        self.assertEqual((0, 1), rc["test_budget.py"])        # the real regression is measured
        self.assertEqual((False, "CANDIDATE_REGRESSES_A_FROZEN_GUARD"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    def test_checkout_is_byte_neutral_under_autocrlf(self):
        """Finding 4: core.autocrlf=true (Git for Windows' default) rewrote every surface on
        checkout and every record failed SURFACE_BYTES_DIVERGE."""
        repo, base, cand = self._guarded_repo("self.fail('over budget')", delete_budget=False,
                                              grow=False)
        self._git(repo.root, "config", "core.autocrlf", "true")
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        self.assertEqual((True, "PASS_TO_FAIL_UNDER_MUTATION"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    # ---- fresh review of 617ba01: findings 1 and 6 ---------------------------------------------
    def test_a_carried_surface_keeps_its_tracked_mode(self):
        """Finding 1 (a 2.8.6 regression): the carried blob landed as 0644, so a mode-checking
        acceptance read FAIL at the base and FAIL->PASS was reported for a pair that repairs
        nothing (2.8.5 measured it correctly)."""
        modes = ("import os, unittest\nfrom pathlib import Path\n"
                 "ROOT = Path(__file__).resolve().parents[2]\n"
                 "class Modes(unittest.TestCase):\n"
                 "    def test_shebang_scripts_are_executable(self):\n"
                 "        for p in (ROOT / 'scripts').rglob('*.py'):\n"
                 "            if p.read_text().startswith('#!'):\n"
                 "                self.assertTrue(os.access(p, os.X_OK), p)\n")
        root = self.tmp / "modes"
        root.mkdir()
        self._git(root, "init", "-q")
        (root / "scripts").mkdir()
        (root / "scripts/tool.py").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        os.chmod(root / "scripts/tool.py", 0o755)
        self._git(root, "add", "-A")
        self._git(root, "commit", "-q", "--no-verify", "-m", "base")
        base = self._git(root, "rev-parse", "HEAD")
        (root / "scripts/tests").mkdir()
        (root / "scripts/tests/test_modes.py").write_text("#!/usr/bin/env python3\n" + modes,
                                                          encoding="utf-8")
        os.chmod(root / "scripts/tests/test_modes.py", 0o755)
        self._git(root, "add", "-A")
        self._git(root, "commit", "-q", "--no-verify", "-m", "candidate")
        cand = self._git(root, "rev-parse", "HEAD")
        facts = self.mod.recompute_transition(self.mod.Repo(root), base, cand, "A_REPAIR")
        self.assertNotIn("error", facts, facts)
        (surface,) = facts["surfaces"]
        self.assertEqual(("DELTA_ADDED", 0, 0), (surface["provenance"], surface["rc_base"],
                                                 surface["rc_cand"]))
        self.assertEqual((False, "BASE_EQUALS_CANDIDATE"),
                         self.mod.transition_verdict("A_REPAIR", facts))

    def test_an_untracked_file_from_one_run_never_reaches_the_next(self):
        """Finding 6 (mutant `no_clean` survived): an ADDED test leaves an untracked override that
        a FROZEN guard honours; without `git clean` the candidate's regression stays hidden."""
        budget = ("import unittest\nfrom pathlib import Path\n"
                  "ROOT = Path(__file__).resolve().parents[2]\n"
                  "class Budget(unittest.TestCase):\n"
                  "    def test_budget(self):\n"
                  "        if (ROOT / 'budget.override').exists():\n"
                  "            return\n"
                  "        self.assertLessEqual(len((ROOT / 'pointer.md').read_bytes()), 10)\n")
        writer = ("import unittest\nfrom pathlib import Path\n"
                  "ROOT = Path(__file__).resolve().parents[2]\n"
                  "class Aaa(unittest.TestCase):\n"
                  "    def test_writes(self):\n"
                  "        (ROOT / 'budget.override').write_text('x')\n")
        repo, base, cand = self._repo(
            {"scripts/tests/test_links.py": self.LINKS, "scripts/tests/test_budget.py": budget,
             "README.md": "start\n", "pointer.md": "short\n"},
            {"docs/new.md": "new\n", "README.md": "see [new](docs/new.md)\n",
             "pointer.md": "now far beyond its byte budget\n",
             "scripts/tests/test_aaa_writer.py": writer}, name="carryover")
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        rc = {Path(e["path"]).name: (e["rc_base"], e["rc_cand"]) for e in facts["surfaces"]}
        self.assertEqual((0, 1), rc["test_budget.py"])
        self.assertEqual((False, "CANDIDATE_REGRESSES_A_FROZEN_GUARD"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    # ---- review of 1e8ac1f: open P3-2 (branches 2.8.7 left untested) ---------------------------
    def _mode_repo(self, name: str):
        root = self.tmp / name
        root.mkdir()
        self._git(root, "init", "-q")
        return root

    def test_a_mode_only_change_is_delta_modified(self):
        root = self._mode_repo("modeonly")
        base = self._commit(root, {"scripts/tests/test_m.py":
                                   "import unittest\nclass M(unittest.TestCase):\n"
                                   "    def test_m(self):\n        pass\n"}, "base")
        os.chmod(root / "scripts/tests/test_m.py", 0o755)
        self._git(root, "add", "-A")
        self._git(root, "commit", "-q", "--no-verify", "-m", "candidate")
        cand = self._git(root, "rev-parse", "HEAD")
        facts = self.mod.recompute_transition(self.mod.Repo(root), base, cand, "A_REPAIR")
        self.assertNotIn("error", facts, facts)
        self.assertEqual(["DELTA_MODIFIED"], [e["provenance"] for e in facts["surfaces"]])

    def test_an_exec_bit_flipped_on_disk_diverges(self):
        root = self._mode_repo("execflip")
        self._commit(root, {"scripts/validate_x.py": "print(1)\n"}, "base")
        blob = self._git(root, "rev-parse", "HEAD:scripts/validate_x.py")
        self.assertIsNone(self.mod._bytes_diverge(root, {"scripts/validate_x.py":
                                                         (blob, "100644")}))
        os.chmod(root / "scripts/validate_x.py", 0o755)
        self.assertEqual("scripts/validate_x.py",
                         self.mod._bytes_diverge(root, {"scripts/validate_x.py": (blob, "100644")}))

    def test_a_deleted_executable_guard_is_carried_with_its_mode(self):
        """The deleted leg carries (blob, mode) too: a 100755 guard that checks its own exec bit
        must still pass at the candidate, not read as a regression."""
        selfcheck = ("import os, unittest\n"
                     "class Self(unittest.TestCase):\n"
                     "    def test_self_executable(self):\n"
                     "        self.assertTrue(os.access(__file__, os.X_OK))\n")
        root = self._mode_repo("deleted755")
        (root / "scripts/tests").mkdir(parents=True)
        (root / "scripts/tests/test_self.py").write_text(selfcheck, encoding="utf-8")
        os.chmod(root / "scripts/tests/test_self.py", 0o755)
        base = self._commit(root, {"scripts/tests/test_links.py": self.LINKS,
                                   "README.md": "start\n"}, "base")
        self._git(root, "rm", "-q", "scripts/tests/test_self.py")
        cand = self._commit(root, {"docs/new.md": "new\n", "README.md": "see [new](docs/new.md)\n"},
                            "candidate")
        facts = self.mod.recompute_transition(self.mod.Repo(root), base, cand,
                                              "B_REGRESSION_GUARD")
        (deleted,) = facts["deleted_surfaces"]
        self.assertEqual((0, 0), (deleted["rc_base"], deleted["rc_cand"]))
        self.assertEqual((True, "PASS_TO_FAIL_UNDER_MUTATION"),
                         self.mod.transition_verdict("B_REGRESSION_GUARD", facts))

    def test_pythonpath_never_reaches_an_acceptance(self):
        """The acceptance imports from the same places the isolated name lookup resolves: a module
        reachable only through the operator's PYTHONPATH must not decide a verdict."""
        tree = self.tmp / "pp"
        (tree / "scripts").mkdir(parents=True)
        (tree / "scripts/validate_x.py").write_text(
            "import sys\ntry:\n    import h2_pythonpath_probe\nexcept ImportError:\n"
            "    sys.exit(1)\nsys.exit(0)\n", encoding="utf-8")
        extra = self.tmp / "extra"
        extra.mkdir()
        (extra / "h2_pythonpath_probe.py").write_text("X = 1\n", encoding="utf-8")
        saved = os.environ.get("PYTHONPATH")
        os.environ["PYTHONPATH"] = str(extra)
        try:
            control = subprocess.run([sys.executable, "scripts/validate_x.py"], cwd=str(tree))
            self.assertEqual(0, control.returncode, "positive control: PYTHONPATH is honoured")
            self.assertEqual(1, self.mod.run_acceptance(tree, "scripts/validate_x.py",
                                                        "VALIDATOR", sys.executable))
        finally:
            if saved is None:
                os.environ.pop("PYTHONPATH", None)
            else:
                os.environ["PYTHONPATH"] = saved

    # ---- 2.8.8: externalised-oracle identities are verified from the object database ----------
    def _externalisable(self):
        """A real-repair shape: C fixes lib.py AND rewrites the existing test (the historical delta
        contains its oracle). B' = B + C's test file, built the way admission/externalize.py does."""
        root = self.tmp / "ext"
        root.mkdir()
        self._git(root, "init", "-q")
        b = self._commit(root, {"scripts/lib.py": "def f():\n    return 1\n",
                                "scripts/tests/test_lib.py": "import unittest\n"}, "base")
        c = self._commit(root, {"scripts/lib.py": "def f():\n    return 2\n",
                                "scripts/tests/test_lib.py": "import unittest  # now checks f\n"},
                         "candidate")
        spec = importlib.util.spec_from_file_location(
            "adm_externalize", H2 / "admission" / "externalize.py")
        ext = importlib.util.module_from_spec(spec)
        sys.modules["adm_externalize"] = ext
        spec.loader.exec_module(ext)
        prime = ext.build_base_prime(root, b, c, ["scripts/tests/test_lib.py"])
        return self.mod.Repo(root), root, b, c, prime, ext

    def test_a_correctly_externalised_base_verifies(self):
        repo, _root, b, c, prime, _ext = self._externalisable()
        meta = {"kind": "EXTERNALIZED_ORACLE", "original_base": b,
                "externalized_paths": '["scripts/tests/test_lib.py"]'}
        self.assertEqual([], self.mod.verify_externalized(repo, "x", prime, c, meta))
        # and the new pair derives no trigger: the oracle is no longer in the delta
        self.assertEqual({}, self.mod.derived_triggers(repo.changed_paths_with_status(prime, c)))

    def test_a_forged_externalised_base_is_refused(self):
        repo, root, b, c, prime, ext = self._externalisable()
        meta = {"kind": "EXTERNALIZED_ORACLE", "original_base": b,
                "externalized_paths": '["scripts/tests/test_lib.py"]'}
        # (1) B' also smuggles the FIX in (an extra changed path)
        smuggled = ext.build_base_prime(root, b, c, ["scripts/tests/test_lib.py", "scripts/lib.py"])
        self.assertTrue(self.mod.verify_externalized(repo, "x", smuggled, c, meta))
        # (2) B' whose parent is not the original base
        wrong_parent = ext.build_base_prime(root, c, c, ["scripts/tests/test_lib.py"])
        self.assertTrue(self.mod.verify_externalized(repo, "x", wrong_parent, c, meta))
        # (3) the declared original base is not the candidate's first parent
        self.assertTrue(self.mod.verify_externalized(repo, "x", prime, c,
                                                     dict(meta, original_base=c)))
        # (4) the oracle path in B' is not C's bytes (a weakened oracle) — right parent, right
        #     path set, so ONLY the byte-identity rule can refuse it
        weak_blob = subprocess.run(["git", "-C", str(root), "hash-object", "-w", "--stdin"],
                                   input="import unittest  # weak\n", capture_output=True,
                                   text=True, check=True).stdout.strip()
        index = self.tmp / "weak.index"
        env = dict(os.environ, GIT_INDEX_FILE=str(index))
        subprocess.run(["git", "-C", str(root), "read-tree", b], env=env, check=True)
        subprocess.run(["git", "-C", str(root), "update-index", "--cacheinfo",
                        f"100644,{weak_blob},scripts/tests/test_lib.py"], env=env, check=True)
        tree = subprocess.run(["git", "-C", str(root), "write-tree"], env=env, capture_output=True,
                              text=True, check=True).stdout.strip()
        weakened = self._git(root, "commit-tree", tree, "-p", b, "-m", "weakened")
        errs = self.mod.verify_externalized(repo, "x", weakened, c, meta)
        self.assertEqual(1, len(errs), errs)
        self.assertIn("not mode- and byte-identical", errs[0])
        # (5) malformed declarations
        self.assertTrue(self.mod.verify_externalized(repo, "x", prime, c,
                                                     dict(meta, externalized_paths="[]")))

    # ---- DeepSeek review of ad87629: findings 1 and 3 -------------------------------------------
    def test_the_operators_temp_root_never_decides_a_verdict(self):
        """Finding 1: acceptances inherited TMPDIR; under macOS' symlinked /var/folders/... a
        candidate refusing symlinked components failed at both revisions. 2.8.9 pins a fresh,
        realpath-resolved temp root per run."""
        tree = self.tmp / "tmpdir"
        (tree / "scripts").mkdir(parents=True)
        (tree / "scripts/validate_tmp.py").write_text(
            "import os, sys, tempfile\nroot = tempfile.gettempdir()\n"
            "sys.exit(0 if os.path.realpath(root) == os.path.abspath(root) else 1)\n",
            encoding="utf-8")
        real = self.tmp / "realtmp"
        real.mkdir()
        link = self.tmp / "linktmp"
        link.symlink_to(real)
        saved = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = str(link)
        try:
            control = subprocess.run([sys.executable, "scripts/validate_tmp.py"], cwd=str(tree))
            self.assertEqual(1, control.returncode, "positive control: the symlinked root bites")
            self.assertEqual(0, self.mod.run_acceptance(tree, "scripts/validate_tmp.py",
                                                        "VALIDATOR", sys.executable))
        finally:
            if saved is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = saved

    def test_externalized_paths_cannot_be_inflated(self):
        """Finding 3: verify_externalized proved B' = B + P but not that P is the eligible set, so
        a corpus entry could externalise the fix itself (a source file) or a non-test file."""
        repo, root, b, c, _prime, ext = self._externalisable()
        for paths in (["scripts/tests/test_lib.py", "scripts/lib.py"], ["scripts/lib.py"]):
            prime = ext.build_base_prime(root, b, c, paths)
            meta = {"kind": "EXTERNALIZED_ORACLE", "original_base": b,
                    "externalized_paths": json.dumps(paths)}
            errs = self.mod.verify_externalized(repo, "x", prime, c, meta)
            self.assertTrue(any("derived triggers" in e for e in errs), (paths, errs))

    # ---- DeepSeek review of 667ffe4: finding 1 (the pin CHOSE the environment) ----------------
    def test_a_verdict_that_depends_on_the_temp_root_spelling_is_refused(self):
        """r51's shape: the candidate passes its oracle only when the temp root has no symlinked
        component. 2.8.9 pinned exactly that spelling and called it a repair; 2.8.10 measures the
        moving surface under a SYMLINKED root too and refuses a verdict that depends on it."""
        oracle = ("import sys, unittest\nfrom pathlib import Path\n"
                  "sys.path.insert(0, str(Path(__file__).resolve().parents[1]))\n"
                  "class T(unittest.TestCase):\n"
                  "    def test_ok(self):\n"
                  "        import feature\n"
                  "        self.assertTrue(feature.ok())\n")
        fragile = ("import os, tempfile\n"
                   "def ok():\n"
                   "    root = tempfile.gettempdir()\n"
                   "    return os.path.realpath(root) == os.path.abspath(root)\n")
        robust = "def ok():\n    return True\n"
        for name, impl, want in (("fragile", fragile, (False, "ENVIRONMENT_SENSITIVE_ACCEPTANCE")),
                                 ("robust", robust, (True, "FAIL_TO_PASS"))):
            repo, base, cand = self._repo({"README.md": "a\n"},
                                          {"scripts/feature.py": impl,
                                           "scripts/tests/test_feature.py": oracle},
                                          name=f"env-{name}")
            facts = self.mod.recompute_transition(repo, base, cand, "A_REPAIR")
            self.assertNotIn("error", facts, facts)
            (surface,) = facts["surfaces"]
            self.assertEqual((1, 0), (surface["rc_base"], surface["rc_cand"]), name)
            self.assertEqual(want, self.mod.transition_verdict("A_REPAIR", facts), name)

    def test_a_head_metadata_surface_does_not_bite_on_the_mutation_commit(self):
        """F-A1b: the first 2.8.1 draft committed the mutation under a synthetic identity, and
        validate_governance.py's HEAD-identity check (4b) then failed in the mutation for every
        pair — a new artefact bite, found by re-measuring batch 1. The mutation commit must carry
        the candidate's own metadata, so a surface that reads HEAD sees what it saw there."""
        head_identity = (
            "import subprocess, unittest\n"
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            "class Head(unittest.TestCase):\n"
            "    def test_head_identity_and_subject(self):\n"
            "        fmt = '%an|%ae|%cn|%ce|%s'\n"
            "        out = subprocess.run(['git', '-C', str(ROOT), 'log', '-1', '--format=' + fmt],\n"
            "                             capture_output=True, text=True, check=True).stdout\n"
            "        self.assertEqual('fixture|fixture@invalid|fixture|fixture@invalid',\n"
            "                         out.rsplit('|', 1)[0])\n"
            "        self.assertIn(out.strip().rsplit('|', 1)[1], ('base', 'candidate'))\n")
        repo, base, cand = self._repo({"scripts/tests/test_head.py": head_identity},
                                      {"docs/unrelated.md": "added\n"})
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        (surface,) = facts["surfaces"]
        self.assertEqual((0, 0, 0), (surface["rc_base"], surface["rc_cand"], surface["rc_mut"]))
        self.assertEqual([], facts["biting"])

    def test_a_non_ascii_added_path_is_really_removed(self):
        """`git diff --name-only` quotes a non-ASCII path ("docs/\\346\\225\\260.md"), which names no
        file, so the old loop skipped it and the "mutation" kept the addition. The frozen surface
        here is green exactly when the added file is absent, so a kept file reads as a bite."""
        absent = (
            "import unittest\n"
            "from pathlib import Path\n"
            "ROOT = Path(__file__).resolve().parents[2]\n"
            "class Absent(unittest.TestCase):\n"
            "    def test_addition_is_absent(self):\n"
            "        self.assertFalse((ROOT / 'docs' / '数据.md').exists())\n")
        repo, base, cand = self._repo({"scripts/tests/test_absent.py": absent},
                                      {"docs/数据.md": "added\n"})
        facts = self.mod.recompute_transition(repo, base, cand, "B_REGRESSION_GUARD")
        self.assertNotIn("error", facts, facts)
        (surface,) = facts["surfaces"]
        self.assertEqual((0, 1, 0), (surface["rc_base"], surface["rc_cand"], surface["rc_mut"]),
                         "the surface must see the addition at the candidate (reachability) and "
                         "must not see it in the mutation")
        self.assertEqual([], facts["biting"])


class LaunderingVariants(unittest.TestCase):
    """Ported from the second adversarial review, which demonstrated that a six-field edit of the
    shipped r03 record was counted as an admission. These are now permanent regression tests: the
    attack must stay refused."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmpdir.name)
        doc = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
        for rec in doc["records"]:                      # make citations resolvable from anywhere
            rec["evidence"] = [
                dict(e, source=["experiments/v1.2/h2-lazy-disclosure/" + s
                               if not s.startswith("experiments") else s
                               for s in (e["source"] if isinstance(e["source"], list)
                                         else [e["source"]])])
                for e in rec["evidence"]]
        self.r03 = next(r for r in doc["records"] if r["candidate_id"].startswith("r03"))
        self.r01 = next(r for r in doc["records"] if r["candidate_id"].startswith("r01"))

    def tearDown(self):
        self._tmpdir.cleanup()

    def _launder(self, rec):
        r = copy.deepcopy(rec)
        r["class"] = "A_REPAIR"
        r["class_requirements"] = {"baseline_oracle_status": "FAIL",
                                   "candidate_oracle_status": "PASS",
                                   "oracle_in_worker_scope": False,
                                   "oracle_authority": "FRAMEWORK_FROZEN"}
        r["disclosures"] = {"historical_delta_touched_oracle": False}
        r["reject_triggers"] = []
        r["pending_requirements"] = []
        r["round_admission"] = {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]}
        r.pop("externalized_paths", None)
        return r

    def test_v1_the_reviews_exact_edit(self):
        rc, out = run_validator(document(self._launder(self.r03)), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("DERIVED from the git diff", out)

    def test_v2_borrowed_corpus_identity(self):
        rec = self._launder(self.r03)
        rec["corpus_case_id"] = CASE_R06
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("does not match the corpus case", out)

    def test_v3_drop_one_derived_trigger(self):
        rec = self._launder(self.r03)
        rec["reject_triggers"] = []
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)

    def test_v4_partial_externalisation(self):
        rec = self._launder(self.r03)
        rec["externalized_paths"] = ["adapters/zcode/tests/test_project_continuity.py"]
        rec["pending_requirements"] = ["ORACLE_EXTERNALIZATION: partial"]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("DERIVED from the git diff", out)

    def test_v5_degenerate_or_mismatched_pair(self):
        rec = self._launder(self.r03)
        rec["base_sha"] = rec["candidate_sha"]
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)

    def test_v6_external_pair_asking_for_a_valid_request(self):
        rec = self._launder(self.r01)
        rc, out = run_validator(document(rec), self.tmp)
        self.assertEqual(1, rc, out)
        self.assertIn("locally verifiable revision pair", out)


class GuardUnitChecks(unittest.TestCase):
    """The ancestry and degeneracy guards are only reachable through a corpus pair that is not
    ancestor-related (every pair in today's corpus is a direct parent-child). They are still worth
    keeping, so they are exercised directly against a stubbed repository instead of being deleted
    as unreachable."""

    def _module(self):
        spec = importlib.util.spec_from_file_location("ctc_under_test", VALIDATOR)
        module = importlib.util.module_from_spec(spec)
        sys.modules["ctc_under_test"] = module
        spec.loader.exec_module(module)
        return module

    class _StubRepo:
        def __init__(self, ancestor: bool):
            self._ancestor = ancestor
            self.root = ROOT

        def has_commit(self, _sha):
            return True

        def is_ancestor(self, _base, _cand):
            return self._ancestor

        def changed_paths(self, _base, _cand):
            return []

        def changed_paths_with_status(self, _base, _cand):
            return []

    def _record(self, module, base, cand):
        return {
            "candidate_id": "guard-check", "corpus_case_id": "synthetic-case",
            "source_repository": "x", "base_sha": base, "candidate_sha": cand,
            "sha_binding": "LOCAL_REPO_VERIFIED", "class": "A_REPAIR",
            "class_considered": [{"class": "A_REPAIR", "verdict": "SHAPE_SATISFIED"}],
            "class_requirements": {"baseline_oracle_status": "FAIL",
                                   "candidate_oracle_status": "PASS",
                                   "oracle_in_worker_scope": False,
                                   "oracle_authority": "FRAMEWORK_FROZEN"},
            "disclosures": {"historical_delta_touched_oracle": False},
            "reject_triggers": [], "pending_requirements": [],
            "round_admission": {"verdict": "NOT_ADMITTED", "reason_codes": ["X"]},
            "evidence": [],
        }

    def test_ancestry_guard_fires(self):
        module = self._module()
        base, cand = "a" * 40, "b" * 40
        corpus = {"synthetic-case": (base, cand, "FlapPearLabs/agent-engineering-governance")}
        rec = self._record(module, base, cand)
        errors = module.check_record(rec, self._StubRepo(ancestor=False), ROOT, corpus)
        self.assertTrue(any("requires the candidate to descend from the base" in e for e in errors),
                        errors)

    def test_degeneracy_guard_fires(self):
        module = self._module()
        sha = "a" * 40
        corpus = {"synthetic-case": (sha, sha, "FlapPearLabs/agent-engineering-governance")}
        rec = self._record(module, sha, sha)
        errors = module.check_record(rec, self._StubRepo(ancestor=True), ROOT, corpus)
        self.assertTrue(any("degenerate" in e for e in errors), errors)


    def test_corpus_digest_is_pinned(self):
        """The identity rule's trust root is the replay corpus. Nothing else in this repository
        pins it (it is in no freeze hash and no test checks its SHA values), so the validator pins
        its digest as a literal and this test asserts the literal against the real file. Editing the
        corpus without updating both fails here — visibly, in review."""
        import hashlib
        spec = importlib.util.spec_from_file_location("ctc_corpus_pin", VALIDATOR)
        module = importlib.util.module_from_spec(spec)
        sys.modules["ctc_corpus_pin"] = module
        spec.loader.exec_module(module)
        real = hashlib.sha256((ROOT / "experiments/v1.2/replay/cases.yaml").read_bytes()).hexdigest()
        self.assertEqual(module.CORPUS_SHA256, real,
                         "the pinned corpus digest no longer matches cases.yaml — update the "
                         "constant in check_task_class.py only if the corpus change is intended and "
                         "reviewed")
        self.assertEqual(module.SCHEMA_VERSION, json.loads(
            (H2 / "task-classification-v2.json").read_text(encoding="utf-8"))["schema_version"],
            "the validator and the shipped record must declare the same schema version")

    def test_h2_admission_corpus_digest_is_pinned(self):
        """The admission anchors are a second identity root, pinned exactly like the first."""
        import hashlib
        spec = importlib.util.spec_from_file_location("ctc_h2_pin", VALIDATOR)
        module = importlib.util.module_from_spec(spec)
        sys.modules["ctc_h2_pin"] = module
        spec.loader.exec_module(module)
        real = hashlib.sha256((ROOT / module.H2_CORPUS).read_bytes()).hexdigest()
        self.assertEqual(module.H2_CORPUS_SHA256, real,
                         "the pinned H2 admission corpus digest no longer matches the file")

    def test_a_case_named_by_both_corpora_fails_closed(self):
        """A duplicate id would let one corpus shadow the other's pair; the union refuses it."""
        spec = importlib.util.spec_from_file_location("ctc_dup", VALIDATOR)
        module = importlib.util.module_from_spec(spec)
        sys.modules["ctc_dup"] = module
        spec.loader.exec_module(module)
        import hashlib
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            body = ("cases:\n  - case_id: r99-dup\n    source_repository: x/y\n"
                    "    base_sha: " + "a" * 40 + "\n    candidate_sha: " + "b" * 40 + "\n")
            for rel in (module.CASES_YAML, module.H2_CORPUS):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_text(body, encoding="utf-8")
            digest = hashlib.sha256(body.encode()).hexdigest()
            module.CORPUS_SHA256 = module.H2_CORPUS_SHA256 = digest
            repo = module.Repo(root)
            self.assertEqual({}, module.corpus_pairs(repo))
            (root / module.H2_CORPUS).write_text(body.replace("r99-dup", "r98-other"),
                                                 encoding="utf-8")
            module.H2_CORPUS_SHA256 = hashlib.sha256(
                (root / module.H2_CORPUS).read_bytes()).hexdigest()
            self.assertEqual({"r99-dup", "r98-other"}, set(module.corpus_pairs(repo)))

    def test_every_corpus_case_pair_is_pinned(self):
        """F1, round 4: pinning only the shipped digest let an author edit the corpus AND the
        constant together and keep the validator green for cases no fixture covers (r02, r05, and
        any future case). The pairs of ALL cases are therefore pinned here as literals, in a file
        that is independent of the corpus and of the validator, so any corpus edit — to any case —
        has to touch this literal too and is visible in review."""
        spec = importlib.util.spec_from_file_location("ctc_pairs_pin", VALIDATOR)
        module = importlib.util.module_from_spec(spec)
        sys.modules["ctc_pairs_pin"] = module
        spec.loader.exec_module(module)
        pairs = module.corpus_pairs(module.Repo(ROOT))
        gov = "FlapPearLabs/agent-engineering-governance"
        expected = {
            "r01-zhihu-t14-async-seam-mismatch":
                ("4b6d182f1388e27ae33820feee1589cb0188d59b",
                 "fa997c12e4c35fdb9267882747d2b55d13772ae2",
                 "FlapPearLabs/zhihu-grabber-toolkit"),
            "r02-governance-review-evidence-interface":
                ("e1da1541eb2b11f1e44f972409abde701496f4b6",
                 "2ed08f6f7ddf58b234b54afb8334e6fae32cd768", gov),
            "r03-governance-static-gate-adoption":
                ("015780be7a3f863c05509b437e4e586b4f388794",
                 "65113de69bda6802a476eefa033cf00439d49f04", gov),
            "r05-governance-local-only-precondition-fix":
                ("c08f6f8b3bbe57853a56adf3c2847e806bbb60a3",
                 "6d841d56fe8ccfc5ae3a0590fb73e15a57d38a48", gov),
            "r06-governance-zcode-adapter-reference":
                ("af4df6ae706394db5f9dec313993312392aeb516",
                 "069f8be26cc04bb4f9bf3428c1e23b310debb984", gov),
            # r07-r22: H2 Schema-v2 candidate admission, batch 1 (admission/batch-1/case-map.json)
            "r07-governance-external-findings-f1-f7":
                ("a2bfe70f6d0844012d217f340d2d2fe56f632148",
                 "295ce6514f571ff0c9d8fee72b2fc11f54abc9a9", gov),
            "r08-governance-project-continuity-contract":
                ("f40525bd9f37b883420089f0422abcedef0b7d11",
                 "af4df6ae706394db5f9dec313993312392aeb516", gov),
            "r09-governance-seam-contract-partitions":
                ("8c78e987cbf3007f69876d28c5e3b22ff92c124c",
                 "19c2c43682b4a0b26c44520e297f32c2f5a6c650", gov),
            "r10-governance-p1-t02-pre-ticket-record":
                ("4f4fe4a1aeae6677c4ad167b2c8130ac43ccd95b",
                 "e398dde43042e0e00ca99076aa9ecd3e4f8951dd", gov),
            "r11-governance-p1-t05-evidence-disposition":
                ("89b97e3b65d3f13ec21d2b837457f63f8aff7c02",
                 "1ca93655425e07933f379b3fa30a26819a4adedd", gov),
            "r12-governance-p1-t03-closure-evidence":
                ("11c798b917f3807f9fce65bcf2080ca73ee36f76",
                 "8ae4e6058bbbbf800344d7a2861c1dd82dfda6bd", gov),
            "r13-governance-p1-t06-producer-trust":
                ("8ae4e6058bbbbf800344d7a2861c1dd82dfda6bd",
                 "5c9f6a7fcfa67e081747e418ba549eb96da39a69", gov),
            "r14-governance-p1-t07-evidence-consumption":
                ("51e7604be3689f31142d17144893790000efac30",
                 "05d7c99e255fa278c332b3562e8d1fa7ccf27e5d", gov),
            "r15-governance-p1-t11-destructive-transaction":
                ("127ea0b3b11df08a048d12368164d90c2c1583d4",
                 "dc7aef63001e998d4e0de1fc59d3cfe310ed2a48", gov),
            "r16-governance-p1-t10-audit-visibility":
                ("770388d7acbd9ba818d5287e6dfe7f10c2aec961",
                 "975c559fa9cfcabc012dcb9fb96ffadf32594b03", gov),
            "r17-governance-p1-t08-evidence-lifecycle":
                ("6fd9e3eb74b36649a86572d7d20b2662bcf9863f",
                 "6856a322cdbc5282242464e068e9fb841f017642", gov),
            "r18-governance-p1-t12-single-writer":
                ("50a022f217022c254d00a465a907fa844e56a401",
                 "07430d179138595497ddd8c20a934a93b46620b9", gov),
            "r19-governance-p1-t13-learning-closure":
                ("c1681482a05e1de53b4d3c7e7619def91f94b3c6",
                 "a1cf096ae7901e27c7c7ef7407e8bf542e7bbfc6", gov),
            "r20-governance-p1-t14-model-dispatch":
                ("a1cf096ae7901e27c7c7ef7407e8bf542e7bbfc6",
                 "f1323df2670c3fa6a554ae13d50784e1f96c7603", gov),
            "r21-governance-p1-t18-defect-promotion":
                ("7d868db65d281ec7bd52219c5166ab7b5c96d690",
                 "fc7ad45838a641044b7d0404d25d497d7b11b258", gov),
            "r22-governance-v12-experiment-foundation":
                ("0404879936a3c36f5eca2b32d36f0d664464411a",
                 "0007bb3096791114d4616b599f44428e9bbfeb83", gov),
            # r23-r30: candidate admission, batch 2 (admission/batch-2/case-map.json)
            "r23-governance-bootstrap-facts-review-round-1":
                ("cf7034cb543ce8fc60d783bcdc48f1738daf1aac",
                 "825d3902597655c90393100281260cbba8697c07", gov),
            "r24-governance-bootstrap-budget-repair-round-2":
                ("825d3902597655c90393100281260cbba8697c07",
                 "4505faeaaa7a4a89a94c8751efc1f7cc0738ffe0", gov),
            "r25-governance-readme-design-decisions":
                ("833046a7c440a74925773d7b4fdadbf42c745c27",
                 "a22fe184ef783799cb1ea3ea5f7449f65a1457dd", gov),
            "r26-governance-portable-adoption-exercise":
                ("8c0075c5db0e06eec67d303955d13e214ba22782",
                 "95667e8e3d9ac9742a1a80e7dcf7f8e3b4ea5dba", gov),
            "r27-governance-memory-preset-budget-restore":
                ("3e92751a6e5490e826a130835598e5069d8fe8ce",
                 "7cadc9c445180395bf8494644ab91a4d55717438", gov),
            "r28-governance-adoption-trial-evidence":
                ("1356aa27d16fa41d0706ef2cdc11ef153d341e9d",
                 "0404879936a3c36f5eca2b32d36f0d664464411a", gov),
            "r29-governance-v12-experiment-shape-convergence":
                ("a90fb637928220396cad48d10783f9692aa70cb8",
                 "5205e5bd92317d9ad1ad53725dc14444f5201d32", gov),
            "r30-governance-h3a-replay-results":
                ("a24231483f0046052d86b3d2b27e96b3db6b2629",
                 "a652fd44bcaa0052d3185296ef2b9efd91a14639", gov),
            # r31-r33: candidate admission, batch 3 — PR merges vs first parent
            "r31-governance-pr1-global-governance-audit":
                ("8a99cbff7dfefcaca8000caafe80568c225e072b",
                 "2359283879cec3f37f6e357bd6b9a2cfeb6d45b0", gov),
            "r32-governance-pr40-replay-corpus":
                ("324fc36ec1696116c311fd440225a95aeda04a91",
                 "36b23dc9c1a888d2c4837e7fba1277ae56f8cb02", gov),
            "r33-governance-pr41-structure-delta-v0":
                ("36b23dc9c1a888d2c4837e7fba1277ae56f8cb02",
                 "5b55b6d7c3cd1fa25622b06bac43132e64f6e54a", gov),
            # r34-r52: candidate admission, batch 4 — EXTERNALIZED_ORACLE identities (base = B')
            "r34-governance-ext-enforce-anchored-schema-patterns-and":
                ("e11a8461e3cb906f1321c95589eb88256ae1a213",
                 "b88df0313b3b921978a9869b9422beb686d21f3c", gov),
            "r35-governance-ext-evaluate-character-classes-with-ecma":
                ("ffb8db0dd2122a56004dea40f492fb87a0d0dbb9",
                 "0ec774f06882b923fd89b2bb52784538a3367477", gov),
            "r36-governance-ext-evaluate-declared-patterns-with-ecma":
                ("4c104decd9fd969303c099f5c4bdc8a6eb331013",
                 "1b48d2bb44e56c453a97b82bf5c88df2e89d0791", gov),
            "r37-governance-ext-make-the-p1-t02-mandatory":
                ("a97595229f11cd7262f6a49abb433de408e94ca4",
                 "89b97e3b65d3f13ec21d2b837457f63f8aff7c02", gov),
            "r38-governance-ext-remove-local-digest-fallback-use":
                ("990177774cc4b906ec95146422356c97928b05fc",
                 "33cfcc890e38032ba932e8de30fa30d5721d737a", gov),
            "r39-governance-ext-refuse-every-scheme-form-evidence":
                ("698cd1468f33410800dad3af2972a7bc8b317d7b",
                 "51e7604be3689f31142d17144893790000efac30", gov),
            "r40-governance-ext-make-the-p1-t11-pre":
                ("072d32e2146b28fadbf1c1a1ddcf3bb5cad446a2",
                 "12c32f41898a5cec8db9346637c78800978f7549", gov),
            "r41-governance-ext-scope-the-not-auditable-rule":
                ("7a38de6f3c1f20228b5ecb5bc0bb3d0d49d75e01",
                 "0046c3648c4e6b2530c06cfce80df30c64d66ab6", gov),
            "r42-governance-ext-treat-a-partially-populated-reuse":
                ("e5c5950bca5fba0562f0ad6cd7fe7b367fc64cf3",
                 "1eaaea2c97bfe6ef36ae811298a68a52e04b554a", gov),
            "r43-governance-ext-ground-the-reuse-blank-test":
                ("f1953504789df6a0733646a2a36f5c5461805184",
                 "b03d1811f63a6dbc4f8a983c336518df6bfd492c", gov),
            "r44-governance-ext-converge-the-p1-p2-findings":
                ("ade16de80c1deb47b776874f0f1a2b10e8f7e16c",
                 "579f6d5e7762610382e4362f668efaffc51f04ce", gov),
            "r45-governance-ext-close-an-evidence-orphaning-bug":
                ("d453ec549bea6375564ac943ed35fc0b13e5e9cf",
                 "58870aaebfbd5f9051fed65865a69f5f664814ae", gov),
            "r46-governance-ext-close-the-guard-strength-gaps":
                ("2219e31686c92e58ea77def33ab98cad3d1e1608",
                 "16e30499fcb0bd45abd47f063763708662c12e65", gov),
            "r47-governance-ext-the-agents-guard-was-pinning":
                ("6dffa981941668e70062beb2922e0d2f51d47c2b",
                 "2d4bb9dcbd3cbf70c8fcdb38dbcbc130f9a4c481", gov),
            "r48-governance-ext-close-the-three-guard-holes":
                ("743235ce2c7bccbc3e3f0d58d22c51b96e199e71",
                 "4935283172615de9e0954b67fee710c3b96eb549", gov),
            "r49-governance-ext-roll-p22-up-and-stop":
                ("e1262d527d6b26acdc08a6a0b52cdb619575e11f",
                 "97ec8027d4744219e41e993ce5da361f99cda087", gov),
            "r50-governance-ext-bind-skill-evidence-reads-to":
                ("41cd7f59ca2afe6d4cb44ff5e4bce169108db340",
                 "5d61ad139ceb5408a6d96ce269f9a76f89df8b4e", gov),
            "r51-governance-ext-preserve-the-consumer-specified-skill":
                ("042be40ae27fb8b3da6a941120e9ec5504cf5d3d",
                 "f2f95f1d67cd903f8a3029b88abe62b6975b10ce", gov),
            "r52-governance-ext-apply-skill-receipt-checks-at":
                ("5abdc296c7beebf2416ce41d4d952ddaab756d75",
                 "8c0075c5db0e06eec67d303955d13e214ba22782", gov),
        }
        self.assertEqual(expected, pairs,
                         "the replay corpus's per-case pairs changed — that is an experiment-material "
                         "change: update this pin only with the corpus change, in review")
        self.assertEqual(len(expected), len(pairs))

class ShippedClassification(unittest.TestCase):
    """The repository's own classification must obey the schema it declares."""

    def test_shipped_classification_validates(self):
        proc = subprocess.run([sys.executable, str(VALIDATOR), str(CLASSIFICATION), str(ROOT)],
                              capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("TASK_CLASS_VERDICT = PASS", proc.stdout)

    def test_shipped_classification_classes_bindings_and_requests(self):
        doc = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
        by_id = {r["candidate_id"]: r for r in doc["records"]}
        self.assertEqual(3, len(by_id))
        r01 = by_id["r01-zhihu-t14-async-seam-mismatch"]
        r03 = by_id["r03-governance-static-gate-adoption"]
        r06 = by_id["r06-governance-zcode-adapter-reference"]
        self.assertEqual("A_REPAIR", r01["class"])
        self.assertEqual("C_REJECT", r03["class"])
        self.assertEqual("C_REJECT", r06["class"])
        self.assertEqual("EXTERNAL_UNVERIFIABLE_LOCALLY", r01["sha_binding"])
        self.assertEqual("LOCAL_REPO_VERIFIED", r03["sha_binding"])
        self.assertEqual("LOCAL_REPO_VERIFIED", r06["sha_binding"])
        # no task carries a valid request out of this node
        for rec in (r01, r03, r06):
            self.assertEqual("NOT_ADMITTED", rec["round_admission"]["verdict"])
        codes03 = {t["trigger"] for t in r03["reject_triggers"]}
        codes06 = {t["trigger"] for t in r06["reject_triggers"]}
        self.assertIn("OBSERVATION_COVERAGE_UNPROVEN", codes03)
        self.assertIn("ACCEPTANCE_SURFACE_IN_WORKER_SCOPE", codes03)
        # r03's delta modifies test files, so the derived trigger must be declared
        self.assertIn("WORKER_MODIFIES_TEST_ORACLE", codes03)
        self.assertEqual({"OBSERVATION_COVERAGE_UNPROVEN"}, codes06)

    def test_v2_rejects_the_registered_task_t02_as_specified(self):
        """The claim that this schema is not tailored to admit existing tasks, made mechanical.

        Two facts are read from the frozen registry, not asserted here:
          * `ruff.toml` is inside t02's scope prefixes, so the file that decides the linter's
            verdict is a worker deliverable;
          * the "select is non-empty and correctness-class" requirement is a JUDGMENT entry, i.e.
            prose, so nothing mechanical pins the rule selection.
        A t02-shaped record claiming A_REPAIR while carrying those two triggers must be refused.
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
