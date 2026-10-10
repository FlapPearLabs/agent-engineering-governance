# N6.2 — LongHorizon Mechanism Extraction（V1.2 mechanization gap analysis）

> **状态 = N6.2 本轮产物。非 canonical。**
> 外部材料一律 **E1**，**不得**直接升级为 canonical rule。
> 本文件**不是**项目摘要 —— 只抽取与长周期执行 / Verified State / fresh episode /
> 独立验证 / checkpoint-recovery 有关的机制，并逐条判定我们是否采纳**概念**。

## 0. 证据分级与检索诚实性

```text
E1 = 外部材料（本文件的主要证据）
E2 = 本地单次观测（有精确 SHA/命令）
E3 = 本地可复现、有正控

本次检索的可信度分级（**必须随结论一起读**）：
  VERIFIED_FROM_SOURCE      = 我读到了原文（README 或源码）
  SECONDARY_MENTION         = 只经由搜索引擎快照/第三方镜像，未读到一手页
  NOT_FOUND                 = 明确未找到
```

### 0.1 检索结果摘要

| 来源 | 状态 | 说明 |
|---|---|---|
| `AMAP-ML/LongHorizon-Harness` | **VERIFIED_FROM_SOURCE** | 仓库存在（MIT，arXiv:2608.01964）。读了 README + 源码：`src/lh_harness/prompt_texts.py` / `src/lh_harness/role_prompts.py` / `src/lh_harness/manager.py` / `src/lh_harness/types.py` / `src/lh_harness/adapters/base.py` / `src/lh_harness/environment/base.py` / `src/lh_harness/trajectory_artifacts.py` / `src/lh_harness/runtime_signals.py`。**仓库无 `docs/` 目录** —— 架构表达在 README 与角色 prompt 文本目录里。 |
| Anthropic `harness-design-long-running-apps` | **VERIFIED_FROM_SOURCE** | 2026-03-24 发布，作者 Prithvi Rajasekaran（原文可读原文）。 |
| Anthropic `effective-harnesses-for-long-running-agents` | **VERIFIED_FROM_SOURCE** | 2025-11-26 发布。 |
| OpenAI `harness-engineering` | **SECONDARY_MENTION** ⚠️ | 直连 `openai.com/index/harness-engineering` 返回 ~10KB challenge/stub 页，**未取到正文**。引文来自搜索引擎渲染副本与第三方镜像 `wayintoai.com`。**发布日未确认**（镜像称 ~2026-02；OpenAI 侧未确认）。 |

⚠️ **对 OpenAI 材料的处理纪律**：因为只有二手证据，本文件**不用它支撑任何 ADOPT_CONCEPT 判定**；
它的用途仅限"方向性佐证"，并且在 N6.4 的 `EXTERNAL_EVIDENCE_LEVEL` 列标记为 `E1-SECONDARY`。

---

## 1. 机制登记

### M-01 — Original Goal Persistence（原始目标跨轮持续存在）
```text
SOURCE = LongHorizon README（VERIFIED_FROM_SOURCE）
原文 = "**Plan → act → verify → checkpoint or recover → repeat — until the work is actually done.**"
      mermaid 节点 = "Original goal +<br/>verified state" --> "Plan the next<br/>bounded step"
      src/lh_harness/prompt_texts.py MANAGER_INSTRUCTIONS: "Your input contains the original request, a stable
      task contract, the previous current-task state, and the original natural-language reports
      from all auditor rounds."
      "1. Maintain `Current task state:` from the original request and audited facts."

WHAT_IT_DOES = 每轮重建 prompt 的**输入集合固定包含原始目标**，而不是让目标随上下文衰退。
WHAT_FAILURE_IT_PREVENTS = 目标漂移 / 后期轮次为局部收益牺牲原始目标。
IS_IT = execution harness behavior（循环输入契约）
OUR_LOCAL_ANALOGUE = AGENTS.md §7.1 STATE_RESTORE 的 recovery receipt
      （含 PROJECT / TARGET / SPEC / CURRENT_LEGAL_FRONTIER / READY_TO_CONTINUE）
OUR_LOCAL_EVIDENCE = 本仓 §7.1 已有字段定义，但**没有"每轮重建"的机制** ——
      我们的 state 是"会话开始时恢复一次"，对方是"每轮重建"。
ADOPT_CONCEPT = EXPERIMENT
WHY = 我们的长周期缺陷不在"开局不知道目标"，而在"多个 session 后目标靠人复述"。
      对方把目标做成**循环输入的不变量**，值得在 H5 里作为变体臂验证。
TARGET_LAYER = HARNESS_STATE_MACHINE（H5 验证）
```

