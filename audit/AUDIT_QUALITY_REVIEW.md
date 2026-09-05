# AUDIT_QUALITY_REVIEW — 对第一次治理审计的审计

> 基准：external reviewed HEAD `e5a4871`；外部评审：GPT-5.6 Sol（PR #1，CHANGES_REQUESTED，F1–F7）。
> 目的：找出首审从 **OBSERVATION 滑向 DESIGN CHOICE 而未标注边界** 的位置；区分 MECHANICALLY_PROVEN / DIRECTLY_SUPPORTED / STRONG_INFERENCE / WEAK_INFERENCE / PREMATURE_DESIGN_ASSUMPTION / INCORRECT。
> 方法：重读全部首审产物 + 重探真实环境（含新探针：CodeGraph `--help` 全量子命令、review-agent 契约、MEMORY 注入截断 byte offset、SKILL.md 元数据）。

## 0. 新证据（本次再审计新采集）

| # | 证据 | 采集方式 | 影响 |
|---|---|---|---|
| E-01 | MEMORY.md 注入截断点 = **byte 4028**（`grep -b` 实测；文件共 29,810B）→ 仅 ~13.5% 可见 | 本会话注入副本 + 本地 grep | 首审"~4K 截断"升级为精确机械事实；MEMORY 指针候选必须 ≤~3,500 字符 |
| E-02 | CodeGraph CLI 实际子命令：`init / index / sync / status / query / explore / node / files / callers / callees / impact / affected / daemon / unlock` | `codegraph --help` 全量输出 | `sync`（增量）、`impact`（爆炸半径）、`affected`、`status`（健康）**真实存在** → canonical+delta 有机制支撑，但 db 为**每目录**（`.codegraph/`），无跨 worktree 共享语义 |
| E-03 | `review-agent` 与 Pocock `code-review` 契约互补不重复（前者=只读缺陷列举 subagent 工具；后者=固定基点双向轴工程评审） | 两份 SKILL.md 对照 | 首审"评审 skill 重复冲突"判定降级为误报 |
| E-04 | 主链 skill 的 SKILL.md 均无 version/license/source 字段；无上游 commit 信息 | frontmatter 检查 + 目录清点 | skill manifest 可复现性 = **INCOMPLETE**（按评审要求显式标注并 block deployment） |
| E-05 | Codex code-review 配额耗尽 bot comment 于 PR #1 | PR 评论 | 自动化评审不可用分类（UNAVAILABLE ≠ PENDING）在治理语境再次出现 |
| E-06 | zhihu 主仓无 `.codegraph/`、仅 `wt-p1-t09` 有 | 首审已测，本次复核 | 首审解释"worktree 各持陈旧库"证据不足：主仓从未 init 的可能性未排除 → AS_IS_V2 标 UNKNOWN |

## 1. 逐项分类（首审主要结论）

> 字段：CLAIM / 原证据 / 强度 / 缺失证据 / 矛盾证据 / 现判定 / 行动。VERDICT ∈ MP=MECHANICALLY_PROVEN, DS=DIRECTLY_SUPPORTED, SI=STRONG_INFERENCE, WI=WEAK_INFERENCE, PDA=PREMATURE_DESIGN_ASSUMPTION, INC=INCORRECT。

