# experiments/v1.2/replay — REAL HISTORICAL REPLAY CORPUS（非 canonical）

> 本目录是 V1.2 实验的证据准备产物：为将来的最小 `STRUCTURE_DELTA_SHADOW` 原型
> 提供**真实历史、可机械解析**的输入与对照。它**不是** benchmark framework、
> **不接 CI**、**不 block merge**、**不产生任何自动化判定**；detector / 分类器 / runner 均未实现。
> 状态：`REPLAY_INPUT_CORPUS = READY_FOR_SHADOW_PROTOTYPE`（durable cases 就绪）、
> `DETECTOR = NOT_IMPLEMENTED`、`LOCAL_VALIDATION = NOT_YET_RUN`。
> 建立基线：main 的 324fc36（PR #39 合并后），分支 experiment/v1.2-replay-corpus（PR #40）。

## 每个 case 的构成

每个 case 从**公开来源仓库的真实 Git 历史**取出一个可定位的变更对：

```text
BASE_SHA                       变更前状态（真实提交）
CANDIDATE_SHA                  变更本身（真实提交）
EXPECTED_MECHANICAL_SIGNALS    仅 v1 确定性信号（定义见下）；空列表 = 均不触发
STRUCTURE_DISPOSITION          结构增量是否被架构/票据权威允许（独立轴；AUTHORIZED_STRUCTURE /
                               NO_STRUCTURE_DELTA / NOT_ADJUDICATED）
BEHAVIORAL_DISPOSITION         candidate 自身是否存在行为/合同缺陷（独立轴；KNOWN_DEFECTIVE /
                               POST_REVIEW_REPAIRS_REQUIRED / NO_BEHAVIORAL_CLAIM）
AUTHORITY_REF                  仅当 STRUCTURE_DISPOSITION = AUTHORIZED_STRUCTURE 时必附：
                               独立于 candidate 自述的公开、可解析授权 artifact
PROVENANCE                     来源仓、ref、resolver 命令、评审/修复关联、核验日期
```

## REPLAY_DIFF 唯一绑定（v1）

```text
HISTORICAL_DIFF := git diff <BASE_SHA> <CANDIDATE_SHA>
```

resolver 必须**实际验证这一对**：两枚 SHA 存在（`rev-parse`）＋ `git diff <base> <candidate>`
可解析且非空。readiness 不能只证明「两个 SHA 都存在」——`STALE_OR_WRONG_BASE ⇒ provenance check FAIL`。

逐案可选的更强等式：若某 case 明确设计为 single-parent patch，另验 `candidate^ == base`
（当前全部 ready case 均成立并逐案声明），但该等式**不是** future case 的普遍要求——
允许非 direct-parent 的 diff 对。

## 确定性信号定义（v1）

只有具备**唯一机械谓词与计数单位**的信号才进入 expected counts；否则
`NOT_YET_MECHANICALLY_DEFINED`，不得作为 replay oracle。

| SIGNAL | PREDICATE | COUNTING_UNIT | 状态 |
|---|---|---|---|
| `NEW_FILE` | `git diff --no-renames --name-status <base> <candidate>` 含 ≥1 条 `A` 条目 | `A` 条目数（每条一个新增路径） | v1 确定 |
| `NEW_DIRECTORY` | candidate 树的目录前缀集合 − base 树目录前缀集合（由 `git ls-tree -r --name-only <sha>` 的路径前缀导出） | 差集目录数 | v1 确定 |
| `NEW_DEPENDENCY` | 在声明 manifest 集（v1：`requirements*.txt`，line-oriented）的路径上，diff 新增 ≥1 条依赖声明行（非空、非 `#` 注释） | 此类新增行数 | v1 确定（仅 requirements 家族） |

```text
NOT_YET_MECHANICALLY_DEFINED（不进入 expected counts：
NEW_MODULE / NEW_PUBLIC_INTERFACE / NEW_PACKAGE / NEW_STATE_OWNER /
NEW_PERSISTENCE_SURFACE / CROSS_BOUNDARY_DEPENDENCY / NEW_CONFIG_SURFACE）

原则：NO DETERMINISTIC PREDICATE ⇒ NOT A REPLAY ORACLE。
```

各信号独立计数（允许同时命中，例如一个新增的 manifest 文件同时计入 `NEW_FILE` 与
`NEW_DEPENDENCY`）。`expected_mechanical_signals: []` 是合法 oracle 形态（表示全部 v1
信号均不触发）。其他 manifest 家族（`pyproject.toml` / `package.json` / `Cargo.toml` 等）
及其余类别的确定性定义留待后续轮次；在获得唯一机械定义之前不得计入。

