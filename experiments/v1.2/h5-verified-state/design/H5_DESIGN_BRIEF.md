# H5 — Verified State + Fresh Episode Recovery: design preparation (brief)

Owner decision (2026-10-29): prepare H5's design in parallel with N7. **Design only**:
- no harness build;
- no model runs;
- no runs root;
- no protocol freeze.

Implementer Codex (gpt-6.1-terra); Claude accepts. The output is what N5's entry criteria ask
for (TREE_LEDGER N5):

```text
ENTRY_CRITERIA = N6.5 §0 全部满足 + 一个可重放的 append-only ledger 形状被定义
```

Sources to read first:
- `experiments/v1.2/mechanization-gap/experiment-protocols.md` §0 and §3. These are the frozen
  H5 shape: CONTROL_H5 / VARIANT_H5, M1–M7 and the result vocabulary.
- `longhorizon-mechanism-map.md`: M-02 Verified State, M-06 Fresh Episode, M-12 Completion
  Semantics.
- `failure-mechanism-map.md`: F-014 (the reproducible exec-channel failure, exit 137/139) and
  F-013 (closure = merged + post-merge CI).
- `experiments/v1.2/h2-lazy-disclosure/freeze-v3/`: the hardened harness whose components may
  be reused.
- Its `HARNESS_V3_PLAN.md` and `CODEX_REPORT.md`: what was learnt, especially the T51–T56
  failure history.

## Deliverables (all under `experiments/v1.2/h5-verified-state/design/`)

1. **PRECONDITIONS.md** — §0 P1–P7, one by one, for H5. For each:
   - what it requires of H5 specifically;
   - whether a freeze-v3 component already satisfies it (cite the file/function and the test
     that proves it), or what must be built;
   - the evidence that will close it.

   P7 depends on N7 (#45, in progress in parallel): state exactly which H5 measurement relies on
   a gate being load-bearing (M3 FALSE_CLOSURE: "acceptance predicate not satisfied when
   declaring done"), and what H5 needs from N7's mechanism.
2. **LEDGER_SHAPE.md** — the replayable append-only ledger, which is the N5 entry item.
   - **Record types** with fields, at minimum:
     - goal;
     - episode start/end;
     - state claim;
     - verification result, bound to an exact SHA/worktree and to the predicate it checked;
     - failure evidence;
     - remaining work;
     - supersession.
   - **Rules:**
     - append-only, with a hash chain or equivalent integrity;
     - the replay/fold semantics that derive "verified state" — only verified claims enter the
       state;
     - stale-SHA rejection (M2);
     - wrong-worktree/SHA detection (M1);
     - what "closure" means (M3; align with F-013);
     - how a fresh episode is seeded from the fold.
   - **Must distinguish** "verified state works" from "a snapshot happened to be enough": the §3.1
     requirement that the variant's state is a replayable ledger, not a snapshot. Explain how the
     design makes that distinction measurable.
   - **Reference implementation:** a small pure-Python reference fold is welcome
     (`ledger_ref.py` plus `experiments/v1.2/tests/test_v1_2_h5_ledger_shape.py`). Restrictions:
     - no models, no network, no I/O beyond temp dirs;
     - tests include adversarial cases (tampered record, out-of-order append, stale-SHA
       verification, a claim without verification).

   The reference fold is a design artefact, not the harness.
3. **HARNESS_PLAN.md** — how H5 would be run, written as a task plan for later (T-numbered,
   like `HARNESS_V3_PLAN.md`), not built now:
   - **Arms:** the two arms made concrete on this machine's runtime (opencode, frozen model):
     - what "long-lived orchestrator context + memory" is operationally;
     - what a "fresh episode" is;
     - how both arms run the SAME number of fresh episodes (§3.1).
   - **Tasks:**
     - the source: multi-step tasks with mechanically checkable end states; say whether H2's
       frozen-oracle tasks can be chained, or what else;
     - the minimum count per arm (≥2, per §4).
   - **Measurements:** a mechanical detector for each of M1–M6 (inputs, predicate, failure
     mode), and how M7 (independent review) is blinded.
   - **M4 fault injection:**
     - how the real exit-137/139 channel failure (F-014) is triggered reproducibly, or injected;
     - how recovery is scored.
   - **Reuse map:** which freeze-v3 components are reused unchanged:
     - sandbox/read allowlist;
     - egress proxy;
     - cells;
     - link-safe snapshot;
     - violations;
     - access audit;
     - scheduler;
     - audit retry.

     Also what is new, and which known v3 limitations matter for H5.
   - **Pre-registration list:** everything that must be frozen before any run:
     - decision rules mapping M1–M7 to the four result words;
     - stopping conditions;
     - validity rules.
   - **Risks and costs:** model calls per run, wall time, and the top risks, each with a
     mitigation.
4. **OPEN_QUESTIONS.md** — the decisions only the owner can make, each with options and a
   recommendation (for example: task source, episode count, whether M4 uses the real channel
   failure or an injected kill).

## Rules

- Write only under `experiments/v1.2/h5-verified-state/` and the one new test module.
- Never touch canonical files, `scripts/`, `references/`, `.github/`, `freeze-v2/`, `freeze-v3/`,
  `results-v2/`, or `TREE_LEDGER.md`. The ledger is updated by Claude at PR time.
- No `/Users/<name>` paths in committed files.
- Do not run opencode, any model, or `run_h2r2.py`. Do not create runs roots.
- Cite sources by repo path and section. Mark every claim about the runtime as MEASURED (with the
  command) or ASSUMED.
- Gates before committing:
  - ruff;
  - `scripts/validate_governance.py` 35/35;
  - `scripts/validate_public_release.py` VIOLATIONS=0;
  - the new test module, if any.
