# H2 protocol — Lazy Skill / Progressive Disclosure（冻结版；非 canonical）

> 本文件 = V1.2 H2（节点 N2）实验协议，自 N6.5 §1 冻结协议具体化而来。
> **在第一条 valid run 之前冻结**（freeze = 本目录首次进入默认分支的评审 + merge）。
> 冻结后本文件与 `carriers/`、`routes-h2.json`、`task-registry.json`、`scoring-rubric.md`
> 均不得改动；如必须改 ⇒ 已有 run 全部 invalidated，重开 round（见 §9）。
> 结论词汇仅限 `{DISCLOSURE_SAFE, DISCLOSURE_HAS_COST, INSUFFICIENT_EVIDENCE}`；
> **禁止** PROMOTE / V1.2_READY / CANONICAL_ADOPTED（promotion 属 N9）。

## 1. 核心问题与假设

```text
CORE_QUESTION = 多少治理 / Skill 内容可以离开 HOT，只在任务相关时通过 progressive
                disclosure 加载，而不降低最终正确性？
H2-H1（可falsify形态） = 把 §3/§4/§5 的细节下沉到 WARM 并只留指针，任务正确性不变。
  FALSIFIED_IF = 变体臂出现 ≥1 条对照臂捕获的高价值 finding 未被捕获，
                 且该 finding 的内容位于被下沉/未携带的文本里。
                 （判定边界已写死在 scoring-rubric.md §2–§3，开跑前冻结）
H2-H2（可falsify形态） = 路由可达性是下沉可行性的唯一硬前提。
  FALSIFIED_IF = 出现"路由存在但内容不足"（找到了文件但里面没有所需语义）
                 → 说明需要 anchor 级检查。（H2 对这点只记观察，不建新机制）
```

## 2. 臂定义（两臂唯一自变量 = 治理/Skill 内容的投递方式）

```text
CONTROL_H2  = 当前完整 HOT 治理可达（placed CODEBUDDY.md = 当前 AGENTS.md 逐字全文 + placed
              当前 RULES.md；不额外加资料、无路由机制）
VARIANT_H2  = 精简 HOT 载体（carriers/H2_LEAN_BOOTSTRAP.md → placed CODEBUDDY.md，同槽位；
              只保留 map / invariants / routing pointers；AGENTS §3/§4/§5 与 §0 框架细节下沉 WARM）
              + placed 当前 RULES.md（与对照臂同版）+ WARM 按路由从 placed H2_WARM/ 副本加载
```

**时代同版声明（v5）**：两臂在**所有** run（含 t01–t04 历史 base）都获得**当前时代**的
（a）guidance 载体（**同槽位** `CODEBUDDY.md`——控制 runtime 的自动 guidance 选择在两臂一致）、
（b）RULES.md 副本、（c）路由可达的 WARM owner 副本（`H2_WARM/`，源列表 = routes-h2.json
S3 destinations）。历史 base 只改变任务的代码状态；治理材料全部来自同一冻结材料快照
（receipt 记 `materials_commit`；见 `variant-manifest.json#carrier`）。

**WHAT LEFT HOT / REMAINED / MOVED TO WARM**（结构化声明见 `variant-manifest.json`）：

```text
REMAINED_IN_VARIANT_HOT = 权威链 / 证据路由表 / 风险级骨架 / 禁令集 / 安全地板 N1–N8 /
                          路由表本体（指针）/ 停机条件 / 机械门列表
MOVED_TO_WARM（细节，载体不再携带） = 票生命周期与 DAG 细节（→ ticket-lane.md）/
                          Stage 与分解 gate 细节（→ execution-stage.md）/
                          CodeGraph 三模式与生命周期细节（→ codegraph-grounding.md、
                          project-continuity-contract.md）/ 状态与恢复细节（→
                          project-state-persistence.md）/ 评审与修复预算细节（→
                          review-and-repair-saturation.md）/ CI 集成细节（→
                          git-ci-integration.md）/ 静态门框架细节（→
                          static-analysis-and-code-intelligence.md）/ 记忆闭环细节（→
                          engineering-memory.md）/ Skill 路由细节（→
                          skills-and-model-routing.md）
NOT_CARRIED_BY_VARIANT（对照组全读面的一部分）= AGENTS §6–§10 与 §0 框架的**正文**；
                          其操作性内容由上述 WARM owner + RULES.md 承接；
                          归属判定见 scoring-rubric.md §7（类别 iii/iv）。
```

