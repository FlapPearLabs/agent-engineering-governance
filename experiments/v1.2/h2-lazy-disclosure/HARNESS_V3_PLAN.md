# Harness v3 — hardening the H2 harness for the next counted rounds (plan T50–T54)

Owner decision (user, 2026-10-28): harden the harness first ("目标是让 run 的有效率接近 100%"),
implementers Codex (gpt-6.1-terra) and opencode (deepseek-v4.1-flash) in parallel, Claude accepts,
Codex (gpt-6.1-sol) reviews. The user also asked to consider Anthropic's open-source sandbox
(sandbox-runtime, `srt`).

## Why

H2-R2 (freeze 4aa2e7b, merged in PR #56) ended INSUFFICIENT_EVIDENCE with only 5/10 valid pairs.
All five INVALID runs had passed mechanical acceptance; the invalidations and stalls came from the
harness: an audit allow-list that missed the interpreter's standard library, a classifier that
treated a nonexistent path as a possible success, opencode's `execute` tool unknown to the audit,
a worker `cd ..` that could enter the shared runs root, a named pipe that hung registration, and no
entry to re-run a blocked audit. The post-freeze review of 4aa2e7b (partial) also found that the
driver's snapshot copy follows a worker-planted symlink and can overwrite a file outside the
sandbox — an operator-safety defect.

## Ground rules

- `freeze-v2/` is the provenance of the H2-R2 results and is NEVER modified. v3 lives in
  `experiments/v1.2/h2-lazy-disclosure/freeze-v3/` with its own test module
  `experiments/v1.2/tests/test_v1_2_h2_freeze_v3.py`, its own manifest and materials pins.
- Gates as in freeze-v2's CODEX_PLAN §0; NEVER TOUCH: canonical files, scripts/, references/,
  schemas/, templates/, .github/, freeze-v2/, results-v2/.
- No model calls in tests; no runs against real runs roots by implementers.

## Measured facts (Claude, 2026-10-28, srt 0.0.81, opencode 2.0.25)

- srt's write allowlist, read deny-then-allow, domain allowlist (resolved-address check, loopback
  denied) and unix-socket blocking all work; denials are visible in the macOS unified log
  (`log show --predicate 'subsystem == "com.apple.sandbox.reporting"'`).
- srt forces `TMPDIR=/tmp/claude`, a directory writable by default and shared by every srt sandbox
  on the machine; it must be denied and TMPDIR overridden inside the sandbox.
- opencode (`run --standalone`) needs `network-bind local:*:0` and file-read-data on every ancestor
  of its working directory. In srt the only way to allow the bind on macOS is
  `allowLocalBinding: true`, which also allows connecting to ANY loopback port: from inside such a
  sandbox a raw TCP connection to the operator's local HTTP proxy port on loopback succeeded and
  `CONNECT github.com:443` returned `200 Connection established` — a full bypass of the domain
  allowlist. Decision: keep freeze-v2's per-port loopback profile (proxy port + per-launch serve
  port only) for opencode launches; adopt from srt (a) the read ALLOWLIST approach and (b) the
  sandbox violation log as empirical evidence.

## T50 — fork (Codex terra; must land first)

Copy `freeze-v2/` to `freeze-v3/` and `test_v1_2_h2_freeze_v2.py` to `test_v1_2_h2_freeze_v3.py`;
rename every self-reference (paths, manifest, materials pins, run ids prefix `h2r3-`, registry and
run-plan file names `*-v3`); regenerate run plan / manifest / anchors with the build programs; both
the v2 and the v3 test modules pass; `freeze-v2/build_manifest.py check` still PASS. One commit.

## T51 — driver and sandbox (Codex terra; after T50; files: freeze-v3/run_h2r2.py, sandbox_v2.py →
sandbox profile code, worker-sandbox.sb.template, wrapper_delivery.py, collect_v2.py)

1. Snapshot and every driver-side copy/hash: never follow symlinks (lstat; copy a symlink as a
   symlink; open regular files with O_NOFOLLOW); never open FIFOs, sockets or devices (record type).
   Registration hashing likewise. Tests: a worker-planted symlink to an outside file is copied as a
   link and the outside file is untouched; a FIFO in the run dir never blocks registration.
2. Cell layout: each run lives in its own private parent: `<runs_root>/.cells/<run_id>/<run_id>/`,
   so `cd ..` from the run dir lands in a directory that holds only that run (and is inside the
   run's allowed surface). The sandbox literal ancestors stop at the runs root.
3. Read allowlist: the profile denies file-read-data under `/` and re-allows only: the launch dir
   and its cell, the fresh home, the interpreter's real install prefix (resolved: sys.base_prefix
   and the stdlib dir of the pinned interpreter), the opencode install, the system paths opencode,
   git, zsh and python need (measure them with the violation log and list them as frozen
   constants), and literal ancestors for realPath. Writes stay a whitelist; signal, DNS and
   unix-socket rules stay.
4. Violation evidence: for each confined launch, collect the sandbox violation lines from the
   unified log for that launch's time window and process tree into `.driver/<run>/attempt-<n>/
   violations.jsonl`; expose them to the access audit.
5. Audit retry entry: `run_h2r2.py audit --runs-root R <run_id>` for a run registered BLOCKED only
   because its audit was blocked: runs a fresh audit attempt (same rules, same model, own counter),
   appends an `AUDIT_RESOLVED` line to the registry (never edits the old line); aggregate uses the
   latest resolution. Pre-register in protocol-v3 §6.1.
Tests (stubs; real sandbox-exec where needed): each item above.

## T52 — access audit (opencode; after T50; files: freeze-v3/access_audit.py and its tests only)

1. System allow-list includes the interpreter's real install prefix and stdlib (resolved the same
   way as T51.3), not only sys.prefix of the driver.
2. POSSIBLE_SUCCESS only when the access could actually have succeeded: a read of a path that does
   not exist (checked against the run's snapshot and the filesystem after the launch) or a write
   outside the sandbox write whitelist is DENIED_BY_POLICY/evidence; use T51.4 violations as the
   empirical confirmation when present.
3. URL parsing strips `user:pass@` before extracting the host (review finding 3).
4. SANDBOX_BREACH only for tool output that is file CONTENT of a denied path (a read/cat result),
   never for search listings or messages that merely mention a path (review finding 4).
5. Replay every real stream of H2-R2 (20 counted runs, read-only) and of all pilots through the v3
   audit and commit the replay summary as a test fixture expectation: which runs v3 would classify
   VALID vs INVALID and why (this is a harness measurement, NOT a re-scoring of H2-R2).

## T53 — worker tool surface (opencode; after T50; files: freeze-v3/worker-profile/*,
freeze-v3/isolation_canary.py and their tests)

Disable opencode's `execute` tool for workers and auditors in the frozen worker config (both arms
identically), verified by the canary (the tool is absent from the session's tool list); if the
config cannot disable it, add it to TOOL_ALLOW with an explicit audit rule (its `code` input is an
unresolved construct: evidence, not INVALID) and say which path was taken and why.

## T54 — merge, re-pin, full gates; then review and a 10-task pilot batch

Merge T51–T53, re-pin freeze-v3, all gates. Then: independent review (Codex gpt-6.1-sol, neutral
brief), and a live 10-task pilot batch (one arm each, `run-plan` with the scheduler stopped after
ten starts) whose valid-run rate is the acceptance measure for "close to 100%".
