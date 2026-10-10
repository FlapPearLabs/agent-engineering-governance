# N6.3 — Failure → Mechanism Mapping（V1.2 mechanization gap analysis）

> **状态 = N6.3 本轮产物。非 canonical。**
> 目的：把**失败**（不是规则）作为一等对象，问"这条失败现在靠什么防？能否改由机械防？"
> 规则清单（N6.1）回答"agent 被要求做什么"；本文件回答"不这么做会怎样、以及谁来拦"。

## 0. 最重要的诚实声明

PART 9 给出的失败清单里，**只有一部分在本仓真实发生过**。把假设失败写成已发生失败，
会让后续的机械化决策建立在虚构的需求上（正是 R8「每个机制必须回答防哪次真实失效」要防的）。

```text
EVIDENCE_LEVEL 取值（本文件专用，与外部 E1 无关）：
  E3_LOCAL_REPRODUCIBLE = 本地真实发生 + 有精确 SHA/命令 + 可再次演示（含正控）
  E2_LOCAL_SINGLE       = 本地真实发生 + 有精确 SHA/记录，但未构造正控
  E1_LOCAL_ATTESTED     = 本地真实发生，但只有流程记录（对话/报告），无独立可复算证据
  HYPOTHESIS_NO_LOCAL   = **本仓未发生**；来自外部材料或推理。**不得**据此单独立 gate。
```

```text
本文件统计（**由材料自检机核对过**；首次手写时是错的 —— 见文末 §5）：
  E3_LOCAL_REPRODUCIBLE = 9
  E2_LOCAL_SINGLE       = 6
  E1_LOCAL_ATTESTED     = 1
  HYPOTHESIS_NO_LOCAL   = 6
  合计                  = 22
```

> ⚠️ **HYPOTHESIS_NO_LOCAL 占了 6 条（27%）**。这 6 条的
> `MECHANICAL_REPLACEMENT_CANDIDATE` 一栏**不得**被当作"该建的门"。
> 按 R8，它们最多是 `MECHANIZATION_FOLLOWUP_CANDIDATE`。

---

## 1. 失败登记

### F-001 — Wrong repository（在错的仓里工作）
```text
REAL_INCIDENT = 否
EXACT_EVIDENCE = NONE（HYPOTHESIS_NO_LOCAL）
CURRENT_PREVENTION = BOOTSTRAP_CHECKLIST B5（核验新鲜 remote truth）+ 各 worktree 的 remote 配置
CURRENT_PROMPT_RULE = R-V12-081 B5；R-V12-019 AUTHORITY BEFORE ACTION
MECHANICAL_REPLACEMENT_CANDIDATE = 执行前断言 `git remote get-url origin` == 期望的 repo URL
TARGET_LAYER = MECHANICAL_GATE（成本极低）
DETERMINISTIC_PREDICATE = YES
POSITIVE_CONTROL_AVAILABLE = YES（改 remote 指向 → 断言必须失败）
FAIL_CLOSED_BEHAVIOR = 断言失败即拒绝执行任何写操作
RESIDUAL_RISK = 低。但注意：H1 的 INVALID_001 是"同一 repo 的错误目录"，
  说明真正的风险形态是**目录而非 URL**（见 F-002）
EVIDENCE_LEVEL = HYPOTHESIS_NO_LOCAL
### F-002 — Wrong worktree / 执行目标未被机械绑定 ★
```text
REAL_INCIDENT = **是**。H1 首对 t01 运行：编排者未把 worktree 绝对路径写进 worker prompt，
      两臂 worker 实际停留在治理 HEAD `a7f9e7c`（而非 replay base `c08f6f8`），
      该 HEAD 上缺陷已被修复 ⇒ 任务成 no-op，整对运行作废。
EXACT_EVIDENCE = 见 runs/README.md `INVALID_001 / WRONG_EXECUTION_TARGET`；
      `6d841d5` 是 `a7f9e7c` 的祖先（已核）；HEAD 上该断言 grep 0 命中
CURRENT_PREVENTION = 事后补救：重跑时把 `cd <abs>` + `git rev-parse HEAD` 断言写进 prompt
CURRENT_PROMPT_RULE = R-V12-086（本轮新登记，**尚未进 canonical**）
MECHANICAL_REPLACEMENT_CANDIDATE = worker 启动前置断言三元组
      `WORKTREE_ABSOLUTE_PATH / EXPECTED_BASE_SHA / ACTUAL_HEAD_SHA`，
      不匹配即**不得执行任务**
