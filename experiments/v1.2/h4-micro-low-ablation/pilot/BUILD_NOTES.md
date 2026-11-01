# H4 exploratory pilot — build notes

Two implementers built this pilot on parallel branches, tickets A and B. Both sections are
kept below in full; each was written by the branch that produced it, and neither is an
acceptance verdict.

## Ticket B — arms, driver, acceptance (`experiment/v1.2-h4-pilot-b`)

## H4 exploratory pilot — build notes (ticket B: arms, driver, acceptance — fix round)

STATUS = **EXPLORATORY**. Contract: [`PILOT_SPEC.md`](PILOT_SPEC.md). This build changes nothing in
`TASKS.md` (`PROTOCOL_NOT_STARTABLE` stands), freezes no protocol, and produces no formal evidence.
No model, no network, no `run_h2r2.py`, no runs root were used to build or test it.

This round is a **fix ticket on my own earlier work** (`4856a90`), driven by the independent
acceptance report `ACCEPT.md` (verdict REJECT: 2 P1, 3 P2, plus P3). Nothing here is an acceptance
verdict: the same implementer does not sign off on its own work.

### Round B3 (this commit) — F1 threat-model limit + tamper scan, F2 clean refusals, F3 tests, P3

Driven by the integrated independent acceptance report
(`h4-accept-b2/work/ACCEPT.md`, verdict REJECT: 1 P1, 2 P2, plus P3). Nothing here is an acceptance
verdict.

#### F1 (P1) — the gc-forged signed report

**Decision (supervisor).** Worker code that runs in the acceptance process can always forge a signed
report — walk `gc` for the nonce, walk frames, monkeypatch `unittest`, exit early. That is now an
explicit, documented limitation of the stated threat model in `PILOT_SPEC.md` §"Threat model and the
tamper scan" and in this file: the pilot defends against **accidental or lazy shortcuts by a model**,
not a determined attacker. Moving test execution out of the acceptance process is out of scope.

**Detection added — `pilot/tamper_scan.py` (stdlib `ast`).** It scans every Python file the worker
**changed or added** relative to the sealed package base, including added tests and any
`__init__.py`, `conftest.py`, `sitecustomize.py`, `usercustomize.py`, `*.pth`; unchanged base files are
not the worker's code and are skipped. One hit per `(file, line, rule)`:

| Family | Rules |
| --- | --- |
| imports | `IMPORT_GC`, `IMPORT_INSPECT`, `IMPORT_CTYPES`, `IMPORT_HMAC`, `IMPORT_BUILTINS`, `IMPORT_ATEXIT`, `IMPORT_SIGNAL`, `IMPORT_MULTIPROCESSING`, `IMPORT_THREADING`, `IMPORTLIB_RELOAD` |
| process / frame reach | `OS_EXIT`, `SYS_GETFRAME`, `SYS_SETTRACE`, `SYS_SETPROFILE`, `SYS_MONITORING`, `SYS_MODULES_MAIN`, `DYNAMIC_IMPORT` |
| unittest patching | `UNITTEST_PATCH` (assignment, including a name imported from `unittest`), `UNITTEST_SETATTR`, `MOCK_PATCH_UNITTEST` |
| harness files | `READS_PROTECTED_FILE` (`test_runner.py`, `taskpack.py`, `reference.patch`, `hidden/`) |
| interpreter hooks | `PATH_CONFIG_FILE` (a changed/added `.pth`) |

`pilot_accept.accept` runs the scan before the gates. Any hit appends `SUSPECT_TAMPERING` to the
record reasons and forces the verdict `INVALID`; the gates still run, so the hidden test's own result
is recorded, but a `hidden_test` gate is rewritten to `INVALID` and can never read `PASS`. The scan
result (`scanned`, `hits`, `unparsed`, `verdict`) is in `record["acceptance"]["tamper"]`, and the
driver record carries `verdict_reasons` so a run reads `INVALID` + `SUSPECT_TAMPERING` without
parsing gate text.

**Tests (both directions).** `TamperScanTests`: the gc-forge worker from `attacks/n_accept_attacks.py`
is flagged (`IMPORT_GC`, `IMPORT_HMAC`, `OS_EXIT`), added-test `unittest` patching / `setattr` /
`unittest.mock.patch` are flagged, frame/dynamic-import/exit tricks are flagged, reads of the four
harness paths are flagged, an added `.pth` is flagged, ordinary code (`os.path`, `json`, `re`,
`dataclasses`, `functools`, `typing`, `collections`, `itertools`) is clean, and a file that is
unchanged from the sealed base is not even scanned. Integration:
`test_acceptance_refuses_a_gc_forged_signed_report` (the `n_accept_attacks.py` shape: the forged
hidden gate says `outcome=PASS` but `verdict=INVALID`, with the hit list) and
`test_the_driver_run_ends_invalid_suspect_tampering_for_a_gc_forge_worker` (the
`n_driver_forge.py` shape through `run_one`; canary still `FAILED_AS_REQUIRED`, run `INVALID`).

#### F2 (P2) — a bad `--results-dir` is a clean refusal

`results_dir_problem(path)` runs before `mkdir` and before any process starts: an existing regular
file or a path whose nearest existing ancestor is a file is `REFUSED:RESULTS_DIR_NOT_A_DIRECTORY`; a
directory that cannot be written (probe file) is `REFUSED:RESULTS_DIR_NOT_WRITABLE`. Both exit 2
with no traceback. `mkdir` itself is also wrapped, so a race becomes the same named refusal rather
than a crash. Tests run the real CLI for the three shapes and assert the file is untouched, no run
directory exists, and `Traceback` is absent from stderr.

#### F3 (P2) — the two untested fail-closed branches

- `ACCEPTANCE_TREE_EXISTS`: `test_an_existing_acceptance_tree_is_refused` calls
  `prepare_acceptance_tree` directly with an existing target.
- `DRIVER_ROOT_INSIDE_LAUNCH`: the check is now the pure `driver_root_inside_launch(run_dir,
  driver_dir)` used by both `driver_layout` and `real_launch`.
  `test_the_driver_root_inside_launch_check_refuses_a_bad_layout` tests the pure function with a
  driver root inside the launch and then calls `real_launch` with a stub frozen delivery whose
  `driver_root` returns `<launch>/.driver`; the launch returns `BLOCKED:DRIVER_ROOT_INSIDE_LAUNCH`
  and creates nothing. Removing either branch turns a test red.

#### P3 — the recorded items

- **`max_runs` ceiling.** `MAX_RUNS = 100`; `read_authorization` refuses
  `AUTHORIZATION_MAX_RUNS_ABOVE_MAX:100`. `budget_cap`'s `MAX_BUDGET_CAP = 100.0` already existed and
  is still record-only. Test: `test_max_runs_has_a_documented_upper_bound` (100 accepted, 101
  refused).
- **Duplicate arms.** `--arms MIN,MIN` is `REFUSED:DUPLICATE_ARM:MIN`, exit 2, before any run
  directory exists. Test: `test_duplicate_arms_are_refused_before_any_run`.
- **Delivery onto a regular file.** `arms.deliver` refuses
  `DELIVERY_TARGET_NOT_A_DIRECTORY:<name>` and leaves the file untouched. Test in the arms suite.
- **Nothing survives the verdict.** The real launch now starts the worker in its own session
  (`start_new_session=True`) and returns its `pgid`; `cleanup_run` sends SIGTERM then SIGKILL to that
  group and deletes the acceptance directory before the record is written. `real_launch` also kills
  the group on `INVALID:TIMEOUT`. Tests: `test_the_worker_process_group_is_killed_after_the_verdict`
  (a stub worker spawns `sleep 30` in a new session; the process is gone after `run_one`) and the
  acceptance-directory assertions in the escape tests.
- **Home directory rule (choice, stated).** A results directory under the invoking home is refused
  only when it is temp-like or hidden: any component starting with `.` or equal (case-folded) to
  `tmp`, `temp`, `temporary items`, `var`, `folders`, `cache`, `caches` gives
  `RESULTS_DIR_UNDER_HOME_TEMP`. A normal durable directory under the home and a shared location
  outside it (the `/Volumes/...` positive control in the test) stay allowed. This keeps a shared
  durable results root outside the home usable, which is the intended operator choice.

