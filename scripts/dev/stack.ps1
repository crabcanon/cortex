param(
    [ValidateSet("up", "down", "ps", "logs", "restart", "build")]
    [string]$Action = "up",
    [string[]]$Services = @(),
    [Alias("Profile")]
    [string[]]$ComposeProfile = @(),
    [switch]$Heavy,
    [switch]$Follow,
    [switch]$NoWait,
    [switch]$Build
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$RepoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ComposeArgs = @(
    "compose",
    "-p",
    "cortex-local",
    "-f",
    (Join-Path $RepoRoot "compose.local.yaml")
)

$ActiveProfiles = @($ComposeProfile)
if ($Heavy) {
    $ActiveProfiles += @("docling", "eval-runtime", "synthesis-runtime")
}
$ActiveProfiles = @($ActiveProfiles | Where-Object { $_ } | Select-Object -Unique)
foreach ($ActiveProfile in $ActiveProfiles) {
    $ComposeArgs += @("--profile", $ActiveProfile)
}

if ($Heavy -and $Action -eq "up" -and $Services.Count -eq 0) {
    $Services = @(
        "postgres",
        "minio",
        "redis",
        "jaeger-all-in-one",
        "otel-collector",
        "prometheus",
        "grafana",
        "cortex-migrate",
        "cortex-api",
        "cortex-parse-worker",
        "cortex-parse-worker-docling",
        "cortex-knowledge-worker",
        "cortex-evaluation-worker-runtime",
        "cortex-synthesis-worker-runtime"
    )
}

function Test-ServiceRequested {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name
    )

    if ($Services.Count -eq 0) {
        return $true
    }

    return $Services -contains $Name
}

function Wait-HttpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Uri,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "Timed out waiting for HTTP endpoint: $Uri"
}

function Wait-TcpReady {
    param(
        [Parameter(Mandatory = $true)]
        [string]$HostName,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $client = [System.Net.Sockets.TcpClient]::new()
        try {
            $async = $client.ConnectAsync($HostName, $Port)
            if ($async.Wait(3000) -and $client.Connected) {
                return
            }
        } catch {
            Start-Sleep -Seconds 2
        } finally {
            $client.Dispose()
        }
        Start-Sleep -Seconds 1
    }

    throw "Timed out waiting for TCP endpoint: ${HostName}:${Port}"
}

switch ($Action) {
    "up" {
        $upArgs = @($ComposeArgs + @("up", "-d"))
        if ($Build) {
            $upArgs += "--build"
        }
        $upArgs += $Services
        & docker @upArgs
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
        if (-not $NoWait) {
            if (Test-ServiceRequested "postgres") {
                Wait-TcpReady -HostName "127.0.0.1" -Port 5432
            }
            if (Test-ServiceRequested "minio") {
                Wait-HttpReady -Uri "http://127.0.0.1:9000/minio/health/ready"
            }
            if (Test-ServiceRequested "redis") {
                Wait-TcpReady -HostName "127.0.0.1" -Port 6379
            }
            if (Test-ServiceRequested "otel-collector") {
                Wait-HttpReady -Uri "http://127.0.0.1:13133/"
            }
            if (Test-ServiceRequested "jaeger-all-in-one") {
                Wait-HttpReady -Uri "http://127.0.0.1:16686/"
            }
            if (Test-ServiceRequested "prometheus") {
                Wait-HttpReady -Uri "http://127.0.0.1:9090/-/ready"
            }
            if (Test-ServiceRequested "grafana") {
                Wait-HttpReady -Uri "http://127.0.0.1:3000/api/health"
            }
            if (Test-ServiceRequested "cortex-api") {
                Wait-HttpReady -Uri "http://127.0.0.1:8080/v1/health/live" -TimeoutSeconds 180
            }
        }
    }
    "down" {
        & docker @ComposeArgs down --remove-orphans
        exit $LASTEXITCODE
    }
    "ps" {
        & docker @ComposeArgs ps
        exit $LASTEXITCODE
    }
    "logs" {
        if ($Follow) {
            & docker @ComposeArgs logs -f @Services
        } else {
            & docker @ComposeArgs logs @Services
        }
        exit $LASTEXITCODE
    }
    "build" {
        $buildArgs = @($ComposeArgs + @("build"))
        $buildArgs += $Services
        & docker @buildArgs
        exit $LASTEXITCODE
    }
    "restart" {
        & docker @ComposeArgs restart @Services
        if ($LASTEXITCODE -ne 0) {
            exit $LASTEXITCODE
        }
        if (-not $NoWait) {
            if (Test-ServiceRequested "postgres") {
                Wait-TcpReady -HostName "127.0.0.1" -Port 5432
            }
            if (Test-ServiceRequested "minio") {
                Wait-HttpReady -Uri "http://127.0.0.1:9000/minio/health/ready"
            }
            if (Test-ServiceRequested "redis") {
                Wait-TcpReady -HostName "127.0.0.1" -Port 6379
            }
            if (Test-ServiceRequested "otel-collector") {
                Wait-HttpReady -Uri "http://127.0.0.1:13133/"
            }
            if (Test-ServiceRequested "jaeger-all-in-one") {
                Wait-HttpReady -Uri "http://127.0.0.1:16686/"
            }
            if (Test-ServiceRequested "prometheus") {
                Wait-HttpReady -Uri "http://127.0.0.1:9090/-/ready"
            }
            if (Test-ServiceRequested "grafana") {
                Wait-HttpReady -Uri "http://127.0.0.1:3000/api/health"
            }
            if (Test-ServiceRequested "cortex-api") {
                Wait-HttpReady -Uri "http://127.0.0.1:8080/v1/health/live" -TimeoutSeconds 180
            }
        }
    }
}
