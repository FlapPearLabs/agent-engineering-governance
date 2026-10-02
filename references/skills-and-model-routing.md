# REF: Skills & Model Routing — 执行方法路由与风险优先模型选择

> Canonical owner: AGENTS.md §0（skill 边界）。本文件是路由表（D 层默认）。SKILL_IS_EXECUTION_METHOD / SKILL_IS_NOT_AUTHORITY。
> skill 契约细节以各 SKILL.md 原文为准；本表与其冲突时，修本表而不是曲解 skill。各 skill 的 STATUS/SOURCE/FALLBACK 见 `skills/README.md` 主线清单（V1.1：13 项全部 INSTALLED 于基准环境，SOURCE=UNKNOWN 者按行 FALLBACK，无部署阻塞）。

## 1. Skill 路由表（按流程阶段；2026-09-05 安装与契约核验）

| 阶段 | 首选 skill | 触发条件 | 边界 |
|---|---|---|---|
| 流程定位 | `ask-matt`（可选） | 技能可用且不确定当前工程阶段 | OPTIONAL FLOW ROUTER；非权威、非批准、非合同校验器；缺失不阻断治理 |
| 需求澄清 | `grill-with-docs`（深度访谈；`grilling`/`grill-me`/`batch-grill-me` 为轻量变体） | 需求真实模糊 | 产出 ADR/词汇表，不是 Spec |
| 形式化 | `to-spec` | Grill/讨论已充分 | 不面试，只合成 |
| 分解 | `to-tickets` | approved 架构/Spec 之后 | 必须套用 AGENTS §4 seam-first 约束壳（execution-stage.md §6）；产物标注 Stage 建议 |
| 实现 | `implement` | CODE 票实质实现（MEDIUM/HIGH 默认强制入口；LOW 不强制） | EXECUTION ≠ ARCHITECTURE REOPEN；合同空白 → STOP |
| 行为开发 | `tdd` | 正确性行为/合同 | RED 必须反例触发（ticket-lane.md §4） |
| 评审（工程轴） | `code-review` | push 前自审 + 独立评审可复用其检查轴 | 自审 ≠ 独立评审 gate（R4 条件式） |
| 评审（委派子代理） | `review-agent` | 编排者把**未提交变更/diff**委派给只读缺陷列举 subagent 时 | 与 code-review **互补**：前者=委派型只读列举，后者=固定基点标准+风险双轴；同一票可先后使用，互不替代独立 gate |
| 诊断 | `diagnosing-bugs`（优先于轻量 `diagnose`） | 根因调查 | 不得借诊断扩 scope |
| 冲突 | `resolving-merge-conflicts` | 仅存在真实 merge/rebase 冲突 | 结束后回原 lane 流程 |
| 计划 | `writing-plans` | Spec→tickets 之间的实现计划 | 计划不是架构权威 |
| 子代理编排 | `subagent-driven-development` | 多 lane 并行执行 | 两段评审不豁免 R4/exact-SHA |
| 清理 | `simplify-code` | GREEN 之后 | 不得改行为/合同 |
| 交接 | `handoff` | 跨工具/中断/审计场景 | 默认直接 dispatch，不强制 handoff |

- 重复族裁决：本表为唯一路由权威；未列出的同职责 skill 不进入工程主链。
- skill 不得僭越权威：实现困难不是调用规划/Spec 技能重设计的理由（发现冲突 → STOP/ESCALATE）。
- skill 使用声明需可核验（被实际调用/读取），否则报 `UNVERIFIED`。

### 1.1 开工、阶段转换与专业 Skill 选择

遵守本基线的 Agent，在首次执行及阶段/技术栈/任务变化时，先完成 **阶段 → 触发条件 → Skill 选择 → 原文读取 → 执行或 fallback → 使用后汇报**。安装盘点不等于本票路由，也不等于使用证据。

1. 从票授权、风险与当前阶段选择上表的工作流 Skill；REQUIRED-at-trigger 的语义与缺失处理由 `skills/README.md` 拥有。LOW 不强制 `/implement`；不为凑齐清单调用所有 Skill。
2. 从目标仓权威、manifest、构建/工具配置、变更面与实际平台识别语言、框架、平台及领域；检查当前 runtime registry 中相匹配的**专业 Skill**。用户明确要求的 Skill 必须纳入选择。适用且可用时使用；没有匹配项、不可用或不适用时记录依据与替代方法，不凭文件后缀或名称猜适用性，不为遵守本标准擅自安装工具。
3. 专业 Skill 补充技术方法，不替换本表工作流槽位，不进入固定 13 项获取清单。重叠项选最小充分集合并说明理由；本表“未列出的同职责 skill”限制的是工作流替代，不能据此排除适用的专业 Skill。
4. 定位并读**完整 SKILL.md**；其引用的材料按任务所需读取。frontmatter 健康检查只证明定位成功。调用 Skill 的机制已实际加载全文时保留该事件，不重复读同一未变化版本。内容或任务变化时重新判断；不得把上一票的读取自动算本票应用。
5. 按原文执行，遵守 A/B/C/D 权威；Skill 的要求不能自动授权扩 scope、委派、联网、部署或发消息。方法与产品权威冲突时按 R1 处理；缺失按已定义 fallback 执行，报告 `SKILL_UNAVAILABLE`，无法证明实际使用则 `UNVERIFIED`。

