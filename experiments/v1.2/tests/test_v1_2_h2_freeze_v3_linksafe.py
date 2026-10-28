import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
FZ = ROOT / 'experiments/v1.2/h2-lazy-disclosure/freeze-v3'
sys.path.insert(0, str(FZ))
import collect_v2 as collect
import run_audit_v2 as audit
import run_h2r2 as driver
import sandbox_v2 as sandbox
import wrapper_delivery as delivery

spec = importlib.util.spec_from_file_location('retry_helpers', Path(__file__).with_name('test_v1_2_h2_freeze_v3_auditretry.py'))
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


class LinkSafety(unittest.TestCase):
    def test_collector_and_bundle_do_not_read_report_link(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            run = base / 'run'
            run.mkdir()
            outside = base / 'outside'
            outside.write_text('PRIVATE')
            (run / 'report.md').symlink_to(outside)
            evidence = Path(sandbox.snapshot(run, base / 'snapshot')['path'])
            record, reasons = collect.artifact(evidence, 'report.md', 'MISSING', 'EMPTY')
            self.assertEqual(record['sha256'], hashlib.sha256(str(outside).encode()).hexdigest())
            self.assertEqual(reasons, ["EVIDENCE_UNREADABLE:report.md"])
            (evidence / 'collected.json').write_text(json.dumps({'diff': 'stub'}))
            (evidence / 'verdict.json').write_text(json.dumps({'verdict': 'REJECT', 'reasons': []}))
            contract = base / 'contract'
            contract.write_text('contract\n' + audit.BLOCK_BEGIN + '\nidentity\n' + audit.BLOCK_END + '\n')
            with self.assertRaises((ValueError, OSError)):
                audit.prepare_bundle(evidence, {'task_id': 'f01', 'run_id': 'h2r3-f01-c', 'model': 'stub'}, {'task_id': 'f01'}, contract_path=contract, report_path=evidence / 'report.md', bundle_dir=base / 'bundle')

    def test_registered_legacy_is_readable_and_link_parent_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            legacy = root / 'old-run'
            legacy.mkdir()
            self.assertEqual(delivery.run_dir_for(root, 'old-run'), root / '.cells/old-run/old-run')
            (root / 'registry-v3.jsonl').write_text(json.dumps({'run_id': 'old-run'}) + '\n')
            self.assertEqual(delivery.run_dir_for(root, 'old-run'), legacy)
            outside = root / 'outside'
            outside.mkdir()
            (root / 'parent-link').symlink_to(outside)
            with self.assertRaises(OSError):
                delivery.safe_write(root / 'parent-link/file', b'bad')
            self.assertFalse((outside / 'file').exists())

    def test_delivery_and_events_links_are_not_read(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            outside = base / 'outside'
            outside.write_text('{"secret": true}')
            (base / 'receipt.json').symlink_to(outside)
            receipt, _, reasons = collect.verify_delivery(ROOT, base)
            self.assertEqual(receipt['type'], 'symlink')
            self.assertEqual(receipt['sha256'], hashlib.sha256(str(outside).encode()).hexdigest())
            self.assertEqual(reasons, ['EVIDENCE_UNREADABLE:receipt.json'])
            self.assertEqual(driver.read_events(base / 'receipt.json'), ([], 0))

    def test_roots_are_not_followed(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = base / 'root'
            root.mkdir()
            (root / 'sentinel').write_text('private')
            link = base / 'link'
            link.symlink_to(root)
            with self.assertRaises((ValueError, OSError)):
                sandbox.snapshot(link, base / 'snapshot')
            with self.assertRaises((ValueError, OSError)):
                driver.artifact_hashes(link)

    def test_new_start_ignores_empty_legacy_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            runs = base / 'runs'
            (runs / 'h2r3-f01-c').mkdir(parents=True)
            with patch.object(driver.run_acceptance_v2, 'accept', return_value={'verdict': 'REJECT', 'reasons': ['STUB_REJECT']}), patch.object(driver.violations_v3, 'collect_violations', side_effect=OSError('stub')):
                result = driver.execute('h2r3-f01-c', runs, worker_command=helpers.stub_worker_command(base), server_command=helpers.stub_server_command(base), preflight=helpers.passing_preflight, auditor=helpers.stub_auditor(), profile_env=helpers.profile_env_file(base), probe=helpers.passing_probe, sandbox=helpers.StubSandbox(), auth=helpers.StubAuth(), limit_seconds=30)
            self.assertEqual(result['run_dir'], str(runs / '.cells/h2r3-f01-c/h2r3-f01-c'))

    def test_driver_link_and_legacy_start(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            victim = base / 'victim'
            victim.write_text('SAFE')
            worker = base / 'worker.py'
            worker.write_text('import json\nfrom pathlib import Path\nPath("events.jsonl").symlink_to(' + repr(str(victim)) + ')\nPath("report.md").write_text("report\\n")\nPath(".h2-telemetry.log").write_text("READ FULL repo/RULES.md\\n")\nprint(json.dumps({"type":"text","sessionID":"ses_stub","part":{"text":"DONE"}}))\n')
            runs = base / 'runs'
            (runs / 'h2r3-f01-c').mkdir(parents=True)
            with patch.object(driver.run_acceptance_v2, 'accept', return_value={'verdict': 'REJECT', 'reasons': ['STUB_REJECT']}), patch.object(driver.violations_v3, 'collect_violations', side_effect=OSError('stub')):
                result = driver.execute('h2r3-f01-c', runs, worker_command=(sys.executable, str(worker)), server_command=helpers.stub_server_command(base), preflight=helpers.passing_preflight, auditor=helpers.stub_auditor(), profile_env=helpers.profile_env_file(base), probe=helpers.passing_probe, sandbox=helpers.StubSandbox(), auth=helpers.StubAuth(), limit_seconds=30)
            self.assertEqual(victim.read_text(), 'SAFE')
            self.assertEqual(result['run_dir'], str(runs / '.cells/h2r3-f01-c/h2r3-f01-c'))


if __name__ == '__main__':
    unittest.main()
