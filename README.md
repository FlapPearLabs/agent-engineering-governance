# agent-engineering-governance

> **状态：CANDIDATE（未激活）。** 本仓库承载 FlapPearLabs 全局 agent 工程治理的 AUDIT 与 CANDIDATE 产物。
> 分支 `audit/workbuddy-global-governance-v1-2026-09-05` 是送外部评审（GPT-5.6 Sol）的候选快照；main 在获批前保持最小。

## 1. 为什么存在

现行全局工程治理的全部权威寄宿在一份 29.8KB 的 WorkBuddy 记忆文件里，而该文件的会话注入存在 ~4K 截断 —— 宪法的大部分（含三大 OVERRIDE）对 agent 实际不可见；同时项目仓各自手写 800+ 行 AGENTS.md，语义重复且漂移。本仓库把"治理内容"与"治理载体"解耦：**这里只有一个 canonical owner**，其他位置只留指针或项目 delta。

## 2. 权威模型（获批后的目标态）

```
RULES.md            硬规则（违反即 STOP）
  > AGENTS.md        执行架构（角色/Stage/Lane/评审/收敛/CI/推进）
  > references/      机制细节（6 篇，单一主题）
  > skills/ + mcp/   执行方法与工具治理（不产生权威）
  > MEMORY（≤4KB）    用户偏好、环境事实、指向本仓的指针
  > 项目 AGENTS/RULES 项目合同与 delta（可加严，不得弱化）
  > runtime memory   non-authoritative
```

主题 → 唯一 owner 分配表：`audit/AUTHORITY_MAP_V1.md` §2。

## 3. 仓库内容

| 路径 | 内容 |
|---|---|
| `AGENTS.md` / `RULES.md` | 候选全局执行架构 / 硬规则 |
| `references/*.md` | execution-stage / ticket-lane / review-and-repair-saturation / git-ci-integration / codegraph-grounding / skills-and-model-routing |
| `audit/*.md` | AS_IS_WORKBUDDY / TARGET_WORKFLOW_V1 / WORKFLOW_EVOLUTION_MAP / GAP_MATRIX / PAIN_TO_POLICY_MAP / AUTHORITY_MAP_V1 / MIGRATION_PLAN / SCENARIO_VALIDATION |
| `skills/` | skill 治理政策与清单（不 vendor 第三方内容） |
| `mcp/` | MCP 意图治理 + example 配置（占位符，无 secrets） |

## 4. 部署机制（诚实版）

WorkBuddy 的**实际**加载行为（2026-09-05 实测）：

- 自动注入：`~/.workbuddy/MEMORY.md`（**~4K 截断**）、身份四件套（SOUL/IDENTITY/USER/BOOTSTRAP）、skills 清单。
- **不**自动注入：全局/项目 `AGENTS.md`、`RULES.md` —— 它们依赖 bootstrap 纪律与技能提示被读取（zhihu 仓 AGENTS.md §2 的"缺失即 STOP"就是为此设计）。

因此部署配方（获批后执行，见 audit/MIGRATION_PLAN.md）：

1. `~/.workbuddy/MEMORY.md` 改写为 ≤4KB 指针文件：指向本仓 canonical 文件 + 用户偏好 + 环境事实；
2. 各产品仓安装项目级 `AGENTS.md`/`RULES.md`（全局骨架引用 + 项目 delta + 项目 Spec 权威），bootstrap 检查清单保持"缺失即 STOP"；
3. 本仓 = 唯一可评审的治理真源；治理变更走 PR + 双评审 quorum。

## 5. SOURCE-OF-TRUTH vs MACHINE-SPECIFIC vs 禁止提交

- **SOURCE-OF-TRUTH（本仓）**：全部治理语义。
- **MACHINE-SPECIFIC（不进 canonical 文件）**：本机路径、代理端口、gh 安装位置、凭据通道 → 归档在 `mcp/README.md` §MACHINE_SPECIFIC 与 MEMORY 环境区，使用 `${HOME}` 类占位。
- **NEVER COMMIT**：API key、token、cookie、auth header、SSH 私钥、secret 环境变量、凭据文件路径、真实 `~/.workbuddy/mcp.json`（含机器路径/潜在敏感值——只提交 `mcp/example/mcp.example.json`）。
- 审计证据中的路径一律 home 相对（`~/...`），已去用户名。

## 6. 当前流程状态

```
AUDIT + CANDIDATE 完成（本分支）
→ STOP：外部治理评审（GPT-5.6 Sol）
→ findings 返回 → REPAIR → VALIDATION → FRESH GOVERNANCE REVIEW
→ 批准 → 按 MIGRATION_PLAN 分批部署
```

本分支合并前、候选文件激活前、任何 live 配置改动前，都需要 product owner 明确授权。
