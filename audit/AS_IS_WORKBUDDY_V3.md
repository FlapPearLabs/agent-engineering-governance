# AS_IS_WORKBUDDY_V3 — 描述性冻结（无建议、无目标）

> 每条陈述标注 **FACT / INFERENCE / UNKNOWN**。本文只回答：什么存在、什么加载、什么不加载、什么被截断、什么是项目级 / 全局 / 机器私有、什么是未知的。
> 观测日 **2026-09-27**；观测者 = WorkBuddy 会话（只读探针）。核心机制证据另经**重跑复核**于 2026-09-27（同一 App 包）。
> 与 V2 的关系：`audit/AS_IS_WORKBUDDY_V2.md` 冻结于 2026-09-05 且 `AS_IS_FROZEN = YES`，**本文不改动它**；本文是同一主题的**重新取证**，用于关闭 V2 明确列为 UNKNOWN 的条目。
> `AS_IS_FROZEN = YES`（基于本文件事实层）。

## 0. 观测 profile

- FACT：WorkBuddy `CFBundleShortVersionString = 5.5.3`（`/Applications/WorkBuddy.app/Contents/Info.plist`）。
- FACT：`/Applications/WorkBuddy.app/Contents/Resources/app.asar` = 296,738,763 bytes，mtime 2026-09-04，
  sha256 `f9a3803e32a1832e3041a187aae338e1f13c4c2cce0417718225f1707a4c0b9e`。
- FACT：内置 agent CLI bundle = `app.asar.unpacked/cli/dist/codebuddy.js`（22 MB，mtime 2026-09-04），
  同目录 `codebuddy-headless.js`（19 MB）。CLI 自带文档树 `cli/dist/web-ui/docs/cn/cli/*.md`（hooks / sub-agents /
  skills / memory / permissions / worktree / permissions-modes / workflows / goal / security 等）。
- 边界：本节一切结论**绑定该 profile**；版本变更必须重新取证，不得当作跨版本常数。

## 1. 首轮引导注入机制（V2 §10 UNKNOWN #1 的关闭）

- FACT（逐字提取自 app.asar，`packages/workbuddy-server/src/prompts/user/sections/project-context-section.ts`）：

```js
var GUIDANCE_FILES = ["CODEBUDDY.md", ".codebuddy/CODEBUDDY.md", "AGENTS.md"];
var MAX_GUIDANCE_CHARS = 8e3;
...
const raw = await fs.readFile(target, "utf8");
return wrapXmlTextElement("project_guidance",
  `...File: ${target}\n${(raw.length > MAX_GUIDANCE_CHARS
      ? `${raw.slice(0, MAX_GUIDANCE_CHARS)}\n[...too long, omitted...]`
      : raw).trimEnd()}`);
```

- FACT：循环体内 `return`，故**取第一个存在者**（命中即止，不合并、不级联）。
- FACT：`MAX_GUIDANCE_CHARS = 8000`；计量 = `raw.length`，即 **JavaScript string length**，
  **不是** UTF-8 字节数（多字节文本下二者不相等）。
- FACT：截断语义 = 头部保留 + 尾部追加 `[...too long, omitted...]`；无结构化提示说明丢失了多少。
- FACT：`ProjectContextSection.stage = "first_turn"`；`shouldApply` 在 `alreadyInjectedUserContext === true` 时返回 false。
- FACT：注入根 = 输入 `cwd`（工作区根）；`<project_context>` 同时含 `<project_guidance>` 与 `<project_layout>`。
- FACT：`project_layout` 另有独立上限：`MAX_LAYOUT_ENTRIES = 40`、`MAX_SUBTREE_DEPTH = 6`、`MAX_TOP_EXTENSIONS = 5`。
- INFERENCE：`RULES.md` 不是 `GUIDANCE_FILES` 成员，因此**永不**经该通道自动到达；这一条不依赖任何会话观测。
- FACT（对照观测）：zhihu-grabber-toolkit 的 `AGENTS.md` @ `c462bbe4` = 36,943 bytes / **28,032 chars**。
  与该上限同语义计算 → 保留 8,000 chars（28.5%），**静默丢弃 20,032 chars（71.5%）**；截断点落在该文件 §3 中间，
  故 §3.1、§4（角色）、§5（评审 quorum）、§6、§7（exact-SHA 合并）、§8/§8.1（单活跃写者）、§9–§17、§18 全节
  （含 `/implement` 强制入口与 `/tdd`）均不进入首轮上下文。
- 边界（不得过度概括）：该截断**不等于**治理不可达。`AGENTS.md` §2（Bootstrap）落在保留区内，
  它要求 agent 每次开工完整读取 `AGENTS.md` / `RULES.md` / `project-memory`。
  故正确表述是四个分离的性质，而不是"只有 28.5% 治理可达"。
  **下列字段名与取值的规范声明点 = `deployment/BOOTSTRAP_CONTRACT.md` §1；本处只是引述其观测依据，
  不构成第二声明点，也不得被引用为 rule owner。**

