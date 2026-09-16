# REF: Execution Stage — 执行阶段编组与 seam-first 分解

> Canonical owner: AGENTS.md §2/§4。本文件是**D 层默认**机制（仓政策可通过 C 层覆盖）。设计边界声明：Stage 编组是设计选择，其必要性由"frontier=就绪即全开"的工具语义（`/to-tickets` 原文）与 prompt 搬运痛点支撑；机制本身无历史先例约束。

## 1. Stage 定义

EXECUTION STAGE = 一组**被有意编组**的隔离 Ticket Lane + 一个 Stage barrier。

Frontier（所有阻塞已清的票）只是**合法候选集**；编组才是执行决策。编组输入（全部评估，非全选）：

| 输入 | 问题 |
|---|---|
| LEGAL DAG FRONTIER | 哪些票现在可以合法开工？ |
| ENGINEERING COHESION | 哪些票属于同一行为域/同一缝，合并评审更高效？ |
| WRITE OWNERSHIP | 票间是否触碰同一文件/模块/状态 owner？ |
| BLAST RADIUS | 合并到 master 时谁的失效会 invalidate 谁？ |
| RISK CLASS | LOW/MEDIUM/HIGH 混排是否拉高整组评审成本？ |
| MODEL COST / REVIEW COST | 本组最贵 gate 由谁触发？ |
| INTEGRATION INVALIDATION RISK | 后集成者的 base 会不会被先集成者打 drift？ |

输出：STAGE_MANIFEST（票清单、风险级、预计 gate、集成顺序）。通常 1–4 个 lane。

## 2. Owner 冲突处置（多就绪票共享同一 owner）

命中 WRITE OWNERSHIP 冲突时**三选一**，不得默认并行：
1. **合并为一票**（内聚性优先）；
2. **显式串行集成链**（并行施工可以，但 STAGE_MANIFEST 声明集成顺序，后集成者 merge 前 re-fetch + 必要时 re-form）；
3. **拆 owner**（真正的架构决策 → 走架构授权，不是执行层能决定的事）。

## 3. 无 DAG 退化路径

无分解 DAG（单票项目/未用分解工具/独立项目）：
- Stage = 按风险与内聚选出的单票或票集合；frontier/DAG 输入标记 `NOT_APPLICABLE`；
- barrier、串行集成、remote verify、novelty-first packet 语义全部保留；
- 不得为"凑齐 DAG"而发明票据。

## 4. Stage barrier 与自动推进

```
Stage 组建 → lanes 并行执行（各自完整 gate 链）
→ 全部 lane 到达终态（PASS / SATURATION / STOP）
→ STAGE_REVIEW_PACKET（novelty-first 汇总：新发现、合同影响、遗留 findings 及处置）
→ 外部评审仅当 ESCALATION 触发（AGENTS §3 清单）
→ 修复/批准 → 自动逐个串行集成（按仓政策 merge 方法 + remote verify）
→ 重算 frontier → 下一 Stage
```

- 单 lane STOP 不阻塞已独立完成的 lane 集成，除非写权/顺序冲突。

## 5. 反模式

- `START_ALL`：把 frontier 全量开 lane —— 禁止。
- `SUPER_STAGE`：整个 milestone 编成一个 Stage（barrier 失去意义）。
- `SILENT_REORDER`：不更新 STAGE_MANIFEST 就改集成顺序。

## 6. Seam-first 分解协议（/to-tickets 及等价工具的约束壳）

本节是分解门禁的唯一执行 recipe；合同内容仍由项目权威定义，单票合同块仍归 [ticket-lane.md §3](ticket-lane.md)。不新建 seam/schema/证据数据库。

### 6.1 入口、权威与冲突检查

1. 输入必须是 approved 架构/Spec 下的实现意图，不是“请设计架构”。按 [AUTHORITY_MAP_V2](../audit/AUTHORITY_MAP_V2.md) 发现项目本地权威并确认批准依据；只有 SHA、文件名含 FINAL 或工具建议都不构成批准。
2. 应用门禁前逐项对照：已批准阶段顺序、职责边界、验收语义、接口所有权、实现授权边界。若应用会改变其中任一项，记录 `SPEC_OR_AUTHORITY_CONFLICT`，停止推进受影响分解，按 R1 路由项目 owner / 既有 Spec 变更流程；不得以“全局不变量”自行覆盖。C 层显式等价流程按既有 OVERRIDE 协议记录，未解决的真实冲突不得 PASS。
3. `ONE_CANONICAL_SOURCE_PER_FACT`：术语、决策、缝、共享状态各自找到唯一权威声明点；其他文档只能引用。可使用批准 Spec、项目规则、架构文档、schema、canonical interfaces 或项目已有 CONTEXT/ADR。代码可证明现状，不能自动推翻批准的目标行为。权威不一致且无法按优先级解析 → `AUTHORITY_CONFLICT`。
4. 全局只规定证明义务，不存储下游项目具体术语、ADR、缝图或枚举；不要求项目创建 `CONTEXT.md`、`CONTEXT-MAP.md`、`docs/adr/`。既有已批准决策只引用，不重新决策。

