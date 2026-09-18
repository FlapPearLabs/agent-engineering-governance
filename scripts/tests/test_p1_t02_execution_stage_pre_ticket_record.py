"""Counterexample-driven checks for the P1-T02 pre-ticket identification record
in `references/execution-stage.md` section 6.

SUPPORT surface (RULES R6), NOT an authority surface. This module declares no
seam field and no requirement: it re-reads the canonical reference and fails
when section 6 of `references/execution-stage.md` loses the mandatory pre-ticket
identification record that P1-T02 owns.

BINDING (counterexample-first, P1-T02 RED)
    The expected behaviour is DERIVED FROM THE DOCUMENT TEXT:
      * the five REQ-W1-02-owned record fields (SEAM_IDENTIFICATION,
        CONTRACT_SOURCE, PRODUCTION_SHAPE_SOURCE, COUNTEREXAMPLE_DEFINITION,
        EXPECTED_RED_CONDITION) must be declared as field-list entries inside a
        fenced block within section 6, and those five must be the ONLY field
        entries declared there;
      * the mandatory base record must be stated as EIGHT fields: the five
        components DEFINED HERE plus the three always-required P1-T01 shared
        slots (RED_EXECUTION_OWNER, REACHABILITY_APPLICABILITY,
        REACHABILITY_PROOF_OWNER), which are MEMBERS of the base yet consumed
        BY REFERENCE, not declared here (MF-1);
      * the N/A path must add exactly the two conditional slots
        (REACHABILITY_APPLICABILITY_REASON and
        REACHABILITY_APPLICABILITY_ACCEPTANCE_REF), i.e. eight + two = ten
        slots on that path — MORE than the eight base fields, not fewer;
      * the RED lifecycle rule (RED runs only after TICKET_AUTHORIZATION and
        before implementation, never at decomposition time) must be stated;
      * the no-implicit-aliasing statement between the two symbol families must
        be stated;
      * the five REQ-W1-02-owned fields must NOT be declared as field entries in
        `references/ticket-lane.md` (single declaration point lives here);
      * the P1-T01-frozen applicability/RED slots must appear in section 6 only
        as references, never as field-entry declarations (CE-30).

A drift of the *documented* contract turns these tests RED instead of passing
CI silently. Before P1-T02 lands, section 6 contains no such record, so the
mechanical rejection check FAILS (the canonical RED condition for this ticket).
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXEC_REL = "references/execution-stage.md"
TICKET_LANE_REL = "references/ticket-lane.md"
EXEC_STAGE = ROOT / EXEC_REL
TICKET_LANE = ROOT / TICKET_LANE_REL

# The five REQ-W1-02-owned record fields, defined HERE in section 6.
OWNED_FIELDS = (
    "SEAM_IDENTIFICATION",
    "CONTRACT_SOURCE",
    "PRODUCTION_SHAPE_SOURCE",
    "COUNTEREXAMPLE_DEFINITION",
    "EXPECTED_RED_CONDITION",
)

# P1-T01-frozen applicability / RED slots consumed by reference only.
FROZEN_SLOTS = (
    "REACHABILITY_APPLICABILITY",
    "REACHABILITY_APPLICABILITY_REASON",
    "REACHABILITY_APPLICABILITY_ACCEPTANCE_REF",
    "REACHABILITY_PROOF_OWNER",
    "RED_EXECUTION_OWNER",
)

# Of those frozen slots, exactly three are ALWAYS required and are therefore
# members of the mandatory base record; the remaining two are conditional
# additions that only the N/A path carries.
ALWAYS_REQUIRED_SHARED_BASE_SLOTS = (
    "RED_EXECUTION_OWNER",
    "REACHABILITY_APPLICABILITY",
    "REACHABILITY_PROOF_OWNER",
)
CONDITIONAL_NA_SLOTS = (
    "REACHABILITY_APPLICABILITY_REASON",
    "REACHABILITY_APPLICABILITY_ACCEPTANCE_REF",
)

# The mandatory base composition required by REQ-W1-02 (MF-1):
#   DECLARED HERE            = 5 owned components
#   MANDATORY BASE COMPOSITION = 5 declared here + 3 always-required shared
#                                P1-T01 slots = 8
#   N/A path                 = 8 + 2 conditional slots = 10
OWNED_COMPONENT_COUNT = len(OWNED_FIELDS)
SHARED_BASE_MEMBER_COUNT = len(ALWAYS_REQUIRED_SHARED_BASE_SLOTS)
MANDATORY_BASE_COUNT = OWNED_COMPONENT_COUNT + SHARED_BASE_MEMBER_COUNT
NA_PATH_COUNT = MANDATORY_BASE_COUNT + len(CONDITIONAL_NA_SLOTS)

# The forbidden implicit aliases (P1-T02 contract).
FORBIDDEN_ALIASES = (
    ("SEAM_IDENTIFICATION", "SEAM_ID"),
    ("CONTRACT_SOURCE", "AUTHORITY_REF"),
    ("PRODUCTION_SHAPE_SOURCE", "REAL_SHAPE_FIXTURE_OR_ADAPTER"),
    ("COUNTEREXAMPLE_DEFINITION", "SEAM_COUNTEREXAMPLES"),
)

# Markers that locate the normative composition statements in the prose.
BASE_MARKER_RE = re.compile(r"强制基|MANDATORY[ _]BASE|mandatory base")
BY_REFERENCE_RE = re.compile(
    r"仅引用不重定义|按引用消费|consumed by reference|by reference")
NOT_DECLARED_HERE_RE = re.compile(
    r"不由本文件声明|不在此声明|not declared here|NOT DECLARED HERE")
OWNED_COMPONENT_MARKER_RE = re.compile(r"五个|5\s*个|five")
EIGHT_FIELD_MARKER_RE = re.compile(r"八字段|八个|8\s*个|eight")
COMPONENT_OF_RE = re.compile(r"组成部分|组件|component")
ADDITIVE_CLAIM_RE = re.compile(r"(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)")

SECTION_SIX_RE = re.compile(r"^##\s+6\.", re.M)
NEXT_SECTION_RE = re.compile(r"^##\s", re.M)
FENCE_RE = re.compile(r"^\s*```")
FIELD_ENTRY_RE = re.compile(
    r"^\s*[A-Z][A-Z0-9_]*(?:\s*/\s*[A-Z][A-Z0-9_]*)*\s*(?:#.*)?$")


def section_six(text: str) -> str:
    """Body of `## 6. ...` up to the next level-2 heading."""
    match = SECTION_SIX_RE.search(text)
    if match is None:
        return ""
    rest = text[match.end():]
    nxt = NEXT_SECTION_RE.search(rest)
    return rest[: nxt.start()] if nxt else rest


def fenced_blocks(lines):
    blocks, buf, inside = [], [], False
    for line in lines:
        if FENCE_RE.match(line):
            if inside:
                blocks.append(buf)
                buf = []
            inside = not inside
            continue
        if inside:
            buf.append(line)
    return blocks


def field_entry_names(line: str):
    if not FIELD_ENTRY_RE.match(line):
        return set()
    body = line.split("#", 1)[0]
    return {token.strip() for token in body.split("/") if token.strip()}


def declared_field_entries(blocks):
    names = set()
    for block in blocks:
        for line in block:
            names |= field_entry_names(line)
    return names


def is_field_entry_declared(text: str, name: str) -> bool:
    """True if `name` appears as a field-list ENTRY inside any fenced block."""
    for block in fenced_blocks(text.splitlines()):
        for line in block:
            if name in field_entry_names(line):
                return True
    return False


def paragraphs(text: str):
    """Blank-line separated blocks of text."""
    return [block for block in re.split(r"\n[ \t]*\n", text) if block.strip()]


def additive_claims(text: str):
    """Every `a + b = c` arithmetic claim stated in the text."""
    return {
        (int(a), int(b), int(c))
        for a, b, c in ADDITIVE_CLAIM_RE.findall(text)
    }


class PreTicketIdentificationRecordTests(unittest.TestCase):
    def setUp(self):
        self.exec_text = EXEC_STAGE.read_text(encoding="utf-8")
        self.exec_lines = self.exec_text.splitlines()
        self.section6 = section_six(self.exec_text)
        self.section6_lines = self.section6.splitlines()
        self.section6_blocks = fenced_blocks(self.section6_lines)
        self.section6_declared = declared_field_entries(self.section6_blocks)

        self.ticket_lane_text = TICKET_LANE.read_text(encoding="utf-8")

    # -- the five REQ-W1-02-owned fields must be DEFINED in section 6 --------

    def test_section_six_defines_every_owned_record_field(self):
        for name in OWNED_FIELDS:
            with self.subTest(field=name):
                self.assertIn(
                    name, self.section6_declared,
                    f"{EXEC_REL} section 6 does not declare the "
                    f"REQ-W1-02-owned pre-ticket record field {name}")

    def test_owned_fields_declared_inside_a_fenced_block(self):
        # At least one fenced block within section 6 carries the owned fields
        # as a coherent field list (not merely mentioned in prose).
        found = any(
            OWNED_FIELDS[0] in declared_field_entries([block])
            for block in self.section6_blocks
        )
        self.assertTrue(
            found,
            f"{EXEC_REL} section 6 has no fenced field-list block carrying "
            f"the pre-ticket identification record fields")

    # -- MF-1: the mandatory base record is EIGHT fields, not five ----------

    def test_section_six_declares_only_the_five_owned_components(self):
        """(a) 5 DECLARED HERE: the single declaration point carries exactly the
        five owned components — never the shared slots (CE-30 holds)."""
        self.assertEqual(
            self.section6_declared, set(OWNED_FIELDS),
            f"{EXEC_REL} section 6 must DECLARE exactly the "
            f"{OWNED_COMPONENT_COUNT} REQ-W1-02-owned components and nothing "
            f"else; declared={sorted(self.section6_declared)}")

    def test_owned_five_are_stated_as_components_of_the_eight_field_base(self):
        """(a)+(c) MF-1 root cause: the five must read as the five components OF
        the eight-field mandatory base, never as the mandatory base itself."""
        for para in paragraphs(self.section6):
            if "DEFINED HERE" not in para:
                continue
            if not OWNED_COMPONENT_MARKER_RE.search(para):
                continue
            if not EIGHT_FIELD_MARKER_RE.search(para):
                continue
            if not COMPONENT_OF_RE.search(para):
                continue
            return
        self.fail(
            f"{EXEC_REL} section 6 presents the five owned fields without "
            f"stating that they are the five components OF the "
            f"{MANDATORY_BASE_COUNT}-field mandatory base")

    def test_mandatory_base_composition_is_five_plus_three_equals_eight(self):
        """(b)+(c) The three always-required shared P1-T01 slots must be named as
        MEMBERS of the mandatory base while staying consumed BY REFERENCE."""
        self.assertEqual(OWNED_COMPONENT_COUNT, 5)
        self.assertEqual(SHARED_BASE_MEMBER_COUNT, 3)
        self.assertEqual(MANDATORY_BASE_COUNT, 8)

        markers = {
            "names all three always-required shared slots": lambda p: all(
                slot in p for slot in ALWAYS_REQUIRED_SHARED_BASE_SLOTS),
            "marks them as members of the mandatory base": lambda p: bool(
                BASE_MARKER_RE.search(p)),
            "says they are consumed by reference": lambda p: bool(
                BY_REFERENCE_RE.search(p)),
            "says they are not declared here": lambda p: bool(
                NOT_DECLARED_HERE_RE.search(p)),
            "cites the P1-T01 authority ticket-lane.md 3.1.1": lambda p: (
                "ticket-lane.md" in p and "3.1.1" in p),
        }
        for para in paragraphs(self.section6):
            if all(predicate(para) for predicate in markers.values()):
                break
        else:
            self.fail(
                f"{EXEC_REL} section 6 must state, in one normative statement "
                f"naming {', '.join(ALWAYS_REQUIRED_SHARED_BASE_SLOTS)}, that "
                f"they are members of the mandatory base consumed by reference "
                f"from {TICKET_LANE_REL} section 3.1.1 and not declared here "
                f"(MF-1: the base must not be readable as five fields)")

        self.assertIn(
            (OWNED_COMPONENT_COUNT, SHARED_BASE_MEMBER_COUNT,
             MANDATORY_BASE_COUNT),
            additive_claims(self.section6),
            f"{EXEC_REL} section 6 must state the mandatory base as "
            f"5 + 3 = 8 (five owned components plus three always-required "
            f"shared P1-T01 slots); found additive claims="
            f"{sorted(additive_claims(self.section6))}")

    def test_na_path_composition_is_eight_plus_two_equals_ten(self):
        """(d) The N/A path adds exactly the two conditional slots → 10."""
        self.assertEqual(NA_PATH_COUNT, 10)
        self.assertEqual(
            set(ALWAYS_REQUIRED_SHARED_BASE_SLOTS)
            & set(CONDITIONAL_NA_SLOTS),
            set(),
            "the conditional N/A slots must not be counted in the "
            "always-required base composition")

        for para in paragraphs(self.section6):
            if not all(slot in para for slot in CONDITIONAL_NA_SLOTS):
                continue
            if "N/A" not in para:
                continue
            if (MANDATORY_BASE_COUNT, len(CONDITIONAL_NA_SLOTS),
                    NA_PATH_COUNT) in additive_claims(para):
                return
        self.fail(
            f"{EXEC_REL} section 6 must state, in one statement naming "
            f"{' and '.join(CONDITIONAL_NA_SLOTS)}, that the N/A path carries "
            f"8 + 2 = 10 slots (the {MANDATORY_BASE_COUNT}-field mandatory base "
            f"plus exactly two conditional slots)")

    # -- lifecycle rule ------------------------------------------------------

    def test_red_lifecycle_rule_is_stated(self):
        self.assertIn(
            "TICKET_AUTHORIZATION", self.section6,
            f"{EXEC_REL} section 6 does not state that RED runs only after "
            f"ticket authorization")
        self.assertIn(
            "before implementation", self.section6,
            f"{EXEC_REL} section 6 does not state that RED runs before "
            f"implementation")
        self.assertIn(
            "decomposition", self.section6,
            f"{EXEC_REL} section 6 does not state that RED is not executed at "
            f"decomposition time")

    # -- N/A two-slot rule --------------------------------------------------

    def test_na_requires_two_extra_slots_and_is_not_capped(self):
        for slot in ("REACHABILITY_APPLICABILITY_REASON",
                     "REACHABILITY_APPLICABILITY_ACCEPTANCE_REF"):
            with self.subTest(slot=slot):
                self.assertIn(
                    slot, self.section6,
                    f"{EXEC_REL} section 6 does not state that N/A requires the "
                    f"slot {slot}")
        self.assertIn(
            "NOT capped", self.section6,
            f"{EXEC_REL} section 6 does not state the record is not capped at "
            f"eight fields")
        self.assertIn(
            "N/A", self.section6,
            f"{EXEC_REL} section 6 does not state the N/A path carries MORE than "
            f"the eight base fields")

    # -- no implicit aliasing ------------------------------------------------

    def test_no_implicit_alias_statement_present(self):
        self.assertIn(
            "FORBIDDEN", self.section6,
            f"{EXEC_REL} section 6 does not state the forbidden implicit aliases")
        for left, right in FORBIDDEN_ALIASES:
            with self.subTest(pair=f"{left}={right}"):
                self.assertIn(
                    left, self.section6,
                    f"{EXEC_REL} section 6 does not forbid the alias "
                    f"{left}={right}")

    # -- single declaration point (CE-30) ------------------------------------

    def test_owned_fields_not_declared_in_ticket_lane(self):
        for name in OWNED_FIELDS:
            with self.subTest(field=name):
                self.assertFalse(
                    is_field_entry_declared(self.ticket_lane_text, name),
                    f"{TICKET_LANE_REL} must NOT declare the REQ-W1-02-owned "
                    f"field {name}; its single declaration point is "
                    f"{EXEC_REL} section 6")

    def test_frozen_slots_referenced_not_declared_in_execution_stage(self):
        for slot in FROZEN_SLOTS:
            with self.subTest(slot=slot):
                self.assertIn(
                    slot, self.section6,
                    f"{EXEC_REL} section 6 must reference the P1-T01-frozen "
                    f"slot {slot}")
                self.assertFalse(
                    is_field_entry_declared(self.exec_text, slot),
                    f"{EXEC_REL} must REFERENCE (not re-declare) the "
                    f"P1-T01-frozen slot {slot} (CE-30 single declaration point)")


if __name__ == "__main__":
    unittest.main()
