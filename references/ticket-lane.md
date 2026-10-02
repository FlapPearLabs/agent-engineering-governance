# REF: Ticket Lane — 单票生命周期、合同抽取与反例 TDD

> Canonical owner: AGENTS.md §3。风险矩阵在 AGENTS §3；本文件是**D 层默认**执行细节（仓政策可覆盖，记录 OVERRIDE）。

## 1. Lane 契约（默认；仓政策可定义例外）

```
ONE COHESIVE TICKET
ONE BRANCH
ONE ISOLATED WORKTREE（独立目录 / 独立的【查询+证据】生命周期——不是独立图库所有权，见 codegraph-grounding.md §2）
ONE ACTIVE WRITER（同一 reviewed candidate 不得并发变异；写者交接 = 前写者停止 → fresh fetch → 核验 remote tip → 重建状态 → 从 exact tip 继续）
```

- worktree 基于当前 remote master（或票声明的 authorized base SHA）创建；记录 `LANE_BASE_SHA`。
- 产物回写仅三类：feature branch commits、证据文件（lane 目录内）、tracker 更新（集成后）。

## 2. 读权威与 Relevant Surface Manifest

开工前构建（CodeGraph 辅助；不可用时手工，见 grounding §4）：

```
upstream producers / validators & canonicalizers / direct callers /
downstream consumers / persisted artifacts / state owners /
identity & provenance owners / error & failure propagation /
security & privacy propagation / sibling analogous modules /
adjacent ticket authority boundaries / stale-invalidation deps /
execution-infrastructure surfaces（见下）
```

**execution-infrastructure surfaces** —— 并行 lane 的写面冲突**不只**来自产品文件。
即使两张票的产品写面互不相交，它们仍可能同时需要修改**执行基础设施面**：

```text
CI workflow 的步骤 / job 清单
测试清单、套件登记索引、测试发现配置（含 snapshot / manifest 形式）
生成索引与 barrel 文件
任何"新增条目必须登记"的共享注册表（suite registry / fixture index / 路由表）
```

这类面有一个共同特征：**登记 ≠ 执行** —— 条目被写入登记文件，不代表它会被真实执行；反之亦然
（`REGISTERED != EXECUTED`）。因此两张票各自的"我只加了一行"都成立，合在一起却构成**同一文件的并发写**。

构建 surface manifest 时必须把这类面**单独列出**，按 §8 的 shared-file single-writer 处理，
**不得**因"产品行为互不冲突"而默认并行。

存在未知的重大仓库关系时不开始实质实现（先查清或 STOP）。LOW 票可裁剪为 surface 摘要。

## 3. Contract Extraction（MEDIUM/HIGH 必备字段块）

既有字段块（EXTEND 保留，不删除）：

```
INPUTS / OUTPUTS / PRECONDITIONS / POSTCONDITIONS
HARD_INVARIANTS / VALID_SUCCESS_CASES / FAIL_CLOSED_CASES
ALLOWED_FALLBACKS / FORBIDDEN_FALLBACKS
IDENTITY_DEPENDENCIES / PERSISTENCE_DEPENDENCIES
OWNERSHIP / OUT_OF_SCOPE
```

- 禁止静默把更富合同降级为方便的局部启发式；实现若改变 success/failure/valid/complete/identity/authority 的含义 → STOP（RULES R6）。
- LOW 票至少：INPUTS / OUTPUTS / OUT_OF_SCOPE 三行。
- 字段按**边界是否变化**触发，不按票字数或仅按 LOW 标签豁免；不要求所有票填写所有字段，不适用字段可 `N/A`（reachability 适用性另有判定规则，见 3.1.4）。

### 3.1 Seam 合同的两个分区（设计/权威要求 vs 关闭/观测证据）

seam 合同块由**两个显式标注、互不混写的分区**组成。本文件是 seam 合同字段的 canonical 声明面（canonical owner = AGENTS.md §3/§4）；**不新建第二 seam 权威文件、不新建 seam-map surface、不新增共享 enum**。

- 分区 (1)（设计/权威要求）：表达**要求什么**，拆票前由 authority/design 侧判定并**冻结**。
- 分区 (2)（关闭/观测证据）：记录**实际观测到什么**，实现完成后由执行侧产生。

