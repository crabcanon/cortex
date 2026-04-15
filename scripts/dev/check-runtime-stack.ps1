param(
    [switch]$ForceRecreate
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

. (Join-Path $PSScriptRoot "_uv-env.ps1")
Set-CortexUvEnvironment

if (-not (Test-CortexVenvHealthy)) {
    Write-Host "[cortex] `.venv` is missing or unhealthy, repairing before runtime-stack checks..."
    Repair-CortexVenv -ForceRecreate:$ForceRecreate
}

$PytestPath = Get-CortexVenvCommandPath -Name "pytest"
$env:CORTEX_RUNTIME_STACK = "1"

& $PytestPath "tests/integration/test_runtime_stack.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
& $PytestPath "tests/integration/test_runtime_observability_stack.py"
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
