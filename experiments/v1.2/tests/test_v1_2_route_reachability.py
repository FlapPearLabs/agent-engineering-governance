"""Controls and material checks for the N8 (#46) route-reachability mechanism.

This suite is the falsifiability evidence for the validator itself: a check that
cannot fail is not a check (issue #45's lesson, applied at the disclosure layer).

Controls (the N8 mandate lists T1-T7; T6b/T8/T9 close the set):

  T1  valid route + existing target   -> VALID
  T2  missing target                  -> FAIL (DESTINATION_MISSING)
  T3  zero declared routes            -> NO_ROUTES_DECLARED; never a pass
  T4  historical base e1da154         -> FAIL   [the issue #46 instance]
  T5  later base, same target         -> VALID  (base-relative, not HEAD-only)
  T6  declared anchor missing         -> FAIL (ANCHOR_MISSING)
  T6b declared anchor present         -> VALID
  T7  no declared anchor              -> destination-only VALID
  T8  malformed declarations          -> fail closed, exit 2
  T9  unresolvable base               -> fail closed, exit 4

Plus structural tests that give the manifest a mechanical owner:

  * the manifest's two route sets equal what a bounded extraction finds in the
    two declared carriers (manifest <-> carrier cross-check; a carrier edit that
    adds or removes a references path must fail here until the manifest is
    updated deliberately);
  * the README's ROUTE_RESULT_MATRIX block is re-derived from a LIVE validator
    run at every base it lists (README numbers are owned by the validator).

Base SHAs used below are frozen git facts (all ancestors of main). They are
asserted here so that a rewritten or re-fetched history cannot silently change
what the checks claim:

  e1da1541...  t04 replay base  -- references/ has 10 files; review-evidence.md
                                    and static-tooling-profiles.md are ABSENT
  c08f6f8b...  t01 replay base  -- references/ has 12 files
  6217cc0a...  current main     -- references/ has 12 files

Stdlib only. Run with:
    python3 -m unittest discover -s experiments/v1.2/tests -v
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
RR = ROOT / "experiments" / "v1.2" / "route-reachability"
MANIFEST = RR / "routes.json"
VALIDATOR = RR / "validate_routes.py"
README = RR / "README.md"
LEAN_CARRIER = ROOT / "experiments" / "v1.2" / "h1-hot-context" / "lean" / "CODEBUDDY.md"
AGENTS = ROOT / "AGENTS.md"

BASE_E1DA154 = "e1da1541eb2b11f1e44f972409abde701496f4b6"
BASE_C08F6F8 = "c08f6f8b3bbe57853a56adf3c2847e806bbb60a3"
BASE_MAIN = "6217cc0adcd6c064e8c74e670de6a081bdaba2f6"

# Bounded extraction used for the manifest <-> carrier cross-check. This is
# intentionally the same shape the manifest uses (repo-relative references/*.md).
ROUTE_PATH_RE = re.compile(r"references/[a-z0-9-]+\.md")

# First heading of references/execution-stage.md at main; a literal, verified
# substring used only for the anchor-positive control (T6b). No real route
# currently declares an anchor -- see the README for why.
ANCHOR_PRESENT_LITERAL = "# REF: Execution Stage"

EXPECTED_E1DA154_FAILURES = {"LEAN-07", "LEAN-12", "AGENTS-03"}


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run_validator(base, manifest=None, as_json=True, extra=()):
    """Run the validator; return (returncode, stdout, parsed-json-or-None)."""
    cmd = [
        sys.executable,
        str(VALIDATOR),
        "--base",
        base,
        "--manifest",
        str(manifest or MANIFEST),
        "--repo",
        str(ROOT),
    ]
    if as_json:
        cmd.append("--json")
    cmd.extend(extra)
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), check=False)
    payload = None
    if as_json and proc.stdout.strip():
        payload = json.loads(proc.stdout)
    return proc.returncode, proc.stdout, payload


def _manifest_routes() -> list[dict]:
    return json.loads(_read(MANIFEST))["routes"]


class SyntheticManifests(unittest.TestCase):
    """Scratch manifests for validator-semantics controls; never route evidence."""

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


class TestRouteContractControls(SyntheticManifests):
    """T1/T2/T3/T6/T6b/T7/T8/T9: validator semantics on synthetic inputs."""

    def test_t1_valid_route_and_existing_target_is_valid(self):
        m = self._write({"routes": [{"route_id": "T1", "destination": "references/execution-stage.md"}]})
        code, _out, payload = _run_validator(BASE_MAIN, manifest=m)
        self.assertEqual(0, code)
        self.assertEqual("ALL_ROUTES_VALID", payload["verdict"])
        self.assertEqual("VALID", payload["routes"][0]["result"])
        self.assertTrue(payload["routes"][0]["loadable"])

    def test_t2_missing_target_fails(self):
        m = self._write({"routes": [{"route_id": "T2", "destination": "references/no-such-file.md"}]})
        code, _out, payload = _run_validator(BASE_MAIN, manifest=m)
        self.assertEqual(1, code)
        self.assertEqual("ROUTES_UNSATISFIED", payload["verdict"])
        self.assertEqual("DESTINATION_MISSING", payload["routes"][0]["result"])
        self.assertFalse(payload["routes"][0]["destination_exists"])

    def test_t3_zero_routes_is_never_a_pass(self):
        m = self._write({"routes": []})
        code, out, _payload = _run_validator(BASE_MAIN, manifest=m, as_json=False)
        self.assertNotEqual(0, code, "zero routes must not exit 0")
        self.assertEqual(3, code)
        self.assertIn("VERDICT = NO_ROUTES_DECLARED", out)
        self.assertNotIn("ALL_ROUTES_VALID", out, "empty must never read as all-valid")
        self.assertIn("H2_PRECONDITION = FAIL", out)

    def test_t6_declared_anchor_missing_fails(self):
        m = self._write(
            {
                "routes": [
                    {
                        "route_id": "T6",
                        "destination": "references/execution-stage.md",
                        "anchor": "NO_SUCH_ANCHOR_LITERAL_7f3c",
                    }
                ]
            }
        )
        code, _out, payload = _run_validator(BASE_MAIN, manifest=m)
        self.assertEqual(1, code)
        row = payload["routes"][0]
        self.assertTrue(row["destination_exists"])
        self.assertFalse(row["anchor_exists"])
        self.assertEqual("ANCHOR_MISSING", row["result"])

    def test_t6b_declared_anchor_present_is_valid(self):
        m = self._write(
            {
                "routes": [
                    {
                        "route_id": "T6b",
                        "destination": "references/execution-stage.md",
                        "anchor": ANCHOR_PRESENT_LITERAL,
                    }
                ]
            }
        )
        code, _out, payload = _run_validator(BASE_MAIN, manifest=m)
        self.assertEqual(0, code)
        row = payload["routes"][0]
        self.assertTrue(row["anchor_exists"])
        self.assertEqual("VALID", row["result"])

    def test_t7_undeclared_anchor_checks_destination_only(self):
        m = self._write({"routes": [{"route_id": "T7", "destination": "references/ticket-lane.md"}]})
        code, _out, payload = _run_validator(BASE_MAIN, manifest=m)
        self.assertEqual(0, code)
        row = payload["routes"][0]
        self.assertIsNone(row["anchor"])
        self.assertIsNone(row["anchor_exists"])
        self.assertEqual("VALID", row["result"])

    def test_t8_malformed_declarations_fail_closed(self):
        cases = {
            "route_not_object": {"routes": ["LEAN-01"]},
            "missing_destination": {"routes": [{"route_id": "X1"}]},
            "duplicate_route_id": {
                "routes": [
                    {"route_id": "X1", "destination": "references/ticket-lane.md"},
                    {"route_id": "X1", "destination": "references/ticket-lane.md"},
                ]
            },
            "routes_not_a_list": {"routes": {"route_id": "X1"}},
            "unknown_surface": {
                "surfaces": [{"surface_id": "S1"}],
                "routes": [
                    {"route_id": "X1", "surface": "S9", "destination": "references/ticket-lane.md"}
                ],
            },
            "path_traversal": {"routes": [{"route_id": "X1", "destination": "../outside.md"}]},
            "absolute_path": {"routes": [{"route_id": "X1", "destination": "/etc/passwd"}]},
        }
        for name, body in cases.items():
            with self.subTest(case=name):
                m = self._write(body)
                code, _out, payload = _run_validator(BASE_MAIN, manifest=m)
                self.assertEqual(2, code, f"{name} must fail closed with exit 2")
                self.assertEqual("MALFORMED_MANIFEST", payload["verdict"])
                self.assertEqual("FAIL", payload["h2_precondition"])

    def test_t8b_manifest_that_is_not_json_fails_closed(self):
        m = self._write("{not json at all")
        code, _out, payload = _run_validator(BASE_MAIN, manifest=m)
        self.assertEqual(2, code)
        self.assertEqual("MALFORMED_MANIFEST", payload["verdict"])

    def test_t9_unresolvable_base_fails_closed(self):
        m = self._write({"routes": [{"route_id": "T9", "destination": "references/ticket-lane.md"}]})
        code, _out, payload = _run_validator("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef", manifest=m)
        self.assertEqual(4, code)
        self.assertEqual("BASE_UNRESOLVABLE", payload["verdict"])
        self.assertIsNone(payload["base_sha"])

    def test_base_is_mandatory(self):
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--json"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
            check=False,
        )
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("--base", proc.stderr)

    def test_abbreviated_base_resolves_to_full_sha(self):
        m = self._write({"routes": [{"route_id": "T10", "destination": "references/ticket-lane.md"}]})
        code, _out, payload = _run_validator("6217cc0", manifest=m)
        self.assertEqual(0, code)
        self.assertEqual(BASE_MAIN, payload["base_sha"], "output must be base-attributed")


class TestBaseRelativeResults(unittest.TestCase):
    """The mechanism's real-data controls, at the three frozen bases."""

    def test_all_routes_valid_at_current_main(self):
        code, _out, payload = _run_validator(BASE_MAIN)
        self.assertEqual(0, code)
        self.assertEqual("ALL_ROUTES_VALID", payload["verdict"])
        self.assertEqual(payload["routes_declared"], payload["routes_valid"])
        self.assertGreater(payload["routes_declared"], 0)
        for row in payload["routes"]:
            with self.subTest(route=row["route_id"]):
                self.assertEqual("VALID", row["result"])

    def test_all_routes_valid_at_t01_base(self):
        code, _out, payload = _run_validator(BASE_C08F6F8)
        self.assertEqual(0, code)
        self.assertEqual("ALL_ROUTES_VALID", payload["verdict"])

    def test_the_46_instance_is_rejected_at_its_historical_base(self):
        """T4: the original issue #46 facts, mechanically re-established.

        review-evidence.md exists in the WORKING TREE while this test runs; the
        validator must still report DESTINATION_MISSING because it resolves
        against the declared base (e1da154), not against HEAD or the worktree.
        A validator that passed this would be testing the wrong object.
        """
        m = {"routes": [{"route_id": "T4", "destination": "references/review-evidence.md"}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text(json.dumps(m), encoding="utf-8")
            code, _out, payload = _run_validator(BASE_E1DA154, manifest=path)
        self.assertEqual(1, code)
        self.assertEqual("DESTINATION_MISSING", payload["routes"][0]["result"])
        self.assertEqual(BASE_E1DA154, payload["base_sha"])

        # T5: the same route target at later bases is VALID (base-relative, both ways).
        for base in (BASE_C08F6F8, BASE_MAIN):
            with self.subTest(base=base):
                with tempfile.TemporaryDirectory() as tmp:
                    path = Path(tmp) / "manifest.json"
                    path.write_text(json.dumps(m), encoding="utf-8")
                    code, _out, payload = _run_validator(base, manifest=path)
                self.assertEqual(0, code)
                self.assertEqual("VALID", payload["routes"][0]["result"])

    def test_exactly_three_dangling_routes_at_e1da154(self):
        code, _out, payload = _run_validator(BASE_E1DA154)
        self.assertEqual(1, code)
        failed = {row["route_id"] for row in payload["routes"] if row["result"] != "VALID"}
        self.assertEqual(EXPECTED_E1DA154_FAILURES, failed)
        self.assertEqual(len(EXPECTED_E1DA154_FAILURES), payload["routes_failed"])


class TestManifestMatchesItsCarriers(unittest.TestCase):
    """The manifest's route sets are re-derived from the declared carriers.

    Without this, the manifest could drift from the carriers it claims to
    summarize -- or silently drop a carrier route (the exact defect class this
    mechanism exists to catch).
    """

    def _surface_destinations(self, surface_id: str) -> set[str]:
        return {
            route["destination"]
            for route in _manifest_routes()
            if route.get("surface") == surface_id
        }

    def test_s1_route_set_equals_lean_carrier_extraction(self):
        extracted = set(ROUTE_PATH_RE.findall(_read(LEAN_CARRIER)))
        self.assertEqual(extracted, self._surface_destinations("S1"))

    def test_s2_route_set_equals_agents_dispatcher_extraction(self):
        extracted = set(ROUTE_PATH_RE.findall(_read(AGENTS)))
        self.assertEqual(extracted, self._surface_destinations("S2"))

    def test_route_ids_are_unique_and_surfaces_are_declared(self):
        manifest = json.loads(_read(MANIFEST))
        ids = [route["route_id"] for route in manifest["routes"]]
        self.assertEqual(len(ids), len(set(ids)), "duplicate route_id in the manifest")
        known = {surf["surface_id"] for surf in manifest["surfaces"]}
        for route in manifest["routes"]:
            with self.subTest(route=route["route_id"]):
                self.assertIn(route.get("surface"), known)

    def test_no_real_route_declares_an_anchor_yet(self):
        """Anchor checking exists but has no real instance; keep that visible.

        If a carrier starts declaring anchors, this test fails and forces the
        anchor semantics to be reconsidered with real evidence instead of
        remaining synthetic-only.
        """
        for route in _manifest_routes():
            with self.subTest(route=route["route_id"]):
                self.assertNotIn("anchor", route)


class TestReadmeMatrixMatchesLiveValidator(unittest.TestCase):
    """The README's result matrix is re-derived from live runs, not trusted."""

    BASE_LINE_RE = re.compile(
        r"^base=([0-9a-f]{40})\s+routes=(\d+) valid=(\d+) failed=(\d+)\s*$"
    )
    FAIL_LINE_RE = re.compile(r"^\s+FAIL\s+(\S+)\s+(\S+)\s*$")

    def _readme_matrix(self) -> dict[str, dict]:
        block = _read(README).split("ROUTE_RESULT_MATRIX", 1)[1].split("```", 1)[0]
        matrix: dict[str, dict] = {}
        current: dict | None = None
        for line in block.splitlines():
            head = self.BASE_LINE_RE.match(line)
            if head:
                current = {
                    "routes": int(head.group(2)),
                    "valid": int(head.group(3)),
                    "failed": int(head.group(4)),
                    "fail_routes": set(),
                }
                matrix[head.group(1)] = current
                continue
            fail = self.FAIL_LINE_RE.match(line)
            if fail and current is not None:
                current["fail_routes"].add(fail.group(1))
        return matrix

    def test_readme_matrix_covers_the_three_control_bases(self):
        matrix = self._readme_matrix()
        self.assertTrue(
            {BASE_E1DA154, BASE_C08F6F8, BASE_MAIN}.issubset(matrix),
            f"matrix must cover the control bases; found {sorted(matrix)}",
        )

    def test_readme_numbers_equal_a_live_run_at_every_listed_base(self):
        matrix = self._readme_matrix()
        self.assertTrue(matrix, "no base lines parsed; the matrix block drifted")
        for base, declared in matrix.items():
            with self.subTest(base=base):
                code, _out, payload = _run_validator(base)
                self.assertEqual(declared["routes"], payload["routes_declared"])
                self.assertEqual(declared["valid"], payload["routes_valid"])
                self.assertEqual(declared["failed"], payload["routes_failed"])
                live_fail = {
                    row["route_id"] for row in payload["routes"] if row["result"] != "VALID"
                }
                self.assertEqual(declared["fail_routes"], live_fail)
                expected_code = 0 if declared["failed"] == 0 else 1
                self.assertEqual(expected_code, code)


if __name__ == "__main__":
    unittest.main()
