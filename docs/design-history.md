# 决策历史：治理如何从施工中生长

> 本页是有来源的设计解释，不是新规则、任务账本或完整对话档案。当前执行规范仍由 RULES、AGENTS、references 和 deployment setup 文档拥有。
>
> 核对基线为 [833046a](https://github.com/FlapPearLabs/agent-engineering-governance/commit/833046a7c440a74925773d7b4fdadbf42c745c27)，材料核对日期为 2026-10-02。本页没有重跑历史产品实验；旧报告的 PASS 属于当时报告，不冒充本次实测。

## 从哪里入手

这套治理不是先画好流程，再找项目套用。早期载体是知乎项目的仓内执行纪律和 runtime MEMORY；内容获取与研究不断扩大了身份、验证、跨模块组合和会话恢复的要求。治理解决的已经不只是“让 Agent 写代码”，而是“它凭什么判断已经正确完成”。

到 8 月 25 日，讨论已涉及官方 CLI、API、Session 与跨问题研究。用户要求先核实现有能力、研究官方与成熟开源实现，再明确哪些基础能力复用、哪些是研究引擎的核心。这是需求与方法来源，不证明当时已经接受后来全部治理设计。[C01]

随后施工暴露了另一组矛盾：模块测试可以自洽而真实链路不通；聊天中的状态换会话就消失；加严评审又会滑向反复建图、低收益修复与人工搬运。9 月 5 日用户明确要求把知乎沉淀的纪律从 MEMORY 提升到全局 AGENTS / RULES，保留 Seam、增量 CodeGraph 和完整工程流程，同时去掉不适用于当前宿主的平台约定。[C03]

治理仓成立后也继续踩坑：首版权威倒置、缺少静态门、守卫自身不可证伪、饱和越过评审门、本机 fixture 让 CI 失真。后期 WebCodex 的研究与原生门缺陷提供了同类补充案例；没有证据就不把它们写成治理规则的最初来源。

## 演化索引

| 阶段 | 当时面对的问题 | 判断如何变化 | 来源与边界 |
|---|---|---|---|
| 早期知乎仓内执行 | 会话失忆、票据状态和写权不清 | 仓库与 GitHub 成为恢复依据，明确写者和集成 | [早期演化审计](../audit/WORKFLOW_EVOLUTION_MAP.md)；其“约 8 月初”是历史重建，非独立恢复的完整原文 |
| 8 月需求与设计讨论 | 现有能力、未来目标和可复用基础能力混在一起 | 先调查、核对边界，再决定核心增量 | C01、C02；用户要求与助手设计建议分开 |
| 9 月初 Ticket Lane | 自证、弱 RED、旧 SHA 评审和 CI 假通过 | 合同、反例、独立评审、exact-candidate 证据 | [痛点 P01–P16](../audit/PAIN_TO_POLICY_MAP_V2.md) |
| 9 月 5 日治理抽取 | 最大流程成本过高；MEMORY 载体不可靠 | 风险分级、Stage、饱和收敛；规范进 Git、记忆留指针 | C03；[首轮纠偏 295ce65](https://github.com/FlapPearLabs/agent-engineering-governance/commit/295ce6514f571ff0c9d8fee72b2fc11f54abc9a9) |
| 9 月中下旬机制补齐 | 原则存在，组合、生产形状与关闭证据仍缺 | PRE/POST、seam 分区、证据接口、事务保全和关闭责任 | [50b353b](https://github.com/FlapPearLabs/agent-engineering-governance/commit/50b353b8da8c50c48fbd1feb50f60b7cdb80b719)、R01；[P1 接受点](https://github.com/FlapPearLabs/agent-engineering-governance/commit/a94f509) |
| 9 月末治理自身施工 | 低层缺陷反复逃逸，守卫加固递归，饱和被外推成集成资格 | 静态门、缺陷类晋升、修复与集成权限分离 | 痛点 P20–P22；不是一次成型的正确流程 |
| 10 月测试与环境纠偏 | 私有本机状态让评审与干净 CI 得出不同结果 | 测试拥有前提与相关环境，保留历史失败模式 | [6d841d5](https://github.com/FlapPearLabs/agent-engineering-governance/commit/6d841d56fe8ccfc5ae3a0590fb73e15a57d38a48)、[833046a](https://github.com/FlapPearLabs/agent-engineering-governance/commit/833046a7c440a74925773d7b4fdadbf42c745c27) |

## H01 — 产物成功与完成证明分开

**触发与判断。** 知乎的抓取、canonical source identity、coverage 与分析质量不能由同一个“脚本跑完”覆盖。项目 D01 区分 captured 与 verified，D02 将事实权威交给 controller、语义归纳交给 model，D05 要求 orchestrator 复用已有 primitive。[Z01]

**为什么这样做。** 概率能力可以产生内容，但不能凭自己生成的内容证明“看过全部材料”或重新授予 canonical identity。8/25 的复用要求也是相邻的方法动因；不能据此编造单一事故或一次完整设计授权。[C01]

**取舍与后续。** 显式验证增加合同与 IO 成本，优点是完成事实可审计。全局只抽象证据真实性与不自证；具体 captured 状态、研究 coverage、gold 与检索算法留在知乎项目。当前落点为 [RULES R3](../RULES.md#r3-证据真实性) 与 [证据路由](../AGENTS.md#engineering-evidence-routing)。

**证据边界。** Z01 是项目决策记录，C01 是原始用户讨论；两者不证明每条后来治理机制都由该讨论直接晋升。

## H02 — 状态长于会话，MEMORY 只做导航

**触发与判断。** 早期工作流审计记录会话失忆、私有记忆承载执行状态和人工搬运；9/5 用户直接质疑只写 MEMORY 是否足够。[早期演化审计](../audit/WORKFLOW_EVOLUTION_MAP.md)、C03

**选择与理由。** 活跃状态进入 GitHub，长期项目合同进入仓文档，经验分别落到规范、测试或部署档案。固定状态索引指向这些真相，而不新建第二个知识库。

**取舍与后续。** 持久化会增加成本，因此引入“fresh Agent 缺了它是否会做出实质更差决策”的价值判断，只在有意义转换点写。新仓 bootstrap 与旧仓 lazy adoption 分开，离线不能宣称远端已同步。

**目标仓与证据源。** R01 的 L11 提议在恢复入口区分任务目标仓和证据来源仓：本次目标是治理仓，知乎用于取证。已有项目身份与 restore 是复用基础，该建议的采纳不能仅由身份字段存在推出。原回顾对“曾审错仓”的片段相互矛盾、primary locator 缺失，具体事故仍未证实；它不属于公开署名或本机身份泄露的问题。

**当前落点。** [project-state-persistence](../references/project-state-persistence.md)、[project-continuity-contract](../references/project-continuity-contract.md)、[engineering-memory](../references/engineering-memory.md)；直接提交证据包括 [4b5d9ac](https://github.com/FlapPearLabs/agent-engineering-governance/commit/4b5d9ac)。

## H03 — Seam 先于票，真实生产形状检验组合

**触发与判断。** 按功能清单拆票，会把共享 owner 拆散或制造票据形模块；单元测试采用 consumer 自己想象的 fixture，也会得到自洽绿灯。9/5 已提出 Seam-first 与“DAG 是施工排序”；D6 发生得更晚，进一步暴露执行缺口，不能写成原则的首次诞生。[C03]、痛点 P01–P03、R01

**可核对事故。** 知乎 PR #87 记录真实 synthesize 返回 Promise，T14 却同步校验。修复统一 async seam，并使用真实 runtime 构造器、注入 fake transport 的生产形状测试。[Z03]

**选择与理由。** 先冻结 producer/consumer、同步异步、生命周期和状态 owner 的合同，再产生票据。设计要求与关闭观测分区，生产可达性和真实效果另行证明。

**取舍与后续。** 更多前置合同会减慢开票，却减少晚期集成返工。工具的 prefactor 不产生架构授权；合法架构改变也不能被“DAG 非权威”反向禁止。该对立错误已在首轮再审中纠偏。

**当前落点。** [AGENTS 的 Seam-first](../AGENTS.md#4-seam-first-分解)、[ticket-lane](../references/ticket-lane.md)、[execution-stage](../references/execution-stage.md)。相关 producer identity 与 planner 产品规则仍属于知乎，不能直接升全局。

## H04 — 独立角色与 exact SHA，防止方便的自证

**触发与判断。** executor 把 self-review 当独立通过，repair 后又把旧 PASS 搬到新 HEAD；写者、reviewer 与 integrator 的责任被便利性吸收。痛点 P04–P06 保存该失效模式的历史依据，部分来自用户工程记忆和项目条款，而非完整原始执行日志。

**选择与理由。** reviewed candidate 的写权互斥，修复 append-only；适用 gate 的证据绑定 exact SHA，评审独立于实现。

**取舍与后续。** 不是所有低风险非生产票都强制独立评审；首版过宽要求经纠偏，保留“当 gate 存在时自审不能替代”。默认隔离 worktree 与集成方式可按项目权威覆盖，已评审历史不静默改写的底线保留。

**当前落点。** [RULES R4/R5](../RULES.md)、[角色模型](../AGENTS.md#1-角色模型)、[git-ci-integration](../references/git-ci-integration.md)。变更后的证据可按真实 blast radius 做增量审查，不能任意沿用。

## H05 — RED、反例与失败分类必须证明目标

**触发与判断。** 测试文件存在不证明先测；模块缺失或 harness 损坏产生的 RED 不证明目标反例；worker 自称“已知基线失败”也不能自行解锁集成。痛点 P07–P09 与 R01 的门禁入口、CI 归因回顾记录这些问题。

**选择与理由。** 行为合同用高价值反例检验，独立 reviewer 重建假设并提供独立探针；失败分类仍需相应证据与独立侧接受。LOW 的裁剪服从适用性，不机械凑反例数量。

**代价与边界。** 证据要求多于“新增了测试”；可构造合成态不等于真实可达失败。测试覆盖范围、CLI entrypoint 和 consumer 使用结构化结果是相邻但不同的证明。

**当前落点。** [ticket-lane 的 TDD](../references/ticket-lane.md#4-counterexample-first-tdd)、[git-ci-integration](../references/git-ci-integration.md)、[gate CLI 自测](../scripts/tests/test_p1_t16_gate_cli_entrypoint.py)。不会由一个 exit 0 推出整个消费者已接受。

## H06 — Stage、风险路由与高新颖性报告降低流程成本

**触发与判断。** 早期串行票据限制吞吐；更严的 Lane 又把每张票都变成最大流水线，低风险工作消耗强模型与人工搬运，报告重复“所有门通过”。[早期演化审计](../audit/WORKFLOW_EVOLUTION_MAP.md)、痛点 P14–P16

**选择与理由。** 薄 parent 做控制面，隔离 worker 直接实现；Stage 按内聚、写权、风险和集成失效半径编组，不把 DAG-ready 全部开工。评审与模型按风险路由，报告先说新知，非 PASS 证据保持展开。

**取舍与后续。** Stage 可以减少交接但也可能扩大并行冲突；显式 owner、barrier 与串行集成用于限制这一代价。直接 dispatch 不消除跨工具或中断时的 handoff 需求。

**当前落点。** [execution-stage](../references/execution-stage.md)、[skills-and-model-routing](../references/skills-and-model-routing.md)、[评审与报告](../references/review-and-repair-saturation.md)。模型派发元数据的按需 recipe 保留在路由 owner，不新增每票填表义务。

## H07 — 从 severity 停手到价值收敛，再到权限分离

**原始纠偏。** 9/5 用户指出，不同模型对 P2/P3 的边界不一致，按标签决定是否继续修仍不稳定；提出修复预算与收益递减，并类比知乎研究不能沿长尾无限找信息。这是原始用户动因，具体预算默认与仲裁机制是随后设计，不能把具体数值倒写成用户原话。[C03]

**选择与理由。** 以真实可达性、影响、证据、复杂度与回归风险判断修复价值；高价值 blocker 不因预算耗尽豁免，合法 producer 不能被防御加固误拒。痛点 P11–P13 保留这组张力。

**后来的反噬。** 治理仓自身 T18 加固出现“真 finding 就继续修”“新 SHA 重置预算”；随后又把真实饱和外推成集成资格。P22 的记录和 [0fe2d76](https://github.com/FlapPearLabs/agent-engineering-governance/commit/0fe2d76)、[495f7cd](https://github.com/FlapPearLabs/agent-engineering-governance/commit/495f7cda50837d81f2bb53d8d7965ac37d92759b) 是直接纠偏证据。

**当前判断。** finding 真实性、修复权限、仲裁处置和 required review gate 是不同判断；换 SHA 不自行产生预算，饱和不将阻断结论变成通过。加固治理机制本身也不递归授权更多机制。

**代价与落点。** 需要接受有理由的 backlog、route-to-owner 和明确停机，不能以零 findings 为唯一完成标准。完整机制由 [review-and-repair-saturation](../references/review-and-repair-saturation.md) 拥有；历史记录中的更强覆盖声明后来撤回，读者应保留其限定，不能只摘早期 PASS。

## H08 — 抽象经验，而不是复制最强项目的全部政策

**触发与判断。** 治理首版把知乎 ff-only 等项目政策升为全局硬要求，并规定项目不得削弱全局。外部审查指出这会让产品合同受通用流程支配。[痛点 P17/P18](../audit/PAIN_TO_POLICY_MAP_V2.md)、[295ce65](https://github.com/FlapPearLabs/agent-engineering-governance/commit/295ce6514f571ff0c9d8fee72b2fc11f54abc9a9)

**选择与理由。** 薄普适不变量保留底线，仓本地权威高于全局执行默认；显式覆盖可追溯。工具属于方法，MEMORY 属于导航。Scope 以语义授权为先，不把任何未预载文件自动判错；冻结文件清单时才按相应合同检验。

**取舍与后续。** 不能用一套最长流程覆盖所有仓，需要查清目标仓权威。平台习惯进部署档案，不把一个宿主的 shell 约定注入其他平台。[C03] 提供这一迁移要求的原始动因。

**当前落点。** [RULES R1/R6/R7/R8](../RULES.md)、[AUTHORITY_MAP_V2](../audit/AUTHORITY_MAP_V2.md)。本页不把历史台账的层级意见重新声明成新的权威。

## H09 — 增量 CodeGraph，查询独立而非图库重复

**触发与判断。** 每个 worker / reviewer 重建图，将“独立 grounding”误读为“独立全量建库”；首审还曾先假定工具机制，再做探针。[痛点 P10](../audit/PAIN_TO_POLICY_MAP_V2.md)、C03

**选择与理由。** 明确 base 图加 diff、按需 candidate-exact 与不可用降级的证据范围；初始化与增量同步根据实存 CLI 能力设计。独立的是查询、关系推理与结论，而非必然各自拥有全新库。

**取舍与后续。** 共享 base 图降低成本，但可能陈旧；需要同步、dirty 标记和明确 delta 范围，不能将其说成候选精确覆盖。工具缺失也不自动成为全局硬停机理由。

**当前落点。** [codegraph-grounding](../references/codegraph-grounding.md)、[project-continuity-contract](../references/project-continuity-contract.md)。探针与生命周期回归支撑具体能力，不能从方法原则直接推定所有 runtime 已接线。

## H10 — 拆票前后都有证明，组合不能靠会话连续性

**触发与判断。** 9/16 的分解场景暴露：单票合法、DAG 合法，组合合同仍可能不成立；上下文连续和字段齐全被误当证明。[痛点 P19](../audit/PAIN_TO_POLICY_MAP_V2.md) 明确将其记为 owner 报告的工作流风险，不声称已经复现生产事故。

**选择与理由。** 分解前确认上游权威收敛，分解后检验票集的合同兼容及独立 conformance。新旧会话都要走后置证明，但允许复用未失效的前置证据。

**取舍与后续。** 增加组合检查，不给每次普通编辑增加流程；全局只定义证明义务，项目拥有实际语义。该界限也防止流程借机重开已批准架构。

**当前落点。** [execution-stage](../references/execution-stage.md)、[实施与反例记录](../audit/SPEC_TICKET_GATE_IMPLEMENTATION.md)、[50b353b](https://github.com/FlapPearLabs/agent-engineering-governance/commit/50b353b8da8c50c48fbd1feb50f60b7cdb80b719)。

## H11 — 证据接口很薄，机器不自批语义

**触发与判断。** 评审材料散落，结构合法与来源真实、足够证明容易混淆；复用证据会过期，引用又可能被误当取回或执行授权。R01 的 L04/L15 提出机制缺口，当时的 NEXT 建议不等于后来全部实现。

**选择与理由。** 将结构、来源核验和充分性分开，并绑定 subject、candidate 与失效描述；用既有 collector / validator 消费声明，不另建 tracker、网络客户端或自动 reviewer。

**后续纠偏与代价。** 接口 pattern 的求值语义必须与声明一致，不能用方便的近似引擎接受不同集合；取回边界先判决，再做允许的操作。机器报告不会授予语义 scope 接受或 reviewer verdict，独立消费者仍需自行判断。

**实际可见性另行证明。** 8/28 用户要求固定 SHA 外审读取原始权威与实验。[C02] R01 L09 回顾了 primary 正文不可见、结论为 MORE_EVIDENCE_REQUIRED 的外审：文件列表或摘要不能证明 reviewer 看到了正文。“上下文足以作本次决策审计”与“完整历史 transcript 可得”回答不同问题，分别判断才能保留有界结论。9/20 [975c559](https://github.com/FlapPearLabs/agent-engineering-governance/commit/975c559fa9cfcabc012dcb9fb96ffadf32594b03) 落成按需可见性 recipe，随后 [0046c36](https://github.com/FlapPearLabs/agent-engineering-governance/commit/0046c3648c4e6b2530c06cfce80df30c64d66ab6) 将缺可见性陈述的 NOT_AUDITABLE 限定为已启用 recipe 时触发，避免扩成每票义务。历史外审结果仍是 R01 的回顾，本页未重跑该实验。

**当前落点。** [review-evidence](../references/review-evidence.md)、[schema](../schemas/review-evidence.schema.json)、[review_evidence.py](../scripts/review_evidence.py)、[git-ci-integration](../references/git-ci-integration.md)。这些具体提交把部分回顾建议落成机制，不能因此称完整 review harness 或所有生产消费者已实现。

可见性 recipe 的独立 owner 为 [review-and-repair-saturation §7](../references/review-and-repair-saturation.md)；其范围与机器证据接口分开，本页不复制字段或新建强制门。

## H12 — 保全、回读和真实关闭比一句 done 更重要

**触发与判断。** R01 记录 D6 执行报告中的 stash 恢复事故，但报告前后对 objects / pack 的描述不一致，底层因果未闭合；它支持保全要求，不能支持全局禁止 stash。另有共享 MEMORY 的多项修改遗漏，以及关闭、owner 指令和保证术语缺少 durable 证据的风险。

**选择与理由。** 破坏性动作考虑前后状态与保全集；共享 canonical 文件单写者，修改后逐条回读；learning 关闭需处置、理由和验证；orchestrator 的关闭依据必须由所需门和可引用证据支撑。

**取舍与后续。** 状态与事务记录有成本，因此 recipe 按需使用。补丁可恢复不证明物理原子，进程崩溃安全不证明断电持久，内容完整不直接授予复用权限。CI 绿也不能补出没被测试的更强保证。

**当前落点。** [git-ci-integration](../references/git-ci-integration.md)、[ticket-lane](../references/ticket-lane.md)、[engineering-memory 的 learning 与关闭责任](../references/engineering-memory.md)。[a920c6b](https://github.com/FlapPearLabs/agent-engineering-governance/commit/a920c6b) 是 M1–M9 落地证据，不能把这些职责约束自动等同于通用运行时强制。

## H13 — 先把机器可判缺陷交给最低可靠层

**触发与判断。** 知乎 PR #85 撤销“DeepSeek 不能遵守空 constraints”的旧归因：被测 planner 已损坏。修复恢复可执行性并增加语法和聚焦测试门。[Z02] 治理仓自己的 P20 基线则直接记录代码面存在、相称静态门缺失，correctness 检查能廉价找到重复缺陷。

**选择与理由。** 先发现仓内配置与受影响语言，执行适用静态门，再进入更贵的动态测试与评审；缺陷类是否值得晋升由误报、成本、可靠性和语义稳定性决定，一次出现不自动扩散规则。

**取舍与后续。** 首次静态采纳保持最小 correctness 面，不借机样式迁移；FAST 与 FULL 是证据类别，不强迫两个 CI job。工具判定与行为测试仍互补，不能由 lint 冒充语义证明。

**证据边界与落点。** P20 当时把知乎事故标为 owner-briefed，本页另核到 Z02 作为补充证据，不回写历史记录。当前 owner 是 [静态框架](../references/static-analysis-and-code-intelligence.md)、[语言 profiles](../references/static-tooling-profiles.md)、[票级收据](../references/ticket-lane.md)；P20/P21/P22 也展示加固守卫自身需要负控且必须防递归。

## H14 — 注入与 hook 用实际运行时证据修正

**触发与判断。** 全文放 MEMORY 会被截断；早期“WorkBuddy 不自动加载项目 AGENTS”的结论后来被源码证伪。修正为 guidance 首个存在者、profile 限定的截断与显式读全文路径；不能继续沿用早期假设。[cf7034c](https://github.com/FlapPearLabs/agent-engineering-governance/commit/cf7034cb543ce8fc60d783bcdc48f1738daf1aac)

**选择与理由。** 治理内容放 Git，注入载体留短指针，开工清单读取原文；自动注入覆盖、可达、全文自动送达和机械强制分开验证。预算的单位与观测截断点也不能互相定义，数值与语义只引用 [BOOTSTRAP_CONTRACT](../deployment/BOOTSTRAP_CONTRACT.md)。

**后续纠偏。** WorkBuddy Git hook 的假强推向量经实测撤回，真实向量补上；逐写法加正则又暴露结构边界。9/28 已有文档化拒绝面的接线与真实 deny 记录，当前适配器在该限定 profile 下记为 ENFORCED；不是早期的 live NOT_RUN，也不是完整强推防护或沙箱。

**代价与落点。** 文本分类器接受部分假阳性，也披露 shell 求值、外部 config 等未覆盖；升级宿主后证据不能自动续期。[适配器说明](../adapters/workbuddy/README.md)、[AS-IS V3](../audit/AS_IS_WORKBUDDY_V3.md) 保存实际范围。总体 bootstrap live 仍为 PARTIAL，与限定 hook 生效是不同结论。

## H15 — 治理仓自身暴露 fixture 与环境归属

**触发与判断。** 部署维护记录凭据解析优先级后，local-only 档案暴露 scratch fixture 复制全目录的问题。随后新测试含真实本机身份，又假定私有文件已在开发者机器存在；两个评审通过的环境不等于干净 CI。[72cd1a2](https://github.com/FlapPearLabs/agent-engineering-governance/commit/72cd1a26dd62fd23d43491f0137f667f49f9ada6)、[6d841d5](https://github.com/FlapPearLabs/agent-engineering-governance/commit/6d841d56fe8ccfc5ae3a0590fb73e15a57d38a48)

**选择与理由。** scratch 候选面按 Git 的 tracked 与未忽略 untracked 语义枚举；测试自建文件与 fake identity，控制相关 ambient environment。负控保留同一历史失败模式，不能让无关 fixture 损坏替代 RED。

**取舍与后续。** 检测与测试本身也可能泄露宿主身份；[2006796](https://github.com/FlapPearLabs/agent-engineering-governance/commit/200679649f1ff3fe78cad53fd1006b83ddf792aa) 的 fixture 片段检测是具体加固。测试工程要求只针对相关环境因素，不等于每个测试清空全部环境；干净 checkout 也不证明所有环境依赖都不存在。

**当前落点。** [ticket-lane 的测试工程契约](../references/ticket-lane.md#42-test-engineering-contract)，采纳提交 [833046a](https://github.com/FlapPearLabs/agent-engineering-governance/commit/833046a7c440a74925773d7b4fdadbf42c745c27)。宿主凭据 workaround 仍是 profile 经验，不升成跨平台规则。

## H16 — WebCodex 补充案例：门也必须能失败

**可核对材料。** 9/29 研究分支的 REVIEW_HANDOFF 记录 R29–R33 的反复审查、被拒结论和 R34 未评审修改；固定到该研究快照，不把当时的 NO_PRODUCTION_IMPLEMENTATION 描述当作项目后续状态。[W01]

**教训与代价。** 删除人类审批需求、追加“撤回”措辞或把矛盾移到下游文档，都不能代替真实设计修正。verify.py 的 criterion-reference 子检查因负控失败而停用，其他词法自检仍在运行；这说明 verifier 的绿灯需要可证伪的含义。架构报告是执行者陈述，不是独立安全验收。

**后续直接证据。** 原生门修复提交记录两个组合缺陷：前一个失败 suite 的退出码被后一个成功命令掩盖；PASS marker 在实际断言前输出。修复为独立退出码、断言后输出以及聚合规则的针对性负控。[W02]

**归属与边界。** 这是对既有证据真实性、门入口自测和测试工程的补充验证案例。尚未核到用户明确将这些 WebCodex 事故晋升到本治理仓的记录；也不把 ExecutionBroker、Seatbelt 或其审批设计写成全局治理要求。

## H17 — 从技能盘点到施工证据与使用后汇报

**起因。** 2026-10-02 本次文档审计中，用户追问“有没有要求用对应的 skill，把 skill 嵌入流程”，随后明确要求补齐三处缺口并要求 Agent 使用 Skill 后汇报。检查基线 [7738cb1](https://github.com/FlapPearLabs/agent-engineering-governance/commit/7738cb1107ee6b629b75b2a61ccec1c503fbd454)发现：阶段路由虽存在但入口与生命周期接线不充分；专业 Skill 的一般匹配义务缺位；校验器仅查清单、不能核对本票执行记录。

**选择与代价。** 保留固定工作流 owner，把专业 Skill 作为补充方法；完整读取、实际执行/fallback、使用后短报形成票级证据。增加薄记录校验，沿用原证据 artifact 槽，不改旧 schema 或宿主 hook。代价是少量记录与汇报；同阶段连续步骤可合并，全文日志不进入用户正文，LOW 不因目录齐全而跑全链。

**证据边界与落点。** 这是用户要求与仓内材料审计，不是恢复到的知乎/WebCodex 已复现事故，亦不宣称已完成各 runtime live enforcement。机械校验不证明语义应用或消息送达；原始事件与产物仍需消费者判断。规范落点 = [Skill 路由 §1.1–§1.4](../references/skills-and-model-routing.md#11-开工阶段转换与专业-skill-选择)；审计记录 = [P23](../audit/PAIN_TO_POLICY_MAP_V2.md#p23-skill-停留在盘点实际施工与使用后汇报缺接线2026-10-02-增补)。

## 覆盖映射：避免选择性复盘

下表只将已有痛点导向本页解释，不重声明其 SHOULD_BE_GLOBAL 判定或规范取值。原始痛点、证据强弱及执行面仍在 [PAIN_TO_POLICY_MAP_V2](../audit/PAIN_TO_POLICY_MAP_V2.md)。

| 原有痛点 | 本页解释 | 当前规范导航 |
|---|---|---|
| P01 实现发明架构 | H03、H08 | AGENTS Seam-first；RULES scope |
| P02 DAG 塑造架构 | H03、H10 | execution-stage |
| P03 票据缝错位 | H03、H06 | ticket-lane；execution-stage |
| P04 共享工作树污染 | H04、H12 | ticket-lane；git-ci-integration |
| P05 Worker 自批 | H04 | RULES 独立评审；角色模型 |
| P06 旧 SHA 评审沿用 | H04、H11 | git-ci-integration |
| P07 弱 RED | H05、H15 | ticket-lane |
| P08 反例不足 | H05 | ticket-lane；review-and-repair-saturation |
| P09 CI 基线自分类 | H05、H11 | RULES 真实性；git-ci-integration |
| P10 全量建图仪式 | H09 | codegraph-grounding |
| P11 无限加固 | H07 | review-and-repair-saturation |
| P12 合成态枚举 | H05、H07 | review-and-repair-saturation |
| P13 合法输出被拒 | H07、H14 | ticket-lane；review-and-repair-saturation |
| P14 贵评审滥用 | H06 | skills-and-model-routing |
| P15 Prompt 搬运 | H02、H06 | execution-stage；PORTABLE_SETUP |
| P16 冗长低新颖报告 | H06 | review-and-repair-saturation |
| P17 仓政策全局化 | H08 | RULES；AUTHORITY_MAP_V2 |
| P18 全局压倒仓政策 | H08 | RULES；AUTHORITY_MAP_V2 |
| P19 分解组合失效 | H10 | execution-stage |
| P20 机器可证缺陷逃逸 | H13 | 静态框架 |
| P21 缺陷类晋升缺位 | H13 | 静态框架；ticket-lane |
| P22 finding 扩权、预算重置、饱和越过评审 | H07 | review-and-repair-saturation |
| P23 Skill 盘点与本票执行脱节 | H17 | 本次审计补充；不冒充历史事故 |

9/16 回顾的 17 项经验也逐项定位，防止“已覆盖”被误读为“当时全部实现”。原始 L 编号来自 R01，落地情况以本页基线的实际规范为准。

| 回顾条目 | 本页解释 | 核对重点 |
|---|---|---|
| L01 真实形状 seam | H03 | D6 强化既有原则 |
| L02 生产可达性 | H03、H11 | 组件与生产入口证据分开 |
| L03 门入口自测 | H05、H16 | collector / CLI / consumer 各自证明 |
| L04 机器证据与分级 harness | H06、H11 | 有接口不等于完整 harness |
| L05 Stage 自治 | H06 | 已有授权与 barrier |
| L06 冻结候选与增量重审 | H04、H11 | exact candidate 与失效 |
| L07 拆票一致性 | H10 | PRE 与 POST |
| L08 ADR 与 Seam 解释权 | H01、H03 | 项目设计 owner 保留 |
| L09 审计可见性 | H11 | primary 实际可见性、两个完整度问题与按需边界 |
| L10 破坏性事务 | H12 | 保全，不泛化 stash 根因 |
| L11 项目身份 | H02 | 目标仓与证据源角色；错仓事故与建议采纳均不冒充已证实 |
| L12 远端持久与真实加载 | H02、H14 | Git 中存在不等于注入 |
| L13 CI 与先代码后模型归因 | H05、H13 | D4 的被测实现损坏 |
| L14 单写者与回读 | H04、H12 | 共享基础设施也属于写面 |
| L15 证据复用与失效 | H04、H11 | 可复用不等于永远有效 |
| L16 经验恢复与关闭 | H02、H12 | 处置、理由和验证引用 |
| L17 模型派发 | H06 | 风险与可用能力，不仅是模型名单 |

## 来源索引与证据边界

| 编号 | 来源 | 本页使用方式 |
|---|---|---|
| C01 | 私有原始对话导出《分支 · 自主循环提示词》；导出所载 2026-08-25 16:21、19:44、19:58 用户消息 | 需求扩展、先调查和复用要求；本页为净化后的归纳，不公开整份对话 |
| C02 | 私有原始对话导出《审计结论摘要》；2026-08-28 00:04 用户的固定 SHA 外审请求 | 要求读原始权威与实验，分别 steelman 简单/复杂方案；不是外审已通过的证据 |
| C03 | 私有原始对话导出《分支 · 项目状态交接总结》；2026-09-05 00:54、14:41 用户消息 | 价值收敛、治理出 MEMORY、Seam / DAG / 增量图 / 平台卫生；助手后续方案不混作用户原话 |
| R01 | 私有导出《P1_AGENT_ENGINEERING_RETROSPECTIVE_FINAL_2026-09-16.md》 | 后续证据回顾；用它定位 L01–L17 与缺口，不把摘要当成原始实测 |
| Z01 | [知乎 key-decisions，固定快照](https://github.com/FlapPearLabs/zhihu-grabber-toolkit/blob/2afe106ea9e5420c84ad8a240dfa9bae01b012cd/docs/architecture/key-decisions.md) | 项目设计的原因与代价；D01–D12 编号不等于事故 D1–D6 |
| Z02 | [知乎 PR #85](https://github.com/FlapPearLabs/zhihu-grabber-toolkit/pull/85)，候选 [5de2360](https://github.com/FlapPearLabs/zhihu-grabber-toolkit/commit/5de2360b1434a0c21dfa0265665adfb43f6c50f6) | 可执行实现损坏、旧模型归因撤回与 CI 最小补门 |
| Z03 | [知乎 PR #87](https://github.com/FlapPearLabs/zhihu-grabber-toolkit/pull/87)，候选 [9444a33](https://github.com/FlapPearLabs/zhihu-grabber-toolkit/commit/9444a33b3ca24a53f8da4b9e2cb03a241925f47f) | 同步 double 与异步生产 adapter 不一致的直接修复记录 |
| W01 | [WebCodex REVIEW_HANDOFF，研究快照 eda5a65](https://github.com/FlapPearLabs/webcodex/blob/eda5a659df0710b84de5becc9b3bebbb3fc51575/REVIEW_HANDOFF.md) | 当时研究/评审状态与自检限制，不证明后来实现或安全验收 |
| W02 | [WebCodex 原生门修复 909ffb0](https://github.com/FlapPearLabs/webcodex/commit/909ffb02bfa241384a5daa790f47c5b64bd461e3) | 退出码遮蔽、提前 PASS 与聚合自测的具体代码变更 |
| G01 | [WORKFLOW_EVOLUTION_MAP](../audit/WORKFLOW_EVOLUTION_MAP.md) | 早期世代与反噬的历史重建；其中 CURRENT TARGET / TO-BE 是成文时状态 |
| G02 | [PAIN_TO_POLICY_MAP_V2](../audit/PAIN_TO_POLICY_MAP_V2.md) | P01–P22 的原证据强弱、政策取舍和纠偏 |
| G03 | [AUTHORITY_MAP_V2](../audit/AUTHORITY_MAP_V2.md)、[AUDIT_QUALITY_REVIEW](../audit/AUDIT_QUALITY_REVIEW.md) | 首轮审计自身的权威与证据纠偏 |
| C04 | 本次会话 2026-10-02 的用户要求与基线 7738cb1 仓内审计 | Skill 接入、三处缺口及使用后汇报；不是历史生产事故证明 |
| G04 | [AS_IS_WORKBUDDY_V3](../audit/AS_IS_WORKBUDDY_V3.md)、[WorkBuddy adapter](../adapters/workbuddy/README.md) | 限定 profile 的注入与 hook 观测，保留未覆盖 |

**置信度使用。** 固定提交内容与已恢复的用户要求具有高置信度；只有工程记忆、后续摘要或执行者自报的事故原因保持中等或更低置信度，不写成独立复现。历史测试数量与底层 stash 根因缺证时不补造。

**覆盖限制。** 本页覆盖目前定位到的治理相关决策及上述两份经验台账，不声称检索了全部项目、全部历史原文或所有分支。尚无明确晋升链的其他施工经验保持项目案例；新证据到来后可补出处或纠正归因，不据此自动新增规则。
