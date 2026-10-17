# H2 Candidate Admission — CLOSURE REPORT

> Append-only closure record of the Candidate Admission sub-stage of N2 (after N2.1, before Freeze v2).
> The reviewed artefact SHA is fixed below; this file's own commit SHA is not written here.

```text
REPO                 = FlapPearLabs/agent-engineering-governance
BRANCH               = experiment/v1.2-h2-freeze-v2
STAGE_BASE           = f4eb50370f7edbad03451b73affc6db4bb379a92   (N2.1 closure; stacked on PR #55 @ 1b82a53)
FINAL_REVIEW_SHA     = 1e8ac1fefeab28d694c47db7da18756e3ed7dd6e   (validator 2.8.7)
FINAL_REVIEW_ROUND   = 7
FINAL_REVIEW_VERDICT = PASS   P0=0 P1=0 P2=0 P3=5
ADMISSION_STATUS     = CLOSED

RESULT
  SCHEMA_V2_VALID_REQUESTS = 23   (batch 1: 15, batch 2: 5, batch 3: 3)  >= 6 required: COUNT MET
  REJECTED_RECORDS         = 5    (r08 r11 BASE_EQUALS_CANDIDATE; r23 r26 r29 CANDIDATE_REGRESSES_A_FROZEN_GUARD)
  COVERAGE                 = all 198 non-merge pairs + 25 merges of main @ 5ab500e routed; 111 executed
  EXECUTIONS_DISAGREE      = 0;  all 111 measurements stamped with the committed validator's sha256
  NEGATIVE_CONTROLS        = ALL_REFUSED_BY_CURRENT (earlier validators loaded from git accept them)
  TASK QUALITY             = NOT YET SHOWN: strongest stratum (BEHAVIORAL r02 r13 r17 + FRAMEWORK_FROZEN
                             r24) = 4 < 6; DOC_TEXT family needs FZ-ADM-1; B requests are link guards

REVIEW HISTORY (each round a fresh, independent reviewer at an exact SHA)
  R1 4add2ca  CHANGES_REQUIRED  1xP1 4xP2      (F-A4 merge artefact, F-A5 glob, F-A6, H3 contamination, EVID)
  R2 f2c48a0  CHANGES_REQUIRED  2xP2 3xP3      (F-A7 unmeasured guard, F-A8 deleted guard, F-A9 -z)
  R3 ceb3a72  CHANGES_REQUIRED  1xP2 4xP3      (F-A10 filesystem vs git surface identity)
  R4 6527c81  CHANGES_REQUIRED  1xP1 1xP2 3xP3 (F-A11 import shadow, F-A12 checkout filter; pre-date stage)
  R5 72f0bb4  CHANGES_REQUIRED  2xP1 4xP3      (F-A13 shadow class, F-A14 cross-run rewrite; pre-date stage)
  R6 617ba01  CHANGES_REQUIRED  1xP2 6xP3      (F-A15 carried mode — a 2.8.6 regression); boundary SOUND
  R7 1e8ac1f  PASS              5xP3           boundary SOUND
  Defects found by real candidates before any review: F-A1 (P1), F-A1b (P1), F-A1c (P2), F-A3 (P1).

OPEN P3 (non-blocking; carried into Freeze v2 as its FIRST validator change, under its own review)
  P3-1 2.8.7 un-flagged scripts/tests/__init__.py on a FALSE premise: frozen test_p1_t18 imports
       `scripts.tests.test_p1_t17_...`, which executes scripts/tests/__init__.py. Restore the trigger
       (fail-closed; no routing change in history) and correct §3, §6.7 and the code comment.
       This was the executor's error, recorded as such.
  P3-2 untested 2.8.7 branches: exec-bit identity check, mode-aware provenance (mode-only change ->
       DELTA_MODIFIED), env/-s hardening, deleted-leg mode carry. Add the four tests the review names.
  P3-3 exec-bit check is not portable: under core.fileMode=false a self-chmod is not restored by
       reset (fails closed); on Windows st_mode has no exec bit. Reset with -c core.fileMode=true;
       skip the exec comparison where the platform cannot represent it.
  P3-4 CorpusPairsAreMainHistory selects "local" by label, the validator by resolvability; four
       local candidates are side-branch commits (reachable, base == cand^1, not first-parent chain).
       Select by has_commit; reword §6.6 to "base is the candidate's first parent; candidate
       reachable from main".
  P3-5 stale wording: §3.1 DELTA_FROZEN / SURFACE_BYTES_DIVERGE / "carried byte-identically" omit
       the mode; §3 trigger list predates the 2.8.7 scoping; `__pycache__/` matched as a substring.

BOUNDARY (schema §6.6, assessed SOUND by R6 and R7): the validator executes candidate code and is
  not a sandbox; it targets mis-measurement of real history and record laundering; hostile pairs are
  bounded by the pinned, review-visible corpus. PRECONDITION binding Freeze v2: if the validator is
  ever run on WORKER-produced deltas, the boundary must be re-decided first.

FREEZE V2 INPUTS
  FZ2-1..FZ2-4 (n21-closure-report.md) + FZ-ADM-1..9 (admission/README.md §5) + P3-1..P3-5 above.

UNCHANGED
  Frozen H2 surface (task-registry / scoring-rubric / routes-h2 / protocol / variant-manifest /
  run-plan-r2 / round-2-freeze) and H3's replay/cases.yaml byte-identical to f4eb503.
  No H2-R2 run executed. Nothing merged. main untouched.

TREE_NODES_TOTAL = 19
CURRENT_NODE     = N2 — H2 Lazy Skill / Progressive Disclosure (ACTIVE)
SUBSTATE         = N2.1 CLOSED; Candidate Admission CLOSED; next: Freeze v2
NEXT_NODE        = N2 — Freeze v2 (task selection, materialisation, delivery anchors, run plan)
```
