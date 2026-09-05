# TARGET_WORKFLOW_V1 — 目标多代理工程架构

> 本文件是 TO-BE 蓝图。它是候选治理文件（`AGENTS.md` / `RULES.md` / `references/`）的语义总纲；
> 候选文件是它的可部署形态。未经外部评审与用户批准，不激活。

## 1. 角色架构

```
PRODUCT OWNER / HUMAN
  拥有：产品方向、scope 授权、Approved Spec 裁决、架构未决决策、外部 gate 决策
        ↓ 授权（"开始施工"级）
PARENT ORCHESTRATOR  = CONTROL PLANE（thin）
  拥有：读权威、repo 状态核验、frontier 计算、Stage 编组、lane 创建、
        模型路由、证据归集、gate 执行、repair 预算控制、集成、tracker 更新、Stage 推进
  默认不做生产编码（隔离 worker 可用时）
        ↓ 派发
EXECUTION STAGE  = 一组经编排的隔离 TICKET LANES
        ↓
WORKER（每 lane 一个）      REVIEWER（独立 context）      INTEGRATOR
  一个票/一分支/一工作树      查合同/缝/所有权/失败语义      exact 核验 + 串行集成
```

- `PARENT_ORCHESTRATOR = CONTROL_PLANE`；`ISOLATED_WORKER_IMPLEMENTATION = ALLOWED_AND_PREFERRED`。
- Worker 实现不获得架构/Spec 权威。Reviewer 不拥有无限修复权。Integrator 在 quorum PASS 同一 exact SHA 前不动作。
- 角色不得因便利静默吸收他角色权威（SELF_REVIEW != INDEPENDENT_REVIEW）。

## 2. EXECUTION STAGE（执行阶段）

- DAG-ready ≠ 立即开工。Stage 编组输入：合法 DAG frontier + 工程内聚性 + 写权冲突 + 爆炸半径 + 风险级 + 模型/评审成本 + 集成失效风险。
- 禁止 `ALL_READY_TICKETS = START_ALL`。
- Stage 内允许多个隔离 lane 并行；Stage 结束设 barrier：Stage Review Packet（按 novelty-first 汇总）→ 需要时外部评审 → 修复/批准 → 自动集成 → 重算 frontier → 下一 Stage。
- 目标交互：`开始施工` → Stage 自主执行 → Stage Packet → （仅必要时）外部评审 → 自主集成与推进。
- 详见 `references/execution-stage.md`。

## 3. TICKET LANE（单票生命周期，风险分级裁剪）

```
AUTHORIZED TICKET → exact base SHA → 隔离 branch/worktree → 读权威
→ 自然缝识别 → CodeGraph grounding → Relevant Surface Manifest → Contract Extraction
→ counterexample 设计 → TDD RED → /implement → GREEN → 回归
→ fresh independent review →（有价值才）repair → 风险需要时 adversarial review
→ PR → real CI → 风险需要时 post-CI review → merge gate → 串行集成 → remote verify → tracker
```

- **不是每票都跑最大链**。风险四级 LOW/MEDIUM/HIGH/CRITICAL，门槛递增（矩阵见 `references/ticket-lane.md`）。LOW = 文档/fixture/机械胶水：最小 grounding + 聚焦测试 + 普通 CI，无三方评审。
- ONE TICKET = ONE BRANCH = ONE ISOLATED WORKTREE = ONE MUTABLE WORKSPACE = ONE ACTIVE WRITER。

## 4. SEAM-FIRST 分解

合法顺序：AUTHORITY/产品行为 → 既有架构 → producer/consumer → 状态/身份/校验归属 → 持久化/失败/安全边界 → 自然缝 → 内聚行为切片 → 票据 → DAG。
禁止顺序：DAG → 发明票据形状的模块 → 假缝 → 逼架构就范。

- 全局语义：`DAG_IS_EXECUTION_MODEL` / `DAG_IS_NOT_ARCHITECTURE_AUTHORITY`。
- `/to-tickets` 定位 = **实现分解 + 一致性 lint**（阻塞边、合同溯源、约束可满足性审计），不是架构生成器；其 "prefactor" 提示必须服从既有架构权威，不得发明模块。
- 每票应代表：内聚行为 + 自然缝 + 显式 owner + 可测验收合同 + 合理评审边界。

## 5. CODEGRAPH GROUNDING

- 用途 = 回答结构问题（谁调用/谁生产/谁校验/谁拥有状态/谁持久化/下游谁坏/信任边界在哪），不是索引仪式。
- `INDEPENDENT_CODEGRAPH_GROUNDING != INDEPENDENT_FULL_REINDEX`：独立性 = 独立查询与关系推理，不是各自重建库。
- 目标形态：canonical healthy graph @ current master → worker 独立查询 → 候选增量同步（delta grounding）→ reviewer 独立查询。全量重建仅由健康/schema/配置证据触发，永不是每票/每评审 gate。
- 详见 `references/codegraph-grounding.md`。

## 6. CONTRACT + COUNTEREXAMPLE TDD

- `CONTRACT → COUNTEREXAMPLES → RED → IMPLEMENT → GREEN → REFACTOR → REGRESSION`。
- `TEST_FILE_EXISTS != TDD_RED_PROVEN`；证据必须区分 TEST_FIRST 与 COUNTEREXAMPLE_SPECIFIC_RED（RED 由目标反例触发，非 harness 坏/模块缺失）。
- 反例瞄准高价值失效类：身份错配、陈旧复用、部分冒充完整、静默 fallback、所有权漂移、序列化危害、安全泄漏、现实畸形持久态、**合法生产输出被拒**。
- 详见 `references/ticket-lane.md` §counterexample。

