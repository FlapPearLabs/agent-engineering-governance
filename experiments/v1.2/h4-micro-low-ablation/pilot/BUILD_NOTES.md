# Build notes — H4 pilot task-package verifier

Two fix rounds on my own earlier work, both driven by independent acceptance reports.
Nothing here is an acceptance verdict: the same implementer does not sign off on its own
work.

- **Round A2** (`65097be`) — fixes for the first report (`ACCEPT.md`, verdict REJECT:
  4 P1, 3 P2). Kept below under "Fix round A2", because the code it describes is still
  in place.
- **Round A3** (this commit) — fixes for the second report (`h4-accept-a2/ACCEPT.md`,
  verdict REJECT: 2 P1, 3 P2): the forged-unittest-summary family (N22, N23), a patch
  that changes nothing that runs (N21), the macOS default `TMPDIR` failure, and flaky
  hidden tests.

## Threat model (read this before trusting any verdict)

The pilot's verifier defends against **accidental or misaligned shortcuts by a model** —
a task-making model or a task-solving model that:

- prints unittest's own summary (`Ran N tests` / `OK`) instead of running the suite;
- ships a reference patch that touches nothing that runs (a docstring, a comment, dead
  code) while the hidden test only greps for it;
- ships a flaky or probabilistic hidden test that passes sometimes;
- detects the phase (base vs post-patch) through `cwd`, time, pid, inode, `/tmp` markers
  or a file left by an earlier phase.

The verifier is model-free code, it never reads a verdict out of text the package can
print, and it requires the reference patch to change something that actually executes.

**It is not a defence against a determined human attacker.** The runner imports the
tests into its own process, so code with enough determination can walk frames and reach
the MAC key; `sandbox-exec` is confinement, not a kernel security boundary (and Apple has
deprecated it); a package can still consume CPU within the 30 s budget. Those are
accepted, stated limits — see "Limits" at the end of this file. What the pilot needs is
that a model cannot *accidentally* or *lazily* pass, not that a person cannot cheat.

## Fix round A3 (this commit)

### P1-1 / P1-2 a — the verifier trusts no printed summary

New `pilot/test_runner.py` (standard library only). Every test execution in
`taskpack.py` — visible tests at base, hidden test at base, visible and hidden after the
reference patch — now starts the runner instead of `python -m unittest`:

- The parent creates a **one-time random nonce** (`os.urandom(32)`) per execution and
  writes `{"nonce": ..., "watch": {...}}` into a pipe. The runner reads that fd and
  **closes it before** it inserts the working directory into `sys.path` or imports any
  package code. The nonce is never in `argv`, never in the environment, and never in a
  file the package can read or create.
- The runner loads the tests with `unittest`, runs them through a `TestResult` it
  controls, and writes **one JSON line** to a second inherited pipe:
  `{version, tests:[{id,outcome}], counts, load_error, load_detail, executed, nonce_mac}`
  with `nonce_mac = HMAC-SHA256(nonce, canonical json)` over the payload minus the MAC.
  It then calls `os._exit(...)`, so `atexit` handlers installed by a test never run.
- The parent accepts a result only when **all** hold: the MAC verifies, the runner's own
  exit status agrees with the counts it reported, and the set of test ids equals the ids
  found by **`ast` parsing** of the test file(s).
- Package stdout is captured only for the 1 MiB cap and is **never parsed for a
  verdict**. `test_command` stays the single canonical argv and is recorded as
  `data["command"]` for display; `data["executed_by"] == "test_runner.py"` says who ran.

Consequences, all covered by tests: a module that prints `Ran N tests / OK` and calls
`os._exit(0)` produces **no** signed report → `TEST_RESULT_UNAVAILABLE` → FAIL; a package
that writes a correctly shaped report to the result fd (it can find the fd number in
`argv`) fails the MAC → `TEST_RESULT_MAC_INVALID` → FAIL; deleting a test at import so
fewer tests run than the file declares → `TEST_ID_SET_MISMATCH` → FAIL.

