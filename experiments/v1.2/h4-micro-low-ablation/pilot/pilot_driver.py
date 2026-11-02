#!/usr/bin/env python3
"""H4 exploratory pilot driver — one worker per (task, arm), durable per-run records.

Contract: `PILOT_SPEC.md` §"Driver and acceptance", §"Roles and isolation"; design draft:
`../HARNESS_PLAN.md` T70–T74. EXPLORATORY only: no result here is formal evidence.

Two launch paths, deliberately separated:

  * `--fake-worker` — a deterministic stub that applies the package's `reference.patch`. No model,
    no network, no sandbox; this is the path every test uses, and it is labelled
    `NOT_A_MEASUREMENT` in every record it produces.
  * the real launch — `real_launch()` imports the frozen `freeze-v3/sandbox_v2.py` and
    `freeze-v3/wrapper_delivery.py` (never copies or edits them), puts the driver root at the frozen
    `wrapper_delivery.driver_root(run_dir)` (a sibling of the launch, so the plant, the profile and
    the fresh home are outside the tree the worker owns), renders a per-launch profile, runs the
    model-free confinement self-test, and only then starts the worker inside the sandbox with a
    fresh isolated home. **No test executes it.** It also requires authorization:
    `H4_PILOT_RUN_AUTH` must point at an absolute, non-symlink, non-temporary JSON file carrying a
    numeric `budget_cap` (at most `MAX_BUDGET_CAP`) and `max_runs`, and without it the driver exits
    non-zero before any process starts.

Every run writes one record to the caller-given durable results directory (never a temporary
directory for a real run): task, arm, model, base SHA, seal SHA, carrier hashes, worker exit status,
the three acceptance verdicts, the INJECT verdict and durations. Anything not observed is
`UNKNOWN` — never `0`.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import arms
import pilot_accept

PILOT_DIR = Path(__file__).resolve().parent
ROOT = PILOT_DIR.parents[3]
FREEZE_V3 = ROOT / "experiments/v1.2/h2-lazy-disclosure/freeze-v3"

SCHEMA = "h4-pilot-run/1"
AUTH_ENV = "H4_PILOT_RUN_AUTH"
MODEL = "opencode-go/deepseek-v4.1-flash"
MODEL_FAKE = "FAKE_WORKER"
LABEL = arms.LABEL
UNKNOWN = pilot_accept.UNKNOWN
PASS = pilot_accept.PASS
FAIL = pilot_accept.FAIL
INVALID = pilot_accept.INVALID

WALL_CLOCK_SECONDS = 90 * 60
WORKER_REPORT = "worker-report.json"
RECORD_NAME = "record.json"
CANDIDATE_MANIFEST = "candidate-manifest.json"
TEMP_ROOT_PREFIXES = ("/tmp", "/private/tmp", "/var/folders", "/private/var/folders")
REQUIRED_AUTHORIZATION_KEYS = ("budget_cap", "max_runs")
ALLOWED_AUTHORIZATION_KEYS = REQUIRED_AUTHORIZATION_KEYS
# The authorization file may cap the run cost, but no run cost was ever observed, so `budget_cap` is
# only ever *recorded* (MAX_RUNS_ONLY;RUN_COST_UNOBSERVED). An unbounded or absurd cap would make
# that record look like a real spend limit, so a cap above this ceiling is refused at read time.
MAX_BUDGET_CAP = 100.0
# `max_runs` is the one limit that is actually enforced (`plan_size_reason`), so it gets a documented
# ceiling of its own: an authorization that asks for a billion runs is not a control either.
MAX_RUNS = 100
# A results directory under the invoking user's home is refused only when it is a temp-like or hidden
# location; normal durable shared locations outside the home (a `/Volumes/...` path) stay allowed.
HOME_TEMP_COMPONENTS = ("tmp", "temp", "temporary items", "var", "folders", "cache", "caches")
SANDBOX_PROBE_ARGV = ("-p", "(version 1)(allow default)", "/usr/bin/true")

GIT_IDENTITY = {"GIT_AUTHOR_NAME": "H4 Pilot", "GIT_AUTHOR_EMAIL": "h4@pilot.invalid",
                "GIT_COMMITTER_NAME": "H4 Pilot", "GIT_COMMITTER_EMAIL": "h4@pilot.invalid",
                "GIT_AUTHOR_DATE": "2000-01-01T00:00:00 +0000",
                "GIT_COMMITTER_DATE": "2000-01-01T00:00:00 +0000"}

FAKE_PROMPT_NOTE = "fake worker: applies the package reference patch, no model is started"


class AuthorizationError(RuntimeError):
    """No valid run authorization: the driver must exit before any process starts."""


class DriverRefusal(RuntimeError):
    """The invocation itself is refused (seal, results directory, run id, plan size)."""


# ---------------------------------------------------------------------------
# Authorization and durable results directory
# ---------------------------------------------------------------------------

def _is_number(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return value == value and value not in (float("inf"), float("-inf"))     # NaN / inf refused


def _is_file_symlink(path: Path) -> bool:
    """True when the given path is itself a symlink (whatever it points at).

    Ancestor directories are not checked: on macOS `/var` and `/tmp` are symlinks themselves, so a
    component walk would refuse ordinary absolute paths for no reason. The file-level symlink is
    what the gate is about — it can be re-pointed between the check and the read.
    """
    return Path(path).is_symlink()


def _under_temp_root(path: Path) -> bool:
    """Whether `path` resolves inside a temporary root (where anyone could have written it)."""
    resolved = Path(path).resolve()
    prefixes = {prefix.rstrip(os.sep) or os.sep for prefix in TEMP_ROOT_PREFIXES}
    prefixes.add(os.path.realpath(tempfile.gettempdir()).rstrip(os.sep) or os.sep)
    text = str(resolved)
    return any(text == prefix or text.startswith(prefix + os.sep) for prefix in prefixes)


def is_temporary_path(path) -> bool:
    """Public form of the durability predicate, so callers and tests use one definition."""
    return _under_temp_root(Path(path))


def read_authorization(environ=None) -> dict:
    """`H4_PILOT_RUN_AUTH` -> a file with numeric `budget_cap` and `max_runs`. Fail closed.

    The file must be an absolute path to a regular, non-symlink file outside every temporary root:
    a relative path is resolved against the caller's cwd, a symlink can be re-pointed between the
    check and the read, and a world-writable temporary directory is not an authorization store.
    """
    environ = os.environ if environ is None else environ
    value = environ.get(AUTH_ENV)
    if not value:
        raise AuthorizationError(f"{AUTH_ENV}_NOT_SET")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise AuthorizationError("AUTHORIZATION_FILE_NOT_ABSOLUTE")
    if _is_file_symlink(path):
        raise AuthorizationError("AUTHORIZATION_FILE_SYMLINK")
    if not path.is_file():
        raise AuthorizationError("AUTHORIZATION_FILE_MISSING")
    if _under_temp_root(path):
        raise AuthorizationError("AUTHORIZATION_FILE_UNDER_TEMP")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AuthorizationError("AUTHORIZATION_FILE_UNREADABLE") from exc
    if not isinstance(data, dict):
        raise AuthorizationError("AUTHORIZATION_FILE_NOT_AN_OBJECT")
    unknown = sorted(set(data) - set(ALLOWED_AUTHORIZATION_KEYS))
    if unknown:
        raise AuthorizationError("AUTHORIZATION_UNKNOWN_KEYS:" + ",".join(unknown))
    for key in REQUIRED_AUTHORIZATION_KEYS:
        if key not in data:
            raise AuthorizationError(f"AUTHORIZATION_{key.upper()}_MISSING")
        if not _is_number(data[key]) or data[key] <= 0:
            raise AuthorizationError(f"AUTHORIZATION_{key.upper()}_NOT_POSITIVE_NUMERIC")
    if float(data["max_runs"]) != int(data["max_runs"]):
        raise AuthorizationError("AUTHORIZATION_MAX_RUNS_NOT_INTEGER")
    if data["max_runs"] > MAX_RUNS:
        raise AuthorizationError(f"AUTHORIZATION_MAX_RUNS_ABOVE_MAX:{MAX_RUNS}")
    if data["budget_cap"] > MAX_BUDGET_CAP:
        raise AuthorizationError(
            f"AUTHORIZATION_BUDGET_CAP_ABOVE_MAX:{MAX_BUDGET_CAP}")
    return {"path": str(path), "budget_cap": data["budget_cap"], "max_runs": int(data["max_runs"])}


def results_dir_reason(path) -> str | None:
    """Why `path` is not an acceptable durable results directory, or None when it is."""
    resolved = Path(path).resolve()
    root = ROOT.resolve()
    if resolved == root or root in resolved.parents:
        return "RESULTS_DIR_INSIDE_REPOSITORY"
    text = str(resolved)
    for prefix in TEMP_ROOT_PREFIXES:
        if text == prefix or text.startswith(prefix + os.sep):
            return "RESULTS_DIR_UNDER_TEMP"
    home = Path.home().resolve()
    if resolved == home or home in resolved.parents:
        relative = resolved.relative_to(home)
        if any(part.startswith(".") or part.casefold() in HOME_TEMP_COMPONENTS
               for part in relative.parts):
            return "RESULTS_DIR_UNDER_HOME_TEMP"
    return None


def results_dir_problem(path) -> str | None:
    """Why `path` cannot be used as a results directory at all (F2), or None when it can.

    Checked before `mkdir`, so a bad path is a clean `REFUSED:…` with exit 2 instead of a traceback:
    an existing regular file (or a file where a parent directory should be) is not a directory, and
    a directory the caller cannot write to is not a results store.
    """
    path = Path(path)
    if path.exists() and not path.is_dir():
        return "RESULTS_DIR_NOT_A_DIRECTORY"
    ancestor = path
    while not ancestor.exists():
        if ancestor.parent == ancestor:
            break
        ancestor = ancestor.parent
    if ancestor.exists() and not ancestor.is_dir():
        return "RESULTS_DIR_NOT_A_DIRECTORY"
    target = path if path.is_dir() else ancestor
    if target.is_dir():
        probe = target / f".h4-write-probe-{os.getpid()}"
        try:
            probe.write_text("probe\n", encoding="utf-8")
        except OSError:
            return "RESULTS_DIR_NOT_WRITABLE"
        finally:
            try:
                probe.unlink()
            except OSError:
                pass
    return None


def results_durability(path, fake_worker: bool) -> str:
    reason = results_dir_reason(path)
    if reason is None:
        return "DURABLE"
    if fake_worker and reason == "RESULTS_DIR_UNDER_TEMP":
        return "EPHEMERAL_TEST_PATH"
    raise DriverRefusal(reason)


def plan_size_reason(count: int, authorization: dict | None) -> str | None:
    """A plan may never schedule more runs than the authorization's `max_runs`."""
    if authorization is None:
        return None
    if count > authorization["max_runs"]:
        return f"MAX_RUNS_EXCEEDED:{count}>{authorization['max_runs']}"
    return None


