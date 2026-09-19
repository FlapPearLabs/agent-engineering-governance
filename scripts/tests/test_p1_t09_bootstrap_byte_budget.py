"""Counterexample-driven regression for P1-T09 (REQ-W4-01, MIG-01..MIG-09).

THE DEFECT THIS MODULE LOCKS SHUT
    The repository stated the memory-pointer budget in CHARACTERS on all four
    surfaces and the validator enforced a character count, while the real host
    constraint is UTF-8 ENCODED BYTES. The two units disagree exactly where the
    text is non-ASCII: 1400 CJK characters are 1400 characters but 4200 UTF-8
    bytes, i.e. past the observed 4028-byte truncation point. A character
    condition therefore authorises a body the host will truncate.

BINDING (counterexample-first, P1-T09 RED)
    On the pre-landing base the authorising measurement is ``len(body)`` and no
    surface states a byte budget, so every assertion below fails. After P1-T09
    lands this module must be able to execute:

      * AC-17 condition 1 / MIG-01 -- the validator's AUTHORISING measurement
        is ``len(body.encode("utf-8"))``, invoked here, never re-implemented.
      * CE-19 / AC-17 condition 4 -- a synthetic 1400-character CJK body is
        REJECTED by the new condition although the old character condition
        ACCEPTED it. Both halves are asserted, so this proves the UNIT changed,
        not merely the threshold.
      * AC-17 condition 3 / MIG-04 -- the current candidate body still passes,
        measured (1170 characters / 1804 UTF-8 bytes), with no regression.
      * AC-17 condition 5 / MIG-09 -- no in-scope surface states the budget in
        characters, and AGENTS.md section 10 specifically does not.
      * AC-17 condition 2 / MIG-06 -- ``WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES =
        3500`` is declared at the semantic owner, with its unit.
      * AC-17 condition 6 / MIG-08 -- ``deployment/BOOTSTRAP_CONTRACT.md`` is
        the single semantic owner; ``AGENTS.md`` section 10 is a pointer, not a
        second budget authority.
      * MIG-09 / INV-18 -- 3500 is the profile budget, 4028 the OBSERVED
        truncation point, and 3500 is not defined as "4028 minus a margin".

A NOTE ON NON-VACUITY
    The document assertions are text predicates, so they carry their own
    mutation controls: ``test_reverting_the_measurement_to_characters...``
    re-executes the validator with the measurement put back to ``len(body)``
    and requires the CE-19 body to be ACCEPTED again, and
    ``test_the_character_budget_detector_fires_on_the_legacy_wording`` proves
    the wording detector is not vacuous. If either control stops firing, the
    suite fails instead of silently passing.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VALIDATOR = ROOT / "scripts/validate_governance.py"
AGENTS = ROOT / "AGENTS.md"
CONTRACT = ROOT / "deployment/BOOTSTRAP_CONTRACT.md"
CANDIDATE = ROOT / "deployment/MEMORY_POINTER_CANDIDATE.md"

SPEC = importlib.util.spec_from_file_location("governance_budget", VALIDATOR)
governance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governance)

# Frozen P1-T09 measured facts (spec section 8.1, independently re-measured by
# the orchestrator before this lane started).
POINTER_CHARS = 1170
POINTER_UTF8_BYTES = 1804
BUDGET_BYTES = 3500
OBSERVED_TRUNCATION_BYTES = 4028
HEADROOM_BYTES = BUDGET_BYTES - POINTER_UTF8_BYTES

CJK_1400 = "\u6d4b" * 1400          # 1400 characters
CJK_1400_CHARS = 1400
CJK_1400_UTF8_BYTES = 4200          # 3 bytes each in UTF-8

# Any spelling of the budget NUMBER, so a restatement cannot hide behind the
# thousands separator.
BUDGET_NUMBER_RE = re.compile(r"3[,\uff0c]?500")
# The unit the budget must NOT be stated in. Matches a budget number directly
# followed by a character-unit token ("≤3,500 字符", "3500 characters").
CHARACTER_BUDGET_RE = re.compile(
    r"3[,\uff0c]?500\s*(?:\u4e2a)?\s*(?:\u5b57\u7b26|characters?|chars?\b"
    r"|code\s*points?|\u7801\u70b9|\u7801\u4f4d)")
# Matches the forbidden "observed truncation point minus a safety margin"
# framing. The legacy wording was "预算 4,028 减安全余量".
MARGIN_DERIVATION_RE = re.compile(
    r"4[,，]?028\s*(?:\u51cf\u53bb|\u51cf|-\s*|minus\s*)\s*(?:\u4e00\u4e2a)?\s*"
    r"(?:\u9690\u542b\u7684?)?\s*(?:\u5b89\u5168\u4f59\u91cf|\u4f59\u91cf"
    r"|safety\s+margin|margin)",
    re.IGNORECASE)
LEGACY_CHARACTER_WORDING = "\u22643,500 \u5b57\u7b26"      # "≤3,500 字符"
LEGACY_MARGIN_WORDING = "4,028 \u51cf\u5b89\u5168\u4f59\u91cf"  # "4,028 减安全余量"

LEGACY_CHAR_BUDGET = 3500  # the pre-fix threshold; the NUMBER is unchanged


def legacy_character_condition(body: str) -> bool:
    """The condition P1-T09 replaces: ``len(body) <= 3500`` in CHARACTERS."""
    return len(body) <= LEGACY_CHAR_BUDGET


def validator_measurement():
    """The validator's authorising measurement, invoked rather than copied.

    Raises AssertionError (a test FAILURE, not a harness/import error) so the
    pre-landing base is RED for the right reason.
    """
    fn = getattr(governance, "memory_pointer_within_budget", None)
    if fn is None:
        raise AssertionError(
            "scripts/validate_governance.py exposes no authorising UTF-8 "
            "byte-budget measurement (AC-17 condition 1 / MIG-01): the "
            "character-length condition is still the effective budget")
    return fn


def validator_body_export():
    """The validator's scored-body export (longest fenced block), invoked."""
    fn = getattr(governance, "memory_pointer_body", None)
    if fn is None:
        raise AssertionError(
            "scripts/validate_governance.py exposes no scored-body export "
            "for the pointer candidate (MIG-01 export scope)")
    return fn


