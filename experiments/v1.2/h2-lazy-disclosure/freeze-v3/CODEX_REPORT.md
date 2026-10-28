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

### Merge T51c+T51e

Merged T51e (violation wiring) into T51c's tree (`db64a46`): T51c's `audit_attempt()` call kept, T51e's evidence ported into it.
`confined()` no longer closes over `drive()`'s `attempt`: `launch_tools` takes an `evidence_dir` getter and writes `violations_file(evidence_dir(), stream.name)`, so `drive()` files under `attempt-<n>/` and `audit_retry()` under `audit-retry-<n>/` — each launch's log sits in the directory of the attempt it belongs to.
`audit_attempt()`'s `sandbox_record` carries `"violations": (audit.get("launch") or {}).get("violations")`; `violations_path()` keeps its shape (delegates to `violations_file()`), so the T51e path test and `IN_RUN_FIELDS` needed no change.
Checks: ruff clean on `freeze-v3` + `tests`; `auditretry`/`violations`/`driverfs`/`sandboxread` ran 10/13/6/3 tests, all OK; a throwaway stub run (not committed) produced `attempt-1/violations-worker.jsonl`, `attempt-1/violations-audit-attempt-1.jsonl` and `audit-retry-1/violations-stream.jsonl` (count 0, sha256 `e3b0c442…b855`), with the retry's `audit_sandbox.violations` pointing at its file.
No model ran, no real runs root was touched, nothing was re-pinned.
## T53 worker tool surface (opencode)

Path taken: **the config disables the tool**, so the `TOOL_ALLOW` fallback was not used. `execute`
stays out of `freeze-v3/access_audit.py`'s `TOOL_ALLOW`: the audit still treats a `code` program it
cannot resolve as `TOOL_NOT_ALLOWED` evidence, and the tool no longer reaches a launch.

The frozen profile now carries `"permission": {"execute": "deny"}` next to the existing
`question` deny, in the one template
(`freeze-v3/worker-profile/opencode.json`) that `sandbox_v2.fresh_home` copies into every fresh
home: `home-<n>` (worker), `audit-home-<n>` (per-run auditor) and `probe-home-<purpose>-<n>`
(reachability). Both arms of `run-plan-v3.json` name the same profile, so the two arms are
identical by construction, and a test asserts exactly that.

Evidence, all without a model call, opencode 2.0.25, THROWAWAY HOME under the shared review
directory (`$HOME`, `XDG_CONFIG_HOME=$HOME/.config`, `opencode service set port <free>` first so no
service setting of the operator is touched):

- `opencode --version` -> `opencode v2.0.25`.
- `opencode debug agents` -> `[]`. This build has no agent/tool listing surface, so the absence of
  a tool cannot be read from that command; it is recorded here as a measured negative.
- `opencode debug config` with the frozen template before this task -> `info.permissions` held only
  `{"action": "question", "resource": "*", "effect": "deny"}`.
- `opencode debug config` with the template after this task -> `info.permissions` holds
  `{"action": "execute", "resource": "*", "effect": "deny"}` and the same `question` rule, and the
  command exits 0 (no unknown-key diagnostic). The recorded output, home path sanitised to
  `<PROFILE_HOME>`, is committed as `freeze-v3/fixtures/preflight-debug-config-execute-deny.json`.
- The legacy form `"tools": {"execute": false}` normalises to the same rule; `permission` was
  chosen because the frozen template already uses that map for `question`.