两个分区之间的信息流是**单向**的：

```
PARTITION (1) IS FROZEN BEFORE TICKETING
PARTITION (2) ONLY FILLS THE SLOTS DECLARED BY (1)
CLOSURE_EVIDENCE_CAN_NEVER_REWRITE_A_REQUIREMENT
```

- 分区 (2) 的记录**只填充**分区 (1) 声明的槽位；若发现 (1) 的要求本身有误 → 走 authority / spec 变更流程，**不得**在关闭阶段就地改写要求。
- 分区 (1)/(2) 的字段名**不得同名**，也不得近似到需要 implementer 猜测；**禁止改名、禁止发明别名、禁止新增两个分区之间的同义词**。

#### 3.1.1 (1) DESIGN / AUTHORITY REQUIREMENTS —— 拆票前冻结

```
SEAM_ID / AUTHORITY_REF / CONTRACT_VERSION
PRODUCER / CONSUMER
SEMANTIC_OWNER / IDENTITY_OWNER / PERSISTENCE_OWNER / RETRY_OWNER / ERROR_OWNER
INPUT_CONTRACT / OUTPUT_CONTRACT
SYNC_OR_ASYNC / AWAIT_REQUIREMENT / LIFECYCLE_REQUIREMENT
LEGAL_STATES / ILLEGAL_STATES / FAIL_OPEN_OR_FAIL_CLOSED
MUST_FIELDS / MUST_NOT_FIELDS
EXPECTED_PRODUCTION_CALLER            # requirement：必须存在生产调用者（不是观测）
TEST_CALLER
EXPECTED_PRODUCTION_EFFECT            # requirement：期望的生产效果（不是观测）
REAL_SHAPE_FIXTURE_OR_ADAPTER
SEAM_COUNTEREXAMPLES                  # 反例定义（requirement，不是执行结果）
REACHABILITY_APPLICABILITY            # REQUIRED | N/A
REACHABILITY_APPLICABILITY_REASON     # 仅当 APPLICABILITY = N/A 时必填
REACHABILITY_APPLICABILITY_ACCEPTANCE_REF
                                      # 仅当 APPLICABILITY = N/A 时必填；
                                      # 指向 reviewer/integrator 的接受记录（引用槽位，不是结论）
REACHABILITY_REQUIREMENT              # 该 seam 必须被真实入口到达的规范声明
REACHABILITY_PROOF_OWNER              # 谁在关闭时提供证据（角色，不是结论）
RED_EXECUTION_OWNER                   # 谁在票内执行 RED（角色）
```

**唯一声明点规则**：`EXPECTED_PRODUCTION_EFFECT` HAS EXACTLY ONE NORMATIVE DECLARATION POINT —— 即上方分区 (1) 字段清单内的那一条。其它一切位置（本文件别处、其它 `references/*.md`、ticket 正文、测试断言、消费方文档）**只引用**该字段，**不得重复声明**同一规范事实。

```
# 声明点判定（机械可查）
DECLARATION = 该字段名作为字段条目出现在分区 (1) 的字段清单代码块内
REFERENCE   = 其它任何位置的提及（prose / 配对表 / 测试断言 / 消费方文档）
```

#### 3.1.2 (2) CLOSURE / OBSERVATION EVIDENCE —— 实现完成后产生

```
REAL_ENTRYPOINT / PRODUCTION_CALL_CHAIN
OBSERVED_PRODUCTION_EFFECT            # 实际观测到的生产效果（引用分区 (1) 的对应要求字段）
PRODUCTION_CALLERS                    # 实际生产调用者集合（可为空集）
RUNTIME_REACHABLE / EVIDENCE_REF      # 观测结论 / 证据引用
```

- 本分区**只声明 observation 字段**；不声明任何 requirement 字段，不复述 3.1.1 的唯一声明点规则，不新增要求语义。

#### 3.1.3 冻结配对表（design ↔ observation）

```
EXPECTED_PRODUCTION_EFFECT          ->  OBSERVED_PRODUCTION_EFFECT
EXPECTED_PRODUCTION_CALLER          ->  PRODUCTION_CALLERS
REACHABILITY_REQUIREMENT            ->  RUNTIME_REACHABLE
```

