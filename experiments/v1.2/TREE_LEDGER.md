# TREE_LEDGER — V1.2 逻辑工作树账本

> **本文件是 V1.2 的「逻辑研究树」+「Git 执行树」的**唯一**登记处。非 canonical。**
>
> **纪律**：一个 *logical node* 与 *git branch / worktree / commit* **不是一回事**。
> 一个 node 可以对应多个分支；一个分支也可能只负责某个 node 的 closure。
> 禁止把两者混写，也禁止**默默**改变项目树：
> 任何节点增删都必须带 `TREE_CHANGE = / ADDED_NODES = / REMOVED_NODES = / REASON =`。
>
> 新增主研究节点（H6/H7…）的**准入条件**只有一个：
> `A new finding invalidates a current architecture assumption`。
> 普通 P2/P3 走 issue / backlog，**不**扩展主树。

*Last reconciled：2026-10-10，针对 `origin/main = c028a719ba27ab7aff3035c6269e477491983219`。*

---

## A. Logical Research Tree

```text
N0  V1.2 ROOT
│
├── N1  H1 — Bounded Bootstrap / HOT Context                      [CLOSED]
│       STATUS = CLOSED / INSUFFICIENT_EVIDENCE
│
├── N2  H2 — Lazy Skill / Progressive Disclosure                  [PLANNED]
├── N3  H3 — Prospective Structure Shadow                         [COLLECTING]
├── N4  H4 — MICRO/LOW Governance Ablation                        [PLANNED]
├── N5  H5 — Verified State + Fresh Episode Recovery              [PLANNED]
│
├── N6  Mechanization Gap Analysis                                [ACTIVE]
│   ├── N6.1 Current Rule Inventory                               [ACTIVE]
│   ├── N6.2 LongHorizon Mechanism Extraction                     [ACTIVE]
│   ├── N6.3 Failure → Mechanism Mapping                          [ACTIVE]
│   ├── N6.4 Rule Migration / Target Layer Matrix                 [ACTIVE]
│   └── N6.5 H2 / H4 / H5 Protocol Freeze                         [ACTIVE]
│
├── N7  #45 Load-Bearing Gate Disposition                         [BACKLOG / E3]
├── N8  #46 Route Reachability Disposition                        [BACKLOG / E2]
│
├── N9  V1.2 Architecture Synthesis                               [PLANNED]
├── N10 V1.2 Candidate                                            [PLANNED]
├── N11 Fresh Adversarial Audit                                   [PLANNED]
├── N12 Real-Project Dogfood                                      [PLANNED]
└── N13 V1.2 Release                                              [PLANNED]
```

```text
TREE_NODES_TOTAL = 19   （N0 + N1–N13 = 14，N6.1–N6.5 = 5）
CURRENT_NODE     = N6.4 — Rule Migration / Target Layer Matrix
```

### A.1 节点详情

#### N0 — V1.2 ROOT
```text
NAME = V1.2 experiment programme
PARENT = （无）
STATUS = ACTIVE
ENTRY_CRITERIA = V1.1.1 canonical 已 merged 且被认为"提示词过重"这一前提被 H1 量化
EXIT_CRITERIA = N13 发布，或某一轮 audit 判定 arch 假设失效（→ 允许新增主节点）
EVIDENCE = experiments/v1.2/README.md + evidence-lineage.md
BRANCH = （multiple）
WORKTREE = （multiple）
HEAD_SHA = （n/a）
PR = （n/a）
DEPENDENCIES = （无）
BLOCKERS = （无）
NEXT_NODE = N6
```

#### N1 — H1 Bounded Bootstrap / HOT Context
```text
STATUS = **CLOSED**
ENTRY_CRITERIA = 需要量化"把治理全塞进 HOT"的实际代价
EXIT_CRITERIA = 一轮完整 A/B + 诚实入仓 + 独立评审
EVIDENCE = experiments/v1.2/h1-hot-context/{README,results}.md + runs/README.md（run 注册表）
  H1_RESULT = INSUFFICIENT_EVIDENCE
  BLIND_EVALUATION = VOID（匿名化存在完美判别器）
  AUTO_INJECTION_TRUNCATION_CONFIRMED = YES ／ END_TO_END_GOVERNANCE_LOSS_PROVEN = NO
  HOT：15,784 → 6,382 js_chars（−59.6%）；可见投递 7,840 → 4,354（−44.5%）
BRANCH = experiment/v1.2-h1-hot-context-ablation → experiment/v1.2-h1-closure-ledger
WORKTREE = v1.2-h1-hot-context
HEAD_SHA = 639d19991256156bc9d2cec266e611931d6a8645（closure ledger）
PR = #47（merge 5ea5ed41f42cb83c97e0227d594b7501ed617eba）
     #48（merge c028a719ba27ab7aff3035c6269e477491983219）
DEPENDENCIES = （无）
BLOCKERS = （无）
NEXT_NODE = N6
NOTE = H1 **没有**产出 promotion 建议，只产出了量化事实与三条 issue/发现
```