| # | CLAIM（首审） | 原证据 | 强度 | 缺失 | 矛盾 | VERDICT | ACTION |
|---|---|---|---|---|---|---|---|
| C01 | MEMORY 注入 ~4K 截断，OVERRIDE 在截断区 | 本会话注入副本中途断句 + 文件 29,810B | WI→**MP**（现测 byte 4028） | — | — | **MP** | 保留；指针候选限 ≤3,500 字符 |
| C02 | 全局无 AGENTS.md/RULES.md/CLAUDE.md | `ls -d` 全 miss | **MP** | — | — | **MP** | 保留 |
| C03 | 项目 AGENTS/RULES 不被 WorkBuddy 自动注入 | 无任何注入证据 | **DS**（缺证类主张，正向自动加载主张应为 UNKNOWN） | 未测新会话正向行为 | — | **DS**（自动加载=UNKNOWN） | AS_IS_V2 显式标 UNKNOWN |
| C04 | 全局注入优先序（system>memory>identity>…） | 本会话组合观测 | SI | 无文档化裁决规则 | — | **SI** | AUTHORITY_MAP_V2 以冲突算法替代"顺序" |
| C05 | 项目内权威链 RULES>Specs>AGENTS>runtime memory | zhihu AGENTS §1 原文 | **MP**（文本在） | — | — | **DS→MP** | 保留为 C 层证据 |
| C06 | README 部署节"指针+安装清单"足以让新会话看到治理 | 设计意图 | **PDA** | 无机制证明（F2） | F2 | **INC（部署充分性）** | deployment/BOOTSTRAP_CONTRACT + 指针候选 + 校验脚本 |
| C07 | Execution Stage 概念必要 | `/to-tickets` start-all 语义 + 搬运痛点 | SI（痛点实、Stage 为设计） | — | S15：无 DAG 项目不适配 | **SI + 边界未标注 = PDA 成分** | 保留为默认机制；无 DAG 优雅降级；显式标注设计边界 |
| C08 | `/to-tickets` frontier=就绪即全开 | skill 原文 "Work the frontier" | **MP** | — | — | **MP** | 保留（C08 支撑 C07） |
| C09 | `/to-tickets` prefactor 架构漂移风险 | skill 原文条款 | **DS** | — | — | **DS** | 保留 seam-first 约束壳 |
| C10 | seam-first 原则（DAG 非架构权威） | 痛点史 + zhihu AGENTS §18.3 | **DS** | — | — | **DS** | 保留；具体 lint 设计=设计选择（已标注） |
| C11 | CodeGraph canonical+delta 可行 | 仅 MEMORY 愿景句 | **WI**（首审未验证工具） | 未查 CLI | E-02 现已证实 sync/impact/status 存在 | 首审 WI → **现在机制可行（MP for capability）** | 重写 reference 至真实 CLI 语义（F5） |
| C12 | worktree 图库碎片化/陈旧 | wt 有 .codegraph、主仓无 | **MP**（碎片化事实） | 陈旧性/创建时间未证（E-06） | "主仓从未 init" 同样成立 | **MP（碎片）/ UNKNOWN（陈旧度）** | AS_IS_V2 拆分陈述 |
| C13 | 风险四级 LOW/MED/HIGH/CRITICAL | 设计选择 | **PDA** | 无推导 | CRITICAL=HIGH+升级触发，可合并 | **PDA** | 改 3 级 + ESCALATION 触发清单 |
| C14 | L0/L1/L2 评审分层 | 设计（源自首审 prompt §13 + 痛点） | SI | — | **F3：LOW 行三处互相矛盾（INC）** | SI + LOW 行 **INC** | 统一为：非生产 LOW 可 L0-only（repo 政策允许时）；生产 LOW 需 L1；MEDIUM+ 必须 L1 |
| C15 | budget=2 为全局硬数字 | 实践惯例 | **PDA**（硬数字未论证） | T09 类案例细节未归档 | — | **PDA** | 降为 DEFAULT（project-overridable）；普适部分="高价值 blocker 永不豁免" |
| C16 | exact-SHA PASS 绑定（生产代码） | 项目 RULES §8 + git 史 | **MP**（实践文本） | — | — | **DS→保留为普适**（生产代码评审完整性） | 保留 RULES，措辞限定"reviewed/published 历史" |
| C17 | ff-only 全局硬规则 | 项目本地政策 | **PDA→INC**（F4：仓库合并政策被全局化） | — | squash-merge 仓被非法化 | **INC** | 降级 reference 默认；RULES 只留"不得静默改写 reviewed/published 历史" |
| C18 | reset --hard / clean -fd 全局禁止 | 项目 RULES §8 | **PDA→INC**（F4：对可弃 worktree 过宽） | — | — | **INC** | 移回 reference（含项目 §8.1 无损恢复流程作参考） |
| C19 | changed_files ⊆ 授权清单为 scope 校验 | 设计 | **PDA→INC**（F6：僵化） | — | 支撑文件/测试常合法涌现 | **INC** | 语义 scope + expected surface + 意外文件需正当化 |
| C20 | macOS 全局硬基线（R12） | 本机事实 | **PDA→INC**（F7） | — | 跨平台目标仓被非法化 | **INC** | 降为 deployment profile；RULES 只留"不得注入无关平台 shell 要求" |
| C21 | 活跃面 Windows 残留为零 | 三处 grep 零命中 | **MP** | git 历史未查（超出范围） | — | **MP（活跃面）** | 保留 |
| C22 | code-review 与 review-agent 重复冲突 | 仅凭名字 | **WI→误报**（E-03 互补） | 未读 review-agent 契约 | E-03 | **INC（重复判定）** | skills manifest 修正为互补路由 |
| C23 | 模型名单不可核验/无文件级路由 | settings.json 无模型字段 | **MP** | — | — | **DS** | 保留；路由表按档位+核验义务 |
| C24 | auto-advance 缺失造成搬运负担 | 用户痛点 + zhihu 连续模式已实现 | SI | — | — | **SI** | 保留为默认 |
| C25 | 治理变更双评审 | zhihu AGENTS §5 实践 | **DS**（项目实践） | 全局推广未论证 | — | **DS，GLOBAL_DEFAULT** | 保留但标注默认属性 |
| C26 | 单分支单活跃写者为硬规则 | zhihu AGENTS §8.1 | **DS**（项目实践） | — | 并行写场景属仓政策 | **DS，DEFAULT**（硬核=同一 reviewed candidate 不得并发变异） | 降级为默认 |
| C27 | 场景校验 10/10 PASS | 首审自评 | **WI（自评过宽）** | S1 与 F3 矛盾 | F3/F4/F7 场景全未覆盖 | **INC（覆盖不足）** | TARGET_ARCHITECTURE_CHALLENGE 15 场景重做 |
| C28 | 文件/行数/版本等清单事实 | ls/wc/--version | **MP** | — | — | **MP** | 直接进 AS_IS_V2 |

