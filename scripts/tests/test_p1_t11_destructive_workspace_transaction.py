"""Counterexample-driven regression checks for the destructive workspace
transaction recipe in `references/git-ci-integration.md` section 5.2 (P1-T11,
REQ-W4-02b).

SUPPORT surface (RULES.md R6), NOT an authority surface. This module declares no
recipe field and no requirement of its own: it re-reads the canonical reference
and fails when the destructive workspace transaction loses its ordered
transaction, its preferred baseline, its lane isolation, its preservation
obligations, its post-state record, its destructive-only applicability, its
NOT-a-global-stash-ban non-decision, or its recorded underlying cause.

BINDING (references/ticket-lane.md section 4, counterexample-first)
    The recipe itself is a document fact: it is located by marker groups over
    the non-blank lines of section 5.2, so mutating (or deleting) a normative
    sentence turns the corresponding probe RED instead of passing CI silently.
    The `PROBE` table and its anti-vacuity mutations at the bottom perform
    exactly that mutation in memory and require the probe to flip.

    The constants below (`RECIPE_SIGNATURE`, `EXPECTED_STEPS`, the marker
    groups) are ASSERTION INPUTS -- a lock read back from the producer -- never a
    second declaration point of the recipe. The one normative declaration point
    of the recipe is section 5.2 of the canonical owner; see
    `test_the_recipe_is_declared_in_exactly_one_canonical_file`.

    The recipe is not restated here and the P1-T03 integration closure evidence
    is not touched: section 5.2 must not mention any P1-T03-owned marker, and the
    landed section 4/5/5.1 content must still be present.

Counterexamples exercised here (parent spec section 9): CE-16 (a preservation
step that loses a tracked modification or an untracked artefact must be
rejected), CE-28 (a recipe defined in two canonical files has a dual owner and
must be rejected and converged onto one). The ticket STATE_CONTRACT is executed
as a small resolver rather than asserted as prose alone:
LEGAL = a destructive action with a recorded pre-state, a preserved set and a
recorded post-state; ILLEGAL = without preservation / without a post-state
record / a blanket global stash prohibition presented as a rule.

RED condition before P1-T11 lands: the canonical owner carries no ordered
destructive transaction, so a destructive action can be performed with no
pre-state, no preservation and no post-state. Every probe below FAILS.

Stdlib only. Run with:
    python3 -m unittest scripts.tests.test_p1_t11_destructive_workspace_transaction
"""
from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GIT_CI_REL = "references/git-ci-integration.md"
GIT_CI = ROOT / GIT_CI_REL
TICKET_LANE_REL = "references/ticket-lane.md"

# The landed P1-T03 anchors (section 4/5 headings and the section 5.1
# subsection). This module only asserts they survive; it never restates them.
SECTION_4_HEADING = "## 4. Scope 核验（L0；语义优先）"
SECTION_5_HEADING = "## 5. Exact-SHA 评审协议"
SECTION_5_1_HEADING = "### 5.1 集成关闭证据（INTEGRATION CLOSURE EVIDENCE）"

# The subsection this ticket adds: the natural home is section 5.
SECTION_5_2_HEADING = (
    "### 5.2 破坏性工作区事务（DESTRUCTIVE_WORKSPACE_TRANSACTION）")

RECIPE_ID = "DESTRUCTIVE_WORKSPACE_TRANSACTION"
# The ordered transaction, byte-exact as the document must render it.
RECIPE_SIGNATURE = (
    "status -> uncommitted / untracked / owner -> preserve -> operate -> "
    "post-state")
EXPECTED_STEPS = ("status", "uncommitted / untracked / owner", "preserve",
                  "operate", "post-state")
ORDER_TOKENS = ("status", "uncommitted", "untracked", "owner", "preserve",
                "operate", "post-state")

# Markers owned by P1-T03 (section 5.1): the new subsection must not restate or
# alter them, so it must not name them at all.
P1_T03_OWNED_MARKERS = (
    "CLOSURE-REQUIRED", "DISCONNECTED", "DYNAMIC-PATH", "TEST-CALLER",
    "NO-CALLER-PATH", "N/A-PATH", "INTEGRATION_COMPLETE", "TEST_ONLY_CALLERS",
    "REAL_ENTRYPOINT", "PRODUCTION_CALL_CHAIN", "OBSERVED_PRODUCTION_EFFECT",
    "PRODUCTION_CALLERS", "RUNTIME_REACHABLE", "EVIDENCE_REF",
)