#### N2 — H2 Lazy Skill / Progressive Disclosure
```text
STATUS = PLANNED
ENTRY_CRITERIA = ① #46 的机械映射落地（否则变体臂在"部分路由不可达"环境中运行）
                 ② N6.5 §0 的 P1–P7 全部满足
EXIT_CRITERIA = ≥2 臂 × ≥2 任务，且结论词汇 ∈ {DISCLOSURE_SAFE, DISCLOSURE_HAS_COST,
                INSUFFICIENT_EVIDENCE}
EVIDENCE = （待产）experiments/v1.2/mechanization-gap/experiment-protocols.md §1
BRANCH = （待建）
WORKTREE = （待建）
PR = （待开）
DEPENDENCIES = N6（协议）+ N8（#46）
BLOCKERS = #46 未落地
NEXT_NODE = N9
```

#### N3 — H3 Prospective Structure Shadow
```text
STATUS = **COLLECTING**（旁路，不阻塞任何节点）
ENTRY_CRITERIA = 协议在默认分支冻结（merge a7f9e7c1fb2b868ffae9627825c9d1953b36956d）
EXIT_CRITERIA = TARGET = 10 个 **interpretable** prospective observation
EVIDENCE = H3_B1_STATUS = COLLECTING；PROSPECTIVE_EPOCH_START = 2026-10-08T04:16:03Z；
  detector = experiments/v1.2/structure_delta.py（V0_IMPLEMENTED_NOT_WIRED）
BRANCH = experiment/v1.2-prospective-shadow（已合并）
HEAD_SHA = 06e9cb873818ad9018c3585f267873891a4f25a7
PR = #43（merge a7f9e7c1fb2b868ffae9627825c9d1953b36956d）
DEPENDENCIES = （无）
BLOCKERS = （无 —— **不得**为凑样本制造 ticket）
NEXT_NODE = N9
NOTE = 本轮（N6）**未**触碰 H3；detector 未改；不接 CI；不 block merge
```

#### N4 — H4 MICRO/LOW Governance Ablation
```text
STATUS = PLANNED
ENTRY_CRITERIA = ① #45 的"门是否承重"判定落地（H4 的判据依赖机械验收的判别力）
                 ② N6.5 §0 的 P1–P7 全部满足
                 ③ 三臂设计（含 ARM_INJECT）可用
EXIT_CRITERIA = ≥4 个真实 MICRO/LOW 任务 × 3 臂；结论 ∈ 预注册集合
EVIDENCE = experiment-protocols.md §2
DEPENDENCIES = N6（协议）+ N7（#45）
BLOCKERS = #45 未落地
NEXT_NODE = N9
```

#### N5 — H5 Verified State + Fresh Episode Recovery
```text
STATUS = PLANNED
ENTRY_CRITERIA = N6.5 §0 全部满足 + 一个可重放的 append-only ledger 形状被定义
EXIT_CRITERIA = M1–M3（wrong-state / stale-SHA / false closure）机械可测且变体臂更低，
                或明确判 NO_ADVANTAGE / HAS_COST
EVIDENCE = experiment-protocols.md §3；机制来源见 longhorizon-mechanism-map.md
  （M-02 Verified State / M-06 Fresh Episode / M-12 Completion Semantics，均 E1）
DEPENDENCIES = N6（协议）
BLOCKERS = （无硬阻塞；但 §0 P3/P4 必须先做）
NEXT_NODE = N9
NOTE = 本机有**可稳定触发**的执行通道故障（exit 137/139，已发生 3 轮）⇒ M4
       （runtime failure recovery）不需要模拟，真实故障会自己来
```

