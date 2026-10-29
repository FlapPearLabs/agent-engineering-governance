# H4 task selection — draft, not a freeze

**PROTOCOL_NOT_STARTABLE**: three rounds of search now cover every pool this repository has
offered, and still only three tasks qualify for the MICRO/LOW pool — two eligible outcomes
(r27, p01) plus one required false-green control (t01), `2 + 1 = 3 < 4`. Round 3 widened the
search past H2 admission's `5ab500e` ceiling into the 149 experiment-only commits landed since
(up to the immutable upper bound `87d0414`), screened them cheaply, and executed the three
survivors. The shortfall is a property of this repository's history, not of the probe's scope.

All risk classifications remain **ASSUMED**; the independent review of `bbca663` accepted the
current per-row upgrades but rejected the earlier production-code generalization (F6, restated
here). Risk level and review strength are separate axes. `AGENTS.md` section 3 (risk table, line 85-87, and the ESCALATION
list, line 89-92) puts documentation, fixture, deterministic glue, mechanical configuration and
**micro production fixes** in LOW, and its review column requires L1 for production code: “生产
代码：**必须 L1**”. A required L1 review therefore does **not** by itself raise a task above LOW
— section 3 says LOW may take “非生产/机械票：可 L0-only（仓政策允许时）”, so L0-only is an
allowance for some LOW tickets, not the definition of LOW. The only thing that moves a task
above LOW here is the ESCALATION list: “Approved Spec / governance 变更”, “安全/凭据边界”, and
the rest of its items. `experiments/v1.2/mechanization-gap/rule-inventory.md` R-V12-042 keeps
production code at L1 or above (review strength) and does not classify any production change as
non-LOW. Canonical references, canonical contracts and governance validators escalate because
they are governance changes on the ESCALATION list, not because they are production code; a
production script with no canonical or security surface would stay LOW with a mandatory L1.

## Round 3: the post-admission experiment pool

Round 2 examined the freeze-v3 registry plus three admission rows; its search stopped where H2
admission stopped. `git log --no-merges --format='%H %s' 5ab500e..87d0414 -- experiments/`
lists **149** further commits, all of them confined to `experiments/`. The upper bound is the
immutable round-3 baseline `87d041453cf6e1b034225a561008d483cf8a014e`, not the moving
`origin/main` ref (which this clone resolves elsewhere and which answered 0 for the same
command); the screen is reproducible against the recorded commit. The cheap screen ran
before any oracle was executed (`git diff --numstat <c>^ <c>` over the whole commit, not just
the `experiments/` paths, so a commit that also touched a canonical file would have shown up):

| Step | Rows | Excluded here, and why |
| --- | --- | --- |
| pool | 149 | — |
| touches `experiments/v1.2/tests/` | 98 | 51 touch nothing there |
| adds a test file (`DELTA_ADDED`) | 15 | the other 83 rewrite an existing test and add nothing — the r03 shape: the delta edited the acceptance that is supposed to judge it, so it is not admissible as a basis (eligibility-schema-v2 §3.3) |
| adds a test and rewrites no test | 12 | 3 also rewrite a sibling test (`eac803686f`, `7b9251aaa8`, `4add2ca288`) — same r03 shape, refused |
| touches no canonical path | 12 | 0 — the survivor set is experiment-only |
| non-test delta ≤ 200 changed lines | 5 | 7 are 213–16395 lines (213 `718ab4efdd`, 264 `c57f8f4c12`, 540 `46fb9fb39e`, 650 `db64a465b6`, 790 `7ba6361189`, 1566 `ea268dd888`, 16395 `bcbd3c4c3a`) |
| LOW after the risk screen | 3 | `6951caa07b` (82) rewrites `run_acceptance_v2.py` — the program that produces the verdict — and `sandbox_v2.py`; `510478fb19` (91) rewrites `sandbox_v2.py` and `worker-sandbox.sb.template`, the OS sandbox profile. Both hit section 3's ESCALATION list (“安全/凭据边界”, and for the acceptance program the governance/verdict analogue), so they were never executed |
| executed oracles | 3 | `20403fe6b3`, `1dbcf3f2d3`, `d9c4b9a7b8` — the three smallest non-test deltas (56/151/160) |

