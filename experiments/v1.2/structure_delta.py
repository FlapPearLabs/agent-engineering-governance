#!/usr/bin/env python3
"""STRUCTURE_DELTA_SHADOW v0 -- minimal deterministic structure-signal extractor.

Reads REAL historical BASE->CANDIDATE git diffs and mechanically extracts
exactly the three frozen v1 deterministic signals defined in
`experiments/v1.2/replay/README.md` (the experiment oracle):

  NEW_FILE        count of `A` entries in
                  `git diff --no-renames --name-status <base> <candidate>`
  NEW_DIRECTORY   |candidate directory-prefix set - base directory-prefix set|,
                  prefixes derived from `git ls-tree -r --name-only <sha>`
                  (every ancestor prefix counts, with trailing "/")
  NEW_DEPENDENCY  count of added declaration lines (non-blank, non-`#` comment)
                  on paths whose basename matches `requirements*.txt`
                  (v1 manifest family; line-oriented)

Boundary (H3-A / shadow only):
- Exactly these three signals; every other signal name stays
  NOT_YET_MECHANICALLY_DEFINED and is NOT implemented here.
- No structure verdict, no behavioral verdict, no scoring, no promotion
  decision. STRUCTURE_SIGNAL != STRUCTURE_VERDICT != CANDIDATE_CORRECTNESS.
- stdlib + git subprocess only; no repository dependency, no CI wiring,
  no canonical change. The optional `replay` command compares actual counts
  against the corpus' expected counts (MATCH / MISMATCH) and nothing more.

Unresolvable inputs (unknown/short/non-commit revisions) raise
StructureDeltaError; there is no silent fallback.

Usage:
  python3 experiments/v1.2/structure_delta.py signals \
      --repo /path/to/clone --base <sha> --candidate <sha>
  python3 experiments/v1.2/structure_delta.py replay \
      --cases experiments/v1.2/replay/cases.yaml \
      --repo-map FlapPearLabs/<name>=/path/to/clone [--repo-map ...] [--json]
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

SUPPORTED_SIGNALS = ("NEW_FILE", "NEW_DIRECTORY", "NEW_DEPENDENCY")

# v1 manifest family, exactly as frozen in the replay README: basename matching
# `requirements*.txt` (applies at any directory depth; line-oriented counting).
_MANIFEST_BASENAME = "requirements*.txt"

_CASE_ANCHOR = "\n  - case_id: "
_SHA_RE = re.compile(r"[0-9a-f]{40}")
_SIGNAL_ENTRY_RE = re.compile(r"- signal: ([A-Z_]+)\s*\n\s*count: (\d+)")


class StructureDeltaError(RuntimeError):
    """Inputs cannot be resolved mechanically -- fail loudly, never silently."""


def _git(repo: str, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise StructureDeltaError(
            f"git {' '.join(args)} failed: {proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout


def require_commit(repo: str, sha: str) -> None:
    """The revision must exist and be a commit; anything else raises."""
    if not _SHA_RE.fullmatch(sha):
        raise StructureDeltaError(f"revision {sha!r} is not a 40-hex SHA")
    try:
        kind = _git(repo, "cat-file", "-t", sha).strip()
    except StructureDeltaError as exc:
        raise StructureDeltaError(f"unresolvable revision {sha!r} in {repo}") from exc
    if kind != "commit":
        raise StructureDeltaError(f"revision {sha!r} is not a commit (type={kind})")


def count_new_files(repo: str, base_sha: str, candidate_sha: str) -> int:
    out = _git(repo, "diff", "--no-renames", "--name-status", base_sha, candidate_sha)
    return sum(1 for line in out.splitlines() if line.startswith("A\t"))


def _directory_prefixes(repo: str, sha: str) -> set[str]:
    prefixes: set[str] = set()
    for path in _git(repo, "ls-tree", "-r", "--name-only", sha).splitlines():
        parts = path.split("/")
        for depth in range(1, len(parts)):
            prefixes.add("/".join(parts[:depth]) + "/")
    return prefixes


def count_new_directories(repo: str, base_sha: str, candidate_sha: str) -> int:
    return len(_directory_prefixes(repo, candidate_sha) - _directory_prefixes(repo, base_sha))


def count_new_dependencies(repo: str, base_sha: str, candidate_sha: str) -> int:
    name_status = _git(repo, "diff", "--no-renames", "--name-status", base_sha, candidate_sha)
    total = 0
    for line in name_status.splitlines():
        fields = line.split("\t")
        if len(fields) < 2:
            continue
        status, path = fields[0], fields[-1]
        if status == "D":
            continue
        if not fnmatch.fnmatchcase(path.rsplit("/", 1)[-1], _MANIFEST_BASENAME):
            continue
        patch = _git(repo, "diff", "--no-renames", base_sha, candidate_sha, "--", path)
        for patch_line in patch.splitlines():
            if not patch_line.startswith("+") or patch_line.startswith("+++"):
                continue
            content = patch_line[1:].strip()
            if content and not content.startswith("#"):
                total += 1
    return total


def extract_signals(repo: str, base_sha: str, candidate_sha: str) -> dict[str, int]:
    """All three v1 signals for one BASE->CANDIDATE pair (fixed key order)."""
    require_commit(repo, base_sha)
    require_commit(repo, candidate_sha)
    return {
        "NEW_FILE": count_new_files(repo, base_sha, candidate_sha),
        "NEW_DIRECTORY": count_new_directories(repo, base_sha, candidate_sha),
        "NEW_DEPENDENCY": count_new_dependencies(repo, base_sha, candidate_sha),
    }


def signals_report(repo: str, base_sha: str, candidate_sha: str) -> dict:
    return {
        "base_sha": base_sha,
        "candidate_sha": candidate_sha,
        "signals": extract_signals(repo, base_sha, candidate_sha),
    }


def _field(block: str, name: str) -> str:
    match = re.search(rf"^    {re.escape(name)}: (.+)$", block, re.M)
    if not match:
        raise StructureDeltaError(f"case block is missing field {name!r}")
    return match.group(1).strip()


def load_replay_cases(cases_path: Path | str) -> list[dict]:
    """Focused, stdlib-only reader for the fields this experiment needs.

    Reads only the `cases:` (ready) section; `not_replay_ready` anchors are a
    different key and are therefore never loaded. Structural invariants are
    asserted (anchor/block count, unique ids, required fields, 40-hex SHAs,
    v1-only expected signal names) so a case can never be silently skipped and
    a non-v1 signal can never be silently compared.
    """
    text = Path(cases_path).read_text(encoding="utf-8")
    ready = text.split("\nnot_replay_ready:", 1)[0]
    blocks = ready.split(_CASE_ANCHOR)[1:]
    anchors = re.findall(r"^  - case_id: (r\d\d-[a-z0-9-]+)$", ready, re.M)
    if len(blocks) != len(anchors):
        raise StructureDeltaError(
            f"case blocks ({len(blocks)}) do not match case_id anchors ({len(anchors)})"
        )
    cases = []
    seen: set[str] = set()
    for block in blocks:
        case_id = block.splitlines()[0].strip()
        if case_id in seen:
            raise StructureDeltaError(f"duplicate case_id {case_id!r}")
        seen.add(case_id)
        expected: dict[str, int] = {}
        for name, count in _SIGNAL_ENTRY_RE.findall(block):
            expected[name] = int(count)
        unknown = sorted(set(expected) - set(SUPPORTED_SIGNALS))
        if unknown:
            raise StructureDeltaError(
                f"{case_id}: non-v1 signal in expected counts: {unknown}"
            )
        base_sha = _field(block, "base_sha")
        candidate_sha = _field(block, "candidate_sha")
        for sha in (base_sha, candidate_sha):
            if not _SHA_RE.fullmatch(sha):
                raise StructureDeltaError(f"{case_id}: not a 40-hex SHA: {sha!r}")
        cases.append(
            {
                "case_id": case_id,
                "source_repository": _field(block, "source_repository"),
                "base_sha": base_sha,
                "candidate_sha": candidate_sha,
                "expected_signals": expected,
            }
        )
    if not cases:
        raise StructureDeltaError("no ready cases found (empty corpus is not a pass)")
    return cases


def _aligned(counts: dict[str, int]) -> dict[str, int]:
    return {signal: counts.get(signal, 0) for signal in SUPPORTED_SIGNALS}


def replay_reports(cases: list[dict], repo_map: dict[str, str]) -> dict:
    """Run every ready case and compare actual vs expected counts (nothing more)."""
    per_case = []
    matched = mismatched = false_positives = false_negatives = 0
    for case in cases:
        repo = repo_map.get(case["source_repository"])
        if not repo:
            raise StructureDeltaError(
                f"no local clone mapped for {case['source_repository']!r}"
            )
        unknown = sorted(set(case["expected_signals"]) - set(SUPPORTED_SIGNALS))
        if unknown:
            raise StructureDeltaError(
                f"{case['case_id']}: non-v1 signal in expected counts: {unknown}"
            )
        actual = _aligned(extract_signals(repo, case["base_sha"], case["candidate_sha"]))
        expected = _aligned(case["expected_signals"])
        case_match = actual == expected
        if case_match:
            matched += 1
        else:
            mismatched += 1
        for signal in SUPPORTED_SIGNALS:
            if expected[signal] == 0 and actual[signal] > 0:
                false_positives += 1
            elif expected[signal] > 0 and actual[signal] < expected[signal]:
                false_negatives += 1
        per_case.append(
            {
                "case_id": case["case_id"],
                "expected": expected,
                "actual": actual,
                "match": case_match,
            }
        )
    return {
        "cases": per_case,
        "ready_cases": len(cases),
        "matched": matched,
        "mismatched": mismatched,
        "false_positive_signal_count": false_positives,
        "false_negative_signal_count": false_negatives,
    }


def _repo_map_pairs(values: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise StructureDeltaError(f"--repo-map expects OWNER/NAME=PATH, got {value!r}")
        key, path = value.split("=", 1)
        mapping[key] = path
    return mapping


def _print_replay_text(report: dict) -> None:
    for case in report["cases"]:
        expected = ", ".join(
            f"{name}={count}" for name, count in case["expected"].items() if count
        ) or "(empty)"
        actual = ", ".join(f"{name}={count}" for name, count in case["actual"].items())
        print(f"CASE_ID = {case['case_id']}")
        print(f"EXPECTED = {expected}")
        print(f"ACTUAL = {actual}")
        print(f"MATCH = {'YES' if case['match'] else 'NO'}")
        print()
    print(f"READY_CASES = {report['ready_cases']}")
    print(f"MATCHED = {report['matched']}")
    print(f"MISMATCHED = {report['mismatched']}")
    print(f"FALSE_POSITIVE_SIGNAL_COUNT = {report['false_positive_signal_count']}")
    print(f"FALSE_NEGATIVE_SIGNAL_COUNT = {report['false_negative_signal_count']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="structure_delta.py",
        description="STRUCTURE_DELTA_SHADOW v0 (shadow only; not wired to CI)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_signals = sub.add_parser("signals", help="extract v0 signals for one BASE->CANDIDATE pair")
    p_signals.add_argument("--repo", required=True)
    p_signals.add_argument("--base", required=True)
    p_signals.add_argument("--candidate", required=True)

    p_replay = sub.add_parser("replay", help="replay all ready cases and compare counts")
    p_replay.add_argument(
        "--cases",
        default=str(Path(__file__).resolve().parent / "replay" / "cases.yaml"),
    )
    p_replay.add_argument(
        "--repo-map",
        action="append",
        default=[],
        metavar="OWNER/NAME=PATH",
        help="local clone path for a source_repository (repeatable)",
    )
    p_replay.add_argument("--json", action="store_true", help="emit machine-readable JSON")

    args = parser.parse_args(argv)

    if args.command == "signals":
        print(json.dumps(signals_report(args.repo, args.base, args.candidate), indent=2))
        return 0

    cases = load_replay_cases(args.cases)
    report = replay_reports(cases, _repo_map_pairs(args.repo_map))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_replay_text(report)
    clean = (
        report["mismatched"] == 0
        and report["false_positive_signal_count"] == 0
        and report["false_negative_signal_count"] == 0
    )
    return 0 if clean else 1


def cli() -> None:
    try:
        sys.exit(main())
    except StructureDeltaError as exc:
        print(f"STRUCTURE_DELTA_ERROR: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    cli()
