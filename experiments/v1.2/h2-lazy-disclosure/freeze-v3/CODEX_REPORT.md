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

### T54a — integration and re-pin

Built on `da2744c` (T50–T53 merged). One commit; no model, no worker and no run against a real
runs root was performed.

**(1) Audit inputs wired.** `freeze-v3/run_h2r2.py` now calls
`access_audit.audit(..., snapshot=evidence, violations=record["violations"]["path"])`: the
post-sweep snapshot directory and this launch's `violations-<launch>.jsonl`. The earlier
`confinement["violations"]` record is still handed over, but it is no longer the only path: the
two parameters `audit()` actually reads are populated. A read of an existing outside path that
the sandbox denied and the unified log recorded is therefore `DENIED_BY_POLICY`/`VIOLATION_LOG`
instead of `POSSIBLE_SUCCESS`. New stubbed driver test
`test_v1_2_h2_freeze_v3_violations.AuditInputWiring.test_snapshot_and_violations_reach_the_audit_it_reads`:
the audit spy receives the driver's own snapshot path and violations path, and with a profile
that proves nothing the violation record alone changes the class (PASS, one `DENIED_BY_POLICY`
attempt, `policy: VIOLATION_LOG`). No production defect was needed beyond the missing wiring.

**(2) Frozen test module against the merged design.** The first full run before any change was
`Ran 229 tests`, `FAILED (failures=10, errors=21)`; after the updates below it is
`Ran 229 tests ... OK`. Expectations changed, each only to the pre-registered design:

- Flat run dir `runs/<run_id>` → `wrapper_delivery.run_dir_for(...)` (T51b cell layout
  `.cells/<run_id>/<run_id>`), including fixture plants, cleanups and "no run dir was created"
  assertions. Where the driver root is asserted it is `runs/.driver/<run_id>`, not the cell
  parent's child (T51b).
- `test_the_deny_roots_are_the_frozen_templates_own_list` became
  `test_the_deny_surface_is_the_frozen_templates_deny_all_plus_allowlist`: parsed deny surface is
  `read: ["/"], write: ["/"]`, the rendered profile carries
  `(deny file-read-data (subpath "/"))` and no shared-root read deny (T51d/T51e).
- `test_the_template_denies_the_shared_roots...` became
  `test_the_template_denies_every_read_and_renders_only_the_allowlisted_surface`: it checks the
  equivalent allowlist property — an outside path under `Users` or the temp root is
  `DENIED_BY_POLICY` through `access_audit.path_class`, while the launch, its cell parent
  (literal only) and home are re-allowed (T51d/T51e).
- The end-to-end dynamic-read stub computed the driver root as `dirname(cwd)/.driver/<run_id>`;
  with a cell launch it must be the runs root three levels up (T51b). This was a test-fixture
  assumption, not a driver defect.
- The started-but-dead scheduler fixture now plants the run's cell (T51b), so the
  `INTERRUPTED` property is exercised on the production layout.
- Pins regenerated (below); no assertion was deleted and none was weakened.

The gate sandbox self-test (`GATE_SANDBOX_NOT_CONFINING`) no longer fails: it was a consequence
of the flat run-dir expectations aborting the driver tests before the real gate path ran, not a
separate defect. No production code change was required for it.

**(3) Re-pin, using the freeze-v3 build programs as in T50.** Materials = `da2744c` (parent of
this commit):

- `delivery_anchors.py . admission/freeze-v2-input/shortlist.json --materials da2744c --out
  delivery-anchors.json` → `DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0,
  "WRAPPER": 10}`; exit 0. Re-measured because `wrapper_delivery.py` changed in T51b and the
  anchors pin the measuring program by hash.
- `build_run_plan.py --materials da2744c --out run-plan-v3.json` →
  `RUN_PLAN_V3 runs=20 control_first=5 variant_first=5 fresh_episode=20`.
- `build_manifest.py build --freeze-parent da2744c --out freeze-manifest.json` →
  `FREEZE_MANIFEST files=63 delivery_payload_equivalent_to_T2=YES`.
