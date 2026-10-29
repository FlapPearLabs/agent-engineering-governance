# Freeze v2 — acceptance round 3 of 5b14c2b: F5–F6 closed; F7 open (fix plan T18–T20)

Accepted at 5b14c2b (verified by Claude): write scope; frozen surfaces untouched; identity; every
gate green on independent re-run; and, LIVE in the isolated profile with the frozen
worker-profile/opencode.json installed byte-identically:

```text
F5  preflight (opencode debug paths/config)    -> PASS, all paths in the profile home, exactly the
                                                  two profile config sources, template sha256 equal
F5  live canary with the structured line       -> PASS; H2_CANARY_SOURCES mcp=0 plugin_agents=0
                                                  skills=opencode,report; startup/repo/nested order
F6  worker told to use the question tool       -> tool unavailable, run ends in 9 s (no stall)
```

Implementer: opencode (deepseek-v4.1-flash). The ground rules, NEVER TOUCH list and GATES of
CODEX_PLAN.md §0 still bind every task; write scope unchanged (freeze-v3/** and
experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py).

## Finding

```text
F7  P1  NO FROZEN WAY TO RUN A WORKER. Delivery, collection, acceptance, preflight and the
        canary are frozen, but HOW a run is executed is not: the worker launch command, the
        launch prompt, the 90-minute limit, plan-order enforcement, the per-run independent
        auditor (protocol-v2 §5 step 4) and the run registry exist only as prose. Whatever the
        operator types at run time would be an unfrozen experimental input, and could differ
        between arms or runs.
```

## T18 — `freeze-v3/run_h2r2.py` (the only way a run is executed)

Subcommands: `next --runs-root R` (prints the next run id in plan order), `run <run_id> --runs-root R`,
`status --runs-root R`. Rules:
- R must pass the T13 run-root rule (outside every home, no guidance-bearing ancestor).
- Plan order: `run` refuses any run whose predecessors in run-plan-v3.json are not registered
  (ACCEPT / REJECT / INVALID / BLOCKED all count as registered). A run id that was ever started
  can never start again: a second attempt is refused (protocol §6: no silent re-run).
- Steps, each recorded with timestamps in `R/<run_id>/run.json`:
  1. `wrapper_delivery.prepare` with the plan's materials commit;
  2. `isolation_canary preflight` against the frozen worker-profile template — FAIL => BLOCKED,
     worker never launched;
  3. `render_brief` into `R/<run_id>/CONTRACT.md`;
  4. worker launch, exactly:
     `opencode run --standalone --auto --format json -m <plan model> "<LAUNCH_PROMPT>"`
     with cwd = `R/<run_id>`, stdin = /dev/null, the environment = the profile env file's
     exports applied to a minimal base env (PATH, LANG; nothing else inherited), stdout →
     `events.jsonl`, stderr → `stderr.txt`. LAUNCH_PROMPT is one frozen constant, identical for
     both arms, that only says to read ./CONTRACT.md and do what it asks. Hard wall-clock limit
     90 min: on expiry the process group is killed and the run is INVALID:TIMEOUT. A non-zero
     exit, an `error` event or an empty event stream is INVALID with that reason.
  5. `collect_v2` + `run_acceptance_v2` → `verdict.json`;
  6. auditor (T19);
  7. append one line to `R/registry-v3.jsonl`: run_id, task_id, arm, verdict, audit verdict,
     invalid/blocked reason, session id, wall clock, sha256 of every artifact.
- The worker command, the launch prompt, the env allow-list and the limit are module constants
  pinned in the manifest. For tests only, the worker command can be replaced by a stub through
  an argument that the `run` CLI does not expose.

## T19 — per-run independent auditor (protocol-v2 §5 step 4, rubric §4/§10)

- After acceptance, a FRESH opencode session (same isolated profile, same model, new session,
  cwd = `R/<run_id>/audit/`, outside the worker's dir) audits a BLINDED bundle copied into that
  dir: CONTRACT.md with the delivery block removed, the base→worker diff, verdict.json, the
  worker report; arm label, carrier text, H2_WARM paths and telemetry are excluded; any
  remaining arm-revealing string found by a frozen scan is recorded as LEAKAGE (best effort,
  rubric §10). Frozen AUDIT_PROMPT constant; the auditor writes `audit.json` with the rubric §4
  correctness fields and the rubric §2–§3 finding list. Missing/malformed audit.json => the run
  is BLOCKED (not INVALID), visibly.
- The registry records both the mechanical verdict and the audit; the stricter one wins
  (protocol: conservative).

## T20 — tests, re-pin, report

- Tests use a stub worker (never a model): the stub applies the candidate's non-test delta
  (=> ACCEPT path end to end), does nothing (=> REJECT), sleeps past a shortened limit
  (=> INVALID:TIMEOUT), and writes an `error` event (=> INVALID). Also: plan order refusal,
  second-start refusal, BLOCKED on preflight failure, blinded bundle contains no arm label.
- Regenerate run plan / manifest / literals; append a T18–T20 section to CODEX_REPORT.md.
