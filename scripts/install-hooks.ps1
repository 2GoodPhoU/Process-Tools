# Install the Process-Tools pre-commit hook on Windows.
#
# Usage (from repo root, in PowerShell):
#     .\scripts\install-hooks.ps1
#
# The hook itself is a bash script — git on Windows runs hooks via the
# bash that ships with Git for Windows, so you don't need anything
# extra installed.

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$hooksDir = Join-Path $repoRoot ".git\hooks"

if (-not (Test-Path $hooksDir)) {
    Write-Host "error: $hooksDir does not exist." -ForegroundColor Red
    Write-Host "Are you running this from a git working tree?" -ForegroundColor Red
    exit 1
}

$src = Join-Path $repoRoot "scripts\pre-commit-check.sh"
$dst = Join-Path $hooksDir "pre-commit"

if (Test-Path $dst) {
    Write-Host "note: overwriting existing $dst"
}

Copy-Item -Path $src -Destination $dst -Force

Write-Host "installed: $dst" -ForegroundColor Green
Write-Host ""
Write-Host "Test: stage a Python file with a syntax error, then 'git commit'."
Write-Host "The hook will reject the commit with a friendly error message."