The size bound is **≤ 200 changed lines outside the oracle test**; the whole 149-commit pool
contains nothing between 160 and 213, so any bound in [160, 213) yields the same three rows, and
the two rows just above it are escalated on security grounds anyway. The bound is stated rather
than tuned; it is the only judgement in the screen that is not mechanical.

Executing 3 of 149 commits is well inside the 25-execution cap, and it is the smallest-delta
end of the pool by construction.

## How experiment harness code is treated as risk

`experiments/` is experiment material, not the repository's governed surface: the D-layer
canonical files are `AGENTS.md` and `references/` (with `deployment/` contracts and the
`scripts/` validators that enforce them), and the round-3 pool was selected precisely because it
is **non-canonical**. The harness under `experiments/v1.2/h2-lazy-disclosure/` is therefore
**not production**: no file under `scripts/` or `.github/workflows/` references `experiments/`
(checked with `grep -rn 'experiments/' scripts/*.py .github/workflows/*.yml` → no output), it
ships no gate the repository enforces, and it is not covered by `validate_governance.py`.

The text relied on, in order of precedence:

* `AGENTS.md` section 3 LOW row: “LOW | 文档、fixture、确定性胶水、机械配置；**微型生产修复** |
  非生产/机械票：**可 L0-only 闭合（仓政策允许时）**；生产代码：**必须 L1**”.
* R-V12-042 (`rule-inventory.md` 358-366): “REQ = LOW：非生产/机械票可 L0-only（仓政策允许时）；
  生产代码必须 L1。” — the *review-strength* axis is production vs non-production (production
  mandates L1); it does not say production code is non-LOW.
* R-V12-043/R-V12-044: the escalation list still binds a LOW ticket — “LOW 票不得触发 ESCALATION
  清单，除非命中清单本身” — with “安全与凭据边界” and “Approved Spec 或 governance 变更” as
  list items.

So: an `experiments/`-only delta is LOW because it is neither a governance change nor a security
boundary, **not** because “non-production” is the definition of LOW; production code is
compatible with LOW and only adds a mandatory L1 review. The escalation list is then applied
*on top*, not replaced by the risk kind. A delta that itself decides what a sandbox allows, what
the access audit convicts, or what the acceptance program returns is a mechanism whose
correctness carries the escalation trigger even though the code is experimental — which is why
the two sandbox/verdict rows above were screened out before execution rather than argued down to
LOW for being under `experiments/`. Size is recorded separately (`MICRO`/`LOW` by the ≤ 200-line
bound) and never used to argue a security-boundary delta downward.

Re-checked under the separated rule (F6): every one of f01–f10 also touches a canonical
document (`references/`, `deployment/`, `audit/` or `schemas/`), so each still hits “Approved
Spec / governance 变更” on the ESCALATION list and keeps `ESCALATION_REQUIRED` even though its
production-code content alone would not change its risk. r24 is the same canonical-contract
delta as f08. No excluded candidate changes class under the corrected rule, and none was
excluded on production-code status alone.

## Examined rows and ASSUMED classification

`git diff --stat <base> <candidate>` is the evidence for what each delta touches.

