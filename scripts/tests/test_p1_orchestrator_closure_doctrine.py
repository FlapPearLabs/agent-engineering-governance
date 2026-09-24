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

def complete_evidence():
    sha = "a" * 40
    return {
        "candidate_sha": sha,
        "post_integration_ci_status": "completed",
        "post_integration_ci_conclusion": "success",
        "post_integration_ci_completed_at": "2026-09-21T18:11:47Z",
        "post_integration_ci_run_ref": "https://example.test/ci/1",
        "post_integration_verify_ref": "https://example.test/verify/1",
        "REACHABILITY_APPLICABILITY": "REQUIRED",
        "REAL_ENTRYPOINT": "bin/production-entry",
        "PRODUCTION_CALL_CHAIN": "production entry -> wiring -> effect",
        "OBSERVED_PRODUCTION_EFFECT": "effect observed on live entry",
        "PRODUCTION_CALLERS": ["production entry"],
        "RUNTIME_REACHABLE": "TRUE",
        "EVIDENCE_REF": "https://example.test/evidence/reachability",
        "INTEGRATION_COMPLETE": "TRUE",
        "pre_close_checked_at": "2026-09-21T18:15:00Z",
        "pre_close_comment_ref": "https://github.com/example/repo/issues/1#issuecomment-1",
        "independent_review_refs": [
            {"reviewer": "A", "ref": "https://example.test/review/a", "reviewed_sha": sha},
            {"reviewer": "B", "ref": "https://example.test/review/b", "reviewed_sha": sha},
        ],
        "findings": [],
    }

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
        evidence = complete_evidence()
        evidence["ticket_close_timestamp"] = "2026-09-21T18:09:55Z"
        ok, reason = check_closure_evidence_predicates(evidence, post_close=True)
        self.assertFalse(ok)
        self.assertIn("premature close", reason)

    def test_v1_incomplete_or_failed_ci_fails(self):
        evidence = complete_evidence()
        evidence["post_integration_ci_status"] = "in_progress"
        evidence["post_integration_ci_conclusion"] = None
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("post-integration CI", reason)

    def test_v1_legal_order_passes(self):
        evidence = complete_evidence()
        evidence["ticket_close_timestamp"] = "2026-09-21T18:15:01Z"
        ok, reason = check_closure_evidence_predicates(evidence, post_close=True)
        self.assertTrue(ok)
        self.assertEqual(reason, "OK")

    def test_v2_review_summary_without_artifacts_fails(self):
        evidence = complete_evidence()
        evidence["independent_review_refs"] = []
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("V2: two independent raw review references", reason)

    def test_v2_dual_independent_artifacts_pass(self):
        evidence = complete_evidence()
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertTrue(ok)

    def test_v3_open_finding_requiring_change_without_new_sha_fails(self):
        evidence = complete_evidence()
        evidence["findings"] = [{"id": "F-02", "severity": "P1", "status": "open",
                                 "requires_change": True, "reviewed_sha": evidence["candidate_sha"]}]
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("V3: finding F-02 remains open", reason)

    def test_v3_open_finding_with_new_sha_passes(self):
        evidence = complete_evidence()
        evidence["findings"] = [{"id": "F-02", "severity": "P1", "status": "resolved",
                                 "requires_change": True, "reviewed_sha": "b" * 40,
                                 "repair_sha": evidence["candidate_sha"]}]
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertTrue(ok)

    def test_v4_chat_scope_amendment_not_persisted_fails(self):
        evidence = complete_evidence()
        evidence.update(relies_on_scope_amendment=True, persisted_scope_amendment_ref=None)
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("V4: scope amendment lacks persisted authority ref", reason)

    def test_v4_persisted_scope_amendment_passes(self):
        evidence = complete_evidence()
        evidence.update(relies_on_scope_amendment=True,
                        persisted_scope_amendment_ref="https://example.test/issues/94#amendment")
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertTrue(ok)

    def test_v5_guarantee_overclaim_fails(self):
        evidence = complete_evidence()
        evidence.update(threat_model="PROCESS_CRASH_RECOVERY",
                        declared_guarantees=["PROCESS_CRASH_RECOVERY", "STRICT_ATOMIC_REPLACEMENT"])
        ok, reason = check_closure_evidence_predicates(evidence)
        self.assertFalse(ok)
        self.assertIn("V5: guarantee overclaim", reason)

    def test_v5_consistent_guarantee_passes(self):
        evidence = complete_evidence()
        evidence.update(threat_model="PROCESS_CRASH_RECOVERY",
                        declared_guarantees=["PROCESS_CRASH_RECOVERY", "FAIL_SAFE_RECOVERY"])
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

    def test_malformed_parent_header_cannot_enable_merge_exception(self):
        import scripts.validate_public_release as vpr

        def commit(repo, tree, message, parents=(), committer_name="GitHub",
                   committer_email="noreply@github.com"):
            env = os.environ.copy()
            env.update({
                "GIT_AUTHOR_NAME": "FlapPearLabs",
                "GIT_AUTHOR_EMAIL": "151931662+FlapPearLabs@users.noreply.github.com",
                "GIT_COMMITTER_NAME": committer_name,
                "GIT_COMMITTER_EMAIL": committer_email,
            })
            parent_args = [arg for parent in parents for arg in ("-p", parent)]
            return subprocess.run(
                ["git", "-C", str(repo), "commit-tree", tree, *parent_args],
                input=message, capture_output=True, text=True, env=env, check=True,
            ).stdout.strip()

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "symbolic-ref", "HEAD", "refs/heads/test"], check=True)
            tree = subprocess.run(
                ["git", "-C", str(repo), "mktree"], input="", capture_output=True,
                text=True, check=True,
            ).stdout.strip()
            real_parent = commit(repo, tree, "base\n", committer_name="FlapPearLabs",
                                 committer_email="151931662+FlapPearLabs@users.noreply.github.com")
            valid_single = commit(repo, tree, "A\n", (real_parent,))
            raw = subprocess.run(
                ["git", "-C", str(repo), "cat-file", "-p", valid_single],
                capture_output=True, text=True, check=True,
            ).stdout
            raw = raw.replace("\n\nA\n", "\nparent #987\n\nA\n", 1)
            malformed = subprocess.run(
                ["git", "-C", str(repo), "hash-object", "-t", "commit", "-w", "--stdin"],
                input=raw, capture_output=True, text=True, check=True,
            ).stdout.strip()
            subprocess.run(["git", "-C", str(repo), "update-ref", "refs/heads/test", malformed], check=True)

            rev_list = subprocess.run(
                ["git", "-C", str(repo), "rev-list", "--parents", "-n", "1", "HEAD"],
                capture_output=True, text=True, check=True,
            ).stdout.split()
            self.assertEqual(len(rev_list), 2)
            meta = vpr.head_commit_metadata(repo)
            self.assertEqual(meta["is_merge_commit"], "false")
            self.assertNotEqual(vpr.identity_problems(
                "committer", meta["committer_name"], meta["committer_email"],
                is_merge_commit=meta["is_merge_commit"] == "true"), [])

    def test_duplicate_parent_oid_does_not_enable_merge_exception(self):
        import scripts.validate_public_release as vpr

        tested_formats = []
        for object_format in ("sha1", "sha256"):
            with self.subTest(object_format=object_format):
                with tempfile.TemporaryDirectory() as tmp:
                    repo = Path(tmp)
                    init_args = ["git", "init", "-q"]
                    if object_format == "sha256":
                        init_args.append("--object-format=sha256")
                    init_args.append(str(repo))
                    initialized = subprocess.run(init_args, capture_output=True, text=True)
                    if initialized.returncode != 0:
                        if object_format == "sha256":
                            continue
                        self.fail(initialized.stderr)
                    tested_formats.append(object_format)
                    subprocess.run(["git", "-C", str(repo), "symbolic-ref", "HEAD", "refs/heads/test"], check=True)
                    tree = subprocess.run(
                        ["git", "-C", str(repo), "mktree"], input="", capture_output=True,
                        text=True, check=True,
                    ).stdout.strip()

                    def commit(message, parents=(), committer_name="FlapPearLabs",
                               committer_email="151931662+FlapPearLabs@users.noreply.github.com"):
                        env = os.environ.copy()
                        env.update({
                            "GIT_AUTHOR_NAME": "FlapPearLabs",
                            "GIT_AUTHOR_EMAIL": "151931662+FlapPearLabs@users.noreply.github.com",
                            "GIT_COMMITTER_NAME": committer_name,
                            "GIT_COMMITTER_EMAIL": committer_email,
                        })
                        parent_args = [arg for parent in parents for arg in ("-p", parent)]
                        return subprocess.run(
                            ["git", "-C", str(repo), "commit-tree", tree, *parent_args],
                            input=message, capture_output=True, text=True, env=env, check=True,
                        ).stdout.strip()

                    real_parent = commit("base\n")
                    valid_single = commit(
                        "single\n", (real_parent,),
                        committer_name="GitHub", committer_email="noreply@github.com",
                    )
                    raw = subprocess.run(
                        ["git", "-C", str(repo), "cat-file", "-p", valid_single],
                        capture_output=True, text=True, check=True,
                    ).stdout
                    parent_line = next(
                        line for line in raw.splitlines() if line.startswith("parent ")
                    )
                    raw = raw.replace(parent_line + "\n", parent_line + "\n" + parent_line + "\n", 1)
                    duplicate_head = subprocess.run(
                        ["git", "-C", str(repo), "hash-object", "-t", "commit", "-w", "--stdin"],
                        input=raw, capture_output=True, text=True, check=True,
                    ).stdout.strip()
                    subprocess.run(["git", "-C", str(repo), "update-ref", "refs/heads/test", duplicate_head], check=True)

                    header = raw.split("\n\n", 1)[0]
                    parent_oids = [
                        line[len("parent "):] for line in header.splitlines()
                        if line.startswith("parent ")
                    ]
                    self.assertEqual(len(parent_oids), 2)
                    self.assertEqual(len(set(parent_oids)), 1)
                    self.assertEqual(len(parent_oids[0]), 40 if object_format == "sha1" else 64)
                    meta = vpr.head_commit_metadata(repo)
                    self.assertEqual(meta["is_merge_commit"], "false")
                    self.assertNotEqual(vpr.identity_problems(
                        "committer", meta["committer_name"], meta["committer_email"],
                        is_merge_commit=meta["is_merge_commit"] == "true"), [])

        self.assertIn("sha1", tested_formats)

if __name__ == "__main__":
    unittest.main()
