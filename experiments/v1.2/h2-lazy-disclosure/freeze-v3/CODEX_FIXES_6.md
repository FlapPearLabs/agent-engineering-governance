# Freeze v2 — acceptance round 6 of dd786f2: F14 provider flakiness (fix plan T26–T27)

Implementer: opencode (deepseek-v4.1-flash). The ground rules, NEVER TOUCH list and GATES of
CODEX_PLAN.md §0 still bind every task; write scope unchanged.

Accepted at dd786f2 (verified by Claude): write scope; identity; T24 behaviour on the live pilot
stream (access audit PASS on the real stream; reads of the governance checkout, `../` escapes,
`git -C`/`cd` into another repository and `~` paths INVALID; the `source /dev/null;` test command
PASS; PYTHONDONTWRITEBYTECODE=1 frozen into the worker env).

## Finding

```text
F14 P1  A TRANSIENT PROVIDER ERROR DESTROYS A RUN. Live pilot #2 (run_h2r2.py at dd786f2,
        separate runs root) ended INVALID after 14 s: the worker's first and only event was
        {"type":"error","error":{"type":"provider.no-route",
         "message":"Model unavailable: opencode-go/deepseek-v4.1-flash"}}, exit 1, no tool call.
        Minutes later the SAME env (built by run_h2r2.worker_env) answered a test prompt twice.
        This is the third transient upstream failure in two days (401 Invalid credential,
        "stream ended without finish_reason", provider.no-route). Under the current rules such a
        run is INVALID and may never run again, so infrastructure noise — not the treatment —
        would eat counted runs, possibly unequally between arms.
```

## T26 — pre-registered infrastructure-failure rule (decided before any counted run)

1. Reachability check: immediately before launching the worker (and the auditor), the driver sends
   one frozen minimal prompt (e.g. "Reply with exactly: H2_REACHABLE") with the SAME command, model
   and env, in a scratch dir outside the run dir, with a short limit (e.g. 120 s). Failure =>
   the run is BLOCKED:PROVIDER_UNREACHABLE, nothing is launched, no attempt is consumed, and
   `run` may be invoked again for the same run id later (record every check with timestamp).
2. Failure before work: if the worker's event stream contains a provider error (`error` event
   whose type starts with `provider.`) BEFORE its first tool_use event, or the worker exits
   non-zero with zero tool_use events, the attempt is BLOCKED:PROVIDER_FAILED_BEFORE_WORK. The
   driver archives that attempt's artefacts under `<run_id>/attempts/<n>/`, re-prepares a FRESH
   run dir from scratch (new repo/, new delivery, preflight again) and retries; at most 3
   attempts per run id; every attempt is a registry line with its attempt number. After 3
   blocked attempts the run is BLOCKED and the driver stops (operator decides later; never
   silently skipped).
3. Once the worker has made ANY tool call, nothing is retried: a later provider error, exit or
   timeout is INVALID exactly as now. The same rule, with its own counter, applies to the
   auditor (a blocked audit leaves the mechanical verdict intact and the run BLOCKED until a
   later audit succeeds).
4. The final per-run verdict is taken from the single attempt that reached work; the registry
   keeps all attempts. protocol-v2 §6 and README record the rule, its rationale (F14, the three
   observed failures) and that it is arm-symmetric and outcome-blind (it triggers only before any
   worker action, so it cannot be used to re-roll a result).

Tests (stub worker, never a model): reachability failure => BLOCKED, no attempt consumed;
provider error before work => retried with a fresh run dir, attempt 2 ACCEPTs; three
before-work failures => BLOCKED and stop; provider error AFTER a tool call => INVALID, no retry;
attempt archives are complete and hashed.

## T27 — re-pin and report

Regenerate run plan / manifest / literals; append a T26–T27 section to CODEX_REPORT.md.
