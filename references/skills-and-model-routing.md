# REF: Skills & Model Routing — 执行方法路由与风险优先模型选择

> Canonical owner: AGENTS.md §0（skill 边界）。本文件是路由表（D 层默认）。SKILL_IS_EXECUTION_METHOD / SKILL_IS_NOT_AUTHORITY。
> skill 契约细节以各 SKILL.md 原文为准；本表与其冲突时，修本表而不是曲解 skill。各 skill 的 STATUS/SOURCE/FALLBACK 见 `skills/README.md` 主线清单（V1.1：13 项全部 INSTALLED 于基准环境，SOURCE=UNKNOWN 者按行 FALLBACK，无部署阻塞）。

## 1. Skill 路由表（按流程阶段；2026-09-05 安装与契约核验）

| 阶段 | 首选 skill | 触发条件 | 边界 |
|---|---|---|---|
| 流程定位 | `ask-matt`（可选） | 技能可用且不确定当前工程阶段 | OPTIONAL FLOW ROUTER；非权威、非批准、非合同校验器；缺失不阻断治理 |
| 需求澄清 | `grill-with-docs`（深度访谈；`grilling`/`grill-me`/`batch-grill-me` 为轻量变体） | 需求真实模糊 | 产出 ADR/词汇表，不是 Spec |
| 形式化 | `to-spec` | Grill/讨论已充分 | 不面试，只合成 |
| 分解 | `to-tickets` | approved 架构/Spec 之后 | 必须套用 AGENTS §4 seam-first 约束壳（execution-stage.md §6）；产物标注 Stage 建议 |
| 实现 | `implement` | CODE 票实质实现（MEDIUM/HIGH 默认强制入口；LOW 不强制） | EXECUTION ≠ ARCHITECTURE REOPEN；合同空白 → STOP |
| 行为开发 | `tdd` | 正确性行为/合同 | RED 必须反例触发（ticket-lane.md §4） |
| 评审（工程轴） | `code-review` | push 前自审 + 独立评审可复用其检查轴 | 自审 ≠ 独立评审 gate（R4 条件式） |
| 评审（委派子代理） | `review-agent` | 编排者把**未提交变更/diff**委派给只读缺陷列举 subagent 时 | 与 code-review **互补**：前者=委派型只读列举，后者=固定基点标准+风险双轴；同一票可先后使用，互不替代独立 gate |
| 诊断 | `diagnosing-bugs`（优先于轻量 `diagnose`） | 根因调查 | 不得借诊断扩 scope |
| 冲突 | `resolving-merge-conflicts` | 仅存在真实 merge/rebase 冲突 | 结束后回原 lane 流程 |
| 计划 | `writing-plans` | Spec→tickets 之间的实现计划 | 计划不是架构权威 |
| 子代理编排 | `subagent-driven-development` | 多 lane 并行执行 | 两段评审不豁免 R4/exact-SHA |
| 清理 | `simplify-code` | GREEN 之后 | 不得改行为/合同 |
| 交接 | `handoff` | 跨工具/中断/审计场景 | 默认直接 dispatch，不强制 handoff |

- 重复族裁决：本表为唯一路由权威；未列出的同职责 skill 不进入工程主链。
- skill 不得僭越权威：实现困难不是调用规划/Spec 技能重设计的理由（发现冲突 → STOP/ESCALATE）。
- skill 使用声明需可核验（被实际调用/读取），否则报 `UNVERIFIED`。

## 2. 模型路由（RISK FIRST, MODEL SECOND；D 层默认）

按平台实际**档位**映射，不硬编码不可核验的具体型号：

| 风险 | 档位 | 说明 |
|---|---|---|
| LOW（机械、胶水、文档） | lite / 低成本档 | 产出可被 L0（+生产票 L1）兜住 |
| MEDIUM（常规实现） | default / 中档实现模型 | 已知架构内的实现 |
| LONG CONTEXT（Spec/planning/审计） | 大上下文档（reasoning-tier） | 全文权威阅读与综合 |
| HIGH + ESCALATION 触发 | 最强可用推理档；终审可用外部强模型（Sol 级，人工搬运） | 语义错误成本最高的 gate 集中强模型 |

- ESCALATION 触发清单 = AGENTS §3（架构不确定、并发/canonical、安全边界、评审分歧、Spec/governance、里程碑、高爆炸半径）。
- 评审多样性：优先不同 context；高风险优先不同模型族（经济允许时）；不可得时如实记录 `MODEL_DIVERSITY = UNAVAILABLE`，保留 fresh context + 独立 grounding + 独立反例 + exact-SHA。
- 自动化评审不可用（配额/故障）= `UNAVAILABLE`：按仓政策路由到指定独立评审，不得静默豁免。
- 名单核验义务：本表每次治理评审（或至少每季度）对照平台可用档位复核；失效名单比没有名单更危险。

## 3. 平台映射备注

- WorkBuddy：Agent 工具 `model` 参数（default/lite/reasoning）+ 会话模型选择；Hermes：runtime 模型配置。
- 外部强评审当前人工搬运（PRE-EXTERNAL TERMINAL BARRIER 之后的 minimal handoff），见 AGENTS §10 与 deployment/BOOTSTRAP_CONTRACT.md。

## 4. 派发元数据 recipe（MODEL_DISPATCH_METADATA；RISK FIRST, MODEL SECOND）

派发决策按固定字段组记录并逐字段核对，不以散文冒充合同。字段组**顺序即语义**：

```text
ROLE
TASK
RISK
MODEL_OR_TIER
REASONING_EFFORT
WHY
EXPECTED_OUTPUT
ESCALATE_IF
```

- **顺序是规范的（§2 的 RISK FIRST, MODEL SECOND 在此展开为字段序）**：`RISK` 必须先于 `MODEL_OR_TIER` 记录；先定风险，再由风险决定档位——风险驱动档位选择，反之不成立。
- `MODEL_OR_TIER` 记录的是**档位 / profile 引用**（§2 的档位名），**不是**具体型号：具体型号是 **profile / 可更新值，不是不变量**。
  后续 profile 更新换掉具体型号时，**不得要求改动本节的规范文本**——可核验性来自 profile 引用，不来自写死的型号字面量。
- 缺任一字段 = 派发记录无效。
- 顺序错误 = 派发记录无效。
- 把不可核验的具体型号写死成不变量 = 缺陷，须如实上报，不得静默通过。
- `ESCALATE_IF` **只引用** `AGENTS.md` §3 的 ESCALATION 触发清单，不在此重列触发项（清单的单一 owner 是 AGENTS §3）。
- 本 recipe 的合法 / 非法集合是**局部的**：本节**不引入**全局状态机，也不引入共享枚举。

```text
LEGAL    RISK 记录在 MODEL_OR_TIER 之前的完整字段组
LEGAL    MODEL_OR_TIER 解析为 profile 值，更新 profile 不需改不变量
ILLEGAL  缺失任一字段
ILLEGAL  把不可核验的具体型号写死为不变量
```

- CE-28：本字段组**只在本文件定义一次**；其它 surface 只指针 / 链接，不重复定义。
