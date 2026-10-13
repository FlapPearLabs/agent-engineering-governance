#!/usr/bin/env bash
# H2 harness — check_scope.sh <WORKTREE> <TASK_ID>
# Enforces the task's scope predicates from task-registry.json#tasks[].scope (bot review R5-4):
#   deny_prefixes   — no changed path may start with any of these (hard fail)
#   require_any_in  — if non-null, at least one changed path must start with one of these
#   max_files       — if non-null, the number of changed paths must be <= it
# Prints the full change surface (placed harness artifacts excluded) and exits nonzero on
# any violation.
# ---------------------------------------------------------------------------------------------
# STRUCTURAL ENV SANITIZATION (fresh review on d2c9b99, P1-1/P2-1): the caller's environment is
# re-created from scratch (env -i) before ANY git invocation, so the whole GIT_* injection class
# — GIT_CONFIG_PARAMETERS (applied AFTER the GIT_CONFIG_COUNT pins and previously honoured),
# GIT_CONFIG, GIT_DIR/GIT_WORK_TREE/GIT_COMMON_DIR, GIT_OBJECT_DIRECTORY/alternates, namespaces —
# cannot reach the judgement commands. The branch is taken when the marker is absent OR when any
# GIT_* variable is still present (so forging the marker while injecting GIT_* re-sanitizes
# anyway). A caller that fully controls the process environment (PATH hijack, loader injection)
# remains the documented same-UID boundary; the enforcement points are operator-run collect and
# independent review.
if [ "${H2_ENV_SANITIZED:-}" != "1" ] || env | grep -q '^GIT_'; then
  exec env -i PATH="$PATH" HOME="$HOME" LANG="${LANG:-C}" LC_ALL="${LC_ALL:-C}" \
       TERM="${TERM:-dumb}" H2_ENV_SANITIZED=1 PY="${PY:-}" \
       H2_RUNS_ROOT="${H2_RUNS_ROOT:-}" \
       WORKER_MODEL="${WORKER_MODEL:-}" WORKER_EPISODE="${WORKER_EPISODE:-}" \
       AUDITOR_EPISODE="${AUDITOR_EPISODE:-}" bash "$0" "$@"
fi

set -uo pipefail
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_INDEX_FILE
# global/system git config must not influence judgement (fresh review on 9c5f059, P0)
# Command-scope pins, set AFTER the caller's environment (overwriting any caller-provided
# GIT_CONFIG_* / GIT_ATTR_*): hooks cannot execute, fsmonitor is off, status never hides
# untracked entries, and the global attribute/exclude layers are neutralised. These hold
# independently of the metadata guard (fresh review on 61bfbac, P0/P1 — all three vectors
# verified empirically against the unpinned behaviour).
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_CONFIG_COUNT=5
export GIT_CONFIG_KEY_0=core.hooksPath            GIT_CONFIG_VALUE_0=/dev/null
export GIT_CONFIG_KEY_1=core.fsmonitor            GIT_CONFIG_VALUE_1=false
export GIT_CONFIG_KEY_2=status.showUntrackedFiles GIT_CONFIG_VALUE_2=all
export GIT_CONFIG_KEY_3=core.attributesFile       GIT_CONFIG_VALUE_3=/dev/null
export GIT_CONFIG_KEY_4=core.excludesFile         GIT_CONFIG_VALUE_4=/dev/null
export GIT_ATTR_NOSYSTEM=1
# replacement objects (git replace) are disabled for EVERY judgement command: even a replace ref
# that the metadata guard failed to see cannot substitute the commits these commands compare
# (fresh review on d2c9b99, P0 — pack-refs hid a replace ref from the guard and made the base
# object itself resolve to attacker content).
export GIT_NO_REPLACE_OBJECTS=1
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP_DIR="$(cd "$HERE/.." && pwd)"
PY="${PY:-python3}"
WT="${1:?usage: check_scope.sh <WORKTREE> <TASK_ID> [RUN_ID]}"
TASK_ID="${2:?usage: check_scope.sh <WORKTREE> <TASK_ID> [RUN_ID]}"
SCOPE_RUN_ID="${3:-}"
# The judgement base is the worktree's OWN git view, and .git/ is inside the worker's write
# surface: `update-index --assume-unchanged`, a clean filter via .git/info/attributes+config, or
# an .git/info/exclude edit can hide forbidden changes while the files stay dirty. Refuse such a
# worktree instead of judging it (fresh review on 9c5f059, P0).
GM="$(bash "$HERE/check_git_metadata.sh" "$WT")"; _gmrc=$?
if [ "$_gmrc" -eq 2 ]; then
  echo "SCOPE_FAIL reason=WORKTREE_GIT_METADATA_UNREADABLE"; exit 2
fi
if [ "$_gmrc" -ne 0 ]; then
  echo "SCOPE_FAIL reason=WORKTREE_GIT_METADATA_TAMPERED [$GM]"; exit 2
fi
# The base and the task identity are derived from the FROZEN plan + registry, never from the
# receipt: receipt.json is worker-writable, and reading expected_base from it let a worker run
# this check with a rewritten base (skipping the committed-change enumeration), record a PASS,
# then restore the receipt so collection still passed (fresh adversarial review on 9f8e4ee, P0).
if [ -z "$SCOPE_RUN_ID" ]; then
  echo "SCOPE_FAIL reason=MISSING_RUN_ID (frozen facts cannot be derived without the run id)"
  exit 2
