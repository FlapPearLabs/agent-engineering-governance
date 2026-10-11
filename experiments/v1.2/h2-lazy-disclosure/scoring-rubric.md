# H2 scoring rubric（P5 预注册；非 canonical）

> **本文件在第一条 valid run 之前冻结。** 评分维度、"高价值"判定边界、missed-guidance
> 归属规则、结论计算规则全部写死在此；**看到结果后不得重定义任何一项**。
> 与 `protocol.md` 冲突时以本文件的**边界定义**为准（protocol 管流程，本文件管判定）。

## 0. 一条纪律

```text
NO POST-HOC RECLASSIFICATION（禁止事后重解释）
  · 不允许在结果出来后重新定义"什么算高价值"；
  · 不允许把"变体臂的 miss 不重要"作为免罪理由（该判断只允许按 §2 的定义机械执行）；
  · 任何确实需要两个版本并存的判断分歧 → 两个版本都记录，取**保守**（对 DISCLOSURE_SAFE 不利）者；
  · 所有判定必须能指回 run 的落盘 artifact（file/section 级引用）。
```

## 1. 指标定义（M1–M7 + 体量）

```text
M1 ROUTE_EXISTENCE_RATE   = 声明路由中、目标在声明 base 上存在的比例（机械）
                            ← 由 N8 validator 在 6 个不同 base 上实测（H2 base = n02 base = 9494de8；见 routes-h2.json）
M2 ROUTE_LOADABLE_RATE    = agent 实际尝试加载的路由中，成功加载的比例（遥测）
M3 WARM_FILES_LOADED      = **完整读取**（非 grep 命中、非部分读取）的 references/ 与
                            skills/ 文件数；口径 = 只有完整读取计入（协议 §1.3 定义）
M4 MISSED_GUIDANCE        = 变体臂漏掉的、对照臂捕获的高价值 finding（定义见 §2–§3）
M5 FINAL_CORRECTNESS      = 逐 run 判定（机械验收 + 独立评审），定义见 §4
M6 SKILL_RETRIEVAL_HIT    = 任务本应触发的 Skill 是否被正确处置（定义见 §5）
M7 UNNECESSARY_LOAD       = 加载了与任务无关的 WARM 内容（人工判定，保守；见 §6）
HOT_JS_CHARS              = 两臂的 HOT 声明面（js_chars；单位与 H1 一致）
VISIBLE_DELIVERED_CHARS   = 两臂合同下**实际投递**的字符（本实验两臂均按合同全文投递）
TOKEN_USAGE / WALL_CLOCK / APPROX_TOKENS = NOT_OBSERVABLE（禁止由字符数估算）

遥测分别记三档（不得混同）：DISCOVERED（grep/find 命中）/ PARTIAL（部分读取）/ FULLY_LOADED（完整读取）。
```

## 2. HIGH_VALUE_FINDING 的预注册定义

一条 finding 计为 high-value，当且仅当它属于以下类别之一（P3 措辞/风格问题**不自动**计入）：

```text
HV1  P0/P1 级 correctness 或 safety 缺陷（含：会静默改变产物语义者）
HV2  机械验收失败类（门假绿、断言空转、状态坍缩）
HV3  wrong repo / wrong base / wrong worktree 类（执行目标错位）
HV4  scope violation（越出任务合同允许的变更面）
HV5  false closure（完成声明无证据支撑 / 证据与声明不符）
HV6  未处置的 substantive review finding（把已发现的高价值问题留为未决）
HV7  缺失被要求的 artifact 组件
HV8  route/skill retrieval failure 且该失败改变了任务结果
```

证据形态纪律：一条 finding 要进入统计，必须在其 run 的 artifact 中有**可指回的最小证据**
（命令、构造物、文件+节号）；纯语气/格式/风格观察不计。

## 3. MISSED_GUIDANCE 的预注册定义（三合取，全部满足才成立）

```text
MISSED_GUIDANCE(任务 T) 成立  ⟺ 以下三项同时为真：
  ① 存在一条 high-value finding F（§2 类别之一）：
        CONTROL 臂在 T 的某次**有效** run 中捕获（finding 进入该 run 报告且审计确认真实）；
     AND VARIANT 臂在 T **至少存在 1 个有效 run**，且其**全部有效 run** 均未捕获；
        （若 T 的全部 variant run 为 INVALID/BLOCKED → 本项不成立；此时按 §9 走
         INSUFFICIENT_EVIDENCE —— 不得把"没有观察"读成"变体漏了"。）
  ② F 的知识位于 **MOVED_TO_WARM 集**：
        = 存在于 CONTROL 投递面（AGENTS.md 全文）或任一 WARM owner，
        但**不在** H2 载体（carriers/H2_LEAN_BOOTSTRAP.md）中。
        判定按 finding 的主题逐条映射到知识位置（见 §7 映射表方法），
        F 与知识位置的关联须写出理由。
  ③ F 不是"两臂共同盲区"：CONTROL 确实捕获且 VARIANT 确实未捕获（①已含），
        且该 finding 不属于双方均不可达的知识（当时不可观测/环境阻塞）。

反例（不算 MISSED_GUIDANCE）：
  · 变体与对照输出不同、但没有任何一方漏掉 high-value finding；
  · 变体犯了错误，但所需知识不在 MOVED_TO_WARM 集（例如双方都从未达到的语义）；
  · 变体漏掉的是 P3 措辞风格类；
  · 环境阻塞（exit 137/139 等）导致的未做 → 记 BLOCKED，不记 miss（但要在 §8 计数）。
```

