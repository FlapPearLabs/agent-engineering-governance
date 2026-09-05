# Skills Governance

## 政策

1. **不 vendor 第三方 skill 内容**。本目录只维护治理元数据（来源、版本、期望能力、路由、兼容性）。只有当许可与所有权明确允许时才收录实际内容。
2. **SKILL_IS_EXECUTION_METHOD / SKILL_IS_NOT_AUTHORITY**：路由唯一权威 = `references/skills-and-model-routing.md` §1。
3. skill 使用声明必须可核验：被实际调用/读取的证据，否则报 `UNVERIFIED`。
4. 新装 skill 进入主链前必须先入路由表与 manifest。

## 主链 skill manifest（工程技能族，2026-09-05 实测）

> **REPRODUCIBILITY = INCOMPLETE**：本机 SKILL.md 均无 version/license/source 元数据，上游 repo/commit 未在本轮确认。
> **按外部评审要求：在 manifest 补齐（source + commit + license）之前，治理候选 DEPLOYMENT受阻**（不激活、不注入 MEMORY）。补齐前本表如实登记现状。

| skill | SOURCE | VERSION/COMMIT | LICENSE | REAL CONTRACT（核验摘要） | ROUTING |
|---|---|---|---|---|---|
| grill-with-docs | 本机安装（`~/.workbuddy/skills/`），上游待录 | UNKNOWN | UNKNOWN | 深度访谈 + ADR/词汇表产出 | 需求澄清首选 |
| to-spec | 同上 | UNKNOWN | UNKNOWN | 由对话合成 Spec，无访谈 | 形式化 |
| to-tickets | 同上 | UNKNOWN | UNKNOWN | tracer-bullet 垂直切片 + blocking edges + "work the frontier"；`disable-model-invocation: true` | 分解（+seam-first 约束壳） |
| implement | 同上 | UNKNOWN | UNKNOWN | spec/tickets 驱动实现入口 | MEDIUM/HIGH 实现入口 |
| tdd | 同上 | UNKNOWN | UNKNOWN | red-green-refactor 纪律 | 行为开发 |
| code-review | 同上 | UNKNOWN | UNKNOWN | 固定基点的 Standards+Risk 双轴评审 | 评审（工程轴）/自审 |
| review-agent | 同上 | UNKNOWN | UNKNOWN | 只读缺陷列举，服务委派评审（未提交变更/diff） | 评审（委派子代理）；与 code-review 互补 |
| diagnosing-bugs | 同上 | UNKNOWN | UNKNOWN | 疑难 bug/回归诊断循环 | 诊断 |
| resolving-merge-conflicts | 同上 | UNKNOWN | UNKNOWN | 真实 merge/rebase 冲突处理 | 冲突 |
| writing-plans | 同上 | UNKNOWN | UNKNOWN | bite-sized 实现计划 | 计划 |
| subagent-driven-development | 同上 | UNKNOWN | UNKNOWN | delegate_task 子代理两段评审 | 子代理编排 |
| simplify-code | 同上 | UNKNOWN | UNKNOWN | GREEN 后并行清理 | 清理 |
| setup-matt-pocock-skills | 同上 | UNKNOWN | UNKNOWN | 仓内 tracker/标签/文档布局一次性配置 | 一次性 setup |

TODO（NEXT，解锁 deployment 的条件）：确认上游仓库与 commit → 登记 LICENSE → 建立 update 策略（升级前 diff 行为变化）。
