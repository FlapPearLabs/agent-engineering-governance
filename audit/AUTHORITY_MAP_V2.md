# AUTHORITY_MAP_V2 — 六层权威模型（F1 修复的语义基础）

> 取代 AUTHORITY_MAP_V1 的"全局宪法 > 一切，项目只能更严"倒置模型。
> 核心修正：**仓库本地产品权威高于全局执行默认**；只有极薄的普适不变量（B 层）高于一切用户治理；平台/系统权威（A 层）高于一切。
> AUTHORITY_MODEL_FROZEN = YES。

## 0. 冲突裁决算法

```
冲突发生 → 按 LAYER 表找 CAN_BE_OVERRIDDEN_BY
→ 可解析 → 按解析结果执行并记录（哪个层、哪条授权覆盖了哪个默认）
→ 不可解析（真实契约冲突）→ STOP: CONTRACT_CONFLICT → product owner 裁决
```

- "覆盖"必须是**显式**的（repo 文档/Issue/Spec 明文），静默覆盖 = 违规。
- 任何层都不得覆盖 A（平台/系统）与 B（普适不变量）。
- 记录格式：`OVERRIDE = <layer> <clause> overridden by <authority> <clause> (source: <path/issue>)`。

## 1. 层定义

### A. PLATFORM / SYSTEM AUTHORITY
| 字段 | 内容 |
|---|---|
| SCOPE | runtime/OS/安全沙箱/工具契约/网络与凭据基础设施（WorkBuddy 系统提示、sandbox、MCP 契约、OS） |
| CAN_OVERRIDE | 无（不可被任何用户治理覆盖） |
| CAN_BE_OVERRIDDEN_BY | 无 |
| CONFLICT_BEHAVIOR | 平台约束即边界；治理只能在其内设计 |
| EXAMPLE | sandbox 写白名单、Agent 工具契约、MCP timeout 语义 |

### B. UNIVERSAL ORGANIZATION HARD INVARIANTS（普适硬不变量，薄）
| 字段 | 内容 |
|---|---|
| SCOPE | 跨所有仓必须成立的最小集：①凭据/secret 不进入产物②证据真实性（UNKNOWN != PASS、不伪造证据/新颖性）③评审独立性（当存在独立评审 gate 时 SELF_REVIEW ≠ 独立评审；不得自批自合并）④不得静默改写 reviewed/published 历史⑤机器私有数据不入共享治理产物 |
| CAN_OVERRIDE | A 层除外的一切 |
| CAN_BE_OVERRIDDEN_BY | 仅 A |
| CONFLICT_BEHAVIOR | 违反即错；repo 声明不得削弱；repo 只能加严或指定"由谁执行" |
| EXAMPLE | 任何仓都不允许把 UNKNOWN 报成 PASS；任何仓不允许提交 cookie |

### C. REPOSITORY-LOCAL PRODUCT AUTHORITY（仓库本地产品权威）
| 字段 | 内容 |
|---|---|
| SCOPE | 仓 RULES/AGENTS、Approved Specs、产品行为合同、仓库架构/所有权、仓 CI/merge 政策、ticket 授权与 scope |
| CAN_OVERRIDE | D、E、F 全部 |
| CAN_BE_OVERRIDDEN_BY | A、B（且仅当仓政策试图削弱 B 时无效） |
| CONFLICT_BEHAVIOR | 仓明确政策 > 全局默认；仓文本冲突内部 → STOP |
| EXAMPLE | 仓选择 squash-merge → 全局 ff-only 默认对该仓失效；仓 Approved Spec 的字段语义压倒全局通用启发式 |

### D. GLOBAL DEFAULT ENGINEERING WORKFLOW（全局默认工作流）
| 字段 | 内容 |
|---|---|
| SCOPE | seam-first 分解、风险分级评审、隔离 lane/worktree 默认、CodeGraph grounding、repair 饱和与预算默认、exact-SHA 评审协议、Stage 编组、novelty-first 报告 |
| CAN_OVERRIDE | E、F |
| CAN_BE_OVERRIDDEN_BY | A、B、C |
| CONFLICT_BEHAVIOR | 作为默认生效；被覆盖时记录 OVERRIDE；未被覆盖时按本仓 references 执行 |
| EXAMPLE | 默认 append-only repair commit；若仓政策定义等价审查协议则从仓 |

### E. METHODS / TOOLS（技能与工具）
| 字段 | 内容 |
|---|---|
| SCOPE | skills 的使用方法、MCP 操作细节、脚本 |
| CAN_OVERRIDE | F |
| CAN_BE_OVERRIDDEN_BY | A、B、C、D |
| CONFLICT_BEHAVIOR | 方法不产生权威；方法与 D/C 冲突时从 D/C |
| EXAMPLE | `/to-tickets` 的 frontier 提示不得违背 D 层 Stage 编组 |

### F. MEMORY / PREFERENCES（记忆与偏好）
| 字段 | 内容 |
|---|---|
| SCOPE | 用户偏好、环境事实、动态上下文、未升格的经验 |
| CAN_OVERRIDE | 无 |
| CAN_BE_OVERRIDDEN_BY | A–E 全部 |
| CONFLICT_BEHAVIOR | 永不压倒契约；仅提供背景与指针 |
| EXAMPLE | "外网走本地代理"属于环境事实 → 部署档案（machine-specific），不是规则 |

## 2. 与 V1 的差异（F1 修复）

| V1（错误） | V2（修正） |
|---|---|
| "项目级权威在其更严格处生效，但不得弱化本文件与 RULES"（全局全胜） | 只有 B 层薄集不可削弱；C 层显式政策可覆盖 D 层全部默认（含 ff-only、评审配比、merge 政策、CI 形态、worktree 用法、预算数值） |
| 未含平台/系统层 | 新增 A 层（最高） |
| 权威=静态优先序 | 权威=层 + 显式覆盖记录 + 冲突算法 |

## 3. 现有候选文件的去向（先映射，编辑在冻结后执行）

| 内容 | 现宿主 | 正确层 |
|---|---|---|
| 凭据安全 / 证据真实性 / 评审独立性 / 不静默改史 / 机器私有卫生 | RULES.md | B |
| exact-SHA 评审协议细节、CI 状态机、repair 预算、worktree 隔离、Stage、CodeGraph grounding | AGENTS/references | D（默认） |
| ff-only、merge 方法、squash/rebase 细则 | references/git-ci-integration | C-overrideable 的 D 默认 |
| macOS/gh 路径/代理端口 | RULES R12 / mcp README | A-adjacent 的部署档案（machine-specific 文档） |
| 文件 allowlist | RULES R3 V: | 语义 scope + expected surface（C 层仓可冻结例外） |
| 模型选择 | references | E+D（风险优先默认） |
