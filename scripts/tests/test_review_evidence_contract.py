"""Counterexample-first contract tests for the Review Evidence interface (P1-T04 / Issue #11).

SUPPORTING SURFACE (RULES.md R6, declared): the frozen interface lives in four
coordinated surfaces --

    references/review-evidence.md          single semantic detail owner
    schemas/review-evidence.schema.json    versioned machine contract
    templates/review-evidence.json         placeholder-form template
    scripts/review_evidence.py             thin collect / validate CLI

-- and this module is the test surface that consumes them. It declares no part
of the interface; every field name and closed set asserted below is a readback
of what those four surfaces must declare exactly once.

RED DISCIPLINE (references/ticket-lane.md section 4): while the contract is
absent every test fails with an explicit ``CONTRACT_ABSENT`` message. RED is
never allowed to surface as ImportError / ModuleNotFoundError / a broken
harness. Each test acquires its subject through a ``require_*`` helper that
fails the test with that message instead of raising.

Counters covered (HIGH risk requires at least five meaningful counterexamples):
CE-06 wrong repo / baseSha / candidateSha; CE-10 schema vs validator sample
disposition; CE-24 CHECK_STATUS used as a CI status machine; CE-28 dual
canonical owner of the interface. Plus the ticket-local counters: unknown
schemaVersion, missing required result field, CHECK_STATUS outside its closed
set, ``ci.originalState`` outside the seven-value set, ``unverified[]`` omission
versus an explicit empty array, a free-text reuse descriptor, an invalid reuse
VERIFICATION_STATE, template/schema divergence, axis collapse (``INSUFFICIENT``
on the source axis), the legal ``SOURCE_VERIFICATION_STATE = VERIFIED`` together
with ``EVIDENCE_SUFFICIENCY = INSUFFICIENT`` pair, and ``seams.applicability =
N/A`` without a reason or without an acceptance reference.

Stdlib only. Run with:
    python3 -m unittest scripts.tests.test_review_evidence_contract -v
"""
from __future__ import annotations

import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CLI_PATH = ROOT / "scripts" / "review_evidence.py"
SCHEMA_PATH = ROOT / "schemas" / "review-evidence.schema.json"
TEMPLATE_PATH = ROOT / "templates" / "review-evidence.json"
REFERENCE_PATH = ROOT / "references" / "review-evidence.md"
CI_REFERENCE_PATH = ROOT / "references/git-ci-integration.md"

# --------------------------------------------------------------------------
# Frozen vocabulary readback targets. These are the literal identifiers the
# ticket freezes; hard-coding them here is the point -- a rename in any one of
# the four surfaces must fail this module.
# --------------------------------------------------------------------------
SCHEMA_VERSION = 1

REPO_OK = "FlapPearLabs/agent-engineering-governance"
REPO_OTHER = "FlapPearLabs/zhihu-grabber-toolkit"

BASE_SHA = "1111111111111111111111111111111111111111"
CANDIDATE_SHA = "2222222222222222222222222222222222222222"
OTHER_SHA = "3333333333333333333333333333333333333333"

CHECK_STATUS = ("PASS", "FAIL", "SKIPPED", "ERROR", "UNKNOWN")
CI_STATUS = ("PASS", "FAIL", "NOT_TRIGGERED", "CANCELLED",
             "INFRASTRUCTURE_FAILURE", "KNOWN_BASELINE_FAILURE", "UNKNOWN")
AXIS_SETS = {
    "STRUCTURALLY_VALID": ("YES", "NO"),
    "SOURCE_VERIFICATION_STATE": ("VERIFIED", "INVALID",
                                  "TEMPORARILY_UNAVAILABLE", "NOT_VERIFIED"),
    "EVIDENCE_SUFFICIENCY": ("SUFFICIENT", "INSUFFICIENT"),
}
REUSE_DESCRIPTOR_KEYS = ("WHAT", "IDENTITY_VERSION_OR_DIGEST", "VALID_FOR",
                         "INVALIDATED_BY", "VERIFICATION_STATE")
REUSE_VERIFICATION_STATES = ("VERIFIED", "UNKNOWN")
AUTHORITY_FIELD_NAMES = ("semanticScopeStatus", "reviewerDecisionRefs")
GROUNDING_MODES = ("BASE_PLUS_DIFF", "LANE_INDEX", "UNAVAILABLE")

REUSE_DESCRIPTOR = {
    "WHAT": "shared schema:schemas/project-state.schema.json",
    "IDENTITY_VERSION_OR_DIGEST": "sha256:" + "1" * 64,
    "VALID_FOR": "the whole candidate range of this lane",
    "INVALIDATED_BY": "shared schema change / master drift",
    "VERIFICATION_STATE": "VERIFIED",
}

ERROR_CODES = ("EVIDENCE_VERSION_UNKNOWN", "EVIDENCE_SUBJECT_MISMATCH",
               "EVIDENCE_STALE_SUBJECT", "REJECT")

# A command reference that would leave a trace if anything ever ran it.
# `commandRef` is a REFERENCE, never an execution authority (REQ-W2-04(d)).
EXECUTION_CANARY = "sh -c 'touch REVIEW_EVIDENCE_COMMAND_REF_EXECUTED'"
EXECUTION_CANARY_MARKER = "REVIEW_EVIDENCE_COMMAND_REF_EXECUTED"

# Structural failure vocabulary the validator must expose, and the reasons that
# are NOT structural (declared error semantics). Read from the CLI so the two
# sides cannot drift.
STRUCTURAL_REASONS = {
    "PACK_ABSENT", "PACK_NOT_JSON", "PACK_NOT_AN_OBJECT",
    "UNKNOWN_SCHEMA_VERSION", "SCHEMA_INVALID", "SCHEMA_KEYWORD_UNSUPPORTED",
    "TYPE_MISMATCH", "CONST_VIOLATION", "ENUM_VIOLATION", "PATTERN_VIOLATION",
    "REQUIRED_FIELD_MISSING", "ADDITIONAL_PROPERTY_FORBIDDEN",
    "MIN_ITEMS_VIOLATION", "MIN_LENGTH_VIOLATION", "ONEOF_VIOLATION",
}

_MODULE_CACHE: dict = {}