### M-02 — Verified State（只有通过独立验证的结果才成为可信状态）
```text
SOURCE = LongHorizon README + arXiv:2608.01964（VERIFIED_FROM_SOURCE）
原文 (README) = "Only results that pass independent verification become trusted task state.
                A rejected result remains evidence, not progress."
原文 (arXiv abstract) = "...maintains the task state explicitly outside execution and updates it
                only with facts independently verified from the environment."
原文 (src/lh_harness/prompt_texts.py) = "Cite an auditor round such as `round_003` for every fact. Without audit
                evidence, label it unverified. Never promote an executor's unaudited claim."

WHAT_IT_DOES = 状态更新有**准入条件**：必须引用一条独立验证记录；否则显式标 unverified。
WHAT_FAILURE_IT_PREVENTS = 执行者的自述被当成进度（**这正是我们的头号失败类**）。
IS_IT = governance invariant（**这一条我判它是普适的**，不是实现细节）
OUR_LOCAL_ANALOGUE = R3（EVIDENCE BEFORE CONFIDENCE / UNKNOWN != PASS）+
      AGENTS §7.1 的 STATE_FLUSH —— 但我们的 R3 管**声明**，不管**状态转移**
OUR_LOCAL_EVIDENCE = H1：两臂都自报 `VALID_COMPLETION = NO` 且理由经复核成立（R3 生效）；
      但同一实验里，**编排者自己的记录转录错误**被盲评者当成实验发现（D8）——
      说明"未验证的东西可以通过记录进入可信面"。
ADOPT_CONCEPT = YES
WHY = 这是本轮**最强的一条**：它把 R3 从"措辞纪律"升级为"状态机的转移条件"。
      我们的 MEMORY 是 navigation hint，但**没有任何机制阻止**一个未经独立验证的结论
      写进 MEMORY 或 canonical 并被下游当事实。
TARGET_LAYER = HARNESS_STATE_MACHINE（H5 核心）
```

### M-03 — Unverified vs Verified Evidence Separation（证据分级）
```text
SOURCE = LongHorizon src/lh_harness/prompt_texts.py / types.py（VERIFIED_FROM_SOURCE）
原文 = "In round one, hypotheses may come from the request, but current desktop, file, webpage,
        application, or service facts must remain unverified until confirmed by an auditor or
        direct environment evidence."
      "Include `Current task state:` every round, with Completed, Incomplete, Blockers/Risks, and
        **Untrusted/Do not reuse**."
      types.py: `AuditReport.integrity_status: Literal["clean","suspect","violation"]`
      逐约束 verdict = "verified/unknown/violated/not_applicable"

WHAT_IT_DOES = 证据带**分级**，且有一类被显式标为"不可复用"。
WHAT_FAILURE_IT_PREVENTS = 可疑产物被下游当可信输入（污染扩散）。
IS_IT = execution harness behavior
OUR_LOCAL_ANALOGUE = `Tier A/B`（评审证据/执行证据）在 review-evidence 家族里的区分；
      R2 的"未扫描 != 干净"同构
OUR_LOCAL_EVIDENCE = 我们有"某个字段要标 NOT_OBSERVABLE"的纪律（H1 里执行得很好），
      但没有**多值**证据分级，也没有"不可复用"这个类别。
ADOPT_CONCEPT = EXPERIMENT
WHY = 二值（可信/不可信）比多值更简单；先验证"加一个 UNTRUSTED 桶"是否真的改变行为，
      不要一步到位上四值。
TARGET_LAYER = HARNESS_STATE_MACHINE
```

