"""Tests for the read-only H2 results export and report."""
import hashlib
import importlib.util
import json
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
            example_home = "/" + "Users" + "/" + "example"
            files = {"verdict.json": json.dumps({"path": example_home + "/private"}),
                     "audit/audit.json": json.dumps({"correctness": "PASS",
                                                     "invalid_completion": False, "findings": []}),
                     "report.md": "TASK_COMPLETED = YES\n",
                     "run.json": f'{{"root":"{root}"}}',
                     "access-audit.json": '{"denied_attempts": []}'}
            for name, value in files.items():
                (run / name).write_text(value)
            artifacts = {name: hashlib.sha256(value.encode()).hexdigest()
                         for name, value in files.items()}
            row = {"run_id": run.name, "task_id": "f01", "arm": "control",
                   "verdict": "ACCEPT", "final_verdict": "ACCEPT", "artifacts": artifacts}
            (root / "registry-v2.jsonl").write_text(json.dumps(row) + "\n")
            out = Path(temp) / "out"
            exporter.export(root, out)
            self.assertNotIn(example_home, (out / run.name / "verdict.json").read_text())
            self.assertNotIn(str(root), (out / "aggregate.json").read_text())
            hashes = json.loads((out / "hashes.json").read_text())
            self.assertEqual(hashes[f"{run.name}/run.json"]["original_sha256"], artifacts["run.json"])
            (run / "audit/audit.json").write_text("tampered")
            with self.assertRaisesRegex(ValueError, "SHA256_MISMATCH"):
                exporter.export(root, Path(temp) / "bad")

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