# ---------------------------------------------------------------------------
# Workspace, worker, candidate capture
# ---------------------------------------------------------------------------

def prepare_workspace(pkg, workspace: Path) -> dict:
    """Copy `pkg/base` into a one-commit repository; the base tree is never modified in place."""
    repo = workspace / "repo"
    workspace.mkdir(parents=True, exist_ok=True)
    copied = pilot_accept.copy_tree(pkg["base"], repo)
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env.update(GIT_IDENTITY)
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, env=env)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "h4 pilot base"],
                   check=True, env=env)
    base_sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True, env=env,
                              capture_output=True, text=True).stdout.strip()
    return {"repo": repo, "base_sha": base_sha, "files": len(copied["files"]),
            "digest": copied["digest"]}


def capture_candidate(repo: Path, dest: Path) -> dict:
    """Freeze the worker's tree (tracked and untracked, no `.git`) as the untouched candidate."""
    if dest.exists():
        raise DriverRefusal("CANDIDATE_DIR_EXISTS")
    files = {}
    for path in sorted(Path(repo).rglob("*")):
        rel = path.relative_to(repo).as_posix()
        if rel == ".git" or rel.startswith(".git/"):
            continue
        if path.is_symlink():
            raise DriverRefusal("CANDIDATE_SYMLINK:" + rel)
        target = dest / rel
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        files[rel] = pilot_accept.sha256(path.read_bytes())
    dest.mkdir(parents=True, exist_ok=True)
    manifest = "\n".join(f"{rel} {digest}" for rel, digest in sorted(files.items()))
    (dest.parent / CANDIDATE_MANIFEST).write_text(manifest + "\n", encoding="utf-8")
    return {"digest": pilot_accept.sha256(manifest.encode()), "files": len(files)}


