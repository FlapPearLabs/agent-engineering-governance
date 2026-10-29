#!/usr/bin/env python3
"""Measure frozen historical acceptances and the per-base F-010 injection.

Two oracle paths are measured, read-only, against a disposable `git clone --shared`:

* `oracle_kind == "freeze_v3"`: the freeze-v3 acceptance program is imported, not
  reimplemented (`run_acceptance_v2.accept`), and called twice on the same prepared
  run: once on the unchanged base and once after the candidate's non-test delta.
* otherwise: the frozen test is run at both revisions with the H2 acceptance command.

The F-010 injection ("a gate that always passes") is then applied to the task's own
base tree, because that is the tree the task's gate has to catch a defect in. A base
without `ruff.toml` gets the gate that does exist there: the `markdown-links-resolve`
predicate of `scripts/validate_governance.py` is forced to `True` and the N7 governance
probe must report the hollowed gate. A base with no measurable gate at all is
`INJECT_NOT_APPLICABLE`, never `PROBE_ERROR`.
"""
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[3]
ADMISSION = ROOT / "experiments/v1.2/h2-lazy-disclosure/admission"
GATES = ROOT / "experiments/v1.2/gate-load-bearing/gates.json"
sys.path.insert(0, str(ADMISSION))
import measure  # noqa: E402

LOW_RISKS = ("MICRO", "LOW")
RUFF_SELECT = r'(?m)^select\s*=\s*\["E9",\s*"F"\]\s*$'
GOVERNANCE_PREDICATE = r'check\("markdown-links-resolve",\s*[^,]+,\s*'


