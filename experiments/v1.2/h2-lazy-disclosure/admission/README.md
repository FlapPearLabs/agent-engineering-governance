# H2 Schema-v2 Candidate Admission (pre-freeze)

> Node: N2 — H2 · sub-stage after N2.1 CLOSED, before Freeze v2.
> This directory finds real historical tasks, measures them, and lets **Schema v2 decide**.
> It grants nothing: `REQUEST_VALID` is a request to Freeze v2; the grant is Freeze v2 + fresh review.
> It does not modify the frozen surface (task-registry / run plan / variant manifest / scoring /
> routes / protocol / round-2 freeze) and executes no H2-R2 run. H3's replay corpus
> (`experiments/v1.2/replay/cases.yaml`) is byte-identical to `f4eb503`.

## 1. Workflow (repeatable; every step is a program, every output is in the batch directory)

```text
discover.py        every non-merge commit (or, with --merges, every merge vs its FIRST parent) on
                   <ref> -> one pair -> ONE disposition; nothing is dropped silently. Uses the
                   validator's own derived_triggers() and acceptance convention.
                     DERIVED_TRIGGER_PRESENT     delta rewrites a test/validator: cannot be a valid
                                                 request as a historical pair
                     MEASURE_ADDED_ACCEPTANCE    delta adds an acceptance surface -> measured
                     DEFERRED_FROZEN_BASIS_SCAN  no added acceptance -> every surface executed
                     DUPLICATE_TASK (--merges)   same base tree + candidate tree as a commit pair
                     NO_DELTA / NO_PARENT
measure.py         the validator's own recompute_transition() per pair; raw exit codes per surface,
                   stamped with the validator file's sha256
probe_basis.py     what the basis acceptance EXERCISED (unittest ran/skipped/failures/errors)
diagnose_bites.py  which named check BIT, rebuilt with the validator's own _materialise_mutation()
corpus_cases.py    renders identity anchors for admission/corpus.yaml (NOT H3's corpus); signal
                   counts computed independently of the H3 detector and cross-checked by tests
build_records.py   one Schema-v2 record (request) per routed pair; every evidence, disclosure and
                   rejection string derived from the pair's disposition and measured facts
check_task_class.py THE VERDICT: re-executes every transition and binds every declared status
ledger.py          all required per-candidate fields from the files above; asserts the two
                   independent executions (measure.py vs the validator) agree
negative_controls.py  laundered records through the current validator + the attack pairs through
                   earlier validator revisions loaded straight from git -> negative-controls/report.txt
```

Reproduce (worktree root; `PY` = the pinned toolchain interpreter; `<scratch>` outside the repo):

```bash
A=experiments/v1.2/h2-lazy-disclosure/admission
$PY $A/discover.py . 5ab500e5478b671f43df80a78730ca172da6cf2b <scratch>/d.json            # == batch-1 routing
$PY $A/discover.py . 5ab500e5478b671f43df80a78730ca172da6cf2b <scratch>/m.json --merges   # == batch-3 routing
for b in 1 2 3; do $PY experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py $A/batch-$b/classification.json . ; done
for b in 1 2 3; do $PY $A/ledger.py $A/batch-$b; done
$PY $A/negative_controls.py .
```

Every measurement file (168) was produced by validator **2.8.8** — `environment.validator_sha256`
equals the committed `harness/check_task_class.py`. Earlier measurements were regenerated, never
edited. `measure.py --jobs N` runs pairs in parallel; a concurrent `git worktree add` can race
and fail CLOSED (WORKTREE_MATERIALISATION_FAILED) — re-run that pair serially; it is never a pass.

## 2. Coverage — governance repository, `origin/main` @ `5ab500e`

