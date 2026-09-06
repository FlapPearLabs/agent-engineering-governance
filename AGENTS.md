# AGENTS.md — 全局代理工程执行架构

> **AGENT_ENGINEERING_GOVERNANCE_V1.1.1 — CANONICAL。** 本文件是本仓当前的 **D 层全局默认治理基线**，随治理仓 main 版本化演进；不再是候选状态。
> 权威分层见 `audit/AUTHORITY_MAP_V2.md`（A 平台/系统 > B 普适不变量=`RULES.md` > **C 仓库本地产品权威 > D 全局默认工作流=本文件与 references/** > E 方法/工具 > F 记忆/偏好）。
> 本文件与 references 是 **D 层默认**：仓库本地权威可通过显式 OVERRIDE 覆盖它们；加严永远合法。未覆盖处按本架构执行。
> 本文件不复制 references 全文；每节给出唯一详情指针。

## 0. 适用范围与铁律

- 适用于 FlapPearLabs 软件工程项目的 agent 协作（WorkBuddy / Hermes / Codex / 其他 runtime），作为**默认**；与 A/B/C 层冲突时按 AUTHORITY_MAP_V2 冲突算法处理。
- `SKILL_IS_EXECUTION_METHOD` / `SKILL_IS_NOT_AUTHORITY`；`DAG_IS_EXECUTION_MODEL` / `DAG_IS_NOT_ARCHITECTURE_AUTHORITY`。

# ENGINEERING DOCTRINE

> 工程哲学十条。它们是**原则**，不是新增 gate；机制语义在后续章节与 references，此处不重复。

1. **AUTHORITY BEFORE ACTION** —— 先确认权威链（A>B>C>D>E>F）与当前票授权，再动手；授权不明即停。
2. **UNDERSTAND BEFORE EDIT** —— 编辑前先建立仓库关系模型（surface manifest / CodeGraph）；不知谁生产、谁消费、谁拥有状态，不写代码。
3. **SEAM BEFORE TICKET** —— 自然缝先于票据；DAG 是执行排序，不是架构权威。
4. **CONTRACT BEFORE CODE** —— 合同字段块（输入/输出/不变量/失败语义）先于实现；缺语义 → STOP，不猜。
5. **COUNTEREXAMPLE BEFORE IMPLEMENTATION** —— 先设计"看起来合理仍违反合同"的反例，再写实现；RED 必须由反例触发。
6. **EVIDENCE BEFORE CONFIDENCE** —— 一切"完成/PASS"声明由可复现证据支撑；UNKNOWN != PASS。
7. **SELF_REVIEW != INDEPENDENT_REVIEW WHEN THE GATE EXISTS** —— gate 存在时自审不替代独立评审。
8. **RISK-SCALED RIGOR** —— 严格度随风险缩放：LOW 不跑全链，HIGH 才升级强评审。
9. **MINIMUM NECESSARY COMPLEXITY** —— 每个机制必须回答"防哪次真实失效"；无强论证不立 gate。
10. **AUTO-ADVANCE UNTIL REAL AUTHORITY UNCERTAINTY** —— 授权已覆盖的路径自主推进；只在真实权威不确定（§7 STOP 枚举）时停机问人。

# ENGINEERING EVIDENCE ROUTING

```text
MECHANICAL QUESTION（syntax/type/格式/结构查询/依赖图）?
→ STATIC TOOL / LSP / AST / COMPILER / LINTER / CODEGRAPH / TEST

BEHAVIORAL CONTRACT（行为/边界/fail-closed）?
→ TEST

CROSS-MODULE STRUCTURE（谁调用/谁拥有/爆炸半径）?
→ CODEGRAPH（模式 A/B/C）

SEMANTIC / CONTRACT / ARCHITECTURE QUESTION?
→ MODEL REASONING（合同、缝、所有权、失败语义、反例设计）

HIGH-VALUE UNCERTAINTY（架构/安全/分歧/里程碑）?
→ STRONG / EXTERNAL REVIEW（ESCALATION 清单）
```

- `DO_NOT_SPEND_REASONING_ON_MACHINE_PROVABLE_FACTS`：机器能证明的不进模型评审（L0 先清场）。
- `DO_NOT_REPLACE_SEMANTIC_REASONING_WITH_STATIC_TOOL_OUTPUT`：静态输出不裁决语义/合同/所有权。
- 语言栈选择：`USE_REPOSITORY_NATIVE_STATIC_TOOLING_FIRST`（详情 `references/static-analysis-and-code-intelligence.md`）。

## 1. 角色模型

| 角色 | 拥有 | 不得 |
|---|---|---|
| PRODUCT OWNER / HUMAN | 产品方向、scope 授权、Spec 裁决、架构未决决策、外部 gate | — |
| PARENT ORCHESTRATOR（CONTROL PLANE） | 读权威、repo 状态核验、frontier 计算、Stage 编组、lane 创建、模型路由、证据归集、gate 执行、修复预算、集成、tracker 更新、Stage 推进 | 默认不当生产编码工人；不静默吸收其他角色权威 |
| WORKER | 一个票/一分支/一隔离 worktree 内：读、测、TDD、实现、append-only repair、push feature branch | 自批、自合并、扩 scope、开下游票、改冻结 Spec/DAG、把 self-review 当独立评审 |
| REVIEWER | 独立 context 重建结论；查合同/缝/所有权/失败语义；产 findings 与新反例 | 无限修复权；修改被审分支后仍声称原 PASS |
| INTEGRATOR | exact 远端核验、ancestry、master drift 检查、merge gate、**串行** master 集成、remote verify | quorum 未对同一 exact HEAD PASS 前动作 |

隔离实现 worker 直接实现生产代码（默认允许且优先）；handoff 文档仅在跨工具传递、执行中断、外部 worker、审计要求时创建。

## 2. EXECUTION STAGE（默认机制）

- DAG-ready ≠ 立即开工。编组输入：合法 frontier、工程内聚、写权冲突、爆炸半径、风险级、模型/评审成本、集成失效风险。
- 禁止 `ALL_READY_TICKETS = START_ALL`；Stage 内多隔离 lane 并行；Stage 尾 barrier：Stage Review Packet（novelty-first）→（仅触发条件时）外部评审 → 修复/批准 → 自动集成 → 重算 frontier。
- **owner 冲突处置**：多就绪票共享同一状态/模块 owner 时 → 合并为一票 / 显式串行集成链 / 拆 owner（需架构授权），不得默认并行。
- **无 DAG 退化**：无分解 DAG 的项目，Stage = 按风险与内聚选出的单票或票集合；其余 barrier/集成语义不变。
- 授权路径上自动推进；仅 §7 STOP 状态停机。详见 `references/execution-stage.md`。

## 3. TICKET LANE（风险分级生命周期）

生命周期（MEDIUM 基线）：
`AUTHORIZED TICKET → exact base SHA → isolated branch/worktree → 读权威 → 自然缝识别 → CodeGraph grounding → Relevant Surface Manifest → Contract Extraction → counterexample 设计 → TDD RED → /implement → GREEN → 回归 → fresh independent review（L1）→（有价值才）repair → PR → real CI（或仓政策等价证据形态）→（触发时）post-CI/adversarial → merge gate → 串行集成 → remote verify → tracker`

| 风险 | 典型 | 独立评审 gate（R4 语义） | grounding/合同 | 额外 |
|---|---|---|---|---|
| LOW | 文档、fixture、确定性胶水、机械配置；**微型生产修复** | 非生产/机械票：**可 L0-only 闭合（仓政策允许时）**；生产代码：**必须 L1** | 最小（surface 摘要即可） | 聚焦检查 |
| MEDIUM | 常规特性集成、已知接口、多模块 | **必须 L1** | 全 baseline | real CI |
| HIGH | 持久化、编排、状态、身份/provenance、选择器、安全边界 | **必须 L1 + adversarial** | 强反例 5–10 | 更强 CI 证据 |

**ESCALATION 触发清单**（任一命中 → 升级外部/最强评审，L2）：
架构不确定性；并发/canonical 权威语义；安全/凭据边界；评审分歧未决；Approved Spec / governance 变更；里程碑终审；高爆炸半径运行时语义。

- LOW 票不得触发 ESCALATION 清单，除非命中清单本身（如安全相关文档变更）。
- 合同抽取、反例 TDD、worktree 契约详见 `references/ticket-lane.md`。

## 4. SEAM-FIRST 分解

合法顺序：权威/产品行为 → 既有架构 → producer/consumer → 状态/身份/校验归属 → 持久化/失败/安全边界 → 自然缝 → 内聚行为切片 → 票据 → DAG。
禁止顺序：DAG → 发明票据形状模块 → 假缝 → 逼架构就范。

- `/to-tickets`（或等价分解）定位 = **实现分解 + 一致性 lint**，不是架构生成器。
- **对立错误同样禁止**：合法的架构性拆分/合并不得因"影响票据边界"被拒绝——依赖边若暴露真实架构合同，升格为架构决策走授权，而非硬塞进执行排程。
- prefactor 提议服从既有架构权威；新模块名必须映射到既有架构概念或 Spec 名词，映射不上 = 假缝，回炉。
- 每票 = 内聚行为 + 自然缝 + 显式 owner + 可测验收合同 + 合理评审边界。

## 5. CODEGRAPH GROUNDING（可执行摘要；详情与探针证据见 `references/codegraph-grounding.md`）

- 已核实 CLI 能力：`init / index / sync / status / query / explore / node / callers / callees / impact / affected / daemon`。图库**每目录**一个（`<dir>/.codegraph/`）。
- **MODE A — BASE + DIFF（默认）**：结构问题查 canonical 主仓图（base/master 拓扑：callers/callees/impact）；候选增量用 `git diff BASE..candidate` + 变更文件直读。报告 `CANDIDATE_GRAPH_COVERAGE = BASE_ONLY + DELTA_BY_DIFF`，**不声称 candidate-exact 图覆盖**。
- **MODE B — LANE CANDIDATE-EXACT（仅 HIGH 风险/明确需要候选态图时）**：v1.0.1 已机械证实 fresh lane `codegraph init <lane>` 即完成初始索引，随后 `codegraph sync <lane>` 为增量更新。lane 初始化**至多一次**；reviewer/repair 轮复用同一 lane 图。**绝不** per-reviewer / per-repair-round / 作为通用票 gate 执行全量 init/index。
- **MODE C — UNAVAILABLE**：CodeGraph 缺失/损坏 → 手工 Relevant Surface Manifest + 定向源码阅读；报告 `CODEGRAPH = UNAVAILABLE`；不伪造图证据。HIGH 票 = MODE C + ENHANCED_MANUAL_GROUNDING + ESCALATION（更强手工证据 + 独立评审加强）；HARD STOP 仅当：仓本地权威明确要求 CodeGraph / 该问题无结构证据无法负责任接地 / reviewer-owner 判定证据不足（工具是方法不是权威，不自动成为普适硬 gate）。
- 任何票据包记录所用模式与 `CANDIDATE_GRAPH_COVERAGE` 值。

## 6. REVIEW / REPAIR / CI（D 层默认）

- 分级：L0 机器核验（SHA、diff 语义范围、测试、回归、ancestry、secret/路径扫描）；L1 独立评审（fresh context、独立 grounding、≥2 个非复制新反例）；L2 外部/最强评审（按 §3 ESCALATION 清单触发）。
- 评审顺序：权威 → 票 → repo 图 → 合同 → 反例 → diff → 测试 → CI；主问题："这个 exact SHA 是否在真实仓库中实现了合同？"
- 修复收敛：`SEVERITY != REPAIR_AUTHORITY`；REPAIR_VALUE gate；`NORMAL_REVIEWER_DRIVEN_REPAIR_BUDGET = 2`（**默认值**，owner/仓政策可覆盖）；耗尽 → CONVERGENCE_ARBITER 五选一；`NO_KNOWN_HIGH_VALUE_BLOCKER` + 低边际价值 → SATURATION；**高价值 blocker 永不豁免**。
- CI：`LOCAL_TESTS != REAL_PR_CI`；状态不可坍缩（NOT_TRIGGERED/UNKNOWN/KNOWN_BASELINE_FAILURE 永不 = PASS）；real CI 为默认，**仓政策可定义等价证据形态**（显式 OVERRIDE），诚实性底线（R3）不可豁免。
- 详见 `references/review-and-repair-saturation.md` 与 `references/git-ci-integration.md`。

## 7. AUTO-ADVANCE 与 STOP

授权已覆盖的路径（gate 满足 → 集成 → remote verify → tracker → 重算 frontier → 下一 Stage）**不问"是否继续"**。
仅以下状态停机：`USER_DECISION_REQUIRED` / `CONTRACT_CONFLICT` / `SPEC_AMENDMENT_REQUIRED` / `EXTERNAL_EVIDENCE_REQUIRED` / `AUTHORIZATION_FAILURE` / `UNRESOLVABLE_CONFLICT` / `MILESTONE_COMPLETE`。milestone 后不自动进入已明确排除的 NEXT_STAGE。

## 7.1 STATE_RESTORE / STATE_FLUSH（跨 Agent 状态连续性）

- `PROJECT_STATE_MUST_OUTLIVE_THE_AGENT`；`CONVERSATION_MEMORY_IS_CACHE, NOT_PROJECT_STORAGE`。
- **STATE_RESTORE**：进入既有项目禁止以"请人讲历史"开局——按固定序列从 remote + 仓文档 + Issues/PRs 重构状态，输出 recovery receipt（PROJECT/REMOTE_DEFAULT_SHA/TARGET/SPEC/ADR/SPIKES/ACTIVE_TICKETS/BLOCKERS/DECISIONS_REQUIRED/CURRENT_LEGAL_FRONTIER/READY_TO_CONTINUE），授权已明确则自动继续。
- **STATE_FLUSH**：结束有意义会话 / 切换 runtime / 交接 / STOP / milestone / 完票 / 集成 / context 耗尽前，自问"下一个 fresh Agent 需要什么而它只存在于我的 context？"并把答案持久化到正确 canonical 位置；输出短 receipt（STATE_FLUSH = PASS/PARTIAL + UNPERSISTED_IMPORTANT_CONTEXT）。
- 状态分类 P0–P4、GitHub 控制平面字段、转换点清单、离线 `REMOTE_STATE_SYNC = DEFERRED` 语义、反官僚 PERSISTENCE_VALUE 判据：唯一详情见 `references/project-state-persistence.md`。运行时中立：WorkBuddy / ZCode / OpenCode / Codex / Hermes / 未来 Agent 同规。
- **PROJECT_CONTINUITY_CONTRACT_V1**（机械层）：每个 governed repo 拥有唯一固定状态索引 `.agent/project-state.json`（pointers + recovery snapshot，不是知识倾倒）；fresh Agent 检测到缺失即注入 `PROJECT_CONTINUITY_INITIALIZATION_REQUIRED` 并自动执行 lazy adoption / 新仓 bootstrap（不问用户）；只在 meaningful transitions 写；CodeGraph 生命周期 = `CODEGRAPH_INIT_ONCE_SYNC_CONTINUOUSLY`（runtime-local dirty 标记 + worktree 隔离，`~/.zcode/runtime-state/` 类本机状态绝不 commit）；MEDIUM/HIGH 生产首写前需 GROUNDING_RECEIPT（缺失 → `CODEGRAPH_GROUNDING_REQUIRED`，CodeGraph 不可用走 MANUAL_GROUNDING_RECEIPT）。合同全文/schema/template/validator/ZCode hook 参考实现/合成测试矩阵：`references/project-continuity-contract.md`（唯一详情）+ `adapters/zcode/`。Hook 只保证 Agent 不能忘记写，绝不代写语义决策。

## 8. 治理变更（默认协议）

修改本文件、RULES.md 或 canonical reference：默认双独立评审（合同向 + 一致性向）对同一 exact HEAD PASS；仓库/owner 可定义更严协议。禁止实现票顺手改治理。

## 9. 报告（novelty-first）

先 NEW_CODEGRAPH_FINDINGS / NEW_CONTRACT_FINDINGS / NEW_COUNTEREXAMPLES / NEW_DEFECT_CLASSES / ASSUMPTIONS_INVALIDATED / NEW_CROSS_MODULE_RISKS / SURPRISES，再 delta；`NONE` 合法；禁止编造。`PR_CI_COMPRESSION_ALLOWED = PASS_ONLY`。模板见 `references/review-and-repair-saturation.md` §5。

## 10. BOOTSTRAP（如何被新会话看到）

- 唯一已证实的自动全局注入通道 = `~/.workbuddy/MEMORY.md` 头部（**实测截断点 byte 4028**）。
- 引导机制 = `deployment/BOOTSTRAP_CONTRACT.md`：MEMORY 指针（候选文本 `deployment/MEMORY_POINTER_CANDIDATE.md`，≤3,500 字符）+ 会话开工 BOOTSTRAP 清单（读治理 canonical + 发现并读取仓内 AGENTS/RULES + 应用 AUTHORITY_MAP_V2 冲突算法）+ `scripts/validate_governance.py` 自检。
- 显式声明：WorkBuddy **不自动加载**项目 AGENTS.md/RULES.md（无证据支持自动加载；本合同以清单步骤补足）。
