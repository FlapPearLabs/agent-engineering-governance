# FlapPearLabs 组织策略：适用范围与公开署名

> 本页拥有本治理仓的组织身份政策（C 层），不新增普适不变量、配置 schema 或通用身份管理机制。RULES R2 继续拥有凭据、本机私有身份与公开产物底线。

## 适用范围

- 本仓 `FlapPearLabs/agent-engineering-governance` 明确采纳本策略。
- 其他工程仓只有在目标仓权威明确采纳本策略时才适用；组织名相似、引用框架或使用同一种 Agent 都不构成自动采纳。
- 外部团队采用治理框架时，保留自己的公开身份、署名与协作政策，不冒用 FlapPearLabs。本策略的适用范围是 C 层政策选择，不是以 C 层覆盖 B 层凭据保护。

## 本仓的既有身份约束（原 F4，行为保留）

PUBLIC 仓库对外暴露单一 intentional 公开身份：

```text
PUBLIC_PROJECT_IDENTITY = FlapPearLabs
AUTHOR_NAME = FlapPearLabs
AUTHOR_EMAIL_CLASS = GITHUB_NOREPLY
```

约束同时适用于文件内容与 HEAD 提交的 author/committer 的 name 和 email。规范 noreply 形态为 `(<uid>+)?FlapPearLabs@users.noreply.github.com`；名称正确而邮箱指向其他账号 handle 仍不满足。GitHub 合并机器人等既有例外的机械判定以本仓扫描器和回归为准，本次不改变它们。

只在获授权的目标仓应用署名。独立 worktree 共享 Git 配置时，使用单次命令的 `git -c user.name=... -c user.email=... commit` 或明确的 worktree 配置；不为本票改共享 repo-local/global 配置。

## 工具范围

`scripts/validate_public_release.py` 的 `PUBLIC_PROJECT_IDENTITY` 与 `scripts/validate_governance.py` 的 HEAD 身份门是**本治理仓策略的参考实现**，仍固定为 FlapPearLabs。本次不增加配置参数，也不改变扫描、CI 或 hooks 的拒绝行为。

在本治理仓运行这些命令可检查治理副本；不要把它们原样作为外部项目的通用署名门。外部项目执行自己的公开身份/产物政策。`validate_project_state.py <target-repo>` 与票级证据校验器则按各自接口检查目标项目的声明，不要求目标项目改署名。

## 其他组织采用时

在目标仓已有 AGENTS/RULES 中说明采用的治理版本、公开身份政策和必要的 C-over-D 覆盖即可；示例见 [采用指南](../docs/adoption.md)。不新增第二套组织目录、全局注册表或常驻服务。没有明确署名政策时，先发现既有仓配置与权威；不能自行将个人或组织身份替换成 FlapPearLabs。
