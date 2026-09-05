# PORTABILITY_HARDENING_EVIDENCE — 证据记录（V1.1）

> 方法：原始 WorkBuddy 机只读探针 + ZCode dogfood 报告（用户提供，判定 PASS_WITH_DEGRADED_FIDELITY）。只录支持远程 setup 的必要证据。
> BASE_MAIN_SHA = `2359283879cec3f37f6e357bd6b9a2cfeb6d45b0`（merged V1）。

## 1. 原始 WorkBuddy 机实况（2026-09-05 探针）

### Skills（13 主线）

- 全部 INSTALLED 于 `~/.workbuddy/skills/`（探针逐个 `test -f SKILL.md`）：
  - ZCode dogfood 报告 PRESENT 的 9 项：grill-with-docs / to-spec / to-tickets / implement / tdd / code-review / diagnosing-bugs / resolving-merge-conflicts / handoff。
  - ZCode 报告 MISSING/SOURCE UNKNOWN 的 4 项在**原始机全部在位**：`review-agent`（装于 2026-07-22）、`writing-plans`（2026-06-16）、`subagent-driven-development`（2026-06-02，含本地 .backup 文件）、`simplify-code`（2026-07-01）。
  - 4 项 SKILL.md/frontmatter 均无上游 URL/版本/license 元数据 → `SOURCE = UNKNOWN`（不编造 URL）；ZCode 不可得的原因 = 平台 registry 未收录，非原始机缺失。
  - 判定：4 项全部 `CANONICAL_OPTIONAL`（真实触发场景 + 有效 fallback），无 DEPRECATED/REPLACED/REMOVE。主线 = 9 REQUIRED-at-trigger + 4 OPTIONAL。

### MCP（USER_CONFIGURED，`~/.workbuddy/mcp.json` 实测解析）

- keys = `['codegraph', 'context7', 'gh_grep']` —— canonical 集合**再证实**，未变。
- 平台连接器：github（OPTIONAL_PLATFORM_CONNECTOR，有 PR #1 全程执行证据）；agent-mail（DISCOVERED/NOT_REQUIRED，无采纳证据，非 canonical——维持 D4）。

### CodeGraph / 代码智能 / 静态工具

- CodeGraph v1.0.1（`~/.local/bin/codegraph` → versions/v1.0.1）；CLI 能力面此前已全量核验（init/index/sync/status/query/explore/node/files/callers/callees/impact/affected/daemon）。
- **LSP**：平台提供（WorkBuddy 内置 LSP 工具）→ `PLATFORM_PROVIDED`。
- **AST/结构查询**：CodeGraph 符号级查询 + 平台 Grep（文本层）→ AST 专精工具（tree-sitter 等）`AVAILABLE_BUT_UNUSED/UNVERIFIED`，按仓决定。
- **语言静态工具链**：宿主 PATH **无**全局 tsc/eslint/prettier/biome/ruff/mypy/pyright/pytest/vitest/jest（探针全 absent）→ 全部 `REPOSITORY_PROVIDED`（D12 规则的事实依据）。受管 runtime：node 22.22.2 / python 3.13.12（`~/.workbuddy/binaries/`，`PLATFORM_PROVIDED`）。
- 测试/CI：node 内建 test runner / npm scripts（REPOSITORY_PROVIDED）；CI = GitHub Actions（governance-ci 已接入；仓级 CI 由各仓自带）。

### 分类汇总（D1 分类法）

| 能力 | 分类 |
|---|---|
| git / gh / 代理 | USER_CONFIGURED |
| CodeGraph / context7 / gh_grep | USER_CONFIGURED + REQUIRED_BY_GOVERNANCE |
| LSP 工具 / 受管 runtimes / Grep | PLATFORM_PROVIDED |
| 语言 formatter/linter/typecheck/test | REPOSITORY_PROVIDED（按仓） |
| tree-sitter 等专精 AST 工具 | AVAILABLE_BUT_UNUSED / UNVERIFIED |
| github connector | OPTIONAL_PLATFORM_CONNECTOR |
| agent-mail | DISCOVERED_PLATFORM_CONNECTOR / NOT_REQUIRED |

