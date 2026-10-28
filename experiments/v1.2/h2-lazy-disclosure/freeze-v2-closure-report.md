# H2-R2 — CLOSURE REPORT

## 结论摘要

- 结果：`INSUFFICIENT_EVIDENCE`；decided_by：`COVERAGE:INVALID:h2r2-f03-c`。
- 仅 5/10 个任务有有效配对：f01, f02, f06, f07, f10。
- INVALID：h2r2-f03-c (OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN; <HOME>/.workbuddy/binaries/python/versions/3.13.12/lib/python3.13/unittest/loader.py); h2r2-f03-v (OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN x2; /nope); h2r2-f04-v (OUT_OF_RUN_ACCESS:TOOL_NOT_ALLOWED; execute); h2r2-f05-c (OUT_OF_RUN_ACCESS:TOOL_NOT_ALLOWED; execute); h2r2-f09-c (OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN; ..)。这 5 个 run 的机械验收均为 ACCEPT，都是被 access audit 判为 INVALID 的。
- BLOCKED：h2r2-f08-c (AUDIT_BLOCKED:PROVIDER_UNREACHABLE:EXIT:1; AUDIT_BLOCKED:PROVIDER_UNREACHABLE:PROVIDER_ERROR:provider.no-route; AUDIT_BLOCKED:PROVIDER_UNREACHABLE:NO_ANSWER)。

| 配对 | control FINAL_CORRECTNESS | control findings (severity, category) | variant FINAL_CORRECTNESS | variant findings (severity, category) |
|---|---|---|---|---|
| f01 | PARTIAL | (P2, HV4), (P3, HV1) | PARTIAL | (P2, HV1), (P3, HV1) |
| f02 | PASS | (P3, HV4), (P3, HV4) | PASS | — |
| f06 | PASS | (P2, None), (P2, None) | PASS | (P3, None) |
| f07 | PARTIAL | (P2, HV1), (P2, HV4), (P3, HV4) | PARTIAL | (P2, None), (P3, HV7) |
| f10 | PARTIAL | (P2, HV4), (P3, HV1), (P3, HV6) | PARTIAL | (P2, HV4), (P2, HV5) |

有效配对的结构化比较（共 5 对）：
- FINAL_CORRECTNESS 相同：5/5 对。
- invalid-completion 状态相同：5/5 对。
- finding (severity, category) 多重集相同：0/5 对（不同：f01, f02, f06, f07, f10）。
- 因此预注册的 null-difference 条件只对 0/5 个有效配对成立（没有任何配对三项均相同），对全部有效配对并不成立，null 差异规则不适用。
- 完整配对中未观察到 S2/S3/S4 代价。
- 结果 `INSUFFICIENT_EVIDENCE` 的判定依据是 `COVERAGE:INVALID:h2r2-f03-c`，不是 null difference。

## 问题与预注册设计

精简渐进披露是否保留任务表现？十个冻结任务各以 control 和 variant 执行一次。
详见 [protocol-v2.md](freeze-v2/protocol-v2.md)。

## 预注册偏离与决定

- 十个 frozen-oracle repair 任务替换原任务集；覆盖要求十个有效配对。（来源：[协议 §7](freeze-v2/protocol-v2.md)）
- 仓外 AGENTS 交付、wrapper-relative 遥测及冻结 runtime/profile/model；carrier 缩减以 JS 字符计。（来源：[协议 §7](freeze-v2/protocol-v2.md)）
- 准入、任务、oracle、scope、平衡顺序和验收按注册表与计划；无效及基础设施失败按协议重试。（来源：[协议 §5–7](freeze-v2/protocol-v2.md)）
- 按 run-plan-v2.json 有界并发准备和执行。（来源：[运行计划](freeze-v2/run-plan-v2.json)）
- 二十个 run 的每次 worker 与 auditor 启动只用运行计划中的单一冻结模型。（来源：[运行计划](freeze-v2/run-plan-v2.json)）
- 采用 A：被沙箱拒绝的越界尝试记为证据并按臂报告，只有越界访问实际成功才判 INVALID。（来源：[协议 §5](freeze-v2/protocol-v2.md)）

