"""Counterexample-driven checks for the P1-T07 evidence-consumption and
reviewer-authority separation rule in `references/review-and-repair-saturation.md`.

SUPPORT surface (RULES R6), NOT an authority surface. This module declares no
field name, no closed set and no machine shape: it reads the consumption rule
back out of the canonical owner and fails when that rule is absent, when a
consumer is allowed to derive authority it does not have, or when the owner
starts competing with the Review Evidence interface it is supposed to point at.

BINDING (counterexample-first, P1-T07 RED)
    On the pre-landing base the consumption rule does not exist, so every
    assertion below fails. After P1-T07 lands, the canonical owner must state,
    and this module must be able to execute:

      * CE-35 / AC-35 / INV-04 -- the observed set of changed files NEVER
        self-authorises an approved semantic scope; that status is written by
        reviewer authority and is never promoted by producer observation. A
        pack whose changed files exceed the approved surface does not thereby
        widen the approved scope.
      * CE-36 / AC-36 / INV-03 / AC-08 -- a machine evidence pack NEVER fills
        an independent reviewer verdict; reviewer-decision references are kept
        in fields separate from machine facts, so an empty run that exits 0
        cannot satisfy the consumer.
      * AC-36 -- the integrator consumes evidence with the SAME candidate
        binding, and a Stage packet REFERENCES canonical evidence instead of
        copying it into a third mutable ledger.
      * AC-44 condition 6 / AC-38 / CE-28 -- the section POINTS AT
        `references/review-evidence.md` instead of duplicating it, so the
        protected interface field names are absent from this document (the
        Review Evidence single-declaration scan must stay green).

WHY THE ABSENCE ASSERTION LIVES HERE
    `scripts/tests/` is an excluded test surface of the CE-28 declaration scan,
    so naming the protected tokens in this module declares nothing: it only
    locks the property that the canonical consumption owner must NOT name them.
    See `test_the_owner_does_not_declare_the_protected_field_names`.

A NOTE ON NON-VACUITY
    The decisions below are not greps: `parse_contract` reads the rule lines out
    of the document's fenced blocks and `decide` is driven by the parsed kinds.
    `test_contract_parser_reads_the_document_text` mutates the document and
    proves both that the parser is reading it and that the decisions follow.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_REL = "references/review-and-repair-saturation.md"
DOC = ROOT / DOC_REL
EVIDENCE_OWNER_REL = "references/review-evidence.md"

# --- document parsing ------------------------------------------------------

SECTION_HEADING_RE = re.compile(r"^##\s+6\.", re.M)
NEXT_SECTION_RE = re.compile(r"^##\s", re.M)
FENCE_RE = re.compile(r"^\s*```")
# A rule line: <RULE-ID> <KIND> <normative text>
RULE_LINE_RE = re.compile(
    r"^\s*(?P<rule>[A-Z]{2,}-[A-Z0-9-]+)\s+(?P<kind>[A-Z]{3,})\s+(?P<text>\S.*?)\s*$")

# The kinds the consumption contract may use. A rule line with any other kind
# does not parse, so dropping or corrupting a kind turns the checks RED.
RULE_KINDS = ("AUTHORITY", "FORBIDDEN", "REQUIRED", "OWNER", "POINTER", "REJECT")

# The rule IDs the canonical consumption owner must carry, with the kind that
# gives each one its meaning. Absence and re-typing both fail.
EXPECTED_RULES = {
    "CE-35-A": "AUTHORITY",   # observed changed files never self-authorise a scope
    "CE-35-B": "AUTHORITY",   # the status can only be written by reviewer authority
    "CE-35-C": "FORBIDDEN",   # promoting that status by producer observation
    "CE-36-A": "FORBIDDEN",   # a machine pack filling a reviewer verdict
    "CE-36-B": "REQUIRED",    # reviewer decision refs separated from machine facts
    "CE-36-C": "FORBIDDEN",   # exit 0 / empty run standing in for a verdict
    "CE-36-D": "REQUIRED",    # Stage packet references canonical evidence
    "CE-36-E": "FORBIDDEN",   # Stage packet copying into a third mutable ledger
    "CE-36-F": "REQUIRED",    # the integrator's same candidate binding
    "CE-38-A": "OWNER",       # the consumption rules' single canonical owner
    "CE-38-B": "OWNER",       # the field-name / closed-set single canonical owner
    "CE-38-C": "POINTER",     # other canonical surfaces only point / link
    "AC-44-P": "POINTER",     # this section points at the interface, not a copy
    "CE-28-D": "REJECT",      # a dual owner is rejected and converged
}

# The protected field-name / closed-set tokens of the Review Evidence
# interface. Assertion input (a lock on this document's pointer discipline),
# never a declaration point -- see the module docstring.
PROTECTED_TOKENS = (
    "semanticScopeStatus",
    "reviewerDecisionRefs",
    "STRUCTURALLY_VALID",
    "SOURCE_VERIFICATION_STATE",
    "EVIDENCE_SUFFICIENCY",
    "IDENTITY_VERSION_OR_DIGEST",
)


def section_six(text: str) -> str:
    """The body of `## 6. ...` up to the next level-2 heading (empty if absent)."""
    match = SECTION_HEADING_RE.search(text)
    if match is None:
        return ""
    rest = text[match.end():]
    nxt = NEXT_SECTION_RE.search(rest)
    return rest[: nxt.start()] if nxt else rest


def fenced_block_lines(lines):
    """Every line that sits inside a fenced block."""
    out, inside = [], False
    for line in lines:
        if FENCE_RE.match(line):
            inside = not inside
            continue
        if inside:
            out.append(line)
    return out


def parse_contract(section_text: str) -> dict:
    """Map rule id -> (kind, text) for the rule lines of the section's blocks."""
    contract = {}
    for line in fenced_block_lines(section_text.splitlines()):
        match = RULE_LINE_RE.match(line)
        if match is None:
            continue
        if match.group("kind") not in RULE_KINDS:
            continue
        contract[match.group("rule")] = (match.group("kind"), match.group("text"))
    return contract


