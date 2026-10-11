#!/usr/bin/env python3
"""H2 HOT-surface inventory + truncation oracle（非 canonical；H2 实验材料）。

与 H1 的 hot_inventory.py 同一计量口径（js_chars / 行粒度截断 / TOKENS=NOT_OBSERVABLE），
只替换了变体臂的 HOT 载体并显式声明 H2 的口径：

  HOT_JS_CHARS = guidance-head 面之和（MEMORY_POINTER + 臂的 guidance 载体）
  MANDATORY_FULL_READ = RULES.md（两臂都读全文；单列，不计入 HOT_JS_CHARS 之和）

单位（严格区分，不得互相换算）：LINES / BYTES / JS_CHARS（UTF-16 code units）/
TOKENS_* = NOT_OBSERVABLE（见 experiments/v1.2/metrics.md）。

用法：
    python3 h2_hot_inventory.py            # inventory 表 + 截断算术
    python3 h2_hot_inventory.py --json     # 机器可读
    python3 h2_hot_inventory.py --selftest # 反例自检
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

MAX_GUIDANCE_CHARS = 8000  # profile 事实（BOOTSTRAP_CONTRACT §1；非跨版本常数）
GUIDANCE_FILES = ["CODEBUDDY.md", ".codebuddy/CODEBUDDY.md", "AGENTS.md"]

HOT_SURFACES_CONTROL = [
    ("MEMORY_POINTER", "deployment/MEMORY_POINTER_CANDIDATE.md"),
    ("GUIDANCE_HEAD", "AGENTS.md"),
]
HOT_SURFACES_VARIANT = [
    ("MEMORY_POINTER", "deployment/MEMORY_POINTER_CANDIDATE.md"),
    ("GUIDANCE_HEAD", "experiments/v1.2/h2-lazy-disclosure/carriers/H2_LEAN_BOOTSTRAP.md"),
]

MANDATORY_READ_CONTROL = ["RULES.md"]
MANDATORY_READ_VARIANT = ["RULES.md"]  # H2：两臂都读 RULES.md 全文（差异只在 guidance 载体）


def js_chars(text: str) -> int:
    """JavaScript string length = UTF-16 code units（非 code point、非 byte）。"""
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def measure(rel_path: str) -> dict[str, object]:
    path = REPO_ROOT / rel_path
    if not path.is_file():
        return {"path": rel_path, "exists": False}
    text = path.read_text(encoding="utf-8")
    return {
        "path": rel_path,
        "exists": True,
        "lines": len(text.splitlines()),
        "bytes": len(text.encode("utf-8")),
        "js_chars": js_chars(text),
        "truncated_at_8000": js_chars(text) > MAX_GUIDANCE_CHARS,
        "budget_capped_js_chars": min(js_chars(text), MAX_GUIDANCE_CHARS),
        "tokens": "NOT_OBSERVABLE",
    }


def _visible_js_chars_for(text: str, limit: int) -> int:
    """逐行累计到 limit 为止，返回实际可见前缀的 js_chars（不含截断行）。"""
    acc = 0
    visible = 0
    for line in text.splitlines(keepends=True):
        prev = acc
        acc += js_chars(line)
        if prev < limit <= acc:
            return visible
        visible = acc
    return visible


def _dropped_js_chars_for(text: str, limit: int) -> int:
    """被丢弃的尾部总量 = 总量 - 可见量（行粒度：截断行整行丢弃，其后全丢）。"""
    return max(0, js_chars(text) - _visible_js_chars_for(text, limit))


def guidance_prefix(rel_path: str, limit: int = MAX_GUIDANCE_CHARS) -> dict[str, object]:
    path = REPO_ROOT / rel_path
    if not path.is_file():
        return {"path": rel_path, "exists": False}
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    acc = 0
    cut_line = None
    for idx, line in enumerate(lines, start=1):
        prev = acc
        acc += js_chars(line)
        if prev < limit <= acc:
            cut_line = idx
            break
    visible = "".join(lines[: cut_line - 1]) if cut_line else "".join(lines)
    return {
        "path": rel_path,
        "exists": True,
        "total_lines": len(lines),
        "total_js_chars": js_chars(text),
        "cut_line": cut_line,
        "visible_lines": (cut_line - 1) if cut_line else len(lines),
        "visible_js_chars": js_chars(visible),
        "dropped_js_chars": max(0, js_chars(text) - js_chars(visible)),
        "visible_headings": [
            ln.strip() for ln in visible.splitlines() if re.match(r"^#{1,2} ", ln)
        ],
        "truncated_headings": [
            ln.strip()
            for ln in "".join(lines[(cut_line - 1) if cut_line else len(lines):]).splitlines()
            if re.match(r"^#{1,2} ", ln)
        ],
    }


def summarize(name: str, surfaces: list[tuple[str, str]], mandatory: list[str]) -> dict:
    rows = [measure(p) for _, p in surfaces]
    guidance = guidance_prefix(dict(surfaces)["GUIDANCE_HEAD"])
    mandatory_rows = [measure(p) for p in mandatory]
    return {
        "arm": name,
        "hot_surfaces": rows,
        "hot_lines": sum(int(r.get("lines", 0)) for r in rows),
        "hot_bytes": sum(int(r.get("bytes", 0)) for r in rows),
        "hot_js_chars": sum(int(r.get("js_chars", 0)) for r in rows),
        "hot_approx_tokens": "NOT_OBSERVABLE",
        "guidance_delivery": guidance,
        "mandatory_full_read": mandatory_rows,
        "mandatory_full_read_js_chars": sum(int(r.get("js_chars", 0)) for r in mandatory_rows),
    }


def inventory() -> dict[str, object]:
    control = summarize("CONTROL_H2", HOT_SURFACES_CONTROL, MANDATORY_READ_CONTROL)
    variant = summarize("VARIANT_H2", HOT_SURFACES_VARIANT, MANDATORY_READ_VARIANT)
    red = control["guidance_delivery"]
    grn = variant["guidance_delivery"]
    red_vis = int(red.get("visible_js_chars", 0))
    grn_vis = int(grn.get("visible_js_chars", 0))
    return {
        "profile": {
            "MAX_GUIDANCE_CHARS": MAX_GUIDANCE_CHARS,
            "GUIDANCE_FILES": GUIDANCE_FILES,
            "source": "deployment/BOOTSTRAP_CONTRACT.md §1 (profile fact, not a cross-version constant)",
            "note": "H2 delivers both arms' guidance heads in FULL via the run contract; "
                    "the 8000-char cap is recorded as the canonical-channel context, not as a treatment.",
        },
        "control": control,
        "variant": variant,
        "reduction": {
            "hot_js_chars_control": control["hot_js_chars"],
            "hot_js_chars_variant": variant["hot_js_chars"],
            "hot_reduction_percent": _pct(control["hot_js_chars"], variant["hot_js_chars"]),
            "guidance_visible_control": red_vis,
            "guidance_visible_variant": grn_vis,
            "guidance_visible_reduction_percent": _pct(red_vis, grn_vis),
            "variant_fully_delivered": not grn.get("truncated_headings") and not grn.get("cut_line"),
        },
        "token_usage": "NOT_OBSERVABLE",
    }


def _pct(base: int, after: int) -> str:
    if base == 0:
        return "UNDEFINED_BASE_ZERO"
    return f"{(base - after) * 100.0 / base:.1f}"


def selftest() -> int:
    """反例自检：截断算术、单位区分、两臂不变式。"""
    failures: list[str] = []

    # T1 js_chars 与 byte/char 的区分——astral 字符按 2 计
    if js_chars("a") != 1:
        failures.append("T1a: ascii js_chars != 1")
    if js_chars("\U0001F600") != 2:
        failures.append("T1b: astral char must count 2 UTF-16 units")

    # T2 行粒度截断算术（合成输入）
    one_line = "x" * MAX_GUIDANCE_CHARS
    if _visible_js_chars_for(one_line, MAX_GUIDANCE_CHARS) != 0:
        failures.append("T2a: a line landing exactly on the limit is dropped whole")
    if _dropped_js_chars_for(one_line, MAX_GUIDANCE_CHARS) != MAX_GUIDANCE_CHARS:
        failures.append("T2b: exact-limit single line must be dropped entirely")
    small = "x" * (MAX_GUIDANCE_CHARS - 1)
    if _dropped_js_chars_for(small, MAX_GUIDANCE_CHARS) != 0:
        failures.append("T2c: input below the limit must drop nothing")
    body = "x\n" * (MAX_GUIDANCE_CHARS // 2 + 10)
    total, visible = js_chars(body), _visible_js_chars_for(body, MAX_GUIDANCE_CHARS)
    if _dropped_js_chars_for(body, MAX_GUIDANCE_CHARS) != max(0, total - visible):
        failures.append("T2d: dropped must be total - visible for multi-line input")
    long_line = "x" * (MAX_GUIDANCE_CHARS // 2) + "\n"
    body = long_line * 4
    acc, overflow = 0, None
    for line in body.splitlines(keepends=True):
        prev = acc
        acc += js_chars(line)
        if prev < MAX_GUIDANCE_CHARS <= acc:
            overflow = acc - MAX_GUIDANCE_CHARS
            break
    dropped = _dropped_js_chars_for(body, MAX_GUIDANCE_CHARS)
    if overflow is None or dropped <= overflow:
        failures.append(
            f"T2e: dropped tail ({dropped}) must exceed the cut line's own overflow ({overflow})"
        )

    inv = inventory()
    ctl = inv["control"]["guidance_delivery"]
    grn = inv["variant"]["guidance_delivery"]

    # T3 control 的 AGENTS.md 截断事实（profile 回归）
    if not ctl.get("exists") or not grn.get("exists"):
        failures.append("T3: control/variant guidance files must exist at their declared paths")
    else:
        if not ctl["cut_line"]:
            failures.append("T3a: control AGENTS.md expected to be truncated at 8000")
        if ctl["dropped_js_chars"] <= 0:
            failures.append("T3b: control dropped_js_chars must be > 0")
        if ctl["dropped_js_chars"] != max(0, ctl["total_js_chars"] - ctl["visible_js_chars"]):
            failures.append("T3c: dropped_js_chars must equal total - visible (file-scoped)")

    # T4 variant 完整投递（不截断）——变体存在的前提
    if not inv["reduction"]["variant_fully_delivered"]:
        failures.append("T4: variant guidance head must be fully delivered")

    # T5 token 不得被估算
    if inv["token_usage"] != "NOT_OBSERVABLE":
        failures.append("T5: token usage must stay NOT_OBSERVABLE")
    if inv["control"]["hot_approx_tokens"] != "NOT_OBSERVABLE":
        failures.append("T5b: hot_approx_tokens must stay NOT_OBSERVABLE")

    # T6 lean 必须严格小于 control
    if int(inv["variant"]["hot_js_chars"]) >= int(inv["control"]["hot_js_chars"]):
        failures.append("T6: variant hot_js_chars must be < control")

    # T7 两臂都强制读 RULES.md（H2 口径）
    if inv["variant"]["mandatory_full_read_js_chars"] <= 0:
        failures.append("T7: variant mandatory read (RULES.md) must be present in the metric")

    for f in failures:
        print(f"FAIL {f}")
    print(f"selftest: {'PASS' if not failures else 'FAIL'} ({len(failures)} failures)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--selftest", action="store_true", help="run counterexample checks")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    inv = inventory()
    if args.json:
        print(json.dumps(inv, ensure_ascii=False, indent=2))
        return 0

    c, v, r = inv["control"], inv["variant"], inv["reduction"]
    print("=== H2 HOT inventory (profile: MAX_GUIDANCE_CHARS=8000) ===\n")
    for arm, data in (("CONTROL_H2", c), ("VARIANT_H2", v)):
        print(f"[{arm}]")
        for row in data["hot_surfaces"]:
            if row.get("exists"):
                print(
                    f"   {row['path']:64s} lines={row['lines']:4d} "
                    f"bytes={row['bytes']:6d} js={row['js_chars']:6d} "
                    f"trunc8000={'Y' if row['truncated_at_8000'] else 'n'}"
                )
            else:
                print(f"   {row['path']:64s} MISSING")
        print(
            f"   TOTAL lines={data['hot_lines']} bytes={data['hot_bytes']} "
            f"js_chars={data['hot_js_chars']} tokens={data['hot_approx_tokens']}"
        )
        g = data["guidance_delivery"]
        print(
            f"   guidance delivery: visible_lines={g.get('visible_lines')}/"
            f"{g.get('total_lines')} visible_js={g.get('visible_js_chars')} "
            f"dropped_js={g.get('dropped_js_chars')}"
        )
        for h in g.get("truncated_headings", []):
            print(f"      TRUNCATED SECTION: {h}")
        print(f"   mandatory full-read: {data['mandatory_full_read'] or 'none'}")
        print()
    print("=== reduction ===")
    print(f"   hot js_chars: {r['hot_js_chars_control']} -> {r['hot_js_chars_variant']}"
          f"  ({r['hot_reduction_percent']}%)")
    print(f"   guidance visible js: {r['guidance_visible_control']} ->"
          f" {r['guidance_visible_variant']}  ({r['guidance_visible_reduction_percent']}%)")
    print(f"   variant fully delivered: {r['variant_fully_delivered']}")
    print(f"   token usage: {inv['token_usage']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
