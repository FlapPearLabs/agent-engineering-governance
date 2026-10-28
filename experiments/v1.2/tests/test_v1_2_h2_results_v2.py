"""Tests for the read-only H2 results export and report."""
import hashlib
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parents[1] / "h2-lazy-disclosure"


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / "results-v2" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


exporter = load("export_results")
renderer = load("render_closure")


class ResultsTest(unittest.TestCase):
    def test_export_and_tamper(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "runs"
            root.mkdir()
            run = root / "h2r2-f01-c"
            (run / "audit").mkdir(parents=True)
            (run / "repo").mkdir()
            (run / "repo" / "source").write_text("first")
            os.mkfifo(run / "repo" / "pipe")
            (run / "repo" / "dangling").symlink_to("missing")
            driver = root / ".driver" / run.name
            (driver / "home-worker").mkdir(parents=True)
            (driver / "home-worker" / "file").write_text("home")
            (driver / "events.jsonl").write_text('{}\n')
            example_home = "/" + "Users" + "/" + "example"
            untouched = 'quote " slash \\ newline\n unicode\u2028\u2029 /nope /etc/hosts /dev/null'
            files = {"verdict.json": json.dumps({"verdict": "ACCEPT", "reasons": [untouched]}),
                     "audit/audit.json": json.dumps({"correctness": "PASS", "invalid_completion": False,
                         "findings": [{"id": "F1", "severity": "P2", "category": "TEST",
                                       "location": example_home + "/private", "evidence": "SECRET_PROSE"}]}),
                     "report.md": "TASK_COMPLETED = YES\nSECRET_PROSE\n",
                     "run.json": json.dumps({"root": str(root), "prose": "SECRET_PROSE"}),
                     "access-audit.json": json.dumps({"verdict": "PASS", "hits": [],
                                                       "denied_attempts": []})}
            for name, value in files.items():
                (run / name).write_text(value)
            artifacts = {name: hashlib.sha256(value.encode()).hexdigest()
                         for name, value in files.items()}
            os.mkfifo(run / "registered-pipe")
            artifacts["registered-pipe"] = hashlib.sha256(b"").hexdigest()
            row = {"run_id": run.name, "task_id": "f01", "arm": "control",
                   "verdict": "ACCEPT", "final_verdict": "ACCEPT", "artifacts": artifacts}
            (root / "registry-v2.jsonl").write_text(json.dumps(row) + "\n")
            for name in exporter.LEDGERS[1:]:
                (root / name).write_text("")
            (root / "trace.log").write_text("evidence")
            out = Path(temp) / "out"
            exporter.export(root, out)
            for path in out.iterdir():
                content = path.read_text()
                self.assertNotIn("SECRET_PROSE", content)
                self.assertNotIn(example_home, content)
                if path.suffix == ".json":
                    json.loads(content)
                elif path.suffix == ".jsonl":
                    for line in content.split("\n"):
                        if line:
                            json.loads(line)
            saved = json.loads((out / f"{run.name}.json").read_text())
            self.assertIn({"path": "registered-pipe", "type": "fifo",
                           "registered_sha256": hashlib.sha256(b"").hexdigest(),
                           "verification": "NOT_REVERIFIED_SPECIAL_FILE"},
                          saved["artifact_verification"])
            self.assertEqual(saved["reason_codes"], [])
            self.assertEqual(saved["mechanical"]["reasons"][0], untouched)
            self.assertEqual(saved["auditor"]["findings"][0]["id"], "F1")
            manifest = json.loads((out / "raw-manifest.json").read_text())
            paths = {item["path"] for item in manifest["files"]}
            self.assertTrue({"trace.log", f"{run.name}/audit/audit.json",
                             f".driver/{run.name}/events.jsonl"} <= paths)
            trees = {item["subtree"]: item for item in manifest["subtrees"]}
            self.assertEqual(trees[f"{run.name}/repo"]["files"], 3)
            old = trees[f"{run.name}/repo"]["sha256"]
            (run / "repo" / "source").write_text("second")
            exporter.export(root, Path(temp) / "out2")
            changed = json.loads((Path(temp) / "out2" / "raw-manifest.json").read_text())
            trees2 = {item["subtree"]: item for item in changed["subtrees"]}
            self.assertNotEqual(old, trees2[f"{run.name}/repo"]["sha256"])
            (run / "audit/audit.json").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "SHA256_MISMATCH"):
                exporter.export(root, Path(temp) / "bad")

    def test_report_omits_commands_and_entities(self):
        command = "worker-secret-command && echo dangerous"
        data = {"rows": [{"run_id": "run", "task_id": "f01", "arm": "control",
                          "reason": "OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN:" + command,
                          "attempts": [{"attempt": 1, "kind": "TERMINAL", "reason": command}]}],
                "pairs": [], "usable_pairs": 0, "planned_pairs": 1,
                "decided_by": "COVERAGE", "result": "INSUFFICIENT_EVIDENCE",
                "denied_attempts": {"by_arm": {"control": {"count": 0}, "variant": {"count": 0}}}}
        records = {"run": {"reason_codes": ["OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN"],
                           "access_audit": {"hits": [{"path": "/nope", "value": command}]}}}
        report = renderer.render(data, records)
        self.assertNotIn(command, report)
        self.assertNotIn("&#", report)
        self.assertIn("OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN; /nope", report)
        self.assertEqual(exporter.reason_codes("WORKER_SCOPE_DENIED:a;WORKER_SCOPE_DENIED:b"),
                         ["WORKER_SCOPE_DENIED", "WORKER_SCOPE_DENIED"])

    def test_all_tokens_and_numbers(self):
        data = {"rows": [], "pairs": [{"task_id": "f01", "valid": True}],
                "usable_pairs": 1, "planned_pairs": 10, "decided_by": "TEST",
                "denied_attempts": {"by_arm": {"control": {"count": 3},
                                               "variant": {"count": 7}}}}
        for token in ("DISCLOSURE_SAFE", "DISCLOSURE_HAS_COST", "INSUFFICIENT_EVIDENCE",
                      "SAFE_CANDIDATE_PENDING:S2,S5"):
            data["result"] = token
            report = renderer.render(data)
            self.assertIn(token, report)
            self.assertIn("1/10", report)
            self.assertIn("control 被拒绝尝试总数：3", report)
            self.assertIn("variant 被拒绝尝试总数：7", report)
            self.assertEqual("## 待人工判断" in report, token.startswith("SAFE_CANDIDATE"))


if __name__ == "__main__":
    unittest.main()
