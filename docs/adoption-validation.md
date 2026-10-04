# 采用与恢复验证记录

本页记录采用演练的实际范围，不新增治理 gate 或覆盖。教学步骤见 [walkthrough](adoption-walkthrough.md)，通用采用入口见 [adoption](adoption.md)。

## 实际输入与可复现范围

2026-10-03 起在新建的 stdlib Python 演练仓执行 DEMO-1。Worker 与 Reviewer 分别使用 fresh context；恢复审计在 10-04 封存初始失败、修复后的有界接受与交接。它们使用演练仓中的 AGENTS/SPEC 与固定治理副本，没有修改真实知乎项目。

治理实际输入是本地 `20f2567bb04966ed224d487ecf873a8d28995604`，其公开同 tree 快照为 [3e92751](https://github.com/FlapPearLabs/agent-engineering-governance/tree/3e92751a6e5490e826a130835598e5069d8fe8ce)，tree 均为 `24bef0206266aec15cdde24b6c25583373db4bb4`。两个提交 SHA 不同，不能互称；公开快照供读取相同材料。该输入当时是 PR #38 的待审候选，不是已接受发布。普通采用仍按指南选已接受版本。

该输入固定在采用步骤成形时；后续文档修正没有静默替换演练输入。治理候选曾改动已测 MEMORY 指针正文，引起两项冻结测量测试失败；最终改为在正文外限定组织预设范围，恢复原正文后 602 项脚本测试通过。未改冻结测试或预算，未安装 live MEMORY。最终治理交付与这份演练输入是不同快照，各按自己的检查判断。

演练 remote 是本地 bare Git 仓；合成 SSH 标识由仅目标仓的 URL rewrite 指向它。真实 push/fetch 在此本地范围发生，未访问 SSH 服务或 GitHub。演练 AGENTS 显式覆盖 real PR CI 默认，由独立重跑及 bare remote 核验提供等价证据；治理仓自身的 [PR #38](https://github.com/FlapPearLabs/agent-engineering-governance/pull/38) CI 另行判断。

## 已发生的执行

| 阶段 | 实际结果 | 证据 |
|---|---|---|
| 起点 | 一个同步替身测试通过，真实入口因对 coroutine 取长度失败 | [测试](adoption-evidence/baseline-tests.txt)、[入口](adoption-evidence/baseline-app.txt) |
| 生产形状 RED | 真实 run → FeedClient → async transport 的三个反例在 app 修改前失败；不是导入或 harness 故障 | [RED](adoption-evidence/red-tests.txt) |
| 最小修复 | consumer await producer 后取长度；无重试、缓存、网络或 Spec 修改 | [实际代码与测试 diff](adoption-evidence/code-fix.diff) |
| GREEN 与静态检查 | 修正候选上 3/3 测试通过，真实入口输出 2；语法、状态索引 16/16、diff 与 ancestry 通过 | [独立 exact 检查](adoption-evidence/final-checks.txt) |
| 独立反例 | 等待 transport 完成且调用一次、原 CancelledError 传播、并发与后续调用结果隔离，三个新探针通过 | [探针原文](adoption-evidence/adversarial-probes.py.txt)、[执行输出](adoption-evidence/adversarial-probes-result.txt) |
| 独立接受 | 修正后的 `fe9a33c5cd3a1b014b7f3ac0d22c6e80395b4372` 通过，只有未配置 lint 的非阻断发现；保留原阻断记录 | [结论](adoption-evidence/review-verdict.md)、[封存](adoption-evidence/review-seal.json) |
| 集成与写回 | 独立角色转任 Integrator 后 ff-only 集成接受的候选；再追加仅文档/索引/证据的 LOW 关闭提交，核验远端与 STATE_FLUSH | [远端观察](adoption-evidence/integration-remote.json)、[写回回执](adoption-evidence/integration-state-flush.json) |
| fresh 初始恢复 | 默认克隆无法恢复；指定 main 后内容可恢复，封存 CHANGES_REQUESTED | [初始结论](adoption-evidence/recovery-initial-verdict.md)、[状态](adoption-evidence/recovery-initial-state.json) |
| 默认入口修复 | 只修正 bare HEAD；所有分支及 128 项可达对象清单不变；普通克隆自动检出 main 与索引 | [修正](adoption-evidence/default-head-correction.json)、[远端核验](adoption-evidence/recovery-repair-remote.json) |
| fresh 最终复核 | 当前 main 的普通默认 clone、索引、合同、合法终点与管理 delta 独立核验通过；保留非阻断项 | [结论](adoption-evidence/recovery-final-verdict.md)、[恢复状态](adoption-evidence/recovery-final-state.json)、[实际检查](adoption-evidence/recovery-final-checks.json) |

演练起点为 `0d6d3814c265e6ed10016f84357ac9ca6f8c8eeb`，独立评审绑定行为候选 `fe9a33c5cd3a1b014b7f3ac0d22c6e80395b4372`；初次报告/索引关闭提交为 `7c44db432cf2f82282357085295f400d396d02bc`，其 parent 是前述候选。默认入口修复后又追加 13 个文档/索引/证据路径的 LOW 报告提交 `4bc73940859efbe033fa579a6cda1eb2a6d63a24`，parent 是初次关闭提交；这才是当前实际 remote main。原提供目标 clone 保持旧 7c44 且干净，新普通 clone 从真实 remote 恢复当前主线。报告提交按已采用的非生产 LOW 默认单独 L0 检查，不把旧 SHA 的行为 PASS 重新标成新 SHA 全量评审。源码、测试、Spec、AGENTS 与 LICENSE 均未因关闭记录改变。

## Skill 与采用中发现的问题

Worker 按阶段执行 `diagnosing-bugs`、`implement`、`tdd`、`code-review`、`handoff` 的手工 fallback，使用后向 Parent 汇报；Reviewer、恢复审计员与 Integrator 也按各自实际阶段判断选择集合并使用后汇报。[实际汇报摘录](adoption-evidence/skill-reports.json)与[记录校验](adoption-evidence/skill-validation.json)分别保存。当前 registry 无这些主线 Skill 原文，也无匹配的 stdlib asyncio 专业 Skill。机械记录有效不证明原 Skill 调用、消息送达或宿主强制，输出的 semantic/host booleans 保持 false；执行真实性仍消费原产物与独立重跑。

这次采用暴露并保留了三项摩擦：复制后的 README 相对文档链接失效，治理仓的示例现已改为在线导航并提示读取固定版本或离线副本，旧演练仓保留起点 README；只复制示例目录会漏掉根目录 LICENSE，步骤已补上并在演练仓保留许可；baseline traceback 虽净化了工作区路径，仍含具体 Python 安装根。独立审查因此对 `11062995ea3607f680b6168651d7f2f2b6688354` 给出 CHANGES_REQUESTED，Worker 以 append-only 文档修正回应，不改产品、扫描器或 gate。

fresh 恢复又发现 bare remote 的 HEAD 指向不存在的 `master`，实际主线是 `main`；初始命令只对目标仓指定分支，遗漏了 bare remote。指南已改为 `git init --bare -b main`；独立 Integrator 用 symbolic-ref 修正隔离远端的默认指针，正常 ff push 管理记录并验证新普通 clone。修复时的[写回回执](adoption-evidence/recovery-repair-state-flush.json)保留预算 2/2、旧 snapshot 的历史含义及当时待复核状态，不升级旧行为 PASS。其后独立审计员对当前 4bc739 默认克隆与 13 路径管理 delta 给出有界 PASS_WITH_NONBLOCKING_FINDINGS，STATE_RECOVERY COMPLETE，并完成 handoff；[新封存](adoption-evidence/recovery-final-seal.json)与初始 CHANGES_REQUESTED 分别保留。

现有路径模式扫描对原候选零命中，仍未发现该 traceback 问题；不能把零命中升格为完整 R2 合规或历史干净。恢复复核还实际运行[默认 clone 与错绑 SHA 的正负控](adoption-evidence/recovery-final-controls.json)，原生测试和入口在新 checkout 再次通过。最终[评审记录校验](adoption-evidence/recovery-final-skill-validation.json)、[恢复交接校验](adoption-evidence/recovery-final-handoff-skill-validation.json)与[Integrator exact 校验](adoption-evidence/recovery-repair-final-skill-validation.json)分别保存；中断时未封存收据曾因报告引用不全而失败，补齐关联后才通过并封存，不修改旧阶段报告。

演练累计 reviewer-driven 修复为 2/2（路径净化、默认 HEAD）；各时点的旧记录保留当时轮次，新 SHA、角色转换均不重置预算。

## 不由本演练证明的范围

这是一个 runtime、一个合成行为票的采用试验。演练记录 `LINT/FORMAT = NOT_CONFIGURED`、`TYPECHECK = NOT_APPLICABLE`、`STATIC_GATES_COMPLETE = NO`；规定的原生检查已执行，不能称全部静态工具已通过。CodeGraph 与 canonical MCP 缺失，使用 MODE C；不宣称图或在线工具证据。

所有 runtime 的自动注入、live hook enforcement、第三方 Skill 的真实调用、实际 GitHub CI 与本地 bare remote 是分别验证的面。未改全局 Git 配置、live MEMORY 或 hooks；本 PR 最终治理材料保留既有脚本、schema、CI、adapter 与已测 MEMORY 正文。治理仓 PR 的 CI 只证明该候选的适用检查，不证明目标项目已完成宿主部署，也没有跨项目效率或成本测量。
