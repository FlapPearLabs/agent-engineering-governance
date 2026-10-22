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

## T15–T17（implementer: opencode deepseek-v4.1-flash）

本节由第三轮实现者追加，对应 CODEX_FIXES_2（86ac104 的 acceptance round 2，F5/F6）。
T1–T9 与 T10–T14 的记录原样保留。分支仍为 `experiment/v1.2-h2-freeze-v2`，起点 HEAD
`73924e8`，按 T15→T17 顺序实现，每任务一个本地提交，提交身份 `FlapPearLabs`，message 结尾带
opencode 的 Co-Authored-By。写范围不变：`freeze-v2/**` 与
`experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py`。最终接受仍是 Claude 的独立职责，本轮没有
自批、没有 push/PR、没有执行任何 run、没有调用模型、没有 source profile 的 env.sh、没有写
profile 目录。

### T15 — `021a16e`

F5 的修法是把"运行时自述"换成"运行时自己的配置报告"，并让 canary 的三个声明只有一个可解析
来源。

- `isolation_canary.py preflight <run_dir> --profile-env <env.sh>`：解析 env 文件的 `export`
  行（不 source、不执行），以 `os.environ` 叠加上 profile 变量，cwd = run_dir，只运行
  `opencode debug paths` 与 `opencode debug config`；超时 120s；结论写入
  `<run_dir>/preflight.json`，退出码只对 PASS 为 0。PASS 条件：`home/data/config/cache/state`
  以及所有其它 status 路径都在 profile home 之下、`home` 等于 profile home、配置来源恰好是
  profile 的 `opencode.json` 与 profile 配置目录、且该文件字节等于冻结模板。
- `check`：MCP / plugin-agent / skill 三个声明**只**取自
  `H2_CANARY_SOURCES mcp=<n> plugin_agents=<n> skills=<names>`；行缺失、重复或不可解析一律
  `NO_SOURCES_LINE`，自由文本不再决定这三项。顺序、附着与指令路径规则全部保留；`mcp__` 工具
  事件仍然直接 FAIL。canary 的 wrapper AGENTS.md 新增了产生该行的要求。
- Fixtures（真实输出，仅做路径脱敏；公开扫描 VIOLATIONS=0，仓内无宿主路径）：
  `fixtures/canary-86ac104-events.jsonl`（86ac104 的 live 流，`<RUN_ROOT>` 占位）与
  `fixtures/isolation-canary-events.jsonl`（T12 的流）都是回归样本，现在只报
  `NO_SOURCES_LINE`，不再报 MCP/PLUGIN 污染；
  `fixtures/canary-86ac104-synthetic-sources-line.jsonl` 是**新的、命名与文档都标明 synthetic**
  的 PASS 样本（在 live 流上加入那一行）；`fixtures/preflight-debug-paths.txt` 与
  `fixtures/preflight-debug-config.json` 是 preflight 解析器的脱敏真实输出
  （`<PROFILE_HOME>`、`<OS_TMPDIR>`）。

一处必须公开的口径收窄：交接给的真实 `debug paths` 输出里 `tmp` 是
`<OS_TMPDIR>/opencode`（macOS 的 per-user 临时根，env.sh 不设置 TMPDIR），它不可能在 profile
home 之下。因此实现把 "every printed path under the profile home" 落成：`home` 必须等于 profile
home，其它所有 status 键（data/config/cache/state/bin/log/repos/db）必须在 profile home 之下，
未知键拒绝；`tmp` 单独只要求绝对路径并作为证据记录，不要求位于 home 下。若按字面要求，Claude
实测的那个正确 profile 会 FAIL，这条收窄是让规则与实测一致所必需，且只能放松 tmp 一个键。

开发聚焦运行（程序与测试同批写入，首次运行即 GREEN；负例由 fixture 变异承担，不是 RED 记录）：

```text
Ran 16 tests in 0.201s
OK
```

提交前全门禁原样尾行：Ruff `All checks passed!`、governance `35/35 checks passed`、public
`VIOLATIONS=0`、scripts `Ran 602 tests in 21.795s / OK`、experiments
`Ran 357 tests in 755.345s / OK`；`git diff --check` 与越界 scope diff 均为空输出、exit 0。

### T16 — `a5a0354`

F6 的修法是把 profile 配置从"未记录的实验输入"变成冻结输入。

- `worker-profile/opencode.json`：`$schema`、`autoupdate: false`、`share: "disabled"`、空
  `plugin`、空 `mcp`，以及 `permission: {"question": "deny"}`（JSON 两空格缩进 + 结尾换行，
  与现行 profile 文件同格式）。键名不是猜的：opencode 2.0.25 二进制内嵌的 config 校验器把
  `permission` 对象展开成 `{action, resource: "*", effect}`，其对外的 permission 对象模式把
  `question` 与 read/edit/bash/task/webfetch/... 并列枚举，effect 取值为
  `ask | allow | deny`；同一构建的内置 `build` agent 正是 `action: "question"` 的授权方。
  因此 `permission.question = "deny"` 合法且正好命中该动作。此处不声称曾用 `debug config`
  验证过安装结果——见下面的未做项。
- protocol-v2 §4 与 README §3：模板必须由操作员在首次 run 前逐字节安装；每次 run 之前由
  preflight 证明字节相等；单 run wall-clock 上限 90 分钟，超时按 §6 登记为 INVALID、不静默
  重跑、不算 worker 失败。README §5 第 1 条给出操作员的 preflight 命令与其含义。
