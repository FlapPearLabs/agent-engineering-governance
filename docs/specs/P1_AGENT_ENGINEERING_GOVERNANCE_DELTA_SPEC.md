# SPEC — P1 AGENT ENGINEERING GOVERNANCE DELTA

```text
SPEC_ID              = P1_AGENT_ENGINEERING_GOVERNANCE_DELTA
SPEC_VERSION         = 1 (draft, adversarial finding micro-repair)
STATUS               = DRAFT_FOR_INDEPENDENT_REVIEW
IMPLEMENTATION_AUTHORIZED = NO
REVIEW_GATE          = CHATGPT_INDEPENDENT_EXACT_SHA_SPEC_REVIEW
REVIEW_SCOPE         = FINDING_SCOPED_DELTA_ONLY
ARCHITECTURE_REVIEW  = PASS（W1–W5 架构已通过，不再重开）
AUTHORITY_OWNER      = PRODUCT OWNER (FlapPearLabs) — Spec 批准与 IMPLEMENTATION_AUTHORIZED 唯一裁决者
SPEC_AUTHOR_ROLE     = SPEC_AUTHOR（非架构重设计者、非实现 worker）
TARGET_REPO          = FlapPearLabs/agent-engineering-governance
ZHIHU_REPO           = FlapPearLabs/zhihu-grabber-toolkit
ZHIHU_ROLE           = EVIDENCE_SOURCE_REPO（只读，本 Spec 不修改其任何文件或状态）
BASE_SHA             = 0ba2c7351d45dba1459a391b0d43e418ecf55280
BASELINE_DRIFT       = NONE（远端 main == 本地 HEAD == BASE_SHA；open PRs = 0）
PRIOR_REVIEWED_SHA   = 6492eedf153f9c5f86c4929baca53ba2247d90d0（repaired: ROUND 6 F-B1 把 `README.md` 纳入完整 change surface，见 §16.10）
REPAIR_HISTORY       = 458ed253 → 7d4887b6 (F1–F6) → c7de399/83b714c (R1–R4)
                       → 3803518a (M1–M3) → 60209cd (F-A1/A2/A3)
                       → 6492eed (ROUND 5 owner 裁定 R5 + 同根一致性修复 R5-1/R5-2/R5-3)
                       → 本轮 ROUND 6（F-B1：`README.md` 纳入完整 change surface）
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

共同点：**边界双方对数据、权威、时序或调用关系的假设不一致**（seam 假设错位）。

**证据强度分层（不得过度概括）**：本轮**未重跑任何历史测试**，也无 D1–D6 逐条事故前的单元测试通过快照（primary evidence）。因此**不主张"D1–D6 全部在单元测试通过的前提下逃逸"**。可主张的是：**D1–D6 的共同模式是 seam 假设错位**；其中 **D6（async adapter，PR #87）、T15（零生产调用者，PR #78）、D5（CLI 空跑吞异常，PR #86）三例有明确 B 级证据（exact GitHub PR + merged SHA）证明"局部测试/验证绿色不能单独证明真实边界成立"**。其余条目（D1/D2/D3/D4）**作为同类模式的候选案例，不单独主张其测试先绿史实**。

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

字段分**两类权威**，不得混为一谈（F1 修正；R1 消歧）：**① 设计与权威字段**（拆票前由 authority/design 侧判定并冻结，定义"要求什么"）；**② 关闭证据字段**（实现完成后由执行侧产生，记录"实际观测到什么"）。**同一事实不得同时成为两个权威来源**；关闭证据只能**填充**设计字段声明的槽位，不能反过来改写设计要求。

**命名纪律（R1，不得由 implementer 自行猜测；行为验收见 `AC-43`）**：**① 类字段必须表达 requirement（"要求什么"）**；**② 类字段必须表达 observation（"观测到什么"）**。两类字段名不得同名、不得近似到需要猜测。以下为本 Spec 冻结的正式命名，ticket / schema implementer **必须照此实现，不得自行发明或改名**：

```text
① requirement 语义（设计侧）             ② observation 语义（关闭侧）
EXPECTED_PRODUCTION_EFFECT        →     OBSERVED_PRODUCTION_EFFECT
EXPECTED_PRODUCTION_CALLER        →     PRODUCTION_CALLERS
REACHABILITY_REQUIREMENT          →     RUNTIME_REACHABLE
```

**本纪律由 `AC-43` 验收**（命名消歧 + 唯一声明点 + 违规触发失败），并由 `INV-19`/`INV-20` 约束、`CE-29`/`CE-30` 作为 RED 输入。**已冻结的字段命名不因本轮修复而改变。**

**① 设计与权威字段（拆票前冻结）**

```yaml
SEAM_ID / AUTHORITY_REF / CONTRACT_VERSION
PRODUCER / CONSUMER
SEMANTIC_OWNER / IDENTITY_OWNER / PERSISTENCE_OWNER / RETRY_OWNER / ERROR_OWNER
INPUT_CONTRACT / OUTPUT_CONTRACT
SYNC_OR_ASYNC / AWAIT_REQUIREMENT / LIFECYCLE_REQUIREMENT
LEGAL_STATES / ILLEGAL_STATES / FAIL_OPEN_OR_FAIL_CLOSED
MUST_FIELDS / MUST_NOT_FIELDS
EXPECTED_PRODUCTION_CALLER            # 要求：必须存在生产调用者（requirement，非观测）
TEST_CALLER
EXPECTED_PRODUCTION_EFFECT            # 期望的生产效果（requirement，非观测；全文唯一声明点）
REAL_SHAPE_FIXTURE_OR_ADAPTER
SEAM_COUNTEREXAMPLES                  # 反例定义（requirement，非执行结果）
<!-- REACHABILITY 设计字段（authority/design 侧） -->
REACHABILITY_APPLICABILITY            # REQUIRED | N/A
REACHABILITY_APPLICABILITY_REASON     # REQUIRED when APPLICABILITY = N/A；N/A 时必填理由
REACHABILITY_APPLICABILITY_ACCEPTANCE_REF
                                      # REQUIRED when APPLICABILITY = N/A；
                                      # 指向 reviewer/integrator 的接受记录（引用槽位，不是结论）
REACHABILITY_REQUIREMENT              # 该 seam 必须被真实入口到达的规范声明
REACHABILITY_PROOF_OWNER              # 谁负责在关闭时提供证据（角色，不是结论）
RED_EXECUTION_OWNER                   # 谁负责在票内执行 RED（角色）
```

**唯一声明点规则（R1）**：`EXPECTED_PRODUCTION_EFFECT` **在全文只声明一次**（即上方 ① 块内）。任何其它位置（含 `REQ-W1-03`）**只引用**该字段，**不得重复声明**同一事实。

**② 关闭证据字段（实现完成后产生，填充 ① 的槽位）**

```yaml
REAL_ENTRYPOINT                        # 实际真实入口
PRODUCTION_CALL_CHAIN                  # 实际调用链（真实路径）
OBSERVED_PRODUCTION_EFFECT             # 实际观测到的生产效果（对照 ① EXPECTED_PRODUCTION_EFFECT）
PRODUCTION_CALLERS                     # 实际生产调用者集合（可为空集；对照 ① EXPECTED_PRODUCTION_CALLER）
RUNTIME_REACHABLE                      # 观测结论：TRUE | FALSE（对照 ① REACHABILITY_REQUIREMENT）
EVIDENCE_REF                           # 证据引用
```

**`REACHABILITY_APPLICABILITY` 判定规则（INV-08 在 reachability 上的具体化；R1 冻结字段槽位）**：
- `REQUIRED` → `RUNTIME_REACHABLE` 必须由 ② 的关闭证据证明；无合法生产调用路径 → `RUNTIME_REACHABLE = FALSE` → `INTEGRATION_COMPLETE = FALSE`。
- `N/A` → **必须同时**填写 ① 的 **`REACHABILITY_APPLICABILITY_REASON`**（为什么该 seam 不涉及 reachability：如纯文档、无生产入口语义的变化）**和** **`REACHABILITY_APPLICABILITY_ACCEPTANCE_REF`**（指向适用 reviewer / integrator 的接受记录）。**worker 不得单方面自我豁免**（`INV-08`：N/A 必须来自合同适用性判定，不是 worker 快捷豁免）。任一槽位缺失或为空 → 视为 `REQUIRED` 处理。

字段**按边界是否变化触发，不按票字数或仅按 LOW 标签豁免**。**不要求所有票填写所有字段**；不适用字段可 `N/A`，但 **`N/A` 必须来自合同适用性判定并给出理由**（reachability 字段另需上述 `REASON` + `ACCEPTANCE_REF` 两个槽位），不得以 `UNKNOWN` 冒充已冻结。纯文档等无边界的票可整体 `N/A`（须有理由）。

**REQ-W1-02**（`EXTEND`，`references/execution-stage.md`）拆票前检查 —— **生命周期分离（F1 修正）**

**拆票前（PHASE 0 / 切片阶段）只做识别与定义，不执行 RED。** 拆票前必须输出并冻结：

```text
SEAM_IDENTIFICATION            # 识别被切开的 seam
CONTRACT_SOURCE                # 权威接口来源（或真实上游/下游形状来源）
PRODUCTION_SHAPE_SOURCE        # 生产形状来源（async/await、lifecycle、生产 caller 的判定依据）
COUNTEREXAMPLE_DEFINITION      # 反例定义（requirement，不是执行结果）
EXPECTED_RED_CONDITION         # 期望的 RED 条件（requirement："什么会失败"，不是"已失败"）
RED_EXECUTION_OWNER            # 票内执行 RED 的角色
REACHABILITY_APPLICABILITY     # REQUIRED | N/A（判定规则与配套槽位见 REQ-W1-01）
REACHABILITY_PROOF_OWNER       # 关闭时提供 reachability 证据的角色
```

**`REACHABILITY_APPLICABILITY = N/A` 时**，拆票阶段必须同时冻结 `REACHABILITY_APPLICABILITY_REASON` 与 `REACHABILITY_APPLICABILITY_ACCEPTANCE_REF`（槽位定义见 `REQ-W1-01`，此处不重复定义）。

**真实 RED 执行发生在 `TICKET_AUTHORIZATION` 之后**：即**票内、实现之前**（`AGENTS.md` §3 TICKET LANE 的 counterexample-first TDD 顺序，`references/ticket-lane.md` §4）。**REQ-W1-02 不要求、也不允许在拆票前执行 RED**——拆票前只有"期望 RED 条件"的声明。

拆票前**不要求**提前完成产品 E2E；但**不得用未验证假设声明集成已完成**。

**REQ-W1-03**（`EXTEND`）Integration 关闭增加 Runtime Reachability **关闭证据**字段（**只含 ② 类 observation 字段**；① 类 requirement 声明以 `REQ-W1-01` 为**唯一声明点**，此处**只引用、不重复声明**）：

```text
REAL_ENTRYPOINT / PRODUCTION_CALL_CHAIN
OBSERVED_PRODUCTION_EFFECT            # 观测值；与 ① EXPECTED_PRODUCTION_EFFECT 对照（引用，不重复声明）
PRODUCTION_CALLERS
RUNTIME_REACHABLE / EVIDENCE_REF
```

本清单**只引用** `REQ-W1-01` 的 ② 类 observation 槽位，**不重复声明**。canonical observation 槽位集恒为**六个**（`REAL_ENTRYPOINT`、`PRODUCTION_CALL_CHAIN`、`OBSERVED_PRODUCTION_EFFECT`、`PRODUCTION_CALLERS`、`RUNTIME_REACHABLE`、`EVIDENCE_REF`）；其**唯一声明点**是 `REQ-W1-01`，落地点为 `references/ticket-lane.md` §3.1 的分区 (1)/(2) 字段清单（其中 §3.1.1 / §3.1.2 由 `P1-T01` 落地于 `main`；本 Spec 分支的 `references/` 快照可能早于该落地）。`TEST_ONLY_CALLERS` **不是**第七个 canonical observation 槽位，**不得**被实现为第二个规范声明点；它只作为**派生 / 诊断证据**使用（用于展示"存在测试调用者、但不存在生产调用者"）。owner 裁定记录见 §16.9.1。

涉及 wiring / registration / composition / entrypoint 的票，必须证明**真实入口 → 变化 seam → 实际效果**。**测试直调内部模块不能单独满足此条件。** 动态注册 / 插件 / 回调允许以**合法运行证据**证明，**不以文本 grep 直接函数调用次数为最终裁决**。相关 Integration 票无合法生产调用路径 → `INTEGRATION_COMPLETE = FALSE`。

**`REACHABILITY_APPLICABILITY = N/A` 的票**：不经此证据路径关闭，但必须走 `REQ-W1-01` 的"理由 + reviewer/integrator 接受记录"双条件；缺任一条件按 `REQUIRED` 处理。

**REQ-W1-04**（`EXISTING`，重申不新增）
责任分离保持不变：worker / native harness 生产证据；L0 校验身份、结构、执行状态与引用；reviewer 判断合同覆盖与效果；integrator 核验实际集成结果后方可关闭。允许**真实 adapter + 确定性传输替身**（保生产协议/async/错误形状，不访问网络）；**不强制每票调用付费 API，不强制全员 live E2E**。

### 3.2 工作包 W2 — Review Evidence 最小机制

**REQ-W2-01**（`NEW`）
新增最小机器证据接口，**唯一证据接口详情落点**：

```text
references/review-evidence.md            # 唯一语义详情 / single source
schemas/review-evidence.schema.json      # versioned schema
templates/review-evidence.json           # 占位符形态模板（`RULES.md` R2 兼容）
scripts/review_evidence.py               # 薄 collect/validate CLI
```

**接口一致性要求（M3，必须可验收 —— 见 `AC-44`）**：

```text
1  四个必需 surface 均存在
2  references/review-evidence.md 是唯一语义详情 owner（single source）
3  schema 机械表达所需合同（REQ-W2-04 字段组）
4  template 符合 schema
5  CLI collect / validate 消费同一 schema / 合同
6  其它 canonical surface 只指针 / 链接，不定义竞争性 Review Evidence 接口
7  新增的 references/review-evidence.md **满足仓内全部既有 reference-file 不变量**，
   包括 `scripts/validate_governance.py` 要求的字面 `Canonical owner` 声明（A3）
