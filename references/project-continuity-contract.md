# REF: Project Continuity Contract — PROJECT_CONTINUITY_CONTRACT_V1

> Canonical owner: AGENTS.md §7.1。contract_version = **1**。**运行时中立**：本合同对 WorkBuddy / ZCode / OpenCode / Codex / Hermes / 未来任何 Agent runtime 同规；各 runtime 的 hook/adapter 只是 reference implementation（ZCode 版见 `../adapters/zcode/README.md`），不是合同本身。
> 与 `project-state-persistence.md` 的分工：该文件承载**状态五分类 P0–P4 与 STATE_RESTORE / STATE_FLUSH 执行序列**（canonical 不变）；本文件在其上增加**固定机械入口、初始化语义、写入事件、远端持久化语义、CodeGraph 生命周期、grounding receipt、迁移与失败语义**。两文件互为指针，不重复权威。

核心原则：

```text
PROJECT_STATE_MUST_OUTLIVE_THE_AGENT
CONVERSATION_MEMORY_IS_CACHE_NOT_STORAGE
GLOBAL_CONTRACT_REMOTE
PROJECT_STATE_REMOTE
ONE_FACT_ONE_CANONICAL_OWNER
CODEGRAPH_INIT_ONCE_SYNC_CONTINUOUSLY
GROUND_BEFORE_MEDIUM_HIGH_WRITE
PERSISTENCE_VALUE
```

## 1. 固定项目状态索引（DURABLE RECOVERY INDEX）

每个 governed repository 拥有**全局唯一、可机械发现**的项目状态索引：

```text
<repo-root>/.agent/project-state.json
```

- 一旦确定，全局唯一位置；**任何项目不得自行发明不同路径**。
- Fresh Agent clone 任意项目后，机械寻找该文件即知这是 PROJECT_CONTINUITY_CONTRACT 的入口。
- Schema：`../schemas/project-state.schema.json`（normative shape）；模板：`../templates/project-state.json`（占位符形态，R2 兼容）。
- 校验器：`../scripts/validate_project_state.py`（对任意 repo-root 机械校验，exit 0/1）。
- **索引是 INDEX 不是 KNOWLEDGE DUMP**：不是聊天记录、不是 Agent 日记、不是第二套 Spec/Issue tracker/ADR 副本/MEMORY dump。只存 **pointers + recovery snapshot**，不重复全文。
- schema 至少表达：`contract_version / project_identity / remote / default_branch / canonical_documents(targets|specs|architecture|adrs|spikes|environment) / execution_control_plane / recovery_snapshot(last_verified_remote_sha|last_state_flush_reason|last_state_flush_at|legal_frontier_summary|blocker_refs|next_legal_action) / codegraph_policy`。

### 1.1 事实路由（ONE FACT → ONE CANONICAL OWNER）

```text
产品目标 / success boundary          → TARGET（canonical_documents.targets 指向）
已批准行为 / normative contract      → SPEC
架构选择 / alternatives / rationale  → ADR
技术未知 / experiment / evidence     → SPIKE
代码结构                             → source + architecture docs
真实重要 bug                         → regression test（优先）+ Issue/PR
当前 Ticket / Stage / PR / CI        → GitHub Issue / PR / tracker
恢复入口 / pointers / last snapshot  → .agent/project-state.json
machine-only runtime state           → local runtime state（绝不 commit）
跨项目工程制度                       → agent-engineering-governance 仓
```

禁止重复 authority；路由全表与状态分类见 `project-state-persistence.md` §1/§3。

## 2. 初始化合同（INITIALIZATION）

任何 Agent 进入 Git repo 后先判定：

```text
PROJECT_CONTINUITY_INITIALIZED = YES / NO
```

依据：`.agent/project-state.json` 存在且 schema/version 合法（校验器 PASS）。缺失 → adapter/runtime 注入 `PROJECT_CONTINUITY_INITIALIZATION_REQUIRED`，主 Agent 自动执行初始化（不问"要不要初始化"，这是全局默认）。

### 2.1 既有项目 — LAZY ADOPTION（默认）

**不批量迁移历史仓库。** 已有 repo 第一次在新合同下被 Agent 接管时：

```text
fetch remote → 读仓本地权威 → 发现既有 TARGET/SPEC/ADR/SPIKE 等
→ 发现 GitHub Issues/PRs → 重构当前项目状态
→ 创建 .agent/project-state.json（索引指向现有 canonical docs）
→ validate → commit → 授权允许时 push + remote verify
```

