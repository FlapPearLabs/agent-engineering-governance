# H4 exploratory pilot harness — build spec

STATUS = EXPLORATORY. Owner approved building this harness and, separately later, a capped
exploratory run (owner message 2026-11-01). It does **not** change N4 (`PROTOCOL_NOT_STARTABLE`),
does not freeze the H4 protocol, and nothing it produces is formal evidence or counts toward
the 4 real tasks. Tasks are synthetic, made by a model, and labelled `SYNTHETIC_EXPLORATORY`.
Purpose: exercise the 3-arm flow end to end, learn cost and variance, find leaks, size a later formal run.

## Roles and isolation (the point of the pilot)
- MAKER: one model session in its own git worktree; writes one task package; never sees the worker, arms or results.
- WORKER: one model session per (task, arm); sees only a history-free standalone repo plus `statement.md`.
  Runs inside the freeze-v3 sandbox pattern with an isolated home/profile, so `~/.agents/AGENTS.md`,
  `~/.config/opencode/AGENTS.md` and every other global rule file are NOT visible.
- ACCEPTOR: model-free code; applies the hidden test after the worker finishes.
- QUARANTINE: a directory outside the repo and outside the worker sandbox's readable roots holding
  hidden test, reference patch, SEAL and results. The worker can never read it.
- Maker, worker and reviewer are different sessions with different working directories. No shared context.

## Task package format (`<pkg>/`)
- `package.json`: `task_id`, `title`, `label` = `SYNTHETIC_EXPLORATORY`, `risk` = `LOW`, `language` = `python`,
  `statement` = `statement.md`, `hidden_test` = `hidden/test_hidden.py`, `hidden_test_dest` = `tests/test_hidden.py`,
  `reference_patch` = `reference.patch`, `test_command` (argv list, unittest), `gate` = `{kind: ruff, config: ruff.toml}`.
- `base/`: a small deterministic Python project (stdlib only, no network, no clock/random) with `ruff.toml`
  (`select = ["E9", "F"]`), `src/`, and visible `tests/` that pass at base.
- `statement.md`: the task as a ticket; must not quote or paraphrase the hidden test.
- `hidden/test_hidden.py`, `reference.patch` (touches 1-2 non-test files, <= 60 changed lines).

## Package verifier (`taskpack.py`, model-free) — reject unless ALL hold
1. Required files present; no extra files; no symlinks; paths stay inside the package.
2. `base/` visible tests pass; `ruff check` clean at base.
3. Hidden test copied to `hidden_test_dest` at base: clean unittest FAILURE (`failures>0`, `errors=0`, not skipped, collects >=1 test, no ImportError).
4. After `reference.patch`: hidden test passes, visible tests still pass, ruff clean.
5. `statement.md` contains no >= 8-token substring of the hidden test (leak check) and no mention of arms, governance, FULL/MIN/INJECT.
6. Risk LOW by rule: reference patch <= 60 lines, 1-2 non-test files, no security/credential/concurrency/governance content (simple keyword screen is acceptable, documented as heuristic).
7. Seal: write `SEAL.json` with sha256 of every file; later steps re-verify the seal and refuse on mismatch.
Maker prompt template in `maker_prompt.md`: the maker writes only inside its own cwd `pkg/`, and is told nothing about arms, workers or results.

## Arms and carriers (`arms.py`)
- FULL: deterministic extraction of the canonical `AGENTS.md` sections 2-4 from a pinned materials commit (`git show <sha>:AGENTS.md`),
  with a manifest of rule-ID -> byte range and source hash (see `ARMS.md`, 11 rule IDs R-V12-036..046).
- MIN: an explicit A-layer-only text (`pilot/a_layer_min.md`, flagged ASSUMED) plus the identical gate commands and task contract; must contain none of the 11 process instructions.
- INJECT: same carrier as MIN. After the worker finishes, on a disposable copy of the candidate: hollow `ruff.toml` `select` and place the F841 control at `scripts/n7_control.py` per `experiments/v1.2/gate-load-bearing/gates.json`; the catching gate is `probe_gates.py --worktree` and must reject.
- Delivery: outside the repo, in the worker's isolated home, via the existing `freeze-v3/wrapper_delivery.py::prepare` pattern; read back and compare hashes; reject missing/substituted/hash-mismatch.

## Driver and acceptance (`pilot_driver.py`, `pilot_accept.py`)
- Driver launches a worker per (task, arm) through the existing freeze-v3 sandbox/egress/isolated-profile mechanism (import, do not copy or edit frozen files).
- A real launch REQUIRES `H4_PILOT_RUN_AUTH` pointing at an authorization file with a numeric `budget_cap` and `max_runs`; without it the driver exits non-zero before any process starts. Tests use `--fake-worker` (deterministic stub, no opencode).
- Per run record (JSON, written to a caller-given durable results dir, never /tmp): task_id, arm, model, base sha, seal sha, carrier hashes, worker exit status, hidden-test verdict, ruff verdict, INJECT verdict, durations, token/cost if reported, and `UNKNOWN` (never 0) for anything not observed.
- Acceptance order: visible tests, ruff, then hidden test, then (INJECT only) the N7 probe. A missing control or failed injection is `INVALID`, not green.

## Required tests (`experiments/v1.2/tests/`, stdlib unittest, no model/network)
Verifier rejects: hidden test erroring at base; hidden test already passing at base; reference that breaks visible tests; ruff-dirty reference; statement leaking the hidden test; extra/symlink files; tampered SEAL. Carriers: FULL != MIN; MIN lacks all 11 rule IDs; wrong/missing/substituted carrier rejected. Driver: refuses without `H4_PILOT_RUN_AUTH`; fake worker end to end through all three arms; INJECT with a missed control -> INVALID. Isolation: worker sandbox profile denies reads of quarantine and of global rule files (use the freeze-v3 self-test pattern; skip with an explicit SKIP reason if `sandbox-exec` is unavailable, never a pass).

## Hard rules
No opencode/codex/agy/model run, no network, no `run_h2r2.py`, no runs root. Do not edit anything under `freeze-v3/` or other frozen paths. Write only under `experiments/v1.2/h4-micro-low-ablation/pilot/` and new `experiments/v1.2/tests/test_v1_2_h4_pilot_*.py`. No home-directory paths or secrets in committed files. Gates before commit: ruff, `scripts/validate_governance.py`, `scripts/validate_public_release.py`, the new tests. Commit locally only.
