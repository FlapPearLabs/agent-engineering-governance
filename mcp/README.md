# MCP Guide — canonical 依赖与获取方法（V1）

> **先读这一句（D5）**：下表中的 `TYPE / TRANSPORT / COMMAND / ENDPOINT / HEALTH_CHECK / TRUST_BOUNDARY / REQUIRED_ENV / UPDATE_POLICY` 都是**描述性元数据字段**，不是额外的工具或 MCP server——不要把元数据当成安装需求。
> **环境区分（D3）**：`AVAILABLE_TO_AGENT`（平台可见的一切工具）≠ `USER_CONFIGURED`（用户真实配置的 MCP）≠ `REQUIRED_BY_WORKFLOW`（工作流必需）。本指南只针对 **USER_CONFIGURED ∩ REQUIRED_BY_WORKFLOW**。
> 本目录不提交真实凭据或真实 `~/.workbuddy/mcp.json`（机器私有）；模板见 `example/mcp.example.json`。server 变更走治理变更评审并更新本文件。

# REQUIRED MCP（canonical，V1 全集 = 以下三项）

| 字段 | codegraph | context7 | gh_grep |
|---|---|---|---|
| PURPOSE | 代码结构图：callers/callees/impact/affected 等结构问题接地（模式 A/B/C 见 references/codegraph-grounding.md） | 库/框架文档检索 | GitHub 公开代码搜索 |
| CANONICAL_SOURCE | 本地安装的 CodeGraph CLI（v1.0.1 基准）+ 内置 MCP serve 子命令 | 上游 hosted MCP（context7 官方端点） | 上游 hosted MCP（grep.app 官方端点） |
| INSTALL / ENABLE | 安装 CLI 后加入 agent 的 MCP 配置（`codegraph install` 支持多 agent，或手写配置；模板 `example/mcp.example.json`） | 在 MCP 配置中添加 streamableHttp 端点（模板同左） | 在 MCP 配置中添加 streamableHttp 端点（模板同左） |
| TYPE / TRANSPORT | stdio | streamableHttp | streamableHttp |
| COMMAND / ENDPOINT | `${HOME}/.local/bin/codegraph serve --mcp`（基准宿主；路径以 deployment-profile 为准） | `https://mcp.context7.com/mcp` | `https://mcp.grep.app` |
| REQUIRED_ENV | 无 | 无 | 无 |
| HEALTH_CHECK | `codegraph --version`；MCP 层列 tools；仓库内 `codegraph status` | 任一 library 查询成功 | 任一查询成功 |
| TRUST_BOUNDARY | 本地进程，读仓库（含候选代码）；不出网 | 远程只读查询 | 远程只读查询 |
| UPDATE_POLICY | 版本升级先核验图 schema 兼容（grounding §3 全量重建白名单） | 跟随上游 | 跟随上游 |

**验收（REQUIRED_MCP_READY）**：三个 server 在 agent 的 MCP 工具面可列出并可各完成一次健康查询；缺任一 → 回执 `MISSING_MCP` 并按 CANONICAL_SOURCE 获取；无法获取 → 按 AGENTS §5 MODE C / 相应降级如实报告，不伪造。

# PLATFORM CONNECTORS（平台连接器 —— 不是 MCP）

> 连接器由平台（WorkBuddy/Hermes）连接器体系托管，**不属于 `mcp.json`**；使用时仍受治理 gate 约束（merge/PR/issue 写操作按 RULES/AGENTS 流程执行）。

| CONNECTOR | 分类 | 用途 | 备注 |
|---|---|---|---|
| github | **OPTIONAL_PLATFORM_CONNECTOR** | PR/issue/仓库操作（PR 创建、远程核验等有真实执行证据：governance 仓 bootstrap/PR #1 全程使用） | 可选：无此连接器时用 git + gh CLI（见 deployment-profile）等价完成；canonical MCP 集不含它 |
| agent-mail | DISCOVERED_PLATFORM_CONNECTOR / NOT_REQUIRED / USER_CONFIGURED_UNVERIFIED | （历史发现）agent 邮箱收发 | **无用户采纳/工作流依赖证据，V1 canonical 环境不包含**，setup 路径不安装（D4） |

# 非 canonical 说明

- 平台可见的其他工具/skill/connector 一律视为 `AVAILABLE_TO_AGENT`，**不因可见而成为本工作流依赖**；新增 REQUIRED 项必须走治理变更评审并更新本表。