ADOPTION_MODE 铁律：**不重写历史、不重组既有文档、不制造第二套 Spec/ADR 体系**——只 discover / index / point / initialize / sync remote。

### 2.2 新项目 — 第一天即持久化

新项目在 repo created → remote established → default branch known 后**尽早**初始化（优先在第一次 meaningful implementation 前）：

```text
PROJECT_BOOTSTRAP：git init/remote → governance bootstrap → Project Continuity 初始化
→ .agent/project-state.json → CodeGraph init（code repo 一次）→ validate → first durable commit → push → remote verify
```

### 2.3 远端不可用 / 离线

```text
REMOTE_STATE_SYNC = DEFERRED：先本地初始化并 commit；
远端恢复后第一优先级 = push + remote verify。
禁止 REMOTE_UNKNOWN = REMOTE_SYNCED。
```

## 3. 写入合同（WRITE CONTRACT）

只在 **MEANINGFUL STATE TRANSITIONS** 写，不是每次工具调用、不是每条命令。触发事件至少：

```text
PROJECT_INITIALIZED, TARGET_CHANGED, SPEC_APPROVED_OR_CHANGED,
ADR_ADDED_OR_CHANGED, SPIKE_COMPLETED, ARCHITECTURE_BOUNDARY_CHANGED,
TICKET_STARTED, TICKET_BLOCKED, TICKET_REVIEWED, REPAIR_SHA_CREATED,
PR_CREATED_OR_UPDATED, REAL_CI_CLASSIFIED, INTEGRATION_ACCEPTED, MERGED,
REMOTE_VERIFIED, IMPORTANT_DEFECT_DISCOVERED,
IMPORTANT_DEFECT_FIXED_WITH_REGRESSION, ENVIRONMENT_RECOVERY_FACT_CHANGED,
MILESTONE_COMPLETE, HANDOFF, AGENT_SWITCH, SESSION_END, CONTEXT_PRESSURE
```

每次 transition 三问：`WHAT CHANGED? / WHO OWNS THIS FACT? / WOULD A FRESH AGENT MAKE A WORSE DECISION WITHOUT IT?`（PERSISTENCE_VALUE 判据，与 `project-state-persistence.md` §8 同源）。值得持久化时顺序固定：

```text
先写 canonical owner（TARGET/SPEC/ADR/Issue/回归测试…）
→ 再更新 project-state index 的 pointer / snapshot / last verified state
→ validate → commit → push → remote verify
→ 同步 GitHub Issue / PR / tracker（活跃执行状态属于 GitHub 时）
```

### 3.1 PROJECT_STATE_SYNC_RECEIPT（固定 machine-readable 回执）

```text
CONTRACT_VERSION = / PROJECT = / REMOTE = / LOCAL_HEAD = / REMOTE_HEAD =
EVENT = / CANONICAL_OWNERS_UPDATED = / PROJECT_STATE_INDEX_UPDATED =
TRACKER_SYNC = / PR_SYNC = / REMOTE_SYNC =
UNPERSISTED_IMPORTANT_CONTEXT = / NEXT_LEGAL_ACTION =
```

正常完成时 `UNPERSISTED_IMPORTANT_CONTEXT = NONE`。

## 4. STATE_RESTORE / STATE_FLUSH 接线

- **STATE_RESTORE**：禁止"请人讲历史"开局。序列 = governance bootstrap → fetch project remote → validate project-state contract → **读 `.agent/project-state.json`** → 读其指向的 TARGET/SPEC/ADR/SPIKE/架构 → Issues → PRs → branches → exact SHA → CI → 重构 legal frontier → 未决决策 → 输出 recovery receipt（字段见 `project-state-persistence.md` §5）。只有 persisted evidence 真的不足才问人。
- **STATE_FLUSH**：触发 = meaningful session end / agent·runtime·model switch / STOP / ticket completed / milestone / integration / context pressure / handoff / lane abandoned。核心问句：`WHAT DOES THE NEXT FRESH AGENT NEED THAT CURRENTLY EXISTS ONLY IN MY CONTEXT?` 高价值答案进入正确 canonical owner（序列见 `project-state-persistence.md` §6）。

## 5. 远端持久化语义（REMOTE IS REQUIRED, NOT OPTIONAL）

只写本地不算 complete。正常终态：

```text
LOCAL_DURABLE = YES / REMOTE_DURABLE = YES / REMOTE_VERIFIED = YES
```