### M-04 — Failure Evidence Capture（失败证据进入下一轮）
```text
SOURCE = LongHorizon README + manager.py（VERIFIED_FROM_SOURCE）
原文 = "Plan → act → verify → checkpoint or recover ... feeds failure evidence into the next round."
      Manager 角色列 = "Rebuilds each round from the original goal, verified progress,
      **failure evidence**, and remaining work"
      超时行为 = "If a Manager, Executor, or Auditor reaches its local episode timeout, the run
      keeps the partial trajectory and recorded task state, then lets the next Manager round
      inspect the real workspace and recover."
      实现 = 运行时失败落 `harness_feedback.txt` + `agent_runtime_failed` 事件

WHAT_IT_DOES = 失败不是"重来"，而是一条**被持久化、被下一轮读取**的证据。
WHAT_FAILURE_IT_PREVENTS = 同一失败重复发生；失败原因丢失后重复踩坑。
IS_IT = execution harness behavior
OUR_LOCAL_ANALOGUE = references/engineering-memory.md 的 learning closure（M1–M9）；
      H1/H3 的 INVALID run 保留 + `[fact-check]` 标注
OUR_LOCAL_EVIDENCE = **我们有，而且做得比对方更严**：H1 的 2 个作废 run 被永久保留并写明归因
      （而不是删掉重来）。这是本地优点，不是缺口。
ADOPT_CONCEPT = YES（概念已具备，缺的是**读取侧**）
WHY = 我们记失败，但"下一轮是否真的读了失败证据"无从保证。
      对方把 failure evidence 放进**每轮 prompt 的固定输入**。
TARGET_LAYER = HARNESS_STATE_MACHINE
```

### M-05 — Bounded Next Step（下一小步，禁止捆绑）
```text
SOURCE = LongHorizon prompt_texts.py（VERIFIED_FROM_SOURCE）
原文 = "5. Never bundle multiple dominant state changes into one round."
      "Explicitly evaluate dependencies before routing a single dominant state change to a GUI or
      CLI executor."
      types.py: MAX_ROUNDS = 1000, DEFAULT_MAX_ROUNDS = 25, 每角色 EpisodeBudget

WHAT_IT_DOES = 每轮只推进**一个主导状态变化**，并给每轮硬预算。
WHAT_FAILURE_IT_PREVENTS = 一轮塞太多导致失败原因不可归因；无界执行。
IS_IT = execution harness behavior
OUR_LOCAL_ANALOGUE = 一票一分支一 worktree（R-V12-031）；Stage/barrier；
      references/ticket-lane 的票粒度纪律
OUR_LOCAL_EVIDENCE = H1 的对照/变体臂各自**主动扩大**了交付面（t03：10 文件 vs 9 文件），
      导致"发现集差异部分由造了什么决定" —— 这是"未绑定轮次边界"的可观测代价
ADOPT_CONCEPT = EXPERIMENT
WHY = 我们的"一票"是语义边界，不是**轮次预算**。加预算会改变 agent 行为，
      必须实验而非假定（也可能只是增加摩擦）。
TARGET_LAYER = HARNESS_STATE_MACHINE（H5 可选臂）
```

### M-06 — Fresh Execution Context / Fresh Episode（新上下文，而非续长）
```text
SOURCE = LongHorizon README + src/lh_harness/adapters/base.py + manager.py（VERIFIED_FROM_SOURCE）
原文 = "...executes it with a fresh context..."
      Executor 角色列 = "Starts with a fresh context and completes one clearly defined step..."
      实现 = 每角色一次 `AgentAdapter.run_episode(prompt, env, budget, live_trajectory_path)`
      src/lh_harness/manager.py 注释 = "The Manager prompt is rebuilt entirely from task + rounds + task state +
      contract, so **replaying the ledger restores the full planning context**."

WHAT_IT_DOES = 上下文是**每轮重建**的，可仅凭 ledger 重放恢复 —— 而不是把历史 append 下去。
WHAT_FAILURE_IT_PREVENTS = 上下文膨胀 / compaction 造成的目标衰退 / "context anxiety"。
IS_IT = execution harness behavior
OUR_LOCAL_ANALOGUE = §7.1 STATE_RESTORE/STATE_FLUSH；H1 的"fresh agent 需要什么"自问
OUR_LOCAL_EVIDENCE = H1 的三次 fresh review 都真实执行了"新 context"；
      但**没有一次是从持久化 ledger 重建的** —— 是新开一个空白会话 + 我口头给的 brief。
      即：我们用了 fresh context，但**没有用 replayable ledger**。
ADOPT_CONCEPT = YES
WHY = "fresh context + 可重放 ledger" 才能让 fresh episode **不依赖上一个 agent 的口述**。
      这是把 §7.1 从纪律变成机制的关键。
TARGET_LAYER = HARNESS_STATE_MACHINE（H5 核心）
```

