# V1.2 Evidence Lineage（非 canonical）

> 本文件把三件事放在一起：**第 1 节：本轮从仓内材料整理出的真实历史证据**、
> **第 2 节：候选 H1–H4 的 evidence lineage**、**第 3 节：下一实验候选（STRUCTURE_DELTA_SHADOW）**。
> 整理只做引用与归类，**不新增任何规则**；外部经验只能是 SUPPORT。
> 建立基线：main 的 0404879（2026-10-07），分支 experiment/v1.2-foundation。

## 0. 候选状态语汇（仅用于本目录）

```text
IDEA_ONLY              = 只有方向，尚无任何本地失败证据
LOCAL_FAILURE_OBSERVED = 本地真实失败或命中已有仓内记录
EXPERIMENT_CANDIDATE   = 本地失败证据 + 实验设计（cases / metrics / 机制草案）已就位（可执行回放的前置条件见第 3 节）
LOCALLY_VALIDATED      = 实验已实际运行，候选效果在本地得到证据支持
```

提升规则：外部 SUPPORT 永远不能提升状态；只有本地实验证据可以把状态推进到 `LOCALLY_VALIDATED`。

## 1. 本地证据整理（只归类，不新增规则）

材料简写（相对本目录的链接，首次出现即给出；此后只用简写）：

- **WEM** = [WORKFLOW_EVOLUTION_MAP.md](../../audit/WORKFLOW_EVOLUTION_MAP.md)（G1–G4 世代账本）
- **P2M** = [PAIN_TO_POLICY_MAP_V2.md](../../audit/PAIN_TO_POLICY_MAP_V2.md)（P01–P24 痛点账本）
- **DH** = [design-history.md](../../docs/design-history.md)（H01–H18 决策解释）
- **BC** = [BOOTSTRAP_CONTRACT.md](../../deployment/BOOTSTRAP_CONTRACT.md)（注入通道实测与字节预算）
- **AE** = [adoption-evidence/README.md](../../docs/adoption-evidence/README.md)（采用演练证据附件索引）

### A. GOVERNANCE_OVERHEAD（治理开销）

- Skill 链仪式化（低风险票也要全套）、多套同职责 skill 并存引起路由混乱 —— WEM 的 G2。
- 全员最大流水线化：每票都跑最大流水线，成本与风险不匹配 —— WEM 的 G3；DH 的 H06。
- CodeGraph 全量重建仪式：每个 worker 与评审重建图库 —— WEM 的 G3；P2M 的 P10。
- 评审与修复膨胀：无限修复循环、修复预算被反复重置 —— P2M 的 P11、P22（12 commit 记录）。
- 文本膨胀与注入压力：仓内流程文本一度达 846 行；规则塞入记忆尾部导致注入截断、
  实际可见性崩塌 —— WEM 的 G1、G3；BC（实测截断点与指针字节预算）；DH 的 H14。
- 实验形状的过度机械化（本治理仓自身；2026-10-07 本轮修正记录）：V1.2 地基把一次性的实验启动要求
  （case 数量区间、五类 task_class 全覆盖、指定 failure family 全覆盖）机械固化进 canonical 测试
  套件（274 行），形成新的维护成本 —— `TEMPORARY EXPERIMENT SHAPE != PERMANENT GOVERNANCE
  INVARIANT`。记录为证据，不上升为 canonical rule。

### B. ARCHITECTURE_DRIFT（架构漂移）

- 实现期发明架构：票内自造模块或启发式替代既有权威模块 —— P2M 的 P01。
- 分解产物反向塑造架构、票据形假缝 —— P2M 的 P02；DH 的 H03。
- 缝错位：共享 owner 被拆票、大票无法独立评审 —— P2M 的 P03。
- 「模块测试自洽而真实链路不通」；异步缝合同错误穿透单元层 —— DH 的 H03（含 Z03 记录）。
- 分解组合失效：单票合法、DAG 合法，但组合合同不成立 —— P2M 的 P19。

### C. FALSE_CONFIDENCE（虚假确信）

