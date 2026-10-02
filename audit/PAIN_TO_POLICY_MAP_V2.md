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

## P19 分解入口上下文丢失与票集组合失效（2026-09-16 增补）
- SOURCE_EVIDENCE：本次 owner 授权的外部 Spec → fresh-session 分解场景与 C1–C4 修正；属于用户报告的工作流风险，不声称已复现某个生产事故。已知关联痛点 P01/P02/P03/P06/P17/P18。
- FAILURE_CLASS：单票有效、DAG 有效但组合合同不成立；连续会话或字段齐全被当作证明。
- POLICY：R3 仅补证据真实性推论；AGENTS §4 路由；execution-stage §6 唯一拥有 PRE/POST recipe。全局证明义务与项目语义严格分离。
- R8：适用于票据分解，不给每次编辑新增流程；无相关 seam 可说明 N/A；复用有效证据，独立 POST 与既有 conformance 同次审查，避免重复劳动。
- SHOULD_BE_GLOBAL：证明真实性原则 YES；执行 recipe DEFAULT_ONLY（受 R1 与项目显式权威约束，冲突先 STOP）。
- MACHINE_ENFORCED：仅 recipe 接线与已知结构事实；SEMANTIC_JUDGMENT = INDEPENDENT_REVIEW。反例与验证边界见 `audit/SPEC_TICKET_GATE_IMPLEMENTATION.md`。

## P20 机器可证的编码缺陷逃到动态测试 / 模型评审 / CI（2026-09-28 增补）

- FAILURE_CLASS（`REGISTERED != EXECUTED` 家族）：(a) 有代码面但**无语言相称静态工具**；(b) **已配置**的静态工具没有被真正执行；(c) 机器可证的缺陷（syntax / undefined name / unused import）被留到动态测试、模型评审甚至 CI 之后才发现。
- REAL INCIDENT / REPEATED FAILURE：
  - **GOV（一手、可复现）**：本治理仓在本次采纳前含 **35 个 Python 文件 / 22,994 行**，而 `pyproject.toml` / `ruff.toml` / `.ruff.toml` / `mypy.ini` / `.flake8` / `tox.ini` / `pytest.ini` / `setup.cfg` / `requirements*.txt` / `.pre-commit-config.yaml` / `Makefile` **全部不存在**——代码面存在、语言相称静态工具完全缺失。这是本痛点在本仓的直接实例，不依赖任何外部传闻。
  - **OWNER-BRIEFED（owner 在本次任务书中提供；本仓未独立核验）**：zhihu-grabber-toolkit 曾有 JavaScript 语法缺陷抵达 master，原因是相关研究子系统没有语法门。按 RULES R3，此行标记为 **owner 报告而非已核实事实**，不得据此升级出更强的历史结论。
