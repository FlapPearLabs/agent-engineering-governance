#!/usr/bin/env bash
# H2 harness — publish_run.sh <RUN_ID>
# Copies a run's durable evidence into the repo-tracked runs/<RUN_ID>/ record (R2-sanitized):
#   report.md, acceptance.txt, carrier-recheck.txt, telemetry.log -> telemetry.json, run.json
# Safe to re-run (idempotent overwrite); refuses to publish when the evidence dir is absent.
set -u
# Fresh adversarial review on 9f8e4ee (P3): `git -C <path>` resolves through GIT_DIR/GIT_WORK_TREE
# from the environment; clear them so path resolution cannot be redirected by a wrapper.
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR
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
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP_DIR="$(cd "$HERE/.." && pwd)"
PY="${PY:-python3}"
H2_RUNS_ROOT="${H2_RUNS_ROOT:?set H2_RUNS_ROOT}"
RUN_ID="${1:?usage: publish_run.sh <RUN_ID>}"
EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
DEST="$EXP_DIR/runs/$RUN_ID"
[ -d "$EV" ] || { echo "PUBLISH_FAIL reason=NO_EVIDENCE $EV"; exit 2; }

# R9-11: a missing report is an INVALID run — never manufacture a placeholder.
if [ ! -f "$EV/report.md" ]; then
  echo "PUBLISH_REFUSED reason=MISSING_REPORT $EV/report.md (protocol: missing report => run INVALID; do not manufacture a placeholder)"
  exit 2
fi

# R9-8: once a run is finalized, its artifact set must not be silently replaced.
if [ -f "$DEST/run.json" ]; then
  FINALIZED="$("$PY" -c "import json,sys;d=json.load(open(sys.argv[1]));print(d.get('status') or '')" "$DEST/run.json" 2>/dev/null || echo '')"
  if [ -n "$FINALIZED" ] && [ "$FINALIZED" != "PENDING_REVIEW" ]; then
    for f in report.md acceptance.txt carrier-recheck.txt telemetry.log; do
      if [ -f "$EV/$f" ] && [ -f "$DEST/$f" ]; then
        a="$(shasum -a 256 "$EV/$f" | awk '{print $1}')"
        b="$(shasum -a 256 "$DEST/$f" | awk '{print $1}')"
        if [ "$a" != "$b" ]; then
          echo "PUBLISH_REFUSED reason=REVIEWED_ARTIFACT_REPLACEMENT file=$f (run is finalized; explicitly accept or invalidate first)"
          exit 3
        fi
      fi
    done
  fi
fi
# F18 [P1, Codex on 09ed257]: validate every sanitizer input BEFORE creating or modifying DEST.
# Previously the sanitizer sources were checked last, so a refusal exited nonzero only after the
# destination had already been written with unsanitized host paths.
CUR_USER_PRE="$(id -un)"
MATERIALS_WT_PRE="$(git -C "$EXP_DIR" rev-parse --show-toplevel 2>/dev/null || true)"
_preflight_fail() {
  echo "PUBLISH_REFUSED reason=$1 ($2)"
  echo "  DEST_MODIFIED = NO (refused before touching $DEST)"
  exit 2
}
[ -n "$CUR_USER_PRE" ] || _preflight_fail PREFLIGHT_FAILED "empty current user"
[ -n "$MATERIALS_WT_PRE" ] || _preflight_fail EMPTY_SANITIZER_SOURCE "materials worktree (not a git checkout)"
[ -n "$H2_RUNS_ROOT" ] || _preflight_fail EMPTY_SANITIZER_SOURCE "runs root"
[ -n "$WT" ] || _preflight_fail EMPTY_SANITIZER_SOURCE "run worktree"
[ -n "$EV" ] || _preflight_fail EMPTY_SANITIZER_SOURCE "run evidence"
# fresh adversarial review on 9f8e4ee (P1): the model/episode gates were keyed on the
# RECEIPT's plan_index — a worker-writable field. Deleting that field (or setting it to -1)
# skipped the model-evidence, episode-presence and episode-uniqueness gates entirely, so a run
# could be published under the Round-1 invalid episode, which the protocol forbids reusing.
# Real-run status is now derived from FROZEN PLAN membership, and the receipt's plan_index must
# AGREE with the frozen position instead of deciding whether the gates run.
REAL_ROW="$("$PY" - "$EXP_DIR" "$RUN_ID" <<'PYEOF'
import json, os, sys
exp, rid = sys.argv[1], sys.argv[2]
for name in ("run-plan-r2.json", "run-plan.json"):
    p = os.path.join(exp, "harness", name)
    if not os.path.isfile(p):
        continue
    try:
        plan = json.load(open(p, encoding="utf-8"))
    except Exception:
        print("__UNREADABLE__"); raise SystemExit(0)
    rows = [r for r in plan if r.get("run_id") == rid]
    # fresh review on 9c5f059 (P2): folding "0 rows" and ">1 rows" into one answer made a
    # DUPLICATED plan row silently disable every gate (the "worst input = pass" shape). A
    # duplicate is fail-closed here, matching frozen_run_facts.py and collect_run.sh.
    if len(rows) > 1:
        print("__DUPLICATE__"); raise SystemExit(0)
    if len(rows) == 1:
        print(f"{plan.index(rows[0])}\t{name}"); raise SystemExit(0)
