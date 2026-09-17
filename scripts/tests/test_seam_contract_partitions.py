"""Counterexample-driven regression checks for the seam contract block in
`references/ticket-lane.md` section 3.

SUPPORT surface (RULES R6), NOT an authority surface. This module declares no
seam field and no requirement: it re-reads the canonical reference and fails
when the contract loses its two labelled partitions, breaks a frozen field
name, collides a design/authority name with a closure/observation name, or
loses its single-declaration-point and fail-closed applicability rules.

The field-name tuples below are ASSERTION INPUTS (a lock on the canonical
file), never a second declaration point. The one normative declaration point of
`EXPECTED_PRODUCTION_EFFECT` is partition (1) of
`references/ticket-lane.md` section 3; see
`test_repository_declares_expected_production_effect_exactly_once`.

Counterexamples exercised here (parent spec section 9): CE-01, CE-02, CE-03,
CE-13, CE-14, CE-29, CE-30.
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TICKET_LANE_REL = "references/ticket-lane.md"
TICKET_LANE = ROOT / TICKET_LANE_REL

# Frozen partition labels (the two explicitly labelled partitions of section 3).
PARTITION_1_LABEL = "(1) DESIGN / AUTHORITY REQUIREMENTS"
PARTITION_2_LABEL = "(2) CLOSURE / OBSERVATION EVIDENCE"

# Frozen seam field names. Byte-exact; never rename, never add synonyms.
EFFECT_FIELD = "EXPECTED_PRODUCTION_EFFECT"

PARTITION_1_FIELDS = (
    "SEAM_ID", "AUTHORITY_REF", "CONTRACT_VERSION", "PRODUCER", "CONSUMER",
    "SEMANTIC_OWNER", "IDENTITY_OWNER", "PERSISTENCE_OWNER", "RETRY_OWNER",
    "ERROR_OWNER",
    "INPUT_CONTRACT", "OUTPUT_CONTRACT",
    "SYNC_OR_ASYNC", "AWAIT_REQUIREMENT", "LIFECYCLE_REQUIREMENT",
    "LEGAL_STATES", "ILLEGAL_STATES", "FAIL_OPEN_OR_FAIL_CLOSED",
    "MUST_FIELDS", "MUST_NOT_FIELDS",
    "EXPECTED_PRODUCTION_CALLER", "TEST_CALLER",
    "EXPECTED_PRODUCTION_EFFECT",
    "REAL_SHAPE_FIXTURE_OR_ADAPTER", "SEAM_COUNTEREXAMPLES",
    "REACHABILITY_APPLICABILITY", "REACHABILITY_APPLICABILITY_REASON",
    "REACHABILITY_APPLICABILITY_ACCEPTANCE_REF", "REACHABILITY_REQUIREMENT",
    "REACHABILITY_PROOF_OWNER", "RED_EXECUTION_OWNER",
)

PARTITION_2_FIELDS = (
    "REAL_ENTRYPOINT", "PRODUCTION_CALL_CHAIN", "OBSERVED_PRODUCTION_EFFECT",
    "PRODUCTION_CALLERS", "RUNTIME_REACHABLE", "EVIDENCE_REF",
)

# Frozen pairings: design/authority name -> closure/observation name.
FROZEN_PAIRINGS = (
    ("EXPECTED_PRODUCTION_EFFECT", "OBSERVED_PRODUCTION_EFFECT"),
    ("EXPECTED_PRODUCTION_CALLER", "PRODUCTION_CALLERS"),
    ("REACHABILITY_REQUIREMENT", "RUNTIME_REACHABLE"),
)

# Pre-existing section 3 fields that must survive the extension.
LEGACY_SECTION_THREE_FIELDS = (
    "INPUTS", "OUTPUTS", "PRECONDITIONS", "POSTCONDITIONS",
    "HARD_INVARIANTS", "VALID_SUCCESS_CASES", "FAIL_CLOSED_CASES",
    "ALLOWED_FALLBACKS", "FORBIDDEN_FALLBACKS",
    "IDENTITY_DEPENDENCIES", "PERSISTENCE_DEPENDENCIES",
    "OWNERSHIP", "OUT_OF_SCOPE",
)

SECTION_THREE_RE = re.compile(r"^##\s+3\.", re.M)
NEXT_SECTION_RE = re.compile(r"^##\s", re.M)
FENCE_RE = re.compile(r"^\s*```")
UPPER_TOKEN_RE = re.compile(r"[A-Z][A-Z0-9_]*")
# A field-list ENTRY line: bare field name(s) joined by "/", optional "#" note.
FIELD_ENTRY_RE = re.compile(
    r"^\s*[A-Z][A-Z0-9_]*(?:\s*/\s*[A-Z][A-Z0-9_]*)*\s*(?:#.*)?$")
TEXT_SUFFIXES = (".md", ".py", ".json", ".yml", ".yaml", ".txt", ".js", ".ts")

REQUIREMENT_MARKERS = ("EXPECTED_",)
OBSERVATION_MARKERS = ("OBSERVED_",)


# --------------------------------------------------------------------------
# document helpers
# --------------------------------------------------------------------------

def section_three(text: str) -> str:
    """Return the body of `## 3. ...` up to the next level-2 heading."""
    match = SECTION_THREE_RE.search(text)
    if match is None:
        return ""
    rest = text[match.end():]
    nxt = NEXT_SECTION_RE.search(rest)
    return rest[: nxt.start()] if nxt else rest


def fenced_blocks(lines):
    """Return the list of fenced-block bodies (list of lines, fences stripped)."""
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


def block_after_label(lines, label: str) -> str:
    """Return the first fenced block following the first line carrying `label`."""
    for index, line in enumerate(lines):
        if label not in line:
            continue
        opener = index + 1
        while opener < len(lines) and not FENCE_RE.match(lines[opener]):
            opener += 1
        body, cursor = [], opener + 1
        while cursor < len(lines) and not FENCE_RE.match(lines[cursor]):
            body.append(lines[cursor])
            cursor += 1
        return "\n".join(body)
    return ""


def field_entry_names(line: str):
    """Field names declared by a field-list entry line; empty when not one."""
    if not FIELD_ENTRY_RE.match(line):
        return set()
    body = line.split("#", 1)[0]
    return {token.strip() for token in body.split("/") if token.strip()}


def declaration_points(root: Path, field: str = EFFECT_FIELD):
    """Repo-wide normative declaration points of `field`.

    DECLARATION = the field appears as a field-list ENTRY inside a fenced block
    (the shape of a normative declaration). Everything else -- prose, a
    `A -> B` pairing row, a test assertion, a consumer document -- is a
    REFERENCE.
    """
    points = []
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for block_index, block in enumerate(fenced_blocks(lines)):
            for line in block:
                if field in field_entry_names(line):
                    points.append(
                        (str(path.relative_to(root)), block_index, line.strip()))
    return points


def count_occurrences(root: Path, needle: str) -> int:
    total = 0
    for path in sorted(root.rglob("*")):
        if path.is_dir() or ".git" in path.parts:
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        total += path.read_text(
            encoding="utf-8", errors="replace").count(needle)
    return total


def pairing_rows(lines):
    """Return `(left_names, right_names)` for every `A ... -> ... B` row."""
    rows = []
    for line in lines:
        if "->" not in line:
            continue
        left, _, right = line.partition("->")
        rows.append((set(UPPER_TOKEN_RE.findall(left)),
                     set(UPPER_TOKEN_RE.findall(right))))
    return rows


# --------------------------------------------------------------------------
# executable encodings of the documented rules (fixtures live in the tests)
# --------------------------------------------------------------------------

def canonical_stem(name: str) -> str:
    """Strip a requirement/observation marker so near-names become comparable."""
    for marker in REQUIREMENT_MARKERS + OBSERVATION_MARKERS:
        if name.startswith(marker):
            return name[len(marker):]
    return name


def ambiguous_pairs(design, observation, frozen):
    """Design/observation name pairs a reader cannot tell apart (CE-29)."""
    problems = []
    for left in design:
        for right in observation:
            if left == right:
                problems.append((left, right, "identical name"))
            elif (canonical_stem(left) == canonical_stem(right)
                  and (left, right) not in frozen):
                problems.append(
                    (left, right, "near-identical stem, not cured by a frozen pairing"))
    return problems


def filled(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


def resolve_applicability(record):
    """Executable encoding of the documented applicability judgement rule.

    Fail-closed: a missing/empty reason or acceptance reference, or any value
    outside the frozen domain, is processed as REQUIRED. A worker can never
    self-grant N/A, because N/A without a reviewer/integrator acceptance
    reference fails closed.
    """
    value = record.get("REACHABILITY_APPLICABILITY")
    if value == "N/A":
        if (filled(record.get("REACHABILITY_APPLICABILITY_REASON"))
                and filled(record.get("REACHABILITY_APPLICABILITY_ACCEPTANCE_REF"))):
            return "N/A"
        return "REQUIRED"
    return "REQUIRED"


def state_verdict(record, observed: str) -> str:
    """Reject an illegal state; accept a legal one; fail closed on unclassified."""
    if observed in (record.get("ILLEGAL_STATES") or ()):
        return "REJECT"
    if observed in (record.get("LEGAL_STATES") or ()):
        return "ACCEPT"
    return "REJECT"


def timing_signature(record):
    return (
        record.get("SYNC_OR_ASYNC"),
        record.get("AWAIT_REQUIREMENT"),
        record.get("LIFECYCLE_REQUIREMENT"),
    )


def named_failure_states(record, outcomes):
    """Which of `outcomes` the seam can name individually as an illegal state."""
    declared = set(record.get("ILLEGAL_STATES") or ())
    return {outcome: (outcome in declared) for outcome in outcomes}


# --------------------------------------------------------------------------
# tests
# --------------------------------------------------------------------------

class SeamContractPartitionTests(unittest.TestCase):
    def setUp(self):
        self.text = TICKET_LANE.read_text(encoding="utf-8")
        self.lines = self.text.splitlines()
        self.section = section_three(self.text)
        self.partition_1 = block_after_label(self.lines, PARTITION_1_LABEL)
        self.partition_2 = block_after_label(self.lines, PARTITION_2_LABEL)

    # -- structure ---------------------------------------------------------

    def test_canonical_owner_declaration_retained(self):
        self.assertIn(
            "Canonical owner", self.text,
            f"{TICKET_LANE_REL}: the literal 'Canonical owner' declaration was removed")

    def test_legacy_section_three_fields_retained(self):
        for name in LEGACY_SECTION_THREE_FIELDS:
            with self.subTest(field=name):
                self.assertIn(
                    name, self.section,
                    f"{TICKET_LANE_REL} section 3 lost the pre-existing field {name}")

    def test_low_ticket_minimum_rule_retained(self):
        self.assertIn("LOW", self.section,
                      f"{TICKET_LANE_REL} section 3 lost the LOW-ticket minimum rule")

    def test_section_three_carries_two_labelled_partitions(self):
        self.assertIn(
            PARTITION_1_LABEL, self.text,
            f"{TICKET_LANE_REL} section 3 is missing partition {PARTITION_1_LABEL!r}")
        self.assertIn(
            PARTITION_2_LABEL, self.text,
            f"{TICKET_LANE_REL} section 3 is missing partition {PARTITION_2_LABEL!r}")
        self.assertTrue(
            self.partition_1.strip(),
            f"{TICKET_LANE_REL} section 3: partition (1) carries no field list")
        self.assertTrue(
            self.partition_2.strip(),
            f"{TICKET_LANE_REL} section 3: partition (2) carries no field list")

    def test_partition_one_declares_every_frozen_authority_field(self):
        for name in PARTITION_1_FIELDS:
            with self.subTest(field=name):
                self.assertIn(
                    name, self.partition_1,
                    f"{TICKET_LANE_REL} section 3 partition (1) is missing the "
                    f"frozen design/authority field {name}")

    def test_partition_two_declares_every_frozen_closure_field(self):
        for name in PARTITION_2_FIELDS:
            with self.subTest(field=name):
                self.assertIn(
                    name, self.partition_2,
                    f"{TICKET_LANE_REL} section 3 partition (2) is missing the "
                    f"frozen closure/observation field {name}")

    def test_partition_one_is_frozen_before_ticketing(self):
        self.assertIn(
            "PARTITION (1) IS FROZEN BEFORE TICKETING", self.section,
            "section 3 does not state that partition (1) is frozen before ticketing")

    def test_partition_two_only_fills_declared_slots(self):
        self.assertIn(
            "PARTITION (2) ONLY FILLS THE SLOTS DECLARED BY (1)", self.section,
            "section 3 does not state that partition (2) only fills declared slots")

    def test_closure_evidence_can_never_rewrite_a_requirement(self):
        self.assertIn(
            "CLOSURE_EVIDENCE_CAN_NEVER_REWRITE_A_REQUIREMENT", self.section,
            "section 3 does not state that closure evidence cannot rewrite a requirement")

    def test_partition_two_shares_no_name_with_partition_one(self):
        shared = sorted(set(PARTITION_1_FIELDS) & set(PARTITION_2_FIELDS))
        self.assertEqual(
            shared, [],
            f"design/authority and closure/observation partitions share names: {shared}")

    # -- CE-29 -------------------------------------------------------------

    def test_frozen_pairing_rows_are_rendered(self):
        rows = pairing_rows(self.lines)
        for left, right in FROZEN_PAIRINGS:
            with self.subTest(pairing=f"{left} -> {right}"):
                self.assertNotEqual(
                    left, right,
                    f"frozen pairing collapses into one name: {left}")
                self.assertTrue(
                    any(a == {left} and right in b for a, b in rows),
                    f"the frozen pairing row {left} -> {right} is not rendered "
                    f"in {TICKET_LANE_REL}")

    def test_no_ambiguous_design_observation_pair(self):
        self.assertEqual(
            ambiguous_pairs(PARTITION_1_FIELDS, PARTITION_2_FIELDS, FROZEN_PAIRINGS),
            [],
            "an ambiguous design/observation field pair exists")

    def test_ambiguity_detector_rejects_a_synthetic_collision(self):
        self.assertTrue(
            ambiguous_pairs(("WIDGET_STATE",), ("WIDGET_STATE",), FROZEN_PAIRINGS),
            "detector failed to flag an identical design/observation name")
        self.assertTrue(
            ambiguous_pairs(("EXPECTED_WIDGET_STATE",), ("OBSERVED_WIDGET_STATE",),
                            FROZEN_PAIRINGS),
            "detector failed to flag an unfrozen near-name pair")
        self.assertEqual(
            ambiguous_pairs(("EXPECTED_PRODUCTION_EFFECT",),
                            ("OBSERVED_PRODUCTION_EFFECT",), FROZEN_PAIRINGS),
            [],
            "the frozen pairing must be accepted")

    # -- CE-30 -------------------------------------------------------------

    def test_repository_declares_expected_production_effect_exactly_once(self):
        points = declaration_points(ROOT)
        self.assertEqual(
            len(points), 1,
            f"{EFFECT_FIELD} must have exactly one normative declaration point; "
            f"found {len(points)}: {points}")
        rel, _block_index, entry = points[0]
        self.assertEqual(
            rel, TICKET_LANE_REL,
            f"the single declaration point must live in {TICKET_LANE_REL}, not {rel}")
        self.assertTrue(
            entry.startswith(EFFECT_FIELD),
            f"unexpected declaration entry: {entry!r}")
        occurrences = count_occurrences(ROOT, EFFECT_FIELD)
        self.assertGreater(
            occurrences, len(points),
            f"expected reference occurrences of {EFFECT_FIELD} besides the single "
            f"declaration point; total={occurrences}")

    def test_single_declaration_rule_is_stated_in_section_three(self):
        self.assertIn(
            "HAS EXACTLY ONE NORMATIVE DECLARATION POINT", self.section,
            "section 3 does not state the single normative declaration point rule")
        self.assertIn(
            "DECLARATION =", self.section,
            "section 3 does not define what a declaration is")
        self.assertIn(
            "REFERENCE   =", self.section,
            "section 3 does not define what a reference is")

    def test_duplicate_declaration_detector_flags_a_second_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "references").mkdir(parents=True)
            canonical = root / TICKET_LANE_REL
            canonical.write_text(
                "# lane\n\n```\nSEAM_ID / AUTHORITY_REF\n"
                f"{EFFECT_FIELD}            # requirement\n```\n",
                encoding="utf-8")
            self.assertEqual(len(declaration_points(root)), 1)

            consumer = root / "references/execution-stage.md"
            consumer.write_text(
                "# stage\n\n```\nREAL_ENTRYPOINT\n"
                f"{EFFECT_FIELD}            # duplicated declaration\n```\n",
                encoding="utf-8")
            self.assertEqual(
                len(declaration_points(root)), 2,
                "detector failed to flag a second normative declaration point")

            consumer.write_text(
                "# stage\n\n"
                f"See {EFFECT_FIELD} for the expectation.\n\n"
                "```\n"
                f"{EFFECT_FIELD}          ->  OBSERVED_PRODUCTION_EFFECT\n"
                "```\n",
                encoding="utf-8")
            self.assertEqual(
                len(declaration_points(root)), 1,
                "a prose mention or a pairing row is a reference, not a declaration")

    # -- CE-01 / CE-02 / CE-03 --------------------------------------------

    def test_async_production_shape_is_expressible(self):
        for name in ("SYNC_OR_ASYNC", "AWAIT_REQUIREMENT", "LIFECYCLE_REQUIREMENT"):
            with self.subTest(field=name):
                self.assertIn(
                    name, self.partition_1,
                    f"partition (1) cannot express the production timing field {name}")
        ideal_sync_mock = {
            "SYNC_OR_ASYNC": "SYNC",
            "AWAIT_REQUIREMENT": "NONE",
            "LIFECYCLE_REQUIREMENT": "NONE",
        }
        real_async_adapter = {
            "SYNC_OR_ASYNC": "ASYNC",
            "AWAIT_REQUIREMENT": "AWAIT_SETTLEMENT_BEFORE_READ",
            "LIFECYCLE_REQUIREMENT": "PRODUCER_MUST_NOT_COMPLETE_BEFORE_SETTLEMENT",
        }
        self.assertNotEqual(
            timing_signature(ideal_sync_mock), timing_signature(real_async_adapter),
            "the contract must distinguish an ideal sync mock from a real async adapter")

    def test_premature_completion_before_delayed_resolve_is_expressible(self):
        for name in ("LEGAL_STATES", "ILLEGAL_STATES"):
            with self.subTest(field=name):
                self.assertIn(
                    name, self.partition_1,
                    f"partition (1) cannot express the seam state field {name}")
        # Fixture state names are test-local data, not a canonical enum.
        seam = {
            "LEGAL_STATES": ("PENDING", "RESOLVED"),
            "ILLEGAL_STATES": ("COMPLETED_BEFORE_DELAYED_RESOLVE",),
        }
        self.assertEqual(
            state_verdict(seam, "COMPLETED_BEFORE_DELAYED_RESOLVE"), "REJECT",
            "a producer completing before a delayed resolve must be rejectable")
        self.assertEqual(
            state_verdict(seam, "RESOLVED"), "ACCEPT",
            "the post-resolution state must stay legal")
        self.assertEqual(
            state_verdict(seam, "UNCLASSIFIED"), "REJECT",
            "an unclassified state must fail closed")

    def test_producer_reject_and_resolved_but_malformed_stay_distinct(self):
        for name in ("ERROR_OWNER", "FAIL_OPEN_OR_FAIL_CLOSED"):
            with self.subTest(field=name):
                self.assertIn(
                    name, self.partition_1,
                    f"partition (1) cannot express the error semantics field {name}")
        self.assertIn(
            "FAIL_CLOSED_CASES", self.section,
            "section 3 lost the pre-existing fail-closed case block")
        outcomes = ("PRODUCER_REJECT", "RESOLVED_BUT_MALFORMED")
        expressive = {"ILLEGAL_STATES": outcomes}
        self.assertEqual(
            named_failure_states(expressive, outcomes),
            {outcomes[0]: True, outcomes[1]: True},
            "the contract must be able to name both failure outcomes separately")
        collapsed = {"ILLEGAL_STATES": ("FAILURE",)}
        self.assertEqual(
            named_failure_states(collapsed, outcomes),
            {outcomes[0]: False, outcomes[1]: False},
            "a collapsed single failure state cannot represent both outcomes")

    # -- CE-13 / CE-14 -----------------------------------------------------

    def test_applicability_rule_is_documented(self):
        self.assertIn(
            "REACHABILITY_APPLICABILITY = REQUIRED | N/A", self.section,
            "section 3 does not carry the REACHABILITY_APPLICABILITY value domain")
        self.assertIn(
            "RUNTIME_REACHABLE          = TRUE | FALSE", self.section,
            "section 3 does not fix the RUNTIME_REACHABLE observation domain")
        self.assertIn(
            "MISSING_OR_EMPTY(REACHABILITY_APPLICABILITY_REASON)", self.section,
            "section 3 does not state the fail-closed rule for a missing reason")
        self.assertIn(
            "MISSING_OR_EMPTY(REACHABILITY_APPLICABILITY_ACCEPTANCE_REF)", self.section,
            "section 3 does not state the fail-closed rule for a missing acceptance ref")
        self.assertIn(
            "WORKER_SELF_GRANTED_N/A", self.section,
            "section 3 does not forbid a worker self-granting N/A")

    def test_pure_documentation_seam_may_legally_declare_na(self):
        record = {
            "REACHABILITY_APPLICABILITY": "N/A",
            "REACHABILITY_APPLICABILITY_REASON": "pure documentation seam, no runtime entrypoint",
            "REACHABILITY_APPLICABILITY_ACCEPTANCE_REF": "review-record#accepted",
        }
        self.assertEqual(
            resolve_applicability(record), "N/A",
            "a pure-documentation seam with both slots must be accepted as N/A")

    def test_runtime_seam_abusing_na_fails_closed(self):
        base = {
            "REACHABILITY_APPLICABILITY": "N/A",
            "REACHABILITY_APPLICABILITY_REASON": "reason",
            "REACHABILITY_APPLICABILITY_ACCEPTANCE_REF": "review-record#accepted",
        }
        cases = {}
        missing_reason = dict(base)
        del missing_reason["REACHABILITY_APPLICABILITY_REASON"]
        cases["missing reason"] = missing_reason
        missing_ref = dict(base)
        del missing_ref["REACHABILITY_APPLICABILITY_ACCEPTANCE_REF"]
        cases["missing acceptance ref"] = missing_ref
        cases["empty reason"] = dict(base, REACHABILITY_APPLICABILITY_REASON="")
        cases["blank reason"] = dict(base, REACHABILITY_APPLICABILITY_REASON="   ")
        cases["empty acceptance ref"] = dict(base, REACHABILITY_APPLICABILITY_ACCEPTANCE_REF="")
        cases["worker self-granted N/A"] = {
            "REACHABILITY_APPLICABILITY": "N/A",
            "REACHABILITY_APPLICABILITY_REASON": "looks pure to me",
        }
        for label, record in cases.items():
            with self.subTest(case=label):
                self.assertEqual(
                    resolve_applicability(record), "REQUIRED",
                    f"{label}: N/A must fail closed and be processed as REQUIRED")

    def test_applicability_domain_has_no_third_value(self):
        self.assertEqual(
            resolve_applicability({"REACHABILITY_APPLICABILITY": "UNKNOWN"}), "REQUIRED",
            "UNKNOWN must never stand in for a frozen applicability value")
        self.assertEqual(
            resolve_applicability({}), "REQUIRED",
            "a missing applicability value must be processed as REQUIRED")


if __name__ == "__main__":
    unittest.main()
