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

### T51a — partial implementation

Registration artifact hashing records symbolic links by target-string hash and records special
file types without opening them. Regular files are opened with `O_NOFOLLOW` and checked after
opening. A focused test covers link hashing, non-descent and a FIFO timeout.

Not completed: snapshot and other driver copies still need the requested no-follow treatment;
`sandbox_v2.py` snapshot code is outside this task's allowed ancestor-only edits. The cell layout
is not implemented: the existing `wrapper_delivery.py` driver-root calculation requires changes
outside the allowed write scope. Consequently T51a is not complete and the new test does not
claim the snapshot or cell-layout acceptance criteria.

Checks: the new unittest module ran 1 test (OK); ruff on the changed Python files passed;
`validate_public_release.py` reported `VIOLATIONS=0`; the freeze-v2 manifest check reported
`PASS` with no mismatches. The full freeze-v3 suite was not run.

### T51b — snapshot and cell layout

Snapshot copies now reject non-directory target collisions, create files exclusively without
following links, and open regular sources nonblocking with no-follow and a post-open type check.
The gate copy uses the same snapshot mechanism and rejects unreadable or colliding entries.
Runs use `.cells/<run_id>/<run_id>` with a private cell parent; legacy flat runs remain readable,
and driver artifacts remain under `.driver/<run_id>`. This closes T51a's identified snapshot
and cell-layout gaps. The directory-collision test simulates the case-folding collision by
planting a symlink at the target; it does not exercise an actual case-insensitive APFS collision.

Checks: driverfs unittest module (6 tests); ruff for changed Python files; public-release
validator `VIOLATIONS=0`; freeze-v2 manifest check `PASS`; `git diff --check`. The full freeze-v3
suite and re-pinning are deferred to T54; no live worker or platform sandbox launch was run.