- `FROZEN_FILES` gained the three evidence fixtures created after T50:
  `fixtures/access-audit-replay-v3.json` (T52 replay expectation),
  `fixtures/preflight-debug-config-execute-deny.json` and
  `fixtures/canary-86ac104-synthetic-sources-and-tools-line.jsonl` (T53). `EXPECTED_V3_HASHES`
  (63 entries) and `MANIFEST_SHA256` in the v3 test module were regenerated from the new
  manifest.

**Gate outputs** (`PYTHONPATH` unset, `TMPDIR=$(cd /tmp && pwd -P)`; run after the final edits):

- `python -m ruff check .` → `All checks passed!`
- `python scripts/validate_governance.py` → `35/35 checks passed`
- `python scripts/validate_public_release.py` → `VIOLATIONS=0`
- `freeze-v2/build_manifest.py check` → `{"verdict": "PASS", "mismatches": []}`
- `freeze-v3/build_manifest.py check` → `{"verdict": "PASS", "mismatches": []}`
- `git diff --exit-code 4aa2e7b -- experiments/v1.2/h2-lazy-disclosure/freeze-v2` → exit 0
  (`freeze-v2/` byte-identical)
- `python -m unittest discover -s experiments/v1.2/tests -p 'test_v1_2_h2_freeze_v3*.py'` →
  `Ran 262 tests in 650.654s`, `OK` (229 big module + 14 violations + 10 auditretry + 6
  driverfs + 3 sandboxread).
- `git diff --check` → exit 0.

**Not verified / limits:** no live worker, auditor, model or platform launch was run here; the
T53 `H2_CANARY_TOOLS` line still awaits the operator's pilot. The re-measured anchors reproduce
T50's neutral verdict (WRAPPER 10/10); the `CODEBUDDY`/`AGENTS` slots remain blocked by design.
No file outside `freeze-v3/` (plus the two v3 test modules) was modified.

### T55a

- F1 (P0): violation matching previously discarded operation and time, allowing a same-path
  write denial to hide a successful read. Matching now requires the same resolved path,
  `file-read-*` for read-classified accesses or `file-write-*` for write-classified accesses,
  a parseable timestamp inside the supplied launch window, and matching PID when both event
  and record carry one. Raw records, including PID and timestamp, remain in the audit output.
  Successful content results are not overridden by a log denial. Shell path tokens retain the
  existing conservative read classification; a write denial cannot confirm them.
- Deleted-before-end: filesystem absence is only provisional. A completed read or shell result
  containing output restores `POSSIBLE_SUCCESS` instead of treating end-of-launch absence as
  proof that no read occurred. An absent path with an error result remains denial evidence.
- Regression: `test_v1_2_h2_freeze_v3_auditfix.py` adapts the review probes with local synthetic
  files and records. On baseline `86930fd`, the successful read with write denial and the
  read-then-delete tests both failed (`PASS` instead of `INVALID`); both pass after the fix.
  Additional tests cover matching reads and writes, wrong operation, PID mismatch, missing or
  out-of-window timestamps, successful content and absent targets. The existing wiring test now
  checks that a path-only record is insufficient, while still checking the log is delivered.
- Limitations: the current driver does not supply `launch_window`, so its violation records do
  not confirm a denial in this integration; static classification remains in force. Supplying
  trusted bounds from the driver is outside T55a's owned files. The old large test module was not
  run; its pre-T55a test expecting a path-only or untimed record to confirm a denial needs to be
  reconciled by the integration owner. The v3 manifest was not re-pinned. No archive replay was
  attempted: the full source replay requires the forbidden H2-R2 archive. The committed T52
  fixture is unchanged; H2-R2/pilot streams carry no violation logs. This is not a claim that
  all source events were recomputed or that deleted-read outcomes cannot differ on replay.
### T55b

- F2: Copy-back followed worker-created destination links, and collection and blind-bundle reads followed snapshot links. The driver now replaces destination leaves with exclusive no-follow creation, and evidence readers use no-follow regular-file reads; artifact links are recorded with a hash of the link text and `EVIDENCE_UNREADABLE:<name>`, resulting in the existing `INVALID` collection verdict. Snapshot and artifact-hash roots reject symlinks. Audit input links are refused. The new linksafe tests derive from the review probes and exercise the driver, collector, bundle, receipt, events and root links.
- F4: The shared path resolver previously let an empty legacy directory choose the location of a new launch. New launches now select `.cells/<id>/<id>` directly; legacy resolution requires a registered run. The new driver regression creates an empty legacy directory and verifies the cell path.
- RED: On base `86930fd`, the linksafe collector, root and driver-link tests failed, and the separately run legacy-start regression failed. GREEN: the linksafe module passed after the fixes. The full long-running module, live runs, re-pinning and independent review were not performed in this task.
### T55c

