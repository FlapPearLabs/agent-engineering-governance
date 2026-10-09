# RUN_B9 — t02 / one arm（anonymous）

> 匿名 run 记录。评估者先读本文件与 `RUN_M4`，判定后再解盲。
> **匿名化规约（v2）**：bootstrap 载体归一化为 `PRIMARY_BOOTSTRAP`；路由表称
> `THE_ROUTING_TABLE`；不出现 arm 名称、载体文件名或可识别 arm 的路径。

```text
RUN_ID = RUN_B9
TASK_ID = t02
MODE = <ANONYMOISED>
PRIMARY_BOOTSTRAP_LINES = 145
MANDATORY_READ_LINES = 76
HOT_LINES_TOTAL = 221
WARM_FILES_LOADED = 8
SKILLS_LOADED = 0
TEST_RUNS = 8
WALL_CLOCK = ~9 min of task execution (host latency inflated it)
SELF_REPORTED_VALID_COMPLETION = YES
```

## 报告的高价值 finding

1. **真实correctness 缺陷但落在禁改路径**：`scripts/validate_project_state.py:158` 有
   一处真实 dead store（F841），而该路径被本任务 scope 禁止修改。以`per-file-ignores`
   钉住并附移除条件，而非静默吸收或非法编辑。
2. **4 处在允许范围内的 F841 修复**，逐一验证行为中性。
3. **CI Python 版本与本地不一致**：CI provisions 3.12，本地 3.13.12 → target-version
   钉到 py312，使门与解释器无关。
4. **门未被任何 CI job 调用**（`.github/` 在禁改目录）—— 已配置且本地验证，但**未被
   强制执行**。自报为本次交付的最大缺口。
5. **`select` 集可被静默清空而CI 仍绿**：把 select 改为 `[]` 后门完全失明且退出码为 0，
   而治理校验器 32 项检查无一覆盖 `ruff.toml`。历史提交曾有 `ci-executes-static-gate`
   检查，但不在本base。

## 自述的 missed 项

- 从未在 Python 3.12 下跑过该门（本机只有 3.13.12）—— py312 target-version 是从CI 配置
  断言的，非实证。
- 未加「门配置自身不被篡改」的测试 —— 配置可能静默漂移到风格规则。
- 未验证门在其他 ruff 版本下的行为。

## 自述的 false / redundant 治理动作

- FALSE_GOVERNANCE_ACTIONS = 两条**负控本身有缺陷**：第一次设`select=["E9"]` 同时
  `ignore=["F841"]`，等于关掉了被测规则，控制「无法失败」；第二次因状态泄漏而出现
  假通过（继承了前一次的 select）。两者都是通过断言配置内容而非信任退出码发现的。
- REDUNDANT_GOVERNANCE_ACTIONS = 末尾重复跑了一次全量检查（因状态泄漏事故后的防御性
  复跑，属正当）

## 基线（配置前实测）

```text
ruff 0.15.18, 无配置：Found19 errors = E702 x13 + F841 x5 + E402 x1
分类探针：E9=0, F=5, E4=1
测试基线：scripts/tests 423 OK；workbuddy 42 OK；zcode 90 跑 / 23 errors（预存在）
```

## 负控

```text
NC1注入 F841 未定义符号 → 门 FAILED exit 1 → 探针删除后恢复 exit 0
NC2  移除 per-file-ignores → 门 FAILED（点名 validate_project_state.py:158）→ 恢复 exit 0
NC3  在自己编辑过的文件里注入 dead store → 门 FAILED（证明 F841 在改动文件内真被强制）
STYLE-SCOPE 对照：--select E4,E7 → exit 1, 14 errors 仍存在且故意不强制
                ⇒ 确认未做legacy 风格迁移，select 未被扩大
```

## 验证结果

```text
TESTS_RESULT = scripts/tests 423 OK；workbuddy 42 OK；zcode 90 跑 / 23 errors（前后同）
VALIDATE_GOVERNANCE = 32/32 checks passed
PUBLIC_RELEASE_VIOLATIONS = 0
PREEXISTING_FAILURES = zcode 23 errors —— 非本改动造成，证据：
   (a) 前后失败集合逐项相同   (b) traceback 止于宿主 shim 的 mkdir broker
   (c) `env -u PYTHONPATH` 下 90/90 OK
FILES_CHANGED = ruff.toml(新增) + 3 个测试文件（3 处 F841 修复）
DIFF_STAT = tracked 3 files, +3/-4；ruff.toml 新增 27 行
VALID_COMPLETION = YES
```

[fact-check] 编排者独立核验：worktree HEAD = 015780be…（与预期 base 一致）；改动为
新增 `ruff.toml` + 3 个测试文件；**canonical 治理面未被触碰**。