# only the REGISTERED dry-run ids are exempt from the identity gates; any other unknown id is
# refused rather than allowed to skip them
if not rid.startswith("H2-DRYRUN"):
    print("__UNKNOWN__"); raise SystemExit(0)
print("__DRY_RUN__")
PYEOF
)" || { echo "PUBLISH_REFUSED reason=PLAN_LOOKUP_FAILED"; exit 2; }
case "$REAL_ROW" in
  __UNREADABLE__) echo "PUBLISH_REFUSED reason=PLAN_UNREADABLE"; exit 2 ;;
  __DUPLICATE__) echo "PUBLISH_REFUSED reason=PLAN_DUPLICATE_ROWS (the run id appears more than once; refusing rather than skipping the gates)"; exit 2 ;;
  __UNKNOWN__) echo "PUBLISH_REFUSED reason=UNKNOWN_RUN_ID (not a plan row and not a registered dry-run id)"; exit 2 ;;
esac

# publish is DOWNSTREAM of collection. Fresh review on 9c5f059 (P1): presence checks over
# worker-writable evidence files let a hand-written collect-summary/carrier-recheck pass as a
# "successful collect". Verification now uses the collect-ok MARKER — written only by a
# successful collect, and living OUTSIDE the evidence dir — and BINDS the two files by hash, so
# editing either one after collection is refused.
MARKER="$H2_RUNS_ROOT/collect-ok/$RUN_ID.json"
if [ ! -f "$MARKER" ]; then
  echo "PUBLISH_REFUSED reason=NO_COLLECT_EVIDENCE (no collect-ok marker for this run; run collect_run.sh first)"
  exit 2
fi
EVID="$("$PY" - "$MARKER" "$RUN_ID" "$EV" <<'PYEOF'
import hashlib, json, os, sys
marker_p, rid, ev = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    m = json.load(open(marker_p, encoding="utf-8"))
except Exception:
    print("MARKER_UNREADABLE"); raise SystemExit(0)
if m.get("run_id") != rid or m.get("collect") != "OK":
    print("MARKER_MISMATCH"); raise SystemExit(0)
# fresh review on 61bfbac (P1-4): the marker previously bound only 2 of the 6 evidence files
# publish consumes, so report/acceptance/telemetry could be swapped between collect and publish.
# Every file the record is built from is now verified against the marker: a file that was
# collected must be unchanged; a file that APPEARED after collection is refused as UNBOUND.
checks = [("collect-summary.txt", "summary_sha256"), ("carrier-recheck.txt", "recheck_sha256"),
          ("telemetry.log", "telemetry_sha256"), ("report.md", "report_sha256"),
          ("acceptance.txt", "acceptance_sha256")]
for name, key in checks:
    p = os.path.join(ev, name)
    bound = m.get(key) or ""
    if not os.path.isfile(p):
        if bound:
            print(f"MISSING:{name}"); raise SystemExit(0)
        continue
    if not bound:
        print(f"UNBOUND:{name}"); raise SystemExit(0)
    if hashlib.sha256(open(p, "rb").read()).hexdigest() != bound:
        print(f"MISMATCH:{name}"); raise SystemExit(0)
