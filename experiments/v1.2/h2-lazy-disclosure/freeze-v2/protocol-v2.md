# H2-R2 Freeze v2 protocol — candidate authority, execution pending

本协议定义新的十任务、二十 run 实验材料。它不改写旧轮次记录，不授权 promotion，
不表示已经执行 H2-R2。字节冻结见 freeze-manifest.json；正式接受与合并仍须独立评审。
旧协议的判定边界和流程以 [protocol.md](../protocol.md)、[scoring-rubric.md](../scoring-rubric.md)
为来源；以下明确列出 v2 的适配与偏离，未列出的评分边界保持原义。

## 1. 准入的唯一时点（FZ2_1）

Eligibility validator 2.8.12 是 PRE-FREEZE MECHANICAL GATE。任务身份来自已测量的
admission 分类、ledgers 和 shortlist，再由本轮 task-registry-v2.json 承载冻结准入。
流程为 candidate task → eligibility validation → admitted corpus → Freeze v2。
每个 run 消费这个已冻结决定，不在 worker runtime 重新决定 eligibility。

Finding-1 的 acceptance 必须观察目标谓词 / discriminator 义务已由 validator 的复算
机制承载，不降级为纯文档说明或延迟给人工评审。其执行边界与显式未强制项见
[Schema v2](../eligibility-schema-v2.md) §3.1、§6.6–§6.8。这里不扩大 validator 对未知
worker delta 的安全保证；worker 的成果走第 5 节验收。

## 2. 类语义与任务身份（FZ2_2、FZ2_4）

引用 Schema v2：A_REPAIR 是 frozen attributable FAIL→PASS；B_REGRESSION_GUARD 是
PASS→controlled mutation FAIL。本轮十个任务全部为 A_REPAIR，oracle 在 base B' 与
历史 candidate 的 blob 相同，标为 FRAMEWORK_FROZEN。base 的失败是待修复信号。
交付必须对这些失败中性；不把交付新增的失败归入任务原有失败。

t02 = NOT_ADMITTED_CURRENT_REVISION（FZ2_4）。它不在本轮注册表中，不为凑样本救活；
将来若采用不同 oracle / scope，必须是新任务身份、新 revision 和新的 measurement / freeze。
旧 task-registry、旧 run plan 与旧结果保持历史原状。

## 3. 聚合集合与分母（FZ2_3）

唯一机械 owner 是 [aggregate_set.py](aggregate_set.py)：

```text
aggregate_set = derive(records where REQUEST_VALID AND admitted_by_freeze)
admitted_by_freeze = case identity membership in task-registry-v2.json
```

输入是 admission/batch-1..4/classification.json 的冻结 eligibility records。实现按
corpus_case_id 与注册表 case_id 相交；重复身份拒绝。没有另一个手维护的 aggregate flag。
所有任务数、计划 run 数、各臂分母和结果统计都从该集合出发。运行后统计只在此集合上
连接有效 run；有效性过滤不回写任务 eligibility。无效和 blocked 记录仍全部保留在原始登记中。
当前生成结果应覆盖全部十个注册任务，每任务每臂一条；任何缺口必须暴露，不能补造计数。

## 4. Runtime、交付与已披露混杂

采用 README §3 决定的 opencode 2.0.25：每次 confined launch 先在 sandbox 内起
`opencode serve --hostname 127.0.0.1 --port <P>`，再以
`opencode run --server http://127.0.0.1:<P> ...` 连接它（F26，见 §4.0），模型固定为
`opencode-go/deepseek-v4.1-flash`，隔离 profile 为 `~/.h2-worker-profile`。
HOME/XDG 隔离、无用户插件/MCP/Skills/全局指令、关闭自动更新的实际状态必须由操作员的
已登录 profile canary 再核验；合成 parser 测试不能替代该 live 证据。

run root 是 `H2_RUNS_ROOT = <SHARED_RUN_ROOT>`：macOS Shared 目录下的操作员目录，位于所有
home 之外，且祖先目录不得含 `.agents`、`.opencode`、`.claude`、`AGENTS.md`、`CLAUDE.md`
或 `opencode.json`（run 自己投放的 AGENTS.md 除外）。`wrapper_delivery.py prepare` 与
`isolation_canary.py prepare` 都拒绝 home 之下的 run root 与带上述祖先的 run root。
原因见 F4：opencode 从 cwd 向上发现 `.agents/` 与 `.opencode/`，可越过被重定向的 HOME，
把操作员的技能目录重新引入 worker。位于 Shared 目录的 run root 只出现两个内置 skill
`opencode` 与 `report`，两臂完全相同；这是已披露的、臂对称的运行时事实，不是交付差异。

