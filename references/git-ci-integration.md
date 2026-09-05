# REF: Git / CI / Integration — 精确 SHA、CI 状态与串行集成

> Canonical owner: RULES.md R4/R5/R7 + AGENTS.md §6。本文件是证据块与核验清单。

## 1. 分支与提交

- 一票 = 一分支 = 一 worktree = 一 PR（除非显式 override）。
- 分支基于最新 remote master；禁止 master 直接施工；scope-clean commits。
- Conventional Commits（`feat/fix/docs/test/refactor/chore`）；凭据、临时产物、runtime memory 不提交。
- 署名约定：AUTHOR_NAME=`FlapPearLabs`；AUTHOR_EMAIL_CLASS=`GITHUB_NOREPLY`（执行点 = 仓 repo-local `git config user.name/user.email`）。

## 2. Merge gate（每次 merge 重新执行，不得沿用旧结论）

```
1. fresh fetch
2. origin/<feature> == REVIEWED_HEAD（exact SHA）
3. current remote master / merge-base 核验
4. master drift? → re-form candidate + fresh review（不 force-push、不转移 PASS）
5. required quorum（本票风险级）已对同一 exact HEAD PASS
6. ff-only merge
7. push
8. remote verify（origin/master 新 SHA == 预期）
9. 之后才允许 close Issue / tracker DONE
```

`MASTER_DRIFT != CONTENT_CONFLICT`：前者是机械时序条件（re-form + fresh review），后者才是 product-owner 裁决的契约冲突。

## 3. CI 状态语义

| 状态 | 必须披露 |
|---|---|
| PASS | 可压缩为一行（`PR_CI_COMPRESSION_ALLOWED = PASS_ONLY`） |
| FAIL | generic block + 失败签名 |
| NOT_TRIGGERED | 绝不得表述为 PASS 或 CI 完成 |
| SKIPPED | 为什么必需 CI 未执行 + skip 是否被授权 |
| CANCELLED | 外部/手动/被取代/候选相关 |
| INFRASTRUCTURE_FAILURE | 与候选代码失效区分 |
| KNOWN_BASELINE_FAILURE | generic block + 9 字段基线块 |
| BLOCKED | 阻塞依赖或授权条件 |
| UNKNOWN | 保持 UNKNOWN 直至证据充分；`UNKNOWN != PASS` |

### Generic non-PASS block（所有非 PASS 必附）

```
CI_STATE / CI_TRIGGERED / CI_RUN_ID_OR_URL / CI_OBSERVED_AT /
CI_FAILURE_SIGNATURE / RETRY_PERFORMED / CI_BLOCKER_CLASS(CANDIDATE|BASELINE|INFRASTRUCTURE|AUTHORIZATION|SCHEDULING|UNKNOWN) /
REVIEWER_ACCEPTED_CLASSIFICATION / REQUIRED_NEXT_ACTION
```

### KNOWN_BASELINE_FAILURE 9 字段块（叠加，不减）

```
CANDIDATE_CI_TRIGGERED / CANDIDATE_FAILURE_SIGNATURE / BASELINE_REPRODUCED /
BASELINE_SHA / BASELINE_FAILURE_SIGNATURE / SIGNATURE_MATCH /
CANDIDATE_CAUSED_FAILURE / CI_CLASSIFICATION / REVIEWER_ACCEPTED_CLASSIFICATION
```

分类权威：worker = PROPOSAL_ONLY；接受需独立评审 YES（R7）。

## 4. 修复后的 delta 评审协议

```
previous reviewed SHA --(diff)--> current candidate SHA
+ CodeGraph blast radius（变更触碰的 owner 模块与下游）
+ 权威（新增/变更的合同面）
→ 决定本轮需重开的 gate（全量链 vs delta 链）
```

- blast radius 未扩张且合同面未变 → 仅重开受影响 gate；
- 触及 owner 模块/安全边界/持久化语义 → 全链 fresh review；
- 争议/不确定 → 就高不就低。

## 5. L0 机械核验清单（harness 目标形态，NOW 部分可手工执行）

SHA 绑定、diff 范围、测试与回归执行记录、ancestry（merge-base --is-ancestor）、禁改文件清单、`git diff --check`、secret/路径扫描、CI 状态与证据块存在性校验、graph base SHA 记录。
（完整 harness 工具化 = NEXT，见 GAP_MATRIX G-09；先规则后工具，不为工具化推迟规则生效。）

## 6. 远端操作环境事实（指针，非规则）

- 凭据通道、gh CLI 路径、代理端口等机器特定事实 → `mcp/README.md` §MACHINE_SPECIFIC。本文件不记录任何环境值。
