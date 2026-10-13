#!/usr/bin/env bash
# H2 harness — collect_run.sh <RUN_ID>
# Captures the worker's diff (non-destructively, rc-checked), status, and telemetry into the
# evidence dir; re-verifies the FULL delivered surface at collection (both arms' carrier hash,
# H2_RULES.md, the H2_WARM bundle, run-tree AGENTS.md/RULES.md untouched, and non-empty
# well-formed telemetry); exits 3 on ANY failure (fail-closed: the run must be registered
# INVALID). Never uses `reset --hard`; only `git reset` (mixed) to unstage.
# ---------------------------------------------------------------------------------------------
# STRUCTURAL ENV SANITIZATION (fresh review on d2c9b99, P1-1/P2-1): the caller's environment is
# re-created from scratch (env -i) before ANY git invocation, so the whole GIT_* injection class
# — GIT_CONFIG_PARAMETERS (applied AFTER the GIT_CONFIG_COUNT pins and previously honoured),
# GIT_CONFIG, GIT_DIR/GIT_WORK_TREE/GIT_COMMON_DIR, GIT_OBJECT_DIRECTORY/alternates, namespaces —
# cannot reach the judgement commands. The branch is taken when the marker is absent OR when any
# GIT_* variable is still present (so forging the marker while injecting GIT_* re-sanitizes
# anyway). A caller that fully controls the process environment (PATH hijack, loader injection)
# remains the documented same-UID boundary; the enforcement points are operator-run collect and
# independent review.
if [ "${H2_ENV_SANITIZED:-}" != "1" ] || env | grep -q '^GIT_'; then
  exec env -i PATH="$PATH" HOME="$HOME" LANG="${LANG:-C}" LC_ALL="${LC_ALL:-C}" \
       TERM="${TERM:-dumb}" H2_ENV_SANITIZED=1 PY="${PY:-}" \
       H2_RUNS_ROOT="${H2_RUNS_ROOT:-}" \
       WORKER_MODEL="${WORKER_MODEL:-}" WORKER_EPISODE="${WORKER_EPISODE:-}" \
       AUDITOR_EPISODE="${AUDITOR_EPISODE:-}" bash "$0" "$@"
fi

set -u
# Fresh adversarial review on 9f8e4ee (P3): `git -C <path> rev-parse` resolves the repository
# through GIT_DIR/GIT_WORK_TREE from the environment; a wrapper that exported either would
# silently redirect every path resolution below. The harness controls its own environment.
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR
# global/system git config must not influence judgement or capture (fresh review on 9c5f059)
# Command-scope pins, set AFTER the caller's environment (overwriting any caller-provided
# GIT_CONFIG_* / GIT_ATTR_*): hooks cannot execute, fsmonitor is off, status never hides
# untracked entries, and the global attribute/exclude layers are neutralised. These hold
# independently of the metadata guard (fresh review on 61bfbac, P0/P1 — all three vectors
# verified empirically against the unpinned behaviour).
export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null
export GIT_CONFIG_COUNT=5
export GIT_CONFIG_KEY_0=core.hooksPath            GIT_CONFIG_VALUE_0=/dev/null
export GIT_CONFIG_KEY_1=core.fsmonitor            GIT_CONFIG_VALUE_1=false
export GIT_CONFIG_KEY_2=status.showUntrackedFiles GIT_CONFIG_VALUE_2=all
export GIT_CONFIG_KEY_3=core.attributesFile       GIT_CONFIG_VALUE_3=/dev/null
export GIT_CONFIG_KEY_4=core.excludesFile         GIT_CONFIG_VALUE_4=/dev/null
export GIT_ATTR_NOSYSTEM=1
# replacement objects (git replace) are disabled for EVERY judgement command: even a replace ref
# that the metadata guard failed to see cannot substitute the commits these commands compare
# (fresh review on d2c9b99, P0 — pack-refs hid a replace ref from the guard and made the base
# object itself resolve to attacker content).
export GIT_NO_REPLACE_OBJECTS=1
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP_DIR="$(cd "$HERE/.." && pwd)"
PY="${PY:-python3}"
H2_RUNS_ROOT="${H2_RUNS_ROOT:?set H2_RUNS_ROOT}"
RUN_ID="${1:?usage: collect_run.sh <RUN_ID>}"
WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
if [ ! -d "$WT" ]; then echo "COLLECT_FAIL reason=NO_WORKTREE $WT"; exit 2; fi
if [ ! -f "$EV/receipt.json" ]; then echo "COLLECT_FAIL reason=NO_RECEIPT $EV"; exit 2; fi
fail() { [ -n "${IDX_FILE:-}" ] && rm -f "$IDX_FILE"; echo "COLLECT_FAIL reason=$1"; exit "${2:-4}"; }

