# REF: Engineering Memory — 持久工程知识的晋升政策

> Canonical owner: AGENTS.md（权威分层）。本文件定义 runtime MEMORY 与 canonical 治理的边界与晋升生命周期。
> 核心原则：**MEMORY_IS_DISCOVERY_NOT_AUTHORITY** —— runtime MEMORY（`~/.workbuddy/MEMORY.md` 等）是导航/上下文材料；durable 工程真理必须落在 RULES / AGENTS / references / deployment 文档、Spec、Git、测试、CodeGraph、评审证据中，并可回溯指向这些权威。

## 1. 晋升判定

| 类别 | 处置 |
|---|---|
| approved 工程原则 / 重复失效模式 / 稳定工作流决策 / 评审经济学 / 模型与工具路由哲学 / durable CI 语义 / CodeGraph 稳定经验 / 跨项目工程偏好 / 已证反模式 / 稳定自治与 STOP 行为 | **PROMOTE**（进 canonical 文档对应节；或确认已覆盖） |
| 临时事故记录、当前任务状态、旧 SHA/status、一次性 troubleshooting、用户个人细节、凭据、deployment profile 之外的本地路径事实、原始对话、推测性推理、已被取代的规则 | **DO NOT PROMOTE**（留在 runtime memory 或丢弃） |

每次晋升记录：`SOURCE = MEMORY` / `DURABILITY_REASON` / `CANONICAL_DESTINATION` / `EXISTING_DUPLICATE = YES|NO` / `ACTION = ADD|MERGE|ALREADY_COVERED|DROP`。逐项台账见 `audit/PORTABILITY_HARDENING_EVIDENCE.md`。

### 记忆路由（V1.1.2，与 project-state-persistence §9 同步）

```text
临时想法 → P0 ephemeral；当前票状态 → GitHub Issue/PR/tracker（P1）；
长期项目决策 → TARGET/SPEC/ADR/架构（P2）；技术不确定性/结果 → SPIKE（P2）；
重要缺陷 → TEST + Issue/PR（P3）；环境要求 → 本机全量 + sanitized 远端 profile（P4）；
跨项目工程经验 → 本治理仓（canonical）；用户/runtime 便利记忆 → MEMORY（F 层导航）。
```

同一真相不做五处竞争副本——始终有唯一可识别的 canonical owner。

## 2. 已晋升内容（V1.1，源自原始 MEMORY 的 durable 工程知识）

### Engineering style（工程风格原则，SOURCE = MEMORY Lane V2 "Engineering style"；DURABILITY_REASON = 跨项目稳定的实现美学，防过度设计与静默 fallback；EXISTING_DUPLICATE = 部分（doctrine 已覆盖最小复杂性）；ACTION = ADD）

- Minimum correct architecture；复杂度必须由当前需求或已证风险辩护。
- Explicit ownership；simple boundaries；deterministic behavior。
- Fail closed where required；**no silent fallback**（fallback 必须在合同中声明 ALLOWED/FORBIDDEN）。
- No unnecessary abstraction；no speculative future-proofing；no overengineering。
- Testable seams；replaceable components；preserve frozen authority。

> 落点说明：上列原则在执行时通过 ticket-lane 合同字段块（ALLOWED_FALLBACKS/FORBIDDEN_FALLBACKS）、REPAIR_VALUE、doctrine #4/#9 具体化；本节是它们的 durable 汇总锚点。

## 3. 原始 MEMORY 的其余内容

全部已在 V1 迁移中进入 canonical 文档（AGENTS/RULES/references）或按 R2 分区处理（机器事实 → deployment profile；偏好 → 指针文件）。台账见 `audit/PORTABILITY_HARDENING_EVIDENCE.md` §memory。**本文件不复制 MEMORY 正文**，也不构成第二权威层。

## 4. Learning 关闭条件（按需 recipe；非每票模板）

本节是 learning 条目关闭条件的**唯一 canonical owner**；其它 surface 只指针或链接到本节，不复述这些条件（`AC-38` / `CE-28`）。

