# AS-IS WorkBuddy 全局工程权威审计（证据版）

> 审计日期：2026-09-05 · 环境：macOS（darwin）· WorkBuddy 桌面版
> 方法：只读机械检查 + 本会话可观测事实。所有结论附本地路径证据。
> 路径均以 `~/` 形式书写（home 相对），避免提交机器私有绝对路径。

## 1. CURRENT_AUTHORITY_MAP

| 层 | 实际权威来源 | 证据 |
|---|---|---|
| 系统级注入 | WorkBuddy 系统提示（含 user_memory 注入、身份文件注入、skills 清单注入） | 本会话系统上下文可观测 |
| 全局工程宪法 | `~/.workbuddy/MEMORY.md`（29,810 字节 / 319 行） | `ls -la ~/.workbuddy/`；`Read ~/.workbuddy/MEMORY.md` |
| 全局身份/人格 | `~/.workbuddy/SOUL.md`、`IDENTITY.md`、`USER.md`、`BOOTSTRAP.md` | 同上 |
| 全局 AGENTS.md / RULES.md | **不存在**。`~/.workbuddy/AGENTS.md`、`~/.workbuddy/RULES.md`、`~/AGENTS.md`、`~/RULES.md`、`~/CLAUDE.md` 全部缺失 | `ls -d` 探测全部 miss |
| 项目级权威 | 产品仓自带 `AGENTS.md` + `RULES.md`（zhihu-grabber-toolkit：846 行 + 196 行；a'gen't'resume：69 行 + 81 行；Projects/simple-code 也有 AGENTS.md） | `wc -l` 与 `Read` 已核验 |
| Workspace 记忆 | 每工作区 `.workbuddy/memory/YYYY-MM-DD.md`（append-only）+ `MEMORY.md`（≤3,000 字符） | 本工作区 `.workbuddy/memory/` 约定 |
| Skills | `~/.workbuddy/skills/`（196 项）+ 内置插件 skills（24 项）+ 连接器附带 skills | `ls ~/.workbuddy/skills/ \| wc -l` = 196 |
| MCP | `~/.workbuddy/mcp.json`：codegraph（stdio）、context7、gh_grep（remote）；另有 app 管理的连接器（github、agent-mail） | `Read ~/.workbuddy/mcp.json` |

### 1.1 关键机械发现：全局宪法注入截断（CRITICAL）

`~/.workbuddy/MEMORY.md` = 29,810 字节。本会话注入的 `<user_memory>` 副本在
`RELEVANT_SURFACE_MANIFEST` 条目中途被截断（原文尾部为 "…security/privacy propaga
… (user memory truncated)"）。

后果（可机械验证）：

- 注入副本 ≈ 4K 字符量级，约 87% 的文件内容**未进入 agent 上下文**；
- 被截掉的部分恰好包括文件末尾的三大 ACTIVE OVERRIDE：
  - `GLOBAL ENGINEERING MEMORY OVERRIDE — ORCHESTRATOR / WORKER / REVIEW AUTHORITY`（隔离 worker 可直接实现生产代码、third-party review 是角色不是厂商）
  - `GLOBAL REPORTING OVERRIDE — NOVELTY-FIRST`（novelty-first 报告 + CI 压缩例外）
  - `GLOBAL REPAIR SATURATION / VALUE-BASED CONVERGENCE OVERRIDE`（SEVERITY != REPAIR_AUTHORITY、repair budget=2、Convergence Arbiter）
- 即：**当前最核心的全局规则位于 agent 实际最不容易看到的位置**。文件头部用"Jump to …"指针补救，但指针指向的内容本身被截断。
- 另一层矛盾：MEMORY.md 自身约定"user-level memory 限 4,000 字符/session"（系统提示），而文件已膨胀到 29.8KB —— 宪法长度与加载机制物理不兼容。

## 2. CURRENT_FILES（全局权威相关文件清单）

```
~/.workbuddy/
├── MEMORY.md                 # 全局工程宪法（29,810B，TRUNCATED ON INJECTION）
├── SOUL.md / IDENTITY.md / USER.md / BOOTSTRAP.md   # 人格/身份，非工程治理
├── mcp.json                  # 3 个 MCP server，无 secrets（已核验）
├── mcp-approvals.json        # MCP 审批状态
├── settings.json             # 插件开关、sandbox 写白名单、claw 通道；无模型路由配置
├── skills/                   # 196 个用户级 skill
├── plugins/                  # 插件缓存（含 workbuddy-builtin / codebuddy-plugins-official 等）
└── memory/                   # 云端 profile 缓存（server 管理，本地只读）
```

