# H3-A — STRUCTURE_DELTA_SHADOW v0 历史回放结果（非 canonical）

> 本文件记录 V1.2 Experiment 1 / H3-A 的**真实运行结果**：v0 detector 在已合并的
> replay corpus（[replay/cases.yaml](../replay/cases.yaml)）全部 ready cases 上运行
> 历史回放并逐案比较 expected / actual。
> 运行基线：main @ `36b23dc9c1a888d2c4837e7fba1277ae56f8cb02`，分支
> `experiment/v1.2-structure-delta-v0`。
> 边界：不接 CI、不 block merge、不产生任何自动化判定；canonical 语义零改动。

## 实现与运行

DETECTOR_PATH = `experiments/v1.2/structure_delta.py`（stdlib + git subprocess；
无新增依赖；无 CLI 框架；无 CI 接入）。

支持信号 = 仅 replay README 冻结的 v1 三信号（PREDICATE / COUNTING_UNIT 完全服从该定义）：

```text
NEW_FILE        git diff --no-renames --name-status <base> <candidate> 的 A 条目数
NEW_DIRECTORY   candidate 树目录前缀集合 − base 树目录前缀集合的差集大小
                （前缀由 git ls-tree -r --name-only <sha> 导出；每个祖先前缀计入）
NEW_DEPENDENCY  requirements*.txt（basename，任意深度）新增声明行数
                （非空、非 '#' 注释；行级计数）
```

其余信号名（NEW_MODULE / NEW_PUBLIC_INTERFACE / …）= `NOT_YET_MECHANICALLY_DEFINED`：
**未实现**（如 corpus 出现，loader 与 runner 会硬失败而非静默跳过）。

运行命令（两个来源仓均为 public；任意含完整历史的 clone 均可）：

```bash
python3 experiments/v1.2/structure_delta.py replay \
  --cases experiments/v1.2/replay/cases.yaml \
  --repo-map FlapPearLabs/agent-engineering-governance=<governance-clone> \
  --repo-map FlapPearLabs/zhihu-grabber-toolkit=<zhihu-grabber-toolkit-clone>
```

## 逐案结果

```text
CASE_ID = r01-zhihu-t14-async-seam-mismatch
EXPECTED = NEW_FILE=3
ACTUAL = NEW_FILE=3, NEW_DIRECTORY=0, NEW_DEPENDENCY=0
MATCH = YES

CASE_ID = r02-governance-review-evidence-interface
EXPECTED = NEW_FILE=5
ACTUAL = NEW_FILE=5, NEW_DIRECTORY=0, NEW_DEPENDENCY=0
MATCH = YES

CASE_ID = r03-governance-static-gate-adoption
EXPECTED = NEW_FILE=4, NEW_DEPENDENCY=1
ACTUAL = NEW_FILE=4, NEW_DIRECTORY=0, NEW_DEPENDENCY=1
MATCH = YES

CASE_ID = r05-governance-local-only-precondition-fix
EXPECTED = (empty)
ACTUAL = NEW_FILE=0, NEW_DIRECTORY=0, NEW_DEPENDENCY=0
MATCH = YES

CASE_ID = r06-governance-zcode-adapter-reference
EXPECTED = NEW_FILE=8, NEW_DIRECTORY=4
ACTUAL = NEW_FILE=8, NEW_DIRECTORY=4, NEW_DEPENDENCY=0
MATCH = YES
```

## 汇总

```text
READY_CASES = 5                     （动态读取 cases.yaml，不硬编码 case 数量）
MATCHED = 5
MISMATCHED = 0
FALSE_POSITIVE_SIGNAL_COUNT = 0     （expected 0 / actual >0 计）
FALSE_NEGATIVE_SIGNAL_COUNT = 0     （expected >0 / actual 更低计）
```

独立交叉核验（不同实现路径，对全部 5 案重计数，与 detector 逐项一致）：

