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

# --- R11-5: receipt revalidation -------------------------------------------------
# receipt.json lives in the evidence dir, which the worker CAN write (it writes report.md
# there). Trusting it would let a worker rewrite expected_base to a HEAD it committed and
# adjust the recorded carrier hashes, flipping WORKER_COMMITTED to NO and hiding the commit
# from every base-relative check below. So the load-bearing fields are re-derived from the
# FROZEN plan + task registry (which the worker cannot reach) and compared; any divergence
# invalidates the run before the receipt is used as the root of collection evidence.
# The plan file is selected the SAME way prepare selected it. If the two disagree, a Round-2
# run prepared against run-plan-r2.json would be validated against the Round-1 plan and every
# run would fail revalidation -- a harness defect of exactly the kind this repair exists to
# remove (adversarial review B1).
RECEIPT_PLAN="${H2_PLAN_FILE:-$EXP_DIR/harness/run-plan.json}"
if [ ! -f "$RECEIPT_PLAN" ]; then
  echo "COLLECT_FAIL reason=PLAN_FILE_MISSING $RECEIPT_PLAN"; exit 2
fi
RECEIPT_AUTH="$("$PY" - "$EV/receipt.json" "$RECEIPT_PLAN" "$EXP_DIR/task-registry.json" "$RUN_ID" <<'PYEOF'
import json, sys
receipt = json.load(open(sys.argv[1], encoding="utf-8"))
plan_path, reg_path, rid = sys.argv[2], sys.argv[3], sys.argv[4]
plan = json.load(open(plan_path, encoding="utf-8"))
reg = {t["task_id"]: t for t in json.load(open(reg_path, encoding="utf-8"))["tasks"]}
problems = []
if receipt.get("run_id") != rid:
    problems.append(f"run_id {receipt.get('run_id')!r} != {rid!r}")
rows = [r for r in plan if r["run_id"] == rid]
if len(rows) == 1:
    row = rows[0]
    idx = plan.index(row)
    for field, want in (("task_id", row["task_id"]), ("arm", row["arm"]),
                        ("expected_base", reg[row["task_id"]]["base_sha"])):
        if receipt.get(field) != want:
            problems.append(f"{field} {receipt.get(field)!r} != frozen {want!r}")
    if str(receipt.get("plan_index", "")) != str(idx):
        problems.append(f"plan_index {receipt.get('plan_index')!r} != frozen position {idx}")
elif len(rows) > 1:
    problems.append(f"frozen plan contains {len(rows)} rows for {rid}")
else:
    # No plan row (the registered dry-run ids): there is no arm/order to check, but the
    # base and task are still re-derivable from the FROZEN registry, so the receipt is not
    # left unvalidated — a plan-less receipt must still name a real task at its frozen base.
    tid = receipt.get("task_id")
    if tid not in reg:
        problems.append(f"task_id {tid!r} is not in the frozen task registry")
    elif receipt.get("expected_base") != reg[tid]["base_sha"]:
        problems.append(
            f"expected_base {receipt.get('expected_base')!r} != frozen {reg[tid]['base_sha']!r}")
    if str(receipt.get("plan_index", "")) != "-1":
        problems.append(f"plan_index {receipt.get('plan_index')!r} must be -1 without a plan row")
print("; ".join(problems))
PYEOF
)" || RECEIPT_AUTH="RECEIPT_REVALIDATION_FAILED"
if [ -n "$RECEIPT_AUTH" ]; then
  echo "COLLECT_FAIL reason=RECEIPT_REVALIDATION $RECEIPT_AUTH"
  echo "  -> the worker-accessible receipt.json diverges from the frozen plan/registry; register this run as INVALID"
  exit 3
fi

BASE="$("$PY" - "$EV/receipt.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["expected_base"])
PYEOF
)" || fail RECEIPT_READ_FAILED 2
HEAD="$(git -C "$WT" rev-parse HEAD)" || fail HEAD_UNREADABLE 2
WORKER_COMMITTED=NO
if [ "$HEAD" != "$BASE" ]; then WORKER_COMMITTED=YES; fi