- SOURCE_EVIDENCE：本仓 `git ls-files` 语言普查 + 工具配置存在性检查（下方 P20 BASELINE 即其记录）；AGENTS.md 既有的 `MECHANICAL PROOF BEFORE MODEL REASONING` / `USE_REPOSITORY_NATIVE_STATIC_TOOLING_FIRST`；`references/static-analysis-and-code-intelligence.md` 旧版仅止于"发现原生工具"，**未**定义执行义务、状态语义与证据形态。
- ROOT_CAUSE：static-first 当时只是**方向**而非**可执行机制**——缺 (i) 发现协议、(ii) 已配置工具必须执行的默认、(iii) 非坍缩的状态语义、(iv) 新仓与遗留仓的采纳分流。
- WHAT_WENT_WRONG：(a) 无门 → 缺陷类只在更贵的地方被发现；(b) 有配置无执行 → `CONFIG_FILE_EXISTS` 被当成 `GATE_EXECUTED`；(c) 工具缺失被静默读作"没问题"（`NOT_CONFIGURED` 冒充 `PASS`）。
- POLICY_INTENDED：跨语言静态门框架 = 发现（`STATIC_TOOLING_DISCOVERY`）→ profile / 状态模型 → `CONFIGURED_STATIC_TOOLING_MUST_RUN` → GREENFIELD 与 LEGACY 分流 → 票级 `STATIC_GATE_RECEIPT`；本仓按其采纳最小 correctness 基线并在 CI **真实执行**。
- CURRENT_BEST_ABSTRACTION：static-first 的**机制化**。语言特定工具**不**升格为 B 层不变量——策略停在 D 层默认 + C 层仓政策（与 P17/P18 的分层结论一致）。
- R8 四问：(1) 防哪次真实失效 → 上述 (a)(b)(c)，其中 (a) 已在本仓实证；(2) 机器能否更便宜地做 → 能，且本框架**本身**就是机器门（compile / lint）；(3) 每个风险级都需要吗 → 否，静态门按"变更面是否含代码 + 仓是否已配置该工具"触发，LOW 无强制；(4) 能否降级为 reference/默认 → **是**，整套框架为 D 层默认，推荐矩阵 recommendation-only，仓可显式 OVERRIDE。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**（configured-tooling-must-run 与状态非坍缩作为 D 层默认；**不**新增 B 层条目，`RULES.md` 未改动）。
- CAN_BE_MACHINE_ENFORCED：**部分**。文档接线与"CI 是否真的执行静态门"可机械校验（`scripts/validate_governance.py` 的 `ci-executes-static-gate` / `static-gate-documentation-wiring-only`）；"某门是否适用于本次变更 / 是否真的跑过"仍需评审判断。
- NEEDS_AGENT_JUDGMENT = YES（判定变更面适用性）。NEEDS_HUMAN_JUDGMENT = NO（常规流程）。
- 与既有痛点的关系：P01 / P02（发明架构）、P19（证明真实性）邻域；本项**不**新建权威文件，canonical owner 复用既有 `references/static-analysis-and-code-intelligence.md`（避免双 owner，CE-28 语义）。
- MACHINE_ENFORCED = PARTIAL。

### P20 BASELINE（采纳前对干净 main 实测）

```text
BASELINE_TOOL      = ruff
BASELINE_COMMAND   = ruff check --no-cache --select <SET> .   （仓根执行）

BASELINE_FINDINGS_BY_CANDIDATE_SET
  E9,F          ->   5     F841 x5
  E4,E7,E9,F    ->  19     + E702 x13, + E402 x1
  E             -> 555     E501 x541, E702 x13, E402 x1
  UP            -> 143
  RUF           -> 189
  B             ->   6
  I             ->   3
  PLE           ->   0
  E9 (alone)    ->   0

FINDING_CLASSES    = correctness: 未使用变量（F841）
                     style/modernisation: 一行多语句（E702）、行过长（E501）、
                     导入位置（E402）、pyupgrade / ruff-native / isort
NOTE               = 上表以 ruff 默认 target-version 测量（与 BASELINE_COMMAND 一致）。
                     仅 `UP` 行对 target-version 敏感：同一选择在 `target-version =
                     "py312"` 下为 147 而非 143。采纳行 `E9,F` 两种设定下均为 0
                     （修复前为 5）。该差异已同步标注在 `ruff.toml`。
ADOPTION_COST      = 低。采纳 `E9,F`（correctness-only），修复 5 处 F841
                     （全部经逐点判定为行为中性），**不**触碰样式面。
                     未采纳集合保持为独立工具票的候选（§20 禁止把首次采纳
                     做成样式迁移）。
```

## P21 机械可判缺陷反复消耗独立评审预算 / 缺"缺陷类→门"晋升判定（2026-09-29 增补）

