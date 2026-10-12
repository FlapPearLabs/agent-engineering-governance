#!/usr/bin/env python3
"""H2 HOT-surface inventory + truncation oracle（非 canonical；H2 实验材料）。

与 H1 的 hot_inventory.py 同一单位口径（js_chars / TOKENS=NOT_OBSERVABLE），
但截断语义按 **v2（bot-review 修正）** 建模：

  运行时实测（`audit/AS_IS_WORKBUDDY_V3.md:29`）= `raw.slice(0, MAX_GUIDANCE_CHARS)`
  —— **字符级**前缀（保留跨界行的部分内容），其后整体丢弃。
  本脚本以该语义为主口径（`visible_js_chars` / `dropped_js_chars`）；
  H1 的**行粒度**算法保留为标注为 secondary 的对照字段（`line_granular_*`），
  仅供与 H1 已发布数字对照，不再用于本实验的结论口径。

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
H2_DIR = Path(__file__).resolve().parent
HARNESS = H2_DIR / "harness"

MAX_GUIDANCE_CHARS = 8000  # profile 事实（BOOTSTRAP_CONTRACT §1；非跨版本常数）
GUIDANCE_FILES = ["CODEBUDDY.md", ".codebuddy/CODEBUDDY.md", "AGENTS.md"]

# R11-4: the control arm does NOT receive bare AGENTS.md — prepare_run.sh delivers
# control-carrier-header.md + AGENTS.md (verbatim) + control-carrier-footer.md AS
# CODEBUDDY.md. The measured control surface must therefore be those composed bytes;
# the wrapper files are read from the same paths preparation uses, so the two can
# never drift (no duplicated literals).
CONTROL_CARRIER_PARTS = [
    HARNESS / "control-carrier-header.md",
    REPO_ROOT / "AGENTS.md",
    HARNESS / "control-carrier-footer.md",
]

HOT_SURFACES_CONTROL = [
    ("MEMORY_POINTER", "deployment/MEMORY_POINTER_CANDIDATE.md"),
]
HOT_SURFACES_VARIANT = [
    ("MEMORY_POINTER", "deployment/MEMORY_POINTER_CANDIDATE.md"),
]

MANDATORY_READ_CONTROL = ["RULES.md"]
MANDATORY_READ_VARIANT = ["RULES.md"]  # H2：两臂都读同版 RULES.md（差异只在 guidance 载体）


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


def _char_slice_prefix(text: str, limit: int) -> str:
    """Primary semantics: `raw.slice(0, limit)` in UTF-16 units.

    Accumulates whole characters; a character whose units would cross the limit is NOT
    included (the runtime may split an astral pair mid-way; we stop before it — the only
    divergence is a lone surrogate at the boundary, which no repo file exercises).
    """
    acc = 0
    out = []
    for ch in text:
        u = 2 if ord(ch) > 0xFFFF else 1
        if acc + u > limit:
            break
        acc += u
        out.append(ch)
    return "".join(out)


def _line_granular_visible_for(text: str, limit: int) -> str:
    """Secondary (H1 comparability): whole lines only; a line reaching the limit exactly is
    still dropped whole (H1 arithmetic: prev < limit <= acc ⇒ crossing line dropped)."""
    acc = 0
    visible_lines = []
    for line in text.splitlines(keepends=True):
        prev = acc
        acc += js_chars(line)
        if prev < limit <= acc:
            break
        visible_lines.append(line)
    return "".join(visible_lines)


def guidance_prefix(rel_path: str, limit: int = MAX_GUIDANCE_CHARS) -> dict[str, object]:
    path = REPO_ROOT / rel_path
    if not path.is_file():
        return {"path": rel_path, "exists": False}
    return guidance_prefix_bytes(path.read_text(encoding="utf-8"), rel_path, limit)


def guidance_prefix_bytes(text: str, label: str, limit: int = MAX_GUIDANCE_CHARS) -> dict[str, object]:
    """Truncation arithmetic over already-loaded text (R11-4: the control arm's delivered
    carrier is a COMPOSITION, so the measurement must accept composed bytes, not only a
    single repo-relative file)."""
    visible = _char_slice_prefix(text, limit)
    lg_visible = _line_granular_visible_for(text, limit)

    lines = text.splitlines(keepends=True)
    acc = 0
    cut_line = None
    for idx, line in enumerate(lines, start=1):
        prev = acc
        acc += js_chars(line)
        if prev < limit <= acc:
            cut_line = idx
            break
    tail = "".join(lines[(cut_line - 1) if cut_line else len(lines):])
    return {
        "path": label,
        "exists": True,
        "semantics": "char_slice(0, limit) per audit/AS_IS_WORKBUDDY_V3.md; line_granular_* is H1 comparability only",
        "total_lines": len(lines),
        "total_js_chars": js_chars(text),
        "cut_line": cut_line,
        "visible_js_chars": js_chars(visible),
        "dropped_js_chars": max(0, js_chars(text) - js_chars(visible)),
        "line_granular_visible_js_chars": js_chars(lg_visible),
        "line_granular_dropped_js_chars": max(0, js_chars(text) - js_chars(lg_visible)),
        "visible_headings": [
            ln.strip() for ln in visible.splitlines() if re.match(r"^#{1,2} ", ln)
        ],
        "truncated_headings": [
            ln.strip() for ln in tail.splitlines() if re.match(r"^#{1,2} ", ln)
        ],
    }


def control_carrier_bytes() -> str | None:
    """The exact bytes prepare_run.sh writes to CODEBUDDY.md for the control arm."""
    try:
        blobs = [p.read_bytes() for p in CONTROL_CARRIER_PARTS]
    except OSError:
        return None
    return b"".join(blobs).decode("utf-8")


def summarize(
    name: str,
    surfaces: list[tuple[str, str]],
    mandatory: list[str],
    guidance_text: str | None,
    guidance_label: str,
) -> dict:
    rows = [measure(p) for _, p in surfaces]
    if guidance_text is None:
        guidance = {"path": guidance_label, "exists": False}
        carrier_js = 0
    else:
        guidance = guidance_prefix_bytes(guidance_text, guidance_label)
        carrier_js = int(guidance["total_js_chars"])
    mandatory_rows = [measure(p) for p in mandatory]
    # The guidance carrier IS part of the HOT surface in both arms; it is listed separately in
    # guidance_delivery (with its truncation arithmetic) but counted in the arm totals, so
    # hot_js_chars keeps its original meaning (R11-4 changed the control BYTES, not the metric).
    carrier_row = {
        "path": guidance_label,
        "exists": guidance_text is not None,
        "lines": int(guidance.get("total_lines", 0)),
        "bytes": len(guidance_text.encode("utf-8")) if guidance_text is not None else 0,
        "js_chars": carrier_js,
        "truncated_at_8000": carrier_js > MAX_GUIDANCE_CHARS,
        "budget_capped_js_chars": min(carrier_js, MAX_GUIDANCE_CHARS),
        "tokens": "NOT_OBSERVABLE",
        "composition": "header + AGENTS.md(verbatim) + footer" if guidance_text is not None else None,
    }
    rows = rows + [carrier_row]
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
    ctl_carrier = control_carrier_bytes()
    ctl_label = " + ".join(
        str(p.relative_to(REPO_ROOT)) if p.is_relative_to(REPO_ROOT) else str(p)
        for p in CONTROL_CARRIER_PARTS
    )
    var_label = "experiments/v1.2/h2-lazy-disclosure/carriers/H2_LEAN_BOOTSTRAP.md"
    var_path = REPO_ROOT / var_label
    var_text = var_path.read_text(encoding="utf-8") if var_path.is_file() else None
    control = summarize("CONTROL_H2", HOT_SURFACES_CONTROL, MANDATORY_READ_CONTROL,
                        ctl_carrier, ctl_label)
    variant = summarize("VARIANT_H2", HOT_SURFACES_VARIANT, MANDATORY_READ_VARIANT,
                        var_text, var_label)
    red = control["guidance_delivery"]
    grn = variant["guidance_delivery"]
    red_vis = int(red.get("visible_js_chars", 0))
    grn_vis = int(grn.get("visible_js_chars", 0))
    return {
        "profile": {
            "MAX_GUIDANCE_CHARS": MAX_GUIDANCE_CHARS,
            "GUIDANCE_FILES": GUIDANCE_FILES,
            "source": "deployment/BOOTSTRAP_CONTRACT.md §1 (profile fact, not a cross-version constant)",
            "truncation_model": "char-exact raw.slice(0, MAX) per audit/AS_IS_WORKBUDDY_V3.md:29",
            "note": "H2 delivers both arms' guidance heads in FULL via placed copies; the "
                    "8000-char cap is recorded as the canonical-channel context, not as a treatment.",
        },
        "control": control,
        "variant": variant,
        "reduction": {
            "hot_js_chars_control": control["hot_js_chars"],
            "hot_js_chars_variant": variant["hot_js_chars"],
            "hot_reduction_percent": _pct(control["hot_js_chars"], variant["hot_js_chars"]),
            "carrier_js_chars_control": int(red.get("total_js_chars", 0)),
            "carrier_js_chars_variant": int(grn.get("total_js_chars", 0)),
            "carrier_reduction_percent": _pct(int(red.get("total_js_chars", 0)),
                                              int(grn.get("total_js_chars", 0))),
            "carrier_reduction_note": "reduction is computed over the DELIVERED guidance carriers only; the host-injected MEMORY pointer text is not observable per run and is excluded (bot review R9-12)",
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
    """反例自检：字符级截断语义（v2）、单位区分、两臂不变式。"""
    failures: list[str] = []

    # T1 js_chars 与 byte/char 的区分——astral 字符按 2 计
    if js_chars("a") != 1:
        failures.append("T1a: ascii js_chars != 1")
    if js_chars("\U0001F600") != 2:
        failures.append("T1b: astral char must count 2 UTF-16 units")

    # T2 字符级截断（v2）：单行 8000 字符必须**完整可见**（bot review 反例）
    one_line = "x" * MAX_GUIDANCE_CHARS
    if js_chars(_char_slice_prefix(one_line, MAX_GUIDANCE_CHARS)) != MAX_GUIDANCE_CHARS:
        failures.append("T2a: a single 8000-char line must be delivered in full (char slice)")
    if js_chars(one_line) - js_chars(_char_slice_prefix(one_line, MAX_GUIDANCE_CHARS)) != 0:
        failures.append("T2b: exact-limit single line must drop nothing under char slice")
    # 7999 → 无丢弃
    small = "x" * (MAX_GUIDANCE_CHARS - 1)
    if js_chars(small) - js_chars(_char_slice_prefix(small, MAX_GUIDANCE_CHARS)) != 0:
        failures.append("T2c: input below the limit must drop nothing")
    # 多行：visible == limit（纯 ASCII），dropped == total - limit
    body = "x\n" * (MAX_GUIDANCE_CHARS // 2 + 10)
    visible_units = js_chars(_char_slice_prefix(body, MAX_GUIDANCE_CHARS))
    if visible_units != MAX_GUIDANCE_CHARS:
        failures.append("T2d: char slice must deliver exactly the limit in units (ascii input)")
    if js_chars(body) - visible_units != max(0, js_chars(body) - MAX_GUIDANCE_CHARS):
        failures.append("T2e: dropped must equal total - limit under char slice")
    # astral 边界：一个 2-unit 字符不得被劈开计入
    pairy = "\U0001F600" * 10  # 20 units
    got = js_chars(_char_slice_prefix(pairy, 5))  # 5 units → 2 chars = 4 units (5th unit would split)
    if got != 4:
        failures.append(f"T2f: astral pair must not be split by the slice (got {got}, want 4)")
    # secondary（H1 对照）行粒度行为保留
    if js_chars(_line_granular_visible_for(one_line, MAX_GUIDANCE_CHARS)) != 0:
        failures.append("T2g: line-granular secondary must still drop the crossing line whole")

    inv = inventory()
    ctl = inv["control"]["guidance_delivery"]
    grn = inv["variant"]["guidance_delivery"]

    # T3 control 的 AGENTS.md 截断事实（字符级口径）
    if not ctl.get("exists") or not grn.get("exists"):
        failures.append("T3: control/variant guidance files must exist at their declared paths")
    else:
        if not ctl["cut_line"]:
            failures.append("T3a: control AGENTS.md expected to be truncated at 8000")
        if ctl["dropped_js_chars"] <= 0:
            failures.append("T3b: control dropped_js_chars must be > 0")
        if ctl["visible_js_chars"] != MAX_GUIDANCE_CHARS:
            failures.append("T3c: control visible_js_chars must equal the char-slice limit")
        if ctl["dropped_js_chars"] != max(0, ctl["total_js_chars"] - ctl["visible_js_chars"]):
            failures.append("T3d: dropped_js_chars must equal total - visible")

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

    # T7 两臂都强制读同版 RULES.md（H2 口径）
    if inv["variant"]["mandatory_full_read_js_chars"] <= 0:
        failures.append("T7: variant mandatory read (RULES.md) must be present in the metric")

    # T8 carrier-only reduction is the S1 surface (R9-12) and must clear the 30% floor
    red = inv["reduction"]
    if int(red["carrier_js_chars_variant"]) >= int(red["carrier_js_chars_control"]):
        failures.append("T8: carrier reduction must be negative-sized (variant < control)")
    if float(red["carrier_reduction_percent"]) < 30.0:
        failures.append("T8b: carrier reduction must clear the preregistered 30% floor")

    # T9 (R11-4): the measured control surface is the COMPOSED carrier actually delivered as
    # CODEBUDDY.md — it must contain the verbatim AGENTS.md bytes plus BOTH wrapper parts, and
    # its js_chars must equal their exact sum. A bare-AGENTS measurement would fail here.
    ctl_text = control_carrier_bytes()
    if ctl_text is None:
        failures.append("T9a: control carrier composition must be readable")
    else:
        parts = [p.read_bytes() for p in CONTROL_CARRIER_PARTS]
        if ctl_text.encode("utf-8") != b"".join(parts):
            failures.append("T9b: composed control carrier must equal header+AGENTS+footer bytes")
        agents_bytes = (REPO_ROOT / "AGENTS.md").read_bytes()
        if agents_bytes not in ctl_text.encode("utf-8"):
            failures.append("T9c: composed control carrier must embed AGENTS.md verbatim")
        if js_chars(ctl_text) != sum(
            js_chars(part.read_text(encoding="utf-8")) for part in CONTROL_CARRIER_PARTS
        ):
            failures.append("T9d: composed carrier js_chars must equal the sum of its parts")
        if js_chars(ctl_text) <= js_chars((REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")):
            failures.append("T9e: composed carrier must be strictly larger than bare AGENTS.md")

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
    print("=== H2 HOT inventory (profile: MAX_GUIDANCE_CHARS=8000; char-slice semantics) ===\n")
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
            f"   guidance delivery (char-slice): visible_js={g.get('visible_js_chars')} "
            f"dropped_js={g.get('dropped_js_chars')} cut_line={g.get('cut_line')} "
            f"[line-granular secondary: visible_js={g.get('line_granular_visible_js_chars')}]"
        )
        for h in g.get("truncated_headings", []):
            print(f"      TRUNCATED SECTION: {h}")
        print(f"   mandatory full-read: {data['mandatory_full_read'] or 'none'}")
        print()
    print("=== reduction ===")
    print(f"   hot js_chars: {r['hot_js_chars_control']} -> {r['hot_js_chars_variant']}"
          f"  ({r['hot_reduction_percent']}%)")
    print(f"   guidance visible js (char-slice): {r['guidance_visible_control']} ->"
          f" {r['guidance_visible_variant']}  ({r['guidance_visible_reduction_percent']}%)")
    print(f"   variant fully delivered: {r['variant_fully_delivered']}")
    print(f"   token usage: {inv['token_usage']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
