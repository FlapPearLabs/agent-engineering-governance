# experiments/v1.2/h1-hot-context — H1 HOT context / progressive disclosure ablation（非 canonical）

> 本目录是 V1.2 Experiment 1 / **H1** 的隔离消融实验：检验「更薄的 HOT bootstrap +
> progressive disclosure 是否在普通工程任务上损失高价值 catch」。
> **非 canonical、不接 CI、不 block merge、不改任何 canonical 语义。**
> canonical 控制组 = `AGENTS.md` + `RULES.md` + `references/`（V1.1.1，main @ a7f9e7c）。
> 变量 = **仅** HOT 上下文加载策略。Skill 选择语义、评审政策、风险政策、修复预算、
> detector、CI gate 全部不变（H2/H4 单独测）。

## 0. 第一轮结论

```text
H1_RESULT       = INSUFFICIENT_EVIDENCE
BLIND_EVALUATION = VOID（匿名化存在完美判别器）
```

**理由不是「没跑够」，而是三条各自独立即充分的排除理由**：

1. 存在 additional high-value miss（t03 变体臂漏掉对照臂的3 条治理级发现）；
2. 盲评作废 —— 盲评者独立发现 2 个完美判别器，配对级比较无法在盲态下取得；
3. 每臂每任务 n=1，且环境故障在至少3 对中主导结果。

另外 canonical HOT 面的截断结论本轮已**主动降级**（§4.1）：
`END_TO_END_GOVERNANCE_LOSS_PROVEN = NO` —— 截断 ≠ 治理丢失，补读是清单义务。
详见 `results.md`。

## 1. 目录

| 文件 | 作用 |
|---|---|
| `README.md` | 本文件：实验边界、HOT/WARM/COLD 定义、变量隔离、metric 可观测性 |
| `tasks.yaml` | 任务集（4 个真实历史 ticket，全部 SHA 对已实证可 replay） |
| `lean/CODEBUDDY.md` | **H1_LEAN_HOT_VARIANT** —— 本实验的变量载体（已冻结） |
| `hot_inventory.py` | HOT 面机械计量 + 截断 oracle（`--selftest` 反例自检） |
| `runs/README.md` | **run 身份的唯一注册表**：8 有效 / 2 被取代 / 2 作废 |
| `runs/RUN_*.md` | run 记录（opaque ID；映射表见注册表） |
| `results.md` | 结果 + 缺陷清单 + 混杂声明 + 局限 + 复现前置条件 + 闭环状态 |

## 2. HOT / WARM / COLD 定义（沿用 V1.2 既有概念）

```text
HOT   = agent 启动时默认注入 / 默认必须读的治理内容
WARM  = 仅在任务条件触发时再读的 references / skills / methods
COLD  = scripts / tests / validators / machine checks
```

本仓当前的**真实** HOT 面（由 `hot_inventory.py` 机械测得，非估计）：

```text
通道 1  ~/.workbuddy/MEMORY.md 头部   → deployment/MEMORY_POINTER_CANDIDATE.md
通道 2  工作区根 GUIDANCE_FILES[0]   → AGENTS.md（按 MAX_GUIDANCE_CHARS 截断）
不在通道内  RULES.md（B 层不变量，必须显式全文读）
```

## 3. 变量隔离声明

本轮**只**改 HOT → WARM 的加载策略。以下**明确未改**：

```text
skill selection semantics   = UNCHANGED（H2 单独测；本轮仅记录 routing 是否触发加载）
review policy               = UNCHANGED
risk policy                 = UNCHANGED（lean 的 §3 是 canonical §3 的指针式复述，非新政策）
repair budget               = UNCHANGED（= 2，PART 12）
detector (H3)               = UNCHANGED（未触碰）
CI gates                    = UNCHANGED
canonical 文件              = UNCHANGED（H1_CHANGED_FILES 只含本目录）
```

## 4. 关键事前事实：当前 HOT 面自身在崩塌

`hot_inventory.py` 的截断 oracle 给出一条**独立于本实验假设**的实测结论：

```text
MAX_GUIDANCE_CHARS = 8000（profile 事实：WorkBuddy 5.5.3, 2026-09-04）
AGENTS.md          = 13,756 js chars → 在第 109/151 行被截断，丢 5,916 js chars
被截断的章节       = §6 REVIEW/REPAIR/CI、§7 AUTO-ADVANCE 与 STOP、
                     §7.1 STATE_RESTORE/STATE_FLUSH、§8 治理变更、§9 报告、§10 BOOTSTRAP
```

