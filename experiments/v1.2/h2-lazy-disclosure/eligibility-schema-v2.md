# H2 eligibility schema v2 — task classification and acceptance rules

```text
SCHEMA_ID      = ELIGIBILITY_SCHEMA_V2
VERSION        = 2.8.3  (2.0.0 -> … -> 2.8.0; nine review rounds; 2.8.1-2.8.3 = defects raised by real
                 admission candidates and the fresh reviews of 4add2ca and f2c48a0, see §6.7)
STATUS         = PROPOSED / NOT FROZEN
PROPOSED_IN    = N2.1 Eligibility Schema Revision
FROZEN_ONLY_BY = H2-R2 Freeze v2  (this file has no effect on the frozen surface until then)
SUPERSEDES     = the C1–C5 admissibility criteria AS APPLIED in the N2 measurement round
EXTENDS        = ELIGIBILITY_RULE_v2 (task-registry.json#eligibility_rule) — see §7: a task must
                 satisfy BOTH layers; nothing in v2 weakens the earlier rule
MECHANICALLY_ENFORCED_BY = harness/check_task_class.py + experiments/v1.2/tests/test_v1_2_h2_eligibility_v2.py
REVIEW_HISTORY = round 9 (commit 75c77ff) returned PASS with ONE P2 that this revision closes:
                 the validator checked a self-authored record's internal consistency, so a
                 five-field edit of the shipped r06 record formed `valid_requests=1` without
                 falsifying anything — r06 is the one corpus pair whose delta touches no test and
                 no validator, so NO trigger was derived and the trigger that actually rejected it
                 was erasable. The fix is not a declaration: the class claim is a STATE TRANSITION
                 claim, so the transition is now RECOMPUTED BY EXECUTION (§3.1, §6.6).
                 Round 5 (commit 269b263) returned PASS: the per-case pin holds in its
                 category-level form — re-attempting the round-4 attack on r05, r02 and a newly
                 added sixth case each forced a second file to move, so validator and suite cannot
                 agree without a review-visible edit. Its five findings were P3 (two mechanical
                 gaps, three documentation defects) and are closed in the version after it.
                 Round 4 (commit 41c6598) returned CHANGES_REQUIRED (no P0) and found that pinning
                 only the corpus digest fixed the demonstrated case and not the class: r02, r05 and
                 any future case stayed unguarded. Fixed by pinning the per-case pairs of all five
                 cases as literals in the test file.
                 Round 5's five findings were P3 and are closed in the version after it, as are
                 the two P3 defects the closing review found in THOSE fixes: a disclosure check that
                 sat after a declaration short-circuit (dead for the shape that needs it) and an
                 own-class rule that matched a name but not its verdict.
                 Round 1 (commit ea268dd) returned CHANGES_REQUIRED (2xP1, no P0): the validator
                 judged only self-consistency while §6.5 claimed a structural proof. Round 2
                 (commit 5aa079f) returned CHANGES_REQUIRED again and was right once more: the
                 revision pair was not bound to the record's IDENTITY, so a six-field edit of the
                 shipped r03 record — borrowing its real, local, ancestor-related pair — was still
                 counted as an admission. v2.2.0 fixes that: identity is bound to the replay corpus,
                 two triggers are DERIVED from the delta's own file list, a valid request requires a
                 locally verifiable pair, and the verdict vocabulary no longer says 'admitted' at
                 all — this program validates a REQUEST and never grants one.
                 Round 3 (commit e1d04e2) returned CHANGES_REQUIRED (no P0) and found that
                 round 2's identity rule rested on an UNPINNED file: the replay corpus was in no
                 freeze hash and no test pinned its SHA values, so a corpus edit made the
                 identity binding vacuous. v2.3.0 pins the corpus digest as a literal in the
                 validator (asserted by a test), binds source_repository per case, forbids two
                 records over one case, requires schema_version to equal the implemented
                 version, and scopes evidence citations to the repository.
MACHINE_READABLE_RECORDS = task-classification-v2.json
EVIDENCE       = precondition/n2-eligibility-measurement.md, precondition/n2-c2c3-gap-analysis.md,
                 precondition/n2-vacuity-probe.txt, precondition/n2-r0*.txt,
                 precondition/n2-controls-*.txt, precondition/p7-gates.txt
```

> This document lives in the **experiment protocol layer** (`experiments/v1.2/**`), not in
> `docs/`. Rationale: it is a proposal that must be reviewed and frozen through the experimental
> protocol path, and it must not be read as a repository-level (canonical) rule. A promotion to a
> `docs/` surface would be a separate, later decision.

---

## 1. Why the old C2 ∧ C3 is unsuitable for real engineering tasks

### 1.1 The two criteria, read formally

For a task T (base B, delta D) and an acceptance command G (deterministic: tree → {PASS, FAIL}):

```text
C2(G,T) := G(B) = PASS                    "the acceptance is green at the frozen base"
C3(G,T) := the acceptance distinguishes PASS from FAIL after the worker changes the target
```

C3 as written admits two readings, and the difference is not cosmetic:

```text
reading (i)  verdict moves relative to the base:   G(B+D) ≠ G(B)
reading (ii) the acceptance can tell a correct deliverable from an incorrect one
```

