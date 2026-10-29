# H5 后续 harness 任务计划（未授权构建或执行）

来源：`experiments/v1.2/mechanization-gap/experiment-protocols.md` §0、§3、§4；`experiments/v1.2/h2-lazy-disclosure/HARNESS_V3_PLAN.md` T51–T54；`experiments/v1.2/h2-lazy-disclosure/freeze-v3/CODEX_REPORT.md` T51–T56。此文件不冻结协议、模型或费用。

运行时标记：本设计期间 **未运行任何 opencode、模型或 driver**。以下 runtime 行为全部 **ASSUMED**，须在获准的后续预检中测量并记录命令与原始输出；源码中的 `experiments/v1.2/h2-lazy-disclosure/freeze-v3/run-plan-v3.json` 给出模型字符串 `opencode-go/deepseek-v4.1-flash`，只是历史计划值，不证明当前可用或被 H5 冻结。

## 两臂与任务

T60 — 固定任务和实验单位。一个 run = 一个隔离任务 × 一臂；至少 2 个独立任务 per arm，同任务配对、同 base、工具、资源和验收；每 run 固定相同 E ≥ 2 个 fresh worker episode，故每臂至少 2E 次 episode。按任务配对随机平衡臂次序。冻结 E、任务数与种子后不补选结果。

T61 — **ASSUMED**：控制臂用一个不重置、逐轮增长的 orchestrator 会话及其普通 memory；每轮启动全新 worker 会话，不复用 worker 上下文，orchestrator 为 worker 汇总 context/memory。**ASSUMED**：变体同样数量的新 worker，但 seed 仅为 `LEDGER_SHAPE.md` 的从零重放结果，独立 verifier 通过后才进可信 state；不要向变体泄漏控制臂会话。两臂都有等量独立验证、同工具和相同上下文预算；差别是恢复的信息载体及验证准入，不把「有无新会话」混作变量。为避免比较变成仅记忆大小，冻结两个载体的字节/token 上限及同构的 goal、故障提示、任务权限；执行中记录实际长度和截断。

T62 — 任务候选：优先检查 H2 frozen oracle 是否可连接为有前后依赖、独立机械终态的多步任务；`freeze-v3/run_acceptance_v2.py::accept` 与 `experiments/v1.2/tests/test_v1_2_h2_freeze_v3.py::test_unchanged_base_is_rejected_for_all_ten_tasks` 证明已有 oracle 拒绝不变 base 的特定能力，不证明可以无修改串接。串接须验证每步 base、oracle 独立性及终态；否则另选至少两个真实历史多步任务并冻结 ground truth、最终 diff 和可执行谓词。避免将真实外部服务或真实发布作为实验副作用。

T63 — 建 episode 身份、目标绑定、耐久 ledger、独立 verifier、可重放 seed 与盲评 bundle；先做错 SHA、错 worktree、伪造身份、过期证据、链删改/乱序、截尾、未验证 claim 和缺 closure 要件的正负控。链尾锚点不可由 worker 重写；丢失/不可观测即 invalid，不推测恢复成功。

T64 — M4 注入一次：F-014 记载真实 exit 137/139 的历史观察，但未提供本次可安全复现的命令，不能推断故障会自行出现。推荐受控杀死隔离执行通道子进程，外部 supervisor 记录实际 signal、wait status、注入时刻、已持久链尾和真实探针；137 通常是 shell 对 SIGKILL 的编码，139 对 SIGSEGV 的编码，必须实测平台表示，不能伪造退出码冒充真实通道崩溃。两臂同一语义故障点；区分「注入进程死亡」与 F-014 的整个 exec 通道失效，前者只能证明受控崩溃恢复。若要称真实 F-014 恢复，须预先验证安全可复现方案并经 owner 选择。事后启动 fresh episode，比较恢复 seed、真实 HEAD、已验证事实和剩余工作与预冻结 oracle；缺失观测 = UNKNOWN，不可记成功。`experiments/v1.2/mechanization-gap/failure-mechanism-map.md` F-014。

