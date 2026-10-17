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


class AdmissionCorpusStaysOutOfH3(unittest.TestCase):
    """Fresh review of 4add2ca, finding 4: the anchors must not change H3's replay input."""

    def test_h3_corpus_is_byte_identical_to_the_n21_closure(self):
        proc = subprocess.run(["git", "-C", str(ROOT), "diff", "--quiet",
                               "f4eb50370f7edbad03451b73affc6db4bb379a92", "--",
                               "experiments/v1.2/replay/cases.yaml"])
        self.assertEqual(0, proc.returncode, "replay/cases.yaml (H3's input) was modified")

    def test_admission_signals_agree_with_the_h3_detector(self):
        """corpus_cases.py counts signals with different git commands; the detector must agree."""
        sys.path.insert(0, str(ROOT / "experiments" / "v1.2"))
        import structure_delta
        cases = structure_delta.load_replay_cases(ADM / "corpus.yaml")
        self.assertEqual(27, len(cases))
        for c in cases:
            self.assertEqual(
                structure_delta._aligned(c["expected_signals"]),
                structure_delta._aligned(structure_delta.extract_signals(
                    str(ROOT), c["base_sha"], c["candidate_sha"])), c["case_id"])


class CorpusPairsAreMainHistory(unittest.TestCase):
    """The execution boundary (schema §6.6) rests on every LOCAL corpus case being a real
    main-reachable pair whose base is the candidate's first parent; review of 617ba01 noted this
    was a review obligation only. It is now checked for both corpora."""

    MAIN = "5ab500e5478b671f43df80a78730ca172da6cf2b"

    def test_every_local_case_is_a_first_parent_pair_on_main(self):
        ctc = _load("adm_ctc_main", VALIDATOR)
        pairs = ctc.corpus_pairs(ctc.Repo(ROOT))
        self.assertTrue(pairs)
        local = 0
        for case_id, (base, cand, repo) in pairs.items():
            if repo != "FlapPearLabs/agent-engineering-governance":
                continue                          # external (r01): verified out of band
            local += 1
            self.assertEqual(0, subprocess.run(["git", "-C", str(ROOT), "merge-base",
                                                "--is-ancestor", cand, self.MAIN]).returncode,
                             f"{case_id}: candidate not reachable from main {self.MAIN[:12]}")
            first = subprocess.run(["git", "-C", str(ROOT), "rev-parse", cand + "^1"],
                                   capture_output=True, text=True, check=True).stdout.strip()
            self.assertEqual(first, base, f"{case_id}: base is not the first parent")
        self.assertEqual(31, local)


