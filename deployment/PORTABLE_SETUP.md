# PORTABLE_SETUP — 新 Agent 入口（AGENT_ENGINEERING_GOVERNANCE_V1.1.1）

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
15. **运行治理校验**：`python3 scripts/validate_governance.py`（本仓内）——要求全部检查 PASS（以运行时输出为准）。
16. **输出 bootstrap receipt**（下方 schema）给用户/编排者。
17. **开始工程工作**：按 AGENTS.md 生命周期执行；授权路径自主推进，只在 §7 STOP 状态停机。

## 项目状态恢复（STATE_RESTORE）

进入**既有项目**（非本仓）时，禁止以"请人讲历史"开局：fetch remote → 读仓本地权威 → 读 TARGET/SPEC/ADR/SPIKE → 检视 open Issues/PRs/tracker → exact branch SHAs → CI/评审状态 → 重构合法 frontier。输出恢复回执（字段与协议见 `references/project-state-persistence.md` §5）：

```text
PROJECT =
REMOTE_DEFAULT_SHA =
TARGET = SPEC = ADR = SPIKES =
ACTIVE_STAGE = ACTIVE_TICKETS = ACTIVE_PRS =
BLOCKERS = DECISIONS_REQUIRED =
CURRENT_LEGAL_FRONTIER =
STATE_RECOVERY = COMPLETE / PARTIAL / BLOCKED
READY_TO_CONTINUE = YES / NO
```

GitHub/仓内证据足够时不要求用户复述历史；授权已明确则自动继续。自己**离开**会话前执行 STATE_FLUSH（见同 reference §6）：问"下一个 fresh Agent 需要什么而它只存在于我的 context？"并持久化。

## 项目连续性合同（PROJECT_CONTINUITY_CONTRACT_V1）

目标仓根有 `.agent/project-state.json` 即为 PROJECT_CONTINUITY_CONTRACT 入口——**先读它**（pointers + recovery snapshot），再按其指向的 canonical 文档与 GitHub 控制平面完成恢复。缺失：既有仓 **lazy adoption**（discover → index → point，不重写历史），新仓在第一次 meaningful implementation 前 bootstrap；自动执行、不问用户。CodeGraph code 仓 `INIT_ONCE_SYNC_CONTINUOUSLY`，runtime-local dirty 状态绝不 commit。全文/schema/template/validator：`references/project-continuity-contract.md`、`schemas/`、`templates/`、`scripts/validate_project_state.py`。

## 环境能力矩阵（Environment Capability Matrix）

> 新 Agent 开工前对目标环境逐行盘点并按此 schema 回报；语言特定工具**由目标仓决定**（`USE_REPOSITORY_NATIVE_STATIC_TOOLING_FIRST`），不全局要求任何语言栈。原始机实测值见 `audit/PORTABILITY_HARDENING_EVIDENCE.md`。

| CAPABILITY | STATUS（回报值） | SOURCE（可能来源） | VERIFY | FALLBACK | BLOCKING? |
|---|---|---|---|---|---|
| Git | USER_CONFIGURED / MISSING | 本机 git | `git --version` | 无（硬前提） | **YES** |
| GitHub access | USER_CONFIGURED / OPTIONAL | gh CLI 或平台 connector | `gh auth status` / PR API 试读 | 仅本地工作（remote gate 降级并如实报告） | 远程操作 YES |
| CodeGraph | USER_CONFIGURED / MISSING | `~/.local/bin/codegraph` + MCP 配置 | `codegraph --version` + `status` | MODE C（MEDIUM 直接降级；HIGH = ENHANCED_MANUAL_GROUNDING + ESCALATION，HARD STOP 仅三种条件，见 codegraph-grounding §4） | 非普适硬 gate（如实标注 UNAVAILABLE） |
| LSP | PLATFORM_PROVIDED / ABSENT | 平台内置 LSP 工具 + 目标仓语言服务器 | 对目标仓符号执行 go-to-def/references | 源码阅读 + CodeGraph | NO（降级） |
| AST / static-query | PLATFORM_PROVIDED 或 REPOSITORY_PROVIDED | CodeGraph 符号查询；仓内语言工具 | 对已知符号执行结构查询 | grep（标注非结构证明） | NO |
| formatter / linter | REPOSITORY_PROVIDED | 仓 package/lint 配置 | 跑仓配置的命令 | 无——不注入仓外工具链 | NO（但仓有配置则为该仓 gate） |
| type checker / compiler | REPOSITORY_PROVIDED | 仓构建配置 | 跑仓配置的命令 | 无 | 该仓 gate YES |
| test runner | REPOSITORY_PROVIDED | 仓 package/test 配置 | 跑仓测试命令 | 无——测试 gate 不可豁免 | **YES**（适用 gate） |
| canonical Skills | INSTALLED / PARTIAL / MISSING | 平台 skill registry / `~/.workbuddy/skills/` | 定位各 `SKILL.md` | skills/README.md 各行 FALLBACK | NO（如实标注 SKILL_UNAVAILABLE） |
| canonical MCP（codegraph/context7/gh_grep） | READY / PARTIAL | mcp/README.md INSTALL 方法 | 各一次健康查询 | 降级如实报告（context7/gh_grep 非阻断；codegraph 见上） | codegraph HIGH 票 YES |
| CI access | AVAILABLE / ABSENT | GitHub Actions（governance-ci；仓级 CI） | `gh run list` | 仓政策等价证据形态（OVERRIDE 记录） | MEDIUM+ remote YES |

语言示例：TypeScript 仓 → tsserver/tsc/eslint（若仓配置）；Python 仓 → pyright/mypy/ruff/pytest（仅当仓配置实际使用）。**绝不注入无关工具链。**

## Bootstrap Receipt（回执 schema，≤20 行）

```text
GOVERNANCE_SOURCE = <repo url / local path>
GOVERNANCE_VERSION = AGENT_ENGINEERING_GOVERNANCE_V1.1.1 (<git sha if available>)
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
CAPABILITIES = <git/lsp/ast/formatter/linter/typecheck/test-runner/CI: per capability matrix, blocking gaps flagged>

BOOTSTRAP = GOVERNANCE_POINTER_MISSING / COMPLETE
READY_FOR_ENGINEERING = YES / NO (+ reason)
```

## 边界

- 本文件是**入口指引**，不是新权威层；冲突裁决永远回到 `audit/AUTHORITY_MAP_V2.md` 算法。
- 本仓不是第三方工具的分发渠道（D1/D2）：skill/MCP 的实际内容一律从其 canonical 来源获取。
- live WorkBuddy 部署（MEMORY 指针替换）不在本 setup 路径内——见 BOOTSTRAP_CONTRACT 的受控部署前置条件。
