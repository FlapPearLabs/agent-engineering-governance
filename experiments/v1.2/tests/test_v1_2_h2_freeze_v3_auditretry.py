"""T51c: the v3 audit retry entry — `audit` appends an `AUDIT_RESOLVED` over a registration.

Every test here uses a stub worker, a stub auditor and a stub sandbox: no model, no network call,
and never a real runs root. The in-run audit is compared against the fields the registration
produced before the retry entry existed, because refactoring the audit attempt must not change what
a normal run registers.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
H2 = ROOT / "experiments/v1.2/h2-lazy-disclosure"
FZ = H2 / "freeze-v3"
RUN_ID = "h2r3-f01-c"
BLOCKED_AUDIT = ("PROVIDER_UNREACHABLE:EXIT:1",)

# The fields a run's own registry line has (`register`). An AUDIT_RESOLVED line is a different
# record; a normal run must keep registering exactly these.
IN_RUN_FIELDS = {"run_id", "task_id", "arm", "verdict", "audit_verdict", "final_verdict",
                 "reason", "session_id", "wall_clock_seconds", "started_at", "finished_at",
                 "artifacts", "attempt", "attempts", "denied_attempts"}

STUB_SERVER = '''"""Test-only loopback server: it only has to answer on its port (F26 / T36b)."""
import socket
import sys
import time

port = int(sys.argv[-1])
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("127.0.0.1", port))
server.listen(8)
server.settimeout(1.0)
deadline = time.time() + 60
while time.time() < deadline:
    try:
        conn, _ = server.accept()
    except OSError:
        continue
    conn.close()
'''

STUB_WORKER = '''"""Test-only worker: leaves the artefacts a run needs, never a model call."""
import json
import sys

open("report.md", "w").write("# report\\n\\nstub worker\\n")
open(".h2-telemetry.log", "w").write("READ FULL repo/RULES.md\\n")
print(json.dumps({"type": "text", "sessionID": "ses_stub", "part": {"text": "stub done"}}))
sys.exit(0)
'''


def load(name):
    # The same isolation the v3 suite uses: never let a v2 module answer for a v3 one.
    v2 = (H2 / "freeze-v2").resolve()
    for key, module in list(sys.modules.items()):
        source = getattr(module, "__file__", None)
        if source and Path(source).resolve().is_relative_to(v2):
            del sys.modules[key]
    if str(FZ) in sys.path:
        sys.path.remove(str(FZ))
    sys.path.insert(0, str(FZ))
    spec = importlib.util.spec_from_file_location(name, FZ / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class StubSandbox:
    """A stand-in for the OS sandbox: the driver's steps run, the barrier does not."""

    def available(self):
        return True

    def plant(self, driver_dir):
        path = Path(driver_dir) / "confinement-plant-stub.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stub-plant\n", encoding="utf-8")
        return path, "stub-plant"

    def profile(self, stream_dir, launch, home, python=None, *, proxy_port, serve_port):
        path = Path(stream_dir) / "worker.sb"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("(stub sandbox)\n", encoding="utf-8")
        return {"path": str(path), "sha256": digest(b"(stub sandbox)\n"), "template": "stub",
                "template_sha256": digest(b"stub"), "launch": str(launch), "home": str(home),
                "interpreter": str(python or sys.executable), "deny_roots": [],
                "proxy_port": int(proxy_port), "serve_port": int(serve_port)}

    def confine(self, profile_path, argv):
        return [str(item) for item in argv]

    def self_test(self, profile_path, launch, planted, python=None, token=None, *,
                  proxy_port, serve_port):
        return {"verdict": "PASS", "reasons": [],
                "profile_sha256": digest(Path(profile_path).read_bytes()),
                "proxy_port": int(proxy_port), "serve_port": int(serve_port)}


class StubAuth:
    """Test-only credential hand-off: never a real credential."""

    def import_(self, master_env, env, cwd):
        return {"ok": True, "export_returncode": 0, "import_returncode": 0, "bytes": 0}

    def logout(self, env, cwd):
        return {"ran": True, "returncode": 0}


def profile_env_file(directory):
    path = Path(directory) / "profile-env.sh"
    path.write_text(f"export PATH={os.environ.get('PATH', '/usr/bin:/bin')}\nexport LANG=C\n",
                    encoding="utf-8")
    return path


