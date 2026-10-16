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
    return {"schema": "ELIGIBILITY_SCHEMA_V2", "schema_version": "2.8.0", "records": list(records)}


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
