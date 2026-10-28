# Freeze v2 — acceptance round 1 of ab37a9d: CHANGES_REQUIRED (Codex fix plan T10–T14)

Accepted as built: write scope (only the two allowed paths), frozen surfaces untouched, commit
identity, no local paths, every gate green on independent re-run, registry and run plan
byte-deterministic and equal to the committed files, manifest check PASS, protocol-v2 content
(FZ2_1..FZ2_4, no C2 language, verbatim confound, conservative null rule), WRAPPER anchors 10/10
neutral, both disclosed interpretations (materials = T8 parent; n01/n02-style prefixes) as
REASONING — but the prefix choice is superseded by F1.

The GROUND RULES, NEVER TOUCH list and GATES of CODEX_PLAN.md §0 still bind every task below.

## Findings (verified by Claude with reproducers)

```text
F1  P1  ORACLE BYPASS BY AN ADDED FILE. Scope freezes only the test files that exist at the
        base (deny_prefixes = []), so adding files under scripts/tests/ is allowed.
        `unittest discover -s scripts/tests` puts scripts/tests first on sys.path, so an added
        scripts/tests/json.py shadows the stdlib json every oracle imports. Reproduced at f01's
        unfixed base e11a846 with ONLY that added file (it replaces unittest.TestCase.run with
        an always-success stub, then loads the real json):
          base untouched                 -> FAILED (failures=17)
          base + added scripts/tests/json.py -> Ran 46 tests ... OK
F2  P1  NO EXECUTABLE PER-RUN ACCEPTANCE. protocol-v2 §5 specifies collection, scope check,
        oracle FAIL->PASS in both temp-root spellings and the full-suite comparison, but no
        program implements it (CODEX_PLAN omitted it — a plan defect, not an implementer one).
        It must exist and be frozen before the first run.
F3  P2  isolation_canary.py `check` FAILS on a real opencode 2.0.25 event stream whose
        behaviour is correct (wrapper AGENTS.md at startup; repo AGENTS.md attached after the
        first read; nested after the second). Reasons emitted: INCOMPLETE_STREAM,
        NESTED_BEFORE_READ, NO_NESTED_ATTACHMENT, NO_REPO_ATTACHMENT, REPO_BEFORE_READ,
        UNEXPECTED_READ. The parser was tested only on hand-made events. Real events are
        {type: step_start|text|tool_use|step_finish, part: {type, text | tool, state: {input,
        output}}}; the canary markers appear in `text` parts, reads in `tool_use` parts.
F4  P1  RUN ROOT LEAKS USER SKILLS. With the run dir under the operator's home directory, the
        isolated worker still listed ~185 user skills: opencode discovers `.agents/`
        (and `.opencode/`) by walking UP from the cwd, past the redirected HOME. Re-run with the
        run root in the macOS Shared folder (outside every home): only the wrapper AGENTS.md at startup, no MCP, no
        plugin agent, and only two skills (`opencode`, `report`) — opencode built-ins, identical
        in both arms.
```

## T10 — close F1 (scope + shadow refusal)

- Registry: `deny_prefixes = ["scripts/tests/"]` for every task (no add / modify / delete /
  rename under it); keep the per-file deny list. Record the change and why in the registry's
  `scope_prefix_source` and protocol-v2 §7.
- The per-run scope check (T11) must also apply `check_task_class.shadow_paths` (validator
  2.8.12, import it; do not copy it) to every path the worker ADDED or renamed anywhere in repo/,
  refusing any BYTECODE / PACKAGE_IMPORTED_BY_DISCOVERY / PACKAGE_MARKER / SHADOWS hit
  (WORKER_SHADOWS_IMPORT), and refuse added `sitecustomize.py`, `usercustomize.py`, `*.pth`
  anywhere in repo/.
- Tests: the F1 reproducer (the added scripts/tests/json.py) must be REFUSED; an added
  stdlib-named module elsewhere (e.g. scripts/json.py) must be REFUSED by the shadow rule.

## T11 — close F2: `freeze-v2/collect_v2.py` + `freeze-v2/run_acceptance_v2.py`

- collect: full base→worker diff of repo/ (tracked, untracked, ignored, deletions, renames, and
  any worker commits: diff against the registry base, never HEAD), report + telemetry from the
  wrapper, re-verify every receipt hash of the delivered files; missing/empty telemetry or report
  is INVALID (never synthesised).
- acceptance (one verdict JSON per run): scope (T10 rules + nothing delivered inside repo/ +
  no path escapes repo/); oracle bytes == registry base hash; oracle in BOTH
  `acceptance_env("RESOLVED")` and `acceptance_env("SYMLINKED")`: base not passing, worker tree
  passing, executed count > 0, skips / expected failures / unexpected successes / unmeasured
  never PASS; full scripts/tests in both spellings: no non-passing id beyond T2's PRE set for
  that task (a SYMLINKED-only new failure is recorded and BLOCKS, never normalised). Exit 0 only
  for ACCEPT.
- Controls (tests, all 10 tasks where stated):
  POSITIVE  worker result = the historical candidate's non-test delta applied to B' (i.e. the
            candidate tree) -> ACCEPT for all 10 tasks.
  NEGATIVE  unchanged base -> REJECT (all 10); F1 json shadow -> REJECT; editing the oracle or
            any base test -> REJECT; a delivered file copied into repo/ -> REJECT; a worker commit
            that reverts a test edit inside history but leaves it in the tree -> REJECT.

## T12 — close F3: canary parser on the real event schema

Rewrite `check` against the real schema above. Add a test fixture built from the real stream
(provided at hand-off, paths replaced by `<RUN_ROOT>` placeholders; commit only the sanitised
fixture) that must PASS, plus mutated copies for each FAIL reason (marker missing, marker before
its read, extra read, MCP / plugin-agent / skill-catalogue contamination named in text). Skill
names other than the built-in allow-list {opencode, report} are contamination.

## T13 — close F4: run-root rule

- wrapper_delivery.py `prepare` refuses a run_dir that has ANY ancestor directory containing
  `.agents`, `.opencode`, `.claude`, `AGENTS.md`, `CLAUDE.md` or `opencode.json` (other than
  the run_dir's own AGENTS.md), and any run_dir under `$HOME` of the operator. Test with a
  temp ancestor carrying `.agents/`.
- README §3 / protocol-v2 §4: H2_RUNS_ROOT = `<SHARED_RUN_ROOT>`, an operator directory in the macOS Shared
  folder, outside every home (committed text names it only by this placeholder); the two built-in skills `opencode`, `report` are a disclosed, arm-symmetric fact.

## T14 — re-pin and report

Regenerate the run plan (materials per the T8 rule), the manifest (add collect_v2.py,
run_acceptance_v2.py) and the test literals; append to CODEX_REPORT.md a T10–T14 section in the
same evidence style. One commit per task; gates before each.
