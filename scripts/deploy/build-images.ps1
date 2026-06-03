param(
    [string] $Registry = "ghcr.io",
    [string] $Namespace = "crabcanon",
    [string] $Tag = "",
    [string] $Platform = "linux/amd64",
    [string] $RuntimeConfigPath = "configs/cortex.runtime.prod.yaml",
    [switch] $Heavy,
    [switch] $Push,
    [switch] $NoLatest
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-DefaultTag {
    $sha = (& git rev-parse --short HEAD 2>$null)
    if ($LASTEXITCODE -eq 0 -and $sha) {
        return $sha.Trim()
    }
    return (Get-Date -Format "yyyyMMddHHmmss")
}

function Add-OptionalBuildArg {
    param(
        [System.Collections.Generic.List[string]] $Args,
        [string] $Name,
        [string] $Value
    )

    if ($Value) {
        $Args.Add("--build-arg")
        $Args.Add("${Name}=${Value}")
    }
}

if (-not $Tag) {
    $Tag = Get-DefaultTag
}

$targets = @(
    @{ Target = "api"; Image = "cortex-api"; Heavy = $false },
    @{ Target = "parse-worker"; Image = "cortex-parse-worker"; Heavy = $false },
    @{ Target = "knowledge-worker"; Image = "cortex-knowledge-worker"; Heavy = $false },
    @{ Target = "evaluation-worker"; Image = "cortex-evaluation-worker"; Heavy = $false },
    @{ Target = "synthesis-worker"; Image = "cortex-synthesis-worker"; Heavy = $false },
    @{ Target = "parse-worker-docling"; Image = "cortex-parse-worker-docling"; Heavy = $true },
    @{ Target = "evaluation-worker-runtime"; Image = "cortex-evaluation-worker-runtime"; Heavy = $true },
    @{ Target = "synthesis-worker-runtime"; Image = "cortex-synthesis-worker-runtime"; Heavy = $true }
)

$selectedTargets = $targets | Where-Object { -not $_.Heavy -or $Heavy }

Write-Host "[cortex] Building $($selectedTargets.Count) image(s) for ${Registry}/${Namespace}:$Tag"
Write-Host "[cortex] Runtime config path: $RuntimeConfigPath"
if (-not $Heavy) {
    Write-Host "[cortex] Heavy images are skipped. Pass -Heavy to include Docling, Eval runtime, and Synthesis runtime images."
}

foreach ($item in $selectedTargets) {
    $image = "${Registry}/${Namespace}/$($item.Image):${Tag}"
    $latest = "${Registry}/${Namespace}/$($item.Image):latest"
    $args = [System.Collections.Generic.List[string]]::new()
    $args.Add("buildx")
    $args.Add("build")
    $args.Add("--platform")
    $args.Add($Platform)
    $args.Add("--target")
    $args.Add($item.Target)
    $args.Add("--build-arg")
    $args.Add("CORTEX_RUNTIME_CONFIG_PATH=${RuntimeConfigPath}")
    $args.Add("--build-arg")
    $args.Add("CORTEX_PREPARE_CRAWL4AI_RUNTIME=1")
    Add-OptionalBuildArg -Args $args -Name "PYTHON_BASE_IMAGE" -Value $env:CORTEX_PYTHON_BASE_IMAGE
    Add-OptionalBuildArg -Args $args -Name "PLAYWRIGHT_PYTHON_BASE_IMAGE" -Value $env:CORTEX_PLAYWRIGHT_PYTHON_BASE_IMAGE
    Add-OptionalBuildArg -Args $args -Name "UV_IMAGE" -Value $env:CORTEX_UV_IMAGE
    $args.Add("-t")
    $args.Add($image)
    if (-not $NoLatest) {
        $args.Add("-t")
        $args.Add($latest)
    }
    if ($Push) {
        $args.Add("--push")
    } else {
        $args.Add("--load")
    }
    $args.Add(".")

    Write-Host "[cortex] Building target $($item.Target) -> $image"
    & docker @args
    if ($LASTEXITCODE -ne 0) {
        throw "Docker build failed for target $($item.Target)"
    }
}

Write-Host "[cortex] Image build completed."
