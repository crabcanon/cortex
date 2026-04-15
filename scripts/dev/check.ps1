$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

. (Join-Path $PSScriptRoot "_uv-env.ps1")
Set-CortexUvEnvironment

function Invoke-UvCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Args
    )

    $exitCode = Invoke-CortexUv @Args
    if ($exitCode -ne 0) {
        exit $exitCode
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