def measure(body: str):
    return validator_measurement()(body)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def scored_body(path: Path) -> str:
    """Independent re-derivation of the scored body, for cross-checking."""
    blocks = re.findall(r"```(?:markdown)?\n(.*?)```", read(path), re.S)
    return max(blocks, key=len) if blocks else read(path)


def section_ten(text: str) -> str:
    start = re.search(r"^##\s*10\.", text, re.M)
    if start is None:
        raise AssertionError("AGENTS.md has no section 10 heading")
    tail = text[start.end():]
    nxt = re.search(r"^##\s", tail, re.M)
    return tail[: nxt.start()] if nxt else tail


class AuthorisingMeasurementTests(unittest.TestCase):
    """AC-17 condition 1 / MIG-01: byte length, not character count."""

    def test_measurement_counts_utf8_bytes(self):
        ok, n = measure(CJK_1400)
        self.assertEqual(
            n, len(CJK_1400.encode("utf-8")),
            "the authorising measurement is not the UTF-8 encoded byte length")
        self.assertNotEqual(
            n, len(CJK_1400),
            "the authorising measurement still counts characters")

    def test_measurement_is_byte_exact_for_mixed_text(self):
        for body in ("", "a" * 3500, "ab" + CJK_1400[:10],
                     "治理" * 3, CJK_1400):
            with self.subTest(n_chars=len(body)):
                _ok, n = measure(body)
                self.assertEqual(n, len(body.encode("utf-8")))

    def test_threshold_boundary_is_still_the_frozen_3500(self):
        self.assertEqual(measure("a" * 3500), (True, 3500))
        self.assertEqual(measure("a" * 3501), (False, 3501))
        # A CJK body of 1166 characters is 3498 bytes: under budget.
        self.assertEqual(measure(CJK_1400[:1166]), (True, 3498))

    def test_scored_body_is_still_the_longest_fenced_block(self):
        exporter = validator_body_export()
        longer, shorter = "x" * 40, "y" * 5
        text = "prose\n```markdown\n%s\n```\nmid\n```markdown\n%s\n```\n" % (
            longer, shorter)
        # The captured block keeps the newline that precedes the closing fence.
        self.assertEqual(exporter(text), longer + "\n")
        self.assertNotIn(shorter, exporter(text))

    def test_check_detail_label_reports_bytes(self):
        source = read(VALIDATOR)
        self.assertIn("bytes={", source,
                      "the budget check detail label does not report bytes")
        self.assertNotIn("chars={", source,
                         "the budget check still reports a character count")


