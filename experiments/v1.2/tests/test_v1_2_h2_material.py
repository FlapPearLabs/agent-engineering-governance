"""Material checks for the H2 (Lazy Skill / Progressive Disclosure) experiment slice.

Pins, mechanically:

  * the freeze hashes in variant-manifest.json == the actual file bytes (freeze integrity);
  * routes-h2.json S1/S2 sections == the N8 frozen routes.json, route-for-route (no drift);
  * routes-h2.json S3 section == what a bounded extraction finds in the H2 carrier
    (zero routes is never a pass);
  * live validator runs at six distinct bases (H2 base = n02 base = 9494de8e) — P6: expected
    failing route sets are frozen; S3 (H2 carrier) rows are VALID at EVERY base;
  * the N8 frozen routes.json still validates 22/22 at the H2 base;
  * hostile-manifest re-checks: the PR #50 5xP2 hardening must stay closed under H2
    (directory target / unknown key / unhashable surface / zero routes / bad base / missing target);
  * run-plan.json <-> task-registry replication declaration consistency, arm-order
    counterbalance (no fixed control-first ordering), and the run ids appear in run-registry.md;
  * arm-block field parity (P4: same structured fields in both delivery blocks);
  * freeze cross-anchor: manifest hashes == literal constants below (a frozen-file change
    must update both the manifest and these literals; the final anchor is the merged commit).

Run:  python3 -m unittest discover -s experiments/v1.2/tests -v
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
H2 = ROOT / "experiments" / "v1.2" / "h2-lazy-disclosure"
RR = ROOT / "experiments" / "v1.2" / "route-reachability"
VALIDATOR = RR / "validate_routes.py"
ROUTES_H2 = H2 / "routes-h2.json"
FROZEN_ROUTES = RR / "routes.json"
MANIFEST = H2 / "variant-manifest.json"
CARRIER = H2 / "carriers" / "H2_LEAN_BOOTSTRAP.md"
RUN_PLAN = H2 / "harness" / "run-plan.json"
REGISTRY = H2 / "task-registry.json"
RUN_REGISTRY_MD = H2 / "run-registry.md"

BASE_T01 = "c08f6f8b3bbe57853a56adf3c2847e806bbb60a3"
BASE_T02 = "015780be7a3f863c05509b437e4e586b4f388794"
BASE_T03 = "af4df6ae706394db5f9dec313993312392aeb516"
BASE_T04 = "e1da1541eb2b11f1e44f972409abde701496f4b6"
BASE_N01 = "0a180fee4dca9800df1691990293adb083458226"
BASE_H2 = "9494de8e2d3bbc5c38b311e8cce29230e7574dce"

TASK_BASES = [BASE_T01, BASE_T02, BASE_T03, BASE_T04, BASE_N01, BASE_H2]

# Measured at freeze (P6, live runs). Historical dangling rows belong to S1/S2 only
# (N8-frozen facts); S3 must be fully valid at every base.
EXPECTED_FAILS_PER_BASE = {
    BASE_T01: [],
    BASE_T02: ["AGENTS-03", "LEAN-12"],
    BASE_T03: ["AGENTS-03", "LEAN-07", "LEAN-12"],
    BASE_T04: ["AGENTS-03", "LEAN-07", "LEAN-12"],
    BASE_N01: [],
    BASE_H2: [],
}

EXTRACTION_RE = re.compile(r"references/[a-z0-9-]+\.md|skills/README\.md")


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _run_validator(base: str, manifest: Path):
    cmd = [
        sys.executable,
        str(VALIDATOR),
        "--base",
        base,
        "--manifest",
        str(manifest),
        "--repo",
        str(ROOT),
        "--json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), check=False)
    payload = json.loads(proc.stdout) if proc.stdout.strip() else None
    return proc.returncode, payload


# Cross-anchor literals (bot review "Anchor freeze hashes outside the mutable freeze set"):
# changing a frozen file requires updating BOTH variant-manifest.json and these literals;
# neither alone stays silently consistent. The FINAL anchor is the merged commit chain
# (recorded in results.md section 8).
EXPECTED_FREEZE_LITERALS = {
    "VARIANT_HASH": "c5c8261591d70b21c167b1659e1d06cbb3f8f7d347b261180e321f6d6b0c932b",
    "TASK_SET_HASH": "dc007457217f767e50e20633db616c0d424c3dc416b0ff9f87b2b4ce7c5eefd4",
    "SCORING_HASH": "961a49b1f635542bd78990de5ddef8e45899059ba4f993f5025c44bbd915223b",
    "ROUTE_MANIFEST_HASH": "a9d0e61dc85fe4bead5d993ddc0bb805e683bdea88d6c36c3aecdd5653304636",
    "PROTOCOL_HASH": "e46ac8226cc82ed42222aa743c0de2e34923928c5128274781c3431873e7bc59",
}


class FreezeHashes(unittest.TestCase):
    def test_variant_manifest_hashes_match_files(self):
        freeze = json.loads(_read(MANIFEST))["freeze"]
        pairs = {
            "VARIANT_HASH": CARRIER,
            "TASK_SET_HASH": REGISTRY,
            "SCORING_HASH": H2 / "scoring-rubric.md",
            "ROUTE_MANIFEST_HASH": ROUTES_H2,
        }
        for key, path in pairs.items():
            got = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(freeze[key], got, f"{key} stale for {path}")

    def test_manifest_matches_test_literals(self):
        freeze = json.loads(_read(MANIFEST))["freeze"]
        for key, want in EXPECTED_FREEZE_LITERALS.items():
            self.assertEqual(freeze[key], want, f"{key}: manifest vs test-literal mismatch")

    def test_manifest_hot_metrics_match_live_inventory(self):
        proc = subprocess.run(
            [sys.executable, str(H2 / "h2_hot_inventory.py"), "--json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        self.assertEqual(0, proc.returncode, proc.stderr[-800:])
        inv = json.loads(proc.stdout)
        m = json.loads(_read(MANIFEST))["hot_metrics"]["observed_at_freeze_at_H2_base"]
        self.assertEqual(m["CONTROL_CARRIER_JS_CHARS"], inv["reduction"]["carrier_js_chars_control"])
        self.assertEqual(m["VARIANT_CARRIER_JS_CHARS"], inv["reduction"]["carrier_js_chars_variant"])
        self.assertEqual(m["CARRIER_REDUCTION_PERCENT"], inv["reduction"]["carrier_reduction_percent"])

    def test_protocol_hash_is_frozen(self):
        freeze = json.loads(_read(MANIFEST))["freeze"]
        got = hashlib.sha256((H2 / "protocol.md").read_bytes()).hexdigest()
        self.assertEqual(freeze["PROTOCOL_HASH"], got, "protocol.md changed after freeze")


class RouteManifestIntegrity(unittest.TestCase):
    def test_s1_s2_sections_equal_frozen_n8_manifest(self):
        h2_routes = json.loads(_read(ROUTES_H2))["routes"]
        frozen = json.loads(_read(FROZEN_ROUTES))["routes"]

        def triples(rs):
            return sorted(
                (r["route_id"], r.get("surface"), r["destination"]) for r in rs
            )

        inherited = [r for r in h2_routes if r.get("surface") in ("S1", "S2")]
        self.assertEqual(triples(inherited), triples(frozen))

    def test_s3_equals_carrier_extraction(self):
        h2_routes = json.loads(_read(ROUTES_H2))["routes"]
        s3 = {r["destination"] for r in h2_routes if r.get("surface") == "S3"}
        extracted = set(EXTRACTION_RE.findall(_read(CARRIER)))
        self.assertTrue(s3, "S3 must be non-empty: zero routes is never a pass")
        self.assertEqual(s3, extracted)

    def test_live_validation_at_all_six_bases(self):
        for base, expected_fails in EXPECTED_FAILS_PER_BASE.items():
            rc, payload = _run_validator(base, ROUTES_H2)
            self.assertIsNotNone(payload, f"no payload at {base}")
            self.assertEqual(payload["routes_declared"], 33, base)
            fails = sorted(
                r["route_id"] for r in payload["routes"] if r["result"] != "VALID"
            )
            self.assertEqual(fails, expected_fails, f"failing set changed at {base}")
            s3_rows = [r for r in payload["routes"] if r["route_id"].startswith("H2-")]
            self.assertEqual(len(s3_rows), 11, base)
            self.assertTrue(
                all(r["result"] == "VALID" for r in s3_rows),
                f"S3 (H2 carrier) rows must be valid at {base}",
            )

    def test_frozen_n8_manifest_still_22_of_22_at_h2_base(self):
        rc, payload = _run_validator(BASE_H2, FROZEN_ROUTES)
        self.assertEqual(rc, 0)
        self.assertEqual(payload["routes_declared"], 22)
        self.assertEqual(payload["routes_valid"], 22)
        self.assertEqual(payload["verdict"], "ALL_ROUTES_VALID")


class HostileManifestReChecks(unittest.TestCase):
    """PR #50 5xP2 hardening must stay closed when run under the H2 slice."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def _write(self, body) -> Path:
        path = self.tmpdir / "manifest.json"
        if isinstance(body, str):
            path.write_text(body, encoding="utf-8")
        else:
            path.write_text(json.dumps(body), encoding="utf-8")
        return path

    def test_directory_destination_is_not_a_file(self):
        path = self._write({"routes": [{"route_id": "x", "destination": "references"}]})
        rc, payload = _run_validator(BASE_H2, path)
        self.assertEqual(rc, 1)
        result = payload["routes"][0]
        self.assertEqual(result["result"], "DESTINATION_NOT_A_FILE")
        self.assertEqual(result["object_type"], "tree")

    def test_unknown_route_key_fails_closed(self):
        path = self._write(
            {"routes": [{"route_id": "x", "destination": "AGENTS.md", "anchro": "typo"}]}
        )
        rc, payload = _run_validator(BASE_H2, path)
        self.assertEqual(rc, 2)
        self.assertEqual(payload["verdict"], "MALFORMED_MANIFEST")

    def test_unhashable_surface_fails_closed(self):
        path = self._write(
            {"routes": [{"route_id": "x", "destination": "AGENTS.md", "surface": ["S1"]}]}
        )
        rc, payload = _run_validator(BASE_H2, path)
        self.assertEqual(rc, 2)
        self.assertEqual(payload["verdict"], "MALFORMED_MANIFEST")

    def test_zero_routes_never_passes(self):
        path = self._write({"routes": []})
        rc, payload = _run_validator(BASE_H2, path)
        self.assertEqual(rc, 3)
        self.assertEqual(payload["verdict"], "NO_ROUTES_DECLARED")
        self.assertEqual(payload["h2_precondition"], "FAIL")

    def test_unresolvable_base_fails_closed(self):
        rc, payload = _run_validator("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef", ROUTES_H2)
        self.assertEqual(rc, 4)
        self.assertEqual(payload["verdict"], "BASE_UNRESOLVABLE")

    def test_missing_target_fails(self):
        path = self._write(
            {"routes": [{"route_id": "x", "destination": "references/no-such-file-9f3.md"}]}
        )
        rc, payload = _run_validator(BASE_H2, path)
        self.assertEqual(rc, 1)
        self.assertEqual(payload["routes"][0]["result"], "DESTINATION_MISSING")


