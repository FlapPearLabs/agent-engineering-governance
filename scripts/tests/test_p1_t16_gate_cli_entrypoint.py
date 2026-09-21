"""P1-T16 gate CLI entrypoint self-tests (REQ-W4-04; AC-08 / AC-09 / GAP-03).

Discipline this module enforces on itself and on the gates it covers:

  * the gate scripts are driven as real command entrypoints -- an ``argv`` into
    ``main`` through a subprocess, the real process exit code, the structured
    result the entrypoint itself produces, and a probe of the actual side
    effect. A helper import is never accepted as CLI evidence (CE-09);
  * ``exit 0`` with no valid structured result never satisfies the consumer:
    it maps to ``CONSUMER_UNSATISFIED`` and the gate does not open (CE-08 and
    the D5 empty-run row, parent spec section 6.2);
  * the consumer acceptance rule is the product rule in
    ``scripts/validate_governance.py`` (``consumer_disposition``), exercised
    against the real CLI output of the PASS and the FAIL run, so the check is
    not self-referential.

Coverage set (parent spec section 10.3): PASS / FAIL / malformed /
silent-noop / real command entrypoint. Both the accepting and the refusing
outcome are checked against what the consumer actually does, not only against
what the validator printed.

Scratch trees are full copies of this repository without ``.git``, so the
validator resolves its own ``ROOT`` inside the copy and no pristine file of
this worktree is mutated.

Boundary: the guard deny-mapping synthetic tests belong to another ticket and
live under ``adapters/zcode/tests/``; this module owns the gate CLI entrypoint
self-tests and does not touch that surface.
"""
from __future__ import annotations

import importlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

VALIDATOR = ROOT / "scripts" / "validate_governance.py"
EVIDENCE_CLI = ROOT / "scripts" / "review_evidence.py"
SCRIPTS_DIR = ROOT / "scripts"
WORKFLOW = ROOT / ".github" / "workflows" / "governance-ci.yml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"

POINTER_RELATIVE = Path("deployment") / "MEMORY_POINTER_CANDIDATE.md"
BUDGET_CHECK = "memory-pointer-within-budget"

NO_STRUCTURED_RESULT = "CONSUMER_UNSATISFIED"
ACCEPTED = "PASS"
REFUSED = "FAIL"

# The gate module is imported for exactly one thing: its product-side consumer
# acceptance rule. The gate scripts' own checks are never imported or called
# in-process -- they are driven by argv (see the structural test below).
GATE_MODULE_NAME = "validate_governance"
CONSUMER_RULE_NAME = "consumer_disposition"
BUDGET_CONSTANT_NAME = "WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES"

REPO = "FlapPearLabs/agent-engineering-governance"
BASE_SHA = "1" * 40
CANDIDATE_SHA = "2" * 40
STALE_CANDIDATE_SHA = "3" * 40

# Real check ids the validator itself declares. Their presence in a report is
# evidence that the real entrypoint executed its own checks rather than
# printing a canned line. No expected total is hard-coded anywhere.
REQUIRED_REAL_CHECKS = (
    "required-files-exist",
    "markdown-links-resolve",
    "memory-pointer-within-budget",
    "ci-runs-continuity-matrix",
    "ticket-gate-documentation-wiring-only",
)

# Every step that existed in the workflow before this ticket. One of them is
# required literally by the validator itself, so none may be rewritten.
PRE_EXISTING_WORKFLOW_STEPS = (
    "uses: actions/checkout@v4",
    "ref: ${{ github.event.pull_request.head.sha || github.sha }}",
    "uses: actions/setup-python@v5",
    'python-version: "3.12"',
    "name: Run governance self-validation",
    "run: python3 scripts/validate_governance.py",
    "name: Test governance documentation wiring checks",
    "run: python3 -m unittest discover -s scripts/tests",
    "name: Run PROJECT_CONTINUITY_CONTRACT synthetic matrix",
    "run: python3 -m unittest discover -s adapters/zcode/tests",
    "name: Run public-release current-tree scan",
    "run: python3 scripts/validate_public_release.py",
    "name: Run public-release commit metadata gate",
    "run: python3 scripts/validate_public_release.py --commit-metadata",
    "name: Run public-release policy self-tests",
    "run: python3 scripts/validate_public_release.py --selftest",
)