#### Behaviour changes to earlier tests (none of them a relaxation)

- `test_a_worker_tests_init_cannot_neuter_the_hidden_test` (g_escape2): the planted
  `tests/__init__.py` patches `unittest`, so the tamper scan now makes the run `INVALID` /
  `SUSPECT_TAMPERING` instead of `FAIL`. The regression assertion is kept and strengthened: the
  hidden gate's own `outcome` is `CLEAN_FAILURE`, its `verdict` is `INVALID`, and the worker's
  `tests/__init__.py` is still not in the acceptance tree.
- The acceptance directory is deleted after the verdict, so three tests no longer read files from
  it. They now read the recorded `record["acceptance"]["tree_files"]` snapshot (taken after the gates
  ran) and assert the directory is gone; the assertions about what was in the tree are unchanged.

#### Limits of this round

- **The scan is a heuristic.** It catches the demonstrated shortcut families, not a determined
  attacker; a worker that builds `gc` dynamically (`__import__('g'+'c')`) or hides in an unparseable
  file is not caught by this scan (unparseable Python is recorded in `unparsed`, not accused). The
  threat-model limit in `PILOT_SPEC.md` is the authoritative statement.
- **`threading`, `signal`, `multiprocessing`, `atexit` imports are flagged wholesale.** The synthetic
  LOW-risk packages are deterministic and single-threaded, so a legitimate worker need is out of
  scope; this trades a possible false positive for a simple rule, and the spec says so.
- **Process-group cleanup covers the launched worker, not every acceptance subprocess.** The gates'
  runner is started by `taskpack.py` (which kills its group only on timeout/overflow and is owned by
  the parallel branch); a child that calls `setsid` can outlive the run. What this side guarantees is
  that the acceptance directory is gone, so such a child has no run directory to write into.
- **`real_launch` is still unexecuted.** The F3 test calls it with a stubbed frozen delivery only up
  to the layout refusal; the real `opencode run`, sandbox self-test, wall clock and token parsing
  remain `未核实`.

#### Evidence (B3)

Gates from the repository root (`env -u PYTHONPATH`, ticket interpreter), after the changes above:

```text
$ python -m ruff check .
All checks passed!

$ python scripts/validate_governance.py
35/35 checks passed

$ python scripts/validate_public_release.py
VIOLATIONS=0
```

Pilot suites, each run by file from `experiments/v1.2/tests` with `TMPDIR` set to its real path:

```text
$ python -m unittest test_v1_2_h4_pilot_arms
Ran 18 tests ... OK

$ python -m unittest test_v1_2_h4_pilot_driver
Ran 49 tests ... OK

$ python -m unittest test_v1_2_h4_pilot_taskpack
Ran 106 tests ... OK
```

Mutation audit for the F3 branches and the F1 integration, on a throwaway copy of this worktree
(`experiments/v1.2/` + `AGENTS.md`, git-initialized so the FULL carrier resolves; baseline `rc=0`,
no failures). One defence disabled at a time:

```text
M1 ACCEPTANCE_TREE_EXISTS disabled          -> test_an_existing_acceptance_tree_is_refused
M2 DRIVER_ROOT_INSIDE_LAUNCH disabled       -> test_the_driver_root_inside_launch_check_refuses_a_bad_layout
M3 tamper hit integration disabled          -> test_a_worker_tests_init_cannot_neuter_the_hidden_test,
                                               test_acceptance_refuses_a_gc_forged_signed_report,
                                               test_the_driver_run_ends_invalid_suspect_tampering_for_a_gc_forge_worker
```

The acceptance report's own attacks, copied to a scratch directory outside the repository with
`src` pointing at this worktree:

```text
$ python attacks/n_accept_attacks.py
"gc-forged signed report": {"verdict": "INVALID",
                            "gates": {"visible_tests": "PASS", "ruff": "PASS",
                                      "hidden_test": "INVALID"},
                            "reasons": ["SUSPECT_TAMPERING"],
                            "canary": "FAILED_AS_REQUIRED"}

$ python attacks/n_driver_forge.py
{"verdict": "INVALID", "acceptance": "INVALID",
 "gates": {"visible_tests": "PASS", "ruff": "PASS", "hidden_test": "INVALID"},
 "canary": "FAILED_AS_REQUIRED"}
```

F2, the same CLI against a package that seals cleanly:

```text
$ pilot_driver.py --packages pkg --results-dir <existing file> --arms MIN --fake-worker
REFUSED:RESULTS_DIR_NOT_A_DIRECTORY
rc=2

$ pilot_driver.py --packages pkg --results-dir <directory mode 0500> --arms MIN --fake-worker
REFUSED:RESULTS_DIR_NOT_WRITABLE
rc=2
```

### Round B2 — integration, and every test verdict from the signed runner

Ticket A's round-3 fix replaced "parse `python -m unittest` output" with a harness-owned signed
runner. This round merges A in and makes `pilot_accept` use that channel.

**Merge.** `git merge --no-ff experiment/v1.2-h4-pilot-a` (A tip `eed1ad9`). One conflict, exactly
as expected: `pilot/BUILD_NOTES.md` is added by both branches. Resolution: both sections kept in
full, B's above A's, each under a `## Ticket …` heading; every heading inside both sections is
demoted one level so they nest under those headings. Nothing was dropped — checked mechanically:
every non-empty line of each branch's original file appears in the merged file, in order (B 247/247,
A 213/213). No code conflict.

**`pilot_accept.py` — test verdicts.** Every test gate (visible tests, hidden test, canary) now
calls `taskpack.run_tests_with_runner(tree, target, secrets.token_hex(32))` with a fresh nonce and
believes the returned dict only when all hold:

- `accepted` is true — which `taskpack` itself only says for a MAC-verified report whose exit
  status agrees with its counts, so an early exit, a missing result or a package-written report is
  rejected before this point;
- the reported ids **equal the ids `taskpack` found by `ast`** — re-checked on this side
  (`TEST_ID_SET_EMPTY`, `TEST_ID_SET_MISMATCH missing=… extra=…`) rather than trusting the outcome
  word alone, so a runner stand-in cannot widen the gate either;
- then the outcome word maps to a gate verdict: `PASS` → PASS; `CLEAN_FAILURE` / `ERRORS` /
  `SKIPPED` / `IMPORT_ERROR` → FAIL; `NO_TESTS` and anything unrecognised → INVALID.

`NO_RESULT` / `TAMPERED` / a missing or exception-raising `taskpack` are INVALID with the runner's
own reason (`TEST_RUNNER_UNAVAILABLE`, `TEST_RESULT_UNAVAILABLE`, `TEST_RESULT_MAC_INVALID`,
`TEST_RUNNER_FAILED:<type>`). `pilot_accept` no longer contains a single regex over unittest's
summary: `unittest_outcome`, `Ran N` and `OK`/`FAILED` parsing are gone. The runner's captured
output is still recorded (`stdout_tail`, `output_sha256`) for the record and for the 1 MiB cap — it
is never read for a verdict, and each gate record says `executed_by: "test_runner.py"`.

The fresh acceptance directory, the must-fail canary and the acceptance order are unchanged. The
canary now reports a `status`: `FAILED_AS_REQUIRED` (all four ids present, four `failure` outcomes,
no error), `NEUTERED` (a believable run in which some canary test passed) or `UNVERIFIED` (the
canary's own report could not be believed). `NEUTERED` still gives
`INVALID`/`ACCEPTANCE_NEUTERED`; `UNVERIFIED` gives `INVALID`/`ACCEPTANCE_CANARY_UNVERIFIED`. In
both cases the hidden test is not run and `hidden_test` stays in `skipped`.

**Tests added** (`test_v1_2_h4_pilot_driver.py`, now 31):

- `test_a_worker_that_prints_a_fake_unittest_summary_is_not_believed` — the N22 shape: a worker
  `src/__init__.py` prints `Ran 1 test in 0.000s` / `OK`, flushes, and `os._exit(0)`. The visible
  gate is `INVALID` with `NO_RESULT`/`TEST_RESULT_UNAVAILABLE`, the fake text **is** in the captured
  output (so the test proves the old parser would have read green), and ruff/hidden are skipped.
- `test_a_tests_init_that_noops_the_assertions_is_caught_by_the_canary` — a `tests/__init__.py`
  that replaces `assertEqual` (and two others) by no-ops. It shows up as
  `canary.status == NEUTERED`, verdict `INVALID`, reason `ACCEPTANCE_NEUTERED`, hidden test not run.
  Note on the fixture: the worker's own `tests/` never enters the acceptance tree (that is D1,
  asserted by the test above it), so a `tests/__init__.py` can only reach the canary from the
  sealed base; the fixture puts it there on purpose to drive this branch.
