# adapters/workbuddy — WorkBuddy runtime adapter (V1)

> **Runtime adapter, not the contract.** 本目录把治理里**已经存在的**硬约束接到 WorkBuddy 的运行时通道上；
> 它不定义新规则、不覆盖 `RULES.md` / `AGENTS.md` / 任何 canonical reference。
> 参考同类：`adapters/zcode/`（PROJECT_CONTINUITY_CONTRACT 的参考实现）。

## 1. 本版解决的问题（只此一个）

治理里反复出现、且在各仓 `RULES.md` 中已属**硬不变量**的一条：**不得 force push；不得用破坏性
workspace 操作（`reset --hard` / `clean -fd` 类）绕过异常**（参见本仓 `RULES.md` R5 与
`references/git-ci-integration.md` §2）。在 WorkBuddy 下，这条目前是**纯文本纪律**——没有任何机械门。

V1 只把这一条变成 `PreToolUse` 机械门。**其余一律不做**（见 §5 的显式排除清单）。

## 2. 运行时能力假设（以及哪些是 UNKNOWN）

证据与完整记录见 `audit/AS_IS_WORKBUDDY_V3.md` §2–3。摘要：

| 假设 | 状态 | 依据 |
|---|---|---|
| WorkBuddy 会话内 home = `~/.workbuddy`（`CODEBUDDY_CONFIG_DIR`） | FACT | `getWorkbuddyConfigDir()`；`~/.workbuddy/{skills,plugins,logs}` 实测印证 |
| 用户级 settings = `<home>/settings.json` | **INFERENCE**（未做端到端 deny 实测） | `PathUtils.getSettingsFilePath(USER)` = `getHomeDir()/SETTINGS_FILENAME` |
| `PreToolUse` 支持 `permissionDecision = "deny"` 且判为 blocking | FACT | CLI bundle 内 `hookSpecificOutput.permissionDecision` 处理分支 |
| command hook 退出码 2 = 阻塞该工具调用 | FACT | 随 App 发布的 `hooks.md`「简单方式：退出代码」 |
| hook 以 stdin JSON 接收 `hook_event_name` / `tool_name` / `tool_input` | FACT | 随 App 发布的 `hooks.md`「Hook 输入」 |
| hooks 功能状态 | **Beta**（接口可能调整） | 随 App 发布的 `hooks.md` 顶部标注 |
| hook 配置在 WorkBuddy 会话内的**实际接线面** | **UNKNOWN** | 无端到端 deny 观测；`~/.workbuddy/settings.json` 当前无 `hooks` 键 |

`UNKNOWN` 不等于可用。部署方必须跑完 §4 的负例测试，**在真实会话里观察到 deny**，才可声称该门生效。

**强制等级用语（与 `adapters/zcode/` 的既有诚实契约对齐，不得混用）**：

```text
ENFORCED   存在**可核验的宿主 deny 映射**（运行时「exit 2 → 宿主 DENY」的机器可读登记），
           且已在真实会话中观测到一次真实 deny。本适配器当前**不声称** ENFORCED。
ADVISORY   无可核验 deny 映射时的诚实降级态（合法）。**当前状态即 ADVISORY**：
           产物已评审、可部署，但宿主侧是否真的阻断尚未观测。
NOT_RUN    live 端到端 deny 实测未执行。`NOT_RUN` 永不等于 `PASS`。
```

即：**本适配器当前 = `ADVISORY` + `live_verification = NOT_RUN`**。任何报告不得把它写成「已强制」。

## 3. Hook 的拒绝集与边界

`hooks/git_safety_guard.py` 只拒三类：

```text
GIT_PUSH_FORCE    git push --force | -f | --force-with-lease | --force-if-includes
GIT_RESET_HARD    git reset --hard
GIT_CLEAN_FORCE   git clean 带 --force/-f 且不是 dry-run（-fd / -df / -fdx / -f / --force 等）
```

**明确不拒**（因为其合法性取决于执行状态，V1 没有可机读的状态权威）：

```text
git rebase          git commit --amend        Edit / Write
git push --follow-tags      git reset --soft      git clean -n / --dry-run
```

**引号一致性（刻意 fail-closed）**：`bash -c 'git push -f'` 与 `git push -f` 同判。
代价是**打印**这类字符串的命令（`echo 'git push -f'`）也会被拒。换一种写法即可，静默强推不可以。

**命令内强推向量**：不使用 `--force` / `-f` 也能造成强推的写法现在会被拒：

```text
git -c push.force=true push ...            （git config 注入；--config= 亦覆盖）
GIT_PUSH_FORCE=1 git push ...              （环境赋值）
export GIT_PUSH_FORCE=1 && git push ...    （跨语句赋值——与上面同判，见下）
set -a; GIT_PUSH_FORCE=1; set +a; git push ...
```

