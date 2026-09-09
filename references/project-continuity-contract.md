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

- **STATE_RESTORE**：禁止"请人讲历史"开局。序列 canonical = `project-state-persistence.md` §5（14 步）；本合同在其上**只加一步**：在"读仓本地权威"之后插入 **validate project-state contract → 读 `.agent/project-state.json`**，并按其 pointers 调整后续阅读顺序。其余（Issues → PRs → branches → exact SHA → CI → legal frontier → recovery receipt 字段）以 persistence §5 为准，不在此重复。只有 persisted evidence 真的不足才问人。
- **STATE_FLUSH**：触发清单与问句 canonical = `project-state-persistence.md` §6（`WHAT DOES THE NEXT FRESH AGENT NEED THAT CURRENTLY EXISTS ONLY IN MY CONTEXT?`）；本合同补充：flush 产生的 receipt 字段见 §3.1，且 flush 后必须刷新 index 的 recovery snapshot（时点证据，见 §8）。

## 5. 远端持久化语义（REMOTE IS REQUIRED, NOT OPTIONAL）

只写本地不算 complete。正常终态：

```text
LOCAL_DURABLE = YES / REMOTE_DURABLE = YES / REMOTE_VERIFIED = YES
```

远端暂时失败 → `REMOTE_STATE_SYNC = DEFERRED` + 留待同步事实 + 下次 SessionStart 优先处理；诚实语义见 `project-state-persistence.md` §7。

**评审修正 R3（F5/F6，2026-09-07）**：

- **F5 远端持久化是三级阶梯，不得折叠成"完成"**：`LOCAL_DURABLE → REMOTE_PUSHED → REMOTE_VERIFIED`。`record-state-sync` 产出 `remote_durability` 凭据，必须绑定 `HEAD_SHA` + 时间戳；此后任何新 meaningful transition（dirty 置位或 HEAD 前移）都使旧凭据失效（R5-F6：一律 `REMOTE_RECEIPT_INVALID`，fail-closed）。Stop guard 在 remote-backed 项目的合法终态只有两种：`REMOTE_VERIFIED = YES` 或 `REMOTE_STATE_SYNC = DEFERRED`；仅有 LOCAL_DURABLE / REMOTE_PUSHED → `REMOTE_VERIFICATION_REQUIRED`。**未配置 remote 的受管 repo，Stop 同样不是 PASS**（R5-F4：`REMOTE_REQUIRED`）。环境 flush marker（`STATE_FLUSH_COMPLETED=1`）**必须**经 `STATE_FLUSH_HEAD_SHA` 绑定当前 HEAD 且无更新 transition 才被信任；未绑定/过期 marker 一律落穿重估（`UNBOUND_FLUSH_MARKER` / `STALE_FLUSH_MARKER`），且 marker 只是证据、永不 early-return 绕过其余 durability 检查（R4-A2）。
- **R4-A1 DEFERRED 失败凭据权威**（2026-09-07）：`REMOTE_STATE_SYNC = DEFERRED` 不得由裸 `--deferred` 无证据产生——必须绑定一次真实 remote failure receipt（至少 `HEAD_SHA` / `REMOTE_OPERATION` / `FAILURE_CLASS` / `ATTEMPTED_AT`，CLI flags：`--head` / `--remote-operation` / `--failure-class` / `--attempted-at`）；缺证据 → 命令拒绝（`REMOTE_DEFERRED_EVIDENCE_REQUIRED`，rc=2），state 不变。remote 正常可达时不得借 DEFERRED 绕过 remote verify；stop guard 对无凭据 deferred receipt 判 `REMOTE_DEFERRED_EVIDENCE_INVALID`。
- **R4-A2 marker 只是证据、不是 bypass**（2026-09-07）：即使 flush marker 经 `STATE_FLUSH_HEAD_SHA` 绑定当前 HEAD（`BOUND_FLUSH_MARKER`），stop guard 也**不得 early-return PASS**——git dirty / ahead-unpushed / project_state_dirty / graph_dirty / remote durability 全套检查恒执行；marker 只作为证据注记出现在输出中。
- **F6 contract_version == 1 不足以推出 INITIALIZED**。SessionStart 守卫对当前版本 index 至少执行：parse + 必需 top keys + 必需 recovery_snapshot keys + version 校验；不通过 → `PROJECT_STATE_CONTRACT_INVALID`（绝不算 INITIALIZED，也绝不静默销毁，走 repo discovery 修复）；JSON 不可解析同此。

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

