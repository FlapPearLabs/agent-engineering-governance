# Freeze v2 — Codex implementation hand-off

本报告覆写首轮因 sandbox 限制留下的未跟踪报告。分支始终为 `experiment/v1.2-h2-freeze-v2`，起始 HEAD 为 `0edbbaba82de777402addcf9026a3f5dabdd5f02`。
实现按 T1–T9 顺序，每任务一个本地提交；T9 的提交身份由 git 历史记录，不在本文件自引用自己的 SHA。最终接受由 Claude 决定，执行者未自批。

## 新事实与边界

- 新结构发现：无。CodeGraph CLI 1.0.1 可用，但该 worktree 无索引；status/explore 实测确认不可用。计划写范围不允许建立 .codegraph，因此使用 MODE C 手工源码/调用面接地，没有声称图覆盖。
- 新反例：仓内预植交付文件、ignored stray、状态分类、canary 污染/顺序、答案泄漏、aggregate 身份与逐文件 byte mutation，均由指定测试文件承载。
- T2 全量结果：WRAPPER 两臂全部中性；旧仓内交付污染仍保留。没有把执行通过当作披露安全结论。
- canonical、旧 round-2 冻结面、admission 测量和 H3 corpus 没有修改；所有仓库变更仅在计划允许的两个位置。

## 已采用的计划解释

1. T4 的旧 round-2 没有统一 deny_prefixes。旧 t01–t04 前缀会阻断 shortlist r24 所需的 deployment/BOOTSTRAP_CONTRACT.md 修复。依计划“allow everything else in repo/”，本实现采用旧 n01/n02 已有的空前缀列表，同时 deny 每个 base 的全部 scripts/tests 文件与 oracle，brief 禁止改变任何测试。生成器、registry 和协议都公开记录此选择。
2. freeze commit 指 T8 首次加入 manifest 的内容冻结提交 `526aa38`，父提交与全部 run materials 为 `042f2244e453c79daa0ed50d72759a4583bcc43d`。T9 仅更新 README/本报告，最终独立 review 必须绑定 T9 的最终候选 SHA。
两项均已发出异步澄清但未收到答复；以上是根据现有合同采用并公开的解释，不把未回复说成批准，独立验收应特别核对。

## 命令与共同提交门禁

所有命令从仓库根执行。`H=experiments/v1.2/h2-lazy-disclosure`；`PY` 为交接指定的工具链解释器，实测 Ruff 为 0.15.18。未在公开文件写入真实宿主路径。
完整读取了 CODEX_PLAN 及全部 Context to read first 文件后才写代码。只读读取 isolated profile 的 env.sh，未 source 或改写它。

每个 T1–T8 提交前都按以下顺序以 `&&` 串联执行，失败会阻止提交；T9 提交前也执行同一完整命令链。以下是实际命令的可重现写法，省略 local-only 输出重定向：

```bash
$PY -m ruff check .
$PY scripts/validate_governance.py
$PY scripts/validate_public_release.py
TMPDIR=$(cd "$TMPDIR" && pwd -P) $PY -m unittest discover -s scripts/tests
$PY -m unittest discover -s experiments/v1.2/tests
git diff --stat c40266f -- . ':!experiments/v1.2/h2-lazy-disclosure/freeze-v2' ':!experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py'
git diff --check
```

scope 输出额外以非空即失败的断言检查。这个检查覆盖全部允许目录之外的路径，因此也覆盖计划中每条 NEVER TOUCH 路径。每次 scope 与 diff-check 均为空输出、exit 0。
基线实际执行完毕：35/35、VIOLATIONS=0、602 项 scripts 测试 OK、309 项实验测试 OK。

各任务均运行过同一个聚焦命令（初次 RED 与已保存 GREEN 的原样摘要如下），再运行完整门禁：

```bash
$PY -m unittest discover -s experiments/v1.2/tests -p test_v1_2_h2_freeze_v2.py
```

开发中的接口/产物不存在会导致初次 RED；T2 的 RED 来自状态分类缺失。新增用例使部分计数递增，不声称这些记录是一套固定测试对历史缺陷的一对一复现。全量提交门禁是对应候选的最终机械证据。

## T1 — `1dbcf3f`

wrapper_delivery.py 提供 prepare / cleanup。所有 carrier、RULES 与 S3 WARM 字节取自材料 git objects，repo/ 为 detached base worktree。真实 f01 双臂哈希、HEAD、含 ignored 状态、仓外位置和回滚均有测试；预植材料和 ignored 文件都会拒绝并清除分配。

