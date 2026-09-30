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
    "DEFECT_CLASS",
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


# ---------------------------------------------------------------------------
# THE SINGLE-OWNER DETECTOR
# ---------------------------------------------------------------------------
# Every pointer surface may POINT at a value domain. None may spell it out
# again. This section is the one implementation of that rule; the three
# per-domain entry points at the bottom differ only in their member list,
# their anchor phrases and the neighbouring vocabulary to exclude.
#
# WHY STRUCTURAL. Three earlier generations of this guard each failed the
# same way -- they matched a SHAPE of formatting and a reformatting defeated
# them. One matched a single literal spelling; the next required two members
# on one LINE, which a one-bullet-per-line list defeats trivially; the third
# applied the same line rule to a Markdown table. So the question here is not
# "does this look like my example" but "are two domain members separated ONLY
# by enumeration punctuation, with no prose between them" -- and that is
# answered the same way for a slash, a pipe, a comma, a bullet, a table cell
# and a fenced block.
#
# WHY IT IS STILL QUIET. The obvious cost of that question is crying wolf:
# PASS, FAIL, HIGH, MEDIUM and LOW appear in plenty of ordinary prose in this
# repo. Three things keep it silent, and each was added only after it was
# measured against all 39 markdown files rather than assumed:
#
#   1. A DECLARATION NAMES ITS AXIS. The declaration has to introduce itself
#      ("状态集", "处置取值集合", "PROMOTION_VALUE") within a short lead. A
#      sentence that merely mentions a value on the way to a full stop never
#      does. The anchors are per-domain: PROMOTION_VALUE says nothing about
#      the disposition domain, which is what keeps AGENTS.md's legitimate
#      LOW/MEDIUM/HIGH RISK table from reading as a fork of the value axis.
#   2. A NEIGHBOURING DOMAIN IS NOT A FORK. git-ci-integration.md declares
#      its own CI_STATUS set, and review-and-repair-saturation.md grades four
#      other fields HIGH/MEDIUM/LOW. A span carrying a member exclusive to one
#      of those has left this domain's vocabulary.
#   3. AN ILLUSTRATION REPEATS A MEMBER. "NOT_CONFIGURED != PASS、
#      ENV_BLOCKED != PASS、KNOWN_BASELINE_FAILURE != PASS" is the non-collapse
#      rule being demonstrated, and the repeated right-hand side is what makes
#      it a demonstration rather than a declaration. A chain that never
#      repeats -- "A != B != C != D" -- is a domain wearing a disguise, which
#      is exactly the bypass an earlier exemption allowed.
#
# The result is asserted from both sides in
# test_domain_detectors_are_quiet_on_every_pointer_document (silent on the
# pristine tree) and NegativeControlTests (loud on every injected fork).

# Enumeration punctuation, plus "!" so that "A != B" is recognised as two
# members separated by a separator rather than as two members with prose
# between them. Rule 3 above is what tells that apart from an illustration.
_ENUM_SEPARATORS = " \t\r\n|,、/\\|·•+*`~-_=()[]{}<>\"'　!"

# How far back to look for the phrase that introduces a set. Sized to sit
# inside one line of the declaration it introduces ("状态集（不可坍缩）：" is
# 9 characters) without reaching back into unrelated prose.
_MAX_LEAD = 120

# A real enumeration is dense. A long run of prose between two members means
# the document is explaining something, not declaring a domain; the cap keeps
# a table of unrelated prose from reading as one huge span.
_MAX_ENUM_SPAN = 80

# How long the description cell of an aligned value/meaning table may be. The
# canonical 21.3 rows are well under this; ordinary prose is not.
_MAX_DESC_WIDTH = 40

# Column padding before the description cell of an aligned table. Two spaces
# is enough to tell a copied declaration from a sentence that happens to
# mention a value on the way to a full stop.
_MIN_COLUMN_PAD = 2

_BULLET_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+(.*\S)\s*$")
_FENCE_RE = re.compile(r"```[a-zA-Z0-9]*\n(.*?)```", re.S)
_BARE_TOKEN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", re.M)

# The three protected domains. Each entry is the member list, the anchor
# phrases a declaration of THAT domain uses, how many distinct members make
# it a set rather than a mention, and the members that belong to a
# neighbouring domain and therefore cannot appear in a span of this one.
# Abbreviations count as members: KEEP_AS_REVIEW forks the disposition domain
# just as surely as the canonical spelling, and it is the easier typo to make.
_PROTECTED_DOMAINS: dict[str, dict] = {
    "disposition": {
        "members": PROMOTION_DISPOSITIONS + (
            "KEEP_AS_REVIEW", "KEEP_AS_HUMAN"),
        "anchors": ("处置", "disposition", "PROMOTION =", "PROMOTION="),
        "minimum": 2,
        "foreign": (),
    },
    "status": {
        "members": tuple(GOV.STATIC_GATE_STATES),
        "anchors": ("状态集", "状态值域", "状态域", "七值", "STATIC_GATE"),
        "minimum": 2,
        "foreign": ("NOT_TRIGGERED", "CANCELLED",
                    "INFRASTRUCTURE_FAILURE", "UNKNOWN"),
    },
    "promotion_value": {
        "members": ("HIGH", "MEDIUM", "LOW", "NOT_APPLICABLE"),
        "anchors": ("PROMOTION_VALUE", "晋升价值",
                    "value gate", "value-gated"),
        "minimum": 3,
        "foreign": ("NOT_CONFIGURED", "ENV_BLOCKED",
                    "EXPLICIT_AUTHORITY_OVERRIDE",
                    "KNOWN_BASELINE_FAILURE", "IMPACT",
                    "CONTRACT_CONFIDENCE", "REPAIR_COMPLEXITY",
                    "REGRESSION_RISK"),
    },
}


def _member_pattern(members: tuple[str, ...]) -> re.Pattern:
    """Longest first, so a short member cannot shadow a longer one."""
    return re.compile("|".join(
        re.escape(m) for m in sorted(members, key=len, reverse=True)))


def _is_separator_run(text: str) -> bool:
    """True when `text` is made of nothing but enumeration punctuation."""
    return not (set(text) - set(_ENUM_SEPARATORS))


def _line_containing(text: str, left, right) -> str:
    start = text.rfind("\n", 0, left.start()) + 1
    end = text.find("\n", right.end())
    return text[start:end if end != -1 else len(text)]


def _is_anchored(text: str, position: int, anchors: tuple[str, ...]) -> bool:
    """True when a phrase naming this domain introduces the declaration.

    This is the check that makes the detector usable. Without it the same
    question -- "two members, separators only" -- is true of ordinary prose
    ("... 要求全部 PASS / FAIL ...", "MEDIUM/HIGH 生产首写前需 GROUNDING"),
    and a guard that fires on those gets deleted rather than fixed.
    """
    lead = text[max(0, position - _MAX_LEAD):position]
    return any(anchor in lead for anchor in anchors)


_COMPARISON_RE = re.compile(r"^\s*!=\s*$")


def _is_comparison_chain(line: str, matches: list) -> bool:
    """True when every consecutive pair of members is joined by '!='.

    "A != B != C != D" is a chain; "X != Y、Z != Y" is not, because the
    separator between Y and Z is a comma rather than another comparison.
    """
    return all(_COMPARISON_RE.match(line[left.end():right.start()])
               for left, right in zip(matches, matches[1:]))

  
