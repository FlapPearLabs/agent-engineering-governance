# [R2-REDACTION] machine paths replaced with the documented placeholder form
# ('/(?:Users|home)/songshiyao' -> /Users/<LOCAL_OS_USERNAME>, which the public-release rule
#  UNIX_USER_HOME deliberately does not match). Original preserved outside the repo.
# origin sha256 (unredacted original) = e559ea3b69241f0e43aef8a16dada7f2aa314faa989e1e3f9419bc6e56392a5e
# source: N2.1 PART 1 analysis — why C2 and C3 exclude r01 / r03 / r06

# N2 ▸ Eligibility Schema Revision — PART 1：C2 ∧ C3 排除机制诊断

- 时间：2026-10-14（GMT+8）
- 节点：N2 — H2 Lazy Skill / Progressive Disclosure ▸ **Eligibility Schema Revision**（START HERE）
- 性质：**analysis only** —— 未修改 schema、未改 freeze、未跑 H2-R2、未 merge、未碰 canonical
- 依据：`protocol.md` §3/§5(P7)/§9/§10、`task-registry.json#eligibility_rule`（v2）、
  `round-2-freeze.json`（含 revision/INSUFFICIENT）、`precondition/p7-gates.txt`、
  `N2_ELIGIBILITY_FEASIBILITY.md`（r01/r03/r06 全部实测数字）、`precondition/p1-p2-dryrun.txt` [26]–[29]

---

## 0. 形式化：把 C2/C3 写成谓词

对任务 T（base B、delta D）与某条验收命令 G（确定性函数：tree → {PASS, FAIL, ABSENT/ERROR}）：

```
C2(G,T) := G(B) = PASS
C3(G,T) := 存在语义读法两种：
   (i)  判据相对 base 移动：  G(B+D) ≠ G(B)
   (ii) 判据能区分交付物对错： 正确 D 与错误 D' 在 G 上 verdict 不同
```

**C3 的歧义必须在 revision 中消解**，因为它决定诊断：

- 取 **(i)** 时，`C2 ∧ C3 ⟺ G(B)=PASS ∧ G(B+D)=FAIL` —— 即**正确的 delta 必须使一个 base-green 的门变红**。这对任何"正确实现"的任务都是自我矛盾（那等于要求修复造成回归）。⇒ 阅读 (i) 使 C2 ∧ C3 恒不可满足，故不是用户意图。
- 取 **(ii)** 时，C2 = base 环境有效性（门在起点为绿），C3 = 门对交付物有判别力（由 negative control 证明）——自洽，且与 C5 呼应。**本诊断采用 (ii)**，并在下节标注 (i) 下的差异。

---

## 1. r01 —— **repair task**：被 C2 排除

事实（实测）：base R1 = FAIL（509 tests / 508 pass / **1 fail，且失败者恰是目标文件** `test/p1-t14-cross-group-synthesis.test.mjs`，`ERR_MODULE_NOT_FOUND: lib/pre-synthesis-guard.mjs`）；delta R1 = PASS（539/539）。

```
G* = cd research-orchestration && node --test test/*.test.mjs
C2(G*) : FAIL   ← 排除发生在这一项
C3(G*) : ✓      失败⊆{目标文件}，修复后归零；错误 delta（删一个 lib）⇒ 复红（已实测）
C4(G*) : 按 replay 原样 ✗ —— delta 自己改写 oracle 文件；冻结后 ✓（实测：冻结候选测试 @ base=FAIL、@候选=PASS）
```

**机制**：repair 的定义就是「某门在 base 为红、修复后归绿」。C2 要求 base 为绿 ⇒ 与 repair 的定义直接冲突。这不是 r01 的缺陷，而是 **C2 把「base 状态确定且可归因」写成了「base 状态必须为绿」**——前者是环境有效性，后者只是 invariant 型任务的特殊情况。