class RunPlanConsistency(unittest.TestCase):
    EXPECTED_PER_TASK_PER_ARM = {"t01": 1, "t02": 1, "t03": 2, "t04": 2, "n01": 2, "n02": 2}

    def test_plan_matches_replication_declaration(self):
        plan = json.loads(_read(RUN_PLAN))
        self.assertEqual(len(plan), 20)
        ids = [r["run_id"] for r in plan]
        self.assertEqual(len(set(ids)), 20)

        per_task_arm: dict[tuple[str, str], int] = {}
        per_shape_arm: dict[tuple[str, str], int] = {}
        shape_of_task = {}
        reg = json.loads(_read(REGISTRY))
        for shape in reg["replication"]["shapes"]:
            for t in shape["tasks"]:
                shape_of_task[t] = shape["shape_id"]
        for r in plan:
            key = (r["task_id"], r["arm"])
            per_task_arm[key] = per_task_arm.get(key, 0) + 1
            skey = (shape_of_task[r["task_id"]], r["arm"])
            per_shape_arm[skey] = per_shape_arm.get(skey, 0) + 1

        for task, n in self.EXPECTED_PER_TASK_PER_ARM.items():
            for arm in ("control", "variant"):
                self.assertEqual(per_task_arm.get((task, arm), 0), n, f"{task}/{arm}")

        shape_ids = [s["shape_id"] for s in reg["replication"]["shapes"]]
        for sid in shape_ids:
            for arm in ("control", "variant"):
                self.assertEqual(per_shape_arm.get((sid, arm), 0), 2, f"{sid}/{arm}")

    def test_arm_order_is_counterbalanced(self):
        plan = json.loads(_read(RUN_PLAN))
        first_per = {}
        for r in plan:
            first_per.setdefault((r["task_id"], r["rep"]), r["arm"])
        for task in ("t03", "t04", "n01", "n02"):
            self.assertNotEqual(
                first_per[(task, 1)], first_per[(task, 2)],
                f"{task}: the two repetitions must start with different arms",
            )
        self.assertNotEqual(
            first_per[("t01", 1)], first_per[("t02", 1)],
            "t01/t02 (single-rep) must alternate their first arm across tasks",
        )

    def test_run_ids_appear_in_run_registry_md(self):
        text = _read(RUN_REGISTRY_MD)
        plan = json.loads(_read(RUN_PLAN))
        for r in plan:
            self.assertIn(r["run_id"], text, f"{r['run_id']} missing from run-registry.md")

    def test_task_bases_are_resolvable_and_ancestors_of_head(self):
        for base in TASK_BASES:
            proc = subprocess.run(
                ["git", "-C", str(ROOT), "merge-base", "--is-ancestor", base, "HEAD"],
                capture_output=True,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, f"{base} is not an ancestor of HEAD")


