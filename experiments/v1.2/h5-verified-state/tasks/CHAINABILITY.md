# H5 Task C — chainability (T62, Q1)

**Q1 verdict: A.** The frozen-gate measurement reports 37 links among 90 ordered pairs of 10 tasks, of which 45 pairs reached the frozen gate. There are 45 `BROKEN_LINK` pairs, eight other rejected pairs, zero measurement errors and zero oracle-path dependent pairs. The longest graph path is f01 → f02 → f03 → f04 → f05 → f06 → f07 (length 7). The superseded round reported 41 links; the stricter R04 check yields 37.

The archived [measurement JSON](measurement-6dcfcea.json) has SHA-256 `c16c94222f266c6b9576a3897b32d7b9f6ec73d900dd25ffb487fc05c0d63c60`. It was produced from a clean clone at source SHA `6dcfceaf7189628d54aea3ad051427226fc6eeb1`; exit 0 and empty stderr were reported by the measurement run. The command form is `env -u PYTHONPATH python experiments/v1.2/h5-verified-state/tasks/measure_chain.py --repo <clean-clone>`; the original shell command line was not independently recovered. The frozen `run_acceptance_v2.py` is the read-only acceptance oracle, not a model driver. No model runs were performed. This document does not claim the measurement was rerun for this update.

## Summary object

```json
{
    "bases_that_are_not_ancestors_of_their_candidate": [
      "f01",
      "f02",
      "f03",
      "f04",
      "f05",
      "f06",
      "f07",
      "f09",
      "f10"
    ],
    "broken_links": 45,
    "links": 37,
    "links_by_source": {
      "f01": 9,
      "f02": 8,
      "f03": 7,
      "f04": 6,
      "f05": 5,
      "f06": 1,
      "f07": 0,
      "f08": 1,
      "f09": 0,
      "f10": 0
    },
    "longest_chain": [
      "f01",
      "f02",
      "f03",
      "f04",
      "f05",
      "f06",
      "f07"
    ],
    "longest_chain_length": 7,
    "measurement_errors": 0,
    "oracle_dependent_pairs": 0,
    "ordered_pairs": 90,
    "pairs_measured_with_the_frozen_gate": 45,
    "tasks": 10,
    "two_task_chains": 37,
    "verdict": "A"
  }
```

## Links

Derived from the archived JSON with `json.load` and the predicate `pair["chainable"]`:

| From | To |
|---|---|
| f01 | f02, f03, f04, f05, f06, f07, f08, f09, f10 |
| f02 | f03, f04, f05, f06, f07, f08, f09, f10 |
| f03 | f04, f05, f06, f07, f08, f09, f10 |
| f04 | f05, f06, f07, f08, f09, f10 |
| f05 | f06, f07, f08, f09, f10 |
| f06 | f07 |
| f08 | f09 |

## Non-link reasons

| Reason | Count |
|---|---:|
| `BROKEN_LINK` | 45 |
| `INTERMEDIATE:ORACLE_NOT_PRESERVED:REJECT` | 4 |
| `ORACLE_NOT_PRESERVED:REJECT` | 4 |

`BROKEN_LINK` is the ancestry failure category; the other eight rejections are not included in that 45 count.

## Review fixes (9634a0b)

- **R04:** Previously the endpoint at the second task's base alone could produce LINK, even if the second candidate failed, regressed the first task, or an intermediate state failed. The fix checks both candidates and intermediate commits. The reviewer attack rerun below returns `chainable: false` for all four adversarial cases. The test oracle is synthetic; it does not claim the frozen oracle has those failures.
- **R06:** The earlier document attributed a measurement to `c2e0502`, a commit which did not contain the program. This measurement reports the clean-clone source `6dcfcea`, which does contain it. `git cat-file -e 6dcfceaf7189628d54aea3ad051427226fc6eeb1:experiments/v1.2/h5-verified-state/tasks/measure_chain.py` returned exit 0. The full historical invocation and clean-clone status are reported run provenance, not independently reconstructed in this update.
- **R09:** Previously an absent base observation was treated as false and returned LINK. The rerun returns `[false, "BASE_OBSERVATION_UNKNOWN"]`.

Reviewer reproduction: copy `attack_chain.py` to a temporary directory, link its `repo` to this worktree, create its `tmp` directory, and run `env -u PYTHONPATH python <temp>/attack_chain.py`. Actual complete stdout (temporary Git commit hashes vary):

```text
{"calls": [["t1", "178e60a5093aad996fce9fc9840c5b8fae143dfe"], ["t1", "2b98035b835288841ae57f9ede98761bc72ac6a3"], ["t2", "daa5e5f623d23a865cb50eaf99ce20e0482b9113"], ["t2", "daa5e5f623d23a865cb50eaf99ce20e0482b9113"]], "case": "next_task_candidate_rejected", "chainable": false, "next_own_candidate": {"base_passing": false, "verdict": "REJECT"}, "reason": "SECOND_CANDIDATE:ORACLE_NOT_PRESERVED:REJECT"}
{"actual_chain_end": {"base_passing": false, "verdict": "REJECT"}, "calls": [["t1", "178e60a5093aad996fce9fc9840c5b8fae143dfe"], ["t1", "2b98035b835288841ae57f9ede98761bc72ac6a3"], ["t2", "067d15c876ff79528c42c3732896fcb424fc0a7f"], ["t1", "178e60a5093aad996fce9fc9840c5b8fae143dfe"], ["t1", "067d15c876ff79528c42c3732896fcb424fc0a7f"]], "case": "previous_task_regresses_at_next_candidate", "chainable": false, "endpoint": {"base_passing": false, "verdict": "ACCEPT"}, "oracle_overlap": [], "reason": "SECOND_CANDIDATE:ORACLE_NOT_PRESERVED:REJECT"}
{"case": "intermediate_regression", "chainable": false, "endpoint": {"base_passing": false, "verdict": "ACCEPT"}, "intermediate": {"base_passing": false, "verdict": "REJECT"}, "intermediates": {"commits": 4, "measured": true, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 2, "touching_oracle": 0}}
{"case": "base_observation_absent", "judge": [false, "BASE_OBSERVATION_UNKNOWN"]}
{"bad": {"base_passing": false, "verdict": "REJECT"}, "case": "no_intermediate_change_but_dependency_regressed", "chainable": false, "end": {"base_passing": false, "verdict": "ACCEPT"}, "intermediates": {"commits": 4, "measured": true, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}}
```

## Known limits

- The graph path is a succession of measured pair links; it does not by itself prove that every earlier task's predicate remains true at every later step of a seven-task chain.
- Oracle dependence is checked by paths, not semantic dependency. Zero path overlaps is not proof of semantic independence.
- The base/candidate relationship is non-ancestral for nine tasks as shown in the summary. Intermediate checks apply to the measured intervals and recorded gate observations, not arbitrary states outside them.
- R09 was a P3 on the earlier revision and is fixed as shown above; the separate ledger direct-test P3 R10 is addressed in the ledger branch. No additional P3 finding is asserted fixed without evidence.
- Results are tied to the archived source and frozen task set; they do not establish episode, model, ledger, or closure behavior.
