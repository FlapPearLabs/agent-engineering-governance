# REF: Review Evidence — 唯一证据接口详情与冻结的字段合同（REVIEW_EVIDENCE_CONTRACT_V1）

> Canonical owner: AGENTS.md §1/§7（权威分层与证据纪律）。本文件是 **Review Evidence 接口的唯一语义详情 owner（single source）**；schema / template / CLI 是它的机械形态。任何下游票只**引用**本文件，**不得**重新声明本文件已声明的字段名、闭合集或机器形状。

本文件对应父规范 `REQ-W2-01`（四个 surface / 接口一致性要求 1–7）与 `REQ-W2-04` 字段合同，受 `AC-44` / `AC-42` / `AC-10` / `AC-06` / `AC-28` / `AC-29` / `AC-30` 验收，反例输入为 `CE-06` / `CE-10` / `CE-24` / `CE-28`。

## 1. 四个协同 surface（`REQ-W2-01` 要求 1–6）

```text
references/review-evidence.md          唯一语义详情 owner（本文件）
schemas/review-evidence.schema.json    版本化机器合同（机械表达本文件的字段组）
templates/review-evidence.json         占位符形态模板（`RULES.md` R2；必须符合 schema）
scripts/review_evidence.py             薄 collect / validate CLI（消费同一 schema / 合同）
```

一致性规则（不得只满足其一）：

```text
1  四个 surface 均存在
2  语义详情只在 references/review-evidence.md，不在别处复制
3  schema 机械表达第 3 节的字段合同与全部闭合集
4  template 在占位符模式下符合 schema（第 7 节）
5  CLI 与 schema 消费同一份合同：CLI 不另存一份枚举、不另建一套判定
6  其它 canonical surface 只**指针 / 链接**本接口，不定义竞争性 Review Evidence 接口
    （第二个 canonical owner = `CE-28` 双重声明，必须被检出并收敛回本 owner）
7  本文件满足仓内全部既有 reference-file 不变量，含 `scripts/validate_governance.py`
   检查 `references-declare-canonical-owner` 要求的字面 `Canonical owner`（见文件头）
```

**唯一声明点纪律**：第 3 节的字段名、第 4 节的闭合集、第 5 节的复用描述符与第 6 节的两个权威分离字段名，**在仓库范围内各只有一处声明**——即本文件（语义）与其机械形态 `schemas/review-evidence.schema.json` / `templates/review-evidence.json`。消费方只引用；重复声明按 `CE-28` 拒绝。

## 2. 声明 vs 行为边界（本票只声明；`STOP = CONTRACT_GAP` 优先于发明）

```text
P1-T04（本接口）    声明字段名、闭合集与机器形状。不实现任何行为。
P1-T05            消费三条评估轴，拥有其**核验行为与处置**。本文件不定义处置规则。
P1-T06            拥有信任边界（取回 / 网络 / 文件系统权威）。本文件只声明
                  `commandRef` / `artifacts[].location` 是**声明**而非授权。
P1-T07            拥有 `semanticScopeStatus` / `reviewerDecisionRefs` 的**权威与写入语义**。
                  本文件只声明这两个字段名与机器形状：谁可写入、consumer 可推导什么，
                  由 P1-T07 定义。
P1-T08            拥有复用描述符的**行为生命周期**（复用合法性、按类型有效期、定向失效、
                  subject/report commit 身份）。本文件只声明描述符的**形状与闭合值域**。
P1-T16            拥有 gate 入口自测。本文件只**声明** CLI 的 argv / 退出码 / 结构化输出契约，
                  P1-T16 验证而不重定义。
```

因此本文件**不**规定：某个轴取值应当阻断什么、`INVALID` 与 `TEMPORARILY_UNAVAILABLE` 如何按 cause 分类、复用何时合法、reviewer 字段谁能写。任何需要这些行为的判定的实现都属**越界**。

## 3. 字段合同（冻结；不得改名、不得添加同义词）

```text
schemaVersion
subject:      repo, baseSha, candidateSha
authorityRefs
producer:     identity, version, observedAt
checks[]:     id, scope, commandRef, status, exitCode, artifactRefs
artifacts[]:  location, contentDigest
ci:           run, job, checkedSha, originalState
grounding:    mode, coverage, evidenceRef
seams:        applicability, evidenceRefs, reason, acceptanceRef
reuse:        sourceEvidence, validFor, dependencies[], invalidation
unverified[]
STRUCTURALLY_VALID / SOURCE_VERIFICATION_STATE / EVIDENCE_SUFFICIENCY
semanticScopeStatus / reviewerDecisionRefs
```