print("OK")
PYEOF
)" || EVID="VERIFIER_FAILED"
case "$EVID" in
  OK) : ;;
  MISSING:*) echo "PUBLISH_REFUSED reason=NO_COLLECT_EVIDENCE ($EVID; run collect_run.sh first)"; exit 2 ;;
  *) echo "PUBLISH_REFUSED reason=COLLECT_EVIDENCE_MISMATCH ($EVID; the evidence does not match what collect recorded)"; exit 3 ;;
esac
# worst-input-must-not-pass (fresh review on 61bfbac, P1-4): an acceptance file with NO RC marker
# parsed to `fails = []` and was recorded as an all-green acceptance.
if ! grep -qE '^=== RC=-?[0-9]+' "$EV/acceptance.txt"; then
  echo "PUBLISH_REFUSED reason=ACCEPTANCE_MARKERS_MISSING (acceptance.txt contains no '=== RC=' marker; refusing to record it as a passing acceptance)"
  exit 3
fi

if [ "$REAL_ROW" != "__DRY_RUN__" ]; then
  # R10-8 + R10-3: real runs require launcher-provided model evidence matching the frozen tier,
  # and non-null, globally unique episode identities per role.
  EXPECT_IDX="$(printf '%s' "$REAL_ROW" | cut -f1)"
  PLAN_IDX="$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1])).get('plan_index',''))" "$EV/receipt.json" 2>/dev/null || echo '')"
  if [ "$PLAN_IDX" != "$EXPECT_IDX" ]; then
    echo "PUBLISH_REFUSED reason=PLAN_INDEX_MISMATCH receipt=${PLAN_IDX:-<missing>} frozen=$EXPECT_IDX (the receipt may not decide whether the gates run)"
    exit 3
  fi
  TIER="$("$PY" -c "import json,sys;print(json.load(open(sys.argv[1])).get('model_tier',''))" "$EV/receipt.json" 2>/dev/null || echo '')"
  if [ -z "${WORKER_MODEL:-}" ]; then
    echo "PUBLISH_REFUSED reason=MISSING_MODEL_EVIDENCE (set WORKER_MODEL to the observed dispatch tier)"; exit 2
  fi
  if [ "$WORKER_MODEL" != "$TIER" ]; then
    echo "PUBLISH_REFUSED reason=MODEL_MISMATCH observed=$WORKER_MODEL tier=$TIER"; exit 2
  fi
  if [ -z "${WORKER_EPISODE:-}" ]; then
    echo "PUBLISH_REFUSED reason=MISSING_WORKER_EPISODE"; exit 2
  fi
  if [ -z "${AUDITOR_EPISODE:-}" ]; then
    echo "PUBLISH_REFUSED reason=MISSING_AUDITOR_EPISODE (independent review requires an auditor identity distinct from the worker)"; exit 2
  fi
  # R11-3: uniqueness is GLOBAL across roles, not per-role. Compare each supplied identity
  # against BOTH roles stored by prior runs AND against the other identity of this run, so an
  # auditor cannot reuse a worker episode (or vice versa) from this or any earlier run.
  # PART 8: an INVALID run is NOT a nonexistent run. The Round-1 attempt executed a real
  # episode but produced no run.json, so scanning only published run.json files would let
  # Round 2 silently reuse that executor context. Preserved invalid-run records are scanned too.
  DUP="$("$PY" - "$EXP_DIR/runs" "$RUN_ID" "${WORKER_EPISODE}" "${AUDITOR_EPISODE}" <<'PYEOF'
import json, os, sys
runs_dir, self_id, wep, aep = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
dups = []
if wep == aep:
    dups.append(f"within-run:worker==auditor({wep})")
if os.path.isdir(runs_dir):
    for name in sorted(os.listdir(runs_dir)):
        if name == self_id:
            continue
        d = os.path.join(runs_dir, name)
        if not os.path.isdir(d):
            continue
        # (a) published runs
        p = os.path.join(d, "run.json")
        if os.path.isfile(p):
            try:
                rec = json.load(open(p, encoding="utf-8"))
            except Exception:
                rec = None
            if rec:
                sw, sa = rec.get("worker_episode"), rec.get("auditor_episode")
                if sw and sw in (wep, aep):
                    dups.append(f"{name}:stored_worker={sw}")
                if sa and sa in (wep, aep):
                    dups.append(f"{name}:stored_auditor={sa}")
        # (b) preserved INVALID runs (no run.json by construction)
        q = os.path.join(d, "round-1-run-record.json")
        if os.path.isfile(q):
            try:
                inv = json.load(open(q, encoding="utf-8"))
            except Exception:
                inv = None
            if inv:
                ep = (inv.get("episode") or {}).get("worker_episode")
                role = (inv.get("episode") or {}).get("auditor_episode")
                if ep and ep in (wep, aep):
                    dups.append(f"INVALID_EPISODE_REUSE:{inv.get('run_id')}:{ep}")
                if role and role in (wep, aep):
                    dups.append(f"INVALID_EPISODE_REUSE:{inv.get('run_id')}:{role}")
