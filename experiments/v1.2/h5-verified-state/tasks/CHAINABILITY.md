# H5 Task C — chainability of the frozen H2 tasks (T62, Q1)

**Verdict: Q1 = A holds.** 41 of the 45 ordered pairs that git leaves open are valid chain
links under the frozen gate, the longest chain is 8 tasks long, and no link was added by hand:
4 ancestry pairs were refused by the gate and stay refused in the record below.

- measured at `source_sha` = `c2e050282f414e0ae343474717cb061bd07555e8` (branch
  `experiment/v1.2-h5-chain`), frozen registry
  `experiments/v1.2/h2-lazy-disclosure/freeze-v3/task-registry-v3.json`, sha256
  `d0c424ed42036a331c26cfc79cb8fb3b7a5600bc0e4975b5ea11e9d18b11d88b`
- 10 frozen tasks (f01–f10), 90 ordered pairs, 45 of them reach the frozen gate, 41 links,
  45 `BROKEN_LINK` (the reverse direction of every link), 0 oracle-dependent pairs, 0
  measurement errors
- longest chain: `f01 → f02 → f03 → f04 → f05 → f06 → f07 → f09` (8 tasks); equally long,
  `f01 → … → f07 → f10`. All 41 links are also 2-task chains (`two_task_chains`).
- status of every number here: **MEASURED** by the command in §2; the raw output is §3
  verbatim. Nothing in this document is inferred beyond what that output states.

## 1. What counts as a chain link

`measure_chain.py` takes the task table from the frozen registry (no SHA is copied by hand) and
asks three questions of every ordered pair `(i, j)`, `i ≠ j`:

| # | Question | Mechanism | Refusal reason |
|---|---|---|---|
| 1 | Is step i's output step j's input? | `candidate_i == base_j`, or `candidate_i` is an ancestor of `base_j` | `BROKEN_LINK` |
| 2 | Is task i's oracle independent of task j's work? | task j's delta (`base_j..candidate_j`) does not touch task i's oracle path | `ORACLE_DEPENDENCE` |
| 3 | Does the frozen gate still accept task i on the tree at `base_j`, with the base itself still failing? | `run_acceptance_v2.accept` for task i, on the delivered base plus the `base_i..base_j` delta minus `scripts/tests/` (the frozen worker scope denies that directory) | `ORACLE_NOT_PRESERVED:<verdict>`, `ORACLE_ACCEPTS_THE_BASE` |

Question 3 is the expensive one and runs only where 1 and 2 leave the pair open (45 of 90
pairs). Its two verdicts are both required: `ACCEPT` means task i's repair is still there at
`base_j`; `base_passing = false` means the untouched base still fails, so "unchanged" is not
just "the oracle was already green". That is exactly the brief's "each step REJECTS its own
base and ACCEPTS its own candidate".

Fail closed: an exception inside the gate is `MEASUREMENT_ERROR:<type>`, never a link, and it
turns the whole verdict into `INCONCLUSIVE` instead of `A` or `B`.

## 2. How to reproduce it

```sh
export TMPDIR=$(cd /tmp && pwd -P)
env -u PYTHONPATH PYTHON=/path/to/python3 \
  sh experiments/v1.2/h5-verified-state/tasks/run_chain_measurement.sh
```

The runner clones the repository with `--shared` (objects borrowed read-only, nothing written
into the real repository), checks the clone out detached at `HEAD`, and deletes it on exit. The
measurement itself only reads git and runs the frozen gate; it writes no runs root, starts no
driver, and calls no model. It refuses to run when the measured checkout is not at the same
commit as the harness (`MEASUREMENT_REPO_NOT_AT_HARNESS_HEAD`), so the numbers and the code
that produced them are always the same commit. A scoped re-run is
`… run_chain_measurement.sh --tasks f01,f02`.

The measurement was run twice at this SHA; both runs produced the same 41 links, the same 4
refusals and the same summary counts.

## 3. Verbatim output

