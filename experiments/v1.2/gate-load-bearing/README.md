# N7 load-bearing gate experiment

Three approaches address different failures:

| Hollowing | Semantic positive control | Intent binding | Reachability evidence |
|---|---|---|---|
| Empty select | Detects when the chosen rule stops firing | Detects effective rule-set mismatch | Does not establish rule semantics |
| Select narrowed to E9 | Detects an F841 control | Detects mismatch | Does not establish rule semantics |
| Probe ignored | Detects the suppressed control | Detects global rule changes; per-file suppression needs the control | Can show whether the path is included, not whether a rule fires |
| Probe excluded | Detects the suppressed control | Does not prove traversal | Can detect the excluded path |
| CI uses another config | Detects if the invoked command misses the control | Must inspect the settings of the exact invoked command | Command inspection can detect changed routing |
| Stale ignore after a defect is fixed | Does not detect it without a targeted control | Can detect changes to an explicitly bound rule set | Does not determine whether the ignore is still needed |

This prototype combines controls and Ruff's resolved settings, and requires the
recorded command to occur in a workflow. It does not prove that CI executes that
step, bind an alternate config to the settings query, cover exclusions on real
paths, or detect stale ignores. Representative real paths and their effective
settings and traversal require separate evidence; one control is not coverage.

The probe uses a local clone with real history, and injects controls only in the
scratch copy. `--worktree` copies the current tracked and untracked candidate
files; `--ref` tests a committed tree. A gate without a control is listed as
`NO_POSITIVE_CONTROL`. Every status other than `LOAD_BEARING` returns nonzero.
The selftest control proves that the aggregator propagates a False item; it does
not prove that every selftest item retains a live predicate. This experiment does not
change canonical policy or CI and does not close issue #45.
