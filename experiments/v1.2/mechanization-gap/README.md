# experiments/v1.2/mechanization-gap — V1.2 Rule Migration / Mechanization Gap Analysis

> **非 canonical。本目录不实现任何机制、不修改任何 canonical 语义。**
> 本目录回答一个问题：**当前哪些提示词治理要求必须留在 HOT，哪些可以按需披露，
> 哪些应该由 tests / hooks / validators / CI / state machine / execution harness /
> runtime adapter 机械接管。**
>
> 核心原则（贯穿全部产物）：
> ```text
> LESS PROMPT · MORE FREEDOM · HARDER MECHANICAL ACCEPTANCE
> CLAIM != EVIDENCE        REGISTERED != EXECUTED      EXECUTED != LOAD_BEARING
> UNKNOWN != PASS          MEMORY != VERIFIED_STATE    MECHANIZATION_MUST_REPLACE
> RUNTIME_FACT != GOVERNANCE_INVARIANT
> ```

---

## 0. 本目录的读法（5 分钟版）

```text
先读 这一页（README）
  ↓ 想知道"现在有哪些规则"        → rule-inventory.md          （94 条 R-V12-*）
  ↓ 想知道"外部能借什么"          → longhorizon-mechanism-map.md（12 机制 + 7 条拒绝）
  ↓ 想知道"我们在防什么失败"      → failure-mechanism-map.md   （22 条，3 个模式）
  ↓ 想知道"每条规则去哪一层"      → rule-migration-matrix.md   ← **核心**
  ↓ 想知道"接下来怎么验证"        → experiment-protocols.md     （H2/H4/H5）
树位置 / 分支 / worktree 的事实   → ../TREE_LEDGER.md
```

**一句话结论**：缺口不在"缺规则"，而在"缺**可失败性**与**准入条件**"。
本目录给出的不是一个更长的规则表，而是一张**把规则搬离提示词的迁移图**。

---

## 1. WHY V1.2 EXISTS

因为**提示词已经装不下治理，而治理还在继续长**。这不是修辞 —— 它是可测的：

```text
AGENTS.md 实测 = 13,756 js_chars，而 guidance 通道上限 = 8,000 js_chars。
⇒ 只投递 7,840；**5,916 字符（43%）从不自动到达任何 agent**。
⇒ §6 REVIEW/REPAIR/CI、§7 STOP、§7.1 STATE_RESTORE/FLUSH、§8 治理变更、§9 报告、§10 BOOTSTRAP
   —— 这六节在功能上**根本不在 HOT 里**，尽管它们被标注为"HOT（D 层默认）"。
```

H1 实验把这件事变成了数字（`experiments/v1.2/h1-hot-context/`）。
V1.2 要做的不是"把 AGENTS.md 写短一点"，而是**改变治理的承载形态**：
把"要求 agent 记住"改成"让机器拦住"。

---

## 2. WHAT IS WRONG WITH PROMPT-HEAVY GOVERNANCE

三个可指认的机制，不是风格问题：

### 2.1 提示词约束**不可失败**
一条写在 HOT 里的规则，如果违反后没有任何东西会响，它与"没写"在机器意义上等价。
本轮归纳出 **PATTERN-A「空的东西看起来像满的」**，它在一次实验里出现**四次**：

```text
断言层  H1 P1：边界守卫只查工作树洁净度，而评审时工作树本就干净 ⇒ 断言恒真
门层    #45  ：select 清空后，注入真实缺陷，ruff 报 "All checks passed!"，治理校验仍 35/35
自检层  H1 D7：唯一能拦住仪器缺陷的 selftest 项被写成 `del g, exact`（空转）
数据层  H1 D7：仪器把 dropped_js_chars 算成 59（真值 5,916），却产出"可复算"的错数字
```

### 2.2 未验证的东西可以**进入可信面**
**PATTERN-B**：转录错误伪装成实验发现（H1 D8）；跨树数字伪装成矛盾（H1 P1 的 P3）；
记忆被写但无人执行（本仓 §7.1 明文"Hook 绝不代写语义决策"）。
`MEMORY != VERIFIED_STATE` 不是口号，它是**当前状态的真实描述**。