#### N6 — Mechanization Gap Analysis
```text
STATUS = **ACTIVE**
ENTRY_CRITERIA = H1 闭环后，需要把"哪些提示词约束可以交给机器"系统化
EXIT_CRITERIA = N6.1–N6.5 全部产出 + 独立评审 + 入仓
DELIVERABLES = experiments/v1.2/TREE_LEDGER.md（本文件）
             + experiments/v1.2/mechanization-gap/{README,rule-inventory,
               longhorizon-mechanism-map,failure-mechanism-map,rule-migration-matrix,
               experiment-protocols}.md
DEPENDENCIES = N1（H1 的实测事实与教训）
BLOCKERS = （无）
NEXT_NODE = N9
```

#### N6.1 — Current Rule Inventory
```text
NODE_ID = N6.1   NAME = Current Rule Inventory   PARENT = N6
STATUS = ACTIVE
ENTRY_CRITERIA = 需要一个"按独立行为约束拆分"的规则清单，作为迁移矩阵的输入
EXIT_CRITERIA = 每条规则都有 RULE_ID 与 11 个字段；ID 唯一且连续
EVIDENCE = mechanization-gap/rule-inventory.md（95 条 R-V12-*，含评审补录的 R-V12-095）
  + 实测章节字符基数（AGENTS 13,756 / RULES 6,843 / BOOTSTRAP 5,083 / MEMORY 2,028）
  + 6 个重述点登记
DEPENDENCIES = （无）
BLOCKERS = （无）
NEXT_NODE = N6.2
```

#### N6.2 — LongHorizon Mechanism Extraction
```text
NODE_ID = N6.2   NAME = LongHorizon Mechanism Extraction   PARENT = N6
STATUS = ACTIVE
ENTRY_CRITERIA = 需要知道外部长周期 harness 有哪些机制可借、哪些必须拒
EXIT_CRITERIA = 逐机制给出 SOURCE / WHAT_IT_DOES / WHAT_FAILURE_IT_PREVENTS / 分层归属 /
                OUR_LOCAL_ANALOGUE / OUR_LOCAL_EVIDENCE / ADOPT_CONCEPT / TARGET_LAYER
EVIDENCE = mechanization-gap/longhorizon-mechanism-map.md
  12 机制（全部 VERIFIED_FROM_SOURCE，含逐字引用）
  + 3 条 Anthropic 独立佐证 + 1 条 OpenAI **SECONDARY**（明确标注不支撑判定）
  + 7 条 REJECT（拒绝的是实现形态，不是概念）
DEPENDENCIES = （无）
BLOCKERS = OpenAI 一手页不可达（challenge 页）⇒ 该来源仅作方向佐证
NEXT_NODE = N6.3
```

#### N6.3 — Failure → Mechanism Mapping
```text
NODE_ID = N6.3   NAME = Failure → Mechanism Mapping   PARENT = N6
STATUS = ACTIVE
ENTRY_CRITERIA = 需要把"失败"当一等对象，而非从规则反推
EXIT_CRITERIA = 每条失败给出 11 个字段，且**区分真实发生 / 仅属假设**
EVIDENCE = mechanization-gap/failure-mechanism-map.md（22 条 F-*）
  E3=9 / E2=6 / E1_GAP=1 / E1_ATTESTED=0 / HYPOTHESIS=6
  + 3 个跨条模式：PATTERN-A「空的东西看起来像满的」/ B「未验证进入可信面」/ C「声明与目的地脱节」
  + NEW_ISSUES_FROM_THIS_FILE = 0（理由：与 #45 共享同一目标机制，或属实验线纪律）
DEPENDENCIES = N6.1
BLOCKERS = （无）
NEXT_NODE = N6.4
```

#### N6.4 — Rule Migration / Target Layer Matrix
```text
NODE_ID = N6.4   NAME = Rule Migration / Target Layer Matrix   PARENT = N6
STATUS = ACTIVE
ENTRY_CRITERIA = 需要有规则集（N6.1）与失败集（N6.3）才能做去向判定
EXIT_CRITERIA = 每条规则有唯一目标层；每个"可移出 HOT"都有替代论证
EVIDENCE = mechanization-gap/rule-migration-matrix.md
  七层分类：A=29 B=16 C=26 D=18 E=3 F=1 G=2（=95）
  + 决定性事实：AGENTS §6–§10 共 5,096 字符（37%）**从未自动投递**
  + HOT 移除候选逐条走 MECHANIZATION_MUST_REPLACE 四问
DEPENDENCIES = N6.1 + N6.3
BLOCKERS = #46 未落地（B 组下沉的前置）
NEXT_NODE = N6.5
```

