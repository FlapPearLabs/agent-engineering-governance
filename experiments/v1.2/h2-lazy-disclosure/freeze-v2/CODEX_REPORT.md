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

## T26–T27（implementer: opencode deepseek-v4.1-flash）

计划：[CODEX_FIXES_6.md](CODEX_FIXES_6.md)。T26 提交 `4924930`；T27 是本节所在的 re-pin 提交。
写作用域未变；没有执行 `opencode run`、没有任何模型调用、没有跑 H2-R2、没有 push/PR。

### T26 — 关闭 F14：预注册的 provider 基础设施规则（`4924930`）

**F14（P1，基础设施噪声吃掉计数 run）**。live pilot #2 在 14 秒后 INVALID：worker 的首个也是
唯一事件是 `{"type":"error","error":{"type":"provider.no-route"}}`，退出码 1，零工具调用；数分钟
后同一 env 正常应答。这是两天内第三次短暂上游失败（401 Invalid credential、
"stream ended without finish_reason"、`provider.no-route`）。旧规则下该 run 永远不能再跑，噪声
而非处理本身会吃掉计数 run，且可能两臂不等。

规则在 CODEX_FIXES_6 中先于任何计数 run 决定。实现全部落在 `run_h2r2.py`；每一条 launchable
fact 仍是模块常量，CLI 仍只暴露 `--runs-root`（`run --help` 的选项集合仍为
`{--runs-root, --help}`，`probe` 只是 `execute()` 的测试用关键字参数）。

1. **REACHABILITY**。新增常量 `REACHABILITY_PROMPT = "Reply with exactly: H2_REACHABLE"`、
   `REACHABILITY_TOKEN`、`REACHABILITY_LIMIT_SECONDS = 120`。`reachability_probe()` 用 run 自己
   的 `command`、`model` 与 `worker_env()`（含冻结的 `PYTHONDONTWRITEBYTECODE=1`），在
   `<runs_root>/.reachability/` 下的 scratch 目录里以单条 prompt 启动一次；worker 之前与
   auditor 之前各一次。失败判据：超时、非零退出、`provider.*` 错误事件、空事件流、无文本回答。
   失败 => 返回 `{"outcome": "BLOCKED", "registered": False,
   "reason": "PROVIDER_UNREACHABLE:…"}`：删除本次 live run dir（保留更早的 `attempts/`）、
   删除 lock、不写 registry、不写 attempt ledger —— 即"没有消耗 attempt，之后可再次 `run`
   同一 id"。每次检查连同 started_at / finished_at / seconds / returncode / events /
   token_seen / verdict 追加进 `<runs_root>/reachability-v2.jsonl`；scratch 目录的
   `events.jsonl`、`stderr.txt` 保留为证据。`refusal()` 因此只把"run dir 内除 `attempts/`
   以外还有东西"当作已启动。
2. **BEFORE WORK**。`before_work_failure()` 只在两种形状返回原因：首个 tool_use 之前的
   `provider.*` 错误事件；或零 tool_use 且非零退出。命中即该 **attempt** 结束：其产物（不含
   `repo/`，与 registry 的 artifact 排除一致）归档到 `<run_id>/attempts/<n>/`，写
   `attempt.json`（逐文件 sha256、kind、reason、时间戳），随后在全新目录上重新 `prepare`
   （新 standalone repo、重新投放、重新 preflight）+ 重新 reachability + 再试。
   `MAX_ATTEMPTS = 3` 以 run id 为界（`next_attempt_number()` 从 ledger 续号，跨调用也不重号）。
   每个 attempt 是 `attempts-v2.jsonl` 的一行（attempt、kind、verdict、reason、archive、
   manifest_sha256、artifacts）。`registry-v2.jsonl` 仍每个 run id 恰好一行终止记录，新增
   `attempt` / `attempts` 字段说明它来自哪一次 attempt；`REGISTRY_DUPLICATE_RUN_ID` 的唯一性
   检查没有被放宽。
3. **AFTER WORK**。任何 tool_use 之后 `before_work_failure()` 直接返回 None：后续 provider
   错误、非零退出或超时仍按原样 INVALID。auditor 走同一规则、独立计数器：被 block 的 audit
   attempt 归档到 `<run_id>/attempts/audit-<n>/`，最多 3 次；机械裁定原样保留，全部 block 时
   记 `AUDIT_BLOCKED` 且 final verdict 仍取保守者。
4. **3 次之后**。当前 live 树归档为 `attempts/3/`，registry 写一行 `BLOCKED`
   （`attempt` = `attempts` = 3），driver 不再发第四次启动；`next` 因 BLOCKED 是 registered 而
   前进，但该 run id 之后不能再次 `run`。既有"blocked 与 invalid 分开、不能冒充 PASS"未变。
5. **文档与钉版**。protocol-v2 §6.1 记录规则全文、动机、三次观测与"两臂对称 / outcome-blind"；
   README §5 记录同一规则给操作员。manifest 与两个独立测试锚按新字节重钉（仍是 48 个冻结文件）。

**新增测试（7 个，全部 stub worker / stub probe，零模型调用）**：

1. `test_the_reachability_check_is_one_frozen_prompt_with_the_same_command`：prompt 恰是冻结
   文本，token、120 秒与 3 次上限都是常量。
2. `test_every_reachability_check_is_recorded_with_a_timestamp`：真实 `reachability_probe()`
   对两个本地 stub 命令各跑一次；FAIL 记录含 `PROVIDER_ERROR:provider.no-route`，PASS 记录
   `token_seen=True`；两条日志都有时间戳，命令尾部恰为 `[model, prompt]`，scratch 目录在
   `.reachability/` 下，run dir 从未创建。
3. `test_a_failed_reachability_check_blocks_without_consuming_an_attempt`：probe FAIL =>
   BLOCKED，worker 未启动（marker 不存在），无 registry / attempt ledger / lock / run dir；
   随后同一 run id 再次 `run` 直接 ACCEPT，`attempts == 1`。
4. `test_a_provider_error_before_work_is_retried_on_a_fresh_run_dir`：stub 第一次
   `provider.no-route`、第二次做完整的候选修复 => ACCEPT、`attempts == 2`、preflight 被调用 2 次
   （真·重新准备）；`attempts/1/run.json` 的 worker step 为 BLOCKED、events 保留
   `provider.no-route`、`attempt.json` 的哈希逐条复核、`repo/` 不在归档内；ledger 两行
   （PROVIDER_FAILED_BEFORE_WORK + TERMINAL），registry 一行
   `attempt=2 attempts=2 final=ACCEPT`，archive 的 manifest hash 与 ledger 对得上。
5. `test_three_before_work_failures_block_the_run_and_stop_retrying`：三次失败 => registry 一行
   `BLOCKED`（attempt/attempts = 3）、`attempts/1..3` 齐全、ledger 三行、stub 只被启动三次、
   `next` 前进，该 id 二次启动被 `RUN_ALREADY_REGISTERED` 拒绝。
6. `test_a_provider_error_after_a_tool_call_is_invalid_and_never_retried`：先有 tool_use 再
   provider 错误 => INVALID、只启动一次、无 `attempts/`、ledger 一行 TERMINAL。
7. `test_a_blocked_audit_is_retried_and_keeps_the_mechanical_verdict`：第一次 audit 的流是
   provider 错误 => `attempts/audit-1` 归档、第二次 audit PASS、机械裁定 ACCEPT 保留。

既有测试只改了两处断言（步骤表新增 `reachability` 一栏；escape stub 的事件顺序恢复为
tool_use 在前），其余断言的语义未放宽。

### T27 — re-pin 与报告

从仓库根执行（`T26 = 4924930b71473efcb7f7fd84973d5574f873b03c`）：