```json
{
  "schema_version": 1,
  "program": "experiments/v1.2/h5-verified-state/tasks/measure_chain.py",
  "source_sha": "c2e050282f414e0ae343474717cb061bd07555e8",
  "registry": "experiments/v1.2/h2-lazy-disclosure/freeze-v3/task-registry-v3.json",
  "registry_sha256": "d0c424ed42036a331c26cfc79cb8fb3b7a5600bc0e4975b5ea11e9d18b11d88b",
  "measurement_repo_is_harness_head": true,
  "python": "3.13.12",
  "tasks": [
    {"base": "e11a8461e3cb906f1321c95589eb88256ae1a213", "candidate": "b88df0313b3b921978a9869b9422beb686d21f3c", "id": "f01", "oracle_surface": ["scripts/tests/test_review_evidence_contract.py"]},
    {"base": "a97595229f11cd7262f6a49abb433de408e94ca4", "candidate": "89b97e3b65d3f13ec21d2b837457f63f8aff7c02", "id": "f02", "oracle_surface": ["scripts/tests/test_p1_t02_execution_stage_pre_ticket_record.py"]},
    {"base": "990177774cc4b906ec95146422356c97928b05fc", "candidate": "33cfcc890e38032ba932e8de30fa30d5721d737a", "id": "f03", "oracle_surface": ["scripts/tests/test_p1_t05_evidence_disposition.py"]},
    {"base": "698cd1468f33410800dad3af2972a7bc8b317d7b", "candidate": "51e7604be3689f31142d17144893790000efac30", "id": "f04", "oracle_surface": ["scripts/tests/test_p1_t06_producer_trust_boundary.py"]},
    {"base": "072d32e2146b28fadbf1c1a1ddcf3bb5cad446a2", "candidate": "12c32f41898a5cec8db9346637c78800978f7549", "id": "f05", "oracle_surface": ["scripts/tests/test_p1_t11_destructive_workspace_transaction.py"]},
    {"base": "7a38de6f3c1f20228b5ecb5bc0bb3d0d49d75e01", "candidate": "0046c3648c4e6b2530c06cfce80df30c64d66ab6", "id": "f06", "oracle_surface": ["scripts/tests/test_p1_t10_audit_visibility_recipe.py"]},
    {"base": "e5c5950bca5fba0562f0ad6cd7fe7b367fc64cf3", "candidate": "1eaaea2c97bfe6ef36ae811298a68a52e04b554a", "id": "f07", "oracle_surface": ["scripts/tests/test_p1_t08_evidence_lifecycle.py"]},
    {"base": "825d3902597655c90393100281260cbba8697c07", "candidate": "4505faeaaa7a4a89a94c8751efc1f7cc0738ffe0", "id": "f08", "oracle_surface": ["scripts/tests/test_p1_t09_bootstrap_byte_budget.py"]},
    {"base": "ade16de80c1deb47b776874f0f1a2b10e8f7e16c", "candidate": "579f6d5e7762610382e4362f668efaffc51f04ce", "id": "f09", "oracle_surface": ["scripts/tests/test_p1_t18_defect_promotion_fast_full.py"]},
    {"base": "41cd7f59ca2afe6d4cb44ff5e4bce169108db340", "candidate": "5d61ad139ceb5408a6d96ce269f9a76f89df8b4e", "id": "f10", "oracle_surface": ["scripts/tests/test_skill_execution.py"]}
  ],
  "base_to_candidate": [
    {"base_ancestor_candidate": false, "candidate_ancestor_base": false, "id": "f01"},
    {"base_ancestor_candidate": false, "candidate_ancestor_base": false, "id": "f02"},
    {"base_ancestor_candidate": false, "candidate_ancestor_base": false, "id": "f03"},
    {"base_ancestor_candidate": false, "candidate_ancestor_base": false, "id": "f04"},
    {"base_ancestor_candidate": false, "candidate_ancestor_base": false, "id": "f05"},
    {"base_ancestor_candidate": false, "candidate_ancestor_base": false, "id": "f06"},
    {"base_ancestor_candidate": false, "candidate_ancestor_base": false, "id": "f07"},
    {"base_ancestor_candidate": true, "candidate_ancestor_base": false, "id": "f08"},
    {"base_ancestor_candidate": false, "candidate_ancestor_base": false, "id": "f09"},
    {"base_ancestor_candidate": false, "candidate_ancestor_base": false, "id": "f10"}
  ],
  "pairs": [
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f01", "intermediates": {"commits": 5, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 2, "touching_oracle": 2}, "oracle_overlap": [], "reason": "LINK", "to": "f02"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f01", "intermediates": {"commits": 7, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 3, "touching_oracle": 2}, "oracle_overlap": [], "reason": "LINK", "to": "f03"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f01", "intermediates": {"commits": 12, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 5, "touching_oracle": 2}, "oracle_overlap": [], "reason": "LINK", "to": "f04"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f01", "intermediates": {"commits": 16, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 6, "touching_oracle": 2}, "oracle_overlap": [], "reason": "LINK", "to": "f05"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f01", "intermediates": {"commits": 19, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 6, "touching_oracle": 2}, "oracle_overlap": [], "reason": "LINK", "to": "f06"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f01", "intermediates": {"commits": 26, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 7, "touching_oracle": 2}, "oracle_overlap": [], "reason": "LINK", "to": "f07"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f01", "intermediates": {"commits": 51, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 9, "touching_oracle": 2}, "oracle_overlap": [], "reason": "LINK", "to": "f08"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f01", "intermediates": {"commits": 67, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 9, "touching_oracle": 3}, "oracle_overlap": [], "reason": "LINK", "to": "f09"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f01", "intermediates": {"commits": 94, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 9, "touching_oracle": 3}, "oracle_overlap": [], "reason": "LINK", "to": "f10"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f02", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f01"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f02", "intermediates": {"commits": 2, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f03"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f02", "intermediates": {"commits": 7, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f04"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f02", "intermediates": {"commits": 11, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f05"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f02", "intermediates": {"commits": 14, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f06"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f02", "intermediates": {"commits": 21, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f07"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f02", "intermediates": {"commits": 46, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f08"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f02", "intermediates": {"commits": 62, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f09"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f02", "intermediates": {"commits": 89, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f10"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f03", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f01"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f03", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f02"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f03", "intermediates": {"commits": 5, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 1, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f04"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f03", "intermediates": {"commits": 9, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 2, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f05"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f03", "intermediates": {"commits": 12, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 2, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f06"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f03", "intermediates": {"commits": 19, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 3, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f07"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f03", "intermediates": {"commits": 44, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 5, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f08"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f03", "intermediates": {"commits": 60, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 5, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f09"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f03", "intermediates": {"commits": 87, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 5, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f10"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f04", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f01"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f04", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f02"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f04", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f03"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f04", "intermediates": {"commits": 4, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f05"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f04", "intermediates": {"commits": 7, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f06"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f04", "intermediates": {"commits": 14, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 1, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f07"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f04", "intermediates": {"commits": 39, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 3, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f08"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f04", "intermediates": {"commits": 55, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 3, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f09"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f04", "intermediates": {"commits": 82, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 3, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f10"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f05", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f01"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f05", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f02"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f05", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f03"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f05", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f04"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f05", "intermediates": {"commits": 3, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f06"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f05", "intermediates": {"commits": 10, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 1, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f07"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f05", "intermediates": {"commits": 35, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 2, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f08"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f05", "intermediates": {"commits": 51, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 3, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f09"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f05", "intermediates": {"commits": 78, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 3, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f10"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f06", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f01"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f06", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f02"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f06", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f03"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f06", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f04"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f06", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f05"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f06", "intermediates": {"commits": 7, "measured": false, "stability": "NO_INTERMEDIATE_CHANGE", "touching_fix_paths": 0, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f07"},
    {"ancestor": true, "chainable": false, "endpoint": {"base_passing": false, "reasons": ["FULL_SUITE_NEW_NOT_PASSING:RESOLVED:test_p1_t09_bootstrap_byte_budget.DocumentConvergenceTests.test_contract_is_the_single_semantic_owner", "FULL_SUITE_NEW_NOT_PASSING:SYMLINKED:test_p1_t09_bootstrap_byte_budget.DocumentConvergenceTests.test_contract_is_the_single_semantic_owner"], "verdict": "REJECT"}, "equal": false, "from": "f06", "intermediates": {"commits": 32, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 1, "touching_oracle": 0}, "oracle_overlap": [], "reason": "ORACLE_NOT_PRESERVED:REJECT", "to": "f08"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f06", "intermediates": {"commits": 48, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 2, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f09"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f06", "intermediates": {"commits": 75, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 10, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f10"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f07", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f01"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f07", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f02"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f07", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f03"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f07", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f04"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f07", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f05"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f07", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f06"},
    {"ancestor": true, "chainable": false, "endpoint": {"base_passing": false, "reasons": ["FULL_SUITE_NEW_NOT_PASSING:RESOLVED:test_p1_t09_bootstrap_byte_budget.DocumentConvergenceTests.test_contract_is_the_single_semantic_owner", "FULL_SUITE_NEW_NOT_PASSING:SYMLINKED:test_p1_t09_bootstrap_byte_budget.DocumentConvergenceTests.test_contract_is_the_single_semantic_owner"], "verdict": "REJECT"}, "equal": false, "from": "f07", "intermediates": {"commits": 25, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 1, "touching_oracle": 1}, "oracle_overlap": [], "reason": "ORACLE_NOT_PRESERVED:REJECT", "to": "f08"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f07", "intermediates": {"commits": 41, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 2, "touching_oracle": 1}, "oracle_overlap": [], "reason": "LINK", "to": "f09"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f07", "intermediates": {"commits": 68, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 2, "touching_oracle": 1}, "oracle_overlap": [], "reason": "LINK", "to": "f10"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f08", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f01"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f08", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f02"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f08", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f03"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f08", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f04"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f08", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f05"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f08", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f06"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f08", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f07"},
    {"ancestor": true, "chainable": true, "endpoint": {"base_passing": false, "reasons": [], "verdict": "ACCEPT"}, "equal": false, "from": "f08", "intermediates": {"commits": 15, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 1, "touching_oracle": 0}, "oracle_overlap": [], "reason": "LINK", "to": "f09"},
    {"ancestor": true, "chainable": false, "endpoint": {"base_passing": false, "reasons": ["FULL_SUITE_NEW_NOT_PASSING:RESOLVED:test_p1_t16_gate_cli_entrypoint.RealCommandEntrypointTests.test_consumer_accepts_the_real_structured_pass_run,test_p1_t16_gate_cli_entrypoint.RealCommandEntrypointTests.test_legacy_stdout_is_unchanged_and_carries_no_structured_result,test_p1_t16_gate_cli_entrypoint.RealCommandEntrypointTests.test_malformed_result_is_never_accepted", "FULL_SUITE_NEW_NOT_PASSING:SYMLINKED:test_p1_t16_gate_cli_entrypoint.RealCommandEntrypointTests.test_consumer_accepts_the_real_structured_pass_run,test_p1_t16_gate_cli_entrypoint.RealCommandEntrypointTests.test_legacy_stdout_is_unchanged_and_carries_no_structured_result,test_p1_t16_gate_cli_entrypoint.RealCommandEntrypointTests.test_malformed_result_is_never_accepted"], "verdict": "REJECT"}, "equal": false, "from": "f08", "intermediates": {"commits": 42, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 1, "touching_oracle": 0}, "oracle_overlap": [], "reason": "ORACLE_NOT_PRESERVED:REJECT", "to": "f10"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f09", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f01"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f09", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f02"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f09", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f03"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f09", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f04"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f09", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f05"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f09", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f06"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f09", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f07"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f09", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f08"},
    {"ancestor": true, "chainable": false, "endpoint": {"base_passing": false, "reasons": ["WORKER_NOT_PASSING:RESOLVED", "WORKER_NOT_PASSING:SYMLINKED"], "verdict": "REJECT"}, "equal": false, "from": "f09", "intermediates": {"commits": 27, "measured": false, "stability": "ENDPOINT_ONLY", "touching_fix_paths": 9, "touching_oracle": 17}, "oracle_overlap": [], "reason": "ORACLE_NOT_PRESERVED:REJECT", "to": "f10"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f10", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f01"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f10", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f02"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f10", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f03"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f10", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f04"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f10", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f05"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f10", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f06"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f10", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f07"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f10", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f08"},
    {"ancestor": false, "chainable": false, "endpoint": null, "equal": false, "from": "f10", "intermediates": null, "oracle_overlap": [], "reason": "BROKEN_LINK", "to": "f09"}
  ],
  "summary": {
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
    "links": 41,
    "links_by_source": {
      "f01": 9,
      "f02": 8,
      "f03": 7,
      "f04": 6,
      "f05": 5,
      "f06": 3,
      "f07": 2,
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
      "f07",
      "f09"
    ],
    "longest_chain_length": 8,
    "measurement_errors": 0,
    "oracle_dependent_pairs": 0,
    "ordered_pairs": 90,
    "pairs_measured_with_the_frozen_gate": 45,
    "tasks": 10,
    "two_task_chains": 41,
    "verdict": "A"
  }
}
```