### M-07 — Independent Verification As A Distinct Step（独立验证是独立步骤）
```text
SOURCE = LongHorizon README + src/lh_harness/role_prompts.py + manager.py（VERIFIED_FROM_SOURCE）
原文 = "🔍 Ground truth | Auditor | Independently inspects the actual files, interfaces, logs,
        and tests instead of trusting the Executor's claim."
      arXiv = "...a read-only auditor to verify the resulting environment state before the next round."
      auditor prompt = "**Executor text is only a claim.**" /
      "Harness prompts, trajectories, role outputs, and prior reports are run records, not task
      deliverables or standalone completion evidence."
      实现 = auditor 是**独立 episode**，有自己的 adapter 与 budget

WHAT_IT_DOES = 验证者与执行者**不是同一个 episode**，且验证者被明令"不得执行"。
WHAT_FAILURE_IT_PREVENTS = 自审替代独立评审（我们的 R4）。
IS_IT = governance invariant（R4 已是我们的 B 层不变量）
OUR_LOCAL_ANALOGUE = RULES R4 + AGENTS §6 L1（fresh context、独立 grounding、≥2 新反例）
OUR_LOCAL_EVIDENCE = 本仓做得**更严**（要求 ≥2 个非复制新反例；对方只要求独立）。缺口在
      **可核性**：R4 的满足程度目前靠评审记录自述，无机械断言"评审者 != 执行者"。
ADOPT_CONCEPT = YES（概念已有；取它的**可核性做法**）
WHY = 对方把"独立"落成**结构事实**（另一个 episode、另一个 adapter 调用），
      我们是**流程事实**（换个人/换个会话）。结构事实可机械核验。
TARGET_LAYER = MECHANICAL_GATE（身份断言）+ HARNESS_STATE_MACHINE
```

### M-08 — Checkpoint / Recovery（记账 + 恢复，而非"检查点对象"）
```text
SOURCE = LongHorizon README + manager.py（VERIFIED_FROM_SOURCE；**术语需澄清**）
原文 = 图节点 "Checkpoint<br/>verified progress"；边 "V -->|Fail| R[\"Record evidence<br/>and recover\"]"
      "The complete task state and audit trail make the agent's progress inspectable,
      **recoverable**, and reproducible."
      实现 = **append-only ledger**：`rounds.jsonl` / 每轮 `round.json` / `events.jsonl`；
      `resume` 路径重读 ledger；`_recorded_rounds()` 注释 =
      "Unreadable or malformed lines are skipped: a partially written tail must not prevent a resume."

⚠️ TERMINOLOGY HONESTY（研究者的原话，必须保留）：**代码里没有名为 checkpoint 的对象**。
   "checkpoint" 只出现在 README 叙述里；dashboard 里的 "checkpoint" 是**人工审批点**，不是持久化单元。
   真正的恢复机制 = 每轮 append-only 记账 + resume 容忍半写尾部。

WHAT_IT_DOES = 进度**可恢复**，且恢复路径对"最后一行可能只写了一半"有明确容忍。
WHAT_FAILURE_IT_PREVENTS = 崩溃后全部进度丢失；或坏尾行让整个 resume 失败。
IS_IT = execution harness behavior
OUR_LOCAL_ANALOGUE = `.agent/project-state.json`（唯一状态索引）+ STATE_RESTORE 序列
OUR_LOCAL_EVIDENCE = **我们在这里有一个真实的、代价已付的缺口**：H1 D9 ——
      run 产物落在 `/tmp`，被系统清理，8 个 worktree 全 prunable，diff **不可事后重放**。
      我们的"状态索引"是快照，对方的 ledger 是**追加流 + 可重放**。
ADOPT_CONCEPT = YES
WHY = 快照会丢中间过程（我们就丢了）；ledger 让她"replayable"。
      且"容忍半写尾部"是一条我们完全没有的**失败语义**。
TARGET_LAYER = HARNESS_STATE_MACHINE + MECHANICAL_GATE（产物持久化路径断言）
```