- F3: `violations_v3.py` was executed by the driver but absent from `FROZEN_FILES`.
  Added it and a recursive AST import-closure test for the four runtime entry points, plus a
  synthetic transitive-helper check. The closure test failed at 86930fd with that file missing.
  Literal dynamic imports are covered; computed import names and imports outside freeze-v3 are
  not inferred by this test. The manifest JSON was intentionally not re-pinned.
- F5: confined acceptance gates bypassed the existing launch collector. Each gate now starts a
  process group, observes its PIDs and time window, and records the collected JSONL path, count
  and hash, or an error, in its gate record. The probe-derived test ran a real confined gate;
  at 86930fd it failed because the record had no violations. It also checks collector failure
  does not change a successful gate. PID polling is a lower bound and may miss short-lived or
  detached children. Timeout still raises as before; collection is attempted during cleanup,
  but a raised timeout does not return an acceptance gate record.
- F6: the Gate documentation incorrectly claimed no endpoint was allowed. Corrected it to the
  inherited loopback outbound/bind rule without changing the rule. The documentation regression
  failed at 86930fd. No live external network experiment was performed.

T55c checks (local, `PYTHONPATH` unset and `TMPDIR` resolved to `/tmp`'s physical path):
`ruff check .` passed; public-release scan `VIOLATIONS=0`; freeze-v2 manifest check `PASS`
with no mismatches; gateevidence unittest 4 tests OK; existing violations unittest 14 tests OK;
`git diff --check` passed. The 11-minute suite, live model runs, independent review, and v3
manifest re-pin were not performed.

### T55d — integration and re-pin

- F1: the worker uses the same trusted start and post-sweep end for both the unified-log
  collection and `access_audit.audit(..., launch_window=...)`. Both bounds are timezone-aware
  UTC ISO timestamps with subsecond precision; the audit accepts local-time log timestamps
  with numeric offsets. A stubbed driver test checks that a matching `file-read-data` denial
  inside the window gives `PASS` and `DENIED_BY_POLICY`/`VIOLATION_LOG`, whereas a record
  outside the window leaves `POSSIBLE_SUCCESS` and `INVALID`.
- F1/F4: updated the old violation-confirmation fixture to provide operation, time and window,
  and registered the legacy run in the cell-resolution fixture. F3: refreshed the independent
  literals for all 64 manifest members, including `violations_v3.py`.
- F2: a missing receipt was incorrectly reclassified as unreadable when no-follow reading was
  introduced. Restore `MISSING_RECEIPT` for `FileNotFoundError` while retaining no-follow
  behavior and the link-specific evidence checks. The original CLI assertion now passes.
- F5: the gate test now patches the collector actually referenced by its gate, preserving the
  same assertions when other test modules reload the collector module.
- Re-pin at materials/freeze parent `10cbf3c`: `delivery_anchors.py` returned neutral slots
  `CODEBUDDY=0, AGENTS=0, WRAPPER=10`; `build_run_plan.py` returned `runs=20 control_first=5
  variant_first=5 fresh_episode=20`; `build_manifest.py build` returned `files=64
  delivery_payload_equivalent_to_T2=YES`.

Gate evidence (the specified Python, `PYTHONPATH` unset and physical system `TMPDIR`):

- `python -m ruff check .`: `All checks passed!`.
- `python scripts/validate_governance.py`: `35/35 checks passed`.
- `python scripts/validate_public_release.py`: `MODE=PUBLIC`, `VIOLATIONS=0`.
- v2 and v3 `build_manifest.py check`: each `{"verdict": "PASS", "mismatches": []}`.
- `git diff --exit-code 4aa2e7b -- experiments/v1.2/h2-lazy-disclosure/freeze-v2`: exit 0;
  `git diff --check`: exit 0.
- A guarded foreground discovery of all eight v3 modules completed: `Ran 282 tests in
  781.234s`, `FAILED (failures=1, skipped=5)`. The sole failure was the F5 test's stale mock
  target after module reload. The 229-test main module had no failures; three of its tests
  were skipped. After correcting that mock target, a combined rerun of the other seven modules
  returned `Ran 53 tests in 20.015s`, `OK (skipped=2)`; the gate and driver wiring tests also
  passed together (`Ran 6 tests`, `OK`). The full 282-test discovery was not rerun after the
  test-only correction, so its final aggregate status remains unverified.
- The five skipped checks are the unavailable/forbidden archive replay, three prohibited driver
  subcommand CLI checks (including help-only calls), and the platform test containing real
  `opencode --version`. They are not passes. The test runner blocked those calls and archive
  access; it allowed local stubs. An initial full attempt also failed because its write guard
  mistook directory-relative no-follow opens for outside writes; that guard was corrected before
  the 282-test run above.

No live model, real opencode or real run was launched. Independent review and real CI for this
new candidate were not performed; the prior review applies to an earlier SHA.

### T55e

- An absent read target outside the launch, home and profile write allowances remains
  `PATH_DOES_NOT_EXIST` evidence even when a shell command returned text. For a writable
  target, completed content still restores `POSSIBLE_SUCCESS`; operation, launch-window and
  PID matching are unchanged. Profile subpath, literal and regex write allowances are checked.
- The new outside-root shell error-output test failed on the prior implementation (expected
  `PASS`, observed `INVALID`). The read-then-delete regression uses a profile granting the
  scratch root write access and remains `INVALID`.
- With `PYTHONPATH` unset and physical system `TMPDIR`: ruff returned `All checks passed!`;
  public release validation returned `VIOLATIONS=0`; freeze-v2 manifest check returned
  `PASS`. Auditfix, violations and AccessAuditV3Hardening together returned `Ran 40 tests`,
  `OK`, including the real archive replay. The committed replay fixture was unchanged.
- Rebuilt the run plan and manifest at parent `1ee80a6`: 20 runs and 64 manifest files;
  delivery payload equivalence was `YES`. Updated independent hashes for the auditor, run
  plan and manifest. Freeze-v3 manifest check returned `PASS`; `FreezeManifest` returned
  `Ran 2 tests`, `OK`. The first manifest-test attempt exposed the required run-plan hash
  update; it passed after that pin was corrected.
- Independent review and real CI were not performed in this implementation session.

### T56

- Refuse snapshot, artifact hash and collector worktree roots when any path component resolves
  through a symlink, retaining the existing refusal or unreadable semantics. The new tests use a
  parent link into an outside directory; the snapshot target is not created and the sentinel is
  unchanged. This is a path check, not a claim of race-free protection against concurrent swaps.
- Round the unified-log start down and its end up to whole seconds for every collector call;
  retain observed-PID filtering. The machine rejected a fractional-second `log show` argument
  with exit 64. A real short gate denial and a synthetic foreign-PID control cover the window.
- Bound the second gate `communicate` after a timeout, close inherited pipes on expiry and bound
  the parent wait. The detached child probe verifies return within 2.3 seconds for a 0.3-second
  timeout; the gate's separate log collection remains subject to its own timeout.
- On baseline `1fe5d67`, the ancestor-link, outward-rounding, detached-pipe and short-gate
  tests each failed; the empty collector-root ancestor-link test also failed. On the candidate
  all pass. With the specified Python, unset `PYTHONPATH`, and physical system `TMPDIR`:
  `ruff check .` passed; public-release validation reported `VIOLATIONS=0`; freeze-v2 manifest
  check reported `PASS`; the four requested test modules returned `Ran 36 tests`, `OK`.
- Re-pinned at `1fe5d67` after re-measuring delivery anchors and rebuilding the 20-run plan;
  freeze-v3 manifest and independent literal hashes are checked separately. No live model,
  real opencode, driver run/run-plan/audit, push, or independent review was performed.
- Final re-pin output: `DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0,
  "WRAPPER": 10}`; `RUN_PLAN_V3 runs=20 control_first=5 variant_first=5 fresh_episode=20`;
  `FREEZE_MANIFEST files=64 delivery_payload_equivalent_to_T2=YES`. Freeze-v3 manifest check
  returned `PASS` with no mismatches; `FreezeManifest` returned `Ran 2 tests`, `OK`.