# --- capture (rc-checked; committed changes captured vs base; placed artifacts excluded;
#     TEMP index so the worker's real index is never mutated — R9-13) ---
export GIT_INDEX_FILE="$EV/collect.index"
git -C "$WT" read-tree HEAD || { unset GIT_INDEX_FILE; fail CAPTURE_INDEX_INIT_FAILED; }
git -C "$WT" add -A || { unset GIT_INDEX_FILE; fail CAPTURE_ADD_FAILED; }
git -C "$WT" reset -q -- CODEBUDDY.md .h2-telemetry.log H2_RULES.md H2_WARM 2>/dev/null || true
(
  if [ "$HEAD" != "$BASE" ]; then
    git -C "$WT" diff --binary "$BASE" "$HEAD" -- . ':!CODEBUDDY.md' ':!H2_RULES.md' ':!H2_WARM' || exit 4
  fi
  git -C "$WT" diff --cached --binary || exit 4
) > "$EV/diff.patch" || { unset GIT_INDEX_FILE; fail CAPTURE_DIFF_FAILED; }
git -C "$WT" diff --cached --stat > "$EV/diffstat.txt" 2>/dev/null || : > "$EV/diffstat.txt"
unset GIT_INDEX_FILE
git -C "$WT" status --porcelain > "$EV/status-after.txt" || fail CAPTURE_STATUS_FAILED
git -C "$WT" status --porcelain --ignored > "$EV/status-after-ignored.txt" || fail CAPTURE_STATUS_FAILED

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
  "$PY" - "$EV/receipt.json" "$WT" "$EV" "$EXP_DIR/routes-h2.json" "$EXP_DIR/harness/read_surface.py" \
          "$(git -C "$EXP_DIR" rev-parse --show-toplevel)" <<'PYEOF'
import hashlib, importlib.util, json, os, re, subprocess, sys
receipt = json.load(open(sys.argv[1], encoding="utf-8"))
wt, ev = sys.argv[2], sys.argv[3]
routes_manifest = sys.argv[4]
# single source of truth for the read surface (shared with the regression suite)
_spec = importlib.util.spec_from_file_location("read_surface", sys.argv[5])
rs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rs)
# the frozen materials tree root is passed explicitly: it is NOT an ancestor of the run
# worktree (separate checkouts), so it can never be inferred from the worktree path.
materials_root = sys.argv[6]
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
bundle_root = os.path.join(wt, "H2_WARM")
found = set()
expected_dirs = set()
for dest in dests:
    parts = dest.split("/")
    for k in range(1, len(parts)):
        expected_dirs.add("/".join(parts[:k]))
allowed = set(dests) | expected_dirs
# Recursive scan that also surfaces unexpected intermediate dirs and SYMLINKED dirs (R9-9).
# R11-2: a symlink is an integrity failure wherever it appears — INCLUDING at an expected
# destination name. Recording the expected relative path would keep extra/missing empty while
# isfile()/open() follow the link, so a same-byte external file would pass the digest check.
# Symlinks are therefore collected separately and always fail the bundle.
stack = [bundle_root]
symlinked = set()
while stack:
    d = stack.pop()
    for entry in os.scandir(d):
        rel = os.path.relpath(entry.path, bundle_root)
        if entry.is_symlink():
            symlinked.add(rel)
            found.add(rel)
        elif entry.is_dir(follow_symlinks=False):
            if rel in expected_dirs:
                stack.append(entry.path)
            else:
                found.add(rel + "/")
        else:
            found.add(rel)
extra = sorted(found - allowed)
missing = sorted(set(dests) - found)
lines = []
for dest in dests:
    fp = os.path.join(wt, "H2_WARM", dest)
    if os.path.islink(fp):
        lines.append(f"{dest} SYMLINK")
    elif not os.path.isfile(fp):
        lines.append(f"{dest} MISSING")
    else:
        lines.append(f"{dest} {sha(fp)}")