class DiscoveryIsReproducible(unittest.TestCase):
    def test_rerun_at_the_recorded_ref_reproduces_the_routing(self):
        for name, extra in (("batch-1/discovery-governance.json", []),
                            ("batch-3/discovery-merges.json", ["--merges"])):
            self._reproduce(ADM / name, extra)

    def _reproduce(self, path: Path, extra: list[str]):
        recorded = json.loads(path.read_text(encoding="utf-8"))
        have = subprocess.run(["git", "-C", str(ROOT), "cat-file", "-e",
                               recorded["ref_sha"] + "^{commit}"]).returncode == 0
        if not have:
            self.fail(f"recorded ref {recorded['ref_sha']} is not in this object database — "
                      f"the discovery cannot be reproduced here (failing, not skipping)")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "d.json"
            proc = subprocess.run([sys.executable, str(ADM / "discover.py"), str(ROOT),
                                   recorded["ref_sha"], str(out), *extra], capture_output=True,
                                  text=True)
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
        self.assertEqual(["batch-1", "batch-2", "batch-3"], [b.name for b in BATCHES])

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

    def test_evidence_strings_match_each_pairs_own_facts(self):
        """Fresh review of 4add2ca, finding 5: hardcoded strings told batch 2 it was routed as
        MEASURE_ADDED_ACCEPTANCE with a DELTA_ADDED basis. Every string must match the pair."""
        for batch in BATCHES:
            cdoc = json.loads((batch / "case-map.json").read_text(encoding="utf-8"))
            disc = json.loads((batch / cdoc.get("discovery", "discovery-governance.json"))
                              .read_text(encoding="utf-8"))
            pairs = {q["candidate_sha"]: q for q in disc["pairs"] if "base_sha" in q}
            ledger = {r["CASE_ID"]: r for r in json.loads(
                (batch / "ledger.json").read_text(encoding="utf-8"))["rows"]}
            for rec in json.loads((batch / "classification.json").read_text(
                    encoding="utf-8"))["records"]:
                pair = pairs[rec["candidate_sha"]]
                self.assertEqual(f"discovery disposition {pair['disposition']}",
                                 rec["evidence"][0]["measured"], rec["corpus_case_id"])
                m = json.loads((batch / "measurements" / f"{rec['candidate_sha'][:12]}.json")
                               .read_text(encoding="utf-8"))
                carried = ((m["facts"]["discriminating"] or [None])[0]
                           if rec["class"] == "A_REPAIR" else
                           (m["facts"]["biting"] or [None])[0]
                           if rec["class"] == "B_REGRESSION_GUARD" else None)
                note = rec["disclosures"]["acceptance_provenance_note"]
                ext = ledger[rec["corpus_case_id"]]["ORACLE_EXTERNALIZATION"]
                if carried is None:
                    self.assertIn("no surface carries", note)
                    detail = rec["reject_triggers"][0]["detail"]
                    for cls_key in ("A_REPAIR", "B_REGRESSION_GUARD"):
                        reason = m["verdicts"][cls_key]["reason"]
                        self.assertIn(reason, detail, rec["corpus_case_id"])
                        self.assertIn(reason, rec["round_admission"]["reason_codes"])
                    for e in m["facts"].get("biting") or []:
                        self.assertIn(e["path"], detail, rec["corpus_case_id"])
                    continue
                self.assertIn(f"{carried['path']} [{carried['provenance']}]", note)
                if rec["class"] == "A_REPAIR":
                    self.assertTrue(ext.startswith("REQUIRED_AT_FREEZE_V2"
                                                   if carried["provenance"] == "DELTA_ADDED"
                                                   else "FRAMEWORK_FROZEN"), rec["corpus_case_id"])

    # one record per stratum: A on an added oracle, A on a frozen oracle, B, C, A on a PR merge.
    # The full re-validation of every record is the reviewer command in admission/README.md.
    SAMPLE = ("r09-governance-seam-contract-partitions", "r24-governance-bootstrap-budget-repair-round-2",
              "r30-governance-h3a-replay-results", "r08-governance-project-continuity-contract",
              "r31-governance-pr1-global-governance-audit")

    def test_a_stratified_sample_revalidates_exactly_as_recorded(self):
        records, recorded = [], {}
        for batch in BATCHES:
            doc = json.loads((batch / "classification.json").read_text(encoding="utf-8"))
            run = (batch / "validator-run.txt").read_text(encoding="utf-8").splitlines()
            for r in doc["records"]:
                if r["corpus_case_id"] in self.SAMPLE:
                    records.append(r)
                    cid = r["corpus_case_id"]
                    recorded[cid] = sorted(ln.strip() for ln in run
                                           if ln.strip().split(" ")[:2] == ["TRANSITION", cid]
                                           or ln.strip().startswith(cid + " "))
        self.assertEqual(len(self.SAMPLE), len(records))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "c.json"
            path.write_text(json.dumps({"schema": "ELIGIBILITY_SCHEMA_V2",
                                        "schema_version": self.ctc.SCHEMA_VERSION,
                                        "records": records}), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(VALIDATOR), str(path), str(ROOT)],
                                  capture_output=True, text=True)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        lines = [ln.strip() for ln in proc.stdout.splitlines()]
        for cid in self.SAMPLE:
            again = sorted(ln for ln in lines if ln.split(" ")[:2] == ["TRANSITION", cid]
                           or ln.startswith(cid + " "))
            self.assertEqual(recorded[cid], again, cid)

if __name__ == "__main__":
    unittest.main()
