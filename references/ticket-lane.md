# REF: Ticket Lane — 单票生命周期、合同抽取与反例 TDD

> Canonical owner: AGENTS.md §3。风险矩阵在 AGENTS §3；本文件是**D 层默认**执行细节（仓政策可覆盖，记录 OVERRIDE）。

## 1. Lane 契约（默认；仓政策可定义例外）

```
ONE COHESIVE TICKET
ONE BRANCH
ONE ISOLATED WORKTREE（独立目录 / 独立的【查询+证据】生命周期——不是独立图库所有权，见 codegraph-grounding.md §2）
ONE ACTIVE WRITER（同一 reviewed candidate 不得并发变异；写者交接 = 前写者停止 → fresh fetch → 核验 remote tip → 重建状态 → 从 exact tip 继续）
```

- worktree 基于当前 remote master（或票声明的 authorized base SHA）创建；记录 `LANE_BASE_SHA`。
- 产物回写仅三类：feature branch commits、证据文件（lane 目录内）、tracker 更新（集成后）。

## 2. 读权威与 Relevant Surface Manifest

开工前构建（CodeGraph 辅助；不可用时手工，见 grounding §4）：

```
upstream producers / validators & canonicalizers / direct callers /
downstream consumers / persisted artifacts / state owners /
identity & provenance owners / error & failure propagation /
security & privacy propagation / sibling analogous modules /
adjacent ticket authority boundaries / stale-invalidation deps
```

存在未知的重大仓库关系时不开始实质实现（先查清或 STOP）。LOW 票可裁剪为 surface 摘要。

## 3. Contract Extraction（MEDIUM/HIGH 必备字段块）

既有字段块（EXTEND 保留，不删除）：

```
INPUTS / OUTPUTS / PRECONDITIONS / POSTCONDITIONS
HARD_INVARIANTS / VALID_SUCCESS_CASES / FAIL_CLOSED_CASES
ALLOWED_FALLBACKS / FORBIDDEN_FALLBACKS
IDENTITY_DEPENDENCIES / PERSISTENCE_DEPENDENCIES
OWNERSHIP / OUT_OF_SCOPE
```

- 禁止静默把更富合同降级为方便的局部启发式；实现若改变 success/failure/valid/complete/identity/authority 的含义 → STOP（RULES R6）。
- LOW 票至少：INPUTS / OUTPUTS / OUT_OF_SCOPE 三行。
- 字段按**边界是否变化**触发，不按票字数或仅按 LOW 标签豁免；不要求所有票填写所有字段，不适用字段可 `N/A`（reachability 适用性另有判定规则，见 3.1.4）。

### 3.1 Seam 合同的两个分区（设计/权威要求 vs 关闭/观测证据）

seam 合同块由**两个显式标注、互不混写的分区**组成。本文件是 seam 合同字段的 canonical 声明面（canonical owner = AGENTS.md §3/§4）；**不新建第二 seam 权威文件、不新建 seam-map surface、不新增共享 enum**。

- 分区 (1)（设计/权威要求）：表达**要求什么**，拆票前由 authority/design 侧判定并**冻结**。
- 分区 (2)（关闭/观测证据）：记录**实际观测到什么**，实现完成后由执行侧产生。

两个分区之间的信息流是**单向**的：

```
PARTITION (1) IS FROZEN BEFORE TICKETING
PARTITION (2) ONLY FILLS THE SLOTS DECLARED BY (1)
CLOSURE_EVIDENCE_CAN_NEVER_REWRITE_A_REQUIREMENT
```

- 分区 (2) 的记录**只填充**分区 (1) 声明的槽位；若发现 (1) 的要求本身有误 → 走 authority / spec 变更流程，**不得**在关闭阶段就地改写要求。
- 分区 (1)/(2) 的字段名**不得同名**，也不得近似到需要 implementer 猜测；**禁止改名、禁止发明别名、禁止新增两个分区之间的同义词**。

#### 3.1.1 (1) DESIGN / AUTHORITY REQUIREMENTS —— 拆票前冻结

