# H5 可重放 ledger：候选合同

来源：`experiments/v1.2/mechanization-gap/experiment-protocols.md` §3.1–3.3；`experiments/v1.2/mechanization-gap/longhorizon-mechanism-map.md` M-02、M-06、M-12；`experiments/v1.2/mechanization-gap/failure-mechanism-map.md` F-013/F-014。此为设计，不是协议冻结，也不是已经实现的 harness。

## 编码与完整性

每条为一行 UTF-8 JSON，禁止重复 key；采用 RFC 8785 canonical JSON 字节、SHA-256。共同字段：`version`、`ledger_id`、从 0 连续的 `seq`、`prev_hash`、`type`、`event_id`、`timestamp`、`actor_id`、`payload`、`hash`；hash = SHA-256(canonical JSON of all fields except `hash`)；首条 `prev_hash` 为 64 个零。每一事件 ID 唯一，严格先引用后出现；未知版本、缺字段、错误类型、重复 ID/序号、缺序、乱序、链不匹配均 fail closed。写入必须单 writer 或经锁的 compare-and-append，持久化数据后再更新可信外部链尾锚点；断电恢复发现残行或锚点不一致则隔离、报告，不自动裁掉。hash 链自身不能阻止整体重写或截尾，外部不可由 worker 改写的持久锚点才检测这些攻击；签名、锚点存放与权限需预先指定。

## 记录及字段

所有 SHA 为完整 Git object ID，标明算法；仓库、worktree 使用由可信 orchestrator 分配的稳定身份及其真实路径，路径本身不进入盲审投影。

| type | 必需 payload（均含 evidence 的可验证内容哈希或原始证据引用） |
| --- | --- |
| `goal` | `goal_id`, `text_hash`, `authority_ref`, `repo_id`, `base_sha`, `predicate_specs`（版本、输入及 hash）；每 ledger 一条，序号 0。 |
| `episode_start` | `episode_id`, `arm`, `repo_id`, `worktree_id`, `head_sha`, `seed_head_hash`, `context_id`；只有匹配实际目标的启动检查通过后可执行。 |
| `state_claim` | `claim_id`, `episode_id`, `subject`, `value`, `repo_id`, `worktree_id`, `candidate_sha`, `predicate_id`, `predicate_version`, `evidence_refs`；执行者可声明，不可自证。 |
| `verification` | `verification_id`, `claim_id`, `independent_verifier_id`, `predicate_id`, `predicate_version`, `repo_id`, `worktree_id`, `sha`, `result`（PASS/FAIL/UNKNOWN）, `command`, `exit_code`, `evidence_refs`, `evidence_hashes`；验证者与该 claim 的生产者独立，可信调度器认证身份。 |
| `failure_evidence` | `failure_id`, `episode_id`, `kind`, `observed_exit`, `evidence_refs`, `evidence_hashes`, `impact`, `recovery_status`；包括环境故障，不可删除。 |
| `remaining_work` | `item_id`, `episode_id`, `description`, `status`（OPEN/BLOCKED/DONE_CLAIM）, `blocker_refs`, `evidence_refs`；DONE_CLAIM 仍需相应独立验证才可消除。 |
| `supersession` | `target_event_id`, `replacement_event_id`, `reason`, `evidence_refs`；只允许指向已存在事件及同语义 subject 的替代项，不抹掉历史，不自动授权替代项。 |
| `episode_end` | `episode_id`, `result`（COMPLETE_CLAIM/INCOMPLETE/ENV_BLOCKED）, `last_observed_sha`, `evidence_refs`；完成声明不是验收。 |

## Fold 和恢复

1. 从创世记录到外部锚点完整验链、验 schema、顺序、引用、唯一 episode 起止及身份。任何破损返回 `INVALID_LEDGER`，不返回部分可信状态。
2. 从可信外部读取当前 repo/worktree/HEAD；不能读取则 `UNKNOWN`，不可用先前声明替代。仅当 claim 与独立 PASS 验证的仓、worktree、完整 SHA、谓词及其版本、证据哈希全部一致，并等于当前实际目标时，将其加入 verified facts；其他 claim 显示为未验证/失败/过期。自报告 PASS、不同 worktree（即使 SHA 相同）、旧 SHA、其他 predicate 或不存在的 evidence 不准进入 state。后续 HEAD 变化使旧验证失效；重新验证新 SHA 后才可恢复。验证源文件或 artifact 的 hash 也须重新检查。
3. supersession 不删除被替代事件及失败史；替代 claim 必须重新通过上述验证。对于冲突的有效 claim，未指定且经验证的 supersession 时报告冲突并阻止 closure，不按时间静默取胜。
4. `accepted` 仅由可信 harness 检查**全部**冻结的任务谓词；对于声明需仓库闭环的任务，至少包括预期产物属于 merge commit、候选 ancestry 与 merge 对应、同一 merge SHA 的 post-merge CI 成功、全部必需验证与无未解决 blocker。F-013 的 merged + post-merge CI 是闭环最低要求而非任何任务的全部合同。缺失、未知、过期均不能接受；记录缺项，恢复时保留。隔离实验不可真实合并/查询 CI 时，应预先设计可审计的隔离替身并限制结论，不能声称真实仓库闭环。
5. `episode_start` 的 seed 是固定 goal、当前重放出的 verified facts、未解决 failure evidence、remaining work、blockers、目标绑定与链尾锚点；排除未验证事实但保留其状态和待查项。普通 memory 仅导航，不是事实；真实仓库/环境是 ground truth，verified state 是证据支持的解释。开始后仍再次检查 P1。

## 可测的 ledger 而非碰巧够用的快照

先在同一受控 fixture 中生成含通过、失败、过期及 supersession 的事件序列，将中间快照移除；从事件 + 独立锚点重放，逐字段对比预注册期望，再从仅终态快照尝试回答「某失败何时发生、为何 supersede、哪个验证因 SHA 变更过期」；缺少历史必须判不可回答。对账本每一事件做篡改、重排、删中间/删尾（带外锚点）均必须拒绝。正式变体每次新 episode 都记录重放链尾和 seed hash，随机抽查从零重放一致；仅有快照或没有链尾锚点则实验无效。该结构性检查不单独证明因果优势，优势仍由同任务配对比较 M1–M7 判断。
