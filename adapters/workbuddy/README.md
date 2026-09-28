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
| 用户级 settings = `<home>/settings.json` | **FACT**（2026-09-28 端到端 deny 实测） | 源码推断 + 已安装注册与 live deny 实测（见本节末 AFTER 块） |
| `PreToolUse` 支持 `permissionDecision = "deny"` 且判为 blocking | FACT | CLI bundle 内 `hookSpecificOutput.permissionDecision` 处理分支 |
| command hook 退出码 2 = 阻塞该工具调用 | FACT | 随 App 发布的 `hooks.md`「简单方式：退出代码」 |
| hook 以 stdin JSON 接收 `hook_event_name` / `tool_name` / `tool_input` | FACT | 随 App 发布的 `hooks.md`「Hook 输入」 |
| hooks 功能状态 | **Beta**（接口可能调整） | 随 App 发布的 `hooks.md` 顶部标注 |
| hook 配置在 WorkBuddy 会话内的**实际接线面** | **OBSERVED**（2026-09-28） | `~/.workbuddy/settings.json` 现有 1 条 PreToolUse 注册（matcher `Bash`）；真实会话中命中拒绝面的工具调用**在执行前**被宿主拦截（见本节末 AFTER 块） |

`UNKNOWN` 不等于可用。部署方必须跑完 §4 的负例测试，**在真实会话里观察到 deny**，才可声称该门生效。

**强制等级用语（与 `adapters/zcode/` 的既有诚实契约对齐，不得混用）**：

```text
ENFORCED   存在**可核验的宿主 deny 映射**（运行时「exit 2 → 宿主 DENY」的机器可读登记），
           且已在真实会话中观测到一次真实 deny。
ADVISORY   无可核验 deny 映射时的诚实降级态（合法）：产物已评审、可部署，
           但宿主侧是否真的阻断尚未观测。
NOT_RUN    live 端到端 deny 实测未执行。`NOT_RUN` 永不等于 `PASS`。
```

**部署前（2026-09-27 评审时，历史记录）**：`ADVISORY` + `live_verification = NOT_RUN`
（当时无 deny 映射登记、无 live 观测）。

**部署后 / 实况验证（2026-09-28 实测，WorkBuddy 5.5.3）**：
**本适配器当前 = `ENFORCED`**——**仅**在下列限定内成立：

- 限于本文件 §3 文档化的拒绝面；分类器仍是**非封闭**的静态文本分类器
  （KNOWN NON-COVERAGE 第 4 类「结构边界」不变，`--shallow-file` 等"今日即不完整"
  实例仍在，shell 求值 / 别名 / 文本外 config 等类全部不变）；
- deny 映射登记 = `~/.workbuddy/settings.json` 的 PreToolUse 注册（机器可读；已部署产物
  sha256 `b22b0659…` 与集成源 `cea9acc` 一致）+ 宿主真实拦截观测；
- 观测到的 deny = 真实会话中命中拒绝面的工具调用**在执行前**被宿主拦截
  （2026-09-27 两次、2026-09-28 一次；2026-09-28 为真实的 `git push --force` 形式）；
- 状态只对**观测到的 WorkBuddy profile** 成立，不随版本自动延续；
  hook 卸载 / 注册缺失 / 宿主行为变化 → 回落 `ADVISORY`。

`NOT_RUN 永不等于 PASS` 的规则不变。**任何报告不得据此写成**：所有强推路径已不可能 /
所有破坏性 Git 行为已被阻止 / 本 hook 是完整的 Git 安全边界 / 静态命令分类器已封闭——
这些都不成立（见 §3 已知未覆盖）。

## 3. Hook 的拒绝集与边界

`hooks/git_safety_guard.py` 只拒三类：

```text
GIT_PUSH_FORCE    git push / git send-pack --force | -f | --force-with-lease | --mirror
                  以及**命令文本中指名了强推载体 config 键**的 push：
                      remote.<name>.mirror
                      remote.<name>.push
                  按**键**匹配、不按注入写法——`-c`、`--config-env`（等号与空格两种）、
                  `--config=`、`GIT_CONFIG_COUNT/KEY_n/VALUE_n` 都被同一条规则覆盖。
                  判定在**去引号后的 token 上**做、且**不依赖子命令定位**，所以
                  `remote."origin".mirror` 与「未知取值型全局选项吞掉子命令」也不能绕过。
                  **但这不等于封闭**——见下第 4 条。
GIT_RESET_HARD    git reset --hard
GIT_CLEAN_FORCE   git clean 带 --force/-f 且不是 dry-run（-fd / -df / -fdx / -f / --force 等）
```