def good_pack() -> dict:
    """A pack that the frozen contract must accept."""
    pack = {
        "schemaVersion": SCHEMA_VERSION,
        "subject": {
            "repo": REPO_OK,
            "baseSha": BASE_SHA,
            "candidateSha": CANDIDATE_SHA,
        },
        "authorityRefs": ["P1_AGENT_ENGINEERING_GOVERNANCE_DELTA_SPEC#REQ-W2-04"],
        "producer": {
            "identity": "laneB-worker",
            "version": "1",
            "observedAt": "2026-09-17T00:00:00Z",
        },
        "checks": [
            {
                "id": "governance-self-validation",
                "scope": "scripts/validate_governance.py",
                "commandRef": "references/review-evidence.md#cli-contract",
                "status": "PASS",
                "exitCode": 0,
                "artifactRefs": ["evidence/laneB/governance.txt"],
            }
        ],
        "artifacts": [
            {
                "location": "evidence/laneB/governance.txt",
                "contentDigest": "sha256:" + "0" * 64,
            }
        ],
        "ci": {
            "run": "1234567890",
            "job": "validate-governance",
            "checkedSha": CANDIDATE_SHA,
            "originalState": "PASS",
        },
        "grounding": {
            "mode": "UNAVAILABLE",
            "coverage": "CODEGRAPH_UNAVAILABLE",
            "evidenceRef": "references/codegraph-grounding.md#4",
        },
        "seams": {
            "applicability": "REQUIRED",
            "evidenceRefs": ["references/ticket-lane.md#3"],
        },
        "reuse": {
            "sourceEvidence": "the project-state schema contract referenced above",
            "validFor": "this lane candidate range only",
            "dependencies": [dict(REUSE_DESCRIPTOR)],
            "invalidation": "a shared schema change invalidates this reuse claim",
        },
        "unverified": [
            "ci.checkedSha was not independently re-verified by a second runner"
        ],
        "STRUCTURALLY_VALID": "YES",
        "SOURCE_VERIFICATION_STATE": "VERIFIED",
        "EVIDENCE_SUFFICIENCY": "SUFFICIENT",
        "semanticScopeStatus": None,
        "reviewerDecisionRefs": [],
    }
    return json.loads(json.dumps(pack))


