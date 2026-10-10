# N6.5 — H2 / H4 / H5 Protocol Freeze（V1.2 mechanization gap analysis）

> **状态 = N6.5 本轮产物。非 canonical。**
> **本轮只设计，不执行。** `H2_EXECUTED = H4_EXECUTED = H5_EXECUTED = NO`。
> 输入 = N6.1（95 条规则）/ N6.3（22 条失败，3 个模式）/ N6.4（迁移矩阵）。
>
> **三个协议共享的前置条件（H1 的代价换来的，不得再犯）**列在 §0，写在每个协议之前。

---

## 0. 共享前置条件（三个协议都适用；不满足则**不得开始**）

```text
P1  执行目标机械绑定（R-V12-086 / F-002）
    worker 启动前断言 WORKTREE_ABSOLUTE_PATH + EXPECTED_BASE_SHA == ACTUAL_HEAD_SHA。
    不匹配 ⇒ 拒绝执行。H1 因此作废过一整对 run。

P2  载体投放断言（R-V12-087 / F-002 变体）
    bootstrap 载体的"投放"必须是 harness 的机械步骤。
    未投放会让臂静默回落到默认载体 ⇒ **自变量被悄悄取消**（H1 INVALID_002）。

P3  产物持久化（R-V12-089 / F-015）
    run 产物不得写入 /tmp 或 $TMPDIR。H1 的 8 个 replay worktree 因此全部不可复验。

P4  遥测匿名化覆盖字段**存在性**（R-V12-088 / F-019 的近亲）
    两臂报告模板必须同构（同一生成路径）；任何"只在一臂出现"的结构化字段都是判别器。
    H1 的 `H1_RECEIPT` 有无实现过 4/4 完美切分 ⇒ `BLIND_EVALUATION = VOID`。

P5  预注册评分规约（R-V12-090）
    评分维度、"高价值"判定边界、停止条件必须在**开跑前**冻结并写入本仓。
    不允许看到结果再定义"什么算高价值"。

P6  可达性前置（#46 的机械映射）
    若协议依赖"agent 能按路由找到 WARM 内容"，则**先**证明路由目标存在且可载。
    否则实验测的是"路由坏了"而不是"披露有没有代价"。

P7  门完整性前置（#45 的机械映射）
    若协议用"某机械门通过"作为质量判据，**先**证明该门是承重的
    （有正控：注入已知坏输入时它会失败）。否则"门绿"不携带信息。
```

**不满足任一项 ⇒ `PROTOCOL_NOT_STARTABLE`。** 这是 H1 三条教训的直接制度化。

---

## 1. H2 — Lazy Skill / Progressive Disclosure

```text
NODE = N2
CORE_QUESTION = 多少治理/Skill 内容可以离开 HOT、只在相关时才加载，而**不降低正确性**？
MIGRATION_MATRIX_LINK = 检验 B 组 19 条 + R-V12-047/049 的可下沉性
```

### 1.1 假设与可falsify形态

```text
H2-H1 = 把 §3/§4/§5 的细节下沉到 WARM 并只留指针，任务正确性不变。
FALSIFIED_IF = 变体臂出现 ≥1 条对照臂捕获的高价值 finding 未被捕获，
               且该 finding 的内容**恰好**在被下沉的文本里。
               （这条判定边界必须在开跑前写死 —— 否则事后可以无限解释"这不算"）
H2-H2 = 路由可达性是下沉可行性的**唯一硬前提**。
FALSIFIED_IF = 出现"路由存在但内容不足"（即：找到了文件但里面没有所需语义）
               → 说明"目标存在"不足以保证"可载"，需要 anchor 级检查。
```

### 1.2 设计

```text
TASKS = 复用 H1 的 4 个真实历史任务（t01–t04，SHA 对已实证）
        + 至少 2 个**新**的真实任务，其中至少 1 个历史形状是"评审/修复"类
          （H1 里 t04 正是这一类，且它恰好暴露了 #46）
  理由：H1 的 4 个任务全部来自同一仓；H2 若要测"Skill 检索"，需要至少一个
        历史上真的用到了 Skill 的任务。

ARMS =
  CONTROL_H2 = 当前 HOT（AGENTS.md 全文可达，即 P6 修复后的状态）+ 无路由
  VARIANT_H2 = 精简 HOT（§3/§4/§5 细节下沉，HOT 留指针）+ 强制路由
  两臂**其余全部相同**：同 base、同任务文本、同工具、同验收契约、同模型档位。

N_PER_ARM = ≥2（H1 的 n=1 是它无法归因的直接原因；少于 2 不得开跑）
```

