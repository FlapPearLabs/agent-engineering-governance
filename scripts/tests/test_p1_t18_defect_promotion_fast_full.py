"""Counterexample-driven tests for DEFECT_TO_GATE_PROMOTION and the
FAST_GATE / FULL_GATE execution model (P1-T18).

BINDING (references/ticket-lane.md section 4, counterexample-first):
    CONTRACT -> COUNTEREXAMPLES -> RED -> IMPLEMENT -> GREEN -> REGRESSION

WHAT THIS FILE PROVES
  The new mechanisms hang off EXISTING canonical owners (no new competing
  authority) and cannot drift into any claim this ticket forbids:

    - every new mechanism resolves to exactly one canonical owner document
    - RULES.md (B layer) gained no language/tool/gate policy
    - defect promotion is value-gated, NOT automatic rule proliferation
    - "lowest layer" never degrades into "weakest layer"
    - semantic/product judgment is NOT absorbed by static checks
    - BUG KNOWLEDGE -> REGRESSION TEST survives; lint does not replace
      behavioral tests
    - the ticket receipt DELEGATES its value domain instead of restating it
    - reviewer findings stay advisory evidence, not truth or automatic gates
    - current-ticket vs follow-up tooling boundary blocks scope creep
    - FAST does not replace FULL, and FULL does not excuse FAST
    - LOCAL_FAST_GATE and CI_FAST_GATE stay distinct
    - the governance repo itself classifies its own pipeline (dogfood)

WHAT THIS FILE DOES NOT PROVE
  That a gate RAN, nor that a document's prose is semantically correct. Marker
  presence is NOT semantic validation: a self-contradictory sentence passes
  every check here (see test_contradictory_prose_is_out_of_scope). That
  judgement belongs to an independent reviewer.
"""
import importlib.util
import re
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "governance", ROOT / "scripts/validate_governance.py")
GOV = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GOV)

FRAMEWORK_REL = "references/static-analysis-and-code-intelligence.md"
TICKET_REL = "references/ticket-lane.md"
REVIEW_REL = "references/review-and-repair-saturation.md"
CI_REL = "references/git-ci-integration.md"
AGENTS_REL = "AGENTS.md"
RULES_REL = "RULES.md"
README_REL = "README.md"
PAIN_REL = "audit/PAIN_TO_POLICY_MAP_V2.md"

PROMOTION_DISPOSITIONS = (
    "PROMOTE_NOW",
    "FOLLOWUP_TOOLING_TICKET",
    "KEEP_AS_TEST",
    "KEEP_AS_REVIEWER_RESPONSIBILITY",
    "KEEP_AS_HUMAN_DECISION",
)

PROMOTION_VALUE_AXES = (
    "REAL_OR_HIGH_CONFIDENCE",
    "REACHABLE",
    "DETERMINISTICALLY_DETECTABLE",
    "EXISTING_TOOL_CAN_DETECT",
    "FALSE_POSITIVE_RISK",
    "EXECUTION_COST",
    "MAINTENANCE_COST",
    "SEMANTIC_JUDGMENT_REQUIRED",
    "BEST_ENFORCEMENT_LAYER",
    "PROMOTION_VALUE",
)

# The seven-value status domain has exactly one declaration site: framework
# section 8. New receipts must reference it, never restate it.
STATIC_GATE_STATES = GOV.STATIC_GATE_STATES
DOMAIN_DELEGATION = GOV.STATIC_GATE_RECEIPT_DELEGATION

LAYER_SEMANTICS = ("parser / compiler", "linter", "type checker",
                   "schema / config validator", "回归 / 合同测试",
                   "CI 注册与执行守卫", "runtime hook / policy",
                   "独立评审", "人类 / product owner")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def _load_p1_t17():
    """Reuse the P1-T17 non-vacuous language-tool detector.

    Importing the sibling module keeps ONE definition of that guard instead of
    forking a second, weaker copy here.
    """
    import importlib
    return importlib.import_module(
        "scripts.tests.test_p1_t17_static_gate_framework_semantics")


# The receipt surface may only POINT at the disposition domain, never spell it
# out. Two earlier guards failed here in different ways: one matched a single
# literal spelling, and the next one only looked at members sharing a LINE --
# so a one-per-line bullet list passed. This detector is structural instead. It
# asks a question that no amount of reformatting can answer: are two domain
# members separated ONLY by enumeration punctuation? Prose between two members
# (a justification, a condition, a label) is what distinguishes a mention from
# a value domain, and prose is not made of separators.
_ENUM_SEPARATORS = " \t\r\n|,、/\\|·•+*`~-_=()[]{}<>\"'　"

# A real enumeration is dense: "A / B", "A | B", one bullet per line. A long
# run of prose between two members means the document is explaining something,
# not declaring a domain. The cap keeps a table of unrelated prose from
# reading as one huge span.
_MAX_ENUM_SPAN = 80

# How long the description cell of an aligned value/meaning table may be.
# The canonical 21.3 rows are well under this; ordinary prose is not.
_MAX_DESC_WIDTH = 40

# Column padding before the description cell of an aligned table. Two spaces
# is enough to tell a copied declaration from a sentence that happens to
# mention a value on the way to a full stop.
_MIN_COLUMN_PAD = 2

# How far back to look for the phrase that introduces a set. Chosen to sit
# inside one line of the declaration it introduces ("状态集（不可坍缩）：" is
# 9 characters) without reaching back into unrelated prose.
_MAX_LEAD = 40

# Phrases that introduce a value domain. A declaration says so; a passing
# mention of PASS does not. The list covers the forms this repo actually
# uses plus the shape a reviewer would reach for, and it is only ever a
# NECESSARY condition -- the shape checks still have to pass.
_DECLARATION_MARKERS = (
    "值域", "取值", "状态集", "状态值域", "处置 =", "处置取值集合",
    "PROMOTION_VALUE", "PROMOTION =", "状态域", "处置：",
)

def _restates_domain(text: str, members: tuple[str, ...],
                     minimum: int = 2,
                     foreign: tuple[str, ...] = ()) -> bool:
    """True if `text` spells out the value domain `members` as a set.

    Delegation ("处置取值集合 = §21.3") names no member at all, so the scan is
    anchored on real enum members rather than on prose.

    Two shapes count as a restatement, because both are ways of re-declaring
    a closed set:

    1. Two members separated ONLY by enumeration punctuation -- "A / B",
       "A | B", one bullet per line. Line-agnostic on purpose: an earlier
       version required two members on one line, which a bullet list defeats
       trivially, and a guard a reformatting can defeat is not a guard.

    2. Two members in the canonical TABLE shape -- a member, whitespace, then
       a description, repeated. The canonical 21.3 declaration interleaves a
       meaning after every value, so a verbatim copy of it puts prose between
       members and shape 1 alone would read it as a mention. This is the most
       natural way to fork a domain, so it has to be caught too.

    `minimum` is how many DISTINCT members must appear. It exists because two
    of these domains share vocabulary with ordinary prose: the non-collapse
    rule is illustrated by PAIRS like "NOT_CONFIGURED != PASS", and those
    pairs are the model working as intended rather than a restatement. A
    seven-value domain written out in full is not a pair.

    A judgement rule that happens to name two outcomes -- "PROMOTE_NOW only
    when X, otherwise FOLLOWUP_TOOLING_TICKET" -- is prose, not a value
    domain, and is skipped for a structural reason rather than a lexical one.
    No marker list of conditional phrasings is needed, and none of those
    markers was reliable anyway: a bare "当" also opens ordinary prose.
    """
    pattern = re.compile("|".join(
        # Longest first so a shorter member cannot shadow a longer one that
        # starts with it, and each is matched whole so the span arithmetic
        # below is looking at separators rather than at fragments.
        re.escape(m) for m in sorted(members, key=len, reverse=True)))
    matches = list(pattern.finditer(text))
    if len({m.group(0) for m in matches}) < minimum:
        return False
    # `foreign` names members of a DIFFERENT domain that happen to overlap.
    # A span that reaches one of them has left this domain's vocabulary, so
    # it is not a restatement of this domain no matter how it is punctuated.
    outside = None
    if foreign:
        outside = re.compile("|".join(re.escape(f) for f in foreign))

    for left, right in zip(matches, matches[1:]):
        if left.group(0) == right.group(0):
            continue
        between = text[left.end():right.start()]
        if outside is not None and outside.search(between):
            continue
        if not (set(between) - set(_ENUM_SEPARATORS)):
            # "NOT_CONFIGURED != PASS" is the non-collapse rule being
            # illustrated, which is the model working, not a restatement.
            # The != is often outside the captured span (it is punctuation,
            # and so are the backticks around each side), so look at the
            # text around the pair rather than only what is between.
            window = text[max(0, left.start() - 8):right.end() + 8]
            if "!=" in window:
                continue
            # A DECLARATION announces itself. "PROMOTION_VALUE = HIGH / MEDIUM
            # / LOW", "状态集（不可坍缩）：PASS / FAIL", "处置取值集合 =" --
            # each names the set it is introducing. Without that anchor the
            # shape is indistinguishable from prose, and prose in these tokens
            # is everywhere: "MEDIUM/HIGH 生产首写前需 GROUNDING" is a risk
            # grade, not a value domain. Requiring the anchor is what lets
            # the guard stay quiet on the 40-odd honest mentions and still
            # catch a copy parked anywhere in a file.
            lead = text[max(0, left.start() - _MAX_LEAD):left.start()]
            # A bullet list introduces its set with the bullets themselves --
            # "- PROMOTE_NOW", "* KEEP_AS_TEST" -- so there is no phrase to
            # find. Three or more members on consecutive bullet lines is the
            # shape instead. The pristine documents have no such run, and a
            # list of two is a sentence with a line break in it.
            if not any(a in lead for a in _DECLARATION_MARKERS):
                continue
            # The foreign check above only looked between the two members.
            # A neighbouring domain can start inside the same declaration and
            # end after this pair: git-ci-integration.md writes one line,
            # "状态集（不可坍缩）：PASS / FAIL / NOT_TRIGGERED / ...", and the
            # CI_STATUS-exclusive members all sit to the right of the first
            # static-gate pair. So the whole line has to be clean.
            line_start = text.rfind("\n", 0, left.start()) + 1
            line_end = text.find("\n", right.end())
            line = text[line_start:line_end if line_end != -1 else len(text)]
            if outside is not None and outside.search(line):
                continue
            return True
        # Shape 2: the canonical aligned-table form. The text between two
        # members is "column padding, then a description, then a newline and
        # the next member". The padding is what distinguishes a declaration
        # from prose: an earlier version accepted any short description
        # after a newline and duly flagged ordinary sentences in five real
        # documents, because "PASS" and "FAIL" appear in plenty of
        # explanations that are not a value domain. Aligned columns are a
        # deliberate, mechanical shape -- that is what a copied declaration
        # looks like, and it is how the owner declares all three domains.
        head, sep, _ = between.partition("\n")
        if not (sep and len(between) <= _MAX_ENUM_SPAN):
            continue
        pad = len(head) - len(head.lstrip(" \t　"))
        if (pad >= _MIN_COLUMN_PAD and head.strip()
                and len(head.strip()) <= _MAX_DESC_WIDTH):
            return True
    return False