class ReviewEvidenceContractTests(unittest.TestCase):
    """Counterexample-first contract tests for the Review Evidence interface."""

    # ---------------- subject acquisition (RED-safe) ----------------

    def require_cli(self):
        """Load scripts/review_evidence.py, or fail with CONTRACT_ABSENT."""
        if "cli" in _MODULE_CACHE:
            return _MODULE_CACHE["cli"]
        if not CLI_PATH.is_file():
            self.fail(
                "CONTRACT_ABSENT: scripts/review_evidence.py does not exist, so "
                "the Review Evidence machine contract cannot be exercised "
                "(expected RED condition of P1-T04 before implementation)")
        spec = importlib.util.spec_from_file_location("review_evidence", CLI_PATH)
        if spec is None or spec.loader is None:
            self.fail("CONTRACT_ABSENT: scripts/review_evidence.py is not "
                      "loadable as a module")
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            self.fail("CONTRACT_BROKEN: scripts/review_evidence.py raised while "
                      f"loading: {type(exc).__name__}: {exc}")
        for name in ("schema_violations", "validate_pack", "collect_skeleton",
                     "load_contract", "main", "SUPPORTED_SCHEMA_KEYWORDS",
                     "STRUCTURAL_REASONS", "NON_STRUCTURAL_REASONS"):
            if not hasattr(module, name):
                self.fail("CONTRACT_BROKEN: scripts/review_evidence.py does not "
                          f"expose the declared entry point {name!r}")
        _MODULE_CACHE["cli"] = module
        return module

    def require_schema(self) -> dict:
        if not SCHEMA_PATH.is_file():
            self.fail(
                f"CONTRACT_ABSENT: {SCHEMA_PATH.relative_to(ROOT)} does not "
                "exist, so the versioned machine contract cannot be exercised "
                "(expected RED condition of P1-T04 before implementation)")
        try:
            return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            self.fail(f"CONTRACT_BROKEN: the schema is not valid JSON: {exc}")

    def require_template(self) -> dict:
        if not TEMPLATE_PATH.is_file():
            self.fail(
                f"CONTRACT_ABSENT: {TEMPLATE_PATH.relative_to(ROOT)} does not "
                "exist (expected RED condition of P1-T04 before implementation)")
        try:
            return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            self.fail(f"CONTRACT_BROKEN: the template is not valid JSON: {exc}")

    def require_reference(self) -> str:
        if not REFERENCE_PATH.is_file():
            self.fail(
                f"CONTRACT_ABSENT: {REFERENCE_PATH.relative_to(ROOT)} does not "
                "exist, so the interface has no single semantic owner "
                "(expected RED condition of P1-T04 before implementation)")
        return REFERENCE_PATH.read_text(encoding="utf-8")

    # ---------------- helpers ----------------

    def schema_of(self, schema: dict, pointer: str):
        node = schema
        for part in pointer.strip("/").split("/"):
            node = node["$defs"][part] if part in node.get("$defs", {}) else node[part]
        return node

    def codes(self, result: dict) -> set:
        return {violation["code"] for violation in result["violations"]}

    def reasons(self, result: dict) -> set:
        return {violation["reason"] for violation in result["violations"]}

    def axis_readback_violations(self, schema: dict):
        """The three axes must be exactly the frozen closed sets, and disjoint."""
        problems = []
        for axis, members in AXIS_SETS.items():
            try:
                declared = self.schema_of(schema, f"properties/{axis}")["enum"]
            except (KeyError, TypeError):
                problems.append(f"{axis}: not declared as an enum")
                continue
            if set(declared) != set(members):
                problems.append(
                    f"{axis}: declared={sorted(declared)} expected={sorted(members)}")
            if len(declared) != len(set(declared)):
                problems.append(f"{axis}: duplicate members (aliasing)")
        declared = {axis: set(self.schema_of(schema, f"properties/{axis}")["enum"])
                    for axis in AXIS_SETS
                    if self.schema_of(schema, f"properties/{axis}").get("enum")}
        names = sorted(declared)
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                if declared[names[i]] & declared[names[j]]:
                    problems.append(
                        f"{names[i]} and {names[j]} share a value domain "
                        "(axis collapse)")
        return problems

    def write_pack(self, directory: Path, pack: dict, name="pack.json") -> Path:
        path = directory / name
        path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
        return path

    def run_cli(self, args, cwd=None):
        return subprocess.run(
            [sys.executable, str(CLI_PATH), *args],
            capture_output=True, text=True, cwd=cwd, check=False)

    def parse_stdout(self, completed):
        try:
            return json.loads(completed.stdout)
        except Exception as exc:  # noqa: BLE001
            self.fail("CLI_STRUCTURED_OUTPUT_ABSENT: stdout is not JSON "
                      f"({exc}); stdout={completed.stdout[:400]!r} "
                      f"stderr={completed.stderr[:400]!r}")

    def validate(self, pack: dict, expect_repo=REPO_OK, expect_base_sha=BASE_SHA,
                 expect_candidate_sha=CANDIDATE_SHA) -> dict:
        return self.require_cli().validate_pack(
            pack, schema=self.require_schema(), expect_repo=expect_repo,
            expect_base_sha=expect_base_sha,
            expect_candidate_sha=expect_candidate_sha)

    # --- declaration scan implementation -----------------------------------

    TEXT_SUFFIXES = {".md", ".json", ".py", ".yml", ".yaml", ".txt", ".cfg",
                     ".toml"}
    EXCLUDED_DIRS = {".git", "__pycache__", ".agent"}
    # Test surfaces assert on the declared tokens; they do not declare them.
    # Both discovery roots are excluded explicitly, never silently -- see
    # SELF_REVIEW.md DECLARATION_POINT_PROOF.
    TEST_SURFACE_PREFIXES = ("scripts/tests/", "adapters/zcode/tests/")

    def iter_canonical_text_files(self, root: Path):
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if any(part in self.EXCLUDED_DIRS for part in path.parts):
                continue
            if path.suffix not in self.TEXT_SUFFIXES:
                continue
            relative = path.relative_to(root).as_posix()
            if relative.startswith(self.TEST_SURFACE_PREFIXES):
                continue
            yield relative, path

    def scan_token(self, token, root: Path | None = None):
        root = root or ROOT
        hits = set()
        for relative, path in self.iter_canonical_text_files(root):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if token in text:
                hits.add(relative)
        return hits

    def scan_family(self, tokens, root: Path | None = None):
        """A family is re-declared only by naming every one of its members."""
        root = root or ROOT
        hits = set()
        for relative, path in self.iter_canonical_text_files(root):
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if all(token in text for token in tokens):
                hits.add(relative)
        return hits

    # ==================================================================
    # Surface presence and single ownership
    # ==================================================================

    def test_01_four_surfaces_exist(self):
        missing = [str(p.relative_to(ROOT)) for p in
                   (REFERENCE_PATH, SCHEMA_PATH, TEMPLATE_PATH, CLI_PATH)
                   if not p.is_file()]
        self.assertEqual(
            [], missing,
            "CONTRACT_ABSENT: the four coordinated surfaces are incomplete; "
            f"missing={missing}")

    def test_02_reference_declares_canonical_owner_literal(self):
        text = self.require_reference()
        self.assertIn(
            "Canonical owner", text,
            "VALIDATOR_INVARIANT_VIOLATED: references-declare-canonical-owner "
            "requires the literal 'Canonical owner' in every references/*.md")

    def test_03_reference_is_the_declared_semantic_owner(self):
        text = self.require_reference()
        for marker in ("review-evidence.schema.json", "review-evidence.json",
                       "review_evidence.py"):
            self.assertIn(marker, text,
                          "SURFACE_DISAGREEMENT: the semantic owner does not "
                          f"name its mechanical form {marker!r}")

    # --- declaration-point expectation table --------------------------------
    # The four coordinated surfaces ARE ONE interface: the single semantic
    # owner plus its mechanical forms (schema / template / CLI). A declaration
    # point OUTSIDE this set is a competing declaration of the interface
    # (CE-28) and must be rejected / converged onto the single owner.
    HEAD = frozenset({
        "references/review-evidence.md",
        "schemas/review-evidence.schema.json",
        "templates/review-evidence.json",
    })
    WITH_CLI = HEAD | {"scripts/review_evidence.py"}

    # Token -> the interface surfaces that may mention it, and no others. The
    # CLI appears only where it must name a declared field in order to emit a
    # schema-conforming skeleton; it enumerates no value domain (asserted by
    # test_06).
    PROTECTED_TOKENS = {
        "IDENTITY_VERSION_OR_DIGEST": HEAD,
        "semanticScopeStatus": WITH_CLI,
        "reviewerDecisionRefs": WITH_CLI,
        "STRUCTURALLY_VALID": WITH_CLI,
        "SOURCE_VERIFICATION_STATE": WITH_CLI,
        "EVIDENCE_SUFFICIENCY": WITH_CLI,
    }

    # Distinctive name sets: a file re-declares a family only by naming every
    # one of its members. Short generic enum members (YES / NO / VERIFIED /
    # UNKNOWN) are deliberately excluded here -- they are ordinary words in
    # prose and cannot carry a declaration-point claim.
    PROTECTED_FAMILIES = {
        "three-axis field names": (
            ("STRUCTURALLY_VALID", "SOURCE_VERIFICATION_STATE",
             "EVIDENCE_SUFFICIENCY"), WITH_CLI),
        "reuse dependency descriptor": (REUSE_DESCRIPTOR_KEYS, HEAD),
        "authority-separation field names": (AUTHORITY_FIELD_NAMES, WITH_CLI),
    }

    def test_04_single_declaration_point_repo_wide(self):
        """CE-28: no competing owner mentions a declared name."""
        for token, expected in self.PROTECTED_TOKENS.items():
            found = self.scan_token(token)
            self.assertEqual(
                set(expected), found,
                f"DUAL_DECLARATION (CE-28): {token!r} must be declared only by "
                f"the Review Evidence interface; unexpected={sorted(found - set(expected))} "
                f"missing={sorted(set(expected) - found)}")

    def test_05_single_declaration_point_families(self):
        """CE-28: a competing owner is a file that names a whole family."""
        for family, (tokens, expected) in self.PROTECTED_FAMILIES.items():
            found = self.scan_family(tokens)
            self.assertTrue(found, f"DUAL_DECLARATION scan is vacuous for {family}")
            self.assertEqual(
                set(expected), found,
                f"DUAL_DECLARATION (CE-28): the {family} contract is declared "
                f"outside the single interface; unexpected="
                f"{sorted(found - set(expected))}")

    def test_06_the_cli_consumes_the_contract_without_redeclaring_it(self):
        """A consumer names fields; it does not enumerate a closed set."""
        cli_source = CLI_PATH.read_text(encoding="utf-8")
        assert_path = SCHEMA_PATH.read_text(encoding="utf-8")
        for axis, members in AXIS_SETS.items():
            quoted_absent = [m for m in members
                             if f'"{m}"' not in cli_source]
            self.assertTrue(
                quoted_absent,
                f"RE_DECLARATION: scripts/review_evidence.py must not enumerate "
                f"the {axis} closed set, yet every member appears as a literal")
        for surface, text in (("schema", assert_path), ("CLI", cli_source)):
            self.assertIn(
                "references/review-evidence.md", text,
                f"SINGLE_OWNER: the {surface} must point at the sole semantic "
                "owner instead of restating it")

    def test_06b_dual_declaration_is_detectable(self):
        """CE-28 negative control: an injected competing owner IS detected."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "references").mkdir(parents=True)
            (root / "scripts" / "tests").mkdir(parents=True)
            body = "\n".join(REUSE_DESCRIPTOR_KEYS + AUTHORITY_FIELD_NAMES
                             + tuple(AXIS_SETS))
            (root / "references/competing-review-evidence.md").write_text(
                "# competing declaration\n" + body + "\n", encoding="utf-8")
            (root / "scripts/tests/test_probe.py").write_text(body, encoding="utf-8")
            self.assertIn(
                "references/competing-review-evidence.md",
                self.scan_family(REUSE_DESCRIPTOR_KEYS, root=root),
                "DUAL_DECLARATION_SCAN_VACUOUS: an injected competing canonical "
                "owner went undetected")
            self.assertIn(
                "references/competing-review-evidence.md",
                self.scan_token("semanticScopeStatus", root=root),
                "DUAL_DECLARATION_SCAN_VACUOUS: the token scan missed an "
                "injected competing owner")
            self.assertNotIn(
                "scripts/tests/test_probe.py",
                self.scan_family(REUSE_DESCRIPTOR_KEYS, root=root),
                "the declared test-surface exclusion must hold")

    # ==================================================================
    # The three orthogonal axes
    # ==================================================================

    def test_07_three_axes_are_three_distinct_closed_sets(self):
        problems = self.axis_readback_violations(self.require_schema())
        self.assertEqual([], problems,
                         "AXIS_DRIFT/AXIS_COLLAPSE: " + "; ".join(problems))

    def test_08_insufficient_is_not_a_source_axis_value(self):
        pack = good_pack()
        pack["SOURCE_VERIFICATION_STATE"] = "INSUFFICIENT"
        result = self.validate(pack)
        self.assertFalse(result["ok"], "AXIS_COLLAPSE: INSUFFICIENT belongs to "
                                       "EVIDENCE_SUFFICIENCY only")
        self.assertIn("REJECT", self.codes(result))
        self.assertIn("ENUM_VIOLATION", self.reasons(result))
        self.assertTrue(
            self.require_cli().schema_violations(pack, schema=self.require_schema()),
            "AC-10: the schema must dispose of this sample the same way as the "
            "validator")

    def test_09_source_verified_with_insufficient_evidence_is_accepted(self):
        """Positive control: the two axes are independent, so the pair is legal."""
        pack = good_pack()
        pack["SOURCE_VERIFICATION_STATE"] = "VERIFIED"
        pack["EVIDENCE_SUFFICIENCY"] = "INSUFFICIENT"
        result = self.validate(pack)
        self.assertTrue(
            result["ok"],
            "AXIS_COLLAPSE: VERIFIED + INSUFFICIENT is the frozen legal pair of "
            "two independent axes; violations=" + repr(result["violations"]))

    def test_10_temporarily_unavailable_is_a_distinct_declared_state(self):
        """unreachable != invalidated: the state must exist, distinctly."""
        schema = self.require_schema()
        states = list(self.schema_of(
            schema, "properties/SOURCE_VERIFICATION_STATE")["enum"])
        self.assertIn("TEMPORARILY_UNAVAILABLE", states)
        self.assertIn("INVALID", states)
        self.assertEqual(len(states), len(set(states)),
                         "STATE_ALIAS: the members must be distinct")
        pack = good_pack()
        pack["SOURCE_VERIFICATION_STATE"] = "TEMPORARILY_UNAVAILABLE"
        pack["EVIDENCE_SUFFICIENCY"] = "INSUFFICIENT"
        self.assertTrue(
            self.validate(pack)["ok"],
            "an unreachable source must be representable as its own state "
            "rather than folded into INVALID")

    def test_11_folding_temporarily_unavailable_into_invalid_is_rejected(self):
        """Mutation counterexample: a contract that folds the state is rejected."""
        schema = self.require_schema()
        self.assertEqual([], self.axis_readback_violations(schema),
                         "the readback must accept the landed contract first")
        folded = json.loads(json.dumps(schema))
        source = folded["properties"]["SOURCE_VERIFICATION_STATE"]
        source["enum"] = [value for value in source["enum"]
                          if value != "TEMPORARILY_UNAVAILABLE"]
        problems = self.axis_readback_violations(folded)
        self.assertTrue(
            problems,
            "FOLD_NOT_REJECTED: recording the temporary-unavailability state as "
            "INVALID (by folding the state away) must be detectably rejected")
        aliased = json.loads(json.dumps(schema))
        aliased["properties"]["SOURCE_VERIFICATION_STATE"]["enum"] = [
            "VERIFIED", "INVALID", "INVALID", "NOT_VERIFIED"]
        self.assertTrue(self.axis_readback_violations(aliased),
                        "an aliased/shortened source axis must be rejected")

    # ==================================================================
    # CHECK_STATUS vs CI_STATUS
    # ==================================================================

    def test_12_check_status_and_ci_status_are_two_machines(self):
        schema = self.require_schema()
        checks = set(self.schema_of(
            schema, "properties/checks/items/properties/status")["enum"])
        ci = set(self.schema_of(
            schema, "properties/ci/properties/originalState")["enum"])
        self.assertEqual(set(CHECK_STATUS), checks)
        self.assertEqual(set(CI_STATUS), ci)
        self.assertNotEqual(
            checks, ci,
            "CE-24: checks[].status must not be a second competing CI machine")
        self.assertFalse(checks <= ci,
                         "CHECK_STATUS must not be a subset of CI_STATUS")
        self.assertFalse(ci <= checks,
                         "CI_STATUS must not be a subset of CHECK_STATUS")

    def test_13_check_status_outside_closed_set_is_rejected(self):
        for bogus in ("GREEN", "OK", "SUCCESS"):
            with self.subTest(status=bogus):
                pack = good_pack()
                pack["checks"][0]["status"] = bogus
                result = self.validate(pack)
                self.assertFalse(result["ok"], f"{bogus!r} is not a CHECK_STATUS")
                self.assertIn("REJECT", self.codes(result))

    def test_14_ci_status_outside_seven_value_set_is_rejected(self):
        for bogus in ("SKIPPED", "ERROR", "SUCCESS", "GREEN"):
            with self.subTest(originalState=bogus):
                pack = good_pack()
                pack["ci"]["originalState"] = bogus
                self.assertFalse(
                    self.validate(pack)["ok"],
                    f"{bogus!r} is neither CHECK_STATUS-as-CI_STATUS nor a "
                    "member of the existing seven-value CI_STATUS set")

    def test_15_ci_status_seven_value_set_is_adopted_not_replaced(self):
        """CE-30: the set is read from the canonical file, not restated."""
        schema = self.require_schema()
        self.assertTrue(CI_REFERENCE_PATH.is_file())
        canonical = CI_REFERENCE_PATH.read_text(encoding="utf-8")
        lines = [line for line in canonical.splitlines()
                 if "不可坍缩" in line and "NOT_TRIGGERED" in line]
        self.assertEqual(1, len(lines),
                         "the canonical CI status set line must exist exactly once")
        canonical_set = set(re.findall(r"[A-Z][A-Z_]{2,}", lines[0]))
        self.assertEqual(
            set(CI_STATUS), canonical_set,
            "the readback of the canonical existing CI_STATUS set disagrees with "
            "the frozen seven values")
        declared = list(self.schema_of(
            schema, "properties/ci/properties/originalState")["enum"])
        self.assertEqual(
            sorted(canonical_set), sorted(declared),
            "CE-30: the review-evidence contract must adopt the existing "
            "seven-value CI_STATUS set unchanged -- neither replaced nor extended")
        for relative, path in self.iter_canonical_text_files(ROOT):
            if not relative.endswith(".json") or path == SCHEMA_PATH:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            self.assertNotIn(
                "KNOWN_BASELINE_FAILURE", text,
                f"CE-24: {relative} looks like a second CI status machine")

    # ==================================================================
    # unverified[] and seams.applicability
    # ==================================================================

    def test_16_unverified_omission_is_structurally_invalid(self):
        pack = good_pack()
        del pack["unverified"]
        result = self.validate(pack)
        self.assertFalse(
            result["ok"],
            "UNVERIFIED_OMITTED: omission is structurally invalid; an explicit "
            "empty array is the legal statement of 'nothing unverified'")
        self.assertIn("REQUIRED_FIELD_MISSING", self.reasons(result))
        self.assertIn("REJECT", self.codes(result))

    def test_17_unverified_empty_array_is_legal(self):
        pack = good_pack()
        pack["unverified"] = []
        result = self.validate(pack)
        self.assertTrue(result["ok"],
                        "an explicit empty unverified[] is legal; violations="
                        + repr(result["violations"]))

    def test_18_seams_applicability_mirrors_reachability_applicability(self):
        """AC-42: REQUIRED | N/A; N/A needs a reason plus an acceptance reference."""
        schema = self.require_schema()
        branches = self.schema_of(schema, "properties/seams")["oneOf"]
        declared = {branch["properties"]["applicability"]["const"]
                    for branch in branches}
        self.assertEqual({"REQUIRED", "N/A"}, declared)

        legal = good_pack()
        legal["seams"] = {"applicability": "N/A", "evidenceRefs": [],
                          "reason": "docs-only ticket: no runtime seam exists",
                          "acceptanceRef": "issue-11-comment-1"}
        self.assertTrue(
            self.validate(legal)["ok"],
            "seams.applicability = N/A with a reason plus an acceptance "
            "reference is legal")

        for dropped in ("reason", "acceptanceRef"):
            with self.subTest(dropped=dropped):
                pack = json.loads(json.dumps(legal))
                del pack["seams"][dropped]
                result = self.validate(pack)
                self.assertFalse(result["ok"],
                                 f"applicability = N/A without {dropped} must be "
                                 "rejected")
                self.assertIn("REJECT", self.codes(result))

        bare = good_pack()
        bare["seams"] = {"applicability": "N/A", "evidenceRefs": []}
        self.assertFalse(self.validate(bare)["ok"])

        bogus = good_pack()
        bogus["seams"] = {"applicability": "MAYBE", "evidenceRefs": []}
        self.assertFalse(self.validate(bogus)["ok"])

    # ==================================================================
    # reuse descriptor
    # ==================================================================

    def test_19_reuse_descriptor_shape_is_frozen(self):
        schema = self.require_schema()
        node = self.schema_of(schema, "properties/reuse/properties/dependencies")
        self.assertEqual("array", node["type"])
        item = node["items"]
        ref = item.get("$ref", "")
        self.assertTrue(ref.startswith("#/$defs/"),
                        "the descriptor must be a declared, referenced structure")
        item = self.schema_of(schema, ref[len("#/$defs/"):])
        self.assertEqual(set(REUSE_DESCRIPTOR_KEYS), set(item["required"]),
                         "REQ-W2-04(e): the descriptor is a closed structure")
        self.assertEqual(False, item["additionalProperties"])
        self.assertEqual(
            set(REUSE_VERIFICATION_STATES),
            set(item["properties"]["VERIFICATION_STATE"]["enum"]),
            "VERIFICATION_STATE = VERIFIED | UNKNOWN exactly")
        self.assertEqual(
            set(AXIS_SETS["SOURCE_VERIFICATION_STATE"]),
            set(self.schema_of(
                schema, "properties/SOURCE_VERIFICATION_STATE")["enum"]),
            "the source axis is declared independently of the descriptor state")

    def test_20_free_text_reuse_descriptor_is_rejected(self):
        for shape in ("whole-group", "element"):
            with self.subTest(shape=shape):
                pack = good_pack()
                if shape == "whole-group":
                    pack["reuse"]["dependencies"] = "the project-state schema"
                else:
                    pack["reuse"]["dependencies"] = ["the project-state schema"]
                result = self.validate(pack)
                self.assertFalse(
                    result["ok"],
                    "FREE_TEXT_DESCRIPTOR: the descriptor must be the declared "
                    "closed structure, not free text")
                self.assertIn("REJECT", self.codes(result))

    def test_21_incomplete_or_invalid_reuse_descriptor_is_rejected(self):
        for missing in REUSE_DESCRIPTOR_KEYS:
            with self.subTest(missing=missing):
                pack = good_pack()
                del pack["reuse"]["dependencies"][0][missing]
                self.assertFalse(self.validate(pack)["ok"],
                                 f"the descriptor must require {missing}")
        for bogus in ("MAYBE", "INSUFFICIENT", "NOT_VERIFIED"):
            with self.subTest(verification_state=bogus):
                pack = good_pack()
                pack["reuse"]["dependencies"][0]["VERIFICATION_STATE"] = bogus
                result = self.validate(pack)
                self.assertFalse(result["ok"],
                                 f"{bogus!r} is not a descriptor VERIFICATION_STATE")
                self.assertIn("REJECT", self.codes(result))

    # ==================================================================
    # Error semantics: version, subject, declared structural axis
    # ==================================================================

    def test_22_unknown_schema_version_is_rejected_without_migration_guess(self):
        for bogus in (2, 99, "1", None):
            with self.subTest(schema_version=bogus):
                pack = good_pack()
                pack["schemaVersion"] = bogus
                result = self.validate(pack)
                self.assertFalse(result["ok"])
                self.assertEqual(
                    {"EVIDENCE_VERSION_UNKNOWN"}, self.codes(result),
                    "an unknown schemaVersion must be its own distinguishable "
                    "code; no speculative migration may be guessed")

    def test_23_wrong_repository_is_rejected(self):
        pack = good_pack()
        pack["subject"]["repo"] = REPO_OTHER
        result = self.validate(pack)
        self.assertFalse(result["ok"])
        self.assertEqual({"EVIDENCE_SUBJECT_MISMATCH"}, self.codes(result))

    def test_24_wrong_base_sha_and_wrong_candidate_sha_are_rejected(self):
        """CE-06: a stale subject must not be submittable."""
        pack = good_pack()
        pack["subject"]["baseSha"] = OTHER_SHA
        result = self.validate(pack)
        self.assertFalse(result["ok"])
        self.assertEqual({"EVIDENCE_STALE_SUBJECT"}, self.codes(result))

        pack = good_pack()
        pack["subject"]["candidateSha"] = OTHER_SHA
        result = self.validate(pack)
        self.assertEqual(
            {"EVIDENCE_STALE_SUBJECT"}, self.codes(result),
            "a pack declaring a candidate SHA other than the candidate under "
            "review must be rejected as a stale subject")

    def test_25_missing_required_result_field_is_rejected(self):
        cases = (
            ("checks[].exitCode", lambda p: p["checks"][0].pop("exitCode")),
            ("ci.checkedSha", lambda p: p["ci"].pop("checkedSha")),
            ("ci.originalState", lambda p: p["ci"].pop("originalState")),
            ("producer.observedAt", lambda p: p["producer"].pop("observedAt")),
            ("artifacts[].contentDigest",
             lambda p: p["artifacts"][0].pop("contentDigest")),
            ("grounding.mode", lambda p: p["grounding"].pop("mode")),
            ("STRUCTURALLY_VALID", lambda p: p.pop("STRUCTURALLY_VALID")),
            ("SOURCE_VERIFICATION_STATE",
             lambda p: p.pop("SOURCE_VERIFICATION_STATE")),
            ("EVIDENCE_SUFFICIENCY", lambda p: p.pop("EVIDENCE_SUFFICIENCY")),
            ("reviewerDecisionRefs", lambda p: p.pop("reviewerDecisionRefs")),
        )
        for label, mutate in cases:
            with self.subTest(field=label):
                pack = good_pack()
                mutate(pack)
                result = self.validate(pack)
                self.assertFalse(result["ok"], f"missing {label} must be rejected")
                self.assertIn("REJECT", self.codes(result))
                self.assertIn("REQUIRED_FIELD_MISSING", self.reasons(result))

    def test_26_unparseable_subject_sha_is_rejected(self):
        for field in ("baseSha", "candidateSha"):
            with self.subTest(field=field):
                pack = good_pack()
                pack["subject"][field] = "soon"
                result = self.validate(pack)
                self.assertFalse(result["ok"])
                self.assertIn("REJECT", self.codes(result))

    def test_27_declared_structurally_invalid_pack_is_rejected(self):
        pack = good_pack()
        pack["STRUCTURALLY_VALID"] = "NO"
        result = self.validate(pack)
        self.assertFalse(result["ok"],
                         "STRUCTURALLY_VALID = NO does not enter consumption")
        self.assertEqual({"REJECT"}, self.codes(result))

    # ==================================================================
    # Template conformance (placeholder form, RULES.md R2)
    # ==================================================================

    def test_28_committed_template_conforms_to_the_schema(self):
        template = self.require_template()
        cli = self.require_cli()
        schema = self.require_schema()
        violations = cli.schema_violations(template, schema=schema,
                                           allow_placeholders=True)
        self.assertEqual([], violations,
                         "TEMPLATE_NONCONFORMANT: the committed template must "
                         f"conform to the schema; violations={violations}")
        self.assertGreaterEqual(json.dumps(template).count("${"), 5,
                               "RULES.md R2: the template must stay "
                               "placeholder-form")
        self.assertIn("unverified", template,
                      "the template must carry unverified[] explicitly")
        self.assertIn("schemaVersion", template)

    def test_29_template_divergence_is_detectable(self):
        cli = self.require_cli()
        schema = self.require_schema()
        mutations = {
            "enum-outside-set": lambda t: t["ci"].__setitem__(
                "originalState", "BROKEN"),
            "illegal-axis-value": lambda t: t.__setitem__(
                "EVIDENCE_SUFFICIENCY", "VERIFIED"),
            "unverified-dropped": lambda t: t.pop("unverified"),
            "unknown-field": lambda t: t.__setitem__("unexpectedField", "x"),
            "descriptor-as-free-text": lambda t: t["reuse"].__setitem__(
                "dependencies", "${REUSE_DEPENDENCIES}"),
            "enum-field-as-placeholder": lambda t: t["ci"].__setitem__(
                "originalState", "${CI_ORIGINAL_STATE}"),
        }
        for label, mutate in mutations.items():
            with self.subTest(mutation=label):
                template = json.loads(json.dumps(self.require_template()))
                mutate(template)
                violations = cli.schema_violations(template, schema=schema,
                                                   allow_placeholders=True)
                self.assertTrue(
                    violations,
                    f"SCHEMA_TEMPLATE_DISAGREEMENT: mutation {label!r} must be "
                    "detectably rejected")

    # ==================================================================
    # CLI surface: exit codes, structured output, trust boundary
    # ==================================================================

    def test_30_cli_accepts_the_committed_template(self):
        self.require_cli()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_pack(Path(temp), self.require_template(),
                                   name="template.json")
            completed = self.run_cli(["validate", "--pack", str(path),
                                      "--allow-placeholders"])
            payload = self.parse_stdout(completed)
            self.assertEqual(0, completed.returncode,
                             f"expected PASS; stdout={completed.stdout[:600]}")
            self.assertTrue(payload["ok"])
            self.assertEqual(0, payload["exitCode"])
            self.assertEqual([], payload["violations"])
            self.assertEqual("review_evidence", payload["tool"])
            self.assertEqual("validate", payload["mode"])

    def test_31_cli_rejects_a_candidate_subject_pack(self):
        self.require_cli()
        cases = (
            ("repo", "subject.repo", REPO_OTHER, "EVIDENCE_SUBJECT_MISMATCH"),
            ("baseSha", "subject.baseSha", OTHER_SHA, "EVIDENCE_STALE_SUBJECT"),
            ("candidateSha", "subject.candidateSha", OTHER_SHA,
             "EVIDENCE_STALE_SUBJECT"),
        )
        with tempfile.TemporaryDirectory() as temp:
            for label, dotted, value, expected in cases:
                with self.subTest(subject=label):
                    pack = good_pack()
                    section, key = dotted.split(".")
                    pack[section][key] = value
                    path = self.write_pack(Path(temp), pack, name=f"{label}.json")
                    completed = self.run_cli([
                        "validate", "--pack", str(path),
                        "--expect-repo", REPO_OK,
                        "--expect-base-sha", BASE_SHA,
                        "--expect-candidate-sha", CANDIDATE_SHA,
                    ])
                    payload = self.parse_stdout(completed)
                    self.assertEqual(1, completed.returncode)
                    self.assertFalse(payload["ok"])
                    self.assertEqual(1, payload["exitCode"])
                    self.assertEqual(
                        [expected],
                        sorted({v["code"] for v in payload["violations"]}))

    def test_32_cli_accepts_a_conformant_pack(self):
        self.require_cli()
        with tempfile.TemporaryDirectory() as temp:
            path = self.write_pack(Path(temp), good_pack())
            completed = self.run_cli([
                "validate", "--pack", str(path),
                "--expect-repo", REPO_OK,
                "--expect-base-sha", BASE_SHA,
                "--expect-candidate-sha", CANDIDATE_SHA,
            ])
            payload = self.parse_stdout(completed)
            self.assertEqual(0, completed.returncode,
                             f"stdout={completed.stdout[:600]}")
            self.assertEqual([], payload["violations"])

    def test_33_cli_never_executes_command_ref(self):
        self.require_cli()
        pack = good_pack()
        pack["checks"][0]["commandRef"] = EXECUTION_CANARY
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            path = self.write_pack(workdir, pack)
            completed = self.run_cli(["validate", "--pack", str(path)],
                                     cwd=str(workdir))
            self.assertTrue(completed.stdout)
            self.assertFalse(
                (workdir / EXECUTION_CANARY_MARKER).exists(),
                "commandRef is a REFERENCE, never an execution authority")
        source = CLI_PATH.read_text(encoding="utf-8")
        for forbidden in ("subprocess", "os.system", "os.exec", "eval(",
                          "exec(", "urllib", "socket", "http.client",
                          "ftplib", "shutil.rmtree", "glob("):
            self.assertNotIn(
                forbidden, source,
                f"TRUST_BOUNDARY: the CLI must not carry {forbidden!r} (no "
                "execution, no network fetch, no recursive discovery)")

    def test_34_cli_reports_a_structured_failure_shape(self):
        self.require_cli()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing.json"
            completed = self.run_cli(["validate", "--pack", str(path)])
            payload = self.parse_stdout(completed)
            self.assertEqual(1, completed.returncode)
            self.assertFalse(payload["ok"])
            for key in ("tool", "mode", "ok", "exitCode", "contract",
                        "violations"):
                self.assertIn(key, payload)
            self.assertEqual("schemas/review-evidence.schema.json",
                             payload["contract"]["schemaPath"])
            self.assertEqual([SCHEMA_VERSION],
                             payload["contract"]["supportedSchemaVersions"])
            self.assertEqual(sorted(ERROR_CODES),
                             sorted(payload["contract"]["errorCodes"]))
            self.assertEqual("REJECT",
                             {v["code"] for v in payload["violations"]}.pop())

    # ==================================================================
    # collect: thin and non-authoritative
    # ==================================================================

    def test_35_collect_emits_a_conforming_non_authoritative_skeleton(self):
        cli = self.require_cli()
        schema = self.require_schema()
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            out = workdir / "skeleton.json"
            completed = self.run_cli([
                "collect", "--out", str(out),
                "--repo", REPO_OK, "--base-sha", BASE_SHA,
                "--candidate-sha", CANDIDATE_SHA,
                "--producer-identity", "laneB-worker",
                "--producer-version", "1",
                "--observed-at", "2026-09-17T00:00:00Z",
            ], cwd=str(workdir))
            payload = self.parse_stdout(completed)
            self.assertEqual(0, completed.returncode,
                             f"stdout={completed.stdout[:800]} "
                             f"stderr={completed.stderr[:800]}")
            self.assertEqual("collect", payload["mode"])
            skeleton = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(
                [], cli.schema_violations(skeleton, schema=schema),
                "collect must emit a schema-conforming skeleton")
            self.assertIsNone(skeleton["semanticScopeStatus"],
                              "collect must never populate reviewer authority")
            self.assertEqual([], skeleton["reviewerDecisionRefs"])
            self.assertTrue(skeleton["unverified"],
                            "a freshly collected skeleton has unverified items")
            self.assertEqual([], skeleton["checks"])
            self.assertEqual([], skeleton["artifacts"])
            self.assertNotEqual("PASS", skeleton["ci"]["originalState"])
            self.assertNotEqual("VERIFIED", skeleton["SOURCE_VERIFICATION_STATE"])
            self.assertNotEqual("SUFFICIENT", skeleton["EVIDENCE_SUFFICIENCY"])

    def test_36_collect_writes_only_to_the_explicit_output_path(self):
        self.require_cli()
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            before = {p.relative_to(workdir).as_posix()
                      for p in workdir.rglob("*")}
            out = workdir / "skeleton.json"
            completed = self.run_cli([
                "collect", "--out", str(out),
                "--repo", REPO_OK, "--base-sha", BASE_SHA,
                "--candidate-sha", CANDIDATE_SHA,
                "--producer-identity", "laneB-worker",
                "--producer-version", "1",
                "--observed-at", "2026-09-17T00:00:00Z",
            ], cwd=str(workdir))
            after = {p.relative_to(workdir).as_posix()
                     for p in workdir.rglob("*")}
            self.assertEqual(0, completed.returncode)
            self.assertEqual({"skeleton.json"}, after - before,
                             "no writes outside an explicitly-passed output path")

    def test_37_reference_declares_scope_boundaries_and_exit_code_contract(self):
        """The declaration/behaviour boundary and the exit-code contract are
        declared once, in the semantic owner."""
        text = self.require_reference()
        for marker in ("P1-T05", "P1-T06", "P1-T07", "P1-T08", "P1-T16"):
            self.assertIn(marker, text,
                          f"SCOPE_LEAK: {marker} ownership must be stated as a "
                          "boundary, not implemented")
        self.assertIn("commandRef", text,
                      "the owner must declare commandRef as a reference only")
        lowered = text.lower()
        self.assertIn("never an execution authority", lowered)
        self.assertIn("self-approv", lowered,
                      "the owner must state the no-self-approval boundary")
        self.assertIn("exit status", lowered,
                      "the exit-code contract is declared here, once")
        self.assertIn("0", text)

    # ==================================================================
    # AC-10: shared sample disposition table
    # ==================================================================

    def samples(self):
        """(name, pack, schema_verdict, validator_ok, expected codes)."""
        rows = []

        def add(name, pack, schema_verdict, ok, codes):
            rows.append((name, pack, schema_verdict, ok, set(codes)))

        add("P1 conformant pack", good_pack(), "ACCEPT", True, ())
        pack = good_pack(); pack["subject"]["repo"] = REPO_OTHER
        add("N1 wrong repository", pack, "ACCEPT", False,
            {"EVIDENCE_SUBJECT_MISMATCH"})
        pack = good_pack(); pack["subject"]["baseSha"] = OTHER_SHA
        add("N2 wrong base SHA", pack, "ACCEPT", False, {"EVIDENCE_STALE_SUBJECT"})
        pack = good_pack(); pack["subject"]["candidateSha"] = OTHER_SHA
        add("N3 wrong candidate SHA", pack, "ACCEPT", False,
            {"EVIDENCE_STALE_SUBJECT"})
        pack = good_pack(); pack["schemaVersion"] = 2
        add("N4 unknown schemaVersion", pack, "REJECT", False,
            {"EVIDENCE_VERSION_UNKNOWN"})
        pack = good_pack(); pack["checks"][0].pop("exitCode")
        add("N5 missing required result field", pack, "REJECT", False, {"REJECT"})
        pack = good_pack(); pack["checks"][0]["status"] = "GREEN"
        add("N6 CHECK_STATUS outside closed set", pack, "REJECT", False, {"REJECT"})
        pack = good_pack(); pack["checks"][0]["status"] = "NOT_TRIGGERED"
        add("N7 CI_STATUS used as CHECK_STATUS", pack, "REJECT", False, {"REJECT"})
        pack = good_pack(); pack["ci"]["originalState"] = "SKIPPED"
        add("N8 CHECK_STATUS used as CI_STATUS", pack, "REJECT", False, {"REJECT"})
        pack = good_pack(); del pack["unverified"]
        add("N9 unverified omitted", pack, "REJECT", False, {"REJECT"})
        pack = good_pack(); pack["unverified"] = []
        add("P2 unverified explicit empty array", pack, "ACCEPT", True, ())
        pack = good_pack(); pack["reuse"]["dependencies"] = "free text"
        add("N10 free-text reuse descriptor", pack, "REJECT", False, {"REJECT"})
        pack = good_pack()
        pack["reuse"]["dependencies"][0]["VERIFICATION_STATE"] = "MAYBE"
        add("N11 invalid descriptor VERIFICATION_STATE", pack, "REJECT", False,
            {"REJECT"})
        pack = good_pack(); pack["SOURCE_VERIFICATION_STATE"] = "INSUFFICIENT"
        add("N12 INSUFFICIENT on the source axis", pack, "REJECT", False, {"REJECT"})
        pack = good_pack()
        pack["SOURCE_VERIFICATION_STATE"] = "VERIFIED"
        pack["EVIDENCE_SUFFICIENCY"] = "INSUFFICIENT"
        add("P3 VERIFIED + INSUFFICIENT", pack, "ACCEPT", True, ())
        pack = good_pack()
        pack["SOURCE_VERIFICATION_STATE"] = "TEMPORARILY_UNAVAILABLE"
        pack["EVIDENCE_SUFFICIENCY"] = "INSUFFICIENT"
        add("P4 TEMPORARILY_UNAVAILABLE + INSUFFICIENT", pack, "ACCEPT", True, ())
        pack = good_pack()
        pack["seams"] = {"applicability": "N/A", "evidenceRefs": []}
        add("N13 seams N/A without reason and acceptance ref", pack, "REJECT",
            False, {"REJECT"})
        pack = good_pack(); pack["STRUCTURALLY_VALID"] = "NO"
        add("N14 declared STRUCTURALLY_VALID = NO", pack, "ACCEPT", False,
            {"REJECT"})
        return rows

    def test_38_ac10_schema_and_validator_dispose_samples_consistently(self):
        cli = self.require_cli()
        schema = self.require_schema()
        declared_codes = set(ERROR_CODES)
        table = []
        for name, pack, schema_verdict, expected_ok, expected_codes in self.samples():
            structural = cli.schema_violations(pack, schema=schema)
            result = cli.validate_pack(
                pack, schema=schema, expect_repo=REPO_OK,
                expect_base_sha=BASE_SHA, expect_candidate_sha=CANDIDATE_SHA)
            codes = self.codes(result)
            reasons = self.reasons(result)
            structural_fired = bool(reasons & STRUCTURAL_REASONS)
            table.append((name, schema_verdict, bool(structural), expected_ok,
                          result["ok"], sorted(codes)))

            # AC-10 property 1 (bidirectional): the schema evaluator and the
            # validator agree about whether a structural failure exists.
            self.assertEqual(
                schema_verdict == "REJECT", structural_fired,
                f"{name}: schema verdict ({schema_verdict}, envelope="
                f"{bool(structural)}) disagrees with the validator's structural "
                f"reasons {sorted(reasons)}")
            # AC-10 property 2: every validator rejection is either structural
            # or one of the four declared error-semantics codes.
            if not result["ok"]:
                self.assertTrue(
                    structural_fired or codes <= declared_codes,
                    f"{name}: rejection is neither structural nor declared: {codes}")
            self.assertEqual(expected_ok, result["ok"], name)
            self.assertEqual(expected_codes, codes, name)

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            print("")
            print("SAMPLE_DISPOSITION_TABLE (AC-10, schema vs validator)")
            print("  sample | schema_verdict | schema_structural | expected_ok | "
                  "validator_ok | codes")
            for name, verdict, structural, expected_ok, ok, codes in table:
                print(f"  {name} | {verdict} | {structural} | {expected_ok} | "
                      f"{ok} | {codes}")
        sys.stderr.write(buffer.getvalue())

    def test_39_schema_uses_only_supported_keywords(self):
        """No silent drift: the contract may only use operators the validator
        actually implements, and an unknown operator must be detectably
        rejected rather than silently ignored."""
        cli = self.require_cli()
        schema = self.require_schema()
        supported = set(getattr(cli, "SUPPORTED_SCHEMA_KEYWORDS", ()))
        self.assertTrue(supported, "the validator must declare its supported "
                                   "JSON Schema operator subset")
        for operator in ("type", "required", "properties",
                         "additionalProperties", "items", "enum", "const",
                         "pattern", "oneOf", "$defs", "$ref"):
            self.assertIn(operator, supported)
        self.assertEqual([], cli.schema_violations(good_pack(), schema=schema),
                         "the landed schema must be fully consumable")

        drifting = json.loads(json.dumps(schema))
        drifting["properties"]["checks"]["items"]["patternProperties"] = {
            "^x-": {"type": "string"}}
        violations = cli.schema_violations(good_pack(), schema=drifting)
        self.assertTrue(violations,
                        "SCHEMA_KEYWORD_UNSUPPORTED: an operator the validator "
                        "does not implement must never be silently ignored")
        self.assertIn("SCHEMA_KEYWORD_UNSUPPORTED",
                      {v["reason"] for v in violations})

    def test_40_grounding_mode_matches_the_canonical_grounding_reference(self):
        schema = self.require_schema()
        grounding = self.schema_of(schema, "properties/grounding")
        self.assertEqual(
            set(GROUNDING_MODES),
            set(grounding["properties"]["mode"]["enum"]),
            "grounding.mode must be the machine spelling of the three modes the "
            "canonical grounding reference owns")
        text = self.require_reference()
        for marker in (*GROUNDING_MODES, "codegraph-grounding.md"):
            self.assertIn(marker, text,
                          "grounding.mode must stay traceable to the canonical "
                          f"grounding reference; missing={marker!r}")


if __name__ == "__main__":
    unittest.main()