- 模板进 manifest 与测试独立字面量；新增测试断言模板的确切内容（键集合、各值、
  `permission == {"question": "deny"}`）以及 `CONFIG_TEMPLATE` 正好指向该文件。

开发聚焦运行：

```text
Ran 14 tests in 0.592s
OK
```

提交前全门禁原样尾行：Ruff、governance 35/35、public VIOLATIONS=0、scripts
`Ran 602 tests in 21.896s / OK`、experiments `Ran 359 tests in 788.572s / OK`；diff-check 与
scope 均空。

### T17 — re-pin（本节在 T17 提交前写入）

按 T8/T14 的同一规则，materials 前移到 T17 提交的父提交
`a5a03543d2ccbe4cfa727ffa0be0bf513a871a39`（T16），并重跑交付锚，而不是沿用旧测量：现在的
测试要求 anchors 记录的 materials 等于 manifest 的 materials，且 materials 必须是 HEAD 的祖先。

```bash
$PY $H/freeze-v2/delivery_anchors.py . $H/admission/freeze-v2-input/shortlist.json \
    --materials a5a0354 --out $H/freeze-v2/delivery-anchors.json
$PY $H/freeze-v2/build_run_plan.py --materials a5a03543d2ccbe4cfa727ffa0be0bf513a871a39 \
    --out $H/freeze-v2/run-plan-v2.json
$PY $H/freeze-v2/build_manifest.py build --freeze-parent a5a03543d2ccbe4cfa727ffa0be0bf513a871a39 \
    --out $H/freeze-v2/freeze-manifest.json
$PY $H/freeze-v2/build_manifest.py check
```

十任务全部跑完（未抽样，8:17.83），原样尾行：

```text
DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0, "WRAPPER": 10}
```

与上一份 anchors 的逐字段比对（不写实施者本机路径）：

```text
old materials fb9ce4f80286c8c365d66bd8c9ed7df985f7b7a9
new materials a5a03543d2ccbe4cfa727ffa0be0bf513a871a39
identical apart from materials_commit: True
neutral {'CODEBUDDY': 0, 'AGENTS': 0, 'WRAPPER': 10}
```

manifest 的冻结集合从 36 增至 41：新增 T15 的四个 fixture 与 T16 的 profile 模板（T15 提交时
已先钉四个 fixture 为 40，T16 再钉模板），manifest 自身仍是独立字面量，逐字节变异测试现在覆盖
41 + 1 = 42 个文件。生成与 check 原样输出：

```text
RUN_PLAN_V2 runs=20 control_first=5 variant_first=5 fresh_episode=20
FREEZE_MANIFEST files=41 delivery_payload_equivalent_to_T2=YES
{"verdict": "PASS", "mismatches": []}
```

测试里的独立字面量按文件本身重算（41 个文件哈希 + manifest 自身哈希），不是从 manifest 抄写。
README §4 的计数与 materials 叙述、§5 的 preflight 步骤已同步。

T17 提交前全门禁原样尾行（在最终代码树上执行，晚于它写入的只有本节文字）：

```text
=== RUFF
All checks passed!
=== GOVERNANCE
35/35 checks passed
=== PUBLIC
VIOLATIONS=0
=== SCRIPTS_TESTS
Ran 602 tests in 23.564s
OK
=== EXPERIMENTS_TESTS
Ran 359 tests in 785.552s
OK
=== DIFFCHECK
（空输出，exit 0）
=== SCOPE_EMPTY
（空输出，exit 0）
```

T23（本提交）之前：

```text
=== RUFF
All checks passed!
=== GOVERNANCE
35/35 checks passed
=== PUBLIC
VIOLATIONS=0
=== SCRIPTS_TESTS
Ran 602 tests in 24.572s
OK
=== EXPERIMENTS_TESTS
Ran 378 tests in 809.480s
OK
=== NEVER_TOUCH
NEVER_TOUCH_DIFF_EMPTY
=== FREEZE_MANIFEST
{"verdict": "PASS", "mismatches": []}
```

### 本轮未做、未证明与遗留缺口

1. **live preflight 没有跑过。** 本轮禁止调用模型与写 profile，因此 `preflight` 只用脱敏的真实
   输出做过解析器与 CLI 测试；profile 里那份 `opencode.json` 是否已逐字节等于模板，第一次真实
   裁定属于 Claude（README §5 第 1 条）。实现没有声称已经证明。
2. **preflight 没有被验收程序强制消费。** `collect_v2.py` / `run_acceptance_v2.py` 不读取
   `preflight.json`，所以"每次 run 之前 preflight 必须 PASS"是操作员义务 + 留在 run dir 的证据，
   不是机械拒绝条件。把它升为 collection 的硬门会改变 T11 已冻结的验收语义（并需要重跑十任务
   正向/负向控制），本轮没有做；这是 F6 闭合度的残余缺口，应作为下一轮工具票的输入。
3. **90 分钟上限同样是操作员登记规则**，没有程序计时器；超时按 §6 登记为 INVALID。
4. 没有执行 H2-R2、没有 push/PR/merge，真实 PR CI 状态仍为 NOT_TRIGGERED；T15–T17 的机械证据
   全部来自本地门禁与十任务锚测量。

## T18–T20（implementer: opencode deepseek-v4.1-flash）

本节由第四轮实现者追加，对应 CODEX_FIXES_3（5b14c2b 的 acceptance round 3，F7）。
T1–T17 的记录原样保留。分支仍为 `experiment/v1.2-h2-freeze-v2`，起点 HEAD `c080fae`；
按 T18→T19→T20 顺序实现，每任务一个本地提交，提交身份 `FlapPearLabs`，message 结尾带
opencode 的 Co-Authored-By。写范围不变：`freeze-v2/**` 与
`experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py`。最终接受仍是 Claude 的独立职责：本轮
没有自批、没有 push/PR、没有执行任何 H2-R2 run、没有调用模型、没有运行 `opencode run`、
没有 source 或写 `~/.h2-worker-profile`、没有写 profile 目录。

