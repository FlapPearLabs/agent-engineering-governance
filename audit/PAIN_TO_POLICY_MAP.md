# PAIN_TO_POLICY_MAP — 痛点 → 政策溯源

> 防止治理变成官僚：每条政策都能回答"它防的是哪次真实失效"。
> WHERE_POLICY_SHOULD_LIVE 的键：RULES（硬规则）/ AGENTS（执行架构）/ REF（references 详情）/ MEM（仅记忆指针）/ PROJECT（留在项目，不全局化字面）。

## P-01 实现期间发明架构

- PAIN：agent 边实现边造模块，票据 DAG 反向塑造系统。
- REAL FAILURE MODE：票据形状的假缝进入生产代码；实现票静默变成架构票。
- POLICY RESPONSE：`DAG_IS_EXECUTION_MODEL / DAG_IS_NOT_ARCHITECTURE_AUTHORITY`；seam-first 分解顺序成文；worker 边界（MAY NOT 修改冻结 Spec/DAG）。
- WHERE：RULES（R14 边界）+ AGENTS（seam-first 节）+ REF:execution-stage。
- HOW TO VALIDATE：抽查 `/to-tickets` 产物——每票是否有既有自然缝与显式 owner；架构类新增模块是否都能追溯到 Approved Spec/架构决策。

## P-02 合同靠猜

- PAIN：实现者静默填补合同空白、把"方便的局部启发式"冒充合同。
- REAL FAILURE MODE：success/valid/complete/identity 语义被实现偷改；`CONTRACT_GAP` 未触发 STOP。
- POLICY RESPONSE：CONTRACT EXTRACTION 义务 + "algorithm changes what success/failure/identity means → STOP"；`CONTRACT_GAP` STOP 态。
- WHERE：AGENTS（lane 生命周期节）+ REF:ticket-lane。
- HOW TO VALIDATE：MEDIUM+ 票据评审时必须存在合同字段块；missing semantics 必须 STOP 而非补齐。

## P-03 DAG 塑造架构

- PAIN：分解工具的输出（DAG）被当作架构权威。
- REAL FAILURE MODE：为满足依赖图造出票据形模块（与 P-01 同根，视角不同：分解时点）。
- POLICY RESPONSE：同 P-01 + `/to-tickets` 重定位为实现分解 + 一致性 lint（阻塞边审计、合同溯源审计、约束审计），prefactor 条款服从既有架构权威。
- WHERE：AGENTS + REF:execution-stage。
- HOW TO VALIDATE：对任何分解做"反向追溯"：每个新模块名必须能映射到既有架构概念或 Spec 名词；映射不上 = 假缝。

## P-04 共享工作树污染

- PAIN：多票共享一个工作区，互相覆盖/半成品混入。
- REAL FAILURE MODE：未完成票 A 的变更出现在票 B 的 diff 里；评审范围失真。
- POLICY RESPONSE：ONE TICKET = ONE BRANCH = ONE ISOLATED WORKTREE = ONE ACTIVE WRITER；writer takeover 纪律。
- WHERE：AGENTS（lane 契约）+ REF:git-ci-integration；RULES（R15 单写者）。
- HOW TO VALIDATE：每 lane 的 `git worktree list` 与分支映射唯一；diff 范围核验（L0 可自动）。

## P-05 Worker 自审

- PAIN：executor 自称评审通过（SELF_REVIEW == INDEPENDENT_REVIEW 混淆）。
- REAL FAILURE MODE：worker 假设 → worker 测试 → 评审共享假设 → 共同盲区。
- POLICY RESPONSE：R6 硬规则（不得自批/自合并/派生自己的 reviewer）；fresh reviewer ≥2 个新反例义务。
- WHERE：RULES + AGENTS（评审节）。
- HOW TO VALIDATE：PASS 记录必须含独立 reviewer 身份与 exact SHA；任何"自评 PASS"直接无效。

## P-06 Stale exact-SHA 评审

- PAIN：修复（哪怕一个字节）后旧 PASS 被转移。
- REAL FAILURE MODE：评审结论覆盖的不是被合并的代码。
- POLICY RESPONSE：R5（CODE_CHANGE → 旧评审对变更代码失效）+ delta 评审协议（blast radius 未扩张时不重读全仓）。
- WHERE：RULES + REF:git-ci-integration。
- HOW TO VALIDATE：merge gate 的机械核验：REVIEWED_HEAD == branch tip == candidate SHA（L0 可自动）。

## P-07 弱反例覆盖

- PAIN："tests were added" 冒充 TDD；RED 只是 MODULE_NOT_FOUND / harness 损坏。
- REAL FAILURE MODE：反例从未攻击真实失效类；绿灯证明力为零。
- POLICY RESPONSE：COUNTEREXAMPLE_SPECIFIC_RED 证据标准 + 高价值反例类目清单（身份/陈旧/部分完整/静默 fallback/合法输出被拒…）。
- WHERE：REF:ticket-lane + AGENTS（TDD 节）。
- HOW TO VALIDATE：RED 证据必须指名触发其失败的反例断言；reviewer 抽查 RED 复现。

