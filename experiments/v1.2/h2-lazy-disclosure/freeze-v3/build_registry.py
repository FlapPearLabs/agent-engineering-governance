#!/usr/bin/env python3
"""Generate the ten-task registry from the fixed shortlist and admission ledgers."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from wrapper_delivery import H2_REL, ROOT, git, sha256

# F1 (CODEX_FIXES_1 T10): `unittest discover -s scripts/tests` puts scripts/tests first on sys.path,
# so an ADDED module there decides what the frozen oracle imports (an added json.py shadowing the
# stdlib made an unfixed base run green). The prefix freezes the whole directory for every task, on
# top of the per-file deny list of every base test file and the oracle.
DENY_PREFIXES = ("scripts/tests/",)
SCOPE_PREFIX_SOURCE = (
    "F1 (CODEX_FIXES_1 T10): deny_prefixes = ['scripts/tests/'] for every task — no add, modify, "
    "delete or rename inside the directory discover imports from, on top of the per-file deny "
    "list. Supersedes the round-2 n01/n02 empty-prefix interpretation, because an added "
    "stdlib-named module there shadows the imports the frozen oracle resolves and can make an "
    "unrepaired base pass.")


def build(root: Path = ROOT) -> dict:
    h2 = root / H2_REL
    shortlist = json.loads((h2 / "admission/freeze-v2-input/shortlist.json").read_text())["shortlist"]
    if len(shortlist) != 10:
        raise ValueError("SHORTLIST_COUNT_MISMATCH")
    ledgers = {}
    for index in range(1, 5):
        rel = f"{H2_REL}/admission/batch-{index}/ledger.json"
        for row in json.loads((root / rel).read_text())["rows"]:
            if row["CASE_ID"] in ledgers:
                raise ValueError("DUPLICATE_CASE")
            ledgers[row["CASE_ID"]] = (row, rel)
    tasks, expected = [], {}
    for index, source in enumerate(shortlist, 1):
        tid = f"f{index:02d}"
        row, ledger = ledgers[source["CASE_ID"]]
        base, candidate = source["BASE_SHA"], source["CANDIDATE_SHA"]
        if (row["BASE_SHA"] != base or row["CANDIDATE_SHA"] != candidate
                or row["SCHEMA_V2_RESULT"] != "A_REPAIR / REQUEST_VALID"
                or row["REGRESSED_GUARDS"] or row["DELETED_ACCEPTANCE_SURFACES"]):
            raise ValueError(f"ADMISSION_MISMATCH {tid}")
        path = source["ORACLE"]["path"]
        base_hash = sha256(git(root, "show", f"{base}:{path}", binary=True))
        candidate_hash = sha256(git(root, "show", f"{candidate}:{path}", binary=True))
        if base_hash != candidate_hash or candidate_hash != source["ORACLE"]["candidate_blob_sha256"]:
            raise ValueError(f"ORACLE_NOT_FROZEN {tid}")
        subject = git(root, "show", "-s", "--format=%s", candidate).strip()
        summary = re.sub(r"^[^:]+:\s*", "", subject)
        summary = re.sub(r"\s*\(Issue #\d+\)", "", summary).rstrip(".")
        task_text = (f"Repair the reported issue: {summary}; make `{path}` pass "
                     "without modifying any test file.")
        denied = set(git(root, "ls-tree", "-r", "--name-only", base, "--",
                         "scripts/tests/").splitlines()) | {path}
        tasks.append({"task_id": tid, "case_id": source["CASE_ID"], "base_sha": base,
                      "task_class": "A_REPAIR",
                      "oracle": {"path": path, "base_blob_sha256": base_hash,
                                 "candidate_blob_sha256": candidate_hash,
                                 "provenance": "FRAMEWORK_FROZEN",
                                 "command": source["ORACLE"]["command"]},
                      "admission": {"request_status": "REQUEST_VALID", "ledger": ledger},
                      "scope": {"deny": sorted(denied), "deny_prefixes": list(DENY_PREFIXES),
                                "allow": "Every other path inside repo/"},
                      "task_text": task_text})
        expected[tid] = {"candidate_sha": candidate}
    return {"schema_version": 2, "program": "freeze-v3/build_registry.py",
            "scope_prefix_source": SCOPE_PREFIX_SOURCE,
            "tasks": tasks, "expected": expected}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(build(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("REGISTRY_V3 tasks=10 FRAMEWORK_FROZEN=10")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
