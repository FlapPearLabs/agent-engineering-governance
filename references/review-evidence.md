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
P1-T05            消费三条评估轴，拥有其**核验行为与处置**；该行为在 §9.6 声明
                  （P1-T05 的行为段），第 3–4 节的字段合同不定义它。
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

因此第 3–4 节的字段合同**不**规定：某个轴取值应当阻断什么、`INVALID` 与 `TEMPORARILY_UNAVAILABLE`
如何按 cause 分类、复用何时合法、reviewer 字段谁能写（三轴取值的处置由 P1-T05 在 §9.6 落成行为）。
任何需要这些行为的判定的实现都属**越界**。

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

`REJECT` 附带机器可读的 `reason`，使子类可区分；四类 `reason` 分开（**结构**与**不充分**永不混同；
**结构**与**处置**亦互不相交，后者的唯一声明点是 §9.6.2）：

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
处置类（P1-T05 行为层，判定包内容）
                                 只声明于 §9.6.2；与上述三类互不相交
```

`SCHEMA_KEYWORD_UNSUPPORTED` 同时承载**声明 pattern 不可求值**这一情形（§9.5）：合同使用本 CLI
无法按 ECMA-262 忠实求值的构造时，按"未实现的算子"同一 reason 拒绝整份合同，而不是改用 Python 语义。

`authorityRefs` 的缺失（键省略或空数组）**不属于以上任何一类**：按 §3.1 它是充分性事实，由
`EVIDENCE_SUFFICIENCY` 轴承载；CLI 对它**不产出任何违规**，也**不**代 P1-T05 处置它。结构合法性
与证据充分性因此永不互相冒充：结构层只回答"这个包是否可按本合同解释"。

**判定顺序（冻结，先到先得）**：

```text
0  contract     声明的合同不可读 / 不可解析 / 不是合同对象 → REJECT（SCHEMA_UNAVAILABLE）
                合同不可用时不存在可解释的包判定，故先于一切包判定
                "合同对象"= JSON 对象 且 含非空根 `properties` 且 含非空 `schemaVersion` 值域
                （`const` 或 `enum`）；三者缺一即不是合同对象 → 仍在第 0 步被拒，
                不得降级成第 2 步的包版本问题（`EVIDENCE_VERSION_UNKNOWN`）
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
0  validate：全部检查通过（含包与目标 subject 一致，§9.1），**且**最终 P1-T05 处置允许 PASS（§9.6）
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

`violations` 为空数组表示通过。`skeleton` / `skeletonPath` 是**声明过的信封键**，因此在**每一条**路径上
都存在：`validate` 与一切失败路径上恒为 `null`（它们只在 `collect` 模式下有意义），`collect` 模式下
`skeleton` 为生成的骨架、`skeletonPath` 为显式 `--out` 的落盘路径（未给 `--out` 或落盘失败时为 `null`）。
信封形状**在所有失败路径上保持不变**；只有取值降级：当合同本身不可用（`SCHEMA_UNAVAILABLE`）时，
`contract.schemaPath` 回显调用方请求的路径，`contract.supportedSchemaVersions` 为 `[]`（没有可声明的
支持值域），`contract.errorCodes` 仍为四个已声明错误码。

本形状**不新增键**：P1-T05 的三轴处置结论走既有的 `violations` 清单（§9.6.3），因此本信封仍是唯一
声明点、也不存在第二个输出权威。

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

schema 的 `pattern` 是 JSON Schema 的 `pattern`，其语义由 JSON Schema 规定为 **ECMA-262**。CLI **必须**
按 ECMA-262 求值，且**不得在任何代码路径上回退到 Python 默认语义**——Python 的 `$` 还会匹配尾随换行
之前、`\d` 还会匹配非 ASCII 数字、`\s`/`\w` 是 Unicode 语义、`.` 只排除 `\n`，每一项都会接受声明
pattern **不允许**的取值，或拒绝它**允许**的取值。声明的 pattern 文本本身不因求值方式而改写；被拒绝的
是值（`PATTERN_VIOLATION`），不是合同。

**被翻译的构造**（与 Python 语义不同，必须翻译；这是本 CLI 实现且测试面逐项读回的构造清单）：

```text
ECMA262_TRANSLATED    $ \d \D \s \S \w \W
```

映射（右侧取值来自一份独立 ECMA-262 引擎的实测，不是 Python 的同名转义）：

```text
$   -> \Z                   输入末尾（不是"尾随换行之前"）
\d  -> [0-9]                ASCII 数字；类外 \D -> [^0-9]
\s  -> [\t\n\x0b\x0c\r \u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]
\S  -> 同一集合的补集（类外）
\w  -> [0-9A-Za-z_]         ASCII 词字符；类外 \W -> [^0-9A-Za-z_]
字符类内：\d \s \w 内联为该集合的成员；类内 \D \S \W 无法内联（补集不能内联进类）→ 按下方失败关闭
```

