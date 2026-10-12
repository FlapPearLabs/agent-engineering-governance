# H2_LEAN_BOOTSTRAP — lean HOT variant（非 canonical；实验材料，不得当作权威）

> **本文件不是权威层。** 它是 V1.2 **H2（Lazy Skill / Progressive Disclosure）** 实验的
> 变量载体：一份刻意精简的 HOT bootstrap。**治理地图、不变量与路由指针在这里；
> 细节不在这里** —— 细节按路由、在任务相关时再加载（progressive disclosure）。
> 不授予权限、不改变 gate、不覆盖 `RULES.md` / `AGENTS.md` / 仓本地权威；
> 冲突时以 canonical 为准（`RULES.md` > `AGENTS.md` > 本文件）。
> 载体形态参照 `deployment/BOOTSTRAP_CONTRACT.md` §2.4（工作区根 bootstrap 指针）。

## 0. 模式

```text
MODE = H2_LEAN_DISCLOSURE_EXPERIMENT
```

## 1. 开工序列（顺序固定）

```text
S0 PREFLIGHT   执行目标核验：本 worktree 的 HEAD 必须等于任务声明的 base SHA（见运行合同）。
               核验前不得声称任何 repo 状态；不匹配 = 拒绝执行并如实上报。
S1 AUTHORITY   读 H2_RULES.md 全文（harness 投放的当前 RULES.md 全文副本；B 层不变量）。
S2 TASK_CLASS  判定本任务风险级 LOW / MEDIUM / HIGH（判据见 §3；判不出 → MEDIUM）。
S3 LOAD        按 §4 路由表**只**加载与本任务相关的那一层 WARM。不允许"先全读一遍再决定"。
S4 RECEIPT     输出回执（两臂同构字段）。
```

S0–S4 完成后输出一行回执：

```text
H2_RECEIPT = S0:<sha|MISMATCH> S1:<read|missing> S2:<LOW|MEDIUM|HIGH> S3:<targets|none> S4:<full|partial|missing>
```

（S4 槽 = 载体 `CODEBUDDY.md` 的完整读取状态；S3 槽 = 实际加载的 WARM 目标。）

## 2. 安全地板 N1–N8（不可删；精简只改变它们写在哪，不删除其中任何一条）

```text
N1 AUTHORITY BEFORE ACTION     权威不明即停；不猜、不顺手扩权。
N2 UNDERSTAND BEFORE EDIT      改之前知道谁生产、谁消费、谁拥有状态。
N3 EVIDENCE BEFORE CONFIDENCE  UNKNOWN != PASS；完成声明须可复现证据。
N4 STOP ON AUTHORITY UNCERTAINTY   真实权威不确定才停机问人（枚举见 §6）。
N5 ISOLATION                   独立分支/worktree；一个 repo 一个 writer。
N6 NO FALSE PASS               门状态不可坍缩（NOT_RUN/UNKNOWN/KNOWN_BASELINE_FAILURE != PASS）。
N7 NO STALE REVIEW TRANSFER    修复产生新 SHA ⇒ 旧批准不适用于新对象。
N8 NO SILENT BASELINE DRIFT    基线在开工时核验；漂移显式上报，不静默跟随。
```

机械替换者登记（登记为空者不得删除）：仅 N6 有**部分**机械替换
（`scripts/validate_governance.py` + `scripts/validate_public_release.py`，CI 强制，
仅覆盖本仓产物；agent 侧 PASS 措辞纪律仍在 HOT）。其余 N1–N5、N7、N8 无机械替换者，保留。

## 3. 治理地图（细节不在本载体；需要时按 §4 加载）

- 权威链：A 平台/系统 > B 不变量（`RULES.md`）> C 仓本地权威 > D 默认（`AGENTS.md` + references）> E 方法/工具 > F 记忆/偏好。加严永远合法；未覆盖处按本架构执行。
- 证据路由（保留不动）：MECHANICAL QUESTION → 静态工具/测试；BEHAVIORAL CONTRACT → TEST；CROSS-MODULE STRUCTURE → CODEGRAPH；SEMANTIC/CONTRACT → 模型推理；HIGH-VALUE UNCERTAINTY → 强/外部评审。
- 风险级骨架（保留）：LOW 可 L0-only（仓政策允许时；生产代码仍需 L1）；MEDIUM 必须 L1；HIGH 必须 L1 + adversarial。
- **禁令（保留，不缩）**：LOW 不得触发 ESCALATION 清单（除非命中清单本身）；禁止"配置即错误的门"（未测基线的门）；门状态不得坍缩；`SELF_REVIEW != INDEPENDENT_REVIEW`（gate 存在时）。
- **细节下沉清单（以下内容不在本载体，按路由加载）**：
  - 票生命周期 / DAG / 分解细节 → `references/ticket-lane.md`；
  - Stage 编组 / 分解 gate 序列细节 → `references/execution-stage.md`；
  - CodeGraph 三模式 / 生命周期细节 → `references/codegraph-grounding.md`、`references/project-continuity-contract.md`；
  - 状态 / 恢复 / 留痕细节 → `references/project-state-persistence.md`；
  - 评审 / 修复预算 / 饱和细节 → `references/review-and-repair-saturation.md`；
  - CI / 集成细节 → `references/git-ci-integration.md`；
  - 静态门框架 / defect→gate 细节 → `references/static-analysis-and-code-intelligence.md`；
  - 记忆 / 学习闭环细节 → `references/engineering-memory.md`；
  - Skill 路由细节 → `references/skills-and-model-routing.md`。

