# experiments/v1.2/live-shadow — H3-B LIVE SHADOW（非 canonical）

> 本目录是 V1.2 Experiment 1 / **H3-B** 的最小观察面：在**真实工程 ticket** 上测量
> `STRUCTURE_DELTA_SHADOW v0`（H3-A，已合并于 main @ 5b55b6d）的三个机械信号是否
> 提供正常 V1.1.1 流程之外**独特、高价值**的信息。
> 边界：**非 canonical、不接 CI、不 block merge、不产生任何自动化判定、不进入 reviewer
> 正常流程**；shadow 输出在正常证据冻结之前不可见。

## 1. 问题（本轮只回答这个）

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
  本轮**不实现**（否则实验变量改变、数据失去可比性）。
- shadow 运行 = `python3 experiments/v1.2/structure_delta.py signals --repo ... --base ... --candidate ...`
  （只输出三项计数；不加第四种信号、不加判定字段）。

## 3. 每个 observation 的顺序（强制）

```text
Step A  正常 V1.1.1 工作先完成：BASE/CANDIDATE + tests + CI + review + findings
        → 冻结 NORMAL_EVIDENCE_SNAPSHOT（tests / ci / review 三栏）
        （此刻之前：不运行、不展示任何 shadow 输出）
Step B  对同一对 BASE/CANDIDATE 运行 shadow（仅三信号计数）
Step C  事后价值判断：normal evidence + shadow signals 对照
```

原则：`NORMAL WORKFLOW FIRST, SHADOW OBSERVATION AFTER`。
shadow 输出从未参与、也不得参与实现 / reviewer / tests / CI / merge decision /
risk / architecture disposition；observation 记录 `shadow_influenced_normal_review: false`。

## 4. 资格与排除（pre-registered）

ELIGIBLE 必须全部满足：

```text
REAL_USER_OR_PROJECT_TASK = YES     真实工程任务（非 synthetic、非 demo）
REAL_BASE / REAL_CANDIDATE = YES    两枚真实提交，可由 clone 解析
NORMAL_WORKFLOW_ALREADY_RAN = YES   正常流程实际发生（tests / CI / review 记录在案）
NORMAL_FINDINGS_FROZEN_BEFORE_SHADOW = YES
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

枚举命令（可复现）：

```bash
gh pr list -R <repo> --state merged --limit 100 --search "merged:>=2026-09-24"
```

## 6. 候选矩阵（FROZEN @ 本提交；inclusion 于 shadow 运行前锁定）

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
逐案等式不适用于多提交 PR。已改为 fork-point 对并复跑；本批 5/7 票受此修正影响
（#128/#36/#37/#38/#132）。此为实验协议修正，非 detector 机械错误。

## 7. Observation receipt（observations.jsonl，一行一条）

```json
{
  "observation_id": "h3b-00N",
  "repository": "owner/repo",
  "ticket_ref": "PR #N — title",
  "base_sha": "...", "candidate_sha": "...",
  "normal_evidence_frozen": true,
  "normal_findings": {"tests": [], "ci": [], "review": []},
  "shadow_signals": {"NEW_FILE": 0, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 0},
  "value_disposition": "...", "rationale": "...",
  "shadow_influenced_normal_review": false,
  "shadow_runtime_ms": 0
}
```

- `normal_findings` 只存稳定 refs / 紧凑摘要（不复制大段 reviewer 文本）。
- `tests/ci` = 正常流程实际记录的测试与 CI 证据（check-run 名与结论）；
  `review` = 实际记录的评审 findings（含「无记录」这一事实本身）。
- `shadow_runtime_ms` = 本地 signals 运行墙钟（informational）。

## 8. Value disposition（窄语义，防状态坍缩）

```text
NO_SIGNAL                       三项均为 0。
DUPLICATE_OF_NORMAL_EVIDENCE    signal 对应信息在 shadow 运行前已被 contract / review /
                                tests / CI 明确记录。
NON_ACTIONABLE_STRUCTURE_FACT   机械事实真实、但对 ticket 无决策价值（无需任何处置）。
UNIQUE_LOW_VALUE_INFORMATION    normal evidence 未记录，但知道它也不会改变任何决策
                                （implementation / review / owner / architecture / merge）。
UNIQUE_HIGH_VALUE_FINDING       同时满足：NOT_PRESENT_IN_NORMAL_EVIDENCE + ACTIONABLE +
                                MATERIALLY_CHANGES_ENGINEERING_DECISION；
                                必须写明 WHAT_DECISION_WOULD_CHANGE。
UNINTERPRETABLE                 证据不足，不硬分类。
```

判档指引（防主观漂移）：先查「是否已被记录」→ DUPLICATE；未记录时再查「是否可行动且
改变决策」→ HIGH；未记录且无需处置 → NON_ACTIONABLE；未记录且仅信息性 → LOW_VALUE。
`FALSE POSITIVE` 一词保留给**机械计算错误**（本轮若出现 ⇒ 记录并重开 H3-A defect）；
「算对了但没价值」一律记 NON_ACTIONABLE，不称 false positive。

## 9. Metrics（按 observations.jsonl 聚合）

```text
OBSERVATIONS / SIGNAL_FIRED_TICKETS / NO_SIGNAL_TICKETS
SIGNAL_EVENTS = Σ 触发信号的（ticket × signal）对
DUPLICATE_EVENTS / NON_ACTIONABLE_EVENTS / UNIQUE_LOW_VALUE_EVENTS /
UNIQUE_HIGH_VALUE_FINDINGS / UNINTERPRETABLE_EVENTS
  = 按 ticket 的 disposition 归类其 fired events（ticket 级处置、event 级计数）