# Judgement-base integrity (fresh review on 9c5f059, P0): the capture below reads the worktree's
# OWN git view, and .git/ is inside the worker's write surface — assume-unchanged / skip-worktree
# flags, a clean filter, or an info/exclude edit make that view lie. Such a run is INVALID rather
# than judged on a doctored surface.
GM="$(bash "$HERE/check_git_metadata.sh" "$WT")"; _gmrc=$?
if [ "$_gmrc" -eq 2 ]; then
  echo "COLLECT_FAIL reason=WORKTREE_GIT_METADATA_UNREADABLE"; exit 3
fi
if [ "$_gmrc" -ne 0 ]; then
  echo "COLLECT_FAIL reason=WORKTREE_GIT_METADATA_TAMPERED [$GM]"; exit 3
fi

# --- R11-5: receipt revalidation -------------------------------------------------
# receipt.json lives in the evidence dir, which the worker CAN write (it writes report.md
# there). Trusting it would let a worker rewrite expected_base to a HEAD it committed and
# adjust the recorded carrier hashes, flipping WORKER_COMMITTED to NO and hiding the commit
# from every base-relative check below. So the load-bearing fields are re-derived from the
# FROZEN plan + task registry (which the worker cannot reach) and compared; any divergence
# invalidates the run before the receipt is used as the root of collection evidence.
# The plan file is selected the SAME way prepare selected it, and validated against the SAME
# frozen hash (F17): an unchecked override let a caller point both scripts at an edited copy
# whose single remaining row became index 0, bypassing the frozen ordering.
RECEIPT_PLAN="${H2_PLAN_FILE:-$EXP_DIR/harness/run-plan-r2.json}"
if [ ! -f "$RECEIPT_PLAN" ]; then
  echo "COLLECT_FAIL reason=PLAN_FILE_MISSING $RECEIPT_PLAN"; exit 2
fi
if [ "$RECEIPT_PLAN" != "$EXP_DIR/harness/run-plan-r2.json" ]; then
  echo "COLLECT_FAIL reason=PLAN_AUTHORITY_FAIL (not the canonical Round 2 plan) $RECEIPT_PLAN"; exit 2
fi
_want_ph="$("$PY" - "$EXP_DIR/round-2-freeze.json" <<'PYEOF'
import json, sys
print(json.load(open(sys.argv[1], encoding="utf-8"))["freeze"]["RUN_PLAN_HASH_R2"])
PYEOF
)" || { echo "COLLECT_FAIL reason=RUN_PLAN_HASH_UNREADABLE"; exit 2; }
_got_ph="$(shasum -a 256 "$RECEIPT_PLAN" | awk '{print $1}')"
if [ "$_got_ph" != "$_want_ph" ]; then
  echo "COLLECT_FAIL reason=PLAN_AUTHORITY_FAIL RUN_PLAN_HASH_R2 frozen=$_want_ph actual=$_got_ph"; exit 2