远端暂时失败 → `REMOTE_STATE_SYNC = DEFERRED` + 留待同步事实 + 下次 SessionStart 优先处理；诚实语义见 `project-state-persistence.md` §7。

## 6. CodeGraph 生命周期合同

原则：`CODEGRAPH_INIT_ONCE / CODEGRAPH_SYNC_CONTINUOUSLY / NO_REDUNDANT_FULL_REINDEX`。机制协议（模式 A/B/C、真实工具能力）见 `codegraph-grounding.md`，本节是其生命周期外壳。

### 6.1 适用性

含 production source 的 governed repo 默认 `CODEGRAPH_APPLICABILITY = REQUIRED`；docs-only / 非 code repo 可 `NOT_APPLICABLE`，**但必须有机械依据**（不是"Agent 觉得项目小"）。

### 6.2 INIT — 至多一次

允许 full init 仅当：`INDEX_MISSING`，或 `CORRUPT / VERSION_INCOMPATIBLE` 且 rebuild 已明确授权。**禁止**以下触发 full init：SESSION START / BRANCH SWITCH / NEW TICKET / REVIEW ROUND / NEW WORKER。

### 6.3 SYNC — 增量、按需

健康 index + repository 变化 → `codegraph sync`（增量）；无变化 → `NO_SYNC`。分支切换 = 增量 sync，不是 init。

### 6.4 Runtime-local 状态（绝不 commit）

`GRAPH_DIRTY / LAST_SYNC_HEAD / LAST_SYNC_AT / GROUNDING_RECEIPT_RUNTIME_CACHE` 是 machine-local state，放 local runtime state root（ZCode 默认 `~/.zcode/runtime-state/`，其他 runtime 用等价本机位置），按 **repo realpath + worktree realpath** 隔离键。**绝不提交进 Git。**

### 6.5 Worktree 隔离

```text
repo
├── worktree A → 自己的 GRAPH_DIRTY / LAST_SYNC_HEAD / GROUNDING_RECEIPT
├── worktree B → …
└── worktree C → …
```

不得共享可变 dirty state（工具数据库每目录一库的既有事实见 `codegraph-grounding.md` §1）。

### 6.6 JIT sync（不是 per-edit sync）

```text
Edit Edit Edit → GRAPH_DIRTY（只标脏，不同步）
即将 CodeGraph query / independent review / blast-radius check / integration review / Stop
  时：if GRAPH_DIRTY → codegraph sync 一次
```

Stop 前若 `GRAPH_DIRTY = YES` 且 index 健康 → sync 一次；**sync 失败不得自动 fallback 到 full init**（fail → 如实报告 DEFERRED）。

## 7. GROUNDING（MEDIUM/HIGH 生产写前置）

- 任何 **MEDIUM / HIGH** 生产代码票在第一次 meaningful production write 前必须有 **GROUNDING_RECEIPT**（入 runtime-local state，绝不 commit），至少字段：

```text
TICKET = RISK = BASE_SHA = GRAPH_MODE = GRAPH_BASE_SHA = TARGET_SEAM =
DIRECT_TARGETS = UPSTREAM_PRODUCERS = CALLERS = CALLEES = DOWNSTREAM_CONSUMERS =
IMPACT = AFFECTED = STATE_OWNER = IDENTITY_OWNER = VALIDATION_OWNER =
EXPECTED_EDIT_SURFACE = OUT_OF_SCOPE =
```

回答五问：真正 owner 在哪？谁调用它/它调用谁？修改会炸到哪里？最小修改面是什么？哪里绝对不应该动？

- **Pre-write guard**：`RISK >= MEDIUM + production write + receipt missing` → `CODEGRAPH_GROUNDING_REQUIRED`（自动阻止/软阻止）。主 Agent 自行 `fresh graph → grounding → receipt → continue`，**不需要用户**。
- **MANUAL fallback**：CodeGraph 不可用 → `GROUNDING_MODE = MANUAL`（grep / AST / 仓内静态工具 / 定向阅读 / Relevant Surface Manifest）→ 产出 `MANUAL_GROUNDING_RECEIPT` → 继续。工具缺失不得永久阻塞（与 `codegraph-grounding.md` §4 Mode C 同规）。
- **Review 接线**：独立 reviewer 开工前必须知道 `GRAPH_FRESHNESS`；candidate-exact 与 `BASE_ONLY + DELTA_BY_DIFF` 不得混称（见 `codegraph-grounding.md` §2.1）。

