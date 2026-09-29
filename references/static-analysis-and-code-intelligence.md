# REF: Static Analysis & Code Intelligence — 机械优先层级与跨语言静态门框架

> Canonical owner: AGENTS.md §ENGINEERING EVIDENCE ROUTING。本文件是 **STATIC-ANALYSIS-FIRST 与 STATIC GATE FRAMEWORK 的 D 层 canonical 政策面**（仓政策可显式 OVERRIDE；加严永远合法）。
> 核心原则：**MECHANICAL PROOF BEFORE MODEL REASONING**；同时 **static 输出不取代语义/合同评审**。
> 权威分层：本文件**不**进入 B 层不变量——`RULES.md` **不包含任何语言/工具特定策略**；语言/生态的**推荐**工具矩阵属 `references/static-tooling-profiles.md`（**推荐，不是安装强制**）。
> 票级落点：`references/ticket-lane.md` §9 `STATIC_GATE_RECEIPT` 是本框架的票级证据形态。

## 1. 代码智能层级（用最便宜的可靠事实源）

| 层 | 解决什么 | 事实类型 | 注意 |
|---|---|---|---|
| grep / search | 字面发现、快速回忆 | 文本命中 | **GREP != AST**：文本命中不是结构证明 |
| AST / 结构查询 | 语法感知搜索、模式区分、安全变换 | 语法结构 | **AST != LSP**：AST 知结构，不知类型/项目语义 |
| LSP | diagnostics、符号解析、references、rename 安全性、类型/签名反馈 | 项目级类型语义 | **LSP != CODEGRAPH**：LSP 强在单仓类型事实，弱在跨仓关系图 |
| CodeGraph | 跨文件结构、callers/callees、ownership surface、impact/affected、爆炸半径 | 仓库关系图 | 模式 A/B/C 见 codegraph-grounding.md |
| 源码阅读 | 最终语义确认 | 语义 | 结论的最终裁判（结合合同） |

层级用法：先问"这个问题属于哪一层"，用该层工具拿事实；低层事实不足再升层，**不要跳层烧推理**。

## 2. STATIC-ANALYSIS-FIRST 规则

低层编码问题（syntax/type/imports/dead symbol/call-site mismatch/formatting/simple lint）在升级到任何模型评审**之前**，先跑适用的：

formatter → linter → type checker / compiler → LSP diagnostics → static analyzer → schema validator → AST 查询。

机器证据能精确定位的 → 直接修 + 用测试证明，**不要叫强评审员来重新发现 undefined variable**。

静态门因此是**成本闸门**，不是信任闸门：它把机器可证的缺陷类**先清掉**，让动态测试与模型推理只花在机器证不了的地方。

## 3. STATIC 不裁决语义

静态工具证明结构/机械事实，**不**裁决：业务行为、权威归属、产品有效性、fallback 语义、身份含义、架构所有权。这些是合同/模型/人的领地（对应 doctrine #4/#6 与评审分级）。

## 4. USE_REPOSITORY_NATIVE_STATIC_TOOLING_FIRST（D12）

- 全局治理**不固定任何语言栈**。进入目标仓先发现其原生工具：package/编译/lint/CI 配置、语言服务器支持。
- 用仓里已有的工具；只有当**重复出现的真实缺陷类** + 现有工具无法廉价检出 + 期望值 > 维护成本时，才建议新增静态工具。
- 语言工具链**按仓安装**，正确姿势是仓库受控的版本与确定性的 CI provisioning，而不是依赖某台机器恰好装了什么（见 §14）。

## 5. 本框架回答的问题

跨语言静态门的完整问题集（**所有条目都必须在"这个仓实际是什么"上回答，不允许用通则代替本仓事实**）：

```text
1. 这个仓实际包含哪些语言/代码面？
2. 哪些静态工具已经被配置？
3. 哪些命令**真的**在执行这些门？
4. 本票哪些门是强制的？
5. 哪些**期望能力缺失**？
6. 缺失工具如何**诚实上报**？
7. 新仓（GREENFIELD）与成熟/遗留仓（ESTABLISHED / LEGACY）如何区别对待？
8. 静态检查如何接在动态测试与模型评审**之前**？
```

## 6. STATIC_TOOLING_DISCOVERY —— 先发现，后规定

对一个 CODE 仓库，静态工具链必须从**仓库事实**中发现：

```text
language manifests
package / build 文件
工具配置文件
lockfile
编译器配置
CI
Makefile / task runner
workspace / monorepo 配置
既有脚本
语言文件扩展名（**次要证据**）
```

