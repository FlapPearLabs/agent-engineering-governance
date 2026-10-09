# H1 run registry（非 canonical）

> 本文件是 H1 实验 **run 身份的唯一注册表**。`results.md` 与 `README.md` 只引用此处，
> 不另行定义。目的：让「哪些算 run、哪些不算、每个 run 属于哪个 task/arm/base」
> 可被机械核验，不依赖散文叙述。

## 1. 有效 run（VALID_RUNS = 8）

每个 run 声明：`EXPECTED_REPO == ACTUAL_REPO`、`EXPECTED_WORKTREE == ACTUAL_WORKTREE`、
`EXPECTED_BASE_SHA == ACTUAL_HEAD_AT_START`。

```text
EXPECTED_REPO = FlapPearLabs/agent-engineering-governance
EXPECTED_WORKTREE_PATTERN = /tmp/h1-runs/<task>__<arm>   （git worktree，detached HEAD）
```

| # | RUN_ID | 记录文件 | TASK | ARM | REPLAY_BASE_SHA | 记录内自报 MATCH |
|---|---|---|---|---|---|---|
| 1 | `RUN_K7` | `RUN_K7.md` | t01 LOW | CONTROL | `c08f6f8b3bbe57853a56adf3c2847e806bbb60a3` | YES |
| 2 | `RUN_Q2` | `RUN_Q2.md` | t01 LOW | VARIANT | `c08f6f8b3bbe57853a56adf3c2847e806bbb60a3` | YES |
| 3 | `RUN_B9` | `RUN_B9.md` | t02 MEDIUM | CONTROL | `015780be7a3f863c05509b437e4e586b4f388794` | YES |
| 4 | `RUN_M4` | `RUN_M4.md` | t02 MEDIUM | VARIANT | `015780be7a3f863c05509b437e4e586b4f388794` | YES |
| 5 | `RUN_Z8` | `RUN_Z8.md` | t03 HIGH | CONTROL | `af4df6ae706394db5f9dec313993312392aeb516` | YES |
| 6 | `RUN_T1` | `RUN_T1.md` | t03 HIGH | VARIANT | `af4df6ae706394db5f9dec313993312392aeb516` | YES |
| 7 | `RUN_W6` | `RUN_W6.md` | t04 HIGH | CONTROL | `e1da1541eb2b11f1e44f972409abde701496f4b6` | YES |
| 8 | `RUN_P3` | `RUN_P3.md` | t04 HIGH | VARIANT | `e1da1541eb2b11f1e44f972409abde701496f4b6` | YES |

`ARM` 一列在本轮为**已解盲**映射：`BLIND_EVALUATION = VOID`（见 `results.md` §7），
且该映射已由 `results.md` §5 公开。此处并列记录是为了让「同任务两臂是否真的跑在
同一 base」可被逐行核验。

### 1.1 base 可达性（编排者机械核验）

四个 replay base 在对象库中均为 commit（`git cat-file -t` = `commit`）：

```text
c08f6f8b…  commit       015780be…  commit
af4df6ae…  commit       e1da1541…  commit
```

### 1.2 复验条件的退化（必须记录）

```text
REPLAY_WORKTREE_REVERIFIABLE_NOW = NO
原因：8 个 replay worktree 位于 /tmp/h1-runs/，已被系统清理；
      `git worktree list` 对应条目现为 prunable。
后果：run 当时的 base 断言无法在事后重新在该目录上核验。
可用替代：记录内自报（worker 侧）+ 编排者投递前的机械断言 + 四个 base 仍可解析
         + run 记录内的 [fact-check] 块。
不足：本实验**未**保留 replay worktree 的持久副本，因此 run 实际产出的 diff
      不能事后重放。这是证据耐久性缺口，已列入复现前置条件（results.md §11）。
```

## 2. 被取代的原始记录（SUPERSEDED，不计入 run 数）

`RUN_A.md` / `RUN_B.md` 是 t01 两臂在**第一轮**的原始记录。第二轮为满足匿名化要求
将其重新记录为 `RUN_K7` / `RUN_Q2`（opaque ID + 载体槽位归一化 + 追加编排者复验块）。

| 原始记录 | 被取代为 | 关系 |
|---|---|---|
| `RUN_A.md` | `RUN_K7.md` | **同一次 run**（t01 / CONTROL / base c08f6f8） |
| `RUN_B.md` | `RUN_Q2.md` | **同一次 run**（t01 / VARIANT / base c08f6f8） |

```text
COUNTING_RULE: RUN_A / RUN_B 不增加 run 计数。
  它们是同一批执行的早期记录形式，保留是为了给 v2 记录提供**对照来源** ——
  这一点已被证明必要：v2 重写时 RUN_K7 的行数三元组被转录成 t02 的数字，
  正是靠 RUN_A 才发现并更正（见 RUN_K7.md 的 [v2-CORRECTION] 块）。
```

## 3. 作废 run（INVALID_RUNS = 2，永久排除）

作废 run **无记录文件**（在形成记录前即被判定无效），但其身份与原因必须保留在此，
不得删除、不得并入任何 aggregate。

| # | 标识 | TASK/ARM | 作废原因 | 归因 | 证据 |
|---|---|---|---|---|---|
| 1 | `INVALID_001` | t01 首对（两臂） | worker 实际运行在 governance HEAD `a7f9e7c`，而非 replay base `c08f6f8`。该 HEAD 上 t01 的缺陷**已被修复**，故任务成为 no-op；两臂都正确地拒绝编造改动。 | **harness 缺陷**（编排者 prompt 未写入 worktree 绝对路径） | `results.md` §4；已核实 `6d841d5` 是 `a7f9e7c` 的祖先、该断言在 HEAD 上 grep 0 命中 |
| 2 | `INVALID_002` | t02 VARIANT 首跑 | harness 未把 bootstrap 载体（`CODEBUDDY.md`）放入 worktree 根 ⇒ 该臂 HOT 面按 `BOOTSTRAP_CONTRACT` §1 fallback 链回落到 `AGENTS.md` ⇒ **两臂 bootstrap 相同，自变量未建立**。 | **harness 缺陷**（worker 严格按合同 fallback 处理，行为正确） | `results.md` §4；编排者事后实测该 worktree 根无载体、`find` 0 命中 |

```text
INVALID_001_CLASS = WRONG_EXECUTION_TARGET
INVALID_002_CLASS = TREATMENT_NOT_ESTABLISHED
两者均非 worker 质量缺陷，且均未并入任何配对比较。
```

## 4. 与 `results.md` 的一致性

本注册表与 `results.md` 的一致性由材料自检机械校验
（`experiments/v1.2/tests/test_h1_material.py::TestRunRegistry`）：
文件集合、run 数、无 arm 标签、以及作废 run 的保留性。
