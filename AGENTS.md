# AGENTS.md — 全局代理工程执行架构（CANDIDATE V1）

> **状态：CANDIDATE — 未激活。** 本文件是全局执行架构候选，等待外部治理评审与 product owner 批准。
> 冲突裁决：`RULES.md`（硬规则）> 本文件（执行架构）> `references/*`（机制细节）> skills/MCP（执行方法）> MEMORY（偏好/环境事实）> runtime/conversation memory。
> 项目级权威在其**更严格**处生效，但不得弱化本文件与 RULES。
> 本文件不复制 references 全文；每节末尾给出唯一详情指针。

## 0. 适用范围与两条铁律

- 适用于**所有** FlapPearLabs 软件工程项目的 agent 协作（WorkBuddy / Hermes / Codex / 其他 runtime）。
- `SKILL_IS_EXECUTION_METHOD` / `SKILL_IS_NOT_AUTHORITY`：技能教"怎么干"，从不授予"干什么与何时干"的权威。
- `DAG_IS_EXECUTION_MODEL` / `DAG_IS_NOT_ARCHITECTURE_AUTHORITY`：票据依赖图是执行排程，不是架构来源。

## 1. 角色模型

| 角色 | 拥有 | 不得 |
|---|---|---|
| PRODUCT OWNER / HUMAN | 产品方向、scope 授权、Spec 裁决、架构未决决策、外部 gate | 被自动化替代的部分逐条列出才可委托 |
| PARENT ORCHESTRATOR（CONTROL PLANE） | 读权威、repo 状态核验、frontier 计算、Stage 编组、lane 创建、模型路由、证据归集、gate 执行、修复预算、集成、tracker 更新、Stage 推进 | 默认不当生产编码工人；不静默吸收其他角色权威 |
| WORKER | 一个票/一分支/一隔离 worktree 内：读、测、TDD、实现、append-only repair、push feature branch | 自批、自合并、扩 scope、开下游票、改冻结 Spec/DAG、force-push、把 self-review 当独立评审 |
| REVIEWER | 独立 context 重建结论；查合同/缝/所有权/失败语义；产 findings 与新反例 | 无限修复权；修改被审分支后仍声称原 PASS |
| INTEGRATOR | exact 远端核验、ancestry、master drift 检查、merge gate、**串行** master 集成、remote verify | quorum 未对同一 exact HEAD PASS 前动作 |

隔离实现 worker 直接实现生产代码（`ISOLATED_WORKER_IMPLEMENTATION = ALLOWED_AND_PREFERRED`）；handoff 文档仅在跨工具传递、执行中断、外部 worker、审计要求时创建。

## 2. EXECUTION STAGE

- DAG-ready ≠ 立即开工。编排者按以下输入编组 Stage：合法 frontier、工程内聚、写权冲突、爆炸半径、风险级、模型与评审成本、集成失效风险。
- 禁止 `ALL_READY_TICKETS = START_ALL`。
- Stage 内多隔离 lane 并行；Stage 尾设 barrier：Stage Review Packet（novelty-first）→（仅触发条件时）外部评审 → 修复/批准 → 自动集成 → 重算 frontier → 下一 Stage。
- 授权路径上自动推进；仅 §7 STOP 状态停机。
- 详见 `references/execution-stage.md`。

## 3. TICKET LANE（风险分级生命周期）

生命周期（MEDIUM 基线链）：
`AUTHORIZED TICKET → exact base SHA → isolated branch/worktree → 读权威 → 自然缝识别 → CodeGraph grounding → Relevant Surface Manifest → Contract Extraction → counterexample 设计 → TDD RED → /implement → GREEN → 回归 → fresh independent review →（有价值才）repair →（风险需要）adversarial review → PR → real CI →（风险需要）post-CI review → merge gate → 串行集成 → remote verify → tracker`

| 风险 | 典型 | 最小门槛 |
|---|---|---|
| LOW | 文档、fixture、确定性胶水、机械配置 | 最小 grounding；聚焦检查；L0+L1 或机器核验；普通 CI |
| MEDIUM | 常规特性集成、已知接口、多模块 | 全基线链（上行）；L1 评审 |
| HIGH | 持久化、编排、状态、身份/provenance、选择器、安全边界 | 强反例 5–10；fresh+adversarial 评审；更强 CI 证据 |
| CRITICAL | 架构不确定、并发、canonical 权威、高爆炸半径运行时、里程碑终审 | 升级高权威模型 / L2 外部评审 |

合同抽取、反例 TDD、worktree 隔离契约详见 `references/ticket-lane.md`。

## 4. SEAM-FIRST 分解