**按需**：本节是按需 recipe —— 只有需要关闭一个 learning 条目时才适用；它不是每票必填的字段组，不向常规工单增加必填字段，也不构成第二套状态机。

关闭一个 learning 条目必须同时给出「显式处置（采纳 accept / 拒绝 reject）+ 理由 + 验证引用」；三者缺一即关闭无效。

仅凭一句状态断言（fixed / done / resolved / 已修复 / 已完成 / 已解决）**不得**关闭 learning 条目 —— 状态字符串既不是处置，也不是证据。

本节只使用最小处置词表 accept / reject，不引入新的全局枚举、状态机或字段名。

状态合同：

```text
LEGAL    ACCEPT + 采纳理由 + 验证引用
LEGAL    REJECT + 拒绝理由 + 验证引用
ILLEGAL  仅状态断言（fixed / done / resolved / 已修复 / 已完成 / 已解决）-> 拒绝
ILLEGAL  缺少采纳/拒绝理由 -> 拒绝
ILLEGAL  缺少验证引用 -> 拒绝
```

错误语义（fail closed）：

```text
missing disposition      -> 关闭无效
missing reason           -> 关闭无效
missing verification ref -> 关闭无效
assertion-only closure   -> 关闭无效
```

同一关闭条件 recipe 在两个 canonical 文件重复定义（双 owner）必须拒绝并收敛为单一 owner（`CE-28` / `AC-38`）。

`CE-18`：一个 learning 条目在没有采纳/拒绝理由与验证引用时被关闭必须被拒绝。

本节 recipe 属 canonical reference 变更，按 [AGENTS.md](../AGENTS.md) 第 8 节的治理变更协议执行；它只在关闭条件被应用时生效，不是逐票模板。

## 5. ORCHESTRATOR CLOSURE DOCTRINE (M1-M9)
<!-- Canonical owner: references/engineering-memory.md -->
<!-- Authority: Engineering Memory Doctrine for Autonomous Orchestrators -->

Autonomous orchestrators and multi-agent harnesses MUST abide by the following nine mechanical closure predicates. A ticket closure or completion claim that violates these predicates is an `ORCHESTRATOR_FALSE_CLOSURE` and must be rejected fail-closed.

* **M1 — CLOSE IS DERIVED**: `CLOSE_READY` is a mechanically evaluated boolean predicate over all required gates, never an orchestrator or implementer judgment. A ticket is closed ONLY when all closure predicates evaluate to TRUE.
* **M2 — POST-INTEGRATION FIRST**: When a ticket requires post-integration verification, closing the ticket before post-integration CI completes with success is strictly prohibited. The legal sequence is: `MERGE -> POST-INTEGRATION CI START -> WAIT -> POST-INTEGRATION CI SUCCESS -> POST-INTEGRATION VERIFY PASS -> CLOSE`. Close timestamp MUST be strictly greater than CI completion timestamp.
* **M3 — A FINDING REQUIRING CHANGE MUST LEAVE A NEW ARTIFACT**: If an independent review finding (P0/P1) requires a code, documentation, contract, or test change, closure evidence MUST contain a new commit SHA or an authoritative recorded amendment. Re-declaring closed without a new artifact or a persisted `NO_CHANGE_REQUIRED` independent ruling is prohibited.
* **M4 — REVIEW SUMMARY IS NOT REVIEW EVIDENCE**: An orchestrator summary stating "Reviewer A PASS, Reviewer B PASS" cannot substitute for the reviewers' raw artifacts or legally referenceable evidence. Review quorum must be independently referenceable.
* **M5 — OWNER CHAT DIRECTIVE MUST ENTER THE AUTHORITY CHAIN**: When a Product Owner authorizes a scope change during orchestration, the agent must persist that directive to a canonical authority surface (e.g. authoritative issue amendment comment or spec record) before relying on it. Chat context is not permanent repository authority.
* **M6 — GREEN TESTS DO NOT PROVE A STRONGER CONTRACT**: CI green proves only that executed assertions passed. It does not prove unmodeled properties such as atomicity, durability, or crash consistency unless the test suite and platform semantics directly falsify and verify them.
* **M7 — TERMINOLOGY MUST MATCH GUARANTEE**: Terminology must strictly reflect verified guarantees:
  * `RECOVERABLE != ATOMIC`: A two-step replacement with an unlink gap is recoverable/fail-safe, but not physically atomic.
  * `PROCESS_CRASH_SAFE != POWER_LOSS_DURABLE`: Tolerating process death does not prove surviving disk cache loss on power failure.
  * `CONTENT_INTEGRITY != REUSE_AUTHORITY`: Valid bytes do not grant reuse authority unless bound by the authoritative checkpoint.
