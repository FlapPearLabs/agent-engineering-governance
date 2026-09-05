# REF: Project State Persistence — 跨 Agent 状态持久化与恢复

> Canonical owner: AGENTS.md（STATE_RESTORE / STATE_FLUSH 节）。本文件定义状态分类、持久化位置与恢复协议。
> 两条产品原则：**`PROJECT_STATE_MUST_OUTLIVE_THE_AGENT`**；**`CONVERSATION_MEMORY_IS_CACHE, NOT_PROJECT_STORAGE`**。
> 运行时中立：适用于 WorkBuddy / ZCode / OpenCode / Codex / Hermes / 未来 Agent——各 runtime 机制可不同，持久化语义相同。

## 1. 状态五分类

| 类 | 内容 | 默认归属 | 持久化要求 |
|---|---|---|---|
| **P0 EPHEMERAL SCRATCH** | 临时假设、被丢弃的路径、探索命令、低价值中间推理、已失效观察 | `LOCAL_ONLY / MAY_DISAPPEAR` | 不入 Git/文档/Issue——不要用每个想法污染远端 |
| **P1 ACTIVE EXECUTION STATE** | 当前票状态、Stage、branch/worktree、base SHA、exact HEAD、owner、评审状态、repair 轮次、CI 状态、blockers、next legal action、集成状态 | **GitHub Issue / PR / tracker**（Git 本身提供 branch/SHA 真相） | **绝不允许只存在于聊天里**；在有意义转换点更新（见 §3） |
| **P2 DURABLE PROJECT KNOWLEDGE** | 项目目标、已接受架构、重要设计决策、合同、自然缝、长期实现决策、其拒绝有长期后果的备选架构、集成规则、状态所有权、持久化语义、身份/provenance 语义、重要失败语义 | 仓内 durable 工件：TARGET / SPEC / ADR / SPIKE / 架构文档 / 合同文档 / project map | 遵循目标仓既有约定；仓无约定时可提最小约定（`docs/target|specs|adr|spikes/`），**最终布局由仓本地权威（C 层）决定** |
| **P3 DEFECT / LEARNING STATE** | 重要 bug 与工程发现 | 按价值比例持久化：**优先 `BUG KNOWLEDGE → REGRESSION TEST`**；辅以 Issue / fixture / ADR（架构相关）/ SPIKE（不确定性调查）/ commit-PR 说明 | 触发条件：可能复发、行为重要、跨模块、难重新发现、架构相关、安全/状态/身份相关、构成有用回归边界。**typo 不建永久 Issue** |
| **P4 ENVIRONMENT / MACHINE STATE** | 所需 runtime、工具版本、MCP 意图、CodeGraph 能力、平台限制、构建前提、shell/平台假设、部署要求 | 双轨：**`LOCAL_FULL_FIDELITY + REMOTE_SANITIZED_RECOVERY`** | 本机存全量保真配置；Git 只存安全恢复信息（所需能力、相关工具/版本、canonical 获取方法、验证命令、占位符、平台注意）。**绝不提交**：凭据/token/cookie/私密身份/RULES R2 禁止的私有文件系统事实/含密原始配置 |

## 2. GitHub = 活跃执行控制平面（P1）

项目连接 GitHub 时，live Ticket/Lane 状态持久化到 GitHub。一张票应允许 fresh Agent 重构至少：

```text
TICKET = STATUS = STAGE = OWNER = SEAM =
BASE_SHA = BRANCH = HEAD_SHA =
IMPLEMENTATION = TEST = REVIEW = REPAIR_ROUND =
CI = INTEGRATION =
BLOCKERS = DECISIONS_REQUIRED = NEXT_LEGAL_ACTION =
```

- 不相关字段不要求填写；**不造官僚模板**。目标是 fresh Agent 看 Issue/PR 即可回答：我们在哪？什么已被证明？下一步合法动作是什么？
- **更新发生在有意义转换点**，不是每条命令：START_GATE 授予 / 实现开始 / 实现完成 / 评审完成 / repair 改变 exact SHA / CI 已分类 / 发现 blocker / 需要 product 决策 / 集成接受 / merged / remote verified / 票关闭。
- 活跃票状态主要属于 GitHub 时，**不得**为对称性制造本地重复权威副本：Git 承载本地实现状态，GitHub 承载远端工作流状态，仓文档承载 durable 项目真相——各归其位，避免双权威漂移。

## 3. 仓文档 = 长期项目知识（P2/P3 的家）

GitHub Issues 不替代架构/规格工件。角色分工不混用：

| 工件 | 承载 |
|---|---|
| TARGET | 项目要达成什么、成功定义、重要边界、长期方向 |
| SPEC | 已批准行为、外部有意义合同、规范要求 |
| ADR | 架构决策、重要备选、为何选它、后果 |
| SPIKE | 未解决的技术不确定性、实验、测量、可行性证据、决策建议 |
| TEST / FIXTURE | 可执行行为知识、绝不能复发的 bug、稳定反例 |
| ISSUE / PR | 执行状态、所有权、进行中工作、评审/CI/集成进度 |

