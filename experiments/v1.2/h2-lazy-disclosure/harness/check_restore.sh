#!/usr/bin/env bash
# H2 harness — check_restore.sh <RUN_ID>
# Restore discipline (used as a mechanical acceptance command for n02):
#   (1) after normalizing ONLY the exact root-level harness artifacts (CODEBUDDY.md /
#       .h2-telemetry.log / H2_RULES.md / H2_AGENTS.md / H2_WARM/**), the worktree status must be
#       EMPTY — a freshly prepared worktree normalizes to nothing, so any remaining entry is
#       worker residue;
#   (2) ruff.toml in the worktree must byte-equal the FROZEN BASE BLOB (raw or CRLF-normalized).
# Exits nonzero on ANY failed assertion.
#
# HARDENING (fresh adversarial review on 9f8e4ee, P0):
#   * the previous version compared against EV/status-pre-ignored.txt — a snapshot NOTHING wrote
#     and the WORKER could create/append to; the expectation is now stated directly (empty);
#   * the previous version compared ruff.toml against receipt["ruff_toml_worktree_sha256"] when
#     present, so editing the file AND rewriting that field passed; the comparison is now against
#     the frozen base blob only, and the receipt is not consulted for any verdict;
#   * base comes from the frozen plan+registry (frozen_run_facts.py), not from the receipt.
set -u
unset GIT_DIR GIT_WORK_TREE GIT_COMMON_DIR GIT_INDEX_FILE
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
RUN_ID="${1:?usage: check_restore.sh <RUN_ID>}"
WT="$H2_RUNS_ROOT/worktrees/$RUN_ID"
EV="$H2_RUNS_ROOT/evidence/$RUN_ID"
if [ ! -d "$WT" ]; then echo "RESTORE_FAIL reason=NO_WORKTREE"; exit 2; fi
# refuse a worktree whose own git metadata was used to hide changes (fresh review 9c5f059, P0):
# `--assume-unchanged` made STATUS_RESTORED read YES over a dirty tree.
GM="$(bash "$HERE/check_git_metadata.sh" "$WT")"; _gmrc=$?
if [ "$_gmrc" -eq 2 ]; then
  echo "RESTORE_FAIL reason=WORKTREE_GIT_METADATA_UNREADABLE"; exit 2
fi
if [ "$_gmrc" -ne 0 ]; then
  echo "RESTORE_FAIL reason=WORKTREE_GIT_METADATA_TAMPERED [$GM]"; exit 2
fi
FROZEN="$("$PY" "$HERE/frozen_run_facts.py" "$EXP_DIR" "$RUN_ID")"
_frc=$?
if [ "$_frc" -ne 0 ]; then
  if [ "$_frc" -eq 2 ]; then
    echo "RESTORE_FAIL reason=NO_FROZEN_ROW run_id=$RUN_ID"
  else
    echo "RESTORE_FAIL reason=FROZEN_FACTS_UNREADABLE"
  fi
  exit 2
fi
"$PY" - "$WT" "$FROZEN" <<'PYEOF'
import hashlib, os, subprocess, sys
wt = sys.argv[1]
base = sys.argv[2].split("\t")[1]
ROOT_ARTIFACTS = {"CODEBUDDY.md", ".h2-telemetry.log", "H2_RULES.md", "H2_AGENTS.md"}


def run(*a):
    return subprocess.run(a, capture_output=True)


def norm(lines):
    out = []
    for line in lines:
        s = line.rstrip("\n")
        body = s[3:] if len(s) > 3 else s  # strip porcelain XY+space (incl. '!!' ignored)
        if body in ROOT_ARTIFACTS or body.startswith("H2_WARM/"):
            continue
        out.append(s)
    return out


failed = False
cur = norm(run("git", "-C", wt, "status", "--porcelain", "--ignored", "--untracked-files=all").stdout
           .decode("utf-8", errors="replace").splitlines())
# A freshly prepared worktree has ONLY the placed artifacts in its status; after normalization
# that is the empty list. Anything else is worker residue that was not restored.
restored = (cur == [])
print("STATUS_RESTORED =", "YES" if restored else "NO")
if not restored:
    print("  RESIDUE NOW:", cur)
    failed = True

blob = run("git", "-C", wt, "show", f"{base}:ruff.toml")
if blob.returncode == 0:
    p = os.path.join(wt, "ruff.toml")
    if not os.path.exists(p):
        print("RUFF_TOML_RESTORED = NO (absent in worktree; present at the frozen base)")
        failed = True
    else:
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        raw_h = hashlib.sha256(blob.stdout).hexdigest()
        crlf_h = hashlib.sha256(blob.stdout.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")).hexdigest()
        print("RUFF_TOML_WORKTREE_SHA256 =", h)
        print("RUFF_TOML_BASE_SHA256     =", raw_h)
        # raw OR CRLF-normalized: robust to autocrlf/smudge filters WITHOUT trusting a
        # worker-writable recorded hash.
        ok = h in (raw_h, crlf_h)
        print("RUFF_TOML_RESTORED =", "YES" if ok else "NO")
        if not ok:
            failed = True
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