TARGET_LAYER = HARNESS_STATE_MACHINE（前置门）
DETERMINISTIC_PREDICATE = YES（三个字符串比较）
POSITIVE_CONTROL_AVAILABLE = YES（把 worker 指向错误目录 → 必须拒绝启动）
FAIL_CLOSED_BEHAVIOR = 拒绝启动，且把不匹配三值记入 run 记录
RESIDUAL_RISK = 低。**这是我们代价最明确的一条**：一次作废 run + 一整轮返工。
EVIDENCE_LEVEL = E3_LOCAL_REPRODUCIBLE  # 错误形态已复现，修复后重复验证过 6 个 worktree
```

### F-003 — Stale-SHA review（评审绑定到旧 SHA）
```text
REAL_INCIDENT = 是（流程层面真实存在，且本仓有明文规则但无门）
EXACT_EVIDENCE = RULES.md R5 的 V 钩子写着 "REVIEWED_HEAD == candidate tip（适用时，L0 机械核验）"，
      **但仓内没有任何脚本实现该断言**（`scripts/` 全面检视后无对应检查）
CURRENT_PREVENTION = 评审记录里写 SHA；靠人比对
CURRENT_PROMPT_RULE = R-V12-077（R5）+ R-V12-033（INTEGRATOR quorum）
MECHANICAL_REPLACEMENT_CANDIDATE = 断言"评审记录中的被审 SHA == 即将合并的 SHA"
TARGET_LAYER = MECHANICAL_GATE
DETERMINISTIC_PREDICATE = YES
POSITIVE_CONTROL_AVAILABLE = YES（把 review 的 SHA 改成另一个 → 门必须失败）
FAIL_CLOSED_BEHAVIOR = merge gate 拒绝
RESIDUAL_RISK = 中。难点是"评审记录"目前是分散的（PR comment / 报告文本），
      要机械核验先得有一个**结构化的评审记录对象**（review-evidence schema 已存在但未强制）
EVIDENCE_LEVEL = E1_LOCAL_ATTESTED  # 规则存在、实现缺失，均可在仓内直接查证；无 incident 记录
```

### F-004 — Review completed after merge（先合并后评审）
```text
REAL_INCIDENT = 否
EXACT_EVIDENCE = NONE（HYPOTHESIS_NO_LOCAL）
CURRENT_PREVENTION = 流程顺序纪律（AGENTS §3 生命周期：fresh independent review → PR → real CI → merge gate）
CURRENT_PROMPT_RULE = R-V12-040（生命周期）+ R-V12-033
MECHANICAL_REPLACEMENT_CANDIDATE = merge 前置断言：存在一条 review 记录，其 SHA == 候选 SHA，
      且其时间戳早于 merge 请求时间
TARGET_LAYER = HARNESS_STATE_MACHINE
DETERMINISTIC_PREDICATE = YES（时间戳 + SHA）
POSITIVE_CONTROL_AVAILABLE = YES
FAIL_CLOSED_BEHAVIOR = 拒绝 merge
RESIDUAL_RISK = 中（依赖结构化 review 对象，同 F-003）
EVIDENCE_LEVEL = HYPOTHESIS_NO_LOCAL
### F-005 — Review exists but findings ignored（有评审结论但 finding 被忽略）
```text
REAL_INCIDENT = 否（本仓历史上 finding 都被处置了）
EXACT_EVIDENCE = 反证：本仓 PR #47 的 review 1 = CHANGES_REQUIRED（1×P1+1×P2+5×P3），
      7 条全部处置后才进入 review 2 —— 是**正面实例**
CURRENT_PREVENTION = 修复预算 + 逐条 disposition + resolved 线程
CURRENT_PROMPT_RULE = R-V12-052（修复收敛）+ R-V12-063（novelty-first 报告）
MECHANICAL_REPLACEMENT_CANDIDATE = 断言"每条 review finding 都有 disposition 且 P0/P1 为 0 才可 merge"
TARGET_LAYER = MECHANICAL_GATE
DETERMINISTIC_PREDICATE = PARTIAL（"是否被处置"需要 finding 的结构化列表）
POSITIVE_CONTROL_AVAILABLE = YES
FAIL_CLOSED_BEHAVIOR = merge 拒绝（存在未处置的 P0/P1）
RESIDUAL_RISK = 中。"处置"的语义（拒绝 vs 修复 vs 记录为后续）本身是判断
EVIDENCE_LEVEL = HYPOTHESIS_NO_LOCAL
### F-006 — 一个 reviewer APPROVE 而另一个有 finding（评审分歧被多数票掩盖）
```text
REAL_INCIDENT = 否
EXACT_EVIDENCE = NONE（HYPOTHESIS_NO_LOCAL）
CURRENT_PREVENTION = AGENTS §6 修复收敛 + CONVERGENCE_ARBITER 五选一；
      §8 治理变更要求**双独立评审都对同一 exact HEAD PASS**
CURRENT_PROMPT_RULE = R-V12-052 / R-V12-062
MECHANICAL_REPLACEMENT_CANDIDATE = 对治理变更：断言存在 ≥2 条独立评审记录且**全部**为 PASS
      （不是 quorum，是合取）
