# T50 fork report

The v3 fork has separate registry, run plan, run IDs, manifest and test anchors. Its materials
commit is the parent of the T50 commit. Historical v2 documents and fixtures are context, not
evidence that a v3 run occurred. No model runs were performed.

Delivery anchors: `WRAPPER: 10` neutral tasks. Manifest build: 60 frozen files, delivery payload
verified equivalent to the measured payload. The v2 and v3 manifest checks both returned PASS.
The full experiment suite returned `Ran 733 tests ... OK`; the scripts suite returned
`Ran 602 tests ... OK`. Ruff passed; governance returned 35/35 and public release returned
`VIOLATIONS=0`. Earlier runs exposed stale fixture hashes, a v2 registry error assertion and
shared module names; the final suite passed after preserving the historical fixtures, updating the
assertion and isolating the v3 test module loader.

`git diff --cached --check` reports an extra blank line at EOF in the two copied historical
worker sandbox fixtures. Their bytes are retained as recorded; this whitespace check is not among
the T50 gates, and the two fixtures are pinned by the v3 manifest.

### T51a — partial implementation

Registration artifact hashing records symbolic links by target-string hash and records special
file types without opening them. Regular files are opened with `O_NOFOLLOW` and checked after
opening. A focused test covers link hashing, non-descent and a FIFO timeout.

Not completed: snapshot and other driver copies still need the requested no-follow treatment;
`sandbox_v2.py` snapshot code is outside this task's allowed ancestor-only edits. The cell layout
is not implemented: the existing `wrapper_delivery.py` driver-root calculation requires changes
outside the allowed write scope. Consequently T51a is not complete and the new test does not
claim the snapshot or cell-layout acceptance criteria.

Checks: the new unittest module ran 1 test (OK); ruff on the changed Python files passed;
`validate_public_release.py` reported `VIOLATIONS=0`; the freeze-v2 manifest check reported
`PASS` with no mismatches. The full freeze-v3 suite was not run.

### T51b — snapshot and cell layout

Snapshot copies now reject non-directory target collisions, create files exclusively without
following links, and open regular sources nonblocking with no-follow and a post-open type check.
The gate copy uses the same snapshot mechanism and rejects unreadable or colliding entries.
Runs use `.cells/<run_id>/<run_id>` with a private cell parent; legacy flat runs remain readable,
and driver artifacts remain under `.driver/<run_id>`. This closes T51a's identified snapshot
and cell-layout gaps. The directory-collision test simulates the case-folding collision by
planting a symlink at the target; it does not exercise an actual case-insensitive APFS collision.

Checks: driverfs unittest module (6 tests); ruff for changed Python files; public-release
validator `VIOLATIONS=0`; freeze-v2 manifest check `PASS`; `git diff --check`. The full freeze-v3
suite and re-pinning are deferred to T54; no live worker or platform sandbox launch was run.
### T51e — cell-only parent read, violation wiring (finished by opencode deepseek-v4.1-flash)

This task was started by Codex, whose session ended (quota) with an UNCOMMITTED working-tree diff;
opencode deepseek-v4.1-flash reviewed that diff, kept the parts that matched the task, corrected
the rest and finished the remaining work. What the partial diff got right: it removed the T51d
`(allow file-read-data (subpath <launch.parent>))` rule from `sandbox_v2.allow_rules` and added a
`ps`-based group poll around the launched process. What was wrong or missing: no cell-only parent
grant, no auditor collection (the guard `directory != run_dir` skipped nothing useful and the
auditor's start timestamp was never recorded), a second `sweep()` call inside `confined` (a new
kill path beside the auditor launch), the worker's evidence went to the stream directory instead of
the attempt directory, `violations_v3` raised a bare `TypeError` on a failing `log show` with no
reason recorded, `log show` got the driver's ISO/UTC timestamps in a spelling the T51d live test
never proved, and the pid set was built inside the record helper instead of at the launch.

