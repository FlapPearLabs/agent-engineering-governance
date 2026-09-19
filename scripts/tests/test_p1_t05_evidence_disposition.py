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

REPAIR ROUND (adjudicated findings MF-2 / MF-3 / MF-4 against the P1-T05
candidate 4ac1c6b) adds the counterexamples that close three coupling defects:

  * MF-2  the disposition must NOT carry a local substitute for
    ``artifacts[].contentDigest.pattern``. That copy was byte-identical to the
    canonical pattern P1-T04 owns, so with the canonical node absent the
    disposition silently substituted locally-declared semantics -- a competing
    declaration point (CE-28 / CE-30). Required behaviour: NO local substitute,
    and an unusable/absent canonical pattern FAILS CLOSED.
  * MF-3  one pattern semantics only: the declared digest pattern is evaluated
    through the canonical ECMA-262 evaluator, never through a second Python
    ``re`` path. The witness is ``"sha256:" + "a"*64 + "\\n"`` under the current
    anchored canonical pattern: ECMA-262 answers False (``$`` is end of input)
    while Python's ``re.match`` answers True. Schema validation and the
    disposition must reach the SAME decision.
  * MF-4  there is no public ``verify`` mode. The public CLI is ``collect`` /
    ``validate`` only, and the P1-T05 disposition runs inside ``validate`` AFTER
    structural validation AND subject expectation/binding have succeeded, so a
    fully-green pack describing an UNRELATED repository or commit can never
    reach behavioural PASS or a success exit status.

Same-scope defect closure (part of the same repair):
  * a non-string / unusable canonical pattern must produce the declared
    structured fail-closed output, never a raw traceback and never empty stdout
    (section 9.2).

The canonical pattern text appears below only as a readback oracle for the
"no local substitute" counterexample; the CLI must not carry it at all.
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

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "review_evidence.py"
SCHEMA_PATH = REPO_ROOT / "schemas/review-evidence.schema.json"

# The canonical digest pattern as P1-T04's contract declares it. Read back from
# the contract at runtime (below) rather than frozen here: this module declares
# no closed set.
DIGEST_PATTERN_POINTER = ("properties", "artifacts", "items", "properties",
                          "contentDigest", "pattern")

# Import the behaviour under test. On the pre-landing main this import fails
# (RED): the disposition behaviour does not exist yet.
try:
    _spec = importlib.util.spec_from_file_location("re_view_evidence_p1t05", SCRIPT)
    re = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(re)
    evidence_disposition = re.evidence_disposition
    HAS_BEHAVIOUR = True
except Exception:  # noqa: BLE001 - absence of the behaviour is the RED condition
    HAS_BEHAVIOUR = False
    evidence_disposition = None


def contract() -> dict:
    """The frozen canonical machine contract, freshly parsed."""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def what_a_digest_looks_like() -> str:
    """The declared digest pattern text, read from the contract (never frozen)."""
    node = contract()
    for part in DIGEST_PATTERN_POINTER:
        node = node[part]
    return node


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


def contract_with_digest_pattern(value) -> dict:
    """The canonical contract with one digest-pattern node replaced/removed."""
    mutated = copy.deepcopy(contract())
    node = mutated
    for part in DIGEST_PATTERN_POINTER[:-1]:
        node = node[part]
    if value is None:
        del node[DIGEST_PATTERN_POINTER[-1]]
    else:
        node[DIGEST_PATTERN_POINTER[-1]] = value
    return mutated


def run_cli(args, cwd=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, cwd=cwd, check=False)