| ID | Role | ASSUMED risk | Delta and why |
| --- | --- | --- | --- |
| f01 | outcome | ESCALATION_REQUIRED | `references/review-evidence.md` 81, `schemas/review-evidence.schema.json` 3, `scripts/review_evidence.py` 193: canonical reference plus governance-validator production code |
| f02 | outcome | ESCALATION_REQUIRED | `references/execution-stage.md` 18: canonical D-layer reference |
| f03 | outcome | ESCALATION_REQUIRED | `references/review-evidence.md` 71, `scripts/review_evidence.py` 194: canonical reference plus production code |
| f04 | outcome | ESCALATION_REQUIRED | `references/review-evidence.md` 32, `scripts/review_evidence.py` 105: canonical reference plus production code |
| f05 | outcome | ESCALATION_REQUIRED | `references/git-ci-integration.md` 9: canonical reference |
| f06 | outcome | ESCALATION_REQUIRED | `references/review-and-repair-saturation.md` 6: canonical reference |
| f07 | outcome | ESCALATION_REQUIRED | `references/git-ci-integration.md` 2, `references/review-evidence.md` 7, `scripts/review_evidence.py` 27: canonical references plus production code |
| f08 | outcome | ESCALATION_REQUIRED | `audit/AUDIT_QUALITY_REVIEW.md` 2, `deployment/BOOTSTRAP_CONTRACT.md` 2: canonical bootstrap contract |
| f09 | outcome | ESCALATION_REQUIRED | `references/review-and-repair-saturation.md` 2, `references/static-analysis-and-code-intelligence.md` 2, `references/ticket-lane.md` 3: canonical references |
| f10 | outcome | ESCALATION_REQUIRED | `audit/PAIN_TO_POLICY_MAP_V2.md` 1, `docs/design-history.md` 2, `references/skills-and-model-routing.md` 3, `scripts/skill_execution.py` 60: canonical reference plus production code |
| r24 | not a candidate | ESCALATION_REQUIRED | Canonical bootstrap contract; the same historical pair as f08, kept as round 1's diagnostic row |
| r27 | outcome | LOW | `deployment/MEMORY_POINTER_CANDIDATE.md` 4 (3+,1-): a candidate pointer text, not the approved canonical contract |
| t01 | false-green control | LOW | `scripts/tests/test_p1_t16_gate_cli_entrypoint.py` 55 (test-only fix); `experiments/v1.2/h1-hot-context/tasks.yaml` records `risk: LOW` |
| p01 | outcome | LOW | `freeze-v3/run_h2r2.py` 30/10, `CODEX_REPORT.md` 16/0 + the added oracle 59/0: non-test delta 56 lines, experiment-only. Artifact hashing records symlinks/FIFOs instead of silently skipping them — evidence bookkeeping in the experimental driver. Closest call of the three: it stops a symlink from being followed while hashing, so it *is* integrity code; it is not an enforcement boundary (nothing is allowed or denied by it, no credential, no sandbox rule) and no canonical file is touched |
| p02 | outcome | LOW | `freeze-v2/wrapper_delivery.py` 151/0 (one new module) + the added oracle 143/0: non-test delta 151 added lines, experiment-only, no deletion. Carrier delivery for the experiment; no canonical file, no gate mechanism |
| p03 | outcome | LOW | `results-v2/export_results.py` 91/0 and `results-v2/render_closure.py` 69/0 (two new reporting modules) + the added oracle 71/0: non-test delta 160 added lines, experiment-only. Report rendering; no canonical file, no gate mechanism |

Per-row evidence text is in `task-candidates.json` (`risk_evidence`).

## Oracle path

f01-f10 are the ten tasks registered in
`experiments/v1.2/h2-lazy-disclosure/freeze-v3/task-registry-v3.json`; their candidate
revisions are the `CANDIDATE_SHA` values in
`experiments/v1.2/h2-lazy-disclosure/admission/freeze-v2-input/shortlist.json`. For these rows
`measure_eligibility.py` imports `run_acceptance_v2.accept` (it does not reimplement the
oracle) and calls it twice on one prepared run: on the unchanged base, then after applying the
candidate's non-test delta. The base must be `REJECT` with `WORKER_NOT_PASSING:RESOLVED` and
`WORKER_NOT_PASSING:SYMLINKED` and no `BASE_NOT_FAILING:*`; the candidate must be `ACCEPT`.
This is the path that handles ADDED and externalized acceptances.

r27 and t01 keep the frozen-test path: the test is byte-identical at both revisions and run
with the H2 acceptance command (`unittest discover -s scripts/tests`). t01's oracle is a
different, untouched test, so it is `NOT_TRANSITIONING` with the base green — that is what makes
it the false-green control, not an outcome task.

p01-p03 use the **added-oracle path** (`oracle_kind: added_experiment`). The candidate ADDS the
test, so there is no frozen surface to run at the base; the candidate's own bytes are carried
onto the base tree — the externalised oracle of eligibility-schema-v2 §3.1 (“They are carried
byte-identically into the base tree, so the BASE verdict cannot be produced by editing the
acceptance between the two runs”), with provenance `DELTA_ADDED`. The measurement refuses a row
whose oracle already exists at the base (that would be `DELTA_MODIFIED`, the r03 shape), then
runs the carried test with `unittest discover -s experiments/v1.2/tests` at the base and at the
candidate.