### 2.1 投递机制（P1/P2 的机械部分）

每个 run 的投递由 harness 机械完成（`harness/prepare_run.sh`），不是 prompt 散文：

```text
投放前 harness 断言 worktree 根部投放槽位（CODEBUDDY.md / H2_RULES.md / H2_AGENTS.md / H2_WARM）
均不存在（存在 ⇒ RUN_INVALID: DELIVERY_SLOT_CONTAMINATED）。
两臂公共（同槽位、同版；治理材料全部取自冻结材料快照）：
  · CODEBUDDY.md = 本臂的 guidance 载体（control: 当前 AGENTS.md 逐字全文 + 薄头/尾；
    variant: 冻结的 lean 载体）；receipt 记 carrier_kind + carrier_hash（sha256）。
  · H2_RULES.md = 当前 RULES.md 全文副本（receipt 记 sha256）。
  · H2_WARM/ = 当前时代的路由 WARM owner 副本（源 = routes-h2.json 的 S3 destinations，
    单一来源；receipt 记 warm_bundle_sha256 = 排序后 "dest sha256" 行集合的 sha256）。
collection 侧（collect_run.sh）重新核 hash（载体 / H2_RULES / H2_WARM bundle）并断言：
  run 树自带 AGENTS.md/RULES.md 未被改动；`.h2-telemetry.log` 存在、非空且含 ≥1 条格式
  合法行（缺失/空 ⇒ **不得合成空日志**，直接记 INVALID）。任何 FAIL ⇒ 脚本 exit 3。
```

run 合同（两臂同构，差异只在 `BOOTSTRAP_DELIVERY` 槽位）冻结于
`harness/worker-brief-template.md`；报告模板冻结于 `harness/worker-report-template.md`
（同一生成路径、同结构字段 —— P4）。

### 2.2 worker 禁看清单（防污染）

run worker 不得读取：其他 run 的目录、`runs/` 注册表、`task-registry.json` 的
`expected_outcome`、本 protocol 的 §8/§11、历史答案（git log 中该任务的候选 commit）。
worker 只能获得：任务文本（由 run 合同给出）、自己的 worktree、自己的载体投递面、
工具访问、验收合同的**存在**（不含 oracle 内容）。

## 3. 任务集与复制（单位与分配已冻结）

任务集 = `task-registry.json`（6 个：t01–t04 逐字复用 H1 注册表；n01/n02 为带 provenance
的真实新任务）。复制设计：

```text
REPLICATION_UNIT = task-shape × arm（见 task-registry.json#replication）
shapes: FIX{t01×1,t02×1} / HIGH-STATE{t03×2} / HIGH-REVIEW-EVIDENCE{t04×2} /
        REVIEW-REPAIR{n01×2} / DIAGNOSIS-SKILL{n02×2}   （每 shape 每臂恰为 2）
N_PER_ARM_TOTAL = 10；N_TOTAL_RUNS = 20
```

**执行顺序（冻结；臂序已对消 —— bot review「Counterbalance the arm execution order」）**：
同一任务内不固定"先对照后变体"；臂序在任务间交替、且在重复对之间**互换**：
block-1（每任务第 1 次）＝ t01:C,V；t02:V,C；t03:C,V；t04:V,C；n01:C,V；n02:V,C；
block-2（t03/t04/n01/n02 第 2 次）＝ t03:V,C；t04:C,V；n01:V,C；n02:C,V。
即：重复任务的两对臂序相反（C-first ↔ V-first 互换）；不可重复的 t01/t02 在任务间交替。
两 block 规则完全相同；任何环境中断都按 §8 注册，不得"重跑到好看为止"。

