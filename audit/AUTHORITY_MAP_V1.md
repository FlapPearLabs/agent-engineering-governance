# AUTHORITY_MAP_V1 — 权威分层与唯一归属

## 1. 目标分层（自上而下裁决）

```
1. HARD RULES                    RULES.md（治理仓）        不可违反约束；违反即 STOP
2. EXECUTION ARCHITECTURE        AGENTS.md（治理仓）        角色模型/Stage/Lane/评审/收敛/CI/推进
3. DETAILED REFERENCES           references/*.md            机制细节；与 1/2 冲突时以 1/2 为准
4. SKILLS / MCP EXECUTION        skills/ + mcp/（治理仓）    执行方法与工具；不产生权威
5. MEMORY POINTERS + 偏好        ~/.workbuddy/MEMORY.md     ≤4KB：用户偏好、环境事实、当前例外、指向 1-3 的指针
6. PROJECT-LOCAL AUTHORITY       各仓 AGENTS/RULES/Specs    项目合同与 delta；不得弱化 1-3
7. RUNTIME / CONVERSATION        .workbuddy/memory/、聊天    non-authoritative，永不覆盖 1-6
```

裁决原则：上层覆盖下层；同层冲突 → STOP: CONTRACT_CONFLICT（不可静默择便）。项目权威在**更强**处生效（更严格的项目约束有效），不得**弱化**全局硬规则。

## 2. 主题 → 唯一 canonical owner

| 主题 | CANONICAL OWNER | 其他出现位置的处理 |
|---|---|---|
| 凭据/secret 红线 | RULES.md R2 | 项目 RULES 可加严（如 zhihu cookie 条款），不得放宽 |
| exact-SHA 绑定 | RULES.md R5 | 项目 AGENTS 中的重述逐步删除，改引用 |
| SELF_REVIEW != INDEPENDENT_REVIEW | RULES.md R6 | 同上 |
| CI 状态语义/分类权威 | RULES.md R7 + REF:git-ci-integration | MEMORY 报告 override 段迁移后删除 |
| fail-closed + 不过度拒绝 | RULES.md R9 | — |
| 角色/控制面边界 | AGENTS.md §Roles | MEMORY Override §1-§12 迁移后删除 |
| Execution Stage | AGENTS.md §Stage + REF:execution-stage | 新增 |
| Ticket Lane 生命周期/风险矩阵 | AGENTS.md §Lane + REF:ticket-lane | MEMORY Lane V2 主体迁移 |
| seam-first / DAG 语义 | AGENTS.md §Seam-first | 新增成文 |
| CodeGraph 机制 | REF:codegraph-grounding | MEMORY 段迁移；绝对路径改 `${HOME}` |
| 评审分级/REPAIR_VALUE/Arbiter/饱和 | AGENTS §Review/Convergence + REF:review-and-repair-saturation | MEMORY 两大 override 迁移 |
| 报告格式（novelty-first） | REF:review-and-repair-saturation | MEMORY 报告 override 迁移 |
| git 红线/署名/代理约定 | RULES.md R4 + REF:git-ci-integration | MEMORY 段迁移 |
| skill 路由与边界 | REF:skills-and-model-routing + skills/README | 新增 |
| 模型路由 | REF:skills-and-model-routing | MEMORY 名单迁移并改为档位映射 |
| auto-advance / STOP 枚举 | AGENTS.md §Auto-advance | 新增全局版（项目七类 STOP 是其子集） |
| 项目产品合同（captured!=verified 等） | 各项目 Spec/RULES | 全局只留抽象原则（SUCCESSFUL_PRODUCTION != VERIFIED） |
| 用户个人偏好/沟通语言/交互习惯 | MEMORY.md（KEEP_IN_MEMORY 区） | — |
| 机器特定事实（路径/代理端口/gh PATH） | 治理仓 mcp/README MACHINE_SPECIFIC + MEMORY 环境区 | 不进 AGENTS/RULES |

## 3. 现有 MEMORY.md 内容逐段再分类

| MEMORY.md 段落（行号） | 分类 | 去向 |
|---|---|---|
| 头部三条 OVERRIDE 指针（L1-11） | DUPLICATE | 迁移后删除（指向的内容本身入 AGENTS/REF） |
| TICKET LANE V2 主体（L13-70） | MOVE_TO_AGENTS + MOVE_TO_REFERENCE | 流程骨架→AGENTS；合同字段/反例类目→REF:ticket-lane |
| CodeGraph grounding（L26-30） | MOVE_TO_REFERENCE（+STALE 路径剥离） | REF:codegraph-grounding；绝对路径→`${HOME}` |
| ORCHESTRATOR/WORKER/REVIEW AUTHORITY Override（L73-136） | MOVE_TO_AGENTS | AGENTS §Roles/Lane/Review；去重复 |
| REPORTING OVERRIDE（L140-283） | MOVE_TO_REFERENCE | REF:review-and-repair-saturation（报告模板节） |
| REPAIR SATURATION OVERRIDE（L287-319） | MOVE_TO_AGENTS（原则）+ MOVE_TO_REFERENCE（字段表） | AGENTS 收敛节 + REF 详表 |
| （当前 MEMORY 缺失的）用户偏好/环境事实区 | KEEP_IN_MEMORY | 迁移后新 MEMORY 主体 |
| （当前 MEMORY 缺失的）治理指针区 | 新增 | 指向治理仓 + 部署状态 |

STALE/DUPLICATE 净结论：无独立 STALE 段（Windows 残留为 0）；DUPLICATE 主要是三大 Override 与项目 AGENTS.md 的双写。

## 4. 反目标（防过度治理）

- AGENTS.md 不复制 references 全文，只留骨架 + 指针（目标 <300 行）。
- RULES.md 只写"违反即错"的条款（目标 <150 行），不写 how。
- references 每篇单一主题；跨篇引用用链接，不复制段落。
- 一个主题一个 owner：本文件 §2 是唯一分配表；迁移评审（PR review）应把"同一规则出现在两个 owner 文件"视为缺陷。