顶层与各子对象均 `additionalProperties: false`：契约外的字段被拒绝，而不是被忽略。

第 3 节列出**字段名与机器形状**；哪些**键**是结构必需键由 schema 的 `required` 机械表达、由 §3.1 的失败语义逐字段说明，二者必须一致。当前**唯一**不是结构必需键的字段是 `authorityRefs`（§3.1）：它的缺失是**不充分性**，不是结构不合法。

### 3.1 逐字段语义与失败语义（对齐父规范 §5.1）

| 字段 | 语义 | 失败语义 |
|---|---|---|
| `schemaVersion` | 证据包合同版本；当前值域 `{1}` | 未知值 → `EVIDENCE_VERSION_UNKNOWN`，**reject，且绝不猜测迁移**（见第 8 节顺序） |
| `subject.repo` | 目标仓 remote 或 `owner/repo` | 与目标仓不符 → `EVIDENCE_SUBJECT_MISMATCH` |
| `subject.baseSha` | 候选基线全文 40-hex SHA | 不可解析 → `REJECT`；与受评基线不符 → `EVIDENCE_STALE_SUBJECT` |
| `subject.candidateSha` | 被评候选全文 40-hex SHA | 不可解析 → `REJECT`；与受评候选不符 → `EVIDENCE_STALE_SUBJECT` |
| `authorityRefs` | 版本化合同引用；**键省略与空数组等价**（二者都是"未声明任何版本化合同引用"这一陈述） | **不充分性，不是结构不合法**：两种形态都**不**产生任何结构违规，尤其**不得**产生 `REQUIRED_FIELD_MISSING`。该情形由**正交**的 `EVIDENCE_SUFFICIENCY = INSUFFICIENT` 承载；充分性轴的**处置**属 P1-T05，本合同只声明形状、不判定它（见 §8 的 reason 分类：它不属于其中任何一类） |
| `producer.identity/version/observedAt` | 生成者、版本与观测时刻（ISO-8601 UTC） | 缺任一 → `REJECT`（必需结果字段） |
| `checks[].id/scope/commandRef/status/exitCode/artifactRefs` | **单条机械检查**的事实 | 缺任一 → `REJECT`；`status` 越出闭合集 → `REJECT` |
| `artifacts[].location` | 产物位置**声明**：repo 相对路径或 CI artifact 标识 | **不是**网络或文件系统授权；取回边界不由本合同决定（P1-T06） |
| `artifacts[].contentDigest` | 内容摘要（`算法:十六进制`） | 形状不符 → `REJECT`；摘要变化属于消费侧判定，不在此定义 |
| `ci.run/job/checkedSha/originalState` | CI 事实；`checkedSha` 允许空串表示"未观测到 CI" | `originalState` 越出既有七值集 → `REJECT`；`checkedSha != subject.candidateSha` 时**不得作为该候选的 CI 证据**（消费规则，P1-T05） |
| `grounding.mode/coverage/evidenceRef` | 接地模式与覆盖（命名对齐 `codegraph-grounding.md` §2.1，见第 6 节） | `mode` 越出三模式拼写 → `REJECT` |
| `seams.applicability/evidenceRefs/reason/acceptanceRef` | Seam 适用性与证据 | `applicability = N/A` 缺 `reason` 或缺 `acceptanceRef` → `REJECT`（见第 6 节） |
| `reuse.sourceEvidence/validFor/dependencies/invalidation` | 复用声明；`dependencies` 为第 5 节闭结构数组 | 形状不合法（含自由文本）→ `REJECT` |
| `unverified[]` | 显式未验证项 | **省略 = 结构不合法（`REJECT`）**；显式空数组 = 合法的"无未验证项" |
| `STRUCTURALLY_VALID` | 结构轴（闭合集） | 值 `NO` → `REJECT`，不进入消费（见第 8 节） |
| `SOURCE_VERIFICATION_STATE` | 来源轴（闭合集） | 越出闭合集 → `REJECT`；跨轴取值 → `REJECT`（轴坍缩） |
| `EVIDENCE_SUFFICIENCY` | 充分性轴（闭合集，独立于来源轴） | 越出闭合集 → `REJECT` |
| `semanticScopeStatus` | **仅字段名**；取值来自 reviewer 权威（`REQ-W2-05`） | 不由 producer 观测升格；`null` 表示尚未由 reviewer 写入。写入与推导语义属 P1-T07 |
| `reviewerDecisionRefs` | **仅字段名**；与机器事实分字段（`REQ-W2-06`） | 机器证据包**不得自批 reviewer verdict**（self-approval 被禁止）；写入与推导语义属 P1-T07 |

