# REF: Execution Stage — 执行阶段编组与 seam-first 分解

> Canonical owner: AGENTS.md §2/§4。本文件是机制细节。

## 1. Stage 定义

EXECUTION STAGE = 一组**被有意编组**的隔离 Ticket Lane + 一个 Stage barrier。

Frontier（所有阻塞已清的票）只是**合法候选集**；编组才是执行决策。编组输入（全部评估，非全选）：

| 输入 | 问题 |
|---|---|
| LEGAL DAG FRONTIER | 哪些票现在可以合法开工？ |
| ENGINEERING COHESION | 哪些票属于同一行为域/同一缝，合并评审更高效？ |
| WRITE OWNERSHIP | 票间是否触碰同一文件/模块/状态 owner？ |
| BLAST RADIUS | 合并到 master 时谁的失效会 invalidate 谁？ |
| RISK CLASS | LOW/MEDIUM/HIGH/CRITICAL 混排是否拉高整组评审成本？ |
| MODEL COST / REVIEW COST | 本组最贵 gate 由谁触发？ |
| INTEGRATION INVALIDATION RISK | 后集成者的 base 会不会被先集成者打 drift？ |

输出：一个 Stage（通常 1–4 个 lane），附 STAGE_MANIFEST（票清单、风险级、预计 gate、集成顺序）。

## 2. Stage barrier 与自动推进

```
Stage 组建 → lanes 并行执行（各自完整 gate 链）
→ 全部 lane 到达终态（PASS / SATURATION / STOP）
→ STAGE_REVIEW_PACKET（novelty-first 汇总：新发现、合同影响、遗留 findings 及处置）
→ 外部评审仅当触发：CRITICAL 票、评审分歧、governance 变更、里程碑
→ 修复/批准 → 自动逐个串行集成（ff-only + remote verify）
→ 重算 frontier → 下一 Stage
```

- 集成顺序 = STAGE_MANIFEST 声明的顺序；后集成者 merge 前重新 fetch + 核验（R4/R5）。
- 单 lane STOP 不阻塞已独立完成的 lane 集成，除非写权/顺序冲突。

## 3. 反模式

- `START_ALL`：把 frontier 全量开_lane —— 禁止。
- `SUPER_STAGE`：把整个 milestone 编成一个 Stage（barrier 失去意义）。
- `SILENT_REORDER`：不更新 STAGE_MANIFEST 就改集成顺序。

## 4. Seam-first 分解协议（/to-tickets 及等价工具的约束壳）

分解工具在候选治理下的运行契约：

1. 输入必须是 approved 架构/Spec 下的实现意图，不是"请设计架构"。
2. 切片前先输出缝清单：既有模块边界、producer/consumer 关系、状态/身份/校验 owner、持久化与安全边界（可用 CodeGraph 辅助）。
3. 票据 = 内聚行为切片；每票字段含：SEAM（触碰的自然缝）、OWNER（既有权威模块）、OUT_OF_SCOPE。
4. 三项 lint：阻塞边审计（每票仅依赖声明的前驱）、合同溯源审计（每个规范要求有 disposition；禁止发明阈值/策略/算法）、约束审计（所有票的约束可同时满足）。
5. prefactor 提议仅当其目标模块在既有架构中已存在或由 Spec 明确授权；否则删除该提议并报告。
6. 产物按 Stage 编组建议标注（建议分组 + 理由），编排者拥有最终编组权。

## 5. 与反例的接口

分解发现"两票共享同一状态 owner"→ 不是加票据边，而是回查缝：要么拆 owner（需要架构授权 → STOP），要么合并为一票。
