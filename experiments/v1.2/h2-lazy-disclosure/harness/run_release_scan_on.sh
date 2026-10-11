#!/usr/bin/env bash
# H2 harness — run_release_scan_on.sh <WORKTREE> [PY]
# Runs the current-era R2 release scanner against the RUN WORKTREE by copying the checker
# INTO the candidate first: validate_public_release.py resolves its scan root from
# __file__.parent.parent, so an external invocation would scan the checker's own checkout
# (bot review R5-3). The temp copy is removed afterwards.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
H2_REPO="$(git -C "$(cd "$HERE/.." && pwd)" rev-parse --show-toplevel)" \
  || { echo "RELEASE_SCAN_FAIL reason=H2_REPO_UNREADABLE"; exit 2; }
WT="${1:?usage: run_release_scan_on.sh <WORKTREE> [PY]}"
PY="${2:-python3}"
SRC="$H2_REPO/scripts/validate_public_release.py"
[ -f "$SRC" ] || { echo "RELEASE_SCAN_FAIL reason=CHECKER_MISSING $SRC"; exit 2; }
# The checker resolves its scan root as __file__.parent.parent. To make that resolve to the
# CANDIDATE worktree, the copy must sit exactly two levels below $WT (R6-1): $WT/.h2_scan_tools/<file>.
TOOLS_DIR="$WT/.h2_scan_tools"
# Clean any leftover from an interrupted prior run, then place the copy. (An earlier version
# refused on occupancy; a leftover dir from an aborted battery turned that into a spurious
# rc=2 — recorded in precondition/p1-p2-dryrun.txt [12]/[12a].)
rm -rf "$TOOLS_DIR" 2>/dev/null || true
mkdir -p "$TOOLS_DIR" || { echo "RELEASE_SCAN_FAIL reason=MKDIR_FAILED"; exit 2; }
DEST="$TOOLS_DIR/validate_public_release.py"
cp "$SRC" "$DEST" || { echo "RELEASE_SCAN_FAIL reason=COPY_FAILED"; exit 2; }
( cd "$WT" && PUBLIC_RELEASE=1 "$PY" "$DEST" )
rc=$?
rm -rf "$TOOLS_DIR" 2>/dev/null || true
exit $rc
