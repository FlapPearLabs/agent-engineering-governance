# T50 fork report

The v3 fork has separate registry, run plan, run IDs, manifest and test anchors. Its materials
commit is the parent of the T50 commit. Historical v2 documents and fixtures are context, not
evidence that a v3 run occurred. No model runs were performed.

Delivery anchors: `WRAPPER: 10` neutral tasks. Manifest build: 60 frozen files, delivery payload
verified equivalent to the measured payload. The v2 and v3 manifest checks both returned PASS.
The full experiment suite returned `Ran 733 tests ... OK`; the scripts suite returned
`Ran 602 tests ... OK`. Ruff passed; governance returned 35/35 and public release returned
`VIOLATIONS=0`. Earlier runs exposed stale fixture hashes, a v2 registry error assertion and
shared module names; the final suite passed after preserving the historical fixtures, updating the
assertion and isolating the v3 test module loader.

`git diff --cached --check` reports an extra blank line at EOF in the two copied historical
worker sandbox fixtures. Their bytes are retained as recorded; this whitespace check is not among
the T50 gates, and the two fixtures are pinned by the v3 manifest.

## T53 worker tool surface (opencode)

Path taken: **the config disables the tool**, so the `TOOL_ALLOW` fallback was not used. `execute`
stays out of `freeze-v3/access_audit.py`'s `TOOL_ALLOW`: the audit still treats a `code` program it
cannot resolve as `TOOL_NOT_ALLOWED` evidence, and the tool no longer reaches a launch.

The frozen profile now carries `"permission": {"execute": "deny"}` next to the existing
`question` deny, in the one template
(`freeze-v3/worker-profile/opencode.json`) that `sandbox_v2.fresh_home` copies into every fresh
home: `home-<n>` (worker), `audit-home-<n>` (per-run auditor) and `probe-home-<purpose>-<n>`
(reachability). Both arms of `run-plan-v3.json` name the same profile, so the two arms are
identical by construction, and a test asserts exactly that.

Evidence, all without a model call, opencode 2.0.25, THROWAWAY HOME under the shared review
directory (`$HOME`, `XDG_CONFIG_HOME=$HOME/.config`, `opencode service set port <free>` first so no
service setting of the operator is touched):

- `opencode --version` -> `opencode v2.0.25`.
- `opencode debug agents` -> `[]`. This build has no agent/tool listing surface, so the absence of
  a tool cannot be read from that command; it is recorded here as a measured negative.
- `opencode debug config` with the frozen template before this task -> `info.permissions` held only
  `{"action": "question", "resource": "*", "effect": "deny"}`.
- `opencode debug config` with the template after this task -> `info.permissions` holds
  `{"action": "execute", "resource": "*", "effect": "deny"}` and the same `question` rule, and the
  command exits 0 (no unknown-key diagnostic). The recorded output, home path sanitised to
  `<PROFILE_HOME>`, is committed as `freeze-v3/fixtures/preflight-debug-config-execute-deny.json`.
- The legacy form `"tools": {"execute": false}` normalises to the same rule; `permission` was
  chosen because the frozen template already uses that map for `question`.
- Why that rule removes the tool (local binary, 2.0.25): a config document's `info.permissions` are
  appended to every agent's rule list (`agent.transform`, after the built-in `{"action": "*",
  "resource": "*", "effect": "allow"}`); the tool snapshot drops a tool whose last matching rule is
  `effect: "deny"` with `resource: "*"`, and the Code Mode `execute` tool is only built when
  `execute` is not denied that way. This is the same mechanism the frozen `question` deny already
  relies on (protocol-v3.md, the `permission.question = "deny"` rationale).

The canary is the live instrument (still no model call in this task): `prepare` now requires one
more machine-readable line, `H2_CANARY_TOOLS <comma-separated tool names>`, and `check_stream`
fails closed with `NO_TOOLS_LINE` when it is missing or unparseable, `TOOLS_LINE_INCOMPLETE` when
`read` is not in it, and `EXECUTE_TOOL_PRESENT` when `execute` is listed or named as a `tool_use`.
The pre-T53 pass fixture (sources line only) now fails on the missing tools line and is kept as the
regression for that; the new synthetic pass fixture adds the tools line to the same live stream, so
`event_count` stays 10.

Pin failures caused ONLY by changed freeze-v3 files (expected until T54 re-pins; no pinned literal
was edited):

- `FreezeManifest.test_two_independent_anchors_and_materials_binding`
- `FreezeManifest.test_one_byte_mutation_of_every_frozen_file_is_rejected`

Both fail because `freeze-manifest.json` still pins the pre-T53 bytes of
`freeze-v3/isolation_canary.py` and `freeze-v3/worker-profile/opencode.json`.
`freeze-v3/build_manifest.py check` therefore reports exactly those two paths as mismatches; the
T53 gate set only requires `freeze-v2/build_manifest.py check`, which returns `PASS`.

Gates run in this worktree (PYTHONPATH unset, TMPDIR resolved with `pwd -P`):

- `python -m ruff check .` -> `All checks passed!`
- `python scripts/validate_governance.py` -> `35/35 checks passed`
- `python scripts/validate_public_release.py` -> `VIOLATIONS=0`
- `python experiments/v1.2/h2-lazy-disclosure/freeze-v2/build_manifest.py check` -> `PASS`
- `python -m unittest discover -s experiments/v1.2/tests -p test_v1_2_h2_freeze_v3.py` ->
  `Ran 214 tests`, `FAILED (failures=2)`, both the pin tests named above. With an unresolved
  `TMPDIR` the same module also reports two `/var` vs `/private/var` path-equality failures that
  this task does not touch; resolving `TMPDIR` (as the freeze protocol does) removes them.

Not verified here: no live canary run was made (models are out of scope for T53), so the
`H2_CANARY_TOOLS` line has not yet been seen coming from a real session; that observation belongs
to the operator/T54 pilot. The auditor's own launch reads no bot/agent configuration different from
the worker's, but the auditor prompt itself was not changed by this task.
