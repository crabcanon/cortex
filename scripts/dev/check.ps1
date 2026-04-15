$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true
$env:UV_PYTHON_INSTALL_DIR = (Join-Path $PSScriptRoot "..\\..\\.uv-python")

function Invoke-UvCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    & uv @Args
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
}

Write-Host "[cortex] validating YAML and OpenAPI assets..."
Invoke-UvCheck @("run", "--all-packages", "--all-groups", "python", "scripts/ci/validate_yaml.py")

Write-Host "[cortex] running Ruff..."
Invoke-UvCheck @("run", "--all-packages", "--group", "lint", "ruff", "check", ".")

Write-Host "[cortex] running Pyright..."
Invoke-UvCheck @("run", "--all-packages", "--group", "types", "pyright")

Write-Host "[cortex] running pytest..."
Invoke-UvCheck @("run", "--all-packages", "--group", "test", "pytest")

Write-Host "[cortex] checks complete."