print(" ".join(dups))
PYEOF
)"
  if [ -n "$DUP" ]; then
    echo "PUBLISH_REFUSED reason=EPISODE_REUSE [$DUP]"; exit 3
  fi
fi

# stage, never write DEST directly: an invalid input or a staging failure must leave DEST as it
# was. Created only AFTER every preflight and identity gate — an earlier placement meant a
# refusal (missing plan_index, missing episode, ...) exited before cleanup and left
# *.staging.* residue behind (observed by the round-6 battery: 7 residue dirs).
STAGE="$DEST.staging.$$"
rm -rf "$STAGE"
mkdir -p "$STAGE" || { echo "PUBLISH_REFUSED reason=STAGE_CREATE_FAILED $STAGE"; exit 3; }
# The explicit refusals below clean the stage themselves; this trap also covers INTERRUPTION
# (fresh review on 9c5f059, P3: no trap meant a SIGINT left *.staging.<pid> behind).
trap '[ -n "${STAGE:-}" ] && rm -rf "$STAGE"' EXIT INT TERM

# fresh adversarial review on 9f8e4ee (P1-2): the copies were not rc-checked, so an unreadable
# report.md (the R9-11 gate above passes on stat) silently produced a record WITHOUT the report
# while PUBLISH_RUN OK was printed. Every copy is rc-checked; the staged artifact set is
# verified before promotion below.
for f in report.md acceptance.txt carrier-recheck.txt; do
  if [ -f "$EV/$f" ]; then
    cp "$EV/$f" "$STAGE/$f" || { rm -rf "$STAGE"; echo "PUBLISH_REFUSED reason=ARTIFACT_COPY_FAILED file=$f"; exit 3; }
  fi
done
if [ -f "$EV/telemetry.log" ]; then
  cp "$EV/telemetry.log" "$STAGE/telemetry.log" || { rm -rf "$STAGE"; echo "PUBLISH_REFUSED reason=ARTIFACT_COPY_FAILED file=telemetry.log"; exit 3; }
else
  : > "$STAGE/telemetry.log"
fi

"$PY" - "$EV" "$STAGE" "$DEST" <<'PYEOF'
import json, os, re, sys
ev, dest = sys.argv[1], sys.argv[2]
prior = sys.argv[3]
lines = open(f"{ev}/telemetry.log", encoding="utf-8", errors="replace").read().splitlines()
tel = {"fully_read": [], "partial_read": [], "grepped": [], "routes": [], "skills": [], "other": []}
for raw in lines:
    ln = raw.strip()  # match collection's strip() domain exactly (R8-8)
    m = re.match(r"^READ\s+(FULL|PARTIAL|GREP)\s+(.+)$", ln)
    if m:
        key = {"FULL": "fully_read", "PARTIAL": "partial_read", "GREP": "grepped"}[m.group(1)]
        tel[key].append(m.group(2).strip())
        continue
    m = re.match(r"^ROUTE\s+(\S+)\s+(\S+)\s+(LOADED|MISSING|SKIPPED)$", ln)
    if m:
        tel["routes"].append({"route_id": m.group(1), "target": m.group(2), "result": m.group(3)})
        continue
    m = re.match(r"^SKILL\s+(\S+)\s+(LOADED|UNAVAILABLE|NOT_REQUIRED|WRONG|NONE)$", ln)
    if m:
        tel["skills"].append({"name": m.group(1), "result": m.group(2)})
        continue
    if ln.strip():
        tel["other"].append(ln.strip())
