#!/usr/bin/env bash
# H2 harness — check_restore.sh <RUN_ID>
# Fresh status capture, normalized ONLY for the exact root-level harness artifacts
# (CODEBUDDY.md / .h2-telemetry.log / H2_RULES.md / H2_AGENTS.md — [10]), compared to the
# prepare-time snapshot; plus a byte-level ruff.toml check against the base blob when
# ruff.toml exists at the base (the n02 restore discipline). Exits nonzero on ANY failed
# assertion ([14]; used as a mechanical acceptance command for n02).
set -u
PY="${PY:-python3}"
H2_RUNS_ROOT="${H2_RUNS_ROOT:?set H2_RUNS_ROOT}"
RUN_ID="${1:?usage: check_restore.sh <RUN_ID>}"
WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
if [ ! -f "$EV/receipt.json" ]; then echo "RESTORE_FAIL reason=NO_RECEIPT"; exit 2; fi
"$PY" - "$WT" "$EV" <<'PYEOF'
import hashlib, json, os, re, subprocess, sys
wt, ev = sys.argv[1], sys.argv[2]
receipt = json.load(open(f"{ev}/receipt.json", encoding="utf-8"))
base = receipt["expected_base"]
ROOT_ARTIFACTS = {"CODEBUDDY.md", ".h2-telemetry.log", "H2_RULES.md", "H2_AGENTS.md"}
def run(*a):
    return subprocess.run(a, capture_output=True, text=True)

def norm(lines):
    out = []
    for line in lines:
        s = line.rstrip("\n")
        body = s[3:] if len(s) > 3 else s  # strip porcelain XY+space (incl. '!!' ignored)
        if body in ROOT_ARTIFACTS or body.startswith(("H2_WARM/", ".h2_scan_tools/")):
            continue
        out.append(s)
    return out

failed = False
prev = norm(open(f"{ev}/status-pre-ignored.txt", encoding="utf-8").read().splitlines())
cur = norm(run("git", "-C", wt, "status", "--porcelain", "--ignored").stdout.splitlines())
restored = (prev == cur)
print("STATUS_RESTORED =", "YES" if restored else "NO")
if not restored:
    print("  PRE :", prev)
    print("  NOW :", cur)
    failed = True

blob = run("git", "-C", wt, "rev-parse", f"{base}:ruff.toml")
recorded = receipt.get("ruff_toml_worktree_sha256") or ""
if blob.returncode == 0 or recorded:
    p = os.path.join(wt, "ruff.toml")
    if os.path.exists(p):
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        print("RUFF_TOML_WORKTREE_SHA256 =", h)
        if recorded:
            # Prepared-worktree byte hash (R6-12): robust to autocrlf / smudge filters.
            print("RUFF_TOML_PREPARED_SHA256 =", recorded)
            ok = h == recorded
        else:
            show = run("git", "-C", wt, "show", f"{base}:ruff.toml")
            base_h = hashlib.sha256(show.stdout.encode("utf-8")).hexdigest()
            print("RUFF_TOML_BASE_SHA256     =", base_h)
            ok = h == base_h
        print("RUFF_TOML_RESTORED =", "YES" if ok else "NO")
        if not ok:
            failed = True
    else:
        print("RUFF_TOML_RESTORED = N/A (absent in worktree)")
else:
    print("RUFF_TOML_RESTORED = N/A (absent at base)")

sys.exit(1 if failed else 0)
PYEOF
rc=$?
if [ "$rc" -ne 0 ]; then
  echo "RESTORE_CHECK = FAIL (rc=$rc)"
else
  echo "RESTORE_CHECK = PASS"
fi
exit $rc