### M-09 — Role Separation as Implementation Boundaries（**不是**三个 agent）
```text
SOURCE = LongHorizon README + prompt_texts.py（VERIFIED_FROM_SOURCE）
原文 = **"One loop. Three focused responsibilities. The roles are implementation boundaries
        inside the loop, not three agents independently growing their own versions of the task."**
      MANAGER_INSTRUCTIONS = "Your only responsibilities are task decomposition and next-step
      scheduling. You must not execute the task, modify files, operate the GUI, or run commands
      to advance it."
      实现事实 = 实际角色槽多于三个：gui_executor / cli_executor / gui_auditor / cli_auditor /
      manager / final_response

WHAT_IT_DOES = 把职责切成**边界**，而不是强制进程拓扑。
WHAT_FAILURE_IT_PREVENTS = 每个 agent 各自长出一份自己的任务版本（state 分叉）。
IS_IT = **governance invariant 的候选**（我判它是）：`ROLE_SEPARATION != PROCESS_TOPOLOGY`
OUR_LOCAL_ANALOGUE = AGENTS §1 角色模型（5 角色，明确 own / 不得）
OUR_LOCAL_EVIDENCE = H1 的实际做法与它一致：**同一 runtime 里换 context** 实现"独立"，
      而不是起三个进程。且本仓 H3-B1 的"single-writer-per-repo"是同一原则的另一面。
ADOPT_CONCEPT = YES（**取"边界而非拓扑"这一表述，不取任何固定角色数**）
WHY = 这条**直接支持"不要复制固定 Agent 拓扑"**（PART 8）。它同时说明：
      角色数应该是**我们自己的风险模型**决定的，不是从外部抄的。
TARGET_LAYER = HOT（表述纪律）+ HARNESS_STATE_MACHINE（边界如何被强制）
```

### M-10 — AgentAdapter / Environment Abstraction（把 runtime 差异挡在外面）
```text
SOURCE = LongHorizon src/lh_harness/adapters/base.py + src/lh_harness/environment/base.py + README（VERIFIED_FROM_SOURCE）
原文 (README) = "A lightweight `AgentAdapter` preserves each agent's native execution loop while
      LongHorizon-Harness coordinates role boundaries, verified task state, and cross-round
      progress around it."
源码 (src/lh_harness/adapters/base.py) =
      "@runtime_checkable
       class AgentAdapter(Protocol):
           async def run_episode(self, prompt: str, env: Environment, budget: EpisodeBudget,
                                 live_trajectory_path: str | None = None) -> EpisodeResult: ..."
源码 (src/lh_harness/environment/base.py) =
      "class Environment(Protocol):
           async def exec(self, command: str, timeout: int = 30, tee_path: str | None = None) -> ExecResult: ...
           async def screenshot(self) -> bytes: ...
           async def upload(self, local_path: str, remote_path: str) -> None: ...
           async def download(self, remote_path: str, local_path: str) -> None: ..."
后端 = ClaudeCodeAdapter / CodexAdapter / OpenCodeAdapter / DeepSeekHarnessAdapter

WHAT_IT_DOES = 核心只依赖**极窄的协议**（一个 run_episode + 一个 exec/screenshot/upload/download），
      具体 runtime 的命令与习惯全在 adapter 里。
WHAT_FAILURE_IT_PREVENTS = runtime 细节渗进核心，使治理不可移植（我们的 R7）。
IS_IT = runtime adapter behavior（协议形状）+ governance invariant（分层原则）
OUR_LOCAL_ANALOGUE = R7 平台注入卫生 + adapters/{workbuddy,zcode}/ 的既有分层 +
      deployment/PORTABLE_SETUP.md 的能力矩阵
OUR_LOCAL_EVIDENCE = 我们**已经有正确的分层**，但能力声明面比对方宽：
      `CAN_BIND_WORKDIR / CAN_READ_AUTHORITY / CAN_RUN_TESTS / CAN_INSPECT_ENVIRONMENT /
      CAN_REQUEST_REVIEW / CAN_PERSIST_STATE / CAN_SPAWN_FRESH_EPISODE`（模式要求，本轮登记）
ADOPT_CONCEPT = YES（取"协议极窄"这一纪律；不取它的具体方法名）
WHY = 我们的能力矩阵描述的是**能力**，对方的协议是**最小调用面**。
      最小调用面更容易写出正控（"没有这个能力时会发生什么"）。
TARGET_LAYER = RUNTIME_ADAPTER
```