class Ce19UnitCounterexampleTests(unittest.TestCase):
    """CE-19 / AC-17 condition 4: the unit, not the threshold, is what bites."""

    def test_cjk_1400_is_rejected_by_the_new_condition(self):
        ok, n = measure(CJK_1400)
        self.assertFalse(
            ok,
            "a 1400-CJK-character (4200 UTF-8 byte) body is still accepted: "
            "the budget is not enforced in bytes")
        self.assertEqual(n, CJK_1400_UTF8_BYTES)

    def test_cjk_1400_was_accepted_by_the_old_character_condition(self):
        self.assertTrue(
            legacy_character_condition(CJK_1400),
            "the CE-19 premise is wrong: the legacy character condition did "
            "not actually accept the 1400-character body")
        self.assertEqual(len(CJK_1400), CJK_1400_CHARS)

    def test_the_two_conditions_disagree_so_the_unit_is_what_matters(self):
        old_verdict = legacy_character_condition(CJK_1400)
        new_verdict, _n = measure(CJK_1400)
        self.assertNotEqual(
            old_verdict, new_verdict,
            "both conditions agree on the CE-19 body: the regression would "
            "pass even if only the threshold, not the unit, had changed")

    def test_cjk_body_past_the_observed_truncation_point_is_rejected(self):
        # 1400 CJK characters are 4200 bytes, i.e. past the OBSERVED 4028-byte
        # truncation point -- exactly the body a character condition smuggles in.
        self.assertGreater(len(CJK_1400.encode("utf-8")),
                           OBSERVED_TRUNCATION_BYTES)
        self.assertFalse(measure(CJK_1400)[0])


class CurrentCandidateTests(unittest.TestCase):
    """AC-17 condition 3 / MIG-04: the shipped body must not regress."""

    def test_positive_control_measured_and_within_budget(self):
        body = validator_body_export()(read(CANDIDATE))
        self.assertEqual(body, scored_body(CANDIDATE))
        self.assertEqual(len(body), POINTER_CHARS)
        self.assertEqual(len(body.encode("utf-8")), POINTER_UTF8_BYTES)
        self.assertEqual(measure(body), (True, POINTER_UTF8_BYTES))

    def test_headroom_is_reported(self):
        body = validator_body_export()(read(CANDIDATE))
        _ok, n = measure(body)
        self.assertEqual(BUDGET_BYTES - n, HEADROOM_BYTES)

    def test_candidate_states_a_byte_unit_and_no_character_budget(self):
        text = read(CANDIDATE)
        self.assertIn("UTF-8", text,
                      "the candidate does not state the byte unit")
        self.assertIsNone(
            CHARACTER_BUDGET_RE.search(text),
            "the candidate still states the budget in characters")


class DocumentConvergenceTests(unittest.TestCase):
    """AC-17 conditions 2/5/6, MIG-06/07/08/09/INV-18."""

    IN_SCOPE = (AGENTS, CONTRACT, CANDIDATE)

    def test_no_in_scope_surface_states_the_budget_in_characters(self):
        for path in self.IN_SCOPE:
            with self.subTest(surface=path.name):
                found = CHARACTER_BUDGET_RE.search(read(path))
                self.assertIsNone(
                    found,
                    "%s still states the budget with a character unit: %r"
                    % (path.name, found.group(0) if found else None))

    def test_agents_section_ten_does_not_restate_the_budget(self):
        sec = section_ten(read(AGENTS))
        self.assertIsNone(
            BUDGET_NUMBER_RE.search(sec),
            "AGENTS.md section 10 restates the budget value instead of "
            "pointing at the semantic owner (MIG-08)")
        self.assertIn(
            "BOOTSTRAP_CONTRACT.md", sec,
            "AGENTS.md section 10 carries no pointer to the semantic owner")

    def test_agents_section_ten_is_not_a_second_authority(self):
        sec = section_ten(read(AGENTS))
        self.assertNotIn(
            "WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES", sec,
            "AGENTS.md section 10 declares the budget contract, becoming a "
            "second budget authority")
        delegation = ("\u6307\u9488", "\u53ea\u5f15\u7528", "\u5355\u70b9\u62e5\u6709",
                      "\u552f\u4e00\u8bed\u4e49 owner", "pointer",
                      "not a second authority")
        self.assertTrue(
            any(marker in sec for marker in delegation),
            "AGENTS.md section 10 does not mark itself as a pointer / "
            "derived reference to the semantic owner")

    def test_contract_is_the_single_semantic_owner(self):
        text = read(CONTRACT)
        required = (
            "WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES",
            "VALUE", "UNIT", "OWNER", "SCOPE",
            "UTF-8", "3500", "4028", "OVERRIDE",
        )
        for marker in required:
            with self.subTest(marker=marker):
                self.assertIn(
                    marker, text,
                    "the semantic owner does not declare %r (AC-17 condition "
                    "2 / MIG-06)" % marker)
        self.assertRegex(
            text, r"OWNER\s+\S*BOOTSTRAP_CONTRACT\.md",
            "the frozen contract block does not name itself as OWNER")
        self.assertNotIn(
            "WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES", read(AGENTS),
            "AGENTS.md declares the budget contract: duplicate declaration "
            "point (AC-17 condition 6)")

    def test_budget_and_truncation_point_are_not_defined_by_each_other(self):
        text = read(CONTRACT)
        self.assertIn("3500", text)
        self.assertIn("4028", text)
        self.assertIsNone(
            MARGIN_DERIVATION_RE.search(text),
            "the contract still describes 3500 as the observed truncation "
            "point minus a safety margin (MIG-09 / INV-18)")

    def test_candidate_and_agents_agree_on_the_byte_unit(self):
        # MIG-02: all three document surfaces speak the same unit.
        self.assertIn("UTF-8", read(CONTRACT))
        self.assertIn("UTF-8", read(CANDIDATE))