- FAILURE_CLASS：(a) 同一**确定性的低层缺陷类**在多轮评审中被反复重新发现，每轮都花费独立评审预算；(b) 已知"这类问题工具能查"，但**没有把该缺陷类下沉到机器门**的判定点，于是修复停留在"本票改掉了"而不复发预防；(c) 反向风险——为减少评审负载而无节制地新增规则，导致**规则指数扩散与误报本身成为新缺陷类**。
- REAL INCIDENT / REPEATED FAILURE：
  - **GOV（一手、可复现）**：P20 采纳的同一次 dogfood 中，本仓 `scripts/` 与 `adapters/zcode/tests/` 存在 **5 处 F841**（未使用的局部赋值）。这类缺陷**完全机械可判**（ruff `F` 规则一次命中 5 处），却在没有静态门时需要人工/评审逐个发现；P20 落地后 `ruff check .` 一次即全部检出。**这是"同一缺陷类 → 单次机械检出"的仓内一手证据。**
  - **GOV（治理侧，可复现）**：本次变更前，本仓的 `references/review-and-repair-saturation.md` 已有 `DEFECT_CLASS` 元数据（L32 附近）与 L1"不重复报告 L0 已可确定性检出的问题"，但**无**"这个缺陷类能否下沉到哪一层"的判定模型，也**无**"重复出现是否构成缺门证据"的联动规则；`references/static-analysis-and-code-intelligence.md` 旧 §4 D12 仅覆盖"**重复出现**的真实缺陷类 + 现有工具无法廉价检出"才建议新增工具——**单次**高价值可机械检出的缺陷类不在其表述内，晋升判定缺位。
  - **GOV（本票内的复发实例，一手可复现）**：P20 落地时 `ruff check .` 一次性检出并修掉了 5 处 **F841**（未使用局部赋值）。撰写本票的新测试文件时，同一**缺陷类**（未使用导入，规则 **F401**）**再次**被 `ruff check .` 命中（`test_p1_t18_defect_promotion_fast_full.py` 首个 `re` import），移除后转绿。这是"**同一确定性缺陷类在已有机械门的情况下仍会复发**"的直接证据：门存在不等于门会拦住**新引入**的同类缺陷，而人工/评审仍是最后一道发现者——支持"机械可判缺陷必须由门持续拦截"的动机，也说明 `LOCAL_FAST_GATE` 必须在写码回路内跑。
  - **OWNER-BRIEFED（owner 在本次任务书中提供；本仓未独立核验）**：任务书列举"评审轮次反复发现机械可分类问题"的通用模式。按 RULES R3，此行标记为 **owner 报告而非已核实事实**。
