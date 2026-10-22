#!/usr/bin/env python3
"""Generate paired fresh episodes. At T8, regenerate with that freeze commit's parent."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from wrapper_delivery import H2_REL, ROOT, git


def build(materials: str, root: Path = ROOT) -> dict:
    materials = git(root, "rev-parse", "--verify", f"{materials}^{{commit}}").strip()
    registry = json.loads((root / H2_REL / "freeze-v2/task-registry-v2.json").read_text())
    runs = []
    for index, task in enumerate(registry["tasks"]):
        arms = ("control", "variant") if index % 2 == 0 else ("variant", "control")
        for arm in arms:
            runs.append({"run_id": f"h2r2-{task['task_id']}-{arm[0]}",
                         "task_id": task["task_id"], "arm": arm,
                         "materials_commit": materials,
                         "model": "opencode-go/deepseek-v4.1-flash",
                         "runtime": "opencode 2.0.25 --standalone",
                         "profile": "~/.h2-worker-profile", "fresh_episode": True})
    return {"program": "freeze-v2/build_run_plan.py",
            "materials_binding": "Parent of the T8 commit introducing freeze-manifest.json; "
                                 "finalized by regeneration immediately before T8 hashing.",
            "runs": runs}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materials", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.write_text(json.dumps(build(args.materials), indent=2) + "\n", encoding="utf-8")
    print("RUN_PLAN_V2 runs=20 control_first=5 variant_first=5 fresh_episode=20")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