json.dump(tel, open(f"{dest}/telemetry.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)

receipt = json.load(open(f"{ev}/receipt.json", encoding="utf-8"))
summary = {}
try:
    for ln in open(f"{ev}/collect-summary.txt", encoding="utf-8").read().splitlines():
        if "=" in ln:
            k, v = ln.split("=", 1)
            summary[k.strip()] = v.strip()
except FileNotFoundError:
    pass
acc = open(f"{dest}/acceptance.txt", encoding="utf-8", errors="replace").read()
# Current marker: "=== RC=<n> (tee=<n>) ==="; legacy marker tolerated. BOTH failure channels
# are preserved (R8-5/R9-10): a zero command rc with a failing tee still records the tee value.
pairs = [(int(a), int(b)) for a, b in re.findall(r"^=== RC=(-?\d+) \(tee=(-?\d+)\) ===$", acc, re.M)]
legacy = [int(a) for a in re.findall(r"^=== RC=(-?\d+) ===$", acc, re.M)]
fails = sorted(
    {x for rc, tee in pairs if (rc != 0 or tee != 0) for x in (rc, tee) if x != 0}
    | {rc for rc in legacy if rc != 0}
)
prev = {}
if os.path.exists(f"{prior}/run.json"):
    try:
        prev = json.load(open(f"{prior}/run.json", encoding="utf-8"))
    except Exception:
        prev = {}
run = {
    "run_id": receipt["run_id"],
    "task_id": receipt["task_id"],
    "arm": receipt["arm"],
    "expected_base": receipt["expected_base"],
    "actual_head_start": receipt["actual_head"],
    "collect_head": summary.get("head"),
    "worker_committed": summary.get("worker_committed"),
    "materials_commit": receipt.get("materials_commit"),
    "model_tier": receipt.get("model_tier"),
    "carrier_kind": receipt.get("carrier_kind"),
    "carrier_hash": receipt.get("carrier_hash"),
    "h2_rules_sha256": receipt.get("h2_rules_sha256"),
    "warm_bundle_sha256": receipt.get("warm_bundle_sha256"),
    "acceptance_nonzero_rcs": fails,
    "acceptance_statuses": [{"rc": rc, "tee": tee} for rc, tee in pairs],
    "model_observed": prev.get("model_observed") or os.environ.get("WORKER_MODEL", "default"),
    "worker_episode": prev.get("worker_episode") or os.environ.get("WORKER_EPISODE"),
    "auditor_episode": prev.get("auditor_episode") or os.environ.get("AUDITOR_EPISODE"),
    # Re-publication must not clobber a finalized review (R8-4).
    "status": prev.get("status") or "PENDING_REVIEW",
    "review": prev.get("review"),
}
json.dump(run, open(f"{dest}/run.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"composed run.json + telemetry.json for {receipt['run_id']}")
PYEOF
COMP_RC=$?
if [ "$COMP_RC" -ne 0 ]; then
  # Codex finding on 61dcf99 (P1): this step is not rc-checked, so a composition error (missing
  # acceptance.txt, malformed receipt, ...) still fell through to promotion: the finalized
  # destination was replaced by the PARTIAL stage, the backup was deleted and the script printed
  # PUBLISH_RUN OK. Refuse, discard the stage, and leave DEST exactly as it was.
  rm -rf "$STAGE"
  echo "PUBLISH_REFUSED reason=COMPOSITION_FAILED rc=$COMP_RC (staged artifacts discarded; DEST unchanged)"
  exit 3
fi
# fresh adversarial review on 9f8e4ee (P1-2): the composer reads acceptance.txt and telemetry.log
# but never verifies report.md reached the stage, so a failed copy surfaced only as a silent
# omission in the published record. Verify the FULL required artifact set before promotion.
# (The former `[ -L ]` half was removed as unreachable — cp dereferences, so a staged entry is
# never a symlink — rather than kept as a vacuous check; flagged by the 9c5f059 review.)
for f in report.md acceptance.txt carrier-recheck.txt telemetry.log telemetry.json run.json; do
  if [ ! -f "$STAGE/$f" ]; then
    rm -rf "$STAGE"
    echo "PUBLISH_REFUSED reason=STAGED_ARTIFACT_MISSING file=$f (refusing to promote an incomplete record)"
    exit 3
  fi
done

# R2 sanitization pass (placeholders only; must not alter meaning).
# Path forms are derived at RUNTIME (runs root / run worktree / evidence / materials worktree)
# plus user-home identity forms — no hard-coded macOS layout (R9-3).
"$PY" - "$STAGE" "$CUR_USER_PRE" "$H2_RUNS_ROOT" "$WT" "$EV" "$MATERIALS_WT_PRE" <<'PYEOF'
import pathlib, re as _re, sys
root = pathlib.Path(sys.argv[1])
user = sys.argv[2]
runs_root, wt, ev, materials_wt = sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
literal_reps = [(wt, "<RUN_WORKTREE>"),
                (ev, "<RUN_EVIDENCE>"),
                (runs_root, "<H2_RUNS_ROOT>"),
                (materials_wt, "<H2_WORKTREE>"),
                (f"/Users/{user}/.workbuddy/binaries/python/envs/default/bin/python", "<PY>"),
                (f"/Users/{user}", "<USER_HOME>")]
# An EMPTY replacement source is catastrophic, not cosmetic: str.replace("", X) inserts X
# between every character, silently corrupting every published artifact. This is reachable when
# the harness is invoked from a directory that is not a git worktree (git rev-parse then yields
# an empty string). Refuse instead of publishing a mangled record.
empty = [name for name, val in (("run_worktree", wt), ("run_evidence", ev),
                                ("runs_root", runs_root), ("materials_worktree", materials_wt),
                                ("user_home", f"/Users/{user}")) if not val]
if empty:
    print(f"PUBLISH_REFUSED reason=EMPTY_SANITIZER_SOURCE {empty} "
          f"(a replacement source resolved to an empty string; refusing to write corrupt artifacts)")
    raise SystemExit(2)
regex_reps = []
if len(user) >= 8:
    regex_reps.append((_re.compile(r"(?<![A-Za-z0-9._-])" + _re.escape(user) + r"(?![A-Za-z0-9._-])"),
                       "<USER>"))
else:
    print(f"WARNING: short login ({len(user)} chars) — bare-name redaction skipped (path-bounded forms only)")
changed = []
for p in sorted(root.rglob("*")):
    if not p.is_file():
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    o = t
    for a, b in literal_reps:
        t = t.replace(a, b)
    for rx, b in regex_reps:
        t = rx.sub(b, t)
    if t != o:
        p.write_text(t, encoding="utf-8")
        changed.append(p.name)
print("sanitized:", changed or "nothing-needed")
PYEOF
SAN_RC=$?
if [ "$SAN_RC" -ne 0 ]; then
  # The sanitizer refuses rather than writing a mangled record; that refusal must reach the
  # caller. Without this the script would print PUBLISH_RUN OK and exit 0 over a rejected
  # sanitization — a fail-open on the exact path that protects published artifacts.
  rm -rf "$STAGE"
  echo "PUBLISH_REFUSED reason=SANITIZATION_FAILED rc=$SAN_RC (staged artifacts discarded; DEST unchanged)"
  exit 3
fi
# fresh adversarial review on 9f8e4ee (P3): the sanitizer is a literal replacement table, so an
# equivalent spelling that misses the table would publish a machine-local path with rc=0 (the
# review demonstrated both /Users/<other-user> and an unresolved relative-spelling form). The
# published record must be host-path-free AT THE SOURCE; refuse rather than publish.
if grep -rqI "/Users/" "$STAGE" 2>/dev/null; then
  rm -rf "$STAGE"
  echo "PUBLISH_REFUSED reason=UNSANITIZED_HOST_PATH (a /Users/ path survived sanitization; refusing to publish)"
  exit 3
fi
# atomic promotion: DEST only ever moves to its final state in one step, so a failure above
# cannot leave a partially written publication
rm -rf "$DEST.prev.$$"
if [ -e "$DEST" ]; then mv "$DEST" "$DEST.prev.$$" || { rm -rf "$STAGE"; echo "PUBLISH_REFUSED reason=PROMOTION_FAILED"; exit 3; }; fi
if ! mv "$STAGE" "$DEST"; then
  [ -e "$DEST.prev.$$" ] && mv "$DEST.prev.$$" "$DEST"
  rm -rf "$STAGE"
  echo "PUBLISH_REFUSED reason=PROMOTION_FAILED (DEST restored)"; exit 3
fi
rm -rf "$DEST.prev.$$"
echo "PUBLISH_RUN OK run_id=$RUN_ID dest=$DEST"
