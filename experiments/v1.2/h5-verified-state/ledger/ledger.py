"""H5 reference ledger. Anchor protection and identity authentication are external.

Evidence references are relative paths under an independently supplied evidence root.
Git object IDs use the form ``sha1:<40 hex>`` or ``sha256:<64 hex>``.
"""
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path

ZERO = '0' * 64
FIELDS = {
    'goal': ('goal_id', 'text_hash', 'authority_ref', 'repo_id', 'base_sha', 'predicate_specs'),
    'episode_start': ('episode_id', 'arm', 'repo_id', 'worktree_id', 'head_sha', 'seed_head_hash', 'context_id'),
    'state_claim': ('claim_id', 'episode_id', 'subject', 'value', 'repo_id', 'worktree_id', 'candidate_sha', 'predicate_id', 'predicate_version', 'evidence_refs'),
    'verification': ('verification_id', 'claim_id', 'independent_verifier_id', 'predicate_id', 'predicate_version', 'repo_id', 'worktree_id', 'sha', 'result', 'command', 'exit_code', 'evidence_refs', 'evidence_hashes'),
    'failure_evidence': ('failure_id', 'episode_id', 'kind', 'observed_exit', 'evidence_refs', 'evidence_hashes', 'impact', 'recovery_status'),
    'remaining_work': ('item_id', 'episode_id', 'description', 'status', 'blocker_refs', 'evidence_refs'),
    'supersession': ('target_event_id', 'replacement_event_id', 'reason', 'evidence_refs'),
    'episode_end': ('episode_id', 'result', 'last_observed_sha', 'evidence_refs'),
}
COMMON = {'version', 'ledger_id', 'seq', 'prev_hash', 'type', 'event_id', 'timestamp', 'actor_id', 'payload', 'hash'}


class InvalidLedger(ValueError):
    pass