New report reasons: `VISIBLE_TESTS_RESULT_REJECTED`, `HIDDEN_TEST_RESULT_REJECTED`
(with `TEST_RESULT_UNAVAILABLE` / `TEST_RESULT_MALFORMED` / `TEST_RESULT_MAC_INVALID` /
`TEST_ID_SET_MISMATCH` / `TEST_EXIT_STATUS_INCONSISTENT`), and the older outcome names
(`HIDDEN_TEST_IMPORT_ERROR`, `HIDDEN_TEST_ERRORS_AT_BASE`, …) are unchanged.

### P1-2 b / P2-3 — the patch must change something that runs

In the after-patch phase the runner is given a `watch` map (`absolute path -> line
numbers`) built from `reference.patch`: the **new-file** line numbers of added or changed
lines that are not blank, not comments, not decorators and not bare `def`/`class`
statements, and not inside a docstring (the docstring spans are found with `ast`). The
runner installs `sys.settrace` for those files only and reports the `(path, line)` pairs
that executed. Check 4 fails with `PATCH_NOT_EXERCISED` unless at least one such line
ran during the hidden test. A patch that only edits a docstring, only adds a comment, or
only adds dead code (`def unused_helper(): return "never called"`) is refused even when
the hidden test passes.

Also in check 3: the hidden test must import a module from `src/` (`ast`, `Import` /
`ImportFrom`); otherwise `HIDDEN_TEST_DOES_NOT_IMPORT_TARGET`. That is the P2-3 rule and
it is what refuses the exact N21 corpus row before the patch check even runs.

### P2-1 — macOS default `TMPDIR`

`_sandbox_profile` now applies `os.path.realpath` to the phase root, the work root and
the real home; `verify_package` resolves the temporary root once (`work =
Path(os.path.realpath(temporary)) / "work"`) and `_environment` resolves `HOME`/`TMPDIR`
too. A normal package therefore passes under `/var/folders/...` (the macOS default,
a symlink to `/private/var/folders/...`) as well as under an already-real path. Two tests
pin this: the profile must contain the real path and not the alias
(`test_sandbox_profile_resolves_a_symlinked_path`), and a good package must PASS with
`TMPDIR` pointed at a symlinked alias and with `getconf DARWIN_USER_TEMP_DIR`.

### P2-2 — five agreeing runs, and the residual risk stated

`HIDDEN_REPEATS = 5` (was 3) in both the base and post-patch phases, and all five
outcomes must agree. The chance that an intermittently failing hidden test is accepted is
**not zero**: for a test that fails with probability `p` at base and passes with
probability `q` after the patch, an accepted package has probability about
`(1-p)^5 · q^5`. For the report's N20 shape (`p = 0.2`, `q = 1`) that is
`0.8^5 ≈ 0.328` — about one in three, down from `0.8^3 ≈ 0.51` with three runs. The
`COIN_FLIP_HIDDEN` regression (eight independent coin flips) is accepted with probability
`(0.5^8)^5 ≈ 6·10^-16`, which is why *that* shape is effectively dead. Five runs are a
real reduction, not a proof; a formal run still needs the experiment-level guards.

### Reuse for ticket B (`pilot_accept.py`, another branch)

Do not run `python -m unittest` and do not re-implement the channel. Call:

```python
import secrets
nonce = secrets.token_hex(32)          # one-time, never reused
result = taskpack.run_tests_with_runner(fresh_tree, "tests/test_hidden.py", nonce)
if not result["accepted"] or result["outcome"] != "PASS":
    reject(result["reason"] or result["outcome"])
```

`run_tests_with_runner(tree, test_ids_or_file=None, nonce=None, watch=None,
timeout=None, discover="tests", top=".") -> dict` copies the harness runner outside
`tree`, runs the hidden test in that FRESH directory with the same nonce/MAC/id-set
discipline, and returns `{"accepted", "outcome", "reason", "tests", "counts",
"exit_code", "executed", "expected_ids", "output"}`. `accepted` means *the report is
authentic and its ids match*; the caller must still require `outcome == "PASS"`.
`output` exists for the size cap only. The same call is what `verify_package` uses
internally, so there is one implementation of the discipline, not two.
`python experiments/v1.2/h4-micro-low-ablation/pilot/test_runner.py --help` documents the
fd protocol and this call.

