#!/usr/bin/env python3
"""The per-run independent auditor (protocol-v2 §5 step 4, rubric §4 and §10) — F7 / T19.

After acceptance, a FRESH opencode session in the same isolated profile, with the same model and
the same command, is started in `R/<run_id>/audit/` — outside the worker's directory — with a
blind bundle and one frozen prompt. The auditor writes `audit.json`; this module validates it and
turns it into the audit half of the run's verdict.

THE BUNDLE IS BLIND BY CONSTRUCTION, NOT BY TRUST:

  * `CONTRACT.md` is the worker contract with the delivery-identity block (RUN_ID, ARM,
    CARRIER_KIND, CARRIER_SHA256, MATERIALS_COMMIT) removed between its two markers, and T38a
    (F38) builds it from the DRIVER's copy (`.driver/<run_id>/CONTRACT.md`) rather than from the
    run directory the worker can write; a run-dir copy that differs is a tamper, not a source;
  * `verdict.json` is a whitelist projection of the mechanical verdict: `run_id`, `arm`,
    `run_dir`, `materials_commit`, `base_sha` and `case_id` never enter the bundle (T38a / F41:
    the last two name the task and its base, so the auditor would judge a known task instead of
    the four files in front of it);
  * `diff.patch` is the collected base->worker delta and `report.md` is the worker's own report
    (from the driver's snapshot, when the driver supplies one);
  * the carrier text, the `H2_WARM/` bundle and the telemetry are NOT copied — and where a
    remaining string still names the arm (a worker that wrote the carrier name into its report,
    say) the frozen scan below records it as `LEAKAGE` against rubric §10 instead of pretending
    the bundle is clean. The scan is best effort and its output is kept either way.

H2_WARM is deliberately NOT a leakage token: both arms receive the same layout (README §3), so
naming it distinguishes nothing. The tokens below are the facts that really differ between arms.

A missing, unreadable or malformed `audit.json` makes the run BLOCKED — visibly, and never
INVALID and never a pass, because an unread audit is an absent judgement, not a bad worker.
"""
from __future__ import annotations

import json
from pathlib import Path

import wrapper_delivery
from wrapper_delivery import sha256

AUDIT_DIR = "audit"
CONTRACT_NAME = "CONTRACT.md"
REPORT_NAME = "report.md"
DIFF_NAME = "diff.patch"
VERDICT_NAME = "verdict.json"
COLLECTED_NAME = "collected.json"
EVENTS_NAME = "events.jsonl"
STDERR_NAME = "stderr.txt"
REQUEST_NAME = "audit-request.json"
RESULT_NAME = "audit.json"

BLOCK_BEGIN = "<!-- BOOTSTRAP_DELIVERY_BEGIN -->"
BLOCK_END = "<!-- BOOTSTRAP_DELIVERY_END -->"
BLIND_NOTE = ("[delivery identity block removed: judge the contract and the artefacts below "
              "only]\n")

CORRECTNESS = ("PASS", "FAIL", "PARTIAL", "BLOCKED")
SEVERITIES = ("P0", "P1", "P2", "P3")
CATEGORIES = {
    "HV1": "correctness or safety defect, including one that silently changes the product",
    "HV2": "a mechanical gate that passes falsely",
    "HV3": "wrong repository, base or worktree",
    "HV4": "scope violation",
    "HV5": "completion claimed without evidence (false closure)",
    "HV6": "an undisposed substantive finding",
    "HV7": "a missing required artefact",
    "HV8": "a route or retrieval failure that changed the result",
}

# Facts that differ between the arms. Scanned in every bundle file; a hit is recorded, not fixed.
ARM_REVEALING = ("h2r3-", "control_full_v1", "variant_lean_v1", "control-carrier",
                 "H2_LEAN_BOOTSTRAP", "ARM = control", "ARM = variant", "CARRIER_KIND",
                 "CARRIER_SHA256")
# The mechanical verdict is copied field by field; run identity and arm never enter the bundle.
# T38a / F41: `base_sha` and `case_id` are gone too — they name the task and its registered base,
# which the auditor must not be able to look up while judging the four files it was given.
VERDICT_KEEP = ("schema_version", "verdict", "reasons", "task_id",
                "oracle", "scope", "full_suite", "collected", "collected_diff_sha256",
                "spellings")

