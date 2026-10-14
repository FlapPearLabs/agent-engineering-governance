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
  # Lexically normalize the FULL unresolved path (incl. '..' segments), then resolve the
  # deepest existing ancestor for symlinks and re-append the remainder (R10-6).
  R_MATCH="$("$PY" - "$R_TRIM" <<'PYEOF'
import os, sys
p = os.path.normpath(sys.argv[1])
anc = p
while not os.path.isdir(anc) and os.path.dirname(anc) != anc:
    anc = os.path.dirname(anc)
real = os.path.realpath(anc)
rest = os.path.relpath(p, anc)
print(p if rest == os.curdir else os.path.normpath(os.path.join(real, rest)))
PYEOF
)" || R_MATCH="$R_TRIM"
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
# N1: reject whitespace-bearing roots BEFORE any run allocation. The telemetry grammar is
# `READ <kind> <\S+>`; if the runs root (or any ancestor) contains a space, the evidence
# namespace and any absolute spelling become unrepresentable, so a contract-compliant run would
# be invalidated by the collector. Refusing up front is the fail-closed choice; no escaping DSL
# is introduced for an experiment harness.
case "$R_LC" in
  *[[:space:]]*)
    echo "PREPARE_FAIL reason=UNSUPPORTED_RUN_ROOT_WHITESPACE root='$R_TRIM'"
    echo "  (telemetry tokens are whitespace-delimited; a root containing whitespace cannot be"
    echo "   represented in a machine-readable READ event — use a whitespace-free runs root)"
    exit 2 ;;
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
  PLAN_IDX="-1"
  REG="$EXP_DIR/task-registry.json"
  WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
  EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
else
  # Round 2 uses its own frozen plan (new run identities H2-R2-R01..R20); the Round-1 plan file
  # stays frozen as part of the Round-1 record and is never repurposed.
  # F17 [P1, Codex on 09ed257]: an unchecked H2_PLAN_FILE override let a caller point at an
  # EDITED copy — a one-row copy containing H2-R2-R20 makes that run index 0, bypassing every
  # prior-run ordering check and silently destroying the frozen counterbalancing order. The
  # override is therefore no longer trusted: the selected file must be the canonical committed
  # Round 2 plan AND hash to the frozen RUN_PLAN_HASH_R2. Hash-only would still allow an
  # identical-bytes file at an arbitrary path to be substituted silently, so both are required.
  PLAN="${H2_PLAN_FILE:-$EXP_DIR/harness/run-plan-r2.json}"
  if [ ! -f "$PLAN" ]; then
    echo "PREPARE_FAIL reason=PLAN_FILE_MISSING $PLAN"; exit 2
  fi
  _canon="$EXP_DIR/harness/run-plan-r2.json"
  if [ "$PLAN" != "$_canon" ]; then
    echo "PREPARE_FAIL reason=PLAN_AUTHORITY_FAIL (the selected plan is not the canonical Round 2 plan)
  selected = $PLAN
  canonical = $_canon"
    exit 2
  fi
  _want_plan_hash="$("$PY" - "$EXP_DIR/round-2-freeze.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["freeze"]["RUN_PLAN_HASH_R2"])
