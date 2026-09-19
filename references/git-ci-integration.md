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
