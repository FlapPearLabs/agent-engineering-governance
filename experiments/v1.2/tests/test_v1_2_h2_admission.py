"""Material tests for the H2 Schema-v2 candidate-admission workflow (h2-lazy-disclosure/admission/).

What is pinned here, and why each is a mechanical check rather than a restatement:

  * the discovery prefilter's acceptance-path predicate equals the validator's own
    acceptance_surfaces() on a tree that contains near-miss paths — a prefilter that disagreed
    with the validator would silently drop or invent candidates;
  * discovery is reproducible: re-running it at the recorded ref gives the recorded funnel and the
    recorded routing of every pair (nothing typed into the discovery file by hand);
  * identity: every case the batch claims is a corpus case with exactly that pair, and every record
    names its own case;
  * the ledger's counts are the classification's counts, and every evidence path resolves;
  * a SAMPLE of the batch's records is re-validated from scratch here (the full re-run is the
    reviewer's command in admission/README.md — fifteen transitions are too slow for this suite):
    one valid request and one rejection must come out exactly as the recorded run says.

Stdlib only. Run with:  python3 -m unittest discover -s experiments/v1.2/tests -p 'test_v1_2_h2_admission.py'
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
H2 = ROOT / "experiments" / "v1.2" / "h2-lazy-disclosure"
ADM = H2 / "admission"
BATCH1 = ADM / "batch-1"
VALIDATOR = H2 / "harness" / "check_task_class.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


class DiscoveryAgreesWithTheValidator(unittest.TestCase):
    def test_acceptance_path_predicate_equals_acceptance_surfaces(self):
        disc = _load("adm_discover", ADM / "discover.py")
        ctc = disc.ctc
        paths = ["scripts/validate_a.py", "scripts/tests/test_b.py", "scripts/tests/helper.py",
                 "scripts/tests/sub/test_c.py", "scripts/sub/validate_d.py", "scripts/test_e.py",
                 "scripts/check_f.py", "adapters/x/tests/test_g.py", "validate_h.py",
                 "scripts/validate_i.sh"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for p in paths:
                (root / p).parent.mkdir(parents=True, exist_ok=True)
                (root / p).write_text("", encoding="utf-8")
            surfaces = set(ctc.acceptance_surfaces(root))
        self.assertEqual({"scripts/validate_a.py", "scripts/tests/test_b.py"}, surfaces)
        self.assertEqual(surfaces, {p for p in paths if disc.ACCEPTANCE_PATH_RE.match(p)})


class DiscoveryIsReproducible(unittest.TestCase):
    def test_rerun_at_the_recorded_ref_reproduces_the_routing(self):
        recorded = json.loads((BATCH1 / "discovery-governance.json").read_text(encoding="utf-8"))
        have = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e",
                               recorded["ref_sha"] + "^{commit}"]).returncode == 0
        if not have:
            self.fail(f"recorded ref {recorded['ref_sha']} is not in this object database — "
                      f"the discovery cannot be reproduced here (failing, not skipping)")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "d.json"
            proc = subprocess.run([sys.executable, str(ADM / "discover.py"), str(ROOT),
                                   recorded["ref_sha"], str(out)], capture_output=True, text=True)
            self.assertEqual(0, proc.returncode, proc.stderr)
            again = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(recorded["funnel"], again["funnel"])
        self.assertEqual(
            [(p.get("base_sha"), p["candidate_sha"], p["disposition"]) for p in recorded["pairs"]],
            [(p.get("base_sha"), p["candidate_sha"], p["disposition"]) for p in again["pairs"]])


BATCHES = sorted(p for p in ADM.glob("batch-*") if (p / "classification.json").is_file())


class BatchIdentityAndLedger(unittest.TestCase):
    """Every batch that ships records: identity, ledger counts, evidence reachability."""

    def setUp(self):
        self.ctc = _load("adm_ctc", VALIDATOR)
        self.corpus = self.ctc.corpus_pairs(self.ctc.Repo(ROOT))

    def test_batches_exist(self):
        self.assertEqual(["batch-1", "batch-2"], [b.name for b in BATCHES])

    def test_every_claimed_case_is_that_corpus_case(self):
        self.assertTrue(self.corpus, "the corpus did not load under its pinned digest")
        seen = set()
        for batch in BATCHES:
            cmap = json.loads((batch / "case-map.json").read_text(encoding="utf-8"))["cases"]
            doc = json.loads((batch / "classification.json").read_text(encoding="utf-8"))
            for cand, case_id in cmap.items():
                self.assertNotIn(case_id, seen, "a case is classified in exactly one batch")
                seen.add(case_id)
                self.assertIn(case_id, self.corpus)
                base, want_cand, repo = self.corpus[case_id]
                self.assertEqual(cand, want_cand, case_id)
                parent = subprocess.run(["git", "-C", str(ROOT), "rev-parse", cand + "^"],
                                        capture_output=True, text=True, check=True).stdout.strip()
                self.assertEqual(parent, base, case_id)
                self.assertEqual("FlapPearLabs/agent-engineering-governance", repo)
            self.assertEqual(sorted(cmap.values()),
                             sorted(r["corpus_case_id"] for r in doc["records"]))

    def test_ledger_counts_are_the_classification_counts(self):
        for batch in BATCHES:
            doc = json.loads((batch / "classification.json").read_text(encoding="utf-8"))
            ledger = json.loads((batch / "ledger.json").read_text(encoding="utf-8"))
            valid = [r for r in doc["records"]
                     if r["round_admission"]["verdict"] == "REQUEST_VALID"]
            s = ledger["summary"]
            self.assertEqual("PASS", s["validator_run"], batch.name)
            self.assertEqual(len(doc["records"]), s["records"], batch.name)
            self.assertEqual(len(valid), s["schema_v2_valid_requests"], batch.name)
            self.assertEqual(0, s["executions_disagree"], batch.name)
            for row in ledger["rows"]:
                for p in row["EVIDENCE_PATHS"]:
                    self.assertTrue((ROOT / p).is_file(), p)

    def test_a_sample_revalidates_exactly_as_recorded(self):
        """r09 (valid, fast) and r08 (rejected) re-run from scratch through the real validator."""
        doc = json.loads((BATCH1 / "classification.json").read_text(encoding="utf-8"))
        self.doc = doc
        sample = [r for r in doc["records"]
                  if r["corpus_case_id"] in ("r08-governance-project-continuity-contract",
                                             "r09-governance-seam-contract-partitions")]
        self.assertEqual(2, len(sample))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(json.dumps(dict(self.doc, records=sample)), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(VALIDATOR), str(path), str(ROOT)],
                                  capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("valid_requests=1 rejected=1 errors=0", proc.stdout)
        self.assertIn("TRANSITION r09-governance-seam-contract-partitions class=A_REPAIR "
                      "verdict=FAIL_TO_PASS", proc.stdout)


if __name__ == "__main__":
    unittest.main()