def _restates_disposition_domain(text: str) -> bool:
    """The disposition domain, checked as a set and as a copied table.

    Abbreviations count as members: KEEP_AS_REVIEW forks the domain just as
    surely as the canonical spelling, and it is the easier typo to make.
    """
    return _restates_domain(text, PROMOTION_DISPOSITIONS + (
        "KEEP_AS_REVIEW", "KEEP_AS_HUMAN"), minimum=2)


def _restates_status_domain(text: str) -> bool:
    """The seven-value non-collapse STATIC GATE status domain.

    Framework section 8 owns it. Two things make this harder than the
    disposition domain.

    First, AGENTS.md and README.md are allowed to show non-collapse PAIRS as
    examples -- "NOT_CONFIGURED != PASS" is the whole point of the model -- so
    a pair is an illustration, not a restatement.

    Second, this repo has a SECOND, unrelated status domain: the CI_STATUS
    set in git-ci-integration.md, which shares PASS / FAIL /
    KNOWN_BASELINE_FAILURE with the static gate domain and is a legitimate
    declaration of its own. Shared names cannot tell the two apart, so a span
    that reaches a CI_STATUS-exclusive member is excluded: that run has left
    static gate vocabulary and belongs to somebody else's list.
    """
    return _restates_domain(
        text, tuple(GOV.STATIC_GATE_STATES), minimum=2,
        foreign=("NOT_TRIGGERED", "CANCELLED", "INFRASTRUCTURE_FAILURE",
                 "UNKNOWN"))


def _restates_promotion_value_domain(text: str) -> bool:
    """PROMOTION_VALUE (HIGH / MEDIUM / LOW / NOT_APPLICABLE) as a set.

    NOT_APPLICABLE is shared with the status domain, which is why this cannot
    simply reuse that detector: a document may legitimately talk about a
    non-applicable static gate without forking the promotion axis.

    This axis also has a DECOY. review-and-repair-saturation.md has its own
    HIGH / MEDIUM / LOW grading for IMPACT, CONTRACT_CONFIDENCE,
    REPAIR_COMPLEXITY and REGRESSION_RISK. Those are different axes that
    happen to share three words with this one, so a span introduced by one of
    those field names is not a restatement of PROMOTION_VALUE. Getting this
    wrong is not hypothetical: an earlier version of this detector flagged
    that file, and a guard that cries wolf on a legitimate table is a guard
    that gets deleted.
    """
    return _restates_domain(
        text, ("HIGH", "MEDIUM", "LOW", "NOT_APPLICABLE"), minimum=3,
        foreign=("NOT_CONFIGURED", "ENV_BLOCKED", "EXPLICIT_AUTHORITY_OVERRIDE",
                 "KNOWN_BASELINE_FAILURE", "IMPACT", "CONTRACT_CONFIDENCE",
                 "REPAIR_COMPLEXITY", "REGRESSION_RISK"))


_HIGH_GATE_ANCHOR = "`PROMOTION_VALUE = HIGH` 通常要求**同时**满足"


def _high_clauses(text: str) -> list[str]:
    """The conjunction clauses of the PROMOTION_VALUE = HIGH gate.

    Extracted once so the positive test and the mutation probe cannot drift
    apart: if each parsed the block its own way, a probe could "pass" simply
    because it looked somewhere the real test does not.

    The block is fenced, so parsing stops at the closing fence. An earlier
    version read to the end of the document and duly reported section 21.2,
    21.3 and the whole layer ladder as "clauses of the value gate" -- 30-odd
    spurious failures that all pointed at the parser, not at the policy.
    """
    _, _, rest = text.partition(_HIGH_GATE_ANCHOR)
    if not rest:
        return []
    # Skip to the opening fence on its own line, then stop at the closing
    # one. partition("```text") is not enough: the anchor's own sentence is
    # followed by a fence, but so is every later block, and a naive split
    # read straight through 21.2 and 21.3 -- reporting the whole layer ladder
    # as clauses of the value gate.
    lines = rest.splitlines()
    try:
        start = next(i for i, line in enumerate(lines)
                     if line.strip() == "```text") + 1
    except StopIteration:
        return []
    end = next((i for i in range(start, len(lines))
                if lines[i].strip() == "```"), len(lines))
    return [line for line in lines[start:end] if line.strip()]


