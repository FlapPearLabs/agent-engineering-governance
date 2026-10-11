BOOTSTRAP_DELIVERY = LEAN_CARRIER + ROUTING

你的治理 bootstrap = 本 worktree 根部的 `CODEBUDDY.md`（由 harness 机械投放的 lean HOT 载体；
**先完整读取它**，再按其执行）：

- S1  按其 §1：先读 RULES.md 全文。
- S2  判定任务风险级 LOW / MEDIUM / HIGH。
- S3  按其 §4 路由表**只**加载命中的 WARM 目标；Skill 按其 §5 处置；不预读全量。
- S4  核验：worktree HEAD 必须等于 EXPECTED_BASE_SHA；核验前不得声称任何 repo 状态。

完成后把一行回执写入报告 §A：

```text
H2_RECEIPT = S1:<read|missing> S2:<LOW|MEDIUM|HIGH> S3:<loaded targets|none> S4:<sha|MISMATCH>
```
