# BOOTSTRAP_CONTRACT — 治理如何被新会话真实看到（F2 修复）

> **CANONICAL（V1.1.1）**。本文只回答：**fresh 工程会话如何保证在开工前看到 canonical 治理**。
> 只用**已验证存在**的机制；不建框架；不假装自动加载。证据 owner = `audit/AS_IS_WORKBUDDY_V3.md` §1–3、§7。
>
> - `BOOTSTRAP_STATIC_VALIDATION = PASS` —— §2.1 预算断言通过；B1–B6 成文；§2.4 交付契约及其仓侧校验器已接入；`scripts/validate_governance.py` 全绿；governance-ci green。
> - `BOOTSTRAP_LIVE_VALIDATION = PARTIAL` —— 机制层与静态层已证；端到端注入观测的取得条件见 §4，不得用笼统 PASS 措辞覆盖。
> - **维护约束**：`deployment/` 受 `no-raw-memory-archive` 的 8 KiB 上限约束。本文件已接近该上限——**记录类内容一律写入 `audit/`，本节只放合同与状态字段**；新增前先确认余量。

## 1. 注入事实（结论层；证据 owner = `audit/AS_IS_WORKBUDDY_V3.md`）

观测 profile：WorkBuddy 5.5.3（app.asar sha256 `f9a3803e…`，2026-09-04）。

```text
GUIDANCE_FILES      = [CODEBUDDY.md, .codebuddy/CODEBUDDY.md, AGENTS.md]  取第一个存在者，不合并
MAX_GUIDANCE_CHARS  = 8000    计量 = JS string length（不是 UTF-8 字节）
注入时机            = first_turn；注入根 = 会话 cwd；截断后仅追加 [...too long, omitted...]
RULES.md            不在清单内 → 永不「经该通道」到达
项目 AGENTS.md      在清单内   → 会到达，但被静默裁剪
CODEBUDDY.md        在清单首位 → 若仓根存在，优先于 AGENTS.md 被选中
```

**四个必须分开的性质**（字段名 owner = 本节；引用本合同必须用下列措辞，不得说「治理已自动交付」）：

```text
FIRST_TURN_AUTO_INJECTION_COVERAGE = PARTIAL
FULL_GOVERNANCE_REACHABILITY       = YES_IF_BOOTSTRAP_FOLLOWED
FULL_GOVERNANCE_AUTOMATIC_DELIVERY = NO
MECHANICAL_ENFORCEMENT             = PARTIAL
AUTO_INJECTION != FULL_GOVERNANCE_DELIVERY
```

故 bootstrap = 自动指针（§2.1）+ 仓侧指针（§2.4）+ 显式清单（§2.2）+ 机械自检（§2.3）。

## 2. Bootstrap 机制（四件套）

### 2.1 MEMORY 指针（自动可见层）

- 候选全文 = `deployment/MEMORY_POINTER_CANDIDATE.md`（治理指针 + 读取清单 + 4 条 B 层不变量摘要），受下方冻结预算约束。
- **部署 = 把候选内容写入 `~/.workbuddy/MEMORY.md`**（一次性、可回滚：旧 MEMORY 原始备份 **local-only（Git 之外）**；`deployment/archive/` 只收 sanitized 快照并过 R2 第一层扫描）。
- 前置：`GOVERNANCE_CORE = PASS` + skills 指南就绪 + owner 对 live 部署的**显式授权**。

**冻结的预算合同（本节是本合同的唯一语义 owner：预算值、单位、profile 区分、override 语义与观测截断点区分只在此处声明；其他 surface 只引用不重述）**：

```text
NAME     WORKBUDDY_MEMORY_POINTER_BUDGET_BYTES
VALUE    3500
UNIT     UTF-8 编码字节数（byte）—— 不是字符数（char），不是 code point 数
SOURCE   WorkBuddy profile 安全预算（观测/profile 属性，不是规范常数）
SCOPE    仅在本 WorkBuddy profile 内有效；不是跨 runtime 通用常数
OWNER    本节（deployment/BOOTSTRAP_CONTRACT.md）；scripts/validate_governance.py 只消费该值
3500 bytes = 主动的规范预算（BUDGET）
4028 bytes = 被动的历史观测截断点（TRUNCATION）；二者性质不同，不得互为定义，取 3500 只为不贴近 4028。
非默认 profile 用自有预算时，必须先有该 profile 自身的已核验观测并**显式记录 OVERRIDE
（值 + 来源 + 观测依据）**；静默替换 = 违规。无已核验 profile 则回落 3500。
```

**单位一致性**：`scripts/validate_governance.py` 的授权测量必须是 `len(body.encode("utf-8"))`；`AGENTS.md` §10 只作指针，不重述预算值。

### 2.2 会话开工清单（agent 执行，每工程会话一次）