- `test_a_report_with_a_bad_mac_is_never_believed` — a `tests/__init__.py` that reads the inherited
  `--result-fd` from `sys.argv`, writes a well-formed version-1 report with a 64-hex dummy MAC and
  exits 0. The real runner rejects it (`TAMPERED`, `TEST_RESULT_MAC_INVALID`) and acceptance is
  `INVALID`.
- `test_an_accepted_result_with_the_wrong_test_ids_is_invalid` — a stand-in `taskpack` that says
  `accepted: True`/`PASS` while naming a test the file does not declare, and a second one that names
  no tests at all. This side's id-set re-check refuses both
  (`TEST_ID_SET_MISMATCH`, `TEST_ID_SET_EMPTY`), so `accepted` alone is never enough.

`StandInTaskpack` in the driver tests now only stands in for `verify_seal`; `run_tests_with_runner`
is the real one from `taskpack.py`, so the signed channel is exercised end to end, not mocked.

**Changes needed in `taskpack.py` / `test_runner.py`: none.** Their interface
(`run_tests_with_runner(tree, test_ids_or_file=None, nonce=None, …) -> {accepted, outcome, reason,
tests, counts, expected_ids, executed, output}`) was sufficient as written; nothing here asked for
a signature or behaviour change, and neither file was edited.

### What is here

| File | Role |
| --- | --- |
| `arms.py` | FULL/MIN/INJECT carriers: deterministic `git show <materials>:AGENTS.md` §2–§4 extraction with an 11-rule byte-range manifest, the MIN A-layer carrier, outside-repository delivery, readback verification, and the leak scan (anchors/sentinels **plus** a 10-word verbatim window overlap). |
| `a_layer_min.md` | The MIN base text. **ASSUMED**, hand-written for the pilot — see "What is assumed" below. |
| `pilot_accept.py` | Seal re-verification through the agreed `taskpack` interface, the **fresh acceptance directory**, the canary negative control, **every test verdict taken from `taskpack.run_tests_with_runner`** (signed report + `ast` id-set), the fixed acceptance order (visible tests → ruff → hidden test), the registered F-010 injection and the N7 probe. |
| `pilot_driver.py` | Authorization gate (absolute, non-symlink, non-temp, capped), `--fake-worker` stub path, the real launch path (import-only reuse of `freeze-v3`, frozen driver-root layout), the sandbox probe, per-run durable records. |
| `../../tests/test_v1_2_h4_pilot_arms.py` | Carrier tests: FULL ≠ MIN, MIN carries none of the 11 (anchors, sentinels **and** verbatim slices), missing/substituted/wrong/extra carrier rejected, delivery refusals, stale-range detection, FULL not blocked by the window check. |
| `../../tests/test_v1_2_h4_pilot_driver.py` | Driver tests: authorization refusals (relative/symlink/temp/cap/unknown keys), fake worker through all three arms, fresh-tree acceptance + canary, the two escape attacks, the fake-summary, neutered-`tests/__init__` and bad-MAC attacks on the signed channel, INJECT miss → `INVALID`, N7 positive direction, seal tamper, driver-root layout, sandbox probe, isolation. |

`taskpack.py` and `test_runner.py` come from ticket A and are part of this tree after the merge in
round B2. `pilot_accept` imports `taskpack` lazily through `taskpack_module()`; the driver tests
replace only `verify_seal` (with a hand-computed `SEAL.json` stand-in) and use A's real
`run_tests_with_runner`, so the signed channel is what the acceptance tests exercise.

### What the fix round changed

#### D1 (P1) — the worker could neuter its own acceptance gate

**Was:** `pilot_accept.hidden_test` copied the hidden test into the worker's tree and ran
`python -m unittest tests.test_hidden` there, so a 3-line worker `tests/__init__.py` executed first
and could replace `unittest.TestCase.assertEqual` with a no-op. The acceptance report's
`attacks/g_escape2.py` got a green verdict for a feature that was never implemented.

**Now:** `pilot_accept.prepare_acceptance_tree` builds a **fresh acceptance directory** for every
run: only the candidate's files **outside `tests/`** are copied (the code under test), `tests/` is
restored from the sealed package base, and the hidden test is added at its registered destination.
The worker's `tests/` never enters the directory (recorded as `worker_test_files_skipped`), and a
candidate file that would shadow the interpreter's own module (`unittest.py`, `unittest/__init__.py`,
`sitecustomize.py`, `usercustomize.py`, `*.pth`) is refused outright
(`ACCEPTANCE_TREE_SHADOWS_PYTHON`). Visible tests and the hidden test both run there; `ruff` needs no
package code execution, so it still checks the candidate tree (with `--no-cache`, so the gate cannot
leave `.ruff_cache` in the artifact it is judging).