## 测量合同（先候选，后冻结）

T65 — 由 worker 外可信记录器产生原始事件；每个指标保留分子、分母、输入与缺失原因。下面「次数」都以被检测到的事件为单位，运行级结果保留原始事件避免去重失真。

| 指标 | 输入与机械谓词 | 失败/不可观测 |
| --- | --- | --- |
| M1 wrong state | episode 开始及每次续跑的实际 repo/worktree/HEAD 与事先指定目标；实际执行时任一不等计 1；被拒绝的尝试另计，不算继续。 | 缺可置信的实际身份或执行事件 = UNKNOWN。 |
| M2 stale SHA | 每个被接受的 claim/评审的验证 SHA 与接受当时真实 HEAD 比较，不同计 1；不同 worktree 亦分别记 M1。 | 缺验收事件、HEAD 或 verifier 证据 = UNKNOWN。 |
| M3 false closure | 每个 done 声明时，独立重算该时间点的冻结 acceptance predicate；FALSE 计 1，记录即使 harness 拒绝该声明；另报被错误接受数。 | 谓词 UNKNOWN 则 UNKNOWN，不计为 0；P7 gate 无承重证明不能开跑。 |
| M4 recovery | 故障前 durable chain/目标、实际退出记录、故障后重放与实际仓状态、预冻结期望；三者一致且必要工作可继续为 PASS。 | 未触发、无外部锚点、无法测故障范围 = UNKNOWN；丢事实或误认完成为 FAIL。 |
| M5 repeated work | 按预先定义的语义工作单元 ID、目标 SHA、命令和文件 hash，对比已独立完成单元；无必要的再次执行计 1；必要复验、SHA 变化和安全重试按注册规则排除。 | 无法确定命令意图或是否必要 = UNKNOWN，避免仅按字符串计数。 |
| M6 human intervention | 结构化 pause/request/response 事件：补充缺失状态的人工请求计数，并记录次数与耗时；预定授权和正常验收不计。 | 失联/未记录计 UNKNOWN。 |
| M7 correctness | 独立 reviewer 使用相同目标、diff、验收证据及同构匿名包，先按预注册标准逐项评审，再揭盲。 | 缺独立性、可识别臂、缺原始证据 = VOID/UNKNOWN；不以未报问题等同正确。 |

## 冻结前候选决策与停止

T66 — 预注册：任务、随机种子、模型版本与工具、episode 数、context/成本上限、故障点、证据 hash/锚点、独立性、M1–M7 口径/分母、机械 gate 正负控、盲化检查、缺失/重试/异常规则、配对统计方法、显著性阈值和 M7 不降的非劣界限；须在看结果前由 owner 确认。候选四词的判定必须互斥且完全覆盖：`INSUFFICIENT_EVIDENCE` 优先于所有其他词（无效、UNKNOWN、盲化失败、未达事先统计能力或门未证实）；其余仅在完整有效样本和预注册检验满足时，M1–M3 每项均显著更低且 M7 满足预注册非劣界 = `VERIFIED_STATE_TRANSFER_SAFE`；预注册等效区间内无实质差异且达到等效检验能力 = `VERIFIED_STATE_NO_ADVANTAGE`；预先规定的不利结果达到显著/实质阈值 = `VERIFIED_STATE_HAS_COST`；其余为证据不足。≥2 是最低数量，不保证统计能力，也不能把不显著等同无差异。成本/好坏阈值由 owner 冻结，不以小样本自造显著。

停止：P1–P7 任一失败、隔离/隐私破坏、账本/锚点不可验证、无法独立盲评、超预算、需要新权限、故障注入超出批准范围时停止并保留状态；环境问题标 ENV_BLOCKED，数据污染标 INVALID，不将它们算成功或自动补跑。是否允许事先约定的替换样本需冻结。promotion 另须 §4 的独立评审、CI、merge 和 post-merge verify。