### 6.7 生命周期决策表（单一规范决策面）

整个生命周期只有一个决策入口（ZCode 参考实现：`adapters/zcode/hooks/codegraph_lifecycle.py`，命令 `decide --intent <I>`），任何 session / hook / orchestrator 都不得自行从散文重新推导规则。判定枚举封闭，共 13 个：

```text
INIT_ONCE                      新仓（无 index 且无 init 记录）→ 允许一次 full init（仅限 main checkout 或显式 MODE B lane）
CANONICAL_INIT_REQUIRED_AT_MAIN  R4-C：普通 MODE A worktree lane 永不自 init——canonical graph 缺失时，
                                 全部 init-offering intents 都指向 main checkout
FULL_INIT_FORBIDDEN            已有 init 记录或 index → full init 永远不合法
INCREMENTAL_SYNC_ONCE          dirty → 增量同步恰好一次，随后清脏
NO_SYNC                        干净 → 无事可做
GROUNDING_REQUIRED             MEDIUM/HIGH 生产写且无 receipt（§7）
BLAST_RADIUS_REQUIRED          有 receipt 但无 blast radius / 失效 / UNRESOLVED / MODE_A_BASE_MISMATCH
BLAST_RADIUS_EXPANSION_REQUIRED  写入已跟踪但不在 blast radius 内的文件
ALLOW_WRITE                    pre-edit 门禁满足
MARK_DIRTY                     改完只标脏，同步延后（§6.6）
SYNC_FAILED_DEFERRED           同步失败如实报告，绝不升级为 full init
CODEGRAPH_REBUILD_REQUIRED     R6-F6：已注册 graph 健康探测失败 = 损坏/不完整/不兼容 →
                               报告原因；绝不 auto delete、绝不 auto full init；必须由
                               orchestrator 显式 rebuild 权限（record-rebuild）裁决；
                               未决期间 MEDIUM/HIGH 可走 MODE C manual grounding
CODEGRAPH_UNAVAILABLE          R6.1-2：CodeGraph CLI/工具本身不可用（CLI 未安装 /
                               探测进程错误）——与"健康工具报告损坏 index"（→
                               CODEGRAPH_REBUILD_REQUIRED）分类区分；同为 MODE C
                               manual grounding，绝不 auto-init、绝不 auto-rebuild
NO_REPO                        非 git worktree → no-op
```

意图路由（`INTENT ∈ session-start | pre-edit | post-edit | query | review | blast-radius | handoff | stop`）：

| 时机 | 规则 |
| --- | --- |
| 新代码仓 | **init 一次**（`INIT_ONCE`，随后立即 `record-init` 固化记录） |
| 以后 | **sync 增量维护**（`INCREMENTAL_SYNC_ONCE` / `NO_SYNC`） |
| 改代码前 | **先 grounding / blast radius**（`GROUNDING_REQUIRED` → `BLAST_RADIUS_REQUIRED` → `ALLOW_WRITE`） |
| 改完 | **标 dirty**（`MARK_DIRTY`，绝不同步编辑） |
| review / handoff / stop | 必要时 **incremental sync**（dirty → `INCREMENTAL_SYNC_ONCE`） |
| 永远不是 | **每个 session 再 full init**（`FULL_INIT_FORBIDDEN`） |

机械不变量（`verify` 命令，退出码 1 = 违规，供 CI / 测试门禁）：

