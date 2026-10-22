# Freeze v2 — pinned candidate materials (acceptance pending)

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
    --materials <commit> --out $H/freeze-v2/delivery-anchors.json
    (T2 recorded 1dbcf3f; re-measured at the T14 materials fb9ce4f — every row identical
     except the recorded commit, so the PRE/POST numbers below are the same measurement)
Gates: the task oracle and the full scripts/tests suite, PRE vs POST delivery, zero worker edits,
compared by the SET of non-passing test ids (not exit codes: every A_REPAIR oracle is red at its
base, and round 1's t01 went 1 -> 4 failures without changing rc).

RESULT  neutral tasks: CODEBUDDY slot 0/10, AGENTS slot 0/10, WRAPPER slot 10/10.
  oracle      newly-not-passing ids in 4/20 CODEBUDDY cells, 7/20 AGENTS cells, 0/20 WRAPPER
              cells. No newly-passing ids in any slot. Every cell has ran_delta = 0.
  full suite  newly-not-passing ids in all 20 CODEBUDDY and all 20 AGENTS cells, in BOTH arms:
              the repository's single-declaration scans
              (test_seam_contract_partitions, test_p1_t10/t11/t12 "declared exactly once") read
              every non-test text file under the root, so the in-tree copies — H2_WARM/ reference
              copies and a carrier that restates AGENTS.md — become second declaration points.
              Replacing AGENTS.md (AGENTS slot) additionally breaks the tests that read AGENTS.md
              (test_ticket_gate_wiring, test_p1_t09 section-ten checks).
  WRAPPER     every oracle and full-suite PRE/POST pair has identical non-passing sets and
              return codes, ran_delta = 0, no newly-passing or newly-not-passing id (20/20 cells).
              Skip, expected-failure and unexpected-success statuses count as non-passing;
              none occurs in this measurement.
```

Consequence: under §6.4 no shortlisted task is admissible with IN-TREE delivery, in either slot;
all 10 are delivery-neutral with the WRAPPER layout in §3.
This is the round-1 t01 contamination mechanism, now measured on every base. It is attributed to
the experiment's delivery, not to the tasks, and is recorded rather than normalised (§4.6).
The wrapper keeps the carrier and WARM bundle outside the repository root. The isolated runtime
canary remains a separate, pending acceptance check; delivery neutrality alone does not prove
startup guidance isolation.

## 3. Worker runtime and delivery layout (operator decision 2026-10-19)

```text
RUNTIME   opencode (CLI 2.0.25), model opencode-go/deepseek-v4.1-flash, in an ISOLATED profile
          (HOME and XDG_* redirected to a dedicated profile directory outside every repository:
          no user plugins, MCP servers, skills, memory or global AGENTS.md; autoupdate off;
          `run --standalone`, so no shared background service). The profile is logged in once
          by the operator; credentials never enter this repository.
RUNS_ROOT H2_RUNS_ROOT = `<SHARED_RUN_ROOT>`: an operator directory in the macOS Shared folder,
          outside every home and every git repository, with NO ancestor carrying `.agents`,
          `.opencode`, `.claude`, `AGENTS.md`, `CLAUDE.md` or `opencode.json`.
          WHY (F4): opencode discovers `.agents/` and `.opencode/` by walking UP from the cwd, past
          the redirected HOME. A run root below the operator's home re-admitted ~185 user skills;
          with the root outside every home only the two built-in skills `opencode` and `report`
          appear, identically in both arms. `prepare` refuses a run root that is under the
          operator's HOME or below any such ancestor.
LAYOUT    <run>/                 worker cwd (not a git repository)
            AGENTS.md            the arm's carrier (control: header + AGENTS.md + footer;
                                 variant: carriers/H2_LEAN_BOOTSTRAP.md) — the ONLY guidance
                                 opencode loads at startup (canaries; re-checked in
                                 the isolated profile once it is logged in)
            H2_RULES.md          RULES.md at the materials commit
            H2_WARM/             the S3 WARM owners at the materials commit
            repo/                the task worktree at the base — NO delivered file inside it,
                                 so §2's in-tree contamination cannot occur
WHY       measured on 2026-10-19 with canary instruction files: opencode loads the cwd's
          AGENTS.md at startup; a repository's own AGENTS.md (and nested ones) are ATTACHED to
          the first read of a file beneath them; the user's normal profile also injects its
          global AGENTS.md, MCP servers and a plugin agent.
DISCLOSED CONFOUND  the task repository's own (base-era) AGENTS.md is attached to BOTH arms on
          the worker's first read inside repo/. Neither arm can be kept from it under this
          runtime. The arms therefore differ in the STARTUP carrier (full current-era HOT vs
          lean carrier + routed WARM), not in whether any full governance text is reachable.
          A null difference is reported as INSUFFICIENT_EVIDENCE, never as DISCLOSURE_SAFE on
          this ground alone.
