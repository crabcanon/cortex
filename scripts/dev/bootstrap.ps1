$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_uv-env.ps1")
Set-CortexUvEnvironment

Write-Host "[cortex] syncing workspace dependencies..."
$syncExitCode = Invoke-CortexUv sync --all-packages --all-groups
if ($syncExitCode -ne 0) {
    exit $syncExitCode
}

Write-Host "[cortex] workspace bootstrap complete."
