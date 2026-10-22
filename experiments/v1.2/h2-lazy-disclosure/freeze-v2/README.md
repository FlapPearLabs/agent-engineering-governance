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
    --materials <commit> --out $H/freeze-v2/delivery-anchors.json   (recorded: 1dbcf3f)
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
LAYOUT    <run>/                 worker cwd (not a git repository)
            AGENTS.md            the arm's carrier (control: header + AGENTS.md + footer;
                                 variant: carriers/H2_LEAN_BOOTSTRAP.md) — the ONLY guidance
                                 opencode loads at startup (canaries; PENDING re-check in
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