def fake_worker(repo: Path, pkg, run_dir: Path, timeout: int = 120) -> dict:
    """Deterministic stub: apply the package's reference patch. No model, no network."""
    patch_rel = pkg["package"]["reference_patch"]
    patch = pkg["path"] / patch_rel
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    started = time.monotonic()
    result = subprocess.run(["git", "-C", str(repo), "apply", "--whitespace=nowarn", str(patch)],
                            capture_output=True, text=True, env=env, timeout=timeout)
    seconds = round(time.monotonic() - started, 3)
    output = (result.stdout or "") + (result.stderr or "")
    report = {"kind": MODEL_FAKE, "deterministic": True, "reference_patch": patch_rel,
              "status": "COMPLETED" if result.returncode == 0 else "FAILED",
              "output_sha256": pilot_accept.sha256(output.encode("utf-8", "replace"))}
    (run_dir / WORKER_REPORT).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                         encoding="utf-8")
    return {"kind": MODEL_FAKE, "exit_status": result.returncode, "seconds": seconds,
            "report": report, "note": FAKE_PROMPT_NOTE}


def frozen_modules():
    """Import the FROZEN freeze-v3 modules. Import only: nothing here copies or edits them."""
    if str(FREEZE_V3) not in sys.path:
        sys.path.insert(0, str(FREEZE_V3))
    import sandbox_v2
    import wrapper_delivery
    return sandbox_v2, wrapper_delivery


