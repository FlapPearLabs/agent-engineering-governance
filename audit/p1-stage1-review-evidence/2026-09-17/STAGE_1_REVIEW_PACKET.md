# P1 STAGE 1 — REVIEW PACKET (novelty-first)

Project: `FlapPearLabs/agent-engineering-governance`
Stage: **P1 Stage 1** — `LANE_A = P1-T01 (#10)`, `LANE_B = P1-T04 (#11)`
Stage start main: `8c78e987cbf3007f69876d28c5e3b22ff92c124c`
Final remote main: `0ec774f06882b923fd89b2bb52784538a3367477`
Approved parent spec: `60209cdaf2beeaa718fadcc4028a41c2f0f07db1` (branch `spec/p1-agent-engineering-governance-delta`)

---

## 1. WHAT WE LEARNED THIS ROUND (new information only)

**NEW_CODEGRAPH_FINDINGS = NONE**

**NEW_CONTRACT_FINDINGS = 2**

1. **The frozen `(2)` closure-evidence name list is under-declared in the ticket set.** The approved
   spec renders the REQ-W1-03 `(2)` block with **7** names (the extra one being `TEST_ONLY_CALLERS`)
   while REQ-W1-01's `(2)` block and the P1-T01 ticket body both carry **6**. P1-T01 could not adopt
   the seventh name without *inventing* a frozen identifier, which is exactly what
   `references/ticket-lane.md` `FAIL-CLOSED DUPLICATE_NORMATIVE_DECLARATION` and the ticket's
   `OUT_OF_SCOPE` ("creating new canonical files or a separate seam-map authority surface") forbid.
   Adjudicated `FORWARD_RISK_RECORDED`: this is a **spec self-contradiction**, not a reachable defect
   in P1-T01 today, and it is bound as a **pre-P1-T03 gate**. It is the reason P1-T01 was closed
   conformed-to-its-own-frozen-six rather than conformed-to-the-spec's-seven.

2. **A zero-deleted-lines base advance is a *provable* non-interference certificate.** The strongest
   transferable result of this round is methodological: when a later lane must be re-formed onto a
   moved base, "does the base advance reach my lane?" is not a judgement call. If every intervening
   change is *strictly additive* and the re-formed lane's own blobs are byte-identical, then anchor
   rot and contract-surface interference are both **mechanically excluded**, because the anchors the
   lane cites cannot have been deleted by a change that deleted nothing.

**NEW_COUNTEREXAMPLES**

| # | Owner | Attack | Changed code? |
|---|---|---|---|
| CE-01/02/03/13/14/29/30 | WORKER (Lane A) | seam-partition and single-declaration-point counterexamples | yes (drove the RED) |
| RV-A1b ×3 + 4 new | REVIEWER (Lane A consistency) | document mutations that the first oracle failed to kill | yes — forced repair round 1 |
| RV-B1 F1 | REVIEWER (Lane B adversarial) | anchored `pattern` accepted a SHA with a trailing `\n` | yes — forced repair round 1 |
| RV-B1 N1 | REVIEWER (Lane B adversarial recheck) | `\s`/`\S` still Python-Unicode classes; `subject.repo` with `\uFEFF` falsely accepted | yes — forced repair round 2 |
| RV-B1c | REVIEWER (Lane B adversarial R3) | `[]` / `[^]` composites were not refused and fell through to Python | yes — forced repair round 3 |
| DR-1 ×3 | REVIEWER (independent delta) | blob identity, contribution-patch digest, intersection | no |
| DR-2 ×9 | REVIEWER (adversarial delta) | ref rot, test interference, CLI divergence across SHAs, history rewrite | no |

**NEW_BUGS_FOUND_DURING_REVIEW = 4** (the three Lane B pattern-semantics defects above plus the
Lane A self-referential-oracle defect). All four are repaired and regression-locked; none survives.

**ASSUMPTIONS_INVALIDATED = 1.** "Declaring ECMA-262 semantics in the reference document is equivalent
to implementing them." It is not — see §4.

**NEW_CROSS_MODULE_RISKS = 1.** The two lanes both add files under `scripts/tests/`. A future lane
that adds a third must re-run the collision check; today the module/class names are distinct and the
combined discovery is order-independent (`ORDER_DEPENDENCE = NOT_FOUND`).

**SURPRISES = 2**

- **S-1 (tooling, high value).** In this environment `grep` is a WorkBuddy **brokered shim**, and its
  **BRE alternation is broken**: `grep "A\|B" file` returns nothing and `rc=1` *even when matches
  exist*, while `grep -E "A|B"` and plain single patterns work. This silently produced three false
  negative searches during this stage (including "the repo has no `MASTER_DRIFT` language", which is
  false — it is in `references/git-ci-integration.md` §2). Every closure-evidence search in this
  packet was re-run with `-E`/`-F` or with the built-in search tool after the defect was caught.
  **Never conclude absence from a `\|` grep here.**