NEW_WORKFLOW_STEP_RUN = (
    "python3 -m unittest scripts.tests.test_p1_t16_gate_cli_entrypoint"
)
NEW_WORKFLOW_STEP_NAME = "name: Run gate CLI entrypoint self-tests"

# The historic rendering of the human report. These two statements are the
# whole non-JSON output contract of the validator.
LEGACY_LINE_STATEMENT = (
    """print(f"{'PASS' if ok else 'FAIL'}  {name}" """
    """+ (f"  [{detail}]" if detail and not ok else ""))"""
)
LEGACY_COUNTS_STATEMENT = (
    r'print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")'
)

_LEGACY_LINE = re.compile(r"^(PASS|FAIL)  (\S+)(?:  \[.*\])?$")
_LEGACY_COUNTS = re.compile(r"^(\d+)/(\d+) checks passed$")
_BUDGET_DECLARATION = re.compile(
    re.escape(BUDGET_CONSTANT_NAME) + r"\s*=\s*(\d+)")

SILENT_NOOP_GATE_SOURCE = '''\
"""A gate whose real command entrypoint exits 0 having produced nothing.

This is the CE-08 counterexample producer: a script that would authorise
continuation by its exit code alone. Nothing here is imported; it is executed
as a real command entrypoint by the self-test.
"""
import sys

sys.exit(0)
'''

_SCRATCH: dict = {}


def run_cli(script, *argv):
    """Drive a real command entrypoint: argv -> main, real exit code."""
    return subprocess.run(
        [sys.executable, str(script), *argv],
        capture_output=True, text=True, check=False,
    )


def validator_in(tree: Path) -> Path:
    return Path(tree) / "scripts" / "validate_governance.py"


def structured(completed) -> dict | None:
    """The machine-readable result on stdout, or None when there is none."""
    try:
        payload = json.loads(completed.stdout)
    except (ValueError, TypeError):
        return None
    return payload if isinstance(payload, dict) else None


def declared_pointer_budget() -> int:
    """The pointer budget, consumed from its single declaration point.

    The value and its unit are owned by the deployment contract; the validator
    declares them once and this probe reads that declaration instead of
    restating a number of its own.
    """
    match = _BUDGET_DECLARATION.search(VALIDATOR.read_text(encoding="utf-8"))
    if not match:
        raise AssertionError(
            f"{VALIDATOR} does not declare {BUDGET_CONSTANT_NAME}, so the "
            "byte-budget probe cannot be sized from the landed contract")
    return int(match.group(1))


def require_consumer_rule(testcase: unittest.TestCase):
    """The product consumer rule, or fail naming the missing behaviour."""
    sys.path.insert(0, str(SCRIPTS_DIR))
    try:
        module = importlib.import_module(GATE_MODULE_NAME)
    except Exception as exc:  # noqa: BLE001 - a broken import is not the RED
        testcase.fail(
            "GATE_MODULE_UNIMPORTABLE: the governance validator cannot be "
            f"imported ({type(exc).__name__}: {exc}); that is a broken "
            "harness, not a counterexample RED")
    rule = getattr(module, CONSUMER_RULE_NAME, None)
    if not callable(rule):
        testcase.fail(
            "CONSUMER_RULE_ABSENT: the governance validator exposes no "
            f"{CONSUMER_RULE_NAME}(exit_code, structured_result) rule, so "
            "'exit 0 with no valid structured result' cannot be refused at "
            "the consumer boundary yet (expected RED condition of P1-T16 "
            "before implementation)")
    return rule


def scratch_tree() -> Path:
    """A pristine full copy of this repository, without ``.git``."""
    if "pristine" not in _SCRATCH:
        root = Path(tempfile.mkdtemp(prefix="p1t16-pristine-"))
        shutil.copytree(ROOT, root / "tree",
                        ignore=shutil.ignore_patterns(".git"), symlinks=True)
        _SCRATCH["pristine"] = root / "tree"
    return _SCRATCH["pristine"]


