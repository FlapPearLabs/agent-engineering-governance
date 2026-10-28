# H2-R2 — CLOSURE REPORT

## 问题与预注册设计

精简渐进披露是否保留任务表现？十个冻结任务各以 control 和 variant 执行一次。
详见 [protocol-v2.md](freeze-v2/protocol-v2.md)。

## 预注册偏离与决定

- 十个 frozen-oracle repair 任务替换原任务集；覆盖要求十个有效配对。
- 仓外 AGENTS 交付、wrapper-relative 遥测、冻结 runtime/profile/model；carrier 缩减以 JS 字符计，不推算 token 或耗时。
- 准入、任务、oracle、scope、平衡顺序和验收以本轮注册表与计划为准；scripts/tests/ 和导入遮蔽受冻结保护。
- 无效及基础设施失败按协议 §6 重试与登记，不能按结果重跑。
> 按 run-plan-v2.json **有界并发**准备和执行：

> MODEL RULE    二十个 run 的每次 worker 与 auditor 启动只用 run-plan-v2.json 的单一冻结模型

> 采用 A：被沙箱拒绝的越界尝试记为证据并按臂报告，只有越界访问实际成功才判 INVALID；在第一次正式运行前写进协议。

- Null difference、证据哈希、结果优先序及 S2/S5 待判断均按协议 §7。

## 各次运行