- SOURCE_EVIDENCE：本仓 `ruff check . --select F841` 实测命中 5 处（与 P20 BASELINE 记录的 `E9,F = 5` 一致）；`references/review-and-repair-saturation.md` §1 L1 纪律与 §4 finding 元数据（`DEFECT_CLASS` 已存在，无 `MACHINE_DETECTABLE` 轴）；`references/static-analysis-and-code-intelligence.md` 旧 §4 D12 原文；`references/git-ci-integration.md` 旧 §3 无 FAST/FULL 分类。
- ROOT_CAUSE：static-first 框架解决了"**门内**的缺陷如何执行与记账"（P20），但**没有**回答"门外的缺陷发现**是否**应被提升进门"——晋升判定缺位，导致机械可判缺陷停留在"人工发现 + 一次性修复"循环。
- WHAT_WENT_WRONG：(a) 机械可判缺陷类反复占用独立评审预算；(b) 修复后无复发预防，同类问题在下一票重新出现；(c) 缺少晋升判定也意味着**无法区分**"该下沉"与"不该下沉"，后者若处理不当会退化为规则扩散。
- POLICY_INTENDED：`references/static-analysis-and-code-intelligence.md` §21 `DEFECT_TO_GATE_PROMOTION`——按**缺陷类**（非单行）评估晋升价值（真实/高置信 + 判定确定 + 误报风险低 + 执行与维护代价低 + 语义稳定 + 无隐藏产品语义判断），沿 §21.2 层级选**最便宜可靠**层；**处置取值集合的唯一声明点 = 框架 §21.3**（本表为证据记录，不重述值域——重述即双 owner，CE-28）；`references/review-and-repair-saturation.md` §4.1 定义 reviewer **建议性**元数据（不扩权）、§6.5 定义"重复低层发现 = 缺门证据"但**一次出现 ≠ 自动晋升**；票级落点 = `references/ticket-lane.md` §9.4。
- CURRENT_BEST_ABSTRACTION：晋升是 **value-gated 判定**，不是自动规则扩散。防扩散的三个既有约束被显式复用：`BUG KNOWLEDGE → REGRESSION TEST` 保留（框架 §19，行为知识不得被 lint 替换）、`一次出现 ≠ 自动治理缺陷`、本票内下沉六条件（框架 §21.3）。`LOWEST ≠ WEAKEST`：选层标准是"可靠检出"，语义/产品判断**不得**为省评审而塞进静态检查（框架 §3）。
- R8 四问：(1) 防哪次真实失效 → 上述 (a)(b)，其中"5 处 F841 一次检出"为本仓一手证据；(2) 机器能否更便宜地做 → 能，晋升后的门就是机器门；(3) 每个风险级都需要吗 → 否，晋升判定按 `PROMOTION_VALUE` 分级，LOW/琐碎 finding **不**要求产出收据；(4) 能否降级为 reference/默认 → **是**，整套为 D 层默认 + 仓可显式 OVERRIDE，不升 B 层（`RULES.md` 未改动）。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**（晋升判定与 FAST/FULL 分类均为 D 层默认；**不**新增 B 层不变量——"任何仓必须装某个 linter"或"必须做缺陷分类"都属过度普适）。
- CAN_BE_MACHINE_ENFORCED：**部分**。可机械校验的是：值域**委托**（收据不得重述状态值域——`scripts/validate_governance.py` 的 `static_gate_wiring` 检查委托标记计数与被禁 token）、处置与 PROMOTION_VALUE 值域的**单一 owner**（本票 `scripts/tests/test_p1_t18_*.py` 的结构化检测器，遍历全仓除 owner 外的每个 md）、以及票级字段与章节指针的**存在性与可解析性**（同文件测试）。**不由机器判定**的是："`PROMOTION_VALUE` 判定"与"某缺陷类是否可靠可机械检出"——本质是判断型，需 agent 判断 + 评审确认。
- NEEDS_AGENT_JUDGMENT = YES（判定缺陷类可靠性、误报风险、晋升价值）。NEEDS_HUMAN_JUDGMENT = 争议时 YES（`KEEP_AS_HUMAN_DECISION` / 晋升需改架构时）。
- 与既有痛点的关系：P20 的**直接续篇**（P20 = 门内执行与记账；P21 = 门外缺陷是否应进门）。P14（贵评审滥用）邻域但不同：P14 是"评审预算分配"，P21 是"把可机械判的部分移出评审域"。本项**不**新建权威文件，canonical owner 全部挂在既有 references（避免双 owner，CE-28 语义）。
- MACHINE_ENFORCED = PARTIAL。

## P22 真 finding 被当作修复授权 / 新 SHA 重置修复预算（2026-09-29 增补）

> 本项证据全部来自本仓 `main` 的一手 git 史与评审 receipt，可复现；**未**新增任何外部或推测性失败史。

- FAILURE_CLASS：(a) reviewer 报告一条**真实、可复现、机制可检测**的 finding，该真实性被**隐式**当作修复授权，于是修；(b) 修复产生新 SHA，exact-SHA 评审使先前 PASS 失效；(c) fresh reviewer 在新 SHA 上又报出**同类非阻塞**弱化，(b)(c) 循环；(d) 该循环持续发生在**核心合同已满足**之后——required quorum 早已 APPROVED / 0 P0 / 0 P1。
- REAL INCIDENT / REPEATED FAILURE（本仓一手）：
  - **commit 数**：P1-T18 一票共 **12 个 commit**（`3918a93` 基线后 `4935283`/`e4ecd61`/`4832b6f`/`f7fc998`/`c705821`/`a0c30e1` 等）。
  - **PASS 早已达成仍继续施工**：到 `c705821` 为止本票已取得 `OPEN_P0=0 / OPEN_P1=0`（CONTRACT 结论记于 `a0c30e1` 的 commit message，CONSISTENCY 结论记于 `c705821` 记其父 `f7fc998` 的 message）——两票结论取自**不同 SHA**，但都早于 `a0c30e1`；其后仍追加了 `a0c30e1`（仅加一条负控测试）。
  - **元加固递归产生元加固**：r5 的负控被证明"钉住自己的副本而非被测守卫"，修其负控又需新 SHA → 新评审；r7 的 block scoping 强度只由**手工**变异建立 → r8 将其编码为套件事实。每个修复都在**加固治理装置本身**。
  - **收敛指令最终以人工方式下达**，而非由既有规则自动导出——这正是本项缺口的直接证据：仓内**有** saturation 判据（§3），但**无**"通过之后默认停止"的规则。
