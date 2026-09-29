# REF: Review & Repair Saturation — 评审分级、收敛仲裁与报告

> Canonical owner: AGENTS.md §6/§9。本文件是**D 层默认**字段表、判据与模板（仓政策可覆盖，记录 OVERRIDE）。
> F3 修复：LOW 评审语义统一为单一规则（见 §1 触发列），与 RULES R4 的条件式独立评审语义一致。

## 1. 评审分级（L0/L1/L2）

| 层 | 承担者 | 核验内容 | 触发（唯一规则） |
|---|---|---|---|
| L0 MACHINE | harness / 脚本 / agent 机械执行 | exact SHA、base SHA、diff 语义范围、**syntax/build、formatter、lint、type、LSP/静态诊断（按仓配置）**、测试执行与结果、回归、ancestry、静态检查、secret/路径扫描、图 base SHA 记录 | **每票必做；L0 先清场——机器能定位的缺陷在进入 L1 前修复并由测试证明** |
| L1 NORMAL | 低成本 fresh context 独立评审 | 合同满足、缝与所有权、scope、失败语义、缺失假设、缺失高价值反例（≥2 个非复制 worker 的新反例）；**不重复报告 L0 已可确定性检出的问题**（效率规则，非豁免） | **生产代码（全部风险级）必须；非生产票按仓政策可选**。即：非生产/机械 LOW 票可 L0-only 闭合（仓政策允许时）；生产代码 LOW/MEDIUM/HIGH 一律 L1 |
| L2 STRONG/EXTERNAL | 强模型/外部独立评审（不同模型族优先） | 架构、安全、状态/并发、身份/provenance、评审分歧仲裁、governance/Spec 变更、里程碑、高爆炸半径 | 仅 AGENTS §3 ESCALATION 清单命中时 |

- **MACHINE BEFORE MODEL（D2/D5）**：升级方向恒为 静态/机器证据 → 测试证据 → 常规模型推理 → 强模型/外部评审，不可反向。工具层级见 `references/static-analysis-and-code-intelligence.md`。

- 独立性语义：fresh context + 独立 grounding（查询独立，非重建库）+ 独立反例。
- 评审顺序：权威 → 票 → repo 图 → 合同 → 反例 → diff → 测试 → CI；不从 worker 解释出发。主问题永远是："这个 exact SHA 是否在真实仓库中实现了合同？"
- `SELF_REVIEW != INDEPENDENT_REVIEW` 仅在独立评审 gate 存在时适用（RULES R4 条件式）。

## 2. REPAIR_VALUE gate

任何 reviewer 驱动的修复（超出初始 blocker）先过：

| 字段 | 取值 |
|---|---|
| IMPACT | HIGH / MEDIUM / LOW |
| REACHABILITY | PRODUCIBLE_STATE / REALISTIC_RECOVERY_STATE / ARBITRARY_SYNTHETIC_STATE |
| EVIDENCE_STRENGTH | EXECUTED / MECHANICALLY_PROVEN / PLAUSIBLE / SPECULATIVE |
| CONTRACT_CONFIDENCE | HIGH / MEDIUM / LOW |
| REPAIR_COMPLEXITY | LOW / MEDIUM / HIGH |
| REGRESSION_RISK | LOW / MEDIUM / HIGH |
| DEFECT_CLASS | 稳定语义类目 |

决策：REPAIR_NOW / BACKLOG / ROUTE_TO_OWNER / INFORMATIONAL / OUT_OF_SCOPE。
经济学 = 期望风险降低 vs（复杂度 + 回归风险）。加固若可能拒绝当前合法输出且权威不明确 → 不自动修（`LEGAL_RUNTIME_REGRESSION_RISK`）。

**高价值类（默认 REPAIR_NOW，severity 标签仅次要）**：身份/provenance 错配；validity 升级；fail-open；安全/隐私/凭据泄漏；现实持久化/恢复损坏；陈旧产物复用；错误完成语义；显式仓库合同违反；控制器/权威所有权违反；可达的原始失效破坏 fail-closed 边界。

### 2.1 `FINDING_IS_TRUE != REPAIR_NOW`（真 finding 不等于修复授权）