TARGET_LAYER = MECHANICAL_GATE
DETERMINISTIC_PREDICATE = YES（若评审记录结构化）
POSITIVE_CONTROL_AVAILABLE = YES
FAIL_CLOSED_BEHAVIOR = 治理变更在任一致命 finding 未处置时不得 merge
RESIDUAL_RISK = 中。"独立"本身不可机械证明（见 F-007）
EVIDENCE_LEVEL = HYPOTHESIS_NO_LOCAL
### F-007 — 自审冒充独立评审（self-review 替换 gate）
```text
REAL_INCIDENT = 否（作为 R4 的动机存在，但无本仓 incident）
EXACT_EVIDENCE = NONE。反面：本仓三轮 review 都用**新 context** 实现，
      且 reviewer 明确自报"未参与任一臂执行"（H1 runs 记录可查）
CURRENT_PREVENTION = R4 + 评审记录自述
CURRENT_PROMPT_RULE = R-V12-075（R4）/ R-V12-030（WORKER 六禁止）
MECHANICAL_REPLACEMENT_CANDIDATE = 断言"review 的执行者身份 != candidate 的作者身份"
      （本仓已有 `--commit-metadata` 查 author/committer 的先例，可复用同一数据源）
TARGET_LAYER = MECHANICAL_GATE
DETERMINISTIC_PREDICATE = PARTIAL（身份可比对；但"受自己影响"不可判定）
POSITIVE_CONTROL_AVAILABLE = PARTIAL
FAIL_CLOSED_BEHAVIOR = 身份相同时拒绝把该评审计入 gate
RESIDUAL_RISK = **高**。"派生受自己影响的 reviewer"在技术上无法完全机械识别
      （同一账号下的另一个会话就是合法形态）。机械门只能覆盖"同一身份"这一最粗的失败。
EVIDENCE_LEVEL = HYPOTHESIS_NO_LOCAL
### F-008 — CI green while the intended path is unreachable（CI 绿但意图路径不可达）
```text
REAL_INCIDENT = **是**（形态等价）。H1 t03 两臂都报：请求的公开候选面扫描器在该 replay base
      **不存在**（`scripts/` 下只有 2 个校验器）；而同一套 CI 在该树上仍会通过它实际运行的那些步骤。
EXACT_EVIDENCE = `git ls-tree af4df6a scripts/` 只列 2 个校验器（编排者独立复核）；
      两臂各自独立报告同一事实
CURRENT_PREVENTION = 无（"被请求的检查不存在"不会被现有任何门发现）
CURRENT_PROMPT_RULE = R-V12-012（CONFIGURED_STATIC_TOOLING_MUST_RUN）—— 但它管"配置了就须跑"，
      **不管"被引用的检查是否存在"**
MECHANICAL_REPLACEMENT_CANDIDATE = 断言"任务/流程引用的每个检查点，其目标在声明的 base 上存在"
TARGET_LAYER = MECHANICAL_GATE
DETERMINISTIC_PREDICATE = YES（路径存在性）
POSITIVE_CONTROL_AVAILABLE = YES（引用一个不存在的脚本 → 必须失败）
FAIL_CLOSED_BEHAVIOR = 报告 `CHECK_DECLARED_BUT_ABSENT`，不得当作 PASS 也不得当作 FAIL
RESIDUAL_RISK = 低。**与 #46 同族**（ROUTE_DECLARED != DESTINATION_EXISTS）——
      差别只在"路由表"与"任务指令"。
EVIDENCE_LEVEL = E2_LOCAL_SINGLE
### F-009 — Negative assertion without positive control（只有否证没有正控）
```text
REAL_INCIDENT = **是**。H1 的 `TestCanonicalUntouched` 两个测试都只看 `git status --porcelain`，
      而评审时工作树本就干净 ⇒ 断言**恒真**，任何**已提交**的 canonical 越界都能通过。
EXACT_EVIDENCE = PR #47 review 1 的 P1；修复后活体证伪：探针提交触碰 `references/ticket-lane.md`
      → 测试 FAIL（`committed changes outside experiments/v1.2/: ['references/ticket-lane.md']`），
      非破坏性还原后文件 SHA256 前后一致
CURRENT_PREVENTION = **修复后**：断言已提交变更集（`merge-base..HEAD`），无 base ref 时显式 fail
CURRENT_PROMPT_RULE = R-V12-091（本轮新登记）
MECHANICAL_REPLACEMENT_CANDIDATE = 对每个"守卫型"断言要求一个**正控**：构造应当失败的输入，
      证明它真的失败
TARGET_LAYER = MECHANICAL_GATE（正控可脚本化）
DETERMINISTIC_PREDICATE = PARTIAL（"这条断言是否可失败"可探针；"是否检验了正确对象"需人判）
POSITIVE_CONTROL_AVAILABLE = YES（本身就是关于正控的规则）
FAIL_CLOSED_BEHAVIOR = 无正控的守卫断言不得计入"已机械覆盖"
RESIDUAL_RISK = 中。正控只能证明"能失败"，不能证明"在正确对象上失败"。
EVIDENCE_LEVEL = E3_LOCAL_REPRODUCIBLE
### F-010 — Gate executes but its predicate is hollow（门跑了但谓词已空）★
```text
REAL_INCIDENT = **是**。Issue #45：`ruff.toml` 的 `select` 清空后，
      `ruff check .` 对**注入的真实 F841 缺陷**报 `All checks passed!`，
      而 `validate_governance.py` 仍 35/35、`ci-executes-static-gate` 仍 PASS。
