# N6.1 — Current Rule Inventory（V1.2 mechanization gap analysis）

> **状态 = N6.1 ACTIVE / 本轮产物。非 canonical、不改任何 canonical 语义。**
> 目的：把 agent 当前**必须读、记住、遵守**的治理规则**按独立行为约束**逐条列出，
> 为 `rule-migration-matrix.md` 提供输入。
> **不按文件统计**：同一条约束在多处重述时只登记一次，并在 `RESTATED_IN` 指出重述点
> （重述点本身是机械化候选 —— 单一 owner 原则）。

## 0. 方法与口径

```text
CURRENT_RULE_COUNT        = 95
```

> 上行的值是**机械数出来的**（`R-V12-###` 的去重计数），不是手写声明 ——
> 材料自检 `test_declared_total_matches_the_id_space` 会逐次比对。手写数字曾在本轮出错
> （见 `failure-mechanism-map.md` 的诚实附注），故此处只登记可复算的值。

```text
拆分粒度 = 一个可独立违反的行为约束 = 一条 RULE_ID。
  反例（不算独立规则）：某个章节里对同一条约束的三次强调。
  正例：同一节里"必须先测基线"与"不得扩大 select 集合"是两条。

CURRENT_DELIVERY_LAYER 取值：
  HOT     = 首轮自动注入 / 默认必读（AGENTS.md 经通道 2；MEMORY 指针经通道 1）
  WARM    = 仅在条件触发时读的 references/**
  COLD    = scripts / schemas / tests / CI（机器执行，不要求 agent 记住）
  MEMORY  = ~/.workbuddy/MEMORY.md 头部指针
  MANUAL_REVIEW = 只能靠人或评审者判断，当前无机械 owner

AGENT_MUST_REMEMBER_IT：
  YES   = 不记住就会违反，且违反不会被机器拦住
  NO    = 有机械 owner 兜底（但"知道它存在"仍有导航价值）
  PARTIAL = 部分由机器兜底，残余仍需记住

DETERMINISTIC_PREDICATE_AVAILABLE：
  YES / PARTIAL / NO —— "能否写成一个确定性谓词"，不承诺已写。
CURRENT_MECHANICAL_ENFORCEMENT：
  NONE / PARTIAL / FULL + owner（具体文件或检查名）。

PROMPT_COST_CHARS = 该规则的承载成本。**逐条精确切分不可靠**，故记
  `shared:<section>` 并给出该 section 的实测总字符数（可复算；测量命令见 §附录）。
TOKEN_COST = 一律 NOT_OBSERVABLE（仓内 metrics.md 已定，禁止由字符数估算）。
```

### 0.1 实测基数（可复算）

```text
AGENTS.md                        = 13,756 js_chars / 151 行
  header（引用块）                 =    376
  §0 适用范围+铁律+DOCTRINE+ROUTING =  4,100
  §1 角色模型                      =    698
  §2 EXECUTION STAGE              =    466
  §3 TICKET LANE                  =  1,270
  §4 SEAM-FIRST                   =    699
  §5 CODEGRAPH GROUNDING          =  1,051
  §6 REVIEW / REPAIR / CI         =  1,068
  §7 AUTO-ADVANCE 与 STOP          =    339
  §7.1 STATE_RESTORE / STATE_FLUSH =  1,755
  §8 治理变更                      =    257
  §9 报告                          =    391
  §10 BOOTSTRAP                   =  1,286

RULES.md                         =  6,843 js_chars / 75 行
  R1 = 407   R2 = 4,196   R3 = 561   R4 = 295
  R5 = 343   R6 = 282     R7 = 299   R8 = 179

deployment/BOOTSTRAP_CONTRACT.md =  5,083 js_chars / 117 行
deployment/MEMORY_POINTER_CANDIDATE.md = 2,028 js_chars / 35 行

HOT 合计（control 口径）= MEMORY 指针 2,028 + AGENTS.md 13,756 = 15,784 js_chars
  但 guidance 通道实际只投递前 8,000 → 可见 7,840，丢弃 5,916。
```

**一条值得注意的分布事实**：`R2` 一条占 `RULES.md` 的 **61%**（4,196 / 6,843），
而它同时是**机械化最彻底**的一条（双层扫描 + 无自我豁免 + 不依赖后缀 + 有界读取 +
INDEX/工作区双面 + symlink 不解引用 + fail-closed 超限）。
→ 这是「机械接管后可以从提示词里大幅收缩」的**已有实例**，不是假设。

---

## A. AGENTS.md §0 — 铁律 / doctrine / 证据路由（R-V12-001 … R-V12-027）

### R-V12-001 — SKILL_IS_NOT_AUTHORITY
```text
SOURCE = AGENTS.md §0
REQ = Skill 是执行方法，不是权威；读 Skill 不改变权威链。
PREVENTS = 用一个工具的说明覆盖 A/B/C 层权威。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = NO（语义判断） | ENFORCEMENT = NONE
EVIDENCE = NONE | COST = shared:AGENTS§0
```

### R-V12-002 — Skill 接入流程（选 → 读全文 → 应用/如实 fallback → 汇报 + 票级证据）
```text
REQ = 首次执行与阶段转换时按阶段/风险/技术栈选 Skill；读完整原文；应用或**如实** fallback；
      使用后必须汇报并留票级证据。安装清单不证明使用；工具不授予扩权。
PREVENTS = 装了但没用（REGISTERED != EXECUTED）；假装用了。
LAYER = HOT | MUST_REMEMBER = PARTIAL
PREDICATE = PARTIAL（"是否读了/是否汇报"可机械；"是否应用得当"不可）
ENFORCEMENT = PARTIAL → schemas/skill-execution.schema.json + scripts/skill_execution.py
              + templates/skill-report.json + scripts/tests/test_skill_execution.py
EVIDENCE = test_skill_execution 覆盖 SAFE_RETRIEVAL_UNAVAILABLE fallback 等真实分支
COST = shared:AGENTS§0
```

### R-V12-003 … 007 — 证据路由五分支
```text
R-V12-003 MECHANICAL QUESTION → STATIC TOOL / LSP / AST / COMPILER / LINTER / CODEGRAPH / TEST
R-V12-004 BEHAVIORAL CONTRACT → TEST
R-V12-005 CROSS-MODULE STRUCTURE → CODEGRAPH（模式 A/B/C）
R-V12-006 SEMANTIC / CONTRACT / ARCHITECTURE → MODEL REASONING
R-V12-007 HIGH-VALUE UNCERTAINTY → STRONG / EXTERNAL REVIEW（ESCALATION 清单）
SOURCE = AGENTS.md §0 ENGINEERING EVIDENCE ROUTING
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = NO（分类判断） | ENFORCEMENT = NONE
PREVENTS = 用错证据形态（拿静态输出裁决语义 / 拿模型猜机器可证事实）
COST = shared:AGENTS§0
```

### R-V12-008 — DO_NOT_SPEND_REASONING_ON_MACHINE_PROVABLE_FACTS
```text
REQ = 机器可证的事实不进模型评审（L0 先清场）。
PREVENTS = 昂贵的语义推理被用来回答机器即可回答的问题。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§0
```

### R-V12-009 — DO_NOT_REPLACE_SEMANTIC_REASONING_WITH_STATIC_TOOL_OUTPUT
```text
REQ = 静态工具输出不裁决语义/合同/所有权。
PREVENTS = 绿 lint 被当作合同正确。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§0
```