**Reading (i) makes C2 ∧ C3 self-contradictory**: it demands `G(B) = PASS` *and* `G(B+D) ≠ PASS`,
i.e. it demands that the *correct* delta turn a green gate red — that is a requirement that the
repair be a regression. A rule that is only satisfiable by a regression is not a strict rule; it is
an unusable one. v2 therefore fixes the ambiguity: **reading (ii) is the intended meaning**, and
"verdict moves relative to the base" is demoted to *one* admissible class's lifecycle (A_REPAIR),
not a universal requirement.

### 1.2 What the criteria actually assume

C1–C5 silently assume that **one** acceptance object exists which is simultaneously
(a) green at the base, (b) unwritable by the worker, (c) sensitive to the delta. The three measured
replay candidates break **different** conjuncts, which is why no single patch to C2 rescues them:

| candidate | archetype | broken conjunct | measured mechanism |
|---|---|---|---|
| r01 | repair task | **(a) green at base** | base oracle FAIL by design: 509 tests / 508 pass / the single failing entry is the task's target file (`ERR_MODULE_NOT_FOUND: lib/pre-synthesis-guard.mjs`); candidate 539/539 |
| r03 | regression guard / validator task | **(b) unwritable by the worker** | the verdict-producing bytes are the deliverables (`ruff.toml`, the t17 semantics test); the delta also mutates `scripts/validate_governance.py` (check count 32 → 34), and the base-green gates show *zero* verdict movement (32/32 → 34/34, 423 → 441 tests, both OK) |
| r06 | coverage gap task | **(c) sensitive to the delta** | the delta adds eight files and the only era gate reports 23/23 both before and after, item-for-item identical |

Proof that patching only C2 is insufficient: relaxing C2 admits r01 *only*; r03 still fails on
oracle authorship and r06 still fails on observability. Three axes have to move together.

### 1.3 Why that makes it unusable as a benchmark, not merely inconvenient

A benchmark whose admissibility rule admits only "invariant" tasks while excluding every real
engineering change **mis-measures the thing it claims to measure**. The H2 question is whether
progressive disclosure preserves *task correctness*; real tasks are overwhelmingly repairs,
guards and gap-closures. An admissibility rule that only admits tasks whose acceptance was already
green cannot express "did the worker fix the defect", so it ends up measuring "did the worker
avoid breaking anything", which is a different (and much weaker) claim.

The inverse failure is worse and is measured here: when the rule *is* stretched to admit such
tasks without the authoring and coverage constraints, the acceptance becomes satisfiable without
the work — `ruff check .` reports **"All checks passed" (rc=0)** under `select = []` on the r03
tree, and under `select = ["F841"]` the framework-owned single-specimen probe **passes** while the
gate is hollowed.

---

## 2. Task classification

```text
CLASS A — REPAIR TASK
  definition : a real defect repair against a frozen oracle
  lifecycle  : baseline  { oracle_status: FAIL }
               candidate { oracle_status: PASS }
  required   : baseline_oracle_status      = FAIL         (declared by the record; NOT recomputed
                                                             by the validator — see §6.6)
               candidate_oracle_status     = PASS         (declared; NOT recomputed)
               oracle_in_worker_scope      = false
               oracle_authority            ∈ { FRAMEWORK_FROZEN, PENDING_FREEZE_V2 }
                                            (PENDING blocks round admission and requires an
                                             ORACLE_EXTERNALIZATION pending requirement)

CLASS B — REGRESSION GUARD TASK
  definition : verification of a protective capability against mutations
  lifecycle  : baseline  { oracle_status: PASS }
               mutation  { oracle_status: FAIL }
  required   : baseline_oracle_status               = PASS
               mutation_oracle_status              = FAIL
               mutation_touches_target_predicate   = true   (a mutation that fails for an
                                                             unrelated reason proves nothing)
               acceptance_surface_frozen           = true
               validator_not_worker_controlled     = true

CLASS C — REJECT
  definition : not admissible under any class; carries enumerated triggers + the blocked-class
               reasoning (a task may not be dumped here unexamined)
```

A task may be considered under more than one class (`class_considered` records each with its
verdict and, for rejected ones, the blocking condition). The classification is a property of the
**proposed task design**, not of a historical commit: the replay supplies the observed oracle
statuses, and everything not yet materialised is listed in `pending_requirements`.

---

## 3. Acceptance rule per class

```text
FOR EVERY CLASS
  · IDENTITY: the record names the replay-corpus case it classifies and carries THAT case's
    revision pair; the pair is read from cases.yaml, never taken from the record
  · DERIVED TRIGGERS: the delta's own changed-file list is read from the object database — every
    REWRITTEN test file derives WORKER_MODIFIES_TEST_ORACLE and every REWRITTEN validate_*/check_*
    file derives WORKER_MODIFIES_VALIDATOR; each must be declared or its paths externalised.
    ADDED paths derive nothing: a newly added acceptance cannot neuter an oracle that already
    existed, and it is held to §3.1 instead (it must demonstrably fail against the unfixed base)
  · THE TRANSITION IS RECOMPUTED BY EXECUTION (§3.1). Nothing the record declares substitutes it:
    the declared lifecycle statuses are BOUND to the measured verdicts, and an admissible claim
    whose transition cannot be computed fails closed
  · the acceptance is decided by bytes that are NOT part of the worker's delta              (R3/R4/R5)
  · the acceptance names its oracle explicitly, and the oracle's authority is DERIVED from the
    acceptance provenance, not chosen by the record                                          (R4)
  · a valid REQUEST is never implicit and is never an admission: it requires an admissible class,
    zero triggers, zero pending requirements, a fully materialised oracle authority, and a
    locally verifiable revision pair — and the GRANT is the round freeze plus review          (R7)
  · every record carries measured evidence (claim / measured / source)                      (R8)

### 3.1 The recomputed transition

```text
ACCEPTANCE := the CANDIDATE revision's own acceptance surfaces, discovered from that tree by the
              repository's own path conventions (scripts/validate_*.py, scripts/tests/test_*.py).
              They are carried byte-identically into the base tree, so the BASE verdict cannot be
              produced by editing the acceptance between the two runs.

