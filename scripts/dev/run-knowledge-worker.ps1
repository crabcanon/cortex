param(
    [switch]$Once,
    [switch]$ForceRecreate,
    [int]$IntervalSeconds = 1
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_uv-env.ps1")

Set-CortexUvEnvironment
if (-not (Test-CortexVenvHealthy)) {
    Write-Host "[cortex] `.venv` is missing or unhealthy, repairing before launching Knowledge Worker..."
    Repair-CortexVenv -ForceRecreate:$ForceRecreate
}

$workerPath = Get-CortexVenvCommandPath -Name "cortex-knowledge-worker"
if (-not (Test-Path -LiteralPath $workerPath)) {
    Write-Host "[cortex] Knowledge Worker entrypoint is missing, syncing workspace first..."
    Repair-CortexVenv -ForceRecreate:$ForceRecreate
    $workerPath = Get-CortexVenvCommandPath -Name "cortex-knowledge-worker"
}

if (-not (Test-Path -LiteralPath $workerPath)) {
    throw "Knowledge Worker executable was not found after repair: $workerPath"
}

Push-Location (Get-CortexRepoRoot)
try {
    if ($Once) {
        & $workerPath
        exit $LASTEXITCODE
    }

    while ($true) {
        & $workerPath
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
        Start-Sleep -Seconds $IntervalSeconds
    }
} finally {
    Pop-Location
}