- 三个配对必须一眼可辨；**不得**把任一配对坍缩成一个名字，**不得**在两个分区之间共享字段名。
- 设计/观测同名或近似名（CE-29）→ 拒绝；冻结配对表是唯一解药。

#### 3.1.4 适用性判定规则（`REACHABILITY_APPLICABILITY`）

```
REACHABILITY_APPLICABILITY = REQUIRED | N/A
RUNTIME_REACHABLE          = TRUE | FALSE
REQUIRED  -> RUNTIME_REACHABLE 必须由分区 (2) 的关闭证据证明；无合法生产调用路径 => FALSE
N/A       -> 必须同时填写 REACHABILITY_APPLICABILITY_REASON 与 REACHABILITY_APPLICABILITY_ACCEPTANCE_REF
FAIL-CLOSED  MISSING_OR_EMPTY(REACHABILITY_APPLICABILITY_REASON)         => PROCESS_AS REQUIRED
FAIL-CLOSED  MISSING_OR_EMPTY(REACHABILITY_APPLICABILITY_ACCEPTANCE_REF) => PROCESS_AS REQUIRED
FAIL-CLOSED  WORKER_SELF_GRANTED_N/A                                      => CONTRACT_VIOLATION
FAIL-CLOSED  DUPLICATE_NORMATIVE_DECLARATION                              => CONTRACT_VIOLATION
FAIL-CLOSED  PARTITION_FIELD_NAME_COLLISION                               => CONTRACT_VIOLATION
```

- `REACHABILITY_APPLICABILITY` 合法值域只有 `REQUIRED | N/A`；`UNKNOWN` 不得冒充已冻结的适用性取值。
- `REQUIRED`：`RUNTIME_REACHABLE` 必须由分区 (2) 的关闭证据证明；无合法生产调用路径 → `RUNTIME_REACHABLE = FALSE`。
- `N/A`：**必须同时**具备 `REACHABILITY_APPLICABILITY_REASON`（为什么该 seam 不涉及 reachability，如纯文档、无生产入口语义变化）与 `REACHABILITY_APPLICABILITY_ACCEPTANCE_REF`（指向 reviewer / integrator 接受记录的引用槽位，不是结论）。
- **worker 不得单方自授 `N/A`**（`N/A` 来自合同适用性判定，不是 worker 快捷豁免）；任一槽位**缺失或为空** → fail closed，按 `REQUIRED` 处理。
- `RUNTIME_REACHABLE` 是**观测轴**，合法域固定为 `TRUE | FALSE`，与 `REACHABILITY_APPLICABILITY`（判定轴）不是同一个量。
- 纯文档等无边界的票可整体 `N/A`（须双槽位齐备）。

## 4. Counterexample-first TDD

链条：`CONTRACT → COUNTEREXAMPLES → RED → IMPLEMENT → GREEN → REFACTOR → REGRESSION`。

**证据标准**：
- `TEST_FILE_EXISTS != TDD_RED_PROVEN`；RED 必须由目标反例断言触发（MODULE_NOT_FOUND / harness 损坏不算 RED）；
- 证据区分 `TEST_FIRST` 与 `COUNTEREXAMPLE_SPECIFIC_RED`；
- 最低数量（仅对**承载正确性行为**的票）：MEDIUM ≥3；HIGH（持久化/状态/身份/安全/编排）≥5；LOW 无强制（有合同就必须有对应正/反测试）。

**高价值反例类目**（瞄准"看起来合理、过了显眼测试、仍违反合同"的实现）：
合法解被拒；非法输入变成功；约束被静默忽略；缺身份被当可复用；陈旧产物被接受；空结果当成功；重复身份破坏集合语义；malformed-but-coercible 被接受；排序/并列/边界失效；一项满足两个不同要求；合法上游输出违反下游合同；caller 控制数据泄入日志/产物；默认值掩盖缺失必需状态；实现越入他票权威。

**防伪**：禁止新增 skip、删断言、缩范围伪造绿灯。

### 4.1 Test-first defect closure（缺陷闭环，D4）

worker 或 reviewer 发现**真实可达缺陷**时，先问：`CAN_THIS_FAILURE_BE_CAPTURED_AS_A_STABLE_TEST?`