```

## 4. What is frozen

[freeze-manifest.json](freeze-manifest.json) pins 36 files: the registry, run plan, brief,
protocol, runtime/measurement/generator modules, the per-run collector and acceptance
(`collect_v2.py`, `run_acceptance_v2.py`) with the scope rules (`scope_v2.py`), the sanitised
canary fixture, route measurements, admission inputs, routes, carrier bytes, report template,
rubric and validator. The same hashes are independent literals in
`experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py`; the manifest itself has a separate literal
hash there. Tests reject a one-byte mutation of each of these 37 files on a temporary copy.
README, the implementation plan, review log and CODEX_REPORT are operator documents outside
this byte freeze. The §3 confound must remain byte-equal to protocol-v2.md.

The content-freeze commit is the T14 re-pin commit; its parent and the shared run materials are
`fb9ce4f80286c8c365d66bd8c9ed7df985f7b7a9` (the T13 commit). The delivered payload — carrier
bytes, `RULES.md`, the WARM bundle, routes and the shortlist — is byte-identical to the T8
materials `042f2244e453c79daa0ed50d72759a4583bcc43d`; what moved forward is `wrapper_delivery.py`
(T13's run-root refusal) and the four programs/fixtures the F1/F2 fixes added. Because the
runner program changed, the T2 delivery anchors were re-measured at the new materials instead of
being carried over: [delivery-anchors.json](delivery-anchors.json) records that re-measurement
(materials `fb9ce4f`, same 10/10 WRAPPER neutrality, same per-task PRE sets). The original T2
measurement commit `1dbcf3f2d3bc9ec0c230c36784db6adcc2a8713a` is kept in the record because the
PRE baseline itself did not move. T14 regenerated the run plan before hashing. The final
default-branch merge remains the review/history anchor; hashes alone are not acceptance.

Registry scope interpretation (superseded by F1, CODEX_FIXES_1 T10): the earlier reading of “allow
everything else in repo/” reused round-2 n01/n02's empty deny-prefix list. That list let an added
`scripts/tests/json.py` shadow the stdlib import the frozen oracle resolves, so `deny_prefixes` is
now `scripts/tests/` for every task: no add, modify, delete or rename inside the directory
`unittest discover` imports from. Every base `scripts/tests/` file and each oracle stay
individually denied, the worker contract prohibits changing any test, and every added or renamed
path is held to the validator's `shadow_paths` rule plus the startup-hook refusal (protocol-v2 §7).
The re-pin definition (materials = parent of the re-pin commit, proven byte-equal at HEAD) and this
scope decision are recorded for independent acceptance in CODEX_REPORT.md.

## 5. Before the first run

No H2-R2 run was executed by the implementer. All of the following remain operator/Claude work:

1. **Claude runs the isolation canary in the logged-in isolated profile and records the verdict.**
   From the repository root, with `H=experiments/v1.2/h2-lazy-disclosure`, `PY` set to the pinned
   interpreter and `H2_RUNS_ROOT` set to `<SHARED_RUN_ROOT>` (§3: in the macOS Shared folder,
   outside every home, no discoverable ancestor):

   ```bash
   $PY $H/freeze-v2/isolation_canary.py prepare "$H2_RUNS_ROOT/isolation-canary"
   ```

   This prints the exact `source ~/.h2-worker-profile/env.sh && opencode run --standalone
   --format json -m opencode-go/deepseek-v4.1-flash` command, including its cwd and prompt.
   Claude executes that printed command, checks the pinned CLI version, retains events/stderr,
   then records the parser verdict outside the repository:

   ```bash
   $PY $H/freeze-v2/isolation_canary.py check "$H2_RUNS_ROOT/isolation-canary/events.jsonl" > "$H2_RUNS_ROOT/isolation-canary/verdict.json"
   ```

   Require wrapper-at-startup, repo-only-after-read and nested-after-read evidence, with no
   observed MCP/plugin/global/user/skill contamination beyond the two built-in skills `opencode`
   and `report` — a disclosed, arm-symmetric fact of this runtime, not a delivery difference.
   The parser covers observable events; inspect the live evidence and profile rather than
   claiming visibility into hidden context.

2. **Fresh DeepSeek review of the exact final freeze candidate SHA.** Review this plan, the full
   final diff, registry/scope interpretation, declared confound, scoring deviations and both
   anchors. Run the pinned tests and manifest check. This is an independent review, not the
   implementer's self-check. Any repair produces a new SHA requiring a fresh matching review.

3. **Merge path per [protocol.md §12](../protocol.md#12-收尾--合并门part-3032).** Enumerate the
   applicable independent reviews, bot output, inline/conversation threads and configured CI
   at the final SHA; disclose missing channels, settle findings, obtain lawful integration
   authority, then follow the serial integration and remote-verification path. No push, PR,
   merge or actual experiment is authorized by this implementation hand-off alone.

The run protocol is [protocol-v2.md](protocol-v2.md), the full implementation receipt is
[CODEX_REPORT.md](CODEX_REPORT.md). Start execution only after the external prerequisites and
the separate run authorization are satisfied.
