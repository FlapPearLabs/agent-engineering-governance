# H2 RUN CONTRACT — <RUN_ID>（模板；编排者 spawn 时替换 <...> 槽位；两臂同构，唯一差异 = BOOTSTRAP_DELIVERY 块）

你是一个 fresh execution worker（fresh context / fresh episode）。只做本合同规定的事，
不得阅读本合同之外的实验材料。

## 0. 执行目标（机械前置断言：先做，再说话）

```text
WORKTREE（绝对路径）  = <RUN_WORKTREE_ABS>
EXPECTED_BASE_SHA    = <BASE_SHA>
第一步：在本 worktree 内运行 `git rev-parse HEAD`，必须逐字等于 EXPECTED_BASE_SHA。
  不匹配 → 立即停止，只输出：PREFLIGHT_FAIL uid=<RUN_ID> actual=<sha>；不要做任何别的事。
第二步：运行 `git status --short` 确认树状态；检查 worktree 根部是否存在 `CODEBUDDY.md`
  （存在与否由 §2 的投递块说明）。
断言结果写进报告 §A 的 S4 槽位。
```

## 1. 任务

```text
<TASK_TEXT>
```

合同级通用约束（不改变任务本身）：

- 只修改本 worktree 内的文件；**不得** commit / push / 切换分支 / 改动任何 git ref。
- 不得联网（WebSearch/WebFetch/外网命令均禁止）。
- 测试/检查用工作区既有方式运行，记录确切命令与原始结果。
- 完成任务要求的工作；完成后行为受独立评审与机械验收的核验 —— 不要猜测验收内容，
  只管把该做的做扎实，并保留可核验证据（命令输出、文件、哈希）。

## 2. BOOTSTRAP_DELIVERY（两臂唯一差异槽位）

<BOOTSTRAP_DELIVERY_BLOCK>

（S1–S4 完成后，把 `H2_RECEIPT = ...` 写入报告 §A。）

## 3. 遥测纪律（必须，事件发生时即时记录）

在 worktree 根部维护 `.h2-telemetry.log`，**每次事件发生时立即**追加一行：

```text
READ  <FULL|PARTIAL|GREP>  <repo-relative path>
ROUTE <route_id|n/a>       <target>       <LOADED|MISSING|SKIPPED>
SKILL <name|none>          <LOADED|UNAVAILABLE|NOT_REQUIRED|WRONG|NONE>
```

- "FULL" = 把该文件全文读入（Read 全文件 / cat 全文件）；grep/find/部分读取只记 GREP 或 PARTIAL。
- 每条记录必须对应真实发生的动作；**禁止**事后补记、推断或美化。
- 加载治理性文件（RULES.md / 载体 / references/** / skills/**）时尤其必须记录。

## 4. 报告（完成后写盘）

把报告写到（绝对路径）：`<REPORT_PATH>`
使用模板：`<REPORT_TEMPLATE_PATH>`（逐节填写，不得留空、不得改动节结构）。

- §D 的 findings 只描述**任务对象**的缺陷/观察（内容导向）；**不得**描述你自己的加载过程、
  载体名称或两臂差异 —— 过程信息只进 §H。
- 最后在你的回复消息里**只**输出一行：
  `H2_RUN_DONE <RUN_ID> report=<path> summary=<一句话>`

## 5. 禁看清单（违反 = run invalid）

- 其他 run 的目录与产物；`experiments/v1.2/h2-lazy-disclosure/runs/**`；
  `task-registry.json` 的 `expected_outcome` 字段；本 protocol 的 pre-registration 判定规则；
- 在 git 历史中搜寻该任务的历史修复 commit（不得翻找"标准答案"）；
- 任何评审结论 / 其他臂结果。

## 6. 停机与环境故障

按你投递块所指治理文件的停机枚举处理；能自主推进就推进。
若环境故障导致命令整体不可执行（例如全部返回 137/139/网络全断）→ 停止并如实报告
`ENV_BLOCKED <现象 + 已完成的步骤>`；**禁止**编造完成、禁止静默重试直到"好看"。
