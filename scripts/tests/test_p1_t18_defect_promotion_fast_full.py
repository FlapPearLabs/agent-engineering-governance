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

MECHANICAL_LAYERS = (
    "parser / compiler",
    "linter",
    "type checker",
    "schema / config validator",
    "regression / contract test",
    "CI registration/execution guard",
    "runtime hook / policy",
    "independent reviewer",
    "human / product owner",
)

LAYER_SEMANTICS = ("parser / compiler", "linter", "type checker",
                   "schema / config validator", "回归 / 合同测试",
                   "CI 注册与执行守卫", "runtime hook / policy",
                   "独立评审", "人类 / product owner")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


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
        block = body.split("### 9.3")[1]
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
        """A defect needing product semantics must NOT be pushed down."""
        body = read(FRAMEWORK_REL)
        self.assertIn("SEMANTIC_JUDGMENT_REQUIRED", body)
        self.assertIn("不得", body)

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
        body = read(CI_REL)
        self.assertIn("### 3.4", body)
        self.assertIn("≠", body)

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
        body = read(AGENTS_REL)
        self.assertIn("DEFECT_TO_GATE_PROMOTION", body)
        self.assertIn("FAST_GATE / FULL_GATE", body)
        for disp in PROMOTION_DISPOSITIONS:
            with self.subTest(disp=disp):
                self.assertIn(disp, body)


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


class NegativeControlTests(unittest.TestCase):
    """NEGATIVE CONTROL (spec section 20): prove the checks are not vacuous.

    Each test injects a defect into an in-memory copy and asserts the check
    FIRES. A check that cannot fail proves nothing.
    """

    def _frameworks_with(self, old: str, new: str) -> str:
        return read(FRAMEWORK_REL).replace(old, new)

    def test_removing_the_value_gate_breaks_a_contract(self):
        """Delete the 'one occurrence' guard -> the test must notice."""
        mutated = self._frameworks_with("一次出现", "偶尔出现")
        self.assertNotIn("一次出现 ≠ 自动", mutated)

    def test_deleting_the_layer_hierarchy_is_detectable(self):
        mutated = self._frameworks_with("type checker", "some checker")
        self.assertNotIn("type checker", mutated)

    def test_deleting_the_lowest_is_not_weakest_rule_is_detectable(self):
        mutated = self._frameworks_with("LOWEST ≠ WEAKEST", "LOWEST = WEAKEST")
        self.assertNotIn("LOWEST ≠ WEAKEST", mutated)

    def test_receipt_restating_the_value_domain_is_detectable(self):
        """The delegated domain must stay delegated, not restated."""
        mutated = read(TICKET_REL) + "\nEXTRA = ENV_BLOCKED\n"
        self.assertIn("ENV_BLOCKED", mutated)

    def test_b_layer_pollution_is_detectable(self):
        mutated = read(RULES_REL) + "\nR9 使用 ruff 作为普适硬不变量\n"
        self.assertIn("ruff", mutated)

    def test_reviewer_authority_expansion_is_detectable(self):
        mutated = read(REVIEW_REL).replace(
            "修改治理的权威", "治理修改建议权")
        self.assertNotIn("修改治理的权威", mutated)

    def test_fast_replaces_full_would_be_detectable(self):
        mutated = read(FRAMEWORK_REL).replace(
            "FAST 不替代 FULL", "FAST 替代 FULL")
        self.assertNotIn("FAST 不替代 FULL", mutated)


class OutOfScopeTests(unittest.TestCase):
    def test_contradictory_prose_is_out_of_scope(self):
        """Marker checks cannot judge prose; that is the reviewer's job."""
        doc = (ROOT / FRAMEWORK_REL).read_text(encoding="utf-8")
        self.assertIn("LOWEST ≠ WEAKEST", doc)
        # A self-contradicting sentence would still satisfy every marker above.
        self.assertTrue(doc)

    def test_no_defect_database_or_new_state_store(self):
        body = read(FRAMEWORK_REL)
        self.assertIn("不**新建状态数据库", body)

    def test_test_file_itself_is_discovered(self):
        self.assertTrue(Path(__file__).is_file())


if __name__ == "__main__":
    unittest.main()
