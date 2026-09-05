# REF: CodeGraph Grounding — 结构接地与增量同步（按真实工具能力）

> Canonical owner: AGENTS.md §5。本文件是机制协议。**已对照安装版 CodeGraph v1.0.1 的真实 CLI 能力校准（2026-09-05 `--help` 全量核验）**；不发明工具不存在的机制。

## 1. 已核实的工具能力面

```
init / uninit      建库（.codegraph/ 目录）/ 移除
index              全量索引（重）
sync               增量同步（"Sync changes since last index"）
status             索引状态与健康统计
query / explore / node / files / callers / callees   查询族
impact             变更影响分析（爆炸半径）
affected           变更源文件 → 受影响测试
daemon             后台常驻
```

**限制（必须如实接受）**：数据库是**每目录**的（`<dir>/.codegraph/`），无内建跨目录/跨 worktree 共享库语义。

## 2. 目标拓扑（默认，全部落在真实能力内）

```
主仓库目录 = CANONICAL GRAPH（BASE 态：master/已合并拓扑）
  init 一次（base = 当前 master）
  master 前进后 → codegraph sync（增量）
  健康检查 → codegraph status
        ↑ 查询（daemon / 直接 CLI 指向主仓目录）
LANE WORKTREE
  独立的【查询 + 证据】生命周期；candidate 态按 §2.1 三种模式之一接地
```

- `INDEPENDENT_GROUNDING != INDEPENDENT_REINDEX`：独立的是**查询、关系推理与证据**，不是库所有权。
- 禁止：每票/每评审跑全量 `index`；每个 worktree 长期维护互不相通的陈旧库。
- Reviewer 复用同一 lane 库（若存在）完全不**损害**评审独立性——独立性由 fresh context、独立查询路径、独立反例承担。

### 2.1 Candidate 接地三模式（R3 修复：可执行且诚实）

工具现实：worktree 新建时**没有**本地 `.codegraph`，`sync` 无库可增；canonical 图只代表 base/master，**看不到未合并的候选编辑**。因此：

| 模式 | 机制 | 覆盖声明 | 成本 |
|---|---|---|---|
| A. BASE + DIFF（默认） | 结构问题查 canonical（base 拓扑：callers/callees/impact）；候选增量用 `git diff BASE..candidate` + 变更文件直读 | `CANDIDATE_GRAPH_COVERAGE = BASE_ONLY + DELTA_BY_DIFF`（**不声称 candidate-exact 图覆盖**） | 零额外索引 |
| B. LANE_INDEX（按需，每 lane 一次；**已机械证实**，见下方探针证据） | 确需 candidate-exact 图查询时（HIGH 风险/重跨模块候选），在 lane worktree `codegraph init` **一次**——v1.0.1 实测 `init` 即完成初始全量索引——后续编辑用 `sync` 增量 | `CANDIDATE_GRAPH_COVERAGE = CANDIDATE_EXACT` | 每 lane 一次 init；lane 内 reviewer **复用同一库**，绝不每评审重建 |
| C. UNAVAILABLE | CodeGraph 不可用 → 手工 surface manifest + 重点阅读 | `CODEGRAPH = UNAVAILABLE` | — |

**Mode B 探针证据（B1 修复，2026-09-05，安装版 codegraph v1.0.1，隔离一次性目录 /tmp/cg-probe-*，未触碰任何产品仓；探针目录已销毁）**：

```
$ codegraph init /tmp/cg-probe-9822
◆  Indexed 3 files
●  7 nodes, 6 edges in 2.6s
└  Done                              # → init 即完成初始全量索引（fresh 目录无先验库）

$ codegraph status /tmp/cg-probe-9822
Index Statistics:  Files: 3  Nodes: 7  Edges: 6  DB Size: 0.14 MB

$ codegraph query "computeTotal" --path /tmp/cg-probe-9822
function computeTotal (9311%)  src/core.js:1

# 新增 billing.js 后（增量验证）：
$ codegraph sync /tmp/cg-probe2
●  Added: 1 — 2 nodes in 513ms       # → sync 为真增量，无需重建

$ codegraph impact "computeTotal" --path /tmp/cg-probe2
Impact of changing "computeTotal" — 2 affected symbols: computeTotal, checkout
```

结论：**评审选项 A 成立** —— Mode B 执行路径 = `init`（每 lane 至多一次，即初始索引）→ `sync`（增量）；`init`/`index` 全量操作**绝不** per-reviewer / per-repair-round 重复。

- 报告必须写明所用模式与 `CANDIDATE_GRAPH_COVERAGE` 值；A 模式下凡涉及"候选编辑后的新关系"的结论，证据来源必须标注为 diff/源码而非图查询。
- 禁止：per-reviewer / per-repair-round 的全量 `index`/`init`；跨 worktree 共享库的虚构机制（工具不支持）。

## 3. delta grounding 协议（对应 §2.1 模式落地步骤）

1. lane 开始：`status` 确认 canonical 图健康；记录 `GRAPH_BASE_SHA`（应 == 票 base SHA 或 master）；**选择模式 A/B 并写入票据包**（默认 A）。
2. 候选编辑后（模式 A）：`git diff BASE..candidate` + 变更文件直读；对触及符号在 canonical 上跑 `impact` 评估 base 拓扑下的爆炸半径。
3. 候选编辑后（模式 B）：lane 库 `sync` 同步变更文件 → candidate-exact 查询更新后的关系。
4. 回归定位：`affected <files>`（模式 B 为候选态；模式 A 为 base 态近似，须标注）。
5. 评审：reviewer 独立查询（模式 B 复用 lane 库；模式 A 复用 canonical + 独立 diff 阅读路径），重点复核 worker 声明的关系（producer/consumer/owner）。
6. 全量重建白名单：`status` 报告损坏/过期不可 sync；schema/版本升级不兼容；`init` 配置变更。**除此之外全量重建不是任何 gate**；模式 B 的 lane init 每 lane 至多一次。

## 4. 不可用降级（SKILL/TOOL_IS_METHOD_NOT_AUTHORITY：工具缺失不自动成为普适硬 gate）

CodeGraph 未安装/损坏/库不可恢复 → **MODE C**：手工 Relevant Surface Manifest + 定向源码阅读；报告 `CODEGRAPH = UNAVAILABLE`（UNKNOWN ≠ PASS，不得伪造接地）。

- **MEDIUM**：MODE C 继续推进，前提 = 适用仓合同允许；必须如实标注降级。
- **HIGH**：默认 **MODE C + ENHANCED_MANUAL_GROUNDING + ESCALATION**（更强手工证据 + 独立评审加强），**不得**假装发生了正常图接地；`CANDIDATE_GRAPH_COVERAGE` 记为 UNAVAILABLE/DELTA_BY_DIFF。
- **仅以下条件触发 HARD STOP**：①仓本地权威（C 层）明确要求 CodeGraph；②该 HIGH 风险问题在没有结构证据时无法负责任地接地；③reviewer/owner 判定证据不足。
- 详见 `references/static-analysis-and-code-intelligence.md`（工具层级与降级路径）。

## 5. 与权威的关系

CodeGraph 产出**证据**，不产出权威；结构问题的裁决权在 C 层（仓架构/Spec）与 D 层（本协议默认）。