**明确不拒**（因为其合法性取决于执行状态，V1 没有可机读的状态权威）：

```text
git rebase          git commit --amend        Edit / Write
git push --follow-tags      git reset --soft      git clean -n / --dry-run
```

**与 `references/git-ci-integration.md` 的两处有意差异（部署方必须知道）**：该文件对破坏性工作区动作
设了两处放宽，本 guard **两处都不做**：

```text
§2    对「可弃的一次性 worktree（未评审、未推送、可重建）」豁免 reset --hard / clean -fd
§5.2  把「有 pre-state 记录 + 保全集 + post-state 记录」的破坏性动作判为 LEGAL
      （该节是这一面的 canonical owner；本 README 只指针，不重述其 recipe id）
```

两者都需要可机读的执行状态权威（判断一个 worktree 是否可弃、一个事务是否已完整记录），而 V1 没有。
因此本 guard 在这两点上**比 §2 / §5.2 更严**，且方向是 fail-closed；它不新增规则，也不放宽这两节的
任何要求。把这条差异写出来，是为了避免读者把「更严」误读成规则本身。

**引号一致性（刻意 fail-closed）**：`bash -c 'git push -f'` 与 `git push -f` 同判。
代价是**打印**这类字符串的命令（`echo 'git push -f'`）也会被拒。换一种写法即可，静默强推不可以。

**拒绝集是「实测」得出的，不是「相信」得出的**。每个候选向量都在 git 2.53.0 上跑过「本地与远端
已分叉」的真实场景，判据是**远端 ref 是否真的移动**（`(forced update)`）：

```text
真实强推 → 拒绝              --force | -f | --force-with-lease | --mirror
                            任何指名 remote.<name>.mirror / remote.<name>.push 的
                            命令行 config 注入；以下每一种写法都实测过：
                                -c remote.<name>.mirror=true
                                -c remote.<name>.push=+<refspec>
                                --config-env=remote.<name>.mirror=V        （等号形式）
                                --config-env remote.<name>.mirror=V        （空格形式）
                                GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=remote.<name>.mirror
                                    GIT_CONFIG_VALUE_0=true
                                git --config=remote.<name>.mirror=true     （git 其实拒绝该写法）
真实强推 → 已声明未覆盖       git push origin +main                （见下第 1 条）
                            命令文本之外的 config 载体            （见下第 3 条）
                            **本分类器尚不能封闭的其它轴**         （见下第 4 条）
并非强推 → 放行              --force-if-includes 单独出现         （--force-with-lease 的附属项）
                            -c push.force=true                    （git 没有 push.force 这个键）
                            GIT_PUSH_FORCE=1 / PUSH_FORCE=1       （git 不认这些环境变量）
```

`git help --config` 列出 `push.default` / `push.followTags` / `push.useForceIfIncludes` 等，
**没有 `push.force`**。

**评审第 4 轮的更正（诚实记录，不掩埋）**：第 1–3 轮曾把 `-c push.force=true` 与前置
`GIT_PUSH_FORCE=1` 当作强推载体并加了拒绝规则，其依据是一个**未经实测的假设**。实测证明该假设为假：
两者都被 git 以 non-fast-forward 拒绝、远端 ref 未动。因此第 4 轮**移除**了这些规则——拒绝一条合法
且不会强推的命令不服务于任何不变量，并违反 R8「它防住哪一次已发生的失效？」。同一轮**加入**了实测
确认为真实强推、而此前被放行的 `--mirror` 与 config 注入载体。移除项与加入项都在测试矩阵中显式断言
（`MeasuredNonVectors` / `ConfigInjectedForce`），使这次更正不会被静默回退。

**评审第 5 轮的更正**：同一把尺子继续量下去，又得到两处修正——都是「用一样的判据」，不是新政策：

