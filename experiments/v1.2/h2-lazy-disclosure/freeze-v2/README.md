# Freeze v2 — pinned candidate materials (acceptance pending)

Inputs: the 10-task shortlist `admission/freeze-v2-input/shortlist.json` (validator 2.8.12).

## 1. Route preconditions (protocol §10, FZ-ADM-4) — `route_preconditions.py`

```text
from the REPOSITORY ROOT, H=experiments/v1.2/h2-lazy-disclosure (any other root is refused):
$H/freeze-v2/route_preconditions.py . $H/admission/freeze-v2-input/shortlist.json \
    --out $H/freeze-v2/route-preconditions.json
ROUTES_ADMISSIBLE 10/10. r44, r50 bases: 33/33 valid. The other 8 bases: 31/33, failing only
LEAN-12 and AGENTS-03 (references/static-tooling-profiles.md not yet in history) — S1/S2 rows no
task touches -> HISTORICAL_BASE_ROUTE_UNSATISFIED, the class P6 already recorded for 015780b.
No S3 (H2 carrier) row fails anywhere.
```

## 2. Delivery anchors (schema §6.4, FZ-ADM-3) — `delivery_anchors.py`

```text
from the REPOSITORY ROOT:
$H/freeze-v2/delivery_anchors.py . $H/admission/freeze-v2-input/shortlist.json \
    --materials <commit> --out $H/freeze-v2/delivery-anchors.json
    (T2 recorded 1dbcf3f; re-measured at each later materials set — every row identical except the
     recorded commit, so the PRE/POST numbers below are the same measurement. T21/F8 re-measured
     again at 20719b56 with the repository shape changed from a linked worktree to a standalone
     history-free repository; every PRE set, every `ran` count and every POST cell came back
     identical, so the numbers below still hold and nothing was carried over. T28/F18 re-measured
     it again at 4924930 with a neutral parentless delivered head: the program hash moved, every
     row came back byte-identical again, still WRAPPER 10/10)
Gates: the task oracle and the full scripts/tests suite, PRE vs POST delivery, zero worker edits,
compared by the SET of non-passing test ids (not exit codes: every A_REPAIR oracle is red at its
base, and round 1's t01 went 1 -> 4 failures without changing rc).

RESULT  neutral tasks: CODEBUDDY slot 0/10, AGENTS slot 0/10, WRAPPER slot 10/10.
  oracle      newly-not-passing ids in 4/20 CODEBUDDY cells, 7/20 AGENTS cells, 0/20 WRAPPER
              cells. No newly-passing ids in any slot. Every cell has ran_delta = 0.
  full suite  newly-not-passing ids in all 20 CODEBUDDY and all 20 AGENTS cells, in BOTH arms:
              the repository's single-declaration scans
              (test_seam_contract_partitions, test_p1_t10/t11/t12 "declared exactly once") read
              every non-test text file under the root, so the in-tree copies — H2_WARM/ reference
              copies and a carrier that restates AGENTS.md — become second declaration points.
              Replacing AGENTS.md (AGENTS slot) additionally breaks the tests that read AGENTS.md
              (test_ticket_gate_wiring, test_p1_t09 section-ten checks).
  WRAPPER     every oracle and full-suite PRE/POST pair has identical non-passing sets and
              return codes, ran_delta = 0, no newly-passing or newly-not-passing id (20/20 cells).
              Skip, expected-failure and unexpected-success statuses count as non-passing;
              none occurs in this measurement.
  PRE sets    non-passing ids per task 4, 3, 8, 9, 9, 2, 8, 1, 2, 5; suite sizes
              78, 96, 122, 178, 231, 274, 301, 423, 519, 598.
```

T21/F8 changed the shape of PRE: it is now the same standalone, history-free repository the worker
gets (§3 LAYOUT), not a full-history worktree. A test that depended on git history would therefore
fail PRE and POST alike and be recorded as such; the full re-measurement found none. The JSON also
records `repository`, `wrapper_program_sha256` (the program that produced the measurement) and
`shortlist_sha256`; `build_manifest.py` binds those two hashes, and the delivered payload is
verified byte-equal at the recorded materials and at HEAD.