Defect fix (1): the parent of a launch is no longer a `subpath` read grant for anyone. A cell run
dir `<runs_root>/.cells/<run_id>/<run_id>` gets its cell parent as a `literal` only; a legacy
flat-layout run dir and a directory inside a run (the auditor's `audit`) get no parent grant at
all, so a flat worker can no longer read the whole runs root and the auditor can no longer read the
worker's run dir as a tree. New helper `sandbox_v2.cell_parent()` implements the
`wrapper_delivery.runs_root_of` cell test (`parent.name == launch.name and
parent.parent.name == ".cells"`).

Violation wiring (2): `run_h2r2.py` now collects `violations_v3.collect_violations` per confined
launch of a run. The start stamp is taken in `confine_state` immediately before the launch's
`opencode serve` starts and the end stamp is taken when the evidence is written — for the worker
after the post-launch `sweep`, so the sweep's pids join the pid set. The pid set
(`run_h2r2.pid_set`) is the launched pid, every pid the 0.5 s process-group poll saw, the serve
pid and its group members at stop time, and — for non-worker launches — one `processes_under` lsof
pass. Files land in `.driver/<run_id>/attempt-<n>/violations-<launch>.jsonl`
(`violations_path`), and `{"path", "count", "sha256"}` is stored in `record["violations"]`, in
`record["observed_pids"]`, in each auditor entry of `record["audit_sandbox"]`, and in the launch
record the access audit already receives (`record["sandbox"]["confinement"]["violations"]`, handed
over as `confinement=`; `access_audit.py` was not edited). A collector failure is recorded as
`{"error", "reason"}` and the run continues. `violations_v3.stamp()` converts the driver's ISO/UTC
stamps to the one local spelling the T51d live test proved (`%Y-%m-%d %H:%M:%S%z`) and passes an
unparseable value through unchanged.

Limits, stated as limits: the pid set is a LOWER BOUND — a child that starts and exits between two
observations is not attributed, and the report says so instead of claiming a full process tree.
`log show` returns the denials the unified log still holds for the window; it is evidence, never a
verdict. Gate executions are still NOT collected: they are launched inside `run_acceptance_v2.py`
(not in this task's write scope), so gate-run violations remain uncollected and T52 §2 consumes
violations "when present" only. A real auditor launch was not run (it needs a model): the auditor
shares the `confined` code path that the probes exercised, and its record key is populated from
`audit["launch"]["violations"]`; with the suite's stub auditor it is `null`.

Tests: new module `experiments/v1.2/tests/test_v1_2_h2_freeze_v3_violations.py`, 13 tests, all OK
— rendered rules for a cell worker, a flat-layout worker and an auditor dir; a live
`sandbox-exec` check that the auditor cannot read a file in the run dir outside its audit dir and
that a cell worker can list its cell parent; `violations_path` per launch; path/count/sha
recorded; an empty collection hashed (count 0) rather than treated as an error; collector
exception and an unwritable path recorded and non-fatal; pid set = serve + launched + group +
sweep pids; `pid_set` ignoring junk entries; a real `launch` returning the pid it observed; the
timestamp spelling. One end-to-end check with the v3 suite's stubs (throwaway script, not committed)
produced `record["violations"]` = `.driver/h2r3-f01-c/attempt-1/violations-worker.jsonl`, count 0,
sha256 `e3b0c442…b855`, `observed_pids` = two pids (worker + serve), the same dict in
`record["sandbox"]["confinement"]["violations"]`, and `violations-probe-worker-1.jsonl` /
`violations-probe-auditor-1.jsonl` beside it.

Checks: ruff on the four touched files passed; `scripts/validate_public_release.py` reported
`VIOLATIONS=0`; `freeze-v2/build_manifest.py check` reported `PASS` with no mismatches; the new
module ran 13 tests (OK). Two existing freeze-v3 tests in the suite
(`test_the_frozen_env_is_exactly_what_the_worker_and_the_auditor_receive` and
`test_the_default_probe_confines_launches_and_reaches_the_worker`) fail on an unchanged
`run_dir = runs / "<id>"` expectation that the T51b cell layout replaced; that mismatch predates
this task and its fix is not in this write scope. The full freeze-v3 suite and re-pinning are
deferred to T54; no pinned literal was edited, no model ran, and `run_h2r2.py` was not run against
a real runs root.

### T51d — sandbox reads and violation evidence

Added a read allowlist, interpreter and opencode prefix resolution, and a standalone unified-log collector; the driver is not wired here. On 2026-10-28 (Darwin 25, opencode 2.0.25), the five requested commands exited successfully in the candidate sandbox with a launch-local TMPDIR. Iterative unified-log inspection identified the listed system paths and Homebrew git dependencies. The live test observed a denial for its child PID. The profile does not set a launch tag; filtering uses event-message PIDs.

Limitation: the five commands still emit `file-write-data /dev/dtracehelper` denials. Thus the requested zero-denial measurement was not achieved; the write whitelist was kept unchanged. System roots are candidate measurements, not a proven minimal list. The full freeze-v3 suite and re-pin were intentionally not run. The new tests, lint, release scanner and freeze-v2 manifest checks were run separately; see session output for results.
