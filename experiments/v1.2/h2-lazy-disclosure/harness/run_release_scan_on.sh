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
DEST="$WT/.h2_validate_public_release.py"
cp "$SRC" "$DEST" || { echo "RELEASE_SCAN_FAIL reason=COPY_FAILED"; exit 2; }
( cd "$WT" && PUBLIC_RELEASE=1 "$PY" "$DEST" )
rc=$?
rm -f "$DEST"
exit $rc
