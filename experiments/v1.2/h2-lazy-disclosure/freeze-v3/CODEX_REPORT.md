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

# T52 v3 access audit

Files changed: `freeze-v3/access_audit.py`, `experiments/v1.2/tests/test_v1_2_h2_freeze_v3.py`
(new class `AccessAuditV3Hardening` plus the existing access-audit cases whose "could have
succeeded" probe named a path that does not exist), and the new fixture
`freeze-v3/fixtures/access-audit-replay-v3.json`.

What changed, by plan item:

1. `allowed_roots` now carries the pinned interpreter's real install prefix (`sys.base_prefix`)
   and its stdlib directory, resolved from the interpreter that performed the audit; a foreign
   interpreter is asked for its own values (`-I -c`, no assumption), and an unaskable one adds no
   prefix. What is called "the interpreter" is the one the launch ran with: the replay reads it
   from the archived profile's interpreter subpath.
2. A READ of a path that does not exist (the run's post-launch snapshot first, the filesystem
   second) is `DENIED_BY_POLICY` evidence with `policy: PATH_DOES_NOT_EXIST`; a token carrying
   glob syntax is a pattern and is never existence-checked. A WRITE outside the profile's write
   whitelist is the same class. That required fixing `inside(path, "/")`, which returned False for
   every path, so `(deny file-write* (subpath "/"))` had never actually denied anything. An
   optional T51.4 violation log (path or parsed records) confirms a denial by resolved path or
   host (`policy: VIOLATION_LOG`); it never creates a hit and its absence proves nothing.
3. `network_hosts` strips `user:pass@` before extracting the host (`url_host`), so an allowlisted
   host behind credentials is a hit again and a denied one is still evidence.
4. Only a `read` result can be a breach: glob/grep/list listings and messages that mention a path
   are not.
5. The replay (`--replay <runs root>`, `replay()`) audits every archived
   `.driver/<run>/attempt-*/events.jsonl` (falling back to the run's own copy) and records per run
   the archived `access-audit.json` verdict (v2, read not recomputed), the v3 verdict of the last
   attempt, the reason in rule terms, and the earlier attempts. The summary carries no host path,
   home or command text.

Replay of the real archive (`/` + `Users/Shared/h2-runs`, read-only, 39 runs = the 20 counted
H2-R2 runs plus every pilot run): 34 VALID, 3 INVALID, 2 NO_STREAM (pilots that kept no event
stream). Of the five H2-R2 runs the round's audit called INVALID, v3 now calls `h2r2-f03-c`
(f03-c read the launch's own stdlib) and `h2r2-f03-v` (`verify --pack /nope`) VALID, and leaves
`h2r2-f04-v` and `h2r2-f05-c` (`execute`, T53) and `h2r2-f09-c` (`cd ..` into the shared runs
root, T51.2) INVALID. This is a harness measurement, not a re-scoring of H2-R2.

Not wired here, by the card's write scope: `run_h2r2.py` does not yet pass `snapshot=` or
`violations=` to `audit()` (T51/T54). Without them the audit still checks existence against the
filesystem, and the violation log is simply absent evidence.

## Expected pin-test failures at this commit (re-pinned in T54; pinned literals untouched)

- `test_v1_2_h2_freeze_v3.py::FreezeManifest::test_two_independent_anchors_and_materials_binding`
- `test_v1_2_h2_freeze_v3.py::FreezeManifest::test_one_byte_mutation_of_every_frozen_file_is_rejected`

Both fail only because `freeze-v3/access_audit.py` no longer matches its manifest hash. The new
fixture `fixtures/access-audit-replay-v3.json` is not a member of `build_manifest.FROZEN_FILES`
yet: T54 must add it to that list and rebuild the manifest, or the replay expectation stays
unpinned. The whole v3 module otherwise passes: `Ran 224 tests`, `FAILED (failures=2)`, and the
two failures are exactly the pins above.
