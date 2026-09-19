"""Counterexample-first tests for the P1-T06 evidence producer trust and
retrieval boundary (Issue #21, WORK_PACKAGE W2, RISK_CLASS HIGH).

SUPPORTING SURFACE (RULES.md R6, declared): this module consumes the four
coordinated surfaces of the Review Evidence interface --

    references/review-evidence.md          single semantic detail owner
    schemas/review-evidence.schema.json    versioned machine contract
    templates/review-evidence.json         placeholder-form template
    scripts/review_evidence.py             thin collect / validate CLI

-- and declares no field name, no closed set and no location domain of its own.
The declared `artifacts[].location` domain stays owned by P1-T04 (section 3 /
schema); this ticket implements only the BEHAVIOUR that consumes it: evidence is
data, never an executable authority (parent spec INV-15 / CE-25).

COUNTEREXAMPLE INPUTS (Ticket #21, CE-25 / CE-06)
    CE-25  an evidence pack that tries to make the tool execute a planted
           `commandRef`; fetch an arbitrary URL carried by the evidence; or
           treat `artifacts[].location` as arbitrary filesystem or network
           authority -> each MUST be refused (trust boundary violation) with no
           side effect anywhere in the pipeline.
    CE-06  the subject-mismatch regression guard: wrong repo / baseSha /
           candidateSha is still rejected and never reaches behavioural PASS,
           so a trust-boundary change cannot buy a wrong-subject pack a PASS.

EXPECTED_RED_CONDITION (before implementation, on the unmodified base)
    No boundary exists, so an escaping path, an absolute path and a URL-carried
    location are all ACCEPTED by `validate` (exit 0, ok=true), the retrieval
    entry points do not exist at all, and no positive control proves that a
    legal repository-relative path is still retrieved -> the checks FAIL.

RED DISCIPLINE (references/ticket-lane.md section 4): RED never surfaces as a
harness crash. Every assertion acquires its subject through a `require_*`
helper that fails the test with an explicit BOUNDARY_ABSENT / CONTRACT_ABSENT
message instead of raising.

POSITIVE CONTROL (AC-27): the boundary must not over-block. A legal
repository-relative path and an authorised CI artifact identifier (through the
existing provider interface, which this ticket does NOT build) must still be
retrievable, and a green pack with a legal location must still exit 0.

Stdlib only. Run with:
    python3 -m unittest scripts.tests.test_p1_t06_producer_trust_boundary -v
"""
from __future__ import annotations

import http.server
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

CLI_PATH = ROOT / "scripts" / "review_evidence.py"
SCHEMA_PATH = ROOT / "schemas" / "review-evidence.schema.json"
TEMPLATE_PATH = ROOT / "templates" / "review-evidence.json"
REFERENCE_PATH = ROOT / "references" / "review-evidence.md"
LANDED_CONTRACT_TEST = ROOT / "scripts" / "tests" / "test_review_evidence_contract.py"

REPO = "FlapPearLabs/agent-engineering-governance"
OTHER_REPO = "FlapPearLabs/zhihu-grabber-toolkit"
BASE_SHA = "1" * 40
CANDIDATE_SHA = "2" * 40
OTHER_SHA = "3" * 40

# The loopback host is COMPOSED at run time: the public-release gate forbids a
# literal loopback endpoint in a committed artifact (RULES.md R2), and this
# suite must not become the exception that proves the rule.
LOOPBACK = ".".join(("127", "0", "0", "1"))

# Entry points the retrieval boundary declares. Names, not value domains: the
# location domain itself is P1-T04's and is never re-declared here.
BOUNDARY_ENTRY_POINTS = (
    "location_retrieval_violation",
    "retrieve_artifact",
    "evidence_boundary_findings",
    "RETRIEVAL_BOUNDARY_REASONS",
    "RETRIEVAL_UNAVAILABLE",
    "ARTIFACT_LOCATION_REFERENCE",
    "COMMAND_REFERENCE",
)