**`seams.reason` / `seams.acceptanceRef` 的命名说明**：`REQ-W2-04(f)` 冻结的字段组简写为 `seams(applicability/evidenceRefs)`，而同一票的 `STATE_CONTRACT` 要求 `applicability = N/A` 必须**同时**具备理由与接受记录（与 `REQ-W1-01` 的 `REACHABILITY_APPLICABILITY` 同构）。这两个槽位因此以 `reason` / `acceptanceRef` 命名并**只在本文件声明一次**；它们与 `REACHABILITY_APPLICABILITY_REASON` / `REACHABILITY_APPLICABILITY_ACCEPTANCE_REF` 同构，是**引用该同构关系**，不是第二套适用性机制。

## 4. 五个状态机：闭合集，互不坍缩

```text
CHECK_STATUS                = PASS | FAIL | SKIPPED | ERROR | UNKNOWN
CI_STATUS                   = PASS | FAIL | NOT_TRIGGERED | CANCELLED |
                              INFRASTRUCTURE_FAILURE | KNOWN_BASELINE_FAILURE | UNKNOWN
STRUCTURALLY_VALID          = YES | NO
SOURCE_VERIFICATION_STATE   = VERIFIED | INVALID | TEMPORARILY_UNAVAILABLE | NOT_VERIFIED
EVIDENCE_SUFFICIENCY        = SUFFICIENT | INSUFFICIENT
```

- `CHECK_STATUS` 不是 `CI_STATUS`：前者描述**单条机械检查**，后者描述 **CI 运行整体**。两者不得互相替代、不得互相升格，**不得出现第二个竞争性 CI 状态机**（`CE-24` / `INV-02`）。
- `checks[].status` 只取 `CHECK_STATUS`；`ci.originalState` 只取 `CI_STATUS`。
- 三条评估轴各自取值，**互不折叠、不共用枚举**：`INSUFFICIENT` **只属于** `EVIDENCE_SUFFICIENCY`，**不是** `SOURCE_VERIFICATION_STATE` 的取值；`TEMPORARILY_UNAVAILABLE` **不得**折叠为 `INVALID`（不可达 ≠ 已作废），二者是两个各自独立、各自可表示的成员。
- 合法且必须被接受的组合（两轴独立，非矛盾）：`SOURCE_VERIFICATION_STATE = VERIFIED` + `EVIDENCE_SUFFICIENCY = INSUFFICIENT`。同理 `TEMPORARILY_UNAVAILABLE` + `INSUFFICIENT` 合法。
- 各轴取值的**处置**（是否阻断 PASS）不在本文件定义（P1-T05）。

## 5. `reuse` 依赖描述符 —— 闭结构，只在此声明一次（`REQ-W2-04(e)`）

```text
reuse.dependencies[] = {
  WHAT                       依赖是什么（共享 schema / 共享依赖 / 入口拓扑 / toolchain / authority profile）
  IDENTITY_VERSION_OR_DIGEST 依赖身份：版本号或内容摘要（至少其一）
  VALID_FOR                  该证据在哪些范围内仍适用
  INVALIDATED_BY             什么变化会使它失效（对应既有失效触发清单）
  VERIFICATION_STATE         闭合值域 VERIFIED | UNKNOWN
}
```

- 描述符是**闭结构**：五个键全部必需、`additionalProperties: false`。**自由文本不是合法取值**——`dependencies` 为字符串、或数组元素为字符串，均 `REJECT`。
- `VERIFICATION_STATE = UNKNOWN` 表示该依赖未被核验；**其行为后果（不允许复用）属 P1-T08**，本文件只声明值域。
- 组级 `reuse.validFor` 描述**整条复用声明**主张的适用范围；描述符内 `VALID_FOR` 描述**该条依赖**的适用范围。二者的使用方式属 P1-T08。
- `reuse.dependencies` 允许空数组（本包未复用任何先前证据）。

## 6. 两处同构与外接命名（只拼写，不拥有语义）

### 6.1 `seams.applicability`（与 `REACHABILITY_APPLICABILITY` 同构）

```text
applicability = REQUIRED | N/A
REQUIRED          ：该 seam 必须被真实入口到达（默认；缺理由/接受记录时按 REQUIRED 处理）
N/A               ：必须同时具备 reason 与 acceptanceRef（缺一 → REJECT）
```

