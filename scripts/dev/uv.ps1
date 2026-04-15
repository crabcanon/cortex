param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "_uv-env.ps1")

Set-CortexUvEnvironment
Push-Location (Get-CortexRepoRoot)
try {
    & uv @Args
    $exitCode = $LASTEXITCODE
} finally {
    Pop-Location
}

exit $exitCode