开发聚焦 RED 摘要：

```text
Ran 3 tests in 0.001s
FAILED (errors=3)
```

开发聚焦 GREEN 摘要：

```text
Ran 4 tests in 0.763s
OK
```

提交前全门禁原样尾行（依次为 Ruff、governance、public scan、scripts tests、experiment tests）：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
----------------------------------------------------------------------
Ran 602 tests in 16.197s

OK
----------------------------------------------------------------------
Ran 313 tests in 482.187s

OK
```

scope / diff-check：空输出，exit 0。

## T2 — `1804055`

delivery_anchors.py 加入 WRAPPER，保留旧布局语义，并处理 expected failure / unexpected success。全部十任务测量完成，未抽样。WRAPPER 10/10 中性，两个臂的 oracle/full-suite 非通过集合相同且 ran_delta=0；旧两布局各 0/10。README §2 数字仅来自新 JSON。

实际执行的任务命令 / 上下文：

```bash
$PY $H/freeze-v2/delivery_anchors.py . $H/admission/freeze-v2-input/shortlist.json --materials HEAD --out $H/freeze-v2/delivery-anchors.json
# 执行时 HEAD = 1dbcf3f2d3bc9ec0c230c36784db6adcc2a8713a
```

开发聚焦 RED 摘要：

```text
Ran 5 tests in 0.817s
FAILED (errors=1)
```

开发聚焦 GREEN 摘要：

```text
Ran 5 tests in 0.900s
OK
```

提交前全门禁原样尾行（依次为 Ruff、governance、public scan、scripts tests、experiment tests）：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
----------------------------------------------------------------------
Ran 602 tests in 16.282s

OK
----------------------------------------------------------------------
Ran 315 tests in 482.515s

OK
```

scope / diff-check：空输出，exit 0。

长测量最终原样输出：

```text
DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0, "WRAPPER": 10}
```

## T3 — `048db45`

isolation_canary.py 构造 synthetic repo 和三层 canary，只返回供操作员执行的命令。解析器覆盖正常顺序、提前披露、MCP、plugin agent、global/user 指令、Skill、错误/畸形/不完整流。实际 profile canary 未执行，解析器仅能裁定可见事件。

开发聚焦 RED 摘要：

```text
Ran 9 tests in 0.808s
FAILED (errors=3)
```

开发聚焦 GREEN 摘要：

```text
Ran 9 tests in 0.850s
OK
```

提交前全门禁原样尾行（依次为 Ruff、governance、public scan、scripts tests、experiment tests）：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
----------------------------------------------------------------------
Ran 602 tests in 16.225s

OK
----------------------------------------------------------------------
Ran 318 tests in 480.836s

OK
```

scope / diff-check：空输出，exit 0。

## T4 — `b5d7b63`

build_registry.py 从 shortlist 和四批 ledgers 生成 f01..f10。oracle 在 base/candidate 的对象哈希逐一核对且相等；candidate SHA 仅在顶层 expected。两次 CLI 生成字节一致，原始 worker-visible 字符串不含候选 SHA 的七位前缀，也不含非测试 delta 中长度至少 20 的新增行。

实际执行的任务命令 / 上下文：

```bash
$PY $H/freeze-v2/build_registry.py --out $H/freeze-v2/task-registry-v2.json
```

开发聚焦 RED 摘要：

```text
Ran 11 tests in 0.859s
FAILED (errors=2)
```

开发聚焦 GREEN 摘要：

```text
Ran 11 tests in 1.384s
OK
```

提交前全门禁原样尾行（依次为 Ruff、governance、public scan、scripts tests、experiment tests）：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
----------------------------------------------------------------------
Ran 602 tests in 16.428s

OK
----------------------------------------------------------------------
Ran 320 tests in 482.460s

OK
```

scope / diff-check：空输出，exit 0。

## T5 — `d8c5e9a`

build_run_plan.py 生成 20 个唯一 run。每任务每臂一条，C-first/V-first 各五，固定 model/runtime/profile，fresh episode，无 session 复用。此任务先以当时 HEAD 生成，T8 再统一绑定最终冻结父提交。

实际执行的任务命令 / 上下文：