## 4. FINAL_CORRECTNESS 的预注册定义（逐 run）

```text
FINAL_CORRECTNESS(run) ∈ {PASS, FAIL, PARTIAL, BLOCKED}
  = task-registry.json 中该任务的 mechanical 验收命令结果
    + 独立 auditor 对 artifact 的评审结论（两者都记录，冲突时取保守）
判定纪律：
  · worker 自报 done ≠ PASS（必须过机械验收 + 独立评审）；
  · mechanical 命令在 run worktree 上由编排者执行并落盘输出；
  · auditor 只看 artifacts / diff / 测试输出 / 报告，不看 worker 过程性叙述中的自我辩护；
  · PARTIAL = 主体达成但存在 §2 未覆盖的次要缺口（须逐条列出）。
INVALID_COMPLETION(run) = worker 声明完成但机械验收或评审不成立（false closure 类，HV5）。
```

## 5. SKILL_RETRIEVAL 处置集合（M6）

```text
每个 (run, task) 的期望 Skill 见 task-registry.json（expected_skill）。
SKILL_RETRIEVAL_OUTCOME ∈ {
  LOADED,                      # 期望 Skill 可用且被实际加载（含读全文证据）
  UNAVAILABLE_FALLBACK_OK,     # 期望 Skill 不可用 → 记 SKILL_UNAVAILABLE + 按 fallback 执行并报告
  NOT_REQUIRED,                # 任务无强制 Skill（如 LOW 票）
  WRONG_SKILL,                 # 加载了与任务不匹配的 Skill（按路由表应能避免）
  NOT_ATTEMPTED,               # 应当触发但未触发任何 Skill 处置（miss）
  UNVERIFIED                   # 声称加载但无证据
}
SKILL_RETRIEVAL_HIT(run) = outcome ∈ {LOADED, UNAVAILABLE_FALLBACK_OK, NOT_REQUIRED}。
聚合 SKILL_RETRIEVAL_HIT = 达到 HIT 的 run 数 / 适用 run 数（NOT_REQUIRED 计入分母）。
纪律：不得为凑 hit 率强制加载无关 Skill（加载无关 Skill 同时记入 M7）。
```

## 6. UNNECESSARY_LOAD 判定（M7）

```text
UNNECESSARY_LOAD(run) = run 加载的 WARM 内容中，有**明确与任务无关**且按路由本不应命中的项。
判定保守：只有"路由行明显不命中 + 内容确实未用于任务"同时成立才计数；模糊不计数。
（例：LOW 文档任务加载了状态机/持久化细节且报告未使用 → 计 1。）
```

## 7. 知识位置映射（用于 §3 的 ② 项）

对每个任务的 ground truth（must_catch 列表）与可能的捕获点，预先生成映射：

```text
知识位置类别：
  (i)   H2 载体自身（地图/不变量/禁令）        → 变体也有
  (ii)  WARM owner（routes-h2.json 的目标）     → 变体应经路由到达；对照也能读
  (iii) AGENTS §3/§4/§5 与 §0 框架的细节文本    → 载体不含；CONTROL 全文投递有
  (iv)  AGENTS §6–§10 等"控制面全读"文本        → 载体不含；CONTROL 全文投递有
  (v)   双方都未达到的语义                      → 双方同盲
MOVED_TO_WARM_SET（§3 ② 的判定集） = (ii) ∪ (iii) ∪ (iv)，且该知识在上述位置确实存在。
说明：(ii) **计入** —— "按任务相关性加载正确的 WARM"本身是本文变体的被测机制；
对照臂捕获、而变体经其路由面仍漏掉可达 WARM 中的知识 = 披露机制失败，正属于本实验
要测量的代价（bot review「Include WARM-owner findings in missed-guidance scoring」）。
```

## 8. 结果环境变量（不计入评分，但必须记录）

```text
ENV_BLOCKED_RUNS      = 因环境故障（exit 137/139、网络、通道死亡）未能完成或未能验收的 run 数
INVALID_RUNS          = 按 protocol §19 注册的作废 run 数
REPLICATION_STATUS    = 每 shape 的实际 n/arm（目标 2；不足时逐 shape 列出实际值）
```

