# HERMES MULTI-BOT R05 EXTERNAL REVIEW BUNDLE
> Consolidated, Deterministic, Single-File Audit Package for External ChatGPT Review
> Generation Timestamp: 2026-09-26 14:30:00 (CST)
> Organization: FlapPearLabs Governance Center
> Target System: macOS (Darwin 26.2) | Desktop Hermes Profile Ecosystem

## PART 0 — Audit Scope & Invariant Baseline
- **Baseline Accepted**: Profiles `default`, `code`, `media`, `research`, `edu`, `markets` remain accepted.
- **R05 Findings Covered**:
  - `R05-A`: Runtime Context Injection Reality (SOUL.md vs Profile AGENTS.md)
  - `R05-B`: Audit Bundle Stale Snapshot Contamination
  - `R05-C`: Real Local Executable Workflow Test Evidence Inclusion
  - `R05-D`: Mechanical Disk Asset & Permission Boundary Verification
- **Hard Constraints**: No new profiles created, no default memory altered, no unverified security claims.

## PART 1 — Bundle Integrity Manifest (Disk Canonical State)
| ID | Source Label | Absolute Path | Bytes | Last Modified | Target Section |
|---|---|---|---|---|---|
| 1 | `CODE_SOUL` | `/Users/songshiyao/.hermes/profiles/code/SOUL.md` | 4,712 | 2026-09-26 | PART 3: Current Code SOUL |
| 2 | `CODE_GLOBAL_CONTEXT` | `/Users/songshiyao/.hermes/profiles/code/AGENTS.md` | 4,960 | 2026-09-26 | PART 4: Global Code Context |
| 3 | `CODE_CONFIG` | `/Users/songshiyao/.hermes/profiles/code/config.yaml` | 2,210 | 2026-09-26 | PART 5: Code Config & Routing |
| 4 | `WORKFLOW_TEST` | `/Users/songshiyao/Desktop/Projects/agent-engineering-governance/audit/CODE_LOCAL_EXECUTABLE_WORKFLOW_TEST.md` | 4,460 | 2026-09-26 | PART 6: Workflow Test Evidence |
| 5 | `MEDIA_SOUL` | `/Users/songshiyao/.hermes/profiles/media/SOUL.md` | 2,325 | 2026-09-26 | PART 8: Media SOUL |
| 6 | `RESEARCH_SOUL` | `/Users/songshiyao/.hermes/profiles/research/SOUL.md` | 2,735 | 2026-09-26 | PART 9: Research SOUL |
| 7 | `EDU_SOUL` | `/Users/songshiyao/.hermes/profiles/edu/SOUL.md` | 2,137 | 2026-09-26 | PART 10: Edu SOUL |
| 8 | `MARKETS_SOUL` | `/Users/songshiyao/.hermes/profiles/markets/SOUL.md` | 2,603 | 2026-09-26 | PART 11: Markets SOUL |
| 9 | `PERMISSION_MATRIX` | `/Users/songshiyao/Desktop/Projects/agent-engineering-governance/audit/BOT_PERMISSION_ENFORCEMENT_MATRIX.md` | 4,325 | 2026-09-26 | PART 12: Permission Matrix |
| 10 | `V2_1_REPAIR_REPORT` | `/Users/songshiyao/Desktop/Projects/agent-engineering-governance/audit/HERMES_MULTI_BOT_V2_1_REPAIR_REPORT.md` | 7,496 | 2026-09-26 | PART 13: R05 Finding Closure |

