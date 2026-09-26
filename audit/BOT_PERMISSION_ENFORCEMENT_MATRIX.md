# Bot Permission Enforcement & Boundary Matrix

**Audit Standard**: Zero-Illusion Security & Permission Enforcement (V2.1 Hardening)  
**Host Context**: macOS (Darwin) Single-User Desktop Environment  

---

## 1. 概念与边界诚实界定 (Security Boundary Clarification)

在本次 V2.1 修复中，彻底消除任何“虚假安全背书”：

- **Hermes Profile 隔离的本质**：
  提供的是 **STATE & CONTEXT ISOLATION（状态与上下文隔离）**。它在文件系统层将配置、记忆库、会话历史、数据库和特定工具配置隔开。
- **它不是 OS-Level Security Sandbox（操作系统级安全沙盒）**：
  只要运行 Hermes 的宿主进程具备当前用户的 shell/terminal 权限，如果模型出现提示词越狱或调用了系统级执行工具，宿主系统并无 Docker 容器或 macOS AppSandbox 做物理拦截。
- **强制规则分类**：
  - `RUNTIME_ENFORCED`：通过工具白名单（Tool Allow-list）、缺失配置（No Credentials）、进程只读挂载或硬件环境真正阻断的能力。
  - `POLICY_ENFORCED_ONLY`：通过 System Prompt / SOUL / AGENTS 规则约束模型不调用或拒绝执行，但在技术上有潜在调用途径。

---

## 2. 真实权限与安全边界矩阵 (Updated R06 Dual-Dimension Matrix)

### 2.1 维度一：Automatic Profile State Injection (Hermes 运行时自动注入隔离)
| Profile | 自动注入隔离能力 | 技术可用性 (Technically Available?) | 政策允许 (Policy Allowed?) | 强制类型 (Enforcement Type) | 证据 (Evidence) | 残留风险 (Residual Risk) |
|---|---|---|---|---|---|---|
| `all` | 跨 Profile 记忆/会话/配置自动混杂 | NO | NO | **PROFILE_RUNTIME_ROUTING** | Hermes Profile 架构将 `HERMES_HOME`、`memories/`、`state.db` 独立寻址 | 极低（仅在显式传入 `--profile` 切换时由用户或运行时路由） |

### 2.2 维度二：Cross-Profile Filesystem Confidentiality (宿主机文件系统访问保密性)
| Bot | 能力项 (Capability) | 技术可用性 (Technically Available?) | 政策允许 (Policy Allowed?) | 强制类型 (Enforcement Type) | 证据 (Evidence) | 残留风险 (Residual Risk) |
|---|---|---|---|---|---|---|
| `markets` | 外部券商/交易所写入下单 | NO | NO | **RUNTIME_ABSENT** | 零交易工具接入；零 API Key 配置 | 无（物理不可执行） |
| `markets` | 本地终端/文件系统越权修改 | YES (宿主用户权限) | NO | **POLICY_ENFORCED_ONLY** | 工具集未绑定 OS 级 chroot/jail | 中（若模型越狱调用底层 shell 技术上可读写同账户文件） |
| `code` | 读取其他 Profile 目录数据 | YES (宿主用户权限) | NO | **OS_NOT_ISOLATED** | 进程以当前 macOS 用户运行，系统级读权限存在 | 中（依赖工程治理与 SOUL Scope 约束，无 UID 隔离） |
| `reviewer`| 生产代码修改/提交/合并 | YES (若拥有 shell) | NO | **POLICY_ENFORCED_ONLY** | Subagent Prompt 约束；git-guardrails 拦截 | 低（依赖隔离会话与 Hook 拦截，非容器只读挂载） |
| `code` | Git Force Push 破坏历史 | YES (网络与 git) | NO | **POLICY_ENFORCED_ONLY** | 本地 git-guardrails active；规范严禁 | 低（依赖 Hook 拦截，若直连 git 可能触发） |


---

## 3. 审查员结论 (Auditor Takeaway)
任何宣称卫星 Bot 具备“操作系统级安全物理隔离”或“严格只读运行时硬沙盒”的说法均为伪命题。当前系统通过 **Profile 状态隔离 + 金融凭据物理缺失 + Git Guardrails 钩子拦截 + SOUL 行为契约** 构筑了多层纵深防御，但底层安全边界严格属于 **POLICY_ENFORCED**。审计结论诚实定性，无任何过度包装。