#### N6.5 — H2 / H4 / H5 Protocol Freeze
```text
NODE_ID = N6.5   NAME = H2 / H4 / H5 Protocol Freeze   PARENT = N6
STATUS = ACTIVE
ENTRY_CRITERIA = 前四部分完成后才设计实验（否则会设计出无测量面的协议）
EXIT_CRITERIA = 三个协议各自的对照/变体/测量/停止条件/结论词汇 + 共享前置 P1–P7
EVIDENCE = mechanization-gap/experiment-protocols.md
DEPENDENCIES = N6.1–N6.4
BLOCKERS = （无 —— 本轮只设计不执行）
NEXT_NODE = N9
```

#### N7 — #45 Load-Bearing Gate Disposition
```text
STATUS = BACKLOG / E3
EVIDENCE = ISSUE #45；本地四步复现（含 ruff.toml 哈希级恢复）；failure-mechanism-map F-010
TARGET_LAYER = C（MECHANICAL_GATE）
DEPENDENCIES = （无）
BLOCKERS = （无；可以随时立独立工具票）
NOTE = 与 F-009/F-018（断言层/自检层空转）**共享同一目标机制**（正控/突变探针）
       ⇒ 按 PART 21 合并处置，不拆成多个 issue
```

#### N8 — #46 Route Reachability Disposition
```text
STATUS = BACKLOG / E2
EVIDENCE = ISSUE #46；git ls-tree 双向取证（base e1da154 不存在 / main 存在，由 2ed08f6 引入）；
           failure-mechanism-map F-011
TARGET_LAYER = C（MECHANICAL_GATE）
DEPENDENCIES = （无）
BLOCKERS = （无）
NOTE = **同时是 N2（H2）与所有 B 组规则下沉的前置条件**
```

#### N9 — V1.2 Architecture Synthesis
```text
NODE_ID = N9   NAME = V1.2 Architecture Synthesis   PARENT = N0
STATUS = PLANNED
ENTRY_CRITERIA = N6 闭环（本 PR 后）+ 至少一个实验（H2/H4/H5）有**预注册集合内**的结论
EXIT_CRITERIA = 一份候选架构，明确 HOT/WARM/机械/harness/adapter 各层的最终分工
EVIDENCE = （待产）
BRANCH = （待建）   WORKTREE = （待建）   HEAD_SHA = （n/a）   PR = （待开）
DEPENDENCIES = N6 + （N2|N4|N5 至少其一）
BLOCKERS = 尚无实验结论
NEXT_NODE = N10
```

#### N10 — V1.2 Candidate
```text
NODE_ID = N10   NAME = V1.2 Candidate   PARENT = N0
STATUS = PLANNED
ENTRY_CRITERIA = N9 产出候选架构
EXIT_CRITERIA = 存在一个 exact SHA 的候选变更集，可被独立评审
EVIDENCE = （待产）
BRANCH = （待建）   WORKTREE = （待建）   HEAD_SHA = （n/a）   PR = （待开）
DEPENDENCIES = N9
BLOCKERS = （依赖 N9）
NEXT_NODE = N11
```

#### N11 — Fresh Adversarial Audit
```text
NODE_ID = N11   NAME = Fresh Adversarial Audit   PARENT = N0
STATUS = PLANNED
ENTRY_CRITERIA = N10 有 exact SHA 的候选
EXIT_CRITERIA = 无未处置 P0/P1；P2 有 disposition
EVIDENCE = （待产）
BRANCH = （待建）   WORKTREE = （待建）   HEAD_SHA = （n/a）   PR = （待开）
DEPENDENCIES = N10
BLOCKERS = （依赖 N10）
NEXT_NODE = N12
```

