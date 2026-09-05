# MCP Governance

## 原则

1. 本目录治理 **MCP 意图**（要哪些 server、为什么、如何验证），不提交任何真实凭据或单机路径。
2. 可提交的只有 `example/mcp.example.json`（占位符形态）。真实 `~/.workbuddy/mcp.json` 属机器私有，禁止入库。
3. server 变更（新增/升级/移除）必须更新本 README 的 manifest 表，走治理变更评审。

## SERVER manifest

| SERVER | PURPOSE | TYPE | COMMAND / URL | REQUIRED_ENV | TRUST_BOUNDARY | HEALTH_CHECK | UPDATE_POLICY |
|---|---|---|---|---|---|---|---|
| codegraph | 代码结构图 MCP（结构问题接地） | stdio | `${HOME}/.local/bin/codegraph serve --mcp` | 无 | 本地进程，读仓库 | `codegraph --version`；serve 后列 tools | 版本升级需先核验图 schema 兼容（见 references/codegraph-grounding.md） |
| context7 | 库文档检索 | streamableHttp | `https://mcp.context7.com/mcp` | 无 | 远程只读 | 请求任一 library id | 跟随上游 |
| gh_grep | GitHub 代码搜索 | streamableHttp | `https://mcp.grep.app` | 无 | 远程只读 | 任一查询 | 跟随上游 |
| (connector) github | GitHub REST/GraphQL：仓库/PR/issue 管理 | app connector | WorkBuddy 连接器管理 | OAuth（connector 托管） | 写操作（repo/PR/issue） | `get_me` | 依赖平台 |
| (connector) agent-mail | agent 邮箱收发 | app connector | WorkBuddy 连接器管理 | 托管 | 邮件边界 | `GetMe` | 依赖平台 |

配置模板见 `example/mcp.example.json`。**占位符约定**：`${HOME}`（用户目录）、`${TOKEN_FROM_ENV}`（从环境变量注入，绝不硬编码）、`<PATH_TO_BINARY>`（本机二进制路径）。

## 信任边界提醒

- stdio server 与 agent 同权限运行：只安装可信来源，来源与本表登记一致。
- 写型 connector（github）的写操作受治理 gate 约束（merge/PR/issue 写入按 RULES/AGENTS 流程执行）。

## MACHINE_SPECIFIC（环境事实登记处，不进 canonical 治理文件）

> 本节内容按机器登记；换机时先复核再使用。示例机器：macOS 工作站（2026-09-05）。

- 外网代理：本机出网统一走本地代理（端口见用户环境约定，如 `http://127.0.0.1:<PORT>`）；git push / gh / npm 均依赖，按操作显式注入 `HTTPS_PROXY`，未写入任何全局 git 配置。
- gh CLI：安装于 Homebrew 路径（如 `${HOME}/opt/homebrew/bin/gh` 或 `/opt/homebrew/bin/gh`），可能不在 agent sandbox 默认 PATH —— 用绝对路径调用；凭据通道 = gh auth git-credential（git credential helper 配置）。
- Git 身份：全局 user.name/email 可能为空；按仓 repo-local 配置署名约定（见 references/git-ci-integration.md §1）。
- WorkBuddy 数据目录：`~/.workbuddy/`（mcp.json、skills、memory 等的宿主）。