def stub_server_command(directory):
    path = Path(directory) / "stub-server.py"
    path.write_text(STUB_SERVER, encoding="utf-8")
    return (sys.executable, str(path))


def stub_worker_command(directory):
    path = Path(directory) / "stub-worker.py"
    path.write_text(STUB_WORKER, encoding="utf-8")
    return (sys.executable, str(path))


def passing_preflight(run_dir, env_file, **kwargs):
    return {"verdict": "PASS", "reasons": []}


def passing_probe(purpose, attempt):
    """A reachability check that passes; never a model, never a network call (F14)."""
    return {"verdict": "PASS", "reasons": [], "seconds": 0.01, "events": 2, "token_seen": True,
            "purpose": purpose, "attempt": attempt}


def stub_auditor(verdict="PASS", reasons=(),
                 findings=(), invalid_completion=False):
    """A stub auditor: it records what it was given and writes no model output."""
    def audit(run_dir, plan_run, task, *, launch, command, env, limit_seconds,
              events_path=None, stderr_path=None, **kwargs):
        if verdict == "PASS":
            bundle = Path(kwargs.get("bundle_dir") or (Path(run_dir) / "audit"))
            bundle.mkdir(parents=True, exist_ok=True)
            (bundle / "audit.json").write_text(json.dumps(
                {"correctness": verdict, "invalid_completion": invalid_completion,
                 "findings": list(findings)}), encoding="utf-8")
        return {"verdict": verdict,
                "correctness": verdict if verdict != "BLOCKED" else None,
                "findings": list(findings), "invalid_completion": invalid_completion,
                "leakage": [], "reasons": list(reasons)}
    return audit


