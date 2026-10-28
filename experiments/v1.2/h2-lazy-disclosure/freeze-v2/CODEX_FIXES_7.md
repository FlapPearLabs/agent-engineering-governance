# Freeze v2 — independent review of 8585ba2: F15–F21 (fix plan T28–T31)

Implementer: opencode (deepseek-v4.1-flash). The ground rules, NEVER TOUCH list and GATES of
CODEX_PLAN.md §0 still bind every task; write scope unchanged.

Accepted at 8585ba2 (verified by Claude): every gate green; live pilot #3 executed end to end
(access PASS, scope OK, mechanical ACCEPT, real audit PARTIAL -> REJECT). The independent
DeepSeek-V4.1-Flash review (WorkBuddy, fresh clone at 8585ba2) returned CHANGES_REQUIRED. Claude
re-ran each attack below on a separate copy and every one reproduces. F21 is Claude's own.

## Findings

```text
F15 P1  ASSUME-UNCHANGED HIDES DENY EDITS AND DELETES (review P1-1). A worker runs
        `git update-index --assume-unchanged scripts/tests/<deny file>` and then edits or deletes
        that file: `git status`/`git diff <base>` show nothing, collect_v2 reports only the real
        fix, run_acceptance_v2 gives ACCEPT, and the auditor's diff.patch omits the change.
        The collector trusts state the worker controls (index flags, and by the same token
        skip-worktree, .gitattributes filters, repo-local config, refs/replace).
F16 P1  ACCESS AUDIT IS BYPASSED BY DYNAMIC PATHS (review P1-2). `cat $(printf '\057etc\057passwd')`,
        `echo <base64> | base64 -d | xargs cat`, `python3 -c "open(chr(47)+...)"` all read outside
        the run and the audit says PASS (0 hits). Static shell analysis cannot be complete; the
        audit must stop being the only barrier.
F17 P2  RETRY RULE RE-ROLLABLE / EVENT STREAM TAMPERABLE (review P2-1, widened). events.jsonl is
        written inside the run dir, the worker's own cwd. A worker that acted can delete it and exit
        non-zero -> classified PROVIDER_FAILED_BEFORE_WORK -> up to 3 re-rolls. Worse (Claude): the
        worker can rewrite it to drop tool_use lines, and the access audit reads that same file.
F18 P2  BASE COMMIT MESSAGE LEAKS THE CANDIDATE SHA (review P2-2). `git log` in repo/ prints
        "h2-admission: externalized oracle for <candidate sha>".
F19 P2  SHARED WORKER STATE ACROSS RUNS (Claude). Every worker and auditor uses the one profile
        ~/.h2-worker-profile: its opencode.db (15 MB) holds every earlier session (pilots,
        probes, and later the other arm's counted runs) and its config dir is writable, so a run can
        read another run's transcript or alter the config the next run gets.
F20 P3  Review P3-1 (run-root guard is $HOME-relative; broken-symlink markers missed), P3-2 (blocked
        audit probes not archived as §6.1 says), P3-3 (README lacks the run prerequisites: clear
        PYTHONPATH; interpreter with os.open in os.supports_dir_fd), P3-4 (no frozen program joins
        the registry into the §7 result; `status` reads "registered=20" as done).
F21 P3  (Claude) TMPDIR is inherited implicitly; a run's scratch goes to the shared OS temp dir.
```

## Measured facts for the design (Claude, 2026-10-23, opencode 2.0.25, macOS 26)

- `sandbox-exec -f <profile>` with `(allow default)`, `(deny file-read-data file-write* (subpath
  "/Users") (subpath "/private/tmp") (subpath "/private/var/folders"))`, then
  `(allow file-read-data (literal <each ancestor dir of the run dir>))` and
  `(allow file-read-data file-write* (subpath <run dir>) (subpath <per-run home>))` and
  `(allow file-read-data (subpath <interpreter prefix>))`:
  `cat`, `python -c open(...)` and `cat $(printf ...)` of governance / runs-root files all fail
  with EPERM; writes inside the run dir work.
- opencode needs `file-read-data` on each ANCESTOR directory as a `literal` (its config discovery
  calls realPath on them; without it: "PlatformError ... FileSystem.realPath" -> HTTP 500).
