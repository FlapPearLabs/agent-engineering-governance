# N7 — #45 Load-Bearing Gate Disposition (plan)

Owner decision (2026-10-29): start N7 after H2 harness v3 (#58) and its ledger record (#59).
Implementer Codex (gpt-6.1-terra); independent review Codex (gpt-6.1-sol, neutral brief);
Claude plans and accepts.

## Why

Issue #45 (E3): emptying `select` in `ruff.toml` turns the static correctness gate into a no-op,
and every governance check and the CI step stay green. The same failure class appears at three
levels (failure-mechanism-map F-009 assertion, F-010 gate, F-018 selftest; PATTERN-A "the empty
thing looks full"). N6.5 §0 P7 makes "the gate is load-bearing" a precondition of every protocol
that uses a mechanical gate as a quality criterion: H4 directly, and H5's M3 FALSE_CLOSURE.

```text
GATE_GREEN != GATE_STILL_ENFORCES_ITS_CLAIM      (EXECUTED != LOAD-BEARING)
```

## Scope and form (same pattern as N8 / #46)

- An experiment-level mechanism under `experiments/v1.2/gate-load-bearing/`, with tests in
  `experiments/v1.2/tests/test_v1_2_gate_load_bearing.py`.
- NOT a canonical change. `scripts/`, `references/`, `.github/`, `ruff.toml` and
  `requirements*.txt` are not edited; `scripts/validate_governance.py` is not wired.
- #45 stays OPEN / PROMOTION_PENDING. Promotion is a separate decision.
- Non-goals (from #45): no mutation testing, no coverage regime, no widening of the adopted rule
  set.

## Deliverables

1. **README.md — compare before choosing.** #45 names three candidates:
   - semantic positive control;
   - declared-intent binding;
   - gate reachability evidence.
   For each, state what it catches and misses against these hollowing variants:
   - `select = []`;
   - narrowing to `["E9"]`;
   - adding `per-file-ignores` or `extend-ignore` that covers the probe;
   - `exclude` or `extend-exclude` that covers the probe path;
   - pointing the CI command at another config;
   - an `ignore` entry that outlives its defect.

   Then justify the chosen smallest combination. A positive control alone cannot detect an
   `exclude` that covers only real code paths, so say what the design does about that.
2. **gates.json — a manifest of the mechanical gates CI runs** (`.github/workflows/*.yml`).
   - Each gate records its id, the exact command, its declared intent, and its positive
     control: a minimal known-bad input plus the place it is injected, chosen so the gate MUST
     fail.
   - Gates that cannot be given a positive control are listed with the reason. They count as
     `NO_POSITIVE_CONTROL`, never as load-bearing.
   - Minimum coverage:
     - ruff;
     - `validate_governance.py`, with at least one of its checks;
     - `validate_public_release.py` default mode;
     - `validate_public_release.py --selftest`, the F-018 level: show that a vacuous selftest
       item would be noticed, or record that it cannot be.
3. **probe_gates.py — the probe.**
   - **Setup:** it builds a scratch copy of a given tree (a git ref, via `git archive` or a
     detached worktree, never the caller's working tree).
   - **Per gate:**
     - (a) run the gate on the clean copy; expect PASS;
     - (b) inject the positive control; expect FAIL with the expected signal (for ruff, the
       expected rule code);
     - (c) report `LOAD_BEARING`, `GATE_NOT_LOAD_BEARING` (it passed on the known-bad input),
       `BASELINE_FAILING` (it failed on the clean copy) or `PROBE_ERROR`.
   - **Ruff declared-intent check:** the effective rule selection that ruff resolves for the
     probe file must equal the declared set. Use `ruff check --show-settings` on the injected
     file, or an equivalent supported command; never parse `ruff.toml` by hand as the only
     source.
   - **Fail closed:** any error is a failure, never a PASS.
   - **Output:** JSON on stdout, and a non-zero exit when any gate is not `LOAD_BEARING`.
4. **The probe's own positive controls** (#45 promotion item 2, "must not create an empty PASS of
   its own").
   - The test module builds deliberately hollowed copies:
     - `select = []`;
     - narrowed `select`;
     - an ignore covering the probe;
     - an exclude covering the probe path;
     - a `validate_governance.py` check that always passes, on a scratch copy only.
   - Each must be reported `GATE_NOT_LOAD_BEARING`. The intact tree must be `LOAD_BEARING` for
     every gate with a control.
   - A broken manifest entry (a missing positive control, or one whose injection does not apply)
     must be `PROBE_ERROR`, never PASS.
5. **results.md — the controls matrix as executed at the exact SHA**, with commands and verbatim
   outputs, and a replay of the #45 reproducer that shows the mechanism catches it.

## Acceptance (Claude)

- Every deliverable is present.
- Tests run with no model, no network and no write outside temp/scratch.
- Gates stay green: ruff, validate_governance 35/35, validate_public_release VIOLATIONS=0,
  scripts tests, and all experiments/v1.2 test modules.
- Claude reruns the #45 reproducer against the probe.
- The independent review is PASS, with no P0/P1/P2.

## After merge

- Ledger: N7 → CLOSED / EXPERIMENTAL_MECHANISM_READY.
- Mapping: N6.5 §0 P7 for H4 and H5.
- #45 gets a durable comment, but only with the owner's approval, because it is an outward
  action.
