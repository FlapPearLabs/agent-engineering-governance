# Route Reachability — progressive-disclosure route validation (V1.2 · N8 · issue #46)

> **EXPERIMENTAL MECHANISM. Non-canonical.** Lives under `experiments/v1.2/` on purpose —
> `PROMOTION_NOT_YET_EARNED` (see §9). Nothing here changes canonical behaviour or CI.
> Logical node: **N8 — #46 Route Reachability Disposition** (`experiments/v1.2/TREE_LEDGER.md`).
> The numeric claims in this file are re-derived from a live validator run by
> `experiments/v1.2/tests/test_v1_2_route_reachability.py`; they are not hand-trusted.

```text
ROUTE_DECLARED != DESTINATION_EXISTS != DESTINATION_LOADABLE
```

---

## 1. WHAT ISSUE #46 PROVED

A progressive-disclosure carrier can declare a route whose **destination does not
exist on the base where the route is used**. The declaration is syntactically
valid, every existing mechanical check stays green, and nothing observes that the
route cannot reach its intended content.

The recorded instance: during the H1 replay of task t04, the experiment carrier's
routing row for review/repair tasks pointed to `references/review-evidence.md`,
and at replay base `e1da1541…` that file did not exist (`references/` had 10
files; the target lands later via `2ed08f6`). A fresh agent following the route
found nothing, with **no signal that the route was unsatisfiable**.

Why nothing caught it (two axes, both outside existing coverage):

- `scripts/validate_governance.py` resolves markdown internal links for a fixed
  **canonical file list**; route targets are plain paths inside fenced code
  blocks of non-canonical carriers — outside that check on both axes.
- route validity is **base-relative**; a check run only at HEAD cannot see it.

## 2. WHAT THIS VALIDATOR CHECKS

Per declared route, against a **declared base** (a full commit-ish; there is no
HEAD-only mode):

```text
DESTINATION_EXISTS = `git cat-file -e <base>:<destination>` succeeds
ANCHOR_EXISTS      = only when the route declares an anchor; the anchor is a
                     literal substring of the destination blob at that base
LOADABLE           = DESTINATION_EXISTS and (no anchor declared or ANCHOR_EXISTS)
```

`LOADABLE` is a deliberately minimal definition: **the declared text is present at
the declared base**. It is *not* a claim that any agent found, read, or understood
it — that is beyond what a mechanical check can prove.

## 3. WHAT IT DOES NOT CHECK

- Not a dependency graph, package resolver, or build system.
- Not a documentation crawler: only the routes **declared in the manifest** are
  checked, not every path string in the repo.
- No semantic/fuzzy section matching: anchors (when declared) are literal substrings.
- No claim of agent comprehension (`EXISTS != UNDERSTOOD`).
- It does not require any carrier to declare anchors, and it does not modify any
  carrier, route, or reference.
- It does not run in CI; it is not wired into any gate (experimental status).

## 4. THE ROUTE CONTRACT (minimal, no DSL)