- With the master profile mounted read-only opencode fails ("Instruction initialization blocked
  by unavailable sources: core/instructions"). With a FRESH per-run HOME (only the frozen
  worker-profile/opencode.json in `.config/opencode/`, XDG_* under it, credential imported by
  `opencode auth export --standalone opencode | <fresh env> opencode auth import --standalone`)
  the reachability prompt answers H2_REACHABLE under the sandbox. The master profile is then not
  mounted at all.

## T28 — collection that trusts nothing the worker can write (F15, F18)

1. At prepare time the driver (outside any sandbox) records the base from the GOVERNANCE repo,
   never from repo/: `<runs_root>/.driver/<run_id>/base/` = `git archive <base>` extracted, and
   `base-manifest.json` = every path with mode, type (file/symlink) and blob sha.
2. collect_v2 computes changes by walking repo/'s working tree on the filesystem (excluding
   `.git/`) and comparing bytes, mode and type against the manifest: A / M / D / T. No `git status`,
   no index, no repo-local config, no attributes or filters decide what changed. A deny path with
   D or M or T is WORKER_SCOPE_DENIED exactly like today; deletions of base test files are denied.
3. The diff handed to acceptance and to the auditor is produced from `.driver/<run_id>/base/` vs
   the worktree bytes with `git diff --no-index --no-ext-diff --no-textconv` under
   `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, `-c core.attributesFile=/dev/null`,
   `GIT_NO_REPLACE_OBJECTS=1` (or an equivalent pure-Python diff). Same isolation for any other
   git call on repo/.
4. Check run_acceptance_v2: any oracle run must work on bytes copied from the worktree, never on a
   checkout through repo/.git; if it already does, say so in the report.
5. F18: `standalone_repository` leaves HEAD at a NEW commit with B's tree, fixed neutral message
   `h2 task base`, fixed author/committer name, email and date (deterministic sha); the original
   commit is not fetched into repo/ at all (`commit-tree` in the governance repo under a private
   ref, fetch that, delete the ref). The receipt records `base_sha` (original) and
   `delivered_head`; verify_standalone checks tree(delivered_head) == tree(base) and that
   `git log --all` in repo/ contains no 40-hex string of the candidate or the base.
Tests: the review's assume-unchanged edit and delete attacks, skip-worktree, a `.gitattributes`
filter, a repo-local `diff.external` and a `refs/replace` object each end REJECT
WORKER_SCOPE_DENIED (or TASK_REPOSITORY_UNREADABLE fail-closed) with the change visible in
collected changes and diff; positive controls f01-f03 still ACCEPT; `git log --all` shows only the
neutral commit.

## T29 — OS confinement, fresh per-run state, driver-held streams (F16, F17, F19, F21)

1. Frozen sandbox template `worker-sandbox.sb.template` (hashed in the manifest) rendered per
   launch with: the launch directory (run dir for the worker, audit dir for the auditor) rw; the
   per-run home rw; the interpreter prefix ro; each ancestor directory of the launch directory as
   a `literal` ro; everything else under /Users, /private/tmp and /private/var/folders denied for
   file-read-data and file-write*. Rendered profile saved and hashed per attempt.
2. Fresh per-run home `<runs_root>/.driver/<run_id>/home-<attempt>` (and `audit-home-<n>` for the
   auditor; also one for each reachability check), mode 0700: only the frozen
   worker-profile/opencode.json, XDG_* inside it, TMPDIR = `<launch dir>/.tmp`, credential imported
   by piping `opencode auth export --standalone opencode` (master profile env) into
   `opencode auth import --standalone` (fresh env). The secret never touches argv, logs, events,
   the registry or stdout. After the attempt: `opencode auth logout` in that home (best effort,
   recorded). The master profile is never mounted in the sandbox.
3. Worker, auditor AND reachability check are all launched as `sandbox-exec -f <rendered> <the
   frozen command>` with that env (PATH, LANG, the fresh-home exports, PYTHONDONTWRITEBYTECODE=1,
   TMPDIR). The reachability check therefore proves the real launch path.
4. Confinement self-test before every launch (no model): inside the same rendered sandbox, `cat`
   and `<PY> -c open(...)` of a driver-planted file under `.driver/<run_id>/` must fail and a
   write inside the launch dir must succeed. Otherwise BLOCKED:SANDBOX_NOT_CONFINING (no attempt
   consumed, re-invokable, recorded). No sandbox-exec on the platform => BLOCKED:SANDBOX_UNAVAILABLE.
5. stdout/stderr of every launch go to `<runs_root>/.driver/<run_id>/attempt-<n>/` (outside the
   sandbox's writable set). Every verdict input (before-work rule, tool-call count, access audit,
   telemetry) reads ONLY that copy; a copy may be placed in the run dir afterwards for humans.
   A missing or unreadable driver copy => INVALID:EVIDENCE_MISSING, never a retry.
6. Access audit keeps every existing rule and verdict (static out-of-run paths still INVALID). It
   adds evidence fields: `unresolved_constructs` (command substitution, backticks, eval, `-c`
   programs, base64/xxd decoding, xargs) and `sandbox_denied` (tool results containing
   "Operation not permitted" for a path outside the launch dir). Pre-register in protocol §4: the
   sandbox is the enforcing barrier; a denied dynamic attempt obtained nothing and is reported
   per run in the closure report, not INVALID; a static hit stays INVALID (no rule relaxed).
7. isolation_canary preflight runs against the fresh home (not the master profile) and still
   requires 0 mcp / 0 plugin agents / skills = opencode,report.
8. protocol-v2 §4–§6 and README record F15–F21, the sandbox, the fresh home, the driver-held
   streams, and that directory NAMES of ancestors remain listable (contents are not) — disclosed.
Tests (stub worker, never a model; sandbox tests `skipUnless` darwin + sandbox-exec, with the
driver fail-closed elsewhere): the three dynamic reads of a planted outside file fail inside the
sandbox; a stub that deletes or rewrites run_dir/events.jsonl after a tool call gets INVALID with
its tool call counted from the driver copy, no retry; a stub that reads the planted file via
`python -c` is denied and recorded in `sandbox_denied`; fresh home contains no other run's data;
the rendered profile and its hash are archived.

## T30 — P3 items (F20)

1. run_root_reason: refuse a run root under Path.home() OR under any home directory in the OS user
   database (`pwd.getpwall()`, excluding the shared users folder, `/var/empty`, `/dev/null` and other
   non-directories), independent of the process HOME; ancestor markers tested with
   `os.path.lexists` (a broken symlink counts).
2. A blocked audit reachability or confinement check writes `<run_id>/attempts/audit-<n>/probe.json`
   as §6.1 says.
3. README §5 "Run prerequisites": empty PYTHONPATH (a host sitecustomize can pre-import stdlib
   modules and mask the F1 shadow test); an interpreter where `os.open in os.supports_dir_fd`
   (scripts/tests/test_skill_execution.py needs it); macOS with sandbox-exec.
4. Frozen `aggregate_runs.py`: reads registry-v2.jsonl + attempts-v2.jsonl + the per-run verdict
   files of one runs root and outputs, per arm and per task, the valid pairs, the INVALID/BLOCKED
   lists with reasons, and the protocol §7 result (DISCLOSURE_SAFE / DISCLOSURE_HAS_COST /
   INSUFFICIENT_EVIDENCE) with the exact rule that decided it, including the null-difference
   rule. Fields it cannot decide mechanically (audited finding identity) come only from the audit
   verdict files; if any are missing the result is INSUFFICIENT_EVIDENCE with that reason.
   `run_h2r2.py status` additionally prints `usable_pairs` and `blocked`/`invalid` counts.
Tests: run-root under a user home with a fake HOME is still refused; broken `.agents` symlink
refused; aggregate on synthetic registries gives each of the three results and INSUFFICIENT on a
missing pair.

## T31 — re-pin and report

Regenerate run plan / manifest / literals; append a T28–T31 section to CODEX_REPORT.md with the
evidence for each finding.

## Notes for the implementer

- The public-release gate rejects any concrete `/Users/<name>` or `/home/<name>` string (including
  the shared users folder) and the host package prefix with a trailing slash. Write such paths in
  code by composition (e.g. `Path("/Users") / "Shared"`) or derive them at run time; the sandbox
  template may name `/Users`, `/private/tmp` and `/private/var/folders` (they do not match).
- Never print, log or commit a credential; tests use a fake `auth export` stub.
