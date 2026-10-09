# RUN_B — t01 / the other arm（anonymous；解盲映射见 results.md）

> **SUPERSEDED — 见 `runs/README.md` §2。** 本文件是 t01 VARIANT 臂在**第一轮**的原始记录；
> 第二轮已将其重新记录为 `RUN_Q2.md`（opaque ID + 载体槽位归一化 + 编排者复验块）。
> 本文件保留原文不改，作为 v2 记录的**对照来源**；**不增加 run 计数**。
> 注意：本文件中的 `HOT_FILES_READ` 直接写出了载体文件名 —— 这正是被记录的匿名化缺陷
> （见 `results.md` §2 D2）。**不要**把本文件用作盲评输入。
>
> 匿名 run 记录。评估者先读本文件与 `RUN_A`，判定后再解盲。
> **记录纪律**：以下内容为执行 worker 的原始结构化报告，未经本轮改写；
> 明显错误处只做 `[fact-check]` 标注，不改写其自述。

```text
TASK_ID = t01
MODE = <ANONYMOUS>
BASE_SHA_VERIFIED = c08f6f8b3bbe57853a56adf3c2847e806bbb60a3
H1_RECEIPT = S1:read S2:LOW S3:references/review-and-repair-saturation.md S4:c08f6f8
HOT_FILES_READ = lean/CODEBUDDY.md:157, RULES.md:75
HOT_LINES_TOTAL = 232
WARM_FILES_LOADED = 1
SKILLS_LOADED = 0
TOOL_CALLS_APPROX = 63
TEST_RUNS = 8
REVIEW_CALLS = 0
WALL_CLOCK_APPROX_MIN = 25
HUMAN_INTERRUPTS = 0
VALID_COMPLETION = NO
```

[fact-check] `HOT_FILES_READ` 中的 `lean/CODEBUDDY.md` 是**变体臂的 bootstrap
载体**；该字段的存在本身会解盲。本轮如实保留该偏差并在此标注 —— 严格匿名化
本应把 bootstrap 载体归一化为 `AGENTS.md` 槽位。记录该 protocol 缺陷供后续轮次修正。

## 报告的高价值 finding

1. **任务前提缺陷（TASK_PREMISE_DEFECT）**：任务描述称该测试「makes a false
   pass in clean environments」；实测在干净树下产生 **hard FAIL**
   （`AssertionError: False is not true`），不是假通过。真实缺陷是
   「环境依赖导致该门在 CI 恒不可用 + reviewer 的 PASS 来自本机树」
   （N6 NO FALSE PASS 的证据面污染），而非门状态坍缩。按观察上报，未按描述改写。
2. **共享缓存别名（SHARED_CACHE_ALIASING）**：`scratch_tree()` 是模块级 memo。
   测试按字母序运行时，`test_consumer_accepts...` 先构建缓存副本；到本测试时
   副本早于文件创建时刻建成 —— **即使枚举逻辑完全损坏（误纳 ignored 文件）
   该断言也会通过**。以 `fresh_surface_tree()` 重新枚举修复，并加非空性断言
   防「空目录平凡排除」。
3. **阴性对照暴露**：在宿主预置真实 profile 后复跑，14/14 OK 且 md5 与内容逐字
   未变 —— 证明新逻辑不读、不写、不删真实宿主档案。

## 自述的 missed 项

- 未审计其余约 601 个测试中是否还有同类 machine-local false-pass 实例
  （仅做了定向 grep）。
- 未在真实 GitHub Actions runner 下执行（仅本地干净 env，**严格弱于** CI 保证）。
- 未确认 32 项 `test_skill_execution` 失败在无限制宿主上是否复现
  （根因仅断言到直接观测到的程度）。
  [fact-check] 编排者既有环境记录确认该 32 项失败为**沙箱性预存在失败**
  （SAFE_RETRIEVAL_UNAVAILABLE fallback），clean main 同样存在。

## 自述的 false / redundant 治理动作

- FALSE_GOVERNANCE_ACTIONS = 无（无门报未实跑的 PASS；`test_skill_execution`
  按 ENV_BLOCKED 类失败上报，未报 PASS 也未静默省略）
- REDUNDANT_GOVERNANCE_ACTIONS = 跑了两次 `scripts/tests` 全量 discover
  （一次取失败清单、一次按模块分类），第二次可避免

## 落盘事实（本轮独立核验，非 worker 自述）

```text
FILES_CHANGED = scripts/tests/test_p1_t16_gate_cli_entrypoint.py
模块 docstring 新增段落（L30-36）= "A test never inherits a precondition from
  the machine it happens to run on."，显式指向 build_local_profile_precondition
新增符号 = SYNTHETIC_LOCAL_PROFILE_BODY / build_local_profile_precondition
         / fresh_surface_tree / _materialise_surface（抽出复用）
fresh_surface_tree 实现 = 重新运行 _candidate_surface_paths(ROOT) 枚举，
  addCleanup 删除临时根；docstring 明确说明「memo 缓存会造成平凡通过」
fixture body = 固定字面量，声明无主机路径/登录名/端口
```

## 未闭环项（worker 自述）

- **阻断**：Bash 通道收尾阶段持续 exit 137 / SIGTERM，git status、stash drop、
  测试复跑均无法执行。三个后果需复核者接手：
  a) 仓库残留一个 stash（worker 自述 refs/stash = e6448c26…）需清理；
  b) 目标文件「恢复后」未复跑（Write 源与测试通过时的备份同一份、749 行一致，
     但严格意义上最终落盘状态未复验）；
  c) 建议在干净树重跑 `python3 -m unittest scripts.tests.test_p1_t16_gate_cli_entrypoint`。

[fact-check] 编排者已用 Read 独立核验 b)：落盘文件确含
`fresh_surface_tree`（L268-280）与 docstring 新增段（L30-36），
即 worker 的 Write 确实生效。**但编排者同样无法运行测试**（Bash 137），
故 14/14 OK 这一数字仍属 worker 自述，未经独立复跑。

## 反例 / 阴性对照证据（worker 自述，均在 SIGTERM 之前取得）

- 修复前该测试 FAIL（复现任务所述缺陷）
- 修复后 14/14 OK
- 阴性对照：移除枚举的 `--exclude-standard` → FAIL（`True is not false`），
  证明断言有牙齿且原版会空过
- 宿主预置 profile 场景 14/14 OK 且档案 md5 未变
- `validate_governance.py` 34/34；`unittest discover -s scripts/tests` 553 tests OK
- `validate_public_release.py` VIOLATIONS=0（text_scanned=88, 86 deduped）
- `--selftest` 51/51
- diff 扫描无 `songshiyao` / `/Users/` / `/tmp/h1-runs` 泄漏

## 约束遵守（worker 自述 + 编排者核验）

- 未 commit / 未 push / 未接触 remote ✔
- 未触碰 AGENTS.md / RULES.md / references/ / deployment/ / scripts/validate_*.py / .github/ ✔
- 无新依赖 ✔；CI 语义未改 ✔
- 原有 `exists()` 与 `check-ignore` 断言全部保留，无一条被削弱或删除 ✔
  （唯一删除的是宿主机存在性断言，由 fixture 建立 + exists 断言等价替代）
- 自我约束：S3 严格按路由表只加载 1 份 WARM；命中「MICRO/LOW 仅改 fixture」行；
  未加载架构/状态/持久化类 reference；无 ESCALATED_LOAD ✔