### T18 — `run_h2r2.py`（run 的唯一执行路径）

F7 指出的缺口是"怎么执行一个 run"只存在于散文里。现在只有一条路径：
`next --runs-root R` / `run <run_id> --runs-root R` / `status --runs-root R`。

- run root 先过 T13 规则（不在任何 home 之下、祖先无 `.agents`/`.opencode`/`.claude`/
  `AGENTS.md`/`CLAUDE.md`/`opencode.json`），然后才分配；三个子命令都先判它。
- 计划顺序即唯一顺序：只有在 run-plan-v2.json 中排在它前面的 run 全部登记
  （ACCEPT/REJECT/INVALID/BLOCKED 都算登记）才允许开始；启动过的 run_id 永不再启动——
  第二次尝试被拒，且"启动过但没登记"的记录一次 `INVALID:INTERRUPTED`
  （`registered_by = SECOND_START_ATTEMPT_REFUSED`），计划因此能前进而不静默重跑。
- 步骤全部带时间戳写入 `R/<run_id>/run.json`：prepare（计划里的 materials commit）→
  preflight（FAIL ⇒ BLOCKED，worker 从未启动）→ render_brief 到 `CONTRACT.md` →
  worker 启动 → collect_v2 + run_acceptance_v2 → auditor → 一条 `R/registry-v2.jsonl`。
- worker 启动写成模块常量：`WORKER_COMMAND = ("opencode", "run", "--standalone", "--auto",
  "--format", "json", "-m")`、`LAUNCH_PROMPT = "Read ./CONTRACT.md and do what it asks."`、
  `ENV_ALLOW = ("PATH", "LANG")`（再叠加 profile env 文件的 export 行）、
  `WALL_CLOCK_LIMIT_SECONDS = 90 * 60`。超时按进程组 SIGKILL 并登记 INVALID:TIMEOUT；
  非零退出、`error` 事件、空事件流同样 INVALID（reason 逐条记录）。stdin 为 /dev/null，
  stdout → `events.jsonl`，stderr → `stderr.txt`，session id 从事件流读出。
- 登记行含 run_id、task_id、arm、verdict、audit verdict、final verdict、reason、session id、
  wall clock、以及 run dir 内每个 artifact 的 sha256（`repo/` 工作树不是 run artifact）。
- 替换 worker 命令 / preflight / auditor / 上限的参数只在 `execute()` 上，`run` CLI 不暴露；
  T20 的测试用同一事实断言 CLI 只有 `run_id` 与 `--runs-root`。

开发期冒烟（临时脚本在仓外，未入仓；不是门禁证据）：四种 stub 模式分别得到
ACCEPT（历史 candidate 非测试 delta）/ REJECT / INVALID:TIMEOUT / INVALID:WORKER_ERROR_EVENT；
计划顺序外启动被拒且不产生 registry 与 run dir；预检失败时 worker 未启动、run.json 只有
prepare/preflight/registry 三步且 preflight=BLOCKED。

### T19 — `run_audit_v2.py`（逐 run 独立评审）

- 验收之后，同一隔离 profile、同一模型、同一命令、新的 session，cwd = `R/<run_id>/audit/`：
  盲包 = 去掉 delivery 识别块的 CONTRACT.md、收集到的 base→worker diff、verdict.json 的
  白名单投影（不含 run_id/arm/run_dir/materials_commit）与 worker 报告。carrier 正文、
  `H2_WARM/` 包与遥测不投放进盲包。
- 冻结的 `ARM_REVEALING` 扫描只记录不修改：命中写 LEAKAGE（rubric §10，尽力而为）。
  `H2_WARM` 不在扫描表里，因为两臂布局相同（README §3），命名它不区分任何臂。
- 冻结的 `AUDIT_PROMPT`；auditor 自己写 `audit.json`，必须含 rubric §4 的 correctness、
  invalid_completion 与 rubric §2–§3 的 finding 列表（id / severity P0–P3 / category HV1–HV8
  或 null / location / evidence）。缺失、不可解析或不完整 ⇒ 该 run BLOCKED（不是 INVALID，
  也不是通过），原因以 `AUDIT_BLOCKED:*` 写入。
- 机械与评审两个结论都进登记，`strictest()` 取保守者；audit 只能收紧、不能放宽机械 ACCEPT。
  INVALID run 不审计（SKIPPED），保持 INVALID。

开发期冒烟（仓外临时脚本）：用 stub 同时扮演 worker 与 auditor，ACCEPT run 的 audit 步
执行了真实的 `prepare_bundle` + `evaluate`（cwd 为 audit 目录，argv 与 worker 相同），
结果 audit_verdict=PARTIAL、final_verdict=REJECT；盲包内无 CARRIER_KIND/run_id。

### T20 — tests、re-pin、报告

新增 11 个测试（`RunDriver` 8 + `RunAuditV2` 3），worker 始终是 stub：
ACCEPT 端到端（含 run.json 七步与时间戳、registry 每个 artifact 的 sha256 复核、next/status）、
无操作 ⇒ REJECT（即使 audit 给 PASS 也不放宽）、缩短上限 ⇒ INVALID:TIMEOUT、
`error` 事件 ⇒ INVALID、计划顺序与二次启动拒绝（含 INTERRUPTED 登记）、preflight 失败 ⇒
BLOCKED 且 worker 未启动、CLI 不暴露替换参数、strictest 组合、盲包不含臂标签并记录 leakage、
audit.json 缺失/畸形 ⇒ BLOCKED、完整 audit 回读。

