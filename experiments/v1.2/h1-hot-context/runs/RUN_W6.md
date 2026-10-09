# RUN_W6 — t04 / one arm（anonymous）

> 匿名 run 记录。评估者先读本文件与 `RUN_P3`，判定后再解盲。
> **匿名化规约（v2）**：bootstrap 载体归一化为 `PRIMARY_BOOTSTRAP`；路由表称
> `THE_ROUTING_TABLE`；不出现 arm 名称、载体文件名或可识别 arm 的路径。

```text
RUN_ID = RUN_W6
TASK_ID = t04
MODE = <ANONYMOISED>
PRIMARY_BOOTSTRAP_LINES = 141
MANDATORY_READ_LINES = 76
HOT_LINES_TOTAL = 1017
WARM_FILES_LOADED = 1
SKILLS_LOADED = 0
TEST_RUNS = 14
WALL_CLOCK = ~92 分钟
SELF_REPORTED_VALID_COMPLETION = NO
```

## 报告的高价值 finding

1. **历史改动的面集已确认**（用 `--name-status` 确认，非猜测）：4 个文件 + 一个测试套件；
   其父提交即本 base。
2. **授权 artifact 已定位**：某已批准 spec 的REQ-W2-01..07 / AC-24..32 / AC-39/42/44。
   **写代码前先逐字提取其 (a)-(g) 子合同。**
3. **CI 状态七值集合的owner 是既有reference 文件**（非自造枚举）。schema 枚举从该文件
   文本导出并由测试绑定 ⇒ 漂移会变红。
4. 接地模式拼写取自既有reference 的 A/B/C 三模式，已核对行号。
5. **校验器会对每个 reference 文件强制要求字面「Canonical owner」** ⇒ 新 reference 必须
   带该标记，否则 31 项门失败。**预先规避而非事后发现。**
6. **仓用 unittest 且 CI 的discover 不带 `-t .`**；加 `-t .` 会破坏发现
   （「Start directory is not importable」）。用了 CI 的写法。
7. **自己最初的 4 个测试失败是自己测试代码的真实缺陷**（声明枚举遍历父节点顺序错；
   关键字扫描命中了「本工具从不自我批准」这类docstring 里的词）。以AST 去除docstring
   修复，而非削弱检查。
8. 某适配器套件的 23 errors **非本改动造成**：traceback 落在宿主沙箱 shim 的mkdir
   broker；该套件对改动文件无依赖。

## 自述的 missed 项

- 环境故障后**未能**在负控恢复之后重跑两个校验器。手头证据（套件全绿、schema 字节相同、
  git status 只含预期文件）来自同一棵恢复后的树，但**最终一次全新绿跑未被观测**。
- 从未跑 `--commit-metadata` 与 `--selftest` 两道门。
- spec 声明的 AC-24/25/26/27 只部分断言：测的是源码级「无网络导入 + 词汇」，
  **不是**植入命令的活体副作用探针。**弱于 spec 的证据标准。**
- 单owner 检查用标题正则扫 reference 文件，抓不到措辞不同的竞争声明。
- **无独立评审**：按规则 MEDIUM 票需 L1，自审不满足；本候选未经独立评审。

## 顺序与语义边界

```text
FIELD_CONTRACT_FROZEN_BEFORE_CLI = YES
  实际顺序：(1) 治理面 (2) 提取 spec 子合同 (3) 写 schema (4) 写 CLI
             (5) 模板 + reference (6) 测试。schema 在磁盘上早于 CLI。
UNDECLARED_FIELDS_ADDED_TO_CLI = NO
  以 AST 抽取 CLI 全部字符串字面量，与 schema 的 16 个顶层键做差集：
  schema 中从未被 CLI 提及的键 = 空；CLI 独有的裁决类键 = 空
CLI_CONTAINS_SEMANTIC_ADJUDICATION = NO
  证明它不能裁决评审结果：
   - 只有两个子命令（collect / validate），由测试断言
   - collect 硬编码**非权威**占位值，不填任何评审权威
   - 唯一触及该轴的地方是「对已声明值的拒绝消费门」：读生产者声明的值，从不计算它
   - 可执行源码扫描（AST 去docstring）不含任何严重度/裁决/批准类 token；无网络
AUTHORITY_REF = 某已批准 spec（提交号已定位）+ 两份既有 reference
  **明确区分**：这命名的是授权**结构**的 artifact；
  它**不**确立本候选正确 —— 只有针对这些条款的独立评审才能，而它没发生。
REVIEWED_HISTORY_REWRITTEN = NO（HEAD 仍是 base；5 个文件均为未跟踪新增）
```

## 负控

```text
NC1弱化 schema 中某哈希字段的模式 40位→7位，用 7 位输入验证
    弱化后 →被接受 exit 0（= 控制生效）
    恢复后 → 拒绝 exit 1，理由为模式违规
    恢复验证：SHA256 前后一致 + 独立副本逐字节比对 + Read 复核
NC2 把四个仅 CI 状态并入通用状态枚举，用该值验证
    弱化后 → 被接受 exit 0；且套件变红（"某状态意外出现在枚举中"）
    恢复后 → 拒绝 exit 1；套件恢复全绿；schema 字节相同
两条都是真控制：应被拒的输入只在故意变异下被接受。
```

## 验证结果

```text
TESTS_RESULT = scripts/tests 66 tests OK（含 32 项新检查 + 34 项既有）
              adapters 套件 69 跑 / 23 errors（全部为宿主沙箱 shim 的 mkdir 权限错）
VALIDATE_GOVERNANCE = 31/31 checks passed
PUBLIC_RELEASE_VIOLATIONS = 0（脚本在该 base 存在；61 个对象被扫，
   对象数因新增文件而上升，违规数仍为 0）
   NOT_MEASURABLE：--commit-metadata 与 --selftest 从未运行
PREEXISTING_FAILURES = 适配器套件 23 errors —— 归因四证：改动前可复现；
   该测试文件对本改动文件无依赖；换TMPDIR 只改路径前缀不改结果；
   traceback 在沙箱 shim 之下。未修（越界）
FILES_CHANGED = 5 个新未跟踪文件，0 修改，0 删除
VALID_COMPLETION = NO
```

**为何 NO**：套件、治理门、公开候选面三者在**这棵恢复后的树**上都观测为绿，两条负控
均通过且恢复为字节相同。但环境随后死亡，无法在恢复后**再观测一次全新绿跑**，
且两道门从未运行。按「未知 ≠ 通过」，不把未观测的跑法报成通过。

## 值得单独提出的一条判断

历史分支在完成本候选后**还需要三次后续修复**，其中包括「强制 schema 模式使用锚定
语义与已声明的失败信封」和「以 ECMA-262 语义端到端求值并fail closed」。
本候选用的是 Python 正则（`re.search`，无 ECMA-262 的锚定/字符类语义），
**很可能带有本候选本应修复的同一类缺陷**。未读那些后续 diff，无法确认；
标记为独立评审应最先检查的高价值项。

[fact-check] 编排者独立核验：本臂产出的 reference 文件在该 base **不存在**
（该文件属于本臂新增产物之一，见FILES_CHANGED），
故另一臂报告的「路由目标悬空」不与本臂冲突 —— 两臂各自新建了同名文件。