### 2.3 声明与目的地**脱节**
**PATTERN-C**：执行目标未绑定（H1 INVALID_001 作废一整对 run）；被引用的检查不存在
（H1 t03 两臂独立发现）；路由目标不存在（#46）；实验产物落在 /tmp 后永久丢失（H1 D9）。

**共同点**：三个模式都不是"规则写得不清楚"，而是"**没有东西会在违反时响**"。

---

## 3. WHAT SHOULD STAY IN HOT

**判据（三条同时成立才留）**：
```text
① 违反的后果**不可机械检出**，且后果严重（授权倒置 / 假证据 / 静默改写历史）
② 它是**语义判断**（"是不是在授权范围内"、"这个证据够不够"），不是流程步骤
③ 它是**导航**（"存在一个 X→Y 的表"），而不是表的内容本身
```

```text
留下的 = A 层 25 条（rule-migration-matrix §2）
  典型：AUTHORITY BEFORE ACTION · EVIDENCE BEFORE CONFIDENCE（UNKNOWN != PASS）
        SELF_REVIEW != INDEPENDENT_REVIEW · 门状态不得坍缩的值域纪律
        SATURATION != REVIEW_GATE_BYPASS · MINIMUM NECESSARY COMPLEXITY
  另有 B 层的**指针**：HOT 保留"有这么一张表"，表的内容下沉。
```

**同时必须承认一件事**：当前 31 条"声明为 HOT"的规则（AGENTS §6–§10）**从来没被投递过**。
它们的问题不是"该不该留"，而是"**如实重分类**"。这一步不需要任何实验、成本为零。

---

## 4. WHAT MOVES TO WARM

**B 层 19 条**：决策树 / 默认值 / 退化路径 / 边界说明。

```text
形态 = "当 X 时读 Y"。HOT 只需要知道**存在一个 X→Y 的表**。
典型：证据路由五分支（§0）· SEAM-FIRST 顺序（§4）· CODEGRAPH 三模式（§5）
      Stage 退化语义（§2）· 评审顺序与主问题（§6）· 部署验收记录（BOOTSTRAP §4）
```

> ⚠️ **硬前置（#46）**：**下沉前必须先证明路由目标存在且可载**，
> 否则"下沉"就等于"把内容移到一个找不到的地方"。
> 这不是推测 —— #46 就是在一个真实 base 上抓到的实例（`references/review-evidence.md`
> 在该 base 不存在，它由**该任务的候选本身**才引入）。
> 因此 H2 的核心问题恰好是 WARM reachability / route existence / route loadability。

---

## 5. WHAT BECOMES MECHANICAL

**C 层 26 条**。判据（四条同时成立才机械接管）：
```text
predicate 足够确定 · 失败语义明确 · 有正控 · 误通过风险已知
```
并且必须满足 **MECHANIZATION_MUST_REPLACE**：任何 HOT 移除都要能回答
`WHAT NOW ENFORCES IT / WHERE / HOW IT FAILS / HOW WE KNOW IT IS LOAD-BEARING`。

### 5.1 现在就能接管的（替代者已在仓内**并已验证**）

```text
R2 全部操作细节（4,196 字符 = RULES.md 的 61%）→ validate_public_release.py + governance 扫描
   **承重证据**：2026-10-09 一个 subagent 把含真实家目录路径的脚本写进 repo 根 →
   该门当场报 2 项 FAIL。门真的会响。
R7 平台卫生           → no-unrelated-platform-requirements
MEMORY 预算 3500 字节 → memory-pointer-within-budget + t09（24 tests）
PROJECT_CONTINUITY    → validate_project_state.py + schema + guard（H1 t03 臂已活体验证
                         "hook 不代写语义"）
注入通道事实（8,000/13,756/7,840/5,916）→ hot_inventory.py 已把它变成**可复算数字**
```