TEXT_SUFFIXES = (".md", ".py", ".json", ".yml", ".yaml", ".txt", ".cfg",
                 ".toml")
EXCLUDED_DIRS = {".git", "__pycache__", ".agent"}
# Declared explicitly, never silently: a test surface asserts on a declared
# fact, it does not declare it. Both discovery roots are excluded, so the scan
# cannot be satisfied by this module's own constants.
TEST_SURFACE_PREFIXES = ("scripts/tests/", "adapters/zcode/tests/")

FENCE_RE = re.compile(r"^\s*```")
NEXT_HEADING_RE = re.compile(r"^#{2,3} ", re.M)
SECTION_RE = re.compile(r"^##\s+(\d+)\.", re.M)
FIELD_ENTRY_RE = re.compile(
    r"^\s*[A-Z][A-Z0-9_]*(?:\s*/\s*[A-Z][A-Z0-9_]*)*\s*(?:#.*)?$")

# ==========================================================================
# document helpers
# ==========================================================================

def section_body(text: str, number: int) -> str:
    """Body of `## <number>. ...` up to the next level-2 heading."""
    headings = list(SECTION_RE.finditer(text))
    for index, match in enumerate(headings):
        if int(match.group(1)) != number:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        return text[match.end():end]
    return ""


def subsection_body(text: str, heading: str) -> str:
    """Body of a `### ...` subsection up to the next level-2/3 heading."""
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


def recipe_line(body: str) -> str:
    """The line that renders the ordered transaction, or ''."""
    for block in fenced_blocks(body):
        for line in block:
            if "->" in line and line.strip():
                return line.strip()
    return ""


def recipe_steps(body: str):
    """The arrow-separated steps of the documented transaction, as rendered."""
    line = recipe_line(body)
    if not line:
        return ()
    return tuple(step.strip() for step in line.split("->"))


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
    """Canonical text files naming the recipe identifier exactly once."""
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
REJECT_WITHOUT_PRESERVATION = "REJECT_WITHOUT_PRESERVATION"
REJECT_LOST_WORK = "REJECT_LOST_WORK"
REJECT_BLANKET_STASH_PROHIBITION = "REJECT_BLANKET_STASH_PROHIBITION"
INVALID_WITHOUT_PRE_STATE = "INVALID_WITHOUT_PRE_STATE"
INVALID_WITHOUT_POST_STATE = "INVALID_WITHOUT_POST_STATE"
INVALID_OUT_OF_ORDER = "INVALID_OUT_OF_ORDER"
NOT_APPLICABLE = "NOT_APPLICABLE"


def transaction_verdict(record: dict, steps) -> str:
    """Dispose of a destructive-transaction record against the DOCUMENTED order.

    The `steps` argument is the order parsed out of the canonical file, so a
    drift of the documented transaction changes the verdict instead of passing
    silently. The documented contract:
      - the recipe applies to destructive actions only;
      - a preservation step that loses a tracked modification or an untracked
        artefact is a reject, not a warning;
      - a missing pre-state or post-state record makes the transaction invalid;
      - a blanket global stash prohibition is presented as a rule, so a record
        that carries one is rejected rather than accepted.
    """
    if record.get("blanketStashBan"):
        return REJECT_BLANKET_STASH_PROHIBITION
    if record.get("scope") != "destructive":
        return NOT_APPLICABLE
    if not record.get("preState"):
        return INVALID_WITHOUT_PRE_STATE
    preserved = set(record.get("preserved") or ())
    searched = set(record.get("artefactsSeen") or ())
    if searched - preserved:
        return REJECT_LOST_WORK
    if not record.get("preserved"):
        return REJECT_WITHOUT_PRESERVATION
    if not record.get("postState"):
        return INVALID_WITHOUT_POST_STATE
    if tuple(record.get("steps") or ()) != tuple(steps):
        return INVALID_OUT_OF_ORDER
    return LEGAL_VERDICT


