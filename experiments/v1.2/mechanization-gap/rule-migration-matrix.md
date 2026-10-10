# N6.4 — Rule Migration / Target Layer Matrix（V1.2 mechanization gap analysis）

> **状态 = N6.4 本轮产物。非 canonical。本文件是 N6 的核心交付物。**
> 输入 = `rule-inventory.md`（94 条规则）+ `failure-mechanism-map.md`（22 条失败，3 个模式）
> + `longhorizon-mechanism-map.md`（12 个机制）。
> **本文件只决定"应该去哪一层"，不实现任何一层。**

## 0. 一条必须先摆出来的事实（它改变整张表的读法）

实测（命令见 `rule-inventory.md` 附录 B）：`AGENTS.md` 经 guidance 通道**只投递前 108 行 = 7,840 字符**。

```text
§ 0 适用范围与铁律        4,100   VISIBLE
§ 1 角色模型                698   VISIBLE
§ 2 EXECUTION STAGE         466   VISIBLE
§ 3 TICKET LANE           1,270   VISIBLE
§ 4 SEAM-FIRST              699   VISIBLE
§ 5 CODEGRAPH               231 / 1,051   PARTIAL（尾部 820 被丢弃）
§ 6 REVIEW / REPAIR / CI  1,068   **DROPPED**
§ 7 AUTO-ADVANCE 与 STOP     339   **DROPPED**
§ 7.1 STATE_RESTORE/FLUSH 1,755   **DROPPED**
§ 8 治理变更                 257   **DROPPED**
§ 9 报告                     391   **DROPPED**
§ 10 BOOTSTRAP            1,286   **DROPPED**
                          ─────
NEVER_AUTO_DELIVERED      5,096 字符 = AGENTS.md 的 37%
```

**读法**：§6–§10 里的规则当前处于一个**自我描述与实际投递不符**的状态 ——
它们被写成"HOT（D 层默认）"，但**从不自动到达**任何 agent。实际上它们靠
`BOOTSTRAP_CHECKLIST` B3（"必须继续读到其指向的全文"）**作为条件读取**才可能生效。

```text
⇒ 对这批规则，"CAN_REMOVE_FROM_HOT" 这个问题的形态变了：
   不是"能不能移出 HOT"，而是"**它们本来就不在 HOT**，只是被这样标注着"。
⇒ 因此本表对它们的处置是：**如实重分类**（多为 WARM 或 MECHANICAL），
   而不是"删除一条正在生效的 HOT 规则"。
```

这条同时解释了 H1 的裁断结论（`END_TO_END_GOVERNANCE_LOSS_PROVEN = NO`）：
补读是清单义务，义务存在 ≠ 已执行。本表的作用是让**哪些内容依赖该义务**变得可数。

---

## 1. 层定义与判定口径

```text
CURRENT_LAYER（按**实际投递**记，不按文件自称；词表固定为下列六个）：
  HOT_AUTO          = 经 guidance 通道自动注入，且落在前 8,000 字符内
  HOT_AUTO_MEMORY   = 经 MEMORY 指针通道注入（不在 AGENTS.md 内）
  HOT_AUTO_PARTIAL  = 所属章节**部分**被投递（尾部被截断）
  HOT_NOT_DELIVERED = 文件自称 HOT，但实测**从不**投递（§6–§10 主体）
  HOT_READ          = 不自动注入，但 BOOTSTRAP_CHECKLIST 要求显式全文读（RULES.md）
  EXPERIMENT_ONLY   = 只存在于实验线记录，尚未进入 canonical

TARGET_LAYER（七选一，每条规则**只能**有一个主目标）：
  A. HOT_INVARIANT              语义不变量：必须留在（真正会到达的）HOT 里
  B. WARM_PROGRESSIVE_DISCLOSURE 细节下沉到 references，HOT 只留指针
  C. MECHANICAL_GATE            由 tests / validators / hooks / CI 接管
  D. HARNESS_STATE_MACHINE      由执行 harness 的状态转移接管
  E. RUNTIME_ADAPTER            平台/运行时特有行为下沉
  F. DELETE_REDUNDANT           与另一条重复，可删（先合并 owner）
  G. KEEP_PENDING_EVIDENCE      方向已定但**证据不足**，暂不迁移

四条判定纪律（PART 11/12/13/15）：
  ① MECHANIZATION_MUST_REPLACE —— 任何 HOT 移除必须能回答：
     WHAT NOW ENFORCES IT / WHERE / HOW IT FAILS / HOW WE KNOW IT IS LOAD-BEARING。
     答不出 ⇒ 记 NOT_YET，不得移除。
  ② 不因"能写成代码"就机械化：须 predicate 足够确定 + 失败语义明确 + 有正控 + 误通过风险已知。
  ③ `ROLE_SEPARATION != PROCESS_TOPOLOGY`：D 层只定义**职责边界与转移**，不定义进程数。
  ④ 外部材料（E1）**不**支撑任何 TARGET 层的选定；只作方向佐证。
```