**revision 所需**：把 C2 改为 **base 状态三值可归因**（GREEN / RED / ABSENT）＋归因规则（该 RED 必须由任务声明的缺陷造成，而非 harness 投递造成）。后者已有现成机械实现：`[29]` 的双锚点 `DELIVERY_DELTA`（pre/post-delivery 零 worker 改动对测，GREEN→RED 判为投递污染）。

---

## 2. r03 —— **regression guard / validator task**：被 C3（＋C4）排除

事实（实测）：base 侧 4 门全绿（32/32；423 OK；12 OK；rc=0）→ delta 侧仍全绿（34/34；441 OK；12 OK；rc=0），**verdict 逐项相同**；唯一判别的门是 `ruff check .`（base 19 errors → delta 0）与候选自带 t17（absent → OK），**二者在 base 均不满足 C2**。

```
对已存在的 base-green 门（suite / validate_governance）:  C2 ✓,  C3 ✗  ← 排除
对新装的 guard 门（ruff / t17）:                          C2 ✗,  C3 ✓  ← 排除（另一项）
```

**机制（本候选最特殊）**：交付物**本身是一个探测器**。探测器的价值不是「树满足 P」，而是「树将**检出** ¬P」。因此：
- 它对自己的合规树**必然**判绿 —— 于是相对 base 移动量为零（阅读 (i) 下 C3 恒 ✗）；
- 它的语义**由 worker 写**（`ruff.toml`、t17 都是交付物）—— 实测 `select = []` ⇒ `ruff check .` **rc=0「All checks passed」**，即 C4 被直接击穿；
- 它还改了 `scripts/validate_governance.py` 本体（check 数 32→34），故 validator 也不能充当 oracle。

**revision 所需**：guard 型任务只能用**样本式验收**（specimen-based acceptance）：
框架提供**成对样本**（合规样本 + 违规样本，均为冻结字节），要求 worker 的交付物对二者给出**相反的 verdict**。
这样 C2 落在「样本对在 base 上的状态可判定」，C3 落在「违规样本必须被检出」，C4 落在「样本由框架提供、worker 不可写」。

**此概念协议层已有前身**：§5 P7「门完整性」＋「无法证明承重的门 ⇒ 其 PASS 不得计为高置信证据」，并**预先声明** ruff 的**掏空方向不可靠（#45）**——本次测量正是该声明的实测复现。缺口在于：**eligibility schema 没有复用 P7 的"承重"概念**，只保留了 P7 的「注入必红」（teeth）方向，而没有「掏空必红」（vacuity）方向。

---

## 3. r06 —— **coverage gap task**：被 C3 排除（由构造）

事实（实测）：base 39 文件、**无测试面**（`unittest discover -s scripts/tests` 直接 `ImportError: Start directory is not importable`）；唯一门 `validate_governance.py` 在 base **23/23 PASS** → delta 仍 **23/23 PASS，逐项相同**；新增的 8 个文件对门**完全不可见**。

```
G = python3 scripts/validate_governance.py
C2(G) : ✓
C3(G) : ✗ ← 排除（交付物不存在任何可观测签名）
```

**机制**：coverage gap 的**定义**就是「这块内容当前没有任何门在观测」。因此任何现存门都对它零敏感 —— 不是 r06 的资料问题，而是**任务类型与 C3 的定义性冲突**。

**revision 所需**：要么由框架提供**观测该交付物的冻结符合性 spec**（例如把 adapter 合同写成可执行的 conformance 检查，样本由框架提供），要么该任务只能被排除。**在本轮的约束下（不改 task set / 不改 scoring）r06 应保持 NON_ELIGIBLE** —— revision 不必为了让 r06 通过而放宽判据。

---

## 4. 三个原型各被**不同**的合取项排除（这是 revision 的关键结论）

