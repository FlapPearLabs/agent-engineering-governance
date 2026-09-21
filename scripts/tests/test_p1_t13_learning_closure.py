"""Counterexample-first regression for the on-demand learning-closure recipe in
`references/engineering-memory.md` section 4 (Issue #13 / P1-T13 / REQ-W4-02d).

SUPPORT surface (RULES.md R6), NOT an authority surface. This module declares no
recipe of its own: it reads the closure conditions back out of their single
canonical owner and fails when

  * a bare status assertion (`fixed` / `done` / `resolved` / 已修复 / 已完成 /
    已解决) is accepted as a closure (`CE-18` / `AC-16`);
  * the closure stops requiring an explicit accept-or-reject disposition WITH a
    reason, or stops requiring a verification reference;
  * any one of the three illegal cases stops being a rejection;
  * the recipe turns into a mandatory per-ticket field set / template
    (`REQ-W4-02d`: the recipe is ON DEMAND);
  * the memory promotion policy in section 1 (`PROMOTE` / `DO NOT PROMOTE` rows
    and the per-promotion record fields) is altered, or a landed section is
    renamed;
  * a second canonical file restates the closure conditions (`CE-28` / `AC-38`).

WHY THIS IS NOT A VACUOUS GREP
    `parse_closure_contract` reads the LEGAL rows, the ILLEGAL rows and the
    fenced blocks out of the document's own text, and `decide_closure` is driven
    by the requirements those rows declare. `test_every_rule_flips_red_under_a
    targeted_mutation` rewrites the normative prose in memory and requires each
    decision to follow. Every mutation is anchored on text that is asserted to
    exist (and to be unique) BEFORE it is used -- a mutation control that cannot
    find its anchor must fail loudly rather than pass silently.

RED condition before P1-T13 lands: the canonical owner ends at section 3, so it
carries no closure-condition text at all -- there is no section 4, no state
contract and no illegal-closure case, so a status-only closure is
indistinguishable from a grounded one and every probe below FAILS with an
explicit RECIPE_ABSENT style message (never an ImportError / broken harness).

Stdlib only. Run with:
    python3 -m unittest scripts.tests.test_p1_t13_learning_closure
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_REL = "references/engineering-memory.md"
DOC = ROOT / DOC_REL

# The appended section. No landed section is renamed or renumbered: the new
# section is added after the landed section 3.
SECTION_4_HEADING = "## 4. Learning 关闭条件（按需 recipe；非每票模板）"

# The landed headings that must survive verbatim and in order.
LANDED_HEADINGS = (
    "## 1. 晋升判定",
    "### 记忆路由（V1.1.2，与 project-state-persistence §9 同步）",
    "## 2. 已晋升内容（V1.1，源自原始 MEMORY 的 durable 工程知识）",
    "## 3. 原始 MEMORY 的其余内容",
)

# The landed section 1 promotion policy: the two dispositions and the
# per-promotion record fields. Locked verbatim; this recipe must not touch them.
PROMOTION_ROWS = (
    "| approved 工程原则 / 重复失效模式 / 稳定工作流决策 / 评审经济学 / "
    "模型与工具路由哲学 / durable CI 语义 / CodeGraph 稳定经验 / 跨项目工程偏好 / "
    "已证反模式 / 稳定自治与 STOP 行为 | **PROMOTE**（进 canonical 文档对应节；"
    "或确认已覆盖） |",
    "| 临时事故记录、当前任务状态、旧 SHA/status、一次性 troubleshooting、"
    "用户个人细节、凭据、deployment profile 之外的本地路径事实、原始对话、"
    "推测性推理、已被取代的规则 | **DO NOT PROMOTE**（留在 runtime memory 或丢弃） |",
)
PROMOTION_RECORD_FIELDS = (
    "每次晋升记录：`SOURCE = MEMORY` / `DURABILITY_REASON` / "
    "`CANONICAL_DESTINATION` / `EXISTING_DUPLICATE = YES|NO` / "
    "`ACTION = ADD|MERGE|ALREADY_COVERED|DROP`。"
)
CANONICAL_OWNER_LITERAL = "Canonical owner"

# The CE-18 anchor: a plain-text sentence that must exist exactly once. It is
# asserted to be present and unique BEFORE any mutation control uses it.
CE_18_ANCHOR = (
    "仅凭一句状态断言（fixed / done / resolved / 已修复 / 已完成 / 已解决）")

# The two rendered blocks of section 4.
STATE_LABEL = "状态合同"
ERROR_SEMANTICS_LABEL = "错误语义"
CLOSURE_INVALID = "关闭无效"

# Markers for the repo-wide single-owner scan (CE-28 / AC-38).
RECIPE_MARKERS = (SECTION_4_HEADING, CE_18_ANCHOR)

FENCE_RE = re.compile(r"^\s*```")
NEXT_HEADING_RE = re.compile(r"^## ", re.M)
# A field-name-shaped token (ALL_CAPS_SNAKE_CASE). The recipe must introduce no
# new field name, so none may appear in the appended section.
FIELD_NAME_RE = re.compile(r"\b[A-Z][A-Z0-9]*_[A-Z0-9_]+\b")
MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")

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

    A normative rule is located on ONE line, so a probe cannot be satisfied by
    markers scattered across unrelated statements.
    """
    return [line.strip() for line in section_text.splitlines()
            if line.strip() and not FENCE_RE.match(line)]


