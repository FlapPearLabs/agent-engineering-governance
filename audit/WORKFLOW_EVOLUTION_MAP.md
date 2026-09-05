# WORKFLOW_EVOLUTION_MAP — 工作流演化重建

> 原则：不为任何规则建立治理，除非理解它因哪次真实失败而生。
> 证据源：`~/.workbuddy/MEMORY.md` 全文（319 行）、zhihu-grabber-toolkit 仓内 `AGENTS.md`（846 行，含 2026-08-09 重建/2026-08-23 归一化/2026-08-30 压缩合同三个时间戳）、`RULES.md`、git 历史（work/p1-t07…t10 分支与 repair 链）、用户工程记忆。

## 世代划分

### GENERATION 1 — 连续票据执行 + 独立评审 + 串行集成（≈2026-08 初）

- 形态：`AGENTS.md`（zhihu 仓）2026-08-09 由历史任务契约重建；GitHub Tracker/Issues 为 durable ledger；fresh Agent 仅凭 repo + GitHub state 恢复现场。
- 起源痛点：执行状态活在聊天窗口/agent 私有记忆里，会话即失忆；人工搬运 prompt。
- 修好什么：repo truth > conversation memory；单分支单写者；ff-only 串行 master。
- 引入的新失败模式：流程文本膨胀（846 行）；每个仓重复手写一套；票据串行过严导致吞吐低。
- 现状：KEEP（作为项目层执行架构的雏形），语义已被 G3/G4 吸收升级。

### GENERATION 2 — Matt Pocock 技能驱动实现（2026-08 中）

- 形态：`grill-with-docs → to-spec → to-tickets → implement → tdd → code-review → simplify` 全链路技能；`/implement` 为强制工程入口（zhihu AGENTS.md §18.1）。
- 起源痛点：agent 边实现边发明架构；验收合同缺失；测试是马后粉饰。
- 修好什么：把"怎么干活"从即兴变成可复用方法；skill 责任边界成文（§18.1/18.8：`/implement`≠架构重开、`/simplify` 不得改行为、skill 使用需证据）。
- 引入的新失败模式：技能链仪式化（低风险票也要全套）；skill 被当作权威来源（方法≠权威）；多套同职责 skill 并存引起路由混乱。
- 现状：KEEP + MODIFY（保留技能族，增加全局路由表与 SKILL_IS_NOT_AUTHORITY 边界）。

### GENERATION 3 — Ticket Lane V2（2026-09 初，写入全局 MEMORY）

- 形态：AUTHORITY CHECK → EXACT-SHA GROUNDING → CONTRACT EXTRACTION → COUNTEREXAMPLE-FIRST TDD → IMPLEMENT → GREEN → FRESH REVIEW → THIRD-PARTY ADVERSARIAL → PR CI → POST-CI REVIEW → EXACT-SHA MERGE。
- 起源痛点：worker 自证（self-certify）；合同靠猜；报告漂亮但语义错；CI_NOT_TRIGGERED 被当 PASS；stale 评审被转移。
- 修好什么：exact-SHA 绑定、counterexample 门槛、独立评审 quorum、CI 诚实性枚举、CodeGraph grounding 义务。
- 引入的新失败模式：
  - **全员 T09 化**——每票都跑最大流水线，成本与风险不匹配；
  - **CodeGraph 全量重建仪式**——每个 worker/reviewer 重建图库；
  - **评审膨胀→无限修复循环**（小 finding → repair → 更小 finding → …）；
  - 规则全部塞进 MEMORY.md 尾部 → 注入截断，实际可见性崩塌。
- 现状：MODIFY（原则全保留，强度改为风险分级 + 饱和收敛）。

### GENERATION 4 / CURRENT TARGET — 多代理阶段架构（本审计目标）

- 形态：Parent Orchestrator（thin control plane）→ Execution Stage（风险分级的票据编组）→ 隔离 Ticket Lane（worker 直接实现）→ 分级评审 → repair saturation → 串行集成 → auto-advance。
- 起源痛点：G3 的过严与仪式成本超过工程风险；人工在票间搬运成为瓶颈；CodeGraph 重建浪费；报告冗长无信息量。
- 修好什么：SEAM-FIRST 分解、Stage 屏障减少人工交接、L0/L1/L2 评审分级、repair budget=2 + Convergence Arbiter、canonical graph + delta、novelty-first 报告。
- 潜在新失败模式（候选治理必须预埋防御）：Stage 编组错误导致并行冲突；饱和判定被滥用为提前放行；canonical graph 失同步后 delta 评审建立在陈旧图上。
- 现状：TO-BE（本仓库候选治理的目标态）。