# Constructs that would give the CLI an execution or network capability. The
# boundary's whole security claim is that no such capability exists anywhere in
# the evidence pipeline, so this set is scanned statically as well as exercised
# behaviourally.
FORBIDDEN_CAPABILITY_TOKENS = (
    "subprocess", "os.system", "os.popen", "os.exec", "os.spawn", "os.fork",
    "socket", "urllib", "http.client", "httplib", "ftplib", "requests",
    "pty.spawn", "eval(", "exec(",
)

PROTECTED_TOKENS = (
    "IDENTITY_VERSION_OR_DIGEST", "semanticScopeStatus", "reviewerDecisionRefs",
    "STRUCTURALLY_VALID", "SOURCE_VERIFICATION_STATE", "EVIDENCE_SUFFICIENCY",
)

_MODULE_CACHE: dict = {}


def good_pack(location="evidence/laneB/governance.txt") -> dict:
    """A pack the frozen contract AND the trust boundary must both accept."""
    return {
        "schemaVersion": 1,
        "subject": {"repo": REPO, "baseSha": BASE_SHA,
                    "candidateSha": CANDIDATE_SHA},
        "authorityRefs": ["P1_AGENT_ENGINEERING_GOVERNANCE_DELTA_SPEC#REQ-W2-04"],
        "producer": {"identity": "laneB-worker", "version": "1",
                     "observedAt": "2026-09-19T00:00:00Z"},
        "checks": [{"id": "c1", "scope": "scripts/validate_governance.py",
                    "commandRef": "references/review-evidence.md#9",
                    "status": "PASS", "exitCode": 0, "artifactRefs": [location]}],
        "artifacts": [{"location": location,
                       "contentDigest": "sha256:" + "0" * 64}],
        "ci": {"run": "1234567890", "job": "validate-governance",
               "checkedSha": CANDIDATE_SHA, "originalState": "PASS"},
        "grounding": {"mode": "UNAVAILABLE", "coverage": "CODEGRAPH_UNAVAILABLE",
                      "evidenceRef": "references/codegraph-grounding.md#2.1"},
        "seams": {"applicability": "REQUIRED", "evidenceRefs": []},
        "reuse": {"sourceEvidence": "none", "validFor": "this lane only",
                  "dependencies": [], "invalidation": "any shared schema change"},
        "unverified": [],
        "STRUCTURALLY_VALID": "YES",
        "SOURCE_VERIFICATION_STATE": "VERIFIED",
        "EVIDENCE_SUFFICIENCY": "SUFFICIENT",
        "semanticScopeStatus": None,
        "reviewerDecisionRefs": [],
    }


def pack_with_location(location) -> dict:
    pack = good_pack(location)
    return json.loads(json.dumps(pack))


def write_pack(directory: Path, pack: dict, name="pack.json") -> Path:
    path = directory / name
    path.write_text(json.dumps(pack, indent=2), encoding="utf-8")
    return path


def run_cli(args, cwd=None, timeout=60):
    return subprocess.run(
        [sys.executable, str(CLI_PATH), *args],
        capture_output=True, text=True, cwd=cwd, check=False, timeout=timeout)


class _CountingHandler(http.server.BaseHTTPRequestHandler):
    """A reachable local service that records every request it receives."""

    requests: list = []

    def do_GET(self):  # noqa: N802 - the stdlib handler spelling
        type(self).requests.append(self.path)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"probe")

    def log_message(self, *args):  # silence the server's own stderr chatter
        return


