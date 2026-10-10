#!/usr/bin/env python3
"""Experimental route-reachability validator for V1.2 N8 (issue #46). Non-canonical.

What it proves, per declared route, against a DECLARED BASE (never implicitly HEAD):

    ROUTE_DECLARED != DESTINATION_EXISTS != DESTINATION_LOADABLE

    DESTINATION_EXISTS = `git cat-file -e <base>:<destination>` succeeds
    ANCHOR_EXISTS      = only when the route declares an anchor; the anchor is a
                         literal substring of the destination blob at that base
    LOADABLE           = DESTINATION_EXISTS and (no anchor declared or ANCHOR_EXISTS)
                         -- a deliberately minimal definition: the declared text is
                         present at the declared base. It is NOT a claim that any
                         agent found, read, or understood it.

Fail-closed by construction (an empty PASS is impossible):

    exit 0  ALL_ROUTES_VALID     (>=1 route declared, all valid)
    exit 1  ROUTES_UNSATISFIED   (>=1 route failed)
    exit 2  MALFORMED_MANIFEST   (schema / fields / destination sanity; also the
                                  argparse usage error when --base is omitted)
    exit 3  NO_ROUTES_DECLARED   (zero routes is never a pass; H2 precondition FAIL)
    exit 4  BASE_UNRESOLVABLE    (the declared base does not resolve to a commit)

Route validity is base-relative by design: the same route can be VALID at one base
and DESTINATION_MISSING at another (that is exactly how issue #46 manifested).

Usage:
    python3 validate_routes.py --base <commit-ish> [--manifest routes.json]
                               [--repo .] [--json]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

EXIT_ALL_VALID = 0
EXIT_UNSATISFIED = 1
EXIT_MALFORMED = 2
EXIT_NO_ROUTES = 3
EXIT_BASE_UNRESOLVABLE = 4

DESTINATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class Malformed(Exception):
    """Manifest violates the minimal route contract; the validator fails closed."""


def _git(repo: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        errors="replace",
        check=False,
    )


def resolve_base(repo: str, base: str) -> str | None:
    """Resolve the declared base to a full commit SHA, or None if it does not resolve."""
    proc = _git(repo, "rev-parse", "--verify", "--quiet", f"{base}^{{commit}}")
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def load_manifest(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Malformed(f"manifest unreadable or not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise Malformed("manifest top level must be an object")
    routes = data.get("routes")
    if not isinstance(routes, list):
        raise Malformed("manifest must carry a 'routes' list")

    surfaces = data.get("surfaces", [])
    if not isinstance(surfaces, list):
        raise Malformed("'surfaces' must be a list when present")
    surface_ids: set[str] = set()
    for surf in surfaces:
        if not isinstance(surf, dict):
            raise Malformed("each surface must be an object")
        sid = surf.get("surface_id")
        if not isinstance(sid, str) or not sid:
            raise Malformed("each surface needs a non-empty string 'surface_id'")
        surface_ids.add(sid)

    checked: list[dict] = []
    seen_ids: set[str] = set()
    for i, route in enumerate(routes):
        if not isinstance(route, dict):
            raise Malformed(f"routes[{i}] is not an object")
        rid = route.get("route_id")
        dest = route.get("destination")
        anchor = route.get("anchor")
        if not isinstance(rid, str) or not rid:
            raise Malformed(f"routes[{i}] needs a non-empty string 'route_id'")
        if rid in seen_ids:
            raise Malformed(f"duplicate route_id: {rid}")
        seen_ids.add(rid)
        if not isinstance(dest, str) or not dest:
            raise Malformed(f"{rid}: missing 'destination'")
        if dest.startswith("/") or "\\" in dest or ".." in dest.split("/"):
            raise Malformed(f"{rid}: destination must be a clean repo-relative path: {dest!r}")
        if not DESTINATION_RE.match(dest):
            raise Malformed(f"{rid}: destination has unsupported characters: {dest!r}")
        if anchor is not None and (not isinstance(anchor, str) or not anchor):
            raise Malformed(f"{rid}: 'anchor' must be a non-empty string when present")
        surf = route.get("surface")
        if surf is not None and surf not in surface_ids:
            raise Malformed(f"{rid}: references unknown surface {surf!r}")
        checked.append({"route_id": rid, "destination": dest, "anchor": anchor})
    return {"routes": checked}


def evaluate(repo: str, base_sha: str, routes: list[dict]) -> list[dict]:
    results: list[dict] = []
    for route in routes:
        spec = f"{base_sha}:{route['destination']}"
        exists = _git(repo, "cat-file", "-e", spec).returncode == 0
        anchor: str | None = route["anchor"]
        anchor_exists: bool | None = None
        if exists and anchor is not None:
            blob = _git(repo, "cat-file", "-p", spec)
            anchor_exists = blob.returncode == 0 and anchor in blob.stdout
        if not exists:
            result, loadable = "DESTINATION_MISSING", False
        elif anchor is not None and not anchor_exists:
            result, loadable = "ANCHOR_MISSING", False
        else:
            result, loadable = "VALID", True
        results.append(
            {
                "route_id": route["route_id"],
                "destination": route["destination"],
                "anchor": anchor,
                "destination_exists": exists,
                "anchor_exists": anchor_exists,
                "loadable": loadable,
                "result": result,
            }
        )
    return results


def emit(summary: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print(f"BASE = {summary['base_sha'] or summary['base']}")
    for r in summary["routes"]:
        anchor = f" ANCHOR={r['anchor']!r}" if r.get("anchor") else ""
        print(f"  ROUTE={r['route_id']} DESTINATION={r['destination']}{anchor} RESULT={r['result']}")
    print(f"ROUTES_DECLARED = {summary['routes_declared']}")
    print(f"ROUTES_VALID = {summary['routes_valid']}")
    print(f"ROUTES_FAILED = {summary['routes_failed']}")
    print(f"VERDICT = {summary['verdict']}")
    print(f"H2_PRECONDITION = {summary['h2_precondition']}")
    if summary.get("error"):
        print(f"ERROR = {summary['error']}")
    if summary.get("note"):
        print(f"NOTE = {summary['note']}")


def _summary(base: str, base_sha: str | None, verdict: str, **extra) -> dict:
    summary = {
        "base": base,
        "base_sha": base_sha,
        "routes_declared": 0,
        "routes_valid": 0,
        "routes_failed": 0,
        "verdict": verdict,
        "h2_precondition": "PASS" if verdict == "ALL_ROUTES_VALID" else "FAIL",
        "routes": [],
    }
    summary.update(extra)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--manifest", default=str(Path(__file__).with_name("routes.json")))
    parser.add_argument(
        "--base",
        required=True,
        help="declared base (commit-ish); required — HEAD-only validation is not a supported mode",
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    base_sha = resolve_base(args.repo, args.base)
    if base_sha is None:
        emit(_summary(args.base, None, "BASE_UNRESOLVABLE"), args.as_json)
        return EXIT_BASE_UNRESOLVABLE

    try:
        manifest = load_manifest(Path(args.manifest))
    except Malformed as exc:
        emit(_summary(args.base, base_sha, "MALFORMED_MANIFEST", error=str(exc)), args.as_json)
        return EXIT_MALFORMED

    routes = manifest["routes"]
    declared = len(routes)
    if declared == 0:
        emit(
            _summary(
                args.base,
                base_sha,
                "NO_ROUTES_DECLARED",
                note="zero declared routes is never a pass; H2 precondition is FAIL",
            ),
            args.as_json,
        )
        return EXIT_NO_ROUTES

    results = evaluate(args.repo, base_sha, routes)
    valid = sum(1 for r in results if r["result"] == "VALID")
    failed = declared - valid
    verdict = "ALL_ROUTES_VALID" if failed == 0 else "ROUTES_UNSATISFIED"
    summary = {
        "base": args.base,
        "base_sha": base_sha,
        "manifest": args.manifest,
        "routes_declared": declared,
        "routes_valid": valid,
        "routes_failed": failed,
        "verdict": verdict,
        "h2_precondition": "PASS" if failed == 0 else "FAIL",
        "routes": results,
    }
    emit(summary, args.as_json)
    return EXIT_ALL_VALID if failed == 0 else EXIT_UNSATISFIED


if __name__ == "__main__":
    sys.exit(main())
