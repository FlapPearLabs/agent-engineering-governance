# MEMORY_POINTER_CANDIDATE — ~/.workbuddy/MEMORY.md 替换候选（未部署）

> 部署前置：外部 fresh 评审 APPROVE + skills manifest 补齐 + product owner 授权（见 BOOTSTRAP_CONTRACT §2.1）。
> 硬约束：全文 ≤3,500 字符（实测注入截断点 byte 4028）。旧 MEMORY 29,810B 全部语义已迁移至治理仓 canonical 文件；部署时旧文归档不删除。
> 下方代码块内 = 候选正文原文。

```markdown
# GLOBAL MEMORY — 指针层（治理正文在 FlapPearLabs/agent-engineering-governance）

> 本文件是治理指针 + 最低不变量；工程治理 canonical = GitHub repo
> FlapPearLabs/agent-engineering-governance（分支 main；候选经 PR 评审）。
> 工程会话开工前执行 BOOTSTRAP_CHECKLIST（见该仓 deployment/BOOTSTRAP_CONTRACT.md）：
> 读 AGENTS.md+RULES.md+相关 references → 发现仓内 AGENTS/RULES/Specs → 应用六层权威
> （A 平台 > B 不变量 > C 仓权威 > D 全局默认 > E 方法 > F 记忆）→ 输出引导回执。

## B 层不变量摘要（任何仓不可削弱；全文见治理仓 RULES.md）
1. 凭据/secret 绝不进入 repo/log/产物/记忆。
2. 证据真实性：UNKNOWN != PASS；不伪造证据/新颖性；自分类仅提案。
3. 独立评审 gate 存在时，self-review 不满足之；不自批不自合并。
4. reviewed/published 历史不被静默改写；修复 = append-only commit。

## 环境事实（machine-specific，非规则）
- 外网走本地代理 http://127.0.0.1:<port>（git push/gh/npm 依赖，显式 env 注入）。
- gh CLI: /opt/homebrew/bin/gh（不在 agent sandbox PATH，用绝对路径；已认证 FlapPearLabs）。
- CodeGraph: ~/.local/bin/codegraph serve --mcp（MCP 已配）；CLI 含 sync/impact/affected。
- 模型路由按 RISK FIRST：LOW→lite 档；MEDIUM→default；长文→大上下文；ESCALATION→最强可用（外部 Sol 级人工搬运）。

## 偏好
- 中文交流；结构化交付（PHASE/STEP、blocker/non-blocking、显式 VERDICT）。
- 执行前显式授权；USER_DECISION_REQUIRED 即 STOP；freshness check 先行。
- 禁 amend/squash/rebase 已评审历史；AUTHOR_NAME=FlapPearLabs、AUTHOR_EMAIL_CLASS=GITHUB_NOREPLY。
```