```bash
$PY $H/freeze-v2/build_run_plan.py --materials HEAD --out $H/freeze-v2/run-plan-v2.json
# T5 执行时 HEAD = b5d7b63；T8 以 042f224 再生成
```

开发聚焦 RED 摘要：

```text
Ran 12 tests in 1.396s
FAILED (errors=1)
```

开发聚焦 GREEN 摘要：

```text
Ran 12 tests in 1.359s
OK
```

提交前全门禁原样尾行（依次为 Ruff、governance、public scan、scripts tests、experiment tests）：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
----------------------------------------------------------------------
Ran 602 tests in 16.489s

OK
----------------------------------------------------------------------
Ran 321 tests in 493.333s

OK
```

scope / diff-check：空输出，exit 0。

## T6 — `6a31c05`

worker-brief-v2.md 与 render_brief.py 使用 wrapper cwd、repo/ 任务目录、仓外 report/telemetry、明确读写边界和禁看清单。十任务双臂正文仅 delivery block 不同；CLI 实际复制材料对象中的同构报告模板到临时仓外目录。

实际执行的任务命令 / 上下文：

```bash
# 聚焦测试内部调用了 render_brief.py --run-id <首条run> --python <TOOLCHAIN_PYTHON> --out <临时仓外contract>
```

开发聚焦 RED 摘要：

```text
Ran 14 tests in 1.524s
FAILED (errors=2)
```

开发聚焦 GREEN 摘要：

```text
Ran 14 tests in 2.895s
OK
```

提交前全门禁原样尾行（依次为 Ruff、governance、public scan、scripts tests、experiment tests）：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
----------------------------------------------------------------------
Ran 602 tests in 16.875s

OK
----------------------------------------------------------------------
Ran 323 tests in 491.674s

OK
```

scope / diff-check：空输出，exit 0。

## T7 — `042f224`

protocol-v2.md 承接 FZ2_1..FZ2_4、双 temp-root oracle 转移、无新增非通过 ID、scope、invalid 注册与不静默重跑。confound 与 README 字节相等。aggregate_set.py 从 REQUEST_VALID 与 frozen membership 相交派生唯一集合；真实记录为十任务、每臂十条、共二十条计划 run。null/覆盖规则的偏离已预注册，未计算实际实验结论。

实际执行的任务命令 / 上下文：

```bash
$PY $H/freeze-v2/aggregate_set.py
```

开发聚焦 RED 摘要：

```text
Ran 16 tests in 2.780s
FAILED (errors=2)
```

开发聚焦 GREEN 摘要：

```text
Ran 16 tests in 2.881s
OK
```

提交前全门禁原样尾行（依次为 Ruff、governance、public scan、scripts tests、experiment tests）：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
----------------------------------------------------------------------
Ran 602 tests in 18.105s

OK
----------------------------------------------------------------------
Ran 325 tests in 490.161s

OK
```

scope / diff-check：空输出，exit 0。

## T8 — `526aa38`

build_manifest.py 与 freeze-manifest.json 钉住 32 个文件，测试内保存同值独立字面量，并另钉 manifest 自身哈希。临时副本的 33 个逐文件单字节变异均被完整性谓词拒绝。最终 materials 为 042f224；与 T2 的载荷、shortlist 和 wrapper 程序等价性由生成器和测试实际核对。

实际执行的任务命令 / 上下文：

```bash
$PY $H/freeze-v2/build_run_plan.py --materials HEAD --out $H/freeze-v2/run-plan-v2.json
$PY $H/freeze-v2/build_manifest.py build --freeze-parent HEAD --out $H/freeze-v2/freeze-manifest.json
$PY $H/freeze-v2/build_manifest.py check
# T8 执行时 HEAD = 042f2244e453c79daa0ed50d72759a4583bcc43d
```

开发聚焦 RED 摘要：

```text
Ran 18 tests in 2.790s
FAILED (failures=1, errors=1)
```

开发聚焦 GREEN 摘要：

```text
Ran 18 tests in 3.141s
OK
```

提交前全门禁原样尾行（依次为 Ruff、governance、public scan、scripts tests、experiment tests）：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
----------------------------------------------------------------------
Ran 602 tests in 16.520s

OK
----------------------------------------------------------------------
Ran 327 tests in 486.776s

OK
```

scope / diff-check：空输出，exit 0。

生成与 check 的原样输出：

```text
FREEZE_MANIFEST files=32 delivery_payload_equivalent_to_T2=YES
{"verdict": "PASS", "mismatches": []}
```