这些测试写在 T18/T19 代码之后，首次运行即基本 GREEN；唯一真实 RED 是测试自身的笔误
（把 audit_verdict 的 PASS 误写成 ACCEPT、把注入的 stub 上限误写成默认 5400/120），
已在同一提交前修正。这里不声称它们是"先 RED 再 GREEN"的证据。

re-pin 按 T8/T14/T17 的同一规则做（materials = 本提交的父提交 = T19 的
`371fd482dfff0bf4e19d6d86437e1641bb16b365`），十任务重新测量而不是沿用旧值：

```bash
$PY $H/freeze-v2/delivery_anchors.py . $H/admission/freeze-v2-input/shortlist.json \
    --materials 371fd482dfff0bf4e19d6d86437e1641bb16b365 --out $H/freeze-v2/delivery-anchors.json
$PY $H/freeze-v2/build_run_plan.py --materials 371fd482dfff0bf4e19d6d86437e1641bb16b365 \
    --out $H/freeze-v2/run-plan-v2.json
$PY $H/freeze-v2/build_manifest.py build --freeze-parent 371fd482dfff0bf4e19d6d86437e1641bb16b365 \
    --out $H/freeze-v2/freeze-manifest.json
$PY $H/freeze-v2/build_manifest.py check
```

原样输出：

```text
DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0, "WRAPPER": 10}
RUN_PLAN_V2 runs=20 control_first=5 variant_first=5 fresh_episode=20
FREEZE_MANIFEST files=43 delivery_payload_equivalent_to_T2=YES
{"verdict": "PASS", "mismatches": []}
```

冻结集合从 41 增至 43（新增 `run_h2r2.py` 与 `run_audit_v2.py`），manifest 自身仍有独立字面量；
逐字节变异测试现在覆盖 43 + 1 = 44 个文件。测试里的字面量用脚本从文件字节重算（不是从
manifest 抄写），README §4 的计数与 §5 的执行入口、protocol-v2 §5 的"唯一执行路径"同步更新。

T18 提交前全门禁原样尾行（当时 `run_audit_v2.py` 已存在但尚未入该提交）：

```text
=== RUFF
All checks passed!
=== GOVERNANCE
35/35 checks passed
=== PUBLIC
VIOLATIONS=0
=== SCRIPTS_TESTS
Ran 602 tests in 23.582s
OK
=== EXPERIMENTS_TESTS
Ran 359 tests in 804.002s
OK
=== DIFFCHECK
=== SCOPE_EMPTY
SCOPE_EMPTY_OK
```

T19 提交前全门禁原样尾行：

```text
=== RUFF
All checks passed!
=== GOVERNANCE
35/35 checks passed
=== PUBLIC
VIOLATIONS=0
=== SCRIPTS_TESTS
Ran 602 tests in 23.187s
OK
=== EXPERIMENTS_TESTS
Ran 359 tests in 804.297s
OK
=== DIFFCHECK
=== SCOPE_EMPTY
SCOPE_EMPTY_OK
ALL_GATES_PASSED
```

### 本轮未做、未证明与遗留缺口

1. **没有跑过真实 worker 与真实 auditor。** 本轮的 ACCEPT/REJECT/INVALID 全部由 stub 产生；
   `run_audit_v2.audit()` 只有在 stub 扮演 auditor 时被端到端覆盖过，真实 opencode session
   的第一次执行属于 Claude。
2. **launch prompt 的模型行为未验证。** 冻结的是一个常量，不是"模型确实照做"的证据。
3. **driver 没有强制的并发锁**（只有 pid 存活判断的 lock 文件）：同一 run 的并发启动在
   单操作员假设下靠 lock + run dir + registry 三重拒绝，未做文件系统级原子锁。
4. **auditor 的 leakage 扫描是尽力而为**，且 `H2_WARM` 被有意排除；`report.md` 里若写
   载体名会以 LEAKAGE 记录而不是被清洗。
5. 没有执行 H2-R2、没有 push/PR/merge，真实 PR CI 状态仍为 NOT_TRIGGERED。

T20 提交前全门禁原样尾行（跑在最终代码树上；晚于它写入的只有本段文字）：

```text
=== RUFF
All checks passed!
=== GOVERNANCE
35/35 checks passed
=== PUBLIC
VIOLATIONS=0
=== SCRIPTS_TESTS
Ran 602 tests in 21.184s
OK
=== EXPERIMENTS_TESTS
Ran 370 tests in 760.166s
OK
=== DIFFCHECK
=== SCOPE_EMPTY
SCOPE_EMPTY_OK
ALL_GATES_PASSED
```

这段文字写入后重跑了读取文本的门（Ruff / governance / public release / `git diff --check` /
越界 scope），结果同为全绿；两个长套件不读本文件，故不再重复。

## T21–T23（implementer: opencode deepseek-v4.1-flash）

本节由第五轮实现者追加，对应 CODEX_FIXES_4（f94360c 的 acceptance round 4，F8/F9）。
T1–T20 的记录原样保留。分支仍为 `experiment/v1.2-h2-freeze-v2`，起点 HEAD `20719b5`；
按 T21→T22→T23 顺序实现，每任务一个本地提交，身份 `FlapPearLabs`，message 结尾带 opencode
的 Co-Authored-By。写范围不变：`freeze-v2/**` 与
`experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py`。没有自批、没有 push/PR/merge、没有执行
H2-R2、没有调用模型、没有运行 `opencode run`、没有 source 或写 `~/.h2-worker-profile`。
临时 run 目录只建在 `<SHARED_RUN_ROOT>/impl-scratch`（回合结束后删除）。

