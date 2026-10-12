# H2 Round 1 — closure record (INVALID)

Machine-readable summary of the Round-1 experiment attempt that was terminated by a
**global harness contract defect**. This record is written after the fact; it does not
reinterpret any observation, and it does not produce an H2 result.

```text
ROUND_ID                  = H2-R1
H2_ROUND_1_STATUS         = CLOSED / INVALID
ROUND_INVALID_REASON      = GLOBAL_HARNESS_CONTRACT_DEFECT
VALID_RUNS                = 0
INVALID_RUNS              = 1
H2_RESULT                 = NOT_PRODUCED
EXPERIMENT_STATE          = EXPERIMENT_NOT_VALIDLY_STARTED
```

## Why this is NOT `INSUFFICIENT_EVIDENCE`

`H2_RESULT = INSUFFICIENT_EVIDENCE` is one of the three values the pre-registered rubric may
produce, and it is reserved for an experiment that **ran validly** and whose observations were
too weak to decide. Round 1 produced **no valid observation at all**: the single run was
rejected by the harness before any cell could be scored. Asserting `INSUFFICIENT_EVIDENCE`
here would falsely imply that a valid experiment ran and came back weak. The correct state is
that the experiment never validly started.

## Root cause (PART 4)

```text
CONTRACT says        : the worker should read <REPORT_TEMPLATE_PATH>
REPORT_TEMPLATE_PATH : resolved into the FROZEN MATERIALS TREE
TELEMETRY validator  : READ targets must resolve inside the run worktree
therefore            : a CONTRACT-COMPLIANT worker is REJECTED by the harness
```

The worker's only "violation" was obeying the contract. This is a **global harness contract
defect**, not a worker error, not a task error, not an arm effect, and not a
progressive-disclosure cost. It was discovered on the first run, but it is global by nature:
it would have invalidated **every** run of Round 1, and it was invisible to every gate until a
real worker executed the contract.

## What is explicitly NOT concluded

- No statement is made about whether H2 would yield `DISCLOSURE_SAFE` or
  `DISCLOSURE_HAS_COST`.
- No per-arm or per-task comparison is drawn: there is one run, and it is invalid.
- No governance, canonical, H3, H4 or H5 surface is touched by this record.

## Durable lessons (PART 28)

```text
CONTRACT-LEGAL ACTION != HARNESS-ACCEPTED ACTION
```

When the two disagree, the harness invalidates its own compliant worker. The defect is only
observable by executing the contract, so "the contract is documented" is not evidence that
the contract is executable.

```text
GLOBAL_HARNESS_DEFECT != SINGLE_RUN_FAILURE
```

It surfaced in one run. It is not cell-level: it invalidates the whole round. Do not downgrade
a global defect to a single-cell invalidation because that is where it was first seen.

Neither lesson is promoted to canonical here; that is deferred to N9 synthesis.
