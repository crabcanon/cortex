param(
    [switch]$ForceRecreate,
    [switch]$SkipBrowserBootstrap,
    [switch]$NoBrowserInstall
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_uv-env.ps1")

Set-CortexUvEnvironment
if (-not (Test-CortexVenvHealthy)) {
    if (Test-CortexProjectVenvActive) {
        throw (
            "The project `.venv` is currently activated in this shell and cannot be repaired in place. " +
            "Run `deactivate` (or open a fresh terminal), then rerun " +
            "`scripts/dev/repair-venv.ps1 -ForceRecreate` and `scripts/dev/run-api.ps1`."
        )
    }
    Write-Host "[cortex] `.venv` is missing or unhealthy, repairing before launching API..."
    Repair-CortexVenv -ForceRecreate:$ForceRecreate
}

$apiPath = Get-CortexVenvCommandPath -Name "cortex-api"
if (-not (Test-Path -LiteralPath $apiPath)) {
    if (Test-CortexProjectVenvActive) {
        throw (
            "The API entrypoint is missing from the currently activated project `.venv`. " +
            "Run `deactivate` (or open a fresh terminal), then rerun " +
            "`scripts/dev/repair-venv.ps1 -ForceRecreate` and `scripts/dev/run-api.ps1`."
        )
    }
    Write-Host "[cortex] API entrypoint is missing, syncing workspace first..."
    Repair-CortexVenv -ForceRecreate:$ForceRecreate
    $apiPath = Get-CortexVenvCommandPath -Name "cortex-api"
}

if (-not (Test-Path -LiteralPath $apiPath)) {
    throw "API executable was not found after repair: $apiPath"
}

if (-not $SkipBrowserBootstrap) {
    $prepExitCode = Invoke-CortexRuntimePrep -InstallIfMissing:(-not $NoBrowserInstall)
    if ($prepExitCode -ne 0) {
        exit $prepExitCode
    }
}

Push-Location (Get-CortexRepoRoot)
try {
    & $apiPath
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
