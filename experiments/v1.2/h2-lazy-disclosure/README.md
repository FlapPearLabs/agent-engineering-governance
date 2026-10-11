# experiments/v1.2/h2-lazy-disclosure — H2 Lazy Skill / Progressive Disclosure（非 canonical）

> 本目录是 V1.2 **H2**（逻辑节点 **N2**）的实验：验证「多少治理 / Skill 内容可以离开 HOT、
> 只在任务相关时通过 progressive disclosure 加载，而不降低最终正确性」。
> **非 canonical、不接 CI、不 block merge、不改任何 canonical 语义。**
> 结论词汇仅限 `{DISCLOSURE_SAFE, DISCLOSURE_HAS_COST, INSUFFICIENT_EVIDENCE}`。

```text
CORE_QUESTION = LESS HOT + TASK-RELEVANT WARM LOADING + SAME MECHANICAL ACCEPTANCE
                = DO WE LOSE CORRECTNESS?
```

## 0. 状态（随 round 推进更新；最终值只在闭环后写）

```text
H2_STATUS            = FROZEN（协议/载体/任务集/评分已冻结；等待 runs）
H2_RESULT            = （待产）
CANONICAL_CHANGED    = NO
H3_CHANGED           = NO
H4_EXECUTED / H5_EXECUTED = NO / NO
```

## 1. 目录

| 文件 | 作用 |
|---|---|
| `README.md` | 本文件：边界、目录、复现、当前状态 |
| `protocol.md` | **冻结协议**：臂定义、投递机制、P1–P7、遥测、PART 22/23 规则、收尾门 |
| `carriers/H2_LEAN_BOOTSTRAP.md` | **变体载体**（VARIANT_H2 的 HOT 面；冻结） |
| `routes-h2.json` | H2 路由 manifest（S1/S2 逐字继承 N8；S3 = H2 载体路由；33 条，冻结） |
| `task-registry.json` | 任务集 + 复制设计 + 验收锚点（冻结） |
| `scoring-rubric.md` | **P5 预注册**：高价值边界 / MISSED_GUIDANCE 定义 / 结果计算规则（冻结） |
| `variant-manifest.json` | 冻结面登记（四个 hash + WHAT MOVED 声明 + receipt 规则） |
| `h2_hot_inventory.py` | HOT 面机械计量（与 H1 同口径；含 `--selftest` 反例自检） |
| `harness/` | 机械 harness：prepare/collect/acceptance/restore/hygiene + 两臂投递块 + 两份同构模板 + run-plan |
| `run-registry.md` | **run 身份唯一注册表**（冻结的 20-run 计划 + 逐 run 状态） |
| `runs/<RUN_ID>/` | 逐 run 记录（run.json / report.md / telemetry.json / acceptance.txt / review.md） |
| `precondition/` | P1–P7 前置证据（dry-run、validator 运行、正控输出） |
| `results.md` | 结果 + 缺陷 + 混杂声明 + 局限 + 闭环记录 |

## 2. 两臂与唯一自变量

```text
CONTROL_H2  = 当前完整 HOT 治理可达：placed CODEBUDDY.md（= 当前 AGENTS.md 逐字全文 + 薄头/尾）
              + 当前 RULES.md 全文（H2_RULES.md）；不额外加资料、无路由机制
VARIANT_H2  = 精简 HOT 载体（carriers/H2_LEAN_BOOTSTRAP.md → 投放为 CODEBUDDY.md）+ 同版
              H2_RULES.md + 任务相关 WARM 按路由加载 + Skill 按 §5 路由处置
```

**时代同版（v5）**：两臂（含 t01–t04 历史 base）都收到**当前时代**的治理材料 ——
同槽位 `CODEBUDDY.md` 载体（control=当前 AGENTS 逐字全文 / variant=lean 载体）、同版
`H2_RULES.md`、以及路由可达的 WARM owner 副本 `H2_WARM/`（源 = routes-h2.json S3 目标）。
历史 base 只改变任务代码状态；唯一自变量 = 披露策略。

- 其余全部相同：同 base、同任务文本、同工具、同验收契约、同评审协议、同模型档位（冻结）。
- WHAT LEFT HOT / REMAINED / MOVED TO WARM = `variant-manifest.json` 的结构化声明
  （细节下沉去向：AGENTS §3/§4/§5 与 §0 框架细节 → `references/` 各 owner）。
- 投递是 **harness 的机械步骤**（P2）：逐文件 sha256（含 `warm_bundle_sha256`）+
  `materials_commit` + `model_tier` 记录 + 槽位污染断言；交付侧与 collection 侧双重核验
  （含遥测存在性；任何 FAIL ⇒ collect exit 3，run 记 INVALID）。

## 3. 复现（本目录的所有机械部分）

```text
python3 experiments/v1.2/h2-lazy-disclosure/h2_hot_inventory.py            # HOT 计量
python3 experiments/v1.2/h2-lazy-disclosure/h2_hot_inventory.py --selftest # 反例自检
python3 experiments/v1.2/route-reachability/validate_routes.py \
        --base 9494de8e2d3bbc5c38b311e8cce29230e7574dce \
        --manifest experiments/v1.2/h2-lazy-disclosure/routes-h2.json --json   # P6
python3 -m unittest discover -s experiments/v1.2/tests -v                  # 材料自检（含 H2 套件）
```

run 侧复现（持久工作区，避免 /tmp）：

```text
export H2_RUNS_ROOT=<持久目录，非 /tmp>
bash experiments/v1.2/h2-lazy-disclosure/harness/prepare_run.sh <RUN_ID> <control|variant>
bash experiments/v1.2/h2-lazy-disclosure/harness/collect_run.sh <RUN_ID>
bash experiments/v1.2/h2-lazy-disclosure/harness/run_acceptance.sh <RUN_ID>
bash experiments/v1.2/h2-lazy-disclosure/harness/check_restore.sh <RUN_ID>
```

## 4. 本轮的边界（防误读）

```text
· 本目录的材料**不是** canonical change proposal；promotion 属 N9。
· 变体载体**不**弱化 RULES.md；冲突时 canonical 胜出。
· H2 不测试 "全部治理都可离开 HOT"；只测**受测任务分布 × 受测路由/Skill 机制**下的安全性。
· 实验结果（含 INSUFFICIENT_EVIDENCE）只进入 experiments/ 记录，不改变 AGENTS/RULES/references。
```