```text
LC-INV1  一旦存在 init 记录，任何 intent 都不得再返回 INIT_ONCE
LC-INV2  已 init 仓的 session-start 永不 INIT_ONCE
LC-INV3  同步失败后永不回落到 INIT_ONCE
LC-INV4  dirty 状态下 sync 意图必须返回 INCREMENTAL_SYNC_ONCE（R5-F2 例外：普通
         MODE A lane 的源码编辑是 candidate delta，图判定诚实答案为 NO_SYNC——
         不存在可要求的 lane graph sync）
LC-INV5  全部判定都来自封闭枚举
LC-INV6  MODE_A_LANE_NEVER_INIT_ONCE（R4-C）：普通 MODE A worktree lane 对全部 intents
         永不返回 INIT_ONCE；canonical 未初始化时 init-offering intents 一律
         CANONICAL_INIT_REQUIRED_AT_MAIN
LC-INV7  GRAPH_OWNER_HEAD_FRESHNESS（R5-F1）：GRAPH_INDEX_SHA != GRAPH_OWNER_HEAD ⇒
         全部 sync intents 返回 INCREMENTAL_SYNC_ONCE，即使 GRAPH_DIRTY=NO
         （在 graph owner checkout 处强制；MODE A lane 在 NO_SYNC 注记中上报
         staleness，绝不把 canonical sync 伪装成 lane sync）
LC-INV8  UNAPPROVED_DELTA_DETECTED（R6-F4）：OBSERVED_DELTA ⊄ APPROVED_EDIT_SURFACE
         ⇒ `verify` FAIL——已变更文件是证据不是权威，重算不会自我授权
```

**评审修正 R6（PR #5 convergence repair F1–F7，2026-09-09）**：

- **F1 stop marker 是证据不是 issue**。Stop guard 不再把 marker note 塞进 issues 集合——旧代码 `issues.insert(0, note)` 使干净有效的 BOUND_FLUSH_MARKER 令 issues 非空，PASS 分支结构上不可达。真实 issue 独立评估；`BOUND marker + clean git + 无未推送 + state/graph clean + 有效 remote 终态` → `STATE_FLUSH_GUARD=PASS`。
- **F2 graph init record 是 WRITE-ONCE**。`record-init` 是"成功初始化的注册"，不是新鲜度更新：已有 `graph_init` 记录后再调用一律拒绝（`GRAPH_INIT_ALREADY_RECORDED`）。新鲜度只经 `codegraph sync → record-sync-result --ok → last_sync_head = graph owner 实际 HEAD` 推进。显式 rebuild 是独立恢复路径（`record-rebuild --authority CODEGRAPH_REBUILD_AUTHORIZED`），绝不从 record-init 静默可达。
- **F3 shell/Bash 不可绕过 MEDIUM/HIGH grounding**。新增 `bash_preflight_guard.py`（PreToolUse）：有有效 receipt → 正常放行；RISK < MEDIUM → 放行；否则仅放行严格只读白名单（git status/diff/log/show/rev-parse/merge-base/ls-files/branch --show-current、rg/grep/find/ls/dir/cat/Get-Content），重定向 / 链接 / 任意脚本 / git 变更 / 文件变更命令 / 未知命令族一律 `UNKNOWN_BASH_MUTABILITY` → BLOCK（fail closed）。纵深防御：生命周期边界机械检查 git 源码 delta（tracked/untracked/rename 双端点，排除 runtime state 与 .codegraph）——即使 HEAD 不变、graph_dirty 缺失，生产源码 delta 也要求 graph 增量 sync（MODE B lane 同理要求 lane sync；MODE A lane 仍是 candidate delta 证据、无 lane sync）。
- **F4 权威与观测分离**。blast radius 三面分离：`APPROVED_EDIT_SURFACE`（权威：仅来自显式 targets / EXPECTED_EDIT_SURFACE / 显式授权扩张，绝不来自观测 git 变更，也绝不来自 CodeGraph impact）、`OBSERVED_DELTA`（证据：tracked/untracked/deletes/renames）、`IMPACT_SURFACE`（结构感知，不自动授权编辑每个受影响文件）。不变量 `OBSERVED_DELTA ⊆ APPROVED_EDIT_SURFACE`，违反 → `UNAPPROVED_DELTA_DETECTED`；扩张唯一途径是显式 authority action（--target / EXPECTED_EDIT_SURFACE）后重算——"已改过的文件重算后自动获批"被机制性禁止。机械化为 `LC-INV8`。
- **F5 MODE A base/graph 一致性**。grounding/review 时比较 `LANE_BASE_SHA（TICKET_BASE_SHA）` 与 `CANONICAL_GRAPH_INDEX_SHA`：不等 → `MODE_A_BASE_MISMATCH`，绝不静默把最新 main 的 graph 当作旧 lane 的 base graph。Orchestrator 三选项：(A) lane 更新/整合到当前授权 base、(B) 升级 MODE B candidate-exact graph、(C) MODE C manual grounding。未和解前 MEDIUM/HIGH 生产写/review 不得声称有效 Mode A 结构 grounding；grounding receipt 绑定 `BASE_SHA / GRAPH_BASE_SHA / GRAPH_MODE` 且校验实际比较这些字段。**不实现 graph snapshot versioning**，保持最小修复。
- **F6 损坏/不完整 index 有显式恢复态**。`.codegraph` 存在但健康探测失败且 init 记录已存在 → `CODEGRAPH_REBUILD_REQUIRED`（第 13 个封闭枚举值）：报告原因、绝不 auto delete、绝不 auto full init、必须 orchestrator 显式 rebuild 权限；未决期间 MEDIUM/HIGH 可走 MODE C manual grounding（不阻塞、不静默降级）。同时防止 LC-INV3/4/7 在恢复态误触发。
- **F7a state-sync receipt 的 HEAD 绑定**。`record-state-sync` 以**当前 git HEAD 为默认真相**：当前 HEAD 必须存在、receipt HEAD 必须等于当前 HEAD；显式 `--head` 与当前 HEAD 矛盾 → `STATE_SYNC_HEAD_MISMATCH` 拒绝（rc=2）；旧缓存的 `last_state_sync_head` 绝不再充当新 receipt 的默认值——绝不制造绑定旧 HEAD 的"新鲜" receipt。
- **F7b NUL diff 路径逐字保留**。`git diff --name-only -z` 已提供 NUL 边界——不做 `.strip()`（首/尾空格是合法文件名字符）；NUL 之间字节逐字保留，仅空 NUL 字段被跳过；绝不变异文件名却返回 resolved=true。