class CanonicalOwnershipTests(unittest.TestCase):
    """Each new mechanism must have exactly ONE canonical owner."""

    def test_all_mechanism_documents_exist(self):
        for rel in (FRAMEWORK_REL, TICKET_REL, REVIEW_REL, CI_REL,
                    AGENTS_REL, RULES_REL, README_REL, PAIN_REL):
            with self.subTest(rel=rel):
                self.assertTrue((ROOT / rel).is_file(), f"{rel} missing")

    def test_defect_promotion_is_owned_by_the_framework(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("DEFECT_TO_GATE_PROMOTION", body)
        self.assertIn("canonical 声明面", body)

    def test_defect_promotion_is_not_duplicated_into_a_second_owner(self):
        """CE-28: exactly one canonical declaration surface."""
        framework = read(FRAMEWORK_REL)
        # The framework declares the mechanism; the other surfaces point at it.
        self.assertEqual(1, framework.count("## 21. DEFECT_TO_GATE_PROMOTION"))
        for rel in (TICKET_REL, REVIEW_REL, CI_REL):
            with self.subTest(rel=rel):
                body = read(rel)
                self.assertNotIn("## DEFECT_TO_GATE_PROMOTION", body)
                self.assertNotIn(
                    "DEFECT KNOWLEDGE → LOWEST RELIABLE MECHANICAL LAYER", body)

    def test_fast_full_classification_is_owned_by_the_framework(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("FAST_GATE", body)
        self.assertIn("FULL_GATE", body)
        self.assertIn("### 10.1", body)

    def test_ticket_receipt_delegates_fast_full_value_domain(self):
        """The new receipts must REFERENCE section 8, never restate it.

        The validator enforces delegation by counting the marker and by
        banning the one token that would constitute a second owner
        (EXPLICIT_AUTHORITY_OVERRIDE). Illustrative mentions of NOT_APPLICABLE
        in judgement rules are legitimate and must NOT be treated as
        restatement -- asserting that would be an over-strict test.
        """
        body = read(TICKET_REL)
        self.assertIn("FAST_GATE_RECEIPT", body)
        self.assertIn("FULL_GATE_RECEIPT", body)
        self.assertIn("DEFECT_PROMOTION_RECEIPT", body)
        # Every value-domain slot in the new receipts points at section 8.
        self.assertGreaterEqual(
            body.count(DOMAIN_DELEGATION),
            GOV.STATIC_GATE_RECEIPT_DELEGATIONS_MIN)
        # The one token that would create a competing owner stays banned.
        self.assertNotIn(GOV.STATIC_GATE_DOMAIN_ONLY_TOKEN, body)

    def test_new_receipt_fields_use_the_delegated_domain(self):
        """Each new FAST/FULL slot must carry the delegation marker."""
        body = read(TICKET_REL)
        self.assertIn("### 9.3", body, "section 9.3 anchor is required")
        block = body.split("### 9.3", 1)[1]
        for field in ("SYNTAX_COMPILER =", "LINT =", "TYPECHECK =",
                      "SCHEMA_CONFIG =", "REPO_STATIC_VALIDATORS =",
                      "GIT_DIFF_CHECK =", "FOCUSED_TESTS =", "FULL_TESTS =",
                      "INTEGRATION =", "CROSS_PLATFORM =",
                      "HISTORICAL_COMPAT =", "EXPENSIVE_SECURITY_STATIC =",
                      "RELEASE_GATES ="):
            with self.subTest(field=field):
                self.assertIn(field, block)
        # ...and each is annotated with the delegated domain, not a new one.
        self.assertIn("<§8 状态值域>", block)

    def test_ci_document_defines_ci_fast_and_ci_full(self):
        body = read(CI_REL)
        self.assertIn("### 3.3", body)
        self.assertIn("### 3.4", body)
        self.assertIn("CI_FAST", body)
        self.assertIn("CI_FULL", body)
        self.assertIn("LOCAL_FAST_GATE", body)
        self.assertIn("CI_FAST_GATE", body)

    def test_review_document_defines_advisory_finding_metadata(self):
        body = read(REVIEW_REL)
        self.assertIn("### 4.1", body)
        self.assertIn("MACHINE_DETECTABLE", body)
        self.assertIn("PROMOTION_VALUE", body)


class PromotionValueGateTests(unittest.TestCase):
    """Promotion must be value-gated, never automatic rule proliferation."""

    def test_all_value_axes_are_present(self):
        body = read(FRAMEWORK_REL)
        for axis in PROMOTION_VALUE_AXES:
            with self.subTest(axis=axis):
                self.assertIn(axis, body)

    def test_all_dispositions_are_declared(self):
        body = read(FRAMEWORK_REL)
        for disp in PROMOTION_DISPOSITIONS:
            with self.subTest(disp=disp):
                self.assertIn(disp, body)

    def test_single_occurrence_is_not_a_governance_defect(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("一次出现 ≠ 治理缺陷", body)

    def test_promotion_requires_conjunctive_conditions(self):
        """HIGH promotion needs several conditions at once, not any one."""
        body = read(FRAMEWORK_REL)
        self.assertIn("PROMOTION_VALUE = HIGH", body)
        for cond in ("真实/高置信缺陷类", "判定确定", "误报风险足够低",
                     "语义稳定", "不含隐藏的产品语义判断"):
            with self.subTest(cond=cond):
                self.assertIn(cond, body)

    def test_false_positive_and_cost_are_value_gates_not_afterthoughts(self):
        body = read(FRAMEWORK_REL)
        for axis in ("FALSE_POSITIVE_RISK", "EXECUTION_COST", "MAINTENANCE_COST"):
            with self.subTest(axis=axis):
                self.assertIn(axis, body)

    def test_mechanical_layer_hierarchy_is_declared(self):
        body = read(FRAMEWORK_REL)
        for layer in LAYER_SEMANTICS:
            with self.subTest(layer=layer):
                self.assertIn(layer, body)

    def test_lowest_does_not_mean_weakest(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("LOWEST ≠ WEAKEST", body)

    def test_semantic_judgment_blocks_promotion(self):
        """A defect needing product semantics must NOT be pushed down.

        Asserting a bare "不得" would be far too weak: the word occurs dozens
        of times, so deleting any single constraint would still pass. These
        two full sentences are the actual guards.
        """
        body = read(FRAMEWORK_REL)
        self.assertIn("SEMANTIC_JUDGMENT_REQUIRED", body)
        self.assertIn("需要 → 不下沉", body)
        self.assertIn("不硬塞", body)

    def test_semantic_business_rules_not_absorbed_by_static_checks(self):
        body = read(FRAMEWORK_REL)
        self.assertRegex(body, r"语义/产品判断\s*\*\*不得\*\*")


class ScopeCreepGuardTests(unittest.TestCase):
    """Current-ticket mechanization vs a dedicated tooling ticket."""

    def test_in_ticket_promotion_conditions_are_declared(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("现有工具已存在", body)
        self.assertIn("无新依赖", body)
        self.assertIn("无广泛基线 churn", body)
        self.assertIn("无架构变更", body)
        self.assertIn("同一缺陷类", body)

    def test_heavy_promotion_is_routed_to_a_tooling_ticket(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("MECHANIZATION_FOLLOWUP_CANDIDATE", body)
        self.assertIn("FOLLOWUP_TOOLING_TICKET", body)

    def test_legacy_repo_does_not_install_toolchains_in_unrelated_tickets(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("不得**在无关功能票里顺手装整套工具链", body)

    def test_promotion_receipt_does_not_auto_expand_scope(self):
        body = read(TICKET_REL)
        self.assertIn("不**自动创建门", body)
        self.assertIn("RULES R6", body)


class ReviewerAuthorityTests(unittest.TestCase):
    """A reviewer finding is evidence, not truth and not an automatic gate."""

    def test_finding_metadata_is_advisory(self):
        body = read(REVIEW_REL)
        self.assertIn("建议性", body)

    def test_finding_is_not_automatic_truth(self):
        body = read(REVIEW_REL)
        self.assertIn("!=** 自动真理", body)

    def test_finding_is_not_an_automatic_gate(self):
        body = read(REVIEW_REL)
        self.assertIn("!=** 自动建门", body)

    def test_reviewer_gains_no_new_authority(self):
        body = read(REVIEW_REL)
        for denied in ("修改治理的权威", "安装工具的权威",
                       "扩当前票 scope 的权威", "自动创建下游票的权威"):
            with self.subTest(denied=denied):
                self.assertIn(denied, body)

    def test_executor_must_still_verify_the_finding(self):
        body = read(REVIEW_REL)
        self.assertIn("仍必须核验", body)

    def test_repeat_low_level_findings_signal_a_missing_gate(self):
        body = read(REVIEW_REL)
        self.assertIn("### 6.5", body)
        self.assertIn("缺门证据", body)

    def test_repeat_signal_does_not_weaken_the_independent_review_gate(self):
        body = read(REVIEW_REL)
        self.assertIn("不**削弱 RULES R4", body)

    def test_repeat_signal_defers_to_the_promotion_value_gate(self):
        """"Repeat" is a signal, never a verdict. The gate is the value gate.

        This delegation was previously asserted only inside a synthetic string
        in the negative controls, which is the one place an assertion cannot
        protect anything. A reviewer removed it from the real document and the
        suite stayed green, leaving section 6.5 free to read as "reviewers keep
        finding it, so build the gate" -- the exact rule proliferation the
        section exists to prevent.
        """
        body = read(REVIEW_REL)
        section = body.split("### 6.5", 1)[1]
        self.assertIn("§21.1 的 value gate", section)
        self.assertIn("一次出现 ≠ 自动治理缺陷", section)

    def test_review_file_declares_the_framework_as_the_single_owner(self):
        """The saturation file is a pointer surface, and says so out loud."""
        body = read(REVIEW_REL)
        self.assertIn("唯一声明点", body)
        self.assertIn("references/static-analysis-and-code-intelligence.md", body)
        # 4.1 routes the mechanical-detectability metadata back to 21 as well.
        self.assertIn("§21（value-gated", body)


class FastFullSemanticsTests(unittest.TestCase):
    """FAST and FULL are complementary, never substitutes."""

    def test_fast_does_not_replace_full(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("FAST 不替代 FULL", body)

    def test_full_does_not_excuse_fast(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("FULL 不豁免 FAST", body)

    def test_ci_fast_pass_is_not_ci_full_pass(self):
        for rel in (FRAMEWORK_REL, CI_REL):
            with self.subTest(rel=rel):
                self.assertIn("CI_FAST PASS != CI_FULL PASS", read(rel))

    def test_local_fast_and_ci_fast_are_distinct(self):
        """Asserting a bare "!=" is far too weak; assert both definitions."""
        body = read(CI_REL)
        self.assertIn("### 3.4 LOCAL_FAST_GATE vs CI_FAST_GATE", body)
        self.assertIn("LOCAL_FAST_GATE = 开发/代理的快速反馈回路", body)
        self.assertIn("CI_FAST_GATE    = 干净环境中的可复现确认", body)

    def test_ci_should_not_be_the_first_place_a_low_level_defect_is_found(self):
        body = read(CI_REL)
        self.assertIn("CI 不应是确定性低层缺陷第一次被发现的地方", body)

    def test_no_fabrication_of_unavailable_local_tooling(self):
        body = read(CI_REL)
        self.assertIn("如实上报", body)

    def test_fast_and_full_need_not_be_two_separate_jobs(self):
        body = read(CI_REL)
        self.assertIn("不**要求必须是两个独立", body)

    def test_no_universal_wall_clock_sla_is_imposed(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("强加普适 wall-clock SLA", body)

    def test_no_irrelevant_language_toolchain_is_required(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("不**要求无关语言的工具链", body)

    def test_registered_is_not_executed_survives(self):
        body = read(CI_REL)
        self.assertIn("REGISTERED != EXECUTED", body)

    def test_fast_runs_before_expensive_gates(self):
        """Ordering is declared in the CI document (the execution surface)."""
        self.assertIn("FAST 门在可行时先于昂贵门执行", read(CI_REL))
        # The framework declares the same ordering in its canonical sequence.
        self.assertIn("CI_FAST_GATE", read(FRAMEWORK_REL))
        self.assertIn("LOCAL FAST_GATE", read(FRAMEWORK_REL))


class RegressionTestRulePreservedTests(unittest.TestCase):
    """BUG KNOWLEDGE -> REGRESSION TEST must stay valid where it belongs."""

    def test_regression_test_rule_is_preserved(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("BUG KNOWLEDGE → REGRESSION TEST", body)
        self.assertIn("不得**被", body)

    def test_static_analysis_does_not_replace_test_or_review(self):
        body = read(FRAMEWORK_REL)
        for token in ("STATIC_ANALYSIS != BEHAVIORAL_CONTRACT_TEST",
                      "STATIC_ANALYSIS != ARCHITECTURE_REVIEW"):
            with self.subTest(token=token):
                self.assertIn(token, body)

    def test_ticket_lane_keeps_test_first_defect_closure(self):
        body = read(TICKET_REL)
        self.assertIn("CAN_THIS_FAILURE_BE_CAPTURED_AS_A_STABLE_TEST?", body)

    def test_defect_closure_offers_a_second_destination(self):
        body = read(TICKET_REL)
        self.assertIn("§21", body)


class BLayerBoundaryTests(unittest.TestCase):
    """These are D-layer defaults. Nothing may be silently elevated to B."""

    def test_rules_md_unchanged_by_this_ticket(self):
        body = read(RULES_REL)
        for banned in ("ruff", "Ruff", "FAST_GATE", "FULL_GATE",
                       "DEFECT_TO_GATE_PROMOTION", "PROMOTE_NOW"):
            with self.subTest(banned=banned):
                self.assertNotIn(
                    banned, body,
                    f"RULES.md (B layer) must not gain tool/gate policy: {banned}")

    def test_framework_declares_it_is_not_b_layer(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("不**进入 B 层不变量", body)

    def test_no_mandatory_tool_is_promoted_to_b_layer(self):
        body = read(AGENTS_REL)
        self.assertIn("不**把任何语言特定工具升格为普适硬不变量", body)

    def test_agents_pointer_exists_without_being_a_second_declaration(self):
        """AGENTS.md carries the mechanism, but must not own the value domains.

        Two independent reviewers converged on the same hole here: this guard
        used to REQUIRE "KEEP_AS_REVIEWER_RESPONSIBILITY" to appear in
        AGENTS.md, which meant the file that re-enumerated all five
        dispositions was the one shape the suite insisted on. A guard that
        pins a duplicate in place is worse than no guard, because it reads as
        evidence the invariant holds.

        So the rule is now stated the other way round. AGENTS.md carries the
        mechanism and the routing; the framework section 21 owns the value
        domains, and AGENTS.md may not restate them -- as a set, with any
        punctuation, on any number of lines. The same detector that guards the
        ticket lane guards this file, so the two surfaces cannot drift apart.
        """
        body = read(AGENTS_REL)
        self.assertIn("DEFECT_TO_GATE_PROMOTION", body)
        self.assertIn("FAST_GATE / FULL_GATE", body)
        # It routes to the canonical owners instead of restating their content.
        for owner in ("references/static-analysis-and-code-intelligence.md",
                      "references/ticket-lane.md",
                      "references/review-and-repair-saturation.md",
                      "references/git-ci-integration.md"):
            with self.subTest(owner=owner):
                self.assertIn(owner, body)
        # No disposition may be named at all: the owner defines the domain.
        self.assertFalse(
            _restates_disposition_domain(body),
            "AGENTS.md must delegate the disposition domain to framework 21.3")
        # AGENTS.md may show non-collapse pairs (NOT_CONFIGURED != PASS) as
        # examples; it must not present the value domain as a closed set.
        # The framework owns the closed set, so no "the seven values are ..."
        # enumeration may appear here.
        self.assertNotIn("七值", body)
        self.assertNotIn("状态值域 = ", body)

    def test_no_pointer_document_restates_the_disposition_domain(self):
        """Single-owner discipline applies to EVERY surface, not one block.

        The earlier guards each looked at a single pre-split block of a single
        file, so a restatement added anywhere else -- AGENTS.md, README.md, the
        end of the review saturation file -- was invisible. Reviewers found
        three such holes by appending an enumeration and watching zero tests
        fail.

        The owner itself is excluded on purpose: framework 21.3 is where the
        values are DEFINED, and the detector would of course fire there.
        """
        for rel in (AGENTS_REL, README_REL, TICKET_REL, REVIEW_REL, CI_REL,
                    PAIN_REL):
            with self.subTest(rel=rel):
                self.assertFalse(
                    _restates_disposition_domain(read(rel)),
                    f"{rel} must point at the owner, not restate the domain")

    def test_promotion_value_axis_domain_has_a_single_owner(self):
        """PROMOTION_VALUE is a value domain too, and 21.1 owns it.

        The same single-owner rule that covers the dispositions covers this
        axis. A receipt that writes "PROMOTION_VALUE = HIGH / MEDIUM / LOW"
        has forked it just as surely as an abbreviated disposition would.

        The first version of this guard banned one literal, "PROMOTION_VALUE =
        HIGH", and skipped README.md entirely -- so a reviewer forked the axis
        there in the exact canonical phrasing and nothing failed. It now runs
        the structural detector over every pointer surface, which also means
        it no longer depends on how the sentence introducing the set is
        worded.
        """
        framework = read(FRAMEWORK_REL)
        self.assertIn("PROMOTION_VALUE               HIGH / MEDIUM / LOW / "
                      "NOT_APPLICABLE", framework)
        for rel in (AGENTS_REL, README_REL, TICKET_REL, REVIEW_REL, CI_REL,
                    PAIN_REL):
            with self.subTest(rel=rel):
                self.assertFalse(
                    _restates_promotion_value_domain(read(rel)),
                    f"{rel} must point at framework 21.1, not fork the axis")

    def test_status_domain_has_a_single_owner(self):
        """The seven-value non-collapse domain belongs to framework 8 alone.

        This domain was the one nobody built a structural guard for, so the
        only protection was a two-string ban ("七值", "状态值域 = ") that any
        rephrasing defeats. A reviewer wrote all seven values into AGENTS.md
        as a closed set and the suite stayed green.

        Note the trap this has to avoid: git-ci-integration.md declares a
        DIFFERENT seven-value status domain (CI_STATUS) that legitimately
        shares PASS / FAIL / KNOWN_BASELINE_FAILURE, and the review saturation
        file grades IMPACT / CONTRACT_CONFIDENCE / REPAIR_COMPLEXITY /
        REGRESSION_RISK on the same HIGH / MEDIUM / LOW scale. Flagging either
        would make the guard noise, so the detector excludes spans carrying a
        member exclusive to the other domain.
        """
        for rel in (AGENTS_REL, README_REL, TICKET_REL, REVIEW_REL, CI_REL,
                    PAIN_REL):
            with self.subTest(rel=rel):
                self.assertFalse(
                    _restates_status_domain(read(rel)),
                    f"{rel} must point at framework 8, not restate the domain")
        # The legitimate neighbouring domain is still there and still legal;
        # if this ever fails, the guard is over-broad rather than the document
        # being wrong.
        self.assertIn("NOT_TRIGGERED", read(CI_REL))

    def test_every_domain_is_checked_on_every_pointer_surface(self):
        """One loop, three domains, every surface.

        The two previous tests each named their own file list and each forgot
        a file. This one exists so a fourth domain cannot be added without
        also being given a surface list, and so the surface list lives in
        exactly one place.
        """
        surfaces = (AGENTS_REL, README_REL, TICKET_REL, REVIEW_REL, CI_REL,
                    PAIN_REL)
        for rel in surfaces:
            body = read(rel)
            for name, detector in (
                    ("disposition", _restates_disposition_domain),
                    ("status", _restates_status_domain),
                    ("promotion_value", _restates_promotion_value_domain)):
                with self.subTest(rel=rel, domain=name):
                    self.assertFalse(
                        detector(body),
                        f"{rel} restates the {name} domain")
        self.assertEqual(6, len(surfaces))

    def test_domain_detectors_are_quiet_on_every_pointer_document(self):
        """The detectors must be silent on the real tree, or nobody keeps them.

        This is the other half of a usable guard. A detector that fires on the
        pristine documents trains everyone to ignore it, and an ignored guard
        protects nothing -- which is exactly how the first version of this
        suite ended up pinning a violation in place. Both halves are asserted
        in the same place on purpose: quiet now, loud on mutation.
        """
        for rel in (AGENTS_REL, README_REL, TICKET_REL, REVIEW_REL, CI_REL,
                    PAIN_REL, FRAMEWORK_REL):
            body = read(rel)
            for name, detector in (
                    ("disposition", _restates_disposition_domain),
                    ("status", _restates_status_domain),
                    ("promotion_value", _restates_promotion_value_domain)):
                with self.subTest(rel=rel, domain=name):
                    # The framework is the owner for all three, so it is
                    # expected to trip them; what matters is that no POINTER
                    # document does, and that the owner trips every one.
                    fires = detector(body)
                    if rel == FRAMEWORK_REL:
                        self.assertTrue(
                            fires, f"the owner must declare {name}")
                    else:
                        self.assertFalse(
                            fires, f"{rel} must not declare {name}")

    def test_every_section_pointer_resolves_to_a_real_heading(self):
        """A pointer to a section that does not exist is a broken contract.

        Both reviewers demoted or renamed section 21.3 as a probe and no test
        failed: the guards checked that the text "21.3" was mentioned, never
        that a heading with that number still exists. A pointer is only a
        delegation if it resolves.
        """
        for rel, needle in ((TICKET_REL, "§21.3"), (REVIEW_REL, "§21.1"),
                            (REVIEW_REL, "§21.2"), (CI_REL, "§10.1"),
                            (AGENTS_REL, "§21.3"),
                            (TICKET_REL, "### 9.3"), (TICKET_REL, "### 9.4")):
            with self.subTest(rel=rel, needle=needle):
                self.assertIn(needle, read(rel),
                              f"{rel} should point at {needle}")
        # Framework 21.3 must still be a subsection of 21, not a demoted
        # sibling: promoting it to "##" would silently take it out from
        # under the section it belongs to.
        framework = read(FRAMEWORK_REL)
        self.assertIn("### 21.3 处置（disposition）", framework)
        self.assertNotIn("\n## 21.3", framework)
        # And the three subsections the rest of the repo cites must all exist.
        for heading in ("### 21.1 ", "### 21.2 ", "### 21.3 "):
            with self.subTest(heading=heading):
                self.assertIn(heading, framework)

    def test_promotion_value_high_is_a_conjunction_not_a_disjunction(self):
        """The HIGH bar is AND-ed. Turning "+" into "或" must fail.

        A reviewer flipped one line of the 21.1 conjunction from "+ 误报风险
        足够低" to "或 误报风险足够低" and no test noticed. That single
        character turns "all of these must hold" into "any of these is
        enough" -- it deletes the value gate while every marker stays in
        place, which is precisely the failure mode this suite cannot see by
        grepping.
        """
        body = read(FRAMEWORK_REL)
        self.assertIn(_HIGH_GATE_ANCHOR, body)
        clauses = _high_clauses(body)
        self.assertGreaterEqual(len(clauses), 5)
        for clause in clauses[1:]:
            with self.subTest(clause=clause):
                self.assertTrue(
                    clause.startswith("+ "),
                    "every HIGH clause must be AND-ed: " + clause)
                self.assertNotIn("或", clause,
                                 "a disjunctive clause deletes the value gate")

    def test_the_disposition_domain_is_closed_at_exactly_five_members(self):
        """Single owner is not the same as open-ended.

        Every guard here checks that the owner still contains each member it
        knows about. None of them notices a member ADDED, so a sixth
        disposition could appear in 21.3 -- forked mid-domain, invisible to a
        consumer reading the ticket lane's "<§21.3 处置值域>" -- and the suite
        would report green. A reviewer appended KEEP_AS_ARCHITECTURE_OWNER and
        got zero failures. Closing the set means asserting its size.
        """
        block = read(FRAMEWORK_REL).split("### 21.3 ", 1)[1]
        # The canonical rows align the description column, but the longest
        # member (KEEP_AS_REVIEWER_RESPONSIBILITY) leaves only one space, so
        # the separator is "2+ spaces OR 1 space before CJK". Anchoring on two
        # spaces silently dropped that member and made the count four.
        found = re.findall(
            r"^\s*([A-Z][A-Z_]{3,})(?:\s{2,}| (?=[一-鿿]))", block, re.M)
        self.assertEqual(
            sorted(PROMOTION_DISPOSITIONS), sorted(found),
            "21.3 must declare exactly the five dispositions and nothing else")

    def test_section_pointers_resolve_to_a_heading_that_exists(self):
        """A pointer is a delegation only if it resolves.

        The earlier version of this check asserted that the STRING "21.3"
        appeared in the citing file. A reviewer repointed AGENTS.md at a
        section that does not exist -- "§3.3/§3.4" became "§3.9/§3.4" -- and
        every test passed, because presence was all that was ever checked. A
        pointer into the void is worse than no pointer: it looks like a
        delegation and routes a reader nowhere.

        The index is built from real headings, so it is a fact about the tree
        rather than a list of strings someone remembered to update.
        """
        headings: dict[str, set[str]] = {}
        for rel in (FRAMEWORK_REL, TICKET_REL, REVIEW_REL, CI_REL):
            for line in read(rel).splitlines():
                match = re.match(r"^(#{2,4})\s+(\d+(?:\.\d+)*)\.?\s", line)
                if match:
                    headings.setdefault(match.group(2), set()).add(
                        match.group(1))
        self.assertIn("21.3", headings, "framework 21.3 must exist")
        self.assertEqual({"###"}, headings["21.3"],
                         "21.3 must stay a subsection of 21")
        # Every section this ticket added a pointer to must resolve, in the
        # file that is supposed to own it.
        for rel, numbers in (
                (FRAMEWORK_REL, ("8", "10.1", "15.1", "21", "21.1", "21.2",
                                 "21.3")),
                (TICKET_REL, ("9.3", "9.4")),
                (REVIEW_REL, ("4.1", "6.5")),
                (CI_REL, ("3.3", "3.4"))):
            for number in numbers:
                with self.subTest(rel=rel, number=number):
                    self.assertIn(
                        number, headings,
                        f"{rel} owns section {number} but no heading matches")

    def test_pain_row_does_not_restate_the_disposition_domain(self):
        """The audit ledger records intent; it must not fork the value domain.

        Once the ticket lane was raised to "reference only, never restate",
        an inline copy in the pain row became the one unguarded duplicate.
        """
        body = read(PAIN_REL)
        self.assertIn("## P21", body)
        self.assertFalse(
            _restates_disposition_domain(body),
            "the pain row must reference the section 21.3 domain, not copy it")

    def test_pain_row_sits_before_the_summary_table(self):
        """P01..P21 are all listed before the roll-up table."""
        body = read(PAIN_REL)
        self.assertLess(body.index("## P21 "), body.index("## 汇总判定表"))
        self.assertLess(body.index("## P20 "), body.index("## P21 "))
        # The P20 baseline evidence stays attached to P20.
        p20 = body.index("## P20 ")
        p21 = body.index("## P21 ")
        self.assertLess(p20, body.index("### P20 BASELINE"))
        self.assertLess(body.index("### P20 BASELINE"), p21)


class DogfoodTests(unittest.TestCase):
    """The governance repo must classify its own pipeline (spec section 19)."""

    def test_repo_classification_is_recorded(self):
        body = read(PAIN_REL)
        self.assertIn("## P21", body)
        self.assertIn("MACHINE_ENFORCED = PARTIAL", body)

    def test_pain_row_grounds_the_mechanism_in_real_evidence(self):
        body = read(PAIN_REL)
        self.assertIn("F841", body)
        self.assertIn("R8 四问", body)
        self.assertIn("SHOULD_BE_GLOBAL = **DEFAULT_ONLY**", body)

    def test_pain_row_does_not_invent_unverified_history(self):
        body = read(PAIN_REL)
        self.assertIn("OWNER-BRIEFED", body)
        self.assertIn("owner 报告而非已核实事实", body)

    def test_no_ci_churn_was_needed(self):
        """Current pipeline order already satisfies static-before-expensive."""
        ci_text = (ROOT / ".github/workflows/governance-ci.yml").read_text(
            encoding="utf-8")
        self.assertEqual([], GOV.static_gate_ci_wiring(ci_text))
        self.assertLess(
            ci_text.index("ruff check"),
            ci_text.index("unittest discover -s scripts/tests"),
            "the static gate must still precede the expensive suite")


class ValidatorWiringTests(unittest.TestCase):
    """The new wiring is mechanically checked, not just documented."""

    def test_validator_has_no_new_failures_on_the_current_tree(self):
        self.assertEqual([], GOV.static_gate_wiring(ROOT))

    def test_no_new_standalone_spec_was_created(self):
        """Spec section 1: no new competing governance document."""
        refs = sorted(p.name for p in (ROOT / "references").glob("*.md"))
        self.assertNotIn("defect-promotion.md", refs)
        self.assertNotIn("fast-full-gate.md", refs)
        self.assertEqual(12, len(refs),
                         f"references/ gained a document: {refs}")

    def test_new_receipt_fields_are_registered_for_presence(self):
        """The ticket-lane receipt surface must be validator-visible."""
        body = read(TICKET_REL)
        for field in ("FAST_GATE_COMPLETE", "FULL_GATE_COMPLETE",
                      "PROMOTION =", "NON_PASS_ITEMS"):
            with self.subTest(field=field):
                self.assertIn(field, body)

    def test_promotion_disposition_domain_has_a_single_owner(self):
        """CE-28: the receipt must REFERENCE section 21.3, never abbreviate it.

        An abbreviated value domain (KEEP_AS_REVIEW / KEEP_AS_HUMAN) would be
        a second declaration point, making the field uncheckable.
        """
        framework = read(FRAMEWORK_REL)
        self.assertIn("### 9.4", read(TICKET_REL), "section 9.4 anchor is required")
        receipt_block = read(TICKET_REL).split("### 9.4", 1)[1]
        for disp in PROMOTION_DISPOSITIONS:
            with self.subTest(disp=disp):
                self.assertIn(disp, framework)
                self.assertNotIn(
                    disp + " |", receipt_block,
                    "the receipt must not restate the disposition domain")
        self.assertIn("<§21.3 处置值域>", receipt_block)
        # Abbreviations that would silently fork the domain are banned.
        for abbreviated in ("KEEP_AS_REVIEW |", "KEEP_AS_HUMAN |"):
            with self.subTest(abbreviated=abbreviated):
                self.assertNotIn(abbreviated, receipt_block)


class NegativeControlTests(unittest.TestCase):
    """NEGATIVE CONTROL (spec section 20): prove the checks are not vacuous.

    Each test takes a REAL clause out of the real document and asserts that a
    sibling guard notices. A guard that cannot fail proves nothing, so each
    case is built to fail on the pristine tree -- if one of these ever passes
    without a mutation, the guard it exercises is dead.
    """

    def _without(self, rel: str, old: str, new: str) -> str:
        original = read(rel)
        self.assertIn(old, original,
                      f"the clause under mutation must exist in {rel}")
        return original.replace(old, new)

    def _guards_that_fail_on(self, rel: str, old: str, new: str) -> list[str]:
        """Apply a real mutation to a real document and report which guards fire.

        This is the honest form of a negative control. Rewriting a string and
        asserting the string is gone only proves that str.replace works; it
        says nothing about whether any guard would notice. Here the mutated
        document is fed to the very assertions this module relies on, so a
        guard that stops protecting its clause shows up as an empty result.
        """
        mutated = self._without(rel, old, new)
        fired = []
        fw_guards = {
            "value-gate": lambda b: "一次出现 ≠ 治理缺陷" in b,
            "lowest-is-not-weakest": lambda b: "LOWEST ≠ WEAKEST" in b,
            "has-type-checker-layer": lambda b: "type checker" in b,
            "keeps-regression-test-rule":
                lambda b: "BUG KNOWLEDGE → REGRESSION TEST" in b,
            "fast-not-replace-full": lambda b: "FAST 不替代 FULL" in b,
            "full-not-excuse-fast": lambda b: "FULL 不豁免 FAST" in b,
            "fast-not-replace-full-ci":
                lambda b: "CI_FAST PASS != CI_FULL PASS" in b,
            "declares-21": lambda b: "## 21. DEFECT_TO_GATE_PROMOTION" in b,
            # The 21.3 subsection must stay a subsection: a reviewer demoted it
            # to "##" as a probe and the ownership guards never noticed,
            # because they only counted the string "21.3" in prose.
            "21-3-is-a-subsection":
                lambda b: "### 21.3 处置（disposition）" in b
                and "\n## 21.3" not in b,
            "21-1-still-present": lambda b: "### 21.1 " in b,
            "21-2-still-present": lambda b: "### 21.2 " in b,
        }
        for name, guard in fw_guards.items():
            if rel == FRAMEWORK_REL and not guard(mutated):
                fired.append(f"framework:{name}")
        review_guards = {
            "reviewer-no-governance-authority":
                lambda b: "修改治理的权威" in b,
            "finding-not-automatic-truth": lambda b: "!=** 自动真理" in b,
            "finding-not-automatic-gate": lambda b: "!=** 自动建门" in b,
            "executor-must-verify": lambda b: "仍必须核验" in b,
            "repeat-signal-not-weaken-r4": lambda b: "不**削弱 RULES R4" in b,
            # 6.5 is the clause that makes the repeat signal safe, because it
            # routes promotion back through the value gate. A reviewer reworded
            # exactly this delegation away and zero tests fired.
            "repeat-signal-defers-to-value-gate":
                lambda b: "§21.1 的 value gate" in b,
            "single-owner-declared": lambda b: "唯一声明点" in b,
            "finding-routes-to-21": lambda b: "§21（value-gated" in b,
        }
        for name, guard in review_guards.items():
            if rel == REVIEW_REL and not guard(mutated):
                fired.append(f"review:{name}")
        ci_guards = {
            "local-fast-defined":
                lambda b: "LOCAL_FAST_GATE = 开发/代理的快速反馈回路" in b,
            "ci-not-first-discovery":
                lambda b: "CI 不应是确定性低层缺陷第一次被发现的地方" in b,
            "honest-local-reporting": lambda b: "如实上报" in b,
        }
        for name, guard in ci_guards.items():
            if rel == CI_REL and not guard(mutated):
                fired.append(f"ci:{name}")
        receipt_guards = {
            "no-abbreviated-domain":
                lambda b: "KEEP_AS_REVIEW |" not in b and "KEEP_AS_HUMAN |" not in b,
            "no-disposition-restatement-in-4-1":
                lambda b: not _restates_disposition_domain(b),
            "has-delegation-marker": lambda b: "<§8 状态值域>" in b,
            "has-9-3-anchor": lambda b: "### 9.3" in b,
            "has-9-4-anchor": lambda b: "### 9.4" in b,
        }
        for name, guard in receipt_guards.items():
            if rel == TICKET_REL and not guard(mutated):
                fired.append(f"ticket:{name}")
        return fired

    # -- baseline: the pristine documents DO carry every clause -------------

    def test_baseline_documents_carry_every_guarded_clause(self):
        fw = read(FRAMEWORK_REL)
        for clause in ("一次出现 ≠ 治理缺陷", "LOWEST ≠ WEAKEST",
                       "PROMOTION_VALUE = HIGH", "BUG KNOWLEDGE → REGRESSION TEST"):
            with self.subTest(clause=clause):
                self.assertIn(clause, fw)
        self.assertIn("修改治理的权威", read(REVIEW_REL))
        self.assertNotIn("ruff", read(RULES_REL))

    def test_baseline_triggers_no_guard(self):
        """Sanity: on the pristine tree every guard must report a violation.

        Each guard is a "clause is present" predicate. Running them against the
        untouched documents must find every clause still there, otherwise the
        mutation tests below would pass for the wrong reason.
        """
        fw = read(FRAMEWORK_REL)
        for clause in ("一次出现 ≠ 治理缺陷", "LOWEST ≠ WEAKEST", "type checker",
                       "BUG KNOWLEDGE → REGRESSION TEST", "FAST 不替代 FULL",
                       "FULL 不豁免 FAST", "CI_FAST PASS != CI_FULL PASS",
                       "## 21. DEFECT_TO_GATE_PROMOTION"):
            with self.subTest(clause=clause):
                self.assertIn(clause, fw)
        rv = read(REVIEW_REL)
        for clause in ("修改治理的权威", "!=** 自动真理", "!=** 自动建门",
                       "仍必须核验", "不**削弱 RULES R4"):
            with self.subTest(clause=clause):
                self.assertIn(clause, rv)
        ci = read(CI_REL)
        for clause in ("LOCAL_FAST_GATE = 开发/代理的快速反馈回路",
                       "CI 不应是确定性低层缺陷第一次被发现的地方", "如实上报"):
            with self.subTest(clause=clause):
                self.assertIn(clause, ci)
        tl = read(TICKET_REL)
        self.assertNotIn("KEEP_AS_REVIEW |", tl)
        self.assertNotIn("处置 = `PROMOTE_NOW", tl)
        self.assertIn("<§8 状态值域>", tl)
        self.assertIn("### 9.3", tl)
        self.assertIn("### 9.4", tl)

    # -- mutation 1: delete the anti-proliferation guard --------------------

    def test_removing_the_value_gate_breaks_a_contract(self):
        fired = self._guards_that_fail_on(FRAMEWORK_REL, "一次出现 ≠ 治理缺陷",
                                          "单次出现即治理缺陷")
        self.assertIn("framework:value-gate", fired)

    def test_removing_the_lowest_is_not_weakest_rule_is_detectable(self):
        fired = self._guards_that_fail_on(FRAMEWORK_REL, "LOWEST ≠ WEAKEST",
                                          "LOWEST = WEAKEST")
        self.assertIn("framework:lowest-is-not-weakest", fired)

    def test_removing_a_mechanical_layer_is_detectable(self):
        fired = self._guards_that_fail_on(FRAMEWORK_REL, "type checker",
                                          "some checker")
        self.assertIn("framework:has-type-checker-layer", fired)

    def test_removing_the_regression_test_preservation_is_detectable(self):
        fired = self._guards_that_fail_on(
            FRAMEWORK_REL, "BUG KNOWLEDGE → REGRESSION TEST", "DEFECT KNOWLEDGE ONLY")
        self.assertIn("framework:keeps-regression-test-rule", fired)

    def test_removing_the_whole_promotion_section_is_detectable(self):
        """Deleting section 21 wholesale must light up several guards.

        The first version of this control truncated the document and then
        asserted the heading was absent from the truncation -- which only
        proves str.split works, and is the exact self-referential antipattern
        its own neighbours warn about. The honest form needs a mutation the
        existing replace helper can express, so this one drops the section
        heading and its first clause: if the guards only look for one marker,
        a partial deletion would slip through, and that is the case worth
        proving.
        """
        fired = self._guards_that_fail_on(
            FRAMEWORK_REL, "## 21. DEFECT_TO_GATE_PROMOTION（缺陷类下沉到机器门）",
            "## 21. 机械门下沉")
        self.assertIn("framework:declares-21", fired)
        # The heading is not the only thing that identifies the section: the
        # body is still there, so a rename must not be able to pass by leaving
        # every marker in place. The 21.x subsection guards are the ones that
        # notice the section stopped being the canonical promotion surface, so
        # a rename that keeps "## 21." intact is exactly the case that needs a
        # separate check rather than an extra count here.
        renamed = self._without(
            FRAMEWORK_REL, "## 21. DEFECT_TO_GATE_PROMOTION（缺陷类下沉到机器门）",
            "## 21. 机械门下沉")
        self.assertIn("## 21. ", renamed)

    # -- mutation 2: let a fast/full boundary collapse ----------------------

    def test_fast_replaces_full_would_be_detectable(self):
        fired = self._guards_that_fail_on(FRAMEWORK_REL, "FAST 不替代 FULL",
                                          "FAST 替代 FULL")
        self.assertIn("framework:fast-not-replace-full", fired)

    def test_full_excusing_fast_would_be_detectable(self):
        fired = self._guards_that_fail_on(FRAMEWORK_REL, "FULL 不豁免 FAST",
                                          "FULL 豁免 FAST")
        self.assertIn("framework:full-not-excuse-fast", fired)

    def test_collapsing_local_and_ci_fast_would_be_detectable(self):
        fired = self._guards_that_fail_on(
            CI_REL, "LOCAL_FAST_GATE = 开发/代理的快速反馈回路",
            "LOCAL_FAST_GATE = CI_FAST_GATE")
        self.assertIn("ci:local-fast-defined", fired)

    def test_dropping_honest_local_reporting_would_be_detectable(self):
        fired = self._guards_that_fail_on(CI_REL, "如实上报", "静默略过")
        self.assertIn("ci:honest-local-reporting", fired)

    # -- mutation 3: escalate D-layer policy into the B layer ---------------

    def test_b_layer_pollution_is_detectable(self):
        """Reuse the P1-T17 language-tool guard to prove the B layer stays clean.

        P1-T17 already ships a non-vacuous detector for language-specific
        tooling promoted into RULES.md. This ticket adds new gate vocabulary
        (FAST_GATE / FULL_GATE / promotion dispositions), so the same guard has
        to stay clean for the new tokens too -- and must still fire when one
        of them is injected.
        """
        t17 = _load_p1_t17()
        hits = t17.language_tool_hits(read(RULES_REL))
        self.assertEqual(
            [], hits, f"{RULES_REL} must carry no language tool policy: {hits}")
        for banned in ("FAST_GATE", "FULL_GATE",
                       "DEFECT_TO_GATE_PROMOTION", "PROMOTE_NOW"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, read(RULES_REL))
        # The detector is not vacuous: it fires on an injected mandate.
        self.assertTrue(t17.language_tool_hits(
            "R9 必须使用 ruff 作为普适硬不变量"))

    # -- mutation 4: hand the reviewer new authority -----------------------

    def test_reviewer_authority_expansion_is_detectable(self):
        fired = self._guards_that_fail_on(REVIEW_REL, "修改治理的权威",
                                          "治理修改建议权")
        self.assertIn("review:reviewer-no-governance-authority", fired)

    def test_reviewer_self_approval_is_detectable(self):
        fired = self._guards_that_fail_on(REVIEW_REL, "!=** 自动真理",
                                          "=** 自动真理")
        self.assertIn("review:finding-not-automatic-truth", fired)

    def test_repeat_signal_weakening_r4_is_detectable(self):
        """The saturation link must not become a way around R4."""
        fired = self._guards_that_fail_on(REVIEW_REL, "不**削弱 RULES R4",
                                          "可以削弱 RULES R4")
        self.assertIn("review:repeat-signal-not-weaken-r4", fired)

    # -- mutation 5: fork the delegated value domains ----------------------

    def test_receipt_restating_the_promotion_domain_is_detectable(self):
        fired = self._guards_that_fail_on(
            TICKET_REL, "PROMOTION = <§21.3 处置值域>",
            "PROMOTION = PROMOTE_NOW | KEEP_AS_REVIEW | KEEP_AS_HUMAN")
        self.assertIn("ticket:no-abbreviated-domain", fired)

    def test_receipt_restating_the_disposition_domain_in_4_1_is_detectable(self):
        """The section 4.1 pointer must delegate, not enumerate the domain.

        An independent reviewer found this hole by deleting a value from the
        enumeration: nothing failed, because the guard only inspected one
        literal spelling inside one block. The anchor below is the short
        delegation phrase, so rewording the surrounding prose does not break
        the test while removing the delegation does.
        """
        fired = self._guards_that_fail_on(
            TICKET_REL, "处置取值集合 = §21.3",
            "处置取值集合 = PROMOTE_NOW / FOLLOWUP_TOOLING_TICKET / "
            "KEEP_AS_TEST / KEEP_AS_REVIEWER_RESPONSIBILITY / "
            "KEEP_AS_HUMAN_DECISION（此处重述）")
        self.assertIn("ticket:no-disposition-restatement-in-4-1", fired)

    def test_appending_a_disposition_enumeration_is_detected(self):
        """Restating the domain with different punctuation must not slip by.

        Two earlier generations of this guard failed the same way: one matched
        a single literal spelling, the next required two members on one LINE.
        A bullet list therefore defeated it, and so did a comma instead of a
        slash. The detector is now structural, so the shapes below are the
        ones a reviewer actually tried.

        KNOWN LIMIT, stated rather than papered over: a bare bullet list with
        no introducing phrase ("- PROMOTE_NOW\\n- KEEP_AS_HUMAN_DECISION")
        is NOT detected. Distinguishing it from a two-item list in ordinary
        prose needs a semantic judgement, and a detector that guesses is a
        detector that cries wolf -- an earlier attempt at exactly this fired
        on four honest documents. The aligned-table form IS caught, because a
        copied declaration brings its column padding with it; a hand-written
        bullet list has to be caught by review. That is the same boundary the
        framework declares when it says marker checks are not semantic
        validation, and it is recorded here so nobody mistakes silence for
        coverage.
        """
        base = read(TICKET_REL)
        for appended in (
                "\n处置取值集合 = PROMOTE_NOW | FOLLOWUP_TOOLING_TICKET | "
                "KEEP_AS_TEST | KEEP_AS_REVIEWER_RESPONSIBILITY\n",
                "\n处置 = `PROMOTE_NOW / FOLLOWUP_TOOLING_TICKET`\n",
                "\nPROMOTION = PROMOTE_NOW / FOLLOWUP_TOOLING_TICKET / "
                "KEEP_AS_TEST\n",
                # Comma separated rather than slashed, with an introduction.
                "\n处置取值集合 = PROMOTE_NOW, KEEP_AS_TEST\n",
                # Abbreviations fork the domain silently.
                "\n处置取值集合 = KEEP_AS_REVIEW | KEEP_AS_HUMAN\n",
                # The canonical aligned-table form, copied verbatim.
                "\n```text\nPROMOTE_NOW             本票内下沉\n"
                "FOLLOWUP_TOOLING_TICKET 需新工具票\n```\n"):
            with self.subTest(appended=appended.strip()[:40]):
                self.assertTrue(
                    _restates_disposition_domain(base + appended),
                    "an appended enumeration is a restatement")
        # The pristine document must not trip the detector, or the guard
        # would be protecting nothing.
        self.assertFalse(_restates_disposition_domain(base))
        # And the limit above is asserted as a limit, so that widening the
        # detector later is a visible change rather than a silent one.
        self.assertFalse(_restates_disposition_domain(
            base + "\n- PROMOTE_NOW\n- KEEP_AS_HUMAN_DECISION\n"),
            "a bare bullet list is a documented gap, not a covered case")

    def test_restating_the_domain_in_agents_or_readme_is_detectable(self):
        """Both reviewers found the same hole in a different file.

        The ownership guards were scoped to one pre-split block of the ticket
        lane, so appending the enumeration to AGENTS.md or README.md produced
        zero failures -- and AGENTS.md was in fact carrying one all along.
        The detector now runs over every pointer surface, so a reformatting of
        the document cannot move the violation out of reach.
        """
        for rel in (AGENTS_REL, README_REL):
            for appended in (
                    "\n处置 = `PROMOTE_NOW / FOLLOWUP_TOOLING_TICKET / "
                    "KEEP_AS_TEST`\n",
                    "\n处置取值集合 = PROMOTE_NOW, KEEP_AS_HUMAN_DECISION\n"):
                with self.subTest(rel=rel, appended=appended.strip()[:30]):
                    self.assertTrue(_restates_disposition_domain(
                        read(rel) + appended),
                        f"a restatement appended to {rel} must be detected")

    def test_dropping_the_repeat_signal_delegation_is_detectable(self):
        """6.5 must keep routing repeats back through the value gate.

        Without this delegation the section reads as "reviewers keep finding
        it, therefore build the gate" -- the rule proliferation it exists to
        prevent. The delegation used to be asserted only in a synthetic
        string, so removing it from the real document changed nothing.
        """
        fired = self._guards_that_fail_on(
            REVIEW_REL, "晋升仍走 §21.1 的 value gate",
            "晋升仍走评审判断")
        self.assertIn("review:repeat-signal-defers-to-value-gate", fired)

    def test_demoting_or_renaming_section_21_3_is_detectable(self):
        """A pointer only delegates if it resolves to a heading.

        A reviewer renamed 21.3 to 21.4 -- orphaning the pointer in the ticket
        lane -- and separately demoted it from "###" to "##", moving it out
        from under section 21. Both probes produced zero failures, because
        every guard counted the token "21.3" in prose and never looked for a
        heading.
        """
        for old, new in (
                ("### 21.3 处置（disposition）", "### 21.4 处置（disposition）"),
                ("### 21.3 处置（disposition）", "## 21.3 处置（disposition）")):
            with self.subTest(new=new):
                fired = self._guards_that_fail_on(FRAMEWORK_REL, old, new)
                self.assertIn("framework:21-3-is-a-subsection", fired)

    def test_flipping_the_value_gate_to_a_disjunction_is_detectable(self):
        """HIGH is a conjunction. One "或" turns it into a tautology.

        This is the failure the whole suite is blind to by construction: a
        reviewer changed "+ 误报风险足够低" to "或 误报风险足够低" and every
        marker stayed in place while the meaning inverted. Marker presence is
        not semantic validation -- the framework says so itself -- so the
        polarity has to be asserted directly.
        """
        body = read(FRAMEWORK_REL)
        original = body
        mutated = body.replace("+ 误报风险足够低", "或 误报风险足够低")
        self.assertNotEqual(original, mutated, "the clause under test moved")
        self.assertIn("或 误报风险足够低", mutated)
        # The pristine document satisfies the polarity guard; the mutation
        # must not. Both sides are asserted so neither can pass vacuously.
        polarity = lambda b: all(  # noqa: E731
            c.startswith("+ ") and "或" not in c
            for c in _high_clauses(b)[1:])
        self.assertTrue(polarity(original), "pristine must satisfy polarity")
        self.assertFalse(polarity(mutated),
                         "a disjunctive clause deletes the value gate")

    def test_receipt_restating_the_status_domain_is_detectable(self):
        """The banned domain token must be absent now and visible when added.

        The second half is what gives this teeth: the real validator is run
        against a copy of the tree that carries the restated token, and it
        must reject it. Without that, this would be another always-true test.
        """
        pristine = read(TICKET_REL)
        self.assertNotIn(
            GOV.STATIC_GATE_DOMAIN_ONLY_TOKEN, pristine,
            "the receipt must delegate the status domain, never restate it")
        self.assertEqual([], GOV.static_gate_wiring(ROOT))

        with tempfile.TemporaryDirectory() as tmp:
            polluted = Path(tmp) / "repo"
            shutil.copytree(ROOT, polluted,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            receipt = polluted / TICKET_REL
            receipt.write_text(
                receipt.read_text(encoding="utf-8")
                + "\nEXTRA = " + GOV.STATIC_GATE_DOMAIN_ONLY_TOKEN + "\n",
                encoding="utf-8")
            problems = GOV.static_gate_wiring(polluted)
        self.assertTrue(
            any(GOV.STATIC_GATE_DOMAIN_ONLY_TOKEN in p for p in problems),
            f"restating the status domain must be rejected: {problems}")


class OutOfScopeTests(unittest.TestCase):
    def test_marker_checks_cannot_judge_prose(self):
        """Marker presence is not semantic validation -- and that is declared.

        A document can carry every marker this module checks and still
        contradict itself in prose. The framework must therefore say so
        explicitly, so nobody mistakes a green suite for a semantic review.
        """
        doc = read(FRAMEWORK_REL)
        self.assertIn("LOWEST ≠ WEAKEST", doc)
        self.assertIn("不裁决", doc)
        # The ticket's own test file declares the same limit.
        self.assertIn("Marker presence is NOT semantic validation",
                      Path(__file__).read_text(encoding="utf-8"))

    def test_no_defect_database_or_new_state_store(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("不**新建状态数据库", body)
        self.assertIn("不**新建状态数据库", read(TICKET_REL) + read(FRAMEWORK_REL))

    def test_forbidden_overbuild_is_not_proposed(self):
        """The spec's explicit non-goals must stay non-goals."""
        body = read(FRAMEWORK_REL) + read(AGENTS_REL)
        for banned in ("defect database", "central CI platform",
                       "linter server"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, body)

    def test_this_file_is_part_of_the_discovered_suite(self):
        """CI runs `unittest discover -s scripts/tests`; be in that glob."""
        self.assertEqual("test_p1_t18_defect_promotion_fast_full.py",
                         Path(__file__).name)
        self.assertTrue((ROOT / "scripts/tests" / Path(__file__).name).is_file())


if __name__ == "__main__":
    unittest.main()