def tree_digest(root: Path) -> dict:
    """Every path under `root` with its content hash, for a before/after comparison."""
    root = Path(root)
    found = {}
    for directory, dirnames, filenames in os.walk(root):
        current = Path(directory)
        for name in sorted(dirnames):
            found[(current / name).relative_to(root).as_posix()] = "dir"
        for name in sorted(filenames):
            path = current / name
            found[path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return found


class AuditRetry(unittest.TestCase):
    """T51c: one fresh audit over a run whose audit the harness blocked."""

    def setUp(self):
        self.driver = load("run_h2r2")
        self.aggregate = load("aggregate_runs")
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.tmp = Path(self.temp.name)
        self.runs = self.tmp / "runs"

    # -- fixtures ---------------------------------------------------------------------------
    def execute(self, auditor):
        """One stubbed run: stub worker, stub auditor, stub sandbox, and a stubbed acceptance.

        The frozen acceptance gate (its own real sandbox self-test and the task oracle) is not what
        T51c decides; the mechanical verdict is fixed here so the audit half is the only variable.
        """
        accepted = {"verdict": "ACCEPT", "reasons": [], "gates": [], "oracle": {}}
        with mock.patch.object(self.driver.run_acceptance_v2, "accept",
                               return_value=accepted):
            return self.driver.execute(
                RUN_ID, self.runs, worker_command=stub_worker_command(self.tmp),
                server_command=stub_server_command(self.tmp), preflight=passing_preflight,
                auditor=auditor, profile_env=profile_env_file(self.tmp), probe=passing_probe,
                sandbox=StubSandbox(), auth=StubAuth())

    def blocked_run(self):
        """A real (stubbed) run, registered BLOCKED because its own audit was blocked."""
        result = self.execute(stub_auditor("BLOCKED", BLOCKED_AUDIT))
        self.assertEqual("EXECUTED", result["outcome"], result)
        self.assertEqual("BLOCKED", result["final_verdict"], result)
        # The `run` invocation is over, so its lock is no longer held by a live process; in this
        # process it would still read as live, so the fixture ends it the way a finished run does.
        self.driver.lock_path(self.runs, RUN_ID).unlink(missing_ok=True)
        return result

    def registry_bytes(self) -> bytes:
        return (self.runs / self.driver.REGISTRY_NAME).read_bytes()

    def registry_rows(self) -> list[dict]:
        return [json.loads(line) for line in self.registry_bytes().decode("utf-8").split("\n")
                if line.strip()]

    def write_registry(self, *rows) -> None:
        self.runs.mkdir(parents=True, exist_ok=True)
        (self.runs / self.driver.REGISTRY_NAME).write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")

    def retry(self, auditor, **kwargs):
        result = self.driver.audit_retry(
            RUN_ID, self.runs, auditor=auditor, probe=passing_probe, sandbox=StubSandbox(),
            auth=StubAuth(), server_command=stub_server_command(self.tmp),
            profile_env=profile_env_file(self.tmp), **kwargs)
        # In production every retry is its own process; this test process keeps living, so it ends
        # the invocation the way process exit does.
        self.driver.lock_path(self.runs, RUN_ID).unlink(missing_ok=True)
        return result

    # -- the in-run path is unchanged -------------------------------------------------------
    def test_the_in_run_audit_still_registers_the_same_fields(self):
        self.blocked_run()
        lines = self.registry_bytes().decode("utf-8").split("\n")
        self.assertEqual(1, len([line for line in lines if line.strip()]))
        line = json.loads(lines[0])
        self.assertEqual(IN_RUN_FIELDS, set(line))
        self.assertIn(line["verdict"], ("ACCEPT", "REJECT"))
        self.assertEqual(("BLOCKED", "BLOCKED"), (line["audit_verdict"], line["final_verdict"]))
        self.assertTrue(line["reason"].endswith("AUDIT_BLOCKED:PROVIDER_UNREACHABLE:EXIT:1"),
                        line["reason"])
        self.assertEqual((1, 1), (line["attempt"], line["attempts"]))
        self.assertNotIn("audit_retry", line)
        self.assertNotIn("kind", line)

    # -- refusals ---------------------------------------------------------------------------
    def test_a_run_that_is_not_blocked_is_refused(self):
        self.write_registry({"run_id": RUN_ID, "verdict": "ACCEPT", "audit_verdict": "PASS",
                             "final_verdict": "ACCEPT"})
        with self.assertRaisesRegex(ValueError, "AUDIT_RETRY_NOT_BLOCKED:ACCEPT"):
            self.retry(stub_auditor("PASS"))
        self.assertEqual(1, len(self.registry_rows()))

    def test_a_blocked_run_with_a_non_audit_reason_is_refused(self):
        self.write_registry({"run_id": RUN_ID, "verdict": "BLOCKED", "audit_verdict": None,
                             "final_verdict": "BLOCKED", "reason": "ATTEMPTS_EXHAUSTED"})
        with self.assertRaisesRegex(ValueError, "AUDIT_RETRY_NOT_AUDIT_BLOCKED"):
            self.retry(stub_auditor("PASS"))
        self.write_registry({"run_id": RUN_ID, "verdict": "ACCEPT", "final_verdict": "BLOCKED",
                             "reason": "AUDIT_BLOCKED:A;OUT_OF_RUN_ACCESS:TOOL_NOT_ALLOWED"})
        with self.assertRaisesRegex(ValueError, "AUDIT_RETRY_NOT_AUDIT_BLOCKED"):
            self.retry(stub_auditor("PASS"))

    def test_an_unregistered_run_is_refused(self):
        with self.assertRaisesRegex(ValueError, f"AUDIT_RETRY_NOT_REGISTERED:{RUN_ID}"):
            self.retry(stub_auditor("PASS"))

    def test_the_three_retries_are_a_hard_budget(self):
        self.blocked_run()
        rows = self.registry_rows()
        for number in (1, 2, 3):
            rows.append({"kind": "AUDIT_RESOLVED", "run_id": RUN_ID, "audit_retry": number,
                         "verdict": "BLOCKED",
                         "audit": {"verdict": "BLOCKED", "reasons": ["PROVIDER_UNREACHABLE"]},
                         "resolved_at": "2026-10-28T00:00:00+00:00"})
        self.write_registry(*rows)
        with self.assertRaisesRegex(ValueError, "AUDIT_RETRY_EXHAUSTED:3"):
            self.retry(stub_auditor("PASS"))

    # -- the resolution ---------------------------------------------------------------------
    def test_the_retry_appends_one_line_and_keeps_the_earlier_bytes(self):
        self.blocked_run()
        before = self.registry_bytes()
        run_dir = self.driver.wrapper_delivery.run_dir_for(self.runs, RUN_ID)
        run_before = tree_digest(run_dir)
        result = self.retry(stub_auditor("PASS"))
        after = self.registry_bytes()
        self.assertTrue(after.startswith(before))
        self.assertEqual(1, after[len(before):].decode("utf-8").count("\n"))
        line = self.registry_rows()[-1]
        self.assertEqual({"kind", "run_id", "task_id", "arm", "audit_retry", "verdict",
                          "mechanical_verdict", "audit_verdict", "audit", "snapshot",
                          "retry_dir", "probe", "audit_sandbox", "resolved_at"}, set(line))
        self.assertEqual(("AUDIT_RESOLVED", 1), (line["kind"], line["audit_retry"]))
        self.assertEqual("PASS", line["audit"]["correctness"])
        self.assertEqual("ACCEPT", line["mechanical_verdict"])
        self.assertEqual("ACCEPT", (line["verdict"]))
        self.assertEqual("ACCEPT", result["verdict"])
        self.assertEqual(run_before, tree_digest(run_dir))
        retry_dir = Path(line["retry_dir"])
        self.assertEqual(self.driver.wrapper_delivery.driver_root(run_dir) / "audit-retry-1",
                         retry_dir)
        self.assertTrue((retry_dir / "audit" / "audit.json").is_file())

    def test_a_blocked_retry_is_appended_as_blocked(self):
        self.blocked_run()
        result = self.retry(stub_auditor("BLOCKED", ["PROVIDER_UNREACHABLE:NO_ANSWER"]))
        line = self.registry_rows()[-1]
        self.assertEqual(("BLOCKED", "BLOCKED"), (line["verdict"], line["audit"]["verdict"]))
        self.assertEqual("BLOCKED", result["verdict"])
        self.assertEqual(["PROVIDER_UNREACHABLE:NO_ANSWER"], result["reasons"])
        entry = self.aggregate.read_registry(self.runs)[RUN_ID]
        self.assertEqual(("BLOCKED", 1), (entry["final_verdict"], entry["audit_retry"]))
        self.assertEqual("AUDIT_BLOCKED:PROVIDER_UNREACHABLE:NO_ANSWER", entry["reason"])

    def test_the_aggregate_uses_the_latest_resolution(self):
        self.blocked_run()
        self.retry(stub_auditor("BLOCKED", ["PROVIDER_UNREACHABLE:NO_ANSWER"]))
        self.retry(stub_auditor("PASS"))
        entry = self.aggregate.read_registry(self.runs)[RUN_ID]
        self.assertEqual(2, entry["audit_retry"])
        self.assertEqual("PASS", entry["audit"]["correctness"])
        self.assertEqual("ACCEPT", entry["verdict"])
        self.assertEqual("ACCEPT", entry["final_verdict"])
        self.assertIsNone(entry["reason"])
        row = next(item for item in self.aggregate.aggregate(self.runs)["rows"]
                   if item["run_id"] == RUN_ID)
        self.assertEqual(2, row["audit_retry"])
        self.assertEqual("PASS", row["audited_correctness"])

    def test_the_bundle_can_be_built_outside_the_run_dir(self):
        auditor = load("run_audit_v2")
        self.blocked_run()
        run_dir = self.driver.wrapper_delivery.run_dir_for(self.runs, RUN_ID)
        plan_run = next(run for run in self.driver.plan_runs(ROOT) if run["run_id"] == RUN_ID)
        bundle_dir = self.tmp / "bundle"
        before = self.registry_bytes()
        driver_dir = self.driver.wrapper_delivery.driver_root(run_dir)
        bundle = auditor.prepare_bundle(
            run_dir, plan_run, self.driver.task_of(ROOT, plan_run["task_id"]),
            contract_path=driver_dir / "CONTRACT.md",
            report_path=run_dir / "report.md", bundle_dir=bundle_dir)
        self.assertEqual(str(bundle_dir), bundle["audit_dir"])
        self.assertEqual({"CONTRACT.md", "diff.patch", "verdict.json", "report.md",
                          "audit-request.json"},
                         {path.name for path in bundle_dir.iterdir()})
        self.assertFalse((run_dir / "audit" / "audit.json").exists())
        self.assertEqual(before, self.registry_bytes())

    def test_the_cli_refuses_and_exits_non_zero(self):
        import subprocess
        self.runs.mkdir(parents=True, exist_ok=True)
        finished = subprocess.run(
            [sys.executable, str(FZ / "run_h2r2.py"), "audit", RUN_ID,
             "--runs-root", str(self.runs)],
            capture_output=True, text=True, cwd=str(self.tmp))
        self.assertEqual(1, finished.returncode)
        self.assertIn("AUDIT_RETRY_NOT_REGISTERED", finished.stderr)


if __name__ == "__main__":
    unittest.main()
