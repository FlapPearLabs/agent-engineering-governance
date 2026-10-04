# 把治理框架带进你的项目

> 本页是采用导航与示例，不新增权威层、回执字段或部署授权。执行合同由 RULES、AGENTS、PORTABLE_SETUP 与对应 reference 拥有。

## 你会得到什么

Agent 先确认允许做什么，再按风险选择方法、验证、独立评审和集成；下一位 Agent 从仓库与远端证据接手。一个正常任务大致经历：**读权威与恢复状态 → 确认合同和风险 → 选择/读取 Skill 或 fallback → 实现与验证 → 适用评审和 CI → 集成、远端核验与状态写回**。

| 任务 | 最小合适路径 | 仍须保留的底线 |
|---|---|---|
| 普通文档、无生产影响的机械 LOW 修改 | 范围确认、相关机械检查；仓政策允许时 L0-only | 真实结果、scope、公开产物底线 |
| 修复生产行为的 MEDIUM 任务 | 合同、grounding、反例测试、静态/动态检查、独立评审、CI 与集成 | 当前候选的证据；自审不替代独立门 |
| 架构、并发、身份或高失效半径任务 | 按 AGENTS §3 升级评审 | 工具缺失时的证据不足不能伪装为通过 |

这张表帮助选择入口，完整风险政策仍读 AGENTS。可运行的演练见 [贯穿案例](adoption-walkthrough.md)。

## 最小准备

需要可读的治理副本、目标 Git 仓、获授权的任务，以及目标仓实际使用的工具。远程操作还需要对应访问权限。

- **Python 3** 用于本仓的薄校验器，不是所有目标项目的强制技术栈；本仓 CI 的具体版本与依赖由 requirements-dev 和 workflow 拥有。
- **Skills/MCP** 按任务触发和真实能力盘点；不要求使用者先安装全部 13 个 Skill 或全部 MCP。按其现有 fallback 执行，如实报告缺失和限制。
- **宿主 hook** 是可选部署工作。普通采用不需要改全局 MEMORY、系统设置或安装 adapter。

## 1. 固定治理来源

获取本仓并选择一个已接受的 commit/tag，在目标仓记录 URL 与完整 SHA。记录后的升级是显式变更，不把浮动 `main` 悄悄当成同一版本。

运行命令前，将 `GOVERNANCE_DIR` 设为准备保存治理副本的新目录，将 `TARGET_DIR` 设为已有目标仓根目录；两者不可混用。

```bash
git clone https://github.com/FlapPearLabs/agent-engineering-governance.git "$GOVERNANCE_DIR"
git -C "$GOVERNANCE_DIR" rev-parse HEAD
```

`GOVERNANCE_DIR` 是你选择的本地目录；不把真实宿主路径写进公开产物。离线使用可信副本时保留版本和未核验限制。

## 2. 在目标仓的已有权威中加一个指针

合并到已有 AGENTS/RULES，保留项目合同和宿主原有入口；不要覆盖完整 AGENTS，也不要盲目新建 CODEBUDDY.md 改变 runtime 的 guidance 选取。

```text
治理来源：FlapPearLabs/agent-engineering-governance @ <已接受完整 SHA>
采用范围：RULES 的通用底线，以及 AGENTS/references 的执行默认。
读取顺序：治理 README/RULES/AGENTS → 本仓 RULES/AGENTS/Approved Specs → 本票相关 reference。
组织政策：本仓保留自己的批准公开身份与署名；不采纳 FlapPearLabs 的组织策略。
项目合同与部署权限：以本仓已有权威为准；治理提示词不自行授予部署权限。
C-over-D 覆盖：<有则按 RULES R1 逐条记录；无则 NONE>。
```

占位符必须替换。`OVERRIDE` 只用于实际覆盖 D 层执行默认，不可用来豁免 B 层底线。本仓的 FlapPearLabs 身份约束与扫描器范围见 [组织策略](../deployment/organization-policy.md)；外部团队不应把自己的作者改成 FlapPearLabs。

## 3. 让 Agent 开工并核验回执

将 [README 完整提示词](../README.md#3-复制即用发给-agent-的引导提示词)与具体任务交给 Agent，按 [PORTABLE_SETUP](../deployment/PORTABLE_SETUP.md)执行。回执应指出实际读取的权威、版本、覆盖和能力缺口；不把示例回执直接复制成真实记录。

CodeGraph 不可用时读 [grounding §4](../references/codegraph-grounding.md#4-不可用降级skilltool_is_method_not_authority工具缺失不自动成为普适硬-gate)：MEDIUM 使用手工 manifest 与源码；HIGH 加强证据与评审，阻断由该规范的三个条件判断。Skill 缺失按 [获取指南](../skills/README.md)的 fallback，不谎称调用。

## 4. 初始化或恢复状态

目标仓固定入口为 `.agent/project-state.json`：新仓按 [连续性合同](../references/project-continuity-contract.md) bootstrap，旧仓 discover/index/point，保留已有 TARGET/SPEC/ADR/Issues。

使用 [原模板](../templates/project-state.json)填写实际指针与 snapshot；代码仓的 CodeGraph applicability 与 unavailable grounding 是不同问题，缺工具不能擅自改成 NOT_APPLICABLE。

```bash
python3 "$GOVERNANCE_DIR/scripts/validate_project_state.py" "$TARGET_DIR"
```

这证明索引结构符合该接口，不证明已批准目标、指针正文、远端已同步或恢复判断正确。Agent 仍核对它指向的权威和远端。

## 5. 跑完一张票，并让另一个 Agent 接手

按风险执行相关 references；Skill 使用或 fallback 后必须短报名称、目的、动作、结果、证据、限制。票级 Skill 校验的原命令与接口见 [路由 §1.4](../references/skills-and-model-routing.md#14-机械核验与独立判断)，不在本页另定义字段。

关闭前按 STATE_FLUSH 写事实所属位置，再更新索引、持久化并核验远端。另一位 fresh Agent 应能仅凭治理入口、目标仓与远端，从 STATE_RESTORE 得到下一合法动作。若仍需你补述只存在于聊天中的关键决定，采用尚未闭环。

## 哪些东西需要配置，哪些不用搬

| 面 | 采用方式 |
|---|---|
| 治理规范 | 固定来源与 SHA，引用原文；无需每仓复制全部 references |
| 产品合同/任务/CI/署名 | 留在目标仓已有权威，必要覆盖逐条留证 |
| 状态索引 | 按原 schema/template 初始化，指向实际材料 |
| Skills/MCP | registry 与配置健康盘点，按适用来源获取或 fallback |
| 全局 MEMORY / hooks | 独立部署范围，需明确授权及对应宿主验证 |
| 本仓公开扫描器 | 在治理仓检查该仓策略；不能原样当外部仓的通用署名校验器 |

## 复用与升级

本仓代码、文档、模板及演练材料按 [MIT](../LICENSE)提供。复制实质内容时保留版权与许可通知；组织名只是出处，不要求你的项目使用该署名。链接到的第三方项目和 Skill 仍遵守各自许可，不因本仓 MIT 获得额外授权。

升级治理版本时核对差异、目标仓覆盖与能力变化，重新取得适用证据。不自动改产品规范，不迁移全部历史，不自动部署 hooks。