> 本节是**修复授权来源**的唯一声明点。§2 字段表定义单条 finding 的价值；本节定义"是否由它产生修复权"。

一条 finding 可以**同时**满足下列全部条件而仍然**不获得**修复授权：

```text
FINDING_IS_TRUE          = YES     # 真实、可复现、机制可检测、reviewer 报告正确
DISPOSITION              = BACKLOG | INFORMATIONAL | ROUTE_TO_OWNER
REPAIR_NOW               = NO
```

推论（均为本节的一部分，不需另找依据）：

- **修复授权来自 `REPAIR_VALUE` + 当前票权威，不来自 finding 的真实性。** 真实只是进入判定的**前提**，不是判定**结果**。
- **可机械检测性不是修复理由。** §2 的 `EVIDENCE_STRENGTH = MECHANICALLY_PROVEN` 描述证据强度，**不**抬高 `DISPOSITION`；"能机械化"回答的是"能否自动发现"，不是"是否应当现在修"。
- **severity 标签（P0–P3）是意见，不是授权。** `SEVERITY_OPINION = P0` 与 `DISPOSITION = BACKLOG` 可以同时为真且不矛盾——P0 意见 + 非高价值类 = 记录并延后。
- 已知高价值 blocker（§2 高价值类）**不可**用本节延后；本节只约束**非**高价值 finding。


## 3. Budget 与 Convergence Arbiter

- `NORMAL_REVIEWER_DRIVEN_REPAIR_BUDGET = 2` 是**默认值**（D 层）：owner/仓政策可按风险与证据质量调高/调低并记录 OVERRIDE；**不可覆盖**的部分 = "已知高价值 blocker 永不因预算耗尽而被豁免"。
- 流程：初始候选 → fresh review → 修复轮 1（仅高价值 blocker）→ fresh review → 修复轮 2（仅高价值 blocker）→ `AUTO_REPAIR_AUTHORITY = EXHAUSTED`。
- 耗尽 ≠ PASS：产生 CONVERGENCE_ARBITER（fresh、高权威、合同/架构向）裁决，五选一：`REPAIR_MORE / SATURATION_REACHED / ARCHITECTURE_REOPEN / ROUTE_TO_OTHER_OWNER / BACKLOG_LONG_TAIL`。
- `REPAIR_SATURATION_REACHED = YES` 判据：无已知高价值 blocker + 近轮缺陷类新颖性低 + 剩余提议边际价值低 + 剩余 findings 多为重复变体/防御加固/合成态/低影响清理。
- Saturation ≠ 无 bug：只表示本票高价值修复区已耗尽。
- 评审探索预算：fresh/third-party 各 2–4 个高价值独立对抗探针；`NEW_COUNTEREXAMPLES = NONE` 合法；禁止机械枚举组合凑数。

### 3.1 预算的票作用域与单调性（`NEW_SHA != NEW_REPAIR_BUDGET`）

> 本节是**预算计数语义**的唯一声明点。§3 的数值是默认值；本节规定它**如何被消耗**。

`NORMAL_REVIEWER_DRIVEN_REPAIR_BUDGET` 是**原始票 / 已授权任务上的累计预算**，不是"每个 SHA 一个"或"每轮评审一个"。

```text
NEW_SHA                 != NEW_REPAIR_BUDGET   # append-only commit 只换证据绑定，不重置换计数器
FRESH_REVIEW            != NEW_REPAIR_BUDGET
NEW_REVIEWER            != NEW_REPAIR_BUDGET   # 换 reviewer 不产生新预算
REVIEWER_DISAGREEMENT   != AUTOMATIC_BUDGET_RESET
MODEL_FALLBACK          != NEW_REPAIR_BUDGET   # 换模型重试不是新一轮修复
```