PYEOF
)" || { echo "PREPARE_FAIL reason=RUN_PLAN_HASH_UNREADABLE"; exit 2; }
  _got_plan_hash="$(shasum -a 256 "$PLAN" | awk '{print $1}')"
  if [ "$_got_plan_hash" != "$_want_plan_hash" ]; then
    echo "PREPARE_FAIL reason=PLAN_AUTHORITY_FAIL (RUN_PLAN_HASH_R2 mismatch)
  frozen = $_want_plan_hash
  actual = $_got_plan_hash"
    exit 2
  fi
  # ...and the bytes must equal the version committed in the frozen materials snapshot, so a
  # later edit to the working tree cannot re-freeze a different order.
  if ! git -C "$H2_WT" cat-file -e "$MATERIALS_COMMIT:experiments/v1.2/h2-lazy-disclosure/harness/run-plan-r2.json" 2>/dev/null; then
    echo "PREPARE_FAIL reason=PLAN_AUTHORITY_FAIL (run-plan-r2.json is absent from the frozen materials commit)"; exit 2
  fi
  _frozen_plan_hash="$(git -C "$H2_WT" show "$MATERIALS_COMMIT:experiments/v1.2/h2-lazy-disclosure/harness/run-plan-r2.json" | shasum -a 256 | awk '{print $1}')"
  if [ "$_frozen_plan_hash" != "$_got_plan_hash" ]; then
    echo "PREPARE_FAIL reason=PLAN_AUTHORITY_FAIL (working-tree plan differs from the frozen materials commit)
  frozen_commit = $_frozen_plan_hash
  working_tree  = $_got_plan_hash"
    exit 2
  fi
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
# P0-2 disposition (2026-10-14, evidence [27]): a plan row may be marked NON_ELIGIBLE. Such a row
# keeps its run id and its place in the frozen order — ids are never reused or renumbered — but it
# must not be prepared, because the task it names has no honest green path and would burn a run
# id on a guaranteed INVALID record. Refusing HERE (rather than only documenting it) is what makes
# the marker mechanical: a sentinel that could still be executed would not be a sentinel.
if row.get("eligibility") == "NON_ELIGIBLE":
    print(f"__NON_ELIGIBLE__ {row.get('ineligible_reason_token', 'UNSPECIFIED')} "
          f"causal_role={row.get('causal_role', 'UNSPECIFIED')[:60]}")
    raise SystemExit(0)
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
  # R9-4/R10-2: enforce the FROZEN plan order — every prior plan row must have reached a
  # RECORDED TERMINAL state (prepared AND collected: collect-summary.txt exists). The frozen
  # counterbalancing controls execution-time carryover, so preparation/execution must not
  # outrun the plan.
  ORDER_CHECK="$("$PY" - "$PLAN" "$RUN_ID" "$H2_RUNS_ROOT" "$MATERIALS_COMMIT" <<'PYEOF'
import json, os, sys
plan = json.load(open(sys.argv[1], encoding="utf-8"))
rid, runs_root, commit = sys.argv[2], sys.argv[3], sys.argv[4]
idx = [i for i, r in enumerate(plan) if r["run_id"] == rid][0]
# A NON_ELIGIBLE row is refused at the eligibility gate BEFORE any allocation, so it can never
# produce a collect-summary.txt. Without this exemption the order check is unsatisfiable for
# every later row and the whole round deadlocks (round-13 P0-2, DEMONSTRATED: R03..R20 all failed
# with OUT_OF_ORDER missing_terminal_prior_runs=[H2-R2-R01]). A refused row is a DELIBERATE,
# RECORDED non-execution, not a missing terminal state: its ineligibility is a frozen property of
# the plan row, so it is as settled as a collected row. Ordering among ELIGIBLE rows is unchanged.
not_collected = [plan[i]["run_id"] for i in range(idx)
                 if plan[i].get("eligibility") != "NON_ELIGIBLE"
                 and not os.path.isfile(os.path.join(runs_root, "evidence", plan[i]["run_id"], "collect-summary.txt"))]
# R10-1: bind every run of THIS ROUND to ONE materials commit. The scan is scoped to the run
# ids named by the selected plan: a retained runs root also holds the previous round's
# receipts, and comparing those against this round's materials commit would refuse a correct
# preparation (Codex finding on 7ba6361).
round_ids = {r["run_id"] for r in plan}
mismatch = []
evroot = os.path.join(runs_root, "evidence")
if os.path.isdir(evroot):
    for name in sorted(os.listdir(evroot)):
        if name not in round_ids:
            continue
        rp = os.path.join(evroot, name, "receipt.json")
        if os.path.isfile(rp):
            try:
                mc = json.load(open(rp, encoding="utf-8")).get("materials_commit")
            except Exception:
                continue
            if mc and mc != commit:
                mismatch.append(f"{name}:{mc[:10]}")