- ROOT_CAUSE：`FINDING_IS_TRUE` 与 `REPAIR_NOW` 之间缺一条显式否定式；`NORMAL_REVIEWER_DRIVEN_REPAIR_BUDGET = 2`（§3）规定了**数值**却未规定**计数作用域**，因而可被"新 SHA / fresh review / 新 reviewer / 模型回退"反复重置；§3 的 saturation 判据是**可判据**而非**默认态**，故不自动生效。
- WHAT_WAS_TRUE_BUT_NOT_AUTHORIZING：多数被修的 finding 确为真实且可机械检测——**真实性从未被质疑，缺的是从真实性到授权的那一步**。这使 `SEVERITY != REPAIR_AUTHORITY`（P11 已有的原则）不足以止损：finding 多数只带 P2/P3 意见，但"可机械检测"这一性质被当成了升级理由。
- POLICY_INTENDED：四条唯一声明点全部落在既有 canonical owner `references/review-and-repair-saturation.md`——**§2.1** `FINDING_IS_TRUE != REPAIR_NOW`（真 finding ≠ 修复授权；可机械检测性与 severity 标签均非授权来源）、**§3.1** 预算票作用域与单调（`NEW_SHA != NEW_REPAIR_BUDGET`，唯一合法重置途径 = 开新票）、**§4.2** POST-PASS 收敛切断（quorum PASS + 无高价值 blocker ⇒ `REPAIR_SATURATION_REACHED = YES` 为默认态，P2/P3 单独不得重开施工）、**§6.6** `META_GOVERNANCE_RECURSION_CUTOFF`（加固治理装置本身不递归授权；`MECHANIZATION_VALUE > MECHANIZATION_COST + MAINTENANCE_COST`）。与 §21 的交互 = 饱和后新机械化机会默认 `FOLLOWUP_TOOLING_TICKET`（框架 §21.3 尾段最小指针，**未**重写 §21）。
- R8 四问：(1) 防哪次真实失效 → 上述 12 commits / PASS 后仍施工 / 元加固递归；(2) 机器能否更便宜地做 → **不能且不应**——为证明散文规则而新增通用解析器、变异框架、Markdown 分类器或 guard-of-guard 本身即 §6.6 不等式所禁止，故 CAN_BE_MACHINE_ENFORCED = **NO**；(3) 每个风险级都需要吗 → 否，按 `REPAIR_VALUE` 分级，LOW 票可 L0-only 闭合；(4) 能否降级为 reference/默认 → **是**，全为 D 层默认 + 仓可显式 OVERRIDE，不升 B 层。
- SHOULD_BE_GLOBAL = **YES（原则）/ DEFAULT（数值）**。不可让步的是"**已知高价值 blocker 永不因预算耗尽而豁免**"；预算数值 2 仍为可覆盖默认值（P11 `LATER_BROKE` 的教训未被推翻）。
- CAN_BE_MACHINE_ENFORCED = **NO**（**有意**）。四条规则全部为**授权/计数/默认态**语义，判定者是**当前票权威与独立评审**，不是模式匹配器。为其新增检测器会构成 §6.6 明令禁止的递归机械化——**这是本项选择"文档 + 独立评审"作为执行层的理由，而非证据不足**。
- NEEDS_AGENT_JUDGMENT = YES（判定某 finding 是否构成高价值 blocker、是否满足 §6.6 经济不等式）。NEEDS_HUMAN_JUDGMENT = 预算上调与 CONVERGENCE_ARBITER 裁决时 YES。
- 与既有痛点的关系：P11 的**续篇且其缺口已被实测填平**——P11 记录了"severity 标签自动授权修复"并给出 `SEVERITY != REPAIR_AUTHORITY`，但**未**覆盖"finding 真实性本身充当授权"与"新 SHA 重置预算"两条路径。P21 邻域但方向相反：P21 把可机械判的部分**移出**评审域（建门），P22 防止**为建门而无限加固**（§6.6 明写该分工）。本项**不**新建权威文件、不新增 Spec、不新增检测器。
- MACHINE_ENFORCED = NO（有意；见 CAN_BE_MACHINE_ENFORCED）。