def _is_illustration(line: str, pattern: re.Pattern,
                     minimum: int) -> bool:
    """True for the non-collapse DEMONSTRATION ("X != Y、Z != Y、W != Y").

    Three conditions, each earning its place by being measured against the
    real tree rather than assumed. Note that condition 1 is only reachable
    for a domain whose `minimum` exceeds 2 -- for a two-member domain the
    earlier distinct<2 test has already returned, so a lone pair there is NOT
    waved through by this function.

    What actually keeps the non-collapse examples in AGENTS.md quiet is
    worth stating precisely, because it is not this function. That line
    carries SEVEN status values, not two, so the "too few values" reading is
    simply wrong there; it is quiet because no status anchor appears in the
    preceding 120 characters, so the pair-scan never offers a span to judge.
    This function is what keeps an ANCHORED example quiet, which is the case
    that would otherwise become a false positive -- README.md states its
    seven-value pivot demonstration under an explicit anchor.

    1. TOO FEW VALUES TO BE A SET. Below the domain's own minimum, the
       author cannot be enumerating. "PROMOTION_VALUE = HIGH != LOW" is two
       of the four values compared, which is a judgement about two things,
       not a fork of the axis.
    2. A CHAIN IS A DOMAIN. Once three or more members appear and every
       consecutive pair is joined by "!=", the author is enumerating, not
       demonstrating: a demonstration compares one pivot against several
       others and therefore needs a separator other than "!=" to come back
       for the next comparison. This is what closes the bypass the earlier
       version of this function left open -- a chain in which one member
       repeats ("A != B != A != C") was reported clean because the old rule
       only asked whether some member repeated, and a chain can be made to
       repeat one.
    3. OTHERWISE, A REPEATED MEMBER MEANS DEMONSTRATION. Three or more
       members that are NOT chained, with some value recurring, is the
       "X != Y、Z != Y" shape.
    """
    if "!=" not in line:
        return False
    matches = list(pattern.finditer(line))
    distinct = {match.group(0) for match in matches}
    if len(distinct) < 2:
        return False
    if len(distinct) < minimum:
        # Too few values to be a set at all; a pair is the illustration.
        return True
    if _is_comparison_chain(line, matches):
        return False
    counts: dict[str, int] = {}
    for match in matches:
        counts[match.group(0)] = counts.get(match.group(0), 0) + 1
    return any(count > 1 for count in counts.values())


def _restates_domain(text: str, members: tuple[str, ...],
                     minimum: int = 2,
                     anchors: tuple[str, ...] = (),
                     foreign: tuple[str, ...] = ()) -> bool:
    """True if `text` spells out the value domain `members` as a set.

    Delegation ("处置取值集合 = §21.3") names no member at all, so the scan is
    anchored on real enum members rather than on prose. Four shapes count,
    because each is a way of re-declaring a closed set:

      1. two members separated ONLY by enumeration punctuation -- "A / B",
         "A | B", "A, B", one bullet per line, a `!=` chain;
      2. two members in a TABLE shape -- a member, whitespace, then a short
         description, repeated. The canonical 21.3 declaration interleaves a
         meaning after every value, so a verbatim copy puts prose between
         members and shape 1 alone would read it as a mention;
      3. a fenced block of bare member names, one per line -- which is how
         framework 8 declares the seven-value set;
      4. a run of bullets whose entire content is members -- which has no
         introducing phrase at all, because the list IS the declaration.

    Shapes 3 and 4 exist because the first version of this detector was
    caught by both: a bare bullet list slipped through every anchored check,
    and the file that legitimately owns the status domain declared it in a
    shape none of the rules could see, so the guard never fired on the owner
    either. A guard that cannot see its own owner's declaration is a guard
    whose silence proves nothing.
    """
    pattern = _member_pattern(members)
    outside = (_member_pattern(foreign) if foreign else None)
    matches = list(pattern.finditer(text))

    for left, right in zip(matches, matches[1:]):
        if left.group(0) == right.group(0):
            continue
        if not _is_anchored(text, left.start(), anchors):
            continue
        between = text[left.end():right.start()]
        if outside is not None and outside.search(between):
            continue
        # The whole LINE has to be clean, not just the span: a neighbouring
        # domain can start inside the same declaration and run past this pair
        # (git-ci-integration.md writes one line carrying both PASS/FAIL and
        # the CI_STATUS-exclusive NOT_TRIGGERED).
        line = _line_containing(text, left, right)
        if outside is not None and outside.search(line):
            continue
        if _is_illustration(line, pattern, minimum):
            continue
        if _is_separator_run(between):
            return True
        # Shape 2: a table row, in the several forms a copied declaration
        # arrives in -- the aligned plain-text block the owner uses
        # ("NAME<pad>meaning"), a Markdown row ("| NAME | meaning |"), and
        # the definition-list form ("NAME: meaning") that a reviewer produces
        # when pasting a table into a pointer document. The colon matters:
        # without it in the separator set, "PROMOTE_NOW: 本票内下沉" reads as
        # prose and every one of those rows escapes.
        head, sep, tail = between.partition("\n")
        if not (sep and len(between) <= _MAX_ENUM_SPAN):
            continue
        if head.lstrip().startswith("|"):
            if "|" in head and "|" in tail.split("\n")[0]:
                return True
            continue
        # Definition-list / numbered-with-colon form: the description is
        # introduced by a colon, so the leading pad may be absent entirely.
        # The colon sits at the START of `head`, because it belongs to the
        # row above ("PROMOTE_NOW: meaning"), and a numbered list puts its own
        # marker in front of the next value ("2. FOLLOWUP_TOOLING_TICKET:").
        # Checking only the tail end of `head` therefore missed every one of
        # these, which is the form a reviewer produces when pasting a table
        # into prose.
        stripped = head.strip()
        if stripped.endswith((":", "：")) and len(stripped) <= _MAX_DESC_WIDTH:
            return True
        lead = stripped.lstrip("|-—•*> \t　")
        if lead[:1] in (":", "：") and len(lead) <= _MAX_DESC_WIDTH:
            return True
        pad = len(head) - len(head.lstrip(" \t　"))
        if (pad >= _MIN_COLUMN_PAD and stripped
                and len(stripped) <= _MAX_DESC_WIDTH):
            return True

    # Shape 3: a fenced block of bare member names. This is the owner's own
    # declaration form, so it has to be recognised or the guard is silent on
    # the one document that is allowed to declare the domain.
    #
    # Shapes 3 and 4 deliberately require NO anchor phrase, and that is the
    # fix for the finding that the bare-bullet shape was still only caught by
    # coincidence: the test that claimed to close it appended bullets to a
    # file whose preceding text happened to contain "PROMOTION =", so the
    # anchored pair-scan fired and the bullet path was never exercised. A
    # shape that needs no introduction has no introduction to look for, and
    # gating it on one is what made the guarantee fictional. Requiring the
    # whole bullet to be BARE is what keeps this from becoming a guess, and
    # that was measured over every markdown file in the repo: zero hits on
    # the pristine tree.
    for block in _FENCE_RE.finditer(text):
        values = {m.group(1) for m in _BARE_TOKEN_RE.finditer(block.group(1))}
        if len(values) >= minimum and len(values & set(members)) >= minimum:
            return True

    # Shape 4: a bullet run whose content is nothing but members. Each bullet
    # must be bare -- "- PROMOTE_NOW" rather than "- PROMOTE_NOW（行为知识）" --
    # so an ordinary prose bullet can never be mistaken for a declaration.
    run: list[str] = []
    for raw in text.splitlines() + [""]:
        bullet = _BULLET_RE.match(raw)
        if bullet and _is_separator_run(pattern.sub("", bullet.group(1))):
            run.append(bullet.group(1))
        else:
            if run:
                listed = "\n".join(run)
                distinct = {m.group(0) for m in pattern.finditer(listed)}
                if len(distinct) >= minimum:
                    return True
            run = []
    return False


def _restates_named_domain(text: str, name: str) -> bool:
    """Run the one detector for one of the three protected domains."""
    spec = _PROTECTED_DOMAINS[name]
    return _restates_domain(
        text, spec["members"], minimum=spec["minimum"],
        anchors=spec["anchors"], foreign=spec["foreign"])


def _restates_disposition_domain(text: str) -> bool:
    return _restates_named_domain(text, "disposition")