> **一个有说服力的分布事实**：`RULES.md` 里最长的一条（R2，61%）恰恰是**机械化最彻底**的一条。
> 这不是巧合 —— 它是"机械接管后提示词可大幅收缩"的**已有实例**，不是假设。

### 5.2 需要新机制（本轮只映射，不实现）

```text
执行目标绑定（F-002 / H1 INVALID_001）      → 前置断言三元组
评审 exact-SHA 绑定（F-003 / R5 的 L0 钩子） → 断言 review SHA == candidate SHA
门"是否仍承重"（#45）                        → 语义正控 / 突变探针
路由可达性（#46）                            → 目标存在性（须在声明 base 上跑）
产物持久化（F-015 / H1 D9）                  → 拒绝 /tmp 与 $TMPDIR
守卫与仪器可失败性（F-009/F-017/F-018）      → 正控 + 已知答案的合成输入自检
```

---

## 6. WHAT BECOMES HARNESS STATE

**D 层 18 条**。这是 H5 的标的，也是**外部机制与我们的缺口最对齐**的一层。

```text
候选状态模型（分析用，未实现）：
  UNVERIFIED → EVIDENCE_COLLECTED → VERIFIED → ACCEPTED → CHECKPOINTED
  失败路径：… → REJECTED → FAILURE_EVIDENCE → REPLAN

**禁止的转移**（本层最核心的三条断言）：
  executor self-report → VERIFIED        （M-12：完成是 harness 级判定，不是执行者自述）
  VERIFIED → ACCEPTED 而缺验收谓词
  REJECTED → 状态回退成"没发生过"        （M-04：失败证据必须保留）
```

```text
进这一层的规则：角色边界（029/030）· 一票一分支一 worktree（031）· 串行集成（034）
  · Stage barrier 与 owner 冲突（037/038）· **TICKET LANE 22 步生命周期（040，最大单块）**
  · 风险分级绑定（042，H4 标的）· STATE_RESTORE/FLUSH（057–060）
  · 治理变更双评审（062）· BOOTSTRAP B1–B6（081）
  · H1/H3 教训（086–088/090）
```

**为什么这一层重要**：`MEMORY != VERIFIED_STATE` 的解法不在 HOT 里 ——
它需要一条**准入规则**（"没有独立验证来源的事实不得进入 state"）。
这正是 LongHorizon 的 `Never promote an executor's unaudited claim` 在做的事。

---

## 7. WHAT IS RUNTIME-SPECIFIC

**E 层 3 条**，以及一条**分层纪律**：

```text
E 层规则：
  R-V12-066 两条自动注入通道（MEMORY 头部 / GUIDANCE_FILES 首个存在者 + 8000 截断）
  R-V12-067 机制事实是 **profile 事实**（WorkBuddy 5.5.3 @ 2026-09-04），非跨版本常数
  R-V12-083 工作区根 bootstrap 指针的交付形态（参考实现在别仓，本仓不 vendor）
```

```text
纪律 = Core 只应表达能力，不应表达工具命令。
  能力面（本轮登记的形状）：
    CAN_BIND_WORKDIR · CAN_READ_AUTHORITY · CAN_RUN_TESTS · CAN_INSPECT_ENVIRONMENT
    CAN_REQUEST_REVIEW · CAN_PERSIST_STATE · CAN_SPAWN_FRESH_EPISODE
  ⇒ 推论：能力缺失时的**行为**（如实报 ENV_BLOCKED，而非编造）属于 Core；
         具体"怎么跑测试"属于 Adapter。
```

**本轮的实测养料**：执行通道故障（exit 137/139）在 H1 的三轮里反复发生 ——
这是一个**真实的、可稳定触发的**能力缺失场景，`CAN_RUN_TESTS = NO` 时的行为
（如实上报 vs 编造）已经有真实观测样本。见 failure-mechanism-map F-014。

---

## 8. WHAT LONGHORIZON CONTRIBUTED

`AMAP-ML/LongHorizon-Harness`（MIT，arXiv:2608.01964）。全部为 **E1**。
12 个机制逐条判定（详见 `longhorizon-mechanism-map.md`）：