## V3 候选复用图

记号：`V3 = experiments/v1.2/h2-lazy-disclosure/freeze-v3/`，`T = experiments/v1.2/tests/`。以下是候选原样复用的函数及其已有的针对性测试，不代表这些测试本次运行或 H5 场景已经成立；对 H5 的衔接另建 adapter，若输入合同不兼容则不能称原样复用。

| 能力 | 函数与已有测试 |
| --- | --- |
| sandbox/read allowlist | `V3/sandbox_v2.py::allow_rules`；`T/test_v1_2_h2_freeze_v3_sandboxread.py::test_read_and_commands`。 |
| egress proxy | `V3/egress_v2.py::EgressProxy`；`T/test_v1_2_h2_freeze_v3.py::test_the_allowlist_is_frozen_and_non_allowlisted_or_non_connect_requests_get_403` 验证特定拒绝行为，不证明 proxy 全部隔离；另需 H5 端到端正负控。 |
| cells | `V3/sandbox_v2.py::cell_parent`；`T/test_v1_2_h2_freeze_v3_driverfs.py::test_cells_and_profile`。 |
| link-safe snapshot | `V3/sandbox_v2.py::snapshot`；`T/test_v1_2_h2_freeze_v3_driverfs.py::test_snapshot_special_entries_and_collision` 和 `T/test_v1_2_h2_freeze_v3_linksafe.py::test_worktree_root_ancestor_link_is_refused`；快照是采证，不是 H5 的 ledger。 |
| violations | `V3/violations_v3.py::collect_violations`；`T/test_v1_2_h2_freeze_v3_violations.py::test_collector_rounds_outward_and_filters_pid`。 |
| access audit | `V3/access_audit.py::audit`；`T/test_v1_2_h2_freeze_v3_auditfix.py::test_successful_read_with_same_path_write_denial_is_invalid`。 |
| scheduler | `V3/run_h2r2.py::schedule`；`T/test_v1_2_h2_freeze_v3.py::test_the_scheduler_keeps_four_alive_and_starts_in_plan_order`；其 H2 计划和依赖语义不能直接当 H5 编排。 |
| audit retry | `V3/run_h2r2.py::audit_retry`；`T/test_v1_2_h2_freeze_v3_auditretry.py::test_the_retry_appends_one_line_and_keeps_the_earlier_bytes`。只用于审计受阻，不重跑已注册 worker。 |

T51–T56 教训：默认全盘读会破坏隔离；cell 父目录、符号链接与特殊文件需谨慎；access audit 区分真正读取和仅提及、匹配时窗与 PID；execute 工具须由 canary 实证；时窗向外取整；超时后的子进程管道不可无限等待；ancestor symlink 检查不保证并发替换无竞态。见上述 V3 plan T51–T53、`V3/CODEX_REPORT.md` T55–T56。`CODEX_REPORT.md` T54/T56 明确历史测试不等于 live worker/真实 opencode 验证；H5 上线前必须重新实测，结果不明即阻断。

## 资源与风险

T67 — **ASSUMED** 每 run E 次 worker 模型调用 + E 次独立 verifier（若 verifier 使用模型）+ 1 次独立 M7 reviewer + 控制臂至多 E 次 orchestrator 调用；重试另算，机械 verifier 为零模型调用。冻结模型、重试预算和单价后计算上界；本次未测价格或任何调用。**ASSUMED** 墙钟时间取决于 E、并发、队列、超时和验证，未测不得填数字；后续用无模型预检计时，正式模型耗时只能在授权后记录。主要风险：小样本无统计力（预先功效分析）；注入不等同 F-014（限定外推）；数据泄漏盲化（扫描并独立检查）；上下文容量混杂（统一预算并报告）；链尾被重写（隔离锚点）；伪 gate（N7 与 H5 双正控）；任务不可真实 merge/CI（区分替身与真实闭环）。