Consequence: under §6.4 no shortlisted task is admissible with IN-TREE delivery, in either slot;
all 10 are delivery-neutral with the WRAPPER layout in §3.
This is the round-1 t01 contamination mechanism, now measured on every base. It is attributed to
the experiment's delivery, not to the tasks, and is recorded rather than normalised (§4.6).
The wrapper keeps the carrier and WARM bundle outside the repository root. The isolated runtime
canary remains a separate, pending acceptance check; delivery neutrality alone does not prove
startup guidance isolation.

## 3. Worker runtime and delivery layout (operator decision 2026-10-19)

```text
RUNTIME   opencode (CLI 2.0.25), model opencode-go/deepseek-v4.1-flash, in an ISOLATED profile
          (HOME and XDG_* redirected to a dedicated profile directory outside every repository:
          no user plugins, MCP servers, skills, memory or global AGENTS.md; autoupdate off;
          `run --standalone`, so no shared background service). The profile is logged in once
          by the operator; credentials never enter this repository.
PROFILE   the profile config is a FROZEN INPUT (F6). The operator installs
          `freeze-v2/worker-profile/opencode.json` as the profile's
          `~/.config/opencode/opencode.json`, byte for byte (no reformatting): `$schema`,
          autoupdate off, `share: "disabled"`, empty `plugin` and `mcp`, and
          `permission.question = "deny"`. WHY: the resolved `build` agent allows the `question`
          tool, and a non-interactive `opencode run` that calls it waits forever with no output.
          Before EVERY run, `isolation_canary.py preflight <run_dir> --profile-env <env.sh>`
          must PASS: it runs only `opencode debug paths` and `opencode debug config`, and
          requires every printed state path to be under the profile home, the config sources to
          be exactly the profile `opencode.json` and its directory, and that file's bytes to
          equal the frozen template. The verdict stays in `<run_dir>/preflight.json`.
LIMIT     one run may not exceed 90 minutes of wall clock. Past that it is registered INVALID
          per protocol §8 (RUN_ID, ARM, TASK_ID, reason, discovery time, artifact location) and
          never silently re-run; a timeout is neither a worker failure nor a pass.
ACCESS    after the worker exits, `access_audit.py` replays `events.jsonl`: every path argument,
          and every path-shaped token of a shell command (`shell` is this runtime's tool name;
          `bash` is accepted too), must resolve inside the run directory, except the frozen system
          allow-list (the pinned interpreter and its prefix, /usr, /bin, /opt/homebrew, /System,
          /Library/Developer, the OS temp roots, /dev/null). The command is tokenised with shell
          punctuation, so a separator is never glued to a path; every token, the value of a
          `NAME=value` assignment included, resolves against the working directory the same
          command established with a preceding `cd` (F27b), so `cd repo && T=../.tmp/probe` is
          `<run>/.tmp/probe` and inside. Shell `git` invocations that reach another repository
          (`push`, `ls-remote`, `submodule`, `remote add|set-url|…`) and any tool outside the
          frozen allow-list are hits as well; `clone` / `fetch` / `pull` are judged by their SOURCE
          (F27a): a local path that resolves, after any `cd`/`-C`, inside the run directory is the
          run's own repository and is not an escape, while a URL, an scp `host:path` form, a path
          outside the run directory or no source at all stays a hit. A git command's EFFECTIVE
          repository — after a `cd` in the same command and after its own
          `-C` / `--git-dir` / `--work-tree` — is foreign only when it resolves outside the run
          directory AND outside the OS temp roots (archiving the base into a temp directory and
          running git and tests there is legitimate work; another program's `-C`, such as
          `tar -x -C`, is not git's). Any hit makes the run INVALID:OUT_OF_RUN_ACCESS —
          registered, never re-run (protocol-v2 §6) — and the audit verdict keeps every hit
          verbatim. No rule is relaxed by the sandbox below: the audit also records two evidence
          fields that never change a verdict — `unresolved_constructs` (command substitution,
          backticks, eval, `-c` programs, decoders, xargs: paths a static tokenizer cannot see) and
          `sandbox_denied` (a tool result whose DENIAL LINE says "Operation not permitted" AND
          names a path outside the launch directory; a document that merely contains the phrase is
          not a denial, F29). A denied dynamic attempt obtained nothing: it is reported per run in
          the closure report, not turned into INVALID (F16 / protocol-v2 §4.0).
SANDBOX   static auditing cannot be complete, so the OS sandbox is the enforcing barrier
          (F16 / T29). Every launch — worker, per-run auditor and each reachability check — is
          `sandbox-exec -f <rendered profile> <the frozen command>`. The frozen template
          `worker-sandbox.sb.template` re-allows exactly the launch surface: the launch directory
          (run dir for the worker, audit dir for the auditor) and the fresh per-launch home
          read-write, the interpreter prefix read-only, each ANCESTOR of the launch directory as a
          read-only `literal`; every other path under /Users, /private/tmp and /private/var/folders
          is denied for file-read-data and file-write*. The rendered profile and its sha256 are
          archived per attempt. Before each launch a model-free self-test must deny `cat` and
          `<PY> -c open(...)` of a driver-planted file and allow a write inside the launch
          directory; otherwise BLOCKED:SANDBOX_NOT_CONFINING (no attempt consumed, the same run id
          may be invoked again, recorded). No sandbox-exec on the platform =>
          BLOCKED:SANDBOX_UNAVAILABLE. DISCLOSED: the NAMES of ancestor directories stay listable
          (a `literal` allows the directory node itself); their contents are not readable.
FRESH HOME every launch gets a brand-new `<runs_root>/.driver/<run_id>/home-<n>` (auditor:
          `audit-home-<n>`, reachability: `probe-home-<purpose>-<n>`), mode 0700, holding only the
          frozen `worker-profile/opencode.json` and its own XDG_* directories; TMPDIR is
          `<launch dir>/.tmp`, so scratch never lands in the shared OS temp dir (F19 / F21). The
          credential is piped from the master profile (`opencode auth export --standalone opencode`
          into `opencode auth import --standalone`) and never touches argv, a log, the event
          stream, the registry or stdout; `opencode auth logout` runs in that home afterwards (best
          effort, recorded). The master profile is never mounted in the sandbox, and preflight
          attests the fresh home rather than the master profile.
STREAMS   stdout/stderr of every launch are written under `<runs_root>/.driver/<run_id>/`, outside
          the sandbox's writable set (F17). The before-work rule, the tool-call count, the access
          audit and telemetry read ONLY that copy; a copy may be placed in the run dir afterwards
          for humans. A missing or unreadable driver copy is INVALID:EVIDENCE_MISSING, never a
          retry.
ENV       the worker and the per-run auditor run with a minimal base env (PATH, LANG), the profile
          env file's `export` lines and the frozen `PYTHONDONTWRITEBYTECODE=1`, applied last so the
          profile cannot override it (F11). WHY: running the oracle and the full suite as the
          contract instructs writes `__pycache__/*.pyc` under `repo/`, which the `scripts/tests/`
          prefix rule and the validator's BYTECODE rule rightly refuse — the cause is fixed, not
          the rule. A `.pyc` that still appears under `repo/` stays a scope refusal.
RUNS_ROOT H2_RUNS_ROOT = `<SHARED_RUN_ROOT>`: an operator directory in the macOS Shared folder,
          outside every home and every git repository, with NO ancestor carrying `.agents`,
          `.opencode`, `.claude`, `AGENTS.md`, `CLAUDE.md` or `opencode.json`.
          WHY (F4): opencode discovers `.agents/` and `.opencode/` by walking UP from the cwd, past
          the redirected HOME. A run root below the operator's home re-admitted ~185 user skills;
          with the root outside every home only the two built-in skills `opencode` and `report`
          appear, identically in both arms. `prepare` refuses a run root that is under ANY home the
          OS user database declares (`pwd.getpwall()`, the shared users folder excluded) or below
          any such ancestor — including a BROKEN symlink named `.agents` or `.opencode`, which a
          runtime walking up from the cwd would still discover (F20).
LAYOUT    <run>/                 worker cwd (not a git repository)
            AGENTS.md            the arm's carrier (control: header + AGENTS.md + footer;
                                 variant: carriers/H2_LEAN_BOOTSTRAP.md) — the ONLY guidance
                                 opencode loads at startup (canaries; re-checked in
                                 the isolated profile once it is logged in)
            H2_RULES.md          RULES.md at the materials commit
            H2_WARM/             the S3 WARM owners at the materials commit
            repo/                the task repository at the base: a STANDALONE repository whose
                                 object store is exactly B's TREE (T21/F8) — one parentless
                                 commit with the fixed neutral message `h2 task base`, fixed
                                 author/committer and date, no remote, no alternates, no
                                 reflog; detached HEAD is that neutral commit, whose tree
                                 equals B's (F18/T28). The original base commit is never
                                 fetched, so `git log --all` names neither B nor the
                                 candidate. NO delivered file inside it, so §2's in-tree
                                 contamination cannot occur, and no worker can read the
                                 historical candidate out of a shared object database
WHY       measured on 2026-10-19 with canary instruction files: opencode loads the cwd's
          AGENTS.md at startup; a repository's own AGENTS.md (and nested ones) are ATTACHED to
          the first read of a file beneath them; the user's normal profile also injects its
          global AGENTS.md, MCP servers and a plugin agent.
DISCLOSED CONFOUND  the task repository's own (base-era) AGENTS.md is attached to BOTH arms on
          the worker's first read inside repo/. Neither arm can be kept from it under this
          runtime. The arms therefore differ in the STARTUP carrier (full current-era HOT vs
          lean carrier + routed WARM), not in whether any full governance text is reachable.
          A null difference is reported as INSUFFICIENT_EVIDENCE, never as DISCLOSURE_SAFE on
          this ground alone.
```

## 4. What is frozen

[freeze-manifest.json](freeze-manifest.json) pins 51 files: the registry, run plan, brief,
protocol, runtime/measurement/generator modules, the run driver and the per-run auditor
(`run_h2r2.py`, `run_audit_v2.py`), the runs-root aggregate (`aggregate_runs.py`), the OS
confinement module and its frozen profile template
(`sandbox_v2.py`, `worker-sandbox.sb.template`), the per-run collector and acceptance
(`collect_v2.py`, `run_acceptance_v2.py`) with the scope rules (`scope_v2.py`), the out-of-run
access audit and its four event fixtures (`access_audit.py`: two hand-built shape fixtures plus
the two sanitised REAL streams the live pilot and the tool-name probe recorded, whose absolute
path prefixes are placeholders re-expanded by the tests), the frozen
worker-profile config (`worker-profile/opencode.json`, §3 PROFILE), the sanitised canary and
preflight fixtures, route measurements, admission inputs, routes, carrier bytes, report template,
rubric and validator. The same hashes are independent literals in
`experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py`; the manifest itself has a separate literal
hash there. Tests reject a one-byte mutation of each of these 52 files on a temporary copy.
README, the implementation plan, review log and CODEX_REPORT are operator documents outside
this byte freeze. The §3 confound must remain byte-equal to protocol-v2.md.

The content-freeze commit at this round is the T28 re-pin commit. The materials the run plan binds
— and therefore the freeze parent in [freeze-manifest.json](freeze-manifest.json) — remain
`4924930b71473efcb7f7fd84973d5574f873b03c` (the T26 commit). The delivered payload —
carrier bytes, `RULES.md`, the WARM bundle, routes and the shortlist — is byte-identical to the T8
materials `042f2244e453c79daa0ed50d72759a4583bcc43d`; what moved forward across rounds are
`wrapper_delivery.py` (T13's run-root refusal, then T21's standalone history-free task
repository, then T28's neutral delivered head and driver-recorded base snapshot), the
programs/fixtures the F1/F2 fixes added (T11/T12), the F5/F6 work (T15/T16: the
preflight attestation, its sanitised evidence fixtures and the frozen worker-profile template),
the F8/F9 work (T21/T22: the standalone repository and the out-of-run access audit with its two
shape fixtures), the F10–F13 work (T24: `shell` as the real tool name, shell-punctuation
tokenisation, the effective-git-repository rule, the frozen `PYTHONDONTWRITEBYTECODE=1` worker and
auditor environment, and the two sanitised REAL event streams that now pin those rules), the
F14 work (T26: the pre-registered provider-infrastructure rule in the run driver — the reachability
probe, the before-work retry with hashed attempt archives and the attempt ledger, and the auditor's
own counter; §5 and protocol-v2 §6.1), the F15/F18 work (T28: the collector now decides the
delta from the worktree's bytes against a driver-recorded base snapshot, and the delivered
repository head is a deterministic neutral commit), and the F16/F17/F19/F21 work (T29: every launch
runs under a rendered `sandbox-exec` profile with a model-free confinement self-test, in a fresh
per-launch home with its credential piped in and logged out again, with TMPDIR inside the launch
directory, and the driver's own stdout/stderr copy is the only evidence the verdict reads). The T2
delivery anchors were re-measured instead of being carried over; the last measurement is
[delivery-anchors.json](delivery-anchors.json), taken at `4924930` with the T28 program: every
PRE/POST cell, `ran` count and verdict is byte-identical to the T21 measurement at `20719b56`,
which was itself identical to the T17 measurement at `a5a0354` (same 10/10 WRAPPER neutrality,
same per-task PRE sets). T23, T25 and T27 did not re-measure it, because neither the delivered
payload nor the measuring program nor the shortlist moved at those commits; T28 did, because the
measuring program moved. The earlier measurement commits
`1dbcf3f2d3bc9ec0c230c36784db6adcc2a8713a` (T2), `fb9ce4f80286c8c365d66bd8c9ed7df985f7b7a9`
(T14) and `a5a03543d2ccbe4cfa727ffa0be0bf513a871a39` (T17) are kept in the record because the
PRE baseline itself did not move. The run plan is regenerated before hashing at every re-pin.
The measurement's provenance is bound by hash, not by commit identity: the JSON records
`wrapper_program_sha256` and `shortlist_sha256`, and `build_manifest.py` refuses a manifest whose
anchors were produced by a different program or a different shortlist. The final default-branch
merge remains the review/history anchor; hashes alone are not acceptance.

Registry scope interpretation (superseded by F1, CODEX_FIXES_1 T10): the earlier reading of “allow
everything else in repo/” reused round-2 n01/n02's empty deny-prefix list. That list let an added
`scripts/tests/json.py` shadow the stdlib import the frozen oracle resolves, so `deny_prefixes` is
now `scripts/tests/` for every task: no add, modify, delete or rename inside the directory
`unittest discover` imports from. Every base `scripts/tests/` file and each oracle stay
individually denied, the worker contract prohibits changing any test, and every added or renamed
path is held to the validator's `shadow_paths` rule plus the startup-hook refusal (protocol-v2 §7).
The re-pin definition (materials = parent of the re-pin commit, proven byte-equal at HEAD) and this
scope decision are recorded for independent acceptance in CODEX_REPORT.md.

## 5. Before the first run

No H2-R2 run was executed by the implementer. All of the following remain operator/Claude work:

**Run prerequisites (F20).** Three environment facts the harness assumes, checked before the first
run because each one silently changes what a gate measures:

- `PYTHONPATH` must be empty. A host `sitecustomize` that pre-imports stdlib modules can mask the
  F1 shadow test (`scripts/tests/` shadowing a stdlib import) and make an unfixed base look green.
- the pinned interpreter must report `os.open in os.supports_dir_fd`
  (`scripts/tests/test_skill_execution.py` needs it); otherwise those tests fail for the
  environment, not for the task.
- macOS with `sandbox-exec`. Every launch is confined (F16/T29); without it the driver reports
  `BLOCKED:SANDBOX_UNAVAILABLE` before any worker starts.

0. **Run only through the frozen driver.** An ordinary run is:
   `$PY $H/freeze-v2/run_h2r2.py run <run_id> --runs-root <SHARED_RUN_ROOT>`, with
   `next --runs-root <SHARED_RUN_ROOT>` printing the eligible run id and `status` printing the
   plane. The driver owns the launch prompt and the two sublimits by construction: the worker is
   `opencode run --standalone --auto --format json -m <plan model>` with the frozen prompt, the
   profile env file's exports over a minimal base env, and a 90-minute wall clock; the per-run
   auditor then runs the same command in `R/<run_id>/audit/`. Nothing about a run is typed by
   the operator except the run root.

0. **Execute runs only through the frozen driver.** `freeze-v2/run_h2r2.py` is the single entry
   point (`next`, `run <run_id>`, `status`, all against `H2_RUNS_ROOT`): it prepares the wrapper,
   runs the preflight before any worker, renders the contract, launches the frozen worker command
   under the profile environment with the 90-minute wall clock, collects, accepts, starts the blind
   per-run audit, and appends one `registry-v2.jsonl` line per run. It refuses a run whose
   predecessors are not registered and refuses any run id that is registered or was started and
   reached work, so no operator input can change what a run does or how often it happens.
   A third program closes the loop over a runs root: `$PY $H/freeze-v2/aggregate_runs.py
   <SHARED_RUN_ROOT>` prints the per-task per-arm valid pairs, the INVALID and BLOCKED runs with
   their reasons, and the protocol-v2 §7 result token with the exact rule that decided it;
   `status` reports the same `usable_pairs` plus the `blocked`/`invalid` counts, so
   "registered=20" cannot be mistaken for a result.

   **Infrastructure failure is not a result (F14).** The rule was decided before any counted run and
   is recorded in protocol-v2 §6.1; the driver owns both halves. Immediately before the worker (and
   again before the auditor) it sends one frozen minimal prompt with the same command, model and
   environment in a scratch directory outside the run dir: a failure is `BLOCKED:PROVIDER_UNREACHABLE`,
   nothing is launched, no attempt is consumed and the same run id may be invoked again later; every
   check is kept with its timestamp in `<runs_root>/reachability-v2.jsonl`. A provider error before
   the worker's first tool call, or a non-zero exit with zero tool calls, ends that ATTEMPT rather
   than the run: its tree is archived under `<run_id>/attempts/<n>/` with a per-file sha256 manifest,
   a fresh run dir is prepared from scratch (new repository, new delivery, new preflight) and the run
   is attempted again, at most three attempts per run id (`attempts-v2.jsonl` keeps one line per
   attempt with its number). Once the worker has made any tool call nothing is retried; a later
   error, exit or timeout is `INVALID` as before. The auditor has the same rule with its own counter
   (blocked audit attempts are archived under `<run_id>/attempts/audit-<n>/` — a block at the
   reachability, fresh-home or confinement check leaves its `probe.json` there, the mechanical
   verdict is untouched, and the run stays `BLOCKED` until an audit succeeds). The final verdict comes from
   the single attempt that reached work, and `registry-v2.jsonl` keeps exactly one terminal line per
   run id naming that attempt. Why: live pilot #2 ended INVALID after 14 s on a transient
   `provider.no-route` with zero tool calls, and it was the third transient upstream failure in two
   days (401 Invalid credential, "stream ended without finish_reason", `provider.no-route`). Under
   the old rules that noise, not the treatment, would eat counted runs — possibly unequally between
   arms. The rule is arm-symmetric and outcome-blind because it can only fire before any worker
   action: it cannot re-roll a result.

   **Four runs at a time, with backoff and one frozen model (T34, T35).** `$PY
   $H/freeze-v2/run_h2r2.py run-plan --runs-root <SHARED_RUN_ROOT>` schedules the whole plan: at
   most `MAX_PARALLEL = 4` runs of that root are in flight, each a separate `run` child process, so
   one crash cannot take another run down. Starts stay in plan order — a run starts only when every
   earlier run is registered or running, and the second arm of a task starts only after the first
   arm is registered — so only finishing overlaps and a concurrent set is always different tasks.
   `run` refuses a non-eligible id with `PREDECESSOR_NOT_STARTED:<id>`,
   `SAME_TASK_ARM_NOT_REGISTERED:<id>` or `PARALLEL_LIMIT:<n>`; start/end lines (time, pid, run id,
   outcome) go to `<runs_root>/scheduler-v2.jsonl`; registry and attempt lines are appended under an
   exclusive `fcntl.flock`, so two finishing runs cannot interleave. A run that ends BLOCKED before
   work and registered nothing (a failed reachability check, or any pre-work provider state that
   consumed no attempt) is re-queued in plan position after an exponential backoff with jitter —
   60 s, 120 s, 240 s, 480 s, capped at 900 s, at most six re-queues per scheduler invocation. Each
   wait is a `wait` line (requeue number, seconds) in the scheduler log, the other live runs keep
   their slots meanwhile, and after the budget the scheduler stops and prints what is left for the
   operator to re-invoke. A registered run is never re-run: the three-attempt `BLOCKED` line of
   protocol-v2 §6.1 stays terminal, and the scheduler never rewrites a verdict. Each `run.json`
   records `concurrent_with` and its start/end times; `aggregate_runs.py` reports the overlap pairs
   and `status` shows in-progress runs. Shared machine resources follow the same rule: the preflight
   service port is chosen per run (bound and released immediately before `service set port`) and a
   collision is retried with a new port at most three times, recorded. WHY (decided 2026-10-23; the
   constant was raised from two to four while still before any counted run): twenty 10–90 minute
   runs would take most of a day serially, while the isolation in §3 makes cross-run influence
   impossible except shared provider load — and that load is arm-symmetric because concurrent runs
   are different tasks and the arms alternate in plan order. **The model is frozen too:** every
   worker and auditor launch of the twenty uses the single `run-plan-v2.json` model
   `opencode-go/deepseek-v4.1-flash`, and a plan carrying a second one is refused before anything
   is spawned (`MODEL_NOT_FROZEN`). There is no model failover inside the experiment — the model is
   part of the treatment environment, so a pair whose arms ran on different models is not a
   comparison (protocol-v2 §6/§6.1: model tier mismatch is INVALID). Outages are met only by
   waiting (the reachability, before-work and backoff rules); failover exists only in the
   implementation pipeline, which never touches an H2-R2 run.

1. **Install the frozen profile template, then attest it before every run.** Install
   `freeze-v2/worker-profile/opencode.json` as the profile's
   `~/.config/opencode/opencode.json`, byte for byte (§3 PROFILE). From the repository root,
   with `H=experiments/v1.2/h2-lazy-disclosure` and `PY` set to the pinned interpreter, run the
   preflight in each prepared run directory before its worker starts:

   ```bash
   $PY $H/freeze-v2/isolation_canary.py preflight "$H2_RUNS_ROOT/<run>" \
       --profile-env ~/.h2-worker-profile/env.sh
   ```

   It calls only `opencode debug paths` and `opencode debug config`, writes
   `<run>/preflight.json`, and must print `"verdict": "PASS"` (exit 0). A FAIL means the run
   does not start: the profile is not the frozen one, or a state path or config source escapes
   it. This is the mechanical answer to F6; the implementer never ran it against the live
   profile, so the first real verdict is Claude's.

2. **Claude runs the isolation canary in the logged-in isolated profile and records the verdict.**
   With `H2_RUNS_ROOT` set to `<SHARED_RUN_ROOT>` (§3: in the macOS Shared folder, outside every
   home, no discoverable ancestor):

   ```bash
   $PY $H/freeze-v2/isolation_canary.py prepare "$H2_RUNS_ROOT/isolation-canary"
   ```

   This prints the exact `source ~/.h2-worker-profile/env.sh && opencode run --standalone
   --format json -m opencode-go/deepseek-v4.1-flash` command, including its cwd and prompt.
   Claude executes that printed command, checks the pinned CLI version, retains events/stderr,
   then records the parser verdict outside the repository:

   ```bash
   $PY $H/freeze-v2/isolation_canary.py check "$H2_RUNS_ROOT/isolation-canary/events.jsonl" > "$H2_RUNS_ROOT/isolation-canary/verdict.json"
   ```

   Require wrapper-at-startup, repo-only-after-read and nested-after-read evidence, with no
   observed MCP/plugin/global/user/skill contamination beyond the two built-in skills `opencode`
   and `report` — a disclosed, arm-symmetric fact of this runtime, not a delivery difference.
   The parser covers observable events; inspect the live evidence and profile rather than
   claiming visibility into hidden context.

3. **Fresh DeepSeek review of the exact final freeze candidate SHA.** Review this plan, the full
   final diff, registry/scope interpretation, declared confound, scoring deviations and both
   anchors. Run the pinned tests and manifest check. This is an independent review, not the
   implementer's self-check. Any repair produces a new SHA requiring a fresh matching review.

4. **Merge path per [protocol.md §12](../protocol.md#12-收尾--合并门part-3032).** Enumerate the
   applicable independent reviews, bot output, inline/conversation threads and configured CI
   at the final SHA; disclose missing channels, settle findings, obtain lawful integration
   authority, then follow the serial integration and remote-verification path. No push, PR,
   merge or actual experiment is authorized by this implementation hand-off alone.

The run protocol is [protocol-v2.md](protocol-v2.md), the full implementation receipt is
[CODEX_REPORT.md](CODEX_REPORT.md). Start execution only after the external prerequisites and
the separate run authorization are satisfied.
