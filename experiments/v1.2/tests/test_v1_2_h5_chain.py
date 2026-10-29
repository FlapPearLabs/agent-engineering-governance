"""Adversarial controls for the H5 chainability measurement (task C).

The measurement's job is to say "these two frozen tasks form a real chain link" and nothing
more. A check that cannot fail is not a check, so every way of looking chainable while not
being chainable gets a fixture here, in a real temporary git repository:

  F1  the oracle already accepts the base  -> ORACLE_ACCEPTS_THE_BASE
      (ancestry holds, nothing overlaps, the gate says ACCEPT — and still no link, because
      an oracle that passes before the repair proves nothing about a preserved verdict)
  F2  broken link                          -> BROKEN_LINK
      (`candidate_i` is not `base_j` and not an ancestor of it: two divergent lines)
  F3  dependent oracle                     -> ORACLE_DEPENDENCE
      (task j's delta edits task i's oracle surface: the verdict is not task i's any more)

  P0  positive control                     -> LINK
      (the same shape as F1 with the base still failing: the fixtures above fail for their
      stated reason, not because the measurement rejects everything)

Plus the fail-closed rules: a gate exception, a REJECT, and an unmeasured pair are never
links, and the gate is not even invoked once git has settled the pair.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TASKS = ROOT / 'experiments/v1.2/h5-verified-state/tasks'
REGISTRY = ROOT / 'experiments/v1.2/h2-lazy-disclosure/freeze-v3/task-registry-v3.json'


def load_measure():
    spec = importlib.util.spec_from_file_location('measure_chain', TASKS / 'measure_chain.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules['measure_chain'] = module
    spec.loader.exec_module(module)
    return module


measure = load_measure()


def run(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], capture_output=True, check=True).stdout


def commit(repo, message):
    run(repo, 'add', '-A')
    run(repo, '-c', 'user.name=H5', '-c', 'user.email=h5@example.invalid', 'commit', '-qm',
        message)
    return run(repo, 'rev-parse', 'HEAD').decode().strip()


def write(repo, rel, text):
    path = Path(repo) / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def build(tmp, *, dependent_oracle=False, diverged=False):
    """A two-task history: base_i -> candidate_i -> base_j -> candidate_j (or a fork for F2)."""
    repo = Path(tmp) / 'repo'
    repo.mkdir()
    run(repo, 'init', '-q', '-b', 'main')
    write(repo, 'src/one.py', 'VALUE = 0\n')
    write(repo, 'oracle/test_t1.py', 'T1 ORACLE\n')
    write(repo, 'oracle/test_t2.py', 'T2 ORACLE\n')
    trunk = commit(repo, 'trunk')
    write(repo, 'oracle/test_t1.py', 'T1 ORACLE EXTERNALIZED\n')
    base_i = commit(repo, 'h2-admission: externalized oracle for candidate_i')
    write(repo, 'src/one.py', 'VALUE = 1\n')
    candidate_i = commit(repo, 'fix(t1): make the t1 oracle pass')
    if diverged:
        run(repo, 'checkout', '-q', '-b', 'fork', trunk)
        write(repo, 'src/two.py', 'OTHER = 0\n')
        base_j = commit(repo, 'h2-admission: externalized oracle for candidate_j')
    else:
        write(repo, 'src/two.py', 'OTHER = 0\n')
        base_j = commit(repo, 'h2-admission: externalized oracle for candidate_j')
    write(repo, 'oracle/test_t1.py' if dependent_oracle else 'src/two.py',
          'T1 ORACLE REWRITTEN\n' if dependent_oracle else 'OTHER = 1\n')
    candidate_j = commit(repo, 'fix(t2): make the t2 oracle pass')
    first = {'id': 't1', 'base': base_i, 'candidate': candidate_i,
             'oracle_surface': ['oracle/test_t1.py']}
    second = {'id': 't2', 'base': base_j, 'candidate': candidate_j,
              'oracle_surface': ['oracle/test_t2.py']}
    return repo, first, second


def gate(verdict='ACCEPT', base_passing=False, calls=None):
    def accept_at(task, commit_sha):
        if calls is not None:
            calls.append((task['id'], commit_sha))
        return {'verdict': verdict, 'base_passing': base_passing, 'reasons': []}
    return accept_at


def forbidden(*_args, **_kwargs):
    raise AssertionError('the frozen gate must not run for a pair git already settled')


class ChainFixtures(unittest.TestCase):
    def test_f1_an_oracle_that_accepts_the_base_is_not_a_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp)
            result = measure.measure_pair(repo, first, second, gate(base_passing=True))
            self.assertTrue(result['ancestor'])
            self.assertEqual([], result['oracle_overlap'])
            self.assertEqual('ACCEPT', result['endpoint']['verdict'])
            self.assertFalse(result['chainable'])
            self.assertEqual('ORACLE_ACCEPTS_THE_BASE', result['reason'])

    def test_p0_the_same_shape_with_a_failing_base_is_a_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp)
            calls = []
            result = measure.measure_pair(repo, first, second, gate(calls=calls))
            self.assertTrue(result['chainable'], result['reason'])
            self.assertEqual('LINK', result['reason'])
            self.assertIn(('t1', second['base']), calls)
            self.assertIn(('t1', first['candidate']), calls)
            self.assertIn(('t2', second['candidate']), calls)
            self.assertIn(('t1', second['candidate']), calls)

    def test_f2_a_candidate_outside_the_next_base_is_a_broken_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp, diverged=True)
            result = measure.measure_pair(repo, first, second, forbidden)
            self.assertFalse(result['ancestor'])
            self.assertFalse(result['chainable'])
            self.assertEqual('BROKEN_LINK', result['reason'])
            self.assertIsNone(result['endpoint'])

    def test_f3_a_dependent_oracle_is_unchainable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp, dependent_oracle=True)
            result = measure.measure_pair(repo, first, second, forbidden)
            self.assertEqual(['oracle/test_t1.py'], result['oracle_overlap'])
            self.assertFalse(result['chainable'])
            self.assertEqual('ORACLE_DEPENDENCE', result['reason'])

    def test_equality_is_measured_too_and_needs_the_same_accept(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp)
            second = dict(second, base=first['candidate'])
            result = measure.measure_pair(repo, first, second, gate())
            self.assertTrue(result['equal'])
            self.assertTrue(result['chainable'], result['reason'])
            rejected = measure.measure_pair(repo, first, second, gate(verdict='REJECT'))
            self.assertFalse(rejected['chainable'])
            self.assertEqual('ORACLE_NOT_PRESERVED:REJECT', rejected['reason'])

    def test_the_gate_is_only_reached_when_git_leaves_the_pair_open(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp, dependent_oracle=True)
            calls = []
            measure.measure_pair(repo, first, second, gate(calls=calls))
            self.assertEqual([], calls)


class FailClosed(unittest.TestCase):
    def test_a_gate_exception_is_never_a_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp)

            def explode(_task, _commit):
                raise RuntimeError('DELTA_DOES_NOT_APPLY')

            result = measure.measure_pair(repo, first, second, explode)
            self.assertFalse(result['chainable'])
            self.assertEqual('MEASUREMENT_ERROR:RuntimeError', result['reason'])
            self.assertTrue(result['endpoint']['error'])

    def test_judge_rejects_unmeasured_and_non_accept_verdicts(self):
        relation = {'from': 't1', 'to': 't2', 'equal': False, 'ancestor': True,
                    'oracle_overlap': []}
        self.assertEqual((False, 'UNMEASURED'), measure.judge(relation, None))
        self.assertEqual((False, 'ORACLE_NOT_PRESERVED:INVALID'),
                         measure.judge(relation, {'verdict': 'INVALID'}))
        self.assertEqual((False, 'MEASUREMENT_ERROR:KeyError'),
                         measure.judge(relation, {'error': 'KeyError'}))
        self.assertEqual((False, 'BASE_OBSERVATION_UNKNOWN'),
                         measure.judge(relation, {'verdict': 'ACCEPT'}))
        self.assertEqual((True, 'LINK'), measure.judge(
            relation, {'verdict': 'ACCEPT', 'base_passing': False}))

    def test_a_measurement_error_makes_the_verdict_inconclusive_not_b(self):
        pairs = [{'from': 't1', 'to': 't2', 'chainable': False,
                  'reason': 'MEASUREMENT_ERROR:RuntimeError', 'endpoint': None}]
        summary = measure.summarise([{'id': 't1'}, {'id': 't2'}], pairs, [])
        self.assertEqual('INCONCLUSIVE', summary['verdict'])
        self.assertEqual(1, summary['measurement_errors'])


class IntermediateCensus(unittest.TestCase):
    def test_an_interval_that_leaves_the_fix_and_the_oracle_alone_is_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp)
            write(repo, 'docs/notes.md', 'unrelated\n')
            later = commit(repo, 'docs: unrelated note')
            census = measure.intermediate_census(repo, first, dict(second, base=later))
            self.assertEqual(3, census['commits'])        # base_j, candidate_j, the note
            self.assertEqual(0, census['touching_fix_paths'])
            self.assertEqual(0, census['touching_oracle'])
            self.assertEqual('NO_INTERMEDIATE_CHANGE', census['stability'])
            self.assertFalse(census['measured'])          # never claimed as re-run

    def test_an_interval_that_rewrites_the_fix_is_only_endpoint_measured(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp)
            write(repo, 'src/one.py', 'VALUE = 2\n')
            rewrite = commit(repo, 'refactor: touch the repaired file again')
            census = measure.intermediate_census(repo, first, dict(second, base=rewrite))
            self.assertEqual(1, census['touching_fix_paths'])
            self.assertEqual('ENDPOINT_ONLY', census['stability'])


class ReviewRegressions(unittest.TestCase):
    def test_next_candidate_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp)
            def oracle(task, _sha):
                return {'verdict': 'REJECT' if task['id'] == 't2' else 'ACCEPT',
                        'base_passing': False}
            self.assertFalse(measure.measure_pair(repo, first, second, oracle)['chainable'])

    def test_first_regresses_in_second_candidate(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp)
            write(repo, 'src/one.py', 'VALUE = 0\n')
            second = dict(second, candidate=commit(repo, 'regress first'))
            def oracle(task, sha):
                value = run(repo, 'show', sha + ':src/one.py').decode()
                return {'verdict': 'ACCEPT' if task['id'] == 't2' or 'VALUE = 1' in value
                        else 'REJECT',
                        'base_passing': False}
            result = measure.measure_pair(repo, first, second, oracle)
            self.assertFalse(result['chainable'])
            self.assertEqual('FINAL_FIRST:ORACLE_NOT_PRESERVED:REJECT', result['reason'])

    def test_dependency_regression_in_interval(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo, first, second = build(tmp)
            write(repo, 'src/dependency.py', 'bad')
            commit(repo, 'break dependency')
            write(repo, 'src/dependency.py', 'good')
            second = dict(second, base=commit(repo, 'restore dependency'))
            def oracle(_task, sha):
                files = run(repo, 'ls-tree', '-r', '--name-only', sha).decode()
                good = ('src/dependency.py' not in files or
                        run(repo, 'show', sha + ':src/dependency.py') == b'good')
                return {'verdict': 'ACCEPT' if good else 'REJECT', 'base_passing': False}
            self.assertFalse(measure.measure_pair(repo, first, second, oracle)['chainable'])

    def test_source_program_exists_at_head_and_dirty_source_is_detectable(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run(repo, 'init', '-q', '-b', 'main')
            write(repo, 'other', 'baseline\n')
            old = commit(repo, 'before program')
            write(repo, 'measure.py', 'original\n')
            sha = commit(repo, 'measurement source')
            self.assertFalse(measure.source_matches(repo, old, 'measure.py', ['measure.py']))
            self.assertTrue(measure.source_matches(repo, sha, 'measure.py', ['measure.py']))
            write(repo, 'measure.py', 'changed\n')
            self.assertFalse(measure.source_matches(repo, sha, 'measure.py', ['measure.py']))


class FrozenLoader(unittest.TestCase):
    def test_the_task_table_comes_from_the_frozen_file(self):
        frozen = json.loads(REGISTRY.read_text(encoding='utf-8'))
        tasks = measure.load_tasks()
        self.assertEqual([task['task_id'] for task in frozen['tasks']],
                         [task['id'] for task in tasks])
        for task in tasks:
            source = next(t for t in frozen['tasks'] if t['task_id'] == task['id'])
            self.assertEqual(source['base_sha'], task['base'])
            self.assertEqual(frozen['expected'][task['id']]['candidate_sha'],
                             task['candidate'])
            self.assertEqual([source['oracle']['path']], task['oracle_surface'])

    def test_a_registry_without_a_candidate_is_refused(self):
        frozen = json.loads(REGISTRY.read_text(encoding='utf-8'))
        dropped = frozen['tasks'][0]['task_id']
        frozen['expected'].pop(dropped)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'registry.json'
            path.write_text(json.dumps(frozen), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, f'NO_CANDIDATE_SHA:{dropped}'):
                measure.load_tasks(path)


class VerdictRule(unittest.TestCase):
    def test_two_links_hold_a_and_one_link_does_not(self):
        tasks = [{'id': name} for name in ('t1', 't2', 't3')]
        one = [{'from': 't1', 'to': 't2', 'chainable': True, 'reason': 'LINK', 'endpoint': {}},
               {'from': 't2', 'to': 't3', 'chainable': False, 'reason': 'BROKEN_LINK',
                'endpoint': None}]
        self.assertEqual('B', measure.summarise(tasks, one, [])['verdict'])
        two = one + [{'from': 't1', 'to': 't3', 'chainable': True, 'reason': 'LINK',
                      'endpoint': {}}]
        summary = measure.summarise(tasks, two, [])
        self.assertEqual('A', summary['verdict'])
        self.assertEqual(['t1', 't2'], summary['longest_chain'])
        self.assertEqual(2, summary['two_task_chains'])


if __name__ == '__main__':
    unittest.main()
