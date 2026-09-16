# SPEC — P1 AGENT ENGINEERING GOVERNANCE DELTA

```text
SPEC_ID              = P1_AGENT_ENGINEERING_GOVERNANCE_DELTA
SPEC_VERSION         = 1 (draft)
STATUS               = DRAFT_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED = NO
REVIEW_GATE          = CHATGPT_INDEPENDENT_EXACT_SHA_SPEC_REVIEW
AUTHORITY_OWNER      = PRODUCT OWNER (FlapPearLabs) — Spec 批准与 IMPLEMENTATION_AUTHORIZED 唯一裁决者
SPEC_AUTHOR_ROLE     = SPEC_AUTHOR（非架构重设计者、非实现 worker）
TARGET_REPO          = FlapPearLabs/agent-engineering-governance
ZHIHU_REPO           = FlapPearLabs/zhihu-grabber-toolkit
ZHIHU_ROLE           = EVIDENCE_SOURCE_REPO（只读，本 Spec 不修改其任何文件或状态）
BASE_SHA             = 0ba2c7351d45dba1459a391b0d43e418ecf55280
BASELINE_DRIFT       = NONE（远端 main == 本地 HEAD == BASE_SHA；open PRs = 0）
```

## 0. 阅读契约与证据纪律

本 Spec 把一轮已完成的架构审计转成**可独立审查、可拆票**的实现规格。它**不是**架构重设计：第四至九节的全部机制边界来自本轮架构决策输入，Spec Author 未重新发明边界、未扩大机制范围、未改变 owner。

读者必须区分三类内容，全文以固定标记表达：

| 标记 | 含义 |
|---|---|
| `EXISTING` | 当前 canonical 已存在并有仓内证据；本 Spec 不改其语义，只做 LINK_ONLY 或补执行 recipe |
| `EXTEND` | 扩展既有 canonical 条款（新增字段/条件/验收），不新建第二权威体系 |
| `NEW` | 当前仓内不存在，需要新文件或新机制 |
| `DEPLOYMENT_ONLY` | 属仓库部署政策或 live 宿主动作，**不在本 Spec 实现范围内**；本 Spec 只定义未来验收与所需权限 |

**证据等级**（沿用输入证据的 A–E 定义）：A = 原始对话/执行记录；B = exact GitHub code/test/Issue/PR；C = 固定 SHA 外审结果；D = 检索片段；E = 后续摘要。本轮 Spec 写作**没有重跑任何历史产品测试**；输入报告中的 PASS 一律不写成本轮执行结果。凡主张证据不足处显式标 `NOT_VERIFIED`。

**不使用固定测试总数作为通过标准。** 验收以行为覆盖表达，允许合并测试；不要求凑测试数量。

---

## 1. WHY

### 1.1 触发事故（B 级证据，知乎仓编号 T16 产品事故 D1–D6 / T15）

| ID | 事故 | Seam 类型 | 证据 |
|---|---|---|---|
| D6 | 生产 `synthesize()` 返回 `chatJson(...)` 的 Promise；旧测试同步消费并把 Promise 当普通模型结果校验 → `T14_RUNTIME_OUTPUT_INVALID` | sync/async adapter | PR #87，merged `9444a33b3ca24a53f8da4b9e2cb03a241925f47f` |
| T15 | 新 composition owner 已合并关闭，但**没有生产调用者**；canonical runner 仍走 v0.3 | runtime reachability | PR #78，merged head `4a6767ff8b40c7bf2dbee2f220fc5194f553ede5` |
| D5 | preflight 缺 `pathToFileURL` 且吞掉入口异常 → CLI 可能从未真正执行检查（exit 0 制造虚假许可） | executable entrypoint | PR #86，merged `0d305b03c64f8b4f057415a29043aa41af082576` |
| D1/D4 | Planner 提供语义 `groupKey` / 自由 `constraints`，下游当作 canonical ID / 可执行硬过滤 | semantic / authority | PR #82 / #85 |
| D2 | 真实 provider 同 channel 重复，与冻结 RRF 唯一性假设不一致 | provider-normalization-fusion | PR #83 |
| D3 | 异步 handler 中强制 exit 与 Windows libuv teardown 冲突；stdout 完整 ≠ 正常完成 | runtime lifecycle | PR #81，merged `ca61d57f676bb81171d7869a0eb39fe84baae161` |

共同点：**边界双方对数据、权威、时序或调用关系的假设不一致**；且全部**在单元测试通过的前提下逃逸**。

### 1.2 为什么现有 canonical 未能阻断

不是"规则缺失"，而是 `RULE_EXISTS_BUT_NOT_EXECUTABLE`：

- Seam 原则与合同块已 canonical（`AGENTS.md` §4 doctrine 3/4、`references/ticket-lane.md` §3）——但缺**生产形状**（async/await、lifecycle、生产 caller）的可执行 recipe。
- 集成关闭已要求 exact-SHA / ancestry（`AGENTS.md` §6）——但缺**真实入口 → 变化 seam → 可观察效果**的关闭证据。
- L0/L1/L2 分级已 canonical（`references/review-and-repair-saturation.md` §1）——但历史 `audit/GAP_MATRIX.md` G-09 明确把 review harness 列为 NEXT，缺**机器证据包的最小接口**。
- 增量重审已 canonical（`references/git-ci-integration.md` §5）——但缺**跨候选复用的显式依赖与失效清单**。

一句话：**已覆盖的原则需要一个能真正阻断旧事故的执行层**，而不是又一套同义 doctrine。

### 1.3 安全 / 成本约束

- 治理自重是平台级风险（`RULES.md` R8）：每个新机制必须回答"防哪次真实失效"，否则不入 canonical。
- 昂贵 reviewer 不应重复机械检查（历史 C1 §13 REVIEW MODEL，A 级）；机械事实应由机器生成、绑定候选身份、按风险交给独立判断。
- 不建第二套证据账本、不建通用 CI runner、不建通用 orchestration framework。