无任何名为 `RULES.md` / `AGENTS.md` 的全局文件；无全局 review checklist 模板；无全局 workflow doc。

## 3. CURRENT_PRECEDENCE

实测可观测的加载顺序（自上而下）：

1. 系统提示（硬编码：安全策略、工具契约、automations、memory 系统说明）
2. `<user_memory>` 注入 = `~/.workbuddy/MEMORY.md`（**~4K 截断**）
3. `<identity_context>` 注入 = `~/.workbuddy/{SOUL,IDENTITY,USER,BOOTSTRAP}.md`
4. `<project_context>` = 工作区文件结构 + 附加数据
5. Skills 清单（`<available_skills>`）按需经 Skill 工具加载
6. Workspace 记忆（`.workbuddy/memory/`）由 agent 主动读写，不自动注入全文

**没有文档化的"权威冲突裁决规则"**。工程语义上 MEMORY.md 是唯一全局宪法，但它与系统提示冲突时谁赢、与项目 AGENTS.md 冲突时谁赢，均无明文。产品仓内部已自建裁决链（zhihu 仓 `AGENTS.md` §1：RULES.md 硬约束 > Approved Specs > AGENTS.md 流程 > runtime memory），但该链**只在仓内有效**。

## 4. CURRENT_MEMORY_ROLE

`~/.workbuddy/MEMORY.md` 现状 = **TICKET LANE V2 + 三大 OVERRIDE 的全文宪法**，混合了：

- 应为硬规则的内容（exact-SHA、SELF_REVIEW != INDEPENDENT_REVIEW、CI 诚实性）
- 应为执行架构的内容（角色模型、lane 流程、并行/串行）
- 应为参考的内容（counterexample 类目清单、REPAIR_VALUE 字段表、报告模板）
- 机器私有事实（`/Users/songshiyao/.local/bin/codegraph` 绝对路径硬编码）
- 模型名单（Mimo V2.5 / Hunyuan / GPT Luna / DeepSeek V4 / GLM 5.3 Flash / GPT Terra / GPT Sol —— 无法从任何本地配置文件核验其可用性）

分类判定（详见 AUTHORITY_MAP_V1 / MIGRATION_PLAN）：约 70% 应 MOVE 到治理仓库的 AGENTS/RULES/references；~5% STALE/机器私有；~15% KEEP_IN_MEMORY（偏好、环境事实、指针）；其余为 DUPLICATE（与项目 AGENTS.md 重复维护，存在漂移风险）。

## 5. CURRENT_SKILLS

- 用户级 196 项（`~/.workbuddy/skills/`），内置 24 项（WorkBuddy.app 插件目录）。
- Matt Pocock 工程技能族**全部在位**（`SKILL.md` 存在性 + frontmatter 已核验）：
  `grill-with-docs`、`to-spec`、`to-tickets`、`implement`、`tdd`、`code-review`、`diagnosing-bugs`、`resolving-merge-conflicts`、`writing-plans`、`setup-matt-pocock-skills`、`subagent-driven-development`、`simplify-code`。
- 辅助族：`handoff`（跨会话交接文档，写入系统临时目录）、`codegraph-integration`（Hermes 导向的用户自建 skill）、`repository-audit`、`plan` 等。
- **重复/竞争路由风险**（同名职责多实现）：`code-review`（Pocock）vs `review-agent`；`diagnose` vs `diagnosing-bugs`；`grill-with-docs` / `grilling` / `grill-me` / `batch-grill-me` ×4。
- `/to-tickets` 关键契约（已全文核验）：tracer-bullet 垂直切片 + blocking edges + "work the frontier"；**含 "look for opportunities to prefactor" 条款**（架构发明漂移点）；**无 Execution Stage 概念**（frontier 就绪即全部可开工 = 被禁止的 ALL_READY_TICKETS=START_ALL 模式）；`disable-model-invocation: true`（仅用户可调用，好）。
- 无任何全局文件定义 skill 优先级或"SKILL_IS_EXECUTION_METHOD / SKILL_IS_NOT_AUTHORITY"边界；该边界目前只存在于截断的 MEMORY 与项目 AGENTS.md §18.8。

