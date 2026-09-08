# deployment-profile — 宿主/环境事实模板（PUBLIC-SAFE TEMPLATE）

> **本文件是模板，不是任何真实机器的档案。**
> 本仓库是 **PUBLIC** 仓库：公开产物不得承载真实宿主事实（路径 / 端口 / 二进制位置 / 运行时版本 / 本地恢复细节）。因此本表用占位符表达**档案的形状**；真实值只写在 **local-only** 的 `deployment/deployment-profile.local.md`（已被 `.gitignore` 忽略，永不入库）。
> 校验入口：`python3 scripts/validate_public_release.py`（CURRENT_TREE_SCAN，PUBLIC 模式拒绝真实值）。
> 私有仓如需保留 designated machine-recovery 语义，见 RULES.md R2 与 `scripts/validate_public_release.py` 顶部威胁模型。
> 不属于 RULES，不属于任何仓的产品语义（RULES R7）。

## 占位符约定

| 占位符 | 含义 | 示意（非本机事实） |
|---|---|---|
| `<HOST_OS>` | 宿主操作系统 | `macOS (darwin)` / `Windows` / `Linux` |
| `<PATH_TO_GH>` + `<VERSION>` | gh CLI 绝对路径与版本 | `/usr/local/bin/gh` `2.x` |
| `<PATH_TO_CODEGRAPH>` + `<VERSION>` | CodeGraph 可执行文件与版本 | `${HOME}/.local/bin/codegraph` `1.x` |
| `<LOCAL_PROXY_URL>` | 出网代理端点（该机器若存在） | `http://127.0.0.1:<port>` |
| `${HOME}` | 宿主 HOME 的可移植写法 | `${HOME}/.workbuddy/` |
| `<MEMORY_INJECTION_BUDGET_BYTES>` | 平台自动注入记忆的截断点 | `4028` |

规则：一律写 `<UPPER_SNAKE>` 或 `${HOME}`；**禁止**写入具体用户名、具体 HOME 绝对路径、具体监听端口、具体运行时版本。

## 档案模板（复制后填真实值，仅存 local-only 文件）

| 项 | 模板值 | 性质 |
|---|---|---|
| 宿主 OS | `<HOST_OS>` | FACT |
| shell 基线 | `<SHELL>`；UTF-8 | FACT |
| gh CLI | `<PATH_TO_GH>`（`<VERSION>`；认证 `<GITHUB_ACCOUNT>`） | FACT |
| git | `<VERSION>`；credential = gh auth git-credential | FACT |
| 出网代理 | `<LOCAL_PROXY_URL>`（显式 `HTTPS_PROXY` 注入，无持久配置） | FACT |
| WorkBuddy 数据目录 | `${HOME}/.workbuddy/`（MEMORY/mcp.json/skills/settings） | FACT |
| CodeGraph | `<PATH_TO_CODEGRAPH>`（→ `<VERSION>`）；MCP serve 已配置 | FACT |
| MEMORY 注入预算 | 实测截断点 `<MEMORY_INJECTION_BUDGET_BYTES>` bytes | FACT（机制层面 UNKNOWN） |

## 本地档案（local-only，禁止入库）

真实机器档案路径：

```
deployment/deployment-profile.local.md
```

- 已被 `.gitignore` 忽略；生成/更新后用 `git status --ignored` 确认它从未进入暂存区。
- 用途 = 本机恢复与环境复现；可含真实路径 / 端口 / 版本。
- **仍然绝对禁止**写入：凭据、secret、私钥、cookie / auth header、真实 `~/.workbuddy/mcp.json`。
- 备份走 Git 之外的私有存储（与 `deployment/BOOTSTRAP_CONTRACT.md` 的旧 MEMORY local-only 备份政策一致）。

## 跨平台说明

- 模板中的 `<HOST_OS>` 取值**不构成**对任何仓库的目标平台约束：任何目标平台完全合法（RULES R7）。
- 历史 Windows/PowerShell 治理材料分类：`WINDOWS_PORTABILITY_REFERENCE`。
