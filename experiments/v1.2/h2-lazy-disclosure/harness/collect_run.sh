#!/usr/bin/env bash
# H2 harness — collect_run.sh <RUN_ID>
# Captures the worker's diff (non-destructively, rc-checked), status, and telemetry into the
# evidence dir; re-verifies the delivered governance texts at collection (P2 collection side);
# exits 3 when the recheck fails (fail-closed: the run must be registered INVALID).
# Never uses `reset --hard`; only `git reset` (mixed) to unstage afterwards.
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
fail() { echo "COLLECT_FAIL reason=$1"; exit "${2:-4}"; }

BASE="$("$PY" - "$EV/receipt.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["expected_base"])
PYEOF
)" || fail RECEIPT_READ_FAILED 2
HEAD="$(git -C "$WT" rev-parse HEAD)" || fail HEAD_UNREADABLE 2
WORKER_COMMITTED=NO
if [ "$HEAD" != "$BASE" ]; then WORKER_COMMITTED=YES; fi

# --- capture (rc-checked; [9] committed changes are captured vs base; [11] no silent capture failure) ---
git -C "$WT" add -A || fail CAPTURE_ADD_FAILED
git -C "$WT" reset -q -- CODEBUDDY.md .h2-telemetry.log H2_RULES.md H2_AGENTS.md 2>/dev/null || true
if [ "$HEAD" != "$BASE" ]; then
  git -C "$WT" diff --binary "$BASE" > "$EV/diff.patch" || fail CAPTURE_DIFF_FAILED
else
  git -C "$WT" diff --cached --binary > "$EV/diff.patch" || fail CAPTURE_DIFF_FAILED
fi
git -C "$WT" diff --cached --stat > "$EV/diffstat.txt" 2>/dev/null || : > "$EV/diffstat.txt"
git -C "$WT" status --porcelain > "$EV/status-after.txt" || fail CAPTURE_STATUS_FAILED
git -C "$WT" reset -q || fail CAPTURE_RESET_FAILED

if [ -f "$WT/.h2-telemetry.log" ]; then cp "$WT/.h2-telemetry.log" "$EV/telemetry.log"
else : > "$EV/telemetry.log"; fi
{
  echo "run_id=$RUN_ID"
  echo "head=$HEAD"
  echo "base=$BASE"
  echo "worker_committed=$WORKER_COMMITTED"
} > "$EV/collect-summary.txt"

# --- delivery re-check at collection ([8][18][21]; fail-closed) ---
RECHECK="$EV/carrier-recheck.txt"
RFAIL=0
{
  "$PY" - "$EV/receipt.json" "$WT" <<'PYEOF'
import hashlib, json, os, subprocess, sys
receipt = json.load(open(sys.argv[1], encoding="utf-8"))
wt = sys.argv[2]
fail = 0

def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()

def report(label, ok, detail=""):
    global fail
    print(f"{label} = {'OK' if ok else 'FAIL'}{(' ' + detail) if detail else ''}")
    if not ok:
        fail = 1

arm = receipt["arm"]
if arm == "variant":
    p = os.path.join(wt, "CODEBUDDY.md")
    if os.path.exists(p):
        report("CARRIER_RECHECK(variant carrier)",
               sha(p) == receipt["carrier_hash"], f"sha256={sha(p)}")
    else:
        report("CARRIER_RECHECK(variant carrier)", False, "carrier missing at collection")
    report("CARRIER_RECHECK(variant has no H2_AGENTS.md)",
           not os.path.exists(os.path.join(wt, "H2_AGENTS.md")))
    report("CARRIER_RECHECK(variant has no unexpected CODEBUDDY copies elsewhere)",
           not subprocess.run(["git", "-C", wt, "status", "--porcelain"], capture_output=True,
                              text=True).stdout.count("CODEBUDDY.md") > 1)
else:
    report("CARRIER_RECHECK(control: no carrier file)",
           not os.path.exists(os.path.join(wt, "CODEBUDDY.md")))
    p = os.path.join(wt, "H2_AGENTS.md")
    if os.path.exists(p):
        report("CARRIER_RECHECK(control H2_AGENTS.md)",
               sha(p) == receipt["h2_agents_sha256"], f"sha256={sha(p)}")
    else:
        report("CARRIER_RECHECK(control H2_AGENTS.md)", False, "missing at collection")

p = os.path.join(wt, "H2_RULES.md")
if os.path.exists(p):
    report("CARRIER_RECHECK(H2_RULES.md, both arms)",
           sha(p) == receipt["h2_rules_sha256"], f"sha256={sha(p)}")
else:
    report("CARRIER_RECHECK(H2_RULES.md, both arms)", False, "missing at collection")

# The run tree's OWN canonical texts must be untouched (base-relative; status shows tracked edits).
st = subprocess.run(["git", "-C", wt, "status", "--porcelain", "--", "AGENTS.md", "RULES.md"],
                    capture_output=True, text=True).stdout.strip()
report("CARRIER_RECHECK(run-tree AGENTS.md/RULES.md untouched)", st == "", st)

sys.exit(fail)
PYEOF
} > "$RECHECK" 2>&1 || RFAIL=1
cat "$RECHECK"

DIFF_SHA="$(shasum -a 256 "$EV/diff.patch" | awk '{print $1}')"
TEL_SHA="$(shasum -a 256 "$EV/telemetry.log" | awk '{print $1}')"
if [ "$RFAIL" -ne 0 ]; then
  echo "COLLECT_RUN INVALID (delivery recheck FAIL) run_id=$RUN_ID head=$HEAD base=$BASE"
  echo "  diff_sha256=$DIFF_SHA telemetry_sha256=$TEL_SHA (evidence captured)"
  echo "  -> register this run as INVALID in run-registry.md (delivery not intact at collection)"
  exit 3
fi
echo "COLLECT_RUN OK run_id=$RUN_ID head=$HEAD base=$BASE worker_committed=$WORKER_COMMITTED"
echo "  diff_sha256=$DIFF_SHA"
echo "  telemetry_sha256=$TEL_SHA"
echo "  diffstat:"
sed 's/^/    /' "$EV/diffstat.txt"
