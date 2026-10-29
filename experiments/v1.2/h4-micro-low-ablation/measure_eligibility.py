#!/usr/bin/env python3
"""Measure frozen historical acceptances and N7 in disposable clones."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
ADMISSION = ROOT / "experiments/v1.2/h2-lazy-disclosure/admission"
sys.path.insert(0, str(ADMISSION))
import measure  # noqa: E402


def load_probe():
    path = ROOT / "experiments/v1.2/gate-load-bearing/probe_gates.py"
    spec = importlib.util.spec_from_file_location("n7_probe", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


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


def evaluate(repo, task):
    result = {"id": task["id"], "verdict": "PROBE_ERROR"}
    try:
        with tempfile.TemporaryDirectory(prefix="h4-eligibility-") as directory:
            root = Path(directory) / "repo"
            subprocess.run(["git", "clone", "--no-hardlinks", "--quiet", "--no-checkout",
                            str(repo), str(root)], check=True, capture_output=True)
            for field in ("base", "candidate"):
                result[field + "_resolved"] = git(root, "rev-parse", "--verify",
                                                   task[field] + "^{commit}")
            path = task["oracle"]
            if Path(path).is_absolute() or ".." in Path(path).parts:
                raise ValueError("invalid oracle path")
            blobs = [git(root, "rev-parse", rev + ":" + path)
                     for rev in (result["base_resolved"], result["candidate_resolved"])]
            if blobs[0] != blobs[1]:
                raise ValueError("oracle must be frozen at both revisions")
            for field in ("base", "candidate"):
                git(root, "checkout", "--quiet", "--detach", result[field + "_resolved"])
                result[field + "_oracle_rc"] = run_oracle(root, path)
            oracle_ok = result["base_oracle_rc"] != 0 and result["candidate_oracle_rc"] == 0
            config = root / "ruff.toml"
            if not config.is_file():
                raise ValueError("candidate has no ruff.toml")
            original = config.read_text(encoding="utf-8")
            changed, count = re.subn(r'(?m)^select\s*=\s*\["E9",\s*"F"\]\s*$',
                                     'select = []', original)
            if count != 1:
                raise ValueError("candidate has no unique E9,F ruff predicate")
            probe = load_probe()
            control = root / "scripts/n7_control.py"
            if control.exists():
                raise ValueError("control already exists")
            control.write_text("def example():\n    unused = 1\n", encoding="utf-8")
            before = probe.run("python3 -m ruff check scripts/n7_control.py", root)
            result["ruff_before_rc"] = before.returncode
            result["ruff_before_output"] = before.stdout.strip()
            if before.returncode not in (0, 1):
                raise ValueError("ruff positive control execution failed")
            control.unlink()
            config.write_text(changed, encoding="utf-8")
            control.write_text("def example():\n    unused = 1\n", encoding="utf-8")
            after = probe.run("python3 -m ruff check scripts/n7_control.py", root)
            result["ruff_after_rc"] = after.returncode
            result["ruff_after_output"] = after.stdout.strip()
            control.unlink()
            if after.returncode not in (0, 1):
                raise ValueError("hollowed ruff control execution failed")
            manifest = json.loads((ROOT / "experiments/v1.2/gate-load-bearing/gates.json").read_text())
            gate = next(gate for gate in manifest["gates"] if gate["id"] == "ruff")
            observed = probe.probe_tree(root, {"gates": [gate]})[0]
            result["n7"] = observed
            if observed["status"] in ("PROBE_ERROR", "BASELINE_FAILING"):
                raise ValueError("N7 could not measure the injected gate")
            result["verdict"] = ("ELIGIBLE" if task["role"] == "outcome" and oracle_ok
                                 and task["risk"] in ("MICRO", "LOW")
                                 and before.returncode == 1 and "F841" in before.stdout
                                 and after.returncode == 0
                                 and observed["status"] == "GATE_NOT_LOAD_BEARING"
                                 else "INELIGIBLE")
    except Exception as exc:
        result["error"] = str(exc)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--tasks", type=Path, default=Path(__file__).with_name("task-candidates.json"))
    args = parser.parse_args()
    try:
        tasks = json.loads(args.tasks.read_text(encoding="utf-8"))["tasks"]
        results = [evaluate(args.repo.resolve(), task) for task in tasks]
        count = sum(item["verdict"] == "ELIGIBLE" for item in results)
        print(json.dumps({"eligible_count": count, "task_count_gate":
                          "PASS" if count >= 4 else "PROTOCOL_NOT_STARTABLE",
                          "tasks": results}, indent=2))
        return int(any(item["verdict"] == "PROBE_ERROR" for item in results))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"verdict": "PROBE_ERROR", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
