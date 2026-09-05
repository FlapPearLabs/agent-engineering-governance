# Skills Acquisition Guide — 主线工程技能获取指南（V1.1 portability hardening）

> **政策**：本仓**不 vendor 任何第三方 skill 源码**；本文件告诉 fresh Agent：哪些 skill 属于工程工作流、如何获取/验证、何时该用/不该用、缺了怎么办。
> **SKILL_IS_METHOD / SKILL_IS_NOT_AUTHORITY**：路由唯一权威 = `references/skills-and-model-routing.md` §1。
> **SKILL_MISSING != USER_MUST_COPY_FILES_MANUALLY**：缺 skill 不是让人肉拷文件——按各行 FALLBACK 执行并如实标注 `SKILL_UNAVAILABLE`。
> **来源标注规则（D2）**：以实际安装元数据/包证据为准；上游无法确证时 `SOURCE = UNKNOWN`，不阻塞；禁止编造上游 URL。
> **REQUIRED 语义**：= 触发条件命中时必须可用（或如实走 FALLBACK），不是全局常驻。

## 通用获取与验证

- **VERIFY（统一）**：定位 `SKILL.md`（基准环境 `~/.workbuddy/skills/<name>/SKILL.md` 或当 runtime 的 skill registry 等价物）并读 frontmatter 确认 `name`。
- **原始机实况（2026-09-05 探针）**：13 项全部 INSTALLED（含 4 个 ZCode dogfood 降级项，安装于 2026-06/07）。
- 使用声明必须可核验（被实际调用/读取），否则报 `UNVERIFIED`。

## 主线清单（9 REQUIRED-at-trigger + 4 OPTIONAL；不为凑数保留任何项）

| NAME | STATUS | REQUIRED? | PURPOSE | SOURCE | PRIMARY_TRIGGER | IMPORTANT_BOUNDARY | FALLBACK |
|---|---|---|---|---|---|---|---|
| grill-with-docs | CANONICAL | REQUIRED | 深度需求访谈 + ADR/词汇表 | UNKNOWN（用户归属 Matt Pocock 族；上游待 registry 确证） | 需求真实模糊 | 产出 ADR/词汇表，非 Spec | 按票模板手工访谈并成文 |
| to-spec | CANONICAL | REQUIRED | 对话合成 Spec | 同上 UNKNOWN | Grill/讨论已完成 | 不访谈；approved 前非权威 | 按合同字段块手工成文 |
| to-tickets | CANONICAL | REQUIRED | 垂直切片 + 阻塞边 | 同上 UNKNOWN | approved 架构/Spec 后 | 套 seam-first 约束壳（execution-stage §6） | 手工切片 + 三项 lint |
| implement | CANONICAL | REQUIRED | 实现入口 | 同上 UNKNOWN | MEDIUM/HIGH CODE 票 | EXECUTION ≠ ARCHITECTURE REOPEN；缺语义 STOP | 按 ticket-lane 生命周期手工执行 |
| tdd | CANONICAL | REQUIRED | red-green-refactor | 同上 UNKNOWN | 正确性行为存在 | RED 须反例触发 | 手工 TDD（合同→反例→RED→GREEN） |
| code-review | CANONICAL | REQUIRED | Standards+Risk 双轴评审 | 同上 UNKNOWN | push 前自审；独立评审复用其轴 | 自审 ≠ 独立 gate（R4） | 按评审 PASS 契约手工评审 |
| diagnosing-bugs | CANONICAL | REQUIRED | 根因诊断循环 | 同上 UNKNOWN | 疑难 bug/回归 | 不借诊断扩 scope | 结构化假设-验证循环 |
| resolving-merge-conflicts | CANONICAL | REQUIRED | 真实冲突处置 | 同上 UNKNOWN | 仅存在真实 merge/rebase 冲突 | 结束回原 lane | 手工冲突处置 + 评审 |
| handoff | CANONICAL | REQUIRED | 跨会话交接文档 | 同上 UNKNOWN | 跨工具/中断/审计 | 默认直接 dispatch | 按 minimal packet 手工成文 |
| review-agent | CANONICAL | OPTIONAL | 只读缺陷列举（委派型 subagent 评审） | UNKNOWN（本机 2026-07 装；无上游证据） | 编排者把未提交变更/diff 委派子代理评审 | 与 code-review 互补不互替；不替代独立 gate | 编排者以 fresh context 内联只读评审 |
| writing-plans | CANONICAL | OPTIONAL | bite-sized 实现计划 | UNKNOWN（本机 2026-06 装） | Spec→tickets 间需实现计划 | 计划不是架构权威 | 按 ticket-lane §3 手工计划 |
| subagent-driven-development | CANONICAL | OPTIONAL | 子代理两段评审编排 | UNKNOWN（本机 2026-06 装） | 多 lane 并行执行 | 不豁免 R4/exact-SHA | 平台原生子代理机制（WorkBuddy Agent 等） |
| simplify-code | CANONICAL | OPTIONAL | GREEN 后并行清理 | UNKNOWN（本机 2026-07 装） | 测试全绿后 | 不得改行为/合同 | 手工按比例清理或跳过（可选步骤） |

无 DEPRECATED / REPLACED / REMOVE_FROM_MAINLINE 项（2026-09-05 复核：四项 OPTIONAL 均有真实触发场景与有效 fallback，保留价值 > 维护成本）。

## 更新流程

安装/升级/替换主线 skill → 更新对应行（STATUS/SOURCE 如实）→ 治理变更评审（默认双评审）。
