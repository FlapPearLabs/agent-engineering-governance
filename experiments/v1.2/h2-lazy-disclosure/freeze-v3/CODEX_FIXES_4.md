# Freeze v2 — acceptance round 4 of f94360c: F8–F9 open (fix plan T21–T23)

Implementer: opencode (deepseek-v4.1-flash). The ground rules, NEVER TOUCH list and GATES of
CODEX_PLAN.md §0 still bind every task; write scope unchanged.

Accepted at f94360c (verified by Claude): write scope; identity; every gate green on independent
re-run; the driver's frozen constants (one worker command and one launch prompt for both arms,
PATH/LANG + profile env only, 90-minute limit).

## Findings

```text
F8  P1  THE WORKER CAN READ THE ANSWER. repo/ is a `git worktree add` of the governance
        repository, so it shares the whole object database. Reproduced in a real prepared f01
        run (control): `git for-each-ref | wc -l` = 104 refs, `git log --all` = 397 commits,
        `git cat-file -t <f01 candidate>` = commit, and
        `git log --all --grep "anchored schema patterns"` prints the candidate. Any worker can
        `git show` the historical fix. Both arms equally — it inflates correctness and makes the
        per-run audit meaningless.
F9  P1  NOTHING DETECTS ACCESS OUTSIDE THE RUN. With --auto the worker has the whole
        filesystem; the governance checkout itself (with the candidate's code) is on the same
        disk. The contract forbids it, but no frozen check reads the evidence that already
        exists: events.jsonl records every tool call input (read/glob/grep/edit/write paths,
        shell commands).
```

## T21 — close F8: a history-free task repository

- wrapper_delivery: repo/ becomes a STANDALONE repository whose object store holds exactly the
  base commit B' and its tree: e.g. `git clone --no-local --depth 1` of a temporary ref, then
  remove every remote, every other ref, FETCH_HEAD, packed-refs leftovers, reflogs and any
  `objects/info/alternates`; HEAD stays B' (same SHA, same metadata) so HEAD-metadata tests see
  what they saw. Postconditions (fail closed): `git rev-list --all` == [B']; `git remote` empty;
  no alternates; `git cat-file -e <candidate>` fails for this task's candidate; no path of the
  governance checkout appears anywhere under repo/.git.
- collect_v2 / run_acceptance_v2: adapt to the standalone repo (diff against B' still).
- Because the repository shape changed, RE-MEASURE with the new layout and record honestly:
  T2 delivery anchors (all 10 tasks, both arms; a test that depends on history now fails PRE
  and POST alike and is recorded, never hidden) and the T11 positive/negative controls (all 10
  tasks). README §2 numbers come only from the new JSON.

## T22 — close F9: access audit from the event stream

- `freeze-v3/access_audit.py`: reads events.jsonl and flags every tool call whose path argument,
  or any absolute/`~`/`$HOME`/`..`-escaping path inside a shell command, resolves outside the
  run dir, except a frozen allow-list of system locations needed to run tests (the pinned PY,
  /usr, /bin, /opt/homebrew, /System, /Library/Developer, the temp dirs). Also flag shell `git`
  invocations that try to reach other repositories (`remote add`, `fetch`, `clone`, `-C <path
  outside run dir>`) and any tool that is not in the frozen tool allow-list.
- run_h2r2: the access audit runs after the worker; any hit => INVALID:OUT_OF_RUN_ACCESS
  (registered, never re-run). The verdict lists every hit verbatim.
- Tests on fixtures: clean stream => PASS; each flagged shape => INVALID; allow-listed test
  runs => PASS.

## T23 — re-pin and report

Regenerate run plan / manifest / literals; append a T21–T23 section to CODEX_REPORT.md.