#### N12 — Real-Project Dogfood
```text
NODE_ID = N12   NAME = Real-Project Dogfood   PARENT = N0
STATUS = PLANNED
ENTRY_CRITERIA = N11 PASS
EXIT_CRITERIA = 在**至少一个真实外部仓**上跑通（不是本仓自证）
EVIDENCE = （待产 —— 候选真实仓：zhihu-grabber-toolkit）
BRANCH = （待建）   WORKTREE = （待建）   HEAD_SHA = （n/a）   PR = （待开）
DEPENDENCIES = N11
BLOCKERS = （依赖 N11）
NEXT_NODE = N13
NOTE = 这一节点是防"本仓自证"的关键：V1.1.1 的 R1 明确治理是 D 层默认，
       只在**采纳它的仓**里才算真正生效。
```

#### N13 — V1.2 Release
```text
NODE_ID = N13   NAME = V1.2 Release   PARENT = N0
STATUS = PLANNED
ENTRY_CRITERIA = N12 通过 + README §13 的 6 条 promotion 前置全部满足
EXIT_CRITERIA = 版本发布，canonical 更新
EVIDENCE = （待产）
BRANCH = （待建）   WORKTREE = （待建）   HEAD_SHA = （n/a）   PR = （待开）
DEPENDENCIES = N12
BLOCKERS = （依赖 N12）
NEXT_NODE = （无 —— 树终点）
```

---

## B. Git Execution Tree

> 与逻辑树**分开**记账。本节只描述真实的 git 对象，不做语义判断。

```text
DEFAULT_BRANCH      = main
DEFAULT_BRANCH_SHA  = c028a719ba27ab7aff3035c6269e477491983219
                      （= PR #48 的 merge；`git ls-remote origin refs/heads/main` 复核一致）
```

### B.1 ACTIVE

```text
ACTIVE_EXPERIMENT_BRANCHES =
  experiment/v1.2-mechanization-gap-analysis   （本轮 N6 交付）
  ⚠️ **本文件不写死自身 SHA** —— 自引用无法收敛（写进去的那一刻就变了）。
     取当前 head 请用：`git rev-parse HEAD`（或对该分支 `git ls-remote origin`）。

ACTIVE_WORKTREES =
  <WORKSPACE_ROOT>/v1.2-mechanization-gap     [experiment/v1.2-mechanization-gap-analysis]
  <GOVERNANCE_CLONE_ROOT>                     [audit/hermes-multibot-r062]（父 clone，勿打扰）

  ⚠️ **路径在本文件中一律用占位符**（`<WORKSPACE_ROOT>` / `<GOVERNANCE_CLONE_ROOT>`）：
     本仓是 **PUBLIC**，R2 第二层对 PUBLIC 仓**不存在豁免**，只允许占位符形态
     （同 `deployment/deployment-profile.md` 的既有做法）。
     **这一条是被机器抓出来的**：本文件初稿写了真实家目录路径，`validate_governance.py`
     的 `no-credentials-anywhere` 与 `validate_public_release.py` 同时报 FAIL。
     记录下来，因为它正是本目录主张的"声明要能被机器对照"的一个现场实例。
```

### B.2 MERGED（全部已进 origin/main —— 逐个用 `git merge-base --is-ancestor` 核过）

```text
experiment/v1.2-foundation                  @ 56769cf   MERGED
experiment/v1.2-replay-corpus               @ f84d4ae   MERGED   （PR #40）
experiment/v1.2-structure-delta-v0          @ eb2f51f   MERGED   （PR #41）
experiment/v1.2-live-shadow                 @ 8aff541   MERGED   （PR #42）
experiment/v1.2-prospective-shadow          @ 06e9cb8   MERGED   （PR #43）
experiment/v1.2-h1-hot-context-ablation     @ d9c809e   MERGED   （PR #47）
experiment/v1.2-h1-closure-ledger           @ 639d199   MERGED   （PR #48）
```

### B.3 STALE / PRUNABLE