**禁止**仅凭文件扩展名推断工具链。示例（**非穷尽**）：

```text
package.json / eslint.config.* / tsconfig.json
pyproject.toml / ruff.toml / mypy.ini
go.mod
Cargo.toml
pom.xml / build.gradle*
*.csproj / Directory.Build.props
Package.swift
Gemfile
composer.json
CMakeLists.txt / compile_commands.json
*.tf
.shellcheckrc
```

发现结论必须落到 §7 的 `STATIC_GATE_PROFILE`；**发现结果驱动政策**，而不是政策预设语言。

## 7. STATIC_GATE_PROFILE —— 轻量证据结构

```text
STATIC_GATE_PROFILE

LANGUAGES =
CODE_SURFACES =
REPOSITORY_TYPE =
  GREENFIELD | ESTABLISHED | LEGACY | MONOREPO

CONFIGURED_STATIC_TOOLS =
CONFIGURED_COMMANDS =

SYNTAX_OR_COMPILER_GATE =
FORMAT_GATE =
LINT_GATE =
TYPE_GATE =
DEEP_STATIC_ANALYSIS_GATE =
SCHEMA_CONFIG_GATE =

REPOSITORY_GLOBAL_GATES =

MISSING_RECOMMENDED_CAPABILITIES =

STATIC_TOOLING_GAPS =

AUTHORITY_OVERRIDES =
```

这是一个**证据/报告结构**，不是新数据库。**不得**引入新的强制 JSON 状态子系统，除非既有治理架构客观要求（当前不要求）。

## 8. STATIC GATE STATUS MODEL —— 显式非坍缩状态机

每个门只允许以下取值：

```text
PASS
FAIL
NOT_CONFIGURED
NOT_APPLICABLE
KNOWN_BASELINE_FAILURE
ENV_BLOCKED
EXPLICIT_AUTHORITY_OVERRIDE
```

硬语义（**不得**在任何报告/收据/摘要中坍缩）：

```text
NOT_CONFIGURED          != PASS
ENV_BLOCKED             != PASS
KNOWN_BASELINE_FAILURE  != PASS
TOOL_EXISTS             != TOOL_EXECUTED
CONFIG_FILE_EXISTS      != GATE_EXECUTED
LINTER_CONFIGURED       != LINTER_PASSED
```

- `PASS` 声明**必须**有真实执行证据（命令 + 调用点 + 结果）。
- `NOT_APPLICABLE` 是**适用性判定**，不是"没跑"的委婉说法：它要求"该类别在本语言/本项目设计上不成立"（如无类型系统的项目 `TYPECHECK = NOT_APPLICABLE`）。
- `KNOWN_BASELINE_FAILURE` 是**提案**语义（RULES R3）：只可作为提案上报，接受需独立侧证据，不得自我豁免。
- `ENV_BLOCKED` 记录环境阻塞（工具不可获取/平台不支持），**不**代表代码干净。

## 9. CONFIGURED TOOLING IS MANDATORY —— 已配置的工具必须执行

D 层默认规则：

```text
IF 仓库已经配置了某个静态工具
AND 本次变更面落在该工具的 scope 内
THEN 适用的静态门必须在动态测试之前执行
```

示例：

```text
eslint config 存在            → 适用的 JS/TS 变更必须跑 ESLint
tsconfig 存在且仓用 tsc 做校验 → 适用的 TS 变更必须跑 typecheck
ruff config 存在              → 适用的 Python 变更必须跑 Ruff
Cargo workspace 配置了 Clippy  → 适用的 Rust 变更必须跑 Clippy
```

- 仓库权威（C 层）可以**显式**覆盖本默认（记录 `OVERRIDE`）。
- **不得**因为"测试是绿的"就静默跳过已配置的工具。
- 反向同样成立：**不要**因为某工具在本机全局存在就声称仓库有该门（§14）。

## 10. CHEAP LANGUAGE-NATIVE CHECKS（FAST_GATE 的适用范围）

对有代码的语言，只要仓库正常工具链里存在**廉价的**编译器/解析器/语法检查，优先在动态测试之前跑：

```text
JavaScript 语法解析          Python compile / 语法校验
Go 编译器 / vet 路径         Rust cargo check
Java / Kotlin 编译阶段       C / C++ 编译器诊断
C# build / analyzer 阶段     Ruby 语法检查
PHP 语法检查                 Shell 语法解析
Terraform validate           JSON / YAML / TOML 解析
```

**不要**在工具链各不相同的情况下硬编码单一"万能命令"；命令来自 §6 的发现结果。

### 10.1 FAST_GATE / FULL_GATE 执行分类

