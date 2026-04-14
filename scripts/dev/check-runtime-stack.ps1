param(
    [string]$PytestPath = ".\.venv\Scripts\pytest.exe"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$env:CORTEX_RUNTIME_STACK = "1"

& $PytestPath "tests/integration/test_runtime_stack.py"
