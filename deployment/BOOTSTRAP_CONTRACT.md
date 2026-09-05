# BOOTSTRAP_CONTRACT — 治理如何被新会话真实看到（F2 修复）

> 状态：CANDIDATE。本文回答一个工程问题：**fresh WorkBuddy 工程会话如何保证在开工前看到 canonical 治理**。
> 原则：只使用**已验证存在**的机制；不建框架；不假装自动加载。
>
> **验证状态（证据诚实拆分，R2 修复）**：
> - `BOOTSTRAP_STATIC_VALIDATION = PASS` —— 指针预算断言（≤3,500 字符 vs 实测截断 4028）通过；BOOTSTRAP_CHECKLIST B1–B5 成文；`scripts/validate_governance.py` 9/9 通过；GitHub Actions governance-ci 已配置（R1）。
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

- `deployment/MEMORY_POINTER_CANDIDATE.md` = 替换 `~/.workbuddy/MEMORY.md` 的候选全文，**≤3,500 字符**（预算 4,028 减安全余量）。
- 内容 = 治理仓指针 + 读取清单 + 4 条 B 层不变量摘要（即使后续加载全部失败，这 4 条也已随注入可见）。
- **部署 = 把候选内容写入 `~/.workbuddy/MEMORY.md`**（一次性、可回滚：旧 MEMORY 全文先归档到治理仓 `deployment/archive/`，不删除任何历史语义——全部内容已迁移至本仓 canonical 文件）。
- 部署前置条件：外部 fresh 评审 APPROVE + skills manifest 补齐（REPRODUCIBILITY=INCOMPLETE 未解除）+ product owner 显式授权。**当前未部署**。

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

`scripts/validate_governance.py`：canonical 文件存在性、markdown 链接、JSON 解析、secret/机器路径扫描、指针预算（≤3,500 字符）、平台标记、manifest 字段、canonical owner 声明、矛盾权威标记。push 前必跑。

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
