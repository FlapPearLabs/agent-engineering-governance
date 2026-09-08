# ZCode Adapter — PROJECT_CONTINUITY_CONTRACT_V1 reference implementation

> Runtime adapter, **not** the contract. Canonical contract text: `../../references/project-continuity-contract.md`（contract_version = 1，运行时中立）。其他 runtime（WorkBuddy / OpenCode / Codex / …）按同一合同实现等价 hook 即可，不依赖 ZCode。

## What hooks exist / what event they bind / what contract they enforce

| hook 脚本 | ZCode 事件 | 强制的合同条款 | 语义 |
|---|---|---|---|
| `hooks/governance_sync.py` | SessionStart | 治理仓同步 | SYNCED / BEHIND_FAST_FORWARDABLE / DIRTY / DIVERGED / REMOTE_UNAVAILABLE；不覆盖 dirty/diverged |
| `hooks/project_state_guard.py` | SessionStart | 合同 §2 初始化 | 缺 `.agent/project-state.json` → `PROJECT_CONTINUITY_INITIALIZATION_REQUIRED`（orchestrator 自动执行 lazy adoption / 新仓 bootstrap，不问用户）；版本不兼容 → `PROJECT_STATE_CONTRACT_MIGRATION_REQUIRED` |
| `hooks/codegraph_state.py`（`--hook`） | PostToolUse | 合同 §6.6 / §3 | 生产源码编辑 → `CODEGRAPH_DIRTY`；状态文档编辑 → `PROJECT_STATE_DIRTY`；只标脏，绝无 per-edit sync / full index |
| `hooks/state_flush_guard.py` | Stop | 合同 §5 / §9 durability gate | 未提交/未推 → `STATE_FLUSH_REQUIRED`；project_state_dirty → `DURABLE_STATE_SYNC_REQUIRED`；remote-backed 项目按 F5 阶梯判定：无凭据/LOCAL_DURABLE/REMOTE_PUSHED → `REMOTE_VERIFICATION_REQUIRED`，凭据缺 HEAD 绑定或绑定已前移的 HEAD → `REMOTE_RECEIPT_INVALID`（R5-F6 fail-closed），无凭据 deferred → `REMOTE_DEFERRED_EVIDENCE_INVALID`，合法终态仅 `REMOTE_VERIFIED=YES` 或带凭据 `REMOTE_STATE_SYNC=DEFERRED`；**未配置 remote → `REMOTE_REQUIRED`（R5-F4：REMOTE IS REQUIRED, NOT OPTIONAL——no-remote Stop 永非 PASS）**，唯一诚实替代终态为绑定 HEAD 的 no-remote DEFERRED failure receipt；env flush marker **只是证据不是 bypass**（R4-A2）——即使经 `STATE_FLUSH_HEAD_SHA` 绑定当前 HEAD 也照常执行全套检查，未绑定/过期 → `UNBOUND/STALE_FLUSH_MARKER`；graph_dirty → `CODEGRAPH_SYNC_REQUIRED_BEFORE_STOP`（sync 一次，禁止 fallback init） |
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
       # R5-F2: status 增列 CANDIDATE_DELTA_DIRTY；PostToolUse 在普通 MODE A lane
       # 的源码编辑标 candidate_delta_dirty（绝不标 lane graph dirty）
record-state-sync [--head SHA] [--event E]
                  [--deferred --remote-operation OP --failure-class C --attempted-at AT]
                  # R4-A1: 裸 --deferred 拒绝（rc=2 REMOTE_DEFERRED_EVIDENCE_REQUIRED）；
                  #        DEFERRED 必须绑定真实失败凭据 HEAD_SHA+OP+C+AT
set-grounding --ticket T --risk RISK --base-sha SHA --mode graph|manual
              [--seam S] [--surface S] [--out-of-scope S] | --clear
pre-query   # R4-B: 仅委托 codegraph_lifecycle decide(intent=query)——ONE LIFECYCLE →
            # ONE DECISION SURFACE，本入口不再自判 init（旧 INIT_ONCE_ALLOWED 已删除）
```

## codegraph_lifecycle.py CLI（合同 §6.7 — 生命周期单一决策入口）

```text
decide --intent session-start|pre-edit|post-edit|query|review|blast-radius|handoff|stop
       [--risk R] [--file F] [--request-full-init] [--lane-mode A|B]
       # R5-F1 freshness: GRAPH_INDEX_SHA（最近 sync SHA，否则 graph_init.head）!=
       # GRAPH_OWNER_HEAD（实际 graph owner 的 HEAD）→ INCREMENTAL_SYNC_ONCE，
       # 即使 GRAPH_DIRTY=NO（pull/merge/ff/checkout/外部 commit 不触发 Edit marker）
       # R5-F2: 普通 MODE A lane 的 sync intents → NO_SYNC（candidate delta 经
       # marker 或 git status 机械证据检测；coverage=BASE_ONLY+DELTA_BY_DIFF）
record-init [--head SHA] [--mode full] [--lane]
       # F7/R4-D: 健康证据必须真实——生产默认跑真实 `codegraph status`（exit 0 才算健康），
       # 测试经 ZCODE_CODEGRAPH_HEALTH_CMD 注入 mock；空 .codegraph 目录不算健康。
       # R4-B4 scope 分离: record-init 只验证 canonical graph path，--lane 只验证 lane
       # graph path；lane index 永不能冒充 canonical init。
       # R5-F5: 记录的 init SHA = graph owner 的实际 HEAD（canonical 从 lane 调用绑定
       # 主 checkout HEAD）；显式 --head 与 owner HEAD 矛盾 → GRAPH_INIT_HEAD_MISMATCH