### M-11 — Event / Trajectory Persistence（事件流 + 轨迹）
```text
SOURCE = LongHorizon README + src/lh_harness/manager.py + trajectory_artifacts.py（VERIFIED_FROM_SOURCE）
原文 (README 运行记录表) = "🧾 Event stream | What happened throughout the run" /
      "🧠 Role trajectories | Manager, Executor, and Auditor inputs and outputs"
      实现 = `events.jsonl`（含 schema_version / event_id / ts）；`rounds.jsonl`；
      每角色 `<role>_raw_trajectory.jsonl`；src/lh_harness/trajectory_artifacts.py 把截图物化成
      **provider-neutral** 的 trajectory + manifest

WHAT_IT_DOES = 全过程留痕，且物化层与 provider 解耦。
WHAT_FAILURE_IT_PREVENTS = "后来没人知道发生了什么"；证据只在对话里（我们的"零持久化"失败类）。
IS_IT = execution harness behavior
OUR_LOCAL_ANALOGUE = 评审证据 schema（schemas/review-evidence.schema.json）+
      `scripts/review_evidence.py`（1653 行）+ H1 的 run registry
OUR_LOCAL_EVIDENCE = 本仓本轮**刚因为这条吃过亏**：H1 的评审证据一度只存在于对话中，
      事后才补成 PR 评论（"只存在于对话窗口 = 零持久化"是用户已立的红线）
ADOPT_CONCEPT = YES
WHY = 我们有 schema 与 CLI，但**没有事件流**：状态转移不是 append-only 的，
      所以"为什么变成现在这样"无法重放。这正好补 M-08 的缺口。
TARGET_LAYER = HARNESS_STATE_MACHINE
```

### M-12 — Completion Semantics（完成是 harness 级判定）
```text
SOURCE = LongHorizon src/lh_harness/prompt_texts.py + manager.py（VERIFIED_FROM_SOURCE）
原文 (src/lh_harness/prompt_texts.py) = "6. Output completion only when an auditor's first three control lines are
      `Status: complete`, `Integrity: clean`, and `Contract audit: aligned`, and its report
      supports every original requirement."
      实现 = `_latest_auditor_is_clean_complete()` 只在
      report.status=="complete" AND integrity_status=="clean" AND contract_audit_status=="aligned" 时返回 True
      代码注释 = **"Final status is a harness-level decision, not the last executor agent's self claim."**
      零信任守卫 = `_invalid_completion_feedback()`：Manager 若无干净审计报告就说 done →
      该完成被**拒绝**，并回灌一份合成修复报告
      FINAL_STATE_SEMANTIC_GUARD = "completion must exist in the state actually consumed by the
      user, target application, or downstream process... A natural-language claim, progress
      screenshot, temporary log, or handwritten substitute cannot replace it."

WHAT_IT_DOES = "完成"由**机器检查一个结构化谓词**决定，且执行者的自述被显式降级为 claim。
WHAT_FAILURE_IT_PREVENTS = **false closure**（我们的 "agent says CLOSED before evidence closure"）。
IS_IT = governance invariant（完成语义）+ execution harness behavior（实现）
OUR_LOCAL_ANALOGUE = AGENTS §7 STOP 枚举里的 MILESTONE_COMPLETE；
      R3 的"完成声明须有可复现证据"；H1 的 `VALID_COMPLETION` 三层区分
OUR_LOCAL_EVIDENCE = H1 的**三层区分**（EXECUTION_COMPLETED / VALID_COMPLETION / QUALITY_RESULT）
      方向完全一致，但它是**实验里的记录约定**，不是 runtime 的转移条件。
      且 H1 里 worker 自报 NO、编排者复跑后改 YES —— 说明"谁有权宣布完成"没有机械答案。
ADOPT_CONCEPT = YES
WHY = 这是把 R3 落成状态机的**转移条件**。对方的零信任守卫（说 done 就回灌修复报告）
      是一个可直接实验的具体形状。
TARGET_LAYER = HARNESS_STATE_MACHINE（H5 核心）
```

