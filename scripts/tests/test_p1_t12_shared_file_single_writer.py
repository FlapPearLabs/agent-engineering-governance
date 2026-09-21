"""Counterexample-driven regression checks for the shared-file single-writer
and final-readback recipe in `references/ticket-lane.md` section 8 (P1-T12,
REQ-W4-02c).

SUPPORT surface (RULES.md R6), NOT an authority surface. This module declares no
recipe field and no requirement of its own: it re-reads the canonical reference
and fails when the shared-file recipe loses its one-active-writer rule, its
aggregation of compatible edits into a single / explicitly serialised
modification, its expected-entries definition, its final readback over EVERY
expected entry, its rejection of edit-tool success as content verification, or
its three rendered rejections (concurrent writers / missing entry at readback /
edit-tool success offered as proof).

BINDING (references/ticket-lane.md section 4, counterexample-first)
    The recipe itself is a document fact: it is located by marker groups over
    the non-blank, non-fence lines of section 8, so mutating (or deleting) a
    normative sentence turns the corresponding probe RED instead of passing CI
    silently. The `PROBE` table and its anti-vacuity mutations at the bottom
    perform exactly that mutation in memory and require the probe to flip.

    The constants below (`RECIPE_SIGNATURE`, the marker groups, the mutation
    anchors) are ASSERTION INPUTS -- a lock read back from the producer -- never
    a second declaration point of the recipe. The one normative declaration
    point of the recipe is section 8 of the canonical owner; see
    `test_the_recipe_is_declared_in_exactly_one_canonical_file`.

    The recipe EXTENDS the section 1 lane term ONE ACTIVE WRITER; it must not
    re-declare that term (the section 1 declaration must survive verbatim) and
    must not disturb the P1-T01 seam-contract machinery in section 3.1 (the
    single declaration point of `EXPECTED_PRODUCTION_EFFECT`, the literal
    `Canonical owner`). No new shared enum or state name is introduced and none
    of the protected review-evidence tokens may appear in the new section.

Counterexamples exercised here (parent spec section 9): CE-17 (any one of
several expected updates to a shared file missing at the final readback must be
detected), CE-28 (a recipe defined in two canonical files has a dual owner and
must be rejected and converged onto one -- AC-38: `execution-stage.md` only
references, never restates).

RED condition before P1-T12 lands: the canonical owner carries no shared-file
aggregation or readback rule, so a missing expected entry cannot be detected
and a concurrent-writer arrangement cannot be rejected. Every probe FAILS.

Stdlib only. Run with:
    python3 -m unittest scripts.tests.test_p1_t12_shared_file_single_writer
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TICKET_LANE_REL = "references/ticket-lane.md"
TICKET_LANE = ROOT / TICKET_LANE_REL
EXEC_STAGE_REL = "references/execution-stage.md"
EXEC_STAGE = ROOT / EXEC_STAGE_REL

# The subsection this ticket adds: a new level-2 section after the landed
# section 7. No existing section is renamed or renumbered.
SECTION_8_HEADING = "## 8. 共享文件单写者与最终回读（SHARED_FILE_SINGLE_WRITER）"

RECIPE_ID = "SHARED_FILE_SINGLE_WRITER"
# The ordered pipeline, byte-exact as the document must render it.
RECIPE_SIGNATURE = (
    "ONE ACTIVE WRITER -> expected entries -> single / serialised modification "
    "-> final readback -> every expected entry present")

# The landed section 1..7 headings that must survive unchanged (no rename, no
# renumbering): the new section is appended after section 7.
LANDED_HEADINGS = (
    "## 1. Lane 契约（默认；仓政策可定义例外）",
    "## 2. 读权威与 Relevant Surface Manifest",
    "## 3. Contract Extraction（MEDIUM/HIGH 必备字段块）",
    "## 4. Counterexample-first TDD",
    "## 5. 实现与自审",
    "## 6. Repair",
    "## 7. Live 状态持久化（P1）",
)
SECTION_ONE_DECLARATION = (
    "ONE ACTIVE WRITER（同一 reviewed candidate 不得并发变异；写者交接 = "
    "前写者停止 → fresh fetch → 核验 remote tip → 重建状态 → 从 exact tip 继续）")

# The landed P1-T01 seam-contract anchors (section 3.1): the new section must
# not restate or alter them.
PARTITION_1_LABEL = "(1) DESIGN / AUTHORITY REQUIREMENTS"
PARTITION_2_LABEL = "(2) CLOSURE / OBSERVATION EVIDENCE"
EFFECT_FIELD = "EXPECTED_PRODUCTION_EFFECT"
CANONICAL_OWNER_LITERAL = "Canonical owner"

# Protected review-evidence tokens (test_review_evidence_contract.py): none of
# them may be introduced into the new section.
PROTECTED_TOKENS = (
    "IDENTITY_VERSION_OR_DIGEST", "semanticScopeStatus", "reviewerDecisionRefs",
    "STRUCTURALLY_VALID", "SOURCE_VERIFICATION_STATE", "EVIDENCE_SUFFICIENCY",
)

TEXT_SUFFIXES = (".md", ".py", ".json", ".yml", ".yaml", ".txt", ".cfg",
                 ".toml")
EXCLUDED_DIRS = {".git", "__pycache__", ".agent"}
# Declared explicitly, never silently: a test surface asserts on a declared
# fact, it does not declare it. Both discovery roots are excluded, so the scan
# cannot be satisfied by this module's own constants.
TEST_SURFACE_PREFIXES = ("scripts/tests/", "adapters/zcode/tests/")

FENCE_RE = re.compile(r"^\s*```")
NEXT_HEADING_RE = re.compile(r"^## ", re.M)
FIELD_ENTRY_RE = re.compile(
    r"^\s*[A-Z][A-Z0-9_]*(?:\s*/\s*[A-Z][A-Z0-9_]*)*\s*(?:#.*)?$")

# ==========================================================================
# document helpers
# ==========================================================================

def section_body(text: str, heading: str) -> str:
    """Body of the `heading` section up to the next level-2 heading."""
    index = text.find(heading)
    if index < 0:
        return ""
    rest = text[index + len(heading):]
    nxt = NEXT_HEADING_RE.search(rest)
    return rest[: nxt.start()] if nxt else rest


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


def effect_declaration_points(root: Path):
    """Repo-wide fenced field-entry declaration points of `EFFECT_FIELD`.

    Mirrors the P1-T01 rule: DECLARATION = the field appears as a field-list
    ENTRY inside a fenced block; everything else is a REFERENCE.
    """
    points = []
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        for block in fenced_blocks(
                path.read_text(encoding="utf-8", errors="replace")):
            for line in block:
                if EFFECT_FIELD in field_entry_names(line):
                    points.append(
                        (path.relative_to(root).as_posix(), line.strip()))
    return points


# ==========================================================================
# the single-declaration-point scan (AC-38 / CE-28)
# ==========================================================================

def canonical_text_files(root: Path):
    """Every canonical (non-test) text surface of the repository."""
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if path.suffix not in TEXT_SUFFIXES:
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(TEST_SURFACE_PREFIXES):
            continue
        yield relative, path


def markdown_declaration_points(root: Path, signature: str = RECIPE_SIGNATURE):
    """Markdown files that render the recipe (a declaration-surface scan)."""
    points = []
    for path in sorted(root.rglob("*.md")):
        if ".git" in path.parts:
            continue
        if signature in path.read_text(encoding="utf-8", errors="replace"):
            points.append(path.relative_to(root).as_posix())
    return points


def token_declaration_points(root: Path, token: str = RECIPE_ID):
    """Canonical text files naming the recipe identifier."""
    hits = []
    for relative, path in canonical_text_files(root):
        if token in path.read_text(encoding="utf-8", errors="replace"):
            hits.append(relative)
    return hits


# ==========================================================================
# the executable state contract (STATE_CONTRACT / ERROR_SEMANTICS)
# ==========================================================================

STATE_LABEL = "状态合同"

LEGAL_VERDICT = "ACCEPT"
REJECT_CONCURRENT_WRITERS = "REJECT_CONCURRENT_WRITERS"
REJECT_MISSING_ENTRY = "REJECT_MISSING_ENTRY"
REJECT_TOOL_SUCCESS_AS_EVIDENCE = "REJECT_TOOL_SUCCESS_AS_EVIDENCE"


def readback_verdict(record: dict, expected_entries) -> str:
    """Dispose of a shared-file write record against the documented contract.

    Fail-closed: two writers on one canonical file, a readback missing any
    expected entry, and an edit-tool success offered as content verification
    are each a reject; only a single-writer record whose readback confirms
    every expected entry is accepted.
    """
    if record.get("concurrentWriters", 1) > 1:
        return REJECT_CONCURRENT_WRITERS
    if record.get("toolSuccessAsEvidence"):
        return REJECT_TOOL_SUCCESS_AS_EVIDENCE
    if not record.get("readbackPerformed"):
        return REJECT_MISSING_ENTRY
    confirmed = set(record.get("confirmedEntries") or ())
    if not set(expected_entries) <= confirmed:
        return REJECT_MISSING_ENTRY
    return LEGAL_VERDICT


def state_entries(lines):
    """(legal, illegal) rows of the rendered state contract block."""
    legal, illegal = [], []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("LEGAL"):
            legal.append(stripped)
        elif stripped.startswith("ILLEGAL"):
            illegal.append(stripped)
    return tuple(legal), tuple(illegal)


# ==========================================================================
# the normative rules of section 8, decomposed into marker groups
# ==========================================================================

ONE_WRITER_GROUPS = (
    ("canonical 文件",),
    ("同一时刻",),
    ("一个活跃写者",),
)

EXTENDS_NOT_REDECLARES_GROUPS = (
    ("ONE ACTIVE WRITER",),
    ("延伸", "extends"),
)

AGGREGATE_GROUPS = (
    ("聚合",),
    ("串行",),
    ("并行",),
)

EXPECTED_ENTRIES_GROUPS = (
    ("预期条目",),
    ("完整清单",),
)

READBACK_GROUPS = (
    ("最终回读",),
    ("重新读取",),
    ("每一个预期条目",),
)

TOOL_SUCCESS_GROUPS = (
    ("编辑工具",),
    ("成功",),
    ("核验",),
    ("不得", "never", "must not"),
)

EXEC_STAGE_REFERENCE_ONLY_GROUPS = (
    ("execution-stage.md",),
    ("只引用", "only reference"),
)

CE_17_GROUPS = (
    ("CE-17",),
    ("缺失",),
    ("检出",),
)

CE_28_GROUPS = (
    ("CE-28",),
    ("双 owner",),
    ("拒绝",),
)

# The rendered state contract must carry each invalid case as a rejection.
CONCURRENT_ILLEGAL_MARKERS = ("并发", "REJECT")
MISSING_ENTRY_ILLEGAL_MARKERS = ("缺失", "REJECT")
TOOL_SUCCESS_ILLEGAL_MARKERS = ("编辑工具", "REJECT")

PROBES = {
    "one_active_writer_at_a_time_on_a_shared_canonical_file": ONE_WRITER_GROUPS,
    "the_recipe_extends_the_lane_term_without_redeclaring_it":
        EXTENDS_NOT_REDECLARES_GROUPS,
    "compatible_edits_are_aggregated_or_explicitly_serialised": AGGREGATE_GROUPS,
    "expected_entries_are_the_complete_list_of_intended_edits":
        EXPECTED_ENTRIES_GROUPS,
    "a_final_readback_must_confirm_every_expected_entry": READBACK_GROUPS,
    "edit_tool_success_is_not_content_verification": TOOL_SUCCESS_GROUPS,
    "execution_stage_only_references_the_recipe": EXEC_STAGE_REFERENCE_ONLY_GROUPS,
    "counterexample_ce_17_is_stated": CE_17_GROUPS,
    "counterexample_ce_28_is_stated": CE_28_GROUPS,
}

# Anti-vacuity mutations: each removes one required marker group from the SAME
# live text and must flip its probe to False. Every mutation inverts an
# obligation, deletes a prohibition, or turns a prohibition into a permission.
PROBE_MUTATIONS = {
    "one_active_writer_at_a_time_on_a_shared_canonical_file": (
        "同一时刻只有一个活跃写者", "同一时刻允许多个活跃写者"),
    "the_recipe_extends_the_lane_term_without_redeclaring_it": (
        "在共享写面上的**延伸**", "对 §1 术语的重新声明"),
    "compatible_edits_are_aggregated_or_explicitly_serialised": (
        "聚合为一次修改或显式串行的多次修改", "各自并行修改、互不协调"),
    "expected_entries_are_the_complete_list_of_intended_edits": (
        "全部修改的**完整清单**", "大致意图即可，不必列全"),
    "a_final_readback_must_confirm_every_expected_entry": (
        "重新读取落盘结果，逐条确认**每一个预期条目**均已落盘",
        "无需重新读取落盘结果，相信写入即可"),
    "edit_tool_success_is_not_content_verification": (
        "永远不得被当作内容正确的核验", "可以作为内容正确的核验"),
    "execution_stage_only_references_the_recipe": (
        "**只引用本节**，不复述 recipe", "可自行复述 recipe"),
    "counterexample_ce_17_is_stated": (
        "→ 必须检出", "→ 可以放过"),
    "counterexample_ce_28_is_stated": (
        "→ 必须拒绝并收敛为单一 owner", "→ 可以接受双 owner 并存"),
}


class SharedFileSingleWriterTests(unittest.TestCase):
    def setUp(self):
        self.text = TICKET_LANE.read_text(encoding="utf-8")
        self.exec_text = EXEC_STAGE.read_text(encoding="utf-8")
        self.body = section_body(self.text, SECTION_8_HEADING)
        self.state_block = block_after_label(
            self.body.splitlines(), STATE_LABEL)

    # -- placement and scope of the new section ----------------------------

    def test_section_8_is_appended_after_the_landed_sections(self):
        self.assertIn(
            SECTION_8_HEADING, self.text,
            f"{TICKET_LANE_REL} does not carry the shared-file single-writer "
            f"section {SECTION_8_HEADING!r}")
        for heading in LANDED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(
                    heading, self.text,
                    f"{TICKET_LANE_REL} lost the landed heading {heading!r}; "
                    f"no existing section may be renamed or renumbered")
        positions = [self.text.index(h) for h in LANDED_HEADINGS]
        self.assertEqual(
            positions, sorted(positions),
            "the landed sections 1..7 must keep their order")
        self.assertGreater(
            self.text.index(SECTION_8_HEADING),
            self.text.index(LANDED_HEADINGS[-1]),
            "the new section must be appended after section 7")
        self.assertTrue(
            self.body.strip(), f"{TICKET_LANE_REL} section 8 is empty")

    def test_the_recipe_pipeline_is_rendered(self):
        self.assertIn(
            RECIPE_SIGNATURE, self.body,
            f"{TICKET_LANE_REL} section 8 must render the ordered pipeline "
            f"{RECIPE_SIGNATURE!r}")

    # -- the normative rules -----------------------------------------------

    def test_one_active_writer_at_a_time_on_a_shared_canonical_file(self):
        self.assertTrue(
            probe(self.body, ONE_WRITER_GROUPS),
            f"{TICKET_LANE_REL} section 8 does not require one active writer "
            f"at a time on a shared canonical file")

    def test_the_recipe_extends_the_lane_term_without_redeclaring_it(self):
        self.assertTrue(
            probe(self.body, EXTENDS_NOT_REDECLARES_GROUPS),
            f"{TICKET_LANE_REL} section 8 does not state that it extends the "
            f"section 1 lane term ONE ACTIVE WRITER")
        self.assertIn(
            SECTION_ONE_DECLARATION, self.text,
            f"{TICKET_LANE_REL} section 1 lost the ONE ACTIVE WRITER "
            f"declaration; the recipe must extend it, not replace it")

    def test_compatible_edits_are_aggregated_or_explicitly_serialised(self):
        self.assertTrue(
            probe(self.body, AGGREGATE_GROUPS),
            f"{TICKET_LANE_REL} section 8 does not aggregate compatible edits "
            f"into a single or explicitly serialised modification")

    def test_expected_entries_are_the_complete_list_of_intended_edits(self):
        self.assertTrue(
            probe(self.body, EXPECTED_ENTRIES_GROUPS),
            f"{TICKET_LANE_REL} section 8 does not define expected entries as "
            f"the complete list of intended edits")

    def test_a_final_readback_must_confirm_every_expected_entry(self):
        self.assertTrue(
            probe(self.body, READBACK_GROUPS),
            f"{TICKET_LANE_REL} section 8 does not require a final readback "
            f"confirming every expected entry")

    def test_edit_tool_success_is_not_content_verification(self):
        self.assertTrue(
            probe(self.body, TOOL_SUCCESS_GROUPS),
            f"{TICKET_LANE_REL} section 8 does not reject an edit-tool "
            f"success as content verification")

    # -- the state contract, rendered and executed --------------------------

    def test_the_rendered_state_contract_is_legal_and_illegal_rows(self):
        legal, illegal = state_entries(self.state_block)
        self.assertEqual(
            len(legal), 1,
            f"{TICKET_LANE_REL} section 8 must render exactly one LEGAL row; "
            f"legal={legal}")
        self.assertEqual(len(illegal), 3, f"illegal={illegal}")
        self.assertIn("最终回读", legal[0])
        joined = " | ".join(illegal)
        for label, markers in (
                ("concurrent writers", CONCURRENT_ILLEGAL_MARKERS),
                ("missing expected entry", MISSING_ENTRY_ILLEGAL_MARKERS),
                ("edit-tool success", TOOL_SUCCESS_ILLEGAL_MARKERS)):
            with self.subTest(invalid=label):
                row = next(
                    (r for r in illegal if all(m in r for m in markers)), None)
                self.assertIsNotNone(
                    row,
                    f"{TICKET_LANE_REL} section 8 lost the ILLEGAL rejection "
                    f"row for {label}; illegal={illegal}")
                self.assertIn(
                    "-> REJECT", row,
                    f"the {label} row must be a rejection: {row!r}")

    def test_the_state_contract_parser_is_not_vacuous(self):
        """Turning an ILLEGAL row into a LEGAL one must change the parse."""
        legal, illegal = state_entries(self.state_block)
        self.assertEqual((len(legal), len(illegal)), (1, 3))
        mutated = [
            line.replace("ILLEGAL  两个写者并发编辑",
                         "LEGAL    两个写者并发编辑")
            for line in self.state_block]
        legal2, illegal2 = state_entries(mutated)
        self.assertNotEqual(
            (len(legal2), len(illegal2)), (1, 3),
            "the state-contract parser is VACUOUS: promoting an ILLEGAL row "
            "to LEGAL did not change the parsed sets")

    def test_a_single_writer_with_a_full_readback_is_accepted(self):
        self.assertEqual(
            readback_verdict(
                {"concurrentWriters": 1, "readbackPerformed": True,
                 "confirmedEntries": ("add section 8",)},
                ("add section 8",)),
            LEGAL_VERDICT,
            "a single-writer record whose readback confirms every expected "
            "entry must be legal")

    def test_two_concurrent_writers_on_one_canonical_file_are_rejected(self):
        self.assertEqual(
            readback_verdict(
                {"concurrentWriters": 2, "readbackPerformed": True,
                 "confirmedEntries": ("add section 8",)},
                ("add section 8",)),
            REJECT_CONCURRENT_WRITERS,
            "two concurrent writers on one canonical file must be rejected")

    def test_a_missing_expected_entry_at_the_readback_is_rejected(self):
        self.assertEqual(
            readback_verdict(
                {"concurrentWriters": 1, "readbackPerformed": True,
                 "confirmedEntries": ("add section 8",)},
                ("add section 8", "add the state contract")),
            REJECT_MISSING_ENTRY,
            "a readback missing one expected entry must be rejected (CE-17)")
        self.assertEqual(
            readback_verdict(
                {"concurrentWriters": 1, "readbackPerformed": False,
                 "confirmedEntries": ()},
                ("add section 8",)),
            REJECT_MISSING_ENTRY,
            "closing without any readback must be rejected")

    def test_edit_tool_success_offered_as_proof_is_rejected(self):
        self.assertEqual(
            readback_verdict(
                {"concurrentWriters": 1, "toolSuccessAsEvidence": True,
                 "readbackPerformed": False, "confirmedEntries": ()},
                ("add section 8",)),
            REJECT_TOOL_SUCCESS_AS_EVIDENCE,
            "an edit-tool invocation offered as proof of correctness must be "
            "rejected, never accepted as verification")

    # -- counterexamples ----------------------------------------------------

    def test_counterexample_ce_17_is_stated(self):
        self.assertTrue(
            probe(self.body, CE_17_GROUPS),
            f"{TICKET_LANE_REL} section 8 does not state CE-17 (a missing "
            f"expected entry at the final readback must be detected)")

    def test_counterexample_ce_28_is_stated(self):
        self.assertTrue(
            probe(self.body, CE_28_GROUPS),
            f"{TICKET_LANE_REL} section 8 does not state CE-28 (a recipe "
            f"defined in a second canonical file has a dual owner and must be "
            f"rejected and converged)")

    # -- execution-stage.md stays reference-only (AC-38 / CE-28) ------------

    def test_execution_stage_does_not_restate_the_recipe(self):
        self.assertNotIn(
            RECIPE_ID, self.exec_text,
            f"{EXEC_STAGE_REL} must not name the recipe identifier "
            f"{RECIPE_ID}; it may only reference the canonical owner")
        self.assertNotIn(
            RECIPE_SIGNATURE, self.exec_text,
            f"{EXEC_STAGE_REL} must not render the recipe pipeline")
        for marker in ("最终回读", "expected entries"):
            self.assertNotIn(
                marker, self.exec_text,
                f"{EXEC_STAGE_REL} restates a recipe-defining marker "
                f"({marker!r}) instead of referencing the owner")

    def test_the_owner_conflict_disposition_of_execution_stage_is_untouched(self):
        self.assertIn(
            "## 2. Owner 冲突处置（多就绪票共享同一 owner）", self.exec_text,
            f"{EXEC_STAGE_REL} lost its owner-conflict disposition section")
        for disposition in ("合并为一票", "显式串行集成链", "拆 owner"):
            with self.subTest(disposition=disposition):
                self.assertIn(
                    disposition, self.exec_text,
                    f"{EXEC_STAGE_REL} section 2 lost the disposition "
                    f"{disposition!r}")

    # -- single owner / single declaration point (AC-38, CE-28) -------------

    def test_the_recipe_is_declared_in_exactly_one_canonical_file(self):
        points = markdown_declaration_points(ROOT)
        self.assertEqual(
            points, [TICKET_LANE_REL],
            f"CE-28: the shared-file single-writer recipe must be rendered "
            f"exactly once, in {TICKET_LANE_REL}; found={points}")

    def test_the_recipe_identifier_appears_once_on_canonical_surfaces(self):
        hits = token_declaration_points(ROOT)
        self.assertEqual(
            hits, [TICKET_LANE_REL],
            f"CE-28: {RECIPE_ID} must appear on exactly one canonical surface "
            f"({TICKET_LANE_REL}); found={hits}")

    def test_the_dual_owner_detector_flags_a_second_copy(self):
        """Negative control: an injected second owner IS detected."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "references").mkdir(parents=True)
            owner = root / TICKET_LANE_REL
            owner.write_text(
                "# lane\n\n" + RECIPE_SIGNATURE + "\n" + RECIPE_ID + "\n",
                encoding="utf-8")
            self.assertEqual(markdown_declaration_points(root), [TICKET_LANE_REL])
            self.assertEqual(token_declaration_points(root), [TICKET_LANE_REL])

            second = root / "references/competing-lane-recipe.md"
            second.write_text(
                "# competing owner\n\n" + RECIPE_SIGNATURE + "\n" + RECIPE_ID + "\n",
                encoding="utf-8")
            self.assertEqual(
                len(markdown_declaration_points(root)), 2,
                "DUAL_OWNER_SCAN_VACUOUS: a second canonical rendering went "
                "undetected")
            self.assertEqual(
                len(token_declaration_points(root)), 2,
                "DUAL_OWNER_SCAN_VACUOUS: a second canonical owner naming the "
                "recipe identifier went undetected")

    def test_the_dual_owner_detector_ignores_a_test_surface(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts/tests").mkdir(parents=True)
            (root / "scripts/tests/test_probe.py").write_text(
                RECIPE_ID + "\n" + RECIPE_SIGNATURE + "\n", encoding="utf-8")
            self.assertEqual(
                token_declaration_points(root), [],
                "a test surface asserts on a declared fact; it does not "
                "declare it (the declared exclusion must hold)")

    # -- the landed P1-T01 machinery must survive ----------------------------

    def test_canonical_owner_literal_is_retained(self):
        self.assertIn(
            CANONICAL_OWNER_LITERAL, self.text,
            f"{TICKET_LANE_REL}: the literal {CANONICAL_OWNER_LITERAL!r} "
            f"declaration was removed")

    def test_the_seam_contract_partitions_are_untouched(self):
        self.assertIn(
            PARTITION_1_LABEL, self.text,
            f"{TICKET_LANE_REL} lost the partition (1) label")
        self.assertIn(
            PARTITION_2_LABEL, self.text,
            f"{TICKET_LANE_REL} lost the partition (2) label")
        self.assertIn(
            "HAS EXACTLY ONE NORMATIVE DECLARATION POINT", self.text,
            f"{TICKET_LANE_REL} lost the single declaration point rule")

    def test_the_effect_field_keeps_exactly_one_declaration_point(self):
        points = effect_declaration_points(ROOT)
        self.assertEqual(
            len(points), 1,
            f"{EFFECT_FIELD} must keep exactly one normative declaration "
            f"point; found {len(points)}: {points}")
        self.assertEqual(
            points[0][0], TICKET_LANE_REL,
            f"the single declaration point must stay in {TICKET_LANE_REL}")

    def test_the_new_section_declares_no_field_entry(self):
        """A recipe is prose plus a pipeline, not a field block."""
        declared = declared_field_entries(self.body)
        self.assertEqual(
            declared, set(),
            f"{TICKET_LANE_REL} section 8 must not declare a field-list "
            f"entry; declared={sorted(declared)}")

    def test_no_protected_token_is_introduced(self):
        for token in PROTECTED_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(
                    token, self.body,
                    f"{TICKET_LANE_REL} section 8 must not introduce the "
                    f"protected token {token}")

    # -- anti-vacuity ---------------------------------------------------------

    def test_every_probe_holds_for_the_live_document(self):
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                self.assertTrue(
                    probe(self.body, groups),
                    f"{TICKET_LANE_REL} section 8: probe {name} is not "
                    f"satisfied by the live document")

    def test_every_probe_flips_red_under_a_targeted_mutation(self):
        """A mutated normative sentence must turn its probe RED (not vacuous)."""
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                old, new = PROBE_MUTATIONS[name]
                self.assertTrue(
                    probe(self.body, groups),
                    f"{TICKET_LANE_REL}: probe {name} must hold on the live "
                    f"text before the mutation is attempted")
                self.assertIn(
                    old, self.body,
                    f"{TICKET_LANE_REL}: probe {name} is not anchored to "
                    f"document text; the expected marker {old!r} is absent")
                mutated = self.body.replace(old, new)
                self.assertNotEqual(mutated, self.body)
                self.assertFalse(
                    probe(mutated, groups),
                    f"{TICKET_LANE_REL}: probe {name} is VACUOUS - mutating "
                    f"{old!r} -> {new!r} did not turn it RED")

    def test_probe_helper_requires_all_marker_groups_on_one_statement(self):
        groups = (("ALPHA",), ("BETA",))
        self.assertTrue(probe("ALPHA and BETA", groups))
        self.assertFalse(
            probe("ALPHA\nBETA", groups),
            "the probe helper must not be satisfiable by markers scattered "
            "across unrelated statements")


if __name__ == "__main__":
    unittest.main()