### 1.3 测量（每项都必须可机械取得或明确标 NOT_OBSERVABLE）

```text
M1  ROUTE_EXISTENCE_RATE      = 被声明的路由中，目标在声明 base 上存在的比例（机械）
M2  ROUTE_LOADABLE_RATE       = agent 实际读取成功的路由比例（机械：读文件调用日志）
M3  WARM_FILES_LOADED         = **必须定义口径**（H1 的 8 个数互不对账 = L5）
                                 定义 = 被**完整读取**（非 grep 命中）的 references 文件数
M4  MISSED_GUIDANCE           = 变体臂漏掉的、对照臂捕获的高价值 finding（人工判定，预注册边界）
M5  FINAL_CORRECTNESS          = 每臂按 MIGRATION 前的验收契约判定（机械 + 评审）
M6  SKILL_RETRIEVAL_HIT       = 任务本应触发的 Skill 是否被加载（机械：对照 skill-execution schema）
M7  UNNECESSARY_LOAD          = 加载了与任务无关的 WARM 内容（人工判定）
TOKEN_USAGE / WALL_CLOCK      = NOT_OBSERVABLE（除非 runner 提供可靠采集；H1 的教训）

BLINDNESS = 必须（PART 4 的 P4）。若无法做到同构模板 + 存在性归一化，
           则**接受非盲**并显式标 `BLIND_EVALUATION = NOT_ATTEMPTED`，
           **不得**再次产出 `VOID` 还声称是盲评。
```

### 1.4 停止条件与结论词汇

```text
STOP_WHEN = N_PER_ARM 达成 且 两臂都有机械可核的终态（测试/验收/评审证据）
RESULT_VOCABULARY = { DISCLOSURE_SAFE, DISCLOSURE_HAS_COST, INSUFFICIENT_EVIDENCE }
  禁止 PROMOTE（promotion 属 V1.2 synthesis）
LEAN_PROMOTING 类结论的最低要求（借 H1 的 PART 17 形状）：
  · HOT 体量实质下降（机械可算）
  · **无** additional high-value miss
  · **不增加** invalid completion
  · 有"减少了不必要治理动作"的证据
```

### 1.5 与 #46 的关系

```text
H2 是 #46 的**第一个被测对象**：#46 的机械映射（路由可达性检查）应在 H2 开跑前落地，
否则 H2 的变体臂会在"部分路由不可达"的环境中运行 —— 那测到的是环境缺陷，不是披露代价。
```

---

## 2. H4 — MICRO/LOW Governance Ablation

```text
NODE = N4
CORE_QUESTION = 对 MICRO/LOW 风险任务，能去掉多少**程序性**治理，而机械验收仍保住质量？
MIGRATION_MATRIX_LINK = 检验 A 组里"程序性"的部分（R-V12-036..046）+ R-V12-042 的风险绑定
目标形状 = **more agent freedom / less prompt process / same-or-higher mechanical acceptance**
```

### 2.1 关键设计难点（必须先承认）

```text
难点 = "去掉程序后质量不变"是**不可证**的（只能falsify）。
  因此 H4 不能问"能不能去掉"，只能问"去掉之后，机械验收面是否仍然拦住真实缺陷"。
⇒ H4 的判据必须是**机械验收的判别力**，而不是"没有出事"。
⇒ 这要求一个**注入缺陷的正控臂**（见 2.3 的 ARM_INJECT）。
```

### 2.2 任务选择（必须有真实 MICRO/LOW 历史）

```text
任务来源 = 真实 MICRO/LOW 历史 ticket（文档、fixture、确定性胶水、机械配置、微型生产修复）
  H1 的 t01 就是这一类（LOW，且它暴露了 false-pass 家族）
TASKS = ≥4 个，其中 ≥1 个历史上出过 false-green（H1 t01 的直接复用）
```

### 2.3 三臂设计（而不是两臂）

```text
ARM_PROCESS_FULL   = 当前程序性治理完整保留
ARM_PROCESS_MIN    = 砍掉程序性治理，只保留：（a）A 层不变量；（b）机械门；（c）验收契约
ARM_INJECT         = 同 ARM_PROCESS_MIN，但**故意注入一个真实缺陷类**
                     （从 failure-mechanism-map 里选一个 E3 级的，例如
                      "产物写到易失目录"或"门谓词被掏空"）
```