## 2. 主表（94 条，一行一条）

列含义：`CUR` = 当前实际层；`TGT` = 目标层；`FORGET` = 机械化后 agent 是否可忘；
`PRED` = 确定性谓词可得性；`MECH_TODAY` = 现有机械 owner；`RM` = 现在可否移出（真正会到达的）HOT。

```text
ID       CUR                        TGT  FORGET PRED     MECH_TODAY                              RM
──────── 每一条的"现在可否移出"都以 §3 的替代论证为准 ────────────────────────────────────────────
R-V12-001  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-002  HOT_AUTO                 C    PART   PARTIAL  skill_execution.py + schema + 32 tests  NOT_YET
R-V12-003  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-004  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-005  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-006  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-007  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-008  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-009  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-010  HOT_AUTO                 B    YES    PARTIAL  —                                       YES
R-V12-011  HOT_AUTO                 C    PART   YES      ✗ 无（本轮机械候选）                     NOT_YET
R-V12-012  HOT_AUTO                 C    PART   YES      PARTIAL: ci-executes-static-gate        NOT_YET
R-V12-013  HOT_AUTO                 A    NO     PARTIAL  PARTIAL: 值域多处断言                   NO
R-V12-014  HOT_AUTO                 C    YES    YES      PARTIAL: ticket-lane §9 schema           NOT_YET
R-V12-015  HOT_AUTO                 A    NO     PARTIAL  PARTIAL: t18（103 tests）               NO
R-V12-016  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-017  HOT_AUTO                 A    NO     PARTIAL  PARTIAL: CI 结构                       NO
R-V12-018  HOT_AUTO                 A    NO     PARTIAL  —                                       NO
R-V12-019  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-020  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-021  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-022  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-023  HOT_AUTO                 A    NO     PARTIAL  —                                       NO
R-V12-024  HOT_AUTO                 A    NO     PARTIAL  PARTIAL: R3 与其下游检查                NO
R-V12-025  HOT_AUTO                 A    NO     PARTIAL  PARTIAL: 见 R-V12-076                  NO
R-V12-026  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-027  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-028  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-029  HOT_AUTO                 D    PART   PARTIAL  —                                       NOT_YET
R-V12-030  HOT_AUTO                 D    PART   PARTIAL  PARTIAL: --commit-metadata（身份）       NOT_YET
R-V12-031  HOT_AUTO                 D    YES    YES      ✗ 无（F-002 的规则）                     NOT_YET
R-V12-032  HOT_AUTO                 A    NO     PARTIAL  —                                       NO
R-V12-033  HOT_AUTO                 C    YES    YES      ✗ 无（R5 的 L0 钩子无实现）              NOT_YET
R-V12-034  HOT_AUTO                 D    PART   PARTIAL  —                                       NOT_YET
R-V12-035  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-036  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-037  HOT_AUTO                 D    PART   PARTIAL  PARTIAL: execution-stage §6             NOT_YET
R-V12-038  HOT_AUTO                 D    PART   NO       —                                       NOT_YET
R-V12-039  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-040  HOT_AUTO                 D    PART   PARTIAL  ✗ 无 —— **最大单块机械候选**            NOT_YET
R-V12-041  HOT_AUTO                 C    PART   PARTIAL  PARTIAL: CI 步骤顺序                   NOT_YET
R-V12-042  HOT_AUTO                 D    PART   PARTIAL  ✗ 无（H4 的标的）                      NOT_YET
R-V12-043  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-044  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-045  HOT_AUTO                 B    YES    NO       —                                       YES
R-V12-046  HOT_AUTO                 B    PART   PARTIAL  PARTIAL: t02（11 tests）               YES
R-V12-047  HOT_AUTO                 B    YES    PARTIAL  PARTIAL: codegraph_lifecycle（1323）    YES
R-V12-048  HOT_AUTO_PARTIAL     C    YES    YES      FULL-ish: LC-INV1..INV5                 YES
R-V12-049  HOT_AUTO_PARTIAL     C    YES    YES      PARTIAL: schema 字段                    NOT_YET
R-V12-050  HOT_AUTO                 A    NO     PARTIAL  PARTIAL: L0 项散落在多个扫描器         NO
R-V12-051  HOT_AUTO                 G    PART   NO       —                                       NO
R-V12-052  HOT_NOT_DELIVERED     G    PART   PARTIAL  PARTIAL: 饱和文件 + 评审证据          NO
R-V12-053  HOT_NOT_DELIVERED   A    NO     NO       —                                       NO
R-V12-054  HOT_NOT_DELIVERED   C    PART   PARTIAL  PARTIAL: t03（17 tests）               NOT_YET
R-V12-055  HOT_NOT_DELIVERED   B    YES    NO       —                                       YES
R-V12-056  HOT_NOT_DELIVERED   A    NO     PARTIAL  —                                       NO
R-V12-057  HOT_NOT_DELIVERED   D    PART   PARTIAL  PARTIAL: state_flush_guard（198）       NOT_YET
R-V12-058  HOT_NOT_DELIVERED   D    PART   YES      PARTIAL: project-state schema           NOT_YET
R-V12-059  HOT_NOT_DELIVERED   D    PART   PARTIAL  PARTIAL: state_flush_guard（只提示）     NOT_YET
R-V12-060  HOT_NOT_DELIVERED   D    YES    YES      FULL-ish: validate_project_state（252）   YES
R-V12-061  HOT_NOT_DELIVERED   C    PART   PARTIAL  PARTIAL: grounding_guard（262）         NOT_YET
R-V12-062  HOT_NOT_DELIVERED   D    PART   PARTIAL  ✗ 无（双评审是流程纪律）               NOT_YET
R-V12-063  HOT_NOT_DELIVERED   B    PART   PARTIAL  PARTIAL: 饱和文件 §5 模板              YES
R-V12-064  HOT_NOT_DELIVERED   C    YES    YES      ✗ 无                                     NOT_YET
R-V12-065  HOT_NOT_DELIVERED   C    PART   PARTIAL  PARTIAL: skills-and-model-routing      NOT_YET
R-V12-066  HOT_AUTO_MEMORY         E    PART   YES      FULL-ish: hot_inventory.py              YES
R-V12-067  HOT_AUTO_MEMORY         E    YES    PARTIAL  PARTIAL: 预算检查                    YES
R-V12-068  HOT_AUTO                 A    NO     NO       —                                       NO
R-V12-069  HOT_READ                 A    NO     PARTIAL  PARTIAL: no-authority-inversion         NO
R-V12-070  HOT_READ                 C    YES    YES      FULL: validate_public_release           YES
R-V12-071  HOT_READ                 C    YES    YES      FULL: machine-facts-…                   YES
R-V12-072  HOT_READ                 C    PART   YES      PARTIAL: 归档规则                      NOT_YET
R-V12-073  HOT_READ                 C    PART   YES      PARTIAL: mcp-canonical-set-v1            NOT_YET
R-V12-074  HOT_READ                 C    YES    YES      FULL: --selftest 51/51                  YES
R-V12-075  HOT_READ                 A    NO     PARTIAL  PARTIAL: t05/t06/t07/t08             NO
R-V12-076  HOT_READ                 C    PART   PARTIAL  ✗ 无（身份断言）                        NOT_YET
R-V12-077  HOT_READ                 C    YES    YES      ✗ 无（R5 L0 钩子未实现）                 NOT_YET
R-V12-078  HOT_READ                 C    PART   PARTIAL  PARTIAL: H1 新增的 committed-set 检查   NOT_YET
R-V12-079  HOT_READ                 C    YES    YES      FULL: no-unrelated-platform-…            YES
R-V12-080  HOT_READ                 A    NO     NO       —                                       NO
R-V12-081  HOT_AUTO_MEMORY         D    PART   PARTIAL  PARTIAL: B5 可全机械                 NOT_YET
R-V12-082  HOT_READ                 C    YES    YES      FULL: memory-pointer-within-budget       YES
R-V12-083  HOT_AUTO                 E    PART   YES      PARTIAL: 参考实现在别仓                  NOT_YET
R-V12-084  HOT_NOT_DELIVERED   F    YES    —        —（与 R-V12-066 重复）                  YES
R-V12-085  HOT_NOT_DELIVERED   B    YES    PARTIAL  —                                       YES
R-V12-086  EXPERIMENT_ONLY          D    YES    YES      ✗ 无（H1 教训）                          N/A
R-V12-087  EXPERIMENT_ONLY          D    YES    YES      ✗ 无（H1 教训）                          N/A
R-V12-088  EXPERIMENT_ONLY          D    PART   PARTIAL  ✗ 无（H1 教训）                          N/A
R-V12-089  EXPERIMENT_ONLY          C    YES    YES      ✗ 无（H1 教训）                          N/A
R-V12-090  EXPERIMENT_ONLY          D    PART   PARTIAL  ✗ 无（H1 教训）                          N/A
R-V12-091  EXPERIMENT_ONLY          C    PART   PARTIAL  ✗ 无（H1 教训）                          N/A
R-V12-092  EXPERIMENT_ONLY          C    PART   PARTIAL  ✗ 无（H1 教训）                          N/A
R-V12-093  EXPERIMENT_ONLY          C    PART   PARTIAL  ✗ 无（H1 教训）                          N/A
R-V12-094  HOT_AUTO                 A    NO     NO       —                                       NO
```