---

## 2. CURRENT_GAP

| GAP_ID | 缺口 | 失效类型 | 当前证据 | 本轮处置 |
|---|---|---|---|---|
| GAP-01 | 无生产形状 Seam recipe（async/await、pending、reject、malformed、lifecycle、production caller 未进合同与反例） | RULE_EXISTS_BUT_NOT_EXECUTABLE | ticket-lane §3 有合同块但无生产形状字段 | `EXTEND` |
| GAP-02 | Integration 关闭缺"真实入口 → 效果"证据；模块测试绿可关闭集成票 | RULE_EXISTS_BUT_NOT_EXECUTABLE | 治理 Issue #9 OPEN；`IMPLEMENTATION_AUTHORIZATION=NONE` | `EXTEND` |
| GAP-03 | 门禁脚本自身无入口自测；helper 测试冒充 CLI 证据；exit 0 空跑可过 | TOOLING_GAP | D5 / PR #86（B） | `EXTEND` |
| GAP-04 | 无最小 review evidence producer/schema/validator/consumer；机械事实与 reviewer 结论无固定分字段接口 | TOOLING_GAP | `audit/GAP_MATRIX.md` G-09 harness=NEXT；仓内 `scripts/` 只有 governance/public-release/state 校验器 | `NEW` |
| GAP-05 | 跨候选证据复用与失效条件无统一清单；易全量重做或无条件复用 | TOOLING_GAP / RULE_TOO_VAGUE | git-ci-integration §5 只覆盖 delta 重审 | `EXTEND` |
| GAP-06 | Bootstrap 字节预算单位不一致：校验器用 `len(body)<=3500`（**字符**），文档引用 **byte 4028** 截断观测 | 单位不一致（可达反例已实测） | 见 §9.1 实测 | `EXTEND` |
| GAP-07 | 审计可见性协议只存在于项目专用包，未提炼为按需 recipe | RULE_TOO_VAGUE | 8/27–28 两份外审报告（C）；`CONTEXT_COMPLETENESS_FOR_DECISION_AUDIT` 未进通用模板 | `EXTEND` |
| GAP-08 | 按需 audit/ops/learning/dispatch 配方缺失（共享文件回读、破坏性操作保全、learning 关闭证据、模型派发字段） | PARTIALLY_PERSISTED | L09/L10/L14/L16/L17 | `EXTEND` |
| GAP-09 | Bootstrap live adoption 与 GitHub enforcement 无验收定义 | DEPLOYMENT_ONLY | `BOOTSTRAP_LIVE_VALIDATION = NOT_RUN`；main protected=false | `DEPLOYMENT_ONLY` |

---

## 3. TARGET_BEHAVIOR（要求清单）

每条 requirement 具有稳定 ID、分类标记与验收映射。**REQ-* 是本 Spec 的规范主体；§8 给出统一验收矩阵。**

### 3.1 工作包 W1 — Seam + Reachability

**REQ-W1-01**（`EXTEND`，`references/ticket-lane.md`）
扩展既有合同块（不新建独立 Seam 权威体系），新增生产形状字段组：

```yaml
SEAM_ID / AUTHORITY_REF / CONTRACT_VERSION
PRODUCER / CONSUMER
SEMANTIC_OWNER / IDENTITY_OWNER / PERSISTENCE_OWNER / RETRY_OWNER / ERROR_OWNER
INPUT_CONTRACT / OUTPUT_CONTRACT
SYNC_OR_ASYNC / AWAIT_REQUIREMENT / LIFECYCLE_REQUIREMENT
LEGAL_STATES / ILLEGAL_STATES / FAIL_OPEN_OR_FAIL_CLOSED
MUST_FIELDS / MUST_NOT_FIELDS
PRODUCTION_CALLER / TEST_CALLER / OBSERVABLE_PRODUCTION_EFFECT
REAL_SHAPE_FIXTURE_OR_ADAPTER
SEAM_COUNTEREXAMPLES / PRODUCTION_REACHABILITY_PROOF
```

字段**按边界是否变化触发，不按票字数或仅按 LOW 标签豁免**。**不要求所有票填写所有字段**；不适用字段可 `N/A`，但 **N/A 必须来自合同适用性判定并给出理由**，不得以 `UNKNOWN` 冒充已冻结。纯文档等无边界的票可整体 `N/A`（须有理由）。

**REQ-W1-02**（`EXTEND`，`references/execution-stage.md`）
拆票前检查引用该合同：切片前输出 seam 清单并确认上下游真实形状或权威接口来源；**已有实现时先取得目标 RED**。拆票前**不要求**提前完成产品 E2E；但**不得用未验证假设声明集成已完成**。

**REQ-W1-03**（`EXTEND`）
Integration 关闭增加 Runtime Reachability 证据字段：

```text
REAL_ENTRYPOINT / PRODUCTION_CALL_CHAIN
EXPECTED_PRODUCTION_EFFECT / OBSERVED_PRODUCTION_EFFECT
TEST_ONLY_CALLERS / PRODUCTION_CALLERS
RUNTIME_REACHABLE / EVIDENCE_REF
```

涉及 wiring / registration / composition / entrypoint 的票，必须证明**真实入口 → 变化 seam → 实际效果**。**测试直调内部模块不能单独满足此条件。** 动态注册 / 插件 / 回调允许以**合法运行证据**证明，**不以文本 grep 直接函数调用次数为最终裁决**。相关 Integration 票无合法生产调用路径 → `INTEGRATION_COMPLETE = FALSE`。

**REQ-W1-04**（`EXISTING`，重申不新增）
责任分离保持不变：worker / native harness 生产证据；L0 校验身份、结构、执行状态与引用；reviewer 判断合同覆盖与效果；integrator 核验实际集成结果后方可关闭。允许**真实 adapter + 确定性传输替身**（保生产协议/async/错误形状，不访问网络）；**不强制每票调用付费 API，不强制全员 live E2E**。

