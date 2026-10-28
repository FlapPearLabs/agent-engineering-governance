# N2.1 — Eligibility Schema Revision · CLOSURE REPORT

> 本文件是 N2.1 节点的关闭交付物（append-only）。
> 被复核的工件 SHA 固定为 `95985d2ca14b72b656ecacf4adf7ce5da9280e6c`（见 `FINAL_REVIEW_SHA`）。
> 本文件自身的提交 SHA 不在此处写死（禁止文档自引用 SHA）。

---

## FINAL REPORT（按指令 PART 12 / FINAL REPORT 模板）

```text
REPO               = FlapPearLabs/agent-engineering-governance
BRANCH             = experiment/v1.2-h2-eligibility-schema
BASE_SHA           = 1b82a53f97bde2062ef39b93aa06cc6c9fbda38b   (N2.1 起点 base)
FINAL_CANDIDATE_SHA= 95985d2ca14b72b656ecacf4adf7ce5da9280e6c
REMOTE_HEAD        = 95985d2ca14b72b656ecacf4adf7ce5da9280e6c   (已推送，与本地一致)

ROUND8_RECOVERY    = Round-8 修复（harness read-boundary + repair-record 自引用 helper）已恢复，
                     并按 Round-9 裁定「走 B」扩展至 F1/F2/F4/F5/F6，最终定型于 95985d2。
ROUND8_TESTS       = 见 FULL_GATES（95985d2 上的全部门禁）。

FULL_GATES:
  full_suite          = Ran 255 tests in 238.586s · OK
  eligibility_suite   = Ran 73 tests in 192.737s · OK
  ruff                = All checks passed! (ruff 0.15.18)
  validator           = TASK_CLASS_VERDICT = PASS · records=3 · valid_requests=0 ·
                         rejected=3 · errors=0 · enforcement=IDENTITY+DERIVED_TRIGGERS+REPO_FACTS
  public_release      = MODE=PUBLIC · VIOLATIONS=0
  scope               = 16 changed paths，全部 under experiments/；
                         四冻结文件 vs 1b82a53 全部 IDENTICAL
                         (task-registry.json / scoring-rubric.md / routes-h2.json / protocol.md)
  canonical_diff      = 变更集全部位于 experiments/；CANONICAL 失败 ID 集合保持 28（未引入新治理缺陷）

SCHEMA_VERSION      = 2.8.0
FACTORY_VALID_REQUESTS = 0

LAUNDERING_VARIANTS = 永久回归已就位：
                     · RecomputedTransition.test_r06_laundering_reproduction_is_refused
                       （重新将 shipped r06 记录归类为 B_REGRESSION_GUARD，清 trigger，
                        断言以 MUTATION_DOES_NOT_BITE 拒绝）
                     · LaunderingVariants 类（六变体）覆盖 shape/identity 级拒绝
                       （DERIVED-from-git-diff / corpus mismatch / degenerate pair）
FAKE_VALID_REQUESTS_ACCEPTED = 0

FINAL_REVIEW_ROUND = 10
FINAL_REVIEW_SHA   = 95985d2ca14b72b656ecacf4adf7ce5da9280e6c
FINAL_REVIEW_P0    = 0
FINAL_REVIEW_P1    = 0
FINAL_REVIEW_P2    = 0
FINAL_REVIEW_P3    = 2
FINAL_REVIEW_VERDICT = PASS

KNOWN_NONBLOCKING_P3 =
  P3-A · check_task_class.py:505-506
        B_REGRESSION_GUARD 的 candidate_oracle_status 将未测量候选 rc(124/127) 合并为 "FAIL"，
        与全仓其他处置不一致。该字段仅为 bound/reported 字段，不被 transition_verdict 读取，
        无法造成任何放行；仅在「B 记录同时声明 candidate_oracle_status 且某 FROZEN 面超时」的
        构造情形下产生一条虚假 ERROR 文案。不影响 V1 操作性条款（裁决逻辑已排除 124/127）。
        → 记录，不改；下次触及时修。
  P3-B · eligibility-schema-v2.md:523
        文档称 v2.2.0 的动机攻击「pinned by the LaunderingVariants test class」；
        但 r06 laundering 的「复算级」永久回归实际位于
        RecomputedTransition.test_r06_laundering_reproduction_is_refused(:662)，
        LaunderingVariants(:826) 的六变体为 shape/identity 拒绝，并非该复算回归。
        文档定位措辞过时。
        → 记录，不改；Freeze v2 或下次编辑该文件时校正。

N2_1_STATUS        = CLOSED

FREEZE_CHANGED     = NO
TASK_SET_CHANGED   = NO
SCORING_CHANGED    = NO
ROUTE_CHANGED      = NO
TREATMENT_CHANGED  = NO
H2_R2_EXECUTED     = NO

FREEZE_V2_HANDOFF:
  FZ2_1 (Eligibility validator ownership)
        disposition：eligibility validator 成为 PRE-FREEZE MECHANICAL GATE，
        不是 worker runtime gate：
            candidate task → eligibility validation → admitted corpus → Freeze v2
        Freeze v2 完成后，worker 执行过程不重新决定 task eligibility。
        本项必须承载 Finding-1 残留：Finding-1（acceptance 须观察谓词 / discriminator）
        已由 validator 复算机制机械化（F6 显式 NOT ENFORCED 条款代替人工评审），
        不得降级为纯文档说明，也不得推迟到 Freeze v2 人工评审。
  FZ2_2 (Old C2 language)
        删除/替换字面 C2「baseline must be green」。
        Freeze v2 authority 应引用 Eligibility Schema v2 类语义：
            A_REPAIR:        frozen attributable FAIL → PASS
            B_REGRESSION_GUARD: PASS → controlled mutation FAIL
        不得重新引入 C2∧C3 互斥定义。
  FZ2_3 (Aggregate set single source of truth)
        禁止同时手维护 counts_toward_h2_aggregate 与 aggregate_set 两个独立 truth source。
        定义单一机械 owner：
            aggregate_set = derive(
              eligibility records
              where request_status == VALID
              AND admitted_by_freeze == TRUE )
        其余计数全部由它推导。
  FZ2_4 (t02 disposition)
        t02 不得为了凑样本被「救活」：ruff.toml 当前属 worker scope，
        把它移为 framework-frozen oracle 会改变任务身份 / treatment boundary。
        默认：t02 = NOT_ADMITTED_CURRENT_REVISION。
        若未来确有「externally frozen ruff configuration」设计，
        必须建立 NEW TASK IDENTITY / NEW REVISION 并重新 measurement/eligibility/freeze，
        不得把旧 t02 静默改写为 eligible。

TREE_NODES_TOTAL   = 19
CURRENT_NODE       = N2 — H2 Lazy Skill / Progressive Disclosure
CURRENT_NODE_SUBSTATE = N2.1 Eligibility Schema Revision CLOSED
NEXT_NODE          = N2 — H2-R2 Freeze v2 preparation

GIT_LOCATION       = branch experiment/v1.2-h2-eligibility-schema @ 95985d2 (clean, pushed)
```