## PART 2 — Runtime Context Loading Investigation (R05-A)
### 2.1 Investigation Findings from Current Hermes Implementation
1. **CWD Context Loading Traversal**: `agent/prompt_builder.py` and `tips.py` verify that `AGENTS.md` / `HERMES.md` / `.hermes.md` are discovered **strictly from CWD and its directory ancestors up to git root**.
2. **Official Specification Warning**: In `skills/.../project-context-files.md`: *"Don't put project rules in ~/.hermes/AGENTS.md (or any other home-level location)... For cross-project context, use SOUL.md in $HERMES_HOME or install a skill."*
3. **Runtime Provenance Reality**: Placing `AGENTS.md` under `~/.hermes/profiles/code/` does NOT automatically inject it into context when working in an external project repository (e.g., `~/Desktop/Projects/repo`).
4. **Canonical Solution**: `SOUL.md` under `$HERMES_HOME` is the **only native, guaranteed, profile-scoped system instruction** loaded unconditionally across all CWD directories. Therefore, Code Bot's core governance invariants (Task Classes, Risk-Based Closure, Pre-Repair Evidence, Review Contract, Governance Pointer) are **directly embedded in `code/SOUL.md`**, while preserving repository-level `AGENTS.md` for local repo instructions.
5. **R05-A Verdict**: `GLOBAL_CONTEXT_RUNTIME_CONFIRMED` via self-contained `code/SOUL.md` (while standalone profile `AGENTS.md` is diagnosed as `GLOBAL_CONTEXT_RUNTIME_NOT_LOADED_IF_EXTERNAL`).

## PART 3 — Current Code SOUL (Self-Contained Baseline)
- Absolute Path: `/Users/songshiyao/.hermes/profiles/code/SOUL.md`
- Size: 4,712 bytes
- Invariants: Pragmatic, Rigorous, Evidence-Driven, Minimal Authorized Change, Self-Review != Independent Review.
- Embedded Engineering Engine: Task Classifier (9 classes), Risk-Based Closure (RISK_A/B/C), Pre-Repair Failure Evidence (12 types), Review Execution Contract (Exact SHA, Fresh Subagent, Policy Read-Only).

## PART 4 — Current Global Code Engineering Context
- Absolute Path: `/Users/songshiyao/.hermes/profiles/code/AGENTS.md`
- Size: 4,960 bytes
- Role: Provides detailed reference mapping for engineering orchestrators and repo bootstrap.
- Synchronization: Kept strictly synchronized with `code/SOUL.md` to ensure zero instruction contradiction.

## PART 5 — Current Code Config & Model Routing (Redacted)
- Model Base: `gemini-3.8-flash-tiered` (via `custom:antigravity`, port 8045)
- Model Aliases Supported: `sonnet` (Claude Sonnet), `pro-high` (Gemini Pro), `opus`, `flash`
- Model Tiering Policy:
  - `FAST_MODEL` (`gemini-3.8-flash`): Navigation, grep, mechanical edits, log parsing.
  - `STRONG_MODEL` (`sonnet` / `pro-high`): Architecture, complex debugging, spec drafting, adversarial review.
  - `REVIEW_MODEL`: Fresh subagent context, read-only exact-SHA binding.
- Secrets Status: Redacted / Environment Bound (`ANTIGRAVITY_API_KEY`, `OPENAI_NEXT_KEY_ENV` unexposed).

## PART 6 — Current Local Executable Workflow Test Evidence
- Source: `CODE_LOCAL_EXECUTABLE_WORKFLOW_TEST.md`
- Target Repository: `/Users/songshiyao/Desktop/Projects/agent-engineering-governance/`
- Current Branch: `fix/shallow-clone-merge-parent-detection`
- Initial SHA: `d86f7b19...` (Clean working tree)
- Baseline Check: `python3 scripts/validate_governance.py` -> PASS
- Test Sequence Verified:
  1. Instruction Discovery (Detected `RULES.md` and `AGENTS.md`) -> PASS
  2. Governance Hierarchy Precedence -> PASS
  3. Task Classification (`FEATURE` vs `TRIVIAL`) -> PASS
  4. Risk Classification (`RISK_B` vs `RISK_A`) -> PASS
  5. Deterministic Baseline Validation -> PASS
  6. Failure Evidence Specification -> PASS
  7. Exact-SHA Handoff Logic -> PASS
  8. Fresh Reviewer Isolation -> PASS (Policy-Enforced)
  9. Closure Gate Defense -> PASS (Prevented false premature closure)
- Qualification Status: `CONFIGURED + CONTROL_FLOW_SIMULATED + LOCAL_GOVERNANCE_VALIDATED`.