fi
# Fresh adversarial review on 9f8e4ee (P1): the hash pin above lives in the SAME working tree as
# the plan, so editing the plan AND the round-2-freeze pin in lockstep satisfies it while still
# substituting a different order. The plan must also equal the version committed at the materials
# checkout's HEAD — the same binding prepare_run.sh applies.
_live_head="$(git -C "$EXP_DIR" rev-parse HEAD 2>/dev/null)" || { echo "COLLECT_FAIL reason=PLAN_AUTHORITY_FAIL (materials HEAD unreadable)"; exit 2; }
_plan_rel="experiments/v1.2/h2-lazy-disclosure/harness/run-plan-r2.json"
if git -C "$EXP_DIR" cat-file -e "$_live_head:$_plan_rel" 2>/dev/null; then
  _frozen_ph="$(git -C "$EXP_DIR" show "$_live_head:$_plan_rel" | shasum -a 256 | awk '{print $1}')"
  if [ "$_frozen_ph" != "$_got_ph" ]; then
    echo "COLLECT_FAIL reason=PLAN_AUTHORITY_FAIL (working-tree plan differs from the frozen commit)"
    echo "  frozen_commit = $_frozen_ph"
    echo "  working_tree  = $_got_ph"
    exit 2
  fi
else
  echo "COLLECT_FAIL reason=PLAN_AUTHORITY_FAIL (run-plan-r2.json is absent from the materials HEAD commit)"; exit 2
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
# Fresh adversarial review on 9f8e4ee (P3): the index path was a FIXED name inside the
# worker-writable evidence dir, so a symlink planted at that name would redirect the index
# writes; the name is now unpredictable (mktemp) and the file is removed on every exit path.
IDX_FILE="$(mktemp "$EV/collect.index.XXXXXX")" || fail CAPTURE_INDEX_CREATE_FAILED 2
export GIT_INDEX_FILE="$IDX_FILE"
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
rm -f "$IDX_FILE"
git -C "$WT" status --porcelain > "$EV/status-after.txt" || fail CAPTURE_STATUS_FAILED
git -C "$WT" status --porcelain --ignored > "$EV/status-after-ignored.txt" || fail CAPTURE_STATUS_FAILED

if [ -f "$WT/.h2-telemetry.log" ]; then
  cp "$WT/.h2-telemetry.log" "$EV/telemetry.log" || fail TELEMETRY_COPY_FAILED
else
  : > "$EV/telemetry.log"
fi
{
  echo "run_id=$RUN_ID"
  echo "head=$HEAD"
  echo "base=$BASE"
  echo "worker_committed=$WORKER_COMMITTED"
} > "$EV/collect-summary.txt"

