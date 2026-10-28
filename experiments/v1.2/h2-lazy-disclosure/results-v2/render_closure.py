#!/usr/bin/env python3
"""Render the H2 closure report from the exported aggregate."""
import argparse
import json
from pathlib import Path


def cell(value):
    return str(value if value is not None else "—").replace("|", "\\|").replace("\n", " ")


def render(data, protocol=""):
    lines = ["# H2-R2 — CLOSURE REPORT", "", "## 问题与预注册设计", "",
             "精简渐进披露是否保留任务表现？十个冻结任务各以 control 和 variant 执行一次。",
             "详见 [protocol-v2.md](freeze-v2/protocol-v2.md)。", "",
             "## 预注册偏离与决定", "",
             "- 十个 frozen-oracle repair 任务替换原任务集；覆盖要求十个有效配对。",
             "- 仓外 AGENTS 交付、wrapper-relative 遥测、冻结 runtime/profile/model；"
             "carrier 缩减以 JS 字符计，不推算 token 或耗时。",
             "- 准入、任务、oracle、scope、平衡顺序和验收以本轮注册表与计划为准；"
             "scripts/tests/ 和导入遮蔽受冻结保护。",
             "- 无效及基础设施失败按协议 §6 重试与登记，不能按结果重跑。",
             "> 按 run-plan-v2.json **有界并发**准备和执行：", "",
             "> MODEL RULE    二十个 run 的每次 worker 与 auditor 启动只用 run-plan-v2.json 的单一冻结模型",
             "", "> 采用 A：被沙箱拒绝的越界尝试记为证据并按臂报告，只有越界访问实际成功才判 INVALID；在第一次正式运行前写进协议。",
             "", "- Null difference、证据哈希、结果优先序及 S2/S5 待判断均按协议 §7。",
             "", "## 各次运行", "",
             "| Run | Task | Arm | Attempts | Mechanical | Audit correctness | Final verdict | Denied | Reason |",
             "|---|---|---|---|---|---|---|---|---|"]
    for row in data["rows"]:
        values = [row.get("run_id"), row.get("task_id"), row.get("arm"),
                  json.dumps(row.get("attempts", []), ensure_ascii=False),
                  row.get("mechanical_verdict", row.get("verdict")), row.get("audited_correctness"),
                  row.get("final_verdict"), row.get("denied_attempts"), row.get("reason")]
        lines.append("| " + " | ".join(map(cell, values)) + " |")
    valid = [p["task_id"] for p in data["pairs"] if p["valid"]]
    lines += ["", "## 聚合结果", "", f"- 有效配对：{data['usable_pairs']}/{data['planned_pairs']}；"
              + (", ".join(valid) if valid else "无"),
              f"- 结果：`{data['result']}`；决定依据：`{data['decided_by']}`。"]
    for arm in ("control", "variant"):
        lines.append(f"- {arm} 被拒绝尝试总数：{data['denied_attempts']['by_arm'][arm]['count']}。")
    lines += ["", "## 混杂与限制", "",
              "仓库自身的 AGENTS.md 在首次读取时附加到两臂；预注册的 null difference "
              "必须判为 INSUFFICIENT_EVIDENCE。每个任务每臂仅一次，只有一个模型和 runtime；"
              "结论仅适用于本 cohort。"]
    if protocol:
        section = protocol.split("## 7. ", 1)[1].split("## 8. ", 1)[0]
        lines += ["", "## 协议 §7 的完整预注册结果规则与偏离", "", "### " + section.strip()]
    if data["result"].startswith("SAFE_CANDIDATE_PENDING:"):
        lines += ["", "## 待人工判断", "", "结果仍为 pending，不能称为 SAFE。"]
        for rule in data["result"].split(":", 1)[1].split(","):
            evidence = {"S2": "逐臂检查任务与审计记录，判断是否遗漏必要指导",
                        "S5": "依据 rubric §5 检查各发现及其 disposition"}.get(rule, "检查协议与相关审计证据")
            lines.append(f"- {rule}：{evidence}。")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = json.loads((args.export / "aggregate.json").read_text(encoding="utf-8"))
    protocol = (args.export / "protocol-v2.md").read_text(encoding="utf-8")
    args.out.write_text(render(data, protocol), encoding="utf-8")


if __name__ == "__main__":
    main()