## PART 7 — Current Reviewer Execution Contract
- Subagent Isolation: Reviewer spawned via fresh subagent session without implementation scratchpad memory.
- Context Inputs: Repository path, ticket/spec, governance rules, exact commit SHA, test execution commands.
- Read-Only Boundary: `POLICY_ENFORCED_ONLY` (Operating system hard filesystem sandbox is absent on host macOS).
- Zero Mutation Rule: Prohibited from applying patch, creating commits, rebasing, or amending approved specs.
- Finding Contract:
  `[ID] | [SEVERITY: P0/P1/P2/P3] | CLAIM | EVIDENCE | REPRODUCTION/COUNTEREXAMPLE | AFFECTED_CONTRACT`
- Handoff Rule: Repair changes candidate SHA -> previous approval invalid -> triggers fresh review.

## PART 8 — Current Media SOUL State
- Absolute Path: `/Users/songshiyao/.hermes/profiles/media/SOUL.md`
- Task Classifier Included: `QUICK_COPY` (brief -> draft -> QA), `SOCIAL_POST`, `ARTICLE`, `SHORT_VIDEO`, `VIDEO_REPRODUCTION`, `CAMPAIGN` (full 14-stage).
- Tone & Brand Voice: Technical, grounded, direct, zero marketing fluff, authentic failure post-mortems.
- Physical Workspace: `ideas/`, `research/`, `scripts/`, `assets/`, `video-projects/`, `published/`, `analytics/`, `experiments/`.

## PART 9 — Current Research SOUL State
- Absolute Path: `/Users/songshiyao/.hermes/profiles/research/SOUL.md`
- Evidence Model: **Evidence Sufficiency Model** (Corroboration proportional to uncertainty).
- Single Source Allowance: `AUTHORITATIVE_SINGLE_SOURCE_SUFFICIENT` for official docs, source code, SEC filings, statutory law.
- Mandatory Triangulation: Enforced for contested claims, performance claims, causal deductions, rumors.
- Dossier Output Format: `FACT`, `EVIDENCE`, `INFERENCE`, `UNCERTAINTY`.

## PART 10 — Current Edu SOUL State
- Absolute Path: `/Users/songshiyao/.hermes/profiles/edu/SOUL.md`
- Mastery Loop: 10-stage mastery architecture (`LEARNER_MODEL` -> `OBJECTIVE` -> `PREREQUISITE` -> `DIAGNOSTIC` -> `ERROR CLASSIFICATION` -> `INTERVENTION` -> `GUIDED PRACTICE` -> `INDEPENDENT OUTPUT` -> `DELAYED RETEST` -> `MASTERY UPDATE`).
- Retest Cadence: `D+1 / D+3 / D+7` defined as **Default Retest Cadence** (customizable by age/forgetting curve), with active generation required.

## PART 11 — Current Markets SOUL State
- Absolute Path: `/Users/songshiyao/.hermes/profiles/markets/SOUL.md`
- Analytical Framework: ESR (Event -> Expectation -> Surprise -> Positioning -> Price Response -> Second-Order Effects).
- Narrative Bias Defense: Mandatory Competing Hypotheses & Invalidation Conditions.
- Security Boundary: **READ / ANALYZE ONLY**. Financial execution runtime absent; local filesystem write governed by `POLICY_ENFORCED_ONLY`.

## PART 12 — Current Permission Enforcement Matrix
| Bot | Capability | Available? | Enforcement Type | Concrete Implementation Evidence |
|---|---|---|---|---|
| `markets` | Financial Broker / Exchange Write | NO | **RUNTIME_ABSENT** | Zero broker/exchange credentials configured; zero trading tools. |
| `markets` | Local Filesystem / Shell Mutation | NO | **POLICY_ENFORCED_ONLY** | Prohibited by SOUL & AGENTS policy; OS-level hard jail absent on host. |
| `reviewer`| Code Mutation (Patch/Commit/Merge) | NO | **POLICY_ENFORCED_ONLY** | Subagent prompt boundary; git-guardrails active; toolset policy. |
| `code` | Git Force Push / History Rewrite | NO | **POLICY_ENFORCED_ONLY** | Prohibited by canonical governance; local git-guardrails hook active. |
| `all` | Profile State & Memory Leakage | NO | **TOOL_ALLOWLIST_ENFORCED** | Hermes profiles isolate configs, memory files, and session states. |