- **YES（默认路径）**：写/强化回归测试 → 观察失败（适用时）→ 修复 → 观察 PASS → **测试随修复保留**。可靠的回归知识住在测试里，不住在任何人的记忆里。
- 不为此制造低价值测试：无合同意义的实现细节；已被 formatter/linter 机械强制的行为；低价值合成态（REPAIR_VALUE 已裁定的 long-tail）。
- 测试应编码**有意义的行为知识**（回归、边界、fail-closed、producer/consumer 合同、持久化、身份/provenance、已知反例）。

**缺陷类机械化（与 §4.1 并列的第二条去向）**：当 `CAN_THIS_FAILURE_BE_CAPTURED_AS_A_STABLE_TEST?` 为 **NO**（机械可判、非行为知识）时，按 `references/static-analysis-and-code-intelligence.md` §21 评估**缺陷类**能否下沉到更低可靠机械层；**处置取值集合 = §21.3**（本节不重述、不缩写——重述即双 owner，同 §9 值域纪律）。回归测试**不得**被"能覆盖某个实现形状的 lint 规则"替换（框架 §19 保留）。

### 4.2 Test Engineering Contract

本节是测试工程契约与 reviewer checklist 的**唯一语义声明点**，约束 §4/§4.1 产生的测试质量：`TEST FAILURE KNOWLEDGE → REGRESSION TEST → HERMETIC TEST`。

**Fixture ownership + environment ownership**

- 测试拥有所需 files / directories / configs / temporary repositories / fake identities / generated fixtures：自行创建、管理并清理；使用仓内 tracked fixture 时明确声明输入。
- 不得依赖开发者 local files、碰巧存在的 ignored/untracked files、真实 credentials、真实 usernames/hostname、host-specific secrets，或开发者已有的 HOME/XDG、SSH 配置。测试主动在隔离目录创建并控制 ignored/untracked 场景是合法 fixture。
- **Environment ownership**：测试必须控制或显式声明会影响被测行为或断言的 ambient environment 边界，包括相关 environment variables、工作目录、HOME/XDG configuration、git configuration、PATH/toolchain、credential resolution、identity sources，以及相关 OS/locale/timezone。
- **只要求相关环境因素有归属**，不要求每个测试隔离所有可能环境。可控制的因素由测试设置/隔离/替换并恢复或清理；平台/工具链等运行条件可由仓库配置或 CI provisioning 显式声明并限定验证范围。声明不得把开发者私有状态变成合法前提。
- **Minimal environment 不等于 empty environment**：只供应必需输入，并隔离与测试无关的宿主状态。

**Category-specific clean checkout verification**

变化影响以下行为时，必须至少一次执行 **fresh checkout + minimal environment** 验证：

- Git state（含 index/worktree、分支、提交与 history）；
- tracked/untracked/ignored file discovery 与 filesystem discovery；
- release/publication behavior；
- environment/config resolution；
- credential behavior。

其它类别不普遍强制 clean checkout，由 reviewer 按相关环境依赖与风险决定。

验证使用 **exact candidate SHA** 的 fresh checkout，不复制开发者工作目录产物；控制相关环境输入，记录 command、SHA、environment boundary 与 result。**Clean checkout PASS 只证明该环境下执行的检查通过，不证明所有可能环境依赖都不存在。**

**Regression preserves the historical failure mode**

回归测试保留「什么条件触发 bug / 发生什么失败 / 现在必须满足什么合同」，不能只证明当前实现成功。在适用且可复现时，用同一测试与受控前置条件证明：

```text
Before fix: historical failure mode → RED
After fix:  contract satisfied      → GREEN
```

旧版本不能直接运行时，可在隔离副本中移除或绕过**相关修复机制**作为 negative control；它必须重现同一历史失败模式，不能用无关 mutation 引起的失败替代。对照不适用时说明具体原因与证据范围。

RED 必须由目标历史失败模式的断言触发。**导入错误、损坏的 fixture、harness 失败或无关失败，都不是回归覆盖证据。** 不得以空 fixture、缺失必需前提、仅验证 setup 的断言，或宿主已满足条件制造 GREEN；缺失必需前提应明确失败或报告验证受阻。

**Examples**