## 4. 路由表（只加载命中行）

```text
IF 任务触及 票生命周期 / DAG / 分解 / 缝
  → references/ticket-lane.md；references/execution-stage.md

IF 任务触及 持久化 / 状态 / 编排 / 身份 / provenance
  → references/project-state-persistence.md；references/project-continuity-contract.md

IF 任务触及 CI / release / merge / gate 接线
  → references/git-ci-integration.md；references/static-analysis-and-code-intelligence.md

IF 任务是 评审 / 修复 / 饱和 / 仲裁 / 报告
  → references/review-and-repair-saturation.md

IF 任务触及 CodeGraph / 结构接地 / 依赖图
  → references/codegraph-grounding.md

IF 任务是 Skill 选择 / 模型路由 / Skill 执行
  → references/skills-and-model-routing.md；skills/README.md

IF 任务是 记忆 / 学习闭环
  → references/engineering-memory.md

IF 任务涉及 语言工具选型 / 静态门采纳
  → references/static-analysis-and-code-intelligence.md
```

路由纪律：
- 一次任务通常命中 1–3 行，不是全部 8 行。
- 命中行之间有重叠时读**每行第一个**（更具体的 owner）；重复读取不是默认值。
- 加载后发现需要未命中的目标 → 可追加加载，并记 `ESCALATED_LOAD`。
- **副本读取（v5）**：命中的每个目标，实际读取路径 = `H2_WARM/<目标>`
  （例如 `H2_WARM/references/ticket-lane.md`；由 harness 投放、与本文同版）。
  上表坐标为**声明坐标**；run 树自带的 `references/**` 是历史版本，不作为治理读取面。
- **每个实际加载都必须在 run 的 telemetry 中记录**（格式见运行合同）。

## 5. Skill 路由（任务相关时才加载）

首次执行与阶段/技术栈变化时：按 `references/skills-and-model-routing.md` §1 选择适用的工作流 Skill；
可用 → 读完整 SKILL.md 原文并应用；不可用 / 不适用 → 记 `SKILL_UNAVAILABLE` 并按其已定义 fallback 执行；
使用后输出短报告（名称 / 目的 / 动作 / 结果 / 证据 / 限制）。**不为凑清单加载全部 Skill。**

## 6. 停机条件（仅这些停机问人）

```text
USER_DECISION_REQUIRED / CONTRACT_CONFLICT / SPEC_AMENDMENT_REQUIRED /
EXTERNAL_EVIDENCE_REQUIRED / AUTHORIZATION_FAILURE / UNRESOLVABLE_CONFLICT / MILESTONE_COMPLETE
```

授权已覆盖的路径**自主推进**，不问"是否继续"。

## 7. 机械门（不进 HOT，但结论必须落到它们上）

```text
COLD = scripts/ + schemas/ + tests/ + CI workflows
```

- 本仓任何改动 → `scripts/validate_governance.py` 必须绿。
- 公开产物 / 身份门 → `PUBLIC_RELEASE=1 python3 scripts/validate_public_release.py`。
- 状态文件改动 → `scripts/validate_project_state.py`。
- 门未跑 ≠ 通过。跑不动 → 如实报 `ENV_BLOCKED`，不得报 PASS。

## 8. 边界声明

- 本文件**不含**任何 canonical 语义的新增、删除或改写。
- 本文件**不**弱化 `RULES.md` 任一条；冲突时 `RULES.md` 胜出。
- 本文件**不**授予权限、不设 gate、不定义豁免。
- 完整 canonical 治理在 `AGENTS.md`（全文）+ `RULES.md` + `references/`。
  **lean 的含义 = "先读薄入口，再按需读权威"，不是"什么都不读"。**
