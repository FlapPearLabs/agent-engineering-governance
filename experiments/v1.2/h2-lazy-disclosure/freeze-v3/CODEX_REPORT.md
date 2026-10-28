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

### T51d — sandbox reads and violation evidence

Added a read allowlist, interpreter and opencode prefix resolution, and a standalone unified-log collector; the driver is not wired here. On 2026-10-28 (Darwin 25, opencode 2.0.25), the five requested commands exited successfully in the candidate sandbox with a launch-local TMPDIR. Iterative unified-log inspection identified the listed system paths and Homebrew git dependencies. The live test observed a denial for its child PID. The profile does not set a launch tag; filtering uses event-message PIDs.

Limitation: the five commands still emit `file-write-data /dev/dtracehelper` denials. Thus the requested zero-denial measurement was not achieved; the write whitelist was kept unchanged. System roots are candidate measurements, not a proven minimal list. The full freeze-v3 suite and re-pin were intentionally not run. The new tests, lint, release scanner and freeze-v2 manifest checks were run separately; see session output for results.
