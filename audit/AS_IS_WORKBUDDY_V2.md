# AS_IS_WORKBUDDY_V2 — 描述性冻结（无建议、无目标）

> 每条陈述标注 **FACT / INFERENCE / UNKNOWN**。本文不含任何 target 建议（AS-IS 只回答：什么存在、什么加载、什么不加载、什么被执行、什么只是写下来的、什么是项目级/全局/机器私有、什么是未知的）。
> 观测日期 2026-09-05；观测者 = WorkBuddy 会话（只读探针）。路径以 `~/` 相对书写。
> AS_IS_FROZEN = YES（基于本文件与 AUDIT_QUALITY_REVIEW 的事实层）。

## 1. 文件系统事实

- FACT：`~/.workbuddy/MEMORY.md` 存在，29,810 字节 / 319 行，内容 = TICKET LANE V2 + ORCHESTRATOR/REPORTING/REPAIR-SATURATION 三 OVERRIDE。
- FACT：`~/.workbuddy/` 与 `~/` 下不存在 AGENTS.md、RULES.md、CLAUDE.md（`ls -d` 探测 miss）。
- FACT：存在身份文件 `SOUL.md / IDENTITY.md / USER.md / BOOTSTRAP.md`（人格/身份内容）。
- FACT：`~/.workbuddy/skills/` 含 196 项；WorkBuddy 内置插件 skills 24 项（App 资源目录清点）。
- FACT：`~/.workbuddy/mcp.json` 定义 3 个 server：codegraph(stdio, 指向 `~/.local/bin/codegraph`)、context7、gh_grep；文件内无 token/secret 字段。
- FACT：`~/.workbuddy/settings.json` 含插件开关、sandbox 写白名单、claw 通道配置；无任何模型路由字段。
- FACT：`~/.local/bin/codegraph` → `~/.codegraph/versions/v1.0.1/bin/codegraph`；CLI 子命令实测 = init/uninit/index/sync/status/query/explore/node/files/callers/callees/impact/affected/daemon/unlock/install。
- FACT：`.codegraph/` 目录存在于 `~/WorkBuddy/wt-p1-t09/`，不存在于 zhihu 主仓目录（`ls -d` 实测）。
- UNKNOWN：wt-p1-t09 图库的创建时间、索引 base、新鲜度（未做 status 探测的历史还原）。
- UNKNOWN：`~/.codegraph/daemons` 运行中的 daemon 与 repo 的映射关系。

## 2. 加载/注入行为

- FACT：WorkBuddy 会话注入 `~/.workbuddy/MEMORY.md` 内容为 `<user_memory>`，且**在 byte 4028 处截断**（本会话注入副本于 `security/privacy propaga` 处中断 + `grep -b` 定位）。即 319 行中约前 33 行可见，三大 OVERRIDE 全部不可见。
- FACT：同一会话注入了 `~/.workbuddy/{SOUL,IDENTITY,USER,BOOTSTRAP}.md` 全文（身份四件套无截断迹象）。
- FACT：本会话注入了 `<available_skills>` 清单与项目上下文（工作区文件树）。
- FACT：本会话**未**注入任何项目仓的 AGENTS.md/RULES.md（本工作区为空目录，无法构成反例）。
- INFERENCE：WorkBuddy 对用户级 MEMORY 注入存在 ~4K 量级预算（由 4028 截断点推断；具体预算数值与策略未被文档证实）。
- UNKNOWN：WorkBuddy 是否会在"工作区根含 AGENTS.md"的场景自动注入它（本审计无该场景观测）。
- UNKNOWN：MEMORY 注入预算是否可配置（settings.json 中无相关字段）。

## 3. 什么在被"执行" vs 只是"写下来"

- FACT（被执行）：zhihu-grabber-toolkit 仓内 RULES.md/AGENTS.md 的约束在其实际 git 史中可见遵循痕迹（ff merge、append-only repair、Conventional Commits、scope-clean 分支；`git log` 实测 T07/T10 系列）。
- FACT（被执行）：WorkBuddy 系统层约束（sandbox、权限、工具契约）由平台强制（本会话直接可观测）。
- FACT（只是写下来）：全局 MEMORY.md 尾部三大 OVERRIDE——写下来了但因截断**无法被会话看到**（机械事实），故"全局执行"无从谈起。
- INFERENCE：MEMORY.md 头部（可见区）的 Lane V2 主体 + "Jump to"指针是当前唯一有真实到达机会的全局工程语义。
- UNKNOWN：历史上其他会话是否曾加载过完整 MEMORY（例如更早版本较短时）。
- FACT（项目级被执行的评审纪律）：zhihu 仓 AGENTS §5 quorum 表、§18.4 顺序、§18.5 barrier、§18.6 评审状态分类均为仓库文本且在 commit 史有对应实践痕迹（review/self-review/repair commit 序列）。
- UNKNOWN：各实践在项目内的执行率/违例率（无统计）。

## 4. 全局 / 项目 / 机器私有归属（现状）