`acceptanceRef` 是**引用槽位**（指向 reviewer/integrator 的接受记录），不是结论本身。

### 6.2 `grounding.mode`（`codegraph-grounding.md` §2.1 的机器拼写）

| `grounding.mode` | 对齐 `references/codegraph-grounding.md` §2.1 |
|---|---|
| `BASE_PLUS_DIFF` | 模式 A — BASE + DIFF（默认） |
| `LANE_INDEX` | 模式 B — LANE_INDEX（候选精确图） |
| `UNAVAILABLE` | 模式 C — 不可用（退化到手工 surface manifest） |

该值域**只是 §2.1 三模式的机器拼写**，使 §5.1 所要求的"命名一致性"可机械判定；接地模式语义的 owner 仍是 `codegraph-grounding.md` §2.1。`grounding.coverage` 保持自由字符串，使用该参考文件的词汇。

## 7. 模板的占位符模式（`RULES.md` R2）

`templates/review-evidence.json` 是**占位符形态模板**，不是可提交的证据包。一致性判定规则（可机械判定，且只在占位符模式下生效）：

```text
- 占位符 token = 整串匹配 ^\$\{[A-Z0-9_]+\}$
- 占位符只在 schema 要求 string 的位置被接受
- 占位符**不**被接受为 enum / const 取值（闭合集字段必须写具体合法字面量）
- 占位符**不**能替代必需键：键缺失一律结构性不合法
- 类型不匹配不会被占位符模式救回（如数组位置写占位符字符串仍然 REJECT）
- 占位符模式是**唯一**不要求目标 subject 的模式：占位符形态模板不是对一个具体候选的主张，
  因此无法、也无需与目标 subject 比较（§9.1 的 subject 强制规则）
```

模板因此对闭合集字段写入具体合法字面量（`ci.originalState = UNKNOWN`、
`seams.applicability = REQUIRED`、描述符 `VERIFICATION_STATE = UNKNOWN`、
三轴 = `YES` / `NOT_VERIFIED` / `INSUFFICIENT`），并对自由字符串使用占位符。
`semanticScopeStatus` 写 `null`、`reviewerDecisionRefs` 写空数组，因为**只有 reviewer 权威可写入它们**。

## 8. 错误语义与判定顺序（冻结）

四个可区分的错误码：

```text
EVIDENCE_VERSION_UNKNOWN  未知 schemaVersion → reject；绝不猜测迁移
EVIDENCE_SUBJECT_MISMATCH subject.repo 不是目标仓 → reject
EVIDENCE_STALE_SUBJECT    subject.candidateSha（或 baseSha）不是受评候选 → reject
REJECT                    STRUCTURALLY_VALID = NO → 不进入消费
                          （同样用于一切结构/形状违规）
```

`REJECT` 附带机器可读的 `reason`，使子类可区分；三类 `reason` 分开（**结构**与**不充分**永不混同）：

```text
结构类（schema 层，判定包内容）  PACK_ABSENT / PACK_NOT_JSON / PACK_NOT_AN_OBJECT /
                                 UNKNOWN_SCHEMA_VERSION / SCHEMA_INVALID /
                                 SCHEMA_KEYWORD_UNSUPPORTED / TYPE_MISMATCH /
                                 CONST_VIOLATION / ENUM_VIOLATION / PATTERN_VIOLATION /
                                 REQUIRED_FIELD_MISSING / ADDITIONAL_PROPERTY_FORBIDDEN /
                                 MIN_ITEMS_VIOLATION / MIN_LENGTH_VIOLATION / ONEOF_VIOLATION
声明类（错误语义层，判定包内容）  SUBJECT_REPO_MISMATCH / SUBJECT_BASE_SHA_STALE /
                                 SUBJECT_CANDIDATE_SHA_STALE / STRUCTURALLY_VALID_NO
调用类（判定调用本身与输出路径，不判定包内容）
                                 SUBJECT_EXPECTATION_ABSENT /
                                 SUBJECT_EXPECTATION_INCOMPLETE /
                                 SCHEMA_UNAVAILABLE / OUTPUT_NOT_WRITABLE
```

`authorityRefs` 的缺失（键省略或空数组）**不属于以上任何一类**：按 §3.1 它是充分性事实，由
`EVIDENCE_SUFFICIENCY` 轴承载；CLI 对它**不产出任何违规**，也**不**代 P1-T05 处置它。结构合法性
与证据充分性因此永不互相冒充：结构层只回答"这个包是否可按本合同解释"。

