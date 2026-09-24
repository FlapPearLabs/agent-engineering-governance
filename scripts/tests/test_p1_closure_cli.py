"""Real pre-close entrypoint and fail-closed closure evidence regressions."""

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GATE = ROOT / "scripts" / "validate_governance.py"
sys.path.insert(0, str(ROOT / "scripts"))
from validate_governance import check_closure_evidence_predicates


def evidence():
    sha = "a" * 40
    return {
        "candidate_sha": sha,
        "post_integration_ci_status": "completed",
        "post_integration_ci_conclusion": "success",
        "post_integration_ci_completed_at": "2026-09-21T18:11:47Z",
        "post_integration_ci_run_ref": "https://example.test/ci/1",
        "pre_close_checked_at": "2026-09-21T18:15:00Z",
        "pre_close_comment_ref": "https://github.com/example/repo/issues/1#issuecomment-1",
        "post_integration_verify_ref": "https://example.test/verify/1",
        "REACHABILITY_APPLICABILITY": "REQUIRED",
        "REAL_ENTRYPOINT": "bin/production-entry",
        "PRODUCTION_CALL_CHAIN": "production entry -> wiring -> effect",
        "OBSERVED_PRODUCTION_EFFECT": "effect observed on live entry",
        "PRODUCTION_CALLERS": ["production entry"],
        "RUNTIME_REACHABLE": "TRUE",
        "EVIDENCE_REF": "https://example.test/evidence/reachability",
        "INTEGRATION_COMPLETE": "TRUE",
        "independent_review_refs": [
            {"reviewer": "A", "ref": "https://example.test/review/a", "reviewed_sha": sha},
            {"reviewer": "B", "ref": "https://example.test/review/b", "reviewed_sha": sha},
        ],
        "findings": [],
    }


