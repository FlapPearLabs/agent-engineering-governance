# REF: Git / CI / Integration — 证据块、merge gate 与串行集成（默认协议）

> Canonical owner: RULES.md R3/R5 + AGENTS.md §6。本文件是 **D 层默认**：所有 merge/CI 形态条款均可被仓库本地政策（C 层）显式 OVERRIDE；不可覆盖的是 RULES R3（证据真实性）与 R5（reviewed/published 历史不被静默改写）。

## 1. 分支与提交（默认）

- 一票 = 一分支 = 一隔离 worktree（**默认**；微小机械修复/共享迁移等场景仓政策可定义例外）。
- 分支基于最新 remote master；默认禁止 master 直接施工；scope-clean commits。
- Conventional Commits（`feat/fix/docs/test/refactor/chore`）；凭据、临时产物、runtime memory 不提交。
- 署名约定：AUTHOR_NAME=`FlapPearLabs`、AUTHOR_EMAIL_CLASS=`GITHUB_NOREPLY`（执行点 = 仓 repo-local git config）。

## 2. Merge 方法（C 层决定，D 层默认）

- **默认**：ff-only 集成、master 串行（任一时刻至多一个 Integrator）。
- **仓库政策可覆盖**：squash / merge commit / rebase-based 流程均为合法集成形态——此时 B 层不变量仍适用：被评审的候选分支不得被静默改写（R5），且 PR/评审记录必须保留 reviewed SHA 与最终集成产物的对应关系。
- 每次集成前重新执行：fresh fetch → `origin/<branch> == REVIEWED_HEAD`（若分支未被 squash 类方法改变语义）→ master drift 检查 → 按**仓政策**执行 merge → push → remote verify → 关 tracker。
- `MASTER_DRIFT != CONTENT_CONFLICT`：前者是机械时序条件（re-form + fresh review），后者才走 STOP 裁决。
- 无损恢复（refs 丢失/损坏）：优先使用仓库自带恢复流程；无仓库流程时 STOP 求裁决，不得用 `reset --hard`/`clean -fd` 猜测性修复**已评审/已发布对象**；对可弃的一次性 worktree（未评审、未推送、可重建）的清理不受此限。

## 3. CI 语义（诚实性 = R3，不可豁免；形态 = 可覆盖默认）

- 默认要求：MEDIUM+ 票集成前存在 **real PR CI** 证据；`LOCAL_TESTS != REAL_PR_CI`。
- **仓政策可 OVERRIDE**：无 CI 基础设施的仓可定义等价证据形态（如确定性本地套件 + reviewer 现场执行 + remote 核验），必须显式记录为 OVERRIDE。
- 状态集（不可坍缩）：`PASS / FAIL / NOT_TRIGGERED / CANCELLED / INFRASTRUCTURE_FAILURE / KNOWN_BASELINE_FAILURE / UNKNOWN`。
- 永不成立：`NOT_TRIGGERED = PASS`、`UNKNOWN = PASS`、`KNOWN_BASELINE_FAILURE = PASS`、`SKIPPED = PASS`。

### 3.1 非 PASS 通用证据块（R3 强制）

```
CI_STATE / CI_TRIGGERED / CI_RUN_ID_OR_URL / CI_OBSERVED_AT /
CI_FAILURE_SIGNATURE / RETRY_PERFORMED /
CI_BLOCKER_CLASS (CANDIDATE|BASELINE|INFRASTRUCTURE|AUTHORIZATION|SCHEDULING|UNKNOWN) /
REVIEWER_ACCEPTED_CLASSIFICATION / REQUIRED_NEXT_ACTION
```

### 3.2 KNOWN_BASELINE_FAILURE 附加 9 字段（加法不减法）

```
CANDIDATE_CI_TRIGGERED / CANDIDATE_FAILURE_SIGNATURE / BASELINE_REPRODUCED /
BASELINE_SHA / BASELINE_FAILURE_SIGNATURE / SIGNATURE_MATCH /
CANDIDATE_CAUSED_FAILURE / CI_CLASSIFICATION / REVIEWER_ACCEPTED_CLASSIFICATION
```

- Worker 分类 = PROPOSAL_ONLY（R3）。自动化评审不可用（配额/故障）= `UNAVAILABLE`，不是 PENDING，也不得静默豁免 gate——按仓政策路由到指定独立评审。

## 4. Scope 核验（L0；语义优先）