- append-only repair 的**唯一**作用是把修复绑定到可核验的证据 SHA；它**不**重置计数。
- 预算**只能**由 owner / 仓政策在既有治理语义下**显式**上调（记录 OVERRIDE，见 §3 默认值条款），**不能**由修复动作、评审轮次、reviewer 更替或模型回退自行产生。
- 已知高价值 blocker 不受预算耗尽豁免（§3 首条）；**高价值**判定走 §2 / §2.1，不因预算耗尽而改变。
- **票边界定义预算边界**：预算随票关闭而消失；开启新票 = 新的累计预算（这是唯一合法的重置途径，且由开票行为而非 SHA 变化构成）。


## 4. PASS 语义与 findings 处置

- 合法成功态：`PASS / PASS_WITH_NONBLOCKING_FINDINGS / SATURATION_REACHED_WITH_BACKLOG`。`ZERO_FINDINGS` 不是完成定义。
- 终局问题："这个 exact 候选是否对现实可达状态正确实现其拥有的合同、并在真实信任边界安全失败、无已知高价值 blocker？"
- 每条未修复 finding 必带：FINDING / SEVERITY_OPINION(P0–P3) / DEFECT_CLASS / REACHABILITY / REPAIR_VALUE / DISPOSITION(REPAIRED|BACKLOG|ROUTE_TO_OWNER|INFORMATIONAL|OUT_OF_SCOPE) / WHY_NOT_REPAIRED / OWNER。
- WHO_OWNS_THE_FIX：根因属他模块/他票权威 → ROUTE_TO_OWNER，不造第二弱策略凑零 findings。

### 4.2 POST-PASS 收敛切断（`REPAIR_SATURATION_REACHED` 的默认态）

> 本节是**通过之后是否继续施工**的唯一声明点。§3.1 管预算怎么花，本节管通过之后默认做什么。

当**当前 exact 候选**同时满足：

```text
REQUIRED_REVIEW_QUORUM         = PASS | APPROVED
NO_KNOWN_HIGH_VALUE_BLOCKER    = YES
```

默认状态即：

```text
REPAIR_SATURATION_REACHED = YES
DISPOSITION_DEFAULT        = BACKLOG | INFORMATIONAL
```

以下**单独**出现时**不得**自行重开施工：

```text
P2 / P3 opinion
additional mutation coverage
guard robustness / test robustness
documentation polish
alternative prose encoding
extra defensive hardening
```

- 重开**仅**允许于：fresh 证据依 §2 / §2.1 建立了**高价值 blocker**。**severity 标签本身不构成授权**（§2.1）。
- 收敛后的剩余风险**有意**留给独立评审承担：把 `REPAIR_SATURATION_REACHED = YES` 当作"本票高价值修复区已耗尽"（§3），**不**当作"再无弱化空间"。
- 本节**不**削弱 RULES R4 独立评审 gate：saturation 之后 reviewer 仍可报告新事实；变的是**处置默认值**，不是**报告权利**。

### 4.1 缺陷的机械可检测性元数据（**建议性证据**）

reviewer finding **MAY** 附带以下**建议性**元数据，帮助 executor 判断该缺陷类能否下沉到机器门：

```text
DEFECT_CLASS =              # 稳定语义类目
MACHINE_DETECTABLE = YES / NO / UNCERTAIN
CANDIDATE_MECHANICAL_LAYER = # §21.2 层级中的候选层
PROMOTION_VALUE = # 见框架 §21.1（reviewer 建议值，不自动生效）
```

**权威边界（不可越界）**——reviewer **不**因附带这些元数据而获得：

```text
修改治理的权威
安装工具的权威
扩当前票 scope 的权威
自动创建下游票的权威
```

- finding **!=** 自动真理：executor / orchestrator **仍必须核验**该 finding（§6.1「观测是证据，不是权威」：观测永不自我授权）。
- finding **!=** 自动建门：晋升判定与处置见 `references/static-analysis-and-code-intelligence.md` §21（value-gated，非自动规则扩散）。
- 语义/合同判断类 finding 的 `MACHINE_DETECTABLE` 通常为 `NO`，应明确标出以免被误下沉（框架 §3/§19）。

### 4.3 `SATURATION != REVIEW_GATE_BYPASS`（饱和不得替代评审门）

