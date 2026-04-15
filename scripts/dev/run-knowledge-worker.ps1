param(
    [switch]$Once,
    [switch]$ForceRecreate,
    [int]$IntervalSeconds = 1
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_uv-env.ps1")

Set-CortexUvEnvironment
if (-not (Test-CortexVenvHealthy)) {
    if (Test-CortexProjectVenvActive) {
        throw (
            "The project `.venv` is currently activated in this shell and cannot be repaired in place. " +
            "Run `deactivate` (or open a fresh terminal), then rerun " +
            "`scripts/dev/repair-venv.ps1 -ForceRecreate` and `scripts/dev/run-knowledge-worker.ps1`."
        )
    }
    Write-Host "[cortex] `.venv` is missing or unhealthy, repairing before launching Knowledge Worker..."
    Repair-CortexVenv -ForceRecreate:$ForceRecreate
}

$workerPath = Get-CortexVenvCommandPath -Name "cortex-knowledge-worker"
if (-not (Test-Path -LiteralPath $workerPath)) {
    if (Test-CortexProjectVenvActive) {
        throw (
            "The Knowledge Worker entrypoint is missing from the currently activated project `.venv`. " +
            "Run `deactivate` (or open a fresh terminal), then rerun " +
            "`scripts/dev/repair-venv.ps1 -ForceRecreate` and `scripts/dev/run-knowledge-worker.ps1`."
        )
    }
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