```text
PRUNABLE_WORKTREES = 8
  /private/tmp/h1-runs/t{01,02,03,04}__{CONTROL,VARIANT}
  原因 = 位于 /tmp，已被系统清理；`git worktree list` 标 prunable。
  后果 = H1 的 run diff **不可事后重放**（见 failure-mechanism-map F-015）。
  处置 = **不** prune（保留元数据以留编号痕迹）；已在 h1 runs/README.md 显式声明
         `REPLAY_WORKTREE_REVERIFIABLE_NOW = NO`。
  教训 = 已登记为 R-V12-089（产物必须落持久化位置）→ H2/H5 的协议前置条件 P3。

STALE_WORKTREES = NONE（除上述 prunable 外无）

WORKTREE_COUNTS（`git worktree list` 实测，2026-10-10）：
  NON_PRUNABLE = 8   PRUNABLE = 8

UNMERGED_LOCAL_COMMITS（`git rev-list --count origin/main..<branch>` 逐分支实测）：
  experiment/*                            = **0**（7 个已合并分支）
  experiment/v1.2-mechanization-gap-analysis = **不写数字** —— 它每提交一次就变一次，
                                              写进去必然立刻过期（同"不自写自身 SHA"）。
                                              取法：`git rev-list --count origin/main..HEAD`
  audit/hermes-multibot-r062              = 2   ← **非 experiment 分支**，父 clone 的审计分支，
                                                  有意不合并（勿动）
  work/p1-orchestrator-closure-doctrine   = 1   ← 同上，非本实验线

  ⚠️ **两次修正记录**：
     ① 初稿写「UNMERGED_LOCAL_COMMITS = 0（逐分支 … 全部为 0）」，只统计了 `experiment/*`
        却写成全部 —— 外部评审用上面两条非 experiment 分支证伪。
     ② 修正稿把本分支写成「= 2（本 PR 的两提交）」，而补提交之后实际是 3 —— **同一类错误再犯一次**，
        因为"当前分支的提交数"本身就是一个会漂移的自引用量。
     ⇒ 处置：按域记账，并且**凡是会随本次提交变化的数字一律不写**，只写取法。
     教训：`SELF_REFERENTIAL_COUNTS GO STALE BY CONSTRUCTION`。
```

### B.4 本轮的 Git 位置（阶段汇报用）

```text
GIT_LOCATION =
  repo   = FlapPearLabs/agent-engineering-governance
  branch = experiment/v1.2-mechanization-gap-analysis
  worktree = <WORKSPACE_ROOT>/v1.2-mechanization-gap
  base   = c028a719ba27ab7aff3035c6269e477491983219
  head   = （提交前为 base；提交后更新）
```

---

## C. Tree Footer（每个 checkpoint / 最终报告必须附）

```text
TREE_NODES_TOTAL = 19
CURRENT_NODE = N6 — Mechanization Gap Analysis
CURRENT_NODE_STATUS = ACTIVE（N6.1–N6.5 产出已完成；**状态转 CLOSED 以 merge 为条件**）
NEXT_NODE = N2 — H2 Lazy Skill / Progressive Disclosure（依赖 #46 先落地）
  · 旁路并行：N3 — H3 保持 COLLECTING，**不阻塞** N2
  · 更远：N9 V1.2 Architecture Synthesis（需要 N6 闭环 + 至少一个实验有结论）
GIT_LOCATION =
  repo     = FlapPearLabs/agent-engineering-governance
  branch   = experiment/v1.2-mechanization-gap-analysis
  worktree = <WORKSPACE_ROOT>/v1.2-mechanization-gap
  base     = c028a719ba27ab7aff3035c6269e477491983219（本分支的起点）
  head     = 见 `git rev-parse HEAD` —— 同上：不写死自引用 SHA
```

> **为什么这里不写 `CLOSED`**：本文件此刻尚未 merge，声称 `CLOSED` 就是假闭环
> （`failure-mechanism-map.md` F-013）。状态的权威判据是"进默认分支且 post-merge CI 绿"，
> 不是"文件写了 CLOSED"。merge 后由下一轮的 TREE_CHANGE 记录这次转迁。

---

## D. TREE_CHANGE 记录

```text
[TREE_CHANGE 2026-10-10] 建立本账本（首次）。
ADDED_NODES = N0, N1–N13, N6.1–N6.5（共 19）
REMOVED_NODES = 无
REASON = N6 需要唯一树登记处；此前的实验线状态散落在 daily logs 与各 PR 中，
         没有单一 place 能回答"当前在哪个节点、下一个是什么"。
         （H1 的 INSUFFICIENT_EVIDENCE 与 H3 的 COLLECTING 曾长期只存在于报告文字里。）
```

```text
[TREE_CHANGE 2026-10-10] N6.1–N6.5 从 PLANNED 推进为 ACTIVE。
ADDED_NODES = 无
REMOVED_NODES = 无
REASON = 本轮产出全部五个子节点交付物。
```

> **未发生**：本轮**没有**新增 H6/H7 等主研究节点 —— 无 finding 使现有架构假设失效。