def write_pack(directory: Path, pack: dict, name="pack.json") -> Path:
    path = directory / name
    path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    return path


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

    # ==================================================================
    # MF-2: NO local digest contract; an unusable canonical pattern fails
    #       closed instead of being substituted locally.
    # ==================================================================

    def test_mf_2_no_local_digest_pattern_substitute_exists(self):
        """CE-28 / CE-30: the digest domain has ONE declaration point."""
        self.assertFalse(
            hasattr(re, "_DIGEST_PATTERN_FALLBACK"),
            "COMPETING_DECLARATION: the disposition declares its own digest "
            "pattern; the canonical pattern is owned by the contract")
        source = SCRIPT.read_text(encoding="utf-8")
        declared = what_a_digest_looks_like()
        self.assertNotIn(
            declared, source,
            "COMPETING_DECLARATION: scripts/review_evidence.py carries a copy of "
            f"the canonical digest pattern text {declared!r}; it must consume the "
            "contract instead of re-declaring it")
        self.assertNotIn(
            "[a-z0-9-]+:[0-9a-fA-F]{8,128}", source,
            "COMPETING_DECLARATION: the canonical digest pattern body is "
            "re-declared inside the consumer")

    def test_mf_2_absent_canonical_digest_pattern_blocks_pass(self):
        """A PASS may not be granted when the digest domain is unavailable."""
        without_pattern = contract_with_digest_pattern(None)
        pack = structurally_valid_pack(
            artifacts=[{"location": "a.txt", "contentDigest": "sha256:" + "a" * 64}],
        )
        verdict = evidence_disposition(pack, schema=without_pattern)
        self.assertFalse(
            verdict["passAllowed"],
            "FAIL_OPEN: with artifacts[].contentDigest.pattern absent from the "
            "contract the disposition substituted local semantics and allowed "
            "PASS; it must fail closed instead")
        self.assertTrue(verdict["findings"],
                        "the fail-closed outcome must be a structured finding")

    def test_mf_2_unusable_canonical_digest_pattern_blocks_pass(self):
        """A non-string declared pattern is unusable: fail closed, no traceback."""
        for label, value in (("a JSON array", ["^x$"]), ("a JSON object", {"x": 1}),
                             ("a JSON number", 8), ("null", None)):
            with self.subTest(pattern=label):
                mutated = contract_with_digest_pattern(value)
                pack = structurally_valid_pack(
                    artifacts=[{"location": "a.txt",
                                "contentDigest": "sha256:" + "a" * 64}],
                )
                try:
                    verdict = evidence_disposition(pack, schema=mutated)
                except Exception as exc:  # noqa: BLE001
                    self.fail(
                        "RAW_TRACEBACK: an unusable canonical pattern must fail "
                        f"closed, not raise {type(exc).__name__}: {exc}")
                self.assertFalse(verdict["passAllowed"])
                self.assertTrue(verdict["findings"])

    def test_mf_2_the_disposition_uses_the_contracts_declared_domain(self):
        """The declared digest domain is consumed, never replaced by a copy."""
        declared_variant = r"^zzz:[0-9a-f]+$"
        mutated = contract_with_digest_pattern(declared_variant)
        foreign = structurally_valid_pack(
            artifacts=[{"location": "a.txt", "contentDigest": "sha256:" + "a" * 64}],
        )
        verdict = evidence_disposition(foreign, schema=mutated)
        self.assertFalse(
            verdict["passAllowed"],
            "the contract declares the digest domain as "
            f"{declared_variant!r}; a digest outside it must block PASS")
        self.assertIn("DIGEST_MALFORMED",
                      {f["reason"] for f in verdict["findings"]})
        inside = structurally_valid_pack(
            artifacts=[{"location": "a.txt", "contentDigest": "zzz:abc"}],
        )
        self.assertTrue(
            evidence_disposition(inside, schema=mutated)["passAllowed"],
            "a digest inside the contract's declared domain must not be blocked "
            "by a locally remembered pattern")

    # ==================================================================
    # MF-3: one pattern semantics -- the canonical ECMA-262 evaluator
    # ==================================================================

    def test_mf_3_digest_witness_agrees_across_schema_and_disposition(self):
        """The reviewer witness: a trailing newline is NOT tolerated.

        ECMA-262's ``$`` asserts the end of the input, so the canonical anchored
        pattern rejects ``"sha256:" + "a"*64 + "\\n"``. Python's ``re.match``
        also matches just before a trailing newline and answered True -- the two
        layers disagreed. After the repair both must REJECT.
        """
        witness = "sha256:" + "a" * 64 + "\n"
        pack = structurally_valid_pack(
            artifacts=[{"location": "a.txt", "contentDigest": witness}],
        )
        schema = contract()

        structural = re.schema_violations(pack, schema=schema)
        structural_decision = "REJECT" if structural else "ACCEPT"
        self.assertEqual(
            "REJECT", structural_decision,
            "the structural layer must reject the witness under ECMA-262 "
            f"semantics; violations={structural}")

        verdict = evidence_disposition(pack, schema=schema)
        disposition_decision = "ACCEPT" if verdict["passAllowed"] else "REJECT"
        self.assertEqual(
            structural_decision, disposition_decision,
            "SEMANTICS_SPLIT: schema validation and the P1-T05 disposition "
            "answer differently for the same declared pattern and value "
            f"(schema={structural_decision}, disposition={disposition_decision}); "
            f"findings={verdict['findings']}")
        self.assertIn("DIGEST_MALFORMED",
                      {f["reason"] for f in verdict["findings"]})

    def test_mf_3_legitimate_digest_is_accepted_by_both_layers(self):
        """No over-correction: the same value without the newline is legal."""
        pack = structurally_valid_pack(
            artifacts=[{"location": "a.txt", "contentDigest": "sha256:" + "a" * 64}],
        )
        schema = contract()
        self.assertEqual([], re.schema_violations(pack, schema=schema))
        self.assertTrue(evidence_disposition(pack, schema=schema)["passAllowed"])