### 3.2 工作包 W2 — Review Evidence 最小机制

**REQ-W2-01**（`NEW`）
新增最小机器证据接口，**唯一证据接口详情落点**：

```text
references/review-evidence.md            # 唯一接口详情（single source）
schemas/review-evidence.schema.json      # versioned schema
templates/review-evidence.json           # 占位符形态模板（R2 兼容）
scripts/review_evidence.py               # 薄 collect/validate CLI
```

**边界约束**：不修改 `project-state` 的状态职责，不复制其全文，不建立第二状态源或第二 tracker。

**REQ-W2-02**（`NEW`）Producer 职责

- 收集**可直接核验**的 repo / base / candidate / diff 等事实；接收原生测试/CI **结果与 artifact reference**。
- 记录**来源与未验证项**（`unverified` 字段）。
- **不替项目执行任意 build/test 命令**；**不读取或执行 evidence 文件提供的任意 shell 指令**（evidence 是数据，不是可执行权威）。

**REQ-W2-03**（`NEW`）Validator 职责 — 三层不可坍缩

```text
STRUCTURALLY_VALID          schema 合法
SOURCE_VERIFIED             来源已核验（SHA/路径/可取回）
EVIDENCE_SUFFICIENT         证据充分
```

**不得**因 schema 合法、字段写 `PASS`、或 `exitCode = 0` 就宣告行为通过。对以下情形给明确失败：未知 schemaVersion、缺必需结果字段、SHA 不符、产物丢失或内容摘要变化、路径越界读取（拒绝被污染的路径）。

**复用现有公开发布/隐私政策，不自建第二套 secret scanner**；**不把原始 runtime-local grounding receipt 全量发布**（machine-local 状态绝不 commit，见 `references/project-continuity-contract.md` §6.4）。

**REQ-W2-04**（`NEW`）最小字段组

```text
subject(repo/baseSha/candidateSha) / authorityRefs
producer(identity/version/observedAt)
checks(id/scope/commandRef/status/exitCode/artifactRefs)
artifacts(location/contentDigest)
ci(run/job/checkedSha/originalState)
grounding(mode/coverage/evidenceRef)
seams(applicability/evidenceRefs)
reuse(sourceEvidence/validFor/dependencies/invalidation)
unverified
```

字段按适用性扩展，**不给小票强加全量表格负担**。

**REQ-W2-05**（`NEW`）语义 scope 的权威分离

**观测到的 changed files 不自动成为批准编辑范围**（与 `project-continuity-contract.md` §6.7 F4 `APPROVED_EDIT_SURFACE` / `OBSERVED_DELTA` / `IMPACT_SURFACE` 三面分离同源）。语义 scope 仍由 reviewer 判断；`semanticScopeStatus` 由 reviewer 结论写入，不由 producer 观测自动升格。

**REQ-W2-06**（`NEW`）Consumer 与自批禁止

- L1/L2 读取并核验相关证据，**保留独立判断**。
- Integrator 使用**同一候选绑定**的证据。
- Stage packet **只引用，不复制**为第三个账本。
- **机器证据包不得自批 reviewer verdict**（`reviewerDecisionRefs` 与机器事实分字段；`RULES.md` R4）。

**REQ-W2-07**（`NEW`）存储与 SHA 循环避免

- 优先**引用已有 CI artifact / PR evidence**。
- **不为把含 candidate SHA 的证据提交进候选仓而破坏 candidate 身份**：若每次提交报告都改变 candidate SHA，则形成循环。如仓政策要求提交报告，**必须显式区分 `subject commit` 与 `report commit`**，且**新增报告提交不得自动继承旧评审 PASS**。

### 3.3 工作包 W3 — Review / Stage / CI Consumption + Reuse/Invalidation

**REQ-W3-01**（`EXTEND`）证据类型独立有效期

**不统一成"任何 HEAD 前进则所有 receipt 失效"。** 分别保持：

```text
reviewer PASS       → 绑定原 exact SHA（RULES R5）
CI                  → 绑定真实运行检查的 SHA 与对应 jobs
grounding           → 服从现有 base/ancestry/mode/freshness 合同
durability          → 服从现有 current HEAD / meaningful transition 合同
测试证据            → 绑定实际输入、代码、配置、环境与测试范围
```

**REQ-W3-02**（`EXTEND`）跨候选复用条件

只能声明**特定证据在明确范围仍适用**；必须有**依赖未变的依据**。**不能把旧结果改名成新 SHA 的全量 PASS。** 依赖分析 `UNKNOWN` 时 → **重跑所需范围或请求必要证据**，不得默认复用。

**REQ-W3-03**（`EXTEND`）失效触发清单

```text
master drift
共享 schema / 共享依赖变化
入口拓扑变化
authority / profile / toolchain 相关变化
```

命中 → 触发**对应**失效检查（定向，不是全量重做）。

**REQ-W3-04**（`EXISTING`，重申不新增）CI 状态语义

保留原 CI 状态集合：`PASS / FAIL / NOT_TRIGGERED / CANCELLED / INFRASTRUCTURE_FAILURE / KNOWN_BASELINE_FAILURE / UNKNOWN`。**`KNOWN_BASELINE_FAILURE` / `NOT_TRIGGERED` / `UNKNOWN` 不等于 PASS**。非 PASS 分类继续依赖**现有独立接受**与明确仓政策。**不得生成新失败状态机替换旧状态系统**（见 GAP-05 与 §3.6 INV 表）。

### 3.4 工作包 W4 — Scoped Recipes + 字节预算修正

**REQ-W4-01**（`EXTEND`）Bootstrap 字节预算修正

按 **UTF-8 字节**检查**实际部署正文**，对齐文档、候选与校验器**单位**。宿主容量是**观测/profile 信息**，**不是跨 runtime 常数**。

- **当前静态修正**（校验器 + 文档措辞）与**未来真实部署**分开处理；本 Spec 只授权前者。
- 迁移与兼容见 §7。