**统计**

```text
A  HOT_INVARIANT               = 25
B  WARM_PROGRESSIVE_DISCLOSURE = 19   （其中 13 条现在即可下沉；6 条 §6–§10 本来就没投递）
C  MECHANICAL_GATE             = 26
D  HARNESS_STATE_MACHINE       = 18
E  RUNTIME_ADAPTER             =  3
F  DELETE_REDUNDANT            =  1
G  KEEP_PENDING_EVIDENCE       =  2
                               ────
                                  94
```

---

## 3. HOT 移除候选 —— 逐条替代论证（MECHANIZATION_MUST_REPLACE）

**格式纪律**：每一条必须同时回答四个问题，缺一即判 `NOT_YET`。

### 3.1 现在即可移除（替代者已在仓内并已验证）

#### R-V12-070 / R-V12-071 / R-V12-074 / R-V12-079 / R-V12-082 — R2 与 R7 的机械面
```text
（五个 ID 逐一列出，不用 "070 / 071" 这类简写 —— 简写无法被机器逐条核验）
WHAT NOW ENFORCES IT = validate_public_release.py（1414 行，双层扫描 + 5 条实现纪律）
                       + validate_governance.py 的 `no-credentials-anywhere` /
                         `machine-facts-only-in-designated-files` /
                         `no-unrelated-platform-requirements` / `memory-pointer-within-budget`
WHERE = CI 步骤 `Run public-release current-tree scan` / `--commit-metadata` / `--selftest`
        + `Run governance self-validation`
HOW IT FAILS = 命中即 FAIL 并列出命中位置（不是 warn）
HOW WE KNOW IT IS LOAD-BEARING = **有实证**：2026-10-09 一个 subagent 把含真实家目录路径的
        评审脚本写进 repo 根 → 该门当场报 2 项 FAIL（`no-credentials-anywhere` +
        `machine-facts-only-by-designated-files`）。**门真的会响。**
        另有 `--selftest` 51/51 与"向校验器源码副本注入本机路径 → 必须 FAIL"的回归。
CAN_AGENT_FORGET_AFTER_MECHANIZATION = YES（对"不要写凭据/本机路径"这件事）
RESIDUAL RISK = 扫描器只能命中**模式化**的泄漏。非模式化的敏感内容（例如一段描述内部系统的散文）
        仍需人判 → 因此 **R2 的价值主张（"泄漏不可撤回"）保留在 A 层作为一句认知**，
        但 4,196 字符的操作细节可以从必读面移除。
EXTERNAL_EVIDENCE_LEVEL = N/A（不依赖外部）
PROMOTION_REQUIRED = NO（已在 main）
```

