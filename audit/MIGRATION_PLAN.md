# MIGRATION_PLAN — 迁移计划（仅计划，本审计不执行）

> STATUS: PLAN_ONLY。本文件描述"如果候选治理获批，如何把现状迁到目标态"。
> 本审计**未**修改 `~/.workbuddy/MEMORY.md`、live skills、live MCP、任何产品仓。
>
> **V2 增补（F1–F7 修复后）**：
> 1. Batch 1 的"新 MEMORY.md"已物化为 `deployment/MEMORY_POINTER_CANDIDATE.md`（≤3,500 字符，实测截断点 4028）；部署前置 = fresh 评审 APPROVE + skills manifest 补齐 + owner 授权（deployment/BOOTSTRAP_CONTRACT.md §2.1）。
> 2. 风险模型定稿为 **LOW/MEDIUM/HIGH 三级 + ESCALATION 触发清单**（原四级 CRITICAL 并入触发清单）。
> 3. ff-only / merge 方法 / CI 形态 / worktree 例外 / macOS 全部降为 D 层默认或 deployment 档案（`deployment/deployment-profile.md`），不再是组织硬规则。
> 4. 新增 Batch 2.5：BOOTSTRAP 部署（MEMORY 指针替换 + fresh-session 验收协议执行 + 归档旧 MEMORY 至 `deployment/archive/`）。
> 5. CodeGraph 机制按真实 CLI 校准（init/sync/status 每目录库；canonical = 主仓目录）——Batch 3 相应行以 references/codegraph-grounding.md V2 为准。
> 6. Machine-specific 政策定稿（R2 第二层）：`deployment/` 下带 `MACHINE-SPECIFIC ALLOWED` 标记的 designated 文件（profile / MEMORY_POINTER / archive）允许宿主路径/端口入库（私有仓、机器恢复用途）；凭据/secret/用户名任何位置绝对禁止；一般治理产物仍禁 machine 事实。旧 MEMORY 归档到 designated 区因此与 R2 一致。

## 迁移批次

### Batch 1 — 宪法搬家（解 G-01/G-02/G-07，P0）

| CURRENT_SOURCE | TARGET_SOURCE | SEMANTIC_CHANGE | WHY | RISK | VALIDATION_REQUIRED |
|---|---|---|---|---|---|
| `~/.workbuddy/MEMORY.md` L13-70（Lane V2 主体） | 治理仓 AGENTS.md §Lane + references/ticket-lane | 语义等价，重排为"骨架在 AGENTS、细节在 REF" | 注入截断修复 | 旧记忆残留造成双权威 → 迁移时同步改写 MEMORY | 新会话注入可见性抽查；两处无重复 |
| MEMORY L73-136（Orchestrator Override） | AGENTS.md §Roles | 等价 | 同上 | 同上 | 同上 |
| MEMORY L140-283（Reporting Override） | references/review-and-repair-saturation §Reporting | 等价（含 CI 压缩例外） | 同上 | 报告格式回退 → 保留模板原文 | 下一票据包按新模板抽检 |
| MEMORY L287-319（Repair Saturation） | AGENTS §Convergence + REF 详表 | 等价 | 同上 | budget 语义丢失 → 逐字段核对 | R3 场景演练 |
| MEMORY L26-30 CodeGraph 段 | references/codegraph-grounding | 绝对路径 → `${HOME}`；补 canonical graph 协议 | 机器私有剥离 | — | wt-lane 图基 SHA 记录存在 |
| 新 MEMORY.md（≤4KB） | — | 指针 + 偏好 + 环境事实 | 载入预算适配 | 遗漏关键指针 → 用本表回填 | 4KB 上限断言 |

### Batch 2 — 机制新建（解 G-03/G-04/G-06/G-12，P0/P1）

| CURRENT_SOURCE | TARGET_SOURCE | SEMANTIC_CHANGE | WHY | RISK | VALIDATION_REQUIRED |
|---|---|---|---|---|---|
| 无（新增） | AGENTS §Stage + REF:execution-stage | 新增 Stage 编组与 barrier | 禁止 START_ALL | 编组保守化拖慢节奏 → Stage 选择输入已含成本项 | SCENARIO S6 演练 |
| 无（新增） | AGENTS §Seam-first | 新增 DAG 非权威语义 | 防 DAG 造架构 | — | SCENARIO P-03 反向追溯 |
| Lane V2 全员全链 | AGENTS §Lane 风险矩阵 | LOW 票减负，CRITICAL 票加档 | 风险分级 | 分级错误放行 → 矩阵含升级触发器 | S1/S2/S3 演练 |
| 项目七类 STOP（zhihu AGENTS §3） | AGENTS §Auto-advance 全局 STOP 枚举 | 抽象为全局七类 | 自治红利全局化 | 越权 → 每类 STOP 有明确触发定义 | S5 演练 |

### Batch 3 — 工具与环境事实（解 G-05/G-09/G-13/G-15，P1/P2）

| CURRENT_SOURCE | TARGET_SOURCE | SEMANTIC_CHANGE | WHY | RISK | VALIDATION_REQUIRED |
|---|---|---|---|---|---|
| 散文 CodeGraph 语义 | REF:codegraph-grounding（canonical+delta） | 新增机制 | 图库碎片化 | delta 漂移 → base SHA 记录义务 | S7 演练 |
| MEMORY CI 段 | REF:git-ci-integration（状态表+证据块） | 等价迁移 | 同 Batch1 | — | S8 演练 |
| 无 | mcp/README（MACHINE_SPECIFIC 节） | 代理/gh PATH/凭据通道成文 | 换机可恢复 | 泄漏敏感信息 → 只写机制不写凭据 | 干净机器按 README 复原演练 |
| 用户记忆署名纪律 | REF:git-ci-integration §署名 | 成文 | 身份一致 | — | commit 作者抽检 |

### Batch 4 — 项目仓降权（解 G-02 尾巴，获批后逐仓执行）

| CURRENT_SOURCE | TARGET_SOURCE | SEMANTIC_CHANGE | WHY | RISK | VALIDATION_REQUIRED |
|---|---|---|---|---|---|
| zhihu AGENTS.md 846 行 | 保留项目特有（Spec 引用、capability isolation、tracker 细节），通用流程段改为引用全局 | 去重 | 双写漂移 | 引用断链 → 保留一层"项目 delta 清单" | 评审 quorum 不变核验 |
| a'gen't'resume AGENTS/RULES | 同上（规模小，改动小） | 同上 | 同上 | — | — |
| adaptive-vocab-reader（无 AGENTS/RULES） | 安装全局候选 + 项目 delta | 新增 | 治理可移植 | — | 项目 Spec 九条 STOP gate 仍优先核验 |

## 执行前置条件（全部满足才可动）

1. 外部治理评审（GPT-5.6 Sol）findings 修复并通过 fresh governance review；
2. 用户明确批准部署；
3. 治理仓 main 已合入候选（approved main）；
4. MEMORY 改写按 Batch 1 一次性完成（避免双权威窗口期）。

## 明确不做

- 不 amend/改写任何产品仓 git 历史；
- 不删除 MEMORY 原文（改写为指针文件前先在治理仓归档原文副本）；
- 不把项目专属字面条款（T08/T09/T12、schema 字段、provider 语义）全局化；
- 不为迁移本身新建自动化。