STATES := base tree · candidate tree · CONTROLLED MUTATION (the candidate tree with every path the
          delta ADDS removed — modified paths keep their candidate content, because reverting them
          wholesale would rebuild the base tree and make the mutation a no-op by construction)

PROVENANCE (recomputed from the object database, per surface)
  DELTA_FROZEN    identical bytes at both revisions
  DELTA_ADDED     the delta introduces it
  DELTA_MODIFIED  the delta rewrites it        <- NEVER a basis: the delta rewrote the thing that
                                                  judges it, which is the shape every vacuity
                                                  attack takes (`select = []` on r03 is this shape)

DERIVED
  A_REPAIR           supported  <=>  some DELTA_FROZEN or DELTA_ADDED surface reports FAIL at the
                                     base and PASS at the candidate
  B_REGRESSION_GUARD supported  <=>  some DELTA_FROZEN surface is GREEN at the base and RED under
                                     the controlled mutation
  otherwise                      =>  REQUEST_VALID is forbidden (fail closed): BASE_EQUALS_CANDIDATE
                                     when nothing moves, NO_DISCRIMINATING_ACCEPTANCE when surfaces
                                     move but not in the claimed direction, NO_ACCEPTANCE when the
                                     candidate ships none, or the materialisation error

BOUND (the declared value must equal the measured one; a disagreement is an error)
  baseline_oracle_status · candidate_oracle_status · mutation_oracle_status ·
  oracle_in_worker_scope · acceptance_surface_frozen · mutation_touches_target_predicate ·
  oracle_authority (FRAMEWORK_FROZEN for a DELTA_FROZEN basis; DELTA_AUTHORED_DISCRIMINATING for
  a DELTA_ADDED one)
```

A missing, unrunnable, timed-out or uncomputable acceptance is never a pass.

### 3.2 The classes, in terms of it

```text
CLASS A  (repair)
  the acceptance must be RED at the base and GREEN at the candidate — recomputed, and reported
  with the surface that carried it and that surface's provenance. The single failing identity at
  the base must be the task's declared target, not an unrelated defect and not an artefact
  introduced by the experiment's own delivery (see §6.4).

CLASS B  (regression guard)
  the framework owns the specimen battery and the harness that applies it; the deliverable may be
  READ by that harness but must not be part of it. The acceptance requires BOTH verdicts:
  compliant specimen → the deliverable's guard must pass; violating specimen → it must fail.
  A single specimen proves only that specimen (§6.3). In the transition vocabulary: a FROZEN
  acceptance must be green at the base and red under the controlled mutation.

CLASS C  (reject)
  every admissible class must be listed as BLOCKED with a non-empty reason, and at least one
  enumerated trigger code must be present with a reason_code (format-checked UPPER_SNAKE, not a
  closed vocabulary — the code names the evidence, it does not classify it) and a detail.
```

### 3.3 Why the recomputation has the shape it has (measured)

Every corpus pair was measured in all three states. The result is the reason A_REPAIR cannot be
expressed with a strictly frozen acceptance:

```text
r02  base e1da1541 → cand 2ed08f6f    scripts/tests/test_review_evidence_contract.py  DELTA_ADDED
                                       base_rc=1  cand_rc=0    <- a real repair
r03  base 015780be → cand 65113de6    scripts/tests/test_p1_t17_...                  DELTA_ADDED
                                       base_rc=1  cand_rc=0
                                      scripts/validate_governance.py                DELTA_MODIFIED
                                       base_rc=1  cand_rc=0    <- excluded, see below
r05  base c08f6f8b → cand 6d841d56    18 FROZEN tests, all unchanged verdicts       no transition
r06  base af4df6ae → cand 069f8be2    2 FROZEN validators, both unchanged            no transition
```

A FROZEN acceptance exists identically at both revisions, so on a landed pair it was already green
at the base — which is why every frozen surface above is invariant, and why an A_REPAIR supported
only by frozen acceptances has an EMPTY extension over THESE FIVE pairs. (Not over all history:
Candidate Admission found two — r24 / 4505fae and r27 / 7cadc9c repair a t09 regression that the
previous commit introduced, so the frozen test was red at the base.) The acceptance that does move
is the one the fix ships, and r03's second row is exactly why a REWRITTEN one is excluded while an
ADDED one is admissible: rewriting `validate_governance.py` is how the delta took over the thing
that was supposed to judge it.

CLASS C
  every admissible class must be listed as BLOCKED with a non-empty reason, and at least one
  enumerated trigger code must be present with a reason_code (format-checked UPPER_SNAKE, not a
  closed vocabulary — the code names the evidence, it does not classify it) and a detail.
```

