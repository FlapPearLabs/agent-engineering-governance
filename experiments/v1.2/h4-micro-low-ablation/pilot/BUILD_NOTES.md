# H4 exploratory pilot — build notes (ticket B: arms, driver, acceptance — fix round)

STATUS = **EXPLORATORY**. Contract: [`PILOT_SPEC.md`](PILOT_SPEC.md). This build changes nothing in
`TASKS.md` (`PROTOCOL_NOT_STARTABLE` stands), freezes no protocol, and produces no formal evidence.
No model, no network, no `run_h2r2.py`, no runs root were used to build or test it.

This round is a **fix ticket on my own earlier work** (`4856a90`), driven by the independent
acceptance report `ACCEPT.md` (verdict REJECT: 2 P1, 3 P2, plus P3). Nothing here is an acceptance
verdict: the same implementer does not sign off on its own work.

## What is here

| File | Role |
| --- | --- |
| `arms.py` | FULL/MIN/INJECT carriers: deterministic `git show <materials>:AGENTS.md` §2–§4 extraction with an 11-rule byte-range manifest, the MIN A-layer carrier, outside-repository delivery, readback verification, and the leak scan (anchors/sentinels **plus** a 10-word verbatim window overlap). |
| `a_layer_min.md` | The MIN base text. **ASSUMED**, hand-written for the pilot — see "What is assumed" below. |
| `pilot_accept.py` | Seal re-verification through the agreed `taskpack` interface, the **fresh acceptance directory**, the canary negative control, the fixed acceptance order (visible tests → ruff → hidden test), the registered F-010 injection and the N7 probe. |
| `pilot_driver.py` | Authorization gate (absolute, non-symlink, non-temp, capped), `--fake-worker` stub path, the real launch path (import-only reuse of `freeze-v3`, frozen driver-root layout), the sandbox probe, per-run durable records. |
| `../../tests/test_v1_2_h4_pilot_arms.py` | Carrier tests: FULL ≠ MIN, MIN carries none of the 11 (anchors, sentinels **and** verbatim slices), missing/substituted/wrong/extra carrier rejected, delivery refusals, stale-range detection, FULL not blocked by the window check. |
| `../../tests/test_v1_2_h4_pilot_driver.py` | Driver tests: authorization refusals (relative/symlink/temp/cap/unknown keys), fake worker through all three arms, fresh-tree acceptance + canary, the two escape attacks, INJECT miss → `INVALID`, N7 positive direction, seal tamper, driver-root layout, sandbox probe, isolation. |

`taskpack.py` is **not** in this worktree: it belongs to a parallel implementer. `pilot_accept`
imports it lazily through `taskpack_module()`, and the tests replace that function with a stand-in
that implements the agreed `verify_seal(pkg_dir) -> None` / `taskpack.SealError` contract over a
hand-built package and a hand-computed `SEAL.json`. The real module was exercised separately — see
"Merge with the taskpack branch" below.

## What the fix round changed

### D1 (P1) — the worker could neuter its own acceptance gate

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

### D2 (P1) — a MIN carrier could carry verbatim rule text

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

### D3 (P2) — the real launch put the driver root inside the worker's launch

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

### D4 (P2) — two rejections had no test behind them

**Was:** deleting the `raise` in `arms.build`'s MIN leak guard, or the
`RESULTS_DIR_INSIDE_REPOSITORY` branch in `pilot_driver.results_dir_reason`, left the suite green.

**Now:** the two tests above (D2 build refusal) and
`test_a_results_directory_inside_the_repository_is_refused` fail when those lines are removed.
Verified by mutation: a throwaway copy of this worktree with each guard disabled shows exactly one
new failure per mutation and an empty `alive` list (see evidence).

### D5 (P2) — the isolation test was red instead of skipped under an outer sandbox

**Was:** `SANDBOX_READY` was `platform == darwin and which("sandbox-exec")`, which is true inside the
acceptance wrapper even though `sandbox_apply` fails there; the isolation test then failed red.

**Now:** `pilot_driver.sandbox_probe()` really runs
`sandbox-exec -p '(version 1)(allow default)' /usr/bin/true` and requires rc 0. On failure the last
stderr line (`sandbox_apply: Operation not permitted`) becomes the `skipUnless` reason. A probe that
cannot even start, and a host without `sandbox-exec`, also return `False` with a reason — never a
pass. Tests: `test_the_sandbox_probe_reports_the_real_failure_reason`,
`test_the_sandbox_probe_never_passes_without_running`,
`test_the_sandbox_probe_confirms_a_working_host` (runs only on a host that passes the probe).