### P22 增补（2026-09-29 同票第二次纠正）：饱和被当作评审门的替代证据

> 本增补不新建记录：与上同属"权威从相邻概念被推出"这一失败族。证据分两类，下文**逐条标注**——`GIT_VERIFIABLE` = 可在本仓 git 史中核实；`SESSION_RECEIPT` = 票务会话内的一手 receipt，**不落盘在仓内**，故第三方无法从本仓复核。

- FAILURE_CLASS：required 一致性评审对 exact SHA 返回 `CHANGES_REQUESTED`（阻断性）；修复预算耗尽；CONVERGENCE_ARBITER 把该 finding 判为**非高价值**并返回 `SATURATION_REACHED`；候选**随即被集成**，而仓政策（AGENTS §8）此时仍要求合同向 + 一致性向对同一 exact HEAD 双 PASS。
- REAL INCIDENT / REPEATED FAILURE：
  - `GIT_VERIFIABLE`：`97ec802` 存在、是 `origin/main` 的祖先、其 commit message 自述 `Repair round 2 of 2`（故预算 2/2 已耗尽）。
  - `GIT_VERIFIABLE`（**逐 token 核验；语义仍是 first-party 自述**）：`495f7cda` 的 commit message 中**实际存在**的相关字面 token 只有 `CONTRACT=APPROVED`、`CONSISTENCY=CHANGES_REQUESTED`、`SATURATION_REACHED`（均无空格写法），以及对非高价值判定的**散文**表述——原文该句在 `as` 后换行（`...the remaining P1 as` / `non-high-value`），跨行拼接后逐字为 `the arbiter classified the remaining P1 as non-high-value`（对单行 `grep -cF` 命中为 0，属**折行**而非引错）。**该 message 中不存在** `HIGH_VALUE_CLASS`、`DISPOSITION`、`BACKLOG` 三个字段名（在该 message 中命中数均为 0）。在**截至 `7fa2f5d9`（= `c526d729` 之父、`15ebd5e8` 之祖父）为止、且不计本记录自身及其后继 message** 的历史中，三者命中数分别为 0 / 1 / 1，后两次落在 `0fe2d765`、与 `495f7cda` 无关，且该处 `DISPOSITION = BACKLOG` 是 §2.1 条款的**通用举例**、并非某条 finding 的处置。**复核配方**：逐 commit 跑 `git show <sha> --no-patch --format=%B | grep -cF <token>` 再对 `git rev-list --reverse 7fa2f5d9` 求和。因此本记录**不**把它们写成该 message 的逐字内容——按本文件方法论，**不得以规范化字段名冒充逐字 provenance**。（**计数口径警告**：凡**逐字点名这些 token** 的历史命中计数，都会被写下该计数的那条 commit message 自身污染——因为该 message 本身就含有这些字面 token。故此类计数必须钉住排除边界，否则数字在被写下的瞬间即失效。）即使上述 token 存在，可核实的也只是"该陈述存在"，**不是**"该陈述为真"：它仍是本仓自述，不是独立 receipt。
  - `SESSION_RECEIPT`（**不落盘在仓内**，第三方无法从本仓复核）：仲裁对该 finding 的**具体处置标签**（含其 `HIGH_VALUE_CLASS` 取值与 `DISPOSITION` 归类），以及"该候选仍被集成"这一动作本身。
  - `GIT_VERIFIABLE`（消融证据，**成立 SHA 已钉住，且计数已与实测对齐**）：删除 `audit/PAIN_TO_POLICY_MAP_V2.md` 整个 P12 章节及其汇总行后——该结果**只在修复前的 `97ec802` 上成立**（`Ran 550 tests … OK`）；在 `495f7cda` 与后续候选上同一消融为**红**。`495f7cda` 实测 `FAILED (failures=2)`；本票最终候选同样为 `FAILED (failures=2)`，failing = `test_every_pain_row_survives_in_the_roll_up_table` + `test_deleting_a_pain_section_is_detectable`。计数为 2 依赖负控中那条读**真实树**的断言；移除它则退化为 `failures=1`，但**此时守卫仍然失败**——即真实树被消融这一场景**并非**由该断言唯一覆盖，守卫同样覆盖。此处 `failures=2` 是**可复现的实测值，不是估计**。台账不因此声称任何"当前可复现的全绿"。
