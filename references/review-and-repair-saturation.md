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

## 3. Budget 与 Convergence Arbiter

- `NORMAL_REVIEWER_DRIVEN_REPAIR_BUDGET = 2` 是**默认值**（D 层）：owner/仓政策可按风险与证据质量调高/调低并记录 OVERRIDE；**不可覆盖**的部分 = "已知高价值 blocker 永不因预算耗尽而被豁免"。
- 流程：初始候选 → fresh review → 修复轮 1（仅高价值 blocker）→ fresh review → 修复轮 2（仅高价值 blocker）→ `AUTO_REPAIR_AUTHORITY = EXHAUSTED`。
- 耗尽 ≠ PASS：产生 CONVERGENCE_ARBITER（fresh、高权威、合同/架构向）裁决，五选一：`REPAIR_MORE / SATURATION_REACHED / ARCHITECTURE_REOPEN / ROUTE_TO_OTHER_OWNER / BACKLOG_LONG_TAIL`。
- `REPAIR_SATURATION_REACHED = YES` 判据：无已知高价值 blocker + 近轮缺陷类新颖性低 + 剩余提议边际价值低 + 剩余 findings 多为重复变体/防御加固/合成态/低影响清理。
- Saturation ≠ 无 bug：只表示本票高价值修复区已耗尽。
- 评审探索预算：fresh/third-party 各 2–4 个高价值独立对抗探针；`NEW_COUNTEREXAMPLES = NONE` 合法；禁止机械枚举组合凑数。

## 4. PASS 语义与 findings 处置

- 合法成功态：`PASS / PASS_WITH_NONBLOCKING_FINDINGS / SATURATION_REACHED_WITH_BACKLOG`。`ZERO_FINDINGS` 不是完成定义。
- 终局问题："这个 exact 候选是否对现实可达状态正确实现其拥有的合同、并在真实信任边界安全失败、无已知高价值 blocker？"
- 每条未修复 finding 必带：FINDING / SEVERITY_OPINION(P0–P3) / DEFECT_CLASS / REACHABILITY / REPAIR_VALUE / DISPOSITION(REPAIRED|BACKLOG|ROUTE_TO_OWNER|INFORMATIONAL|OUT_OF_SCOPE) / WHY_NOT_REPAIRED / OWNER。
- WHO_OWNS_THE_FIX：根因属他模块/他票权威 → ROUTE_TO_OWNER，不造第二弱策略凑零 findings。

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