EXACT_EVIDENCE = 2026-10-09 在 `562cb5c` 上复现（A/B/C/D 四步，含恢复前后 `ruff.toml`
      SHA256 一致 `5e1a8244…`）；issue #45 正文含最小反例
CURRENT_PREVENTION = 无（35 项治理检查无一读 `ruff.toml`）
CURRENT_PROMPT_RULE = R-V12-012 / R-V12-013（门状态不可坍缩）—— 但"谓词是否仍然承重"是**下一层**，
      不在现有措辞里
MECHANICAL_REPLACEMENT_CANDIDATE = 语义正控：注入已知坏输入，断言门**必须失败**；
      以及"声明的 select 集合非空且与声明意图一致"
TARGET_LAYER = MECHANICAL_GATE
DETERMINISTIC_PREDICATE = YES（注入 → 期望失败）
POSITIVE_CONTROL_AVAILABLE = YES（定义上）
FAIL_CLOSED_BEHAVIOR = 门无法失败时报告 `GATE_NOT_LOAD_BEARING`，不得计入 PASS
RESIDUAL_RISK = 低-中。**这是 #45 的机械映射**；本轮只映射，不实现。
EVIDENCE_LEVEL = E3_LOCAL_REPRODUCIBLE
### F-011 — Route declared but target missing（路由声明的目标不存在）★
```text
REAL_INCIDENT = **是**。Issue #46：渐进披露路由表把评审任务指向
      `references/review-evidence.md`，而该文件在 replay base `e1da154` **不存在**
      （该 base 的 `references/` 只有 10 项）；它在 current main 存在，由 **`2ed08f6`（即该任务的候选本身）**引入。
EXACT_EVIDENCE = `git ls-tree e1da154 references/` → 10 项，无该文件；
      `git cat-file -e origin/main:references/review-evidence.md` → 存在
CURRENT_PREVENTION = 无。`validate_governance` 的 markdown 链接检查只覆盖**固定 canonical 文件清单**
      （`CANONICAL_FILES`），而路由目标是**围栏代码块里的纯文本路径**，两个维度都不在检查面内
CURRENT_PROMPT_RULE = R-V12-083（交付契约不检查目的地）
MECHANICAL_REPLACEMENT_CANDIDATE = 路由目标存在性（路径可解析 + 可选 anchor 存在）
TARGET_LAYER = MECHANICAL_GATE
DETERMINISTIC_PREDICATE = YES
POSITIVE_CONTROL_AVAILABLE = YES（指向一个不存在的目标 → 必须失败）
FAIL_CLOSED_BEHAVIOR = 报告 `ROUTE_TARGET_ABSENT`（**注意：#46 已指明该检查必须能在声明 base 上跑**，
      只在 HEAD 跑看不出来）
RESIDUAL_RISK = 低。**这是 #46 的机械映射**；本轮只映射，不实现。
EVIDENCE_LEVEL = E3_LOCAL_REPRODUCIBLE
### F-012 — Memory saved but not enforced（写进记忆但没人执行）
```text
REAL_INCIDENT = **是**（作为既有设计缺口，且本仓自己承认）
EXACT_EVIDENCE = 本仓 §7.1 明文："Hook 只保证 Agent 不能忘记写，**绝不代写语义决策**"，
      且 `adapters/zcode/hooks/state_flush_guard.py` 只 append 信号字符串、从不写状态索引
      （H1 t03 臂的 NC5 以"索引 SHA 前后不变"机械证明过该边界）
CURRENT_PREVENTION = hook 保证"不忘记写"；但"写了之后有没有被遵守"无机制
CURRENT_PROMPT_RULE = R-V12-059 / R-V12-061
MECHANICAL_REPLACEMENT_CANDIDATE = 不可直接机械化（"是否遵守了一条记忆"是语义判断）。
      可做的是**收窄**：把"记忆"限制为机器可读的结构化字段，从而让部分子集可核
TARGET_LAYER = HARNESS_STATE_MACHINE（把"记忆"变成"状态转移的条件"而非"文本"）
DETERMINISTIC_PREDICATE = NO（对自由文本） / PARTIAL（对结构化字段）
POSITIVE_CONTROL_AVAILABLE = N/A
FAIL_CLOSED_BEHAVIOR = N/A
RESIDUAL_RISK = **高**。这是"提示词治理"的根问题，也是 V1.2 的核心标的。
      外部材料（M-02/M-12）给的解法是"状态只能由独立验证推进"，那才可核。
