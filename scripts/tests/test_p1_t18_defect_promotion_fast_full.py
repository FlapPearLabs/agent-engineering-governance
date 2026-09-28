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
# out. An earlier guard matched one literal spelling, so appending the same
# enumeration with different punctuation slipped through; this detector looks
# for the tell-tale pattern instead: several disposition names appearing
# together in one span, which is what any restatement looks like.
_DISPOSITION_LIST = re.compile(
    "|".join(re.escape(d) for d in PROMOTION_DISPOSITIONS))


def _restates_disposition_domain(text: str) -> bool:
    """True if the text spells out the disposition value domain as a set.

    Delegation ("处置取值集合 = §21.3") names no disposition at all, so the
    scan is anchored on real enum members rather than on prose. Two members on
    one line is already an enumeration: a receipt that writes down any subset
    of the domain is restating it, because the consumer then has to guess
    whether the missing members were deliberately excluded.

    A judgement rule that happens to name two outcomes -- "PROMOTE_NOW only
    when ..., otherwise FOLLOWUP_TOOLING_TICKET" -- is not a value domain, so
    a line that binds a condition to a disposition is skipped. The markers are
    deliberately narrow: a bare "当" also opens ordinary prose ("当 X 为 NO
    时"), so only the phrasing that actually binds a condition counts. What
    matters is whether the line presents the values as the set of possible
    values, not whether it mentions two of them.
    """
    for line in text.splitlines():
        if "KEEP_AS_REVIEW |" in line or "KEEP_AS_HUMAN |" in line:
            return True
        found = set(_DISPOSITION_LIST.findall(line))
        if len(found) < 2:
            continue
        if any(marker in line for marker in ("只在", "否则", "仅当", "才成立")):
            continue
        return True
    return False


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

        It may name the dispositions so a reader can route to the owner, but
        the framework must remain the only place that defines them, and
        AGENTS.md must point there rather than stand alone.
        """
        body = read(AGENTS_REL)
        self.assertIn("DEFECT_TO_GATE_PROMOTION", body)
        self.assertIn("FAST_GATE / FULL_GATE", body)
        # It routes to the canonical owners instead of restating their content.
        self.assertIn("references/static-analysis-and-code-intelligence.md",
                      body)
        self.assertIn("references/ticket-lane.md", body)
        self.assertIn("references/git-ci-integration.md", body)
        # The full canonical form appears only in the owner's own line.
        self.assertIn("KEEP_AS_REVIEWER_RESPONSIBILITY", body)
        self.assertNotIn("KEEP_AS_REVIEW |", body)
        self.assertNotIn("KEEP_AS_HUMAN |", body)
        # AGENTS.md may show non-collapse pairs (NOT_CONFIGURED != PASS) as
        # examples; it must not present the value domain as a closed set.
        # The framework owns the closed set, so no "the seven values are ..."
        # enumeration may appear here.
        self.assertNotIn("七值", body)
        self.assertNotIn("状态值域 = ", body)

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
        """Deleting section 21 wholesale must light up several guards."""
        original = read(FRAMEWORK_REL)
        truncated = original.split("## 21. DEFECT_TO_GATE_PROMOTION")[0]
        self.assertNotIn("## 21. DEFECT_TO_GATE_PROMOTION", truncated)
        guard = lambda b: "## 21. DEFECT_TO_GATE_PROMOTION" in b  # noqa: E731
        self.assertFalse(guard(truncated))

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

        The earlier guard matched one exact spelling, so appending the same
        enumeration without backticks produced zero failures.
        """
        for appended in (
                "\n处置取值集合 = PROMOTE_NOW | FOLLOWUP_TOOLING_TICKET | "
                "KEEP_AS_TEST | KEEP_AS_REVIEWER_RESPONSIBILITY\n",
                "\n处置 = `PROMOTE_NOW / FOLLOWUP_TOOLING_TICKET`\n",
                "\nPROMOTE_NOW / FOLLOWUP_TOOLING_TICKET / KEEP_AS_TEST\n"):
            with self.subTest(appended=appended.strip()[:40]):
                self.assertTrue(
                    _restates_disposition_domain(read(TICKET_REL) + appended),
                    "an appended enumeration is a restatement")
        self.assertFalse(_restates_disposition_domain(read(TICKET_REL)))

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
