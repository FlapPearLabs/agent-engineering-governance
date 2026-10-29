# H5 前置条件：设计，不是启动许可

权威：`experiments/v1.2/mechanization-gap/experiment-protocols.md` §0、§3；N5 入口另见 `experiments/v1.2/TREE_LEDGER.md` N5。本文件只定义关闭证据，全部条件尚未实测，`PROTOCOL_NOT_STARTABLE`。N7 状态按本次任务书描述为并行进行，不以旧树状态推断其结果。

记号：`V3 = experiments/v1.2/h2-lazy-disclosure/freeze-v3/`，`T = experiments/v1.2/tests/`。下列测试是源码中针对该能力的已有测试，不代表本次执行或 H5 集成已通过。

| 条件 | H5 具体要求与已有依据 | 关闭证据 |
| --- | --- | --- |
| P1 目标绑定 | 每次 episode、验证、恢复前绑定 repository identity、真实 worktree、expected HEAD；逐一比对实际 HEAD，错即拒绝。V3 `run_h2r2.py::drive` 记录 base，`T/test_v1_2_h2_freeze_v3.py::test_the_driver_records_the_base_from_the_governance_repository` 仅证明该记录，不证明 H5 每次续跑绑定。须新建绑定检查。 | 正确目标允许；换仓、同 SHA 的另一 worktree、错 SHA 各拒绝，保存每次检查及实测命令。 |
| P2 投放 | 控制臂机械投放规定的长期 context/memory，变体投放由完整账本重放得到的 seed；两臂禁止静默回退。V3 `wrapper_delivery.py::prepare` 的投放由 `T/test_v1_2_h2_freeze_v3.py::test_both_arms_deliver_only_outside_clean_base_with_object_hashes` 覆盖；它不实现 H5 seed。 | 两臂投放路径、哈希、读取回执；删改载体、错 seed 均启动失败。 |
| P3 持久化 | 所有账本、worktree、stdout、原始验证及索引存于 owner 批准的非临时持久位置；中断后可由新进程读取。V3 `sandbox_v2.py::snapshot`、`T/test_v1_2_h2_freeze_v3_driverfs.py::test_snapshot_special_entries_and_collision` 覆盖快照复制的特定边界，不保证持久性或账本可重放。 | 路径设备和持久性检查、重启后完整性与哈希复验、链尾外部锚点；禁用临时目录作为正式证据根。 |
| P4 同构盲化 | 两臂提交同 schema 的 M1–M7 与验收证据，统一投影；隐藏 arm、run ID、路径和其他可识别特征。V3 `run_audit_v2.py::project_verdict`，`T/test_v1_2_h2_freeze_v3.py::test_the_auditor_projection_drops_the_base_sha_and_the_case_id` 仅覆盖已有投影的部分字段，不证明 H5 无侧信道。 | schema 相等测试、逐字段存在性差异与内容扫描、独立盲测记录；无法盲化标 VOID，不填 PASS。 |
| P5 预注册 | H5 开跑前冻结任务、样本数、M1–M7 定义、显著性、成本、停止及无效规则；见 `HARNESS_PLAN.md`。 | owner 批准的版本和 hash；禁止结果后选阈值；当前只是候选。 |
| P6 可达 | 两臂每次要加载的 seed、memory、谓词及任务契约均存在、可读、内容 hash 匹配；不依赖检索 WARM 的假设，但必要路由仍须检查。V3 `sandbox_v2.py::allow_rules` 与 `T/test_v1_2_h2_freeze_v3_sandboxread.py::test_read_and_commands` 覆盖该测试范围内读取，不保证 H5 目标存在且可载。 | 在每个 base、两臂新 home 中逐项读取与 hash 回执；缺失、拒读、过期均不启动。 |
| P7 门完整性 | M3 FALSE_CLOSURE 的定义是宣布 done 时 acceptance predicate 未满足；若把机械门通过当成质量依据，必须先证明 gate 承重。N7 #45 需给出明确 gate/输入/期望、正控（已知坏输入必须被拒）、干净负控通过、失败码与 exact 版本证据；H5 还要对自己的复合 closure 谓词做同样正负控。不得把 N7 的状态或一次绿灯当成证明。 | 可复跑的 N7 处置与 gate 证据，以及 H5 缺 merge、错 SHA、缺 post-merge CI 等注入均失败的证据；否则 P7 未满足。 |

F-013 要求将 completion 当作独立 harness 谓词而非执行者自述；F-014 的环境失败须保留，不可伪造测试成功：`experiments/v1.2/mechanization-gap/failure-mechanism-map.md` F-013/F-014。所有未关闭条件均为未验证，不因本文存在而关闭。
