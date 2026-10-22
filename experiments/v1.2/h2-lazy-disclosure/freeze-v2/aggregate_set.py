#!/usr/bin/env python3
"""The sole owner of H2-v2 aggregate membership; no runtime eligibility reclassification."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def derive(records: list[dict], registry: dict) -> list[dict]:
    requests = {}
    for record in records:
        case = record["corpus_case_id"]
        if case in requests:
            raise ValueError("DUPLICATE_ELIGIBILITY_RECORD")
        requests[case] = record["round_admission"]["verdict"]
    tasks = registry["tasks"]
    if (len({t["case_id"] for t in tasks}) != len(tasks)
            or len({t["task_id"] for t in tasks}) != len(tasks)):
        raise ValueError("DUPLICATE_FROZEN_MEMBERSHIP")
    return [{"task_id": t["task_id"], "case_id": t["case_id"]} for t in tasks
            if requests.get(t["case_id"]) == "REQUEST_VALID"]


def counts(aggregate: list[dict]) -> dict:
    size = len(aggregate)
    return {"tasks": size, "planned_per_arm": size, "planned_runs": size * 2}


def main() -> int:
    records = []
    for index in range(1, 5):
        records.extend(json.loads((HERE.parent / f"admission/batch-{index}/classification.json")
                                  .read_text())["records"])
    registry = json.loads((HERE / "task-registry-v2.json").read_text())
    aggregate = derive(records, registry)
    print(json.dumps({"aggregate_set": aggregate, "counts": counts(aggregate)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
