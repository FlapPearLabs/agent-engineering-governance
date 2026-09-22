"""
Counterexample-driven regression tests for Orchestrator Closure Doctrine (M1-M9)
and machine-enforced closure predicate validation.
"""

import unittest
import os
from pathlib import Path
import subprocess
import tempfile
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

    def test_github_merge_committer_identity_positive_and_negative(self):
        import scripts.validate_public_release as vpr
        # Positive case 1: normal commit with canonical public identity
        self.assertEqual(vpr.identity_problems("committer", "FlapPearLabs", "151931662+FlapPearLabs@users.noreply.github.com", is_merge_commit=False), [])
        # Positive case 2: merge commit with GitHub committer
        self.assertEqual(vpr.identity_problems("committer", "GitHub", "noreply@github.com", is_merge_commit=True), [])
        # Negative case 1: normal commit (is_merge_commit=False) with GitHub committer must FAIL
        self.assertNotEqual(vpr.identity_problems("committer", "GitHub", "noreply@github.com", is_merge_commit=False), [])
        # Negative case 2: merge commit with non-canonical personal author/committer must FAIL
        self.assertNotEqual(vpr.identity_problems("committer", "random_user", "random@example.com", is_merge_commit=True), [])
        self.assertNotEqual(vpr.identity_problems("author", "random_user", "random@example.com", is_merge_commit=True), [])

    def test_github_merge_identity_regression_is_discovered(self):
        test_names = {
            test.id().rsplit(".", 1)[-1]
            for test in unittest.defaultTestLoader.loadTestsFromTestCase(type(self))
        }
        self.assertIn("test_github_merge_committer_identity_positive_and_negative", test_names)

    def test_head_commit_metadata_counts_only_header_parents(self):
        import scripts.validate_public_release as vpr

        def commit(repo, tree, message, parents=(), author_name="FlapPearLabs",
                   author_email="151931662+FlapPearLabs@users.noreply.github.com",
                   committer_name=None, committer_email=None):
            committer_name = committer_name or author_name
            committer_email = committer_email or author_email
            env = os.environ.copy()
            env.update({
                "GIT_AUTHOR_NAME": author_name,
                "GIT_AUTHOR_EMAIL": author_email,
                "GIT_COMMITTER_NAME": committer_name,
                "GIT_COMMITTER_EMAIL": committer_email,
            })
            parent_args = [arg for parent in parents for arg in ("-p", parent)]
            result = subprocess.run(
                ["git", "-C", str(repo), "commit-tree", tree, *parent_args],
                input=message,
                capture_output=True,
                text=True,
                env=env,
                check=True,
            )
            return result.stdout.strip()

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "symbolic-ref", "HEAD", "refs/heads/test"], check=True)
            tree = subprocess.run(
                ["git", "-C", str(repo), "mktree"], input="", capture_output=True,
                text=True, check=True,
            ).stdout.strip()

            base = commit(repo, tree, "base\n")
            single_parent = commit(repo, tree, "A\n\nparent #123\n", (base,))
            (repo / ".git" / "shallow").write_text(single_parent + "\n")
            subprocess.run(["git", "-C", str(repo), "update-ref", "refs/heads/test", single_parent], check=True)
            case_a = vpr.head_commit_metadata(repo)
            self.assertEqual(case_a["is_merge_commit"], "false")

            second_parent = commit(repo, tree, "B\n")
            merge = commit(repo, tree, "D\n", (single_parent, second_parent),
                           committer_name="GitHub", committer_email="noreply@github.com")
            # B: true double-parent shape; D: the same legitimate GitHub merge
            # shape, whose GitHub committer identity must remain accepted.
            subprocess.run(["git", "-C", str(repo), "update-ref", "refs/heads/test", merge], check=True)
            case_b = vpr.head_commit_metadata(repo)
            self.assertEqual(case_b["is_merge_commit"], "true")
            self.assertEqual(vpr.identity_problems(
                "committer", case_b["committer_name"], case_b["committer_email"],
                is_merge_commit=case_b["is_merge_commit"] == "true"), [])

            canonical_single = commit(repo, tree, "C\n", (base,))
            subprocess.run(["git", "-C", str(repo), "update-ref", "refs/heads/test", canonical_single], check=True)
            case_c = vpr.head_commit_metadata(repo)
            self.assertEqual(case_c["is_merge_commit"], "false")
            self.assertEqual(vpr.identity_problems(
                "committer", case_c["committer_name"], case_c["committer_email"],
                is_merge_commit=False), [])

if __name__ == "__main__":
    unittest.main()
