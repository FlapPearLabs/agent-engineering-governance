# DEMO-1 执行证据

这里是 2026-10-03 本地隔离演练的实际输出，经路径与合成提交身份净化后发布。原执行的主体与限制见 [验证记录](../adoption-validation.md)。这些文件是证据附件，不是规范、预填回执或新的执行状态机。

- baseline-tests.txt / baseline-app.txt：错误形状替身绿灯，真实入口失败。
- red-tests.txt：真实生产形状反例在修复前失败。
- final-checks.txt：修正后的 exact 演练候选，由独立 Reviewer 执行的检查与运行结果；集成关闭记录另行判断。
- skill-validation.json：实际票级结构校验结果，不证明原 Skill 调用或宿主强制。
- skill-reports.json / repair-skill-validation.json：真实使用后汇报摘录与文档修正阶段的记录校验；并非可直接输入校验器的完整收据。
- artifact-repair.json：独立审查指出路径净化缺口后的逐字保全核验，以及 LICENSE 与固定来源一致的证明。
- review-verdict.md / review-seal.json / review-skill-validation.json：修正候选的独立结论、封存记录与收据校验。此公开选集不含 seal 列举的全部附件；完整 portable packet 留在演练目标仓，不能声称本目录可完成整包摘要复核。
- integration-remote.json / integration-state-flush.json / integration-skill-validation.json：接受的行为候选与后续报告 tip 的分别记录、实际 bare remote 复读和有界写回结果。
- adversarial-probes.py.txt / adversarial-probes-result.txt：独立 Reviewer 的实际探针原文与执行输出。脚本需要放在名为 `candidate` 的演练候选 checkout 旁，保存为 `.py` 再运行；不会自动在治理仓执行。
- code-fix.diff：从演练起点到已实现候选的 app/test 差异，可在复制的 fixture 中复现修复。

演练 SHA 来自本地 bare Git 对象，不是另一个公开 GitHub 项目的提交链接；治理输入有公开的同 tree 快照。路径净化不改变退出状态和断言含义，净化输出不冒充原字节流。复现时重新取得自己的证据，不能把这里的 PASS 绑定到你的候选。

## fresh 恢复的初始故障

[初始结论](recovery-initial-verdict.md)、[封存](recovery-initial-seal.json)、[状态](recovery-initial-state.json)与[远端观察](recovery-initial-remote.json)保存默认 HEAD 故障；[HEAD 检查](recovery-initial-default-head.txt)说明 clone 退出 0 仍可能没有可恢复 checkout。这些初始记录保持失败状态，后续修正不能把它们改名为 PASS。

[回执正负控](recovery-receipt-controls.json)验证原 subject 并拒绝错绑当前 SHA；[恢复行为探针](recovery-behavior-probes.py.txt)与[输出](recovery-initial-probes.txt)是新审计员自有的取消异常身份和重叠调用检查。脚本保存为 `.py`，放在名为 `initial-clone` 的候选 checkout 旁再运行。

[初审 Skill 校验](recovery-initial-skill-validation.json)与[交接校验](recovery-handoff-skill-validation.json)保留机械结果。公开选集不含初始 seal 的全部 49 附件，同样不声明完整封包可在本目录核验。

## 默认入口的有界修复

[HEAD 修正](default-head-correction.json)保存仅元数据操作前后 refs/对象清单不变；[当前远端核验](recovery-repair-remote.json)保存新管理提交和无分支参数的普通 clone；[写回记录](recovery-repair-state-flush.json)保持旧 snapshot 与当前真实 head 的区别。[发布前 Skill 校验](recovery-repair-prepublication-skill-validation.json)只绑定当时已完成阶段，不冒充后续 exact final receipt 或独立恢复接受。

## 修复后的独立恢复接受

[最终结论](recovery-final-verdict.md)、[状态](recovery-final-state.json)、[实际远端](recovery-final-remote.json)和[检查](recovery-final-checks.json)绑定当前管理报告；[正负控](recovery-final-controls.json)重新验证默认恢复和错绑旧 SHA 的拒绝。[新测试](recovery-final-tests.txt)与[入口](recovery-final-app.txt)在真实默认 clone 执行。

[最终评审校验](recovery-final-skill-validation.json)、[交接校验](recovery-final-handoff-skill-validation.json)和[Integrator final 校验](recovery-repair-final-skill-validation.json)记录各自实际阶段。[最终 seal](recovery-final-seal.json)仍是完整外部封包的清单；本目录是净化选集，不含全部 50 附件。实际调用和消息送达继续由原事件与产物判断，机械 true/false/false 不升格为原 Skill 调用或 live enforcement。
