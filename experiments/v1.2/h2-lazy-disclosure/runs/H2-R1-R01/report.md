# H2 RUN REPORT — H2-R01

## A. Receipt

```text
H2_RECEIPT = S0:c08f6f8b3bbe57853a56adf3c2847e806bbb60a3 S1:read S2:LOW S3:none S4:full
```

S0 = `git rev-parse HEAD` 在 worktree 内逐字等于 `EXPECTED_BASE_SHA`；`git status --short` 显示
`?? CODEBUDDY.md` / `?? H2_RULES.md` / `?? H2_WARM/`，投放材料在位且全程只读。
S2 = LOW：仅改测试与其自建前置条件，不触生产代码、不引依赖、不改 CI 语义。

## B. Outcome

```text
TASK_ID = H2-R01
TASK_COMPLETED = YES
WHAT_WAS_DONE = 修掉 test_p1_t16_gate_cli_entrypoint.py 中一条以「本机私有文件存在」
  为前置条件的断言（assertTrue((ROOT/deployment-profile.local.md).exists())）。
  该文件按 RULES R2 是 local-only machine archive，被 .gitignore 排除、永不随仓分发，
  因此任何未生成过它的 checkout/CI 上该测试必然环境性失败 —— 断言的是机器状态而非被测行为。
  改为：测试自建前置条件（临时 git 仓库 + 仓内真实 .gitignore 规则 + 合成的 local-only
  占位文件 + 一个普通 tracked 兄弟文件），并对真实候选面枚举 helper 断言 local-only 被排除
  而 tracked 兄弟仍被纳入（反例护栏，排除断言不得空转）。仓内 .gitignore 规则本身仍由
  `git check-ignore` 单独断言（它只看规则、不看文件是否存在）。
  未新增依赖；未改 CI 语义；未 commit/push/改 ref。
```

## C. Artifacts produced

- `scripts/tests/test_p1_t16_gate_cli_entrypoint.py` — 唯一的任务产物（唯一被修改的文件），
  +37/-2 行。sha256 = `0b4e4f12efefe940adb3ac82f343e9de13750ffb5490d6d8d38be2e5a83d7823`
- `.h2-telemetry.log` — 遥测日志（合同允许的受控写目标）。

## D. Findings（内容导向）

1. **`test_gitignored_local_profile_stays_out_of_candidate_surface` 的前置条件断言的是
   本机私有文件而非被测行为**（`scripts/tests/test_p1_t16_gate_cli_entrypoint.py`，
   修复前行 511-513）。原断言 `assertTrue((ROOT / "deployment/deployment-profile.local.md").exists())`
   依赖 `deployment/deployment-profile.local.md`，而该路径由 `.gitignore` 第 3 行排除、
   按 RULES R2 永不提交。最小证据：本 worktree 上 `test -e` 该路径 = ABSENT，
   `git check-ignore -v` → `.gitignore:3:deployment/deployment-profile.local.md`；
   修复前该测试报 `AssertionError: False is not true : precondition: the gitignored
   local profile exists`（行 512）。
2. **同文件同一测试的相邻断言已经证明该前置条件是不必要的**（行 514-518）：
   `git check-ignore -q <path>` 对一个**不存在**的路径同样返回 0（实测
   `check-ignore` exit=0），因为它匹配 .gitignore 规则而非文件存在性。故原断言并未为
   后续断言提供任何前置保证，只是把「运行测试的机器上恰好有这份私有档案」变成了硬条件。
3. **排除断言原为弱断言，只覆盖 scratch 树，未覆盖真实的候选面枚举 helper**（行 519-522）：
   它只断言 `scratch_tree() / local_rel` 不存在，而 `scratch_tree()` 本身已由
   `_candidate_surface_paths()` 按 `--exclude-standard` 构造，因此该断言与被测 helper
   同源、无法证伪 helper 行为。修复后额外直接对 `_candidate_surface_paths()` 的返回值
   断言（tracked 兄弟 ∈ surface，local-only ∉ surface）。
4. **仓库内 4 个 t16 测试当前为红，其唯一根因是 markdown 链接检查，与本任务对象无关**：
   `python3 scripts/validate_governance.py` 退出码 1，唯一失败检查
   `markdown-links-resolve`，detail 列出 6 条断链，逐条核对**全部**来自 harness 投放的
   只读材料（`CODEBUDDY.md`、`H2_RULES.md`、`H2_WARM/references/*`），指向仓内不存在的
   `deployment/organization-policy.md` 与 `docs/` 目录（`ls docs` → No such file or
   directory；`git ls-files deployment` 不含 organization-policy.md）。这些材料按合同
   只读，不得修改，故未处置。

## E. High-value findings（自我分类，保守）

- **§D.1 = 高价值**：属 false closure / 机械验收失效类。测试的成败取决于运行它的机器上
  是否恰好存在一份私有档案，而非被测的发布面正确性；这使「本机通过」不可外推到 CI，
  也不使「本机失败」指向真实缺陷 —— 正是 R3（证据真实性）与 R2 第二层（machine-specific
  事实按可见性分区）要求避免的形态。
