# H2 Schema-v2 Candidate Admission (pre-freeze)

> Node: N2 — H2 · sub-stage after N2.1 CLOSED, before Freeze v2.
> This directory finds real historical tasks, measures them, and lets **Schema v2 decide**.
> It grants nothing: `REQUEST_VALID` is a request to Freeze v2; the grant is Freeze v2 + fresh review.
> It does not modify the frozen surface (task-registry / run plan / variant manifest / scoring /
> routes / protocol) and executes no H2-R2 run.

## 1. Workflow (repeatable; every step is a program, every output is in the batch directory)

```text
discover.py      every non-merge commit on <ref> -> one (parent, commit) pair -> ONE disposition
                 (nothing dropped silently). Uses the validator's own derived_triggers() and
                 acceptance convention (cross-checked by test_v1_2_h2_admission.py).
                   DERIVED_TRIGGER_PRESENT     delta rewrites a test/validator -> cannot be a valid
                                               request as a historical pair
                   MEASURE_ADDED_ACCEPTANCE    -> measured in the batch that routes it
                   DEFERRED_FROZEN_BASIS_SCAN  -> needs every surface executed (separate batch)
measure.py       the validator's own recompute_transition() per pair (base / candidate /
                 controlled mutation); raw exit codes per surface
probe_basis.py   what the basis acceptance EXERCISED (unittest ran/skipped/failures/errors)
corpus_cases.py  renders replay-corpus case blocks (identity root of Schema v2); signal counts are
                 computed independently of the H3 detector and cross-checked by the H3 loader
build_records.py one Schema-v2 record (request) per measured pair, class = measured transition
check_task_class.py  THE VERDICT: re-executes every transition and binds every declared status
ledger.py        all required fields per candidate, from the above files only; asserts the two
                 independent executions agree
```

Reproduce end to end (from the worktree root; `PY` = the pinned toolchain interpreter;
`<scratch>` = any directory outside the repository):

```bash
A=experiments/v1.2/h2-lazy-disclosure/admission
$PY $A/discover.py . 5ab500e5478b671f43df80a78730ca172da6cf2b <scratch>/d.json   # == batch-1 routing
$PY experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py $A/batch-1/classification.json .
$PY experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py $A/batch-2/classification.json .
$PY $A/ledger.py $A/batch-1 && $PY $A/ledger.py $A/batch-2
```

All measurements in both batches were (re)produced by the FINAL validator 2.8.1 (F-A1, F-A1b,
F-A3 fixed); every earlier measurement file was regenerated, none was edited.

## 2. Batch 1 — governance repository, `origin/main` @ `5ab500e`

```text
PAIRS_TOTAL                     200 non-merge commits (+2 root commits: NO_PARENT)
DERIVED_TRIGGER_PRESENT          98   rewrite an existing test / validate_* / check_* file
DEFERRED_FROZEN_BASIS_SCAN       83   -> batch 2
MEASURE_ADDED_ACCEPTANCE         17   -> measured, recorded, validated
SCHEMA_V2 (validator 2.8.1)      TASK_CLASS_VERDICT = PASS records=17 valid_requests=15 rejected=2
EXECUTIONS_DISAGREE              0    (measurement vs the validator's own re-execution)
REJECTED                         r08 (af4df6a) BASE_EQUALS_CANDIDATE — its only added acceptance,
                                       validate_project_state.py, fails at both revisions here
                                 r11 (1ca9365) BASE_EQUALS_CANDIDATE — the added test passes
                                       against the unfixed base (it does not observe the change)
```

Per-candidate fields (CASE_ID … EVIDENCE_PATHS) are in `batch-1/ledger.json`.

### 2.1 What the 15 valid requests are — composition (observations, not verdicts)

```text
ORACLE_KIND   BEHAVIORAL 3   r02 (review-evidence interface), r13 (P1-T06 producer trust),
                             r17 (P1-T08 evidence lifecycle) — the deliverable is code the oracle runs
              DOC_TEXT  11   the deliverable is reference text; the oracle reads it with marker
                             groups + anti-vacuity probes (e.g. r15's test mutates each normative
                             sentence and requires the probe to flip)
              DOC_OR_DATA 1  r22 (experiment foundation: a corpus file + docs)
FAMILY        8 of 15 are one family (P1 ticket doc-recipes: r10 r12 r14 r15 r16 r18 r19 r20)
BASIS         all 15 bases are DELTA_ADDED (the historical delta authored its oracle); no
              DELTA_FROZEN basis exists in this batch (see schema §3.3 for why)
EXERCISED     the 14 TEST bases each ran >= 7 tests with 0 skips at the candidate; at the base,
              13 of them fail with AssertionError (the predicate is reached) and r22's fails with
              FileNotFoundError (its deliverable file is absent). r07's basis is a VALIDATOR, whose
              exit code is its only report. No all-skipped PASS anywhere (see F-A2)
```

