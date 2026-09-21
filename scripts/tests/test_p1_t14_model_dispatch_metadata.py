"""Counterexample-driven regression checks for the model dispatch metadata
recipe in `references/skills-and-model-routing.md` section 4 (P1-T14,
REQ-W4-02e).

SUPPORT surface (RULES.md R6), NOT an authority surface. This module declares no
recipe field and no requirement of its own: it re-reads the canonical reference
and fails when the dispatch field group loses a field, loses its declared order,
lets the model tier precede risk, freezes a concrete model as an invariant,
stops resolving `MODEL_OR_TIER` through an updatable profile, restates the
AGENTS section 3 escalation trigger list instead of referencing it, or loses its
single canonical owner.

BINDING (references/ticket-lane.md section 4, counterexample-first)
    The recipe is a document fact: the declared field order is PARSED OUT OF the
    canonical file (one field name per line inside the section's field-group
    block), so reordering the rendered document reorders the parsed tuple and
    the positional risk-before-tier assertion flips. The `PROBES` table and its
    anti-vacuity mutations at the bottom rewrite one normative sentence in
    memory and require the probe to flip, so mutating the prose turns the suite
    RED instead of passing CI silently.

    The constants below (the approved field order, the escalation trigger
    inventory, the mutation anchors) are ASSERTION INPUTS -- a lock read back
    from the producer -- never a second declaration point of the recipe. The one
    normative declaration point of the field group is section 4 of the canonical
    owner; see `test_the_recipe_is_declared_in_exactly_one_canonical_file`.

    The recipe EXTENDS the landed section 2 principle `RISK FIRST, MODEL
    SECOND`; it must not rename, renumber or restate the landed sections 1..3,
    and it must not re-declare the escalation trigger inventory owned by
    `AGENTS.md` section 3 (it only references it). No new shared enum and no
    global state machine is introduced: the verdict set below is local to this
    recipe and never appears in the canonical text. None of the protected
    review-evidence tokens may appear.

Counterexamples exercised here (parent spec section 9): CE-28 (a recipe defined
in two canonical files has a dual owner and must be rejected and converged onto
one -- AC-38).

RED condition before P1-T14 lands: the canonical owner carries no dispatch field
group, so a dispatch record cannot be checked field by field and a model-first
ordering cannot be rejected. Every structural probe and every ordering assertion
FAILS.

Stdlib only. Run with:
    python3 -m unittest scripts.tests.test_p1_t14_model_dispatch_metadata
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROUTING_REL = "references/skills-and-model-routing.md"
ROUTING = ROOT / ROUTING_REL
AGENTS_REL = "AGENTS.md"
AGENTS = ROOT / AGENTS_REL

# The subsection this ticket adds: a new level-2 section after the landed
# section 3. No existing section is renamed or renumbered.
SECTION_4_HEADING = (
    "## 4. 派发元数据 recipe（MODEL_DISPATCH_METADATA；RISK FIRST, MODEL SECOND）")

# The landed sections 1..3 headings that must survive unchanged.
LANDED_HEADINGS = (
    "## 1. Skill 路由表（按流程阶段；2026-09-05 安装与契约核验）",
    "## 2. 模型路由（RISK FIRST, MODEL SECOND；D 层默认）",
    "## 3. 平台映射备注",
)

# The approved field group, in the approved order (parent spec section 3.4
# REQ-W4-02e). This tuple is an ASSERTION INPUT; the document is parsed back
# into it, it is never the declaration point.
FIELD_ORDER = (
    "ROLE", "TASK", "RISK", "MODEL_OR_TIER", "REASONING_EFFORT", "WHY",
    "EXPECTED_OUTPUT", "ESCALATE_IF",
)
RISK_FIELD = "RISK"
MODEL_FIELD = "MODEL_OR_TIER"
# The anchor used by the mutation controls: the field group as it must render.
FIELD_GROUP_SIGNATURE = "\n".join(FIELD_ORDER)
FIELD_GROUP_LABEL = "字段组**顺序即语义**"
STATE_LABEL = "本 recipe 的合法 / 非法集合"
RECIPE_ID = "MODEL_DISPATCH_METADATA"

CANONICAL_OWNER_LITERAL = "Canonical owner"

# The landed escalation-trigger sentence of section 2, byte-exact. The recipe
# must NOT alter it and must not re-enumerate the triggers.
ESCALATION_TRIGGER_LINE = (
    "- ESCALATION 触发清单 = AGENTS §3（架构不确定、并发/canonical、安全边界、"
    "评审分歧、Spec/governance、里程碑、高爆炸半径）。")
ESCALATION_INVENTORY_ANCHOR = "架构不确定性；并发/canonical 权威语义"
ESCALATION_TRIGGER_COUNT = 7

# The landed platform tier keys of section 3. The dispatch `MODEL_OR_TIER`
# domain is exactly this profile-key domain; a value outside it is a concrete
# model frozen into the text, not a dispatch value.
TIER_KEY_ANCHOR = "`model` 参数（"
TIER_KEY_RE = re.compile(r"`model` 参数（([^）]+)）")

# Protected review-evidence tokens (test_review_evidence_contract.py): none of
# them may be introduced into the canonical owner.
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
FIELD_LINE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
FROZEN_MODEL_RE = re.compile(r"MODEL_OR_TIER`?\s*[=＝]")


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


def declared_field_order(section_text: str):
    """The ordered field group exactly as the canonical owner renders it.

    Parsed, never assumed: one field name per line inside the section's
    field-group block. A reordered document yields a reordered tuple.
    """
    block = block_after_label(section_text.splitlines(), FIELD_GROUP_LABEL)
    return tuple(
        line.strip() for line in block if FIELD_LINE_RE.match(line.strip()))


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


def frozen_model_assignments(section_text: str):
    """Statements that freeze `MODEL_OR_TIER` to a literal value.

    The invariant text must give the field NO value: the concrete model is a
    profile value, so an assignment in the recipe text is exactly the
    unverifiable invariant the ticket forbids.
    """
    return [line for line in statements(section_text)
            if FROZEN_MODEL_RE.search(line)]


def platform_tier_keys(text: str):
    """Declared platform tier/profile keys, parsed out of section 3."""
    match = TIER_KEY_RE.search(text)
    if not match:
        return frozenset()
    return frozenset(
        part.strip() for part in match.group(1).split("/") if part.strip())


def escalation_inventory(text: str):
    """The escalation trigger inventory owned by `AGENTS.md` section 3."""
    for line in text.splitlines():
        if ESCALATION_INVENTORY_ANCHOR in line:
            body = line.strip().rstrip("。").rstrip("；")
            return tuple(
                part.strip() for part in body.split("；") if part.strip())
    return ()


# ==========================================================================
# the executable dispatch-record contract (STATE_CONTRACT / ERROR_SEMANTICS)
# ==========================================================================

# A closed verdict set LOCAL to this recipe. Deliberately not a shared enum and
# deliberately not a global state machine: the parent spec freezes only
# "missing field -> invalid" and "invalid ordering -> invalid".
VALID = "VALID"
INVALID_MISSING_FIELD = "INVALID_MISSING_FIELD"
INVALID_ORDERING = "INVALID_ORDERING"


def dispatch_verdict(record, order=FIELD_ORDER) -> str:
    """Dispose of an ordered dispatch record against the documented order.

    Fail-closed: the record must carry exactly the declared field group, in the
    declared order. A missing field is a missing-field reject; a complete but
    rearranged record is an ordering reject -- precisely the model-before-risk
    case the ticket forbids.
    """
    declared = tuple(order)
    recorded = tuple(record)
    if len(recorded) != len(declared) or set(recorded) != set(declared):
        return INVALID_MISSING_FIELD
    if recorded != declared:
        return INVALID_ORDERING
    return VALID


def resolve_model_tier(tier_ref, profile, domain):
    """Resolve a `MODEL_OR_TIER` reference through the profile.

    A reference is legal only when it names a tier of the DECLARED domain and
    the profile currently maps that tier to a concrete model. A value outside
    the declared domain cannot be re-verified against the profile, so it is a
    hard-coded concrete model -- a defect, not a dispatch value.
    """
    if tier_ref not in domain:
        return None
    return profile.get(tier_ref)


def hardcoded_model_defect(tier_ref, profile, domain) -> bool:
    """True when the recorded model cannot be re-verified against the profile."""
    return resolve_model_tier(tier_ref, profile, domain) is None


# Placeholder values only: this module names NO concrete model identifier, so
# the profile fixtures below are deliberately non-model strings.
def profile_fixture(domain, suffix: str):
    return {key: f"placeholder-value-{index}{suffix}"
            for index, key in enumerate(sorted(domain))}


def complete_value_record(tier_ref, order=FIELD_ORDER):
    record = {name: "placeholder-value" for name in order}
    record[MODEL_FIELD] = tier_ref
    return record


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


def markdown_declaration_points(root: Path,
                                signature: str = FIELD_GROUP_SIGNATURE):
    """Markdown files that render the dispatch field group (declaration scan)."""
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
# the normative rules of section 4, decomposed into marker groups
# ==========================================================================

RISK_FIRST_GROUPS = (
    ("RISK",),
    ("MODEL_OR_TIER",),
    ("必须先于",),
)

PROFILE_NOT_INVARIANT_GROUPS = (
    ("profile",),
    ("可更新",),
    ("不是不变量",),
)

MISSING_FIELD_GROUPS = (
    ("缺任一字段",),
    ("无效",),
)

INVALID_ORDERING_GROUPS = (
    ("顺序错误",),
    ("无效",),
)

HARDCODED_DEFECT_GROUPS = (
    ("不变量",),
    ("缺陷",),
    ("如实上报",),
)

ESCALATE_IF_REFERENCE_ONLY_GROUPS = (
    ("ESCALATE_IF",),
    ("AGENTS §3",),
    ("只引用",),
)

LOCAL_CLOSED_SET_GROUPS = (
    ("局部的",),
    ("不引入",),
    ("共享枚举",),
)

CE_28_GROUPS = (
    ("CE-28",),
    ("只在本文件定义一次",),
    ("不重复定义",),
)

TIER_BASED_DOMAIN_GROUPS = (
    ("MODEL_OR_TIER",),
    ("档位",),
    ("profile",),
)

PROBES = {
    "risk_is_recorded_before_the_model_tier": RISK_FIRST_GROUPS,
    "the_concrete_model_is_a_profile_value_not_an_invariant":
        PROFILE_NOT_INVARIANT_GROUPS,
    "a_missing_field_invalidates_the_dispatch_record": MISSING_FIELD_GROUPS,
    "an_invalid_ordering_invalidates_the_dispatch_record":
        INVALID_ORDERING_GROUPS,
    "a_hard_coded_model_invariant_is_a_defect_requiring_honest_reporting":
        HARDCODED_DEFECT_GROUPS,
    "escalate_if_references_the_agents_trigger_list_without_restating_it":
        ESCALATE_IF_REFERENCE_ONLY_GROUPS,
    "the_closed_invalid_set_is_local_and_introduces_no_shared_enum":
        LOCAL_CLOSED_SET_GROUPS,
    "counterexample_ce_28_is_stated": CE_28_GROUPS,
    "the_model_or_tier_domain_is_tier_and_profile_based":
        TIER_BASED_DOMAIN_GROUPS,
}

# Anti-vacuity mutations: each rewrites one normative sentence of the SAME live
# text and must flip its probe to False. Every mutation inverts an obligation or
# deletes a prohibition.
PROBE_MUTATIONS = {
    "risk_is_recorded_before_the_model_tier": (
        "`RISK` 必须先于 `MODEL_OR_TIER` 记录",
        "`MODEL_OR_TIER` 先于 `RISK` 记录"),
    "the_concrete_model_is_a_profile_value_not_an_invariant": (
        "**profile / 可更新值，不是不变量**", "**写死的不变量**"),
    "a_missing_field_invalidates_the_dispatch_record": (
        "缺任一字段 = 派发记录无效。", "缺任一字段可以接受。"),
    "an_invalid_ordering_invalidates_the_dispatch_record": (
        "顺序错误 = 派发记录无效。", "顺序错误可以容忍。"),
    "a_hard_coded_model_invariant_is_a_defect_requiring_honest_reporting": (
        "把不可核验的具体型号写死成不变量 = 缺陷，须如实上报，不得静默通过。",
        "把不可核验的具体型号写死成不变量 = 可以静默通过。"),
    "escalate_if_references_the_agents_trigger_list_without_restating_it": (
        "`ESCALATE_IF` **只引用** `AGENTS.md` §3 的 ESCALATION 触发清单",
        "`ESCALATE_IF` 自行重列 ESCALATION 触发清单"),
    "the_closed_invalid_set_is_local_and_introduces_no_shared_enum": (
        "合法 / 非法集合是**局部的**", "合法 / 非法集合是全局的"),
    "counterexample_ce_28_is_stated": (
        "本字段组**只在本文件定义一次**；其它 surface 只指针 / 链接，不重复定义。",
        "本字段组可在多个 canonical 文件各自定义。"),
    "the_model_or_tier_domain_is_tier_and_profile_based": (
        "`MODEL_OR_TIER` 记录的是**档位 / profile 引用**（§2 的档位名）",
        "`MODEL_OR_TIER` 记录具体型号"),
}


class ModelDispatchMetadataTests(unittest.TestCase):
    def setUp(self):
        self.text = ROUTING.read_text(encoding="utf-8")
        self.agents_text = AGENTS.read_text(encoding="utf-8")
        self.body = section_body(self.text, SECTION_4_HEADING)
        self.state_block = block_after_label(
            self.body.splitlines(), STATE_LABEL)

    # -- placement and scope of the new section ----------------------------

    def test_section_4_is_appended_after_the_landed_sections(self):
        self.assertIn(
            SECTION_4_HEADING, self.text,
            f"{ROUTING_REL} does not carry the dispatch metadata section "
            f"{SECTION_4_HEADING!r}")
        for heading in LANDED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertIn(
                    heading, self.text,
                    f"{ROUTING_REL} lost the landed heading {heading!r}; no "
                    f"existing section may be renamed or renumbered")
        positions = [self.text.index(h) for h in LANDED_HEADINGS]
        self.assertEqual(
            positions, sorted(positions),
            "the landed sections 1..3 must keep their order")
        self.assertGreater(
            self.text.index(SECTION_4_HEADING),
            self.text.index(LANDED_HEADINGS[-1]),
            "the new section must be appended after section 3")
        self.assertTrue(
            self.body.strip(), f"{ROUTING_REL} section 4 is empty")

    def test_the_field_group_anchor_renders_exactly_once(self):
        """The mutation-control anchor must exist before any control uses it."""
        self.assertEqual(
            self.text.count(FIELD_GROUP_SIGNATURE), 1,
            f"{ROUTING_REL} must render the field group exactly once; "
            f"found {self.text.count(FIELD_GROUP_SIGNATURE)}")
        self.assertEqual(
            self.text.count(SECTION_4_HEADING), 1,
            f"{ROUTING_REL} must carry exactly one section-4 heading")

    # -- the declared field group ------------------------------------------

    def test_the_declared_field_group_is_exactly_the_eight_approved_fields(self):
        declared = declared_field_order(self.body)
        self.assertEqual(
            len(declared), len(FIELD_ORDER),
            f"{ROUTING_REL} section 4 must declare exactly "
            f"{len(FIELD_ORDER)} fields; declared={declared}")
        self.assertEqual(
            set(declared), set(FIELD_ORDER),
            f"{ROUTING_REL} section 4 field set drifted; declared={declared}")
        self.assertEqual(
            len(set(declared)), len(declared),
            f"{ROUTING_REL} section 4 declares a duplicated field; "
            f"declared={declared}")

    def test_risk_precedes_the_model_tier_positionally_in_the_declared_order(self):
        """POSITIONAL: index(RISK) < index(MODEL_OR_TIER) in the DECLARED list."""
        declared = list(declared_field_order(self.body))
        self.assertIn(RISK_FIELD, declared, f"declared={declared}")
        self.assertIn(MODEL_FIELD, declared, f"declared={declared}")
        risk_index = declared.index(RISK_FIELD)
        model_index = declared.index(MODEL_FIELD)
        self.assertLess(
            risk_index, model_index,
            f"RISK FIRST, MODEL SECOND violated: index({RISK_FIELD})="
            f"{risk_index} must be < index({MODEL_FIELD})={model_index} in "
            f"{declared}")

    def test_the_declared_order_matches_the_approved_order(self):
        self.assertEqual(
            declared_field_order(self.body), FIELD_ORDER,
            f"{ROUTING_REL} section 4 declares a different field order than "
            f"the approved one")

    # -- the executable dispatch-record contract ---------------------------

    def test_a_complete_record_in_the_declared_order_is_valid(self):
        self.assertEqual(
            dispatch_verdict(FIELD_ORDER), VALID,
            "a complete dispatch field group recorded in the declared order "
            "must be valid")

    def test_each_missing_field_invalidates_the_dispatch_record(self):
        for index, field in enumerate(FIELD_ORDER):
            with self.subTest(missing=field):
                record = FIELD_ORDER[:index] + FIELD_ORDER[index + 1:]
                self.assertEqual(
                    dispatch_verdict(record), INVALID_MISSING_FIELD,
                    f"dropping {field} from the dispatch record must make it "
                    f"invalid; record={record}")

    def test_swapping_risk_and_the_model_tier_is_an_invalid_ordering(self):
        declared = list(FIELD_ORDER)
        risk_index = declared.index(RISK_FIELD)
        model_index = declared.index(MODEL_FIELD)
        declared[risk_index], declared[model_index] = (
            declared[model_index], declared[risk_index])
        self.assertEqual(
            set(declared), set(FIELD_ORDER),
            "the swap must keep the same field set, so the reject is an "
            "ORDERING reject and not a missing-field reject")
        self.assertEqual(
            dispatch_verdict(declared), INVALID_ORDERING,
            f"a record placing the model tier ahead of risk must be rejected as "
            f"an invalid ordering; record={declared}")

    def test_placing_the_model_tier_first_is_an_invalid_ordering(self):
        model_first = (MODEL_FIELD,) + tuple(
            f for f in FIELD_ORDER if f != MODEL_FIELD)
        self.assertEqual(
            model_first.index(MODEL_FIELD), 0,
            "control: the model tier must be recorded first in this record")
        self.assertEqual(
            dispatch_verdict(model_first), INVALID_ORDERING,
            f"the model must never be chosen before risk is recorded; "
            f"record={model_first}")

    def test_any_deviation_from_the_declared_order_is_an_invalid_ordering(self):
        declared = list(FIELD_ORDER)
        for index in range(1, len(declared)):
            with self.subTest(rotation=index):
                rotated = declared[index:] + declared[:index]
                self.assertEqual(
                    set(rotated), set(declared),
                    "control: a rotation keeps the field set intact")
                self.assertEqual(
                    dispatch_verdict(rotated), INVALID_ORDERING,
                    f"a record that deviates from the declared order must be "
                    f"rejected as an invalid ordering; record={rotated}")

    def test_an_incomplete_and_reordered_record_is_still_invalid(self):
        record = (MODEL_FIELD, RISK_FIELD, "ROLE")
        self.assertEqual(
            dispatch_verdict(record), INVALID_MISSING_FIELD,
            "a record that is both incomplete and reordered must be rejected")

    def test_the_verdict_helper_is_not_vacuous(self):
        """Success and failure are distinguishable on the same input set."""
        self.assertEqual(dispatch_verdict(FIELD_ORDER), VALID)
        self.assertNotEqual(
            dispatch_verdict(FIELD_ORDER), INVALID_MISSING_FIELD)
        self.assertNotEqual(dispatch_verdict(FIELD_ORDER), INVALID_ORDERING)

    # -- the model is a profile value, never an invariant ------------------

    def test_the_declared_tier_domain_is_parsed_and_non_empty(self):
        self.assertIn(
            TIER_KEY_ANCHOR, self.text,
            f"{ROUTING_REL} section 3 lost the platform tier-key anchor "
            f"{TIER_KEY_ANCHOR!r}; the tier domain cannot be derived")
        keys = platform_tier_keys(self.text)
        self.assertEqual(
            len(keys), 3,
            f"the declared platform tier/profile keys must stay intact; "
            f"parsed={sorted(keys)}")

    def test_a_field_value_drawn_from_the_tier_domain_resolves(self):
        domain = platform_tier_keys(self.text)
        profile = profile_fixture(domain, "-a")
        for key in sorted(domain):
            with self.subTest(tier=key):
                self.assertIsNotNone(
                    resolve_model_tier(key, profile, domain),
                    f"tier {key!r} must resolve through the profile")

    def test_a_profile_update_changes_the_model_without_editing_the_text(self):
        """PROFILE_NOT_INVARIANT: update the profile, leave the text untouched."""
        domain = platform_tier_keys(self.text)
        invariant_text = self.body
        profile_before = profile_fixture(domain, "-before")
        profile_after = profile_fixture(domain, "-after")
        for key in sorted(domain):
            with self.subTest(tier=key):
                before = resolve_model_tier(key, profile_before, domain)
                after = resolve_model_tier(key, profile_after, domain)
                self.assertIsNotNone(before, f"tier {key!r} must resolve")
                self.assertIsNotNone(after, f"tier {key!r} must resolve")
                self.assertNotEqual(
                    before, after,
                    f"a profile update must be able to change the concrete "
                    f"model for tier {key!r}")
        self.assertEqual(
            self.body, invariant_text,
            f"{ROUTING_REL} section 4 must not be edited to change the "
            f"concrete model: the model is a profile value, not an invariant")

    def test_a_hard_coded_concrete_model_value_is_a_defect(self):
        domain = platform_tier_keys(self.text)
        profile = profile_fixture(domain, "-a")
        frozen = "placeholder-not-a-declared-tier"
        self.assertNotIn(frozen, domain)
        self.assertTrue(
            hardcoded_model_defect(frozen, profile, domain),
            "a value outside the declared tier domain cannot be re-verified "
            "against the profile and must be reported as a defect")
        record = complete_value_record(frozen)
        self.assertEqual(
            dispatch_verdict(FIELD_ORDER), VALID,
            "control: the ordering is still valid, so the defect is the frozen "
            "model value and not the ordering")
        self.assertTrue(
            hardcoded_model_defect(record[MODEL_FIELD], profile, domain),
            "the frozen model value must be flagged on the record")

    def test_the_invariant_text_freezes_no_model_value(self):
        self.assertEqual(
            frozen_model_assignments(self.body), [],
            f"{ROUTING_REL} section 4 must give MODEL_OR_TIER no literal value; "
            f"found={frozen_model_assignments(self.body)}")
        injected = self.body + "\n- `MODEL_OR_TIER` = placeholder-concrete-model\n"
        self.assertNotEqual(
            frozen_model_assignments(injected), [],
            "HARDCODED_MODEL_SCAN_VACUOUS: an injected frozen model assignment "
            "went undetected")

    # -- the rendered legal / illegal closed set ---------------------------

    def test_the_closed_set_is_rendered_as_legal_and_illegal_rows(self):
        legal, illegal = state_entries(self.state_block)
        self.assertEqual(
            len(legal), 2,
            f"{ROUTING_REL} section 4 must render exactly two LEGAL rows; "
            f"legal={legal}")
        self.assertEqual(
            len(illegal), 2,
            f"{ROUTING_REL} section 4 must render exactly two ILLEGAL rows; "
            f"illegal={illegal}")
        for label, markers in (
                ("risk-before-tier completeness", ("RISK", "MODEL_OR_TIER")),
                ("profile-resolved model", ("profile", "不变量"))):
            with self.subTest(legal_case=label):
                row = next((r for r in legal
                            if all(m in r for m in markers)), None)
                self.assertIsNotNone(
                    row, f"section 4 lost the LEGAL row for {label}; "
                         f"legal={legal}")
        for label, markers in (
                ("missing field", ("缺", "字段")),
                ("hard-coded model invariant", ("不变量",))):
            with self.subTest(illegal_case=label):
                row = next((r for r in illegal
                            if all(m in r for m in markers)), None)
                self.assertIsNotNone(
                    row, f"section 4 lost the ILLEGAL row for {label}; "
                         f"illegal={illegal}")

    def test_the_closed_set_parser_is_not_vacuous(self):
        legal, illegal = state_entries(self.state_block)
        self.assertEqual((len(legal), len(illegal)), (2, 2))
        mutated = [
            line.replace("ILLEGAL  缺失任一字段", "LEGAL    缺失任一字段")
            for line in self.state_block]
        legal2, illegal2 = state_entries(mutated)
        self.assertNotEqual(
            (len(legal2), len(illegal2)), (2, 2),
            "the closed-set parser is VACUOUS: promoting an ILLEGAL row to "
            "LEGAL did not change the parsed sets")

    def test_the_recipe_introduces_no_new_shared_state_name(self):
        for name in (VALID, INVALID_MISSING_FIELD, INVALID_ORDERING):
            with self.subTest(name=name):
                self.assertNotIn(
                    name, self.body,
                    f"{ROUTING_REL} section 4 must not introduce the local "
                    f"verdict name {name} as a shared state name; the closed "
                    f"set stays local to this recipe")

    # -- the escalation trigger list is referenced, not restated -----------

    def test_the_escalation_trigger_list_is_unchanged(self):
        self.assertEqual(
            self.text.count(ESCALATION_TRIGGER_LINE), 1,
            f"{ROUTING_REL} section 2 must keep exactly one byte-exact "
            f"escalation-trigger sentence")
        inventory = escalation_inventory(self.agents_text)
        self.assertEqual(
            len(inventory), ESCALATION_TRIGGER_COUNT,
            f"{AGENTS_REL} section 3 must keep its escalation trigger "
            f"inventory; parsed={inventory}")

    def test_the_new_section_does_not_redeclare_the_escalation_triggers(self):
        self.assertNotIn(
            ESCALATION_INVENTORY_ANCHOR, self.body,
            f"{ROUTING_REL} section 4 must reference the AGENTS section 3 "
            f"trigger list, not re-enumerate it")
        self.assertNotIn(
            ESCALATION_TRIGGER_LINE, self.body,
            f"{ROUTING_REL} section 4 must not re-declare the section 2 "
            f"trigger sentence")

    # -- the landed machinery must survive ---------------------------------

    def test_canonical_owner_literal_is_retained(self):
        self.assertIn(
            CANONICAL_OWNER_LITERAL, self.text,
            f"{ROUTING_REL}: the literal {CANONICAL_OWNER_LITERAL!r} "
            f"declaration was removed")

    def test_the_landed_risk_first_principle_is_untouched(self):
        self.assertIn(
            "RISK FIRST, MODEL SECOND", self.text,
            f"{ROUTING_REL} lost the landed risk-first principle")
        self.assertIn(
            "按平台实际**档位**映射，不硬编码不可核验的具体型号：", self.text,
            f"{ROUTING_REL} section 2 lost its tier-mapping rule")
        self.assertIn(
            "| HIGH + ESCALATION 触发 | 最强可用推理档", self.text,
            f"{ROUTING_REL} section 2 lost a landed routing-table row")

    def test_no_protected_token_is_introduced(self):
        for token in PROTECTED_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(
                    token, self.body,
                    f"{ROUTING_REL} section 4 must not introduce the protected "
                    f"token {token}")

    # -- single owner / single declaration point (AC-38, CE-28) -------------

    def test_the_recipe_is_declared_in_exactly_one_canonical_file(self):
        points = markdown_declaration_points(ROOT)
        self.assertEqual(
            points, [ROUTING_REL],
            f"CE-28: the dispatch field group must be rendered exactly once, "
            f"in {ROUTING_REL}; found={points}")

    def test_the_recipe_identifier_appears_once_on_canonical_surfaces(self):
        hits = token_declaration_points(ROOT)
        self.assertEqual(
            hits, [ROUTING_REL],
            f"CE-28: {RECIPE_ID} must appear on exactly one canonical surface "
            f"({ROUTING_REL}); found={hits}")

    def test_the_dual_owner_detector_flags_a_second_copy(self):
        """Negative control: an injected second owner IS detected."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "references").mkdir(parents=True)
            owner = root / ROUTING_REL
            owner.write_text(
                "# routing\n\n" + FIELD_GROUP_SIGNATURE + "\n" + RECIPE_ID
                + "\n", encoding="utf-8")
            self.assertEqual(markdown_declaration_points(root), [ROUTING_REL])
            self.assertEqual(token_declaration_points(root), [ROUTING_REL])

            second = root / "references/competing-dispatch-recipe.md"
            second.write_text(
                "# competing owner\n\n" + FIELD_GROUP_SIGNATURE + "\n"
                + RECIPE_ID + "\n", encoding="utf-8")
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
                RECIPE_ID + "\n" + FIELD_GROUP_SIGNATURE + "\n",
                encoding="utf-8")
            self.assertEqual(
                token_declaration_points(root), [],
                "a test surface asserts on a declared fact; it does not "
                "declare it (the declared exclusion must hold)")

    def test_the_declared_order_parser_is_not_vacuous(self):
        """Reordering the rendered block must reorder the parsed tuple."""
        declared = declared_field_order(self.body)
        self.assertEqual(declared, FIELD_ORDER)
        block = block_after_label(self.body.splitlines(), FIELD_GROUP_LABEL)
        lines = [line for line in block if line.strip()]
        self.assertEqual(
            len(lines), len(FIELD_ORDER),
            f"the field-group block must render one field per line; "
            f"lines={lines}")
        reordered = (
            SECTION_4_HEADING + "\n" + FIELD_GROUP_LABEL + "：\n```text\n"
            + "\n".join(reversed(lines)) + "\n```\n")
        parsed = declared_field_order(reordered)
        self.assertEqual(
            parsed, tuple(reversed(FIELD_ORDER)),
            f"ORDER_PARSER_VACUOUS: reversing the rendered field block did not "
            f"reorder the parsed field list; parsed={parsed}")
        self.assertGreater(
            parsed.index(RISK_FIELD), parsed.index(MODEL_FIELD),
            "control: the reversed rendering places the model tier ahead of "
            "risk, which is exactly the ordering the positional test rejects")

    # -- anti-vacuity -------------------------------------------------------

    def test_every_probe_holds_for_the_live_document(self):
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                self.assertTrue(
                    probe(self.body, groups),
                    f"{ROUTING_REL} section 4: probe {name} is not satisfied by "
                    f"the live document")

    def test_every_probe_flips_red_under_a_targeted_mutation(self):
        """A mutated normative sentence must turn its probe RED (not vacuous)."""
        self.assertEqual(
            self.text.count(FIELD_GROUP_SIGNATURE), 1,
            "the mutation-control anchor must exist exactly once before any "
            "control uses it")
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                old, new = PROBE_MUTATIONS[name]
                self.assertTrue(
                    probe(self.body, groups),
                    f"{ROUTING_REL}: probe {name} must hold on the live text "
                    f"before the mutation is attempted")
                self.assertIn(
                    old, self.body,
                    f"{ROUTING_REL}: probe {name} is not anchored to document "
                    f"text; the expected marker {old!r} is absent")
                mutated = self.body.replace(old, new)
                self.assertNotEqual(mutated, self.body)
                self.assertFalse(
                    probe(mutated, groups),
                    f"{ROUTING_REL}: probe {name} is VACUOUS - mutating "
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