def legal_record(steps):
    """The LEGAL record of the documented state contract."""
    return {
        "scope": "destructive",
        "steps": tuple(steps),
        "preState": "worktree read: no untracked artefacts, no uncommitted edits",
        "artefactsSeen": ("tracked modification", "untracked artefact"),
        "preserved": ("tracked modification", "untracked artefact"),
        "postState": "worktree re-read after the operation; branch tip recorded",
    }


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
# the normative rules of section 5.2, decomposed into marker groups
# ==========================================================================

# The ordered transaction must be located on an actual arrow chain, so the
# probe cannot be satisfied by a gloss that merely names the steps.
ORDERED_GROUPS = (
    ("status -> ",),
    ("uncommitted / untracked / owner",),
    (" -> preserve",),
    (" -> operate",),
    (" -> post-state",),
)

BASELINE_GROUPS = (
    ("独立", "independent"),
    ("干净", "clean"),
    ("worktree",),
    ("优先", "preferred"),
    ("baseline",),
)

LANE_GROUPS = (
    ("其它 lane", "another lane", "other lane"),
    ("绝不", "never", "must not"),
    ("触碰", "touch"),
)

TRACKED_LOSS_GROUPS = (
    ("tracked 修改",),
    ("不得静默丢失", "may not silently lose", "must not silently lose"),
    ("reject", "拒绝"),
)

UNTRACKED_LOSS_GROUPS = (
    ("untracked 产物",),
    ("不得静默丢失", "may not silently lose", "must not silently lose"),
    ("reject", "拒绝"),
)

POST_STATE_GROUPS = (
    ("post-state",),
    ("无效", "invalid"),
    ("没有记录", "without a record", "missing"),
)

APPLICABILITY_GROUPS = (
    ("仅限", "limited to"),
    ("破坏性动作", "destructive action"),
    ("不触发", "does not apply"),
)

NO_GLOBAL_BAN_GROUPS = (
    ("全局", "global"),
    ("stash",),
    ("不构成", "does not establish"),
)

CAUSE_GROUPS = (
    ("NEEDS_PRIMARY_EVIDENCE_RECOVERY",),
    ("不推广", "not generalis", "never generalise"),
    ("记录", "recorded"),
)

CE_16_GROUPS = (
    ("CE-16",),
    ("tracked",),
    ("untracked",),
    ("loses", "丢失"),
    ("REJECT", "拒绝"),
)

CE_28_GROUPS = (
    ("CE-28",),
    ("dual owner", "second canonical", "双 owner"),
    ("REJECT", "拒绝"),
)

PROBES = {
    "ordered_transaction_is_an_ordered_sequence": ORDERED_GROUPS,
    "preferred_baseline_is_an_independent_clean_worktree": BASELINE_GROUPS,
    "lane_isolation_is_stated": LANE_GROUPS,
    "tracked_modification_loss_is_rejected": TRACKED_LOSS_GROUPS,
    "untracked_artefact_loss_is_rejected": UNTRACKED_LOSS_GROUPS,
    "destructive_action_without_a_post_state_is_invalid": POST_STATE_GROUPS,
    "applicability_is_limited_to_destructive_actions": APPLICABILITY_GROUPS,
    "no_blanket_stash_prohibition_is_established": NO_GLOBAL_BAN_GROUPS,
    "the_underlying_cause_is_recorded": CAUSE_GROUPS,
    "counterexample_ce_16_is_stated": CE_16_GROUPS,
    "counterexample_ce_28_is_stated": CE_28_GROUPS,
}

