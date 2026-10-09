# H1 结果（非 canonical）

> 结果语义仅三取值：`INSUFFICIENT_EVIDENCE` / `LEAN_NOT_BETTER` / `LEAN_PROMISING`。
> **本轮不含 `PROMOTE`。** 不可观测量记`NOT_OBSERVABLE`，无估算。
> 本轮为**恢复执行 + 完整一轮**：t01 终态已独立复验，t02/t03/t04 已补跑，盲评已派。

## 0. 结论

```text
H1_RESULT = INSUFFICIENT_EVIDENCE
BLIND_EVALUATION = VOID（匿名化存在完美判别器，见 §7）
VARIANT_CHANGED_AFTER_FREEZE = NO
```

判定依据有三条，**任何一条单独即足以排除 `LEAN_PROMISING`**：

```text
1. 存在 additional high-value miss
   t03 的 VARIANT 臂漏掉了 3 条 CONTROL 臂捕获的治理级发现，其中一条是
   校验器合同自相矛盾（remote 非空 ⇒ last_verified_remote_sha 必须 40 位
   合法 SHA ⇒ 「有remote + 延迟同步 + 空 SHA」不可表达）。
2. blind evaluation 作废 ⇒ 配对级比较无法在盲态下取得。
   盲评者独立发现 2 个完美判别器（见 §7）。
3. 每臂每任务 n=1，且环境在至少 3 对中主导了结果。
   盲评者独立指出：t04 两臂最大的质量差（一个跑了两道门、另一个没跑）
   可由一次 shell 死亡完全解释，与臂无关。
```

按 PART 21：`LEAN_NOT_BETTER` 需要「有证据显示 lean 更差」——
本轮**没有**这个证据（唯一那条 additional miss 在 n=1 下不可归因，见 §6）。
故如实记 `INSUFFICIENT_EVIDENCE`。

## 1. 本轮实际发生的环境故障（不归因给任何臂）

```text
t01 两臂收尾阶段   : SIGTERM / exit 137（上一轮遗留）
本轮 t02 VARIANT 首次: worker 的 shell 在侦察中途死亡（exit 137）
本轮 t03 CONTROL / t04 CONTROL: shell 多次死亡，含裸 echo
本轮 t04 VARIANT   : 每条命令约 3 分钟（同一故障的轻症）
本轮编排者自身     : 两次全通道死亡（exit 137 / 139），期间改用
                     Read/Glob/Write 独立路径继续取证
```

**关键处置**：环境故障一律记为环境，不记为任一臂的质量缺陷。
t04 两臂 `VALID_COMPLETION` 分叉（NO / YES）的直接原因就是 shell 死亡时机，
盲评者独立复核后判定该分叉**不可归因于臂**。

## 2. 本轮修复的自身缺陷（D1–D9；全部先取证再改）

### D1 匿名化 v2 只归一化了名字，没归一化遥测

见 D2 的判别器 1。载体文件名被替换成槽位，但 `H1_RECEIPT` 字段的**存在性**本身
就是臂标志 —— `ANONYMIZE_THE_NAME != ANONYMIZE_THE_TELEMETRY`。

### D2 匿名化泄臂（盲评判别器的根源）

上一轮盲评者已上报 `HOT_FILES_READ` 字段本身泄臂。本轮做了 v2 归一化
（载体→ `PRIMARY_BOOTSTRAP`，路由表 → `THE_ROUTING_TABLE`），
**但只归一化了名字，没归一化遥测本身**。本轮盲评者进一步发现两个更深的判别器：

```text
判别器 1：H1_RECEIPT 字段的有无
  出现于 4 条记录，缺席于 4 条 —— 4/4 完美切分。
  而收据内容本身就是被操纵的自变量（风险档位 / WARM 载入数 /远端处置）。
  ⇒ 任何知道哪一臂装了路由表的人可把 receipt-present 全部映射到该臂。
  **本项独立且充分，未受下述 D8 影响。**

判别器 2：PRIMARY_BOOTSTRAP_LINES / MANDATORY_READ_LINES / HOT_LINES_TOTAL
  RUN_Q2 与 RUN_M4 均为 157 / 75 / 232（两者同为变体臂，读同一份 157 行载体）
  ⇒ 该三元组在**跨任务**上仍指向变体臂；载体行数是臂的标识符。
```