---

## 2. Anthropic 的独立佐证（三条与上述机制**独立收敛**）

```text
A-01 — Context RESET vs COMPACTION（独立佐证 M-06）
SOURCE = anthropic.com/engineering/harness-design-long-running-apps（2026-03-24，VERIFIED_FROM_SOURCE）
原文 = "Context resets—clearing the context window entirely and starting a fresh agent, combined
        with a structured handoff that carries the previous agent's state and the next steps—
        addresses both these issues. This differs from compaction, where earlier parts of the
        conversation are summarized in place so the same agent can keep going on a shortened
        history. While compaction preserves continuity, it doesn't give the agent a clean slate,
        which means context anxiety can still persist. A reset provides a clean slate, **at the
        cost of the handoff artifact having enough state for the next agent to pick up the work
        cleanly**."
      另一句 = "...decomposing the build into tractable chunks, and using structured artifacts to
        hand off context between sessions."
意义 = 独立来源把"fresh episode"的关键**代价**点出来了：handoff artifact 必须**足够**。
      这正是我们的 §7.1 STATE_FLUSH 想做的事，但我们的 artifact（MEMORY 指针 / 项目状态索引）
      没有被验证过"够不够"。
ADOPT_CONCEPT = YES → 直接支撑 H5 的对照设计（reset + handoff vs 长 context + memory）
```

```text
A-02 — 独立评估者（独立佐证 M-07）
SOURCE = 同上（VERIFIED_FROM_SOURCE）
原文 = "When asked to evaluate work they've produced, agents tend to respond by confidently
        praising the work... **Separating the agent doing the work from the agent judging it
        proves to be a strong lever** to address this issue."
      架构 = "a three-agent architecture—planner, generator, and evaluator"
意义 = 与 M-07 独立收敛。注意 Anthropic 的表述是"three-agent"，而 LongHorizon 明确说
      "不是三个 agent、是实现边界" —— **两者对同一原则给了不同拓扑**，恰好证明
      `ROLE_SEPARATION != PROCESS_TOPOLOGY`（PART 8）。我们取**职责**，不取三进程。
```

```text
A-03 — 一个与我们完全同型的失败模式（独立佐证 M-12）
SOURCE = anthropic.com/engineering/effective-harnesses-for-long-running-agents（2025-11-26）
原文 = "After some features had already been built, **a later agent instance would look around,
        see that progress had been made, and declare the job done.**"
      对策 = "...an initializer agent that sets up the environment on the first run, and a coding
        agent that is tasked with making incremental progress in every session, while **leaving
        clear artifacts for the next session**."
      另一句 = "The key insight here was finding a way for agents to quickly understand the state
        of work when starting with a fresh context window, which is accomplished with the
        claude-progress.txt file alongside the git history."
意义 = 这句话描述的就是我们的 "false closure"：新 agent 看到有进度就宣布完成。
      它也给出最便宜的对策形状（progress 文件 + git 历史作为可读状态）。
ADOPT_CONCEPT = YES（作为 H5 的失败判据之一）
```

---

## 3. OpenAI 材料（SECONDARY_MENTION ⚠️ —— 不支撑任何判定）

```text
检索状态 = 直连 openai.com 失败（challenge/stub 页）。以下引文来自搜索引擎渲染副本与第三方镜像，
           标注为 SECONDARY_MENTION，**不用于支撑 ADOPT_CONCEPT**。

（搜索副本，attributed to openai.com/index/harness-engineering）
  "Over the past five months, our team has been running an experiment: building and shipping an
   internal beta of a software product with 0 lines of manually-written code."
  "Humans steer. Agents execute."
  "we instruct Codex to review its own changes locally, request additional specific agent reviews
   both locally and in the cloud, respond to any human or agent given feedback, and iterate in a
   loop until all agent reviewers are satisfied."

（第三方镜像 wayintoai.com —— 二手）
  "We regularly see single Codex runs work on a single task for upwards of six hours (often while
   the humans are sleeping)."
  "Context is a scarce resource. A giant instruction file crowds out the task, the code, and the
   relevant docs—so the agent either misses key constraints or starts optimizing for the wrong ones."
  "Execution plans — checked into the repo as first-class artifacts with progress and decision logs."

用途（仅此而已）：
  · "Context is a scarce resource / a giant instruction file crowds out the task"
    —— **方向性佐证** V1.2 的前提假设（与 H1 的 59.6% 缩减方向一致）；
  · "Execution plans checked into the repo as first-class artifacts"
    —— 与 M-11（事件/轨迹持久化）方向一致。
NOTE = 上述任何一条**都不得**进入 canonical，也不得单独支撑某个机制。
       若未来要采用，先补一手检索（E1 升级为 VERIFIED_FROM_SOURCE）。
```