---

## 4. Failure cases (all measured; nothing here is hypothetical)

### 4.1 The corpus, reclassified

| id | class | verdict | decisive evidence |
|---|---|---|---|
| r01 | **A_REPAIR** | shape satisfied, **pending materialisation** | baseline FAIL (the only failure is the target file) → candidate PASS (539/539); an externalised oracle was cross-tested: the candidate's test file in the base tree fails, and passes in the candidate tree. Historical delta **did** modify the oracle file → externalisation is mandatory. Round admission: **NOT_ADMITTED** (pending: oracle externalisation, delivery-delta measurement, round-scope decision, Node runtime) |
| r03 | **C_REJECT** | rejected | triggers: `WORKER_MODIFIES_VALIDATOR`, `WORKER_MODIFIES_TEST_ORACLE` (derived from the diff), `ACCEPTANCE_SURFACE_IN_WORKER_SCOPE`, `OBSERVATION_COVERAGE_UNPROVEN` |
| r06 | **C_REJECT** | rejected | trigger: `OBSERVATION_COVERAGE_UNPROVEN` (`NO_GATE_OBSERVES_THE_DELIVERABLE`) |

**No candidate is admitted to the round by this node** (`admitted_to_round=0`). Admission is a
Freeze-v2 decision; the current node may not change the task set.

### 4.2 `ORACLE_SATISFIABLE_WITHOUT_THE_PREDICATE` (vacuity)

On the r03 tree, with `select = []`:
`ruff check .` → **rc=0 "All checks passed!"** — the gate is green and no correctness rule is on.
The framework-owned probe `check_t02_gate_teeth.sh` *does* refuse this configuration
(`T02_POSITIVE_CONTROL = FAIL … GATE_NOT_LOAD_BEARING`). Conclusion: **the linter alone is not an
acceptance; the probe is load-bearing and must be part of it.**

### 4.3 `SPECIMEN_SET_DOES_NOT_COVER_THE_PREDICATE` (narrowing)

With `select = ["F841"]` — narrowed to exactly the rule the probe injects:
`check_t02_gate_teeth.sh` → **rc=0 "T02_POSITIVE_CONTROL = PASS"** and `ruff check .` → rc=0.
The single-specimen probe cannot observe the hollowing. The only artefact that catches it is
`scripts/tests/test_p1_t17_static_gate_framework_semantics.py`
(`test_pinned_toolchain_is_repository_controlled` FAILS) — which is **the worker's own
deliverable**, i.e. self-certification. Conclusion: a CLASS B battery must be **multi-specimen and
sealed against rule-set narrowing**, and the specimen bytes must be framework-owned.

### 4.4 A real semantic defect invisible to both base-green gates

Forcing the state validator (`scripts/validate_project_state.py`) to report every check as passing
— a validator that can no longer fail — leaves the full suite at **441 tests OK** and
`validate_governance.py` at **34/34 passed**. Neither base-green gate notices. "It passes" is not
"it observes".

### 4.5 A frozen oracle does not automatically certify its own candidate

The base version of `adapters/zcode/tests/test_project_continuity.py` run against the r03
candidate tree: **69 tests, 23 errors**. Freezing an oracle is necessary but not sufficient — the
frozen bytes must be cross-tested against the candidate before they are trusted.

### 4.6 Delivery contamination (why §6.4 exists)

The earlier round's t01 was rendered unrunnable by the experiment's own delivery: on a pristine
prepared worktree with **zero worker edits**, the HEAD-era carrier's links raised the task gate
from 1 failure to 4 and the full suite from 1 to 19. Both repair routes were refused by the frozen
scope. The operator's ruling — recorded then and carried into this schema — is that such a
`GREEN→RED` delta must be **measured and attributed**, never normalised into a "pre-existing red"
baseline.

---

## 5. Why this is not a lowering of the standard

The revision **replaces one universal requirement with a class-specific one, and adds three new
requirements**. Per axis:

