# H5 ledger reference

## Review fixes (9634a0b)

The fold snapshots the target and retains a target reader. Production callers must provide a trusted callable that reads the current repo, worktree and HEAD each time; a dict is only a mutable test stand-in and cannot detect changes outside that dict. Seed and closure fail closed if the reader no longer matches. The hash and inputs in each goal specification are frozen metadata; verification identifies its predicate by ID and version, and the trusted verifier is responsible for applying the corresponding frozen inputs and hash. A DONE_CLAIM is resolved only by an active independently verified claim whose subject is the item ID and whose value is the JSON string `DONE`; its history remains in the ledger.

Reproductions below are the reviewer's unmodified scripts copied into a temporary directory, with `repo` symlinked to this tree. `PY` denotes the specified Python interpreter; `W=/tmp/h5-ledger-repro`. Each Python invocation used `env -u PYTHONPATH TMPDIR=/tmp` and PATH prefixed with the interpreter directory. Output lines below are verbatim selections; before is the 9634a0b tree and after is this fix. The R10 before output is the original reviewer log. The scripts include unrelated probes; their output is omitted here.

### R01 — `attack_ledger.py`

Command: `env -u PYTHONPATH TMPDIR=/tmp "$PY" "$W/attack_ledger.py"`

before:

```text
{"case": "frozen_predicate_omitted", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": true, "missing": []}, "goal": [{"hash": "c1cda26362828b69266512052b97cb3729e3b052e4ade47c0a1e3383defe73c7", "id": "p", "inputs": {}, "version": "1"}, {"hash": "c1cda26362828b69266512052b97cb3729e3b052e4ade47c0a1e3383defe73c7", "id": "q", "inputs": {}, "version": "1"}], "verified": ["p"]}
```

after:

```text
{"case": "frozen_predicate_omitted", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": false, "missing": ["required_verifications", "predicate:q@1"]}, "goal": [{"hash": "c1cda26362828b69266512052b97cb3729e3b052e4ade47c0a1e3383defe73c7", "id": "p", "inputs": {}, "version": "1"}, {"hash": "c1cda26362828b69266512052b97cb3729e3b052e4ade47c0a1e3383defe73c7", "id": "q", "inputs": {}, "version": "1"}], "verified": ["p"]}
```


### R01 — `extra_ledger.py`

Command: `env -u PYTHONPATH TMPDIR=/tmp "$PY" "$W/extra_ledger.py"`

before:

```text
{"case": "predicate_version_not_goal_version", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": true, "missing": []}, "state": "VALID", "verified": 1}
{"case": "predicate_specs_wrong_element_types", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": true, "missing": []}, "state": "VALID", "verified": 1}
```

after:

```text
{"case": "predicate_version_not_goal_version", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": false, "missing": ["required_verifications", "predicate:p@2"]}, "state": "VALID", "verified": 1}
{"case": "predicate_specs_wrong_element_types", "error": "InvalidLedger", "message": "invalid predicate_specs"}
```


### R02 — `state_alias.py`

Command: `env -u PYTHONPATH TMPDIR=/tmp "$PY" "$W/state_alias.py"`

before:

```text
{"case": "target_alias_after_fold", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": true, "missing": []}, "fact_sha": "sha1:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "same_object": true, "target": "sha1:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"}
```

after:

```text
KeyError: 'target'
```

The original script expects the stale seed to contain a target and aborts on the fail-closed result. The regression also asserts the copied target, stale seed status, and closure reason, including a live-reader case.

### R03 — `attack_ledger.py`

Command: `env -u PYTHONPATH TMPDIR=/tmp "$PY" "$W/attack_ledger.py"`

before:

```text
{"case": "done_work_verified", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": false, "missing": ["open_blockers"]}, "verified": 2}
```

after:

```text
{"case": "done_work_verified", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": true, "missing": []}, "verified": 2}
```


### R05 — `extra_ledger.py`

Command: `env -u PYTHONPATH TMPDIR=/tmp "$PY" "$W/extra_ledger.py"`

before:

```text
{"case": "empty_snapshot_control", "passed": true, "testsRun": 1}
```

after:

```text
{"case": "empty_snapshot_control", "passed": false, "testsRun": 1}
```


### R07 — `attack_ledger.py`

Command: `env -u PYTHONPATH TMPDIR=/tmp "$PY" "$W/attack_ledger.py"`

before:

```text
{"case": "bool_int_conflict", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": true, "missing": []}, "conflicts": [], "values": [1, true]}
```

after:

```text
{"case": "bool_int_conflict", "closure": {"CLOSURE_SOURCE": "STAND_IN", "accepted": false, "missing": ["conflicts"]}, "conflicts": [["e2", "e4"]], "values": [1, true]}
```


### R08 — `canonical_check.py`

Command: `env -u PYTHONPATH TMPDIR=/tmp "$PY" "$W/canonical_check.py"`

before:

```text
{"case": "RFC8785_UTF16_sorted_ledger", "fold": "INVALID_LEDGER", "value_expected": "{\"😀\":1,\"�\":2}", "value_implementation": "{\"�\":2,\"😀\":1}"}
```

after:

```text
{"case": "RFC8785_UTF16_sorted_ledger", "fold": "VALID", "value_expected": "{\"😀\":1,\"�\":2}", "value_implementation": "{\"😀\":1,\"�\":2}"}
```


### R10 — direct test entry

Command: `env -u PYTHONPATH TMPDIR=/tmp "$PY" "$W/execute.py" experiments/v1.2/tests/test_v1_2_h5_ledger.py`

Before (reviewer log):

```text
...............
----------------------------------------------------------------------
Ran 15 tests in 0.033s

OK
```

After:

```text
.......................................................
----------------------------------------------------------------------
Ran 55 tests in 0.478s

OK
```

The test suite also compares direct-entry and module-discovery test counts. The snapshot control preserves the final facts and tests distinguishable histories, including different failure times, supersession reasons, and verification SHA staleness. The empty-snapshot mutation is rejected.