- ROOT_CAUSE：§4.2 的 POST-PASS 收敛切断其前置条件写的是 `REQUIRED_REVIEW_QUORUM = PASS | APPROVED`，但仓内**无**任何条款规定该条件未满足时的后果；`SATURATION_REACHED` 与 `REQUIRED_REVIEW_QUORUM_PASS` 之间**缺一条显式否定式**。于是"处置剩余 findings 的机制"被读成"判定评审结论的机制"，仲裁结论被当成了通过证据。P22 上半部分解决的是"真 finding → 修复授权"，本增补解决的是"饱和/仲裁 → 集成授权"——**同一形状的权威越界，发生在相邻的另一个门口**。
- WHAT_WAS_TRUE_BUT_NOT_AUTHORIZING：仲裁对该 finding 的**价值分类是正确的**（它确实不是 §2 高价值类），`SATURATION_REACHED` 作为**修复区耗尽**的陈述也是真的；错的只是把它**外推**为集成资格已满足。真实性与正确分类同样不构成越权依据（同 P22 上半部分的道理，此处是它的第二个应用面）。
- POLICY_INTENDED：唯一新增声明点 = `references/review-and-repair-saturation.md` **§4.3** `SATURATION != REVIEW_GATE_BYPASS`——三机制分权（`REPAIR_BUDGET` 管修复授权 / `CONVERGENCE_ARBITER` 管 findings 处置 / `REQUIRED_REVIEW_QUORUM` 管集成资格）；`SATURATION_REACHED != REQUIRED_REVIEW_QUORUM_PASS`；仲裁**不得**把 `CHANGES_REQUESTED / REQUEST_CHANGES / REJECT / FAIL` 改写为 `PASS / APPROVED`；`AUTO_REPAIR_AUTHORITY = EXHAUSTED` 与 `INTEGRATION_AUTHORITY = NOT_SATISFIED` 是**两个独立字段、可同时成立**；合法下一步仅限既有权威机制；**禁止评审者购物**。AGENTS §6 仅加指针并把声明点数由四条改为五条；§8 加一句 `SATURATION != REVIEW_GATE_BYPASS` 短原则并**自标为指针、非第二声明点**；**RULES.md 不变**。
- 同票一并修复的**已知回退**（唯一另一项授权变更）：上一轮把痛点台账守卫从硬编码 `range(1,22)` 改为按 `^## (P\d\d) ` 章节派生时，丢掉了"章节标题必须存在"的断言，而其 docstring 仍声称"删掉整节也会被抓到"。修复取**派生结构**下的最小稳定表达：章节编号**连续性**（中间无缺口）+ 汇总行与已发现章节**双向对应**；连续性判定抽成单一函数 `_pain_numbering_gaps` 供守卫与负控共用。**该锚点只覆盖"中间缺口"**：尾部截断与"删节后一致重编号"两种逃逸**原理上不可见于只读当前文档的检查**，已在守卫 docstring 中如实列为已知边界而非粉饰为已覆盖。**不**恢复任何硬编码上界，**不**新增检测器/变异框架/解析器。
- R8 四问：(1) 防哪次真实失效 → 上述 `97ec802` 集成事件与经消融证明的 P12 章节删除逃逸；(2) 机器能否更便宜地做 → 规则**部分**：§4.3 是授权/资格语义，判定者为票权威与独立评审，同 §2.1/§6.6 不新增检测器；但**该票自身的覆盖率回退**是纯结构事实，已由既有守卫的派生连续性检查覆盖；(3) 每个风险级都需要吗 → 否，治理文本按 §8 走双 quorum，产品代码票不适用；(4) 能否降级为 reference/默认 → **是**，D 层默认 + 仓可加严，不升 B 层。
- SHOULD_BE_GLOBAL = **YES（原则）**（"saturation/仲裁不得替代未满足的评审门"不可被仓政策默认放宽；仓**可以**定义更严协议，不能更松）。CAN_BE_MACHINE_ENFORCED = **NO**（有意，同上）。
- MACHINE_ENFORCED = NO（有意）。同票修复的台账守卫回退另由既有守卫覆盖，不改变本行。

