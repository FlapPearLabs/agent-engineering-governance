# experiments/v1.2/replay — REAL HISTORICAL REPLAY CORPUS（非 canonical）

> 本目录是 V1.2 实验的证据准备产物：为将来的最小 `STRUCTURE_DELTA_SHADOW` 原型
> 提供**真实历史、可机械解析**的输入与对照。它**不是** benchmark framework、
> **不接 CI**、**不 block merge**、**不产生任何判定**；detector / 分类器 / runner 本轮均未实现。
> 建立基线：main 的 324fc36（PR #39 合并后，2026-10-07），分支 experiment/v1.2-replay-corpus。

## 每个 case 的构成

每个 case 从**公开来源仓库的真实 Git 历史**取出一个可定位的变更对：

```text
BASE_SHA                       变更前状态（真实提交）
CANDIDATE_SHA                  变更本身（真实提交；diff 由 git show 解析，禁止改写为合成 patch）
EXPECTED_MECHANICAL_SIGNALS    机器未来应该能够观察到的结构事实
SEMANTIC_EXPECTATION           KNOWN_BAD / KNOWN_GOOD / NEUTRAL_STRUCTURE_CHANGE（与机械信号分字段）
PROVENANCE                     来源仓、ref、解析命令、评审/修复关联、核验日期
```

禁止项（与 [seed corpus](../cases.yaml) 同规则）：

- 根据任何文字描述**重新编写**类似实现并称为 historical replay（synthetic reconstruction）；
- 把语义裁决写进机械信号（机械信号 ≠ 漂移结论）；
- 为了让未来 detector 容易成功而挑选过度简化的案例（selection bias 由独立评审检查，见下）。

## 字段对应（本目录 ↔ 本轮契约字段名）

| cases.yaml 字段 | 契约字段 |
|---|---|
| `case_id` | CASE_ID |
| `source_repository` | SOURCE_REPOSITORY |
| `source_ref` | SOURCE_REF |
| `base_sha` | BASE_SHA |
| `candidate_sha` | CANDIDATE_SHA |
| `historical_diff` | HISTORICAL_DIFF（解析命令） |
| `expected_mechanical_signals` | EXPECTED_MECHANICAL_SIGNALS |
| `semantic_expectation` | SEMANTIC_EXPECTATION |
| `provenance` | PROVENANCE |

## replay-readiness 判据（ready case 必须全部满足）

```text
REAL_BASE = YES                     两枚 SHA 真实存在于来源仓
REAL_CANDIDATE_OR_DIFF = YES        可由 SHA 直接取出（非重写）
PROVENANCE_RESOLVES = YES           解析命令在来源仓 clone 中可执行
EXPECTED_MECHANICAL_SIGNAL_DEFINED = YES
SEMANTIC_EXPECTATION_SEPARATE = YES 与机械信号分字段、不混写
SYNTHETIC_RECONSTRUCTION = NO
```

## 核验协议（2026-10-07 已执行）

在对应来源仓的 clone 中（三个来源仓均为 public，2026-10-07 经 GitHub API 核验；
本目录不记录任何本机路径）：

```bash
git rev-parse <base_sha> <candidate_sha>            # 两枚 SHA 存在
git merge-base --is-ancestor <sha> <source_ref>     # 可达性
git show <candidate_sha>                            # diff 可解析
```

PR 类 provenance 另用 GitHub API 核验（例：`gh pr view 87` 的 title / headRefName /
mergeCommit 与实际本地提交逐字段一致）。

## 用例一览

| case | class | 来源 | 结构信号（预期） | 语义裁决 |
|---|---|---|---|---|
| [r01](cases.yaml) | POSITIVE_SEAM_DRIFT | zhihu-grabber-toolkit | NEW_MODULE ×3；NEW_PUBLIC_INTERFACE | KNOWN_BAD |
| [r02](cases.yaml) | NEGATIVE_AUTHORIZED_STRUCTURE | agent-engineering-governance | NEW_PUBLIC_INTERFACE；NEW_MODULE；新文档/模板文件 | KNOWN_GOOD |
| [r03](cases.yaml) | NEGATIVE_AUTHORIZED_STRUCTURE | agent-engineering-governance | NEW_DEPENDENCY；NEW_MODULE；ruff.toml；CI 执行静态门 | KNOWN_GOOD |
| [r04](cases.yaml) | NEGATIVE_NO_STRUCTURE_DELTA | webcodex | 无结构增量（噪声底对照） | NEUTRAL_STRUCTURE_CHANGE |

## 与 seed corpus 的 crosswalk

[seed corpus](../cases.yaml) 是索引；本目录把其中可解析的 seed 落到真实提交，并按本轮
契约补充了负控（r02、r03）。未就绪项逐条记录在本目录 cases.yaml 的 `not_replay_ready`：

| seed | 状态 | 落点 / 原因（摘要） |
|---|---|---|
| c06 | RESOLVED | → r01（真实提交 + PR #87） |
| c11 | RESOLVED | → r04（webcodex 原生门修复提交） |
| c12 | ADJACENT_ONLY | 结构侧 trace = r03（同一提交记录并修复 gate 前基线）；c12 自身无单一可回放 diff |
| c01 / c02 | HISTORICAL_EVIDENCE_ONLY | 采用演练记录真实，但其被测代码是合成 fixture |
| c03 / c04 / c05 / c07 / c08 / c09 / c10 | NOT_REPLAY_READY | 事件级 trace 未定位，或属流程语义而非结构 diff（逐条原因见 cases.yaml） |

## 边界（与 [evidence-lineage.md](../evidence-lineage.md) 第 3 节一致）

- 非 canonical；本目录可整体删除而不影响任何 canonical 语义。
- 不接入 CI、不 block merge、不新增评审门、不改变既有评审语义。
- 本目录只承载**输入**；detector 实现、promotion 与任何形式化都不在本轮范围内。