#### R-V12-060 — PROJECT_CONTINUITY_CONTRACT 的机械面
```text
WHAT NOW ENFORCES IT = scripts/validate_project_state.py（252 行）+ schema + project_state_guard
WHERE = CI（validator）+ hook（写入侧）
HOW IT FAILS = 校验器 FAIL；hook 只在缺失时注入 `PROJECT_CONTINUITY_INITIALIZATION_REQUIRED`
HOW WE KNOW IT IS LOAD-BEARING = H1 t03 臂做过活体验证：4 个 hook 对真实仓运行后，
        已提交状态索引 **sha256 不变**（证明 hook 不代写语义）；且校验器有 14 项检查、
        基线（无索引时）确实是 0/1 FAIL —— 门在缺索引时会红。
CAN_AGENT_FORGET = YES（对"索引必须存在且合 schema"这件事）
RESIDUAL = "何时写"（meaningful transitions 的判定）仍需认知 → 保留一句在 A 层
PROMOTION_REQUIRED = NO
```

#### R-V12-048 R-V12-066 R-V12-067 R-V12-084 — 注入通道事实 + 预算 + 重复项
```text
R-V12-048（FULL_INIT_FORBIDDEN）= codegraph_lifecycle verify 输出 LC-INV1..INV5，可接 CI
R-V12-066/067（两条通道 + 四性质 + profile 事实）= hot_inventory.py 已把它变成**可复算数字**
        （8,000 / 13,756 / 7,840 / 5,916 / 59.6%），且 H1 材料里有回归测试
R-V12-084 = **与 R-V12-066 重复**（AGENTS §10 与 BOOTSTRAP_CONTRACT §1 双声明）
        处置 = 合并 owner：数值 owner 归 BOOTSTRAP_CONTRACT §1，AGENTS §10 只作指针
        （这正是仓内既有的 §9 值域纪律的同一做法）
CAN_AGENT_FORGET = YES
PROMOTION_REQUIRED = NO（对 066/067/084 的**去重**；048 已有门）
```