# Anti-vacuity mutations: each removes one required marker group from the SAME
# live text and must flip its probe to False. Every mutation inverts an
# obligation, deletes a prohibition, or turns a prohibition into a permission.
PROBE_MUTATIONS = {
    "ordered_transaction_is_an_ordered_sequence": (
        " -> preserve -> operate -> ", " -> operate -> "),
    "preferred_baseline_is_an_independent_clean_worktree": (
        "在一个独立、干净的 worktree 上建立基线"
        "（preferred baseline = independent clean worktree）",
        "在一个共享的 worktree 上建立基线（shared worktree）"),
    "lane_isolation_is_stated": (
        "绝不**触碰其它 lane 的工作", "可以**触碰其它 lane 的工作"),
    "tracked_modification_loss_is_rejected": (
        "不得静默丢失 tracked 修改", "可以静默丢失 tracked 修改"),
    "untracked_artefact_loss_is_rejected": (
        "不得静默丢失 untracked 产物", "可以静默丢失 untracked 产物"),
    "destructive_action_without_a_post_state_is_invalid": (
        "该事务**无效**（invalid）", "该事务**有效**（valid）"),
    "applicability_is_limited_to_destructive_actions": (
        "仅限破坏性动作", "适用于任何动作"),
    "no_blanket_stash_prohibition_is_established": (
        "不构成 blanket / global stash prohibition",
        "构成 blanket / global stash prohibition"),
    "the_underlying_cause_is_recorded": (
        "NEEDS_PRIMARY_EVIDENCE_RECOVERY", "NEEDS_GENERAL_STASH_BAN"),
    "counterexample_ce_16_is_stated": (
        "preservation loses a tracked modification or an untracked artefact -> REJECT",
        "preservation loses a tracked modification or an untracked artefact -> WARNING"),
    "counterexample_ce_28_is_stated": (
        "the recipe is declared in a second canonical file (dual owner) -> REJECT",
        "the recipe is declared in a second canonical file (dual owner) -> ACCEPT"),
}