- 文件发现回归：测试在临时仓库创建配置与忽略规则，覆盖文件存在/不存在的场景；移除相关过滤修复后，由目标发现结果断言触发 RED，恢复修复后 GREEN。
- 身份回归：测试提供 fake identities 并控制身份/凭据解析来源，验证合法 synthetic fixture 与非法输入的行为；不读取开发者真实身份来决定预期结果，相关修复被移除时由目标合同断言触发 RED。

**Reviewer checklist（只在此声明）**

- □ fixture preconditions owned by test
- □ relevant ambient environment boundaries controlled or declared
- □ no undeclared developer-host dependency
- □ no local identity leakage
- □ mandatory clean-checkout categories identified and verified
- □ historical failure mode preserved; before-fix RED / after-fix GREEN or justified negative control demonstrated when applicable

## 5. 实现与自审

- `/implement` 是 MEDIUM/HIGH 实质实现的默认强制工程入口（LOW 不强制）；`/tdd` 在正确性行为存在时强制（不可测需客观理由）；`/simplify-code` 只在 GREEN 之后且不得改行为/合同（名称以本机 `SKILL.md` frontmatter `name` 为准，见 `references/skills-and-model-routing.md` §1）。
- skill 使用声明需可核验证据（被实际调用/读取），否则报 `UNVERIFIED`。
- 自审（/code-review 等）只是 worker 证据；**当独立评审 gate 存在时**（AGENTS §3 风险矩阵）不满足该 gate（RULES R4）。

## 6. Repair

- 只修 reviewer 指出的 blocker + 同 scope 内明确真实缺陷；append-only commit（RULES R5）。
- 新 SHA 触发失效链；delta 评审协议见 git-ci-integration.md §5。
- 修复轮次受 REPAIR_VALUE gate 与 budget 默认约束（review-and-repair-saturation.md §3）。

## 7. Live 状态持久化（P1）

Ticket/Lane 的活跃状态按 `references/project-state-persistence.md` §2–3 在**有意义转换点**持久化到 GitHub（Issue/PR/tracker：status/owner/SHA/评审/CI/blockers/next legal action）；离线时 `REMOTE_STATE_SYNC = DEFERRED` 且不声称远端已同步。票结束或会话离开前执行 STATE_FLUSH。

## 8. 共享文件单写者与最终回读（SHARED_FILE_SINGLE_WRITER）

> 本节是 shared-file single-writer + readback recipe 的 canonical 声明面（`REQ-W4-02c`；single owner = 本文件）。[execution-stage.md §2](execution-stage.md) 的 owner 冲突处置（合并为一票 / 显式串行集成链 / 拆 owner）**只引用本节**，不复述 recipe。本节是 §1 `ONE ACTIVE WRITER` 在共享写面上的**延伸**：不重新声明该 lane 术语，不改写 §1/§2 的读权威与 surface 规则。

多张票共享同一 canonical 文件时，"功能行为不同"不构成并行写权：

```
ONE ACTIVE WRITER -> expected entries -> single / serialised modification -> final readback -> every expected entry present
```

### 8.1 规则

- **同一 canonical 文件同一时刻只有一个活跃写者**；写者交接沿用 §1 的 ONE ACTIVE WRITER 交接序列（前写者停止 → fresh fetch → 核验 remote tip → 重建状态 → 从 exact tip 继续）。
- 动笔前先汇总各票的**预期条目**（expected entries = 各票打算对该文件作出的全部修改的**完整清单**）；兼容的修改**聚合为一次修改或显式串行的多次修改**，不得因"行为互不冲突"而默认并行施工。
- 写入完成后必须执行**最终回读**（final readback）：重新读取落盘结果，逐条确认**每一个预期条目**均已落盘；缺失任何一条即修改不完整。
- **编辑工具调用成功 ≠ 内容证据**：编辑器/工具返回成功永远不得被当作内容正确的核验；只有回读到内容才算证据。

### 8.2 状态合同

```
LEGAL    单写者 + 预期条目聚合（single / serialised modification）+ 最终回读确认每一个预期条目均已落盘
ILLEGAL  两个写者并发编辑同一 canonical 文件          -> REJECT（write conflict）
ILLEGAL  最终回读缺失任一预期条目                    -> REJECT（modification incomplete）
ILLEGAL  以编辑工具调用成功充当内容核验              -> REJECT（not evidence）
```

### 8.3 反例