def driver_root_inside_launch(run_dir, driver_dir) -> bool:
    """The pure layout check `real_launch` refuses on (F3): is the driver root inside the launch?

    `run_dir` is the tree the worker owns; the driver root holds the confinement plant, the rendered
    profile and the fresh home. If it is the launch itself or anywhere below it, the worker could read
    or rewrite its own controls, so the launch must be refused. Extracted from `real_launch` so the
    rejection can be tested with a bad layout without starting a worker.
    """
    run_dir, driver_dir = Path(run_dir), Path(driver_dir)
    return driver_dir == run_dir or run_dir in driver_dir.parents


def driver_layout(run_dir) -> dict:
    """The frozen layout for a launch: `<runs_root>/.driver/<run_id>`, OUTSIDE the launch.

    The worker owns the launch directory (it is its project plus its written tree), so the driver
    root that holds the confinement plant, the rendered profile, the fresh home and the driver-held
    streams must be a sibling, not a child. `wrapper_delivery.driver_root` is the frozen definition
    of that location; this function only applies it and reports whether the result is outside.
    """
    _sandbox, delivery = frozen_modules()
    run_dir = Path(run_dir)
    driver_dir = Path(delivery.driver_root(run_dir))
    return {"run_dir": str(run_dir), "driver_dir": str(driver_dir),
            "runs_root": str(Path(delivery.runs_root_of(run_dir))),
            "inside_launch": driver_root_inside_launch(run_dir, driver_dir),
            "directly_under_runs_root": run_dir.parent
            == Path(delivery.runs_root_of(run_dir))}


