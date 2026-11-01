# H4 exploratory pilot harness — build spec

STATUS = EXPLORATORY. Owner approved building this harness and, separately later, a capped
exploratory run (owner message 2026-11-01). It does **not** change N4 (`PROTOCOL_NOT_STARTABLE`),
does not freeze the H4 protocol, and nothing it produces is formal evidence or counts toward
the 4 real tasks. Tasks are synthetic, made by a model, and labelled `SYNTHETIC_EXPLORATORY`.
Purpose: exercise the 3-arm flow end to end, learn cost and variance, find leaks, size a later formal run.

## Roles and isolation (the point of the pilot)
- MAKER: one model session in its own git worktree; writes one task package; never sees the worker, arms or results.
- WORKER: one model session per (task, arm); sees only a history-free standalone repo plus `statement.md`.
  Runs inside the freeze-v3 sandbox pattern with an isolated home/profile, so `~/.agents/AGENTS.md`,
  `~/.config/opencode/AGENTS.md` and every other global rule file are NOT visible.
- ACCEPTOR: model-free code; applies the hidden test after the worker finishes.
- QUARANTINE: a directory outside the repo and outside the worker sandbox's readable roots holding
  hidden test, reference patch, SEAL and results. The worker can never read it.
- Maker, worker and reviewer are different sessions with different working directories. No shared context.

## Task package format (`<pkg>/`)
- `package.json`: `task_id`, `title`, `label` = `SYNTHETIC_EXPLORATORY`, `risk` = `LOW`, `language` = `python`,
  `statement` = `statement.md`, `hidden_test` = `hidden/test_hidden.py`, `hidden_test_dest` = `tests/test_hidden.py`,
  `reference_patch` = `reference.patch`, `test_command` (argv list, unittest), `gate` = `{kind: ruff, config: ruff.toml}`.
- `base/`: a small deterministic Python project (stdlib only, no network, no clock/random) with `ruff.toml`
  (`select = ["E9", "F"]`), `src/`, and visible `tests/` that pass at base.
- `statement.md`: the task as a ticket; must not quote or paraphrase the hidden test.
- `hidden/test_hidden.py`, `reference.patch` (touches 1-2 non-test files, <= 60 changed lines).

## Package verifier (`taskpack.py`, model-free) — reject unless ALL hold
1. Required files present; no extra files; no symlinks; paths stay inside the package.
2. `base/` visible tests pass; `ruff check` clean at base.
3. Hidden test copied to a randomised `tests/test_<hex>.py` (same directory as `hidden_test_dest`) at base: clean unittest FAILURE (`failures>0`, `errors=0`, not skipped, collects >=1 test, no ImportError). The random name is used in BOTH phases of one verification, so the phase path stays identical; it exists so a package cannot key a forgery on the canonical `test_hidden.py` name.
4. After `reference.patch`: hidden test passes, visible tests still pass, ruff clean, and the patch passes the STRUCTURAL RULE: every added/changed line must lie inside the body of a function or method that already exists in `base/`; a new top-level def/class/name is `PATCH_ADDS_NEW_API` unless `statement.md` names it as the requested API (backticked or written as a call), and a module-level line outside any function is `PATCH_OUTSIDE_EXISTING_FUNCTION`. The hidden test must also CALL a function the patch actually changed (`HIDDEN_TEST_NEVER_CALLS_TARGET`); a changed line that only runs while the module is imported does not count.
5. `statement.md` contains no >= 8-token substring of the hidden test (leak check) and no mention of arms, governance, FULL/MIN/INJECT.
6. Risk LOW by rule: reference patch <= 60 lines, 1-2 non-test files, no security/credential/concurrency/governance content (simple keyword screen is acceptable, documented as heuristic).
7. Seal: write `SEAL.json` with sha256 of every file; later steps re-verify the seal and refuse on mismatch.
Maker prompt template in `maker_prompt.md`: the maker writes only inside its own cwd `pkg/`, and is told nothing about arms, workers or results.

## Arms and carriers (`arms.py`)
- FULL: deterministic extraction of the canonical `AGENTS.md` sections 2-4 from a pinned materials commit (`git show <sha>:AGENTS.md`),
  with a manifest of rule-ID -> byte range and source hash (see `ARMS.md`, 11 rule IDs R-V12-036..046).