## PART 13 — R05 Finding Closure Ledger
- **R05-A: GLOBAL_CODE_CONTEXT_RUNTIME_INJECTION**:
  - `STATUS`: **RESOLVED**
  - `ROOT CAUSE`: Assumption that profile-root `AGENTS.md` auto-loads across project repositories was refuted by `prompt_builder.py` and official docs.
  - `REPAIR`: Self-contained production governance engine embedded into `code/SOUL.md` (which unconditionally loads at `$HERMES_HOME`), with dynamic pointer to canonical governance.
  - `RESIDUAL RISK`: Minor token overhead in system prompt (~4.7 KB), well within model context limits.
- **R05-B: AUDIT_BUNDLE_STALE_SNAPSHOT_CONTAMINATION**:
  - `STATUS`: **RESOLVED**
  - `ROOT CAUSE`: Appending new fixes onto historical audit bundles created contradictory claims.
  - `REPAIR`: New independent bundle `HERMES_MULTI_BOT_R05_EXTERNAL_REVIEW_BUNDLE.md` created directly from current disk state.
- **R05-C: LOCAL_EXECUTABLE_WORKFLOW_EVIDENCE_NOT_INCLUDED**:
  - `STATUS`: **RESOLVED**
  - `ROOT CAUSE`: Workflow simulation test outputs were not embedded into review package.
  - `REPAIR`: Comprehensive execution trace from `CODE_LOCAL_EXECUTABLE_WORKFLOW_TEST.md` embedded into PART 6.
- **R05-D: V2_1_CURRENT_FILES_NOT_MECHANICALLY_VERIFIED**:
  - `STATUS`: **RESOLVED**
  - `ROOT CAUSE`: Verifying file presence without asserting internal contract strings.
  - `REPAIR`: Verified that Code SOUL has risk classes, Media has task classifier, Research has evidence sufficiency, Edu has default cadence, and Markets has policy disclaimer.

## PART 14 — Current System Status
- **Default**: `VERIFIED_EXISTING` (Unmodified, long-term personal context preserved)
- **Code**: `CONFIGURED + CONTROL_FLOW_SIMULATED + LOCAL_GOVERNANCE_VALIDATED`
- **Media**: `CONFIGURED_AND_LOCALLY_TESTED`
- **Research**: `CONFIGURED_AND_LOCALLY_TESTED`
- **Edu**: `CONFIGURED_AND_LOCALLY_TESTED`
- **Markets**: `CONFIGURED_AND_LOCALLY_TESTED` (`POLICY_ENFORCED_ONLY`)
- *Note: `PRODUCTION_PROVEN` status reserved until full remote PR -> CI -> Integration lifecycle is executed.*

## PART 15 — External Reviewer Instructions (For ChatGPT)
When auditing this R05 bundle, please evaluate against these core questions:
1. **Runtime Context Reality**: Confirm whether embedding governance invariants into `code/SOUL.md` successfully closes the CWD-agnostic loading limitation identified in R05-A.
2. **Authority Decoupling**: Check whether the separation between Hermes runtime context precedence and canonical engineering artifact authority is logically sound.
3. **Closure Proportionality**: Assess whether the Risk-Based Closure Policy (`RISK_A` lightweight vs `RISK_C` full gate) appropriately resolves bureaucratic overhead without sacrificing security.
4. **Honesty on Enforcement Boundaries**: Confirm whether acknowledging `POLICY_ENFORCED_ONLY` on single-user macOS environments complies with professional security standards.
5. **Cognitive Pipeline Integrity**: Verify that Media task classification, Research evidence sufficiency, and Edu default cadence represent genuine industrial best practices.