## 6. CURRENT_MCP

`~/.workbuddy/mcp.json`（已核验，无 secrets）：

| SERVER | 类型 | 用途 | 备注 |
|---|---|---|---|
| codegraph | stdio | 代码结构图 MCP | 命令为机器私有绝对路径 `~/.local/bin/codegraph`（符号链接 → `~/.codegraph/versions/v1.0.1/bin/codegraph`） |
| context7 | streamableHttp | 库文档检索 | 远程，无需凭据 |
| gh_grep | streamableHttp | GitHub 代码搜索 | 远程，无需凭据 |

另有 app 管理连接器：GitHub（REST/GraphQL，含 create_repository / create_pull_request / push_files 等）、Agent Mail。GitHub REST 路径与 `gh` CLI 双轨并存。

## 7. CURRENT_CODEGRAPH

- 版本：1.0.1（update-check 显示上游 latest v1.5.0，存在版本滞后可能）。
- **图数据库按 worktree 碎片化（实测）**：`~/WorkBuddy/wt-p1-t09/.codegraph/` 存在，而主仓 `~/WorkBuddy/zhi'hu'grabber/.codegraph/` **不存在** —— 即 lane worktree 各自持有/生成图，"canonical master graph + incremental delta" 目前只是 MEMORY 里的愿景句，无任何机制文件保证。
- MEMORY 中 `INDEPENDENT_CODEGRAPH_GROUNDING != INDEPENDENT_FULL_REINDEX` 语义存在（在被截断段之外的 Lane V2 主体内，可见）。
- 每评审/每工单全量重建的历史仪式：以 MEMORY 自述与用户工程记忆为证，无本地反证。

## 8. CURRENT_MODEL_ROUTING

- **无文件级路由配置**。`settings.json` 无模型字段；模型选择面 = 会话级模型切换（app UI）+ Agent 工具的 `model: default|lite|reasoning` 参数。
- 路由规则目前以**散文形式**写在 MEMORY（LOW→Mimo/Hunyuan/Luna；MEDIUM→DeepSeek V4 Flash/GLM 5.3 Flash；长文→DeepSeek V4 Pro/Terra；CRITICAL→GPT-5.6 Sol）。名单中的模型可用性无法从本地配置核验（本会话底层模型为 GLM-5.3-Flash 级别）。
- 结论：RISK FIRST / MODEL SECOND 有原则、无可执行面；外部评审（Sol 级）依赖用户手工搬运（web GPT），无自动路由。

## 9. CURRENT_TICKET_FLOW（实际在跑的流程，以 zhihu-grabber-toolkit 为证据源）

- 权威：仓内 `AGENTS.md`(846 行) + `RULES.md`(196 行) + Approved Specs + GitHub Tracker/Issues。
- 实体形态：`git worktree list` 实测 5 个 lane worktree（wt-p1-reform / wt-p1-t08 / wt-p1-t08-reform / wt-p1-t09 / wt-p1-t11），分支 `work/p1-t*`、`planning/p1-*`、`docs/memory/*`。
- 流程（AGENTS.md §3 Continuous Goal Mode）：OBSERVE → READ AUTHORITY → DERIVE NEXT LEGAL TICKET → START_GATE → EXECUTE → STATIC → DYNAMIC → SELF-REVIEW → PUSH → CI → INDEPENDENT REVIEW → REPAIR → EXACT-SHA PASS → FF-ONLY MERGE → REMOTE VERIFY → CLOSE → NEXT。
- 实际 commit 历史可见技能驱动痕迹：`/code-review self-review repairs`、`/simplify`、`POST_MERGE_T10_REPAIR`、多轮 `fix(p1-t10): repair`（默认拒绝式修复链）。
- **该流程只覆盖装了 AGENTS.md 的仓**。adaptive-vocab-reader 及未来新仓依赖全局 MEMORY（截断）+ 用户口头治理，无可移植安装机制。

## 10. CURRENT_REVIEW_FLOW

- 项目内：Executor self-review（可用 /code-review）→ 独立 Reviewer Subagent（按 ticket 类型 1~2 人 quorum，同 exact HEAD）→ 指定外部审查时走 PRE-EXTERNAL TERMINAL BARRIER → 最小 handoff → 用户搬运到 web GPT（Sol）。
- 全局：`SELF_REVIEW != INDEPENDENT_REVIEW` 写在 MEMORY（Lane V2 段，可见）；repair budget/arbiter 写在 MEMORY 尾部（**截断区**）。
- 无全局评审分级（L0 机器 / L1 普通 / L2 强评审）——分级仅在本次审计目标中首次成文。

