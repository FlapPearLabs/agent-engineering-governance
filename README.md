# agent-engineering-governance

> **AGENT_ENGINEERING_GOVERNANCE_V1.1.1 — CANONICAL** —— FlapPearLabs 全局工程治理基线（external verdict: `PASS_WITH_DEPLOYMENT_BLOCKERS` → V1 架构 `PASS`，核心治理已通过并合并）。
>
> - `GOVERNANCE_CORE = PASS`（GPT-5.6 Sol 多轮评审收敛；权威分层/Stage/Lane/风险分级/评审收敛/CI/exact-SHA/Seam-first 均已接受）
> - `PORTABLE_SETUP = READY`（见 `deployment/PORTABLE_SETUP.md`）
> - `BOOTSTRAP_STATIC_VALIDATION = PASS`（指针预算 ≤3,500 vs 实测截断 4028；governance-ci green；自检以 `python3 scripts/validate_governance.py` 全部 PASS 为准）
> - `BOOTSTRAP_LIVE_VALIDATION = NOT_RUN`（fresh-session 验收待受控部署后执行——唯一遗留部署事项，非 V1.1.1 阻塞）
>
> V1.1.1 是 canonical 工程治理基线；后续变更是正常版本化演进。`audit/` 全部为**历史证据**，不是 runtime 权威；**canonical runtime 权威 = `RULES.md` + `AGENTS.md` + `references/` + `deployment/` setup 文档**。

## 1. 新 Agent 入口

**`deployment/PORTABLE_SETUP.md`** —— 17 步：读权威 → 调和权威（六层算法）→ 检查/获取 Skills（canonical upstream）→ 检查/获取 MCP（codegraph/context7/gh_grep）→ 验证 → 输出 bootstrap receipt → 开工。本仓**不 vendor** 任何第三方工具内容。

## 2. 为什么存在

现行全局工程治理的全部权威曾寄宿在一份 29.8KB 的 WorkBuddy 记忆文件里，而该文件的会话注入在 **byte 4028** 截断 —— 宪法的大部分（含三大 OVERRIDE）对 agent 实际不可见；同时项目仓各自手写 800+ 行 AGENTS.md，语义重复且漂移。本仓库把"治理内容"与"治理载体"解耦：**这里只有一个 canonical owner**，其他位置只留指针或项目 delta。

## 3. 权威模型（六层）

```
A  PLATFORM / SYSTEM        平台/系统/沙箱/工具契约 —— 不可覆盖
B  UNIVERSAL INVARIANTS     RULES.md（薄：凭据/证据/评审独立/历史完整/机器卫生）—— 任何仓不得削弱
C  REPOSITORY-LOCAL         仓 RULES/AGENTS、Approved Specs、仓 merge/CI 政策、ticket 授权
D  GLOBAL DEFAULT WORKFLOW  AGENTS.md + references/（风险分级、Stage/Lane、评审收敛、CodeGraph、报告）
E  METHODS / TOOLS          skills / MCP / 脚本 —— 方法不产生权威
F  MEMORY / PREFERENCES     指针 + 偏好 + 环境事实 —— 永不压倒契约
```

- **C 层显式政策可覆盖 D 层全部默认**（记录 `OVERRIDE = ...`）；加严永远合法。
- 不可解析的真实冲突 → STOP: CONTRACT_CONFLICT。详细层表与冲突算法：`audit/AUTHORITY_MAP_V2.md`。

## 4. 仓库内容

| 路径 | 内容 |
|---|---|
| `AGENTS.md` / `RULES.md` | 执行架构（含 ENGINEERING DOCTRINE 十原则）/ 普适硬不变量（B 层） |
| `references/*.md` | execution-stage / ticket-lane / review-and-repair-saturation / git-ci-integration / codegraph-grounding（含 Mode A/B/C 探针证据）/ skills-and-model-routing |
| `deployment/PORTABLE_SETUP.md` | **新 Agent 17 步入口 + bootstrap receipt** |
| `deployment/` 其余 | BOOTSTRAP_CONTRACT（static PASS / live NOT_RUN）、MEMORY_POINTER_CANDIDATE、deployment-profile（designated 机器事实） |
| `skills/README.md` | 主线 13 skill 获取指南（SOURCE/FALLBACK，不 vendor 源码） |
| `mcp/README.md` | REQUIRED MCP 三项（元数据字段≠工具）+ PLATFORM CONNECTORS（github=OPTIONAL；agent-mail 非 canonical） |
| `scripts/validate_governance.py` | 治理自检（CI 接入 `.github/workflows/governance-ci.yml`） |
| `audit/` | 历史证据：AS-IS/演化/GAP/PAIN/AUTHORITY/MIGRATION/场景对抗/质量复核（**非 runtime 权威**） |

## 5. SOURCE-OF-TRUTH vs MACHINE-SPECIFIC vs 禁止提交

- **SOURCE-OF-TRUTH（本仓）**：全部治理语义。
- **MACHINE-SPECIFIC（RULES R2 第二层）**：宿主路径/端口/二进制位置仅允许出现在 `deployment/` 下带 `MACHINE-SPECIFIC ALLOWED` 标记的 designated 文件；**raw 旧 MEMORY 备份 local-only（Git 之外）**，仓内只收 sanitized/redacted 迁移快照。
- **NEVER COMMIT（R2 第一层，任何位置）**：凭据/secret/私钥/cookie/auth header/local OS identity、真实 `~/.workbuddy/mcp.json`。
- 校验器双层扫描强制执行（凭据/local-identity 全库；machine 模式限非 designated）。

## 6. 状态与后续

```
AGENT_ENGINEERING_GOVERNANCE_V1.1.1 —— CANONICAL（本版；closure patch 完成状态矛盾清理与 skill 溯源验证）
→ 下一步：fresh-agent full-fidelity dogfood（仅凭 PORTABLE_SETUP 重建环境 + bootstrap receipt）
→ 遗留部署事项（非 V1.1.1 阻塞）：BOOTSTRAP_LIVE_VALIDATION（受控部署后）；
  MEMORY 指针部署按 BOOTSTRAP_CONTRACT §2.1 前置条件执行
→ 后续变更 = 正常版本化演进（治理变更评审协议，AGENTS §8）
```
