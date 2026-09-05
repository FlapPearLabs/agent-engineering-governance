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
主仓库目录 = CANONICAL GRAPH
  init 一次（base = 当前 master）
  master 前进后 → codegraph sync（增量）
  健康检查 → codegraph status
        ↑ 查询（daemon / 直接 CLI 指向主仓目录）
LANE WORKTREE
  独立的【查询 + 证据】生命周期：
  a) 通过 daemon 查询 canonical；或
  b) 对本目录库执行 sync（从其 base 增量，廉价）
  记录 GRAPH_BASE_SHA（= grounding 依据的图所对应的提交）
```

- `INDEPENDENT_GROUNDING != INDEPENDENT_REINDEX`：独立的是**查询、关系推理与证据**，不是库所有权。
- 禁止：每票/每评审跑全量 `index`；每个 worktree 长期维护互不相通的陈旧库。
- Reviewer 复用同一 canonical/增量库完全**不**损害评审独立性——独立性由 fresh context、独立查询路径、独立反例承担。

## 3. delta grounding 协议

1. lane 开始：`status` 确认图健康；记录 `GRAPH_BASE_SHA`（应 == 票 base SHA 或 master）。
2. 候选编辑后：`sync` 同步变更文件 → 查询更新后的关系。
3. 爆炸半径：`impact <symbol>`；回归定位：`affected <files>`。
4. 评审：reviewer 对同一 exact SHA 独立查询；重点复核 worker 声明的关系（producer/consumer/owner）。
5. 全量重建白名单：`status` 报告损坏/过期不可 sync；schema/版本升级不兼容；`init` 配置变更。**除此之外全量重建不是任何 gate。**

## 4. 不可用降级

CodeGraph 未安装/损坏/库不可恢复 → 该票 grounding 降级为：手工 Relevant Surface Manifest + 重点文件阅读；报告 `CODEGRAPH = UNAVAILABLE`（UNKNOWN ≠ PASS，不得伪造接地）。降级是否阻塞由风险级决定：HIGH 默认阻塞（等待修复或 owner 豁免），MEDIUM 允许降级继续但必须标注。

## 5. 与权威的关系

CodeGraph 产出**证据**，不产出权威；结构问题的裁决权在 C 层（仓架构/Spec）与 D 层（本协议默认）。