## 4. What the output says

- **The frozen tasks really do chain.** Every `i < j` pair is an ancestry pair (45 of 45), and
  41 of them survive the gate. A chain link needs no synthesised tree: the endpoint of step i
  is `base_j`, a frozen commit that is itself the input of a real task, so the end state of a
  chain is mechanically addressable by SHA.
- **The links are not one lucky pair.** `links_by_source` spreads them over f01–f08
  (9, 8, 7, 6, 5, 3, 2, 1) and the longest chain has 8 tasks, so the ten tasks can be chained
  into multi-step work in many orders, not just adjacently.
- **No step depends on another step's oracle.** `oracle_dependent_pairs` is 0 over all 90
  ordered pairs: no task's delta touches another task's oracle path.
- **The base always still fails.** `base_passing` is `false` in all 45 measured endpoints, so
  every link's `ACCEPT` is a repair, not an oracle that was already green.

### The four pairs git allows and the gate refuses

| pair | reason | what the gate saw |
|---|---|---|
| `f06 → f08` | `ORACLE_NOT_PRESERVED:REJECT` | `FULL_SUITE_NEW_NOT_PASSING` on `test_p1_t09_bootstrap_byte_budget.DocumentConvergenceTests.test_contract_is_the_single_semantic_owner` (both arms) |
| `f07 → f08` | `ORACLE_NOT_PRESERVED:REJECT` | same test, both arms |
| `f08 → f10` | `ORACLE_NOT_PRESERVED:REJECT` | `FULL_SUITE_NEW_NOT_PASSING` on three `test_p1_t16_gate_cli_entrypoint.RealCommandEntrypointTests` cases, both arms |
| `f09 → f10` | `ORACLE_NOT_PRESERVED:REJECT` | `WORKER_NOT_PASSING:RESOLVED` and `WORKER_NOT_PASSING:SYMLINKED` — f09's repair is **not** there at `base_f10`, even though `candidate_f09` is an ancestor of it |