Strictness, applied on **every** oracle path: the candidate must be a clean `OK` with at least
one test run and no errors or skips, and the **base must be a clean unittest FAILURE** — at least
one test run, `failures=`, no `errors=`, no skips. A base run whose module never imports is
`ORACLE_BASE_NO_LOAD`; a base run that reports any `errors=` is `ORACLE_BASE_ERRORS`, because a
clean assertion failure must not be mixed with errors. Both are recorded as
`NOT_TRANSITIONING`: a surface that cannot run reports no verdict to disagree with — schema
§3.1, “A missing, unrunnable, timed-out or uncomputable acceptance is never a pass”.

This rule is now identical on the freeze-v3 path (F2). `accept` records per-test names in
`not_passing` but not whether unittest counted a failure or an error, so after the acceptance
reports `REJECT`/`ACCEPT` the measurement also runs the task's frozen oracle at the base and
requires a pure assertion failure; f10's base reports `FAILED (failures=4, errors=1)` and is
therefore `ORACLE_BASE_ERRORS`, not `FAIL_TO_PASS`. The skip rule also bites the candidate side
(F1): a summary such as `OK (skipped=1)` is parsed as one skip, so a candidate that skips its own
oracle never counts as a clean pass.

This is the decisive rule for p02/p03, and it is deliberately the conservative one. Their tests
produce no assertion failure at the base: p03 cannot import at all, and p02 errors on the symbol
the delta creates. A grader that counts “could not run” as FAIL_TO_PASS would admit both. It is
not counted here: the delta would be judged by a test it authored against an API that does not
exist at the base — the same takeover §3.3 refuses for r03 — and a worker holding the base cannot
even learn the API from a hidden oracle. Under that looser reading the eligible count would be 4
(r27, p01, p02, p03), which with t01 would make the gate MET; the reading is recorded here so the
choice is visible, not because it is unavailable.

## Injection (F-010 hollowed gate), per base

The hollowed gate is injected into the task's **base** tree, which is the tree the task's gate
has to catch a defect in, and the N7 load-bearing probe grades it:

- base has `ruff.toml` with the exact `select = ["E9", "F"]` line (f09, f10, r27, t01, p01, p02,
  p03): the predicate is hollowed to `select = []` and the F841 control must flip from caught to
  missed;
- base has no `ruff.toml` (f01-f08, r24): `scripts/validate_governance.py`'s
  `markdown-links-resolve` predicate is forced to `True` and the N7 governance probe must find
  the planted broken link missed. The unmodified gate reports `LOAD_BEARING` on the same tree,
  so the probe discriminates;
- `INJECT_NOT_APPLICABLE` is reserved for a base with neither gate. No row needed it.

`PROBE_ERROR` is only raised for a real measurement failure; a missing single gate is not one.

## Measurement

**MEASURED (re-run for the review fixes):** at source checkout
`bbca6634f54364ec047555af0709ba9d0bed39d8` with the review-fix deliverables uncommitted, using
Python 3.13.12, `PYTHONPATH` unset, physical `TMPDIR`, and the Python environment's bin
directory first on `PATH`:

`<PY> experiments/v1.2/h4-micro-low-ablation/measure_eligibility.py`

exit 0. Verbatim JSON:

