# deployment-profile — 宿主/环境事实（machine-specific，非组织规则）

> **MACHINE-SPECIFIC ALLOWED** —— 本文件是 RULES R2 第二层的 designated deployment profile：宿主路径/端口/二进制位置允许入库（私有仓、用途 = 机器恢复与环境复现）；**凭据/secret/local OS identity 仍然绝对禁止**（R2 第一层，designated 不豁免）。
> 本文只登记**当前宿主**的事实；换机/换环境时复核改写。不属于 RULES，不属于任何仓的产品语义（RULES R7）。
> 通用占位符约定见 mcp/README.md。

## 当前部署档案（macOS 工作站，登记于 2026-09-05）

| 项 | 值 | 性质 |
|---|---|---|
| 宿主 OS | macOS (darwin) | FACT |
| shell 基线 | zsh；UTF-8 | FACT |
| gh CLI | `/opt/homebrew/bin/gh`（v2.89.0，认证 FlapPearLabs；不在 agent sandbox PATH，绝对路径调用） | FACT |
| git | 2.50.1；credential = gh auth git-credential；全局 user.name/email 空（按仓 repo-local 设置） | FACT |
| 出网代理 | 本地代理 `http://127.0.0.1:7897`（git push / gh / npm 依赖；显式 `HTTPS_PROXY` 注入，无持久配置） | FACT |
| WorkBuddy 数据目录 | `~/.workbuddy/`（MEMORY/mcp.json/skills/settings） | FACT |
| CodeGraph | `~/.local/bin/codegraph`（→ versions/v1.0.1）；MCP serve 已配置 | FACT |
| MEMORY 注入预算 | 实测截断点 byte 4028 | FACT（机制层面 UNKNOWN） |

## Windows / 跨平台说明

- 本档案的 macOS 事实**不构成**对任何仓库的目标平台约束：Windows 目标仓完全合法（RULES R7）。
- 历史 Windows/PowerShell 治理材料分类：`WINDOWS_PORTABILITY_REFERENCE`（活跃面零残留，2026-09-05 grep 核验）。
