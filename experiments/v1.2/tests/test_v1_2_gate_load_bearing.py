"""Controls for the experimental gate probe."""
import hashlib
import importlib.util
import json
import copy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[3]
DIRECTORY = ROOT / "experiments/v1.2/gate-load-bearing"
SPEC = importlib.util.spec_from_file_location("n7_probe", DIRECTORY / "probe_gates.py")
PROBE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)
MANIFEST = json.loads((DIRECTORY / "gates.json").read_text())


def snapshot():
    files = subprocess.check_output(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT)
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in files.decode().split("\0") if name and (ROOT / name).is_file()}


class ProbeTests(unittest.TestCase):
    def test_full_probe_preserves_checkout(self):
        before = snapshot()
        completed = subprocess.run([PROBE.sys.executable, str(DIRECTORY / "probe_gates.py"),
                                    "--worktree"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertEqual(before, snapshot())

    def test_exit_modes(self):
        missing = [{"id": "example", "status": "NO_POSITIVE_CONTROL"}]
        self.assertEqual(PROBE.exit_status(missing), 1)
        for status in ("GATE_NOT_LOAD_BEARING", "BASELINE_FAILING", "PROBE_ERROR"):
            self.assertEqual(PROBE.exit_status([{"status": status}]), 1)

    def test_wrong_cause_is_not_attributed_for_each_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for gate in MANIFEST["gates"]:
                with self.subTest(gate=gate["id"]):
                    wrong = f"unrelated failure: {gate['control']['signal']} {gate['control']['path']}\n"
                    with patch.object(PROBE, "run", return_value=subprocess.CompletedProcess([], 1, "[]")):
                        self.assertFalse(PROBE.has_signal(root, gate, wrong))

    def test_invalid_control_paths_preflight_all_kinds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "scratch"
            root.mkdir()
            victim = Path(temporary) / "victim"
            victim.write_bytes(b"unchanged")
            (root / "link").symlink_to(victim)
            for kind in ("file", "append", "replace", "delete", "history", "metadata"):
                for path in (str(victim), "../victim", "link"):
                    with self.subTest(kind=kind, path=path):
                        gate = {"id": kind, "control": {"kind": kind, "path": path}}
                        self.assertEqual(PROBE.probe_tree(root, {"gates": [gate]})[0]["status"], "PROBE_ERROR")
                        self.assertEqual(victim.read_bytes(), b"unchanged")

    def test_history_absolute_path_leaves_caller_byte_identical(self):
        with tempfile.TemporaryDirectory() as temporary:
            caller = Path(temporary) / "caller"
            PROBE.scratch(ROOT, "HEAD", caller, worktree=True)
            gate = copy.deepcopy(next(item for item in MANIFEST["gates"] if item["id"] == "history"))
            gate["control"]["path"] = str(caller / "caller-escape.txt")
            (caller / "experiments/v1.2/gate-load-bearing/gates.json").write_text(
                json.dumps({"gates": [gate]}))
            def files():
                return {str(path.relative_to(caller)): hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in caller.rglob("*") if path.is_file() and not path.is_symlink()}
            before = files()
            result = subprocess.run([PROBE.sys.executable, str(DIRECTORY / "probe_gates.py"),
                                     "--worktree", "--repo", str(caller)], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["gates"][0]["status"], "PROBE_ERROR")
            self.assertEqual(before, files())

    def test_ruff_wrong_rule_and_syntax(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            PROBE.scratch(ROOT, "HEAD", root, worktree=True)
            gate = copy.deepcopy(next(item for item in MANIFEST["gates"] if item["id"] == "ruff"))
            for content in ("F841\n", "def F841(:\n"):
                with self.subTest(content=content):
                    gate["control"]["content"] = content
                    self.assertEqual(PROBE.probe_tree(root, {"gates": [gate]})[0]["status"], "PROBE_ERROR")

    def test_worktree_copy_preserves_checkout(self):
        before = snapshot()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            PROBE.scratch(ROOT, "HEAD", root, worktree=True)
            self.assertEqual((root / "experiments/v1.2/gate-load-bearing/gates.json").read_bytes(),
                             (DIRECTORY / "gates.json").read_bytes())
        self.assertEqual(before, snapshot())

    def test_scratch_and_ruff_controls_leave_checkout_unchanged(self):
        before = snapshot()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            PROBE.scratch(ROOT, "HEAD", root)
            gate = next(item for item in MANIFEST["gates"] if item["id"] == "ruff")
            manifest = {"gates": [gate]}
            self.assertEqual(PROBE.probe_tree(root, manifest)[0]["status"], "LOAD_BEARING")
            config = root / "ruff.toml"
            original = config.read_text()
            for replacement in ('select = []', 'select = ["E9"]',
                                'select = ["E9", "F"]\nextend-ignore = ["F841"]',
                                'select = ["E9", "F"]\nexclude = ["scripts/n7_control.py"]'):
                with self.subTest(replacement=replacement):
                    config.write_text(original.replace('select = ["E9", "F"]', replacement))
                    self.assertEqual(PROBE.probe_tree(root, manifest)[0]["status"], "GATE_NOT_LOAD_BEARING")
            config.write_text(original)
            broken = dict(gate, control={"kind": "replace", "path": "ruff.toml", "before": "not present", "after": "", "signal": "F841"})
            self.assertEqual(PROBE.probe_tree(root, {"gates": [broken]})[0]["status"], "PROBE_ERROR")
        self.assertEqual(before, snapshot())

    def test_governance_hollow_and_missing_control(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            PROBE.scratch(ROOT, "HEAD", root)
            gate = next(item for item in MANIFEST["gates"] if item["id"] == "governance")
            self.assertEqual(PROBE.probe_tree(root, {"gates": [gate]})[0]["status"], "LOAD_BEARING")
            script = root / "scripts/validate_governance.py"
            text = script.read_text()
            text = text.replace('check("markdown-links-resolve", not bad_links,',
                                'check("markdown-links-resolve", True,')
            script.write_text(text)
            self.assertEqual(PROBE.probe_tree(root, {"gates": [gate]})[0]["status"], "GATE_NOT_LOAD_BEARING")
            broken = dict(gate, control=None)
            self.assertEqual(PROBE.probe_tree(root, {"gates": [broken]})[0]["status"], "PROBE_ERROR")

    def test_selftest_hollow(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            PROBE.scratch(ROOT, "HEAD", root)
            gate = next(item for item in MANIFEST["gates"] if item["id"] == "selftest")
            self.assertEqual(PROBE.probe_tree(root, {"gates": [gate]})[0]["status"], "LOAD_BEARING")
            script = root / "scripts/validate_public_release.py"
            text = script.read_text()
            text = text.replace('results.append((name, ok, detail))',
                                'results.append((name, True, detail))')
            script.write_text(text)
            self.assertEqual(PROBE.probe_tree(root, {"gates": [gate]})[0]["status"], "GATE_NOT_LOAD_BEARING")


if __name__ == "__main__":
    unittest.main()