```json
{
  "source_sha": "bbca6634f54364ec047555af0709ba9d0bed39d8",
  "measurement_sha256": "bb5c1dfc86e4365a76f567058b1ce9f972c62401c1d82ff747330c49314749eb",
  "candidates_sha256": "45c1c75c2584f4df40864dee4f6f5d719dedd4b9c69bb4153e9bb1323624cd27",
  "eligible_count": 2,
  "false_green_control_count": 1,
  "task_count_gate": "PROTOCOL_NOT_STARTABLE",
  "funnel": {
    "examined": 16,
    "not_a_candidate": 1,
    "excluded_at_oracle": 3,
    "excluded_at_risk": 9,
    "excluded_at_injection": 0,
    "probe_error": 0,
    "eligible_outcomes": 2,
    "qualifying_controls": 1
  },
  "tasks": [
    {
      "id": "f01",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "e11a8461e3cb906f1321c95589eb88256ae1a213",
      "candidate_resolved": "b88df0313b3b921978a9869b9422beb686d21f3c",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 46,
        "failures": 17,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "governance",
        "gate": "N7 governance load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "hollow_run_rc": 0,
        "crucible": "markdown-links-resolve",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "f02",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "a97595229f11cd7262f6a49abb433de408e94ca4",
      "candidate_resolved": "89b97e3b65d3f13ec21d2b837457f63f8aff7c02",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 11,
        "failures": 3,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "governance",
        "gate": "N7 governance load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "hollow_run_rc": 0,
        "crucible": "markdown-links-resolve",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "f03",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "990177774cc4b906ec95146422356c97928b05fc",
      "candidate_resolved": "33cfcc890e38032ba932e8de30fa30d5721d737a",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 26,
        "failures": 12,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "governance",
        "gate": "N7 governance load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "hollow_run_rc": 0,
        "crucible": "markdown-links-resolve",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "f04",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "698cd1468f33410800dad3af2972a7bc8b317d7b",
      "candidate_resolved": "51e7604be3689f31142d17144893790000efac30",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 39,
        "failures": 25,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "governance",
        "gate": "N7 governance load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "hollow_run_rc": 0,
        "crucible": "markdown-links-resolve",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "f05",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "072d32e2146b28fadbf1c1a1ddcf3bb5cad446a2",
      "candidate_resolved": "12c32f41898a5cec8db9346637c78800978f7549",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 38,
        "failures": 17,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "governance",
        "gate": "N7 governance load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "hollow_run_rc": 0,
        "crucible": "markdown-links-resolve",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "f06",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "7a38de6f3c1f20228b5ecb5bc0bb3d0d49d75e01",
      "candidate_resolved": "0046c3648c4e6b2530c06cfce80df30c64d66ab6",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 21,
        "failures": 2,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "governance",
        "gate": "N7 governance load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "hollow_run_rc": 0,
        "crucible": "markdown-links-resolve",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "f07",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "e5c5950bca5fba0562f0ad6cd7fe7b367fc64cf3",
      "candidate_resolved": "1eaaea2c97bfe6ef36ae811298a68a52e04b554a",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 25,
        "failures": 10,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "governance",
        "gate": "N7 governance load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "hollow_run_rc": 0,
        "crucible": "markdown-links-resolve",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "f08",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "825d3902597655c90393100281260cbba8697c07",
      "candidate_resolved": "4505faeaaa7a4a89a94c8751efc1f7cc0738ffe0",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 24,
        "failures": 1,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "governance",
        "gate": "N7 governance load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "hollow_run_rc": 0,
        "crucible": "markdown-links-resolve",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "f09",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "ade16de80c1deb47b776874f0f1a2b10e8f7e16c",
      "candidate_resolved": "579f6d5e7762610382e4362f668efaffc51f04ce",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 71,
        "failures": 5,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "ruff",
        "gate": "N7 ruff load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "control_before": 1,
        "control_after": 0,
        "crucible": "F841",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "f10",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "41cd7f59ca2afe6d4cb44ff5e4bce169108db340",
      "candidate_resolved": "5d61ad139ceb5408a6d96ce269f9a76f89df8b4e",
      "base_accept": {
        "verdict": "REJECT",
        "reasons": [
          "WORKER_NOT_PASSING:RESOLVED",
          "WORKER_NOT_PASSING:SYMLINKED"
        ]
      },
      "candidate_accept": {
        "verdict": "ACCEPT",
        "reasons": []
      },
      "base_oracle": {
        "rc": 1,
        "ran": 28,
        "failures": 4,
        "errors": 1,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "NOT_TRANSITIONING",
      "base_passing": false,
      "injection": {
        "kind": "ruff",
        "gate": "N7 ruff load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "control_before": 1,
        "control_after": 0,
        "crucible": "F841",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "ORACLE_BASE_ERRORS",
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "r24-governance-bootstrap-budget-repair-round-2",
      "verdict": "INELIGIBLE",
      "role": "excluded",
      "risk": "ESCALATION_REQUIRED",
      "risk_basis": "ASSUMED",
      "base_resolved": "825d3902597655c90393100281260cbba8697c07",
      "candidate_resolved": "4505faeaaa7a4a89a94c8751efc1f7cc0738ffe0",
      "base_oracle_rc": 1,
      "candidate_oracle_rc": 0,
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "governance",
        "gate": "N7 governance load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "hollow_run_rc": 0,
        "crucible": "markdown-links-resolve",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "ROLE_EXCLUDED",
        "RISK_ABOVE_LOW"
      ]
    },
    {
      "id": "r27-governance-memory-preset-budget-restore",
      "verdict": "ELIGIBLE",
      "role": "outcome",
      "risk": "LOW",
      "risk_basis": "ASSUMED",
      "base_resolved": "3e92751a6e5490e826a130835598e5069d8fe8ce",
      "candidate_resolved": "7cadc9c445180395bf8494644ab91a4d55717438",
      "base_oracle_rc": 1,
      "candidate_oracle_rc": 0,
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "ruff",
        "gate": "N7 ruff load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "control_before": 1,
        "control_after": 0,
        "crucible": "F841",
        "status": "DETECTED"
      },
      "ineligible_reasons": []
    },
    {
      "id": "t01-low-doc-accuracy",
      "verdict": "CONTROL",
      "role": "false-green-control",
      "risk": "LOW",
      "risk_basis": "ASSUMED",
      "base_resolved": "c08f6f8b3bbe57853a56adf3c2847e806bbb60a3",
      "candidate_resolved": "6d841d56fe8ccfc5ae3a0590fb73e15a57d38a48",
      "base_oracle_rc": 0,
      "candidate_oracle_rc": 0,
      "oracle_transition": "NOT_TRANSITIONING",
      "base_passing": true,
      "injection": {
        "kind": "ruff",
        "gate": "N7 ruff load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "control_before": 1,
        "control_after": 0,
        "crucible": "F841",
        "status": "DETECTED"
      },
      "ineligible_reasons": []
    },
    {
      "id": "p01-driver-artifact-link-safety",
      "verdict": "ELIGIBLE",
      "role": "outcome",
      "risk": "LOW",
      "risk_basis": "ASSUMED",
      "base_resolved": "bcbd3c4c3ab9d9399a5337cb1da60dfa5f800a0b",
      "candidate_resolved": "20403fe6b3be306b71bd5181517ca23e99c774da",
      "oracle_provenance": "DELTA_ADDED",
      "base_oracle": {
        "rc": 1,
        "ran": 1,
        "failures": 1,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "candidate_oracle": {
        "rc": 0,
        "ran": 1,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "FAIL_TO_PASS",
      "base_passing": false,
      "injection": {
        "kind": "ruff",
        "gate": "N7 ruff load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "control_before": 1,
        "control_after": 0,
        "crucible": "F841",
        "status": "DETECTED"
      },
      "ineligible_reasons": []
    },
    {
      "id": "p02-freeze-v2-carrier-delivery",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "LOW",
      "risk_basis": "ASSUMED",
      "base_resolved": "0edbbaba82de777402addcf9026a3f5dabdd5f02",
      "candidate_resolved": "1dbcf3f2d3bc9ec0c230c36784db6adcc2a8713a",
      "oracle_provenance": "DELTA_ADDED",
      "base_oracle": {
        "rc": 1,
        "ran": 4,
        "failures": 0,
        "errors": 4,
        "skipped": 0,
        "loaded": true
      },
      "candidate_oracle": {
        "rc": 0,
        "ran": 4,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "NOT_TRANSITIONING",
      "base_passing": false,
      "injection": {
        "kind": "ruff",
        "gate": "N7 ruff load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "control_before": 1,
        "control_after": 0,
        "crucible": "F841",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "ORACLE_BASE_ERRORS"
      ]
    },
    {
      "id": "p03-results-export-renderer",
      "verdict": "INELIGIBLE",
      "role": "outcome",
      "risk": "LOW",
      "risk_basis": "ASSUMED",
      "base_resolved": "231dd720bedd047f9ae07d9237da6382f080d136",
      "candidate_resolved": "d9c4b9a7b8c96f4c370d3ed837873dcde967bd8c",
      "oracle_provenance": "DELTA_ADDED",
      "base_oracle": {
        "rc": 1,
        "ran": 1,
        "failures": 0,
        "errors": 1,
        "skipped": 0,
        "loaded": false
      },
      "candidate_oracle": {
        "rc": 0,
        "ran": 2,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "loaded": true
      },
      "oracle_transition": "NOT_TRANSITIONING",
      "base_passing": false,
      "injection": {
        "kind": "ruff",
        "gate": "N7 ruff load-bearing probe",
        "clean": "LOAD_BEARING",
        "hollow": "GATE_NOT_LOAD_BEARING",
        "control_before": 1,
        "control_after": 0,
        "crucible": "F841",
        "status": "DETECTED"
      },
      "ineligible_reasons": [
        "ORACLE_BASE_NO_LOAD"
      ]
    }
  ]
}
```

