import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
H2 = ROOT / "experiments/v1.2/h2-lazy-disclosure"
FZ = H2 / "freeze-v3"
SANDBOX_READY = sys.platform == "darwin" and shutil.which("sandbox-exec") is not None


def load(name):
    # The full suite also loads v2 modules under these unqualified names. Drop only
    # those v2 modules and put the v3 directory first before resolving dependencies.
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


sandbox = load("sandbox_v2")
violations = load("violations_v3")


class Tests(unittest.TestCase):
    def test_parse(self):
        entries = ['bad', json.dumps({'timestamp': 'now', 'eventMessage':
                   'Sandbox: cat(42) deny(1) file-read-data /secret'}),
                   json.dumps({'eventMessage': 'Sandbox: cat(43) deny(1) file-read-data /x'})]
        with tempfile.TemporaryDirectory() as tmp, patch.object(violations.subprocess, 'run') as run:
            run.return_value.stdout = '\n'.join(entries)
            out = Path(tmp) / 'violations.jsonl'
            self.assertEqual(violations.collect_violations('a', 'b', {42}, out), 1)
            self.assertEqual(json.loads(out.read_text())['path'], '/secret')

    @unittest.skipUnless(SANDBOX_READY, 'sandbox-exec unavailable')
    def test_read_and_commands(self):
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            base = Path(tmp).resolve(); launch = base / 'cell' / 'launch'; launch.mkdir(parents=True)
            home = base / 'home'; home.mkdir(); (launch / 'inside').write_text('ok')
            secret = Path(outside) / 'secret'; secret.write_text('secret')
            profile = base / 'profile.sb'; profile.write_text(sandbox.render(launch, home, sys.executable))
            def run(argv):
                return subprocess.run(['sandbox-exec', '-f', str(profile), *argv], cwd=launch,
                                      capture_output=True, text=True, env={**os.environ, 'HOME': str(home), 'TMPDIR': str(launch)})
            result = run(['/bin/cat', str(launch / 'inside')]); self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotEqual(run(['/bin/cat', str(secret)]).returncode, 0)
            subprocess.run(['git', 'init', '-q', str(launch)], check=True)
            for cmd in [['/bin/zsh', '-c', 'true'], ['git', '--version'], ['git', 'status'],
                        [sys.executable, '-c', 'import json,unittest,subprocess'],
                        ['opencode', '--version']]:
                result = run(cmd)
                self.assertEqual(result.returncode, 0, (cmd, result.stderr))

    @unittest.skipUnless(SANDBOX_READY, 'sandbox-exec unavailable')
    def test_live_violation(self):
        import datetime
        import time
        with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as outside:
            base = Path(tmp).resolve()
            launch = base / 'cell' / 'launch'
            launch.mkdir(parents=True)
            home = base / 'home'
            home.mkdir()
            secret = Path(outside) / 'secret'
            secret.write_text('secret')
            profile = base / 'profile.sb'
            profile.write_text(sandbox.render(launch, home, sys.executable))
            start = datetime.datetime.now().astimezone() - datetime.timedelta(seconds=2)
            proc = subprocess.Popen(['sandbox-exec', '-f', str(profile), '/bin/cat', str(secret)],
                                    cwd=launch, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            proc.wait()
            self.assertNotEqual(proc.returncode, 0)
            out = base / 'violations.jsonl'
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                end = datetime.datetime.now().astimezone() + datetime.timedelta(seconds=2)
                fmt = '%Y-%m-%d %H:%M:%S%z'
                if violations.collect_violations(start.strftime(fmt), end.strftime(fmt), {proc.pid}, out):
                    rows = [json.loads(line) for line in out.read_text().splitlines()]
                    self.assertTrue(any(row['path'] == str(secret) for row in rows))
                    return
                time.sleep(1)
            self.skipTest('log show returned no matching denial within 10 seconds')
