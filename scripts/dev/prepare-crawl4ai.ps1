param(
    [switch]$ForceRecreate,
    [switch]$NoProbe,
    [switch]$InstallIfMissing,
    [switch]$WithDeps
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_uv-env.ps1")

Set-CortexUvEnvironment
if (-not (Test-CortexVenvHealthy)) {
    if (Test-CortexProjectVenvActive) {
        throw (
            "The project `.venv` is currently activated in this shell and cannot be repaired in place. " +
            "Run `deactivate` (or open a fresh terminal), then rerun " +
            "`scripts/dev/repair-venv.ps1 -ForceRecreate` and `scripts/dev/prepare-crawl4ai.ps1`."
        )
    }
    Write-Host "[cortex] `.venv` is missing or unhealthy, repairing before preparing Crawl4AI..."
    Repair-CortexVenv -ForceRecreate:$ForceRecreate
}

$exitCode = Invoke-CortexRuntimePrep `
    -InstallIfMissing:$InstallIfMissing `
    -WithDeps:$WithDeps `
    -NoProbe:$NoProbe
exit $exitCode