- 默认校验 = **语义 scope**：changed files 落在票声明的行为范围 / expected surface 内。
- 实施中涌现的支撑文件（测试/fixture/生成物/缝支撑）不是自动违规——需在票据包中有 justification 行并经评审确认（RULES R6）。
- 仅当票**明确冻结了文件清单**时，才执行子集校验。
- 触及 wiring / registration / composition / entrypoint 的票：语义 scope 包含「真实入口 → 变更缝 → 生产效果」这条链；模块级 / 内部测试证据本身不构成 scope 关闭（集成关闭条件见 §5.1）。
- 附带机械检查：`git diff --check` clean；无凭据/机器私有路径混入。

## 5. Exact-SHA 评审协议

- PASS 绑定 exact SHA（R5）；code-changing repair → 新 SHA → 适用 gate 新鲜重审。
- 新鲜 ≠ 重读全仓：blast radius 未扩张时 = previous reviewed SHA + delta（diff + `impact` 爆炸半径 + 权威对照）。
- AUTO_ADVANCE 集成序列见 AGENTS §2/§7；Stage 内集成顺序 = STAGE_MANIFEST 声明顺序。

### 5.1 集成关闭证据（INTEGRATION CLOSURE EVIDENCE）

集成票不得仅凭模块级 / 内部测试证据关闭：关闭需要 REAL_ENTRYPOINT -> PRODUCTION_CALL_CHAIN -> OBSERVED_PRODUCTION_EFFECT 的观测链，或一条显式的「集成未完成」声明（INTEGRATION_COMPLETE = FALSE）。

槽位清单（按引用消费 `REQ-W1-01`，单一声明点 = `references/ticket-lane.md` §3.1.2，此处只引用、不在此重声明）：`REAL_ENTRYPOINT` / `PRODUCTION_CALL_CHAIN` / `OBSERVED_PRODUCTION_EFFECT` / `PRODUCTION_CALLERS` / `RUNTIME_REACHABLE` / `EVIDENCE_REF`；`RUNTIME_REACHABLE` 的取值域同样按引用取自 `references/ticket-lane.md` §3.1.4。

```text
REAL_ENTRYPOINT            -> 真实入口：生产可执行入口，不是测试入口
PRODUCTION_CALL_CHAIN      -> 真实入口到变更缝的调用链
OBSERVED_PRODUCTION_EFFECT -> 生产侧实际观测到的效果（引用分区 (1) 的对应要求字段）
PRODUCTION_CALLERS         -> 实际生产调用者集合（可为空集）
RUNTIME_REACHABLE          -> 运行期可达性观测结论（取值域引用 references/ticket-lane.md §3.1.4）
EVIDENCE_REF               -> 证据引用槽位
```

关闭条件（本节与 §4 的语义 scope 共同构成集成关闭判定）：

```text
CLOSURE-REQUIRED      触及 wiring / registration / composition / entrypoint 的集成票必须有 REAL_ENTRYPOINT -> PRODUCTION_CALL_CHAIN -> OBSERVED_PRODUCTION_EFFECT 的观测证据；模块级 / 内部测试证据本身不构成关闭，直接调用内部模块的测试不能单独满足本条
DISCONNECTED          生产入口断开（ENTRYPOINT_DISCONNECTED）时，模块级 / 内部测试全绿也不得关闭该集成票
DYNAMIC-PATH          合法的动态注册 / 插件 / 回调路径不得被拒绝：不得用直接调用的静态计数作最终裁决，允许用合法的运行期证据替代对直接调用的文本 grep；静态计数只是派生 / 诊断证据
TEST-CALLER           测试调用者不是生产调用者：仅测试调用者永不满足生产 reachability；TEST_ONLY_CALLERS 若出现只是派生 / 诊断证据，不是 canonical observation 槽位
NO-CALLER-PATH        REQUIRED 可达性下不存在合法生产调用者路径 => RUNTIME_REACHABLE = FALSE 且 INTEGRATION_COMPLETE = FALSE（永不判绿）
N/A-PATH              N/A 票不通过本条证据路径关闭，仍须满足 REACHABILITY_APPLICABILITY_REASON 与 REACHABILITY_APPLICABILITY_ACCEPTANCE_REF（引用 references/ticket-lane.md §3.1.4）
```

- 关闭结论绑定 exact SHA（§5 上文）：`RUNTIME_REACHABLE = TRUE` 必须有真实入口、调用链与已观测效果；`FALSE` 必须附显式的集成未完成声明。仅测试调用者永不满足生产 reachability。

### 5.2 破坏性工作区事务（DESTRUCTIVE_WORKSPACE_TRANSACTION）

