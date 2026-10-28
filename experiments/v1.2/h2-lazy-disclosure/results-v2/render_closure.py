#!/usr/bin/env python3
"""Render the H2 closure report from the exported aggregate and run records."""
import argparse
from collections import Counter
import json
import re
from pathlib import Path


CORRECTNESS_ORDER = {"PASS": 0, "PARTIAL": 1, "FAIL": 2, "BLOCKED": 3}


def cell(value):
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def finding_shape(record):
    """The pre-registered finding shape of one arm: a (severity, category) multiset."""
    return tuple(sorted(tuple(item) for item in record.get("finding_shape", ())))


def pair_costs(arms):
    """The pre-registered S2/S3/S4 cost rules, evaluated on one complete pair."""
    control, variant = arms["control"], arms["variant"]
    costs = []
    for row in (control, variant):
        if row.get("missed_guidance"):
            costs.append(f"S2:{row.get('run_id')}")
    if int(bool(variant.get("invalid_completion"))) > int(bool(control.get("invalid_completion"))):
        costs.append(f"S3:{variant.get('run_id')}")
    if CORRECTNESS_ORDER[variant["final_correctness"]] > CORRECTNESS_ORDER[control["final_correctness"]]:
        costs.append(f"S4:{variant.get('run_id')}")
    return costs


def null_difference_lines(complete, data):
    """Count the pre-registered null-difference fields from the export and state the decision.

    Every count is derived from the exported runs: nothing here is asserted about the result.
    """
    compared = []
    for arms in complete:
        control, variant = arms["control"], arms["variant"]
        compared.append({"task": control["task_id"],
                         "correctness": control["final_correctness"] == variant["final_correctness"],
                         "invalid": bool(control.get("invalid_completion"))
                         == bool(variant.get("invalid_completion")),
                         "shape": finding_shape(control) == finding_shape(variant),
                         "costs": pair_costs(arms)})
    total = len(compared)

    def same(field):
        return sum(1 for item in compared if item[field])

    null_pairs = [item["task"] for item in compared
                  if item["correctness"] and item["invalid"] and item["shape"]]
    shape_diff = [item["task"] for item in compared if not item["shape"]]
    costs = [(item["task"], cost) for item in compared for cost in item["costs"]]
    decided_by = str(data.get("decided_by", "—"))
    lines = [f"有效配对的结构化比较（共 {total} 对）：",
             f"- FINAL_CORRECTNESS 相同：{same('correctness')}/{total} 对。",
             f"- invalid-completion 状态相同：{same('invalid')}/{total} 对。",
             f"- finding (severity, category) 多重集相同：{same('shape')}/{total} 对"
             + (f"（不同：{', '.join(shape_diff)}）。" if shape_diff else "。")]
    if len(null_pairs) == total:
        lines.append(f"- 因此预注册的 null-difference 条件对全部 {total} 个有效配对成立。")
    else:
        detail = (f"（三项均相同的配对：{', '.join(null_pairs)}）" if null_pairs
                  else "（没有任何配对三项均相同）")
        lines.append(f"- 因此预注册的 null-difference 条件只对 {len(null_pairs)}/{total} 个有效配对成立{detail}，"
                     "对全部有效配对并不成立，null 差异规则不适用。")
    if costs:
        lines.append("- 完整配对中观察到 S2/S3/S4 代价：" + "; ".join(f"{task} {cost}" for task, cost in costs) + "。")
    else:
        lines.append("- 完整配对中未观察到 S2/S3/S4 代价。")
    if decided_by.startswith("NULL_DIFFERENCE"):
        lines.append(f"- 结果 `{data.get('result')}` 由 null difference 决定（decided_by：`{decided_by}`）。")
    else:
        lines.append(f"- 结果 `{data.get('result')}` 的判定依据是 `{decided_by}`，不是 null difference。")
    return lines


def attempts_summary(attempts):
    blocked = [a for a in attempts if a.get("kind") == "PROVIDER_FAILED_BEFORE_WORK"]
    if not blocked:
        return str(len(attempts))
    numbers = [a["attempt"] for a in blocked]
    span = str(numbers[0]) if len(numbers) == 1 else f"{numbers[0]}–{numbers[-1]}"
    return f"{len(attempts)} ({span} BLOCKED before work: provider.no-route)"


def mechanical_verdict(row, records):
    """The exported per-run mechanical verdict; the aggregate's own verdict is never used."""
    record = records.get(row.get("run_id")) or {}
    verdict = (record.get("mechanical") or {}).get("verdict")
    return verdict if verdict is not None else row.get("mechanical_verdict")


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
            line = f"- {label}：" + "; ".join(
                f"{r['run_id']} ({reason_summary(records.get(r['run_id'], {}))})" for r in group) + "。"
            accepted = [r for r in group if mechanical_verdict(r, records) == "ACCEPT"]
            if label == "INVALID" and len(accepted) == len(group):
                line += f"这 {len(group)} 个 run 的机械验收均为 ACCEPT，都是被 access audit 判为 INVALID 的。"
            lines.append(line)
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
        lines.append("")
        lines += null_difference_lines(complete, data)
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
                  mechanical_verdict(row, records), row.get("audited_correctness"),
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