print(f"{idx} {' '.join(not_collected)} MISMATCH={' '.join(mismatch) or 'none'}")
PYEOF
)" || { echo "PREPARE_FAIL reason=ORDER_CHECK_FAILED"; exit 2; }
  PLAN_IDX="${ORDER_CHECK%% *}"
  REST2="${ORDER_CHECK#* }"
  MISSING_PREV="${REST2%% *}"
  MAT_MISMATCH="${REST2#*MISMATCH=}"
  if [ -n "$MISSING_PREV" ]; then
    echo "PREPARE_FAIL reason=OUT_OF_ORDER missing_terminal_prior_runs=[$MISSING_PREV] (the frozen plan order is the control for time/carryover effects)"
    exit 2
  fi
  if [ "$MAT_MISMATCH" != "none" ]; then
    echo "PREPARE_FAIL reason=MATERIALS_ADVANCED prior_runs=[$MAT_MISMATCH] current=$MATERIALS_COMMIT (all runs must use ONE frozen materials snapshot)"
    exit 2
  fi
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
  # The run worktree is an INDEPENDENT repository (not a linked worktree), so it is removed
  # directly; `git worktree remove` does not apply to it.
  rm -rf "$WT" >/dev/null 2>&1 || true
  mv "$EV" "$EV.failed-$(date -u +%Y%m%dT%H%M%SZ)" 2>/dev/null || true
}
fatal_alloc() {
  echo "PREPARE_FAIL reason=$1 (allocation rolled back: worktree removed; failed evidence preserved beside $EV)"
  alloc_rollback
  exit 2
}

# The run worktree is created as an INDEPENDENT, depth-1 repository rather than as a linked
# worktree of the materials checkout. A linked worktree shares the object database, so a
# worker could run `git show <materials_commit>:...` and read the protocol, the task registry
# (which carries the oracle), the scoring rubric and the OTHER arm's carrier — none of which
# is a filesystem path, so no path allowlist can observe it, and the commit SHA is published
# in the worker's own receipt. A depth-1 independent repo contains only the task base, so
# every other object is absent and the oracle is unreachable.
git init -q "$WT" || fatal_alloc "WORKTREE_INIT_FAILED"
# N3: --no-write-fetch-head. Without it git records "of file://<materials checkout>" in
# .git/FETCH_HEAD, which sits inside the worker's allowed read surface; the worker could recover
# the materials checkout path from it and then read the protocol, the oracle-bearing task
# registry or the opposite-arm carrier directly, defeating the object-database isolation.
# The checkout then detaches at BASE_SHA (the object the fetch just delivered) rather than at
# FETCH_HEAD, which --no-write-fetch-head deliberately does not create.
if ! git -C "$WT" fetch -q --depth=1 --no-write-fetch-head "file://$H2_WT" "$BASE_SHA" 2>/dev/null; then
  # older git without the flag: fall back, then scrub the file so the path is not recoverable
  git -C "$WT" fetch -q --depth=1 "file://$H2_WT" "$BASE_SHA" \
    || fatal_alloc "WORKTREE_FETCH_FAILED base=$BASE_SHA (independent shallow repo)"
  rm -f "$WT/.git/FETCH_HEAD"
fi
git -C "$WT" checkout -q --detach "$BASE_SHA" || fatal_alloc "WORKTREE_CHECKOUT_FAILED base=$BASE_SHA"
# Prove the isolation rather than assuming it: the materials-era commit must be unreachable.
if git -C "$WT" cat-file -e "$MATERIALS_COMMIT^{commit}" 2>/dev/null; then
  fatal_alloc "ODB_NOT_ISOLATED (the materials commit is present in the run worktree)"
fi
# ...and the materials CHECKOUT PATH must not be recoverable from any git metadata the worker
# can read. This is a scan, not an assumption: a future git change that re-adds the URL would
# otherwise silently reopen the leak.
if grep -rIl -e "$H2_WT" -e "file://" "$WT/.git" 2>/dev/null | grep -q .; then
  # .git/config legitimately records the remote for this repo; check every OTHER file too
  if grep -rIl -e "$H2_WT" "$WT/.git" 2>/dev/null | grep -qv '\.git/config$'; then
    fatal_alloc "SOURCE_PATH_LEAK (the materials checkout path is recoverable from .git metadata)"
  fi
fi
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
  # The header and footer live in files so that h2_hot_inventory.py can measure the EXACT
  # composed bytes without duplicating the literals (R11-4: the control surface must be the
  # bytes actually delivered as CODEBUDDY.md, not bare AGENTS.md).
  "$PY" - "$HERE/control-carrier-header.md" "$HERE/control-carrier-footer.md" "$H2_WT" \
        "$MATERIALS_COMMIT" "$WT/CODEBUDDY.md" <<'PYEOF' \
    || fatal_alloc "CONTROL_CARRIER_COMPOSE_FAILED"
