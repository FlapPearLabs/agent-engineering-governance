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
### T51d — sandbox reads and violation evidence

Added a read allowlist, interpreter and opencode prefix resolution, and a standalone unified-log collector; the driver is not wired here. On 2026-10-28 (Darwin 25, opencode 2.0.25), the five requested commands exited successfully in the candidate sandbox with a launch-local TMPDIR. Iterative unified-log inspection identified the listed system paths and Homebrew git dependencies. The live test observed a denial for its child PID. The profile does not set a launch tag; filtering uses event-message PIDs.

Limitation: the five commands still emit `file-write-data /dev/dtracehelper` denials. Thus the requested zero-denial measurement was not achieved; the write whitelist was kept unchanged. System roots are candidate measurements, not a proven minimal list. The full freeze-v3 suite and re-pin were intentionally not run. The new tests, lint, release scanner and freeze-v2 manifest checks were run separately; see session output for results.

### T51c — audit retry entry (`AUDIT_RESOLVED`)

Finished by opencode (deepseek-v4.1-flash) on top of a partial Codex diff that was left uncommitted:
the registry reader applied an `AUDIT_RESOLVED` line over a run and the protocol carried a short
paragraph. That reading was kept (and extended); the `audit` command, the audit factoring and the
stubbed integration tests did not exist and are written here.

What changed:

- `run_h2r2.py audit --runs-root R <run_id>` (`audit_retry`). Refused, with a `ValueError` and
  nothing appended, when the run is not registered, its latest state is not `BLOCKED`, any of its
  `;`-separated reasons does not start with `AUDIT_BLOCKED`, its three retries are used up, its
  frozen materials are missing, no sandbox is available, or a live process holds its lock. One
  attempt, over the run's existing frozen materials (driver `CONTRACT.md`, the snapshot's
  `report.md`, the run's `collected.json`/`verdict.json`), with the same model, rules, reachability
  probe and confinement; the worker is never launched and the run directory is only read. Its
  bundle, home, rendered profile, stream and egress log live under
  `.driver/<run_id>/audit-retry-<n>/`. It appends exactly one line — `{"kind": "AUDIT_RESOLVED",
  "run_id", "audit_retry", "verdict", "audit", "resolved_at", ...}` — where `verdict` is
  `strictest(mechanical, audit)` exactly as registration computes it, and it appends the same line
  with `verdict: "BLOCKED"` when the retry is blocked again. Earlier lines are never rewritten.
- Factoring: the body of the in-run audit loop became `audit_attempt()`, called by both paths; the
  caller injects where a blocked attempt is archived, so the retry writes nothing into the run dir.
  The four launch closures (`fresh_state`, `confine_state`, `release`, `confined`) and the default
  probe moved verbatim into `launch_tools()`; the only changed expression is
  `state["master_env"]` → a `master_env()` getter, because a run sets its profile just before its
  first fresh state. `launch_server`/`confine_state` were not restructured.
- `aggregate_runs.py`: `registry_entries` applies the latest `AUDIT_RESOLVED` over the original
  entry (mechanical verdict and its non-audit reasons preserved; the audit-blocked reasons
  replaced), still rejects every other duplicate and a resolution for an unregistered run;
  `audited_for` reads the resolution's audit; `audit_record` is one shared validator; the aggregate
  row exposes `audit_retry`. `run_h2r2.status` shows `audit_retry`/`resolved_at`.
- `run_audit_v2.prepare_bundle`/`audit` take `bundle_dir`, so the same blind bundle can be built
  outside the run directory; the in-run default is unchanged.
- `aggregate_set.py` is unchanged: the retry changes no task membership (`derive` reads admission
  records and the frozen task registry, neither of which it touches).
- `protocol-v3.md` §6.1.1 pre-registers the rule (trigger, 3-retry budget, same frozen model, same
  materials and rules, appended evidence, latest resolution wins).

Checks: the new module `experiments/v1.2/tests/test_v1_2_h2_freeze_v3_auditretry.py` ran 10 tests,
OK (stub worker/auditor/probe/sandbox; the frozen acceptance gate is stubbed because the mechanical
verdict is not what this item decides). It covers: refusal for a non-`BLOCKED` run, for a
`BLOCKED` run with a non-audit reason, for an unregistered run and for the exhausted budget; one
appended line with the earlier bytes unchanged and the run directory byte-identical; a blocked
retry appended as `BLOCKED`; the aggregate taking the latest resolution; the bundle built outside
the run dir; the CLI exiting 1 on a refusal; and the in-run audit's registry fields. For that last
one the same stubbed run was executed against `HEAD`'s modules and against this change: the
registry line (minus session id, timestamps and hashes) is byte-identical, and the test pins the
exact field set plus `audit_verdict`/`final_verdict`/reason/attempt numbers. Ruff passed on the
three changed modules, `validate_public_release.py` reported `VIOLATIONS=0` and the freeze-v2
manifest check reported `PASS`.

Not done / limits:

- The full freeze-v3 suite was not run and nothing was re-pinned (T54 owns that). `run_h2r2.py`,
  `aggregate_runs.py`, `run_audit_v2.py` and `protocol-v3.md` hashes in the v3 manifest and in the
  v3 test module's literal table are therefore stale by design.
- The frozen v3 test module already fails 18 of the 61 driver/aggregate/registry tests on `HEAD` in
  this environment (flat-run-dir paths from T51b's cell layout, the `DENY_ROOTS` literal from T51d,
  and the acceptance gate's own sandbox self-test returning `GATE_SANDBOX_NOT_CONFINING`). The same
  61 tests fail with exactly the same 18 names before and after this change; T54 must fix that
  module, not this ticket.
- `audit_retry` is not wrapped in the F23 harness-defect guard: an unexpected exception exits the
  command with its traceback and appends nothing (the registry is only written after the attempt).
- A retry blocked before the auditor runs (reachability, fresh state, confinement) consumes one of
  the three retries; the in-run loop's three before-work attempts are not replayed inside a retry.
- No model, no worker and no platform sandbox launch was performed, and no real runs root was
  touched.
