#!/usr/bin/env bash
# H2 harness — prepare_run.sh <RUN_ID> <ARM>       ARM ∈ {control, variant}
# Fail-closed: any mismatch aborts with PREPARE_FAIL and a machine-readable reason.
#
# Delivery v5 (symmetric slots; same governance era everywhere):
#   BOTH arms : CODEBUDDY.md  = the arm's guidance carrier in the SAME recognized slot
#                               (control: current AGENTS.md verbatim full text with a thin
#                                header/footer; variant: the frozen lean carrier)
#               H2_RULES.md   = placed copy of the CURRENT RULES.md
#               H2_WARM/      = placed copies of the CURRENT routed WARM owners
#                               (source list = routes-h2.json S3 destinations, single source)
#   Receipts: carrier_kind, carrier_hash, h2_rules_sha256, warm_bundle_sha256,
#             materials_commit, model_tier.
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
# strip the trailing slash, and reject empty/"/" or relative roots. (v2 fixed the //tmp
# fail-open; v3 added OS temp roots + trim; v4 resolves non-existent paths through their
# deepest existing ancestor; controls in precondition/p1-p2-dryrun.txt.)
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

# ---- materials validation FIRST, before any run-id allocation (R8-9) ----
MATERIALS_COMMIT="$(git -C "$H2_WT" rev-parse HEAD)" \
  || { echo "PREPARE_FAIL reason=MATERIALS_COMMIT_UNREADABLE"; exit 2; }
DIRTY="$(git -C "$H2_WT" status --porcelain -- . ':(exclude)experiments/v1.2/h2-lazy-disclosure/runs' ':(exclude).workbuddy')"
if [ -n "$DIRTY" ]; then
  echo "PREPARE_FAIL reason=MATERIALS_DIRTY (delivery sources must come from a clean, frozen commit; run records under runs/ are exempt)"
  echo "$DIRTY" | head -5
  exit 2
fi
git -C "$H2_WT" cat-file -e "$MATERIALS_COMMIT:RULES.md" 2>/dev/null \
  || { echo "PREPARE_FAIL reason=SOURCE_RULES_MISSING"; exit 2; }
git -C "$H2_WT" cat-file -e "$MATERIALS_COMMIT:AGENTS.md" 2>/dev/null \
  || { echo "PREPARE_FAIL reason=SOURCE_AGENTS_MISSING"; exit 2; }

if [ "$RUN_ID" = "H2-DRYRUN" ] || [ "$RUN_ID" = "H2-DRYRUN-control" ] || [ "$RUN_ID" = "H2-DRYRUN-variant" ]; then
  TASK_ID="t01"
  BASE_SHA="c08f6f8b3bbe57853a56adf3c2847e806bbb60a3"
  MODEL_TIER="default"
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
print(f"{row['task_id']} {t['base_sha']} {row.get('model_tier', 'default')}")
PYEOF
)" || { echo "PREPARE_FAIL reason=RUN_LOOKUP_FAILED"; exit 2; }
  case "$INFO" in __*) echo "PREPARE_FAIL reason=$INFO"; exit 2 ;; esac
  TASK_ID="${INFO%% *}"
  REST="${INFO#* }"
  BASE_SHA="${REST%% *}"
  MODEL_TIER="${REST##* }"
  WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
  EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
fi
if [ -e "$WT" ]; then echo "PREPARE_FAIL reason=WORKTREE_EXISTS $WT"; exit 2; fi
if [ -e "$EV" ]; then echo "PREPARE_FAIL reason=EVIDENCE_EXISTS $EV (silent rerun of a run id is forbidden; register a new run id)"; exit 2; fi
mkdir -p "$EV" || { echo "PREPARE_FAIL reason=MKDIR_EVIDENCE_FAILED $EV"; exit 2; }

# Transactional rollback for failures AFTER allocation (R8-9): remove the half-created
# worktree and move the (partial) evidence aside, so the frozen run id can be re-prepared
# after the operator fixes the problem without tripping the EXISTS guards forever.
alloc_rollback() {
  git -C "$H2_WT" worktree remove --force "$WT" >/dev/null 2>&1 || true
  mv "$EV" "$EV.failed-$(date -u +%Y%m%dT%H%M%SZ)" 2>/dev/null || true
}
fatal_alloc() {
  echo "PREPARE_FAIL reason=$1 (allocation rolled back: worktree removed; failed evidence preserved beside $EV)"
  alloc_rollback
  exit 2
}

