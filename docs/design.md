# 设计说明：权威、执行与证据

> 本页解释现有设计，不定义新字段、状态域、gate 或覆盖规则。当前规范由 RULES、AGENTS、references 和 deployment setup 文档拥有；历史材料用于解释动因。执行以原文为准。
>
> 本页对照的基线：[833046a](https://github.com/FlapPearLabs/agent-engineering-governance/commit/833046a7c440a74925773d7b4fdadbf42c745c27)。更新后的规范可能继续演进。

## 设计要解决的矛盾

Agent 需要足够明确的合同与检查来避免自证、遗漏和越权；把每张票都送进最大流水线，又会造成昂贵评审、反复建图、人工搬运和无限加固。

因此本仓把不可削弱的底线与可覆盖的执行默认分开，把机器事实、行为证据、语义判断分别交给合适的执行层。它是一套治理合同与薄工具，不是已经实现全部工作流的自动调度器。

## 权威：全局默认如何与项目共存

| 层 | 回答的问题 | 规范与说明入口 |
|---|---|---|
| A 平台 / 系统 | 当前 runtime、OS 和工具实际允许什么 | 当前平台契约；[权威映射](../audit/AUTHORITY_MAP_V2.md) |
| B 普适不变量 | 哪些底线不能被项目削弱 | [RULES](../RULES.md) |
| C 仓库本地权威 | 产品合同、批准的设计、scope 和集成政策是什么 | 目标仓 RULES / AGENTS / Approved Specs / Issue 授权 |
| D 全局执行默认 | 项目未覆盖处如何施工 | [AGENTS](../AGENTS.md) 与 [references](../references/) |
| E 方法与工具 | 通过何种技能、脚本或查询执行 | [Skills 路由](../references/skills-and-model-routing.md)、[获取指南](../skills/README.md)、[MCP](../mcp/README.md) |
| F 记忆与偏好 | 有哪些背景、导航和尚未晋升的经验 | [engineering-memory](../references/engineering-memory.md) |

C 层明确政策可覆盖 D 层默认，并按 RULES R1 记录覆盖；加严与真正冲突的处理也以 R1 为准。方法、记忆、票据依赖图不会自行产生产品权威。

AUTHORITY_MAP_V2 保存分层修正的解释，执行边界已固化在 RULES R1。不能因为该文档位于 audit 目录，就把它所解释的既有权威算法忽略；也不能将其他历史候选意见当成新规则。

## 角色：写代码、裁决与集成分开

| 角色 | 主要责任 | 关键边界 |
|---|---|---|
| Product Owner | 产品方向、scope、规范裁决和未决架构选择 | 授权由可追溯权威承载 |
| Parent Orchestrator | 恢复状态、计算 frontier、编组、派发、归集证据和推进 | 默认保持薄控制面，不吸收实现者或独立评审的权威 |
| Worker | 在授权 lane 内实现、测试与修复 | 不自批、不扩大 scope |
| Reviewer | 以 fresh context 和独立 grounding 判断合同 | finding 不自动产生修复授权；修改候选后原结论不再证明新候选 |
| Integrator | 核验候选、串行集成、远端验证和关闭 | 依赖适用 gate 的 exact-candidate 证据 |

完整角色合同见 [AGENTS](../AGENTS.md#1-角色模型)。默认允许隔离 worker 直接实现；handoff 文档只在跨工具、中断、外部 worker 或审计等需要传递时创建。

## 拆票与 Stage：先自然缝，再施工排序

产品行为和已有架构决定 producer、consumer、状态/身份 owner 及失败边界；由这些自然缝产生内聚票据，再建立 DAG。依赖图只提供候选 frontier，Stage 还要考虑写权冲突、风险、成本和集成失效半径。

分解前的收敛检查与分解后的票集组合检查承担不同任务。单票结构正确、DAG 无环或一直在同一会话里，都不能证明组合合同成立。连续会话可以复用仍有效的证据；新会话也不必重做一切，但两条路径都不能省略拆票后的证明。

对应规范：[execution-stage 的分解协议](../references/execution-stage.md#6-seam-first-分解协议to-tickets-及等价工具的约束壳)、[AGENTS 的 Seam-first](../AGENTS.md#4-seam-first-分解)。设计与关闭证据的分区由 [ticket-lane](../references/ticket-lane.md) 拥有，实际观测不能反向改写冻结要求。

并行冲突还包括 CI workflow、测试登记、生成索引和共享注册表。产品文件互不相交，不证明执行基础设施写面互不相交；共享文件的单写者与最终回读见 ticket-lane。

## Lane：从合同到可集成证据

MEDIUM 基线的阅读顺序是：授权和 exact base、隔离 lane、读取权威与 grounding、surface manifest、合同和反例、实现、适用静态门、动态验证、独立评审、CI 与串行集成。完整顺序、风险裁剪和升级条件留在 [AGENTS](../AGENTS.md#3-ticket-lane风险分级生命周期)。

| 机制 | 解决的问题 | 唯一详情入口 |
|---|---|---|
| Contract / real-shape seam | 避免 consumer 的假设自己证明自己 | [ticket-lane](../references/ticket-lane.md) |
| Counterexample-first TDD | 区分目标反例 RED 与损坏 harness | [ticket-lane](../references/ticket-lane.md#4-counterexample-first-tdd) |
| Test engineering | 让 fixture、相关环境和历史失败模式有归属 | [ticket-lane 的测试工程契约](../references/ticket-lane.md#42-test-engineering-contract) |
| Static-first / FAST 与 FULL | 在较便宜可靠层发现缺陷，同时保留更广集成证明 | [静态门框架](../references/static-analysis-and-code-intelligence.md)、[语言推荐矩阵](../references/static-tooling-profiles.md) |
| Risk-scaled review | 将贵评审用于适用的语义和高风险不确定性 | [review-and-repair-saturation](../references/review-and-repair-saturation.md) |
| Exact-SHA / serial integration | 防止旧结论沿用到新候选、并行覆盖和假关闭 | [git-ci-integration](../references/git-ci-integration.md) |

静态工具不能裁决产品语义；回归测试承载的行为知识也不能被一个近似 lint 规则取代。缺陷类是否值得下沉、选择哪层以及是否需要独立工具票，由既有静态框架的晋升判定负责，本页不重声明其取值集合。

## Grounding：独立查询不等于重复重建

默认使用 canonical base 图与 candidate diff；需要候选精确图时使用 lane 图；CodeGraph 不可用则走明确的手工路径。所用证据范围必须如实报告，不能把 base 图称为 candidate-exact 覆盖。

独立评审需要独立查询、关系推理与反例，不要求每个 reviewer 从头建库。初始化、增量同步、dirty 状态与 grounding receipt 的运行时合同见 [codegraph-grounding](../references/codegraph-grounding.md) 和 [project-continuity-contract](../references/project-continuity-contract.md)。合成 hook 测试证明所测逻辑，不证明所有 runtime 已接线。

## 证据：合法形状、真实来源、足够证明是不同问题

[Review Evidence 接口](../references/review-evidence.md) 与 [schema](../schemas/review-evidence.schema.json) 区分结构、来源核验和充分性。字段齐全不证明来源真实，来源真实也不证明足以支撑结论。

证据绑定具体 subject 与 candidate；可复用描述还要消费失效条件。路径与 CI artifact 取回有显式边界，命令引用是溯源数据，不成为执行授权。机器可以处理声明过的结构事实，语义 scope 与 reviewer verdict 仍由相应独立角色裁决。

本仓的 collector / validator 不是完整的 review harness、自动 reviewer 或第二个 tracker。接口正确不自动证明所有生产消费者都已接入。

## 收敛：修复权与集成资格独立

早期按 severity 自动修复，导致同一任务不断追加低收益加固。现有机制先判断修复价值与票授权，再消费累计预算；换 SHA 或 reviewer 不自动产生新预算。

预算耗尽会改变下一步的修复权限，不会抹掉高价值 blocker，也不会把未通过的评审改成通过。仲裁负责 findings 的去向，required review gate 负责集成资格。通过后的停手边界、元治理递归切断与外部交接前 barrier 见 [review-and-repair-saturation](../references/review-and-repair-saturation.md)；本页不另建仲裁流程。

## 恢复与关闭：项目状态必须长于会话

GitHub Issue / PR 承载活跃执行，仓文档承载长期决策，测试承载缺陷知识，部署档案承载经净化的环境要求。固定状态索引负责指向它们；聊天记忆只提供缓存与发现入口。

恢复、flush、离线同步与“值得持久化吗”的判据见 [project-state-persistence](../references/project-state-persistence.md)。learning 条目如何关闭、orchestrator 的关闭责任与保证术语见 [engineering-memory](../references/engineering-memory.md)。评审摘要、绿色测试和 owner 的聊天指令，各自仍需相应的可追溯证据与权威落点。

## Runtime：治理可达与机械强制分开验证

治理内容放进 Git，并不保证每个 Agent 自动读取全文。WorkBuddy 的注入机制依赖被观测的 profile，guidance 选取与截断事实已修正；可靠读取路径由 [BOOTSTRAP_CONTRACT](../deployment/BOOTSTRAP_CONTRACT.md) 定义。

[WorkBuddy hook](../adapters/workbuddy/README.md) 有限定拒绝面的 live 接线与拦截记录；它仍是非封闭的静态命令分类器，存在已知绕过和宿主载荷依赖，不能称为完整沙箱。[ZCode hooks](../adapters/zcode/README.md) 是连续性合同参考实现，不能由合成矩阵推定其他宿主的端到端效果。

本仓的公开扫描也只证明被扫描面与其策略：当前候选面、提交元数据和历史模式分别核验。真实机器身份与凭据的边界由 [RULES R2](../RULES.md#r2-凭据与机器私有信息安全) 定义，不能靠目录标记或测试用途豁免。

## 规范地图

| 内容 | 执行时读取 | 解释与证据 |
|---|---|---|
| 最小底线与全局默认 | [RULES](../RULES.md)、[AGENTS](../AGENTS.md) | [权威分层纠偏](../audit/AUTHORITY_MAP_V2.md) |
| 分解、编组、单票 | [execution-stage](../references/execution-stage.md)、[ticket-lane](../references/ticket-lane.md) | [痛点映射](../audit/PAIN_TO_POLICY_MAP_V2.md) |
| 评审、证据与集成 | [review-and-repair-saturation](../references/review-and-repair-saturation.md)、[review-evidence](../references/review-evidence.md)、[git-ci-integration](../references/git-ci-integration.md) | [审计目录](../audit/) |
| 代码智能与工具成本 | [codegraph-grounding](../references/codegraph-grounding.md)、[静态框架](../references/static-analysis-and-code-intelligence.md)、[profiles](../references/static-tooling-profiles.md)、[模型路由](../references/skills-and-model-routing.md) | [可移植性证据](../audit/PORTABILITY_HARDENING_EVIDENCE.md) |
| 连续性与经验 | [project-state-persistence](../references/project-state-persistence.md)、[project-continuity-contract](../references/project-continuity-contract.md)、[engineering-memory](../references/engineering-memory.md) | [决策历史](design-history.md) |
| 开工与部署 | [PORTABLE_SETUP](../deployment/PORTABLE_SETUP.md)、[BOOTSTRAP_CONTRACT](../deployment/BOOTSTRAP_CONTRACT.md)、[adapters](../adapters/) | [使用指南](getting-started.md)、[AS-IS V3](../audit/AS_IS_WORKBUDDY_V3.md) |