**评审修正 R6.1（PR #5 final convergence patch F1–F3，2026-09-09）**：

- **R6.1-1 Bash receipt 校验复用 grounding 语义**。`bash_preflight_guard` 不再把"存在 `{BASE_SHA: ...}` 形状的字段"当作充分 grounding：receipt 有效性/新鲜度直接复用 `grounding_guard` 的语义（`REQUIRED_RECEIPT_KEYS` / `base_is_fresh` / 当前 HEAD 比较）。partial receipt → BLOCK（`GROUNDING_RECEIPT_INVALID` + 具体缺陷）；曾经有效但已 stale（HEAD 前移）→ BLOCK；完整且新鲜 → 正常 Bash。防死锁：仅精确放行 canonical 内部命令 `python <hooks>/codegraph_state.py set-grounding ...`（token[0] 为 python/`sys.executable`、token[1] 为本 hook 目录 realpath 下的 `codegraph_state.py`、token[2] == `set-grounding`、其余仅允许 flags；链式/重定向/任意脚本一律拒绝）。验证走真实 Bash preflight 路径：readonly grounding → trusted set-grounding → receipt 存在 → 正常 Bash 放行。
- **R6.1-2 Mode A 一致性覆盖 review；Mode C 真实逃逸；工具不可用分类**。graph-backed Mode A 声称 `BASE_ONLY + DELTA_BY_DIFF` 前（pre-edit / review / grounding 校验至少三处）强制 `BASE_SHA == GRAPH_BASE_SHA == CANONICAL_GRAPH_INDEX_SHA`。长寿命 lane（lane base ≠ canonical graph base）的 review 绝不返回正常 `BASE_ONLY + DELTA_BY_DIFF PASS`。`GRAPH_MODE=manual` → MODE C → canonical graph/base 相等不作要求（真实和解路径，不被 mode_a_base_coherence 阻塞）。分类区分：CodeGraph CLI/工具不可用（CLI 未安装 / 探测进程错误）→ `CODEGRAPH_UNAVAILABLE`（第 14 个封闭枚举值，MODE C manual grounding，绝不 auto-init / auto-rebuild）；健康工具 + 损坏/不完整 index → `CODEGRAPH_REBUILD_REQUIRED`（R6-F6 恢复态不变）。
- **R6.1-3 未批准观测 delta 是运行时门**。`OBSERVED_DELTA ⊄ APPROVED_EDIT_SURFACE` → `UNAPPROVED_DELTA_DETECTED` 机械阻塞：至少 MEDIUM/HIGH 进一步生产写（pre-edit）、review / handoff / stop（review/handoff/stop 门仅要求存在带 unapproved delta 的 blast_radius 记录，不要求 canonical graph 已 init，也不要求 graph-backed receipt），直至未授权 delta 移除或显式扩张批准面。LC-INV8 保持纵深防御，但不再是唯一强制路径。

