# REF: Execution Stage — 执行阶段编组与 seam-first 分解

> Canonical owner: AGENTS.md §2/§4。本文件是**D 层默认**机制（仓政策可通过 C 层覆盖）。设计边界声明：Stage 编组是设计选择，其必要性由"frontier=就绪即全开"的工具语义（`/to-tickets` 原文）与 prompt 搬运痛点支撑；机制本身无历史先例约束。

## 1. Stage 定义

EXECUTION STAGE = 一组**被有意编组**的隔离 Ticket Lane + 一个 Stage barrier。

Frontier（所有阻塞已清的票）只是**合法候选集**；编组才是执行决策。编组输入（全部评估，非全选）：

| 输入 | 问题 |
|---|---|
| LEGAL DAG FRONTIER | 哪些票现在可以合法开工？ |
| ENGINEERING COHESION | 哪些票属于同一行为域/同一缝，合并评审更高效？ |
| WRITE OWNERSHIP | 票间是否触碰同一文件/模块/状态 owner？ |
| BLAST RADIUS | 合并到 master 时谁的失效会 invalidate 谁？ |
| RISK CLASS | LOW/MEDIUM/HIGH 混排是否拉高整组评审成本？ |
| MODEL COST / REVIEW COST | 本组最贵 gate 由谁触发？ |
| INTEGRATION INVALIDATION RISK | 后集成者的 base 会不会被先集成者打 drift？ |

输出：STAGE_MANIFEST（票清单、风险级、预计 gate、集成顺序）。通常 1–4 个 lane。

## 2. Owner 冲突处置（多就绪票共享同一 owner）

命中 WRITE OWNERSHIP 冲突时**三选一**，不得默认并行：
1. **合并为一票**（内聚性优先）；
2. **显式串行集成链**（并行施工可以，但 STAGE_MANIFEST 声明集成顺序，后集成者 merge 前 re-fetch + 必要时 re-form）；
3. **拆 owner**（真正的架构决策 → 走架构授权，不是执行层能决定的事）。

## 3. 无 DAG 退化路径

无分解 DAG（单票项目/未用分解工具/独立项目）：
- Stage = 按风险与内聚选出的单票或票集合；frontier/DAG 输入标记 `NOT_APPLICABLE`；
- barrier、串行集成、remote verify、novelty-first packet 语义全部保留；
- 不得为"凑齐 DAG"而发明票据。

## 4. Stage barrier 与自动推进

```
Stage 组建 → lanes 并行执行（各自完整 gate 链）
→ 全部 lane 到达终态（PASS / SATURATION / STOP）
→ STAGE_REVIEW_PACKET（novelty-first 汇总：新发现、合同影响、遗留 findings 及处置）
→ 外部评审仅当 ESCALATION 触发（AGENTS §3 清单）
→ 修复/批准 → 自动逐个串行集成（按仓政策 merge 方法 + remote verify）
→ 重算 frontier → 下一 Stage
```

- 单 lane STOP 不阻塞已独立完成的 lane 集成，除非写权/顺序冲突。

## 5. 反模式

- `START_ALL`：把 frontier 全量开 lane —— 禁止。
- `SUPER_STAGE`：整个 milestone 编成一个 Stage（barrier 失去意义）。
- `SILENT_REORDER`：不更新 STAGE_MANIFEST 就改集成顺序。

## 6. Seam-first 分解协议（/to-tickets 及等价工具的约束壳）

1. 输入必须是 approved 架构/Spec 下的实现意图，不是"请设计架构"。
2. 切片前先输出缝清单：既有模块边界、producer/consumer 关系、状态/身份/校验 owner、持久化与安全边界（CodeGraph 辅助）。
3. 票据 = 内聚行为切片；每票字段含：SEAM、OWNER、OUT_OF_SCOPE。
4. 三项 lint：阻塞边审计（每票仅依赖声明的前驱）、合同溯源审计（每个规范要求有 disposition；禁止发明阈值/策略/算法）、约束审计（所有票约束可同时满足）。
5. prefactor 提议仅当目标模块在既有架构中已存在或由 Spec 明确授权；否则删除并报告。
6. **对立错误防护**：合法架构性拆分/合并不得因票据边界被拒——依赖边暴露真实架构合同时，升格为架构决策走授权（AGENTS §4）。
7. 产物按 Stage 编组建议标注（分组 + 理由），编排者拥有最终编组权。

## 7. 与反例的接口

分解发现"两票共享同一状态 owner" → 回查缝：拆 owner（架构授权 → STOP）、合并一票，或走 §2.2 串行链。