---

## 4. 明确拒绝的部分（防 cargo-culting）

```text
REJECT-01 固定三角色进程拓扑（Manager / Executor / Auditor 三进程）
  理由 = LongHorizon 自己说 "not three agents"；Anthropic 说 "three-agent" —— 两个来源
        对同一原则给出**不同拓扑**。拓扑不是不变式。我们取职责边界，取自己的运行时形状。
  抽象 = ROLE_SEPARATION != PROCESS_TOPOLOGY

REJECT-02 桌面/GUI computer-use 相关机制（screenshot / upload / download 作为核心协议）
  理由 = 我们的受治理对象是**代码仓**，不是桌面应用。把 screenshot 搬进 Core 是把
        某类任务的实现细节当普适能力。
  例外 = 概念上"Environment 是窄协议"这一点被采纳（M-10），但协议内容按我们的领域定义。

REJECT-03 直接采用其 rounds.jsonl 文件格式或字段名
  理由 = 实现细节。我们采纳的是"append-only + 可重放 + 容忍半写尾部"这三条**语义**。

REJECT-04 MAX_ROUNDS = 1000 / DEFAULT 25 之类的具体数值
  理由 = 数值是它的工作负载与预算的函数。直接抄会把别人的成本模型变成我们的规则
        （R8 最小复杂性护栏 + RUNTIME_FACT != GOVERNANCE_INVARIANT）。

REJECT-05 引入常驻 daemon / 数据库 / 服务
  理由 = 本轮明确禁止（PART 20）。且 append-only 文本文件已足以表达我们需要的 ledger 语义。

REJECT-06 把 "clean / suspect / violation" 三值直接搬成我们的证据分级
  理由 = 我们的证据面已经有两套分级（Tier A/B 与 NOT_OBSERVABLE），再叠一层是复杂度增加。
        先实验二值加一个 UNTRUSTED 桶（M-03），有证据再扩。

REJECT-07 Anthropic 的 "three-agent" 表述本身
  理由 = 同上 REJECT-01。我们引用的是它关于**独立评估价值**的结论，不是它的拓扑建议。
```

---

## 5. 汇总

```text
LONGHORIZON_MECHANISMS_REVIEWED = 12（M-01..M-12）
ANTHROPIC_CORROBORATIONS          = 3（A-01..A-03）
OPENAI_SECONDARY                  = 1（不支撑判定）

ADOPT_CONCEPT = YES         → M-02, M-04, M-06, M-07, M-09, M-10, M-11, M-12   (8)
ADOPT_CONCEPT = EXPERIMENT  → M-01, M-03, M-05                                 (3)
ADOPT_CONCEPT = NO          → (无机制被整体拒绝；拒绝的是**实现形态**，见 §4 REJECT-01..07)

EXPERIMENT_REQUIRED = 3（M-01 / M-03 / M-05 —— 这三条是"加机制会改变 agent 行为、可能只是加摩擦"，
      必须先实验；其余 8 条是**语义澄清或已有方向的确证**，可通过 H5 协议一并验证）

最高价值的三条（若只能取三条）：
  M-12 completion semantics（完成 = harness 级判定，非执行者自述）
  M-02 verified state（状态转移需要独立验证准入）
  M-06 fresh episode + 可重放 ledger（fresh context 我们已经会用；缺的是"不靠口述"）
```

> **范围声明**：本文件的全部外部内容为 **E1**。它们**不**构成 canonical rule，
> 也**不**授权任何实现。要进入 canonical 必须：本地复现（E3）→ 独立评审 → PR。