class DestructiveWorkspaceTransactionTests(unittest.TestCase):
    def setUp(self):
        self.text = GIT_CI.read_text(encoding="utf-8")
        self.section5 = section_body(self.text, 5)
        self.body = subsection_body(self.text, SECTION_5_2_HEADING)

    # -- placement and scope of the new subsection -------------------------

    def test_section_5_2_lives_under_the_landed_section_5(self):
        self.assertIn(
            SECTION_5_2_HEADING, self.text,
            f"{GIT_CI_REL} does not carry the destructive workspace "
            f"transaction subsection {SECTION_5_2_HEADING!r}")
        self.assertIn(
            SECTION_5_2_HEADING, self.section5,
            f"{GIT_CI_REL}: the new subsection must live under section 5, whose "
            f"anchor `git-ci-integration.md#5-exact-sha-评审协议` is cited by "
            f"references/execution-stage.md")
        self.assertLess(
            self.text.index(SECTION_5_1_HEADING),
            self.text.index(SECTION_5_2_HEADING),
            "the new subsection must be appended after the landed section 5.1")
        self.assertTrue(
            self.body.strip(), f"{GIT_CI_REL} section 5.2 is empty")

    # -- the ordered transaction -------------------------------------------

    def test_the_recipe_is_rendered_as_an_ordered_transaction(self):
        steps = recipe_steps(self.body)
        self.assertEqual(
            list(steps), list(EXPECTED_STEPS),
            f"{GIT_CI_REL} section 5.2 must render the ordered transaction "
            f"{' -> '.join(EXPECTED_STEPS)!r}; rendered={' -> '.join(steps)!r}")
        line = recipe_line(self.body)
        positions = [line.index(token) for token in ORDER_TOKENS]
        self.assertEqual(
            positions, sorted(positions),
            f"{GIT_CI_REL}: the transaction steps are not in order in {line!r}")

    def test_the_order_check_rejects_a_reordered_recipe(self):
        """Non-vacuity: swapping two steps must break the ordering check."""
        mutated = self.body.replace(
            "-> preserve -> operate", "-> operate -> preserve")
        self.assertNotEqual(mutated, self.body)
        line = recipe_line(mutated)
        positions = [line.index(token) for token in ORDER_TOKENS]
        self.assertNotEqual(
            positions, sorted(positions),
            "the ordering check is VACUOUS: reordering preserve/operate did "
            "not turn it RED")

    def test_the_ordered_transaction_names_every_step_and_the_owner(self):
        self.assertTrue(
            probe(self.body, ORDERED_GROUPS),
            f"{GIT_CI_REL} section 5.2 must state the ordered transaction "
            f"`status -> uncommitted / untracked / owner -> preserve -> "
            f"operate -> post-state` on one statement")

    # -- baseline, isolation, preservation, post-state ---------------------

    def test_a_clean_independent_worktree_is_the_preferred_baseline(self):
        self.assertTrue(
            probe(self.body, BASELINE_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not state that a clean independent "
            f"worktree is the preferred baseline of a destructive action")

    def test_lane_isolation_is_stated_as_a_prohibition(self):
        self.assertTrue(
            probe(self.body, LANE_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not prohibit touching another "
            f"lane's work")

    def test_losing_a_tracked_modification_during_preservation_is_rejected(self):
        self.assertTrue(
            probe(self.body, TRACKED_LOSS_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not reject a preservation step "
            f"that silently loses a tracked modification (CE-16)")

    def test_losing_an_untracked_artefact_during_preservation_is_rejected(self):
        self.assertTrue(
            probe(self.body, UNTRACKED_LOSS_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not reject a preservation step "
            f"that silently loses an untracked artefact (CE-16)")

    def test_a_destructive_action_without_a_post_state_record_is_invalid(self):
        self.assertTrue(
            probe(self.body, POST_STATE_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not state that a destructive "
            f"action without a recorded post-state is invalid")

    def test_applicability_is_limited_to_destructive_actions(self):
        self.assertTrue(
            probe(self.body, APPLICABILITY_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not limit the recipe to "
            f"destructive actions")

    # -- the non-decision on global stash bans -----------------------------

    def test_no_blanket_stash_prohibition_is_established(self):
        self.assertTrue(
            probe(self.body, NO_GLOBAL_BAN_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not state that the recipe "
            f"establishes NO blanket / global stash prohibition")

    def test_the_underlying_cause_is_recorded_not_generalised(self):
        self.assertTrue(
            probe(self.body, CAUSE_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not record the underlying cause "
            f"NEEDS_PRIMARY_EVIDENCE_RECOVERY as a recorded fact that is not "
            f"generalised into a rule")

    def test_the_no_global_ban_wording_is_not_readable_as_a_ban(self):
        """The recipe must not contain a positive global-ban instruction."""
        banned = [line for line in statements(self.body)
                  if "stash" in line.lower()
                  and any(marker in line for marker in
                          ("禁止使用 stash", "禁用 stash", "never stash",
                           "must not stash", "stash 一律禁止"))]
        self.assertEqual(
            banned, [],
            f"{GIT_CI_REL}: a blanket/global stash prohibition was introduced "
            f"as a rule: {banned}")

    # -- counterexamples ---------------------------------------------------

    def test_counterexample_ce_16_is_stated(self):
        self.assertTrue(
            probe(self.body, CE_16_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not state CE-16 (a preservation "
            f"step that loses a tracked modification or an untracked artefact "
            f"must be rejected)")

    def test_counterexample_ce_28_is_stated(self):
        self.assertTrue(
            probe(self.body, CE_28_GROUPS),
            f"{GIT_CI_REL} section 5.2 does not state CE-28 (a recipe defined "
            f"in a second canonical file has a dual owner and must be rejected "
            f"and converged)")

    # -- the state contract, executed --------------------------------------

    def test_the_rendered_state_contract_is_legal_and_illegal_rows(self):
        legal, illegal = state_entries(block_after_label(
            self.body.splitlines(), STATE_LABEL))
        self.assertEqual(
            len(legal), 1,
            f"{GIT_CI_REL} section 5.2 must render exactly one LEGAL row; "
            f"legal={legal}")
        self.assertEqual(len(illegal), 3, f"illegal={illegal}")
        self.assertIn("pre-state", legal[0])
        self.assertIn("preserved set", legal[0])
        self.assertIn("post-state", legal[0])
        joined = " | ".join(illegal)
        for marker in ("without preservation", "without a post-state record",
                       "global stash prohibition"):
            with self.subTest(illegal=marker):
                self.assertIn(
                    marker, joined,
                    f"{GIT_CI_REL} section 5.2 lost the ILLEGAL row {marker!r}")

    def test_the_state_contract_parser_is_not_vacuous(self):
        """Turning an ILLEGAL row into a LEGAL one must change the parse."""
        lines = block_after_label(self.body.splitlines(), STATE_LABEL)
        legal, illegal = state_entries(lines)
        self.assertEqual((len(legal), len(illegal)), (1, 3))
        mutated = [line.replace("ILLEGAL  destructive action without preservation",
                                "LEGAL    destructive action without preservation")
                   for line in lines]
        legal2, illegal2 = state_entries(mutated)
        self.assertNotEqual(
            (len(legal2), len(illegal2)), (1, 3),
            "the state-contract parser is VACUOUS: promoting an ILLEGAL row to "
            "LEGAL did not change the parsed sets")

    def test_a_legal_destructive_transaction_is_accepted(self):
        steps = recipe_steps(self.body)
        self.assertEqual(list(steps), list(EXPECTED_STEPS))
        self.assertEqual(
            transaction_verdict(legal_record(steps), steps), LEGAL_VERDICT,
            "a destructive action with a recorded pre-state, a preserved set "
            "and a recorded post-state must be legal")

    def test_a_preservation_step_that_loses_work_is_rejected(self):
        steps = recipe_steps(self.body)
        self.assertEqual(list(steps), list(EXPECTED_STEPS))
        cases = {}
        cases["tracked modification lost"] = dict(
            legal_record(steps),
            preserved=("untracked artefact",))
        cases["untracked artefact lost"] = dict(
            legal_record(steps),
            preserved=("tracked modification",))
        cases["nothing preserved"] = dict(
            legal_record(steps), preserved=())
        for label, record in cases.items():
            with self.subTest(case=label):
                self.assertIn(
                    transaction_verdict(record, steps),
                    (REJECT_LOST_WORK, REJECT_WITHOUT_PRESERVATION),
                    f"{label}: CE-16 requires a reject")

    def test_a_destructive_action_without_a_post_state_is_invalid(self):
        steps = recipe_steps(self.body)
        self.assertEqual(list(steps), list(EXPECTED_STEPS))
        self.assertEqual(
            transaction_verdict(
                dict(legal_record(steps), postState=""), steps),
            INVALID_WITHOUT_POST_STATE)
        self.assertEqual(
            transaction_verdict(
                dict(legal_record(steps), preState=""), steps),
            INVALID_WITHOUT_PRE_STATE)

    def test_a_blanket_stash_prohibition_record_is_rejected(self):
        steps = recipe_steps(self.body)
        self.assertEqual(list(steps), list(EXPECTED_STEPS))
        self.assertEqual(
            transaction_verdict(
                dict(legal_record(steps), blanketStashBan=True), steps),
            REJECT_BLANKET_STASH_PROHIBITION,
            "a record that carries a blanket global stash prohibition must be "
            "rejected, never accepted as the legal state")

    def test_the_recipe_does_not_apply_to_non_destructive_actions(self):
        steps = recipe_steps(self.body)
        self.assertEqual(list(steps), list(EXPECTED_STEPS))
        self.assertEqual(
            transaction_verdict(
                dict(legal_record(steps), scope="read-only"), steps),
            NOT_APPLICABLE,
            "the recipe is limited to destructive actions")

    def test_an_out_of_order_transaction_is_invalid(self):
        steps = recipe_steps(self.body)
        self.assertEqual(list(steps), list(EXPECTED_STEPS))
        record = legal_record(steps)
        record["steps"] = ("status", "preserve", "operate", "post-state")
        self.assertEqual(
            transaction_verdict(record, steps), INVALID_OUT_OF_ORDER,
            "a transaction that skips the documented steps must not be accepted")

    def test_the_verdict_reads_the_documented_order(self):
        """Non-vacuity: drift of the documented order must change the verdict."""
        steps = recipe_steps(self.body)
        record = legal_record(steps)
        self.assertEqual(transaction_verdict(record, steps), LEGAL_VERDICT)
        drifted = tuple(step for step in steps if step != "preserve")
        self.assertNotEqual(drifted, steps)
        self.assertEqual(
            transaction_verdict(record, drifted), INVALID_OUT_OF_ORDER,
            "the verdict resolver is VACUOUS: dropping the documented preserve "
            "step did not change it")

    # -- single owner / single declaration point (AC-38, CE-28) ------------

    def test_the_single_declaration_point_is_section_5_2_of_the_owner(self):
        self.assertIn(RECIPE_SIGNATURE, self.body,
                      f"{GIT_CI_REL}: section 5.2 must be the recipe's "
                      f"declaration point")
        self.assertIn(RECIPE_ID, self.body,
                      f"{GIT_CI_REL}: section 5.2 must name the recipe "
                      f"identifier {RECIPE_ID}")
        self.assertIn(
            GIT_CI_REL, self.body,
            "the single declaration point must name its canonical owner "
            "(other surfaces only point or link)")
        self.assertIn(
            TICKET_LANE_REL, self.body,
            "the recipe must cite references/ticket-lane.md as the rule it "
            "follows for single declaration points")

    def test_the_recipe_is_declared_in_exactly_one_canonical_file(self):
        points = markdown_declaration_points(ROOT)
        self.assertEqual(
            points, [GIT_CI_REL],
            f"CE-28: the destructive workspace transaction must be rendered "
            f"exactly once, in {GIT_CI_REL}; found={points}")

    def test_the_recipe_identifier_appears_once_on_canonical_surfaces(self):
        hits = token_declaration_points(ROOT)
        self.assertEqual(
            hits, [GIT_CI_REL],
            f"CE-28: {RECIPE_ID} must appear on exactly one canonical surface "
            f"({GIT_CI_REL}); found={hits}")

    def test_the_dual_owner_detector_flags_a_second_copy(self):
        """Negative control: an injected second owner IS detected."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "references").mkdir(parents=True)
            owner = root / GIT_CI_REL
            owner.write_text(
                "# git ci\n\n" + RECIPE_SIGNATURE + "\n" + RECIPE_ID + "\n",
                encoding="utf-8")
            self.assertEqual(markdown_declaration_points(root), [GIT_CI_REL])
            self.assertEqual(token_declaration_points(root), [GIT_CI_REL])

            second = root / "references/competing-workspace-recipe.md"
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

    # -- the landed P1-T03 evidence must survive ---------------------------

    def test_the_landed_sections_4_5_and_5_1_are_still_present(self):
        for heading in (SECTION_4_HEADING, SECTION_5_HEADING,
                        SECTION_5_1_HEADING):
            with self.subTest(heading=heading):
                self.assertIn(
                    heading, self.text,
                    f"{GIT_CI_REL} lost the landed heading {heading!r}")
        closure = section_body(self.text, 4) + "\n" + section_body(self.text, 5)
        for marker in P1_T03_OWNED_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(
                    marker, closure,
                    f"{GIT_CI_REL} sections 4/5 lost the P1-T03-owned marker "
                    f"{marker}")
        self.assertIn("ticket-lane.md", closure)
        self.assertIn("3.1.2", closure)

    def test_the_new_subsection_does_not_restate_the_closure_evidence(self):
        for marker in P1_T03_OWNED_MARKERS:
            with self.subTest(marker=marker):
                self.assertNotIn(
                    marker, self.body,
                    f"{GIT_CI_REL} section 5.2 must not restate or alter the "
                    f"integration closure evidence owned by P1-T03; it names "
                    f"{marker}")

    def test_the_new_subsection_declares_no_field_entry(self):
        """A recipe is prose plus an ordered transaction, not a field block."""
        declared = declared_field_entries(self.body)
        self.assertEqual(
            declared, set(),
            f"{GIT_CI_REL} section 5.2 must not declare a field-list entry; "
            f"declared={sorted(declared)}")

    # -- anti-vacuity ------------------------------------------------------

    def test_every_probe_holds_for_the_live_document(self):
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                self.assertTrue(
                    probe(self.body, groups),
                    f"{GIT_CI_REL} section 5.2: probe {name} is not satisfied "
                    f"by the live document")

    def test_every_probe_flips_red_under_a_targeted_mutation(self):
        """A mutated normative sentence must turn its probe RED (not vacuous)."""
        for name, groups in PROBES.items():
            with self.subTest(probe=name):
                old, new = PROBE_MUTATIONS[name]
                self.assertTrue(
                    probe(self.body, groups),
                    f"{GIT_CI_REL}: probe {name} must hold on the live text "
                    f"before the mutation is attempted")
                self.assertIn(
                    old, self.body,
                    f"{GIT_CI_REL}: probe {name} is not anchored to document "
                    f"text; the expected marker {old!r} is absent")
                mutated = self.body.replace(old, new)
                self.assertNotEqual(mutated, self.body)
                self.assertFalse(
                    probe(mutated, groups),
                    f"{GIT_CI_REL}: probe {name} is VACUOUS - mutating "
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
