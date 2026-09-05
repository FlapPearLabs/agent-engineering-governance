# PAIN_TO_POLICY_MAP_V2 — 从真实失效重建（不从候选规则倒推）

> 方法：先找 REAL INCIDENT / REPEATED FAILURE（证据：git 史、项目 AGENTS/RULES 文本对应的条款动因、用户工程记忆），再推导政策，再判定 SHOULD_BE_GLOBAL 与执行面。
> PAIN_TO_POLICY_FROZEN = YES。
> 证据记号：ZH=zhihu-grabber-toolkit（只读）；MEM=用户工程记忆；GOV=本治理仓首审产物。

## P01 实现期间发明架构
- REAL INCIDENT / REPEATED FAILURE：实现 agent 在票内自造模块/启发式，替代既有权威模块（MEM；ZH AGENTS §18.3 "FROZEN AUTHORITY IS MECHANICALLY CONSUMED" 即其制度化产物）。
- SOURCE_EVIDENCE：ZH AGENTS §18.3 原文；ZH RULES §6/§8 STOP 条款。
- ROOT_CAUSE：实现者默认"补齐比停下来便宜"。
- WHAT_WENT_WRONG：局部方便启发式替代 canonical 语义。
- POLICY_INTENDED：CONTRACT_GAP STOP；冻结权威机械消费；合同抽取义务。
- WHAT_POLICY_LATER_BROKE：无重大反噬；偶尔过度 STOP（表现为频繁上报）。
- CURRENT_BEST_ABSTRACTION：实现≠架构权威；缺语义即 STOP。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**（B 层不含此项；D 层默认 + 仓可加严）。
- CAN_BE_MACHINE_ENFORCED：部分（L0 diff 语义比对困难 → 靠评审）。
- NEEDS_AGENT_JUDGMENT = YES（识别"我在发明语义"）。
- NEEDS_HUMAN_JUDGMENT = NO（STOP 后由 owner 裁决属常规流程）。

## P02 DAG 塑造架构 / 票据形模块
- REAL INCIDENT：分解产物反向驱动模块设计，制造假缝（MEM）。
- SOURCE_EVIDENCE：`/to-tickets` "work the frontier"+prefactor 条款原文（GOV 首审引用）；ZH ticket 契约文档普遍按"行为切片"表述。
- ROOT_CAUSE：分解工具输出被当作架构输入。
- POLICY_INTENDED：seam-first 顺序 + 分解 lint。
- WHAT_POLICY_LATER_BROKE：首审把"DAG 非权威"写死，可能反向禁止**合法**架构性分解（评审 F 项关于对立错误的提醒）。
- BEST_ABSTRACTION：架构/自然缝 → 票 → DAG；依赖边若是执行排程则非合同，若暴露真实合同则升格为架构决策。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**。
- MACHINE_ENFORCED：NO（判断型）。AGENT_JUDGMENT = YES。HUMAN_JUDGMENT = 升格为架构决策时 YES。

## P03 票据缝放错位（共享 owner 拆两票 / 无关行为塞一票）
- REAL INCIDENT：两票共享同一状态 owner 导致互相 invalidate；大票无法独立评审（MEM）。
- SOURCE_EVIDENCE：ZH worktree 史（t08/t08-reform 并存 = 同票重建）；Stage 编组输入清单（GOV）。
- ROOT_CAUSE：分解只看功能清单不看所有权。
- POLICY_INTENDED：票 = 内聚行为 + 自然缝 + 显式 owner。
- LATER_BROKE：无（默认未强制执行到位）。
- BEST_ABSTRACTION：共享 owner/状态 → 一票或显式集成票；owner 冲突 → 回架构层。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**。

## P04 共享工作树污染
- REAL INCIDENT：多 agent 写同一分支/目录互相覆盖（MEM；ZH AGENTS §8.1 单写者规则为制度化产物）。
- SOURCE_EVIDENCE：ZH AGENTS §8.1 原文。
- ROOT_CAUSE：无写权契约。
- POLICY_INTENDED：ONE ACTIVE WRITER per branch；跨分支并行。
- LATER_BROKE：无重大；但全局化为硬规则会阻碍合法共享迁移场景（评审 §9 提醒）。
- BEST_ABSTRACTION：同一 reviewed candidate 不得并发变异（B 层邻域）；工作树隔离 = 默认而非普适。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**（硬核：candidate 变异互斥）。

## P05 Worker 自批
- REAL INCIDENT：executor 将 self-review 当独立评审 PASS（MEM；ZH RULES §9 明文）。
- SOURCE_EVIDENCE：ZH AGENTS §4.2/§4.3、RULES §9。
- ROOT_CAUSE：角色吸收（方便）。
- POLICY_INTENDED：SELF_REVIEW != INDEPENDENT_REVIEW。
- LATER_BROKE：F3 指出"每个 PASS 都必须有独立评审者"过宽（LOW 非生产票被误伤）。
- BEST_ABSTRACTION：**当存在独立评审 gate 时**自审不满足之；gate 是否存在由风险级 + 仓政策决定。
- SHOULD_BE_GLOBAL = **YES**（B 层：评审独立性语义本身）。
- MACHINE_ENFORCED：部分（PASS 记录字段校验可机器做）。