def probe(section_text: str, groups) -> bool:
    """True when ONE statement carries every marker group (any alternative)."""
    for line in statements(section_text):
        if all(any(alt in line for alt in group) for group in groups):
            return True
    return False


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


# ==========================================================================
# the executable closure contract (STATE_CONTRACT / ERROR_SEMANTICS)
# ==========================================================================

DISPOSITIONS = ("accept", "reject")

# Component markers of a LEGAL row: the two things closure requires.
REASON_MARKER = "理由"
VERIFICATION_MARKER = "验证引用"

# Condition markers of an ILLEGAL row, in match order.
ILLEGAL_CONDITION_MARKERS = (
    ("assertion_only", ("状态断言",)),
    ("missing_verification", ("缺少", VERIFICATION_MARKER)),
    ("missing_reason", ("缺少", REASON_MARKER)),
)

LEGAL_VERDICT = "ACCEPT"
REJECT_ASSERTION_ONLY = "REJECT_ASSERTION_ONLY"
REJECT_MISSING_REASON = "REJECT_MISSING_REASON"
REJECT_MISSING_VERIFICATION = "REJECT_MISSING_VERIFICATION"
REJECT_NO_DISPOSITION = "REJECT_NO_DISPOSITION"

# A condition name -> the rejection it produces when the document declares it.
CONDITION_REJECTIONS = {
    "assertion_only": REJECT_ASSERTION_ONLY,
    "missing_reason": REJECT_MISSING_REASON,
    "missing_verification": REJECT_MISSING_VERIFICATION,
}


def parse_legal_row(row: str):
    """(disposition, frozenset(required components)) of a rendered LEGAL row."""
    body = row.strip().split(None, 1)[1] if len(row.strip().split(None, 1)) > 1 else ""
    parts = [part.strip() for part in body.split("+") if part.strip()]
    if not parts:
        return None, frozenset()
    disposition = parts[0].strip().lower()
    components = set()
    for part in parts[1:]:
        if REASON_MARKER in part:
            components.add("reason")
        if VERIFICATION_MARKER in part:
            components.add("verification")
    return disposition, frozenset(components)


def parse_illegal_row(row: str):
    """The declared illegal-closure condition of a rendered ILLEGAL row."""
    for name, markers in ILLEGAL_CONDITION_MARKERS:
        if all(marker in row for marker in markers):
            return name
    return None