- FACT：当前全局层 = MEMORY.md（截断注入）+ 身份文件 + 系统提示（含 skills 清单）。
- FACT：工程宪法语义当前实际宿主 = 项目仓（zhihu AGENTS/RULES 全文），而非任何全局文件。
- FACT：机器私有事实散落处 = MEMORY.md 内绝对路径（`/Users/…/.local/bin/codegraph`）、mcp.json 绝对路径、git credential helper 的 gh 绝对路径、代理端口仅存在于用户操作习惯（无持久配置文件）。
- FACT：`gh` 2.89.0 位于 `/opt/homebrew/bin/gh`，已认证 FlapPearLabs；agent sandbox PATH 中无 `gh`（裸命令 miss，绝对路径可用）。
- FACT：全局 git config：credential.helper 走 gh；user.name/email 为空；无 http.proxy 配置。
- FACT：zhihu 仓 5 个 linked worktree（wt-p1-reform/t08/t08-reform/t09/t11）——每 lane 独立目录/分支。
- FACT：a'gen't'resume 仓同样采用 AGENTS.md+RULES.md 模式（内容与 zhihu 不同，未共享文件）。

## 5. skills 实际契约（主链，全文/头部已读）

- FACT：`grill-with-docs / to-spec / to-tickets / implement / tdd / code-review / diagnosing-bugs / resolving-merge-conflicts / writing-plans / setup-matt-pocock-skills / subagent-driven-development / simplify-code` 全部存在且 frontmatter 可读。
- FACT：`to-tickets` 契约含 "Work the frontier"（就绪即开工）与 prefactor 提示条款；`disable-model-invocation: true`。
- FACT：`review-agent`（只读缺陷列举，服务委派评审）与 Pocock `code-review`（固定基点标准+风险双轴）契约为互补关系。
- FACT：主链 SKILL.md 均无 version/license/source 元数据字段。
- UNKNOWN：各 skill 上游仓库与 commit（本机无记录）。

## 6. CodeGraph 实际行为

- FACT：能力面 = init/index/sync/status/query/explore/node/files/callers/callees/impact/affected/daemon（`--help` 全量）。
- FACT：`sync` 帮助文本 = "Sync changes since last index"（增量语义存在）；`impact` = 变更影响分析；`affected` = 受影响测试定位。
- FACT：图数据库位于项目目录 `.codegraph/`（uninit 帮助："deletes .codegraph/ directory"）——**每目录一库**，无内建跨目录共享。
- UNKNOWN：worktree 场景下官方推荐用法；daemon 与多目录的关系细节。

## 7. Git/GitHub/网络现状

- FACT：git 2.50.1；credential 走 gh auth git-credential；gh 已认证（FlapPearLabs 活跃 + panglihaoshuai）。
- FACT：治理仓 bootstrap（本会话）通过显式 `HTTPS_PROXY=http://127.0.0.1:<port>` 注入完成 push/PR——该代理仅存在于操作时刻的环境变量，无持久配置。
- INFERENCE：本机外网操作依赖本地代理（多项目记忆与本次成功操作一致指向该结论）。
- UNKNOWN：无代理时各端点的可达性（未测）。

## 8. 平台（runtime）层

- FACT：WorkBuddy 提供 Agent 子代理工具（general-purpose/Explore/Plan 等）、后台任务、消息传递；沙箱与审批由平台强制。
- FACT：本会话模型层 = GLM-5.3-Flash 级（系统可观测）；Agent 工具 `model` 参数支持 default/lite/reasoning。
- FACT：MEMORY 所列具体型号（Mimo/Hunyuan/Luna/DeepSeek V4/Terra/Sol）在本地任何配置文件中无对应条目。
- UNKNOWN：平台会话模型选择与 MEMORY 名单的映射关系。

## 9. 产品仓证据现状（READ-ONLY）

- FACT：zhihu-grabber-toolkit 主仓 AGENTS.md=846 行、RULES.md=196 行、Approved Specs（v2 baseline + v0.3 additive）、docs/t01/t4/t5*/t7/t9 契约文档存在。
- FACT：git 史含多轮 repair 链（如 T10 系列 fix/repair commits、POST_MERGE_T10_REPAIR）、reform 分支（wt-p1-t08 与 wt-p1-t08-reform 并存）。
- FACT：docs/t7-top-percent-contract-decision.md、t9-hierarchical-digest-contract.md 等冻结决策文档存在（存在性核验；全文未在本轮重读）。
- UNKNOWN：T08/T09 评审收敛过程的完整归档细节（超出本轮读取范围，未重读）。

## 10. 明确的 UNKNOWN 清单（后续按需补证）

1. WorkBuddy 对工作区根 AGENTS.md 的处理（自动注入与否）。
2. MEMORY 注入预算的官方数值/可配置性。
3. CodeGraph 多 worktree/daemon 官方语义。
4. 主链 skill 上游 source/commit/license。
5. 首审期间 wt-p1-t09 图库的 base 与新鲜度。
6. 代理缺失时的网络行为。