```text
NON-MERGE COMMITS   200 = 198 pairs + 2 root commits (NO_PARENT)
  DERIVED_TRIGGER_PRESENT       98   not executed (Schema v2 refuses them as historical pairs; FZ-ADM-6)
  MEASURE_ADDED_ACCEPTANCE      17   batch 1
  DEFERRED_FROZEN_BASIS_SCAN    83   batch 2
MERGE COMMITS        25 (first-parent pairs, batch 3)
  DUPLICATE_TASK                 7   same trees as a commit pair: one task, not two
  DERIVED_TRIGGER_PRESENT        6
  NO_DELTA                       1
  MEASURED                      11   1 MEASURE_ADDED_ACCEPTANCE + 10 DEFERRED_FROZEN_BASIS_SCAN
EXECUTED IN TOTAL              111 pairs (17 + 83 + 11)
```

## 3. Results (validator 2.8.8; `<batch>/validator-run.txt`, `<batch>/ledger.json`)

```text
                     records  valid  rejected  executions_disagree
batch 1 (commits)       17      15       2              0
batch 2 (frozen scan)    8       5       3              0      (75 pairs: no transition, no record)
batch 3 (PR merges)      3       3       0              0      (8 pairs: no transition, no record)
batch 4 (externalized)  19      19       0              0      (57 identities built; 38 no transition)
TOTAL                   47      42       5              0
```

Records are made for every pair whose measured transition supports a class, plus the rejections
that are named examples (r08, r11 batch 1; r23, r26, r29 batch 2). Per-candidate fields CASE_ID …
EVIDENCE_PATHS are in each `ledger.json`.

### 3.1 What the 23 valid requests are (observations for Freeze v2, not verdicts)

```text
A_REPAIR, DELTA_ADDED oracle     16   the historical delta authored its oracle
   BEHAVIORAL 3   r02 review-evidence interface, r13 P1-T06 producer trust, r17 P1-T08 lifecycle
   DOC_TEXT  11   reference text checked by marker groups + anti-vacuity probes; 8 of them are one
                  family (P1 ticket doc-recipes: r10 r12 r14 r15 r16 r18 r19 r20)
   DOC/DATA   2   r22 experiment foundation (corpus file + docs); r31 PR #1 (governance baseline;
                  its basis is the validator it adds)
A_REPAIR, FRAMEWORK_FROZEN oracle 2  r24 (4505fae) repairs the t09 byte-budget regression that its
                  parent 825d390 introduced ("repair round 2" of a review cycle); r27 (7cadc9c)
                  restores t09 after 95667e8 broke it. Oracle test_p1_t09_bootstrap_byte_budget.py
                  is byte-identical at both revisions. r24's delta is two doc files and restores
                  a contract (OWNER self-naming); r27's is a byte-exact one-line REVERT of
                  95667e8, and its oracle fails at the base only on exact length pins (1686 vs
                  1696, 1144 vs 1170 chars) — a much weaker task than r24.
B_REGRESSION_GUARD                5   r25 r28 r30 (commits), r32 r33 (PR #40, #41): EVERY bite is
                  validate_governance.py `markdown-links-resolve` (test_p1_t16 fails because it
                  runs that validator in a scratch copy). Real but SHALLOW: removing the added doc
                  leaves a dangling link; nothing about the doc's content is checked.
EXERCISED  the 16 TEST bases each ran >= 7 tests with 0 skips at the candidate. At the base, 15
           fail at AssertionError level (r02 also raises FileNotFoundError, r21 also IndexError);
           r22's base fails only with FileNotFoundError (its deliverable file is absent). r07 and
           r31 have VALIDATOR bases, whose exit code is their only report.
OVERLAP    r31 (PR #1) contains r07's commit 295ce65; r33 (PR #41) contains r30's commit a652fd4.
           Different task identities, correlated content (FZ-ADM-8).
REJECTED   r08, r11  BASE_EQUALS_CANDIDATE (the added acceptance does not move)
           r23, r26  CANDIDATE_REGRESSES_A_FROZEN_GUARD (each breaks t09; F-A3 / F-A6)
           r29       CANDIDATE_REGRESSES_A_FROZEN_GUARD via a DELETED guard: it removes
                     test_experiment_v12_foundation.py, whose base bytes fail against the
                     candidate (F-A8); the only pair of the 111 that deletes an acceptance surface
```