## Funnel

Sixteen rows examined; each excluded row is charged to the first step it fails.

1. not a candidate: 1 (r24, canonical contract, duplicate of f08);
2. oracle does not transition: 3 — p02 (`ORACLE_BASE_ERRORS`: its test loads but errors on the
   symbol the delta creates), p03 (`ORACLE_BASE_NO_LOAD`: its test module cannot import at all)
   and f10 (`ORACLE_BASE_ERRORS`: its base reports `FAILED (failures=4, errors=1)`, so the base
   run is not a clean assertion failure). Nine of the ten freeze-v3 oracles reject their base
   and accept their reference candidate; p01 transitions; both frozen-test rows behave as
   designed. f10 remains ineligible for risk as well; under the strict rule it is now charged
   to the oracle step first, which is why the risk bucket drops from 10 to 9 without any
   verdict changing;
3. risk above LOW: 9 — every remaining freeze-v3 task is a canonical-reference or
   canonical-contract change, so the ESCALATION list applies (not its production-code status);
4. injection not detected: 0 — every base had a gate that exists there, and p01-p03's bases
   carry the exact E9,F ruff select line;
5. probe errors: 0;
6. eligible outcomes: 2 (r27, p01); qualifying false-green controls: 1 (t01).

`eligible + controls = 3 < 4`, so `task_count_gate = PROTOCOL_NOT_STARTABLE`. The gate needs
four qualifying tasks including at least one control.