def parse_closure_contract(state_block, error_block) -> dict:
    """Read the closure rules out of the document's own rendered rows.

    Nothing is hard-coded here: the legal rows define which components a
    disposition requires, the illegal rows define which invalid cases are
    rejected, and the error-semantics rows define the closed failure text.
    """
    legal_rows: dict = {}
    illegal_conditions = set()
    for line in state_block:
        stripped = line.strip()
        if stripped.startswith("LEGAL"):
            disposition, components = parse_legal_row(stripped)
            if disposition:
                legal_rows[disposition] = components
        elif stripped.startswith("ILLEGAL"):
            condition = parse_illegal_row(stripped)
            if condition:
                illegal_conditions.add(condition)
    invalid_outcomes = [line.strip() for line in error_block if line.strip()]
    return {
        "legal_rows": legal_rows,
        "illegal_conditions": illegal_conditions,
        "invalid_outcomes": tuple(invalid_outcomes),
    }


def decide_closure(record: dict, contract: dict) -> str:
    """Dispose of a candidate learning-entry closure against the parsed rules.

    Fail-closed: a bare status assertion, a missing reason and a missing
    verification reference are each a rejection when -- and only when -- the
    canonical owner declares that case illegal. Deleting a requirement, deleting
    an illegal row or turning a requirement into a permission therefore changes
    the verdict, which is what the mutation controls below assert.
    """
    legal_rows = contract["legal_rows"]
    illegal = contract["illegal_conditions"]
    disposition = (record.get("disposition") or "").strip().lower()

    if disposition not in legal_rows:
        if "assertion_only" in illegal:
            return REJECT_ASSERTION_ONLY
        return REJECT_NO_DISPOSITION

    required = legal_rows[disposition]
    if ("reason" in required and not (record.get("reason") or "").strip()
            and "missing_reason" in illegal):
        return REJECT_MISSING_REASON
    if ("verification" in required
            and not (record.get("verification_ref") or "").strip()
            and "missing_verification" in illegal):
        return REJECT_MISSING_VERIFICATION
    return LEGAL_VERDICT


# ==========================================================================
# the normative rules of section 4, decomposed into marker groups
# ==========================================================================

CLOSURE_REQUIRES_BOTH_GROUPS = (
    ("必须同时", "must both"),
    ("accept",),
    ("reject",),
    (REASON_MARKER,),
    (VERIFICATION_MARKER,),
)

STATUS_ONLY_FORBIDDEN_GROUPS = (
    ("状态断言",),
    ("不得", "must not", "never"),
)

ON_DEMAND_GROUPS = (
    ("按需",),
    ("不是",),
    ("每票必填",),
)

NO_SECOND_STATE_MACHINE_GROUPS = (
    ("不引入",),
    ("枚举",),
    ("状态机",),
)

SINGLE_OWNER_GROUPS = (
    ("唯一 canonical owner",),
)

POINTER_ONLY_GROUPS = (
    ("其它 surface",),
    ("只指针", "只引用", "只链接"),
)

CE_18_GROUPS = (
    ("CE-18",),
    ("拒绝",),
)

CE_28_GROUPS = (
    ("CE-28",),
    ("双 owner",),
    ("拒绝",),
)

PROBES = {
    "closure_requires_disposition_reason_and_verification":
        CLOSURE_REQUIRES_BOTH_GROUPS,
    "status_only_closure_is_forbidden": STATUS_ONLY_FORBIDDEN_GROUPS,
    "the_recipe_is_on_demand_and_not_a_per_ticket_field_set": ON_DEMAND_GROUPS,
    "no_new_global_enum_or_state_machine_is_introduced":
        NO_SECOND_STATE_MACHINE_GROUPS,
    "the_section_names_its_single_canonical_owner": SINGLE_OWNER_GROUPS,
    "other_surfaces_only_point_at_the_recipe": POINTER_ONLY_GROUPS,
    "counterexample_ce_18_is_stated": CE_18_GROUPS,
    "counterexample_ce_28_is_stated": CE_28_GROUPS,
}

