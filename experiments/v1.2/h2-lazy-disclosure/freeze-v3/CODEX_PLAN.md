# Freeze v2 completion — implementation plan for Codex (acceptance by Claude)

You are implementing; you are NOT the reviewer and you do NOT decide acceptance. Every task below
ends in mechanical gates. Stop after T9. Do NOT execute any H2-R2 run.

## 0. Ground rules (violating any one fails acceptance outright)

```text
REPO        $REPO = this git worktree (absolute path given in the hand-off prompt)
BRANCH      experiment/v1.2-h2-freeze-v3   (start: c40266f or later; never switch branch)
PY          $PY = the toolchain python given in the hand-off prompt (ruff 0.15.18)
WRITE ONLY  experiments/v1.2/h2-lazy-disclosure/freeze-v3/**   (new files and the README)
            experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py   (new)
NEVER TOUCH scripts/ adapters/ references/ AGENTS.md RULES.md (canonical)
            experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py (validator 2.8.12)
            experiments/v1.2/h2-lazy-disclosure/admission/** (measured data)
            the round-2 frozen set: task-registry.json scoring-rubric.md routes-h2.json
              protocol.md variant-manifest.json round-2-freeze.json harness/run-plan-r2.json
              carriers/ harness/*.sh harness/*template*.md harness/control-carrier-*.md
            replay/ experiments/v1.2/cases.yaml (H3 corpus)
            any other repository; ~/.h2-worker-profile (only READ env.sh)
NO          push, PR, network (except none needed), credentials, model calls, `git reset` of
            others' work, editing measured JSON by hand (regenerate with the program instead)
TEXT RULE   never write the recipe identifiers that references/*.md declare (the repo's
            single-declaration tests scan every text file); refer to sections by path instead
COMMITS     one commit per task, identity:
            git -c user.name=FlapPearLabs -c user.email="151931662+FlapPearLabs@users.noreply.github.com" commit
            message ends with: Co-Authored-By: Codex <noreply@openai.com>
GATES       (run before every commit; all must pass)
            $PY -m ruff check .
            $PY scripts/validate_governance.py                      -> 35/35
            $PY scripts/validate_public_release.py                  -> VIOLATIONS=0
            TMPDIR=$(cd "$TMPDIR" && pwd -P) $PY -m unittest discover -s scripts/tests   -> OK
            $PY -m unittest discover -s experiments/v1.2/tests      -> OK
            git diff --stat c40266f -- <every NEVER TOUCH path>      -> empty
```

Context to read first (do not modify): `freeze-v3/README.md` (all of it — §3 is the decided
runtime and layout), `freeze-v3/review-log.md`, `admission/freeze-v2-input/shortlist.json`,
`protocol.md` §2–§4 §8–§10 §12, `scoring-rubric.md`, `harness/prepare_run.sh` (delivery v5 and
DELIVERY_ANCHORS blocks: the byte composition to reuse), `harness/worker-brief-template.md`,
`n21-closure-report.md` FREEZE_V2_HANDOFF (FZ2_1..FZ2_4), `admission/README.md` §5 (FZ-ADM-*).

## T1 — wrapper-layout delivery: `freeze-v3/wrapper_delivery.py`

One module, importable, plus a CLI `prepare <run_dir> <task_id> <arm> --materials <commit>`.
- Builds `<run_dir>/` exactly as README §3 LAYOUT: `AGENTS.md` (arm carrier, bytes composed exactly
  as prepare_run.sh composes CODEBUDDY.md: control = control-carrier-header.md + `git show
  <materials>:AGENTS.md` + control-carrier-footer.md; variant = carriers/H2_LEAN_BOOTSTRAP.md with
  sha256 == variant-manifest VARIANT_HASH), `H2_RULES.md` (materials RULES.md), `H2_WARM/` (S3
  destinations of routes-h2.json at materials), `repo/` = `git worktree add --detach` at the task
  base. Report and telemetry paths live in `<run_dir>/`, NEVER under `repo/`.
- All delivered bytes are read from git objects at `--materials`, never the working tree.
- Postconditions (fail closed, non-zero exit, nothing half-built left behind): `repo/` HEAD ==
  base; `git -C repo status --porcelain --ignored` is empty; no delivered name exists anywhere
  under `repo/` that did not exist at the base; `<run_dir>` is not inside any git repository.
- Writes `<run_dir>/receipt.json`: task_id, arm, base_sha, materials_commit, carrier_kind,
  carrier_sha256, rules_sha256, warm_bundle_sha256 (same definition as prepare_run.sh), program
  sha256 of wrapper_delivery.py.
- `cleanup <run_dir>`: removes the worktree via `git worktree remove --force` + prune.
GATE T1: tests in test_v1_2_h2_freeze_v2.py build both arms for one real shortlisted task into a
temp dir and assert every postcondition and receipt hash; a test that pre-plants a stray file in
the base tree path proves the "nothing under repo/" check fails closed.

## T2 — delivery anchors for the wrapper layout