want = receipt["warm_bundle_sha256"]
got = hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()
report("CARRIER_RECHECK(H2_WARM bundle)",
       not extra and not missing and not symlinked and got == want,
       f"recomputed={got} expected={want} files={len(found)}/{len(dests)} "
       f"extra={extra} missing={missing} symlinks={sorted(symlinked)}")

# 4. run tree's own canonical texts untouched (worktree status AND base-relative, incl. commits — R8-2)
st = subprocess.run(["git", "-C", wt, "status", "--porcelain", "--", "AGENTS.md", "RULES.md"],
                    capture_output=True, text=True).stdout.strip()
d = subprocess.run(["git", "-C", wt, "diff", "--name-status", "--no-renames",
                    receipt["expected_base"], "--", "AGENTS.md", "RULES.md"],
                   capture_output=True, text=True).stdout.strip()
report("CARRIER_RECHECK(run-tree AGENTS.md/RULES.md untouched)", st == "" and d == "",
       "; ".join(x for x in (st, d) if x))

# 5. telemetry present, non-empty, FULL-GRAMMAR valid, and targets verified (R9-2/R9-10)
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
    s3ids = {r["route_id"] for r in routes if r.get("surface") == "S3"}
    s3dests = set(dests)
    problems = []
    for ln in nonempty:
        m = re.match(r"^ROUTE\s+(\S+)\s+(\S+)\s+(LOADED|MISSING|SKIPPED)$", ln)
        if m:
            rid, tgt, res = m.groups()
            if res == "LOADED" and tgt not in s3dests:
                problems.append(f"ROUTE LOADED for undeclared target: {tgt}")
            if rid != "n/a" and rid not in s3ids:
                problems.append(f"ROUTE unknown route id: {rid}")
    # READ targets are classified by the shared read-surface module: the task worktree and
    # THIS run's evidence dir are allowed; the materials root, the other arm's carrier, a
    # sibling run's evidence and any non-canonicalizable path are refused with a reason.
    problems.extend(rs.classify_telemetry(nonempty, wt, ev, materials_root))
    report("TELEMETRY_TARGETS", not problems, "; ".join(problems[:5]))

# 6. per-run report-template binding still holds at collection (PART 6 / adversarial B3).
#    The receipt is worker-writable, so trusting its recorded source hash would let the check
#    satisfy ITSELF (edit the template, edit both receipt fields, collect reports OK). The
#    source is therefore re-read from the frozen materials COMMIT here and compared three-way:
#    frozen source bytes == what prepare recorded == what is on disk at collection.
TPL_REL="experiments/v1.2/h2-lazy-disclosure/harness/worker-report-template.md"
tpl = os.path.join(ev, "worker-report-template.md")
src_h = receipt.get("report_template_source_sha256")
run_h = receipt.get("report_template_run_sha256")
# materials_root is argv[6] — the frozen checkout, passed explicitly because it is NOT an
# ancestor of the run worktree and cannot be derived from any path inside the runs root.
frozen = subprocess.run(["git", "-C", materials_root, "show", f"{receipt['materials_commit']}:{TPL_REL}"],
                        capture_output=True)
if frozen.returncode != 0:
    report("TEMPLATE_BINDING", False, "cannot re-read the template from the frozen materials commit")
elif os.path.islink(tpl) or not os.path.isfile(tpl):
    report("TEMPLATE_BINDING", False, "per-run template missing or is a symlink")
else:
    frozen_h = hashlib.sha256(frozen.stdout).hexdigest()
    got = sha(tpl)
    report("TEMPLATE_BINDING", frozen_h == run_h == got,
           f"frozen_source={frozen_h[:12]} receipt_copy={run_h[:12]} at_collect={got[:12]}")

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
