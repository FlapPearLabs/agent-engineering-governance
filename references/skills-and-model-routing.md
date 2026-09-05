# REF: Skills & Model Routing — 执行方法路由与风险优先模型选择

> Canonical owner: AGENTS.md §0（skill 边界）。本文件是路由表。SKILL_IS_EXECUTION_METHOD / SKILL_IS_NOT_AUTHORITY。

## 1. Skill 路由表（按流程阶段）

| 阶段 | 首选 skill（已安装核验 2026-09-05） | 触发条件 | 边界 |
|---|---|---|---|
| 需求澄清 | `grill-with-docs`（族内唯一深度访谈；`grilling`/`grill-me`/`batch-grill-me` 为轻量变体，不混用于正式 Grill） | 需求真实模糊 | 产出 ADR/词汇表，不是 Spec |
| 形式化 | `to-spec` | Grill/讨论已充分 | 不面试，只合成 |
| 分解 | `to-tickets` | approved 架构/Spec 之后 | 必须套用 AGENTS §4 seam-first 约束壳（见 execution-stage.md §4）；产物标注 Stage 建议 |
| 实现 | `implement` | CODE 票实质实现（MEDIUM+ 强制入口） | EXECUTION ≠ ARCHITECTURE REOPEN；合同空白 → STOP |
| 行为开发 | `tdd` | 正确性行为/合同 | RED 必须反例触发（ticket-lane.md §4） |
| 评审 | `code-review` | push 前自审 + 独立评审可复用其检查轴 | 自审 ≠ 独立评审（R6）；与内置 review-agent 冲突时**本表优先 code-review** |
| 诊断 | `diagnosing-bugs`（优先于轻量 `diagnose`） | 根因调查 | 不得借诊断扩 scope |
| 冲突 | `resolving-merge-conflicts` | 仅存在真实 merge/rebase 冲突 | 结束后回原 lane 流程 |
| 计划 | `writing-plans` | Spec→tickets 之间的实现计划 | 计划不是架构权威 |
| 子代理编排 | `subagent-driven-development` | 多 lane 并行执行 | 两段评审不豁免 R6/exact-SHA |
| 清理 | `simplify-code` | GREEN 之后 | 不得改行为/合同 |
| 交接 | `handoff` | 跨工具/中断/审计场景 | 默认直接 dispatch，不强制 handoff |

- 重复族裁决原则：本表为唯一路由权威；未列出的同职责 skill 不进入工程主链。
- skill 不得僭越权威：实现困难不是调用规划/Spec 技能重设计的理由（发现冲突 → STOP/ESCALATE）。
- skill 使用声明需可核验（AGENTS §3 / ticket-lane.md §5）。

## 2. 模型路由（RISK FIRST, MODEL SECOND）

按平台实际档位映射（档位 = 会话/Agent 工具可选模型层），不硬编码不可核验的具体型号：

| 风险 | 档位 | 说明 |
|---|---|---|
| LOW（机械、胶水、文档） | lite / 低成本档 | 产出可被 L0+抽样 L1 兜住 |
| MEDIUM（常规实现） | default / 中档实现模型 | 已知架构内的实现 |
| LONG CONTEXT（Spec/planning/审计） | 大上下文档（reasoning-tier） | 全文权威阅读与综合 |
| HIGH/CRITICAL（架构、安全、状态、终审） | 最强可用推理档；终审可用外部强模型（Sol 级，人工搬运） | 语义错误成本最高的 gate 集中强模型 |

- 评审多样性：优先不同 context；高风险优先不同模型族（经济允许时）；多样性不可得时如实记录 `MODEL_DIVERSITY = UNAVAILABLE`，保留 fresh context + 独立 grounding + 独立反例 + exact-SHA。
- 外部强评审触发条件（AGENTS §2/§6）：CRITICAL 票、评审分歧、governance/Spec 变更、里程碑、高爆炸半径；绝不默认全票触发。
- 名单核验义务：此表每次治理评审（或至少每季度）对照平台可用档位复核一次；失效名单比没有名单更危险。

## 3. 平台映射备注

- WorkBuddy：Agent 工具 `model` 参数（default/lite/reasoning）+ 会话模型选择；Hermes：runtime 模型配置。
- 外部评审当前人工搬运（PRE-EXTERNAL TERMINAL BARRIER 之后的 minimal handoff），见 AGENTS §10。