def sandbox_probe(binary_path=None) -> tuple[bool, str]:
    """Does `sandbox-exec` really apply a profile here? A `which` hit is not a proof (D5).

    `sandbox-exec -p '(version 1)(allow default)' /usr/bin/true` must exit 0. Under an outer sandbox
    (the usual case for a CI wrapper) it exits non-zero with `sandbox_apply: Operation not
    permitted`; that message becomes the skip reason instead of a red isolation test.
    """
    executable = binary_path or shutil.which("sandbox-exec")
    if sys.platform != "darwin" or not executable:
        return False, "sandbox-exec is not installed on this platform"
    try:
        completed = subprocess.run([str(executable), *SANDBOX_PROBE_ARGV],
                                   capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"sandbox-exec could not be run ({type(exc).__name__})"
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "no output").strip()
        last = message.splitlines()[-1] if message else "no output"
        return False, (f"sandbox-exec cannot apply a profile here "
                       f"(rc={completed.returncode}): {last}")
    return True, "sandbox-exec applied a throwaway profile (rc=0)"


def render_profile(stream_dir, run_dir, home) -> dict:
    """The rendered per-launch confinement profile (no worker, no model, import only)."""
    sandbox, _delivery = frozen_modules()
    return sandbox.profile(Path(stream_dir), Path(run_dir), Path(home), sys.executable)


def kill_process_group(pgid, grace: float = 2.0) -> dict:
    """SIGTERM then SIGKILL a whole process group (P3): nothing the worker started keeps running.

    The worker is launched in its own session, so its pid is the group id. A background child it
    leaves behind is in that group and receives the same signal. `gone` is a best-effort observation
    (`killpg(..., 0)`): an unreaped zombie still counts as present, which is why the caller's record
    reports the signals it sent rather than claiming a death it did not verify.
    """
    result = {"attempted": True, "pgid": pgid, "term_sent": False, "kill_sent": False,
              "gone": False}
    if not isinstance(pgid, int) or pgid <= 0:
        return {"attempted": False, "pgid": pgid, "reason": "NO_PGID"}
    try:
        os.killpg(pgid, signal.SIGTERM)
        result["term_sent"] = True
    except ProcessLookupError:
        result["gone"] = True
        return result
    except OSError as exc:
        result["error"] = type(exc).__name__
        return result
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        try:
            os.killpg(pgid, 0)
        except ProcessLookupError:
            result["gone"] = True
            return result
        except OSError:
            break
        time.sleep(0.05)
    try:
        os.killpg(pgid, signal.SIGKILL)
        result["kill_sent"] = True
    except ProcessLookupError:
        result["gone"] = True
    except OSError as exc:
        result["error"] = type(exc).__name__
    return result