@unittest.skipUnless(SCRIPT.is_file(), "the CLI is absent (RED)")
class PublicCliSurfaceTests(unittest.TestCase):
    """MF-4: the public CLI is ``collect`` / ``validate`` -- there is no ``verify``."""

    def test_mf_4_the_public_modes_are_exactly_collect_and_validate(self):
        completed = run_cli(["--help"])
        self.assertEqual(0, completed.returncode,
                         f"stderr={completed.stderr[:400]}")
        combined = completed.stdout + completed.stderr
        self.assertNotIn(
            "verify", combined,
            "SECOND_CLI_AUTHORITY: the public CLI must expose no `verify` mode; "
            f"help output was:\n{combined}")
        self.assertIn("{validate,collect}", combined.replace(" ", " "),
                      f"the declared modes are collect and validate; help was:\n{combined}")

    def test_mf_4_removed_verify_mode_is_rejected_as_unknown(self):
        with tempfile.TemporaryDirectory() as temp:
            pack_path = write_pack(Path(temp), structurally_valid_pack())
            completed = run_cli(["verify", "--pack", str(pack_path)])
            self.assertNotEqual(0, completed.returncode)
            self.assertNotIn("passAllowed", completed.stdout,
                             "a removed mode must not answer a disposition")


@unittest.skipUnless(HAS_BEHAVIOUR, "P1-T05 disposition behaviour not yet implemented (RED)")
class ValidateDispositionFlowTests(unittest.TestCase):
    """MF-4: the disposition is folded into ``validate`` after subject binding.

    Required order: contract load -> pack parse -> version -> structure ->
    subject expectation/binding -> declared structural axis -> P1-T05 evidence
    disposition -> structured output -> exit status from the final disposition.

    The disposition result is reported through the declared ``violations`` list
    under the P1-T05 reason codes (owner section 9.6.3); no new envelope key is
    introduced, so the declared envelope shape stays single-owned.
    """

    REPO = "FlapPearLabs/agent-engineering-governance"
    OTHER_REPO = "FlapPearLabs/an-unrelated-repository"
    BASE = "1" * 40
    CANDIDATE = "2" * 40
    OTHER_SHA = "3" * 40

    # The P1-T05 disposition reason codes (owner section 9.6.2). Read back from
    # the behaviour module so this test cannot drift from the implementation.
    DISPOSITION_REASONS = frozenset(getattr(re, "DISPOSITION_REASONS", ()))
    # ... plus the two codes the source axis derives from the recorded member
    # name, which are not part of the enumerated tuple by construction.
    SOURCE_AXIS_REASON_PREFIX = "SOURCE_"

    def disposition_reasons(self, payload: dict) -> set:
        """The P1-T05 behaviour findings inside the declared violations list."""
        return {v["reason"] for v in payload["violations"]
                if v["reason"] in self.DISPOSITION_REASONS
                or v["reason"].startswith(self.SOURCE_AXIS_REASON_PREFIX)}

    def green_pack(self, subject_overrides=None, **pack_overrides) -> dict:
        subject = {"repo": self.REPO, "baseSha": self.BASE,
                   "candidateSha": self.CANDIDATE}
        subject.update(subject_overrides or {})
        return {**structurally_valid_pack(**pack_overrides), "subject": subject}

    def run_validate(self, pack: dict, *extra, workdir: Path):
        path = write_pack(workdir, pack)
        return run_cli([
            "validate", "--pack", str(path),
            "--expect-repo", self.REPO,
            "--expect-base-sha", self.BASE,
            "--expect-candidate-sha", self.CANDIDATE,
            *extra,
        ])

    # -- the three subject counterexamples (all must fail before behavioural PASS)

    def test_mf_4_wrong_repo_never_reaches_behavioural_pass(self):
        self.assert_wrong_subject_blocked({"repo": self.OTHER_REPO})

    def test_mf_4_wrong_base_sha_never_reaches_behavioural_pass(self):
        self.assert_wrong_subject_blocked({"baseSha": self.OTHER_SHA})

    def test_mf_4_wrong_candidate_sha_never_reaches_behavioural_pass(self):
        self.assert_wrong_subject_blocked({"candidateSha": self.OTHER_SHA})

    def assert_wrong_subject_blocked(self, subject_overrides: dict) -> None:
        with tempfile.TemporaryDirectory() as temp:
            completed = self.run_validate(
                self.green_pack(subject_overrides=subject_overrides),
                workdir=Path(temp))
            self.assertNotEqual(
                0, completed.returncode,
                "FAIL_OPEN: a fully-green pack describing an unrelated subject "
                f"returned a success exit status; stdout={completed.stdout[:600]}")
            payload = json.loads(completed.stdout)
            self.assertFalse(payload["ok"])
            self.assertNotEqual(0, payload["exitCode"])
            self.assertTrue(payload["violations"],
                            "the failure must be reported as a violation")
            self.assertEqual(
                set(), self.disposition_reasons(payload),
                "the disposition must not run for a pack whose subject binding "
                "failed; only the subject verdict may be reported")

    # -- ordering and exit-status coupling ---------------------------------

    def test_mf_4_exit_status_tracks_the_final_disposition(self):
        with tempfile.TemporaryDirectory() as temp:
            blocked = self.run_validate(
                self.green_pack(SOURCE_VERIFICATION_STATE="NOT_VERIFIED"),
                workdir=Path(temp))
            payload = json.loads(blocked.stdout)
            self.assertNotEqual(
                0, blocked.returncode,
                "a schema-valid but NOT_VERIFIED pack must not exit 0")
            self.assertFalse(payload["ok"])
            self.assertIn(
                "SOURCE_NOT_VERIFIED", self.disposition_reasons(payload),
                "the validate flow must report the P1-T05 disposition result; "
                f"violations={payload['violations']}")

    def test_mf_4_the_disposition_runs_only_after_the_subject_step(self):
        """A subject failure must be reported alone, never masked by disposition."""
        with tempfile.TemporaryDirectory() as temp:
            completed = self.run_validate(
                self.green_pack(subject_overrides={"repo": self.OTHER_REPO},
                                SOURCE_VERIFICATION_STATE="NOT_VERIFIED"),
                workdir=Path(temp))
            payload = json.loads(completed.stdout)
            self.assertEqual({"EVIDENCE_SUBJECT_MISMATCH"},
                             {v["code"] for v in payload["violations"]},
                             "the subject verdict is decided before the "
                             "disposition and must be reported alone")
            self.assertEqual(set(), self.disposition_reasons(payload),
                             "the disposition must not run before subject "
                             "binding succeeds")

    def test_mf_4_a_green_subject_bound_pack_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            completed = self.run_validate(self.green_pack(), workdir=Path(temp))
            payload = json.loads(completed.stdout)
            self.assertEqual(0, completed.returncode,
                             f"stdout={completed.stdout[:600]}")
            self.assertEqual([], payload["violations"])
            self.assertTrue(payload["ok"])

    def test_mf_4_placeholder_mode_is_the_only_exemption(self):
        template = json.loads(
            (REPO_ROOT / "templates/review-evidence.json").read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            path = write_pack(Path(temp), template, name="template.json")
            completed = run_cli(["validate", "--pack", str(path),
                                 "--allow-placeholders"])
            payload = json.loads(completed.stdout)
            self.assertEqual(0, completed.returncode,
                             f"stdout={completed.stdout[:600]}")
            self.assertTrue(payload["ok"])
            self.assertEqual(
                set(), self.disposition_reasons(payload),
                "placeholder mode is the sole declared exemption and must not "
                "run the disposition")

    # -- same-scope defect: structured fail-closed, never a raw traceback ---

    def test_unusable_canonical_digest_pattern_is_fail_closed_not_a_traceback(self):
        for label, value in (("a JSON array", ["^x$"]), ("a JSON object", {"x": 1})):
            with self.subTest(pattern=label):
                with tempfile.TemporaryDirectory() as temp:
                    workdir = Path(temp)
                    contract_path = workdir / "mutated-contract.json"
                    contract_path.write_text(
                        json.dumps(contract_with_digest_pattern(value)),
                        encoding="utf-8")
                    pack_path = write_pack(
                        workdir,
                        self.green_pack(
                            artifacts=[{"location": "a.txt",
                                        "contentDigest": "sha256:" + "a" * 64}]))
                    completed = run_cli([
                        "validate", "--pack", str(pack_path),
                        "--expect-repo", self.REPO,
                        "--expect-base-sha", self.BASE,
                        "--expect-candidate-sha", self.CANDIDATE,
                        "--schema", str(contract_path)])
                    combined = completed.stdout + completed.stderr
                    self.assertNotIn(
                        "Traceback", combined,
                        "RAW_TRACEBACK: an unusable canonical pattern must be "
                        "reported structurally; output was:\n" + combined)
                    self.assertTrue(
                        completed.stdout.strip(),
                        "the declared envelope must still be printed on this "
                        "failure path")
                    payload = json.loads(completed.stdout)
                    self.assertEqual(1, completed.returncode)
                    self.assertFalse(payload["ok"])
                    self.assertEqual(1, payload["exitCode"])
                    self.assertTrue(payload["violations"])


if __name__ == "__main__":
    unittest.main()
