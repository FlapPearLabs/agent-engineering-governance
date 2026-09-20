"""Counterexample-first lifecycle tests for the P1-T08 evidence reuse /
invalidation consumption behaviour (Issue #24, REQ-W3-01/02/03 + REQ-W2-07).

SUPPORT SURFACE (RULES.md R6, declared): the reuse dependency descriptor SHAPE
is declared exactly once by P1-T04 (schemas/review-evidence.schema.json
`reuse_dependency_descriptor` + references/review-evidence.md section 5). This
module is the test surface of the BEHAVIOUR that consumes that shape:

    scripts/review_evidence.py  evidence_lifecycle_findings(...)  and its
    folding into the existing `validate` flow (no new CLI mode, no new
    envelope key); references/git-ci-integration.md section 5.3 is the
    normative rule-text owner.

RED DISCIPLINE (references/ticket-lane.md section 4): while the behaviour is
absent, every behavioural test fails with an explicit ``LIFECYCLE_ABSENT``
message or with a concrete observed/expected mismatch on the real CLI output.
RED is never allowed to surface as ImportError / ModuleNotFoundError / a
broken harness: the CLI module is acquired through ``require_cli`` and the
lifecycle entry point through ``require_lifecycle``, each failing the test
with that message instead of raising.

Counterexamples covered (parent spec section 9):
  CE-26  VERIFICATION_STATE = UNKNOWN (or a malformed / free-text descriptor)
         while reuse is declared -> the pack is REJECTED
  CE-11  a relevant dependency change (invalidation trigger hit) invalidates
         EXACTLY the affected dependency scope, not everything
  CE-12  an unrelated change triggers NO invalidation at all
         (over-invalidation is itself a defect, AC-34)
  CE-07  a reuse declaration that identifies no source evidence (missing
         required evidence) is not accepted as PASS

Positive controls (parent spec section 10.2):
  AC-31  a time-valid descriptor with VERIFICATION_STATE = VERIFIED inside a
         bounded VALID_FOR scope is permitted (legal reuse still succeeds)
  AC-37  the subject candidate SHA stays explicit: a pack bound to a
         different (e.g. report-commit-moved) candidate is rejected and can
         never inherit the old PASS through the lifecycle stage

Stdlib only. Run with:
    python3 -m unittest scripts.tests.test_p1_t08_evidence_lifecycle -v
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CLI_PATH = ROOT / "scripts" / "review_evidence.py"
SCHEMA_PATH = ROOT / "schemas" / "review-evidence.schema.json"
GIT_CI_PATH = ROOT / "references" / "git-ci-integration.md"
REVIEW_EVIDENCE_PATH = ROOT / "references" / "review-evidence.md"

REPO_OK = "FlapPearLabs/agent-engineering-governance"
BASE_SHA = "1" * 40
CANDIDATE_SHA = "2" * 40
OTHER_CANDIDATE_SHA = "3" * 40

# The four invalidation triggers, exactly as the normative rule text
# (references/git-ci-integration.md section 5.3) declares them. These are
# assertion INPUTS read back from the canonical text, never a second
# declaration of the trigger list.
TRIGGER_MASTER_DRIFT = "master drift"
TRIGGER_SHARED_SCHEMA = "shared schema or shared dependency change"
TRIGGER_ENTRY_TOPOLOGY = "entry topology change"
TRIGGER_AUTHORITY_TOOLCHAIN = "authority profile toolchain change"

LIFECYCLE_REASONS = (
    "REUSE_DESCRIPTOR_MALFORMED",
    "REUSE_SCOPE_UNBOUNDED",
    "REUSE_SOURCE_MISSING",
    "REUSE_DEPENDENCY_UNKNOWN",
    "REUSE_CLAIM_INVALIDATED",
    "REUSE_SCOPE_INVALIDATED",
)


def verified_descriptor(**overrides) -> dict:
    """A shape-legal descriptor the P1-T04 schema accepts, VERIFIED."""
    descriptor = {
        "WHAT": "shared schema:schemas/project-state.schema.json",
        "IDENTITY_VERSION_OR_DIGEST": "sha256:" + "1" * 64,
        "VALID_FOR": "this lane candidate range only",
        "INVALIDATED_BY": TRIGGER_MASTER_DRIFT,
        "VERIFICATION_STATE": "VERIFIED",
    }
    descriptor.update(overrides)
    return descriptor


def good_pack() -> dict:
    """A pack the whole landed contract accepts AND that declares reuse."""
    return {
        "schemaVersion": 1,
        "subject": {"repo": REPO_OK, "baseSha": BASE_SHA,
                    "candidateSha": CANDIDATE_SHA},
        "authorityRefs":
            ["P1_AGENT_ENGINEERING_GOVERNANCE_DELTA_SPEC#REQ-W3-02"],
        "producer": {"identity": "laneA-worker", "version": "1",
                     "observedAt": "2026-09-20T00:00:00Z"},
        "checks": [{"id": "c1", "scope": "scripts/validate_governance.py",
                    "commandRef": "references/review-evidence.md#9",
                    "status": "PASS", "exitCode": 0,
                    "artifactRefs": ["evidence/laneA/governance.txt"]}],
        "artifacts": [{"location": "evidence/laneA/governance.txt",
                       "contentDigest": "sha256:" + "0" * 64}],
        "ci": {"run": "1234567890", "job": "validate-governance",
               "checkedSha": CANDIDATE_SHA, "originalState": "PASS"},
        "grounding": {"mode": "UNAVAILABLE",
                      "coverage": "CODEGRAPH_UNAVAILABLE",
                      "evidenceRef": "references/codegraph-grounding.md#2.1"},
        "seams": {"applicability": "REQUIRED", "evidenceRefs": []},
        "reuse": {
            "sourceEvidence":
                "the reviewed evidence pack of the previous reviewed SHA",
            "validFor": "this lane candidate range only",
            "dependencies": [verified_descriptor()],
            "invalidation": "a hit on the declared invalidation trigger",
        },
        "unverified": [],
        "STRUCTURALLY_VALID": "YES",
        "SOURCE_VERIFICATION_STATE": "VERIFIED",
        "EVIDENCE_SUFFICIENCY": "SUFFICIENT",
        "semanticScopeStatus": None,
        "reviewerDecisionRefs": [],
    }


def write_pack(directory: Path, pack: dict, name="pack.json") -> Path:
    path = directory / name
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path


_MODULE_CACHE: dict = {}


def require_cli(testcase: unittest.TestCase):
    """Load scripts/review_evidence.py, or fail with LIFECYCLE_ABSENT."""
    if "cli" in _MODULE_CACHE:
        return _MODULE_CACHE["cli"]
    if not CLI_PATH.is_file():
        testcase.fail(
            "LIFECYCLE_ABSENT: scripts/review_evidence.py does not exist, so "
            "the P1-T08 lifecycle behaviour cannot be exercised")
    spec = importlib.util.spec_from_file_location(
        "review_evidence_p1_t08", CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 - a broken harness is not RED
        testcase.fail(
            f"LIFECYCLE_ABSENT: scripts/review_evidence.py cannot be imported "
            f"({type(exc).__name__}: {exc}); that is a broken harness, not a "
            "counterexample RED")
    _MODULE_CACHE["cli"] = module
    return module


def require_lifecycle(testcase: unittest.TestCase):
    """The P1-T08 lifecycle entry point, or fail with LIFECYCLE_ABSENT."""
    cli = require_cli(testcase)
    lifecycle = getattr(cli, "evidence_lifecycle_findings", None)
    if lifecycle is None or not callable(lifecycle):
        testcase.fail(
            "LIFECYCLE_ABSENT: scripts/review_evidence.py exposes no "
            "evidence_lifecycle_findings behaviour, so the P1-T08 reuse "
            "legality / targeted invalidation rules are not implemented yet "
            "(expected RED condition of P1-T08 before implementation)")
    return lifecycle


class LifecycleCLITests(unittest.TestCase):
    """The lifecycle stage folded into the existing `validate` flow."""

    def run_validate(self, pack: dict):
        with tempfile.TemporaryDirectory() as temp:
            path = write_pack(Path(temp), pack)
            completed = subprocess.run(
                [sys.executable, str(CLI_PATH), "validate",
                 "--pack", str(path),
                 "--expect-repo", pack["subject"]["repo"],
                 "--expect-base-sha", pack["subject"]["baseSha"],
                 "--expect-candidate-sha", pack["subject"]["candidateSha"]],
                capture_output=True, text=True)
        return completed, json.loads(completed.stdout)

    def reasons(self, payload) -> set:
        return {v.get("reason") for v in payload["violations"]}

    # -- CE-26 / AC-32: UNKNOWN dependency + reuse declared -> reject -------

    def test_ce26_unknown_dependency_with_reuse_declared_is_rejected(self):
        """CE-26: UNKNOWN is never a reusable dependency state."""
        pack = good_pack()
        pack["reuse"]["dependencies"][0]["VERIFICATION_STATE"] = "UNKNOWN"
        completed, payload = self.run_validate(pack)
        self.assertEqual(
            1, completed.returncode,
            f"CE-26 RED (pre-implementation) or failure: a pack that declares "
            f"reuse while its dependency analysis is UNKNOWN must be "
            f"rejected; stdout={completed.stdout[:600]}")
        self.assertFalse(payload["ok"])
        self.assertIn("REUSE_DEPENDENCY_UNKNOWN", self.reasons(payload),
                      f"violations={payload['violations']}")

    def test_ce26_free_text_dependencies_are_rejected(self):
        """CE-26: free-text dependencies are not a legal reuse declaration."""
        pack = good_pack()
        pack["reuse"]["dependencies"] = "the project-state schema contract"
        completed, payload = self.run_validate(pack)
        self.assertEqual(1, completed.returncode,
                         f"stdout={completed.stdout[:600]}")
        self.assertFalse(payload["ok"])

    def test_ce26_malformed_descriptor_with_reuse_is_rejected(self):
        """CE-26: a descriptor missing a required key is not reusable."""
        pack = good_pack()
        del pack["reuse"]["dependencies"][0]["INVALIDATED_BY"]
        completed, payload = self.run_validate(pack)
        self.assertEqual(1, completed.returncode,
                         f"stdout={completed.stdout[:600]}")
        self.assertFalse(payload["ok"])

    # -- AC-31: the legal reuse case still succeeds (positive control) ------

    def test_ac31_legal_verified_bounded_reuse_succeeds(self):
        """AC-31: VERIFIED + bounded VALID_FOR is permitted, no findings."""
        completed, payload = self.run_validate(good_pack())
        self.assertEqual(
            0, completed.returncode,
            f"AC-31 positive control failed: stdout={completed.stdout[:600]}")
        self.assertTrue(payload["ok"])
        self.assertEqual([], payload["violations"])
        self.assertEqual(set(), self.reasons(payload) & set(LIFECYCLE_REASONS),
                         "a legal reuse pack must carry no lifecycle finding")

    # -- reuse legality details ---------------------------------------------

    def test_reuse_with_unbounded_scope_is_rejected(self):
        """Legal reuse needs a bounded VALID_FOR scope; empty is unbounded."""
        pack = good_pack()
        pack["reuse"]["validFor"] = ""
        completed, payload = self.run_validate(pack)
        self.assertEqual(
            1, completed.returncode,
            f"a reuse declaration without a bounded scope must be rejected; "
            f"stdout={completed.stdout[:600]}")
        self.assertIn("REUSE_SCOPE_UNBOUNDED", self.reasons(payload),
                      f"violations={payload['violations']}")

    def test_reuse_without_source_evidence_is_rejected(self):
        """CE-07 remainder: reuse declared but no source evidence identified.

        A reuse declaration that names no retrievable/identified source is a
        missing required evidence declaration; it must not be accepted as
        PASS (never defaults to silent reuse).
        """
        pack = good_pack()
        pack["reuse"]["sourceEvidence"] = ""
        completed, payload = self.run_validate(pack)
        self.assertEqual(
            1, completed.returncode,
            f"a reuse declaration without source evidence must be rejected; "
            f"stdout={completed.stdout[:600]}")
        self.assertIn("REUSE_SOURCE_MISSING", self.reasons(payload),
                      f"violations={payload['violations']}")

    # -- F1 regression: a partially-populated reuse object IS a claim -------

    def f1_reuse(self, **overrides) -> dict:
        """A pack whose reuse object starts fully empty, then is populated."""
        pack = good_pack()
        pack["reuse"] = {"sourceEvidence": "", "validFor": "",
                         "dependencies": [], "invalidation": ""}
        pack["reuse"].update(overrides)
        return pack

    def test_f1_whitespace_source_empty_deps_with_claim_is_rejected(self):
        """F1 fail-open repair: whitespace source + empty dependencies still
        asserts a claim when validFor / invalidation are non-blank, so the
        pack must be REJECTED (REUSE_SOURCE_MISSING, CE-07), never exit 0
        with zero findings."""
        pack = self.f1_reuse(sourceEvidence="   ", validFor="range",
                             invalidation="trigger hit")
        completed, payload = self.run_validate(pack)
        self.assertEqual(
            1, completed.returncode,
            f"F1 fail-open: a partially-populated reuse object asserts a "
            f"reuse claim and must be rejected; stdout={completed.stdout[:600]}")
        self.assertIn("REUSE_SOURCE_MISSING", self.reasons(payload),
                      f"violations={payload['violations']}")

    def test_f1_empty_source_empty_deps_with_claim_is_rejected(self):
        """F1: an empty source with empty dependencies but an asserted claim
        scope is a declared reuse -> REUSE_SOURCE_MISSING."""
        pack = self.f1_reuse(validFor="range", invalidation="trigger hit")
        completed, payload = self.run_validate(pack)
        self.assertEqual(
            1, completed.returncode,
            f"F1 fail-open: empty source + empty deps + a claimed scope is "
            f"still a reuse declaration; stdout={completed.stdout[:600]}")
        self.assertIn("REUSE_SOURCE_MISSING", self.reasons(payload),
                      f"violations={payload['violations']}")

    def test_f1_claim_via_dependencies_only_is_rejected(self):
        """F1: a populated dependency list alone is a declaration; without a
        bounded scope or identified source the existing rejections apply."""
        pack = self.f1_reuse(dependencies=[verified_descriptor()])
        completed, payload = self.run_validate(pack)
        self.assertEqual(
            1, completed.returncode,
            f"F1 fail-open: a populated dependency list alone declares "
            f"reuse; stdout={completed.stdout[:600]}")
        reasons = self.reasons(payload)
        self.assertIn("REUSE_SCOPE_UNBOUNDED", reasons,
                      f"violations={payload['violations']}")
        self.assertIn("REUSE_SOURCE_MISSING", reasons,
                      f"violations={payload['violations']}")

    # -- AC-37: the subject candidate SHA stays explicit --------------------

    def test_ac37_moved_candidate_sha_never_inherits_the_old_pass(self):
        """AC-37: a report commit that moved the candidate cannot carry the
        old PASS forward -- the pack bound to the old candidate is rejected
        against the new HEAD, and no lifecycle rule rescues it."""
        pack = good_pack()
        with tempfile.TemporaryDirectory() as temp:
            path = write_pack(Path(temp), pack)
            completed = subprocess.run(
                [sys.executable, str(CLI_PATH), "validate",
                 "--pack", str(path),
                 "--expect-repo", REPO_OK,
                 "--expect-base-sha", BASE_SHA,
                 "--expect-candidate-sha", OTHER_CANDIDATE_SHA],
                capture_output=True, text=True)
        payload = json.loads(completed.stdout)
        self.assertEqual(1, completed.returncode,
                         f"stdout={completed.stdout[:600]}")
        self.assertIn("SUBJECT_CANDIDATE_SHA_STALE", self.reasons(payload),
                      f"violations={payload['violations']}")


class LifecycleFunctionTests(unittest.TestCase):
    """Targeted invalidation decisions of the lifecycle entry point."""

    def findings(self, pack, hit_triggers):
        lifecycle = require_lifecycle(self)
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        return lifecycle(pack, schema=schema, hit_triggers=hit_triggers)

    def two_dependency_pack(self) -> dict:
        """Reuse pack with two dependencies of DIFFERENT trigger scopes."""
        pack = good_pack()
        pack["reuse"]["invalidation"] = \
            "a hit on the declared invalidation trigger"
        pack["reuse"]["dependencies"] = [
            verified_descriptor(WHAT="entry topology:server bootstrap",
                                INVALIDATED_BY=TRIGGER_ENTRY_TOPOLOGY),
            verified_descriptor(WHAT="shared schema:schemas/project-state.",
                                INVALIDATED_BY=TRIGGER_MASTER_DRIFT),
        ]
        return pack

    def test_ce11_hit_invalidates_exactly_the_affected_scope(self):
        """CE-11: a master-drift hit invalidates the master-drift-bound
        dependency ONLY; the entry-topology-bound dependency is untouched."""
        findings = self.findings(self.two_dependency_pack(),
                                 (TRIGGER_MASTER_DRIFT,))
        scope_hits = [f for f in findings
                      if f.get("reason") == "REUSE_SCOPE_INVALIDATED"]
        self.assertEqual(
            1, len(scope_hits),
            f"CE-11: exactly the affected dependency scope must be "
            f"invalidated; findings={findings}")
        self.assertIn("[1]", scope_hits[0]["path"],
                      f"the hit must target the master-drift dependency "
                      f"(index 1), got {scope_hits[0]['path']}")
        self.assertNotIn(
            "[0]", " ".join(f["path"] for f in findings),
            f"CE-11: the unrelated dependency must NOT be invalidated by a "
            f"hit outside its scope; findings={findings}")

    def test_ac34_unrelated_change_triggers_no_invalidation(self):
        """CE-12 / AC-34: an unrelated trigger hit must not invalidate
        anything -- over-invalidation is itself a defect."""
        for hit_triggers in ((TRIGGER_AUTHORITY_TOOLCHAIN,), ()):
            with self.subTest(hit_triggers=hit_triggers):
                findings = self.findings(self.two_dependency_pack(),
                                         hit_triggers)
                self.assertEqual(
                    [], findings,
                    f"CE-12: an unrelated change must trigger no "
                    f"invalidation finding; findings={findings}")

    def test_claim_level_hit_invalidates_the_reuse_claim(self):
        """A hit matching the claim-level invalidation record kills the
        whole reuse claim (still not a global wipe of other evidence)."""
        pack = good_pack()
        pack["reuse"]["invalidation"] = \
            f"{TRIGGER_SHARED_SCHEMA} invalidates this reuse claim"
        findings = self.findings(pack, (TRIGGER_SHARED_SCHEMA,))
        reasons = {f.get("reason") for f in findings}
        self.assertIn("REUSE_CLAIM_INVALIDATED", reasons,
                      f"findings={findings}")

    def test_no_reuse_declaration_yields_no_lifecycle_findings(self):
        """An empty reuse block declares no reuse; the lifecycle stage must
        stay silent (the collect skeleton and most packs keep flowing).

        F1 documented semantics: a FULLY-empty reuse object (all four fields
        blank/empty, including whitespace-only strings -- the collect-skeleton
        form) asserts no claim; a PARTIALLY populated object is a claim.
        """
        pack = good_pack()
        pack["reuse"] = {"sourceEvidence": "", "validFor": "",
                         "dependencies": [], "invalidation": ""}
        self.assertEqual([], self.findings(pack, (TRIGGER_MASTER_DRIFT,)))
        pack["reuse"] = {"sourceEvidence": "   ", "validFor": "  ",
                         "dependencies": [], "invalidation": ""}
        self.assertEqual([], self.findings(pack, (TRIGGER_MASTER_DRIFT,)),
                         "whitespace-only fields still assert no claim")

    def test_f1_partially_populated_reuse_is_a_declared_claim(self):
        """F1: ANY of non-blank sourceEvidence / validFor / invalidation, or
        a non-empty dependencies list, makes the reuse object a DECLARED
        claim; the legality rejections then apply instead of a silent pass."""
        cases = (
            ({"sourceEvidence": "   ", "validFor": "range",
              "invalidation": "trigger hit"},
             {"REUSE_SOURCE_MISSING"}),
            ({"validFor": "range", "invalidation": "trigger hit"},
             {"REUSE_SOURCE_MISSING"}),
            ({"invalidation": "trigger hit"},
             {"REUSE_SCOPE_UNBOUNDED", "REUSE_SOURCE_MISSING"}),
            ({"dependencies": [verified_descriptor()]},
             {"REUSE_SCOPE_UNBOUNDED", "REUSE_SOURCE_MISSING"}),
        )
        for overrides, expected in cases:
            with self.subTest(overrides=overrides):
                pack = good_pack()
                pack["reuse"] = {"sourceEvidence": "", "validFor": "",
                                 "dependencies": [], "invalidation": ""}
                pack["reuse"].update(overrides)
                findings = self.findings(pack, ())
                reasons = {f.get("reason") for f in findings}
                self.assertTrue(
                    expected <= reasons,
                    f"expected reasons {expected} inside {reasons}; "
                    f"findings={findings}")

    def test_lifecycle_reasons_are_disjoint_from_landed_vocabularies(self):
        """No layer may alias another: the P1-T08 reason vocabulary stays
        disjoint from the structural / declared / disposition / boundary
        vocabularies landed by P1-T04/05/06."""
        cli = require_cli(self)
        landed = (set(cli.STRUCTURAL_REASONS)
                  | set(cli.NON_STRUCTURAL_REASONS)
                  | set(cli.DISPOSITION_REASONS)
                  | set(cli.RETRIEVAL_BOUNDARY_REASONS))
        self.assertEqual(set(), set(LIFECYCLE_REASONS) & landed,
                         "the lifecycle reason vocabulary must never alias a "
                         "landed failure vocabulary")


class NormativeRuleTextTests(unittest.TestCase):
    """Readback of the normative rule text owner (git-ci-integration.md 5.3).

    The lifecycle BEHAVIOUR tests above drive the real implementation
    surface; this class only locks the canonical clause to the behaviour
    (a mutated or removed 5.3 turns this module RED).
    """

    def setUp(self):
        if not GIT_CI_PATH.is_file():
            self.fail("LIFECYCLE_ABSENT: references/git-ci-integration.md "
                      "does not exist")
        self.text = GIT_CI_PATH.read_text(encoding="utf-8")

    def section_5_3_body(self) -> str:
        marker = "### 5.3"
        index = self.text.find(marker)
        if index < 0:
            self.fail("LIFECYCLE_ABSENT: references/git-ci-integration.md "
                      "carries no section 5.3 lifecycle clause")
        rest = self.text[index:]
        nxt = rest.find("\n## ", 1)
        return rest if nxt < 0 else rest[:nxt]

    def test_5_3_declares_the_four_invalidation_triggers(self):
        body = self.section_5_3_body()
        for phrase in ("master drift", "shared schema", "entry topology",
                       "toolchain"):
            self.assertIn(phrase, body,
                          f"the 5.3 trigger table lost {phrase!r}")

    def test_5_3_declares_the_subject_report_commit_distinction(self):
        body = self.section_5_3_body()
        self.assertIn("report commit", body,
                      "the 5.3 clause must declare the subject commit versus "
                      "report commit distinction")
        self.assertIn("UNKNOWN", body,
                      "the 5.3 clause must declare that an UNKNOWN dependency "
                      "analysis never permits reuse")

    def test_5_3_cites_the_descriptor_shape_by_pointer_only(self):
        body = self.section_5_3_body()
        self.assertIn("reuse_dependency_descriptor", body,
                      "5.3 must cite the descriptor shape by pointer to the "
                      "schema $def")
        self.assertIn("review-evidence.md", body,
                      "5.3 must point at the semantic owner")
        # CE-28 guards: the protected identity token never appears here, and
        # the five-key descriptor family is never enumerated as a whole.
        self.assertNotIn("IDENTITY_VERSION_OR_DIGEST", self.text,
                         "the protected identity token must stay declared "
                         "only by the Review Evidence interface")
        keys = ("WHAT", "IDENTITY_VERSION_OR_DIGEST", "VALID_FOR",
                "INVALIDATED_BY", "VERIFICATION_STATE")
        if all(key in body for key in keys):
            self.fail("DUAL_DECLARATION (CE-28): section 5.3 names the whole "
                      "reuse dependency descriptor family; cite the schema "
                      "instead")

    def test_5_3_does_not_redeclare_the_ci_status_machine(self):
        """CHECK_STATUS / CI_STATUS stay owned by review-evidence.md §4 and
        git-ci-integration.md §3; 5.3 adopts them by reference only."""
        body = self.section_5_3_body()
        self.assertNotIn("NOT_TRIGGERED", body,
                         "5.3 must not re-enumerate the CI status values")
        self.assertNotIn("不可坍缩", body,
                         "the canonical non-collapsing CI status line stays "
                         "unique in section 3")


class PlaceholderExemptionScopeTests(unittest.TestCase):
    """F2 coherence readback: `references/review-evidence.md` is the SINGLE
    declaration point of `--allow-placeholders` and of the validate judgment
    order. The code exempts the P1-T08 lifecycle stage in placeholder mode
    and `git-ci-integration.md` 5.3 declares that exemption, so every
    flag-scope sentence here must name the same scope (pointer-style; no
    re-declaration of the lifecycle rules)."""

    def setUp(self):
        if not REVIEW_EVIDENCE_PATH.is_file():
            self.fail("LIFECYCLE_ABSENT: references/review-evidence.md "
                      "does not exist")
        self.text = REVIEW_EVIDENCE_PATH.read_text(encoding="utf-8")

    def section(self, start_marker: str, end_marker: str) -> str:
        index = self.text.find(start_marker)
        if index < 0:
            self.fail(f"review-evidence.md lost the {start_marker!r} marker")
        rest = self.text[index:]
        end = rest.find(end_marker, len(start_marker))
        return rest if end < 0 else rest[:end]

    def test_9_6_1_exemption_sentence_names_the_lifecycle_stage(self):
        body = self.section("### 9.6.1", "### 9.6.2")
        self.assertIn("--allow-placeholders", body)
        self.assertIn("P1-T08", body,
                      "the 9.6.1 exemption sentence must name the P1-T08 "
                      "lifecycle stage as part of the flag's scope")
        self.assertIn("git-ci-integration.md", body,
                      "the 9.6.1 exemption sentence must point at the "
                      "lifecycle stage's normative owner")
        self.assertIn("取回边界", body,
                      "the 9.6.1 exemption sentence must keep declaring that "
                      "the P1-T06 retrieval boundary is NOT exempted")

    def test_9_6_1_order_chain_includes_the_lifecycle_stage(self):
        body = self.section("### 9.6.1", "### 9.6.2")
        self.assertIn("P1-T08", body.split("```text", 1)[-1].split("```", 1)[0],
                      "the declared-once validate order chain must carry the "
                      "P1-T08 lifecycle stage the candidate folded in")

    def test_9_7_1_exemption_scope_names_the_lifecycle_stage(self):
        body = self.section("### 9.7.1", "### 9.7.2")
        self.assertIn("只豁免", body)
        self.assertIn("P1-T08", body,
                      "the 9.7.1 flag-scope sentence must name the P1-T08 "
                      "lifecycle stage alongside the P1-T05 disposition")
        self.assertIn("git-ci-integration.md", body,
                      "the 9.7.1 flag-scope sentence must point at the "
                      "lifecycle stage's normative owner")

    def test_9_1_subject_exemption_coverage_names_the_lifecycle_stage(self):
        body = self.section("### 9.1 subject", "### 9.2")
        self.assertIn("--allow-placeholders", body)
        self.assertIn("P1-T08", body,
                      "the 9.1 exemption-coverage sentence must name the "
                      "P1-T08 lifecycle stage in the flag's covered scope")

    def test_5_3_declares_the_caller_supplied_observation_boundary(self):
        cli_text = GIT_CI_PATH.read_text(encoding="utf-8")
        index = cli_text.find("### 5.3")
        if index < 0:
            self.fail("LIFECYCLE_ABSENT: git-ci-integration.md lost section "
                      "5.3")
        body = cli_text[index:]
        self.assertIn("hit_triggers", body,
                      "5.3's mechanical-consumption boundary must declare "
                      "that targeted invalidation is driven by caller-supplied "
                      "observations")
        self.assertIn("REUSE_SCOPE_INVALIDATED", body,
                      "5.3 must state which invalidation reasons are "
                      "reachable only from callers with observability")
        self.assertIn("每一次", body,
                      "5.3 must state that the UNKNOWN / malformed / source "
                      "legality checks run on every validate")


if __name__ == "__main__":
    unittest.main()