```
SEAM_ID / AUTHORITY_REF / CONTRACT_VERSION
PRODUCER / CONSUMER
SEMANTIC_OWNER / IDENTITY_OWNER / PERSISTENCE_OWNER / RETRY_OWNER / ERROR_OWNER
INPUT_CONTRACT / OUTPUT_CONTRACT
SYNC_OR_ASYNC / AWAIT_REQUIREMENT / LIFECYCLE_REQUIREMENT
LEGAL_STATES / ILLEGAL_STATES / FAIL_OPEN_OR_FAIL_CLOSED
MUST_FIELDS / MUST_NOT_FIELDS
EXPECTED_PRODUCTION_CALLER            # requirement：必须存在生产调用者（不是观测）
TEST_CALLER
EXPECTED_PRODUCTION_EFFECT            # requirement：期望的生产效果（不是观测）
REAL_SHAPE_FIXTURE_OR_ADAPTER
SEAM_COUNTEREXAMPLES                  # 反例定义（requirement，不是执行结果）
REACHABILITY_APPLICABILITY            # REQUIRED | N/A
REACHABILITY_APPLICABILITY_REASON     # 仅当 APPLICABILITY = N/A 时必填
REACHABILITY_APPLICABILITY_ACCEPTANCE_REF
                                      # 仅当 APPLICABILITY = N/A 时必填；
                                      # 指向 reviewer/integrator 的接受记录（引用槽位，不是结论）
REACHABILITY_REQUIREMENT              # 该 seam 必须被真实入口到达的规范声明
REACHABILITY_PROOF_OWNER              # 谁在关闭时提供证据（角色，不是结论）
RED_EXECUTION_OWNER                   # 谁在票内执行 RED（角色）
```

**唯一声明点规则**：`EXPECTED_PRODUCTION_EFFECT` HAS EXACTLY ONE NORMATIVE DECLARATION POINT —— 即上方分区 (1) 字段清单内的那一条。其它一切位置（本文件别处、其它 `references/*.md`、ticket 正文、测试断言、消费方文档）**只引用**该字段，**不得重复声明**同一规范事实。

```
# 声明点判定（机械可查）
DECLARATION = 该字段名作为字段条目出现在分区 (1) 的字段清单代码块内
REFERENCE   = 其它任何位置的提及（prose / 配对表 / 测试断言 / 消费方文档）
```

#### 3.1.2 (2) CLOSURE / OBSERVATION EVIDENCE —— 实现完成后产生

```
REAL_ENTRYPOINT / PRODUCTION_CALL_CHAIN
OBSERVED_PRODUCTION_EFFECT            # 实际观测到的生产效果（引用分区 (1) 的对应要求字段）
PRODUCTION_CALLERS                    # 实际生产调用者集合（可为空集）
RUNTIME_REACHABLE / EVIDENCE_REF      # 观测结论 / 证据引用
```

- 本分区**只声明 observation 字段**；不声明任何 requirement 字段，不复述 3.1.1 的唯一声明点规则，不新增要求语义。

#### 3.1.3 冻结配对表（design ↔ observation）

```
EXPECTED_PRODUCTION_EFFECT          ->  OBSERVED_PRODUCTION_EFFECT
EXPECTED_PRODUCTION_CALLER          ->  PRODUCTION_CALLERS
REACHABILITY_REQUIREMENT            ->  RUNTIME_REACHABLE
```

- 三个配对必须一眼可辨；**不得**把任一配对坍缩成一个名字，**不得**在两个分区之间共享字段名。
- 设计/观测同名或近似名（CE-29）→ 拒绝；冻结配对表是唯一解药。

#### 3.1.4 适用性判定规则（`REACHABILITY_APPLICABILITY`）

```
REACHABILITY_APPLICABILITY = REQUIRED | N/A
RUNTIME_REACHABLE          = TRUE | FALSE
REQUIRED  -> RUNTIME_REACHABLE 必须由分区 (2) 的关闭证据证明；无合法生产调用路径 => FALSE
N/A       -> 必须同时填写 REACHABILITY_APPLICABILITY_REASON 与 REACHABILITY_APPLICABILITY_ACCEPTANCE_REF
FAIL-CLOSED  MISSING_OR_EMPTY(REACHABILITY_APPLICABILITY_REASON)         => PROCESS_AS REQUIRED
FAIL-CLOSED  MISSING_OR_EMPTY(REACHABILITY_APPLICABILITY_ACCEPTANCE_REF) => PROCESS_AS REQUIRED
FAIL-CLOSED  WORKER_SELF_GRANTED_N/A                                      => CONTRACT_VIOLATION
FAIL-CLOSED  DUPLICATE_NORMATIVE_DECLARATION                              => CONTRACT_VIOLATION
FAIL-CLOSED  PARTITION_FIELD_NAME_COLLISION                               => CONTRACT_VIOLATION
```