What this round establishes, beyond round 2: the post-admission history does not contain the
missing tasks either. 149 experiment-only commits, 15 that add a test, 12 that add a test
without rewriting one, 5 within the size bound, 3 after the risk screen — and of those three
exactly one is a repair a base-held worker could actually be asked to make. The rest of the pool
is either a security/verdict mechanism (escalated on the list, not on size) or a test that only
exists to check a module the same commit creates.

## Review fixes (bbca663)

The independent review of `bbca663` (its report is outside this repository) reported P2×2 and
P3×4. All six are fixed below; the measurement was re-run afterwards. “Before” outputs are the
review's own reproduction logs; “after” outputs were produced by the same probes pointed at this
tree. After commands: the measurement command in “Measurement” above; the review's
`skip_probe.py`, `f10_strict.py` and `absent_test_probe.py` re-pointed at this tree; and
`python -m unittest discover -s experiments/v1.2/tests -p test_v1_2_h4_material.py`. Each
regression test was also checked against a one-line mutation of the guard it covers (the file
was restored and its SHA256 re-verified after every mutant).

**F1 / P2 — a candidate that only skips was accepted.** Before: `skip_probe.py` printed
`"verdict": "ELIGIBLE"`, `"candidate_oracle": {... "skipped": 0 ...}` while the raw run said
`Ran 1 test ... OK (skipped=1)`. Cause: only `FAILED (...)` summaries were parsed, so `OK
(skipped=N)` yielded no summary and zero skips (`measure_eligibility.py:143`). After: one parser
reads both `FAILED (...)` and `OK (...)`; the same probe prints `"skipped": 1`,
`"oracle_transition": "NOT_TRANSITIONING"`, `"verdict": "INELIGIBLE"`, reasons
`["ORACLE_NOT_TRANSITIONING"]`. Regression test:
`test_skipped_candidate_is_not_a_transition`; restoring the old `FAILED`-only parser makes that
test red (mutant rc=1).

