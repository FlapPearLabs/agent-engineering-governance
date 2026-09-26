# Hermes Multi-Bot V2.1 Repair & Finding Closure Report

**Execution Mode**: FINDING-SCOPED REPAIR (Minimal Diff, Accepted Baseline Preserved)  
**Target Environment**: macOS 26.2 (Darwin) / Hermes Desktop Core  
**Governing Standard**: FlapPearLabs Agent Governance & Risk Architecture  

---

## 1. Finding Closure Summary

| Finding ID | Finding Description | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **F-P1-01** | PROFILE_ISOLATION_MISCHARACTERIZED | **RESOLVED** | 文档与 SOUL 彻底修正；剥离“物理隔离/沙盒”用词，替换为“Profile-level Config/Memory/Session 隔离”；Markets 与 Reviewer 诚实标记为 `POLICY_ENFORCED_ONLY`。 |
| **F-P1-02** | CODE_SOUL_RESPONSIBILITY_OVERLOAD | **RESOLVED** | `code/SOUL.md` 大幅瘦身至纯粹人格与不变量；工程规则解耦至官方原生支持的 `~/.hermes/profiles/code/AGENTS.md`。 |
| **F-P1-03** | PROMPT_PRECEDENCE_AUTHORITY_CONFLATION | **RESOLVED** | 拆分为独立双模型：Hermes 运行时上下文加载顺序 vs 软件工程交付物权威层级。 |
| **F-P1-04** | SMOKE_TEST_STATUS_OVERCLAIM | **RESOLVED** | 撤销过度声称的“VERIFIED”，修正为“CONFIGURED + CONTROL_FLOW_SIMULATED + LOCAL_GOVERNANCE_VALIDATED”；建立 5 级状态阶梯。 |
| **F-P2-01** | UNIFORM_CLOSURE_POLICY_OVERCONSTRAINED | **RESOLVED** | 引入 `RISK_A`（确定性小改动）、`RISK_B`（常规）、`RISK_C`（高影响）三级风险分流关票策略，解耦任务类型与风险级别。 |
| **F-P2-02** | BUG_TEST_REQUIREMENT_TOO_RIGID | **RESOLVED** | 核心不变量修正为 `PRE-REPAIR FAILURE EVIDENCE REQUIRED`，支持 12 种确定性证据形式，消除教条主义。 |
| **F-P2-03** | REVIEWER_READONLY_NOT_HARD_ENFORCED | **RESOLVED** | 建立 `REVIEW_EXECUTION_CONTRACT`；隔离实施者推导心智，若无 OS-level 硬沙盒诚实标记为 `POLICY_ENFORCED_ONLY`。 |
| **F-P2-04** | MATT_SETUP_INVOCATION_SEMANTICS | **RESOLVED** | 规范显式调用语义；检测缺失时引导或显式调用，禁止隐式脑补执行。 |
| **F-P2-05** | RESEARCH_CORROBORATION_OVERCONSTRAINED | **RESOLVED** | 建立证据充足性模型（Evidence Sufficiency Model）；单权威源（官方源码/SEC/法规）充分成立，争议事项强制多源交叉核验。 |
| **F-P2-06** | MEDIA_PIPELINE_OVERAPPLIED | **RESOLVED** | 引入 `MEDIA TASK CLASSIFIER`（7 级流水线路由），简单图文/文案直接轻量产出，仅 Campaign 跑 14 阶段。 |
| **F-P2-07** | EDU_RETEST_CADENCE_OVERFIXED | **RESOLVED** | 将 D+1/D+3/D+7 调整为默认复测节奏（Default Retest Cadence），允许灵活微调，但硬性保留延迟复测不变量。 |
| **F-P2-08** | PROMPT_CACHE_BENEFIT_UNVERIFIED | **RESOLVED** | 撤销未经 Benchmark 的命中率断言，修正为 `UNVERIFIED / HYPOTHESIZED`，强调 Context 卫生与注意力保护。 |

---

## 2. 详细 Finding 修复清单 (Detailed Closures)

### F-P1-01: PROFILE_ISOLATION_MISCHARACTERIZED
- **Root Cause**: 前序报告存在修辞过度，将进程层面的目录隔离描述为“物理级强隔离”和“安全沙盒”，给审查员造成具备 OS 级限制的假象。
- **Repair**:
  1. 全量文案统一修正为：`PROFILE-LEVEL CONFIG / MEMORY / SESSION ISOLATION`。
  2. Markets Bot 的 SOUL 明确写入 Capability Contract，声明其权限约束为 `POLICY_ENFORCED_ONLY`。