**判定顺序（冻结，先到先得）**：

```text
0  contract     声明的合同不可读 / 不可解析 / 不是合同对象 → REJECT（SCHEMA_UNAVAILABLE）
                合同不可用时不存在可解释的包判定，故先于一切包判定
1  parse        包不存在 / 不是 JSON / 不是对象            → REJECT
2  version      schemaVersion 不在支持值域                 → EVIDENCE_VERSION_UNKNOWN（短路）
                未知版本无法用已知 schema 解释，故不继续判定，也不猜测迁移
3  structure    按合同逐节点判定                           → REJECT（含全部结构类 reason）
4  subject      目标 subject 的声明完整性（§9.1）与比较     → SUBJECT_EXPECTATION_ABSENT（全缺）/
                                                            SUBJECT_EXPECTATION_INCOMPLETE（只声明一部分）/
                                                            EVIDENCE_SUBJECT_MISMATCH /
                                                            EVIDENCE_STALE_SUBJECT
5  declared axis 声明的 STRUCTURALLY_VALID != YES           → REJECT（STRUCTURALLY_VALID_NO）
```

`collect` 在全部判定通过后写 `--out`；显式 `--out` 无法写入 → `REJECT`（`OUTPUT_NOT_WRITABLE`），
**仍**输出结构化信封并以退出码 1 结束，且不写 `--out` 以外的任何路径。

第 5 步只读**包自己声明的**结构轴值；另外两条轴的**处置**（是否阻断 PASS）不在本接口定义（P1-T05）。因此 `VERIFIED` + `INSUFFICIENT` 的包在本接口下 **被接受**。

**本票可实现性的诚实边界**：`TEMPORARILY_UNAVAILABLE` 与 `INVALID` 的**区分**在本合同中通过"两个成员各自独立存在、均不被别名化/折叠"来机械保证（把临时态折叠进 `INVALID` 的合同必须被检出并拒绝）；**按 cause 判定某次不可达应记哪一个值**属于三轴核验行为，归 P1-T05。本文件不发明该行为。

## 9. CLI 契约（`scripts/review_evidence.py`）

### 9.1 argv surface

```text
review_evidence.py validate --pack PATH
                            [--expect-repo R]
                            [--expect-base-sha SHA40]
                            [--expect-candidate-sha SHA40]
                            [--allow-placeholders]
                            [--schema PATH]
review_evidence.py collect  --repo R --base-sha SHA40 --candidate-sha SHA40
                            --producer-identity I --producer-version V
                            [--observed-at ISO8601_UTC] [--out PATH]
                            [--schema PATH]
```

### 9.1 subject 强制规则（`AC-06`；只在此声明一次）

一次 `validate` 的结论必须建立在**已声明的目标 subject** 之上：一个包"是否属于受评候选"只能对某个声明的目标作答。

```text
完整声明（三者同时给出） --expect-repo + --expect-base-sha + --expect-candidate-sha
                        → 执行 subject 比较，产出 EVIDENCE_SUBJECT_MISMATCH /
                          EVIDENCE_STALE_SUBJECT（= AC-06 的判定）
完全不声明（三者都不给）  → 不构成一次 subject 一致性判定 → REJECT（SUBJECT_EXPECTATION_ABSENT）
只声明一部分              → 请求本身不完整（会只强制 subject 的一部分）→ REJECT（SUBJECT_EXPECTATION_INCOMPLETE）
占位符模式 --allow-placeholders
                        → **唯一**声明的例外（§7）：占位符形态模板不是对一个具体候选的主张，
                          故无需目标 subject；该模式下的通过**不**构成 AC-06 的 subject 强制
```

该规则属判定顺序第 4 步（§8）；第 0–3 步先到先得，因此合同不可用、包缺失/不可解析、版本未知或结构违规时先报那些失败。
未声明目标 subject 是**调用类**失败，不是包形状失败，故**不**产出 `REQUIRED_FIELD_MISSING`。

### 9.2 exit status 契约（**只在此声明一次**；P1-T16 验证而不重定义）

```text
0  validate：全部检查通过（含包与目标 subject 一致，§9.1）
   collect ：生成的骨架符合同一份合同，并已按 --out 落盘（若给出 --out）
1  任一失败：违规清单**仍然**以结构化 JSON 输出到 stdout（§9.3 的信封）
0  --help（参数解析自行在 stderr 报用法）
```