**但盲评者当时援引的第二组证据（`RUN_K7` 与 `RUN_B9` 均为 `145 / 76 / 221`）是错的**：
那不是载体指纹，而是**编排者自己的转录错误**（见 D8）。更正后 `RUN_K7` = `150 / 75 / 225`，
与 `RUN_B9` 不再相同。**必须记录这一点**，否则会把一个记录缺陷当成实验发现。

判别器 1 不受影响，`BLIND_EVALUATION = VOID` 的结论不变。

**教训**：`ANONYMIZE_THE_NAME != ANONYMIZE_THE_TELEMETRY`。
下一轮若再做盲评，必须把两臂的报告模板统一到**同一生成路径**，
并且归一化「结构化遥测字段的存在性」，而不只是字段内容。

### D3 / D4 已关闭：t01 两臂终态由编排者独立复跑

```text
CONTROL : 14 tests OK / 553 全量 OK / 34/34 治理门 / VIOLATIONS=0 / 无残留
VARIANT : 14 tests OK / 553 全量 OK / 34/34 治理门 / VIOLATIONS=0 / 无残留
两臂 HEAD 均 = c08f6f8b…（=预期 replay base，detached）
```

**上一轮记为 `VALID_COMPLETION = NO` 的原因是环境阻塞，不是臂缺陷。**
沙箱本轮恢复了安全读取原语，故此前记录的 32 项预存在失败**未出现** ——
这正是必须现场复跑、不得沿用旧文字报告的理由。

### D5 已关闭：残留 stash 清理（含上一轮记录的偏差）

```text
上一轮记录：残留 stash 在 t01__VARIANT，SHA = e6448c26
本轮实测：e6448c26 在**两臂**都可见 —— 因为 stash 是 repo 共享的 refs/stash，
         同一对象在所有 worktree 可见。上一轮「只有 VARIANT 残留」不完整。
身份取证：两臂均为同一条 stash（base c08f6f8、blob db44fdd）
安全证明：VARIANT 侧 stash blob == 工作树 blob（冗余快照）
         CONTROL 侧工作树 blob 0dcf4ef 是 stash 的更新版本（130+/23- vs 117+/15-）
处置    : drop stash@{0}（不接受的裸 SHA，须用引用）
落盘复核：两臂工作树 blob 未变，改动完好
```

### D7 计量仪器缺陷（本轮新发现，重要）

`hot_inventory.py` 的 `dropped_js_chars` 被实现为「截断行自身的溢出量」：

```text
原实现 = max(0, acc - limit)        → AGENTS.md 上 = 59
正确值 = 总量 - 可见量              → AGENTS.md 上 = 5,916
```

即把「丢弃了整个尾部」误报成59 字符，**低估约 100 倍**。
更严重的是：`selftest` 的 T2 项原本写成 `del g, exact`（**空转**），
其注释声称「真实截断算术由 T3 用仓内文件覆盖」——而 T3 只检查 `> 0`，
59 也`> 0`。**唯一能拦住它的检查被自己删掉了。**

修复：
```text
1. dropped_js_chars 改为 总量 - 可见量（并加total_js_chars 字段作为口径锚点）
2. T2 恢复为合成输入上的算术自检（原本空转）
3. 新增 T3c：dropped == 该文件 total - visible（口径锚定到文件自身，非臂合计）
4. 新增 T2e：多行输入下丢弃尾部必须 > 截断行溢出量（二者不得混同）
```

**修复过程中我自己写错了4 处期望值**（单行恰好等于 limit 的语义、拿臂合计
当分母、用 limit 近似溢出量），逐条改正的是**测试**，不是仪器。
记录在此是因为「改测试追绿」与「修正错误的测试期望」必须可区分。

