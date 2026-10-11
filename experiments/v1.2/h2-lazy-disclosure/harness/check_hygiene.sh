#!/usr/bin/env bash
# H2 harness — check_hygiene.sh <WORKTREE>
# (1) py_compile every changed/untracked .py file in the worktree diff/status;
# (2) count __pycache__ / *.pyc entries in status + changed file list.
# Prints FAIL lines and exits non-zero if any check fails.
set -u
PY="${PY:-python3}"
WT="${1:?usage: check_hygiene.sh <WORKTREE>}"
fail=0

mapfile_cmd() { :; }  # placeholder for portability below

files="$( { git -C "$WT" diff --name-only HEAD; git -C "$WT" ls-files --others --exclude-standard; } | sort -u )"
pyfiles="$(printf '%s\n' "$files" | grep -E '\.py$' | grep -v '__pycache__' || true)"

if [ -n "$pyfiles" ]; then
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    if ! (cd "$WT" && "$PY" -m py_compile "$f" >/dev/null 2>&1); then
      echo "FAIL py_compile: $f"; fail=1
    else
      echo "OK   py_compile: $f"
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
