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

## MACHINE_SPECIFIC（政策指针，非登记处）

> 本文件属一般治理产物，按 RULES R2 第二层**不得**登记宿主路径/端口。
> 机器特定事实的唯一登记处 = `deployment/deployment-profile.md`（designated，带 `MACHINE-SPECIFIC ALLOWED` 标记）。
> 与 MCP 相关的机器事实（gh CLI 位置、代理端口、凭据通道）见该档案；本节仅保留机制性说明：
> 外网操作按操作显式注入 `HTTPS_PROXY`（未写入全局 git 配置）；gh 可能不在 agent sandbox 默认 PATH，用绝对路径调用。
