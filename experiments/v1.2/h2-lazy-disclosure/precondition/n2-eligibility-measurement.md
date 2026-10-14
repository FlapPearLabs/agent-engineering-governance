# [R2-REDACTION] machine paths replaced with the documented placeholder form
# ('/(?:Users|home)/songshiyao' -> /Users/<LOCAL_OS_USERNAME>, which the public-release rule
#  UNIX_USER_HOME deliberately does not match). Original preserved outside the repo.
# origin sha256 (unredacted original) = 7f137516e6d712dee86420007c5007494cde7e8388e5e65f8a0e18b6f5faca45
# source: N2 replay-corpus eligibility feasibility measurement (r01 / r03 / r06)

# N2 — Replay corpus 候选任务 eligibility feasibility measurement

- 测量时间：2026-10-14（GMT+8）
- 范围：`experiments/v1.2/replay/cases.yaml` 的 r01 / r03 / r06（用户指定优先检查项）
- 模式：**measurement only**
- 已遵守的约束：**未修改 freeze**（task-registry / run-plan-r2 / variant-manifest / round-2-freeze 全未触碰）、**未新增任务**、**未执行 H2-R2**、未推送任何提交。
- 隔离方式：从两个父 clone 做**只读 clone**（`git clone --shared`）到 scratch，再在 scratch clone 内建 6 个 detached worktree 测量。父 clone 状态核验：gov `HEAD=6ebde95` clean、zhihu `HEAD=961d771` clean（测量前后均 dirty=0）。六个测量树测量后全部 `dirty=0`。
- 环境：Python 3.13.12（managed；**时代 CI 声明 3.12，此处为 disclosed deviation**）、Node v22.22.2（与时代 CI matrix 一致）、ruff 0.15.18（与 r03 候选 pin 一致）。

---

## 1. 结果表（请求字段）

| 字段 | r01 | r03 | r06 |
|---|---|---|---|
| TASK_ID | r01-zhihu-t14-async-seam-mismatch | r03-governance-static-gate-adoption | r06-governance-zcode-adapter-reference |
| 源仓库 | FlapPearLabs/zhihu-grabber-toolkit | FlapPearLabs/agent-engineering-governance | FlapPearLabs/agent-engineering-governance |
| BASE_SHA | `4b6d182f1388e27ae33820feee1589cb0188d59b` | `015780be7a3f863c05509b437e4e586b4f388794` | `af4df6ae706394db5f9dec313993312392aeb516` |
| CANDIDATE_SHA | `fa997c12e4c35fdb9267882747d2b55d13772ae2` | `65113de69bda6802a476eefa033cf00439d49f04` | `069f8be26cc04bb4f9bf3428c1e23b310debb984` |
| ACCEPTANCE_COMMAND | `cd research-orchestration && node --test test/*.test.mjs`（模块 package.json 声明的 `npm test`；该时代根 CI **不覆盖**此模块） | 时代 CI 声明 4 门（base 侧）＋候选新增 2 门：`python3 scripts/validate_governance.py`；`python3 -m unittest discover -s scripts/tests`；`python3 -m unittest scripts.tests.test_p1_t16_gate_cli_entrypoint`；`python3 -m compileall -q scripts adapters`；`python3 -m ruff check .`（候新增）；`python3 -m unittest scripts.tests.test_p1_t17_static_gate_framework_semantics`（候新增） | `python3 scripts/validate_governance.py`（该时代 CI 声明的**唯一**门；base 无测试面） |
| BASE_RESULT | **FAIL** — 509 tests / pass 508 / fail 1；失败者＝`test/p1-t14-cross-group-synthesis.test.mjs`（`ERR_MODULE_NOT_FOUND: lib/pre-synthesis-guard.mjs`） | base 侧 4 门全 **PASS**（32/32 checks；423 tests OK；12 tests OK；compileall rc=0）／候选新增 2 门 **FAIL**（`ruff check .` 19 errors；t17 文件不存在） | **PASS** — 23/23 checks，rc=0 |
| WORKER_DELTA_RESULT | **PASS** — 539 tests / pass 539 / fail 0（单文件：31/31） | base 侧 4 门仍全 **PASS**（34/34 checks；441 tests OK；12 tests OK；compileall rc=0）／候选新增 2 门 **PASS**（ruff "All checks passed"；t17 18 tests OK） | **PASS** — 23/23 checks，rc=0（与 base **逐项相同**） |
| ORACLE_TYPE | execution-based 仓库测试套件（Node 内置 test runner），模块局部，无外部依赖/网络 | 混合：文档/结构 validator ＋ 仓库测试套件 ＋ linter ＋ 语义测试 | 文档/结构 validator（静态文件检查），**不执行** delta 的任何行为 |
| ELIGIBLE / NON_ELIGIBLE | **NON_ELIGIBLE** | **NON_ELIGIBLE** | **NON_ELIGIBLE** |
| 原因 | 见 §3.1 | 见 §3.2 | 见 §3.3 |

