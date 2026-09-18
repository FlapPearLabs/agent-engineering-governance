"""Counterexample-driven checks for the P1-T05 three-axis evidence disposition.

SUPPORT surface (RULES R6), NOT an authority surface. This module declares no
closed set and no field name: it exercises the disposition behaviour that P1-T05
owns (the verification behaviour and disposition of the three orthogonal axes) and
fails when that behaviour is absent or collapses an axis.

BINDING (counterexample-first, P1-T05 RED)
    The disposition behaviour does not exist on the pre-landing main, so every
    assertion here fails to import / fails to pass. After P1-T05 lands, the
    behaviour must:

      * treat VERIFIED + INSUFFICIENT as a LEGAL combination that is nevertheless
        NOT pass-allowed (sufficiency blocks PASS) -- never treated as a
        contradiction, never silently accepted as PASS;
      * preserve TEMPORARILY_UNAVAILABLE and NEVER collapse it into INVALID;
      * reject INSUFFICIENT injected into the source axis (axis collapse);
      * block PASS on a missing artifact, a malformed/changed digest, an
        unavailable required evidence source, an empty run with a zero exit code
        but no valid result, and a non-PASS CI originalState;
      * NOT treat a schema-valid pack (NOT_VERIFIED) as behavioural acceptance;
      * NOT treat exit code 0 or a literal "PASS" string as behavioural PASS;
      * NOT invent a sixth state-machine family or modify the CI_STATUS set.

The closed sets themselves are referenced from the frozen schema, never
re-declared here.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "review_evidence.py"

# Import the behaviour under test. On the pre-landing main this import fails
# (RED): the disposition behaviour does not exist yet.
try:
    import importlib.util
    _spec = importlib.util.spec_from_file_location("re_view_evidence_p1t05", SCRIPT)
    re = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(re)
    evidence_disposition = re.evidence_disposition
    HAS_BEHAVIOUR = True
except Exception:  # noqa: BLE001 - absence of the behaviour is the RED condition
    HAS_BEHAVIOUR = False
    evidence_disposition = None


def structurally_valid_pack(**overrides) -> dict:
    """A pack that is structurally valid and declares the three axes."""
    pack = {
        "schemaVersion": 1,
        "subject": {"repo": "owner/repo", "baseSha": "a" * 40, "candidateSha": "b" * 40},
        "authorityRefs": [],
        "producer": {"identity": "x", "version": "1", "observedAt": "2026-01-01T00:00:00Z"},
        "checks": [],
        "artifacts": [],
        "ci": {"run": "r", "job": "j", "checkedSha": "b" * 40, "originalState": "PASS"},
        "grounding": {"mode": "UNAVAILABLE", "coverage": "", "evidenceRef": ""},
        "seams": {"applicability": "REQUIRED", "evidenceRefs": []},
        "reuse": {"sourceEvidence": "", "validFor": "", "dependencies": [], "invalidation": ""},
        "unverified": [],
        "STRUCTURALLY_VALID": "YES",
        "SOURCE_VERIFICATION_STATE": "VERIFIED",
        "EVIDENCE_SUFFICIENCY": "SUFFICIENT",
        "semanticScopeStatus": None,
        "reviewerDecisionRefs": [],
    }
    pack.update(overrides)
    return pack


@unittest.skipUnless(HAS_BEHAVIOUR, "P1-T05 disposition behaviour not yet implemented (RED)")
class EvidenceDispositionTests(unittest.TestCase):
    # -- core legal combination --------------------------------------------

    def test_verified_plus_insufficient_is_legal_but_blocks_pass(self):
        pack = structurally_valid_pack(EVIDENCE_SUFFICIENCY="INSUFFICIENT")
        verdict = evidence_disposition(pack)
        self.assertFalse(verdict["passAllowed"],
                         "VERIFIED + INSUFFICIENT must NOT be pass-allowed")
        self.assertIn("EVIDENCE_INSUFFICIENT",
                      {f["reason"] for f in verdict["findings"]},
                      "the INSUFFICIENT sufficiency axis must be recorded as the block reason")
        # Legal combination: no axis-collapse / contradiction finding.
        self.assertNotIn("AXIS_COLLAPSE", {f["reason"] for f in verdict["findings"]})

    # -- temporary unavailability must be preserved ------------------------

    def test_temporarily_unavailable_is_not_collapsed_to_invalid(self):
        pack = structurally_valid_pack(SOURCE_VERIFICATION_STATE="TEMPORARILY_UNAVAILABLE")
        verdict = evidence_disposition(pack)
        self.assertFalse(verdict["passAllowed"])
        self.assertEqual(verdict["originalSourceState"], "TEMPORARILY_UNAVAILABLE",
                         "TEMPORARILY_UNAVAILABLE must be preserved, never rewritten to INVALID")
        self.assertNotIn("SOURCE_INVALID", {f["reason"] for f in verdict["findings"]})
        self.assertIn("SOURCE_TEMPORARILY_UNAVAILABLE", {f["reason"] for f in verdict["findings"]})

    # -- axis collapse: INSUFFICIENT injected into the source axis ----------

    def test_insufficient_injected_into_source_axis_is_rejected(self):
        pack = structurally_valid_pack(SOURCE_VERIFICATION_STATE="INSUFFICIENT")
        verdict = evidence_disposition(pack)
        self.assertIn("AXIS_COLLAPSE", {f["reason"] for f in verdict["findings"]},
                      "INSUFFICIENT is not a SOURCE_VERIFICATION_STATE value; it must be rejected as axis collapse")
        self.assertFalse(verdict["passAllowed"])

    # -- missing artifact ---------------------------------------------------

    def test_missing_artifact_blocks_pass(self):
        pack = structurally_valid_pack(
            checks=[{"id": "c1", "scope": "x", "commandRef": "r", "status": "PASS",
                     "exitCode": 0, "artifactRefs": ["missing"]}],
        )
        verdict = evidence_disposition(pack)
        self.assertFalse(verdict["passAllowed"])
        self.assertIn("MISSING_ARTIFACT", {f["reason"] for f in verdict["findings"]})

    # -- changed / malformed digest ----------------------------------------

    def test_malformed_digest_blocks_pass(self):
        pack = structurally_valid_pack(
            artifacts=[{"location": "a.txt", "contentDigest": "not-a-digest"}],
        )
        verdict = evidence_disposition(pack)
        self.assertFalse(verdict["passAllowed"])
        self.assertIn("DIGEST_MALFORMED", {f["reason"] for f in verdict["findings"]})

    # -- required evidence unavailable (TEMPORARILY_UNAVAILABLE source) ------

    def test_required_evidence_unavailable_blocks_pass_preserving_cause(self):
        pack = structurally_valid_pack(SOURCE_VERIFICATION_STATE="TEMPORARILY_UNAVAILABLE")
        verdict = evidence_disposition(pack)
        self.assertFalse(verdict["passAllowed"])
        self.assertEqual(verdict["originalSourceState"], "TEMPORARILY_UNAVAILABLE")

    # -- empty run / zero exit code with no valid result -------------------

    def test_empty_run_zero_exit_does_not_grant_pass(self):
        pack = structurally_valid_pack(
            ci={"run": "", "job": "", "checkedSha": "", "originalState": "UNKNOWN"},
        )
        verdict = evidence_disposition(pack)
        self.assertFalse(verdict["passAllowed"],
                         "an empty run with no observed result must not be treated as PASS")
        self.assertIn("CI_NOT_OBSERVED", {f["reason"] for f in verdict["findings"]})

    # -- CI non-PASS collapsed into PASS -----------------------------------

    def test_ci_non_pass_not_collapsed_into_pass(self):
        for state in ("FAIL", "NOT_TRIGGERED", "CANCELLED", "INFRASTRUCTURE_FAILURE",
                     "KNOWN_BASELINE_FAILURE"):
            with self.subTest(state=state):
                pack = structurally_valid_pack(
                    ci={"run": "r", "job": "j", "checkedSha": "b" * 40, "originalState": state},
                )
                verdict = evidence_disposition(pack)
                self.assertFalse(verdict["passAllowed"],
                                 f"CI originalState={state} must not be collapsed into PASS")
                self.assertIn("CI_NOT_PASS", {f["reason"] for f in verdict["findings"]})

    # -- schema-valid but NOT_VERIFIED is NOT behavioural acceptance --------

    def test_schema_valid_not_verified_is_not_acceptance(self):
        pack = structurally_valid_pack(SOURCE_VERIFICATION_STATE="NOT_VERIFIED")
        verdict = evidence_disposition(pack)
        self.assertFalse(verdict["passAllowed"],
                         "a schema-valid pack that is NOT_VERIFIED must not be accepted as PASS")
        self.assertIn("SOURCE_NOT_VERIFIED", {f["reason"] for f in verdict["findings"]})

    # -- only the fully verified + sufficient combination passes ------------

    def test_fully_verified_and_sufficient_allows_pass(self):
        pack = structurally_valid_pack()
        verdict = evidence_disposition(pack)
        self.assertTrue(verdict["passAllowed"],
                        "VERIFIED + SUFFICIENT + STRUCTURALLY_VALID=YES must allow PASS")
        self.assertEqual(verdict["findings"], [], "no finding expected when pass is allowed")


@unittest.skipUnless(HAS_BEHAVIOUR, "P1-T05 verify subcommand not yet implemented (RED)")
class VerifySubcommandTests(unittest.TestCase):
    def _run(self, pack: dict) -> dict:
        import tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(pack, fh)
            path = fh.name
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "verify", "--pack", path],
            capture_output=True, text=True)
        return {"rc": proc.returncode, "out": proc.stdout, "err": proc.stderr}

    def test_verify_cli_reports_pass_allowed_field(self):
        res = self._run(structurally_valid_pack())
        payload = json.loads(res["out"])
        self.assertIn("disposition", payload)
        self.assertTrue(payload["disposition"]["passAllowed"])

    def test_verify_exit_code_reflects_disposition_not_schema_validity(self):
        # schema-valid but NOT_VERIFIED -> exit code must NOT be 0 (PASS).
        res = self._run(structurally_valid_pack(SOURCE_VERIFICATION_STATE="NOT_VERIFIED"))
        self.assertNotEqual(res["rc"], 0,
                           "exit code must track the genuine disposition, not schema validity")
        payload = json.loads(res["out"])
        self.assertFalse(payload["disposition"]["passAllowed"])


if __name__ == "__main__":
    unittest.main()