本节是 **FAST_GATE / FULL_GATE 语义与边界的 canonical 声明面**（执行落点见 `references/git-ci-integration.md` §3）。

**FAST_GATE** = 便宜的、确定性的**预检**，目标是**快速失败**，先于昂贵测试与模型评审：

```text
语法 / parser / compiler 检查
lint
typecheck（语言有类型时）
schema / config 校验
git diff --check
廉价的仓库校验器
聚焦测试（focused tests）
廉价的静态/安全扫描
```

属性：`FAST` / `DETERMINISTIC` / `HIGH_SIGNAL` / 尽量**本地可离线** / 便宜到适合迭代执行。

- **不**强加普适 wall-clock SLA（各仓工具链差异过大，硬性秒数会诱发"为了达标而削弱门"）。
- **不**要求无关语言的工具链（仓里没有的语言不构成缺口）。

**FULL_GATE** = 更广的集成证据：

```text
全量单元/回归套件
集成测试
跨平台矩阵
历史兼容性
完整离线套件
昂贵的静态/安全分析
打包/构建验证
发布/公开门
```

两条互不替代，**双向都不豁免**：

```text
FAST 不替代 FULL：FAST PASS 不等于集成证据充分
FULL 不豁免 FAST：FULL PASS 不抹掉 FAST 阶段的失败
CI_FAST PASS != CI_FULL PASS
```

FAST/FULL 是**执行类别**，**不**要求必须是两个独立 CI job。

## 11. 跨语言推荐矩阵（指针）

`references/static-tooling-profiles.md` **只**拥有推荐档位：档位**名与语义的唯一声明点 = 该文件**。本文件**不重述档位清单**——与 §8 状态值域同一纪律（单一声明点；重述 = 双 owner，处置见 `ticket-lane.md` §8.3 CE-28）。

该矩阵是**推荐，不是普适安装强制**；采用与否按 §12/§13 判定。

## 12. GREENFIELD 与 ESTABLISHED / LEGACY

这个区分是**强制**的。

### GREENFIELD

在**首次实质生产代码合入之前**，为每个主要实现语言建立最小静态基线，通常包含：

```text
语法/编译校验
+ 一个生态相称的正确性 linter / static analyzer
+ 语言/项目设计依赖类型时：类型检查
+ 已标准化格式时：格式校验
```

**不**要求装满所有分析器。

### ESTABLISHED / LEGACY

推荐工具缺失时：

```text
记录 STATIC_TOOLING_GAP
```

- **不要**在无关功能票里顺手安装/配置新 linter。
- 缺失推荐工具**本身不**追溯性地让既有票全部失效。
- 工具采用通常应是**独立**的工程/工具票（§13）。

## 13. LEGACY ADOPTION RULE

向既有仓库引入新静态工具时：

先对**干净的当前 master** 跑它，分类：

```text
BASELINE_CLEAN
BASELINE_FINDINGS_EXIST
TOOL_INCOMPATIBLE
ENV_BLOCKED
```

**禁止**：

```text
打开 linter
→ 发现上百条 findings
→ 在无关功能票里大规模重写仓库
```

偏好采纳路径：

```text
测基线
→ 选择最小高价值规则集
→ 合法配置 generated / vendor 排除
→ 把机械格式与行为变更分开
→ 加入 CI
→ 有意识地收敛既有债务
```

若提出"仅对增量/新代码强制"：它必须**机械可靠**。**不要**为了回避修债务而发明脆弱的 diff-lint 框架。

若采纳需要广泛行为改动或大规模 churn：

```text
STOP: STATIC_TOOLING_BASELINE_TOO_DIRTY
```

改为返回一份采纳计划，而不是硬推。

## 14. NO GLOBAL TOOL DEPENDENCY

仓库所需的静态工具必须能从**仓库受控配置**复现。**不得**依赖：

```text
"ESLint 恰好全局装了"
"这台笔记本上有 Ruff"
"评审机器上有 Clang-Tidy"
```

偏好仓库/包/构建受控的版本，或确定性的 CI provisioning。

开发机可以持有全局二进制，但**全局存在不构成仓库门可复现性的证明**（`GLOBAL_BINARY_PRESENT != REPOSITORY_GATE_REPRODUCIBLE`）。

## 15. STATIC-FIRST 执行顺序

保留既有原则：**机器可证的失败要在昂贵的动态/模型评审之前清掉**。

**不**在跨生态强加单一字面命令顺序。canonical 阶段顺序：