```text
FIRST_TURN_AUTO_INJECTION_COVERAGE = PARTIAL
FULL_GOVERNANCE_REACHABILITY       = YES_IF_BOOTSTRAP_FOLLOWED
FULL_GOVERNANCE_AUTOMATIC_DELIVERY = NO
MECHANICAL_ENFORCEMENT             = PARTIAL
```

## 2. 用户级 / 项目级 / 机器私有通道（V2 §2 的复核与补充）

- FACT：App 启动时设 `process.env.CODEBUDDY_CONFIG_DIR = getWorkbuddyConfigDir()`；
  `getWorkbuddyConfigDir()` = `WORKBUDDY_CONFIG_DIR` 或 `~/.workbuddy`。
- FACT（cross-validation）：CLI 侧 `getHomeDir()` = `CODEBUDDY_CONFIG_DIR` 或 `~/.codebuddy`；
  `getHomeSkillsDir()` = `<home>/skills`、`getHomePluginsDir()` = `<home>/plugins`、`getLoggerDir()` = `<home>/logs`。
  机器上实测存在 `~/.workbuddy/skills`（192 项）、`~/.workbuddy/plugins`、`~/.workbuddy/logs`，
  故 WorkBuddy 会话内的 home = `~/.workbuddy`（**不是** `~/.codebuddy`）。
- FACT：`PathUtils.getSettingsFilePath(scope)`：`USER → join(getHomeDir(), SETTINGS_FILENAME)`；
  `PROJECT → <cwd>/.codebuddy/settings.json`；`PROJECT_LOCAL → <cwd>/.codebuddy/settings.local.json`。
  推论（INFERENCE，未做端到端实测）：WorkBuddy 的**用户级 settings = `~/.workbuddy/settings.json`**。
- FACT：`~/.codebuddy/settings.json` 存在且含一条 `hooks.UserPromptSubmit`（指向 `~/.codebuddy/hooks/task_auto_name_hook.py`）。
  该文件属于独立 CodeBuddy CLI 的配置面；在 WorkBuddy 会话内是否被读取**未证实**（UNKNOWN）。
- FACT：`~/.workbuddy/settings.json` 实测键 = `enabledPlugins / sandbox / claw / autoLaunchLegacyCleanerRanAt / dockRecentAppsRepairedAt`，
  **无 `hooks` 键**；`~/.workbuddy/hooks/` 不存在。即：该 profile 下 **WorkBuddy 会话未配置任何 hook**。
- FACT：`~/.workbuddy/MEMORY.md` = 1,804 bytes，mtime 2026-09-23；正文 = 治理指针
  （与 `deployment/MEMORY_POINTER_CANDIDATE.md` 的围栏内正文一致）。对照 V2 §1 记录的 29,810 bytes，
  即指针替换**已实际发生**（这正是 V2 §2「尾部三 OVERRIDE 因截断不可见」问题的解法落地）。
- FACT：会话注入的身份四件套（`SOUL/IDENTITY/USER/BOOTSTRAP.md`）仍为全文注入。
- UNKNOWN：MEMORY 注入预算的官方可配置性（`settings.json` 无相关字段，未见公开契约）。

## 3. Hook 能力面（V2 未覆盖）

- FACT：CLI bundle 含完整 hook 事件枚举：
  `PreToolUse / PostToolUse / PostToolUseFailure / Notification / UserPromptSubmit / SessionStart / SessionEnd / Stop / SubagentStart / SubagentStop / PreCompact / PermissionRequest / WorktreeCreate / WorktreeRemove`。
- FACT：执行链含 `executeHooks` / `getMatchingInternalHooks` / `findMatchingHooks` / `filterHooksByIfRule` /
  `deduplicateHooks` / `executeLocalHook`，结果聚合为 `{allowed}`。
- FACT：PreToolUse 支持 `hookSpecificOutput.permissionDecision = "allow" | "deny" | "ask"`；
  `"deny"` 判为 `blocking: true`，`permissionDecisionReason` 传给 agent。
- FACT：command hook 退出码语义 = `0` 成功 / `2` 阻塞错误（消息源 stdout 优先、stderr 仅 fallback）/ 其他为非阻塞错误；
  也可用 stdout JSON 的 `hookSpecificOutput` 表达决策。
- FACT：文档标注 hooks 为 **Beta**，接口可能调整。
- FACT：CLI 安全模型把「修改 `.codebuddy/settings*.json` / `CODEBUDDY.md` / `CODEBUDDY.local.md` /
  `.codebuddy/hooks/` / `.codebuddy/rules/` 等控制 agent 自身行为或权限的文件」列为 **Self-Modification** 类可疑行为；
  但同处**显式豁免**：「Editing `CODEBUDDY.md` or `CODEBUDDY.local.md` where the written content does not change
  permissions, authorizations, or auto-mode behaviour in any way — These edits are always allowed.」
