# RUN_P3 — t04 / the other arm（anonymous）

> 匿名 run 记录。评估者先读本文件与 `RUN_W6`，判定后再解盲。
> **匿名化规约（v2）**：bootstrap 载体归一化为 `PRIMARY_BOOTSTRAP`；路由表称
> `THE_ROUTING_TABLE`；不出现 arm 名称、载体文件名或可识别 arm 的路径。

```text
RUN_ID = RUN_P3
TASK_ID = t04
MODE = <ANONYMOISED>
H1_RECEIPT = S1:read S2:MEDIUM S3:one WARM ref via THE_ROUTING_TABLE S4:NO_REMOTE
PRIMARY_BOOTSTRAP_LINES = 158
MANDATORY_READ_LINES = 76
HOT_LINES_TOTAL = 234
WARM_FILES_LOADED = 1 of2 named by row
SKILLS_LOADED = 0
TEST_RUNS = 9 distinct invocations
WALL_CLOCK = ~57 分钟（每条命令约 3 分钟，因环境故障）
SELF_REPORTED_VALID_COMPLETION = YES
```

## 报告的高价值 finding

1. **THE_ROUTING_TABLE 存在悬空目标** —— 路由表把评审任务指向
   `references/review-evidence.md`，而该文件**在 base 不存在**（已用文件枚举证明：
   10 个 reference 文件中无它）。**载体指向了一个不存在的 WARM 目标。**
   本臂通过自行撰写该文件闭合。
   **这正是 lean 载体的风险形态 —— 路由行会把一个 fresh agent 送到死路径。**
2. **模板 vs schema 过度断言（自伤）**：最初测试断言交付的占位模板能干净通过校验；
   它不能（某哈希字段要求 40 位）。改为只断言结构，不断言字面值。
3. **边界测试测的是散文不是代码（自伤）**：最初的「不做裁决」测试用 grep 匹配
   docstring，而那些 docstring 恰恰在**声明**该边界。改写为对代码的 AST 分析。
4. **负控空转（自伤）**：对列表用「包含」断言，会漏掉带细节后缀的违规项。
   改为前缀容忍的匹配。

## 自述的 missed 项

自述未发现遗漏项。残余缺口：**无L1 独立评审**（自审 ≠ 独立评审）。
边界测试是基于标记的，**无法证明裁决语义的缺席** —— 内容必须由独立评审判断。

## 顺序与语义边界

```text
FIELD_CONTRACT_FROZEN_BEFORE_CLI = YES
  顺序：(1) schema (2) CLI (3) reference (4) 模板 (5) 测试。
  schema 写完并封闭后才存在任何 CLI 代码。
UNDECLARED_FIELDS_ADDED_TO_CLI = NO
  三重检查：(a) 测试断言 CLI 枚举 == schema 枚举；
  (b) 测试断言模板键 ⊆ 合同声明的允许键集；
  (c) AST 测试断言 CLI 未引入 collect/validate 之外的 flag。
  schema 设 additionalProperties:false；每个 CLI 字段都可溯到已声明槽位。
CLI_CONTAINS_SEMANTIC_ADJUDICATION = NO
  引用实际机制：
   - 「已声明裁决」字段：范围校验，从不推导
   - 「严重度意见」字段：评审人的意见，范围校验，从不推导
   - 不存在「finding 有效性」代码路径：校验函数只读键与形状，从不读finding 语义
   - 运行时输出明写：本工具不做裁决，已声明值是**转录**而非**推导**
   - AST 强制：没有任何赋值目标指向那些语义字段；没有名为裁决/判定/评审的函数
AUTHORITY_REF = 两个，且它们授权的是**不同的东西** —— 已分开陈述：
  - 结构（哪些文件可以存在）：由 THE_ROUTING_TABLE 命名该路径为授权依据，
    加既有的 schema/模板先例与校验器先例
  - 字段语义：取自既有reference 的对应小节 —— 是**转录**而非发明，
    并由测试断言转录的枚举与该 reference 一致
  **明确声明**：没有任何票或已批准 spec 授权本候选的**内容**。
  这就是「已授权结构 ≠ 候选正确」。本报告声称结构被授权，
  **不**声称候选正确。正确性需要本臂无法执行的独立评审。
REVIEWED_HISTORY_REWRITTEN = NO（HEAD 未变；未提交/推送/接触远端；工作区差异为空）
```

## 负控（每项均以 SHA-256 字节比对确认恢复）

```text
A 窄化 schema 严重度枚举 → 枚举一致性测试如期变红 → schema 字节相同地恢复
B 放宽 CLI 已声明裁决集合，加一个不可能值 → 越界测试如期变红 → CLI 字节相同地恢复
C 直接：喂入该不可能的已声明裁决值 → FAIL 枚举违规，exit=1
端到端演示：collect → 0 violations 通过；篡改 → exit=1
```

## 验证结果

```text
TESTS_RESULT = scripts/tests 69 tests OK（既有 32 + 新增 37）
              新文件单独 34 OK；负控 3 OK
              adapters 套件 69 跑 / 23 errors（预存在）
VALIDATE_GOVERNANCE = 31/31（与基线一致；新增 6 个文件零违规）
状态校验器 = 16/16
PUBLIC_RELEASE_VIOLATIONS = 0（对象数 57→63，本臂 6 个文件进入公开候选面并被扫，干净）
   --commit-metadata: VIOLATIONS=0；--selftest: 51/51
   脚本在该 base 确实存在；实测所得，非替代
PREEXISTING_FAILURES = 适配器套件 23 errors —— 归因已证，非假定：
   在**不含本臂任何文件**的纯净 base 上同样复现（69 跑 / 23 errors），换TMPDIR 亦然。
   非本臂造成；既非纯环境 —— 是既有测试fixture 代码里的潜在缺陷，
   Linux CI 可能不触发。未修（越界）
FILES_CHANGED = 6 个新未跟踪文件，0 修改
DIFF_STAT = 全部新增，+1361 / -0
   受保护路径未触碰；载体未修改；未读 experiments/
VALID_COMPLETION = YES
```

## 自陈的两条保留

1. **授权缺口是真的**：结构由路由表授权，内容由既有 reference 授权，但没有任何已批准
   spec 授权**本候选的字段选择**。没有把「路径被批过」当作「合同是对的」——
   这一区分正是历史评审的全部要点，而那样声称恰是本次要测的失败模式。
2. **`VALID_COMPLETION = YES` 只覆盖机械验证**。按规则这是自审；合同的**语义**正确性
   必须由独立评审判断，本臂无法提供。

[fact-check] 编排者独立核验：本臂产出的 3 个关键文件确实落盘。
`references/review-evidence.md` 属本臂新增产物之一，**不在 base** ——
这独立佐证了本臂报告的「路由目标悬空」finding 为真，而非工作记忆偏差。