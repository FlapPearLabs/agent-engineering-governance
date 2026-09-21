#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P1-T15 — guard exit-code contract + adapter deny-mapping contract (synthetic).

REQ-W4-03 (S1 core half) / AC-18 / CE-20 (core facet) / CE-27 / INV-17.

Contract under test (grounding_guard.py, contract layer added by P1-T15):

  exit 0  = ALLOW
  exit 2  = REQUEST_BLOCK — a REQUEST is NOT proof of enforcement
  ENFORCED  = the runtime maps the block request to an actual host deny, and a
              VERIFIABLE deny-mapping registry exists (machine-readable JSON)
  ADVISORY  = no verifiable deny mapping exists; the hook only makes the
              omission mechanically visible; the authoritative gate remains
              the orchestrator discipline — an honest ADVISORY is LEGAL
  NOT_RUN   = the live host deny verification (REQ-W4-03-D / AC-18-D, W5,
              DEPLOYMENT_ONLY) has not been performed — NOT_RUN is never PASS

Fail-closed counterexamples (each maps to a test below):
  CE-27a  adapter claims ENFORCED with no deny-mapping registry  -> rejected
  CE-27b  degraded (unverifiable) registry + ENFORCED claim      -> rejected
  CE-20   hook prints BLOCK but no host deny mapping exists -> the BLOCK
          print is NOT enforcement evidence (status stays ADVISORY)
  malformed / missing / wrong-exit-code / non-DENY registry       -> ADVISORY

These are synthetic / reference-level tests only: no real host, no network,
no live runtime events. The live half (real tool event -> block -> host deny
-> target unchanged) belongs to REQ-W4-03-D / W5 and is reported NOT_RUN here,
never PASS.

Run:  python3 -m unittest adapters.zcode.tests.test_p1_t15_guard_deny_mapping
  or  python3 -m unittest discover -s adapters/zcode/tests
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
HOOKS = HERE.parent / "hooks"
GROUND_GUARD = str(HOOKS / "grounding_guard.py")

# Import the guard module for the contract layer (hooks dir on sys.path so the
# sibling shared module _continuity_state resolves).
if str(HOOKS) not in sys.path:
    sys.path.insert(0, str(HOOKS))
import grounding_guard as gg  # noqa: E402

REGISTRY_ENV = "ZCODE_DENY_MAPPING_REGISTRY"


def valid_registry(**overrides):
    """A structurally verifiable deny-mapping registry payload."""
    payload = {
        "deny_mapping_version": 1,
        "adapter": "zcode",
        "hook": "grounding_guard.py",
        "allow_exit_code": 0,
        "request_block_exit_code": 2,
        "host_decision_on_request_block": "DENY",
        "recorded_at": "2026-09-20T00:00:00Z",
        "recorded_by": "synthetic-deployment-reference",
    }
    payload.update(overrides)
    return payload


def env_with(registry_path=None):
    """Explicit env mapping for the contract functions (hermetic, no ambient)."""
    env = {}
    if registry_path is not None:
        env[REGISTRY_ENV] = str(registry_path)
    return env


def hook_env(tmp_root):
    """Hermetic env for subprocess runs of the guard hook."""
    env = os.environ.copy()
    env["ZCODE_RUNTIME_STATE_DIR"] = str(Path(tmp_root) / "runtime-state")
    env.pop("ZCODE_PROJECT_DIR", None)
    env.pop("ZCODE_TICKET_RISK", None)
    env.pop(REGISTRY_ENV, None)
    return env