def _pain_numbering_gaps(body: str) -> list[int]:
    """Numbers missing from the pain ledger's section sequence.

    One implementation, deliberately shared. The guard and its negative
    control used to inline this expression twice, which is the defect this
    suite already corrected once elsewhere (a negative control that pins its
    own copy of the parsing rather than the guard it protects). Reverting
    the guard to a no-op left the control green, which is exactly what a
    control that re-derives the rule instead of exercising it will always
    do.

    The range is bounded by what the ledger actually contains, so this never
    asserts an upper bound the ledger has not reached. Its limit is equally
    real and is stated by the caller: a gap means a section was removed from
    the middle, and a truncation at the tail is invisible here because max()
    moves with the deletion. Closing that second hole needs an independent
    anchor on the ledger's high-water mark; it is NOT solved by this
    function and pretending otherwise is how the docstring came to lie.
    """
    numbers = sorted(int(label[1:]) for label in
                     set(re.findall(r"^## (P\d\d) ", body, re.M)))
    if not numbers:
        return []
    return sorted(set(range(1, max(numbers) + 1)) - set(numbers))


def _restates_status_domain(text: str) -> bool:
    """The seven-value non-collapse STATIC GATE status domain (framework 8).

    Two things make this harder than the disposition domain.

    First, AGENTS.md and README.md are allowed to show non-collapse PAIRS as
    examples -- "NOT_CONFIGURED != PASS" is the whole point of the model -- so
    a demonstration is not a restatement.

    Second, this repo has a SECOND, unrelated status domain: the CI_STATUS
    set in git-ci-integration.md, which shares PASS / FAIL /
    KNOWN_BASELINE_FAILURE with the static gate domain and is a legitimate
    declaration of its own. Shared names cannot tell the two apart, so a span
    that reaches a CI_STATUS-exclusive member is excluded.
    """
    return _restates_named_domain(text, "status")


def _restates_promotion_value_domain(text: str) -> bool:
    """PROMOTION_VALUE (HIGH / MEDIUM / LOW / NOT_APPLICABLE) as a set.

    NOT_APPLICABLE is shared with the status domain, which is why this cannot
    simply reuse that detector: a document may legitimately talk about a
    non-applicable static gate without forking the promotion axis.

    This axis also has a DECOY. review-and-repair-saturation.md has its own
    HIGH / MEDIUM / LOW grading for IMPACT, CONTRACT_CONFIDENCE,
    REPAIR_COMPLEXITY and REGRESSION_RISK, and AGENTS.md has a LOW / MEDIUM /
    HIGH RISK TABLE. Those are different axes that happen to share three
    words with this one. Getting this wrong is not hypothetical: an earlier
    version of this detector flagged AGENTS.md, and a guard that cries wolf on
    a legitimate table is a guard that gets deleted. The per-domain anchor is
    what settles it -- only a phrase naming PROMOTION_VALUE itself opens this
    domain.
    """
    return _restates_named_domain(text, "promotion_value")


_DOMAIN_DETECTORS = (
    ("disposition", _restates_disposition_domain),
    ("status", _restates_status_domain),
    ("promotion_value", _restates_promotion_value_domain),
)

# ---------------------------------------------------------------------------
# SECTION POINTER RESOLUTION
# ---------------------------------------------------------------------------
# A pointer is a delegation only if it resolves. Two earlier generations of
# this guard asserted that the STRING "21.3" appeared in the citing file,
# which a repoint to a section that does not exist satisfies just as well --
# "§3.3" changed to "§3.9" and every test passed. So the check below is not
# presence but resolution: parse the target file's real heading index and
# require the cited number to be in it.

_HEADING_RE = re.compile(r"^(#{2,4})\s+(\d+(?:\.\d+)*)\.?\s")
_SECTION_REF_RE = re.compile(r"§\s*(\d+(?:\.\d+)*)")

# A reference to a section of ANOTHER document has to say so. The audit
# files cite the upstream zhihu governance ("ZH AGENTS §18.3"), a parent Spec
# ("父 Spec §10.2") or the project-level AGENTS ("项目 AGENTS §2.1.6"), and
# those numbers resolve to nothing in this repo -- correctly so, because they
# were never meant to. Requiring the qualifier is what lets the check cover
# every file in the repo instead of only the handful this ticket touched,
# without forcing a rewrite of reviewed historical audit records.
#
# The patterns are word-bounded on purpose. An earlier version matched "ZH"
# case-insensitively and bare, so any "zh" inside any word -- "zhe", "gongzhi"
# -- counted as an external qualifier and excused whatever pointer sat nearby.
_EXTERNAL_REF_RE = re.compile(
    r"(\bZH\b|zhihu|父\s*Spec|项目\s*AGENTS|本仓以外|外部|spec\s*行)", re.I)

# The files whose pointers this ticket is responsible for. The check is
# deliberately NOT global: two historical audit files carry an unqualified
# bare "§18.1" in a bullet that inherits its qualifier from the line above,
# and editing a reviewed audit record to satisfy a new gate is scope creep,
# not correctness. That boundary is asserted rather than left implicit.
_TICKET_SCOPED_FILES = (
    FRAMEWORK_REL, TICKET_REL, REVIEW_REL, CI_REL, AGENTS_REL, README_REL,
    PAIN_REL,
)


def _heading_index() -> dict[str, dict[str, set[str]]]:
    """Map every section number to {file: {heading levels that define it}}.

    Built from the whole tree, so it is a fact about the repository rather
    than a list someone remembered to keep in sync. Section numbers are only
    unique WITHIN a document -- §8 means something different in every
    reference -- which is why resolution has to consider the whole tree while
    the level assertion has to be per file.
    """
    index: dict[str, dict[str, set[str]]] = {}
    for rel in _pointer_surfaces() + [FRAMEWORK_REL]:
        for line in read(rel).splitlines():
            match = _HEADING_RE.match(line)
            if match:
                index.setdefault(match.group(2), {}).setdefault(
                    rel, set()).add(match.group(1))
    return index


def _unqualified_pointers(rel: str, index: dict) -> list[tuple[int, str]]:
    """Every §N in `rel` that claims this repo and resolves to nothing.

    A pointer to another document has to SAY SO, and it has to say so in a
    position that actually attaches to it. The qualifier may sit on the same
    line, or on the bullet immediately above -- a list routinely establishes
    "these are all zhihu AGENTS sections" once and then continues the
    enumeration -- so the window is the line plus its predecessor.

    The window is deliberately not wider than that. An earlier version
    reached back over the whole paragraph, which meant a qualifier written for
    one pointer could excuse an unrelated dangling one on the next line:
    "以下章节号均指外部 zhihu AGENTS。" followed by "另见 §99.99" reported no
    problem, because the second pointer inherited the first one's exemption.
    A qualifier that is genuinely about a pointer is adjacent to it.
    """
    lines = read(rel).splitlines(keepends=True)
    dangling: list[tuple[int, str]] = []
    for number, line in zip(range(1, len(lines) + 1), lines):
        for match in _SECTION_REF_RE.finditer(line):
            if match.group(1) in index:
                continue
            window = _paragraph_before(lines, number)
            if _EXTERNAL_REF_RE.search(window):
                continue
            dangling.append((number, match.group(1)))
    return dangling


def _paragraph_before(lines: list[str], number: int) -> str:
    """The nearest non-blank line above `number`, plus its own line.

    One line is the right window: in this repo a qualifier for a bullet run
    is either on the same bullet or on the line just above it. Reaching
    further would let a qualifier in a previous section excuse a genuinely
    dangling pointer in the next one.
    """
    window = lines[number - 1]
    for index in range(number - 2, max(-1, number - 4), -1):
        if lines[index].strip():
            window += lines[index]
            break
    return window


