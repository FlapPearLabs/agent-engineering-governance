# Freeze v2 — pilot batch at 8850187: F44 (fix plan T42)

Implementer: opencode (deepseek-v4.1-flash via the implementation launcher). Ground rules and NEVER
TOUCH list of CODEX_PLAN.md §0 bind; write scope unchanged.

Accepted at 8850187 (Claude): F43 fixed — the real event streams of all six pilots so far (285 tool
calls, including pilot #9's workdir calls) replay through the T41 audit with 0 hits.

## Finding

```text
F44 P2  BOUNDED CONCURRENCY IS EFFECTIVELY SERIAL. run-plan-v2 lists both arms of a task next to
        each other (f01 c,v / f02 v,c / ...). T34's eligibility rule (d) "every run earlier in plan
        order is registered or in progress" plus rule (b) "the other arm of the same task, if
        earlier, is registered" means the second arm of task k blocks every later run until the
        first arm of task k has finished. Live: `run-plan` on a pilot runs root started exactly one
        run (h2r2-f01-c) in five minutes with MAX_PARALLEL = 4. The user-approved speed-up (four at
        a time) never happens; the twenty runs would take most of a day.
```

## T42 — eligibility that keeps the pre-registered order and actually parallelises (one commit)

1. Replace rule (d): a run may start when every EARLIER run in plan order is registered, in
   progress, OR is itself waiting only on rule (b) (its own task's first arm is not yet registered).
   Rules (a) not registered/not started, (b) same-task first arm registered, (c) fewer than
   MAX_PARALLEL live runs are unchanged. Effect: the first arms of up to four tasks start together
   in plan order; a second arm starts as soon as its own first arm is registered, before any later
   task that has not started yet (plan order among eligible runs is preserved). Within-task
   counterbalancing (c-first vs v-first) is exactly as frozen.
2. Refusal reasons stay explicit (`PREDECESSOR_NOT_STARTED:<id>` now only for an earlier run that is
   neither started nor waiting on rule (b)). protocol-v2 §5/§6 and README: state the rule, that it
   was changed before the first counted run, and why (F44).
3. Tests (stub workers, never a model): with MAX_PARALLEL = 4 and the real run plan, the first four
   starts are the first arms of four different tasks in plan order; no second arm starts before its
   first arm is registered; a second arm whose first arm finished is started before a later task's
   first arm; never more than four alive; a killed scheduler leaves started runs to the existing
   INTERRUPTED rule.
4. Regenerate run plan / manifest / anchors / literals with the build programs; append a T42 section
   to CODEX_REPORT.md; run ALL gates of CODEX_PLAN §0 once; commit only if all pass.
