# RUN_Q2 — t01 / the other arm（anonymous）

> 匿名 run 记录。评估者先读本文件与 `RUN_K7`，判定后再解盲。
> **匿名化规约（v2）**：bootstrap 载体一律归一化为 `PRIMARY_BOOTSTRAP` 槽位；
> 路由表一律称 `THE_ROUTING_TABLE`；不出现 arm 名称、载体文件名或可识别 arm 的路径。
> **记录纪律**：内容为执行 worker 的原始结构化报告，未经改写；错误处只做 `[fact-check]` 标注。

```text
RUN_ID = RUN_Q2
TASK_ID = t01
MODE = <ANONYMOISED>
H1_RECEIPT = S1:read S2:LOW S3:one WARM ref via THE_ROUTING_TABLE S4:<sha>
PRIMARY_BOOTSTRAP_LINES = 157
MANDATORY_READ_LINES = 75
HOT_LINES_TOTAL = 232
WARM_FILES_LOADED = 1
SKILLS_LOADED = 0
TEST_RUNS_APPRX = 8
WALL_CLOCK_APPROX_MIN = 25
HUMAN_INTERRUPTS = 0
SELF_REPORTED_VALID_COMPLETION = NO
```

## 报告的高价值 finding

1. **任务前提缺陷**：任务描述称该测试「makes a false pass in clean environments」；
   实测在干净树下产生 **hard FAIL**，不是假通过。真实缺陷是「环境依赖导致该门在 CI
   恒不可用 + reviewer 的 PASS 来自本机树」，而非门状态坍缩。按观察上报。
2. **共享缓存别名**：`scratch_tree()` 是模块级memo。测试按字母序运行时，
   `test_consumer_accepts...` 先构建缓存副本；到本测试时副本早于文件创建时刻建成 ——
   **即使枚举逻辑完全损坏（误纳 ignored 文件）该断言也会通过**。以重新枚举修复，
   并加非空性断言防「空目录平凡排除」。
3. **阴性对照暴露**：在宿主预置真实 profile 后复跑，全部OK 且md5 与内容逐字未变 ——
   证明新逻辑不读、不写、不删真实宿主档案。

## 自述的 missed 项

- 未审计其余约 601 个测试中是否还有同类machine-local false-pass 实例。
- 未在真实 CI runner 下执行（仅本地干净 env，**严格弱于** CI 保证）。
- 未确认一批 skill 测试失败在无限制宿主上是否复现。

[fact-check] 编排者既有环境记录确认该批失败为**沙箱性预存在失败**；本轮复跑中该批
失败**未出现**（沙箱已恢复相关原语），故不再构成当前失败面。

## 自述的 false / redundant 治理动作

- FALSE_GOVERNANCE_ACTIONS = 无（无门报未实跑的 PASS；失败按环境阻塞类上报，未报 PASS
  也未静默省略）
- REDUNDANT_GOVERNANCE_ACTIONS = 跑了两次全量 discover，第二次可避免

## 落盘事实（编排者独立核验，非 worker 自述）

```text
FILES_CHANGED = 1（scripts/tests/test_p1_t16_gate_cli_entrypoint.py）
模块 docstring 新增段落 = "A test never inherits a precondition from the machine
   it happens to run on."，显式指向自建前置条件构造函数
新增符号 = 合成 profile 正文 / 前置构造函数 / fresh_surface_tree / _materialise_surface
fresh_surface_tree 实现 = 重新运行候选面枚举，addCleanup 删除临时根；
   docstring 明确说明「memo 缓存会造成平凡通过」
DIFF_STAT = +117 / -15
```

## 未闭环项（worker 自述）

- **阻断**：执行环境收尾阶段持续 exit 137 / SIGTERM，git status、stash 清理、测试复跑
  均无法执行。三个后果需复核者接手：a) 仓库残留一个 stash需清理；b) 目标文件最终落盘
  状态未复验；c) 建议在干净树重跑目标测试模块。

[fact-check] 编排者已用独立执行路径复核 a) 与 b)：残留 stash 经身份取证后已清理，
两臂工作树 blob 未变；b) 落盘文件确含 `fresh_surface_tree` 与 docstring 新增段。

## 反例 / 阴性对照证据（worker 自述，均在 SIGTERM 之前取得）

- 修复前该测试 FAIL（复现任务所述缺陷）
- 修复后 14/14 OK
- 阴性对照：移除枚举的 `--exclude-standard` → FAIL，证明断言有牙齿且原版会空过
- 宿主预置 profile 场景全OK 且档案 md5 未变

## 编排者独立复验（本轮新增；worker 自述的 GREEN 已获独立证据）

```text
HEAD_SHA_MATCHES_EXPECTED_BASE = YES（c08f6f8b…，detached）
DIFF_CHECK_CLEAN = YES
APPLICABLE_TESTS        = 14 tests / OK
FULL_REGRESSION         = 553 tests / OK
VALIDATE_GOVERNANCE     = 34/34 checks passed
PUBLIC_RELEASE          = VIOLATIONS=0（text_scanned=88, deduped=86）
RESIDUE_IN_DEPLOYMENT   = NONE（fixture 未残留）
WORKER_SELF_REPORT      = NO  → 编排者复跑后 = YES（差异归因见 results.md §D4）
```

## 约束遵守（worker 自述 + 编排者核验）

- 未 commit / 未 push / 未接触 remote ✔
- 未触碰 canonical 治理面 ✔；无新依赖 ✔；CI 语义未改 ✔
- 原有 `exists()` 与 `check-ignore` 断言全部保留，无一条被削弱或删除 ✔
- 自我约束：严格按THE_ROUTING_TABLE 只加载 1 份 WARM；未加载架构/状态/持久化类
  reference；无 ESCALATED_LOAD ✔

[fact-check] 本臂严格遵守渐进披露路由（1 份 WARM），与 `THE_ROUTING_TABLE` 声明一致。
上一轮记录中的载体文件名泄臂缺陷已按 v2 规约归一化。