即：**canonical 控制组自己**在 guidance通道上看不到 STOP 枚举全文、
state continuity 合同、bootstrap 机制说明与修复预算默认值。
这与 `evidence-lineage.md` H1 段记录的本地失败证据
（注入截断导致可见性崩塌，WEM G3 / DH H14）方向一致，
且给出了此前未量化的具体章节清单。

**这不构成对 canonical 的批评** —— canonical 已显式记录该截断
（`BOOTSTRAP_CONTRACT.md` §1 的 `AUTO_INJECTION != FULL_GOVERNANCE_DELIVERY`）。
本轮只把它变成可复算的数字。

### 4.1 截断结论的强度（独立事实核验，非实验变量）

测得的截断**不等于**治理丢失。二者必须分开表述：

```text
AUTO_INJECTION_TRUNCATION_CONFIRMED = YES
  依据 = 13,756 js chars 在第 109/151 行处被裁剪，丢弃 5,916 js chars（可复算）

AUTO_INJECTION_DROPPED_SECTIONS =
  §6  REVIEW / REPAIR / CI（尾部）
  §7  AUTO-ADVANCE 与 STOP（尾部）
  §7.1 STATE_RESTORE / STATE_FLUSH
  §8  治理变更（默认协议）
  §9  报告（novelty-first）
  §10 BOOTSTRAP（如何被新会话看到）
```

canonical 已自行声明这四个字段（`BOOTSTRAP_CONTRACT.md` §1），本轮只做独立复核：

```text
FIRST_TURN_AUTO_INJECTION_COVERAGE = PARTIAL
FULL_GOVERNANCE_REACHABILITY       = YES_IF_BOOTSTRAP_FOLLOWED
FULL_GOVERNANCE_AUTOMATIC_DELIVERY = NO
MECHANICAL_ENFORCEMENT             = PARTIAL
```

**bootstrap 路径是否随后要求/读取全文 —— 已核验（只做事实核验，未扩成实验变量）**：

```text
FULL_GOVERNANCE_LATER_LOADED = YES_IF_BOOTSTRAP_FOLLOWED
证据 = deployment/BOOTSTRAP_CONTRACT.md §2.2  BOOTSTRAP_CHECKLIST
   B2 读治理仓：AGENTS.md + RULES.md + 相关 references
   B3 发现仓内权威 →「必须继续读到其指向的全文」
   §2.2 尾注：「仓本地权威可加严本清单，不得削弱 B1–B5 的读取义务」
被截断的 AGENTS.md §10:148 自身即规定该清单含「发现并读取仓内AGENTS/RULES 全文」
   ⇒ 被丢弃的尾部自己规定了补读全文的义务
```

**因此本轮不声称端到端治理丢失**：

```text
END_TO_END_GOVERNANCE_LOSS_PROVEN = NO
理由 = 截断是first-turn 自动注入通道的事实；补读是清单义务（B1–B6）。
       义务存在 ≠ 已执行。本轮未测「清单是否被实际执行」，
       故真实暴露面是「依赖 agent 遵守一条被截断掉的规则」，
       而非「治理不可达」。
```

这条区分对 H1 的意义：lean variant 的收益**不能**表述为「修复了治理丢失」
（canonical 本就不声称丢失）；它可表述为「把关键内容移出截断区」。

## 5. 第一轮的 HOT 计量（`python3 hot_inventory.py`）

```text
CONTROL  hot js_chars = 15,784（MEMORY_POINTER 2,028 + AGENTS.md 13,756）
         guidance 实际投递 = 7,840 js chars / 108 行（其余被丢弃）
         强制全文读 = RULES.md 6,843

VARIANT  hot js_chars = 6,382（MEMORY_POINTER 2,028 + lean/CODEBUDDY.md 4,354）
         guidance 实际投递 = 4,354 js chars / 157 行（完整投递，0 丢弃）
         强制全文读 = 无（改为路由加载）

HOT_REDUCTION            = 59.6%
GUIDANCE_VISIBLE_REDUCTION = 44.5%
VARIANT_FULLY_DELIVERED  = YES
TOKEN_USAGE              = NOT_OBSERVABLE（metrics.md 已定；禁止由字符数估算）
```