def kind_of(contract: dict, rule: str):
    entry = contract.get(rule)
    return entry[0] if entry else None


# --- executable consumption rule -------------------------------------------

def clean_record() -> dict:
    return {
        "observed_changed_files": [DOC_REL],
        "approved_scope_widened_by_observation": False,
        "scope_status_written_by": "reviewer",
        "reviewer_verdict_written_by": "reviewer",
        "verdict_fields_shared_with_machine_facts": False,
        "machine_exit_zero_treated_as_verdict": False,
        "stage_packet_references_canonical_evidence": True,
        "stage_packet_copies_evidence": False,
        "candidate_binding": "same",
    }


def decide(record: dict, contract: dict):
    """Consume an evidence record; the decisions follow the parsed contract.

    Every check is gated on the kind the document declares for its rule, so a
    missing or re-typed rule stops enforcing that rule (and fails the tests).
    """
    problems = []
    if (kind_of(contract, "CE-35-A") == "AUTHORITY"
            and record["approved_scope_widened_by_observation"]):
        problems.append("OBSERVED_DELTA_SELF_AUTHORISED_THE_APPROVED_SEMANTIC_SCOPE")
    if (kind_of(contract, "CE-35-B") == "AUTHORITY"
            and record["scope_status_written_by"] != "reviewer"):
        problems.append("SEMANTIC_SCOPE_STATUS_NOT_WRITTEN_BY_REVIEWER_AUTHORITY")
    if (kind_of(contract, "CE-35-C") == "FORBIDDEN"
            and record["scope_status_written_by"] == "producer"):
        problems.append("PRODUCER_PROMOTED_THE_SEMANTIC_SCOPE_STATUS")
    if (kind_of(contract, "CE-36-A") == "FORBIDDEN"
            and record["reviewer_verdict_written_by"] == "machine"):
        problems.append("MACHINE_PACK_FILLED_AN_INDEPENDENT_REVIEWER_VERDICT")
    if (kind_of(contract, "CE-36-B") == "REQUIRED"
            and record["verdict_fields_shared_with_machine_facts"]):
        problems.append("REVIEWER_DECISION_REFS_NOT_SEPARATED_FROM_MACHINE_FACTS")
    if (kind_of(contract, "CE-36-C") == "FORBIDDEN"
            and record["machine_exit_zero_treated_as_verdict"]):
        problems.append("EMPTY_RUN_WITH_EXIT_ZERO_SATISFIED_THE_CONSUMER")
    if (kind_of(contract, "CE-36-D") == "REQUIRED"
            and not record["stage_packet_references_canonical_evidence"]):
        problems.append("STAGE_PACKET_DOES_NOT_REFERENCE_CANONICAL_EVIDENCE")
    if (kind_of(contract, "CE-36-E") == "FORBIDDEN"
            and record["stage_packet_copies_evidence"]):
        problems.append("STAGE_PACKET_COPIED_EVIDENCE_INTO_A_THIRD_MUTABLE_LEDGER")
    if (kind_of(contract, "CE-36-F") == "REQUIRED"
            and record["candidate_binding"] != "same"):
        problems.append("INTEGRATOR_DID_NOT_USE_THE_SAME_CANDIDATE_BINDING")
    return "REJECT" if problems else "ACCEPT"


def scan_tokens(text: str, tokens) -> list:
    return sorted(token for token in tokens if token in text)


