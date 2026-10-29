# Freeze v2 — acceptance round 2 of 86ac104: CHANGES_REQUIRED (fix plan T15–T17)

Implementer: opencode (deepseek-v4.1-flash). The ground rules, NEVER TOUCH list and GATES of
CODEX_PLAN.md §0 still bind every task; write scope unchanged (freeze-v3/** and
experiments/v1.2/tests/test_v1_2_h2_freeze_v2.py).

Accepted at 86ac104 (verified by Claude): write scope; frozen surfaces untouched; identity; every
gate green on independent re-run (35/35, VIOLATIONS=0, scripts 602 OK, experiments 347 OK);
F1–F4 closed, reproduced end to end through wrapper_delivery → collect_v2 → run_acceptance_v2 on
f01 in a run root outside every home:

```text
T13  prepare under the operator home         -> rc=1 RUN_DIR_UNDER_OPERATOR_HOME
F2   untouched base                          -> REJECT WORKER_NOT_PASSING:RESOLVED/SYMLINKED
F1   added scripts/tests/json.py shadow      -> REJECT WORKER_SCOPE_DENIED + WORKER_SHADOWS_IMPORT:json
F2   candidate's non-test delta on B'        -> ACCEPT
F3   recorded clean stream / home stream     -> PASS / FAIL SKILL_CATALOGUE_CONTAMINATION
```

## Findings

```text
F5  P2  CANARY FALSE POSITIVE ON A CLEAN LIVE RUN. A fresh live canary at 86ac104 (isolated
        profile, run root outside home) behaved correctly — wrapper AGENTS.md only at startup,
        repo/nested attached after their reads, skills {opencode, report} — but `check` returned
        FAIL [MCP_CONTAMINATION, PLUGIN_AGENT_CONTAMINATION]. The model wrote
        "- Plugin agents: none present" and "- MCP servers: none configured/present in this
        context"; text_reasons() flags any line containing "mcp"/"plugin" unless NEGATION_RE
        matches, and the model's wording changes every run. Free-text self-report is not a
        reliable instrument for this claim.
F6  P2  WORKER CAN STALL SILENTLY. The isolated profile's resolved `build` agent allows the
        `question` tool; in a non-interactive `opencode run` a worker that calls it waits forever
        with no output (the same silent stall that cost four review runs). Nothing frozen pins
        the profile's config, so its content is an unrecorded experimental input.
```

Deterministic evidence that IS available (measured by Claude in the isolated profile, cwd = a run
dir outside home): `opencode debug paths` (no service needed) prints home/data/config/cache/state
all under the profile home; `opencode debug config` (needs the profile's own service port) prints
exactly two sources — the profile's `opencode.json` (`mcp: {}`, plugin list empty) and the
profile config directory — and no project or global source.

## T15 — close F5: deterministic preflight + structured canary line

- `isolation_canary.py preflight <run_dir> --profile-env <env.sh>`: runs ONLY
  `opencode debug paths` and `opencode debug config` (never `run`, never a model) with the profile
  env and cwd = run_dir; writes `<run_dir>/preflight.json`; PASS iff every printed path is under
  the profile home, the config sources are exactly {profile opencode.json, profile config dir},
  and the profile opencode.json bytes equal the frozen template of T16. Unit-test the parser of
  both outputs on sanitised fixtures (real outputs are given at hand-off).
- Canary prompt: the wrapper canary AGENTS.md additionally requires one machine-readable line
  `H2_CANARY_SOURCES mcp=<integer> plugin_agents=<integer> skills=<comma-separated names>`.
  `check` takes the MCP / plugin / skill claims ONLY from that line (missing or malformed line ->
  FAIL NO_SOURCES_LINE); free prose no longer decides them. Keep every ordering / attachment /
  path rule. Tool-use events naming an `mcp__` tool still FAIL regardless.
- Fixtures: the fresh 86ac104 stream (given at hand-off, sanitised) must PASS under the new rule
  only if it carries the line — it does not, so build the PASS fixture from it by adding the line
  as a NEW, clearly-labelled synthetic fixture, and keep the original as a regression fixture
  proving the old false positive cannot recur (it must yield NO_SOURCES_LINE, not
  MCP_CONTAMINATION).

## T16 — close F6: frozen worker-profile config

- `freeze-v3/worker-profile/opencode.json`: the exact profile config —
  `{"$schema":"https://opencode.ai/config.json","autoupdate":false,"share":"disabled",
  "plugin":[],"mcp":{},"permission":{"question":"deny"}}` (keep any key the current profile file
  has; add `permission.question = "deny"`; verify the key name against opencode 2.0.25's config
  schema text in the binary-independent docs you can read locally — do not guess silently: if
  unsure, say so in the report).
- protocol-v2 §4 and README §3: the operator installs this file into the profile before the
  first run; preflight (T15) proves byte equality before EVERY run; a per-run wall-clock limit
  (state the value, e.g. 90 min) after which the run is registered INVALID (protocol §8),
  never silently re-run.
- Pin it in the manifest (T17).

## T17 — re-pin and report

Regenerate the run plan (materials per the T8 rule), the manifest and the test literals; append
a "T15–T17 (implementer: opencode deepseek-v4.1-flash)" section to CODEX_REPORT.md in the same
evidence style. One commit per task; gates before each.