- `REACHABILITY_APPLICABILITY` 合法值域只有 `REQUIRED | N/A`；`UNKNOWN` 不得冒充已冻结的适用性取值。
- `REQUIRED`：`RUNTIME_REACHABLE` 必须由分区 (2) 的关闭证据证明；无合法生产调用路径 → `RUNTIME_REACHABLE = FALSE`。
- `N/A`：**必须同时**具备 `REACHABILITY_APPLICABILITY_REASON`（为什么该 seam 不涉及 reachability，如纯文档、无生产入口语义变化）与 `REACHABILITY_APPLICABILITY_ACCEPTANCE_REF`（指向 reviewer / integrator 接受记录的引用槽位，不是结论）。
- **worker 不得单方自授 `N/A`**（`N/A` 来自合同适用性判定，不是 worker 快捷豁免）；任一槽位**缺失或为空** → fail closed，按 `REQUIRED` 处理。
- `RUNTIME_REACHABLE` 是**观测轴**，合法域固定为 `TRUE | FALSE`，与 `REACHABILITY_APPLICABILITY`（判定轴）不是同一个量。
- 纯文档等无边界的票可整体 `N/A`（须双槽位齐备）。

## 4. Counterexample-first TDD

链条：`CONTRACT → COUNTEREXAMPLES → RED → IMPLEMENT → GREEN → REFACTOR → REGRESSION`。

**证据标准**：
- `TEST_FILE_EXISTS != TDD_RED_PROVEN`；RED 必须由目标反例断言触发（MODULE_NOT_FOUND / harness 损坏不算 RED）；
- 证据区分 `TEST_FIRST` 与 `COUNTEREXAMPLE_SPECIFIC_RED`；
- 最低数量（仅对**承载正确性行为**的票）：MEDIUM ≥3；HIGH（持久化/状态/身份/安全/编排）≥5；LOW 无强制（有合同就必须有对应正/反测试）。

**高价值反例类目**（瞄准"看起来合理、过了显眼测试、仍违反合同"的实现）：
合法解被拒；非法输入变成功；约束被静默忽略；缺身份被当可复用；陈旧产物被接受；空结果当成功；重复身份破坏集合语义；malformed-but-coercible 被接受；排序/并列/边界失效；一项满足两个不同要求；合法上游输出违反下游合同；caller 控制数据泄入日志/产物；默认值掩盖缺失必需状态；实现越入他票权威。

**防伪**：禁止新增 skip、删断言、缩范围伪造绿灯。

### 4.1 Test-first defect closure（缺陷闭环，D4）

worker 或 reviewer 发现**真实可达缺陷**时，先问：`CAN_THIS_FAILURE_BE_CAPTURED_AS_A_STABLE_TEST?`

- **YES（默认路径）**：写/强化回归测试 → 观察失败（适用时）→ 修复 → 观察 PASS → **测试随修复保留**。可靠的回归知识住在测试里，不住在任何人的记忆里。
- 不为此制造低价值测试：无合同意义的实现细节；已被 formatter/linter 机械强制的行为；低价值合成态（REPAIR_VALUE 已裁定的 long-tail）。
- 测试应编码**有意义的行为知识**（回归、边界、fail-closed、producer/consumer 合同、持久化、身份/provenance、已知反例）。

## 5. 实现与自审

- `/implement` 是 MEDIUM/HIGH 实质实现的默认强制工程入口（LOW 不强制）；`/tdd` 在正确性行为存在时强制（不可测需客观理由）；`/simplify` 只在 GREEN 之后且不得改行为/合同。
- skill 使用声明需可核验证据（被实际调用/读取），否则报 `UNVERIFIED`。
- 自审（/code-review 等）只是 worker 证据；**当独立评审 gate 存在时**（AGENTS §3 风险矩阵）不满足该 gate（RULES R4）。

## 6. Repair

- 只修 reviewer 指出的 blocker + 同 scope 内明确真实缺陷；append-only commit（RULES R5）。
- 新 SHA 触发失效链；delta 评审协议见 git-ci-integration.md §5。
- 修复轮次受 REPAIR_VALUE gate 与 budget 默认约束（review-and-repair-saturation.md §3）。

## 7. Live 状态持久化（P1）

Ticket/Lane 的活跃状态按 `references/project-state-persistence.md` §2–3 在**有意义转换点**持久化到 GitHub（Issue/PR/tracker：status/owner/SHA/评审/CI/blockers/next legal action）；离线时 `REMOTE_STATE_SYNC = DEFERRED` 且不声称远端已同步。票结束或会话离开前执行 STATE_FLUSH。