## 主要规则演化账本

| RULE | ORIGINATING_PAIN | WHAT_IT_FIXED | NEW_FAILURE_MODE_INTRODUCED | CURRENT_STATUS |
|---|---|---|---|---|
| exact-SHA PASS 绑定 | 评审 PASS 被转移到"看起来等价"的新 commit | 修复后旧 PASS 一律作废 | 修复任意字节即触发全链重审 → 仪式化 | KEEP（配 delta 评审减负） |
| 禁 amend/rebase/force-push，append-only repair | reviewed 历史被改写、评审失锚 | 评审身份永远可机械核验 | 无显著 | KEEP |
| ff-only + master 串行集成 | 并行 push 互相覆盖 | master 历史线性可审计 | 无显著 | KEEP |
| 单分支单活跃写者 | 双会话并发写同分支 | 写权唯一化 | 无显著 | KEEP |
| SELF_REVIEW != INDEPENDENT_REVIEW | worker 自证通过 | 独立评审 gate 不可取消 | 评审数量膨胀 | KEEP |
| CodeGraph grounding 义务 | worker 不懂跨模块所有权就动手 | 结构问题强制查图 | 每票/每评审全量重建仪式 | MODIFY → canonical graph + delta |
| CONTRACT EXTRACTION 全字段表 | 实现者静默填补合同空白 | 合同先于实现成文 | 字段清单过长变成填表仪式 | MODIFY → 风险分级裁剪 |
| COUNTEREXAMPLE-FIRST TDD | "tests were added"冒充 TDD；RED 只是 MODULE_NOT_FOUND | RED/GREEN 证据 + 反例类目 | 反例数量军备竞赛 | MODIFY → 高价值类目优先 |
| REAL PR CI + CI 状态枚举 | LOCAL_TESTS 冒充 CI；NOT_TRIGGERED=PASS | 状态不可坍缩；worker 分类仅 PROPOSAL_ONLY | 手工核验重复劳动 | KEEP（L0 harness 承接） |
| THIRD-PARTY ADVERSARIAL REVIEW 固定 ChatGPT | —（旧规则） | — | 强模型浪费在低风险票；人工搬运 | REMOVE（已被 Override 取代：角色化 + 风险触发） |
| "WorkBuddy 禁写生产代码，全部经 Codex CLI" | 早期失控防御 | — | handoff 文档搬运负担 | REMOVE（已被 Override 取代：隔离 worker 直接实现） |
| REPAIR_BUDGET=2 + Convergence Arbiter | 无限防御性修复循环 | 修复授权价值化 | 可能被滥用为提前放行 → 需高价值 blocker 语义兜底 | KEEP（G4 核心） |
| NOVELTY-FIRST 报告 | 报告奖励流水账 | 先讲新知；PASS_ONLY 才可压缩 CI | 可能抑制必要证据 → 非 PASS 强制展开已内置 | KEEP |
| 模型按风险路由 | 强模型滥用/弱模型错配 | 语义风险集中强模型 | 名单不可核验、无执行面 | MODIFY → 映射到实际可用档位 |
| Continuous Goal Mode（项目级） | 每步问"是否继续" | 合法授权内自主推进 | 越权风险 → 七类 STOP 状态兜底 | KEEP + 全局化 |
| `captured != verified`（zhihu 专项） | 抓取成功冒充验证通过 | 验证权威唯一化 | — | PROJECT_ONLY（全局只留抽象：SUCCESSFUL_PRODUCTION != VERIFIED） |
| capability isolation 语义 | prompt 禁令冒充硬隔离 | 运行时证据才能解锁 | — | PROJECT_ONLY（抽象保留：prompt-only guard ≠ isolation） |
| Windows/PowerShell 移植政策 | 旧环境编码/路径问题 | — | 在 macOS 上成为误移植风险 | REMOVE from global（归档为 STALE_FOR_CURRENT_WORKBUDDY；活跃面 grep 实测 0 残留） |
| handoff doc 强制 | 跨工具/跨人传递 | — | 每票手工搬运 | MODIFY → 默认直接 dispatch，仅跨工具/中断/审计场景使用 |
