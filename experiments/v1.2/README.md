# experiments/v1.2 — V1.2 Experiment Foundation（非 canonical）

> 本目录是 **experimental / non-canonical** 材料：它不改变、不覆盖、不弱化任何 canonical 语义。
> **V1.1.x remains canonical control.**（`AGENTS.md`、`RULES.md`、`references/`、`deployment/` 与现 CI = 控制组）
> **V1.2 尚未成立**：这里只有实验地基——不是候选规范、不是 release 材料、不是第二套权威。

## 本实验验证什么

验证一个方向性问题：**把高价值约束更多下沉到机械层（CI、hooks、静态检查、权限、状态机）之后，治理成本（上下文压力、评审轮次、仪式化流程）能否下降，而质量底线（真实失败仍被捕获）不退化。**

比较方式：同一批真实历史 case（`cases.yaml`）在控制组与实验候选下回放；单边数字不构成结论。

## 原则

- **PROMOTION**：候选只有在（a）有本地失败证据、（b）在 `cases.yaml` 上完成回放、（c）由独立评审确认质量底线不退化之后，才可能进入 canonical 流程的变更协议；提升动作复用既有治理变更协议，本目录不定义其形态。
- **ROLLBACK**：本目录可整体删除而不影响任何 canonical 语义；实验分支合入与否都不影响控制组。
- **EXTERNAL_EVIDENCE != LOCAL_PROOF**：外部平台经验（仅作 SUPPORT）永远不提升实验候选的状态；状态提升只由本地证据驱动。
- **MECHANIZATION REPLACES TEXT, NOT STACKS ON IT**：机械化优先替代文字规则，而不是在文字规则之上再叠加机械层（避免双重付费）。
- 外部经验（OpenAI / Anthropic 等外部平台实践）只能出现在 SUPPORT 字段。

## 结构

| 文件 | 作用 |
|---|---|
| [`cases.yaml`](cases.yaml) | benchmark case manifest：真实历史 case；禁止 synthetic 材料 |
| [`metrics.md`](metrics.md) | 最小 metrics 定义（含可观测性标注） |
| [`evidence-lineage.md`](evidence-lineage.md) | 本地证据整理 + 候选 H1–H4 的 evidence lineage + 下一实验候选 |
| [`../../scripts/tests/test_experiment_v12_foundation.py`](../../scripts/tests/test_experiment_v12_foundation.py) | 只验证本目录材料自身正确性的轻量测试 |

材料自检：`python3 -m unittest scripts.tests.test_experiment_v12_foundation -v`