```text
加入  --config-env=<name>=<envvar>    `-c` 的长形兄弟，git 亦确有该选项。
                                    实测 V=true git --config-env=remote.origin.mirror=V push origin
                                    造成真实强推，而此前被放行。
                                    其值不在命令文本里、hook 也看不见 shell 环境，故对匹配键
                                    **fail-closed 拒绝**（即使该变量恰好是假值）——这是一处
                                    刻意接受的假阳性，写在明处而非藏起来。
移除  --force-if-includes             实测单独出现时不强推（rc=1、远端未动）；而它真实出现时必然
                                    与 --force / --force-with-lease 同现，那两种写法早已被拒。
                                    故它对检测**零边际贡献**，只增加假阳性面——判据与第 4 轮
                                    移除那批规则完全相同。此前代码与本表互相矛盾，现已一致。
```

**评审第 6 轮的更正——换形状，而不是再加一条规则**：

```text
第 4 轮加了 `-c` / `--config-env=` 的解析；第 5 轮补上 `--config-env` 的空格形式；
第 5 轮评审随即又找到 `GIT_CONFIG_COUNT` / `GIT_CONFIG_KEY_n` / `GIT_CONFIG_VALUE_n`
与空格形式仍可强推。两轮各补一种写法、每次又被找到下一种——这说明**问题在形状，不在勤勉**。

第 6 轮改为**按键匹配**：只要命令文本里出现 `remote.<name>.mirror` 或
`remote.<name>.push`，且同一段文本里存在 push，即拒绝。于是
`_config_assignments` / `_push_force_via_git_config` / `_truthy` 与两条按写法的正则
**被删除**（分类逻辑净减 12 行：355 → 343）、覆盖面更大，且不必在将来 git 新增写法时
再补一次。文件总行数持平——删掉的是机械，补上的是这条规则必须的解释。
```

**由此刻意接受的假阳性**（写成测试断言，见 `AcceptedFalsePositives`）：命令里只要**指名**了载体键
就会被拒，即使它并不能强推：

```text
git -c remote.origin.mirror=false push origin             命名了键，但不能强推
git -c remote.origin.push=refs/heads/x:refs/heads/x      值不是 + 强推 refspec
git push origin && git config remote.origin.mirror true   在 push 之后才设键
```

每一行的代价是「一个没人会写的命令形式」；静默强推的代价是被改写的历史。这条取舍与既有的
`echo 'git push -f'` 同源，不是新政策。该清单是**举例而非穷尽**（例如载体挂在**另一个远端**上，
如 `git -c remote.upstream.mirror=true push origin`，同样会被拒而同样不会强推）。

**评审第 7 轮的更正——补三个实例，同时收回一句过度声明**：

```text
实例（均已实测会强推、此前放行）：
  引号        git -c remote."origin".mirror=true push origin
              → 判定改为在**去引号 token** 上做（tokenizer 本来就去引号，旧代码却拿原始串正则匹配）
  取值型选项  git --attr-source HEAD push -f origin master
              → --attr-source 会吞掉 `push`，使子命令被误判；已把它加入取值型全局选项表
  管线命令    git send-pack --force <url> <refspec>
              → send-pack 是 push 的管线等价物，已与 push 同等对待

收回的声明：第 6 轮写过「将来新增的写法都被覆盖」。该句只对**同一机制的新写法**成立，
对引号与选项元数（arity）并不成立——第 6 轮评审正是从这两处绕过的。已按实际测量改正。
```

**已知未覆盖（诚实边界，非疏忽）**——本 guard 是**静态文本分类器，不是 shell 求值器**，且是纵深防御而非沙箱：