**跨语句 env 赋值（评审第 2 轮后补入）**：`export GIT_PUSH_FORCE=1 && git push …` 把赋值放在了
**另一条语句**里，逐语句扫描会漏掉而 bash 仍会强推。现在按 fail-closed 处理：
**同一命令串内**任意位置出现真值 force 赋值 **且** 任意位置存在 `git push` → 拒绝。
代价是 `git push origin main GIT_PUSH_FORCE=1` 这类并非真强推的写法也会被拒——与既有 fail-closed
取向一致，并已在测试中断言。

**已知未覆盖（诚实边界，非疏忽）**——本 guard 是**静态文本分类器，不是 shell 求值器**，且是纵深防御而非沙箱：

```text
1. refspec 强推        git push origin +main
                       原因：`+` 前缀无法在没有真实 ref 解析时与非常规 ref 名区分，
                       而误拒一次普通 push 被判定为更坏的失败。

2. shell 求值类        C="git push -f"; $C                B=git; A='push -f'; $B $A
                       `git push --force`                 $(git push --force)
                       alias g=git; g push -f             function g { git "$@"; }; g push -f
                       ./renamed-wrapper push -f
                       原因：字面 token `git` + `push` + force 标志被 shell 展开、别名或包装脚本
                       隐藏后，文本分析根本看不见。这一层应由会话级权限规则或宿主侧 deny 映射承担；
                       本 hook 不假装自己是那一层。
```

上述「未覆盖」不是可以靠加正则解决的缺陷；测试 `DocumentedNonCoverage` **主动断言这些形式确实不被捕获**，
一旦哪天被捕获该测试即失败，迫使 README 同步更新——避免边界从「已披露」退化成「想当然」。

**内部错误行为**：脚本内部异常 → **放行 + stderr 诊断**（不阻塞会话）。理由：本 hook 是纵深防御，
不是主 gate；一个会崩的安全网不得让所有普通 Bash 调用失效。脚本仅用标准库、无网络、无子进程、无文件写入，
使该路径实际不可达，并由测试矩阵断言。

**不泄漏**：拒绝理由只含稳定分类 id，**绝不回显、绝不落盘被拒命令文本**——hook 不得成为凭据外泄面。

## 4. 部署（INSTALL / VERIFY / ROLLBACK）

```bash
python3 adapters/workbuddy/install.py status     # 只读盘点
python3 adapters/workbuddy/install.py install    # 幂等；改动前先备份
python3 adapters/workbuddy/install.py verify     # 摘要一致 / 恰好一条注册 / selfcheck
python3 adapters/workbuddy/install.py rollback   # 机械回滚
```

- **幂等**：二次 `install` 不产生重复注册。
- **可回滚**：改 `settings.json` 前备份到 `<home>/backups/workbuddy-git-safety-guard/`（**仓库之外的 local-only 位置**），
  并把摘要写入 `install-state.json`；`rollback` 用摘要核验后恢复。无可用备份时只移除**本 guard 自己的**注册，其它内容不动。
- **冲突即停**：若已存在**同样匹配 Bash** 且不是本 guard 的 `PreToolUse` hook → 打印
  `STOP: LOCAL_HOOK_CONFIGURATION_CONFLICT` 并**保持原状**，不静默替换用户的既有配置。匹配其它工具的条目原样保留。
- **不输出秘密**：只打印摘要、键名与布尔值；`settings.json` 内容（可能含凭据）从不回显。

### 4.1 部署前置条件（顺序不可交换）

```text
1. 本适配器源码已经独立评审（SECURITY + CODE_OR_CONTRACT，同一 exact HEAD）
2. 已合入并 remote verify
3. 使用**该已合入版本**的产物部署（不得手写第二份实现）
4. 部署前有本地备份；部署后用一次性临时仓库做正 / 负 / 回滚三组验证
```

### 4.2 部署状态

本地部署状态（不是本仓事实）登记在 `deployment/BOOTSTRAP_CONTRACT.md` §4 的字段块内，
逐项观测与边界见 `audit/AS_IS_WORKBUDDY_V3.md` §7。

## 5. V1 显式不做的事

以下全部**不在**本版范围，且未经新的独立授权不得顺手加入：

```text
自动 ticket / scope 归属解析
自动 reviewer quorum 状态机
自动 Issue 变更
分布式分支锁
通用 project-state 引擎
自动语义 scope 分类
自动文件写面授权
```

理由（对应 `AGENTS.md` §0 与 `RULES.md` R8 的最小复杂性护栏）：这些机制各自需要可机读的
执行状态权威，而当前不存在；在没有状态权威的前提下做自动化，只会把误拒成本转嫁给日常工程。
每一次扩张都应先回答：**它防住哪一次已发生的失效？**

## 6. 目录

```text
adapters/workbuddy/
├── README.md                          本文件
├── install.py                         INSTALL / VERIFY / ROLLBACK / STATUS
├── hooks/git_safety_guard.py          PreToolUse command hook（待部署产物）
└── tests/test_git_safety_guard.py     确定性测试矩阵（无网络 / 无仓库 / 无子进程）
```

CI 执行：`python3 -m unittest discover -s adapters/workbuddy/tests`（见 `.github/workflows/governance-ci.yml`）。