| axis | old (C1–C5) | v2 | direction |
|---|---|---|---|
| base polarity | must be GREEN, one value | class-specific and **attributed**: A requires FAIL, B requires PASS; the base state must additionally be attributed (an A-class RED caused by the experiment's own delivery is refused, §6.4) | **stricter**: adds attribution; the only relaxation is that a RED base is now *expressible* instead of silently disqualifying |
| oracle authorship | implied, never checked | explicit: FRAMEWORK_FROZEN or PENDING (which blocks admission); worker-authored verdict surfaces are a trigger | **new requirement** |
| observability | implied by "distinguishes PASS/FAIL" | must be proven for the **target predicate**; vacuity and narrowing are enumerated rejection reasons | **new requirement** |
| mutation coverage (B) | absent | the mutation must touch the target predicate, and the battery must survive narrowing | **new requirement** |
| admission | implicit in passing C1–C5 | explicit field; ADMITTED requires clean triggers, zero pending requirements and a materialised oracle authority | **stricter** |
| class discipline | absent | C_REJECT must show which admissible class was blocked and with what reason | **new requirement** |

Two pieces of evidence that this is not a retrofit for existing tasks:

1. **It rejects the one task that the previous round had admitted** — and that claim is now
   mechanical, not prose: `test_v2_rejects_the_registered_task_t02_as_specified` reads the two
   facts from the frozen registry and shows the resulting record being refused. t02's acceptance is
   `ruff check .` plus a single-specimen probe, and its `ruff.toml` is inside the worker's scope
   (scope prefix `ruff.toml`); the registry's "select is non-empty and correctness-class" entry is a
   prose/JUDGMENT entry, not a mechanical one. Under v2 that task carries
   `ACCEPTANCE_SURFACE_IN_WORKER_SCOPE` and `OBSERVATION_COVERAGE_UNPROVEN` for the narrowing
   direction, so it is **not** admissible as currently specified. A schema tailored to admit
   existing tasks would have done the opposite.
2. **It rejects r03 and r06 outright**, even though admitting them would be convenient — r03 is the
   only governance-repo candidate with a rich gate surface, and r06 is the only one with a clean
   pure-addition delta.

The revision therefore buys *expressiveness* (A and B are now describable at all) at the price of
*strictly more conditions*. No task's admission is easier to obtain than before; several are harder.

---

## 6. How benchmark gaming is prevented

### 6.1 The six enumerated rejection triggers

```text
T1 WORKER_MODIFIES_VALIDATOR          the verdict-deciding harness/validator is in the worker's delta
T2 WORKER_MODIFIES_TEST_ORACLE        the test oracle is in the worker's delta
T3 ACCEPTANCE_SURFACE_IN_WORKER_SCOPE the verdict-producing surface is authored by the worker
T4 SELF_PROVING_HASH                  a hash the acceptance relies on is computed from worker-writable bytes
T5 OBSERVATION_COVERAGE_UNPROVEN      no frozen acceptance observes the target predicate
                                      sub-reasons: ORACLE_SATISFIABLE_WITHOUT_THE_PREDICATE,
                                                   SPECIMEN_SET_DOES_NOT_COVER_THE_PREDICATE,
                                                   NO_GATE_OBSERVES_THE_DELIVERABLE
T6 BASE_CANDIDATE_NOT_COMPARABLE      base and candidate are not comparable under one delivery + one oracle
```

A claim of an admissible class carrying **any** trigger is a validator error — the triggers cannot
be "noted and waived". C_REJECT must carry at least one, with a reason code and detail, and must
show which admissible class was blocked.

**Two of the six are not declarable-away.** `WORKER_MODIFIES_TEST_ORACLE` and
`WORKER_MODIFIES_VALIDATOR` are DERIVED by the validator from the revision pair's own
changed-file list (`git diff --name-only`), which is a fact about the object database rather than
an author's statement. A record must declare each derived trigger, or externalise every one of
its paths with the `ORACLE_EXTERNALIZATION` pending requirement — which is why the shipped r03
record had to gain `WORKER_MODIFIES_TEST_ORACLE` when this rule landed (the validator found four
test files the prose had not mentioned).

### 6.2 Why a worker cannot satisfy the acceptance without doing the work

- For CLASS A, the oracle is framework-frozen and outside the worker's scope, so weakening the
  assertions is not available; the failing identity at the base must be the task's target, so an
  unrelated red cannot be substituted.
- For CLASS B, the specimens and the harness that applies them are framework-owned; the deliverable
  is only *read*. A vacuous deliverable fails the compliant/ violating pair, and a narrowed one
  fails the multi-specimen battery.

### 6.3 Battery design rule (learned from §4.3)

A specimen battery must (i) contain at least one specimen per enabled correctness class, (ii) be
non-trivially defeated by narrowing the deliverable's rule selection, and (iii) live in frozen
bytes. A one-specimen probe is a *load-bearingness* hint, not coverage, and must not be recorded as
coverage.

### 6.4 Delivery attribution rule

Both anchors must be measured on the same base with **zero worker edits**: pre-delivery and
post-delivery. `GREEN → RED` under delivery alone is `DELIVERY_CONTAMINATION`, attributed to the
experiment, not to the worker; it blocks admission (it is a `BASE_CANDIDATE_NOT_COMPARABLE` case)
and is recorded, never normalised away. The existing two-anchor implementation is the harness's
delivery-anchor measurement; this schema depends on it rather than re-deriving it.

### 6.5 Rule-change invariant

No rule in this schema may be introduced, relaxed or re-scoped in order to admit a named task.
Three structural properties make that checkable rather than merely declared:

- `PENDING` states **block** admission instead of granting it, so an unmaterialised fact can never
  be counted as a satisfied one;
- the reject class must name the admissible class it blocked, so a task cannot be filed away
  without showing why A and B failed;
- the disclosure ↔ authority binding is mechanical: a record that discloses its historical delta
  touched the oracle may not simultaneously claim the oracle is already framework-frozen, and must
  carry the `ORACLE_EXTERNALIZATION` pending requirement (with that exact code).

### 6.6 Enforcement surface — what this schema enforces, and what it does not

Four adversarial review rounds attacked this schema, and each found the same class of defect: a
control that read a self-authored field and called it a fact. Round 1 demonstrated a hand-written
record counted as an admission; round 2 demonstrated that a record could BORROW a real local pair
from an unrelated case; round 3 demonstrated that the identity root (the replay corpus) was in no
freeze hash and pinned by nothing; round 4 demonstrated that pinning only the corpus digest let an
author edit the corpus and the constant together, leaving cases no fixture covers unprotected.
Each hole is now closed by recomputation or by a pin that a second file has to agree with, and
what remains is stated rather than implied.

```text
RECOMPUTED BY THE VALIDATOR (facts it does not read from the record)
  · IDENTITY — the record's corpus_case_id must name a case in experiments/v1.2/replay/cases.yaml,
    and the record's revision pair AND source repository must EQUAL that case's. This closes the
    laundering route the second review demonstrated: a borrowed pair (or repository) no longer
    matches the borrowed identity;
  · THE IDENTITY ROOT IS PINNED TWICE — each corpus's sha256 is a literal in the validator (the H3
    replay corpus and, since 2.8.2, the separate admission corpus), and the per-case pairs of ALL
    cases of both are a literal in the test file. Editing a corpus therefore
    means editing two reviewed files, and any case (not only the ones a fixture happens to cover)
    trips the pin;
  · THE STATE TRANSITION (§3.1) — for an admissible claim the candidate revision's own acceptance
    surfaces are executed against materialised base and candidate worktrees, and against a
    controlled mutation; the class is supported only if the measured verdicts move as the class
    claims, and the recomputation is printed so a PASS cannot be attributed to another guard;
  · THE ACCEPTANCE PROVENANCE (DELTA_FROZEN / DELTA_ADDED / DELTA_MODIFIED), recomputed from the
    object database per surface. A REWRITTEN acceptance is never a basis — the delta rewrote the
    thing that judges it — and `oracle_authority` is DERIVED from the basis provenance rather than
    chosen;
  · DERIVED TRIGGERS — the pair's changed-file list is read from the object database; a REWRITTEN
    test file derives WORKER_MODIFIES_TEST_ORACLE and a changed validate_*/check_* file derives
    WORKER_MODIFIES_VALIDATOR. Neither can be talked away INTO A VALID REQUEST: silencing one
    requires externalising every derived path, which requires the ORACLE_EXTERNALIZATION pending
    requirement, which forbids a valid request. A disclosure that CONTRADICTS the derivation is
    refused whatever the record declares — a `historical_delta_touched_validator` of false beside a
    delta that provably changes a validator is an error even when the derived trigger is declared
    (the check runs before the declaration short-circuit);
  · REVISION BINDING — a pair this repository contains is resolved with `git cat-file`; a claim of
    an admissible class additionally requires the candidate to descend from the base
    (`git merge-base --is-ancestor`) and the pair to be non-degenerate (base != candidate);
  · a pair that does not resolve here must be declared EXTERNAL_UNVERIFIABLE_LOCALLY with a named
    repository and the external verification command, and it can never carry a valid request;
  · every evidence[].source must resolve to an existing file INSIDE the repository;
  · a record may not list its OWN class as BLOCKED, and `class_considered` must name the record's
    own class under an AFFIRMATIVE verdict from a closed two-value vocabulary (for admissible
    claims — a C_REJECT lists the admissible classes it blocked, and the reject class is the outcome
    rather than an option considered). The vocabulary is closed because an open one let a synonym
    ("NOT_APPLICABLE") stand in for "blocked";
  · a non-object `disclosures` is a structured error rather than a traceback, and the
    disclosure-cross-check runs on BOTH derived axes — a false `historical_delta_touched_oracle`
    beside a delta that provably changes test files is an error exactly as the validator axis is;
  · the closed vocabularies, the per-class field equalities, the trigger/class consistency, the
    disclosure-to-authority binding, the C_REJECT "show which class you blocked" rule, the exact
    pending-code match, and the structural rules (unique ids, required schema_version, malformed
    records as structured errors, no early return that masks a record's other defects).

NOT ENFORCED — out-of-band obligations, named so that a PASS is not mistaken for a proof
  · (2.7.0 said the lifecycle statuses were "never recomputed". That stopped being true in 2.8.0:
    they are recomputed by execution, and a declared value that disagrees is an error. What is
    STILL not recomputed is whether the acceptance's own semantics are sound — a DELTA_ADDED
    acceptance can be SHALLOW (`assert Path("newfile").exists()` fails against the base and passes
    at the candidate, which is a true lifecycle and a weak oracle) — that is the human review's
    job, and it is the reason the grant is the round freeze plus review rather than this program;
  · whether a DELTA_ADDED acceptance belongs in the frozen surface at all is a decision Freeze v2
    makes when it adopts it; the validator proves it discriminates, not that it deserves freezing;
  · §3.2's "the single failing identity at the base must be the task's declared target" is NOT
    implemented: the recomputation proves the acceptance MOVES, not that its failure at the base is
    the task's own subject rather than an unrelated defect or a delivery artefact. That judgement
    is the reviewer's, and it is named here so the clause is not read as enforced;
  · for an externally bound pair the derived-trigger rule cannot run at all (the diff is not in this
    object database) — one more reason such a record cannot carry a valid request;
  · the derived-trigger rules are NAME-based (tests?/, .test., test_*.py, validate_*.py,
    check_*.sh|py) and therefore know nothing about ROLE: a file that validates without matching
    those names derives nothing. The corpus contains one — r02's scripts/review_evidence.py, a
    collect/validate CLI — and any task whose verdict hangs on such a file must declare the trigger
    by hand. A role-aware rule would need a declared manifest, which is not in scope here;
  · externalisation that silences a derived trigger is an ASSERTION, bounded only by the fact that
    the same pending requirement forbids a valid request; `externalized_paths` entries must exist
    in the delta WHEN THE PAIR RESOLVES HERE — for an externally bound pair the delta cannot be read
    at all, so the check is skipped and only the "no valid request" rule bounds it; nothing proves
    the externalisation happened in either case;
  · the record's CLASS is bound to the recomputed transition but to nothing beyond it: the
    program proves the pair's acceptance moves as the class claims; nothing in the repository says
    a given change WAS a repair. The corpus's own per-case dispositions are deliberately not
    consulted, because the corpus header forbids collapsing those axes;
  · nothing compels a pending requirement to be discharged: a candidate may sit in NOT_ADMITTED
    indefinitely. That is a liveness limit, not a soundness one, and it is the conservative
    direction;
  · ancestry is deliberately NOT required of C_REJECT: a non-comparable pair is a legitimate reason
    to reject, so the check applies to admissible claims only;
  · the validator is NOT yet wired into prepare/collect/publish: nothing in the run pipeline
    consults it. Freeze v2 must decide whether it becomes a gate or stays an operator tool.

THE CONSEQUENCE, STATED PLAINLY: a PASS means "internally consistent AND consistent with every fact
this repository can recompute — the corpus identity, the delta's own file list, the revision
graph, and the reachability of the cited evidence". It is NOT a statement that the declared oracle
statuses are true. This is why `round_admission.verdict` has no "admitted" value: the program
validates a REQUEST, and the grant belongs to the round freeze plus independent review. The limit
is pinned by `test_known_boundary_declared_statuses_are_not_recomputed`. The shape/identity
laundering that motivated v2.2.0 is pinned by the `LaunderingVariants` test class, whose six
variants must stay refused; the RECOMPUTATION-level r06 laundering (round 9) is pinned separately by
`RecomputedTransition.test_r06_laundering_reproduction_is_refused` (N2.1 P3-B corrected the
earlier wording, which credited both to `LaunderingVariants`).

### 6.7 The controlled mutation is a revision (2.8.1–2.8.3 — findings raised by real candidates and fresh reviews)

Found by a real candidate during Candidate Admission, not by a fixture. Up to 2.8.0 the mutation
unlinked the added paths from the working tree and left them in git's index. An acceptance that
enumerates the index (`git ls-files`) then crashes on the missing file, and the crash was counted as
a BITE. Measured on 0007bb3 (whose delta only adds experiment files):
`test_p1_t16_gate_cli_entrypoint.py` rc=1 with `FileNotFoundError` under the unlink mutation, rc=0
under an index-consistent one — so a B_REGRESSION_GUARD claim was "supported" by a frozen surface
that never observes the deliverable. The defect is a category — any surface that reads git's
index or HEAD (at main, `test_p1_t16` and the frozen `validate_public_release.py` call
`git ls-files` directly) — not the one demonstrated test. It was latent only
because no corpus case had that shape yet; admission adds cases, so it had to close first.

```text
2.8.1 (committed at 4add2ca)
  F-A1   the mutation became a committed revision (`git rm` + commit), tree clean afterwards.
  F-A1b  that commit carried the candidate's author/committer/dates/message: under a synthetic
         identity validate_governance.py's HEAD-identity check (4b) bit in every pair.
  F-A1c  added paths read with `-z` (a quoted non-ASCII path named no file and was kept).
  F-A3   a bite requires base = candidate = green and mutation red, and >= 1 added path: 825d390
         adds nothing, breaks test_p1_t09 (0/1/1) and was SUPPORTED as B_REGRESSION_GUARD.
  P3-A   B's candidate_oracle_status no longer folded an unmeasured rc into FAIL.

2.8.2 (fresh adversarial review of 4add2ca: one P1, two P2 in this function)
  F-A4 P1  2.8.1 committed the mutation ON TOP of the candidate: a new single parent, so a PR merge
         stopped being a merge, HEAD^ became the candidate, and the copied message gained a
         newline. Measured on PR #49's merge 6217cc0: the HEAD-identity check bit (0/0/1) and a
         B request was ACCEPTED end to end. 2.8.2 writes the candidate's OWN commit object with
         exactly one change — the `tree` header — so parents, identities, dates, any signature
         header and the message bytes are verbatim (a carried signature no longer verifies;
         stated, not hidden). Postconditions, fail closed: clean tree, parents identical to the
         candidate's, and `git diff <cand> HEAD` is exactly one deletion per added path.
  F-A5 P2  `git rm <path>` read a path as a glob (`docs/[ab].md` also removed docs/a.md):
         2.8.2 runs it with --literal-pathspecs, and the exact-diff postcondition would catch any
         other over-removal.
  F-A6 P2  2.8.1 checked the candidate leg only on the BITING surface: r26 (95667e8) breaks t09
         (0/1/1) while a link guard bit, and was a valid B request. A regression-guard task
         protects a correct state, so 2.8.2 refuses B when ANY frozen surface goes green -> red
         at the candidate (CANDIDATE_REGRESSES_A_FROZEN_GUARD, checked before the bite).
         B's candidate_oracle_status now means exactly that regression (it was FAIL for every B
         record because a surface red at both revisions in this environment counted), and a
         declared value must be PASS or FAIL (UNMEASURED can no longer be declared to match).
  IDENTITY the admission anchors moved out of H3's replay/cases.yaml (restored byte-identical to
         f4eb503) into admission/corpus.yaml, pinned by H2_CORPUS_SHA256; the identity root is the
         union and a case id in both corpora fails closed (finding 4 of the same review: H3's
         loader had counted 24 H2 anchors as detector cases).
