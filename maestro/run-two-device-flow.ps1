<#
.SYNOPSIS
Runs a two-device Maestro flow (match-and-call.yaml or report-block.yaml) on
two Android emulators/devices in parallel.

.DESCRIPTION
Maestro CLI (non-Cloud) drives one device per invocation - see the comment
header in match-and-call.yaml. This script launches two `maestro test`
processes against two device serials, each with a different DEVICE_ROLE
(a/b), and waits for both to finish. UNVERIFIED against a live Maestro run -
see tasks/NEEDS-HUMAN-REVIEW-maestro-e2e.md item 6.

.PARAMETER FlowFile
Path to the flow YAML (e.g. match-and-call.yaml or report-block.yaml).

.PARAMETER DeviceA
adb device serial for the "a" role.

.PARAMETER DeviceB
adb device serial for the "b" role.

.EXAMPLE
./run-two-device-flow.ps1 -FlowFile match-and-call.yaml -DeviceA emulator-5554 -DeviceB emulator-5556
#>
param(
    [Parameter(Mandatory = $true)][string]$FlowFile,
    [Parameter(Mandatory = $true)][string]$DeviceA,
    [Parameter(Mandatory = $true)][string]$DeviceB,
    [string]$ApiBaseUrl = "http://10.0.2.2:8000"
)

$flowPath = Join-Path $PSScriptRoot $FlowFile

$jobA = Start-Job -ScriptBlock {
    param($flowPath, $device, $apiBaseUrl)
    maestro --device $device test $flowPath -e DEVICE_ROLE=a -e API_BASE_URL=$apiBaseUrl
    exit $LASTEXITCODE
} -ArgumentList $flowPath, $DeviceA, $ApiBaseUrl

$jobB = Start-Job -ScriptBlock {
    param($flowPath, $device, $apiBaseUrl)
    maestro --device $device test $flowPath -e DEVICE_ROLE=b -e API_BASE_URL=$apiBaseUrl
    exit $LASTEXITCODE
} -ArgumentList $flowPath, $DeviceB, $ApiBaseUrl

Wait-Job $jobA, $jobB | Out-Null

Receive-Job $jobA
Receive-Job $jobB

# NOTE: Start-Job's own State reports "Completed" as soon as the scriptblock
# returns, regardless of the native `maestro` exe's exit code, UNLESS the
# `exit $LASTEXITCODE` above causes PowerShell to treat it as a script
# failure. This has NOT been verified against a real Maestro binary - if
# both devices report success here even on an assertion failure, check
# $LASTEXITCODE handling first. See
# tasks/NEEDS-HUMAN-REVIEW-maestro-e2e.md item 6.
$failed = ($jobA.State -eq "Failed") -or ($jobB.State -eq "Failed")
Remove-Job $jobA, $jobB

if ($failed) {
    Write-Error "two-device flow failed (see maestro output above)"
    exit 1
}
