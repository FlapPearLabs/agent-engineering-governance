# H2 run registry（非 canonical）

> 本文件是 H2 实验 **run 身份的唯一注册表**。`results.md` 与 `README.md` 只引用此处，
> 不另行定义。§1 的计划表在冻结时写死；**执行顺序与 arm 分配不得更改**。
> 状态取值：`PLANNED` / `VALID` / `INVALID` / `BLOCKED`（BLOCKED = 环境阻塞；
> **禁止静默重跑** —— 阻塞后的重试 = 新登记行 + 原因，或按 protocol §8 作废）。
> **臂序对消**（bot review 处置）：同一任务内不固定"先对照后变体"；重复对之间 C/V 次序
> **互换**，不可重复的 t01/t02 在任务间交替 —— 消除"臂与时刻"完全相关的时间混杂。

## 1. 冻结的 run 计划（N_TOTAL = 20；arm 映射即本表）

| # | RUN_ID | TASK | ARM | REP | BLOCK | STATUS | 记录文件 |
|---|--------|------|-----|-----|-------|--------|----------|
| 1 | H2-R01 | t01 | control | 1 | 1 | PLANNED | runs/H2-R01/ |
| 2 | H2-R02 | t01 | variant | 1 | 1 | PLANNED | runs/H2-R02/ |
| 3 | H2-R03 | t02 | variant | 1 | 1 | PLANNED | runs/H2-R03/ |
| 4 | H2-R04 | t02 | control | 1 | 1 | PLANNED | runs/H2-R04/ |
| 5 | H2-R05 | t03 | control | 1 | 1 | PLANNED | runs/H2-R05/ |
| 6 | H2-R06 | t03 | variant | 1 | 1 | PLANNED | runs/H2-R06/ |
| 7 | H2-R07 | t04 | variant | 1 | 1 | PLANNED | runs/H2-R07/ |
| 8 | H2-R08 | t04 | control | 1 | 1 | PLANNED | runs/H2-R08/ |
| 9 | H2-R09 | n01 | control | 1 | 1 | PLANNED | runs/H2-R09/ |
| 10 | H2-R10 | n01 | variant | 1 | 1 | PLANNED | runs/H2-R10/ |
| 11 | H2-R11 | n02 | variant | 1 | 1 | PLANNED | runs/H2-R11/ |
| 12 | H2-R12 | n02 | control | 1 | 1 | PLANNED | runs/H2-R12/ |
| 13 | H2-R13 | t03 | variant | 2 | 2 | PLANNED | runs/H2-R13/ |
| 14 | H2-R14 | t03 | control | 2 | 2 | PLANNED | runs/H2-R14/ |
| 15 | H2-R15 | t04 | control | 2 | 2 | PLANNED | runs/H2-R15/ |
| 16 | H2-R16 | t04 | variant | 2 | 2 | PLANNED | runs/H2-R16/ |
| 17 | H2-R17 | n01 | variant | 2 | 2 | PLANNED | runs/H2-R17/ |
| 18 | H2-R18 | n01 | control | 2 | 2 | PLANNED | runs/H2-R18/ |
| 19 | H2-R19 | n02 | control | 2 | 2 | PLANNED | runs/H2-R19/ |
| 20 | H2-R20 | n02 | variant | 2 | 2 | PLANNED | runs/H2-R20/ |

复制声明：`REPLICATION_UNIT = task-shape × arm`（见 `task-registry.json#replication`）；
每 shape 每臂恰 2；t03/t04/n01/n02 另有 per-task ×2；t01/t02 为 per-task n=1（shape 级 2）。
臂序：t03 rep1=C-first / rep2=V-first；t04 rep1=V-first / rep2=C-first；n01 rep1=C-first /
rep2=V-first；n02 rep1=V-first / rep2=C-first；t01 C-first、t02 V-first（不可重复，任务间交替）。

## 2. 有效 run（完成时逐行回填 receipt 摘要）

判定为 VALID 的 run 记录：`EXPECTED_BASE == ACTUAL_HEAD`（prepare 断言 + worker S0 回报）、
投递 receipt（materials_commit + 各投放物 sha256）、collect 结果（diff sha256 / telemetry
sha256 / carrier-recheck 全 OK）、acceptance 结果、auditor 结论。

```text
（待回填：RUN_ID / ARM / TASK / BASE / CARRIER_HASH / DIFF_SHA256 / ACCEPTANCE / REVIEW）
```

## 3. 无效 / 阻塞 run（保留、登记、不纳入统计、禁止 silent rerun）

```text
（待回填；原因枚举见 protocol §8）
RUN_ID / ARM / TASK_ID / INVALID_REASON / DISCOVERY_TIME / ARTIFACT_PATH
```

## 4. 与材料自检的一致性

`experiments/v1.2/tests/test_v1_2_h2_material.py` 校验：计划表 20 行与
`harness/run-plan.json` 逐行一致（run_id/task/arm/rep/block）；臂序对消属性；
冻结 hash（manifest ↔ 测试字面量 ↔ 文件字节）三方一致。逐 run 状态的最终一致性由闭环轮复核。