**结论：README / results 原先声称的 5,916 是对的，仪器是错的。**
仪器 SHA256：`096142b7…`（修前）→ `400458cb…`（修后）。

### D8 run 记录转录错误（本轮发现，编排者引入）

第二轮把 t01 两臂重新记录为 `RUN_K7` / `RUN_Q2`（opaque ID）时，
`RUN_K7` 的行数三元组被误写成 **`145 / 76 / 221`** —— 那是同批 **t02** 记录的数字。
原始记录 `RUN_A` 写的是 `AGENTS.md:150 + RULES.md:75 = 225`。

```text
RUN_K7 原写 = 145 / 76 / 221   ← 错误（t02 的数字）
RUN_K7 更正 = 150 / 75 / 225   ← 与原始记录 RUN_A 一致
旁证 = AGENTS.md@c08f6f8 = 150 行（git show | wc -l）、RULES.md@c08f6f8 = 75 行
```

**为什么这条必须记录**：盲评者曾把「`RUN_K7` 与 `RUN_B9` 三元组逐字相同」当作
**载体指纹**（一个关于实验对象的结论）。更正后二者不同 ⇒ 那条证据消失。
若不记录，仓库里会留下一个**由记录缺陷伪装成的实验发现**。
（判别器 1 独立成立，故 `BLIND_EVALUATION = VOID` 不变。）

发现方式：清理轮对 `RUN_A`（原始记录，未改写）逐字段复核。
这与「保留原始记录」的做法直接相关 —— 若只保留 v2 记录，此错将无法被发现。

### D9 replay worktree 的证据耐久性缺口（本轮发现，环境造成）

```text
8 个 replay worktree 位于 /tmp/h1-runs/，现已被系统清理。
`git worktree list` 中对应条目状态 = prunable。
```

后果：run 当时的 base 断言**无法在事后于该目录重新核验**；
run 实际产出的 diff **未持久化**，不能事后重放。

```text
REPLAY_WORKTREE_REVERIFIABLE_NOW = NO
```

可用替代证据：run 记录内自报 + 编排者投递前的机械断言（六个 worktree MATCH=YES）
+ 四个 base SHA 仍可在对象库解析（`git cat-file -t` = commit）
+ 记录内 `[fact-check]` 块。

**不把「当时断言过」记成「现在仍可复验」。** 已列入复现前置条件（§11）。

### 裁断结论强度已校正（PART 6）

```text
AUTO_INJECTION_TRUNCATION_CONFIRMED = YES
  依据 = 13,756 js chars 在第 109/151 行被裁剪，丢弃 5,916 js chars（可复算）

AUTO_INJECTION_DROPPED_SECTIONS =
  §6 REVIEW/REPAIR/CI（尾部）、§7 AUTO-ADVANCE 与 STOP（尾部）
  §7.1 STATE_RESTORE/STATE_FLUSH、§8 治理变更、§9 报告、§10 BOOTSTRAP

FULL_GOVERNANCE_LATER_LOADED = YES_IF_BOOTSTRAP_FOLLOWED
  已核验的证据链：
   1. canonical 自设字段 FULL_GOVERNANCE_REACHABILITY = YES_IF_BOOTSTRAP_FOLLOWED
      FULL_GOVERNANCE_AUTOMATIC_DELIVERY = NO
   2. BOOTSTRAP_CONTRACT §2.2 B3 = 「读存在者…必须继续读到其指向的全文」
      §2.2 尾注 = 「仓本地权威可加严本清单，不得削弱 B1–B5 的读取义务」
   3. 被截断掉的 AGENTS.md §10:148 **自身**规定了含「发现并读取仓内
      AGENTS/RULES 全文」的引导清单 ⇒ 被丢弃的尾部自己规定了补读义务

END_TO_END_GOVERNANCE_LOSS_PROVEN = NO
  理由 = 截断是 first-turn 自动注入通道的事实；补读是清单义务。
         义务存在 ≠ 已执行。本轮未测「清单是否被实际执行」。
```