- **S-2 (evidence, medium value).** The repository's own `markdown-links-resolve` check only proves
  the *file* exists — it does not resolve the `#fragment`. A dangling `ticket-lane.md#3` inside a JSON
  fixture would have passed the gate. DR-1 closed that gap with an independent anchor resolver.

---

## 2. WHAT CHANGED

**IMPLEMENTATION_DELTA (main `8c78e987..0ec774f`, 7 files, +4211 / −0)**

| Surface | Change | Lane |
|---|---|---|
| `references/ticket-lane.md` | §3 extended: `### 3.1` + `#### 3.1.1`–`#### 3.1.4` | A (97 insertions / **0 deletions**) |
| `scripts/tests/test_seam_contract_partitions.py` | new counterexample suite (919 lines) | A |
| `references/review-evidence.md` | new — sole semantic owner of the Review Evidence contract | B |
| `schemas/review-evidence.schema.json` | new — versioned, closed enums | B |
| `templates/review-evidence.json` | new — conforming placeholder | B |
| `scripts/review_evidence.py` | new — stdlib-only collect/validate CLI, no `commandRef` execution, no network/fs authority | B |
| `scripts/tests/test_review_evidence_contract.py` | new counterexample suite (2545 lines) | B |

**TEST_DELTA.** `scripts/tests` at `8c78e987` → `0ec774f`: +2 test files; combined discovery runs
**85 tests, OK** at the integrated SHA. `adapters/zcode/tests` unchanged at **69 tests, OK**.
Measured split: Lane A file **28**, Lane B file **53**, pre-existing `test_ticket_gate_wiring.py`
**4** → 28 + 53 + 4 = 85. Lane B alone measures 53 both at `8871e646` and at `0ec774f`, confirming the
re-form did not perturb it.

**Lane A — the two labelled partitions.** Partition (1) design/authority carries 33 frozen names
(closed before ticket decomposition); partition (2) closure/observation evidence carries 6 frozen
names (produced after implementation). The partitions share **zero** names. `EXPECTED_PRODUCTION_EFFECT`
has **exactly one** normative declaration point (the partition (1) field list) and appears elsewhere
only by reference. `REACHABILITY_APPLICABILITY = REQUIRED | N/A` is fail-closed on both slots.

**Lane B — the frozen machine contract.** `subject{repo,baseSha,candidateSha}`, `producer`,
`checks[].status = PASS|FAIL|SKIPPED|ERROR|UNKNOWN`, `ci.originalState` = the existing
seven-value CI set (**not** a second CI state machine), `grounding.mode`, `seams` (`oneOf`
REQUIRED / N/A), `reuse` descriptor
(`WHAT` / `IDENTITY_VERSION_OR_DIGEST` / `VALID_FOR` / `INVALIDATED_BY` /
`VERIFICATION_STATE = VERIFIED|UNKNOWN`), `unverified[]`, and three orthogonal axes
`STRUCTURALLY_VALID = YES|NO` / `SOURCE_VERIFICATION_STATE = VERIFIED|INVALID|TEMPORARILY_UNAVAILABLE|NOT_VERIFIED` /
`EVIDENCE_SUFFICIENCY = SUFFICIENT|INSUFFICIENT` with `INSUFFICIENT` confined to the sufficiency axis.
All members are **byte-identical to the approved spec**.

---

## 3. GATES

```
EXACT_SHA            LANE_A e1da1541eb2b11f1e44f972409abde701496f4b6
                     LANE_B 0ec774f06882b923fd89b2bb52784538a3367477
CODEGRAPH            initialised once per directory; incremental sync; no per-ticket rebuild
TDD                  RED captured before GREEN on both lanes; RED failed on contract absence,
                     not harness breakage
TESTS                scripts/tests 85 OK · adapters/zcode/tests 69 OK  (LOCAL; != REAL CI)
CODE_REVIEW          LANE_A L1 + DUAL INDEPENDENT PASS (RV-A1c contract + RV-A1b consistency)
                     LANE_B L1 adversarial + DUAL INDEPENDENT PASS (RV-B1d + RV-B2b)
                     then DUAL INDEPENDENT DELTA REVIEW after re-form (DR-1 + DR-2), both PASS
REPAIR_ROUNDS        LANE_A 1 · LANE_B 3 (third authorised by CONVERGENCE_ARBITER, single commit)
PR_CI                LANE_A 35191793461 success @ e1da1541
                     LANE_B 35192312691 success @ 0ec774f (branch)
POST_CI_REVIEW       main push 35194686693 success @ 0ec774f (all steps green)
```

All nine local gates green at the integrated SHA: `validate_governance.py` 31/31,
`validate_project_state.py` 16/16, `scripts/tests` 85 OK, `adapters/zcode/tests` 69 OK,
`validate_public_release.py` tree `VIOLATIONS=0` / commit-metadata `VIOLATIONS=0` / selftest 51/51,
`git diff --check` clean.

