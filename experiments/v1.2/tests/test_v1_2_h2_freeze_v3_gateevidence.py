import ast
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
FZ = ROOT / 'experiments/v1.2/h2-lazy-disclosure/freeze-v3'
sys.path.insert(0, str(FZ))
import build_manifest  # noqa: E402
import run_acceptance_v2  # noqa: E402
import sandbox_v2  # noqa: E402


def local_closure(directory, roots):
    pending = list(roots)
    seen = set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        tree = ast.parse((directory / (name + '.py')).read_text())
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name.split('.')[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module.split('.')[0]]
            elif isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant):
                if (isinstance(node.func, ast.Name) and node.func.id == '__import__') or (
                    isinstance(node.func, ast.Attribute) and node.func.attr == 'import_module'
                ):
                    if isinstance(node.args[0].value, str):
                        names = [node.args[0].value.split('.')[0]]
            pending.extend(n for n in names if (directory / (n + '.py')).is_file())
    return seen


class GateEvidenceTests(unittest.TestCase):
    def test_runtime_closure_is_frozen(self):
        roots = ['run_h2r2', 'aggregate_runs', 'run_acceptance_v2', 'run_audit_v2']
        closure = local_closure(FZ, roots)
        self.assertIn('violations_v3', closure)
        missing = {str((FZ / (name + '.py')).relative_to(ROOT)) for name in closure} - set(build_manifest.FROZEN_FILES)
        self.assertEqual(missing, set())

    def test_closure_finds_transitive_new_helper(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            (directory / 'entry.py').write_text('import intermediate\n')
            (directory / 'intermediate.py').write_text('import future_helper\n')
            (directory / 'future_helper.py').write_text('')
            self.assertEqual(local_closure(directory, ['entry']),
                             {'entry', 'intermediate', 'future_helper'})

    def test_gate_records_separate_evidence_and_nonfatal_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            tests = base / 'source/scripts/tests'
            tests.mkdir(parents=True)
            (tests / 'test_probe.py').write_text('import unittest\nclass Probe(unittest.TestCase):\n def test_one(self): self.assertEqual(1,1)\n')
            calls = []

            def collect(start, end, pids, path):
                calls.append((start, end, pids, Path(path)))
                Path(path).write_text('denial\n')
                return 1

            # F5: patch the collector instance used by the gate even after module reloads.
            with patch.object(run_acceptance_v2.delivery_anchors.violations_v3,
                              'collect_violations', side_effect=collect):
                result, info = run_acceptance_v2.gate_run(base / 'attempt', base / 'source', 'test_probe.py', 'RESOLVED', number=1)
            self.assertEqual((result['rc'], result['ran']), (0, 1))
            evidence = info['violations']
            self.assertEqual(Path(evidence['path']).parent, base / 'attempt/gate-1')
            self.assertEqual(evidence['count'], 1)
            self.assertEqual(evidence['sha256'], hashlib.sha256(b'denial\n').hexdigest())
            self.assertTrue(calls[0][0] <= calls[0][1])
            self.assertTrue(calls[0][2])
            with patch.object(run_acceptance_v2.delivery_anchors.violations_v3,
                              'collect_violations', side_effect=OSError('log failed')):
                other, info2 = run_acceptance_v2.gate_run(base / 'attempt', base / 'source', 'test_probe.py', 'RESOLVED', number=2)
            self.assertEqual((other['rc'], other['ran']), (0, 1))
            self.assertEqual(info2['violations']['error'], 'OSError')
            self.assertFalse((base / 'attempt/gate-2/violations.jsonl').exists())

    def test_gate_comment_describes_loopback(self):
        self.assertIn('any localhost port', sandbox_v2.Gate.__doc__)
        self.assertNotIn('no network endpoint at all', sandbox_v2.Gate.__doc__)


if __name__ == '__main__':
    unittest.main()
