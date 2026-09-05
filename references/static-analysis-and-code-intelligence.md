# REF: Static Analysis & Code Intelligence — 机械优先工具层级

> Canonical owner: AGENTS.md §ENGINEERING EVIDENCE ROUTING。本文件定义工具层级与 static-first 升级方向（D2/D5）。
> 核心原则：**MECHANICAL PROOF BEFORE MODEL REASONING**；同时 **static 输出不取代语义/合同评审**。

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

## 3. STATIC 不裁决语义

静态工具证明结构/机械事实，**不**裁决：业务行为、权威归属、产品有效性、fallback 语义、身份含义、架构所有权。这些是合同/模型/人的领地（对应 doctrine #4/#6 与评审分级）。

## 4. USE_REPOSITORY_NATIVE_STATIC_TOOLING_FIRST（D12）

- 全局治理**不固定任何语言栈**。进入目标仓先发现其原生工具：package/编译/lint/CI 配置、语言服务器支持。
- 用仓里已有的工具；只有当**重复出现的真实缺陷类** + 现有工具无法廉价检出 + 期望值 > 维护成本时，才建议新增静态工具。
- 基准环境事实（2026-09-05 实测）：宿主 PATH 无全局 tsc/eslint/prettier/ruff/mypy/pytest 等——语言工具链**按仓安装**，这正则符合本规则。