### Evidence (A3)

- `python experiments/v1.2/tests/test_v1_2_h4_pilot_taskpack.py` → `Ran 106 tests` `OK`
  (the 83 from A2 plus 23 new: N21/N22/N23, the fd forgery, the MAC and id-set mutation
  anchors, the patch-exercise cases, the runner API, the TMPDIR alias and Darwin default).
- Mutation audit (7 mutations, one defence removed at a time): all 7 killed,
  `ALIVE: none`, and the file was restored to the same sha256 afterwards. Anchors:
  `_verify_report_mac` → `return True`; `if missing or extra:` → `if False:`;
  `exercised = _patch_exercise_reason(...)` → `None`; the two `realpath` calls in
  `_sandbox_profile` removed; `if not _imports_src(...)` → `if False:`;
  `_interesting_patch_line` → `return True`; `HIDDEN_REPEATS = 1`.
- The round-2 corpus itself (copied to a scratch dir with `src/` linked read-only to this
  tree) now: `N21` exact → FAIL (`HIDDEN_TEST_DOES_NOT_IMPORT_TARGET`, and
  `PATCH_NOT_EXERCISED` for the importing variant); `N22` exact → FAIL
  (`VISIBLE_TESTS_RESULT_REJECTED TEST_RESULT_UNAVAILABLE`); `N23` exact → FAIL
  (`HIDDEN_TEST_RESULT_REJECTED TEST_RESULT_UNAVAILABLE`); `E4` → FAIL at structure
  (`TEST_COMMAND_NOT_CANONICAL`, no process started); `GOOD` → PASS.
- `python -m ruff check .`, `python scripts/validate_governance.py` (35/35),
  `python scripts/validate_public_release.py` (`VIOLATIONS=0`) — exact output in the
  final report of this commit.

### Limits introduced or still open in A3

- **In-process attacker.** The runner imports the tests into its own process; the nonce
  is deleted after the report is written and the runner exits with `os._exit`, but code
  that walks frames (`sys._getframe`) while the tests run could reach the key. That is
  out of the stated threat model, not a claim of impossibility.
- **`def`/`class` lines are not counted as "the patch ran".** That is what kills the
  dead-code shape, but it also means a legitimate patch whose only added line is a bare
  declaration (with no executable body line) is refused. In practice a real fix adds at
  least one assignment, call, return or import.
- **Test ids are `Class.method`.** Two classes with the same name in different files
  collide, and a test case imported from another module (`from helpers import Base`
  where `Base` has `test_*` methods) is collected at runtime but absent from the static
  map, so such a package is refused. Both are documented rather than guessed around;
  synthetic packages define their cases locally.
- **Discovery mirrors `test*.py` by file name.** `unittest discover` additionally
  requires packages in subdirectories; a `tests/sub/test_x.py` without `__init__.py`
  would be counted by the AST scan and not by discovery, i.e. refused rather than
  silently ignored.
- The **`watch` map is per run**. If the hidden test never calls the changed function
  (for example it only reads the source), the fix is refused — by design (N21), but it
  also means a reference patch that fixes code the hidden test does not touch is
  rejected. That is the "hidden test must exercise the target" rule from P2-3.

## Fix round A2 (`65097be`) — carried forward

`pilot/taskpack.py`

- **P1-1 `test_command`**: only `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]`
  is accepted (`TEST_COMMAND_NOT_CANONICAL`). The check lives in check 1, before any
  process is started, so a `-c` payload that prints fake unittest output never runs.
  (A3 adds that this argv is display-only: the runner replaces its execution.)
- **P1-2/P1-3 phase and path awareness**: every phase runs at one fixed path,
  `<work>/phase/repo`, and the phase directory is deleted and recreated between phases.
- **P1-3 confinement**: commands run under `sandbox-exec` with a generated profile that
  denies `network*`, denies every write outside the phase directory (plus `/dev/null` and
  friends), and denies `file-read*` of the real home directory and of `/Users`. The
  reference patch is handed to `git apply` on stdin.