- INFERENCE：因此"仓根新增 bootstrap 指针"属被显式允许的形态（内容不含权限/自动模式变更）；
  而"写 hook 配置"属 Self-Modification 类，**需要显式用户授权**才能实施——本治理仓的 `adapters/workbuddy/` 因此
  只提供**待部署产物 + INSTALL/VERIFY/ROLLBACK**，不自行接线。
- UNKNOWN：hook 配置在 WorkBuddy（相对独立 CodeBuddy CLI）中的**实际接线面**是否与 §2 的 `getSettingsFilePath` 推论一致；
  未有端到端 deny 观测。

## 4. 其他平台层

- FACT：WorkBuddy 原生提供 Agent 子代理工具、后台任务、worktree 任务（`~/WorkBuddy/Worktrees/<repo>/<branch>`，
  分支前缀 `workbuddy/`）。
- FACT：平台层沙箱 + 命令安全审计以**哈希链**（`prevHash` / `hash` / `sequence`）落盘于 `~/.workbuddy/audit-log/`，
  事件形如 `command-safety.sandbox-executed`（含 `decision`）。
- FACT：`~/.workbuddy/tasks/<sessionId>/` 存在会话级任务态；`~/.workbuddy/projects/<slug>/` 存在会话转录（`.jsonl`）。
- INFERENCE：会话转录在仓库之外，属 runtime working memory，按 `RULES.md` R2 与 AGENTS §1 为 non-authoritative。

## 5. 本文件关闭的 V2 UNKNOWN

```text
V2 §10.1  WorkBuddy 对工作区根 AGENTS.md 的处理（自动注入与否）
          -> CLOSED：自动注入，且被 MAX_GUIDANCE_CHARS 截断；RULES.md 不在清单内（本文件 §1）
V2 §2     项目仓 AGENTS.md/RULES.md 是否被注入（"本会话未注入，工作区为空目录，无法构成反例"）
          -> CLOSED：机制层已答，不再依赖会话观测（本文件 §1）
```

## 6. 仍未解决的 UNKNOWN（后续按需补证）

1. MEMORY 注入预算的官方数值与可配置性（§2）。
2. `GUIDANCE_FILES` / `MAX_GUIDANCE_CHARS` 在**未来版本**的稳定性。
3. hook 配置在 WorkBuddy 会话内的实际接线面，以及真实 deny 的端到端观测（§3）。
4. `~/.codebuddy/settings.json` 是否被 WorkBuddy 会话读取（§2）。
5. fresh-session 首轮注入的**直接观测**（`<project_guidance>` 的 `File:` 值 + 是否含 omitted 标记）——
   该观测需要与实现会话无关的全新会话，不能由同一上下文自证。

## 7. 部署验收记录（2026-09-27）

> 本节是**记录**，不是合同；合同层结论的唯一 owner = `deployment/BOOTSTRAP_CONTRACT.md`。
> 每项独立，引用时必须按字段取值，不得合并为一个笼统 PASS。

- FACT（MEMORY 指针已部署）：`~/.workbuddy/MEMORY.md` = 1,804 bytes（≤ BOOTSTRAP_CONTRACT §2.1 预算），
  正文与 `deployment/MEMORY_POINTER_CANDIDATE.md` 的 markdown 围栏内正文一致（仅差候选文件自身的说明头与围栏）。
  观测方式 = 字节计数 + 正文比对。
- FACT（工作区根 bootstrap 指针已交付）：`FlapPearLabs/zhihu-grabber-toolkit` 仓根新增 `CODEBUDDY.md`，
  以 ff-only 集成，remote master 已核验。
- FACT（尺寸）：该 `CODEBUDDY.md` = **3,443 JS chars**（UTF-8 4,886 bytes）；
  远低于运行时上限 8,000（§1）与仓侧安全上限 7,000 → `TRUNCATION_RISK = NONE`。
- FACT（交付契约机械门）：该仓新增 `scripts/validate-codebuddy-bootstrap.mjs` 并接入其 CI；
  校验项覆盖尺寸（按 JS string length）、必备权威指针、不得内联 AGENTS.md 正文、不得出现权限授予 / gate 豁免、
  回执 schema 完整性。负向测试实测：超限 / 指针缺失 / 内联 AGENTS / 权限授予四类输入均被拒（exit 1）。
- FACT（该门证明的边界）：它证明的是**交付契约**成立，**不是**运行时行为。二者不得互相冒充。
- UNKNOWN（本节无法自证的项）：fresh-session 实际选中的 guidance 文件、是否被截断、随后是否完整读取权威。
  取得该证据需要与实现会话无关的全新会话直接观测首轮上下文；实现者从同一上下文自我取证不成立。
  因此 `BOOTSTRAP_LIVE_VALIDATION = PARTIAL`，不是 PASS。
