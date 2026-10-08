# experiments/v1.2/live-shadow — H3-B0 retrospective calibration + H3-B1 prospective shadow（非 canonical）

> 本目录是 V1.2 Experiment 1 / **H3-B** 的最小观察面：在**真实工程 ticket** 上测量
> `STRUCTURE_DELTA_SHADOW v0`（H3-A，已合并于 main @ 5b55b6d）的三个机械信号是否
> 提供正常 V1.1.1 流程之外**独特、高价值**的信息。
> 组成：**H3-B0**（retrospective calibration：对 2026-09-24..10-08 已完成真实 ticket 的
> 事后校准，n=7，见文末段）与 **H3-B1**（prospective live shadow：自 PROSPECTIVE_EPOCH_START
> 起对自然发生的 ticket 做序时受控观察；协议为紧随的独立增量）。
> 边界：**非 canonical、不接 CI、不 block merge、不产生任何自动化判定、不进入 reviewer
> 正常流程**；shadow 输出在正常证据冻结之前不可见。

## 1. 问题（只回答这个）

```text
在真实 ticket 中，NEW_FILE / NEW_DIRECTORY / NEW_DEPENDENCY 是否提供正常 V1.1.1
流程（tests / CI / review）之外的独特、高价值信息？
```

不回答：detector 对不对（H3-A 已答）；结构变化对不对（detector 不负责判定）。

## 2. Detector（冻结，不得扩展）

- 路径：[`../structure_delta.py`](../structure_delta.py)（H3-A 产物；main @
  `5b55b6d7c3cd1fa25622b06bac43132e64f6e54a` 合并）。
- 信号集合冻结为三项：`NEW_FILE` / `NEW_DIRECTORY` / `NEW_DEPENDENCY`。
  即使发现「加 NEW_MODULE 能抓到更多」也只记录 `UNSUPPORTED_SIGNAL_OPPORTUNITY`，
  **不实现**（否则实验变量改变、数据失去可比性）。
- shadow 运行 = `python3 experiments/v1.2/structure_delta.py signals --repo ... --base ... --candidate ...`
  （只输出三项计数；不加第四种信号、不加判定字段）。

## 3. 目标时序（H3-B1 prospective 形态；强制）

```text
ticket 正常发生 → 正常实现 → tests / CI / review → 冻结 NORMAL_EVIDENCE_SNAPSHOT
（记录 normal_evidence_frozen_at）→ 首次运行 shadow（记录 shadow_first_run_at）
→ 事后价值判断（Step C）
```

原则：`NORMAL WORKFLOW FIRST, SHADOW OBSERVATION AFTER`。
shadow 输出从未参与、也不得参与实现 / reviewer / tests / CI / merge decision /
risk / architecture disposition；observation 记录 `shadow_influenced_normal_workflow: false`。

（H3-B0 为 **retrospective calibration**：7 票在 detector 存在之前即已完成并 merged，
证据为事后快照，序时不可事后补证；该限制按重分类处理并显式免责——见文末 H3-B0 段。
其记录**不携带**冻结/shadow 时间戳。）

## 4. 资格与排除（pre-registered）

ELIGIBLE 必须全部满足：

```text
REAL_USER_OR_PROJECT_TASK = YES     真实工程任务（非 synthetic、非 demo）
REAL_BASE / REAL_CANDIDATE = YES    两枚真实提交，可由 clone 解析
NORMAL_WORKFLOW_ALREADY_RAN = YES   正常流程实际发生（tests / CI / review 记录在案）
NORMAL_FINDINGS_FROZEN_BEFORE_SHADOW = YES
                                    （prospective 由 §7 时间戳强制；retrospective 为事后快照，见免责）
```

排除（pre-registered）：

```text
- replay corpus cases r01–r06 的源变更对（不得再次计入）；
- agent-engineering-governance PR #39 / #40 / #41（V1.2 实验构造弧自身；#41 含 detector
  实现，明文禁止）；
- synthetic fixture / 为 detector 写的 demo / 人为制造的结构变化；
- 为凑样本重新执行的历史 ticket。
```

## 5. 采样规则与窗口（pre-registered，signal-blind）

