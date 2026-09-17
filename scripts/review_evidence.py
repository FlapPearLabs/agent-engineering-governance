#!/usr/bin/env python3
"""REVIEW_EVIDENCE_CONTRACT_V1 — thin collect / validate CLI.

The single semantic detail owner of the Review Evidence interface is
references/review-evidence.md. This script is its thin mechanical consumer:

  validate  check a pack against the frozen machine contract
            (schemas/review-evidence.schema.json) and against the candidate
            the caller says is under review
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

What this script deliberately does NOT do (owned by other tickets): decide the
three-axis verification behaviour or its disposition (P1-T05), define the trust
boundary (P1-T06), define who may write the reviewer authority fields
(P1-T07), implement the reuse-descriptor lifecycle (P1-T08), or verify the CLI
entry points themselves (P1-T16).

Exit status contract (declared once, in references/review-evidence.md):
  0  every check passed
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

# JSON Schema mandates ECMA-262 regular expression semantics, which differ from
# Python's in two ways that would each accept a value the declared pattern does
# not permit. The declared pattern text is never rewritten; it is translated
# into Python syntax that asserts what ECMA-262 asserts (see the semantic owner,
# section 9.5):
#   * Python's `$` also matches just before a trailing newline, while ECMA-262's
#     `$` asserts the end of the input
#   * Python's `\d` also matches non-ASCII digits, while ECMA-262's `\d` is
#     exactly `[0-9]`
_ECMA262_CACHE: dict = {}


def ecma262_pattern(pattern: str) -> str:
    """Translate a declared pattern into Python syntax with ECMA-262 meaning."""
    out: list = []
    index = 0
    length = len(pattern)
    in_class = False
    while index < length:
        char = pattern[index]
        if char == "\\" and index + 1 < length:
            escaped = pattern[index + 1]
            if escaped == "d":
                out.append("0-9" if in_class else "[0-9]")
            elif escaped == "D":
                # An in-class `\D` cannot be inlined without knowing the other
                # class members; the declared contract uses none.
                out.append("\\D" if in_class else "[^0-9]")
            else:
                out.append(char + escaped)
            index += 2
            continue
        if in_class:
            if char == "]":
                in_class = False
            out.append(char)
            index += 1
            continue
        if char == "[":
            in_class = True
            out.append(char)
            index += 1
            if index < length and pattern[index] == "^":
                out.append("^")
                index += 1
            if index < length and pattern[index] == "]":
                out.append("]")
                index += 1
            continue
        if char == "$":
            out.append("\\Z")
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def pattern_matches(pattern: str, value: str) -> bool:
    """Evaluate a declared `pattern` keyword with ECMA-262 semantics."""
    compiled = _ECMA262_CACHE.get(pattern)
    if compiled is None:
        compiled = re.compile(ecma262_pattern(pattern))
        _ECMA262_CACHE[pattern] = compiled
    return compiled.search(value) is not None


RESULT_FIELD = "STRUCTURALLY_VALID"
SUBJECT_POINTERS = ("repo", "baseSha", "candidateSha")


# ---------------------------------------------------------------------------
# contract loading (explicit path only; nothing is discovered)
# ---------------------------------------------------------------------------

def load_contract(schema_path: Path | None = None) -> dict:
    """Load the frozen machine contract from its declared path."""
    path = Path(schema_path) if schema_path else SCHEMA_PATH
    schema = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(schema, dict):
        # A contract that is not an object cannot be evaluated at all; the CLI
        # turns this into the declared SCHEMA_UNAVAILABLE failure instead of
        # silently accepting every pack.
        raise ValueError(f"the contract at {path} is not a JSON object")
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
        if "pattern" in node and not pattern_matches(node["pattern"], value):
            out.append(_violation("REJECT", "PATTERN_VIOLATION", path,
                                  f"{value!r} does not match the declared shape"))
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


def _envelope(mode: str, result: dict, contract: dict) -> dict:
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
        if not pack_path.is_file():
            result = {"ok": False, "violations": [_violation(
                "REJECT", "PACK_ABSENT", "$.pack",
                f"no pack at {args.pack}")]}
        else:
            try:
                pack = json.loads(pack_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 - a malformed pack is a finding
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
    envelope = _envelope("collect", result, contract)
    envelope["skeleton"] = skeleton
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
    elif result["ok"]:
        envelope["skeletonPath"] = None
    _emit(envelope)
    return 0 if envelope["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
