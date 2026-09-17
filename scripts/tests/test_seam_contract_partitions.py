"""Counterexample-driven regression checks for the seam contract block in
`references/ticket-lane.md` section 3.

SUPPORT surface (RULES R6), NOT an authority surface. This module declares no
seam field and no requirement: it re-reads the canonical reference and fails
when the contract loses its two labelled partitions, breaks a frozen field
name, collides a design/authority name with a closure/observation name, or
loses its single-declaration-point and fail-closed applicability rules.

BINDING (repair of finding F1, consistency axis)
    The expected behaviour of the CE-01 / CE-02 / CE-03 / CE-13 / CE-14 /
    CE-29 checks is DERIVED FROM THE DOCUMENT TEXT instead of being re-stated
    as a constant inside this module:

      * the partition (1) / partition (2) name sets are parsed out of the
        section 3.1.1 / 3.1.2 field blocks (`parse_partition_names`), so an
        injected or demoted name changes the compared sets;
      * the `REACHABILITY_APPLICABILITY` value domain, the slots an `N/A`
        declaration must carry, the missing/empty fail-closed outcome and the
        worker-self-grant violation are parsed out of the section 3.1.4 rule
        block and its normative prose (`parse_applicability_contract`); the
        applicability resolver used by the counterexamples is then built from
        that parsed contract (`resolve_applicability`) rather than from a
        hard-coded rule;
      * the requirement/observation semantic roles of the two partitions, and
        the absence of decorative annotations on requirement fields, are read
        back from the document (`decorative_entries` and the role assertions).

    A drift of the *documented* contract therefore turns these tests RED
    instead of passing CI silently.

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

# Section anchors used to locate the canonical rule blocks inside section 3.
PARTITION_1_HEADING = "#### 3.1.1"
PARTITION_2_HEADING = "#### 3.1.2"
APPLICABILITY_HEADING = "#### 3.1.4"

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

# Fields whose semantics the CE-01 / CE-02 / CE-03 counterexamples exercise.
TIMING_FIELDS = ("SYNC_OR_ASYNC", "AWAIT_REQUIREMENT", "LIFECYCLE_REQUIREMENT")
STATE_FIELDS = ("LEGAL_STATES", "ILLEGAL_STATES")
ERROR_FIELDS = ("ERROR_OWNER", "FAIL_OPEN_OR_FAIL_CLOSED")

# Applicability fields (CE-13 / CE-14).
APPLICABILITY_FIELD = "REACHABILITY_APPLICABILITY"
APPLICABILITY_REASON_FIELD = "REACHABILITY_APPLICABILITY_REASON"
APPLICABILITY_REF_FIELD = "REACHABILITY_APPLICABILITY_ACCEPTANCE_REF"
APPLICABILITY_SLOTS = (APPLICABILITY_REASON_FIELD, APPLICABILITY_REF_FIELD)
REACHABILITY_OBSERVATION_FIELD = "RUNTIME_REACHABLE"
APPLICABILITY_DOMAIN = frozenset({"REQUIRED", "N/A"})
REACHABILITY_OBSERVATION_DOMAIN = frozenset({"TRUE", "FALSE"})

# Annotation markers that would declare a requirement field non-binding. A
# requirement field carrying one of these is decorative and no longer a
# requirement, which is exactly the drift the CE-01/02/03 checks must catch.
DECORATIVE_MARKERS = (
    "decorative", "cosmetic", "informational", "informative", "advisory",
    "non-normative", "nonnormative", "not enforceable", "not enforced",
    "unenforced", "no enforcement", "ignored", "may be omitted",
    "not required", "optional",
    "仅供参考", "装饰", "装饰性", "非强制", "无强制", "不强制", "不必填",
    "可不填", "可选", "非规范", "无约束", "仅说明", "无需强制",
)

SECTION_THREE_RE = re.compile(r"^##\s+3\.", re.M)
NEXT_SECTION_RE = re.compile(r"^##\s", re.M)
FENCE_RE = re.compile(r"^\s*```")
UPPER_TOKEN_RE = re.compile(r"[A-Z][A-Z0-9_]*")
# A field-list ENTRY line: bare field name(s) joined by "/", optional "#" note.
FIELD_ENTRY_RE = re.compile(
    r"^\s*[A-Z][A-Z0-9_]*(?:\s*/\s*[A-Z][A-Z0-9_]*)*\s*(?:#.*)?$")
# A whole field name (at least one underscore), used to read rule prose.
FIELD_TOKEN_RE = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b")
DOMAIN_RE = re.compile(r"^\s*([A-Z][A-Z0-9_]*)\s*=\s*(.+?)\s*$", re.M)
FAIL_CLOSED_RE = re.compile(r"^FAIL-CLOSED\s+(.*?)\s*=>\s*(.*?)\s*$", re.M)
MISSING_OR_EMPTY_RE = re.compile(
    r"MISSING_OR_EMPTY\(\s*([A-Z][A-Z0-9_]*)\s*\)")
NA_RULE_RE = re.compile(r"^\s*N/A\s*->\s*(.+)$")
NA_BULLET_RE = re.compile(r"^\s*-\s*`N/A`")
PROCESS_AS_PREFIX = "PROCESS_AS "
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


def block_lines_after_label(lines, label: str):
    """Fenced-block lines following the first line carrying `label`."""
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


def block_after_label(lines, label: str) -> str:
    """Return the first fenced block following the first line carrying `label`."""
    return "\n".join(block_lines_after_label(lines, label))


def field_entry_names(line: str):
    """Field names declared by a field-list entry line; empty when not one."""
    if not FIELD_ENTRY_RE.match(line):
        return set()
    body = line.split("#", 1)[0]
    return {token.strip() for token in body.split("/") if token.strip()}


def field_entries(block_lines):
    """Map field name -> annotation for every entry line of a field block."""
    entries = {}
    for line in block_lines:
        names = field_entry_names(line)
        if not names:
            continue
        annotation = line.split("#", 1)[1].strip() if "#" in line else ""
        for name in names:
            entries[name] = annotation
    return entries


def parse_partition_names(block_lines):
    """The field names a document field block actually declares."""
    return {name for line in block_lines for name in field_entry_names(line)}


def partition_name_collisions(design_lines, observation_lines):
    """Names shared by the design/authority and closure/observation blocks."""
    return (parse_partition_names(design_lines)
            & parse_partition_names(observation_lines))


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
# section 3.1.4: the applicability contract, parsed out of the document
# --------------------------------------------------------------------------

def effective_outcome(outcome: str):
    """`PROCESS_AS REQUIRED` resolves to the effective applicability `REQUIRED`."""
    if outcome.startswith(PROCESS_AS_PREFIX):
        return outcome[len(PROCESS_AS_PREFIX):].strip()
    return outcome


def parse_applicability_contract(block_lines, section_lines):
    """Derive the applicability contract from the section 3.1.4 text.

    Everything the CE-13 / CE-14 counterexamples assert is read back from the
    document here: the legal value domain, the slots an `N/A` declaration must
    carry (from BOTH the rule block line and its normative prose bullet, which
    must agree), the fail-closed outcome for a missing/empty slot, and the
    outcome of a worker self-granting `N/A`.
    """
    block_text = "\n".join(block_lines)

    domain = frozenset()
    runtime_domain = frozenset()
    for name, rhs in DOMAIN_RE.findall(block_text):
        if name == APPLICABILITY_FIELD:
            domain = frozenset(
                token.strip() for token in rhs.split("|") if token.strip())
        elif name == REACHABILITY_OBSERVATION_FIELD:
            runtime_domain = frozenset(
                token.strip() for token in rhs.split("|") if token.strip())

    block_rule_slots = frozenset()
    for line in block_lines:
        match = NA_RULE_RE.match(line)
        if match:
            block_rule_slots = frozenset(FIELD_TOKEN_RE.findall(match.group(1)))

    prose_rule_slots = frozenset()
    for line in section_lines:
        if NA_BULLET_RE.match(line):
            prose_rule_slots = frozenset(FIELD_TOKEN_RE.findall(line))
            break

    fail_closed = {}
    for condition, outcome in FAIL_CLOSED_RE.findall(block_text):
        key = re.sub(r"\s+", " ", condition).strip()
        fail_closed[key] = outcome.strip()

    missing_or_empty = {}
    for condition, outcome in fail_closed.items():
        match = MISSING_OR_EMPTY_RE.search(condition)
        if match:
            missing_or_empty[match.group(1)] = effective_outcome(outcome)

    self_grants = sorted(
        condition for condition in fail_closed
        if "WORKER_SELF_GRANTED" in condition)
    self_grant_outcome = fail_closed[self_grants[0]] if self_grants else None

    fallback_values = {missing_or_empty[slot] for slot in missing_or_empty}
    fallback = fallback_values.pop() if len(fallback_values) == 1 else None

    required_slots = frozenset(block_rule_slots | prose_rule_slots)

    return {
        "domain": domain,
        "runtime_domain": runtime_domain,
        "block_rule_slots": block_rule_slots,
        "prose_rule_slots": prose_rule_slots,
        "required_slots": required_slots,
        "missing_or_empty": missing_or_empty,
        "fail_closed": fail_closed,
        "self_grant_outcome": self_grant_outcome,
        "fallback": fallback,
    }


def resolve_applicability(record, contract):
    """Executable applicability resolver, driven by the parsed contract.

    Fail-closed: a value outside the documented domain, a missing/empty slot
    required for `N/A`, or a worker self-granting `N/A` (no acceptance
    reference) is processed as the documented fail-closed outcome -- which the
    document fixes as `REQUIRED`.
    """
    value = record.get(APPLICABILITY_FIELD)
    if value != "N/A" or "N/A" not in contract["domain"]:
        return contract["fallback"]
    for slot in sorted(contract["required_slots"]):
        if not filled(record.get(slot)):
            return contract["missing_or_empty"].get(slot, contract["fallback"])
    return "N/A"


# --------------------------------------------------------------------------
# executable encodings used as positive controls (fixtures live in the tests)
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


def decorative_entries(entries):
    """Requirement entries whose annotation declares them non-binding."""
    problems = []
    for name, annotation in entries.items():
        lowered = annotation.lower()
        for marker in DECORATIVE_MARKERS:
            if marker in lowered:
                problems.append((name, marker, annotation))
    return problems


def filled(value) -> bool:
    return isinstance(value, str) and value.strip() != ""


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
        self.section_lines = self.section.splitlines()

        self.partition_1_lines = block_lines_after_label(
            self.lines, PARTITION_1_LABEL)
        self.partition_2_lines = block_lines_after_label(
            self.lines, PARTITION_2_LABEL)
        self.partition_1 = "\n".join(self.partition_1_lines)
        self.partition_2 = "\n".join(self.partition_2_lines)

        # Both partitions are read from the document, never from a constant.
        self.partition_1_entries = field_entries(self.partition_1_lines)
        self.partition_2_entries = field_entries(self.partition_2_lines)
        self.partition_1_names = set(self.partition_1_entries)
        self.partition_2_names = set(self.partition_2_entries)

        self.applicability_block = block_lines_after_label(
            self.lines, APPLICABILITY_HEADING)
        self.applicability = parse_applicability_contract(
            self.applicability_block, self.section_lines)

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

    def test_partition_name_sets_parsed_from_the_document_are_exact(self):
        """The document's own field blocks, not a constant, define the sets."""
        self.assertEqual(
            sorted(self.partition_1_names), sorted(PARTITION_1_FIELDS),
            f"{TICKET_LANE_REL} section 3 partition (1) block declares "
            f"{sorted(self.partition_1_names)}")
        self.assertEqual(
            sorted(self.partition_2_names), sorted(PARTITION_2_FIELDS),
            f"{TICKET_LANE_REL} section 3 partition (2) block declares "
            f"{sorted(self.partition_2_names)}")

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
        shared = sorted(partition_name_collisions(
            self.partition_1_lines, self.partition_2_lines))
        self.assertEqual(
            shared, [],
            f"{TICKET_LANE_REL} section 3: the design/authority and "
            f"closure/observation partitions share names: {shared}")

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
            ambiguous_pairs(sorted(self.partition_1_names),
                            sorted(self.partition_2_names), FROZEN_PAIRINGS),
            [],
            "an ambiguous design/observation field pair exists in "
            f"{TICKET_LANE_REL} section 3")

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

    def test_collision_detector_reads_the_document_blocks(self):
        """Injecting a partition (1) name into partition (2) must be detected."""
        self.assertEqual(
            partition_name_collisions(self.partition_1_lines,
                                      self.partition_2_lines),
            set(),
            "the live document already collides a partition name")
        injected = list(self.partition_2_lines) + ["EXPECTED_PRODUCTION_CALLER"]
        self.assertIn(
            "EXPECTED_PRODUCTION_CALLER",
            partition_name_collisions(self.partition_1_lines, injected),
            "the collision check no longer derives its name sets from the "
            "document blocks")

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

    def test_design_partition_is_documented_as_the_requirement_side(self):
        """Partition (1) must be documented as requirements, (2) as observations."""
        self.assertIn(
            "DESIGN / AUTHORITY REQUIREMENTS", self.text,
            f"{TICKET_LANE_REL} lost the design/authority requirements heading")
        self.assertIn(
            "CLOSURE / OBSERVATION EVIDENCE", self.text,
            f"{TICKET_LANE_REL} lost the closure/observation evidence heading")
        self.assertIn(
            "要求什么", self.section,
            "section 3 no longer says partition (1) expresses what is required")
        self.assertIn(
            "实际观测到什么", self.section,
            "section 3 no longer says partition (2) records what was observed")
        self.assertEqual(
            decorative_entries(self.partition_1_entries), [],
            f"{TICKET_LANE_REL} section 3 partition (1) declares a requirement "
            f"field as non-binding/decorative")

    def test_async_production_shape_is_expressible(self):
        for name in TIMING_FIELDS:
            with self.subTest(field=name):
                self.assertIn(
                    name, self.partition_1_names,
                    f"{TICKET_LANE_REL} partition (1) cannot express the "
                    f"production timing requirement {name}")
                self.assertNotIn(
                    name, self.partition_2_names,
                    f"{TICKET_LANE_REL} demoted the timing requirement {name} "
                    f"into the closure/observation partition")
        # The document must bind the timing block to the frozen requirement
        # side: a field parked in partition (1) is a requirement, so marking it
        # decorative or optional would silently make timing unexpressible.
        self.assertIn(
            "PARTITION (1) IS FROZEN BEFORE TICKETING", self.section,
            "section 3 no longer freezes partition (1) before ticketing")
        self.assertIn(
            "要求什么", self.section,
            "section 3 no longer defines partition (1) as the requirement side")
        self.assertEqual(
            decorative_entries(
                {name: self.partition_1_entries[name] for name in TIMING_FIELDS}),
            [],
            f"{TICKET_LANE_REL} marks a production timing requirement field as "
            f"decorative")
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
        for name in STATE_FIELDS:
            with self.subTest(field=name):
                self.assertIn(
                    name, self.partition_1_names,
                    f"{TICKET_LANE_REL} partition (1) cannot express the seam "
                    f"state requirement {name}")
                self.assertNotIn(
                    name, self.partition_2_names,
                    f"{TICKET_LANE_REL} demoted the seam state requirement {name} "
                    f"into the closure/observation partition")
        # An illegal-state requirement only binds while partition (2) is barred
        # from rewriting it; the document must still say so.
        self.assertIn(
            "PARTITION (2) ONLY FILLS THE SLOTS DECLARED BY (1)", self.section,
            "section 3 no longer bars partition (2) from rewriting requirements")
        self.assertIn(
            "CLOSURE_EVIDENCE_CAN_NEVER_REWRITE_A_REQUIREMENT", self.section,
            "section 3 no longer bars closure evidence from rewriting a requirement")
        self.assertEqual(
            decorative_entries(
                {name: self.partition_1_entries[name] for name in STATE_FIELDS}),
            [],
            f"{TICKET_LANE_REL} marks an illegal-state requirement field as decorative")
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
        for name in ERROR_FIELDS:
            with self.subTest(field=name):
                self.assertIn(
                    name, self.partition_1_names,
                    f"{TICKET_LANE_REL} partition (1) cannot express the error "
                    f"semantics requirement {name}")
                self.assertNotIn(
                    name, self.partition_2_names,
                    f"{TICKET_LANE_REL} demoted the error semantics requirement "
                    f"{name} into the closure/observation partition")
        self.assertIn(
            "FAIL_CLOSED_CASES", self.section,
            "section 3 lost the pre-existing fail-closed case block")
        self.assertIn(
            "要求什么", self.section,
            "section 3 no longer defines partition (1) as the requirement side, "
            "so a collapsed failure requirement would go unnoticed")
        self.assertEqual(
            decorative_entries(
                {name: self.partition_1_entries[name] for name in ERROR_FIELDS}),
            [],
            f"{TICKET_LANE_REL} marks an error semantics requirement field as decorative")
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

    def test_applicability_contract_is_derived_from_the_document(self):
        """The parsed contract must match what the document normatively says."""
        contract = self.applicability
        self.assertEqual(
            contract["domain"], APPLICABILITY_DOMAIN,
            f"{TICKET_LANE_REL} section 3.1.4 applicability value domain is "
            f"{sorted(contract['domain'])}, not {sorted(APPLICABILITY_DOMAIN)}")
        self.assertEqual(
            contract["runtime_domain"], REACHABILITY_OBSERVATION_DOMAIN,
            f"{TICKET_LANE_REL} section 3.1.4 RUNTIME_REACHABLE domain is "
            f"{sorted(contract['runtime_domain'])}")
        self.assertEqual(
            contract["block_rule_slots"], frozenset(APPLICABILITY_SLOTS),
            f"the 3.1.4 rule block no longer requires both slots for N/A: "
            f"{sorted(contract['block_rule_slots'])}")
        self.assertEqual(
            contract["prose_rule_slots"], frozenset(APPLICABILITY_SLOTS),
            f"the 3.1.4 normative prose no longer requires both slots for N/A: "
            f"{sorted(contract['prose_rule_slots'])}")
        self.assertEqual(
            contract["required_slots"], frozenset(APPLICABILITY_SLOTS),
            f"the N/A slots required by the document are "
            f"{sorted(contract['required_slots'])}")
        self.assertEqual(
            contract["fallback"], "REQUIRED",
            f"the documented fail-closed applicability outcome is "
            f"{contract['fallback']!r}, not 'REQUIRED'")
        for slot in APPLICABILITY_SLOTS:
            self.assertEqual(
                contract["missing_or_empty"].get(slot), "REQUIRED",
                f"section 3 does not state that a missing/empty {slot} is "
                f"processed as REQUIRED")
        self.assertEqual(
            contract["self_grant_outcome"], "CONTRACT_VIOLATION",
            "section 3 no longer makes a worker self-granted N/A a contract violation")
        self.assertNotIn(
            contract["self_grant_outcome"], contract["domain"],
            "the self-grant outcome must not be a legal applicability value")

    def test_applicability_parser_reads_the_document_text(self):
        """Dropping a slot from the document must change the parsed contract."""
        mutated = []
        for line in self.applicability_block:
            if line.lstrip().startswith("N/A") and "->" in line:
                line = "N/A       -> 必须同时填写 " + APPLICABILITY_REASON_FIELD
            mutated.append(line)
        contract = parse_applicability_contract(mutated, self.section_lines)
        self.assertNotEqual(
            contract["block_rule_slots"], frozenset(APPLICABILITY_SLOTS),
            "the applicability parser is not reading the document text")
        self.assertEqual(
            self.applicability["block_rule_slots"], frozenset(APPLICABILITY_SLOTS))

    def test_pure_documentation_seam_may_legally_declare_na(self):
        record = {
            APPLICABILITY_FIELD: "N/A",
            APPLICABILITY_REASON_FIELD: "pure documentation seam, no runtime entrypoint",
            APPLICABILITY_REF_FIELD: "review-record#accepted",
        }
        self.assertEqual(
            resolve_applicability(record, self.applicability), "N/A",
            "a pure-documentation seam with both slots must be accepted as N/A")

    def test_runtime_seam_abusing_na_fails_closed(self):
        base = {
            APPLICABILITY_FIELD: "N/A",
            APPLICABILITY_REASON_FIELD: "reason",
            APPLICABILITY_REF_FIELD: "review-record#accepted",
        }
        cases = {}
        missing_reason = dict(base)
        del missing_reason[APPLICABILITY_REASON_FIELD]
        cases["missing reason"] = missing_reason
        missing_ref = dict(base)
        del missing_ref[APPLICABILITY_REF_FIELD]
        cases["missing acceptance ref"] = missing_ref
        cases["empty reason"] = dict(base, **{APPLICABILITY_REASON_FIELD: ""})
        cases["blank reason"] = dict(base, **{APPLICABILITY_REASON_FIELD: "   "})
        cases["empty acceptance ref"] = dict(base, **{APPLICABILITY_REF_FIELD: ""})
        cases["worker self-granted N/A"] = {
            APPLICABILITY_FIELD: "N/A",
            APPLICABILITY_REASON_FIELD: "looks pure to me",
        }
        for label, record in cases.items():
            with self.subTest(case=label):
                self.assertEqual(
                    resolve_applicability(record, self.applicability), "REQUIRED",
                    f"{label}: N/A must fail closed and be processed as REQUIRED")

    def test_applicability_domain_has_no_third_value(self):
        fallback = self.applicability["fallback"]
        self.assertNotIn(
            "UNKNOWN", self.applicability["domain"],
            "UNKNOWN must never be a frozen applicability value")
        self.assertEqual(
            resolve_applicability(
                {APPLICABILITY_FIELD: "UNKNOWN"}, self.applicability), fallback,
            "UNKNOWN must never stand in for a frozen applicability value")
        self.assertEqual(
            resolve_applicability({}, self.applicability), fallback,
            "a missing applicability value must be processed as REQUIRED")


if __name__ == "__main__":
    unittest.main()
