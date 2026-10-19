#Requires -Version 7
<#
.SYNOPSIS
    Run DrinkingBuddy on a physical Android phone over wifi - no USB cable.

.DESCRIPTION
    1. Starts the backend stack (via setup.ps1 -Up) unless /health already answers.
    2. Opens inbound TCP 8000 (API) + 8081 (Metro) in Windows Firewall on private
       networks - one UAC prompt, first run only.
    3. Optionally builds the dev-client APK in the cloud (EAS) - install it from
       the QR code/link it prints. Only needed once, or after native deps change.
    4. Starts Metro for the dev client. Open the DrinkingBuddy app on the phone
       (same wifi) and pick this machine, or scan the QR code.

    The app finds the backend on its own (port 8000 on the Metro host), and dev
    builds sign in straight away without opening the magic-link email.

.PARAMETER Build
    Run `eas build --profile development --platform android` first.

.EXAMPLE
    ./scripts/phone.ps1 -Build   # first time
    ./scripts/phone.ps1          # every time after
#>
param([switch]$Build)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$app = Join-Path $repoRoot 'app'
$firewallRule = 'DrinkingBuddy dev (API 8000, Metro 8081)'

function Step([string]$Name) { Write-Host "`n==> $Name" -ForegroundColor Cyan }
function Fail([string]$Message) { Write-Host "ERROR: $Message" -ForegroundColor Red; exit 1 }

Step 'Backend'
try {
    Invoke-RestMethod http://localhost:8000/health -TimeoutSec 3 | Out-Null
    Write-Host 'already running on :8000'
} catch {
    & (Join-Path $PSScriptRoot 'setup.ps1') -Up
    if ($LASTEXITCODE -ne 0) { Fail 'backend failed to start' }
}

Step 'Firewall'
if (Get-NetFirewallRule -DisplayName $firewallRule -ErrorAction SilentlyContinue) {
    Write-Host 'rule present'
} else {
    Write-Host 'adding inbound rule for TCP 8000/8081 on private networks (UAC prompt)'
    $cmd = "New-NetFirewallRule -DisplayName '$firewallRule' -Direction Inbound -Protocol TCP -LocalPort 8000,8081 -Action Allow -Profile Private"
    Start-Process pwsh -Verb RunAs -Wait -ArgumentList '-NoProfile', '-Command', $cmd
    if (-not (Get-NetFirewallRule -DisplayName $firewallRule -ErrorAction SilentlyContinue)) {
        Fail 'firewall rule not created (UAC declined?)'
    }
}
$public = Get-NetConnectionProfile | Where-Object NetworkCategory -eq 'Public'
if ($public) {
    Write-Host "WARNING: network '$($public.Name -join ', ')' is Public - the phone can't reach this PC. Switch it to Private in Windows network settings (only on a network you trust)." -ForegroundColor Yellow
}

if ($Build) {
    Step 'Cloud build: dev-client APK (EAS)'
    Push-Location $app
    try {
        npx eas-cli build --profile development --platform android
        if ($LASTEXITCODE -ne 0) { Fail 'eas build failed' }
    } finally { Pop-Location }
    Write-Host 'Open the link/QR above on the phone and install the APK, then come back here.'
}

Step 'Metro (dev client)'
$lanIp = (Get-NetIPConfiguration | Where-Object { $_.IPv4DefaultGateway -and $_.NetAdapter.Status -eq 'Up' } |
    Select-Object -First 1).IPv4Address.IPAddress
Write-Host "Phone must be on the same wifi. PC address: $lanIp (API http://${lanIp}:8000)"
# Pin Metro to the wifi adapter - otherwise it can advertise a Docker/WSL virtual
# adapter IP, and the app derives the API host from it.
$env:REACT_NATIVE_PACKAGER_HOSTNAME = $lanIp
Push-Location $app
try {
    npx expo start --dev-client
} finally { Pop-Location }
