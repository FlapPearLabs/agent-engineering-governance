# H2 results（非 canonical；run 完成后回填）

> 结构与判定规则已在 `scoring-rubric.md` 冻结。本文件只**回填**，不新增判定口径。
> 状态：STUB（等待 runs）。

## 1. 观测的 HOT 体量（PART 27）

```text
OBSERVED_CONTROL_HOT_CHARS = （待填；h2_hot_inventory.py @ H2 base）
OBSERVED_VARIANT_HOT_CHARS = （待填）
OBSERVED_REDUCTION          = （待填）
VARIANT_FULLY_DELIVERED     = （待填）
N6_PROJECTION != H2_OBSERVATION（两者不得互引为证据）
```

## 2. run 总表（引用 run-registry.md）

```text
CONTROL_VALID_RUNS =   VARIANT_VALID_RUNS =   INVALID_RUNS =   BLOCKED_RUNS =
（逐 run 明细见 run-registry.md §1–§3）
```

## 3. 指标（M1–M7；口径见 scoring-rubric §1）

```text
M1 ROUTE_EXISTENCE_RATE  = （待填；P6 输出）
M2 ROUTE_LOADABLE_RATE   = （待填）
M3 WARM_FILES_LOADED     = CONTROL: / VARIANT:（仅完整读取）
M4 MISSED_GUIDANCE       = （待填；逐条）
M5 FINAL_CORRECTNESS     = （逐 task 两臂比较）
M6 SKILL_RETRIEVAL_HIT   = （聚合）
M7 UNNECESSARY_LOAD      = （逐 run）
```

## 4. 逐任务结果（两臂对照）

（逐 task：findings 对照 / correctness / missed-guidance 判定 / 备注）

## 5. H2_RESULT 判定

```text
H2_RESULT ∈ {DISCLOSURE_SAFE, DISCLOSURE_HAS_COST, INSUFFICIENT_EVIDENCE}
（按 scoring-rubric §9 的 S1–S5 / MISSED_GUIDANCE 优先序计算；逐条列出成立与否）
```

## 6. 迁移矩阵对账（PART 26）

```text
B 组 16 条 + R-V12-049：逐条 RULE_ID / H2_EVIDENCE / STATUS
（SUPPORTED_TO_MOVE / NOT_SUPPORTED / STILL_UNKNOWN）
```

## 7. 局限与混杂声明

（环境故障、n=1 的 shape、blind 状态、其他 CONFOUNDERS —— 逐条列出）

## 8. 闭环记录

```text
PR =   MERGE_SHA =   POST_MERGE_CI = （merge 后补记）
```