本节是 destructive workspace transaction recipe（`DESTRUCTIVE_WORKSPACE_TRANSACTION`）的**唯一规范声明点**：canonical owner = 本文件（`references/git-ci-integration.md`）。其它 surface 只指针 / 链接、不重复定义该 recipe（CE-28）；唯一声明点规则本身按引用取自 `references/ticket-lane.md` §3.1，此处不重述其定义。consumer = 执行破坏性工作区动作的 ticket worker 与 reviewer。

适用面**仅限破坏性动作**（会丢弃工作区状态的动作：`clean` / `reset` / 强推前分支清理 / `stash drop` / 删除未评审产物等）；非破坏性的读取、构建与普通提交不触发本节。

有序事务（**顺序不可交换、不可跳步**）：

```text
status -> uncommitted / untracked / owner -> preserve -> operate -> post-state
```

- 逐步语义：`status` 读取并留存现场事实（pre-state 记录）；`uncommitted / untracked / owner` 步识别未提交修改、未跟踪产物**及其 owner**（属于哪个 lane / 哪个任务）；`preserve` 保全；`operate` 执行动作；`post-state` 记录操作后的状态。
- **基线优先**：破坏性动作**优先**在一个独立、干净的 worktree 上建立基线（preferred baseline = independent clean worktree），它不是唯一合法形态；不得在未识别未提交 / 未跟踪产物的现场直接执行破坏性动作。
- **lane 隔离**：**绝不**触碰其它 lane 的工作——其它 lane 的 worktree / branch / 未提交产物 / 未跟踪产物都不在本事务的操作面内；跨 lane 清理 = 越权，直接拒绝。
- **tracked 修改**：`preserve` 步骤**不得丢失 tracked 修改**；无论该丢失静默与否（silent or announced）都不豁免——发生即 reject，不是 warning，也不得降级为提示。
- **untracked 产物**：`preserve` 步骤**不得丢失 untracked 产物**；无论该丢失静默与否（silent or announced）都不豁免——发生即 reject，不是 warning，也不得降级为提示。
- **pre-state 记录是事务的一部分**：破坏性操作若没有记录 `pre-state`，该事务**无效**（invalid），不得据此声明操作完成。
- **post-state 是事务的一部分**：破坏性操作若没有记录 `post-state`，该事务**无效**（invalid），不得据此声明操作完成。
- **不建立全局 stash 禁令**：本 recipe 不构成 blanket / global stash prohibition，且在其它 surface 上也不得被读成一条通用禁令。
- **底层因果按事实记录、不推广**：被记录下来的真实失效原因是 `NEEDS_PRIMARY_EVIDENCE_RECOVERY`（primary-evidence recovery need）；该因果只作为**记录**存在，不升格为规则（父 Spec §4.3 的对应 non-decision = `REJECTED_WITH_REASON`）。
- **接地（grounding）**：pre-state 义务取自父 Spec §10.1a 的可观测 `保全前后状态记录`（`REQ-W4-02b`，spec 行 1045）；无条件保全丢失拒绝取自父 Spec §9 `CE-16`（spec 行 982）与 §10.2 `AC-14`（spec 行 1115）——两者均为**无条件**，不得被读成以「丢失是否被声明」为前提。

状态合同与错误语义：

```text
LEGAL    destructive action with a recorded pre-state + preserved set + recorded post-state
ILLEGAL  destructive action without preservation
ILLEGAL  destructive action without a pre-state record
ILLEGAL  destructive action without a post-state record
ILLEGAL  blanket / global stash prohibition presented as a rule
CE-16    preservation loses a tracked modification or an untracked artefact -> REJECT
CE-28    the recipe is declared in a second canonical file (dual owner) -> REJECT and converge
```

- 本小节与 §5.1 的集成关闭证据互不重叠：§5.1 的字段与规则由 P1-T03 拥有，本节不重述、不改写，只在其之外新增破坏性工作区事务的适用面、有序步骤与状态合同。

### 5.3 证据生命周期消费（EVIDENCE LIFECYCLE CONSUMPTION）

本节是证据复用 / 失效生命周期**消费行为**的规范声明点（canonical producer = 本文件，父 Spec §10.1a `REQ-W3-03` 行）；机械形态 = `scripts/review_evidence.py` 的生命周期检查（P1-T08），折叠进既有 `validate` 流程。复用依赖描述符的**形状**（五字段闭结构，含依赖身份字段与核验状态闭合值域）由 `schemas/review-evidence.schema.json` 的 `reuse_dependency_descriptor` **唯一声明**，语义详情见 `references/review-evidence.md` §5——本节只**引用并消费**该形状，不重述字段名清单、不改名、不建第二生命周期（`references/execution-stage.md` 的证据复用条即引用本节；CE-28 / CE-30）。

