#!/usr/bin/env bash
# H2 harness — collect_run.sh <RUN_ID>
# Captures the worker's diff (non-destructively), status, and telemetry log into the
# evidence dir. Never uses `reset --hard`; only `git reset` (mixed) to unstage afterwards.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP_DIR="$(cd "$HERE/.." && pwd)"
PY="${PY:-python3}"
H2_RUNS_ROOT="${H2_RUNS_ROOT:?set H2_RUNS_ROOT}"
RUN_ID="${1:?usage: collect_run.sh <RUN_ID>}"
WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
if [ ! -d "$WT" ]; then echo "COLLECT_FAIL reason=NO_WORKTREE $WT"; exit 2; fi
if [ ! -f "$EV/receipt.json" ]; then echo "COLLECT_FAIL reason=NO_RECEIPT $EV"; exit 2; fi

BASE="$("$PY" - "$EV/receipt.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["expected_base"])
PYEOF
)"
HEAD="$(git -C "$WT" rev-parse HEAD)"
WORKER_COMMITTED=NO
if [ "$HEAD" != "$BASE" ]; then WORKER_COMMITTED=YES; fi

git -C "$WT" add -A
git -C "$WT" reset -q -- CODEBUDDY.md .h2-telemetry.log 2>/dev/null || true
git -C "$WT" diff --cached --binary > "$EV/diff.patch"
git -C "$WT" diff --cached --stat > "$EV/diffstat.txt" 2>/dev/null || : > "$EV/diffstat.txt"
git -C "$WT" status --porcelain > "$EV/status-after.txt"
git -C "$WT" reset -q

if [ -f "$WT/.h2-telemetry.log" ]; then cp "$WT/.h2-telemetry.log" "$EV/telemetry.log"
else : > "$EV/telemetry.log"; fi

# P2 re-check at collection: carrier delivery must still be intact (variant-manifest.json).
VAR_HASH="$("$PY" - "$EXP_DIR/variant-manifest.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["freeze"]["VARIANT_HASH"])
PYEOF
)"
RECHECK="$EV/carrier-recheck.txt"
if grep -q '"arm": "variant"' "$EV/receipt.json"; then
  if [ ! -f "$WT/CODEBUDDY.md" ]; then
    echo "CARRIER_RECHECK = FAIL (variant carrier missing at collection) — RUN_INVALID candidate" > "$RECHECK"
  else
    GOT="$(shasum -a 256 "$WT/CODEBUDDY.md" | awk '{print $1}')"
    if [ "$GOT" = "$VAR_HASH" ]; then
      echo "CARRIER_RECHECK = OK (variant, sha256=$GOT)" > "$RECHECK"
    else
      echo "CARRIER_RECHECK = FAIL (variant sha256=$GOT != $VAR_HASH) — RUN_INVALID candidate" > "$RECHECK"
    fi
  fi
else
  if [ -e "$WT/CODEBUDDY.md" ]; then
    echo "CARRIER_RECHECK = FAIL (control: CODEBUDDY.md unexpectedly present) — RUN_INVALID candidate" > "$RECHECK"
  else
    echo "CARRIER_RECHECK = OK (control, no carrier file)" > "$RECHECK"
  fi
fi
cat "$RECHECK"

DIFF_SHA="$(shasum -a 256 "$EV/diff.patch" | awk '{print $1}')"
TEL_SHA="$(shasum -a 256 "$EV/telemetry.log" | awk '{print $1}')"
if grep -q "FAIL" "$RECHECK"; then
  echo "COLLECT_RUN INVALID (carrier recheck FAIL) run_id=$RUN_ID head=$HEAD base=$BASE"
  echo "  diff_sha256=$DIFF_SHA telemetry_sha256=$TEL_SHA (evidence captured)"
  echo "  -> register this run as INVALID in run-registry.md (carrier not intact at collection)"
  exit 3
fi
echo "COLLECT_RUN OK run_id=$RUN_ID head=$HEAD base=$BASE worker_committed=$WORKER_COMMITTED"
echo "  diff_sha256=$DIFF_SHA"
echo "  telemetry_sha256=$TEL_SHA"
echo "  diffstat:"
sed 's/^/    /' "$EV/diffstat.txt"