class P1T15Base(unittest.TestCase):
    """Shared fixtures. Self-contained: no docs mkdir, no git repo, no network."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="p1t15-"))
        self.addCleanup(_rmtree, self.tmp)

    def guard_attr(self, name):
        """RED helper: a missing contract symbol is a test FAILURE (not a
        harness error) — it proves the contract layer is absent on the base."""
        attr = getattr(gg, name, None)
        if attr is None:
            self.fail(
                "RED (REQ-W4-03 S1 core): grounding_guard exposes no %r — the "
                "exit-code / deny-mapping contract layer is not implemented on "
                "this base" % name)
        return attr

    def write_registry(self, payload):
        path = self.tmp / "deny-mapping.json"
        path.write_text(json.dumps(payload, indent=1), encoding="utf-8")
        return path

    def run_guard(self, *flags):
        src = self.tmp / "src"
        src.mkdir(exist_ok=True)
        target = src / "app.py"
        if not target.exists():
            target.write_text("def main():\n    pass\n", encoding="utf-8")
        args = [sys.executable, GROUND_GUARD] + list(flags)
        return subprocess.run(
            args, cwd=str(self.tmp), env=hook_env(self.tmp),
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            timeout=30, errors="replace")


def _rmtree(path):
    import shutil
    shutil.rmtree(path, ignore_errors=True)


class ExitCodeContractUnchanged(P1T15Base):
    """Positive control — the hook's own exit codes and decision lines are
    byte-compatible with the pre-P1-T15 behaviour (ticket hard constraint)."""

    def test_block_case_exit_2_and_decision_line(self):
        r = self.run_guard("--file", "src/app.py", "--risk", "HIGH")
        self.assertEqual(r.returncode, 2,
                         "exit 2 = REQUEST_BLOCK must stay unchanged; stderr=%r stdout=%r"
                         % (r.stderr, r.stdout))
        self.assertIn("GROUNDING_GUARD_DECISION=BLOCK", r.stdout)
        self.assertIn("CODEGRAPH_GROUNDING_REQUIRED", r.stdout)

    def test_allow_case_exit_0_and_decision_line(self):
        r = self.run_guard("--file", "src/app.py", "--risk", "LOW")
        self.assertEqual(r.returncode, 0,
                         "exit 0 = ALLOW must stay unchanged; stderr=%r stdout=%r"
                         % (r.stderr, r.stdout))
        self.assertIn("GROUNDING_GUARD_DECISION=ALLOW", r.stdout)

    def test_module_exit_code_constants_match_contract(self):
        self.assertEqual(self.guard_attr("ALLOW_EXIT_CODE"), 0)
        self.assertEqual(self.guard_attr("REQUEST_BLOCK_EXIT_CODE"), 2)


class StatusDerivationFailClosed(P1T15Base):
    """The status derivation is fail-closed: an unverifiable / malformed /
    missing mapping can NEVER yield ENFORCED."""

    def test_no_registry_at_all_is_advisory(self):
        status = self.guard_attr("runtime_status")
        result = status(env_with(None))
        self.assertEqual(result["status"], "ADVISORY",
                         "no mapping recorded -> honest ADVISORY (legal state)")
        self.assertIsNone(result["mapping"])

    def test_missing_registry_file_is_advisory(self):
        status = self.guard_attr("runtime_status")
        result = status(env_with(self.tmp / "nope.json"))
        self.assertEqual(result["status"], "ADVISORY")

    def test_malformed_json_registry_is_advisory(self):
        path = self.tmp / "broken.json"
        path.write_text("{not json", encoding="utf-8")
        result = self.guard_attr("runtime_status")(env_with(path))
        self.assertEqual(result["status"], "ADVISORY")

    def test_registry_missing_required_field_is_advisory(self):
        payload = valid_registry()
        del payload["request_block_exit_code"]
        result = self.guard_attr("runtime_status")(env_with(self.write_registry(payload)))
        self.assertEqual(result["status"], "ADVISORY")

    def test_registry_with_wrong_exit_codes_is_advisory(self):
        result = self.guard_attr("runtime_status")(
            env_with(self.write_registry(valid_registry(request_block_exit_code=1))))
        self.assertEqual(result["status"], "ADVISORY")
        result = self.guard_attr("runtime_status")(
            env_with(self.write_registry(valid_registry(allow_exit_code="0"))))
        self.assertEqual(result["status"], "ADVISORY")

    def test_registry_with_non_deny_host_decision_is_advisory(self):
        result = self.guard_attr("runtime_status")(
            env_with(self.write_registry(
                valid_registry(host_decision_on_request_block="ALLOW"))))
        self.assertEqual(result["status"], "ADVISORY")

    def test_registry_not_binding_this_hook_is_advisory(self):
        result = self.guard_attr("runtime_status")(
            env_with(self.write_registry(valid_registry(hook="some_other_hook.py"))))
        self.assertEqual(result["status"], "ADVISORY")

    def test_verifiable_registry_yields_enforced(self):
        result = self.guard_attr("runtime_status")(env_with(self.write_registry(valid_registry())))
        self.assertEqual(result["status"], "ENFORCED")
        self.assertIsInstance(result["mapping"], dict)


class CounterexamplesCE20_CE27(P1T15Base):
    """CE-20 (core facet) + CE-27 — the RED inputs from the ticket."""

    def test_ce27a_enforced_claim_without_mapping_is_rejected(self):
        check = self.guard_attr("check_adapter_claim")
        accepted, reason = check({"adapter": "zcode", "status": "ENFORCED"},
                                 env_with(None))
        self.assertFalse(accepted,
                         "ENFORCED claim with no deny mapping is a contract "
                         "violation (CE-27) and must be rejected")
        self.assertTrue(reason)

    def test_ce27b_degraded_registry_recorded_enforced_is_rejected(self):
        # A registry that exists but fails verification (missing field) is a
        # DEGRADED adapter; recording it as ENFORCED must be rejected.
        payload = valid_registry()
        del payload["host_decision_on_request_block"]
        check = self.guard_attr("check_adapter_claim")
        accepted, reason = check({"adapter": "zcode", "status": "ENFORCED"},
                                 env_with(self.write_registry(payload)))
        self.assertFalse(accepted,
                         "a degraded (unverifiable) adapter recorded as ENFORCED "
                         "must be rejected (CE-27)")
        self.assertTrue(reason)

    def test_ce20_block_print_is_not_enforcement_evidence(self):
        # The guard prints BLOCK and exits 2, but no host deny mapping exists:
        # the script print is NOT proof the action was denied.
        r = self.run_guard("--file", "src/app.py", "--risk", "HIGH")
        self.assertEqual(r.returncode, 2)
        self.assertIn("GROUNDING_GUARD_DECISION=BLOCK", r.stdout)
        check = self.guard_attr("check_adapter_claim")
        accepted, _reason = check({"adapter": "zcode", "status": "ENFORCED"},
                                  env_with(None))
        self.assertFalse(accepted,
                         "a script printing BLOCK without a host deny is NOT "
                         "enforcement evidence (CE-20 core facet)")
        result = self.guard_attr("runtime_status")(env_with(None))
        self.assertNotEqual(result["status"], "ENFORCED")

    def test_unknown_or_missing_claim_status_is_rejected(self):
        check = self.guard_attr("check_adapter_claim")
        for claim in ({}, {"status": ""}, {"status": "SOMETHING_ELSE"}):
            accepted, _reason = check(claim, env_with(None))
            self.assertFalse(accepted,
                             "fail-closed: unknown/missing claim status %r must "
                             "be rejected" % (claim,))


class LiveVerificationNotRun(P1T15Base):
    """REQ-W4-03-D / AC-18-D is NOT part of this ticket: the live host deny
    verification is NOT_RUN, and NOT_RUN is never PASS — no S1 input may
    flip it (fail-closed against fake live claims)."""

    def test_live_verification_is_not_run_without_registry(self):
        lv = self.guard_attr("live_verification_status")
        self.assertEqual(lv(env_with(None)), "NOT_RUN")

    def test_live_verification_is_not_run_even_with_verifiable_registry(self):
        lv = self.guard_attr("live_verification_status")
        self.assertEqual(lv(env_with(self.write_registry(valid_registry()))),
                         "NOT_RUN")

    def test_live_verification_cannot_be_flipped_by_registry_fields(self):
        # A registry claiming a live verification happened must NOT produce
        # PASS/ENFORCED at the S1 contract layer — W5 owns the only upgrade.
        lv = self.guard_attr("live_verification_status")
        payload = valid_registry(
            live_verification={"performed": True, "evidence": "self-claimed"})
        self.assertEqual(lv(env_with(self.write_registry(payload))), "NOT_RUN")
        self.assertNotIn(lv(env_with(self.write_registry(payload))),
                         ("PASS", "ENFORCED"))


class PositiveControlsLegalStates(P1T15Base):
    """The honest states the contract must ACCEPT."""

    def test_honest_advisory_claim_without_mapping_is_legal(self):
        check = self.guard_attr("check_adapter_claim")
        accepted, _reason = check({"adapter": "zcode", "status": "ADVISORY"},
                                  env_with(None))
        self.assertTrue(accepted,
                        "an adapter with no mapping that declares ADVISORY "
                        "honestly is legal")

    def test_enforced_claim_with_verifiable_mapping_is_accepted(self):
        check = self.guard_attr("check_adapter_claim")
        accepted, _reason = check({"adapter": "zcode", "status": "ENFORCED"},
                                  env_with(self.write_registry(valid_registry())))
        self.assertTrue(accepted,
                        "a verifiable deny mapping makes the ENFORCED claim "
                        "derivable (still synthetic-level, live half = W5)")

    def test_runtime_status_reports_not_run_for_live_dimension(self):
        result = self.guard_attr("runtime_status")(env_with(None))
        self.assertEqual(result.get("live_verification"), "NOT_RUN",
                         "the live-host dimension must be reported NOT_RUN, "
                         "never PASS, by this ticket")


if __name__ == "__main__":
    unittest.main()