profile 配置本身是冻结输入（F6）。[worker-profile/opencode.json](worker-profile/opencode.json)
是唯一模板：`$schema`、关闭自动更新、`share: "disabled"`、空的 `plugin` 与 `mcp`，以及
`permission.question = "deny"`。理由：隔离 profile 的解析结果里 `build` agent 允许
`question` 动作，而 `opencode run` 是非交互的——worker 一旦调用该工具就无输出地永久等待，
这也是此前四次评审 run 无声卡死的原因。操作员必须在首次 run 之前把模板原样安装为 profile 的
`~/.config/opencode/opencode.json`（逐字节，不重新格式化）。每次 run 之前必须执行
`isolation_canary.py preflight <run_dir> --profile-env <env.sh>`：它只调用
`opencode debug paths` 与 `opencode debug config`（不 run、不调模型），把裁定写入
`<run_dir>/preflight.json`，并要求打印出的 status 路径都在 profile home 之下、配置来源恰好是
profile 的 `opencode.json` 与 profile 配置目录、且该文件字节等于冻结模板。preflight 不 PASS
则不得开始该 run，`preflight.json` 留在 run dir 作为证据。

单 run 的 wall-clock 上限是 90 分钟。超时按第 6 节登记为 INVALID（RUN_ID、ARM、TASK_ID、
原因、发现时间、artifact 位置），不静默重跑，也不把超时当作 worker 失败或通过。

worker 结束后、机械验收之前，access audit 从 `events.jsonl` 复算访问面：每个 tool call 的
路径参数与 shell 命令中的路径 token 都必须解析到 run 目录之内，冻结的系统白名单（固定 PY
及其 prefix、/usr、/bin、/opt/homebrew、/System、/Library/Developer、OS temp 根、/dev/null）
除外；试图触达其他仓库的 shell `git` 调用与白名单外的工具同样计为命中。任一命中使该 run
为 INVALID:OUT_OF_RUN_ACCESS，按第 6 节登记且不再重跑，audit verdict 逐条保留命中原文。

shell 工具在本 runtime 中名为 `shell`（`bash` 一并接受），命令按 shell 标点切分为 token 后
再解析路径；`git` 的判定对象是它在同一命令中的**有效仓库**——先应用同一命令内的 `cd`，再应用
该 git 调用自己的 `-C` / `--git-dir` / `--work-tree`——只有解析到 run 目录与 OS temp 根之外时
才算 `GIT_FOREIGN_REPOSITORY`。理由：把 base 归档到 temp 目录并在其中运行 git 与测试是合法
工作，而同一管道中其他程序的 `-C`（如 `tar -x -C`）不是 git 的。

### 4.0 OS 隔离、fresh home 与 driver-held 流（F16/F17/F19/F21，T29）

静态审计不可能完备（F16）：`cat $(printf ...)`、反引号、base64/xxd 解码、xargs 与 `-c` 程序
都能隐藏一个路径。因此 sandbox 成为实际执行屏障，access audit 仍是静态证据层：

