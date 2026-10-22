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