```text
BOOTSTRAP_CHECKLIST（工程任务开工前执行）:
B1 读 MEMORY 注入中的治理指针（不存在 → 按治理仓 URL 直接读取并报告缺失）
B2 读治理仓：AGENTS.md + RULES.md + 相关 references（按指针清单）
B3 发现仓内权威：repo 根 AGENTS.md / RULES.md / docs/specs → 读存在者
   若仓根存在 bootstrap 指针文件（§2.4），它不构成权威，必须继续读到其指向的全文
B4 应用 AUTHORITY_MAP_V2 冲突算法：A>B>C>D；记录所有对 D 层的显式 OVERRIDE
B5 核验新鲜 remote truth（有 remote 时）：fetch 后核对 default branch 的 exact SHA
B6 输出引导回执：GOVERNANCE_LOADED=... / REPO_AUTHORITY=... / OVERRIDES=...
```

- 不可静默跳过：B1 失败 → `GOVERNANCE_POINTER_MISSING`；B3 失败 → 该仓无项目权威，纯 D 层默认生效。
- 回执是**证据**；仓本地权威可**加严**本清单，不得削弱 B1–B5 的读取义务。

### 2.3 机械自检（治理仓 CI）

`scripts/validate_governance.py`：canonical 文件存在性、markdown 链接、JSON 解析、secret/机器路径扫描、指针预算（判定 = §2.1）、平台标记、canonical owner 声明、矛盾权威标记。push 前必跑。

### 2.4 工作区根 bootstrap 指针（仓侧交付契约）

§1 表明该通道只取一个文件且会截断，故把全部治理语义放进 `AGENTS.md` 必然只交付头部。

```text
仓根 CODEBUDDY.md = WORKBUDDY_BOOTSTRAP_POINTER
  显式声明「不覆盖 RULES.md / Approved Specs / AGENTS.md / 当前票授权」
  只做一件事：命令 agent 先完整读取被指向的权威，再动手
  仓侧 delivery-contract 校验器保护：尺寸 + 必备指针 + 不得膨胀为第二份 AGENTS.md
  + 不得出现权限授予 / gate 豁免语句 + 回执 schema 完整
```

- 它是**指针，不是权威层**：不得授予权限、改变自动模式、定义例外或豁免 gate；**不得**为迁就注入上限而删减 `AGENTS.md` 的成熟治理语义。
- 尺寸约束的 owner = **目标仓自己的校验器**（须用 §1 的 JS string length 语义）。参考实现：zhihu-grabber-toolkit 的 `CODEBUDDY.md` + `scripts/validate-codebuddy-bootstrap.mjs`；本仓不 vendor 之。

## 3. Fresh-session 验证协议

中立新工作区开新会话（无项目 AGENTS/RULES）逐项核验：B1 指针注入 → 回执正确 → zhihu-grabber-toolkit 的 C 层权威已发现 → 运行时实际选中 `CODEBUDDY.md`、未被截断、随后**完整读取** AGENTS/RULES/project-memory → 硬安全 hook 正 / 负 / 回滚三组（`adapters/workbuddy/`）。

## 4. 部署验收记录

记录本体（逐项观测、证据与边界）的唯一 owner = `audit/AS_IS_WORKBUDDY_V3.md` §7。本节只登记状态字段：

```text
MEMORY_POINTER_DEPLOYED         = YES
CODEBUDDY_CREATED               = YES    （zhihu-grabber-toolkit 仓根；3443 JS chars，无截断风险）
DELIVERY_CONTRACT_VALIDATOR     = zhihu-grabber-toolkit: scripts/validate-codebuddy-bootstrap.mjs
BOOTSTRAP_STATIC_VALIDATION     = PASS   （含负向测试；PASS 的对象 = 交付契约，不是运行时行为）
BOOTSTRAP_LIVE_VALIDATION       = PARTIAL
FRESH_SESSION_SELECTED_GUIDANCE = NOT_PROVABLE_IN_THIS_RECORD（理由与取证条件见 V3 §7）
```

## 5. 边界

- 已关闭的旧 UNKNOWN：「工作区根 AGENTS.md 是否被自动注入」→ **关**：注入**是**发生的，但被 `MAX_GUIDANCE_CHARS` 截断，且 `RULES.md` 不在清单内（限 §1 的 profile/版本；升级后须重新取证）。
- 已关闭的旧 UNKNOWN：「hooks 接线面与端到端 deny 观测」→ **关**（2026-09-28 实测：注册 1 条 + 执行前拦截）；状态 owner = `adapters/workbuddy/README.md` §2。
- 仍未解决（保持 UNKNOWN，不得靠推断填补）：MEMORY 预算的官方可配置性；`GUIDANCE_FILES` / `MAX_GUIDANCE_CHARS` 的未来版本稳定性；`~/.codebuddy/settings.json` 是否被 WorkBuddy 读取。详见 V3 §6。
- 跨 runtime（Hermes/Codex）：重复 §2.2 清单即可；§2.1 与 §2.4 的机制假设仅针对 §1 标注的 profile。
