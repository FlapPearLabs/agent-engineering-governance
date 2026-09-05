# SCENARIO_VALIDATION — 候选治理十场景校验

> 校验对象：候选 `AGENTS.md` / `RULES.md` / `references/*`。方法：语义推演（本审计不建运行时）。

| # | 场景 | 候选治理中的依据 | 预期行为 | 校验结论 |
|---|---|---|---|---|
| S1 | 简单低风险文档票 | AGENTS §Lane 风险矩阵 LOW 行：最小 grounding、聚焦检查、L1 或机器核验、无三方评审 | 不触发 T09 式全链；当日完成 | PASS — LOW 通道明确排除 third-party/post-CI |
| S2 | 已知缝上的中等特性票 | 矩阵 MEDIUM 行 + REF:ticket-lane 全链 | CodeGraph grounding + 合同抽取 + 反例 TDD + L1 独立评审 + 真 CI；无 L2 | PASS |
| S3 | 高风险持久化/状态票 | 矩阵 HIGH/CRITICAL 行 | 强反例（5–10）+ fresh/adversarial 评审 + 有界修复 + CI/post-CI gate；必要时 L2 外部 | PASS |
| S4 | 评审员两轮后抛出 4 个合成变体 | RULES R13 + REF saturation：`SEVERITY != REPAIR_AUTHORITY`、`ARBITRARY_SYNTHETIC_STATE` 不自动授权加固、budget=2 | 无自动 R3+；进入 Arbiter（REPAIR_MORE/SATURATION/…五选一）；合成变体记 BACKLOG_LONG_TAIL | PASS — 新案例≠新信息已硬编码 |
| S5 | worker 在 /implement 中发现架构冲突 | AGENTS worker 边界（MAY NOT 修改冻结 Spec/DAG）+ R14 + STOP 枚举 CONTRACT_CONFLICT | STOP/ESCALATE，不得静默重设计；产物为最小决策包 | PASS |
| S6 | 三个独立就绪票 | AGENTS §Stage：frontier 只是合法集，编组考虑写权/爆炸半径/内聚/成本 | Orchestrator 选内聚 Stage（可能 2+1 拆分），非 START_ALL | PASS — Stage 层为非默认语义，评审重点核对 |
| S7 | 新票 worktree 启动但 master 已有健康图 | REF:codegraph-grounding：canonical graph + delta sync；全量重建仅健康触发 | 复用 + 增量同步；记录 base SHA；无重建仪式 | PASS |
| S8 | CI 疑似基线失败 | RULES R7 + REF:git-ci-integration 证据块 | worker 仅 PROPOSAL_ONLY；独立证据（base 复现+签名比对）+ REVIEWER_ACCEPTED_CLASSIFICATION=YES 才接受 | PASS |
| S9 | 评审修复改变候选 SHA | RULES R5 | 旧评审对变更代码失效；delta 评审（blast radius 未扩张不重读全仓） | PASS |
| S10 | 另一模块已拥有 canonical validation | AGENTS seam/ownership + REF saturation ROUTE_TO_OWNER；zhihu 教训（不得造第二个弱校验） | 复用权威；不建重复弱校验；finding 处置记 ROUTE_TO_OWNER | PASS |

## 结论

- 10/10 场景在候选语义下产出预期行为。
- 语义风险点（需外部评审重点看）：S4（饱和判据可被滥用提前放行——由"高价值 blocker 永远阻塞"兜底）、S6（Stage 编组保守/激进平衡——由编组输入清单与 Stage Packet 事后审计兜底）、S7（delta 陈旧风险——由 base SHA 记录 + 健康触发重建兜底）。