**REQ-W4-02**（`NEW`）按需配方（audit / ops / learning / dispatch）

新增按需（非全票强制）recipe：

- **Audit visibility**：`evidence / requested SHA / actually read scope / SEEN|PARTIAL|NOT_SEEN|UNCERTAIN / supports / missing / verdict impact / recovery artifact`，并分别输出 `CONTEXT_COMPLETENESS_FOR_DECISION_AUDIT` 与 `FULL_HISTORICAL_TRANSCRIPT_COMPLETENESS`。**外审 primary 不可见时必须限定结论，不得伪称完整**（8/27 Perplexity 报告 MORE_EVIDENCE_REQUIRED 为正例）。
- **Destructive workspace transaction safety**：`status → 未提交/未追踪/owner → 保全 → 操作 → post-state`；基线优先独立干净 worktree；禁止动其它 lane 工作；仅对破坏性动作触发。**不建立全局 stash 禁令**（底层因果 `NEEDS_PRIMARY_EVIDENCE_RECOVERY`，见 §4.3）。
- **Shared-file single-writer + readback**：同一共享文件聚合成一次/串行修改，**最终回读核验所有预期条目**（不得以编辑工具成功代替内容核验）。
- **Learning closure**：关闭必须有**采纳/拒绝理由 + 验证引用**；不得仅标"bug fixed"。
- **Model dispatch**：`ROLE / TASK / RISK / MODEL_OR_TIER / REASONING_EFFORT / WHY / EXPECTED_OUTPUT / ESCALATE_IF`。风险先于型号；**型号放可更新 profile，不写死不变量**。

**REQ-W4-03**（`EXTEND`）ZCode guard 运行时映射

`exit 2` 需要 **runtime 映射为 deny**；**不能只验证脚本打印 BLOCK**。

**REQ-W4-04**（`EXTEND`）Gate 入口自测

会授权继续执行的脚本必须验证：`argv → main`、退出码、结构化输出与**实际副作用/探针**。**模块 import 不冒充 CLI**；`exit 0 + 空输出` 不得满足门禁。

### 3.5 工作包 W5 — Live Adoption + Server Enforcement（`DEPLOYMENT_ONLY`）

**REQ-W5-01**（`DEPLOYMENT_ONLY`）Bootstrap live 验收

fresh neutral session / project session；验证 authority loading / override handling；state restore / authorized auto-advance；真实工具事件 → hook → runtime deny → **目标未被修改**；失败与 advisory 降级**如实记录**（`NOT_RUN` ≠ PASS）。

**REQ-W5-02**（`DEPLOYMENT_ONLY`）GitHub enforcement

GitHub enforcement 是**仓库部署政策**，不是所有项目通用硬规则。本 Spec 只**定义未来验收与所需权限**；**不在本阶段配置 required checks / rulesets / bypass**；**不得通过向真实未保护 main 试推来验证缺口**。

### 3.6 INVARIANTS

```text
INV-01  SELF_REVIEW != INDEPENDENT_REVIEW WHEN THE GATE EXISTS（RULES R4，条件式）
INV-02  UNKNOWN != PASS；NOT_TRIGGERED != PASS；KNOWN_BASELINE_FAILURE != PASS
INV-03  机器证据包不得自批 reviewer verdict
INV-04  观测 changed files 不自动成为批准编辑范围
INV-05  Integration 关闭必须有真实入口 → 效果的证据（或显式 INTEGRATION_COMPLETE = FALSE）
INV-06  证据复用必须绑定候选身份与依赖；跨 SHA 不得全量继承
INV-07  单一 canonical owner：不新建第二 project-state / tracker / Stage system / 证据数据库
INV-08  N/A 必须来自合同适用性，不是 worker 快捷豁免
INV-09  治理变更不随实现票顺手进行（AGENTS §8）
INV-10  评审历史 append-only；修复 = 新 commit → 新 SHA（RULES R5）
```

---

## 4. AUTHORITY_OWNER

### 4.1 权威归属（不新增权威层）

| 关注点 | Owner | 性质 |
|---|---|---|
| Spec 批准 / `IMPLEMENTATION_AUTHORIZED` | PRODUCT OWNER（human） | 唯一裁决 |
| B 层普适不变量 | `RULES.md`（本仓 main 版本化） | 不可削弱 |
| D 层执行默认 | `AGENTS.md` + `references/` | 仓政策可显式 OVERRIDE |
| Seam 合同字段 | `references/ticket-lane.md`（canonical owner = AGENTS §3/§4） | `EXTEND`，不建第二权威 |
| 拆票前检查 | `references/execution-stage.md`（canonical owner = AGENTS §2/§4） | `EXTEND` |
| Review evidence 接口 | 本 Spec §3.2 → 未来 `references/review-evidence.md` | `NEW`，单一接口详情 |
| CI 语义 | `references/git-ci-integration.md`（canonical owner = RULES R3/R5 + AGENTS §6） | `EXISTING` |
| 评审分级 / 收敛 | `references/review-and-repair-saturation.md`（canonical owner = AGENTS §6/§9） | `EXISTING` |
| 状态索引 / grounding 生命周期 | `references/project-continuity-contract.md`（canonical owner = AGENTS §7.1） | `EXISTING` |
| Bootstrap 机制 | `deployment/BOOTSTRAP_CONTRACT.md` | `EXTEND`（单位对齐） |
| GitHub 保护设置 | 仓部署政策 / PRODUCT OWNER | `DEPLOYMENT_ONLY` |

### 4.2 冲突处理

按 `audit/AUTHORITY_MAP_V2.md`：A 平台 > B 不变量 > C 仓权威 > D 全局默认 > E 方法 > F 记忆。D 层覆盖必须**显式记录** `OVERRIDE = <clause> overridden by <authority> <clause> (source)`；静默覆盖 = 违规；**加严永远合法**。

### 4.3 明确不作出的决策（NOT_VERIFIED / 保留矛盾）

