# ZCode Adapter — PROJECT_CONTINUITY_CONTRACT_V1 reference implementation

> Runtime adapter, **not** the contract. Canonical contract text: `../../references/project-continuity-contract.md`（contract_version = 1，运行时中立）。其他 runtime（WorkBuddy / OpenCode / Codex / …）按同一合同实现等价 hook 即可，不依赖 ZCode。

## What hooks exist / what event they bind / what contract they enforce

| hook 脚本 | ZCode 事件 | 强制的合同条款 | 语义 |
|---|---|---|---|
| `hooks/governance_sync.py` | SessionStart | 治理仓同步 | SYNCED / BEHIND_FAST_FORWARDABLE / DIRTY / DIVERGED / REMOTE_UNAVAILABLE；不覆盖 dirty/diverged |
| `hooks/project_state_guard.py` | SessionStart | 合同 §2 初始化 | 缺 `.agent/project-state.json` → `PROJECT_CONTINUITY_INITIALIZATION_REQUIRED`（orchestrator 自动执行 lazy adoption / 新仓 bootstrap，不问用户）；版本不兼容 → `PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED` |
| `hooks/codegraph_state.py`（`--hook`） | PostToolUse | 合同 §6.6 / §3 | 生产源码编辑 → `CODEGRAPH_DIRTY`；状态文档编辑 → `PROJECT_STATE_DIRTY`；只标脏，绝无 per-edit sync / full index |
| `hooks/state_flush_guard.py` | Stop | 合同 §5 / §9 durability gate | 未提交/未推 → `STATE_FLUSH_REQUIRED`；project_state_dirty → `DURABLE_STATE_SYNC_REQUIRED`；graph_dirty → `CODEGRAPH_SYNC_REQUIRED_BEFORE_STOP`（sync 一次，禁止 fallback init） |
| `hooks/grounding_guard.py` | PreToolUse | 合同 §7 | RISK≥MEDIUM + 生产写 + 无 receipt → block（exit 2）`CODEGRAPH_GROUNDING_REQUIRED`；receipt 的 BASE_SHA 不在 HEAD 祖先链（base 被重写/换底）→ `GROUNDING_RECEIPT_STALE`——worker 自身的新 commit 不失效 receipt；MANUAL receipt（mode=manual）→ 放行 |
| `hooks/codegraph_lifecycle.py` | CLI（orchestrator 决策入口） | 合同 §6.7 | 生命周期单一规范决策面：`INIT_ONCE / FULL_INIT_FORBIDDEN / INCREMENTAL_SYNC_ONCE / NO_SYNC / GROUNDING_REQUIRED / BLAST_RADIUS_REQUIRED / BLAST_RADIUS_EXPANSION_REQUIRED / ALLOW_WRITE / MARK_DIRTY / SYNC_FAILED_DEFERRED / NO_REPO`；`verify` 输出 LC-INV1..INV5 不变量（exit 1 = 违规，可接 CI 门禁） |

共享状态：`hooks/_continuity_state.py`（runtime-local，见下）。

## Runtime-local state（绝不 commit）

```text
~/.zcode/runtime-state/continuity/<sha256(worktree realpath)>/state.json
```

- 键 = **repo realpath + worktree realpath**（worktree 隔离，合同 §6.5）。
- 内容：`graph_dirty / project_state_dirty / last_sync_head / last_sync_at / last_state_sync_* / grounding_receipt / graph_init / blast_radius / last_sync_failed`（后三项由生命周期决策面写入，合同 §6.7）。
- 测试覆盖根：环境变量 `ZCODE_RUNTIME_STATE_DIR`（合成测试矩阵用它保持 hermetic）。
- **这些字段是 machine-only runtime state，绝不进入 Git / project-state index**（合同 §6.4；validator 会拒绝混入）。

## codegraph_state.py CLI（orchestrator / 测试驱动面）