def _json(value):
    def check(v):
        if isinstance(v, float) or v is None:
            raise InvalidLedger('unsupported JSON value')
        if isinstance(v, dict):
            if any(not isinstance(k, str) for k in v):
                raise InvalidLedger('non-string key')
            for x in v.values():
                check(x)
        elif isinstance(v, list):
            for x in v:
                check(x)
        elif not isinstance(v, (str, int, bool)):
            raise InvalidLedger('unsupported JSON value')
    check(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _hash(value):
    return hashlib.sha256(_json(value)).hexdigest()


def _pairs(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise InvalidLedger('duplicate key')
        d[k] = v
    return d


def _sha(s):
    return isinstance(s, str) and bool(re.fullmatch(r'(?:sha1:[0-9a-f]{40}|sha256:[0-9a-f]{64})', s))


def _read(path):
    data = Path(path).read_bytes()
    if not data or not data.endswith(b'\n'):
        raise InvalidLedger('empty or partial ledger')
    events = []
    ids, claims, episodes, ended, identities = {}, {}, {}, set(), set()
    prev = ZERO
    supersession_targets = set()
    for line in data.splitlines():
        e = json.loads(line, object_pairs_hook=_pairs)
        if _json(e) != line or set(e) != COMMON or e['version'] != 1 or type(e['version']) is not int:
            raise InvalidLedger('noncanonical or invalid record')
        typ, p = e['type'], e['payload']
        if typ not in FIELDS or not isinstance(p, dict) or set(p) != set(FIELDS[typ]):
            raise InvalidLedger('unknown type or payload schema')
        if type(e['seq']) is not int or e['seq'] != len(events) or e['prev_hash'] != prev or e['hash'] != _hash({k: v for k, v in e.items() if k != 'hash'}):
            raise InvalidLedger('chain mismatch')
        if any(not isinstance(e[k], str) or not e[k] for k in ('ledger_id', 'event_id', 'timestamp', 'actor_id')) or e['event_id'] in ids or (events and e['ledger_id'] != events[0]['ledger_id']):
            raise InvalidLedger('identity mismatch')
        if (not events and typ != 'goal') or (events and typ == 'goal'):
            raise InvalidLedger('invalid genesis')
        lists = {'predicate_specs', 'evidence_refs', 'evidence_hashes', 'blocker_refs'}
        for k, v in p.items():
            if k in lists:
                if not isinstance(v, list):
                    raise InvalidLedger('expected list')
            elif k in ('exit_code', 'observed_exit'):
                if type(v) is not int:
                    raise InvalidLedger('expected exit code')
            elif k != 'value' and (not isinstance(v, str) or not v):
                raise InvalidLedger('expected nonempty string')
        for k in ('base_sha', 'head_sha', 'candidate_sha', 'sha', 'last_observed_sha'):
            if k in p and not _sha(p[k]):
                raise InvalidLedger('invalid git object id')
        for k in ('evidence_refs', 'blocker_refs'):
            if k in p and any(not isinstance(x, str) or not x for x in p[k]):
                raise InvalidLedger('invalid reference')
        if 'evidence_hashes' in p and (len(p['evidence_hashes']) != len(p['evidence_refs']) or any(not isinstance(h, str) or not re.fullmatch('[0-9a-f]{64}', h) for h in p['evidence_hashes'])):
            raise InvalidLedger('invalid evidence hashes')
        ep = p.get('episode_id')
        if typ == 'episode_start':
            if ep in episodes or p['repo_id'] != events[0]['payload']['repo_id']:
                raise InvalidLedger('invalid episode')
            episodes[ep] = p
        elif ep is not None and (ep not in episodes or ep in ended):
            raise InvalidLedger('unknown or ended episode')
        if typ == 'episode_end':
            ended.add(ep)
        if typ == 'state_claim' and any(p[k] != episodes[ep][k] for k in ('repo_id', 'worktree_id')):
            raise InvalidLedger('claim episode identity mismatch')
        for key in ('goal_id', 'claim_id', 'verification_id', 'failure_id', 'item_id'):
            if key in p and not (key == 'claim_id' and typ == 'verification'):
                identity = (key, p[key])
                if identity in identities:
                    raise InvalidLedger('duplicate identity')
                identities.add(identity)
        if typ == 'state_claim':
            if p['claim_id'] in claims:
                raise InvalidLedger('duplicate claim')
            claims[p['claim_id']] = e
        if typ == 'verification':
            if p['claim_id'] not in claims or p['result'] not in ('PASS', 'FAIL', 'UNKNOWN'):
                raise InvalidLedger('invalid verification')
        if typ == 'remaining_work' and p['status'] not in ('OPEN', 'BLOCKED', 'DONE_CLAIM'):
            raise InvalidLedger('invalid work status')
        if typ == 'episode_end' and p['result'] not in ('COMPLETE_CLAIM', 'INCOMPLETE', 'ENV_BLOCKED'):
            raise InvalidLedger('invalid end result')
        if typ == 'supersession':
            a, b = ids.get(p['target_event_id']), ids.get(p['replacement_event_id'])
            if not a or not b or a['type'] != 'state_claim' or b['type'] != 'state_claim' or a['payload']['subject'] != b['payload']['subject'] or a == b or a['event_id'] in supersession_targets or b['event_id'] in supersession_targets:
                raise InvalidLedger('invalid supersession')
            supersession_targets.add(a['event_id'])
        for ref in p.get('blocker_refs', []):
            if ref not in ids:
                raise InvalidLedger('dangling blocker')
        ids[e['event_id']] = e
        events.append(e)
        prev = e['hash']
    return events


def append(ledger, record):
    """Compare and append under an exclusive advisory lock; never touch anchor."""
    path = Path(ledger)
    with path.open('a+b') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        old = f.read()
        line = _json(record) + b'\n'
        # Validate the prospective complete ledger before modifying the real file.
        import tempfile
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.write(old + line)
            tmp.flush()
            _read(tmp.name)
        f.seek(0, os.SEEK_END)
        f.write(line)
        f.flush()
        os.fsync(f.fileno())


def make_record(ledger_id, seq, prev_hash, typ, event_id, timestamp, actor_id, payload):
    record = dict(version=1, ledger_id=ledger_id, seq=seq, prev_hash=prev_hash,
                  type=typ, event_id=event_id, timestamp=timestamp, actor_id=actor_id, payload=payload)
    record['hash'] = _hash(record)
    return record


def anchor(ledger, anchor_path):
    """Trusted caller persists the validated tail; storage access is caller-owned."""
    events = _read(ledger)
    p = Path(anchor_path)
    if p.resolve() == Path(ledger).resolve():
        raise InvalidLedger('anchor must be separate')
    with p.open('w', encoding='utf-8') as f:
        f.write(events[-1]['hash'] + '\n')
        f.flush()
        os.fsync(f.fileno())


def _evidence(root, refs, hashes):
    if not refs or len(refs) != len(hashes):
        return False
    try:
        base = Path(root).resolve(strict=True)
        for ref, expected in zip(refs, hashes):
            path = (base / ref).resolve(strict=True)
            if not path.is_relative_to(base) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                return False
        return True
    except (OSError, ValueError, TypeError):
        return False


def fold(ledger, anchor_path, actual_target, evidence_root):
    try:
        events = _read(ledger)
        if Path(anchor_path).resolve() == Path(ledger).resolve() or Path(anchor_path).read_text(encoding='utf-8') != events[-1]['hash'] + '\n':
            raise InvalidLedger('anchor mismatch')
        if not isinstance(actual_target, dict) or any(not isinstance(actual_target.get(k), str) or not actual_target[k] for k in ('repo_id', 'worktree_id', 'sha')) or not _sha(actual_target['sha']):
            return {'status': 'UNKNOWN'}
        claims = [e for e in events if e['type'] == 'state_claim']
        verifications = [e for e in events if e['type'] == 'verification']
        verified, unverified = [], []
        for c in claims:
            p = c['payload']
            matches = []
            for v in verifications:
                q = v['payload']
                if (q['claim_id'] == p['claim_id'] and q['result'] == 'PASS' and q['exit_code'] == 0
                    and q['independent_verifier_id'] == v['actor_id'] and v['actor_id'] != c['actor_id']
                    and all(q[k] == p[k] for k in ('repo_id', 'worktree_id', 'predicate_id', 'predicate_version'))
                    and q['sha'] == p['candidate_sha'] == actual_target['sha']
                    and all(p[k] == actual_target[k] for k in ('repo_id', 'worktree_id'))
                    and q['evidence_refs'] == p['evidence_refs'] and _evidence(evidence_root, q['evidence_refs'], q['evidence_hashes'])):
                    matches.append(v['event_id'])
            (verified if matches else unverified).append({'event': c, 'verification_ids': matches})
        verified_ids = {x['event']['event_id'] for x in verified}
        superseded = {e['payload']['target_event_id'] for e in events if e['type'] == 'supersession' and e['payload']['replacement_event_id'] in verified_ids}
        active = [x for x in verified if x['event']['event_id'] not in superseded]
        conflicts = []
        for i, a in enumerate(active):
            for b in active[i + 1:]:
                pa, pb = a['event']['payload'], b['event']['payload']
                if pa['subject'] == pb['subject'] and pa['value'] != pb['value']:
                    conflicts.append([a['event']['event_id'], b['event']['event_id']])
        return {'status': 'VALID', 'goal': events[0], 'events': events, 'tail': events[-1]['hash'],
                'target': actual_target, 'verified_facts': active, 'unverified': unverified,
                'conflicts': conflicts, 'failures': [e for e in events if e['type'] == 'failure_evidence'],
                'remaining_work': [e for e in events if e['type'] == 'remaining_work']}
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        return {'status': 'INVALID_LEDGER'}


def closure(state, predicates):
    """Evaluate explicit stand-in observations; missing and unknown never pass."""
    result = {'CLOSURE_SOURCE': 'STAND_IN', 'accepted': False, 'missing': []}
    if state.get('status') != 'VALID' or not isinstance(predicates, dict):
        result['missing'].append('valid_ledger')
        return result
    sha = state['target']['sha']
    for key in ('artefact_in_merge', 'ancestry_matches'):
        if predicates.get(key) is not True:
            result['missing'].append(key)
    if predicates.get('merge_sha') != sha or predicates.get('ci_sha') != sha or predicates.get('ci_success') is not True or predicates.get('ci_post_merge') is not True:
        result['missing'].append('post_merge_ci_same_sha')
    required = predicates.get('required_predicates')
    facts = {x['event']['payload']['predicate_id'] for x in state['verified_facts']}
    if not isinstance(required, list) or not required or any(not isinstance(x, str) or x not in facts for x in required):
        result['missing'].append('required_verifications')
    if state['conflicts']:
        result['missing'].append('conflicts')
    if any(e['payload']['status'] in ('OPEN', 'BLOCKED', 'DONE_CLAIM') for e in state['remaining_work']) or predicates.get('open_blockers') != []:
        result['missing'].append('open_blockers')
    result['accepted'] = not result['missing']
    return result


def seed(state):
    if state.get('status') != 'VALID':
        return {'status': state.get('status', 'INVALID_LEDGER')}
    return {'status': 'VALID', 'goal': state['goal'], 'verified_facts': state['verified_facts'],
            'unverified': state['unverified'], 'failures': [e for e in state['failures'] if e['payload']['recovery_status'] != 'RESOLVED'],
            'remaining_work': state['remaining_work'], 'conflicts': state['conflicts'],
            'target': state['target'], 'tail': state['tail']}