## P06 SHA 变更后沿用旧评审
- REAL INCIDENT：repair 后旧 PASS 被转移到新 HEAD（MEM；ZH RULES §8 明文 "PASS 只绑定 exact reviewed SHA"）。
- SOURCE_EVIDENCE：ZH RULES §8/AGENTS §7。
- ROOT_CAUSE：SHA 与评审证据解耦。
- POLICY_INTENDED：exact-SHA 绑定 + append-only repair。
- LATER_BROKE：无；delta 评审细则需按 blast radius 弹性（已入 reference）。
- BEST_ABSTRACTION：生产代码变更 → 旧评审对该变更失效；reviewed/published 历史不静默改写。
- SHOULD_BE_GLOBAL = **YES**（B 层 ④ + D 层协议细节）。

## P07 弱 TDD RED 证据
- REAL INCIDENT："tests were added" 冒充 TDD；RED 由 harness 损坏/模块缺失构成（MEM）。
- SOURCE_EVIDENCE：ZH AGENTS §18.2（"Tests must be observed RED"）。
- ROOT_CAUSE：证据形态未定义。
- POLICY_INTENDED：COUNTEREXAMPLE_SPECIFIC_RED 标准。
- LATER_BROKE：LOW 票被要求同等证据 → 过度（风险分级已修）。
- BEST_ABSTRACTION：有正确性行为的票才强制；RED 必须由目标反例断言触发。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**（分级适用）。

## P08 反例不足
- REAL INCIDENT：worker 测试与评审共享盲区（MEM）。
- SOURCE_EVIDENCE：ZH AGENTS §5.2 / 评审新反例义务。
- ROOT_CAUSE：同源假设链。
- POLICY_INTENDED：fresh reviewer ≥2 新反例；探索预算 2–4。
- LATER_BROKE：机械凑数风险（已有 NEW_CASE != NEW_INFORMATION 对冲）。
- BEST_ABSTRACTION：独立反例义务绑定独立评审 gate 存在时。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**。

## P09 CI 基线自分类
- REAL INCIDENT：worker 自称 KNOWN_BASELINE_FAILURE 放行（MEM；ZH RULES §10 + MEMORY CI 例外块）。
- SOURCE_EVIDENCE：ZH RULES §10；MEMORY 报告 override（截断区）。
- ROOT_CAUSE：分类权与证据权混淆。
- POLICY_INTENDED：PROPOSAL_ONLY + REVIEWER_ACCEPTED + 9 字段证据。
- LATER_BROKE：无。
- BEST_ABSTRACTION：非 PASS 分类 = 提案，接受权在独立侧。
- SHOULD_BE_GLOBAL = **YES**（证据真实性 B 层的具体化）。

## P10 CodeGraph 全量重建仪式
- REAL INCIDENT：每 worker/评审重建图库（MEM）。
- SOURCE_EVIDENCE：MEMORY Lane V2 independence 语义；E-02 探针（sync/impact/status 实存）。
- ROOT_CAUSE：把"独立 grounding"误解为"独立重建"。
- POLICY_INTENDED：INDEPENDENT_QUERY != INDEPENDENT_REINDEX；canonical db + sync。
- LATER_BROKE：首审把"canonical @ master"写成机制而未验证工具（F5 相关）；且每目录一库的现实与"共享库"表述矛盾。
- BEST_ABSTRACTION：主仓库 = canonical；lane 用 `sync`（增量）或查询 daemon；独立的是**查询与证据**，不是库。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**（无 CodeGraph 的仓需降级路径）。

## P11 评审无限防御加固
- REAL INCIDENT：T10 系列 5+ 轮 fix/repair（ZH git 史实测）；更早 T09 类收敛失控（MEM）。
- SOURCE_EVIDENCE：ZH `git log`（b4d9d53→b726c87→27a7fcb→4226bc3 连续修复）；MEMORY saturation override。
- ROOT_CAUSE：severity 标签自动授权修复。
- POLICY_INTENDED：SEVERITY != REPAIR_AUTHORITY；budget；Arbiter。
- LATER_BROKE：budget=2 硬数字全局化过强（评审 §11 质询）。
- BEST_ABSTRACTION：预算 = 默认可覆盖；不可让步的是"高价值 blocker 永不豁免"。
- SHOULD_BE_GLOBAL = **YES（原则）/ DEFAULT（数值）**。

## P12 合成态枚举
- REAL INCIDENT：评审员枚举 ARBITRARY_SYNTHETIC_STATE 凑 findings（MEM）。
- SOURCE_EVIDENCE：MEMORY saturation override reachability 三分类。
- ROOT_CAUSE：把"能构造"当"能发生"。
- POLICY_INTENDED：REACHABILITY 三分类。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**。