- CE-17 共享文件多项预期更新中任一在最终回读时缺失 → 必须检出（modification incomplete）。
- CE-28 同一 recipe 在两个 canonical 文件重复定义（双 owner）→ 必须拒绝并收敛为单一 owner；其它 surface（含 execution-stage.md）只指针/链接，不重复定义。

## 9. STATIC_GATE_RECEIPT（票级静态门收据）

> 本节是 **STATIC_GATE_RECEIPT 的 canonical 声明面**（canonical owner = AGENTS.md §3；框架政策唯一详情 = `references/static-analysis-and-code-intelligence.md` §5–§20）。
> **状态值域不在本节重述**——取值集合与硬语义的**唯一声明点** = `references/static-analysis-and-code-intelligence.md` §8（STATIC GATE STATUS MODEL）。本节只声明收据**字段**，并**引用**该值域。重述值域 = 双 owner（同 §8.3 CE-28 处置）。

承载正确性或存在代码面的票（MEDIUM/HIGH；LOW 无强制）在 `SELF REVIEW` 之前产出：

```text
STATIC_GATE_RECEIPT

CHANGED_LANGUAGE_SURFACES =            # 本次 diff 实际触及的语言/代码面（来自 diff，不是来自猜测）

SYNTAX_OR_COMPILER =        <§8 状态值域>
FORMAT =                    <§8 状态值域>
LINT =                      <§8 状态值域>
TYPECHECK =                 <§8 状态值域>
DEEP_STATIC_ANALYSIS =      <§8 状态值域>
SCHEMA_CONFIG =             <§8 状态值域>

GIT_DIFF_CHECK =                       # 仓库全局机械门（diff 级：冲突标记/空白/路径/secret 扫描类）
STATIC_TOOLING_GAPS =                  # 期望能力缺失清单（无则 NONE）
BASELINE_COMPARISON =                  # 仅当某门为 KNOWN_BASELINE_FAILURE 或新采纳工具时需要
STATIC_GATES_COMPLETE = YES | NO
```

### 9.1 判定规则

- **不要求每个类别都是 PASS。** 例如未采纳静态类型的项目 `TYPECHECK = NOT_APPLICABLE` 合法；无 schema 的仓库 `SCHEMA_CONFIG = NOT_APPLICABLE` 合法。
- `STATIC_GATES_COMPLETE = YES` **不得**在以下任一情形成立：
  - 仓库**已配置**的适用工具被静默跳过（`CONFIG_FILE_EXISTS != GATE_EXECUTED`；AGENTS §ENGINEERING EVIDENCE ROUTING 的 configured-tooling 默认）；
  - 任一适用门处于 §8 值域中的**非 PASS**状态（`NOT_APPLICABLE` 除外）而未按 §8 语义务实上报；
  - `STATIC_TOOLING_GAPS` 非 `NONE`（即存在"该语言**有**廉价机械门、而本仓**未**配置"的**期望能力缺失**）——此时 `YES` 不成立，除非仓政策对该缺失留有显式 OVERRIDE 记录（RULES R1 的显式覆盖语义）。CE-31 是本项的直接反例：**如实**上报 `NOT_CONFIGURED` 也不能绕过"缺失期望能力"这一事实；
  - 仅有 `FORMAT = PASS` 而无任何正确性门（`FORMAT_PASS != LINT_PASS`）。
- `KNOWN_BASELINE_FAILURE` 只能以**提案**形态出现（RULES R3）；接受权在独立侧。
- `BASELINE_COMPARISON` 是**新工具采纳或基线类失败**的必需伴随证据：记录 `BASELINE_COMMAND` / `BASELINE_FINDINGS` / `FINDING_CLASSES` / `ADOPTION_COST`，落地形态 = `references/static-analysis-and-code-intelligence.md` §13。
- 收据是**证据**，不是判定权：它不替代 RULES R4 的独立评审 gate，也不使静态门的绿灯升级为语义/合同结论。

### 9.2 反例

