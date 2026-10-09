# RUN_K7 — t01 / one arm（anonymous）

> 匿名 run 记录。评估者先读本文件与 `RUN_Q2`，判定后再解盲。
> **匿名化规约（v2）**：bootstrap 载体一律归一化为 `PRIMARY_BOOTSTRAP` 槽位；
> 路由表一律称 `THE_ROUTING_TABLE`；不出现 arm 名称、载体文件名或可识别 arm 的路径。
> **记录纪律**：内容为执行 worker 的原始结构化报告，未经改写；错误处只做 `[fact-check]` 标注。
>
> [v2-CORRECTION 2026-10-09] 本记录在 v2 重写时曾把行数三元组误记为 `145 / 76 / 221`
> （那是同批 t02 记录的数字，非本次 run 的数字）。已按**原始记录 `RUN_A`** 恢复为
> `150 / 75 / 225`。原始记录仍在 `RUN_A.md` 中保留（superseded，见 `runs/README.md`），
> 是本次更正的对照来源。该错误影响的是记录转录，不影响该 run 的执行结果。

```text
RUN_ID = RUN_K7
TASK_ID = t01
MODE = <ANONYMOISED>
PRIMARY_BOOTSTRAP_LINES = 150
MANDATORY_READ_LINES = 75
HOT_LINES_TOTAL = 225
WARM_FILES_LOADED = 0
SKILLS_LOADED = 0
TEST_RUNS_APPRX = 6
WALL_CLOCK = NOT_OBSERVABLE
HUMAN_INTERRUPTS = 0
SELF_REPORTED_VALID_COMPLETION = NO
```

## 报告的高价值 finding

1. **任务前提方向被实测推翻**：任务描述称该测试在干净环境「false pass」；实测在本
   干净树中它是 **hard FAIL**，不是假通过。按观察上报，**未按描述改写断言**。
2. **原测试存在空洞通过路径**：共享的 `scratch_tree()` 是模块级缓存；若在fixture
   存在前已构建，`(scratch_tree()/local_rel).exists()` 断言即为平凡真。
3. 发现仓内已有可复用的 fixture 建造范式。

## 自述的 missed 项

- 未能核实「CI 实际执行树」的workflow checkout 细节。

## 自述的 false / redundant 治理动作

- FALSE_GOVERNANCE_ACTIONS = 无
- REDUNDANT_GOVERNANCE_ACTIONS = 未预读 `references/*`（自述依据：LOW 票最小 grounding）

## 落盘事实（编排者独立核验，非 worker 自述）

```text
FILES_CHANGED = 1（scripts/tests/test_p1_t16_gate_cli_entrypoint.py）
新增符号 = LOCAL_PROFILE_RELATIVE / LOCAL_PROFILE_FIXTURE
fixture 内容 = 纯占位符表格，无真实主机路径、端口、版本或本机 OS 身份
字面量构造 = 以字符串拼接构造，注释自述目的：避免成为可被 TIER-A 扫描命中的连续字面量
DIFF_STAT = +130 / -23
```

## 未闭环项（worker 自述）

- 最后一次死代码清理之后，执行环境被 SIGTERM 终止（`echo` 亦返回 137），该次清理后的
  最终全绿未经 worker 实测。

## 反例证据（worker 自述，均在 SIGTERM 之前取得）

- 反例 1：移除 .gitignore 中该行 → RED
- 反例 2：削弱枚举逻辑去掉 `--exclude-standard` → RED，点名 fixture 出现在候选面
- 宿主 profile 保护：预置含真实内容的该文件，跑完测试 OK，md5 前后一致
- 清理：fixture 走 addCleanup；运行后 `deployment/` 无该文件

## 编排者独立复验（本轮新增；worker 自述的 GREEN 已获独立证据）

```text
HEAD_SHA_MATCHES_EXPECTED_BASE = YES（c08f6f8b…，detached）
DIFF_CHECK_CLEAN = YES
APPLICABLE_TESTS        = 14 tests / OK
FULL_REGRESSION         = 553 tests / OK
VALIDATE_GOVERNANCE     = 34/34 checks passed
PUBLIC_RELEASE          = VIOLATIONS=0（text_scanned=88, deduped=86）
RESIDUE_IN_DEPLOYMENT   = NONE（fixture 未残留）
WORKER_SELF_REPORT      = NO  →编排者复跑后 = YES（差异归因见 results.md §D4）
```

[fact-check] 137阻塞在本轮被独立复现后**已恢复**；恢复后的复跑证明该臂改动确实全绿。
上一轮记为 `VALID_COMPLETION = NO` 的原因是环境阻塞，不是该臂的质量缺陷。