AUDIT_PROMPT = (
    "You are the independent auditor of one finished run. You have not seen the worker's "
    "session and you must not try to. Read only these four files in this directory: "
    "./CONTRACT.md, ./verdict.json, ./diff.patch, ./report.md. Do not run commands, do not read "
    "anything outside this directory, and do not search for the task's history.\n"
    "Decide FINAL_CORRECTNESS against ./CONTRACT.md: PASS (contract met and the mechanical "
    "verdict is consistent), PARTIAL (main goal met with a minor gap you enumerate), FAIL "
    "(contract not met, including a completion claim the evidence does not support), BLOCKED "
    "(the four files cannot support any verdict).\n"
    "List findings. Each finding is an object with: id, severity (P0/P1/P2/P3), category (one "
    "of HV1..HV8 or null), location, evidence. Categories: HV1 correctness or safety defect; "
    "HV2 a mechanical gate that passes falsely; HV3 wrong repository, base or worktree; HV4 "
    "scope violation; HV5 completion claimed without evidence; HV6 an undisposed substantive "
    "finding; HV7 a missing required artefact; HV8 a route or retrieval failure that changed "
    "the result. Every finding needs a pointer into one of the four files; keep no finding "
    "without evidence, and do not invent one to fill the list.\n"
    "Write ./audit.json as {\"correctness\": <PASS|FAIL|PARTIAL|BLOCKED>, "
    "\"invalid_completion\": <true|false>, \"findings\": [<finding>, ...], \"notes\": "
    "<string>}. Then answer in one line: AUDIT_DONE <correctness>."
)


def blind_contract(text: str) -> str:
    """The worker contract with the delivery-identity block replaced by a neutral note."""
    begin = text.find(BLOCK_BEGIN)
    end = text.find(BLOCK_END)
    if begin < 0 or end < begin:
        raise ValueError("DELIVERY_BLOCK_NOT_FOUND")
    return text[:begin] + BLIND_NOTE + text[end + len(BLOCK_END):]


def project_verdict(verdict: dict) -> dict:
    """The auditable part of the mechanical verdict, with no run identity and no arm."""
    if not isinstance(verdict, dict):
        raise ValueError("VERDICT_NOT_AN_OBJECT")
    return {key: verdict[key] for key in VERDICT_KEEP if key in verdict}


def scan(files: dict[str, str]) -> list[dict]:
    """Every arm-revealing string left in the bundle: recorded as LEAKAGE, never rewritten."""
    hits = []
    for name in sorted(files):
        for token in ARM_REVEALING:
            if token in files[name]:
                hits.append({"file": name, "token": token})
    return hits


def prepare_bundle(run_dir: Path, plan_run: dict, task: dict, *,
                   contract_path: Path | None = None,
                   report_path: Path | None = None,
                   bundle_dir: Path | None = None) -> dict:
    """Copy the blind bundle into `<run_dir>/audit/` and record what went in and what leaked.

    T38a (F38 / F33): `contract_path` is the DRIVER's copy of the rendered contract and
    `report_path` is the worker's report inside the driver's snapshot. The driver passes both;
    without them the run directory is used, which is the CLI form only.
    T51c: `bundle_dir` puts the bundle somewhere else — the audit retry keeps it under its own
    driver directory — while every input is still read from the run's existing frozen materials.
    """
    run_dir = Path(run_dir).absolute()
    if plan_run["task_id"] != task["task_id"]:
        raise ValueError("TASK_ID_MISMATCH")
    audit_dir = Path(bundle_dir) if bundle_dir is not None else run_dir / AUDIT_DIR
    # F19 / T29: the driver creates the auditor's launch directory before the fresh home (its
    # TMPDIR lives inside it); the bundle still goes in before the auditor is launched.
    audit_dir.mkdir(parents=True, exist_ok=True)
    contract = wrapper_delivery.safe_read(Path(contract_path or run_dir / CONTRACT_NAME)).decode("utf-8")
    collected = json.loads(wrapper_delivery.safe_read(run_dir / COLLECTED_NAME).decode("utf-8"))
    verdict = json.loads(wrapper_delivery.safe_read(run_dir / VERDICT_NAME).decode("utf-8"))
    report = Path(report_path or run_dir / REPORT_NAME)
    try:
        report_data = wrapper_delivery.safe_read(report)
    except OSError as exc:
        raise ValueError("REPORT_MISSING") from exc
    files = {
        CONTRACT_NAME: blind_contract(contract),
        DIFF_NAME: str(collected.get("diff", "")),
        VERDICT_NAME: json.dumps(project_verdict(verdict), indent=2, sort_keys=True) + "\n",
        REPORT_NAME: report_data.decode("utf-8", errors="replace"),
    }
    for name, text in files.items():
        wrapper_delivery.safe_write(audit_dir / name, text.encode("utf-8"))
    leakage = scan(files)
    request = {"schema_version": 1, "program": "freeze-v3/run_audit_v2.py",
               "run_id": plan_run["run_id"], "task_id": plan_run["task_id"],
               "model": plan_run["model"], "output": RESULT_NAME,
               "blind": [CONTRACT_NAME, DIFF_NAME, VERDICT_NAME, REPORT_NAME],
               "excluded": ["carrier text", "H2_WARM bundle", "telemetry", "run identity",
                            "arm label"],
               "observation_scope": ("Best-effort blinding: the bundle is built from the run's "
                                     "artefacts, and what remains is recorded as leakage."),
               "contract_sha256": sha256(contract.encode("utf-8")),
               "correctness": list(CORRECTNESS),
               "severity": list(SEVERITIES),
               "category": CATEGORIES,
               "leakage": leakage,
               "bundle": {name: sha256(text.encode()) for name, text in files.items()}}
    wrapper_delivery.safe_write(audit_dir / REQUEST_NAME,
                                (json.dumps(request, indent=2, sort_keys=True) + "\n").encode())
    return {"audit_dir": str(audit_dir), "leakage": leakage, "request": request}


