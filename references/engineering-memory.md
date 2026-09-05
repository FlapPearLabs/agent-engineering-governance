# REF: Engineering Memory — 持久工程知识的晋升政策

> Canonical owner: AGENTS.md（权威分层）。本文件定义 runtime MEMORY 与 canonical 治理的边界与晋升生命周期。
> 核心原则：**MEMORY_IS_DISCOVERY_NOT_AUTHORITY** —— runtime MEMORY（`~/.workbuddy/MEMORY.md` 等）是导航/上下文材料；durable 工程真理必须落在 RULES / AGENTS / references / deployment 文档、Spec、Git、测试、CodeGraph、评审证据中，并可回溯指向这些权威。

## 1. 晋升判定

| 类别 | 处置 |
|---|---|
| approved 工程原则 / 重复失效模式 / 稳定工作流决策 / 评审经济学 / 模型与工具路由哲学 / durable CI 语义 / CodeGraph 稳定经验 / 跨项目工程偏好 / 已证反模式 / 稳定自治与 STOP 行为 | **PROMOTE**（进 canonical 文档对应节；或确认已覆盖） |
| 临时事故记录、当前任务状态、旧 SHA/status、一次性 troubleshooting、用户个人细节、凭据、deployment profile 之外的本地路径事实、原始对话、推测性推理、已被取代的规则 | **DO NOT PROMOTE**（留在 runtime memory 或丢弃） |

每次晋升记录：`SOURCE = MEMORY` / `DURABILITY_REASON` / `CANONICAL_DESTINATION` / `EXISTING_DUPLICATE = YES|NO` / `ACTION = ADD|MERGE|ALREADY_COVERED|DROP`。逐项台账见 `audit/PORTABILITY_HARDENING_EVIDENCE.md`。

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
