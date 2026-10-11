# H2 RUN REPORT — <RUN_ID>

> 同构模板（两臂同一生成路径）。填写纪律：如实记录实测事实；错误只加 `[fact-check]` 标注，
> 不改写；不得美化、不得为投稿式叙事增删。没有内容的节写 `NONE`。

## A. Receipt

```text
H2_RECEIPT = S1:<read|missing> S2:<LOW|MEDIUM|HIGH> S3:<targets|none> S4:<sha|MISMATCH>
```

## B. Outcome

```text
TASK_ID = <task-id>
TASK_COMPLETED = YES | NO | PARTIAL
WHAT_WAS_DONE = <≤10 行：内容导向 —— 改了什么 / 产出了什么>
```

## C. Artifacts produced

（每个产物：worktree 相对路径 + 一句话用途；关键产物给 sha256。）

- ...

## D. Findings（内容导向）

（只描述**任务对象**的缺陷/观察；每条附最小证据：文件+节号 / 命令 / 构造物。无则写 NONE。

1. ...
2. ...）

## E. High-value findings（自我分类，保守）

（引用 §D 编号；判据 = correctness/safety 缺陷、机械验收失效、false closure、
scope 违例、缺失必需产物。不确定标记 UNCERTAIN。无则写 NONE。）

## F. Verification performed

（确切命令 → 原始结果摘要（计数/OK/FAIL/未跑+原因）。环境故障写 ENV_BLOCKED + 现象。）

- ...

## G. Self-declared misses / uncertainties

- ...

## H. Telemetry（必填）

```text
FILES_FULLY_READ = [ ... ]
FILES_PARTIAL_READ = [ ... ]
FILES_GREPPED_FOUND = [ ... ]
ROUTES_USED = [ <route_id> -> <target> -> LOADED|MISSING|SKIPPED ... ]
SKILLS_LOADED = [ ... ]
SKILL_FALLBACK_REPORTED = YES | NO | NA
ESCALATED_LOADS = [ ... ]
WALL_CLOCK = NOT_OBSERVABLE
TOKEN_USAGE = NOT_OBSERVABLE
```

（与 `.h2-telemetry.log` 保持一致；若日志与本节冲突，以日志为准并在 §G 标注。）

## I. Stop conditions hit

- （无则写 NONE）