```

**既有机械合同的采纳（A3，不是新机制）**：`scripts/validate_governance.py` **已存在**检查 #7 `references-declare-canonical-owner` —— 它对 `references/*.md` 做 glob，**每个文件必须包含字面标记 `Canonical owner`**：

```python
for ref in sorted((ROOT / "references").glob("*.md")):
    if "Canonical owner" not in ref.read_text(encoding="utf-8"):
        owner_missing.append(ref.name)
check("references-declare-canonical-owner", not owner_missing, f"missing={owner_missing}")
```

因此未来由本 requirement 创建的 `references/review-evidence.md` **MUST 满足该既有仓级不变量**，其中包含 **validator 所要求的 `Canonical owner` 声明**。**不得修改 validator 来豁免新文件**；这是**采纳既有仓内不变量**，**不是**新治理机制。

**边界约束**：不修改 `project-state` 的状态职责，不复制其全文，不建立第二状态源或第二 tracker。接口一致性由 `AC-44` 验收；**`review-evidence.md` 的单一 owner 地位与 `REQ-W4-02a` 的"只引用"要求同源**（区别于 recipe owner，不冲突）。

**REQ-W2-02**（`NEW`）Producer 职责

- 收集**可直接核验**的 repo / base / candidate / diff 等事实；接收原生测试/CI **结果与 artifact reference**。
- 记录**来源与未验证项**（`unverified` 字段）。
- **不替项目执行任意 build/test 命令**；**不读取或执行 evidence 文件提供的任意 shell 指令**（evidence 是数据，不是可执行权威）。
- **信任 / 取回边界**（见 `REQ-W2-04(d)`）：`commandRef` 只作声明与溯源，**不执行**；**不取回**用户/证据提供的任意 URL；`artifacts[].location` **不得**被当作任意网络或任意文件系统权威；取回仅限 repo 相对路径（含越界检查）与既有 CI provider 接口。

**REQ-W2-03**（`NEW`）Validator 职责 — **三层正交，不可坍缩（R2 修正）**

三条是**相互独立的评估轴**，各自取值，**不得互相折叠、不得共用一个枚举**：

```text
STRUCTURALLY_VALID        YES | NO
SOURCE_VERIFICATION_STATE VERIFIED | INVALID | TEMPORARILY_UNAVAILABLE | NOT_VERIFIED
EVIDENCE_SUFFICIENCY      SUFFICIENT | INSUFFICIENT
```

**轴语义边界（冻结，不得重新坍缩）**：

```text
STRUCTURALLY_VALID        schema 是否合法（含未知 schemaVersion、缺必需结果字段、形状不符）

SOURCE_VERIFICATION_STATE 来源/内容本身是否可信
  VERIFIED                  SHA/路径/摘要均已核验通过
  INVALID                   **只**表示来源/内容本身机械错误：
                              SHA mismatch / digest mismatch /
                              forged-or-invalid source identity / path violation
  TEMPORARILY_UNAVAILABLE   网络不可达 / provider 或 auth 不可用 / 远端 artifact 暂不可达
  NOT_VERIFIED              尚未完成核验（核验未执行或未完成）

EVIDENCE_SUFFICIENCY      证据是否足以支撑判断
  SUFFICIENT               足以支撑判断
  INSUFFICIENT             证据不足（如来源完全真实但缺少完成判断所需的某类证据）
```

**关键规则**：`INSUFFICIENT` **只属于 `EVIDENCE_SUFFICIENCY`**，**不得**作为 `SOURCE_VERIFICATION_STATE` 的取值。反例（必须成立且不得报错）：

```text
STRUCTURALLY_VALID        = YES
SOURCE_VERIFICATION_STATE = VERIFIED          ← 来源完全真实，已核验
EVIDENCE_SUFFICIENCY      = INSUFFICIENT      ← 但仍缺某类必要证据
```

**不得**因 schema 合法、字段写 `PASS`、或 `exitCode = 0` 就宣告行为通过。对以下情形给明确失败：未知 schemaVersion、缺必需结果字段、SHA 不符、产物丢失或内容摘要变化、路径越界读取（拒绝被污染的路径）。

**轴间处置规则（R2）**：

```text
SOURCE_VERIFICATION_STATE = VERIFIED              且 EVIDENCE_SUFFICIENCY = SUFFICIENT   → 可进入后续判断
SOURCE_VERIFICATION_STATE = INVALID                                                    → 阻断 PASS；须重新产出证据
SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE                                    → 阻断 PASS；保留原始 cause；
                                                                                          恢复可达后重核（**不得**判为 INVALID）
SOURCE_VERIFICATION_STATE = NOT_VERIFIED                                               → 阻断 PASS；须先完成核验
EVIDENCE_SUFFICIENCY      = INSUFFICIENT                                               → 阻断 PASS；须补足证据
任一轴为否/未决 → 阻断 PASS。
```

**网络/provider/auth/远端 artifact 不可达 MUST NOT 被自动宣告为 `INVALID`。** 该情形产出 `SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE`、`EVIDENCE_SUFFICIENCY = INSUFFICIENT`，**保留原始 cause 与诊断信息**，并且**阻断 PASS**。区分 `INVALID` 与 `TEMPORARILY_UNAVAILABLE` 是硬要求：前者要求重新产出证据，后者只要求恢复可达后重核。

**复用现有公开发布/隐私政策，不自建第二套 secret scanner**；**不把原始 runtime-local grounding receipt 全量发布**（machine-local 状态绝不 commit，见 `references/project-continuity-contract.md` §6.4）。

**REQ-W2-04**（`NEW`）最小字段组 —— **拆票前必须冻结的字段合同（F2 修正）**

```text
subject(repo/baseSha/candidateSha) / authorityRefs
producer(identity/version/observedAt)
checks(id/scope/commandRef/status/exitCode/artifactRefs)
artifacts(location/contentDigest)
ci(run/job/checkedSha/originalState)
grounding(mode/coverage/evidenceRef)
seams(applicability/evidenceRefs)
reuse(sourceEvidence/validFor/dependencies/invalidation)
unverified[]
```

字段按适用性扩展，**不给小票强加全量表格负担**。以下子合同必须在**拆票前**即可写票，不得留给实现票自行决定：

**(a) `checks[].status` —— 闭合最小集，且 `CHECK_STATUS != CI_STATUS`**

```text
CHECK_STATUS = PASS | FAIL | SKIPPED | ERROR | UNKNOWN      # 闭合集，机器检查自身结果
```

**必须显式声明：`CHECK_STATUS` 不是 `CI_STATUS`，两者不是同一个状态机。** CI 状态继续使用 `REQ-W3-04` 的既有七值集（`PASS / FAIL / NOT_TRIGGERED / CANCELLED / INFRASTRUCTURE_FAILURE / KNOWN_BASELINE_FAILURE / UNKNOWN`）；`checks[].status` 只描述**单条机械检查**的结果。**不得让 `CHECK_STATUS` 成为第二个竞争性 CI 状态机**（`INV-02` / `REQ-W3-04` / §6.3）。跨字段一致性：`ci.originalState` 的取值域 = 既有 `CI_STATUS` 集，**不引入新值**。

**(b) `artifacts[].location` —— 位置 ≠ 任意取回授权**

`location` 是**证据声明**，不是给机制任意网络/文件系统权限的凭据。取值受限：

```text
ALLOWED   repo 相对路径（受路径越界检查约束）
ALLOWED   CI artifact 标识（经既有 CI provider 接口取回）
FORBIDDEN 任意 URL / 任意绝对路径 / 指向仓外任意主机的位置
```

`location` 越界 → `REJECT`（等同路径越界读取）。

**(c) 来源核验与证据充分性 —— 两条独立轴，不得把"取不回"判成"证据无效"（R2 修正）**

```text
SOURCE_VERIFICATION_STATE = VERIFIED                # SHA/路径/摘要均核验通过
SOURCE_VERIFICATION_STATE = INVALID                 # 来源/内容本身机械错误：
                                                    #   SHA mismatch / digest mismatch /
                                                    #   forged-or-invalid source identity / path violation
SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE # 网络不可达 / provider 或 auth 不可用 / 远端 artifact 暂不可达
SOURCE_VERIFICATION_STATE = NOT_VERIFIED            # 核验尚未执行或未完成

EVIDENCE_SUFFICIENCY      = SUFFICIENT              # 证据足以支撑判断
EVIDENCE_SUFFICIENCY      = INSUFFICIENT            # 证据不足（来源可完全真实）
```

**`INSUFFICIENT` 不是 `SOURCE_VERIFICATION_STATE` 的取值**（这是 R2 修正的核心）。合法且必须接受的组合：

```text
SOURCE_VERIFICATION_STATE = VERIFIED
EVIDENCE_SUFFICIENCY      = INSUFFICIENT
```

**网络/provider/auth/远端 artifact 不可达 MUST NOT 被自动宣告为 `INVALID`。** 该情形产出 `SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE` + `EVIDENCE_SUFFICIENCY = INSUFFICIENT`，**保留原始 cause 与诊断信息**，并**阻断 PASS**（阻断 ≠ 把它误记为作废证据）。区分 `INVALID` 与 `TEMPORARILY_UNAVAILABLE` 是硬要求：前者要求重新产出证据，后者只要求恢复可达后重核。两条轴的完整处置规则见 `REQ-W2-03`。

**(d) `review_evidence.py` 的信任 / 取回边界（安全硬约束）**

```text
MUST NOT 执行 commandRef 指向的任何命令（commandRef 是声明与溯源，不是执行授权）
MUST NOT 取回用户/证据提供的任意 URL
MUST NOT 把 artifacts[].location 变成任意网络或任意文件系统权威
MUST      只从允许来源取回：repo 相对路径（含越界检查）、既有 CI provider 接口
```

证据是**数据**，不是可执行权威（与 `REQ-W2-02` 同源，此处上升为机制边界）。

**(e) `reuse` 依赖描述符 —— 最小规范形状**

```text
WHAT                依赖是什么（共享 schema / 共享依赖 / 入口拓扑 / toolchain / authority profile）
IDENTITY_VERSION_OR_DIGEST   依赖的身份：版本号或内容摘要（至少其一）
VALID_FOR           该证据在哪些范围内仍适用
INVALIDATED_BY      什么变化会使它失效（对应 REQ-W3-03 触发清单）
VERIFICATION_STATE  VERIFIED | UNKNOWN
```

**`VERIFICATION_STATE = UNKNOWN` → 不允许复用**（`REQ-W3-02` 的硬约束在此落实为字段级规则）。

**(f) `seams.applicability` / `unverified[]`**

- `seams.applicability = REQUIRED | N/A`，与 `REQ-W1-01` 的 `REACHABILITY_APPLICABILITY` 同构；`N/A` 需理由（+ 接受记录，见 `REQ-W1-01`）。
- `unverified[]` 空数组合法；**不得以省略代替**（省略 = 结构不合法 → `REJECT`；空数组 = 显式声明"无未验证项"）。

**(g) `ci.originalState`** 取值域 = 既有 `CI_STATUS`（见 (a)）；`checkedSha != subject.candidateSha` → 不得作为该候选的 CI 证据。

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

> W4 各 recipe 均为 **`EXTEND`**，逐条绑定**单一 canonical owner**（F3 修正）；`REQ-W4-03-D`（live host deny 映射）归 `DEPLOYMENT_ONLY` / W5。

**REQ-W4-01**（`EXTEND`）Bootstrap 字节预算修正 —— **预算合同必须在拆票前冻结（F5 修正）**

按 **UTF-8 字节**检查**实际部署正文**，对齐文档、候选与校验器**单位**。宿主容量是**观测/profile 信息**，**不是跨 runtime 常数**。

**冻结的预算合同（实现票不得自行决定）**：

```text
NAME     WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES
VALUE    3500
UNIT     UTF-8 编码字节数（byte），不是字符数（char）、不是 code point 数
OWNER    deployment/BOOTSTRAP_CONTRACT.md（正文语义 owner）；scripts/validate_governance.py 消费该值
SOURCE   WorkBuddy profile 安全预算（观察值/profile 属性，见下方 profile 分层）
SCOPE    本 profile 内有效；**不是跨 runtime 通用不变量**
```

**必须区分的两个量（不得混为一谈）**：

```text
3500   = 当前 WorkBuddy profile 的安全预算（本 Spec 冻结的 BUDGET 值）
4028   = 历史观测到的实际截断点（byte；BOOTSTRAP_CONTRACT §1 观测事实）
```

`3500` 与 `4028` **不是同一个东西**：前者是**主动留出余量的规范预算**，后者是**被动观测到的硬截断边界**。预算取 3500 是为避免贴近 4028 观测边界，**不是**把 4028 当成预算。

**OVERRIDE / PROFILE 语义**：

```text
- 3500 是**本 profile（WorkBuddy）**的预算，不是跨 runtime 的普适常数。
- 未来 runtime 若存在**自身已核验的 profile**（含其自有的 cutover 观测），可使用其自有预算值。
- 使用非默认 profile 预算时，必须显式记录 OVERRIDE（值 + 来源 + 观测依据），
  静默替换预算值 = 违规（对齐 §4.2 的 OVERRIDE 纪律）。
- 无已核验 profile 时，默认回落到 3500（本 profile 值）并标注来源。
```

**校验器语义必须是 UTF-8 编码字节长度**，即对实际部署正文取 `len(body.encode("utf-8"))`，**不得**使用 `len(body)`（字符数）。当前实现为 `len(body) <= 3500`（字符），是本 Spec 要修正的缺陷（GAP-06 / §8.1）。

**完整 canonical change surface（F-A1 修正 —— 不得遗漏宿主面；F-B1 扩为五 surface）**

本 Spec 冻结了 `UNIT = UTF-8 bytes`，因此未来 S1 实现若**只改**此前枚举的三个文件，会留下 `AGENTS.md → characters` 与 `canonical contract / validator → UTF-8 bytes` 的**残留冲突**——这正是本 Spec `INV-22`（`ROW_PRESENT != BEHAVIOR_ACCEPTED`，含 incomplete change surface）所禁止的同类问题。

**因此未来 S1 change surface 必须完整覆盖以下五个 surface（`AGENTS.md` 由 F-A1 纳入；`README.md` 由 F-B1 纳入）**：

```text
1  AGENTS.md §10 BOOTSTRAP                     ← F-A1 纳入（此前遗漏）
2  deployment/BOOTSTRAP_CONTRACT.md            （语义 owner）
3  deployment/MEMORY_POINTER_CANDIDATE.md
4  scripts/validate_governance.py              （消费方）
5  README.md（§7.4 bootstrap 三件套 + 仓库树注记） ← F-B1 新增纳入（此前未审计）
```

**`README.md` 的未来目标语义（F-B1 冻结）**：`README.md` 是 **bootstrap-facing 的派生消费者 / 运行时文档**，**不是**第二预算 authority。它只可把预算表述为 **`≤ 3500 UTF-8 bytes`**，或等价的「指向 `deployment/BOOTSTRAP_CONTRACT.md` §2.1 语义 owner」措辞；**不得**保留「≤3,500 字符」式的字符预算语义，也**不得**自行声明预算值、单位或 profile 语义。

**`AGENTS.md` §10 的未来目标语义（冻结，二选一，优先 A）**：

```text
A（优先）pointer / derived-summary 模式：
  AGENTS.md §10 不再自行声明字符数预算；
  改为引用由 deployment/BOOTSTRAP_CONTRACT.md 拥有的 canonical WorkBuddy byte budget。

B（次选）显式 derived summary：
  若必须在 AGENTS.md 内给出摘要，则明确写成 "≤ 3500 UTF-8 bytes"，
  且 deployment/BOOTSTRAP_CONTRACT.md 仍为语义 owner。
```

**硬约束**：**`AGENTS.md` 不得成为第二预算 authority**。无论 A 或 B，**语义 owner 始终是 `deployment/BOOTSTRAP_CONTRACT.md`**；`AGENTS.md` 只能是 pointer 或显式 derived summary。优先 adopt **A**。

**BOOTSTRAP_CONTRACT 措辞对齐（A2 修正）**

当前 canonical 文本仍含等价于 "≤3,500 字符" 与 "预算 4,028 减安全余量" 的措辞，与本 Spec 已冻结的区分冲突。**未来 S1 实现必须把 canonical 措辞对齐为下述目标语义**：

```text
3500 bytes  = 当前 WorkBuddy profile 安全预算（BUDGET；由 BOOTSTRAP_CONTRACT 拥有）
4028 bytes  = 历史观测到的实际截断点（TRUNCATION；观测事实）

3500 **不是**在数学上或规范上被定义为 "4028 减去某个隐含安全余量"。
两者是不同性质的量：前者是主动规范预算，后者是被动观测边界。
```

**不新增机制、不新增 profile 系统**；A2 仅为 **canonical 措辞同步**（把已批准的区分落到正文措辞）。

**授权边界（F5 措辞修正）**：

- 本轮为 **Spec 写作**，`IMPLEMENTATION_AUTHORIZED = NO`（见文件头）。**本 Spec 不授权任何实现动作。**
- 本 Spec 将上述**静态修正**（校验器单位 + 文档措辞对齐 + `AGENTS.md` 宿主面纳入）纳入**未来 S1 core scope**；**只有 `SPEC_REVIEW = PASS` 且 owner 明确授权后方可实施**（见 §12）。
- **本轮不修改** `AGENTS.md` / `deployment/BOOTSTRAP_CONTRACT.md` / `deployment/MEMORY_POINTER_CANDIDATE.md` / `scripts/validate_governance.py` / `README.md` / `references/*`；它们是被纳入 Spec 的**未来实现面**，不是本轮改动对象。
- **未来真实部署**（live bootstrap 落地）与静态修正分开处理，属 `DEPLOYMENT_ONLY` / S3（见 `REQ-W5-01`）。
- 迁移与兼容见 §8.1。

**REQ-W4-02a**（`EXTEND`，`references/review-and-repair-saturation.md`）Audit visibility recipe

**单一 owner：`references/review-and-repair-saturation.md`**（该文件已是评审分级/收敛的 canonical owner；`references/review-evidence.md` 对该 recipe **只引用，不重复定义**）。二选一必须择一，**不得两处并存**。

按需（非全票强制）字段：`evidence / requested SHA / actually read scope / SEEN|PARTIAL|NOT_SEEN|UNCERTAIN / supports / missing / verdict impact / recovery artifact`，并分别输出 `CONTEXT_COMPLETENESS_FOR_DECISION_AUDIT` 与 `FULL_HISTORICAL_TRANSCRIPT_COMPLETENESS`。**外审 primary 不可见时必须限定结论，不得伪称完整**（8/27 Perplexity 报告 MORE_EVIDENCE_REQUIRED 为正例）。受 `AC-13` / `CE-15` 验收。

**REQ-W4-02b**（`EXTEND`，`references/git-ci-integration.md`）Destructive workspace transaction safety

**单一 owner：`references/git-ci-integration.md`**（workspace/CI 集成面本就承载破坏性操作的 scope 与证据纪律）。

`status → 未提交/未追踪/owner → 保全 → 操作 → post-state`；基线优先独立干净 worktree；禁止动其它 lane 工作；仅对破坏性动作触发。**不建立全局 stash 禁令**（底层因果 `NEEDS_PRIMARY_EVIDENCE_RECOVERY`，见 §4.3）。受 `AC-14` / `CE-16` 验收。

**REQ-W4-02c**（`EXTEND`，`references/ticket-lane.md`）Shared-file single-writer + readback

**单一 owner：`references/ticket-lane.md`**（择一并与 `WRITE OWNERSHIP` 对齐；`references/execution-stage.md` 对该条**只引用，不重复定义**）。选择理由：单票 lane 契约已定义 lane 内写权与 lane 边界（§1/§2），共享文件的 single-writer 与最终回读属 lane 内写权纪律的自然延伸。

同一共享文件聚合成一次/串行修改，**最终回读核验所有预期条目**（不得以编辑工具成功代替内容核验）。受 `AC-15` / `CE-17` 验收。

**REQ-W4-02d**（`EXTEND`，`references/engineering-memory.md`）Learning closure

**单一 owner：`references/engineering-memory.md`**（learning 条目生命周期本就归其管辖）。

关闭必须有**采纳/拒绝理由 + 验证引用**；不得仅标"bug fixed"。受 `AC-16` / `CE-18` 验收。

**REQ-W4-02e**（`EXTEND`，`references/skills-and-model-routing.md`）Model dispatch metadata

**单一 owner：`references/skills-and-model-routing.md`**（模型派发与技能路由的既有 owner）。

`ROLE / TASK / RISK / MODEL_OR_TIER / REASONING_EFFORT / WHY / EXPECTED_OUTPUT / ESCALATE_IF`。风险先于型号；**型号放可更新 profile，不写死不变量**。受 `AC-19` 验收（见 §10.2）。

**注**：上述五条中，**无一条属于 `NEW` 子系统** —— 每条都有既有 canonical 文件作为单一 owner，故分类为 `EXTEND`（新增字段/条件/验收），不新建第二权威体系（`INV-07`）。

**REQ-W4-03**（`EXTEND`）Guard 退出码合同 + runtime deny 映射合同（**S1 core 部分**）

`grounding_guard.py` 的**合同语义**（core，可在 S1 定义与单测）：

```text
exit 0  → ALLOW（放行）
exit 2  → REQUEST_BLOCK（请求宿主阻断该动作）
```

**若 runtime 未把 `exit 2` 映射为 deny，则该 hook 退化为 advisory（仅建议，不阻断）。**

本 Spec 在本条定义的**core 合同**为：**任何声称提供 `ENFORCED` 阻断的 runtime adapter，必须暴露一个可核验的 deny 映射合同**，并具备**合成/reference 级测试**（不依赖真实宿主）。即：adapter 不得在未定义 deny 映射的情况下宣称 `ENFORCED`；无法提供映射时必须**降级声明为 `ADVISORY`** 并如实记录（`fail-closed`：不得静默宣称阻断有效）。

**不属于 S1 的部分（见下）**：**真实宿主行为**（真实工具事件 → hook 发出 block → 宿主实际映射为 deny → **目标文件未被修改**）**不在 S1 core 范围**，属 `REQ-W4-03-D`。

**REQ-W4-03-D**（`DEPLOYMENT_ONLY`）Live host deny mapping 实测

真实宿主的 deny 映射端到端验证：**真实工具事件 → hook 发出 block → 宿主将该 block 映射为 deny → 目标文件保持未被修改**。本项属 **W5 / `DEPLOYMENT_ONLY` / `LIVE_ADOPTION`**（见 `REQ-W5-01`）；**本轮与 S1 均不实施**，也不以"脚本打印 BLOCK"冒充该验证。受 `AC-18`（S1 合同面）+ `AC-18-D`（W5 live 面）双段验收（见 §10.2）。

**REQ-W4-04**（`EXTEND`）Gate 入口自测

会授权继续执行的脚本必须验证：`argv → main`、退出码、结构化输出与**实际副作用/探针**。**模块 import 不冒充 CLI**；`exit 0 + 空输出` 不得满足门禁。

### 3.5 工作包 W5 — Live Adoption + Server Enforcement（`DEPLOYMENT_ONLY`）

**REQ-W5-01**（`DEPLOYMENT_ONLY`）Bootstrap live adoption 验收（复合，**R3 补齐行为面**）

未来 deployment acceptance **至少**覆盖（不只是 host deny）：

```text
1  fresh neutral session        → governance authority loaded（authority 正确加载）
2  project session              → repository authority discovered（仓级权威被发现）
3  override                     → correct resolution（覆盖被正确解析，符合 §4.2 层级）
4  existing project             → state restore works（既有项目状态可恢复）
5  authorized legal frontier    → auto-advance according to canonical rule（按 canonical 规则自动前进）
6  advisory / NOT_RUN           → **never** reported as ENFORCED / PASS（如实记录降级）
7  real host deny               → target unchanged（真实工具事件 → hook → runtime deny → 目标未被修改；
                                   对应 REQ-W4-03-D）
```

第 7 项即原 host deny 面；**前 6 项为 R3 补齐的行为面，此前缺失**。失败与 advisory 降级**如实记录**（`NOT_RUN` ≠ PASS；advisory 降级不得记作 ENFORCED）。受 `AC-40` 复合验收。

**REQ-W5-02**（`DEPLOYMENT_ONLY`）GitHub enforcement（**R3 赋予自有验收**）

GitHub enforcement 是**仓库部署政策**，不是所有项目通用硬规则。本 Spec 只**定义未来验收与所需权限**；**不在本阶段配置 required checks / rulesets / bypass**；**不得通过向真实未保护 main 试推来验证缺口**。

未来验收（`AC-41`）：

```text
authorized repository settings / API evidence
  → expected required checks / ruleset / bypass policy observed

permission unavailable
  → NOT_VERIFIED
  → **not PASS**

must not require destructive direct-push probe
```

**此项不得再映射到 host deny 的 `AC-18-D`**（R3 纠正的语义错配）。

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
INV-11  seam 合同的设计/权威字段（①）与关闭证据字段（②）分离；同一事实不得有两个权威来源（F1）
INV-12  拆票前只做识别与定义（含"期望 RED 条件"）；RED 执行属票内、实现之前（F1）
INV-13  CHECK_STATUS != CI_STATUS；两者不得坍缩为同一状态机（F2）
INV-14  来源暂不可达（网络/provider/auth/远端 artifact）!= 证据无效；前者须保留 cause 且阻断 PASS（F2）
INV-15  证据是数据不是执行权威：不执行 commandRef、不取回任意 URL、location 非任意取回凭据（F2）
INV-16  每条 scoped recipe 必须有且仅有一个 canonical owner（F3）
INV-17  live 宿主行为（真实 deny 映射等）与 core 合同分离；后者可在 S1，前者属 DEPLOYMENT_ONLY / W5（F4）
INV-18  预算值（BUDGET）与观测截断点（TRUNCATION）不是同一个量；预算不得由截断点反推（F5）
INV-19  ① 类字段名必须表达 requirement、② 类字段 name 必须表达 observation；
        二者不得同名或近似到需 implementer 猜测（R1）
INV-20  每个规范事实只有一个声明点；其余位置只引用不重复声明
        （`EXPECTED_PRODUCTION_EFFECT` 为具体适用例）（R1）
INV-21  结构 / 来源 / 充分性为三条独立评估轴，取值互不折叠；
        `INSUFFICIENT` 只属充分性轴，不得作为来源轴取值（R2）
INV-22  验收矩阵行存在（ROW_PRESENT）!= 行为被验收（BEHAVIOR_ACCEPTED）；
        每条 requirement 必须绑到语义相关的 AC，不得以无关 AC 充数（R3）
```

**INV 与修复轮次对应**：

```text
INV-11/12 ← F1        INV-13/14/15 ← F2        INV-16 ← F3
INV-17 ← F4           INV-18 ← F5              INV-19/20 ← R1
INV-21 ← R2           INV-22 ← R3
F6 为可追溯性补全（无新增不变量）；R4 为引用同步（无新增不变量）。
M1–M3 为验收补全与 prose 消歧（无新增不变量）：
  M1 为 INV-19/INV-20 补行为验收 → AC-43
  M2 消解 TEMPORARILY_UNAVAILABLE 的 prose 冲突 → 不变量文本不变，语义收敛
  M3 为 REQ-W2-01 补接口一致性验收 → AC-44
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
| Audit visibility recipe | `references/review-and-repair-saturation.md`（**单一 owner**；`review-evidence.md` 只引用） | `EXTEND`（`REQ-W4-02a`） |
| Destructive workspace transaction safety | `references/git-ci-integration.md`（**单一 owner**） | `EXTEND`（`REQ-W4-02b`） |
| Shared-file single-writer + readback | `references/ticket-lane.md`（**单一 owner**，与 WRITE OWNERSHIP 对齐；`execution-stage.md` 只引用） | `EXTEND`（`REQ-W4-02c`） |
| Learning closure | `references/engineering-memory.md`（**单一 owner**） | `EXTEND`（`REQ-W4-02d`） |
| Model dispatch metadata | `references/skills-and-model-routing.md`（**单一 owner**） | `EXTEND`（`REQ-W4-02e`） |
| Guard 退出码 / deny 映射合同（core） | `adapters/zcode/hooks/grounding_guard.py` + adapter 合同 | `EXTEND`（`REQ-W4-03`，S1） |
| Live host deny 映射实测 | 真实宿主运行环境 | `DEPLOYMENT_ONLY`（`REQ-W4-03-D`，W5） |
| 状态索引 / grounding 生命周期 | `references/project-continuity-contract.md`（canonical owner = AGENTS §7.1） | `EXISTING` |
| Bootstrap 机制 | `deployment/BOOTSTRAP_CONTRACT.md`（预算语义 owner）；**`AGENTS.md` §10 与 `README.md` 为 pointer/derived-summary 消费者，非第二 authority（F-A1 / F-B1）** | `EXTEND`（单位对齐 + 完整 change surface） |
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
| `checks[].id/scope/commandRef/status/exitCode/artifactRefs` | 机械检查事实；`status ∈ CHECK_STATUS`（闭合集，**≠ `CI_STATUS`**，见 `REQ-W2-04(a)`） | `status=PASS` 但 `artifactRefs` 不可取回 → 拒绝 |
| `artifacts[].location/contentDigest` | 产物位置与内容摘要；`location` 受限于 repo 相对路径 / CI artifact 标识，**不是任意取回授权**（`REQ-W2-04(b)`） | 摘要变化 → `EVIDENCE_ARTIFACT_CHANGED`；位置越界 → `REJECT` |
| `ci.run/job/checkedSha/originalState` | CI 事实；`originalState ∈ CI_STATUS`（既有七值集，不新增） | `checkedSha != subject.candidateSha` → 不得作为该候选 CI 证据 |
| `grounding.mode/coverage/evidenceRef` | 接地模式与覆盖 | 与 `codegraph-grounding.md` §2.1 命名不一致 → 拒绝 |
| `seams.applicability/evidenceRefs` | Seam 适用性与证据 | `applicability = N/A` 无理由（或缺接受记录）→ 拒绝 |
| `reuse.sourceEvidence/validFor/dependencies/invalidation` | 复用声明；`dependencies` 按 `REQ-W2-04(e)` 最小形状 | `dependencies` 形状不合法或 `VERIFICATION_STATE = UNKNOWN` 且声明复用 → 拒绝 |
| `unverified[]` | 显式未验证项 | 空数组合法；**不得以省略代替**（省略 = 结构不合法） |
| 结构合法性轴 | `STRUCTURALLY_VALID = YES | NO`（见 `REQ-W2-03`） | `NO` → `REJECT`（不进入消费） |
| 来源核验轴 | `SOURCE_VERIFICATION_STATE = VERIFIED | INVALID | TEMPORARILY_UNAVAILABLE | NOT_VERIFIED`（见 `REQ-W2-04(c)`） | `INVALID` → 阻断 PASS 且须重新产出证据；`TEMPORARILY_UNAVAILABLE` **不得**记为 `INVALID`（来源未作废），保留 cause、阻断 PASS、恢复后重核，且在**当前候选判定**上对应 `EVIDENCE_SUFFICIENCY = INSUFFICIENT`（M2）；`NOT_VERIFIED` → 阻断 PASS |
| 证据充分性轴 | `EVIDENCE_SUFFICIENCY = SUFFICIENT | INSUFFICIENT`（**独立于来源轴**；见 `REQ-W2-03`） | `INSUFFICIENT` → 阻断 PASS。合法组合含 `SOURCE_VERIFICATION_STATE = VERIFIED` + `EVIDENCE_SUFFICIENCY = INSUFFICIENT`，以及 `SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE` + `EVIDENCE_SUFFICIENCY = INSUFFICIENT` |

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

### 6.1 三类失败必须可分（R2 修正：与三轴正交对齐；M2 修正：语义冻结）

```text
REJECT                结构/来源/必填不合法 → 不进入消费
                      （STRUCTURALLY_VALID = NO，或 SOURCE_VERIFICATION_STATE = INVALID）
INSUFFICIENT          结构合法、来源可核验但证据不足 → 不得当作 PASS
                      （EVIDENCE_SUFFICIENCY = INSUFFICIENT；
                       含 SOURCE_VERIFICATION_STATE = VERIFIED 但缺必要证据的合法组合，
                       也含 SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE 的情形，
                       见下方冻结语义）
CONSUMER_UNSATISFIED  证据合法且充分但 consumer 门未满足（如空跑 exit 0、无有效结果）→ gate 不开
```

**`TEMPORARILY_UNAVAILABLE` 的冻结语义（M2：两类歧义表述在此收敛为一套）**：

```text
SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE

means:
  source is NOT declared invalid;
  verification cannot currently complete;
  original cause is preserved.

For CURRENT candidate acceptance:
  EVIDENCE_SUFFICIENCY = INSUFFICIENT
  until required source verification can complete;
  PASS is blocked meanwhile.

This does NOT mean the underlying artifact is invalid.
```

**核心区分（不得再混用）**：

```text
source validity          !=  current evidence sufficiency
（来源是否作废，属 SOURCE_VERIFICATION_STATE 轴）
（当前候选的证据是否足以放行，属 EVIDENCE_SUFFICIENCY 轴）
```

要点：`TEMPORARILY_UNAVAILABLE` **不是来源轴上的 `INVALID`**（来源未作废、不需重新产出），但**在当前候选判定上**它确实使 `EVIDENCE_SUFFICIENCY = INSUFFICIENT`（核验尚不能完成，故证据不足以放行），且**阻断 PASS**。两句分属**不同两条轴**，不构成冲突。

**`TEMPORARILY_UNAVAILABLE` 与 `REJECT` 的关系**：它**不是** `REJECT`（证据未作废、不重产）；它是**阻断 PASS 的独立来源态**：**保留 cause**、**恢复可达后重核**、**不得**折叠进 `INVALID`。**不新增第四条来源轴，也不新增其它架构概念。**

### 6.2 关键失败映射（逐条对齐旧事故）

| 旧事故 | 新机制的失败语义 |
|---|---|
| D6 async seam | `checks` 中 producer 形状与 consumer 期望不一致 → `SEAM_SHAPE_MISMATCH`；`pending` 期间写完成态 → 非法状态，red |
| T15 reachability | `PRODUCTION_CALLERS = []` 且票声明接线（`REACHABILITY_APPLICABILITY = REQUIRED`）→ `INTEGRATION_COMPLETE = FALSE`（不得绿） |
| D5 empty-run | `exitCode = 0` 但无有效结构化结果 → `CONSUMER_UNSATISFIED` |
| 陈旧产物复用 | `contentDigest` 变化或 `reuse.dependencies` 的 `VERIFICATION_STATE = UNKNOWN` → 拒绝复用 |
| 错 SHA | `subject.candidateSha` 不符 → `EVIDENCE_STALE_SUBJECT` |
| CE-20 guard 假阻断 | S1：adapter 无 deny 映射合同却声明 ENFORCED → 合同违规；W5：真实宿主未映射 deny 而目标被修改 → live 验收失败 |

### 6.2a 状态机分离（F2 修正；R2 修正：三轴正交）

```text
STRUCTURALLY_VALID（结构轴，闭合集）
  YES | NO
SOURCE_VERIFICATION_STATE（来源轴，闭合集）
  VERIFIED | INVALID | TEMPORARILY_UNAVAILABLE | NOT_VERIFIED
EVIDENCE_SUFFICIENCY（充分性轴，闭合集，独立于来源轴）
  SUFFICIENT | INSUFFICIENT
CHECK_STATUS（单条机械检查结果，闭合集）
  PASS | FAIL | SKIPPED | ERROR | UNKNOWN
CI_STATUS（CI 运行整体状态，既有七值集，不新增）
  PASS | FAIL | NOT_TRIGGERED | CANCELLED | INFRASTRUCTURE_FAILURE | KNOWN_BASELINE_FAILURE | UNKNOWN
```

**五个状态机互不坍缩**：

```text
- CHECK_STATUS 不得升格为 CI_STATUS
  （它们描述不同粒度：单条检查 vs CI 运行整体）
- STRUCTURALLY_VALID 不得替代 SOURCE_VERIFICATION_STATE
  （schema 合法 ≠ 来源可信）
- SOURCE_VERIFICATION_STATE 不得吸收 EVIDENCE_SUFFICIENCY
  （INSUFFICIENT 不是来源轴的取值；来源可为 VERIFIED 而证据仍 INSUFFICIENT）
- TEMPORARILY_UNAVAILABLE 不得折叠为 INVALID
  （暂不可达 ≠ 证据作废）
- TEMPORARILY_UNAVAILABLE 在**当前候选判定**上对应
  EVIDENCE_SUFFICIENCY = INSUFFICIENT（核验尚不能完成）
  —— 二者属**不同轴**，故不矛盾（M2）
- 任一轴为否/未决 → 阻断 PASS；不得以任一轴的成功代替其它轴
```

**不得建立本 Spec 五轴之外的第六套概念**（R2 边界约束）。

### 6.3 不得生成的失败语义

不新增替换既有 CI 状态机的新枚举；不把 `UNKNOWN` 折叠为任一终态；不支持"重试直到碰巧成功"。

---

## 7. INTEGRATION_POINTS

| 集成点 | 现有文件 | 变更性质 |
|---|---|---|
| 单票生命周期 / Seam 合同 | `references/ticket-lane.md` §3 | `EXTEND` 生产形状字段组（设计①/证据②分离，`REQ-W1-01`）+ single-writer recipe（`REQ-W4-02c`） |
| 拆票前检查 | `references/execution-stage.md` §6 | `EXTEND` 引用 Seam 合同；**拆票前不执行 RED**（`REQ-W1-02`） |
| Integration 关闭条件 | `references/git-ci-integration.md` §4/§5 + AGENTS §6 | `EXTEND` reachability 关闭证据（`REQ-W1-03`）+ destructive transaction safety（`REQ-W4-02b`） |
| Review 分级与消费 | `references/review-and-repair-saturation.md` §1/§4 | `EXTEND` 引用 evidence 接口 + audit visibility recipe 单一 owner（`REQ-W4-02a`） |
| Evidence 接口 | **新增** `references/review-evidence.md` | `NEW`（对 `REQ-W4-02a` 只引用，不重复定义） |
| Evidence 机械形态 | **新增** `schemas/review-evidence.schema.json`、`templates/review-evidence.json`、`scripts/review_evidence.py` | `NEW`（含 `REQ-W2-04` 字段合同与信任边界） |
| Learning 条目生命周期 | `references/engineering-memory.md` | `EXTEND` learning closure 单一 owner（`REQ-W4-02d`） |
| 模型派发 / 技能路由 | `references/skills-and-model-routing.md` | `EXTEND` model dispatch metadata 单一 owner（`REQ-W4-02e`） |
| Guard 退出码 / deny 映射合同 | `adapters/zcode/hooks/grounding_guard.py` + `adapters/zcode/README.md` | `EXTEND` core 合同 + 合成/reference 测试（`REQ-W4-03`，S1） |
| 状态索引契约 | `references/project-continuity-contract.md` | `EXISTING`（不修改语义，只被引用） |
| Bootstrap 预算 | **`AGENTS.md` §10**（F-A1 新增纳入）+ `deployment/BOOTSTRAP_CONTRACT.md` §2.1（语义 owner）+ `deployment/MEMORY_POINTER_CANDIDATE.md` + `scripts/validate_governance.py`（`memory-pointer-within-budget` 检查）+ **`README.md`**（F-B1 新增纳入；§7.4 bootstrap 三件套的派生消费者，非第二 authority） | `EXTEND` 单位对齐 + 预算值冻结 + 措辞对齐 + **完整 change surface（五 surface，不得只改校验器）** |
| 公开发布扫描 | `scripts/validate_public_release.py` | `EXISTING`（复用，不改判定） |
| CI 接入 | `.github/workflows/governance-ci.yml` | `EXTEND`（新增 evidence CLI 自测步骤；不新建 runner） |
| GitHub 保护 | repo settings | `DEPLOYMENT_ONLY` |
| Live host deny 映射 | 真实宿主运行环境 | `DEPLOYMENT_ONLY`（`REQ-W4-03-D`，W5） |
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
MIG-01  校验器按 UTF-8 字节检查指针正文（len(body.encode("utf-8"))，不是 len(body)）
MIG-02  文档、候选、校验器三方单位一致（全部 byte）
MIG-03  文档措辞不得把宿主容量写成跨 runtime 常数
MIG-04  当前正文（1804 byte）在新条件下保持 PASS（无回归）
MIG-05  预算阈值来源必须显式标注为观测/profile，不是规范常数
MIG-06  BUDGET 值冻结为 WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES = 3500（见 REQ-W4-01），
        实现票不得自行选定；profile override 须显式记录（值+来源+观测依据）
MIG-07  完整 change surface 覆盖五个 surface（F-A1 的四个 + F-B1 新增 `README.md`）：
         AGENTS.md §10 / deployment/BOOTSTRAP_CONTRACT.md /
         deployment/MEMORY_POINTER_CANDIDATE.md / scripts/validate_governance.py /
         README.md（§7.4 bootstrap 三件套 + 仓库树注记；派生消费者，非第二 authority）
        任一面保留 "3500 字符" 作为有效预算语义 = 未完成
MIG-08  AGENTS.md §10 改为 pointer（优先）或显式 derived summary "≤ 3500 UTF-8 bytes"；
        语义 owner 仍为 deployment/BOOTSTRAP_CONTRACT.md，
        AGENTS.md 不得成为第二预算 authority（A1）
MIG-09  canonical 措辞对齐（A2）：去除 "≤3,500 字符" 与 "预算 4,028 减安全余量" 式表述，
        明确 3500 bytes = WorkBuddy profile 安全预算、4028 bytes = 历史观测截断点，
        且 3500 不被定义为 "4028 减去隐含安全余量"
```

**新增 canonical surface 的实测证据（F-A1，本轮候选核验）**：

```text
AGENTS.md:138                      含 "≤3,500 字符"                          ← F-A1 残留冲突（此前未纳入 change surface）
BOOTSTRAP_CONTRACT.md:25           含 "≤3,500 字符（预算 4,028 减安全余量）"    ← A2 措辞冲突
BOOTSTRAP_CONTRACT.md:46           含 "指针预算（≤3,500 字符）"                ← A2 措辞冲突
MEMORY_POINTER_CANDIDATE.md:5      含 "全文 ≤3,500 字符"                      ← 单位冲突
scripts/validate_governance.py     当前用 len(body) <= 3500（字符）           ← 单位冲突
```

即：**若 S1 只改此前枚举的三个文件，`AGENTS.md` 会留下字符预算语义**，与冻结的 UTF-8 byte 语义形成残留冲突（`INV-22` 同类：incomplete change surface）。

**预算值 vs 截断点的显式区分（F5；A2 措辞目标）**：

```text
WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES = 3500   # 规范预算（主动留余量），本 profile
DOC_CLAIMED_TRUNCATION                = 4028   # 观测到的实际截断点（被动边界）
两者不是同一个量；预算 ≠ 截断点；预算不得被反推为"4028 是预算"。
3500 **不是**在数学上或规范上被定义为 "4028 减去某个隐含安全余量"。
```

**兼容性**：当前正文两条件均 PASS，故本修正**不产生 breaking change**；修正后用户若未来写入更多 CJK 文本，将在真正超限时被拒绝而非静默截断。

### 8.2 分阶段实施（未来分解边界，**不创建 implementation tickets**）

建议五个工作包，仅作分解边界参考；实际票据分解须在 Spec 获独立审查 PASS 后另行授权。

| 包 | 内容 | 依赖 | 写权冲突 |
|---|---|---|---|
| W1 | Seam + Reachability（`EXTEND` ticket-lane / execution-stage / git-ci-integration） | 无 | 与 W2 共享 `references/` 但文件不同；与 W4 共触 `ticket-lane.md` / `git-ci-integration.md`（**须串行或单写者**，见 `REQ-W4-02c`） |
| W2 | Evidence producer/schema/validator + CLI self-tests | 无 | 新增文件，低冲突 |
| W3 | Review/Stage/CI consumption + reuse/invalidation | **依赖 W1 + W2** | 引用 W1/W2 产物 |
| W4 | Scoped recipes（`REQ-W4-02a`..`02e`，分属 5 个既有 reference）+ byte budget + guard core 合同 | 无（byte budget 独立） | 触 `validate_governance.py`、`ticket-lane.md`、`git-ci-integration.md`、`review-and-repair-saturation.md`、`engineering-memory.md`、`skills-and-model-routing.md`、`grounding_guard.py` |
| W5 | Live adoption + server enforcement + live host deny 映射 | **依赖 W1–W4 核心合并** | `DEPLOYMENT_ONLY`，需单独授权 |

**硬约束**：**W2 未接入 W3，不得称机制完成。** 不为凑数拆票。**W1 与 W4 对 `ticket-lane.md` / `git-ci-integration.md` 有共享写面 → 必须遵循 single-writer + 最终回读**（`REQ-W4-02c`）。

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
CE-21  拆票阶段就被要求执行 RED（或拆票前把"期望 RED 条件"当作已执行结果）→ 必须按生命周期分离拒绝
CE-22  `REACHABILITY_APPLICABILITY = N/A` 仅由 worker 自填、无理由或无 reviewer/integrator 接受记录 → 必须按 REQUIRED 处理
CE-23  证据来源因网络/provider/auth/远端产物暂不可达 → 被错判为 `INVALID`（证据作废）→ 必须改判 `SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE`（并据 M2 对应 `EVIDENCE_SUFFICIENCY = INSUFFICIENT`）且仍阻断 PASS
CE-24  `checks[].status` 被当作 CI 状态机使用（第二竞争状态机）→ 必须拒绝
CE-25  `artifacts[].location` 被当作任意 URL / 任意路径的取回授权，或 `commandRef` 被实际执行 → 必须拒绝（信任边界违规）
CE-26  `reuse.dependencies` 为自由文本或 `VERIFICATION_STATE = UNKNOWN` 仍声明复用 → 必须拒绝
CE-27  声称 ENFORCED 的 adapter 无 deny 映射合同（S1）；或无映射却降级后仍记为 ENFORCED → 必须拒绝
CE-28  同一 recipe 在两个 canonical 文件重复定义（双 owner）→ 必须拒绝并收敛为单一 owner
CE-29  设计字段与关闭证据字段同名/近似名（需求与观测同形）→ 必须拒绝并要求按 INV-19 冻结命名
CE-30  同一规范事实（如 `EXPECTED_PRODUCTION_EFFECT`）在两处重复声明 → 必须拒绝，收敛为唯一声明点 + 引用
CE-31  把 `EVIDENCE_SUFFICIENCY = INSUFFICIENT` 写入 `SOURCE_VERIFICATION_STATE` → 必须拒绝（轴坍缩）
CE-32  来源完全真实但缺某类必要证据时被误判为 `INVALID` → 必须改为 `VERIFIED` + `INSUFFICIENT`
CE-33  验收矩阵行存在但绑定的 AC 语义与该 requirement 行为无关 → 视为验收缺陷，须重新绑定
CE-34  `REQ-W5-02` 以 host deny 类 AC 充数（无自有 enforcement 验收）→ 必须拒绝
CE-35  `REQ-W5-01` 只验 host deny、未覆盖 authority load / override / state restore / auto-advance / advisory 如实记录 → 必须拒绝
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

### 10.1a 显式交叉映射表（F6 修正；R3 修正：语义绑定）

下表为**每条 requirement 的显式交叉映射**（producer → interface → consumer → evidence → acceptance）。**多个 requirement 可共用同一 AC**，但必须逐条在表中出现，不得以"见上文"省略。**不为凑数量增加低价值测试。**

**R3 要求**：**`ROW_PRESENT != BEHAVIOR_ACCEPTED`**。每行绑定的 AC 必须**语义相关**于该 requirement 的行为；语义无关的绑定视为缺陷（`INV-22`）。

| REQ | Producer | Interface | Consumer | Evidence | AC（语义绑定） |
|---|---|---|---|---|---|
| `REQ-W1-01` | 拆票主体（authority/design 侧冻结①类）+ 执行侧（产生②类） | `references/ticket-lane.md` §3 seam 合同块（①/② 分区） | 票内 worker、L1 reviewer、integrator | 冻结的 seam 字段组 + 关闭证据字段；`EVIDENCE_REF` | **`AC-43`**（命名与唯一声明，M1）, `AC-01`, `AC-02`, `AC-03`, `AC-12`, `AC-20` |
| `REQ-W1-02` | 拆票主体 | `references/execution-stage.md` §6 拆票前识别清单 | ticket authorization 后的票内执行者 | 拆票前 8 字段记录 + 票内 RED 执行记录（owner = `RED_EXECUTION_OWNER`） | `AC-21`, `AC-12` |
| `REQ-W1-03` | 执行侧（集成票） | `references/git-ci-integration.md` §4/§5 + AGENTS §6 | integrator | `REAL_ENTRYPOINT`/`PRODUCTION_CALL_CHAIN`/`OBSERVED_PRODUCTION_EFFECT`/`PRODUCTION_CALLERS`/`RUNTIME_REACHABLE`/`EVIDENCE_REF` | `AC-04`, `AC-05`, `AC-23`, `AC-20` |
| `REQ-W1-04` | worker / native harness；L0；reviewer；integrator | 既有角色分离（AGENTS §3/§6） | 同上 | 各方产出物分离，互不代替 | `AC-01` |
| `REQ-W2-01` | 本 Spec → 未来实现 | `references/review-evidence.md` + schema + template + CLI（四文件） | L1/L2/integrator/CI | 四文件存在且互相一致（single source）；**新 `references/review-evidence.md` 通过既有 `references-declare-canonical-owner` 检查**（A3） | **`AC-44`**（接口一致性，M3/A3）, `AC-06`, `AC-10`, `AC-42` |
| `REQ-W2-02` | producer（`scripts/review_evidence.py` collect） | `unverified[]` + 信任/取回边界 | validator、L1 | 收集到的事实 + 未验证项 + 不执行/不取回的边界证明 | `AC-24`, `AC-25`, `AC-26`, `AC-27`, `AC-06`, `AC-42` |
| `REQ-W2-03` | validator | 三条正交轴（`STRUCTURALLY_VALID` / `SOURCE_VERIFICATION_STATE` / `EVIDENCE_SUFFICIENCY`） | L0/L1 gate | 三轴各自取值 + 轴间处置 + 失败分类 | `AC-39`, `AC-06`, `AC-07`, `AC-10`, `AC-22` |
| `REQ-W2-04` | 本 Spec（字段合同）→ producer/validator 实现 | `schemas/review-evidence.schema.json` + `templates/review-evidence.json` | validator、L1、integrator | (a)–(g) 子合同逐条可判 | (a)(g) `AC-28`, `AC-29`, `AC-30`；(b)(d) `AC-24`, `AC-25`, `AC-26`, `AC-27`；(c) `AC-39`；(e) `AC-31`, `AC-32`；(f) `AC-42`；通用 `AC-06`, `AC-07`, `AC-10`, `AC-22` |
| `REQ-W2-05` | reviewer（语义 scope 结论） | `semanticScopeStatus` 字段（reviewer 写入） | L1/L2、integrator | reviewer 权威写入；观测不自动升格 | `AC-35` |
| `REQ-W2-06` | consumer 侧（L1/L2/integrator/Stage） | `reviewerDecisionRefs` 与机器事实分字段 | L1/L2/integrator/Stage packet | 不自批证据 + Stage 只引用不复制 | `AC-36`, `AC-08` |
| `REQ-W2-07` | 仓政策 + producer | `subject commit` / `report commit` 显式区分 | integrator、后续 reviewer | 两 commit 身份分离；新报告提交不继承旧 PASS | `AC-37` |
| `REQ-W3-01` | 证据各类型 owner | 各类型独立有效期（五类） | L1/L2/CI/integrator | 各 receipt 与其绑定对象 | `AC-33`, `AC-34`, `AC-11` |
| `REQ-W3-02` | 复用声明者 | `reuse` 依赖描述符（`REQ-W2-04(e)`） | L1/L2 | `VALID_FOR` + `VERIFICATION_STATE != UNKNOWN` | `AC-31`, `AC-32`, `AC-11` |
| `REQ-W3-03` | canonical（`git-ci-integration.md`） | 失效触发清单（四项） | L1/L2/CI | 命中记录 + 定向失效范围 | `AC-33` |
| `REQ-W3-04` | canonical（既有） | 既有 `CI_STATUS` 七值集 | CI/L1/consumer | CI 原始状态 + 非 PASS 独立接受记录 | `AC-30`, `AC-11`, `AC-22` |
| `REQ-W4-01` | 本 Spec（冻结预算）→ 未来实现 | **`AGENTS.md` §10**（F-A1 新增）+ `deployment/BOOTSTRAP_CONTRACT.md` §2.1（语义 owner）+ 候选 + `scripts/validate_governance.py` + **`README.md`**（F-B1 新增） | 校验器、部署者、**AGENTS.md 与 README 读者** | `WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES=3500` 契约 + UTF-8 byte 检查 + 实测反例 + **五 surface 无残留字符预算语义** | `AC-17` |
| `REQ-W4-02a` | canonical owner（`review-and-repair-saturation.md`） | audit visibility recipe（字段组 + 两个 completeness 输出） | 外审/审计执行者、reviewer | recipe 记录 + `CONTEXT_COMPLETENESS_FOR_DECISION_AUDIT` / `FULL_HISTORICAL_TRANSCRIPT_COMPLETENESS` | `AC-13`, `AC-38` |
| `REQ-W4-02b` | canonical owner（`git-ci-integration.md`） | destructive transaction recipe（`status → 保全 → 操作 → post-state`） | 执行者、reviewer | 保全前后状态记录 | `AC-14`, `AC-38` |
| `REQ-W4-02c` | canonical owner（`ticket-lane.md`） | single-writer + readback recipe | 票内执行者、L1 | 聚合修改记录 + **最终回读**核验结果 | `AC-15`, `AC-38` |
| `REQ-W4-02d` | canonical owner（`engineering-memory.md`） | learning closure 条件 | 执行者、reviewer | 采纳/拒绝理由 + 验证引用 | `AC-16`, `AC-38` |
| `REQ-W4-02e` | canonical owner（`skills-and-model-routing.md`） | model dispatch 字段组 | 派发者、reviewer | 字段齐备 + 型号可更新 profile | `AC-19`, `AC-38` |
| `REQ-W4-03` | adapter/hook 实现（S1） | `grounding_guard.py` 退出码合同 + adapter deny 映射合同 | 宿主 runtime bridge、L0/L1 | exit 0/2 语义 + adapter deny 映射合同 + 合成/reference 测试；无映射 → ADVISORY | `AC-18` |
| `REQ-W4-03-D` | live 宿主（W5） | 真实 runtime deny 路径 | integrator（live） | 真实工具事件 → block → deny → 目标未修改 | `AC-18-D` |
| `REQ-W4-04` | gate 脚本实现 | CLI 入口自测（`argv → main`、退出码、结构化输出、探针） | consumer / CI | 真实命令入口测试（非 import 冒充）+ 副作用的探针 | `AC-09` |
| `REQ-W5-01` | live 宿主 + 部署者 | fresh neutral session / project session 验收协议 | PRODUCT OWNER | session 记录 + authority load/override/state restore/auto-advance + deny 实测 + 降级如实记录 | `AC-40`（并含 `AC-18-D` 作为其中第 7 项） |
| `REQ-W5-02` | 仓部署政策 / PRODUCT OWNER | GitHub 保护配置（未来） | PRODUCT OWNER | 授权的 settings/API 证据；权限不可得 → `NOT_VERIFIED` | `AC-41` |

**AC 引用为完整显式 ID**（不用 `AC-28/29/30` 之类缩写），以便审查方机械核验每条绑定存在且语义相关。

**共 AC 说明**：`AC-01` 由 `REQ-W1-01` 与 `REQ-W1-04` 共用；`AC-06`、`AC-07`、`AC-10`、`AC-22`、`AC-42` 由 W2 多条共用；`AC-11` 由 W3 四条共用；`AC-31`、`AC-32` 由 `REQ-W2-04(e)` 与 `REQ-W3-02` 共用；`AC-33` 由 `REQ-W3-01` 与 `REQ-W3-03` 共用；`AC-30` 由 `REQ-W2-04(a)` 与 `REQ-W3-04` 共用；`AC-38` 由 `REQ-W4-02a`..`REQ-W4-02e` 五条共用；`AC-18` / `AC-18-D` 分别承担 `REQ-W4-03` 的 S1 与 W5 两面。**共用不表示可省略任一 requirement 的映射行，也不表示可用语义无关的 AC 充数。**

**R3 纠正记录（原语义错配 → 现绑定）**：

```text
REQ-W2-05  原 AC-07（产物摘要类，语义无关）        → 现 AC-35（语义 scope 权威分离）
REQ-W5-02  原 AC-18-D（host deny，语义无关）       → 现 AC-41（GitHub enforcement 自有验收）
REQ-W2-02  原 AC-06/08/22 泛化带过                → 现 AC-24/25/26/27（信任边界四行为）
REQ-W2-04  原 AC-06/07/10/22 泛化带过             → 现 AC-28/29/30/31/32/39/42（字段合同逐条）
REQ-W2-06  原 AC-08 单点                          → 现 AC-36（不自批 + Stage 只引用）
REQ-W2-07  原 AC-06/11（间接）                    → 现 AC-37（subject/report commit 分离）
REQ-W4-02a..02e  原无 owner 唯一性验收            → 现 AC-38
```

**专项交叉映射（F6 点名的关注点；R3 补齐语义 AC）**：

```text
(1) W2 producer / schema / field / consumer / storage
    → REQ-W2-01..07 行（producer=`review_evidence.py` collect；schema=`schemas/review-evidence.schema.json`；
      field=REQ-W2-04 (a)–(g) → AC-42 逐条可判；consumer=L1/L2/integrator/Stage；
      storage=引用既有 CI artifact/PR evidence，不建第二账本 → AC-36；
      subject/report commit 分离 → REQ-W2-07 / AC-37）
(2) Model dispatch recipe
    → REQ-W4-02e 行（owner=`skills-and-model-routing.md`；interface=字段组；consumer=派发者/reviewer；AC-19 + AC-38）
(3) W5 Bootstrap live adoption
    → REQ-W5-01 行（producer=live 宿主+部署者；consumer=PRODUCT OWNER；**AC-40 复合验收**；
      fresh neutral session / project session / override / state restore / auto-advance / advisory-NOT_RUN 不得报 PASS / real host deny）
(4) W5 GitHub enforcement
    → REQ-W5-02 行（**AC-41 自有验收**：授权的 settings/API 证据 → 预期 required checks/ruleset/bypass；
      权限不可得 → NOT_VERIFIED 不是 PASS；不得要求破坏性直推探针；本阶段不配置）
(5) subject/report commit SHA 循环避免
    → REQ-W2-07 行（**AC-37**：两 commit 身份分离；不继承旧 PASS；无 candidate↔report 无限循环）
(6) 语义 scope 权威分离
    → REQ-W2-05 行（reviewer 写 `semanticScopeStatus`；producer 观测不自动升格；**AC-35**）
(7) Review Evidence 信任边界
    → REQ-W2-02 / REQ-W2-04(d) 行（**AC-24 不执行 commandRef / AC-25 不取回任意 URL /
      AC-26 绝对越界路径拒绝 / AC-27 合法 repo 相对路径与授权 CI artifact 仍可取回**）
(8) Runtime reachability applicability / N/A review
    → REQ-W1-01（判定规则 + REASON/ACCEPTANCE_REF 槽位）/ REQ-W1-03（关闭证据）/ AC-20
```

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
| AC-13 | 外审 primary 不可见时限定结论，不伪称完整 | REQ-W4-02a | CE-15 |
| AC-14 | 保全操作不丢 tracked 修改与 untracked 成果 | REQ-W4-02b | CE-16 |
| AC-15 | 共享文件多项预期更新经最终回读均存在 | REQ-W4-02c | CE-17 |
| AC-16 | learning 关闭有采纳/拒绝理由与验证引用 | REQ-W4-02d | CE-18 |
| AC-17 | **Bootstrap 字节预算（A1 补强）** — PASS iff ① 校验器使用 **UTF-8 编码字节长度**（`len(body.encode("utf-8"))`，非字符数）；② `WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES = 3500` 已冻结；③ 当前候选正文仍在预算内（无回归）；④ **CJK 反例按预期失败**（1400 汉字 = 4200 bytes > 4028 观测截断点）；⑤ **不存在任何 canonical / bootstrap-facing surface 仍把 "3500 characters" 作为有效预算语义**（含 `AGENTS.md` §10、`README.md`）；⑥ `deployment/BOOTSTRAP_CONTRACT.md` **仍是** WorkBuddy budget / profile 区分的**唯一语义 owner** | REQ-W4-01 / MIG-01..09 | CE-19 |
| AC-18 | **S1 core**：声称 ENFORCED 的 runtime adapter 必须暴露可核验 deny 映射合同 + 合成/reference 测试；无映射须降级声明为 ADVISORY | REQ-W4-03 | CE-20（core 面） |
| AC-18-D | **W5 / DEPLOYMENT_ONLY**：真实宿主下 真实工具事件 → hook block → 宿主映射 deny → 目标未被修改 | REQ-W4-03-D / REQ-W5-01 | CE-20（live 面） |
| AC-19 | model dispatch 字段齐备且风险先于型号；型号不写死不变量 | REQ-W4-02e | — |
| AC-20 | `REACHABILITY_APPLICABILITY = N/A` 必须同时具备 `REACHABILITY_APPLICABILITY_REASON` 与 `REACHABILITY_APPLICABILITY_ACCEPTANCE_REF`；缺一按 REQUIRED 处理 | REQ-W1-01/03 | CE-14 |
| AC-21 | 拆票前不得执行 RED；RED 仅在 ticket authorization 后、票内实现前执行 | REQ-W1-02 | — |
| AC-22 | 来源暂不可达（网络/provider/auth/远端 artifact）不得被判为 `INVALID`；须 `SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE` + `EVIDENCE_SUFFICIENCY = INSUFFICIENT` + 阻断 PASS + 保留 cause | REQ-W2-03/04 | CE-07/CE-23 |
| AC-23 | `REACHABILITY_APPLICABILITY = REQUIRED` 的 Integration 票缺真实入口 → `INTEGRATION_COMPLETE = FALSE` | REQ-W1-03 | CE-04 |
| **AC-24** | **信任边界 · 不执行**：`commandRef` 指向的命令在任何证据处理路径中**均未被执行**（含植入可观测副作用的探针命令仍无副作用） | REQ-W2-02 / REQ-W2-04(d) | CE-25 |
| **AC-25** | **信任边界 · 不取任意 URL**：证据携带的任意 URL **均未被取回**（含指向可达测试 HTTP 服务、仍不得发生请求） | REQ-W2-02 / REQ-W2-04(d) | CE-25 |
| **AC-26** | **信任边界 · 路径拒绝**：绝对路径与越界路径（`..` 逃逸、仓根之外）**被拒绝**并报路径违规 | REQ-W2-04(b) / REQ-W2-04(d) | CE-25 |
| **AC-27** | **信任边界 · 允许路径仍可用（正向对照）**：合法 repo 相对路径与经授权的 CI artifact 标识**仍能正常取回** —— 边界收紧不得把合法取回一并封锁 | REQ-W2-04(b) / REQ-W2-04(d) | — |
| **AC-28** | **状态机分离 · 不可互用**：`checks[].status` 不得被用作 CI 状态；以 `CHECK_STATUS` 冒充 `CI_STATUS` 的消费路径必须失败 | REQ-W2-04(a) | CE-24 |
| **AC-29** | **状态机分离 · 未知值拒绝**：`checks[].status` 取闭合集之外的值 → 拒绝；`ci.originalState` 取既有七值集之外的值 → 拒绝 | REQ-W2-04(a) / REQ-W2-04(g) | CE-24 |
| **AC-30** | **状态机分离 · 既有 CI 状态保持 canonical**：`REQ-W3-04` 七值集未被新枚举替换或扩写 | REQ-W3-04 / REQ-W2-04(a) | CE-24 |
| **AC-31** | **复用 · 合法复用（正向）**：形状合法且 `VERIFICATION_STATE = VERIFIED` 的描述符 → 在声明的 `VALID_FOR` 范围内**允许复用** | REQ-W2-04(e) / REQ-W3-02 | CE-11/CE-12 |
| **AC-32** | **复用 · UNKNOWN 拒绝**：`VERIFICATION_STATE = UNKNOWN`（或描述符形状不合法）却声明复用 → **拒绝** | REQ-W2-04(e) / REQ-W3-02 | CE-26 |
| **AC-33** | **复用 · 相关失效**：命中 `REQ-W3-03` 触发清单（master drift / 共享 schema 或依赖变化 / 入口拓扑变化 / authority-profile-toolchain 变化）→ 相关证据**失效**，须定向重取 | REQ-W3-03 / REQ-W3-01 | CE-11 |
| **AC-34** | **复用 · 无关不失效**：与依赖无关的变更**不触发**全量失效（避免过度失效） | REQ-W3-01 / REQ-W3-02 | CE-12 |
| **AC-35** | **语义 scope 权威分离**：观测到的 changed files **不得**自我授权为语义 scope；`semanticScopeStatus` **只能**来自 reviewer 权威写入，producer 观测不得自动升格 | REQ-W2-05 | — |
| **AC-36** | **不自批 + Stage 只引用**：机器证据**不得**填充独立 reviewer verdict（`reviewerDecisionRefs` 与机器事实分字段）；Stage packet **只引用** canonical 证据，**不复制**为第三个可变账本 | REQ-W2-06 | — |
| **AC-37** | **subject/report commit 分离**：`subject candidate SHA` 保持显式；`report commit SHA` 独立；新增报告提交**不自动继承**旧 reviewer PASS；不存在 candidate-SHA ↔ report-SHA 无限循环 | REQ-W2-07 | — |
| **AC-38** | **owner 唯一性**：同一 recipe 定义**只**出现在一个 canonical owner；其它 surface **只指针/链接**、不重复定义 | REQ-W4-02a..02e | CE-28 |
| **AC-39** | **三轴正交**：合法组合 `SOURCE_VERIFICATION_STATE = VERIFIED` + `EVIDENCE_SUFFICIENCY = INSUFFICIENT` **被接受**；`INSUFFICIENT` 不得作为来源轴取值 | REQ-W2-03 / REQ-W2-04(c) | — |
| **AC-40** | **W5 Bootstrap live adoption（复合）**：fresh neutral session → governance authority loaded；project session → repository authority discovered；override → 正确 resolution；既有项目 → state restore 生效；authorized legal frontier → 按 canonical 规则 auto-advance；advisory / `NOT_RUN` → **never** 报为 ENFORCED/PASS；real host deny → 目标未被修改 | REQ-W5-01 | CE-20（live 面） |
| **AC-41** | **W5 GitHub enforcement**：经**授权的** repository settings / API 证据 → 观察到预期的 required checks / ruleset / bypass 政策；权限不可得 → `NOT_VERIFIED`（**不是** PASS）；**不得**要求破坏性直推探针 | REQ-W5-02 | — |
| **AC-42** | **字段合同逐条可判**：`REQ-W2-04(a)`–`(g)` 每一条子合同均有针对该条自身语义的行为验收（非仅由泛化 AC 带过）；含 `unverified[]` 省略非法 vs 空数组合法、`seams.applicability` 与 reachability applicability 同构 | REQ-W2-04 | CE-06/CE-07 |
| **AC-43** | **Seam authority/observation 命名与唯一声明（M1）**：PASS iff ① design/authority 字段表达 requirement；② closure 字段表达 observation；③ 不存在命名歧义的 design/observation 对；④ `EXPECTED_PRODUCTION_EFFECT` 恰有**一个**规范性声明点；⑤ 重复声明或歧义命名**触发失败** | REQ-W1-01（并覆盖 `INV-19`/`INV-20`） | CE-29/CE-30 |
| **AC-44** | **Review Evidence 接口一致性（M3；A3 补强）**：PASS iff ① 四个必需 surface 均存在；② `references/review-evidence.md` 是**唯一**语义详情 owner；③ schema 机械表达所需合同；④ template 符合 schema；⑤ CLI collect/validate 消费**同一** schema/合同；⑥ 其它 canonical surface **只指针/链接**、不定义竞争性 Review Evidence 接口；⑦ **新建的 `references/review-evidence.md` 通过既有 `references-declare-canonical-owner` 检查（含字面 `Canonical owner` 声明），且未削弱或绕过既有 validator** | REQ-W2-01 | CE-28（同源：单一 owner） |

**M1/M3 语义绑定原则**：`AC-43` 使 `REQ-W1-01` 的命名与唯一声明规则（`INV-19`/`INV-20`）具备**真实行为验收**，不再只靠规则文本；`AC-44` 使 `REQ-W2-01` 的四文件接口一致性具备自有验收，不再由 `AC-06`/`AC-10`/`AC-42` 泛化带过。二者均**不改变已冻结的字段命名**，也不新增 architecture mechanism。

**R3 语义绑定原则**：**`ROW_PRESENT != BEHAVIOR_ACCEPTED`**（`INV-22`）。上表每条 AC 必须描述**其覆盖 requirement 的真实行为**；不得以语义无关的 AC 充数。原先把 `REQ-W2-05` 绑到产物摘要类 `AC-07`、把 `REQ-W5-02` 绑到 host deny 类 `AC-18-D` 的映射**已在本轮纠正**（见 §10.1a 更新行）。

### 10.3 Gate 自测覆盖

```text
PASS / FAIL / malformed / silent-noop / 真实命令入口
正确结果与错误结果都要检查消费者实际处置
```

### 10.4 本 Spec 自身的验收（本次会话）

```text
SPEC COMMITTED          （append-only 新 commit，无 amend）
SPEC PUSHED
REMOTE EXACT SHA VERIFIED
SPEC_REVIEW = PENDING_FINAL_RE_REVIEW
STOP
```

**`SELF_REVIEW != SPEC_APPROVAL`**：本 Spec 的自检、格式校验、远端上传成功**均不构成**批准。**修复本身也不构成批准**——修复后的新 SHA 必须重新走独立 exact-SHA Spec review（`RULES.md` R5，见 §16）。`ARCHITECTURE_REVIEW = PASS` 仅表示架构层已通过，**不代替** Spec 层审查。

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
| **S1 core 实现** | W1–W4 的 canonical 变更与新增文件；**含 `REQ-W4-01` 的完整五 surface（`AGENTS.md` §10 由 F-A1 纳入，`README.md` 由 F-B1 纳入）** | ❌ **需要 owner 明确 `SPEC_REVIEW = PASS` 后才进入拆票与执行** |
| **S2 core 合并后采用** | 把已合并的 canonical 变更在真实仓采用（含 bootstrap 静态修正落地） | ❌ 需 S1 完成 + 单独授权 |
| **S3 live deployment** | bootstrap 真实部署、GitHub enforcement、host guard deny 映射实测 | ❌ `DEPLOYMENT_ONLY`，需**单独 live 部署授权** |

**S1 写面提示（F-A1 + F-B1）**：`REQ-W4-01` 的 S1 写面为 **5 个 surface**（`AGENTS.md` §10 / `deployment/BOOTSTRAP_CONTRACT.md` / `deployment/MEMORY_POINTER_CANDIDATE.md` / `scripts/validate_governance.py` / `README.md`）。**只改校验器或只改 contract 均视为未完成**（`AC-17` 第 5 项）。本轮 `IMPLEMENTATION_AUTHORIZED = NO`，**未触碰以上任何文件**。

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
| `EXTEND` | REQ-W1-01, REQ-W1-02, REQ-W1-03, REQ-W3-01, REQ-W3-02, REQ-W3-03, REQ-W4-01, REQ-W4-02a, REQ-W4-02b, REQ-W4-02c, REQ-W4-02d, REQ-W4-02e, REQ-W4-03, REQ-W4-04 |
| `NEW` | REQ-W2-01, REQ-W2-02, REQ-W2-03, REQ-W2-04, REQ-W2-05, REQ-W2-06, REQ-W2-07 |
| `DEPLOYMENT_ONLY` | REQ-W4-03-D, REQ-W5-01, REQ-W5-02 |

**F3 修正说明**：原 `REQ-W4-02`（单一 `NEW` 复合子系统）拆为 `REQ-W4-02a`..`REQ-W4-02e`，**每条绑定单一 canonical owner**，分类由 `NEW` 改为 `EXTEND`（不新建第二权威体系，`INV-07`）。

**F4 修正说明**：原 `REQ-W4-03` 拆为 **S1 core**（`REQ-W4-03`，`EXTEND`，adapter deny 映射合同 + 合成测试）与 **W5 live**（`REQ-W4-03-D`，`DEPLOYMENT_ONLY`，真实宿主 deny 映射实测）。

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

受影响 requirement：`REQ-W4-01`。最小候选解决方案：`MIG-01..MIG-09`（完整 migration set；MIG-01..06 由 F5 定义，MIG-07..09 由本轮 F-A1/A2 扩充）。因可在既有 authority 下唯一解决，**不 STOP**。

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
REPAIR_ROUND             = 6（F-B1：把 `README.md` 纳入 REQ-W4-01 完整 change surface；
                            ROUND 1 = F1–F6，ROUND 2 = R1–R4，ROUND 3 = M1–M3，ROUND 4 = F-A1/A2/A3，
                            ROUND 5 = owner 裁定 R5 + 同根一致性修复 R5-1/R5-2/R5-3）
ARCHITECTURE_REOPEN      = NO（ARCHITECTURE_REVIEW = PASS）
REPAIR_SCOPE             = ROUND 6 F-B1（第五个 bootstrap 收敛面 = `README.md`）+ DIRECT SAME-ROOT CONSISTENCY ONLY
                           （同根：同步更新全部「四 surface」枚举与轮次账本登记）
FILES_CHANGED             = docs/specs/P1_AGENT_ENGINEERING_GOVERNANCE_DELTA_SPEC.md（唯一）
IMPLEMENTATION_FILES      = NONE（AGENTS.md / BOOTSTRAP_CONTRACT.md / validate_governance.py /
                            references/* 均为被纳入 Spec 的未来实现面，本轮未修改）
ZHIHU_MODIFIED            = NONE
CANONICAL_MODIFIED        = NONE（RULES.md / AGENTS.md / references/* 均未修改）
ISSUE_9                   = OPEN（未关闭）
TICKETS_CREATED           = NONE
MERGED                    = NO
SPEC_REVIEW               = PENDING_FINDING_SCOPED_RE_REVIEW
NEXT                      = INDEPENDENT_EXACT_SHA_RE_REVIEW_ROUND_6
```

---

## 16. FINDING-SCOPED REPAIR 记录

### 16.0 修复轮次索引

```text
ROUND 1（F1–F6）   reviewed SHA 458ed253 → 修复 SHA 7d4887b6
ROUND 2（R1–R4）   reviewed SHA 7d4887b6 → 修复 SHA c7de399 + 83b714c
ROUND 3（M1–M3）   reviewed SHA 83b714c2 → 修复 SHA 3803518a
ROUND 4（F-A1/A2/A3） reviewed SHA 3803518a → 修复 SHA 60209cd
ROUND 5（OWNER 裁定 R5 + 同根一致性修复 R5-1/R5-2/R5-3） reviewed SHA 60209cd → 修复 SHA 6492eed
ROUND 6（F-B1：把 `README.md` 纳入完整 change surface） reviewed SHA 6492eed → 本文件当前内容（见 §16.10）
```

每轮均为**评审后修复**：`SPEC_REVIEW = CHANGES_REQUESTED`，`REVIEW_SCOPE = FINDING_SCOPED_DELTA_ONLY`。**仅修改本文件**，append-only 新 commit，无 amend / rebase / force push，同一 feature branch。**修复不构成批准**；修复后新 SHA 必须重新走独立 exact-SHA review（`RULES.md` R5）。

### 16.1 ROUND 1 逐条处置（F1–F6）

| Finding | 处置 | 落点 |
|---|---|---|
| **F1** 生命周期与 Contract/Evidence 分离 | `REQ-W1-01` 字段拆为 **① 设计/权威字段** 与 **② 关闭证据字段**；`REACHABILITY_APPLICABILITY` 拆出 authority 侧四字段（`REACHABILITY_APPLICABILITY` / `REACHABILITY_REQUIREMENT` / `EXPECTED_PRODUCTION_EFFECT` / `REACHABILITY_PROOF_OWNER`），`N/A` 需**理由 + reviewer/integrator 接受记录**，worker 不得自行豁免；`REQ-W1-02` 改为**拆票前只做识别与定义（8 字段）**，**RED 执行移到 ticket authorization 之后、票内实现之前**；`REQ-W1-03` 改为只承载②类关闭证据 | §3.1 `REQ-W1-01/02/03`；`INV-11/12`；`AC-20/21/23`；`CE-21/22` |
| **F2** 冻结 Review Evidence 字段合同 | 新增 `REQ-W2-04(a)`–`(g)`：`CHECK_STATUS` 闭合集且 `≠ CI_STATUS`；`artifacts[].location` 受限；来源三态（`INVALID` vs 暂不可达 vs `INSUFFICIENT`；F2 当时记为 `UNVERIFIED_TEMPORARILY_UNAVAILABLE`，**已由 R2 更名为 `TEMPORARILY_UNAVAILABLE` 并将充分性迁出该轴**）；`review_evidence.py` 信任/取回边界；`reuse` 依赖描述符最小形状（`VERIFICATION_STATE = UNKNOWN` → 不许复用）；`unverified[]` 省略非法；`ci.originalState` 取值域 | §3.2 `REQ-W2-02/03/04`；§5.1 字段表；§6.2a；`INV-13/14/15`；`AC-22`；`CE-23/24/25/26` |
| **F3** 按 canonical owner 拆分 W4 配方 | 原 `REQ-W4-02`（单一 `NEW` 复合子系统）拆为 `REQ-W4-02a`..`02e`，逐条绑定**单一 owner**（`review-and-repair-saturation.md` / `git-ci-integration.md` / `ticket-lane.md` / `engineering-memory.md` / `skills-and-model-routing.md`），分类由 `NEW` → **`EXTEND`**；同步 `AUTHORITY_OWNER`、`INTEGRATION_POINTS`、分类总表、staging 写面 | §3.4；§4.1；§7；§12.2；§8.2；`INV-16`；`CE-28` |
| **F4** live deny 映射移到 `DEPLOYMENT_ONLY` | `REQ-W4-03` 保留 **S1 core 合同**（exit 0/2 语义 + adapter 必须暴露可核验 deny 映射合同 + 合成/reference 测试；无映射须降级声明 ADVISORY）；真实宿主 deny 映射实测拆为 **`REQ-W4-03-D`（`DEPLOYMENT_ONLY` / W5）**；`AC-18` 拆为 `AC-18`（S1）+ `AC-18-D`（W5）；`REQ-W5-01` 吸收 live deny 映射 | §3.4/§3.5；§4.1；§7；§10.2；`INV-17` |
| **F5** Bootstrap 字节预算合同 | 冻结 `WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES = 3500`，显式给出 **VALUE / UNIT / OWNER / SOURCE / SCOPE / OVERRIDE-PROFILE SEMANTICS**；显式区分 **3500（预算）≠ 4028（观测截断点）**；校验器须用 UTF-8 编码字节长度；把"本 Spec 只授权前者"改为"**纳入未来 S1 core scope；只有 SPEC_REVIEW = PASS 且 owner 授权后方可实施**" | §3.4 `REQ-W4-01`；§8.1 `MIG-01..06`；`INV-18`；`AC-17`；`CE-19` |
| **F6** 验收可追溯性 + 收窄历史过度概括 | 新增 §10.1a **显式交叉映射表**（逐 requirement：producer → interface → consumer → evidence → AC），含共 AC 条目与 8 项专项关注点；§1.1 把"D1–D6 全部在单元测试通过的前提下逃逸"收窄为"共同模式是 seam 假设错位；其中 D6 / T15 / D5 有 B 级证据证明局部绿色不足以证明真实边界成立，其余条目不作测试先绿主张" | §10.1a；§1.1 |

### 16.2 保留项确认（未重开）

以下**均未被本轮修复改动**，与 `PRESERVE / DO NOT_REOPEN` 清单一致：

```text
W1–W5 总体架构                      保留
Seam Before Ticket 方向             保留（仅修正其 RED 执行时点，未反转方向）
Runtime Reachability 进入治理        保留（仅拆分权威/证据字段）
Review Evidence 需最小机器层         保留
project-state 不成为第二 tracker     保留（REQ-W2-01 边界约束未变）
证据包不成为 CI runner               保留
L0/L1/L2                            保留（§5.2 未改）
exact SHA / delta review            保留
既有 CI 状态系统                     保留（REQ-W3-04 未改，F2 只声明 CHECK_STATUS != CI_STATUS）
证据复用既非全失效也非无条件          保留（REQ-W3-01/02/03 未改，F2 只补依赖描述符形状）
audit visibility 按需非每票强制       保留
不建全局 stash 禁令                  保留（§4.3 未改）
知乎仓仅作证据源                     保留
Bootstrap live adoption / GitHub enforcement 延后   保留
anti-bloat                         保留（F3 使 W4 由 NEW 降为 EXTEND，净减少新权威面）
CE-01..CE-20 未与 finding 冲突的部分  保留（新增 CE-21..28，未删改既有条目语义）
```

### 16.3 修复后仍属未决（`UNRESOLVED_DECISIONS`）

```text
UNRESOLVED-01  CHECK_STATUS 闭合集中的 SKIPPED / ERROR 与 CI_STATUS 的对应关系细则，
              留待 S1 实现票按 schema 冻结（本 Spec 只冻结"两者不同"与闭合集本身）。
UNRESOLVED-02  audit visibility recipe 的两处候选 owner 已择一
              （review-and-repair-saturation.md），但 review-evidence.md 的"只引用"措辞
              需在 S1 写该文件时落实（本 Spec 无法在文件不存在时核验）。
UNRESOLVED-03  3500 之外是否存在其它已核验 runtime profile，
              本 Spec 无 primary evidence，按"无已核验 profile 时回落 3500"处理。
UNRESOLVED-04  D1/D2/D3/D4 是否同样具备"事故前单元测试绿色"的 primary evidence，
              NOT_VERIFIED，故不作该主张（见 §1.1）。
```

**这些未决项不阻塞 Spec 审查**：它们是实现期变量，不是 Spec 层的权威冲突；且均以 fail-closed 方式处理（无依据 → 回落严格侧 / 不作过度主张）。

---

### 16.4 ROUND 2 逐条处置（R1–R4）

**审查候选**：`OLD_REVIEWED_SHA = 7d4887b60b36219a4e4aa4fc11264e31d894fc7a`；`ARCHITECTURE_REOPEN = NO`；`TICKETING = NO`；`IMPLEMENTATION = NO`。本轮**只修 R1–R4**，未重开已通过的 F3/F4 架构，未扩大 W1–W5，未新增治理子系统。

#### 16.4.1 R1 — 消除剩余 Seam 权威歧义

| 项 | 处置 | 落点 |
|---|---|---|
| `EXPECTED_PRODUCTION_EFFECT` 重复声明 | **只保留一个 canonical declaration**：仅在 `REQ-W1-01` ① 块内声明一次；新增**唯一声明点规则**（全文其它位置含 `REQ-W1-03` 只引用、不重复声明） | `REQ-W1-01`；`REQ-W1-03`；`INV-20`；`CE-30` |
| `PRODUCTION_CALLER`（设计）vs `PRODUCTION_CALLERS`（观测）歧义 | 设计侧**改名为 `EXPECTED_PRODUCTION_CALLER`**（与全文 `EXPECTED_*` 命名族最一致，明确表达 requirement）；关闭侧保留 `PRODUCTION_CALLERS`（observation）。冻结正式映射表：`EXPECTED_PRODUCTION_EFFECT → OBSERVED_PRODUCTION_EFFECT`、`EXPECTED_PRODUCTION_CALLER → PRODUCTION_CALLERS`、`REACHABILITY_REQUIREMENT → RUNTIME_REACHABLE` | `REQ-W1-01` 两处字段块；`INV-19`；`CE-29` |
| 设计/观测语义纪律 | 明确：**① 类字段必须表达 requirement；② 类字段必须表达 observation**；两类不得同名、不得近似到需 implementer 猜测 | `REQ-W1-01` 命名纪律段；`INV-19` |
| `N/A` 的字段槽位未冻住 | 冻结两个最小槽位：**`REACHABILITY_APPLICABILITY_REASON`** 与 **`REACHABILITY_APPLICABILITY_ACCEPTANCE_REF`**；任一缺失/为空 → 按 `REQUIRED` 处理 | `REQ-W1-01` ①块 + 判定规则；`REQ-W1-02`；`AC-20` |

#### 16.4.2 R2 — 来源核验与证据充分性正交

**原缺陷**：`SOURCE_VERIFIED = NO + cause = INSUFFICIENT` 把"充分性"塞进"来源轴"，违反本 Spec 自己的"三层不可坍缩"。

**修正**：改为**三条独立状态轴**（`R2` 推荐的最小规范，原样采纳）：

```text
STRUCTURALLY_VALID        = YES | NO
SOURCE_VERIFICATION_STATE = VERIFIED | INVALID | TEMPORARILY_UNAVAILABLE | NOT_VERIFIED
EVIDENCE_SUFFICIENCY      = SUFFICIENT | INSUFFICIENT
```

- `INVALID` **只**表示来源/内容本身机械错误（SHA mismatch / digest mismatch / forged-or-invalid source identity / path violation）。
- `TEMPORARILY_UNAVAILABLE` 表示 network / provider-auth / remote-artifact 暂不可达。
- `INSUFFICIENT` **只属于 `EVIDENCE_SUFFICIENCY`**；新增合法且必须接受的组合：`SOURCE_VERIFICATION_STATE = VERIFIED` + `EVIDENCE_SUFFICIENCY = INSUFFICIENT`。

同步落点：`REQ-W2-03`（三轴 + 轴间处置规则）；`REQ-W2-04(c)`（轴定义）；§5.1（字段表拆为三行）；§6.1（失败分类与 `TEMPORARILY_UNAVAILABLE` 独立归类）；§6.2a（五状态机不坍缩表）；`INV-21`；`AC-22`（改写）/`AC-39`（新增）；`CE-31/CE-32`（新增）。**未引入五轴之外的第六套概念。**

#### 16.4.3 R3 — 修复语义验收交叉映射（不只是行覆盖）

**原缺陷**：§10.1a 每行都出现（`ROW_PRESENT`），但部分 AC 与 requirement **语义不相关**（`!= BEHAVIOR_ACCEPTED`）。

**修正**：新增 `AC-24`–`AC-42` 共 19 条语义相关验收，并**重新绑定** §10.1a 各行。逐项对照：

| 要求覆盖项 | 新增/重绑 AC | 覆盖 REQ | CE |
|---|---|---|---|
| **A** 信任边界（不执行 commandRef / 不取任意 URL / 越界路径拒绝 / 合法取回仍可用） | `AC-24` / `AC-25` / `AC-26` / `AC-27`（正向对照） | `REQ-W2-02`、`REQ-W2-04(b)(d)` | `CE-25` |
| **B** `CHECK_STATUS` vs `CI_STATUS` 分离（不可互用 / 未知值拒绝 / 既有 CI 状态保持 canonical） | `AC-28` / `AC-29` / `AC-30` | `REQ-W2-04(a)(g)`、`REQ-W3-04` | `CE-24` |
| **C** reuse 依赖描述符（合法复用 / `UNKNOWN` 拒绝 / 相关失效 / 无关不失效） | `AC-31` / `AC-32` / `AC-33` / `AC-34` | `REQ-W2-04(e)`、`REQ-W3-01/02/03` | `CE-11/12/26` |
| **D** 语义 scope 权威分离 | `AC-35`（**重绑**：原错绑产物摘要类 `AC-07`） | `REQ-W2-05` | — |
| **E** 不自批 + Stage 只引用 | `AC-36` | `REQ-W2-06` | — |
| **F** subject/report commit 循环 | `AC-37` | `REQ-W2-07` | — |
| **G** Bootstrap live adoption（7 项行为） | `AC-40`（复合，含原 host deny 面 + 补齐 6 项） | `REQ-W5-01` | `CE-20`（live 面） |
| **H** GitHub enforcement 自有验收 | `AC-41`（**重绑**：原错绑 host deny `AC-18-D`） | `REQ-W5-02` | — |
| **I** single-owner recipe | `AC-38` | `REQ-W4-02a..02e` | `CE-28` |
| **J** schema/validator 字段合同 | `AC-42`（(a)–(g) 逐条可判） | `REQ-W2-04` | `CE-06/07` |

**新增不变量** `INV-22`：`ROW_PRESENT != BEHAVIOR_ACCEPTED`。**新增反例** `CE-29`..`CE-35`（含"AC 语义无关"与"W5-02 以 host deny 充数"两类）。**未增加低价值凑数测试。**

#### 16.4.4 R4 — 可追溯性同步

原 `AC-17` 的迁移引用为 `MIG-01..05`，但 migration set 实为 `MIG-01..06`（轮 1 已新增 `MIG-06` 冻结预算值）。处置：

```text
AC-17 覆盖引用           MIG-01..05  →  MIG-01..06      （已改）
§13 受影响 requirement    MIG-01..05  →  MIG-01..06（语义为完整 migration set，已改）
```

全文 `MIG-01..05` 字样已清零；`MIG-01..06` 成为当时的完整引用形态。**（轮 4 已将完整 migration set 扩充为 `MIG-01..09`，见 §16.8。本行为轮 2 记录，保留原样。）**

---

### 16.5 ROUND 2 保留项确认（未重开）

```text
W1–W5 overall architecture                    保留
Seam Before Ticket                            保留
RED lifecycle after ticket authorization      保留（R1 未改其生命周期，仅消歧字段命名）
Runtime Reachability                          保留
Review Evidence minimal machine layer         保留
W4 canonical owner split (F3)                 保留（未重开；R3 仅补 AC-38 验收）
core vs live host deny split (F4)             保留（未重开；R3 仅补 AC-40 其余 6 项行为）
3500-byte WorkBuddy budget decision           保留
4028 observed truncation distinction          保留
UTF-8 byte semantics                          保留
L0/L1/L2                                      保留
exact-SHA / incremental review                保留
anti-bloat                                    保留（未新增子系统；AC-24..42 为已有行为的验收补全）
Zhihu evidence-only boundary                  保留
GitHub enforcement DEPLOYMENT_ONLY            保留（R3 只为其补自有验收，未改其 DEPLOYMENT_ONLY 定位）
```

### 16.6 ROUND 2 修复后仍属未决（`UNRESOLVED_DECISIONS`，增量）

```text
UNRESOLVED-05  AC-27（合法 repo 相对路径 / 授权 CI artifact 仍可取回）的"正向对照"具体探针形态，
              留待 S1 实现票按 `review_evidence.py` 实际接口冻结；本 Spec 只冻结该正向行为必须被验收。
UNRESOLVED-06  AC-40 第 5 项（authorized legal frontier → auto-advance）所依赖的 canonical
              auto-advance 规则细则属 AGENTS §7 既有条款，本 Spec 只引用不重述。
UNRESOLVED-07  AC-41 中"预期 required checks / ruleset / bypass 政策"的具体目标值，
              属 PRODUCT OWNER 的部署决策，本 Spec 不预设（本阶段亦不配置）。
```

轮 1 的 `UNRESOLVED-01`..`04` 继续有效（合计 `UNRESOLVED-01`..`07`）。**均不阻塞 Spec 审查**：它们是实现期/部署期变量，不是 Spec 层权威冲突，且全部 fail-closed 处理。

---

### 16.7 ROUND 3 — FINAL FINDING-SCOPED MICRO-REPAIR（M1–M3）

**审查候选**：`OLD_REVIEWED_SHA = 83b714c2cc35db1523f4e6593b67ef7dc8b2e67c`；
`ARCHITECTURE_REVIEW = PASS`；`SPEC_REVIEW = CHANGES_REQUESTED`；`ARCHITECTURE_REOPEN = NO`。
本轮**只修 M1–M3**：未重开 W1–W5、未新增 architecture mechanism、未重新整理全文、未拆 ticket / 实现 / merge。

#### 16.7.1 M1 — 让 R1 命名/唯一声明规则具备真实验收

**原缺口**：`INV-19`/`INV-20`/`CE-29`/`CE-30` 已定义命名消歧与唯一声明点规则，但 `REQ-W1-01` 的 crosswalk 尚无**真正验收这些行为**的 AC。

**修正**：新增 **`AC-43 — Seam authority/observation 命名与唯一声明**，PASS 条件为：

```text
1  design/authority 字段表达 requirement
2  closure 字段表达 observation
3  不存在命名歧义的 design/observation 对
4  EXPECTED_PRODUCTION_EFFECT 恰有一个规范性声明点
5  重复声明或歧义命名触发失败
```

`AC-43` 显式加入 `REQ-W1-01` 的 §10.1a crosswalk 行（置于该行首位）。落点：§3.1 `REQ-W1-01` 命名纪律段（新增 `AC-43` 引用与"已冻结命名不变"声明）；§10.2 `AC-43` 定义（覆盖 `REQ-W1-01` 并覆盖 `INV-19`/`INV-20`，RED 输入 `CE-29`/`CE-30`）；§10.1a `REQ-W1-01` 行。**未改变任何已冻结的字段命名。**

#### 16.7.2 M2 — 消除 `TEMPORARILY_UNAVAILABLE` / `INSUFFICIENT` 的 prose 歧义

**原缺陷**：§6.1 曾把 `TEMPORARILY_UNAVAILABLE` 描述为**不属于充分性问题**（原文称其既非 `REJECT` 亦非另一类失败），而同 spec 多处（`REQ-W2-03`、`REQ-W2-04(c)`、`AC-22`）规定该来源态会使 `EVIDENCE_SUFFICIENCY = INSUFFICIENT`。两种表述并存 = 冲突。

**修正（按审查方建议冻结，未新增第四轴或新概念）**：

```text
SOURCE_VERIFICATION_STATE = TEMPORARILY_UNAVAILABLE

means:
  source is NOT declared invalid;
  verification cannot currently complete;
  original cause is preserved.

For CURRENT candidate acceptance:
  EVIDENCE_SUFFICIENCY = INSUFFICIENT
  until required source verification can complete;
  PASS is blocked meanwhile.

This does NOT mean the underlying artifact is invalid.
```

核心区分冻结为：**`source validity != current evidence sufficiency`**。§6.1 原有的"`TEMPORARILY_UNAVAILABLE` 与 `INSUFFICIENT` 互不相干"式表述已移除，替换为：`TEMPORARILY_UNAVAILABLE` **不是来源轴上的 `INVALID`**，但在**当前候选判定**上确实使 `EVIDENCE_SUFFICIENCY = INSUFFICIENT`——两句分属**不同两条轴**，故不冲突。

同步落点：§6.1（冻结语义块 + 核心区分段 + 与 `REJECT` 的关系）；§6.2a（新增一条不坍缩说明）；§5.1（来源核验轴 + 证据充分性轴两行的合法组合补全）；`CE-23`（陈旧 token `UNVERIFIED_TEMPORARILY_UNAVAILABLE` → `TEMPORARILY_UNAVAILABLE`，并注明 M2 对应关系）；§16.1 F2 行（标注该 token 已由 R2 更名）。三轴架构本身**未变**：`STRUCTURALLY_VALID` / `SOURCE_VERIFICATION_STATE` / `EVIDENCE_SUFFICIENCY` 保持原样。

#### 16.7.3 M3 — 让 `REQ-W2-01` 具备自有接口一致性验收

**原缺口**：`REQ-W2-01` 定义四个 surface 并要求 `review-evidence.md` 为语义 single source，但 `AC-06`/`AC-10`/`AC-42` 只泛化带过，未真正验收该 requirement。

**修正**：新增 **`AC-44 — Review Evidence interface coherence`**，至少验收：

```text
1  四个必需 surface 均存在
2  references/review-evidence.md 是唯一语义详情 owner
3  schema 机械表达所需合同
4  template 符合 schema
5  CLI collect/validate 消费同一 schema/合同
6  其它 canonical surface 只指针/链接、不定义竞争性 Review Evidence 接口
```

`AC-44` 显式加入 `REQ-W2-01` 的 §10.1a crosswalk 行（置于该行首位），原有 `AC-06`/`AC-10`/`AC-42` 保留（均语义相关），但**不得以无关 AC 代替 `AC-44`**。落点：§3.2 `REQ-W2-01`（新增接口一致性要求块 + `AC-44` 引用 + 与 `REQ-W4-02a` 同源说明）；§10.2 `AC-44` 定义；§10.1a `REQ-W2-01` 行。顺带把该条模板注释 `R2 兼容` 明确为 `` `RULES.md` R2 兼容 ``，消除与修复轮次命名的歧义。

#### 16.7.4 ROUND 3 最终一致性核对（仅针对本轮改动）

```text
AC-43 defined and bound                      YES（§10.2 定义 + §10.1a REQ-W1-01 行）
AC-44 defined and bound                      YES（§10.2 定义 + §10.1a REQ-W2-01 行）
CE-29 / CE-30 have behavioral acceptance     YES（由 AC-43 覆盖）
REQ-W2-01 has semantic interface acceptance  YES（AC-44）
TEMPORARILY_UNAVAILABLE prose consistent     YES（冲突表述已移除；全篇统一为一套冻结语义）
```

#### 16.7.5 ROUND 3 保留项确认（未重开）

```text
W1–W5 overall architecture                    保留（ARCHITECTURE_REVIEW = PASS，未动）
W1–W5 机制边界与 owner                        保留
R1 已冻结字段命名（EXPECTED_* / *_CALLERS 等）  保留（M1 只增加验收，不改命名）
R2 三轴架构                                   保留（M2 只消歧 prose，不增删轴）
Review Evidence 最小机器层                     保留（M3 只增加接口一致性验收）
W4 canonical owner split (F3)                 保留
core vs live host deny split (F4)             保留
3500 / 4028 / UTF-8 byte 语义                  保留
L0/L1/L2、exact-SHA / delta review            保留
anti-bloat                                    保留（本轮仅新增 2 条 AC，无新机制、无新子系统）
Zhihu evidence-only boundary                  保留
GitHub enforcement DEPLOYMENT_ONLY            保留
CE-01..CE-35 未与 finding 冲突的部分            保留（本轮未新增 CE，未改既有 CE 语义）
```

#### 16.7.6 ROUND 3 新增未决项

```text
UNRESOLVED-08  AC-44 第 3/4/5 项（schema 机械表达合同、template 符合 schema、
              CLI 消费同一 schema）的具体校验形态，留待 S1 按实际 schema/CLI 接口冻结；
              本 Spec 只冻结这些一致性行为必须被验收。
```

轮 1/轮 2 的 `UNRESOLVED-01`..`07` 继续有效（合计 `UNRESOLVED-01`..`08`）。**均不阻塞 Spec 审查**：均为实现期/部署期变量，非 Spec 层权威冲突，且全部 fail-closed 处理。

---

### 16.8 ROUND 4 — ADVERSARIAL FINDING FINAL MICRO-REPAIR（F-A1 + A2 + A3）

**审查候选**：`OLD_REVIEWED_SHA = 3803518a3c6c40578a6e31a69be95bd4fb7de1fd`；
`ARCHITECTURE_REVIEW = PASS`；`ARCHITECTURE_REOPEN = NO`；
`REPAIR_SCOPE = F-A1 + DIRECT SAME-ROOT CONSISTENCY ONLY`。
本轮**未重新审计或改写 W1–W5、未新增机制、未扩大到其它 Tier-C observations**。

#### 16.8.1 F-A1 — 补齐 Bootstrap 字节预算的 canonical change surface

**独立核验（本轮在本机候选上实测，非仅采信报告）**：

```text
AGENTS.md:138        含 "≤3,500 字符"（原文：MEMORY 指针（候选文本 ...，≤3,500 字符））
```

**缺陷**：本 Spec 已冻结 `UNIT = UTF-8 bytes`，但 `§7 INTEGRATION_POINTS` 的 Bootstrap 行与 `REQ-W4-01` 的 change surface 此前**只枚举三个文件**（`BOOTSTRAP_CONTRACT.md` / `MEMORY_POINTER_CANDIDATE.md` / `validate_governance.py`）。若未来 S1 严格照此实施，会留下：

```text
AGENTS.md                          → characters
canonical contract / validator     → UTF-8 bytes
```

**残留冲突**。这正是本 Spec `INV-22` 所禁止的 `ROW_PRESENT != BEHAVIOR_ACCEPTED` 同类问题（**incomplete change surface**）。

**修正**：

1. `REQ-W4-01` 新增**「完整 canonical change surface」**块：未来 S1 change surface **必须覆盖四个 surface**，**`AGENTS.md` §10 本轮新增纳入**（此前遗漏）。
2. 冻结 `AGENTS.md` §10 的**未来目标语义**（二选一，**优先 A**）：
   - **A（优先）** pointer / derived-summary：`AGENTS.md` §10 不再自行声明字符数预算，改为引用由 `deployment/BOOTSTRAP_CONTRACT.md` 拥有的 canonical WorkBuddy byte budget；
   - **B（次选）** 显式 derived summary：若必须在 `AGENTS.md` 内给摘要，则明确写 "≤ 3500 UTF-8 bytes"，语义 owner 仍为 `BOOTSTRAP_CONTRACT.md`。
3. **硬约束**：**`AGENTS.md` 不得成为第二预算 authority**。
4. 同步落点：`§3.4 REQ-W4-01`（change surface + 目标语义 + 授权边界补充"本轮不修改 AGENTS.md 等四 surface"）；`§4.1`（Bootstrap 机制行）；`§7 INTEGRATION_POINTS`（Bootstrap 预算行）；`§8.1`（新增 `MIG-07`/`MIG-08` + 实测证据块）；`§10.1a`（`REQ-W4-01` 行）；`§10.2 AC-17`（补强）；`§13`（migration set 引用）。

**AC-17 补强（6 项 PASS 条件）**：

```text
1  校验器使用 UTF-8 编码字节长度
2  WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES = 3500
3  当前候选正文仍在预算内（无回归）
4  CJK 反例按预期失败
5  不存在任何 canonical / bootstrap-facing surface 仍把 "3500 characters" 作为有效预算语义
6  deployment/BOOTSTRAP_CONTRACT.md 仍是 WorkBuddy budget/profile 区分的唯一语义 owner
```

**未建立新的 budget owner。**

#### 16.8.2 A2 — 对齐 BOOTSTRAP_CONTRACT 措辞与已批准的区分

**独立核验（本轮实测）**：

```text
BOOTSTRAP_CONTRACT.md:25   含 "≤3,500 字符（预算 4,028 减安全余量）"
BOOTSTRAP_CONTRACT.md:46   含 "指针预算（≤3,500 字符）"
MEMORY_POINTER_CANDIDATE.md:5  含 "全文 ≤3,500 字符"
```

当前 canonical 文本仍含 "≤3,500 字符" 与 "预算 4,028 减安全余量" 式措辞，与本 Spec 已冻结的区分（`3500` = WorkBuddy profile 安全预算；`4028` = 历史观测截断点；`budget != truncation point`）冲突。

**修正**：在 `REQ-W4-01` / migration acceptance 中冻结**未来 S1 必须对齐的目标措辞**：

```text
3500 bytes  = 当前 WorkBuddy profile 安全预算
4028 bytes  = 历史观测到的实际截断点
3500 **不是**在数学上或规范上被定义为 "4028 减去某个隐含安全余量"
```

落点：`§3.4 REQ-W4-01`（「BOOTSTRAP_CONTRACT 措辞对齐（A2 修正）」块）；`§8.1`（`MIG-09` + 「预算值 vs 截断点」块补一句）。**不新增机制、不新增 profile 系统**；A2 **仅为 canonical 措辞同步**。

#### 16.8.3 A3 — 采纳既有 mechanical contract（新 references/*.md）

**独立核验（本轮读取 validator 源码）**：

```text
scripts/validate_governance.py:219-224
  # 7. references declare canonical owner
  for ref in sorted((ROOT / "references").glob("*.md")):
      if "Canonical owner" not in ref.read_text(encoding="utf-8"):
          owner_missing.append(ref.name)
  check("references-declare-canonical-owner", not owner_missing, f"missing={owner_missing}")
```

**缺陷**：`REQ-W2-01` 未来创建的 `references/review-evidence.md` 会被该 glob 命中；若不含字面 `Canonical owner`，`references-declare-canonical-owner` 检查将失败。此前 Spec 未显式声明这一既有约束。

**修正**：在 `REQ-W2-01` 接口一致性要求中新增**第 7 项**，并加入源码证据块，明确：

```text
references/review-evidence.md MUST satisfy all existing repository-wide
reference-file invariants, including the validator-required
"Canonical owner" declaration.
```

`AC-44` 同步扩为 **7 项**，第 7 项为：**新建 `references/review-evidence.md` 通过既有 `references-declare-canonical-owner` 检查（含字面 `Canonical owner` 声明），且未削弱或绕过既有 validator**。**明确不修改 validator 豁免新文件** —— 这是**采纳既有仓内不变量**，**不是**新治理机制。

#### 16.8.4 ROUND 4 保留项确认（未重开）

```text
Seam architecture                   保留（未动）
Runtime Reachability                保留（未动）
RED lifecycle                       保留（未动）
Review Evidence state model         保留（A3 只采纳既有 reference-file 不变量，不改状态模型）
trust boundary                      保留（未动）
reuse / invalidation                保留（未动）
CHECK_STATUS / CI_STATUS            保留（未动）
W4 owner split                      保留（未动）
core / live deny split              保留（未动）
W5 / GitHub enforcement             保留（未动）
3500-byte value itself              保留（本轮不改值，只补 change surface 与措辞对齐要求）
4028 observed value itself          保留（本轮不改观测值）
```

**未处理**（按指令排除）：其它 Tier-C observations、新 edge case、新 AC family。（`TEST_ONLY_CALLERS` 命名已于 §16.9.1 由 owner 裁定并关闭，不再是未处理项。）

#### 16.8.5 ROUND 4 新增未决项

```text
UNRESOLVED-09  AGENTS.md §10 最终采用 pointer（A）还是显式 derived summary（B），
              属 S1 实施时的措辞选择；本 Spec 已冻结"优先 A"与"不得成为第二 authority"
              两条硬约束，具体句式留待 S1 按 owner 决定。
```

### 16.9 ROUND 5 — OWNER 裁定 + 同根一致性修复

> 本节是 ROUND 5 的规范记录。触发是 owner 对 `TEST_ONLY_CALLERS` 命名的裁定；收敛范围限于该裁定本身及其**同根一致性**后果（R5-1 引用可解析性、R5-2 轮次账本登记），不扩张到已通过的其它面。

#### 16.9.1 OWNER 裁定：`TEST_ONLY_CALLERS` 不是 canonical 槽位

本节裁定由 project owner 作出，用于关闭 §16.8.4 记录为"未处理"的 `TEST_ONLY_CALLERS` 命名歧义
（即 `REQ-W1-03` 的引用清单**曾**渲染为七个名字、而 `REQ-W1-01` 落地分区声明为六个名字的 6-vs-7 分歧）。

```text
TEST_ONLY_CALLERS_STATUS               = DERIVED_DIAGNOSTIC_NOT_CANONICAL_SLOT
CANONICAL_OBSERVATION_FIELDS           = 6
  REAL_ENTRYPOINT / PRODUCTION_CALL_CHAIN / OBSERVED_PRODUCTION_EFFECT
  PRODUCTION_CALLERS / RUNTIME_REACHABLE / EVIDENCE_REF
SINGLE_DECLARATION_POINT               = REQ-W1-01（落地点 references/ticket-lane.md §3.1 分区 (1)/(2)；
                                         §3.1.1/§3.1.2 由 P1-T01 落地于 main）
REQ_W1_03                              = 消费上述六个槽位；不新增、不重声明
P1_T01_CONTRACT_RETROACTIVELY_EXPANDED = NO
NORMATIVE_BEHAVIOUR_CHANGED            = NO
```

裁定要点：

- canonical 关闭 / 观测字段集**恒为六个**，即 `REQ-W1-01` 已声明的六个 ② 类 observation 槽位；`REQ-W1-03` 只**消费**它们。
- `TEST_ONLY_CALLERS` **可以**作为**派生 / 诊断证据**使用（用于展示"存在测试调用者、但不存在生产调用者"），但**不得**成为：第二个规范声明点；新的 canonical observation 槽位；与 `REQ-W1-01` 并存的重复 owner；或追溯扩张已完成的 P1-T01 合同的理由。
- **行为要求不变**：仅测试调用者**不得**满足生产 reachability。该行为仍由既有 canonical 事实证明——`PRODUCTION_CALLERS`、`RUNTIME_REACHABLE`、`REAL_ENTRYPOINT`、`PRODUCTION_CALL_CHAIN`——外加常规测试 / 评审证据。
- 本裁定是**澄清**：不改变验收语义、不改变接口所有权、不改变已批准阶段顺序、不新增 AC family、不新增 authority 层。
- 受影响合同面：`REQ-W1-03` 的引用清单已在本 ROUND 5 内收敛为六个槽位。`P1-T03`/Issue #17 的草稿合同**仍渲染七个名字**；其校正**尚未实施**，须在本裁定获批后，按该票 `TICKET_CONFORMANCE_REVIEW = PENDING` / `IMPLEMENTATION_AUTHORIZED = NO` 的状态实施 —— 属 #17 自身的一致性条件，**不属**本 Spec 变更的完成条件。

#### 16.9.2 ROUND 5 同根一致性修复登记

```text
R5-1  引用可解析性   REQ-W1-03 清单与 §16.9.1 对 `references/ticket-lane.md` 的引用，
                     改为具名落地点（§3.1 分区 (1)/(2)，§3.1.1/§3.1.2 由 P1-T01 落地于 main），
                     并声明本 Spec 分支的 `references/` 快照可能早于该落地。
                     原因：原引用在本 Spec 分支自身树内不可解析（该分支无 §3.1 节）。
R5-2  轮次账本登记   补登 §0 头部、§15、§16.0 三处轮次账本，并把 ROUND 5 提为独立
                     `### 16.9`（原为嵌在 `### 16.8 ROUND 4` 内的 16.8.6）。
                     原因：追加提交后 §16.0 的 ROUND 4 行仍称"本文件当前内容"，
                     该陈述变为假；且 ROUND 5 未被任何账本记录。
```

两项均为**同根一致性**修复：不改变任何槽位集、验收语义、接口所有权或阶段顺序。

轮 1–3 的 `UNRESOLVED-01`..`08` 继续有效（合计 `UNRESOLVED-01`..`09`）。**均不阻塞 Spec 审查**：均为实现期/部署期变量，非 Spec 层权威冲突，且全部 fail-closed 处理。

---

### 16.10 ROUND 6 — `README.md` 纳入 REQ-W4-01 完整 change surface

> 本节是 ROUND 6 的规范记录。触发是 **P1-T09 / Issue #12 在 Stage-4 关闭时暴露的真实 change-surface 缺口**：其 `CLOSURE_EVIDENCE` 要求「仓库范围内不存在残留的字符预算语义」，而该搜索**无法干净通过**，因为 `README.md` 仍在两处保留「≤3,500 字符」。owner 裁定：**扩张已批准的 `REQ-W4-01` change surface 以纳入 `README.md`**，**不**采用「收窄 `AC-17` 第 5 项 / `MIG-07`」的替代方案。收敛范围限于该裁定本身及其**同根一致性**后果（同根：全部「四 surface」枚举的同步），不扩张到已通过的其它面。

#### 16.10.1 OWNER 裁定：`README.md` 是第五个 bootstrap-facing 收敛面

```text
FINDING                      F-B1
CLASS                        SPEC_CHANGE_SURFACE_GAP（incomplete change surface；INV-22 同类）
OWNER_DECISION               EXTEND_THE_APPROVED_CHANGE_SURFACE
ALTERNATIVE_REJECTED         NARROW_AC_17_COND_5_OR_MIG_07（不得收窄仓库级无残留要求）
COMPLETE_CHANGE_SURFACE      5 surfaces
  1  README.md（新增）          ← bootstrap-facing 派生消费者 / 运行时文档；非第二预算 authority
  2  AGENTS.md §10              （F-A1 纳入）
  3  deployment/BOOTSTRAP_CONTRACT.md        （唯一语义 owner —— 不变）
  4  deployment/MEMORY_POINTER_CANDIDATE.md
  5  scripts/validate_governance.py          （消费方）
README_TARGET_SEMANTICS      「≤ 3500 UTF-8 bytes」或等价的「指向 deployment/BOOTSTRAP_CONTRACT.md §2.1」措辞；
                             不得保留字符预算语义；不得自行声明预算值 / 单位 / profile 语义
BUDGET_VALUE_CHANGED         NO（WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES = 3500；UNIT = UTF-8 编码字节数）
TRUNCATION_POINT_CHANGED     NO（4028 bytes = 历史观测截断点；3500 **不是** "4028 减去隐含安全余量"）
AC_17_COND_5_NARROWED        NO（维持仓库级无残留要求）
MIG_07_NARROWED              NO（由「四个 surface」**扩为**「五个 surface」）
SEMANTIC_OWNER_CHANGED       NO（恒为 `deployment/BOOTSTRAP_CONTRACT.md`）
OTHER_W4_REQUIREMENTS        UNCHANGED（`REQ-W4-02a..e` / `REQ-W4-03` / `REQ-W4-04` 未重开）
W5_SCOPE_CHANGED             NO（`DEPLOYMENT_ONLY`，未重开）
```

裁定要点：

- `AC-17` 第 5 项与 `MIG-07` 的**仓库级无残留要求不变**。本 ROUND 6 **扩大**被要求收敛的 surface 集合，而非放宽判据：**任何** canonical / bootstrap-facing surface 保留「3500 字符」式的有效预算语义，仍等于未完成。
- `README.md` 是 **bootstrap-facing 的派生消费者 / 运行时文档**（其 §7.4 即 bootstrap 三件套；校验器把它列入 `REQUIRED_FILES` 与 `runtime_files`），**不是**第二预算 authority。它只可把预算表述为 `≤ 3500 UTF-8 bytes`，或指向 `deployment/BOOTSTRAP_CONTRACT.md` §2.1 的语义 owner。
- 本裁定是**范围扩张**，**不是**语义变更：预算值、单位、profile / override 语义、「`3500` ≠ `4028` 减安全余量」的区分，以及 W1/W2/W3/W5 的语义**全部不变**。
- 受影响 requirement：**仅** `REQ-W4-01`。未新增机制、未新增 profile 系统、未新增 AC family、未新增 authority 层（`INV-07`）。

**变更面实测证据（F-B1；本轮在 current main 上核验）**：

```text
README.md:487                     含 "≤3,500 字符"                        ← F-B1 残留冲突（此前未被审计）
README.md:540                     含 "≤3,500 字符"                        ← F-B1 残留冲突（此前未被审计）
AGENTS.md:138                     F-A1 面已收敛（该处已无字符预算语义）       ← ROUND 4 已纳入
BOOTSTRAP_CONTRACT.md:7/25/46     A2 面已收敛（byte 措辞 + 3500≠4028 区分）  ← ROUND 4 已纳入
MEMORY_POINTER_CANDIDATE.md:5     已收敛为 byte 语义                         ← ROUND 4 已纳入
scripts/validate_governance.py    已改为 UTF-8 编码字节长度度量               ← ROUND 4 已纳入
```

**F-A1 残留审计为何漏掉 `README.md`**：ROUND 4 的 F-A1 残留审计只覆盖它自己枚举的三个文件加 `AGENTS.md`，**从未审计 `README.md`**；因此该缺口在 ROUND 4 客观上不可能被发现，直到 P1-T09 的仓库级关闭证据搜索才暴露。本记录**保留该事实，不追溯改写 ROUND 4 的记录**。

**历史审计文档的处置**：`audit/AUDIT_QUALITY_REVIEW.md`、`audit/MIGRATION_PLAN.md` 中的「≤3,500 字符」属**历史审计证据**，**不在**本 change surface 内、**不重写**；`AC-17` 第 5 项针对的是 **current canonical / bootstrap-facing** surface。

#### 16.10.2 ROUND 6 同根一致性修复登记

```text
R6-1  四→五 surface 枚举同步   把全部「四个 surface / 四 surface / 4 个 surface」陈述同步为五个，
                             并把 `README.md` 加入枚举：
                               §3.4 REQ-W4-01「完整 canonical change surface」块（+ `README.md` 目标语义）
                               §3.4 授权边界「本轮不修改」文件清单（补 `MEMORY_POINTER_CANDIDATE.md`、`README.md`）
                               §4.1 Bootstrap 机制行（消费者：`AGENTS.md` §10 与 `README.md`）
                               §7 INTEGRATION_POINTS Bootstrap 预算行
                               §8.1 `MIG-07` 完整 change surface 枚举
                               §10.1a `REQ-W4-01` 行（写面 + 「五 surface 无残留」）
                               §10.2 `AC-17` 第 5 项括注（`AGENTS.md` §10、`README.md`）
                               §12 S1 core 行 + 「S1 写面提示」
                             原因：F-B1 把 change surface 由四个扩为五个后，上述陈述全部变为假。
R6-2  轮次账本登记             补登 §0 头部（`PRIOR_REVIEWED_SHA` / `REPAIR_HISTORY`）、
                             §15（`REPAIR_ROUND` / `REPAIR_SCOPE` / `NEXT`）、§16.0 轮次索引
                             （冻结 ROUND 5 行 + 新增 ROUND 6 行），并新增本节 `### 16.10`。
                             原因：ROUND 5 的教训——追加提交会使旧账本陈述变为假，须在同一提交内登记。
```

两项均为**同根一致性**修复：不改变任何预算值 / 单位 / 语义 owner / 验收判据宽度。轮 1–5 的 `UNRESOLVED` 项继续有效，**均不阻塞 Spec 审查**。
