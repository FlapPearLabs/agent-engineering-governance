# H2 closure — results export and closure report (plan T47–T48)

Implementer: Codex (gpt-6.1-terra). Acceptance: Claude. Independent review: Codex (gpt-6.1-sol).
The freeze is 4aa2e7b. The twenty counted runs execute from a clean clone of 4aa2e7b into the runs
root `<RUNS_ROOT>` (path given at hand-off); they are LIVE while T47 is built — never write to, lock,
signal or run anything against that runs root except the read-only export in T48.

NEVER TOUCH: everything under `experiments/v1.2/h2-lazy-disclosure/freeze-v2/` (the frozen materials;
`freeze-v2/build_manifest.py check` must still PASS after every commit), canonical files
(AGENTS.md, RULES.md, references/, scripts/, schemas/, templates/, .github/), other experiments.

## T47 — export tooling and closure-report generator (now, before the results)

Write scope: `experiments/v1.2/h2-lazy-disclosure/results-v2/**` (new),
`experiments/v1.2/tests/test_v1_2_h2_results_v2.py` (new).

1. `results-v2/export_results.py <runs_root> --out <dir>`: read-only over the runs root. Copies, for
   the record, `registry-v2.jsonl`, `attempts-v2.jsonl`, `scheduler-v2.jsonl`,
   `reachability-v2.jsonl`, and per registered run: `verdict.json`, `access-audit.json`,
   `audit/audit.json`, `run.json`, `report.md`; every local absolute path is replaced by a stable
   placeholder (`<RUNS_ROOT>`, `<HOME>`, `<PY>`, `<GOVERNANCE>`) so the public-release gate passes,
   and the export records the sha256 of every ORIGINAL file and of every exported file. It verifies
   each run's audit/verdict files against the hashes in its registry line (as aggregate_runs.py
   does) and refuses on a mismatch. It then imports (never copies) the frozen
   `freeze-v2/aggregate_runs.py` and writes `aggregate.json` exactly as that program outputs it.
2. `results-v2/render_closure.py <export dir> --out <md>`: renders the closure report from the
   export only (no hand-typed numbers): question and pre-registered design (link protocol-v2.md),
   all pre-registered deviations and user decisions (bounded concurrency, frozen model, denied
   attempts are evidence — quote the decision lines from protocol-v2), a table of all twenty runs
   (task, arm, attempts, mechanical verdict, audit correctness, final verdict, denied attempts,
   reasons), the valid pairs, the aggregate result token and its `decided_by`, the per-arm denied
   attempt totals, the disclosed confound (the repository's own AGENTS.md is attached to both arms
   on first read; a null difference is INSUFFICIENT_EVIDENCE), the limitations (one run per task per
   arm, one model and runtime, cohort-only validity), and — only when the token is
   `SAFE_CANDIDATE_PENDING:<rules>` — a section that lists the pending rules with the evidence a
   human needs to decide them and states the result as pending, never SAFE.
3. Tests (no model, no live runs root): a synthetic runs root built in a temp dir with the frozen
   registry format; the export sanitises every absolute path; a tampered audit file is refused;
   the rendered report's numbers equal the aggregate's; each of the four result tokens renders.
   Also run the export read-only against the pilot runs root `<PILOT_ROOT>` (path given at
   hand-off) as a smoke test and keep the output OUT of the repository.
4. Gates (foreground, PYTHONPATH unset, TMPDIR resolved): ruff; validate_governance (35/35);
   validate_public_release (VIOLATIONS=0); `freeze-v2/build_manifest.py check` PASS; the new test
   module; `experiments/v1.2/tests` full suite. Commit only if all pass.

## T48 — results (after the runs are COMPLETE; dispatched separately)

Run the export into `results-v2/r2-4aa2e7b/`, render `experiments/v1.2/h2-lazy-disclosure/
freeze-v2-closure-report.md`, update `experiments/v1.2/TREE_LEDGER.md` N2 per the result
(CLOSED with the result token), full gates, commit.