## T9 与外部交接

README §4 指向 manifest 与独立锚，§5 明确 Claude 先执行 logged-in isolated canary 并保存 verdict，再作 fresh DeepSeek exact-SHA review，最后按旧 protocol §12 进入合法合并路径。本次到 T9 停止，不进入实际实验。

未做及原因：实际 opencode/model canary 与独立 DeepSeek review 均未运行（用户禁止模型调用，计划明确交给 Claude）；未 push、未开 PR、未 merge、未进行 remote verification，真实 PR CI 状态为 NOT_TRIGGERED；未运行 H2-R2。parser fixture PASS 不表示 live profile 已验证。
旧 shell prepare/collect/acceptance harness 未改写为 wrapper 版本；本次交付是计划要求的材料、准备/渲染模块、测量和协议，并未声称已经完成实际二十条 run 的执行/收集。

## Agent / Skill、自校验与最终责任

- 实际执行 agent：Codex 主执行者。没有调用子代理、workbuddy、opencode、外部模型或联网服务。
- 已读取并应用：implement（按既有计划实现及逐任务提交）、tdd（预先设计合同/反例，聚焦 RED/GREEN）、software-development（scope、证据、机械验证）、codegraph-integration（能力探测后手工接地 fallback）。
- code-review 原文已读取，因当前任务禁止模型调用，没有执行其并行模型评审；自检采用 standards / plan 两轴，不冒充独立评审。未安装插件或新增工具。
- 修复/自校验结果：T2 修正已记录的 P3 状态遗漏；其余按计划构建并补充针对性的负例。T1–T8 全部指定门禁在各自提交前通过，未出现需要越写范围修复的门禁失败。
- Codex 机械交付结论：T1–T8 已实现且逐票门禁通过；T9 提交前执行同一全门禁。最终接受仍为 Claude 的独立职责，未自批。
- 规则/门禁/文档：只新增实验测试和 v2 实验协议/材料/README/报告，没有修改 canonical 规则、脚本门禁或旧冻结面。
- 状态交接已持久化到本报告与 README。重要上下文未持久化项：无。原始开发/门禁终端日志 local-only，公开报告保存可重跑命令和原样尾行，T2 完整测量 JSON 已入仓并钉 hash。

## T10–T14（implementer: opencode deepseek-v4.1-flash）

本节由第二轮实现者追加。上一轮以 Codex 身份完成的 T1–T9 记录原样保留。本轮分支仍为
`experiment/v1.2-h2-freeze-v2`，起点 HEAD `7e9c516`（acceptance round 1 的提交），按
T10→T14 顺序实现，每任务一个本地提交，提交身份 `FlapPearLabs`，message 结尾带
opencode 的 Co-Authored-By。最终接受仍是 Claude 的独立职责，本轮没有自批、没有 push/PR。

写范围与上一轮相同：`experiments/v1.2/h2-lazy-disclosure/freeze-v2/**` 与
`experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py`。每个提交前都跑同一完整门禁链（Ruff、
governance、public release、scripts tests、experiments tests、越界 diff、`git diff --check`）。
长测量（delivery anchors、experiments 全量套件）都跑到底，没有抽样。

### T10 — `1574054`

registries 的 `deny_prefixes` 从 round-2 n01/n02 的空列表改为每任务 `scripts/tests/`，
per-file deny 保留；新增 `scope_v2.py` 实现 `check_scope`：路径逃逸、deny 文件/前缀、
新增或重命名目标的 startup hook（`sitecustomize.py`、`usercustomize.py`、`*.pth`），以及
导入 validator 2.8.12 的 `check_task_class.shadow_paths`（import，不复制）后对
BYTECODE / PACKAGE_IMPORTED_BY_DISCOVERY / PACKAGE_MARKER / SHADOWS 的拒绝。registry 的
`scope_prefix_source`、protocol-v2 §7 与 README §4 记录这次废止与原因。

F1 复现不是空断言：测试在临时目录里放 `scripts/tests/json.py` 并证明它确实遮蔽 stdlib
（子进程输出 `shadowed`），再把同一路径交给 `check_scope` 断言被拒；另测 `scripts/json.py`、
`json.py`、`scripts/shadow.pyc`、`scripts/__init__.py`、rename 两侧、startup hook 与路径逃逸。

开发聚焦运行（改动 registry/protocol 后、未重钉 manifest 时，两个冻结测试为 RED）：