These matter for Freeze v2, not for Schema v2 — see §4.

## 2b. Batch 2 — the 83 DEFERRED_FROZEN_BASIS_SCAN pairs of batch 1's discovery

```text
MEASURED            83   every surface executed in base / candidate / mutation
NO TRANSITION       75   72 BASE_EQUALS_CANDIDATE with no bite, 3 NO_ACCEPTANCE (no scripts/ tree)
SUPPORTED            7   -> records r24-r30; plus r23 (825d390) as the named F-A3 negative example
SCHEMA_V2 (2.8.1)        TASK_CLASS_VERDICT = PASS records=8 valid_requests=7 rejected=1
A_REPAIR, FROZEN    r24 4505fae  repairs the t09 byte-budget regression introduced by 825d390
  basis (2)                       ("repair round 2" of a review cycle)
                    r27 7cadc9c  restores t09 after 95667e8 broke it
                    oracle = scripts/tests/test_p1_t09_bootstrap_byte_budget.py, DELTA_FROZEN, i.e.
                    FRAMEWORK_FROZEN: red at the base (AssertionError, 24 tests run), green at the
                    candidate, and the worker's delta is one doc file. These are the only true
                    "real regression, frozen oracle" repairs in the repository's history.
B_REGRESSION_GUARD  r25 r26 r28 r29 r30 — EVERY bite is `markdown-links-resolve`
  (5)                (validate_governance.py; test_p1_t16 fails because it runs the same validator
                    in a scratch copy): the delta adds a document and edits others to link it, so
                    removing it leaves a dangling link. A real guard, but a SHALLOW one: it proves
                    the linked file exists, nothing about its content (batch-2/bite-diagnosis.json)
REJECTED            r23 (825d390) — it adds nothing and breaks t09; 2.8.0 accepted it as a
                    B_REGRESSION_GUARD (F-A3)
```

## 3. Findings raised by real candidates (fact → reproducer → severity → fix → falsification)

```text
F-A1   P1  (validator 2.8.0; fixed in 2.8.1)
       FACT        the controlled mutation unlinked added files but left them in git's index; an
                   acceptance that enumerates `git ls-files` crashed, and the crash counted as a BITE
       REPRODUCER  0007bb3 (r22): test_p1_t16_gate_cli_entrypoint.py rc=1 FileNotFoundError under
                   the unlink mutation, rc=0 under an index-consistent one; a B_REGRESSION_GUARD
                   request for r22 is ACCEPTED by 2.8.0 (see SEVERITY line)
       SEVERITY    P1 — erroneously accepts a candidate; latent until the corpus grew (this stage)
                   (output: negative-controls/nc-r22-launder-B.under-2.8.0.txt vs .under-2.8.1.txt)
       CATEGORY    any surface that reads git's index or HEAD; at main two call `git ls-files`
                   directly (test_p1_t16 and the frozen validate_public_release.py, which other
                   surfaces reference) — a class, not the one demonstrated test
       FIX         mutation = committed revision (git rm + commit, tree must be clean); `-z` paths
       REGRESSION  MutationMaterialisation (4 tests) incl. a positive control that a real
                   dependency on an added file still bites
F-A1b  P1  (introduced by the first 2.8.1 draft; caught before commit by re-measurement)
       FACT        committing under a synthetic identity made validate_governance.py's HEAD-identity
                   check (4b) fail in every mutation -> 15/17 pairs "bit"
       FIX         the mutation commit carries the candidate's author/committer/dates/message
       REGRESSION  test_a_head_metadata_surface_does_not_bite_on_the_mutation_commit (fails on the
                   draft, passes on the fix)
F-A1c  P2  non-ASCII added paths were quoted by `git diff --name-only` and silently not removed
           (mutation kept the addition). Fixed with -z; regression test_a_non_ascii_added_path_...
F-A3   P1  (validator 2.8.0 and the 2.8.1 draft; fixed in 2.8.1)
       FACT        a bite required green at the base and red under the mutation, not green at the
                   CANDIDATE; with no added path the mutation IS the candidate
       REPRODUCER  825d390 (r23) adds nothing and breaks t09 (rc 0/1/1); a B_REGRESSION_GUARD
                   request for it is ACCEPTED by 2.8.0 (negative-controls/nc-r23-launder-B.under-2.8.0.txt)
       FIX         bite = base green AND candidate green AND mutation red AND >= 1 added path
       REGRESSION  test_a_candidate_that_breaks_a_guard_is_not_a_bite (red before, green after)
F-A2   P3  (latent; not observed) the validator reads exit codes only, so an all-skipped unittest
           module would read as PASS. Not observed on any basis (probe: 0 skips everywhere).
           Mitigation here: probe_basis.py evidence per record. Left out of the validator: no real
           case exercises it, and the stop rule says record, don't polish.
N2.1 P3-A / P3-B   closed while touching the same files (see eligibility-schema-v2.md §6.7).
```