### T21 — `wrapper_delivery.py`：history-free 任务仓库（F8）

F8 的机制是 `repo/` 曾是治理仓的 `git worktree`，与主仓共享整个对象库，所以 worker 能
`git show` 到历史 candidate。现在的形状：

- `repo/` 是独立仓库：`git init` + 对治理仓里一个临时 ref 做 `--depth 1` fetch + 取出 B'，
  随后删除该 ref、所有 remote（本来就没有）、`FETCH_HEAD`/`ORIG_HEAD`/`COMMIT_EDITMSG`/
  `packed-refs`、reflog、`refs/remotes`、`refs/tags`、`worktrees` 与
  `objects/info/alternates`，再 `gc --prune=now`；HEAD 仍是 detached 的 B'（同一 SHA），
  `rev-list --all` 恰为 `[B']`，对象集合 == B' 及其 tree（80 个对象对 61 个文件，
  与 object 枚举逐项相等）。
- 投放后置条件全部 fail closed：`rev-parse --show-toplevel` 必须是 repo 自身；
  `rev-list --all == [B']`；`git remote` 空；无 alternates；`objects == reachable`；
  `git cat-file -e <本任务 candidate>` 必须失败；`repo/.git` 下任何普通文件的字节里
  不得出现治理 checkout 的路径。任一不满足即抛错，`cleanup` 删除整个 run dir。
- 临时 ref 在 `finally` 里删除；一次 prepare 约 0.5 秒。`cleanup` 兼容旧布局：
  `.git` 是文件（linked worktree）走 `worktree remove`，是目录（standalone）直接删。
- `collect_v2` 追加两条 fail-closed 理由：任务仓库出现 remote 或 alternates 链接即为
  `TASK_REPOSITORY_HAS_REMOTE` / `TASK_REPOSITORY_HAS_ALTERNATES`；base→worker diff 仍对
  注册表 base 做，不受影响。`run_acceptance_v2` 的 base 门也改成同一 standalone 形状。
- receipt 增加 `repository_kind = standalone_history_free`，测试直接断言。

交付锚点重测（不是沿用）：`PRE` 现在也是同样的 standalone、history-free 形状，否则
"history 依赖的测试"会被误算成交付污染。十任务两臂的完整重测输出：

```text
  r34-... pre oracle=4 suite=4/78 ... WRAPPER/control: DELIVERY_NEUTRAL, WRAPPER/variant: DELIVERY_NEUTRAL
  r37-... pre oracle=3 suite=3/96 ...
  r38-... pre oracle=8 suite=8/122 ...
  r39-... pre oracle=9 suite=9/178 ...
  r40-... pre oracle=9 suite=9/231 ...
  r41-... pre oracle=2 suite=2/274 ...
  r42-... pre oracle=8 suite=8/301 ...
  r24-... pre oracle=1 suite=1/423 ...
  r44-... pre oracle=2 suite=2/519 ...
  r50-... pre oracle=5 suite=5/598 ...
DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0, "WRAPPER": 10}
```

逐格比较新旧 JSON（脚本比较 `pre_delivery` 与 6 个 POST 单元的 `not_passing`/`ran`/`rc`
以及 8 个 verdict）：**没有任何一格变化**，输出 `identical`。也就是说这十个 base 的
`scripts/tests` 里没有依赖 git 历史的测试，history-free 形状本身是中性的；PRE 基线没有移动。
README §2 的数字因此仍是实测值（4/20、7/20、0/20、20/20、20/20），但现在来自本轮 JSON，
并且 §2/§3/§4 写明了新形状与重测事实。

锚点的 provenance 绑定方式变更（记录在此，供独立评审）：旧测试与 `build_manifest.build`
要求"锚点 commit 里的 `wrapper_delivery.py` 字节 == 当前程序字节"。改变投放程序的提交
（正是 T21）永远无法满足它——测量只能发生在提交之后，而门禁要求在提交之前。现在
`delivery-anchors.json` 记录 `repository`、`wrapper_program_sha256`、`shortlist_sha256`；
测试与 `build_manifest.build` 断言：投放 payload 在锚点 materials 与当前 HEAD 上逐字节相等，
且锚点由**当前冻结程序**在**当前冻结 shortlist** 上产生。这比 commit 字节比较更贴近真实
不变量，且没有放松 payload 相等这一条。

T11 正/负控制在 10 个任务上整体重跑（`AcceptanceV2` 两个测试，standalone 形状）：
正控（历史 candidate 的非测试 delta）ACCEPT 10/10；负控（未改动的 base）REJECT 10/10，
两种 temp-root spelling 都返回 `WORKER_NOT_PASSING:*`。输出 `Ran 7 tests in 193.894s / OK`。

### T22 — `access_audit.py`：从事件流审计越界访问（F9）