```text
Ran 23 tests in 4.518s
FAILED (failures=2)
```

重钉后：

```text
Ran 23 tests in 5.027s
OK
```

提交前全门禁原样尾行：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
Ran 602 tests in 21.445s
OK
Ran 332 tests in 561.030s
OK
```

### T11 — `76be472`

新增 `collect_v2.py` 与 `run_acceptance_v2.py`（F2 的可执行实现），并把
`delivery_anchors.run_gate` 扩出 `style` 参数（默认 RESOLVED，T2 语义不变），让"什么算非通过"
只有一个 owner。

- collect：`git diff <registry base>`（含已提交、删除、重命名）+ untracked + ignored 的完整
  base→worker 差异，**永远对 registry base，不对 HEAD**；报告与遥测必须存在且非空；每个投放
  文件同时按 receipt 哈希与"从 materials commit 重新组合出的字节"两次核对，注入的额外文件也拒。
- acceptance：一份 verdict JSON，退出码只对 ACCEPT 为 0。顺序为 collection 有效性 →
  T10 scope + repo/ 内的投放/报告/遥测副本 + 路径逃逸 → oracle 字节等于 registry base hash →
  两种 temp-root spelling 的 base 不通过 / worker 通过（执行数 > 0，skip / expected failure /
  unexpected success 不算通过）→ 两种 spelling 的完整 scripts/tests 对 T2 PRE 集合比较。
  INVALID、scope 违规、oracle 字节变动均为终局，不再绕过测量。

投放副本的判据写进了 protocol-v2 §5.3：arm carrier 没有仓内 owner，出现即拒；
`H2_WARM/<dest>` 与 `<dest>`、`H2_RULES.md` 与 `RULES.md` 是同一 owner，同一字节出现在 owner
路径上是修复而不是副本——这是 f02 第一次跑正向控制时暴露出来的假阳性（candidate 对
`references/execution-stage.md` 的修复恰好等于当代 WARM 副本），已按 owner 规则修正，原始失败
如下：

```text
FAIL: test_positive_control_accepts_the_candidate_delta_for_all_ten_tasks ... (task='f02')
AssertionError: 'ACCEPT' != 'REJECT' : f02: ['WORKER_DELIVERY_IN_REPO:references/execution-stage.md']
ERROR: test_added_discovery_shadow_is_rejected_and_would_have_fooled_the_oracle ... KeyError: 'oracle'
Ran 7 tests in 178.535s
FAILED (failures=1, errors=1)
```

修正后（含十任务正向控制与十任务 unchanged-base 负向控制，均为完整双 spelling 测量）：

```text
Ran 7 tests in 191.786s
OK
```

F1 端到端负例同时证明复现仍然有效：加了 `scripts/tests/json.py` 后 oracle gate 返回
`{'rc': 0, 'ran': 46, 'not_passing': []}`（假绿），acceptance 仍以
`WORKER_SCOPE_DENIED:scripts/tests/json.py` 与
`WORKER_SHADOWS_IMPORT:scripts/tests/json.py:SHADOWS:json` 拒绝。

提交前全门禁原样尾行：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
Ran 602 tests in 20.925s
OK
Ran 342 tests in 747.787s
OK
```

### T12 — `9a3f83d`

`isolation_canary.check` 按真实 schema 重写：顶层 `step_start|text|tool_use|step_finish|error`，
marker 只在 `part.text`，读取在 `tool_use` 的 `state.input.path`（同时兼容 `filePath`），完成
条件不再要求 `step_finish(reason=stop)`（真实 run 不产生它，旧实现因此在正确流上同时报
INCOMPLETE_STREAM 等六个原因）。文本判据：skill 来源必须是内置两个的子集，MCP / plugin agent
只在非"缺席声明"行上算污染，三处 canary 之外的 `AGENTS.md` 路径算全局/用户指令。

提交的 fixture 是真实正确流、把每个 run root 前缀替换成 `<RUN_ROOT>`（10 事件，无宿主路径）；
每个拒绝原因一个变异副本（marker 缺失、marker 早于其读取、额外读取、MCP、plugin agent、
skill catalogue、非 read 工具、截断流）。

用交接的两份真实流实际复跑（只读，未 source profile，未运行 opencode）：

