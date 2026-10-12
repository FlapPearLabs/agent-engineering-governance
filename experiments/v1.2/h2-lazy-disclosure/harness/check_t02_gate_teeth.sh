#!/usr/bin/env bash
# H2 harness — check_t02_gate_teeth.sh <WORKTREE> <RUN_ID> [PY]
# t02 positive control ([12]): prove the run's OWN ruff gate still catches a real F841
# defect. Builds a scratch dir under the run evidence dir, copies the run's ruff.toml,
# injects an F841 probe, and requires ruff to FAIL on it. A pass-through here means the
# gate was silently hollowed — GATE_NOT_LOAD_BEARING.
set -u
H2_RUNS_ROOT="${H2_RUNS_ROOT:?set H2_RUNS_ROOT}"
WT="${1:?usage: check_t02_gate_teeth.sh <WORKTREE> <RUN_ID> [PY]}"
RUN_ID="${2:?usage: check_t02_gate_teeth.sh <WORKTREE> <RUN_ID> [PY]}"
PY="${3:-python3}"
EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
SC="$EV/t02-positive-control"

rm -rf "$SC"
mkdir -p "$SC" || { echo "T02_POSITIVE_CONTROL = FAIL (scratch mkdir failed)"; exit 2; }
if [ ! -f "$WT/ruff.toml" ]; then
  echo "T02_POSITIVE_CONTROL = FAIL (no ruff.toml in the run worktree)"
  exit 1
fi
cp "$WT/ruff.toml" "$SC/ruff.toml"
printf 'def f():\n    unused_local = 1\n    return 2\n' > "$SC/_probe_f841.py"
( cd "$SC" && "$PY" -m ruff check --no-cache --config "$SC/ruff.toml" . ) > "$SC/ruff-out.txt" 2>&1
rc=$?
cat "$SC/ruff-out.txt"
if [ "$rc" -ne 0 ] && grep -q "F841" "$SC/ruff-out.txt"; then
  echo "T02_POSITIVE_CONTROL = PASS (injected F841 caught by the run's own gate config)"
  exit 0
fi
echo "T02_POSITIVE_CONTROL = FAIL (injected F841 NOT caught; rc=$rc) — GATE_NOT_LOAD_BEARING"
exit 1