### R-V12-010 — USE_REPOSITORY_NATIVE_STATIC_TOOLING_FIRST
```text
REQ = 优先用仓库原生静态工具。
LAYER = HOT | MUST_REMEMBER = PARTIAL
PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL（references/static-analysis… §15）
COST = shared:AGENTS§0
```

### R-V12-011 — STATIC_TOOLING_DISCOVERY（先发现后规定）
```text
REQ = 从 manifest / 构建 / 工具配置 / CI / 脚本**发现**工具，**不**凭文件扩展名推断。
PREVENTS = 假设一个不存在的工具链，或漏掉仓已配置的门。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = YES（可枚举上述来源并与仓内事实比对）
ENFORCEMENT = PARTIAL → validate_governance: `ci-executes-static-gate` 只查"CI 是否调用"，
              **不查"发现的集合是否正确"**（→ 机械候选）
EVIDENCE = #45（门可以存在却不再承重）
COST = shared:AGENTS§0
```

### R-V12-012 — CONFIGURED_STATIC_TOOLING_MUST_RUN
```text
REQ = 仓已配置且覆盖本次变更面的静态工具**必须执行**；不得因"测试是绿的"静默跳过。
PREVENTS = 配置了但没跑。
LAYER = HOT | MUST_REMEMBER = PARTIAL
PREDICATE = YES（配置存在 → 执行 → 有收据）
ENFORCEMENT = PARTIAL → CI 步骤存在；但**"覆盖本次变更面"未被判定**（→ 机械候选）
EVIDENCE = #45
COST = shared:AGENTS§0
```

### R-V12-013 — 门状态不得坍缩（值域）
```text
REQ = NOT_CONFIGURED != PASS、ENV_BLOCKED != PASS、KNOWN_BASELINE_FAILURE != PASS、
      TOOL_EXISTS != TOOL_EXECUTED、CONFIG_FILE_EXISTS != GATE_EXECUTED、
      LINTER_CONFIGURED != LINTER_PASSED、FORMAT_PASS != LINT_PASS。
PREVENTS = 空门禁 / 假绿。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（对每对可写判定；但"是否有人在报告里坍缩"需要读报告）
ENFORCEMENT = PARTIAL → 治理校验器多处断言具体值域；报告措辞层面无门
COST = shared:AGENTS§0
```

### R-V12-014 — STATIC_GATE_RECEIPT 进票级
```text
REQ = 静态门结论进票级收据（字段 owner = references/ticket-lane.md §9/§9.3）。
LAYER = HOT（指针）| MUST_REMEMBER = YES
PREDICATE = YES（schema 可校验） | ENFORCEMENT = PARTIAL（schema 存在；票级强制靠流程）
COST = shared:AGENTS§0
```

### R-V12-015 — DEFECT_TO_GATE_PROMOTION（按缺陷类；LOWEST != WEAKEST；一次出现 ≠ 自动晋升）
```text
REQ = 发现真实缺陷后按**缺陷类**问能否机械可靠检出；能且晋升有价值才下沉到最便宜可靠层；
      处置取值集合 = 框架 §21.3（不得重述/缩写）；一次出现 ≠ 自动晋升；
      行为缺陷的回归测试不得被 lint 规则替换。
PREVENTS = 规则指数扩散；把行为知识替换成弱检查。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL → test_p1_t18_defect_promotion_fast_full.py（103 tests）
COST = shared:AGENTS§0
```

### R-V12-016 — FINDING != AUTOMATIC_TRUTH != AUTOMATIC_GATE
```text
REQ = reviewer finding 的"可机械检测性"元数据是**建议性证据**，不授予改治理/装工具/扩 scope/
      自动开票的权威。
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§0
```

### R-V12-017 — FAST_GATE / FULL_GATE 双向不豁免
```text
REQ = FAST != FULL、CI_FAST PASS != CI_FULL PASS、FULL PASS 不抹掉 FAST 失败；
      FAST/FULL 是执行类别，不要求两个 CI job。
LAYER = HOT | MUST_REMEMBER = PARTIAL
PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL（CI 结构可查；"是否抹掉"需读报告）
COST = shared:AGENTS§0
```

### R-V12-018 — LOCAL_FAST_GATE != CI_FAST_GATE
```text
REQ = 目标是"确定性低层缺陷不该在 CI 第一次被发现"；本地不可行时**如实上报**而非编造。
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = PARTIAL | ENFORCEMENT = NONE
COST = shared:AGENTS§0
```

### R-V12-019 … 028 — ENGINEERING DOCTRINE 十条
```text
R-V12-019 AUTHORITY BEFORE ACTION —— 先确认权威链与票授权；授权不明即停。
R-V12-020 UNDERSTAND BEFORE EDIT —— 编辑前建立仓库关系模型；不知谁生产/消费/拥有状态不写码。
R-V12-021 SEAM BEFORE TICKET —— 自然缝先于票据；DAG 是执行排序不是架构权威。
R-V12-022 CONTRACT BEFORE CODE —— 合同字段块先于实现；缺语义 STOP 不猜。
R-V12-023 COUNTEREXAMPLE BEFORE IMPLEMENTATION —— 先设计"看起来合理仍违反合同"的反例；RED 须由反例触发。
R-V12-024 EVIDENCE BEFORE CONFIDENCE —— 完成/PASS 由可复现证据支撑；UNKNOWN != PASS。
R-V12-025 SELF_REVIEW != INDEPENDENT_REVIEW（gate 存在时）。
R-V12-026 RISK-SCALED RIGOR —— 严格度随风险缩放。
R-V12-027 MINIMUM NECESSARY COMPLEXITY —— 每个机制必须回答"防哪次真实失效"。
R-V12-028 AUTO-ADVANCE UNTIL REAL AUTHORITY UNCERTAINTY。
SOURCE = AGENTS.md §0 ENGINEERING DOCTRINE
LAYER = HOT | MUST_REMEMBER = YES（全部）
PREDICATE = NO（原则层，不可直接判定） | ENFORCEMENT = NONE（作为原则）
备注：本组是**原则声明**，其可判定后代分散在 §1–§10 与 RULES；盘点它们是为了识别
      "同一约束被原则层与操作层双重承载"这一重述模式。
COST = shared:AGENTS§0
```

---

## B. AGENTS.md §1 — 角色模型（R-V12-029 … R-V12-035）

### R-V12-029 — PARENT ORCHESTRATOR 默认不当生产编码工人
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = NO | ENFORCEMENT = NONE
PREVENTS = 编排者自己下场改代码，从而同时充当执行者与验收者。
COST = shared:AGENTS§1
```

### R-V12-030 — WORKER 六条禁止
```text
REQ = 不得自批 / 自合并 / 扩 scope / 开下游票 / 改冻结 Spec-DAG / 把 self-review 当独立评审。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（自合并可机械看 merge 作者；自批部分可查 review 身份）
ENFORCEMENT = PARTIAL → validate_public_release --commit-metadata（身份门）；
              R4 的完成门靠评审记录，无机械 owner
