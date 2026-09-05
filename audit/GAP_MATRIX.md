# GAP_MATRIX — AS-IS → TO-BE 差距矩阵

> 优先级按工程价值（影响 × 可达性 × 修复收益 / 复杂度与回归风险），不按严重性修辞。
> 证据缩写：[M]=`~/.workbuddy/MEMORY.md`；[A]=zhihu 仓 AGENTS.md；[S]=本会话机械观测；[K]=skills 目录核验。

| ID | CURRENT_BEHAVIOR | TARGET_BEHAVIOR | EVIDENCE | IMPACT | REACHABILITY | ROOT_CAUSE | RECOMMENDED_CHANGE | AUTHORITY_DESTINATION | COMPLEXITY | REGRESSION_RISK | PRIORITY |
|---|---|---|---|---|---|---|---|---|---|---|---|
| G-01 | 全局宪法 29.8KB 全文塞在 MEMORY.md，注入 ~4KB 即截断；三大 OVERRIDE 位于截断区，agent 实际不可见 | 治理迁入治理仓；MEMORY.md 缩为 ≤4KB 指针文件（偏好/环境事实/指针） | [M] 319 行；[S] 本会话注入副本于 RELEVANT_SURFACE_MANIFEST 中途截断 | 极高：全局规则整体失效于无形 | 每个会话必然发生 | 宪法内容持续追加，载体容量固定 | 全文迁移（MIGRATION_PLAN），MEMORY 只留指针 | 治理仓 AGENTS/RULES/references | 中（迁移+回填） | 低（内容不变，载体变） | **P0** |
| G-02 | 无全局 AGENTS.md/RULES.md；每仓手写一套（zhihu 846 行 vs a'gen't'resume 69 行），语义重复且开始漂移 | 全局 AGENTS/RULES 承载跨仓不变量；项目文件降为 delta + 项目合同 | [S] ls 探测缺失；[K] wc -l 两仓 | 高：跨仓不一致、新仓裸奔 | 每个新项目必然 | 治理以项目为单位生长，无全局宿主 | 建立全局候选文件 + 部署机制 | 治理仓根 | 中 | 低 | **P0** |
| G-03 | `/to-tickets` "work the frontier"：就绪即全部可开工；无 Stage 概念 | Execution Stage 编组：内聚性/写权/爆炸半径/成本选票组，Stage barrier | [K] to-tickets SKILL.md 全文 | 高：并行冲突、人工逐票搬运 | 每个多票项目 | 分解工具早于 Stage 概念诞生 | AGENTS 增加 Stage 层；/to-tickets 产物标注建议 Stage | AGENTS §Stage + references/execution-stage | 低-中 | 中（编组错误需仲裁） | **P0** |
| G-04 | 全局层无 `DAG_IS_NOT_ARCHITECTURE_AUTHORITY` 语义；to-tickets 含 "prefactor" 漂移点 | seam-first 成文：分解=实现切分+lint，禁止票据形状造架构 | [K] SKILL.md "Look for opportunities to prefactor"；[M] 无此语义 | 高（历史真实失效：T08/T09 架构返工类风险） | 高频路径 | 技能默认值未对齐工程教训 | AGENTS 硬语义 + seam-first 参考 | AGENTS + references/execution-stage | 低 | 低 | **P0** |
| G-05 | CodeGraph 语义（增量/独立性）只在 MEMORY 散文；worktree 图库碎片化（wt 有 .codegraph、主仓没有）；canonical graph 无机制 | canonical healthy graph @ master + delta 同步协议 + 健康触发全量重建 | [S] .codegraph 存在性差异；[M] Lane V2 段 | 高：评审建立在陈旧图上 | 每个 lane | 图库所有权未定义；worktree 天然分叉 | references/codegraph-grounding 成文 + 部署约定 | references/codegraph-grounding | 中 | 中 | **P1** |
| G-06 | 评审分级缺失：MEDIUM/HIGH 票一律触发全链（含三方评审），LOW 票也无减负通道 | L0/L1/L2 分级 + 风险四档门槛矩阵 | [M] Lane V2 自动适用于 MEDIUM/HIGH，无 LOW 通道；[A] quorum 表仅按 ticket TYPE | 高：成本/时延浪费，流程压垮低风险工作 | 每票 | V2 设计目标是堵住 T09 级失效，未做强度分级 | AGENTS 评审分级节 + ticket-lane 风险矩阵 | AGENTS + references/ticket-lane | 中 | 中（分级错误→放行） | **P1** |
| G-07 | REPAIR_SATURATION / budget=2 / Arbiter 语义位于 MEMORY 尾部截断区 | 语义迁入候选 AGENTS/RULES + 专门 reference | [S] 注入截断位置；[M] 287-319 行 | 高：无限修复循环在不知情时复发 | 每次评审分歧 | Override 追加在文件尾 | 迁移（同 G-01） | AGENTS + references/review-and-repair-saturation | 低（随 G-01） | 低 | **P0** |
| G-08 | NOVELTY-FIRST 报告语义同在截断区；项目 AGENTS §2.1.5/2.1.6 另有一套（重复维护） | 全局统一 novelty-first；项目只留项目特有字段 | [M] 140-283 行；[A] §2.1 | 中：报告冗长复发 | 每票汇报 | 双处维护 | 迁移 + 声明 canonical owner（去重） | references/review-and-repair-saturation | 低 | 低 | **P1** |
| G-09 | CI 状态规则在截断区；机械核验全靠 agent 手工；无 harness | CI 语义全局成文；L0 harness 按 NOW/NEXT 分级引入 | [M] 189-248 行；[S] 无任何 harness 文件 | 中-高 | 每个带 CI 的 PR | 规则无宿主、无工具化 | git-ci-integration 成文；harness 列 NEXT（先规则后工具） | references/git-ci-integration | NOW 低 / NEXT 中 | 低 | **P1** |
| G-10 | 模型路由表为散文名单（型号不可核验），无执行面 | RISK FIRST 映射到实际档位（lite/default/reasoning/外部）；外部评审走显式路由 | [M] 65-66 行；[S] settings.json 无模型字段 | 中 | 每次派工 | 名单先于平台档位体系 | skills-and-model-routing 成文 + 每季核验名单 | references/skills-and-model-routing | 低 | 低 | **P2** |
| G-11 | 同职责 skill 多套并存（code-review×2、diagnose×2、grill×4），无路由优先级；SKILL_IS_NOT_AUTHORITY 无全局成文 | 全局 skill 路由表 + 权威边界条款 | [K] 目录清单 | 中：路由歧义、技能僭越权威 | 偶发但后果中 | 技能自由生长 | references/skills-and-model-routing + skills/README 治理 | references + skills/ | 低 | 低 | **P2** |
| G-12 | 全局无 auto-advance / STOP 状态枚举；未装 AGENTS.md 的仓退回"逐票请示" | 全局 auto-advance 条款 + 七类 STOP | [A] §3/§17 有；[M] 无全局对应 | 中：自治红利只在个别仓兑现 | 每个非 zhihu 项目 | 项目级进化未回填全局 | AGENTS auto-advance 节 | AGENTS | 低 | 中（越权风险→STOP 兜底） | **P1** |
| G-13 | 机器私有事实进入全局宪法：codegraph 绝对路径硬编码；proxy 127.0.0.1:7897 无任何持久文档；gh 不在 agent PATH | `${HOME}` 占位约定；机器特定事实入 mcp/README MACHINE_SPECIFIC 节；工具链事实成文 | [M] 27 行；[S] 探测记录 | 中：可移植性/可恢复性 | 换机/换环境必炸 | 宪法兼作环境备忘 | 迁移时剥离 + mcp/README 承接 | mcp/README + 治理仓 | 低 | 低 | **P2** |
| G-14 | 部署机制缺失：项目 AGENTS/RULES 靠人肉复制，新仓 bootstrap 无从谈起 | README 提供安装/部署配方（WorkBuddy 实际加载行为的诚实描述） | [S] 全局无 AGENTS/RULES；两仓各自手写 | 中 | 每个新仓 | 无治理发行物 | README 部署节（本 PR 即含） | 治理仓 README | 低 | 低 | **P1** |
| G-15 | `git config --global user.name/email` 为空；署名纪律只活在用户记忆 | 署名约定写入 git-ci 参考（repo-local config 为执行点） | [S] git config 探测 | 低-中：身份不一致影响审计 | 每次提交 | 从未落文 | references/git-ci-integration 记录约定 | references/git-ci-integration | 低 | 低 | **P2** |
| G-16 | LOW/机械工作无 L0 承接：简单文档票也走完整 agent 链 | 机器可验事项机器做（清单化），agent 只做语义判断 | [M]/[A] 均无 L0 概念 | 中：成本与延迟 | 高频（大多数票其实是 LOW） | 评审架构未分层 | review 分级（同 G-06）+ harness（G-09） | AGENTS + references | 中 | 低 | **P2** |
| G-17 | 历史手改 Spec/治理需用户逐轮把关（Spec 4 轮 + tickets 1 轮全人工） | governance change 走双评审 quorum（CONTRACT+CONSISTENCY），人只在真 gate | [A] §5.1 已有；[M] 无全局对应 | 中 | 低频高价值 | 项目机制未全局化 | AGENTS governance-change 条款 | AGENTS | 低 | 低 | **P2** |
| G-18 | Windows 时代政策：活跃面 0 残留（grep 实测），但无分类条款防再移植 | macOS 基线成文；旧 Windows 材料归档为 STALE/REFERENCE | [S] 三处 grep 全空 | 低 | 低 | 环境已切换 | RULES 加 macOS-baseline 条款 | RULES | 低 | 低 | **P3** |

## 汇总

- CRITICAL_GAPS = [G-01, G-02, G-03, G-04, G-07]
- HIGH_VALUE_NONCRITICAL = [G-05, G-06, G-09, G-12, G-14]
- LOW_VALUE_LONG_TAIL = [G-10, G-11, G-13, G-15, G-16, G-17, G-18]
- STALE_POLICIES = [Windows 系（仅历史形态，活跃面已清零 → G-18）]
- DUPLICATE_POLICIES = [G-08（MEMORY vs 项目 AGENTS 双写）, G-02（跨仓重复）]
- WINDOWS_ONLY_POLICIES = []（活跃面无）
- PROJECT_SPECIFIC_NOT_GLOBALIZED = [captured!=verified、capability isolation、Continuous Goal Mode、双评审 quorum —— 均按"抽象保留全局、字面留在项目"处理]
