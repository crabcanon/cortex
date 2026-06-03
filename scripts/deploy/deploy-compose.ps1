param(
    [string] $EnvFile = ".env.prod",
    [string] $Project = "cortex-prod",
    [switch] $Heavy,
    [switch] $Pull,
    [switch] $NoMigrate,
    [string] $HealthUrl = "http://127.0.0.1:8080/v1/health/live",
    [int] $TimeoutSeconds = 180
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    throw "Env file not found: $EnvFile. Copy .env.prod.example and fill production values first."
}

$compose = @("--env-file", $EnvFile, "-p", $Project, "-f", "compose.prod.yaml")
$profiles = @()
if ($Heavy) {
    $profiles += @("--profile", "docling", "--profile", "eval-runtime", "--profile", "synthesis-runtime")
}

Write-Host "[cortex] Validating production Compose config..."
& docker compose @compose @profiles config --quiet
if ($LASTEXITCODE -ne 0) {
    throw "docker compose config failed."
}

if ($Pull) {
    Write-Host "[cortex] Pulling images..."
    & docker compose @compose @profiles pull
    if ($LASTEXITCODE -ne 0) {
        throw "docker compose pull failed."
    }
}

if (-not $NoMigrate) {
    Write-Host "[cortex] Running database migration..."
    & docker compose @compose --profile migrate run --rm cortex-migrate
    if ($LASTEXITCODE -ne 0) {
        throw "cortex database migration failed."
    }
}

Write-Host "[cortex] Starting production services..."
& docker compose @compose @profiles up -d
if ($LASTEXITCODE -ne 0) {
    throw "docker compose up failed."
}

if ($HealthUrl) {
    Write-Host "[cortex] Waiting for health endpoint: $HealthUrl"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            $response = Invoke-WebRequest -UseBasicParsing -Uri $HealthUrl -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 300) {
                Write-Host "[cortex] API health check passed."
                & docker compose @compose @profiles ps
                exit 0
            }
        } catch {
            Start-Sleep -Seconds 3
        }
    } while ((Get-Date) -lt $deadline)

    & docker compose @compose @profiles ps
    throw "Timed out waiting for Cortex API health endpoint: $HealthUrl"
}

& docker compose @compose @profiles ps
