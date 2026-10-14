# H2 run registry（非 canonical）

> 本文件是 H2 实验 **run 身份与终态的唯一权威来源**。下表即权威数据；prose 不重复声明状态。
> §1 = Round 1 终态表；§2 = Round 2 冻结表。**执行顺序与 arm 分配不得更改。**
> 状态取值：`PLANNED` / `VALID` / `INVALID` / `BLOCKED` / `CANCELLED_ROUND_INVALID` /
> `FROZEN_NOT_EXECUTED`。`CANCELLED_ROUND_INVALID` = 该身份因所属 round 整体作废而从未执行。
> **禁止静默重跑** —— 阻塞后的重试 = 新登记行 + 原因，或按 protocol §8 作废。
> **臂序对消**：同一任务内不固定"先对照后变体"；重复对之间 C/V 次序**互换**，不可重复的
> t01/t02 在任务间交替 —— 消除"臂与时刻"完全相关的时间混杂。
> 机器一致性由 `experiments/v1.2/tests/test_v1_2_h2_run_registry.py` 强制。

## 1. Round 1（H2-R1）— CLOSED / INVALID（终态表，权威）

Round 1 因 `GLOBAL_HARNESS_CONTRACT_DEFECT` 整体关闭：`VALID_RUNS = 0` / `INVALID_RUNS = 1` /
`H2_RESULT = NOT_PRODUCED`（状态 = `EXPERIMENT_NOT_VALIDLY_STARTED`，**不是**
`INSUFFICIENT_EVIDENCE` —— 后者留给有效执行但证据不足的情形）。结案记录 `round-1-closure.md`；
R01 产物 `runs/H2-R1-R01/`（占位符脱敏，无本机路径）。

| # | RUN_ID | TASK | ARM | REP | BLOCK | STATUS | 记录文件 |
|---|--------|------|-----|-----|-------|--------|----------|

| 1 | H2-R01 | t01 | control | 1 | 1 | INVALID | runs/H2-R1-R01/ |
| 2 | H2-R02 | t01 | variant | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 3 | H2-R03 | t02 | variant | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 4 | H2-R04 | t02 | control | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 5 | H2-R05 | t03 | control | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 6 | H2-R06 | t03 | variant | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 7 | H2-R07 | t04 | variant | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 8 | H2-R08 | t04 | control | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 9 | H2-R09 | n01 | control | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 10 | H2-R10 | n01 | variant | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 11 | H2-R11 | n02 | variant | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 12 | H2-R12 | n02 | control | 1 | 1 | CANCELLED_ROUND_INVALID | (never executed) |
| 13 | H2-R13 | t03 | variant | 2 | 2 | CANCELLED_ROUND_INVALID | (never executed) |
| 14 | H2-R14 | t03 | control | 2 | 2 | CANCELLED_ROUND_INVALID | (never executed) |
| 15 | H2-R15 | t04 | control | 2 | 2 | CANCELLED_ROUND_INVALID | (never executed) |
| 16 | H2-R16 | t04 | variant | 2 | 2 | CANCELLED_ROUND_INVALID | (never executed) |
| 17 | H2-R17 | n01 | variant | 2 | 2 | CANCELLED_ROUND_INVALID | (never executed) |
| 18 | H2-R18 | n01 | control | 2 | 2 | CANCELLED_ROUND_INVALID | (never executed) |
| 19 | H2-R19 | n02 | control | 2 | 2 | CANCELLED_ROUND_INVALID | (never executed) |
| 20 | H2-R20 | n02 | variant | 2 | 2 | CANCELLED_ROUND_INVALID | (never executed) |
> H2-R1-R01: `invalid_reason = GLOBAL_HARNESS_CONTRACT_DEFECT`,
> `worker_episode = workbuddy-agent-8c1a4d7e2f94b60`（已持久化 —— INVALID run ≠ 不存在的 run，Round 2
> 不得复用该 executor context）。

## 2. Round 2（H2-R2）— FROZEN / NOT_EXECUTED（权威；身份不复用 Round 1）

Round 2 使用全新身份命名空间；Round 1 的行号与身份**永不复用**。冻结哈希集与 review 门见
`round-2-freeze.json`；计划权威见 `harness/run-plan-r2.json`。

| # | RUN_ID | TASK | ARM | REP | BLOCK | STATUS | 记录文件 |
|---|--------|------|-----|-----|-------|--------|----------|

| 1 | H2-R2-R01 | t01 | control | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R01/ |
| 2 | H2-R2-R02 | t01 | variant | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R02/ |
| 3 | H2-R2-R03 | t02 | variant | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R03/ |
| 4 | H2-R2-R04 | t02 | control | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R04/ |
| 5 | H2-R2-R05 | t03 | control | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R05/ |
| 6 | H2-R2-R06 | t03 | variant | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R06/ |
| 7 | H2-R2-R07 | t04 | variant | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R07/ |
| 8 | H2-R2-R08 | t04 | control | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R08/ |
| 9 | H2-R2-R09 | n01 | control | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R09/ |
| 10 | H2-R2-R10 | n01 | variant | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R10/ |
| 11 | H2-R2-R11 | n02 | variant | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R11/ |
| 12 | H2-R2-R12 | n02 | control | 1 | 1 | FROZEN_NOT_EXECUTED | runs/H2-R2-R12/ |
| 13 | H2-R2-R13 | t03 | variant | 2 | 2 | FROZEN_NOT_EXECUTED | runs/H2-R2-R13/ |
| 14 | H2-R2-R14 | t03 | control | 2 | 2 | FROZEN_NOT_EXECUTED | runs/H2-R2-R14/ |
| 15 | H2-R2-R15 | t04 | control | 2 | 2 | FROZEN_NOT_EXECUTED | runs/H2-R2-R15/ |
| 16 | H2-R2-R16 | t04 | variant | 2 | 2 | FROZEN_NOT_EXECUTED | runs/H2-R2-R16/ |
| 17 | H2-R2-R17 | n01 | variant | 2 | 2 | FROZEN_NOT_EXECUTED | runs/H2-R2-R17/ |
| 18 | H2-R2-R18 | n01 | control | 2 | 2 | FROZEN_NOT_EXECUTED | runs/H2-R2-R18/ |
| 19 | H2-R2-R19 | n02 | control | 2 | 2 | FROZEN_NOT_EXECUTED | runs/H2-R2-R19/ |
| 20 | H2-R2-R20 | n02 | variant | 2 | 2 | FROZEN_NOT_EXECUTED | runs/H2-R2-R20/ |