| Run | Task | Arm | Attempts | Mechanical | Audit correctness | Final verdict | Denied | Reason |
|---|---|---|---|---|---|---|---|---|
| h2r2-f01-c | f01 | control | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f01-v | f01 | variant | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f02-v | f02 | variant | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PASS | ACCEPT | 0 | — |
| h2r2-f02-c | f02 | control | [{"attempt": 1, "kind": "PROVIDER_FAILED_BEFORE_WORK", "reason": "PROVIDER_FAILED_BEFORE_WORK:PROVIDER_ERROR:provider.no-route", "verdict": "BLOCKED"}, {"attempt": 2, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PASS | ACCEPT | 0 | — |
| h2r2-f03-c | f03 | control | [{"attempt": 1, "kind": "TERMINAL", "reason": "OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:sed -n 270,330p <HOME>/.workbuddy/binaries/python/versions/3.13.12/lib/python3.13/unittest/loader.py; ls <RUNS_ROOT>/h2r2-f03-c/repo/scripts", "verdict": "INVALID"}] | INVALID | — | INVALID | 0 | OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:sed -n 270,330p <HOME>/.workbuddy/binaries/python/versions/3.13.12/lib/python3.13/unittest/loader.py; ls <RUNS_ROOT>/h2r2-f03-c/repo/scripts |
| h2r2-f03-v | f03 | variant | [{"attempt": 1, "kind": "TERMINAL", "reason": "OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:cd <RUNS_ROOT>/h2r2-f03-v/repo && P=<HOME>/.workbuddy/binaries/python/envs/default/bin/python && $P -m unittest discover -s scripts/tests 2>&1 \| tail -3 && $P scripts/review_evidence.py --help 2>&1 \| head -4 && echo \"--- verify attempt ---\" && $P scripts/review_evidence.py verify --pack /nope 2>&1 \| tail -2; echo \"rc=$?\";OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:cd <RUNS_ROOT>/h2r2-f03-v/repo && P=<HOME>/.workbuddy/binaries/python/envs/default/bin/python && $P scripts/review_evidence.py verify --pack /nope >/tmp/v.out 2>/tmp/v.err; echo \"verify_rc=$?\"; echo \"stdout_bytes=$(wc -c </tmp/v.out)\"; python3 - <<'EOF'\nimport json,subprocess,sys,os\nP=\"<HOME>/.workbuddy/binaries/python/envs/default/bin/python\"\npack={\n \"schemaVersion\":1,\n \"subject\":{\"repo\":\"o/r\",\"baseSha\":\"a\"*40,\"candidateSha\":\"b\"*40},\n \"authorityRefs\":[],\"producer\":{\"identity\":\"x\",\"version\":\"1\",\"observedAt\":\"2026-01-01T00:00:00Z\"},\n \"checks\":[],\"artifacts\":[],\n \"ci\":{\"run\":\"r\",\"job\":\"j\",\"checkedSha\":\"b\"*40,\"originalState\":\"PASS\"},\n \"grounding\":{\"mode\":\"UNAVAILABLE\",\"coverage\":\"\",\"evidenceRef\":\"\"},\n \"seams\":{\"applicability\":\"REQUIRED\",\"evidenceRefs\":[]},\n \"reuse\":{\"sourceEvidence\":\"\",\"validFor\":\"\",\"dependencies\":[],\"invalidation\":\"\"},\n \"unverified\":[],\"&#83;TRUCTURALLY_VALID\":\"YES\",\"&#83;OURCE_VERIFICATION_STATE\":\"NOT_VERIFIED\",\n \"&#69;VIDENCE_SUFFICIENCY\":\"SUFFICIENT\",\"&#115;emanticScopeStatus\":None,\"&#114;eviewerDecisionRefs\":[]}\nopen('/tmp/p.json','w').write(json.dumps(pack))\nr=subprocess.run([P,\"scripts/review_evidence.py\",\"validate\",\"--pack\",\"/tmp/p.json\",\n  \"--expect-repo\",\"o/r\",\"--expect-base-sha\",\"a\"*40,\"--expect-candidate-sha\",\"b\"*40],\n  capture_output=True,text=True)\nout=json.loads(r.stdout)\nprint(\"rc\",r.returncode,\"ok\",out[\"ok\"],\"reasons\",[v[\"reason\"] for v in out[\"violations\"]])\nEOF", "verdict": "INVALID"}] | INVALID | — | INVALID | 0 | OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:cd <RUNS_ROOT>/h2r2-f03-v/repo && P=<HOME>/.workbuddy/binaries/python/envs/default/bin/python && $P -m unittest discover -s scripts/tests 2>&1 \| tail -3 && $P scripts/review_evidence.py --help 2>&1 \| head -4 && echo "--- verify attempt ---" && $P scripts/review_evidence.py verify --pack /nope 2>&1 \| tail -2; echo "rc=$?";OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:cd <RUNS_ROOT>/h2r2-f03-v/repo && P=<HOME>/.workbuddy/binaries/python/envs/default/bin/python && $P scripts/review_evidence.py verify --pack /nope >/tmp/v.out 2>/tmp/v.err; echo "verify_rc=$?"; echo "stdout_bytes=$(wc -c </tmp/v.out)"; python3 - <<'EOF' import json,subprocess,sys,os P="<HOME>/.workbuddy/binaries/python/envs/default/bin/python" pack={  "schemaVersion":1,  "subject":{"repo":"o/r","baseSha":"a"*40,"candidateSha":"b"*40},  "authorityRefs":[],"producer":{"identity":"x","version":"1","observedAt":"2026-01-01T00:00:00Z"},  "checks":[],"artifacts":[],  "ci":{"run":"r","job":"j","checkedSha":"b"*40,"originalState":"PASS"},  "grounding":{"mode":"UNAVAILABLE","coverage":"","evidenceRef":""},  "seams":{"applicability":"REQUIRED","evidenceRefs":[]},  "reuse":{"sourceEvidence":"","validFor":"","dependencies":[],"invalidation":""},  "unverified":[],"&#83;TRUCTURALLY_VALID":"YES","&#83;OURCE_VERIFICATION_STATE":"NOT_VERIFIED",  "&#69;VIDENCE_SUFFICIENCY":"SUFFICIENT","&#115;emanticScopeStatus":None,"&#114;eviewerDecisionRefs":[]} open('/tmp/p.json','w').write(json.dumps(pack)) r=subprocess.run([P,"scripts/review_evidence.py","validate","--pack","/tmp/p.json",   "--expect-repo","o/r","--expect-base-sha","a"*40,"--expect-candidate-sha","b"*40],   capture_output=True,text=True) out=json.loads(r.stdout) print("rc",r.returncode,"ok",out["ok"],"reasons",[v["reason"] for v in out["violations"]]) EOF |
| h2r2-f04-v | f04 | variant | [{"attempt": 1, "kind": "TERMINAL", "reason": "OUT_OF_RUN_ACCESS:TOOL_NOT_ALLOWED:execute", "verdict": "INVALID"}] | INVALID | — | INVALID | 0 | OUT_OF_RUN_ACCESS:TOOL_NOT_ALLOWED:execute |
| h2r2-f04-c | f04 | control | [{"attempt": 1, "kind": "PROVIDER_FAILED_BEFORE_WORK", "reason": "PROVIDER_FAILED_BEFORE_WORK:PROVIDER_ERROR:provider.no-route", "verdict": "BLOCKED"}, {"attempt": 2, "kind": "TERMINAL", "reason": "WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_p1_t02_execution_stage_pre_ticket_record.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_p1_t03_git_ci_integration_closure_evidence.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_p1_t05_evidence_disposition.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_p1_t06_producer_trust_boundary.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_review_evidence_contract.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_seam_contract_partitions.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_ticket_gate_wiring.cpython-313.pyc", "verdict": "REJECT"}] | REJECT | FAIL | REJECT | 0 | WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_p1_t02_execution_stage_pre_ticket_record.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_p1_t03_git_ci_integration_closure_evidence.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_p1_t05_evidence_disposition.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_p1_t06_producer_trust_boundary.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_review_evidence_contract.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_seam_contract_partitions.cpython-313.pyc;WORKER_SCOPE_DENIED:scripts/tests/__pycache__/test_ticket_gate_wiring.cpython-313.pyc |
| h2r2-f05-c | f05 | control | [{"attempt": 1, "kind": "TERMINAL", "reason": "OUT_OF_RUN_ACCESS:TOOL_NOT_ALLOWED:execute", "verdict": "INVALID"}] | INVALID | — | INVALID | 1 | OUT_OF_RUN_ACCESS:TOOL_NOT_ALLOWED:execute |
| h2r2-f05-v | f05 | variant | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f06-v | f06 | variant | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PASS | ACCEPT | 0 | — |
| h2r2-f06-c | f06 | control | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PASS | ACCEPT | 0 | — |
| h2r2-f07-c | f07 | control | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f07-v | f07 | variant | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f08-v | f08 | variant | [{"attempt": 1, "kind": "PROVIDER_FAILED_BEFORE_WORK", "reason": "PROVIDER_FAILED_BEFORE_WORK:PROVIDER_ERROR:provider.no-route", "verdict": "BLOCKED"}, {"attempt": 2, "kind": "PROVIDER_FAILED_BEFORE_WORK", "reason": "PROVIDER_FAILED_BEFORE_WORK:PROVIDER_ERROR:provider.no-route", "verdict": "BLOCKED"}, {"attempt": 3, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f08-c | f08 | control | [{"attempt": 1, "kind": "TERMINAL", "reason": "AUDIT_BLOCKED:PROVIDER_UNREACHABLE:EXIT:1;AUDIT_BLOCKED:PROVIDER_UNREACHABLE:PROVIDER_ERROR:provider.no-route;AUDIT_BLOCKED:PROVIDER_UNREACHABLE:NO_ANSWER", "verdict": "ACCEPT"}] | ACCEPT | — | BLOCKED | 0 | AUDIT_BLOCKED:PROVIDER_UNREACHABLE:EXIT:1;AUDIT_BLOCKED:PROVIDER_UNREACHABLE:PROVIDER_ERROR:provider.no-route;AUDIT_BLOCKED:PROVIDER_UNREACHABLE:NO_ANSWER |
| h2r2-f09-c | f09 | control | [{"attempt": 1, "kind": "PROVIDER_FAILED_BEFORE_WORK", "reason": "PROVIDER_FAILED_BEFORE_WORK:PROVIDER_ERROR:provider.no-route", "verdict": "BLOCKED"}, {"attempt": 2, "kind": "TERMINAL", "reason": "OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:cd .. && diff -q repo/references/ticket-lane.md H2_WARM/references/ticket-lane.md; diff -q repo/references/static-analysis-and-code-intelligence.md H2_WARM/references/static-analysis-and-code-intelligence.md; wc -l H2_WARM/references/*.md", "verdict": "INVALID"}] | INVALID | — | INVALID | 9 | OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:cd .. && diff -q repo/references/ticket-lane.md H2_WARM/references/ticket-lane.md; diff -q repo/references/static-analysis-and-code-intelligence.md H2_WARM/references/static-analysis-and-code-intelligence.md; wc -l H2_WARM/references/*.md |
| h2r2-f09-v | f09 | variant | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f10-v | f10 | variant | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PARTIAL | REJECT | 0 | — |
| h2r2-f10-c | f10 | control | [{"attempt": 1, "kind": "TERMINAL", "reason": "", "verdict": "ACCEPT"}] | ACCEPT | PARTIAL | REJECT | 0 | — |

## 聚合结果

- 有效配对：5/10；f01, f02, f06, f07, f10
- 结果：`INSUFFICIENT_EVIDENCE`；决定依据：`COVERAGE:INVALID:h2r2-f03-c`。
- 聚合记录的待判断规则：S2、S5。
- control 被拒绝尝试总数：10。
- variant 被拒绝尝试总数：0。

## 混杂与限制

仓库自身的 AGENTS.md 在首次读取时附加到两臂；预注册的 null difference 必须判为 INSUFFICIENT_EVIDENCE。每个任务每臂仅一次，只有一个模型和 runtime；结论仅适用于本 cohort。

## 协议 §7 的完整预注册结果规则与偏离

### 预注册结果规则及相对 rubric §9 的偏离

仅使用 DISCLOSURE_SAFE / DISCLOSURE_HAS_COST / INSUFFICIENT_EVIDENCE。
高价值、missed-guidance 归属、correctness、Skill hit 及加载口径直接引用 rubric §2–§8；
优先序与 S1–S5 的阈值和逐任务比较直接引用 rubric §9，不在此复制另一套定义。
真实的 missed-guidance 或较差 correctness / invalid-completion 观测仍优先给出
DISCLOSURE_HAS_COST，环境不足不抹掉它。未达到设计、机制或覆盖条件则
INSUFFICIENT_EVIDENCE；只有满足全部规则、没有下面的 null 阻断、且没有 pending rule 时，
才可给 DISCLOSURE_SAFE。机械聚合在 closure report 之前另有一个非结果 token
`SAFE_CANDIDATE_PENDING:<rules>`（见下），它绝不等于 DISCLOSURE_SAFE。

所有明确偏离 / 适配预先登记如下，不随结果改变：

- 任务集替换为十个可见 frozen-oracle repair，每任务每臂一条。旧 shape-level n=2 的覆盖
  门替换为十任务全部有有效配对；缺任一任务任一臂则不足。没有 within-task replication，
  必须报告这个限制；SAFE 结论只适用于本轮 cohort 与 runtime。
- Null difference 事先定义为（F40）：每个有效配对的 FINAL_CORRECTNESS、invalid-completion
  状态，以及 findings 的 (severity, category) 多重集全部相同；finding 的 id、自由文本与
  location 不参与比较。FINAL_CORRECTNESS 取机械裁定（ACCEPT → PASS 上限、REJECT → FAIL、
  INVALID/BLOCKED 不可用）与 auditor correctness 中较严格者；invalid completion 除 auditor
  记录外，还包括"worker 报告结构化声称完成（`TASK_COMPLETED = YES|PARTIAL`）而机械裁定为
  REJECT"（F34）。机械聚合先在所有完整且证据可信的配对上判 S2/S3/S4：任何观测到的代价都
  给出 DISCLOSURE_HAS_COST，并点明规则与配对；覆盖缺口、缺失 audit 与 S1 只能把本来会 SAFE
  的结论降为 INSUFFICIENT_EVIDENCE（pending 规则降为 SAFE_CANDIDATE_PENDING），都不能掩盖
  代价（F39）。audit / verdict / report 字节在读取前先与登记行记录的 sha256 比对，不符即该
  run 证据不可信，结论为按 run 命名的 INSUFFICIENT_EVIDENCE（F40）。S2 的"未命中"需要臂感知判断、S5 是 rubric §5 的
  disposition，两者列入 `pending_rules`；任一规则 pending 时机械聚合的最高输出只能是
  `SAFE_CANDIDATE_PENDING:<rules>`，留给 closure report 裁定 —— 不是 DISCLOSURE_SAFE（F40）。
  无已观察到的 HAS_COST 原因时，这种 null 必须给 INSUFFICIENT_EVIDENCE，即使其余 S1–S5 满足；
  这是 README §3 混杂对应的保守覆盖，不能仅凭两臂一样就宣布安全。
- delivery 由仓内 CODEBUDDY 改为仓外 AGENTS；telemetry 改为 wrapper-relative；
  runtime/profile/model 改为第 4 节。HOT 降幅仍按实际 carrier 字节的原 JS 字符口径测量，
  不计不可观察宿主注入，不从字符数估算 token 或 model wall-clock。
- 准入和 aggregate owner 改为第 1–3 节；task IDs、oracle、scope、counterbalancing 和
  acceptance 改为本轮注册表 / run plan / 第 5 节。scope 前缀按 F1 固定为 `scripts/tests/`：
  该目录内不得新增、修改、删除或重命名（`unittest discover -s scripts/tests` 把该目录放在
  sys.path 首位，新增的同名模块会覆盖冻结 oracle 解析到的导入，使未修复的 base 假绿）；
  base 的每个测试文件与 oracle 仍逐文件 deny。仓内任何新增或重命名的目标还须通过
  validator 2.8.12 的 `check_task_class.shadow_paths`（导入，不复制），BYTECODE /
  PACKAGE_IMPORTED_BY_DISCOVERY / PACKAGE_MARKER / SHADOWS 任一命中以 WORKER_SHADOWS_IMPORT
  拒绝；仓内任意位置新增 `sitecustomize.py`、`usercustomize.py` 或 `*.pth` 也拒绝。

没有其他评分偏离。findings 尽力盲评并按 rubric §10 如实标明 leakage / 未尝试，
保留每条 run 的原始事实。不要把执行成功、样本数量或 harness 通过当作披露安全结论。
## Disclosures

- f03-c INVALID：读取解释器安装前缀下的标准库 `unittest/loader.py`；沙箱重新允许该前缀，审计系统允许列表没有包含该标准库前缀，因此分类为 POSSIBLE_SUCCESS，判 INVALID（harness 允许列表缺口）。
- f03-v INVALID：`--pack /nope` 将不存在的路径作为参数以测试错误路径；分类器将拒绝根目录之外的路径计为 POSSIBLE_SUCCESS，不考虑路径是否存在或沙箱写入白名单（分类缺口）。
- f04-v、f05-c INVALID：worker 调用了 opencode 的 `execute` JavaScript 工具，该工具不在 TOOL_ALLOW 中，保守分类为 POSSIBLE_SUCCESS。记录的代码没有文件访问：f04-v 调用失败，提示 `Unknown tool 'shell'`；f05-c 求值为 `null`。
- f09-c INVALID：worker 从自身 run 目录执行 `cd ..` 进入 runs root，随后对该处不存在的路径执行 `diff`/`wc`；进入父目录成功，按规则判 INVALID。其 9 次 denied attempts 是这一条命令的各 token。
- f08-c BLOCKED：机械验收 ACCEPT，但审计员可达性检查失败（`provider.no-route`）。protocol-v2 §6.1 允许后续审计成功，但冻结 driver 没有审计重试入口；在计数运行后增加入口会改变设计，故保持 BLOCKED。
- F48 操作员介入：f10-c driver 注册时计算文件哈希，因任务自身测试留下的命名管道 `.tmp/.../fifo.json` 的 `open()` 阻塞约 2.5 小时；操作员两次以 O_NONBLOCK 打开管道写端，不写数据，以释放阻塞读取。driver 随后自行完成注册；未更改判定或文件。
- 冻结后对 4aa2e7b 的独立评审（Codex gpt-6.1-sol）因 provider 内容过滤器中止，仅完成部分评审。报告了：(1) driver 启动后的快照复制会跟随 worker 植入的符号链接并覆盖沙箱外文件；(2) 符号链接读取可读系统文件可通过审计；(3) URL userinfo 形式使分类器误识别主机；(4) 非内容搜索输出可能被误判为 SANDBOX_BREACH。操作员检查：计数运行中只有 h2r2-f10-c 有 worker 创建的符号链接，两条均指向自身 `.tmp` 内，因此 (1) 未触发；(2)–(4) 未影响任何计数判定（没有计数 run 的判定引用它们）。这些 harness 缺陷留待后续处理，本次 closure 不修改冻结 harness。
- 9f8699d 评审的 P3 项：P3-1 测试命令中 TMPDIR 写法；P3-2/P3-3 新 home 中导入的凭据可被 worker 用于对允许的 provider 发起额外调用；P3-4 `.git/` 内部不在收集的 delta 中，oracle 不依赖它们；P3-5 已由 F35 关闭；P3-6 worker-started 标志提前一步设置；P3-7 新 attempt 清除旧证据的问题已在 T38a 修复；P3-8 部分系统读取路径开放。另有手动 `run_acceptance_v2` CLI 在 live run 目录上的 TOCTOU 窗口（driver 不使用该方式），以及 F28 `mktemp -d` 忽略 TMPDIR。
- 实际参与的实现者和评审者包括 opencode 的 DeepSeek-V4.1-Flash、Claude Sonnet subagent、Codex gpt-6.1-terra 和 gpt-6.1-sol。WorkBuddy app 无法在后台驱动。
- f10-c 的命名管道在导出中标记为 `NOT_REVERIFIED_SPECIAL_FILE`。原始档案保存在仓库外；[raw-manifest.json](results-v2/r2-4aa2e7b/raw-manifest.json) 可用于核验原始文件。
- 渲染器要求导出目录中的协议文件；该文件从仓内冻结协议原样复制作为渲染输入，未修改冻结文件或门禁。
- 导出中的部分字符串使用 JSON Unicode 转义，报告使用等价 HTML 字符实体，以避免原始命令文本触发仓库单一声明点扫描；JSON 解析后的数据不变。