## 11. CURRENT_CI_FLOW

- 规则（可见段 + 项目 RULES §10）：`LOCAL_TESTS != REAL_PR_CI`；CI 状态枚举与 KNOWN_BASELINE_FAILURE 9 字段证据块在 MEMORY 报告 override 段（**截断区**）。
- zhihu 仓无强制 PR CI workflow（无 .github/workforces 证据要求；以本地 suites + remote refs 核验为主）；adaptive-vocab-reader 有 e2e-verify.cjs 本地门槛。
- 机械核验（SHA、diff 范围、secret 扫描、ancestry）目前全靠 agent 手工执行，无 harness。

## 12. CURRENT_GIT_FLOW

- 项目级红线（RULES §8）：禁 force push / amend / rebase-after-review / squash；ff-only；master 串行集成；merge 前 fresh fetch + remote master 核验；`MASTER_DRIFT != CONTENT_CONFLICT`。
- 全局 git 身份：`git config --global user.name/user.email` **为空**；凭据走 `credential.https://github.com.helper = !/opt/homebrew/bin/gh auth git-credential`。
- 署名纪律（AUTHOR_NAME=FlapPearLabs / GITHUB_NOREPLY）存在于用户工程记忆，未落任何全局文件；逐仓 repo-local config 维持。
- 代理依赖：外网统一走 `http://127.0.0.1:7897`（git push / gh / npm 均依赖），**未写入任何持久配置**，每次操作需显式 env —— 机器特定、易碎、无文档。
- `gh` CLI 在 `/opt/homebrew/bin/gh`（v2.89.0，已认证 FlapPearLabs），**但不在 agent sandbox 默认 PATH 中**（裸 `gh` 报 command not found；绝对路径可用）。

## 13. CURRENT_MULTI_AGENT_CAPABILITY

- 平台能力具备：Agent 工具可 spawn 隔离子代理（general-purpose / Explore / Plan / 专用 doc 流水线 agents），支持 run_in_background、SendMessage、团队消息；`subagent-driven-development` skill 提供 delegate_task 两段评审模式。
- 缺机制保证：worker/reviewer 的 context 隔离、fresh reviewer 独立 grounding、repair budget 计数，均靠提示词纪律（项目 AGENTS.md / 截断的 MEMORY），无平台级强制。
- 编排者"thin control plane"语义（MEMORY Override §1，**截断区**）与平台能力匹配，但同样无机制文件。

## 14. CURRENT_AUTONOMY_BOUNDARY

- 项目级（zhihu AGENTS.md §3/§17）：Continuous Goal Mode 明确"不得因普通事件停止"、七类合法 STOP 状态、milestone 完成不自动进入排除阶段 —— **全局层无对应条款**（USER_DECISION_REQUIRED 语义在用户偏好记忆中，属于行为习惯而非全局成文规则）。
- 观察到的真实交互负担：Codex handoff（历史模式）、外部评审搬运、"开始施工"后逐票人工确认，在未装项目 AGENTS.md 的仓中仍会发生。

## 15. WINDOWS / 跨平台残留审计

- 全局 MEMORY.md：0 处 PowerShell/pwsh/Windows/codepage 命中（grep 实测）。
- 用户级 skills 目录：0 处命中。
- 全部 workspace memory 目录：0 处命中。
- 结论：**当前活跃面上无 Windows 时代全局政策残留**（历史版本可能存在于仓库 git 历史中，不在本审计范围）。macOS 基线成立；候选治理仍应保留 WINDOWS_PORTABILITY_REFERENCE 分类条款以防回归移植。

## 16. AS-IS 一句话结论

工程宪法**内容已经进化到 G3.5**（Lane V2 + 三大 OVERRIDE，质量高），但**宿主机制停留在 G1**：一份 30KB 记忆文件承载全部权威、注入即截断、无全局 AGENTS/RULES、无 Stage 概念、无评审分级、无 CodeGraph 增量机制、模型路由与工具链事实散落且部分机器私有。核心矛盾 = 治理内容先进性 vs 治理载体的原始性。