EVIDENCE = H1 外的历史：reviewer 与 executor 同一身份无法机械发现（→ 机械候选）
COST = shared:AGENTS§1
```

### R-V12-031 — WORKER 一票 / 一分支 / 一隔离 worktree
```text
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = YES（分支/worktree 与票的对应可断言）
ENFORCEMENT = PARTIAL（无强制的"一票一 worktree"检查）
EVIDENCE = H1 INVALID_001/002（worker 跑在错误目录/错误 HEAD）
COST = shared:AGENTS§1
```

### R-V12-032 — REVIEWER 不得无限修复权 / 修改后不得声称原 PASS
```text
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL | ENFORCEMENT = NONE
COST = shared:AGENTS§1
```

### R-V12-033 — INTEGRATOR：quorum 未对同一 exact HEAD PASS 前不得动作
```text
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = YES（review 记录的 SHA == 被合入 SHA）
ENFORCEMENT = PARTIAL → R5 的 `REVIEWED_HEAD == candidate tip` 是 L0 机械核验，
              但仓内无脚本实现该断言（→ 机械候选，与 #45 同类）
EVIDENCE = 历史 stale-SHA review（见 failure-mechanism-map F-003）
COST = shared:AGENTS§1
```

### R-V12-034 — INTEGRATOR 串行 master 集成
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = PARTIAL（集成顺序可观测） | ENFORCEMENT = NONE
COST = shared:AGENTS§1
```

### R-V12-035 — 隔离 worker 直接实现；handoff 文档仅四情形
```text
REQ = 隔离实现 worker 直接实现生产代码（默认允许且优先）；handoff 仅在跨工具传递 /
      执行中断 / 外部 worker / 审计要求时创建。
PREVENTS = 为仪式而产出的 handoff 文档（反官僚）。
LAYER = HOT | MUST_REMEMBER = PARTIAL | PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§1
```

---

## C. AGENTS.md §2–§4（R-V12-036 … R-V12-046）

### R-V12-036 — DAG-ready ≠ 立即开工；禁止 START_ALL
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§2
```

### R-V12-037 — Stage 内并行 + Stage 尾 barrier（Stage Review Packet → 触发时外部评审 → 修复/批准 → 自动集成 → 重算 frontier）
```text
LAYER = HOT | MUST_REMEMBER = PARTIAL | PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL
COST = shared:AGENTS§2
```

### R-V12-038 — owner 冲突三选一（合并为一票 / 显式串行链 / 拆 owner），不得默认并行
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = NO | ENFORCEMENT = NONE
EVIDENCE = H1：两臂共享同一物理仓时必须串行（single-writer 是它的近亲）
COST = shared:AGENTS§2
```

### R-V12-039 — 无 DAG 退化语义
```text
LAYER = HOT | MUST_REMEMBER = PARTIAL | PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§2
```

### R-V12-040 — TICKET LANE 生命周期顺序（22 步）
```text
REQ = AUTHORIZED TICKET → exact base SHA → isolated branch/worktree → 读权威 → Skill 路由 →
      自然缝识别 → CodeGraph grounding → Relevant Surface Manifest → Contract Extraction →
      counterexample 设计 → TDD RED → /implement → applicable static/mechanical gates →
      GREEN → 回归 → fresh independent review(L1) →（有价值才）repair → PR → real CI →
      （触发时）post-CI/adversarial → merge gate → 串行集成 → remote verify → tracker
PREVENTS = 跳步（例如先实现后想合同）。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（每步的产物可查；"顺序"本身无机械 enforcement）
ENFORCEMENT = NONE → **本组是本轮最大的单块机械候选**（见 N6.3/N6.4）
EVIDENCE = H1：两次 harness 作废都发生在"exact base SHA / isolated worktree"这两步
COST = shared:AGENTS§3
```

### R-V12-041 — 静态门位置固定（IMPLEMENT 后、DYNAMIC GREEN 前）
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL（CI 步骤顺序）
COST = shared:AGENTS§3
```

### R-V12-042 — 风险分级（LOW/MEDIUM/HIGH）× 评审与 grounding 要求
```text
REQ = LOW：非生产/机械票可 L0-only（仓政策允许时）；生产代码必须 L1。
      MEDIUM：必须 L1 + 全 baseline。HIGH：必须 L1 + adversarial + 强反例 5–10。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（票声明的 risk 与"实际是否 L1"可核）
ENFORCEMENT = NONE（无脚本把 risk 级与评审要求绑定）
EVIDENCE = H1 t03/t04 声明 HIGH，但"是否真的做了 adversarial"只由报告自述（→ 机械候选）
COST = shared:AGENTS§3
```

### R-V12-043 / 044 — ESCALATION 清单与其边界
```text
R-V12-043 任一命中即升级 L2：架构不确定性 / 并发与 canonical 权威语义 / 安全与凭据边界 /
          评审分歧未决 / Approved Spec 或 governance 变更 / 里程碑终审 / 高爆炸半径运行时语义。
R-V12-044 LOW 票不得触发 ESCALATION，除非命中清单本身。
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§3
```

### R-V12-045 — SEAM-FIRST 合法顺序与禁止顺序
```text
REQ = 合法：权威/产品行为 → 既有架构 → producer/consumer → 状态/身份/校验归属 →
      持久化/失败/安全边界 → 自然缝 → 内聚行为切片 → 票据 → DAG。
      禁止：DAG → 发明票据形状模块 → 假缝 → 逼架构就范。
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§4
```

### R-V12-046 — 分解的四条纪律
```text
REQ = ① /to-tickets = 实现分解 + 一致性 lint，不是架构生成器；
      ② 分解入口必须读 execution-stage §6 的 gate 序列（两条路径均不得跳过 POST）；
      ③ 合法的架构性拆分/合并不得因"影响票据边界"被拒绝；依赖边暴露真实架构合同时升格为架构决策；
      ④ prefactor 提议服从既有架构权威；新模块名映射不上既有概念 = 假缝，回炉。
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL
      → scripts/tests/test_p1_t02_execution_stage_pre_ticket_record.py（11 tests）
COST = shared:AGENTS§4
```

---

## D. AGENTS.md §5–§10（R-V12-047 … R-V12-062）

### R-V12-047 — CODEGRAPH 三模式语义
```text
REQ = A（默认）BASE+DIFF，报 CANDIDATE_GRAPH_COVERAGE = BASE_ONLY + DELTA_BY_DIFF，
      **不声称** candidate-exact 覆盖；B（仅 HIGH/明确需要候选态图）lane 一次 init 后 sync；
      C 不可用 → 手工 Relevant Surface Manifest + 定向阅读，报 CODEGRAPH = UNAVAILABLE，不伪造图证据。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL → adapters/zcode/hooks/codegraph_lifecycle.py (1323 行)
EVIDENCE = 生命周期 hook 已存在；"是否伪造图证据"无门
COST = shared:AGENTS§5
```

### R-V12-048 — FULL_INIT_FORBIDDEN / lane init 至多一次
```text
LAYER = HOT | MUST_REMEMBER = PARTIAL
PREDICATE = YES | ENFORCEMENT = FULL-ish → codegraph_lifecycle verify 输出 LC-INV 系列
      真实集合 = LC-INV1..LC-INV8（第二轮复评者核实 hook 实现）；
      不写上限的理由是 **canonical 自身不一致**（AGENTS §7.1 说 INV5，contract 说 INV8）——
      详见附录 E 的 U-03。
COST = shared:AGENTS§5
```

### R-V12-049 — 票据包记录所用模式与 CANDIDATE_GRAPH_COVERAGE
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = YES（字段存在性） | ENFORCEMENT = PARTIAL（schema）
COST = shared:AGENTS§5
```