```text
$PY .../isolation_canary.py check .../freeze-v2/fixtures/isolation-canary-events.jsonl
"verdict": "PASS", "reasons": [], "event_count": 10
# 退出码 0

$PY .../isolation_canary.py check <HOME>/.h2-runs/isolation-canary/events.jsonl
"verdict": "FAIL", "reasons": ["SKILL_CATALOGUE_CONTAMINATION"], "event_count": 10
# 退出码 1（该流的真实路径以交接给的 home 目录为准，此处只写 <HOME> 占位）
```

聚焦运行：

```text
Ran 6 tests in 0.066s
OK
```

提交前全门禁原样尾行：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
Ran 602 tests in 21.086s
OK
Ran 345 tests in 742.439s
OK
```

### T13 — `fb9ce4f`

`wrapper_delivery.run_root_reason` 拒绝两类 run root：位于操作员 HOME 之下，或任一祖先目录
（含 run dir 自身，但排除 prepare 自己写的 `AGENTS.md`）含 `.agents`、`.opencode`、`.claude`、
`AGENTS.md`、`CLAUDE.md`、`opencode.json`。`prepare` 在 `outside_repository` 之后、任何分配之前
调用它；`isolation_canary.prepare` 用同一函数。README §3 与 protocol-v2 §4 把 run root 只写成
`H2_RUNS_ROOT = <SHARED_RUN_ROOT>`（macOS Shared 目录、所有 home 之外），并把两个内置 skill
`opencode`、`report` 记为已披露、臂对称的运行时事实。

测试逐个 marker 建临时祖先并断言拒绝且不留下分配，另用 `HOME` 覆盖断言 home 规则，并保留一条
"干净 root 仍可用"的正向控制。第一次聚焦运行暴露父目录不存在（`run_dir.mkdir()` 不建父目录，
既有语义），修的是测试：

```text
ERROR: test_a_clean_foreign_run_root_is_still_accepted ... FileNotFoundError
Ran 6 tests in 1.310s
FAILED (errors=1)
```

修正后：

```text
Ran 6 tests in 1.310s
OK
```

提交前全门禁原样尾行：

```text
All checks passed!
35/35 checks passed
VIOLATIONS=0
Ran 602 tests in 21.785s
OK
Ran 347 tests in 750.981s
OK
```

### T14 — re-pin（本节在 T14 提交前写入）

manifest 的冻结集合从 32 增至 36：新增 `scope_v2.py`、`collect_v2.py`、`run_acceptance_v2.py`
与 `fixtures/isolation-canary-events.jsonl`。`collect_v2.py`、`run_acceptance_v2.py` 是
CODEX_FIXES_1 T14 点名要求；`scope_v2.py` 是 T10 的拒绝测试在 T11 程序存在之前就需要的规则
owner（规则本身仍来自 validator 的 `shadow_paths`，不复制）；fixture 是 T12 的冻结证据。四个
都以同一冻结机制钉住，避免出现"有冻结文件但未钉"的口子。manifest 自身仍有独立字面量，
逐字节变异测试现在覆盖 36 + 1 = 37 个文件。

materials 依 T8 规则前移到 T14 提交的父提交 `fb9ce4f80286c8c365d66bd8c9ed7df985f7b7a9`
（T13）。这是必须的：T13 改了 `wrapper_delivery.py`，若继续钉 `042f224`，冻结就会指向一个
已被替换的 runner 程序。交付载荷本身未变（carrier、`RULES.md`、WARM、routes、shortlist 与
T8 materials 逐字节相同），因此按同名程序重新测量而不是沿用旧测量：

```bash
$PY $H/freeze-v2/delivery_anchors.py . $H/admission/freeze-v2-input/shortlist.json \
    --materials fb9ce4f --out $H/freeze-v2/delivery-anchors.json