```text
第三臂是**本协议最关键的设计**：
  ARM_PROCESS_MIN 与 ARM_PROCESS_FULL 同时绿，可能只是"这个问题本来就简单"（无判别力）；
  只有 ARM_INJECT **红**，才能证明"砍掉程序后机械门仍然拦住真实缺陷"。
  若 ARM_INJECT 也绿 ⇒ 判 `MECHANICAL_ACCEPTANCE_HAS_NO_TEETH`，
  这是比"保留程序"更重要的结论。
```

### 2.4 测量

```text
M1  PROCEDURAL_STEPS_EXECUTED = 每臂实际执行的程序性步骤数（可机械记：命令/文件证据）
M2  MECHANICAL_ACCEPTANCE      = 机械门结果（每臂逐门）
M3  INJECTED_DEFECT_CAUGHT     = ARM_INJECT 是否被拦住（**核心判据**）
M4  FINAL_CORRECTNESS          = 独立评审判定（预注册边界）
M5  FALSE_PASS_OBSERVED        = 出现"报告 PASS 但证据不成立"的次数
M6  HUMAN_INTERRUPTS           = 结构性停机次数（客观记录）
```

### 2.5 结论词汇

```text
RESULT_VOCABULARY = {
  PROCESS_ABLATION_SAFE,            # 砍掉后机械验收仍拦住注入缺陷，且无额外高价值 miss
  PROCESS_ABLATION_UNSAFE,          # 出现 additional high-value miss 或注入缺陷漏过
  MECHANICAL_ACCEPTANCE_HAS_NO_TEETH,  # ARM_INJECT 也绿 ⇒ 问题不在"程序多少"
  INSUFFICIENT_EVIDENCE
}
```

---

## 3. H5 — Verified State + Fresh Episode Recovery

```text
NODE = N5  ← **本轮最高价值的协议**（M-12/M-02/M-06 三条外部机制的本地验证）
CORE_QUESTION = 完成 / 恢复 / 继续的语义，能否从 prompt + memory 移入 **Verified-State 转移**？
```

### 3.1 对照与变体（PART 18 给定形状）

```text
CONTROL_H5 = 长寿命 orchestrator context + 普通 memory
   = 一个持续增长的会话 + ~/.workbuddy/MEMORY.md 作为记忆。
   （这正是本仓当前的实际形态。）

VARIANT_H5 = Original Goal
             + Verified State
             + Failure Evidence
             + Remaining Work
             → **fresh execution episode**
             → **independent verification**
             → **只有通过验证的结果才进入下一个状态**

关键差异（必须在两臂同时成立才叫对照）：
  · 两臂都做**同样多**的 fresh episode（差异只在"用什么恢复"，不在"是否 fresh"）
  · 两臂的 episode 数、任务、工具、验收契约相同
  · 变体臂的"状态"必须是**可重放的 ledger**（append-only），不是快照
    —— 否则无法区分"Verified State 有效"与"快照恰好够用"
```

### 3.2 状态模型（最小候选；分析用，不实现）

```text
UNVERIFIED
   ↓ 收集证据
EVIDENCE_COLLECTED
   ↓ **独立验证**（不是执行者自述）
VERIFIED
   ↓ 验收谓词成立
ACCEPTED
   ↓ 记账
CHECKPOINTED

失败路径：
UNVERIFIED / EVIDENCE_COLLECTED
   ↓ 验证未通过
REJECTED
   ↓ 记录
FAILURE_EVIDENCE
   ↓
REPLAN

**禁止的转移**（本协议的核心断言）：
  executor self-report → VERIFIED          （必须有独立验证步骤）
  VERIFIED → ACCEPTED 而缺验收谓词          （M-12：完成是 harness 级判定）
  REJECTED → 状态回退到"没发生过"           （M-04：失败证据必须保留）
```

### 3.3 Verified State 最小候选 schema（评估，不实现）

