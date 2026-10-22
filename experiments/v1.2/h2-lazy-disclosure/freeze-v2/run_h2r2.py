#!/usr/bin/env python3
"""The frozen run driver — the only way an H2-R2 run is executed (F7 / T18).

Subcommands, each taking `--runs-root R`:

    next             the next run id in plan order (or COMPLETE)
    run <run_id>     the five mechanical steps, the independent audit and the registry line
    status           the state of every planned run, plus the next run id

WHY THIS FILE EXISTS. Delivery (`wrapper_delivery`), briefing (`render_brief`), collection
(`collect_v2`), acceptance (`run_acceptance_v2`), preflight (`isolation_canary`) and the per-run
auditor (`run_audit_v2`) were frozen, but HOW a run is executed existed only as prose. Whatever an
operator typed at run time would have been an unfrozen experimental input that could differ
between arms or runs. Every launchable fact is therefore a module constant here —
`WORKER_COMMAND`, `LAUNCH_PROMPT`, `ENV_ALLOW`, `WALL_CLOCK_LIMIT_SECONDS` — and the file is
byte-pinned in freeze-manifest.json with an independent literal in the tests.

THE ORDER IS THE PLAN'S ORDER. A run starts only when every earlier run in run-plan-v2.json is
registered (ACCEPT, REJECT, INVALID and BLOCKED all count as registered). A run id that was ever
started is never started again: a second attempt is refused, and an interrupted run is registered
INVALID:INTERRUPTED so the plan can advance without a silent re-run (protocol-v2 §6).

`execute()` takes the stub/preflight/auditor/limit parameters so tests can drive a stub worker
(never a model). The `run` CLI exposes none of them.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import collect_v2
import isolation_canary
import run_acceptance_v2
import run_audit_v2
import wrapper_delivery
from wrapper_delivery import H2_REL, ROOT, sha256

FZ = Path(__file__).resolve().parent
PLAN_NAME = "run-plan-v2.json"
REGISTRY_NAME = "registry-v2.jsonl"
LOCK_DIR = ".locks"
RECORD_NAME = "run.json"
CONTRACT_NAME = "CONTRACT.md"
TEMPLATE_NAME = "worker-report-template.md"
COLLECTED_NAME = "collected.json"
VERDICT_NAME = "verdict.json"
EVENTS_NAME = "events.jsonl"
STDERR_NAME = "stderr.txt"

# The launchable facts of a run. Pinning the module in the manifest pins these.
WORKER_COMMAND = ("opencode", "run", "--standalone", "--auto", "--format", "json", "-m")
LAUNCH_PROMPT = "Read ./CONTRACT.md and do what it asks."
ENV_ALLOW = ("PATH", "LANG")
WALL_CLOCK_LIMIT_SECONDS = 90 * 60
# The auditor is launched with the same runtime, model, limit and environment; only the cwd and
# the prompt differ, so one run can never outlive two wall-clock limits.
AUDIT_LIMIT_SECONDS = WALL_CLOCK_LIMIT_SECONDS
ARTIFACT_EXCLUDED = ("repo",)

# Conservative combination of the mechanical verdict and the audit (protocol-v2 §5.4).
SEVERITY = {"ACCEPT": 0, "PASS": 0, "PARTIAL": 1, "REJECT": 2, "FAIL": 2, "INVALID": 3,
            "BLOCKED": 4}
AUDIT_AS_VERDICT = {"PASS": "ACCEPT", "PARTIAL": "REJECT", "FAIL": "REJECT",
                    "BLOCKED": "BLOCKED"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def plan_runs(root: Path = ROOT) -> list[dict]:
    return json.loads((Path(root) / H2_REL / "freeze-v2" / PLAN_NAME).read_text())["runs"]


def check_runs_root(runs_root: Path) -> Path:
    """R must pass the T13 run-root rule: outside every home, no guidance-bearing ancestor."""
    runs_root = Path(runs_root).resolve()
    reason = wrapper_delivery.run_root_reason(runs_root)
    if reason is not None:
        raise ValueError(reason)
    return runs_root


def registry_path(runs_root: Path) -> Path:
    return Path(runs_root) / REGISTRY_NAME


def read_registry(runs_root: Path) -> dict[str, dict]:
    """The append-only registry, keyed by run id. A duplicate id is fatal, never last-wins."""
    path = registry_path(runs_root)
    entries: dict[str, dict] = {}
    if not path.is_file():
        return entries
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except ValueError as exc:
            raise ValueError(f"REGISTRY_MALFORMED_LINE:{number}") from exc
        run_id = entry.get("run_id") if isinstance(entry, dict) else None
        if not isinstance(run_id, str) or not run_id:
            raise ValueError(f"REGISTRY_MALFORMED_LINE:{number}")
        if run_id in entries:
            raise ValueError(f"REGISTRY_DUPLICATE_RUN_ID:{run_id}")
        entries[run_id] = entry
    return entries


def lock_path(runs_root: Path, run_id: str) -> Path:
    return Path(runs_root) / LOCK_DIR / f"{run_id}.json"


def pid_alive(pid) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def next_run_id(runs_root: Path, root: Path = ROOT) -> str | None:
    """The first planned run that is not registered, in plan order; None when all are."""
    entries = read_registry(check_runs_root(runs_root))
    for run in plan_runs(root):
        if run["run_id"] not in entries:
            return run["run_id"]
    return None


def refusal(runs_root: Path, plan_run: dict, planned: list[dict],
            entries: dict[str, dict]) -> str | None:
    """Why `run` may not start this run, or None. Every refusal is checkable, none is advisory."""
    run_id = plan_run["run_id"]
    if run_id in entries:
        return "RUN_ALREADY_REGISTERED"
    order = [run["run_id"] for run in planned]
    missing = [earlier for earlier in order[:order.index(run_id)] if earlier not in entries]
    if missing:
        return f"PREDECESSOR_NOT_REGISTERED:{missing[0]}"
    lock = lock_path(runs_root, run_id)
    if lock.is_file():
        try:
            holder = json.loads(lock.read_text(encoding="utf-8")).get("pid")
        except (OSError, ValueError):
            holder = None
        return "RUN_IN_PROGRESS" if pid_alive(holder) else "RUN_ALREADY_STARTED"
    if (Path(runs_root) / run_id).exists():
        return "RUN_ALREADY_STARTED"
    return None


def profile_env_file(plan_run: dict, profile_env: Path | None) -> Path:
    """The frozen profile env file: the plan names the profile, nothing else may override it."""
    if profile_env is not None:
        return Path(profile_env).expanduser()
    return Path(plan_run["profile"]).expanduser() / "env.sh"


def worker_env(env_file: Path) -> dict[str, str]:
    """`export` lines of the profile env file over a minimal base env (PATH, LANG only)."""
    try:
        exported = isolation_canary.parse_profile_env(env_file.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError("PROFILE_ENV_UNREADABLE") from exc
    if not exported:
        raise ValueError("PROFILE_ENV_EMPTY")
    env = {key: os.environ[key] for key in ENV_ALLOW if key in os.environ}
    env.update(exported)
    return env


def launch(argv: list[str], cwd: Path, env: dict[str, str], limit_seconds: int,
           stdout_path: Path, stderr_path: Path) -> dict:
    """One command in its own process group, stdin closed, killed as a group at the limit."""
    with (Path(stdout_path).open("wb") as out, Path(stderr_path).open("wb") as err,
          open(os.devnull, "rb") as null):
        process = subprocess.Popen(list(argv), cwd=str(cwd), env=dict(env), stdin=null,
                                   stdout=out, stderr=err, start_new_session=True)
        timed_out = False
        try:
            code = process.wait(timeout=limit_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                process.kill()
            code = process.wait()
    return {"returncode": code, "timed_out": timed_out, "command": list(argv)}


def read_events(path: Path) -> tuple[list, int]:
    """The JSON event stream, line by line; the count of lines that are not JSON."""
    events: list = []
    malformed = 0
    if not Path(path).is_file():
        return events, malformed
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except ValueError:
            malformed += 1
    return events, malformed


def session_id(events: list) -> str | None:
    for event in events:
        if not isinstance(event, dict):
            continue
        for container in (event, event.get("part")):
            if not isinstance(container, dict):
                continue
            for key in ("sessionID", "session_id"):
                value = container.get(key)
                if isinstance(value, str) and value:
                    return value
    return None


def worker_reasons(result: dict, events: list, malformed: int) -> list[str]:
    """The terminal reasons of step 4; empty only when the worker really ran and finished."""
    if result["timed_out"]:
        return ["TIMEOUT"]
    reasons = []
    if not events:
        reasons.append("EMPTY_EVENT_STREAM")
    if any(isinstance(event, dict) and event.get("type") == "error" for event in events):
        reasons.append("WORKER_ERROR_EVENT")
    if result["returncode"] != 0:
        reasons.append(f"WORKER_EXIT:{result['returncode']}")
    if malformed:
        reasons.append(f"MALFORMED_EVENT_LINES:{malformed}")
    return reasons


def artifact_hashes(run_dir: Path) -> dict[str, str]:
    """sha256 of every run artifact; the task worktree under repo/ is not a run artifact."""
    hashes: dict[str, str] = {}
    run_dir = Path(run_dir)
    for path in sorted(run_dir.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(run_dir)
        if rel.parts and rel.parts[0] in ARTIFACT_EXCLUDED:
            continue
        hashes[rel.as_posix()] = sha256(path.read_bytes())
    return hashes


def start_step(record: dict, name: str) -> dict:
    entry = {"step": name, "started_at": now(), "finished_at": None, "status": "RUNNING"}
    record["steps"].append(entry)
    return entry


def finish_step(entry: dict, status: str, **extra) -> None:
    entry.update(extra)
    entry["status"] = status
    entry["finished_at"] = now()


def strictest(verdict: str, audit_verdict: str | None) -> str:
    """The stricter of the mechanical verdict and the audit; the audit can only tighten."""
    if audit_verdict is None or audit_verdict == "SKIPPED":
        return verdict
    mapped = AUDIT_AS_VERDICT.get(audit_verdict, "BLOCKED")
    return verdict if SEVERITY[mapped] <= SEVERITY[verdict] else mapped


def register(runs_root: Path, plan_run: dict, *, verdict: str | None, reason: str | None,
             run_dir: Path, audit_verdict: str | None = None, session: str | None = None,
             wall_clock: float | None = None, started_at: str | None = None,
             registered_by: str | None = None) -> dict:
    """Append the one registry line of a run. Appending is the only way a run is registered."""
    line = {"run_id": plan_run["run_id"], "task_id": plan_run["task_id"],
            "arm": plan_run["arm"], "verdict": verdict, "audit_verdict": audit_verdict,
            "final_verdict": strictest(verdict, audit_verdict),
            "reason": reason or None, "session_id": session, "wall_clock_seconds": wall_clock,
            "started_at": started_at, "finished_at": now(),
            "artifacts": artifact_hashes(run_dir) if Path(run_dir).is_dir() else {}}
    if registered_by is not None:
        line["registered_by"] = registered_by
    with registry_path(runs_root).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(line, sort_keys=True) + "\n")
    return line


def execute(run_id: str, runs_root: Path, *, root: Path = ROOT, worker_command=None,
            preflight=None, auditor=None, limit_seconds: int | None = None,
            audit_limit_seconds: int | None = None, profile_env: Path | None = None) -> dict:
    """Execute one planned run. Refusals allocate nothing; every other path ends registered."""
    root = Path(root).resolve()
    runs_root = check_runs_root(runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)
    planned = plan_runs(root)
    plan_run = next((run for run in planned if run["run_id"] == run_id), None)
    if plan_run is None:
        raise ValueError("UNKNOWN_RUN")
    entries = read_registry(runs_root)
    reason = refusal(runs_root, plan_run, planned, entries)
    if reason is not None:
        if reason == "RUN_ALREADY_STARTED":
            register_interrupted(runs_root, plan_run)
        return {"outcome": "REFUSED", "run_id": run_id, "reason": reason}

    run_dir = runs_root / run_id
    env_file = profile_env_file(plan_run, profile_env)
    command = tuple(worker_command or WORKER_COMMAND)
    limit = WALL_CLOCK_LIMIT_SECONDS if limit_seconds is None else int(limit_seconds)
    audit_limit = AUDIT_LIMIT_SECONDS if audit_limit_seconds is None else int(audit_limit_seconds)
    started = time.monotonic()
    record = {"schema_version": 1, "program": "freeze-v2/run_h2r2.py", "run_id": run_id,
              "task_id": plan_run["task_id"], "arm": plan_run["arm"],
              "materials_commit": plan_run["materials_commit"], "model": plan_run["model"],
              "runtime": plan_run["runtime"], "profile_env": str(env_file),
              "worker_command": list(command), "launch_prompt": LAUNCH_PROMPT,
              "env_allow_list": list(ENV_ALLOW), "limit_seconds": limit,
              "audit_limit_seconds": audit_limit, "started_at": now(), "finished_at": None,
              "wall_clock_seconds": None, "verdict": None, "audit_verdict": None,
              "final_verdict": None, "reasons": [], "session_id": None, "steps": []}
    lock = acquire_lock(runs_root, run_id)

    def save() -> None:
        (run_dir / RECORD_NAME).write_text(json.dumps(record, indent=2) + "\n",
                                           encoding="utf-8")

    def finish(verdict: str, reasons: list[str], audit: dict | None = None) -> dict:
        record["verdict"] = verdict
        record["reasons"] = list(reasons)
        record["audit_verdict"] = audit["verdict"] if audit else None
        record["final_verdict"] = strictest(verdict, record["audit_verdict"])
        record["finished_at"] = now()
        record["wall_clock_seconds"] = round(time.monotonic() - started, 3)
        entry = start_step(record, "registry")
        finish_step(entry, "DONE", file=REGISTRY_NAME)
        save()
        line = register(runs_root, plan_run, verdict=record["verdict"],
                        reason=";".join(record["reasons"]), run_dir=run_dir,
                        audit_verdict=record["audit_verdict"], session=record["session_id"],
                        wall_clock=record["wall_clock_seconds"],
                        started_at=record["started_at"])
        annotate_lock(lock, record["final_verdict"])
        return {"outcome": "EXECUTED", "run_dir": str(run_dir),
                "registry": str(registry_path(runs_root)), "session_id": record["session_id"],
                "verdict": record["verdict"], "audit_verdict": record["audit_verdict"],
                "final_verdict": line["final_verdict"], "reasons": record["reasons"],
                "wall_clock_seconds": record["wall_clock_seconds"]}

    entry = start_step(record, "prepare")
    try:
        wrapper_delivery.prepare(root, run_dir, plan_run["task_id"], plan_run["arm"],
                                 plan_run["materials_commit"])
    except ValueError as exc:
        finish_step(entry, "FAILED", reasons=[str(exc)])
        reason = f"PREPARE_FAILED:{exc}"
        line = register(runs_root, plan_run, verdict="INVALID", reason=reason, run_dir=run_dir)
        annotate_lock(lock, line["final_verdict"])
        return {"outcome": "EXECUTED", "run_dir": str(run_dir),
                "final_verdict": line["final_verdict"], "verdict": "INVALID",
                "audit_verdict": None, "reasons": [reason], "session_id": None,
                "wall_clock_seconds": round(time.monotonic() - started, 3)}
    finish_step(entry, "DONE")
    save()

    entry = start_step(record, "preflight")
    attester = preflight or isolation_canary.preflight
    try:
        attestation = attester(run_dir, env_file)
    except ValueError as exc:
        attestation = {"verdict": "FAIL", "reasons": [str(exc)]}
    if attestation.get("verdict") != "PASS":
        found = [str(item) for item in attestation.get("reasons", [])] or ["PREFLIGHT_FAIL"]
        finish_step(entry, "BLOCKED", reasons=found)
        return finish("BLOCKED", [f"PREFLIGHT_FAIL:{reason}" for reason in found])
    finish_step(entry, "PASS")
    save()

    entry = start_step(record, "brief")
    brief = subprocess.run([sys.executable, str(FZ / "render_brief.py"), "--run-id", run_id,
                            "--python", sys.executable, "--out", str(run_dir / CONTRACT_NAME)],
                           capture_output=True, text=True)
    if brief.returncode != 0 or not (run_dir / CONTRACT_NAME).is_file():
        finish_step(entry, "FAILED", returncode=brief.returncode)
        return finish("INVALID", [f"BRIEF_FAILED:{brief.returncode}"])
    finish_step(entry, "DONE", sha256=sha256((run_dir / CONTRACT_NAME).read_bytes()),
                template=(run_dir / TEMPLATE_NAME).is_file())
    save()

    entry = start_step(record, "worker")
    try:
        env = worker_env(env_file)
    except ValueError as exc:
        finish_step(entry, "FAILED", reasons=[str(exc)])
        return finish("INVALID", [str(exc)])
    result = launch([*command, plan_run["model"], LAUNCH_PROMPT], run_dir, env, limit,
                    run_dir / EVENTS_NAME, run_dir / STDERR_NAME)
    events, malformed = read_events(run_dir / EVENTS_NAME)
    record["session_id"] = session_id(events)
    reasons = worker_reasons(result, events, malformed)
    finish_step(entry, "INVALID" if reasons else "DONE", returncode=result["returncode"],
                timed_out=result["timed_out"], events=len(events), malformed=malformed,
                reasons=reasons)
    save()
    if reasons:
        return worker_terminal(run_dir, record, root, finish, reasons)

    entry = start_step(record, "acceptance")
    collected = collect_v2.collect(root, run_dir)
    (run_dir / COLLECTED_NAME).write_text(
        json.dumps(collected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verdict = run_acceptance_v2.accept(root, run_dir)
    (run_dir / VERDICT_NAME).write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    finish_step(entry, verdict["verdict"], reasons=verdict["reasons"],
                collected=collected["status"], diff_sha256=collected["diff_sha256"])
    save()

    audit: dict | None = None
    if verdict["verdict"] in ("ACCEPT", "REJECT"):
        entry = start_step(record, "audit")
        chosen = auditor or run_audit_v2.audit
        try:
            audit = chosen(run_dir, plan_run, task_of(root, plan_run["task_id"]),
                           launch=launch, command=command, env=env,
                           limit_seconds=audit_limit)
        except (ValueError, OSError) as exc:
            audit = {"verdict": "BLOCKED", "reasons": [f"AUDIT_FAILED:{exc}"], "leakage": []}
        finish_step(entry, audit.get("verdict", "BLOCKED"),
                    reasons=audit.get("reasons", []), leakage=audit.get("leakage", []))
        save()
    else:
        audit = {"verdict": "SKIPPED", "reasons": [f"RUN_{verdict['verdict']}"], "leakage": []}
        entry = start_step(record, "audit")
        finish_step(entry, "SKIPPED", reasons=audit["reasons"])

    reasons = list(verdict["reasons"])
    if audit["verdict"] == "BLOCKED":
        reasons = reasons + [f"AUDIT_BLOCKED:{reason}" for reason in audit.get("reasons", [])]
    return finish(verdict["verdict"], reasons, audit)


def worker_terminal(run_dir: Path, record: dict, root: Path, finish, reasons):
    """An invalid worker is terminal, but the run still gets its collection and its verdict.

    Collecting after a timeout or an error is evidence, not a second chance: acceptance is run so
    the run has exactly one verdict JSON, and the terminal reason is never softened by it.
    """
    entry = start_step(record, "acceptance")
    collected = collect_v2.collect(root, run_dir)
    (run_dir / COLLECTED_NAME).write_text(
        json.dumps(collected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    verdict = run_acceptance_v2.accept(root, run_dir)
    (run_dir / VERDICT_NAME).write_text(json.dumps(verdict, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    finish_step(entry, verdict["verdict"], collected=collected["status"],
                diff_sha256=collected["diff_sha256"], terminal="INVALID")
    audit = {"verdict": "SKIPPED", "reasons": ["RUN_INVALID"], "leakage": []}
    entry = start_step(record, "audit")
    finish_step(entry, "SKIPPED", reasons=audit["reasons"])
    return finish("INVALID", reasons, audit)


def task_of(root: Path, task_id: str) -> dict:
    registry = json.loads((Path(root) / H2_REL / "freeze-v2" / "task-registry-v2.json")
                          .read_text())
    return next(task for task in registry["tasks"] if task["task_id"] == task_id)


def acquire_lock(runs_root: Path, run_id: str) -> Path:
    path = lock_path(runs_root, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"run_id": run_id, "pid": os.getpid(), "started_at": now()}) + "\n",
                    encoding="utf-8")
    return path


def annotate_lock(path: Path, verdict: str) -> None:
    try:
        entry = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        entry = {}
    entry.update({"finished_at": now(), "final_verdict": verdict})
    Path(path).write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")


def register_interrupted(runs_root: Path, plan_run: dict) -> None:
    """A started run that never registered is registered now, once, as INVALID:INTERRUPTED."""
    register(runs_root, plan_run, verdict="INVALID", reason="INTERRUPTED",
             run_dir=Path(runs_root) / plan_run["run_id"],
             registered_by="SECOND_START_ATTEMPT_REFUSED")


def status(runs_root: Path, root: Path = ROOT) -> dict:
    runs_root = check_runs_root(runs_root)
    entries = read_registry(runs_root)
    rows = []
    for plan_run in plan_runs(root):
        run_id = plan_run["run_id"]
        run_dir = runs_root / run_id
        if run_id in entries:
            entry = entries[run_id]
            state = "REGISTERED"
            row = {"verdict": entry.get("verdict"), "audit_verdict": entry.get("audit_verdict"),
                   "final_verdict": entry.get("final_verdict"), "reason": entry.get("reason"),
                   "wall_clock_seconds": entry.get("wall_clock_seconds")}
        elif (run_dir / RECORD_NAME).is_file() or lock_path(runs_root, run_id).is_file():
            state = "STARTED_NOT_REGISTERED"
            row = {"record": (run_dir / RECORD_NAME).is_file()}
        else:
            state = "NOT_STARTED"
            row = {}
        rows.append({"run_id": run_id, "task_id": plan_run["task_id"],
                     "arm": plan_run["arm"], "state": state, **row})
    registered = sum(1 for row in rows if row["state"] == "REGISTERED")
    return {"runs_root": str(runs_root), "planned": len(rows), "registered": registered,
            "next": next((row["run_id"] for row in rows if row["state"] != "REGISTERED"), None),
            "runs": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    nxt = commands.add_parser("next", help="print the next run id in plan order")
    nxt.add_argument("--runs-root", required=True, type=Path)
    run = commands.add_parser("run", help="execute one planned run")
    run.add_argument("run_id")
    run.add_argument("--runs-root", required=True, type=Path)
    show = commands.add_parser("status", help="print the state of every planned run")
    show.add_argument("--runs-root", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "status":
            print(json.dumps(status(args.runs_root), indent=2, sort_keys=True))
            return 0
        if args.command == "next":
            run_id = next_run_id(args.runs_root)
            print(run_id if run_id is not None else "COMPLETE")
            return 0
        result = execute(args.run_id, args.runs_root)
        print(json.dumps(result, sort_keys=True))
        return 0 if result.get("final_verdict") == "ACCEPT" else 1
    except ValueError as exc:
        parser.exit(1, f"RUN_H2R2_FAIL {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