**Non-PASS CI state, declared honestly (`git-ci-integration.md` §3.1).**

```
CI_STATE                     = NOT_TRIGGERED
CI_TRIGGERED                 = NO
CI_RUN_ID_OR_URL             = N/A
CI_OBSERVED_AT               = 2026-09-17T07:28Z
CI_FAILURE_SIGNATURE         = N/A
RETRY_PERFORMED              = NO
CI_BLOCKER_CLASS             = SCHEDULING   (path filter; not a failure)
WORKER_CLASSIFICATION        = PROPOSAL_ONLY
REVIEWER_ACCEPTED_CLASSIFICATION = PENDING
REQUIRED_NEXT_ACTION         = none required for this candidate; governance-ci (the per-push
                               gate) ran and passed on the exact SHA.
```

`public-release-audit` did not fire because its path filter watches
`scripts/validate_public_release.py`, `scripts/validate_governance.py`,
`.github/workflows/public-release-audit.yml`, `deployment/**`, `audit/**` — none of which this stage
touches. `NOT_TRIGGERED` is **not** PASS and is not being reported as one.

---

## 4. FULL HISTORY OF THE `ECMA-262` DEFECT CLASS (why three repair rounds were justified)

The Lane B contract validates a JSON Schema whose `pattern` keywords are **ECMA-262** regexes, but
the implementation is Python `re`. The reference document *declared* ECMA-262 semantics; the code
did not have them. Three distinct, sequentially-discovered members of this class:

| Round | Defect | Reachability | Fix |
|---|---|---|---|
| R1 | `re.search` with anchored patterns let `\n`-suffixed SHA pass | PRODUCIBLE | `$`→`\Z`, `\d`→`[0-9]`, subject enforcement fail-closed |
| R2 | `\s`/`\S` still Python Unicode classes → `subject.repo` with `\uFEFF` accepted | PRODUCIBLE | full emulation from V8-derived class bodies; fail-closed `SCHEMA_KEYWORD_UNSUPPORTED` |
| R3 | `[]` / `[^]` composites not refused; fell through to Python (POSIX leading-`]` rule) | SYNTHETIC-then-argued | `[]`→`(?!)`, `[^]`→refused; 0 class-oracle mismatches over the 302-pair corpus + exhaustive BMP scans |

Round 3 was initially argued **not reachable**. `CONVERGENCE_ARBITER` overrode that, on the ground
that a *silent Python fallback* violates the lane's own declared fail-closed boundary even when the
input is synthetic — i.e. `REACHABILITY` is not the only repair trigger when the defect class is
"contract declares X, code does Y". Bounded to a single commit, which was respected.

---

## 5. DECISION

```
UNRESOLVED_P0 = NONE
UNRESOLVED_P1 = NONE
READY_FOR_EXTERNAL_REVIEW = N/A (no external/manual review was required by this stage's gate set)
HIGH_VALUE_BLOCKER_REMAINS = NO  (both lanes, per two independent reviewers each)
STAGE_1 = COMPLETE
TICKET_10 = CLOSED (COMPLETED)
TICKET_11 = CLOSED (COMPLETED)
NEW_FRONTIER = 9 tickets: #12 P1-T09, #13 P1-T13, #14 P1-T14, #15 P1-T15,
               #16 P1-T02, #17 P1-T03, #18 P1-T05, #19 P1-T07, #20 P1-T12
STILL_BLOCKED = #21 P1-T06 (#18), #22 P1-T10 (#19), #23 P1-T11 (#17),
                #24 P1-T08 (#21,#23), #25 P1-T16 (#12,#24)
NEXT_LEGAL_ACTION = AWAIT_OWNER_STAGE_2_PLAN_AND_AUTHORIZATION
```

**Carry-forward obligations (recorded, not silently dropped):**

1. **Pre-P1-T03 gate — spec `(2)`-block self-contradiction.** The 7th name `TEST_ONLY_CALLERS` must be
   resolved (spec fix, or explicit owner parking) *before* P1-T03 works the closure-evidence block.
2. **Stage 2 planning must re-audit frontier write-surface disjointness.** The 9-ticket frontier has
   **not** been re-checked for pairwise disjointness at the new main; the six shared write chains
   recorded for Stage 1 were computed against the old base.
3. **State flush is prepared but NOT integrated.** `state/p1-stage1-flush-20260917` @ `4f4fe4a1`
   (parent = main `0ec774f`) is pushed with green CI. Repo policy forbids direct master construction,
   so merging it is an **owner decision**, exactly as the previous flush was.
4. **CI classification acceptance.** `public-release-audit`'s `NOT_TRIGGERED` is a worker proposal
   (`PROPOSAL_ONLY`); it has not been accepted by an independent reviewer.
