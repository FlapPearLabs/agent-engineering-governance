# 使用指南：采用、恢复与维护

> 本页是操作导航，不新增治理规则、回执 schema 或部署授权。执行步骤以 [PORTABLE_SETUP](../deployment/PORTABLE_SETUP.md)、[AGENTS](../AGENTS.md) 和对应 reference 为准。

## 选择入口

| 你的任务 | 从哪里开始 | 应获得的结果 |
|---|---|---|
| 第一次让 Agent 使用治理 | [README 的完整复制提示词](../README.md#3-复制即用发给-agent-的引导提示词)，再读 [PORTABLE_SETUP](../deployment/PORTABLE_SETUP.md) | 已读取治理与目标仓权威；能力缺口、覆盖记录和开工回执可核验 |
| 接手已有项目或切换 runtime | [项目状态恢复](../references/project-state-persistence.md#5-state_restore--每个-fresh-agent-进入既有项目时) | 根据远端、规范与票据证据重建当前合法 frontier |
| 新仓采用或旧仓补齐连续性 | [项目连续性合同](../references/project-continuity-contract.md) | 固定状态索引指向已有权威，初始化方式与仓库阶段相符 |
| 调整宿主能力、Skills 或 MCP | [能力矩阵](../deployment/PORTABLE_SETUP.md#环境能力矩阵environment-capability-matrix)、[Skills](../skills/README.md)、[MCP](../mcp/README.md) | 实际能力与降级路径被记录；不把工具缺失伪装为通过 |
| 维护治理仓 | 本页“本仓检查”与 [治理变更协议](../AGENTS.md#8-治理变更默认协议) | 变更在授权范围内，检查与适用的独立评审对应同一候选 |

## 新 Agent 开工

先打开本治理仓与目标工程仓，按 PORTABLE_SETUP 的既有顺序读取 README、RULES、AGENTS、目标仓权威及相关 references。README 是入口，完整提示词是可复制摘要；发生冲突时回到规范原文。

三个容易遗漏的动作：

- **两处权威都读。** 本治理仓提供普适不变量与执行默认，目标仓提供产品合同与仓库政策。冲突按 [RULES 的 R1](../RULES.md#r1-权威分层与冲突) 处理。
- **验证能力，不只登记名称。** Skills 的来源、触发条件与 fallback 见其获取指南；MCP 的配置模板不是实际启用证据。CodeGraph 缺失时按 [grounding 降级路径](../references/codegraph-grounding.md#4-不可用降级skilltool_is_method_not_authority工具缺失不自动成为普适硬-gate) 处理。
- **使用现有回执。** 开工回执与能力矩阵的定义留在 PORTABLE_SETUP，本页不维护第二份字段清单。

获授权的任务按 AGENTS 执行；提示词不会自行创建产品 scope、部署授权或下一个 milestone。

## 按阶段使用与汇报 Skill

安装盘点之后，按 [路由规范 §1.1–§1.4](../references/skills-and-model-routing.md#11-开工阶段转换与专业-skill-选择)进入本票执行：选择触发的工作流 Skill，并从仓权威/工具配置与 registry 匹配专业 Skill；读完整原文，应用或 fallback。**使用后向用户/编排者汇报**实际动作、结果、证据与限制，Parent 归集 worker 后转报用户。

在评审/交接前，用 [模板](../templates/skill-execution.json)组织既有 trace 与报告摘录，按路由规范的命令校验 subject、必需集合和附件。收据放在票级证据/CI artifact，不提交自引用 SHA；无效记录须补齐。机械验证不能证明日志真实或规则遵守，适用 reviewer 继续检查原始事件与产物。

## 恢复既有项目

项目的 .agent/project-state.json 是恢复索引，不能代替它指向的规范、Issue、PR 和评审证据。缺失时按项目连续性合同的 lazy adoption 路径补齐，不重写项目历史。

恢复时尤其注意：

1. 核验 remote default branch、候选分支及 exact SHA，不能把本地检出状态当成远端状态。
2. 将已接受的目标、规范、决策与当前工作票分开，检查 CI 与评审是否仍绑定当前候选。
3. 已完成 milestone 不自动授权下一阶段；离线与状态未同步时保留真实限制。
4. 离开会话、交接或完成有意义转换时执行 STATE_FLUSH。状态写回何处、何时写及反官僚判据见 [状态持久化](../references/project-state-persistence.md)。

## 在目标仓采用

采用治理不要求复制一整套全局规范到每个项目。目标仓保留本地 RULES、Approved Specs、架构决策、CI/merge 政策与明确的项目 delta，再通过指针引用治理。

- 新项目与已有项目的初始化不同，按 [连续性合同](../references/project-continuity-contract.md) 选择现有路径。
- 项目状态文件使用 [已有 schema](../schemas/project-state.schema.json) 和 [已有模板](../templates/)，字段验证由 [validate_project_state.py](../scripts/validate_project_state.py) 负责。
- 宿主事实按 [部署档案模板](../deployment/deployment-profile.md) 记录。本仓是公开仓；真实机器档案 local-only，凭据和本机身份不进入 Git。
- 学习条目的发现不等于已沉淀。关闭条目的已有条件见 [engineering-memory](../references/engineering-memory.md#4-learning-关闭条件按需-recipe非每票模板)。

## Runtime 与部署

| Runtime / 机制 | 文档入口 | 使用边界 |
|---|---|---|
| WorkBuddy guidance / MEMORY | [BOOTSTRAP_CONTRACT](../deployment/BOOTSTRAP_CONTRACT.md) | profile 限定的自动注入不证明全文送达；遵循显式读取清单 |
| WorkBuddy Git safety hook | [适配器说明](../adapters/workbuddy/README.md) | 读取当前部署证据和已知未覆盖；安装、verify、rollback 是不同操作 |
| ZCode continuity hooks | [适配器说明](../adapters/zcode/README.md) | 宿主接线和真实拒绝效果需要各自验证，合成测试不能代替 live 验收 |
| Codex / Hermes / OpenCode / 其他 Agent | [PORTABLE_SETUP](../deployment/PORTABLE_SETUP.md) | 使用相同规范读取与恢复路径，不推定它们具备 WorkBuddy 注入机制 |

普通采用与 live 部署分开。修改 README 或运行本仓测试，不构成写入用户 MEMORY、安装 hook 或改变宿主设置的授权。WorkBuddy live 部署的既有前置条件在 BOOTSTRAP_CONTRACT，hook 的顺序在适配器说明。

## 本仓检查

本仓配置了 Python correctness 静态门。以下命令在治理仓根执行；依赖版本取自仓内 requirements-dev.txt，不依赖某台机器恰好安装的工具。

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m compileall -q scripts adapters
python3 -m ruff check .
python3 scripts/validate_governance.py
python3 -m unittest discover -s scripts/tests
python3 -m unittest discover -s adapters/zcode/tests
python3 -m unittest discover -s adapters/workbuddy/tests
PUBLIC_RELEASE=1 python3 scripts/validate_public_release.py
PUBLIC_RELEASE=1 python3 scripts/validate_public_release.py --commit-metadata
PUBLIC_RELEASE=1 python3 scripts/validate_public_release.py --selftest
```

完整 CI 执行清单以 [governance-ci.yml](../.github/workflows/governance-ci.yml) 为准，包括 gate CLI entrypoint 自测。上列命令方便本地核验，不把本地结果等同于真实 PR CI。

历史公开扫描的命令为：

```bash
PUBLIC_RELEASE=1 python3 scripts/validate_public_release.py --history
```

它与当前候选面扫描的范围不同。报告须保留扫描 scope 与跳过项，不把有限的可达文本对象扫描称为全历史干净；完整语义见 RULES R2。

## 继续阅读

- [设计说明](design.md)：权威、角色、执行、证据和恢复如何连接。
- [决策历史](design-history.md)：事故、讨论、取舍、纠偏及来源。
- [README](../README.md)：入口、当前状态和完整复制提示词。
