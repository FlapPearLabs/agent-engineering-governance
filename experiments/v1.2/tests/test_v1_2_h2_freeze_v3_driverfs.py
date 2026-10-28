import hashlib
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
