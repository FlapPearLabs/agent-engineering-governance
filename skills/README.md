# Skills Governance

## 政策

1. **不 vendor 第三方 skill 内容**。本目录只维护治理元数据（来源、版本、期望能力、路由、兼容性）。只有当许可与所有权明确允许时才收录实际内容。
2. **SKILL_IS_EXECUTION_METHOD / SKILL_IS_NOT_AUTHORITY**：skill 教方法，不授权威；路由唯一权威 = `references/skills-and-model-routing.md` §1。
3. skill 使用声明必须可核验：被实际调用/读取的证据，否则报 `UNVERIFIED`。
4. 新装 skill 进入主链前必须先入路由表；未列入路由表的同职责 skill 不得进入工程主链。

## Manifest 条目格式

```
name / source(repo+path or URL) / version_or_commit / expected_capability /
routing_rule(见 references) / compatibility(runtime) / license_note
```

## 当前清单快照（2026-09-05 实测）

- 用户级 skill 总数：196（`~/.workbuddy/skills/`）；WorkBuddy 内置插件 skill：24。
- Matt Pocock 工程技能族（第三方，source：开源 skills 仓库，commit 级版本待补录）：`grill-with-docs`、`to-spec`、`to-tickets`、`implement`、`tdd`、`code-review`、`diagnosing-bugs`、`resolving-merge-conflicts`、`writing-plans`、`setup-matt-pocock-skills`、`subagent-driven-development`、`simplify-code`。
  - license_note：待核验上游 LICENSE 后在此登记；核验前不复制其内容进本仓。
- 用户自建：`codegraph-integration`（Hermes 导向）、其他领域 skill（写作/内容/工具类，不属于工程主链）。
- 已知重复族（路由表已裁决首选）：`code-review` vs `review-agent`；`diagnosing-bugs` vs `diagnose`；`grill-with-docs` vs `grilling`/`grill-me`/`batch-grill-me`。
- TODO（NEXT）：为全部工程主链 skill 补 commit 级 manifest；为第三方 skill 建立 update 策略（升级前 diff 行为变化）。

## 更新流程

安装/升级/替换工程主链 skill → 提交本目录 manifest 变更 PR → 按治理变更评审（双评审）。
