# Freeze v2 — independent review of 9f8699d: F31–F41 (fix plan T38a, T38b, T39) — LAST ROUND

Implementer: opencode (deepseek-v4.1-flash via the implementation launcher). Ground rules and NEVER
TOUCH list of CODEX_PLAN.md §0 bind; write scope unchanged. User rule (2026-10-23): this is the last
review round; P3 findings are recorded as known, not reopened. T38a and T38b run in parallel on two
branches with disjoint source files; T39 merges, re-pins and runs the full gates once.

Accepted at 9f8699d (Claude): independent parallel gates all pass (11 experiment modules / 457
tests, scripts 602, ruff, governance 35/35, public release 0, manifest PASS); live pilot #7 ran end
to end under sandbox + egress allowlist (mech ACCEPT, access PASS 0/49, real audit PARTIAL -> REJECT).

The independent review of 9f8699d (Claude Sonnet subagent, same brief; WorkBuddy could not be driven)
returned CHANGES_REQUIRED, P1=4 P2=9 P3=8. Claude re-ran the reproductions: P1-1 (sandbox wrote into
the host package bin dir, /Applications, /Library/Caches, /private/var/tmp), P1-2 (acceptance executed
worker code unsandboxed and it read a secret planted outside the run), P1-3 (a detached survivor
replaced the oracle mid-acceptance -> ACCEPT with zero recorded changes), P1-4/P2-5/P2-6/P2-7
(synthetic aggregates: mechanical REJECT + id-only audit noise -> DISCLOSURE_SAFE; an observed cost
masked by another task's INVALID run), P2-1 (a sandboxed `kill` terminated an outside process) all
reproduce. Report: the reviewer's REVIEW_REPORT.md (paths and repro scripts are local, not committed).

## Findings (review id -> F number)

```text
F31 P1 (P1-1) Sandbox writes are a deny-list on top of (allow default): system dirs on the operator
       PATH stay writable, so a planted binary can later run unsandboxed in the driver.
F32 P1 (P1-2) Acceptance (oracle + full suite via delivery_anchors.run_gate) and any other execution
       of worker-written code runs in the driver's own unsandboxed process.
F33 P1 (P1-3) No process sweep after a launch: a detached survivor keeps sandbox write access to the
       run dir and can change files between collection, hashing and the gate run.
F34 P1 (P1-4) aggregate_runs compares only audit correctness; the mechanical verdict never enters
       FINAL_CORRECTNESS / invalid completion.
F35 P2 (P2-1) No signal confinement (sandbox can kill driver, scheduler, other runs).
F36 P2 (P2-2) Unix-socket egress and DNS resolution are open.
F37 P2 (P2-3) One unreadable file in the run dir makes every registration path raise -> run wedged.
F38 P2 (P2-4) CONTRACT.md is read back from the worker-writable run dir into the audit bundle.
F39 P2 (P2-5) decide(): coverage/S1 checks run before S2/S3/S4, so an observed cost is masked.
F40 P2 (P2-6, P2-7, P2-8) Null difference compares free-text finding ids; S2 is mechanically
       unreachable but not pending; audit files are not checked against the registered hashes.
F41 P2 (P2-9) base_sha and case_id are projected into the auditor's blind bundle.
P3-7 (fixed here, cheap): preparing the next attempt wipes the previous attempt's evidence dir.
Known P3, recorded not fixed: P3-1 (TMPDIR spelling in the test command), P3-2/P3-3 (the fresh home
holds the imported credential the worker could read and use for extra calls to the allowlisted
provider), P3-4 (.git/ internals outside the collected delta; no oracle depends on them), P3-5
(closed by F35), P3-6 (worker-started flag set one step early), P3-8 (some system read paths open).
```

## Measured facts (Claude, live, opencode 2.0.25 under sandbox-exec)

This profile kept opencode fully working (model reachable through the allowlist proxy, shell tool,
zsh heredoc) while: writes to the host package bin dir and /Applications fail; a write in the run dir works;
`kill` of an outside process fails (EPERM) but killing the sandbox's own child works; DNS resolution
fails; connecting to /var/run/mDNSResponder fails:

    (version 1)
    (allow default)
    (deny file-read-data file-write* (subpath "/Users") (subpath "/private/tmp") (subpath "/private/var/folders"))
    (allow file-read-data (literal <each ancestor of the launch dir>))
    (allow file-read-data file-write* (subpath <launch dir>) (subpath <fresh home>))
    (allow file-read-data (subpath <interpreter prefix>))
    (deny file-write* (subpath "/"))
    (allow file-write* (subpath <launch dir>) (subpath <fresh home>) (literal "/dev/null")
                       (literal "/dev/tty") (subpath "/dev/fd") (regex #"^/dev/ttys[0-9]+$"))
    (deny network-outbound)
    (allow network-outbound (remote ip "localhost:<proxy>") (remote ip "localhost:<serve port>"))
    (deny network-bind)
    (allow network-bind (local ip "localhost:<serve port>"))
    (deny signal)
    (allow signal (target same-sandbox))
    (deny mach-lookup (global-name "com.apple.dnssd.service"))

(No `(allow network-outbound (remote unix-socket))` line: opencode did not need it.)

## T38a — confinement of every execution of worker code (F31, F32, F33, F35, F36, F37, F38, F41, P3-7)
Main branch. Files: sandbox_v2.py, worker-sandbox.sb.template, run_h2r2.py, run_acceptance_v2.py,
delivery_anchors.py (run_gate), collect_v2.py, run_audit_v2.py, egress_v2.py if needed. Do NOT
touch aggregate_runs.py.

1. F31/F35/F36: the template becomes the measured profile above (write whitelist, signal, unix
   socket by omission, DNS). The confinement self-test adds: a write outside the launch dir (e.g. a
   system dir) fails; a signal to an outside process fails; DNS resolution fails. Driver-side tool
   invocations use absolute paths resolved once at startup (git, sandbox-exec, opencode, python),
   never a PATH lookup after a launch.
2. F33 snapshot: immediately after a worker launch ends (normal exit, error or timeout) the driver
   (a) kills the launch's process group AND every remaining process whose cwd or open files are
   under the launch dir (`lsof +D` / equivalent; record each pid and command in
   `.driver/<run_id>/attempt-<n>/sweep.json`), then (b) copies the run dir (repo/, report,
   telemetry, delivered files) into `.driver/<run_id>/attempt-<n>/snapshot/` — a path the sandbox
   cannot write — and records its sha256 manifest. Collection, scope, oracle hashing, the gate runs
   and the audit bundle all use ONLY the snapshot. A process found by the sweep is recorded as
   evidence (`lingering_processes`), never silently ignored.
3. F32: every execution of worker-written code during acceptance (the oracle in both temp-root
   spellings and the full suite) runs inside a rendered sandbox: launch dir = a fresh per-gate copy
   of the snapshot under `.driver/<run_id>/attempt-<n>/gate-<k>/`, NO network at all (no proxy, no
   loopback), writes only in that copy, and the two temp-root spellings are provided INSIDE it
   (a real dir and a symlink to it, so RESOLVED vs SYMLINKED still differ). Same confinement for
   any other worker-code execution you find (search for subprocess calls on repo/).
4. F37: artifact_hashes records an unreadable file as `{"path": ..., "unreadable": true}` instead of
   raising; every registration path stays total; an unreadable file in the snapshot makes the run
   INVALID:EVIDENCE_UNREADABLE (registered).
5. F38: the driver keeps the rendered CONTRACT bytes in `.driver/<run_id>/CONTRACT.md` with its
   sha256; the audit bundle is built from that copy; a run-dir CONTRACT.md that differs is recorded
   (`CONTRACT_TAMPERED`) and makes the run INVALID.
6. F41: the auditor bundle's verdict projection drops `base_sha` and `case_id` (they stay in the
   driver-side records); fix protocol/README wording to match what is actually where.
7. P3-7: preparing a new attempt archives (never deletes) the previous attempt's evidence dir.
Tests (no model): the reviewer's attacks as tests — a sandboxed write into a system dir fails; a
sandboxed signal to an outside process fails; DNS fails in the sandbox; a detached survivor that
rewrites the oracle after the worker exits is killed and/or cannot affect the verdict (verdict and
collected changes come from the snapshot; the survivor appears in sweep.json); worker code appended
to an imported module runs inside the gate sandbox and cannot read a planted outside file nor write
outside its gate copy; an unreadable run-dir file registers INVALID:EVIDENCE_UNREADABLE; a tampered
run-dir CONTRACT.md is detected; the auditor bundle has no base_sha/case_id; RESOLVED vs SYMLINKED
oracle runs still see different spellings inside the gate sandbox.
Gate: speed rule (ruff, governance, public release, the freeze-v2 test module only; no re-pin).

## T38b — aggregate_runs.py (F34, F39, F40) — branch experiment/v1.2-h2-freeze-v2-par
Touch ONLY aggregate_runs.py, its tests (own class) and the protocol/README lines describing it.
1. F34: per run, FINAL_CORRECTNESS = the stricter of the mechanical verdict (ACCEPT -> PASS ceiling;
   REJECT -> FAIL; INVALID/BLOCKED -> not usable) and the audit correctness; invalid completion is
   true when the worker report claims completion and the mechanical verdict is REJECT, or as the
   audit records.
2. F39: evaluate S2/S3/S4 on every COMPLETE usable pair first; any hit -> DISCLOSURE_HAS_COST with
   the rule and pair named, regardless of coverage elsewhere. Coverage gaps, missing audits, S1 and
   pending rules can only turn a would-be SAFE into INSUFFICIENT_EVIDENCE, never mask a cost.
3. F40: null difference compares only structured fields per pair: FINAL_CORRECTNESS, invalid
   completion, and the multiset of (severity, category) of findings — never free-text ids, text or
   locations. S2 (missed guidance, needs an arm-aware judgement) and S5 are listed in
   `pending_rules`; while any rule is pending the mechanical aggregate's best possible output is
   `SAFE_CANDIDATE_PENDING:<rules>` (to be decided in the closure report), never DISCLOSURE_SAFE.
   Before reading any run's audit/verdict files, check them against the sha256 recorded in that
   run's registry line; a mismatch makes that run's evidence untrusted -> INSUFFICIENT_EVIDENCE
   naming the run.
Tests (synthetic registries): the reviewer's L1b, L2, L2b, L3, L5, l6 scenarios give HAS_COST /
HAS_COST / HAS_COST / INSUFFICIENT_EVIDENCE / SAFE_CANDIDATE_PENDING / INSUFFICIENT_EVIDENCE
respectively (derive exact expectations from the rules above and state them in the test names).
Gate: speed rule (no re-pin).

## T39 — merge, re-pin, full gates, report
Merge refs/heads/experiment/v1.2-h2-freeze-v2-par (T38b) into the main branch keeping both sides;
regenerate run plan / manifest / anchors / literals with the build programs; append a T38–T39
section (F31–F41) to CODEX_REPORT.md; run ALL gates once; commit only if all pass.
