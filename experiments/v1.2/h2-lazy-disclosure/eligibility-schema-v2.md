# H2 eligibility schema v2 — task classification and acceptance rules

```text
SCHEMA_ID      = ELIGIBILITY_SCHEMA_V2
VERSION        = 2.5.0  (2.0.0 -> 2.1.0 -> 2.2.0 -> 2.3.0 -> 2.4.0 -> 2.5.0; five review rounds)
STATUS         = PROPOSED / NOT FROZEN
PROPOSED_IN    = N2.1 Eligibility Schema Revision
FROZEN_ONLY_BY = H2-R2 Freeze v2  (this file has no effect on the frozen surface until then)
SUPERSEDES     = the C1–C5 admissibility criteria AS APPLIED in the N2 measurement round
EXTENDS        = ELIGIBILITY_RULE_v2 (task-registry.json#eligibility_rule) — see §7: a task must
                 satisfy BOTH layers; nothing in v2 weakens the earlier rule
MECHANICALLY_ENFORCED_BY = harness/check_task_class.py + experiments/v1.2/tests/test_v1_2_h2_eligibility_v2.py
REVIEW_HISTORY = round 5 (commit 269b263) returned PASS: the per-case pin holds in its
                 category-level form — re-attempting the round-4 attack on r05, r02 and a newly
                 added sixth case each forced a second file to move, so validator and suite cannot
                 agree without a review-visible edit. Its five findings were P3 (two mechanical
                 gaps, three documentation defects) and are closed in the version after it.
                 Round 4 (commit 41c6598) returned CHANGES_REQUIRED (no P0) and found that pinning
                 only the corpus digest fixed the demonstrated case and not the class: r02, r05 and
                 any future case stayed unguarded. Fixed by pinning the per-case pairs of all five
                 cases as literals in the test file.
                 Round 3 (commit e1d04e2) returned CHANGES_REQUIRED (no P0) and found that
                 round 2's identity rule rested on an UNPINNED file — the replay corpus was in no
                 freeze hash and no test pinned its values — so a corpus edit made the binding
                 vacuous. Fixed by pinning the corpus digest as a literal.
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
    changed test file derives WORKER_MODIFIES_TEST_ORACLE and every changed validate_*/check_*
    file derives WORKER_MODIFIES_VALIDATOR; each must be declared or its paths externalised
  · the acceptance is decided by bytes that are NOT part of the worker's delta              (R3/R4/R5)
  · the acceptance names its oracle explicitly, and the oracle's authority is declared      (R4)
  · a valid REQUEST is never implicit and is never an admission: it requires an admissible class,
    zero triggers, zero pending requirements, a fully materialised oracle authority, and a
    locally verifiable revision pair — and the GRANT is the round freeze plus review          (R7)
  · every record carries measured evidence (claim / measured / source)                      (R8)

CLASS A
  the frozen oracle must be RED at the base and GREEN at the candidate, and the single failing
  identity at the base must be the task's declared target — not an unrelated defect and not an
  artefact introduced by the experiment's own delivery (see §6.4)

CLASS B
  the framework owns the specimen battery and the harness that applies it; the deliverable may be
  READ by that harness but must not be part of it. The acceptance requires BOTH verdicts:
  compliant specimen → the deliverable's guard must pass; violating specimen → it must fail.
  A single specimen proves only that specimen (§6.3).

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
  · THE IDENTITY ROOT IS PINNED TWICE — the corpus's sha256 is a literal in the validator, and the
    per-case pairs of ALL five cases are a literal in the test file. Editing the corpus therefore
    means editing two reviewed files, and any case (not only the ones a fixture happens to cover)
    trips the pin;
  · DERIVED TRIGGERS — the pair's changed-file list is read from the object database; a changed
    test file derives WORKER_MODIFIES_TEST_ORACLE and a changed validate_*/check_* file derives
    WORKER_MODIFIES_VALIDATOR. Neither can be talked away by editing the record;
  · REVISION BINDING — a pair this repository contains is resolved with `git cat-file`; a claim of
    an admissible class additionally requires the candidate to descend from the base
    (`git merge-base --is-ancestor`) and the pair to be non-degenerate (base != candidate);
  · a pair that does not resolve here must be declared EXTERNAL_UNVERIFIABLE_LOCALLY with a named
    repository and the external verification command, and it can never carry a valid request;
  · every evidence[].source must resolve to an existing file;
  · the closed vocabularies, the per-class field equalities, the trigger/class consistency, the
    disclosure-to-authority binding, the C_REJECT "show which class you blocked" rule, the exact
    pending-code match, and the structural rules (unique ids, required schema_version, malformed
    records as structured errors, no early return that masks a record's other defects).

NOT ENFORCED — out-of-band obligations, named so that a PASS is not mistaken for a proof
  · the TRUTH of baseline_oracle_status / mutation_oracle_status is never recomputed: this program
    cannot re-run a candidate's oracle. A record bound to a real corpus pair can still declare false
    statuses and be accepted as a well-formed REQUEST;
  · whether the oracle really sits outside the worker's scope is a claim about a task design that
    does not exist yet;
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
  · the record's CLASS is bound to nothing recomputable: the corpus's own per-case dispositions are
    deliberately not consulted, because the corpus header forbids collapsing those axes;
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
is pinned by `test_known_boundary_declared_statuses_are_not_recomputed`, and the attack that
motivated v2.2.0 is pinned by the `LaunderingVariants` test class, whose six variants must stay
refused.

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
