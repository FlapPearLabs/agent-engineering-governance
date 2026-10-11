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
WT="${1:?usage: check_scope.sh <WORKTREE> <TASK_ID>}"
TASK_ID="${2:?usage: check_scope.sh <WORKTREE> <TASK_ID>}"
"$PY" - "$EXP_DIR/task-registry.json" "$WT" "$TASK_ID" <<'PYEOF'
import json, subprocess, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
wt, tid = sys.argv[2], sys.argv[3]
task = [t for t in reg["tasks"] if t["task_id"] == tid][0]
scope = task.get("scope") or {}
ARTIFACTS = {"CODEBUDDY.md", ".h2-telemetry.log", "H2_RULES.md", "H2_AGENTS.md"}

st = subprocess.run(["git", "-C", wt, "status", "--porcelain=v1", "--untracked-files=all"],
                    capture_output=True, text=True)
if st.returncode != 0:
    print("SCOPE_FAIL reason=GIT_INSPECTION_FAILED"); sys.exit(2)
paths = []
for line in st.stdout.splitlines():
    p = line[3:]
    if " -> " in p:
        p = p.split(" -> ")[-1]
    if p in ARTIFACTS or p.startswith("H2_WARM/"):
        continue
    paths.append(p)
paths = sorted(set(paths))
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
