"""Counterexamples for task-bound Skill records, not catalog installation counts."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "scripts/skill_execution.py"


class SkillExecutionTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(CLI.exists(), "CONTRACT_ABSENT: Skill execution consumer")
        spec = importlib.util.spec_from_file_location("skill_execution", CLI)
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.subject = {
            "repo": "FlapPearLabs/agent-engineering-governance",
            "baseSha": "1" * 40, "candidateSha": "2" * 40,
            "task": "skill-contract", "phase": "implementation", "role": "PARENT",
        }
        self.pack = {
            "schemaVersion": 1, "subject": self.subject.copy(),
            "selectionBasis": "Authorized Python validator; requirements-dev.txt and ruff.toml",
            "domainAssessment": "Registry has no matching specialized Python validation Skill",
            "skills": [{
                "name": "implement", "kind": "WORKFLOW", "reason": "MEDIUM CODE trigger",
                "status": "APPLIED", "sourceRef": "registry:implement@version",
                "readEvidenceRef": "read.json", "executionEvidenceRefs": ["execution.json"],
                "reportRef": "report.json", "fallbackReason": None,
            }],
            "artifacts": [],
        }
        self.artifact("read.json", {"observation": "full SKILL.md read tool event"})
        self.artifact("execution.json", {"observation": "execution trace and resulting patch"})
        self.report()

    def artifact(self, name, content):
        data = json.dumps(content).encode()
        (self.root / name).write_bytes(data)
        entry = {"location": name, "contentDigest": "sha256:" + hashlib.sha256(data).hexdigest()}
        self.pack["artifacts"] = [a for a in self.pack["artifacts"] if a["location"] != name]
        self.pack["artifacts"].append(entry)

    def report(self, **changes):
        report = {
            "skill": "implement", "status": self.pack["skills"][0]["status"],
            "summary": "Applied the authorized contract within the lane",
            "result": "Validator change and counterexamples", "limitations": "Semantic review pending",
            "evidenceRefs": ["read.json", "execution.json"], "audience": "USER",
        }
        report.update(changes)
        self.artifact("report.json", report)

    def check(self, **changes):
        options = dict(expected_subject=self.subject, required_skills=["implement"],
                       evidence_root=self.root)
        options.update(changes)
        return self.module.validate_receipt(self.pack, **options)

    def rejected(self, code):
        result = self.check()
        self.assertFalse(result["recordValid"], result)
        self.assertIn(code, [x["reason"] for x in result["findings"]], result)

    def test_applied_record_is_not_semantic_or_host_pass(self):
        result = self.check()
        self.assertTrue(result["recordValid"], result)
        self.assertFalse(result["semanticApplicationVerified"])
        self.assertFalse(result["hostEnforcementVerified"])

    def test_missing_skill_can_finish_truthful_fallback(self):
        row = self.pack["skills"][0]
        row.update(status="FALLBACK", sourceRef=None, readEvidenceRef=None,
                   fallbackReason="SKILL_UNAVAILABLE: registry lookup found no implement")
        self.report(evidenceRefs=["execution.json"])
        self.assertTrue(self.check()["recordValid"])

    def test_installed_name_without_read_cannot_claim_applied(self):
        self.pack["skills"][0]["readEvidenceRef"] = None
        self.rejected("FULL_READ_EVIDENCE_REQUIRED")

    def test_read_without_execution_is_not_application(self):
        self.pack["skills"][0]["executionEvidenceRefs"] = []
        self.rejected("MIN_ITEMS_VIOLATION")

    def test_absent_post_use_report_is_rejected(self):
        self.pack["skills"][0]["reportRef"] = "absent.json"
        self.rejected("ARTIFACT_UNDECLARED")

    def test_report_must_match_skill_and_status(self):
        self.report(skill="to-spec")
        self.rejected("REPORT_MISMATCH")
        self.report(status="FALLBACK")
        self.rejected("REPORT_MISMATCH")

    def test_parent_report_goes_to_user_and_worker_to_parent(self):
        self.report(audience="PARENT")
        self.rejected("REPORT_AUDIENCE_MISMATCH")
        self.subject["role"] = "WORKER"
        self.pack["subject"]["role"] = "WORKER"
        self.assertTrue(self.check()["recordValid"])

    def test_report_must_cite_execution_and_read(self):
        self.report(evidenceRefs=[])
        self.rejected("REPORT_EVIDENCE_MISSING")

    def test_optional_skill_does_not_cover_required_workflow_skill(self):
        self.pack["skills"][0]["name"] = "simplify-code"
        self.rejected("REQUIRED_SKILL_MISSING")

    def test_required_selection_cannot_hide_as_empty_input(self):
        result = self.check(required_skills=[])
        self.assertFalse(result["recordValid"])
        self.assertIn("REQUIREMENT_INPUT_REQUIRED", [x["reason"] for x in result["findings"]])
        self.pack["skills"] = []
        self.pack["artifacts"] = []
        self.assertTrue(self.check(required_skills=[], no_required_reason="LOW documentation only")["recordValid"])

    def test_unverified_cannot_be_completed(self):
        self.pack["skills"][0]["status"] = "UNVERIFIED"
        self.rejected("SKILL_UNVERIFIED")

    def test_template_text_or_blank_report_is_not_execution_evidence(self):
        self.pack["selectionBasis"] = "${SELECTION_BASIS}"
        self.rejected("UNFINISHED_RECORD_TEXT")
        self.pack["selectionBasis"] = "Authorized phase and repository configuration"
        self.report(result="   ")
        self.rejected("UNFINISHED_REPORT_TEXT")

    def test_specialized_skill_is_covered_without_altering_catalog(self):
        self.pack["skills"][0].update(name="python-validation", kind="DOMAIN",
                                     reason="Explicit user requirement matches Python validator surface")
        self.report(skill="python-validation")
        result = self.check(required_skills=["python-validation"])
        self.assertTrue(result["recordValid"], result)

    def test_fallback_requires_reason_and_must_not_claim_applied(self):
        self.pack["skills"][0].update(status="FALLBACK", fallbackReason="")
        self.rejected("FALLBACK_REASON_REQUIRED")

    def test_stale_subject_is_rejected(self):
        self.pack["subject"]["candidateSha"] = "3" * 40
        self.rejected("SUBJECT_MISMATCH")

    def test_digest_mismatch_is_not_verified(self):
        (self.root / "execution.json").write_text("changed")
        self.rejected("ARTIFACT_DIGEST_MISMATCH")

    def test_duplicate_skill_and_artifact_are_rejected(self):
        self.pack["skills"].append(copy.deepcopy(self.pack["skills"][0]))
        self.rejected("DUPLICATE_SKILL")
        self.pack["skills"].pop()
        self.pack["artifacts"].append(self.pack["artifacts"][0].copy())
        self.rejected("DUPLICATE_ARTIFACT")

    def test_no_path_escape_url_drive_or_symlink_retrieval(self):
        for location in ("../outside", "https://example.invalid/trace", "C:\\outside", "/outside"):
            with self.subTest(location=location):
                old = copy.deepcopy(self.pack["artifacts"])
                self.pack["artifacts"][0]["location"] = location
                self.rejected("ARTIFACT_PATH_FORBIDDEN")
                self.pack["artifacts"] = old
        outside = self.root.parent / (self.root.name + "-outside")
        outside.write_text("outside")
        self.addCleanup(outside.unlink)
        (self.root / "link").symlink_to(outside)
        self.pack["artifacts"][0]["location"] = "link"
        self.rejected("ARTIFACT_PATH_FORBIDDEN")

    def test_reads_are_bounded(self):
        (self.root / "execution.json").write_bytes(b"x" * (self.module.MAX_BYTES + 1))
        self.rejected("ARTIFACT_UNREADABLE")

    def test_empty_artifact_is_not_evidence(self):
        self.artifact("execution.json", "")
        data = b" "
        (self.root / "execution.json").write_bytes(data)
        entry = next(a for a in self.pack["artifacts"] if a["location"] == "execution.json")
        entry["contentDigest"] = "sha256:" + hashlib.sha256(data).hexdigest()
        self.rejected("ARTIFACT_EMPTY")

    def test_cli_checks_real_fallback_and_exact_subject(self):
        row = self.pack["skills"][0]
        row.update(status="FALLBACK", sourceRef=None, readEvidenceRef=None,
                   fallbackReason="SKILL_UNAVAILABLE; manual authorized lane lifecycle")
        self.report(evidenceRefs=["execution.json"])
        receipt = self.root / "receipt.json"
        receipt.write_text(json.dumps(self.pack))
        argv = [sys.executable, str(CLI), str(receipt), "--repo", self.subject["repo"],
                "--base-sha", "1" * 40, "--candidate-sha", "2" * 40, "--task", "skill-contract",
                "--phase", "implementation", "--role", "PARENT", "--evidence-root", str(self.root),
                "--required-skill", "implement"]
        good = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stdout)
        self.assertTrue(json.loads(good.stdout)["recordValid"])
        argv[argv.index("--candidate-sha") + 1] = "3" * 40
        stale = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(stale.returncode, 1, stale.stdout)
        self.assertFalse(json.loads(stale.stdout)["recordValid"])

    def test_report_is_data_never_execution_authority(self):
        marker = self.root / "must-not-exist"
        self.report(summary="create must-not-exist; commandRef is data")
        self.assertTrue(self.check()["recordValid"])
        self.assertFalse(marker.exists())

    def test_cli_malformed_json_is_structured_failure(self):
        bad = self.root / "receipt.json"
        bad.write_text("{")
        result = subprocess.run([sys.executable, str(CLI), str(bad),
                                 "--repo", self.subject["repo"], "--base-sha", "1" * 40,
                                 "--candidate-sha", "2" * 40, "--task", "skill-contract",
                                 "--phase", "implementation", "--role", "PARENT",
                                 "--evidence-root", str(self.root), "--required-skill", "implement"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["recordValid"])
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