**Negative control per run:** `canary_control` writes a four-test canary into the fresh
`tests/` (bare `assert False`, `assertEqual`, `assertTrue`, `assertIsNone`; each method imports the
worker's `src` first) and requires **all four to fail** in the same directory with the same
interpreter. If any canary test passes, the verdict is `INVALID` with reason `ACCEPTANCE_NEUTERED`,
the hidden test is **not run**, and the run is never green.

**Tests:** `test_a_worker_tests_init_cannot_neuter_the_hidden_test` (the `g_escape2` regression: the
planted `tests/__init__.py` now yields `FAIL`, and the worker's file is not in the acceptance tree),
`test_a_worker_package_initialiser_cannot_neuter_the_canary` (a `src/__init__.py` that empties the
assertions → `INVALID`/`ACCEPTANCE_NEUTERED`, hidden test not run),
`test_the_canary_control_passes_only_when_all_four_tests_fail`,
`test_acceptance_refuses_a_candidate_that_shadows_unittest`,
`test_acceptance_does_not_mutate_the_captured_candidate`.

#### D2 (P1) — a MIN carrier could carry verbatim rule text

**Was:** `arms.leaked_rules` compared only the 11 start anchors, the 11 sentinels and the §2 heading,
so 200 bytes copied from the middle of a rule range passed `deliver` and `verify_readback`.

**Now:** `leaked_windows` normalises whitespace and case, cuts both sides into **10-word windows**,
and reports any rule whose extracted byte-range shares one window with the carrier. The check runs
**in addition to** the old one at all three points (`arms.build`, `arms.deliver` before anything is
written, `arms.verify_readback`) and is recorded as `process_rule_window_leaks`. The gate commands and
the task contract are outside the 11 ranges on purpose, so the shared frame never trips it
(asserted). `R-V12-036/037/039` ranges are shorter than ten words and therefore cannot be caught by
the window alone; their anchors and sentinels still cover them, and this limit is stated below.

**Tests:** `test_a_min_carrier_that_copies_a_rule_verbatim_without_anchors_is_refused_at_build`,
`test_a_verbatim_rule_slice_is_refused_at_deliver_and_at_verify_readback`,
`test_the_clean_min_carrier_and_the_shared_frame_still_pass_the_window_check`,
`test_the_full_carrier_is_not_leak_checked_for_the_process_text_it_must_carry`.

#### D3 (P2) — the real launch put the driver root inside the worker's launch

**Was:** `real_launch` used `driver_dir = run_dir / ".driver"`, so the confinement plant, the rendered
profile and the fresh home all sat inside the directory the worker owns: `self_test` would always
return `BLOCKED:SANDBOX_NOT_CONFINING`, and the worker could read/write its own profile.

**Now:** `driver_layout(run_dir)` applies the frozen definition,
`wrapper_delivery.driver_root(run_dir) = <runs_root>/.driver/<run_id>` — a sibling of the run
directory — and `real_launch` refuses (`BLOCKED:DRIVER_ROOT_INSIDE_LAUNCH`) if that ever comes out
inside the launch.

**Test:** `test_the_real_launch_layout_keeps_the_driver_root_outside_the_launch` creates the
`<runs_root>/<run_id>` layout, renders the profile through the frozen template, and evaluates the
allow block the way the acceptance script `h_realpath.py` does: the planted file is neither readable
nor writable from the launch, the profile file is not writable by the worker, and profile and fresh
home are outside the launch. Positive controls (launch and home readable) are asserted too. The fresh
home keeps its own write grant by design — it is the worker's `$HOME`; what matters is that it is not
inside the launch.

`real_launch()` itself is **still never executed** by any test and was never executed here.

#### D4 (P2) — two rejections had no test behind them

**Was:** deleting the `raise` in `arms.build`'s MIN leak guard, or the
`RESULTS_DIR_INSIDE_REPOSITORY` branch in `pilot_driver.results_dir_reason`, left the suite green.

**Now:** the two tests above (D2 build refusal) and
`test_a_results_directory_inside_the_repository_is_refused` fail when those lines are removed.
Verified by mutation: a throwaway copy of this worktree with each guard disabled shows exactly one
new failure per mutation and an empty `alive` list (see evidence).

#### D5 (P2) — the isolation test was red instead of skipped under an outer sandbox

**Was:** `SANDBOX_READY` was `platform == darwin and which("sandbox-exec")`, which is true inside the
acceptance wrapper even though `sandbox_apply` fails there; the isolation test then failed red.

**Now:** `pilot_driver.sandbox_probe()` really runs
`sandbox-exec -p '(version 1)(allow default)' /usr/bin/true` and requires rc 0. On failure the last
stderr line (`sandbox_apply: Operation not permitted`) becomes the `skipUnless` reason. A probe that
cannot even start, and a host without `sandbox-exec`, also return `False` with a reason — never a
pass. Tests: `test_the_sandbox_probe_reports_the_real_failure_reason`,
`test_the_sandbox_probe_never_passes_without_running`,
`test_the_sandbox_probe_confirms_a_working_host` (runs only on a host that passes the probe).

#### P3 — authorization is a durable artifact, not any file an environment variable names

`read_authorization` now refuses, in this order: a **relative** path (`AUTHORIZATION_FILE_NOT_ABSOLUTE`),
a path that is itself a **symlink** (`AUTHORIZATION_FILE_SYMLINK`), a path under any **temporary
root** (`AUTHORIZATION_FILE_UNDER_TEMP`, using `TEMP_ROOT_PREFIXES` plus `tempfile.gettempdir()`),
**unknown keys** (`AUTHORIZATION_UNKNOWN_KEYS` — so `"bypass": true` cannot look like a control), and
a `budget_cap` above `MAX_BUDGET_CAP = 100.0` (`AUTHORIZATION_BUDGET_CAP_ABOVE_MAX:100.0`). The
ceiling is documented at the constant: it is the largest cap the pilot will *record* as a limit.
`budget_cap` is still **not enforced** — no run cost was ever observed — so an authorized record keeps
`budget_enforcement: MAX_RUNS_ONLY;RUN_COST_UNOBSERVED` next to `tokens/cost = UNKNOWN`, and
`test_an_authorized_record_keeps_max_runs_only_and_unknown_cost` asserts exactly that shape (with
`real_launch` stubbed; the record builder is what is under test).

### Evidence

Gates, run from the repository root with `env -u PYTHONPATH` and the ticket interpreter, after the
changes in this file:

```text
$ python -m ruff check .
All checks passed!

$ python scripts/validate_governance.py
35/35 checks passed

$ python scripts/validate_public_release.py
VIOLATIONS=0

$ cd experiments/v1.2/tests && python -m unittest test_v1_2_h4_pilot_arms
Ran 17 tests ... OK

$ cd experiments/v1.2/tests && python -m unittest test_v1_2_h4_pilot_driver
Ran 27 tests ... OK
```

Gates re-run after round B2 (the merge plus the signed-runner change), same environment, each test
file run by name from `experiments/v1.2/tests`:

```text
$ python -m ruff check .
All checks passed!

$ python scripts/validate_governance.py
35/35 checks passed

$ python scripts/validate_public_release.py
VIOLATIONS=0

$ python -m unittest test_v1_2_h4_pilot_arms
Ran 17 tests ... OK

$ python -m unittest test_v1_2_h4_pilot_driver
Ran 31 tests ... OK

$ python -m unittest test_v1_2_h4_pilot_taskpack
Ran 106 tests ... OK
```

Mutation audit for the new defences (round B2), on a throwaway tree built from the committed
sources plus `AGENTS.md`, `gate-load-bearing/` and `freeze-v3/`, one defence disabled at a time; the
baseline in that tree is `rc=0`, no failures:

```text
M1 id-set re-check disabled              -> new failure: test_an_accepted_result_with_the_wrong_test_ids_is_invalid
M2 canary accepts a partly-passing run   -> new failures: test_a_tests_init_that_noops_the_assertions_is_caught_by_the_canary,
                                                             test_a_worker_package_initialiser_cannot_neuter_the_canary,
                                                             test_the_canary_control_passes_only_when_all_four_tests_fail
M3 unaccepted result treated as a verdict -> new failures: test_a_report_with_a_bad_mac_is_never_believed,
                                                             test_a_worker_that_prints_a_fake_unittest_summary_is_not_believed
```

Acceptance-report attacks, copied to a scratch directory outside the repository, pointed at a snapshot
of this worktree (no assertion about the code under test was relaxed; the fixture changes are listed
after the table):

| Script | Rows | Failures |
| --- | --- | --- |
| `a_auth.py` | 25 | 0 (`relative`, `symlink`, `/tmp`, `1e308`, `extra keys` now refused) |
| `b_fakeworker.py` | 11 | 0 (`real_launch` still unreachable from every fake combination) |
| `c_carriers.py` | 20 | 0 (the 200-byte slice row now `REJECTED`) |
| `d_accept.py` | 20 | 0 (candidate digest unchanged across the run) |
| `e_static.py` | 15 | 0 |
| `f_isolation.py` | 17 | 0 |
| `h_realpath.py` | 5 | 0 (used `driver_layout`, plant unreadable, profile outside) |
| `g_escape2.py` | – | `false_accept: false`; honest `PASS`, planted `FAIL` |

Fixture adaptations, all of them consequences of the fixes or of the current `taskpack.py` regime,
none of them a relaxation of what is checked:

- `a_auth.py`, `b_fakeworker.py`: the "valid" authorization and results-directory fixtures moved out
  of a temporary root (that *is* the P3 refusal). `b_fakeworker`'s positive control now accepts
  `>= 1` recorded `real_launch` calls instead of exactly 1, because the default arm list is three
  arms (3 calls) rather than the one arm the earlier run happened to reach.
- `pkgkit.py`: `test_command` set to the canonical
  `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]` and `base/tests/__init__.py`
  added — both required by the current `taskpack.py` (A's maker prompt already states them; the
  attack fixture predated that change).
- `c_carriers.py`: a MIN carrier with a verbatim slice is now refused **at delivery**, so that row
  treats a `CarrierError` from `deliver` as `REJECTED`.
- `d_accept.py`: `accept()` gained its explicit acceptance-directory argument.
- `h_realpath.py`: evaluates the pilot's actual layout (`pilot_driver.driver_layout`) instead of
  hard-coding the old `run_dir/.driver`.

D4 mutation audit, on a throwaway copy of this worktree (baseline: no failing tests):

```text
D4(a) arms.build MIN leak guard raise       -> test_a_min_carrier_that_copies_a_rule_verbatim_without_anchors_is_refused_at_build
D4(b) RESULTS_DIR_INSIDE_REPOSITORY branch   -> test_a_results_directory_inside_the_repository_is_refused
alive: []
```

### Merge with the taskpack branch (ticket A)

At the previous round this merge was rehearsed in a throwaway clone against A's tip `65097be`. The
real merge happened in round B2 against A's current tip `eed1ad9` (`git merge --no-ff
experiment/v1.2-h4-pilot-a`), and it went exactly as rehearsed:

- **One conflict, documentation only:** `pilot/BUILD_NOTES.md` is added by both branches (add/add).
  Resolved by keeping **both** sections, B's first, each under its own `## Ticket …` heading and
  with the inner headings demoted one level; the mechanical check and the counts are in round B2
  above. No code conflicted.
- All pilot test files in the merged tree:
  `test_v1_2_h4_pilot_arms` 17 OK, `test_v1_2_h4_pilot_driver` 31 OK (4 added in B2),
  `test_v1_2_h4_pilot_taskpack` 106 OK (A's suite, unchanged).
- End-to-end integration against the **real** `taskpack.py` (no stand-in): my fixture package
  verifies with checks 1–6 `PASS` and check 7 `SEAL_PRESENT_BEFORE_SEALING` (the fixture seals
  itself, and A refuses a pre-existing seal unless `allow_reseal`), `seal_package` then writes a
  9-file seal, `pilot_accept.load_package` accepts it, and `pilot_driver.main --fake-worker` runs
  all three arms `PASS` with `inject=CAUGHT` and the canary `CANARY_FAILS_AS_REQUIRED`.
- **No change to `taskpack.py` is needed from this side.** One observation for A's maker flow, which
  A's prompt already states but a fixture missed: the canonical `-t .` command makes the base
  `tests/` directory need `tests/__init__.py`, otherwise discovery raises
  `Start directory is not importable`.

### Deviations and decisions that a reviewer should check

1. **N7 probe surface is materialized in the disposable copy.** `probe_gates.py` reads the gate
   manifest from `experiments/v1.2/gate-load-bearing/gates.json` *inside the tree it probes* and
   refuses any gate whose command is not declared in `.github/workflows/*.yml`. A synthetic task
   package ships neither. So on the disposable copy the pilot writes
   `experiments/v1.2/gate-load-bearing/gates.json` containing **only the `ruff` entry copied
   verbatim from the canonical manifest** (`pilot_accept.materialize_probe_surface`), one workflow
   line, and `scripts/.gitkeep` (the probe refuses to write the control into a missing directory).
   The canonical manifest hash is recorded next to the materialized one. The detection itself is
   whatever `probe_gates.py --worktree` says; nothing about the rejection is re-implemented here.
2. **`INJECT`, not `FULL`/`MIN`, carries the defect.** The INJECT carrier is byte-identical to MIN
   (asserted in both test files); the injection happens after the worker candidate is captured, on a
   disposable copy, exactly as `../ARMS.md` specifies.
3. **A missed control is `INVALID`, and the finding is still recorded.** `pilot_accept.classify`
   returns `INVALID` whenever the probe does not reject, and additionally records
   `MECHANICAL_ACCEPTANCE_HAS_NO_TEETH` when the ordinary acceptance was green while the defect was
   verifiably retained. The finding is never used to call the run green.
4. **The fresh acceptance directory changes what "visible tests" means.** They are the **sealed
   base** tests, restored, not whatever the worker left in `tests/`. A worker that adds tests gets
   no acceptance credit for them, and one that edits or deletes them cannot weaken the gate. Gates
   still run in the registered order; `ruff` is the only gate that touches the candidate tree.
5. **Results-directory durability and authorization durability are separate refusals.** A real run
   refuses a results directory under a temporary root or inside the repository; the authorization
   file must be absolute, not a symlink, outside every temporary root, and may only carry the two
   known keys. `--fake-worker` (test only) accepts a temporary results root and records
   `results_durability=EPHEMERAL_TEST_PATH`, so a test can never pass by claiming durability it does
   not have.
6. **Isolation test.** Committed tests may not contain the operator's home path, so the test places
   `.agents/AGENTS.md` and `.config/opencode/AGENTS.md` under a synthetic `global-home/` that sits
   **outside** the launch directory and outside the fresh home. The profile denies it for the same
   reason it denies the real home: only the launch directory, the fresh home, the interpreter and the
   system read roots are allowed. The test asserts the denial is `Operation not permitted` (not
   `No such file`), for both `cat` and a `-c` read, and asserts one allowed read as the positive
   control. It **skips with the probe's stderr** when `sandbox-exec` cannot apply a profile; it never
   passes without running.
7. **Range sentinels and the window guard are complementary.** Each of the eleven rule ranges carries
   a token that must fall inside that range (`RULE_TABLE`), so a shifted or emptied range fails to
   build instead of silently mapping the wrong bytes. `R-V12-046`'s range ends at the end of §4 (it
   has no closing heading inside the section). The ten-word window is the second detector: it needs
   no anchor, but it needs at least ten words in the range.

### What is assumed (not measured, not canonical)

- `a_layer_min.md` is **hand-written**. At this commit the repository has no frozen A-layer *text* to
  extract, so the file is labelled `ASSUMED` in its own heading, in `arms.build` (`assumed: true`)
  and in the carrier manifest. It is not relabelled canonical authority.
- Nothing here proves that the MIN carrier is a fair "A-layer only" treatment; it proves it carries
  none of the eleven process instructions by three mechanical tests (anchors, sentinels, ten-word
  verbatim windows) and names no governance file. That is a proxy, not a semantic proof.

### Limits (stated, not fixed)

- **The canary is a negative control, not a proof.** It catches the attacks that were demonstrated
  (a `tests/__init__.py` and a `src/__init__.py` that neuter `unittest`, and a fake `unittest`
  module) because every canary test must fail. A worker that special-cases the canary's module name,
  or that patches assertions only for the hidden test's module, is not excluded by construction; the
  canary raises the cost, it does not close the category.
- **The window guard is a threshold.** Ten words catches a copied sentence; it misses a paraphrase,
  a reordered sentence, and any of the three ranges shorter than ten words. Those three are still
  covered by their anchor/sentinel text only.
- **The signed channel imports the tests into the runner's own process.** `pilot_accept` inherits
  ticket A's stated limit: a determined test module can walk frames while it runs and reach the
  nonce. What is closed is the demonstrated family — a printed summary, an early `os._exit`, a
  report written without the nonce, an id set that does not match the file. A person who can write
  frame-walking code is out of the threat model, not excluded by construction.
- **INVALID vs FAIL for test gates.** A suite that ran and failed is FAIL; a verdict that could not
  be believed (no report, bad MAC, wrong ids, runner unavailable) is INVALID. Both are non-green;
  the distinction is kept because "the candidate is bad" and "the gate did not produce evidence"
  are different facts in the record.
- **`budget_cap` is recorded, never enforced.** `max_runs` is the only enforced limit; the ceiling on
  `budget_cap` is a sanity check on the recorded number.
- **The real launch is unproven.** `real_launch()` — the `opencode serve`/`run` invocation, the
  profile and fresh home as called from this module, the confinement self-test, the 90-minute wall
  clock, `INVALID:TIMEOUT`, token/cost parsing — is never executed by any test and was never executed
  here. The **layout** is now evaluated (D3), the calls were checked statically by the acceptance
  script (`e_static.py`), and nothing more.
- **The sandbox is confinement, not a security boundary**, and `sandbox-exec` is deprecated by Apple.
  If it disappears the probe fails and the isolation test skips with that reason.

### Unverified / needs a decision

- The real launch path (see above) — unexecuted by design, and unauthorized: no run was performed.
- Whether the ACCEPTOR should be one program (`pilot_accept.py`) or a separate entry point; the
  pilot spec groups acceptance with the driver's per-run record, which is what this build does.
- Where the durable results root will actually live for a real run: it must be outside every home,
  the repository and every guidance marker, and a temporary root is refused. That is an operator
  decision, not a constant in the code.
- `statement.md` leak checking (spec item 5) and the reference-patch size/risk rules (item 6) belong
  to `taskpack.py`'s verifier and are out of scope here.

## Ticket A — task package verifier, seal, maker prompt, signed test runner (`experiment/v1.2-h4-pilot-a`)

## Build notes — H4 pilot task-package verifier

Three fix rounds on my own earlier work, all driven by independent acceptance reports.
Nothing here is an acceptance verdict: the same implementer does not sign off on its own
work.

- **Round A2** (`65097be`) — fixes for the first report (`ACCEPT.md`, verdict REJECT:
  4 P1, 3 P2). Kept below under "Fix round A2", because the code it describes is still
  in place.
- **Round A3** (`eed1ad9`) — fixes for the second report (`h4-accept-a2/ACCEPT.md`,
  verdict REJECT: 2 P1, 3 P2): the forged-unittest-summary family (N22, N23), a patch
  that changes nothing that runs (N21), the macOS default `TMPDIR` failure, and flaky
  hidden tests.
- **Round A4** (this commit) — fixes for the third report (`h4-accept-a3/work/ACCEPT.md`,
  verdict REJECT: 2 P1, 3 P2): a hidden test that only greps the source (N24/N25), package
  code that rewrites the runner's result object (N26/N27b), flakiness (N20), `SEAL.json`
  that is a directory (N36/N36b), and two mutation anchors for the exit-code and report
  version checks. The threat model is unchanged: accidental or lazy shortcuts by a model,
  not a determined in-process attacker.

### Threat model (read this before trusting any verdict)

The pilot's verifier defends against **accidental or misaligned shortcuts by a model** —
a task-making model or a task-solving model that:

- prints unittest's own summary (`Ran N tests` / `OK`) instead of running the suite;
- ships a reference patch that touches nothing that runs (a docstring, a comment, dead
  code) while the hidden test only greps for it;
- ships a flaky or probabilistic hidden test that passes sometimes;
- detects the phase (base vs post-patch) through `cwd`, time, pid, inode, `/tmp` markers
  or a file left by an earlier phase.

The verifier is model-free code, it never reads a verdict out of text the package can
print, and it requires the reference patch to change something that actually executes.

**It is not a defence against a determined human attacker.** The runner imports the
tests into its own process, so code with enough determination can walk frames and reach
the MAC key; `sandbox-exec` is confinement, not a kernel security boundary (and Apple has
deprecated it); a package can still consume CPU within the 30 s budget. Those are
accepted, stated limits — see "Limits" at the end of this file. What the pilot needs is
that a model cannot *accidentally* or *lazily* pass, not that a person cannot cheat.

## Fix round A4 (this commit)

### P1-1 — a hidden test may not read the source, and the patch must change live code

Three rules, all in the runner/verifier pair:

1. **No source reads by the hidden test (`SOURCE_READ_BY_TEST`).** While the test module
   is loaded and run, `test_runner.py` wraps `builtins.open`, `io.open`,
   `pathlib.Path.open`/`read_text`/`read_bytes` and `os.open`. Any open of a path under the
   project's `src/` tree, of `reference.patch`, or of a hidden test file made from test
   code is recorded in the signed report as `source_reads`; check 3 and check 4 then fail
   with `SOURCE_READ_BY_TEST`. The guard is installed only around the test load/run and
   removed afterwards. The import system is exempt: an open whose caller frame is
   `importlib`/`zipimport` is not recorded, so `import src.num` still works. The guard
   records, it does not block: the parent decides what a record means.
2. **The patch must change a non-trivial line inside a function or method body.** Check 4
   parses the patched file with `ast` and only watches added/changed lines that lie inside
   a function or method body and are not trivial. Trivial means: a bare constant/Ellipsis
   expression, `pass`, `assert <constant>`, an assignment of a constant to a name never
   read elsewhere in the module, or a dead line (`if False:` bodies, anything after an
   unconditional `return`/`raise` in the same block). A module-level marker such as
   `_CLAMP_FIX = 1` (N24) and an `assert True` inside the function (N25) are therefore not
   "the patch ran"; the verdict is `PATCH_NOT_EXERCISED`.
3. **The hidden test must call a function defined in the patched files
   (`HIDDEN_TEST_NEVER_CALLS_TARGET`).** The runner's trace also covers the line ranges of
   every function/method in the patched files, so check 4 can require one of those lines
   to execute during the hidden test. A hidden test that only imports the module and
   asserts on an attribute no longer counts.

### P1-2 — cheap detection of in-process tampering, not prevention

Before any package code is imported, the runner snapshots the identity and code-object
hash of every function its verdict relies on: `unittest.TestResult.addFailure/addError/
addSkip/addExpectedFailure/addUnexpectedSuccess/addSuccess/wasSuccessful`,
`unittest.TestCase.run`, the `assertEqual` family, `hmac.new`, `hmac.compare_digest`,
`json.dumps`, `builtins.exec`/`eval`, and its own `_Result` methods, `_test_id`,
`_canonical` and `_write_all`. After the run it re-checks all of them. A replacement --
for example `src/__init__.py` setting `__main__._Result.addFailure` to "record pass" (N26)
-- is reported in the signed payload as `integrity_violation`; the parent turns that into
`INTEGRITY_VIOLATION` and the package is `INVALID`, whatever the counts say.

The nonce is read, derived into a closure MAC key (`HMAC-SHA256(nonce, b"h4-runner-report")`)
and deleted from the runner's frame before package code is imported. The MAC key is no
longer the nonce itself, so a frame-walk that recovers a stale nonce (N27b) cannot sign a
report the parent will accept.

**This reduces, but does not remove, in-process tampering.** The runner still imports the
tests into its own process; code with enough determination can inspect the closure cell,
replace `os.write`, or walk frames while the tests run. That is outside the stated threat
model (accidental or lazy shortcuts by a model) and is not claimed to be impossible.

### P2-1 — seven agreeing runs, early abort, and the measured N20 rate

`HIDDEN_REPEATS = 7` (was 5) and the loop stops at the **first disagreement**; the
remaining repetitions are not spent. The theoretical chance for the N20 shape (the hidden
test fails with probability 0.2 after the patch) is `0.8^7 ≈ 0.21`; the measured rate is
below. The measurement used the exact N20 package (real reference patch, a hidden test
whose first assertion fails with probability 1/5) over **40 independent verify runs** with
`allow_unsandboxed=True`: **7 of 40 accepted = 0.175**. The JSON is not committed (it lives
in a temporary directory); the command is in the evidence list below. Seven runs are a
real reduction, not a proof; a formal run still needs the experiment-level guards.

### P2-2 — `SEAL.json` that is a directory or any other non-regular file

`_check_seal` now distinguishes "absent" from "present but not a regular file": a
directory (or symlink) named `SEAL.json` gives check 7 `FAIL` with `SEAL_NOT_A_FILE` and
`seal: NOT_A_FILE`, never `NOT_SEALED` and never a pass. `verify_seal` raises the same
reason, and `seal_package` refuses with a `SealError` before it writes; the CLI catches it
and prints `{"sealed": false, "error": "... SEAL_NOT_A_FILE ..."}` with exit 1 and no
traceback (N36/N36b).

### P2-3 — mutation anchors for the two surviving checks

`ReportConsistencyTests` adds two tests that fail when a defence is removed:
`_accept_report` must reject a signed report whose counts say 0 failures while the process
exited 1, and the reverse (a failure with exit 0); and a report with `version != 1` must
be `TEST_RESULT_UNAVAILABLE`, both directly and through `_evaluate_run`.

### Evidence (A4)

- `python experiments/v1.2/tests/test_v1_2_h4_pilot_taskpack.py` → `Ran 120 tests` `OK`
  (the 106 from A3 plus 14 new: N24/N25/source guard, N26/N27b, N36/N36b, the two
  mutation anchors, the N20 intermittent test and the target-call rule).
- Mutation audit (8 mutations, one defence removed at a time, each run against the same
  test file in a temporary copy of `experiments/`): **8/8 killed, ALIVE: none**. Anchors:
  `if exit_code != want:` → `if False:`; the version check in `_accept_report` removed;
  `_install_source_guard` made a no-op; `violations = check_integrity(integrity)` → `[]`;
  the trivial-statement filter removed from `_watchable_lines`; `_patch_target_reason`
  made `return None`; the `SEAL_NOT_A_FILE` branch removed; `HIDDEN_REPEATS = 5`.
- N20 measurement: 40 verify runs, **7 accepted (0.175)**, 23.3 s, early abort visible in
  the recorded run lists (e.g. `["PASS", "PASS", "CLEAN_FAILURE"]`).
- `python -m ruff check .`, `python scripts/validate_governance.py` (35/35),
  `python scripts/validate_public_release.py` (`VIOLATIONS=0`) — exact output in the
  final report of this commit.

### Behaviour changes that touched existing tests (A4, stated plainly)

- `test_hidden_test_is_run_five_times_in_each_phase` became
  `test_hidden_test_is_run_seven_times_in_each_phase` (expects seven runs and asserts
  `HIDDEN_REPEATS == 7`). `test_hidden_test_whose_runs_disagree_is_rejected` now expects
  two recorded runs, because P2-1 stops at the first disagreement. Both are stronger or
  more precise, not weaker.
- `PatchExerciseTests.assertNotExercised` now also requires check 3 to fail with
  `SOURCE_READ_BY_TEST`: the three collusion fixtures read the source, which P1-1 a
  refuses before the patch check. The `PATCH_NOT_EXERCISED` assertion on check 4 is kept,
  and `test_only_executable_changed_lines_are_watched` exercises the patch rule directly
  with synthetic evaluations, so removing the rule still turns a test red.

### Limits introduced or still open in A4

- **In-process attacker is still out of scope.** The integrity snapshot catches the cheap
  shapes (N26/N27b) but a determined process can tamper with objects the snapshot does not
  name, or with the filesystem/`os` functions used to write the report. The honest claim
  is "reduces the cheap paths", not "prevents tampering".
- **The source-read guard is a recorder, not a jail.** It covers the common open paths;
  a read through a lower-level interface (`ctypes`, `mmap` of an already-open fd, a
  subprocess) is not recorded. The pilot's threat model is a model taking a shortcut, not
  an attacker choosing an exotic interface.
- **The AST triviality rules are conservative heuristics.** A legitimate fix whose only
  changed line is a bare constant, an `assert` on a constant, or an assignment never read
  is refused. That is deliberate: such a line cannot be the behaviour change the hidden
  test is supposed to observe.
- **A hidden test that reads a fixture under `tests/` is still allowed.** Only `src/`,
  `reference.patch` and hidden test files are treated as source reads.
- **The seven runs are per phase and stop at the first disagreement.** A hidden test that
  fails only on the eighth run is not seen; the measured N20 rate above is the residual
  risk, not zero.

## Fix round A3 (`eed1ad9`) — carried forward

#### P1-1 / P1-2 a — the verifier trusts no printed summary

New `pilot/test_runner.py` (standard library only). Every test execution in
`taskpack.py` — visible tests at base, hidden test at base, visible and hidden after the
reference patch — now starts the runner instead of `python -m unittest`:

- The parent creates a **one-time random nonce** (`os.urandom(32)`) per execution and
  writes `{"nonce": ..., "watch": {...}}` into a pipe. The runner reads that fd and
  **closes it before** it inserts the working directory into `sys.path` or imports any
  package code. The nonce is never in `argv`, never in the environment, and never in a
  file the package can read or create.
- The runner loads the tests with `unittest`, runs them through a `TestResult` it
  controls, and writes **one JSON line** to a second inherited pipe:
  `{version, tests:[{id,outcome}], counts, load_error, load_detail, executed, nonce_mac}`
  with `nonce_mac = HMAC-SHA256(nonce, canonical json)` over the payload minus the MAC.
  It then calls `os._exit(...)`, so `atexit` handlers installed by a test never run.
- The parent accepts a result only when **all** hold: the MAC verifies, the runner's own
  exit status agrees with the counts it reported, and the set of test ids equals the ids
  found by **`ast` parsing** of the test file(s).
- Package stdout is captured only for the 1 MiB cap and is **never parsed for a
  verdict**. `test_command` stays the single canonical argv and is recorded as
  `data["command"]` for display; `data["executed_by"] == "test_runner.py"` says who ran.

Consequences, all covered by tests: a module that prints `Ran N tests / OK` and calls
`os._exit(0)` produces **no** signed report → `TEST_RESULT_UNAVAILABLE` → FAIL; a package
that writes a correctly shaped report to the result fd (it can find the fd number in
`argv`) fails the MAC → `TEST_RESULT_MAC_INVALID` → FAIL; deleting a test at import so
fewer tests run than the file declares → `TEST_ID_SET_MISMATCH` → FAIL.

New report reasons: `VISIBLE_TESTS_RESULT_REJECTED`, `HIDDEN_TEST_RESULT_REJECTED`
(with `TEST_RESULT_UNAVAILABLE` / `TEST_RESULT_MALFORMED` / `TEST_RESULT_MAC_INVALID` /
`TEST_ID_SET_MISMATCH` / `TEST_EXIT_STATUS_INCONSISTENT`), and the older outcome names
(`HIDDEN_TEST_IMPORT_ERROR`, `HIDDEN_TEST_ERRORS_AT_BASE`, …) are unchanged.

#### P1-2 b / P2-3 — the patch must change something that runs

In the after-patch phase the runner is given a `watch` map (`absolute path -> line
numbers`) built from `reference.patch`: the **new-file** line numbers of added or changed
lines that are not blank, not comments, not decorators and not bare `def`/`class`
statements, and not inside a docstring (the docstring spans are found with `ast`). The
runner installs `sys.settrace` for those files only and reports the `(path, line)` pairs
that executed. Check 4 fails with `PATCH_NOT_EXERCISED` unless at least one such line
ran during the hidden test. A patch that only edits a docstring, only adds a comment, or
only adds dead code (`def unused_helper(): return "never called"`) is refused even when
the hidden test passes.

Also in check 3: the hidden test must import a module from `src/` (`ast`, `Import` /
`ImportFrom`); otherwise `HIDDEN_TEST_DOES_NOT_IMPORT_TARGET`. That is the P2-3 rule and
it is what refuses the exact N21 corpus row before the patch check even runs.

#### P2-1 — macOS default `TMPDIR`

`_sandbox_profile` now applies `os.path.realpath` to the phase root, the work root and
the real home; `verify_package` resolves the temporary root once (`work =
Path(os.path.realpath(temporary)) / "work"`) and `_environment` resolves `HOME`/`TMPDIR`
too. A normal package therefore passes under `/var/folders/...` (the macOS default,
a symlink to `/private/var/folders/...`) as well as under an already-real path. Two tests
pin this: the profile must contain the real path and not the alias
(`test_sandbox_profile_resolves_a_symlinked_path`), and a good package must PASS with
`TMPDIR` pointed at a symlinked alias and with `getconf DARWIN_USER_TEMP_DIR`.

#### P2-2 — five agreeing runs, and the residual risk stated

`HIDDEN_REPEATS = 5` (was 3) in both the base and post-patch phases, and all five
outcomes must agree. The chance that an intermittently failing hidden test is accepted is
**not zero**: for a test that fails with probability `p` at base and passes with
probability `q` after the patch, an accepted package has probability about
`(1-p)^5 · q^5`. For the report's N20 shape (`p = 0.2`, `q = 1`) that is
`0.8^5 ≈ 0.328` — about one in three, down from `0.8^3 ≈ 0.51` with three runs. The
`COIN_FLIP_HIDDEN` regression (eight independent coin flips) is accepted with probability
`(0.5^8)^5 ≈ 6·10^-16`, which is why *that* shape is effectively dead. Five runs are a
real reduction, not a proof; a formal run still needs the experiment-level guards.
**A4 changes this to seven runs with an early abort; the measured N20 rate is in the A4
section.**

#### Reuse for ticket B (`pilot_accept.py`, another branch)

Do not run `python -m unittest` and do not re-implement the channel. Call:

```python
import secrets
nonce = secrets.token_hex(32)          # one-time, never reused
result = taskpack.run_tests_with_runner(fresh_tree, "tests/test_hidden.py", nonce)
if not result["accepted"] or result["outcome"] != "PASS":
    reject(result["reason"] or result["outcome"])
```

`run_tests_with_runner(tree, test_ids_or_file=None, nonce=None, watch=None,
timeout=None, discover="tests", top=".") -> dict` copies the harness runner outside
`tree`, runs the hidden test in that FRESH directory with the same nonce/MAC/id-set
discipline, and returns `{"accepted", "outcome", "reason", "tests", "counts",
"exit_code", "executed", "expected_ids", "output"}`. `accepted` means *the report is
authentic and its ids match*; the caller must still require `outcome == "PASS"`.
`output` exists for the size cap only. The same call is what `verify_package` uses
internally, so there is one implementation of the discipline, not two.
`python experiments/v1.2/h4-micro-low-ablation/pilot/test_runner.py --help` documents the
fd protocol and this call.

#### Evidence (A3)

- `python experiments/v1.2/tests/test_v1_2_h4_pilot_taskpack.py` → `Ran 106 tests` `OK`
  (the 83 from A2 plus 23 new: N21/N22/N23, the fd forgery, the MAC and id-set mutation
  anchors, the patch-exercise cases, the runner API, the TMPDIR alias and Darwin default).
- Mutation audit (7 mutations, one defence removed at a time): all 7 killed,
  `ALIVE: none`, and the file was restored to the same sha256 afterwards. Anchors:
  `_verify_report_mac` → `return True`; `if missing or extra:` → `if False:`;
  `exercised = _patch_exercise_reason(...)` → `None`; the two `realpath` calls in
  `_sandbox_profile` removed; `if not _imports_src(...)` → `if False:`;
  `_interesting_patch_line` → `return True`; `HIDDEN_REPEATS = 1`.
- The round-2 corpus itself (copied to a scratch dir with `src/` linked read-only to this
  tree) now: `N21` exact → FAIL (`HIDDEN_TEST_DOES_NOT_IMPORT_TARGET`, and
  `PATCH_NOT_EXERCISED` for the importing variant); `N22` exact → FAIL
  (`VISIBLE_TESTS_RESULT_REJECTED TEST_RESULT_UNAVAILABLE`); `N23` exact → FAIL
  (`HIDDEN_TEST_RESULT_REJECTED TEST_RESULT_UNAVAILABLE`); `E4` → FAIL at structure
  (`TEST_COMMAND_NOT_CANONICAL`, no process started); `GOOD` → PASS.
- `python -m ruff check .`, `python scripts/validate_governance.py` (35/35),
  `python scripts/validate_public_release.py` (`VIOLATIONS=0`) — exact output in the
  final report of this commit.

#### Limits introduced or still open in A3

- **In-process attacker.** The runner imports the tests into its own process; the nonce
  is deleted after the report is written and the runner exits with `os._exit`, but code
  that walks frames (`sys._getframe`) while the tests run could reach the key. That is
  out of the stated threat model, not a claim of impossibility.
- **`def`/`class` lines are not counted as "the patch ran".** That is what kills the
  dead-code shape, but it also means a legitimate patch whose only added line is a bare
  declaration (with no executable body line) is refused. In practice a real fix adds at
  least one assignment, call, return or import.
- **Test ids are `Class.method`.** Two classes with the same name in different files
  collide, and a test case imported from another module (`from helpers import Base`
  where `Base` has `test_*` methods) is collected at runtime but absent from the static
  map, so such a package is refused. Both are documented rather than guessed around;
  synthetic packages define their cases locally.
- **Discovery mirrors `test*.py` by file name.** `unittest discover` additionally
  requires packages in subdirectories; a `tests/sub/test_x.py` without `__init__.py`
  would be counted by the AST scan and not by discovery, i.e. refused rather than
  silently ignored.
- The **`watch` map is per run**. If the hidden test never calls the changed function
  (for example it only reads the source), the fix is refused — by design (N21), but it
  also means a reference patch that fixes code the hidden test does not touch is
  rejected. That is the "hidden test must exercise the target" rule from P2-3.

### Fix round A2 (`65097be`) — carried forward

`pilot/taskpack.py`

- **P1-1 `test_command`**: only `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]`
  is accepted (`TEST_COMMAND_NOT_CANONICAL`). The check lives in check 1, before any
  process is started, so a `-c` payload that prints fake unittest output never runs.
  (A3 adds that this argv is display-only: the runner replaces its execution.)
- **P1-2/P1-3 phase and path awareness**: every phase runs at one fixed path,
  `<work>/phase/repo`, and the phase directory is deleted and recreated between phases.
- **P1-3 confinement**: commands run under `sandbox-exec` with a generated profile that
  denies `network*`, denies every write outside the phase directory (plus `/dev/null` and
  friends), and denies `file-read*` of the real home directory and of `/Users`. The
  reference patch is handed to `git apply` on stdin.
- **P1-3 unsandboxed fallback**: `sandbox_available()` probes `sandbox-exec` for real.
  When it is unavailable the package is still verified, `isolation` is `NONE`, and the
  overall verdict is `UNSANDBOXED` — never `PASS` — unless `allow_unsandboxed=True`.
  A3 adds `sandbox_probe_reason()`, which quotes the probe's own output; the tests that
  need confinement skip with that reason (a nested `sandbox-exec` lands here) and never
  pass without it.
- **P1-4 determinism**: `PYTHONHASHSEED=0`, `LC_ALL=C`, `PYTHONDONTWRITEBYTECODE=1`; the
  hidden test runs `HIDDEN_REPEATS` times per phase (3 at A2, 5 at A3) and the outcomes
  must agree, otherwise `NONDETERMINISTIC`.
- **P2-3**: `RUN_TIMEOUT = 30`; the first timeout (or output overflow) aborts the
  remaining phases.
- **P3**: unknown `package.json` / `gate` keys refused; `.git`, `__pycache__` and
  `*.pyc`/`*.pyo` refused; mode changes, copies/renames and binary hunks in
  `reference.patch` refused; the statement screen gained `oracle`, `grader`, `evaluat*`,
  `experiment*`, `treatment*`; the 8-word leak check also runs over case-folded word
  tokens; captured output capped at 1 MiB (`OUTPUT_OVERFLOW`); a package that already
  carries `SEAL.json` is refused by a plain `verify_package`
  (`SEAL_PRESENT_BEFORE_SEALING`) and only `seal_package` / `allow_reseal=True` may accept
  one; every verdict carries `sealed` and `isolation`; the CLI exits non-zero for
  anything that is not `PASS`.
- **E14**: two detectors close the single-assertion leak — the 8-word window and a
  24-character fragment window (`LEAK_CHAR_RUN`, `STATEMENT_LEAKS_HIDDEN_FRAGMENT`).

`pilot/maker_prompt.md` — the `test_command` value is the only accepted argv; the
eight-word leak window ignores case and punctuation; `.git`, `*.pyc` and `__pycache__`
anywhere are refused; the patch rules name copies and file deletions; and the base
section says confinement is enforced rather than requested.

`experiments/v1.2/tests/test_v1_2_h4_pilot_taskpack.py` — the 35 original tests stay,
plus 48 at A2 (83 total), plus 23 at A3 (106).

#### Behaviour changes that touched existing tests (stated plainly)

- At A2, `GoodPackageTests.test_good_package_is_accepted_then_sealed` now passes
  `allow_reseal=True` for the re-verification step, exactly as E22/E23 require; new
  tests assert the refusal without it. Nothing deleted or loosened.
- At A3, `test_hidden_test_is_run_three_times_in_each_phase` became
  `test_hidden_test_is_run_five_times_in_each_phase` (expects five runs and asserts
  `HIDDEN_REPEATS >= 5`), and `test_hidden_test_whose_runs_disagree_is_rejected` expects
  five recorded runs. Both changes follow P2-2; neither weakens an assertion.

#### Limits (A2, still true)

- **The fragment window is a threshold, not a proof.** A leak shorter than 24 identical
  alphanumeric characters (for example a bare `x + 1`) is not caught, and a statement
  that legitimately shares a 24-character run with the hidden test would be refused.
- **The sandbox is confinement, not a security boundary.** `sandbox-exec` confines the
  workspace, not a kernel-level attacker; Apple has deprecated it. If it disappears, the
  verdict becomes `UNSANDBOXED` and no seal can be written.
- **Read denials cover the real home and `/Users` only.** Other absolute paths (for
  example another mount under `/Volumes`) are not denied; writes are still limited to the
  phase directory.
- **`git` is required** for the patch phase, and it must be able to stat the parent of
  the phase directory, which is why the work directory itself is not on the read-deny
  list.
- **The 1 MiB cap is per process**, not per verification: several phases may each produce
  up to the cap before the first overflow aborts the run.