* **M8 — ORCHESTRATOR CANNOT SELF-CERTIFY**: Implementers cannot give their own work final review pass, and orchestrators cannot certify their own closure evidence. Independent gates require distinct, independent review execution.
* **M9 — CONTINUE-UNTIL-CLOSED DOES NOT MEAN BYPASS-GATES**: "Continue working until closed" means executing the cycle: `reproduce -> repair -> test -> re-review -> CI -> merge -> verify -> close`. It never permits skipping or weakening gates to force a premature closed state.

For an integration ticket whose authority requires post-integration CI and dual independent review, the orchestrator must take the facts from the existing Issue/PR control plane and run `python3 scripts/validate_governance.py --pre-close < closure-evidence.json` before closing the Issue. Exit 0 and `close_ready: true` are both required; an absent or failed result leaves the Issue open. The JSON is a temporary input assembled from the existing records, not a new tracker or a second authority. It must identify the candidate SHA, completed successful CI run and completion time, post-integration verification reference plus `post_integration_verify_status: PASS` and `post_integration_verified_at`, two distinct raw `PASS` reviewer references bound to that SHA, the disposition of every P0/P1 finding, and the six existing `references/git-ci-integration.md` §5.1 reachability slots when `REACHABILITY_APPLICABILITY = REQUIRED`. A separate independent `NO_CHANGE_REQUIRED` ruling reference may settle a finding but never counts toward the two-`PASS` quorum. `RUNTIME_REACHABLE = FALSE` or `INTEGRATION_COMPLETE = FALSE` cannot pass. `PRODUCTION_CALLERS` may be an empty set for a legitimate dynamic path when the runtime entrypoint, call chain, observed effect, evidence reference, and `RUNTIME_REACHABLE = TRUE` substantiate it; static caller count alone is not a veto. `N/A` requires the existing policy reason and reviewer/integrator acceptance reference from `references/ticket-lane.md` §3.1.4; a worker cannot self-grant it. Any relied-on scope amendment needs a persisted HTTPS reference, not chat text. The CLI overwrites any caller-supplied pre-check time and emits `checked_at`, `candidate_sha`, and `close_ready`. The orchestrator must persist that exact result as a comment on the existing Issue before closing, retain its comment URL, and verify that the cited CI, reviewer, reachability, scope-amendment, and acceptance records really say what the JSON claims. The CLI checks slots and order; it does not authenticate the supplied URLs or grant authority to caller-supplied exemptions.

After closing, run the same entrypoint with `--post-close`, copying the emitted `checked_at` to `pre_close_checked_at`, providing the persisted `pre_close_comment_ref`, and supplying the actual GitHub `closedAt` as `ticket_close_timestamp`. It requires `CI completed_at < post_integration_verified_at < pre_close_checked_at < ticket_close_timestamp`. Before accepting that result, the orchestrator must read the GitHub comment's body and `createdAt`, confirm the recorded `close_ready: true` / `candidate_sha` / `checked_at` match the CLI input and that the comment predates the actual close event; the JSON alone cannot authenticate its own timestamp. A failed post-close result or a source mismatch means the close claim violates M2 and must be corrected in the existing Issue control plane. Other ticket kinds use their own authorized gate requirements; this integration-ticket CLI does not create a universal second closure state machine.