def pristine_legacy_run():
    """The real no-flag validator run on the pristine copy (one spawn)."""
    if "legacy" not in _SCRATCH:
        _SCRATCH["legacy"] = run_cli(validator_in(scratch_tree()))
    return _SCRATCH["legacy"]


def pristine_json_run():
    """The real structured validator run on the pristine copy (one spawn)."""
    if "json" not in _SCRATCH:
        _SCRATCH["json"] = run_cli(validator_in(scratch_tree()), "--json")
    return _SCRATCH["json"]


def over_budget_tree() -> Path:
    """A copy of the pristine tree whose pointer body is over its budget.

    Only ``deployment/MEMORY_POINTER_CANDIDATE.md`` differs from the pristine
    copy. The padding is CJK text inserted inside the scored fenced block, so
    the overrun is an encoding overrun: characters are not the unit. The
    amount is derived from the value the validator declares, and the padding
    alone already exceeds it, so the overrun does not depend on how much slack
    the current body happens to have.
    """
    if "over_budget" not in _SCRATCH:
        budget = declared_pointer_budget()
        chars = budget // 3 + 2  # 3 UTF-8 bytes per CJK character

        root = Path(tempfile.mkdtemp(prefix="p1t16-overbudget-"))
        tree = root / "tree"
        shutil.copytree(scratch_tree(), tree, symlinks=True)
        pointer = tree / POINTER_RELATIVE
        text = pointer.read_text(encoding="utf-8")
        padded, count = re.subn(r"(```(?:markdown)?\n)",
                                lambda m: m.group(1) + "本" * chars + "\n",
                                text, count=1)
        if count != 1:
            raise AssertionError(
                "the pointer candidate has no scored fenced block to pad")
        pointer.write_text(padded, encoding="utf-8")
        _SCRATCH["over_budget"] = tree
    return _SCRATCH["over_budget"]