---

## Round-9 裁定 10 项要求 — 满足性追踪

| # | 裁定要求 | 状态 | 证据 |
|---|---------|------|------|
| 1 | 走 B：validator 独立从钉死仓内 corpus/evidence 复算类所需状态转移 | ✅ | `recompute_transition()` / `transition_verdict()`，code 处 A_REPAIR 取 discriminating、B 取 biting |
| 2 | 禁止新增 self-declared eligibility 字段 | ✅ | schema v2.8.0 未增任何 self-declared 资格字段；class/class_requirements/reject_triggers/disclosures/round_admission 仅承载，不复算 |
| 3 | A_REPAIR 须 BASE=FAIL→CANDIDATE=PASS | ✅ | `test_positive_control_reaches_the_discriminative_predicate` 实测 `base_rc=1 cand_rc=0`（r02） |
| 4 | B_REGRESSION_GUARD 须 BASE=PASS→CONTROLLED_MUTATION=FAIL | ✅ | B 取 biting（mut_rc FAIL）；无 bite ⇒ `MUTATION_DOES_NOT_BITE` 拒绝 |
| 5 | record 字段不能替代复算 | ✅ | 裁决只读真值，validator 以复算事实为准；声明与复算不符一律 ERROR |
| 6 | BASE==CANDIDATE 或非可执行 ⇒ fail-closed | ✅ | `BASE_EQUALS_CANDIDATE` / `NO_DISCRIMINATING_ACCEPTANCE` / `MUTATION_DOES_NOT_BITE` 拒绝路径 |
| 7 | r06 laundering 复现为永久回归 | ✅ | `test_r06_laundering_reproduction_is_refused`（默认跑，非条件）；r06 以 MUTATION_DOES_NOT_BITE 拒绝 |
| 8 | 阳性对照须到达判别谓词 | ✅ | 见 #3；真实子进程测量（非 mock）打印 `TRANSITION ... FAIL_TO_PASS ... DELTA_ADDED` |
| 9 | Finding-1 不得降级为文档 / 不得推迟到 Freeze v2 人工评审 | ✅ | 复算机制机械化 Finding-1；F6 显式 NOT ENFORCED（见 schema §3.1 NOT ENFORCED 块）；FZ2-1 承接残留 |
| 10 | Round-10 仅在真实 P2 时允许；修复后 P0=P1=P2=0 ⇒ 关闭，无 Round 11 | ✅ | 本复核（#10）VERDICT=PASS，P0=P1=P2=0；2 个非阻塞 P3 仅记录 |

