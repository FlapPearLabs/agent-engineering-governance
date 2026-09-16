# Spec → ticket re-entry and composition: implementation evidence

## Scope and authority

- Owner authorization: 2026-09-16 direct isolated governance implementation, required corrections C1–C4; commit/push authorized, integration not authorized.
- Target: `FlapPearLabs/agent-engineering-governance`.
- Base: `0ba2c7351d45dba1459a391b0d43e418ecf55280` (fresh remote main).
- Feature branch: `fix/spec-ticket-semantic-gates-20260916`.
- Owner-designated external compatibility input for this governance design/review (owner identifies it as approved): [exact Spec](https://github.com/FlapPearLabs/agent-engineering-governance/blob/60209cdaf2beeaa718fadcc4028a41c2f0f07db1/docs/specs/P1_AGENT_ENGINEERING_GOVERNANCE_DELTA_SPEC.md), `P1_SPEC_SHA = 60209cdaf2beeaa718fadcc4028a41c2f0f07db1`. Read-only; not this feature branch's in-tree canonical Spec pointer. The branch has no in-tree P1 Spec, so `canonical_documents.specs = ["NONE"]`. No Spec or parallel ticket content is copied or modified.
- This authorization is separate from that Spec's implementation authorization. No claim that its W1–W5 work is implemented here.
- Independent governance review remains required: two independent axes on the same exact candidate under AGENTS §8. This document is executor evidence, never reviewer approval.

## Grounding and owner placement

`CODEGRAPH = UNAVAILABLE`; `MODE = C`; `CANDIDATE_GRAPH_COVERAGE = MANUAL_SURFACE_AND_DIFF`.
Enhanced manual grounding read RULES, AGENTS, authority/pain maps, execution-stage, ticket-lane, git-ci-integration, review-and-repair, project continuity/persistence, bootstrap, skill routing, validators and CI entrypoints.

| Producer / owner | Consumer / consequence |
|---|---|
| RULES R3 | Proof honesty only; no project vocabulary or workflow recipe |
| AGENTS §4 | Bootstrap-loaded decomposition route to the one recipe |
| execution-stage §6 | PRE, draft, POST and independent conformance obligations; project agents consume |
| ticket-lane §3/§4 (unchanged) | Owns single-ticket contracts and authorized RED execution |
| git-ci-integration §5 (unchanged) | Owns exact-SHA/delta review policy; reuse points here |
| skill routing | ask-matt optional, cannot approve anything |
| validate_governance → ticket_gate_wiring | Static presence/routing checks only; CI calls actual CLI |
| scripts/tests → CI | Mutation checks catch deleted routes/guards, expose semantic limitations |
| existing project-state schema/validator | Initialize this governance repo's missing index; no downstream project memory |

The smallest enforceable layer here is an agent/reviewer procedure plus static wiring regression. No universal natural-language semantic checker or runtime publish interceptor is claimed. Runtime enforcement/deployment: NOT_RUN / outside this change. Governance review is HIGH-value escalation, retained for independent review after push.

## Matt source inspection

Source inspected at upstream commit `959a8e9f1edc3adbe2f7e3054bb6fbefa6696260`, not a claim about another machine's installation. No third-party skill source vendored.

| Skill under [upstream engineering skills](https://github.com/mattpocock/skills/tree/959a8e9f1edc3adbe2f7e3054bb6fbefa6696260/skills/engineering) | Observed principle | Local artifact policy |
|---|---|---|
| ask-matt | Router; recommends continuity through ticketing, permits phase-boundary compaction | Advice is not authority or evidence |
| grill-with-docs | Calls grilling and domain-modeling | No forced replay of interviews |
| domain-modeling | Stable terms, challenge overloads; ADR for hard-to-reverse, surprising, real trade-offs | CONTEXT and ADR formats are project choices |
| codebase-design | Interface includes invariants, ordering, errors, config, performance; seam discipline | Do not impose its exact vocabulary on all domains |
| to-spec | Synthesize settled decisions; inspect repo and confirm seams | An externally approved Spec can supply equivalent knowledge |
| to-tickets | Context-driven tracer bullets with blockers; publishing/frontier defaults | Governance keeps drafts non-executable until composition/review/authorization |

These files were inspected as source evidence, not invoked to interview the owner, generate a new Spec, or decompose the concurrent lane's tickets.

## C1–C4 and frozen Spec compatibility

| Correction | Implementation / compatibility finding |
|---|---|
| C1 | PRE proves upstream readiness; POST checks the actual draft set. Independent POST semantics and ticket conformance can share one review. No early RED/E2E requirement; consistent with Spec REQ-W1-02 / AC-21. |
| C2 | Valid evidence reuse binds repo, approved source, reference versions and scope; unknown dependencies rebuild affected scope only. Reuses git-ci-integration owner and agrees with REQ-W3-01/02/03; does not implement a competing W2 evidence schema. |
| C3 | Explicit five-part approved-contract comparison and conflict STOP; R1 resolution retained. Does not change W1–W5 ordering, authorization or frozen field names. |
| C4 | Structural result is separate from independent semantic verdict. Static wiring cannot grant project PASS; CE-G13/G14 below make the limit concrete. |

`ARCHITECTURE_CONFLICT = NONE_IDENTIFIED_BY_EXECUTOR` for this isolated delta. This is not independent approval and does not authorize retroactive application to another active lane. Shared future edit surface (execution-stage / validator / routing) requires normal integration conflict review; neither lane may silently overwrite the other's changes.

## Counterexample design walkthrough (not live project gate execution)

The following are manual, source-to-rule walkthroughs by the executor. The outcome column is the required protocol disposition after applying the cited clause; it is **not** a claim that a semantic validator ran or that an independent reviewer approved. `LIVE_PROJECT_GATE_RUN = NOT_RUN` for every row.

| Case | Input / discriminator | Required disposition and clause |
|---|---|---|
| CE-G1 | Contiguous Matt flow with valid bound upstream evidence | PRE reuses it, POST still required (§6.2/6.4) |
| CE-G2 | New session, external approved exact Spec with sufficient semantics | Reconstruct needed scope and allow drafts (§6.2) |
| CE-G3 | No CONTEXT/ADR; Spec and repo contracts sufficient | Allow; filenames are not proof requirements (§6.1) |
| CE-G4 | Project uses canonical CONTEXT/ADR | Consume references, do not copy globally (§6.1) |
| CE-G5 | Two tickets define incompatible enum meanings | POST FAIL: STATE_DRIFT (§6.4) |
| CE-G6 | Valid A→B DAG, A output violates B precondition | POST FAIL despite DAG (§6.4) |
| CE-G7 | Async producer, synchronous consumer | POST FAIL: TIMING_DRIFT (§6.4) |
| CE-G8 | One term with two incompatible project definitions | PRE conflict until authority resolves (§6.1/6.2) |
| CE-G9 | Ticket author discovers a new architectural trade-off | ARCHITECTURE_OR_DOMAIN_GAP; planning owns decision (§6.2/6.5) |
| CE-G10 | Matt unavailable | Same proof procedure remains usable (§6; routing optional) |
| CE-G11 | ask-matt recommends a flow | Recommendation cannot mint PASS (routing table) |
| CE-G12 | Fresh unrelated repo | Discover that repo's own authority; no global domain values (§6.1) |
| CE-G13 | Both fields user_id; internal DB PK vs external account ID | Structural match possible; independent POST must FAIL IDENTITY_DRIFT (§6.4) |
| CE-G14 | Both states READY; persisted/executable vs validated/not necessarily persisted | Structural match possible; independent POST must FAIL STATE_DRIFT (§6.4) |
| CE-G15 | Same session but relevant authority digest changed | Invalidate affected PRE proof; no same-session shortcut (§6.2) |
| CE-G16 | New session, unchanged bound evidence | Allow reuse; no mandatory full reconstruction (§6.2) |
| CE-G17 | Applying gate changes approved stage/owner/acceptance/authorization | SPEC_OR_AUTHORITY_CONFLICT before decomposition (§6.1) |
| CE-G18 | All fields present but author self-reports POST PASS | Remain draft; independent semantic verdict missing (§6.4) |
| CE-G19 | Final output intentionally goes to an external consumer | Explicit authority/owner/acceptance avoids false orphan rejection (§6.4) |
| CE-G20 | Error means retryable for producer, terminal for consumer | POST FAIL ERROR_SEMANTICS_DRIFT (§6.4) |
| CE-G21 | Producer requires persist-before-publish; consumer reverses order | POST FAIL ORDERING_DRIFT (§6.4) |
| CE-G22 | Conformance-approved ticket text changes in tracker | Rebind exact content snapshot; old whole-set PASS not inherited (§6.4/6.5) |

### CE-G13/G14 explicit structural/semantic separation

Both records can have complete IDs, owners, authority refs and acyclic blockers. A structural checker comparing the visible field/state strings will accept the equality. It must not claim semantic compatibility.

| Case | Producer statement | Consumer interpretation | Concrete mismatch witness |
|---|---|---|---|
| G13 | user_id = internal database primary key | user_id = external provider account ID | Internal key 42 belongs to account A; external account ID 42 belongs to account B. Shape and number match while identity does not. |
| G14 | READY guarantees payload persisted and downstream executable | READY only guarantees validation, persistence may be absent | A validated-only record is READY for consumer semantics but violates the producer's READY invariant. The shared state admits different legal sets even if the persisted subset works in one direction. |

No automatic equivalence of such meanings is implemented. Tests explicitly demonstrate that a contradictory prose sentence can still pass the wiring checker, preventing the test suite from being advertised as semantic assurance.

## Verification and continuation

Required commands: `python3 scripts/validate_governance.py`; `python3 -m unittest discover -s scripts/tests`; `python3 -m unittest discover -s adapters/zcode/tests`; `python3 scripts/validate_project_state.py .`; `PUBLIC_RELEASE=1 python3 scripts/validate_public_release.py`; `PUBLIC_RELEASE=1 python3 scripts/validate_public_release.py --selftest`; after commit, `PUBLIC_RELEASE=1 python3 scripts/validate_public_release.py --commit-metadata`; `git diff --check`.

Observed local checks before commit: governance wiring/full self-validation 31/31; project-state 16/16; documentation mutation tests 4 tests PASS (including 7 removed-marker subcases); existing project-continuity regression suite 68/68; public-release policy self-tests 51/51; public candidate scan zero violations; diff whitespace check clean. These are executor-run mechanical checks, not independent gate verdicts. Remote CI is reported separately for the pushed exact commit. Mutation tests are structural tests, not semantic CE executions. No TDD RED claim for this documentation recipe. Bootstrap live adoption and other runtime hooks remain untested here.

Next legal action after verified push: `INDEPENDENT_EXACT_SHA_GOVERNANCE_REVIEW`. Do not merge, deploy, or amend the approved Spec. The remote feature tip identifies the candidate; this report intentionally does not embed its own containing commit SHA.

## Publication transport correction

HTTPS Git push lacked credentials. Publication is retried through the connected GitHub Git-data API under renewed owner authorization. The earlier account-profile-based inference about commit metadata was insufficient: actual commit metadata must be inspected. API-created commit identity may differ from local commit identity; compare tree SHA to establish identical file content, and bind independent review to the actual remote commit. Remote ref verification and CI state are reported after publication, not inferred from successful tree creation.
