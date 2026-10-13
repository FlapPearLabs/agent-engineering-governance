# H2 RUN CONTRACT — <RUN_ID>（模板；编排者 spawn 时替换 <...> 槽位；两臂同构，唯一差异 = BOOTSTRAP_DELIVERY 块）

你是一个 fresh execution worker（fresh context / fresh episode）。只做本合同规定的事，
不得阅读本合同之外的实验材料。

## 0. 执行目标（S0：机械前置断言 —— 所有动作之前先做这步）

```text
WORKTREE（绝对路径）  = <RUN_WORKTREE_ABS>
EXPECTED_BASE_SHA    = <BASE_SHA>
MODEL_TIER           = <MODEL_TIER>（全部 run 冻结为同一档；不得更换，更换即 run invalid）
S0 第一步：在本 worktree 内运行 `git rev-parse HEAD`，必须逐字等于 EXPECTED_BASE_SHA。
  不匹配 → 立即停止，只输出：PREFLIGHT_FAIL uid=<RUN_ID> actual=<sha>；不要做任何别的事。
第二步：运行 `git status --short` 确认树状态；确认 harness 投放材料在位
  （`H2_RULES.md` 与 `CODEBUDDY.md` 必在、`H2_WARM/` 目录必在；本臂投递块说明用途）。
  投放材料是**只读材料**：不得修改、删除或重命名。
断言结果写进报告 §A 的 S0 槽位。
```

## 1. 任务

```text
<TASK_TEXT>
```

合同级通用约束（不改变任务本身）：

- 只修改本 worktree 内的文件；**例外（受控产物）**：报告必须写到合同 §4 指定的
  `REPORT_PATH`，遥测日志必须写在 worktree 根部 `.h2-telemetry.log` —— 这两处是允许的
  写目标，除此以外不得写 worktree 之外的任何路径。
- **读边界（与 §3 遥测校验同一套规则，必须知悉）**：只允许读取
  ① 本 worktree 内（含 harness 投放的 `CODEBUDDY.md` / `H2_RULES.md` / `H2_WARM/**`）；
  ② 你自己这个 run 的 evidence 目录里的合同与报告模板副本。
  **不得**读取 materials 树（本 run 合同与报告模板的原始出处已**复制**到你的 evidence
  目录，路径见 §4）、其他 run 的任何目录、任何未被路由到你的治理材料。
- **不得** commit / push / 切换分支 / 改动任何 git ref。
- 不得联网（WebSearch/WebFetch/外网命令均禁止）。
- 测试/检查用工作区既有方式运行，记录确切命令与原始结果。
- 完成任务要求的工作；完成后行为受独立评审与机械验收的核验 —— 不要猜测验收内容，
  只管把该做的做扎实，并保留可核验证据（命令输出、文件、哈希）。

## 2. BOOTSTRAP_DELIVERY（两臂唯一差异槽位）

<BOOTSTRAP_DELIVERY_BLOCK>

（S0–S4 完成后，把 `H2_RECEIPT = ...` 写入报告 §A。）

## 3. 遥测纪律（必须，事件发生时即时记录）

在 worktree 根部维护 `.h2-telemetry.log`，**每次事件发生时立即**追加一行：

```text
READ  <FULL|PARTIAL|GREP>  <path>
ROUTE <route_id|n/a>       <target>       <LOADED|MISSING|SKIPPED>
SKILL <name|none>          <LOADED|UNAVAILABLE|NOT_REQUIRED|WRONG|NONE>
```

- 路径基准（**唯一确定**，机器可校验，**且不得含宿主绝对路径**）：
  - worktree 内的文件写 **repo-relative 路径**（如 `CODEBUDDY.md`、`scripts/tests/x.py`）；
  - 你 evidence 目录内的文件写**稳定命名空间**：`RUN_EVIDENCE/<文件名>`
    （如 `RUN_EVIDENCE/contract.md`、`RUN_EVIDENCE/worker-report-template.md`）。
  - **绝对路径一律不合格**：遥测日志会被收集进 run 记录并发布，写入真实宿主路径违反本仓
    公开数据政策；且旧校验里 `os.path.join(worktree, "/abs")` 会丢弃 worktree 前缀，使绝对
    路径可绕过边界 —— 现已直接拒绝该形式。
- **禁止缩写**：不得出现 `...` / `~` / 相对猜测。缩放只允许出现在给人看的展示层，
  机器可读事件里必须是可解析的确定路径。含 `...` 的事件会被判为不合格。
- evidence 命名空间**只接受** `contract.md` / `worker-report-template.md` / `report.md`
  三个文件名；`receipt.json`、`task.txt` 等不在允许面内。
- "FULL" = 把该文件全文读入（Read 全文件 / cat 全文件）；grep/find/部分读取只记 GREP 或 PARTIAL。
- 每条记录必须对应真实发生的动作；**禁止**事后补记、推断或美化。
- 加载治理性文件（`H2_RULES.md` / `CODEBUDDY.md` / `H2_WARM/**` 等投放材料）时尤其必须记录。

## 4. 报告（完成后写盘）

把报告写到（绝对路径，属 §1 的受控产物例外）：`<REPORT_PATH>`
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
