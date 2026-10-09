# H1_LEAN_BOOTSTRAP — lean HOT variant（非 canonical；实验材料，禁止当作权威）

> **这不是权威层。** 它是 H1 实验的**变量载体**：一份比 `AGENTS.md` 更薄的
> HOT bootstrap，用于检验「更少热上下文是否损失高价值 catch」。
> 它不授予任何权限、不改变任何 gate、不覆盖 `RULES.md` / `AGENTS.md` / 仓本地权威。
> 冲突时**以 canonical 为准**（`RULES.md` > `AGENTS.md` > 本文件）。
> 载体形态遵循 `deployment/BOOTSTRAP_CONTRACT.md` §2.4（工作区根 bootstrap 指针）。

## 0. 你现在处于哪种模式

```text
MODE = H1_LEAN_BOOTSTRAP_EXPERIMENT
```

本文件只在 H1 实验的 variant arm 中作为 HOT 面出现。canonical 控制组看到的是
`AGENTS.md`（被 8000 字符上限截断）。两臂之差**只有本文件的加载策略**。

## 1. 开工前必须做的四件事

顺序不可换。

```text
S1  AUTHORITY      读 RULES.md 全文（B 层不变量，6843 js chars，不在注入通道内，
                    任何情况下都必须显式读取）。冲突算法 A>B>C>D 见 R1。
S2  TASK_CLASS     判定本任务的风险级：LOW / MEDIUM / HIGH（判据见 §3）。
                    判不出 → 按 MEDIUM。
S3  LOAD           按 §4 路由表**只**加载与本任务相关的那一层 WARM。
                    不允许「先全读一遍再决定」。
S4  BASELINE       有 remote 时：fetch 后核对 default branch 的 exact SHA，
                    记录为 BASELINE_SHA。核验前不得声称任何 repo 状态。
```

S1–S4 完成后输出一行回执：

```text
H1_RECEIPT = S1:<read|missing> S2:<LOW|MEDIUM|HIGH> S3:<loaded files> S4:<sha|NO_REMOTE>
```

## 2. 不可删的底线（无论多薄）

以下 8 条是 H1 的**安全地板**。lean 只允许改变「它们写在哪一层」，
不允许删除它们中任何一条没有替代控制的内容。

```text
N1 AUTHORITY BEFORE ACTION     权威不明即停；不猜、不顺手扩权。
N2 UNDERSTAND BEFORE EDIT      改之前知道谁生产、谁消费、谁拥有状态。
N3 EVIDENCE BEFORE CONFIDENCE  UNKNOWN != PASS；完成声明须可复现证据。
N4 STOP ON AUTHORITY UNCERTAINTY
                              真实权威不确定才停机问人（枚举见 §5）。
N5 ISOLATION                  生产改动走独立分支/worktree；一个 repo 一个 writer。
N6 NO FALSE PASS              门状态不可坍缩（NOT_RUN/UNKNOWN/BASELINE_FAILURE ≠ PASS）。
N7 NO STALE REVIEW TRANSFER   修复产生新 SHA ⇒ 旧批准不适用于新对象。
N8 NO SILENT BASELINE DRIFT   基线在开工时核验；漂移显式上报，不静默跟随。
```

### MECHANICAL_REPLACEMENT 声明

lean variant 允许把**已被机械控制完整覆盖**的条款从 HOT 文本中移除，
但必须在此登记替换者。登记为空 ⇒ 该条款仍在 HOT 且不得删除。

| 底线 | 机械替换者 | 覆盖完整性 |
|---|---|---|
| N5 ISOLATION | 无（保留在 HOT） | — |
| N6 NO FALSE PASS | `scripts/validate_governance.py` + `scripts/validate_public_release.py`（COLD 层，CI 强制） | 仅覆盖**本仓**产物；agent 侧的 PASS 措辞纪律仍在 HOT |
| N7 / N8 | 无（保留在 HOT） | — |

其余 N1–N4 无机械替换者，保留在 HOT。

