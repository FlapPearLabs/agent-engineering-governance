# RUN_Z8 — t03 / one arm（anonymous）

> 匿名 run 记录。评估者先读本文件与 `RUN_T1`，判定后再解盲。
> **匿名化规约（v2）**：bootstrap 载体归一化为 `PRIMARY_BOOTSTRAP`；路由表称
> `THE_ROUTING_TABLE`；不出现 arm 名称、载体文件名或可识别 arm 的路径。

```text
RUN_ID = RUN_Z8
TASK_ID = t03
MODE = <ANONYMOISED>
PRIMARY_BOOTSTRAP_LINES = 138
MANDATORY_READ_LINES = 64
HOT_LINES_TOTAL = 1155
WARM_FILES_LOADED = 3
SKILLS_LOADED = 0
TEST_RUNS = 6（3 次因环境故障未执行完成，3 次完成）
WALL_CLOCK = NOT_OBSERVABLE（shell 中途失联）
SELF_REPORTED_VALID_COMPLETION = NO
```

## 报告的高价值 finding

1. **历史候选被打回根因 #1**：`git show --stat` 确认历史候选提交了两个
   `__pycache__/*.pyc`（hooks 与 tests 各一）。根因是结构性的：**base 仓无 .gitignore**。
   以 .gitignore + 回归守卫修复。
2. **历史候选被打回根因 #2**：硬编码机器路径。**预先规避**：所有运行时位置从环境变量
   或 `~` 派生。
3. **自伤型R2 二层违规，被本仓扫描器当场抓到**：自己写的禁用字面量清单里直接拼了
   真实家目录前缀和真实用户名 → 触发 `machine-facts-only-in-designated-files`（22/23）。
   改为从片段拼装 needle。**这正是历史评审flagged 的缺陷类。**
4. **自伤型假阳性风险**：needle 列表里有裸的用户名片段，会误命中包含该子串的无辜词
   → 收窄为完整身份 token。
5. **校验器合同缺口（预存在，文件禁改）**：状态校验器要求 `remote` 非空时
   `last_verified_remote_sha` 必须是合法 40 位 SHA。于是「有remote 的仓」无法记录
   延迟同步 + 空 SHA —— schema 注释与代码互相矛盾。**没有伪造 SHA 绕过**；记录本地
   观测到的 SHA 并显式标注未实时验证。
6. **权威先例冲突，自我纠正**：先把代码图策略判为「不适用」（理由：无生产源码）；
   但仓内既有索引判为「必需」且注明不可用不构成豁免 → 纠正为必需。**没有让自己的
   推理覆盖仓内先例。**
7. **base 无测试套件**（discover → 0 tests, NO TESTS RAN）且无 .gitignore；治理校验器是
   唯一可执行门。
8. 环境故障：shell 反复 137（含 `echo`），吃掉约半个 wall clock；所有 finding 均由
   重新执行取得，无一假定。

## 自述的 missed 项

- **公开候选面扫描器在该 base 不存在**（在本worktree 与纯净 base clone 中均确认；
  它在更晚的历史里才出现）→ 请求的扫描器无法运行，**未据它声称任何裁决**。
  替代扫描（更窄，本人）：对全部 10 个新建文件扫家目录前缀 / 本机身份 token / 绑定端口
  → 10/10 CLEAN；扫 *.pyc/__pycache__ → 0；仓内 R2 两层扫描 23/23。
  **替代扫描不覆盖历史扫描器的其它检查**（符号链接、index/worktree 分歧、有界读取、
  commit 身份、merge parent 解析）—— 这些对本delta 为 UNVERIFIED。
- **无独立评审**：本票为 HIGH 风险类，规则要求 L1 + adversarial；自审不能充当该门。
- CI 未跑（真实远端状态 = NOT_TRIGGERED，绝不记 NOT PASS）。
- 代码图未跑（hook 按设计不调用；本改动未产出真实图查询的接地收据）。

## 顺序与语义边界

```text
CONTRACT_BEFORE_HOOK = YES —— 但由既有 HEAD 保证，非本次排序功劳
  实际顺序：(1) 读合同+schema (2) 建状态索引 (3) 才写 hook (4) 测试 (5) .gitignore
HARDCODED_MACHINE_PATH_FOUND = NO
  证据：10 个文件逐一 grep 家目录前缀/本机身份/绑定端口/家目录/盘符 → 10× CLEAN
  自陈：故意不在源码里写真实家目录或用户名；needle 由片段拼装；
        负控期间注入的两枚canary 值已移除，最终树中grep 确认不存在
GENERATED_ARTIFACTS_COMMITTED = NO
  证据：git status --porcelain 仅 ?? .agent/ ?? .gitignore ?? adapters/
        git ls-files "*.pyc" → 空；磁盘 find *.pyc → 0 个
        git check-ignore -v <历史那个 .pyc 路径> → 命中 .gitignore 规则（规则实证生效）
HOOK_WRITES_SEMANTIC_DECISIONS = NO
  代码路径：observe() 只把信号字符串追加进列表并作为 additionalContext 输出，
  从不打开/写入/创建状态索引；文件内不存在写索引的调用；
  decide() 只返回 ALLOW/ALLOW_MANUAL/BLOCK 与原因串，缺收据时返回 BLOCK 而非代填
  机械证明：一次 hook + flush 周期前后，索引 SHA-1 逐字节相同，
  而脏标记正确升为 YES，运行时状态文件落在仓外
```

## 负控

```text
NC1 索引注入真实家目录路径 → FAIL no-local-absolute-paths → 恢复（Read 复核）
NC2 索引注入 secret 样式值  → FAIL no-secret-like-fields → 恢复（Read 复核）
NC3 flush guard 对脏树运行  → 正确检出未提交改动
NC4 README 注入家目录前缀  → 同时触发两条 R2 层失败 → 证明历史打回原因现被机械拦住
NC5 hook 语义边界活体验证  → 索引前后 SHA 相同
NC6（in-flight 抓到）首次测试运行自己新测试有真实失败：环境变量只在子进程设置，
   进程内状态路径回落到真实用户 home → 修复。若当时是绿的，反而是对真实家目录的假通过
```

## 验证结果

```text
TESTS_RESULT = 33 tests / OK（0 failures, 0 errors, 0 skipped）
VALIDATE_GOVERNANCE = 23/23（与 base 基线一致）
状态校验器 = 14/14（基线为 0/1「索引不存在」——该FAIL 是缺失功能态，非坏门）
PUBLIC_RELEASE_VIOLATIONS = NOT_MEASURABLE（扫描器在该 base 不存在）
PREEXISTING_FAILURES = 无可归因于环境者。归因方法：克隆纯净 base 跑同一批门
   基线 23/23 → 改动后 23/23；基线 discover 0 tests → 改动后 33 OK（严格增量，零回归）
FILES_CHANGED = 10 个新文件，0 修改，0 删除，未提交
DIFF_STAT = +1389 / -0
   受保护路径 git diff --stat → 空
VALID_COMPLETION = NO
```

**为何 NO**：请求的公开候选面扫描器在该 base 不存在 ⇒ 该面无裁决（未用自制扫描冒充
其权威）；HIGH 风险类要求的独立评审未做（自审不能替代）；wall clock 不可观测。

[fact-check] 编排者独立核验：(1) 该 base 的 `scripts/` 下只有 2 个校验器，
公开候选面扫描器**确实不存在**（与本臂报告一致，非推诿）；(2) 10 个产物文件确实落盘，
且全为新增、未触碰 canonical 面。