class EvidenceConsumptionSeparationTests(unittest.TestCase):
    def setUp(self):
        self.text = DOC.read_text(encoding="utf-8")
        self.section = section_six(self.text)
        self.contract = parse_contract(self.section)

    # -- the canonical consumption owner carries the rule set ---------------

    def test_canonical_owner_declares_the_consumption_contract(self):
        self.assertTrue(
            self.section.strip(),
            f"{DOC_REL} has no section 6 declaring the evidence consumption and "
            "reviewer-authority separation rule")
        missing = sorted(
            rule for rule, kind in EXPECTED_RULES.items()
            if kind_of(self.contract, rule) != kind)
        self.assertEqual(
            [], missing,
            f"{DOC_REL} section 6 does not declare {missing} with the expected "
            f"kind; parsed={sorted(self.contract)}")

    def test_canonical_owner_literal_retained(self):
        self.assertIn(
            "Canonical owner", self.text,
            "VALIDATOR_INVARIANT_VIOLATED: references-declare-canonical-owner "
            "requires the literal 'Canonical owner' in every references/*.md")

    def test_legacy_review_grading_sections_retained(self):
        for marker in ("## 1. 评审分级（L0/L1/L2）", "## 4. PASS 语义与 findings 处置"):
            with self.subTest(marker=marker):
                self.assertIn(
                    marker, self.text,
                    f"{DOC_REL} lost the pre-existing review grading / PASS "
                    f"semantics section {marker!r}")

    # -- CE-35 / AC-35 / INV-04 --------------------------------------------

    def test_observed_changed_files_never_self_authorise_a_semantic_scope(self):
        self.assertEqual("AUTHORITY", kind_of(self.contract, "CE-35-A"))
        self.assertEqual("FORBIDDEN", kind_of(self.contract, "CE-35-C"))
        widened = clean_record()
        widened["observed_changed_files"] = [DOC_REL, "scripts/review_evidence.py"]
        widened["approved_scope_widened_by_observation"] = True
        widened["scope_status_written_by"] = "producer"
        self.assertEqual(
            "REJECT", decide(widened, self.contract),
            "a pack whose changed files exceed the approved surface must not "
            "thereby widen the approved semantic scope")
        self.assertEqual(
            "ACCEPT", decide(clean_record(), self.contract),
            "a reviewer-authored status inside the approved surface must be accepted")

    def test_semantic_scope_status_needs_reviewer_authority_not_producer_observation(self):
        self.assertEqual("AUTHORITY", kind_of(self.contract, "CE-35-B"))
        machine_written = clean_record()
        machine_written["scope_status_written_by"] = "machine"
        self.assertEqual(
            "REJECT", decide(machine_written, self.contract),
            "the semantic scope status must not be derivable from observed data")
        for writer in ("producer", "machine"):
            with self.subTest(writer=writer):
                record = clean_record()
                record["scope_status_written_by"] = writer
                self.assertEqual("REJECT", decide(record, self.contract))

    # -- CE-36 / AC-36 / AC-08 / INV-03 ------------------------------------

    def test_machine_pack_never_fills_an_independent_reviewer_verdict(self):
        self.assertEqual("FORBIDDEN", kind_of(self.contract, "CE-36-A"))
        self.assertEqual("REQUIRED", kind_of(self.contract, "CE-36-B"))
        machine_verdict = clean_record()
        machine_verdict["reviewer_verdict_written_by"] = "machine"
        self.assertEqual("REJECT", decide(machine_verdict, self.contract))
        shared_fields = clean_record()
        shared_fields["verdict_fields_shared_with_machine_facts"] = True
        self.assertEqual(
            "REJECT", decide(shared_fields, self.contract),
            "reviewer decision references must stay in fields separate from "
            "machine facts")

    def test_empty_run_with_exit_zero_cannot_satisfy_the_consumer(self):
        """CE-08 / AC-08."""
        self.assertEqual("FORBIDDEN", kind_of(self.contract, "CE-36-C"))
        empty_run = clean_record()
        empty_run["machine_exit_zero_treated_as_verdict"] = True
        self.assertEqual(
            "REJECT", decide(empty_run, self.contract),
            "a validator exit 0 with an empty run and no valid result must not "
            "satisfy the consumer")

    def test_stage_packet_references_canonical_evidence_without_a_third_ledger(self):
        self.assertEqual("REQUIRED", kind_of(self.contract, "CE-36-D"))
        self.assertEqual("FORBIDDEN", kind_of(self.contract, "CE-36-E"))
        copier = clean_record()
        copier["stage_packet_copies_evidence"] = True
        copier["stage_packet_references_canonical_evidence"] = False
        self.assertEqual(
            "REJECT", decide(copier, self.contract),
            "a Stage packet that copies canonical evidence into a third mutable "
            "ledger must be rejected")
        referencing_only = clean_record()
        self.assertEqual("ACCEPT", decide(referencing_only, self.contract))

    def test_integrator_consumes_evidence_with_the_same_candidate_binding(self):
        self.assertEqual("REQUIRED", kind_of(self.contract, "CE-36-F"))
        stale = clean_record()
        stale["candidate_binding"] = "different"
        self.assertEqual(
            "REJECT", decide(stale, self.contract),
            "the integrator must consume evidence bound to the same candidate")

    # -- AC-44 condition 6 / AC-38 / CE-28 ---------------------------------

    def test_the_section_points_at_the_evidence_interface_instead_of_duplicating_it(self):
        self.assertEqual("POINTER", kind_of(self.contract, "AC-44-P"))
        self.assertEqual("REJECT", kind_of(self.contract, "CE-28-D"))
        self.assertIn(
            EVIDENCE_OWNER_REL, self.section,
            f"{DOC_REL} section 6 does not name {EVIDENCE_OWNER_REL} as the "
            "owner of the field names it consumes")
        self.assertIn(
            "不重声明", self.section,
            f"{DOC_REL} section 6 does not state that it does not restate the "
            "field names / closed sets declared by the Review Evidence owner")

    def test_the_owner_does_not_declare_the_protected_field_names(self):
        """CE-28 / AC-44: a second declaration point must not appear here."""
        found = scan_tokens(self.text, PROTECTED_TOKENS)
        self.assertEqual(
            [], found,
            f"DUAL_DECLARATION (CE-28): {DOC_REL} declares the Review Evidence "
            f"field-name contract outside the single interface; unexpected={found}")

    def test_protected_token_scan_is_not_vacuous(self):
        control = "| field | note |\n| --- | --- |\n| `semanticScopeStatus` | x |\n"
        self.assertTrue(
            scan_tokens(control, PROTECTED_TOKENS),
            "the protected-token scan is vacuous: it missed an injected "
            "competing declaration")
        self.assertEqual(sorted(PROTECTED_TOKENS),
                         scan_tokens(" ".join(PROTECTED_TOKENS), PROTECTED_TOKENS))

    def test_single_owner_separation_is_stated(self):
        self.assertEqual("OWNER", kind_of(self.contract, "CE-38-A"))
        self.assertEqual("OWNER", kind_of(self.contract, "CE-38-B"))
        self.assertEqual("POINTER", kind_of(self.contract, "CE-38-C"))
        self.assertEqual(
            "OWNER", self.contract["CE-38-A"][0],
            "the consumption rules must name their single canonical owner")
        self.assertIn(
            EVIDENCE_OWNER_REL, self.text,
            "the field-name / closed-set owner must be named as the Review "
            "Evidence interface")

    # -- non-vacuity: the decisions follow the document --------------------

    def test_contract_parser_reads_the_document_text(self):
        """Dropping or re-typing a rule in the document must change decisions."""
        self.assertTrue(self.contract, "the contract parser read nothing")

        without_self_authorisation = "\n".join(
            line for line in self.section.splitlines()
            if not re.match(r"^\s*CE-35-[A-Z]\s", line))
        weakened = parse_contract(without_self_authorisation)
        self.assertNotEqual(
            self.contract, weakened,
            "the contract parser is not reading the document text")
        self.assertIsNone(kind_of(weakened, "CE-35-A"))

        widened = clean_record()
        widened["approved_scope_widened_by_observation"] = True
        widened["scope_status_written_by"] = "producer"
        self.assertEqual(
            "REJECT", decide(widened, self.contract),
            "the live contract must reject a self-authorised scope")
        self.assertEqual(
            "ACCEPT", decide(widened, weakened),
            "the mutation did not change the decision, so these checks are not "
            "capture-capable")

        retyped = "\n".join(
            re.sub(r"^(?P<lead>\s*CE-36-A\s+)FORBIDDEN\b", r"\g<lead>AUTHORITY", line)
            for line in self.section.splitlines())
        retyped_contract = parse_contract(retyped)
        machine_verdict = clean_record()
        machine_verdict["reviewer_verdict_written_by"] = "machine"
        self.assertEqual("REJECT", decide(machine_verdict, self.contract))
        self.assertEqual(
            "ACCEPT", decide(machine_verdict, retyped_contract),
            "re-typing CE-36-A from FORBIDDEN to AUTHORITY did not change the "
            "decision")

    def test_every_expectation_has_a_declared_rule(self):
        """No expectation may be satisfied by a rule the document does not carry."""
        for rule, kind in EXPECTED_RULES.items():
            with self.subTest(rule=rule):
                self.assertIn(rule, self.contract,
                              f"{DOC_REL} section 6 is missing rule {rule}")
                self.assertEqual(kind, self.contract[rule][0])
                self.assertTrue(
                    self.contract[rule][1].strip(),
                    f"{DOC_REL} rule {rule} carries no normative text")


if __name__ == "__main__":
    unittest.main()
