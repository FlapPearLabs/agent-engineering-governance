# H4 — MICRO/LOW Governance Ablation: freeze preparation (brief)

Owner decision (2026-10-29): continue V1.2 after N7 closed; H4 is the next experiment because
it tests the slimming claim most directly ("less prompt process, same-or-higher mechanical
acceptance") and N7 removed its main blocker (#45, experiment level).

This round is **freeze preparation**:
- no harness build;
- no model runs;
- no runs root;
- no protocol freeze.

Mechanical, read-only measurements on git history are in scope (task eligibility, gate probes).
Implementer Codex (gpt-6.1-terra); independent review Codex (gpt-6.1-sol); Claude accepts.

## Sources to read first

- `experiments/v1.2/mechanization-gap/experiment-protocols.md`:
  - §0 P1–P7;
  - §2 H4, the frozen shape: three arms, M1–M6, result vocabulary;
  - §4 promotion preconditions.
- `rule-migration-matrix.md`: R-V12-036..046 (the procedural rules H4 ablates) and R-V12-042
  (risk binding).
- `failure-mechanism-map.md`: the E3 defect classes eligible for ARM_INJECT (e.g. F-010 hollowed
  gate predicate, F-015 artefacts in a volatile directory).
- `experiments/v1.2/h1-hot-context/`, task t01. This is the LOW task that exposed the false-pass
  family, and §2.2 requires it to be reused.
- `experiments/v1.2/h2-lazy-disclosure/`:
  - `eligibility-schema-v2.md`, `task-classification-v2.json`, `freeze-v2-closure-report.md`.
    H2 ended INSUFFICIENT_EVIDENCE largely on task eligibility; do not repeat that.
  - `freeze-v3/`: the hardened harness to reuse.
- `experiments/v1.2/gate-load-bearing/`: the N7 probe; this is how H4 satisfies P7.
- `experiments/v1.2/h5-verified-state/design/`: the format of a design-only round.

## Deliverables (all under `experiments/v1.2/h4-micro-low-ablation/`)

1. **PRECONDITIONS.md** — §0 P1–P7, one by one, for H4. For each:
   - what it requires of H4;
   - which freeze-v3 or N7/N8 component satisfies it (cite file/function and the test proving
     it), or what must be built;
   - the closing evidence.

   For P7, list every gate H4 would use as a quality criterion (M2/M3). Run
   `probe_gates.py --ref HEAD` at this round's base SHA and record the verbatim result.
2. **ARMS.md** — the three arms made concrete.
   - **ARM_PROCESS_FULL:** the current procedural governance.
   - **ARM_PROCESS_MIN:** only the A-layer invariants, the mechanical gates and the acceptance
     contract.
   - **For FULL and MIN:** list exactly which rules or files each arm carries, derived from
     R-V12-036..046 with citations, and how the carrier is built mechanically (P2).
   - **ARM_INJECT:** at least one real E3 defect class from failure-mechanism-map, with:
     - how it is injected (harness-side, deterministic, recorded, invisible to the agent's prompt
       except through the task state);
     - which load-bearing gate must catch it;
     - why a green result would mean `MECHANICAL_ACCEPTANCE_HAS_NO_TEETH`.
3. **TASKS.md + `task-candidates.json` + `measure_eligibility.py`** — at least 4 real MICRO/LOW
   historical tasks from this repo's history.
   - At least one must have a historical false-green; H1 t01 is required by §2.2.
   - **For each task:**
     - base SHA and reference candidate SHA (both resolvable);
     - MICRO/LOW classification evidence (R-V12-042);
     - a mechanical end-state oracle.
   - **`measure_eligibility.py`** measures, read-only and against a scratch clone, that each
     oracle REJECTS the base and ACCEPTS the reference candidate, and that the INJECT defect
     applied to the candidate is REJECTED by the named gate.
   - **No fabrication.** Tasks must be real history. If fewer than 4 qualify, report the count
     and the reasons (`PROTOCOL_NOT_STARTABLE` for that item). Do not invent synthetic tasks.
4. **MEASUREMENT.md** — a DRAFT pre-registration, not frozen.
   - For each of M1–M6: inputs, the mechanical detector, its predicate and its failure mode.
   - How M4 (independent review) is blinded, including P4 template isomorphism.
   - Decision rules mapping M1–M6 to the four result words, mutually exclusive, with
     `INSUFFICIENT_EVIDENCE` as the default.
   - Stopping conditions, validity rules, N per arm (≥2 per §4), and the cost per run.
5. **HARNESS_PLAN.md** — a T-numbered build plan (T70…) for the next round, not built now:
   - a reuse map of freeze-v3 components;
   - what is new: three-arm carriers, injection step, M1 step counter;
   - the known v3 limitations that matter here;
   - risks with mitigations.
6. **OPEN_QUESTIONS.md** — the decisions only the owner can make, each with options and a
   recommendation.

Tests: `experiments/v1.2/tests/test_v1_2_h4_material.py`.
- Structure checks for the deliverables.
- Adversarial cases for `measure_eligibility.py`: an oracle that accepts the base, an
  unresolvable SHA, and an injection the gate does not catch must each be reported as
  ineligible, never as eligible.
- No models, no network, no writes outside temp/scratch.

## Rules

- Write only under `experiments/v1.2/h4-micro-low-ablation/` and the one new test module.
- Never touch canonical files, `scripts/`, `references/`, `.github/`, other experiment
  directories, or `TREE_LEDGER.md`. The ledger is updated by Claude at PR time.
- No `/Users/<name>` paths in committed files.
- Do not run opencode, any model, or any `run_*.py` harness. Do not create runs roots.
- Cite sources by repo path and section. Mark every runtime claim MEASURED (with the command)
  or ASSUMED.
- Gates before committing, with PYTHONPATH unset and TMPDIR set to a physical path:
  - ruff;
  - `scripts/validate_governance.py` 35/35;
  - `scripts/validate_public_release.py` VIOLATIONS=0;
  - the new test module.
