#!/usr/bin/env pwsh
# Lint + format-check + typecheck for backend (ruff, ty) and app (biome, tsc).
# Run from repo root. Exits non-zero on first failure.

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$failed = $false

function Invoke-Step {
    param([string]$Name, [string]$WorkingDir, [string]$Exe, [string[]]$Arguments)

    Write-Host "==> $Name" -ForegroundColor Cyan
    Push-Location $WorkingDir
    try {
        & $Exe @Arguments
        if ($LASTEXITCODE -ne 0) {
            Write-Host "FAILED: $Name" -ForegroundColor Red
            $script:failed = $true
        }
    } finally {
        Pop-Location
    }
}

$backend = Join-Path $repoRoot 'backend'
$app = Join-Path $repoRoot 'app'

Invoke-Step -Name 'ruff check (backend)' -WorkingDir $backend -Exe 'uv' -Arguments @('run', 'ruff', 'check', '.')
Invoke-Step -Name 'ruff format --check (backend)' -WorkingDir $backend -Exe 'uv' -Arguments @('run', 'ruff', 'format', '--check', '.')
Invoke-Step -Name 'ty check (backend)' -WorkingDir $backend -Exe 'uv' -Arguments @('run', 'ty', 'check')

Invoke-Step -Name 'biome check (app)' -WorkingDir $app -Exe 'npx' -Arguments @('biome', 'check', '.')
Invoke-Step -Name 'tsc --noEmit (app)' -WorkingDir $app -Exe 'npx' -Arguments @('tsc', '--noEmit')

if ($failed) {
    Write-Host "`nverify: FAILED" -ForegroundColor Red
    exit 1
}

Write-Host "`nverify: OK" -ForegroundColor Green
exit 0