语义与 ECMA-262 **已知相同**、因而**原样保留**的构造：标点 identity escape
（`\^ \$ \\ \. \* \+ \? \( \) \[ \] \{ \} \| \/ \-`）、控制转义（`\n \r \t \f \v`）、
字符类、`{n}` / `{n,}` / `{n,m}` 量词、分组与交替、`^`、`(?:`、`(?=`、`(?!`。

**其余构造一律失败关闭**。CLI 不得用 Python 语义求值它们；必须把**该合同判为不可用**，以
`SCHEMA_KEYWORD_UNSUPPORTED`（与"未实现的算子"同一 reason，§8）拒绝，并在 `detail` 中点名该构造。
声明的失败关闭清单（测试面逐项验证引擎确实拒绝）：

```text
ECMA262_FAIL_CLOSED   . \b \B \1 \p{L} \cA (?<n>x) (?i) (?<=x)y \Z
```

其中每一项都是"交给 Python 就变成另一条规则"的例子：ECMA-262 的 `.` 排除整个 LineTerminator 集合
（含 U+2028 / U+2029），Python 只排除 `\n`；`\b` / `\B` 的"词字符"在 ECMA-262 中是 ASCII、在 Python
中是 Unicode；`\Z` 在 ECMA-262 中只是字面 `Z`，在 Python 中是输入末尾；`(?<n>x)` / `(?i)` / `(?<=x)y`
是被 Python 赋予不同（或额外）含义的分组构造。**宁可拒绝整份合同，也不给出一个近似答案。**

**声明的残余局限（不是未实现的声明，是两条引擎的已知差异边界）**：ECMA-262 在不带 `u` 标志时按
UTF-16 码元匹配，Python 按码点匹配，故对**含 U+FFFF 以上码点的取值**，量词计数可能不同。本条对本合同
**当前声明的六个 pattern 不可达**：它们的量词要么无界（`+`），要么只作用于 ASCII 字符类（`[0-9]` /
`[0-9a-f]` / `[0-9a-fA-F]` / `[a-z0-9-]`），因此码元与码点的计数差无法改变判决；该结论由独立引擎的
oracle 矩阵逐值核对（含星面码点取值），mismatch = 0。新增 pattern 若
使用受码元计数影响的构造（例如 `.` 或对可匹配星面码点的类施加有界量词），必须连带复核本条。

## 9.6 P1-T05 三轴核验处置（行为 owner：P1-T05；不重声明闭合集）

P1-T05 拥有的**三轴核验行为与处置**折叠进既有的 `validate` 流程，**不新增第三个 CLI 模式**：本 CLI 的公开 argv surface 恒为 §9.1 声明的 `collect` / `validate` 两个模式，`validate` 的输出信封恒为 §9.3 声明的形状。本节写的是**处置规则**，不是字段名或闭合集——三轴字段名与闭合值域的唯一声明点仍是 §3 / §4，本票只**引用**，不重声明（CE-30）。

### 9.6.1 处置在判定顺序中的位置（只在此声明一次）

```text
contract load → pack parse → version → structure → subject 期望/绑定
             → 声明的结构轴 → P1-T05 三轴处置 → 结构化输出 → 退出码
```

处置**只在**结构层（§8 第 0–5 步，含 §9.1 的 subject 期望完整性与绑定比较）**全部通过之后**运行：任何更早的失败原样回显其违规、**不产出任何处置条目**（§9.6.3），**不进入处置**。因此 `repo` / `baseSha` / `candidateSha` 任一不符的包**永不**到达行为层 PASS，`STRUCTURALLY_VALID = NO` 的包同样如此。`evidence_disposition(pack, schema)` 是这一行为的内部入口（行为助手，**不是**公开子命令，也不构成第二个 CLI / 输出权威）。

`--allow-placeholders` 是**唯一**声明的例外，且**不运行**处置（§7：占位符形态模板不是对一个具体候选的主张）：该模式下退出码只由结构层决定，也不产出任何处置条目。

### 9.6.2 处置规则（P1-T05 行为；值域引用 §4）

`evidence_disposition` 把三轴取值与 CI 观测事实消费为"是否允许 PASS"的结论；三条轴**互不折叠**，并以如下规则处置：

