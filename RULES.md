# RULES.md — 普适硬不变量（CANDIDATE V2）

> **状态：CANDIDATE — 未激活。** 本文件只收录"**任何仓库违反即错**"的普适不变量（AUTHORITY_MAP_V2 B 层）。
> 执行方法、风险分级、git/merge/CI 默认全部在 `AGENTS.md` 与 `references/`——它们是**全局默认（D 层）**，仓库本地权威（C 层）可通过显式 OVERRIDE 覆盖。
> 每条规则附 V: 验证钩子。

## R1 权威分层与冲突

- 平台/系统权威（A 层）最高；本文件（B 层）次之；仓库本地产品权威（C 层：RULES/Approved Specs/仓架构/仓 CI 与 merge 政策/ticket 授权）高于全局执行默认（D 层）。
- 对 D 层默认的覆盖必须**显式记录**（`OVERRIDE = <clause> overridden by <authority> <clause> (source)`）；静默覆盖 = 违规。仓库**加严**永远合法且无需记录。
- 权威体系内不可解析的真实冲突 → **STOP: CONTRACT_CONFLICT**，交 product owner 裁决。
- 为什么普适：权威倒置会让任何仓库的产品合同被全局流程压垮（外部评审 F1）。
- V: 治理文件 grep 不存在"项目不得弱化全局/全局高于项目"类单向措辞；校验器检查矛盾权威标记零命中。

## R2 凭据与机器私有信息安全

- **第一层（任何文件、任何位置，绝对禁止）**：Cookie/Secret/Token/API key/登录凭证/SSH 私钥、以及**本机登录名/系统用户身份等 local OS identity**（如宿主登录用户名）绝不进入 repo、log、聊天、产物、长期记忆、报告。凭据探测输出只允许布尔/错误类型。
  - 术语澄清：本层禁的是 **local OS/personal identity**；**repository/account identity**（git 署名如 `FlapPearLabs`、GitHub 账号名、`@users.noreply` 邮箱等公开仓身份）不属于本层禁令，按署名约定正常使用（B2 修复）。
- **第二层（宿主机事实，分区管理）**：宿主路径、端口、二进制位置等 machine-specific 事实——在**一般治理产物**（AGENTS/RULES/references/audit/skills/mcp 等共享语义文件）中禁止；**仅**允许出现在 `deployment/` 下带 `MACHINE-SPECIFIC ALLOWED` 头标记的 designated profile 文件中（私有仓、用途 = 机器恢复与环境复现）。未带标记的文件一律按一般产物对待。
- **历史原文归档（B2 修复）**：被迁移/替换的旧 MEMORY 等 raw 历史文件**默认不进 Git**——原始备份 local-only（Git 之外，如本机私有目录）；治理仓 `deployment/archive/` 只保存 **sanitized/redacted 迁移快照**。任何 raw 归档提交前必须过 R2 第一层扫描 + 人工 redaction，**任何凭据/secret/local identity 命中即阻止 commit**；designated 目录不豁免第一层。
- 提交到 Git 的工具/MCP 配置必须是占位符模板形态（`${HOME}`、`${TOKEN_FROM_ENV}`、`<PATH_TO_BINARY>`）。
- 为什么普适：泄漏不可撤回；分区 + 归档规则让"机器可恢复、历史可追溯"与"共享产物干净"兼容。
- V: `scripts/validate_governance.py` 双层扫描——凭据/local-identity 模式全库零命中（designated 文件不豁免本层）；machine 模式在非 designated 文件零命中；designated 文件必须带头标记。

## R3 证据真实性

- 任何"完成/成功/PASS/verified"声明必须有可复现证据支撑；`UNKNOWN != PASS`；sampled evidence 不得升级为 global claim；报告不得编造新颖性（`NEW_* = NONE` 合法）。
- 对非 PASS CI/评审状态的自分类只能作为**提案**；接受需独立证据 + 独立侧接受（`REVIEWER_ACCEPTED_CLASSIFICATION = YES`）。
- 为什么普适：虚假证据使全部下游 gate 失效。
- V: 非 PASS 状态必附证据块（见 references/git-ci-integration.md）。

## R4 独立评审完整性

- **当**某变更适用独立评审 gate（由风险政策或仓库政策设定）时：executor 的自审（含 /code-review 类工具）不满足该 gate；不得自批自己的 candidate、不得自合并、不得派生受自己影响的 reviewer 冒充独立评审。
- 本条不强制"每个 PASS 都有独立评审者"——gate 是否存在由 D 层风险默认 + C 层仓政策决定（见 AGENTS §3）。
- 为什么普适：gate 存在时被自审替换，则该 gate 形同虚设。
- V: 适用独立评审的 PASS 记录含独立评审者身份 + exact SHA。

## R5 已评审/已发布历史不被静默改写

- 进入评审或已发布（published）的提交历史不得被静默改写：不得 force-push、amend、rebase 已 reviewed 候选分支；修复 = append-only 新 commit → 新 SHA → 适用 gate 按新 SHA 重审。
- 合并方法（ff-only / squash / merge commit）= **仓库政策**（C 层），全局只提供默认（见 references/git-ci-integration.md）。
- 为什么普适：评审结论必须持续对应真实历史；而合并形态属仓库集成政策。
- V: REVIEWED_HEAD == candidate tip（适用时，L0 机械核验）。

## R6 Scope 诚实

- 在票授权的**语义范围**内工作；实现中发现合同空白 → **STOP: CONTRACT_GAP**，不得静默发明缺失语义；发现架构冲突 → **STOP: CONTRACT_CONFLICT**。
- 实施中出现的未预载文件（测试/fixture/支撑缝文件）**不是**自动违规：属票语义范围或有正当理由并经评审确认即可；仅当票明确冻结了文件清单时才适用子集校验。
- 为什么普适：静默扩权与伪 scope 违规都会破坏评审语义。
- V: 意外文件在票据包中有 justification 行（或票声明了冻结清单）。

## R7 平台注入卫生

- 治理/共享产物不得向目标环境注入与其无关的平台特定 shell 要求（例如把单一宿主的 shell/编码习惯设为组织级基线，或反向把另一平台的 shell 习惯注入 macOS 宿主）；宿主环境事实属部署档案（deployment/deployment-profile.md），不是组织规则。
- 为什么普适：平台事实被误升为规则会让跨平台仓库非法化（外部评审 F7）。
- V: `scripts/validate_governance.py` 检查 RULES/AGENTS 无 pwsh/PowerShell/codepage 等异平台 shell 标记。

## R8 最小复杂性护栏

- 新增强制 gate 前必须回答：防哪次真实失效？机器能否更便宜地做？每个风险级都需要吗？能否降级为 reference/默认？
- 无强论证不得入本文件；治理自身受最小复杂性约束。
- 为什么普适：治理自重是平台级风险。
- V: 每条新规则在 audit/PAIN_TO_POLICY_MAP_V2.md 有对应痛点行。
