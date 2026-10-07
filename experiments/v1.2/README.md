# experiments/v1.2 — V1.2 Experiment Foundation（非 canonical）

> 本目录是 **experimental / non-canonical** 材料：它不改变、不覆盖、不弱化任何 canonical 语义。
> **V1.1.x remains canonical control.**（`AGENTS.md`、`RULES.md`、`references/`、`deployment/` 与现 CI = 控制组）
> **V1.2 尚未成立**：这里只有实验地基——不是候选规范、不是 release 材料、不是第二套权威。

## 本实验验证什么

验证一个方向性问题：**把高价值约束更多下沉到机械层（CI、hooks、静态检查、权限、状态机）之后，治理成本（上下文压力、评审轮次、仪式化流程）能否下降，而质量底线（真实失败仍被捕获）不退化。**

比较方式（输入已就绪 / detector 未实现）：`cases.yaml` 仍是 `HISTORICAL BENCHMARK SEED CORPUS`（**不能直接回放**）；真实 replay **输入**已建于 [`replay/`](replay/README.md)——durable cases 就绪，状态块见 [evidence-lineage.md](evidence-lineage.md) 第 3 节：

```text
REPLAY_INPUT_CORPUS = PARTIALLY_READY / READY_FOR_SHADOW_PROTOTYPE
DETECTOR = NOT_IMPLEMENTED
LOCAL_VALIDATION = NOT_YET_RUN
```

回放完成后按 [metrics.md](metrics.md) 成对比较；单边数字不构成结论。

## 原则

- **PROMOTION**：候选只有在（a）有本地失败证据、（b）完成可执行回放（executable replay；输入 corpus 已建于 [`replay/`](replay/README.md)，detector 尚未实现）、（c）由独立评审确认质量底线不退化之后，才可能进入 canonical 流程的变更协议；提升动作复用既有治理变更协议，本目录不定义其形态。
- **ROLLBACK**：本目录可整体删除而不影响任何 canonical 语义；实验分支合入与否都不影响控制组。
- **EXTERNAL_EVIDENCE != LOCAL_PROOF**：外部平台经验（仅作 SUPPORT）永远不提升实验候选的状态；状态提升只由本地证据驱动。
- **MECHANIZATION REPLACES TEXT, NOT STACKS ON IT**：机械化优先替代文字规则，而不是在文字规则之上再叠加机械层（避免双重付费）。
- 外部经验（OpenAI / Anthropic 等外部平台实践）只能出现在 SUPPORT 字段。

## 结构

| 文件 | 作用 |
|---|---|
| [`cases.yaml`](cases.yaml) | historical benchmark seed corpus（**非可执行 replay benchmark**）：真实历史 case；禁止 synthetic 材料 |
| [`replay/`](replay/README.md) | REAL HISTORICAL REPLAY CORPUS（replay **输入**已就绪；detector / runner 未实现）：REPLAY_DIFF 唯一绑定 + v1 确定性信号 + 双轴 disposition |
| [`metrics.md`](metrics.md) | 最小 metrics 定义（含可观测性标注） |
| [`evidence-lineage.md`](evidence-lineage.md) | 本地证据整理 + 候选 H1–H4 的 evidence lineage + 下一实验候选 |
| [`tests/test_material.py`](tests/test_material.py) | 材料完整性自检（留在实验目录内；不进 canonical CI 测试面） |

材料自检：`python3 -m unittest discover -s experiments/v1.2/tests -v`