```text
来源仓 = 当前工作环境内的全部 FlapPearLabs 项目：
  agent-engineering-governance / zhihu-grabber-toolkit / webcodex / workbuddy-toolkit
窗口   = 正常流程到达记录终态（merged）且 mergedAt ∈ [2026-09-24, 2026-10-08]
         （H3-B 开工前 14 天，H3-B 开工前预设，未按结果调整）
单元   = 每个 merged PR = 一个 observation；按 merge 时间顺序连续纳入，不跳选。
```

关键纪律：**纳入决定不基于任何 diff / 信号观察**（枚举只使用 PR 元数据与日期检索）。
diff 与信号只在 inclusion 冻结之后（Step B/C）才被检视。

枚举命令（可复现，含窗口上界；上界必须与下界同时写入，否则窗口后复跑会把窗口外的
后续 PR 混入、复现不出登记时总体）：

```bash
gh pr list -R <repo> --state merged --limit 100 --search "merged:2026-09-24..2026-10-08"
```

## 6. 候选矩阵（FROZEN @ 预注册提交；inclusion 于 shadow 运行前锁定）

```text
INCLUDED（7，按 merge 时间序 → observation_id h3b-001..h3b-007）：
  h3b-001  zhihu-grabber-toolkit #128  109b801089c32a4bf096fccfd434fb177a71d02a  2026-09-27
  h3b-002  zhihu-grabber-toolkit #129  9b9dc12a3b39bfbae39397869b7256a7f72cb75a  2026-09-27
  h3b-003  agent-engineering-governance #35  833046a7c440a74925773d7b4fdadbf42c745c27  2026-10-02
  h3b-004  agent-engineering-governance #36  7738cb1107ee6b629b75b2a61ccec1c503fbd454  2026-10-02
  h3b-005  agent-engineering-governance #37  8c0075c5db0e06eec67d303955d13e214ba22782  2026-10-03
  h3b-006  agent-engineering-governance #38  0404879936a3c36f5eca2b32d36f0d664464411a  2026-10-04
  h3b-007  zhihu-grabber-toolkit #132  880862566478f9885b9a3c5bf25581529edd2a28  2026-10-07

PENDING（不计入）：
  gov #32（OPEN @ head 95de4c3aab；在途，正常证据未冻结——若未来自然完成可入下一批）。

EXCLUDED（pre-registered）：
  gov #39 / #40 / #41（实验构造弧）；replay r01–r06 源变更对；
  webcodex / workbuddy-toolkit：窗口内无 PR 型 workflow 单元（workflow 不产生 PR 记录）；
  纯 issue 型工作（若有）：无单一可落地 diff 对，v1 单元定义之外。
```

BASE/CANDIDATE 绑定（v1 规则，2026-10-08 修正）：采用**ticket 完整落地对**——
`CANDIDATE_SHA = merge 提交`（本批全部 fast-forward 形态，merge == PR head）；
`BASE_SHA = PR 的 fork point`（= PR 提交列表首个提交的父提交，即 GitHub 三点 diff 的基线）。
两枚 SHA 必须可由 clone 解析；否则该 observation 记 `UNINTERPRETABLE`/NOT_OBSERVABLE。

修正记录（append-only，发现于 Step B 首跑）：protocol 冻结时曾写 `BASE_SHA = candidate^`；
h3b-001 首跑即证伪——多提交 FF PR 的 `candidate^` 只给出**最后一个提交**的增量
（得 0/0/0，与 PR 声明的「New module」矛盾）。根因：replay corpus 的 `candidate^ == base`
逐案等式**只适用于 single-commit / direct-parent 情形**，不适用于多提交 PR；
一般多提交 PR 必须改用 PR fork point。已改为 fork-point 对并复跑；本批 5/7 票受此修正
影响（#128/#36/#37/#38/#132）。此为实验协议修正，**非 detector 机械错误**。

## 7. Observation receipt（observations.jsonl，一行一条）