## P23 Skill 停留在盘点，实际施工与使用后汇报缺接线（2026-10-02 增补）

- SOURCE_EVIDENCE：用户在本次文档审计中明确要求“补充你指出的 3 个缺口，同时要求遵守该标准的 agent 在使用 skill 后汇报”；基线 `7738cb1107ee6b629b75b2a61ccec1c503fbd454` 的 README、AGENTS、skills-and-model-routing 与 validate_governance 可直接核对。证据类型 = **USER_REQUEST + REPOSITORY_AUDIT**；不是知乎/WebCodex 历史事故复现。
- OBSERVED_GAP：已有阶段路由与可核验使用要求，但复制入口/生命周期接线不充分；缺技术栈/平台/领域的专业 Skill 一般匹配义务；机械检查只查获取清单，不消费本票执行证据及使用后报告。
- ROOT_CAUSE：可用性盘点、选择、方法执行与对用户交付没有完整连接；不能把清单通过外推成实际使用完成。
- POLICY_INTENDED / CURRENT_BEST_ABSTRACTION：唯一详情 = `references/skills-and-model-routing.md` §1.1–§1.4；专业方法补充工作流，全文读取 → 执行/fallback → 短报 → 票级附件核验。旧 review evidence artifact 槽可直接承载，不建第二 tracker。
- R8 四问：防哪次真实失效 → 防上述**已核对的规范/检查覆盖缺口**，不虚构生产事故；机器能否更便宜做 → 绑定、必需项、引用、digest、报告一致性可机械检查，语义真实性仍由消费者判断；每个风险级都需要吗 → 按触发选择，LOW 不强制 implement，全空必需集合须说明理由；能否降级为 reference/默认 → **是，D 层默认**，可由 C 层显式覆盖，不新增 B 层不变量。
- SHOULD_BE_GLOBAL = **DEFAULT_ONLY**；MECHANICAL_ENFORCEMENT = **票级 CLI 记录与附件核验 + CI 合成反例测试**，**不是各 runtime live hook**。
- COST / BOUNDARY：新增少量票级记录与使用后短报；机器不认证执行者自报、语义应用或用户收讫；专业选择/fallback 充分性与 Parent 转报仍为流程消费义务。

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
| P19 分解入口上下文丢失 | YES(原则)/DEFAULT(recipe) | 部分 | 部分 | 冲突 YES |
| P20 机器可证缺陷逃逸 | DEFAULT_ONLY | 部分 | YES | NO |
| P21 机械可判缺陷反复消耗评审预算 | DEFAULT_ONLY | 部分 | YES | NO |
| P22 真 finding 被当作修复授权 / 新 SHA 重置修复预算 / 饱和被当作评审门替代 | YES(原则)/DEFAULT(数值) | NO | YES | Arbiter YES |
| P23 Skill 盘点与本票执行/汇报脱节 | DEFAULT_ONLY | 部分（票级 CLI；无 live hook） | YES | NO |
