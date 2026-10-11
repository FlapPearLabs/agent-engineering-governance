#!/usr/bin/env bash
# H2 harness — check_hygiene.sh <WORKTREE>
# (1) syntax-compile every changed/untracked .py file IN MEMORY (no __pycache__ residue
#     created by the checker itself — [6]);
# (2) count __pycache__ / *.pyc entries in the change set and status.
# Fails closed if the worktree is not a git worktree or any git inspection fails ([5]).
set -uo pipefail
PY="${PY:-python3}"
WT="${1:?usage: check_hygiene.sh <WORKTREE> [RUN_ID]}"
RUN_ID="${2:-}"
fail=0

if ! git -C "$WT" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "FAIL not a readable git worktree: $WT"
  echo "HYGIENE = FAIL"
  exit 2
fi

# Committed changes must also count: when RUN_ID is given, enumerate from the receipt's base
# (with --no-renames so both sides of a committed rename are visible) — R8-6/R8-7.
BASE_FROM_RECEIPT=""
if [ -n "$RUN_ID" ] && [ -n "${H2_RUNS_ROOT:-}" ]; then
  RP="$H2_RUNS_ROOT/evidence/$RUN_ID/receipt.json"
  if [ -f "$RP" ]; then
    BASE_FROM_RECEIPT="$("$PY" - "$RP" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["expected_base"])
PYEOF
)" || BASE_FROM_RECEIPT=""
  fi
fi

files="$( { git -C "$WT" diff --name-only HEAD && git -C "$WT" ls-files --others --exclude-standard \
  && { [ -n "$BASE_FROM_RECEIPT" ] && git -C "$WT" diff --name-only --no-renames "$BASE_FROM_RECEIPT" || true; }; } | sort -u )" \
  || { echo "FAIL git inspection failed (diff/ls-files)"; echo "HYGIENE = FAIL"; exit 2; }

pyfiles="$(printf '%s\n' "$files" | grep -E '\.py$' | grep -v '__pycache__' || true)"

if [ -n "$pyfiles" ]; then
  while IFS= read -r f; do
    [ -z "$f" ] && continue
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
status_pyc="$(git -C "$WT" status --porcelain | grep -cE '__pycache__|\.pyc$' || true)"
echo "PYCACHE_IN_CHANGESET = $pyc_count"
echo "PYCACHE_IN_STATUS    = $status_pyc"
if [ "$pyc_count" != "0" ] || [ "$status_pyc" != "0" ]; then
  echo "FAIL pycache/pyc residue present"; fail=1
fi

if [ "$fail" = "0" ]; then echo "HYGIENE = PASS"; else echo "HYGIENE = FAIL"; fi
exit $fail
