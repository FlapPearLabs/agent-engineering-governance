# REF: CodeGraph Grounding — 结构接地与增量同步

> Canonical owner: AGENTS.md §5。本文件是机制协议。

## 1. 定位

CodeGraph 回答**结构问题**：谁调用/谁生产/谁校验/谁拥有状态/谁持久化/谁消费/下游谁坏/信任边界在哪。它是 grounding 工具，不是仪式；不产生权威（权威永远是 RULES > AGENTS > Spec）。

## 2. 核心语义

```
INDEPENDENT_CODEGRAPH_GROUNDING != INDEPENDENT_FULL_REINDEX
```

- 独立性 = 独立**查询**与关系推理（worker 与 reviewer 各自回答结构问题）；
- 独立性 ≠ 各自重建索引库；
- 全量重建仅由健康/schema/配置证据触发，且永不是每票/每评审 gate。

## 3. Canonical graph + delta 协议

```
CANONICAL HEALTHY GRAPH @ current remote master
   （主 worktree 持有；master 前进后增量同步）
        ↓ worker lane 开始时
   LANES 记录 GRAPH_BASE_SHA（所查图对应的 master SHA）
        ↓ 候选编辑发生
   INCREMENTAL SYNC / DELTA GROUNDING（只同步本 lane 变更触碰的子图）
        ↓ fresh reviewer
   独立查询：canonical graph @ GRAPH_BASE_SHA + candidate delta
```

义务：

- 每 lane 证据包记录 `GRAPH_BASE_SHA`；评审核对 `GRAPH_BASE_SHA == 当票 base SHA`（陈旧图永不作为 PASS 证据）；
- delta 同步失败/结果可疑 → 该 lane 升级为全量重建（带健康证据），或 STOP；
- worktree 不各自养独立陈旧库：worktree 查询指向 canonical graph（或显式 fork + 记录）；
- 全量重建的合法触发：图健康报告异常、schema 升级、索引配置变更、delta 连续失败、仓库大规模重构。

## 4. 反模式清单

| 反模式 | 后果 | 纠正 |
|---|---|---|
| 每评审员全量重建 | 时间烧在索引；互相得到不同版本的图 | canonical + delta |
| 陈旧图作 PASS 证据 | 评审建立在错误结构事实上 | GRAPH_BASE_SHA 核验 |
| 用图库输出替代权威裁决 | 图描述现状，不裁决合同 | 结构事实供推理，权威链裁决 |
| 为图工具引入第二套竞争索引实现 | 双真相源 | 除非显式要求，只用既有 CodeGraph MCP |

## 5. 部署事实（指针）

- 安装/版本/服务命令/健康检查 = `mcp/README.md`（codegraph 条目 + MACHINE_SPECIFIC）。本文件不写机器路径。
