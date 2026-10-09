# RUN_M4 — t02 / the other arm（anonymous）

> 匿名 run 记录。评估者先读本文件与 `RUN_B9`，判定后再解盲。
> **匿名化规约（v2）**：bootstrap 载体归一化为 `PRIMARY_BOOTSTRAP`；路由表称
> `THE_ROUTING_TABLE`；不出现 arm 名称、载体文件名或可识别 arm 的路径。

```text
RUN_ID = RUN_M4
TASK_ID = t02
MODE = <ANONYMOISED>
H1_RECEIPT = S1:read S2:MEDIUM S3:two WARM refs via THE_ROUTING_TABLE S4:NO_REMOTE
PRIMARY_BOOTSTRAP_LINES = 157
MANDATORY_READ_LINES = 75
HOT_LINES_TOTAL = 232
WARM_FILES_LOADED = 2
SKILLS_LOADED = 0
TEST_RUNS = 15
WALL_CLOCK = NOT_OBSERVABLE (no reliable start/end clock)
SELF_REPORTED_VALID_COMPLETION = YES
```

## 报告的高价值 finding

1. **5 处 F841 全部实测定位**（非从历史提交抄），4 处在允许范围内修复。
2. **第 5 处与 hard scope 冲突**（禁改 `scripts/validate_*.py`）→ 以 `per-file-ignores`
   显式豁免并写明缺陷真实存在、未修原因、移除条件。自报这是本次交付**唯一的覆盖缺口**，
   且以配置注释形式可见 —— 但「注释即控制」不是机械强制。
3. **`select` 集无防篡改守卫**（负控 2 实证）：把 select 清空后门完全失明、退出码 0，
   而 `validate_governance.py` 的 32 项检查无一覆盖 `ruff.toml`。
   历史提交曾有 `ci-executes-static-gate` 检查，但不在本 base。
   **本仓当前状态：静态门可被无声掏空而 CI 仍绿。**
4. **首次负控设计缺陷自查**：下划线前缀变量落入工具默认 dummy-variable 忽略区 ⇒
   控制「无法失败」，重做后才取得真控制。
5. **`select=["E"]` 会使门变红**（E501 占 555 中的 541）→ 红门会被忽略从而失去信号价值。
6. **仓库用 unittest 不是 pytest**；用 pytest 会产生「0 tests」的假通过。

## 自述的 missed 项

- select 集无防篡改守卫（见上）：本次以配置内注释披露替代，非机械强制。
- 工具版本 pin 与本机 PATH 上的二进制未做哈希级一致性校验。
- 未验证 CI 上 py3.12 下的行为与本机一致。
- 未读某policy 映射文件（是否要求新 gate 有痛点行需先确认适用范围）。

## 自述的 false / redundant 治理动作

- FALSE_GOVERNANCE_ACTIONS = 无（未声明任何未观察到的 PASS；zcode 23 errors 如实报为
  环境阻塞，未坍缩为 PASS）
- REDUNDANT_GOVERNANCE_ACTIONS = 首次负控（下划线变量）—— 自查发现控制无效后重做，
  已记入 findings 而非静默丢弃

## 基线（配置前实测）

```text
35 tracked .py / 22,994 lines，零工具配置
select=["E9","F"]→5 | ["E4","E7","E9","F"]→19 | ["E"]→555 | ["UP"]→143
| ["RUF"]→189 | ["B"]→6 | ["I"]→3 | ["E9"]→0
（与历史提交记录逐项吻合，基线可信）
测试基线：scripts/tests 423 OK；workbuddy 42 OK；zcode 90 跑 / 23 errors（预存在）
```

**注**：实测基线直接改变了设计—— 若按工具默认 select 配置，门会要求一次全仓风格迁移
（明确越界）。实测的 14/19 风格类split 才是 `select=["E9","F"]` 的依据。

## 负控

```text
NC1 向脚本注入未使用局部变量 → F841 → exit 1 → 恢复（diff 空 + grep 计数 0）
NC2 同一缺陷在位下把 select 改为 [] → "All checks passed!" exit 0  ← 门失明，证明 select 承重
NC3 注入未使用导入 → F401 → exit 1 → 恢复
每次恢复均核对文件内容与 git diff，不信任退出码
```

## 验证结果

```text
TESTS_RESULT = scripts/tests 423 OK（pre/post 恒等）；workbuddy 42 OK（恒等）
              zcode 90 跑 / 23 errors（pre/post 恒等）
VALIDATE_GOVERNANCE = 32/32（pre 与 post 均 32/32，check 名集合未变）
PUBLIC_RELEASE_VIOLATIONS = 0（pre/post 均 0）；--selftest 51/51（恒等）
PREEXISTING_FAILURES = zcode 23 errors —— 同源证明：前后失败清单逐行一致；
   23/23 全部为宿主 file-broker shim 的 mkdir PermissionError；分类 INFRASTRUCTURE
FILES_CHANGED = ruff.toml(新增) + requirements-dev.txt(新增) + CI 接线(M)
              + 3 个测试文件（F841 修复）
DIFF_STAT = tracked +25/-4；新增 ruff.toml 3445 B / requirements-dev.txt 714 B
VALID_COMPLETION = YES
```

## 有意未复现的历史项

- 历史提交附带的 `references/` 框架扩写 —— 在禁改目录内。
- 某 policy 映射文件的新增条目 —— 需先确认适用范围。

两者都不影响门本身的确定性。

[fact-check] 编排者独立核验：worktree HEAD = 015780be…（与预期 base 一致）。
本臂与另一臂**独立收敛到同一高价值 finding**（第 5 处 F841 的 scope 冲突 + select 可被
静默掏空而 CI 仍绿），且两臂都自报了同一覆盖缺口。