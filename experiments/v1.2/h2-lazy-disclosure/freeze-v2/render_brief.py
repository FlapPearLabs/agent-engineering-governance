#!/usr/bin/env python3
"""Render the common wrapper-layout contract and copy the committed report template."""
from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path

from wrapper_delivery import H2_REL, ROOT, delivery, git, outside_repository, sha256

HERE = Path(__file__).resolve().parent


def render(task: dict, run: dict, interpreter: str, root: Path = ROOT) -> str:
    arm = run["arm"]
    files = delivery(root, run["materials_commit"], arm)
    direction = ("全文读取 AGENTS.md（当前完整治理正文与薄包装），治理 references 使用 H2_WARM/ 副本。"
                 if arm == "control" else
                 "全文读取 AGENTS.md（lean carrier），按其中路由只加载命中的 H2_WARM/，按其 Skill 规则处置。")
    block = (f"RUN_ID = {run['run_id']}\nARM = {arm}\n"
             f"CARRIER_KIND = {'control_full_v1' if arm == 'control' else 'variant_lean_v1'}\n"
             f"CARRIER_SHA256 = {sha256(files['AGENTS.md'])}\n"
             f"MATERIALS_COMMIT = {run['materials_commit']}\n\n"
             "S1：全文读取 ./H2_RULES.md。\nS2：按投递治理判定 LOW / MEDIUM / HIGH。\n"
             f"S3：{direction}\n"
             "S4：记录 startup carrier 全文读取状态，核对其 sha256 与上面的 CARRIER_SHA256。\n\n"
             "报告 §A 使用同一回执格式：\n"
             "H2_RECEIPT = S0:<sha|MISMATCH> S1:<read|missing> S2:<LOW|MEDIUM|HIGH> "
             "S3:<targets|none> S4:<full|partial|missing>\n")
    values = {"<TASK_ID>": task["task_id"], "<MODEL>": run["model"],
              "<BASE_SHA>": task["base_sha"], "<PYTHON>": interpreter,
              "<TASK_TEXT>": task["task_text"],
              "<ORACLE_COMMAND>": task["oracle"]["command"].replace("{PY}", shlex.quote(interpreter)),
              "<SCOPE_JSON>": json.dumps(task["scope"], indent=2, ensure_ascii=False),
              "<BOOTSTRAP_DELIVERY_BLOCK>": block}
    text = (HERE / "worker-brief-v2.md").read_text(encoding="utf-8")
    for key, value in values.items():
        text = text.replace(key, value)
    return text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--python", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    outside_repository(args.out.resolve().parent)
    runs = json.loads((HERE / "run-plan-v2.json").read_text())["runs"]
    run = next(r for r in runs if r["run_id"] == args.run_id)
    tasks = json.loads((HERE / "task-registry-v2.json").read_text())["tasks"]
    task = next(t for t in tasks if t["task_id"] == run["task_id"])
    args.out.write_text(render(task, run, args.python), encoding="utf-8")
    template = git(ROOT, "show", f"{run['materials_commit']}:{H2_REL}/harness/"
                   "worker-report-template.md", binary=True)
    (args.out.parent / "worker-report-template.md").write_bytes(template)
    print("WORKER_BRIEF_V2 rendered; report template copied from materials objects")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
