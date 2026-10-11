BOOTSTRAP_DELIVERY = CANONICAL_FULL_TEXT（当前时代；与变体臂同槽位同版）

你的治理 bootstrap = 本 worktree 根部由 harness 机械投放的**当前时代**全套：

- S0  执行目标核验：`git rev-parse HEAD` 必须等于 EXPECTED_BASE_SHA（运行合同 §0；**最先**执行）。
- S1  读 `H2_RULES.md` 全文（当前 RULES.md 的全文副本；B 层不变量）。
- S2  判定任务风险级 LOW / MEDIUM / HIGH。
- S3  读 `CODEBUDDY.md` 全文（= 当前 AGENTS.md 的逐字全文 + 薄包装头/尾）；
      治理性 references 的读取一律使用 `H2_WARM/references/**` 副本（与投放同版）。
- S4  回执：确认 §0 结果；S4 槽 = 本臂全文投递面（`CODEBUDDY.md`）的完整读取状态。

```text
H2_RECEIPT = S0:<sha|MISMATCH> S1:<read|missing> S2:<LOW|MEDIUM|HIGH> S3:<targets|none> S4:<full|partial|missing>
```

（S3 槽 = 你实际查阅/加载的治理目标；无则 none。两臂同词表、同字段。）