```json
{
  "observation_id": "h3b1-00N（PROSPECTIVE）| h3b-00N（RETROSPECTIVE）",
  "mode": "PROSPECTIVE | RETROSPECTIVE",
  "repository": "owner/repo",
  "ticket_ref": "PR #N — title",
  "base_sha": "...", "candidate_sha": "...",
  "normal_evidence_frozen": true,
  "normal_evidence_frozen_at": "ISO-8601（仅 PROSPECTIVE 必填）",
  "shadow_first_run_at": "ISO-8601（仅 PROSPECTIVE 必填）",
  "normal_findings": {"tests": [], "ci": [], "review": []},
  "shadow_signals": {"NEW_FILE": 0, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 0},
  "signal_dispositions": {"NEW_FILE": "NO_SIGNAL", "NEW_DIRECTORY": "NO_SIGNAL", "NEW_DEPENDENCY": "NO_SIGNAL"},
  "rationale": "...",
  "shadow_influenced_normal_workflow": false,
  "shadow_runtime_ms": 0
}
```

- 处置粒度 = **逐 signal**（`signal_dispositions`，每个信号一个值；未触发信号记 `NO_SIGNAL`）。
  不设 ticket 级单值处置覆盖全部 fired events（混合结果会被迫错分类；见 §8 与收敛记录 F4）。
- 模式/编号配对：RETROSPECTIVE 行 = `h3b-NNN`；PROSPECTIVE 行 = `h3b1-NNN`。
  检查器强制该配对，保证 retrospective 数据**永远不可能**被计入 prospective 计数。
- `normal_findings` 只存稳定 refs / 紧凑摘要（不复制大段 reviewer 文本）；
  `tests/ci` = 正常流程实际记录的测试与 CI 证据（check-run 名与结论）；
  `review` = 实际记录的评审 findings（含「无记录」这一事实本身）。
- `normal_evidence_frozen_at` / `shadow_first_run_at`：**prospective 的「冻结先于 shadow」
  顺序证据**（ISO-8601 含时区偏移；检查器强制前者严格早于后者；违反 ⇒ 该 observation
  对 prospective 无效）。retrospective 行不携带这两个字段——事后快照无法诚实补记时间戳，
  其污染性质以显式免责替代（见 H3-B0 段）。
- `shadow_runtime_ms` = 本地 signals 运行墙钟（informational）。

## 8. Value disposition（逐 signal 窄语义，防状态坍缩）

```text
NO_SIGNAL                       该信号未触发（count = 0）。检查器强制：(count == 0) ⟺ NO_SIGNAL。
DUPLICATE_OF_NORMAL_EVIDENCE    该信号计数的 added set 可从冻结证据**逐项认出**（逐名列出 /
                                review path 锚定 / 由已命名交付物直接推得计数）→ 无新增信息。
NON_ACTIONABLE_STRUCTURE_FACT   机械事实真实、但对 ticket 无决策价值（无需任何处置）。
UNIQUE_LOW_VALUE_INFORMATION    冻结证据未逐项记录该集合或其计数，但知道它也不会改变任何决策
                                （implementation / review / owner / architecture / merge）。
UNIQUE_HIGH_VALUE_FINDING       同时满足：NOT_PRESENT_IN_NORMAL_EVIDENCE + ACTIONABLE +
                                MATERIALLY_CHANGES_ENGINEERING_DECISION；
                                必须写明 what_decision_would_change（检查器强制非空）。
UNINTERPRETABLE                 证据不足，不硬分类。
```

判定边界（2026-10-08 校准确认，供本实验后续一致适用）：

- 「明确记录」的判定以**逐项可认出性**为准：集合可逐项认出 ⇒ 计数可由证据数出 ⇒
  DUPLICATE；证据只以 bundle / 面（如「一个证据包」「一个隔离案例」）描述、集合不可
  逐项认出 ⇒ 该计数属未记录信息 ⇒ 归 UNIQUE_LOW_VALUE（若不可行动）。
  边界意图上**从严**：宁可标 UNIQUE_LOW_VALUE（不夸大 DUPLICATE），也不让
  「聚合量未记录」混入 DUPLICATE。
- 混合结果按 signal 分别判档（不得用一个 ticket 级值覆盖全部 fired events）。
- `FALSE POSITIVE` 一词保留给**机械计算错误**（出现 ⇒ 记录并重开 H3-A defect）；
  「算对了但没价值」一律记 NON_ACTIONABLE / UNIQUE_LOW_VALUE，不称 false positive。

## 9. Metrics（按 observations.jsonl 聚合）