```text
build_run_plan.py --materials <T26> --out run-plan-v2.json
  -> RUN_PLAN_V2 runs=20 control_first=5 variant_first=5 fresh_episode=20
build_manifest.py build --freeze-parent <T26> --out freeze-manifest.json
  -> FREEZE_MANIFEST files=48 delivery_payload_equivalent_to_T2=YES
build_manifest.py check
  -> {"verdict": "PASS", "mismatches": []}
```

两个独立锚由程序从新 manifest 重写：`EXPECTED_V2_HASHES` 的 48 条与 manifest 的 `hashes` 逐字
相同（`freeze_is_intact()` 直接比较两个来源），`MANIFEST_SHA256`
= `300c56e75e9635895c57f654144d2f68910553ad709054e19e7ffe1e6ce281a3`
= `freeze-manifest.json` 的 sha256。manifest 的 `freeze_parent` 与 `materials_commit` 均为 T26，
run plan 的 20 条 `materials_commit` 同为 T26；交付载荷仍与 T8 materials 逐字节相同，所以 T2 的
中性测量没有被重算也没有被改写。README §4 的 re-pin 段改为本次提交与其父提交 T26，并把 T26
列入"前移的内容"。

提交前在 T26 与 T27 各跑一遍 §0 GATES（前台，逐条等待；退出码不经管道）。T26 提交链的实测：

```text
=== RUFF                 All checks passed!
=== GOVERNANCE           35/35 checks passed
=== PUBLIC               VIOLATIONS=0
=== SCRIPTS_TESTS        Ran 602 tests in 21.933s / OK
=== EXPERIMENTS_TESTS    Ran 390 tests in 820.465s / OK
=== NEVER_TOUCH          git diff --stat c40266f -- <NEVER TOUCH 路径> 为空
```

T27 的 gates 跑了两遍：写入本节之前的记录遍（同一棵树，只差本节文本），以及随后带 commit 的
提交链。记录遍的实测：

```text
=== RUFF                 All checks passed!
=== GOVERNANCE           35/35 checks passed
=== PUBLIC               VIOLATIONS=0
=== SCRIPTS_TESTS        Ran 602 tests in 22.143s / OK
=== EXPERIMENTS_TESTS    Ran 390 tests in 820.437s / OK
=== NEVER_TOUCH          NEVER_TOUCH_DIFF_EMPTY
```

T26 之后实验套件从 383 增至 390（+7），`scripts/tests` 仍为 602；T27 只改 run plan、manifest、
测试字面量与文档，计数不变。

### 本轮未做、未证明与遗留缺口

1. **没有真实 provider 证据。** reachability 与 before-work 规则的全部执行证据都来自 stub
   worker / stub probe（禁止模型调用）。第一次真实裁定属于 Claude 的 live pilot。
2. **pilot #2 的 INVALID 不回改。** 它已按 protocol-v2 §6 登记，本轮不重跑、不改写其记录；
   T26 只规定此后如何处理同类噪声。
3. **reachability 的判据是"runtime 有回答"，不是"回答恰好是那个 token"。** `token_seen` 被记录
   但 PASS 只要求非空文本：若模型答了别的话，仍视为可达，以免把风格差异误判成 BLOCKED。代价是
   一个"能回话但对真正 prompt 必失败"的 provider 仍会在 worker 侧变成 INVALID（零 tool_use、
   退出 0 的空回答按原规则 INVALID，不重试）。
4. **probe 不是免费的。** 每个 attempt / audit 之前各多一次模型调用；它只能降低"整个 run 被
   上游噪声摧毁"的概率，不能保证真实 prompt 一定成功。规则只在 worker 未动作时触发，因此不能
   用来重摇结果，也不能把 INVALID 变成 PASS。
5. 未执行 H2-R2、未 push/PR/merge，真实 PR CI 仍为 NOT_TRIGGERED。

## T28（implementer: opencode deepseek-v4.1-flash）

关闭 F15（P1，assume-unchanged 等 worker 可控状态掩盖 deny 编辑/删除）与 F18（P2，base commit
message 泄漏 candidate sha）。只动 `wrapper_delivery.py`、`collect_v2.py`、`delivery_anchors.py`、
`delivery-anchors.json`、冻结 manifest/测试字面量、README 与本节；`run_acceptance_v2.py`、
`scope_v2.py`、access audit 与所有既有拒绝规则原样保留。

### 实现

