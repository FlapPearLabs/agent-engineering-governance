# H5 — owner decisions on the design's open questions

Owner decision (2026-10-29): "按推荐推进". Each question in
`design/OPEN_QUESTIONS.md` is answered with the recommendation written there. This file records
those answers.

This is **not** a protocol freeze and **not** run authorisation:
- no model, opencode or driver runs;
- no exploratory runs (Q5 needs a separate execution authorisation);
- no formal runs.

| # | Question | Decision (the recommendation) | Consequence for the build |
|---|---|---|---|
| Q1 | Task source | **A first.** Run a read-only suitability check on whether H2's real tasks can be chained. If dependency or independent-oracle conditions fail, fall back to **B**: other real historical multi-step tasks. Never fabricate a chain. | T62 runs as a read-only measurement now. |
| Q2 | Sample / episodes | **B.** Size by a power analysis decided before the formal experiment. 2 tasks × 2 episodes per arm is only the floor, not a guarantee. Both arms get equal episode counts. | The power analysis belongs to the formal pre-registration, not to this build. |
| Q3 | M4 fault | **A.** A controlled kill of an isolated child process. The external supervisor records the real signal and wait status. Extrapolation limits are stated: this is not F-014 whole-channel failure. | T64 builds the controlled-kill injector and its controls. |
| Q4 | Closure realism | **A.** An isolated stand-in simulates merge and post-merge CI. No claim of real merge or real post-merge CI may be made from it. | The closure predicate runs against a stand-in; its outputs are labelled as such. |
| Q5 | Thresholds / budget | **B.** A small exploration first, then separate registration of the formal experiment. The exploration needs its own execution authorisation, and its results never enter the formal sample. Without thresholds and power, the only possible verdict is `INSUFFICIENT_EVIDENCE`. | Nothing runs in this round. |
| Q6 | Durable evidence / trust boundary | **A.** A local persistent evidence directory outside any repo (`<H5_EVIDENCE_ROOT>`, a non-temporary local path), plus an independent chain-tail anchor that workers cannot write. Before use, check its permissions and that it can be recovered after a restart. No new external service. | The ledger takes the root and the anchor location as parameters; tests use temp dirs only. |
| Q7 | P7 and N7 | **A.** N7 is now closed (`experiments/v1.2/gate-load-bearing/`, PR #60). H5 adds positive and negative controls of its own for its composite closure predicate. | H5's closure predicate gets its own controls in the ledger tests. |
