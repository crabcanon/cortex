param(
    [switch]$ForceRecreate
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_uv-env.ps1")

Repair-CortexVenv -ForceRecreate:$ForceRecreate
Write-Host "[cortex] workspace environment is healthy at $env:UV_PROJECT_ENVIRONMENT"