## 3. 风险分级（判据，不是标签）

| 风险 | 判据 | 独立评审 |
|---|---|---|
| LOW | 文档 / fixture / 确定性胶水 / 机械配置 / 微型生产修复；不触碰状态、身份、持久化、安全边界 | 生产代码仍需 L1；非生产可 L0-only（**须仓政策允许**） |
| MEDIUM | 常规特性集成、已知接口、多模块 | 必须 L1 |
| HIGH | 持久化、编排、状态、身份/provenance、选择器、安全边界 | 必须 L1 + adversarial |

无法判定 → MEDIUM。**升级容易，降级需要理由。**

## 4. Progressive disclosure 路由表（本 variant 的核心）

只加载命中行。**不预读全量 references。**

```text
IF 任务触及 持久化 / 状态 / 编排 / 身份 / provenance
  → references/project-state-persistence.md
  → references/project-continuity-contract.md
  → references/execution-stage.md

IF 任务触及 CI / release / merge / gate 接线
  → references/git-ci-integration.md
  → references/static-analysis-and-code-intelligence.md

IF 任务是评审 / 修复 / 饱和 / 仲裁
  → references/review-and-repair-saturation.md
  → references/review-evidence.md

IF 任务触及 票生命周期 / DAG / 分解 / 缝
  → references/ticket-lane.md
  → references/execution-stage.md

IF 任务触及 CodeGraph / 结构接地 / 依赖图
  → references/codegraph-grounding.md

IF 任务是 Skill 选择 / 模型路由
  → references/skills-and-model-routing.md

IF 任务是 MICRO / LOW 且仅改文档或 fixture
  → 不加载架构 / 状态 / 持久化 / 编排类 reference
  → 聚焦检查 + 诚实标注证据形态

IF 任务是记忆 / 学习闭环
  → references/engineering-memory.md

IF 任务涉及语言工具选型
  → references/static-tooling-profiles.md
```

**路由纪律**：

- 一次任务通常命中 1–3 行，不是全部 9 行。
- 命中行之间有重叠时读**每行第一个**（更具体的 owner），重复读取不是默认值。
- 加载后若发现需要未命中的 reference，可追加加载并记录 `ESCALATED_LOAD`。
- **Skill 选择语义本轮不变**（H2 单独测）。本文件不改变何时用 Skill。

## 5. 停机条件

仅以下情况停机问人：

```text
USER_DECISION_REQUIRED / CONTRACT_CONFLICT / SPEC_AMENDMENT_REQUIRED /
EXTERNAL_EVIDENCE_REQUIRED / AUTHORIZATION_FAILURE /
UNRESOLVABLE_CONFLICT / MILESTONE_COMPLETE
```

授权已覆盖的路径**自主推进**，不问「是否继续」。

## 6. 机械层的门（不进 HOT，但必须跑）

```text
COLD = scripts/ + schemas/ + tests/ + CI workflows
```

这些**不是**启动时阅读的内容，但结论必须落到它们的输出上：

- 本仓任何改动 → `scripts/validate_governance.py` 必须绿。
- 公开产物 / 身份门 → `PUBLIC_RELEASE=1 python3 scripts/validate_public_release.py`。
- 状态文件改动 → `scripts/validate_project_state.py`。
- 门未跑 ≠ 通过。跑不动 → 如实报 `ENV_BLOCKED`，不得报 PASS。

## 7. 边界声明

- 本文件**不含**任何 canonical 语义的新增、删除或改写。
- 本文件**不**弱化 `RULES.md` 任一条；冲突时 `RULES.md` 胜出。
- 本文件**不**授予权限、不设 gate、不定义豁免。
- 完整 canonical 治理在 `AGENTS.md`（151 行）+ `RULES.md`（75 行）+ `references/`。
  本文件只是**更薄的入口**——若你从未读过 canonical，本文件不足以让你合规工作。
  **S1 是强制的：lean 意味着「先读薄入口，再按需读权威」，不是「什么都不读」。**
