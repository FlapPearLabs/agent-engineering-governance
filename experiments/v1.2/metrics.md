# V1.2 实验 Metrics（最小定义；非 canonical）

> 本文件只定义「以后真正想比较的量」。它不是仪表盘，不要求本轮产生数据；
> 不得为凑数填入无法观测的值。
> 观测标注：`OBSERVABLE` / `OBSERVABLE_WITH_RECEIPT` / `REQUIRES_SEMANTIC_DISPOSITION` / `NOT_OBSERVABLE`。
> `REQUIRES_SEMANTIC_DISPOSITION` = 不能由机械信号直接观测；必须叠加架构/Spec 语义处置才能确认（见 QUALITY 的 confirmed_architecture_drift）。
> `NOT_OBSERVABLE` = 当前 runtime 无法可靠观测：**不得估算、不得造数**。

## QUALITY（质量面）

| 指标 | 定义 | 观测 |
|---|---|---|
| high-value defects escaped | 回放中「must_catch 未命中、且会导致实质错误决策或行为」的缺陷计数 | OBSERVABLE_WITH_RECEIPT（独立评审记录） |
| invalid PASS | 被后续证据推翻的通过声明计数（涵盖状态坍缩与越权授权两类形态） | OBSERVABLE_WITH_RECEIPT |
| structure_delta_signals | 从 diff 机械提取的结构增量信号计数（新模块/目录/依赖/接口/状态 owner/持久化面/跨边界依赖）——**信号 ≠ 漂移结论** | OBSERVABLE（机械提取；v0 已实现 3 类确定性信号：见 [structure_delta.py](structure_delta.py)） |
| confirmed_architecture_drift | 经「结构信号 + 架构/Spec 语义处置」共同确认的漂移计数（信号只是输入） | REQUIRES_SEMANTIC_DISPOSITION（非纯机械可观测；不得以信号数替代） |

## COST（成本面）

| 指标 | 定义 | 观测 |
|---|---|---|
| tokens | 每任务消耗的 token 数 | NOT_OBSERVABLE（当前 runtime 无可靠计量面；不得由字符数估算） |
| model calls | 路由到各档位模型的调用次数 | NOT_OBSERVABLE（无统一计数面） |
| tool calls | 每任务工具调用次数 | NOT_OBSERVABLE（无持久化计数面） |
| wall clock | 任务起止时间差 | OBSERVABLE（时间戳） |
| human interruptions | 每任务人工介入（停机提问与回答）次数 | OBSERVABLE（逐次记录） |

## GOVERNANCE COST（治理开销面）

| 指标 | 定义 | 观测 |
|---|---|---|
| hot prompt bytes | 注入指针正文的 UTF-8 字节数 | OBSERVABLE（既有字节测量法） |
| docs loaded | 会话实际读取的 canonical 文档数 | OBSERVABLE_WITH_RECEIPT（会话回执） |
| skills loaded | 实际加载并执行的 Skill 数 | OBSERVABLE_WITH_RECEIPT（票级 Skill 记录） |
| reviews run | 每个候选消耗的独立评审轮数 | OBSERVABLE（评审记录） |
| unique high-value findings | 每轮评审新增的高价值 finding 数（去重后） | OBSERVABLE_WITH_RECEIPT（novelty 记录） |

## 使用规则

- 比较必须成对：同一 case 分别在控制组与实验候选下回放；单边数字不构成结论。
- 回合边界：一轮回放 = 一个 case 从开工到关闭的完整记录。
- 外部经验不进入指标来源；指标只从本地回放记录采集。
- 回放前置条件见 [evidence-lineage.md](evidence-lineage.md) 第 3 节：seed corpus 尚不可直接回放，就绪前不得据此造数。
