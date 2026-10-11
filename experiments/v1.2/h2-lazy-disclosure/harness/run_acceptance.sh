#!/usr/bin/env bash
# H2 harness — run_acceptance.sh <RUN_ID>
# Executes the MECHANICAL acceptance entries of the run's task (from task-registry.json).
# Entries are executable iff they start with "{PY}" or "{GIT}" or "{HARNESS}";
# entries starting with "JUDGMENT:" are recorded but not executed (auditor's job).
# Placeholders: {PY} {GIT} {WT} {HARNESS}; suffix "(cwd={WT})" means cd first.
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
TASK_ID="$("$PY" - "$EV/receipt.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["task_id"])
PYEOF
)"

: > "$OUT"
"$PY" - "$EXP_DIR/task-registry.json" "$TASK_ID" <<'PYEOF' > /tmp/h2_accept_entries.txt
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
t = [x for x in reg["tasks"] if x["task_id"] == sys.argv[2]][0]
for e in t["acceptance"]["mechanical"]:
    cmd = e["cmd"]
    kind = "EXEC" if cmd.startswith(("{PY}", "{GIT}", "{HARNESS}", "PUBLIC_RELEASE=1")) else "JUDGMENT"
    print(f"{kind}\t{cmd}")
PYEOF

echo "=== ACCEPTANCE run=$RUN_ID task=$TASK_ID ===" >> "$OUT"
while IFS=$'\t' read -r kind cmd; do
  [ -z "$kind" ] && continue
  if [ "$kind" = "JUDGMENT" ]; then
    printf '=== JUDGMENT (not executed) ===\n%s\n\n' "$cmd" >> "$OUT"
    continue
  fi
  run_cmd="$cmd"
  prefix=""
  case "$run_cmd" in
    *"(cwd={WT})"*) run_cmd="${run_cmd/(cwd={WT})/}"; prefix="cd {WT} && " ;;
  esac
  run_cmd="${prefix}${run_cmd}"
  run_cmd="${run_cmd//\{PY\}/$PY}"
  run_cmd="${run_cmd//\{GIT\}/git}"
  run_cmd="${run_cmd//\{WT\}/$WT}"
  run_cmd="${run_cmd//\{RUN_ID\}/$RUN_ID}"
  run_cmd="${run_cmd//\{HARNESS\}/$HERE}"
  {
    printf '=== EXEC CMD ===\n%s\n=== OUTPUT ===\n' "$run_cmd"
  } >> "$OUT"
  bash -c "$run_cmd" 2>&1 | tee -a "$OUT"
  rc=${PIPESTATUS[0]}
  printf '\n=== RC=%s ===\n\n' "$rc" >> "$OUT"
done < /tmp/h2_accept_entries.txt
echo "ACCEPT_RUN DONE run_id=$RUN_ID task=$TASK_ID output=$OUT"