```text
ADOPT_CONCEPT = YES（8）：
  M-02 Verified State（**最强一条**）        M-04 Failure Evidence Capture
  M-06 Fresh Episode + 可重放 ledger        M-07 独立验证是独立步骤
  M-09 Role Separation as Implementation Boundaries
  M-10 AgentAdapter / Environment 窄协议     M-11 Event / Trajectory Persistence
  M-12 Completion Semantics（**完成 = harness 级判定**）

ADOPT_CONCEPT = EXPERIMENT（3）：
  M-01 Original Goal Persistence   M-03 Unverified/Verified 证据分级
  M-05 Bounded Next Step（每轮一个主导状态变化 + 硬预算）

Anthropic 独立佐证（2 篇，VERIFIED_FROM_SOURCE）：
  A-01 context **reset** vs compaction（并指出代价：handoff artifact 必须**足够**）
  A-02 工作与评判分离（"a strong lever"）
  A-03 一句与我们完全同型的失败描述：
       "a later agent instance would look around, see that progress had been made,
        and declare the job done."
```

**三条最高价值**（若只能取三条）：
`M-12 完成语义` · `M-02 状态转移需要独立验证准入` · `M-06 fresh episode 必须靠 ledger 而非口述`。

> 我们的现状与它们的差距**不在概念**（§7.1 已有 STATE_RESTORE/FLUSH 的字段定义），
> 而在**机制**：我们的 state 是"会话开始时恢复一次的**快照**"，
> 它的是"**每轮从 ledger 重建**"。H1 D9（产物落 /tmp 后永久丢失）正是快照 vs ledger 的代价。

---

## 9. WHAT WE REJECTED FROM LONGHORIZON

**拒绝的是实现形态，不是概念**。7 条，逐条给理由（`longhorizon-mechanism-map.md` §4）：

```text
REJECT-01 固定三角色进程拓扑
  理由 = **LongHorizon 自己说** "the roles are implementation boundaries inside the loop,
         **not three agents**"；而 Anthropic 说 "a three-agent architecture"。
         同一原则，两个来源给出**不同拓扑** ⇒ 拓扑不是不变式。
  抽象 = `ROLE_SEPARATION != PROCESS_TOPOLOGY`

REJECT-02 桌面/GUI computer-use 机制进核心协议（screenshot/upload/download）
  理由 = 我们治理的是**代码仓**。把某类任务的实现细节当普适能力。
REJECT-03 直接采用其 rounds.jsonl 格式与字段名
  理由 = 实现细节。采纳的是三条**语义**：append-only · 可重放 · 容忍半写尾部。
REJECT-04 MAX_ROUNDS = 1000 / DEFAULT 25 等具体数值
  理由 = 数值是它工作负载的函数。抄它 = 把别人的成本模型变成我们的规则
         （R8 + `RUNTIME_FACT != GOVERNANCE_INVARIANT`）。
REJECT-05 引入常驻 daemon / 数据库 / 服务
  理由 = 本轮明确禁止；且 append-only 文本已足以表达所需 ledger 语义。
REJECT-06 直接搬 clean/suspect/violation 三值证据分级
  理由 = 我们已有两套分级（Tier A/B 与 NOT_OBSERVABLE）；再叠一层是复杂度增加（R8）。
         先实验"二值 + 一个 UNTRUSTED 桶"。
REJECT-07 Anthropic 的 "three-agent" 表述本身
  理由 = 同 REJECT-01。取它关于**独立评估价值**的结论，不取它的拓扑建议。
```

**OpenAI 材料的处置**：⚠️ 只拿到 **SECONDARY_MENTION**（直连 openai.com 返回 challenge 页）。
因此它**不支撑任何判定**，仅作方向性佐证。`OPENAI_CONTRIBUTION = SECONDARY_ONLY`。

---

## 10. WHICH CLAIMS ARE LOCAL EVIDENCE

**这一节是本目录的可信度边界。** 只有列为下面的才是我们自己的证据：

