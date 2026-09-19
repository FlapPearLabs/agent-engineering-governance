"""Counterexample-driven regression checks for the P1-T03 integration closure
evidence requirement in `references/git-ci-integration.md` sections 4/5.

SUPPORT surface (RULES.md R6), NOT an authority surface. This module declares no
seam field and no requirement of its own: it re-reads the canonical reference and
fails when the integration closure condition loses its reachability evidence, its
disconnected-entrypoint prohibition, its dynamic-path non-rejection rule, its
test-caller separation, or its not-complete outcome.

BINDING (references/ticket-lane.md section 4, counterexample-first)
    The six canonical observation slots are consumed BY REFERENCE from
    REQ-W1-01. Their single normative declaration point is
    `references/ticket-lane.md` section 3.1.2 (partition (2)); the names below
    are ASSERTION INPUTS (a lock read back from that producer), never a second
    declaration point. `references/git-ci-integration.md` must mention them as
    references only and must never re-declare them as field-list entries.

    Every behavioural probe below is derived from the DOCUMENT TEXT: the
    normative rules are located by marker groups over the non-blank lines of
    sections 4/5, so mutating (or deleting) a normative sentence turns the
    corresponding probe RED instead of passing CI silently. The anti-vacuity
    self-checks at the bottom perform exactly that mutation in memory and
    require the probe to flip.

Counterexamples exercised here (parent spec section 9): CE-04 (a disconnected
production entrypoint with green internal tests must not close), CE-05 (a legal
dynamic registration / callback path must not be rejected by a static call
count), CE-14 (a runtime wiring ticket abusing `N/A` must be rejected). CE-30
holds by construction: nothing here re-declares the requirement fields.

RED condition before P1-T03 lands: sections 4/5 carry no reachability closure
evidence at all, so a disconnected production entrypoint can still be closed
and a legal dynamic path cannot be told apart from a missing caller. Every
assertion below FAILS.

Owner adjudication honoured: the canonical slots are SIX. `TEST_ONLY_CALLERS`
is NOT a seventh canonical slot and must never appear as a field-list entry.

Stdlib only. Run with:
    python3 -m unittest scripts.tests.test_p1_t03_git_ci_integration_closure_evidence
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GIT_CI_REL = "references/git-ci-integration.md"
TICKET_LANE_REL = "references/ticket-lane.md"
GIT_CI = ROOT / GIT_CI_REL
TICKET_LANE = ROOT / TICKET_LANE_REL

# The SIX canonical observation slots (REQ-W1-01 partition (2)). Assertion
# inputs read back from `references/ticket-lane.md` section 3.1.2.
CANONICAL_OBSERVATION_SLOTS = (
    "REAL_ENTRYPOINT",
    "PRODUCTION_CALL_CHAIN",
    "OBSERVED_PRODUCTION_EFFECT",
    "PRODUCTION_CALLERS",
    "RUNTIME_REACHABLE",
    "EVIDENCE_REF",
)

# Diagnostic-only derived name. NOT a canonical slot; never a field entry.
TEST_ONLY_CALLERS = "TEST_ONLY_CALLERS"

# The producer section that holds the single declaration point.
PRODUCER_SECTION_HEADING = "#### 3.1.2"

SECTION_RE = re.compile(r"^##\s+(\d+)\.", re.M)
FENCE_RE = re.compile(r"^\s*```")
# A field-list ENTRY line: bare field name(s) joined by "/", optional "#" note.
FIELD_ENTRY_RE = re.compile(
    r"^\s*[A-Z][A-Z0-9_]*(?:\s*/\s*[A-Z][A-Z0-9_]*)*\s*(?:#.*)?$")

# --------------------------------------------------------------------------
# document helpers
# --------------------------------------------------------------------------

def section_body(text: str, number: int) -> str:
    """Body of `## <number>. ...` up to the next level-2 heading."""
    headings = list(SECTION_RE.finditer(text))
    for index, match in enumerate(headings):
        if int(match.group(1)) != number:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        return text[match.end():end]
    return ""


def statements(section_text: str):
    """Non-blank lines that are not fence markers.

    A normative rule is located on ONE line so that a probe cannot be
    satisfied by markers scattered across unrelated statements.
    """
    return [line.strip() for line in section_text.splitlines()
            if line.strip() and not FENCE_RE.match(line)]


def probe(section_text: str, groups) -> bool:
    """True when ONE statement carries every marker group (any alternative)."""
    for line in statements(section_text):
        if all(any(alt in line for alt in group) for group in groups):
            return True
    return False


def fenced_blocks(text: str):
    """Fenced-block bodies (list of lines, fences stripped)."""
    blocks, buf, inside = [], [], False
    for line in text.splitlines():
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


def declared_field_entries(text: str):
    """Every field name DECLARED as a field-list entry in a fenced block."""
    names = set()
    for block in fenced_blocks(text):
        for line in block:
            names |= field_entry_names(line)
    return names


def is_field_entry_declared(text: str, name: str) -> bool:
    return name in declared_field_entries(text)


def block_after_label(lines, label: str):
    """Lines of the first fenced block following the first line carrying label."""
    for index, line in enumerate(lines):
        if label not in line:
            continue
        opener = index + 1
        while opener < len(lines) and not FENCE_RE.match(lines[opener]):
            opener += 1
        if opener >= len(lines):
            return []
        body, cursor = [], opener + 1
        while cursor < len(lines) and not FENCE_RE.match(lines[cursor]):
            body.append(lines[cursor])
            cursor += 1
        return body
    return []


# --------------------------------------------------------------------------
# the closure condition, decomposed into marker groups
# --------------------------------------------------------------------------

MODULE_TEST_MARKERS = ("内部测试", "模块级测试", "模块内测试",
                       "module-level test", "internal test")
CANNOT_CLOSE_MARKERS = ("不得关闭", "不能关闭", "cannot close",
                        "must not close")

# CE-04: a disconnected production entrypoint must not close, even with the
# new behaviour's internal tests green.
DISCONNECTED_GROUPS = (
    ("生产入口断开", "断开的生产入口", "ENTRYPOINT_DISCONNECTED",
     "disconnected production entrypoint"),
    MODULE_TEST_MARKERS,
    CANNOT_CLOSE_MARKERS,
)

# CE-04 root rule: closure needs the real-entrypoint-to-effect chain.
CLOSURE_REQUIRES_GROUPS = (
    ("REAL_ENTRYPOINT",),
    ("PRODUCTION_CALL_CHAIN",),
    ("OBSERVED_PRODUCTION_EFFECT",),
    ("不得仅凭", "不得仅以", "不能仅凭", "not on its own", "alone is not"),
    MODULE_TEST_MARKERS,
)

# CE-05: a legal dynamic registration / plugin / callback path must not be
# rejected because a static direct-call count is zero.
DYNAMIC_PATH_GROUPS = (
    ("动态注册", "dynamic registration"),
    ("插件", "plugin"),
    ("回调", "callback"),
    ("不得被拒绝", "不得拒绝", "must not be rejected", "not rejected"),
    ("静态", "static", "textual"),
    ("计数", "count"),
    ("grep",),
)

# The observation-only separation: a test caller is never a production caller.
TEST_CALLER_GROUPS = (
    ("测试调用者", "test caller"),
    ("生产调用者", "production caller"),
    ("永不", "never"),
)

# CE-14 / AC-23: no legal production caller path is not-complete, never green.
NO_CALLER_PATH_GROUPS = (
    ("无合法生产调用路径", "不存在合法生产调用者路径",
     "no legal production caller path"),
    ("INTEGRATION_COMPLETE = FALSE",),
)

# AC-20: an N/A ticket does not close through this evidence path.
NA_PATH_GROUPS = (
    ("N/A",),
    ("不通过本条证据路径关闭", "不经过本条证据路径关闭",
     "does not close through this evidence path"),
    ("REACHABILITY_APPLICABILITY_REASON",),
    ("REACHABILITY_APPLICABILITY_ACCEPTANCE_REF",),
)

PROBES = {
    "disconnected_entrypoint_cannot_close": DISCONNECTED_GROUPS,
    "closure_requires_real_entrypoint_to_effect": CLOSURE_REQUIRES_GROUPS,
    "dynamic_path_not_rejected_by_static_count": DYNAMIC_PATH_GROUPS,
    "test_caller_is_not_a_production_caller": TEST_CALLER_GROUPS,
    "no_production_caller_path_is_not_complete": NO_CALLER_PATH_GROUPS,
    "na_ticket_does_not_close_through_this_path": NA_PATH_GROUPS,
}

# Anti-vacuity mutations: each removes one required marker group from the SAME
# live text and must flip its probe to False.
PROBE_MUTATIONS = {
    "disconnected_entrypoint_cannot_close": (
        "也不得关闭该集成票", "，可以关闭该集成票"),
    "closure_requires_real_entrypoint_to_effect": (
        "REAL_ENTRYPOINT", "THE_ENTRYPOINT"),
    "dynamic_path_not_rejected_by_static_count": (
        "不得被拒绝", "必须被拒绝"),
    "test_caller_is_not_a_production_caller": ("永不", "可能"),
    "no_production_caller_path_is_not_complete": (
        "INTEGRATION_COMPLETE = FALSE", "INTEGRATION_COMPLETE = TRUE"),
    "na_ticket_does_not_close_through_this_path": (
        "不通过本条证据路径关闭", "通过本条证据路径关闭"),
}


class IntegrationClosureEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.text = GIT_CI.read_text(encoding="utf-8")
        self.section4 = section_body(self.text, 4)
        self.section5 = section_body(self.text, 5)
        self.closure_text = self.section4 + "\n" + self.section5

        self.ticket_lane_text = TICKET_LANE.read_text(encoding="utf-8")
        self.producer_slots = {
            name
            for line in block_after_label(self.ticket_lane_text.splitlines(),
                                          PRODUCER_SECTION_HEADING)
            for name in field_entry_names(line)
        }

    # -- the six slots: present here, declared only in the producer ----------

    def test_sections_four_or_five_consume_every_canonical_observation_slot(self):
        for slot in CANONICAL_OBSERVATION_SLOTS:
            with self.subTest(slot=slot):
                self.assertIn(
                    slot, self.closure_text,
                    f"{GIT_CI_REL} sections 4/5 do not consume the canonical "
                    f"observation slot {slot}")

    def test_the_producer_declares_exactly_the_six_canonical_slots(self):
        """The declaration point this file references must still be the six."""
        self.assertEqual(
            self.producer_slots, set(CANONICAL_OBSERVATION_SLOTS),
            f"{TICKET_LANE_REL} {PRODUCER_SECTION_HEADING} must declare exactly "
            f"the six canonical observation slots; declared="
            f"{sorted(self.producer_slots)}")

    def test_this_file_never_re_declares_a_slot_as_a_field_entry(self):
        """CE-30 discipline: the consumer only references, never declares."""
        declared = declared_field_entries(self.text)
        offending = sorted(declared & set(CANONICAL_OBSERVATION_SLOTS))
        self.assertEqual(
            offending, [],
            f"{GIT_CI_REL} must consume the canonical slots BY REFERENCE from "
            f"{TICKET_LANE_REL} section 3.1.2, not re-declare them as field "
            f"entries; offending={offending}")

    def test_this_file_states_the_single_declaration_point_by_reference(self):
        self.assertIn(
            "ticket-lane.md", self.closure_text,
            f"{GIT_CI_REL} sections 4/5 must cite {TICKET_LANE_REL} as the "
            f"single declaration point of the canonical observation slots")
        self.assertIn(
            "3.1.2", self.closure_text,
            f"{GIT_CI_REL} sections 4/5 must cite section 3.1.2 as the single "
            f"declaration point of the canonical observation slots")

    # -- TEST_ONLY_CALLERS is diagnostic only, never a field entry ----------

    def test_test_only_callers_is_never_a_field_list_entry(self):
        self.assertNotIn(
            TEST_ONLY_CALLERS, CANONICAL_OBSERVATION_SLOTS,
            f"{TEST_ONLY_CALLERS} is not one of the six canonical observation "
            f"slots (owner adjudication)")
        self.assertFalse(
            is_field_entry_declared(self.text, TEST_ONLY_CALLERS),
            f"{GIT_CI_REL} must never write {TEST_ONLY_CALLERS} into a field "
            f"list; it is derived / diagnostic evidence only")

    def test_a_mention_of_test_only_callers_is_flagged_as_diagnostic(self):
        mentions = [line for line in statements(self.closure_text)
                    if TEST_ONLY_CALLERS in line]
        for line in mentions:
            with self.subTest(line=line):
                self.assertTrue(
                    any(marker in line for marker in
                        ("派生", "诊断", "derived", "diagnostic")),
                    f"{GIT_CI_REL}: a mention of {TEST_ONLY_CALLERS} must be "
                    f"marked as derived / diagnostic evidence, never as a "
                    f"canonical slot")

    # -- the normative closure conditions (CE-04 / CE-05 / CE-14) -----------

    def test_section_four_binds_wiring_tickets_into_the_integration_scope(self):
        self.assertTrue(
            probe(self.section4, (
                ("wiring", "entrypoint", "入口"),
                MODULE_TEST_MARKERS,
                ("不构成", "不足", "不是", "仅", "insufficient", "not"),
            )),
            f"{GIT_CI_REL} section 4 must state that the semantic scope of a "
            f"wiring / entrypoint ticket includes the entrypoint-to-effect "
            f"chain, so module-level test evidence alone is not scope closure")

    def test_disconnected_entrypoint_cannot_close(self):
        self.assertTrue(
            probe(self.closure_text, DISCONNECTED_GROUPS),
            f"{GIT_CI_REL} sections 4/5 do not state CE-04: a disconnected "
            f"production entrypoint stays open even though the new "
            f"behaviour's internal tests are green")

    def test_closure_requires_a_real_entrypoint_to_production_effect_chain(self):
        self.assertTrue(
            probe(self.closure_text, CLOSURE_REQUIRES_GROUPS),
            f"{GIT_CI_REL} sections 4/5 do not state that closure requires a "
            f"real entrypoint -> changed seam -> observed production effect "
            f"chain, or an explicit not-complete declaration")

    def test_legal_dynamic_path_is_not_rejected_by_a_static_call_count(self):
        self.assertTrue(
            probe(self.closure_text, DYNAMIC_PATH_GROUPS),
            f"{GIT_CI_REL} sections 4/5 do not state CE-05: a legitimate "
            f"dynamic registration / plugin / callback path must not be "
            f"rejected by a textual count of direct calls")

    def test_a_test_caller_is_never_a_production_caller(self):
        self.assertTrue(
            probe(self.closure_text, TEST_CALLER_GROUPS),
            f"{GIT_CI_REL} sections 4/5 do not state that a test caller is "
            f"never a production caller and never satisfies production "
            f"reachability")

    def test_no_legal_production_caller_path_is_never_complete(self):
        self.assertTrue(
            probe(self.closure_text, NO_CALLER_PATH_GROUPS),
            f"{GIT_CI_REL} sections 4/5 do not state AC-23: with required "
            f"reachability and no legal production caller path, "
            f"INTEGRATION_COMPLETE = FALSE and the ticket is never green")

    def test_an_na_ticket_does_not_close_through_this_evidence_path(self):
        self.assertTrue(
            probe(self.closure_text, NA_PATH_GROUPS),
            f"{GIT_CI_REL} sections 4/5 do not state CE-14 / AC-20: an N/A "
            f"ticket does not close through this evidence path and still owes "
            f"the two P1-T01-owned applicability slots")

    # -- anti-vacuity: the probes read the document text --------------------

    def test_every_probe_holds_for_the_live_document(self):
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                self.assertTrue(
                    probe(self.closure_text, groups),
                    f"{GIT_CI_REL}: probe {name} is not satisfied by the live "
                    f"document")

    def test_every_probe_flips_red_under_a_targeted_mutation(self):
        """A mutated normative sentence must turn its probe RED (not vacuous)."""
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                old, new = PROBE_MUTATIONS[name]
                self.assertTrue(
                    probe(self.closure_text, groups),
                    f"{GIT_CI_REL}: probe {name} must hold on the live text "
                    f"before the mutation is attempted")
                self.assertIn(
                    old, self.closure_text,
                    f"{GIT_CI_REL}: probe {name} is not anchored to document "
                    f"text; the expected marker {old!r} is absent")
                mutated = self.closure_text.replace(old, new)
                self.assertNotEqual(mutated, self.closure_text)
                self.assertFalse(
                    probe(mutated, groups),
                    f"{GIT_CI_REL}: probe {name} is VACUOUS - mutating "
                    f"{old!r} -> {new!r} did not turn it RED")

    def test_probe_helper_requires_all_marker_groups_on_one_statement(self):
        """A marker split across two statements must NOT satisfy a probe."""
        groups = (("ALPHA",), ("BETA",))
        self.assertTrue(probe("ALPHA and BETA", groups))
        self.assertFalse(
            probe("ALPHA\nBETA", groups),
            "the probe helper must not be satisfiable by markers scattered "
            "across unrelated statements")

    def test_field_entry_parser_recognises_a_declaration_and_not_a_reference(self):
        self.assertEqual(
            field_entry_names("REAL_ENTRYPOINT / PRODUCTION_CALL_CHAIN"),
            {"REAL_ENTRYPOINT", "PRODUCTION_CALL_CHAIN"})
        self.assertEqual(
            field_entry_names("REAL_ENTRYPOINT -> 真实入口"),
            set(),
            "a pairing / annotated line is a REFERENCE, not a declaration")
        self.assertEqual(
            field_entry_names("DISCONNECTED  生产入口断开时不得关闭"),
            set(),
            "a labelled prose rule is a REFERENCE, not a declaration")


if __name__ == "__main__":
    unittest.main()