blast radius 语义：影响集 = **意图编辑面（targets / receipt EXPECTED_EDIT_SURFACE）∪ git delta（base..HEAD + 未提交）∪（可选）CodeGraph impact**——不是"自 base 以来已改了什么"（票务开始时 base == HEAD，delta 为空是常态）。`--impact-file` 缺失时 mode 诚实标注 `GIT_DELTA` / `TARGETS_PLUS_GIT_DELTA`；git 无法作答 → `UNRESOLVED`（fail-closed，不静默降级）。runtime-local 状态新增 `graph_init` / `blast_radius` / `last_sync_failed`，遵守 §6.4 绝不 commit。

**评审修正 R3（external review F1–F3/F7，2026-09-07）**：

- **F1 worktree ≠ 独立 full init 候选**。MODE A（默认）：canonical base graph **按 repo 全局 init 一次**，init 记录为 **repo-level**（键 = 主 checkout），所有 worktree lane 复用 base graph + delta-by-diff，**禁止 per-worktree full init**；lane 的 session-start 永不返回 `INIT_ONCE`。MODE B（显式 candidate-exact / HIGH lane，`--lane-mode B` + `record-init --lane`）：lane 自持 graph，**lane 内** init 一次后仅增量同步。MODE C：manual grounding，无 graph 要求。`graph_init` 增加 `scope=canonical|lane` 字段。
- **F2 blast radius `resolved` 是规范性字段**。base 缺失 / BASE_SHA 无法解析 / git diff 或 status 失败 → `mode=UNRESOLVED, resolved=false` → pre-edit 一律 `BLAST_RADIUS_REQUIRED`，**生产写被阻止**；record 可留作 evidence，但不授权任何写。
- **F3 编辑面权威与 git index 无关**。tracked/untracked 不决定 scope authority：任何**已跟踪或新建**的生产文件落在已批准 blast radius / EXPECTED_EDIT_SURFACE 之外 → `BLAST_RADIUS_EXPANSION_REQUIRED`；新文件确需修改时必须显式扩张意图编辑面并重算 radius 后方可 ALLOW。
- **F7 record-init 诚实性**。`record-init` 必须先验证 index 实际存在（最低健康证据）才允许持久化 init 记录；一次失败 init 不得把 repo 永久锁进"已初始化"状态。

**评审修正 R4（external review A1/A2/B1/B2/B3/B4，2026-09-07）**：

- **B1 单一决策面机械成立**。`codegraph_state.py pre-query` 的自有捷径（`.codegraph missing → INIT_ONCE_ALLOWED`）已删除；该入口只委托 `codegraph_lifecycle.decide(intent=query)`。ONE LIFECYCLE → ONE DECISION SURFACE 不得出现第二判定源。
- **B2 lane 不变量覆盖全部 intents**。对 `session-start / query / review / blast-radius / handoff / stop`：普通 MODE A worktree lane **永不返回 `INIT_ONCE`**；canonical graph 未初始化时返回 `CANONICAL_INIT_REQUIRED_AT_MAIN`（新增封闭枚举），绝不让 lane 自行 init。机械化为 `LC-INV6`。
- **B3 健康证据真实化**。`.codegraph` 目录存在**不算** health proof：`record-init` 需真实 health probe 通过——生产默认执行真实 `codegraph status`（exit 0）；合成测试经 `ZCODE_CODEGRAPH_HEALTH_CMD` 注入 mock probe。空目录一律拒绝（`CODEGRAPH_HEALTH_UNPROVEN`），且 repo 不被锁死。
- **B4 init scope 分离**。`record-init` 只验证 **canonical graph path**；`record-init --lane` 只验证 **lane graph path**。lane index 永不能冒充 canonical init。

**评审修正 R5（external review F1–F6，2026-09-08）**：