EVIDENCE_LEVEL = E2_LOCAL_SINGLE  # 本仓自述 + hook 行为已验证
```

### F-013 — Agent says CLOSED before evidence closure（假闭环）★
```text
REAL_INCIDENT = 否（本仓未发生；我们反而不停地在**推迟**闭环 —— 见 H1 D6）
EXACT_EVIDENCE = 反证：H1 第一轮 PART 23 未满足被显式记录并承认（"已尝试并取证，非未尝试"），
      随后单独一轮补闭环。这是 R3 生效的正面实例。
CURRENT_PREVENTION = R3 + AGENTS §7 STOP（MILESTONE_COMPLETE）+ H1 的三层区分
CURRENT_PROMPT_RULE = R-V12-075 / R-V12-024
MECHANICAL_REPLACEMENT_CANDIDATE = **completion 必须是 harness 级判定**（M-12）：
      完成只有当"结构化完成谓词"成立时才被接受，执行者自述降级为 claim
TARGET_LAYER = HARNESS_STATE_MACHINE（H5 的核心）
DETERMINISTIC_PREDICATE = PARTIAL（谓词本身可定义：例如"存在 merge SHA 且其内容含预期产物"）
POSITIVE_CONTROL_AVAILABLE = YES（声称完成但缺谓词要件 → 必须被拒绝）
FAIL_CLOSED_BEHAVIOR = 拒绝完成，回灌缺失项（LongHorizon 的 `_invalid_completion_feedback` 形状）
RESIDUAL_RISK = 中。"完成的谓词"因任务而异，普适化很难；但**"缺少证据即不得完成"**是普适的。
EVIDENCE_LEVEL = HYPOTHESIS_NO_LOCAL  # 机制缺失已确认；失败本身未发生
```

### F-014 — Shell / runtime collapse（执行通道整体死亡）
```text
REAL_INCIDENT = **是，反复发生**。三次：H1 第二轮（exit 137）、H1 第三轮（exit 137/139，
      连裸 `echo` 都死、subagent 的 `run_in_background` 兜底也失效）、本轮之前的一次（同型）。
EXACT_EVIDENCE = 各轮 daily log；本轮（2026-10-09）有完整记录：前台命令 exit 137/139，
      后台通道一度同样失败，最终恢复；期间 Read/Glob/Write/Edit 仍可用
CURRENT_PREVENTION = 无（环境事实，非治理对象）
CURRENT_PROMPT_RULE = R-V12-094（环境故障记为环境，不记为候选缺陷）
MECHANICAL_REPLACEMENT_CANDIDATE = **不是治理规则，是 runtime adapter 的能力声明**：
      声明 `CAN_RUN_TESTS = NO` 时的行为（如实上报而非编造）
TARGET_LAYER = RUNTIME_ADAPTER
DETERMINISTIC_PREDICATE = YES（探针命令失败 = 通道不可用）
POSITIVE_CONTROL_AVAILABLE = YES（探针本身就是）
FAIL_CLOSED_BEHAVIOR = 报告 ENV_BLOCKED，**不得**把未执行的检查记为通过（R3）
RESIDUAL_RISK = 低（就治理而言）。真正的风险是**有人在这种情况下编造结果** —— 那由 R3 管。
EVIDENCE_LEVEL = E3_LOCAL_REPRODUCIBLE  # 探针可重复
```

### F-015 — Evidence lost from /tmp（证据留在易失目录）★
```text
REAL_INCIDENT = **是**。H1 run 产物位于 `/tmp/h1-runs/`，被系统清理；
      8 个 replay worktree 全部 prunable；run 的**实际 diff 不可事后重放**。
EXACT_EVIDENCE = `git worktree list` 显示 8 条 `prunable`；`/tmp/h1-runs` 不存在；
      已写入 runs/README.md `REPLAY_WORKTREE_REVERIFIABLE_NOW = NO`
CURRENT_PREVENTION = 无（当时未意识到）→ 事后补救 = 在记录里显式声明不可复验
CURRENT_PROMPT_RULE = R-V12-089（本轮新登记）
MECHANICAL_REPLACEMENT_CANDIDATE = 断言实验/run 产物路径**不在易失目录**
      （白名单持久化根；`/tmp`、`$TMPDIR` 直接拒绝）