## 2. ZCode dogfood delta（引用既有报告，不复制日志）

- 治理重建 PASS（15/15 validator @ 5ae3e3c 基线）；MCP 分类（AVAILABLE ≠ USER_CONFIGURED ≠ REQUIRED）工作正常。
- 4 skill 降级 = ZCode registry 缺失所致（本探针证明非原始机缺失）→ 修复 = 获取指南 FALLBACK + OPTIONAL 状态（见 skills/README.md V1.1）。
- Windows 环境未继承 macOS 特有规则（R2 两层制 + deployment profile 生效的正面证据）。

## 3. MEMORY 持久知识晋升台账（SOURCE = MEMORY，`~/.workbuddy/MEMORY.md` 319 行全量复核）

| # | MEMORY 内容 | DURABILITY_REASON | CANONICAL_DESTINATION | EXISTING_DUPLICATE | ACTION |
|---|---|---|---|---|---|
| 1 | TICKET LANE V2 主体 | 已迁 | AGENTS + references/ticket-lane | YES | ALREADY_COVERED |
| 2 | ORCHESTRATOR OVERRIDE | 已迁 | AGENTS §1 | YES | ALREADY_COVERED |
| 3 | REPORTING OVERRIDE（novelty-first + CI 压缩例外） | 已迁 | review-and-repair-saturation §5 | YES | ALREADY_COVERED |
| 4 | REPAIR SATURATION OVERRIDE | 已迁 | review-and-repair-saturation §2/3 | YES | ALREADY_COVERED |
| 5 | **Engineering style 十条** | 跨项目实现美学，防过度设计/静默 fallback | **references/engineering-memory.md §2（本轮新增）** | 部分（doctrine #9） | **ADD** |
| 6 | 模型路由哲学 | 已迁 | skills-and-model-routing §2 | YES | ALREADY_COVERED |
| 7 | Axioms（SPEC≠仓库理解 等） | 已迁 | AGENTS doctrine + ticket-lane | YES | ALREADY_COVERED |
| 8 | CI 证据块/KNOWN_BASELINE 9 字段 | 已迁 | git-ci-integration §3 | YES | ALREADY_COVERED |
| 9 | no-mandatory-handoff / FUTURE_MANUAL_HANDOFF=NO | 已迁 | AGENTS §1 + PORTABLE_SETUP | YES | ALREADY_COVERED |
| 10 | "Auto-recorded per ticket" 门字段清单 | 流程样板，已被 Stage/Lane 文档取代 | — | — | **DROP**（superseded） |
| 11 | 旧 SHA/分支/T9-T11 在途状态 | transient | —（Git/Tracker 即权威） | — | **DROP**（transient state） |
| 12 | 用户偏好（中文、结构化交付、显式授权、STOP 纪律） | F 层偏好 + STOP 已成文 | MEMORY 指针（F 层）+ AGENTS §7 | YES | ALREADY_COVERED（偏好部分留 MEMORY，不晋升） |

RAW_MEMORY_COMMITTED = **NO**（本任务全程未上传/提交原始 MEMORY；R2 归档政策不变）。

## 4. 本轮新增/修改的 canonical 文件

- 新增：`references/static-analysis-and-code-intelligence.md`、`references/engineering-memory.md`、`audit/PORTABILITY_HARDENING_EVIDENCE.md`（本文件）。
- 修改：`AGENTS.md`（+ENGINEERING EVIDENCE ROUTING）、`references/ticket-lane.md`（+4.1 test-first defect closure）、`references/review-and-repair-saturation.md`（L0 先清场 + MACHINE BEFORE MODEL）、`skills/README.md`（STATUS/REQUIRED 列 + 4 项 OPTIONAL 化 + SKILL_MISSING 原则）、`deployment/PORTABLE_SETUP.md`（能力矩阵 + receipt CAPABILITIES 行）、`scripts/validate_governance.py`（+V1.1 检查）。
- 未动：权威分层、Stage/Lane、风险/评审分级结构、repair 饱和语义、CI 语义、Seam-first、bootstrap 架构、产品仓、live WorkBuddy。