```text
shell 管道（git diff --name-status | grep '^A'；ls-tree 前缀集合 comm 差集；
diff | grep '^+' 过滤空行/注释）结果：r01 A=3 dirs=0 / r02 A=5 dirs=0 /
r03 A=4 dirs=0 deps=1 / r05 A=0 dirs=0 / r06 A=8 dirs=4
```

## Detector-level negative controls（见 [../tests/test_structure_delta.py](../tests/test_structure_delta.py)）

```text
1. stale / unknown / non-commit base  -> StructureDeltaError（硬失败，无静默结果）
2. rename 在 --no-renames 下           -> 按冻结语义计为 delete + add（新路径 = A）
3. requirements 注释 / 空行            -> 不计入；重复声明按行计；删除行不计入
4. 嵌套目录前缀                        -> 每个祖先前缀均计入（非只计最深一层）
5. 非 requirements manifest            -> v1 家族外（pyproject.toml / package.json 等 → 0）
6. wrong-but-existing base             -> 比较层报告 MISMATCH（不静默通过）
7. expected 中出现非 v1 信号           -> 拒绝（不静默忽略）
```

## v0 解释性注记（冻结定义在微观处的落点；均为实现解释，非新定义）

```text
a. manifest 家族匹配 = basename fnmatch('requirements*.txt')，任意目录深度适用。
b. "注释行" = strip 后以 '#' 开头；"空行" = strip 后为空。逐行计数（不去重）。
c. 目录前缀 = 每个路径的全部祖先前缀，含尾随 '/'（集合差集，不重复计）。
d. base / candidate 必须是可解析的 40-hex commit SHA；否则硬失败。
e. v0 不做 reachability / diff-nonempty 判定（属 corpus provenance 职责，未并入 detector）。
```

## 原始 JSON（detector --json 输出，逐字）

```json
{
  "cases": [
    {
      "case_id": "r01-zhihu-t14-async-seam-mismatch",
      "expected": {"NEW_FILE": 3, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 0},
      "actual": {"NEW_FILE": 3, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 0},
      "match": true
    },
    {
      "case_id": "r02-governance-review-evidence-interface",
      "expected": {"NEW_FILE": 5, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 0},
      "actual": {"NEW_FILE": 5, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 0},
      "match": true
    },
    {
      "case_id": "r03-governance-static-gate-adoption",
      "expected": {"NEW_FILE": 4, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 1},
      "actual": {"NEW_FILE": 4, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 1},
      "match": true
    },
    {
      "case_id": "r05-governance-local-only-precondition-fix",
      "expected": {"NEW_FILE": 0, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 0},
      "actual": {"NEW_FILE": 0, "NEW_DIRECTORY": 0, "NEW_DEPENDENCY": 0},
      "match": true
    },
    {
      "case_id": "r06-governance-zcode-adapter-reference",
      "expected": {"NEW_FILE": 8, "NEW_DIRECTORY": 4, "NEW_DEPENDENCY": 0},
      "actual": {"NEW_FILE": 8, "NEW_DIRECTORY": 4, "NEW_DEPENDENCY": 0},
      "match": true
    }
  ],
  "ready_cases": 5,
  "matched": 5,
  "mismatched": 0,
  "false_positive_signal_count": 0,
  "false_negative_signal_count": 0
}
```

## 结论（仅限本轮范围）

```text
H3_A_RESULT = PASS

v0 detector 在当前真实 replay corpus 的全部 ready cases 上正确提取
NEW_FILE / NEW_DIRECTORY / NEW_DEPENDENCY 三类 deterministic structure signals
（MISMATCHED = 0，FALSE_POSITIVES = 0，FALSE_NEGATIVES = 0）。
```

本结论不外推：不构成 architecture gate validated、不构成 architecture drift solved、
不构成任何 promotion 依据。未实现的信号保持 `NOT_YET_MECHANICALLY_DEFINED`。