```text
E3_LOCAL_REPRODUCIBLE（9 条 —— 有精确 SHA/命令，且有正控或可复算锚点）
  F-002 执行目标未绑定（H1 INVALID_001；修复后 6 个 worktree 全部 MATCH=YES）
  F-009 恒真守卫（H1 P1；活体证伪 + 哈希级还原）
  F-010 门谓词被掏空（#45；四步复现 + ruff.toml 哈希一致）
  F-011 路由目标悬空（#46；git ls-tree 双向）
  F-014 执行通道崩溃（exit 137/139；探针可重复）
  F-015 产物落易失目录（8 个 prunable worktree 现存）
  F-017 仪器口径错误（59 vs 5,916；已复算）
  F-018 selftest 空转（`del g, exact`；已恢复并断言）
  F-019 记录转录错误（t02 数字写进 t01；靠原始记录查出）

E2_LOCAL_SINGLE（6 条 —— 真实发生，有 SHA/记录，但未构造正控）
  F-008 被引用的检查不存在 · F-012 memory 写了不执行 · F-016 作废 run 计数
  · F-020 runtime 事实升格 · F-021 跨树数字 · F-022 回顾性污染

E1_LOCAL_ATTESTED（1 条）
  F-003 stale-SHA review（规则 R5 明写该 L0 钩子，但仓内无实现 —— 可在仓内直接查证，
        无 incident 记录）

HYPOTHESIS_NO_LOCAL（6 条）⚠️
  F-001 wrong repository · F-004 review-after-merge · F-005 findings ignored
  · F-006 reviewer 分歧被多数票掩盖 · F-007 自审冒充独立评审 · F-013 false closure
  **这 6 条不得据以立 gate**（R8：无真实失效不立 gate）
```

> **诚实附注**：本节数字**首次手写时是错的**（写成 4/6/3/9）。是**材料自检**把它抓出来的 ——
> `test_declared_statistics_match_the_entries` 逐级比对声明值与实际条目数，发现不符。
> 这正是本目录主张的那件事的一个现场演示：**声明必须能被机器对照，否则它会静默漂移**。
> 同一次自检还发现 `EVIDENCE_LEVEL` 字段的括号注释含空格、破坏机器可解析性 —— 已规范化为
> `EVIDENCE_LEVEL = <LEVEL>  # <note>`。

**量化基数**（全部可复算，命令见 rule-inventory 附录 B）：
```text
AGENTS.md 13,756 / RULES.md 6,843 / BOOTSTRAP_CONTRACT 5,083 / MEMORY 指针 2,028
HOT 合计 15,784；实际投递 9,868；**从不投递 5,916（43%）**
R2 一条占 RULES.md 的 61%（4,196）—— 而它是机械化最彻底的一条
```

---

## 11. WHICH CLAIMS ARE EXTERNAL E1

```text
LongHorizon-Harness 的 12 个机制  → E1，全部 VERIFIED_FROM_SOURCE（读了 README + 源码）
Anthropic 两篇                    → E1，VERIFIED_FROM_SOURCE（读了原文）
OpenAI harness-engineering        → **E1-SECONDARY** ⚠️ 未读到一手页；不支撑判定

纪律：
  · E1 提供**假设来源**，不提供**规则**。
  · 任何 E1 进入 canonical 必须先有本地复现（E3）→ 独立评审 → PR。
  · 本目录**没有**把任何 E1 写进 TARGET 层判定。
```

---

## 12. WHAT H2 / H4 / H5 WILL TEST

协议已冻结（只设计，未执行）：`experiment-protocols.md`。