### 1.2 使用后必须汇报

每次有意义的 Skill 应用完成或 fallback 完成后，在进入依赖其结果的下一阶段前，**必须向用户/编排者短报**：Skill 名称、选择目的、实际动作、结果/产物、可核验引用与限制（含 fallback 原因、偏离原文与未核验项）。读过但未应用只能说“已读取”；不能说“已使用完成”。同一阶段同一 Skill 的连续步骤可合并一次，独立应用或切换阶段须新增报告。

Worker / Reviewer / Integrator 向 Parent 汇报；Parent 归集后在推进前向用户报告实际应用及结果，可合并同阶段多位 worker 的报告但保留各自出处。报告是必要交付，不授予自批、集成或产品裁决权；正文保持短，详细证据用链接，不倾倒全文 Skill 或私有日志。

### 1.3 票级记录与消费边界

**SKILL_EXECUTION_RECEIPT_V1** 是本节拥有的票级证据附件；不是新 tracker、全局状态机或宿主 hook。开始时记录选择依据；每次 §1.2 汇报后更新记录；进入自审/独立评审/交接前绑定 exact subject 并运行 §1.4 校验器。同一票各阶段分开记录，最终包覆盖实际发生的阶段；尚未发生的应用不得预报完成。票无所需 Skill 时给出明确理由，不伪造应用记录。

机器字段及局部取值唯一声明见 `../schemas/skill-execution.schema.json`，起草用 `../templates/skill-execution.json` 和 `../templates/skill-report.json`；模板占位符不是执行证据，完成记录拒绝空白和未替换占位符。

| 记录面 | 含义 |
|---|---|
| subject | repo、base/candidate SHA、task、phase、role；校验目标由消费者另外提供 |
| selectionBasis / domainAssessment | 风险/阶段选择依据；从仓与 registry 获得的专业 Skill 匹配、排除或缺失理由 |
| skills | 每项理由、工作流/专业类别、状态、原文来源、全文读取证据、执行证据、使用后报告引用、fallback 原因 |
| artifacts | 脱敏证据位置与 sha256；可引用原有 trace、检查结果、产物和汇报摘录，不重造日志系统 |

应用记录必须同时有全文读取事件与实际执行/产物引用。fallback 必须有原因、替代执行证据及明确的 fallback 报告；它不证明原 Skill 已调用。未核验项不能满足完成条件。报告证据是 JSON 摘录，字段由 schema 的 report 定义：名称、状态、目的摘要、结果、证据引用、限制、接收方；消费者核验名称/状态/接收方和关联证据。

真实收据含候选 SHA，放在现有票证据、CI artifact 或本地证据目录，**不把包含自身 commit SHA 的收据提交进该 commit**。公开时按 R2 脱敏；`sourceRef` 用 registry 版本/公开来源标识，不写宿主路径。现有 review evidence 的 `artifacts[]` 可引用收据和校验输出，无需改旧 schema。

### 1.4 机械核验与独立判断

```bash
python3 scripts/skill_execution.py <RECEIPT_JSON> \
  --repo <REPO> --base-sha <BASE_SHA> --candidate-sha <CANDIDATE_SHA> \
  --task <TASK> --phase <PHASE> --role <ROLE> --evidence-root <EVIDENCE_ROOT> \
  --required-skill <TRIGGERED_SKILL>
```

重复 `--required-skill` 传入消费者根据 §1.1 独立核对的**本阶段**必需集合（含用户明确要求项）；不能从生产者收据反向生成集合以掩盖遗漏。没有必需项时改用 `--no-required-skills-reason <REASON>`。未发生阶段不进入集合。专业 Skill 选择是否完整、fallback 是否允许与足够，仍由适用的 reviewer / Parent 判断；显式 C-over-D 覆盖按 R1 留证。