- 读 `events.jsonl`，对每个 `tool_use` 取 `part.state.input`：
  - 路径参数（`path`/`filePath`/`file_path`/`directory`/`dir`）解析到 run dir 之外即命中；
  - `bash` 命令按 token 检查（先按 `--flag=value` / `KEY=value` 拆分），`~`/`$HOME`/`${HOME}`
    解析到 **profile HOME**（driver 传入 worker 环境里的 HOME，绝不是操作员 HOME），
    相对路径按 cwd=run dir 解析，`<RUN_ROOT>` 占位符解析为 run dir；
  - `patch` 的 `patchText` 里 `--- a/x` / `+++ b/x` / `diff --git a/x b/x` 的路径同样检查；
  - shell `git` 的 `clone/fetch/pull/push/ls-remote/submodule`、`remote add|set-url|update|
    prune|rename|remove`、`-C <run 外>`、`--git-dir=<run 外>`、`--work-tree=<run 外>`；
  - 白名单外的工具（`webfetch`、`task`、`skill`、`mcp__*` 等）一律命中——事件流看不见的访问
    不可审计，因此保守拒绝；
  - 缺失事件流、非 JSON 行、无法识别的 tool 全部 fail closed。
- 冻结白名单（写入 audit JSON 的 `allow_list`）：固定解释器路径与其 prefix、`/usr`、`/bin`、
  `/sbin`、`/opt/homebrew`、`/System`、`/Library/Developer`、`/tmp`（含其 realpath）、
  解析后的 OS temp 根、`/dev/null`。**收紧记录**：没有放行整个 `/var/folders` 前缀，只放行
  解析后的 temp 根本身；`-C`/`--git-dir`/`--work-tree` 只对 run dir 判定（temp 目录可以做
  scratch，但不能作为 git 仓库目标）。
- `run_h2r2`：worker 结束、机械验收之前跑 access audit，写 `access-audit.json`（run artifact、
  进 registry artifact 哈希），每条命中变成 `OUT_OF_RUN_ACCESS:<reason>:<value>`。有命中时
  仍产出该 run 唯一的一份 `verdict.json` 与 collected 证据（与 worker 终局路径一致），
  但 verdict 为 INVALID、最终 verdict 为 INVALID，且 registry 已登记，第二次启动被
  `RUN_ALREADY_REGISTERED` 拒绝——命中无法靠重跑消失。worker 自己已经 INVALID 时
  （超时/error），access audit 仍作为证据步记录，但不改变终局 reason。
- 测试：两个入仓 fixture（clean / 四种命中形状）走 parser 与 CLI 双向；逐形状用例覆盖
  绝对路径、`..` 逃逸、`--flag=/x`、git clone/fetch/remote add、`git -C`、
  `git --git-dir`、白名单外工具、patch 头路径；纯解析函数用合成 home 覆盖 `~`/`$HOME`/
  `${HOME}` 与无 home 情况；白名单用例覆盖固定 PY、`/usr/bin/env`、`/bin/sh`、`/tmp`、
  `/dev/null` 与一次正常的 `unittest discover` 命令；缺失流与畸形行各一例。
  driver 层用读 `/etc/hosts` 的 stub worker 端到端得到
  `OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:/etc/hosts`、INVALID 登记与二次启动拒绝。

### T23 — re-pin、README、报告

re-pin 命令与输出（materials = 本提交的父提交 = T22 的 `b874db8515`）：

```bash
$PY $H/freeze-v2/build_run_plan.py --materials b874db851540aaf32c987b6ec037991056f478fa \
    --out $H/freeze-v2/run-plan-v2.json
$PY $H/freeze-v2/build_manifest.py build --freeze-parent b874db851540aaf32c987b6ec037991056f478fa \
    --out $H/freeze-v2/freeze-manifest.json
```

```text
RUN_PLAN_V2 runs=20 control_first=5 variant_first=5 fresh_episode=20
FREEZE_MANIFEST files=46 delivery_payload_equivalent_to_T2=YES
```

冻结集合从 43 增至 46（新增 `access_audit.py` 与两个 access-audit fixture），manifest 自身仍有
独立字面量；逐字节变异测试现在覆盖 46 + 1 = 47 个文件。测试字面量用脚本从 manifest 字节重算。
delivery anchors **没有**在 T23 重测：delivered payload、测量程序和 shortlist 在 T21 之后
都没有变化，manifest 恰好绑定这三者的哈希；README §4 如实写明这一点，而不是声称"每个
re-pin 都重测"。若 Claude 认为应重测，命令已在 README §2，重跑后需要重新 re-pin 一次。

### 提交前门禁原样尾行

T21（提交 `8b860b8`）之前：

```text
=== RUFF
All checks passed!
=== GOVERNANCE
35/35 checks passed
=== PUBLIC
VIOLATIONS=0
=== SCRIPTS_TESTS
Ran 602 tests in 21.779s
OK
=== EXPERIMENTS_TESTS
Ran 371 tests in 780.066s
OK
=== NEVER_TOUCH
NEVER_TOUCH_DIFF_EMPTY
```

T22（提交 `b874db8`）之前：

```text
=== RUFF
All checks passed!
=== GOVERNANCE
35/35 checks passed
=== PUBLIC
VIOLATIONS=0
=== SCRIPTS_TESTS
Ran 602 tests in 23.934s
OK
=== EXPERIMENTS_TESTS
Ran 378 tests in 828.822s
OK
=== NEVER_TOUCH
NEVER_TOUCH_DIFF_EMPTY
```

### 本轮未做、未证明与遗留缺口

1. **没有真实 worker 与真实 auditor。** T22 的端到端证据来自 stub worker 的事件流；
   `access_audit` 的第一次真实 verdict 属于 Claude 的 acceptance。
2. **可观测性边界**：audit 只能看到事件流里记录的 tool 调用。工具内部的隐式访问、隐藏的
   runtime 上下文、以及不产生事件的次生进程都不在可见范围内（audit JSON 的
   `observation_scope` 如实写明）。`task` 子代理被保守拒绝，因为它的子调用不在父流里。