**因此不得把截断表述为治理丢失。** 真实暴露面是「依赖 agent 遵守一条
被截断掉的规则」，而非「治理不可达」。这是本轮对结论强度的一次实质降级。

## 3. HOT 计量（用修好的仪器重算，与上一轮数字一致）

```text
HOT_CONTROL_JS_CHARS= 15,784（MEMORY_POINTER 2,028 + AGENTS.md 13,756）
HOT_CONTROL_VISIBLE_JS_CHARS  = 7,840 / 108 行（丢弃 5,916）
HOT_VARIANT_JS_CHARS          = 6,382（MEMORY_POINTER 2,028 + lean 4,354）
HOT_VARIANT_VISIBLE_JS_CHARS  = 4,354 / 157 行（0 丢弃，完整投递）
HOT_REDUCTION_PERCENT         = 59.6（js_chars 口径）
GUIDANCE_VISIBLE_REDUCTION    = 44.5%
VARIANT_FULLY_DELIVERED       = YES
TOKEN_USAGE                   = NOT_OBSERVABLE（metrics.md 已定；禁止由字符数估算）
```

上一轮报告的 15,784 / 7,840 / 6,382 / 4,354 / 59.6% / 44.5% **逐项复现**。
唯一变化是 `dropped_js_chars`：59（D7 修前）→ 5,916（修后，真值）。

口径纪律：`HOT_VARIANT_LINES`(192) > `HOT_CONTROL_LINES`(186)，
但字符数少 59.6%。**HOT 的成本单位是 context 体量，不是行数。**

## 4. 任务与运行（4 任务 × 2 臂 = 8 有效 run）

**run 身份的唯一注册表 = `runs/README.md`**（task / arm / base SHA / 记录文件的逐行映射，
含被取代记录与作废 run 的处置）。本节只给汇总，不另行定义。

```text
TASKS          = 4（t01 LOW / t02 MEDIUM / t03 HIGH / t04 HIGH）
有效 RUNS      = 8   → runs/README.md §1
作废 RUNS      = 2   → runs/README.md §3
  作废 1 = INVALID_001 / WRONG_EXECUTION_TARGET
           t01 首对：worker 停在 governance HEAD a7f9e7c 而非 replay base c08f6f8
           ⇒ 该 HEAD 上缺陷已被修复，任务成 no-op
  作废 2 = INVALID_002 / TREATMENT_NOT_ESTABLISHED
           t02 VARIANT 首跑：harness 未把 bootstrap 载体放入 worktree 根
           ⇒ 该臂回落到 AGENTS.md ⇒ **两臂 bootstrap 相同，自变量未建立**
两者归因均为 harness 缺陷，非 worker 质量缺陷；均永久排除，不并入任何 aggregate。

worker 启动前置断言（机械核验，非 worker 自述）：
  t02/t03/t04 六个 worktree 全部 MATCH = YES 且树干净
```

t02 VARIANT 首跑的失败模式值得单独记录：worker 严格按 `BOOTSTRAP_CONTRACT`
§1 的 fallback 链处理（载体不存在 → 回落到 `AGENTS.md`），**worker 是对的，
harness 是错的**。

`REPLAY_WORKTREE_REVERIFIABLE_NOW = NO`（见 §2 D9）—— 8 个 replay worktree 已被
系统清理，run 当时产出的 diff 未持久化。本节的 base 断言属**投递前**机械核验，
不得读作「现在仍可复验」。

## 5. 三层区分（PART 15）——逐臂