MECHANICAL_ERRORS  SHADOW_EVALUATOR_CALLS  SHADOW_RUNTIME_MS（可低成本获得时）
```

## 10. 结果语义（pre-registered，无 promotion）

```text
observations < 10                      → H3_B_RESULT = INSUFFICIENT_SAMPLE
observations >= 10 且 UNIQUE_HIGH = 0  → VALUE_NOT_DEMONSTRATED
observations >= 10 且 UNIQUE_HIGH >= 1 → VALUE_SIGNAL_FOUND
```

任何结果都**不**产生 WARN / BLOCK / promotion；`VALUE_SIGNAL_FOUND` 也只说明值得继续
有限 shadow 验证。样本不足 = `H3_B_STATUS = COLLECTING`，完全合法。

## 11. 完整性检查（stdlib，极小）

```bash
python3 experiments/v1.2/live-shadow/check_observations.py
```

仅验证：jsonl 可解析、id 唯一、SHA 非空 40-hex、`normal_evidence_frozen=true`、
`shadow_influenced_normal_review=false`、disposition 属定义集合、shadow_signals 恰为三信号。
不是 schema framework；不生成、不修复、不判定。

## 12. 批次状态

```text
H3_B_BATCH = 1
H3_B_STATUS = COLLECTING（Batch 1 已完成：n=7；结果见下）
```

## Batch 1（2026-10-08）— 结果

```text
OBSERVATIONS = 7                SIGNAL_FIRED_TICKETS = 5        NO_SIGNAL_TICKETS = 2
SIGNAL_EVENTS = 8               DUPLICATE_EVENTS = 8           NON_ACTIONABLE_EVENTS = 0
UNIQUE_LOW_VALUE_EVENTS = 0     UNIQUE_HIGH_VALUE_FINDINGS = 0 UNINTERPRETABLE_EVENTS = 0
MECHANICAL_ERRORS = 0           SHADOW_EVALUATOR_CALLS = 1（batch evaluator，方法审阅）
SHADOW_RUNTIME_MS = 103.4–129.9（单次 signals 运行墙钟，本机，informational）

H3_B_RESULT = INSUFFICIENT_SAMPLE
  （observations = 7 < 10；按预注册语义，即使出现 unique finding 也只能算 early signal）
```

- 逐条 observation：[observations.jsonl](observations.jsonl)（h3b-001..h3b-007，逐案
  EXPECTED-free：仅记录 normal evidence 快照 + 三信号计数 + 窄语义 disposition）。
- 采样面：窗口内全部 merged PR = 10 个（四仓合计：gov 7 + zhihu 3）→ 纳入 7；
  pre-registered 排除 3（实验弧 #39/#40/#41，其中 #41 为 mandate 明文排除）；
  gov #32（OPEN）在途挂起（证据未冻结）。
  （2026-10-08 修正：初稿误记「11 个 / 排除 4」——batch evaluator F1 指出后按事实更正；
  纳入集合本身未受影响。）
- 校准记录（append-only）：见第 6 节修正记录（diff 绑定 → fork-point 对；h3b-001 已重跑）。
- 污染检查：7 票的正常证据（body / review / comments / CI）全文扫描无任何
  shadow / detector / 信号术语命中；shadow 从未进入任何 ticket 流程。
- 早期模式（非结论，供后续批次对照）：5 个 signal-fired ticket 的全部 8 个 fired events
  均为既已记录信息（依据 = contract 逐名声明 / review 直接锚定 / 归档 manifest 机器核验）；
  2 个零信号票与其声明范围一致。本批未见 UNIQUE_* 事件、未见机械错误、
  未见 UNSUPPORTED_SIGNAL_OPPORTUNITY 主张。
- 值得记入的观察（不作为结论）：h3b-007 显示计数型信号与验收管线自带的文件级
  manifest 核验（472 条目 + 缺失文件级 P2）相比，分辨率严格更弱；在该类 ticket 上，
  增加信号类别不会改变这一分辨率关系。
- Batch evaluator（fresh，experiment-method review）@11a46e0 = CHANGES_REQUIRED：
  1×P2（F1：采样面计数笔误，本提交已按事实修正为 10/3）+ 2×P3（F2：绑定规则修正
  已披露、仅预注册卫生注记；F3：h3b-007 在 rubrics 边界上——评阅确认「可辩护、
  immaterial」，本批保留 DUPLICATE，依据 = 归档面已在证据中逐面记录且被文件级核验，
  仅聚合计数未逐字出现）。评阅同时独立复跑全部 7 条计数（与记录逐一相同）、
  复算 3 个 fork 点（全部一致）、污染扫描 0 命中、无 selection bias、detector 零改动。
  F1 修正本身未改变任何 observation、计数、disposition 或结果。