### 6.2 PRE_TICKET_CONVERGENCE_GATE

执行者 = 分解者；问题 = 上游语义是否足以开始切片，**不是**尚不存在的票集是否兼容。

逐项读取并引用项目权威中的：canonical terminology、durable decisions、expected seams、shared state contracts、semantic owners，以及接口不变量、顺序、错误、身份和同步/异步约束。概念名如 `TERMINOLOGY_AUTHORITY_REF` / `DECISION_AUTHORITY_REF` / `SEAM_AUTHORITY_REF` / `STATE_CONTRACT_REF` 只是证明项，不是新项目 schema 或必需文件名。无共享状态或无跨边界行为可给出具体不适用理由；UNKNOWN 不得写成 N/A。

- 切片前输出所需缝及来源引用（可复用已有清单）：既有模块、producer/consumer、状态/身份/校验 owner、持久化和安全边界。不重定义单票合同字段。
- 所需语义均可解析、无已知缺口 → PRE PASS，允许生成草稿。缺关键合同 → `CONTRACT_GAP`；需要新的难以逆转、真实权衡、跨票架构/领域决策 → `ARCHITECTURE_OR_DOMAIN_GAP`，退回项目规划，不准藏入票据。
- 这里只定义反例、期望失败条件及票内执行责任。**不得要求拆票前运行 RED 或完成产品 E2E**；真实 RED 在 ticket authorization 后按 ticket-lane §4 执行，运行可达性关闭证据仍归既有集成合同。

#### 有效证据复用与恢复

`FAST_PATH = VALID_EVIDENCE_REUSE`，不是 same-session trust。复用必须能核对 `PROJECT_REPO`、`APPROVED_SPEC_SHA`（非 Git 项目使用批准权威的不可变版本身份）、`AUTHORITY_REFS` 及相关版本/digest、`SEMANTIC_INPUT_SCOPE`、原证明来源与适用范围。这些是现有项目证据里的绑定要求，不新增 receipt 格式。

逐项确认相关依赖未变且原证据覆盖本次 scope；依赖未知、陈旧、缺失 → 重建受影响范围。新 session、换模型、外部 Spec、handoff 或 compaction 只是检查证据的触发器，不能单独判失败。相反，同一会话也不能免检。

