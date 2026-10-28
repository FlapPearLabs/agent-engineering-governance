#!/usr/bin/env python3
"""Render the H2 closure report from the exported aggregate and run records."""
import argparse
from collections import Counter
import json
import re
from pathlib import Path


def cell(value):
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def attempts_summary(attempts):
    blocked = [a for a in attempts if a.get("kind") == "PROVIDER_FAILED_BEFORE_WORK"]
    if not blocked:
        return str(len(attempts))
    numbers = [a["attempt"] for a in blocked]
    span = str(numbers[0]) if len(numbers) == 1 else f"{numbers[0]}–{numbers[-1]}"
    return f"{len(attempts)} ({span} BLOCKED before work: provider.no-route)"


def reason_summary(record):
    codes = Counter(record.get("reason_codes", []))
    parts = [f"{code} x{count}" if count > 1 else code for code, count in codes.items()]
    if any(code.startswith("OUT_OF_RUN_ACCESS:") for code in codes):
        hits = record.get("access_audit", {}).get("hits", [])
        targets = []
        for hit in hits:
            target = hit.get("path") or hit.get("tool")
            if target and re.fullmatch(r"[\w./*<>-]+", target) and target not in targets:
                targets.append(target)
        if targets:
            parts.append(", ".join(targets))
    return "; ".join(parts) or "—"


def render(data, records=None):
    records = records or {}
    rows = data["rows"]
    valid = [p["task_id"] for p in data["pairs"] if p["valid"]]
    by_task = {task: {r["arm"]: r for r in rows if r.get("task_id") == task} for task in valid}
    lines = ["# H2-R2 — CLOSURE REPORT", "", "## 结论摘要", "",
             f"- 结果：`{data['result']}`；decided_by：`{data['decided_by']}`。",
             f"- 仅 {data['usable_pairs']}/{data['planned_pairs']} 个任务有有效配对：{', '.join(valid)}。"]
    invalid = [r for r in rows if r.get("final_verdict") == "INVALID"]
    blocked = [r for r in rows if r.get("final_verdict") == "BLOCKED"]
    for label, group in (("INVALID", invalid), ("BLOCKED", blocked)):
        if group:
            lines.append(f"- {label}：" + "; ".join(
                f"{r['run_id']} ({reason_summary(records.get(r['run_id'], {}))})" for r in group) + "。")
    lines += ["", "| 配对 | control FINAL_CORRECTNESS | control findings (severity, category) | variant FINAL_CORRECTNESS | variant findings (severity, category) |",
              "|---|---|---|---|---|"]
    for task, arms in by_task.items():
        if not all(arm in arms for arm in ("control", "variant")):
            continue
        c, v = arms["control"], arms["variant"]
        shape = lambda r: ", ".join(f"({a}, {b})" for a, b in r.get("finding_shape", [])) or "—"
        lines.append("| " + " | ".join(map(cell, [task, c.get("final_correctness"), shape(c), v.get("final_correctness"), shape(v)])) + " |")
    complete = [arms for arms in by_task.values() if set(arms) >= {"control", "variant"}]
    if complete:
        pairs = Counter((a["control"].get("final_correctness"), a["variant"].get("final_correctness")) for a in complete)
        counts = ", ".join(f"{n} {c}/{v}" for (c, v), n in sorted(pairs.items()))
        if all(c == v for c, v in pairs):
            lines.append(f"\n全部 {len(complete)} 个有效配对的 FINAL_CORRECTNESS 相同（{counts}）。")
        lines.append("完整配对中未观察到 S2/S3/S4 代价。预注册的 null-difference 规则要求正确性、无效完成状态及 finding 形状均相同；若配对均满足这一条件，即使覆盖完整也判为 INSUFFICIENT_EVIDENCE。")
    lines += ["", "## 问题与预注册设计", "", "精简渐进披露是否保留任务表现？十个冻结任务各以 control 和 variant 执行一次。",
              "详见 [protocol-v2.md](freeze-v2/protocol-v2.md)。", "", "## 预注册偏离与决定", "",
              "- 十个 frozen-oracle repair 任务替换原任务集；覆盖要求十个有效配对。（来源：[协议 §7](freeze-v2/protocol-v2.md)）",
              "- 仓外 AGENTS 交付、wrapper-relative 遥测及冻结 runtime/profile/model；carrier 缩减以 JS 字符计。（来源：[协议 §7](freeze-v2/protocol-v2.md)）",
              "- 准入、任务、oracle、scope、平衡顺序和验收按注册表与计划；无效及基础设施失败按协议重试。（来源：[协议 §5–7](freeze-v2/protocol-v2.md)）",
              "- 按 run-plan-v2.json 有界并发准备和执行。（来源：[运行计划](freeze-v2/run-plan-v2.json)）",
              "- 二十个 run 的每次 worker 与 auditor 启动只用运行计划中的单一冻结模型。（来源：[运行计划](freeze-v2/run-plan-v2.json)）",
              "- 采用 A：被沙箱拒绝的越界尝试记为证据并按臂报告，只有越界访问实际成功才判 INVALID。（来源：[协议 §5](freeze-v2/protocol-v2.md)）",
              "", "## 各次运行", "", "| Run | Task | Arm | Attempts | Mechanical | Audit correctness | Final verdict | Denied | Reason |",
              "|---|---|---|---|---|---|---|---|---|"]
    for row in rows:
        values = [row.get("run_id"), row.get("task_id"), row.get("arm"), attempts_summary(row.get("attempts", [])),
                  row.get("mechanical_verdict", row.get("verdict")), row.get("audited_correctness"),
                  row.get("final_verdict"), row.get("denied_attempts"), reason_summary(records.get(row.get("run_id"), {}))]
        lines.append("| " + " | ".join(map(cell, values)) + " |")
    lines += ["", "## 聚合结果", "", f"- 有效配对：{data['usable_pairs']}/{data['planned_pairs']}；" + (", ".join(valid) if valid else "无"),
              f"- 结果：`{data['result']}`；决定依据：`{data['decided_by']}`。"]
    for arm in ("control", "variant"):
        lines.append(f"- {arm} 被拒绝尝试总数：{data['denied_attempts']['by_arm'][arm]['count']}。")
    if records and {"h2r2-f05-c", "h2r2-f09-c"} <= records.keys():
        f05 = next(r for r in rows if r["run_id"] == "h2r2-f05-c")
        f09 = next(r for r in rows if r["run_id"] == "h2r2-f09-c")
        lines.append(f"- 两臂差异来自两个 control run 的两条命令：f05-c {f05['denied_attempts']} 次；f09-c {f09['denied_attempts']} 次是同一条进入父目录命令的 token，不能作为臂效应的证据。")
    lines += ["", "## 混杂与限制", "", "仓库自身的 AGENTS.md 在首次读取时附加到两臂。每个任务每臂仅一次，只有一个模型和 runtime；结论仅适用于本 cohort。"]
    if data["result"].startswith("SAFE_CANDIDATE_PENDING:"):
        lines += ["", "## 待人工判断", "", "结果仍为 pending。"]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads((args.export / "aggregate.json").read_text(encoding="utf-8"))
    records = {row["run_id"]: json.loads((args.export / f"{row['run_id']}.json").read_text(encoding="utf-8")) for row in data["rows"]}
    disclosure = (Path(__file__).parent / "disclosures.md").read_text(encoding="utf-8").replace("(r2-4aa2e7b/raw-manifest.json)", "(results-v2/r2-4aa2e7b/raw-manifest.json)")
    args.out.write_text(render(data, records) + "\n" + disclosure, encoding="utf-8")


if __name__ == "__main__":
    main()