TARGET_LAYER = MECHANICAL_GATE（成本极低）
DETERMINISTIC_PREDICATE = YES（路径前缀比较）
POSITIVE_CONTROL_AVAILABLE = YES
FAIL_CLOSED_BEHAVIOR = 拒绝把产物写到易失目录 / 或强制复制到持久根并记录
RESIDUAL_RISK = 低。**代价已付**：一个完整实验的证据面被永久削弱。
EVIDENCE_LEVEL = E3_LOCAL_REPRODUCIBLE
### F-016 — Invalid replay accidentally counted（作废 run 被计入）
```text
REAL_INCIDENT = 否（H1 **正确地**排除了 2 个作废 run）
EXACT_EVIDENCE = 反证 + 防回归：`runs/README.md` §3 保留 `INVALID_001/002` 及其归因；
      材料自检 `test_voided_runs_are_retained_in_the_record` 断言其**必须仍在**（删除会掩盖 harness 缺陷）；
      `test_superseded_records_are_not_counted_as_runs` 断言取代记录不重复计数
CURRENT_PREVENTION = 已机械化（这是本仓的**优点**）
CURRENT_PROMPT_RULE = R-V12-092
MECHANICAL_REPLACEMENT_CANDIDATE = 已有；可扩展为"VALID_RUNS 计数必须等于 run registry 的声明"
TARGET_LAYER = MECHANICAL_GATE（已存在）
DETERMINISTIC_PREDICATE = YES
POSITIVE_CONTROL_AVAILABLE = YES
FAIL_CLOSED_BEHAVIOR = 计数不一致即失败
RESIDUAL_RISK = 低
EVIDENCE_LEVEL = E2_LOCAL_SINGLE  # 机制存在并已断言；无 incident
```

### F-017 — Measurement instrument lying（仪器在说谎）★
```text
REAL_INCIDENT = **是**。H1 `hot_inventory.py` 的 `dropped_js_chars` 被实现成
      「截断行自身的溢出量」= **59**，而真值是「总量 − 可见量」= **5,916**（低估约 100×）。
EXACT_EVIDENCE = results.md §2 D7；修复后仪器输出 `dropped_js_chars = 5916`，
      且新增 T2e 断言"多行输入下丢弃尾部必须 > 截断行溢出量"
CURRENT_PREVENTION = **修复后**：口径改为 total−visible；selftest 恢复合成算术自检
CURRENT_PROMPT_RULE = R-V12-093
MECHANICAL_REPLACEMENT_CANDIDATE = 仪器必须有一个**已知答案的合成输入**自检
      （不是用仓内文件"照着算一遍"——那只能证明自洽，不能证明口径对）
TARGET_LAYER = MECHANICAL_GATE
DETERMINISTIC_PREDICATE = YES（合成输入 → 期望输出）
POSITIVE_CONTROL_AVAILABLE = YES（定义上）
FAIL_CLOSED_BEHAVIOR = 口径自检失败即拒绝产出数字
RESIDUAL_RISK = 中。**这是最隐蔽的一类**：错误的仪器会产出"可复算"的错数字，
      而"可复算"给人以可信感。
EVIDENCE_LEVEL = E3_LOCAL_REPRODUCIBLE
### F-018 — Selftest itself empty / vacuous（自检本身是空的）★
```text
REAL_INCIDENT = **是**。同一个 H1 仪器缺陷的直接原因：selftest 的 T2 项被写成
      `del g, exact`（**空转**），注释声称"真实截断算术由 T3 用仓内文件覆盖"，
      而 T3 只检查 `> 0`（59 也 > 0）⇒ **唯一能拦住该缺陷的检查被自己删掉了**。
EXACT_EVIDENCE = results.md §2 D7；修复记录含"T2 恢复为合成输入上的算术自检（原本空转）"
CURRENT_PREVENTION = 修复后 T2 恢复为真检查；且新增 T2e 专门断言"两个量不得混同"
CURRENT_PROMPT_RULE = R-V12-093 / R-V12-091
MECHANICAL_REPLACEMENT_CANDIDATE = 对每个 selftest 项：**它是否是空的**（是否含可失败断言）
TARGET_LAYER = MECHANICAL_GATE
DETERMINISTIC_PREDICATE = PARTIAL（"是否含断言"可静态查；"断言是否有意义"不可）
POSITIVE_CONTROL_AVAILABLE = YES（把一个 selftest 改成恒真 → 探针应发现）
FAIL_CLOSED_BEHAVIOR = 空的 selftest 项不得计入覆盖
RESIDUAL_RISK = 中-高。**这是 F-009 / F-010 的第三次出现**（同一失败类在本轮出现三次：
      空断言、空门、空自检）。三者是同一根问题的三个高度。