证据复用/失效继续由 [git-ci-integration.md §5](git-ci-integration.md#5-exact-sha-评审协议) 管理：只复用依赖未变的特定证明，不把原 exact-SHA PASS 改名为新 SHA 全量 PASS。相关 authority/schema/依赖/入口拓扑变化要重查受影响范围；无关变更不强制全量重建。若项目已采用更完整的 canonical evidence 接口，直接引用其依赖与失效记录，不建第二生命周期。

### 6.3 DRAFT_TICKETS

PRE PASS 后才生成草稿：每票 = 内聚行为切片，含 SEAM、OWNER、OUT_OF_SCOPE、可测验收和权威引用。保持 tracer-bullet 意图；按真实架构处理必须整体迁移的变更，不为票据形状创造模块。

- prefactor 仅限既有模块或 Spec 明确授权的模块；映射不上则报告缺口。
- 三项 lint 保留：阻塞边审计、每个规范要求的 disposition/合同溯源、票间约束可同时满足。禁止自行发明阈值、策略或算法。
- 标注 Stage 建议与理由，最终编组权仍在编排者。发现合法架构拆分需求，走授权而非因影响票界拒绝。
- 草稿保留在项目既有草稿面；若 tracker 必须先分配 ID，显式 `DRAFT / NOT_AUTHORIZED`，不得设置 ready-for-agent。工具的 publish/frontier 默认不授予执行权。

### 6.4 POST_TICKET_COMPOSITION_GATE

两种 PRE 路径都必须对**实际草稿全集及其版本**执行本 gate。DAG 只回答 WHEN，seam 合同回答 WHAT / WHO / HOW。没有数据交换的纯排序边可以给出理由，不强行发明 seam；存在数据交换却无 DAG 边也必须核查。

分解者逐 seam 对照权威与所有相关票：semantic owner、producer、consumer、input/output、shared terms、shared state、sync/async、ordering、error semantics、identity semantics、handshake acceptance。字段可直接引用已有合同；不得各票复制并独立重定义。必须证明 producer 保证满足 consumer 前置条件，并覆盖所需边界集合；仅检查列出的 seam 不能证明没有遗漏。

至少排除：`ORPHAN_INPUT`、`ORPHAN_OUTPUT`、`DUAL_SEMANTIC_OWNER`、`TERM_DRIFT`、`STATE_DRIFT`、`TIMING_DRIFT`、`ORDERING_DRIFT`、`ERROR_SEMANTICS_DRIFT`、`IDENTITY_DRIFT`。合法外部数据源、最终用户/持久化输出及副作用需有明确权威、责任方和接受条件，不能因消费者不在当前票集就误判孤儿；未解释的缺口必须阻断。

每条 required seam 的 handshake acceptance 至少指向：producer 保证、consumer 前提、正向可接受例、针对本 seam 的反例/期望失败条件、将验证它的票或角色。它是**计划期合同验收**，不是提前声称运行期测试已通过。

`STRUCTURAL_VALIDATION != SEMANTIC_COMPATIBILITY`：机器可查引用、ID、字段、已知枚举、重复 owner、孤儿引用和 DAG；只查得到的报结构结果，未实现的检查报 NOT_RUN。名字相等不证明含义相等。语义兼容必须由独立 reviewer 对项目来源和票据内容裁决；作者自报 PASS 矩阵不能替代。

- 已发现任何关键错配 → POST FAIL，留在草稿态；未知语义 → POST UNKNOWN，亦不放行。
- 分解者完成对照后可记录 `POST_CANDIDATE = READY_FOR_INDEPENDENT_REVIEW`，**不能自授最终 POST PASS**。
- 独立 ticket conformance reviewer 核查 exact 草稿版本、PRE 证据、全部 required seam 及反例，形成 POST 语义 verdict；其后完成其余 ticket conformance 审查。可在同一次独立评审中完成这两项义务，不要求两个重复 reviewer。
- 仅 POST PASS **且**独立 conformance PASS，才可称分解完成、发布为候选票；Stage / implementation 仍需既有授权。票据内容或相关权威变化，按影响范围重查，并让独立结论绑定新版本；不得沿用整集旧 PASS。

### 6.5 证据、失败路由与执行限制

证据写入项目**既有**分解/评审记录，Stage packet 只引用：项目和批准来源身份、适用范围、权威引用/版本、PRE 复用或重建依据、exact 草稿集合版本（Git SHA 或 tracker 内容快照/digest）、结构结果及限制、逐 seam 对照/acceptance、未决项、独立 reviewer 身份/结论/证据、下一合法动作。不建全局 ledger、不复制项目语义；证据不是新的规范权威。

| 原因（诊断，不是新状态机） | 既有 STOP / 下一步 |
|---|---|
| SPEC_OR_AUTHORITY_CONFLICT / AUTHORITY_CONFLICT / 任一语义 DRIFT | CONTRACT_CONFLICT；项目权威裁决/修正草稿，需改 Spec 时 SPEC_AMENDMENT_REQUIRED |
| CONTRACT_GAP / ARCHITECTURE_OR_DOMAIN_GAP / 无法解析的 owner | CONTRACT_CONFLICT（R6 原因 CONTRACT_GAP）；回项目规划，需新决策时 USER_DECISION_REQUIRED |
| 必要证据缺失且无法自主恢复 / 独立评审未完成 | EXTERNAL_EVIDENCE_REQUIRED；保留草稿，获取独立证据 |
| 缺少批准/执行授权 | AUTHORIZATION_FAILURE；不得开工 |

失败修复只作用于受影响草稿/证据；不擅自修改并行 lane 已有票集。`scripts/validate_governance.py` 仅校验本治理 recipe 的接线完整性，**不是项目 ticket gate 执行器**，exit 0 不授予任何项目 PRE/POST/独立评审 PASS。运行时强制拦截未部署时必须如实报告，不能把文档协议称为自动拦截器。

## 7. 与反例的接口

分解发现"两票共享同一状态 owner" → 回查缝：拆 owner（架构授权 → STOP）、合并一票，或走 §2.2 串行链。