| 原型 | 被排除项 | 机制 | revision 必须能表达 |
|---|---|---|---|
| r01 repair | **C2** | base 为红是任务定义 | base 状态三值（GREEN/RED/ABSENT）＋归因（DELIVERY_DELTA 双锚点） |
| r03 guard | **C3（＋C4）** | 交付物是探测器；其自证语义由 worker 写 | **样本式验收**（冻结的合规/违规样本对，要求相反 verdict） |
| r06 coverage | **C3** | 交付物定义上不被任何门观测 | 冻结的符合性 spec；无则排除（本轮保持 NON_ELIGIBLE） |

⇒ **只放宽 C2 一项，只能救回 r01；r03/r06 仍被 C3/C4 挡住。** 三轴必须一起改，否则 revision 无效。

---

## 5. schema 层的根因：C1–C5 假设了「单一验收对象」

C1–C5 隐含：存在**一个**对象 G，同时满足 base-green、worker 不可写、对 delta 敏感。
三个原型分别击破**不同**的合取项：repair 破 base-green；guard 破 worker-不可写；coverage 破 delta-敏感。
因此 revision 的最小轴集是**四条**（而非修补 C2 一条）：

```
A. BASE_POLARITY        : GREEN | RED | ABSENT，附归因（谁造成该起始状态）
B. OBSERVABILITY        : 交付物必须存在可观测签名（门 verdict 随交付物正确性移动）
C. ORACLE_AUTHORSHIP    : FRAMEWORK | WORKER_PINNED_BY_SPECIMEN | WORKER_UNPINNED(⇒不合格)
D. VACUITY_RESISTANCE   : 空交付物 / 空洞但合法的交付物 必须使验收判红
                          （= #45「掏空方向」的一般化：ruff 的 select=[] 已实测为绿）
```

**已有可复用资产**（无需从零建）：`DELIVERY_DELTA` 双锚点（[29]）、frozen-oracle 机制与 `oracle_policy`（registry）、`TASK_VALIDITY_STATUS` 三值层（v2）、协议 §5 P7 的「承重证明」与 #45 声明。

**须先消解的歧义**：C3 的两种读法（§0）。取 (i) 会使 C2∧C3 恒不成立（要求正确修复造成回归），故 revision 必须把 C3 明确写为「判别交付物对错」的形态，并把「相对 base 移动」降级为其中的一种情形（repair 才有）。

---

## 6. 与既有 frozen 文本的关系（revision 会触及的锚点）

- `task-registry.json#eligibility_rule` = ELIGIBILITY_RULE_v2（`frozen: true`），本次要改的是它 ⇒ **属于 §9 的冻结面**，按 §9 语义：修改冻结面 ⇒ 须走 ROUND_INVALID 判定或走「Round-2 freeze v2」重开（用户 TREE 的下一节点正是 Freeze v2，顺序自洽）。
- `round-2-freeze.json#revision.INSUFFICIENT.next_action` 现文本写的是
  「add real task(s) … each with its own historical oracle and **a verified base-GREEN property**」
  —— 该句**内建了 C2-字面口径**。若 revision 采纳 base 三值口径，这句必须随 Freeze v2 一并重写，否则 freeze 文本与 schema 互相矛盾。
- 同一份 freeze 的 `aggregate_set` 与 `counts_toward_h2_aggregate` 存在一处口径差：plan 行带该 flag 的为 **4 行**（t01×2 + t02×2，按 task validity 生成），而 freeze 的 `aggregate_set.aggregate_eligible_rows` 为 **2 行**（再与可执行性取交）。两处都对，但**未标注维度差**，Revision 应一并定义「aggregate 成员 = validity ∧ executability」的单一算法以免再次分叉。

---

## 7. 本轮未做（明确边界）

未修改任何 schema / registry / freeze / protocol；未新增或删除任务；未改 scoring / route / treatment；未执行 H2-R2；未 merge；未触碰 canonical。
下一步（待指令）：把本诊断转成**协议层提案**（experiments/v1.2/** 内的 revision 草案）→ 独立评审 → 才动 frozen 面 → 才能进入 Freeze v2 节点。
