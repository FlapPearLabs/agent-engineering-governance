# RULES.md — 全局硬规则（CANDIDATE V1）

> **状态：CANDIDATE — 未激活。** 只写"违反即错、触发即 STOP"的约束；执行方法见 `AGENTS.md` 与 `references/`。
> 项目级 RULES 可在**不弱化**本文件的前提下加严（如凭据类型、行业合规）。
> 每条规则附验证方式（V:），供评审与 L0 机器核验引用。

## R1 权威与冲突

- 权威链：RULES.md > AGENTS.md > references > skills/MCP > MEMORY 偏好 > runtime memory。
- 权威内部出现无法按链裁决的真实冲突 → **STOP: CONTRACT_CONFLICT**，禁止静默择便。
- 修改本文件或 AGENTS.md 必须走治理变更双评审（见 AGENTS §8）。
- V: 治理变更 commit 的 PR 中存在两个独立评审 PASS 记录（同 exact SHA）。

## R2 凭据与机器私有信息安全

- Cookie/Secret/Token/API key/登录凭证/SSH 私钥绝不进入 repo、log、聊天、产物、长期记忆、报告。
- 向 Git 提交的 MCP/工具配置必须是 example/template 形态：`${HOME}`、`${TOKEN_FROM_ENV}`、`<PATH_TO_BINARY>` 占位，不得含真实值或机器私有绝对路径。
- 凭据探测输出只允许布尔/错误类型，不允许值、长度、前缀、哈希。
- V: push 前 secret/路径扫描（gitleaks 类或 grep 清单）零命中。

## R3 Scope 纪律

- 严格按当前票授权 scope 工作；"顺手修"无关文件 = scope violation；future requirement visible ≠ authorized。
- 实现票不得偷改 Spec/治理；发现合同空白 → STOP: CONTRACT_GAP，不得静默补齐。
- V: L0 diff 范围核验（changed files ⊆ 授权清单）。

## R4 Git 红线

- 禁止 force-push、amend、rebase-after-review、squash 已 reviewed 历史。
- master 集成：仅 ff-only、逐个串行；每次 merge 前 fresh fetch + 远端身份核验。
- 禁止 `reset --hard` / `clean -fd` 绕过异常；refs 异常走无损恢复流程并 STOP 求裁决当无法确证。
- V: merge 前机械核验记录（remote master SHA、candidate SHA、ancestry）。

## R5 EXACT-SHA 绑定

- 任何评审 PASS 只绑定 exact commit SHA。任何生产代码变更 → 新 SHA → 旧评审对**变更代码**失效。
- 新鲜评审 ≠ 重读全仓：blast radius 未扩张时 = previous reviewed SHA + delta + CodeGraph 爆炸半径 + 权威。
- MASTER_DRIFT 是机械时序条件（re-form + fresh review），不是契约冲突；CONTENT_CONFLICT 才走 STOP 裁决。
- V: REVIEWED_HEAD == branch tip == merge candidate（L0 自动）。

## R6 SELF_REVIEW != INDEPENDENT_REVIEW

- 任何角色不得批准自己的 candidate、合并自己的产物、或 spawn 受自己影响的 reviewer 冒充独立评审。
- Worker 可跑 `/code-review` 类自审工具，但结果永远只是自审证据。
- V: 每个 PASS 记录含独立评审者身份 + exact SHA；缺任一即无效。

## R7 CI 诚实性

- `LOCAL_TESTS != REAL_PR_CI`。CI 状态集：PASS / FAIL / NOT_TRIGGERED / CANCELLED / INFRASTRUCTURE_FAILURE / KNOWN_BASELINE_FAILURE / UNKNOWN（可扩不可坍缩）。
- 禁止 NOT_TRIGGERED = PASS、UNKNOWN = PASS、KNOWN_BASELINE_FAILURE = PASS。
- Worker 对非 PASS 的分类 = PROPOSAL_ONLY；接受需独立评审 `REVIEWER_ACCEPTED_CLASSIFICATION = YES` + 证据（候选 CI 真实运行、失败签名、干净 base 复现、非候选引入）。
- 证据块格式见 `references/git-ci-integration.md`。
- V: 非 PASS CI 必附 generic evidence block；KNOWN_BASELINE 额外附 9 字段块。

## R8 证据真实性

- 任何"完成/成功/PASS/verified"声明必须有可复现证据支撑；`UNKNOWN != PASS`；sampled evidence 不得升级为 global claim。
- 报告不得编造新颖性；`NEW_* = NONE` 是合法值。
- V: 抽查关键声明的证据链；无证据声明直接无效。

## R9 FAIL-CLOSED 且不过度拒绝

- 新增 validator / fail-closed 路径必须同时回答："它是否拒绝当前合法的生产者输出？"
- `LEGAL_RUNTIME_REGRESSION_RISK` 高或未知且权威不明确 → 不自动加固。
- V: 新拒绝路径附合法输出枚举或授权豁免记录。

## R10 机器私有数据不全局化

- 全局治理文件不得包含：本机绝对路径、用户名、代理地址、端口、凭据文件位置、单机环境备忘。
- 机器特定事实的唯一归属 = 治理仓 `mcp/README.md` MACHINE_SPECIFIC 节 + MEMORY 环境区（显式标注 machine-specific）。
- V: 治理文件 grep 用户名/绝对路径零命中。

## R11 最小必要复杂性（防过度治理）

- 新增强制 gate 前必须回答：防哪次真实失效？机器能否更便宜地做？每个风险级都需要吗？能否降级为 reference？
- 无强论证不入 RULES；治理自身受最小复杂性约束。
- V: 每条新规则在 PAIN_TO_POLICY_MAP 有对应痛点行。

## R12 平台基线

- 当前全局基线 = macOS 原生 shell/工具链，UTF-8。
- 历史 Windows/PowerShell 材料分类为 STALE_FOR_CURRENT_WORKBUDDY 或 WINDOWS_PORTABILITY_REFERENCE，不得激活为全局政策；仓内 Windows 规则不受影响。
- V: 全局治理文件 grep pwsh/PowerShell/codepage 零命中（引用性提及除外）。

## R13 单分支单活跃写者

- 任一分支同一时刻至多一个活跃写者；跨分支并行不受限。
- 写者交接：前写者停止 → fresh fetch → 核验 remote tip → 重建状态 → 从 exact tip 继续。
- 禁止为该规则引入分布式锁/协调服务等多余设施。
- V: 分支写权记录；并发写事故 = 红线事故。

## R14 Worker 权威边界

- Worker 实现不授予架构/Spec 权威：不得扩 scope、开下游票、改冻结 Spec/DAG、把未来需求当当前授权。
- 发现实现需要发明缺失语义 → STOP: CONTRACT_GAP；发现架构冲突 → STOP: CONTRACT_CONFLICT。
- V: 票据包内无超授权文件变更；STOP 记录完整。
