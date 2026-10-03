# 一张行为修复票，直到另一个 Agent 接手

> 本页是演练，不新增合同字段或 gate。fixture 的已批准输入仅适用于 DEMO-1；真实项目的授权、风险、CI 与部署仍由自己的权威决定。

## 这个案例演示什么

同步测试替身绿灯，真实异步入口失败；按生产形状反例修复，留 Skill fallback 与评审证据，集成后由 fresh Agent 恢复。这是受知乎 PR #87 启发的**合成教学案例**，不把演练代码当成历史原件。

| 阶段 | 输入 | 应产生的东西 |
|---|---|---|
| 采用 | 治理 SHA、演练仓 AGENTS/SPEC、实际能力 | bootstrap receipt、目标仓组织政策、能力缺口 |
| 开票/恢复 | 单票合同与真实 producer/consumer | 状态索引、grounding 与合法下一步 |
| 实现 | 入口失败、同步替身绿灯 | 原因明确的 RED、最小修复、生产形状 GREEN |
| 汇报/评审 | exact candidate、检查、Skill 应用或 fallback | 使用后短报、票级附件与独立结论 |
| 集成/交接 | 接受的候选与远端 | ff-only 集成、remote verify、STATE_FLUSH |
| fresh Agent | 只有治理入口、目标仓与 remote | STATE_RESTORE、候选/评审/远端核验、下一合法动作 |

## 1. 建立一次性目标仓

选择三个全新目录：治理副本 `GOVERNANCE_DIR`、演练仓 `DEMO_DIR`、演练 bare remote `DEMO_REMOTE`。这些变量仅在本机使用，公开记录用占位符。

```bash
mkdir "$DEMO_DIR"
cp -R "$GOVERNANCE_DIR/examples/adoption-demo/." "$DEMO_DIR/"
git -C "$DEMO_DIR" init -b main
git init --bare "$DEMO_REMOTE"
git -C "$DEMO_DIR" remote add origin "$DEMO_REMOTE"
```

由测试协调者设置仅供本次演练的合成 Git 作者，提交起点并 push main。不要读取真实凭据，也不要使用 FlapPearLabs 冒充外部项目身份。若目录已存在则换新目录，演练不清理或覆盖既有工程。

记录治理完整 SHA、目标仓 base SHA 和指针到 AGENTS/SPEC。演练 remote 是本地 bare 仓；这能测真实 Git push/fetch，不证明 GitHub API、PR 或 Actions 可用。AGENTS 已限定本演练的 C-over-D CI 覆盖，不能复制成其他项目的无条件豁免。

## 2. 开工与能力不足处理

Agent 按 PORTABLE_SETUP 读两处权威，并使用其原回执。示例环境没有 CodeGraph、主线工程 Skill 或 canonical MCP 时，明确写缺失：MEDIUM 使用 MODE C，专业 Skill 按 registry 的实际匹配判断；不自行安装、不开宿主 hook。

初始化 `.agent/project-state.json`，指向现有 SPEC/AGENTS 与 `docs/task.md`，控制面为 `other`。它是恢复索引，不复制全套合同或日志。用原 `validate_project_state.py` 校验；代码仓仍记 REQUIRED 的 CodeGraph applicability，具体 unavailable grounding 留在票据证据。

## 3. 先证明绿灯为什么不够

在演练仓根运行：

```bash
python3 -m unittest discover -s tests -v
python3 app.py
```

起点前者一个测试通过，后者失败。诊断应指出 `count_records` 对 coroutine 直接取长度；不能归因于模型或网络。这个失败不是损坏测试 harness，应由真实入口复现。

Worker 选择 `diagnosing-bugs` / `implement` / `tdd` 等触发方法，缺 Skill 时按原表 fallback。使用后报告可以很短，例如：“tdd fallback：真实 FeedClient 加 fake async transport 复现入口失败；修复后入口、空结果和异常传播通过。原 Skill 不可用，未声称调用；证据在本票测试和检查记录。”这是**预期报告样式**，实际结果须从自己的执行取得。

## 4. RED → 最小修复 → GREEN

先增加真实 `run(transport)` 的测试，transport 使用 test-owned async fake；观察缺 await 引发的目标失败。将旧同步 fixture 改为合同要求的 async 形状，再在 consumer 中 await producer 的结果。不要增加通用同步兼容、重试、缓存或网络配置。

```python
async def count_records(client):
    records = await client.fetch()
    return len(records)
```

最低关键反例包括真实入口、多次调用错误、空结果及 transport 异常传播，测试数量取决于真实实现；不为凑数写实现镜像测试。执行该仓已配置检查。演练的语法预检与动态命令是：

```bash
python3 -m compileall -q app.py tests
python3 -m unittest discover -s tests -v
python3 app.py
git diff --check
```

该演练没有目标仓配置的 lint/type gate，如实写 NOT_CONFIGURED；治理仓本身的 Ruff 不被自动注入目标仓。

## 5. exact candidate 的独立评审

Worker 在隔离分支提交候选，将真实执行、fallback 后报告和已有日志组织成原 Skill 票级附件；候选 SHA 的收据放票级证据目录，不能提交到包含自身 SHA 的 commit。

适用 reviewer 先读权威与合同，再看 diff 和原始证据，独立复跑并提出至少两个有价值的新反例。同步假测试不能替代真实入口，Worker 自审不能替代该结论。报告缺口、semantic application 与 host enforcement 的限制；机器记录通过不自动裁决真实 Skill 应用。

## 6. 集成与 STATE_FLUSH

Integrator 重新核对 remote main、候选、exact-SHA 结论及演练 CI 覆盖成立后，串行 ff-only 集成并 push/fetch 复读。实际结果与接受记录写入 `docs/task.md` / 票级证据，索引只更新 snapshot 和指针。

包含 review 和 snapshot 的后续提交改变候选时，消费原评审的有效范围并对 delta 取得所需接受，不能把旧 SHA 的 PASS 说成新 SHA 已审。不要创建包含自身 SHA 的循环证明。

离开前按 STATE_FLUSH 报告已持久化事实与未持久化限制；milestone 到此结束，不自动追加产品任务。

## 7. 不带聊天记录的恢复测试

让另一位 fresh Agent 只得到治理副本、目标仓/remote 地址，不提供 Worker 的解释。它按 STATE_RESTORE 读取索引及正文、fetch，确认真实 main、已接受候选与当前状态，复跑相关检查，输出原恢复回执。

若它误把 snapshot SHA 当成最新 remote、把本地套件当成 GitHub CI、找不到使用后报告或还要你讲关键合同，记录为失败/限制，不能写“无缝接手”。通过时应能判断 DEMO-1 的真实状态及下一合法动作，包括 milestone 已结束。

## 8. 验收证据的边界

实际演练记录见 [adoption-validation](adoption-validation.md)。测试须区分本地模拟 remote、实际治理 PR CI、fresh context 与宿主 live 接线。单次演练不证明所有项目、所有 runtime 自动强制，也不提供节省时间或成本的量化结论。