| 项 | 状态 | 理由 |
|---|---|---|
| 全局 stash 禁令 | `REJECTED_WITH_REASON` | 底层因果 `NEEDS_PRIMARY_EVIDENCE_RECOVERY`；不推广 |
| 所有票强制 L2 | 不采纳 | 违 R8 最小复杂性 |
| 每票跑 live 付费 API E2E | 不采纳 | 允许真实 adapter + 确定性替身 |
| 所有项目无条件 ff-only | 不采纳 | ff-only 是 D 层默认，C 层可覆盖 |
| "50 个测试"史实 | 不采用 | 无事故前快照支持；PR 后 40/40、21/21 属不同套件 |
| 8 月 finding 的精确模型档位与 P0 标签 | `NOT_VERIFIED` | 可见正文无该标签 |
| 具体 T07/T10/T11 冻结三票场景 | `NOT_VERIFIED` | `PRIMARY_LOCATOR = NOT_FOUND`；只作验收场景 |
| `REVIEW_EVIDENCE.json` 历史实现 | `NOT_VERIFIED` | 历史原名/schema `NOT_FOUND`；本 Spec 结构是**提案** |
| 知乎 HEAD 与治理 HEAD 的一致性 | `NOT_VERIFIED` | 知乎 `ac49336d…` 为 2026-09-16 输入报告快照；本 Spec 未重新核验 |

---

## 5. DATA_AND_EVIDENCE_CONTRACT

### 5.1 唯一接口详情（规范形态）

`references/review-evidence.md` 是唯一证据接口详情；schema 与模板是其机械形态。字段语义：

| 字段 | 语义 | 失败语义 |
|---|---|---|
| `schemaVersion` | 证据包版本 | 未知版本 → `EVIDENCE_VERSION_UNKNOWN`（reject，不猜测迁移） |
| `subject.repo` | 目标仓 remote | 与目标仓不符 → `EVIDENCE_SUBJECT_MISMATCH` |
| `subject.baseSha` | 候选基线全文 SHA | 不可解析 → reject |
| `subject.candidateSha` | 被评候选全文 SHA | 与当前 candidate 不符 → `EVIDENCE_STALE_SUBJECT` |
| `authorityRefs` | 版本化合同引用 | 缺失 → 证据不充分 |
| `producer.identity/version/observedAt` | 生成者与时间 | 缺失 → 来源未核验 |
| `checks[].id/scope/commandRef/status/exitCode/artifactRefs` | 机械检查事实 | `status=PASS` 但 `artifactRefs` 不可取回 → 拒绝 |
| `artifacts[].location/contentDigest` | 产物与内容摘要 | 摘要变化 → `EVIDENCE_ARTIFACT_CHANGED` |
| `ci.run/job/checkedSha/originalState` | CI 事实 | `checkedSha != subject.candidateSha` → 不得作为该候选 CI 证据 |
| `grounding.mode/coverage/evidenceRef` | 接地模式与覆盖 | 与 `codegraph-grounding.md` §2.1 命名不一致 → 拒绝 |
| `seams.applicability/evidenceRefs` | Seam 适用性与证据 | `applicability = N/A` 无理由 → 拒绝 |
| `reuse.sourceEvidence/validFor/dependencies/invalidation` | 复用声明 | `dependencies = UNKNOWN` 且声明复用 → 拒绝 |
| `unverified[]` | 显式未验证项 | 空数组合法；**不得以省略代替** |

### 5.2 证据分层与不越界（`EXTEND`，对齐既有 L0/L1/L2）

| 层 | 生成/消费 | 不可越界 |
|---|---|---|
| L0 | exact SHA/base、diff 清单、syntax/type/test 结果、CI run、路径/secret 扫描、图谱模式与覆盖、已执行反例 | 文件清单**不自动裁决语义 scope**；CodeGraph 输出**不是**完整语义影响证明 |
| L1 | 独立 grounding；合同、seam、失败语义、缺失反例、owner、scope creep | 不把 worker findings 当唯一检查面；**不自批** |
| L2 | 架构/安全/并发/canonical 权威/未决分歧/Spec 与 governance 变更/里程碑/高爆炸半径 | 可抽查 L0/L1 证据与提出新反证；**减少重复不等于禁止推翻前审** |

### 5.3 Secret / 隐私

复用既有公开发布政策与 `scripts/validate_public_release.py`。**不自建第二套 secret scanner**。原始 runtime-local grounding receipt **不全量发布**。

---

## 6. FAILURE_SEMANTICS

### 6.1 三类失败必须可分

```text
REJECT              结构/来源/必填不合法 → 不进入消费
INSUFFICIENT        结构合法但证据不足（缺必需结果、未知 scope、依赖 UNKNOWN）→ 不得当作 PASS
CONSUMER_UNSATISFIED  证据合法但 consumer 门未满足（如空跑 exit 0、无有效结果）→ gate 不开
```

### 6.2 关键失败映射（逐条对齐旧事故）

| 旧事故 | 新机制的失败语义 |
|---|---|
| D6 async seam | `checks` 中 producer 形状与 consumer 期望不一致 → `SEAM_SHAPE_MISMATCH`；`pending` 期间写完成态 → 非法状态，red |
| T15 reachability | `PRODUCTION_CALLERS = []` 且票声明接线 → `INTEGRATION_COMPLETE = FALSE`（不得绿） |
| D5 empty-run | `exitCode = 0` 但无有效结构化结果 → `CONSUMER_UNSATISFIED` |
| 陈旧产物复用 | `contentDigest` 变化或 `reuse.dependencies = UNKNOWN` → 拒绝复用 |
| 错 SHA | `subject.candidateSha` 不符 → `EVIDENCE_STALE_SUBJECT` |

### 6.3 不得生成的失败语义

不新增替换既有 CI 状态机的新枚举；不把 `UNKNOWN` 折叠为任一终态；不支持"重试直到碰巧成功"。