- 校验器验证结构、subject、必需集合覆盖、全文读取/执行/报告引用、摘要与关联一致、证据文件及 digest；缺汇报、错候选、假引用、`UNVERIFIED` 均使 `recordValid=false`。适用流程须修复无效记录后推进。
- 只读消费者显式提供的证据根内、有界的普通文件；用目录句柄逐层打开且拒绝符号链接，防止“检查后替换路径”读到根外；不联网、不执行证据。退出 0 表示记录及附件核验通过；1 表示失败，均输出 JSON（参数错误按 argparse），不回显原始字段内容。
- 平台缺 descriptor-relative / no-follow 安全读取原语时返回 `SAFE_RETRIEVAL_UNAVAILABLE`，不得降到有竞态的路径读取。本机机械检查如实记环境阻塞；允许 Parent / 适用独立 reviewer 按相同字段、绑定、必需集合与原始来源人工核验并记录接受及限制。此为明确方法 fallback，不声称机器通过、不豁免独立门，也不注入某个宿主的 shell 要求。
- **记录有效不等于 Skill 语义执行已证实。** 一个哈希正确的自报日志不能证明全文实际送达、规则被遵守或汇报真正送达用户。消费者核对原始 runtime 事件与产物；适用独立门时 reviewer 检查真实性/充分性及 Parent 的转报。输出始终保留 `semanticApplicationVerified=false`、`hostEnforcementVerified=false`，不自行裁决 PASS。
- 本仓 CI 执行合成反例测试；本工具不是各 runtime 的自动 hook。现有 adapters 未接入 Skill 使用阻断，不得声称 live enforcement；Agent/Parent 的流程纪律与评审消费承担接线。

## 2. 模型路由（RISK FIRST, MODEL SECOND；D 层默认）

按平台实际**档位**映射，不硬编码不可核验的具体型号：

| 风险 | 档位 | 说明 |
|---|---|---|
| LOW（机械、胶水、文档） | lite / 低成本档 | 产出可被 L0（+生产票 L1）兜住 |
| MEDIUM（常规实现） | default / 中档实现模型 | 已知架构内的实现 |
| LONG CONTEXT（Spec/planning/审计） | 大上下文档（reasoning-tier） | 全文权威阅读与综合 |
| HIGH + ESCALATION 触发 | 最强可用推理档；终审可用外部强模型（Sol 级，人工搬运） | 语义错误成本最高的 gate 集中强模型 |

- ESCALATION 触发清单 = AGENTS §3（架构不确定、并发/canonical、安全边界、评审分歧、Spec/governance、里程碑、高爆炸半径）。
- 评审多样性：优先不同 context；高风险优先不同模型族（经济允许时）；不可得时如实记录 `MODEL_DIVERSITY = UNAVAILABLE`，保留 fresh context + 独立 grounding + 独立反例 + exact-SHA。
- 自动化评审不可用（配额/故障）= `UNAVAILABLE`：按仓政策路由到指定独立评审，不得静默豁免。
- 名单核验义务：本表每次治理评审（或至少每季度）对照平台可用档位复核；失效名单比没有名单更危险。

## 3. 平台映射备注

- WorkBuddy：Agent 工具 `model` 参数（default/lite/reasoning）+ 会话模型选择；Hermes：runtime 模型配置。
- 外部强评审当前人工搬运（PRE-EXTERNAL TERMINAL BARRIER 之后的 minimal handoff）；该 barrier 的**定义与判定 owner = `references/review-and-repair-saturation.md` §8**，本节只引用，不重复定义。

## 4. 派发元数据 recipe（MODEL_DISPATCH_METADATA；RISK FIRST, MODEL SECOND）

派发决策按固定字段组记录并逐字段核对，不以散文冒充合同。字段组**顺序即语义**：

```text
ROLE
TASK
RISK
MODEL_OR_TIER
REASONING_EFFORT
WHY
EXPECTED_OUTPUT
ESCALATE_IF
```

- **顺序是规范的（§2 的 RISK FIRST, MODEL SECOND 在此展开为字段序）**：`RISK` 必须先于 `MODEL_OR_TIER` 记录；先定风险，再由风险决定档位——风险驱动档位选择，反之不成立。
- `MODEL_OR_TIER` 记录的是**档位 / profile 引用**（§2 的档位名），**不是**具体型号：具体型号是 **profile / 可更新值，不是不变量**。
  后续 profile 更新换掉具体型号时，**不得要求改动本节的规范文本**——可核验性来自 profile 引用，不来自写死的型号字面量。
- 缺任一字段 = 派发记录无效。
- 顺序错误 = 派发记录无效。
- 把不可核验的具体型号写死成不变量 = 缺陷，须如实上报，不得静默通过。
- `ESCALATE_IF` **只引用** `AGENTS.md` §3 的 ESCALATION 触发清单，不在此重列触发项（清单的单一 owner 是 AGENTS §3）。
- 本 recipe 的合法 / 非法集合是**局部的**：本节**不引入**全局状态机，也不引入共享枚举。

```text
LEGAL    RISK 记录在 MODEL_OR_TIER 之前的完整字段组
LEGAL    MODEL_OR_TIER 解析为 profile 值，更新 profile 不需改不变量
ILLEGAL  缺失任一字段
ILLEGAL  把不可核验的具体型号写死为不变量
```

- CE-28：本字段组**只在本文件定义一次**；其它 surface 只指针 / 链接，不重复定义。