## 4. 运行机制

```text
每 run：
  1. harness/prepare_run.sh <RUN_ID> <ARM>   → 建 worktree、机械断言、投放载体、写 receipt
  2. fresh worker（独立 subagent，独立 episode；不得复用前一 run 的上下文）
  3. worker 按合同工作 + 就地维护 .h2-telemetry.log（格式见 §6）+ 写报告到指定路径
  4. harness/collect_run.sh <RUN_ID>         → 捕获（worker 违约 commit 时改取 base..worktree
     全量 diff）＋ 复核投放物与遥测（载体 / H2_RULES / H2_WARM / run 树 AGENTS/RULES 未动；
     遥测缺失/空不得合成）⇒ 任一 FAIL exit 3（fail-closed）
  5. harness/run_acceptance.sh <RUN_ID>      → 机械验收（EXEC 条目全跑、任一条 rc≠0 ⇒ exit 1；
     scope 谓词由 `check_scope.sh` 强制；t03 的 R2 扫描由 `run_release_scan_on.sh` 在候选
     副本内执行；t02 的 F841 正控由 `check_t02_gate_teeth.sh` 执行）
  6. 独立 auditor（fresh subagent）评审 artifacts（不看 worker 过程叙述中的自辩）
  7. 全部产物落盘（见 §7）；run 登记进 run-registry.md
```

worker 禁止 commit / push / 改 refs；只允许 worktree 内文件改动与测试运行。
环境故障（exit 137/139、网络、通道死亡）导致的中断 ⇒ 记 BLOCKED 或按 §8 判 INVALID，
**不得静默重跑**（重试 = 新的登记记录，且原因必须写进该 run 的 registry 行）。

## 5. P1–P7 Startability Gate（逐项证明，缺一即 PROTOCOL_NOT_STARTABLE）

| # | 要求 | H2 的机械证明 | 证据位置 |
|---|---|---|---|
| P1 | 执行目标机械绑定 | prepare_run.sh 断言 worktree 绝对路径存在 + `git rev-parse HEAD` == base_sha；worker 合同第 0 步再次自检并回报 `S4:<sha|MISMATCH>`；不匹配 = RUN_INVALID | `precondition/p1-p2-dryrun.txt` |
| P2 | 投递断言（v5） | prepare_run.sh 机械投放**同槽位** `CODEBUDDY.md`（control=当前 AGENTS 逐字全文 / variant=冻结载体）+ 同版 `H2_RULES.md` + `H2_WARM/` 副本；逐项 sha256 + warm_bundle_sha256 + materials_commit + model_tier 入 receipt；collection 再核（含遥测存在性；FAIL ⇒ exit 3） | `precondition/p1-p2-dryrun.txt` |
| P3 | 产物持久化 | 全部 run 产物写 `h2-runs/evidence/**`（持久工作区，非 /tmp）与 repo `runs/**`；worktree 位于 `h2-runs/worktrees/**` | protocol §7 + registry |
| P4 | 报告同构 | 单一模板 `harness/worker-report-template.md`；两臂投递块字段名相同（H2_RECEIPT 等）；抽取评估时对 findings 节做去臂化 | 模板文件 + §6 |
| P5 | 预注册评分 | 本协议 + `scoring-rubric.md`（含高价值边界、missed-guidance 三合取、结果计算）在首 run 前冻结 | 冻结 commit + hash |
| P6 | 路由可达前置 | 在 6 个不同 base 上（H2 base = n02 base = 9494de8；另 5 个为更早的 task base）用 N8 validator 跑 `routes-h2.json`（33 条）；另在 H2 base 复跑 N8 冻结 `routes.json`（22/22）。任何 **H2 载体行** 失败 ⇒ PROTOCOL_NOT_STARTABLE | `precondition/p6-*.txt` |
| P7 | 门完整性 | 正控四件：t01 适用测试在 base 必红；ruff 注入 F841 必红（(d) 同时是 #45 的承重方向证明）；validate_public_release 注入机器路径必红；validate_governance 注入违规必红。无法证明承重的门 ⇒ 其 PASS 不得计为高置信证据（预先声明：ruff 的**掏空方向**已知不可靠（#45），本实验只用其**注入必红方向**） | `precondition/p7-*.txt` |