---

## Round-10 复核（隔离上下文验证评审）摘要

- **VERDICT**: PASS · REVIEWED_BASE `95985d2…` · branch `experiment/v1.2-h2-eligibility-schema` · clean=Y · remote_pin 一致。
- **GATES**: 见上 FULL_GATES。
- **Scoped item**: V1(F1 关闭) / V2(F2 关闭) / V3(F4) / V4(F5) / V5(F6 文档 NOT ENFORCED) / V6(回归扫描) 全部 PASS。
- **V7 新攻击**: `B_REGRESSION_GUARD laundered onto r02's A-shaped pair` —
  期望 `MUTATION_DOES_NOT_BITE` / `NO_FROZEN_ACCEPTANCE`，实际 fail-closed：
  ```
  ERROR … declared mutation_oracle_status='FAIL' but the recomputation gives 'PASS'
  ERROR … declared mutation_touches_target_predicate=True but recomputation gives False
  ERROR … B_REGRESSION_GUARD state transition not supported by execution (MUTATION_DOES_NOT_BITE) …
  TASK_CLASS_VERDICT = FAIL records=1 errors=3   (no valid_requests)
  ```
  结果 PASS（fail-closed，且由 FROZEN 面真实测量 rc 对裁决）。
- **FINDINGS**: 无 P0/P1/P2；P3×2（见 KNOWN_NONBLOCKING_P3）。全程只读，未改 worktree。

---

## 边界与未做事项（显式声明）

- 本节点不 merge；分支保持 `experiment/v1.2-h2-eligibility-schema` 未合并。
- 未实现 Freeze v2（指令 PART 13 明确要求「DO NOT IMPLEMENT YET」），仅交付 FZ2-1..4 handoff。
- 未进入 H2-R2 execution（指令 PART 15：`H2_R2_EXECUTED = NO`）。
- 未触碰 TREE_LEDGER 结构性字段（N2 仍 ACTIVE 为全节点态；N2.1 子态见 CURRENT_NODE_SUBSTATE，记录于本报告）。
- 未因 P3 改动任何代码或 schema 文档（指令 PART 12 停止条件）。
- 发现性快照：四冻结文件 byte-identical to `1b82a53f9…`；变更集 16 路径全部 under `experiments/`。