---

## 2. 五准则逐项判定（严格按用户定义）

| 准则 | r01 | r03 | r06 |
|---|---|---|---|
| C1 有明确 acceptance command | PASS | PASS | PASS |
| C2 acceptance 在 frozen base 上 PASS | **FAIL** | **分裂**：base 侧 4 门 PASS；判别性强的 2 门（ruff / t17）base FAIL | PASS |
| C3 修改目标后可区分 PASS/FAIL | PASS（base FAIL → delta PASS，且失败者恰为目标测试） | **FAIL**（base-green 的 4 门在 base 与 delta 上 verdict 完全相同） | **FAIL**（base 与 delta 逐项相同，23/23 → 23/23） |
| C4 oracle 不依赖 worker 可修改字节 | **FAIL（按 replay 原样）**：历史 delta 自己改写了 oracle 文件本身 | **FAIL**：判别门的语义由 worker 交付物 `ruff.toml` 决定（见 §4.2）；测试面亦为 worker 可写 | **FAIL**：validator 是仓内脚本，且根本不评估 delta |
| C5 有 positive + negative control | PASS | PASS（但暴露一处盲区，§4.3） | PASS（但其 negative control 以未捕获异常形态失败，§4.4） |

**结论：三个候选在严格定义下全部 NON_ELIGIBLE。**

---

## 3. 逐候选证据

### 3.1 r01（zhihu-grabber-toolkit，T14 async seam）

- 候选 delta：**新增 3 个 lib 文件**（`cross-group-aggregation.mjs`、`cross-source-synthesis.mjs`、`pre-synthesis-guard.mjs`）**并修改 oracle 文件本身**：`M research-orchestration/test/p1-t14-cross-group-synthesis.test.mjs`。
- base：R1 FAIL（508/509），失败者**唯一且恰是** `test/p1-t14-cross-group-synthesis.test.mjs`；R2（单文件）FAIL，原因 `ERR_MODULE_NOT_FOUND: .../lib/pre-synthesis-guard.mjs`（任务要创建的文件不存在）。
- delta：R1 **PASS**（539/539）；R2 **PASS**（31/31）。
- 冻结交叉：把**候选的**测试文件放进 **base 树**运行 → FAIL（`Cannot find module`）。即：若把候选测试冻结为 spec oracle，base 红 / 候选绿，判别成立。
- 独立 negative control（注入式，非 base 对照）：从候选树**删掉一个 lib 文件** → R2 FAIL。证明该门在 base 对照之外仍有牙齿。
- **NON_ELIGIBLE 原因**：C2 失败（base 非 PASS）。且 C4 需额外设计：replay 的 delta 自己触碰 oracle 文件，必须把 spec 测试冻结到 worker scope 之外才成立。

### 3.2 r03（governance static gate adoption）

