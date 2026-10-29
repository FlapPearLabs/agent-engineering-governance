# H4 task selection — draft, not a freeze

**PROTOCOL_NOT_STARTABLE**: two of the thirteen examined historical tasks qualify for the
MICRO/LOW pool, and one of those two is the required false-green control. The search is now
wide (the ten real freeze-v3 tasks plus round 1's three rows) and every row carries a measured
oracle transition and a measured per-base injection, so the shortfall is a property of this
repository's history, not of the probe's scope.

All risk classifications are **ASSUMED** pending independent review. The rule text is
`AGENTS.md` section 3 (risk table, line 85-87, and the ESCALATION list, line 89-92) and
`experiments/v1.2/mechanization-gap/rule-inventory.md` R-V12-042: “LOW：非生产/机械票可
L0-only（仓政策允许时）；生产代码必须 L1”. Section 3 puts documentation/fixture/glue/mechanical
configuration in LOW but escalates “Approved Spec / governance 变更”; R-V12-042 keeps any
production code at L1 or above. Canonical references, canonical contracts, governance
validators and production scripts are therefore not LOW.

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
This is the path that handles ADDED and externalized acceptances, which round 1 did not cover.

r27 and t01 keep the frozen-test path: the test is byte-identical at both revisions and run
with the H2 acceptance command. t01's oracle is a different, untouched test, so it is
`NOT_TRANSITIONING` with the base green — that is what makes it the false-green control, not
an outcome task.

## Injection (F-010 hollowed gate), per base

The hollowed gate is injected into the task's **base** tree, which is the tree the task's gate
has to catch a defect in, and the N7 load-bearing probe grades it:

- base has `ruff.toml` with the exact `select = ["E9", "F"]` line (f09, f10, r27, t01): the
  predicate is hollowed to `select = []` and the F841 control must flip from caught to missed;
- base has no `ruff.toml` (f01-f08, r24): `scripts/validate_governance.py`'s
  `markdown-links-resolve` predicate is forced to `True` and the N7 governance probe must find
  the planted broken link missed. The unmodified gate reports `LOAD_BEARING` on the same tree,
  so the probe discriminates;
- `INJECT_NOT_APPLICABLE` is reserved for a base with neither gate. No row needed it.

`PROBE_ERROR` is only raised for a real measurement failure; a missing single gate is not one.

## Measurement

**MEASURED:** at source checkout `7885e6b7f62d59511c80bfcfa61e17e75b53c631` with these
deliverables uncommitted, using Python 3.13.12, `PYTHONPATH` unset, physical `TMPDIR`, and the
Python environment's bin directory first on `PATH`:

`<PY> experiments/v1.2/h4-micro-low-ablation/measure_eligibility.py`

exit 0. Verbatim JSON:

```json
{
  "source_sha": "7885e6b7f62d59511c80bfcfa61e17e75b53c631",
  "measurement_sha256": "03df4bf4965292400714da3448816bc54af14032f197d6354be3ed182c1cbfd9",
  "candidates_sha256": "72b419f4ac44125748d4d8d0ce927dc62e0c59712a99bf9d2514a267fdc36296",
  "eligible_count": 1,
  "false_green_control_count": 1,
  "task_count_gate": "PROTOCOL_NOT_STARTABLE",
  "funnel": {
    "examined": 13,
    "not_a_candidate": 1,
    "excluded_at_oracle": 0,
    "excluded_at_risk": 10,
    "excluded_at_injection": 0,
    "probe_error": 0,
    "eligible_outcomes": 1,
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
    }
  ]
}
```

## Funnel

Thirteen rows examined; each excluded row is charged to the first step it fails.

1. not a candidate: 1 (r24, canonical contract, duplicate of f08);
2. oracle does not transition: 0 — all ten freeze-v3 oracles reject their base and accept their
   reference candidate, and both frozen-test rows behave as designed;
3. risk above LOW: 10 — every freeze-v3 task is a canonical-reference, canonical-contract or
   production-code change, so section 3 escalates it and R-V12-042 keeps production code at L1;
4. injection not detected: 0 — every base had a gate that exists there;
5. probe errors: 0;
6. eligible outcomes: 1 (r27); qualifying false-green controls: 1 (t01).

`eligible + controls = 2 < 4`, so `task_count_gate = PROTOCOL_NOT_STARTABLE`. The gate needs
four qualifying tasks including at least one control. Qualifying f09/f10 style tasks are not
available here: the ten real freeze-v3 tasks are governance work by construction, and widening
the search further would mean searching this repository's history for other non-governance
LOW deltas — that is a new search, not a re-measurement, and it is not claimed here.

## What this does not establish

No H4 protocol, no harness, no model run, no independent review. The risk column is ASSUMED.
N7's limits (`experiments/v1.2/gate-load-bearing/README.md`) still apply: one probe per gate,
no CI-execution claim, no real-path exclusion coverage. The measurement reads committed
objects through `git archive` and `git clone --shared`; the working-tree bytes are covered only
by the two hashes above.