3. **temp 白名单的必然放宽**：落在 OS temp 根内的路径会被放行（spec 要求放行 temp dirs），
   因此一个从 run dir 逃逸到 temp 根的 `..` 不会被判为越界；逃出 temp 根、`~`/`$HOME`、
   绝对路径与 git 外联都仍会被判。解释器 prefix 也在白名单里，worker 因此可以读该 env 目录。
4. **T21 未覆盖"worker 自己 fetch 对象"的静态检测**：standalone 仓库起点是干净的，`collect_v2`
   拒绝 remote/alternates，事件流里 `git fetch|clone` 会被 T22 判无效；但没有做
   "对象库里出现不可达对象"的 fsck 检查，因为正常 worker 的 `git commit --amend` / `stash`
   也会留下 dangling 对象，会产生误判。
5. 没有执行 H2-R2、没有 push/PR/merge，真实 PR CI 状态仍为 NOT_TRIGGERED。

## T24–T25（implementer: opencode deepseek-v4.1-flash）

计划：[CODEX_FIXES_5.md](CODEX_FIXES_5.md)。T24 提交 `f2f9ad9`；T25 是本节所在的 re-pin 提交。
写作用域未变；没有执行 `opencode run`、没有任何模型调用、没有跑 H2-R2、没有 push/PR。

### T24 — 关闭 F10–F13（`f2f9ad9`）

**F10（P1，真实工具名）**。`access_audit.TOOL_ALLOW` 与 `SHELL_TOOLS` 现在接受 `shell`，并把
它当作 shell 工具分析（`bash` 保留，供旧事件流使用）；文件工具继续接受真实流使用的 `path`
键。实测对照：修复前把 pilot 的真实事件流交给旧版 audit，得到 `INVALID` 与 **25 条
`TOOL_NOT_ALLOWED`**（25 次 `shell` 调用）；修复后同一流为 `PASS`，`tool_calls = 50`。

**F11（P1，worker 自己跑测试导致 REJECT）**。`run_h2r2.FROZEN_ENV = {"PYTHONDONTWRITEBYTECODE":
"1"}`，在 profile 的 `export` 之后应用，因此 profile 无法覆盖它；`worker_env()` 的返回值同时交给
worker 与 per-run auditor（`execute()` 把同一个 `env` 传给 auditor），`run.json` 记录
`frozen_env` 与 `env_allow_list`。原因侧修复，规则侧不动：`repo/` 下若仍出现 `.pyc`，仍按 scope
拒绝（`scope_v2` 的 BYTECODE 规则原样保留）。protocol-v2 §4/§5、README §3 的 ENV 段与 §4
都记下了这条决定。

**F12（P2，token 化）**。`shell_tokens()` 用 `shlex.shlex(posix=True, punctuation_chars=True)`
切分，分隔符成为独立 token：pilot 的 `source /dev/null; <PY> -m unittest …` 不再报
`PATH_OUTSIDE_RUN:/dev/null;`。`OPERATORS` 同时是 git 参数表的终止符。

**F13（P2，temp 目录被当成外来仓库）**。`git_hits()` 现在跟踪同一命令内的 `cd`，把每个 git
调用的 `-C` / `--git-dir` / `--work-tree` 依次应用到当前工作目录上，得到**有效仓库**；只有该
仓库既不在 run 目录、也不在 OS temp 根之内时才记 `GIT_FOREIGN_REPOSITORY`。因此 pilot 的
`cd <run> && … && git -C repo archive HEAD | tar -x -C <TMP>/h2-base-check && cd <TMP>/h2-base-check
&& <PY> -m unittest …` 为 PASS；`tar` 的 `-C` 不会再被读成 git 的 `-C`（这既是 F12 的
标点切分结果，也是 F13 的有效仓库判定）。

**保留下来的拒绝**：外联/远端类 `git clone|fetch|pull|push|ls-remote|submodule` 与
`git remote add|set-url|…`、白名单外的工具、run 与 temp 之外的任何绝对路径/`~`/`$HOME`/`..`
逃逸、`--git-dir`/`--work-tree` 指向外部、`patch` 的错误路径，全部照旧命中。既有测试里唯一被
改写的用例是 `git -C /tmp/other log`：按 F13，temp 根内的仓库是合法目标，该用例改为
`/srv/other`，并新增了 temp 侧的正向断言。

**真实事件流 fixtures（只读各自一次）**。两条真实记录被复制成
`fixtures/pilot-f01-c-events.jsonl`（155 事件、50 次 tool 调用，工具集合
`{read, write, edit, shell}`）与 `fixtures/toolname-probe-events.jsonl`（15 事件、6 次调用，每个
真实工具各一次：`read/glob/grep/shell/write/edit`）。sanitise 只做前缀替换：
`<RUN_ROOT>`（run 目录）、`<PY>`（固定解释器）、`<PY_ROOT>`、`<HOME>`、`<TMP>`；替换后逐行
`json.loads` 复核，并断言不再残留 `/Users/` 或 `/private/`。测试在临时 run 目录里把这些占位符
重新展开（`<PY>` 展开为当次 `sys.executable`，因此也落在 audit 的 allow-list 内）。

**新增测试**（5 个，外加 1 个改写）：

1. pilot 真实流：`PASS`，0 hit，155 事件 / 50 调用，工具集合不含 `bash`。
2. tool-name probe：六个真实工具名全部允许，`PASS`，6 调用。
3. pilot 的五个变异各自 `INVALID`：越界 `read`（`/etc/hosts`）、`git -C /srv/other`、
   `cat ~/notes.txt`、`cat ../../../etc/passwd`、把 `read` 改名成 `webfetch`。变异是对真实流
   的事件做结构改写（替换该次调用的 input 或工具名），不是另写一条想象出来的流。