- **F1 graph freshness 追踪 graph-owner HEAD**。脏标记只覆盖 Edit/PostToolUse 路径，git pull / merge / fast-forward / checkout / 外部 commit 不触发任何 marker。机械不变量：`GRAPH_OWNER_HEAD` = 实际 graph owner 的 `git rev-parse HEAD`（MODE A = 主 checkout，MODE B = lane 自身）；`GRAPH_INDEX_SHA` = 最近一次成功 sync 的 SHA，否则 `graph_init.head`。两者不等（且均存在）→ **健康既有图必须回答 `INCREMENTAL_SYNC_ONCE`，即使 `GRAPH_DIRTY = NO`**——绝不 full init。机械化为 `LC-INV7`。
- **F2 MODE A lane 的 delta 不是 graph dirty**。脏状态真值表：canonical（主 checkout）源码变更 → `graph_dirty`（canonical graph）→ 增量 sync canonical；MODE B lane 源码编辑 → lane `graph_dirty` → 增量 sync lane；**普通 MODE A lane 源码编辑 → `candidate_delta_dirty` → NO CodeGraph sync**——新鮮 git diff + changed-file 证据即 candidate 证据，canonical graph 始终 `BASE_ONLY + DELTA_BY_DIFF`。review/handoff/stop 在 MODE A lane 绝不要求不可能的 lane sync；coverage 显式标注 `CANDIDATE_GRAPH_COVERAGE = BASE_ONLY + DELTA_BY_DIFF`。
- **F3 porcelain 路径解析 NUL 安全**。`changed_files()` 改用 `git status --porcelain=v1 -z` + `git diff --name-only -z` 解析（旧 `ln.strip(); ln[3:]` 把 unstaged 的 `" M src/app.py"` 切坏成 `"rc/app.py"`）。必须正确处理 unstaged / staged / untracked / rename（两端点都入集）/ 含空格文件名；**解析失败 → `resolved=false` / `mode=UNRESOLVED`**，绝不产出错误路径的 resolved 证据。
- **F4 REMOTE IS REQUIRED, NOT OPTIONAL**。受管 repo 中**未配置 remote 的 Stop 不是 PASS**：Stop 合法终态仅 `REMOTE_VERIFIED=YES` 或携带 failure/no-remote evidence 且绑定 HEAD 的 `REMOTE_STATE_SYNC=DEFERRED`；否则 `REMOTE_REQUIRED`。新仓 bootstrap 应先 establish remote → push → verify 再宣告 durable 完成。SessionStart 与 Stop 使用同一 remote 语义。
- **F5 record-init 的 SHA 绑定 graph owner**。canonical `record-init`（即使从 lane 调用）记录 **主 checkout 的实际 HEAD**；`record-init --lane` 记录 lane 自身 HEAD；显式 `--head` 与 graph owner 实际 HEAD 矛盾 → 拒绝（`GRAPH_INIT_HEAD_MISMATCH`），绝不静默记录矛盾 SHA。
- **F6 终态 remote receipt 对 HEAD fail-closed**。`REMOTE_VERIFIED` / `DEFERRED` receipt 必须 `receipt.head_sha` 存在、当前 HEAD 存在、且两者相等；否则 `REMOTE_RECEIPT_INVALID`——缺失 HEAD 绑定永不 PASS（本环境已多次观测瞬时 broken HEAD ref，此为现实威胁而非理论）。R4 的 `REMOTE_RECEIPT_STALE` 判定并入 `REMOTE_RECEIPT_INVALID`（fail-closed 语义不变）。
- **脏检测鲁棒性（F1/F2 配套）**：生命周期边界（query / review / handoff / stop）用廉价 git 机械证据（`status --porcelain=v1 -z`）补足 Edit/PostToolUse marker——worker 可能用 Bash 改文件；**JIT at boundaries，绝不 per-edit sync**；git spawn 瞬时失败重试一次后如实失败（不误报为机械证据）。

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
- **评审修正 R3（F4，2026-09-07）**：receipt 的机械有效性 = **§7 全部字段必须存在**（值允许为空 / `NONE` / `UNKNOWN`——诚实缺口，不是字段缺席）；字段缺失 = 未做 structural grounding 却伪造"已 grounding" → `GROUNDING_RECEIPT_INVALID`（fail-closed）。`set-grounding` 支持具名 flag 与 `--field KEY=VALUE` 透传，**不自动补全字段**；MANUAL（Mode C）receipt 同样必须具备 Relevant Surface Manifest 等价字段。

## 8. 迁移与失败语义（MIGRATION / FAILURE）