def real_launch(run_dir: Path, model: str, timeout: int = WALL_CLOCK_SECONDS) -> dict:
    """REAL LAUNCH — imports the frozen sandbox and delivery modules; no test executes this.

    Order is refuse-first: an unavailable sandbox, a run root below a home or a discoverable
    guidance ancestor, a driver root inside the launch, or a confinement self-test that does not
    deny all of its probes returns BLOCKED and starts no worker.
    """
    sandbox, delivery = frozen_modules()
    run_dir = Path(run_dir)
    if not sandbox.available():
        return {"kind": "real", "exit_status": UNKNOWN, "seconds": UNKNOWN,
                "blocked": "BLOCKED:SANDBOX_UNAVAILABLE"}
    if not sandbox.TOOLS.get("opencode"):
        return {"kind": "real", "exit_status": UNKNOWN, "seconds": UNKNOWN,
                "blocked": "BLOCKED:OPENCODE_UNAVAILABLE"}
    reason = delivery.run_root_reason(run_dir)
    if reason is not None:
        return {"kind": "real", "exit_status": UNKNOWN, "seconds": UNKNOWN,
                "blocked": f"BLOCKED:{reason}"}
    driver_dir = Path(delivery.driver_root(run_dir))
    if driver_root_inside_launch(run_dir, driver_dir):
        return {"kind": "real", "exit_status": UNKNOWN, "seconds": UNKNOWN,
                "blocked": "BLOCKED:DRIVER_ROOT_INSIDE_LAUNCH"}
    home = sandbox.fresh_home(driver_dir, "home-1", run_dir)
    profile = sandbox.profile(driver_dir, run_dir, home, sys.executable)
    planted, token = sandbox.plant(driver_dir)
    verdict = sandbox.self_test(profile["path"], run_dir, planted, sys.executable, token)
    if verdict["verdict"] != "PASS":
        return {"kind": "real", "exit_status": UNKNOWN, "seconds": UNKNOWN,
                "blocked": "BLOCKED:SANDBOX_NOT_CONFINING", "self_test": verdict}
    prompt = ((run_dir / "statement.md").read_text(encoding="utf-8")
              + "\n\nThe project is in `repo/`. Work only there, then stop.\n")
    argv = sandbox.confine(profile["path"],
                           [sandbox.TOOLS["opencode"], "run", "--auto", "--format", "json",
                            "-m", model, prompt])
    env = sandbox.home_env(dict(os.environ), home, run_dir)
    started = time.monotonic()
    # A new session per worker: background children it leaves behind stay in its own process
    # group, so `run_one` can kill the whole group after the verdict (P3).
    process = subprocess.Popen(argv, cwd=str(run_dir), env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        stdout, _stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        kill_process_group(process.pid)
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover - SIGKILL should have landed
            pass
        return {"kind": "real", "exit_status": UNKNOWN,
                "seconds": round(time.monotonic() - started, 3), "blocked": "INVALID:TIMEOUT",
                "profile": profile, "self_test": verdict, "pgid": process.pid}
    seconds = round(time.monotonic() - started, 3)
    output = stdout or ""
    (driver_dir / "worker-stream.txt").write_text(output, encoding="utf-8")
    return {"kind": "real", "exit_status": process.returncode, "seconds": seconds,
            "stream_sha256": pilot_accept.sha256(output.encode("utf-8", "replace")),
            "profile": profile, "self_test": verdict, "pgid": process.pid}


# ---------------------------------------------------------------------------
# One run
# ---------------------------------------------------------------------------

def _record_carrier(carrier: dict, delivery: dict) -> dict:
    return {"arm": carrier["arm"], "label": carrier["label"], "assumed": carrier["assumed"],
            "materials": carrier["materials"], "sha256": carrier["hashes"],
            "rules": len(carrier["rules"]), "excluded_rules": len(carrier["excluded_rules"]),
            "delivered_path": delivery["path"], "readback": delivery["files"],
            "readback_verdict": delivery["verdict"]}


def cleanup_run(run_dir, worker: dict) -> dict:
    """After the verdict: kill the worker's process group and delete the acceptance directory.

    A worker (or code it planted) can leave a background process that writes into the acceptance
    directory after acceptance returns; the acceptance report observed exactly that. The worker
    group is signalled first, then the directory is removed, so a leftover writer has nowhere to
    write and no surviving group to run in.
    """
    pgid = worker.get("pgid")
    group = (kill_process_group(pgid) if isinstance(pgid, int) and not isinstance(pgid, bool)
             else {"attempted": False, "pgid": pgid, "reason": "NO_PGID"})
    acceptance_dir = Path(run_dir) / "acceptance"
    removed = False
    if acceptance_dir.exists():
        shutil.rmtree(acceptance_dir, ignore_errors=True)
        removed = not acceptance_dir.exists()
    return {"worker_group": group, "acceptance_dir_removed": removed}


def run_one(pkg_dir, arm: str, results_dir: Path, *, fake_worker_mode: bool, materials,
            model: str, authorization: dict | None) -> dict:
    started = time.monotonic()
    pkg = pilot_accept.load_package(pkg_dir)                     # seal re-verified, fail closed
    task_id = pkg["package"]["task_id"]
    run_id = f"{task_id}-{str(arm).lower()}"
    run_dir = Path(results_dir) / run_id
    if run_dir.exists():
        raise DriverRefusal("RUN_DIR_EXISTS:" + run_id)
    run_dir.mkdir(parents=True)

    timings = {}
    phase = time.monotonic()
    carrier = arms.build(arm, ROOT, materials)
    delivery = arms.deliver(carrier, run_dir, ROOT)
    timings["carrier_seconds"] = round(time.monotonic() - phase, 3)

    shutil.copyfile(pkg["statement_path"], run_dir / "statement.md")
    phase = time.monotonic()
    workspace = prepare_workspace(pkg, run_dir / "workspace")
    timings["workspace_seconds"] = round(time.monotonic() - phase, 3)

    phase = time.monotonic()
    if fake_worker_mode:
        worker = fake_worker(workspace["repo"], pkg, run_dir)
    else:
        worker = real_launch(run_dir, model)
    timings["worker_seconds"] = round(time.monotonic() - phase, 3)

    phase = time.monotonic()
    candidate = capture_candidate(workspace["repo"], run_dir / "candidate")
    acceptance = pilot_accept.accept(run_dir / "candidate", pkg, run_dir / "acceptance")
    timings["acceptance_seconds"] = round(time.monotonic() - phase, 3)

    inject = None
    if carrier["arm"] == arms.ARM_INJECT:
        phase = time.monotonic()
        inject_tree = run_dir / "inject"
        pilot_accept.copy_tree(run_dir / "candidate", inject_tree)
        inject = pilot_accept.inject_n7(inject_tree)
        timings["inject_seconds"] = round(time.monotonic() - phase, 3)

    classification = pilot_accept.classify(acceptance, inject)
    if worker.get("blocked"):
        verdict = INVALID
    else:
        verdict = classification["verdict"]
    cleanup = cleanup_run(run_dir, worker)
    acceptance["directory_removed"] = cleanup["acceptance_dir_removed"]

    report = worker.get("report") or {}
    record = {
        "schema": SCHEMA,
        "run_id": run_id,
        "task_id": task_id,
        "arm": carrier["arm"],
        "label": LABEL,
        "model": model if not fake_worker_mode else MODEL_FAKE,
        "measurement": "NOT_A_MEASUREMENT" if fake_worker_mode else "PILOT_RUN",
        "materials": carrier["materials"],
        "base_sha": workspace["base_sha"],
        "seal_sha256": pkg["seal"]["sha256"],
        "seal_files": pkg["seal"]["files"],
        "carrier": _record_carrier(carrier, delivery),
        "worker": {key: worker.get(key, UNKNOWN) for key in
                   ("kind", "exit_status", "seconds", "blocked", "stream_sha256")},
        "worker_report": report or UNKNOWN,
        "candidate": candidate,
        "acceptance": acceptance,
        "inject": inject,
        "verdict": verdict,
        "verdict_reasons": list(acceptance.get("reasons") or []),
        "cleanup": cleanup,
        "escape": classification["escape"],
        "durations": {**timings, "total_seconds": round(time.monotonic() - started, 3)},
        "tokens": report.get("tokens", UNKNOWN),
        "cost": report.get("cost", UNKNOWN),
        "authorization": ({"kind": "AUTHORIZED", **authorization,
                           "budget_enforcement": "MAX_RUNS_ONLY;RUN_COST_UNOBSERVED"}
                          if authorization else {"kind": MODEL_FAKE,
                                                 "budget_cap": UNKNOWN, "max_runs": UNKNOWN,
                                                 "budget_enforcement": "NOT_APPLICABLE:FAKE_WORKER"}),
        "unobserved": [name for name, value in (("tokens", report.get("tokens", UNKNOWN)),
                                                ("cost", report.get("cost", UNKNOWN)))
                       if value == UNKNOWN],
    }
    (run_dir / RECORD_NAME).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                                       encoding="utf-8")
    return record


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packages", action="append", required=True,
                        help="task package directory (repeatable)")
    parser.add_argument("--arms", default=",".join(arms.ARMS))
    parser.add_argument("--results-dir", required=True)
    parser.add_argument("--materials", default=None,
                        help="pinned materials commit for the FULL carrier (default: HEAD)")
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--fake-worker", action="store_true",
                        help="deterministic stub instead of a model launch (tests use this)")
    return parser.parse_args(argv)