## 4. Findings raised by real candidates and by the fresh reviews of 4add2ca, f2c48a0, ceb3a72, 6527c81, 72f0bb4, 617ba01

Each: fact → reproducer → severity → minimal fix → red-before/green-after test. The version-level
before/after for every one is in `negative-controls/report.txt` (earlier validators loaded from
git, not edited copies).

```text
F-A1  P1  2.8.0  mutation unlinked added files but left them in git's index; index readers crashed
                 and the crash counted as a bite. r22 laundered to B: SUPPORTED by 2.8.0.
F-A1b P1  draft  a mutation commit under a synthetic identity tripped the HEAD-identity check.
F-A1c P2  2.8.0  non-ASCII added paths were quoted by git and silently kept.
F-A3  P1  2.8.0  a frozen surface the CANDIDATE broke counted as a bite (r23 adds nothing, breaks t09).
F-A4  P1  2.8.1  (fresh review) the mutation was committed ON TOP of the candidate: merges stopped
                 being merges, HEAD^ changed; PR #49's merge got a B request accepted end to end.
                 Fix: the mutation is the candidate's own commit object with only its tree changed.
F-A5  P2  2.8.1  (fresh review) `git rm` read a path as a glob. Fix: --literal-pathspecs + exact-diff
                 postcondition.
F-A6  P2  2.8.1  (fresh review) the candidate leg was checked only on the biting surface; r26 breaks
                 t09 while a link guard bit. Fix: B refused when ANY frozen guard regresses.
H3    P2  4add2ca (fresh review) anchors appended to H3's replay corpus changed H3's metrics. Fix:
                 separate pinned admission/corpus.yaml; H3's file restored byte-identical.
EVID  P2  4add2ca (fresh review) hardcoded evidence/disclosure/externalisation strings were wrong for
                 batch 2 (said MEASURE_ADDED_ACCEPTANCE / DELTA_ADDED). Fix: derived per pair.
F-A7  P2  2.8.2  (review of f2c48a0) a guard that HANGS at the candidate (rc 124) escaped the
                 regression rule; B records never declare the status that would have caught it.
                 Fix: B refused on any base-green guard unmeasured at the candidate.
F-A8  P2  2.8.2  (review of f2c48a0) surfaces the delta DELETES were never run; r29 deletes a guard
                 its candidate fails. Fix: base-only surfaces run with base bytes (DELTA_DELETED).
F-A9  P3  2.8.2  (review of f2c48a0) name-status read without -z: a non-ASCII rewritten validator
                 derived no trigger. Fix: -z parsing (discovery routing unchanged, re-verified).
P3    2.8.2      (review of f2c48a0) postconditions had no test (mutants survived) -> perturbation
                 test; EVID fix had no regression test -> test_evidence_strings_match_each_pairs_own_facts;
                 stale docstrings; discovery files regenerated under 2.8.3 (routing identical).
F-A10 P2  2.8.3  (review of ceb3a72) surfaces came from the FILESYSTEM, triggers from GIT: a guard
                 re-added through a symlinked or case-folded directory evaded every rule. Fix:
                 surfaces from `git ls-tree` (regular files, blob provenance) + alias fail-closed.
P3    2.8.3      (review of ceb3a72) C-record details/reason codes derived from facts; explicit
                 rename policy (-M for triggers, --no-renames for added paths); refusal messages
                 name the regressed guard; mutants M3 M8 M10 M13 now killed.
F-A11 P1  <=2.8.4 (review of 6527c81; pre-dates this stage) an added module shadowing an import
                 (scripts/json.py) changed what a FROZEN oracle executes. Fix: derived trigger
                 ACCEPTANCE_SURFACE_IN_WORKER_SCOPE for importable names on acceptance import roots.
F-A12 P2  <=2.8.4 (review of 6527c81; pre-dates this stage) a .gitattributes filter rewrote a
                 frozen guard's bytes. Fix: unfiltered blob identity of every surface in every tree.
F-A13 P1  <=2.8.5 (review of 72f0bb4; pre-dates this stage) F-A11 covered one shape: a root module,
                 a package under scripts/tests, a sourceless .pyc and a committed __pycache__ entry
                 still flipped frozen oracles. Fix: shadow_paths covers the class on every import
                 root (names resolved by an isolated interpreter); acceptances never read bytecode.
F-A14 P1  <=2.8.5 (review of 72f0bb4; pre-dates this stage) one surface rewrote another between
                 runs (identity was checked once, in a shared tree). Fix: every run starts from a
                 tree reset to its pinned revision, carries blobs from the object database and
                 re-verifies identity.
F-A15 P2  2.8.6    (review of 617ba01; a regression of the F-A14 fix) the per-run carry dropped the
                 tracked file mode. Fix: (blob, mode) carried and verified.
BOUNDARY         the review of 617ba01 assessed the stated execution boundary (schema §6.6) as sound
                 for this pre-freeze gate; its precondition — inputs are the project's own history,
                 not worker deltas — binds Freeze v2.
KNOWN P3         overlapping identity defences are not individually tested (single-check mutants can
                 survive); a mode-only change derives a trigger (conservative); the installed-package
                 half of the shadow test depends on the interpreter's site-packages. Discovery
                 routing re-run under 2.8.6: identical for all 225 pairs (the bytecode rule is scoped
                 to acceptance import paths — real history commits bytecode under adapters/).
F-A2  P3  latent the validator reads exit codes only; an all-skipped unittest module would read as
                 PASS. Not observed (0 skips on every basis); probe_basis.py records it per record.
N2.1 P3-A / P3-B closed (eligibility-schema-v2.md §6.7).
```