class ClosureGateTests(unittest.TestCase):
    def test_required_reachability_six_slots_fail_closed(self):
        for field in ("REAL_ENTRYPOINT", "PRODUCTION_CALL_CHAIN",
                      "OBSERVED_PRODUCTION_EFFECT", "PRODUCTION_CALLERS",
                      "RUNTIME_REACHABLE", "EVIDENCE_REF"):
            item = evidence()
            item[field] = [] if field == "PRODUCTION_CALLERS" else ""
            with self.subTest(field=field):
                self.assertFalse(check_closure_evidence_predicates(item)[0])
        for field, value in (("RUNTIME_REACHABLE", "FALSE"),
                             ("INTEGRATION_COMPLETE", "FALSE")):
            item = evidence()
            item[field] = value
            with self.subTest(field=field):
                self.assertFalse(check_closure_evidence_predicates(item)[0])

    def test_na_requires_policy_reason_and_reviewer_acceptance(self):
        item = evidence()
        item["REACHABILITY_APPLICABILITY"] = "N/A"
        for field in ("REAL_ENTRYPOINT", "PRODUCTION_CALL_CHAIN",
                      "OBSERVED_PRODUCTION_EFFECT", "PRODUCTION_CALLERS",
                      "RUNTIME_REACHABLE", "EVIDENCE_REF"):
            item.pop(field)
        self.assertFalse(check_closure_evidence_predicates(item)[0])
        item["REACHABILITY_APPLICABILITY_REASON"] = "Pure documentation; no runtime seam"
        self.assertFalse(check_closure_evidence_predicates(item)[0])
        item["REACHABILITY_APPLICABILITY_ACCEPTANCE_REF"] = "https://example.test/review/accepted-na"
        self.assertTrue(check_closure_evidence_predicates(item)[0])

    def test_pre_close_emits_cli_checked_at_not_caller_time(self):
        item = evidence()
        item["pre_close_checked_at"] = "2099-01-01T00:00:00Z"
        run = subprocess.run([sys.executable, str(GATE), "--pre-close"],
                             input=json.dumps(item), text=True, capture_output=True)
        self.assertEqual(0, run.returncode, run.stdout + run.stderr)
        output = json.loads(run.stdout)
        self.assertEqual(item["candidate_sha"], output["candidate_sha"])
        self.assertNotEqual(item["pre_close_checked_at"], output["checked_at"])

    def test_post_close_rejects_close_before_precheck(self):
        item = evidence()
        item["ticket_close_timestamp"] = "2026-09-21T18:14:00Z"
        self.assertFalse(check_closure_evidence_predicates(item, post_close=True)[0])

    def test_post_close_requires_persisted_precheck_reference(self):
        item = evidence()
        item["ticket_close_timestamp"] = "2026-09-21T18:15:01Z"
        item.pop("pre_close_comment_ref")
        self.assertFalse(check_closure_evidence_predicates(item, post_close=True)[0])
        item["pre_close_comment_ref"] = "https://example.test/not-a-github-comment"
        self.assertFalse(check_closure_evidence_predicates(item, post_close=True)[0])

    def test_missing_m2_timestamps_fail(self):
        for field in ("post_integration_ci_completed_at", "pre_close_checked_at"):
            item = evidence()
            item.pop(field)
            with self.subTest(field=field):
                self.assertFalse(check_closure_evidence_predicates(item)[0])

    def test_duplicate_or_summary_only_review_refs_fail(self):
        for refs in ([evidence()["independent_review_refs"][0]] * 2,
                     ["Reviewer A PASS", "Reviewer B PASS"]):
            item = evidence()
            item["independent_review_refs"] = refs
            with self.subTest(refs=refs):
                self.assertFalse(check_closure_evidence_predicates(item)[0])

    def test_change_finding_needs_artifact_and_fresh_review(self):
        item = evidence()
        item["findings"] = [{"id": "F1", "severity": "P1", "status": "open",
                             "requires_change": True, "reviewed_sha": "b" * 40}]
        self.assertFalse(check_closure_evidence_predicates(item)[0])
        item["findings"][0]["repair_sha"] = item["candidate_sha"]
        self.assertFalse(check_closure_evidence_predicates(item)[0])
        item["findings"][0]["status"] = "resolved"
        item["findings"][0].pop("reviewed_sha")
        self.assertFalse(check_closure_evidence_predicates(item)[0])
        item["findings"][0]["reviewed_sha"] = "b" * 40
        self.assertTrue(check_closure_evidence_predicates(item)[0])

    def test_no_change_ruling_must_be_independent_and_referenceable(self):
        item = evidence()
        item["findings"] = [{"id": "F2", "severity": "P1", "status": "resolved",
                             "requires_change": False,
                             "independent_no_change_ruling_ref": "https://example.test/review/a"}]
        self.assertFalse(check_closure_evidence_predicates(item)[0])
        item["independent_review_refs"][0]["decision"] = "NO_CHANGE_REQUIRED"
        self.assertTrue(check_closure_evidence_predicates(item)[0])

    def test_boolean_exemptions_cannot_skip_required_gates(self):
        item = evidence()
        item.update(requires_post_integration_ci=False,
                    requires_dual_independent_review=False)
        self.assertFalse(check_closure_evidence_predicates(item)[0])

    def test_real_cli_rejects_missing_evidence_and_accepts_complete_evidence(self):
        for item, expected in (({}, 1), (evidence(), 0)):
            run = subprocess.run([sys.executable, str(GATE), "--pre-close"],
                                 input=json.dumps(item), text=True,
                                 capture_output=True)
            self.assertEqual(expected, run.returncode, run.stdout + run.stderr)
            self.assertEqual(expected == 0, json.loads(run.stdout)["close_ready"])

    def test_post_close_requires_actual_timestamp_after_ci(self):
        item = evidence()
        for closed_at, expected in ((None, 1),
                                    ("2026-09-21T18:11:47Z", 1),
                                    ("2026-09-21T18:15:01Z", 0)):
            if closed_at is None:
                item.pop("ticket_close_timestamp", None)
            else:
                item["ticket_close_timestamp"] = closed_at
            run = subprocess.run([sys.executable, str(GATE), "--post-close"],
                                 input=json.dumps(item), text=True,
                                 capture_output=True)
            self.assertEqual(expected, run.returncode, run.stdout + run.stderr)


if __name__ == "__main__":
    unittest.main()