#### 五类证据的独立有效期绑定（REQ-W3-01；INV-06）

**不统一成"任何 HEAD 前进则所有 receipt 失效"。** 分别保持：

```text
reviewer PASS   绑定原 exact SHA（RULES R5）；旧 PASS 永不改名为新候选 SHA 的全量 PASS
CI              绑定真实运行检查的 SHA 与对应 jobs（CI 语义与状态集按引用取自本文件 §3，
                其闭合集仍由 references/review-evidence.md §4 唯一声明，此处不重述、不扩写）
grounding       服从既有 base / ancestry / mode / freshness 合同（codegraph-grounding.md §2.1）
durability      服从既有 current-HEAD / meaningful-transition 合同
测试证据        绑定实际输入、代码、配置、环境与测试范围
```

证据复用必须绑定候选身份与依赖；跨 SHA 不得全量继承（INV-06）。

#### 复用合法性（REQ-W3-02；AC-31 / AC-32）

```text
LEGAL    每条依赖描述符的核验状态为 VERIFIED，且整条复用声明具有有界 VALID_FOR 范围
         → 在该声明范围内允许复用（正向对照 AC-31）
ILLEGAL  任一依赖描述符核验状态为 UNKNOWN 而复用被声明 → 拒绝：
         须重跑所需范围或请求必要证据，绝不默认复用
ILLEGAL  复用被声明而描述符形状不合法（含自由文本、缺必需键）→ 拒绝（结构层 + 行为层双重拒绝）
ILLEGAL  复用被声明而 VALID_FOR 为空（范围无界）→ 拒绝
ILLEGAL  复用被声明而未标识来源证据 → 拒绝（缺来源 = 缺必需证据，不得当作 PASS，CE-07）
```

#### 失效触发清单（REQ-W3-03；AC-33 / AC-34）

四项触发（**canonical 声明点 = 本清单**；机械形态 = 消费方对描述符 `INVALIDATED_BY` 记录与声明级 `invalidation` 记录的触发匹配）：

```text
T1  master drift
T2  共享 schema / 共享依赖变化（shared schema or shared dependency change）
T3  入口拓扑变化（entry topology change）
T4  authority / profile / toolchain 相关变化（authority profile toolchain change）
```

命中 → **定向**失效：只有其失效记录命中该触发的那部分依赖描述符所指的证据范围失效，须**定向重取**（AC-33 / CE-11）；**未命中**的依赖与其余证据**保持可复用**。无关变更触发全量重做本身是缺陷（CE-12 / AC-34）；把任何 HEAD 前进当作一次性作废全部 receipt 被无条件禁止。

#### subject commit 与 report commit（REQ-W2-07；AC-37）

二者是**两个不同身份**：subject candidate SHA 保持显式；report commit SHA 独立记录。新增报告提交**不得自动继承**旧 reviewer PASS——评审结论绑定其原 exact SHA，报告提交改变 HEAD 不改变已评审对象；不存在 candidate-SHA ↔ report-SHA 的无限追逐循环（不为把含 candidate SHA 的证据提交进候选仓而破坏 candidate 身份）。

#### 机械消费边界

生命周期检查在判定顺序中位于结构层、subject 绑定、P1-T05 三轴处置与 P1-T06 取回边界**之后**；不新增 CLI 模式（公开 argv surface 恒为 `collect` / `validate`），不新增信封键，失败条目走既有 `violations` 清单，其 reason 词表与结构类 / 声明类 / 调用类 / 处置类 / 边界类**互不相交**。占位符模式与 P1-T05 处置同样豁免生命周期检查（占位符形态模板不是对一个具体候选的复用主张）；取回边界照常运行。描述符的必需键集与核验状态值域由 CLI **从已加载合同运行时读取**，不在代码中重述（单一声明点纪律）。触发匹配是对声明记录的定向判定，不是对本清单的第二声明；定向失效的这一半由调用方提供的 `hit_triggers` 观测输入驱动——本 CLI 自身不消费任何外部观测，故 `REUSE_SCOPE_INVALIDATED` / `REUSE_CLAIM_INVALIDATED` 只对具备可观测性、按声明传入该观测流（the declared observation feed）的调用方可达，而 UNKNOWN / 形状不合法 / 来源合法性检查在**每一次** `validate` 上运行。