```text
允许 PASS  当且仅当：结构轴 = 是  且  来源轴 = 已核验  且  充分性轴 = 充分
                    且  CI 已观测（run 非空）且 originalState = PASS
                    且  合同为 artifacts[].contentDigest 声明的 pattern 可用
                    且  全部 artifacts[] 的 contentDigest 按该 pattern 合法
                    且  全部 checks[].artifactRefs 都能在 artifacts[] 解析

阻断 PASS（且不互相冒充）的情形（reason 码）：
- 结构轴 != 是                          STRUCTURALLY_VALID_NO
- 来源轴取值越出 §4 闭合域（轴坍缩；
  例如把充分性轴的"不充分"值误置到来源轴）   AXIS_COLLAPSE
- 来源轴 = 作废                          SOURCE_INVALID
- 来源轴 = 临时不可达                    SOURCE_TEMPORARILY_UNAVAILABLE
                                        （保留原值，绝不改写为"作废"）
- 来源轴 = 未核验                        SOURCE_NOT_VERIFIED
- 充分性轴 = 不充分                      EVIDENCE_INSUFFICIENT
                                        （与"已核验"是合法组合，非矛盾；阻断但不报轴坍缩）
- CI run 为空（未观测到 CI）            CI_NOT_OBSERVED
- CI originalState != PASS              CI_NOT_PASS
- artifact contentDigest 形状非法        DIGEST_MALFORMED
- check 引用的 artifact 不在 artifacts[] MISSING_ARTIFACT
- 合同未提供可用的 contentDigest pattern  DIGEST_PATTERN_UNAVAILABLE
                                        （此时不问值是合法还是非法：**不假定**任何本地形状）
```

要点（与 §2 / §4 一致，本票只把它落成行为，不发明新的状态机族）：

- `已核验 + 不充分` 是**合法且必须被接受的组合**，仅因充分性不足而阻断 PASS，绝不被判为矛盾，也绝不报 AXIS_COLLAPSE。
- `临时不可达` 与 `作废` **两个成员各自独立、各自可表示**；处置只记录 `SOURCE_TEMPORARILY_UNAVAILABLE`，**从不改写为** `SOURCE_INVALID`（不可达 ≠ 已作废）。`临时不可达 + 充分` 不构成另一条被声明的矛盾规则：处置逐轴记录（来源轴阻断 PASS），**不**额外发明跨轴判定。
- `不充分` **只属于**充分性轴；它出现在来源轴即 AXIS_COLLAPSE，是轴坍缩，不是合法来源取值。
- CI 的 `originalState` 沿用 §4 的既有七值集（本合同按引用采纳，不改动）；本行为**不**发明第二个竞争性 CI 状态机，也**不**把 `NOT_TRIGGERED` / `UNKNOWN` / `SKIPPED` / 已知基线失败 等任何非 PASS 状态折叠成 PASS。
- `artifacts[].contentDigest.pattern` 与其余闭合集一样**只有一处声明点**（§3 与其机械形态 schema）。消费方**不得**自带一份局部副本作为替代：合同未声明该 pattern、或声明的 pattern 不是可求值的字符串时，处置**失败关闭**并报 `DIGEST_PATTERN_UNAVAILABLE`——**不是**退回一份本地记住的形状，否则该副本自身就成了竞争性声明点（CE-28 / CE-30）。该 pattern 按 §9.5 的同一 ECMA-262 求值语义求值，**不存在**第二条 Python `re` 求值路径：同一 pattern 与同一取值在结构层与行为层必须得到同一判决。
- 退出码**跟随真实处置**：`validate` 的退出码为 0 当且仅当结构层与 subject 层全部通过**且**最终处置允许 PASS；一个结构合法、subject 绑定成功但 `未核验` / `不充分` 的包退出码为 1（不是 0）。`collect` 的退出码仍只描述骨架自检与落盘（§9.4）。阻断条目按 §9.6.3 走既有的 `violations` 清单。

### 9.6.3 处置结论的报告位置（只在此声明一次）

处置结论**不新增信封键**：`validate` 一旦进入处置而处置阻断 PASS，条目的 `reason` 取自 §9.6.2 的
处置码，作为 §9.3 既有 `violations` 清单的一部分输出，`ok` / `exitCode` 随之为 `false` / `1`。

```text
{ "code": "REJECT", "reason": "<§9.6.2 的处置码>",
  "path": "$.SOURCE_VERIFICATION_STATE | $.EVIDENCE_SUFFICIENCY | $.ci.* |
           $.artifacts[].contentDigest | $.checks[].artifactRefs", "detail": "..." }
```

要点：

- `violations` 是**这次调用**的唯一失败清单：为空 ⟺ `ok` 为 `true` ⟺ 退出码 0。处置条目与结构条目不
  混淆：处置类 `reason`（§9.6.2）与结构类 / 声明类 / 调用类（§8）**互不相交**。
- 处置**允许** PASS 时不产出任何条目，`violations` 为空——因此"未核验"这类包不会被伪造成结构违规。
- 处置未运行时（合同不可用、包缺失/不可解析、版本未知、结构违规、subject 未声明或不符、占位符模式）
  不存在任何处置条目：更早的失败先到先得（§9.6.1）。
- 处置记录**原样回显**包自己声明的来源轴取值（含 `临时不可达`），处置过程绝不改写它。
- 本段只承载**机器事实**：它绝不写入 / 升格 `semanticScopeStatus` 与 `reviewerDecisionRefs`（那两个字段的权威属 P1-T07，§3.1）。

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