#### B 组的 19 条（细节下沉，HOT 留指针）
```text
逐条列出（**不用区间/简写** —— 区间会让"哪条被处置了"无法被机器逐条核验）。
这 19 条 = 矩阵中 TGT=B 且 RM=YES 的**全部**（由材料自检与主表比对）。
  R-V12-003  证据路由：MECHANICAL QUESTION → 静态工具
  R-V12-004  证据路由：BEHAVIORAL CONTRACT → TEST
  R-V12-005  证据路由：CROSS-MODULE STRUCTURE → CODEGRAPH
  R-V12-006  证据路由：SEMANTIC / CONTRACT → MODEL REASONING
  R-V12-007  证据路由：HIGH-VALUE UNCERTAINTY → 强/外部评审
  R-V12-008  DO_NOT_SPEND_REASONING_ON_MACHINE_PROVABLE_FACTS
  R-V12-010  USE_REPOSITORY_NATIVE_STATIC_TOOLING_FIRST
  R-V12-021  SEAM BEFORE TICKET
  R-V12-028  AUTO-ADVANCE UNTIL REAL AUTHORITY UNCERTAINTY
  R-V12-035  隔离 worker 直接实现；handoff 仅四情形
  R-V12-036  DAG-ready ≠ 立即开工；禁止 START_ALL
  R-V12-039  无 DAG 退化语义
  R-V12-044  LOW 票不得触发 ESCALATION
  R-V12-045  SEAM-FIRST 合法顺序与禁止顺序
  R-V12-046  分解的四条纪律（/to-tickets 不是架构生成器；必须读 execution-stage §6 …）
  R-V12-047  CODEGRAPH 三模式语义（细节下沉；**它的可达性由 #46 保证**）
  R-V12-055  授权路径自动推进不问"是否继续"
  R-V12-063  报告 novelty-first 七字段模板
  R-V12-085  部署验收记录只登记状态字段

  这几条的共同形态 = "决策树 / 默认值 / 退化路径 / 边界说明"。
  WHAT NOW ENFORCES IT = 不是"由谁强制"，而是**它们本来就不需要被记住**：
    它们是"当 X 时读 Y"的导航，HOT 只需要知道**存在一个 X→Y 的表**。
  WHERE = references/（各自的 owner 文件；HOT 保留指针）
  FAILS WHEN = 若 agent 找不到细节，会先看到指针 → 读 references
    （**可测**：这正是 #46 的"路由可达性"标的）
  LOAD-BEARING = 由 #46 的机械映射保证（ROUTE_DECLARED != DESTINATION_EXISTS）
  CAN_AGENT_FORGET = YES（细节） / NO（指针的存在）
  ⚠️ 关键前置：下沉必须与 **#46 的修复一起做**。否则"下沉"就是"把内容移到不可达处"。
  PROMOTION_REQUIRED = YES（依赖 #46）
```

### 3.2 需要新机制（本轮只映射，不实现）

#### R-V12-031 / 086 — 执行目标机械绑定（F-002，代价最明确）
```text
MECHANICAL_REPLACEMENT = worker 启动前置断言三元组
  WORKTREE_ABSOLUTE_PATH / EXPECTED_BASE_SHA / ACTUAL_HEAD_SHA，不匹配即拒绝执行
TARGET = D（前置门）| PREDICATE = YES（三字符串比较）| POSITIVE_CONTROL = YES
FAIL_CLOSED = 拒绝启动 + 记录不匹配三值
LOCAL_EVIDENCE = E3（H1 INVALID_001，已复现；修复后 6 个 worktree 全部 MATCH=YES）
EXTERNAL_EVIDENCE = E1（LongHorizon M-06 的 fresh-context episode 隐含"目标在启动时确定"）
PROMOTION_REQUIRED = YES（先 H5 验证形状）
REMOVAL_BLOCKER = 机制不存在
```