```text
OBSERVATIONS = RETROSPECTIVE + PROSPECTIVE（两者永不合并计数）
SIGNAL_FIRED_TICKETS / NO_SIGNAL_TICKETS
SIGNAL_EVENTS = Σ 触发信号的（ticket × signal）对
DUPLICATE_EVENTS / NON_ACTIONABLE_EVENTS / UNIQUE_LOW_VALUE_EVENTS /
UNIQUE_HIGH_VALUE_FINDINGS / UNINTERPRETABLE_EVENTS
  = 按逐 signal disposition 归类 fired events（event 级计数；混合结果可表示）
MECHANICAL_ERRORS  SHADOW_EVALUATOR_CALLS  SHADOW_RUNTIME_MS（可低成本获得时）
```

## 10. 结果语义（pre-registered，无 promotion；对 H3-B1 prospective 集生效）

```text
prospective observations < 10                      → H3_B1_STATUS = COLLECTING
prospective observations >= 10 且 UNIQUE_HIGH = 0  → VALUE_NOT_DEMONSTRATED
prospective observations >= 10 且 UNIQUE_HIGH >= 1 → VALUE_SIGNAL_FOUND
```

- H3-B0（retrospective）**不计入** prospective threshold；其结果是校准信息，不是 H3 结论。
- 任何结果都**不**产生 WARN / BLOCK / promotion；`VALUE_SIGNAL_FOUND` 也只说明值得继续
  有限 shadow 验证。样本不足 = `COLLECTING`，完全合法；**不得为凑样本造票**。
- 早停/方向性：若 prospective 连续真实样本继续 0 unique high-value，可在后续实验审查中
  评估 VALUE_NOT_DEMONSTRATED → defer / redesign / delete；禁止自动 WARN / BLOCK。

## 11. 完整性检查（stdlib，极小）

```bash
python3 experiments/v1.2/live-shadow/check_observations.py
```

验证：jsonl 可解析；id 唯一且与 mode 配对（`h3b-` / `h3b1-`）；SHA 40-hex；
`normal_evidence_frozen=true`；`shadow_influenced_normal_workflow=false`；
shadow_signals 恰为三信号且为**非负整数**（拒绝 bool）；signal_dispositions 恰为三信号、
值属词表、强制 `(count==0) ⟺ NO_SIGNAL`；UNIQUE_HIGH_VALUE_FINDING 必须带
`what_decision_would_change`；PROSPECTIVE 行强制 `frozen_at < first_run_at`（ISO-8601 带偏移）。
不是 schema framework；不生成、不修复、不判定。

## 12. 状态

```text
H3_B0 = COMPLETE（retrospective calibration；结果见下）
H3_B1_STATUS = NOT_STARTED（prospective 协议为紧随的独立增量；本文档其后将追加 B1 权威小节）
```

## H3-B0（RETROSPECTIVE CALIBRATION）— 结果（2026-10-08）

```text
RETROSPECTIVE_OBSERVATIONS = 7                 PROSPECTIVE_LIVE_OBSERVATIONS = 0
RETROSPECTIVE_SIGNAL_FIRED_TICKETS = 5         RETROSPECTIVE_NO_SIGNAL_TICKETS = 2
RETROSPECTIVE_SIGNAL_EVENTS = 8
RETROSPECTIVE_DUPLICATE_EVENTS = 3             RETROSPECTIVE_NON_ACTIONABLE_EVENTS = 0
RETROSPECTIVE_UNIQUE_LOW_VALUE_EVENTS = 5      RETROSPECTIVE_UNIQUE_HIGH_VALUE_FINDINGS = 0
RETROSPECTIVE_UNINTERPRETABLE_EVENTS = 0       RETROSPECTIVE_MECHANICAL_ERRORS = 0

SHADOW_EVALUATOR_CALLS = 1（batch method review）+ 1（codex 自动评审轮）
SHADOW_RUNTIME_MS = 103.4–129.9（单次 signals 运行墙钟，本机，informational）

H3_B0_RESULT = NO_UNIQUE_VALUE_OBSERVED
  （精确表述 = NO_UNIQUE_HIGH_VALUE_OBSERVED；另有 5 个 UNIQUE_LOW_VALUE 事件——均为
    「集合未被逐项记录、但非决策相关」的聚合量——不构成价值证据）
H3_B1_STATUS = NOT_STARTED
  （本批 7 条 retrospective observations 不计入 prospective threshold）
```

