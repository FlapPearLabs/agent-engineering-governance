"""H4 exploratory pilot — arm carrier tests (`PILOT_SPEC.md` §"Required tests", carriers).

Standard library only, no model, no network. The canonical AGENTS section is read straight from
`git show HEAD:AGENTS.md` here, so the FULL carrier is compared against the repository rather than
against the builder's own output.
"""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PILOT = ROOT / "experiments/v1.2/h4-micro-low-ablation/pilot"


def load(name):
    if str(PILOT) not in sys.path:
        sys.path.insert(0, str(PILOT))
    spec = importlib.util.spec_from_file_location(name, PILOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


arms = load("arms")


def canonical_section() -> bytes:
    """AGENTS.md §2–§4 at HEAD, read independently of `arms.py`."""
    source = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:AGENTS.md"], check=True,
                            capture_output=True).stdout
    start = source.index("## 2. EXECUTION STAGE".encode("utf-8"))
    end = source.index("## 5. CODEGRAPH GROUNDING".encode("utf-8"))
    return source[start:end]


class CarrierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full = arms.build("FULL", ROOT, "HEAD")
        cls.min = arms.build("MIN", ROOT, "HEAD")
        cls.full_bytes = cls.full["files"]["AGENTS.md"]
        cls.min_bytes = cls.min["files"]["AGENTS.md"]

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_full_and_min_differ_and_full_carries_the_canonical_section(self):
        section = canonical_section()
        self.assertNotEqual(self.full_bytes, self.min_bytes)
        self.assertNotEqual(self.full["hashes"]["AGENTS.md"], self.min["hashes"]["AGENTS.md"])
        self.assertIn(section, self.full_bytes)
        self.assertNotIn(section, self.min_bytes)
        # Both arms keep the identical frame: the A-layer text and the gate/contract tail.
        self.assertIn(b"## A-layer invariants", self.full_bytes)
        self.assertIn(b"## A-layer invariants", self.min_bytes)
        self.assertIn(arms.GATE_TEXT, self.full_bytes)
        self.assertIn(arms.GATE_TEXT, self.min_bytes)
        self.assertIn(arms.CONTRACT_TEXT, self.full_bytes)
        self.assertIn(arms.CONTRACT_TEXT, self.min_bytes)

    def test_min_carrier_carries_none_of_the_eleven_process_rules(self):
        self.assertEqual(arms.PROCESS_RULE_IDS, tuple(
            f"R-V12-{number:03d}" for number in range(36, 47)))
        self.assertEqual(11, len(arms.PROCESS_RULE_IDS))
        self.assertEqual([], arms.leaked_rules(self.min_bytes))
        self.assertEqual([], arms.leaked_references(self.min_bytes))
        manifest = self.min["manifest"]
        self.assertEqual([], manifest["rules"])
        self.assertEqual(list(arms.PROCESS_RULE_IDS), manifest["excluded_rules"])
        self.assertEqual([], manifest["process_rule_leaks"])

    def test_full_manifest_maps_all_eleven_ids_to_unique_ordered_ranges(self):
        manifest = self.full["manifest"]
        rules = manifest["rules"]
        self.assertEqual(list(arms.PROCESS_RULE_IDS), [rule["id"] for rule in rules])
        previous_end = 0
        for rule in rules:
            self.assertLess(rule["carrier_start"], rule["carrier_end"])
            self.assertGreaterEqual(rule["carrier_start"], previous_end)
            previous_end = rule["carrier_end"]
            self.assertEqual(rule["bytes_sha256"],
                             arms.sha256(self.full_bytes[rule["carrier_start"]:
                                                         rule["carrier_end"]]))
            # the sentinel must still be inside the range it was measured against
            self.assertIn(rule["sentinel"].encode("utf-8"),
                          self.full_bytes[rule["carrier_start"]:rule["carrier_end"]])
        section = manifest["section"]
        self.assertEqual(arms.sha256(canonical_section()), section["bytes_sha256"])
        self.assertEqual(section["bytes_sha256"],
                         arms.sha256(self.full_bytes[section["carrier_start"]:
                                                     section["carrier_end"]]))
        self.assertEqual(arms.sha256(subprocess.run(
            ["git", "-C", str(ROOT), "show", "HEAD:AGENTS.md"], check=True,
            capture_output=True).stdout), manifest["sources"]["AGENTS.md"])

    def test_inject_reuses_the_min_carrier_bytes(self):
        inject = arms.build("INJECT", ROOT, "HEAD")
        self.assertEqual(self.min["hashes"]["AGENTS.md"], inject["hashes"]["AGENTS.md"])
        self.assertEqual(self.min_bytes, inject["files"]["AGENTS.md"])
        self.assertEqual(list(arms.PROCESS_RULE_IDS), inject["manifest"]["excluded_rules"])

    def test_assumed_flag_is_recorded_for_the_min_base_text(self):
        for carrier in (self.full, self.min):
            self.assertTrue(carrier["assumed"])
            self.assertIs(True, carrier["manifest"]["assumed"])
            self.assertIn("assumed_reason", carrier["manifest"])

    def test_delivery_outside_the_repository_reads_back_identical(self):
        record = arms.deliver(self.min, self.root / "delivery", ROOT)
        self.assertEqual("PASS", record["verdict"])
        self.assertEqual(self.min["hashes"], record["files"])
        delivered = (self.root / "delivery" / "AGENTS.md").read_bytes()
        self.assertEqual(self.min_bytes, delivered)
        readback = arms.verify_readback(self.min, self.root / "delivery")
        self.assertEqual("PASS", readback["verdict"])
        self.assertTrue(readback["assumed"])
        self.assertEqual([], readback["process_rule_leaks"])

    def test_missing_carrier_file_is_rejected(self):
        arms.deliver(self.full, self.root / "delivery", ROOT)
        (self.root / "delivery" / "AGENTS.md").unlink()
        with self.assertRaises(arms.CarrierError) as caught:
            arms.verify_readback(self.full, self.root / "delivery")
        self.assertIn("CARRIER_MISSING:AGENTS.md", str(caught.exception))

    def test_substituted_carrier_is_rejected(self):
        arms.deliver(self.min, self.root / "delivery", ROOT)
        path = self.root / "delivery" / "AGENTS.md"
        path.write_bytes(path.read_bytes().replace(b"## Task contract", b"## Task contract "))
        with self.assertRaises(arms.CarrierError) as caught:
            arms.verify_readback(self.min, self.root / "delivery")
        self.assertIn("CARRIER_HASH_MISMATCH:AGENTS.md", str(caught.exception))

    def test_extra_delivered_file_is_rejected(self):
        arms.deliver(self.min, self.root / "delivery", ROOT)
        (self.root / "delivery" / "extra.md").write_text("inherited guidance\n")
        with self.assertRaises(arms.CarrierError) as caught:
            arms.verify_readback(self.min, self.root / "delivery")
        self.assertIn("CARRIER_EXTRA:extra.md", str(caught.exception))

    def test_wrong_arm_carrier_is_rejected(self):
        arms.deliver(self.min, self.root / "delivery", ROOT)
        with self.assertRaises(arms.CarrierError) as caught:
            arms.verify_readback(self.full, self.root / "delivery")
        self.assertIn("CARRIER_HASH_MISMATCH:AGENTS.md", str(caught.exception))

    def test_delivery_inside_the_repository_is_refused(self):
        target = PILOT / ".delivery-should-not-exist"
        with self.assertRaises(arms.CarrierError) as caught:
            arms.deliver(self.min, target, ROOT)
        self.assertIn("DELIVERY_INSIDE_REPOSITORY", str(caught.exception))
        self.assertFalse(target.exists())

    def test_inherited_guidance_on_the_delivery_path_is_refused(self):
        cell = self.root / "cell"
        (cell / ".agents").mkdir(parents=True)
        (cell / ".agents" / "AGENTS.md").write_text("global guidance\n")
        with self.assertRaises(arms.CarrierError) as caught:
            arms.deliver(self.min, cell / "delivery", ROOT)
        self.assertIn("INHERITED_GUIDANCE:.agents", str(caught.exception))
        self.assertFalse((cell / "delivery").exists())

    def test_unknown_materials_commit_fails_closed(self):
        with self.assertRaises(arms.CarrierError) as caught:
            arms.build("FULL", ROOT, "0" * 40)
        self.assertIn("MATERIALS_UNAVAILABLE", str(caught.exception))
        with self.assertRaises(arms.CarrierError):
            arms.build("PARTIAL", ROOT, "HEAD")


if __name__ == "__main__":
    unittest.main()