```text
1. refspec 强推        git push origin +main
                       原因：实测 `git check-ref-format --branch "+main"` 判定 `+main` 为
                       **合法分支名**，故前导 `+` 在纯文本层无法与非常规 ref 名区分；
                       而误拒一次普通 push 被判定为更坏的失败。这是「实测会强推但仍放行」
                       的形式之一（另一类是第 3 条的持久 config 载体），且已显式断言在案。

2. shell 求值类        C="git push -f"; $C                B=git; A='push -f'; $B $A
                       `git push --force`                 $(git push --force)
                       alias g=git; g push -f             function g { git "$@"; }; g push -f
                       ./renamed-wrapper push -f
                       git -c alias.f='push -f' f origin  （**git 级**别名——被隐藏 token 的载体
                                                         是 git config，机制与 shell 别名相同）
                       原因：字面 token `git` + `push` + force 标志被 shell 展开、别名或包装脚本
                       隐藏后，文本分析根本看不见。这一层应由会话级权限规则或宿主侧 deny 映射承担；
                       本 hook 不假装自己是那一层。

3. 命令文本之外的载体  **本 guard 读不到其内容的任何配置来源**：
                       · 已写入 .git/config 或 ~/.gitconfig 的 `remote.<name>.mirror` /
                         带 `+` 的 `remote.<name>.push`；
                       · 命令行上指名的**配置文件**（`-c include.path=<file>`、`includeIf.*`）
                         ——载体在文件内部，命令文本并不指名键；
                       · 会话开始之前就已 export 的环境变量。
                       原因：本 guard 只读交给它的那一个命令串；持久配置、被包含的文件与环境继承
                       属于仓库与宿主，不归本分类器。若需要覆盖这一层，应由宿主侧 deny 映射承担。

4. 结构边界（**先读这条**）  **对未经解析的 shell 命令串做静态分类，不可能做到封闭**。
                       连续三轮评审各找到一条新轴，且形状完全相同——「被绕过 **且** 未披露」：
                           · 拼写：`--config-env` 空格形式、`GIT_CONFIG_*` 块
                           · 引号：`git -c remote."origin".mirror=true push origin`
                           · 选项元数：`git --attr-source HEAD push -f`（未知取值型全局选项吞掉子命令）
                           · 管线：`git send-pack --force <url> <refspec>`
                       第 7 轮关掉了这四个**实例**，但**轴上仍然敞开**：
                       · 取值型全局选项表是**枚举，且今天就已不完整**——`--shallow-file` 取值、
                         不在表内，实测 `git --shallow-file <file> push -f` 会真实强推；
                         git 将来新增选项亦然；
                       · `_PUSH_LIKE` 之外的会更新 ref 的管线命令；
                       · 任何使字面 token 从字符串中消失的 shell 构造（第 2 条）。
                       要达到**封闭**保证的正确层次**不是本 hook**，而是**git 解析完参数之后**的
                       宿主侧策略，或**远端的分支保护**。请把本 guard 当作一道快速、便宜、
                       fail-closed 的减速带，而不是强制边界。
```

上述「未覆盖」不是可以靠加正则解决的缺陷：测试 `DocumentedNonCoverage` **主动断言第 1、2 类形式确实不被
捕获**；第 3 类（命令文本之外的载体）由 `PersistentStateCarriers` **同样断言不被捕获**。一旦哪天被捕获，
该测试即失败，迫使 README 同步更新——避免边界从「已披露」退化成「想当然」。

**宿主契约依赖（部署方须知）**：`decide()` 要求 `tool_name` 为 `bash`（大小写不敏感）且
`tool_input.command` 为字符串。若宿主改了工具名拼写或载荷形状，本 guard 会**静默放行**，而
`install.py verify` 检测不到这一点。该风险等级为 UNKNOWN，登记在此以免被读成「无此风险」。

**内部错误行为**：脚本内部异常 → **放行 + stderr 诊断**（不阻塞会话）。理由：本 hook 是纵深防御，
不是主 gate；一个会崩的安全网不得让所有普通 Bash 调用失效。脚本仅用标准库、无网络、无子进程、无文件写入，
使该路径实际不可达，并由测试矩阵断言。

**不泄漏**：拒绝理由只含稳定分类 id，**绝不回显、绝不落盘被拒命令文本**——hook 不得成为凭据外泄面。

**规模特性（非安全缺陷，但部署方应知）**：分类工作量对「同一命令串中 git 调用出现的次数」是二次的；
实测 880 KB 的命令约 14.5 s CPU。宿主应对单条命令长度设上限，本 hook 不代为设限
（设限会引入它自己的一类误拒）。

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

本地部署状态的登记点 = 本文件 §2 的「部署后 / 实况验证」块；
安装器留痕（`install-state.json`、带 sha256 的 settings 备份）在本机
`~/.workbuddy/{hooks,backups}/workbuddy-git-safety-guard/`，不入库。
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
└── tests/
    ├── test_git_safety_guard.py       拒绝集 / 放行集 / 已披露未覆盖 / 自检一致性
    └── test_install.py                安装器：幂等、冲突即停、备份摘要、回滚
```

CI 执行：`python3 -m unittest discover -s adapters/workbuddy/tests`（见 `.github/workflows/governance-ci.yml`）。