1. **driver 记录的 base，不读 repo/**。`wrapper_delivery.record_base()` 在 prepare 时（worker
   启动前）从 GOVERNANCE 仓库的 git objects 读取 `<base>` 的整棵树（`ls-tree -r -z --full-tree`
   + `cat-file --batch`，因此 in-tree `.gitattributes` 的 export 规则也不可能漏路径），写
   `<runs_root>/.driver/<run_id>/base/` 与 `base-manifest.json`：每个路径的 mode、type
   （file/symlink）、git blob sha 与内容 sha256。`cleanup()` 一并删除该目录；`.driver` 在 run dir
   之外，worker 不可写。
2. **collection 不信 git**。`collect_v2` 用 `os.walk(followlinks=False)` 遍历 worktree（只排除
   worktree 根上的 `.git/`），按 bytes/mode/type 与 manifest 比对得到 A/M/D/T；不使用
   `git status`、index、index flag、ignore 文件、`.gitattributes` filter、repo-local config 或
   `refs/replace`。deny 路径上的 D/M/T 与原规则一样是 `WORKER_SCOPE_DENIED`，base 测试文件被删除
   同样拒绝。
3. **diff 由字节生成**。交给 acceptance/auditor 的 `diff.patch` 是 snapshot bytes 对 worktree
   bytes 的纯 Python unified diff（无 git、无 external diff driver、无 textconv），因此
   `diff.external` / attribute 无法把它洗掉。repo/ 上仅存的 git 调用（`rev-parse`、`remote`、
   模型无关的 repository 形状检查）统一走 `wrapper_delivery.repo_git`：
   `GIT_CONFIG_NOSYSTEM=1`、`GIT_CONFIG_GLOBAL=/dev/null`、`GIT_NO_REPLACE_OBJECTS=1`、
   `-c core.attributesFile=/dev/null`、`-c core.fsmonitor=false`。
4. **F18 neutral delivered head**。`standalone_repository()` 先在 GOVERNANCE 仓库用
   `commit-tree <base tree>` 造一个**无父**提交（固定 message `h2 task base`、固定
   author/committer `H2 Delivery <h2@delivery.invalid>`、固定 date `2000-01-01T00:00:00 +0000`，
   因而对同一 tree 确定），经一个临时 `refs/h2-delivery/*` fetch 进 repo/ 后立即删除该 ref；
   base 提交本身从不进入 repo/。`verify_standalone()` 现在核验
   `tree(delivered_head) == tree(base)`、`rev-list --all == [delivered_head]`、对象集 == 可达集、
   无 remote/alternates、且 `git log --all` 不含 base 或 candidate 的 40-hex；receipt 同时记录
   `base_sha`（原提交）与 `delivered_head`，`verify_repo()` 核验 HEAD == `delivered_head`。
   `collect_v2` 把 receipt 的 `delivered_head` 一并写出，缺失即 `INCOMPLETE_RECEIPT`。
5. **acceptance 的 oracle 位置（T28 item 4 的核查结论）**：`run_acceptance_v2` 早已在
   **worktree 的字节上原地**运行 oracle 与完整套件（`gate(run_dir / "repo", ...)`，不经过
   `repo/.git` 的 checkout）；它唯一一次 git checkout 是 BASE 侧（`base_tree()` 对
   **GOVERNANCE** 仓库做 standalone checkout），不是从 repo/.git 物化 worker 结果。因此此处无需
   改动，结论按计划记录在本节。
6. `delivery_anchors.reset()` 改为重置到 delivered HEAD（base 提交对象已不在任务仓库里）。

### 攻击复现（全部 stub/fixture，无模型）

新增 `CollectionTrustNothing`：assume-unchanged 编辑/删除、skip-worktree 编辑/删除、`.gitattributes`
`-diff` + `filter` + repo-local `diff.external`、`refs/replace`（git 自己已看不到 worker 的提交，
collection 仍看到 M 与 diff 原文）、删除 `.git`（`TASK_REPOSITORY_UNREADABLE` 失败关闭）、
snapshot 缺失/与 receipt 不符（`MISSING_BASE_SNAPSHOT` / `BASE_SNAPSHOT_DOES_NOT_MATCH_RECEIPT`）
——每一种都在 collected changes/diff 中留有原文，并落 REJECT `WORKER_SCOPE_DENIED`（或 INVALID
失败关闭）。正向对照仍是原测试：十个任务的 candidate 非测试 delta 全部 ACCEPT，未改动的 base
全部 REJECT。

### 重新测量与 re-pin

`wrapper_delivery.py` 变了（F18），`build_manifest.py` 的 provenance 绑定会拒绝旧 anchors，因此
在 T28 程序上重测（不是手改 JSON）：

```text
$PY experiments/v1.2/h2-lazy-disclosure/freeze-v2/delivery_anchors.py . \
    experiments/v1.2/h2-lazy-disclosure/admission/freeze-v2-input/shortlist.json \
    --materials 4924930 --out experiments/v1.2/h2-lazy-disclosure/freeze-v2/delivery-anchors.json
DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0, "WRAPPER": 10}
```

逐字段对比旧 JSON：**只有** `materials_commit`（20719b56 → 4924930）与
`wrapper_program_sha256` 变化，10 个 row（含每个 PRE 集合、每个 `ran`、每个 POST cell、每格
verdict）逐字节相同；README §2 的数字因此仍然成立。随后用同一 freeze parent 重建 manifest 与
两个独立测试字面量（仍 48 个冻结文件）：

```text
$PY .../build_manifest.py build --freeze-parent 4924930b71473efcb7f7fd84973d5574f873b03c \
    --out .../freeze-manifest.json
FREEZE_MANIFEST files=48 delivery_payload_equivalent_to_T2=YES
$PY .../build_manifest.py check
{"verdict": "PASS", "mismatches": []}
```

### T28 gates（前台逐条运行，退出码不经管道）

```text
=== RUFF                 All checks passed!
=== GOVERNANCE           35/35 checks passed
=== PUBLIC               VIOLATIONS=0
=== SCRIPTS_TESTS        Ran 602 tests in 24.828s / OK
=== EXPERIMENTS_TESTS    Ran 395 tests in 914.822s / OK
=== NEVER_TOUCH          git diff --stat c40266f -- <NEVER TOUCH 路径> 为空
```

上面是写入本节时的记录遍（实验套件 390 → 395，+5：base snapshot、index flags、
attributes/local-config/replace、snapshot 缺失/不符、删除 `.git` 各一条）。写完后同一棵树的
gates 再整体跑一遍并与 commit 以 `&&` 串联，任一门失败则不提交。

## T29（implementer: opencode deepseek-v4.1-flash）

关闭 F16（P1，动态路径绕过 access audit）、F17（P2，事件流可被 worker 删除/改写后重摇）、
F19（P2，跨 run 共享 worker state）与 F21（P3，TMPDIR 隐式继承）。新增冻结模块
`sandbox_v2.py` 与冻结模板 `worker-sandbox.sb.template`，改动 `run_h2r2.py`、`access_audit.py`、
`run_audit_v2.py`、`isolation_canary.py`（preflight 可针对 fresh home）与 `wrapper_delivery.py`
（只改 driver base snapshot 的写法，见下）；README §3/§4、protocol-v2 §4.0/§5/§6、manifest 与
测试字面量同步更新。所有既有拒绝规则与测试保留，未放宽任何一条。

### 实现

1. **OS 隔离（F16）**。每次 launch（worker、per-auditor、以及每次 reachability 检查）都是
   `sandbox-exec -f <rendered profile> <the frozen command>`。渲染规则：launch 目录（worker 为
   run dir，auditor 为 audit dir）与 per-launch home 读写；解释器（`sys.executable` 及其
   realpath、prefix、base_prefix）只读；launch 目录的每个祖先目录（给定与 realpath 两种拼写）
   以 `literal` 只读；`/Users`、`/private/tmp`、`/var/folders`、`/private/var/folders` 之下其余
   内容对 `file-read-data` 与 `file-write*` 一律拒绝。模板冻结在 manifest；每次 launch 渲染出的
   profile 写入 driver 的 attempt 目录，其 sha256 与模板 sha256 一并进 run record。
   实测（本机 darwin + `/usr/bin/sandbox-exec`）：`cat`、`sh -c 'cat $(printf ...)'`、
   `base64 -d | xargs cat`、`<PY> -c open(...)` 读 driver 投放文件全部 EPERM；launch 目录与
   home 内写入成功；`/etc/hosts`（不在拒绝根下）仍可读，如实作为披露事实，不宣称全盘封闭。
2. **confinement 自检**。每次 launch 之前在同一 rendered sandbox 内跑三条无模型命令：`cat` 与
   `<PY> -c open(...)` 读 `.driver/<run_id>/confinement-plant.txt`（随机 token）必须失败且不泄漏
   token，launch 目录内写 `.confine-write` 必须成功。不满足 => `BLOCKED:SANDBOX_NOT_CONFINING`；
   平台无 `sandbox-exec` => `BLOCKED:SANDBOX_UNAVAILABLE`。两者都不消耗 attempt、不登记、
   清掉 lock、把原因追加到 `.driver/<run_id>/blocked.jsonl`，同一 run id 可再次 `run`。
3. **fresh per-launch home（F19）**。`sandbox_v2.fresh_home()` 每次都删旧建新，mode 0700，只放
   冻结的 `worker-profile/opencode.json` 与自己的 `XDG_*` 目录；worker 为 `home-<n>`、auditor 为
   `audit-home-<n>`、每次 reachability 为 `probe-home-<purpose>-<n>`。credential 由
   `opencode auth export --standalone opencode`（master profile env）经 stdin 管道进
   `opencode auth import --standalone`（fresh env）；只记录 return code、字节数与 stderr 的
   sha256，secret 不进 argv、日志、events、registry 或 stdout。每次 launch 之后在 fresh home 里
   `opencode auth logout`（best effort，结果写入 `logout.json` 与 run record）。master profile
   从不挂载进 sandbox。
4. **driver-held 流（F17）**。worker/auditor 的 stdout/stderr 直接写到
   `<runs_root>/.driver/<run_id>/attempt-<n>/`（与 `audit-attempt-<n>/`），不在 sandbox 可写集合
   内；before-work 规则、tool-call 计数、access audit 与 EVIDENCE 判定只读该副本，run dir 里的
   `events.jsonl`/`stderr.txt` 是启动后复制给人读的副本。副本缺失/不可读 =>
   `INVALID:EVIDENCE_MISSING`，终局且不重试。
5. **TMPDIR（F21）**。每次 launch 的 env 为 master env + `HOME`/`XDG_*` 指向 fresh home +
   `TMPDIR=<launch dir>/.tmp`，`PYTHONDONTWRITEBYTECODE=1` 最后应用；不再继承操作员的 TMPDIR。
6. **access audit（F16 证据层）**。既有规则与裁定全部保留；新增 `unresolved_constructs`
   （`COMMAND_SUBSTITUTION`、`BACKTICK`、`EVAL`、`INLINE_PROGRAM`、`DECODER`、`XARGS`）与
   `sandbox_denied`（tool result 含 "Operation not permitted" 且绝对路径在 launch 目录之外）。
   预注册行为：`sandbox_denied` 不改变 verdict（被拒绝的动态访问没有获得任何东西，按 run 报告）；
   静态命中仍 `INVALID`。
7. **preflight 针对 fresh home**。`isolation_canary.preflight(run_dir, env_file, home=, env=)`
   用该 launch 的 fresh env 调 `opencode debug paths/config`，要求配置来源恰是 fresh home 的
   `opencode.json` 且字节等于冻结模板；不给 `home`/`env` 时保持原 master-profile 行为。
8. **base snapshot 不再抹掉 driver 证据**。`wrapper_delivery.record_base()` 原先把整个
   `.driver/<run_id>` 删掉再写 base；T29 的 homes/streams 也在那里，重试时会丢失上一 attempt 的
   driver 证据。现在只替换 `base/` 与 `base-manifest.json`，其余 driver 证据保留。
   因为 `wrapper_delivery.py` 变了，manifest 的 provenance 绑定要求重测 delivery anchors
   （不是手改 JSON）：`DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0,
   "WRAPPER": 10}`，与 T28 相比只有 `wrapper_program_sha256` 一个字段变化，10 个 row 逐字节相同。

### 测试（全部 stub/fixture/fake credential，无模型）

新增 `SandboxConfinement`（真实 `sandbox-exec`，非 darwin 或无 sandbox-exec 时 `skipUnless`）：
模板拒绝根与 allow 面、三种动态读（`cat`、命令替换、base64|xargs、`-c`）全部失败且不泄漏 token、
launch 目录写入成功、自检 PASS 且 profile 与 hash 归档、permissive profile 自检 FAIL、
无 sandbox 时 BLOCKED 且可再次 run、自检失败 BLOCKED 且可再次 run、credential 导入失败 BLOCKED
且可再次 run。新增 `DriverConfinement`：stub 在 tool call 之后删除/改写 `run_dir/events.jsonl`
仍按 driver 副本判 `INVALID`（`WORKER_ERROR_EVENT`、tool_calls=1、不重试、run dir 副本等于
driver 副本）；两次 attempt 各自独立 fresh home（0700、只含冻结 config、`audit-home-1` 存在、
`TMPDIR=run_dir/.tmp`、profile 与 hash 入 record）；一个 home 里放入的 transcript/credential 不会
出现在新 home；真实 sandbox 下 `-c` 动态读被拒并记入 `sandbox_denied`/`INLINE_PROGRAM`，run 仍是
`REJECT` 而非 `INVALID`。`AccessAudit` 增加两种证据字段的单元测试。

### T29 gates（前台逐条运行，退出码不经管道）

```text
=== RUFF                 All checks passed!
=== GOVERNANCE           35/35 checks passed
=== PUBLIC               VIOLATIONS=0
=== SCRIPTS_TESTS        Ran 602 tests in 25.007s / OK
=== EXPERIMENTS_TESTS    Ran 408 tests in 979.635s / OK
=== NEVER_TOUCH          git diff --stat c40266f -- <NEVER TOUCH 路径> 为空
```

实验套件 395 → 408（+13：`SandboxConfinement` 7、`DriverConfinement` 4、access audit 证据字段 2）。
写完后同一棵树的 gates 再整体跑一遍并与 commit 以 `&&` 串联，任一门失败则不提交。

## T30（implementer: opencode deepseek-v4.1-flash）

F20 的四个 P3 项，未改任何既有拒绝或既有测试。

1. **run_root_reason（P3-1）**。`wrapper_delivery.os_home_directories()` 从 OS 用户数据库
   （`pwd.getpwall()`）取全部 home，排除共享 users 目录（用 `Path("/Users") / "Shared"` 组合，
   不在文本里写具名路径）、`/var/empty`、`/dev/null` 与非目录项；`run_root_reason()` 先拒绝
   进程 `Path.home()` 之下（沿用 `RUN_DIR_UNDER_OPERATOR_HOME`），再拒绝**任何** OS home 之下
   （新原因 `RUN_DIR_UNDER_USER_HOME`），因此把 HOME 改到别处也不能把 run root 落回真实 home
   或另一个账户的 home。祖先 marker 改用 `os.path.lexists`：指向不存在目标的 `.agents` /
   `.opencode` 断链同样拒绝（runtime 从 cwd 向上发现的就是这个目录节点）。
2. **blocked audit 归档（P3-2）**。§6.1 要求被 block 的 audit 尝试同样归档。auditor 的
   reachability block、fresh-home/credential block 与 confinement 自检 block 现在都写
   `<run_id>/attempts/audit-<n>/probe.json`（含尝试号、阶段、blocked 原因、probe 记录、
   confinement 的 profile sha256），`probe_sha256` 与该 archive 路径同时进 run record 的 audit
   step；provider-before-work 的 audit 尝试仍由既有 `archive_tree`（`attempt.json`）归档。
3. **README 前置条件（P3-3）**。README §5 新增 “Run prerequisites”：`PYTHONPATH` 必须为空
   （宿主 `sitecustomize` 可预导入 stdlib 模块而掩盖 F1 shadow 测试）、解释器需满足
   `os.open in os.supports_dir_fd`（`scripts/tests/test_skill_execution.py` 需要）、macOS +
   `sandbox-exec`（否则 driver 在任何 worker 之前 `BLOCKED:SANDBOX_UNAVAILABLE`）。
   §4 的冻结文件数与 §3 RUNS_ROOT、§5 audit 归档说明同步更新；run root 拒绝规则改述为
   “任何 OS home”，并说明断链 marker 也算。
4. **`aggregate_runs.py`（P3-4）**。新增冻结程序，输入一个 runs root 的
   `registry-v2.jsonl`、`attempts-v2.jsonl` 与每个 run 自己的 verdict 文件，输出：每个 task 每
   臂的有效配对（`final_verdict` ∈ {ACCEPT, REJECT} 且 `<run_id>/audit/audit.json` 可读且合法）、
   INVALID / BLOCKED / MISSING 列表与登记原因、每个 run 的 attempt 账本、以及 protocol-v2 §7
   结果 token 与**决定它的确切规则**。判定顺序（第一条命中即 `decided_by`）：
   `COVERAGE:MISSING|INVALID|BLOCKED` → `AUDIT_VERDICT_MISSING` → `S1_DESIGN_PRECONDITION_NOT_MET`
   → `S2_MISSED_GUIDANCE_GE_1:<run>:<finding>` → `S3_TREATMENT_ONLY_INVALID_COMPLETION`
   → `S4_TREATMENT_ONLY_CORRECTNESS:<task>` → `NULL_DIFFERENCE`（每对臂的 audited correctness、
   invalid-completion 与 finding 身份集合全同 ⇒ INSUFFICIENT，§7 预注册 null 规则）
   → `NO_COST_OBSERVED:COMPLETE_COVERAGE+NON_NULL_DIFFERENCE+S1_SATISFIED`。
   finding 身份、correctness、invalid-completion 只从 audit verdict 文件读取，程序不自行重标；
   任一缺失即 INSUFFICIENT 并点名 run。S1 是冻结载体面设计事实，从 `variant-manifest.json`
   读（14136 → 5032 js_chars = 64.4% ≥ 30，VARIANT_FULLY_DELIVERED=true）。S5 的 M6 属 rubric
   §5 判定，输出显式标注 `pending_rules=["S5"]`、`result_scope="runs_root_mechanical"`：
   该 token 是 runs-root 机械结果，不能替代 closure report。`run_h2r2.py status` 另以同一
   `aggregate_runs.usable` 判据打印 `usable_pairs`、`planned_pairs`、`blocked`、`invalid`，
   因此 “registered=20” 不再被当成结论。
5. **re-pin**。改了 `wrapper_delivery.py`，故按既有规则**重测** delivery anchors（不手改 JSON）：
   命令同 README §2，`--materials 4924930`；结果 `DELIVERY_ANCHORS neutral per slot:
   {"CODEBUDDY": 0, "AGENTS": 0, "WRAPPER": 10}`，与 T29 相比只有 `wrapper_program_sha256`
   一行变化（`6623762…` → `24da46f…`），10 个 row 逐字节相同。manifest 在 4924930 重建，
   51 个冻结文件（新增 `aggregate_runs.py`），两份独立 literal（`EXPECTED_V2_HASHES` 与
   `MANIFEST_SHA256`）同步重钉。

### 测试（全部 stub / fixture / fake credential，无模型、无真实凭据）

`WrapperDelivery` 新增两项：HOME 指向临时目录时，真实 OS home 与另一 OS home 下的 run root 仍被
`RUN_DIR_UNDER_USER_HOME` 拒绝（共享 users 目录不在 home 集合里）；断链 `.agents` 让
`run_root_reason` 与 `prepare` 都拒绝且不留目录。`RunDriver` 新增两项：auditor 的 reachability
block 与 confinement 自检 block 各自在 `attempts/audit-1/probe.json` 留下阶段、原因与
`probe_sha256`，run 随后仍 ACCEPT；既有 flaky-auditor（provider-before-work）归档测试不变。
`AggregateRunsV2` 六项：完整且非 null 的 runs root ⇒ `DISCLOSURE_SAFE` 与确切规则串、
`usable_pairs=10/10`、`pending_rules=["S5"]`；一条 audited MISSED_GUIDANCE ⇒ `HAS_COST`
（`S2_…:h2r2-f03-v:miss-1`）；variant correctness 更差 / invalid-completion 更多 ⇒ `HAS_COST`
（S4 / S3）；缺一个臂 ⇒ `COVERAGE:MISSING:f07/variant` 且 `missing`/`audit_missing` 点名；
INVALID/BLOCKED 各带登记原因与 attempt 账本；两臂 audited 结果全同 ⇒ `NULL_DIFFERENCE`
（宁可 INSUFFICIENT 也不报 SAFE）。`status` 断言 `planned_pairs=10`、`usable_pairs=0`、
`blocked=0`、`invalid=0`。

### T30 gates（前台逐条运行，退出码不经管道，PYTHONPATH 未设）

```text
=== RUFF                 All checks passed!
=== GOVERNANCE           35/35 checks passed
=== PUBLIC               VIOLATIONS=0
=== SCRIPTS_TESTS        Ran 602 tests in 23.800s / OK
=== EXPERIMENTS_TESTS    Ran 418 tests in 974.488s / OK
=== NEVER_TOUCH          git diff --stat c40266f -- <NEVER TOUCH 路径> 为空
```

实验套件 408 → 418（+10）。

## T32（implementer: opencode deepseek-v4.1-flash）

CODEX_FIXES_8 的 F22–F25。四条都来自 live pilot `pilot-4864655c`（真实 sandbox + fresh home，
跑完 reachability、preflight、confinement、worker、collection、acceptance、access audit、
auditor、registry）。没有改任何既有拒绝，也没有削弱既有测试；既有测试的改动只有三处，都是
本次规则改变后的如实适配，见下。

1. **F22 服务端口**。`opencode debug paths|config` 不是独立命令：没有 service 设置的 fresh home
   会在默认端口上启动 managed 后台服务；机器上已有另一个 opencode 服务占用该端口时即
   `Managed service port ... is already in use`、exit 1、`PREFLIGHT_COMMAND_FAILED:config`，每个
   run 都会被 BLOCKED。`isolation_canary.preflight` 现在在**fresh home 认证**路径（driver 传入
   `home` + `env`）里按序执行：`opencode service set port <由 driver 选的空闲 127.0.0.1 端口>`
   → `debug paths` → `debug config` → `opencode service stop` → `opencode service status`。
   `preflight.json` 新增 `service`：端口、set/stop/status 返回码、status 原文、`left_running`、
   `reasons`；`commands_run` 记录实际执行的完整 argv 序列。stop 即使在前面的 debug 失败后也一定
   执行；stop 失败如实写进 `service.reasons` 与 preflight 原因（`PREFLIGHT_SERVICE_STOP_FAILED:n`），
   不隐藏。`service status` 仍显示服务（非 `stopped`）⇒ 原因 `SERVICE_LEFT_RUNNING`，preflight
   不 PASS，该 run 按既有 preflight 语义登记 BLOCKED（`PREFLIGHT_FAIL:SERVICE_LEFT_RUNNING`），
   `preflight.json` 留在 run dir 作为证据。master profile 认证路径（无 `home` 参数）**不**改操作员
   自己的 service 设置，仍只跑两条 debug。
2. **F23 真实 reachability 路径**。`default_probe` 把 `prepared` 交给 `confined`，而 `confined`
   读 `prepared["profile"]`；`default_probe` 从未把 `confine_state` 渲染出的 profile 放进去，
   于是每次真实 probe 都 `KeyError: 'profile'`，且只捕获 OSError/ValueError ⇒ driver 带 traceback
   退出，run 停在已准备未登记。修复是该赋值；此前所有测试都注入 `probe=passing_probe`，真实路径
   从未被测到（本次新增真实路径测试，见下）。
   同时按 T32 增加顶层守卫：`execute()` 现在只保留输入检查（runs root、plan、registry），真正的
   run 主体搬进 `drive()`，外层 `try/except Exception` 交给 `harness_defect()`。worker 启动**之前**
   的意外异常 ⇒ 本次调用 `BLOCKED:HARNESS_DEFECT:<ExceptionType>`：traceback 写
   `<runs_root>/.driver/<run_id>/harness-defect-<stamp>.txt`，`blocked.jsonl` 记一条，run 目录撤回
   （attempt 归档保留），lock 释放，不消耗 attempt、不登记，同一 run id 可再次 `run`；worker 启动
   **之后** ⇒ 该 run 登记 `INVALID:HARNESS_DEFECT:<ExceptionType>`（run.json 与 registry 各带
   `harness_defect`，attempt 账本记 `HARNESS_DEFECT` 行），不再启动第二次。判定只取启动边界，对
   结果盲。规则写入 protocol-v2 §6.1。
3. **F24 合同里的仓库身份**。T28 交付的是中性 HEAD（f01: `42123e7`），渲染的 CONTRACT 却仍写
   `EXPECTED_BASE_SHA = e11a846`（原始 base），live worker 按合同做 S0 检查后如实停机，两臂都会
   这样结束。现在 CONTRACT §0 写 `EXPECTED_HEAD = <本次投递实际 HEAD>`，并由投递自身同一组函数
   计算（`wrapper_delivery.task_source()` 取注册 base，再 `neutral_commit()` 生成 base tree 的
   确定性中性 re-commit——`prepare` 的 `standalone_repository` 用的就是它），合同同时说明它是
   注册 base tree 的中性 re-commit（单一无父提交、固定 message/author/date，repo/ 不含历史）。
   registry 的 `base_sha` 仍是登记身份。原始 base 与 candidate sha 不再出现在 worker 可见面：
   `receipt.json`（worker cwd 内）删掉 `base_sha`，base 身份只留在 registry 与 driver 的
   `.driver/<run_id>/base-manifest.json`；`collect_v2` 因此改从 driver manifest 读 base 并与 registry
   比对（拒绝原因 `BASE_SNAPSHOT_DOES_NOT_MATCH_REGISTRY`，同一拒绝、只是换掉了 receipt 那一半）。
   审计盲包里的 CONTRACT 也随之写实际 HEAD（身份块本身仍被移除）。
4. **F25 TMPPREFIX**。worker 的 shell 是 zsh，heredoc 临时文件写在 TMPPREFIX 下（默认
   `/tmp/zsh`）而不是 TMPDIR，`/private/tmp` 被 sandbox 拒绝 ⇒
   `can't create temp file for here document`，worker 只能退回 write tool，这个常见 shell 用法在
   两臂都不可用。`sandbox_v2.home_env()` 现在在 TMPDIR 之外给出 `TMPPREFIX=<launch dir>/.tmp/zsh`
   （文件前缀，不需要建目录）；protocol-v2 §4.0 F25、§4 环境段、§5 与 README §3 FRESH HOME 均已
   记录。§5 也补了 F22 的 service 序列与 F24 的合同身份。

### 测试（全部 stub / fixture / fake credential / sandbox-exec，无模型、无真实凭据）

- `RealProbePath`（`skipUnless` darwin + `sandbox-exec`）：`execute(..., probe=None)` 走**真实**
  default probe、真实 sandbox、`StubAuth`，stub 命令在收到冻结 probe prompt 时回答
  `H2_REACHABLE`、否则充当 worker。断言 probe PASS 且 `token_seen`、confinement PASS、
  credential 已 logout、worker 事件在 run dir 而 probe 的 token 不在其中、registry 一行 REJECT。
  该测试对 F23 有牙齿：把那一行赋值删掉后它立刻红（实测
  `BLOCKED:HARNESS_DEFECT:KeyError`，正是 live pilot 的异常）。
- `HarnessDefect`：启动前（preflight 抛 `RuntimeError`）⇒ BLOCKED、未登记、run dir/lock 都不存在、
  `.driver` 有 traceback 文件与 blocked 行、随后同一 run id 仍能 ACCEPT，attempts=1；启动后
  （auditor 抛 `RuntimeError`）⇒ 登记 INVALID、run.json/registry/attempt 账本三处都有
  `HARNESS_DEFECT:RuntimeError`、traceback 标 `worker_launched=True`，再 invoke 同一 run id 被拒。
- `DeliveredHeadContract`：十个任务各做一次真实 `prepare`，`git -C repo rev-parse HEAD` 必须等于
  该任务渲染 CONTRACT 里的 `EXPECTED_HEAD`（且等于 `render_brief.delivered_head()`），合同含
  “中性 re-commit” 说明；原始 base 与 candidate sha 在 CONTRACT 与**run 目录下每个文件**的字节里
  都不出现；registry/base-manifest 仍持 base 身份。
- `SandboxConfinement.test_zsh_and_bash_heredocs_work_inside_the_launch_dir`：真实 sandbox + 冻结
  env 下 `zsh -c 'cat <<EOF … EOF'` 与 bash 等价式都在 launch dir 内成功，且 TMPDIR/TMPPREFIX
  都指向 launch dir 内（去掉 TMPPREFIX 时 zsh 实测仍是 `operation not permitted`）。
- `PreflightServicePort`：PATH 上的 stub `opencode` 记录 argv，断言顺序恰为
  `service set port <port>` → `debug paths` → `debug config` → `service stop` → `service status`
  （无第六条），`preflight.json` 的 `service` 与 `commands_run` 与之一致；stop 失败 + status 仍在
  运行 ⇒ FAIL、`SERVICE_STOP_FAILED:1` 被记录、`SERVICE_LEFT_RUNNING` 出现；master-profile 认证
  路径只跑两条 debug、不碰 service。
- 既有测试的如实适配（不削弱规则）：冻结 env 的允许集合新增 `TMPPREFIX` 并断言其位置；
  T1 receipt 断言改为「不再含 base_sha + driver manifest 的 base_sha 等于 registry」；
  collector 的 tampered-snapshot 断言改用新原因名。测试数 418 → 426。

### 重新测量与 re-pin

改了 `wrapper_delivery.py`，按既有规则**重测** delivery anchors（不手改 JSON）：命令同 README §2，
`--materials 4924930`；`DELIVERY_ANCHORS neutral per slot: {"CODEBUDDY": 0, "AGENTS": 0,
"WRAPPER": 10}`。与 T30 文件逐字段比较，**只有** `wrapper_program_sha256` 变化
（`24da46f…` → `f2dc995f…`），10 个 row、全部 PRE/POST 集合与 ran 计数逐字节相同。manifest 在
4924930 重建（51 个冻结文件），两份独立 literal（`EXPECTED_V2_HASHES` 与 `MANIFEST_SHA256`）
由程序同步重钉，`build_manifest.py check` PASS。

### T32 gates（前台逐条运行，退出码不经管道，PYTHONPATH 未设）

```text
=== RUFF                 All checks passed!
=== GOVERNANCE           35/35 checks passed
=== PUBLIC               VIOLATIONS=0
=== SCRIPTS_TESTS        Ran 602 tests in 25.944s / OK
=== EXPERIMENTS_TESTS    Ran 426 tests in 1048.401s / OK
=== NEVER_TOUCH          git diff --stat c40266f -- <NEVER TOUCH 路径> 为空
```
## T34（implementer: opencode deepseek-v4.1-flash）

分支 `experiment/v1.2-h2-freeze-v2-par`，基线 `b021b9b`。只改
`freeze-v2/**` 与本测试模块；T32（F22–F25）在另一分支并行开发，本票按
`CODEX_FIXES_9.md` 的 speed rule 只跑 ruff、两个 validator 与本测试模块，**不重钉 manifest、
不改任何 pinned literal**（重钉与全量 gate 在 T33）。

### 实现（对应 CODEX_FIXES_9 T34 1–7）

1. **`MAX_PARALLEL = 2`** 作为 `run_h2r2.py` 的模块常量，与程序一起被 freeze-manifest 哈希；
   没有 CLI 参数、没有环境变量可以覆盖它。
2. **资格规则**：`refusal()` 由"每个更早 run 都已登记"改为有界并发——(a) 未登记且未启动
   （原有锁/run dir 检查语义不变），(b) 同任务的另一臂若在 plan 中更早出现则必须已登记，
   (c) 本 runs root 中"活锁持有者"少于 `MAX_PARALLEL`，(d) plan 中每个更早的 run 都已登记
   或正在进行。拒绝原因显式为 `PREDECESSOR_NOT_STARTED:<id>`、
   `SAME_TASK_ARM_NOT_REGISTERED:<id>`、`PARALLEL_LIMIT:<n>`（`<n>` = 当前在进行的 run 数）。
   新增 `in_progress()`/`live_lock()`：只有"锁文件存在且 pid 存活且未登记"才算在进行，
   stale 锁仍是 `RUN_ALREADY_STARTED` 并交给既有 INTERRUPTED 规则。
   **词表变更的说明**：旧原因 `PREDECESSOR_NOT_REGISTERED` 被 T34 预注册的三条替换；
   `RunDriver.test_plan_order_and_every_second_start_are_refused` 中唯一那处断言随之改为
   `SAME_TASK_ARM_NOT_REGISTERED:h2r2-f01-c`（f01-v 之前的 f01-c 既是同任务另一臂也是第一个
   未启动 run，按 (b) 先命中）。该测试的其他断言（第二次启动被拒、stale 锁 ⇒
   INVALID:INTERRUPTED、`next` 前进）原样保留；没有任何规则被放宽。
3. **`run-plan --runs-root R`** 调度器：每个 run 以独立 `run` 子进程启动（stdout/stderr 落在
   `<runs_root>/.driver/<run_id>/scheduler-child-*.log`，`start_new_session=True`），循环
   取下一个 eligible run、等待、直到 plan COMPLETE。未登记的
   `BLOCKED:PROVIDER_UNREACHABLE` 在暂停后按 plan 位置重试，每次调度器调用对该 run 至多 3 次，
   用尽即停止并打印 `left`；已登记的 run 永不重跑。开始/结束行（`at`、`pid`、`run_id`、
   `outcome`、`reasons`、`returncode`）追加到 `<runs_root>/scheduler-v2.jsonl`。第二个调度器
   或操作员自己的 `run` 抢到同一 run id 时，子进程返回 `REFUSED:<reason>`，调度器记录后
   停止，不会产生第二个 worker。
4. **追加写入加锁**：`append_jsonl()` 用 `fcntl.flock(LOCK_EX)` 写整行并 flush；`register()`
   改为经由它写 registry，attempts 账本与 reachability 日志走同一路径。读取侧新增
   `read_text_locked()`（`LOCK_SH`），`read_registry()`/`next_attempt_number()` 使用它，
   读者不会读到半行。run 锁的获取/注释语义（`acquire_lock`/`annotate_lock`）未改。
5. **共享端口**：新增 `free_port()`（bind 127.0.0.1:0 后立刻释放）、`port_collision()`、
   `takes_port()` 与 `attest()`。preflight 调用改经 `attest()`：每个 run 选一个新端口；
   若 attester 接受 `port` 关键字则把该端口交给它；失败且原因是端口被占用
   （`ALREADY_IN_USE` / `PORT_IN_USE` / `SERVICE_PORT_IN_USE`，不区分大小写）时换新端口重试，
   至多 `SERVICE_PORT_ATTEMPTS = 3` 次，每次（attempt、port、verdict、reasons）写入
   `run.json` 的 `preflight.attempts` 与 preflight step 的 `attempts` 计数。不改 F22 的
   `service set port` 实现本身：**合并注记**——T32 分支的 `isolation_canary.preflight()` 目前
   在内部自选端口；合并时它需要接受 `port=` 关键字，`attest()` 才会把驱动选择的端口传进去
   （`takes_port()` 按签名探测，未合并前保持旧行为、只调用一次）。其余共享临时资源：本次
   改动没有新增共享 temp 路径（每 run 的 TMPDIR 仍由 `sandbox_v2.home_env` 固定在 launch dir）。
6. **可观察性**：`run.json` 现在记录 `concurrent_with`（由 `overlap_ids()` 从 registry 的起止
   区间与活锁计算，两侧对称）——`settle`/`terminate`/attempts 耗尽路径与 registry 步骤都会写；
   `status()` 把活锁持有的 run 标为 `IN_PROGRESS` 并输出 `in_progress`、`max_parallel`；
   `aggregate_runs.aggregate()` 新增 `overlap_pairs`（由 registry 自身时间戳推导）。
7. **文档**：protocol-v2 §5 的"串行"段落改写为有界并发规则、三条拒绝原因、scheduler 日志、
   `concurrent_with`/overlap 与端口规则，并写明理由（wall clock；隔离使跨 run 影响不可能；
   并发对必为不同任务、两臂在 plan 中交替 ⇒ 共享 provider 负载对臂对称）与
   "在第一次计数 run 之前固定（2026-10-23）"；§6 增加调度器只重试未登记
   `PROVIDER_UNREACHABLE`、已登记永不重跑、调度器被杀后仍归 INTERRUPTED 规则。README §5
   增加同名段落（`run-plan` 用法、规则、日志、flock、端口、理由）。§3 的 DISCLOSED CONFOUND
   块未改（测试逐字节比对 README 与 protocol）。

### 测试（全部 stub worker / 子进程桩 / StubSandbox / StubAuth，无模型、无真实凭据）

新增 `BoundedConcurrency` 10 项：`MAX_PARALLEL` 与三条拒绝原因（含 `execute` 对非 eligible id
的 REFUSED + `PARALLEL_LIMIT:2`）；调度器 20 个真子进程的 plan 顺序、任意时刻 ≤2 个存活、
重叠对必为不同任务、同任务第二臂晚于第一臂结束、`scheduler-v2.jsonl` 每 run 一 start 一 end、
再次调用 COMPLETE 且零启动；`PROVIDER_UNREACHABLE` 一次后重试并在原 plan 位置继续（日志
`NOT_REGISTERED:BLOCKED` → `ACCEPT`）；连续三次后 STOPPED + `left` 全量；调度器被杀后残留锁
由既有规则登记 `INVALID:INTERRUPTED / SECOND_START_ATTEMPT_REFUSED`；6 进程 × 20 行并发追加
全部可解析且无重复（`fcntl.flock`）；`status` 的 `IN_PROGRESS`；`overlap_ids` 两侧对称 +
`aggregate_runs.overlap_pairs` + `run.json.concurrent_with`；preflight 端口重试（3 次上限、
端口逐个更换、不接受 `port` 的 attester 只调用一次、`run.json.preflight.attempts`）；
`run-plan --help` 只暴露 `--runs-root`。既有 `RunDriver` 全部保留（仅上述一处原因词表断言更新）。

### T34 gates（前台逐条运行，PYTHONPATH 未设，退出码不经管道）

```text
=== RUFF                 All checks passed!                      (exit 0)
=== GOVERNANCE           35/35 checks passed                     (exit 0)
=== PUBLIC               VIOLATIONS=0                            (exit 0)
=== FREEZE_V2_TESTS      Ran 119 tests in 405.143s / FAILED (failures=2)
```

两项失败**只因被改动冻结文件的 pinned hash 变动**（未重钉、未改 literal，T33 统一重钉）：

```text
FreezeManifest.test_two_independent_anchors_and_materials_binding
FreezeManifest.test_one_byte_mutation_of_every_frozen_file_is_rejected
```

两者都在 `freeze_is_intact()` 的首个断言处失败；原因仅是 `run_h2r2.py`、`aggregate_runs.py`
与 `protocol-v2.md` 的字节相对 `EXPECTED_V2_HASHES` / `freeze-manifest.json` 已移动。除这两项
外 117/117 通过。本票未跑 `scripts/tests`、未跑完整 experiments 套件（speed rule），也未执行
任何 H2-R2 run。

## T35（implementer: opencode deepseek-v4.1-flash）

分支 `experiment/v1.2-h2-freeze-v2-par`，基线 `96fe60e`（T34 已在本分支提交）。只改
`freeze-v2/**` 与本测试模块；T32（F22–F25）在另一分支并行开发，本票只动 `run_h2r2.py` 的常量 /
调度器 / 模型校验三处小 hunk，未触碰 `isolation_canary.py`、`sandbox_v2.py`、`aggregate_runs.py`。
按 `CODEX_FIXES_9.md` T35 的 speed rule 只跑 ruff、两个 validator 与本测试模块，**不重钉 manifest、
不改任何 pinned literal**（重钉与全量 gate 在 T33）。

### 实现（对应 CODEX_FIXES_9 T35 1–3）

1. **`MAX_PARALLEL = 4`**（T34 的 2 改为 4，仍与程序一起被 manifest 哈希，无 CLI 参数可覆盖）。
   资格规则一字未改：按 plan 顺序开始、同任务第二臂等第一臂登记、活锁持有者计数、每个更早的 run
   已登记或在进行；三条拒绝原因与 `PARALLEL_LIMIT:<n>` 的值域不变（`<n>` 仍为当前活锁数）。
2. **退避重排**：`SCHEDULER_BACKOFF_FIRST_SECONDS = 60`、`SCHEDULER_BACKOFF_CAP_SECONDS = 900`、
   `SCHEDULER_BACKOFF_JITTER = 0.10`、`SCHEDULER_REQUEUES = 6`。`backoff_delay(n, jitter)` 的
   名义序列为 60/120/240/480/900/900（上限对含抖动的等待生效）；`scheduler_jitter()` 给对称的
   ±10% 分数。`child_outcome()` 的键由 `unreachable` 改为 `retryable`：只有**未登记**且原因为
   `PROVIDER_UNREACHABLE*` / `PROVIDER_FAILED_BEFORE_WORK*` 的 BLOCKED 可重排。每次重排写
   `{"event":"wait","run_id","requeue":n,"seconds","at"}` 到 `<runs_root>/scheduler-v2.jsonl`，
   并把 deadline 放进 `retry_after`；等待期间该 run 不占 slot（其他已启动的 run 继续持有），
   预算用尽（第 7 次 block）即 `STOPPED`、`stopped_by = BLOCKED_BEFORE_WORK:<id>` 并返回 `left`。
   T34 的 `pause` / `SCHEDULER_PAUSE_SECONDS` / `SCHEDULER_UNREACHABLE_RETRIES` 被退避预算取代；
   `schedule()` 新增仅测试可注入的 `backoff` / `jitter` / `clock`（CLI 仍只有 `--runs-root`）。
   **读法注记（冲突处置）**：T35 把"三次 before-work 失败"也列为"在工作之前结束"，但 §6.1 规定这三
   个 attempt 用尽后该 run **登记**为 BLOCKED，而 T35 同一句又写 "nothing registered is ever
   re-run"。两者冲突时**登记优先**：调度器只重排未登记的 before-work BLOCKED；已登记的
   `PROVIDER_FAILED_BEFORE_WORK` 行是终局，调度器不重跑、不改写，留给操作员裁决（§6.1 原本的
   "由操作员后续裁定"）。`test_a_registered_before_work_block_is_never_requeued` 正面固定该读法；
   既有 `test_three_before_work_failures_block_the_run_and_stop_retrying` 与 §6.1 的登记语义未改。
3. **冻结模型规则**：模块常量 `FROZEN_MODEL = "opencode-go/deepseek-v4.1-flash"` 与
   `frozen_model(planned)`；plan 的模型集合不等于 `{FROZEN_MODEL}`（第二模型、缺模型、None）时抛
   `ValueError("MODEL_NOT_FROZEN:<found>")`。`execute()` 在分配 run dir 之前、`schedule()` 在 spawn
   任何子进程之前都调用它；worker 与 auditor 的 argv 都取 `plan_run["model"]`，因此只能携带这个
   模型，实验内不存在 failover 分支。provider 中断只走 reachability / before-work / 退避。
   protocol-v2 §6.1 新增 MODEL RULE 文本块（任何计数 run 之前固定、对结果盲；两臂模型不同的配对
   不构成比较，model tier 不符即 INVALID），README §5 的并发段落改写为四路 + 退避 + 冻结模型；
   protocol §5 的 `MAX_PARALLEL = 2`、理由段落与 §6 的 scheduler 段落同步改为 4 与退避语义，并注明
   2→4 发生在任一计数 run 之前。§3 的 DISCLOSED CONFOUND 块未改（逐字节比对测试仍绿）。

### 测试（全部 stub worker / 子进程桩 / StubSandbox / StubAuth，无模型、无真实凭据）

`BoundedConcurrency` 由 10 项变为 15 项，**无删除**，既有断言未放宽：

- `test_max_parallel_is_frozen_four_and_the_three_refusals_are_explicit`：4 与三条拒绝；四条活锁
  时 `PARALLEL_LIMIT:4`，`execute` 对非 eligible id 返回 REFUSED 且不建 run dir。
- `test_the_scheduler_keeps_four_alive_and_starts_in_plan_order`：20 个真子进程，plan 顺序、
  任意时刻 ≤ 4 个存活（两种口径：已有 end 行的区间与尚未结束的集合）、重叠对必为不同任务、同任务
  第二臂晚于第一臂结束、scheduler-v2.jsonl 每 run 一 start 一 end、再次调用 COMPLETE 且零启动。
- `test_a_reachability_blocked_run_is_retried_in_plan_position_and_frees_its_slot`：一次 block 后
  记一条 60 s 的 wait，再在原位置重试并继续。
- `test_the_backoff_is_exponential_capped_and_jittered`：常量、60/120/240/480/900/900、抖动对称且
  不越过上限。
- `test_a_blocked_before_work_run_is_requeued_with_growing_waits_then_runs`：连续两次 block 后成功，
  日志 waits = [60, 120]（requeue 1、2），随后 f01-v 才启动（plan 位置保留）。
- `test_the_scheduler_stops_at_the_requeue_budget_and_lists_the_run`：7 次启动（6 次重排）后
  `STOPPED` / `BLOCKED_BEFORE_WORK:h2r2-f01-c`，waits = 60/120/240/480/900/900，`left` 为整份 plan，
  registry 为空。
- `test_a_registered_before_work_block_is_never_requeued`：预置 registry 的 before-work BLOCKED 行，
  调度器 COMPLETE 且从不 spawn 该 id。
- `test_one_frozen_model_with_no_failover`：常量与 plan 一致；第二模型 / None 触发
  `MODEL_NOT_FROZEN`；带第二模型的 plan 让 `execute` 与 `schedule` 都在任何进程 / registry 行之前失败。
- `test_every_worker_and_auditor_launch_carries_the_frozen_model`：一次真实 `execute`（stub worker +
  真 `run_audit_v2.audit`，只把 `driver.launch` 换成记录器）捕获 worker 与 auditor 两条 argv，
  都以 `FROZEN_MODEL` 为 `-m` 的值且命令前缀相同。
- 其余 6 项（killed scheduler、并发追加、status IN_PROGRESS、overlap/aggregate、preflight 端口、
  `run-plan --help`）保留，只把已删除的 `pause=` 参数换成注入的 fake clock。

`FakeClock`（测试辅助）让 60/120/… 的等待在假单调时钟上瞬间到期，记录下来的秒数仍是真实等待值。

### T35 gates（前台运行，PYTHONPATH 未设，退出码不经管道）

```text
=== RUFF                 All checks passed!                      (exit 0)
=== GOVERNANCE           35/35 checks passed                     (exit 0)
=== PUBLIC               VIOLATIONS=0                            (exit 0)
=== FREEZE_V2_TESTS      Ran 124 tests in 462.321s / FAILED (failures=2)   (exit 1)
```

两项失败**只因被改动冻结文件的 pinned hash 变动**（未重钉、未改 literal，T33 统一重钉）：

```text
FreezeManifest.test_two_independent_anchors_and_materials_binding
FreezeManifest.test_one_byte_mutation_of_every_frozen_file_is_rejected
```

两者都在 `freeze_is_intact()` 的首个断言处失败；原因仅是 `run_h2r2.py` 与 `protocol-v2.md` 的字节
相对 `EXPECTED_V2_HASHES` / `freeze-manifest.json` 已移动（README 与 CODEX_REPORT 不在 byte freeze
内）。除这两项外 122/122 通过。本票未跑 `scripts/tests`、未跑完整 experiments 套件（speed rule），
也未执行任何 H2-R2 run、未调用任何模型、未触碰 `~/.h2-worker-profile`。

### 本轮未做、未证明与遗留缺口

- manifest 未重钉（T33）；上面两项按 speed rule 记为预期失败，而不是 PASS。
- 四路并发与退避只在 stub 子进程 / fake clock 上证明；真实 provider 中断下的 wall-clock 行为
  未观测（本票不执行任何 run）。
- T35 第 2 条与 §6.1 的"登记后不重跑"冲突按"登记优先"处置（上文），需 Claude 接受该读法。
- `PROVIDER_FAILED_BEFORE_WORK` 前缀留在可重排集合中属防御性写法：当前 `execute()` 在该形状下
  必然登记，故实际只可能是 `PROVIDER_UNREACHABLE` 触发重排。