```text
                        EXECUTION_COMPLETED  VALID_COMPLETION  QUALITY
t01 CONTROL (RUN_K7)        YES                YES※             记录机制但未闭合空面路径
t01 VARIANT (RUN_Q2)        YES                YES※             重新枚举 + 非空断言，结构性闭合
t02 CONTROL (RUN_B9)        YES                YES              交付最小；自报门未接入 CI
t02 VARIANT (RUN_M4)        YES                YES              设计正当性更强；引入了未验证的 pin
t03 CONTROL (RUN_Z8)        YES                NO§捕获 3 条臂外治理发现 + 拒绝伪造 SHA
t03 VARIANT (RUN_T1)        YES                NO§              漏掉 Z8 的 3 条治理发现
t04 CONTROL (RUN_W6)        YES                NO§环境死后无全新绿跑；前瞻风险分析强
t04 VARIANT (RUN_P3)        YES                YES              机械验证最完整；捕获载体级悬空路由

※ = worker 自报 NO（环境阻塞），编排者独立复跑后 = YES。差异归因见 §2D3/D4。
§ = 诚实报告 NO，理由经复核成立（扫描器在该 base 不存在 / 无独立评审 / 环境时机）。
```

```text
VALID_CONTROL_COMPLETIONS = 2/4（t01Y t02Y t03N t04N）
VALID_VARIANT_COMPLETIONS = 3/4（t01Y t02Y t03N t04Y）
```

**但这2:3 不可用于判定**：t04 的分叉由shell 死亡时机直接造成，
t03 两臂同为 NO。n=1 下无任何配对可归因。

## 6. 高价值发现与缺口（配对级，含混杂声明）

```text
CONFOUNDERS =
  1. 每臂每任务 n=1，无重复运行，方差不可估
  2. 环境故障在 t03/t04 两对中主导结果（shell 死亡时机直接决定 VALID_COMPLETION）
  3. 两臂交付物范围不同（t03：10 文件/+1389 vs 9 文件/+1474）
     ⇒ 覆盖面不同 ⇒ 发现集必然部分由「造了什么」决定，非纯能力
  4. 执行预算差异巨大（t04：~92 分钟/14 跑 vs ~57 分钟/9 跑）
  5. WARM_FILES_LOADED 口径未定义且八个数互不对账（0/1/8/2/3/3/1/1）
     ⇒ 渐进披露剂量无法作为协变量控制
  6. TEST_RUNS 三种计数约定（APPRX / 含失败调用 / distinct invocations）⇒ 不可比
  7. 编排者对配对做了跨臂评论与联合修正 ⇒「两臂独立收敛」不是独立证据
```

逐对高价值差异（解盲后）：

| 任务 | 对照臂独有发现 | 变体臂独有发现 |
|---|---|---|
| t01 | —（机制陈述但未证明可达性；空面路径未闭合） | 字母序可达性证明 + 非空断言闭合 |
| t02 | — | `select=["E"]` 会使门变红 → 失去信号价值；基线与独立历史记录逐项吻合 |
| t03 | **校验器 schema/代码自相矛盾**；代码图策略的仓内先例冲突（并自纠）；needle 裸片段误报风险| 自陈 hard scope 越界（诚实披露） |
| t04 | 授权 spec 写码前逐字提取；枚举 owner 绑定既有 reference；ECMA-262 语义前瞻风险 | **路由表悬空目标（载体级缺陷）**；两道别人漏掉的门；23 errors 从「环境」推进到「既有 fixture 潜在缺陷」 |

```text
HIGH_VALUE_MISSES_CONTROL = 见 t01 空面路径未闭合（1 条）
HIGH_VALUE_MISSES_VARIANT = 见 t03 漏掉 3 条治理级发现
```

**这构成 PART 17 意义上的 additional high-value miss，足以排除 `LEAN_PROMISING`。**
但 n=1 +上述 7 项混杂 ⇒ 也不足以支持 `LEAN_NOT_BETTER`。

## 7. 盲评：已派，但**结论作废**

```text
BLIND_EVALUATION = VOID
盲评者 = fresh subagent，未参与任一臂执行，输入仅 8 份匿名记录
盲评者自报 = ANONYMIZATION_DEFECT_FOUND = YES
判别器 = H1_RECEIPT 有无（4/4 完美切分）+ bootstrap 行数三元组（跨任务逐字节相同）
```