### R-V12-050 — L0/L1/L2 分级定义
```text
REQ = L0 机器核验（SHA、diff 语义范围、测试、回归、ancestry、secret/路径扫描）；
      L1 独立评审（fresh context、独立 grounding、≥2 个非复制新反例）；L2 外部/最强评审。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（L0 项大多可机械；"≥2 个非复制新反例"部分可核）
ENFORCEMENT = PARTIAL → validate_public_release / validate_governance 覆盖 L0 的多项
COST = shared:AGENTS§6
```

### R-V12-051 — 评审顺序（权威 → 票 → 图 → 合同 → 反例 → diff → 测试 → CI）+ 主问题
```text
REQ = 主问题 =「这个 exact SHA 是否在真实仓库中实现了合同？」
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§6
```

### R-V12-052 — 修复收敛语义（SEVERITY != REPAIR_AUTHORITY / REPAIR_VALUE gate / 预算 2 / 高价值 blocker 永不豁免）
```text
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（预算计数可机械；价值判断不可）
ENFORCEMENT = PARTIAL → scripts/tests/test_p1_orchestrator_closure_doctrine.py (16)
              + test_review_evidence_contract.py (53)
COST = shared:AGENTS§6
```

### R-V12-053 — SATURATION != REVIEW_GATE_BYPASS
```text
REQ = 饱和/仲裁不得替代评审门；AUTO_REPAIR_AUTHORITY 与 INTEGRATION_AUTHORITY 独立。
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§6
```

### R-V12-054 — CI 状态不可坍缩 + LOCAL_TESTS != REAL_PR_CI
```text
REQ = NOT_TRIGGERED / UNKNOWN / KNOWN_BASELINE_FAILURE 永不 = PASS；
      real CI 为默认，仓政策可定义等价证据形态（显式 OVERRIDE），R3 诚实性底线不可豁免。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL → test_p1_t03_git_ci_integration_closure_evidence.py (17)
EVIDENCE = H1：本机 32+23 项沙箱性预存在失败 vs CI 绿 —— 两种结果都真实，需要"按树归因"才能读对
COST = shared:AGENTS§6
```

### R-V12-055 — 授权路径自动推进，不问"是否继续"
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = NO | ENFORCEMENT = NONE
COST = shared:AGENTS§7
```

### R-V12-056 — STOP 七枚举；milestone 后不自动进入已排除的 NEXT_STAGE
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = PARTIAL（状态名可枚举） | ENFORCEMENT = NONE
COST = shared:AGENTS§7
```

### R-V12-057 — PROJECT_STATE_MUST_OUTLIVE_THE_AGENT / CONVERSATION_MEMORY_IS_CACHE
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL
      → references/project-state-persistence.md + adapters/zcode/hooks/state_flush_guard.py (198)
COST = shared:AGENTS§7.1
```

### R-V12-058 — STATE_RESTORE 固定序列 + recovery receipt 字段
```text
REQ = 禁止以"请人讲历史"开局；按固定序列从 remote + 仓文档 + Issues/PRs 重构；
      输出 receipt（PROJECT / REMOTE_DEFAULT_SHA / TARGET / SPEC / ADR / SPIKES /
      ACTIVE_TICKETS / BLOCKERS / DECISIONS_REQUIRED / CURRENT_LEGAL_FRONTIER / READY_TO_CONTINUE）。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = YES（receipt 字段可校验；序列可脚本化） | ENFORCEMENT = PARTIAL（schema 存在）
COST = shared:AGENTS§7.1
```

### R-V12-059 — STATE_FLUSH 时机 + 自问 + receipt
```text
REQ = 在 结束有意义会话 / 切换 runtime / 交接 / STOP / milestone / 完票 / 集成 / context 耗尽前，
      自问"下一个 fresh agent 需要什么而它只存在于我的 context？"并持久化到正确 canonical 位置；
      输出 STATE_FLUSH = PASS/PARTIAL + UNPERSISTED_IMPORTANT_CONTEXT。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL → state_flush_guard.py（只提示，不代写）
EVIDENCE = 本仓自身：H1 的评审证据一度只存在于对话里（"零持久化"），靠事后补 PR 评论才落地
COST = shared:AGENTS§7.1
```

### R-V12-060 — PROJECT_CONTINUITY_CONTRACT_V1（唯一状态索引 / lazy adoption / 只在 meaningful transitions 写）
```text
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = YES（.agent/project-state.json 的存在性 + schema） | ENFORCEMENT = FULL-ish
      → scripts/validate_project_state.py (252 行) + schemas/project-state.schema.json
      + adapters/zcode/hooks/project_state_guard.py (163)
COST = shared:AGENTS§7.1
```

### R-V12-061 — MEDIUM/HIGH 生产首写前需 GROUNDING_RECEIPT；Hook 只保证不忘记写、绝不代写语义决策
```text
LAYER = HOT | MUST_REMEMBER = PARTIAL
PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL → grounding_guard.py (262) 只读收据、缺则返回 BLOCK
EVIDENCE = adapters/zcode/tests/test_project_continuity.py（69 tests）含"block 不得合成收据"
COST = shared:AGENTS§7.1
```

### R-V12-062 — 治理变更默认双独立评审（合同向 + 一致性向）同一 exact HEAD；禁止实现票顺手改治理
```text
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（"改了什么文件"可机械；"两份评审是否真的独立"不可）
ENFORCEMENT = PARTIAL → validate_governance 的 `no-authority-inversion-markers` 等只查文本形态
EVIDENCE = 本仓每次治理变更都走双评审，但**靠流程纪律而非机械门**
COST = shared:AGENTS§8
```

### R-V12-063 — 报告 novelty-first 七字段；NONE 合法；禁止编造
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = PARTIAL（字段存在性） | ENFORCEMENT = PARTIAL
COST = shared:AGENTS§9
```

### R-V12-064 — PR_CI_COMPRESSION_ALLOWED = PASS_ONLY
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = YES | ENFORCEMENT = NONE（→ 机械候选）
COST = shared:AGENTS§9
```

### R-V12-065 — Skill 使用后汇报与 Parent 转报义务
```text
LAYER = HOT | MUST_REMEMBER = YES | PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL
      → references/skills-and-model-routing.md §1.2–§1.4
COST = shared:AGENTS§9
```

### R-V12-066 — 两条自动注入通道 + 四性质区分
```text
REQ = 通道 1 = ~/.workbuddy/MEMORY.md 头部；通道 2 = 工作区根 GUIDANCE_FILES 首个存在者并被截断。
      四性质：FIRST_TURN_AUTO_INJECTION_COVERAGE / FULL_GOVERNANCE_REACHABILITY /
      FULL_GOVERNANCE_AUTOMATIC_DELIVERY / MECHANICAL_ENFORCEMENT。
      **不得**把"自动注入了一部分"表述为"治理已交付"。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = YES（截断点、预算、文件清单均可复算 —— hot_inventory.py 已实现）
ENFORCEMENT = FULL → scripts/tests/test_p1_t09_bootstrap_byte_budget.py (24)
              + experiments/v1.2/h1-hot-context/hot_inventory.py
