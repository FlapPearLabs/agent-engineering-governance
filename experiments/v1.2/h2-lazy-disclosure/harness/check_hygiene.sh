#!/usr/bin/env bash
# H2 harness — check_hygiene.sh <WORKTREE>
# (1) syntax-compile every changed/untracked .py file IN MEMORY (no __pycache__ residue
#     created by the checker itself — [6]);
# (2) count __pycache__ / *.pyc entries in the change set and status.
# Fails closed if the worktree is not a git worktree or any git inspection fails ([5]).
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
PY="${PY:-python3}"
WT="${1:?usage: check_hygiene.sh <WORKTREE> [RUN_ID]}"
RUN_ID="${2:-}"
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP_DIR="$(cd "$HERE/.." && pwd)"
fail=0

if ! git -C "$WT" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "FAIL not a readable git worktree: $WT"
  echo "HYGIENE = FAIL"
  exit 2
fi
# refuse a worktree whose own git metadata was used to hide changes (fresh review 9c5f059, P0)
GM="$(bash "$HERE/check_git_metadata.sh" "$WT")"; _gmrc=$?
if [ "$_gmrc" -eq 2 ]; then
  echo "FAIL reason=WORKTREE_GIT_METADATA_UNREADABLE"; echo "HYGIENE = FAIL"; exit 2
fi
if [ "$_gmrc" -ne 0 ]; then
  echo "FAIL reason=WORKTREE_GIT_METADATA_TAMPERED [$GM]"; echo "HYGIENE = FAIL"; exit 2
fi

# Committed changes must also count: when RUN_ID is given, enumerate from the FROZEN base derived
# from the plan + registry (with --no-renames so both sides of a committed rename are visible) —
# R8-6/R8-7. The receipt is NOT consulted: it is worker-writable, and reading expected_base from
# it let a worker aim the enumeration at its own HEAD, hiding committed changes entirely (fresh
# adversarial review on 9f8e4ee, P0).
BASE=""
if [ -n "$RUN_ID" ]; then
  FROZEN="$("$PY" "$HERE/frozen_run_facts.py" "$EXP_DIR" "$RUN_ID")"
  _frc=$?
  if [ "$_frc" -ne 0 ]; then
    echo "FAIL frozen facts unavailable (rc=$_frc); refusing rather than trusting the receipt"
    echo "HYGIENE = FAIL"
    exit 2
  fi
  BASE="$(printf '%s' "$FROZEN" | cut -f2)"
fi

# The change set is enumerated with git's OWN report, INCLUDING ignored files
# (--ignored=matching): pycache/pyc residue is usually ignored, and a plain `ls-files
# --exclude-standard` made it invisible to both counters (fresh review on 9c5f059, P2). The
# base-relative diff is rc-checked: a failed diff must refuse, not silently yield an empty set.
FILES="$("$PY" - "$WT" "$BASE" <<'PYEOF'
import subprocess, sys
wt, base = sys.argv[1], sys.argv[2]

def run(*a):
    return subprocess.run(a, capture_output=True)


st = run("git", "-C", wt, "status", "--porcelain=v1", "--untracked-files=all",
         "--ignored=matching", "-z")
if st.returncode != 0:
    print("__GIT_FAIL__ status"); raise SystemExit(0)
status_paths = set()
parts = st.stdout.split(b"\x00")
i = 0
while i < len(parts):
    entry = parts[i]
    if not entry:
        i += 1
        continue
    text = entry.decode("utf-8", errors="replace")
    xy, path = text[:2], text[3:]
    status_paths.add(path)
    if xy and xy[0] in "RC" and i + 1 < len(parts):
        orig = parts[i + 1].decode("utf-8", errors="replace")
        if orig:
            status_paths.add(orig)
        i += 2
    else:
        i += 1

committed_paths = set()
if base:
    d = run("git", "-C", wt, "diff", "--no-ext-diff", "--name-only", "--no-renames", base)
    if d.returncode != 0:
        print("__GIT_FAIL__ base"); raise SystemExit(0)
    committed_paths = {p for p in d.stdout.decode("utf-8", errors="replace").splitlines() if p}

for p in sorted(status_paths):
    print("S\t" + p)
for p in sorted(committed_paths - status_paths):
    print("C\t" + p)
PYEOF
)" || { echo "FAIL git inspection failed"; echo "HYGIENE = FAIL"; exit 2; }
case "$FILES" in
  __GIT_FAIL__*) echo "FAIL git inspection failed or FROZEN_BASE_UNREADABLE (refusing)"; echo "HYGIENE = FAIL"; exit 2 ;;
esac
files="$(printf '%s\n' "$FILES" | cut -f2 | sed '/^$/d' | sort -u)"
status_files="$(printf '%s\n' "$FILES" | awk -F'\t' '$1=="S"{print $2}')"

pyfiles="$(printf '%s\n' "$files" | grep -E '\.py$' | grep -v '__pycache__' || true)"

if [ -n "$pyfiles" ]; then
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    # R11-7: base-relative enumeration lists the OLD path of a committed delete/rename, so the
    # path may legitimately no longer exist in the final worktree. There is no Python source
    # at that path to compile -> SKIP, never FAIL. Dangling symlinks are skipped the same way
    # (no readable source); a readable one is still compiled.
    if [ ! -e "$WT/$f" ] || [ -d "$WT/$f" ]; then
      echo "SKIP py_compile (not a file in the final worktree): $f"
      continue
    fi
    if "$PY" - "$WT/$f" <<'PYEOF'
import pathlib, sys
p = sys.argv[1]
try:
    compile(pathlib.Path(p).read_bytes(), p, "exec")
except SyntaxError as exc:
    print(f"syntax error: {exc}")
    raise SystemExit(1)
PYEOF
    then
      echo "OK   py_compile(memory): $f"
    else
      echo "FAIL py_compile(memory): $f"; fail=1
    fi
  done <<< "$pyfiles"
else
  echo "OK   py_compile: no .py files in change set"
fi

pyc_count="$(printf '%s\n' "$files" | grep -cE '__pycache__|\.pyc$' || true)"
status_pyc="$(printf '%s\n' "$status_files" | grep -cE '__pycache__|\.pyc$' || true)"
echo "PYCACHE_IN_CHANGESET = $pyc_count"
echo "PYCACHE_IN_STATUS    = $status_pyc"
if [ "$pyc_count" != "0" ] || [ "$status_pyc" != "0" ]; then
  echo "FAIL pycache/pyc residue present"; fail=1
fi

if [ "$fail" = "0" ]; then echo "HYGIENE = PASS"; else echo "HYGIENE = FAIL"; fi
exit $fail