EVIDENCE_LEVEL = E3_LOCAL_REPRODUCIBLE
### F-019 — Recording / transcription error（记录转录错误）★
```text
REAL_INCIDENT = **是**。H1 `RUN_K7`（t01）的行数三元组被写成 t02 的数字（145/76/221
      vs 原始记录的 150/75/225）。**且盲评者把这个错误当成「载体指纹」这一实验发现**。
EXACT_EVIDENCE = results.md §2 D8；靠保留原始记录 `RUN_A` 才发现；
      `AGENTS.md@c08f6f8 = 150 行`、`RULES.md@c08f6f8 = 75 行`（git 复算）
CURRENT_PREVENTION = 修复后：更正 + `[v2-CORRECTION]` 留痕 + 原始记录保留为对照来源
CURRENT_PROMPT_RULE = R-V12-092
MECHANICAL_REPLACEMENT_CANDIDATE = 派生记录必须能从原始记录**逐字段复算**
      （而不是人工重写）；或至少：派生记录的每个数字都要有来源指针
TARGET_LAYER = MECHANICAL_GATE（成本低：断言派生记录的数字集合 ⊆ 原始记录的数字集合）
DETERMINISTIC_PREDICATE = PARTIAL
POSITIVE_CONTROL_AVAILABLE = YES
FAIL_CLOSED_BEHAVIOR = 无法溯源的数字不得进入记录
RESIDUAL_RISK = **中-高且被低估**：转录错误不会失败任何门，却会**污染结论**
      （它在本轮真的伪装成了一个「实验发现」）。
EVIDENCE_LEVEL = E3_LOCAL_REPRODUCIBLE
### F-020 — Runtime-specific fact promoted into generic governance（runtime 事实被升格）
```text
REAL_INCIDENT = 否（本仓有 R7 防它，且无违反记录）
EXACT_EVIDENCE = 反证：`validate_governance` 的 `no-unrelated-platform-requirements` 检查存在且通过；
      H1 的 8000 字符上限被**显式标为 profile 事实而非跨版本常数**（AGENTS §10 尾行）
CURRENT_PREVENTION = R7 + `no-unrelated-platform-requirements` + profile/常数区分纪律
CURRENT_PROMPT_RULE = R-V12-079 / R-V12-067 / R-V12-066
MECHANICAL_REPLACEMENT_CANDIDATE = 已有平台标记检查；可扩展为"机器事实白名单"
      （哪些事实允许出现在一般产物）
TARGET_LAYER = MECHANICAL_GATE（部分已有）
DETERMINISTIC_PREDICATE = PARTIAL
POSITIVE_CONTROL_AVAILABLE = YES
FAIL_CLOSED_BEHAVIOR = 已有（机器事实门）
RESIDUAL_RISK = 低
EVIDENCE_LEVEL = E2_LOCAL_SINGLE  # 机制存在；无 incident
```

### F-021 — Cross-tree number conflation（跨树数字被当矛盾/被互替）★
```text
REAL_INCIDENT = **是**（被评审当场指出）。H1 材料同时出现"32 项预存在失败未出现"（replay 树，
      553 tests）与"602 tests / 32 failures"（实验材料树）——两个都为真，但**未标注树**，
      读起来像自相矛盾。
EXACT_EVIDENCE = PR #47 review 1 的 P3；修复后 results.md 显式点明两棵树
      （"553 vs 602 正说明它们是不同的树，不能读作矛盾也不能互相替代"）
CURRENT_PREVENTION = 修复后：报告必须点明数字所属的树
CURRENT_PROMPT_RULE = R-V12-094（本轮新登记）
MECHANICAL_REPLACEMENT_CANDIDATE = 报告中的数字应携带**上下文标签**（树/SHA/命令）
TARGET_LAYER = HOT（认知类）+ MECHANICAL_GATE（若数字来自结构化产物则标签可强制）
DETERMINISTIC_PREDICATE = PARTIAL
POSITIVE_CONTROL_AVAILABLE = PARTIAL
FAIL_CLOSED_BEHAVIOR = N/A（这是可读性/诚实性问题，不是可 fail 的门）
RESIDUAL_RISK = 中。它会**制造假矛盾**，消耗评审预算去消解一个不存在的不一致。
EVIDENCE_LEVEL = E2_LOCAL_SINGLE
### F-022 — Retrospective contamination（回顾性观测被当作前瞻性证据）
```text
REAL_INCIDENT = **是**。H3-B0：7 条 observation 全部为 retrospective
      （ticket 先 merged、detector 后运行）⇒ `H3_B0_RESULT = NO_UNIQUE_VALUE_OBSERVED`；
      污染声明 = `RETROSPECTIVE_CONTAMINATION = STRUCTURALLY_IMPOSSIBLE_BY_DESIGN`。
EXACT_EVIDENCE = PR #42 记录 + 本轮 N6.2 的外部佐证（外部 harness 也把
      "运行前冻结 / 运行后不得改动"作为协议要件）
CURRENT_PREVENTION = H3-B1 的**资格分层**：`ticket_start_at > epoch`（取最早可审计激活记录）
      + `normal_evidence_frozen_at < shadow_first_run_at`
CURRENT_PROMPT_RULE = R-V12-090（预注册）+ H3 协议冻结
MECHANICAL_REPLACEMENT_CANDIDATE = 已有部分机械化（checker 校验自述字段的内部一致性）
      **但**：checker 只校验内部一致性、**不校验真实性**（H3-B1 评审结论）
TARGET_LAYER = HARNESS_STATE_MACHINE
DETERMINISTIC_PREDICATE = PARTIAL（时间戳可比对；"证据是否真的运行前冻结"只能是程序性保证）
POSITIVE_CONTROL_AVAILABLE = YES（构造一个 ticket_start < epoch 的条目 → 必须 NOT_ELIGIBLE）
FAIL_CLOSED_BEHAVIOR = 资格不符即排除，不得计入 cohort
RESIDUAL_RISK = 中。**程序性保证 ≠ 真实性保证**，这条必须一直写在协议里。
EVIDENCE_LEVEL = E2_LOCAL_SINGLE
---

## 2. 跨条目的模式（本轮最重要的观察）

把 22 条按**根因**归并，得到三个反复出现的模式 —— 它们比单条失败更有指导价值：

```text
PATTERN-A 「空的东西看起来像满的」 = F-009 + F-010 + F-018 + F-017
  同一个根问题在本轮出现**四次**，横跨三个高度：
    断言层：恒真的守卫（H1 P1）
    门层：谓词被掏空仍报 PASS（#45）
    自检层：selftest 被写成 `del`（H1 D7）
    数据层：仪器算错口径但产出"可复算"的错数字（H1 D7）
  ⇒ 归纳：**"能失败"必须被证明，而不是被假定。**
  ⇒ 目标机制：正控 / 语义突变探针（MECHANICAL_GATE）
  ⇒ 已立项：#45（门层）。断言层与自检层尚未立项 —— 见 §3。