## 2. OBSERVATION → DESIGN 边界（首审未标注处，现补标）

| 首审把以下"设计选择"写成了"结论" | 真实状态 |
|---|---|
| Execution Stage 编组机制 | 设计选择（痛点 SI 支撑必要性，机制本身无先例约束） |
| LOW/MEDIUM/HIGH/CRITICAL 四级 | 设计选择（已挑战并简化为三级+升级触发） |
| budget=2 硬数字 | 设计默认（实践中未归档 T09 类收敛案例细节） |
| ff-only / reset 禁令 / macOS / 文件 allowlist 为 RULES | 设计越权（仓库政策/部署事实被全局化 = F4/F6/F7） |
| canonical graph + delta 的具体形态 | 设计（工具能力现已证实存在，但具体宿主=主仓 db 的选择需按目录级 db 现实重写） |
| README 部署节充分性 | 设计臆断（F2：无新会话可见性证明） |

## 3. 结论汇总

- **PREMATURE_CONCLUSIONS** = C06, C07(机制部分), C13, C15, C17, C18, C19, C20, C25(全局属性), C26(硬规则属性), C27
- **INCORRECT_CONCLUSIONS** = C06(部署充分性), C14(LOW 行), C17, C18, C19, C20, C22, C27
- **STILL_VALID_HIGH_VALUE** = C01(截断,现精确), C02, C05, C08, C09, C10, C12(碎片事实), C16, C21, C23, C24
- **首审总体判定**：观察层（WHAT EXISTS）大体扎实；设计层（WHAT SHOULD BE）存在系统性的"项目政策/部署事实全局化"与"自评过宽"。与 GPT-5.6 Sol F1–F7 完全对齐。