## 7. RISK-SCALED 评审分级

- L0 MACHINE：SHA、diff 范围、测试执行、回归、ancestry、禁改文件、静态检查、secret/路径扫描、机械反例 —— 机器能做的机器做。
- L1 NORMAL INDEPENDENT REVIEWER：低成本低新鲜上下文；审合同/缝/scope/所有权/失败语义/缺失假设/缺失高价值反例。
- L2 STRONG/EXTERNAL：架构、安全、状态/并发、身份/provenance、评审分歧、Spec/governance、里程碑、高爆炸半径 → 强模型/外部独立评审（不同模型族优先）。
- 原则：机器核验机械事实；便宜评审审普通代码；贵评审只审高价值风险。
- 详见 `references/review-and-repair-saturation.md`。

## 8. REPAIR SATURATION（价值化收敛）

- `SEVERITY != REPAIR_AUTHORITY`；`NEW_CASE != NEW_INFORMATION`；`ZERO_FINDINGS != DEFINITION_OF_DONE`。
- REPAIR_VALUE gate：IMPACT × REACHABILITY × EVIDENCE_STRENGTH × CONTRACT_CONFIDENCE vs REPAIR_COMPLEXITY × REGRESSION_RISK。
- REACHABILITY 三分类：PRODUCIBLE_STATE / REALISTIC_RECOVERY_STATE / ARBITRARY_SYNTHETIC_STATE（合成态不自动授权加固）。
- `NORMAL_REVIEWER_DRIVEN_REPAIR_BUDGET = 2`；耗尽 → `AUTO_REPAIR_AUTHORITY = EXHAUSTED` → CONVERGENCE_ARBITER 裁决：REPAIR_MORE / SATURATION_REACHED / ARCHITECTURE_REOPEN / ROUTE_TO_OWNER / BACKLOG_LONG_TAIL。
- 终态 = `NO_KNOWN_HIGH_VALUE_BLOCKER` + 低边际修复价值 → SATURATION；高价值 blocker 永远阻塞。

## 9. EXACT-SHA + GIT

- 任何生产代码变更 → 旧 code review 对变更代码失效；repair = 新 commit → 新 SHA → 适用 gate 新鲜重审。
- 新鲜评审 ≠ 重读全仓：blast radius 未扩张时用 previous reviewed SHA → delta + CodeGraph 爆炸半径 + 权威。
- 禁 force-push/amend/rebase reviewed 历史；ff-only；master 串行；merge 前 fresh fetch + remote identity 核验。

## 10. CI GOVERNANCE

- `LOCAL_TESTS != REAL_PR_CI`。状态集：PASS / FAIL / NOT_TRIGGERED / CANCELLED / INFRASTRUCTURE_FAILURE / KNOWN_BASELINE_FAILURE / UNKNOWN（可扩，不可坍缩）。
- 禁止 NOT_TRIGGERED=PASS、KNOWN_BASELINE_FAILURE=PASS、UNKNOWN=PASS。
- Worker 对非 PASS 的分类 = PROPOSAL_ONLY；接受需 `REVIEWER_ACCEPTED_CLASSIFICATION = YES` + 独立证据（base 复现、签名比对、非候选引入）。
- 可选 review harness（NOW/NEXT 分级见 GAP_MATRIX G-09）：机器生成机械证据包，减少重复模型劳动。

## 11. AUTO-ADVANCE 与人工边界

授权已含的路径上：gate 满足 → 集成 → remote verify → tracker → 重算 frontier → 下一 Stage。不问"要继续吗"。
仅七类真实停机：USER_DECISION_REQUIRED / CONTRACT_CONFLICT / SPEC_AMENDMENT_REQUIRED / EXTERNAL_EVIDENCE_REQUIRED / AUTHORIZATION_FAILURE / UNRESOLVABLE_CONFLICT / MILESTONE_COMPLETE。

## 12. MODEL ROUTING

- RISK FIRST, MODEL SECOND。映射到实际可用档位（lite / default / reasoning / 外部强模型）而非不可核验的具体型号名单；高危终审用最强可用推理档（外部 Sol 级）。
- 评审独立性：优先不同 context，高风险优先不同模型族（经济允许时）。
- 详见 `references/skills-and-model-routing.md`。

## 13. REPORTING

- NOVELTY-FIRST：先 NEW_CODEGRAPH_FINDINGS / NEW_CONTRACT_FINDINGS / NEW_COUNTEREXAMPLES / NEW_DEFECT_CLASSES / ASSUMPTIONS_INVALIDATED / NEW_CROSS_MODULE_RISKS / SURPRISES，再 delta；合法值 NONE；禁止编造新颖性。
- `PR_CI_COMPRESSION_ALLOWED = PASS_ONLY`。

## 14. 场景校验

十个目标场景（低风险文档票 → SHA 失效 → 验证权威复用）对本架构的逐条校验见 `audit/SCENARIO_VALIDATION.md`。结论：候选治理在全部 10 场景产出预期行为，其中 S4/S6/S7 依赖本文件 §2/§8/§5 的非默认语义（Stage 编组、饱和仲裁、canonical graph）。
