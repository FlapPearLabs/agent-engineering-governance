# Build notes — taskpack fix round (ticket A2)

Fix ticket on my own earlier work (`438755a`), driven by the independent acceptance
report `ACCEPT.md` (verdict REJECT: 4 P1, 3 P2, plus P3). Everything below is either done
and tested, or stated as a limit. Nothing here is an acceptance verdict: the same
implementer does not sign off on its own work.

## What changed

`pilot/taskpack.py`

- **P1-1 `test_command`**: only `["python", "-m", "unittest", "discover", "-s", "tests", "-t", "."]`
  is accepted (`TEST_COMMAND_NOT_CANONICAL`). The check lives in check 1, before any
  process is started, so a `-c` payload that prints fake unittest output never runs.
- **P1-2/P1-3 phase and path awareness**: every phase (base, base+hidden, patched+hidden,
  patched) runs at one fixed path, `<work>/phase/repo`, and the phase directory is deleted
  and recreated between phases. Package code therefore sees an identical `cwd` in both
  phases and cannot find a file left by an earlier phase.
- **P1-3 confinement**: commands run under `sandbox-exec` with a generated profile that
  denies `network*`, denies every write outside the phase directory (plus `/dev/null` and
  friends), and denies `file-read*` of the real home directory and of `/Users`. The
  reference patch is handed to `git apply` on stdin, so the patch never has to be
  readable from inside the phase.
- **P1-3 unsandboxed fallback**: `sandbox_available()` probes `sandbox-exec` for real
  (a profile is applied to a Python child; the probe is not just `which`). When it is
  unavailable the package is still verified, `isolation` is `NONE`, and the overall
  verdict is `UNSANDBOXED` — never `PASS` — unless the caller passes
  `allow_unsandboxed=True`.
- **P1-4 determinism**: the hidden test runs three times at base and three times after
  the patch; the outcomes must agree inside each phase, otherwise
  `NONDETERMINISTIC`. `PYTHONHASHSEED=0`, `LC_ALL=C`, `PYTHONDONTWRITEBYTECODE=1`.
- **P2-3**: `RUN_TIMEOUT = 30`; the first timeout (or output overflow) aborts the
  remaining phases, so a hanging hidden test is paid for once, not twice.
- **P3**: unknown `package.json` / `gate` keys are refused; `.git`, `__pycache__` and
  `*.pyc`/`*.pyo` anywhere in the package are refused; `reference.patch` with a mode
  change, a copy/rename or a binary hunk is refused (creating one new non-test file stays
  legal); the statement screen gained `oracle`, `grader`, `evaluat*`, `experiment*`,
  `treatment*`; the 8-word leak check now also runs over case-folded word tokens, so
  punctuation and capitals cannot hide a copy; captured output is capped at 1 MiB per
  process (`OUTPUT_OVERFLOW` = reject); a package that already carries `SEAL.json` is
  refused by a plain `verify_package` (`SEAL_PRESENT_BEFORE_SEALING`) and only
  `seal_package` / `allow_reseal=True` may accept one; every verdict now carries
  `sealed: true|false` and `isolation: SANDBOX_EXEC|NONE`, and the CLI `verify` exits
  non-zero for anything that is not `PASS`.
- **E14, exactly**: eight words cannot catch one leaked `self.assertEqual(...)` line,
  because that line holds seven words however it is punctuated. Two detectors close the
  case: the word window (catches multi-line punctuation-stripped copies) and a
  fragment window of 24 identical alphanumeric characters with every space and mark
  removed (`LEAK_CHAR_RUN`, `STATEMENT_LEAKS_HIDDEN_FRAGMENT`). The acceptance corpus'
  own E14 payload — `self.assertEqual(limit(1000 -5 7) 7)` against the hidden test's
  `self.assertEqual(limit(1000, -5, 7), 7)` — is now refused. They are separate
  detectors on purpose: the word window is the contract's rule, the fragment window is
  what makes rule and attack meet.

`pilot/maker_prompt.md` — rules that changed: the `test_command` value is the only
accepted argv; the eight-word leak window ignores case and punctuation; `.git`, `*.pyc`
and `__pycache__` anywhere are refused; the patch rules now also name copies and file
deletions; and the base section says that confinement (no socket, no writes outside the
directory, no home reads) is enforced rather than merely requested.