```text
CONTRACT / COUNTEREXAMPLE DESIGN

→ TDD RED（需要时）

→ IMPLEMENT

→ APPLICABLE STATIC / MECHANICAL GATES

→ DYNAMIC GREEN / REGRESSION

→ SELF REVIEW

→ PUSH

→ REMOTE CI

→ INDEPENDENT REVIEW
```

在 `STATIC / MECHANICAL GATES` 内部：可行时**先跑更便宜/更高信号**的已配置工具，再跑更贵的。

### 15.1 FAST_GATE / FULL_GATE 在 canonical 顺序中的位置

把 §10.1 的执行类别嵌入既有阶段链（**不**新增阶段，只标注类别）：

```text
CONTRACT / COUNTEREXAMPLE DESIGN
→ TDD RED（需要时）
→ IMPLEMENT
→ LOCAL FAST_GATE          ← §10.1 便宜确定性预检
→ DYNAMIC GREEN / 聚焦测试
→ FULL 本地套件（相关范围）
→ SELF REVIEW
→ PUSH
→ CI_FAST_GATE            ← 干净环境可复现的等价确认
→ CI_FULL_GATE            ← 更广集成/发布证据
→ INDEPENDENT REVIEW
→ REPAIR / DEFECT PROMOTION 分类（§21）
→ MERGE
```

两条边界保持：

- **不**因已有 TDD RED/GREEN 证据就机械重复跑同一个聚焦测试（同一执行不重复计证据）。
- `LOCAL_FAST_GATE` 与 `CI_FAST_GATE` 的分工见 `references/git-ci-integration.md` §3。

## 16. MONOREPO RULE

monorepo 可以包含多个静态 profile。示例：

```text
frontend = TypeScript profile
backend  = Go profile
scripts  = Python profile
infra    = Terraform profile
```

票级执行应跑二者的**并集**：

```text
覆盖变更面的 static gates
+
仓库全局不变量/配置门
```

PR CI 可按仓库政策跑更广的仓库级静态门。**不要**仅仅因为 monorepo 里存在某语言，就在本地跑无关的语言工具链。

## 17. LSP 的角色

保留既有区分：

```text
LSP diagnostics 是有价值的**交互式**静态证据。
```

但是：

```text
LSP_AVAILABLE_ON_ONE_AGENT_MACHINE
!=
REPRODUCIBLE_CI_GATE
```

LSP 可以**补充**静态收据；除非仓库有可复现的等价物，**不得**作为唯一的远端合入门。

## 18. FORMATTER 不是语义证明

格式校验可以是有用的静态门，但：

```text
FORMAT_PASS != LINT_PASS
FORMAT_PASS != TYPE_PASS
FORMAT_PASS != CONTRACT_PASS
```

- **不要**把 formatter 强塞进每个既有仓库。
- **不要**在工具采纳期间对无关文件做大规模重排。

## 19. STATIC 不取代 TEST / REVIEW

保留：

```text
STATIC_ANALYSIS != BEHAVIORAL_CONTRACT_TEST
STATIC_ANALYSIS != ARCHITECTURE_REVIEW
STATIC_ANALYSIS != SECURITY_PROOF
STATIC_ANALYSIS != PRODUCT_CORRECTNESS
```

静态门的目的是：**在花动态测试与模型推理之前，移除机器可证的缺陷类**。它不是正确性证明，也不降低任何既有评审 gate。

## 20. 非目标与最小复杂性边界（R8）

- 本框架**不**规定任何仓库**必须**使用某个具体工具；§11 的矩阵是推荐档位。
- 本框架**不**新增 B 层不变量；语言/工具特定策略停留在 D 层默认 + C 层仓政策。
- 本框架**不**新建状态数据库；§7/§8 是证据结构。
- 新增强制门必须回答 R8 四问（防哪次真实失效 / 机器能否更便宜地做 / 每个风险级是否都需要 / 能否降级为 reference 或默认），并在 `audit/PAIN_TO_POLICY_MAP_V2.md` 留痛点行。

## 21. DEFECT_TO_GATE_PROMOTION（缺陷类下沉到机器门）

> 本节是 **DEFECT_TO_GATE_PROMOTION 语义的 canonical 声明面**。票级落点 = `references/ticket-lane.md` §9；reviewer 侧元数据与饱和联动 = `references/review-and-repair-saturation.md` §4/§6.5；CI 侧执行分类 = `references/git-ci-integration.md` §3。

方向：

```text
DEFECT KNOWLEDGE → LOWEST RELIABLE MECHANICAL LAYER
MODEL REVIEW BUDGET → RESERVED FOR NON-MECHANICAL PROBLEMS
```