- **P1-3 unsandboxed fallback**: `sandbox_available()` probes `sandbox-exec` for real.
  When it is unavailable the package is still verified, `isolation` is `NONE`, and the
  overall verdict is `UNSANDBOXED` — never `PASS` — unless `allow_unsandboxed=True`.
  A3 adds `sandbox_probe_reason()`, which quotes the probe's own output; the tests that
  need confinement skip with that reason (a nested `sandbox-exec` lands here) and never
  pass without it.
- **P1-4 determinism**: `PYTHONHASHSEED=0`, `LC_ALL=C`, `PYTHONDONTWRITEBYTECODE=1`; the
  hidden test runs `HIDDEN_REPEATS` times per phase (3 at A2, 5 at A3) and the outcomes
  must agree, otherwise `NONDETERMINISTIC`.
- **P2-3**: `RUN_TIMEOUT = 30`; the first timeout (or output overflow) aborts the
  remaining phases.
- **P3**: unknown `package.json` / `gate` keys refused; `.git`, `__pycache__` and
  `*.pyc`/`*.pyo` refused; mode changes, copies/renames and binary hunks in
  `reference.patch` refused; the statement screen gained `oracle`, `grader`, `evaluat*`,
  `experiment*`, `treatment*`; the 8-word leak check also runs over case-folded word
  tokens; captured output capped at 1 MiB (`OUTPUT_OVERFLOW`); a package that already
  carries `SEAL.json` is refused by a plain `verify_package`
  (`SEAL_PRESENT_BEFORE_SEALING`) and only `seal_package` / `allow_reseal=True` may accept
  one; every verdict carries `sealed` and `isolation`; the CLI exits non-zero for
  anything that is not `PASS`.
- **E14**: two detectors close the single-assertion leak — the 8-word window and a
  24-character fragment window (`LEAK_CHAR_RUN`, `STATEMENT_LEAKS_HIDDEN_FRAGMENT`).

`pilot/maker_prompt.md` — the `test_command` value is the only accepted argv; the
eight-word leak window ignores case and punctuation; `.git`, `*.pyc` and `__pycache__`
anywhere are refused; the patch rules name copies and file deletions; and the base
section says confinement is enforced rather than requested.

`experiments/v1.2/tests/test_v1_2_h4_pilot_taskpack.py` — the 35 original tests stay,
plus 48 at A2 (83 total), plus 23 at A3 (106).

### Behaviour changes that touched existing tests (stated plainly)

- At A2, `GoodPackageTests.test_good_package_is_accepted_then_sealed` now passes
  `allow_reseal=True` for the re-verification step, exactly as E22/E23 require; new
  tests assert the refusal without it. Nothing deleted or loosened.
- At A3, `test_hidden_test_is_run_three_times_in_each_phase` became
  `test_hidden_test_is_run_five_times_in_each_phase` (expects five runs and asserts
  `HIDDEN_REPEATS >= 5`), and `test_hidden_test_whose_runs_disagree_is_rejected` expects
  five recorded runs. Both changes follow P2-2; neither weakens an assertion.

### Limits (A2, still true)

- **The fragment window is a threshold, not a proof.** A leak shorter than 24 identical
  alphanumeric characters (for example a bare `x + 1`) is not caught, and a statement
  that legitimately shares a 24-character run with the hidden test would be refused.
- **The sandbox is confinement, not a security boundary.** `sandbox-exec` confines the
  workspace, not a kernel-level attacker; Apple has deprecated it. If it disappears, the
  verdict becomes `UNSANDBOXED` and no seal can be written.
- **Read denials cover the real home and `/Users` only.** Other absolute paths (for
  example another mount under `/Volumes`) are not denied; writes are still limited to the
  phase directory.
- **`git` is required** for the patch phase, and it must be able to stat the parent of
  the phase directory, which is why the work directory itself is not on the read-deny
  list.
- **The 1 MiB cap is per process**, not per verification: several phases may each produce
  up to the cap before the first overflow aborts the run.
