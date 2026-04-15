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

function Test-CortexProjectVenvActive {
    Set-CortexUvEnvironment
    if (-not $env:VIRTUAL_ENV) {
        return $false
    }

    try {
        $activePath = [System.IO.Path]::GetFullPath($env:VIRTUAL_ENV).TrimEnd('\')
        $targetPath = [System.IO.Path]::GetFullPath($env:UV_PROJECT_ENVIRONMENT).TrimEnd('\')
        return $activePath.Equals($targetPath, [System.StringComparison]::OrdinalIgnoreCase)
    } catch {
        return $false
    }
}

function Test-CortexVenvManagedByRepo {
    Set-CortexUvEnvironment
    $configPath = Join-Path $env:UV_PROJECT_ENVIRONMENT "pyvenv.cfg"
    if (-not (Test-Path -LiteralPath $configPath)) {
        return $false
    }

    $homeLine = Get-Content -LiteralPath $configPath |
        Where-Object { $_ -match '^\s*home\s*=' } |
        Select-Object -First 1
    if (-not $homeLine) {
        return $false
    }

    $homePath = ($homeLine -split '=', 2)[1].Trim()
    if (-not $homePath) {
        return $false
    }

    try {
        $actualRoot = [System.IO.Path]::GetFullPath($homePath)
        $expectedRoot = [System.IO.Path]::GetFullPath($env:UV_PYTHON_INSTALL_DIR).TrimEnd('\')
        return $actualRoot.StartsWith($expectedRoot, [System.StringComparison]::OrdinalIgnoreCase)
    } catch {
        return $false
    }
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
    if (-not (Test-CortexVenvManagedByRepo)) {
        return $false
    }

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

    if (Test-CortexProjectVenvActive) {
        throw (
            "The target workspace `.venv` is currently activated in this shell. " +
            "Run `deactivate` (or open a fresh terminal) before repairing it, " +
            "then rerun `scripts/dev/repair-venv.ps1 -ForceRecreate`."
        )
    }

    if ($ForceRecreate -and (Test-Path -LiteralPath $venvRoot)) {
        try {
            Remove-Item -LiteralPath $venvRoot -Recurse -Force
        } catch {
            throw (
                "Failed to recreate the workspace `.venv` because a running `cortex-api` / worker / Python / uv " +
                "process is still using it. Stop those processes first, then rerun " +
                "`scripts/dev/repair-venv.ps1 -ForceRecreate`."
            )
        }
    }

    $syncExitCode = Invoke-CortexUv sync --all-packages --all-groups
    if ($syncExitCode -ne 0) {
        throw (
            "uv sync failed while repairing the workspace environment. " +
            "Stop any running `cortex-api` / worker / Python / uv process that is still using `.venv`, " +
            "then rerun " +
            "`scripts/dev/repair-venv.ps1 -ForceRecreate`."
        )
    }

    if (-not (Test-CortexVenvHealthy)) {
        throw (
            "The workspace `.venv` is still unhealthy after sync. " +
            "Try `scripts/dev/repair-venv.ps1 -ForceRecreate` after stopping any " +
            "`cortex-api` / worker / Python / uv process that is using `.venv`."
        )
    }
}
