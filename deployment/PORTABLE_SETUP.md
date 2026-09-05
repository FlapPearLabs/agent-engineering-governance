# PORTABLE_SETUP — 新 Agent 入口（V1）

# I AM A NEW AGENT. WHAT DO I DO?

> 你只需要本仓 + 目标工程仓。不依赖任何先前对话。按顺序执行；每步失败按该步的降级路径如实报告，不伪造。

1. **clone / open 本治理仓**（FlapPearLabs/agent-engineering-governance）。
2. **读 README.md** —— 仓库目的、版本状态、权威模型速览。
3. **读 RULES.md** —— B 层普适不变量（8 条，含验证钩子）。
4. **读 AGENTS.md** —— ENGINEERING DOCTRINE + 执行架构（Stage/Lane/评审/收敛/CI/推进/STOP）。
5. **发现目标工程仓本地权威**：目标仓根 `AGENTS.md` / `RULES.md` / `docs/specs/*`，存在即读。
6. **按 `audit/AUTHORITY_MAP_V2.md` 调和权威**：A 平台 > B 不变量 > C 仓权威 > D 全局默认 > E 方法 > F 记忆；C 对 D 的覆盖必须显式记录 `OVERRIDE = ...`；不可解析冲突 → STOP: CONTRACT_CONFLICT。
7. **检查所需 Skills**：`skills/README.md` 主线 13 项（grill-with-docs / to-spec / to-tickets / implement / tdd / code-review / review-agent / diagnosing-bugs / resolving-merge-conflicts / writing-plans / subagent-driven-development / simplify-code / handoff）。
8. **获取缺失 Skills**：按该表 SOURCE/FALLBACK —— 定位本机已装 `SKILL.md` 或平台 skill registry；**本仓不含第三方 skill 源码，勿在此找**。
9. **检查所需 MCP**：`mcp/README.md` #REQUIRED MCP —— 仅 codegraph / context7 / gh_grep 三项；平台连接器不是 MCP。
10. **获取/启用缺失 MCP**：按该表 INSTALL/ENABLE 方法与 `example/mcp.example.json` 模板。
11. **不从本仓导入 secrets**：本仓无凭据；真实凭据/机器私有值永不在 Git。
12. **验证 CodeGraph / Context7 / gh_grep**：各完成一次健康查询（codegraph：`--version` + 仓库内 `status`；两个远程 MCP：任一查询成功）。
13. **识别当前 runtime/平台**：读 `deployment/deployment-profile.md`（designated 机器事实）。
14. **只应用适用的 deployment profile**：档案是宿主事实记录，不是规则（RULES R7）；目标仓平台与宿主无关。
15. **运行治理校验**：`python3 scripts/validate_governance.py`（本仓内）——10 项机械检查。
16. **输出 bootstrap receipt**（下方 schema）给用户/编排者。
17. **开始工程工作**：按 AGENTS.md 生命周期执行；授权路径自主推进，只在 §7 STOP 状态停机。

## Bootstrap Receipt（回执 schema，≤20 行）

```text
GOVERNANCE_SOURCE = <repo url / local path>
GOVERNANCE_VERSION = AGENT_ENGINEERING_GOVERNANCE_V1 (<git sha if available>)
RULES_LOADED = YES/NO (8 rules)
AGENTS_LOADED = YES/NO (doctrine + architecture)

REPOSITORY_AUTHORITY = <target repo: AGENTS/RULES/SPECS found or NONE>
OVERRIDES = <explicit C-over-D override records or NONE>

SKILLS = <present count>/13: <names>
MISSING_SKILLS = <names + fallback applied or NONE>

MCP = codegraph/context7/gh_grep ready?
MISSING_MCP = <names + degraded mode or NONE>

CODEGRAPH = MODE_A / MODE_B / UNAVAILABLE
PLATFORM_CONNECTORS = <github optional connector available YES/NO; others NONE>

BOOTSTRAP = GOVERNANCE_POINTER_MISSING / COMPLETE
READY_FOR_ENGINEERING = YES / NO (+ reason)
```

## 边界

- 本文件是**入口指引**，不是新权威层；冲突裁决永远回到 `audit/AUTHORITY_MAP_V2.md` 算法。
- 本仓不是第三方工具的分发渠道（D1/D2）：skill/MCP 的实际内容一律从其 canonical 来源获取。
- live WorkBuddy 部署（MEMORY 指针替换）不在本 setup 路径内——见 BOOTSTRAP_CONTRACT 的受控部署前置条件。