盲评者的per-run 判断（`VALIDITY` / `QUALITY` / `SELF_REPORT_HONEST`）
**仍可作非盲证据引用**，因为这三项不依赖解盲：

```text
8/8 记录 = VALID
8/8 记录 = SELF_REPORT_HONEST = YES
无绿灯造假；6 份报 NO 且理由经得起复核；2 份报 YES 且当场限定了 YES 的射程
盲评者配对结论（盲态）：t01 Q2强 / t02 TIE / t03 Z8 强 / t04 TIE
  ——但因判别器存在，**这些配对结论不可采信为臂效应**
```

**PART 10 未满足**：盲评协议有实质缺陷，须在下一轮修复后才可产出有效盲评。

## 8. 与实验成败无关、但独立成立的实质发现

盲评者建议独立立项，本轮认为成立 —— 它们不依赖臂比较即已由证据支撑。
**本轮已按 ISSUE POLICY 立项；修复不在本 PR 内进行。**

```text
F1_ISSUE = #45
  TITLE = V1.2 evidence: governance checks can remain green after a
          load-bearing static guard is removed
  STATUS = **存活于当前 main**（本轮已复现，非仅历史 base）
  复现 = select=[] 后注入真实 F841 → 门报 "All checks passed!"；
         validate_governance.py 仍 35/35；ci-executes-static-gate 仍 PASS；
         恢复后 ruff.toml SHA256 前后一致（5e1a8244…）
  抽象 = GATE_GREEN != GATE_STILL_ENFORCES_ITS_CLAIM

F2_ISSUE = #46
  TITLE = V1.2 evidence: progressive-disclosure routes need destination
          existence/loadability validation
  STATUS = 机制级发现（base 相对；本轮以 git ls-tree 独立取证）
  复现 = references/review-evidence.md 在 replay base e1da154 **不存在**
         （该 base 的 references/ 共 10 项），在 current main 存在
         （由 2ed08f6 引入 —— 即路由指向一个候选落地后才存在的目标）
  抽象 = ROUTE_DECLARED != DESTINATION_EXISTS != DESTINATION_LOADABLE

F3 = 校验器合同自相矛盾（t03 base；**main 上已解决，故不立项**）
  base af4df6a 的代码 = `deferred = (remote == "")`，
     即「空 SHA 合法」绑定在「仓无远端」上；
  而 schema 注释 = 「Empty string legal only while REMOTE_STATE_SYNC = DEFERRED」，
     绑定在「同步延迟」上。两个不同概念共用 deferred 一词 ⇒ 不一致成立。
  **当前 main 已解决**：schema 注释改为「空 = 尚无远端验证」，校验器放宽为
     `sha == "" or SHA40`。→ 属历史发现，不立 issue。

F4 = base 仓无 .gitignore（t03 base；**main 上已解决，故不立项**）
  该 base `.gitignore` ABSENT（git cat-file 确认），是历史候选提交 .pyc 的机制；
  current main 已有 `.gitignore`。→ 属历史发现，不立 issue。
```

**分类纪律**：只有「在当前 main 上仍可复现」的发现才立项。
F3/F4 描述的是历史 base 的性质，本轮逐一核验其在 main 上的现状后才决定不立项 ——
不把过期的历史缺陷当成待办。

关联：roadmap #44 与 #33/#34 属同一「empty PASS」家族，但机制不同（见 issue 正文的
NON-GOALS 段）。

## 9. 局限（LIMITATIONS）

```text
L1  每臂每任务 n=1，无重复运行，run-to-run 方差不可估 —— 7 项混杂见 §6。
L2  环境故障（shell exit 137 / 139）在至少 3 对中主导结果，
    使 VALID_COMPLETION 分叉不可归因于臂。
L3  BLIND_EVALUATION = VOID ⇒ 配对级比较在盲态下不可得（§7）。
L4  REPLAY_WORKTREE_REVERIFIABLE_NOW = NO ⇒ run 的 diff 不能事后重放（§2 D9）。
L5  WARM_FILES_LOADED 口径未定义且八个数互不对账（0/1/8/2/3/3/1/1），
    渐进披露剂量无法作为协变量控制。
L6  TEST_RUNS 存在多种计数约定（APPRX / 含失败调用 / distinct invocations），跨臂不可比。
L7  TOKEN_USAGE / TOOL_CALLS = NOT_OBSERVABLE：本 harness 无法可靠取得，未估算。
L8  本实验只在**一个仓**（本仓）+ 一个 runtime 上执行；不外推。
L9  run 记录由 worker 自报 + 编排者部分独立核验混合构成，两者在记录中已逐处标注。
```

