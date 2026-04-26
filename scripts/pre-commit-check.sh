#!/usr/bin/env bash
#
# Pre-commit guard against the documented truncation hazard.
#
# Two checks on every staged Python file:
#   1. py_compile must succeed (catches syntax errors / unterminated strings —
#      the typical truncation symptom).
#   2. The file must contain zero NUL bytes (the documented null-byte-tail
#      corruption variant).
#
# Designed to run as the repo's git pre-commit hook. Self-contained — no
# pip installs, no `pre-commit` framework dependency — so it works in
# the Defense-network venv setup where extra tooling is friction.
#
# Install:
#     ln -sf ../../scripts/pre-commit-check.sh .git/hooks/pre-commit
#     chmod +x .git/hooks/pre-commit
#
# Or via the Makefile:  make install-hooks

set -euo pipefail

# --------------------------------------------------------------------------
# Find staged files
# --------------------------------------------------------------------------
# `git diff --cached --name-only --diff-filter=ACM` lists files that are
# Added / Copied / Modified in the index — exactly the set we care about.
mapfile -t staged_py < <(git diff --cached --name-only --diff-filter=ACM | grep -E '\.py$' || true)

if [[ ${#staged_py[@]} -eq 0 ]]; then
    exit 0
fi

# --------------------------------------------------------------------------
# Find a working python
# --------------------------------------------------------------------------
PY="${PYTHON:-python3}"
if ! command -v "$PY" >/dev/null 2>&1; then
    PY=python
fi

# --------------------------------------------------------------------------
# Run the two checks
# --------------------------------------------------------------------------
fail=0

for f in "${staged_py[@]}"; do
    # File may have been renamed/deleted between staging and now; guard.
    if [[ ! -f "$f" ]]; then
        continue
    fi

    # 1. Null-byte check — fast, catches the documented variant.
    if grep -qaP '\x00' -- "$f"; then
        echo "pre-commit: $f contains NUL bytes (truncation-corruption hazard)" >&2
        fail=1
        continue
    fi

    # 2. py_compile — catches syntax errors / unterminated strings.
    if ! "$PY" -m py_compile "$f" >/dev/null 2>&1; then
        echo "pre-commit: $f failed py_compile (syntax error / truncation?)" >&2
        "$PY" -m py_compile "$f" || true   # re-run to surface the message
        fail=1
        continue
    fi
done

if [[ $fail -ne 0 ]]; then
    echo "" >&2
    echo "pre-commit: aborting commit. Fix the issue(s) above and re-stage." >&2
    echo "  - For truncation suspicion: rewrite via heredoc and verify with" >&2
    echo "    'wc -l <file>' and 'tail -5 <file>' before re-staging." >&2
    exit 1
fi

exit 0
