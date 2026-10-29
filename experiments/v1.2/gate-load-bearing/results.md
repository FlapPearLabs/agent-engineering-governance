# N7 results

The worktree run below used base commit `98de40f8d6b20e1f791fa857504a851a63cd5609`
plus the then-current uncommitted candidate files. The committed-tree run is recorded below.

All commands used the requested Python interpreter, with PYTHONPATH unset and
TMPDIR set to the physical temporary directory. The interpreter directory was
prepended to PATH for tests which invoke `python` themselves.

```text
$ python -m ruff check .
All checks passed!
$ python scripts/validate_governance.py
35/35 checks passed
$ python scripts/validate_public_release.py
VIOLATIONS=0
$ python -m unittest discover -s scripts/tests
Ran 602 tests in 24.868s
OK
$ python -m unittest discover -s experiments/v1.2/tests -p test_v1_2_gate_load_bearing.py
......
----------------------------------------------------------------------
Ran 6 tests in 171.384s

OK
```

The preceding excerpts retain the final result lines, not the complete output.
The test module checks the intact probe, empty and narrowed selection, ignore,
exclude, hollow governance and selftest, broken controls, exit modes and caller
byte identity. An independent review and the full v1.2 experiment suite have not
been completed here.

The #45 replay modifies only a scratch copy:

```text
$ python experiments/v1.2/gate-load-bearing/replay_issue_45.py
[
  {
    "id": "ruff",
    "status": "GATE_NOT_LOAD_BEARING",
    "detail": "effective rules differ from E9,F"
  }
]
```

Worktree matrix, exit 0:

```json
{
  "ref": null,
  "worktree": true,
  "gates": [
    {
      "id": "compile",
      "status": "LOAD_BEARING",
      "detail": "SyntaxError"
    },
    {
      "id": "ruff",
      "status": "LOAD_BEARING",
      "detail": "F841"
    },
    {
      "id": "governance",
      "status": "LOAD_BEARING",
      "detail": "FAIL  markdown-links-resolve"
    },
    {
      "id": "scripts-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "cli-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "continuity-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "workbuddy-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "public-release",
      "status": "LOAD_BEARING",
      "detail": "UNIX_USER_HOME"
    },
    {
      "id": "metadata",
      "status": "LOAD_BEARING",
      "detail": "PUBLIC_ACCOUNT_IDENTITY"
    },
    {
      "id": "selftest",
      "status": "LOAD_BEARING",
      "detail": "FAIL  01-public-rejects-unix-user-home"
    },
    {
      "id": "history",
      "status": "LOAD_BEARING",
      "detail": "PASSWORD_ASSIGNMENT"
    }
  ],
  "no_positive_control": []
}
```

Committed-tree probe: exact pre-amend SHA
`b8a6ef5f2beaaec3c2de2a0617c5b887bf8ab14f`. The final amended commit has the
same tree as that SHA except for this results.md update. This output was taken
on the pre-amend SHA, not the final amended SHA.

```text
$ python experiments/v1.2/gate-load-bearing/probe_gates.py --ref HEAD
{
  "ref": "HEAD",
  "worktree": false,
  "gates": [
    {
      "id": "compile",
      "status": "LOAD_BEARING",
      "detail": "SyntaxError"
    },
    {
      "id": "ruff",
      "status": "LOAD_BEARING",
      "detail": "F841"
    },
    {
      "id": "governance",
      "status": "LOAD_BEARING",
      "detail": "FAIL  markdown-links-resolve"
    },
    {
      "id": "scripts-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "cli-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "continuity-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "workbuddy-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "public-release",
      "status": "LOAD_BEARING",
      "detail": "UNIX_USER_HOME"
    },
    {
      "id": "metadata",
      "status": "LOAD_BEARING",
      "detail": "PUBLIC_ACCOUNT_IDENTITY"
    },
    {
      "id": "selftest",
      "status": "LOAD_BEARING",
      "detail": "FAIL  01-public-rejects-unix-user-home"
    },
    {
      "id": "history",
      "status": "LOAD_BEARING",
      "detail": "PASSWORD_ASSIGNMENT"
    }
  ],
  "no_positive_control": []
}
exit=0
```