`experiments/v1.2/tests/test_v1_2_h4_pilot_taskpack.py` — the 35 existing tests stay,
plus 48 new ones (83 total), including one regression per attack row that `ACCEPT.md` §3
marked 错 or 松: E1, E4, E8, E9, E11, E12b, E13b, E14 (both the multi-line and the single
assertion form), E16/E25, E18, E19, E20, E21, E22, E23, E26b, and the `/tmp` write from
`attack_pkg.py`.

## Behaviour change that touched an existing test (stated plainly)

`GoodPackageTests.test_good_package_is_accepted_then_sealed` used to call
`verify_package(sealed_pkg)` and expect `PASS`. Under the new seal rule a package that
already carries a seal is refused unless the caller says `allow_reseal=True`, which is
exactly what E22/E23 require; the call site now passes that flag, and new tests assert
the refusal without it. Nothing was deleted or loosened: the same test now also checks
`sealed`, `isolation` and the check-7 status.

## Evidence

- `python experiments/v1.2/tests/test_v1_2_h4_pilot_taskpack.py` → `Ran 83 tests` `OK`.
- Mutation audit (18 mutations, each removing one fix): all 18 killed, `ALIVE: none`.
  Worst case anchors: `if command != CANONICAL_TEST_COMMAND:` → `if False:`,
  `word_shared = ...` → `word_shared = set()`, `fragment = _shared_char_run(...)` →
  `fragment = None`, `if size > OUTPUT_CAP:` → `if False:`,
  `if not allow_reseal:` → `if False:`, `if run.timed_out:` → `if False:`, the phase
  `shutil.rmtree` → no-op, `range(HIDDEN_REPEATS)` → `range(1)`, and the two check-2
  reason branches. Raw output lives outside the repo (scratch dir, not committed).
- The acceptance corpus itself (`h4-accept-a/work/attacks/`, copied to a scratch dir with
  only `taskpack.py` linked to this tree) re-run against the fixed verifier: every row of
  `ACCEPT.md` §3 marked 错 or 松 is now refused — E1, E4, E8, E9, E11, E12b, E13b,
  E14, E16, E18, E19, E21, E22, E23, E25, E26b, `writes_abs_tmp` — while `GOOD` and
  `E31` (two-file patch) are still accepted. Two rows deserve the plain statement:
  - `E20` (base test opens a socket) is still **accepted**, by design: the socket is
    refused by the sandbox, the test swallows the permission error, and nothing leaks.
    Containment replaced detection. `ConfinementTests.test_network_is_denied_to_package_code`
    proves the denial (it passes only when the connection raises `PermissionError`).
    A reviewer who wants the package *rejected* for even trying needs a static rule the
    contract does not currently state.
  - `attack_pkg.py::writes_outside_home` (`open(os.path.expanduser("~/marker"))`) is
    also accepted, and again that is right: `HOME` points into the phase directory, so the
    write lands inside the sandbox and no real home is touched (`markers: False ...`).
- `python -m ruff check .`, `python scripts/validate_governance.py`,
  `python scripts/validate_public_release.py` — see the final report for the exact
  command output of this commit.

## Limits (not fixed, stated)

- **The fragment window is a threshold, not a proof.** `LEAK_CHAR_RUN = 24` identical
  alphanumeric characters is what separates a copied code fragment from ordinary prose;
  a leak shorter than that (for example a bare `x + 1`) is not caught, and a statement
  that legitimately shares a 24-character run with the hidden test would be refused.
  Raising the constant lowers the false-negative risk and raises the false-positive one.
- **Three agreeing runs make a random hidden test very unlikely to pass, not impossible.**
  A hidden test that fails with probability p at base and passes with probability q
  after the patch is accepted with probability about `(1-p)^3 * q^3`; the regression test
  uses eight independent coin flips, i.e. roughly `10^-8`. It is a real reduction, not a
  proof of determinism.
- **The sandbox is confinement, not a security boundary.** `sandbox-exec` confines the
  workspace, not a kernel-level attacker; Apple has also deprecated it. If it disappears,
  the verdict becomes `UNSANDBOXED` and no seal can be written, which is the honest
  outcome but means the pilot cannot run on such a host without an explicit
  `allow_unsandboxed=True` (a flag the harness never passes).
- **Read denials cover the real home and `/Users` only.** Other absolute paths (for
  example another mount under `/Volumes`) are not denied; writes are still limited to
  the phase directory, so nothing can be persisted there.
- **`git` is required** for the patch phase (as before), and it must be able to stat the
  parent of the phase directory, which is why the work directory itself is not on the
  read-deny list.
- **The 1 MiB cap is per process**, not per verification: four phases may each produce up
  to the cap before the first overflow aborts the run.
