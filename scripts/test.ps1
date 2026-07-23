#Requires -Version 7
<#
.SYNOPSIS
    Run DrinkingBuddy backend test suite.

.PARAMETER Suite
    unit (default) | integration | all

.PARAMETER K
    pytest -k filter expression.

.EXAMPLE
    ./scripts/test.ps1
    ./scripts/test.ps1 -Suite integration
    ./scripts/test.ps1 -Suite all -K health
#>
param(
    [ValidateSet("unit", "integration", "all")]
    [string]$Suite = "unit",
    [string]$K,
    [switch]$VerboseOutput
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"

Push-Location $backendDir
try {
    $pytestArgs = @()

    switch ($Suite) {
        "unit" { $pytestArgs += "tests/unit/" }
        "integration" {
            $pytestArgs += "tests/integration/"
            $pytestArgs += "-m"
            $pytestArgs += "integration"
        }
        "all" { $pytestArgs += "tests/" }
    }

    if ($K) {
        $pytestArgs += "-k"
        $pytestArgs += $K
    }

    if ($VerboseOutput) {
        $pytestArgs += "-v"
    }

    if ($Suite -in @("integration", "all")) {
        docker info *>$null
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Docker daemon not running. Integration tests need testcontainers."
            exit 1
        }
    }

    uv run pytest @pytestArgs
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
