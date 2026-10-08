#!/usr/bin/env python3
"""Minimal stdlib integrity check for H3-B live-shadow observations.

Deliberately small (no schema framework): validates that
`observations.jsonl` is parseable and carries the experiment's invariants:

  * one JSON object per non-blank line;
  * observation_id unique and well-formed (h3b-NNN);
  * base_sha / candidate_sha are non-empty 40-hex SHAs;
  * normal_evidence_frozen is true;
  * shadow_influenced_normal_review is false;
  * value_disposition is inside the declared vocabulary;
  * shadow_signals carries exactly the three frozen v1 signals (ints >= 0).

It does not generate, repair, or judge anything. Exit code 0 when clean.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

DISPOSITIONS = {
    "NO_SIGNAL",
    "DUPLICATE_OF_NORMAL_EVIDENCE",
    "NON_ACTIONABLE_STRUCTURE_FACT",
    "UNIQUE_LOW_VALUE_INFORMATION",
    "UNIQUE_HIGH_VALUE_FINDING",
    "UNINTERPRETABLE",
}
SIGNALS = ("NEW_FILE", "NEW_DIRECTORY", "NEW_DEPENDENCY")
ID_RE = re.compile(r"h3b-\d{3}")
SHA_RE = re.compile(r"[0-9a-f]{40}")


def check(path: Path) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    count = 0
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        count += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {lineno}: not valid JSON: {exc}")
            continue
        oid = record.get("observation_id", "")
        if not ID_RE.fullmatch(str(oid)):
            errors.append(f"line {lineno}: bad observation_id {oid!r}")
        elif oid in seen:
            errors.append(f"line {lineno}: duplicate observation_id {oid!r}")
        else:
            seen.add(oid)
        for field in ("base_sha", "candidate_sha"):
            value = str(record.get(field, ""))
            if not SHA_RE.fullmatch(value):
                errors.append(f"line {lineno}: {field} is not a 40-hex SHA: {value!r}")
        if record.get("normal_evidence_frozen") is not True:
            errors.append(f"line {lineno}: normal_evidence_frozen is not true")
        if record.get("shadow_influenced_normal_review") is not False:
            errors.append(f"line {lineno}: shadow_influenced_normal_review is not false")
        if record.get("value_disposition") not in DISPOSITIONS:
            errors.append(
                f"line {lineno}: unknown value_disposition {record.get('value_disposition')!r}"
            )
        signals = record.get("shadow_signals")
        if not isinstance(signals, dict) or tuple(signals.keys()) != SIGNALS:
            errors.append(
                f"line {lineno}: shadow_signals must be exactly {SIGNALS}, got {signals!r}"
            )
        elif not all(isinstance(v, int) and v >= 0 for v in signals.values()):
            errors.append(f"line {lineno}: shadow_signals values must be non-negative ints")
    return errors, count


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name(
        "observations.jsonl"
    )
    if not path.exists():
        print(f"CHECK_FAIL: {path} not found")
        return 1
    errors, count = check(path)
    print(f"OBSERVATIONS={count}")
    for error in errors:
        print(f"ERROR: {error}")
    print("CHECK=PASS" if not errors else "CHECK=FAIL")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