#### R-V12-033 / 077 — 评审 exact-SHA 绑定 + 历史不改写（F-003）
```text
MECHANICAL_REPLACEMENT = ① 评审记录中的被审 SHA == 即将合并的 SHA；
                        ② `REVIEWED_HEAD == candidate tip`（R5 已声明的 L0 钩子）
TARGET = C | PREDICATE = YES | POSITIVE_CONTROL = YES（改 SHA → 必须失败）
FAIL_CLOSED = merge 拒绝
LOCAL_EVIDENCE = E1（规则存在、实现缺失，可在仓内直接查证）
BLOCKER = 需要一个**结构化评审记录对象**（schemas/review-evidence.schema.json 已存在，
          但当前没有强制它在 PR 流程中被填写）→ 这是 #45 家族的准入条件问题
EXTERNAL_EVIDENCE = E1（LongHorizon M-07：auditor 是独立 episode ⇒ 可结构核验）
```

#### R-V12-011 / 012 / 013 — 门"是否仍承重"（F-010 = #45）
```text
MECHANICAL_REPLACEMENT = 语义正控：注入已知坏输入 → 门**必须**失败；
                        以及"声明 select 非空且与声明意图一致"
TARGET = C | PREDICATE = YES | POSITIVE_CONTROL = YES（定义上）
FAIL_CLOSED = 门无法失败 → 报 `GATE_NOT_LOAD_BEARING`，不得计入 PASS
LOCAL_EVIDENCE = **E3**（#45，2026-10-09 在 main 上四步复现，含哈希级恢复）
EXTERNAL_EVIDENCE = E1-SECONDARY（OpenAI 二手里提到"mechanical enforcement of architecture"，
          但因是二手，**不用于支撑判定**）
PROMOTION_REQUIRED = YES | DISPOSITION_EXPERIMENT = **#45**
REMOVAL_BLOCKER = 机制不存在；且这是 HOT 里最贵的一条（§0 的 4,100 字符里大半与之相关）
```

#### R-V12-083 + 047 — 路由/引用目标可达性（F-011 = #46）
```text
MECHANICAL_REPLACEMENT = 目标存在性（+ 可选 anchor），**且必须在声明 base 上跑**
TARGET = C | PREDICATE = YES | POSITIVE_CONTROL = YES
FAIL_CLOSED = 报 `ROUTE_TARGET_ABSENT`（既非 PASS 也非 FAIL）
LOCAL_EVIDENCE = E3（#46，git ls-tree 双向取证）
PROMOTION_REQUIRED = YES | DISPOSITION_EXPERIMENT = **#46**
RELATION = 所有 B 组下沉的**前置条件**（见 3.1 的 ⚠️）
```

#### R-V12-089 — run/实验产物必须落在持久化位置（F-015）
```text
MECHANICAL_REPLACEMENT = 断言产物路径不在易失目录（/tmp、$TMPDIR 直接拒绝）
TARGET = C | PREDICATE = YES（路径前缀）| POSITIVE_CONTROL = YES
FAIL_CLOSED = 拒绝写 / 强制复制到持久根并记录
LOCAL_EVIDENCE = E3（8 个 prunable worktree 现存）
EXTERNAL_EVIDENCE = NONE（外部材料未讨论产物易失性 —— 这条是**我们的**教训）
PROMOTION_REQUIRED = YES（先作为 H2/H5 的协议前置条件，验证成本为零后再考虑进 CI）
DISPOSITION = 记入 H2/H5 协议（PART 21：不新开 issue —— 它只影响 experiments/，非仓缺陷）
```

#### R-V12-091 / 093 — 守卫与仪器必须可失败（F-009 / F-017 / F-018）
```text
MECHANICAL_REPLACEMENT = ① 对每个守卫型断言要求一个正控（构造应失败输入并证明它失败）；
                        ② 仪器必须有**已知答案的合成输入**自检（不是拿仓内文件照算一遍）
TARGET = C | PREDICATE = PARTIAL（"是否有正控"可查；"是否检验正确对象"需人判）
POSITIVE_CONTROL = YES | FAIL_CLOSED = 无正控的守卫不得计入"已机械覆盖"
LOCAL_EVIDENCE = **E3**（H1 P1 已证伪；D7 的 59/5,916 已复算；selftest 空转已修复）
DISPOSITION = **并入 #45 的映射**（同族根因：PATTERN-A「空的东西看起来像满的」）。
              不新开 issue（PART 21：修法同一）。
```

#### R-V12-042 / 040 — 风险分级绑定与生命周期（最大单块）
```text
MECHANICAL_REPLACEMENT = 把"声明的风险级 → 所需评审强度"变成可核断言；
                        把 22 步生命周期变成状态机的合法转移
TARGET = D | PREDICATE = PARTIAL | POSITIVE_CONTROL = YES（对已定义的转移）
FAIL_CLOSED = 非法转移即拒绝进入下一步
LOCAL_EVIDENCE = E2（H1 t03/t04 声明 HIGH，但"是否真做了 adversarial"只由报告自述）
DISPOSITION = **H4 的标的**（风险分级与 MICRO/LOW 消融直接相关）
              + **H5 的标的**（状态机）
REMOVAL_BLOCKER = 机制不存在；且**不能靠设计消除** —— 需要实验证明边界在哪
```

