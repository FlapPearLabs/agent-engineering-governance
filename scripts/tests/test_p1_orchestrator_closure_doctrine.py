"""
Counterexample-driven regression tests for Orchestrator Closure Doctrine (M1-M9)
and machine-enforced closure predicate validation.
"""

import unittest
from pathlib import Path
import sys

# Add scripts directory to path
SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from validate_governance import check_closure_evidence_predicates

class TestOrchestratorClosureDoctrinePredicates(unittest.TestCase):
    """
    Validates machine-enforced rejection of the five canonical orchestrator closure errors:
    V1: Premature post-integration close (close before CI completion, or failed CI).
    V2: Review summary without independent referenceable raw review artifacts.
    V3: Open P0/P1 finding requiring change but candidate SHA is unchanged without amendment.
    V4: Scope amendment relies on chat rather than persisted canonical authority.
    V5: Guarantee overclaim relative to declared threat model.
    """

    def test_v1_premature_close_fails(self):
        # Case 1: close timestamp <= ci completion timestamp
        evidence = {
            "requires_post_integration_ci": True,
            "post_integration_ci_status": "completed",
            "post_integration_ci_conclusion": "success",
            "post_integration_ci_completed_at": "2026-09-21T18:11:47Z",
            "ticket_close_timestamp": "2026-09-21T18:09:55Z", # 2 mins before CI finished!
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("premature close", reason)

    def test_v1_incomplete_or_failed_ci_fails(self):
        # Case 2: CI failed or still running
        evidence = {
            "requires_post_integration_ci": True,
            "post_integration_ci_status": "in_progress",
            "post_integration_ci_conclusion": None,
            "post_integration_ci_completed_at": None,
            "ticket_close_timestamp": "2026-09-21T18:15:00Z",
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("post-integration CI not completed with success", reason)

    def test_v1_legal_order_passes(self):
        # Legal: CI completed success at 18:11:47, close at 18:15:00
        evidence = {
            "requires_post_integration_ci": True,
            "post_integration_ci_status": "completed",
            "post_integration_ci_conclusion": "success",
            "post_integration_ci_completed_at": "2026-09-21T18:11:47Z",
            "ticket_close_timestamp": "2026-09-21T18:15:00Z",
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertTrue(ok)
        self.assertEqual(reason, "OK")

    def test_v2_review_summary_without_artifacts_fails(self):
        # Only orchestrator summary text, no referenceable raw review artifacts
        evidence = {
            "requires_post_integration_ci": False,
            "requires_dual_independent_review": True,
            "independent_review_refs": [], # Empty!
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("V2: review summary without independent raw artifacts", reason)

    def test_v2_dual_independent_artifacts_pass(self):
        evidence = {
            "requires_post_integration_ci": False,
            "requires_dual_independent_review": True,
            "independent_review_refs": [
                "references/reviews/rev_a_exact_sha.json",
                "references/reviews/rev_b_exact_sha.json"
            ],
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertTrue(ok)

    def test_v3_open_finding_requiring_change_without_new_sha_fails(self):
        evidence = {
            "requires_post_integration_ci": False,
            "candidate_sha": "1e711d0a2d73c369abd1637b3a904c99efae73e4",
            "findings": [
                {
                    "id": "F-02",
                    "severity": "P1",
                    "status": "open",
                    "requires_change": True,
                    "reviewed_sha": "1e711d0a2d73c369abd1637b3a904c99efae73e4",
                }
            ],
            "no_change_authorized": False,
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("V3: finding F-02 requires change but candidate_sha equals reviewed_sha", reason)

    def test_v3_open_finding_with_new_sha_passes(self):
        evidence = {
            "requires_post_integration_ci": False,
            "candidate_sha": "2a890e1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f", # New SHA!
            "findings": [
                {
                    "id": "F-02",
                    "severity": "P1",
                    "status": "open",
                    "requires_change": True,
                    "reviewed_sha": "1e711d0a2d73c369abd1637b3a904c99efae73e4",
                }
            ],
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertTrue(ok)

    def test_v4_chat_scope_amendment_not_persisted_fails(self):
        evidence = {
            "requires_post_integration_ci": False,
            "relies_on_scope_amendment": True,
            "persisted_scope_amendment_ref": None, # Relies only on chat context!
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("V4: scope amendment relies on chat/orchestrator context without persisted authority ref", reason)

    def test_v4_persisted_scope_amendment_passes(self):
        evidence = {
            "requires_post_integration_ci": False,
            "relies_on_scope_amendment": True,
            "persisted_scope_amendment_ref": "https://github.com/FlapPearLabs/zhihu-grabber-toolkit/issues/94#issuecomment-5770985055",
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertTrue(ok)

    def test_v5_guarantee_overclaim_fails(self):
        evidence = {
            "requires_post_integration_ci": False,
            "threat_model": "PROCESS_CRASH_RECOVERY",
            "declared_guarantees": ["PROCESS_CRASH_RECOVERY", "STRICT_ATOMIC_REPLACEMENT"],
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("V5: guarantee overclaim", reason)

    def test_v5_consistent_guarantee_passes(self):
        evidence = {
            "requires_post_integration_ci": False,
            "threat_model": "PROCESS_CRASH_RECOVERY",
            "declared_guarantees": ["PROCESS_CRASH_RECOVERY", "FAIL_SAFE_RECOVERY"],
        }
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertTrue(ok)

if __name__ == "__main__":
    unittest.main()
