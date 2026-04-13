$ErrorActionPreference = "Stop"
$env:UV_PYTHON_INSTALL_DIR = (Join-Path $PSScriptRoot "..\\..\\.uv-python")

Write-Host "[cortex] syncing workspace dependencies..."
uv sync --all-packages

Write-Host "[cortex] workspace bootstrap complete."