#### R-V12-002 / 014 / 049 / 061 / 065 / 072 / 073 / 076 / 078 / 081 / 092 — 其余机械候选
```text
共同形态 = **已有部分机械 owner，但覆盖不完整**。逐条 REMOVAL_BLOCKER：
  002  block = "是否应用得当"不可机械（schema 只能证明"填了"）
  014  block = 票级收据未强制（schema 有，流程未接）
  049  block = CANDIDATE_GRAPH_COVERAGE 字段无强校验
  061  block = grounding hook 只读收据；"收据是否真实"不可核
  065  block = 汇报义务无 schema 级强制
  072  block = raw 归档规则靠人工 redaction
  073  block = MCP 集合检查存在但"配置是否为占位符模板"只覆盖部分
  076  block = **"独立"不可机械证明**（同一账号另一会话 = 合法形态）→ 只能覆盖最粗的身份相等
  078  block = "是否在语义范围内"需要人判；文件清单维度已可核
  081  block = B1–B4 的"是否真读了"不可核；B5 可
  092  block = 派生记录与原始记录的可溯性无机制
统一处置 = `MECHANIZATION_FOLLOWUP_CANDIDATE`（R8：无强论证不立 gate）
```

---

## 4. 量化：提示词减负潜力（PART 16）

### 4.1 计数

```text
CURRENT_RULE_COUNT        = 94（可复算：主表行数 == inventory 的 R-V12-* 去重计数）
HOT_RULE_COUNT            = 86（CUR ∈ {HOT_AUTO, HOT_AUTO_MEMORY, HOT_AUTO_PARTIAL,
                                HOT_NOT_DELIVERED, HOT_READ}）
  ├─ HOT_AUTO                 = 52   **真正自动投递**
  ├─ HOT_AUTO_MEMORY          =  3   经 MEMORY 指针投递
  ├─ HOT_AUTO_PARTIAL         =  2   所属章节部分被投递
  ├─ HOT_NOT_DELIVERED        = 16   **自称 HOT 但从不投递**
  └─ HOT_READ                 = 13   不自动注入，须显式全文读（RULES.md）
EXPERIMENT_ONLY               =  8   仅存在于实验线，尚未进 canonical
                                ────
                                  94

  ⇒ 真正自动到达 agent 的 HOT 规则 = 52 + 3 = **55 / 86（64%）**
  ⇒ 自称 HOT 却从不投递           = **16 条**

MECHANICAL_RULE_COUNT     = 26（TGT = C）
HARNESS_RULE_COUNT        = 18（TGT = D）
ADAPTER_RULE_COUNT        =  3（TGT = E）
REDUNDANT_RULE_COUNT      =  1（TGT = F）
KEEP_PENDING_EVIDENCE     =  2（TGT = G）
WARM_RULE_COUNT           =  0（当前无规则以 WARM 为**主**层；references 承载的是细节而非独立规则）
```

### 4.2 可分阶段移除的 HOT 规则

```text
HOT_RULES_REMOVABLE_NOW = 29    ← 逐个与主表的 RM=YES 列比对（材料自检强制）
  ├─ B 组 19：003,004,005,006,007,008,010,021,028,035,036,039,044,045,046,047,055,063,085
  ├─ C 组  6：048,070,071,074,079,082   （机械替代已在仓内并已验证）
  ├─ D 组  1：060                        （validate_project_state 已 FULL）
  ├─ E 组  2：066,067                    （注入通道事实 → 下沉 runtime adapter）
  └─ F 组  1：084                        （与 066 重复 ⇒ 去重）
  ⚠️ 其中 19 条（B 组）**以 #46 落地为前提** —— 否则"下沉"= 移到不可达处。
     故实操口径：这 19 条在 #46 修复后**立刻**可做。

NOT_YET_REMOVABLE = 30（主表 RM=NOT_YET），按**可能的解锁实验**分组。
  ⚠️ 分组是**假设**，不是承诺；实验可能证明它们**永远不该移除**。
  ├─ H2 可能解锁（WARM 可达/可载与 Skill 检索被证明后）= 002, 049, 065
  ├─ H4 可能解锁（风险绑定与程序性治理的边界被测出后）= 041, 042, 054, 064
  ├─ H5 可能解锁（状态/完成语义移入 harness 后）= 029, 030, 031, 033, 034, 037, 038,
  │      040, 057, 058, 059, 062, 076, 077, 078, 081                （16 条）
  └─ 无明确解锁实验（blocker 是"证据不存在"，非"某实验可产出"）= 011, 012, 014,
         061, 072, 073, 083                                          （7 条）

NEVER_REMOVABLE = 27（主表 RM=NO）
  ├─ A 组 25：语义不变量（违反后果不可机械检出）
  └─ G 组  2：方向已定但证据不足，保持原状

REMOVAL_BLOCKERS 的诚实记法：30 条 NOT_YET 里只有 23 条能指向一个具体实验；
余 7 条没有解锁路径。**不假装它们都有出路。**
```

