#!/bin/sh
# H5 Task C: run the chainability measurement read-only on a throwaway clone.
#
# The measurement needs the frozen history and the frozen gate at one exact commit, so it runs
# in a `--shared` clone (objects borrowed read-only, no write into the real repository) that is
# checked out detached at HEAD and deleted afterwards. Nothing outside the temp dir is written.
#
#   PYTHON=/path/to/python sh experiments/v1.2/h5-verified-state/tasks/run_chain_measurement.sh
set -eu
ROOT=$(git rev-parse --show-toplevel)
PYTHON=${PYTHON:-python3}
SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/h5-chain-XXXXXX")
cleanup() {
    rm -rf "$SCRATCH"
}
trap cleanup EXIT INT TERM
git clone --quiet --shared --no-checkout "$ROOT" "$SCRATCH/repo"
git -C "$SCRATCH/repo" checkout --quiet --detach "$(git -C "$ROOT" rev-parse HEAD)"
env -u PYTHONPATH "$PYTHON" \
    "$ROOT/experiments/v1.2/h5-verified-state/tasks/measure_chain.py" \
    --repo "$SCRATCH/repo" "$@"