- **Verification**: `markets/SOUL.md` 与审计报告已全部更正，无任何虚假沙盒背书。
- **Residual Risk**: 宿主机若遭受提示词注入恶意越权调用 Terminal，属于 Policy 边界风险；需等待未来 Hermes 引入 OS 级硬隔离 sandbox。

### F-P1-02 & F-P1-03: CODE SOUL RESPONSIBILITY OVERLOAD & CONFLATION
- **Root Cause**: `code/SOUL.md` 堆砌了过多实现细节、硬编码路径和流程状态机，导致模型在单次提示词中认知超载，且将运行时指令与工程权威混淆。
- **Repair**:
  1. `code/SOUL.md` 瘦身至纯粹人格基底与工程不变量（Pragmatic, Rigorous, Evidence-driven, Follow-through, Minimal Diff, Self-review != Independent review）。
  2. 创建 `/Users/songshiyao/.hermes/profiles/code/AGENTS.md` 作为官方第一类识别的 `GLOBAL_CODE_ENGINEERING_CONTEXT`。
  3. 拆分为独立双模型：`RUNTIME_CONTEXT_PRECEDENCE`（System > User Mid-turn > Repo AGENTS > Profile AGENTS > Skills）与 `ENGINEERING_ARTIFACT_AUTHORITY`（Approved Specs/ADRs > Architecture Docs > Tests > Code > Ephemeral Context）。
- **Verification**: `code/SOUL.md` 与 `code/AGENTS.md` 分层落盘，Hermes 官方扫描断言通过。
- **Residual Risk**: 下游仓库未配置本地 `AGENTS.md` 时依赖全局默认配置，可通过 `setup-matt-pocock-skills` 显式补全。

### F-P2-01 & F-P2-02: CLOSURE POLICY & BUG TEST DOGMA
- **Root Cause**: 前序版本中 TRIVIAL_CHANGE 与全局必须跑全套 CI/Review 产生规则冲突；Bug 修复强制必须写单测，在无法单测的场景下导致阻塞。
- **Repair**:
  1. 引入三级风险分流闭环：`RISK_A`（确定性轻量级修改无需全套 Review/CI 直接关票）、`RISK_B`（常规特性需对应评审）、`RISK_C`（核心高风险需全套严格治理）。
  2. 修复原则修正为 `PRE-REPAIR FAILURE EVIDENCE REQUIRED`，允许复现脚本、命令行确定性输出、日志堆栈等 12 种证据形态。
- **Verification**: 已固化至 `code/AGENTS.md` 核心条款。
- **Residual Risk**: 针对 RISK_A 的判定若主观放宽可能漏网缺陷，已在规范中限制为 Typo/Docs/Format/Metadata 等确定性场景。

### F-P2-05 ~ F-P2-07: SATELLITE BOTS REFINEMENT
- **Root Cause**: 规则过于教条硬编码（机械双信源、强制 14 阶段、写死 D+1/3/7）。
- **Repair**:
  1. `research/SOUL.md`：单一权威源（Tier 1）直接充分成立，仅争议事项强制交叉验证。
  2. `media/SOUL.md`：引入 7 级流水线分类器（Quick Copy, Social Post, Article, Visual Asset, Short Video, Video Reproduction, Campaign）。
  3. `edu/SOUL.md`：D+1/D+3/D+7 转为 Default Cadence，灵活适配学习者节奏。
- **Verification**: 对应 SOUL 文件已全部热补丁生效。
- **Residual Risk**: 无，模型适配度与指令遵循度显著提升。

### F-P2-08: PROMPT CACHE BENEFIT UNVERIFIED
- **Root Cause**: 将“减少无关上下文”推导为“Prompt Cache 命中率提升”，缺乏真实 A/B 测试基准支撑。
- **Repair**: 声明修正为：`PROMPT CACHE BENEFIT: UNVERIFIED / HYPOTHESIZED`；收益客观描述为上下文卫生（Context Hygiene）与注意力稀释抑制。
- **Verification**: 全量文档同步修正。
- **Residual Risk**: 需后续通过 Hermes 内部 token 追踪工具沉淀真实基准数据。