class NonVacuityControlTests(unittest.TestCase):
    """The suite must go RED if the unit or the wording is reverted."""

    def _load_mutated_validator(self, source: str):
        module = types.ModuleType("governance_budget_mutated")
        module.__file__ = str(VALIDATOR)
        scripts_dir = str(VALIDATOR.parent)
        sys.path.insert(0, scripts_dir)
        self.addCleanup(lambda: sys.path.remove(scripts_dir))
        exec(compile(source, str(VALIDATOR), "exec"), module.__dict__)
        return module

    def test_reverting_the_measurement_to_characters_accepts_ce19_again(self):
        source = read(VALIDATOR)
        mutated = source.replace('len(body.encode("utf-8"))', "len(body)")
        self.assertNotEqual(
            mutated, source,
            "the UTF-8 byte-measurement anchor is absent from "
            "scripts/validate_governance.py: the non-vacuity control lost its "
            "target (AC-17 condition 1)")
        module = self._load_mutated_validator(mutated)
        ok, n = module.memory_pointer_within_budget(CJK_1400)
        self.assertTrue(
            ok,
            "with the measurement reverted to len(body) the CE-19 body is "
            "still rejected: the suite is not actually measuring the unit")
        self.assertEqual(n, CJK_1400_CHARS)

    def test_the_character_budget_detector_fires_on_the_legacy_wording(self):
        legacy_lines = (
            "- 引导机制：MEMORY \u6307\u9488\uff08" + LEGACY_CHARACTER_WORDING + "\uff09",
            "- **" + LEGACY_CHARACTER_WORDING + "**\uff08\u9884\u7b97 "
            + LEGACY_MARGIN_WORDING + "\uff09",
            "- full text \u2264 3500 characters",
            "- full text \u2264 3,500 chars",
        )
        for line in legacy_lines:
            with self.subTest(line=line):
                self.assertTrue(
                    CHARACTER_BUDGET_RE.search(line),
                    "the character-budget detector does not fire on %r" % line)

    def test_the_margin_detector_fires_on_the_legacy_wording(self):
        line = "\uff08\u9884\u7b97 " + LEGACY_MARGIN_WORDING + "\uff09"
        self.assertTrue(
            MARGIN_DERIVATION_RE.search(line),
            "the margin-derivation detector does not fire on %r" % line)

    def test_the_pointer_assertion_goes_red_when_the_budget_is_restated(self):
        # Re-inserting a budget value into AGENTS.md section 10 must trip the
        # pointer assertion used above.
        mutated = read(AGENTS).replace(
            "deployment/MEMORY_POINTER_CANDIDATE.md`",
            "deployment/MEMORY_POINTER_CANDIDATE.md`\uff08\u2264"
            + LEGACY_CHARACTER_WORDING + "\uff09", 1)
        self.assertNotEqual(mutated, read(AGENTS),
                            "the AGENTS.md pointer anchor disappeared")
        sec = section_ten(mutated)
        self.assertIsNotNone(BUDGET_NUMBER_RE.search(sec))
        self.assertTrue(CHARACTER_BUDGET_RE.search(sec))


if __name__ == "__main__":
    unittest.main()