- `contract_version` 语义：`0` = pre-contract stub（v0 从未存在规范 schema，无可保留的 normative 数据）→ `SAFE_MIGRATION`：自动按 repo discovery 重建索引，无数据可毁；`current` 集合内的版本 → 正常；**其余一切（未知更新版本 / 负数 / 非整数 / 损坏）** → 注入 `PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED`，**不静默毁旧数据**，等 owner 裁决。
- **恢复快照 vs 活控制平面**：`.agent/project-state.json` 的 recovery snapshot 是**时点证据（point-in-time evidence）**，永远不是对 live 控制平面的权威；与 GitHub Issue/PR/tracker 冲突时 **tracker 赢**，且必须刷新 index（ONE FACT ONE CANONICAL OWNER：P1 活跃执行状态归 GitHub，见 §1.1）。
- Hook 永不阻塞会话启动/结束（fail-open exit 0）；hook 检测到的状态只注入提醒/阻止信号，语义修复由 Agent 按 canonical 协议执行。
- 校验器禁止项（同样进 validator）：secret-like 字段；committed 状态中的本机绝对路径；**任何值形态**的 machine-only runtime 字段（`GRAPH_DIRTY` / `grounding_receipt` 等按键名拒绝，不只查字符串值）。

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

- **PS1–PS20**（project state）：新仓初始化 / lazy adoption / TARGET·ADR 变更 / ticket·PR·CI·回归事件 / 只读会话不脏 / Stop 脏未 flush / 成功 flush / 远端不可用 / fresh Agent 仅凭 remote 恢复 / 合同版本升级 / 绝对路径拒绝 / secret-like 拒绝 / remote durability 阶梯 / marker 无 bypass / receipt HEAD 绑定（R6-F7a 收口）。
- **CG1–CG15**（CodeGraph）：健康无变更不 sync / 编辑标脏 / 重复编辑仍只脏 / 查询前 JIT sync 一次 / 缺 index 才 init / 已有 index 禁 init / 分支切换=增量 / sync 失败不 fallback init / 双 worktree 状态隔离 / MEDIUM 无 grounding 阻止 / 有 receipt 放行 / UNAVAILABLE → MANUAL fallback / 结构不完整 receipt 拒绝 / pre-query 单一决策面。
- **R6 回归**（PR #5 convergence repair，9 个）：F1 干净 BOUND marker → PASS；F2 record-init write-once + freshness 只经 sync + rebuild 权限门；F3 Bash pre-grounding 白名单（只读放行 / 变更与链接 BLOCK）+ Bash 制造的生产 delta 机械强制 graph sync（A canonical / B lane / A lane candidate）；F4 观测 delta 不自我授权 + LC-INV8；F5 MODE A base/graph 一致性（MODE_A_BASE_MISMATCH 拒绝虚假 BASE_ONLY PASS）；F6 损坏 index 显式恢复态（不自动重建、manual fallback 保留、verify 一致）；F7 receipt 绑当前 HEAD + NUL diff 路径逐字保留（含合成 trailing-space 探针）。
- **R6.1 回归**（PR #5 final convergence patch，5 个）：F1 Bash receipt 校验（partial/stale → `GROUNDING_RECEIPT_INVALID` BLOCK，完整新鲜 → 放行）+ trusted `set-grounding` bootstrap 端到端（readonly grounding → trusted set-grounding → receipt 存在 → 正常 Bash 解锁）；F2 graph-backed Mode A review 一致性（lane base ≠ canonical graph base → review BLOCK）+ MODE C（manual receipt）逃逸 + `CODEGRAPH_UNAVAILABLE` 分类（CLI 不存在 → UNAVAILABLE，健康工具报告损坏 index → REBUILD_REQUIRED）；F3 未批准观测 delta 运行时门（pre-edit BLOCK → review BLOCK → 显式扩张 → recompute → 放行）。
- **CROSS-AGENT RESTORE**：Agent A 初始化→产生状态→STATE_FLUSH→remote simulation；丢弃 A 的全部 context 后 fresh Agent B 仅凭 remote 恢复 target/canonical docs/current state/legal frontier/next legal action，不依赖人工重讲。
- 实现位置：`../adapters/zcode/tests/`（合成本地 synthetic repos，不触碰任何产品仓；CI 接入 `../.github/workflows/governance-ci.yml`）。