COST = shared:AGENTS§10
```

### R-V12-067 — 机制事实是 profile 事实，非跨版本常数；升级后重新取证
```text
LAYER = HOT | MUST_REMEMBER = PARTIAL | PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL
COST = shared:AGENTS§10
```

> **R-V12-068 已移出本组** —— 评审 P2 指出它的文本实际出自 `BOOTSTRAP_CONTRACT.md` §2.4
> （「不得为迁就注入上限而删减 AGENTS.md 的成熟治理语义」），而非 AGENTS §10。
> 它的块现列在 §F（BOOTSTRAP），与 appendix D 的来源声明一致。
> **教训**：来源被记录在两个地方时，只改一处就会造成文件内部自相矛盾 ——
> 这正是本目录第 15 节复盘的那种「声明未写明适用范围」。

---

## E. RULES.md — B 层普适不变量（R-V12-069 … R-V12-082）

### R-V12-069 — R1 权威分层与显式 OVERRIDE
```text
REQ = A > B > C > D；对 D 层默认的覆盖必须显式记录（`OVERRIDE = <clause> overridden by
      <authority> <clause> (source)`）；静默覆盖 = 违规；仓**加严**永远合法且无需记录；
      体系内不可解析冲突 → STOP: CONTRACT_CONFLICT。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（"是否存在未记录的覆盖"很难判；矛盾权威标记可查）
ENFORCEMENT = PARTIAL → validate_governance: `no-authority-inversion-markers`
COST = shared:RULES.R1
```

### R-V12-070 — R2 第一层：凭据与 local OS identity 绝对禁止
```text
REQ = Cookie/Secret/Token/API key/登录凭证/SSH 私钥、以及**本机登录名/系统用户身份**
      绝不进入 repo、log、聊天、产物、长期记忆、报告。凭据探测输出只允许布尔/错误类型。
      无任何可见性/路径豁免。repository/account identity（如 FlapPearLabs 署名）不属本层。
      **机器身份不得硬编码进校验器**：检测模式必须通用。
LAYER = COLD（主要）+ HOT（认知）| MUST_REMEMBER = PARTIAL
PREDICATE = YES（模式匹配） | ENFORCEMENT = **FULL** → validate_public_release.py (1414 行)
      + validate_governance.py `no-credentials-anywhere`
EVIDENCE = 2026-10-09：一个 subagent 把评审脚本写进 repo 根（含真实家目录路径），
      该门当场报 2 项 FAIL —— **门确实有牙齿**
COST = shared:RULES.R2
```

### R-V12-071 — R2 第二层：machine-specific 事实分区
```text
REQ = 一般治理产物中禁止宿主路径/端口/二进制位置/运行时版本；
      PUBLIC 仓**无豁免**（只允许占位符形态）；PRIVATE 仓豁免需**两条件合取**
      （路径在 deployment/ 下 AND 文件头带 MACHINE-SPECIFIC ALLOWED）。
LAYER = COLD + HOT | MUST_REMEMBER = PARTIAL
PREDICATE = YES | ENFORCEMENT = FULL → `machine-facts-only-in-designated-files`
COST = shared:RULES.R2
```

### R-V12-072 — R2 历史原文归档 local-only；raw 归档须过第一层扫描 + redaction
```text
LAYER = COLD + HOT | MUST_REMEMBER = PARTIAL | PREDICATE = YES | ENFORCEMENT = PARTIAL
COST = shared:RULES.R2
```

### R-V12-073 — R2 工具/MCP 配置必须占位符模板形态
```text
LAYER = COLD + HOT | MUST_REMEMBER = PARTIAL | PREDICATE = YES | ENFORCEMENT = PARTIAL
      → validate_governance: `mcp-canonical-set-v1`
COST = shared:RULES.R2
```

### R-V12-074 — R2 扫描的五条实现纪律
```text
REQ = ① 无自我豁免（校验器自身同等受检，测试用运行时合成 fixture）；
      ② 不依赖文件后缀（文本判定基于内容；有界读取而非流式）；
      ③ CURRENT_TREE = 公开候选面 = tracked + untracked 未忽略；
      ④ 未扫描 != 干净（超限 fail-closed 为 UNSCANNED_OVERSIZE_PUBLIC_FILE）；
      ⑤ 扫描 Git 将要发布的内容（INDEX 面 + 工作区面；symlink 不解引用）。
LAYER = COLD | MUST_REMEMBER = NO | PREDICATE = YES | ENFORCEMENT = FULL
      → validate_public_release `--selftest` 51/51 + `--history` 限定措辞
COST = shared:RULES.R2
```

### R-V12-075 — R3 证据真实性
```text
REQ = 任何"完成/成功/PASS/verified"须有可复现证据；UNKNOWN != PASS；sampled 不得升级为 global；
      报告不得编造新颖性（NEW_* = NONE 合法）；非 PASS 状态的自分类**只能作为提案**，
      接受需独立证据 + 独立侧接受（REVIEWER_ACCEPTED_CLASSIFICATION = YES）。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL | ENFORCEMENT = PARTIAL → test_p1_t05_evidence_disposition.py (26)
      + test_p1_t06_producer_trust_boundary.py (39) + test_p1_t07/test_p1_t08
EVIDENCE = H1：两臂都自报 VALID_COMPLETION = NO 且理由经得起复核 —— 这是 R3 生效的正面实例
COST = shared:RULES.R3
```

### R-V12-076 — R4 独立评审完整性
```text
REQ = 当独立评审 gate 存在时：executor 自审（含 /code-review 类工具）不满足该 gate；
      不得自批 / 自合并 / 派生受自己影响的 reviewer 冒充独立评审。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（评审者身份与 executor 身份可机械比对 —— 但仓内**没有**这个断言）
ENFORCEMENT = PARTIAL → 依赖评审记录自述
EVIDENCE = H1：三次 fresh review 都靠"新开一个 context"实现，靠纪律不靠门（→ 机械候选）
COST = shared:RULES.R4
```

### R-V12-077 — R5 已评审/已发布历史不被静默改写
```text
REQ = 不得 force-push / amend / rebase 已 reviewed 候选分支；修复 = append-only 新 commit →
      新 SHA → 适用 gate 按新 SHA 重审。合并方法（ff-only / squash / merge commit）= 仓政策。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = YES（V: REVIEWED_HEAD == candidate tip，L0 机械核验）
ENFORCEMENT = PARTIAL（**该 L0 断言在仓内无实现** → 机械候选）
COST = shared:RULES.R5
```

### R-V12-078 — R6 Scope 诚实
```text
REQ = 在票授权语义范围内工作；发现合同空白 → STOP: CONTRACT_GAP，不得静默发明缺失语义；
      架构冲突 → STOP: CONTRACT_CONFLICT。未预载文件（测试/fixture/支撑缝）**不是**自动违规；
      仅当票明确冻结文件清单时才适用子集校验。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（文件清单可机械；"是否在语义范围内"不可）
ENFORCEMENT = PARTIAL → test_h1_material 的 committed-change-set 检查（H1 本轮新增）
EVIDENCE = H1 P1：守卫曾只看工作树洁净度 → 已提交越界可通；修复后按 `merge-base..HEAD` 判
COST = shared:RULES.R6
```

### R-V12-079 — R7 平台注入卫生
```text
REQ = 治理/共享产物不得注入与其无关的平台特定 shell 要求；宿主环境事实属部署档案。
LAYER = HOT + COLD | MUST_REMEMBER = PARTIAL | PREDICATE = YES
ENFORCEMENT = FULL → validate_governance: `no-unrelated-platform-requirements`
COST = shared:RULES.R7
```

### R-V12-080 — R8 最小复杂性护栏
```text
REQ = 新增强制 gate 前必须回答：防哪次真实失效？机器能否更便宜地做？每个风险级都需要吗？
      能否降级为 reference/默认？无强论证不得入 RULES；治理自身受最小复杂性约束。
