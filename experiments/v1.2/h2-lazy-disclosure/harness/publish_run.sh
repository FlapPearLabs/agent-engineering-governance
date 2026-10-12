#!/usr/bin/env bash
# H2 harness — publish_run.sh <RUN_ID>
# Copies a run's durable evidence into the repo-tracked runs/<RUN_ID>/ record (R2-sanitized):
#   report.md, acceptance.txt, carrier-recheck.txt, telemetry.log -> telemetry.json, run.json
# Safe to re-run (idempotent overwrite); refuses to publish when the evidence dir is absent.
set -u
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
mkdir -p "$DEST"

for f in report.md acceptance.txt carrier-recheck.txt; do
  if [ -f "$EV/$f" ]; then cp "$EV/$f" "$DEST/$f"; fi
done
[ -f "$EV/telemetry.log" ] && cp "$EV/telemetry.log" "$DEST/telemetry.log" || : > "$DEST/telemetry.log"

"$PY" - "$EV" "$DEST" <<'PYEOF'
import json, os, re, sys
ev, dest = sys.argv[1], sys.argv[2]
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
if os.path.exists(f"{dest}/run.json"):
    try:
        prev = json.load(open(f"{dest}/run.json", encoding="utf-8"))
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

# R2 sanitization pass (placeholders only; must not alter meaning).
# Path forms are derived at RUNTIME (runs root / run worktree / evidence / materials worktree)
# plus user-home identity forms — no hard-coded macOS layout (R9-3).
CUR_USER="$(id -un)"
MATERIALS_WT="$(git -C "$EXP_DIR" rev-parse --show-toplevel)"
"$PY" - "$DEST" "$CUR_USER" "$H2_RUNS_ROOT" "$WT" "$EV" "$MATERIALS_WT" <<'PYEOF'
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
echo "PUBLISH_RUN OK run_id=$RUN_ID dest=$DEST"
