# CONVERGENCE ARBITER — P1 Stage 1 (scratch / evidence)

## Inputs read or executed
- `issue10.json` (.body), `issue11.json` (.body), `SPEC_60209cd.md` (REQ-W1-01 §3.1, REQ-W1-03, §16.8.4)
- laneA @ `e1da1541…`: `references/ticket-lane.md` §3, §3.1.1–§3.1.4; diff vs base `8c78e98`
- laneB @ `74679094…`: `scripts/review_evidence.py`, `schemas/review-evidence.schema.json`,
  `references/review-evidence.md` §9.1–§9.5, `scripts/tests/test_review_evidence_contract.py` (test_46–51); diff vs base
- review records: `review/RV-B1c-final/`, `review/RV-B2-independent/`
- **executed**: `ecma262_pattern` differential vs V8 (`new RegExp`, no `u`) — 20 hand-picked class patterns,
  then 442 randomized class patterns × 17 values = 7,514 evaluations; frozen-schema pattern inventory scan;
  `git status --porcelain` / `git rev-parse HEAD` on both worktrees.

## Q1 evidence
Guard: `scripts/review_evidence.py:176-192`. Root cause = POSIX "leading `]` is a literal in a class" rule.
ECMA-262 has no such rule: `[]` is an **empty class** (matches nothing), `[^]` matches anything.

Differential result (V8 oracle):

| pattern | translated | V8 | Python | verdict |
|---|---|---|---|---|
| `^[]]$` | `^[]]\Z` | never matches | matches `]` | DIVERGENT |
| `^[^]]$` | `^[^]]\Z` | matches `x]` | matches any single non-`]` | DIVERGENT (12/17 values) |
| `^[]a]$` | `^[]a]\Z` | never matches | matches `]`,`a` | DIVERGENT |
| `^[a]]$`,`^[0-9]]$`,`^[^a-z]]$`,`^[\]$`,`^[[]$` | — | — | — | identical |

Randomized scan: **28 / 28 mismatches have a class-leading `]`** → single root cause.
60 refused (fail-closed, correct), 15 Python-uncompilable → also refused. **0 other divergences.**

Frozen 6 patterns: **none** contains `[^?]` → removing the POSIX rule **provably cannot** touch the frozen contract.
`--schema` is a declared argv surface (§9.1:240-249, "override the contract path"); §9.5 forbids Python-semantics
fallback "on **any** code path". No in-repo production caller passes `--schema` (only tests, with missing/dir/non-JSON paths).
`test_50` pins `len(patterns) == 6`.

## Q2 evidence
`TEST_ONLY_CALLERS` appears **only** in `SPEC_60209cd.md:187` (REQ-W1-03 ② block, 7 names).
Absent from `SPEC_60209cd.md:144-153` (REQ-W1-01 ② block, 6 names), from `issue10.json` CANONICAL_TERMS_USED,
and from `references/ticket-lane.md` §3.1.2 (6 names) — verified by `grep -rn` over both worktrees: zero hits.
`SPEC_60209cd.md:1701` records it as **"未处理（按指令排除）：`TEST_ONLY_CALLERS` 命名"** → the owner has consciously parked it.
P1-T01 `INVALIDATED_BY`: a later change to frozen field names is a **parent-spec change → new SHA** that invalidates
`e1da1541…`.

## Worktree hygiene
laneA `e1da1541eb2b11f1e44f972409abde701496f4b6` — `git status --porcelain` empty.
laneB `74679094c7cb3a44bab3fdddec9c340cad395214` — empty.