- MIN: an explicit A-layer-only text (`pilot/a_layer_min.md`, flagged ASSUMED) plus the identical gate commands and task contract; must contain none of the 11 process instructions.
- INJECT: same carrier as MIN. After the worker finishes, on a disposable copy of the candidate: hollow `ruff.toml` `select` and place the F841 control at `scripts/n7_control.py` per `experiments/v1.2/gate-load-bearing/gates.json`; the catching gate is `probe_gates.py --worktree` and must reject.
- Delivery: outside the repo, in the worker's isolated home, via the existing `freeze-v3/wrapper_delivery.py::prepare` pattern; read back and compare hashes; reject missing/substituted/hash-mismatch.

## Threat model and the tamper scan (F1)
- The pilot defends against **accidental or lazy shortcuts by a model**, not a determined attacker.
  Test execution is split into two processes (round C1): package code runs in a CHILD that only
  emits raw per-test events on an inherited pipe; the PARENT never imports package code, computes
  the counts and pass/fail, validates the test-id set, and signs the report with the nonce. The
  child never receives the nonce or the result fd, and an ordinary `import __main__` reaches the
  child's `__main__`, which has no module-level result class or integrity snapshot to replace.
  The hidden test also runs under a randomised file name, and a must-fail canary runs in a second
  fresh child with the candidate's real `src/`, so a forgery keyed on `test_hidden.py` flips to a
  real FAIL. A package with arbitrary code execution in the child can still forge its own per-test
  events (walk `gc`, monkeypatch the child's own machinery); that remains a **stated limitation**
  and is what the tamper scan is for.
- What the pilot does add is a cheap, honest detection: `tamper_scan.py` (stdlib `ast`) scans every
  Python file the worker **changed or added** relative to the sealed base (including added tests and
  any `__init__.py`, `conftest.py`, `sitecustomize.py`, `usercustomize.py`, `*.pth`) and flags:
  imports of `gc`, `inspect`, `ctypes`, `hmac`, `builtins`, `atexit`, `signal`, `multiprocessing`,
  `threading`, `__main__`, `importlib.reload`; calls or references to `os._exit`, `sys._getframe`,
  `sys.settrace`, `sys.setprofile`, `sys.monitoring`, `sys.modules['__main__']`,
  `sys.modules.get("__main__")`, `__main__.anything`, `__import__`; `exec(...)`/`eval(...)`/
  `importlib.import_module(...)` whose string literal names `gc`, `__main__` or `sys`; attribute
  assignment to `unittest` or a name imported from it, and to an attribute of `__main__`, `sys`,
  `gc` or `builtins`; `from importlib import *` / `from sys import *` / `from __main__ import *`;
  `setattr`/`unittest.mock.patch` aimed at `unittest`; reading `test_runner.py`, `taskpack.py`,
  `reference.patch` or `hidden/`.
- **Known limits (source-read guard).** The guard in the test child wraps `open`, `io.open`,
  `io.FileIO`, `io.open_code`, `pathlib`, `os.open`, `linecache`, `inspect.getsource*`, the
  importlib loader `get_source`/`get_data`, `os.popen` and `subprocess.Popen`. It cannot cheaply
  see a raw `os.read` on a descriptor opened before the guard, `mmap`, `ctypes`, or a helper binary
  that reads the file without a path argument. Those routes are covered by the structural patch
  rule (the primary defence), not by the guard; a determined in-process attacker remains outside
  the stated threat model.
- **Known limits (dynamic construction).** A literal `exec("import gc")`,
  `eval("__import__('gc')")` and `importlib.import_module("gc")` are flagged. A string assembled at
  runtime (`__import__("g" + "c")`, `getattr(__import__("builtins"), "op" + "en")`) is caught only
  where the existing `__import__` rule sees it; arbitrary runtime construction is not statically
  decidable and is a stated limit.
- On any hit `pilot_accept` sets the verdict to `INVALID` with reason `SUSPECT_TAMPERING` and the hit
  list `(file, line, rule)` in the record. The gates still run so the hidden test's own result is
  recorded, but a hidden-test gate is never allowed to read `PASS` on such a run.
- False-positive control: ordinary code (`os.path`, `json`, `re`, `dataclasses`, `functools`,
  `typing`, `collections`, `itertools`) produces no hit, and unchanged sealed-base code is not
  scanned at all.

## Driver and acceptance (`pilot_driver.py`, `pilot_accept.py`)
- Driver launches a worker per (task, arm) through the existing freeze-v3 sandbox/egress/isolated-profile mechanism (import, do not copy or edit frozen files).
- A real launch REQUIRES `H4_PILOT_RUN_AUTH` pointing at an authorization file with a numeric `budget_cap` and `max_runs`; without it the driver exits non-zero before any process starts. Tests use `--fake-worker` (deterministic stub, no opencode). `budget_cap` has a documented ceiling and is recorded, never enforced; `max_runs` is enforced and has its own ceiling (`MAX_RUNS = 100`).
- The invocation itself is refused cleanly (exit 2, no traceback, no process started) for a duplicated arm in `--arms`, for a results directory that is an existing regular file / has a file as a parent / is unwritable (`REFUSED:RESULTS_DIR_NOT_A_DIRECTORY` / `REFUSED:RESULTS_DIR_NOT_WRITABLE`), and for a carrier delivery target that is a regular file.
- A results directory under the invoking user's home is refused only when it is temp-like or hidden (a `.`-prefixed component, or `tmp`/`temp`/`Temporary Items`/`var`/`folders`/`cache`/`caches`); normal durable shared locations stay allowed.
- After the verdict the driver signals the worker's process group (SIGTERM then SIGKILL) and deletes the acceptance directory, so a background child the worker planted has nothing left to write into.
- Per run record (JSON, written to a caller-given durable results dir, never /tmp): task_id, arm, model, base sha, seal sha, carrier hashes, worker exit status, hidden-test verdict, ruff verdict, INJECT verdict, durations, token/cost if reported, and `UNKNOWN` (never 0) for anything not observed.
- Acceptance order: visible tests, ruff, then hidden test, then (INJECT only) the N7 probe. A missing control or failed injection is `INVALID`, not green.

## Required tests (`experiments/v1.2/tests/`, stdlib unittest, no model/network)
Verifier rejects: hidden test erroring at base; hidden test already passing at base; reference that breaks visible tests; ruff-dirty reference; statement leaking the hidden test; extra/symlink files; tampered SEAL; a reference that only adds an unrelated top-level API (`PATCH_ADDS_NEW_API`) or a module-level line (`PATCH_OUTSIDE_EXISTING_FUNCTION`); a patch whose changed function the hidden test never calls (`HIDDEN_TEST_NEVER_CALLS_TARGET`, isolated by a fixture whose changed line runs only at import); and every ordinary source reader (`io.FileIO`, `io.open_code`, `linecache`, `inspect.getsource*`, loader `get_source`/`get_data`, `os.popen`, `subprocess`). Carriers: FULL != MIN; MIN lacks all 11 rule IDs; wrong/missing/substituted carrier rejected. Driver: refuses without `H4_PILOT_RUN_AUTH`; fake worker end to end through all three arms; INJECT with a missed control -> INVALID. Tamper scan: the gc-forge worker from the acceptance report ends `INVALID`/`SUSPECT_TAMPERING` on both the acceptance path and the driver record path, while ordinary code is not flagged and unchanged base code is not scanned. Driver refusals: results directory that is a file / has a file parent / is unwritable; duplicate arms; delivery onto a regular file; `max_runs` above its ceiling; the `ACCEPTANCE_TREE_EXISTS` and `DRIVER_ROOT_INSIDE_LAUNCH` branches fail when removed. Cleanup: the worker process group is signalled and the acceptance directory is gone after the verdict. Isolation: worker sandbox profile denies reads of quarantine and of global rule files (use the freeze-v3 self-test pattern; skip with an explicit SKIP reason if `sandbox-exec` is unavailable, never a pass).

## Hard rules
No opencode/codex/agy/model run, no network, no `run_h2r2.py`, no runs root. Do not edit anything under `freeze-v3/` or other frozen paths. Write only under `experiments/v1.2/h4-micro-low-ablation/pilot/` and new `experiments/v1.2/tests/test_v1_2_h4_pilot_*.py`. No home-directory paths or secrets in committed files. Gates before commit: ruff, `scripts/validate_governance.py`, `scripts/validate_public_release.py`, the new tests. Commit locally only.
