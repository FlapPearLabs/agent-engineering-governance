# H4 task selection — draft, not a freeze

**PROTOCOL_NOT_STARTABLE**: only one measured outcome candidate qualifies among the
three entries below; this is not an exhaustive search or proof no other tasks qualify.
Risk classification remains an ASSUMPTION requiring independent review.

R-V12-042 says: “LOW：非生产/机械票可 L0-only（仓政策允许时）；生产代码必须 L1”
(`experiments/v1.2/mechanization-gap/rule-inventory.md`, R-V12-042). The risk table in
`AGENTS.md` §3 identifies documentation as LOW, but also escalates governance changes.
`experiments/v1.2/mechanization-gap/rule-migration-matrix.md` R-V12-042/040 identifies
risk binding as H4's target, not an automated risk classifier.

| ID | Role | Classification evidence and limit | Oracle |
| --- | --- | --- | --- |
| r24-governance-bootstrap-budget-repair-round-2 | excluded diagnostic | ASSUMED escalation: modifies canonical bootstrap contract; not counted as LOW | frozen t09 test; candidate has no `ruff.toml` |
| r27-governance-memory-preset-budget-restore | outcome candidate | ASSUMED LOW: one noncanonical preset document, 4 additions/1 deletion; does not amend an approved canonical contract | frozen `scripts/tests/test_p1_t09_bootstrap_byte_budget.py` |
| t01-low-doc-accuracy | false-green control only | LOW explicitly recorded in `experiments/v1.2/h1-hot-context/tasks.yaml` | frozen t09 test is green at both ends; not an outcome oracle |

The pairs and exact oracle paths are in `task-candidates.json`; r24/r27 are admitted
in `experiments/v1.2/h2-lazy-disclosure/admission/batch-2/classification.json` and
`ledger.json`. Admission closure reports 23 schema-v2-valid requests and 5 rejected,
not 23 demonstrated H4 outcome tasks. Per `eligibility-schema-v2.md` §3.3, r05's
18 frozen tests do not transition; H1 t01's historical diff is not an independent
behavioral oracle and cannot discriminate that false-green. t01 is only a control,
not an outcome task; no replacement oracle is asserted. An ADDED acceptance can
transition when candidate bytes are externalized and kept out of worker scope; a
frozen test can transition on a regression-repair pair such as r27. This probe only
accepts identical frozen oracle bytes; it does not claim to cover ADDED surfaces.

MEASURED: at source checkout `bf9e5a7980c3e2f992d540eea80fea2d50c61134` with
these deliverables uncommitted, run
`env -u PYTHONPATH TMPDIR=$(cd /tmp && pwd -P) python experiments/v1.2/h4-micro-low-ablation/measure_eligibility.py`
with the specified Python environment first in PATH. Exit 1 is intentional because
r24's historical candidate lacks the requested gate configuration. Verbatim JSON:

```json
{
  "eligible_count": 1,
  "task_count_gate": "PROTOCOL_NOT_STARTABLE",
  "tasks": [
    {
      "id": "r24-governance-bootstrap-budget-repair-round-2",
      "verdict": "PROBE_ERROR",
      "base_resolved": "825d3902597655c90393100281260cbba8697c07",
      "candidate_resolved": "4505faeaaa7a4a89a94c8751efc1f7cc0738ffe0",
      "base_oracle_rc": 1,
      "candidate_oracle_rc": 0,
      "error": "candidate has no ruff.toml"
    },
    {
      "id": "r27-governance-memory-preset-budget-restore",
      "verdict": "ELIGIBLE",
      "base_resolved": "3e92751a6e5490e826a130835598e5069d8fe8ce",
      "candidate_resolved": "7cadc9c445180395bf8494644ab91a4d55717438",
      "base_oracle_rc": 1,
      "candidate_oracle_rc": 0,
      "ruff_before_rc": 1,
      "ruff_before_output": "F841 Local variable `unused` is assigned to but never used\n --> scripts/n7_control.py:2:5\n  |\n1 | def example():\n2 |     unused = 1\n  |     ^^^^^^\n  |\nhelp: Remove assignment to unused variable `unused`\n\nFound 1 error.\nNo fixes available (1 hidden fix can be enabled with the `--unsafe-fixes` option).",
      "ruff_after_rc": 0,
      "ruff_after_output": "All checks passed!",
      "n7": {
        "id": "ruff",
        "status": "GATE_NOT_LOAD_BEARING",
        "detail": "effective rules differ from E9,F"
      }
    },
    {
      "id": "t01-low-doc-accuracy",
      "verdict": "INELIGIBLE",
      "base_resolved": "c08f6f8b3bbe57853a56adf3c2847e806bbb60a3",
      "candidate_resolved": "6d841d56fe8ccfc5ae3a0590fb73e15a57d38a48",
      "base_oracle_rc": 0,
      "candidate_oracle_rc": 0,
      "ruff_before_rc": 1,
      "ruff_before_output": "F841 Local variable `unused` is assigned to but never used\n --> scripts/n7_control.py:2:5\n  |\n1 | def example():\n2 |     unused = 1\n  |     ^^^^^^\n  |\nhelp: Remove assignment to unused variable `unused`\n\nFound 1 error.\nNo fixes available (1 hidden fix can be enabled with the `--unsafe-fixes` option).",
      "ruff_after_rc": 0,
      "ruff_after_output": "All checks passed!",
      "n7": {
        "id": "ruff",
        "status": "GATE_NOT_LOAD_BEARING",
        "detail": "effective rules differ from E9,F"
      }
    }
  ]
}
```

N7 is the injection detector: the hollowed Ruff command alone is green and therefore
does **not** detect hollowing; N7's effective-rule comparison detects it. No full H4
protocol, independent review, or model run is implied by these measurements.