## 三个事实轴互不替代（防状态坍缩）

```text
STRUCTURE_SIGNAL != STRUCTURE_VERDICT != CANDIDATE_CORRECTNESS
```

即：机械信号（有没有结构增量）≠ 结构裁决（该增量是否被授权）≠ 候选正确性（candidate 是否
无行为/合同缺陷）。授权结构 ≠ 候选无缺陷；候选有行为缺陷 ≠ 结构违规；
`AUTHORIZED_STRUCTURE` 必须有 `authority_ref` 支撑，否则降级 `NOT_ADJUDICATED`。

禁止项（与 [seed corpus](../cases.yaml) 同规则）：

- 根据任何文字描述**重新编写**类似实现并称为 historical replay（synthetic reconstruction）；
- 把任一轴的裁决写进机械信号，或把两个 disposition 轴合并成一个总括 verdict；
- 从 candidate commit message / 后续 review / design-history 总结**单独**推导结构授权；
- 为了让未来 detector 容易成功而挑选过度简化的案例（selection bias 属评审议题：
  本目录**不作自证**；公开的评审轨迹与处置见 PR #40 的 review threads）。

## 字段对应（本目录 ↔ 既有契约字段名）

| cases.yaml 字段 | 契约字段 |
|---|---|
| `case_id` | CASE_ID |
| `source_repository` | SOURCE_REPOSITORY |
| `source_ref` | SOURCE_REF |
| `base_sha` | BASE_SHA |
| `candidate_sha` | CANDIDATE_SHA |
| `historical_diff` | HISTORICAL_DIFF（= `git diff <base> <candidate>`） |
| `expected_mechanical_signals` | EXPECTED_MECHANICAL_SIGNALS（仅 v1 确定性信号） |
| `structure_disposition`（附 `structure_rationale`、必要时 `authority_ref`） | STRUCTURE_DISPOSITION |
| `behavioral_disposition`（附 `behavioral_rationale`） | BEHAVIORAL_DISPOSITION |
| `provenance` | PROVENANCE |

## replay-readiness 判据（ready case 必须全部满足）

```text
REAL_BASE = YES                     两枚 SHA 真实存在于来源仓
REAL_CANDIDATE_OR_DIFF = YES        可由 SHA 直接取出（非重写）
REPLAY_DIFF_UNIQUE_BINDING = YES    git diff <base> <candidate> 可解析且非空（STALE_OR_WRONG_BASE ⇒ FAIL）
PROVENANCE_RESOLVES = YES           解析命令在来源仓 clone 中可执行
EXPECTED_MECHANICAL_SIGNAL_DEFINED = YES   （仅 v1 确定性信号）
STRUCTURE_DISPOSITION_DEFINED = YES        独立成轴；AUTHORIZED_STRUCTURE 必附 authority_ref
BEHAVIORAL_DISPOSITION_DEFINED = YES       独立成轴，不与结构轴合并
READY_CASE_IS_DURABLE = YES                可达来自默认分支（临时分支依赖 ⇒ 不入 ready）
SYNTHETIC_RECONSTRUCTION = NO
```

## 核验协议（2026-10-07 建立；2026-10-08 修订后复跑）

在对应来源仓的 clone 中（三个来源仓均为 public，经 GitHub API 核验；
本目录不记录任何本机路径）：

```bash
git rev-parse <base_sha> <candidate_sha>            # 两枚 SHA 存在
git diff <base_sha> <candidate_sha> --stat          # REPLAY_DIFF 可解析且非空
git merge-base --is-ancestor <candidate_sha> <source_ref>   # 可达性
git rev-parse <candidate_sha>^                      # 逐案声明：direct-parent 等式（若适用）
```

基本结构检查（stdlib-only；仓库配置环境可复现——不需要 PyYAML）：

```bash
python3 - <<'EOF'
import re
t = open("experiments/v1.2/replay/cases.yaml", encoding="utf-8").read()
assert "\t" not in t, "TAB found (YAML 块缩进禁用 tab)"
ids = re.findall(r"^  - case_id: (r\d\d-[a-z0-9-]+)$", t, re.M)
assert ids and len(ids) == len(set(ids)), "case_id missing or duplicated"
assert t.count("historical_diff: 'git diff ") == len(ids), "a case lacks the base..candidate diff binding"
for key in ("base_sha:", "candidate_sha:", "structure_disposition:", "behavioral_disposition:"):
    assert t.count(key) >= len(ids), f"missing {key}"
print("REPLAY_CHEAP_CHECK_OK", len(ids), "ready cases")
EOF
```