### 4.3 字符投影（**PROJECTED ≠ OBSERVED**）

```text
CURRENT_HOT_CHARS          = 15,784（MEMORY 指针 2,028 + AGENTS.md 13,756）
  其中**实际投递** = 2,028 + 7,840 = 9,868
  其中**声明但从不投递** = 5,916

PROJECTED_V1_2_HOT_CHARS   = 见下三种口径（**全部为预测，非观测**）
  口径 1（保守：只做"如实重分类" + 现有机械面）：
    把 §6–§10 的 5,096 字符从"声明 HOT"改为"WARM/机械"标注，
    HOT 声明面 13,756 → 8,660；加上 MEMORY 2,028 ⇒ **10,688**
  口径 2（含 #46 修复后的 B 组下沉）：
    再下沉 §3/§4/§5 的细节约 2,800 字符 ⇒ AGENTS 面 ≈ 5,900 ⇒ **HOT ≈ 7,900**
  口径 3（H2/H4/H5 全部落地后）：
    再移除生命周期与风险分级细节约 2,200 字符 ⇒ AGENTS 面 ≈ 3,700 ⇒ **HOT ≈ 5,700**

PROJECTED_REDUCTION =
  口径 1 = 32%    口径 2 = 50%    口径 3 = 64%（相对 15,784）
  但**可见投递**的缩减更重要：当前 9,868 可见 → 口径 3 的 5,700 仍在 8,000 上限内，
  即 **PROJECTED_DELIVERY_TRUNCATION = 0**（当前是丢 5,916）

PROJECTED_ONLY = **YES**
  ⚠️ 以上三个口径**全部是预测**。它们**不是** H1 实验结果，**不得**被引用为"已验证的减负"。
     H1 的实测结论只有一条：`HOT_REDUCTION = 59.6%`（control 15,784 → variant 6,382），
     且 `H1_RESULT = INSUFFICIENT_EVIDENCE`（减负是否损失质量**未测出**）。
     本节数字的用途仅限"排优先级"，不构成任何 promotion 依据。
```

---

## 5. #45 / #46 的架构映射（PART 17 —— 只映射，不实现）

```text
#45  EXECUTED != LOAD_BEARING
  映射到的架构位置 = **Mechanical Gate integrity**
  目标层 = C（MECHANICAL_GATE）
  所属模式 = PATTERN-A「空的东西看起来像满的」（N6.3）
  需要什么证据才能处置 = ① 候选机制在**故意掏空的**门上演示（scratch copy）；
                        ② 新机制自身有正控（不得制造新的空 PASS —— 本仓已有 #33 的先例）；
                        ③ 独立评审 + PR
  应由哪个实验 disposition = **不需要新实验**。它是一个独立的工具票
                        （R8：无强论证不立 gate；但它**已有**强论证 —— E3 复现 + 真实代价）
  本轮动作 = 仅登记进本表 + 在 H2/H5 协议里把它列为"前置条件"（因为 H2 会大量依赖"门有效"）

#46  ROUTE_DECLARED != DESTINATION_EXISTS != DESTINATION_LOADABLE
  映射到的架构位置 = **Progressive Disclosure reachability**
  目标层 = C（MECHANICAL_GATE）
  所属模式 = PATTERN-C「声明与目的地脱节」
  需要什么证据才能处置 = ① 检查必须能在**声明 base** 上跑（base 相对）；
                        ② "没有路由声明"不得读成"所有路由都解析成功"（防空 PASS）；
                        ③ 至少一个以上载体/base 的证据才可 canonical 采纳
  应由哪个实验 disposition = **H2**（H2 的核心问题就是 WARM reachability / route
                        existence / route loadability）→ #46 是 H2 的**第一个被测对象**
  本轮动作 = 登记为 B 组下沉的**前置条件**（不做它，B 组就变成"移到不可达处"）
```

---

## 6. 本文件不做的事

```text
不做：实现任何门 / hook / 状态机（PART 20 禁止）
不做：修改 canonical（AGENTS/RULES/references 未动）
不做：把任何 EXTERNAL_EVIDENCE 升格为 TARGET（E1 只作方向佐证）
不做：承诺工期
```