LAYER = HOT | MUST_REMEMBER = YES
PREDICATE = NO | ENFORCEMENT = PARTIAL → `orchestrator-closure-doctrine-present`（M1–M9 文本）
COST = shared:RULES.R8
```

---

## F. deployment/BOOTSTRAP_CONTRACT.md（R-V12-081 … R-V12-085）

### R-V12-081 — BOOTSTRAP_CHECKLIST B1–B6
```text
REQ = B1 读 MEMORY 注入中的治理指针（不存在 → 按治理仓 URL 直接读取并报告缺失）；
      B2 读治理仓 AGENTS.md + RULES.md + 相关 references；
      B3 发现仓内权威 → 读存在者；仓根 bootstrap 指针**不是权威**，必须继续读到其指向的全文；
      B4 应用 AUTHORITY_MAP_V2 冲突算法，记录所有对 D 层的显式 OVERRIDE；
      B5 核验新鲜 remote truth（有 remote 时 fetch 后核对 default branch 的 exact SHA）；
      B6 输出引导回执（GOVERNANCE_LOADED / REPO_AUTHORITY / OVERRIDES）。
      不可静默跳过；仓本地权威只可**加严**，不得削弱 B1–B5 的读取义务。
LAYER = MEMORY + HOT | MUST_REMEMBER = YES
PREDICATE = PARTIAL（B5 可完全机械；B1–B4 的"是否真读了"不可）
ENFORCEMENT = PARTIAL（B5 = `git fetch` + SHA 比对；其余靠回执自述）
EVIDENCE = H1 INVALID_002：载体未投放 ⇒ 臂静默回落到默认载体 ⇒ 自变量被悄悄取消
COST = shared:BOOTSTRAP_CONTRACT
```

### R-V12-082 — MEMORY 指针预算 3500 UTF-8 字节（非字符）
```text
REQ = NAME = WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES；VALUE = 3500；UNIT = UTF-8 字节；
      3500（主动预算 BUDGET）与 4028（被动历史截断点 TRUNCATION）性质不同，不得互为定义；
      非默认 profile 用自有预算须先有已核验观测并显式记录 OVERRIDE。
LAYER = COLD | MUST_REMEMBER = NO | PREDICATE = YES
ENFORCEMENT = FULL → validate_governance: `memory-pointer-within-budget`
      + test_p1_t09_bootstrap_byte_budget.py (24)
COST = shared:BOOTSTRAP_CONTRACT
```

### R-V12-083 — 工作区根 bootstrap 指针的交付契约（CODEBUDDY.md）
```text
REQ = 显式声明"不覆盖 RULES.md / Approved Specs / AGENTS.md / 当前票授权"；
      只做一件事：命令 agent 先完整读取被指向的权威，再动手；
      不得授予权限 / 改变自动模式 / 定义例外 / 豁免 gate；不得膨胀为第二份 AGENTS.md。
LAYER = HOT（载体本身）| MUST_REMEMBER = YES
PREDICATE = YES（尺寸 + 必备指针 + 禁止语句可检） | ENFORCEMENT = PARTIAL
      （参考实现在 zhihu-grabber-toolkit；本仓不 vendor）
EVIDENCE = H1 #46：路由目标可以不存在 —— **交付契约不检查目的地**
COST = shared:BOOTSTRAP_CONTRACT
```

### R-V12-084 — 四性质字段与 AUTO_INJECTION != FULL_GOVERNANCE_DELIVERY
```text
见 R-V12-066（同一条约束的两个 owner —— 本身是重述点，见 §附录 RESTATEMENTS）。
```

### R-V12-085 — 部署验收记录只登记状态字段，本体在 audit/
```text
LAYER = HOT（指针）| MUST_REMEMBER = PARTIAL | PREDICATE = PARTIAL | ENFORCEMENT = NONE
COST = shared:BOOTSTRAP_CONTRACT
```

### R-V12-068 — 不得为迁就注入上限而删减成熟治理语义（**评审 P2 后移入本组**）
```text
SOURCE = deployment/BOOTSTRAP_CONTRACT.md §2.4（原文：「不得为迁就注入上限而删减 AGENTS.md 的成熟治理语义」）
REQ = 工作区根 bootstrap 指针不得膨胀为第二份 AGENTS.md；不得为迁就 8000 上限删减成熟语义。
LAYER = HOT_READ（与 R-V12-083 同源；二者是同一约束的两个声明点 → TGT = F / 去重）
MUST_REMEMBER = YES | PREDICATE = YES（尺寸上限） | ENFORCEMENT = PARTIAL
      （参考实现见 zhihu-grabber-toolkit 的校验器；本仓不 vendor）
EVIDENCE = H1：AGENTS.md 13,756 → 只投递 7,840；**该约束正是 H1 的起因**
COST = shared:BOOTSTRAP_CONTRACT
```

> **移动记录（评审 P2）**：本块原先列在 §D（AGENTS §5–§10）并记 `COST = shared:AGENTS§10`，
> 而 appendix D 已把它的来源记为 `BOOTSTRAP_CONTRACT` —— 同一文件里两处说法不一致。
> 现按**实际文本出处**统一到本组。这也是本目录主张的「一个事实只能有一个 owner」的现场应用。

---

## G. 实验线派生的候选规则（本轮新增，R-V12-086 … R-V12-094）

> 另见 §E 的 **R-V12-095**（评审 P1 补录，源自 RULES.md R3 的独立义务）。

> 来源 = H1/H3 的真实失效。**这些目前只在实验记录里，不在 canonical**；
> 登记于此是为了让迁移矩阵能对其处置（多数应进 HARNESS_STATE_MACHINE 或 MECHANICAL_GATE）。

```text
R-V12-086 执行目标机械绑定：worktree 绝对路径 + EXPECTED_BASE_SHA 必须是 worker 的机械前置断言。
  来源 = H1 INVALID_001（worker 停在 HEAD 而非 replay base，任务成 no-op）
  PREDICATE = YES | ENFORCEMENT = NONE（仅 prompt 散文）| 目标层候选 = HARNESS_STATE_MACHINE

R-V12-087 载体投放断言：bootstrap 载体的"投放"必须与"断言"同为 harness 机械步骤。
  来源 = H1 INVALID_002（未投放 ⇒ 臂静默回落 ⇒ 自变量未被建立）
  PREDICATE = YES | ENFORCEMENT = NONE | 目标层候选 = HARNESS_STATE_MACHINE

R-V12-088 遥测匿名化必须覆盖字段的**存在性**，不只内容与文件名。
  来源 = H1 判别器 1（H1_RECEIPT 有无 4/4 完美切分臂）+ 判别器 2（载体行数）
  PREDICATE = PARTIAL（可检查"两臂模板是否同构"）| ENFORCEMENT = NONE
  目标层候选 = HARNESS_STATE_MACHINE / 实验协议