（完整 YAML 解析需要 PyYAML——属 detector 环境职责，本目录不新增依赖；
上述 stdlib 检查覆盖基础结构不变量：无 tab、case_id 唯一、diff 绑定与必需字段的存在性。）

PR 类 provenance 另用 GitHub API 核验（例：`gh pr view 87` 的 title / headRefName /
mergeCommit 与实际本地提交逐字段一致）。

## 用例一览

| case | class | 来源 | EXPECTED_MECHANICAL_SIGNALS（v1） | STRUCTURE_DISPOSITION | BEHAVIORAL_DISPOSITION |
|---|---|---|---|---|---|
| [r01](cases.yaml) | POSITIVE_SEAM_DRIFT | zhihu-grabber-toolkit | NEW_FILE ×3 | NOT_ADJUDICATED | KNOWN_DEFECTIVE |
| [r02](cases.yaml) | NEGATIVE_AUTHORIZED_STRUCTURE | agent-engineering-governance | NEW_FILE ×5 | AUTHORIZED_STRUCTURE（authority_ref = Issue #11） | POST_REVIEW_REPAIRS_REQUIRED |
| [r03](cases.yaml) | NEGATIVE_STRUCTURE_NOT_ADJUDICATED | agent-engineering-governance | NEW_FILE ×4；NEW_DEPENDENCY ×1 | NOT_ADJUDICATED（逐项授权暂不可证） | POST_REVIEW_REPAIRS_REQUIRED |
| [r05](cases.yaml) | NEGATIVE_NO_STRUCTURE_DELTA | agent-engineering-governance | 空集（噪声底对照） | NO_STRUCTURE_DELTA | NO_BEHAVIORAL_CLAIM |
| [r06](cases.yaml) | NEGATIVE_STRUCTURE_NOT_ADJUDICATED | agent-engineering-governance | NEW_FILE ×8；NEW_DIRECTORY ×4 | NOT_ADJUDICATED（逐项授权暂不可证） | POST_REVIEW_REPAIRS_REQUIRED |

（原 r04 = webcodex 原生门修复：真实但仅由临时分支承载，已降级为
`NOT_DURABLE_REPLAY_READY`，见 cases.yaml 的 `not_replay_ready`。）

## 与 seed corpus 的 crosswalk

[seed corpus](../cases.yaml) 是索引；本目录把其中可解析的 seed 落到真实提交，并按既有
轮次补充了负控（r02、r03、r05、r06）。未就绪项逐条记录在本目录 cases.yaml 的 `not_replay_ready`，
两处必须保持一致：

| seed | 状态 | 落点 / 原因（摘要，与 cases.yaml 结构化条目一致） |
|---|---|---|
| c06 | RESOLVED | → r01（真实提交 + PR #87） |
| c11 | NOT_DURABLE_RESOLUTION | 原落点 = webcodex 原生门修复 case；该 case 因临时分支依赖降级（见 `not_replay_ready` 的 `NOT_DURABLE_REPLAY_READY` 条目） |
| c12 | ADJACENT_ONLY | 结构侧 trace = r03；c12 自身无单一可回放 diff（结构化条目在 cases.yaml） |
| c01 / c02 | HISTORICAL_EVIDENCE_ONLY | 采用演练记录真实，但其被测代码是合成 fixture |
| c03 / c04 / c05 / c07 / c08 / c09 / c10 | NOT_REPLAY_READY | 事件级 trace 未定位，或属流程语义而非结构 diff（逐条原因见 cases.yaml） |

## 边界（与 [evidence-lineage.md](../evidence-lineage.md) 第 3 节一致）

- 非 canonical；本目录可整体删除而不影响任何 canonical 语义。
- 不接入 CI、不 block merge、不新增评审门、不改变既有评审语义。
- 本目录只承载**输入**；detector 实现、promotion 与任何形式化都不在本轮范围内。
- 双轴建模（STRUCTURE_DISPOSITION / BEHAVIORAL_DISPOSITION）、v1 信号定义与
  REPLAY_DIFF 绑定均为**实验 corpus 的事实建模**，不升格为 canonical rule。
- manifest 的自动解析校验与 negative controls：`DEFERRED_TO_DETECTOR_IMPLEMENTATION`
  ——detector 本身必然要读取该 corpus，在此之前另建 parser 会形成重复实现与实验维护成本；
  本目录以「基本结构检查（stdlib-only）」（见上）+ 独立评审维持基本数据格式完整性。