git -C "$H2_WT" worktree add "$WT" --detach "$BASE_SHA" >/dev/null 2>&1 \
  || fatal_alloc "WORKTREE_ADD_FAILED base=$BASE_SHA"
ACTUAL="$(git -C "$WT" rev-parse HEAD)" || fatal_alloc "HEAD_UNREADABLE"
if [ "$ACTUAL" != "$BASE_SHA" ]; then
  fatal_alloc "WRONG_BASE expected=$BASE_SHA actual=$ACTUAL"
fi
git -C "$WT" status --porcelain > "$EV/status-pre.txt" || fatal_alloc "STATUS_SNAPSHOT_FAILED"
git -C "$WT" status --porcelain --ignored > "$EV/status-pre-ignored.txt" || fatal_alloc "STATUS_SNAPSHOT_FAILED"

# ---- delivery v5 (symmetric slots; same-era placed texts; commit-sourced reads) ----
SRC_RULES="$H2_WT/RULES.md"
SRC_AGENTS="$H2_WT/AGENTS.md"

for leftover in CODEBUDDY.md H2_RULES.md H2_AGENTS.md H2_WARM; do
  if [ -e "$WT/$leftover" ]; then
    fatal_alloc "DELIVERY_SLOT_CONTAMINATED $leftover"
  fi
done

# All delivery reads come from MATERIALS_COMMIT objects (R6-2: working-tree bytes never leak in).
git -C "$H2_WT" show "$MATERIALS_COMMIT:RULES.md" > "$WT/H2_RULES.md" \
  || fatal_alloc "COPY_RULES_FAILED"
RULES_HASH="$(shasum -a 256 "$WT/H2_RULES.md" | awk '{print $1}')"

if [ "$ARM" = "variant" ]; then
  VAR_HASH="$("$PY" - "$EXP_DIR/variant-manifest.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["freeze"]["VARIANT_HASH"])
PYEOF
)" || fatal_alloc "MANIFEST_UNREADABLE"
  cp "$EXP_DIR/carriers/H2_LEAN_BOOTSTRAP.md" "$WT/CODEBUDDY.md" \
    || fatal_alloc "COPY_CARRIER_FAILED"
  GOT="$(shasum -a 256 "$WT/CODEBUDDY.md" | awk '{print $1}')"
  if [ "$GOT" != "$VAR_HASH" ]; then
    fatal_alloc "CARRIER_HASH_MISMATCH got=$GOT want=$VAR_HASH"
  fi
  CARRIER_KIND="variant_lean_v1"
  CARRIER_HASH="$GOT"
else
  # control carrier = thin header + current AGENTS.md VERBATIM + thin footer, in the SAME
  # recognized slot as the variant carrier (so runtime guidance selection is symmetric).
  "$PY" - "$HERE/control-carrier-header.md" "$H2_WT" "$MATERIALS_COMMIT" "$WT/CODEBUDDY.md" <<'PYEOF' \
    || fatal_alloc "CONTROL_CARRIER_COMPOSE_FAILED"
import pathlib, subprocess, sys
header = pathlib.Path(sys.argv[1]).read_bytes()
agents = subprocess.run(["git", "-C", sys.argv[2], "show", f"{sys.argv[3]}:AGENTS.md"],
                        capture_output=True, check=True).stdout
out_path = pathlib.Path(sys.argv[4])
footer = ("\n---\n（以上为当前时代 AGENTS.md 的逐字全文，由 harness 投放；配套 B 层不变量副本 = "
          "H2_RULES.md；治理性 references 读取一律使用 H2_WARM/ 副本。本臂 = 全文投递。）\n").encode()
out = header + agents + footer
assert agents in out, "verbatim AGENTS.md bytes must be embedded"
out_path.write_bytes(out)
PYEOF
  CARRIER_KIND="control_full_v1"
  CARRIER_HASH="$(shasum -a 256 "$WT/CODEBUDDY.md" | awk '{print $1}')"
fi

