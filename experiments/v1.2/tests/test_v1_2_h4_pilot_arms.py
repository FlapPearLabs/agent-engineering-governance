"""H4 exploratory pilot — arm carrier tests (`PILOT_SPEC.md` §"Required tests", carriers).

Standard library only, no model, no network. The canonical AGENTS section is read straight from
`git show HEAD:AGENTS.md` here, so the FULL carrier is compared against the repository rather than
against the builder's own output.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


def process_slice() -> tuple[str, bytes]:
    """A 200-byte slice from the middle of a rule range that no anchor or sentinel covers.

    This is the acceptance report's D2 payload (`attacks/c_carriers.py` §4): verbatim process text
    with no rule ID, no heading and no blocking token, so the legacy anchor check cannot see it.
    """
    section = canonical_section()
    blockers: list[bytes] = []
    for _rule_id, start_anchor, end_anchor, sentinel in arms.RULE_TABLE:
        blockers.append(start_anchor.encode("utf-8"))
        blockers.append(sentinel.encode("utf-8"))
        if end_anchor:
            blockers.append(end_anchor.encode("utf-8"))
    for rule_id, start_anchor, end_anchor, sentinel in arms.RULE_TABLE:
        start = section.find(start_anchor.encode("utf-8"))
        end = section.find(end_anchor.encode("utf-8")) if end_anchor else len(section)
        for offset in range(start + 20, max(start + 20, end - 200), 10):
            window = section[offset:offset + 200]
            if len(window) == 200 and not any(token in window for token in blockers):
                return rule_id, window
    raise AssertionError("no unanchored 200-byte rule slice in the canonical section")


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

    # -- D2: the verbatim window overlap, not only anchors and sentinels -------------------

    def test_a_min_carrier_that_copies_a_rule_verbatim_without_anchors_is_refused_at_build(self):
        """D4(a): removing the `raise` in `arms.build` makes this test red, not green."""
        rule_id, window = process_slice()
        self.assertEqual([], arms.leaked_rules(window),
                         "the legacy anchor/sentinel check must not see this slice")
        with self.assertRaises(arms.CarrierError) as caught:
            self.build_min_from_leaky_a_layer(window)
        self.assertIn("MIN_CARRIER_LEAKS_PROCESS_RULES", str(caught.exception))
        self.assertIn(rule_id, str(caught.exception))

    def test_a_verbatim_rule_slice_is_refused_at_deliver_and_at_verify_readback(self):
        _rule_id, window = process_slice()
        carrier = self.smuggled_min_carrier(window)
        dest = self.root / "smuggled"
        with self.assertRaises(arms.CarrierError) as caught:
            arms.deliver(carrier, dest, ROOT)
        self.assertIn("MIN_CARRIER_LEAKS_PROCESS_RULES", str(caught.exception))
        self.assertFalse(dest.exists(), "a leaking carrier is never written to disk")
        dest.mkdir()
        for name, data in carrier["files"].items():
            (dest / name).write_bytes(data)
        with self.assertRaises(arms.CarrierError) as caught:
            arms.verify_readback(carrier, dest, ROOT)
        self.assertIn("DELIVERED_CARRIER_LEAKS_PROCESS_RULES", str(caught.exception))

    def test_the_clean_min_carrier_and_the_shared_frame_still_pass_the_window_check(self):
        section = canonical_section()
        rules = arms.extract_rules(section)
        self.assertEqual([], arms.leaked_windows(self.min_bytes, section, rules))
        # the gate commands and task contract are shared by every arm and are not rule text
        self.assertEqual([], arms.leaked_windows(arms.GATE_TEXT + arms.CONTRACT_TEXT, section, rules))
        record = arms.deliver(self.min, self.root / "delivery", ROOT)
        self.assertEqual("PASS", record["verdict"])
        readback = arms.verify_readback(self.min, self.root / "delivery", ROOT)
        self.assertEqual([], readback["process_rule_leaks"])
        self.assertEqual([], readback["process_rule_window_leaks"])

    def test_the_full_carrier_is_not_leak_checked_for_the_process_text_it_must_carry(self):
        section = canonical_section()
        rules = arms.extract_rules(section)
        detected = arms.leaked_windows(self.full_bytes, section, rules)
        self.assertTrue(detected, "at least one rule range is long enough for a 10-word window")
        self.assertTrue(set(detected) <= set(arms.PROCESS_RULE_IDS))
        self.assertEqual([], self.full["manifest"]["process_rule_window_leaks"])
        self.assertEqual("PASS", arms.deliver(self.full, self.root / "full-delivery", ROOT)["verdict"])

    # -- helpers for the two tests above --------------------------------------------------

    def build_min_from_leaky_a_layer(self, payload: bytes):
        """Build MIN against a materials root whose hand-written base text carries `payload`."""
        leaky_root = self.root / "leaky-root"
        target = leaky_root / arms.A_LAYER_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / arms.A_LAYER_REL).read_bytes() + b"\n" + payload + b"\n")
        source = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:AGENTS.md"], check=True,
                                capture_output=True).stdout
        with mock.patch.object(arms, "resolve_materials",
                               lambda _root, _materials: "0" * 40), \
                mock.patch.object(arms, "git_show",
                                  lambda _root, _materials, _rel: source):
            return arms.build(arms.ARM_MIN, leaky_root, "HEAD")

    def smuggled_min_carrier(self, window: bytes) -> dict:
        """The clean MIN carrier with one verbatim rule slice appended, hashes made consistent."""
        carrier_text = self.min_bytes + b"\n<!-- " + window + b" -->\n"
        manifest = dict(self.min["manifest"])
        manifest["files"] = {arms.CARRIER_NAME: arms.sha256(carrier_text)}
        files = {arms.CARRIER_NAME: carrier_text,
                 arms.MANIFEST_NAME: (json.dumps(manifest, indent=2, sort_keys=True,
                                                ensure_ascii=False) + "\n").encode("utf-8")}
        return {"arm": arms.ARM_MIN, "label": arms.LABEL, "assumed": True,
                "materials": self.min["materials"], "rules": [],
                "excluded_rules": list(arms.PROCESS_RULE_IDS),
                "files": files,
                "hashes": {name: arms.sha256(data) for name, data in files.items()}}


if __name__ == "__main__":
    unittest.main()
