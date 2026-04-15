$ErrorActionPreference = "Stop"

$script:CortexRepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

function Get-CortexRepoRoot {
    return $script:CortexRepoRoot
}

function Set-CortexUvEnvironment {
    $repoRoot = Get-CortexRepoRoot
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $repoRoot ".uv-python"
    $env:UV_PROJECT_ENVIRONMENT = Join-Path $repoRoot ".venv"
}

function Get-CortexVenvBinDir {
    Set-CortexUvEnvironment
    $scriptsDir = Join-Path $env:UV_PROJECT_ENVIRONMENT "Scripts"
    if (Test-Path -LiteralPath $scriptsDir) {
        return $scriptsDir
    }
    return (Join-Path $env:UV_PROJECT_ENVIRONMENT "bin")
}

function Get-CortexVenvCommandPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    $binDir = Get-CortexVenvBinDir
    $candidates = @("$Name.exe", $Name)
    foreach ($candidate in $candidates) {
        $path = Join-Path $binDir $candidate
        if (Test-Path -LiteralPath $path) {
            return $path
        }
    }
    return (Join-Path $binDir $Name)
}

function Test-CortexVenvHealthy {
    Set-CortexUvEnvironment
    $pythonPath = Get-CortexVenvCommandPath -Name "python"
    if (-not (Test-Path -LiteralPath $pythonPath)) {
        return $false
    }

    try {
        & $pythonPath -c "import sys; print(sys.executable)" *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Invoke-CortexUv {
    param(
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$Arguments
    )

    Set-CortexUvEnvironment
    Push-Location (Get-CortexRepoRoot)
    try {
        & uv @Arguments
        return $LASTEXITCODE
    } finally {
        Pop-Location
    }
}

function Repair-CortexVenv {
    param(
        [switch]$ForceRecreate
    )

    Set-CortexUvEnvironment
    $venvRoot = $env:UV_PROJECT_ENVIRONMENT

    if ($ForceRecreate -and (Test-Path -LiteralPath $venvRoot)) {
        Remove-Item -LiteralPath $venvRoot -Recurse -Force
    }

    $syncExitCode = Invoke-CortexUv sync --all-packages --all-groups
    if ($syncExitCode -ne 0) {
        throw (
            "uv sync failed while repairing the workspace environment. " +
            "Close any Python/uv/IDE processes holding `.venv`, then rerun " +
            "`scripts/dev/repair-venv.ps1 -ForceRecreate`."
        )
    }

    if (-not (Test-CortexVenvHealthy)) {
        throw (
            "The workspace `.venv` is still unhealthy after sync. " +
            "Try `scripts/dev/repair-venv.ps1 -ForceRecreate` after closing any process " +
            "that is using `.venv`."
        )
    }
}