2.8.3 (fresh adversarial review of f2c48a0: two P2, three P3)
  F-A7 P2  a base-green guard that HANGS (or is otherwise unmeasurable) at the candidate escaped
         the regression rule: `regressed` needs a measured verdict, and B records do not declare
         candidate_oracle_status, so UNMEASURED was never compared. 2.8.3 refuses B on it
         (CANDIDATE_GUARD_UNMEASURED) — an unmeasured acceptance is never a pass.
  F-A8 P2  acceptance surfaces the delta DELETES were never run (surfaces are discovered from the
         candidate tree; derived_triggers skips status D), so deleting a green guard escaped the
         regression rule. Real case: r29 (5205e5b) deletes test_experiment_v12_foundation.py,
         whose base bytes FAIL against the candidate tree. 2.8.3 runs every base-only surface with
         its base bytes against base and candidate (provenance DELTA_DELETED, reported in
         facts.deleted_surfaces); green -> red counts as a regression. A deleted guard whose
         property still holds at the candidate is a disclosed fact, not a regression.
  F-A9 P3  Repo.changed_paths_with_status read `--name-status` without -z, so a rewritten
         non-ASCII validator came back quoted and derived no trigger (same class as F-A1c).
  P3     postconditions of _materialise_mutation now have a perturbation test (over-removal,
         lost parent) that kills the `return True` mutants; the closed vocabulary has a record test.
