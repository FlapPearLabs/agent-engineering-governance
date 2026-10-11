#!/usr/bin/env bash
# H2 harness — check_restore.sh <RUN_ID>
# Fresh status capture, normalized against the two harness artifacts (CODEBUDDY.md carrier,
# .h2-telemetry.log), compared to the prepare-time snapshot; plus a byte-level ruff.toml
# check against the base blob when ruff.toml exists at the base (the n02 restore discipline).
set -u
PY="${PY:-python3}"
H2_RUNS_ROOT="${H2_RUNS_ROOT:?set H2_RUNS_ROOT}"
RUN_ID="${1:?usage: check_restore.sh <RUN_ID>}"
WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
if [ ! -f "$EV/receipt.json" ]; then echo "RESTORE_FAIL reason=NO_RECEIPT"; exit 2; fi
"$PY" - "$WT" "$EV" <<'PYEOF'
import hashlib, json, os, subprocess, sys
wt, ev = sys.argv[1], sys.argv[2]
receipt = json.load(open(f"{ev}/receipt.json", encoding="utf-8"))
base = receipt["expected_base"]

def run(*a):
    return subprocess.run(a, capture_output=True, text=True)

def norm(lines):
    out = []
    for line in lines:
        s = line.strip()
        if s.endswith("CODEBUDDY.md") or s.endswith(".h2-telemetry.log"):
            continue
        out.append(line)
    return out

prev = norm(open(f"{ev}/status-pre.txt", encoding="utf-8").read().splitlines())
cur = norm(run("git", "-C", wt, "status", "--porcelain").stdout.splitlines())
restored = (prev == cur)
print("STATUS_RESTORED =", "YES" if restored else "NO")
if not restored:
    print("  PRE :", prev)
    print("  NOW :", cur)

blob = run("git", "-C", wt, "rev-parse", f"{base}:ruff.toml")
if blob.returncode == 0:
    p = os.path.join(wt, "ruff.toml")
    if os.path.exists(p):
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        show = run("git", "-C", wt, "show", f"{base}:ruff.toml")
        base_h = hashlib.sha256(show.stdout.encode("utf-8")).hexdigest()
        print("RUFF_TOML_WORKTREE_SHA256 =", h)
        print("RUFF_TOML_BASE_SHA256     =", base_h)
        print("RUFF_TOML_RESTORED =", "YES" if h == base_h else "NO")
    else:
        print("RUFF_TOML_RESTORED = N/A (absent in worktree)")
else:
    print("RUFF_TOML_RESTORED = N/A (absent at base)")
PYEOF