R-V12-089 run 产物必须落在持久化位置（非 /tmp）。
  来源 = H1 D9（/tmp/h1-runs 被清理，8 个 worktree 全 prunable，diff 不可事后重放）
  PREDICATE = YES（产物路径不在易失目录）| ENFORCEMENT = NONE
  目标层候选 = MECHANICAL_GATE（低成本）

R-V12-090 预注册评分规约：评分维度与"高价值"边界必须在跑之前冻结。
  来源 = H1 R5 复现前置条件
  PREDICATE = PARTIAL | ENFORCEMENT = NONE | 目标层候选 = 实验协议（非 runtime 规则）

R-V12-091 断言必须检验**正确的对象**与**正确的时点**。
  来源 = H1 P1（边界守卫只查工作树洁净度，而评审时工作树本就干净 ⇒ 恒真）
  PREDICATE = PARTIAL（"断言是否可失败"可探针；"是否检验了正确对象"需人判）
  ENFORCEMENT = NONE | 目标层候选 = MECHANICAL_GATE（正控/mutation probe）

R-V12-092 记录转录保真 + 原始记录必须保留。
  来源 = H1 D8（v2 重写把 t02 的行数写进 t01 记录，且被误当成实验发现）
  PREDICATE = PARTIAL | ENFORCEMENT = NONE | 目标层候选 = MECHANICAL_GATE（哈希/回归）

R-V12-093 计量仪器缺陷：口径变更必须留下可复算锚点；selftest 不得空转。
  来源 = H1 D7（dropped_js_chars 59 vs 5,916；且唯一能拦住它的 T2 被写成 `del`）
  PREDICATE = PARTIAL | ENFORCEMENT = NONE | 目标层候选 = MECHANICAL_GATE（正控）

R-V12-094 环境故障一律记为环境，不记为任一臂/任一候选的质量缺陷；跨树数字不得互换引用。
  来源 = H1（553 vs 602 tests 被读成矛盾）+ H3
  PREDICATE = NO | ENFORCEMENT = NONE | 目标层候选 = HOT（认知类，难机械化）
```

---

## 附录 A — 重述点（同一约束的多 owner，自身即机械化候选）

> ⚠️ **评审 P2 修正**：本节初稿声明「6 个重述点」，而实际 ≥9。漏掉的三个与已列出的三个
> 属**同一家族**（doctrine ↔ 操作层）：
> `R-V12-027` ↔ `R-V12-080`（MINIMUM NECESSARY COMPLEXITY ↔ R8）、
> `R-V12-026` ↔ `R-V12-042`（RISK-SCALED RIGOR ↔ 风险表）、
> `R-V12-021` ↔ `R-V12-045`（SEAM BEFORE TICKET ↔ SEAM-FIRST 顺序）。
> **计数错误的原因与 §G 的统计错误同源**：重述点没有被机器枚举过。

```text
R-V12-024 EVIDENCE BEFORE CONFIDENCE  ←→ R3  ←→ AGENTS §6 的 CI 不可坍缩
R-V12-025 SELF_REVIEW != INDEPENDENT_REVIEW ←→ R4 ←→ AGENTS §1 WORKER 禁止 ←→ §6 L1
R-V12-050 L0/L1/L2  ←→ §3 风险表 ←→ RULES R4（gate 存在性由 D+C 决定）
R-V12-066 四性质  ←→ R-V12-084（AGENTS §10 与 BOOTSTRAP_CONTRACT §1 双声明）
R-V12-013 门状态不可坍缩  ←→ R-V12-054 CI 不可坍缩 ←→ H1 P1（断言可失败性）
R-V12-036/037/038/039 Stage 语义  ←→ references/execution-stage.md §6
R-V12-027 MINIMUM NECESSARY COMPLEXITY ←→ R-V12-080（RULES R8）
R-V12-026 RISK-SCALED RIGOR ←→ R-V12-042（AGENTS §3 风险表）
R-V12-021 SEAM BEFORE TICKET ←→ R-V12-045（SEAM-FIRST 顺序）

**DECLARED_RESTATEMENT_COUNT = 9**（评审修正后）
```

重述不是错误（读者可能只看到其中一处），但它意味着**同一语义有多个维护点**：
任何修订都要同步多处，而"是否同步"当前无机械检查。
→ 候选：`references-declare-canonical-owner` 的加强版（owner 唯一性 + 重述点显式标注）。

## 附录 B — 测量命令（可复算）

```bash
python3 - <<'PY'
import pathlib, re
for name in ("AGENTS.md","RULES.md","deployment/BOOTSTRAP_CONTRACT.md","deployment/MEMORY_POINTER_CANDIDATE.md"):
    t = pathlib.Path(name).read_text(encoding="utf-8")
    print(name, len(t), "js_chars,", len(t.splitlines()), "lines")
PY
# 逐节：按 ^##  切分
```

## 附录 C — 本文件不做的事

```text
不做：决定每条规则去哪个目标层（= N6.4）
不做：判断哪条能立即从 HOT 移除（= N6.4 的 CAN_REMOVE_FROM_HOT）
不做：修改任何 canonical 文件
不做：实现任何机械门
```

## 附录 D — RULE → SOURCE_SECTION（机器可读；CUR 由它推导，不由手工标注）

```text
映射规则（材料自检强制）：
  AGENTS§0-§4 → HOT_AUTO          AGENTS§5 → HOT_AUTO_PARTIAL
  AGENTS§6-§10 → HOT_NOT_DELIVERED
  RULES.R1-R5 → HOT_AUTO_MEMORY（其摘要确实在交付的 MEMORY 指针内）
  RULES.R6-R8 → HOT_READ          BOOTSTRAP_CONTRACT → HOT_READ
  EXPERIMENTS → EXPERIMENT_ONLY

