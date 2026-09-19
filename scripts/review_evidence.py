#!/usr/bin/env python3
"""REVIEW_EVIDENCE_CONTRACT_V1 — thin collect / validate CLI.

The single semantic detail owner of the Review Evidence interface is
references/review-evidence.md. This script is its thin mechanical consumer:

  validate  check a pack against the frozen machine contract
            (schemas/review-evidence.schema.json), against the candidate the
            caller says is under review, and -- once the structural and subject
            steps have both succeeded -- against the P1-T05 three-axis
            verification disposition
  collect   emit a schema-conforming, NON-AUTHORITATIVE skeleton assembled
            only from values the caller passes on the command line

Trust boundary (REQ-W2-04(d)), all four are hard constraints:

  * `commandRef` is a REFERENCE, never an execution authority. Nothing here
    runs it, and nothing here interprets an evidence field as something to do.
  * no network access of any kind and no arbitrary URL retrieval
  * no arbitrary filesystem authority: the only path ever written is the one
    the caller passes as the collect output, and no directory is enumerated
  * the machine pack never self-approves a reviewer verdict: the reviewer
    authority fields stay empty, and neither axis success is asserted here

What this script deliberately does NOT do (owned by other tickets): declare the
three-axis closed sets (they stay owned by the contract and by
references/review-evidence.md; this consumer reads their value domains out of
the loaded contract), define the trust boundary (P1-T06), define who may write
the reviewer authority fields (P1-T07), implement the reuse-descriptor lifecycle
(P1-T08), or verify the CLI entry points themselves (P1-T16).

The three-axis verification BEHAVIOUR is P1-T05's, and it is folded into the
existing `validate` flow: the public CLI has exactly two modes, `collect` and
`validate`. Inside `validate` the disposition runs only after structural
validation AND the subject expectation/binding step have both succeeded, and the
exit status follows the genuine final disposition.

Exit status contract (declared once, in references/review-evidence.md):
  0  validate: every check passed AND the final P1-T05 disposition allows PASS
     collect : the skeleton conforms and was written where the caller asked
  1  any failure; a machine-readable failure envelope is still printed on
     standard output
  0  for --help (argument parsing reports usage itself, on standard error)

That envelope is emitted on EVERY declared failure path, including an unusable
`--schema` contract and an unwritable explicit `--out`; no path may escape as a
raw traceback. The single exceptions are the two argument-parsing paths named
above, which argparse reports itself on standard error.

Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

TOOL = "review_evidence"
CONTRACT_VERSION = "REVIEW_EVIDENCE_CONTRACT_V1"

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "schemas/review-evidence.schema.json"
SCHEMA_PATH_DECLARED = "schemas/review-evidence.schema.json"

# The operators this consumer implements. A contract that uses any other
# operator is rejected instead of being silently ignored, so the schema and
# this CLI can never drift apart without a failure.
SUPPORTED_SCHEMA_KEYWORDS = frozenset({
    "$schema", "$id", "title", "description", "$defs", "$ref",
    "type", "required", "properties", "additionalProperties",
    "items", "minItems", "minLength", "pattern", "enum", "const", "oneOf",
})

ERROR_CODES = (
    "EVIDENCE_VERSION_UNKNOWN",
    "EVIDENCE_SUBJECT_MISMATCH",
    "EVIDENCE_STALE_SUBJECT",
    "REJECT",
)

STRUCTURAL_REASONS = frozenset({
    "PACK_ABSENT", "PACK_NOT_JSON", "PACK_NOT_AN_OBJECT",
    "UNKNOWN_SCHEMA_VERSION", "SCHEMA_INVALID", "SCHEMA_KEYWORD_UNSUPPORTED",
    "TYPE_MISMATCH", "CONST_VIOLATION", "ENUM_VIOLATION", "PATTERN_VIOLATION",
    "REQUIRED_FIELD_MISSING", "ADDITIONAL_PROPERTY_FORBIDDEN",
    "MIN_ITEMS_VIOLATION", "MIN_LENGTH_VIOLATION", "ONEOF_VIOLATION",
})

# Not structural: these are the declared error semantics of the contract.
NON_STRUCTURAL_REASONS = frozenset({
    "SUBJECT_REPO_MISMATCH", "SUBJECT_BASE_SHA_STALE",
    "SUBJECT_CANDIDATE_SHA_STALE", "STRUCTURALLY_VALID_NO",
})

# A whole-string placeholder token, the RULES.md R2 template form. It is only
# accepted where the contract asks for a plain string -- never for an enum or a
# const value, and never as a substitute for a required key.
PLACEHOLDER = re.compile(r"^\$\{[A-Z0-9_]+\}$")

# JSON Schema mandates ECMA-262 regular expression semantics. Python's differ
# for a whole family of character classes, each of which would accept a value
# the declared pattern does not permit, or reject one it does (the declared
# pattern text is never rewritten; it is translated into Python syntax that
# asserts what ECMA-262 asserts -- see the semantic owner, section 9.5):
#   * Python's `$` also matches just before a trailing newline, while ECMA-262's
#     `$` asserts the end of the input
#   * Python's `\d` also matches non-ASCII digits, while ECMA-262's `\d` is
#     exactly `[0-9]`
#   * Python's `\s` is Unicode whitespace (`str.isspace()`: it includes
#     U+001C-U+001F, U+0085, U+2028, U+2029 ...) while ECMA-262's `\s` is the
#     WhiteSpace + LineTerminator set (which includes U+FEFF and excludes those)
#   * Python's `\w` is Unicode-aware while ECMA-262's `\w` is ASCII-only
# A construct this consumer cannot translate faithfully is NEVER evaluated with
# Python semantics: the contract is refused (see UnsupportedPatternConstruct).
class UnsupportedPatternConstruct(ValueError):
    """A declared `pattern` uses a construct this consumer cannot evaluate with
    ECMA-262 meaning, so no Python fallback is permitted."""


# ECMA-262 `\s` (WhiteSpace + LineTerminator) and `\w` (ASCII word characters),
# as measured from an independent ECMA-262 engine -- deliberately not Python's
# same-named classes.
ECMA262_WHITESPACE = ("\\t\\n\\x0b\\x0c\\r \\u00a0\\u1680\\u2000-\\u200a"
                      "\\u2028\\u2029\\u202f\\u205f\\u3000\\ufeff")
ECMA262_WORD = "0-9A-Za-z_"
ECMA262_DIGIT = "0-9"

# The construct inventory this consumer translates. Anything outside it is
# refused rather than evaluated with Python semantics; the inventory is
# declared once, in the semantic owner's section 9.5, and read back by the test
# surface.
ECMA262_TRANSLATED_CONSTRUCTS = frozenset(
    {"$", "\\d", "\\D", "\\s", "\\S", "\\w", "\\W"})
# Escapes whose meaning is already identical in both engines and that are
# therefore passed through verbatim: the punctuation identity escapes and the
# control escapes. ECMA-262's other one-letter escapes (`\b`, `\B`, `\Z`,
# `\A`, `\cX`, `\p{...}`, a backreference, ...) do NOT mean what Python means
# by them and are refused.
ECMA262_EQUIVALENT_ESCAPES = frozenset("nrtfv" + "^$\\.*+?()[]{}|/-")

_ECMA262_CLASS_BODY = {"d": ECMA262_DIGIT, "s": ECMA262_WHITESPACE,
                       "w": ECMA262_WORD}
_ECMA262_COMPLEMENT_BODY = {"D": ECMA262_DIGIT, "S": ECMA262_WHITESPACE,
                            "W": ECMA262_WORD}
# Assertions whose meaning coincides in both engines.
ECMA262_EQUIVALENT_GROUPS = ("(?:", "(?=", "(?!")

_ECMA262_CACHE: dict = {}


def ecma262_pattern(pattern: str) -> str:
    """Translate a declared pattern into Python syntax with ECMA-262 meaning.

    Raises UnsupportedPatternConstruct for any construct this consumer cannot
    translate faithfully; it never falls back to Python's own semantics.
    """
    out: list = []
    index = 0
    length = len(pattern)
    in_class = False
    while index < length:
        char = pattern[index]
        if char == "\\":
            if index + 1 >= length:
                raise UnsupportedPatternConstruct("a trailing backslash")
            escaped = pattern[index + 1]
            if escaped in _ECMA262_COMPLEMENT_BODY:
                if in_class:
                    # A complemented class cannot be inlined among the other
                    # members of the enclosing class.
                    raise UnsupportedPatternConstruct(
                        f"the in-class complement escape '\\{escaped}'")
                out.append("[^" + _ECMA262_COMPLEMENT_BODY[escaped] + "]")
            elif escaped in _ECMA262_CLASS_BODY:
                body = _ECMA262_CLASS_BODY[escaped]
                out.append(body if in_class else "[" + body + "]")
            elif escaped in ECMA262_EQUIVALENT_ESCAPES:
                out.append(char + escaped)
            else:
                raise UnsupportedPatternConstruct(f"the escape '\\{escaped}'")
            index += 2
            continue
        if in_class:
            if char == "]":
                in_class = False
            out.append(char)
            index += 1
            continue
        if char == "[":
            # ECMA-262: CharacterClass :: [ [lookahead != ^] ClassRanges? ]
            #                             | [ ^ ClassRanges? ]
            # A `]` directly after `[` (or `[^`) therefore CLOSES the class:
            # `[]` is the empty class and `[^]` the empty negated class. There
            # is no POSIX-style rule reading a leading `]` as a literal member
            # -- applying one here would silently re-read `^[^]]$` as "one
            # character that is not `]`" where ECMA-262 reads "any one
            # character, then a literal `]`".
            cursor = index + 1
            negated = cursor < length and pattern[cursor] == "^"
            if negated:
                cursor += 1
            if cursor < length and pattern[cursor] == "]":
                if negated:
                    # `[^]` matches any single UTF-16 code unit. Python's
                    # engine has no code-unit mode, so the usual `[\s\S]`
                    # idiom would consume one astral code point where ECMA-262
                    # consumes one surrogate: an approximation, refused here
                    # for the same reason `.` is refused above.
                    raise UnsupportedPatternConstruct(
                        "the empty negated class '[^]' (it matches any one "
                        "UTF-16 code unit, which Python cannot express)")
                # `[]` matches no code unit at all, so `(?!)` -- which can never
                # succeed -- asserts exactly the same thing with no code-unit
                # question anywhere in it.
                out.append("(?!)")
                index = cursor + 1
                continue
            out.append("[^" if negated else "[")
            in_class = True
            index = cursor
            continue
        if char == "$":
            out.append("\\Z")
            index += 1
            continue
        if char == ".":
            # ECMA-262's `.` excludes every LineTerminator (including U+2028 and
            # U+2029); Python's excludes only `\n`. Not faithfully translatable.
            raise UnsupportedPatternConstruct("the '.' wildcard")
        if char == "(" and pattern[index:index + 2] == "(?" and not \
                pattern[index:index + 4].startswith(ECMA262_EQUIVALENT_GROUPS):
            raise UnsupportedPatternConstruct(
                f"the group construct {pattern[index:index + 4]!r}")
        out.append(char)
        index += 1
    if in_class:
        raise UnsupportedPatternConstruct("an unterminated character class")
    return "".join(out)


def _compile_ecma262(pattern: str):
    """The compiled form of a declared pattern, or a refusal; never a fallback."""
    compiled = _ECMA262_CACHE.get(pattern)
    if compiled is None:
        translated = ecma262_pattern(pattern)
        try:
            compiled = re.compile(translated)
        except re.error as exc:
            # A pattern that compiles for ECMA-262 but not for Python cannot be
            # evaluated here either.
            raise UnsupportedPatternConstruct(
                f"a construct Python cannot compile: {exc}") from exc
        _ECMA262_CACHE[pattern] = compiled
    return compiled


def pattern_matches(pattern: str, value: str) -> bool:
    """Evaluate a declared `pattern` keyword with ECMA-262 semantics.

    Raises UnsupportedPatternConstruct rather than evaluating with Python's
    own semantics.
    """
    return _compile_ecma262(pattern).search(value) is not None


def pattern_construct_problems(schema: dict) -> list:
    """Declared `pattern` texts this consumer cannot evaluate with ECMA-262
    meaning, so that an unusable contract is refused as a whole.

    A `pattern` that is not even a string declares no evaluable domain at all,
    and is refused here for the same reason: the alternative is a raw
    `TypeError` out of the regex engine, which no declared failure path may
    produce (section 9.2).
    """
    problems: list = []

    def walk(node, path: str) -> None:
        if not isinstance(node, dict):
            return
        if "pattern" in node:
            declared = node["pattern"]
            if not isinstance(declared, str):
                problems.append(
                    f"{path}.pattern is not a pattern string (found "
                    f"{_type_name(declared)})")
            else:
                try:
                    _compile_ecma262(declared)
                except UnsupportedPatternConstruct as exc:
                    problems.append(f"{path}.pattern uses {exc}")
        for key in ("properties", "$defs"):
            value = node.get(key)
            if isinstance(value, dict):
                for name, sub in value.items():
                    walk(sub, f"{path}.{name}")
        if isinstance(node.get("items"), dict):
            walk(node["items"], f"{path}.items")
        if isinstance(node.get("oneOf"), list):
            for position, sub in enumerate(node["oneOf"]):
                walk(sub, f"{path}.oneOf[{position}]")

    walk(schema, "$")
    return sorted(problems)


RESULT_FIELD = "STRUCTURALLY_VALID"
SUBJECT_POINTERS = ("repo", "baseSha", "candidateSha")


# ---------------------------------------------------------------------------
# contract loading (explicit path only; nothing is discovered)
# ---------------------------------------------------------------------------

def contract_object_problem(schema) -> str | None:
    """Why `schema` is not a contract object, or None when it is one.

    Step 0 of the frozen order judges the contract itself, so a parseable JSON
    value that is not a contract object is refused there rather than being
    carried into the pack judgement (where it could only surface as a version
    or shape complaint about the pack).
    """
    if not isinstance(schema, dict):
        return "it is not a JSON object"
    properties = schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return "it declares no root `properties` mapping"
    if not supported_schema_versions(schema):
        return "it declares no supported schemaVersion value domain"
    return None


def load_contract(schema_path: Path | None = None) -> dict:
    """Load the frozen machine contract from its declared path."""
    path = Path(schema_path) if schema_path else SCHEMA_PATH
    schema = json.loads(path.read_text(encoding="utf-8"))
    problem = contract_object_problem(schema)
    if problem is not None:
        # A contract that is not a contract object cannot be evaluated at all;
        # the CLI turns this into the declared SCHEMA_UNAVAILABLE failure
        # instead of silently accepting every pack or blaming the pack.
        raise ValueError(
            f"the value at {path} is not a contract object: {problem}")
    return {
        "schema": schema,
        "schemaPath": SCHEMA_PATH_DECLARED if not schema_path else str(schema_path),
        "supportedSchemaVersions": supported_schema_versions(schema),
        "errorCodes": list(ERROR_CODES),
    }


def supported_schema_versions(schema: dict) -> list:
    """Read the accepted schemaVersion value domain out of the contract."""
    node = schema.get("properties", {}).get("schemaVersion", {})
    if "const" in node:
        return [node["const"]]
    return list(node.get("enum", []))


def unsupported_keywords(schema: dict) -> list:
    """Operators used by the contract that this consumer does not implement."""
    unknown: list = []

    def walk(node) -> None:
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            if key in ("properties", "$defs"):
                for sub in value.values():
                    walk(sub)
                continue
            if key not in SUPPORTED_SCHEMA_KEYWORDS:
                unknown.append(key)
                continue
            if key in ("items", "oneOf", "additionalProperties", "not"):
                if isinstance(value, dict):
                    walk(value)
                elif isinstance(value, list):
                    for sub in value:
                        walk(sub)

    walk(schema)
    return sorted(set(unknown))


# ---------------------------------------------------------------------------
# minimal contract evaluator (the declared operator subset above)
# ---------------------------------------------------------------------------

def _type_name(value) -> str:
    # bool is an int subclass in Python: name it first so True can never alias
    # its way into an integer-typed field.
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "null"


def _violation(code: str, reason: str, path: str, detail: str) -> dict:
    return {"code": code, "reason": reason, "path": path, "detail": detail}


def _resolve_ref(ref: str, schema: dict):
    prefix = "#/$defs/"
    if isinstance(ref, str) and ref.startswith(prefix):
        return schema.get("$defs", {}).get(ref[len(prefix):])
    return None


def _node_violations(node, value, path, schema, allow_placeholders, out) -> None:
    if not isinstance(node, dict):
        return

    if "$ref" in node:
        target = _resolve_ref(node["$ref"], schema)
        if target is None:
            out.append(_violation("REJECT", "SCHEMA_INVALID", path,
                                  f"unresolvable reference {node['$ref']!r}"))
            return
        _node_violations(target, value, path, schema, allow_placeholders, out)
        return

    if "type" in node:
        allowed = node["type"] if isinstance(node["type"], list) else [node["type"]]
        actual = _type_name(value)
        if actual not in allowed:
            out.append(_violation("REJECT", "TYPE_MISMATCH", path,
                                  f"expected {allowed}, found {actual}"))
            return

    if allow_placeholders and isinstance(value, str) and PLACEHOLDER.match(value) \
            and "enum" not in node and "const" not in node:
        return

    if "const" in node:
        expected = node["const"]
        alias = isinstance(value, bool) != isinstance(expected, bool)
        if alias or value != expected:
            out.append(_violation("REJECT", "CONST_VIOLATION", path,
                                  f"expected {expected!r}, found {value!r}"))
            return

    if "enum" in node and value not in node["enum"]:
        out.append(_violation("REJECT", "ENUM_VIOLATION", path,
                              f"{value!r} is outside the declared closed set"))
        return

    if isinstance(value, str):
        if "pattern" in node:
            try:
                matched = pattern_matches(node["pattern"], value)
            except UnsupportedPatternConstruct as exc:
                # Fail closed: never evaluate an untranslatable pattern with
                # Python's semantics, and never report the value as the fault.
                out.append(_violation(
                    "REJECT", "SCHEMA_KEYWORD_UNSUPPORTED", path,
                    f"the declared pattern cannot be evaluated with ECMA-262 "
                    f"meaning because it uses {exc}"))
            else:
                if not matched:
                    out.append(_violation("REJECT", "PATTERN_VIOLATION", path,
                                          f"{value!r} does not match the "
                                          "declared shape"))
        if "minLength" in node and len(value) < node["minLength"]:
            out.append(_violation("REJECT", "MIN_LENGTH_VIOLATION", path,
                                  "shorter than the declared minimum length"))

    if isinstance(value, list):
        if "minItems" in node and len(value) < node["minItems"]:
            out.append(_violation("REJECT", "MIN_ITEMS_VIOLATION", path,
                                  "fewer items than the declared minimum"))
        if "items" in node:
            for index, item in enumerate(value):
                _node_violations(node["items"], item, f"{path}[{index}]",
                                 schema, allow_placeholders, out)

    if isinstance(value, dict):
        for key in node.get("required", []):
            if key not in value:
                out.append(_violation("REJECT", "REQUIRED_FIELD_MISSING",
                                      f"{path}.{key}",
                                      "the key must be present explicitly"))
        declared = node.get("properties", {})
        for key, sub in declared.items():
            if key in value:
                _node_violations(sub, value[key], f"{path}.{key}", schema,
                                 allow_placeholders, out)
        if node.get("additionalProperties") is False:
            for key in value:
                if key not in declared:
                    out.append(_violation("REJECT",
                                          "ADDITIONAL_PROPERTY_FORBIDDEN",
                                          f"{path}.{key}",
                                          "not part of the frozen contract"))

    if "oneOf" in node:
        matched = 0
        for branch in node["oneOf"]:
            branch_out: list = []
            _node_violations(branch, value, path, schema, allow_placeholders,
                             branch_out)
            if not branch_out:
                matched += 1
        if matched != 1:
            out.append(_violation("REJECT", "ONEOF_VIOLATION", path,
                                  f"{matched} alternative shapes matched, "
                                  "exactly one must"))


def schema_violations(pack, schema: dict | None = None, allow_placeholders: bool = False) -> list:
    """Structural violations of the pack against the frozen contract."""
    contract = schema if schema is not None else load_contract()["schema"]
    unknown = unsupported_keywords(contract)
    if unknown:
        return [_violation("REJECT", "SCHEMA_KEYWORD_UNSUPPORTED", "$schema",
                           f"the contract uses operators this consumer does not "
                           f"implement: {unknown}")]
    untranslatable = pattern_construct_problems(contract)
    if untranslatable:
        # The same rule as an unsupported operator: a contract this consumer
        # cannot evaluate is refused instead of being evaluated approximately.
        return [_violation("REJECT", "SCHEMA_KEYWORD_UNSUPPORTED", "$schema",
                           "the contract declares patterns this consumer cannot "
                           "evaluate with ECMA-262 semantics: "
                           + "; ".join(untranslatable))]
    out: list = []
    _node_violations(contract, pack, "$", contract, allow_placeholders, out)
    return out


# ---------------------------------------------------------------------------
# validation, in the frozen order:
#   parse -> version -> structure -> subject -> declared structural axis
# ---------------------------------------------------------------------------

def validate_pack(pack, schema: dict | None = None, expect_repo=None,
                  expect_base_sha=None, expect_candidate_sha=None,
                  allow_placeholders: bool = False,
                  require_expected_subject: bool = False) -> dict:
    contract = schema if schema is not None else load_contract()["schema"]
    violations: list = []

    if not isinstance(pack, dict):
        violations.append(_violation("REJECT", "PACK_NOT_AN_OBJECT", "$",
                                     f"a pack must be an object, found "
                                     f"{_type_name(pack)}"))
        return {"ok": False, "violations": violations,
                "schemaVersion": None}

    version = pack.get("schemaVersion")
    supported = supported_schema_versions(contract)
    if isinstance(version, bool) or not isinstance(version, int) \
            or version not in supported:
        # An unknown version is rejected outright: the contract for that
        # version is not known, so no migration may be guessed and no further
        # interpretation of the pack is legitimate.
        return {"ok": False,
                "violations": [_violation(
                    "EVIDENCE_VERSION_UNKNOWN", "UNKNOWN_SCHEMA_VERSION", "$.schemaVersion",
                    f"schemaVersion {version!r} is not in the supported value "
                    f"domain {supported}; no migration is guessed")],
                "schemaVersion": version}

    violations.extend(schema_violations(pack, schema=contract,
                                        allow_placeholders=allow_placeholders))

    if not violations:
        subject = pack.get("subject", {})
        # The subject-enforcement rule (AC-06). A verdict about a subject can
        # only be issued against a declared target subject, and the target is
        # declared completely or not at all: a partial declaration would
        # silently enforce only part of the subject while still reporting a
        # passing subject check.
        expectations = (expect_repo, expect_base_sha, expect_candidate_sha)
        supplied = sum(value is not None for value in expectations)
        if supplied not in (0, len(expectations)):
            violations.append(_violation(
                "REJECT", "SUBJECT_EXPECTATION_INCOMPLETE", "$.subject",
                "the target subject must be declared completely (repository, "
                "base SHA and candidate SHA) or not at all"))
        elif require_expected_subject and supplied == 0:
            violations.append(_violation(
                "REJECT", "SUBJECT_EXPECTATION_ABSENT", "$.subject",
                "no target subject was declared, so no subject-consistency "
                "verdict can be issued"))
        if not violations:
            if expect_repo is not None and subject.get("repo") != expect_repo:
                violations.append(_violation(
                    "EVIDENCE_SUBJECT_MISMATCH", "SUBJECT_REPO_MISMATCH",
                    "$.subject.repo",
                    "the pack declares a repository other than the target"))
            if expect_base_sha is not None and subject.get("baseSha") != expect_base_sha:
                violations.append(_violation(
                    "EVIDENCE_STALE_SUBJECT", "SUBJECT_BASE_SHA_STALE",
                    "$.subject.baseSha",
                    "the pack declares a base SHA other than the reviewed base"))
            if expect_candidate_sha is not None \
                    and subject.get("candidateSha") != expect_candidate_sha:
                violations.append(_violation(
                    "EVIDENCE_STALE_SUBJECT", "SUBJECT_CANDIDATE_SHA_STALE",
                    "$.subject.candidateSha",
                    "the pack declares a candidate SHA other than the candidate "
                    "under review"))

    if not violations and pack.get(RESULT_FIELD) != "YES":
        # The declared structural axis. NO does not enter consumption; the
        # disposition of the other two axes is not decided here.
        violations.append(_violation(
            "REJECT", "STRUCTURALLY_VALID_NO", f"$.{RESULT_FIELD}",
            "a pack that declares itself not structurally valid does not enter "
            "consumption"))

    return {"ok": not violations, "violations": violations,
            "schemaVersion": version}


# ---------------------------------------------------------------------------
# P1-T05 three-axis verification disposition (behaviour owner: P1-T05)
# ---------------------------------------------------------------------------

# The single declaration point for every closed set is the contract
# (schemas/review-evidence.schema.json / references/review-evidence.md §4).
# This consumer reads each value domain from the loaded contract at runtime and
# NEVER enumerates it: a competing enumeration would be a CE-28 / CE-30
# violation. That applies to the digest domain too -- `artifacts[].contentDigest`
# .pattern is read from the contract, and there is deliberately NO local
# substitute for it. When the contract provides no usable pattern the
# disposition fails closed (see DIGEST_PATTERN_UNAVAILABLE below) instead of
# re-declaring the shape here.

# Disposition `reason` codes. These are NOT structural reasons and NOT the
# frozen error semantics of P1-T04: they are P1-T05's verification findings,
# kept disjoint from the structural vocabulary so the two layers never alias.
DISPOSITION_REASONS = (
    "STRUCTURALLY_VALID_NO", "AXIS_COLLAPSE",
    "EVIDENCE_INSUFFICIENT", "CI_NOT_OBSERVED", "CI_NOT_PASS",
    "DIGEST_MALFORMED", "MISSING_ARTIFACT", "DIGEST_PATTERN_UNAVAILABLE",
)


def _contract_get(schema, dotted):
    """Read an arbitrary node out of the contract by dotted path.

    Returns None when any segment is missing, so a consumer can fail closed
    instead of re-declaring a value domain (CE-30).
    """
    node = schema
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def _contract_enum(schema, dotted):
    """Read a declared closed value domain from the contract.

    Returns an empty domain when the node is absent so the disposition fails
    closed; it never substitutes a locally enumerated set for the contract.
    """
    node = _contract_get(schema, dotted)
    if isinstance(node, list):
        return set(node)
    return set()


def _usable_declared_pattern(declared) -> str | None:
    """The contract's declared pattern text, or None when it is unusable.

    "Usable" means a string this consumer can evaluate with ECMA-262 meaning
    through the canonical evaluator (`pattern_matches`). There is no local
    substitute for a pattern the contract does not provide: the caller fails
    closed instead.
    """
    if not isinstance(declared, str):
        return None
    try:
        _compile_ecma262(declared)
    except UnsupportedPatternConstruct:
        return None
    return declared


def evidence_disposition(pack, schema=None) -> dict:
    """P1-T05 three-axis verification disposition.

    Consumes the three orthogonal axes declared in the frozen contract
    (STRUCTURALLY_VALID, SOURCE_VERIFICATION_STATE, EVIDENCE_SUFFICIENCY) and
    the CI-observed fact, and decides whether PASS is allowed. It is a
    CONSUMER of the frozen closed sets: their value domains are read from the
    loaded contract, never re-declared here (CE-30). The disposition rules
    themselves are declared in references/review-evidence.md section 9.6.

    The digest domain is consumed the same way: `artifacts[].contentDigest`
    .pattern is read from the contract and evaluated through the canonical
    ECMA-262 evaluator. When the contract provides no usable pattern the
    disposition fails closed (DIGEST_PATTERN_UNAVAILABLE) rather than
    substituting a locally declared shape.

    Returns a verdict dict:
        {
          "passAllowed": bool,
          "findings": [{"code", "reason", "path", "detail"}, ...],
          "originalSourceState": <recorded SOURCE_VERIFICATION_STATE or None>,
        }

    The recorded source state is preserved VERBATIM: TEMPORARILY_UNAVAILABLE
    is never rewritten to INVALID, and the disposition never mutates the pack.
    """
    if not isinstance(pack, dict):
        return {
            "passAllowed": False,
            "findings": [{"code": "REJECT", "reason": "PACK_NOT_AN_OBJECT",
                          "path": "$",
                          "detail": "a pack must be an object"}],
            "originalSourceState": None,
        }

    contract = schema if schema is not None else load_contract()["schema"]

    source_values = _contract_enum(
        contract, "properties.SOURCE_VERIFICATION_STATE.enum")
    sufficiency_values = _contract_enum(
        contract, "properties.EVIDENCE_SUFFICIENCY.enum")
    structural_values = _contract_enum(
        contract, "properties.STRUCTURALLY_VALID.enum")
    digest_pattern = _usable_declared_pattern(_contract_get(
        contract, "properties.artifacts.items.properties.contentDigest.pattern"))

    source_state = pack.get("SOURCE_VERIFICATION_STATE")
    sufficiency = pack.get("EVIDENCE_SUFFICIENCY")
    structural = pack.get(RESULT_FIELD)
    # Preserve the recorded source state verbatim; it is never rewritten.
    original_source_state = source_state

    findings = []

    # -- STRUCTURAL axis ----------------------------------------------------
    if structural not in structural_values or structural != "YES":
        findings.append({
            "code": "REJECT", "reason": "STRUCTURALLY_VALID_NO",
            "path": f"$.{RESULT_FIELD}",
            "detail": "a pack that declares itself not structurally valid does "
                      "not enter consumption"})

    # -- SOURCE axis (independent of sufficiency) ---------------------------
    # The disposition references only the positive member of this axis; every
    # other declared member is handled by a name-derived reason code so the
    # closed set is never enumerated here (CE-30). The temporarily-unavailable
    # member is preserved under its own code and is never rewritten to the
    # invalid member.
    positive_source = "VERIFIED"
    if source_state not in source_values:
        findings.append({
            "code": "REJECT", "reason": "AXIS_COLLAPSE",
            "path": "$.SOURCE_VERIFICATION_STATE",
            "detail": f"{source_state!r} is not a source-axis value; it belongs "
                      f"to another axis (axis collapse)"})
    elif source_state == positive_source:
        pass  # fully verified source: no source-axis block on its own
    else:
        # The reason is derived from the recorded member name; it is never
        # rewritten (the temporarily-unavailable member keeps its own code).
        findings.append({
            "code": "REJECT", "reason": "SOURCE_" + source_state,
            "path": "$.SOURCE_VERIFICATION_STATE",
            "detail": "the recorded source state blocks PASS"})

    # -- SUFFICIENCY axis (independent of source) ---------------------------
    if sufficiency not in sufficiency_values:
        findings.append({
            "code": "REJECT", "reason": "AXIS_COLLAPSE",
            "path": "$.EVIDENCE_SUFFICIENCY",
            "detail": f"{sufficiency!r} is not an EVIDENCE_SUFFICIENCY value"})
    elif sufficiency == "INSUFFICIENT":
        # Legal combination with VERIFIED (not a contradiction); it blocks
        # PASS but must never be reported as axis collapse.
        findings.append({
            "code": "REJECT", "reason": "EVIDENCE_INSUFFICIENT",
            "path": "$.EVIDENCE_SUFFICIENCY",
            "detail": "the evidence is insufficient to allow PASS; a legal "
                      "combination with VERIFIED, not a contradiction"})

    # -- CI-observed fact (CI_STATUS domain, never a second CI machine) ------
    ci = pack.get("ci") if isinstance(pack.get("ci"), dict) else {}
    ci_run = ci.get("run")
    ci_state = ci.get("originalState")
    if not ci_run:
        # An empty run means no CI observation was recorded; not a PASS.
        findings.append({
            "code": "REJECT", "reason": "CI_NOT_OBSERVED",
            "path": "$.ci.run",
            "detail": "no CI run was recorded; nothing to treat as PASS"})
    elif ci_state != "PASS":
        findings.append({
            "code": "REJECT", "reason": "CI_NOT_PASS",
            "path": "$.ci.originalState",
            "detail": f"CI originalState={ci_state!r} is not PASS"})

    # -- artifact / digest consumption --------------------------------------
    artifacts = pack.get("artifacts") if isinstance(pack.get("artifacts"),
                                                    list) else []
    artifact_locations = {a.get("location") for a in artifacts
                          if isinstance(a, dict)}
    if digest_pattern is None:
        # The contract provides no digest domain this consumer can evaluate.
        # Fail closed: the digest axis cannot be cleared, and substituting a
        # locally remembered shape here would make this consumer a second
        # declaration point for a closed set the contract owns (CE-28 / CE-30).
        findings.append({
            "code": "REJECT", "reason": "DIGEST_PATTERN_UNAVAILABLE",
            "path": "$.artifacts[].contentDigest",
            "detail": "the contract declares no contentDigest pattern this "
                      "consumer can evaluate with ECMA-262 meaning, and no local "
                      "substitute is permitted; the digest axis cannot be "
                      "cleared, so PASS is blocked"})
    else:
        for a in artifacts:
            if not isinstance(a, dict):
                continue
            digest = a.get("contentDigest")
            # The declared pattern is evaluated by the canonical ECMA-262
            # evaluator: a second, Python-native regex path would answer
            # differently for the same declared pattern and value.
            if not (isinstance(digest, str)
                    and pattern_matches(digest_pattern, digest)):
                findings.append({
                    "code": "REJECT", "reason": "DIGEST_MALFORMED",
                    "path": "$.artifacts[].contentDigest",
                    "detail": f"artifact digest {digest!r} is not a valid "
                              f"'algorithm:hex' form"})

    # Every check's artifactRefs must resolve to a declared artifact.
    checks = pack.get("checks") if isinstance(pack.get("checks"), list) else []
    for c in checks:
        if not isinstance(c, dict):
            continue
        for ref in (c.get("artifactRefs") or []):
            if ref not in artifact_locations:
                findings.append({
                    "code": "REJECT", "reason": "MISSING_ARTIFACT",
                    "path": "$.checks[].artifactRefs",
                    "detail": f"check {c.get('id')!r} references artifact "
                              f"{ref!r} which is not present in artifacts[]"})

    return {
        "passAllowed": len(findings) == 0,
        "findings": findings,
        "originalSourceState": original_source_state,
    }


# ---------------------------------------------------------------------------
# collect: thin, non-authoritative, local inputs only
# ---------------------------------------------------------------------------

def collect_skeleton(repo: str, base_sha: str, candidate_sha: str,
                     producer_identity: str, producer_version: str,
                     observed_at: str) -> dict:
    """A schema-conforming skeleton from explicitly passed values only.

    Nothing is fetched, discovered or run, and no reviewer authority is
    populated: the reviewer fields stay empty because only reviewer authority
    may fill them.
    """
    return {
        "schemaVersion": 1,
        "subject": {
            "repo": repo,
            "baseSha": base_sha,
            "candidateSha": candidate_sha,
        },
        "authorityRefs": [],
        "producer": {
            "identity": producer_identity,
            "version": producer_version,
            "observedAt": observed_at,
        },
        "checks": [],
        "artifacts": [],
        "ci": {
            "run": "",
            "job": "",
            "checkedSha": "",
            "originalState": "UNKNOWN",
        },
        "grounding": {
            "mode": "UNAVAILABLE",
            "coverage": "",
            "evidenceRef": "",
        },
        "seams": {
            "applicability": "REQUIRED",
            "evidenceRefs": [],
        },
        "reuse": {
            "sourceEvidence": "",
            "validFor": "",
            "dependencies": [],
            "invalidation": "",
        },
        "unverified": [
            "checks[] is empty: no native test or CI result was supplied to collect",
            "artifacts[] is empty: no artifact reference was supplied to collect",
            "ci.run/job/checkedSha are empty: no CI observation was supplied to collect",
            "grounding.mode is UNAVAILABLE: collect performed no grounding",
            "reuse.dependencies is empty: no dependency analysis was supplied to collect",
            "semanticScopeStatus and reviewerDecisionRefs carry no reviewer value: "
            "reviewer authority is not derivable from the machine pack",
        ],
        RESULT_FIELD: "YES",
        "SOURCE_VERIFICATION_STATE": "NOT_VERIFIED",
        "EVIDENCE_SUFFICIENCY": "INSUFFICIENT",
        "semanticScopeStatus": None,
        "reviewerDecisionRefs": [],
    }


# ---------------------------------------------------------------------------
# argv surface
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="review_evidence.py",
        description="Thin collect / validate consumer of "
                    f"{CONTRACT_VERSION} (semantic owner: "
                    "references/review-evidence.md).")
    sub = parser.add_subparsers(dest="mode", required=True)

    check = sub.add_parser("validate", help="validate a pack against the contract")
    check.add_argument("--pack", required=True,
                       help="path to the pack to validate")
    check.add_argument("--expect-repo", default=None,
                       help="the target repository the pack must declare; the "
                            "three --expect-* flags are declared together or "
                            "not at all")
    check.add_argument("--expect-base-sha", default=None,
                       help="the reviewed base SHA the pack must declare; the "
                            "three --expect-* flags are declared together or "
                            "not at all")
    check.add_argument("--expect-candidate-sha", default=None,
                       help="the candidate under review the pack must declare; "
                            "the three --expect-* flags are declared together "
                            "or not at all")
    check.add_argument("--allow-placeholders", action="store_true",
                       help="accept the RULES.md R2 placeholder template form "
                            "for plain string values only; this is the sole "
                            "declared mode that needs no target subject")
    check.add_argument("--schema", default=None,
                       help="override the contract path (default: the "
                            "declared path)")

    gather = sub.add_parser("collect", help="emit a non-authoritative skeleton")
    gather.add_argument("--out", default=None,
                        help="explicit output path; nothing else is ever "
                             "written")
    gather.add_argument("--repo", required=True)
    gather.add_argument("--base-sha", required=True)
    gather.add_argument("--candidate-sha", required=True)
    gather.add_argument("--producer-identity", required=True)
    gather.add_argument("--producer-version", required=True)
    gather.add_argument("--observed-at", default=None,
                        help="ISO-8601 UTC timestamp; defaults to now")
    gather.add_argument("--schema", default=None)

    return parser


def _envelope(mode: str, result: dict, contract: dict,
              skeleton: dict | None = None,
              skeleton_path: str | None = None) -> dict:
    return {
        "tool": TOOL,
        "contractVersion": CONTRACT_VERSION,
        "mode": mode,
        "ok": result["ok"],
        "exitCode": 0 if result["ok"] else 1,
        "contract": {
            "schemaPath": contract["schemaPath"],
            "supportedSchemaVersions": contract["supportedSchemaVersions"],
            "errorCodes": contract["errorCodes"],
        },
        "violations": result["violations"],
        # Declared once in the owner, section 9.3. The keys are emitted on every
        # path so the envelope SHAPE never varies; only the values do, and only
        # `collect` ever populates them. The P1-T05 disposition result travels
        # inside `violations` (owner section 9.6.3) rather than in a new
        # envelope key, so the declared envelope shape stays single-owned.
        "skeleton": skeleton,
        "skeletonPath": skeleton_path,
    }


def _emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # Declared exception (owner, section 9.2): --help and a usage error are
        # reported by argparse itself on standard error and emit no envelope.
        if exc.code == 0:
            return 0
        return 1

    schema_path = SCHEMA_PATH_DECLARED if not args.schema else str(args.schema)
    try:
        contract = load_contract(args.schema)
    except Exception:  # noqa: BLE001 - an unusable contract is a declared path
        # Step 0 of the frozen order: without a readable contract there is no
        # pack judgement to make, and the failure is still declared output.
        result = {"ok": False, "violations": [_violation(
            "REJECT", "SCHEMA_UNAVAILABLE", "$.schema",
            f"the declared contract at {schema_path} could not be read, "
            "parsed, or is not a contract object")]}
        _emit(_envelope(args.mode, result, {
            "schemaPath": schema_path,
            "supportedSchemaVersions": [],
            "errorCodes": list(ERROR_CODES),
        }))
        return 1
    contract["schemaPath"] = schema_path

    if args.mode == "validate":
        pack_path = Path(args.pack)
        pack = None
        if not pack_path.is_file():
            result = {"ok": False, "violations": [_violation(
                "REJECT", "PACK_ABSENT", "$.pack",
                f"no pack at {args.pack}")]}
        else:
            try:
                pack = json.loads(pack_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 - a malformed pack is a finding
                pack = None
                result = {"ok": False, "violations": [_violation(
                    "REJECT", "PACK_NOT_JSON", "$.pack",
                    "the pack is not parseable as JSON")]}
            else:
                result = validate_pack(
                    pack, schema=contract["schema"],
                    expect_repo=args.expect_repo,
                    expect_base_sha=args.expect_base_sha,
                    expect_candidate_sha=args.expect_candidate_sha,
                    allow_placeholders=args.allow_placeholders,
                    # Placeholder mode is the sole declared exemption: a
                    # placeholder-form template is not a claim about a concrete
                    # candidate and therefore declares no target subject.
                    require_expected_subject=not args.allow_placeholders)

        # The P1-T05 behaviour, folded into the frozen order AFTER the declared
        # structural axis: contract load -> pack parse -> version -> structure ->
        # subject expectation/binding -> declared structural axis -> disposition.
        # A pack that failed any earlier step never reaches the disposition, so
        # a wrong repo / baseSha / candidateSha can never reach behavioural PASS.
        # The verdict is reported through the declared `violations` list under
        # the P1-T05 reason codes (owner section 9.6.3): the envelope keeps the
        # shape P1-T04 declares, with a single failure list.
        if result["ok"] and not args.allow_placeholders:
            disposition = evidence_disposition(pack, schema=contract["schema"])
            if not disposition["passAllowed"]:
                # The final disposition is the one that decides the exit status:
                # a structurally valid, subject-bound pack whose axes block PASS
                # is a failure of this command.
                result = {"ok": False,
                          "violations": result["violations"]
                          + disposition["findings"],
                          "schemaVersion": result["schemaVersion"]}

        _emit(_envelope("validate", result, contract))
        return 0 if result["ok"] else 1

    skeleton = collect_skeleton(
        repo=args.repo, base_sha=args.base_sha, candidate_sha=args.candidate_sha,
        producer_identity=args.producer_identity,
        producer_version=args.producer_version,
        observed_at=args.observed_at or _utc_now())
    # Fail closed: collect reports success only if what it produced actually
    # conforms to the same contract a consumer will apply.
    result = validate_pack(skeleton, schema=contract["schema"])
    envelope = _envelope("collect", result, contract, skeleton=skeleton)
    if result["ok"] and args.out:
        out_path = Path(args.out)
        try:
            if out_path.parent and not out_path.parent.is_dir():
                out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(skeleton, indent=2, ensure_ascii=False)
                                + "\n", encoding="utf-8")
        except OSError as exc:  # a declared failure path, never a traceback
            envelope["ok"] = False
            envelope["exitCode"] = 1
            envelope["violations"] = [_violation(
                "REJECT", "OUTPUT_NOT_WRITABLE", "$.out",
                f"the explicit output path {args.out} could not be written: "
                f"{type(exc).__name__}")]
            _emit(envelope)
            return 1
        envelope["skeletonPath"] = str(out_path)
    _emit(envelope)
    return 0 if envelope["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