```text
status | record-event <EVENT> | mark-graph-synced [--head SHA]
record-state-sync [--head SHA] [--event E] [--deferred]
set-grounding --ticket T --risk RISK --base-sha SHA --mode graph|manual
              [--seam S] [--surface S] [--out-of-scope S] | --clear
pre-query   # JIT 规则：INDEX_MISSING→INIT_ONCE_ALLOWED；dirty→SYNC_REQUIRED_ONCE；否则 NO_SYNC
```

## codegraph_lifecycle.py CLI（合同 §6.7 — 生命周期单一决策入口）

```text
decide --intent session-start|pre-edit|post-edit|query|review|blast-radius|handoff|stop
       [--risk R] [--file F] [--request-full-init]
record-init [--head SHA] [--mode full]      # full init 完成后立即固化 → 之后永久 FORBIDDEN
blast-radius [--base SHA] [--target F ...] [--impact-file JSON]
record-sync-result --ok | --fail            # fail → SYNC_FAILED_DEFERRED，绝不回落 init
verify                                      # LC-INV1..INV5；exit 1 = 违规
```

规则一句话版：**新仓 init 一次 → 以后只增量 sync → 改前 grounding + blast radius → 改后标 dirty → review/handoff/stop 必要时增量 sync → 永远不在每个 session 再 full init。**

## Install（新 ZCode 环境重建）

1. 取本仓（fresh clone `FlapPearLabs/agent-engineering-governance`）。
2. 把 `hooks/*.py` 拷到本机 hook 目录（如 `~/.zcode/hooks/`）；共享模块 `_continuity_state.py` 必须同目录。
3. 在 runtime config 的 hooks 节接线：SessionStart → `project_state_guard.py`；PostToolUse → `codegraph_state.py --hook`；Stop → `state_flush_guard.py`；PreToolUse → `grounding_guard.py`。
4. 验证：`python3 ../../scripts/validate_project_state.py <any-governed-repo>` + `python3 -m unittest discover -s tests`（合成矩阵）。

## Version alignment（LOCAL_HOOK_CONTRACT_VERSION == REMOTE）

- 本 adapter 实现的 `contract_version` 见 `hooks/_continuity_state.py` `STATE_VERSION`（当前 **1**），必须等于 governance remote main 上 `schemas/project-state.schema.json` 的 `contract_version`。合同升版 → 本目录同步发 PR，二者永不分叉。

## 已知限制（诚实边界）

- **PreToolUse payload 可靠性未证实（2026-09-06 ZCode 实测）**：`grounding_guard.py` 在 stdin 拿不到 `tool_input.file_path` 时 fail-open（advisory）。**权威 gate 仍是 orchestrator 纪律（合同 §7）**；hook 只把"忘记"变成机械可见。Pre-commit/pre-push 拦截同理：payload 不能可靠识别 `git commit`/`git push` 前**不实现**（合同 §9）。
- Hook 只做机械检测与信号注入，**绝不**写语义决策（架构含义/用户决策/Spec 内容）——合同 §9 HOOK 不写语义决策。
- **状态文档识别是名字启发式**（target/spec/adr/spike/architecture 路径子串，见 `_continuity_state.py`）：MADR 风格 `docs/decisions/` 等布局不会被自动标脏（fail-open 漏报）；`notes/speculation.md` 之类会误报。权威做法 = 按 index 的 `canonical_documents` pointers 分类，留待下一版；漏报时 orchestrator 仍按合同 §3 在 meaningful transition 手动 `record-event`。
- 所有 hook 任何异常 exit 0，绝不阻塞会话启动/结束（`grounding_guard` 的 exit 2 = 显式 block 请求除外）。
- CodeGraph 工具本身**不由 hook 调用**：hook 只维护 dirty 账本并发出 `SYNC_REQUIRED_ONCE / INDEX_MISSING` 指令，执行者是 orchestrator——因此合成测试无需安装 CodeGraph。