```text
H2  Lazy Skill / Progressive Disclosure
    问题 = 多少治理/Skill 内容可以离开 HOT、只在相关时加载，而不降低正确性？
    核心测量 = ROUTE_EXISTENCE / ROUTE_LOADABLE / WARM_FILES_LOADED（**先定义口径**）
              / MISSED_GUIDANCE / FINAL_CORRECTNESS
    前置 = **#46 必须先落地**（否则测的是"路由坏了"而非"披露代价"）

H4  MICRO/LOW Governance Ablation
    问题 = 对 MICRO/LOW 任务能去掉多少**程序性**治理，而机械验收仍保住质量？
    关键设计 = **三臂**（FULL / MIN / MIN+注入缺陷）。
      只有第三臂**红**，才能证明"砍掉程序后机械门仍拦住真实缺陷"。
      若第三臂也绿 ⇒ 判 `MECHANICAL_ACCEPTANCE_HAS_NO_TEETH` —— 这比"保留程序"更重要。

H5  Verified State + Fresh Episode Recovery
    问题 = 完成/恢复/继续的语义能否从 prompt + memory 移入 **Verified-State 转移**？
    对照 = 长寿命 orchestrator context + 普通 memory
    变体 = Original Goal + Verified State + Failure Evidence + Remaining Work
           → fresh execution episode → 独立验证 → 只有通过验证的结果进入下一状态
    核心测量 = WRONG_STATE_CONTINUATION / STALE_SHA_ACCEPTANCE / FALSE_CLOSURE
              / RUNTIME_FAILURE_RECOVERY / REPEATED_WORK / HUMAN_INTERVENTION
    我们独有的优势 = 本机有一个**可稳定触发**的执行通道故障（exit 137/139，已 3 轮）
      ⇒ "崩溃后恢复"不需要模拟，真实故障会自己来。
```

**三个协议的共享前置（H1 的代价换来的）**：P1 执行目标机械绑定 · P2 载体投放断言 ·
P3 产物持久化 · P4 遥测匿名化（存在性）· P5 预注册评分规约 · P6 路由可达 ·
P7 门承重。**不满足任一项 ⇒ `PROTOCOL_NOT_STARTABLE`。**

---

## 13. WHAT MUST BE TRUE BEFORE V1.2 PROMOTION

```text
① 至少一个实验（H2/H4/H5）产出**预注册集合内**的结论，且 N_PER_ARM ≥2、每臂有机械可核终态
② 无未处置 P0/P1；P2 有 disposition
③ 独立评审（exact SHA）+ CI + merge + post-merge verify（**不接受"实验跑完"替代"仓库闭环"**）
④ **#45 与 #46 的机械映射已落地** —— 它们是几乎所有后续验证的前置
   （门不承重则"门绿"不携带信息；路由悬空则"下沉"等于"移到不可达处"）
⑤ 任何"移除 HOT 内容"的结论必须先满足 P6 + P7
⑥ 不得把 E1 当作 promotion 依据
```

**本轮的状态**：只到 ①–⑥ 的**前置条件已被写清**这一步。
`H2_EXECUTED = H4_EXECUTED = H5_EXECUTED = NO`；`CANONICAL_CHANGED = NO`；`H3_CHANGED = NO`。

---

## 14. 目录

| 文件 | 内容 | 规模 |
|---|---|---|
| `README.md` | 本文件：12 问导航 | — |
| `rule-inventory.md` | N6.1 — 94 条规则的逐条登记（含实测字符基数） | 94 规则 |
| `longhorizon-mechanism-map.md` | N6.2 — 12 机制 + 3 佐证 + 7 拒绝 | 12 机制 |
| `failure-mechanism-map.md` | N6.3 — 22 条失败 + 3 个跨条模式 | 22 失败 |
| `rule-migration-matrix.md` | N6.4 — 七层分类 + HOT 移除逐条替代论证 | **核心** |
| `experiment-protocols.md` | N6.5 — H2/H4/H5 协议 + 共享前置 P1–P7 | 3 协议 |
| `../TREE_LEDGER.md` | 逻辑树 + Git 执行树 | 19 节点 |

## 15. 本目录不做的事

```text
不修改 canonical（AGENTS.md / RULES.md / references/ 未动）
不实现任何门 / hook / 状态机
不执行任何实验（H2/H4/H5 只设计）
不改 H3 detector（H3_B1_STATUS 保持 COLLECTING）
不引入 daemon / 数据库 / 服务
不新增主研究节点（无 finding 使现有架构假设失效）
```