## 5. What Freeze v2 must still decide or measure (Schema v2 cannot)

```text
FZ-ADM-1 TASK_TEXT <-> ORACLE ALIGNMENT  DOC_TEXT oracles check specific marker groups; a worker that
         sees a paraphrased task text cannot hit them, so both arms fail and the task carries no
         signal. MEASURED on r15 (Issue #23, 7,976 chars, read-only `gh issue view`): 63 of the
         oracle's 241 string literals occur verbatim in the ticket, and the heading the oracle
         locates the recipe by (`### 5.2 破坏性工作区事务（DESTRUCTIVE_WORKSPACE_TRANSACTION）`) does
         not. Freeze v2 must derive each task text from its ticket and check that every literal the
         oracle requires is derivable — or not select the task.
FZ-ADM-2 STRATA  8/16 DELTA_ADDED A requests are one doc-recipe family; all 5 B requests are one
         shallow guard kind; r27 is a revert pinned by exact lengths. Selection must be
         stratified; the strongest subset today is BEHAVIORAL 3 + r24 = 4, i.e. FEWER than the
         6 the protocol requires without the doc family or the B shape.
FZ-ADM-3 DELIVERY ANCHORS (schema §6.4)  pre-/post-delivery acceptance not measured for any request.
FZ-ADM-4 PER-BASE ROUTE PRECONDITIONS (protocol §10)  request bases are not P6's six bases.
FZ-ADM-5 ORACLE PLACEMENT  DELTA_ADDED bases: the harness must place the frozen candidate blob
         (sha256 in the ledger) and exclude the path from worker scope. FRAMEWORK_FROZEN bases
         (r24, r27) and B guards: the path already exists; it must only be excluded from scope.
FZ-ADM-6 THE DOMINANT REAL-REPAIR SHAPE  98 commits + 6 merges edit an existing test; Schema v2
         derives WORKER_MODIFIES_TEST_ORACLE. Admitting any needs a NEW task identity with an
         externally frozen oracle (the r01 route): a design decision, not a rescue.