## 4. What Freeze v2 must still decide or measure (Schema v2 cannot)

```text
FZ-ADM-1 TASK_TEXT <-> ORACLE ALIGNMENT  The DOC_TEXT oracles check specific marker groups. A
         worker that sees only a paraphrased task text cannot hit them, so both arms would fail
         and the task carries no signal. Freeze v2 must materialise each task's text from its
         ticket/issue and check that every literal the oracle requires is derivable from it — or
         not select the task. (Not enforced anywhere today.)
         MEASURED on r15 (dc7aef6, ticket = Issue #23, 7,976 chars, read-only via `gh issue view`):
         63 of the oracle's 241 string literals occur verbatim in the ticket body, and the heading
         the oracle locates the recipe by — `### 5.2 破坏性工作区事务（DESTRUCTIVE_WORKSPACE_TRANSACTION）`
         — does not. A crude literal count (many literals are code, not required text), but enough
         to show the hazard is real for this family, not hypothetical.
FZ-ADM-2 FAMILY CONCENTRATION  8/15 valid requests are one doc-recipe family; selecting six from
         them would measure one task shape. Selection must be stratified (BEHAVIORAL: only 3).
         The 5 B requests (batch 2) are all link-integrity guards: shallow oracles that prove a file
         exists. Usable as B shape only if Freeze v2 accepts that, and they do not count as
         correctness evidence for the deliverable's content.
FZ-ADM-3 DELIVERY ANCHORS (schema §6.4)  pre-/post-delivery acceptance not yet measured for any
         admitted candidate; t01 showed delivery alone can flip a gate. Required per task.
FZ-ADM-4 PER-BASE ROUTE PRECONDITIONS (protocol §10)  the candidate bases (2026-09-05 .. 10-07)
         are not the six bases P6 verified; routes-h2.json must be re-run per selected base.
FZ-ADM-5 ORACLE EXTERNALISATION  every basis is DELTA_ADDED: the run's worker scope must exclude
         the oracle path and the harness must place the frozen candidate blob (sha256 in ledger).
FZ-ADM-6 THE DOMINANT REAL-REPAIR SHAPE IS NOT ADMISSIBLE AS A HISTORICAL PAIR  98/200 commits
         (incl. most `fix(...)` commits) edit an existing test file; Schema v2 derives
         WORKER_MODIFIES_TEST_ORACLE for them. Admitting any of them needs a NEW task identity with
         an externally frozen oracle (the r01 route) — a Freeze-v2 design decision, not a rescue.
FZ-ADM-7 CROSS-REPOSITORY CANDIDATES  zhihu-grabber-toolkit, workbuddy-toolkit and webcodex hold
         real repair history, but Schema v2 can only validate pairs in this object database
         (EXTERNAL_UNVERIFIABLE_LOCALLY never carries a valid request) and the H2 round, routes and
         delivery are governance-scoped (r01: ROUND_SCOPE_DECISION). Scanning them is wasted work
         until that scope decision is made.
```

## 5. Admission total (both batches; governance repository; validator 2.8.1)

```text
SCHEMA_V2_VALID_REQUESTS   22  = 15 (batch 1) + 7 (batch 2)
  A_REPAIR  DELTA_ADDED     15  BEHAVIORAL 3 · DOC_TEXT 11 · DOC_OR_DATA 1 (8 one P1 doc family)
  A_REPAIR  FRAMEWORK_FROZEN 2  r24, r27 — real regressions repaired against a frozen test
  B_REGRESSION_GUARD         5  all link-integrity guards (shallow)
REJECTED (recorded)          3  r08, r11 (BASE_EQUALS_CANDIDATE), r23 (F-A3 example)
H2 PROTOCOL REQUIREMENT     >= 6 real tasks  -> the COUNT requirement is met by Schema v2
WHAT IS NOT YET SHOWN       that >= 6 of them are good H2 tasks: FZ-ADM-1..5 are open. The
                            strongest subset today: r24, r27 (frozen oracle), r02, r13, r17
                            (behavioural) = 5, plus the doc family only if FZ-ADM-1 passes.
STOP RULE FOR ADMISSION     further history search is not needed for the count; it is only
                            worth doing for the BEHAVIORAL / FROZEN strata, and the governance
                            repository has no more of them (batch 1 + batch 2 cover all 200
                            pairs; the 98 trigger-bearing pairs need FZ-ADM-6, a Freeze-v2
                            design decision, not more searching).
```
