#!/usr/bin/env python3
"""Reproducible negative controls for the admission findings (inputs and outputs are committed).

Two layers, both re-runnable from the repository alone:

  RECORDS   laundered copies of shipped batch records, written to negative-controls/inputs/ and run
            through the CURRENT validator end to end (identity, triggers, transition, bindings).
            Every one must be refused.
  VERSIONS  the attack pairs run through recompute_transition()+transition_verdict() of earlier
            validator revisions, loaded straight from git (no edited copy): the parent of this
            stage (f4eb503, 2.8.0) and the admission commits 4add2ca (2.8.1) and f2c48a0 (2.8.2). This is the layer the
            defects lived in; the identity layer is version-independent and is exercised by
            RECORDS. An attack is demonstrated when an earlier revision SUPPORTS the class and the
            current one refuses it.

Usage:  negative_controls.py <repo_root>        (writes negative-controls/{inputs/*,*.txt})
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "negative-controls"
VALIDATOR_REL = "experiments/v1.2/h2-lazy-disclosure/harness/check_task_class.py"
REVISIONS = ("f4eb50370f7edbad03451b73affc6db4bb379a92", "4add2ca2880c3f25ce5ca76f5ea882274d9461f3",
             "f2c48a05c737d1b4f625036af0ea3fd28094540e")
B_REQ = {"baseline_oracle_status": "PASS", "mutation_oracle_status": "FAIL",
         "mutation_touches_target_predicate": True, "acceptance_surface_frozen": True,
         "validator_not_worker_controlled": True}
A_REQ = {"baseline_oracle_status": "FAIL", "candidate_oracle_status": "PASS",
         "oracle_in_worker_scope": True, "oracle_authority": "DELTA_AUTHORED_DISCRIMINATING"}
# (name, batch, case, class to launder into, finding)
LAUNDERINGS = (
    ("r08-as-A", "batch-1", "r08-governance-project-continuity-contract", "A_REPAIR", "control"),
    ("r22-as-B", "batch-1", "r22-governance-v12-experiment-foundation", "B_REGRESSION_GUARD",
     "F-A1"),
    ("r23-as-B", "batch-2", "r23-governance-bootstrap-facts-review-round-1", "B_REGRESSION_GUARD",
     "F-A3"),
    ("r26-as-B", "batch-2", "r26-governance-portable-adoption-exercise", "B_REGRESSION_GUARD",
     "F-A6"),
    ("r29-as-B", "batch-2", "r29-governance-v12-experiment-shape-convergence",
     "B_REGRESSION_GUARD", "F-A8"),
)
# (finding, base, candidate): pairs for the VERSIONS layer; the merge is PR #49 (not a corpus case)
PAIRS = (
    ("F-A1 r22", "0007bb3096791114d4616b599f44428e9bbfeb83"),
    ("F-A3 r23", "825d3902597655c90393100281260cbba8697c07"),
    ("F-A4 PR#49 merge", "6217cc0adcd6c064e8c74e670de6a081bdaba2f6"),
    ("F-A6 r26", "95667e8e3d9ac9742a1a80e7dcf7f8e3b4ea5dba"),
    ("F-A8 r29", "5205e5bd92317d9ad1ad53725dc14444f5201d32"),
)


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True,
                          check=True).stdout


def load_revision(root: Path, rev: str, tmp: Path):
    src = tmp / f"ctc_{rev[:7]}.py"
    src.write_text(git(root, "show", f"{rev}:{VALIDATOR_REL}"), encoding="utf-8")
    spec = importlib.util.spec_from_file_location(f"ctc_{rev[:7]}", src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def launder(rec: dict, cls: str) -> dict:
    rec = copy.deepcopy(rec)
    rec.update({"class": cls, "reject_triggers": [],
                "class_considered": [{"class": cls, "verdict": "SHAPE_SATISFIED"}],
                "class_requirements": dict(B_REQ if cls == "B_REGRESSION_GUARD" else A_REQ),
                "round_admission": {"verdict": "REQUEST_VALID", "reason_codes": ["SHAPE_COMPLETE"]}})
    return rec


def main(argv: list[str]) -> int:
    root = Path(argv[1]).resolve()
    sys.path.insert(0, str(HERE.parent / "harness"))
    import check_task_class as current
    (OUT / "inputs").mkdir(parents=True, exist_ok=True)
    report = ["NEGATIVE CONTROLS — current validator " + current.SCHEMA_VERSION, ""]
    refused_all = True
    for name, batch, case, cls, finding in LAUNDERINGS:
        doc = json.loads((HERE / batch / "classification.json").read_text(encoding="utf-8"))
        rec = next(r for r in doc["records"] if r["corpus_case_id"] == case)
        path = OUT / "inputs" / f"{name}.json"
        path.write_text(json.dumps({"schema": current.SCHEMA_ID,
                                    "schema_version": current.SCHEMA_VERSION,
                                    "records": [launder(rec, cls)]}, indent=1) + "\n",
                        encoding="utf-8")
        proc = subprocess.run([sys.executable, str(HERE.parent / "harness" / "check_task_class.py"),
                               str(path), str(root)], capture_output=True, text=True)
        refused = proc.returncode == 1 and "valid_requests=" not in proc.stdout
        refused_all &= refused
        report.append(f"[RECORDS] {name} ({finding}) rc={proc.returncode} "
                      f"{'REFUSED' if refused else 'ACCEPTED'}")
        report += ["    " + ln for ln in proc.stdout.splitlines() if "ERROR" in ln or "VERDICT" in ln]
    report.append("")
    with tempfile.TemporaryDirectory() as tmp:
        versions = [(rev[:7], load_revision(root, rev, Path(tmp))) for rev in REVISIONS]
        versions.append(("current", current))
        for finding, cand in PAIRS:
            base = git(root, "rev-parse", f"{cand}^1").strip()
            for label, mod in versions:
                facts = mod.recompute_transition(mod.Repo(root), base, cand, "B_REGRESSION_GUARD")
                verdict = mod.transition_verdict("B_REGRESSION_GUARD", facts)
                bite = [(Path(e["path"]).name, e["rc_base"], e["rc_cand"], e["rc_mut"])
                        for e in facts.get("biting", [])]
                report.append(f"[VERSIONS] {finding:18s} {label:8s} B={verdict} biting={bite}")
                if label == "current" and verdict[0]:
                    refused_all = False
    report.append("")
    report.append(f"NEGATIVE_CONTROLS = {'ALL_REFUSED_BY_CURRENT' if refused_all else 'FAIL'}")
    (OUT / "report.txt").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    return 0 if refused_all else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
