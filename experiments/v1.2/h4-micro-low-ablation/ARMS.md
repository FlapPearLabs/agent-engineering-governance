# H4 arms — design draft, not a freeze

Authority and eligibility: `experiments/v1.2/mechanization-gap/experiment-protocols.md` §0, §2 and §4; `rule-migration-matrix.md` R-V12-036..046 and `rule-inventory.md` §C, both under `experiments/v1.2/mechanization-gap/`. R-V12-042 is a selection constraint: use real MICRO/LOW tasks only, and preserve the applicable independent review and escalation requirements outside the experimental prompt. This experiment cannot waive A-layer authority, safety, or repository acceptance policy. No outcome proves removing governance generally is safe.

## Exact procedural rule set

These eleven IDs are the FULL treatment; the MIN treatment supplies **none of these procedural instructions as prompt process**. The classification column in the migration matrix is not the authority-layer designation. Source for every entry is `rule-inventory.md` §C and canonical `AGENTS.md` §2–§4.

| ID | FULL includes | MIN prompt |
| --- | --- | --- |
| R-V12-036 | DAG-ready is not start permission; no START_ALL | omitted |
| R-V12-037 | Stage parallelism and barrier: packet, conditional external review, repair/approval, integration, frontier | omitted |
| R-V12-038 | owner conflict: merge ticket, serial chain, or authorized owner split | omitted |
| R-V12-039 | no-DAG stage fallback | omitted |
| R-V12-040 | complete ticket-lane lifecycle in canonical order | omitted |
| R-V12-041 | static gates after implementation and before dynamic GREEN | omitted |
| R-V12-042 | LOW/MEDIUM/HIGH review and grounding bindings | omitted as instruction; independently enforced eligibility/review obligations remain |
| R-V12-043 | listed L2 escalation triggers | omitted as instruction; actual escalation obligations remain |
| R-V12-044 | LOW escalation boundary | omitted as instruction; actual escalation obligations remain |
| R-V12-045 | seam-first order and prohibited reverse order | omitted |
| R-V12-046 | four decomposition disciplines, including mandatory POST gate | omitted |

## ARM_PROCESS_FULL and ARM_PROCESS_MIN

FULL carries the canonical current procedural governance, including all eleven IDs above, plus the common safety/authority constraints, actual mechanical gates, and the same task acceptance contract. MIN carries only applicable A-layer invariants, the identical gate requirements and task acceptance contract; it must not include the eleven process instructions, paraphrases, or incidental full governance files. Common gates and contractual requirements remain operative even when a procedural rule names them. Removing them from the prompt does not remove external policy or independent review. An actual unavoidable carrier or environment that re-injects process instructions invalidates the intended contrast rather than being silently called MIN.

P2 build design, **ASSUMED until implemented and tested**: pin an exact materials commit; read the canonical `AGENTS.md` §2–§4 and referenced canonical sources with `git show <materials-sha>:<path>`. A versioned extraction manifest maps each rule ID to exact byte ranges / heading anchors and source hashes; verify unique anchors, complete canonical text, ID coverage, and no overlapping or stale ranges. Generate FULL deterministically from all required canonical governance sources and MIN from explicitly pinned A-layer invariant source texts, gate commands and task contract only; do not treat a manually rewritten summary as canonical. The manifest must explicitly identify the A-layer sources and immutable platform constraints without relabeling repository text as A-layer. A missing source, conflicting constraint, or ambiguous extraction fails closed. Record materials SHA, input and output hashes, selection manifest, actual delivered path, and readback digest. Deliver via a common harness path in isolated homes, reject missing, substituted, or hash-mismatched files, and test that neither inherited guidance nor references reintroduce omitted process; source and destination checks must cover both arms. `freeze-v3/wrapper_delivery.py::prepare` and its existing delivery test are reusable building blocks, not proof of an H4 carrier.

## ARM_INJECT

Same carrier as MIN. Primary control: F-010, an E3 real defect (`failure-mechanism-map.md` F-010): in a disposable candidate copy, deterministically hollow Ruff's selected rules while placing the known F841 control at `scripts/n7_control.py` as specified in `experiments/v1.2/gate-load-bearing/gates.json`. The harness injects after the worker candidate is captured, without announcing it in the agent prompt; preserve the untouched candidate, record exact base/candidate IDs, pre/post hashes, mutation, path, tool/command, exit status, and stdout/stderr in the durable private evidence. The control must itself be confirmed present, in scope, and F841-positive under the unmodified configuration.

The catching gate is the N7 Ruff load-bearing probe, **not Ruff's exit status alone**: run `experiments/v1.2/gate-load-bearing/probe_gates.py` against the mutated candidate tree with `--worktree`, which must reject the hollow configuration / missed positive control. A task-specific oracle and ordinary Ruff are separate M2 gates; no generic oracle is presumed to detect this configuration defect. If a valid, correctly applied control is missed and the designated complete acceptance procedure reports green, the registered conclusion is `MECHANICAL_ACCEPTANCE_HAS_NO_TEETH`; command/environment failures, missing controls, or an unverified injection are INVALID/insufficient evidence, not a green escape. N7's detection scope and limitations are in `PRECONDITIONS.md` P7. F-015 is not selected: there is no demonstrated H4 durable-path catching gate yet, and claiming one would manufacture evidence.
