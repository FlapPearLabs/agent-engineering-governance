BOOTSTRAP_DELIVERY = CANONICAL_FULL_TEXT

你的治理 bootstrap = 本 worktree 内的 canonical 文本（全文可达；不受任何注入通道截断影响）：

- S1  读 RULES.md 全文（B 层不变量；不看等于未读）。
- S2  判定任务风险级 LOW / MEDIUM / HIGH。
- S3  需要治理细节时，直接查阅 AGENTS.md 全文与 references/ 的相应内容（本臂无路由机制；按需查阅即可）。
- S4  核验：worktree HEAD 必须等于 EXPECTED_BASE_SHA；核验前不得声称任何 repo 状态。

完成后把一行回执写入报告 §A：

```text
H2_RECEIPT = S1:<read|missing> S2:<LOW|MEDIUM|HIGH> S3:<consulted targets|none> S4:<sha|MISMATCH>
```