**F2 / P2 — freeze-v3 accepted a base whose oracle errors.** Before: `f10_strict.py` showed
`"oracle_transition": "FAIL_TO_PASS"` with `base_accept` = `REJECT` / only
`WORKER_NOT_PASSING:RESOLVED`,`:SYMLINKED`, while the base oracle ran
`FAILED (failures=4, errors=1)` (`AttributeError: ... 'SAFE_RETRIEVAL_AVAILABLE'`). Cause: the
acceptance records test names in `not_passing` but not whether unittest counted a failure or an
error. After: the freeze-v3 path re-runs the frozen oracle at the base (`strict_base_oracle`) and
applies the same `base_failure_reason` rule as the added-oracle path. Re-running
`f10_strict.py`: `"base_oracle": {"rc": 1, "ran": 28, "failures": 4, "errors": 1, ...}`,
`"oracle_transition": "NOT_TRANSITIONING"`, `"ineligible_reasons":
["ORACLE_BASE_ERRORS", "RISK_ABOVE_LOW"]`. Regression test:
`test_freeze_v3_accept_path_rejects_base_oracle_with_errors`; removing the strict check makes it
red (mutant rc=1). Funnel: `excluded_at_oracle` 2 → 3, `excluded_at_risk` 10 → 9, f10 moves
buckets; `eligible_count` 2 and `false_green_control_count` 1 are unchanged, so the count
statements in `MEASUREMENT.md` and `OPEN_QUESTIONS.md` (3 < 4) still hold.

**F3 / P3 — the absence test did not create the oracle at the base.** Before: after deleting the
base-existence guard the named test stayed green (`shipped_test_mutant_rc=0`) because the
candidate blob did not exist at either end and the measurement failed later. After: the test
commits `test_added.py` at the base and keeps it in the candidate, so the guard is the branch
being exercised; the error is `added oracle exists at the base: not a DELTA_ADDED surface`.
Deleting the guard now makes the test red (mutant rc=1).

**F4 / P3 — header count contradicted the tail.** The opening paragraph said “only two tasks
qualify ... (one of them the required false-green control)” while the funnel and
`MEASUREMENT.md`/`OPEN_QUESTIONS.md` say 2 outcomes + 1 control = 3 < 4. The header now states
“two eligible outcomes (r27, p01) plus one required false-green control (t01), `2 + 1 = 3 < 4`”.
No other count in this directory used the old phrasing.

**F5 / P3 — the round-3 search used a mutable ref.** Before: `git log ... 5ab500e..origin/main`
answered 0 in the review clone (`origin/main` = `1a020733...`). After: the bound is the immutable
round-3 baseline `87d041453cf6e1b034225a561008d483cf8a014e`:
`git log --no-merges --format=%H 5ab500e..87d0414 -- experiments/ | wc -l` → `149`, matching
the recorded pool. The command and the bound are now recorded in the round-3 section.

**F6 / P3 — review strength was used as risk level.** The old text inferred “production scripts
are therefore not LOW” from the L1 requirement. Restated: section 3 puts micro production fixes
in LOW; production code requires L1 review, which does not by itself make a task non-LOW; only
the ESCALATION list (governance/Approved Spec changes, security boundaries, …) moves a task
above LOW. Re-checked every excluded candidate: f01–f10 each also touch a canonical document
(`references/`, `deployment/`, `audit/` or `schemas/`), so all keep `ESCALATION_REQUIRED` on the
list itself, r24 is the f08 pair, and no candidate changes class. No row was excluded on
production-code status alone.

Gates re-run for this round: `ruff check .`, `scripts/validate_governance.py` (35/35),
`scripts/validate_public_release.py` (VIOLATIONS=0), and
`python -m unittest discover -s experiments/v1.2/tests -p test_v1_2_h4_material.py` (10 tests OK).

## What this does not establish

No H4 protocol, no harness, no model run. The draft was independently reviewed and failed on
F1–F6; those fixes are recorded above but have not themselves been independently re-reviewed.
The risk column is ASSUMED. The 200-line size bound is a stated judgement, not a measured
threshold. N7's limits
(`experiments/v1.2/gate-load-bearing/README.md`) still apply: one probe per gate, no
CI-execution claim, no real-path exclusion coverage. The measurement reads committed objects
through `git archive` and `git clone --shared`; the working-tree bytes are covered only by the
two hashes above.