4. F12/F13 正向与反向：分隔符、temp 归档管道、temp 内 git、`cd` 进 temp 后 git 均 `PASS`；
   `git -C /srv/other`、`cd /srv/other && git log`、`tar -x -C /srv/other` 均 `INVALID`。
5. worker env：`FROZEN_ENV == {"PYTHONDONTWRITEBYTECODE": "1"}`；`worker_env()` 的键集不超出
   `{PATH, LANG} ∪ profile exports ∪ {PYTHONDONTWRITEBYTECODE}`；通过 `mock.patch.object` 捕获
   `launch()` 真正收到的 env，并捕获 auditor 收到的 env，两者都逐字等于 `worker_env()`。

### T25 — re-pin 与报告

`build_run_plan.py --materials f2f9ad9` 重生成 run plan（20 run、C-first = V-first = 5），
`build_manifest.py build --freeze-parent f2f9ad9` 重生成 manifest（48 个冻结文件），
`build_manifest.py check` 为 `PASS`，两个独立锚（`EXPECTED_V2_HASHES` 与 `MANIFEST_SHA256`）
由程序从新 manifest 重写。README §4 的 re-pin 段改为本次提交与其父提交 `f2f9ad9`，并补记
T24 前移的内容；§3 增补 ENV 段；§4 的冻结文件计数改为 48 / 49。

交接说明：T24 提交后，上一实现会话在跑 T25 的最后几条 gate 时被中断，留下的未提交工作树
按 T25 的范围复核后才提交。复核不是重读自己的输出，而是重新执行生成器并比对字节：

```text
build_run_plan.py --materials f2f9ad9 --out <TMP>/run-plan.json
  -> RUN_PLAN_V2 runs=20 control_first=5 variant_first=5 fresh_episode=20
build_manifest.py build --freeze-parent f2f9ad9 --out <TMP>/manifest.json
  -> FREEZE_MANIFEST files=48 delivery_payload_equivalent_to_T2=YES
build_manifest.py check
  -> {"verdict": "PASS", "mismatches": []}
diff <TMP>/run-plan.json run-plan-v2.json        -> 无差异
diff <TMP>/manifest.json freeze-manifest.json   -> 无差异
```

两个独立锚与重生成结果逐字相等：`EXPECTED_V2_HASHES` 的 48 条与 manifest 的 `hashes` 完全
相同（程序比对），`MANIFEST_SHA256 = 82fd5e36bc57af8afb330f90d504a44777b49873b111035e748528f02526199b`
即 `freeze-manifest.json` 的 sha256，run plan 的 `1371946a…` 同时出现在 manifest 与测试字面量里。
manifest 的 `freeze_parent` 与 `materials_commit` 均为 `f2f9ad9`，即本次提交的父提交。

提交前在 T24 与 T25 各跑一遍 §0 GATES（前台，逐条等待；退出码不经管道）。T24 的记录：

```text
=== RUFF                 All checks passed!
=== GOVERNANCE           35/35 checks passed
=== PUBLIC               VIOLATIONS=0
=== SCRIPTS_TESTS        Ran 602 tests in 27.042s / OK
=== EXPERIMENTS_TESTS    Ran 383 tests in 906.336s / OK
=== NEVER_TOUCH          git diff --stat c40266f -- <NEVER TOUCH 路径> 为空
```

T25 提交前，被中断的会话之后由本 session 从干净状态整套重跑（下面每条都是实测；实验套件
整套跑了两遍，两次之间只有本报告文本不同，耗时分别为 838.199s 与 786.396s，结果同为 383
个测试 OK，故这里不把某一遍的秒数写成结论）：

```text
=== RUFF                 All checks passed!                 (exit 0)
=== GOVERNANCE           35/35 checks passed                 (exit 0)
=== PUBLIC               VIOLATIONS=0                        (exit 0)
=== SCRIPTS_TESTS        Ran 602 tests in 24.179s / OK       (exit 0)
=== EXPERIMENTS_TESTS    Ran 383 tests / OK                  (exit 0, 838.199s 与 786.396s 两次)
=== NEVER_TOUCH          git diff --stat c40266f -- <NEVER TOUCH 路径> 为空 (exit 0)
```

T24 之后实验套件从 378 增至 383（+5），`scripts/tests` 仍为 602；T25 只改 run plan、manifest、
测试字面量与文档，因此计数不变。

### 本轮未做、未证明与遗留缺口

1. **没有真实 worker run。** pilot 的 `PASS` 是对已经记录的流做 replay，不是新 run；
   `shell`/F12/F13 的第一次真实运行证据仍属于 Claude 的 acceptance（下一次 live pilot）。
2. **F13 的必然放宽（已声明）**：`git -C <temp 根内仓库>` 现在合法，因此一个把 base 解到 temp
   再在 temp 仓库里跑 git 的 worker 不会因此被判无效；逃出 temp 根、`~`、绝对路径、远端操作
   仍会被判。这是 CODEX_FIXES_5 F13 明文要求的行为，不是实现自选。
3. **可观测性边界不变**：audit 只看事件流记录的 tool 调用；工具内部隐式访问、隐藏 runtime
   上下文与不产生事件的次生进程不可见。
4. 真实事件流仍在 hand-off 给出的 run root 下；仓库里只有 sanitise 后的副本。
5. 未执行 H2-R2、未 push/PR/merge，真实 PR CI 仍为 NOT_TRIGGERED。
