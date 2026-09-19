# BOOTSTRAP_CONTRACT — 治理如何被新会话真实看到（F2 修复）

> 状态：**CANONICAL（V1.1.1）**。本文回答一个工程问题：**fresh WorkBuddy 工程会话如何保证在开工前看到 canonical 治理**。
> 原则：只使用**已验证存在**的机制；不建框架；不假装自动加载。
>
> **验证状态（证据诚实拆分，R2 修复）**：
> - `BOOTSTRAP_STATIC_VALIDATION = PASS` —— 指针预算断言（`WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES = 3500` UTF-8 bytes vs 实测截断点 byte 4028，见 §2.1）通过；BOOTSTRAP_CHECKLIST B1–B5 成文；`scripts/validate_governance.py` 全部检查 PASS（以运行时输出为准）；GitHub Actions governance-ci 已接入且 green。
> - `BOOTSTRAP_LIVE_VALIDATION = NOT_RUN` —— fresh neutral-session 验收（§3 协议）只能在受控部署（§2.1 前置条件满足）后执行；在部署完成前**不得**声称 runtime 验证通过，任何报告引用本合同时必须使用上述拆分字段。

## 1. 已验证的注入事实（2026-09-05 实测）

| 通道 | 自动加载？ | 证据 |
|---|---|---|
| `~/.workbuddy/MEMORY.md`（作为 `<user_memory>` 注入） | **是，但头部 ~4K 截断（实测 byte 4028）** | 本会话注入副本中途断句 + grep -b 定位 |
| `~/.workbuddy/{SOUL,IDENTITY,USER,BOOTSTRAP}.md` | 是（全文） | 同会话观测 |
| 项目/工作区根的 `AGENTS.md` / `RULES.md` | **未证实**（无自动加载证据） | 无任何注入观测 |
| 治理仓文件 | 否 | 需 agent 主动读取 |

**结论（显式声明）**：WorkBuddy 当前**不能**保证自动加载项目 AGENTS/RULES；唯一可靠的自动通道是 MEMORY.md 头部。因此 bootstrap = 自动指针 + 显式清单步骤。

## 2. Bootstrap 机制（三件套）

### 2.1 MEMORY 指针（自动可见层）

- `deployment/MEMORY_POINTER_CANDIDATE.md` = 替换 `~/.workbuddy/MEMORY.md` 的候选全文，受下方**冻结的字节预算合同**约束（单位 = UTF-8 编码字节，不是字符数）。
- 内容 = 治理仓指针 + 读取清单 + 4 条 B 层不变量摘要（即使后续加载全部失败，这 4 条也已随注入可见）。
- **部署 = 把候选内容写入 `~/.workbuddy/MEMORY.md`**（一次性、可回滚：旧 MEMORY 原始备份 **local-only（Git 之外）**；治理仓 `deployment/archive/` 只收 **sanitized/redacted 迁移快照**——raw 归档默认不进 Git，提交前过 R2 第一层扫描 + redaction，命中即阻止）。旧 MEMORY 全部语义已迁移至本仓 canonical 文件，无信息丢失。
- 部署前置条件（V1 定稿版）：治理核心已通过（`GOVERNANCE_CORE = PASS`）+ skills 获取指南按 V1 政策就绪（`skills/README.md`，SOURCE=UNKNOWN 不阻塞）+ product owner 对 live 部署的**显式授权**。本次 V1 finalization 不执行 live 部署。

**冻结的预算合同（本节是本合同的唯一语义 owner：预算值、单位、profile 区分、override 语义与观测截断点区分只在此处声明；其他 surface 只引用不重述）**：

```text
NAME     WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES
VALUE    3500
UNIT     UTF-8 编码字节数（byte）—— 不是字符数（char），不是 code point 数
SOURCE   WorkBuddy profile 安全预算（观测/profile 属性，不是规范常数；观测事实见 §1）
SCOPE    仅在本 WorkBuddy profile 内有效；不是跨 runtime 通用常数
OWNER    本节（deployment/BOOTSTRAP_CONTRACT.md）；scripts/validate_governance.py 只消费该值
```

