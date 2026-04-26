# Run every tool's test suite and report a single green/red summary.
#
# Usage (from repo root, in PowerShell):
#     .\scripts\test_all.ps1
#
# Exits 0 if every suite passes, non-zero if any suite fails.

$ErrorActionPreference = "Continue"

$repoRoot = Split-Path -Parent $PSScriptRoot
$tools = @(
    "process-tools-common",
    "compliance-matrix",
    "nimbus-skeleton",
    "requirements-extractor"
)

$python = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }

$totalRan = 0
$failed = @()

foreach ($tool in $tools) {
    Write-Host "==================== $tool ===================="
    Push-Location (Join-Path $repoRoot $tool)
    try {
        $output = & $python -m unittest discover tests 2>&1 | Out-String
        $exitCode = $LASTEXITCODE

        # Show last few lines (the summary)
        $lines = $output.TrimEnd() -split "`n"
        $lines | Select-Object -Last 3 | ForEach-Object { Write-Host $_ }

        # Scrape "Ran N tests"
        if ($output -match "Ran (\d+) tests") {
            $totalRan += [int]$Matches[1]
        }

        if ($exitCode -ne 0) {
            $failed += $tool
        }
    } finally {
        Pop-Location
    }
    Write-Host ""
}

Write-Host "==================== summary ===================="
if ($failed.Count -eq 0) {
    Write-Host "ALL GREEN -- $totalRan tests across $($tools.Count) tools." -ForegroundColor Green
    exit 0
} else {
    Write-Host "FAILED -- $($failed.Count) tool(s) had failures: $($failed -join ', ')" -ForegroundColor Red
    Write-Host "Total ran: $totalRan tests."
    exit 1
}
