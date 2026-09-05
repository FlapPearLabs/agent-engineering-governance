# REF: Review & Repair Saturation — 评审分级、收敛仲裁与报告

> Canonical owner: AGENTS.md §6/§9。本文件是**D 层默认**字段表、判据与模板（仓政策可覆盖，记录 OVERRIDE）。
> F3 修复：LOW 评审语义统一为单一规则（见 §1 触发列），与 RULES R4 的条件式独立评审语义一致。

## 1. 评审分级（L0/L1/L2）

| 层 | 承担者 | 核验内容 | 触发（唯一规则） |
|---|---|---|---|
| L0 MACHINE | harness / 脚本 / agent 机械执行 | exact SHA、base SHA、diff 语义范围、测试执行与结果、回归、ancestry、静态检查、secret/路径扫描、图 base SHA 记录 | **每票必做** |
| L1 NORMAL | 低成本 fresh context 独立评审 | 合同满足、缝与所有权、scope、失败语义、缺失假设、缺失高价值反例（≥2 个非复制 worker 的新反例） | **生产代码（全部风险级）必须；非生产票按仓政策可选**。即：非生产/机械 LOW 票可 L0-only 闭合（仓政策允许时）；生产代码 LOW/MEDIUM/HIGH 一律 L1 |
| L2 STRONG/EXTERNAL | 强模型/外部独立评审（不同模型族优先） | 架构、安全、状态/并发、身份/provenance、评审分歧仲裁、governance/Spec 变更、里程碑、高爆炸半径 | 仅 AGENTS §3 ESCALATION 清单命中时 |

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