import pathlib, subprocess, sys
header = pathlib.Path(sys.argv[1]).read_bytes()
footer = pathlib.Path(sys.argv[2]).read_bytes()
agents = subprocess.run(["git", "-C", sys.argv[3], "show", f"{sys.argv[4]}:AGENTS.md"],
                        capture_output=True, check=True).stdout
out_path = pathlib.Path(sys.argv[5])
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

# ---- DELIVERY_ANCHORS (operator decision 2026-10-14, after round-13) ----------------------
# Two MECHANICAL anchors are measured HERE, at hand-off, on the delivered worktree with ZERO
# worker edits: PRE-delivery (the bare base checkout, carrier stashed aside) and POST-delivery
# (the carrier in place). DELIVERY_DELTA is the explicit difference. It is recorded, never
# normalized away: a harness-induced failure must NOT be laundered into "pre-existing red",
# because that hides a defect of the experiment behind the appearance of a task baseline.
#
# Only REPO-INVARIANT gates are measured — the ones that are expected to hold before AND after the
# work. The scope/hygiene gates are deliberately RED on a pristine worktree (require_any_in has no
# changed path yet), so including them would report RED->RED for every task and measure nothing.
# When a repo-invariant gate is GREEN pre-delivery and RED post-delivery, DELIVERY_CONTAMINATION
# is YES and check_test_provenance.sh refuses to use that file as a frozen oracle — because a
# frozen oracle that is already red at hand-off would refuse every worker edit, honest or not,
# and a gate with no green path has zero discriminating power.
ANCHORS="$("$PY" - "$EXP_DIR/task-registry.json" "$TASK_ID" "$WT" "$RUN_ID" "$HERE" "$PY" \
                "$(git -C "$EXP_DIR" rev-parse --show-toplevel)" <<'PYEOF'
import json, os, pathlib, shutil, subprocess, sys, tempfile
reg_p, tid, wt, rid, here, py = sys.argv[1:7]
wt = pathlib.Path(wt)
task = [t for t in json.load(open(reg_p, encoding="utf-8"))["tasks"]
        if t["task_id"] == tid][0]
entries = [e["cmd"] for e in task["acceptance"]["mechanical"]
           if e["cmd"].startswith(("{PY}", "{GIT}"))
           and "unittest" in e["cmd"]]          # repo-invariant only
res = {"entries": [], "note": "PRE/POST measured with zero worker edits at prepare time; "
                              "DELIVERY_DELTA is their difference and is never normalized away"}
carrier = ["CODEBUDDY.md", "H2_RULES.md", "H2_AGENTS.md", "H2_WARM"]
stash = pathlib.Path(tempfile.mkdtemp(prefix="h2-anchor-stash-"))
try:
    moved = []
    for f in carrier:
        src = wt / f
        if src.exists():
            shutil.move(str(src), str(stash / f)); moved.append(f)
    for label in ("pre_delivery", "post_delivery"):
        if label == "post_delivery":
            for f in moved:
                dst = wt / f
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(stash / f), str(dst))
        for cmd in entries:
            c = cmd.replace("{HARNESS}", here).replace("{WT}", str(wt)).replace("{RUN_ID}", rid)
            c = c.replace("{TASK_ID}", tid).replace("{PY}", py).replace("{GIT}", "git")
            if c.endswith("(cwd={WT})"):
                c = f"cd {str(wt)!r} && " + c[: -len("(cwd={WT})")].rstrip()
            r = subprocess.run(["bash", "-c", c], capture_output=True, text=True,
                               env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            res["entries"].append({"cmd": cmd, "anchor": label, "rc": r.returncode})
finally:
    if stash.exists():
        shutil.rmtree(stash, ignore_errors=True)
# derive the delta per entry
for e in res["entries"]:
    same = [x for x in res["entries"] if x["cmd"] == e["cmd"] and x["anchor"] != e["anchor"]]
    other = same[0] if same else {"rc": None}
    if e["anchor"] == "post_delivery":
        e["pre_delivery_rc"] = other.get("rc")
        e["delivery_delta"] = ("GREEN->RED" if other.get("rc") == 0 and e["rc"] != 0 else
                               "RED->GREEN" if other.get("rc") not in (0, None) and e["rc"] == 0 else
                               "UNCHANGED")
        e["delivery_contamination"] = "YES" if e["delivery_delta"] == "GREEN->RED" else "NO"
res["contamination"] = "YES" if any(
    x.get("anchor") == "post_delivery" and x.get("delivery_contamination") == "YES"
    for x in res["entries"]) else "NO"
print(json.dumps(res))
PYEOF
)" || fatal_alloc "ANCHOR_MEASUREMENT_FAILED"
printf '%s' "$ANCHORS" > "$EV/delivery-anchors.json" \
  || fatal_alloc "ANCHOR_WRITE_FAILED"