```

全部十任务跑完（8 分钟，未抽样），原样尾行：

```text
DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0, "WRAPPER": 10}
```

与旧文件的逐行比对（除 `materials_commit` 外无差异）：

```text
old materials 1dbcf3f2d3bc9ec0c230c36784db6adcc2a8713a
new materials fb9ce4f80286c8c365d66bd8c9ed7df985f7b7a9
neutral old {'CODEBUDDY': 0, 'AGENTS': 0, 'WRAPPER': 10} new {'CODEBUDDY': 0, 'AGENTS': 0, 'WRAPPER': 10}
rows with differences: []
oracle pre sets identical: True ran identical: True
full_suite pre sets identical: True ran identical: True
```

所以 README §2 的 4/20、7/20、20/20、WRAPPER 20/20 与 ran_delta = 0 仍然成立，§2 只是标明
最新一次测量在 `fb9ce4f`。随后重生成 run plan 与 manifest：

```bash
$PY $H/freeze-v2/build_run_plan.py --materials fb9ce4f80286c8c365d66bd8c9ed7df985f7b7a9 --out $H/freeze-v2/run-plan-v2.json
$PY $H/freeze-v2/build_manifest.py build --freeze-parent fb9ce4f80286c8c365d66bd8c9ed7df985f7b7a9 --out $H/freeze-v2/freeze-manifest.json
$PY $H/freeze-v2/build_manifest.py check
```

原样输出：

```text
RUN_PLAN_V2 runs=20 control_first=5 variant_first=5 fresh_episode=20
FREEZE_MANIFEST files=36 delivery_payload_equivalent_to_T2=YES
{"verdict": "PASS", "mismatches": []}
```

测试里的独立字面量按文件本身重算（36 个文件哈希 + manifest 自身哈希），不是从 manifest 抄写。

**anchor 规则的一处修改（公开说明）**：旧冻结测试用
`git log --diff-filter=A` 找到引入 manifest 的提交、要求 materials 等于它的父提交——这会把
materials 永久钉在 `042f224`，而 T13 之后的 runner 程序已经不同，等于用旧程序的门去担保新
程序的 run。改为四条更强且可持续的不变量：(a) materials 是 HEAD 的祖先；(b) 两个臂在
materials 与 HEAD 读出的投放字节完全相同（不是"同一提交"而是"同一载荷"）；(c) anchors 记录的
materials 等于 manifest 的；(d) shortlist 与 `wrapper_delivery.py` 在 materials 与 HEAD 相同。
任何交付输入日后被改动都会直接让测试变红，要求重新冻结。

**两处公开的判定口径**（供独立验收）：

1. 每个 run 只重跑 worker 树的完整 `scripts/tests`（两种 spelling），与 T2 的 RESOLVED PRE 集合
   比较；base 侧只在 oracle 门重跑。理由：协议 §5.2 要求的是"worker 完整套件相对 T2 PRE 不新增
   非通过 ID"，而 base 的完整套件已由 T2 在零 worker 编辑下完整测过。SYMLINKED 下 worker 的
   非通过集合与 RESOLVED 的 PRE 集合比较，环境导致的新失败不会被归一化掉，只会多阻塞，不会
   放宽。
2. 投放副本按内容识别，但 `H2_WARM/<dest>` ↔ `<dest>`、`H2_RULES.md` ↔ `RULES.md` 属同一 owner：
   同一字节出现在 owner 自己的路径上是修复（f02 的真实 candidate 就如此），出现在其它路径才是
   副本并拒绝；arm carrier 没有仓内 owner，出现即拒。这条写进 protocol-v2 §5.3，因为它决定了
   ACCEPT 边界。

本轮未做：没有运行 opencode、没有调用任何模型、没有 source `~/.h2-worker-profile/env.sh`、
未 push、未开 PR、未 merge、未运行 H2-R2，真实 PR CI 状态为 NOT_TRIGGERED。T11 的十任务正向
控制是把历史 candidate 的非测试 delta 应用到 B' 后运行的机械证据，不是实际实验结论。

T14 提交前全门禁原样尾行（从仓库根执行，`&&` 串联；长套件跑到底未抽样）。这一串跑在
T14 的最终代码树上，唯一晚于它写入的是本节这段证据文字：

```text
=== RUFF
All checks passed!
=== GOVERNANCE
35/35 checks passed
=== PUBLIC
VIOLATIONS=0
=== SCRIPTS_TESTS
----------------------------------------------------------------------
Ran 602 tests in 21.676s

OK
=== EXPERIMENTS_TESTS
----------------------------------------------------------------------
Ran 347 tests in 754.858s

OK
=== DIFFCHECK
（空输出，exit 0）
=== SCOPE_EMPTY
（空输出，exit 0）
```

其中 EXPERIMENTS_TESTS 的 347 项包含本轮新增的 scope 拒绝、collect、十任务正向控制、
十任务 unchanged-base 负向控制与真实 schema canary 用例。这段证据文字写入后又重跑了读取
文本的门（Ruff / governance / public release / `git diff --check`），结果同为全绿，见提交
记录；两个长套件不读本文件，故不再重复。
