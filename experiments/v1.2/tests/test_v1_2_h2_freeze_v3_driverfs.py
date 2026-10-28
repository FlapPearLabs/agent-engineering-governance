import hashlib
import importlib.util
import json
from unittest import mock
import os
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
H2 = ROOT / "experiments/v1.2/h2-lazy-disclosure"
FZ = H2 / "freeze-v3"


def load(name):
    v2 = (H2 / "freeze-v2").resolve()
    for key, module in list(sys.modules.items()):
        source = getattr(module, "__file__", None)
        if source and Path(source).resolve().is_relative_to(v2):
            del sys.modules[key]
    if str(FZ) in sys.path:
        sys.path.remove(str(FZ))
    sys.path.insert(0, str(FZ))
    spec = importlib.util.spec_from_file_location(name, FZ / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class DriverHashTests(unittest.TestCase):
    def test_links_and_fifo_registration_hashes(self):
        driver = load("run_h2r2")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run = root / "run"
            run.mkdir()
            outside = root / "outside"
            outside.write_bytes(b"outside")
            before = outside.stat().st_mtime_ns
            (run / "link").symlink_to(outside)
            (run / "dirlink").symlink_to(root, target_is_directory=True)
            os.mkfifo(run / "pipe")
            results = []
            thread = threading.Thread(target=lambda: results.append(driver.artifact_hashes(run)),
                                      daemon=True)
            thread.start()
            thread.join(2)
            self.assertFalse(thread.is_alive(), "registration hashing blocked on FIFO")
            hashes = results[0]
            self.assertEqual(hashes["link"], hashlib.sha256(os.fsencode(outside)).hexdigest())
            self.assertEqual(hashes["dirlink"], hashlib.sha256(os.fsencode(root)).hexdigest())
            self.assertEqual(hashes["pipe"]["type"], "fifo")
            self.assertEqual(outside.read_bytes(), b"outside")
            self.assertEqual(outside.stat().st_mtime_ns, before)


class SnapshotAndCellTests(unittest.TestCase):
    def test_snapshot_special_entries_and_collision(self):
        sandbox = load("sandbox_v2")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel"
            sentinel.write_bytes(b"unchanged")
            before = (sentinel.read_bytes(), sentinel.stat().st_mtime_ns)
            (source / "link").symlink_to(sentinel)
            os.mkfifo(source / "pipe")
            record = sandbox.snapshot(source, root / "snapshot")
            entries = json.loads(Path(record["manifest_path"]).read_text())["entries"]
            self.assertEqual(entries["link"]["type"], "symlink")
            self.assertEqual(entries["pipe"]["type"], "other")
            target = root / "target"
            target.symlink_to(sentinel)
            file = source / "file"
            file.write_bytes(b"attack")
            manifest = {}
            sandbox._snapshot_entry(file, target, "file", manifest)
            self.assertTrue(manifest["file"]["collision"])
            self.assertEqual((sentinel.read_bytes(), sentinel.stat().st_mtime_ns), before)

    def test_directory_collision_does_not_follow_link(self):
        sandbox = load("sandbox_v2")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            (source / "a").mkdir(parents=True)
            (source / "a" / "sentinel").write_bytes(b"attack")
            outside = root / "outside"
            outside.mkdir()
            sentinel = outside / "sentinel"
            sentinel.write_bytes(b"safe")
            before = (sentinel.read_bytes(), sentinel.stat().st_mtime_ns)
            target = root / "snapshot"
            original = Path.mkdir
            def planted(path, *args, **kwargs):
                if path == target / "a":
                    path.symlink_to(outside, target_is_directory=True)
                return original(path, *args, **kwargs)
            with mock.patch.object(Path, "mkdir", planted):
                record = sandbox.snapshot(source, target)
            entries = json.loads(Path(record["manifest_path"]).read_text())["entries"]
            self.assertTrue(entries["a"]["collision"])
            self.assertNotIn("a/sentinel", entries)
            self.assertEqual((sentinel.read_bytes(), sentinel.stat().st_mtime_ns), before)

    def test_source_swap_to_fifo_is_recorded(self):
        sandbox = load("sandbox_v2")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "file"
            source.write_bytes(b"file")
            original = os.open
            def swapped(path, flags, *args):
                if path == source:
                    source.unlink()
                    os.mkfifo(source)
                return original(path, flags, *args)
            manifest = {}
            with mock.patch.object(sandbox.os, "open", swapped):
                sandbox._snapshot_entry(source, root / "copy", "file", manifest)
            self.assertTrue(manifest["file"]["unreadable"])
            self.assertFalse((root / "copy").exists())

    def test_cells_and_profile(self):
        wrapper = load("wrapper_delivery")
        sandbox = load("sandbox_v2")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = wrapper.run_dir_for(root, "run1")
            run.mkdir(parents=True)
            self.assertEqual(wrapper.runs_root_of(run), root)
            self.assertEqual(wrapper.driver_root(run), root / ".driver" / "run1")
            self.assertEqual([p.name for p in run.parent.iterdir()], ["run1"])
            legacy = root / "old"
            legacy.mkdir()
            self.assertEqual(wrapper.run_dir_for(root, "old"), legacy)
            self.assertEqual(wrapper.runs_root_of(legacy), root)
            rules = sandbox.allow_rules(run, run / "home")
            writes = [rule for rule in rules if "file-write*" in rule]
            self.assertTrue(any(f'(subpath "{run}")' in rule for rule in writes))
            self.assertFalse(any(f'(subpath "{run.parent}")' in rule for rule in writes))

    def test_aggregate_uses_cell_path(self):
        aggregate = load("aggregate_runs")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / ".cells" / "r" / "r"
            run.mkdir(parents=True)
            (run / "marker").write_text("cell")
            plan = [{"run_id": "r", "task_id": "t", "arm": "control"}]
            entry = {"run_id": "r", "final_verdict": "INVALID", "verdict": "INVALID"}
            seen = []
            def denied(item, path):
                seen.append((path / "marker").read_text())
                return {"count": 0, "list": [], "verified": True}
            with mock.patch.object(aggregate, "planned_runs", return_value=plan), \
                 mock.patch.object(aggregate, "read_registry", return_value={"r": entry}), \
                 mock.patch.object(aggregate, "denied_attempts", side_effect=denied):
                aggregate.aggregate(root)
            self.assertEqual(seen, ["cell"])


if __name__ == "__main__":
    unittest.main()
