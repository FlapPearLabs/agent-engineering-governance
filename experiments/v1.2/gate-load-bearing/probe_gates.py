#!/usr/bin/env python3
"""Experimental, fail-closed positive controls; never alter the source checkout."""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(command, root):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PUBLIC_RELEASE": "1"})
    args = shlex.split(command)
    if args[0] == "python3":
        args[0] = sys.executable
    return subprocess.run(args, cwd=root, env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def scratch(repo, ref, root, worktree=False):
    subprocess.run(["git", "clone", "--no-hardlinks", "--quiet", "--no-checkout",
                    str(repo), str(root)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "-C", str(root), "checkout", "--quiet", "--detach", ref],
                   check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if worktree:
        names = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-co",
                                         "--exclude-standard", "-z"]).split(b"\0")
        for name in names:
            if not name:
                continue
            rel = Path(os.fsdecode(name))
            source, target = repo / rel, root / rel
            if not source.exists() and not source.is_symlink():
                target.unlink(missing_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.unlink(missing_ok=True)
            if source.is_symlink():
                target.symlink_to(os.readlink(source))
            else:
                shutil.copy2(source, target)


def commit_control(root, control):
    if control["kind"] == "history":
        path = root / control["path"]
        if path.exists():
            raise ValueError("control target already exists")
        # A fabricated match for PASSWORD_ASSIGNMENT, never a real credential.
        path.write_text("pass" + "word=" + "N7" * 12 + "\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", control["path"]], check=True)
    identity = "N7 Synthetic" if control["kind"] == "metadata" else "FlapPearLabs"
    email = "n7@example.invalid" if control["kind"] == "metadata" else "151931662+FlapPearLabs@users.noreply.github.com"
    subprocess.run(["git", "-C", str(root), "-c", "user.name=" + identity,
                    "-c", "user.email=" + email, "commit", "--allow-empty", "-q",
                    "-m", "synthetic control"], check=True)


def inject(root, control):
    path = root / control["path"]
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("control path escapes scratch")
    kind = control["kind"]
    if kind == "file":
        if path.exists():
            raise ValueError("control target already exists")
        path.write_text(control["content"], encoding="utf-8")
    elif kind == "append":
        with path.open("a", encoding="utf-8") as stream:
            stream.write(control["content"])
    elif kind == "delete":
        path.unlink()
    elif kind == "replace":
        text = path.read_text(encoding="utf-8")
        before = control["before"]
        if not before or text.count(before) != 1:
            raise ValueError("control replacement is not unique")
        path.write_text(text.replace(before, control["after"]), encoding="utf-8")
    else:
        raise ValueError("unknown control")


def rules(root, filename, isolated=False):
    command = "python3 -m ruff check --show-settings "
    if isolated:
        command += "--isolated --select E9,F "
    result = run(command + shlex.quote(filename), root)
    match = re.search(r"linter\.rules\.enabled = \[(.*?)\]", result.stdout, re.S)
    if result.returncode or not match:
        raise ValueError("cannot resolve ruff rules")
    return set(re.findall(r"\(([A-Z]+\d+)\)", match.group(1)))


def probe_tree(root, manifest):
    gates = manifest["gates"]
    if not gates or len({gate["id"] for gate in gates}) != len(gates):
        raise ValueError("empty or duplicate gates")
    workflows = "\n".join(path.read_text(encoding="utf-8") for path in
                          (root / ".github/workflows").glob("*.yml"))
    results = []
    for gate in gates:
        result = {"id": gate.get("id"), "status": "PROBE_ERROR"}
        try:
            if not gate.get("command") or not gate.get("intent"):
                raise ValueError("missing command or intent")
            if "run: " + gate["command"] not in workflows:
                raise ValueError("declared CI command not found")
            control = gate.get("control")
            if control is None:
                if not gate.get("reason"):
                    raise ValueError("missing positive control")
                result.update(status="NO_POSITIVE_CONTROL", detail=gate["reason"])
                results.append(result)
                continue
            baseline = run(gate["command"], root)
            if baseline.returncode:
                result.update(status="BASELINE_FAILING", detail=baseline.stdout)
                results.append(result)
                continue
            path = root / control["path"]
            original = path.read_bytes() if path.exists() else None
            try:
                if control["kind"] in ("metadata", "history"):
                    commit_control(root, control)
                else:
                    inject(root, control)
                observed = run(gate["command"], root)
                if gate["id"] == "ruff" and rules(root, control["path"]) != rules(root, control["path"], True):
                    result.update(status="GATE_NOT_LOAD_BEARING", detail="effective rules differ from E9,F")
                elif observed.returncode == 0:
                    result.update(status="GATE_NOT_LOAD_BEARING", detail=observed.stdout)
                elif observed.returncode == 1 and control["signal"] in observed.stdout:
                    result.update(status="LOAD_BEARING", detail=control["signal"])
                else:
                    result.update(detail="unexpected failure: " + observed.stdout)
            finally:
                if control["kind"] == "metadata":
                    subprocess.run(["git", "-C", str(root), "reset", "--soft", "HEAD^"], check=True)
                elif control["kind"] != "history":
                    if original is None:
                        path.unlink(missing_ok=True)
                    else:
                        path.write_bytes(original)
        except (KeyError, OSError, ValueError, subprocess.SubprocessError) as exc:
            result["detail"] = str(exc)
        results.append(result)
    return results


def exit_status(results, strict=False):
    failures = {"GATE_NOT_LOAD_BEARING", "BASELINE_FAILING", "PROBE_ERROR"}
    if strict:
        failures.add("NO_POSITIVE_CONTROL")
    return int(any(item["status"] in failures for item in results))


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--ref")
    group.add_argument("--worktree", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--repo", default=".")
    args = parser.parse_args()
    try:
        with tempfile.TemporaryDirectory(prefix="n7-probe-") as directory:
            root = Path(directory)
            scratch(Path(args.repo).resolve(), args.ref or "HEAD", root, args.worktree)
            manifest = json.loads((root / "experiments/v1.2/gate-load-bearing/gates.json").read_text())
            results = probe_tree(root, manifest)
        missing = [item["id"] for item in results if item["status"] == "NO_POSITIVE_CONTROL"]
        print(json.dumps({"ref": args.ref, "worktree": args.worktree, "gates": results,
                          "no_positive_control": missing}, indent=2))
        return exit_status(results, args.strict)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "PROBE_ERROR", "detail": str(exc)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
