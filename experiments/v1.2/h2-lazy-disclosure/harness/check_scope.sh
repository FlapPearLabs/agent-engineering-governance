#!/usr/bin/env bash
# H2 harness — check_scope.sh <WORKTREE> <TASK_ID>
# Enforces the task's scope predicates from task-registry.json#tasks[].scope (bot review R5-4):
#   deny_prefixes   — no changed path may start with any of these (hard fail)
#   require_any_in  — if non-null, at least one changed path must start with one of these
#   max_files       — if non-null, the number of changed paths must be <= it
# Prints the full change surface (placed harness artifacts excluded) and exits nonzero on
# any violation.
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP_DIR="$(cd "$HERE/.." && pwd)"
PY="${PY:-python3}"
WT="${1:?usage: check_scope.sh <WORKTREE> <TASK_ID> [RUN_ID]}"
TASK_ID="${2:?usage: check_scope.sh <WORKTREE> <TASK_ID> [RUN_ID]}"
SCOPE_RUN_ID="${3:-}"
export SCOPE_RUN_ID
"$PY" - "$EXP_DIR/task-registry.json" "$WT" "$TASK_ID" "$H2_RUNS_ROOT" <<'PYEOF'
import json, os, subprocess, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
wt, tid, runs_root = sys.argv[2], sys.argv[3], sys.argv[4]
task = [t for t in reg["tasks"] if t["task_id"] == tid][0]
scope = task.get("scope") or {}
ARTIFACTS = {"CODEBUDDY.md", ".h2-telemetry.log", "H2_RULES.md", "H2_AGENTS.md"}
PREFIX_ARTIFACTS = ("H2_WARM/", ".h2_scan_tools/")

def in_artifacts(p):
    return p in ARTIFACTS or p.startswith(PREFIX_ARTIFACTS)

def parse_status_z(stdout_bytes):
    """Parse `git status --porcelain=v1 -z` (NUL-separated; quote-safe)."""
    parts = stdout_bytes.split(b"\x00")
    paths = []
    i = 0
    while i < len(parts):
        entry = parts[i]
        if not entry:
            i += 1
            continue
        text = entry.decode("utf-8", errors="replace")
        xy, path = text[:2], text[3:]
        if xy[0] in "RC":  # rename/copy: next token is the ORIGINAL path
            i += 2
        else:
            i += 1
        paths.append(path)
    return paths

st = subprocess.run(["git", "-C", wt, "status", "--porcelain=v1", "--untracked-files=all", "-z"],
                    capture_output=True)
if st.returncode != 0:
    print("SCOPE_FAIL reason=GIT_INSPECTION_FAILED"); sys.exit(2)
paths = set(p for p in parse_status_z(st.stdout) if not in_artifacts(p))

# Committed changes (HEAD != base) must also count: read base from the run receipt when present.
h2r = runs_root
base = None
rid = os.environ.get("SCOPE_RUN_ID") or ""
if rid:
    receipt_path = os.path.join(h2r, "evidence", rid, "receipt.json")
    if os.path.isfile(receipt_path):
        base = json.load(open(receipt_path, encoding="utf-8"))["expected_base"]
if base:
    head = subprocess.run(["git", "-C", wt, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != base:
        # --no-renames: a committed rename must expose BOTH sides (source delete + dest add) — R8-7
        d = subprocess.run(["git", "-C", wt, "diff", "--name-status", "--no-renames", "-z", base],
                           capture_output=True)
        parts = d.stdout.split(b"\x00")
        for tok in parts:
            tok = tok.decode("utf-8", errors="replace")
            if not tok or tok in ("A", "M", "D", "T"):
                continue
            if len(tok) <= 2 and tok.strip() in ("A", "M", "D", "T", "R", "C"):
                continue
            if not in_artifacts(tok):
                paths.add(tok)

paths = sorted(paths)
print("CHANGE SURFACE:")
for p in paths:
    print("  " + p)
viol = []
for p in paths:
    for pre in scope.get("deny_prefixes", []) or []:
        if p.startswith(pre):
            viol.append(f"DENIED_PREFIX {pre!r} matches {p!r}")
req = scope.get("require_any_in")
if req is not None:
    if not any(p.startswith(tuple(req)) for p in paths):
        viol.append(f"REQUIRED_MISSING no changed path under {req}")
mx = scope.get("max_files")
if mx is not None and len(paths) > mx:
    viol.append(f"MAX_FILES_EXCEEDED {len(paths)} > {mx}")
if viol:
    for v in viol:
        print("SCOPE_VIOLATION:", v)
    print("SCOPE = FAIL")
    sys.exit(1)
print("SCOPE = PASS")
PYEOF