> 本节是 **`SATURATION != REVIEW_GATE_BYPASS` 这一否定式的唯一声明点**。§3 管修复授权，§3.1 管预算计数，§4.2 管通过之后默认做什么；本节管**这三者与评审门的优先关系**——它存在的唯一理由是防止前两者被误当成评审门的替代品。
> 正向的评审要求本身（治理变更须双独立评审对同一 exact HEAD PASS）其 owner 是 **AGENTS §8**，本节**不**复述、只声明它不可被本文件其它条款旁路。

三个机制各管一件事，互不越权：

```text
REPAIR_BUDGET           管自动修复授权（还能不能自己修）
CONVERGENCE_ARBITER     管剩余 findings 的处置（怎么归类）
REQUIRED_REVIEW_QUORUM  管集成资格（能不能进 main）
```

因此：

```text
SATURATION_REACHED  !=  REQUIRED_REVIEW_QUORUM_PASS
```

- **CONVERGENCE_ARBITER 不得把阻断性结论改写成通过。** `CHANGES_REQUESTED` / `REQUEST_CHANGES` / `REJECT` / `FAIL` **不**得被仲裁、预算耗尽、严重性意见或"剩余工作边际价值低"改写为 `PASS` / `APPROVED`。仲裁决定 finding 的**去向**，不决定评审的**结论**。
- **饱和不满足任何未满足的 required review gate。** 当仓政策要求 quorum（AGENTS §8 治理变更默认：合同向 + 一致性向对同一 exact HEAD 双 PASS）时，`SATURATION_REACHED` **不**构成该 gate 的替代证据。§4.2 自身的前置条件即 `REQUIRED_REVIEW_QUORUM = PASS | APPROVED`；该条件未满足时 §4.2 的收敛切断**不启动**（§4.2 不是绕过它的入口）。
- **预算耗尽与集成资格是两个独立字段，可同时成立。** required reviewer 仍返回阻断结论时：

```text
AUTO_REPAIR_AUTHORITY  = EXHAUSTED        # 有效：不再自动修复
INTEGRATION_AUTHORITY  = NOT_SATISFIED    # 同时成立：不得集成
```

  耗尽的是**修复权**，未满足的是**集成权**。二者与 §3 首条"已知高价值 blocker 不豁免"**各自独立、互不覆盖**：§3 首条仍是本文件唯一标为"不可覆盖"的部分，本节**不**改变、不降级、不让位于它——预算耗尽与仲裁都**不是**高价值 blocker 的豁免路径。

合法下一步**仅限既有权威机制**（不得静默重解释阻断结论）：

```text
owner 显式授权的新纠正票（可含显式预算 OVERRIDE，见 §3）
ARCHITECTURE_REOPEN / CONTRACT_REOPEN（确有必要时）
ROUTE_TO_OTHER_OWNER（根因属他模块权威）
其它既有已授权解决路径
```

- **不得以"评审者购物"绕过本节。** 反复更换 fresh reviewer 直到某人给出 PASS 属对本条的规避。仅当仓既有 reviewer 路由 / 可用性规则（§3 模型 fallback、AGENTS §6 reviewer 优先级）允许时，更换 replacement reviewer 才合法；**预算耗尽本身不构成更换理由**，有效的 `CHANGES_REQUESTED` 不得因预算耗尽而被抹平。
- 本节**不**削弱 §4.2：quorum 满足后，P2/P3 单独仍不重开施工。变的是**集成资格的判定源**，不是**通过后的收敛默认值**。
- 本节**不**新增检测器：它是**授权/资格**语义，判定者是当前票权威与独立评审（与 §2.1、§6.6 同向，见 `audit/PAIN_TO_POLICY_MAP_V2.md` P22 增补）。本节**不**为自身声明第二条集成资格规则——AGENTS §8 仍是治理变更评审要求的 owner。

## 5. Reporting（novelty-first 模板）