The last row is the important one: ancestry alone would have called `f09 → f10` a link. 17
commits in that interval rewrite task f09's oracle path and 9 touch the files f09 repaired, and
the repair did not survive them. The other three rows are the same failure mode one level up —
`base_f08` and `base_f10` already fail an unrelated suite test that their own task repairs, so
any chain routed through those bases inherits a red suite. The measurement keeps all four
refusals instead of rounding them away.

## 5. Why 9 of 10 bases are not ancestors of their candidates

`base_to_candidate` in the output shows `base_ancestor_candidate = false` for f01–f07, f09 and
f10, and `true` only for f08. This is the H2 admission shape, not a broken registry: for those
nine tasks the frozen base is a **sibling** of the candidate — same parent commit, subject
`h2-admission: externalized oracle for <candidate>`, i.e. the candidate's tree with the oracle
replaced by its frozen copy. So `base_i` is not "before" `candidate_i` on the same line;
`candidate_i` is what a worker would produce on top of it. f08 is the exception: there
`base_f08` is a real ancestor and `candidate_f08`'s parent is `base_f08` itself.

Chainability is unaffected by that shape, because the link direction is `candidate_i` →
`base_j`, and all 45 `i < j` pairs satisfy it. What the shape does mean is that a link's
endpoint is a *base snapshot*, not a *candidate*: the chain composes tasks, it does not
compose deliveries.