def _pointer_surfaces() -> list[str]:
    """Every markdown file in the repo that is not the canonical owner.

    This list is DERIVED, not written down. The previous version of these
    guards named six files by hand, and that is exactly how a fork escaped:
    a reviewer appended the enumeration to references/review-evidence.md or
    references/static-tooling-profiles.md -- neither of which was in the tuple
    -- and every test stayed green. Thirty-three other markdown files were
    equally unguarded.

    A hand-maintained list is a list that rots. Any file added to the repo is
    a surface by default, so "which files are guarded" is a question about the
    tree rather than about someone's memory.
    """
    return sorted(
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*.md")
        if path.relative_to(ROOT).as_posix() != FRAMEWORK_REL
    )

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
        """All SEVEN in-ticket conditions, and the list is not a hand-copy.

        This test asserted five of the seven conditions. The two it skipped
        are "变更微小且局部" and "无无关文件", and the second is the one that
        closes scope creep -- deleting it would let a repair touch unrelated
        files and still call it PROMOTE_NOW, with the suite green. A partial
        list of a conjunction is the failure mode where each individual
        assertion is true and the guarantee is absent.

        The conjunction is located in the framework, and each condition is
        asserted to be a LINE OF THAT BLOCK rather than a phrase somewhere in
        the document. Document-wide membership is not enough: a condition can
        be swapped out of the conjunction while its old wording survives as
        an unrelated prose mention, and the guarantee silently evaporates.
        The block is also required to keep its leading "+" chain, since a
        bullet list is where "any one of these is fine" creeps back in.

        What is and is not derived: the block's location, its shape and its
        size come from the framework, but the seven identities are still
        named here. That is a deliberate limit rather than an oversight --
        deriving the identities would make the test agree with whatever the
        framework says, which is not what a guard is for. The check that
        matters is the second one: a named condition has to be a line of the
        conjunction, so the framework cannot quietly replace it.
        """
        body = read(FRAMEWORK_REL)
        conditions = self._conjunction_conditions(body)
        for condition in ("现有工具已存在", "变更微小且局部", "无新依赖",
                          "无广泛基线 churn", "无架构变更", "无无关文件",
                          "与本票修复属同一缺陷类"):
            with self.subTest(condition=condition):
                self.assertIn(
                    condition, conditions,
                    "a condition of the PROMOTE_NOW conjunction is missing "
                    "from the conjunction itself")
        self.assertEqual(len(conditions), 7,
                         "the conjunction must have exactly the seven "
                         "conditions §21.3 declares")

    def _conjunction_conditions(self, body: str) -> set[str]:
        """The conditions of the in-ticket conjunction, as the block declares.

        The real test goes through this too, so a control built on it cannot
        drift away from the thing it is controlling. An earlier version of
        this control re-parsed the block inline, which meant it kept
        detecting the swap even after the real test had been weakened back
        to a document-wide search -- it was pinning its own copy instead of
        the guard.
        """
        block = re.search(r"现有工具已存在\n(?:\+ .*\n)+", body)
        if block is None:
            self.fail("the in-ticket conditions are not a + conjunction")
        return {line.lstrip("+ ").strip()
                for line in block.group(0).strip().split("\n")}

    def test_swapping_a_condition_out_of_the_conjunction_is_detected(self):
        """NEGATIVE CONTROL for the block-scoped condition check.

        The check above is only stronger than a document-wide assertIn
        because the conditions are matched INSIDE the conjunction block. That
        difference was established by hand -- replace "+ 无无关文件" with
        "+ 无临时文件" and park the old wording in unrelated prose -- and a
        fact established by hand is not a property of the suite. Reverting
        the block scoping to a plain document search would leave every test
        green, which is the silent weakening this file exists to rule out.

        The mutated document is run through the same helper the real test
        uses, so restoring document-wide search makes this control red.
        """
        pristine = read(FRAMEWORK_REL)
        self.assertIn("无无关文件", self._conjunction_conditions(pristine))

        # Swap one condition for a plausible-sounding impostor and keep the
        # original wording alive elsewhere in the document, which is exactly
        # how a quiet substitution would survive a document-wide search.
        mutated = pristine.replace("+ 无无关文件", "+ 无临时文件", 1)
        mutated = mutated.replace(
            "## 21. DEFECT_TO_GATE_PROMOTION",
            "无无关文件 是本节讨论的一个相关概念。\n\n"
            "## 21. DEFECT_TO_GATE_PROMOTION", 1)
        self.assertIn("+ 无临时文件", mutated,
                      "the mutation must actually apply, or this control "
                      "proves nothing")
        self.assertIn("无无关文件", mutated,
                      "the old wording must survive elsewhere, or this is "
                      "just a deletion test")
        self.assertNotIn("无无关文件", self._conjunction_conditions(mutated),
                         "a swapped condition must not still satisfy the "
                         "conjunction")

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

    def test_no_pointer_document_restates_any_protected_domain(self):
        """Single-owner discipline applies to EVERY surface, not one block.

        The earlier guards each looked at a single pre-split block of a single
        file, and then each named its own hand-written file list. Reviewers
        found the resulting holes three separate ways: by appending an
        enumeration to AGENTS.md, by forking the PROMOTION_VALUE axis in
        README.md, and -- once the file list was widened to the six obvious
        documents -- by forking it in references/review-evidence.md, which no
        list had mentioned.

        So there is now ONE loop over every markdown file in the repo except
        the owner, covering all three protected domains. The owner itself is
        excluded on purpose: framework 21 is where the values are DEFINED, and
        the detector would of course fire there.
        """
        for rel in _pointer_surfaces():
            body = read(rel)
            for name, detector in _DOMAIN_DETECTORS:
                with self.subTest(rel=rel, domain=name):
                    self.assertFalse(
                        detector(body),
                        f"{rel} must point at the owner, not restate "
                        f"the {name} domain")

    def test_the_domain_surfaces_are_derived_from_the_tree(self):
        """Guard the guard: the surface list must not shrink back to a tuple.

        The fix above is only durable if a later edit cannot quietly restore a
        short list. This asserts the property the fix is actually for -- that
        files nobody thought to name are covered -- by checking that files
        which exist in the repo and were never in any hand-written tuple are
        among the surfaces.
        """
        surfaces = _pointer_surfaces()
        for rel in ("references/review-evidence.md",
                    "references/static-tooling-profiles.md",
                    "skills/README.md", "mcp/README.md",
                    "adapters/workbuddy/README.md", "audit/GAP_MATRIX.md"):
            with self.subTest(rel=rel):
                self.assertIn(rel, surfaces)
        # The owner is a declaration surface, never a guarded pointer.
        self.assertNotIn(FRAMEWORK_REL, surfaces)
        # Every domain has a detector, so a fourth domain cannot be added
        # without also being given one.
        self.assertEqual(
            {"disposition", "status", "promotion_value"},
            {name for name, _ in _DOMAIN_DETECTORS})

    def test_domain_detectors_are_quiet_on_every_pointer_document(self):
        """The detectors must be silent on the real tree, or nobody keeps them.

        This is the other half of a usable guard, and it is asserted over the
        same derived surface list as the loud half. A detector that fires on
        the pristine documents trains everyone to ignore it, and an ignored
        guard protects nothing -- which is exactly how the first version of
        this suite ended up pinning a violation in place.

        Both directions matter. Quet on all 38 pointer files is a precision
        claim; the owner tripping all three detectors is a sensitivity claim,
        and it is the half that is easy to forget: a detector that cannot see
        its own owner's declaration would report success for the wrong reason.
        """
        surfaces = _pointer_surfaces()
        for rel in surfaces:
            body = read(rel)
            for name, detector in _DOMAIN_DETECTORS:
                with self.subTest(rel=rel, domain=name):
                    self.assertFalse(
                        detector(body), f"{rel} must not declare {name}")
        owner = read(FRAMEWORK_REL)
        for name, detector in _DOMAIN_DETECTORS:
            with self.subTest(domain=name, owner=True):
                self.assertTrue(
                    detector(owner),
                    f"the owner must declare {name}; a detector blind to "
                    f"its own declaration proves nothing")

    def test_every_section_pointer_resolves_to_a_real_heading(self):
        """A pointer to a section that does not exist is a broken contract.

        Both reviewers demoted or renamed section 21.3 as a probe and no test
        failed: the guards checked that the text "21.3" was mentioned, never
        that a heading with that number still exists.

        This resolves every pointer in the files this ticket owns against the
        tree's real heading index, so a repoint into the void fails. The
        earlier version of the same idea only listed the numbers it expected,
        which is why it had to be replaced rather than merely extended.
        """
        index = _heading_index()
        for rel in _TICKET_SCOPED_FILES:
            dangling = _unqualified_pointers(rel, index)
            with self.subTest(rel=rel):
                self.assertEqual(
                    [], dangling,
                    f"{rel} points at sections that exist nowhere in this "
                    f"repo: {dangling}")

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
        index = _heading_index()
        self.assertIn("21.3", index, "framework 21.3 must exist")
        self.assertEqual({"###"}, index["21.3"][FRAMEWORK_REL],
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
                        number, index,
                        f"{rel} owns section {number} but no heading matches")
                    self.assertIn(
                        rel, index[number],
                        f"section {number} exists, but not in {rel}")

    def test_subsection_cannot_be_demoted_out_from_under_its_section(self):
        """A level demotion is as broken as a missing heading.

        This is the same class of defect as a dangling pointer, and it was
        found by the same reviewer: "### 21.3" was demoted to "## 21.3",
        which keeps the NUMBER resolvable while silently moving the section
        out from under the parent that owns it. A presence check cannot see
        that, and neither can a substring check -- "### 21.3 " is a substring
        of "#### 21.3 " -- so the level has to be compared against the
        parent's, per file.

        The rule is arithmetic: N.M is a subsection of N exactly when its
        heading is one level deeper.

        SCOPE, stated rather than hidden: this covers the sections this ticket
        owns, not every numbered heading in the repo. A global version of the
        rule reports 101 pre-existing violations -- README.md numbers §1.1
        under a "## 1." heading that also appears as "## 1" elsewhere, the
        audit files flatten tiers freely, and AGENTS.md has a "## 7.1" that
        is a peer of "## 7" by design. Turning those into failures would mean
        rewriting reviewed history to satisfy a gate that did not exist when
        the history was written, which is scope creep rather than correctness.
        The sections this ticket introduced are held to the rule, and the
        exceptions that remain inside them are listed rather than tolerated
        silently.
        """
        owned: dict[str, set[str]] = {
            FRAMEWORK_REL: {"21.1", "21.2", "21.3", "10.1", "15.1"},
            TICKET_REL: {"9.3", "9.4"},
            REVIEW_REL: {"4.1", "6.5"},
            CI_REL: {"3.3", "3.4"},
        }
        index = _heading_index()
        violations: list[str] = []
        for rel, numbers in owned.items():
            for number in numbers:
                levels = index.get(number, {}).get(rel)
                with self.subTest(rel=rel, number=number):
                    self.assertIsNotNone(
                        levels, f"{rel} lost section {number} entirely")
                    parent = number.rsplit(".", 1)[0]
                    parent_levels = index.get(parent, {}).get(rel)
                    self.assertIsNotNone(
                        parent_levels,
                        f"{rel} §{number} has no §{parent} to sit under")
                    self.assertEqual(
                        {len(min(parent_levels)) + 1},
                        {len(level) for level in levels},
                        f"{rel} §{number} must be one heading level deeper "
                        f"than §{parent}; demoting it moves it out from "
                        f"under the section that owns it")
        self.assertEqual([], violations)

    def test_a_pointer_that_resolves_to_nothing_is_detected(self):
        """Negative control: repointing a delegation must fail a guard.

        The two tests above are the strongest form of this claim -- they check
        every pointer in the tree, not a hand-written list -- but they would
        still pass vacuously if the resolution helper silently returned an
        empty list. So the helper is fed a real repointing mutation and has to
        report it.
        """
        index = _heading_index()
        # The pristine citation resolves; the mutated one does not.
        self.assertIn("21.3", index)
        self.assertNotIn("21.9", index)
        mutated = read(AGENTS_REL).replace("§21.3", "§21.9")
        with tempfile.TemporaryDirectory() as tmp:
            polluted = Path(tmp) / "repo"
            shutil.copytree(ROOT, polluted,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            target = polluted / AGENTS_REL
            target.write_text(mutated, encoding="utf-8")
            original_read = read

            def read_from_copy(rel: str, _polluted=polluted) -> str:
                return (_polluted / rel).read_text(encoding="utf-8")

            try:
                globals()["read"] = read_from_copy
                dangling = _unqualified_pointers(AGENTS_REL, index)
            finally:
                globals()["read"] = original_read
        self.assertTrue(
            any(number == "21.9" for _, number in dangling),
            f"a repointed delegation must be reported: {dangling}")

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

    def test_pain_row_claims_only_enforcement_that_actually_exists(self):
        """A capability claim must be backed by a check that really runs.

        This is the honesty guard for the ledger. The P21 row used to say the
        receipt-field existence and the value-domain delegation were both
        checked by "validate_governance.py + test_p1_t18_*.py". The first is
        not: the validator's static_gate_wiring counts delegation markers and
        bans one token, and the FIELD names are checked by the test file
        alone. A ledger that overstates what is mechanically enforced is worse
        than one that admits a limit, because it is read as evidence when it is
        actually an assertion.

        So each capability the row claims is named against the script that
        actually implements it, and the test below re-derives that mapping from
        the source rather than trusting the sentence.
        """
        body = read(PAIN_REL)
        # The P21 section ends where the next one begins, NOT at the roll-up
        # heading. Ending it at the roll-up meant every pain record added
        # after P21 was silently counted as part of P21, so a second
        # enforcement claim anywhere below P21 would have failed this guard
        # for the wrong reason -- and the only way out was to give P22 a
        # private field name, which is a second copy of the same concept
        # under another spelling. Slicing at the section boundary is what
        # makes the count mean what it says.
        after_p21 = body.split("## P21 ", 1)[1]
        row = re.split(r"^## P\d\d ", after_p21, maxsplit=1,
                       flags=re.M)[0].split("## 汇总判定表", 1)[0]
        claims = [line for line in row.splitlines()
                  if "CAN_BE_MACHINE_ENFORCED" in line]
        self.assertEqual(1, len(claims),
                         "P21 must state its enforcement level exactly once")
        claim = claims[0]
        # The delegation check is real and is the validator's job.
        self.assertIn("static_gate_wiring", claim)
        # The value-domain single-owner check is real and is the test's job.
        self.assertIn("test_p1_t18", claim)
        # And the row must say plainly that the judgement calls are NOT
        # machine-enforced, so the ledger cannot be read as claiming the whole
        # mechanism is mechanised.
        self.assertIn("不由机器判定", claim)
        # The claim must not attribute field-existence checking to the
        # validator, which does not do it.
        self.assertNotIn(
            "validate_governance.py` + `scripts/tests",
            claim,
            "field existence is checked by the test file, not the validator")
        # And the capability it names must actually exist in that script.
        self.assertTrue(hasattr(GOV, "static_gate_wiring"))

    def test_every_pain_row_survives_in_the_roll_up_table(self):
        """Every documented pain point needs a row in the summary table.

        The roll-up table is how a reader sees the whole ledger at once, so a
        pain point documented in full but missing from the table is invisible
        to exactly the audience the table exists for. The P19 row was missing
        for precisely this reason.

        The check is on the TABLE, not on the headings: a section can be
        deleted outright and the heading count would still look plausible --
        which is why the derived set below is anchored against the numbering
        rather than trusted on its own.

        The set of required rows is DERIVED from the sections that exist
        rather than hardcoded. The previous version looped over a literal
        range and then asserted that the next label was absent -- which
        looked like a completeness check but was actually a freeze-frame: the
        moment P22 was documented, the guard silently stopped requiring a row
        for it AND forbade one, so adding the correct row would have failed
        the suite. That inverts the rule it claims to enforce, and it is the
        same shape of defect this ticket exists to correct elsewhere: a
        finding that is true, and a guard that is satisfied, while the thing
        both are supposed to protect goes unrecorded.

        Deriving the set is also what makes the intent honest. The table's
        purpose is to be complete, so a new section must be rolled up; the
        only thing worth forbidding is a row with no section behind it.

        Deriving is necessary but NOT sufficient, and the gap between those
        two words was a real coverage regression here. A purely derived set
        is closed under deletion: drop a whole section and its roll-up row
        together and both directions still balance. Deleting P12 that way
        was shown by ablation to leave the suite green, while this docstring
        still claimed the opposite. So the derived set is anchored against a
        SECOND derived fact -- the section numbering is contiguous.

        WHAT THIS ANCHOR DOES NOT COVER, stated plainly because the previous
        version of this docstring got it wrong in the other direction. The
        range is bounded by max(), so it sees a section removed from the
        MIDDLE and stays silent in two cases:

          - tail truncation: delete the LAST section and its row, max()
            moves down with the deletion and the remaining prefix is still
            contiguous;
          - consistent renumbering: delete a middle section and close the
            gap by renumbering everything after it.

        Both are the same limit rather than two bugs: no check that reads
        only the current document can distinguish "this section was never
        written" from "this section was removed along with every trace of
        it". Closing that needs an anchor OUTSIDE the document -- git history
        or an owner-bumped constant -- and this ticket rules both out (a
        bumped constant is the freeze-frame this guard was written to
        remove, and CI checks out at depth 1 so there is no history to read).

        THIS PARAGRAPH IS ITSELF UNGUARDED, and saying so is the point. An
        earlier version claimed the boundary was "pinned by
        test_deleting_a_pain_section_is_detectable ... so it cannot rot back
        into an overstated claim". Deleting this whole paragraph left the
        suite at 551 OK, because no test asserts that a docstring states its
        own limits -- and building one is the guard-of-guard this ticket
        forbids. So the honesty here rests on review, not on a gate, exactly
        as this module's header says marker presence is not semantic
        validation. Treat any future widening of these claims as a finding
        against this docstring, not as something the suite would catch.
        """
        body = read(PAIN_REL)
        table = body.split("## 汇总判定表", 1)[1]
        documented = set(re.findall(r"^## (P\d\d) ", body, re.M))
        self.assertTrue(documented, "no pain sections found at all")
        for label in sorted(documented):
            with self.subTest(pain=label):
                self.assertIn(
                    f"| {label} ", table,
                    f"{label} must have a row in the roll-up table")
        # The inverse direction is what the freeze-frame version got wrong:
        # a row with no section behind it is the thing worth rejecting.
        rolled_up = set(re.findall(r"^\| (P\d\d) ", table, re.M))
        for label in sorted(rolled_up - documented):
            with self.subTest(orphan=label):
                self.fail(
                    f"the roll-up table claims {label} but no such section is "
                    "documented")
        # The anchor, for gaps in the middle. See the docstring for the two
        # cases it deliberately does not cover.
        gaps = _pain_numbering_gaps(body)
        self.assertEqual(
            [], gaps,
            "pain section numbering must be contiguous from P01; a gap means "
            f"a whole section was deleted from the middle (missing: {gaps}). "
            "Removing a section together with its roll-up row leaves the "
            "derived set balanced, so the correspondence checks above cannot "
            "see it on their own.")

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

        Both mutations below assert on guards that CAN fail. The obvious
        version of this test -- rewrite the parent heading, then assert that
        some OTHER guard also noticed -- is a false requirement: no guard in
        this module is keyed on the section title, because the subsections are
        what make 21 a real section. Asserting that one must exist would have
        added a guard that fires on nothing. So the section title is checked
        against the heading guard that does exist, and the subsections are
        checked against their own guards, which do.
        """
        fired = self._guards_that_fail_on(
            FRAMEWORK_REL, "## 21. DEFECT_TO_GATE_PROMOTION（缺陷类下沉到机器门）",
            "## 21. 机械门下沉")
        self.assertIn("framework:declares-21", fired)
        # A rename that leaves the numbering alone cannot be caught by the
        # heading guard, so the subsections are the load-bearing part. Removing
        # one is a separate mutation, and each subsection guard is real.
        for old, guard in (
                ("### 21.1 晋升判定（value-gated，不是自动规则扩散）",
                 "framework:21-1-still-present"),
                ("### 21.2 LOWEST RELIABLE MECHANICAL LAYER（概念层级）",
                 "framework:21-2-still-present"),
                ("### 21.3 处置（disposition）",
                 "framework:21-3-is-a-subsection")):
            with self.subTest(subsection=old.split()[1]):
                self.assertIn(guard, self._guards_that_fail_on(FRAMEWORK_REL, old, "## 21. 已移除"))


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

        Three earlier generations of this guard failed the same way: each
        matched a SHAPE of formatting, and each shape turned out to be
        reformattable. One matched a single literal spelling; the next
        required two members on one LINE, which a one-bullet-per-line list
        defeats trivially; the third applied that line rule to a Markdown
        table. The detector is now structural, so the shapes below are the
        ones a reviewer actually tried, and the last three are the ones that
        used to be documented gaps rather than covered cases.
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
                "FOLLOWUP_TOOLING_TICKET 需新工具票\n```\n",
                # A bare bullet list: no introducing phrase at all, because
                # the list IS the declaration. This one was previously
                # recorded as a KNOWN LIMIT and had to be caught by review.
                # The third independent reviewer rejected that
                # justification, and this is the shape that closed it.
                "\n- PROMOTE_NOW\n- KEEP_AS_HUMAN_DECISION\n",
                # Ordered-list form of the same thing.
                "\n1. PROMOTE_NOW\n2. FOLLOWUP_TOOLING_TICKET\n",
                # A != chain, which the earlier exemption waved through: it
                # skipped any window containing "!=", so four members of the
                # disposition domain hidden behind a row of != signs were
                # reported as clean.
                "\n处置取值集合 = PROMOTE_NOW != FOLLOWUP_TOOLING_TICKET != "
                "KEEP_AS_TEST != KEEP_AS_HUMAN_DECISION\n",
                # The Markdown table form: "| NAME | meaning |" per row, which
                # is how a reviewer pastes a table into a pointer document.
                "\n| 值 | 含义 |\n|---|---|\n"
                "| PROMOTE_NOW | 本票内下沉 |\n| KEEP_AS_TEST | 行为知识 |\n",
                # Definition-list form: the description is introduced by a
                # colon with no leading column pad at all, so the aligned-pad
                # rule never fires and the row reads as prose.
                "\nPROMOTE_NOW: 本票内下沉\nFOLLOWUP_TOOLING_TICKET: 工具缺口\n"
                "KEEP_AS_HUMAN_DECISION: 保留人工\n",
                # The same form with an ordered list, where the number sits
                # between the member and its colon.
                "\n1. PROMOTE_NOW: 本票内下沉\n2. FOLLOWUP_TOOLING_TICKET: 工具缺口\n"
                "3. KEEP_AS_HUMAN_DECISION: 保留人工\n"):
            with self.subTest(appended=appended.strip()[:40]):
                self.assertTrue(
                    _restates_disposition_domain(base + appended),
                    "an appended enumeration is a restatement")
        # The pristine document must not trip the detector, or the guard
        # would be protecting nothing.
        self.assertFalse(_restates_disposition_domain(base))
        # Closing the bare-bullet gap did NOT cost precision: an ordinary
        # two-item prose bullet is still not a declaration, because its
        # content is not made only of members. Without this the widened
        # bullet rule would be indistinguishable from guessing.
        self.assertFalse(_restates_disposition_domain(
            base + "\n- PROMOTE_NOW 仅在本票内所有条件同时满足时成立\n"
            "- KEEP_AS_HUMAN_DECISION 需要产品裁决\n"),
            "a prose bullet mentioning two values is not a declaration")

    def test_a_comparison_chain_is_a_domain_but_a_pivot_demo_is_not(self):
        """The "!=" rule turns on chain-vs-repeated-pivot, not on "!=" itself.

        Treating "!=" as one more separator let four members of the status
        domain hide behind a row of comparison signs. The fix is not "reject
        !=" but a distinction the non-collapse rule actually turns on: a
        demonstration compares ONE pivot against several others, so it has to
        come back to the pivot with a different separator, and it therefore
        repeats a member. An enumeration needs no such return trip.

        Both halves are asserted, because each one alone is a rule that could
        be satisfied by the other: if every chain were called a demo, the
        first assertion would pass and the guard would be dead; if every
        repeat were called a chain, the second would.
        """
        for label, text in (
                # Distinct members, every pair joined by "!=" -> enumeration.
                ("4-distinct chain",
                 "状态值域 = NOT_CONFIGURED != PASS != FAIL != BLOCKED"),
                ("3-distinct chain",
                 "状态值域 = NOT_CONFIGURED != PASS != FAIL"),
                # A chain CAN be made to repeat a member, and that was the
                # exact bypass: it satisfies the old "some member repeats"
                # rule while being just as much an enumeration.
                ("repeating chain",
                 "状态值域 = NOT_CONFIGURED != PASS != NOT_CONFIGURED != FAIL")):
            with self.subTest(shape=label):
                self.assertTrue(
                    _restates_status_domain(text),
                    "a != chain is a declaration, not a demonstration")
        # The demonstration: one pivot, several comparators, returning to the
        # pivot with "、" rather than another "!=". This is what the
        # non-collapse rule exists to permit, so it must stay permitted.
        #
        # It carries an explicit anchor on purpose. Without one the pair-scan
        # skips the span before _is_illustration is ever consulted, so the
        # assertion would be passing for the wrong reason -- which is the
        # difference between a test that pins this rule and one that merely
        # agrees with it.
        demo = ("状态值域演示：NOT_CONFIGURED != PASS、FAIL != NOT_CONFIGURED、"
                "BLOCKED != NOT_CONFIGURED")
        self.assertTrue(
            _is_anchored(demo, demo.index("NOT_CONFIGURED"),
                         _PROTECTED_DOMAINS["status"]["anchors"]),
            "the demonstration fixture must be anchored, or this assertion "
            "is satisfied by the pair-scan short-circuit instead")
        self.assertTrue(
            _is_illustration(
                demo, _member_pattern(_PROTECTED_DOMAINS["status"]["members"]),
                _PROTECTED_DOMAINS["status"]["minimum"]),
            "a repeated-pivot comparison is the non-collapse model, not a set")
        self.assertFalse(_restates_status_domain(demo),
                         "an anchored pivot demo must not read as a restatement")
        # The single comparison that states the whole rule, on its own.
        self.assertFalse(_restates_status_domain("NOT_CONFIGURED != PASS"),
                         "one comparison is the model, never a value set")

    def test_a_pair_below_the_domain_minimum_is_not_a_declaration(self):
        """PROMOTION_VALUE needs three values before it is being forked.

        HIGH/MEDIUM/LOW/NOT_APPLICABLE is a four-value axis, so naming two of
        them side by side cannot enumerate it. The disposition and status
        domains have a minimum of two, which is why this rule is stated per
        domain rather than as "a pair is never a set" -- the earlier wording
        of that claim was true for one domain and false for the other two,
        and the docstring now says so.
        """
        self.assertEqual(_PROTECTED_DOMAINS["promotion_value"]["minimum"], 3)
        self.assertFalse(_restates_promotion_value_domain(
            "PROMOTION_VALUE = HIGH != LOW"),
            "two of four values compared is a judgement, not a fork of the axis")
        for text in ("PROMOTION_VALUE = HIGH / MEDIUM / LOW",
                     "PROMOTION_VALUE = HIGH, LOW, NOT_APPLICABLE"):
            with self.subTest(text=text[:30]):
                self.assertTrue(_restates_promotion_value_domain(text),
                                "three of four values IS the axis")

    def test_an_external_excuse_needs_a_whole_word(self):
        """"ZH" is an external-reference marker; "zhe" is a Chinese word.

        The qualifier exists so that a pointer into an EXTERNAL document is
        not reported as a dangling one. Written as a bare substring it also
        matched any word containing those two letters -- "zhe", "gongzhi" --
        so an unrelated line of prose silently excused a pointer that goes
        nowhere. Nothing on the pristine tree distinguishes the two versions,
        which is exactly why this needs its own assertion rather than being
        left to a future reviewer to notice.
        """
        for label, text, excused in (
                ("the marker itself", "见 ZH AGENTS §18.3", True),
                ("a word containing zh", "见治理 zhe 文档 §99.9", False),
                ("another word containing zh", "见 gongzhi 规则 §99.9", False),
                ("no excuse at all", "见 §99.9", False)):
            with self.subTest(text=text):
                self.assertEqual(bool(_EXTERNAL_REF_RE.search(text)), excused,
                                 f"{label} must {'not' if excused else ''} "
                                 "count as an external-reference excuse")

    def test_a_bare_bullet_run_is_caught_with_no_introducing_phrase(self):
        """Shape 4 must be load-bearing, not incidentally covered.

        The mutation table above appends its bare bullets to TICKET_REL,
        whose 9.4 tail carries "PROMOTION =", so the ANCHORED pair-scan
        fires first and shape 4 never runs. That is the same coincidence the
        third review rejected, and repeating it in the fix for it would make
        the round-4 headline claim untestable: reverting shape 4 back to
        requiring an anchor leaves the whole suite green.

        So this case is anchored nowhere on purpose. The filler prose is
        there to push every anchor outside _MAX_LEAD, and the assertion is
        also made directly on the bare string, so neither a wider lead window
        nor a longer document can quietly restore the coincidence.
        """
        bullets = "\n- PROMOTE_NOW\n- KEEP_AS_HUMAN_DECISION\n"
        anchorless = "本节讨论评审流程，与取值无关。\n" * 20 + bullets
        # No introducing phrase anywhere in range: the bullets are the
        # declaration, and that is the shape this rule exists to catch.
        self.assertFalse(
            _is_anchored(anchorless, anchorless.index("PROMOTE_NOW"),
                         _PROTECTED_DOMAINS["disposition"]["anchors"]),
            "the fixture must not accidentally supply an anchor, or this "
            "test proves nothing about the anchor-free path")
        self.assertTrue(
            _restates_disposition_domain(anchorless),
            "a bare bullet run with no introducing phrase is a declaration")
        self.assertTrue(
            _restates_disposition_domain(bullets.strip()),
            "the shape must be recognised even with no surrounding document")
        # And the widened rule still has not become a guess: a bullet that
        # carries prose is a mention, whatever is or is not above it.
        self.assertFalse(_restates_disposition_domain(
            "本节讨论评审流程，与取值无关。\n" * 20
            + "\n- PROMOTE_NOW 仅在本票内所有条件同时满足时成立\n"
            "- KEEP_AS_HUMAN_DECISION 需要产品裁决\n"),
            "a prose bullet mentioning two values is not a declaration")

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

    def test_a_fork_in_a_file_no_test_used_to_name_is_detectable(self):
        """The surface list is derived, so a fork anywhere in the repo is caught.

        The single-owner guards named six files by hand. A reviewer appended
        the enumeration to references/review-evidence.md -- a file no list
        mentioned -- and every test stayed green. Thirty-three other markdown
        files were equally unguarded, and the way to find out which ones
        mattered was to enumerate them.

        This walks that list and forks each file in turn, so the claim is
        checked against the whole tree rather than against three convenient
        examples. It is the negative control for
        _pointer_surfaces: if the derived list ever stops covering the repo,
        this test is what notices.
        """
        forks = {
            "disposition": (
                "\n处置取值集合 = PROMOTE_NOW | KEEP_AS_TEST\n",
                _restates_disposition_domain),
            "status": (
                "\n状态集：PASS / FAIL / NOT_CONFIGURED / NOT_APPLICABLE\n",
                _restates_status_domain),
            "promotion_value": (
                "\nPROMOTION_VALUE = HIGH / MEDIUM / LOW / NOT_APPLICABLE\n",
                _restates_promotion_value_domain),
        }
        surfaces = _pointer_surfaces()
        # Forking all 38 files x 3 domains on every run would be slow for no
        # extra information, so a deterministic spread is used: the files a
        # hand-written list would most plausibly have included, plus the ones
        # it would most plausibly have missed.
        sample = [rel for rel in surfaces if rel in (
            AGENTS_REL, README_REL, TICKET_REL, REVIEW_REL, CI_REL, PAIN_REL,
            "references/review-evidence.md",
            "references/static-tooling-profiles.md",
            "skills/README.md", "mcp/README.md",
            "adapters/workbuddy/README.md", "audit/GAP_MATRIX.md")]
        self.assertEqual(12, len(sample),
                         "the sample must cover both the named and the "
                         "previously-unguarded files")
        for rel in sample:
            body = read(rel)
            for domain, (appended, detector) in forks.items():
                with self.subTest(rel=rel, domain=domain):
                    self.assertFalse(
                        detector(body),
                        f"{rel} must be clean before the fork is injected")
                    self.assertTrue(
                        detector(body + appended),
                        f"a {domain} fork appended to {rel} must be caught; "
                        f"this file is not on any guarded surface list")

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

    def test_deleting_a_pain_section_is_detectable(self):
        """The roll-up guard must fail when a section AND its row vanish.

        This is the negative control for the contiguity anchor, and it exists
        because the anchor was missing. The derived-set version of this guard
        was satisfied by a ledger with P12's section and P12's roll-up row
        both deleted: nothing about a self-derived set can notice its own
        removal, so both correspondence directions still balanced. An
        independent reviewer proved it by ablation and the docstring still
        claimed the opposite.

        The mutation keeps the deletion honest, which is the whole difficulty:
        it removes the section body, the heading, and the roll-up row
        together, so the derived set stays balanced and only the numbering
        anchor can see it. The middle section is the victim for the reason
        given in the guard's docstring -- the tail is deliberately outside
        this anchor's coverage, and pretending otherwise is what produced the
        overstated claim in the first place.

        WHAT MAKES THIS A CONTROL RATHER THAN A RESTATEMENT: it calls
        _pain_numbering_gaps, the same function the guard calls. The first
        version of this test inlined the comparison a second time, which
        left it green even when the anchor was reverted to a no-op -- the
        same "pins its own copy" defect this suite already had to correct
        once.

        AND WHAT IT STILL DOES NOT PROTECT, measured rather than assumed.
        Sharing the function makes NEUTERING THE FUNCTION turn this control
        red. It does NOT make these two changes turn it red, both verified
        by ablation on a scratch copy:

          - the guard stops calling the helper (gaps hardcoded to []);
          - the guard asserts against a literal instead of calling it.

        In both cases this control stays green, because it exercises the
        helper rather than the guard's use of it. An earlier version of this
        docstring claimed sharing makes "reverting the guard turn this
        control red too"; that was false and was corrected here rather than
        papered over with another guard. Deciding what the guard asserts is
        exactly the kind of guard-of-guard this ticket rules out, so the
        limit is stated instead of mechanised.
        """
        original = read(PAIN_REL)

        # -- the mutation, applied to a real copy ----------------------------
        # This assertion is NOT redundant with the guard's, and an earlier
        # version of this file removed it on exactly that claim. The two read
        # the same document but they are not the same check: this one reads
        # the REAL tree (`original`), while every assertion below runs against
        # a mutated COPY inside a temp directory. Deleting a section from the
        # real ledger is the dangerous case, and it is the one this assertion
        # is the only thing covering -- measured, not assumed: with it
        # removed, ablating P12 on this SHA takes the suite from
        # FAILED (failures=2) to FAILED (failures=1), the surviving failure
        # being the guard alone.
        self.assertEqual(
            [], _pain_numbering_gaps(original),
            "pristine pain numbering must be contiguous on the real tree")
        numbers = sorted(int(label[1:]) for label in
                         re.findall(r"^## (P\d\d) ", original, re.M))
        victim = f"P{numbers[len(numbers) // 2]:02d}"
        with tempfile.TemporaryDirectory() as tmp:
            polluted = Path(tmp) / "repo"
            shutil.copytree(ROOT, polluted,
                            ignore=shutil.ignore_patterns(".git", "__pycache__"))
            ledger = polluted / PAIN_REL
            mutated = ledger.read_text(encoding="utf-8")
            # Section body + heading, up to the next P-section or the roll-up.
            mutated, n_sections = re.subn(
                rf"^## {victim} .*?(?=^## P\d\d |^## 汇总判定表)",
                "", mutated, flags=re.M | re.S)
            self.assertEqual(1, n_sections,
                             f"{victim} section must be found once")
            # And its roll-up row, so the derived set stays balanced.
            mutated, n_rows = re.subn(rf"^\| {victim} .*?\n", "", mutated,
                                      flags=re.M)
            self.assertEqual(1, n_rows,
                             f"{victim} roll-up row must be removed too")
            self.assertNotIn(f"## {victim} ", mutated)
            ledger.write_text(mutated, encoding="utf-8")

            # The derived set is now balanced -- that is the point.
            ablated = ledger.read_text(encoding="utf-8")
            ablated_doc = set(re.findall(r"^## (P\d\d) ", ablated, re.M))
            ablated_table = ablated.split("## 汇总判定表", 1)[1]
            ablated_rows = set(re.findall(r"^\| (P\d\d) ", ablated_table, re.M))
            self.assertEqual(ablated_doc, ablated_rows,
                             "the derived set must stay balanced, otherwise "
                             "this control would be proving something else")
            self.assertNotIn(victim, ablated_doc)

            # And the guard's own function must report the gap.
            gaps = _pain_numbering_gaps(ablated)
            self.assertTrue(
                gaps, "removing a middle section must leave a numbering gap")
            self.assertIn(int(victim[1:]), gaps,
                          "the gap must name the section that was removed")

        # -- the ledger itself is untouched by the control --------------------
        self.assertEqual(original, read(PAIN_REL),
                         "the negative control must not mutate the real tree")


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
        """The non-goal must be stated in the framework, and the ticket must
        not restate it as a decision of its own.

        The original form asserted the phrase on FRAMEWORK_REL and then
        asserted it again on the CONCATENATION of both files -- the second
        assertion is implied by the first, so half of it could never fail.
        That is not a stylistic complaint: a check that cannot fail is a
        guard that protects nothing, which is the thing this whole class of
        test exists to rule out. What is actually worth asserting is the
        asymmetry -- the framework OWNS the non-goal, while the ticket
        delegates to it, so the ticket must carry the pointer and must not
        carry its own copy of the sentence.
        """
        self.assertIn("不**新建状态数据库", read(FRAMEWORK_REL))
        # The ticket reaches the same constraint by pointing at the owner,
        # and the detector that catches a restated domain is the same one
        # that has to stay quiet here.
        self.assertIn("§21.3", read(TICKET_REL))
        self.assertNotIn("不**新建状态数据库", read(TICKET_REL))

    def test_forbidden_overbuild_is_not_proposed(self):
        """The spec's explicit non-goals must stay non-goals."""
        body = read(FRAMEWORK_REL) + read(AGENTS_REL)
        for banned in ("defect database", "central CI platform",
                       "linter server"):
            with self.subTest(banned=banned):
                self.assertNotIn(banned, body)


if __name__ == "__main__":
    unittest.main()