```
# WHAT WE LEARNED THIS ROUND
NEW_CODEGRAPH_FINDINGS =      # 无则 NONE
NEW_CONTRACT_FINDINGS =
NEW_COUNTEREXAMPLES =         # WORKER_/REVIEWER_/THIRD_PARTY_ 分属；每条注攻击的假设与是否改变代码
NEW_BUGS_FOUND_DURING_REVIEW =
ASSUMPTIONS_INVALIDATED =
NEW_CROSS_MODULE_RISKS =
SURPRISES =

# WHAT CHANGED
IMPLEMENTATION_DELTA =
TEST_DELTA =

# GATES                      （常规行压缩；任何非 PASS 状态必须展开证据块，见 git-ci-integration §3）
EXACT_SHA / CODEGRAPH / TDD / TESTS / CODE_REVIEW / PR_CI / POST_CI_REVIEW

# DECISION
UNRESOLVED_P0 / UNRESOLVED_P1 / READY_FOR_EXTERNAL_REVIEW
```

已知事实不重述；仅在被违反、异常影响、或明确索要审计细节时展开。`PR_CI_COMPRESSION_ALLOWED = PASS_ONLY`。

## 6. 证据消费与 reviewer 权威分离（消费规则；字段名不在此声明）

本节的 owner 范围是**消费规则**本身：**谁可以写**、**consumer 可以／不可以从证据里推导什么**。
**字段名、闭合集与机器形状**的唯一声明点在 `references/review-evidence.md`（Review Evidence 接口）；
本节**只引用 / 指针**该接口，**不重声明**其字段名与闭合集，也不定义竞争性 Review Evidence 接口
（`AC-38` owner 唯一性；`AC-44` 条件 6；`CE-28` 双声明必须收敛回单一 owner）。
本节把既有原则"已批准编辑面 / 观测增量 / 影响面是三个不同的东西"
（`references/project-continuity-contract.md` §6.7 F4 的三面分离）延伸到证据接口——**引用**该同源
关系，不重复定义它。

```text
CE-35-A  AUTHORITY  观测到的 changed files 集合永不自我授权为已批准的语义 scope
CE-35-B  AUTHORITY  该状态只能由 reviewer 权威写入，不由 producer 观测自动升格
CE-35-C  FORBIDDEN  producer 观测把该状态升格为已批准 scope
CE-36-A  FORBIDDEN  机器证据包填充或自批独立 reviewer verdict
CE-36-B  REQUIRED   reviewer 决定引用与机器事实分字段保存、互不冒充、互不可推
CE-36-C  FORBIDDEN  机器退出码 0 / 空跑 / 无有效结果被当作 reviewer verdict
CE-36-D  REQUIRED   Stage packet 只引用 canonical 证据
CE-36-E  FORBIDDEN  Stage packet 把 canonical 证据复制为第三个可变账本
CE-36-F  REQUIRED   integrator 以同一候选绑定消费证据
CE-38-A  OWNER      消费规则的唯一 canonical owner = references/review-and-repair-saturation.md
CE-38-B  OWNER      字段名 / 闭合集 / 机器形状的唯一 canonical owner = references/review-evidence.md
CE-38-C  POINTER    其它 canonical surface 只引用 / 链接同一规则，不重复定义
AC-44-P  POINTER    本节只指针证据接口，不复制它
CE-28-D  REJECT     同一规则在两个 canonical 文件各有一份定义（双 owner）→ 拒绝并收敛
```

### 6.1 语义 scope 的权威分离（`REQ-W2-05` / `AC-35` / `INV-04`）

- **观测是证据，不是权威**。观测到的 changed files 记录"改了什么"；它**永不**自我授权为"允许改什么"。
  一个其 changed files **超出**已批准面的证据包**不因此**获得更宽的已批准 scope：超出部分只扩大**差异
  记录**（与 `UNAPPROVED_DELTA_DETECTED` 同源），扩张的唯一途径是显式 authority action 后重算。
- 语义 scope 的结论状态**只能**由 reviewer 权威写入；producer 观测**不得**自动升格它。写入方与推导规则
  由本节声明；**该字段的字段名与其唯一声明点**在 `references/review-evidence.md`，本节不重声明。

### 6.2 机器证据包不自批 reviewer verdict（`REQ-W2-06` / `AC-36` / `AC-08` / `INV-03`）