REGRESSION (2.8.3)  MutationMaterialisation (15 tests); the four new 2.8.3 tests fail against
         f2c48a0 and pass against 2.8.3; the postcondition test fails against the two surviving
         mutants the review exhibited.
REGRESSION (2.8.2)  MutationMaterialisation (9 tests). Each new test fails against the revision it targets
         and passes against 2.8.2 (the HEAD-metadata test targets the synthetic-identity draft; the
         merge / HEAD^ / glob / other-guard tests fail against 4add2ca). GuardUnitChecks pins both
         corpora and the duplicate-id refusal. Real-pair before/after runs, including loading the
         earlier validators straight from git: admission/negative_controls.py -> report.txt.
Side effect, stated: the mutation commit is an unreachable object in the ODB of the repository the
validator runs in (no ref points to it; `git gc` prunes it).
STILL NOT ENFORCED  a bite proves that a frozen surface depends on SOME added path; it does not
       prove the dependency is the task's target predicate (same limit as §3.2's "single failing
       identity" clause, which stays the reviewer's job). Every B bite admitted so far is the
       markdown link check — a real but shallow guard (admission/README.md).
```

## 7. Relationship to the existing layers

```text
task-registry.json#eligibility_rule (ELIGIBILITY_RULE_v2, frozen)  — entry-kind test:
    TASK_COMPLETION vs BOUNDARY/HYGIENE. Answers "does the registry task declare a mechanical
    completion gate?"  KEPT AS IS; a task must satisfy it too.