---

## 7. INTEGRATION_POINTS

| 集成点 | 现有文件 | 变更性质 |
|---|---|---|
| 单票生命周期 / Seam 合同 | `references/ticket-lane.md` §3 | `EXTEND` 生产形状字段组 |
| 拆票前检查 | `references/execution-stage.md` §6 | `EXTEND` 引用 Seam 合同 |
| Integration 关闭条件 | `references/git-ci-integration.md` §4/§5 + AGENTS §6 | `EXTEND` reachability 证据 |
| Review 分级与消费 | `references/review-and-repair-saturation.md` §1/§4 | `EXTEND` 引用 evidence 接口 |
| Evidence 接口 | **新增** `references/review-evidence.md` | `NEW` |
| Evidence 机械形态 | **新增** `schemas/review-evidence.schema.json`、`templates/review-evidence.json`、`scripts/review_evidence.py` | `NEW` |
| 状态索引契约 | `references/project-continuity-contract.md` | `EXISTING`（不修改语义，只被引用） |
| Bootstrap 预算 | `deployment/BOOTSTRAP_CONTRACT.md` §2.1、`deployment/MEMORY_POINTER_CANDIDATE.md`、`scripts/validate_governance.py`（`memory-pointer-within-budget` 检查） | `EXTEND` 单位对齐 |
| 公开发布扫描 | `scripts/validate_public_release.py` | `EXISTING`（复用，不改判定） |
| CI 接入 | `.github/workflows/governance-ci.yml` | `EXTEND`（新增 evidence CLI 自测步骤；不新建 runner） |
| GitHub 保护 | repo settings | `DEPLOYMENT_ONLY` |
| 知乎仓 | `FlapPearLabs/zhihu-grabber-toolkit` | **无集成点**（`EVIDENCE_SOURCE_REPO`，本 Spec 不修改） |

---

## 8. MIGRATION_AND_COMPATIBILITY

### 8.1 Bootstrap 字节预算迁移（REQ-W4-01 的兼容面）

**实测事实（本 Spec 写作期间核验，机器可复现）**：

```text
POINTER_CHARS           = 1170
POINTER_UTF8_BYTES      = 1804
CURRENT_CHECK           = len(body) <= 3500（字符）
DOC_CLAIMED_TRUNCATION  = 4028（byte，BOOTSTRAP_CONTRACT §1 观测）
POINTER_PASSES_CHAR_CHECK = True
POINTER_PASSES_BYTE_CHECK = True
```

**可达反例（同一实测，证明单位不一致）**：

```text
CJK1400_CHARS           = 1400
CJK1400_UTF8_BYTES      = 4200
CJK1400_PASSES_CHAR_CHECK = True      ← 旧字符条件放行
CJK1400_PASSES_BYTE_CHECK = False     ← 按截断观测应拒绝
```

结论：**1400 个汉字 = 4200 UTF-8 字节，可通过旧字符条件**，但**超过实测截断点 byte 4028**。单位不一致会放行实际会被截断的正文。

**迁移要求（必须同时满足）**：

```text
MIG-01  校验器按 UTF-8 字节检查指针正文
MIG-02  文档、候选、校验器三方单位一致（全部 byte）
MIG-03  文档措辞不得把宿主容量写成跨 runtime 常数
MIG-04  当前正文（1804 byte）在新条件下保持 PASS（无回归）
MIG-05  预算阈值来源必须显式标注为观测/profile，不是规范常数
```

**兼容性**：当前正文两条件均 PASS，故本修正**不产生 breaking change**；修正后用户若未来写入更多 CJK 文本，将在真正超限时被拒绝而非静默截断。

### 8.2 分阶段实施（未来分解边界，**不创建 implementation tickets**）

建议五个工作包，仅作分解边界参考；实际票据分解须在 Spec 获独立审查 PASS 后另行授权。

| 包 | 内容 | 依赖 | 写权冲突 |
|---|---|---|---|
| W1 | Seam + Reachability（`EXTEND` ticket-lane / execution-stage / git-ci-integration） | 无 | 与 W2 共享 `references/` 但文件不同 |
| W2 | Evidence producer/schema/validator + CLI self-tests | 无 | 新增文件，低冲突 |
| W3 | Review/Stage/CI consumption + reuse/invalidation | **依赖 W1 + W2** | 引用 W1/W2 产物 |
| W4 | Scoped audit/ops/learning/dispatch + byte budget | 无（byte budget 独立） | 触 `validate_governance.py` |
| W5 | Live adoption + server enforcement | **依赖 W1–W4 核心合并** | `DEPLOYMENT_ONLY`，需单独授权 |

**硬约束**：**W2 未接入 W3，不得称机制完成。** 不为凑数拆票。

### 8.3 变更传播与失效

- 本 Spec 一旦获批准，其 requirement 是**未来票据的溯源权威**；实现票不得顺手改治理（`AGENTS.md` §8）。
- 修改 `RULES.md` / `AGENTS.md` / canonical reference 默认走**双独立评审**（合同向 + 一致性向）对同一 exact HEAD PASS。
- 本 Spec 自身变更 = 新 commit → 新 SHA → **重新走独立 exact-SHA Spec review**；已评审历史不 amend/rebase/force-push（RULES R5）。

---

## 9. COUNTEREXAMPLES

以下反例是**验收的 RED 输入**。每条瞄准"看起来合理、过了显眼测试、仍违反合同"的实现。**允许合并测试，不要求一例一测试。**