- 机器事实（producer 观测、单条检查结果、CI 观测状态）只描述"发生了什么"；独立 reviewer verdict
  **只能**由 reviewer 写入。机器证据包**永不**填充独立 reviewer verdict（self-approval 被禁止）。
- reviewer 决定引用与机器事实**分字段**保存：二者互不冒充，且不可由一个推出另一个。把 reviewer 决定
  与机器事实混装在同一字段／同一清单即违约。
- 退出码 0、结构性合法、或存在某个字符串**都不等价于** reviewer verdict：validator 以 exit 0 收场但
  **空跑、无有效结果**时，consumer **不得**因此打开 gate（`AC-08`）。
- 字段名与其唯一声明点在 `references/review-evidence.md`；本节只声明**谁能写、consumer 可推导什么**。

### 6.3 consumer 独立性：integrator 与 Stage packet

- **Integrator 使用同一候选绑定**：证据包的 subject（repo / base / candidate）必须与被集成的候选一致；
  绑定不一致的证据**不得**作为该候选的证据被消费，也不得跨候选继承结论。
- **Stage packet 只引用，不复制**：Stage packet 记录**引用槽位**与结论，不把 canonical 证据复制成
  **第三个可变账本**（`INV-07`：不新建第二证据数据库）。Stage packet 的既有写入面见
  `references/execution-stage.md`；本节只声明其**消费规则**，不新建第二个 Stage 权威。
- 消费方**只指针**证据接口，不定义竞争性接口（`AC-44` 条件 6）。

### 6.4 单一 owner 与指针纪律（`AC-38` / `CE-28`）

```text
单一 owner  消费规则只在本文件定义一次；字段名 / 闭合集 / 机器形状只在 references/review-evidence.md
指针纪律    其它 canonical surface 只引用 / 链接该接口；重复定义 → 拒绝并收敛回单一 owner
消费方纪律  消费方不得自带局部副本替代 canonical 声明（第二声明点 = CE-28 违约）
```

### 6.5 重复低层发现 = 缺门证据（与晋升机制联动）

> 晋升判定与处置的唯一声明点 = `references/static-analysis-and-code-intelligence.md` §21。本节只声明**评审/饱和侧的联动语义**。

原则：

```text
reviewers 反复花独立评审预算重新发现同一确定性的低层缺陷类
→ 这是"缺少合适机械门"的证据
```

- **一次出现 ≠ 自动治理缺陷。** 单次发现**不**构成晋升理由；晋升仍走 §21.1 的 value gate（否则规则会指数扩散，误报本身成为新缺陷类）。
- 门一旦建立并生效，reviewer **不**应再把独立评审预算反复花在该机器可判缺陷类上（`DO_NOT_SPEND_REASONING_ON_MACHINE_PROVABLE_FACTS`）——按 §1 的 L1 纪律，不重复报告 L0 已可确定性检出的问题。
- 该联动**不**削弱 RULES R4 独立评审 gate，也不使静态门绿灯升级为语义/合同结论（框架 §19）。
- `REPAIR_SATURATION_REACHED = YES` 判据（§3）**不**因存在机械可判缺陷而自动成立：饱和是**修复预算**判据，晋升是**门建设**判据，两者独立。

### 6.6 `META_GOVERNANCE_RECURSION_CUTOFF`（加固治理机制本身不递归授权）

> 本节是**元治理施工**的唯一声明点。§6.5 管"缺门"的证据方向；本节管"为补门而加固门"的**递归**边界。

当一次修复主要加固的是**治理装置自身**——

```text
a governance guard / validator / mutation test / negative-control test
a test-of-test / a detector for governance prose
```

——该修复**不得**仅因"被加固的机制又暴露了另一处非阻塞弱化"而**递归授权**另一次修复。

```text
ONCE (核心受管辖合同已满足 AND 无高价值 blocker 残留)
  → 记录残余弱化
  → 停止机械化
  → 剩余语义风险留给独立评审承担
```

经济判据（与 §2 的 REPAIR_VALUE 经济学同向）：

```text
MECHANIZATION_VALUE  >  MECHANIZATION_COST + MAINTENANCE_COST
```