- 候选 delta：新增 `ruff.toml` / `requirements-dev.txt` / `references/static-tooling-profiles.md` / **`scripts/tests/test_p1_t17_static_gate_framework_semantics.py`**；**修改 3 个测试文件**（`adapters/zcode/tests/test_project_continuity.py`、`scripts/tests/test_p1_t12_shared_file_single_writer.py`、`scripts/tests/test_review_evidence_contract.py`）**并修改 `scripts/validate_governance.py`**。
- base：4 门 PASS（32/32；423 OK；12 OK；rc=0），`ruff check .` FAIL（19 errors），t17 不存在。
- delta：4 门仍 PASS（34/34；441 OK；12 OK；rc=0），ruff **PASS**，t17 **PASS**（18 tests）。
- **C2/C3 的"毒配对"**：base-green 的 4 门对 delta **零判别**（verdict 完全相同，只是数量 423→441、32→34）；唯一能判别 delta 的门（ruff / t17）**在 base 上不是绿**。
- 另注：`scripts/validate_governance.py` **本身属于 delta**（check 数 32→34），把 validator 当 oracle 等于 worker 自己写一部分 oracle。
- **NON_ELIGIBLE 原因**：C3 失败（base-green 门无判别力）；能判别的门同时使 C2 失败；C4 失败（见 §4.2）。

### 3.3 r06（governance zcode adapter reference）

- base：**只有 39 个文件、无 `scripts/tests/`**；唯一的 CI 门是 `validate_governance.py`。`unittest discover -s scripts/tests` 直接 `ImportError: Start directory is not importable`。
- 候选 delta：**纯新增 8 个文件**（`adapters/**`，含一个被一并提交的 `__pycache__/*.pyc`），**不含任何测试**。
- base 23/23 PASS → delta **23/23 PASS，逐项相同**：validator 对新增的 8 个文件**完全不可见**。
- **NON_ELIGIBLE 原因**：C3 失败——该时代不存在任何能观察任务交付物的门；任务无 verifiable correctness oracle（与 registry 里 t04/n01/n02 的 `NO_MECHANICAL_ACCEPTANCE_TARGET` 同型）。

---

## 4. 控制实验与三个非平凡发现

### 4.1 positive controls（均应 PASS，全部实测通过）

| 候选 | 控制 | 结果 |
|---|---|---|
| r01 | 候选树 R1 | PASS 539/539；R2 31/31 |
| r03 | 候选树 4 门 | 全 PASS（34/34；441 OK；12 OK；rc=0） |
| r03 | 候选自带语义测试 t17 @ 候选树 | **PASS** 18 tests |
| r06 | 候选树 validate_governance | PASS 23/23 |

### 4.2 negative control N2 —— **空洞配置攻击：linter 门可被 worker 自证绿**

r03 候选树上把 `ruff.toml` 改成 `[lint] select = []`：

- `python3 -m ruff check .` → **rc=0 "All checks passed!"** —— **判别门被伪造为绿**，而该文件的作者正是 worker 自己。
- 同状态下候选自带的语义测试 t17 → **FAIL**（抓住）。即：**唯一能识别"空洞配置"的是候选自带的测试，而该测试本身也是 worker 的交付物**。

这是 C4 的直接反例，也复现了 round-13 P0-1 的同一形状（门禁信任 worker 可写字节）。

### 4.3 negative control N3 —— **base-green 验收门存在实测盲区**

在 r03 候选树上把 `validate_project_state.py` 的 `check()` 改写为**任何检查都汇报成功**（一个"永不报错"的验证器——真实的语义缺陷）：

- `python3 -m unittest discover -s scripts/tests` → **rc=0（441 OK）**
- `python3 scripts/validate_governance.py` → **rc=0（34/34 passed）**

**两道 base-green 门都未察觉。** 即：即便把 C2 放宽，这两道门对一类真实缺陷仍无判别力。

### 4.4 r06 negative control —— 门能失败，但以未捕获异常形态