R-V12-001 = AGENTS§0
R-V12-002 = AGENTS§0
R-V12-003 = AGENTS§0
R-V12-004 = AGENTS§0
R-V12-005 = AGENTS§0
R-V12-006 = AGENTS§0
R-V12-007 = AGENTS§0
R-V12-008 = AGENTS§0
R-V12-009 = AGENTS§0
R-V12-010 = AGENTS§0
R-V12-011 = AGENTS§0
R-V12-012 = AGENTS§0
R-V12-013 = AGENTS§0
R-V12-014 = AGENTS§0
R-V12-015 = AGENTS§0
R-V12-016 = AGENTS§0
R-V12-017 = AGENTS§0
R-V12-018 = AGENTS§0
R-V12-019 = AGENTS§0
R-V12-020 = AGENTS§0
R-V12-021 = AGENTS§0
R-V12-022 = AGENTS§0
R-V12-023 = AGENTS§0
R-V12-024 = AGENTS§0
R-V12-025 = AGENTS§0
R-V12-026 = AGENTS§0
R-V12-027 = AGENTS§0
R-V12-028 = AGENTS§0
R-V12-029 = AGENTS§1
R-V12-030 = AGENTS§1
R-V12-031 = AGENTS§1
R-V12-032 = AGENTS§1
R-V12-033 = AGENTS§1
R-V12-034 = AGENTS§1
R-V12-035 = AGENTS§1
R-V12-036 = AGENTS§2
R-V12-037 = AGENTS§2
R-V12-038 = AGENTS§2
R-V12-039 = AGENTS§2
R-V12-040 = AGENTS§3
R-V12-041 = AGENTS§3
R-V12-042 = AGENTS§3
R-V12-043 = AGENTS§3
R-V12-044 = AGENTS§3
R-V12-045 = AGENTS§4
R-V12-046 = AGENTS§4
R-V12-047 = AGENTS§5
R-V12-048 = AGENTS§5
R-V12-049 = AGENTS§5
R-V12-050 = AGENTS§6
R-V12-051 = AGENTS§6
R-V12-052 = AGENTS§6
R-V12-053 = AGENTS§6
R-V12-054 = AGENTS§6
R-V12-055 = AGENTS§7
R-V12-056 = AGENTS§7
R-V12-057 = AGENTS§7.1
R-V12-058 = AGENTS§7.1
R-V12-059 = AGENTS§7.1
R-V12-060 = AGENTS§7.1
R-V12-061 = AGENTS§7.1
R-V12-062 = AGENTS§8
R-V12-063 = AGENTS§9
R-V12-064 = AGENTS§9
R-V12-065 = AGENTS§9
R-V12-066 = AGENTS§10
R-V12-067 = AGENTS§10
R-V12-068 = BOOTSTRAP_CONTRACT
R-V12-069 = RULES.R1
R-V12-070 = RULES.R2
R-V12-071 = RULES.R2
R-V12-072 = RULES.R2
R-V12-073 = RULES.R2
R-V12-074 = RULES.R2
R-V12-075 = RULES.R3
R-V12-076 = RULES.R4
R-V12-077 = RULES.R5
R-V12-078 = RULES.R6
R-V12-079 = RULES.R7
R-V12-080 = RULES.R8
R-V12-081 = BOOTSTRAP_CONTRACT
R-V12-082 = BOOTSTRAP_CONTRACT
R-V12-083 = BOOTSTRAP_CONTRACT
R-V12-084 = BOOTSTRAP_CONTRACT
R-V12-085 = BOOTSTRAP_CONTRACT
R-V12-086 = EXPERIMENTS
R-V12-087 = EXPERIMENTS
R-V12-088 = EXPERIMENTS
R-V12-089 = EXPERIMENTS
R-V12-090 = EXPERIMENTS
R-V12-091 = EXPERIMENTS
R-V12-092 = EXPERIMENTS
R-V12-093 = EXPERIMENTS
R-V12-094 = EXPERIMENTS
R-V12-095 = RULES.R3
```

### R-V12-095 — TICKET_DECOMPOSITION_REQUIRES_CONVERGED_PROJECT_CONTRACTS（**评审 P1 补录**）
```text
SOURCE = RULES.md R3（原文：`TICKET_DECOMPOSITION_REQUIRES_CONVERGED_PROJECT_CONTRACTS`）
REQ = 声称分解完成，必须有**项目权威下的上游语义收敛与票集组合证据**；
      `DEPENDENCY_DAG_VALID` / `STRUCTURAL_VALIDATION` **不证明** `SEMANTIC_COMPATIBILITY`。
      全局定义证明义务，项目定义实际语义；不得借此静默覆盖已批准合同（R1）。
      执行步骤唯一见 `references/execution-stage.md` §6。
PREVENTS = 用一个结构上合法的 DAG 冒充"语义已收敛"——即"图对=对"。
LAYER = HOT_AUTO_MEMORY（其摘要不在 MEMORY 指针的 4 条里；R3 的整体在指针摘要第 2 条）
      —— 严格说本条的**细则**只在 RULES.md 全文里，故实际依赖 HOT_READ。
      ⚠️ 本条的这一层归属本身是一个 MINOR_UNRESOLVED：R3 的摘要极短（13 字），
        不足以承载本条的判定义务。见 §附录 E。
MUST_REMEMBER = YES
PREDICATE = PARTIAL（"是否存在项目权威下的收敛证据"部分可核；"证据是否真的支持语义收敛"不可）
ENFORCEMENT = PARTIAL → `references/execution-stage.md` §6 有 gate 序列与测试
COST = shared:RULES.R3
```

> **为什么这条是补录**：first-pass 盘点把它与 R3 的"证据真实性"合并看待了，导致一条
> 有独立判定义务的约束没有独立 ID。外部评审在攻击"inventory 是否有遗漏"时发现。
> 这正是本目录主张的那件事：**清单必须有机器可核的完备性来源，否则遗漏不可见**。

## 附录 E — MINOR_UNRESOLVED（已知的、未解决的小问题）

```text
U-01 R-V12-095 的层归属：RULES.R3 在 MEMORY 指针里只有 13 字摘要，
     而本条要求「项目权威下的语义收敛证据」这一实质判定义务。
     ⇒ 把整条 R3 归为 HOT_AUTO_MEMORY 是**乐观的**。
     未解决：应否把 R3 降为 HOT_READ？这会连带影响 R3 家族的全部规则。
     处置：登记未解决，不擅自决定（它同时牵动矩阵的 CUR 推导规则）。

U-02 **附录 D 仍是手写输入**（复评 P3，最锋利的一条）：
     CUR 现在"由来源推导"，但**来源表本身**是 95 行手写赋值，且**没有任何外部 owner**。
     这正是本目录要消灭的那个形状 —— 「无外部 owner 的手写声明」—— **上移了一层**。
     已做的部分补救：`test_appendix_d_agrees_with_each_rule_block_source_line`
     对**能逐条归因的**规则块做交叉核对（块级 `COST = shared:<section>` ↔ 附录 D）。
     未解决的部分：分组标题下的规则（如 R-V12-003…008 共用一个标题）无法逐条归因；
     且一次**计数不变的重贴标签**仍能骗过全部测试（复评者已构造并实证）。
     下一步候选（未实现）：把来源标记写进正文结构本身（每组一个 `[SOURCE_SECTION=…]` 标记行），
     使来源从**规则在文件中的位置**推导，而不是从一张表推导。

U-03 **LC-INV 编号范围** —— **已由第二轮复评者解出**（本轮不再 UNVERIFIED）：
     真实集合 = `LC-INV1 … LC-INV8`（`adapters/zcode/hooks/codegraph_lifecycle.py`）。
     ⇒ 因此三处表述统一为「LC-INV 系列」是对的（不写死上限），但**理由变了**：
       不是"无法确定"，而是**canonical 自身互相矛盾**：
       ```text
       AGENTS.md §7.1                    → LC-INV1..INV5   （**少数**）
       references/project-continuity-contract.md → LC-INV1..INV8
       adapters/zcode/README.md          → LC-INV1..INV8
       adapters/zcode/hooks/codegraph_lifecycle.py → 实现 INV1..INV8
       ```
     ⇒ **这是一条真实的 canonical 内部不一致**（AGENTS §7.1 少算了 3 条不变量）。
       依 PART 21 的立项判据评估：可复现 ✓ / current-main 相关 ✓ / 不重复 ✓，
       但**工程影响低**（是文档少算，不是机制缺陷），且修正它属于治理变更（需走 §8 双评审）。
       **处置 = 登记为 FINDING，不新开 issue，不修改 canonical**（本目录不改 canonical）。
       候选接手方：未来的 governance-change 票；判据与方法已写在此处，含行号。

     另：这也说明"标 UNVERIFIED"在**可查而没查**时会掩盖真问题 ——
     本轮把它记为"环境降级导致未复核"是诚实的，但复评者一次 grep 就解出了答案。
     教训：`UNVERIFIED` 应当是**最后手段**，不是省事的默认。
```
