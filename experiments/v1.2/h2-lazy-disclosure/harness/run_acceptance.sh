#!/usr/bin/env bash
# H2 harness — run_acceptance.sh <RUN_ID>
# Executes the MECHANICAL acceptance entries of the run's task (from task-registry.json).
# Entries are executable iff they start with "{PY}" / "{GIT}" / "{HARNESS}" / "PUBLIC_RELEASE=1";
# entries starting with "JUDGMENT:" are recorded but not executed (auditor's job).
# Placeholders: {PY} {GIT} {WT} {RUN_ID} {HARNESS} {H2_REPO}; a trailing "(cwd={WT})" is
# stripped here (in Python, not in shell parameter expansion) and re-applied as a cd prefix.
# Substituted paths are shell-quoted. Exits nonzero if ANY executed entry fails ([15][16][19]).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP_DIR="$(cd "$HERE/.." && pwd)"
PY="${PY:-python3}"
H2_RUNS_ROOT="${H2_RUNS_ROOT:?set H2_RUNS_ROOT}"
RUN_ID="${1:?usage: run_acceptance.sh <RUN_ID>}"
WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
OUT="$EV/acceptance.txt"
if [ ! -f "$EV/receipt.json" ]; then echo "ACCEPT_FAIL reason=NO_RECEIPT"; exit 2; fi
H2_REPO="$(git -C "$EXP_DIR" rev-parse --show-toplevel)" || { echo "ACCEPT_FAIL reason=H2_REPO_UNREADABLE"; exit 2; }
TASK_ID="$("$PY" - "$EV/receipt.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["task_id"])
PYEOF
)" || { echo "ACCEPT_FAIL reason=RECEIPT_READ_FAILED"; exit 2; }

: > "$OUT"
"$PY" - "$EXP_DIR/task-registry.json" "$TASK_ID" > "$EV/acceptance-entries.txt" <<'PYEOF' \
  || { echo "ACCEPT_FAIL reason=ENTRY_GEN_FAILED"; exit 2; }
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
t = [x for x in reg["tasks"] if x["task_id"] == sys.argv[2]][0]
for e in t["acceptance"]["mechanical"]:
    cmd = e["cmd"]
    kind = "EXEC" if cmd.startswith(("{PY}", "{GIT}", "{HARNESS}", "PUBLIC_RELEASE=1")) else "JUDGMENT"
    cwd = "0"
    if kind == "EXEC" and cmd.endswith("(cwd={WT})"):
        cmd = cmd[: -len("(cwd={WT})")].rstrip()
        cwd = "1"
    print(f"{kind}\t{cwd}\t{cmd}")
PYEOF

echo "=== ACCEPTANCE run=$RUN_ID task=$TASK_ID ===" >> "$OUT"
FAIL=0
while IFS=$'\t' read -r kind cwdflag cmd; do
  [ -z "$kind" ] && continue
  if [ "$kind" = "JUDGMENT" ]; then
    printf '=== JUDGMENT (not executed) ===\n%s\n\n' "$cmd" >> "$OUT"
    continue
  fi
  PY_Q="$(printf '%q' "$PY")"; WT_Q="$(printf '%q' "$WT")"
  HARNESS_Q="$(printf '%q' "$HERE")"; H2REPO_Q="$(printf '%q' "$H2_REPO")"
  RUNID_Q="$(printf '%q' "$RUN_ID")"
  run_cmd="${cmd//\{PY\}/$PY_Q}"
  run_cmd="${run_cmd//\{GIT\}/git}"
  run_cmd="${run_cmd//\{WT\}/$WT_Q}"
  run_cmd="${run_cmd//\{RUN_ID\}/$RUNID_Q}"
  run_cmd="${run_cmd//\{TASK_ID\}/$TASK_ID}"
  run_cmd="${run_cmd//\{H2_REPO\}/$H2REPO_Q}"
  run_cmd="${run_cmd//\{HARNESS\}/$HARNESS_Q}"
  if [ "$cwdflag" = "1" ]; then run_cmd="cd $WT_Q && $run_cmd"; fi
  { printf '=== EXEC CMD ===\n%s\n=== OUTPUT ===\n' "$run_cmd"; } >> "$OUT"
  bash -c "$run_cmd" 2>&1 | tee -a "$OUT"
  rc=${PIPESTATUS[0]}
  printf '\n=== RC=%s ===\n\n' "$rc" >> "$OUT"
  if [ "$rc" -ne 0 ]; then FAIL=1; fi
done < "$EV/acceptance-entries.txt"

if [ "$FAIL" -ne 0 ]; then
  echo "ACCEPT_RUN DONE (WITH FAILURES) run_id=$RUN_ID task=$TASK_ID output=$OUT"
  exit 1
fi
echo "ACCEPT_RUN DONE run_id=$RUN_ID task=$TASK_ID output=$OUT"
