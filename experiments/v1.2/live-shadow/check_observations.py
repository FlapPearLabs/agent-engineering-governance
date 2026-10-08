#!/usr/bin/env python3
"""Minimal stdlib integrity check for H3-B0/H3-B1 live-shadow observations.

Deliberately small (no schema framework): validates that
`observations.jsonl` is parseable and carries the experiment's invariants:

  * one JSON object per non-blank line; observation_id unique;
    RETROSPECTIVE rows use h3b-NNN ids, PROSPECTIVE rows use h3b1-NNN ids
    (the mode/prefix pairing keeps the retrospective calibration forever
    separable from the prospective collection);
  * base_sha / candidate_sha are non-empty 40-hex SHAs;
  * normal_evidence_frozen is true;
  * shadow_influenced_normal_workflow is false;
  * shadow_signals carries exactly the three frozen v1 signals with
    non-negative int counts (booleans rejected);
  * signal_dispositions carries one disposition per signal (vocabulary-checked)
    with the cross-field invariant (count == 0) <=> (disposition == NO_SIGNAL);
  * a UNIQUE_HIGH_VALUE_FINDING disposition requires a non-empty
    what_decision_would_change;
  * PROSPECTIVE rows carry normal_evidence_frozen_at < shadow_first_run_at
    (ISO-8601 with UTC offset) as the freeze-before-shadow ordering evidence.

It does not generate, repair, or judge anything. Exit code 0 when clean.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
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
MODES = ("RETROSPECTIVE", "PROSPECTIVE")
ID_RE = {
    "RETROSPECTIVE": re.compile(r"h3b-\d{3}"),
    "PROSPECTIVE": re.compile(r"h3b1-\d{3}"),
}
SHA_RE = re.compile(r"[0-9a-f]{40}")


def _timestamp(value: object, lineno: int, field: str, errors: list[str]):
    if not isinstance(value, str) or not value.strip():
        errors.append(f"line {lineno}: {field} missing or not a string: {value!r}")
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        errors.append(f"line {lineno}: {field} is not ISO-8601: {value!r}")
        return None
    if parsed.tzinfo is None:
        errors.append(f"line {lineno}: {field} must carry a UTC offset: {value!r}")
        return None
    return parsed


def check(path: Path):
    errors: list[str] = []
    seen: set[str] = set()
    counts = {"RETROSPECTIVE": 0, "PROSPECTIVE": 0}
    total = 0
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        total += 1
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {lineno}: not valid JSON: {exc}")
            continue
        mode = record.get("mode")
        if mode not in MODES:
            errors.append(f"line {lineno}: unknown mode {mode!r}")
        else:
            counts[mode] += 1
        oid = str(record.get("observation_id", ""))
        if mode in ID_RE and not ID_RE[mode].fullmatch(oid):
            errors.append(
                f"line {lineno}: observation_id {oid!r} does not match mode {mode!r}"
            )
        if oid in seen:
            errors.append(f"line {lineno}: duplicate observation_id {oid!r}")
        else:
            seen.add(oid)
        for field in ("base_sha", "candidate_sha"):
            value = str(record.get(field, ""))
            if not SHA_RE.fullmatch(value):
                errors.append(f"line {lineno}: {field} is not a 40-hex SHA: {value!r}")
        if record.get("normal_evidence_frozen") is not True:
            errors.append(f"line {lineno}: normal_evidence_frozen is not true")
        if record.get("shadow_influenced_normal_workflow") is not False:
            errors.append(
                f"line {lineno}: shadow_influenced_normal_workflow is not false"
            )
        if not str(record.get("rationale", "")).strip():
            errors.append(f"line {lineno}: rationale is empty")
        signals = record.get("shadow_signals")
        disps = record.get("signal_dispositions")
        if not isinstance(signals, dict) or set(signals) != set(SIGNALS):
            errors.append(
                f"line {lineno}: shadow_signals must be exactly {SIGNALS}, got {signals!r}"
            )
        elif not all(type(v) is int and v >= 0 for v in signals.values()):
            errors.append(
                f"line {lineno}: shadow_signals values must be non-negative ints"
            )
        if not isinstance(disps, dict) or set(disps) != set(SIGNALS):
            errors.append(
                f"line {lineno}: signal_dispositions must be exactly {SIGNALS}, "
                f"got {disps!r}"
            )
        else:
            for name in SIGNALS:
                if disps[name] not in DISPOSITIONS:
                    errors.append(
                        f"line {lineno}: unknown disposition for {name}: {disps[name]!r}"
                    )
            if isinstance(signals, dict) and set(signals) == set(SIGNALS):
                for name in SIGNALS:
                    if (signals[name] == 0) != (disps[name] == "NO_SIGNAL"):
                        errors.append(
                            f"line {lineno}: {name} count/disposition mismatch "
                            f"({signals[name]!r} vs {disps[name]!r})"
                        )
            if "UNIQUE_HIGH_VALUE_FINDING" in disps.values() and not str(
                record.get("what_decision_would_change", "")
            ).strip():
                errors.append(
                    f"line {lineno}: UNIQUE_HIGH_VALUE_FINDING requires "
                    "what_decision_would_change"
                )
        if mode == "PROSPECTIVE":
            frozen = _timestamp(
                record.get("normal_evidence_frozen_at"),
                lineno,
                "normal_evidence_frozen_at",
                errors,
            )
            first = _timestamp(
                record.get("shadow_first_run_at"), lineno, "shadow_first_run_at", errors
            )
            if frozen is not None and first is not None and not frozen < first:
                errors.append(
                    f"line {lineno}: normal_evidence_frozen_at must be strictly "
                    "earlier than shadow_first_run_at"
                )
    return errors, total, counts


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name(
        "observations.jsonl"
    )
    if not path.exists():
        print(f"CHECK_FAIL: {path} not found")
        return 1
    errors, total, counts = check(path)
    print(
        f"OBSERVATIONS={total} RETROSPECTIVE={counts['RETROSPECTIVE']} "
        f"PROSPECTIVE={counts['PROSPECTIVE']}"
    )
    for error in errors:
        print(f"ERROR: {error}")
    print("CHECK=PASS" if not errors else "CHECK=FAIL")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
