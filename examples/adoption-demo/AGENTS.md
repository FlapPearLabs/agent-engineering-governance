# 演练目标仓本地权威（fixture）

本文件与 SPEC 是测试输入，只授权一次隔离演练，不授权修改真实项目或治理仓。

- 采用治理仓的通用 RULES 与 AGENTS/references 默认；使用复制演练时记录的已接受完整 SHA。治理副本由测试入口提供。
- 不采纳 FlapPearLabs 的组织署名；演练仓使用测试协调者设置的合成公开署名。不得读取或改变全局 Git 配置、凭据、MEMORY、hooks。
- 本仓代码任务为 MEDIUM；Task DEMO-1 的合同见 SPEC.md。允许变更 app.py、tests、按既有合同新增的状态索引与票级执行证据。禁止改 Spec 来隐藏失败，禁止添加新产品能力。
- 演练已有批准的单票和真实 producer/consumer 边界；本次不进行新拆票。Worker 仍核对该合同与组合范围，不能由此豁免真实项目的新拆票证明。
- 此演练只使用本地 Git bare remote，执行控制面是 docs/task.md。没有 GitHub Issues、PR 或 Actions。禁止将本地证据说成真实 PR CI。
- `OVERRIDE = references/git-ci-integration.md §3 real PR CI default overridden by this fixture AGENTS: only for DEMO-1, deterministic local tests + independent reviewer rerun + bare-remote push/fetch verification form the integration evidence (source: isolated adoption exercise).`
- Stage 仅 DEMO-1，一次一个 Integrator，ff-only。Worker 不自批或合并；适用 reviewer 对 exact candidate 判断并留记录，再由 Integrator 核验、集成、远端复读。
- 完成 DEMO-1 后 milestone 结束，不授权追加第二张产品票。
