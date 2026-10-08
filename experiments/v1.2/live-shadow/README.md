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

BASE/CANDIDATE 绑定（v1 规则）：采用**集成落地对**——`CANDIDATE_SHA = merge 提交`
（本批全部为 fast-forward 形态，merge == PR head），`BASE_SHA = candidate^`。
两枚 SHA 必须可由 clone 解析；否则该 observation 记 `UNINTERPRETABLE`/NOT_OBSERVABLE。

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
H3_B_STATUS = COLLECTING（处理中；结果见本文件末尾追加的 Batch 1 段）
```