### P3 — authorization is a durable artifact, not any file an environment variable names

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

## Evidence

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

## Merge with the taskpack branch (ticket A, current tip)

A throwaway clone of this branch, with this round's working tree applied, then
`git merge --no-ff origin/experiment/v1.2-h4-pilot-a` (tip `65097be`). Result:

- **One conflict, documentation only:** `pilot/BUILD_NOTES.md` is added by both branches (add/add).
  Resolved in the throwaway clone by keeping this file. Folding the two build notes into one is an
  integrator decision; the *code* merges cleanly.
- All pilot test files in the merged tree:
  `test_v1_2_h4_pilot_arms` 17 OK, `test_v1_2_h4_pilot_driver` 27 OK,
  `test_v1_2_h4_pilot_taskpack` 83 OK (A's suite, unchanged).
- End-to-end integration against the **real** `taskpack.py` (no stand-in): my fixture package
  verifies with checks 1–6 `PASS` and check 7 `SEAL_PRESENT_BEFORE_SEALING` (the fixture seals
  itself, and A refuses a pre-existing seal unless `allow_reseal`), `seal_package` then writes a
  9-file seal, `pilot_accept.load_package` accepts it, and `pilot_driver.main --fake-worker` runs
  all three arms `PASS` with `inject=CAUGHT` and the canary `CANARY_FAILS_AS_REQUIRED`.
- **No change to `taskpack.py` is needed from this side.** One observation for A's maker flow, which
  A's prompt already states but a fixture missed: the canonical `-t .` command makes the base
  `tests/` directory need `tests/__init__.py`, otherwise discovery raises
  `Start directory is not importable`.

## Deviations and decisions that a reviewer should check

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

## What is assumed (not measured, not canonical)

- `a_layer_min.md` is **hand-written**. At this commit the repository has no frozen A-layer *text* to
  extract, so the file is labelled `ASSUMED` in its own heading, in `arms.build` (`assumed: true`)
  and in the carrier manifest. It is not relabelled canonical authority.
- Nothing here proves that the MIN carrier is a fair "A-layer only" treatment; it proves it carries
  none of the eleven process instructions by three mechanical tests (anchors, sentinels, ten-word
  verbatim windows) and names no governance file. That is a proxy, not a semantic proof.

## Limits (stated, not fixed)

- **The canary is a negative control, not a proof.** It catches the attacks that were demonstrated
  (a `tests/__init__.py` and a `src/__init__.py` that neuter `unittest`, and a fake `unittest`
  module) because every canary test must fail. A worker that special-cases the canary's module name,
  or that patches assertions only for the hidden test's module, is not excluded by construction; the
  canary raises the cost, it does not close the category.
- **The window guard is a threshold.** Ten words catches a copied sentence; it misses a paraphrase,
  a reordered sentence, and any of the three ranges shorter than ten words. Those three are still
  covered by their anchor/sentinel text only.
- **`budget_cap` is recorded, never enforced.** `max_runs` is the only enforced limit; the ceiling on
  `budget_cap` is a sanity check on the recorded number.
- **The real launch is unproven.** `real_launch()` — the `opencode serve`/`run` invocation, the
  profile and fresh home as called from this module, the confinement self-test, the 90-minute wall
  clock, `INVALID:TIMEOUT`, token/cost parsing — is never executed by any test and was never executed
  here. The **layout** is now evaluated (D3), the calls were checked statically by the acceptance
  script (`e_static.py`), and nothing more.
- **The sandbox is confinement, not a security boundary**, and `sandbox-exec` is deprecated by Apple.
  If it disappears the probe fails and the isolation test skips with that reason.

## Unverified / needs a decision

- The real launch path (see above) — unexecuted by design, and unauthorized: no run was performed.
- Whether the ACCEPTOR should be one program (`pilot_accept.py`) or a separate entry point; the
  pilot spec groups acceptance with the driver's per-run record, which is what this build does.
- Where the durable results root will actually live for a real run: it must be outside every home,
  the repository and every guidance marker, and a temporary root is refused. That is an operator
  decision, not a constant in the code.
- `statement.md` leak checking (spec item 5) and the reference-patch size/risk rules (item 6) belong
  to `taskpack.py`'s verifier and are out of scope here.