def _summary(record: dict) -> str:
    gates = record["acceptance"]["gates"]
    hidden = gates.get("hidden_test", {}).get("verdict", UNKNOWN)
    ruff = gates.get("ruff", {}).get("verdict", UNKNOWN)
    inject = (record["inject"] or {}).get("verdict", UNKNOWN)
    return (f"{record['run_id']} verdict={record['verdict']} ruff={ruff} "
            f"hidden={hidden} inject={inject}")


def main(argv=None) -> int:
    args = _parse(argv)
    arm_list = [item.strip().upper() for item in args.arms.split(",") if item.strip()]
    unknown = [item for item in arm_list if item not in arms.ARMS]
    if not arm_list or unknown:
        print(f"REFUSED:UNKNOWN_ARM:{','.join(unknown) or 'EMPTY'}", file=sys.stderr)
        return 2
    duplicates = sorted({item for item in arm_list if arm_list.count(item) > 1})
    if duplicates:
        print(f"REFUSED:DUPLICATE_ARM:{','.join(duplicates)}", file=sys.stderr)
        return 2
    results = Path(args.results_dir).resolve()
    problem = results_dir_problem(results)
    if problem is not None:
        print(f"REFUSED:{problem}", file=sys.stderr)
        return 2
    authorization = None
    if not args.fake_worker:
        try:
            authorization = read_authorization()
        except AuthorizationError as exc:
            print(f"REFUSED:{exc}", file=sys.stderr)
            return 2
    try:
        durability = results_durability(results, args.fake_worker)
    except DriverRefusal as exc:
        print(f"REFUSED:{exc}", file=sys.stderr)
        return 2
    plan = [(package, arm) for package in args.packages for arm in arm_list]
    reason = plan_size_reason(len(plan), authorization)
    if reason is not None:
        print(f"REFUSED:{reason}", file=sys.stderr)
        return 2
    try:
        results.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        print(f"REFUSED:RESULTS_DIR_NOT_WRITABLE:{type(exc).__name__}", file=sys.stderr)
        return 2
    print(f"results_durability={durability} runs={len(plan)}")
    exit_code = 0
    for package, arm in plan:
        try:
            record = run_one(package, arm, results, fake_worker_mode=args.fake_worker,
                             materials=args.materials, model=args.model,
                             authorization=authorization)
        except (arms.CarrierError, pilot_accept.PackageError, pilot_accept.SealUnavailable,
                pilot_accept.SealRejected, pilot_accept.InjectionError, DriverRefusal) as exc:
            print(f"REFUSED:{type(exc).__name__}:{exc}", file=sys.stderr)
            return 2
        print(_summary(record))
        if record["verdict"] == INVALID:
            exit_code = 3
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
