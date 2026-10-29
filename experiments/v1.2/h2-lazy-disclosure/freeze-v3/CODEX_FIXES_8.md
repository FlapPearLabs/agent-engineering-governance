# Freeze v2 — acceptance of T28–T30 with a live pilot: F22–F25 (fix plan T32–T33)

Implementer: opencode (deepseek-v4.1-flash). The ground rules, NEVER TOUCH list and GATES of
CODEX_PLAN.md §0 still bind every task; write scope unchanged. T31 of CODEX_FIXES_7 (re-pin and
report) is NOT run separately: it is folded into T33 below.

Accepted (verified by Claude): T28 at 1c2523e — the review's assume-unchanged edit, a
skip-worktree delete, a `.gitattributes` filter and `diff.external` leave `git status` silent but
the collector reports A/M/D, acceptance gives REJECT WORKER_SCOPE_DENIED for both deny files, and
the diff carries the injected line; repo/ history is one neutral commit. T29 at 4864655 — scope and
identity; the tests cover the review's three dynamic reads, the event-stream rewrite and the fresh
home. T30 at 8008cc7 — a fake HOME no longer
unlocks a run root under a user home, a dangling `.agents` symlink is refused, the shared users
folder stays allowed, and aggregate_runs.py on a real pilot runs root reports
COVERAGE:MISSING with every unregistered run.

## Live pilot (not counted; separate runs roots, the T29 driver from a clean clone)

Pilot `pilot-4864655` ended BLOCKED at preflight (F22). With two diagnostic patches applied ONLY in
Claude's scratch clone (never committed: a per-home service port and the F23 line), pilot
`pilot-4864655c` then ran end to end under the real sandbox and fresh home: reachability probe
(H2_REACHABLE), preflight PASS, confinement self-test PASS, worker (9 tool calls), collection,
acceptance, access audit PASS, auditor with a real blind bundle, registry. It exposed F24 and F25.

```text
F22 P1  FRESH-HOME PREFLIGHT COLLIDES ON THE SERVICE PORT. `opencode debug paths|config` is not a
        standalone command: in a home without service settings it starts a managed background
        service on the default port, which another opencode service on the machine (here the
        operator's own) already holds -> "Managed service port ... is already in use", exit 1,
        PREFLIGHT_COMMAND_FAILED:config -> every run BLOCKED. Measured fix: in the fresh home run
        `opencode service set port <free 127.0.0.1 port>` first, then the two debug commands, then
        `opencode service stop`.
F23 P1  THE REAL REACHABILITY PATH CRASHES. default_probe passes `prepared` (no "profile" key) to
        `confined`, so every live probe raises KeyError: 'profile'; it is not caught (only
        OSError/ValueError are), the driver dies with a traceback and the run is left prepared but
        unregistered. Every test injects `probe=passing_probe`, so the real path never ran in a test.
F24 P1  THE CONTRACT EXPECTS THE OLD BASE SHA. T28 delivers a neutral HEAD (f01: 42123e7) but the
        rendered CONTRACT still states EXPECTED_BASE_SHA = the original base (e11a846). The live
        worker ran the contract's S0 check, found the mismatch and halted as instructed
        (report: "PREFLIGHT_FAIL: repo/ HEAD=42123e7... != EXPECTED_BASE_SHA e11a846..."). Every run
        would end the same way in both arms.
F25 P2  ZSH HEREDOCS FAIL IN THE SANDBOX. The worker's shell is zsh; zsh writes heredoc temp files
        under TMPPREFIX (default /tmp/zsh), not TMPDIR, and /private/tmp is denied:
        "can't create temp file for here document: operation not permitted". The worker had to
        fall back to the write tool; a common shell idiom fails in both arms.
```

## T32 — close F22–F25

1. F22: preflight in a fresh home runs `opencode service set port <port>` (a free 127.0.0.1 port
   chosen by the driver), then `debug paths`, `debug config`, then `opencode service stop`; the
   port and the stop result are recorded in preflight.json; a stop failure is recorded, not
   hidden. No service process may outlive the preflight (check `opencode service status` in that
   home says it is not running; else BLOCKED:SERVICE_LEFT_RUNNING). Same for any other `debug`
   call the canary makes.
2. F23: the probe launches with the rendered profile. Add a top-level harness guard in execute():
   an unexpected exception BEFORE the worker is launched ends the invocation as
   BLOCKED:HARNESS_DEFECT:<ExceptionType> (recorded with the traceback under .driver/, no attempt
   consumed, re-invokable); an unexpected exception AFTER the worker was launched registers the
   run INVALID:HARNESS_DEFECT:<ExceptionType>. Record the rule in protocol-v2 §6.1 (outcome-blind:
   it never depends on what the worker did).
3. F24: the rendered CONTRACT (and every place the brief or the auditor bundle states the expected
   repository identity) states the DELIVERED head of that task, computed by the same function
   wrapper_delivery uses (deterministic: base tree + fixed metadata), and states that it is a
   neutral re-commit of the registered base tree. The registry's base_sha stays the identity of
   record. Never expose the original base or candidate sha to the worker.
4. F25: the frozen worker/auditor/probe env adds `TMPPREFIX=<launch dir>/.tmp/zsh` (zsh heredocs)
   next to TMPDIR; record it in protocol-v2 §4/§5 and README.
Tests (no model):
- the REAL default probe path: execute() with `probe=None`, the real sandbox (skipUnless darwin +
  sandbox-exec), StubAuth, and a stub command that answers the probe prompt with H2_REACHABLE and
  then acts as a worker; it must reach the worker and register;
- a stub harness exception before launch -> BLOCKED:HARNESS_DEFECT not registered; after launch ->
  INVALID:HARNESS_DEFECT registered;
- for each of the ten tasks: a real prepare's `git -C repo rev-parse HEAD` equals the expected HEAD
  stated in that task's rendered CONTRACT, and neither the original base nor the candidate sha
  appears in the CONTRACT or anywhere under the run dir;
- under the real sandbox with the frozen env, `zsh -c 'cat <<EOF ... EOF'` and the bash
  equivalent succeed inside the launch dir;
- preflight with a stub `opencode` on PATH records `service set port`, both debug calls and
  `service stop` in that order.

## T33 — re-pin and report (replaces CODEX_FIXES_7 T31)

Regenerate run plan / manifest / literals; append a T28–T33 section to CODEX_REPORT.md with the
evidence for each of F15–F25.