ELIGIBILITY_SCHEMA_V2 (this document)                              — acceptance-shape test:
    which lifecycle the acceptance exhibits, who authored it, whether it observes the predicate.
    Answers "is this acceptance admissible?"  A task must satisfy BOTH layers.

protocol.md §5 P7 ("门完整性" / load-bearing proofs)                — the concept this schema reuses.
    P7 already requires injection-must-fail proofs and already declares that ruff's vacuity
    direction is unreliable (#45). v2 generalises the same idea from "the gate" to "the task's
    acceptance" and supplies the missing vacuity/narrowing direction.

protocol.md §9 (freeze semantics)                                  — this document is NOT part of the
    frozen surface; it becomes binding only when H2-R2 Freeze v2 freezes it. Adopting it therefore
    does not invalidate existing runs by itself; the freeze step is where that decision is made.

protocol.md §10 (per-base route preconditions)                     — unchanged; and it is why a
    cross-repository candidate needs an explicit round-scope decision (§4.1, r01).
```

---

## 8. What this node does not do

```text
· does not modify the frozen surface (task-registry / run plan / variant manifest / scoring /
  routes / protocol are byte-identical to the pushed head)
· does not change the task set, the scoring, the routes or the treatment
· does not admit any task to H2-R2 (admitted_to_round = 0)
· does not execute any H2-R2 run
· does not delete or overwrite any earlier measurement record; the measurement evidence is
  ADDED to the repository (precondition/n2-*) with a redaction header and the original sha256
```

**What Freeze v2 must do with it:** freeze this schema (or amend it under review), decide whether
the validator becomes a pipeline gate, materialise the
A/B task designs it requires, clear each candidate's `pending_requirements`, re-measure the
delivery anchors for every task it intends to run, and regenerate the round freeze. Until then,
Round 2 remains NOT_EXECUTABLE.
