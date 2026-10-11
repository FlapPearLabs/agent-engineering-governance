#!/usr/bin/env bash
# H2 harness — collect_run.sh <RUN_ID>
# Captures the worker's diff (non-destructively, rc-checked), status, and telemetry into the
# evidence dir; re-verifies the FULL delivered surface at collection (both arms' carrier hash,
# H2_RULES.md, the H2_WARM bundle, run-tree AGENTS.md/RULES.md untouched, and non-empty
# well-formed telemetry); exits 3 on ANY failure (fail-closed: the run must be registered
# INVALID). Never uses `reset --hard`; only `git reset` (mixed) to unstage.
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

# --- capture (rc-checked; committed changes captured vs base; placed artifacts excluded) ---
git -C "$WT" add -A || fail CAPTURE_ADD_FAILED
git -C "$WT" reset -q -- CODEBUDDY.md .h2-telemetry.log H2_RULES.md H2_WARM .h2_scan_tools 2>/dev/null || true
if [ "$HEAD" != "$BASE" ]; then
  git -C "$WT" diff --binary "$BASE" -- . ':(exclude)CODEBUDDY.md' ':(exclude)H2_RULES.md' \
    ':(exclude)H2_WARM' > "$EV/diff.patch" || fail CAPTURE_DIFF_FAILED
else
  git -C "$WT" diff --cached --binary > "$EV/diff.patch" || fail CAPTURE_DIFF_FAILED
fi
git -C "$WT" diff --cached --stat > "$EV/diffstat.txt" 2>/dev/null || : > "$EV/diffstat.txt"
git -C "$WT" status --porcelain > "$EV/status-after.txt" || fail CAPTURE_STATUS_FAILED
git -C "$WT" status --porcelain --ignored > "$EV/status-after-ignored.txt" || fail CAPTURE_STATUS_FAILED
git -C "$WT" reset -q || fail CAPTURE_RESET_FAILED

if [ -f "$WT/.h2-telemetry.log" ]; then cp "$WT/.h2-telemetry.log" "$EV/telemetry.log"
else : > "$EV/telemetry.log"; fi
{
  echo "run_id=$RUN_ID"
  echo "head=$HEAD"
  echo "base=$BASE"
  echo "worker_committed=$WORKER_COMMITTED"
} > "$EV/collect-summary.txt"