def load_probe():
    path = ROOT / "experiments/v1.2/gate-load-bearing/probe_gates.py"
    spec = importlib.util.spec_from_file_location("n7_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_acceptance():
    path = ROOT / "experiments/v1.2/h2-lazy-disclosure/freeze-v3"
    sys.path.insert(0, str(path))
    spec = importlib.util.spec_from_file_location("run_acceptance_v2",
                                                  path / "run_acceptance_v2.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def acceptance_transition(base, candidate):
    """True only for a base the oracle rejects on its own and a candidate it accepts."""
    if base["verdict"] == "INVALID" or candidate["verdict"] == "INVALID":
        raise ValueError("freeze-v3 acceptance invalid: " + str(base.get("reasons", []))
                         + " / " + str(candidate.get("reasons", [])))
    reasons = base.get("reasons", [])
    return (base["verdict"] == "REJECT"
            and all("WORKER_NOT_PASSING:" + style in reasons
                    for style in ("RESOLVED", "SYMLINKED"))
            and not any(reason.startswith("BASE_NOT_FAILING:") for reason in reasons)
            and candidate["verdict"] == "ACCEPT")


def freeze_v3_measure(repo, task, directory):
    """Reuse freeze-v3's own acceptance: unchanged base, then the candidate delta."""
    acceptance = load_acceptance()
    wrapper = acceptance.wrapper_delivery
    fixture = Path(directory) / "fixture"
    materials = git(repo, "rev-parse", "HEAD")
    try:
        wrapper.prepare(repo, fixture, task["id"], "control", materials)
        (fixture / "report.md").write_text("# report\n\nFilled.\n", encoding="utf-8")
        (fixture / ".h2-telemetry.log").write_text("READ FULL repo/RULES.md\n",
                                                   encoding="utf-8")
        before = acceptance.accept(repo, fixture)
        patch = subprocess.run(["git", "-C", str(repo), "diff", "--binary",
                                task["base"], task["candidate"], "--", ":!scripts/tests"],
                               check=True, capture_output=True).stdout
        subprocess.run(["git", "-C", str(fixture / "repo"), "apply", "--whitespace=nowarn"],
                       input=patch, check=True, capture_output=True)
        after = acceptance.accept(repo, fixture)
        return before, after
    finally:
        wrapper.cleanup(repo, fixture)


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def base_tree(repo, revision, destination):
    """A disposable copy of `revision`'s tree, with no git metadata to mutate."""
    archive = subprocess.run(["git", "-C", str(repo), "archive", revision],
                             check=True, capture_output=True).stdout
    destination.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(destination, filter="data")
    return destination


def run_oracle(root, path):
    command = measure.ctc.acceptance_command(path, "TEST", sys.executable)
    with measure.ctc.acceptance_env() as env:
        result = subprocess.run(command, cwd=root, env=env, capture_output=True,
                                text=True, timeout=measure.ctc.ACCEPTANCE_TIMEOUT)
    output = result.stdout + result.stderr
    if (not re.search(r"(?m)^Ran [1-9][0-9]* tests? in ", output)
            or re.search(r"(?m)^FAILED \(.*errors=", output)
            or "skipped=" in output
            or result.returncode not in (0, 1)
            or (result.returncode == 1 and not re.search(r"(?m)^FAILED \(failures=", output))
            or (result.returncode == 0 and not re.search(r"(?m)^OK$", output))):
        raise ValueError("oracle did not produce a clean unittest success or assertion failure")
    return result.returncode


def injected(status, **fields):
    fields.update({"status": status})
    return fields


def ruff_injection(tree, probe):
    """F-010 on a ruff base: hollow `select`, the F841 control must stop being caught."""
    config = tree / "ruff.toml"
    original = config.read_text(encoding="utf-8")
    hollowed, count = re.subn(RUFF_SELECT, "select = []", original)
    if count != 1:
        return injected("INJECT_NOT_APPLICABLE", kind="ruff",
                        reason="base ruff.toml has no unique E9,F select line")
    gate = next(gate for gate in json.loads(GATES.read_text())["gates"] if gate["id"] == "ruff")
    control = tree / "scripts/n7_control.py"
    if control.exists():
        raise ValueError("n7 control already exists in the base tree")

    def caught():
        control.write_text("def example():\n    unused = 1\n", encoding="utf-8")
        try:
            result = probe.run("python3 -m ruff check scripts/n7_control.py", tree)
        finally:
            control.unlink()
        return result

    clean = probe.probe_tree(tree, {"gates": [gate]})[0]
    before = caught()
    config.write_text(hollowed, encoding="utf-8")
    after = caught()
    hollow = probe.probe_tree(tree, {"gates": [gate]})[0]
    config.write_text(original, encoding="utf-8")
    detected = (clean["status"] == "LOAD_BEARING" and before.returncode == 1
                and "F841" in before.stdout and after.returncode == 0
                and hollow["status"] == "GATE_NOT_LOAD_BEARING")
    return injected("DETECTED" if detected else "NOT_DETECTED", kind="ruff",
                    gate="N7 ruff load-bearing probe",
                    clean=clean["status"], hollow=hollow["status"],
                    control_before=before.returncode, control_after=after.returncode,
                    crucible="F841" if "F841" in before.stdout else None)


def governance_injection(tree, probe):
    """F-010 on a base without ruff: force one validate_governance predicate to True."""
    script = tree / "scripts/validate_governance.py"
    if not script.is_file():
        return injected("INJECT_NOT_APPLICABLE", kind="none",
                        reason="base has neither ruff.toml nor scripts/validate_governance.py")
    original = script.read_text(encoding="utf-8")
    hollowed, count = re.subn(GOVERNANCE_PREDICATE,
                              'check("markdown-links-resolve", True, ', original, count=1)
    if count != 1:
        return injected("INJECT_NOT_APPLICABLE", kind="governance",
                        reason="base validate_governance has no unique markdown-links-resolve call")
    gate = next(gate for gate in json.loads(GATES.read_text())["gates"]
                if gate["id"] == "governance")
    clean = probe.probe_tree(tree, {"gates": [gate]})[0]
    script.write_text(hollowed, encoding="utf-8")
    try:
        hollow = probe.probe_tree(tree, {"gates": [gate]})[0]
        direct = probe.run("python3 scripts/validate_governance.py", tree)
    finally:
        script.write_text(original, encoding="utf-8")
    detected = (clean["status"] == "LOAD_BEARING" and direct.returncode == 0
                and hollow["status"] == "GATE_NOT_LOAD_BEARING")
    return injected("DETECTED" if detected else "NOT_DETECTED", kind="governance",
                    gate="N7 governance load-bearing probe",
                    clean=clean["status"], hollow=hollow["status"],
                    hollow_run_rc=direct.returncode,
                    crucible="markdown-links-resolve")


def injection_measure(repo, task, directory):
    """Inject the F-010 hollowed gate into the task's own base tree."""
    tree = base_tree(repo, task["base"], Path(directory) / "inject")
    probe = load_probe()
    if (tree / "ruff.toml").is_file() and re.search(
            RUFF_SELECT, (tree / "ruff.toml").read_text(encoding="utf-8")):
        return ruff_injection(tree, probe)
    return governance_injection(tree, probe)


def evaluate(repo, task):
    result = {"id": task["id"], "verdict": "PROBE_ERROR", "role": task["role"],
              "risk": task["risk"], "risk_basis": task.get("risk_basis", "ASSUMED")}
    try:
        with tempfile.TemporaryDirectory(prefix="h4-eligibility-") as directory:
            root = Path(directory) / "repo"
            subprocess.run(["git", "clone", "--shared", "--quiet", "--no-checkout",
                            str(repo), str(root)], check=True, capture_output=True)
            for field in ("base", "candidate"):
                result[field + "_resolved"] = git(root, "rev-parse", "--verify",
                                                   task[field] + "^{commit}")
            path = task["oracle"]
            if Path(path).is_absolute() or ".." in Path(path).parts:
                raise ValueError("invalid oracle path")
            if task.get("oracle_kind") == "freeze_v3":
                git(root, "checkout", "--quiet", "--detach", "HEAD")
                before, after = freeze_v3_measure(root, task, directory)
                result["base_accept"] = {key: before[key] for key in ("verdict", "reasons")}
                result["candidate_accept"] = {key: after[key] for key in ("verdict", "reasons")}
                oracle_ok = acceptance_transition(before, after)
                base_passing = any(reason.startswith("BASE_NOT_FAILING:")
                                   for reason in before["reasons"])
            else:
                blobs = [git(root, "rev-parse", rev + ":" + path)
                         for rev in (result["base_resolved"], result["candidate_resolved"])]
                if blobs[0] != blobs[1]:
                    raise ValueError("oracle must be frozen at both revisions")
                for field in ("base", "candidate"):
                    git(root, "checkout", "--quiet", "--detach", result[field + "_resolved"])
                    result[field + "_oracle_rc"] = run_oracle(root, path)
                oracle_ok = result["base_oracle_rc"] != 0 and result["candidate_oracle_rc"] == 0
                base_passing = result["base_oracle_rc"] == 0
            result["oracle_transition"] = "FAIL_TO_PASS" if oracle_ok else "NOT_TRANSITIONING"
            result["base_passing"] = base_passing
            result["injection"] = injection_measure(root, task, directory)
            injected_ok = result["injection"]["status"] == "DETECTED"
            reasons = []
            if task["role"] == "excluded":
                reasons.append("ROLE_EXCLUDED")
            if task["role"] == "outcome" and not oracle_ok:
                reasons.append("ORACLE_NOT_TRANSITIONING")
            if task["role"] == "false-green-control" and not base_passing:
                reasons.append("CONTROL_BASE_NOT_GREEN")
            if task["risk"] not in LOW_RISKS:
                reasons.append("RISK_ABOVE_LOW")
            if not injected_ok:
                reasons.append("INJECTION_" + result["injection"]["status"])
            result["ineligible_reasons"] = reasons
            if task["role"] == "outcome" and not reasons:
                result["verdict"] = "ELIGIBLE"
            elif task["role"] == "false-green-control" and not reasons:
                result["verdict"] = "CONTROL"
            else:
                result["verdict"] = "INELIGIBLE"
    except Exception as exc:
        result["error"] = str(exc)
    return result


def funnel(results):
    """Exclusive buckets: each examined row is charged to the first step it fails."""
    candidates = [item for item in results if item.get("role") != "excluded"]

    def first(reason):
        return sum((item.get("ineligible_reasons") or [None])[0] == reason
                   for item in candidates)

    def first_prefix(prefix):
        return sum((item.get("ineligible_reasons") or [""])[0].startswith(prefix)
                   for item in candidates)

    return {"examined": len(results),
            "not_a_candidate": len(results) - len(candidates),
            "excluded_at_oracle": (first("ORACLE_NOT_TRANSITIONING")
                                   + first("CONTROL_BASE_NOT_GREEN")),
            "excluded_at_risk": first("RISK_ABOVE_LOW"),
            "excluded_at_injection": first_prefix("INJECTION_"),
            "probe_error": sum(item["verdict"] == "PROBE_ERROR" for item in results),
            "eligible_outcomes": sum(item["verdict"] == "ELIGIBLE" for item in results),
            "qualifying_controls": sum(item["verdict"] == "CONTROL" for item in results)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--tasks", type=Path, default=Path(__file__).with_name("task-candidates.json"))
    args = parser.parse_args()
    try:
        tasks = json.loads(args.tasks.read_text(encoding="utf-8"))["tasks"]
        results = [evaluate(args.repo.resolve(), task) for task in tasks]
        steps = funnel(results)
        meets = (steps["eligible_outcomes"] + steps["qualifying_controls"] >= 4
                 and steps["qualifying_controls"] >= 1)
        print(json.dumps({"source_sha": git(args.repo.resolve(), "rev-parse", "HEAD"),
                          "measurement_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                          "candidates_sha256": hashlib.sha256(args.tasks.read_bytes()).hexdigest(),
                          "eligible_count": steps["eligible_outcomes"],
                          "false_green_control_count": steps["qualifying_controls"],
                          "task_count_gate": "MET" if meets else "PROTOCOL_NOT_STARTABLE",
                          "funnel": steps, "tasks": results}, indent=2))
        return int(any(item["verdict"] == "PROBE_ERROR" for item in results))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"verdict": "PROBE_ERROR", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