## 9. H2_RESULT 计算规则（预注册；与 mandate PART 24 对齐）

```text
DISCLOSURE_SAFE 成立需要**同时**满足：
  S1  HOT 体量实质下降：OBSERVED 降幅 ≥ 30%（HOT_JS_CHARS，H2 base 口径）
      且变体载体完整投递（不截断）；
  S2  无 additional high-value miss：按 §3 判定，全部任务上 MISSED_GUIDANCE = 0；
  S3  未增加 invalid completion：VARIANT 的 INVALID_COMPLETION 数 ≤ CONTROL；
  S4  最终正确性不更差：逐任务把两臂的 FINAL_CORRECTNESS 多重集按序
      （PASS < PARTIAL < FAIL < BLOCKED）排序后**逐位比较**，VARIANT 不得更差。
      （例：control {PASS, FAIL} vs variant {FAIL, FAIL} ⇒ S4 不成立 —— 比较的是结果
      计数分布，不是"是否出现新失败类别"。）
  S5  WARM/Skill 机制实际工作：**来自 variant 臂有效 run 的** M2/M3 有非零真实加载证据 +
      **VARIANT 臂自身**的 M6 ≥ 2/3 适用 run 为 HIT（S5 检验的是变体的懒加载机制；对照臂的
      读取不能替代变体的路由行为，两臂聚合的阈值同样会被掩盖 —— bot review R6-11）。

DISCLOSURE_HAS_COST 成立需要：至少 1 条 §3 定义的 MISSED_GUIDANCE。
INSUFFICIENT_EVIDENCE：valid run 覆盖不足 —— 任一 shape 实际 n/arm < 2，**或任一任务的
  任一臂无有效 run（无法形成配对比较；不再限于 judgment-heavy 任务 —— bot review R5-5）**；
  或环境主导（§8 的 ENV_BLOCKED_RUNS ≥ 4 等）；或归属歧义（同一 finding 的知识位置无法
  稳定归入 §7 任一类别）时成立。

优先序（每一条 S1–S5 失败都有唯一归宿；bot review「Assign an outcome whenever a safety
condition fails」）：
  ① MISSED_GUIDANCE ≥ 1 ⇒ DISCLOSURE_HAS_COST（attribution tag = MISSED_GUIDANCE_MOVED_TEXT）
  ② 无 ①、但 VARIANT 在 S3/S4 上比 CONTROL 更差（invalid completion 更多，或 correctness
     分布更差）⇒ DISCLOSURE_HAS_COST（attribution tag ∈ {TREATMENT_ONLY_CORRECTNESS,
     TREATMENT_ONLY_INVALID_COMPLETION}；与 ① 分开记录）
  ③ 无 ①②、但 S1 不满足（降幅不足 / 变体被截断）⇒ INSUFFICIENT_EVIDENCE（设计前提未兑现）
  ④ 无 ①②③、但 S5 不满足（变体自身机制未 demonstrably 工作）⇒ INSUFFICIENT_EVIDENCE
  ⑤ 全部满足 ⇒ DISCLOSURE_SAFE
（另：§8 的环境性不充分触发 ⇒ INSUFFICIENT_EVIDENCE。禁止出现"无合法结果"的状态。）
```

## 10. 盲评流程（BLIND_FINDINGS_EVALUATION，尽力而为并如实报告）

```text
输入 = 每任务全部 run 的「findings 节」（报告 §D/§E）机械抽取，
       去掉 run_id/arm/载体名（替换为 PRIMARY_BOOTSTRAP 槽位），候选标签按确定性打乱。
评估者 = fresh subagent（不接触 run-registry / 本 rubric 之外的映射）。
输出 = 每候选捕获的 findings 清单 + 对预注册 ground truth 的逐项覆盖矩阵。
结果状态 ∈ {ATTEMPTED_CLEAN, ATTEMPTED_WITH_LEAKAGE, NOT_ATTEMPTED}；
若评估输出表明其能从文本识别臂归属 → 记 LEAKAGE 并降级该次评估的权重（但仍保留输出）。
禁止：把 VOID 当作可预见事故重演 —— 若无法做干净，直接记 NOT_ATTEMPTED。
```

## 11. 对账（PART 26 / PART 27，结果阶段执行）

```text
B 组 16 条（003/004/005/006/007/008/010/021/028/035/039/046/047/055/063/085）
  + R-V12-049（单列）逐条输出：RULE_ID / H2_EVIDENCE / STATUS ∈
  {SUPPORTED_TO_MOVE, NOT_SUPPORTED, STILL_UNKNOWN}。
HOT 投影对账：N6_PROJECTION（口径 2 = HOT ≈ 7,900）!= H2_OBSERVATION（实测值）——
  两者不得互相引用为证据。
```