FZ-ADM-7 CROSS-REPOSITORY CANDIDATES  zhihu-grabber-toolkit, workbuddy-toolkit, webcodex hold real
         repair history, but Schema v2 validates only pairs in this object database and the H2
         round / routes / delivery are governance-scoped (r01: ROUND_SCOPE_DECISION).
FZ-ADM-8 OVERLAP  never select both r31 and r07, or both r33 and r30.
FZ-ADM-9 DELETED / REGRESSED GUARDS  Schema v2 refuses them only for B. Any task Freeze v2 admits
         (A included) must show empty DELETED_ACCEPTANCE_SURFACES and REGRESSED_GUARDS in the
         ledger, or Freeze v2 must justify them (a reference solution that breaks a guard is a
         flawed reference). All 23 valid requests have both empty.
```

## 6. Status of the admission count

```text
SCHEMA_V2_VALID_REQUESTS 23   >= 6 required by the H2 protocol: the COUNT is met by Schema v2.
GOOD H2 TASKS            NOT YET SHOWN — FZ-ADM-1..5, 8, 9 are open; the strongest stratum alone
                         is 4 (FZ-ADM-2).
FURTHER SEARCH HERE      not useful: every non-merge and merge pair of main was routed and every
                         routable pair executed. More strong tasks need FZ-ADM-6 (new identities
                         with externally frozen oracles) or FZ-ADM-7 (a round-scope decision).
```

## 7. Freeze v2 inputs (the governance-repo route the user chose on 2026-10-18)

```text
EXTERNALIZED_ORACLE  57 real repairs whose ONLY derived trigger was WORKER_MODIFIES_TEST_ORACLE were
                     given new identities (B', C) by externalize.py (schema §6.8); B' is
                     deterministic and verified by the validator; all B' are reachable from the
                     pushed branch admission/externalized-oracles-v1. 19 measure A_REPAIR on a
                     FRAMEWORK_FROZEN oracle (batch 4); one of them (r46) regresses another guard.
ALIGNMENT            alignment.py over every hidden-oracle doc request: 7 NOT_ALIGNED, 6 NO_TICKET,
                     0 ALIGNED -> the doc-recipe family drops out (freeze-v2-input/alignment.json).
SHORTLIST            select.py rules S1-S5 (freeze-v2-input/shortlist.json): 10 tasks, every one a
                     real repair judged by a VISIBLE, framework-frozen test, one per oracle file:
  r34-governance-ext-enforce-anchored-schema-patterns- test_review_evidence_contract.py
  r37-governance-ext-make-the-p1-t02-mandatory         test_p1_t02_execution_stage_pre_ticket_record.py
  r38-governance-ext-remove-local-digest-fallback-use  test_p1_t05_evidence_disposition.py
  r39-governance-ext-refuse-every-scheme-form-evidence test_p1_t06_producer_trust_boundary.py
  r40-governance-ext-make-the-p1-t11-pre               test_p1_t11_destructive_workspace_transaction.py
  r41-governance-ext-scope-the-not-auditable-rule      test_p1_t10_audit_visibility_recipe.py
  r42-governance-ext-treat-a-partially-populated-reuse test_p1_t08_evidence_lifecycle.py
  r24-governance-bootstrap-budget-repair-round-2       test_p1_t09_bootstrap_byte_budget.py
  r44-governance-ext-converge-the-p1-p2-findings       test_p1_t18_defect_promotion_fast_full.py
  r50-governance-ext-bind-skill-evidence-reads-to      test_skill_execution.py
STILL TO DO IN FREEZE V2   delivery anchors per task (schema §6.4), route preconditions per base
                     (protocol §10), task texts ("make <oracle> pass without modifying tests"), the
                     counterbalanced run plan, the frozen surface, and the fresh review.
```