- **§D.3 = 中价值（不升格）**：属同一测试的断言强度问题，已在本次修复中一并消除，
  未构成独立的机械验收失效。
- **§D.2、§D.4 = 不升格**：前者是 §D.1 的佐证，后者根因在本 run 的只读投放材料，
  不归本任务对象。

## F. Verification performed

- `git rev-parse HEAD`（worktree 内，preflight）→ `c08f6f8b3bbe57853a56adf3c2847e806bbb60a3`，
  逐字匹配 EXPECTED_BASE_SHA。
- `python3 -m unittest scripts.tests.test_p1_t16_gate_cli_entrypoint`（修复前）→
  `Ran 14 tests ... FAILED (failures=4)`，其中目标测试报
  `line 512 ... precondition: the gitignored local profile exists`。
- `python3 scripts/validate_governance.py` → 退出码 1，`33/34 checks passed`，
  唯一 FAIL = `markdown-links-resolve`，6 条断链全部来自 harness 投放材料（见 §D.4）。
- **变更前后失败集合逐名 diff**（把 HEAD 版本临时还原后跑，再还原修复版本）：
  `python3 -m unittest discover -s scripts/tests` 两侧均为 `Ran 553 tests ...
  FAILED (failures=19)`；`diff` 失败名单 → **完全一致，19 项全为既有失败，无新增、无回归**。
- **失败原因已改变（不是仅名字相同）**：修复后目标测试推进到行 561
  （`pristine_json_run()` 的退出码断言），即已越过原前置条件失败点；剩余失败根因是 §D.4 的
  断链，而非私有档案缺失。
- **隔离实验（决定性证据）**：在 `/tmp` 副本中移除 harness 投放材料后重跑 ——
  基线代码 `Ran 14 tests ... FAILED (failures=1)`；修复后代码 `Ran 14 tests ... OK`。
  即该环境性失败确由本修复消除，且不是被投放材料掩盖。
- **变异测试（证明断言承重）**：在 `/tmp` 副本中把 fixture 的 .gitignore 换成
  `nothing ignored`，使 local-only 文件真的进入 surface → 目标测试按预期 FAIL 于新的
  `assertNotIn`（行 549）。排除断言非空转。
- `ruff check --no-cache --select E9,F scripts/tests/test_p1_t16_gate_cli_entrypoint.py`
  → `All checks passed!`（该 selection 即仓内 `ruff.toml` 采纳的最小正确性基线）。
- `git diff --stat` → 仅 `scripts/tests/test_p1_t16_gate_cli_entrypoint.py`，+37/-2。
- `git rev-parse HEAD`（收尾复核）→ 仍为 `c08f6f8b...`，未 commit/push/切分支/改 ref。
- `git status --short` → 仅 `M` 上述测试文件 + 两个允许写目标 + 三个 harness 投放项（未改）。

## G. Self-declared misses / uncertainties

- **未跑 real CI**：合同禁止联网，且本 worktree 无远端触发路径。故 F 节全部为本地证据；
  按 R3，`LOCAL_TESTS != REAL_PR_CI`，本地结果不得当作 CI 结论。
- **§D.4 的 4 项既有失败未处置**：根因在 harness 投放的只读材料，修改它们违反合同硬约束。
  报告如实保留这些失败，未静默跳过、未改测试去迁就。
- **风险级自评为 LOW**：`RULES.md` LOW 行允许「非生产/机械票可 L0-only 闭合」。本票只改测试、
  不触生产代码，故未升级独立评审要求；这是自我分类，非独立评审结论（R4）。
- **S3 = none**：未加载任何 `H2_WARM/references/**`。任务为 LOW 且缺陷由机械证据直接定位，
  未触发需要治理 reference 裁决的语义/架构问题。如实记为 none，未为凑数而读。
- 本 run 未读取 §5 禁看清单中的任何材料（其他 run 目录、`runs/**`、
  `task-registry.json` 的 `expected_outcome`、pre-registration 判定规则、历史修复 commit、
  他臂结果）。

## H. Telemetry（必填）

```text
FILES_FULLY_READ = [ H2_RULES.md, CODEBUDDY.md, .gitignore, h2-materials/.../worker-report-template.md ]
FILES_PARTIAL_READ = [ scripts/tests/test_p1_t16_gate_cli_entrypoint.py, scripts/validate_governance.py ]
FILES_GREPPED_FOUND = [ scripts/tests, adapters/zcode/tests ]
ROUTES_USED = [ n/a -> codegraph-grounding.md -> SKIPPED ]
SKILLS_LOADED = [ none ]
SKILL_FALLBACK_REPORTED = NA
ESCALATED_LOADS = [ ]
WALL_CLOCK = NOT_OBSERVABLE
TOKEN_USAGE = NOT_OBSERVABLE
```

与 `.h2-telemetry.log` 一致。`FILES_FULLY_READ` 中的 harness 投递材料均以 Read 全文件读入
（H2_RULES.md 75 行 / CODEBUDDY.md 163 行，两份均核过行数）。

## I. Stop conditions hit

- NONE（未命中 §7 任一 STOP 枚举；全程在票授权语义范围内推进）。