**LOWEST ≠ WEAKEST**：选层标准是"能**可靠**检出该缺陷类"，不是"能省多少评审"。语义/产品判断**不得**为了降低评审负载被塞进静态检查（§3/§19）。

### 21.1 晋升判定（value-gated，不是自动规则扩散）

单个真实缺陷被修复后，评估**缺陷类**能否被机械可靠检出。至少回答：

```text
DEFECT_CLASS                  这个缺陷的稳定语义类目
REAL_OR_HIGH_CONFIDENCE       真实或高置信（而非合成/推测）
REACHABLE                     现实可达状态
DETERMINISTICALLY_DETECTABLE  判定可机械复现，不依赖主观解读
EXISTING_TOOL_CAN_DETECT      现有工具/门已能检出（无需新依赖）
FALSE_POSITIVE_RISK           误报风险（高风险 → 不晋升）
EXECUTION_COST                执行代价（应与迭代回路相称）
MAINTENANCE_COST              长期维护代价（规则漂移/版本 churn）
SEMANTIC_JUDGMENT_REQUIRED    是否需要语义/产品判断（需要 → 不下沉）
BEST_ENFORCEMENT_LAYER        §21.2 层级中的最便宜可靠层
PROMOTION_VALUE               HIGH / MEDIUM / LOW / NOT_APPLICABLE
```

`PROMOTION_VALUE = HIGH` 通常要求**同时**满足：

```text
真实/高置信缺陷类
+ 判定确定
+ 误报风险足够低
+ 执行与维护代价足够低
+ 语义稳定（不随产品意图漂移）
+ 不含隐藏的产品语义判断
```

**一次出现 ≠ 治理缺陷。** 不得因单次发现就新增强制规则（否则规则会指数扩散，误报本身成为新缺陷类）。

### 21.2 LOWEST RELIABLE MECHANICAL LAYER（概念层级）

> 与 §1 的区别（避免双 owner 解读）：§1 是**事实源层级**（用什么工具拿到事实：grep / AST / LSP / CodeGraph / 源码）；本节是**缺陷强制执行层级**（用什么门长期拦住这类缺陷）。两者正交，不互相替代。

```text
parser / compiler
→ linter
→ type checker
→ formatter（仅格式缺陷）
→ schema / config validator
→ 仓库特定静态校验器
→ 回归 / 合同测试
→ CI 注册与执行守卫
→ runtime hook / policy
→ 独立评审
→ 人类 / product owner
```

选择规则：沿层级向下找**第一个能可靠检出该缺陷类**的层。找不到（需要语义判断、误报高、或代价过高）→ 留在测试/评审/人类，**不硬塞**。

既有 §19 保留不变：携带**行为知识**的回归测试**不得**被"能覆盖某个实现形状的 lint 规则"替换。`BUG KNOWLEDGE → REGRESSION TEST` 对行为缺陷继续有效；本节只把**机械可判**的那部分下沉。

### 21.3 处置（disposition）

```text
PROMOTE_NOW                    本票内下沉到已有机械层
FOLLOWUP_TOOLING_TICKET        需新工具/新依赖/新 CI 架构 → 独立工具票
KEEP_AS_TEST                   行为知识 → 回归/合同测试
KEEP_AS_REVIEWER_RESPONSIBILITY 机器不可判 → 留在评审
KEEP_AS_HUMAN_DECISION         需产品/架构裁决 → 人类
```

**本票内下沉的允许条件**（全部满足才在当前 repair 内做）：

```text
现有工具已存在
+ 变更微小且局部
+ 无新依赖
+ 无广泛基线 churn
+ 无架构变更
+ 无无关文件
+ 与本票修复属同一缺陷类
```

任一不满足 → **先修当前缺陷**，记录 `MECHANIZATION_FOLLOWUP_CANDIDATE`，采纳放到**专门工具票**。§12/§13 的既有规则继续适用：遗留仓缺工具 → `FOLLOWUP_TOOLING_TICKET`，**不得**在无关功能票里顺手装整套工具链。

**本节不覆盖修复饱和纪律。** `DEFECT_TO_GATE_PROMOTION` 判定的是"这个缺陷类能否下沉到机器门"，**不**判定"现在是否应当再开一轮修复"——后者唯一声明点 = `references/review-and-repair-saturation.md` §4.2 / §6.6。因此：候选达到 required quorum PASS 且 `NO_KNOWN_HIGH_VALUE_BLOCKER = YES` 之后新发现的机械化机会，**默认** → `FOLLOWUP_TOOLING_TICKET`，而**非**在已通过的票内 `PROMOTE_NOW`；唯一例外是它本身为关闭一个高价值 blocker 所必需。