Extend `freeze-v3/delivery_anchors.py` (do not change its existing slots' semantics) with slot
`WRAPPER`: PRE = bare base; POST = the repo/ of a wrapper_delivery build. Also fold in KNOWN_P3-2:
"expected failure" / "unexpected success" lines count as a status change (not passing).
Re-run for all 10 tasks from the repository root:
`$PY $H/freeze-v3/delivery_anchors.py . $H/admission/freeze-v2-input/shortlist.json --materials <HEAD> --out $H/freeze-v3/delivery-anchors.json`
GATE T2: WRAPPER is DELIVERY_NEUTRAL for 10/10 tasks in both arms (oracle and full suite
identical non-passing sets, ran_delta 0). If ANY task is not neutral: STOP, record it in README §2,
do not continue to T4 for that task, and report. Update README §2 numbers from the new JSON only.

## T3 — isolation canary for the isolated worker profile: `freeze-v3/isolation_canary.py`

Builds a wrapper run dir with canary instruction files (wrapper AGENTS.md, repo AGENTS.md, nested
AGENTS.md) in a synthetic repo, and prints the exact opencode command to run under
`source ~/.h2-worker-profile/env.sh` with `opencode run --standalone --format json -m
opencode-go/deepseek-v4.1-flash`. DO NOT run opencode yourself (no model calls): Claude runs it at
acceptance. Provide `isolation_canary.py check <events.jsonl>` that parses the JSON event stream and
emits a verdict JSON: wrapper canary present at startup; repo canary only after the first read
inside repo/; no MCP tool, plugin agent, global/user AGENTS.md, or skill text present.
GATE T3: unit tests of the `check` parser on hand-made event fixtures (positive + each negative).

## T4 — task registry v2: `freeze-v3/task-registry-v3.json` + generator `build_registry.py`

Generated (never hand-edited) from shortlist.json + admission ledgers. 10 tasks, ids f01..f10 in
shortlist order. Per task: case_id, base_sha (B'), oracle {path, blob_sha256 at base and at
candidate (must be equal: FRAMEWORK_FROZEN), command}, candidate_sha kept ONLY in a separate
`expected` block that the worker brief never includes, scope {deny: the oracle path and every
`scripts/tests/` file existing at base; deny_prefixes as round 2; allow everything else in repo/},
task_text = a neutral restatement derived from the candidate's commit subject + "make
`<oracle>` pass without modifying any test file", NO candidate SHA, NO diff hunk, NO literal
copied from the candidate's non-test changes.
GATE T4: generator is deterministic (two runs byte-identical); a test asserts no candidate SHA
(full or ≥7-char prefix) and no line of `git diff base cand -- ':!scripts/tests'` added text of
length ≥ 20 occurs in any worker-visible field; every oracle blob hash matches the object DB.

## T5 — run plan v2: `freeze-v3/run-plan-v3.json` + generator

20 runs = 10 tasks × {control, variant}; run ids `h2r3-f01-c` style; counterbalanced: arm order
alternates task to task (f01 C,V; f02 V,C; …); all runs share one materials_commit (the freeze
commit's parent, recorded), model `opencode-go/deepseek-v4.1-flash`, runtime `opencode 2.0.25
--standalone`, profile `~/.h2-worker-profile`. Fresh episode per run (no session reuse).
GATE T5: test asserts 20 unique runs, each task exactly one per arm, C-first count == V-first
count == 5, one materials_commit, one model.

## T6 — worker brief v2: `freeze-v3/worker-brief-v3.md` + renderer

Adapt harness/worker-brief-template.md to the wrapper layout: worker cwd = `<run_dir>`, repo at
`repo/`, delivered files at `<run_dir>`, report + `.h2-telemetry.log` in `<run_dir>` (never in
repo/), forbidden reads (other runs, registry `expected`, this freeze-v3 directory, git history of
the candidate). Same text for both arms except the BOOTSTRAP_DELIVERY block.
GATE T6: rendering both arms for every task differs ONLY inside the delivery block (test).

## T7 — protocol v2: `freeze-v3/protocol-v3.md`

Authority text for Round H2-R2 that (FZ2_2) contains no "baseline must be green" C2 language and
cites Schema v2 classes (A_REPAIR = frozen attributable FAIL→PASS); (FZ2_1) states the validator is
the PRE-FREEZE gate and that no run re-decides eligibility; (FZ2_3) defines the single aggregate
owner and implements it as `freeze-v3/aggregate_set.py` = derive(records with REQUEST_VALID ∧
admitted_by_freeze) where admitted_by_freeze = membership in task-registry-v3.json, every count
derived from it; (FZ2_4) t02 = NOT_ADMITTED_CURRENT_REVISION, not rescued. It carries README §3's
DISCLOSED CONFOUND verbatim, the result vocabulary DISCLOSURE_SAFE / DISCLOSURE_HAS_COST /
INSUFFICIENT_EVIDENCE with a pre-registered decision rule mapped onto scoring-rubric.md §9 (cite,
do not copy; state every deviation), invalid-run handling (protocol §8: register, never silently
re-run), and the acceptance per run: oracle FAIL→PASS under BOTH temp-root spellings
(check_task_class.acceptance_env), full suite no newly-not-passing id vs the T2 PRE set, scope check.
GATE T7: test greps protocol-v3.md: no "baseline must be green", FZ2_1..FZ2_4 each present, the
three result tokens present, the confound paragraph byte-equal to README §3's.

## T8 — freeze manifest + pins: `freeze-v3/freeze-manifest.json`, generator, tests

sha256 of every frozen v2 file (registry, run plan, brief, protocol-v2, wrapper_delivery.py,
delivery_anchors.py, isolation_canary.py, aggregate_set.py, routes-h2.json, carriers, scoring-rubric.md,
validator check_task_class.py) + the same values as literals in test_v1_2_h2_freeze_v2.py (two
independent anchors, as round 2 did).
GATE T8: changing any one byte of any frozen file turns a test red (test does this on a temp copy).

## T9 — README + hand-off

Update freeze-v3/README.md: §4 "What is frozen" (manifest pointer), §5 "Before the first run":
(a) Claude runs the T3 canary in the logged-in isolated profile and records the verdict JSON;
(b) fresh DeepSeek review of the freeze SHA; (c) merge path per protocol §12. Write
`freeze-v3/CODEX_REPORT.md`: per task T1–T8 what was built, the commands run, gate outputs
(verbatim tail lines), anything you could not do and why. Do not claim anything you did not run.