## 8. 迁移与失败语义（MIGRATION / FAILURE）

- `contract_version < current`：区分 `SAFE_MIGRATION`（结构兼容 → 自动，不毁数据）与 `INCOMPATIBLE_MIGRATION`（→ 注入 `PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED`，**不静默毁旧数据**，等 owner 裁决）。
- Hook 永不阻塞会话启动/结束（fail-open exit 0）；hook 检测到的状态只注入提醒/阻止信号，语义修复由 Agent 按 canonical 协议执行。
- 校验器禁止项（同样进 validator）：secret-like 字段；committed 状态中的本机绝对路径。

## 9. Hook 语义（runtime-neutral；ZCode adapter 见 `../adapters/zcode/README.md`）

任何 runtime 的 adapter 至少提供四个小 hook（等价拆分合法，不做万能巨型 hook）：

| hook | 事件 | 强制行为 |
|---|---|---|
| governance sync | session start | 治理仓同步/状态检测（既有机制不变） |
| project state guard | session start | 检测 git repo → 校验合同 → 注入 `PROJECT_CONTINUITY_INITIALIZED` / `INITIALIZATION_REQUIRED` / `MIGRATION_REQUIRED` |
| graph/state dirty marker | 生产文件变更 | 只标脏：`CODEGRAPH_DIRTY` / `PROJECT_STATE_DIRTY`（不 per-edit sync） |
| durability guard | stop / transition | `PROJECT_STATE_DIRTY` 无 receipt → `DURABLE_STATE_SYNC_REQUIRED`；`GRAPH_DIRTY` → stop 前 sync 一次 |

- **HOOK 不写语义决策**：hook 可以发现"ADR changed / state dirty"，但绝不自行决定架构含义、用户决策、Spec 内容——这些由 Agent 写。Hook 只保证 **Agent 不能忘记写**。
- 有授权覆盖时 stop-gate 触发后 **AUTO-ADVANCE**（STATE_FLUSH → canonical owner → index → commit → push → tracker → remote verify），不问用户。
- Pre-commit/pre-push 拦截只有当 runtime payload 能可靠识别 `git commit`/`git push` 时才实现；否则 Stop/transition guard 已足够（不实现不可靠机制）。

## 10. 可发现性（GLOBAL REMOTE DISCOVERABILITY）

Fresh Agent 只需知道 `FlapPearLabs/agent-engineering-governance` 即可发现：本合同、schema、template、validator、CodeGraph 生命周期、hook 语义、ZCode adapter reference、测试。**不依赖**任何对话、MEMORY 或宿主 config 的隐含知识。

## 11. 反官僚（必须同读）

全局合同不得造成：逐命令日志 / 每 commit 强制 ADR / 每个小 bug 强制 Issue / 每 session 日报 / 每个想法进 PROJECT_STATE / 每 Edit sync CodeGraph / 每次启动 full index。判据 = `PERSISTENCE_VALUE`（`project-state-persistence.md` §8）；机制立 gate 前先过 R8 最小复杂性护栏。

## 12. 测试矩阵（canonical 证据）

- **PS1–PS15**（project state）：新仓初始化 / lazy adoption / TARGET·ADR 变更 / ticket·PR·CI·回归事件 / 只读会话不脏 / Stop 脏未 flush / 成功 flush / 远端不可用 / fresh Agent 仅凭 remote 恢复 / 合同版本升级 / 绝对路径拒绝 / secret-like 拒绝。
- **CG1–CG12**（CodeGraph）：健康无变更不 sync / 编辑标脏 / 重复编辑仍只脏 / 查询前 JIT sync 一次 / 缺 index 才 init / 已有 index 禁 init / 分支切换=增量 / sync 失败不 fallback init / 双 worktree 状态隔离 / MEDIUM 无 grounding 阻止 / 有 receipt 放行 / UNAVAILABLE → MANUAL fallback。
- **CROSS-AGENT RESTORE**：Agent A 初始化→产生状态→STATE_FLUSH→remote simulation；丢弃 A 的全部 context 后 fresh Agent B 仅凭 remote 恢复 target/canonical docs/current state/legal frontier/next legal action，不依赖人工重讲。
- 实现位置：`../adapters/zcode/tests/`（合成本地 synthetic repos，不触碰任何产品仓；CI 接入 `../.github/workflows/governance-ci.yml`）。
