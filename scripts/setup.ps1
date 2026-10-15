#Requires -Version 7
<#
.SYNOPSIS
    One-shot local setup for DrinkingBuddy (backend + app). Idempotent - safe to re-run.

.PARAMETER Up
    After installing, start the backend stack (Docker) and wait for /health.

.EXAMPLE
    ./scripts/setup.ps1
    ./scripts/setup.ps1 -Up

.NOTES
    Bash equivalent: scripts/setup.sh
#>
param([switch]$Up)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $repoRoot 'backend'
$app = Join-Path $repoRoot 'app'

function Step([string]$Name) { Write-Host "`n==> $Name" -ForegroundColor Cyan }
function Fail([string]$Message) { Write-Host "ERROR: $Message" -ForegroundColor Red; exit 1 }
function Invoke-Native([string]$Dir, [string]$Exe, [string[]]$Arguments) {
    Push-Location $Dir
    try {
        & $Exe @Arguments
        if ($LASTEXITCODE -ne 0) { Fail "$Exe $($Arguments -join ' ') failed (exit $LASTEXITCODE)" }
    } finally {
        Pop-Location
    }
}

Step 'Checking prerequisites'
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) { Fail 'uv not found - install: https://docs.astral.sh/uv/getting-started/installation/' }
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { Fail 'node not found - install Node 20.19.4+ / 22.13+ / 24.3+ (see app/.nvmrc)' }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Fail 'npm not found (ships with Node)' }
$v = [version]((node --version).TrimStart('v'))
$nodeOk = ($v.Major -eq 20 -and $v -ge [version]'20.19.4') -or ($v.Major -eq 22 -and $v.Minor -ge 13) -or
          ($v.Major -eq 24 -and $v.Minor -ge 3) -or ($v.Major -ge 25)
if (-not $nodeOk) { Fail "Node $v too old for React Native 0.86 (need ^20.19.4 || ^22.13.0 || ^24.3.0 || >=25)" }
Write-Host "uv $((uv --version).Split(' ')[1]), node v$v"

$dockerOk = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    docker info *> $null
    $dockerOk = $LASTEXITCODE -eq 0
}
if ($dockerOk) { Write-Host 'docker daemon reachable' }
else { Write-Host 'WARNING: Docker daemon not reachable - needed for the backend stack and integration tests, not for install.' -ForegroundColor Yellow }

Step 'Creating .env files (existing ones are left alone)'
foreach ($dir in @($backend, $app)) {
    $rel = [IO.Path]::GetRelativePath($repoRoot, $dir)
    if (Test-Path (Join-Path $dir '.env')) {
        Write-Host "keep   $rel/.env"
    } else {
        Copy-Item (Join-Path $dir '.env.example') (Join-Path $dir '.env')
        Write-Host "create $rel/.env"
    }
}

Step 'Backend: uv sync --extra dev'
Invoke-Native $backend 'uv' @('sync', '--extra', 'dev')

Step 'App: npm ci'
Invoke-Native $app 'npm' @('ci')

if ($Up) {
    if (-not $dockerOk) { Fail '-Up needs a running Docker daemon' }
    $composeArgs = @('compose', '-f', 'docker-compose.yml')
    $plugins = docker plugin ls --format '{{.Name}}' 2>$null
    if (-not ($plugins -match 'loki')) {
        Write-Host 'Loki logging plugin not installed - using docker-compose.windows.yml (json-file logs). See docs/local_dev.md.'
        $composeArgs += @('-f', 'docker-compose.windows.yml')
    }
    Step "Backend stack: docker $($composeArgs -join ' ') up -d --build --wait"
    Invoke-Native $backend 'docker' ($composeArgs + @('up', '-d', '--build', '--wait'))
    Invoke-RestMethod http://localhost:8000/health | ConvertTo-Json -Compress
}

Step 'Done'
Write-Host @'
Next:
  Backend tests:  ./scripts/test.ps1 [-Suite integration|all]   (integration needs Docker)
  Lint/typecheck: ./scripts/verify.ps1
  Backend stack:  ./scripts/setup.ps1 -Up                        (API :8000, Mailpit :8025, Grafana :3000)
  App:            cd app; npx expo run:android | run:ios         (dev build - Expo Go lacks react-native-webrtc)
'@
