#!/usr/bin/env bash
# H2 harness — prepare_run.sh <RUN_ID> <ARM>       ARM ∈ {control, variant}
# Fail-closed: any mismatch aborts with PREPARE_FAIL and a machine-readable reason.
# Mechanically: creates the run worktree at the task base, asserts target binding (P1),
# delivers the carrier for the arm with a sha256 receipt (P2), and writes task/contract files.
# Env: H2_RUNS_ROOT (persistent, non-/tmp) is REQUIRED. PY overrides the python binary.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP_DIR="$(cd "$HERE/.." && pwd)"
H2_WT="$(git -C "$EXP_DIR" rev-parse --show-toplevel)"
PY="${PY:-python3}"

RUN_ID="${1:?usage: prepare_run.sh <RUN_ID> <ARM>}"
ARM="${2:?usage: prepare_run.sh <RUN_ID> <ARM>}"
case "$ARM" in control|variant) ;; *) echo "PREPARE_FAIL reason=BAD_ARM value=$ARM"; exit 2 ;; esac

H2_RUNS_ROOT="${H2_RUNS_ROOT:-}"
if [ -z "$H2_RUNS_ROOT" ]; then
  echo "PREPARE_FAIL reason=H2_RUNS_ROOT_UNSET (must be a persistent, non-/tmp directory)"; exit 2