# --- delivery + evidence re-check at collection (fail-closed) ---
RECHECK="$EV/carrier-recheck.txt"
MATERIALS_ROOT="$(git -C "$EXP_DIR" rev-parse --show-toplevel)"
TPL_REL_ROUTES="routes-h2.json"
RFAIL=0
{
  "$PY" - "$EV/receipt.json" "$WT" "$EV" "$MATERIALS_ROOT" "$TPL_REL_ROUTES" "$RECEIPT_PLAN" <<'PYEOF'
import hashlib, importlib.util, json, os, re, subprocess, sys, types
receipt = json.load(open(sys.argv[1], encoding="utf-8"))
wt, ev = sys.argv[2], sys.argv[3]
materials_root = sys.argv[4]
# Codex finding (7ba6361): the collector must be evaluated with the HARNESS THAT WAS FROZEN for
# this run, not with whatever happens to be in the checkout now. read_surface.py and
# routes-h2.json are therefore loaded from the receipt's independently revalidated materials
# commit; if the checkout has advanced, a more permissive later read-boundary must not be able
# to make evidence pass that the frozen harness would reject.
mc = receipt["materials_commit"]
# Codex finding on 7b9251a (P1): `materials_commit` is itself worker-writable, and the
# validator is loaded FROM it. A worker could point the field at an older reachable commit
# whose read_surface.py is more permissive and make a rejected READ pass collection. The
# value is therefore not trusted: it must equal the materials checkout this collector is
# actually running against, so the frozen harness is the one the operator froze, not one the
# worker chose.
_live = subprocess.run(["git", "-C", materials_root, "rev-parse", "HEAD"],
                       capture_output=True, text=True).stdout.strip()
if _live != mc:
    print(f"TEMPLATE_BINDING = FAIL materials_commit {mc[:12]} != live materials HEAD "
          f"{_live[:12] or 'UNREADABLE'} (the receipt may not select which harness validates the run)")
    raise SystemExit(1)

def _from_commit(relpath, label):
    proc = subprocess.run(["git", "-C", materials_root, "show", f"{mc}:{relpath}"],
                          capture_output=True)
    if proc.returncode != 0:
        print(f"TEMPLATE_BINDING = FAIL cannot load {label} from the frozen materials commit")
        raise SystemExit(1)
    return proc.stdout

routes_manifest = _from_commit("experiments/v1.2/h2-lazy-disclosure/routes-h2.json",
                               "routes-h2.json")
rs_src = _from_commit("experiments/v1.2/h2-lazy-disclosure/harness/read_surface.py",
                      "read_surface.py")
rs = types.ModuleType("read_surface_from_frozen_commit")
rs.__dict__["__file__"] = f"<frozen:{mc}:read_surface.py>"
exec(compile(rs_src.decode("utf-8"), "<frozen read_surface.py>", "exec"), rs.__dict__)

routes = json.loads(routes_manifest.decode("utf-8"))["routes"]
fail = 0

def sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()

def report(label, ok, detail=""):
    global fail
    print(f"{label} = {'OK' if ok else 'FAIL'}{(' ' + detail) if detail else ''}")
    if not ok:
        fail = 1

# 0. FROZEN EXPECTED DELIVERY HASHES (trust-root repair).
# The receipt is worker-writable, so using receipt["carrier_hash"] / ["h2_rules_sha256"] /
# ["warm_bundle_sha256"] as the expected values made the delivery checks SELF-CERTIFYING: a
# worker could edit the delivered bytes, rewrite the matching receipt field, and collect would
# report OK. The expected values are therefore re-derived here from the independently bound
# materials commit; the receipt's copy is kept only as a CLAIM and is compared as well, so the
# three-way identity is frozen == claimed == actual.
H2REL = "experiments/v1.2/h2-lazy-disclosure"
_frozen_cache = {}

def _frozen_bytes(relpath):
    if relpath not in _frozen_cache:
        _frozen_cache[relpath] = _from_commit(relpath, relpath.split("/")[-1])
    return _frozen_cache[relpath]

def _frozen_bytes_or_none(relpath):
    """Total variant of _frozen_bytes for use inside the expected-carrier composition: a read
    failure yields None (the caller reports an UNREADABLE expected value) instead of aborting
    the whole recheck with SystemExit."""
    proc = subprocess.run(["git", "-C", materials_root, "show", f"{mc}:{relpath}"],
                          capture_output=True)
    return None if proc.returncode != 0 else proc.stdout

# ---- expected carrier KIND, derived from the FROZEN ARM (never from the receipt) -------------
# Codex finding on 61dcf99 (P1): the expected carrier was selected by receipt["carrier_kind"],
# which is worker-writable and is NOT covered by receipt revalidation (that checks `arm`).
# For a control run, swapping CODEBUDDY.md for the frozen VARIANT carrier and rewriting
# carrier_kind + carrier_hash made every recheck pass, so a control observation could actually
# receive the variant intervention — the independent variable would silently invert. The kind is
# therefore derived from the plan row's arm, which RECEIPT_AUTH has already validated against the
# frozen plan; the receipt value survives only as a CLAIM.
_ARM_KINDS = {"control": "control_full_v1", "variant": "variant_lean_v1"}
_plan = json.load(open(sys.argv[6], encoding="utf-8"))
_rows = [r for r in _plan if r["run_id"] == receipt.get("run_id")]
if len(_rows) == 1:
    expected_kind = _ARM_KINDS.get(_rows[0]["arm"])
    kind_source = f"frozen plan arm={_rows[0]['arm']}"
else:
    # plan-less dry-run: no frozen arm exists, so the receipt's own arm is the only mapping
    # input and the resulting check is a consistency check, not an independence check. Dry-runs
    # carry no experimental standing; every real run has a frozen plan row.
    expected_kind = _ARM_KINDS.get(receipt.get("arm"))
    kind_source = f"receipt arm claim={receipt.get('arm')} (plan-less dry-run)"

def frozen_carrier_sha():
    """Expected carrier = the FROZEN ARM's carrier, composed from the frozen materials commit —
    exactly what prepare_run.sh delivers (header + AGENTS.md@MATERIALS_COMMIT verbatim + footer
    for control; the lean bootstrap for variant).

    The expected KIND is not read from the receipt (see the derivation above): that field is
    worker-writable, and deriving from it let a control run be handed the VARIANT carrier while
    every hash check still passed because the claim was rewritten to match.
    """
    if expected_kind == "variant_lean_v1":
        blob = _frozen_bytes_or_none(f"{H2REL}/carriers/H2_LEAN_BOOTSTRAP.md")
        return None if blob is None else hashlib.sha256(blob).hexdigest()
    if expected_kind != "control_full_v1":
        return None
    header = _frozen_bytes_or_none(f"{H2REL}/harness/control-carrier-header.md")
    footer = _frozen_bytes_or_none(f"{H2REL}/harness/control-carrier-footer.md")
    # Codex finding on 61dcf99 (P1): this must read AGENTS.md at the FROZEN MATERIALS COMMIT,
    # matching prepare_run.sh. Composing from the historical task base instead made every
    # untouched control run over t01-t04 fail (those AGENTS.md revisions differ from the
    # materials-era one), consuming valid runs as INVALID.
    agents = _frozen_bytes_or_none("AGENTS.md")
    if header is None or footer is None or agents is None:
        return None
    return hashlib.sha256(header + agents + footer).hexdigest()

def frozen_rules_sha():
    return hashlib.sha256(_frozen_bytes("RULES.md")).hexdigest()

def frozen_warm_sha():
    # derived from the frozen routes manifest itself, not from the `dests` variable, because this
    # runs before that is bound
    _dests = sorted({r["destination"] for r in routes if r.get("surface") == "S3"})
    lines = []
    for dest in _dests:
        blob = _frozen_bytes(dest)
        lines.append(f"{dest} {hashlib.sha256(blob).hexdigest()}")
    return hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()

FROZEN_CARRIER = frozen_carrier_sha()
FROZEN_RULES = frozen_rules_sha()
FROZEN_WARM = frozen_warm_sha()

# 1. guidance carrier (both arms; same recognized slot, arm-specific content+hash)
p = os.path.join(wt, "CODEBUDDY.md")
if not os.path.exists(p):
    report("CARRIER_RECHECK(CODEBUDDY.md carrier)", False, "carrier missing at collection")
else:
    actual = sha(p)
    kind_ok = receipt.get("carrier_kind") == expected_kind
    ok = (kind_ok and FROZEN_CARRIER is not None
          and FROZEN_CARRIER == actual and receipt.get("carrier_hash") == actual)
    report("CARRIER_RECHECK(CODEBUDDY.md carrier)", ok,
           f"expected_kind={expected_kind} (from {kind_source}) "
           f"claimed_kind={receipt.get('carrier_kind')} "
           f"frozen={(FROZEN_CARRIER or 'UNREADABLE')[:12]} "
           f"claimed={(receipt.get('carrier_hash') or '')[:12]} actual={actual[:12]}")

# 2. rules copy (both arms)
p = os.path.join(wt, "H2_RULES.md")
if os.path.exists(p):
    actual = sha(p)
    report("CARRIER_RECHECK(H2_RULES.md)",
           FROZEN_RULES == actual and receipt.get("h2_rules_sha256") == actual,
           f"frozen={FROZEN_RULES[:12]} claimed={(receipt.get('h2_rules_sha256') or '')[:12]} "
           f"actual={actual[:12]}")
else:
    report("CARRIER_RECHECK(H2_RULES.md)", False, "missing at collection")

# 3. WARM bundle (both arms): exact recursive file set + digest over the expected destinations
routes = json.loads(routes_manifest.decode("utf-8"))["routes"]
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
claim = receipt.get("warm_bundle_sha256")
got = hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()
# frozen == claimed == actual (F16): the receipt value is a claim, never the root of trust
report("CARRIER_RECHECK(H2_WARM bundle)",
       not extra and not missing and not symlinked and FROZEN_WARM == got and claim == got,
       f"frozen={FROZEN_WARM[:12]} claimed={(claim or '')[:12]} actual={got[:12]} "
       f"files={len(found)}/{len(dests)} extra={extra} missing={missing} "
       f"symlinks={sorted(symlinked)}")

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
# materials_root is argv[4] — the frozen checkout, passed explicitly because it is NOT an
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
    # src_h is the receipt's record of the SOURCE bytes; comparing it too makes the receipt's
    # claim part of the verdict instead of an unused field (fresh adversarial review: it was
    # recorded but never read — a claim that participates in nothing is not a check).
    report("TEMPLATE_BINDING", frozen_h == src_h == run_h == got,
           f"frozen_source={frozen_h[:12]} receipt_source_claim={(src_h or '')[:12]} "
           f"receipt_copy={run_h[:12]} at_collect={got[:12]}")

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
# collect-ok marker (fresh review on 9c5f059, P1): publish must be able to verify that a COLLECT
# of this run's CURRENT evidence actually succeeded, instead of trusting files the worker can
# write. The marker lives OUTSIDE the evidence dir and binds, by hash, the two files publish
# consumes — a hand-written collect-summary/carrier-recheck cannot pass it.
mkdir -p "$H2_RUNS_ROOT/collect-ok" || fail COLLECT_MARKER_DIR_FAILED
SUM_SHA="$(shasum -a 256 "$EV/collect-summary.txt" | awk '{print $1}')"
REC_SHA="$(shasum -a 256 "$EV/carrier-recheck.txt" | awk '{print $1}')"
# the marker binds EVERY file publish consumes/verifies, so nothing in the evidence dir can be
# swapped after collection (fresh review on 61bfbac, P1-4: report/acceptance/telemetry were
# unbound and replaceable between collect and publish)
REPORT_SHA=""; [ -f "$EV/report.md" ] && REPORT_SHA="$(shasum -a 256 "$EV/report.md" | awk '{print $1}')"
ACC_SHA=""; [ -f "$EV/acceptance.txt" ] && ACC_SHA="$(shasum -a 256 "$EV/acceptance.txt" | awk '{print $1}')"
"$PY" - "$H2_RUNS_ROOT/collect-ok/$RUN_ID.json" "$RUN_ID" "$SUM_SHA" "$REC_SHA" "$DIFF_SHA" \
        "$TEL_SHA" "$REPORT_SHA" "$ACC_SHA" <<'PYEOF' \
  || fail COLLECT_MARKER_WRITE_FAILED
import json, sys
p, rid, s, r, d, t, rp, ac = sys.argv[1:9]
json.dump({"run_id": rid, "collect": "OK", "summary_sha256": s, "recheck_sha256": r,
           "diff_sha256": d, "telemetry_sha256": t, "report_sha256": rp,
           "acceptance_sha256": ac}, open(p, "w", encoding="utf-8"), indent=2,
          ensure_ascii=False)
PYEOF
echo "COLLECT_RUN OK run_id=$RUN_ID head=$HEAD base=$BASE worker_committed=$WORKER_COMMITTED"
echo "  diff_sha256=$DIFF_SHA"
echo "  telemetry_sha256=$TEL_SHA"
echo "  diffstat:"
sed 's/^/    /' "$EV/diffstat.txt"