```text
F16  CONFINEMENT  每次 launch（worker、per-auditor、以及每次 reachability 检查）都以
       `sandbox-exec -f <rendered profile> <the frozen command>` 启动。渲染规则：launch 目录
       （worker 为 run dir，auditor 为 audit dir）与 per-launch home 可读写；解释器 prefix 只读；
       launch 目录的每个祖先目录以 `literal` 只读；/Users、/private/tmp、/private/var/folders
       之下其余内容对 file-read-data 与 file-write* 一律拒绝。冻结模板
       worker-sandbox.sb.template 在 manifest 中；渲染后的 profile 与 sha256 逐 attempt 归档。
       披露：祖先目录的 NAMES 仍可列举（`literal` 只放行目录节点本身），其内容不可读。
       访问审计保留全部既有规则与裁定，并新增证据字段 `unresolved_constructs`
       （command substitution / backtick / eval / `-c` 程序 / 解码器 / xargs）与
       `sandbox_denied`（tool result 含 "Operation not permitted" 且路径在 launch 目录之外）。
       预注册：被 sandbox 拒绝的动态访问没有获得任何东西，按 run 记录并在 closure report 中
       报告，不判 INVALID；静态命中仍判 INVALID（不放宽任何规则）。
F19  FRESH STATE 每次 launch 使用全新 `<runs_root>/.driver/<run_id>/home-<n>`（auditor 为
       `audit-home-<n>`，每次 reachability 为 `probe-home-<purpose>-<n>`），mode 0700，只含冻结的
       worker-profile/opencode.json 与自己的 XDG_* 目录。credential 以
       `opencode auth export --standalone opencode`（master profile env）管道进
       `opencode auth import --standalone`（fresh env）；secret 不进 argv、日志、events、
       registry 或 stdout。attempt 之后 `opencode auth logout`（best effort，记录结果）。
       master profile 从不挂载进 sandbox。
F17  DRIVER COPY 每次 launch 的 stdout/stderr 写入 `<runs_root>/.driver/<run_id>/` 之下（sandbox
       不可写）；before-work 规则、tool-call 计数、access audit 与遥测只读该副本，run dir 里的事后
       副本仅供人读。副本缺失或不可读 => INVALID:EVIDENCE_MISSING，不重试。
F21  TMPDIR      每次 launch 的 TMPDIR = `<launch dir>/.tmp`，随 launch 目录一起放行，不再落进
       共享 OS temp 目录。
F25  TMPPREFIX   worker、auditor 与每次 reachability 的冻结 env 在 TMPDIR 之外同时给出
       `TMPPREFIX=<launch dir>/.tmp/zsh`。理由：worker 的 shell 是 zsh，heredoc 的临时文件写在
       TMPPREFIX 下（默认 /tmp/zsh）而不是 TMPDIR，而 sandbox 拒绝 /private/tmp；live pilot 里
       `cat <<EOF ... EOF` 直接失败，worker 只能改用 write tool，同一常见 shell 用法在两臂都
       不可用。TMPPREFIX 是文件前缀，不需要创建目录。
F26  EGRESS     sandbox 只封闭文件系统，不封闭网络：pilot #5 在 sandbox 内 `curl https://github.com`
       返回 200，而公共治理仓的历史含全部候选修复，动态拼 URL 的 worker 可以取到答案而静态审计
       看不见。因此每次 confined launch（worker、per-auditor、每次 reachability）都由 driver 在
       sandbox 之外启动一个仅 CONNECT 的 HTTPS 代理（绑定 127.0.0.1 的空闲端口），allowlist 冻结
       为 `EGRESS_ALLOW = ("opencode.ai", "models.opencode.ai")` 且仅 443；非 CONNECT 请求返回
       403；每个请求以 (time, host, port, ALLOW/DENY) 追加到该 launch 的 driver stream 目录下
       `egress.jsonl`，launch 结束后停止。launch 布局：sandbox 内先
       `opencode serve --hostname 127.0.0.1 --port <P>`（P 每次 launch 空闲选取，撞车以新端口
       有界重试，同 F22），run 命令为
       `opencode run --server http://127.0.0.1:<P> --auto --format json -m <model> <prompt>`；
       每次 launch 一个随机 `OPENCODE_SERVER_PASSWORD`（server 与 client 同值，只经环境传递，
       绝不进 argv、记录、日志或事件流），HTTPS_PROXY/HTTP_PROXY（大小写两种）= 代理，
       NO_PROXY/no_proxy = 127.0.0.1,localhost；serve 进程随该 launch 的进程组一起终止。
       sandbox 模板新增网络规则（仅 proxy 端口与 P）。confinement 自检新增：直连外部主机
       （github.com:443）必须失败，经代理 CONNECT 非 allowlist 主机必须被拒（403 并记录）；
       否则 BLOCKED:SANDBOX_NOT_CONFINING。访问审计新增证据字段 `egress_denied`
       （egress.jsonl 的 DENY 行），与 `sandbox_denied` 一样按 run 报告、不改变裁定（没有数据
       穿过）。
F28  MKTEMP     macOS `mktemp -d` 不带模板时忽略 TMPDIR，改用 /var/folders 下的 per-user
       confstr 临时目录（sandbox 拒绝）。两臂同样受影响，worker 已自行适配。披露，不开放
       /var/folders。