合法顺序：权威/产品行为 → 既有架构 → producer/consumer → 状态/身份/校验归属 → 持久化/失败/安全边界 → 自然缝 → 内聚行为切片 → 票据 → DAG。
禁止顺序：DAG → 发明票据形状模块 → 假缝 → 逼架构就范。

- `/to-tickets`（或等价分解）定位 = **实现分解 + 一致性 lint**：阻塞边审计、合同溯源审计、约束可满足性审计；不是架构生成器。
- 分解中的 prefactor 提议服从既有架构权威；新模块名必须映射到既有架构概念或 Spec 名词，映射不上 = 假缝，回炉。
- 每票 = 内聚行为 + 自然缝 + 显式 owner + 可测验收合同 + 合理评审边界。

## 5. CODEGRAPH GROUNDING

- 用途 = 结构问题（谁调用/生产/校验/拥有状态/持久化；下游谁坏；信任边界），不是索引仪式。
- `INDEPENDENT_CODEGRAPH_GROUNDING != INDEPENDENT_FULL_REINDEX`：独立性 = 独立查询与关系推理。
- 目标形态：canonical healthy graph @ current master → worker 独立查询 → 候选 delta 同步 → reviewer 独立查询；全量重建仅由健康/schema/配置证据触发，永不作为每票/每评审 gate。
- 详见 `references/codegraph-grounding.md`。

## 6. REVIEW / REPAIR / CI

- 评审分级：L0 机器核验机械事实（SHA、diff 范围、测试、回归、ancestry、禁改文件、secret/路径扫描）；L1 普通独立评审（低成本低新鲜 context）；L2 强/外部评审（架构、安全、状态/并发、身份、评审分歧、governance、里程碑、高爆炸半径）。
- 评审顺序：权威 → 票 → repo 图 → 合同 → 反例 → 实际 diff → 测试 → CI；不从 worker 的实现解释出发。
- 修复收敛：`SEVERITY != REPAIR_AUTHORITY`；REPAIR_VALUE gate；`NORMAL_REVIEWER_DRIVEN_REPAIR_BUDGET = 2`；耗尽 → CONVERGENCE_ARBITER 五选一；终态 = `NO_KNOWN_HIGH_VALUE_BLOCKER` + 低边际修复价值 → SATURATION；高价值 blocker 永远阻塞。
- CI：`LOCAL_TESTS != REAL_PR_CI`；状态不可坍缩（NOT_TRIGGERED/UNKNOWN/KNOWN_BASELINE_FAILURE 永不 = PASS）；worker 对非 PASS 分类仅 PROPOSAL_ONLY。
- 详见 `references/review-and-repair-saturation.md` 与 `references/git-ci-integration.md`。

## 7. AUTO-ADVANCE 与 STOP

授权已覆盖的路径（gate 满足 → 集成 → remote verify → tracker → 重算 frontier → 下一 Stage）**不问"是否继续"**。

仅以下状态停机：
`USER_DECISION_REQUIRED` / `CONTRACT_CONFLICT` / `SPEC_AMENDMENT_REQUIRED` / `EXTERNAL_EVIDENCE_REQUIRED` / `AUTHORIZATION_FAILURE` / `UNRESOLVABLE_CONFLICT` / `MILESTONE_COMPLETE`。
milestone 完成后不自动进入已明确排除的 NEXT_STAGE。

## 8. 治理变更

修改本文件、RULES.md 或任何 canonical reference = 高风险文档 gate：双独立评审（CONTRACT_REVIEWER + CONSISTENCY_REVIEWER）对同一 exact HEAD PASS 后方可合并；禁止实现票顺手改治理。

## 9. 报告

NOVELTY-FIRST：先 NEW_CODEGRAPH_FINDINGS / NEW_CONTRACT_FINDINGS / NEW_COUNTEREXAMPLES / NEW_DEFECT_CLASSES / ASSUMPTIONS_INVALIDATED / NEW_CROSS_MODULE_RISKS / SURPRISES，再实现/测试/CI delta；合法值 NONE；禁止编造新颖性。`PR_CI_COMPRESSION_ALLOWED = PASS_ONLY`。模板见 `references/review-and-repair-saturation.md` §Reporting。

## 10. 平台映射备注

- 隔离 lane/worker/评审由平台代理机制实现（WorkBuddy Agent 子代理、Hermes sub-agent 等）；本架构是平台无关语义。
- 外部强评审当前为人工搬运（web GPT/Sol 级）；PRE-EXTERNAL TERMINAL BARRIER（远端 HEAD 稳定 + 静态/动态 gate 完成 + CI 终态 + 自动化评审状态已知 + findings 对账）满足后才生成最小 handoff 并停机。