删除 `mcp/README.md`（REQUIRED_FILES 之一）→ rc=1，但形态是 `Traceback ... validate_governance.py:210` 的未捕获异常（0 条 `FAIL` 行）。门"能失败"，失败模式是崩溃而非结构化报告。

### 4.5 附加：冻结 oracle 兼容性交叉（针对 C4 的可行替代设计）

若把 oracle 冻结到 worker scope 之外，用**base 版**测试文件跑**候选树**：

| r03 被改测试文件 | base 版 @ 候选树 |
|---|---|
| `adapters/zcode/tests/test_project_continuity.py` | **FAIL — 69 tests, 23 errors**（`test_document_pointer_contract`） |
| `scripts/tests/test_p1_t12_shared_file_single_writer.py` | PASS（30 OK） |
| `scripts/tests/test_review_evidence_contract.py` | PASS（53 OK） |

即：**其中一份被改测试的 base 版与候选树不兼容**——冻结 oracle 方案在该文件上不会认可历史候选本身。

---

## 5. 横向结论（对 N2 决策最重要的一条）

**C2 与 C3 对"新增/修复型" delta 构成互斥约束。**

本次三个候选**全部**是新增/修复型 delta（base 缺东西 → 候选补上）。对这类 delta：

- 在 base 上为绿的门（不变量类）→ 对 delta 无判别力（r03 的 4 门、r06 的 validator 实测零判别）；
- 能判别 delta 的门（spec 类）→ 在 base 上必为红。

因此 **C2 ∧ C3 只能在"keep-green"型任务上同时成立**（base 绿的不变量，worker 的改动须不破坏它，其判别力由 negative control 证明）。replay corpus 里没有任何一个 keep-green 型 case。

**对现有 registry 的影响（须注意）**：同样的严格 C2 判定也会把 registry 目前仅有的两个 `ELIGIBLE` 任务标为 NON_ELIGIBLE —— t01（base `c08f6f8b`，t16 门 base RED＝1 failure，那正是它的任务目标）与 t02（base `015780be`，`ruff check .` base RED＝19 errors，本次已实测复现）。也就是说：**按字面执行这五条准则，Round-2 的聚合集会被清空**。

两个可能的口径，需要在下一步前定：

- **(a) 字面口径**：C2 = acceptance 必须在 frozen base 上 PASS。⇒ 只能收 keep-green 型任务；r01/r03/r06 及 t01/t02 全部出局；任务必须**换来源**（corpus 无法提供）。
- **(b) 复合口径**：acceptance 拆为「base-green 不变量门」∧「base-red spec 门（冻结、worker 不可写）」，C2 只对不变量门要求 PASS，C3 由 spec 门承担。⇒ r01 最接近成立（冻结候选测试 @ base FAIL、@ 候选 PASS，实测），但仍需解决 §4.5 的 oracle 兼容问题与 §4.2 的可伪造问题。

本报告不对此做单方面裁定，等待指令。

---

## 6. 方法与可复现

- 六个测量树：`/Users/<LOCAL_OS_USERNAME>/WorkBuddy/agentengineering/h2-n2-feasibility/{r03-base,r03-cand,r06-base,r06-cand,r01-base,r01-cand}`（scratch clone 内 detached worktree；测量后全部 `dirty=0`，HEAD 逐一核验）。
- 原始日志：同目录 `logs/*.log`（`r03-base.log`、`r03-cand.log`、`r06-base.log`、`r06-cand.log`、`r01-base.log`、`r01-cand.log`、`controls-r03.log`、`controls-rest.log`、`controls-final.log`）。
- 命令与 rc 均逐条记录在日志内；所有注入式控制均在 `finally`/恢复步骤后核验 `dirty=0`。
- 测量自身的副作用：`compileall`（探测步骤 D）与运行脚本会产生 `__pycache__`；已在每棵树恢复并核验（r06 候选树自带的已提交 `.pyc` 属候选内容，非本次副作用）。
- 未提交任何内容到任何仓库；两个父 clone 未被写入。
