#!/usr/bin/env bash
#
# Run every tool's test suite and report a single green/red summary.
#
# Usage:
#     bash scripts/test_all.sh
#
# Exits 0 if every suite passes, non-zero if any suite fails.
# Prints individual suite summaries plus a final aggregate count.

set -uo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    PY=python
fi

TOOLS=(
    "process-tools-common"
    "compliance-matrix"
    "nimbus-skeleton"
    "requirements-extractor"
)

overall=0
total_ran=0
declare -a failed_tools

for tool in "${TOOLS[@]}"; do
    echo "==================== $tool ===================="
    pushd "$REPO_ROOT/$tool" >/dev/null

    # Capture the unittest output so we can scrape the "Ran N tests" line.
    out="$("$PY" -m unittest discover tests 2>&1)"
    rc=$?

    echo "$out" | tail -3

    if [[ $rc -ne 0 ]]; then
        overall=1
        failed_tools+=("$tool")
    fi

    # Scrape the "Ran N tests" count.
    n=$(echo "$out" | grep -E "^Ran [0-9]+ tests" | awk '{print $2}')
    if [[ -n "${n:-}" ]]; then
        total_ran=$((total_ran + n))
    fi

    popd >/dev/null
    echo ""
done

echo "==================== summary ===================="
if [[ $overall -eq 0 ]]; then
    echo "ALL GREEN — $total_ran tests across ${#TOOLS[@]} tools."
else
    echo "FAILED — ${#failed_tools[@]} tool(s) had failures: ${failed_tools[*]}"
    echo "Total ran: $total_ran tests."
fi

exit $overall