- 机械化**自身**仍受 `MINIMUM_NECESSARY_COMPLEXITY` 约束：为证明一条散文规则而新增通用解析器 / 变异框架 / Markdown 分类器 / guard-of-guard，属于**不**满足该不等式。
- 本节**不**禁止报告，只禁止**递归施工**；新事实照常可被报告并按 §4.2 归入 `BACKLOG` / `INFORMATIONAL`。
- 本节与 §6.5 的分工：§6.5 说"缺门"应走晋升；本节说"已建的门不必被加固到无穷"。两者不冲突——**门该不该建**与**门是否已足够**是不同问题。


## 7. 审计可见性 recipe（按需；`REQ-W4-02a` / `AC-13` / `AC-38`）

本节是**追加**：owner 范围是**审计可见性 recipe 本身** —— 一个审计 / 外审 reviewer 在给出结论前，
必须先声明它**实际看到了什么证据**。本节**不重述** §6 的证据消费与 reviewer 权威分离规则
（§6 仍是其唯一声明点），也**不重声明** Review Evidence 接口的字段名与闭合集
（该接口的唯一声明点见 `references/review-evidence.md`）。

### 7.1 适用方式（按需）

```text
AUDIT_VISIBILITY_RECIPE            = ON_DEMAND
RECIPE_MANDATORY_PER_TICKET        = NO
VISIBILITY_DOMAIN                  = SEEN | PARTIAL | NOT_SEEN | UNCERTAIN
COMPLETENESS_OUTPUTS               = CONTEXT_COMPLETENESS_FOR_DECISION_AUDIT, FULL_HISTORICAL_TRANSCRIPT_COMPLETENESS
COMPLETENESS_OUTPUTS_COLLAPSIBLE   = NO
```

本 recipe **按需（on demand）** 应用：仅在审计 / 外审 / gate 需要重建"reviewer 到底看到了什么"时启用。
它**不是**每票强制的字段集 —— 常规票不因此新增必填字段，§5 的报告模板也不因此变成全量字段清单。
把本 recipe 当成本票强制字段集，与其按需语义不符。

### 7.2 字段组（按需）

```text
evidence               实际读取到的证据对象（引用 / 标识）
requested SHA          本次结论所针对的 exact SHA
actually read scope    实际读取到的范围（文件 / 提交 / 区间 / 产物）
visibility             取值域 SEEN | PARTIAL | NOT_SEEN | UNCERTAIN
supports               该证据支持了什么
missing                缺失 / 不可见的部分
verdict impact         缺失对结论的限制
recovery artifact      可恢复该证据的产物或复现路径；无则 NONE
```

### 7.3 可见性取值域

```text
SEEN        证据被直接读取并核验
PARTIAL     只读取到部分范围（范围被裁剪 / 截断 / 仅抽样）
NOT_SEEN    外审 primary 证据不可见 / 不存在 / 无法取回
UNCERTAIN   读取到了内容，但无法判断是否覆盖所需范围
```

### 7.4 两个 completeness 输出（分别产出）

```text
CONTEXT_COMPLETENESS_FOR_DECISION_AUDIT   上下文是否足以支撑本次裁决的审计
FULL_HISTORICAL_TRANSCRIPT_COMPLETENESS   完整历史 transcript 是否可得
```

二者回答两个**不同**的问题：前者关乎"这次裁决的上下文够不够审计"，后者关乎"完整历史是否在手"。
两者必须**分别产出**；**禁止**把二者合并为一个 completeness 标志位，也**禁止**以其中一个代替另一个
（合并 = 一条输出冒充两条）。

### 7.5 有界结论规则与失败语义

```text
CE-15-A  FORBIDDEN  外审 primary 不可见（visibility 为 NOT_SEEN）时仍声明完整 / 无限定结论
CE-15-B  REQUIRED   证据不足以支撑完整结论时，结论必须限定（bounded）或返回 MORE_EVIDENCE_REQUIRED
CE-15-C  REQUIRED   两个 completeness 输出必须分别产出，不得由一个标志位替代
CE-15-D  REQUIRED   启用本 recipe 时，缺 visibility 陈述的结论不可审计（NOT_AUDITABLE）
CE-15-E  FORBIDDEN  把两个 completeness 输出合并为一个 completeness 标志位
CE-28-E  OWNER      本 recipe 的唯一 canonical owner 是 references/review-and-repair-saturation.md
CE-28-F  POINTER    其它 surface（含证据接口）只引用 / 链接本 recipe，不重复定义
```

