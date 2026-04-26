param(
    [switch]$Once,
    [switch]$ForceRecreate,
    [int]$IntervalSeconds = 1,
    [switch]$SkipBrowserBootstrap,
    [switch]$NoBrowserInstall,
    [string]$EngineKeys = "crawl4ai,jina_reader,llama_parse,markitdown"
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_uv-env.ps1")

Set-CortexUvEnvironment
if (-not (Test-CortexVenvHealthy)) {
    if (Test-CortexProjectVenvActive) {
        throw (
            "The project `.venv` is currently activated in this shell and cannot be repaired in place. " +
            "Run `deactivate` (or open a fresh terminal), then rerun " +
            "`scripts/dev/repair-venv.ps1 -ForceRecreate` and `scripts/dev/run-parse-worker.ps1`."
        )
    }
    Write-Host "[cortex] `.venv` is missing or unhealthy, repairing before launching Parse Worker..."
    Repair-CortexVenv -ForceRecreate:$ForceRecreate
}

$workerPath = Get-CortexVenvCommandPath -Name "cortex-parse-worker"
if (-not (Test-Path -LiteralPath $workerPath)) {
    if (Test-CortexProjectVenvActive) {
        throw (
            "The Parse Worker entrypoint is missing from the currently activated project `.venv`. " +
            "Run `deactivate` (or open a fresh terminal), then rerun " +
            "`scripts/dev/repair-venv.ps1 -ForceRecreate` and `scripts/dev/run-parse-worker.ps1`."
        )
    }
    Write-Host "[cortex] Parse Worker entrypoint is missing, syncing workspace first..."
    Repair-CortexVenv -ForceRecreate:$ForceRecreate
    $workerPath = Get-CortexVenvCommandPath -Name "cortex-parse-worker"
}

if (-not (Test-Path -LiteralPath $workerPath)) {
    throw "Parse Worker executable was not found after repair: $workerPath"
}

if (-not $SkipBrowserBootstrap) {
    $prepExitCode = Invoke-CortexRuntimePrep -InstallIfMissing:(-not $NoBrowserInstall)
    if ($prepExitCode -ne 0) {
        exit $prepExitCode
    }
}

Push-Location (Get-CortexRepoRoot)
try {
    if ($EngineKeys) {
        $env:CORTEX_PARSE_WORKER_ENGINE_KEYS = $EngineKeys
    }
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
