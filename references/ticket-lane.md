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

```
INPUTS / OUTPUTS / PRECONDITIONS / POSTCONDITIONS
HARD_INVARIANTS / VALID_SUCCESS_CASES / FAIL_CLOSED_CASES
ALLOWED_FALLBACKS / FORBIDDEN_FALLBACKS
IDENTITY_DEPENDENCIES / PERSISTENCE_DEPENDENCIES
OWNERSHIP / OUT_OF_SCOPE
```

- 禁止静默把更富合同降级为方便的局部启发式；实现若改变 success/failure/valid/complete/identity/authority 的含义 → STOP（RULES R6）。
- LOW 票至少：INPUTS / OUTPUTS / OUT_OF_SCOPE 三行。

## 4. Counterexample-first TDD

链条：`CONTRACT → COUNTEREXAMPLES → RED → IMPLEMENT → GREEN → REFACTOR → REGRESSION`。

**证据标准**：
- `TEST_FILE_EXISTS != TDD_RED_PROVEN`；RED 必须由目标反例断言触发（MODULE_NOT_FOUND / harness 损坏不算 RED）；
- 证据区分 `TEST_FIRST` 与 `COUNTEREXAMPLE_SPECIFIC_RED`；
- 最低数量（仅对**承载正确性行为**的票）：MEDIUM ≥3；HIGH（持久化/状态/身份/安全/编排）≥5；LOW 无强制（有合同就必须有对应正/反测试）。

**高价值反例类目**（瞄准"看起来合理、过了显眼测试、仍违反合同"的实现）：
合法解被拒；非法输入变成功；约束被静默忽略；缺身份被当可复用；陈旧产物被接受；空结果当成功；重复身份破坏集合语义；malformed-but-coercible 被接受；排序/并列/边界失效；一项满足两个不同要求；合法上游输出违反下游合同；caller 控制数据泄入日志/产物；默认值掩盖缺失必需状态；实现越入他票权威。

**防伪**：禁止新增 skip、删断言、缩范围伪造绿灯。

## 5. 实现与自审

- `/implement` 是 MEDIUM/HIGH 实质实现的默认强制工程入口（LOW 不强制）；`/tdd` 在正确性行为存在时强制（不可测需客观理由）；`/simplify` 只在 GREEN 之后且不得改行为/合同。
- skill 使用声明需可核验证据（被实际调用/读取），否则报 `UNVERIFIED`。
- 自审（/code-review 等）只是 worker 证据；**当独立评审 gate 存在时**（AGENTS §3 风险矩阵）不满足该 gate（RULES R4）。

## 6. Repair

- 只修 reviewer 指出的 blocker + 同 scope 内明确真实缺陷；append-only commit（RULES R5）。
- 新 SHA 触发失效链；delta 评审协议见 git-ci-integration.md §5。
- 修复轮次受 REPAIR_VALUE gate 与 budget 默认约束（review-and-repair-saturation.md §3）。