- 假 RED：模块缺失或 harness 损坏冒充反例证据 —— P2M 的 P07。
- CI 状态坍缩与自分类：未触发被当通过；执行者自称基线失败自行放行 —— WEM 的 G3；P2M 的 P08、P09。
- 陈旧评审转移：修复后旧批准被沿用到新对象 —— P2M 的 P06；AE 中恢复审计的对照组实证。
- 门无法失败：退出码遮蔽与提前通过标记 —— DH 的 H16（W02）。
- 饱和代替评审门：仲裁结论被外推成集成资格 —— P2M 的 P22 增补。
- 归因撤回：错误的模型归因与错误的「已防强推」向量均被实测撤回 —— DH 的 H13、H14。

### D. STATE / CONTINUITY（状态与连续性）

- 执行状态活在会话记忆里，会话即失忆；人工搬运 prompt —— WEM 的 G1；P2M 的 P15。
- 状态必须长于会话：状态索引与会话缓存分离 —— DH 的 H02。
- 真实恢复故障：远端默认 HEAD 指向不存在分支，clone 退出 0 但无可恢复 checkout —— AE 的 recovery-initial-verdict.md。
- 破坏性动作的保全不足（历史事故教训；底层因果未闭合，按限定表述引用） —— DH 的 H12。

## 2. 候选 Evidence Lineage（H1–H4）

### H1 — reduce hot prompt / progressive disclosure

- CANDIDATE = 减少热提示（注入指针）字节；细节改为按需加载，同时保留必读面的显式性。
- LOCAL_FAILURE_EVIDENCE = 规则全部塞入记忆尾部导致注入截断、可见性崩塌（WEM 的 G3）；注入实测截断点与指针字节预算的存在（BC）；「全文放入记忆会被截断」的实测修正记录（DH 的 H14）。
- EXTERNAL_SUPPORT = 外部 agent 平台的 progressive disclosure 实践（工具与文档按需加载）。SUPPORT ONLY；不构成本仓证据。
- CURRENT_HYPOTHESIS = 当更多约束被下沉到机械层后，热提示可以更小；必读项保持显式、细节按需可达即可，可见性不因变小而受损。
- CURRENT_STATUS = LOCAL_FAILURE_OBSERVED

### H2 — lazy Skill loading

- CANDIDATE = Skill 从「开工全载」改为「阶段转换或领域命中时加载与全文读取」。
- LOCAL_FAILURE_EVIDENCE = 技能链仪式化（低风险票也跑全套）与路由混乱（WEM 的 G2）；全员最大流水线（WEM 的 G3）；Skill 接线与使用后汇报带来的持续记录成本（P2M 的 P23；DH 的 H17）。
- EXTERNAL_SUPPORT = 外部平台的按需、懒加载 Skill 实践。SUPPORT ONLY。
- CURRENT_HYPOTHESIS = 懒加载降低治理开销；风险是「该用的没用」——须保留票级 Skill 记录与使用后短报作为可信性证据，否则不采纳。
- CURRENT_STATUS = LOCAL_FAILURE_OBSERVED

### H3 — architecture structure-delta mechanical detection

- CANDIDATE = 结构增量（新模块、新依赖、新接口、新状态 owner 等）的机械检出；第一形态为 STRUCTURE_DELTA_SHADOW（见第 3 节）。
- LOCAL_FAILURE_EVIDENCE = 实现期发明架构与假缝（P2M 的 P01、P02、P03）；缝合同错误穿透单元层（DH 的 H03；Z03）；P01 明确该类的机械执行面目前是「部分，靠评审」——即机械检出缺位。
- EXTERNAL_SUPPORT = 外部「结构感知检查、diff 结构统计」类实践。SUPPORT ONLY。
- CURRENT_HYPOTHESIS = 结构信号可以从 diff 机械提取，作为 shadow 报告供给评审与架构层；它本身不构成 gate，也不替代语义判断。
- CURRENT_STATUS = EXPERIMENT_CANDIDATE（机制设计见第 3 节；seed corpus 已建；replay input corpus = READY_FOR_SHADOW_PROTOTYPE；v0 detector 已实现、H3-A 历史回放已运行——状态不升级，见第 3 节）

### H4 — reduce low-risk review/process overhead

