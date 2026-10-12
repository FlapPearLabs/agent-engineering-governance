#!/usr/bin/env bash
# H2 harness — list_changes.sh <WORKTREE>
# Prints the worker's complete change surface, INCLUDING untracked files ([31]), excluding
# only the root-level harness delivery artifacts (CODEBUDDY.md / .h2-telemetry.log /
# H2_RULES.md / H2_AGENTS.md). Used by scope-acceptance entries. Fails closed on a bad
# worktree or failed git inspection.
set -uo pipefail
WT="${1:?usage: list_changes.sh <WORKTREE>}"
if ! git -C "$WT" rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "LIST_CHANGES_FAIL reason=NOT_A_GIT_WORKTREE $WT"
  exit 2
fi
changed="$(git -C "$WT" status --porcelain=v1 --untracked-files=all -z \
  | tr '\0' '\n' | sed -E 's/^...//' | sed 's/^.* -> //' | sort -u)" \
  || { echo "LIST_CHANGES_FAIL reason=GIT_INSPECTION_FAILED"; exit 2; }
printf '%s\n' "$changed" | grep -vE '^(CODEBUDDY\.md|\.h2-telemetry\.log|H2_RULES\.md|H2_AGENTS\.md)$' | grep -v '^H2_WARM/' || true
