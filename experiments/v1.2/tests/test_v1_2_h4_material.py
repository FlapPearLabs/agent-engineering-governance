import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
AREA = ROOT / "experiments/v1.2/h4-micro-low-ablation"
SCRIPT = AREA / "measure_eligibility.py"


class EligibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.name", "Test")
        self.git("config", "user.email", "test@example.invalid")
        (self.repo / "scripts/tests").mkdir(parents=True)
        (self.repo / ".github/workflows").mkdir(parents=True)
        (self.repo / ".github/workflows/test.yml").write_text("steps:\n  - run: python3 -m ruff check .\n")
        (self.repo / "scripts/tests/test_oracle.py").write_text(
            "import unittest\nfrom pathlib import Path\n"
            "class Oracle(unittest.TestCase):\n"
            "    def test_marker(self):\n        self.assertEqual(Path('marker').read_text(), 'fixed')\n")
        (self.repo / "ruff.toml").write_text('[lint]\nselect = ["E9", "F"]\n')
        (self.repo / "marker").write_text("broken")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD")
        (self.repo / "marker").write_text("fixed")
        self.git("add", "marker")
        self.git("commit", "-qm", "fix")
        self.candidate = self.git("rev-parse", "HEAD")

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def check_task(self, base=None, candidate=None):
        task = {"id": "test", "base": base or self.base,
                "candidate": candidate or self.candidate,
                "oracle": "scripts/tests/test_oracle.py", "role": "outcome", "risk": "LOW"}
        file = self.root / "tasks.json"
        file.write_text(json.dumps({"tasks": [task]}))
        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        process = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(self.repo),
                                  "--tasks", str(file)], capture_output=True, text=True, env=env)
        return process, json.loads(process.stdout)["tasks"][0]

    def test_base_accepted_is_ineligible(self):
        process, result = self.check_task(base=self.candidate)
        self.assertEqual(result["verdict"], "INELIGIBLE")
        self.assertEqual(process.returncode, 0)

    def test_freeze_v3_accept_path_rejects_base_that_passes(self):
        spec = importlib.util.spec_from_file_location("h4_measure", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        task = {"id": "test", "base": self.base, "candidate": self.candidate,
                "oracle": "scripts/tests/test_oracle.py", "oracle_kind": "freeze_v3",
                "role": "outcome", "risk": "LOW"}
        base = {"verdict": "REJECT", "reasons": ["BASE_NOT_FAILING:RESOLVED",
                                                  "BASE_NOT_FAILING:SYMLINKED"]}
        candidate = {"verdict": "ACCEPT", "reasons": []}
        with mock.patch.object(module, "freeze_v3_measure", return_value=(base, candidate)):
            result = module.evaluate(self.repo, task)
        self.assertEqual("INELIGIBLE", result["verdict"])
        self.assertEqual("REJECT", result["base_accept"]["verdict"])

    def test_missing_revision_is_error(self):
        process, result = self.check_task(base="not-a-commit")
        self.assertEqual(result["verdict"], "PROBE_ERROR")
        self.assertNotEqual(process.returncode, 0)

    def test_gate_cannot_detect_positive_control(self):
        with (self.repo / "ruff.toml").open("a") as stream:
            stream.write('[lint.per-file-ignores]\n"scripts/n7_control.py" = ["F841"]\n')
        (self.repo / "marker").write_text("broken")
        self.git("add", "ruff.toml", "marker")
        self.git("commit", "-qm", "base ignores control")
        base = self.git("rev-parse", "HEAD")
        (self.repo / "marker").write_text("fixed")
        self.git("add", "marker")
        self.git("commit", "-qm", "fix marker")
        process, result = self.check_task(base=base, candidate=self.git("rev-parse", "HEAD"))
        self.assertIn(result["verdict"], ("INELIGIBLE", "PROBE_ERROR"))
        self.assertNotEqual(result["verdict"], "ELIGIBLE")
        if result["verdict"] == "PROBE_ERROR":
            self.assertNotEqual(process.returncode, 0)

    def test_task_ids_match_document(self):
        tasks = json.loads((AREA / "task-candidates.json").read_text())["tasks"]
        text = (AREA / "TASKS.md").read_text()
        receipt = json.loads(re.search(r"```json\n(.*?)\n```", text, re.S).group(1))
        measured = {item["id"]: item for item in receipt["tasks"]}
        self.assertEqual(set(measured), {task["id"] for task in tasks})
        for task in tasks:
            self.assertIn(task["id"], text)
            self.assertEqual(measured[task["id"]]["base_resolved"], task["base"])
            self.assertEqual(measured[task["id"]]["candidate_resolved"], task["candidate"])
        self.assertEqual(len({task["id"] for task in tasks}), len(tasks))
        self.assertEqual(receipt["eligible_count"], sum(
            item["verdict"] == "ELIGIBLE" for item in measured.values()))
        funnel = receipt["funnel"]
        self.assertEqual(len(measured), funnel["examined"])
        self.assertEqual(len(measured), sum(funnel[key] for key in (
            "not_a_candidate", "excluded_at_oracle", "excluded_at_risk",
            "excluded_at_injection", "probe_error", "eligible_outcomes",
            "qualifying_controls")))
        self.assertEqual(funnel["eligible_outcomes"], receipt["eligible_count"])
        self.assertEqual(funnel["qualifying_controls"],
                         receipt["false_green_control_count"])
        self.assertEqual("MET" if (funnel["eligible_outcomes"]
                                   + funnel["qualifying_controls"] >= 4
                                   and funnel["qualifying_controls"] >= 1)
                         else "PROTOCOL_NOT_STARTABLE", receipt["task_count_gate"])
