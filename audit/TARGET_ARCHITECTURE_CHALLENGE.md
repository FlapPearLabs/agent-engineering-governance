# TARGET_ARCHITECTURE_CHALLENGE — 候选架构 15 场景对抗校验

> 对象 = 首审候选（@ e5a4871）+ 本轮修复方向。每场景：EXPECTED / CURRENT_CANDIDATE / CONFLICT / 过度治理风险 / 欠治理风险 / REQUIRED_CHANGE。
> 结论：场景 1/2/4/5/6/10/12/13/15 在首审候选下存在 CONFLICT，全部对应 F1–F7 修复；场景 14 暴露 Stage 编组需显式的 owner 冲突规则。
> TARGET_ARCHITECTURE_CHALLENGED = YES。

## 1. 全新中立仓（无项目 AGENTS/RULES）
- EXPECTED：bootstrap 让新会话看到治理指针 → 读 canonical 治理 → 以全局默认工作（B 层 + D 层默认）。
- CURRENT_CANDIDATE：README 声称"指针+清单"即可，无机制证明 → 新会话可能什么都看不到（F2）。
- CONFLICT：YES（可见性无保障）。OVER：无。UNDER：YES（完全裸奔）。
- REQUIRED_CHANGE：deployment/BOOTSTRAP_CONTRACT.md + MEMORY 指针候选（≤3.5K）+ bootstrap 校验；显式声明"自动加载项目 AGENTS=UNKNOWN，靠契约步骤补足"。

## 2. 仓明确 squash-merge 政策
- EXPECTED：仓政策（C 层）覆盖全局默认（D 层），记录 OVERRIDE；reviewed 候选分支仍禁静默改写。
- CURRENT_CANDIDATE：RULES R4 全局禁 squash/merge commit → 仓政策被非法化（F4）。
- CONFLICT：YES。OVER：YES。UNDER：无。
- REQUIRED_CHANGE：R4 收窄为"不得静默改写 reviewed/published 历史"；merge 方法归仓/reference 默认。

## 3. 仓有更严评审政策（如强制双人 + 外部终审）
- EXPECTED：C 层加严直接生效，全局默认不阻挡。
- CURRENT_CANDIDATE：允许（"更严格生效"），但 R1 措辞"不得弱化全局"可能被读成"加严也要服从全局形式"。
- CONFLICT：部分（语义模糊）。OVER：低。UNDER：无。
- REQUIRED_CHANGE：R1/AGENTS 冲突算法明确"加严永远合法，覆盖 D 层默认永远合法（记录即可）"。

## 4. 仓有意采用较弱但明确的 CI 政策（无 PR CI 基础设施）
- EXPECTED：仓政策定义等价验证形态（本地确定性套件 + 远端核验）→ 合法覆盖"REAL_PR_CI"默认；但 UNKNOWN≠PASS、自分类禁令（B 层）不豁免。
- CURRENT_CANDIDATE：全局要求 real CI，无 CI 设施的仓被卡死（F4 同族）。
- CONFLICT：YES。OVER：YES。UNDER：无（诚实性底线仍在）。
- REQUIRED_CHANGE：CI 要求移为 D 层默认；仓可定义等价证据形态；B 层诚实性（UNKNOWN≠PASS/自分类禁止）不可豁免。

## 5. docs-only 平凡票
- EXPECTED：L0 机器核验 + 自审即可闭合（仓政策允许时）；不进 T09 链。
- CURRENT_CANDIDATE：AGENTS LOW 行 "L0+L1 或机器核验" vs reference "LOW 抽样 L1" vs RULES R6 "每个 PASS 必须有独立评审者身份" 三者矛盾（F3）→ 严格执行 R6 则 docs 票被迫找独立评审。
- CONFLICT：YES。OVER：YES。UNDER：无。
- REQUIRED_CHANGE：统一 = 非生产/机械 LOW 可 L0-only（仓政策允许时）；生产代码 LOW 需 L1；MEDIUM+ 必须 L1；R6 改为"当 gate 存在时自审不满足之"。

## 6. 微型生产修复（1 行修复 + 回归）
- EXPECTED：生产代码 → 独立 L1 不可豁免（B 层），但 grounding/合同抽取按最小面裁剪；不强制全套 Stage 仪式。
- CURRENT_CANDIDATE：LOW 行矛盾同上；且 R3 allowlist 校验可能把补测试文件判为违规（F6 交叉）。
- CONFLICT：YES（同 F3/F6）。OVER：中。UNDER：无。
- REQUIRED_CHANGE：LOW 生产票 = L1 必须 + 最小 grounding；scope 语义化。

## 7. 高风险持久化变更
- EXPECTED：强反例 + 独立评审 + 升级触发（外部/终审按触发清单）；预算耗尽走 Arbiter。
- CURRENT_CANDIDATE：基本满足；但四级风险模型冗余（CRITICAL≈HIGH+触发）。
- CONFLICT：无实质。OVER：轻微（层级冗余）。UNDER：无。
- REQUIRED_CHANGE：三级 LOW/MEDIUM/HIGH + 显式 ESCALATION 触发清单。

