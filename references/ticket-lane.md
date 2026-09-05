# REF: Ticket Lane — 单票生命周期、合同抽取与反例 TDD

> Canonical owner: AGENTS.md §3。风险矩阵在 AGENTS §3；本文件是执行细节。

## 1. Lane 契约（硬边界）

```
ONE COHESIVE TICKET
ONE BRANCH
ONE ISOLATED WORKTREE（独立目录/独立图状态/独立证据生命周期）
ONE ACTIVE WRITER（R13）
```

- worktree 基于**当前 remote master**（或票据声明的 authorized base SHA）创建；创建后记录 `LANE_BASE_SHA`。
- 产物只有三类可回写：feature branch commits、证据文件（lane 目录内）、tracker 更新（集成后）。

## 2. 读权威与 Relevant Surface Manifest

开工前构建（CodeGraph 辅助，不复制全文）：

```
upstream producers / validators & canonicalizers / direct callers /
downstream consumers / persisted artifacts / state owners /
identity & provenance owners / error & failure propagation /
security & privacy propagation / sibling analogous modules /
adjacent ticket authority boundaries / stale-invalidation deps
```

存在未知的重大仓库关系时不开始实质实现（先查清或 STOP）。

## 3. Contract Extraction（MEDIUM+ 必备字段块）

```
INPUTS / OUTPUTS / PRECONDITIONS / POSTCONDITIONS
HARD_INVARIANTS / VALID_SUCCESS_CASES / FAIL_CLOSED_CASES
ALLOWED_FALLBACKS / FORBIDDEN_FALLBACKS
IDENTITY_DEPENDENCIES / PERSISTENCE_DEPENDENCIES
OWNERSHIP / OUT_OF_SCOPE
```

- 禁止静默把更富合同降级为方便的局部启发式。
- 实现若改变 success/failure/valid/complete/identity/authority 的含义 → STOP（AGENTS §7 / RULES R14）。
- LOW 票可裁剪：至少 INPUTS/OUTPUTS/OUT_OF_SCOPE 三行。

## 4. Counterexample-first TDD

链条：`CONTRACT → COUNTEREXAMPLES → RED → IMPLEMENT → GREEN → REFACTOR → REGRESSION`。

**证据标准**：
- `TEST_FILE_EXISTS != TDD_RED_PROVEN`；
- RED 必须由目标反例断言触发（MODULE_NOT_FOUND / harness 损坏不算 RED）；
- 证据区分 `TEST_FIRST` 与 `COUNTEREXAMPLE_SPECIFIC_RED`；
- 最低数量：MEDIUM ≥3；selector/state/orchestration/security/provenance ≥5；HIGH 5–10；LOW 无强制（有合同就必须有对应正/反测试）。

**高价值反例类目**（瞄准"看起来合理、过了显眼测试、仍违反合同"的实现）：
合法解被拒；非法输入变成功；约束被静默忽略；缺身份被当可复用；陈旧产物被接受；空结果当成功；重复身份破坏集合语义；malformed-but-coercible 被接受；排序/并列/边界失效；一项满足两个不同要求；合法上游输出违反下游合同；caller 控制数据泄入日志/产物；默认值掩盖缺失必需状态；实现越入他票权威。

**防伪**：禁止新增 skip、删断言、缩范围伪造绿灯（RULES R8 + 项目 RULES）。

## 5. 实现与自审

- `/implement` 是 MEDIUM+ 实质实现的强制工程入口；`/tdd` 在正确性行为存在时强制（不可测需给出客观理由）；`/simplify` 只在 GREEN 之后且不得改行为/合同。
- skill 使用声明需可核验证据（被实际调用/读取），否则报 `UNVERIFIED`。
- 自审（/code-review 等）产物只是 worker 证据，不满足独立评审 quorum（R6）。

## 6. Repair

- 只修 reviewer 指出的 blocker + 同 scope 内明确真实缺陷；append-only commit（R4）。
- 新 SHA 触发 R5 失效链；delta 评审协议见 `references/git-ci-integration.md`。
- 修复轮次受 REPAIR_VALUE gate 与 budget 约束（见 `references/review-and-repair-saturation.md`）。