# Anti-vacuity mutations: each rewrites ONE normative statement of the live
# section and must flip its probe to False. Every `old` is asserted to exist --
# and to be unique -- before the replacement is attempted.
PROBE_MUTATIONS = {
    "closure_requires_disposition_reason_and_verification": (
        "必须同时给出「显式处置（采纳 accept / 拒绝 reject）+ 理由 + 验证引用」",
        "只需给出一个显式处置（采纳 accept / 拒绝 reject）"),
    "status_only_closure_is_forbidden": (
        "**不得**关闭 learning 条目", "**可以**关闭 learning 条目"),
    "the_recipe_is_on_demand_and_not_a_per_ticket_field_set": (
        "它不是每票必填的字段组",
        "它是每张票都要照抄的强制字段组"),
    "no_new_global_enum_or_state_machine_is_introduced": (
        "不引入新的全局枚举、状态机或字段名",
        "引入新的全局枚举与状态机"),
    "the_section_names_its_single_canonical_owner": (
        "**唯一 canonical owner**", "本节的一家之言"),
    "other_surfaces_only_point_at_the_recipe": (
        "其它 surface 只指针或链接到本节，不复述这些条件",
        "其它 surface 可各自复述这些条件"),
    "counterexample_ce_18_is_stated": (
        "`CE-18`：一个 learning 条目在没有采纳/拒绝理由与验证引用时被关闭"
        "必须被拒绝。",
        "`CE-18` 无需专用处置。"),
    "counterexample_ce_28_is_stated": (
        "必须拒绝并收敛为单一 owner", "可以接受双 owner 并存"),
}

# ==========================================================================
# repo-wide single-owner scan (AC-38 / CE-28)
# ==========================================================================


def canonical_scan_targets(root: Path):
    """`references/**/*.md` plus `AGENTS.md` and `RULES.md`."""
    targets = [root / "AGENTS.md", root / "RULES.md"]
    targets += sorted((root / "references").rglob("*.md"))
    return [path for path in targets if path.is_file()]


def scan_recipe_markers(root: Path) -> dict:
    """Marker -> the canonical files that carry it."""
    hits: dict = {}
    for marker in RECIPE_MARKERS:
        where = []
        for path in canonical_scan_targets(root):
            try:
                text = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if marker in text:
                where.append(path.relative_to(root).as_posix())
        hits[marker] = where
    return hits


