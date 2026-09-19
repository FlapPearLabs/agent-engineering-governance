"""Counterexample-first regression for the P1-T10 on-demand audit visibility
recipe in `references/review-and-repair-saturation.md` (Issue #22 /
`REQ-W4-02a`).

SUPPORT surface (RULES.md R6), NOT an authority surface. This module declares
no competing recipe: it reads the recipe back out of its single canonical
owner and fails when the recipe is absent, when its field group becomes a
mandatory per-ticket field set, when the two completeness outputs are collapsed
into a single completeness flag, when an unqualified conclusion is allowed while
the primary evidence is invisible (`CE-15`), or when the owner starts competing
with the Review Evidence interface it only points at (`CE-28` / `AC-38`).

BINDING (counterexample-first, P1-T10 RED)
    On the pre-landing base the canonical owner ends at `### 6.4`, so there is
    no audit visibility recipe at all: every assertion below fails with an
    explicit RECIPE_ABSENT style message (never an ImportError / broken
    harness). After P1-T10 lands the owner must state, and this module must be
    able to execute:

      * `AC-13` / `CE-15` -- a review that reports a complete conclusion while
        the external primary evidence is `NOT_SEEN` is rejected (or downgraded
        to `MORE_EVIDENCE_REQUIRED`); the same review bounded by an explicit
        incompleteness outcome is accepted. A missing visibility statement
        makes the conclusion non-auditable.
      * `CE-28` / `AC-38` -- the recipe is defined in exactly one canonical
        owner repo-wide; other surfaces only point or link.
      * the field group stays ON DEMAND -- never a mandatory per-ticket field
        set (`REQ-W4-02a`).
      * the two completeness outputs stay two separate outputs and are never
        replaced by one merged completeness flag.

WHY THE PROTECTED-TOKEN ABSENCE ASSERTION LIVES HERE
    `scripts/tests/` is an excluded test surface of the Review Evidence
    single-declaration scan (`scripts/tests/test_review_evidence_contract.py`),
    so naming the protected tokens in this module declares nothing: it only
    locks the property that the audit visibility recipe must express those
    fields by pointer and must NOT carry the Review Evidence field names.

WHY THIS IS NOT A VACUOUS GREP
    `parse_contract` reads the recipe's declarations, field group and rule lines
    out of the document's own fenced blocks, and `decide_audit` is driven by the
    kinds that document declares. `test_contract_is_capture_capable` mutates the
    document text in place and proves that both the parse and the decisions
    follow the text.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC_REL = "references/review-and-repair-saturation.md"
DOC = ROOT / DOC_REL
EVIDENCE_OWNER_REL = "references/review-evidence.md"

# --- recipe expectations ---------------------------------------------------

# The on-demand field group (`REQ-W4-02a` OUTPUT_CONTRACT).
EXPECTED_FIELDS = (
    "evidence",
    "requested SHA",
    "actually read scope",
    "visibility",
    "supports",
    "missing",
    "verdict impact",
    "recovery artifact",
)

# The visibility value domain. Exactly these four, no collapse, no extra.
EXPECTED_VISIBILITY_DOMAIN = ("SEEN", "PARTIAL", "NOT_SEEN", "UNCERTAIN")

# Evidence that is not directly seen cannot support an unqualified conclusion.
INSUFFICIENT_VISIBILITY = ("NOT_SEEN", "PARTIAL", "UNCERTAIN")

# The on-demand scope qualifier `CE-15-D` must carry (RC2-LC-01). `CE-15-D`'s
# trigger is the ABSENCE of a field, and a routine ticket that never opts into
# the recipe has no visibility field by construction -- so an unqualified rule
# would make the on-demand recipe a mandatory per-ticket field set by the back
# door. The rule applies only WHEN THE RECIPE IS ENABLED.
ENABLEMENT_QUALIFIER = "启用本 recipe"

# A record that does not say whether the recipe is in play is read in the
# recipe's own enabled context: the landed `CE-15-D` probe is exactly that case.
# A routine ticket that never opted in declares `recipe_enabled=False`.
RECIPE_IN_PLAY_WHEN_UNSPECIFIED = True

# The two completeness outputs that must stay two separate outputs.
OUTPUT_CONTEXT = "CONTEXT_COMPLETENESS_FOR_DECISION_AUDIT"
OUTPUT_TRANSCRIPT = "FULL_HISTORICAL_TRANSCRIPT_COMPLETENESS"
EXPECTED_COMPLETENESS_OUTPUTS = (OUTPUT_CONTEXT, OUTPUT_TRANSCRIPT)

# Declaration keys the canonical owner must carry.
DECL_RECIPE = "AUDIT_VISIBILITY_RECIPE"
DECL_MANDATORY = "RECIPE_MANDATORY_PER_TICKET"
DECL_DOMAIN = "VISIBILITY_DOMAIN"
DECL_OUTPUTS = "COMPLETENESS_OUTPUTS"
DECL_COLLAPSIBLE = "COMPLETENESS_OUTPUTS_COLLAPSIBLE"

# The recipe's own rules, with the kind that gives each one its meaning.
# Absence and re-typing both turn the checks RED.
EXPECTED_RULES = {
    "CE-15-A": "FORBIDDEN",   # a complete conclusion while primary is NOT_SEEN
    "CE-15-B": "REQUIRED",    # insufficient evidence must yield a bounded outcome
    "CE-15-C": "REQUIRED",    # the two completeness outputs are produced separately
    "CE-15-D": "REQUIRED",    # a missing visibility statement is not auditable
    "CE-15-E": "FORBIDDEN",   # one merged completeness flag standing in for both
    "CE-28-E": "OWNER",       # this recipe's single canonical owner
    "CE-28-F": "POINTER",     # other surfaces only point / link at the recipe
}
# The full rule-kind vocabulary of the canonical owner. The landed section 6
# uses AUTHORITY / REJECT as well, and the section-6 integrity check below must
# be able to read it back; section 7 uses only the first four.
RULE_KINDS = ("AUTHORITY", "FORBIDDEN", "REQUIRED", "OWNER", "POINTER", "REJECT")

# Rule IDs whose single declaration point is the LANDED section 6 (P1-T07).
# Section 7 must be purely additive: it may not restate them.
SECTION_SIX_RULE_IDS = (
    "CE-35-A", "CE-35-B", "CE-35-C",
    "CE-36-A", "CE-36-B", "CE-36-C", "CE-36-D", "CE-36-E", "CE-36-F",
    "CE-38-A", "CE-38-B", "CE-38-C",
    "AC-44-P", "CE-28-D",
)

# The protected Review Evidence field-name / closed-set tokens. Assertion
# input (a lock on this document's pointer discipline), never a declaration
# point -- see the module docstring.
PROTECTED_TOKENS = (
    "IDENTITY_VERSION_OR_DIGEST",
    "semanticScopeStatus",
    "reviewerDecisionRefs",
    "STRUCTURALLY_VALID",
    "SOURCE_VERIFICATION_STATE",
    "EVIDENCE_SUFFICIENCY",
)

# --- document parsing ------------------------------------------------------

SECTION_SEVEN_HEADING_RE = re.compile(r"^(?P<heading>##\s+7\.[^\n]*)$", re.M)
SECTION_SIX_HEADING_RE = re.compile(r"^(?P<heading>##\s+6\.[^\n]*)$", re.M)
NEXT_SECTION_RE = re.compile(r"^##\s", re.M)
FENCE_RE = re.compile(r"^\s*```")

# A declaration line: KEY = VALUE
DECLARATION_RE = re.compile(r"^\s*(?P<key>[A-Z][A-Z0-9_]*)\s*=\s*(?P<value>\S.*?)\s*$")
# A rule line: <RULE-ID> <KIND> <normative text>
RULE_LINE_RE = re.compile(
    r"^\s*(?P<rule>[A-Z]{2,}-\d+-[A-Z])\s+(?P<kind>[A-Z]{3,})\s+(?P<text>\S.*?)\s*$")
# A field line: <lowercase field label> <2+ spaces> <description>
FIELD_LINE_RE = re.compile(r"^\s*(?P<field>[a-z][A-Za-z ]*?)\s{2,}(?P<desc>\S.*?)\s*$")


def _body_after(match: re.Match, text: str) -> str:
    """The body following a level-2 heading match, up to the next level-2 heading."""
    rest = text[match.end():]
    nxt = NEXT_SECTION_RE.search(rest)
    return rest[: nxt.start()] if nxt else rest


def section_six(text: str) -> str:
    match = SECTION_SIX_HEADING_RE.search(text)
    return _body_after(match, text) if match else ""


def section_seven(text: str) -> str:
    match = SECTION_SEVEN_HEADING_RE.search(text)
    return _body_after(match, text) if match else ""


def section_seven_heading(text: str) -> str:
    match = SECTION_SEVEN_HEADING_RE.search(text)
    return match.group("heading") if match else ""


def fenced_block_lines(text: str):
    """Every line that sits inside a fenced block."""
    out, inside = [], False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            inside = not inside
            continue
        if inside:
            out.append(line)
    return out


def parse_contract(section_text: str) -> dict:
    """Read the recipe out of a section's fenced blocks.

    Returns a dict with the declarations, the field group, the visibility domain
    and the rule map -- all read from the document text, never hard-coded.
    """
    declarations: dict = {}
    fields: set = set()
    values: set = set()
    rules: dict = {}
    for line in fenced_block_lines(section_text):
        match = RULE_LINE_RE.match(line)
        if match is not None and match.group("kind") in RULE_KINDS:
            rules[match.group("rule")] = (match.group("kind"), match.group("text"))
            continue
        match = DECLARATION_RE.match(line)
        if match is not None:
            declarations[match.group("key")] = match.group("value")
            continue
        match = FIELD_LINE_RE.match(line)
        if match is not None:
            fields.add(match.group("field"))
    if DECL_DOMAIN in declarations:
        values = {part.strip() for part in declarations[DECL_DOMAIN].split("|") if part.strip()}
    return {
        "declarations": declarations,
        "fields": fields,
        "visibility_domain": values,
        "rules": rules,
    }


def kind_of(contract: dict, rule: str):
    entry = contract["rules"].get(rule)
    return entry[0] if entry else None


def rule_is_scoped_to_enabled_recipe(contract: dict, rule: str) -> bool:
    """Whether the document's own rule TEXT scopes the rule to the enabled case.

    Read from the parsed rule text, never from a constant: deleting the
    qualifier from the canonical owner must stop the rule from firing at all
    (and so fail the two-directional regression below).
    """
    entry = contract["rules"].get(rule)
    return bool(entry) and ENABLEMENT_QUALIFIER in entry[1]


def declared_outputs(contract: dict) -> tuple:
    raw = contract["declarations"].get(DECL_OUTPUTS, "")
    return tuple(part.strip() for part in raw.split(",") if part.strip())


# --- executable audit visibility rule (CE-15) ------------------------------

def clean_audit_record() -> dict:
    """A review that saw its primary evidence and concluded without inflation."""
    return {
        "recipe_enabled": True,
        "visibility_statement_present": True,
        "primary_evidence_visibility": "SEEN",
        "conclusion": "COMPLETE",
        "completeness_outputs": EXPECTED_COMPLETENESS_OUTPUTS,
        "completeness_outputs_merged": False,
    }


def audit_problems(record: dict, contract: dict) -> list:
    """The CE-15 rule violations the parsed contract detects for a record.

    Every check is gated on the kind the document declares for its rule, so a
    rule that is dropped or re-typed stops enforcing (and fails the tests).
    """
    problems = []
    if (kind_of(contract, "CE-15-E") == "FORBIDDEN"
            and record["completeness_outputs_merged"]):
        problems.append("COMPLETENESS_OUTPUTS_COLLAPSED_INTO_A_SINGLE_FLAG")
    if (kind_of(contract, "CE-15-A") == "FORBIDDEN"
            and record["primary_evidence_visibility"] == "NOT_SEEN"
            and record["conclusion"] == "COMPLETE"):
        problems.append("COMPLETE_CONCLUSION_WHILE_PRIMARY_EVIDENCE_NOT_SEEN")
    if (kind_of(contract, "CE-15-C") == "REQUIRED"
            and len(set(record["completeness_outputs"])) < 2):
        problems.append("TWO_COMPLETENESS_OUTPUTS_NOT_PRODUCED_SEPARATELY")
    return problems


def decide_audit(record: dict, contract: dict) -> str:
    """Consume an audit visibility statement.

    ACCEPT / REJECT / NOT_AUDITABLE / MORE_EVIDENCE_REQUIRED. The decisions
    follow the parsed contract, so mutating the document changes them. The
    NOT_AUDITABLE rule is scoped to the ENABLED recipe (`RC2-LC-01`): a routine
    ticket that never opted into the recipe is inert to it, so the absence of a
    visibility statement is not by itself a non-auditable conclusion.
    """
    recipe_in_play = record.get("recipe_enabled", RECIPE_IN_PLAY_WHEN_UNSPECIFIED)
    if (kind_of(contract, "CE-15-D") == "REQUIRED"
            and rule_is_scoped_to_enabled_recipe(contract, "CE-15-D")
            and recipe_in_play
            and not record["visibility_statement_present"]):
        return "NOT_AUDITABLE"
    if audit_problems(record, contract):
        return "REJECT"
    if (kind_of(contract, "CE-15-B") == "REQUIRED"
            and record["primary_evidence_visibility"] in INSUFFICIENT_VISIBILITY):
        return "MORE_EVIDENCE_REQUIRED"
    return "ACCEPT"


def scan_tokens(text: str, tokens) -> list:
    return sorted(token for token in tokens if token in text)


# --- repository-wide single-owner scan (AC-38 / CE-28) ---------------------

TEXT_SUFFIXES = {".md", ".json", ".py", ".yml", ".yaml", ".txt", ".cfg", ".toml"}
EXCLUDED_DIRS = {".git", "__pycache__", ".agent"}
# Test surfaces assert on the declared names; they do not declare them. Both
# discovery roots are excluded explicitly, never silently.
TEST_SURFACE_PREFIXES = ("scripts/tests/", "adapters/zcode/tests/")

# A definition-point claim for this recipe. A pointer from another surface does
# not write the declaration `KEY = ON_DEMAND`, so this marker does not punish
# other surfaces for linking the recipe.
RECIPE_DEFINITION_RE = re.compile(
    r"^\s*" + DECL_RECIPE + r"\s*=\s*ON_DEMAND\s*$", re.M)


def iter_canonical_text_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        relative = path.relative_to(root).as_posix()
        if relative.startswith(TEST_SURFACE_PREFIXES):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        yield relative, path


def scan_recipe_definitions(root: Path) -> set:
    hits = set()
    for relative, path in iter_canonical_text_files(root):
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if RECIPE_DEFINITION_RE.search(text):
            hits.add(relative)
    return hits


class AuditVisibilityRecipeTests(unittest.TestCase):
    def setUp(self):
        self.text = DOC.read_text(encoding="utf-8")
        self.section = section_seven(self.text)
        self.contract = parse_contract(self.section)

    # -- the recipe exists at all ------------------------------------------

    def test_canonical_owner_declares_the_audit_visibility_recipe(self):
        self.assertTrue(
            self.section.strip(),
            f"RECIPE_ABSENT: {DOC_REL} has no `## 7.` section declaring the "
            "on-demand audit visibility recipe")
        self.assertIn(
            "7.", section_seven_heading(self.text),
            f"RECIPE_ABSENT: {DOC_REL} has no numbered `## 7.` heading")

    def test_canonical_owner_literal_retained(self):
        self.assertIn(
            "Canonical owner", self.text,
            "VALIDATOR_INVARIANT_VIOLATED: references-declare-canonical-owner "
            "requires the literal 'Canonical owner' in every references/*.md")

    # -- the on-demand field group -----------------------------------------

    def test_field_group_is_present_and_complete(self):
        self.assertEqual(
            set(EXPECTED_FIELDS), self.contract["fields"],
            f"{DOC_REL} section 7 field group drifted; "
            f"parsed={sorted(self.contract['fields'])}")
        for field in EXPECTED_FIELDS:
            with self.subTest(field=field):
                self.assertRegex(
                    self.section, re.escape(field),
                    f"{DOC_REL} section 7 lost the recipe field {field!r}")

    def test_recipe_is_on_demand_and_not_a_mandatory_field_set(self):
        declarations = self.contract["declarations"]
        self.assertEqual(
            "ON_DEMAND", declarations.get(DECL_RECIPE),
            f"{DOC_REL} section 7 does not declare the recipe as on demand; "
            f"declared={declarations.get(DECL_RECIPE)!r}")
        self.assertEqual(
            "NO", declarations.get(DECL_MANDATORY),
            f"FORBIDDEN (REQ-W4-02a): the recipe must not be a mandatory "
            f"per-ticket field set; declared={declarations.get(DECL_MANDATORY)!r}")
        self.assertIn(
            "按需", self.section,
            f"{DOC_REL} section 7 does not state the recipe is on demand (按需)")

    def test_visibility_domain_is_the_exact_closed_set(self):
        self.assertEqual(
            set(EXPECTED_VISIBILITY_DOMAIN), self.contract["visibility_domain"],
            f"VISIBILITY_DOMAIN drifted; "
            f"parsed={sorted(self.contract['visibility_domain'])}")
        for value in EXPECTED_VISIBILITY_DOMAIN:
            with self.subTest(value=value):
                self.assertIn(
                    value, self.section,
                    f"{DOC_REL} section 7 does not state the visibility value {value}")

    # -- the two completeness outputs stay two outputs ----------------------

    def test_two_completeness_outputs_are_distinct_and_both_declared(self):
        outputs = declared_outputs(self.contract)
        self.assertEqual(
            EXPECTED_COMPLETENESS_OUTPUTS, tuple(sorted(outputs)),
            f"{DOC_REL} section 7 does not declare the two completeness outputs "
            f"separately; declared={outputs}")
        self.assertEqual(
            len(set(outputs)), len(outputs),
            f"COLLAPSE: the two completeness outputs must be distinct; got={outputs}")
        for name in EXPECTED_COMPLETENESS_OUTPUTS:
            with self.subTest(output=name):
                self.assertIn(name, self.section)

    def test_a_single_merged_completeness_flag_is_forbidden(self):
        self.assertEqual(
            "NO", self.contract["declarations"].get(DECL_COLLAPSIBLE),
            f"FORBIDDEN: one merged completeness output must not stand in for "
            f"both; declared={self.contract['declarations'].get(DECL_COLLAPSIBLE)!r}")
        self.assertEqual("FORBIDDEN", kind_of(self.contract, "CE-15-E"))
        self.assertEqual("REQUIRED", kind_of(self.contract, "CE-15-C"))
        merged = clean_audit_record()
        merged["completeness_outputs_merged"] = True
        self.assertEqual(
            "REJECT", decide_audit(merged, self.contract),
            "a review collapsing the two completeness outputs into one flag "
            "must be rejected")
        single = clean_audit_record()
        single["completeness_outputs"] = (OUTPUT_CONTEXT,)
        self.assertEqual(
            "REJECT", decide_audit(single, self.contract),
            "a review producing only one of the two completeness outputs must "
            "be rejected")
        self.assertEqual("ACCEPT", decide_audit(clean_audit_record(), self.contract))

    # -- CE-15 / AC-13: bounded conclusion when primary evidence is invisible

    def test_complete_conclusion_on_invisible_primary_evidence_is_rejected(self):
        """CE-15: the red case; the bounded case is the accepted form."""
        self.assertEqual("FORBIDDEN", kind_of(self.contract, "CE-15-A"))
        invisible = clean_audit_record()
        invisible["primary_evidence_visibility"] = "NOT_SEEN"
        invisible["conclusion"] = "COMPLETE"
        self.assertIn(
            "COMPLETE_CONCLUSION_WHILE_PRIMARY_EVIDENCE_NOT_SEEN",
            audit_problems(invisible, self.contract))
        self.assertEqual(
            "REJECT", decide_audit(invisible, self.contract),
            "an external review giving a complete conclusion while the primary "
            "evidence is invisible must be rejected")

        bounded = clean_audit_record()
        bounded["primary_evidence_visibility"] = "NOT_SEEN"
        bounded["conclusion"] = "BOUNDED"
        self.assertEqual(
            [], audit_problems(bounded, self.contract),
            "a bounded conclusion must not carry the CE-15 rule violation")
        self.assertEqual(
            "MORE_EVIDENCE_REQUIRED", decide_audit(bounded, self.contract),
            "the same review bounded by an explicit incompleteness outcome must "
            "be accepted as MORE_EVIDENCE_REQUIRED, not rejected")

    def test_insufficient_evidence_never_yields_an_unqualified_accept(self):
        self.assertEqual("REQUIRED", kind_of(self.contract, "CE-15-B"))
        for visibility in INSUFFICIENT_VISIBILITY:
            with self.subTest(visibility=visibility):
                record = clean_audit_record()
                record["primary_evidence_visibility"] = visibility
                record["conclusion"] = "BOUNDED"
                self.assertNotEqual(
                    "ACCEPT", decide_audit(record, self.contract),
                    "insufficient primary evidence must not yield an unqualified ACCEPT")
        self.assertEqual(
            "ACCEPT", decide_audit(clean_audit_record(), self.contract),
            "a fully seen primary evidence with both outputs must be accepted")

    def test_missing_visibility_statement_makes_the_conclusion_non_auditable(self):
        self.assertEqual("REQUIRED", kind_of(self.contract, "CE-15-D"))
        silent = clean_audit_record()
        silent["visibility_statement_present"] = False
        silent["primary_evidence_visibility"] = None
        self.assertEqual(
            "NOT_AUDITABLE", decide_audit(silent, self.contract),
            "a review that never states what evidence it saw is not auditable")

    # -- RC2-LC-01: the NOT_AUDITABLE rule is scoped to the ENABLED recipe ---
    # (`REQ-W4-02a`: the recipe is on demand, never a mandatory per-ticket
    # field set. `CE-15-D`'s trigger is the ABSENCE of a field, so an
    # unqualified rule would make every routine ticket non-auditable.)

    def test_routine_ticket_is_not_rendered_not_auditable_without_enabling_the_recipe(self):
        """Direction 1 of the two-directional regression (the violation).

        A routine ticket that never opted into the recipe carries no visibility
        statement by construction -- exactly what the on-demand declaration in
        section 7.1 permits. It must NOT therefore be rendered NOT_AUDITABLE
        and barred as a PASS basis.
        """
        self.assertEqual("REQUIRED", kind_of(self.contract, "CE-15-D"))
        routine = clean_audit_record()
        routine["recipe_enabled"] = False
        routine["visibility_statement_present"] = False
        routine["primary_evidence_visibility"] = None
        decision = decide_audit(routine, self.contract)
        self.assertNotEqual(
            "NOT_AUDITABLE", decision,
            "FORBIDDEN (REQ-W4-02a): a routine ticket that has NOT enabled the "
            "recipe must not be rendered NOT_AUDITABLE merely because no "
            "visibility statement is present -- the recipe is inert unless "
            "enabled, so it can never be mandatory per ticket by the back door")
        self.assertEqual(
            "ACCEPT", decision,
            "a ticket that never opted into the recipe keeps the ordinary "
            "decision; the recipe adds no field requirement to it")

    def test_not_auditable_is_scoped_to_the_enabled_recipe(self):
        """Direction 2: the fix must not be a no-op, and must follow the text.

        The scoping is read out of the canonical owner's own `CE-15-D` rule
        text, and with the recipe ENABLED a missing visibility statement is
        still non-auditable.
        """
        self.assertTrue(
            rule_is_scoped_to_enabled_recipe(self.contract, "CE-15-D"),
            f"{DOC_REL} CE-15-D does not scope its NOT_AUDITABLE rule to the "
            "enabled recipe; every routine ticket would be non-auditable")
        self.assertRegex(
            self.section, re.escape(ENABLEMENT_QUALIFIER),
            f"{DOC_REL} section 7 does not state the enabled-recipe scope")
        self.assertIn(
            "未启用", self.section,
            f"{DOC_REL} section 7 does not state the default: an un-enabled "
            "routine ticket is not rendered NOT_AUDITABLE for a missing "
            "visibility statement")

        enabled = clean_audit_record()
        enabled["recipe_enabled"] = True
        enabled["visibility_statement_present"] = False
        enabled["primary_evidence_visibility"] = None
        self.assertEqual(
            "NOT_AUDITABLE", decide_audit(enabled, self.contract),
            "over-correction: with the recipe ENABLED a missing visibility "
            "statement must still make the conclusion non-auditable")

        routine = clean_audit_record()
        routine["recipe_enabled"] = False
        routine["visibility_statement_present"] = False
        routine["primary_evidence_visibility"] = None
        self.assertNotEqual(
            "NOT_AUDITABLE", decide_audit(routine, self.contract),
            "the default must be stated: an un-enabled routine ticket is not "
            "rendered NOT_AUDITABLE")

        # non-vacuity: the scoping is read from the document text, not hard-coded
        unscoped = re.sub(
            r"(CE-15-D\s+REQUIRED\s+)" + re.escape(ENABLEMENT_QUALIFIER),
            r"\1", self.section, count=1)
        self.assertNotEqual(
            self.section, unscoped,
            "the CE-15-D scoping qualifier is not present in the document")
        unscoped_contract = parse_contract(unscoped)
        self.assertFalse(
            rule_is_scoped_to_enabled_recipe(unscoped_contract, "CE-15-D"),
            "removing the qualifier from the CE-15-D text did not change the parse")
        self.assertNotEqual(
            "NOT_AUDITABLE", decide_audit(enabled, unscoped_contract),
            "the enabled-recipe rule did not follow the CE-15-D document text")

    def test_owner_and_pointer_discipline_for_the_recipe(self):
        self.assertEqual("OWNER", kind_of(self.contract, "CE-28-E"))
        self.assertEqual("POINTER", kind_of(self.contract, "CE-28-F"))
        self.assertIn(
            DOC_REL, self.section,
            f"{DOC_REL} section 7 does not name its own single canonical owner")
        self.assertIn(
            EVIDENCE_OWNER_REL, self.section,
            f"{DOC_REL} section 7 does not name the Review Evidence interface it "
            "must only point at")

    # -- AC-38 / CE-28: single owner, no protected field names -------------

    def test_recipe_is_declared_in_exactly_one_canonical_file(self):
        declarations = scan_recipe_definitions(ROOT)
        self.assertEqual(
            {DOC_REL}, declarations,
            "SINGLE_OWNER (AC-38): the audit visibility recipe must be defined in "
            f"exactly one canonical owner; found={sorted(declarations)}")
        self.assertRegex(
            self.text, RECIPE_DEFINITION_RE,
            f"{DOC_REL} does not carry the recipe's definition point")

    def test_single_owner_scan_is_not_vacuous(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "references").mkdir(parents=True)
            (root / "scripts" / "tests").mkdir(parents=True)
            body = f"{DECL_RECIPE} = ON_DEMAND\n"
            (root / "references/competing-audit-visibility.md").write_text(
                "# competing declaration\n" + body, encoding="utf-8")
            (root / "scripts/tests/test_probe.py").write_text(body, encoding="utf-8")
            found = scan_recipe_definitions(root)
            self.assertIn(
                "references/competing-audit-visibility.md", found,
                "SINGLE_OWNER_SCAN_VACUOUS: an injected competing canonical owner "
                "went undetected")
            self.assertNotIn(
                "scripts/tests/test_probe.py", found,
                "the declared test-surface exclusion must hold")

    def test_the_recipe_does_not_declare_the_protected_field_names(self):
        """CE-28 / AC-38: the recipe points at the interface, never restates it."""
        found = scan_tokens(self.text, PROTECTED_TOKENS)
        self.assertEqual(
            [], found,
            f"DUAL_DECLARATION (CE-28): {DOC_REL} declares the Review Evidence "
            f"field-name contract outside the single interface; unexpected={found}")

    def test_protected_token_scan_is_not_vacuous(self):
        control = "| field | note |\n| --- | --- |\n| `semanticScopeStatus` | x |\n"
        self.assertTrue(
            scan_tokens(control, PROTECTED_TOKENS),
            "the protected-token scan is vacuous: it missed an injected "
            "competing declaration")
        self.assertEqual(sorted(PROTECTED_TOKENS),
                         scan_tokens(" ".join(PROTECTED_TOKENS), PROTECTED_TOKENS))

    # -- the landed section 6 is untouched and section 7 is additive ---------

    def test_landed_section_six_is_still_intact(self):
        six = section_six(self.text)
        self.assertTrue(six.strip(), f"{DOC_REL} lost section 6 entirely")
        six_contract = parse_contract(six)
        missing = [rule for rule in SECTION_SIX_RULE_IDS
                   if rule not in six_contract["rules"]]
        self.assertEqual(
            [], missing,
            f"P1-T07 REGRESSION: {DOC_REL} section 6 lost the landed rule(s) "
            f"{missing}")
        for heading in ("### 6.1", "### 6.2", "### 6.3", "### 6.4"):
            with self.subTest(heading=heading):
                self.assertIn(
                    heading, six,
                    f"P1-T07 REGRESSION: {DOC_REL} section 6 lost {heading}")
        self.assertIn(
            EVIDENCE_OWNER_REL, six,
            "P1-T07 REGRESSION: section 6 no longer points at the Review "
            "Evidence interface")

    def test_legacy_review_grading_sections_retained(self):
        for marker in ("## 1. 评审分级（L0/L1/L2）", "## 4. PASS 语义与 findings 处置"):
            with self.subTest(marker=marker):
                self.assertIn(
                    marker, self.text,
                    f"{DOC_REL} lost the pre-existing section {marker!r}")

    def test_section_seven_is_additive_and_does_not_restate_section_six(self):
        self.assertTrue(
            SECTION_SIX_HEADING_RE.search(self.text)
            and SECTION_SEVEN_HEADING_RE.search(self.text),
            f"{DOC_REL} must carry both the landed section 6 and the new section 7")
        self.assertLess(
            SECTION_SIX_HEADING_RE.search(self.text).start(),
            SECTION_SEVEN_HEADING_RE.search(self.text).start(),
            "section 7 must be appended after the landed section 6")
        restated = sorted(
            rule for rule in SECTION_SIX_RULE_IDS
            if rule in self.contract["rules"])
        self.assertEqual(
            [], restated,
            f"ADDITIVITY: section 7 must not restate the section 6 rule(s) "
            f"{restated}; section 6 remains their single declaration point")

    # -- non-vacuity: the parse and the decisions follow the document --------

    def test_contract_is_capture_capable(self):
        """Mutating the document text must change both parse and decisions."""
        self.assertTrue(self.contract["rules"], "the recipe parser read no rule lines")
        self.assertEqual(
            {rule: kind for rule, kind in EXPECTED_RULES.items()},
            {rule: kind_of(self.contract, rule) for rule in EXPECTED_RULES},
            f"{DOC_REL} section 7 does not declare the expected rules; "
            f"parsed={sorted(self.contract['rules'])}")

        invisible = clean_audit_record()
        invisible["primary_evidence_visibility"] = "NOT_SEEN"
        invisible["conclusion"] = "COMPLETE"

        # (a) inverting the bounded-conclusion rule stops it enforcing
        retyped = re.sub(r"^(\s*CE-15-A\s+)FORBIDDEN\b", r"\1AUTHORITY",
                         self.section, flags=re.M)
        retyped_contract = parse_contract(retyped)
        self.assertNotEqual(self.contract["rules"], retyped_contract["rules"],
                            "the recipe parser is not reading the document text")
        self.assertEqual("REJECT", decide_audit(invisible, self.contract))
        self.assertNotEqual(
            "REJECT", decide_audit(invisible, retyped_contract),
            "re-typing CE-15-A away from FORBIDDEN did not change the decision")

        # (b) dropping the on-demand declaration stops the on-demand property
        without_mode = "\n".join(
            line for line in self.section.splitlines()
            if not re.match(r"^\s*" + DECL_RECIPE + r"\s*=", line))
        dropped = parse_contract(without_mode)
        self.assertEqual("ON_DEMAND", self.contract["declarations"][DECL_RECIPE])
        self.assertIsNone(dropped["declarations"].get(DECL_RECIPE))

        # (c) dropping a field changes the parsed field group
        without_field = "\n".join(
            line for line in self.section.splitlines()
            if not FIELD_LINE_RE.match(line)
            or FIELD_LINE_RE.match(line).group("field") != "recovery artifact")
        self.assertIn("recovery artifact", self.contract["fields"])
        self.assertNotIn("recovery artifact", parse_contract(without_field)["fields"])


if __name__ == "__main__":
    unittest.main()