**两个必须区分的量（不得互为定义）**：

```text
3500 bytes = 当前 WorkBuddy profile 的安全预算（BUDGET；主动留出的规范余量）
4028 bytes = 历史观测到的实际注入截断点（TRUNCATION；被动观测边界，见 §1 实测事实）
```

`3500` 不是由 `4028` 推导出来的量，也不是「截断点减去某个隐含安全余量」的结果；两者性质不同：前者是主动的规范预算，后者是被动的观测边界。取 3500 只是为了不贴近该观测边界。

**OVERRIDE / PROFILE 语义**：

```text
- 3500 是本 profile（WorkBuddy）的预算，不是跨 runtime 的普适常数。
- 非默认 profile 若使用其自有预算，必须先有该 profile 自身的已核验观测，并
  **显式记录 OVERRIDE（值 + 来源 + 观测依据）**；静默替换预算值 = 违规。
- 无已核验 profile 时回落 3500（本 profile 值），并标注来源。
```

**单位一致性**：`scripts/validate_governance.py` 对指针正文的**授权测量**必须是 UTF-8 编码字节长度（`len(body.encode("utf-8"))`），不得使用字符长度；`AGENTS.md` §10 只作本篇的指针，不重述预算值。

### 2.2 会话开工清单（agent 执行，每工程会话一次）

```text
BOOTSTRAP_CHECKLIST（工程任务开工前执行）:
B1 读 MEMORY 注入中的治理指针（不存在 → 按治理仓 URL 直接读取并报告缺失）
B2 读治理仓：AGENTS.md + RULES.md + 相关 references（按指针清单）
B3 发现仓内权威：repo 根 AGENTS.md / RULES.md / docs/specs → 读存在者
B4 应用 AUTHORITY_MAP_V2 冲突算法：A>B>C>D；记录所有对 D 层的显式 OVERRIDE
B5 输出 3 行引导回执：GOVERNANCE_LOADED=... / REPO_AUTHORITY=... / OVERRIDES=...
```

- 清单失败不可静默跳过：B1 失败 → 报 `GOVERNANCE_POINTER_MISSING`（不阻断非工程任务）；B3 失败 → 该仓无项目权威，纯 D 层默认 + B 层不变量生效。
- 回执是**证据**：票据包/Stage Packet 引用之，评审可核对。

### 2.3 机械自检（治理仓 CI）

`scripts/validate_governance.py`：canonical 文件存在性、markdown 链接、JSON 解析、secret/机器路径扫描、指针预算（UTF-8 编码字节，判定 = §2.1）、平台标记、manifest 字段、canonical owner 声明、矛盾权威标记。push 前必跑。

## 3. Fresh-session 验证场景（部署后执行的验收协议）

1. 在**中立新工作区**开新会话（无项目 AGENTS/RULES）。
2. 核对注入内容含治理指针（B1 通过）。
3. 令会话执行 BOOTSTRAP_CHECKLIST → 应产出 B5 回执且能正确复述 D 层默认与 B 层不变量。
4. 在 zhihu-grabber-toolkit 仓重复 → 回执应显示 C 层权威已发现（AGENTS/RULES/Specs）。
5. 结果记入本文件"部署验收记录"节。

## 4. 部署验收记录

（空 —— 未部署。部署后按 §3 填写：日期 / 会话观测 / PASS|FAIL / 链接。）

## 5. 边界

- 本合同不解决：MEMORY 注入预算的官方可配置性（UNKNOWN）、工作区根 AGENTS.md 是否被未来版本自动注入（UNKNOWN）——两者出现官方答案时应回改本合同。
- 跨 runtime（Hermes/Codex）：各 runtime 重复 §2.2 清单步骤即可；本合同机制假设仅 §2.1 依赖 WorkBuddy。
