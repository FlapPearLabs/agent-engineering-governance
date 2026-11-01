# H5 — build round 1 (brief)

Owner decision (2026-10-29): proceed with H5 using the design's recommendations
(`OWNER_DECISIONS.md`).

This round builds mechanism and runs mechanical, read-only measurements only:
- no model, opencode or driver runs;
- no runs root;
- no protocol freeze.

Implementer Codex (gpt-6.1-terra); independent review Codex (gpt-6.1-sol); Claude accepts.

The work is split into two parallel tasks with disjoint files:

## Task L — the ledger (T63 core)

Write `experiments/v1.2/h5-verified-state/ledger/ledger.py`, implementing
`design/LEDGER_SHAPE.md` as pure Python with no dependencies outside the standard library.

**Encoding and integrity**
- One canonical-JSON record per line (RFC 8785 subset sufficient for the record types: sorted
  keys, no insignificant whitespace, UTF-8, no duplicate keys, reject floats or define them).
- SHA-256 hash chain.
- The external chain-tail anchor is a separate file passed by path. The appender cannot write
  it; a separate `anchor()` call does.

**Record types and append**
- The eight record types from LEDGER_SHAPE with their required payload fields.
- `append` validates schema, `seq`, `prev_hash` and reference order: a referenced event must
  already exist.

**Fold: `fold(ledger, anchor, actual_target)`**
- Any break (tamper, gap, reorder, truncation behind the anchor, unknown type, dangling
  reference) → `INVALID_LEDGER`, never a partial state.
- A claim enters verified facts only with an independent PASS verification whose repo,
  worktree, full SHA, predicate, version and evidence hashes all match, and which equals the
  current actual target. Otherwise it is excluded and listed as unverified.
- Stale SHA (M2) is rejected. Wrong worktree or SHA (M1) is detected.
- Supersession keeps history. A conflict without a verified supersession blocks closure.

**Closure: `closure(fold, predicates)`**
- Per Q4, against a stand-in: the expected artefact is in the merge commit, the ancestry
  matches, there is a post-merge CI success for the same merge SHA, all required verifications
  exist, and there are no open blockers.
- Its outputs carry `CLOSURE_SOURCE = STAND_IN`.

**Seed: `seed(fold)`**
- For a fresh episode, per LEDGER_SHAPE §Fold step 5.

**Tests:** `experiments/v1.2/tests/test_v1_2_h5_ledger.py`.

| Kind | Cases |
|---|---|
| Positive controls | Each predicate passes on a correct fixture. |
| Negative controls (each must fail closed) | Tampered byte, deleted middle record, reordered records, truncation behind the anchor, an anchor the appender rewrote, a claim with no verification, a verification by the claim's own producer, a stale SHA, the wrong worktree, a supersession to an unknown event, a conflicting claim, closure with CI on a different SHA, closure with an open blocker. |
| Ledger vs snapshot (the §3.1 distinction) | A fixture with pass, fail, stale and supersession events. Replaying the ledger answers "when did the failure happen, why was X superseded, which verification went stale", while a terminal snapshot provably cannot. |

## Task C — task chainability (T62, Q1 = A)

Write `experiments/v1.2/h5-verified-state/tasks/CHAINABILITY.md` and `measure_chain.py`.

- **What to check:** read-only, on a scratch clone, whether H2's real tasks (the freeze-v3 ten
  tasks f01–f10 and their frozen oracles, `freeze-v3/run_acceptance_v2.py::accept`) can be
  chained into multi-step tasks. A chain needs:
  - step k's candidate is step k+1's base, or is reachable from it in a way the oracle
    tolerates;
  - each step's oracle is independent;
  - each step REJECTS its own base and ACCEPTS its own candidate;
  - the end state is mechanically checkable.
- **Outcome:**
  - At least 2 valid chains: report them.
  - Fewer: report Q1 → B, and list candidate real historical multi-step sequences from git
    history with the same measurements.
  - Never fabricate a chain.
- **Tests:** `experiments/v1.2/tests/test_v1_2_h5_chain.py`. Adversarial cases: an oracle that
  accepts the base, a broken link, a dependent oracle. Each must be reported as unchainable.

## Rules (both tasks)

- Write only the files named for your task.
- Never touch canonical files, `scripts/`, `references/`, `.github/`, `freeze-v2/`,
  `freeze-v3/`, other experiment directories, `design/`, or `TREE_LEDGER.md`.
- No `/Users/<name>` paths in committed files.
- No network, no models, no opencode, no `run_*.py`. Write only to temp/scratch.
- Mark runtime claims MEASURED (with the command) or ASSUMED.
- Gates before committing, with PYTHONPATH unset and TMPDIR set to a physical path:
  - ruff;
  - `scripts/validate_governance.py` 35/35;
  - `scripts/validate_public_release.py` VIOLATIONS=0;
  - your test module.