SELF TEST 每次 launch 之前，driver 在同一 rendered sandbox 内用 `cat` 与 `<PY> -c open(...)` 读
       自己在 `.driver/<run_id>/` 下投放的文件，两者必须失败且不泄漏其 token，且在 launch 目录内
       写入必须成功；否则 BLOCKED:SANDBOX_NOT_CONFINING（不消耗 attempt、可再次 `run`、已记录）。
       平台无 sandbox-exec => BLOCKED:SANDBOX_UNAVAILABLE。preflight 针对 fresh home 运行。
```

worker 与 per-run auditor 的运行环境固定为：最小基础环境（PATH、LANG）、profile env 文件的
`export` 行、第 4.0 节的 fresh state（HOME、XDG_*、TMPDIR、TMPPREFIX），以及冻结的
`PYTHONDONTWRITEBYTECODE=1`；该变量最后应用，profile 不能覆盖。原因
（F11）：按合同执行 oracle 与完整脚本测试会正常在 `repo/` 下写出 `__pycache__/*.pyc`，而
`scripts/tests/` 前缀规则与 validator 的 BYTECODE 规则必须继续拒绝任何 `.pyc`——修的是原因，
不是规则；`repo/` 下若仍出现 `.pyc` 依然是 scope 拒绝。

worker cwd 是任何 git repository 之外的 wrapper。AGENTS.md、H2_RULES.md、H2_WARM/
从同一 materials commit 的 git objects 投放；repo/ 是 task base 的 STANDALONE 仓库：对象库只含
B' 的 tree（F18：单个无父提交，固定中性 message `h2 task base`、固定 author/committer/date，
HEAD detached 于该中性提交，其 tree 等于 B' 的 tree；B' 提交本身不被 fetch），无 remote、
无 alternates、无 reflog，`git log --all` 不含 B' 或 candidate 的 40-hex。因此
worker 无法从共享对象库读到历史 candidate，repository 形状本身由投放后置条件失败关闭核验。
control carrier 的字节为薄头 + 当前 AGENTS.md 全文 + 薄尾；variant 为已钉 hash 的 lean
carrier。报告、遥测、receipt 与报告模板都在 wrapper 中，repo/ 内不得出现任何投放副本。

```text
DISCLOSED CONFOUND  the task repository's own (base-era) AGENTS.md is attached to BOTH arms on
          the worker's first read inside repo/. Neither arm can be kept from it under this
          runtime. The arms therefore differ in the STARTUP carrier (full current-era HOT vs
          lean carrier + routed WARM), not in whether any full governance text is reachable.
          A null difference is reported as INSUFFICIENT_EVIDENCE, never as DISCLOSURE_SAFE on
          this ground alone.
```

T2 的 delivery-anchors.json 是完整 PRE/POST 测量，不取样：每个 shortlisted base 的
oracle 与 scripts/tests 全套，两个臂的 WRAPPER 均须中性，非通过 ID 集合相同且 ran_delta=0。
旧仓内布局的污染保留，不重命名为原有任务失败。receipt 绑定 base、materials、carrier、
rules、WARM bundle 与 wrapper_delivery.py 的 sha256。

materials_commit 定义为首次加入 freeze-manifest.json 的 T8 内容冻结提交的父提交，
T8 生成 manifest 前统一重生成 run plan。T9 只作说明和交接，不前移材料。最终默认分支
merge 是评审历史的外部锚，不改变已选定的 materials object snapshot。

## 5. 每个 run 的执行与验收

按 run-plan-v2.json **有界并发**准备和执行：`run_h2r2.py` 的 `run-plan --runs-root R` 调度器
让同一个 runs root 中同时最多 `MAX_PARALLEL = 4` 个 run 在运行（该常量与程序一起被
freeze-manifest 哈希，改动它是设计变更，不是参数）。run 仍按 plan 顺序**开始**：一个 run 可以
开始时，(a) 它未登记且未启动，(b) 同一任务的另一臂若在 plan 中更早出现则已登记（任务内
counterbalancing 顺序原样保留，因此同一任务的两臂永不重叠），(c) 本 runs root 中在进行的 run
（活锁持有者）少于 MAX_PARALLEL，(d) plan 中每个更早的 run 都已登记或正在进行；只有**完成**
可以重叠。拒绝原因保持显式：`PREDECESSOR_NOT_STARTED:<id>`、
`SAME_TASK_ARM_NOT_REGISTERED:<id>`、`PARALLEL_LIMIT:<n>`。调度器把每个 run 作为独立的 `run`
子进程启动，一个崩溃不会带走另一个；开始/结束（时间、pid、run id、结果）与每次等待（requeue
序号、秒数）追加到 `<runs_root>/scheduler-v2.jsonl`。每个 run.json 记录 `concurrent_with`
（执行区间重叠的 run id）与起止时间，`aggregate_runs.py` 报告 overlap pairs，`status` 把正在
进行的 run 标为 IN_PROGRESS。共享机器资源遵循同一规则：preflight 的 service port 每个 run 各自
选择（绑定后立即释放，紧接在 `service set port` 之前），端口撞车则以新端口重试、至多 3 次并全部
记录。一个在工作之前结束且未登记的 run 由调度器按第 6 节退避重排；二十个 run 的每次 worker 与
auditor 启动只用第 6.1 节冻结的单一模型。

理由（在第一次计数 run 之前固定，2026-10-23；T34 取 2，T35 在任一计数 run 之前改为 4）：单个
run 需要 10–90 分钟，严格串行会让二十个 run 耗掉大半个工作日；而并发的 run 之间没有相互影响的
通道——各有独立 run dir、fresh home、渲染后的 sandbox 与 driver 持有的流，sandbox 拒绝另一个
run 的内容，跨 run 唯一共享的是 provider 负载；并发的 run 必然是**不同任务**，且两臂顺序在 plan
中交替，因此该负载对臂对称。registry 与 attempts 文件以 `fcntl.flock` 独占追加，两个几乎同时
结束的 run 不会交错写行。

执行只有一条路径：`freeze-v2/run_h2r2.py`（`next` / `run <run_id>` / `status` / `run-plan`）是唯一允许启动
worker 的程序，launch prompt、worker 命令、server 命令、env allow-list（含冻结的
`PYTHONDONTWRITEBYTECODE=1`）、auditor 环境与 90 分钟上限是它的模块常量；
run_id 一旦启动过就不再启动第二次，被打断的记录为 INVALID 后计划才继续。worker 验收之后的
独立评审由 `freeze-v2/run_audit_v2.py` 在盲包上执行，机械与评审两个结论都进登记，取保守者。
每次新起 opencode 进程与 episode，不复用 session。f01 为 C,V，f02 为 V,C，依次交替。

第 4.0 节的隔离属于同一条执行路径：driver 为每次 launch 渲染并归档 profile、准备 fresh home、
在 sandbox 之外启动 allowlist 代理并在 sandbox 内启动 loopback server、做无模型的 confinement
自检，然后经 `sandbox-exec` 启动；worker 与 auditor 的 stdout/stderr
只以 driver 副本为准（F17），run dir 中的副本仅供人读。sandbox/credential/server/代理在 worker
未动作前不可用时不消耗 attempt、不登记，同一 run id 可再次 `run`；EVIDENCE_MISSING 是终局
INVALID，绝不因此重试。

fresh home 的 preflight 在同一条路径里完成（F22）：driver 为该 home 选一个空闲 127.0.0.1 端口，
先 `opencode service set port`，再执行两次 debug，然后 `opencode service stop`，最后用
`opencode service status` 复核，仍显示服务在运行 => 该 run 以 BLOCKED 登记、原因
`PREFLIGHT_FAIL:SERVICE_LEFT_RUNNING`（preflight 不 PASS 就不开始该 run，既有的 preflight 语义
不变）。端口与 set/stop/status 的返回码、status 原文都写入 `preflight.json`；stop 失败如实
记录，不隐藏。run 合同（F24）陈述的仓库身份是本次投递实际 HEAD：base tree 的中性 re-commit，
由投递自身同一个函数计算；原始 base 与 candidate sha 都不进合同、也不进 run 目录，registry 的
`base_sha` 仍是登记身份。worker 的 env 另含 `TMPPREFIX`（第 4.0 节 F25）。
wrapper_delivery.py 只准备 standalone 任务仓库和投放，render_brief.py 提供本 run 合同和同构报告模板；
旧 prepare/collect/acceptance shell harness 不作为 v2 wrapper 的适配完成证据。

逐 run 的机械验收由两个程序执行，它们就是第 5 节的实现，不接受人工替代：
`collect_v2.py` 采集 base→worker 全量差异、报告、遥测并复核投放字节；
`run_acceptance_v2.py` 产出唯一 verdict JSON 且只在 ACCEPT 时退出 0。收集判 INVALID、
scope 违规、oracle 字节变动均为终局，不再绕过去测量；每个 run 一个 verdict，不合并、不补造。

准备后再次确认 base HEAD、含 ignored 文件的干净状态、全部投放 hash。完成后收集完整
base→worker 差异（含 worker 违约提交时的完整改动）、报告与原始遥测，复核只读投放 hash。
新遥测路径相对于 wrapper，任务文件带 repo/ 前缀；读完整、部分和 grep 三档保持区分。
缺失或空遥测、错误 base、错误材料或跨臂污染按第 6 节登记，不能补造日志。

逐 run 机械验收必须同时满足：

1. 冻结 oracle 的 bytes / hash 保持注册表 base 值；在 `check_task_class.acceptance_env`
   的 RESOLVED 与 SYMLINKED 两种 temp-root spelling 中，均观察 base FAIL→worker PASS。
   使用操作员固定的 PY、同一 oracle 命令和该函数的环境（含 `-s` 与独立 bytecode 缓存），
   分别保存原始输出、rc、实际执行计数和非通过 ID；跳过、expected failure、unexpected
   success 不当作 PASS，空跑或环境未测量也不当作 PASS。
2. 在相同双环境中执行完整 scripts/tests。相对于 T2 同任务的 PRE 非通过集合，不得新增
   非通过 ID；记录执行数量与任何环境差异。T2 PRE 是 RESOLVED 测量，SYMLINKED 的新增
   失败不能静默归一化为 task baseline，必须保留并按证据裁定阻塞 / 无效。
3. scope 检查包括 tracked、untracked、删除、重命名及 worker 违约 commit 的完整差异。
   注册表 deny 文件（全部 base scripts/tests 文件及 oracle）不得变动，deny_prefixes
   必须满足；测试不可改，投放 / 报告 / 遥测不可写进 repo/。路径不能逃出 repo/。
   投放副本按内容识别，但 WARM 与 rules 的源文件本身（`H2_WARM/<dest>` ↔ `<dest>`、
   `H2_RULES.md` ↔ `RULES.md`）是仓内 owner：它们出现与投放相同的字节是修复，不是副本；
   同一字节出现在别的路径才是副本并拒绝。arm carrier 无仓内 owner，出现即拒绝。
4. fresh 独立 auditor 检查合同、diff、原始验收与报告；按 rubric §4 作逐 run correctness
   判定，机械与评审冲突取保守。worker 自报完成不是接受。

## 6. 无效 run 与不可静默重跑

沿用 protocol.md §8：保留 RUN_ID、ARM、TASK_ID、原因、发现时间和 artifact 位置。
wrong worktree/base、carrier/hash 不符、交付/证据污染、路径/路由条件不满足、遥测或报告
缺失、环境/worker 中断、harness defect、model tier 或 task text 不符都必须登记。越出 run 目录的
访问（OUT_OF_RUN_ACCESS，第 4 节）是独立登记原因：命中即无效，不因机械验收通过而软化。
不覆写原 run，不复用 episode，不默默重跑直到结果好看。任何重试须有新的登记身份与原因；
不能把新增重试混入冻结二十条的确认性统计。blocked 与 invalid 分开，均不能冒充 PASS。

driver 副本缺失（EVIDENCE_MISSING）是 INVALID 的独立原因，且永不重试；sandbox 不可用
（SANDBOX_UNAVAILABLE）、渲染 profile 未通过 confinement 自检（SANDBOX_NOT_CONFINING）与
credential 无法导入 fresh home（CREDENTIAL_IMPORT_FAILED）都发生在 worker 动作之前，属于
BLOCKED：不消耗 attempt、不登记，记录在 driver 目录，可在有 sandbox 的环境再次 `run`。
被 sandbox 拒绝的动态访问（`sandbox_denied`）不是 INVALID 原因，按 4.0 节报告。

调度器（第 5 节）只重排**未登记**且在工作之前结束的 run（reachability 失败，或任何未消耗
attempt 的 provider 前状态）：在 plan 位置等待后重试，等待为指数退避加抖动——60 s、120 s、
240 s、480 s，上限 900 s；每次调度器调用对该 run 至多 6 次重排。等待不占 slot，其他已启动的
run 继续持有自己的 slot；每次等待（requeue 序号与秒数）写入 scheduler-v2.jsonl；预算用尽即停止
并打印剩余 run，由操作员重新调用。已登记的 run 永不被调度器重跑，调度器也不改写任何裁定——
包括 §6.1 中三次 before-work 失败后被登记为 BLOCKED 的 run：它是终局登记，只交给操作员裁决，
不因"在工作之前"这一形状被重排。调度器本身被杀时不做清理：已启动的 run 仍归本节规则处理——
下一次 `run` 遇到其残留锁会登记为 INVALID:INTERRUPTED。

### 6.1 预注册的基础设施失败规则（F14）

F14：短暂的上游 provider 故障曾经摧毁一个已计入的 run。live pilot #2 的首个也是唯一事件是
`provider.no-route`，退出码 1、零工具调用；数分钟后同一 env 能正常应答。最近两天已观测到三次
同类短暂失败（401 Invalid credential、"stream ended without finish_reason"、`provider.no-route`）。
若不预先规定，基础设施噪声而非处理本身会吃掉计数 run，并且可能两臂不等。

规则在任何计数 run 之前就已决定，且**两臂对称、对结果盲**（outcome-blind）：它只在 worker
做出任何动作之前触发，因此不能被用来重摇一个结果。

```text
REACHABILITY  每次启动 worker 与 auditor 之前，driver 用同一命令、同一模型、同一 env，在 run
              目录之外的 scratch 目录发送一条冻结的最小 prompt（120 秒上限）。检查失败 =>
              BLOCKED:PROVIDER_UNREACHABLE：不启动任何进程，不消耗 attempt，该 run id 之后
              仍可再次 `run`。每次检查连同时间戳写入 `<runs_root>/reachability-v2.jsonl`。
BEFORE WORK   worker 事件流在首个 tool_use 之前出现 `provider.*` 错误，或 worker 以非零码退出
              且零 tool_use，则该 **attempt** 结束而非该 run 结束：该 attempt 的全部 run 产物
              归档到 `<run_id>/attempts/<n>/`（含逐文件 sha256 的 attempt manifest），
              从零重新准备一个全新的 run 目录（新 repo/、新投放、重新 preflight）后再试；
              同一 run id 至多 3 个 attempt；每个 attempt 都是 attempt registry
              `attempts-v2.jsonl` 中带 attempt 编号的一行。3 次之后该 run 登记为 BLOCKED 并
              停止尝试（由操作员后续裁定，绝不静默跳过）。
AFTER WORK    一旦 worker 做出任何 tool 调用，任何后续 provider 错误、退出或超时都不重试，
              仍按原规则为 INVALID。auditor 适用同一规则并有自己的计数器：被 block 的 audit
              尝试同样归档（`<run_id>/attempts/audit-<n>/`），机械裁定保持不变，run 在 audit
              成功之前保持 BLOCKED。
VERDICT       每个 run 的最终裁定只取自真正到达工作的那一个 attempt；registry 逐条保留全部
              attempt，`registry-v2.jsonl` 每个 run id 恰好一行终止记录，并写明产生它的
              attempt 编号。
```

原因与边界：这条规则只覆盖"worker 尚未动作"的空转，因此不改变任何 worker 行为或结果的判定
方式；它不能把 INVALID 变成 PASS，也不能重跑已经到达工作的 run。三次观测到的失败都在
provider 层，不是任务或交付差异。

```text
HARNESS DEFECT  driver 自身的意外异常既不是 worker 失败也不是结果（F23）。首次 live pilot 第一次
                走到真实 reachability 路径就抛 KeyError: 'profile'，当时只捕获 OSError/ValueError，
                driver 带 traceback 退出，run 停在已准备但未登记的状态。现在整次调用被守卫：
                在 worker 启动之前发生 => 该次调用以 BLOCKED:HARNESS_DEFECT:<ExceptionType> 结束，
                traceback 记入 `<runs_root>/.driver/<run_id>/`，不消耗 attempt、不登记、run 目录
                撤回，同一 run id 之后仍可再次 `run`；在 worker 启动之后发生 => 该 run 登记为
                INVALID:HARNESS_DEFECT:<ExceptionType>，不再启动第二次。判定只取启动边界，
                因此对结果盲：它不看 worker 做了什么，也不能把 INVALID 变成 PASS。
MODEL RULE    二十个 run 的每次 worker 与 auditor 启动只用 run-plan-v2.json 的单一冻结模型
              `opencode-go/deepseek-v4.1-flash`。驱动的 FROZEN_MODEL 与 plan 行不一致、或 plan
              出现第二个模型时，`run` 与 `run-plan` 都在启动任何进程之前拒绝
              MODEL_NOT_FROZEN。实验内部没有模型 failover：模型是处理环境的一部分，两臂模型
              不同的配对不构成比较（第 6 节原因清单中的 model tier 不符即 INVALID）。
              provider 中断只按上面的等待规则处理：reachability 失败不启动任何进程，before-work
              失败重开一个 attempt，调度器按第 6 节退避重排——都不换模型重摇。failover 只存在于
              实现流水线，那条流水线从不接触 H2-R2 run。
```

该模型规则同样在任何计数 run 之前固定，且对结果盲：它只决定"用哪个模型"，不改变任何结果判定，
也不允许在结果不理想时更换模型。

## 7. 预注册结果规则及相对 rubric §9 的偏离

仅使用 DISCLOSURE_SAFE / DISCLOSURE_HAS_COST / INSUFFICIENT_EVIDENCE。
高价值、missed-guidance 归属、correctness、Skill hit 及加载口径直接引用 rubric §2–§8；
优先序与 S1–S5 的阈值和逐任务比较直接引用 rubric §9，不在此复制另一套定义。
真实的 missed-guidance 或较差 correctness / invalid-completion 观测仍优先给出
DISCLOSURE_HAS_COST，环境不足不抹掉它。未达到设计、机制或覆盖条件则
INSUFFICIENT_EVIDENCE；只有满足全部规则且没有下面的 null 阻断，才可给 DISCLOSURE_SAFE。

所有明确偏离 / 适配预先登记如下，不随结果改变：

- 任务集替换为十个可见 frozen-oracle repair，每任务每臂一条。旧 shape-level n=2 的覆盖
  门替换为十任务全部有有效配对；缺任一任务任一臂则不足。没有 within-task replication，
  必须报告这个限制；SAFE 结论只适用于本轮 cohort 与 runtime。
- Null difference 事先定义为：每个有效配对的 audited correctness、invalid-completion
  状态，以及按 rubric §2–§3、§7 审计确认的 finding 身份集合全部相同。无已观察到的
  HAS_COST 原因时，这种 null 必须给 INSUFFICIENT_EVIDENCE，即使其余 S1–S5 满足；
  这是 README §3 混杂对应的保守覆盖，不能仅凭两臂一样就宣布安全。
- delivery 由仓内 CODEBUDDY 改为仓外 AGENTS；telemetry 改为 wrapper-relative；
  runtime/profile/model 改为第 4 节。HOT 降幅仍按实际 carrier 字节的原 JS 字符口径测量，
  不计不可观察宿主注入，不从字符数估算 token 或 model wall-clock。
- 准入和 aggregate owner 改为第 1–3 节；task IDs、oracle、scope、counterbalancing 和
  acceptance 改为本轮注册表 / run plan / 第 5 节。scope 前缀按 F1 固定为 `scripts/tests/`：
  该目录内不得新增、修改、删除或重命名（`unittest discover -s scripts/tests` 把该目录放在
  sys.path 首位，新增的同名模块会覆盖冻结 oracle 解析到的导入，使未修复的 base 假绿）；
  base 的每个测试文件与 oracle 仍逐文件 deny。仓内任何新增或重命名的目标还须通过
  validator 2.8.12 的 `check_task_class.shadow_paths`（导入，不复制），BYTECODE /
  PACKAGE_IMPORTED_BY_DISCOVERY / PACKAGE_MARKER / SHADOWS 任一命中以 WORKER_SHADOWS_IMPORT
  拒绝；仓内任意位置新增 `sitecustomize.py`、`usercustomize.py` 或 `*.pth` 也拒绝。

没有其他评分偏离。findings 尽力盲评并按 rubric §10 如实标明 leakage / 未尝试，
保留每条 run 的原始事实。不要把执行成功、样本数量或 harness 通过当作披露安全结论。

## 8. 首 run 之前与合并路径

README §5 的 live canary 和 fresh DeepSeek exact-freeze-SHA 评审先完成。
随后沿用 [protocol.md §12](../protocol.md#12-收尾--合并门part-3032) 的合并门：
枚举所有适用评审来源与配置 CI，结论必须绑定同一最终 candidate SHA；修复新 SHA 后重审。
没有该 SHA 的评审不能说成没有 finding。得到合法合并权后才走合并与 remote 核验；
本次实现任务不 push、不建 PR、不合并，也不执行任何 H2-R2 run。