```text
CE-01  sync 理想 mock 通过，但真实 async adapter 不兼容 → 必须检出
CE-02  producer 在 delayed resolve 之前被写为完成态 → 必须拒绝
CE-03  producer reject 与 resolved-but-malformed 被压成同一失败态 → 必须区分
CE-04  生产入口断接线，新行为内部测试全绿 → Integration 必须失败
CE-05  合法动态注册/回调路径被静态 caller 计数误拒 → 必须放行
CE-06  evidence 携带错误 repo / baseSha / candidateSha → 必须拒绝
CE-07  缺 artifact、contentDigest 变化、必需证据不可取回 → 不得当作 PASS
CE-08  validator exit 0 但空跑/无有效结果 → 不能满足 consumer
CE-09  helper 测试通过，真实 CLI 与 consumer 接线未测 → 不得满足门
CE-10  同一组正反样例下 schema 与 validator 处置不一致 → 必须一致
CE-11  相关依赖变更后旧证据仍被复用 → 必须触发失效
CE-12  无关证据因"安全起见"被无理由全量重做 → 不应触发（避免过度失效）
CE-13  纯文档票合法 N/A → 必须接受
CE-14  runtime wiring 票滥用 N/A → 必须拒绝
CE-15  外审 primary 不可见却给出完整结论 → 必须限定结论或 MORE_EVIDENCE_REQUIRED
CE-16  保全操作丢失 tracked 修改或 untracked 成果 → 必须拒绝
CE-17  共享文件多项预期更新中任一在最终回读时缺失 → 必须检出
CE-18  learning 条目在无采纳/拒绝理由与验证引用时被关闭 → 必须拒绝
CE-19  bootstrap 字节预算被字符数条件代替（1400 汉字场景）→ 必须拒绝
CE-20  ZCode guard 仅打印 BLOCK 但 runtime 未映射为 deny → 目标被修改时必须失败
```

**Gate 自测覆盖要求**：`PASS`、`FAIL`、`malformed`、`silent-noop`、**真实命令入口**；**正确结果与错误结果都要检查消费者实际处置**（不仅检查 validator 输出）。

---

## 10. ACCEPTANCE

### 10.1 映射要求

每项 requirement 必须映射：

```text
requirement → producer → interface → consumer → evidence → acceptance
```

允许合并测试，**不要求凑测试数量**。**不使用固定测试总数作为通过标准。**

### 10.2 行为覆盖矩阵

| # | 验收行为 | 覆盖 REQ | CE |
|---|---|---|---|
| AC-01 | sync 理想 mock 通过但真实 async adapter 不兼容时检出 | REQ-W1-01/04 | CE-01 |
| AC-02 | delayed resolve 之前不得提前写完成态 | REQ-W1-01 | CE-02 |
| AC-03 | reject 与 resolved-malformed 分别保留失败语义 | REQ-W1-01 | CE-03 |
| AC-04 | 生产入口断接线时，内部测试通过仍不能关闭 Integration | REQ-W1-03 | CE-04 |
| AC-05 | 合法动态注册路径可以通过，不被静态 caller 数误拒 | REQ-W1-03 | CE-05 |
| AC-06 | evidence 错 repo/base/candidate SHA 被拒 | REQ-W2-03 | CE-06 |
| AC-07 | 缺产物、内容摘要变化、不可取回必需证据不能当 PASS | REQ-W2-03 | CE-07 |
| AC-08 | validator exit 0 空跑/无有效结果不能满足 consumer | REQ-W2-03/06 | CE-08 |
| AC-09 | helper 测试不能替代真实 CLI 与 consumer 接线测试 | REQ-W4-04 | CE-09 |
| AC-10 | schema 与 validator 对同组正反样例保持一致处置 | REQ-W2-03 | CE-10 |
| AC-11 | 相关依赖改变触发失效；无关证据不无理由全量重做 | REQ-W3-01/02/03 | CE-11/CE-12 |
| AC-12 | 文档 N/A 合法；runtime wiring 不能滥用 N/A | REQ-W1-01/02 | CE-13/CE-14 |
| AC-13 | 外审 primary 不可见时限定结论，不伪称完整 | REQ-W4-02 | CE-15 |
| AC-14 | 保全操作不丢 tracked 修改与 untracked 成果 | REQ-W4-02 | CE-16 |
| AC-15 | 共享文件多项预期更新经最终回读均存在 | REQ-W4-02 | CE-17 |
| AC-16 | learning 关闭有采纳/拒绝理由与验证引用 | REQ-W4-02 | CE-18 |
| AC-17 | bootstrap 的字节预算不能被字符数条件代替 | REQ-W4-01 / MIG-01..05 | CE-19 |
| AC-18 | ZCode guard 的 runtime deny 映射真实生效 | REQ-W4-03 | CE-20 |

### 10.3 Gate 自测覆盖

```text
PASS / FAIL / malformed / silent-noop / 真实命令入口
正确结果与错误结果都要检查消费者实际处置
```

### 10.4 本 Spec 自身的验收（本次会话）

```text
SPEC COMMITTED
SPEC PUSHED
REMOTE EXACT SHA VERIFIED
SPEC_REVIEW = PENDING
STOP
```

**`SELF_REVIEW != SPEC_APPROVAL`**：本 Spec 的自检、格式校验、远端上传成功**均不构成**批准。

---

## 11. OUT_OF_SCOPE

```text
1.  修改知乎仓任何文件或状态
2.  实现 scripts / schema / runtime behavior（本阶段只写 Spec）
3.  修改现有 canonical 治理规则（RULES.md / AGENTS.md / references/*）
4.  修改 bootstrap 实际部署或 GitHub 保护设置
5.  关闭治理 Issue #9
6.  创建 implementation tickets
7.  merge 主分支
8.  自行宣布 Spec 已批准
9.  创建第二 project-state / 第二 tracker / 第二 Stage system
10. 创建通用 CI runner / 通用 orchestration framework / 独立证据数据库
11. 建立全局 stash 禁令
12. 配置 required checks / rulesets / bypass
13. 通过向真实未保护 main 试推来验证缺口
14. 把两份 evidence 附件复制/提交/迁移进本仓
```

---

## 12. IMPLEMENTATION_STAGING

本 Spec 是**授权边界**，不是施工令。四类动作必须严格区分：

