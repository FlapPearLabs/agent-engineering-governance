# agent-engineering-governance

> **状态：CANDIDATE V2（未激活）。** 承载 FlapPearLabs 全局 agent 工程治理的 AUDIT 与 CANDIDATE。
> 分支 `audit/workbuddy-global-governance-v1-2026-09-05` = 送外部评审的候选；main 保持最小。
> V2 = 修复 GPT-5.6 Sol 首轮评审 F1–F7 后的候选（修复包见 `audit/AUDIT_QUALITY_REVIEW.md` 与各 V2 文档）。

## 1. 为什么存在

现行全局工程治理的全部权威寄宿在一份 29.8KB 的 WorkBuddy 记忆文件里，而该文件的会话注入在 **byte 4028** 截断 —— 宪法的大部分（含三大 OVERRIDE）对 agent 实际不可见；同时项目仓各自手写 800+ 行 AGENTS.md，语义重复且漂移。本仓库把"治理内容"与"治理载体"解耦：**这里只有一个 canonical owner**，其他位置只留指针或项目 delta。

## 2. 权威模型（V2，修复 F1）

```
A  PLATFORM / SYSTEM        平台/系统/沙箱/工具契约 —— 不可覆盖
B  UNIVERSAL INVARIANTS     RULES.md（薄：凭据/证据/评审独立/历史完整/机器卫生）—— 任何仓不得削弱
C  REPOSITORY-LOCAL         仓 RULES/AGENTS、Approved Specs、仓 merge/CI 政策、ticket 授权
D  GLOBAL DEFAULT WORKFLOW  AGENTS.md + references/（风险分级、Stage/Lane、评审收敛、CodeGraph、报告）
E  METHODS / TOOLS          skills / MCP / 脚本 —— 方法不产生权威
F  MEMORY / PREFERENCES     指针 + 偏好 + 环境事实 —— 永不压倒契约
```

- **C 层显式政策可覆盖 D 层全部默认**（如仓选 squash-merge、无 CI 基础设施的等价证据形态）；加严永远合法；覆盖必须记录 `OVERRIDE = ...`。
- 不可解析的真实冲突 → STOP: CONTRACT_CONFLICT。
- 详细层表与冲突算法：`audit/AUTHORITY_MAP_V2.md`。

## 3. 仓库内容

| 路径 | 内容 |
|---|---|
| `AGENTS.md` / `RULES.md` | 候选全局执行架构 / 普适硬不变量（B 层，薄） |
| `references/*.md` | execution-stage / ticket-lane / review-and-repair-saturation / git-ci-integration / codegraph-grounding / skills-and-model-routing（D 层默认，含真实工具能力校准） |
| `audit/*.md` | V1 审计 + V2 再审计：AUDIT_QUALITY_REVIEW、AS_IS_WORKBUDDY(_V2)、TARGET_WORKFLOW_V1、WORKFLOW_EVOLUTION_MAP、GAP_MATRIX、PAIN_TO_POLICY_MAP(_V2)、AUTHORITY_MAP(_V1/_V2)、MIGRATION_PLAN、SCENARIO_VALIDATION、TARGET_ARCHITECTURE_CHALLENGE |
| `deployment/` | BOOTSTRAP_CONTRACT、MEMORY_POINTER_CANDIDATE（≤3,500 字符）、deployment-profile（机器事实） |
| `scripts/` | validate_governance.py（治理自检 harness） |
| `skills/` | skill 治理政策与 manifest（**REPRODUCIBILITY=INCOMPLETE → deployment 受阻**） |
| `mcp/` | MCP 意图治理 + example 配置（占位符，无 secrets） |

## 4. Bootstrap（如何被新会话看到；F2 修复）

- 已验证：`~/.workbuddy/MEMORY.md` 头部是唯一自动注入通道（截断点 byte 4028）；项目 AGENTS/RULES **无**自动加载证据。
- 机制 = `deployment/BOOTSTRAP_CONTRACT.md`：MEMORY 指针候选（自动可见层）+ 会话开工 BOOTSTRAP_CHECKLIST（B1–B5，产出引导回执）+ `scripts/validate_governance.py` 机械自检。
- 显式声明：自动加载项目 AGENTS/RULES 目前不可保证 —— 以清单步骤补足，并以 fresh-session 验收协议（§3 of contract）验证。

## 5. SOURCE-OF-TRUTH vs MACHINE-SPECIFIC vs 禁止提交

- **SOURCE-OF-TRUTH（本仓）**：全部治理语义。
- **MACHINE-SPECIFIC**：宿主路径、代理端口、gh 位置、凭据通道 → `deployment/deployment-profile.md` + `mcp/README.md` §MACHINE_SPECIFIC；治理文件使用 `${HOME}` 类占位。
- **NEVER COMMIT**：API key、token、cookie、auth header、SSH 私钥、secret 环境变量、凭据文件路径、真实 `~/.workbuddy/mcp.json`。
- 审计证据路径一律 home 相对（`~/...`），无用户名。

## 6. 当前流程状态

```
V1 审计 + 候选（e5a4871）
→ GPT-5.6 Sol 外部评审：CHANGES_REQUESTED（F1–F7）
→ 再审计（AUDIT_QUALITY_REVIEW + 四个冻结 V2 文档）
→ V2 修复（本状态）：append-only commits
→ STOP：等待外部 fresh 评审
→ APPROVE 后：仍受阻两项 —— skills manifest 补齐（source/commit/license）+ MEMORY 指针部署（product owner 授权）
→ 按 MIGRATION_PLAN 分批部署
```

本分支合并前、候选文件激活前、任何 live 配置改动前，都需要 product owner 明确授权。