# ---- WARM bundle: current-era copies of the routed WARM owners (source list = routes-h2 S3;
#      bytes read from MATERIALS_COMMIT objects, never the working tree — R6-2) ----
WARM_HASH="$("$PY" - "$EXP_DIR/routes-h2.json" "$H2_WT" "$MATERIALS_COMMIT" "$WT" <<'PYEOF'
import hashlib, json, pathlib, subprocess, sys
routes = json.load(open(sys.argv[1], encoding="utf-8"))["routes"]
wt_repo, commit, wt = sys.argv[2], sys.argv[3], pathlib.Path(sys.argv[4])
dests = sorted({r["destination"] for r in routes if r.get("surface") == "S3"})
if not dests:
    print("EMPTY_BUNDLE"); raise SystemExit(3)
lines = []
for dest in dests:
    proc = subprocess.run(["git", "-C", wt_repo, "show", f"{commit}:{dest}"], capture_output=True)
    if proc.returncode != 0:
        print(f"MISSING_SOURCE {dest}"); raise SystemExit(4)
    dst = wt / "H2_WARM" / dest
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(proc.stdout)
    lines.append(f"{dest} {hashlib.sha256(dst.read_bytes()).hexdigest()}")
print(hashlib.sha256("\n".join(lines).encode()).hexdigest())
PYEOF
)" || fatal_alloc "WARM_BUNDLE_FAILED $WARM_HASH"

RUFF_WT_HASH=""
if [ -f "$WT/ruff.toml" ]; then
  RUFF_WT_HASH="$(shasum -a 256 "$WT/ruff.toml" | awk '{print $1}')"
fi

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PY" - "$EV/receipt.json" "$RUN_ID" "$TASK_ID" "$ARM" "$WT" "$BASE_SHA" "$ACTUAL" \
        "$CARRIER_KIND" "$CARRIER_HASH" "$RULES_HASH" "$WARM_HASH" \
        "$MATERIALS_COMMIT" "$MODEL_TIER" "$RUFF_WT_HASH" "$TS" <<'PYEOF' \
  || fatal_alloc "RECEIPT_WRITE_FAILED"
import json, sys
(p, rid, tid, arm, wt, base, head, ckind, ch, rh, wh, mc, mt, rth, ts) = sys.argv[1:16]
json.dump({
    "run_id": rid, "task_id": tid, "arm": arm, "worktree": wt,
    "expected_base": base, "actual_head": head,
    "carrier_kind": ckind, "carrier_hash": ch,
    "h2_rules_sha256": rh, "warm_bundle_sha256": wh,
    "materials_commit": mc, "model_tier": mt,
    "ruff_toml_worktree_sha256": rth,
    "codebuddy_present": True, "ts": ts, "prepare": "OK",
}, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PYEOF

"$PY" - "$REG" "$TASK_ID" > "$EV/task.txt" <<'PYEOF' \
  || fatal_alloc "TASK_WRITE_FAILED"
import json, sys
reg = json.load(open(sys.argv[1], encoding="utf-8"))
t = [x for x in reg["tasks"] if x["task_id"] == sys.argv[2]][0]
sys.stdout.write(t["task_text"] + "\n")
PYEOF

"$PY" - "$HERE" "$EV" "$WT" "$BASE_SHA" "$ARM" "$MODEL_TIER" <<'PYEOF' \
  || fatal_alloc "CONTRACT_WRITE_FAILED"
import json, sys
here, ev, wt, base, arm, model_tier = sys.argv[1:7]
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
       .replace("<MODEL_TIER>", model_tier)
       .replace("<REPORT_PATH>", f"{ev}/report.md")
       .replace("<REPORT_TEMPLATE_PATH>", f"{here}/worker-report-template.md")
       .replace("<BOOTSTRAP_DELIVERY_BLOCK>", block))
open(f"{ev}/contract.md", "w", encoding="utf-8").write(out)
PYEOF

echo "PREPARE_RUN OK run_id=$RUN_ID arm=$ARM task=$TASK_ID base=$BASE_SHA"
echo "  worktree = $WT"
echo "  evidence = $EV"
echo "  carrier_kind = $CARRIER_KIND"
echo "  carrier_hash = $CARRIER_HASH"
echo "  h2_rules_sha256 = $RULES_HASH"
echo "  warm_bundle_sha256 = $WARM_HASH"
echo "  materials_commit = $MATERIALS_COMMIT"
echo "  model_tier = $MODEL_TIER"