class ArmBlockParity(unittest.TestCase):
    def test_blocks_share_structured_receipt_fields(self):
        control = _read(H2 / "harness" / "arm-blocks" / "control.md")
        variant = _read(H2 / "harness" / "arm-blocks" / "variant.md")
        for tok in ("H2_RECEIPT = S0:", "S1:", "S2:", "S3:", "S4:"):
            self.assertIn(tok, control)
            self.assertIn(tok, variant)
        for text in (control, variant):
            self.assertIn("H2_RULES.md", text)
            self.assertIn("CODEBUDDY.md", text)
            self.assertIn("H2_WARM", text)

    def test_plan_model_tier_is_uniform(self):
        plan = json.loads(_read(RUN_PLAN))
        tiers = {r.get("model_tier") for r in plan}
        self.assertEqual({"default"}, tiers, "all runs must be frozen to one model tier")

    def test_report_template_declares_shared_fields(self):
        tpl = _read(H2 / "harness" / "worker-report-template.md")
        for tok in (
            "H2_RECEIPT",
            "S0:",
            "FILES_FULLY_READ",
            "FILES_PARTIAL_READ",
            "FILES_GREPPED_FOUND",
            "ROUTES_USED",
            "SKILLS_LOADED",
            "TOKEN_USAGE",
        ):
            self.assertIn(tok, tpl)


if __name__ == "__main__":
    unittest.main()