`APPROX_TOKENS` 一律记 `NOT_OBSERVABLE`。本目录**不产出** token 估算。

## 6. 不可删的安全底线与 MECHANICAL_REPLACEMENT

lean variant 的 8 条底线（N1–N8）见 `lean/CODEBUDDY.md` §2。其中：

```text
MECHANICAL_REPLACEMENT = N6 NO FALSE PASS
  → scripts/validate_governance.py + scripts/validate_public_release.py（COLD，CI 强制）
  → 覆盖完整性 = 仅本仓产物；agent 侧 PASS 措辞纪律仍在 HOT
N1–N5, N7, N8 = 无机械替换者 → 保留在 HOT
```

PART 6 的底线逐条对齐：AUTHORITY BEFORE ACTION（N1）、UNDERSTAND BEFORE EDIT（N2）、
EVIDENCE BEFORE CONFIDENCE（N3）、STOP ON AUTHORITY UNCERTAINTY（N4）、
ONE ACTIVE WRITER / isolated worktree（N5）、no false PASS（N6）、
no stale review transfer（N7）、no silent baseline drift（N8）—— **无一被删除**。

## 7. 路由纪律（progressive disclosure，非「先全读再决定」）

lean 的路由表（`lean/CODEBUDDY.md` §4）覆盖 9 个条件分支，一次任务通常命中 1–3 行。
实测变体臂在 t01/t02/t03/t04 四对中均**自报**遵守（只加载路由命中的 1–3 份 WARM，
未预读全量 `references/`，无 `ESCALATED_LOAD`）。

**但路由表本身存在一个已证实的缺陷（本轮新发现）**：t04 变体臂报告该表把评审任务
指向 `references/review-evidence.md`，而**该文件在该 base 不存在**（编排者已用文件
枚举独立确认）。即渐进披露的路由行可能把fresh agent 送到死路径。
这是载体级缺陷，不是执行者失误 —— 详见 `results.md` §8 F2。

## 8. 防 prompt tuning overfit 的处置

PART 13 要求：任何新增内容必须先回答「通用高价值 invariant 还是 task-specific patch」。

**lean variant 已冻结，本轮全程未修改**：冻结后编排者复算 SHA256，
`lean/CODEBUDDY.md` = `86e24c08…` 与冻结时逐字节一致；`tasks.yaml` = `25ba7d1f…`
同样未变；放入三处 VARIANT worktree 的载体亦逐字节一致。
`PROMPT_TUNING = FROZEN`。

本轮对variant 的**零修改**是机械证据（内容哈希），不是声明。
t04 发现的路由表悬空目标**只进入 FINDING，不进入 PROMPT PATCH** ——
修它会给下一轮 arm 引入新的不对称，正是 PART 18 禁止的方向。

若后续轮次需要新增规则，必须先回答上述问题；task-specific 一律 `DO NOT ADD TO HOT`。

## 9. 本实验的完成状态（防误读）

```text
t01 / t02 / t03 / t04 = 均已跑，4 任务 × 2 臂 = 8 有效 run（注册表见 runs/README.md）
作废 run            = 2（均为 harness 缺陷，非 worker 缺陷；见 runs/README.md §3）
blind evaluation    = 已派，但 **VOID**（匿名化存在完美判别器，见 results.md §7）
多轮验证            = NOT_DONE
H2 / H4             = NOT_STARTED
canonical 变更      = NONE
H3 变更             = NONE
GitHub evidence     = MERGED（PR #47，merge `5ea5ed4`；见 results.md §11）
H1_ROUND1_STATUS    = CLOSED
局限                = 11 项（见 results.md §9）
复现前置条件        = 5 项，**尚未实现**（见 results.md §10）
```

## 10. 复现

```text
python3 experiments/v1.2/h1-hot-context/hot_inventory.py            # 计量表
python3 experiments/v1.2/h1-hot-context/hot_inventory.py --selftest  # 反例自检（T2 已恢复）
python3 experiments/v1.2/h1-hot-context/hot_inventory.py --json      # 机器可读
python3 -m unittest discover -s experiments/v1.2/tests -v            # 材料自检
```