def write_pack(directory: Path, pack: dict, name="pack.json") -> Path:
    path = Path(directory) / name
    path.write_text(json.dumps(pack, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return path


def sufficient_pack() -> dict:
    """A pack the landed evidence contract accepts, with a complete subject."""
    return {
        "schemaVersion": 1,
        "subject": {"repo": REPO, "baseSha": BASE_SHA,
                    "candidateSha": CANDIDATE_SHA},
        "authorityRefs": ["P1_AGENT_ENGINEERING_GOVERNANCE_DELTA_SPEC#REQ-W4-04"],
        "producer": {"identity": "laneA-worker", "version": "1",
                     "observedAt": "2026-09-21T00:00:00Z"},
        "checks": [{"id": "c1", "scope": "scripts/validate_governance.py",
                    "commandRef": "references/review-evidence.md#9",
                    "status": "PASS", "exitCode": 0,
                    "artifactRefs": ["evidence/laneA/governance.txt"]}],
        "artifacts": [{"location": "evidence/laneA/governance.txt",
                       "contentDigest": "sha256:" + "0" * 64}],
        "ci": {"run": "1234567890", "job": "validate-governance",
               "checkedSha": CANDIDATE_SHA, "originalState": "PASS"},
        "grounding": {"mode": "UNAVAILABLE",
                      "coverage": "CODEGRAPH_UNAVAILABLE",
                      "evidenceRef": "references/codegraph-grounding.md#2.1"},
        "seams": {"applicability": "REQUIRED", "evidenceRefs": []},
        "reuse": {"sourceEvidence": "none",
                  "validFor": "this candidate only",
                  "dependencies": [], "invalidation": "master drift"},
        "unverified": [],
        "STRUCTURALLY_VALID": "YES",
        "SOURCE_VERIFICATION_STATE": "VERIFIED",
        "EVIDENCE_SUFFICIENCY": "SUFFICIENT",
        "semanticScopeStatus": None,
        "reviewerDecisionRefs": [],
    }


class RealCommandEntrypointTests(unittest.TestCase):
    """The discipline itself: argv, exit code, structured output, probe."""

    def test_gates_are_driven_by_argv_and_never_imported_as_a_substitute(self):
        """CE-09 / AC-09: a helper import must not stand in for a CLI test."""
        def needle(*parts):
            return "".join(parts)

        source = Path(__file__).read_text(encoding="utf-8")
        for assembled in (
            needle("spec_from_", "file_location"),
            needle("import validate_", "governance"),
            needle("validate_governance.", "main"),
            needle("review_evidence.", "main"),
            needle("ticket_gate_", "wiring"),
            needle("memory_pointer_", "within_budget"),
            needle("memory_pointer_", "body"),
            needle("evidence_lifecycle_", "findings"),
            needle("build_", "parser"),
        ):
            self.assertNotIn(
                assembled, source,
                f"this module must not reference {assembled!r}: the gate "
                "scripts are driven as command entrypoints, not as helpers")
        self.assertIn("subprocess.run(", source)
        self.assertIn("run_cli(validator_in(", source)
        self.assertIn("run_cli(EVIDENCE_CLI", source)
        # Exactly one name is taken from the gate module, in-process: its
        # consumer acceptance rule. Any other access would be a helper
        # shortcut dressed up as CLI evidence. The needles are assembled, not
        # written out, so that the counting statements do not match themselves.
        module_access = needle("getattr(module", ", ")
        self.assertEqual(1, source.count(module_access))
        self.assertIn(module_access + "CONSUMER_RULE_NAME", source)
        self.assertEqual(1, source.count(needle("import_module", "(")))

    def test_the_argv_launcher_really_reaches_a_real_entrypoint(self):
        """The launcher is not a stub: argv reaches a real CLI and returns."""
        completed = run_cli(EVIDENCE_CLI, "--help")
        self.assertEqual(0, completed.returncode,
                         f"stderr={completed.stderr[:400]}")
        self.assertIn("usage:", completed.stdout)

    def test_consumer_accepts_the_real_structured_pass_run(self):
        """PASS: real entrypoint, real exit code, structured result, accepted."""
        completed = pristine_json_run()
        report = structured(completed)
        self.assertIsNotNone(
            report,
            "the validator's real entrypoint produced no machine-readable "
            f"result for the structured flag; stdout={completed.stdout[:400]!r}")
        self.assertEqual(0, completed.returncode,
                         f"stderr={completed.stderr[:400]}")
        self.assertEqual(ACCEPTED, report["verdict"])
        self.assertEqual(len(report["checks"]), report["total"])
        self.assertEqual(len(report["checks"]), report["passed"],
                         "the accepted run reports a failed check")
        names = {entry["name"] for entry in report["checks"]}
        missing = sorted(set(REQUIRED_REAL_CHECKS) - names)
        self.assertEqual(
            [], missing,
            f"the real entrypoint did not execute these checks: {missing}")
        rule = require_consumer_rule(self)
        self.assertEqual(ACCEPTED, rule(completed.returncode, completed.stdout))

    def test_legacy_stdout_is_unchanged_and_carries_no_structured_result(self):
        """Additivity: without the structured flag, only the historic text."""
        completed = pristine_legacy_run()
        self.assertEqual(0, completed.returncode,
                         f"stderr={completed.stderr[:400]}")
        self.assertEqual("", completed.stderr)
        self.assertIsNone(
            structured(completed),
            "a run without the structured flag must not emit a result object")

        lines = completed.stdout.split("\n")
        self.assertEqual("", lines[-1])
        counts = _LEGACY_COUNTS.match(lines[-2])
        self.assertIsNotNone(counts, f"last line={lines[-2]!r}")
        self.assertEqual("", lines[-3], "the counts line must stand alone")
        passed = total = 0
        for line in lines[:-3]:
            match = _LEGACY_LINE.match(line)
            self.assertIsNotNone(match, f"unexpected legacy line: {line!r}")
            total += 1
            passed += match.group(1) == "PASS"
        self.assertEqual(f"{passed}/{total} checks passed", lines[-2])
        self.assertGreaterEqual(total, len(REQUIRED_REAL_CHECKS))
        for name in REQUIRED_REAL_CHECKS:
            self.assertIn(f"PASS  {name}", completed.stdout)

        # The two historic statements are still the whole non-JSON rendering.
        gate_source = VALIDATOR.read_text(encoding="utf-8")
        self.assertIn(LEGACY_LINE_STATEMENT, gate_source)
        self.assertIn(LEGACY_COUNTS_STATEMENT, gate_source)

    def test_mutated_tree_fails_a_check_and_the_consumer_refuses(self):
        """FAIL: a real check fails, real exit code 1, consumer refuses."""
        rule = require_consumer_rule(self)
        completed = run_cli(validator_in(over_budget_tree()), "--json")
        report = structured(completed)
        self.assertIsNotNone(report, f"stdout={completed.stdout[:400]!r}")
        self.assertNotEqual(0, completed.returncode,
                            "a failing check must not exit 0")
        self.assertEqual("FAIL", report["verdict"])
        failed = [entry["name"] for entry in report["checks"]
                  if not entry["ok"]]
        self.assertIn(BUDGET_CHECK, failed)
        self.assertEqual(REFUSED, rule(completed.returncode, completed.stdout))

    def test_malformed_result_is_never_accepted(self):
        """A result the consumer cannot accept is not a satisfied gate."""
        rule = require_consumer_rule(self)

        # A real entrypoint that exits 0 having emitted no result object: the
        # validator's own human rendering, and the evidence CLI's declared
        # no-envelope path.
        legacy = pristine_legacy_run()
        self.assertEqual(0, legacy.returncode)
        self.assertEqual(NO_STRUCTURED_RESULT,
                         rule(legacy.returncode, legacy.stdout))

        helped = run_cli(EVIDENCE_CLI, "--help")
        self.assertEqual(0, helped.returncode)
        self.assertIsNone(structured(helped))
        self.assertEqual(NO_STRUCTURED_RESULT,
                         rule(helped.returncode, helped.stdout))

        # Results that parse as objects but are not usable results.
        for broken in ({"verdict": "PASS"},
                       {"verdict": "PASS", "checks": []},
                       {"verdict": "PASS", "total": 1,
                        "checks": [{"ok": True}]},
                       {"verdict": "PASS", "total": 1,
                        "checks": [{"name": "c", "ok": False}]},
                       {"verdict": "PASS", "total": 2,
                        "checks": [{"name": "c", "ok": True}]},
                       {"ok": True},
                       ""):
            with self.subTest(broken=broken):
                self.assertEqual(NO_STRUCTURED_RESULT, rule(0, broken))

    def test_silent_noop_exit_zero_with_empty_output_cannot_open_the_gate(self):
        """CE-08 / D5: exit 0 with nothing is CONSUMER_UNSATISFIED, not PASS."""
        rule = require_consumer_rule(self)
        temp = Path(tempfile.mkdtemp(prefix="p1t16-noop-"))
        self.addCleanup(shutil.rmtree, temp, True)
        gate = temp / "silent_noop_gate.py"
        gate.write_text(SILENT_NOOP_GATE_SOURCE, encoding="utf-8")

        completed = run_cli(gate)
        self.assertEqual(0, completed.returncode,
                         "the counterexample gate must really exit 0")
        self.assertEqual("", completed.stdout)
        self.assertEqual("", completed.stderr)
        disposition = rule(completed.returncode, completed.stdout)
        self.assertNotEqual(ACCEPTED, disposition,
                            "an empty exit-0 run was read as a satisfied gate")
        self.assertEqual(NO_STRUCTURED_RESULT, disposition)

    def test_p1_t09_probe_the_real_entrypoint_executes_the_budget_check(self):
        """SEAM: the consuming validator really runs the P1-T09 budget check."""
        self.assertIn(f"PASS  {BUDGET_CHECK}", pristine_legacy_run().stdout)

        completed = run_cli(validator_in(over_budget_tree()))
        self.assertNotEqual(0, completed.returncode,
                            "an over-budget pointer must not exit 0")
        match = re.search(
            rf"(?m)^FAIL  {re.escape(BUDGET_CHECK)}  "
            r"\[bytes=(\d+) \(budget (\d+)\)\]$",
            completed.stdout)
        self.assertIsNotNone(
            match, f"the budget check did not report a failure; "
                   f"stdout={completed.stdout[-800:]!r}")
        self.assertGreater(
            int(match.group(1)), int(match.group(2)),
            "the probe did not actually push the scored body over its budget")


class EvidenceCliContractTests(unittest.TestCase):
    """SEAM with the evidence CLI: real argv, real exit code, envelope as-is."""

    def test_real_collect_emits_its_declared_envelope(self):
        temp = Path(tempfile.mkdtemp(prefix="p1t16-collect-"))
        self.addCleanup(shutil.rmtree, temp, True)
        out = temp / "skeleton.json"
        completed = run_cli(
            EVIDENCE_CLI, "collect",
            "--repo", REPO,
            "--base-sha", BASE_SHA,
            "--candidate-sha", CANDIDATE_SHA,
            "--producer-identity", "laneA-worker",
            "--producer-version", "1",
            "--out", str(out))
        envelope = structured(completed)
        self.assertIsNotNone(envelope, f"stdout={completed.stdout[:400]!r}")
        self.assertEqual(0, completed.returncode)
        self.assertEqual(envelope["exitCode"], completed.returncode)
        self.assertEqual("collect", envelope["mode"])
        self.assertTrue(envelope["ok"])
        self.assertTrue(Path(envelope["skeletonPath"]).is_file())
        self.assertIsInstance(envelope["skeleton"], dict)

    def run_validate(self, pack: dict, expected_candidate: str):
        temp = Path(tempfile.mkdtemp(prefix="p1t16-validate-"))
        self.addCleanup(shutil.rmtree, temp, True)
        path = write_pack(temp, pack)
        completed = run_cli(
            EVIDENCE_CLI, "validate",
            "--pack", str(path),
            "--expect-repo", pack["subject"]["repo"],
            "--expect-base-sha", pack["subject"]["baseSha"],
            "--expect-candidate-sha", expected_candidate)
        return completed, structured(completed)

    def test_valid_pack_is_accepted_and_a_violating_pack_is_refused(self):
        rule = require_consumer_rule(self)

        completed, envelope = self.run_validate(sufficient_pack(),
                                               CANDIDATE_SHA)
        self.assertIsNotNone(envelope, f"stdout={completed.stdout[:400]!r}")
        self.assertEqual(0, completed.returncode,
                         f"violations={envelope['violations']}")
        self.assertEqual(envelope["exitCode"], completed.returncode)
        self.assertEqual("validate", envelope["mode"])
        self.assertTrue(envelope["ok"])
        self.assertEqual([], envelope["violations"])
        self.assertEqual(ACCEPTED, rule(completed.returncode, completed.stdout))

        stale, stale_envelope = self.run_validate(sufficient_pack(),
                                                  STALE_CANDIDATE_SHA)
        self.assertIsNotNone(stale_envelope,
                             f"stdout={stale.stdout[:400]!r}")
        self.assertNotEqual(0, stale.returncode)
        self.assertFalse(stale_envelope["ok"])
        reasons = {v.get("reason") for v in stale_envelope["violations"]}
        self.assertIn("SUBJECT_CANDIDATE_SHA_STALE", reasons)
        self.assertEqual(REFUSED, rule(stale.returncode, stale.stdout))


class CiWiringTests(unittest.TestCase):
    """The self-test is wired into the existing workflow; no new runner."""

    def test_self_test_step_is_added_to_the_existing_workflow(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(NEW_WORKFLOW_STEP_NAME, text)
        self.assertIn(NEW_WORKFLOW_STEP_RUN, text)
        self.assertLess(
            text.index("unittest discover -s scripts/tests"),
            text.index(NEW_WORKFLOW_STEP_RUN),
            "the self-test step must run after the discover step")
        for preserved in PRE_EXISTING_WORKFLOW_STEPS:
            self.assertIn(
                preserved, text,
                f"pre-existing workflow text was changed: {preserved!r}")
        self.assertIn("unittest discover -s adapters/zcode/tests", text)

    def test_no_new_workflow_job_or_runner_is_introduced(self):
        self.assertEqual(
            ["governance-ci.yml", "public-release-audit.yml"],
            sorted(path.name for path in WORKFLOWS_DIR.glob("*.yml")),
            "this ticket must not create a workflow file")
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(1, text.count("\njobs:"))
        self.assertEqual(1, text.count("runs-on:"))
        self.assertIn("runs-on: ubuntu-latest", text)


if __name__ == "__main__":
    unittest.main()
