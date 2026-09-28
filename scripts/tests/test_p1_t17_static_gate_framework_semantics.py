"""Counterexample-driven tests for the cross-language STATIC GATE FRAMEWORK
documentation surface (P1-T17).

BINDING (references/ticket-lane.md section 4, counterexample-first):
    CONTRACT -> COUNTEREXAMPLES -> RED -> IMPLEMENT -> GREEN -> REGRESSION

WHAT THIS FILE PROVES
  The framework's canonical documents keep ONE owner per fact, and the stated
  semantics cannot drift into any of the claims this ticket forbids:

    - no language-specific tool became a universal hard invariant (RULES.md,
      the B layer, carries none of them)
    - the recommendation matrix stays recommendation-only
    - configured tooling cannot be silently skipped
    - the status value domain has exactly one declaration site
    - the ticket receipt DELEGATES to that domain instead of restating it
    - NOT_CONFIGURED / ENV_BLOCKED / KNOWN_BASELINE_FAILURE do not collapse
      into PASS
    - not every static category must exist in every language
      (NOT_APPLICABLE is legal)
    - formatting is not semantic proof
    - static analysis does not replace tests or review
    - CI actually EXECUTES the static gate (REGISTERED != EXECUTED)

WHAT THIS FILE DOES NOT PROVE
  That any static gate ran for a given change, and that a document's *prose* is
  semantically correct. Marker presence is NOT semantic validation: a
  contradictory sentence passes every check here
  (see test_contradictory_prose_is_explicitly_out_of_scope). That judgement
  belongs to an independent reviewer, not to a string match.
"""
import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "governance", ROOT / "scripts/validate_governance.py")
governance = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(governance)

FRAMEWORK = governance.STATIC_GATE_FRAMEWORK_REL
RECEIPT = governance.STATIC_GATE_RECEIPT_REL
PROFILES = governance.STATIC_GATE_PROFILES_REL
RULES = "RULES.md"
AGENTS = "AGENTS.md"
CI_REL = ".github/workflows/governance-ci.yml"
RUFF_REL = "ruff.toml"
REQS_REL = "requirements-dev.txt"

# Every file the wiring predicate reads, copied into a throwaway tree so a test
# can mutate exactly one of them.
WIRING_FILES = (FRAMEWORK, RECEIPT, PROFILES, RULES, AGENTS, CI_REL,
                RUFF_REL, REQS_REL)

# The seven-value status domain, mirrored here as a TEST FIXTURE ONLY. It is
# not a second declaration site: these tests assert that the domain stays
# declared in exactly one document.
STATUS_DOMAIN = (
    "PASS", "FAIL", "NOT_CONFIGURED", "NOT_APPLICABLE",
    "KNOWN_BASELINE_FAILURE", "ENV_BLOCKED", "EXPLICIT_AUTHORITY_OVERRIDE",
)

NON_COLLAPSE_PAIRS = (
    ("NOT_CONFIGURED", "PASS"),
    ("ENV_BLOCKED", "PASS"),
    ("KNOWN_BASELINE_FAILURE", "PASS"),
    ("TOOL_EXISTS", "TOOL_EXECUTED"),
    ("CONFIG_FILE_EXISTS", "GATE_EXECUTED"),
    ("LINTER_CONFIGURED", "LINTER_PASSED"),
    ("FORMAT_PASS", "LINT_PASS"),
)

# §22: static tools do not replace tests or review.
STATIC_DOES_NOT_REPLACE = (
    "STATIC_ANALYSIS != BEHAVIORAL_CONTRACT_TEST",
    "STATIC_ANALYSIS != ARCHITECTURE_REVIEW",
    "STATIC_ANALYSIS != SECURITY_PROOF",
    "STATIC_ANALYSIS != PRODUCT_CORRECTNESS",
)

# §8/§11: the twenty language profiles the matrix must carry.
PROFILE_LANGUAGES = (
    "JavaScript", "TypeScript", "Python", "Go", "Rust", "Java", "Kotlin",
    "C", "C++", "C#", "Swift", "Ruby", "PHP", "Shell", "Terraform",
    "JSON", "YAML", "TOML", "Dockerfile", "SQL",
)

# Names that must NOT appear in the B layer: a language-specific tool becoming
# a universal hard invariant is the failure this ticket exists to prevent.
LANGUAGE_SPECIFIC_TOOLS = (
    "ruff", "eslint", "oxlint", "biome", "prettier", "mypy", "pyright",
    "pylint", "flake8", "tsc", "clippy", "rustfmt", "gofmt", "go vet",
    "staticcheck", "shellcheck", "shfmt", "bandit", "hadolint", "sqlfluff",
    "yamllint", "taplo", "tflint", "rubocop", "swiftlint", "ktlint", "detekt",
    "checkstyle", "spotbugs", "clang-tidy", "black", "isort", "maven",
)


class StaticGateFrameworkWiringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in WIRING_FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text((ROOT / name).read_text(encoding="utf-8"),
                              encoding="utf-8")

    def mutate(self, rel, old, new):
        path = self.root / rel
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text, f"{rel}: fixture precondition lost ({old!r})")
        path.write_text(text.replace(old, new), encoding="utf-8")

    # -- baseline ---------------------------------------------------------
    def test_intact_wiring(self):
        self.assertEqual(governance.static_gate_wiring(self.root), [])

    def test_missing_file_is_reported(self):
        (self.root / PROFILES).unlink()
        self.assertIn(PROFILES + ": missing file",
                      governance.static_gate_wiring(self.root))

    # -- canonical-owner rules (the only structural checks) ---------------
    def test_status_domain_has_exactly_one_declaration_site(self):
        # CE: the receipt restating the value domain = dual owner.
        self.mutate(RECEIPT, "## 9. STATIC_GATE_RECEIPT",
                    "## 9. STATIC_GATE_RECEIPT\n\n"
                    "EXPLICIT_AUTHORITY_OVERRIDE\n")
        problems = governance.static_gate_wiring(self.root)
        self.assertTrue(
            any("dual owner" in p for p in problems),
            f"restating the status domain was not rejected: {problems}")

    def test_receipt_must_delegate_its_value_domain(self):
        # CE: a receipt that assigns concrete values instead of delegating to
        # the framework's status model loses the single declaration site.
        path = self.root / RECEIPT
        text = path.read_text(encoding="utf-8")
        path.write_text(
            text.replace(governance.STATIC_GATE_RECEIPT_DELEGATION, "PASS"),
            encoding="utf-8")
        problems = governance.static_gate_wiring(self.root)
        self.assertTrue(
            any("value-domain-delegations" in p for p in problems),
            f"receipt re-declaring the domain was not rejected: {problems}")

    def test_framework_status_domain_must_be_complete(self):
        self.mutate(FRAMEWORK, "EXPLICIT_AUTHORITY_OVERRIDE", "SOMETHING_ELSE")
        problems = governance.static_gate_wiring(self.root)
        self.assertTrue(
            any("status-domain-incomplete" in p for p in problems),
            f"an incomplete domain was not rejected: {problems}")

    def test_required_pointers_removal_is_detected(self):
        cases = (
            (AGENTS, "CONFIGURED_STATIC_TOOLING_MUST_RUN"),
            (AGENTS, "STATIC_TOOLING_DISCOVERY"),
            (AGENTS, "references/static-tooling-profiles.md"),
            (FRAMEWORK, "STATIC_GATE_PROFILE"),
            (FRAMEWORK, "MONOREPO RULE"),
            (FRAMEWORK, "LSP_AVAILABLE_ON_ONE_AGENT_MACHINE"),
            (PROFILES, "Canonical owner"),
            (PROFILES, "RECOMMENDED_TYPE_OR_COMPILER_CHECK"),
            (RECEIPT, "CHANGED_LANGUAGE_SURFACES"),
            (RECEIPT, "GIT_DIFF_CHECK"),
            (RECEIPT, "STATIC_GATES_COMPLETE"),
        )
        for name, marker in cases:
            with self.subTest(name=name, marker=marker):
                path = self.root / name
                original = path.read_text(encoding="utf-8")
                path.write_text(original.replace(marker, "REMOVED"),
                                encoding="utf-8")
                self.assertIn(name + ": " + marker,
                              governance.static_gate_wiring(self.root))
                path.write_text(original, encoding="utf-8")

    # -- the claims this ticket forbids -----------------------------------
    def test_rules_md_carries_no_language_specific_tooling_policy(self):
        """Authority placement: the B layer holds no tool-specific policy.

        If a language's tool ever became a universal hard invariant it would
        land here, and this test is where that is caught.
        """
        text = (ROOT / RULES).read_text(encoding="utf-8")
        hits = [tool for tool in LANGUAGE_SPECIFIC_TOOLS
                if re.search(rf"(?<![\w.-]){re.escape(tool)}(?![\w.-])", text, re.I)]
        self.assertEqual(
            [], hits,
            f"{RULES} must carry no language-specific tooling policy; found {hits}")

    def test_profiles_are_recommendation_only(self):
        text = (ROOT / PROFILES).read_text(encoding="utf-8")
        self.assertIn("推荐，不是安装强制", text,
                      "the matrix must state that it is recommendation-only")
        self.assertIn("不是从本表照抄", text,
                      "the matrix must state that commands come from repository "
                      "discovery, not from the table")

    def test_every_language_profile_is_present(self):
        text = (ROOT / PROFILES).read_text(encoding="utf-8")
        missing = [lang for lang in PROFILE_LANGUAGES if lang not in text]
        self.assertEqual([], missing, f"missing language profiles: {missing}")

    def test_status_model_does_not_collapse(self):
        text = (ROOT / FRAMEWORK).read_text(encoding="utf-8")
        absent = [f"{left} != {right}" for left, right in NON_COLLAPSE_PAIRS
                  if not re.search(rf"{left}\s*!=\s*{right}", text)]
        self.assertEqual([], absent, f"non-collapse semantics missing: {absent}")

    def test_status_domain_is_declared_in_the_framework(self):
        text = (ROOT / FRAMEWORK).read_text(encoding="utf-8")
        absent = [state for state in STATUS_DOMAIN if state not in text]
        self.assertEqual([], absent, f"status domain incomplete: {absent}")

    def test_categories_are_not_all_mandatory(self):
        """A missing/unapplicable category must stay legal and stay non-PASS."""
        receipt = (ROOT / RECEIPT).read_text(encoding="utf-8")
        self.assertIn("不要求每个类别都是 PASS", receipt,
                      "the receipt must state that not every category is required")
        self.assertIn("NOT_APPLICABLE", receipt,
                      "NOT_APPLICABLE must be an available, legal outcome")

    def test_static_analysis_does_not_replace_tests_or_review(self):
        text = (ROOT / FRAMEWORK).read_text(encoding="utf-8")
        absent = [m for m in STATIC_DOES_NOT_REPLACE if m not in text]
        self.assertEqual([], absent, f"boundary statements missing: {absent}")

    def test_formatter_is_not_semantic_proof(self):
        text = (ROOT / FRAMEWORK).read_text(encoding="utf-8")
        for marker in ("FORMAT_PASS != LINT_PASS", "FORMAT_PASS != TYPE_PASS",
                       "FORMAT_PASS != CONTRACT_PASS"):
            self.assertIn(marker, text)

    # -- CI: EXECUTED, not merely REGISTERED --------------------------------
    def test_ci_executes_the_static_gate(self):
        ci = (ROOT / CI_REL).read_text(encoding="utf-8")
        self.assertEqual([], governance.static_gate_ci_wiring(ci))

    def test_ci_dependency_without_invocation_is_rejected(self):
        """REGISTERED != EXECUTED: provisioning alone must not satisfy the gate."""
        ci = (ROOT / CI_REL).read_text(encoding="utf-8")
        for invocation in ("ruff check", "compileall"):
            with self.subTest(removed=invocation):
                stripped = "\n".join(
                    line for line in ci.splitlines()
                    if invocation not in line)
                self.assertIn(invocation,
                              governance.static_gate_ci_wiring(stripped))

    def test_pinned_toolchain_is_repository_controlled(self):
        """§14: no reliance on a globally installed binary."""
        reqs = (ROOT / REQS_REL).read_text(encoding="utf-8")
        self.assertRegex(reqs, r"(?m)^ruff==\d+\.\d+\.\d+\s*$",
                         "the static toolchain must be pinned in the repository")
        self.assertTrue((ROOT / RUFF_REL).is_file())
        # The adopted ruleset must select a correctness family, not nothing:
        # an empty selection would make the gate vacuous.
        self.assertRegex((ROOT / RUFF_REL).read_text(encoding="utf-8"),
                         r'select\s*=\s*\[[^\]]*"F"',
                         "the ruleset must include the pyflakes correctness family")

    # -- honest boundary --------------------------------------------------
    def test_contradictory_prose_is_explicitly_out_of_scope(self):
        # Marker presence is a wiring guarantee, not a semantic one. A
        # contradiction appended to a canonical document still passes; only an
        # independent reviewer can reject it. Documented here so no reader
        # mistakes these tests for semantic validation.
        path = self.root / FRAMEWORK
        with path.open("a", encoding="utf-8") as stream:
            stream.write("\nHypothetical contradiction: a linter PASS proves "
                         "the product contract.\n")
        self.assertEqual(governance.static_gate_wiring(self.root), [])


if __name__ == "__main__":
    unittest.main()