## 6. 遥测（PART 11；三档不得混同）

worker 在 worktree 根部就地维护 `.h2-telemetry.log`，**事件发生时即时追加**：

```text
READ  <FULL|PARTIAL|GREP>  <repo-relative path>
ROUTE <route_id|n/a>       <target>       <LOADED|MISSING|SKIPPED>
SKILL <name|none>          <LOADED|UNAVAILABLE|NOT_REQUIRED|WRONG|NONE>
```

报告 §H 汇总：FILES_FULLY_READ / FILES_PARTIAL_READ / FILES_GREPPED_FOUND /
ROUTES_USED / SKILLS_LOADED / ESCALATED_LOADS / SKILL_FALLBACK_REPORTED /
WALL_CLOCK=NOT_OBSERVABLE / TOKEN_USAGE=NOT_OBSERVABLE。
投放文件（`H2_RULES.md` / `CODEBUDDY.md` / `H2_WARM/**`）的读取按同规则记录。
另：`.h2-telemetry.log` 缺失或空 = 证据缺失 ⇒ collect 判 INVALID（不得合成空日志；bot review R5-6）。
M3 口径 = **完整读取**（非 grep 命中、非部分读取）；DISCOVERED/PARTIAL/FULLY_LOADED 分记。

## 7. 产物位置（PART 21）

```text
repo（tracked，随本轮 PR 合入；提交前过 R2 扫描，必要时以 <WORKSPACE_ROOT> 脱敏并标注）：
  experiments/v1.2/h2-lazy-disclosure/runs/<RUN_ID>/run.json         # 状态、base、arm、receipt 摘要
                                              /report.md             # worker 报告（同构模板）
                                              /telemetry.json        # 从 .h2-telemetry.log 派生
                                              /acceptance.txt        # 机械验收输出
                                              /review.md             # auditor 结论（含 FINAL_CORRECTNESS）
持久工作区（非 /tmp，本机持久）：<H2_RUNS_ROOT>/worktrees/<RUN_ID>/   # run 的 git worktree 本体
                              <H2_RUNS_ROOT>/evidence/<RUN_ID>/      # diff.patch、原始测试输出、receipt.json 原件
```

## 8. 无效 run 注册（PART 19；保留、登记、不纳入统计、禁止 silent rerun）

```text
原因枚举 = wrong worktree / wrong base / carrier not delivered or hash-mismatched /
delivery-or-evidence recheck FAIL（含遥测缺失或空——不得合成）/ delivery slot contaminated /
route precondition false / worker crashed before meaningful execution /
acceptance harness defect / cross-arm contamination / report not produced /
model tier mismatch / task-text mismatch（防走样）。
每条：RUN_ID / ARM / TASK_ID / INVALID_REASON / DISCOVERY_TIME / ARTIFACT_PATH。
```

## 9. 冻结与不可变（PART 5 / PART 20）

```text
VARIANT_HASH / TASK_SET_HASH / SCORING_HASH / ROUTE_MANIFEST_HASH = 见 variant-manifest.json
（在 freeze commit 中写入；此后逐 run 的 receipt 记录全部投放物 sha256（含
warm_bundle_sha256）+ materials_commit + model_tier）。
VARIANT_CHANGED_AFTER_FREEZE = NO 的判定 = ①仓库内冻结文件 hash 未变（material tests 强制，
测试文件中另有**同值字面量**互为锚定）；②全部 valid run 的 receipt 记录与 freeze 一致
（variant: carrier sha256 == VARIANT_HASH；control: H2_AGENTS/H2_RULES 与 receipt 一致）。
若必须修 variant：ROUND_INVALID，已跑 run 全部作废（保留登记），改协议后开新 round。
```