**声明的例外（仅有两条）**：`--help` 与**参数解析失败**（缺少必需参数、未知参数等）由 argparse
自行在 stderr 报用法，不产出信封。除此之外**每一条**声明的失败路径都必须输出 §9.3 的信封并以退出码 1
结束——包括合同不可用（`SCHEMA_UNAVAILABLE`，判定顺序第 0 步）与显式 `--out` 无法写入
（`OUTPUT_NOT_WRITABLE`）；任何失败都**不得**以未捕获异常 / traceback / 空 stdout 收场。

### 9.3 结构化输出形状（**只在此声明一次**）

```json
{
  "tool": "review_evidence",
  "contractVersion": "REVIEW_EVIDENCE_CONTRACT_V1",
  "mode": "validate | collect",
  "ok": true,
  "exitCode": 0,
  "contract": {
    "schemaPath": "schemas/review-evidence.schema.json",
    "supportedSchemaVersions": [1],
    "errorCodes": ["EVIDENCE_VERSION_UNKNOWN", "EVIDENCE_SUBJECT_MISMATCH",
                   "EVIDENCE_STALE_SUBJECT", "REJECT"]
  },
  "violations": [
    {"code": "REJECT", "reason": "REQUIRED_FIELD_MISSING",
     "path": "$.unverified", "detail": "..."}
  ],
  "skeleton": null,
  "skeletonPath": null
}
```

`violations` 为空数组表示通过；`skeleton` / `skeletonPath` 只在 `collect` 模式下有意义。
信封形状**在所有失败路径上保持不变**；只有取值降级：当合同本身不可用（`SCHEMA_UNAVAILABLE`）时，
`contract.schemaPath` 回显调用方请求的路径，`contract.supportedSchemaVersions` 为 `[]`（没有可声明的
支持值域），`contract.errorCodes` 仍为四个已声明错误码。

### 9.4 `collect` 的权威边界（保持薄、非权威）

`collect` 只做两件事：用**调用方显式给出的 argv 值**装配一个符合 schema 的骨架；并对该骨架用**同一份合同**自检，不合规则失败关闭（fail-closed）。

```text
MUST NOT  取回任何 URL / 访问网络
MUST NOT  commandRef 指向的任何命令都被视为待执行对象（never an execution authority）
MUST NOT  枚举目录、递归发现文件、或写 --out 以外的任何路径
MUST NOT  populate / 自批 reviewer 权威字段
          （semanticScopeStatus 保持 null，reviewerDecisionRefs 保持空数组）
MUST NOT  断言任何轴的成功：骨架为 NOT_VERIFIED / INSUFFICIENT / ci.originalState = UNKNOWN
```

骨架的 `unverified[]` 必须显式列出"尚未收集/尚未核验"的每一项（空骨架不代表"无未验证项"）。
显式 `--out` 无法写入（父路径是文件、目标是目录、权限不足等）→ `REJECT`（`OUTPUT_NOT_WRITABLE`），
信封照常输出、退出码 1，且不写 `--out` 以外的任何路径（§8）。

### 9.5 `pattern` 关键字的求值语义（**只在此声明一次**）

schema 的 `pattern` 是 JSON Schema 的 `pattern`，其语义由 JSON Schema 规定为 **ECMA-262**：
`$` 断言**输入末尾**，`\d` 恰为 `[0-9]`。CLI 必须按同一语义求值；Python 的 `$` 还会匹配尾随换行之前、
Python 的 `\d` 还会匹配非 ASCII 数字，二者都会接受声明 pattern **不允许**的取值，因此**不得**直接用
Python 默认语义求值。声明的 pattern 文本本身不因求值方式而改写；被拒绝的是值（`PATTERN_VIOLATION`），
不是合同。

## 10. 消费方（只引用，不复制）

```text
references/ticket-lane.md §4             反例优先 TDD：本接口的红/绿证据形态
references/git-ci-integration.md §3      CI_STATUS 既有七值集（本合同按引用采纳，不改动）
references/codegraph-grounding.md §2.1   grounding 三模式语义 owner
references/review-and-repair-saturation.md §1
                                         评审分级（L0/L1/L2）与不自批纪律
references/project-continuity-contract.md §6.4
                                         machine-local 状态绝不 commit；本接口不建立第二状态源
```

**不建立第二账本**：本接口是证据的**声明形态**，不是状态源、不是 tracker、不是第二套 secret scanner。原始 runtime-local grounding receipt **不进仓**。