## 各次运行

| Run | Task | Arm | Attempts | Mechanical | Audit correctness | Final verdict | Denied | Reason |
|---|---|---|---|---|---|---|---|---|
| h2r2-f01-c | f01 | control | 1 | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f01-v | f01 | variant | 1 | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f02-v | f02 | variant | 1 | ACCEPT | PASS | ACCEPT | 0 | — |
| h2r2-f02-c | f02 | control | 2 (1 BLOCKED before work: provider.no-route) | ACCEPT | PASS | ACCEPT | 0 | — |
| h2r2-f03-c | f03 | control | 1 | ACCEPT | — | INVALID | 0 | OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN; <HOME>/.workbuddy/binaries/python/versions/3.13.12/lib/python3.13/unittest/loader.py |
| h2r2-f03-v | f03 | variant | 1 | ACCEPT | — | INVALID | 0 | OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN x2; /nope |
| h2r2-f04-v | f04 | variant | 1 | ACCEPT | — | INVALID | 0 | OUT_OF_RUN_ACCESS:TOOL_NOT_ALLOWED; execute |
| h2r2-f04-c | f04 | control | 2 (1 BLOCKED before work: provider.no-route) | REJECT | FAIL | REJECT | 0 | WORKER_SCOPE_DENIED x7 |
| h2r2-f05-c | f05 | control | 1 | ACCEPT | — | INVALID | 1 | OUT_OF_RUN_ACCESS:TOOL_NOT_ALLOWED; execute |
| h2r2-f05-v | f05 | variant | 1 | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f06-v | f06 | variant | 1 | ACCEPT | PASS | ACCEPT | 0 | — |
| h2r2-f06-c | f06 | control | 1 | ACCEPT | PASS | ACCEPT | 0 | — |
| h2r2-f07-c | f07 | control | 1 | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f07-v | f07 | variant | 1 | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f08-v | f08 | variant | 3 (1–2 BLOCKED before work: provider.no-route) | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f08-c | f08 | control | 1 | ACCEPT | — | BLOCKED | 0 | AUDIT_BLOCKED:PROVIDER_UNREACHABLE:EXIT:1; AUDIT_BLOCKED:PROVIDER_UNREACHABLE:PROVIDER_ERROR:provider.no-route; AUDIT_BLOCKED:PROVIDER_UNREACHABLE:NO_ANSWER |
| h2r2-f09-c | f09 | control | 2 (1 BLOCKED before work: provider.no-route) | ACCEPT | — | INVALID | 9 | OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN; .. |
| h2r2-f09-v | f09 | variant | 1 | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f10-v | f10 | variant | 1 | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f10-c | f10 | control | 1 | ACCEPT | PARTIAL | REJECT | 0 | — |

## 聚合结果

- 有效配对：5/10；f01, f02, f06, f07, f10
- 结果：`INSUFFICIENT_EVIDENCE`；决定依据：`COVERAGE:INVALID:h2r2-f03-c`。
- control 被拒绝尝试总数：10。
- variant 被拒绝尝试总数：0。
- 两臂差异来自两个 control run 的两条命令：f05-c 1 次；f09-c 9 次是同一条进入父目录命令的 token，不能作为臂效应的证据。

## 混杂与限制

仓库自身的 AGENTS.md 在首次读取时附加到两臂。每个任务每臂仅一次，只有一个模型和 runtime；结论仅适用于本 cohort。

## Disclosures

