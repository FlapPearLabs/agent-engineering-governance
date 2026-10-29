import hashlib
import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE = Path(__file__).resolve().parents[1] / 'h5-verified-state/ledger/ledger.py'
spec = importlib.util.spec_from_file_location('h5_ledger', MODULE)
ledger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ledger)
SHA = 'sha1:' + 'a' * 40
OTHER = 'sha1:' + 'b' * 40


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / 'ledger'
        self.anchor = self.root / 'anchor'
        (self.root / 'evidence').write_bytes(b'proof')
        self.digest = hashlib.sha256(b'proof').hexdigest()
        self.target = {'repo_id': 'r', 'worktree_id': 'w', 'sha': SHA}
        self.add('goal', {'goal_id': 'g', 'text_hash': 'h', 'authority_ref': 'a', 'repo_id': 'r', 'base_sha': SHA, 'predicate_specs': ['p']})
        self.add('episode_start', {'episode_id': 'ep', 'arm': 'a', 'repo_id': 'r', 'worktree_id': 'w', 'head_sha': SHA, 'seed_head_hash': 'h', 'context_id': 'c'})
        self.claim()
        self.verify()
        self.seal()

    def add(self, typ, payload, actor='worker'):
        events = ledger._read(self.path) if self.path.exists() and self.path.stat().st_size else []
        e = ledger.make_record('ledger', len(events), events[-1]['hash'] if events else ledger.ZERO, typ, 'e' + str(len(events)), '2026-01-01T00:00:00Z', actor, payload)
        ledger.append(self.path, e)
        return e

    def claim(self, **changes):
        p = {'claim_id': 'c', 'episode_id': 'ep', 'subject': 'subject', 'value': 'yes', 'repo_id': 'r', 'worktree_id': 'w', 'candidate_sha': SHA, 'predicate_id': 'p', 'predicate_version': '1', 'evidence_refs': ['evidence']}
        p.update(changes)
        return self.add('state_claim', p)

    def verify(self, actor='verifier', **changes):
        p = {'verification_id': 'v', 'claim_id': 'c', 'independent_verifier_id': actor, 'predicate_id': 'p', 'predicate_version': '1', 'repo_id': 'r', 'worktree_id': 'w', 'sha': SHA, 'result': 'PASS', 'command': 'check', 'exit_code': 0, 'evidence_refs': ['evidence'], 'evidence_hashes': [self.digest]}
        p.update(changes)
        return self.add('verification', p, actor)

    def seal(self):
        ledger.anchor(self.path, self.anchor)

    def fold(self):
        return ledger.fold(self.path, self.anchor, self.target, self.root)

    def predicates(self):
        return {'artefact_in_merge': True, 'ancestry_matches': True, 'merge_sha': SHA, 'ci_sha': SHA, 'ci_success': True, 'ci_post_merge': True, 'required_predicates': ['p'], 'open_blockers': []}

    def test_positive(self):
        s = self.fold()
        self.assertEqual(s['status'], 'VALID')
        self.assertEqual(len(s['verified_facts']), 1)
        self.assertTrue(ledger.closure(s, self.predicates())['accepted'])
        self.assertEqual(ledger.seed(s)['tail'], s['tail'])

    def test_tampered_byte(self):
        self.path.write_bytes(self.path.read_bytes().replace(b'worker', b'Worker', 1))
        self.assertEqual(self.fold()['status'], 'INVALID_LEDGER')

    def test_deleted_middle(self):
        lines = self.path.read_bytes().splitlines(keepends=True)
        self.path.write_bytes(b''.join(lines[:1] + lines[2:]))
        self.assertEqual(self.fold()['status'], 'INVALID_LEDGER')

    def test_reordered(self):
        lines = self.path.read_bytes().splitlines(keepends=True)
        lines[1], lines[2] = lines[2], lines[1]
        self.path.write_bytes(b''.join(lines))
        self.assertEqual(self.fold()['status'], 'INVALID_LEDGER')

    def test_truncation(self):
        self.path.write_bytes(b''.join(self.path.read_bytes().splitlines(keepends=True)[:-1]))
        self.assertEqual(self.fold()['status'], 'INVALID_LEDGER')

    def test_appender_does_not_rewrite_anchor(self):
        before = self.anchor.read_bytes()
        self.add('episode_end', {'episode_id': 'ep', 'result': 'INCOMPLETE', 'last_observed_sha': SHA, 'evidence_refs': []})
        self.assertEqual(self.anchor.read_bytes(), before)
        self.assertEqual(self.fold()['status'], 'INVALID_LEDGER')

    def test_claim_without_verification(self):
        self.path.write_bytes(b''.join(self.path.read_bytes().splitlines(keepends=True)[:-1]))
        self.seal()
        self.assertEqual(len(self.fold()['unverified']), 1)
        self.assertFalse(ledger.closure(self.fold(), self.predicates())['accepted'])

    def test_self_verification(self):
        self.path.write_bytes(b''.join(self.path.read_bytes().splitlines(keepends=True)[:-1]))
        self.verify(actor='worker')
        self.seal()
        self.assertEqual(len(self.fold()['unverified']), 1)
        self.assertFalse(ledger.closure(self.fold(), self.predicates())['accepted'])

    def test_stale_sha(self):
        self.target['sha'] = OTHER
        self.assertEqual(len(self.fold()['verified_facts']), 0)

    def test_wrong_worktree(self):
        self.target['worktree_id'] = 'other'
        self.assertEqual(len(self.fold()['verified_facts']), 0)

    def test_unknown_supersession(self):
        with self.assertRaises(ledger.InvalidLedger):
            self.add('supersession', {'target_event_id': 'e2', 'replacement_event_id': 'missing', 'reason': 'new', 'evidence_refs': []})

    def test_conflicting_claim(self):
        self.claim(claim_id='c2', value='no')
        self.verify(claim_id='c2', verification_id='v2')
        self.seal()
        self.assertFalse(ledger.closure(self.fold(), self.predicates())['accepted'])
        self.assertTrue(self.fold()['conflicts'])

    def test_ci_different_sha(self):
        p = self.predicates()
        p['ci_sha'] = OTHER
        self.assertFalse(ledger.closure(self.fold(), p)['accepted'])

    def test_open_blocker(self):
        self.add('remaining_work', {'item_id': 'i', 'episode_id': 'ep', 'description': 'block', 'status': 'OPEN', 'blocker_refs': [], 'evidence_refs': []})
        self.seal()
        self.assertFalse(ledger.closure(self.fold(), self.predicates())['accepted'])

    def test_ledger_vs_snapshot(self):
        self.add('failure_evidence', {'failure_id': 'f', 'episode_id': 'ep', 'kind': 'test', 'observed_exit': 1, 'evidence_refs': ['evidence'], 'evidence_hashes': [self.digest], 'impact': 'blocked', 'recovery_status': 'OPEN'})
        self.verify(verification_id='failed', result='FAIL', exit_code=1)
        self.claim(claim_id='c2', value='new')
        self.verify(claim_id='c2', verification_id='v2')
        self.add('supersession', {'target_event_id': 'e2', 'replacement_event_id': 'e6', 'reason': 'corrected', 'evidence_refs': ['evidence']})
        self.seal()
        s = self.fold()
        history = s['events']
        self.assertEqual([e['timestamp'] for e in history if e['type'] == 'failure_evidence'], ['2026-01-01T00:00:00Z'])
        self.assertEqual([e['payload']['reason'] for e in history if e['type'] == 'supersession'], ['corrected'])
        self.target['sha'] = OTHER
        stale = self.fold()
        self.assertEqual({x['event']['payload']['claim_id'] for x in stale['unverified']}, {'c', 'c2'})
        snapshot = {'verified_facts': s['verified_facts']}
        self.assertNotIn('events', snapshot)
        self.assertNotIn('failures', snapshot)
        self.assertNotIn('supersession', snapshot)


if __name__ == '__main__':
    unittest.main()

class ClosureControls(LedgerTests):
    def test_each_missing_closure_predicate(self):
        for name, bad in [('artefact_in_merge', False), ('ancestry_matches', False),
                          ('merge_sha', OTHER), ('ci_success', False),
                          ('ci_post_merge', False), ('required_predicates', ['missing']),
                          ('open_blockers', ['blocked'])]:
            with self.subTest(predicate=name):
                p = self.predicates()
                p[name] = bad
                self.assertFalse(ledger.closure(self.fold(), p)['accepted'])

    def test_evidence_changed(self):
        (self.root / 'evidence').write_bytes(b'changed')
        self.assertFalse(self.fold()['verified_facts'])

    def test_verification_mismatch(self):
        self.target['repo_id'] = 'other'
        self.assertFalse(self.fold()['verified_facts'])