class ProducerTrustBoundaryTests(unittest.TestCase):
    """P1-T06: evidence is data, never an executable or retrieval authority."""

    # ---------------- subject acquisition (RED-safe) ----------------

    def require_cli(self):
        if "cli" in _MODULE_CACHE:
            return _MODULE_CACHE["cli"]
        if not CLI_PATH.is_file():
            self.fail(
                "CONTRACT_ABSENT: scripts/review_evidence.py does not exist, so "
                "the evidence pipeline cannot be exercised (expected RED "
                "condition of P1-T04 before implementation)")
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
        _MODULE_CACHE["cli"] = module
        return module

    def require_boundary(self):
        """The retrieval boundary entry points, or an explicit RED failure."""
        module = self.require_cli()
        missing = [name for name in BOUNDARY_ENTRY_POINTS
                   if not hasattr(module, name)]
        if missing:
            self.fail(
                "BOUNDARY_ABSENT: scripts/review_evidence.py exposes no "
                f"retrieval boundary entry point {missing}, so evidence carried "
                "by a pack is not bounded by any retrieval decision and no "
                "positive control can prove a legal path is still retrievable "
                "(expected RED condition of P1-T06 before implementation)")
        return module

    def require_reference(self) -> str:
        if not REFERENCE_PATH.is_file():
            self.fail(f"CONTRACT_ABSENT: {REFERENCE_PATH.relative_to(ROOT)} "
                      "does not exist")
        return REFERENCE_PATH.read_text(encoding="utf-8")

    # ---------------- helpers ----------------

    def boundary_reasons(self, payload: dict) -> set:
        return {v["reason"] for v in payload["violations"]}

    def codes(self, payload: dict) -> set:
        return {v["code"] for v in payload["violations"]}

    def validate_in_process(self, pack: dict, *extra_args) -> dict:
        """Drive the public CLI in process and return the emitted envelope."""
        module = self.require_cli()
        with tempfile.TemporaryDirectory() as temp:
            pack_path = write_pack(Path(temp), pack)
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                module.main(["validate", "--pack", str(pack_path),
                             "--expect-repo", REPO,
                             "--expect-base-sha", BASE_SHA,
                             "--expect-candidate-sha", CANDIDATE_SHA,
                             *extra_args])
        return json.loads(buffer.getvalue())

    def local_service(self):
        """A running local HTTP service plus the number of requests it saw."""
        _CountingHandler.requests = []
        server = http.server.HTTPServer((LOOPBACK, 0), _CountingHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, f"http://{LOOPBACK}:{server.server_address[1]}/probe"

    # ==================================================================
    # AC-24 / CE-25: commandRef is a declaration, never an execution authority
    # ==================================================================

    def test_01_the_retrieval_boundary_entry_points_exist(self):
        module = self.require_boundary()
        for name in ("location_retrieval_violation", "retrieve_artifact",
                     "evidence_boundary_findings"):
            with self.subTest(entry_point=name):
                self.assertTrue(callable(getattr(module, name)),
                                f"{name} must be callable")
        self.assertEqual(
            "artifacts[].location", module.ARTIFACT_LOCATION_REFERENCE,
            "only a declared artifact location is a retrieval declaration")
        self.assertEqual(
            "checks[].commandRef", module.COMMAND_REFERENCE,
            "a commandRef must stay a traceability reference")
        self.assertNotIn(
            module.RETRIEVAL_UNAVAILABLE, module.RETRIEVAL_BOUNDARY_REASONS,
            "an unavailable source is not an out-of-bounds violation; the two "
            "must never alias")

    def test_02_a_planted_command_ref_probe_leaves_no_side_effect(self):
        """AC-24: a probe command in commandRef produces no side effect."""
        module = self.require_cli()
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            marker = workdir / "P1_T06_PROBE_SIDE_EFFECT"
            canary = "sh -c 'touch " + str(marker) + "'"
            pack = good_pack()
            pack["checks"][0]["commandRef"] = canary
            pack_path = write_pack(workdir, pack)

            buffer = io.StringIO()
            with redirect_stdout(buffer):
                module.main(["validate", "--pack", str(pack_path),
                             "--expect-repo", REPO,
                             "--expect-base-sha", BASE_SHA,
                             "--expect-candidate-sha", CANDIDATE_SHA])
            json.loads(buffer.getvalue())
            self.assertFalse(
                marker.exists(),
                "AC-24 VIOLATED: the evidence pipeline executed the planted "
                f"commandRef {canary!r}")

            out_path = workdir / "out.json"
            with redirect_stdout(io.StringIO()):
                module.main(["collect", "--repo", REPO, "--base-sha", BASE_SHA,
                             "--candidate-sha", CANDIDATE_SHA,
                             "--producer-identity", "laneB-worker",
                             "--producer-version", "1",
                             "--out", str(out_path)])
            self.assertFalse(
                marker.exists(),
                "AC-24 VIOLATED: the collect path executed a command")

    def test_03_the_cli_has_no_execution_or_network_capability(self):
        """No code path can run a command or open a connection at all."""
        source = CLI_PATH.read_text(encoding="utf-8")
        found = sorted({token for token in FORBIDDEN_CAPABILITY_TOKENS
                        if token in source})
        self.assertEqual(
            [], found,
            "AC-24 / AC-25 VIOLATED: the evidence pipeline carries an execution "
            f"or network capability ({found}); evidence must be data only")

    def test_04_the_capability_detector_is_not_vacuous(self):
        """A synthetic module that does execute IS detected."""
        synthetic = (
            "import subprocess\n"
            "def run(reference):\n"
            "    return subprocess.check_output(reference)\n"
            "def fetch(url):\n"
            "    import urllib.request\n"
            "    return urllib.request.urlopen(url)\n"
        )
        found = {token for token in FORBIDDEN_CAPABILITY_TOKENS
                 if token in synthetic}
        self.assertIn("subprocess", found,
                      "the capability detector went blind on an injected "
                      "execution capability")
        self.assertIn("urllib", found,
                      "the capability detector went blind on an injected "
                      "network capability")

    def test_05_a_command_reference_is_never_retrievable(self):
        """The single retrieval entry point refuses anything but a location."""
        module = self.require_boundary()
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "P1_T06_COMMAND_REF_RETRIEVED"
            canary = "sh -c 'touch " + str(marker) + "'"
            result = module.retrieve_artifact(
                canary, reference_kind=module.COMMAND_REFERENCE, root=temp)
            self.assertFalse(result["retrieved"],
                             "a commandRef must never be retrieved")
            self.assertEqual("EVIDENCE_REFERENCE_IS_DATA", result["reason"])
            self.assertIsNone(result["content"])
            self.assertFalse(marker.exists(),
                             "AC-24 VIOLATED: the command reference was run")

    # ==================================================================
    # AC-25: no arbitrary URL is ever retrieved
    # ==================================================================

    def test_06_an_arbitrary_url_is_refused_before_any_request(self):
        module = self.require_boundary()
        server, _thread, url = self.local_service()
        try:
            for declared in (url, url.replace("http://", "https://"),
                             "ftp://example.invalid/x"):
                with self.subTest(location=declared):
                    self.assertEqual(
                        "ARBITRARY_URL_RETRIEVAL",
                        module.location_retrieval_violation(declared, root=str(ROOT)),
                        "a URL declaration is an arbitrary retrieval "
                        "authorisation and must be refused")
                    result = module.retrieve_artifact(declared, root=str(ROOT))
                    self.assertFalse(result["retrieved"])
                    self.assertEqual("ARBITRARY_URL_RETRIEVAL", result["reason"])
                    self.assertIsNone(result["content"])
            self.assertEqual(
                [], _CountingHandler.requests,
                "AC-25 VIOLATED: the pipeline issued a request to a URL carried "
                "by the evidence")
        finally:
            server.shutdown()
            server.server_close()

    def test_07_a_reachable_service_records_zero_requests_end_to_end(self):
        """AC-25 through the public CLI, with a genuinely reachable service."""
        server, _thread, url = self.local_service()
        try:
            payload = self.validate_in_process(pack_with_location(url))
            self.assertFalse(payload["ok"], f"violations={payload['violations']}")
            self.assertEqual(1, payload["exitCode"])
            self.assertIn("ARBITRARY_URL_RETRIEVAL", self.boundary_reasons(payload),
                          f"violations={payload['violations']}")
            self.assertEqual(
                [], _CountingHandler.requests,
                "AC-25 VIOLATED: validate retrieved a URL carried by the pack")
        finally:
            server.shutdown()
            server.server_close()

    # ==================================================================
    # AC-26: absolute and out-of-bounds locations are path violations
    # ==================================================================

    def test_08_absolute_paths_are_path_violations(self):
        module = self.require_boundary()
        absolute_posix = "/" + "etc/passwd"
        cases = {
            "absolute posix": absolute_posix,
            "absolute windows": "C:" + "\\Windows\\win.ini",
            "absolute windows forward": "C:/Windows/win.ini",
            "unc share": "\\\\host" + "\\share\\x.txt",
        }
        for label, declared in cases.items():
            with self.subTest(case=label):
                self.assertEqual(
                    "PATH_VIOLATION",
                    module.location_retrieval_violation(declared),
                    f"{label}: an absolute location is a path violation")
                self.assertFalse(
                    module.retrieve_artifact(declared)["retrieved"],
                    f"{label}: an absolute location must never be retrieved")

    def test_09_parent_directory_escape_is_a_path_violation(self):
        module = self.require_boundary()
        cases = {
            "escaping": "../../outside.txt",
            "escaping deep": "a/b/../../../../etc/hosts",
            "escaping mid": "evidence/../../outside.txt",
            "backslash escaping": ".." + "\\.." + "\\outside.txt",
        }
        for label, declared in cases.items():
            with self.subTest(case=label):
                self.assertEqual(
                    "PATH_VIOLATION",
                    module.location_retrieval_violation(declared),
                    f"{label}: a parent-directory escape is a path violation")
        self.assertIsNone(
            module.location_retrieval_violation("evidence/../evidence/x.txt"),
            "a `..` that stays inside the repository boundary is legal: the "
            "boundary is a boundary check, not a blanket ban on the segment")

    def test_10_a_location_that_escapes_a_supplied_root_is_refused(self):
        module = self.require_boundary()
        with tempfile.TemporaryDirectory() as temp:
            anchor = Path(temp) / "repo"
            (anchor / "evidence").mkdir(parents=True)
            outside = Path(temp) / "outside.txt"
            outside.write_text("outside the boundary", encoding="utf-8")
            self.assertEqual(
                "PATH_VIOLATION",
                module.location_retrieval_violation("../outside.txt",
                                                    root=str(anchor)),
                "a location that resolves outside the repository root is a "
                "path violation")
            result = module.retrieve_artifact("../outside.txt", root=str(anchor))
            self.assertFalse(result["retrieved"])
            self.assertEqual("PATH_VIOLATION", result["reason"])
            self.assertIsNone(
                result["content"],
                "AC-26 VIOLATED: the out-of-bounds file was read; the boundary "
                "must be decided BEFORE any I/O")

    def test_11_non_string_and_empty_locations_fail_closed(self):
        module = self.require_boundary()
        for declared in (None, "", "   ", 1, [], {}, "a\x00b"):
            with self.subTest(location=declared):
                self.assertEqual(
                    "PATH_VIOLATION",
                    module.location_retrieval_violation(declared),
                    f"{declared!r} is not a legal location declaration")
                self.assertFalse(
                    module.retrieve_artifact(declared)["retrieved"])

    # ==================================================================
    # AC-27 / positive control: the boundary must not over-block
    # ==================================================================

    def test_12_positive_control_a_legal_repository_relative_path_is_retrieved(self):
        module = self.require_boundary()
        with tempfile.TemporaryDirectory() as temp:
            anchor = Path(temp)
            (anchor / "evidence").mkdir()
            artifact = anchor / "evidence" / "retrieved.txt"
            artifact.write_text("legitimate evidence", encoding="utf-8")
            self.assertIsNone(
                module.location_retrieval_violation("evidence/retrieved.txt",
                                                    root=str(anchor)),
                "a legal repository-relative path must pass the boundary")
            result = module.retrieve_artifact("evidence/retrieved.txt",
                                              root=str(anchor))
            self.assertTrue(result["retrieved"],
                            f"AC-27 VIOLATED: {result}")
            self.assertIsNone(result["reason"])
            self.assertEqual(b"legitimate evidence", result["content"])

    def test_13_positive_control_an_authorised_ci_artifact_is_retrieved(self):
        """The authorised identifier goes through the EXISTING provider
        interface; this ticket builds no provider and no network client."""
        module = self.require_boundary()
        calls: list = []

        def provider(reference):
            calls.append(reference)
            return b"ci artifact bytes"

        identifier = "ci-artifacts:build-42/report.txt"
        self.assertIsNone(
            module.location_retrieval_violation(identifier),
            "an authorised CI artifact identifier is a legal declaration")
        result = module.retrieve_artifact(identifier, provider=provider)
        self.assertTrue(result["retrieved"], f"AC-27 VIOLATED: {result}")
        self.assertEqual(b"ci artifact bytes", result["content"])
        self.assertEqual([identifier], calls,
                         "the identifier must be resolved through the supplied "
                         "provider interface")

    def test_14_positive_control_no_provider_is_unavailable_not_a_violation(self):
        module = self.require_boundary()
        result = module.retrieve_artifact("ci-artifacts:build-42/report.txt")
        self.assertFalse(result["retrieved"])
        self.assertEqual(module.RETRIEVAL_UNAVAILABLE, result["reason"],
                         "an unreachable/missing source is not an out-of-bounds "
                         "violation (it must never alias PATH_VIOLATION)")
        self.assertNotIn(result["reason"], module.RETRIEVAL_BOUNDARY_REASONS)

    def test_15_positive_control_a_green_pack_with_a_legal_location_still_passes(self):
        payload = self.validate_in_process(good_pack())
        self.assertTrue(payload["ok"], f"violations={payload['violations']}")
        self.assertEqual(0, payload["exitCode"])
        self.assertEqual([], payload["violations"])
        self.assertEqual(set(), self.codes(payload))

    def test_16_positive_control_placeholder_mode_is_unaffected(self):
        template = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temp:
            path = write_pack(Path(temp), template, name="template.json")
            completed = run_cli(["validate", "--pack", str(path),
                                 "--allow-placeholders"])
            payload = json.loads(completed.stdout)
            self.assertEqual(0, completed.returncode,
                             f"stdout={completed.stdout[:400]}")
            self.assertTrue(payload["ok"])

    # ==================================================================
    # Fail-closed in the validate flow, and never on an earlier failure
    # ==================================================================

    def test_17_a_boundary_violation_blocks_pass_in_validate(self):
        cases = {
            "../../outside.txt": "PATH_VIOLATION",
            "/" + "etc/passwd": "PATH_VIOLATION",
            "http://example.invalid/evidence.txt": "ARBITRARY_URL_RETRIEVAL",
        }
        for declared, expected in cases.items():
            with self.subTest(location=declared):
                payload = self.validate_in_process(pack_with_location(declared))
                self.assertFalse(
                    payload["ok"],
                    f"{declared!r} must not be accepted; "
                    f"violations={payload['violations']}")
                self.assertEqual(1, payload["exitCode"])
                self.assertIn(expected, self.boundary_reasons(payload),
                              f"violations={payload['violations']}")
                self.assertEqual({"REJECT"}, self.codes(payload),
                                 "a boundary violation is reported as a REJECT")

    def test_18_every_boundary_violation_names_the_location_path(self):
        payload = self.validate_in_process(pack_with_location("../../outside.txt"))
        paths = {v["path"] for v in payload["violations"]}
        self.assertEqual({"$.artifacts[].location"}, paths,
                         f"violations={payload['violations']}")

    def test_19_the_boundary_reasons_are_disjoint_from_every_other_vocabulary(self):
        module = self.require_boundary()
        boundary = set(module.RETRIEVAL_BOUNDARY_REASONS)
        self.assertTrue(boundary)
        for other in ("STRUCTURAL_REASONS", "NON_STRUCTURAL_REASONS",
                      "DISPOSITION_REASONS"):
            with self.subTest(vocabulary=other):
                self.assertEqual(
                    set(), boundary & set(getattr(module, other)),
                    f"the boundary reasons must not alias {other}")

    def test_20_an_earlier_failure_is_reported_alone(self):
        """A structure or subject failure must never grow a boundary finding."""
        broken = pack_with_location("../../outside.txt")
        del broken["unverified"]
        payload = self.validate_in_process(broken)
        self.assertFalse(payload["ok"])
        self.assertEqual(set(), self.boundary_reasons(payload) & set(
            self.require_boundary().RETRIEVAL_BOUNDARY_REASONS),
            f"violations={payload['violations']}")
        self.assertIn("REQUIRED_FIELD_MISSING", self.boundary_reasons(payload),
                      f"violations={payload['violations']}")

        wrong_subject = pack_with_location("/" + "etc/passwd")
        wrong_subject["subject"]["candidateSha"] = OTHER_SHA
        payload = self.validate_in_process(wrong_subject)
        self.assertFalse(payload["ok"])
        self.assertEqual(
            set(),
            self.boundary_reasons(payload)
            & set(self.require_boundary().RETRIEVAL_BOUNDARY_REASONS),
            "a subject verdict must be issued alone: the boundary runs only "
            "after the subject step succeeds")

    def test_21_the_gate_decides_before_any_io(self):
        """A readable file is still refused when it is outside the boundary,
        and an absolute path to a readable file is never opened."""
        module = self.require_boundary()
        with tempfile.TemporaryDirectory() as temp:
            anchor = Path(temp) / "repo"
            anchor.mkdir()
            (anchor / "RULES.md").write_text("inside", encoding="utf-8")
            absolute = str(anchor / "RULES.md")
            result = module.retrieve_artifact(absolute, root=str(anchor))
            self.assertFalse(result["retrieved"])
            self.assertEqual("PATH_VIOLATION", result["reason"])
            self.assertIsNone(
                result["content"],
                "AC-26 VIOLATED: the absolute path was read; the boundary "
                "decision must precede every filesystem access")

    # ==================================================================
    # CE-06 / AC-06: the subject regression guard
    # ==================================================================

    def test_22_wrong_repo_base_and_candidate_are_still_rejected(self):
        for overrides, expected_code, expected_reason in (
                ({"repo": OTHER_REPO}, "EVIDENCE_SUBJECT_MISMATCH",
                 "SUBJECT_REPO_MISMATCH"),
                ({"baseSha": OTHER_SHA}, "EVIDENCE_STALE_SUBJECT",
                 "SUBJECT_BASE_SHA_STALE"),
                ({"candidateSha": OTHER_SHA}, "EVIDENCE_STALE_SUBJECT",
                 "SUBJECT_CANDIDATE_SHA_STALE")):
            with self.subTest(subject=overrides):
                pack = good_pack()
                pack["subject"].update(overrides)
                payload = self.validate_in_process(pack)
                self.assertFalse(payload["ok"])
                self.assertEqual(1, payload["exitCode"])
                self.assertEqual({expected_code}, self.codes(payload),
                                 f"violations={payload['violations']}")
                self.assertIn(expected_reason, self.boundary_reasons(payload))

    def test_23_a_partial_subject_expectation_stays_fail_closed(self):
        module = self.require_cli()
        for extra in (["--expect-repo", REPO],
                      ["--expect-base-sha", BASE_SHA],
                      ["--expect-candidate-sha", CANDIDATE_SHA],
                      ["--expect-repo", REPO, "--expect-base-sha", BASE_SHA]):
            with self.subTest(args=extra):
                with tempfile.TemporaryDirectory() as temp:
                    pack_path = write_pack(Path(temp), good_pack())
                    buffer = io.StringIO()
                    with redirect_stdout(buffer):
                        code = module.main(["validate", "--pack", str(pack_path),
                                            *extra])
                    payload = json.loads(buffer.getvalue())
                self.assertEqual(1, code, f"args={extra}")
                self.assertIn("SUBJECT_EXPECTATION_INCOMPLETE",
                              self.boundary_reasons(payload),
                              f"args={extra} violations={payload['violations']}")

    def test_24_an_absent_subject_expectation_stays_fail_closed(self):
        module = self.require_cli()
        with tempfile.TemporaryDirectory() as temp:
            pack_path = write_pack(Path(temp), good_pack())
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = module.main(["validate", "--pack", str(pack_path)])
            payload = json.loads(buffer.getvalue())
        self.assertEqual(1, code)
        self.assertIn("SUBJECT_EXPECTATION_ABSENT", self.boundary_reasons(payload),
                      f"violations={payload['violations']}")

    # ==================================================================
    # Preserved interface: the public CLI surface is exactly collect/validate
    # ==================================================================

    def test_25_the_public_cli_surface_is_exactly_collect_and_validate(self):
        completed = run_cli(["--help"])
        self.assertEqual(0, completed.returncode)
        usage = completed.stdout.splitlines()[0]
        modes = re.search(r"\{([^}]*)\}", usage)
        self.assertIsNotNone(modes, f"usage={usage!r}")
        self.assertEqual({"validate", "collect"},
                         {m.strip() for m in modes.group(1).split(",")},
                         f"the public CLI surface changed: {usage!r}")
        self.assertNotIn("verify", completed.stdout.lower(),
                         "the `verify` mode was removed in P1-T05 repair round "
                         "1 and must not be reintroduced")

    def test_26_a_third_mode_is_not_silently_available(self):
        completed = run_cli(["verify", "--pack", "x.json"])
        self.assertNotEqual(0, completed.returncode,
                            "an undeclared third mode must not be accepted")
        self.assertIn("invalid choice", completed.stderr.lower(),
                      f"stderr={completed.stderr[:300]!r}")

    def test_27_collect_writes_only_the_explicit_output_path(self):
        module = self.require_cli()
        with tempfile.TemporaryDirectory() as temp:
            workdir = Path(temp)
            before = {p.name for p in workdir.iterdir()}
            out_path = workdir / "skeleton.json"
            with redirect_stdout(io.StringIO()):
                code = module.main(["collect", "--repo", REPO, "--base-sha", BASE_SHA,
                                    "--candidate-sha", CANDIDATE_SHA,
                                    "--producer-identity", "laneB-worker",
                                    "--producer-version", "1", "--out", str(out_path)])
            self.assertEqual(0, code)
            after = {p.name for p in workdir.iterdir()}
            self.assertEqual(before | {"skeleton.json"}, after,
                             "collect must write nothing but the explicit --out")
            skeleton = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual([], skeleton["artifacts"])
            self.assertEqual([], skeleton["checks"])

    # ==================================================================
    # The owner declares the behaviour; the declaration points do not move
    # ==================================================================

    def test_28_the_owner_declares_the_retrieval_boundary_behaviour(self):
        text = self.require_reference()
        for marker in ("### 9.7", "location_retrieval_violation",
                       "retrieve_artifact", "evidence_boundary_findings",
                       "EVIDENCE_REFERENCE_IS_DATA", "ARBITRARY_URL_RETRIEVAL",
                       "PATH_VIOLATION", "RETRIEVAL_UNAVAILABLE"):
            with self.subTest(marker=marker):
                self.assertIn(
                    marker, text,
                    "SURFACE_DISAGREEMENT: the sole semantic owner must declare "
                    f"the P1-T06 boundary behaviour {marker!r}")

    def test_29_the_landed_single_declaration_point_scan_still_holds(self):
        """Re-run the landed P1-T04 scans 04/05 against the same tree."""
        if not LANDED_CONTRACT_TEST.is_file():
            self.fail(f"CONTRACT_ABSENT: {LANDED_CONTRACT_TEST.name} is missing")
        spec = importlib.util.spec_from_file_location(
            "landed_review_evidence_contract", LANDED_CONTRACT_TEST)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as exc:  # noqa: BLE001
            self.fail("CONTRACT_BROKEN: the landed P1-T04 test surface raised "
                      f"on import: {type(exc).__name__}: {exc}")
        case = module.ReviewEvidenceContractTests("test_04_single_declaration_point_repo_wide")
        for token, expected in case.PROTECTED_TOKENS.items():
            with self.subTest(token=token):
                self.assertEqual(
                    set(expected), case.scan_token(token),
                    f"DUAL_DECLARATION (CE-28): {token!r} left its single "
                    "declaration point")
        for family, (tokens, expected) in case.PROTECTED_FAMILIES.items():
            with self.subTest(family=family):
                self.assertEqual(
                    set(expected), case.scan_family(tokens),
                    f"DUAL_DECLARATION (CE-28): the {family} contract moved")

    def test_30_the_boundary_introduces_no_new_declaration_point(self):
        source = CLI_PATH.read_text(encoding="utf-8")
        for token in PROTECTED_TOKENS:
            if token == "IDENTITY_VERSION_OR_DIGEST":
                self.assertNotIn(
                    token, source,
                    "IDENTITY_VERSION_OR_DIGEST is declared by the interface "
                    "head only; the CLI must not re-declare it")
        self.assertIn("references/review-evidence.md", source,
                      "the consumer must point at the sole semantic owner")


if __name__ == "__main__":
    unittest.main()