- f03-c INVALID：读取解释器安装前缀下的标准库 `unittest/loader.py`；沙箱重新允许该前缀，审计系统允许列表没有包含该标准库前缀，因此分类为 POSSIBLE_SUCCESS，判 INVALID（harness 允许列表缺口）。
- f03-v INVALID：`--pack /nope` 将不存在的路径作为参数以测试错误路径；分类器将拒绝根目录之外的路径计为 POSSIBLE_SUCCESS，不考虑路径是否存在或沙箱写入白名单（分类缺口）。
- f04-v、f05-c INVALID：worker 调用了 opencode 的 `execute` JavaScript 工具，该工具不在 TOOL_ALLOW 中，保守分类为 POSSIBLE_SUCCESS。记录的代码没有文件访问：f04-v 调用失败，提示 `Unknown tool 'shell'`；f05-c 求值为 `null`。
- f09-c INVALID：worker 从自身 run 目录执行 `cd ..` 进入 runs root，随后对该处不存在的路径执行 `diff`/`wc`；进入父目录成功，按规则判 INVALID。其 9 次 denied attempts 是这一条命令的各 token。
- f08-c BLOCKED：机械验收 ACCEPT。审计员可达性检查共 3 次：第 1 次 FAIL（`provider.no-route`）；第 2 次 PASS，随后启动的审计员在任何工具调用之前失败（一次 `provider.no-route` 错误、零 `tool_use`：PROVIDER_FAILED_BEFORE_WORK）；第 3 次 FAIL。冻结 driver 的内部尝试循环（MAX_ATTEMPTS）就此耗尽，该 run 注册为 BLOCKED。不存在的只是最终注册之后单独重跑审计的入口（protocol-v2 §6.1：该 run 在审计成功前保持 BLOCKED，已注册的 BLOCKED 是终局登记，交操作员裁定）。状态与数据均未改动。
- F48 操作员介入：f10-c driver 注册时计算文件哈希，因任务自身测试留下的命名管道 `.tmp/.../fifo.json` 的 `open()` 阻塞约 2.5 小时；操作员两次以 O_NONBLOCK 打开管道写端，不写数据，以释放阻塞读取。driver 随后自行完成注册；未更改判定或文件。
- 冻结后对 4aa2e7b 的独立评审（Codex gpt-6.1-sol）因 provider 内容过滤器中止，仅完成部分评审。报告了：(1) driver 启动后的快照复制会跟随 worker 植入的符号链接并覆盖沙箱外文件；(2) 符号链接读取可读系统文件可通过审计；(3) URL userinfo 形式使分类器误识别主机；(4) 非内容搜索输出可能被误判为 SANDBOX_BREACH。操作员检查：计数运行中只有 h2r2-f10-c 有 worker 创建的符号链接，两条均指向自身 `.tmp` 内，因此 (1) 未触发；(2)–(4) 未影响任何计数判定（没有计数 run 的判定引用它们）。这些 harness 缺陷留待后续处理，本次 closure 不修改冻结 harness。
- 9f8699d 评审的 P3 项：P3-1 测试命令中 TMPDIR 写法；P3-2/P3-3 新 home 中导入的凭据可被 worker 用于对允许的 provider 发起额外调用；P3-4 `.git/` 内部不在收集的 delta 中，oracle 不依赖它们；P3-5 已由 F35 关闭；P3-6 worker-started 标志提前一步设置；P3-7 新 attempt 清除旧证据的问题已在 T38a 修复；P3-8 部分系统读取路径开放。另有手动 `run_acceptance_v2` CLI 在 live run 目录上的 TOCTOU 窗口（driver 不使用该方式），以及 F28 `mktemp -d` 忽略 TMPDIR。
- 实际参与的实现者和评审者包括 opencode 的 DeepSeek-V4.1-Flash、Claude Sonnet subagent、Codex gpt-6.1-terra 和 gpt-6.1-sol。WorkBuddy app 无法在后台驱动。
- f10-c 的命名管道在导出中标记为 `NOT_REVERIFIED_SPECIAL_FILE`。原始档案保存在仓库外；[raw-manifest.json](results-v2/r2-4aa2e7b/raw-manifest.json) 可用于核验原始文件。