## 8. 实现中发现架构冲突
- EXPECTED：STOP: CONTRACT_CONFLICT → owner 裁决；不静默重设计。
- CURRENT_CANDIDATE：满足（R14/STOP 枚举）。
- CONFLICT：无。OVER：无。UNDER：无。
- REQUIRED_CHANGE：无（保留为 B/D 语义）。

## 9. 已有健康 CodeGraph
- EXPECTED：lane 用 `sync` 增量/查 daemon；记录 base；无重建仪式。
- CURRENT_CANDIDATE：方向正确，但 ticket-lane.md 写"每 worktree 独立图状态"与 codegraph-grounding.md 的 canonical 主张矛盾（F5）。
- CONFLICT：YES（文本级）。OVER：无。UNDER：无。
- REQUIRED_CHANGE：统一为"独立查询/证据生命周期 ≠ 独立库所有权"；按真实 CLI（每目录 .codegraph + sync + status）重写。

## 10. CodeGraph 不可用（未安装/损坏）
- EXPECTED：grounding 默认降级（手工 surface manifest + 重点文件阅读），记录 `CODEGRAPH = UNAVAILABLE`；不伪造接地证据。
- CURRENT_CANDIDATE：MEDIUM+ 强制 grounding，无降级路径 → 卡死。
- CONFLICT：YES。OVER：YES。UNDER：无。
- REQUIRED_CHANGE：grounding = 风险分级默认 + 显式降级与如实标注。

## 11. 两轮修复后评审只剩合成长尾态
- EXPECTED：budget 耗尽 → Arbiter 五选一；合成态 → BACKLOG；无自动 R3+。
- CURRENT_CANDIDATE：满足（budget 硬数字 2 的"硬"程度被质疑，但行为正确）。
- CONFLICT：无实质。OVER：数值硬性轻微。UNDER：无。
- REQUIRED_CHANGE：budget=DEFAULT（仓/owner 可覆盖）；"高价值 blocker 永不豁免"保留硬性。

## 12. 票据实施中需要新增支撑测试/helper 文件
- EXPECTED：语义 scope 内合法；评审核正当性；不判 scope violation。
- CURRENT_CANDIDATE：R3 "changed files ⊆ 授权清单" + L0 子集校验 → 自动判违规（F6）。
- CONFLICT：YES。OVER：YES（把 seam-first 变回僵化计划）。UNDER：无。
- REQUIRED_CHANGE：语义 scope + expected surface；意外文件需 justification/review；仅当票明确冻结 allowlist 时子集校验。

## 13. Windows 为目标的仓（宿主 macOS）
- EXPECTED：完全合法；平台档案只描述宿主事实；不得把宿主 shell 需求注入仓。
- CURRENT_CANDIDATE：RULES R12 "当前全局基线 = macOS" 为组织级硬规则（F7）。
- CONFLICT：YES。OVER：YES。UNDER：无。
- REQUIRED_CHANGE：R12 → "不得注入无关平台特定 shell 要求"（B 邻域）；macOS 事实移 deployment profile。

## 14. 多个就绪票共享同一 owner
- EXPECTED：Stage 编组判 owner 冲突 → 合并为一票或排为串行集成链；不 START_ALL。
- CURRENT_CANDIDATE：Stage 输入清单含 WRITE OWNERSHIP 但未定义"命中后怎么办"。
- CONFLICT：部分（规则缺口）。OVER：无。UNDER：中（可能并行后互相 invalidate）。
- REQUIRED_CHANGE：execution-stage.md 增补 owner 冲突处置：合一票 / 串行 / 拆 owner（架构授权）。

## 15. 独立项目根本没有 DAG（无分解工具/单票项目）
- EXPECTED：Stage/Lane 机制优雅退化：Stage = 风险+内聚选出的单票或票集合；不要求 DAG 工具存在。
- CURRENT_CANDIDATE：Stage 语义隐含依赖 frontier/DAG 概念。
- CONFLICT：部分。OVER：低。UNDER：无。
- REQUIRED_CHANGE：execution-stage.md 增补"无 DAG 退化路径"。

## 汇总

| 场景 | 冲突 | 映射修复 |
|---|---|---|
| 1 | YES | F2 |
| 2 | YES | F4 |
| 3 | 部分 | F1（冲突算法措辞） |
| 4 | YES | F4/F1 |
| 5 | YES | F3 |
| 6 | YES | F3/F6 |
| 7 | 无实质 | 风险模型简化 |
| 8 | 无 | — |
| 9 | YES | F5 |
| 10 | YES | F5/F1（降级路径） |
| 11 | 无实质 | budget 降默认 |
| 12 | YES | F6 |
| 13 | YES | F7 |
| 14 | 部分 | Stage owner 处置增补 |
| 15 | 部分 | Stage 退化路径增补 |