fi
FROZEN="$("$PY" "$HERE/frozen_run_facts.py" "$EXP_DIR" "$SCOPE_RUN_ID")"
_frc=$?
if [ "$_frc" -ne 0 ]; then
  if [ "$_frc" -eq 2 ]; then
    echo "SCOPE_FAIL reason=NO_FROZEN_ROW run_id=$SCOPE_RUN_ID (no plan row; refusing rather than trusting the receipt)"
  else
    echo "SCOPE_FAIL reason=FROZEN_FACTS_UNREADABLE (plan unreadable or not commit-bound)"
  fi
  exit 2
fi
"$PY" - "$EXP_DIR/task-registry.json" "$WT" "$TASK_ID" "$FROZEN" <<'PYEOF'
import json, os, subprocess, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
wt, tid = sys.argv[2], sys.argv[3]
frozen = sys.argv[4].split("\t")
frozen_tid, base, _arm, _idx, _plan = frozen[0], frozen[1], frozen[2], frozen[3], frozen[4]
if tid != frozen_tid:
    print(f"SCOPE_FAIL reason=TASK_ID_DOES_NOT_MATCH_FROZEN_ROW arg={tid!r} frozen={frozen_tid!r}")
    sys.exit(2)
task = [t for t in reg["tasks"] if t["task_id"] == tid][0]
scope = task.get("scope") or {}
ARTIFACTS = {"CODEBUDDY.md", ".h2-telemetry.log", "H2_RULES.md", "H2_AGENTS.md"}
PREFIX_ARTIFACTS = ("H2_WARM/",)  # only the delivered bundle prefix; .h2_scan_tools residue
# is NOT exempt (R9-7): only the exact temporary scanner file created+removed inside one
# acceptance step is legitimate, and any leftover must remain visible in the change surface.

def in_artifacts(p):
    return p in ARTIFACTS or p.startswith(PREFIX_ARTIFACTS)

def parse_status_z(stdout_bytes):
    """Parse `git status --porcelain=v1 -z` (NUL-separated; quote-safe). For rename/copy
    entries, BOTH the destination and the original path are recorded (R9-1: the source side
    of a staged rename must stay visible to deny predicates)."""
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
        paths.append(path)
        if xy[0] in "RC" and i + 1 < len(parts):
            orig = parts[i + 1].decode("utf-8", errors="replace")
            if orig:
                paths.append(orig)
            i += 2
        else:
            i += 1
    return paths

# --ignored=matching: ignored files (e.g. .gitignore'd residue, or files hidden behind an
# .git/info/exclude edit) must stay VISIBLE in the change surface — the fresh review on 9c5f059
# hid untracked denied files from a plain status by adding an exclude line.
st = subprocess.run(["git", "-C", wt, "status", "--porcelain=v1", "--untracked-files=all",
                     "--ignored=matching", "-z"],
                    capture_output=True)
if st.returncode != 0:
    print("SCOPE_FAIL reason=GIT_INSPECTION_FAILED"); sys.exit(2)
paths = set(p for p in parse_status_z(st.stdout) if not in_artifacts(p))

# Committed changes (HEAD != base) must also count. `base` is the FROZEN registry base for this
# run's task (derived above from the plan row); the receipt is deliberately not consulted.
if base:
    head = subprocess.run(["git", "-C", wt, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != base:
        # --no-renames: a committed rename must expose BOTH sides (source delete + dest add) — R8-7
        d = subprocess.run(["git", "-C", wt, "diff", "--name-status", "--no-renames", "-z", base],
                           capture_output=True)
        # fresh review on 9c5f059 (P2): an unchecked rc turned a FAILED diff (bad base object,
        # broken config) into an EMPTY committed-change set — silently hiding every commit.
        if d.returncode != 0:
            print("SCOPE_FAIL reason=FROZEN_BASE_UNREADABLE (the base-relative diff failed; "
                  "refusing rather than judging on a partial surface)")
            sys.exit(2)
        # fresh review on 61bfbac (P3): parse BY PARITY. The old positional heuristic dropped any
        # path token that happened to spell a status letter (a file literally named "A"), so a
        # committed change could vanish from the surface. --no-renames guarantees the stream is
        # strictly alternating single-letter STATUS \0 path \0.
        toks = [t.decode("utf-8", errors="replace") for t in d.stdout.split(b"\x00")]
        i = 0
        while i + 1 < len(toks):
            status, path = toks[i], toks[i + 1]
            if len(status) > 2:
                print("SCOPE_FAIL reason=DIFF_PARSE_ANOMALY (unexpected status token; "
                      "--no-renames guarantees single-letter statuses)")
                sys.exit(2)
            if path and not in_artifacts(path):
                paths.add(path)
            i += 2

paths = sorted(paths)
print("CHANGE SURFACE:")
for p in paths:
    print("  " + p)
viol = []
allow = scope.get("allow_prefixes")
if allow is not None:
    for p in paths:
        if not p.startswith(tuple(allow)):
            viol.append(f"PATH_OUTSIDE_ALLOWED {p!r} (allow_prefixes={allow})")
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
