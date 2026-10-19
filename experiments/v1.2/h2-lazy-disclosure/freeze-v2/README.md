# Freeze v2 — pre-freeze measurements (in progress; nothing here is frozen)

Inputs: the 10-task shortlist `admission/freeze-v2-input/shortlist.json` (validator 2.8.12).

## 1. Route preconditions (protocol §10, FZ-ADM-4) — `route_preconditions.py`

```text
from the REPOSITORY ROOT, H=experiments/v1.2/h2-lazy-disclosure (any other root is refused):
$H/freeze-v2/route_preconditions.py . $H/admission/freeze-v2-input/shortlist.json \
    --out $H/freeze-v2/route-preconditions.json
ROUTES_ADMISSIBLE 10/10. r44, r50 bases: 33/33 valid. The other 8 bases: 31/33, failing only
LEAN-12 and AGENTS-03 (references/static-tooling-profiles.md not yet in history) — S1/S2 rows no
task touches -> HISTORICAL_BASE_ROUTE_UNSATISFIED, the class P6 already recorded for 015780b.
No S3 (H2 carrier) row fails anywhere.
```

## 2. Delivery anchors (schema §6.4, FZ-ADM-3) — `delivery_anchors.py`

```text
from the REPOSITORY ROOT:
$H/freeze-v2/delivery_anchors.py . $H/admission/freeze-v2-input/shortlist.json \
    --materials <commit> --out $H/freeze-v2/delivery-anchors.json   (recorded: 5090f44)
Gates: the task oracle and the full scripts/tests suite, PRE vs POST delivery, zero worker edits,
compared by the SET of non-passing test ids (not exit codes: every A_REPAIR oracle is red at its
base, and round 1's t01 went 1 -> 4 failures without changing rc).

RESULT  neutral tasks: CODEBUDDY slot 0/10, AGENTS slot 0/10.
  oracle      contaminated in 11 of 40 (task x slot x arm) cells: r40 x4 and r41 x4 (every slot,
              both arms), r44 AGENTS/{control,variant}, r24 AGENTS/variant. Four oracles contain
              root-wide single-declaration scans of their own, so the TASK's acceptance is not
              comparable at those bases either (review of 5090f44 corrected an earlier README
              that said "untouched in all 40"; the JSON never did). No test is skipped PRE or
              POST anywhere (skips now count as not passing).
  full suite  every cell gains failures, in BOTH arms: the repository's single-declaration scans
              (test_seam_contract_partitions, test_p1_t10/t11/t12 "declared exactly once") read
              every non-test text file under the root, so the in-tree copies — H2_WARM/ reference
              copies and a carrier that restates AGENTS.md — become second declaration points.
              Replacing AGENTS.md (AGENTS slot) additionally breaks the tests that read AGENTS.md
              (test_ticket_gate_wiring, test_p1_t09 section-ten checks).
```

Consequence: under §6.4 no shortlisted task is admissible with IN-TREE delivery, in either slot.
This is the round-1 t01 contamination mechanism, now measured on every base. It is attributed to
the experiment's delivery, not to the tasks, and is recorded rather than normalised (§4.6).
Delivery must move OUT of the worktree (carrier and WARM bundle outside the repository root),
which makes the worker runtime's guidance-loading behaviour the deciding constraint — see the
stage report for the measured opencode behaviour and the decision it needs.