```text
NOT_SEEN + 完整结论        -> REJECT，或降级为 MORE_EVIDENCE_REQUIRED
缺 visibility 陈述（已启用本 recipe）  -> NOT_AUDITABLE（不得作为 PASS 依据）
两个 completeness 输出合并 -> REJECT
```

**默认（未启用即惰性）**：一张**未启用本 recipe** 的常规票**不**因缺少 visibility 陈述而被渲染为 NOT_AUDITABLE —— 未启用时本 recipe 对结论不施加任何约束，上列 `CE-15-D` 与对应失败行只在**已启用本 recipe**时触发。

### 7.6 与 §6 及证据接口的边界

- **纯追加**：本节的规则 ID 与 §6 的规则 ID 不相交；§6 的消费规则与 reviewer 权威分离语义
  仍只在 §6 声明，本节不复制、不弱化、不改写。
- **只引用不重定义**：`references/review-evidence.md` 只引用 / 链接本 recipe，不重复定义它；
  本 recipe 同样不重声明该接口的字段名、闭合集与机器形状。

## 8. PRE-EXTERNAL TERMINAL BARRIER（外部评审交接前的当前 HEAD 收敛门）

> 本节是该 gate 的 **canonical 声明点**。此前本仓多处引用该术语却无定义（悬空引用：`references/skills-and-model-routing.md` §3 曾指向 `AGENTS.md` §10，而 §10 是 bootstrap 主题，不含该定义）。本节补齐定义；其它 surface 只指针 / 链接，不重复定义（CE-28）。

**适用面**：reviewer route 被显式指定为**外部**评审（不同 runtime / 外部强模型 / 人工搬运）时。
内部子代理评审 route **不**适用本节——其交接发生在同一 runtime 内，成本与漂移风险不同。

**核心命题**：

```text
PUSH != READY_FOR_EXTERNAL_REVIEW
```

push 候选或创建 PR **都不是**终态。进入外部交接前，当前 **exact remote HEAD** 必须同时满足：

```text
REMOTE_HEAD_STABLE
  AND STATIC_GATES_COMPLETE
  AND DYNAMIC_GATES_COMPLETE
  AND CI_TERMINAL                        （CI 为终态；pending / unknown / 未分类不得充当终态）
  AND CONFIGURED_AUTOMATED_REVIEW_STATE_KNOWN
  AND CURRENT_HEAD_FINDINGS_RECONCILED
```

**规则**：

- 目的 = 外部评审是稀缺资源，**一次到位**；把尚未收敛的候选交出去会产生外部往返，并使"被评审对象"在往返中漂移。
- **任何新编辑使旧 SHA 的 static / dynamic / CI / 评审证据失效**（与 §5 的 exact-SHA 绑定同源），必须重新满足本 barrier，不得沿用旧证据交接。
- 满足 barrier 后按 §5 的 novelty-first packet 输出**最小 handoff**（只引用 exact SHA / 仓内路径 / Issue，不复制正文），此时终态为 `READY_FOR_EXTERNAL_REVIEW`。
- 本 barrier **只决定"何时可以交出去"**，不改变 quorum / exact-SHA / PASS 契约，也不指定"谁审"（后者是 §1 L2 与 `references/skills-and-model-routing.md` §1 的范围）。

```text
LEGAL    满足全部六个条件后交接，并给出 minimal handoff
ILLEGAL  仅 push / 开 PR 即宣称进入外部评审           -> REJECT（premature handoff）
ILLEGAL  CI 非终态（pending / unknown）时交接         -> REJECT（CI != TERMINAL）
ILLEGAL  交接后又编辑候选而未重新满足 barrier         -> REJECT（stale barrier）
ILLEGAL  以本 barrier 豁免 quorum / exact-SHA         -> REJECT（barrier 不是豁免）
```
