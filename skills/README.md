# Skills Acquisition Guide — 主链工程技能获取指南（V1）

> **政策**：本仓**不 vendor 任何第三方 skill 源码**；本文件只告诉 fresh Agent：哪些 skill 属于工程工作流、canonical 上游在哪、如何获取/验证、何时该用/不该用。
> **SKILL_IS_EXECUTION_METHOD / SKILL_IS_NOT_AUTHORITY**：路由唯一权威 = `references/skills-and-model-routing.md` §1。
> **来源标注规则（D2）**：以实际安装元数据/包证据为准；上游无法确证时 `SOURCE = UNKNOWN`，**不阻塞 V1**，fallback = 使用前定位本机已装 `SKILL.md` 或平台 skill registry。禁止编造上游 URL。版本 pinning 仅在真实漂移成为问题时再加（MINIMUM NECESSARY COMPLEXITY）。

## 通用获取与验证方法

1. **VERIFY（统一）**：`ls ~/.workbuddy/skills/<name>/SKILL.md`（或当 runtime 的 skill registry 等价物）+ 读 frontmatter 确认 `name` 匹配。
2. **INSTALL（统一）**：本仓不含安装器。主链 13 个 skill 在当前基准环境（`~/.workbuddy/skills/`）**已安装**；新环境按 `SOURCE` 指引获取，或在平台 skill 市场检索同名 skill。
3. 使用声明必须可核验（skill 被实际调用/读取），否则报 `UNVERIFIED`。

## 主线清单

| NAME | PURPOSE | SOURCE | PRIMARY_TRIGGER | IMPORTANT_BOUNDARY |
|---|---|---|---|---|
| grill-with-docs | 深度需求访谈，边问边产出 ADR/词汇表 | UNKNOWN（用户归属 Matt Pocock 工程技能族；上游待 registry 确证） | 需求真实模糊 | 产出是 ADR/词汇表，不是 Spec |
| to-spec | 把已充分讨论的对话合成为 Spec | 同族 UNKNOWN | Grill/讨论已完成 | 不访谈，只合成；approved 前不是权威 |
| to-tickets | tracer-bullet 垂直切片 + 阻塞边发布 | 同族 UNKNOWN | approved 架构/Spec 之后 | 必须套 seam-first 约束壳（execution-stage.md §6）；frontier 提示服从 Stage 编组 |
| implement | 以 Spec/tickets 为输入的实现入口 | 同族 UNKNOWN | MEDIUM/HIGH CODE 票实质实现 | EXECUTION ≠ ARCHITECTURE REOPEN；合同空白 → STOP |
| tdd | red-green-refactor 纪律 | 同族 UNKNOWN | 正确性行为/合同存在 | RED 必须反例触发（ticket-lane.md §4） |
| code-review | 固定基点的 Standards+Risk 双轴评审 | 同族 UNKNOWN | push 前自审；独立评审可复用其检查轴 | 自审 ≠ 独立评审 gate（R4 条件式） |
| review-agent | 只读缺陷列举（委派型 subagent 评审） | 独立 skill，SOURCE UNKNOWN | 编排者把未提交变更/diff 委派给子代理评审时 | 与 code-review **互补**不互替；不替代独立 gate |
| diagnosing-bugs | 疑难 bug/回归根因诊断循环 | 同族 UNKNOWN | 根因调查 | 不得借诊断扩 scope |
| resolving-merge-conflicts | 真实 merge/rebase 冲突处置 | 同族 UNKNOWN | 仅存在真实冲突时 | 结束后回原 lane 流程 |
| writing-plans | bite-sized 实现计划 | 同族 UNKNOWN | Spec→tickets 之间需要实现计划时 | 计划不是架构权威 |
| subagent-driven-development | delegate_task 子代理两段评审编排 | 同族 UNKNOWN | 多 lane 并行执行 | 不豁免 R4 / exact-SHA |
| simplify-code | GREEN 后的并行清理 | 同族 UNKNOWN | 测试全绿之后 | 不得改行为/合同 |
| handoff | 会话压缩为跨 agent 交接文档 | 同族 UNKNOWN | 跨工具/中断/审计场景 | 默认直接 dispatch，不强制 handoff |

**FALLBACK（全部主线 skill 通用）**：使用前定位本机已装 `SKILL.md`（`~/.workbuddy/skills/<name>/SKILL.md`）或平台 skill registry；无法定位且无法获取 → 按 `references/skills-and-model-routing.md` 的职责等价物执行并如实标注 `SKILL_UNAVAILABLE`。

## 更新流程

安装/升级/替换主链 skill → 更新本清单对应行（SOURCE/边界如有变化）→ 治理变更评审（默认双评审）。