# --- delivery + evidence re-check at collection (fail-closed) ---
RECHECK="$EV/carrier-recheck.txt"
RFAIL=0
{
  "$PY" - "$EV/receipt.json" "$WT" "$EV" "$EXP_DIR/routes-h2.json" <<'PYEOF'
import hashlib, json, os, re, subprocess, sys
receipt = json.load(open(sys.argv[1], encoding="utf-8"))
wt, ev = sys.argv[2], sys.argv[3]
routes_manifest = sys.argv[4]
fail = 0

def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()

def report(label, ok, detail=""):
    global fail
    print(f"{label} = {'OK' if ok else 'FAIL'}{(' ' + detail) if detail else ''}")
    if not ok:
        fail = 1

# 1. guidance carrier (both arms; same recognized slot, arm-specific content+hash)
p = os.path.join(wt, "CODEBUDDY.md")
if os.path.exists(p):
    report("CARRIER_RECHECK(CODEBUDDY.md carrier)",
           sha(p) == receipt["carrier_hash"],
           f"kind={receipt.get('carrier_kind')} sha256={sha(p)}")
else:
    report("CARRIER_RECHECK(CODEBUDDY.md carrier)", False, "carrier missing at collection")

# 2. rules copy (both arms)
p = os.path.join(wt, "H2_RULES.md")
if os.path.exists(p):
    report("CARRIER_RECHECK(H2_RULES.md)", sha(p) == receipt["h2_rules_sha256"], f"sha256={sha(p)}")
else:
    report("CARRIER_RECHECK(H2_RULES.md)", False, "missing at collection")

# 3. WARM bundle (both arms): exact recursive file set + digest over the expected destinations
routes = json.load(open(routes_manifest, encoding="utf-8"))["routes"]
dests = sorted({r["destination"] for r in routes if r.get("surface") == "S3"})
expected = set(dests)
found = set()
bundle_root = os.path.join(wt, "H2_WARM")
for root_dir, _dirs, files in os.walk(bundle_root):
    for fname in files:
        found.add(os.path.relpath(os.path.join(root_dir, fname), bundle_root))
extra = sorted(found - expected)
missing = sorted(expected - found)
lines = []
for dest in dests:
    fp = os.path.join(wt, "H2_WARM", dest)
    if not os.path.isfile(fp):
        lines.append(f"{dest} MISSING")
    else:
        lines.append(f"{dest} {sha(fp)}")
want = receipt["warm_bundle_sha256"]
got = hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()
report("CARRIER_RECHECK(H2_WARM bundle)",
       not extra and not missing and got == want,
       f"recomputed={got} expected={want} files={len(found)}/{len(dests)} extra={extra} missing={missing}")

# 4. run tree's own canonical texts untouched (worktree status AND base-relative, incl. commits — R8-2)
st = subprocess.run(["git", "-C", wt, "status", "--porcelain", "--", "AGENTS.md", "RULES.md"],
                    capture_output=True, text=True).stdout.strip()
d = subprocess.run(["git", "-C", wt, "diff", "--name-status", "--no-renames",
                    receipt["expected_base"], "--", "AGENTS.md", "RULES.md"],
                   capture_output=True, text=True).stdout.strip()
report("CARRIER_RECHECK(run-tree AGENTS.md/RULES.md untouched)", st == "" and d == "",
       "; ".join(x for x in (st, d) if x))

# 5. telemetry present, non-empty, FULL-GRAMMAR valid (no synthesized or truncated evidence)
tel = os.path.join(wt, ".h2-telemetry.log")
if not os.path.isfile(tel):
    report("TELEMETRY_RECHECK", False, "missing .h2-telemetry.log (must not be synthesized)")
else:
    body = open(tel, encoding="utf-8", errors="replace").read()
    grammar = re.compile(
        r"^(READ\s+(FULL|PARTIAL|GREP)\s+\S+"
        r"|ROUTE\s+\S+\s+\S+\s+(LOADED|MISSING|SKIPPED)"
        r"|SKILL\s+\S+\s+(LOADED|UNAVAILABLE|NOT_REQUIRED|WRONG|NONE))$"
    )
    nonempty = [ln.strip() for ln in body.splitlines() if ln.strip()]
    bad = [ln for ln in nonempty if not grammar.match(ln)]
    reads = [ln for ln in nonempty if ln.startswith("READ") and grammar.match(ln)]
    report("TELEMETRY_RECHECK",
           bool(reads) and not bad,
           f"lines={len(nonempty)} valid_reads={len(reads)} malformed={len(bad)}")

sys.exit(fail)
PYEOF
} > "$RECHECK" 2>&1 || RFAIL=1
cat "$RECHECK"

DIFF_SHA="$(shasum -a 256 "$EV/diff.patch" | awk '{print $1}')"
TEL_SHA="$(shasum -a 256 "$EV/telemetry.log" | awk '{print $1}')"
if [ "$RFAIL" -ne 0 ]; then
  echo "COLLECT_RUN INVALID (delivery/evidence recheck FAIL) run_id=$RUN_ID head=$HEAD base=$BASE"
  echo "  diff_sha256=$DIFF_SHA telemetry_sha256=$TEL_SHA (evidence captured)"
  echo "  -> register this run as INVALID in run-registry.md (delivery/evidence not intact at collection)"
  exit 3
fi
echo "COLLECT_RUN OK run_id=$RUN_ID head=$HEAD base=$BASE worker_committed=$WORKER_COMMITTED"
echo "  diff_sha256=$DIFF_SHA"
echo "  telemetry_sha256=$TEL_SHA"
echo "  diffstat:"
sed 's/^/    /' "$EV/diffstat.txt"