**锚定语义（bot review「Anchor freeze hashes outside the mutable freeze set」的处置）**：
manifest 的四个 hash 与 material tests 中的同值字面量互相钉住 —— 改动任一冻结文件必须同时
改 manifest 与测试字面量，否则测试红。每个 run 的 receipt 记录 `materials_commit`（投放源
提交）。冻结面的**最终**锚 = 其进入默认分支的 merge commit（merge 后在 `results.md §8`
记录）。仓库内任何锚只能提供"单点或漏改会被发现"的强度，不能提供不可篡改；不可篡改性
的来源是 git 历史 + PR 评审，这里如实区分。

## 10. PART 22 — 每个 task base 的路由预条件

```text
对 6 个 task base（c08f6f8 / 015780b / af4df6a / e1da154 / 0a180fe / 9494de8）逐一跑
routes-h2.json（33 条）。H2 载体行（S3）设计为 base-universal（10 个 references 交集 +
skills/README.md），**不允许**出现"该任务实际需要的 WARM 路由在其 base 上不存在"。
S1/S2 行的历史悬空（e1da154/af4df6a 的 LEAN-07/LEAN-12/AGENTS-03；015780b 的 LEAN-12/
AGENTS-03）属 N8 冻结已知事实、且不是 H2 载体行 ⇒ 记 HISTORICAL_BASE_ROUTE_UNSATISFIED
（N8-already-recorded），不构成 H2 预条件失败，也不得读作 variant failure。
冻结规则：若出现**任务需要**的悬空行 ⇒ 该任务 invalid for H2（登记 + 从结果剔除），
或使用本 manifest 中已冻结的 base-universal 等价目标；禁止把未来文件注入过去 base。
```

## 11. PART 23 — #46 机制不得被绕过

本实验不得弱化 N8 validator 的 5×P2 加固语义。H2 材料测试须复证：
directory target → DESTINATION_NOT_A_FILE；unknown/misspelled key → MALFORMED；
unhashable surface → MALFORMED（非 TypeError）；零路由 → NO_ROUTES_DECLARED（永不 PASS）；
wrong base → BASE_UNRESOLVABLE；missing target → DESTINATION_MISSING。
（复证 = 在 H2 测试文件中对同一 validator 重跑 hostile fixtures，见 tests。）

## 12. 收尾 / 合并门（PART 30–32）

```text
合并门前（对最终 candidate SHA）必须枚举并读取全部评审渠道：
  fresh 独立 subagent 评审（exact SHA） / GitHub Codex bot（若再现） / PR inline threads /
  PR conversation comments / configured CI。
ALL_REVIEW_SOURCES_QUIESCENT = YES 且 LATEST_CODEX_REVIEW_SHA == FINAL_CANDIDATE_SHA
（若 bot 未在最终 SHA 出评审 ⇒ 明示"bot 无该 SHA 评审"而非"无 finding"）。
任何修复产生新 SHA ⇒ 旧 PASS 作废，重跑 exact-SHA 门。
closure-ledger PR 只记录后验事实（merge SHA / post-merge CI），不改实验结果。
```

## 13. 不做清单（本实验的边界）

```text
不改 canonical（AGENTS.md / RULES.md / references 未动；CANONICAL_CHANGED = NO）
不实现 #45（H4/N7 的标的；n02 只诊断）
不触碰 H3（detector、COLLECTING 状态都不动）
不进入 H4 / H5 / N9（H2 结束后停在 N2 CLOSED）
不引入 daemon / 数据库 / 新服务；不改 CI 语义；实验材料不进 canonical CI 测试面
```

## 14. 停止条件

```text
STOP_WHEN = 计划内 20 个 run 全部完成登记（valid 或 invalid）、每 shape 有效 n/arm 达标
（或不足的原因按 §8/§9 如实登记）、两臂都有机械可核的终态（验收 + 评审证据）、
结果按 scoring-rubric.md §9 计算完毕并入仓（PR 合并）。
禁止停止条件："跑到结论好看为止"。
```