class LearningClosureRecipeTests(unittest.TestCase):
    def setUp(self):
        self.text = DOC.read_text(encoding="utf-8")
        self.section = section_body(self.text, SECTION_4_HEADING)
        self.state_block = block_after_label(
            self.section.splitlines(), STATE_LABEL)
        self.error_block = block_after_label(
            self.section.splitlines(), ERROR_SEMANTICS_LABEL)
        self.contract = parse_closure_contract(self.state_block, self.error_block)

    # -- a clean record / the three illegal records -------------------------

    @staticmethod
    def legal_record(disposition: str = "accept") -> dict:
        return {
            "disposition": disposition,
            "reason": "the repeated failure mode is a durable engineering rule",
            "verification_ref": "commit:deadbeef + test_p1_t13_learning_closure",
        }

    @staticmethod
    def status_only_record() -> dict:
        return {"disposition": "fixed", "reason": "", "verification_ref": ""}

    # -- the recipe exists at all -------------------------------------------

    def test_the_canonical_owner_carries_the_closure_section(self):
        self.assertIn(
            SECTION_4_HEADING, self.text,
            f"RECIPE_ABSENT: {DOC_REL} does not carry {SECTION_4_HEADING!r}; "
            f"a status-only closure stays indistinguishable from a grounded one")
        self.assertTrue(
            self.section.strip(),
            f"RECIPE_ABSENT: {DOC_REL} section 4 is empty")

    def test_the_landed_sections_are_not_renamed_or_reordered(self):
        for heading in LANDED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(
                    heading, self.text,
                    f"{DOC_REL} lost the landed heading {heading!r}; no existing "
                    f"section may be renamed or renumbered")
        positions = [self.text.index(heading) for heading in LANDED_HEADINGS]
        self.assertEqual(
            positions, sorted(positions),
            f"{DOC_REL} landed headings must keep their order")
        self.assertIn(
            SECTION_4_HEADING, self.text,
            f"RECIPE_ABSENT: {DOC_REL} does not carry {SECTION_4_HEADING!r}")
        self.assertGreater(
            self.text.index(SECTION_4_HEADING),
            self.text.index(LANDED_HEADINGS[-1]),
            "the closure section must be appended after the landed section 3")

    def test_canonical_owner_literal_is_retained(self):
        self.assertIn(
            CANONICAL_OWNER_LITERAL, self.text,
            f"VALIDATOR_INVARIANT_VIOLATED: references-declare-canonical-owner "
            f"requires the literal {CANONICAL_OWNER_LITERAL!r} in {DOC_REL}")

    # -- the CE-18 anchor: present and unique BEFORE it is mutated -----------

    def test_the_ce_18_anchor_is_present_and_unique(self):
        self.assertEqual(
            self.text.count(CE_18_ANCHOR), 1,
            f"{DOC_REL}: the CE-18 anchor must appear exactly once; "
            f"count={self.text.count(CE_18_ANCHOR)}")
        self.assertIn(
            CE_18_ANCHOR, self.section,
            f"{DOC_REL} section 4 does not carry the CE-18 anchor")

    # -- the normative rules ------------------------------------------------

    def test_closure_requires_disposition_reason_and_verification(self):
        self.assertTrue(
            probe(self.section, CLOSURE_REQUIRES_BOTH_GROUPS),
            f"{DOC_REL} section 4 does not require an explicit accept-or-reject "
            f"disposition WITH a reason AND a verification reference")

    def test_status_only_closure_is_forbidden(self):
        self.assertTrue(
            probe(self.section, STATUS_ONLY_FORBIDDEN_GROUPS),
            f"{DOC_REL} section 4 does not forbid closing a learning entry with "
            f"a bare status assertion")

    def test_the_recipe_is_on_demand_and_not_a_per_ticket_field_set(self):
        self.assertTrue(
            probe(self.section, ON_DEMAND_GROUPS),
            f"{DOC_REL} section 4 does not state the recipe is on demand and "
            f"NOT a mandatory per-ticket field set")
        self.assertIn(
            "按需", self.section,
            f"{DOC_REL} section 4 never says the recipe is 按需 (on demand)")

    def test_no_new_global_enum_or_state_machine_is_introduced(self):
        self.assertTrue(
            probe(self.section, NO_SECOND_STATE_MACHINE_GROUPS),
            f"{DOC_REL} section 4 does not bound its accept/reject vocabulary "
            f"(no new global enum or state machine)")
        self.assertEqual(
            sorted(self.contract["legal_rows"]), ["accept", "reject"],
            f"the closure vocabulary must stay the minimal accept/reject pair; "
            f"parsed={sorted(self.contract['legal_rows'])}")

    def test_the_section_names_its_single_canonical_owner(self):
        self.assertTrue(
            probe(self.section, SINGLE_OWNER_GROUPS),
            f"{DOC_REL} section 4 does not declare itself the unique canonical "
            f"owner of the closure conditions")
        self.assertTrue(
            probe(self.section, POINTER_ONLY_GROUPS),
            f"{DOC_REL} section 4 does not state that other surfaces only point "
            f"at it")

    # -- the rendered state contract, parsed --------------------------------

    def test_the_state_contract_renders_two_legal_and_three_illegal_rows(self):
        legal = [line for line in self.state_block
                 if line.strip().startswith("LEGAL")]
        illegal = [line for line in self.state_block
                   if line.strip().startswith("ILLEGAL")]
        self.assertEqual(len(legal), 2, f"legal={legal}")
        self.assertEqual(len(illegal), 3, f"illegal={illegal}")
        self.assertEqual(
            sorted(self.contract["legal_rows"]), ["accept", "reject"],
            f"each legal row must be an explicit disposition; "
            f"parsed={sorted(self.contract['legal_rows'])}")

    def test_every_illegal_case_is_declared_as_a_rejection(self):
        expected = {"assertion_only", "missing_reason", "missing_verification"}
        self.assertEqual(
            self.contract["illegal_conditions"], expected,
            f"{DOC_REL} section 4 must declare all three illegal closure cases; "
            f"parsed={sorted(self.contract['illegal_conditions'])}")
        for line in self.state_block:
            stripped = line.strip()
            if not stripped.startswith("ILLEGAL"):
                continue
            with self.subTest(row=stripped):
                self.assertIn(
                    "拒绝", stripped,
                    f"an ILLEGAL closure row must be a rejection: {stripped!r}")

    def test_every_error_semantics_row_is_a_closed_invalidity(self):
        rows = self.contract["invalid_outcomes"]
        self.assertEqual(
            len(rows), 4,
            f"{DOC_REL} section 4 error semantics must render four rows; "
            f"rows={rows}")
        for row in rows:
            with self.subTest(row=row):
                self.assertTrue(
                    row.endswith(CLOSURE_INVALID),
                    f"an error-semantics row must end in {CLOSURE_INVALID!r}: "
                    f"{row!r}")
        joined = " | ".join(rows)
        for marker in ("disposition", "reason", "verification", "assertion-only"):
            with self.subTest(marker=marker):
                self.assertIn(
                    marker, joined,
                    f"{DOC_REL} section 4 error semantics lost the "
                    f"{marker!r} row; rows={rows}")

    # -- the state contract, executed ----------------------------------------

    def test_a_grounded_closure_is_accepted(self):
        for disposition in DISPOSITIONS:
            with self.subTest(disposition=disposition):
                self.assertEqual(
                    decide_closure(self.legal_record(disposition), self.contract),
                    LEGAL_VERDICT,
                    f"a {disposition} disposition with a reason and a verification "
                    f"reference must be legal")

    def test_a_status_only_closure_is_rejected(self):
        self.assertIn("assertion_only", self.contract["illegal_conditions"])
        self.assertEqual(
            decide_closure(self.status_only_record(), self.contract),
            REJECT_ASSERTION_ONLY,
            "CE-18: a learning entry closed with a bare status assertion "
            "(e.g. 'fixed') must be rejected")

    def test_a_closure_without_a_reason_is_rejected(self):
        record = self.legal_record()
        record["reason"] = ""
        self.assertEqual(
            decide_closure(record, self.contract), REJECT_MISSING_REASON,
            "a closure with no accept/reject reason must be rejected")

    def test_a_closure_without_a_verification_reference_is_rejected(self):
        record = self.legal_record()
        record["verification_ref"] = ""
        self.assertEqual(
            decide_closure(record, self.contract),
            REJECT_MISSING_VERIFICATION,
            "a closure with no verification reference must be rejected")

    def test_an_unrecognised_disposition_is_not_a_closure(self):
        record = self.legal_record()
        record["disposition"] = "done"
        self.assertEqual(
            decide_closure(record, self.contract), REJECT_ASSERTION_ONLY,
            "a status word is not a disposition: closure must be refused")

    # -- the landed promotion policy is untouched ---------------------------

    def test_the_promotion_policy_rows_are_unchanged(self):
        for row in PROMOTION_ROWS:
            with self.subTest(row=row[:40]):
                self.assertIn(
                    row, self.text,
                    f"{DOC_REL} section 1 lost a landed promotion-policy row")
        self.assertIn(
            PROMOTION_RECORD_FIELDS, self.text,
            f"{DOC_REL} section 1 lost the per-promotion record fields")
        self.assertNotIn(
            "PROMOTE", self.section,
            f"{DOC_REL} section 4 must not restate the promotion policy")
        self.assertNotIn(
            "DO NOT PROMOTE", self.section,
            f"{DOC_REL} section 4 must not restate the promotion policy")

    # -- the section declares no field name and no protected token ----------

    def test_the_section_introduces_no_field_name_token(self):
        found = sorted(set(FIELD_NAME_RE.findall(self.section)))
        self.assertEqual(
            found, [],
            f"{DOC_REL} section 4 must not introduce a field-name-shaped token "
            f"(no new field / enum name); found={found}")

    def test_relative_links_in_the_new_section_resolve(self):
        targets = [target.strip() for target in
                   MD_LINK_RE.findall(self.section)]
        for target in targets:
            with self.subTest(target=target):
                self.assertFalse(
                    target.startswith(("http://", "https://", "mailto:", "#")),
                    f"the recipe must not link off-repository: {target!r}")
                resolved = (DOC.parent / target.split("#")[0]).resolve()
                self.assertTrue(
                    resolved.exists(),
                    f"{DOC_REL} section 4 carries the broken relative link "
                    f"{target!r}")

    # -- single owner / single declaration point (AC-38, CE-28) -------------

    def test_the_recipe_is_declared_in_exactly_one_canonical_file(self):
        hits = scan_recipe_markers(ROOT)
        expected = {marker: [DOC_REL] for marker in RECIPE_MARKERS}
        self.assertEqual(
            hits, expected,
            f"CE-28: the closure recipe must be defined in exactly one "
            f"canonical owner; found={hits}")

    def test_the_single_owner_scan_is_not_vacuous(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "references").mkdir(parents=True)
            (root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
            (root / "RULES.md").write_text("# rules\n", encoding="utf-8")
            (root / "references/engineering-memory.md").write_text(
                "# owner\n" + "\n".join(RECIPE_MARKERS) + "\n",
                encoding="utf-8")
            self.assertEqual(
                scan_recipe_markers(root),
                {marker: [DOC_REL] for marker in RECIPE_MARKERS},
                "the declared single-owner baseline must be reproduced")
            (root / "references/competing-memory.md").write_text(
                "# competing owner\n" + "\n".join(RECIPE_MARKERS) + "\n",
                encoding="utf-8")
            hits = scan_recipe_markers(root)
            self.assertEqual(
                sorted(hits[CE_18_ANCHOR]),
                sorted([DOC_REL, "references/competing-memory.md"]),
                "SINGLE_OWNER_SCAN_VACUOUS: an injected second canonical owner "
                "went undetected")
            (root / "RULES.md").write_text(
                "# rules\n" + CE_18_ANCHOR + "\n", encoding="utf-8")
            self.assertIn(
                "RULES.md", scan_recipe_markers(root)[CE_18_ANCHOR],
                "the scan must also cover AGENTS.md / RULES.md")

    # -- anti-vacuity --------------------------------------------------------

    def test_every_probe_holds_for_the_live_document(self):
        self.assertTrue(self.section.strip(), "RECIPE_ABSENT: no section 4 body")
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                self.assertTrue(
                    probe(self.section, groups),
                    f"{DOC_REL} section 4: probe {name} is not satisfied by the "
                    f"live document")

    def test_every_probe_flips_red_under_a_targeted_mutation(self):
        """A rewritten normative statement must turn its probe RED."""
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                old, new = PROBE_MUTATIONS[name]
                self.assertTrue(
                    probe(self.section, groups),
                    f"{DOC_REL}: probe {name} must hold before the mutation")
                self.assertEqual(
                    self.section.count(old), 1,
                    f"{DOC_REL}: probe {name} is not anchored to unique "
                    f"document text; count({old!r})="
                    f"{self.section.count(old)}")
                mutated = self.section.replace(old, new)
                self.assertNotEqual(mutated, self.section)
                self.assertFalse(
                    probe(mutated, groups),
                    f"{DOC_REL}: probe {name} is VACUOUS -- rewriting "
                    f"{old!r} -> {new!r} did not turn it RED")

    def test_every_decision_flips_red_under_a_targeted_mutation(self):
        """Deleting a requirement or an illegal row must change the verdict."""
        record = self.legal_record()
        stripped_record = dict(record, verification_ref="")
        self.assertEqual(
            decide_closure(stripped_record, self.contract),
            REJECT_MISSING_VERIFICATION)

        # (a) the verification-reference requirement is deleted from the legal
        #     rows: the same ungrounded record is then accepted.
        for old, new in ((" + 验证引用", ""),):
            self.assertIn(old, self.section)
        no_verification = self.section.replace(" + 验证引用", "")
        contract = parse_closure_contract(
            block_after_label(no_verification.splitlines(), STATE_LABEL),
            block_after_label(no_verification.splitlines(), ERROR_SEMANTICS_LABEL))
        self.assertEqual(
            contract["legal_rows"]["accept"], frozenset({"reason"}),
            "the mutation did not remove the verification requirement")
        self.assertEqual(
            decide_closure(stripped_record, contract), LEGAL_VERDICT,
            "MUTATION_CONTROL_VACUOUS: dropping the verification-reference "
            "requirement did not change the verdict")

        # (b) the ILLEGAL row for a missing verification reference is deleted.
        without_row = "\n".join(
            line for line in self.section.splitlines()
            if not (line.strip().startswith("ILLEGAL")
                    and VERIFICATION_MARKER in line and "缺少" in line))
        self.assertNotEqual(without_row, self.section)
        contract = parse_closure_contract(
            block_after_label(without_row.splitlines(), STATE_LABEL),
            block_after_label(without_row.splitlines(), ERROR_SEMANTICS_LABEL))
        self.assertNotIn("missing_verification", contract["illegal_conditions"])
        self.assertEqual(
            decide_closure(stripped_record, contract), LEGAL_VERDICT,
            "MUTATION_CONTROL_VACUOUS: deleting the illegal 'missing "
            "verification reference' row did not change the verdict")

        # (c) the ILLEGAL row for an assertion-only closure is deleted.
        without_assertion = "\n".join(
            line for line in self.section.splitlines()
            if not (line.strip().startswith("ILLEGAL")
                    and "状态断言" in line))
        self.assertNotEqual(without_assertion, self.section)
        contract = parse_closure_contract(
            block_after_label(without_assertion.splitlines(), STATE_LABEL),
            block_after_label(without_assertion.splitlines(), ERROR_SEMANTICS_LABEL))
        self.assertNotIn("assertion_only", contract["illegal_conditions"])
        self.assertNotEqual(
            decide_closure(self.status_only_record(), contract),
            REJECT_ASSERTION_ONLY,
            "MUTATION_CONTROL_VACUOUS: deleting the illegal assertion-only row "
            "did not change the verdict")

    def test_probe_helper_requires_all_marker_groups_on_one_statement(self):
        groups = (("ALPHA",), ("BETA",))
        self.assertTrue(probe("ALPHA and BETA", groups))
        self.assertFalse(
            probe("ALPHA\nBETA", groups),
            "the probe helper must not be satisfiable by markers scattered "
            "across unrelated statements")

    def test_the_contract_parser_is_not_vacuous(self):
        self.assertTrue(
            self.contract["legal_rows"] and self.contract["illegal_conditions"],
            "the closure parser read no rules out of the live document")
        promoted = [
            line.replace("ILLEGAL  缺少验证引用", "LEGAL    缺少验证引用")
            for line in self.state_block]
        contract = parse_closure_contract(promoted, self.error_block)
        self.assertNotEqual(
            contract["illegal_conditions"], self.contract["illegal_conditions"],
            "the state-contract parser is VACUOUS: promoting an ILLEGAL row to "
            "LEGAL did not change the parsed conditions")


if __name__ == "__main__":
    unittest.main()