def finding_problems(index: int, finding) -> list[str]:
    if not isinstance(finding, dict):
        return [f"AUDIT_FINDING_{index}:NOT_AN_OBJECT"]
    problems = []
    if not isinstance(finding.get("id"), str) or not finding["id"].strip():
        problems.append(f"AUDIT_FINDING_{index}:ID_MISSING")
    if finding.get("severity") not in SEVERITIES:
        problems.append(f"AUDIT_FINDING_{index}:SEVERITY_INVALID")
    if finding.get("category") is not None and finding.get("category") not in CATEGORIES:
        problems.append(f"AUDIT_FINDING_{index}:CATEGORY_INVALID")
    if not isinstance(finding.get("evidence"), str) or not finding["evidence"].strip():
        problems.append(f"AUDIT_FINDING_{index}:EVIDENCE_MISSING")
    if not isinstance(finding.get("location"), str):
        problems.append(f"AUDIT_FINDING_{index}:LOCATION_MISSING")
    return problems


def validate(data) -> list[str]:
    """Everything the audit must carry; any gap is a malformed audit, i.e. BLOCKED."""
    if not isinstance(data, dict):
        return ["AUDIT_NOT_AN_OBJECT"]
    problems = []
    if data.get("correctness") not in CORRECTNESS:
        problems.append("AUDIT_CORRECTNESS_INVALID")
    findings = data.get("findings")
    if not isinstance(findings, list):
        problems.append("AUDIT_FINDINGS_NOT_A_LIST")
    else:
        for index, finding in enumerate(findings):
            problems.extend(finding_problems(index, finding))
    if "invalid_completion" in data and not isinstance(data["invalid_completion"], bool):
        problems.append("AUDIT_INVALID_COMPLETION_NOT_BOOLEAN")
    return problems


def evaluate(audit_dir: Path, bundle: dict) -> dict:
    """The audit record: correctness, findings and leakage; BLOCKED unless the audit is complete."""
    record = {"verdict": "BLOCKED", "correctness": None, "findings": [],
              "invalid_completion": None, "leakage": list(bundle.get("leakage", [])),
              "reasons": []}
    path = Path(audit_dir) / RESULT_NAME
    try:
        data = json.loads(wrapper_delivery.safe_read(path))
    except FileNotFoundError:
        record["reasons"] = ["AUDIT_MISSING"]
        return record
    except (OSError, ValueError):
        record["reasons"] = ["AUDIT_UNREADABLE"]
        return record
    problems = validate(data)
    if problems:
        record["reasons"] = problems
        return record
    record.update({"verdict": data["correctness"], "correctness": data["correctness"],
                   "findings": data["findings"],
                   "invalid_completion": bool(data.get("invalid_completion", False)),
                   "notes": data.get("notes") if isinstance(data.get("notes"), str) else None})
    return record


def audit(run_dir: Path, plan_run: dict, task: dict, *, launch, command, env,
          limit_seconds: int, events_path: Path | None = None,
          stderr_path: Path | None = None, contract_path: Path | None = None,
          report_path: Path | None = None, bundle_dir: Path | None = None) -> dict:
    """Build the blind bundle, run one fresh session in it, and validate what it wrote.

    F17 / T29: `events_path`/`stderr_path` let the driver keep the authoritative copy of the
    stream outside the audit directory (and outside the sandbox's writable set); the bundle's own
    directory only receives what the auditor writes there. T38a: `contract_path` and
    `report_path` are the driver's contract copy and the snapshot's report. T51c: `bundle_dir`
    moves the bundle out of the run directory for an audit retry; the inputs do not change.
    """
    bundle = prepare_bundle(run_dir, plan_run, task, contract_path=contract_path,
                            report_path=report_path, bundle_dir=bundle_dir)
    audit_dir = Path(bundle["audit_dir"])
    result = launch([*command, plan_run["model"], AUDIT_PROMPT], audit_dir, env, limit_seconds,
                    Path(events_path) if events_path else audit_dir / EVENTS_NAME,
                    Path(stderr_path) if stderr_path else audit_dir / STDERR_NAME)
    record = evaluate(audit_dir, bundle)
    record["launch"] = result
    record["events_path"] = str(events_path) if events_path else str(audit_dir / EVENTS_NAME)
    if result["timed_out"]:
        record["verdict"] = "BLOCKED"
        record["reasons"] = sorted(set(record["reasons"]) | {"AUDIT_TIMEOUT"})
    elif result["returncode"] != 0:
        record["verdict"] = "BLOCKED"
        record["reasons"] = sorted(set(record["reasons"])
                                   | {f"AUDIT_EXIT:{result['returncode']}"})
    return record
