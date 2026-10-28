# Freeze v2 — bounded parallel execution of the twenty runs (T34)

Implementer: opencode (deepseek-v4.1-flash). The ground rules and NEVER TOUCH list of
CODEX_PLAN.md §0 still bind; write scope unchanged. Decided by the user before any counted run
(2026-10-23): the twenty runs execute two at a time. This is developed in parallel with T32 on a
separate branch and merged before the re-pin (T33), so no counted run ever used the serial rule.

## Why

Each run takes 10–90 minutes; strictly serial execution makes the twenty runs take most of a day.
Every run already has its own run dir, fresh home, rendered sandbox and driver-held streams, so two
runs of DIFFERENT tasks cannot see each other (the sandbox denies every other run's contents).

## T34 — pre-registered bounded concurrency

1. Frozen constant `MAX_PARALLEL = 2` in run_h2r2.py (hashed with the program; changing it is a
   design change).
2. Eligibility replaces "every predecessor registered": a run may start when (a) it is not
   registered and not started (existing checks), (b) the OTHER arm of the same task, if it comes
   earlier in plan order, is registered (within-task counterbalancing order is preserved exactly),
   (c) fewer than MAX_PARALLEL runs of this runs root are in progress (live lock holders), and
   (d) every run earlier in plan order is registered or in progress — i.e. runs START in plan
   order; only finishing may overlap. Refusal reasons stay explicit
   (`PREDECESSOR_NOT_STARTED:<id>`, `SAME_TASK_ARM_NOT_REGISTERED:<id>`,
   `PARALLEL_LIMIT:<n>`).
3. New subcommand `run_h2r2.py run-plan --runs-root R`: a scheduler that repeatedly starts the
   next eligible run (each as its own `run` child process, so one crash cannot take another run
   down), keeps at most MAX_PARALLEL alive, waits, and stops when the plan is COMPLETE. A run that
   ends BLOCKED:PROVIDER_UNREACHABLE (not registered) is retried by the scheduler after a pause,
   in plan position, at most 3 times per scheduler invocation; then the scheduler stops and prints
   what is left (operator re-invokes). It never re-runs a registered run. Scheduler output is
   appended to `<runs_root>/scheduler-v3.jsonl` (start/end time, pid, run id, outcome).
4. Registry and attempts files are appended under an exclusive file lock (fcntl.flock) so two
   finishing runs cannot interleave lines; the run lock logic keeps its current semantics.
5. Shared machine resources: the F22 preflight service port is chosen per run and must not race
   (bind-then-release immediately before `service set port`; on "already in use" retry with a new
   port, at most 3 times, recorded). Any other shared temp or port use found in the code gets the
   same treatment.
6. `status` shows in-progress runs. Each run.json records `concurrent_with` (run ids whose
   execution overlapped it) and start/end timestamps; aggregate_runs.py reports overlap pairs.
7. protocol-v2 §5/§6 and README: the concurrency rule, its rationale (wall clock; isolation makes
   cross-run influence impossible except shared provider load, which is arm-symmetric because two
   concurrent runs are different tasks and arms alternate in plan order), and that it was fixed
   before the first counted run.

Tests (stub workers that sleep, never a model; use the existing StubSandbox/StubAuth): never more
than MAX_PARALLEL alive; starts happen in plan order; the second arm of a task never starts before
the first is registered; a reachability-BLOCKED run is retried by the scheduler and its slot
reused; concurrent registry appends produce well-formed lines; a killed scheduler leaves started
runs to the existing INTERRUPTED rule; `run` of a non-eligible id is refused with the reason.

## Gate for this task (speed rule decided 2026-10-23)

Run ruff, validate_governance, validate_public_release and ONLY the freeze-v3 test module
(`-p test_v1_2_h2_freeze_v2.py`, PYTHONPATH unset). Do NOT run the full scripts/tests or the full
experiments suite and do NOT re-pin the manifest: the merged result is re-pinned and fully gated
once in T33. A manifest-hash test that fails ONLY because run_h2r2.py's bytes changed is expected
here; name it in CODEX_REPORT and do not edit the pinned literals.

## T35 — four-way concurrency, backoff, and the pre-registered model rule (user decision 2026-10-23)

1. `MAX_PARALLEL = 4` (was 2). Same eligibility rules as T34: starts in plan order, the second arm
   of a task only after the first is registered.
2. Backoff: a run that ends BLOCKED before work (PROVIDER_UNREACHABLE, or an attempt that hit the
   before-work rule three times) is re-queued by the scheduler with exponential backoff plus jitter
   (60 s, 120 s, 240 s, 480 s, 900 s cap; up to 6 re-queues per scheduler invocation), keeping its
   plan position; other eligible runs keep their slots meanwhile. Every wait is logged in
   scheduler-v3.jsonl. After the budget the scheduler stops and prints what remains (operator
   re-invokes); nothing registered is ever re-run.
3. Model rule (pre-registered, outcome-blind): every worker and auditor launch of the twenty uses the
   single frozen model of run-plan-v3.json (opencode-go/deepseek-v4.1-flash). There is NO model
   failover inside the experiment: the model is part of the treatment environment, and a pair whose
   arms ran on different models is not a comparison (protocol §6 "model tier mismatch" is INVALID).
   Provider outages are handled only by waiting (rule 2) and by the existing reachability and
   before-work rules. Failover to other models exists only in the implementation pipeline, which
   never touches H2-R2 runs. Record this in protocol-v2 §6.1 and README.
Tests (stubs only): four alive at most; a stub probe failing twice then passing is re-queued with
growing recorded waits and then runs; the budget exhausted -> scheduler exits listing the run; the
worker and auditor argv always carry the frozen model.
Gate: same speed rule as T34 (ruff, governance, public release, the freeze-v3 test module only;
no re-pin).