- 逐条 observation：[observations.jsonl](observations.jsonl)（h3b-001..h3b-007）。逐票
  fired 信号与判档：h3b-001 NEW_FILE×2→DUP；h3b-002/003 零信号；h3b-004 NEW_FILE×3→DUP、
  NEW_DIRECTORY×1→DUP；h3b-005 NEW_FILE×5→UL；h3b-006 NEW_FILE×57→UL、NEW_DIRECTORY×4→UL；
  h3b-007 NEW_FILE×2141→UL、NEW_DIRECTORY×967→UL。
- 采样面：窗口内全部 merged PR = 10 个（四仓合计：gov 7 + zhihu 3）→ 纳入 7；
  pre-registered 排除 3（实验弧 #39/#40/#41，其中 #41 为 mandate 明文排除）；
  gov #32（OPEN）在途挂起（证据未冻结）。
  （2026-10-08 修正：初稿误记「11 个 / 排除 4」——batch evaluator F1 指出后按事实更正；
  纳入集合本身未受影响。）
- **重分类（2026-10-08，本轮）**：本批运行于 ticket 全部完成之后（detector 2026-10-08 才
  首次进入 main），属 **retrospective calibration**，不是 prospective live shadow；
  原「Batch 1 / H3_B_RESULT = INSUFFICIENT_SAMPLE」表述停用。这 7 条不计入 future
  prospective threshold，也**不得**作为 live-shadow 污染控制证据。
- 污染声明的精确形式（重分类后）：
  `RETROSPECTIVE_CONTAMINATION = STRUCTURALLY_IMPOSSIBLE_BY_DESIGN` —— 全部 7 票在 detector
  首次运行前已 merged（2026-09-27..10-07 < 10-08），且各票证据全文扫描 0 命中
  shadow / detector / 信号术语。**免责**：这是事后时序论证，不构成 prospective
  非污染证据——prospective 的「冻结先于 shadow」由 §7 时间戳对强制。
- 逐项判定汇总（8 fired events）：
  - DUPLICATE ×3：h3b-001（两文件逐名）、h3b-004（三文件逐名，目录由其直接推得）；
  - UNIQUE_LOW_VALUE ×5：h3b-005（模块/schema 有 review path 锚定，测试与模板仅机制性
    描述）、h3b-006 ×2（57 文件/4 目录仅以面描述）、h3b-007 ×2（2141 文件/967 目录前缀；
    证据精度为策展的 472 条目 manifest 子集）。判定标准见 §8；无任何 UNIQUE_HIGH_VALUE。
- 值得记入的观察（不作为结论）：在证据密集型流程下，计数型信号与验收管线自带的文件级
  manifest 核验（472 条目 + 缺失文件级 P2）相比，分辨率严格更弱；对 bundle 类变更，
  增加/减少计数不会改变这一分辨率关系。
- 评审收敛记录（append-only）：
  - batch evaluator（fresh，experiment-method review）@11a46e0 = CHANGES_REQUIRED：
    1×P2（采样面计数笔误，已按事实修正为 10/3）+ 2×P3（F2：绑定规则修正已披露、仅
    预注册卫生注记；F3：h3b-007 在 rubrics 边界上——该注记经下述 codex 轮重审后**被取代**：
    007 已按精化边界改判 UNIQUE_LOW_VALUE）。评阅同时独立复跑全部 7 条计数（逐一相同）、
    复算 3 个 fork 点（全部一致）、污染扫描 0 命中、无 selection bias、detector 零改动。
  - codex 自动评审 @59bf724（7 条内联：1×P1 + 6×P2）——全部采纳并修复（本轮）：
    F4(P1) 处置改为逐 signal（`signal_dispositions`）；F7 h3b-007 改判 UNIQUE_LOW_VALUE，
    且同一标准**一致重审** h3b-005/006（其计数集合亦不可从证据逐项认出）；F1/F2/F3 检查器
    强制 `(count==0)⟺NO_SIGNAL`、拒绝 bool 计数、键集合比较（非序数元组）；F5 枚举命令
    补窗口上界；F6 retrospective 序时不可证 ⇒ 重分类 + 免责声明，prospective 时间戳/排序
    强制入检查器。检查器行为经 7 项 /tmp 反例核验（NO_SIGNAL+正计数、bool 计数、乱序键、
    缺键、prospective 排序倒置、裸时间戳、UHV 缺 what_decision_would_change）。
