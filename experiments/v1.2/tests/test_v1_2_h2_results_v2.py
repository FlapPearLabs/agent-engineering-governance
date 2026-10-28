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

    def test_summary_counts_match_export(self):
        export = HERE / "results-v2" / "r2-4aa2e7b"
        data = json.loads((export / "aggregate.json").read_text(encoding="utf-8"))
        report = renderer.render(data, {})
        complete = [pair for pair in data["pairs"] if pair["valid"]]
        total = len(complete)
        same_correctness = sum(pair["control"]["final_correctness"]
                               == pair["variant"]["final_correctness"] for pair in complete)
        same_invalid = sum(bool(pair["control"].get("invalid_completion"))
                           == bool(pair["variant"].get("invalid_completion")) for pair in complete)
        same_shape = sum(renderer.finding_shape(pair["control"])
                         == renderer.finding_shape(pair["variant"]) for pair in complete)
        self.assertGreater(total, 0)
        self.assertIn(f"FINAL_CORRECTNESS 相同：{same_correctness}/{total} 对", report)
        self.assertIn(f"invalid-completion 状态相同：{same_invalid}/{total} 对", report)
        self.assertIn(f"finding (severity, category) 多重集相同：{same_shape}/{total} 对", report)
        # This export's finding shapes differ in every valid pair: the null rule cannot be the
        # reason, so the summary must say so and name the coverage decision instead.
        self.assertLess(same_shape, total)
        self.assertIn("null 差异规则不适用", report)
        self.assertIn(f"的判定依据是 `{data['decided_by']}`，不是 null difference", report)
        self.assertNotIn("若配对均满足这一条件", report)
        costs = [cost for pair in complete
                 for cost in renderer.pair_costs({"control": pair["control"], "variant": pair["variant"]})]
        self.assertEqual(costs, [])
        self.assertIn("完整配对中未观察到 S2/S3/S4 代价", report)

    def test_mechanical_column_comes_from_the_record(self):
        row = {"run_id": "h2r2-f99-c", "task_id": "f99", "arm": "control",
               "verdict": "INVALID", "mechanical_verdict": None, "final_verdict": "INVALID",
               "attempts": [{"attempt": 1, "kind": "TERMINAL"}]}
        data = {"rows": [row], "pairs": [], "usable_pairs": 0, "planned_pairs": 1,
                "decided_by": "COVERAGE:INVALID:h2r2-f99-c", "result": "INSUFFICIENT_EVIDENCE",
                "denied_attempts": {"by_arm": {"control": {"count": 0}, "variant": {"count": 0}}}}
        records = {"h2r2-f99-c": {"mechanical": {"verdict": "ACCEPT", "reasons": []},
                                  "reason_codes": ["OUT_OF_RUN_ACCESS:PATH_OUTSIDE_RUN"],
                                  "access_audit": {"hits": [{"path": ".."}]}}}
        report = renderer.render(data, records)
        columns = [cell.strip() for cell in next(
            line for line in report.splitlines() if line.startswith("| h2r2-f99-c |")
        ).strip("|").split("|")]
        self.assertEqual(columns[4], "ACCEPT")   # Mechanical: the exported per-run verdict
        self.assertEqual(columns[6], "INVALID")  # Final verdict is unchanged
        self.assertIn("机械验收均为 ACCEPT", report)

    def test_null_difference_statement_follows_data(self):
        def pair(task, correctness, invalid, control_shape, variant_shape=None):
            return {"task_id": task, "valid": True,
                    "control": {"run_id": f"{task}-c", "task_id": task, "arm": "control",
                                "final_correctness": correctness, "invalid_completion": invalid,
                                "finding_shape": control_shape, "missed_guidance": []},
                    "variant": {"run_id": f"{task}-v", "task_id": task, "arm": "variant",
                                "final_correctness": correctness, "invalid_completion": invalid,
                                "finding_shape": variant_shape or control_shape,
                                "missed_guidance": []}}
        base = {"usable_pairs": 1, "planned_pairs": 1, "denied_attempts":
                {"by_arm": {"control": {"count": 0}, "variant": {"count": 0}}}}
        identical = pair("f01", "PASS", False, [["P2", "HV1"]])
        data = dict(base, pairs=[identical], rows=[identical["control"], identical["variant"]],
                    result="INSUFFICIENT_EVIDENCE", decided_by="NULL_DIFFERENCE")
        report = renderer.render(data, {})
        self.assertIn("FINAL_CORRECTNESS 相同：1/1 对", report)
        self.assertIn("finding (severity, category) 多重集相同：1/1 对", report)
        self.assertIn("null-difference 条件对全部 1 个有效配对成立", report)
        self.assertIn("由 null difference 决定", report)
        differing = pair("f01", "PASS", False, [["P2", "HV1"]], [["P3", "HV1"]])
        data = dict(base, pairs=[differing], rows=[differing["control"], differing["variant"]],
                    result="INSUFFICIENT_EVIDENCE", decided_by="COVERAGE:MISSING:f02/variant")
        report = renderer.render(data, {})
        self.assertIn("finding (severity, category) 多重集相同：0/1 对（不同：f01）", report)
        self.assertIn("只对 0/1 个有效配对成立", report)
        self.assertIn("不是 null difference", report)
        cost = pair("f01", "PASS", False, [["P2", "HV1"]])
        cost["variant"]["final_correctness"] = "FAIL"
        data = dict(base, pairs=[cost], rows=[cost["control"], cost["variant"]],
                    result="DISCLOSURE_HAS_COST", decided_by="S4_TREATMENT_ONLY_CORRECTNESS:f01")
        report = renderer.render(data, {})
        self.assertIn("FINAL_CORRECTNESS 相同：0/1 对", report)
        self.assertIn("完整配对中观察到 S2/S3/S4 代价：f01 S4:f01-v", report)


if __name__ == "__main__":
    unittest.main()