| 阶段 | 动作 | 当前授权 |
|---|---|---|
| **S0 本轮 Spec 写作** | 新建本文件（+ 必要 Spec 审查说明）；commit + push feature branch；核验远端 exact SHA | ✅ 本轮已授权 |
| **S1 core 实现** | W1–W4 的 canonical 变更与新增文件 | ❌ **需要 owner 明确 `SPEC_REVIEW = PASS` 后才进入拆票与执行** |
| **S2 core 合并后采用** | 把已合并的 canonical 变更在真实仓采用（含 bootstrap 静态修正落地） | ❌ 需 S1 完成 + 单独授权 |
| **S3 live deployment** | bootstrap 真实部署、GitHub enforcement、host guard deny 映射实测 | ❌ `DEPLOYMENT_ONLY`，需**单独 live 部署授权** |

### 12.1 固定后续链路

```text
架构审计（已完成）
→ SPEC_AUTHOR 写 Spec（本轮）
→ push feature branch
→ STOP
→ ChatGPT 独立 exact-SHA Spec review
→ 仅当 owner 明确确认 SPEC_REVIEW = PASS
→ 才进入拆票 / 票据一致性审查 / 执行阶段与实现
```

**不得把自检通过、远端上传成功或自审通过，冒充 Spec 已获批准。**

### 12.2 本 Spec 的 requirement 分类总表

| 分类 | Requirements |
|---|---|
| `EXISTING`（重申，不新增） | REQ-W1-04, REQ-W3-04 |
| `EXTEND` | REQ-W1-01, REQ-W1-02, REQ-W1-03, REQ-W3-01, REQ-W3-02, REQ-W3-03, REQ-W4-01, REQ-W4-03, REQ-W4-04 |
| `NEW` | REQ-W2-01, REQ-W2-02, REQ-W2-03, REQ-W2-04, REQ-W2-05, REQ-W2-06, REQ-W2-07, REQ-W4-02 |
| `DEPLOYMENT_ONLY` | REQ-W5-01, REQ-W5-02 |

### 12.3 NOT_VERIFIED 汇总

```text
NOT_VERIFIED  W1–W5 的任何实施状态（本 Spec 未实现任何代码）
NOT_VERIFIED  知乎仓当前 HEAD 与输入报告快照的一致性
NOT_VERIFIED  8 月外审 finding 的精确模型档位与 P0 标签
NOT_VERIFIED  REVIEW_EVIDENCE.json 的历史 schema / producer 实现
NOT_VERIFIED  所有宿主的 fresh-session 采用与自治运行状态
NOT_VERIFIED  stash 事件的底层根因
NOT_VERIFIED  历史报告中的任何测试 PASS 数值（本轮未重跑）
```

---

## 13. NEW_ARCHITECTURE_FINDINGS

本 Spec 写作期间**未发现**需要触发升级的架构冲突：

```text
CONTRACT_CONFLICT                        = NONE
AUTHORITY_CONFLICT                       = NONE
Astra architecture decision 与 canonical  = 无实质冲突
新证据改变 owner / state model / public interface = NONE
```

一条**非架构性**发现（不改变 owner 或合同，仅确认既有单位缺陷可机械证明）：bootstrap 字节预算的字符/字节单位不一致已被实测反例证实（§8.1），且**当前正文在两条件下均 PASS**，故修正属**向后兼容的收紧**，不需要架构升级。

受影响 requirement：`REQ-W4-01`。最小候选解决方案：`MIG-01..MIG-05`（已写入要求）。因可在既有 authority 下唯一解决，**不 STOP**。

---

## 14. 输入证据引用

本 Spec 的两份 `EVIDENCE_INPUT`（**只读，未复制进本仓，未修改原件**）：

```text
P1_AGENT_ENGINEERING_RETROSPECTIVE_FINAL_2026-09-16.md
  SHA256 = d52cd47f18d56abe87ceb3aef6c23ab90372af64802b3f572de676e028c3758c   ✅ VERIFIED

P1_DIALOGUE_EVIDENCE_SUPPLEMENT_FINAL_2026-09-16.md
  SHA256 = 7375caad167a395aea5201b5d642e945ca048e787a7f4b494af3bf328a370f07   ✅ VERIFIED
```

文件名含 `FINAL` **不表示**其中提案已实现或已生效；两份文件是经验与方案证据，不是已生效的全局规则。

关键历史证据（B/C 级，本 Spec 未重跑）：

```text
治理 Issue #9    Production Runtime Reachability（OPEN）
知乎 PR #87      async adapter seam（merged 9444a33b3ca24a53f8da4b9e2cb03a241925f47f）
知乎 PR #78      T15 零生产调用者接线（merged head 4a6767ff8b40c7bf2dbee2f220fc5194f553ede5）
知乎 PR #86      CLI 入口空跑与吞异常（merged 0d305b03c64f8b4f057415a29043aa41af082576）
audit/GAP_MATRIX.md G-09   review harness = NEXT
```

仓内部署事实（本 Spec 写作期间核验）：

```text
repo visibility        = public
default_branch         = main
branch protection main = not protected (HTTP 404)
rulesets               = []
main HEAD (local+remote) = 0ba2c7351d45dba1459a391b0d43e418ecf55280
open PRs               = 0
```

---

## 15. 本轮执行边界声明

```text
ROLE                     = SPEC_AUTHOR
ADDITIONAL_ARCHITECT_EXPERT = NONE（未调用新架构专家重议已收敛问题）
FILES_CREATED             = docs/specs/P1_AGENT_ENGINEERING_GOVERNANCE_DELTA_SPEC.md
IMPLEMENTATION_FILES      = NONE（§3.2 落点是未来实现目标，本轮未创建）
ZHIHU_MODIFIED            = NONE
CANONICAL_MODIFIED        = NONE
ISSUE_9                   = OPEN（未关闭）
SPEC_REVIEW               = PENDING
NEXT_LEGAL_ACTION         = CHATGPT_INDEPENDENT_EXACT_SHA_SPEC_REVIEW
```