Manifest: `routes.json` — per route, at most three fields (`route_id`,
`destination`, optional `anchor`); the base is supplied by the invocation. Two
surfaces are declared: `S1` (the H1 experiment carrier whose route produced #46)
and `S2` (the canonical `AGENTS.md` dispatcher; its route set = the distinct
`references/*.md` paths it names). See §8 for the inventory and its bounds.

CLI:

```text
python3 experiments/v1.2/route-reachability/validate_routes.py --base <commit-ish>
        [--manifest routes.json] [--repo .] [--json]
```

Fail-closed by construction — an empty PASS is impossible:

```text
exit 0  ALL_ROUTES_VALID     >=1 route declared, all valid
exit 1  ROUTES_UNSATISFIED   >=1 route failed (DESTINATION_MISSING / ANCHOR_MISSING)
exit 2  MALFORMED_MANIFEST   schema/field/path-sanity violation; also the usage
                             error when --base is omitted
exit 3  NO_ROUTES_DECLARED   zero routes is never a pass; H2_PRECONDITION = FAIL
exit 4  BASE_UNRESOLVABLE    the declared base does not resolve to a commit
```

## 5. THE FROZEN RESULT MATRIX (live runs at three frozen bases)

```text
ROUTE_RESULT_MATRIX (re-derived from live validator runs; pinned by the test suite)
base=e1da1541eb2b11f1e44f972409abde701496f4b6  routes=22 valid=19 failed=3
  FAIL LEAN-07 references/review-evidence.md
  FAIL LEAN-12 references/static-tooling-profiles.md
  FAIL AGENTS-03 references/static-tooling-profiles.md
base=c08f6f8b3bbe57853a56adf3c2847e806bbb60a3  routes=22 valid=22 failed=0
base=6217cc0adcd6c064e8c74e670de6a081bdaba2f6  routes=22 valid=22 failed=0
```

Reading the three e1da154 failures (all base-relative, all verified by `git`):

- **LEAN-07** is the **issue #46 instance** — the route the task actually hit.
- **LEAN-12** and **AGENTS-03** target `references/static-tooling-profiles.md`,
  which also did not exist at `e1da154` (added later by `65113de`, 2026-09-28).
  Historical note: at the t04 replay the frozen carrier had **two** dangling
  routes at that base, but progressive disclosure is followed **per task** — the
  t04 task hit the review row, not the tooling row. The validator evaluates every
  declared route at the base, hit or not; that is the intended semantics.
- The frozen route set is the **current** declaration of both carriers; a route
  flagged at a base predating its own declaration is the price of a fixed,
  reviewable manifest. For H2's precondition question ("does the thing we will
  rely on exist at the base we will run on?") the manifest-fixed semantics is the
  correct one.

Matrix facts (provenance): `e1da154` = t04 replay base (references/ = 10 files);
`c08f6f8` = t01 replay base (references/ = 12 files); `6217cc0` = current main
(references/ = 12 files). All three are ancestors of main (checked with
`git merge-base --is-ancestor`).

## 6. CONTROLS — WHY THIS CHECK CAN FAIL

A check that cannot fail is not a check (issue #45's lesson, applied at the
disclosure layer). The test suite carries:

```text
T1  valid route + existing target            -> VALID
T2  missing target                           -> FAIL (DESTINATION_MISSING)
T3  zero declared routes                     -> NO_ROUTES_DECLARED, exit 3, never a pass
T4  historical base e1da154, #46 target      -> FAIL (the mandatory negative control)
T5  later base, same target                  -> VALID (both directions of base-relativity)
T6  declared anchor missing                  -> FAIL (ANCHOR_MISSING)
T6b declared anchor present                  -> VALID
T7  no declared anchor                       -> destination-only VALID
T8  malformed declarations (7 variants)      -> fail closed, exit 2
T9  unresolvable base                        -> fail closed, exit 4
```

T4 is the control the mandate singles out: if the validator ever returns PASS for
the historical case, it is wrong and the mechanism is void. T4 also proves the
validator cannot be HEAD-only: the target exists in the working tree while the
test runs, and the verdict must still be `DESTINATION_MISSING` because it resolves
against the declared base.

Control verdicts in the mandate's vocabulary:

```text
NEGATIVE_CONTROL_REACHABLE = YES   （e1da154 + references/review-evidence.md，rc=128）
VALIDATOR_FAILS            = YES   （exit 1；LEAN-07 = DESTINATION_MISSING）
POSITIVE_CONTROL           = PASS  （c08f6f8 与 6217cc0：22/22 VALID）
ZERO_ROUTE_FALSE_PASS      = IMPOSSIBLE（exit 3；H2_PRECONDITION = FAIL）
```

## 7. WHY BASE SHA MATTERS / WHY ZERO ROUTES != PASS / EXISTS vs LOADABLE

- **Base SHA**: route validity is `valid_at(base)`, not `globally_valid`. The same
  route is `DESTINATION_MISSING` at `e1da154` and `VALID` at `c08f6f8` and main.
  The validator resolves the given commit-ish to a full SHA and attributes every
  result to it (`BASE_SHA` in all output).
- **Zero routes**: `ROUTES_DECLARED = 0` never produces `ALL_ROUTES_VALID` — it
  exits 3 as `NO_ROUTES_DECLARED` with `H2_PRECONDITION = FAIL`. For H2 this is
  mandatory: H2's treatment (progressive disclosure) depends on routes existing,
  so an empty manifest must block, not pass.
- **EXISTS vs LOADABLE**: existence is a `git` object question and is
  deterministic. Loadability adds only the literal-anchor condition on top. No
  stronger claim (readability semantics, agent success) is made, because it is
  not mechanically checkable here.

## 8. ROUTE SURFACE INVENTORY (and its explicit bounds)

Two REAL route surfaces are declared. "Real route surface" means: a carrier whose
declared purpose is to dispatch an agent to further authority — not an ordinary
markdown link and not a general documentation reference.

```text
S1  ROUTE_SURFACE_ID = S1
    SOURCE_FILE      = experiments/v1.2/h1-hot-context/lean/CODEBUDDY.md（§4 路由表）
    KIND             = experiment carrier（按任务类型路由到 WARM references）
    DESTINATIONS     = 12 distinct references/*.md（9 行条件路由；其中 MICRO/LOW 行
                       声明"不加载"，不贡献路由）
    OPTIONAL_ANCHOR  = none declared
    DECLARED_BASE    = supplied per validation run（本文件矩阵 = e1da154 / c08f6f8 / 6217cc0）
    CURRENT_OWNER    = none（实验材料；此前无任何机械校对者）
    CURRENT_MACHINE_CHECK = none before this slice —— 这正是 issue #46 测到的缺口
    WHY REAL         = 它是 #46 的现场载体：一条路由行真的把 fresh agent 送进了死路径

S2  ROUTE_SURFACE_ID = S2
    SOURCE_FILE      = AGENTS.md
    KIND             = canonical dispatcher（"本文件不复制 references 全文；每节给出唯一详情指针"）
    DESTINATIONS     = 10 distinct references/*.md
    OPTIONAL_ANCHOR  = none declared
    DECLARED_BASE    = supplied per validation run
    CURRENT_OWNER    = （canonical 文件自身；其内部链接由既有 canonical 链接检查覆盖一部分，
                       而路由目标路径不在那个检查面内 —— 见 #46 的覆盖分析）
    CURRENT_MACHINE_CHECK = none before this slice（部分：既有链接检查只覆盖 md 链接形态 + 固定文件清单）
    WHY REAL         = 它是**规则自身声明的**渐进披露机制，不是顺带的文档引用
```

Deliberately excluded:

- Ordinary markdown links and general documentation references (owned by the
  existing canonical-link checker for canonical files).
- `deployment/MEMORY_POINTER_CANDIDATE.md` (deployment candidate): its pointers
  are prose inside a not-yet-deployed pointer; extraction from it is not bounded
  the way S1/S2 are. Recorded as a candidate surface for a future round, not
  included now.
- Nothing was fabricated: every S1/S2 route is extracted from the carrier's
  reviewed content and the extraction is re-run by the test suite
  (manifest ↔ carrier cross-check).

Adding or removing a surface is a review-visible change to `routes.json` plus the
tests; the manifest cannot silently drift from the carriers.

## 9. ISSUE #46 DISPOSITION AND WHAT REMAINS BEFORE CANONICAL PROMOTION

```text
N8_STATUS        = CLOSED / EXPERIMENTAL_MECHANISM_READY   (on merge)
ISSUE_46         = OPEN / PROMOTION_PENDING
PROMOTION_READY  = NO (not yet)
EVIDENCE_LEVEL of the mechanism's own validation =
  E3-class within this repo: mechanical reproducer + real negative + positive +
  fail-closed controls, all re-runnable offline at frozen bases.
```

Against issue #46's four promotion requirements:

1. **runs at a declared base, base-attributed** — met by design (`--base`
   required; per-route results carry the resolved base SHA).
2. **no empty PASS** — met (exit 3; `H2_PRECONDITION = FAIL`).
3. **independent review on the exact SHA + PR merge** — the outcome is recorded
   in this PR's own record (review round + merge commit) and, at closure, in a
   comment on issue #46. **This file deliberately does not vouch for its own
   PR** — the authoritative outcome lives in the GitHub record, not here (R3:
   `UNKNOWN != PASS`; a document must not reference an artifact that does not
   exist yet).
4. **evidence from at least one additional carrier/base** — **partially met**:
   an additional real carrier (S2) and additional bases (3) exist and were
   validated, but all evidence is **intra-repo** and there is still exactly one
   independently *reported* incident (#46 itself). Under the conservative
   reading ("a second independent carrier context, not this repo validating
   itself"), this requirement stays open.

Remaining before any canonical promotion proposal:

- out-of-repo / multi-repo carrier evidence (the V1.2 tree designates **N12
  real-project dogfood** as the natural place);
- a real carrier that declares an **anchor**, before anchor-checking could be
  promoted (today the anchor sub-feature has synthetic evidence only and no real
  route declares one);
- the §8 canonical change protocol (dual independent review) — deliberately not
  started here: **no canonical file is modified by this slice**.

## 10. WHAT H2 MAY NOW ASSUME (H2 route precondition)

```text
H2_PRECONDITION_ROUTE_REACHABILITY = PASS
  iff ROUTES_DECLARED > 0 AND VERDICT == ALL_ROUTES_VALID at the H2 base.

Established now: 22/22 VALID at 6217cc0 (the fork point candidate), with the
validator itself controlled (T1-T9). H2 must, at start:

  1. re-run the validator at H2's actual fork base (one command);
  2. extend the manifest with any routes the H2 carrier itself adds
     (freeze-then-validate; a new route is a manifest change + tests);
  3. treat any DESTINATION_MISSING / ANCHOR_MISSING as H2_PRECONDITION = FAIL —
     do not start the ablation on a base where the disclosure surface dangles,
     or the experiment measures an infrastructure defect, not disclosure cost.
```

## 11. REPRO

```text
python3 experiments/v1.2/route-reachability/validate_routes.py --base <BASE>
python3 experiments/v1.2/route-reachability/validate_routes.py --base <BASE> --json
python3 -m unittest discover -s experiments/v1.2/tests -v
```

---

*Provenance: this slice follows the N8 mandate (§0 identity binding: repo
`FlapPearLabs/agent-engineering-governance`, base `6217cc0…`). No canonical file,
no H3 artifact, and no H2/H4/H5 scope is touched. `tests/` changes are additive
to the existing experiment material suite.*