## P13 合法输出被拒（过度拒绝）
- REAL INCIDENT：加固引入对当前合法 producer 输出的拒绝（MEM；ZH t10 default-deny 修复链显示该张力真实存在）。
- SOURCE_EVIDENCE：ZH T10 修复史；MEMORY LEGAL_RUNTIME_REGRESSION_RISK。
- POLICY_INTENDED：FAIL-CLOSED + VALID-PRODUCER ACCEPTANCE 双问。
- SHOULD_BE_GLOBAL = **YES**（跨仓有效的工程经济原则，可机器部分校验=新拒绝路径须附合法输出枚举）。

## P14 贵评审滥用
- REAL INCIDENT：低风险票消耗 Sol 级评审/人工搬运（MEM）。
- SOURCE_EVIDENCE：ZH AGENTS §16（不再要求每票人工 handoff）。
- POLICY_INTENDED：L0/L1/L2 + 升级触发。
- LATER_BROKE：F3 LOW 行自相矛盾。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**。

## P15 Prompt 搬运负担
- REAL INCIDENT：用户在票间/agent 间手工复制 prompt（MEM；ZH AGENTS §2.1 整节为制度化产物）。
- SOURCE_EVIDENCE：ZH AGENTS §2.1 repository-first compression。
- POLICY_INTENDED：直接 dispatch；最小 packet；PRE-EXTERNAL BARRIER。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**。

## P16 报告冗长低新颖
- REAL INCIDENT：流水账报告（MEM；ZH AGENTS §2.1.6 output verbosity contract）。
- SOURCE_EVIDENCE：ZH §2.1.6；MEMORY novelty-first override。
- POLICY_INTENDED：novelty-first 模板 + PASS_ONLY 压缩。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**。

## P17 项目治理被复制到全局
- REAL INCIDENT：首审把 zhihu 的 ff-only/reset/单写者等**仓政策**升格为全局硬规则（GOV 首审 RULES R4/R13；外部 F4 实锤）。
- SOURCE_EVIDENCE：GOV RULES.md V1 vs ZH RULES §8 对照。
- ROOT_CAUSE：从最强实践仓归纳时未做层归属。
- POLICY_INTENDED：AUTHORITY_MAP_V2 分层 + SHOULD_BE_GLOBAL 判定栏。
- SHOULD_BE_GLOBAL = **NO（针对字面）；YES（针对抽象原则）**。

## P18 全局工作流意外压倒仓政策
- REAL INCIDENT：首审候选 AGENTS/RULES 声明"项目不得弱化全局"（GOV AGENTS V1 §0；外部 F1 实锤）。
- SOURCE_EVIDENCE：GOV AGENTS.md/RULES.md/README/AUTHORITY_MAP_V1/codegraph-grounding 对照评审 F1。
- ROOT_CAUSE：权威模型单一方向。
- POLICY_INTENDED：六层模型 + 显式 OVERRIDE 记录 + 冲突算法。
- SHOULD_BE_GLOBAL = **YES（分层机制本身）**。

## 汇总判定表

| PAIN | SHOULD_BE_GLOBAL | 机器可 enforce | agent 判断 | 人判断 |
|---|---|---|---|---|
| P01 实现发明架构 | DEFAULT_ONLY | 部分 | YES | 常规 STOP 流程 |
| P02 DAG 塑造架构 | DEFAULT_ONLY | NO | YES | 升格时 YES |
| P03 缝错位 | DEFAULT_ONLY | NO | YES | NO |
| P04 工作树污染 | DEFAULT_ONLY(+candidate 互斥硬核) | 部分 | 部分 | NO |
| P05 自批 | **YES** | 部分 | 部分 | NO |
| P06 SHA 失效 | **YES** | YES | NO | NO |
| P07 弱 RED | DEFAULT_ONLY | 部分 | YES | NO |
| P08 反例不足 | DEFAULT_ONLY | NO | YES | NO |
| P09 CI 自分类 | **YES** | 部分 | 部分 | 争议时 YES |
| P10 全量重建 | DEFAULT_ONLY | YES(脚本可查) | NO | NO |
| P11 无限加固 | YES(原则)/DEFAULT(数值) | NO | YES | Arbiter YES |
| P12 合成态 | DEFAULT_ONLY | NO | YES | NO |
| P13 过度拒绝 | **YES** | 部分 | YES | 豁免 YES |
| P14 贵评审滥用 | DEFAULT_ONLY | NO | YES | NO |
| P15 搬运负担 | DEFAULT_ONLY | NO | 部分 | NO |
| P16 冗长报告 | DEFAULT_ONLY | 部分 | YES | NO |
| P17 仓政策全局化 | NO(字面)/YES(原则) | YES(校验器可查) | NO | NO |
| P18 全局压倒仓 | **YES**(分层机制) | 部分 | NO | 冲突 YES |
