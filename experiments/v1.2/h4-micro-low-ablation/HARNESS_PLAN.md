# H4 harness plan — design only, not built

Authority: `H4_FREEZE_BRIEF.md` deliverable 5; `experiments/v1.2/mechanization-gap/experiment-protocols.md` §0, §2, §4. All H4 behavior, timings and integration below are **ASSUMED**, pending implementation and test. No harness build, model run or runs root in this round. Task gate remains `PROTOCOL_NOT_STARTABLE` (`TASKS.md`); owner decisions and frozen protocol are prerequisites.

## Verified reuse map

`V3 = experiments/v1.2/h2-lazy-disclosure/freeze-v3/`; `T = experiments/v1.2/tests/`. **MEASURED (existence only):** `rg -n '^def (snapshot|allow_rules|drive|project_verdict|prepare)\(' experiments/v1.2/h2-lazy-disclosure/freeze-v3/{sandbox_v2.py,run_h2r2.py,run_audit_v2.py,wrapper_delivery.py}` and `rg -n 'def test_(both_arms_deliver_only_outside_clean_base_with_object_hashes|the_auditor_projection_drops_the_base_sha_and_the_case_id|read_and_commands|snapshot_special_entries_and_collision|the_driver_records_the_base_from_the_governance_repository)' experiments/v1.2/tests/test_v1_2_h2_freeze_v3*.py`. These establish named symbols, not successful tests or H4 correctness.

| Reuse candidate | Existing test | What it does not establish |
| --- | --- | --- |
| `V3/wrapper_delivery.py::prepare` | `T/test_v1_2_h2_freeze_v3.py::test_both_arms_deliver_only_outside_clean_base_with_object_hashes` | H4's three pinned, uncontaminated carriers or their readback. |
| `V3/sandbox_v2.py::allow_rules` | `T/test_v1_2_h2_freeze_v3_sandboxread.py::test_read_and_commands` | H4-specific route reachability, isolation and carrier coverage. |
| `V3/sandbox_v2.py::snapshot` | `T/test_v1_2_h2_freeze_v3_driverfs.py::test_snapshot_special_entries_and_collision` | Approved durable location or restart recovery. |
| `V3/run_audit_v2.py::project_verdict` | `T/test_v1_2_h2_freeze_v3.py::test_the_auditor_projection_drops_the_base_sha_and_the_case_id` | Three-arm P4 isomorphism or actual blind reviewer independence. |
| `V3/run_h2r2.py::drive` | `T/test_v1_2_h2_freeze_v3.py::test_the_driver_records_the_base_from_the_governance_repository` | Prelaunch actual path/base equality or an H4 driver. |

## Proposed sequence

- **T70 — contract and binding:** freeze approved task list, arm materials, metrics, allocation and immutable registry; assert actual worktree identity and base SHA before launch. Test wrong repo/path/SHA and missing material fail closed.
- **T71 — three-arm carriers:** build pinned extraction manifest and source/output hashes from `ARMS.md`; FULL and MIN are distinct, INJECT receives MIN. Use common external delivery path, isolated homes and readback, with adversarial missing, substituted, inherited and stale carrier tests. No in-tree contamination.
- **T72 — deterministic injection:** apply registered F-010 only in INJECT at an explicitly frozen stage; archive before/after hashes, target, operation and verification. Prove persistence at acceptance, verify clean control, expected N7 rejection and complete-green escape detection; failed injection is INVALID.
- **T73 — M1 counter and event capture:** freeze step dictionary, evidence semantics and deduplication; capture commands/files, interruptions, all gate outcomes and provenance. Test duplicates, retries, absent streams, unobservable steps and forged/partial evidence; unknown is not zero.
- **T74 — P7 and acceptance:** bind Ruff, task oracle and N7 to exact candidate/config; run positive and negative controls and real-path/config checks, including execution path. Test broken gates, timeouts and non-load-bearing controls never produce PASS. t01 is a false-green control, not an outcome oracle.
- **T75 — blind independent review:** implement common three-arm schema and projection; verify same fields, leak scans, adversarial identifiers, review independence and blind receipt. Protect mapping, pin evidence SHA, test leakage and disagreement yield VOID/UNKNOWN.
- **T76 — durable evidence and decision engine:** validate approved persistent non-temporary path including aliases, integrity and restart reread; retain invalid attempts. Implement the registered mutually exclusive precedence and no-teeth counterexample; test missing samples, early stops, false-pass and incomplete gates. Power and costs require owner approval before formal operation.
- **T77 — isolated integration and review:** run focused and full mechanical tests including adversarial cases and delivery canary, then independent review against exact candidate; only after all P1–P7 and task gate close can an authorized experiment be considered. This plan grants no build or run authorization.

## Limitations and risks

V3's standalone worker repository is history-free; history-dependent tests can fail equally at base and candidate. Its outside-repository wrapper avoided in-tree contamination in its own recorded measurement; that does not prove H4 delivery neutrality or startup guidance isolation (`V3/README.md` §2–3). Static audit cannot see every dynamic access; OS enforcement, egress checks and a runtime canary remain necessary (`V3/README.md` §3). V3's two-arm projection and filesystem snapshots are narrower than H4's three-arm blind protocol and durable recovery. N7 does not prove CI execution, alternative config binding, real-path exclusions or stale ignores (`experiments/v1.2/gate-load-bearing/README.md`); inspect actual config/path and independently exercise controls. Operator, carrier or defect leakage can invalidate blinding; test normalized bundles and retain a blind receipt. Sample scarcity and post-hoc oracle choice threaten validity: resolve `OPEN_QUESTIONS.md` before freezing and retain the strict-rule results. Costs and power remain unknown; pre-register caps and calculations rather than treating the minimum N as adequate.