## 4. 写入顺序（持久化的自然管线）

```text
DISCOVER / DECIDE → 写入正确的本地项目工件 → TEST / VALIDATE
→ COMMIT → PUSH → 更新 ISSUE / PR / TRACKER → REMOTE VERIFY
```

## 5. STATE_RESTORE — 每个 fresh Agent 进入既有项目时

**禁止以"请人讲一遍项目历史"开局。** 默认序列：

```text
1 加载当前工程治理（governance bootstrap）
2 fetch 目标仓 remote
3 核验当前 branch / default branch
4 读仓本地权威（AGENTS/RULES/Specs）
5 读 TARGET / SPEC / ADR / SPIKE / 架构文档
6 检视 open Issues
7 检视 open PRs
8 检视当前 Stage/Ticket tracker
9 检视 exact remote branch SHAs
10 检视 CI / 评审状态
11 重构合法 frontier
12 识别未决 product decisions
13 输出简洁 recovery receipt
14 授权已明确 → 自动继续
```

Recovery receipt：

```text
PROJECT =
REMOTE_DEFAULT_SHA =
TARGET = SPEC = ADR = SPIKES =
ACTIVE_STAGE = ACTIVE_TICKETS = ACTIVE_PRS =
BLOCKERS = DECISIONS_REQUIRED =
CURRENT_LEGAL_FRONTIER =
STATE_RECOVERY = COMPLETE / PARTIAL / BLOCKED
READY_TO_CONTINUE = YES / NO
```

GitHub/仓内证据足够时，**不要求用户复述历史**。

## 6. STATE_FLUSH — 每个 Agent 离开前

在以下时点执行持久化检查：结束有意义工作会话 / 切换 Agent/runtime/模型工作区 / 交接 / 到达 STOP / 到达 milestone / 完成票 / 集成 / context 耗尽 / 有意放弃 lane。

核心问句：**`WHAT DOES THE NEXT FRESH AGENT NEED THAT CURRENTLY EXISTS ONLY IN MY CONTEXT?`** —— 只持久化有价值的答案。

```text
STATE_FLUSH = PASS / PARTIAL
LOCAL_HEAD = REMOTE_HEAD =
TICKET_STATE_SYNCED = PR_STATE_SYNCED =
DURABLE_DOCS_UPDATED = REGRESSION_KNOWLEDGE_PERSISTED = ENVIRONMENT_DELTA_PERSISTED =
UNPUSHED_STATE = UNPERSISTED_IMPORTANT_CONTEXT =
NEXT_LEGAL_ACTION =
```

检查单：Code（有意义变更已 commit？exact HEAD 已记录？授权的 remote 工作已 push？）；Ticket（状态/blocker/评审/CI/下一步是否 current）；Durable decisions（新长期决策 → TARGET/SPEC/ADR/SPIKE/架构/ref/test）；Bugs（已修 → 优先回归测试；未决 → Issue/票证据）；Environment（新依赖/限制 → 本机全量 + 远端 sanitized 恢复信息）；Memory（对话记忆获得跨会话事实 → 晋升到正确 canonical 工件，**不留重要真相困在 MEMORY**）。

常规期望 `UNPERSISTED_IMPORTANT_CONTEXT = NONE`；非 NONE 时（除非不安全/未授权）先持久化再终止。

## 7. GitHub 失败 / 离线模式

远端不可用不得摧毁工作：本地持久化 → 适当 commit → 记录 `REMOTE_STATE_SYNC = DEFERRED` → 记录未同步状态 → **不声称远端已持久化** → GitHub 恢复后第一动作 = 同步 + remote verify。

```text
LOCAL_STATE = DURABLE
REMOTE_STATE = DEFERRED
UNSYNCED_COMMITS = ... UNSYNCED_TICKET_UPDATE = ...
```

**`REMOTE_UNKNOWN != REMOTE_SYNCED`**。

## 8. 反官僚（PERSISTENCE_VALUE 原则）

不做：逐命令日志、巨型日报、琐事强制 ADR、琐事 bug 强制 Issue、本地/远端重复 tracker、把聊天记录拷进 Git、把 raw MEMORY 倾倒进仓。

判据：**`PERSISTENCE_VALUE`** —— "fresh Agent 缺了这条信息会做出实质更差的决策吗？" 否 → 不为仪式持久化；是 → 持久化到正确 canonical 位置，且始终有唯一可识别的 canonical owner（不做五处竞争副本）。

## 9. 记忆路由（与 MEMORY_IS_DISCOVERY_NOT_AUTHORITY 同步）

```text
临时想法 → 可保持 ephemeral（P0）
当前票状态 → GitHub Issue / PR / tracker（P1）
长期项目决策 → TARGET / SPEC / ADR / 架构（P2）
技术不确定性/结果 → SPIKE（P2）
重要缺陷 → TEST + Issue/PR（P3）
环境要求 → 本机环境 + sanitized 远端 profile（P4）
跨项目工程经验 → agent-engineering-governance 仓
用户/runtime 便利记忆 → MEMORY（F 层，导航用）
```