- Why that rule removes the tool (local binary, 2.0.25): a config document's `info.permissions` are
  appended to every agent's rule list (`agent.transform`, after the built-in `{"action": "*",
  "resource": "*", "effect": "allow"}`); the tool snapshot drops a tool whose last matching rule is
  `effect: "deny"` with `resource: "*"`, and the Code Mode `execute` tool is only built when
  `execute` is not denied that way. This is the same mechanism the frozen `question` deny already
  relies on (protocol-v3.md, the `permission.question = "deny"` rationale).

The canary is the live instrument (still no model call in this task): `prepare` now requires one
more machine-readable line, `H2_CANARY_TOOLS <comma-separated tool names>`, and `check_stream`
fails closed with `NO_TOOLS_LINE` when it is missing or unparseable, `TOOLS_LINE_INCOMPLETE` when
`read` is not in it, and `EXECUTE_TOOL_PRESENT` when `execute` is listed or named as a `tool_use`.
The pre-T53 pass fixture (sources line only) now fails on the missing tools line and is kept as the
regression for that; the new synthetic pass fixture adds the tools line to the same live stream, so
`event_count` stays 10.

Pin failures caused ONLY by changed freeze-v3 files (expected until T54 re-pins; no pinned literal
was edited):

- `FreezeManifest.test_two_independent_anchors_and_materials_binding`
- `FreezeManifest.test_one_byte_mutation_of_every_frozen_file_is_rejected`

Both fail because `freeze-manifest.json` still pins the pre-T53 bytes of
`freeze-v3/isolation_canary.py` and `freeze-v3/worker-profile/opencode.json`.
`freeze-v3/build_manifest.py check` therefore reports exactly those two paths as mismatches; the
T53 gate set only requires `freeze-v2/build_manifest.py check`, which returns `PASS`.

Gates run in this worktree (PYTHONPATH unset, TMPDIR resolved with `pwd -P`):

- `python -m ruff check .` -> `All checks passed!`
- `python scripts/validate_governance.py` -> `35/35 checks passed`
- `python scripts/validate_public_release.py` -> `VIOLATIONS=0`
- `python experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_manifest.py check` -> `PASS`
- `python -m unittest discover -s experiments/v1.2/tests -p test_v1_2_h2_freeze_v3.py` ->
  `Ran 214 tests`, `FAILED (failures=2)`, both the pin tests named above. With an unresolved
  `TMPDIR` the same module also reports two `/var` vs `/private/var` path-equality failures that
  this task does not touch; resolving `TMPDIR` (as the freeze protocol does) removes them.

Not verified here: no live canary run was made (models are out of scope for T53), so the
`H2_CANARY_TOOLS` line has not yet been seen coming from a real session; that observation belongs
to the operator/T54 pilot. The auditor's own launch reads no bot/agent configuration different from
the worker's, but the auditor prompt itself was not changed by this task.
# T52 v3 access audit

Files changed: `freeze-v3/access_audit.py`, `experiments/v1.2/tests/test_v1_2_h2_freeze_v3.py`
(new class `AccessAuditV3Hardening` plus the existing access-audit cases whose "could have
succeeded" probe named a path that does not exist), and the new fixture
`freeze-v3/fixtures/access-audit-replay-v3.json`.

What changed, by plan item:

1. `allowed_roots` now carries the pinned interpreter's real install prefix (`sys.base_prefix`)
   and its stdlib directory, resolved from the interpreter that performed the audit; a foreign
   interpreter is asked for its own values (`-I -c`, no assumption), and an unaskable one adds no
   prefix. What is called "the interpreter" is the one the launch ran with: the replay reads it
   from the archived profile's interpreter subpath.
2. A READ of a path that does not exist (the run's post-launch snapshot first, the filesystem
   second) is `DENIED_BY_POLICY` evidence with `policy: PATH_DOES_NOT_EXIST`; a token carrying
   glob syntax is a pattern and is never existence-checked. A WRITE outside the profile's write
   whitelist is the same class. That required fixing `inside(path, "/")`, which returned False for
   every path, so `(deny file-write* (subpath "/"))` had never actually denied anything. An
   optional T51.4 violation log (path or parsed records) confirms a denial by resolved path or
   host (`policy: VIOLATION_LOG`); it never creates a hit and its absence proves nothing.
3. `network_hosts` strips `user:pass@` before extracting the host (`url_host`), so an allowlisted
   host behind credentials is a hit again and a denied one is still evidence.
4. Only a `read` result can be a breach: glob/grep/list listings and messages that mention a path
   are not.
5. The replay (`--replay <runs root>`, `replay()`) audits every archived
   `.driver/<run>/attempt-*/events.jsonl` (falling back to the run's own copy) and records per run
   the archived `access-audit.json` verdict (v2, read not recomputed), the v3 verdict of the last
   attempt, the reason in rule terms, and the earlier attempts. The summary carries no host path,
   home or command text.

Replay of the real archive (`/` + `Users/Shared/h2-runs`, read-only, 39 runs = the 20 counted
H2-R2 runs plus every pilot run): 34 VALID, 3 INVALID, 2 NO_STREAM (pilots that kept no event
stream). Of the five H2-R2 runs the round's audit called INVALID, v3 now calls `h2r2-f03-c`
(f03-c read the launch's own stdlib) and `h2r2-f03-v` (`verify --pack /nope`) VALID, and leaves
`h2r2-f04-v` and `h2r2-f05-c` (`execute`, T53) and `h2r2-f09-c` (`cd ..` into the shared runs
root, T51.2) INVALID. This is a harness measurement, not a re-scoring of H2-R2.

Not wired here, by the card's write scope: `run_h2r2.py` does not yet pass `snapshot=` or
`violations=` to `audit()` (T51/T54). Without them the audit still checks existence against the
filesystem, and the violation log is simply absent evidence.

## Expected pin-test failures at this commit (re-pinned in T54; pinned literals untouched)

- `test_v1_2_h2_freeze_v3.py::FreezeManifest::test_two_independent_anchors_and_materials_binding`
- `test_v1_2_h2_freeze_v3.py::FreezeManifest::test_one_byte_mutation_of_every_frozen_file_is_rejected`

Both fail only because `freeze-v3/access_audit.py` no longer matches its manifest hash. The new
fixture `fixtures/access-audit-replay-v3.json` is not a member of `build_manifest.FROZEN_FILES`
yet: T54 must add it to that list and rebuild the manifest, or the replay expectation stays
unpinned. The whole v3 module otherwise passes: `Ran 224 tests`, `FAILED (failures=2)`, and the
two failures are exactly the pins above.