- CANDIDATE = 低风险与非生产票的流程成本下降（更少的固定轮次与证据形态），质量底线不动。
- LOCAL_FAILURE_EVIDENCE = 首版「每个通过都需要独立评审」过宽、误伤低风险非生产票（P2M 的 P05 修正记录）；低风险票被要求同等证据的过度形态（P2M 的 P07 修正记录）；低风险工作消耗强模型与人工搬运（DH 的 H06；P2M 的 P14）；治理仓自身修复循环消耗评审预算（P2M 的 P22）。
- EXTERNAL_SUPPORT = 外部按风险缩放流程的实践。SUPPORT ONLY。
- CURRENT_HYPOTHESIS = 在 B 层不变量与高价值 blocker 语义不动的前提下，低风险票可以进一步薄化；底线由材料回放守住（executable replay corpus 就绪后；must_catch 未命中即失败）。
- CURRENT_STATUS = LOCAL_FAILURE_OBSERVED

## 3. 下一实验候选 — STRUCTURE_DELTA_SHADOW（v0 已实现：H3-A 历史回放已运行，状态见下）

- 目标：把「结构增量」从主观评审判断扩展为可机械提取的第一版观察信号。
- 第一版预计观察（仅 shadow 输出，不做判定）：

```text
NEW_MODULE
NEW_DIRECTORY
NEW_PACKAGE
NEW_DEPENDENCY
NEW_PUBLIC_INTERFACE
NEW_STATE_OWNER
NEW_PERSISTENCE_SURFACE
CROSS_BOUNDARY_DEPENDENCY
```

- （2026-10-08 注）进入 corpus 的 **v1 确定性信号**目前只有 `NEW_FILE` / `NEW_DIRECTORY` /
  `NEW_DEPENDENCY`（唯一 PREDICATE + COUNTING_UNIT，见 [replay/README.md](replay/README.md)
  定义表）；上列其余类别在取得唯一机械谓词之前为 `NOT_YET_MECHANICALLY_DEFINED`，
  不得作为 replay oracle。

- 信号语义（与 [metrics.md](metrics.md) 对齐）：机械信号 ≠ 漂移结论；`confirmed_architecture_drift` 需要「结构信号 + 架构/Spec 语义处置」，不得由信号数替代。
- 明确禁止（本轮与下一轮实现前）：不接入 CI、不 block merge、不新增评审门、不改变既有评审语义；「看起来很好」不构成接入理由。
- **回放前置条件（executable replay corpus）**：当前 cases.yaml 是 `HISTORICAL BENCHMARK SEED CORPUS`，**不能直接回放**；只有补齐全套真实、可恢复的 `BASE STATE / HISTORICAL DIFF OR CANDIDATE / EXPECTED SIGNAL` 的 case，才进入未来的 executable replay corpus。
- **状态更新（2026-10-08，PR #40 → H3-A 轮）**：durable replay-ready cases 已建于 [replay/](replay/)
  （REPLAY_DIFF 唯一绑定 + v1 确定性信号 + 双轴 disposition + authority_ref 纪律）；
  v0 detector（[structure_delta.py](structure_delta.py)）已实现，并在全部 ready cases 上
  完成 H3-A 历史回放（结果见 [results/h3-a-structure-delta-v0.md](results/h3-a-structure-delta-v0.md)）：

```text
REPLAY_INPUT_CORPUS = PARTIALLY_READY / READY_FOR_SHADOW_PROTOTYPE
DETECTOR = V0_IMPLEMENTED_NOT_WIRED
LOCAL_VALIDATION = H3_A_HISTORICAL_REPLAY_RUN
```

  H3 不因此升级（仍 `EXPERIMENT_CANDIDATE`——自分类仅提案，升格另走独立评审）；
  seed corpus 本身的「不能直接回放」性质不变。

- 下一轮优先：从真实历史 commit/diff 中提取少量 positive / negative controls；**禁止**为了让 benchmark 可运行，按事故描述人工编造 synthetic architecture case。（已完成：durable replay-ready cases 已建于 [replay/](replay/)；数量属实验数据，不在此固化。）
- 成本纪律：不得为 shadow 引入每会话全量重建（对照 P2M 的 P10 教训）；只对候选 diff 做增量提取。
- 预期产出仅为 shadow 报告与 reviewer 可引用的证据块；promotion 与否另走既有治理变更协议。
