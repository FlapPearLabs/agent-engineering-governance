# H4 preconditions — design, not authorization to start

Authority: `experiments/v1.2/mechanization-gap/experiment-protocols.md` §0, §2, §4. `V3` denotes `experiments/v1.2/h2-lazy-disclosure/freeze-v3/`; `T` denotes `experiments/v1.2/tests/`. Component/test names below were checked for existence; their existence is not a test run or proof of H4 integration. All proposed behavior is **ASSUMED** pending its closing evidence. Any unclosed condition yields `PROTOCOL_NOT_STARTABLE`.

| Condition | H4 requirement and component or build | Closing evidence |
| --- | --- | --- |
| P1 target binding | Before each worker starts, bind absolute worktree and expected base to actual HEAD; mismatch refuses. V3 `run_h2r2.py::drive` and `T/test_v1_2_h2_freeze_v3.py::test_the_driver_records_the_base_from_the_governance_repository` concern recording, not the full H4 assertion. Build the pre-launch binding. | Correct path/base accepted; wrong path, wrong SHA and wrong repository refused, with commands and recorded actual identities. |
| P2 delivery | FULL, MIN and INJECT receive their specified carrier mechanically, without fallback. V3 `wrapper_delivery.py::prepare` and `T/test_v1_2_h2_freeze_v3.py::test_both_arms_deliver_only_outside_clean_base_with_object_hashes` provide a delivery pattern, not H4 carrier generation. Build pinned extraction and readback checks in `ARMS.md`. | Manifest and hashes for source and delivered bytes; correct treatment for all arms; missing, altered, or contaminating carrier rejected. |
| P3 persistence | All formal run outputs, worktrees, control records and raw logs reside outside `/tmp` and `$TMPDIR` on an approved durable location. V3 `sandbox_v2.py::snapshot` and `T/test_v1_2_h2_freeze_v3_driverfs.py::test_snapshot_special_entries_and_collision` cover snapshot edge cases, not durability. Build path validation and recovery check. | Reject temporary paths and aliases; record approved path, hashes, and successful post-restart reread. Scratch copies used solely for probes are not formal run evidence. |
| P4 blinding | Common report-generation path and identical field presence across all three arms; independent M4 reviewers see no arm-revealing ID, paths or fields. V3 `run_audit_v2.py::project_verdict` and `T/test_v1_2_h2_freeze_v3.py::test_the_auditor_projection_drops_the_base_sha_and_the_case_id` cover a limited projection, not H4 isomorphism. Build three-arm projection and leakage tests. | Exact schema/field-presence equality, blinded sample scan and independent blind-review receipt; leakage makes blinding VOID. |
| P5 preregistration | Freeze M1–M6 detectors, high-value boundaries, result precedence, sample size, invalidity, stops, and costs before any run. No existing V3 function proves H4 preregistration. | Owner-approved immutable protocol and hash, before any results; promotion additionally requires §4 prerequisites including N ≥2 per arm. |
| P6 reachability | Every required carrier, invariant, task contract, and gate is present and readable in the actual worker environment; if WARM routing is used, its target must exist and load. V3 `sandbox_v2.py::allow_rules` and `T/test_v1_2_h2_freeze_v3_sandboxread.py::test_read_and_commands` concern sandbox access, not all H4 targets. Build H4-specific route/readback probes. | Per-arm, per-base existence/read/load and hash receipts; missing or inaccessible target refuses start. |
| P7 gate integrity | Each M2/M3 criterion below requires a clean negative control and a known-bad positive control, on the actual pinned target/config; unknown or non-load-bearing is not PASS. N7 is a candidate component, not end-to-end proof. | Preserve exact source/config, commands, signals, exits and full results; task oracle rejects base and defect, accepts reference; N7 and real-path/config checks pass. |

## P7 gate inventory and scope

The proposed complete quality criteria are: (1) `ruff`: `python3 -m ruff check .`, M2, positive control F841; (2) the registered task-specific mechanical end-state oracle, M2, whose exact command and controlled defect must be fixed per task and tested before start; and (3) N7 load-bearing probe for the exact candidate/config, M2 and M3 for F-010. These are proposed criteria, **ASSUMED** until the task eligibility and H4 harness exist. The eleven N7 controls in `experiments/v1.2/gate-load-bearing/gates.json` are probe coverage, not eleven automatically selected H4 acceptance gates. Task-specific gates cannot be silently added without updating this inventory and P7 controls.

N7 limitations (`experiments/v1.2/gate-load-bearing/README.md`): it does not establish CI execution, bind an alternate config to the settings query, cover real-path exclusions, or detect stale ignores; selftest control checks propagation of one False item, not all predicates. Therefore H4 must inspect the exact invoked configuration, workflow execution and representative actual paths, with task-specific controls; N7 green alone cannot close P7 or prove CI. The supplied N7 README does not identify a separate `N7-03` / P3 item; its precise additional wording is **UNVERIFIED**, not inferred.

### N7 baseline measurement

**MEASURED:** at base `bf9e5a7980c3e2f992d540eea80fea2d50c61134`, with `PYTHONPATH` unset, physical `TMPDIR`, and the specified Python environment on `PATH`: `python experiments/v1.2/gate-load-bearing/probe_gates.py --repo . --ref HEAD` exited 0. Its verbatim output is:

```json
{
  "ref": "HEAD",
  "worktree": false,
  "gates": [
    {
      "id": "compile",
      "status": "LOAD_BEARING",
      "detail": "SyntaxError"
    },
    {
      "id": "ruff",
      "status": "LOAD_BEARING",
      "detail": "F841"
    },
    {
      "id": "governance",
      "status": "LOAD_BEARING",
      "detail": "FAIL  markdown-links-resolve"
    },
    {
      "id": "scripts-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "cli-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "continuity-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "workbuddy-tests",
      "status": "LOAD_BEARING",
      "detail": "FAILED (failures=1"
    },
    {
      "id": "public-release",
      "status": "LOAD_BEARING",
      "detail": "UNIX_USER_HOME"
    },
    {
      "id": "metadata",
      "status": "LOAD_BEARING",
      "detail": "PUBLIC_ACCOUNT_IDENTITY"
    },
    {
      "id": "selftest",
      "status": "LOAD_BEARING",
      "detail": "FAIL  01-public-rejects-unix-user-home"
    },
    {
      "id": "history",
      "status": "LOAD_BEARING",
      "detail": "PASSWORD_ASSIGNMENT"
    }
  ],
  "no_positive_control": []
}
```

This is evidence only for that committed base and N7's selected controls, not for an H4 candidate, task oracle, CI execution, or P7 closure.