## 6. Limits of this measurement (what it does not prove)

- **Intermediate commits are classified, not re-run.** The prescribed measurement is the
  endpoint `base_j`; re-running the gate on every commit in between would mean 1543 more gate
  runs across the 45 measured pairs. 12 links are `NO_INTERMEDIATE_CHANGE` (no commit in the
  interval touches either the repaired files or the oracle path, so the verdict cannot move),
  the other 29 are `ENDPOINT_ONLY` and their interval contains at least one commit that
  rewrites a repaired file or the oracle. `intermediates.measured` is `false` everywhere and
  must stay that way unless someone re-runs the gate per commit.
- **Oracle dependence is a path test.** It compares task j's delta against task i's oracle
  *path*. A semantic dependence that never edits that path is invisible to it; the frozen gate
  is the backstop that caught the `f09 → f10` case.
- **The verdict includes the full suite.** `accept` refuses a tree with newly-not-passing
  suite tests, so a base that is already red (f08, f10) cannot host a link even when its own
  oracle would pass. That is the gate's rule, not a choice made here.
- **This says nothing about episodes, models, the ledger or closure.** No model, no opencode,
  no driver, no runs root: the round is a mechanical, read-only measurement. The fallback
  (`Q1 → B`, real historical multi-step sequences from `git log`) was not needed, so no such
  list is offered; it would also have been unmeasured, and this document does not carry
  unmeasured candidates as if they were chains.