## P-08 CI 基线自分类

- PAIN：worker 自称 KNOWN_BASELINE_FAILURE 从而放行。
- REAL FAILURE MODE：候选引入的回归被标注为基线问题合入 master。
- POLICY RESPONSE：R7（worker 分类 PROPOSAL_ONLY；REVIEWER_ACCEPTED_CLASSIFICATION=YES 才接受）+ 9 字段基线证据块 + 禁止坍缩状态。
- WHERE：RULES + REF:git-ci-integration。
- HOW TO VALIDATE：任何非 PASS CI 的票据包必含 generic block；KNOWN_BASELINE 额外含 9 字段（L0 可校验字段存在性）。

## P-09 CodeGraph 全量重建仪式

- PAIN：每个 worker/评审重建图库，成本高且互相陈旧。
- REAL FAILURE MODE：评审"独立 grounding"退化为"各自过期全量"；时间浪费在索引而非推理。
- POLICY RESPONSE：`INDEPENDENT_CODEGRAPH_GROUNDING != INDEPENDENT_FULL_REINDEX`；canonical graph @ master + delta sync；健康触发全量重建白名单。
- WHERE：REF:codegraph-grounding + AGENTS（CodeGraph 节）。
- HOW TO VALIDATE：lane 开始时记录 graph base SHA == 当前 master；delta 同步记录存在；全量重建必须有健康证据。

## P-10 无限防御性修复

- PAIN：review → 小 finding → repair → 更小 finding → 无限循环。
- REAL FAILURE MODE：流程成本超过工程风险；防御性加固引入合法输出回归。
- POLICY RESPONSE：SEVERITY != REPAIR_AUTHORITY；REPAIR_VALUE gate；budget=2；CONVERGENCE_ARBITER；`NO_KNOWN_HIGH_VALUE_BLOCKER + 低边际价值 → SATURATION`。
- WHERE：AGENTS（收敛节）+ REF:review-and-repair-saturation；RULES（R13 最小复杂性护栏）。
- HOW TO VALIDATE：每轮 repair 前必须有 REPAIR_VALUE 决策记录；R3+ 必须有 Arbiter 裁决而非默认继续。

## P-11 过度拒绝回归（defensive hardening）

- PAIN：新 validator/fail-closed 规则拒绝当前合法的生产输出。
- REAL FAILURE MODE：加固即回归；上游合法产物被下游新闸门打死。
- POLICY RESPONSE：R9（FAIL-CLOSED + VALID-PRODUCER ACCEPTANCE 双问）+ `LEGAL_RUNTIME_REGRESSION_RISK` 高时不自动修。
- WHERE：RULES + REF:review-and-repair-saturation（REPAIR_VALUE 输入项）。
- HOW TO VALIDATE：任何新增拒绝路径必须枚举"当前合法 producer 输出"并声明零误伤（或有授权豁免）。

## P-12 贵评审滥用

- PAIN：Sol 级/外部评审被用在确定性低风险票；或每个票都要人工跑外部评审搬运。
- REAL FAILURE MODE：评审预算耗尽在最没价值的地方；人工成为流水线瓶颈。
- POLICY RESPONSE：L0/L1/L2 分级；外部评审仅高风险/分歧/里程碑触发；`CHATGPT_EXTERNAL_REVIEW != EVERY THIRD_PARTY_REVIEW`。
- WHERE：AGENTS（评审分级）+ REF:skills-and-model-routing。
- HOW TO VALIDATE：Stage Packet 里记录每票评审档位与触发理由；LOW 票不得出现 L2。

## P-13 Prompt 搬运负担

- PAIN：用户在票与票、agent 与 agent 之间人工复制 prompt/handoff/评审包。
- REAL FAILURE MODE：人肉消息总线；上下文丢失；交接即失真。
- POLICY RESPONSE：直接结构化 dispatch 默认化；handoff 仅跨工具/中断/审计场景；PRE-EXTERNAL TERMINAL BARRIER 保证外部评审一次到位；auto-advance 条款。
- WHERE：AGENTS（auto-advance + handoff 节）。
- HOW TO VALIDATE：一个 Stage 内的人工交互次数 ≤ 触发的外部 gate 数。

## P-14 报告冗长无信息量

- PAIN：报告奖励流水账，不奖励新知。
- REAL FAILURE MODE：决策者读完仍不知道"这票揭示了什么"；关键异常被淹没。
- POLICY RESPONSE：NOVELTY-FIRST 优先序；PASS_ONLY 才压缩 CI；已知事实禁止重述；合法值 NONE。
- WHERE：REF:review-and-repair-saturation（报告模板）+ AGENTS 一句话原则。
- HOW TO VALIDATE：抽检最终包：前屏必须是 NEW_* 字段；无编造新颖性（NONE 合法）。
