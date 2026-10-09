# RUN_A — t01 / one arm（anonymous；解盲映射见 results.md）

> **SUPERSEDED — 见 `runs/README.md` §2。** 本文件是 t01 CONTROL 臂在**第一轮**的原始记录；
> 第二轮已将其重新记录为 `RUN_K7.md`（opaque ID + 载体槽位归一化 + 编排者复验块）。
> 本文件保留原文不改，作为 v2 记录的**对照来源**；**不增加 run 计数**。
>
> 匿名 run 记录。评估者先读本文件与 `RUN_B`，判定后再解盲。
> **记录纪律**：以下内容为执行 worker 的原始结构化报告，未经本轮改写；
> 明显错误处只做 `[fact-check]` 标注，不改写其自述。

```text
TASK_ID = t01
MODE = <ANONYMOUS>
BASE_SHA_VERIFIED = c08f6f8b3bbe57853a56adf3c2847e806bbb60a3
HOT_FILES_READ = AGENTS.md:150, RULES.md:75
HOT_LINES_TOTAL = 225
WARM_FILES_LOADED = 0
SKILLS_LOADED = 0
TOOL_CALLS_APPROX = 41
TEST_RUNS = 6
REVIEW_CALLS = 0
WALL_CLOCK_APPROX_MIN = NOT_OBSERVABLE
HUMAN_INTERRUPTS = 0
VALID_COMPLETION = NO
```

## 报告的高价值 finding

1. **任务前提方向被实测推翻**（worker 原文要点）：任务描述称该测试在干净环境
   「false pass」；实测在本干净树中它是 **hard FAIL**（line 512），不是假通过。
   worker 明确按观察上报，**未按描述改写断言**。
2. **原测试存在空洞通过路径**：共享的 `scratch_tree()` 是模块级缓存；若在
   fixture 存在前已构建，`(scratch_tree()/local_rel).exists()` 断言即为平凡真。
3. 发现仓内已有可复用的 fixture 建造范式（`validate_public_release.py` 的
   selftest 在 base/ 子目录内合成）。

## 自述的 missed 项

- 未能核实「CI 实际执行树」的 workflow checkout 细节（`.github/` 在禁改目录，
  仅读未读）。

## 自述的 false / redundant 治理动作

- FALSE_GOVERNANCE_ACTIONS = 无
- REDUNDANT_GOVERNANCE_ACTIONS = 未预读 `references/*`（自述依据：LOW 票最小 grounding，
  且 R2 语义已由 RULES.md 全文覆盖）

## 落盘事实（本轮独立核验，非 worker 自述）

```text
FILES_CHANGED = scripts/tests/test_p1_t16_gate_cli_entrypoint.py
新增符号 = LOCAL_PROFILE_RELATIVE / LOCAL_PROFILE_FIXTURE
fixture 内容 = 纯占位符表格（<HOST_OS> / <LOCAL_PROXY_URL> / ${HOME}），
              无真实主机路径、端口、版本或本机 OS 身份
字面量构造 = "# deployment-profile.local" + "\n\n" 拼接而成，
              注释自述目的：避免成为可被 TIER-A 扫描命中的连续字面量
```

## 未闭环项（worker 自述）

- 最后一次死代码清理（移除未读取的局部变量）之后，执行环境被 SIGTERM 终止
  （`echo` 亦返回 137），**该次清理后的最终全绿未经实测**。
- 清理前同等逻辑版本已实测 14/14 OK 且两个反例均 RED。
- 沙箱拒绝 `git init` / `git add` / 跨 worktree 写入 /tmp/cleanenv*，
  未构造第二棵 git 仓库做对照（自述为环境约束，非跳过验证）。

[fact-check] 137 阻塞已被本轮编排者独立复现：编排者的 Bash 通道在同一时段
对包括裸 `echo` 在内的所有命令返回 exit 137。属环境级故障，非 worker 独有问题。

## 反例证据（worker 自述，均在 SIGTERM 之前取得）

- 反例 1：移除 .gitignore 中该行 → RED
  （"must be gitignored for the fixture to be excluded by construction"）
- 反例 2：削弱 `_candidate_surface_paths` 去掉 `--exclude-standard` → RED，
  明确点名 `deployment/deployment-profile.local.md` 出现在候选面
- 宿主 profile 保护：预置含 "REAL HOST PROFILE" 的该文件，跑完 14 tests OK，
  md5 前后一致（2eec60d7…）
- 清理：fixture 走 addCleanup；运行后 deployment/ 无该文件

## 约束遵守（worker 自述 + 编排者核验）

- 未 commit / 未 push / 未接触 remote ✔（编排者核验：worktree 为 detached HEAD）
- 未触碰 AGENTS.md / RULES.md / references/ / deployment/ / scripts/validate_*.py / .github/ ✔
- 无新依赖 ✔（diff 中无 requirements/ruff.toml 变更）
- CI 语义未改 ✔
- 未读取 `experiments/v1.2/h1-hot-context/` ✔（自述 git grep 时以 `:!experiments` 排除）
