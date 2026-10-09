#!/usr/bin/env python3
"""H1 HOT-surface inventory + truncation oracle（非 canonical；H1 实验材料）。

本脚本只做**机械计量**，不做语义裁决、不改 canonical、不接 CI。

它回答一个问题：当前 V1.1.1 默认治理面在 agent 启动时**实际**能看到什么，
以及把 HOT 换成 lean variant 后体量如何变化。

计量单位（严格区分，不得互相换算）：

  LINES        = 物理行数
  BYTES        = UTF-8 编码字节数
  JS_CHARS     = JavaScript string length（UTF-16 code units）
                 —— 这是 BOOTSTRAP_CONTRACT.md §1 的截断计量单位
  TOKENS_*     = **NOT_OBSERVABLE**（见 experiments/v1.2/metrics.md：
                 当前 runtime 无可靠 token 计量面，禁止由字符数估算）

截断 oracle：MAX_GUIDANCE_CHARS = 8000（BOOTSTRAP_CONTRACT.md §1，profile 事实：
WorkBuddy 5.5.3，2026-09-04 观测；非跨版本常数）。本脚本按该 profile 重算
「guidance 通道实际投递多少」，用于对比 control 与 lean variant 的**可见性**，
而不是断言任何 runtime 的真实行为。

用法：
    python3 hot_inventory.py            # 打印 inventory 表 + 截断算术
    python3 hot_inventory.py --json     # 机器可读输出
    python3 hot_inventory.py --selftest # 反例自检（截断算术 / 单位区分）
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EXPERIMENT_DIR = Path(__file__).resolve().parent

# --- 观测 profile 常量（owner = deployment/BOOTSTRAP_CONTRACT.md §1）-----------
MAX_GUIDANCE_CHARS = 8000
GUIDANCE_FILES = ["CODEBUDDY.md", ".codebuddy/CODEBUDDY.md", "AGENTS.md"]

# --- HOT 面清单（control = 当前 canonical；variant = H1 lean bootstrap）--------
HOT_SURFACES_CONTROL = [
    ("MEMORY_POINTER", "deployment/MEMORY_POINTER_CANDIDATE.md"),
    ("GUIDANCE_HEAD", "AGENTS.md"),
]
HOT_SURFACES_VARIANT = [
    ("MEMORY_POINTER", "deployment/MEMORY_POINTER_CANDIDATE.md"),
    ("GUIDANCE_HEAD", "experiments/v1.2/h1-hot-context/lean/CODEBUDDY.md"),
]

# 随 bootstrap 强制全文读取的面（不是自动注入，但是强制阅读义务）
MANDATORY_READ_CONTROL = ["RULES.md"]
MANDATORY_READ_VARIANT: list[str] = []  # lean variant 改为按路由加载


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
        # Deliberately NOT named `visible_js_chars`: that name is used by
        # `guidance_prefix()` for the *delivered* prefix (7,840 for AGENTS.md),
        # whereas this field is the *budget-capped* size (8,000). Two different
        # quantities must not share a key name in the same JSON payload.
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
    """被丢弃的尾部总量 = 总量 - 可见量。

    刻意与 `guidance_prefix` 共用同一算术定义，使 selftest 能在合成输入上
    独立钉住该语义（`acc - limit` 只量截断行溢出，量不到尾部）。
    """
    return max(0, js_chars(text) - _visible_js_chars_for(text, limit))


def guidance_prefix(rel_path: str, limit: int = MAX_GUIDANCE_CHARS) -> dict[str, object]:
    """重算 guidance 通道的可见前缀（逐行累计到 limit 为止）。"""
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
        # The whole tail is dropped, not just the overflow of the cut line.
        # `acc - limit` measures only how far the cut line overshoots the
        # budget (59 chars for AGENTS.md) and understates the loss by ~100x.
        # The delivery-drops-the-remainder semantics is what the truncation
        # claim rests on, so it must be total - visible.
        "dropped_js_chars": max(0, js_chars(text) - js_chars(visible)),
        "visible_headings": [
            ln.strip()
            for ln in visible.splitlines()
            if re.match(r"^#{1,2} ", ln)
        ],
        "truncated_headings": [
            ln.strip()
            for ln in "".join(lines[(cut_line - 1) if cut_line else len(lines) :]).splitlines()
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
        "mandatory_full_read_js_chars": sum(
            int(r.get("js_chars", 0)) for r in mandatory_rows
        ),
    }


def inventory() -> dict[str, object]:
    control = summarize("CONTROL", HOT_SURFACES_CONTROL, MANDATORY_READ_CONTROL)
    variant = summarize("H1_LEAN", HOT_SURFACES_VARIANT, MANDATORY_READ_VARIANT)
    red = control["guidance_delivery"]
    grn = variant["guidance_delivery"]
    red_vis = int(red.get("visible_js_chars", 0))
    grn_vis = int(grn.get("visible_js_chars", 0))
    return {
        "profile": {
            "MAX_GUIDANCE_CHARS": MAX_GUIDANCE_CHARS,
            "GUIDANCE_FILES": GUIDANCE_FILES,
            "source": "deployment/BOOTSTRAP_CONTRACT.md §1 (WorkBuddy 5.5.3, 2026-09-04)",
            "is_profile_fact_not_constant": True,
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
            "variant_fully_delivered": not grn.get("truncated_headings")
            and not grn.get("cut_line"),
        },
        "token_usage": "NOT_OBSERVABLE",
    }


def _pct(base: int, after: int) -> str:
    if base == 0:
        return "UNDEFINED_BASE_ZERO"
    return f"{(base - after) * 100.0 / base:.1f}"


def selftest() -> int:
    """反例自检：截断算术、单位区分、变体完整性。"""
    failures: list[str] = []

    # T1: js_chars 与 byte/char 的区分—— astral 字符按 2 计
    if js_chars("a") != 1:
        failures.append("T1a: ascii js_chars != 1")
    if js_chars("\U0001F600") != 2:
        failures.append("T1b: astral char must count 2 UTF-16 units")

    # T2: 截断算术在**已知答案**的合成输入上验证。
    # 这一项曾被写成 `del g, exact`（空转），其后果是：真实文件上
    # `dropped_js_chars` 被实现成「截断行自身的溢出量」（AGENTS.md = 59），
    # 而非「被丢弃的整个尾部」（= 5,916），长达一整轮无人发现。
    # 合成算术不是冗余：它是唯一能在不依赖仓内文件的前提下钉住该语义的检查。
    #
    # 语义 = **行粒度**：截断发生在第一个累计越限的行，该行**整行**丢弃，
    # 其后所有行一并丢弃。因此单行恰好等于 limit 时该行仍被丢弃。
    one_line = "x" * MAX_GUIDANCE_CHARS
    if _visible_js_chars_for(one_line, MAX_GUIDANCE_CHARS) != 0:
        failures.append("T2a: a line landing exactly on the limit is dropped whole")
    if _dropped_js_chars_for(one_line, MAX_GUIDANCE_CHARS) != MAX_GUIDANCE_CHARS:
        failures.append("T2b: exact-limit single line must be dropped entirely")
    # 无换行、长度远小于 limit ⇒ 无截断，丢弃为 0
    small = "x" * (MAX_GUIDANCE_CHARS - 1)
    if _dropped_js_chars_for(small, MAX_GUIDANCE_CHARS) != 0:
        failures.append("T2c: input below the limit must drop nothing")
    # 多行输入下，丢弃量恒等于「总量 - 可见量」——本项直接钉住该恒等式
    body = "x\n" * (MAX_GUIDANCE_CHARS // 2 + 10)
    total,visible = js_chars(body), _visible_js_chars_for(body, MAX_GUIDANCE_CHARS)
    if _dropped_js_chars_for(body, MAX_GUIDANCE_CHARS) != max(0, total - visible):
        failures.append("T2d: dropped must be total - visible for multi-line input")
    # 关键反例：多行输入下 `acc - limit`（截断行溢出量）必须与丢弃总量**不同**。
    # 二者若相等，说明实现退化回了那个 59 字符的缺陷语义。
    # 守卫直接对比两个实测量，不拿 limit 做代理（短行文件的尾部可以合法地
    # 小于 limit，那种样本无法区分二者——上一版正是这样误报的）。
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
            f"T2e: dropped tail ({dropped}) must exceed the cut line's own "
            f"overflow ({overflow}); the two quantities are being conflated"
        )

    # T3: control 的 AGENTS.md 必须被截断（profile 事实的回归）
    inv = inventory()
    ctl = inv["control"]["guidance_delivery"]
    if not ctl["cut_line"]:
        failures.append("T3: control AGENTS.md expected to be truncated at 8000")
    if ctl["dropped_js_chars"] <= 0:
        failures.append("T3b: control dropped_js_chars must be > 0")
    # T3c: 丢弃量 == 该文件总量 - 可见量。口径必须是**文件自身**
    # （AGENTS.md 13,756），不是臂合计（含 MEMORY_POINTER 2,028）。
    if ctl["dropped_js_chars"] != max(0, ctl["total_js_chars"] - ctl["visible_js_chars"]):
        failures.append(
            f"T3c: dropped_js_chars={ctl['dropped_js_chars']} != "
            f"total-visible={ctl['total_js_chars'] - ctl['visible_js_chars']}"
        )

    # T4: variant 必须完整投递（不截断）——这是 lean variant 的存在前提
    if not inv["reduction"]["variant_fully_delivered"]:
        failures.append("T4: variant guidance head must be fully delivered")

    # T5: token 不得被估算
    if inv["token_usage"] != "NOT_OBSERVABLE":
        failures.append("T5: token usage must stay NOT_OBSERVABLE")
    if inv["control"]["hot_approx_tokens"] != "NOT_OBSERVABLE":
        failures.append("T5b: hot_approx_tokens must stay NOT_OBSERVABLE")

    # T6: lean 必须严格小于 control（否则 variant 无意义）
    if int(inv["variant"]["hot_js_chars"]) >= int(inv["control"]["hot_js_chars"]):
        failures.append("T6: variant hot_js_chars must be < control")

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
    print("=== H1 HOT inventory (profile: MAX_GUIDANCE_CHARS=8000) ===\n")
    for arm, data in (("CONTROL", c), ("H1_LEAN", v)):
        print(f"[{arm}]")
        for row in data["hot_surfaces"]:
            if row.get("exists"):
                print(
                    f"   {row['path']:58s} lines={row['lines']:4d} "
                    f"bytes={row['bytes']:6d} js={row['js_chars']:6d} "
                    f"trunc8000={'Y' if row['truncated_at_8000'] else 'n'}"
                )
            else:
                print(f"   {row['path']:58s} MISSING")
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
        print(f"   mandatory full-read: {data['mandatory_full_read'] or 'none (routed)'}")
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