echo "PREPARE delivery_anchors: $(printf '%s' "$ANCHORS" | "$PY" -c 'import json,sys; d=json.load(sys.stdin); print("contamination=" + d["contamination"], "entries=" + str(len(d["entries"])))')"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
"$PY" - "$EV/receipt.json" "$RUN_ID" "$TASK_ID" "$ARM" "$WT" "$BASE_SHA" "$ACTUAL" \
        "$CARRIER_KIND" "$CARRIER_HASH" "$RULES_HASH" "$WARM_HASH" \
        "$MATERIALS_COMMIT" "$MODEL_TIER" "$RUFF_WT_HASH" "$PLAN_IDX" "$TS" <<'PYEOF' \
  || fatal_alloc "RECEIPT_WRITE_FAILED"
import json, sys
(p, rid, tid, arm, wt, base, head, ckind, ch, rh, wh, mc, mt, rth, pidx, ts) = sys.argv[1:17]
json.dump({
    "run_id": rid, "task_id": tid, "arm": arm, "worktree": wt,
    "expected_base": base, "actual_head": head,
    "carrier_kind": ckind, "carrier_hash": ch,
    "h2_rules_sha256": rh, "warm_bundle_sha256": wh,
    "materials_commit": mc, "model_tier": mt,
    "ruff_toml_worktree_sha256": rth,
    "plan_index": pidx,
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
import hashlib, json, pathlib, subprocess, sys
here, ev, wt, base, arm, model_tier = sys.argv[1:7]
evp = pathlib.Path(ev)

# ---- read-boundary repair (PART 6) ----------------------------------------------
# The worker is allowed to read its own worktree and its OWN evidence dir, and nothing else.
# The report template used to live in the materials tree, so a contract-compliant read of it
# was rejected by TELEMETRY_TARGETS: the harness invalidated its own compliant worker.
# Fix = place an exact-byte copy in the run's evidence dir and point the contract there.
# The source is read from the MATERIALS COMMIT object (never the working tree), and the copy
# is admitted only when the hashes are equal.
src = subprocess.run(
    ["git", "-C", here, "show", f"{json.load(open(evp / 'receipt.json', encoding='utf-8'))['materials_commit']}:"
     "experiments/v1.2/h2-lazy-disclosure/harness/worker-report-template.md"],
    capture_output=True, check=True).stdout
run_tpl = evp / "worker-report-template.md"
run_tpl.write_bytes(src)
src_hash = hashlib.sha256(src).hexdigest()
run_hash = hashlib.sha256(run_tpl.read_bytes()).hexdigest()
if src_hash != run_hash:
    sys.exit(f"TEMPLATE_HASH_MISMATCH source={src_hash} copy={run_hash}")
if run_tpl.is_symlink() or not run_tpl.is_file():
    sys.exit("TEMPLATE_COPY_NOT_A_PLAIN_FILE")

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
       .replace("<REPORT_TEMPLATE_PATH>", f"{ev}/worker-report-template.md")
       .replace("<BOOTSTRAP_DELIVERY_BLOCK>", block))
open(f"{ev}/contract.md", "w", encoding="utf-8").write(out)

# record both hashes on the receipt so the binding is auditable, not just asserted once
rp = evp / "receipt.json"
data = json.loads(rp.read_text(encoding="utf-8"))
data["report_template_source_sha256"] = src_hash
data["report_template_run_sha256"] = run_hash
data["report_template_run_path"] = str(run_tpl)
rp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"template bound: source={src_hash[:12]} copy={run_hash[:12]} -> {run_tpl.name}")
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
