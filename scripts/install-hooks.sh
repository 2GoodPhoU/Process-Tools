#!/usr/bin/env bash
#
# Install Process-Tools git hooks into .git/hooks/.
#
# Works in:
#   - Linux / macOS bash
#   - Git Bash on Windows (shipped with Git for Windows)
#
# Run from the repo root:
#     bash scripts/install-hooks.sh
#
# Idempotent — safe to run multiple times. Overwrites any existing
# pre-commit hook (you'll see a warning).

set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

if [[ ! -d "$HOOKS_DIR" ]]; then
    echo "error: $HOOKS_DIR does not exist." >&2
    echo "Are you running this from a git working tree?" >&2
    exit 1
fi

src="$REPO_ROOT/scripts/pre-commit-check.sh"
dst="$HOOKS_DIR/pre-commit"

if [[ -e "$dst" || -L "$dst" ]]; then
    echo "note: overwriting existing $dst"
fi

cp "$src" "$dst"
chmod +x "$dst"

echo "installed: $dst"
echo ""
echo "Test: stage a Python file with a syntax error, then 'git commit'."
echo "The hook will reject the commit with a friendly error message."