PATTERN-B 「未验证的东西进入了可信面」= F-003 + F-019 + F-021 + F-022 + F-012
  转录错误伪装成实验发现（F-019）；跨树数字伪装成矛盾（F-021）；
  回顾性观测伪装成前瞻证据（F-022）；记忆被写但无人执行（F-012）。
  ⇒ 归纳：**"进入可信面"缺少准入条件。**
  ⇒ 目标机制：Verified State（HARNESS_STATE_MACHINE，M-02/M-12）
  ⇒ 这正是 H5 的标的。

PATTERN-C 「声明与目的地/对象脱节」= F-002 + F-008 + F-011 + F-015
  执行目标未绑定（F-002）；被引用的检查不存在（F-008）；路由目标不存在（F-011）；
  产物路径易失（F-015）。
  ⇒ 归纳：**声明了目标，但没有断言目标存在/可达/持久。**
  ⇒ 目标机制：存在性/可达性断言（MECHANICAL_GATE，成本极低）
  ⇒ 已立项：#46（路由层）。执行目标与产物路径尚未立项。
```

**三个模式都指向同一结论**：缺口不在"缺规则"，而在"缺**可失败性**与**准入条件**"。
这与 N6.1 的分布事实一致（最长的一条 R2 恰恰是机械化最彻底的）。

---

## 3. 由本文件产生的新发现（**未**自动立项）

按 PART 21 的立项规则（可独立复现 + 当前 main 相关 + 真实工程影响 + 不重复）逐条判定：

```text
CANDIDATE-1  P1 层：恒真的守卫断言没有系统性正控要求
  可复现 = YES（H1 P1 已活体证伪）
  current-main relevant = YES（任何仓内守卫都可能如此）
  真实影响 = YES（这是我们最贵的失败：评审才发现的空守卫）
  是否重复 = **与 #45 同族但不同层**（#45 是门/谓词层；这是断言层）
  判定 = **不新开 issue**，改为记入 #45 的 N6.4 映射（同一目标机制：正控/突变探针）。
  理由（PART 21 "不要无限增长 issue 数"）：两者共享同一个修复方向——
        "为每个守卫/门/自检要求一个正控"。分开立项会制造两份几乎相同的需求。

CANDIDATE-2  P1 层：selftest 可以为空且无人发现
  判定 = 同上，并入 CANDIDATE-1（同一目标机制）。

CANDIDATE-3  P2 层：实验/run 产物落在易失目录（/tmp）无任何断言
  可复现 = YES（8 个 prunable worktree 是现存证据）
  真实影响 = YES（H1 的一个完整证据面被永久削弱）
  是否重复 = NO
  判定 = **OBSERVATION / HYPOTHESIS**（不新开 issue）。
  理由：它的修复极小（一个路径断言），且它**只影响实验线**（experiments/v1.2/**），
        不进 canonical；把它作为 N6.4 的机械候选登记 + H2/H5 的协议前置条件即可。
        开 issue 会把一个"协议纪律"升级成"仓库缺陷"，与它被 experiments/ 隔离的定位不符。

CANDIDATE-4  P2 层：派生记录与原始记录之间无机械可溯性
  判定 = **OBSERVATION**（同上理由：属实验材料纪律，登记进 N6.4）。
  
（无 P0 候选。）
```

```text
NEW_ISSUES_FROM_THIS_FILE = 0
理由摘要 = 所有新发现要么与 #45 共享同一目标机制（合并而非拆分），
          要么属于实验线纪律（登记进 N6.4，不占用 issue 预算）。
```

---

## 4. 本文件不做的事

```text
不做：决定每条失败由哪个目标层接管（= N6.4）
不做：实现任何门
不做：给 HYPOTHESIS_NO_LOCAL 条目承诺工期或 gate（R8：无真实失效不立 gate）
```
