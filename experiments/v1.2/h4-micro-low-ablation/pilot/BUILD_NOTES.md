# H4 exploratory pilot — build notes (ticket B: arms, driver, acceptance)

STATUS = **EXPLORATORY**. Contract: [`PILOT_SPEC.md`](PILOT_SPEC.md). This build changes nothing in
`TASKS.md` (`PROTOCOL_NOT_STARTABLE` stands), freezes no protocol, and produces no formal evidence.
No model, no network, no `run_h2r2.py`, no runs root were used to build or test it.

## What is here

| File | Role |
| --- | --- |
| `arms.py` | FULL/MIN/INJECT carriers: deterministic `git show <materials>:AGENTS.md` §2–§4 extraction with an 11-rule byte-range manifest, the MIN A-layer carrier, outside-repository delivery, readback verification and leak scans. |
| `a_layer_min.md` | The MIN base text. **ASSUMED**, hand-written for the pilot — see "What is assumed" below. |
| `pilot_accept.py` | Seal re-verification through the agreed `taskpack` interface, the fixed acceptance order (visible tests → ruff → hidden test), the registered F-010 injection and the N7 probe. |
| `pilot_driver.py` | Authorization gate, `--fake-worker` stub path, the real launch path (import-only reuse of `freeze-v3`), per-run durable records. |
| `../../tests/test_v1_2_h4_pilot_arms.py` | Carrier tests: FULL ≠ MIN, MIN carries none of the 11, missing/substituted/wrong/extra carrier rejected, delivery refusals, stale-range detection. |
| `../../tests/test_v1_2_h4_pilot_driver.py` | Driver tests: authorization refusals, fake worker through all three arms, INJECT miss → `INVALID`, N7 positive direction, seal tamper, isolation. |

`taskpack.py` is **not** in this worktree: it belongs to a parallel implementer. `pilot_accept` imports
it lazily through `taskpack_module()`, and the tests replace that function with a stand-in that
implements the agreed `verify_seal(pkg_dir) -> None` / `taskpack.SealError` contract over a
hand-built package and a hand-computed `SEAL.json`.

## Real-launch code that no test executes

`pilot_driver.real_launch()` is **never executed by any test** and was **never executed by the
implementer**. It is code that is written against the frozen `freeze-v3` modules but unproven:

- the `opencode serve` / `opencode run` invocation (`sandbox_v2.confine`, `sandbox_v2.TOOLS`), the
  produced prompt, the per-launch `--format json` stream;
- `sandbox_v2.fresh_home` / `home_env` / `plant` / `self_test` as called from this module (the
  self-test itself is exercised by the freeze-v3 suite, not by this pilot);
- `wrapper_delivery.run_root_reason` applied to a pilot run directory;
- the 90-minute wall clock, the `INVALID:TIMEOUT` boundary, token/cost capture from a real stream
  (`worker-report.json` exists only on the fake path, so real runs record `tokens = UNKNOWN` and
  `cost = UNKNOWN` until someone adds a parser);
- any provider reachability, retry or budget-spend behaviour. The pilot enforces `max_runs`; it
  **cannot** enforce `budget_cap` because no run cost was ever observed, so an authorized record
  states `budget_enforcement: MAX_RUNS_ONLY;RUN_COST_UNOBSERVED` next to `tokens/cost = UNKNOWN`.

`pilot_driver.render_profile()` **is** executed by the isolation test — it renders a real
`sandbox-exec` profile through the frozen template and runs reads under it. That is rendering and
confinement, still no worker and no model.

The fake worker is a stub: it applies the package's `reference.patch` and therefore reads quarantine
content. It exists to drive the plumbing deterministically, and every record it produces is labelled
`model: FAKE_WORKER`, `measurement: NOT_A_MEASUREMENT`.

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
4. **Results-directory durability.** A real run refuses a results directory under a temporary root or
   inside the repository. `--fake-worker` (test only) accepts a temporary root and records
   `results_durability=EPHEMERAL_TEST_PATH`, so a test can never pass by claiming durability it does
   not have.
5. **Isolation test uses a synthetic home-shaped tree.** Committed tests may not contain the
   operator's home path, so the test places `.agents/AGENTS.md` and `.config/opencode/AGENTS.md`
   under a synthetic `global-home/` that sits **outside** the launch directory and outside the fresh
   home. The profile denies it for the same reason it denies the real home: only the launch
   directory, the fresh home, the interpreter and the system read roots are allowed. The test asserts
   the denial is `Operation not permitted` (not `No such file`), for both `cat` and a `-c` read, and
   asserts one allowed read as the positive control. It **skips with an explicit reason** when
   `sandbox-exec` is unavailable; it never passes without running.
6. **Range sentinels.** Each of the eleven rule ranges carries a token that must fall inside that
   range (`RULE_TABLE`), so a shifted or emptied range fails to build instead of silently mapping
   the wrong bytes. `R-V12-046`'s range ends at the end of §4 (it has no closing heading inside the
   section).

## What is assumed (not measured, not canonical)

- `a_layer_min.md` is **hand-written**. At this commit the repository has no frozen A-layer *text*
  to extract, so the file is labelled `ASSUMED` in its own heading, in `arms.build`
  (`assumed: true`) and in the carrier manifest. It is not relabelled canonical authority.
- Nothing here proves that the MIN carrier is a fair "A-layer only" treatment; it proves it carries
  none of the eleven process instructions (anchor text + sentinel tokens + no governance-file
  reference), which is a mechanical proxy, not a semantic proof.
- Cost, duration, token counts and variance are **unknown**; no run was performed.

## Gates run before the commit

```text
$ env -u PYTHONPATH python -m ruff check .
All checks passed!

$ env -u PYTHONPATH python scripts/validate_governance.py
35/35 checks passed

$ env -u PYTHONPATH python scripts/validate_public_release.py
VIOLATIONS=0

$ cd experiments/v1.2/tests && env -u PYTHONPATH python -m unittest test_v1_2_h4_pilot_arms
Ran 13 tests ... OK

$ cd experiments/v1.2/tests && env -u PYTHONPATH python -m unittest test_v1_2_h4_pilot_driver
Ran 12 tests ... OK
```

## Unverified / needs a decision

- The real launch path (see above) — unexecuted by design, and unauthorized: no run was performed.
- The seal interface against the real `taskpack.py`; only the stand-in was exercised. The two files
  must be wired together with one shared package fixture once both land.
- Whether the ACCEPTOR should be one program (`pilot_accept.py`) or a separate entry point; the
  pilot spec groups acceptance with the driver's per-run record, which is what this build does.
- `statement.md` leak checking (spec item 5) and the reference-patch size/risk rules (item 6) belong
  to `taskpack.py`'s verifier and are out of scope here.