blast-radius [--base SHA] [--target F ...] [--impact-file JSON]
       # R5-F3: porcelain 解析 NUL 安全（git status --porcelain=v1 -z / diff -z）；
       # unstaged/staged/untracked/rename/空格文件名全支持；解析失败 → resolved=false
record-sync-result --ok | --fail                  # fail → SYNC_FAILED_DEFERRED，绝不回落 init
verify                                            # LC-INV1..INV7；exit 1 = 违规
```

规则一句话版：**新仓 init 一次 → 以后只增量 sync → 改前 grounding + blast radius → 改后标 dirty → review/handoff/stop 必要时增量 sync → 永远不在每个 session 再 full init。**

评审修正 R3（external review F1–F4/F7，2026-09-07）：

- **F1 MODE A（默认）**：canonical base graph 按 **repo 全局** init 一次（`record-init` 写 repo-level 记录）；worktree lane 复用 base graph + delta-by-diff，session-start 永不 `INIT_ONCE`。**MODE B**（`--lane-mode B` 显式 candidate-exact lane）：lane 自持 graph，`record-init --lane` 写 lane-local 记录，lane 内 init 一次。MODE C：manual grounding。
- **F2**：`blast-radius` 产出含规范 `resolved` 字段；base 缺失 / BASE_SHA 不可解析 / git diff 或 status 失败 → `mode=UNRESOLVED` → pre-edit `BLAST_RADIUS_REQUIRED`，生产写被阻止。
- **F3**：编辑面权威与 git index 无关——tracked/untracked 一视同仁，出界即 `BLAST_RADIUS_EXPANSION_REQUIRED`；显式扩张意图编辑面（再跑 `blast-radius --target ...`）后放行。
- **F4**：grounding receipt 机械有效性 = §7 全部字段存在（值可 `NONE/UNKNOWN`）；`set-grounding` 提供 `--field KEY=VALUE` 透传且不自动补全；缺字段 → `GROUNDING_RECEIPT_INVALID`。

评审修正 R4（external review A1/A2/B1/B2/B3/B4，2026-09-07）：

- **A1**：`REMOTE_STATE_SYNC=DEFERRED` 是失败凭据，不是绕行——裸 `--deferred` 拒绝（rc=2）；必须绑定 `--head` + `--remote-operation` + `--failure-class` + `--attempted-at`。stop guard 同步拒收无凭据的 deferred receipt（`REMOTE_DEFERRED_EVIDENCE_INVALID`）。
- **A2**：stop guard 的 env flush marker **只是证据、永不 bypass**——即使绑定当前 HEAD（`BOUND_FLUSH_MARKER`）也照常执行 dirty / unpushed / state / graph / remote 全套检查。
- **B1**：`pre-query` 删除自有 `.codegraph missing → INIT_ONCE_ALLOWED` 捷径，改为委托 `codegraph_lifecycle.decide(intent=query)`——ONE LIFECYCLE → ONE DECISION SURFACE 机械成立。
- **B2**：新增封闭判定 `CANONICAL_INIT_REQUIRED_AT_MAIN`；普通 MODE A worktree 对 **全部 intents**（session-start/query/review/blast-radius/handoff/stop）永不返回 `INIT_ONCE`，canonical 未初始化时一律指向 main checkout；不变量 `LC-INV6 MODE_A_LANE_NEVER_INIT_ONCE` 入 `verify`。

评审修正 R5（external review F1–F6，2026-09-08）：

- **F1 graph freshness**：`GRAPH_INDEX_SHA != GRAPH_OWNER_HEAD → INCREMENTAL_SYNC_ONCE`（即使 dirty=NO）；机械化为 `LC-INV7 GRAPH_OWNER_HEAD_FRESHNESS` 入 `verify`。测试：LC18（HEAD 前移 / 分支切换无 marker → 增量；同 HEAD 干净 → NO_SYNC）。
- **F2 delta 语义**：`CANONICAL_GRAPH_DIRTY`（主 checkout `graph_dirty`）/ `LANE_GRAPH_DIRTY`（MODE B lane `graph_dirty`）/ `CANDIDATE_DELTA_DIRTY`（MODE A lane 专属，不产生任何 CodeGraph sync 要求）；MODE A lane 的 review/handoff/stop 以 NO_SYNC + coverage 标注应答，绝不要求 lane sync。测试：CG9/LC19。
- **F3 porcelain**：`changed_files()` 全量改 `-z` NUL 安全解析；解析失败 → `resolved=false`/`UNRESOLVED`。测试：LC20（unstaged/staged/untracked/rename/空格 + 损坏记录 fail-closed）。
- **F4/F6 remote**：no-remote Stop → `REMOTE_REQUIRED`（非 PASS），诚实终态为绑定 HEAD 的 no-remote DEFERRED failure receipt；`REMOTE_VERIFIED`/`DEFERRED` receipt 缺 HEAD 绑定或绑定已前移 → `REMOTE_RECEIPT_INVALID`。测试：PS10/PS11（SessionStart 与 Stop 同语义）/PS20。
- **F5 owner 绑定**：canonical `record-init` 从 lane 调用绑定主 checkout HEAD；`--head` 与 owner HEAD 矛盾 → 拒绝。测试：LC21。
- **鲁棒性**：lifecycle 边界用廉价 git 机械证据（`status --porcelain=v1 -z`）补足 Edit marker（JIT 不 per-edit）；git spawn 瞬时失败重试一次后如实失败。
- **B3/B4**：`record-init` 需真实 graph health evidence（生产默认 `codegraph status`；测试注入 `ZCODE_CODEGRAPH_HEALTH_CMD` mock），空 `.codegraph` 目录不再算健康；canonical/lane scope 严格分离，lane index 不能冒充 canonical init。

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