## 10. 复现前置条件（REPLICATION PREREQUISITES，尚未实现）

第二轮复现前必须先满足以下条件。**本轮不实现它们**，只登记。

```text
R1  execution-target mechanical binding
    把 worktree 绝对路径 + EXPECTED_BASE_SHA 作为 worker 的**机械前置断言**，
    不靠 prompt 散文。本实验两次作废 run 都源于此（INVALID_001 / INVALID_002）。

R2  bootstrap carrier presence assertion
    载体的**投放**与断言一样必须是 harness 的机械步骤：
    未投放会让臂静默回落到默认载体，从而悄悄取消自变量（INVALID_002）。

R3  arm telemetry anonymization
    归一化必须覆盖**结构化遥测字段的存在性**，不只是字段内容与文件名。
    本轮判别器 1（H1_RECEIPT 有无，4/4 完美切分）就属于「名字改对了、遥测没改」。
    另需把两臂报告模板统一到**同一生成路径**，消除模板级差异。

R4  stable execution runtime
    需要可用的执行通道；本实验 3 轮均被 exit 137/139 打断。
    并把 run 产物写入**持久化**位置（本轮置于 /tmp，已被清理，见 D9）。

R5  pre-registered evaluation rubric
    盲评的评分维度、判定阈值、以及「高价值」的判定边界必须在跑之前冻结，
    而不是在看到结果后定义。
```

## 11. GitHub evidence closure

**历史事实（不得丢弃）**：

```text
PART 23 未满足（第一轮）
  = H1 材料当时只存在于本地 worktree，未 commit / 未 push / 未开 PR / 无 CI / 无 merge。
  原因 = 执行通道对包括裸 echo 在内的所有命令返回 exit 137，已尝试并取证，非「未尝试」。
```

**本轮执行闭环，状态为**：

```text
GITHUB_EVIDENCE_STATE = PENDING_PR_AT_ARTIFACT_COMMIT
```

该状态是**本文件被提交时**的事实：材料已本地冻结、本地总门已跑、准备
commit → push → PR。PR 号 / CI 结果 / merge SHA 属 merge 后事实，
由 PR 本体与 merge commit 记录 —— **本文件不写未发生的未来值**
（R3：UNKNOWN != PASS）。

关联发现（本轮已立项，修复不在本 PR 内）：

```text
F1_ISSUE = #45
F2_ISSUE = #46
```

## 12. 复现

```text
python3 experiments/v1.2/h1-hot-context/hot_inventory.py            # 计量表
python3 experiments/v1.2/h1-hot-context/hot_inventory.py --selftest  # 反例自检（已恢复 T2）
python3 experiments/v1.2/h1-hot-context/hot_inventory.py --json      # 机器可读
python3 -m unittest discover -s experiments/v1.2/tests -v           # 材料自检
```

冻结哈希（`PROMPT_TUNING = FROZEN` 后逐字节未变）：

```text
lean/CODEBUDDY.md     SHA256 = 86e24c088814dfe36203f4271bcf97ed3bd3e6ef733ca3bfa0058a1caccbb0fb
tasks.yaml            SHA256 = 25ba7d1f8177cac7e045e98ee8a475ca45fb1c6ea818e3c17b12ea5b9271d692
三处 VARIANT worktree 内的载体 = 与上述逐字节一致（编排者已核）
```

PART 19「然后停止」= 遵守。本轮不进入 H2 / H4。