```text
评估以下字段是否够用（PART 14 清单），并逐字段标注"可机械取得 / 需人判 / 不可得"：
  ORIGINAL_GOAL                 可机械（写入时固定）
  TASK_AUTHORITY                需人判（授权来源）
  REPO_IDENTITY                 可机械（git remote）
  WORKTREE_IDENTITY             可机械（pwd / git rev-parse --show-toplevel）
  BASE_SHA                      可机械
  CANDIDATE_SHA                 可机械
  VERIFIED_FACTS                混合（每条需附验证来源）
  VERIFIED_ARTIFACTS            可机械（路径 + 哈希）
  PASSED_GATES                  可机械（门名 + 结果 + 运行命令）
  REVIEW_STATE                  需结构化评审对象（仓内 schema 已存在）
  CI_STATE                      可机械（远端 API）
  FAILURE_EVIDENCE              混合
  REMAINING_WORK                需人判（语义）
  BLOCKERS                      需人判
  PROVENANCE                    可机械（生产者 + 时间 + 来源）
  CHECKPOINT_ID                 可机械（ledger 序号 + 内容哈希）

必须写死的三条语义：
  MEMORY            = navigation hint（**不是** state）
  REPOSITORY/REAL ENV = ground truth
  VERIFIED_STATE    = accepted interpretation backed by evidence
    ⇒ 推论：MEMORY 里的任何东西进入 state 都必须重新验证；
            这直接回答 F-012（memory saved but not enforced）。
```

### 3.4 测量（PART 18 给定）

```text
M1  WRONG_STATE_CONTINUATION   = 在错误的 repo/worktree/SHA 上继续的次数（**可机械检测**）
M2  STALE_SHA_ACCEPTANCE       = 接受了绑定到旧 SHA 的评审/证据的次数（**可机械检测**）
M3  FALSE_CLOSURE              = 在验收谓词未成立时宣布完成的次数（**可机械检测**）
M4  RUNTIME_FAILURE_RECOVERY   = 注入一次执行通道故障后，能否从 ledger 恢复到正确状态
                                 （E3 级：我们**已经**有这个故障的稳定复现方式，见 F-014）
M5  REPEATED_WORK              = 重复已完成工作的次数（可机械：命令/文件证据去重）
M6  HUMAN_INTERVENTION         = 需要人补充状态的次数（结构性停机）
M7  FINAL_CORRECTNESS          = 独立评审
```

```text
**M4 是我们独有的优势**：本机有一个可稳定触发的执行通道故障
（exit 137/139，已发生 3 轮）。这意味着 H5 的"运行时崩溃后恢复"不需要模拟 ——
**真实故障会自己来**。这是把一个环境缺陷转成实验资产。
```

### 3.5 结论词汇

```text
RESULT_VOCABULARY = {
  VERIFIED_STATE_TRANSFER_SAFE,      # 变体臂在 M1–M3 上显著更低且 M7 不降
  VERIFIED_STATE_NO_ADVANTAGE,       # 无差异 ⇒ 说明 prompt+memory 已足够（这本身是重要结论）
  VERIFIED_STATE_HAS_COST,           # 变体更差（例如 ledger 维护成本吃掉收益）
  INSUFFICIENT_EVIDENCE
}
```

---

## 4. 三个协议共同的 promotion 前置（写进候选前的门槛）

```text
任何 H2/H4/H5 结论要进入 canonical，必须同时满足：
  ① 至少 N_PER_ARM ≥2 且每臂都有机械可核的终态（不接受"实验跑完"替代"仓库闭环"）
  ② 无未处置的 P0/P1；P2 有 disposition
  ③ 独立评审（exact SHA）+ CI + merge + post-merge verify
  ④ 结论词汇来自预注册集合，且判定边界在开跑前已冻结
  ⑤ **不得**把 E1（外部材料）当作 promotion 依据 —— 外部只提供假设来源
  ⑥ 受限条款：任何"移除 HOT 内容"的结论必须先满足 §0 的 P6（路由可达）与 P7（门承重）
```

---

## 5. 明确不做（本轮）

```text
不实现任何上述机制（PART 20）
不改 H3 detector（H3_B1_STATUS 保持 COLLECTING，旁路收集，不阻塞 H2）
不制造 ticket 以凑 H3 样本
不引入 daemon / 数据库 / 服务
不复制 LongHorizon 的固定 Agent 拓扑（ROLE_SEPARATION != PROCESS_TOPOLOGY）
```

## 6. 顺序（登记，不执行）

```text
1. N6 闭环（本 PR）
2. #45 / #46 的机械映射各自落地（它们是几乎所有后续实验的前置）
3. H2（Lazy Skill / Progressive Disclosure）—— 依赖 #46
4. H4（MICRO/LOW Ablation）—— 依赖 #45 的"门是否承重"判定
5. H5（Verified State）—— 可与 H4 并行（不同标的），但必须先满足 §0 全部前置
6. V1.2 Synthesis
```