fi
# Normalize before matching: resolve symlinks where possible, case-fold, squash duplicate
# slashes, strip the trailing slash, and reject empty/"/" — so //tmp, /tmp/, /TMP,
# /private//tmp etc. cannot bypass the guard. (v2: v1 failed open on `//tmp` — the failing
# control and this correction are recorded in precondition/p1-p2-dryrun.txt [9]/[9b].)
R_ROOT="$H2_RUNS_ROOT"
NORM="$(cd "$R_ROOT" 2>/dev/null && pwd -P)" || NORM=""
if [ -n "$NORM" ]; then R_ROOT="$NORM"; fi
R_LC="$(printf '%s' "$R_ROOT" | tr 'A-Z' 'a-z' | tr -s '/')"
R_LC="${R_LC%/}"
case "$R_LC" in
  ""|"/") echo "PREPARE_FAIL reason=VOLATILE_OR_ROOT $H2_RUNS_ROOT"; exit 2 ;;
  /tmp|/private/tmp|/tmp/*|/private/tmp/*) echo "PREPARE_FAIL reason=VOLATILE_ROOT $H2_RUNS_ROOT"; exit 2 ;;
esac

if [ "$RUN_ID" = "H2-DRYRUN" ] || [ "$RUN_ID" = "H2-DRYRUN-control" ] || [ "$RUN_ID" = "H2-DRYRUN-variant" ]; then
  # P1/P2 self-test path: exercises the SAME worktree/carrier mechanics on task t01.
  # Workspaces live at worktrees/<RUN_ID> + evidence/<RUN_ID> so the generic collect
  # path (collect_run.sh <RUN_ID>) works on them unchanged. Never counted as a run.
  TASK_ID="t01"
  BASE_SHA="c08f6f8b3bbe57853a56adf3c2847e806bbb60a3"
  REG="$EXP_DIR/task-registry.json"
  WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
  EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
else
  PLAN="$EXP_DIR/harness/run-plan.json"
  REG="$EXP_DIR/task-registry.json"
  INFO="$("$PY" - "$PLAN" "$REG" "$RUN_ID" "$ARM" <<'PYEOF'
import json, sys
plan = json.load(open(sys.argv[1], encoding="utf-8"))
reg = json.load(open(sys.argv[2], encoding="utf-8"))
rid, arm = sys.argv[3], sys.argv[4]
rows = [r for r in plan if r["run_id"] == rid]
if len(rows) != 1:
    print("__NO_RUN_ROW__"); raise SystemExit(0)
row = rows[0]
if row["arm"] != arm:
    print(f"__ARM_MISMATCH__ row_arm={row['arm']}"); raise SystemExit(0)
tasks = {t["task_id"]: t for t in reg["tasks"]}
t = tasks.get(row["task_id"])
if t is None:
    print(f"__NO_TASK__ {row['task_id']}"); raise SystemExit(0)
print(f"{row['task_id']} {t['base_sha']}")
PYEOF
)"
  case "$INFO" in __*) echo "PREPARE_FAIL reason=$INFO"; exit 2 ;; esac
  TASK_ID="${INFO%% *}"
  BASE_SHA="${INFO##* }"
  WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
  EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
fi
if [ -e "$WT" ]; then echo "PREPARE_FAIL reason=WORKTREE_EXISTS $WT"; exit 2; fi
mkdir -p "$EV"

git -C "$H2_WT" worktree add "$WT" --detach "$BASE_SHA" >/dev/null 2>&1 \
  || { echo "PREPARE_FAIL reason=WORKTREE_ADD_FAILED base=$BASE_SHA"; exit 2; }
ACTUAL="$(git -C "$WT" rev-parse HEAD)"
if [ "$ACTUAL" != "$BASE_SHA" ]; then
  echo "PREPARE_FAIL reason=WRONG_BASE expected=$BASE_SHA actual=$ACTUAL"; exit 2
fi
git -C "$WT" status --porcelain > "$EV/status-pre.txt"

if [ "$ARM" = "control" ]; then
  if [ -e "$WT/CODEBUDDY.md" ]; then
    echo "PREPARE_FAIL reason=TREATMENT_CONTAMINATED codebuddy_present_at_root"; exit 2
  fi
  AGENTS_BLOB="$(git -C "$WT" rev-parse "$BASE_SHA:AGENTS.md")"
  RULES_BLOB="$(git -C "$WT" rev-parse "$BASE_SHA:RULES.md")"
  CARRIER_EXPECTED="canonical_full_text (AGENTS.md@$BASE_SHA + RULES.md@$BASE_SHA)"
  CARRIER_HASH="agents_blob:$AGENTS_BLOB rules_blob:$RULES_BLOB"
  CB_PRESENT=false
else
  VAR_HASH="$("$PY" - "$EXP_DIR/variant-manifest.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["freeze"]["VARIANT_HASH"])
PYEOF
)"
  cp "$EXP_DIR/carriers/H2_LEAN_BOOTSTRAP.md" "$WT/CODEBUDDY.md"
  GOT="$(shasum -a 256 "$WT/CODEBUDDY.md" | awk '{print $1}')"
  if [ "$GOT" != "$VAR_HASH" ]; then
    rm -f "$WT/CODEBUDDY.md"
    echo "PREPARE_FAIL reason=CARRIER_HASH_MISMATCH got=$GOT want=$VAR_HASH"; exit 2
  fi
  CARRIER_EXPECTED="carriers/H2_LEAN_BOOTSTRAP.md -> CODEBUDDY.md"
  CARRIER_HASH="$GOT"
  CB_PRESENT=true
fi

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PY" - "$EV/receipt.json" "$RUN_ID" "$TASK_ID" "$ARM" "$WT" "$BASE_SHA" "$ACTUAL" \
        "$CARRIER_EXPECTED" "$CARRIER_HASH" "$CB_PRESENT" "$TS" <<'PYEOF'
import json, sys
(p, rid, tid, arm, wt, base, head, ce, ch, cbp, ts) = sys.argv[1:12]
json.dump({
    "run_id": rid, "task_id": tid, "arm": arm, "worktree": wt,
    "expected_base": base, "actual_head": head,
    "carrier_expected": ce, "carrier_hash": ch,
    "codebuddy_present": cbp == "true", "ts": ts, "prepare": "OK",
}, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PYEOF

"$PY" - "$REG" "$TASK_ID" > "$EV/task.txt" <<'PYEOF'
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
t = [x for x in reg["tasks"] if x["task_id"] == sys.argv[2]][0]
sys.stdout.write(t["task_text"] + "\n")
PYEOF

"$PY" - "$HERE" "$EV" "$WT" "$BASE_SHA" "$ARM" <<'PYEOF'
import sys
here, ev, wt, base, arm = sys.argv[1:6]
tpl = open(f"{here}/worker-brief-template.md", encoding="utf-8").read()
block = open(f"{here}/arm-blocks/{arm}.md", encoding="utf-8").read()
import json
receipt = json.load(open(f"{ev}/receipt.json", encoding="utf-8"))
rid = receipt["run_id"]
task = open(f"{ev}/task.txt", encoding="utf-8").read().rstrip("\n")
out = (tpl
       .replace("<RUN_ID>", rid)
       .replace("<TASK_ID>", receipt["task_id"])
       .replace("<BASE_SHA>", base)
       .replace("<RUN_WORKTREE_ABS>", wt)
       .replace("<TASK_TEXT>", task)
       .replace("<REPORT_PATH>", f"{ev}/report.md")
       .replace("<REPORT_TEMPLATE_PATH>", f"{here}/worker-report-template.md")
       .replace("<BOOTSTRAP_DELIVERY_BLOCK>", block))
open(f"{ev}/contract.md", "w", encoding="utf-8").write(out)
PYEOF

echo "PREPARE_RUN OK run_id=$RUN_ID arm=$ARM task=$TASK_ID base=$BASE_SHA"
echo "  worktree = $WT"
echo "  evidence = $EV"
echo "  carrier  = $CARRIER_EXPECTED"
echo "  carrier_hash = $CARRIER_HASH"
