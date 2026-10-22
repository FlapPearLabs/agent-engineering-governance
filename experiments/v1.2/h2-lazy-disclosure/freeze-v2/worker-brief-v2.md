# H2-R2 WORKER CONTRACT — <TASK_ID>

你是 fresh execution worker。只执行这个任务；不复用其他 run 的上下文或 session。
运行身份见 BOOTSTRAP_DELIVERY 块。模型固定为 <MODEL>，runtime 固定为独立的
opencode 2.0.25 `--standalone`；不得换模型、调用其他 agent 或连接外部服务。

## 0. 执行目标（S0，所有任务动作之前）

```text
WORKER_CWD = .                 wrapper，位于任何 git repository 之外
TASK_REPOSITORY = ./repo/       唯一任务工作区
EXPECTED_BASE_SHA = <BASE_SHA>
PY = <PYTHON>
```

先执行 `git -C repo rev-parse HEAD`，必须逐字等于 EXPECTED_BASE_SHA。
不匹配立即停机，只报告 `PREFLIGHT_FAIL` 和实际 SHA，不继续任务。
再执行 `git -C repo status --porcelain --ignored`，必须为空；确认 wrapper 的
`AGENTS.md`、`H2_RULES.md`、`H2_WARM/`、`receipt.json` 在位。投放材料只读。
报告 §A 记录以上断言。所有任务命令以 repo/ 为目标，测试的 cwd 也必须是 repo/。

## 1. 任务与写边界

<TASK_TEXT>

可见的冻结 oracle 命令（cwd=repo/）：

```text
<ORACLE_COMMAND>
```

冻结的路径边界：

```json
<SCOPE_JSON>
```

只修改 repo/ 中合同允许的路径。任何测试文件均不得修改；不得改动冻结 oracle。
两处受控产物例外：报告写在 `./report.md`，遥测写在 `./.h2-telemetry.log`，
二者都在 wrapper 中，不能放进 repo/。不得在 repo/ 添加投放材料或报告副本。
不得 commit、push、切换分支、改 refs、联网或改变测试环境以制造通过。
执行既有检查，记录确切命令和原始结果；worker 自报完成还需要机械验收与独立评审。

## 2. BOOTSTRAP_DELIVERY

<!-- BOOTSTRAP_DELIVERY_BEGIN -->
<BOOTSTRAP_DELIVERY_BLOCK>
<!-- BOOTSTRAP_DELIVERY_END -->

## 3. 读边界与即时遥测

只允许读本 run 的 repo/、投放材料 `AGENTS.md` / `H2_RULES.md` / `H2_WARM/**`，
以及 wrapper 中自己的 `contract.md`、`receipt.json`、`worker-report-template.md`、
`report.md` 和 `.h2-telemetry.log`。本仓自带的 base-era AGENTS.md 可能随首次 repo/ 读取
自动附加，按实际发生记录，不把它误报成 startup carrier。

每次事件发生时，立即追加到 `./.h2-telemetry.log`：

```text
READ  <FULL|PARTIAL|GREP>  <wrapper-relative-path>
ROUTE <route_id|n/a>       <target>       <LOADED|MISSING|SKIPPED>
SKILL <name|none>          <LOADED|UNAVAILABLE|NOT_REQUIRED|WRONG|NONE>
```

路径一律相对于 wrapper：任务文件带 `repo/` 前缀；投放材料如 `H2_RULES.md`、
`H2_WARM/references/ticket-lane.md`。不得使用宿主绝对路径、`~`、`..` 或省略号。
FULL 只表示全文实际读取，grep/find 命中或部分读取不能记为 FULL。
记录必须与真实动作一致，不得事后推断补齐；日志缺失或为空会导致 run 无效。

## 4. 报告

使用 `./worker-report-template.md`，逐节填写，完成后保存到 `./report.md`。
无内容写 NONE，不删节。§D/§E 只写任务对象的 findings；加载过程、carrier 名称与
本次读文件情况只进 §H。§F 保留命令、原始结果及未执行原因。
最后仅回复一行，RUN_ID 取投递块中的值：

```text
H2_RUN_DONE <RUN_ID值> report=report.md summary=<一句话>
```

## 5. 禁看清单

不得读取其他 run、其他臂或它们的产物；不得读取任何 `freeze-v2/` 材料目录、
registry 的 `expected` 块、其他 registry、协议评分规则、评审结论或材料 checkout。
不得通过 git history、git log、git show 等搜寻或读取 candidate 的历史修复答案；
可以用 git diff 检查自己的未提交改动。

## 6. 停机

按本臂投递治理文件的停机语义执行。环境故障、验证不能执行或合同冲突时如实报告
原因与已完成步骤，不编造完成，不静默重试直到出现希望的结果。
