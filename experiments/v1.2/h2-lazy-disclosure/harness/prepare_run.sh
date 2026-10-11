#!/usr/bin/env bash
# H2 harness — prepare_run.sh <RUN_ID> <ARM>       ARM ∈ {control, variant}
# Fail-closed: any mismatch aborts with PREPARE_FAIL and a machine-readable reason.
# Mechanically: creates the run worktree at the task base (P1), delivers the CURRENT-ERA
# governance bootstrap for the arm with sha256 receipts (P2), and writes task/contract files.
#
# Delivery (v4, same governance era for both arms — the ONLY arm difference is the
# disclosure strategy; see protocol §2.1 / variant-manifest.json):
#   BOTH arms : H2_RULES.md  = a placed copy of the CURRENT RULES.md (materials worktree)
#   CONTROL   : H2_AGENTS.md = a placed copy of the CURRENT AGENTS.md (full-text delivery)
#   VARIANT   : CODEBUDDY.md = the frozen lean carrier (VARIANT_HASH)
# Env: H2_RUNS_ROOT (persistent, non-/tmp, absolute) is REQUIRED. PY overrides python.
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
# Normalize before matching: trim whitespace, resolve symlinks where possible (incl. the
# deepest existing ancestor for not-yet-existing paths), case-fold, squash duplicate slashes,
# strip the trailing slash, and reject empty/"/" or relative roots — so //tmp, /tmp/, /TMP,
# /private//tmp, ' /tmp', /var/tmp, $TMPDIR and symlinked-parent spellings cannot bypass the
# guard. (v2 fixed the //tmp fail-open; v3 added OS temp roots + trim; v4 resolves
# non-existent paths through their deepest existing ancestor; controls in
# precondition/p1-p2-dryrun.txt [9]/[9b]/[9c]/[10].)
R_TRIM="$(printf '%s' "$H2_RUNS_ROOT" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"
case "$R_TRIM" in
  "") echo "PREPARE_FAIL reason=H2_RUNS_ROOT_UNSET (must be a persistent, non-/tmp directory)"; exit 2 ;;
  /*) ;;
  *) echo "PREPARE_FAIL reason=ROOT_NOT_ABSOLUTE $H2_RUNS_ROOT"; exit 2 ;;
esac
if [ -d "$R_TRIM" ]; then
  NORM="$(cd "$R_TRIM" && pwd -P)" || NORM=""
  R_MATCH="${NORM:-$R_TRIM}"
else
  PARENT="$(dirname "$R_TRIM")"
  while [ "$PARENT" != "/" ] && [ ! -d "$PARENT" ]; do PARENT="$(dirname "$PARENT")"; done
  PN="$(cd "$PARENT" 2>/dev/null && pwd -P)" || PN=""
  if [ -n "$PN" ]; then R_MATCH="$PN/$(basename "$R_TRIM")"; else R_MATCH="$R_TRIM"; fi
fi
R_LC="$(printf '%s' "$R_MATCH" | tr 'A-Z' 'a-z' | tr -s '/')"
R_LC="${R_LC%/}"
case "$R_LC" in
  ""|"/") echo "PREPARE_FAIL reason=VOLATILE_OR_ROOT $H2_RUNS_ROOT"; exit 2 ;;
  /tmp|/private/tmp|/tmp/*|/private/tmp/*|\
  /var/tmp|/private/var/tmp|/var/tmp/*|/private/var/tmp/*|\
  /var/folders|/private/var/folders|/var/folders/*|/private/var/folders/*)
    echo "PREPARE_FAIL reason=VOLATILE_ROOT $H2_RUNS_ROOT"; exit 2 ;;
esac
H2_RUNS_ROOT="$R_TRIM"

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
)" || { echo "PREPARE_FAIL reason=RUN_LOOKUP_FAILED"; exit 2; }
  case "$INFO" in __*) echo "PREPARE_FAIL reason=$INFO"; exit 2 ;; esac
  TASK_ID="${INFO%% *}"
  BASE_SHA="${INFO##* }"
  WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
  EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
fi
if [ -e "$WT" ]; then echo "PREPARE_FAIL reason=WORKTREE_EXISTS $WT"; exit 2; fi
if [ -e "$EV" ]; then echo "PREPARE_FAIL reason=EVIDENCE_EXISTS $EV (silent rerun of a run id is forbidden; register a new run id)"; exit 2; fi
mkdir -p "$EV" || { echo "PREPARE_FAIL reason=MKDIR_EVIDENCE_FAILED $EV"; exit 2; }

git -C "$H2_WT" worktree add "$WT" --detach "$BASE_SHA" >/dev/null 2>&1 \
  || { echo "PREPARE_FAIL reason=WORKTREE_ADD_FAILED base=$BASE_SHA"; exit 2; }
ACTUAL="$(git -C "$WT" rev-parse HEAD)" || { echo "PREPARE_FAIL reason=HEAD_UNREADABLE"; exit 2; }
if [ "$ACTUAL" != "$BASE_SHA" ]; then
  echo "PREPARE_FAIL reason=WRONG_BASE expected=$BASE_SHA actual=$ACTUAL"; exit 2
fi
git -C "$WT" status --porcelain > "$EV/status-pre.txt" \
  || { echo "PREPARE_FAIL reason=STATUS_SNAPSHOT_FAILED"; exit 2; }

# ---- delivery (v4): same-era placed texts for both arms; carrier for variant ----
MATERIALS_COMMIT="$(git -C "$H2_WT" rev-parse HEAD)" \
  || { echo "PREPARE_FAIL reason=MATERIALS_COMMIT_UNREADABLE"; exit 2; }
SRC_RULES="$H2_WT/RULES.md"
SRC_AGENTS="$H2_WT/AGENTS.md"
[ -f "$SRC_RULES" ] || { echo "PREPARE_FAIL reason=SOURCE_RULES_MISSING $SRC_RULES"; exit 2; }
[ -f "$SRC_AGENTS" ] || { echo "PREPARE_FAIL reason=SOURCE_AGENTS_MISSING $SRC_AGENTS"; exit 2; }

for leftover in H2_RULES.md H2_AGENTS.md CODEBUDDY.md; do
  if [ -e "$WT/$leftover" ]; then
    echo "PREPARE_FAIL reason=DELIVERY_SLOT_CONTAMINATED $leftover"; exit 2
  fi
done

cp "$SRC_RULES" "$WT/H2_RULES.md" || { echo "PREPARE_FAIL reason=COPY_RULES_FAILED"; exit 2; }
RULES_HASH="$(shasum -a 256 "$WT/H2_RULES.md" | awk '{print $1}')"

if [ "$ARM" = "variant" ]; then
  VAR_HASH="$("$PY" - "$EXP_DIR/variant-manifest.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["freeze"]["VARIANT_HASH"])
PYEOF
)" || { echo "PREPARE_FAIL reason=MANIFEST_UNREADABLE"; exit 2; }
  cp "$EXP_DIR/carriers/H2_LEAN_BOOTSTRAP.md" "$WT/CODEBUDDY.md" \
    || { echo "PREPARE_FAIL reason=COPY_CARRIER_FAILED"; exit 2; }
  GOT="$(shasum -a 256 "$WT/CODEBUDDY.md" | awk '{print $1}')"
  if [ "$GOT" != "$VAR_HASH" ]; then
    rm -f "$WT/CODEBUDDY.md" "$WT/H2_RULES.md"
    echo "PREPARE_FAIL reason=CARRIER_HASH_MISMATCH got=$GOT want=$VAR_HASH"; exit 2
  fi
  CARRIER_EXPECTED="carriers/H2_LEAN_BOOTSTRAP.md -> CODEBUDDY.md; current RULES.md -> H2_RULES.md"
  CARRIER_HASH="$GOT"
  AGENTS_HASH=""
  CB_PRESENT=true
else
  cp "$SRC_AGENTS" "$WT/H2_AGENTS.md" || { echo "PREPARE_FAIL reason=COPY_AGENTS_FAILED"; exit 2; }
  AGENTS_HASH="$(shasum -a 256 "$WT/H2_AGENTS.md" | awk '{print $1}')"
  CARRIER_EXPECTED="current AGENTS.md -> H2_AGENTS.md; current RULES.md -> H2_RULES.md (no carrier)"
  CARRIER_HASH=""
  CB_PRESENT=false
fi

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PY" - "$EV/receipt.json" "$RUN_ID" "$TASK_ID" "$ARM" "$WT" "$BASE_SHA" "$ACTUAL" \
        "$CARRIER_EXPECTED" "$CARRIER_HASH" "$AGENTS_HASH" "$RULES_HASH" \
        "$MATERIALS_COMMIT" "$CB_PRESENT" "$TS" <<'PYEOF' \
  || { echo "PREPARE_FAIL reason=RECEIPT_WRITE_FAILED"; exit 2; }
import json, sys
(p, rid, tid, arm, wt, base, head, ce, ch, ah, rh, mc, cbp, ts) = sys.argv[1:15]
json.dump({
    "run_id": rid, "task_id": tid, "arm": arm, "worktree": wt,
    "expected_base": base, "actual_head": head,
    "carrier_expected": ce, "carrier_hash": ch,
    "h2_agents_sha256": ah, "h2_rules_sha256": rh,
    "materials_commit": mc, "codebuddy_present": cbp == "true", "ts": ts, "prepare": "OK",
}, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PYEOF

"$PY" - "$REG" "$TASK_ID" > "$EV/task.txt" <<'PYEOF' \
  || { echo "PREPARE_FAIL reason=TASK_WRITE_FAILED"; exit 2; }
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
t = [x for x in reg["tasks"] if x["task_id"] == sys.argv[2]][0]
sys.stdout.write(t["task_text"] + "\n")
PYEOF

"$PY" - "$HERE" "$EV" "$WT" "$BASE_SHA" "$ARM" <<'PYEOF' \
  || { echo "PREPARE_FAIL reason=CONTRACT_WRITE_FAILED"; exit 2; }
import json, sys
here, ev, wt, base, arm = sys.argv[1:6]
tpl = open(f"{here}/worker-brief-template.md", encoding="utf-8").read()
block = open(f"{here}/arm-blocks/{arm}.md", encoding="utf-8").read()
receipt = json.load(open(f"{ev}/receipt.json", encoding="utf-8"))
task = open(f"{ev}/task.txt", encoding="utf-8").read().rstrip("\n")
out = (tpl
       .replace("<RUN_ID>", receipt["run_id"])
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
echo "  delivery = $CARRIER_EXPECTED"
echo "  carrier_hash = ${CARRIER_HASH:-n/a}"
echo "  h2_rules_sha256 = $RULES_HASH"
echo "  h2_agents_sha256 = ${AGENTS_HASH:-n/a}"
echo "  materials_commit = $MATERIALS_COMMIT"