- CE-30 仓库配了 ESLint，但收据里 `LINT` 直接写 `PASS` 而没有执行证据 → 必须拒绝（`LINTER_CONFIGURED != LINTER_PASSED`）。
- CE-31 适用语言有廉价语法门但收据写 `NOT_CONFIGURED` 却仍标 `STATIC_GATES_COMPLETE = YES` → 必须拒绝。
- CE-32 只有 `FORMAT = PASS` 就声明静态门完成 → 必须拒绝（`FORMAT_PASS != LINT_PASS`）。
- CE-33 把 `ENV_BLOCKED` 记为 `PASS` / 在摘要中省略 → 必须拒绝（`ENV_BLOCKED != PASS`）。

### 9.3 FAST_GATE_RECEIPT / FULL_GATE_RECEIPT（执行类别收据）

> 分类语义与边界的唯一声明点 = `references/static-analysis-and-code-intelligence.md` §10.1；CI 侧执行 = `references/git-ci-integration.md` §3。本节只声明**票级字段**，并**复用 §9 已有的状态值域**（不另立一套 PASS 语义）。

`FAST_GATE_RECEIPT`（在 `SELF REVIEW` 之前产出；类别值域 = §8）：

```text
FAST_GATE_RECEIPT

SYNTAX_COMPILER =         <§8 状态值域>
LINT =                   <§8 状态值域>
TYPECHECK =              <§8 状态值域>
SCHEMA_CONFIG =          <§8 状态值域>
REPO_STATIC_VALIDATORS = <§8 状态值域>
GIT_DIFF_CHECK =         <§8 状态值域>
FOCUSED_TESTS =          <§8 状态值域>

FAST_GATE_COMPLETE = YES | NO
NON_PASS_ITEMS =         # 逐项列出上表中的非 PASS 项及证据；无则 NONE
```

- `FAST_GATE_COMPLETE = YES` **不得**在任一适用项非 PASS 且未按 §8 语义务实上报时成立；`NOT_APPLICABLE` 合法（如无类型系统的语言 `TYPECHECK = NOT_APPLICABLE`）。
- `FAST_GATE_COMPLETE = YES` **不等于**集成证据充分（`FAST != FULL`，框架 §10.1）。

`FULL_GATE_RECEIPT`（**仅当**当前证据架构因显式收据而受益时才要求；否则可用等价证据形态并显式 OVERRIDE 记录）：

```text
FULL_GATE_RECEIPT

FULL_TESTS =             <§8 状态值域>
INTEGRATION =            <§8 状态值域>
CROSS_PLATFORM =         <§8 状态值域>
HISTORICAL_COMPAT =      <§8 状态值域>
EXPENSIVE_SECURITY_STATIC = <§8 状态值域>
RELEASE_GATES =          <§8 状态值域>

FULL_GATE_COMPLETE = YES | NO
```

- **不**强制每个项目填满每个类别；`NOT_APPLICABLE` 是合法取值。
- `FULL_GATE_COMPLETE = YES` **不**抹掉 `FAST_GATE` 阶段的失败（框架 §10.1 双向不豁免）。

### 9.4 DEFECT_PROMOTION_RECEIPT（缺陷类晋升收据）

> 判定模型与处置值域的唯一声明点 = `references/static-analysis-and-code-intelligence.md` §21.1/§21.3。本节只声明字段。

在 reviewer / CI / 测试发现**有意义**缺陷后按比例产出（**不**要求为每个 typo 或琐碎 finding 产出）：

```text
DEFECT_PROMOTION_RECEIPT

DEFECT_CLASS =              # 稳定语义类目
CURRENT_DEFECT_FIXED = YES | NO
MACHINE_DETECTABLE = YES | NO | UNCERTAIN
EXISTING_MACHINE_OWNER =    # 已有的机械归属；无则 NONE
BEST_DURABLE_OWNER =        # §21.2 层级中的最便宜可靠层
PROMOTION = <§21.3 处置值域>
RATIONALE =
```

- `PROMOTION` 的取值集合与硬语义的**唯一声明点** = `references/static-analysis-and-code-intelligence.md` §21.3；本节只**引用**，不缩写、不重述（缩写即双 owner，同 §9 值域纪律）。
- 本收据是**分类证据**，**不**自动创建门、不自动开票、不扩当前票 scope（框架 §21.3；RULES R6）。
- `PROMOTION = PROMOTE_NOW` 只在框架 §21.3 的本票内允许条件**全部**满足时才成立；否则 `FOLLOWUP_TOOLING_TICKET`。
