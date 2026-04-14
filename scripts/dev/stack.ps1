param(
    [ValidateSet("up", "down", "ps", "logs", "restart")]
    [string]$Action = "up",
    [string[]]$Services = @(),
    [switch]$Follow,
    [switch]$NoWait
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
        [string]$Host,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$TimeoutSeconds = 90
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $client = [System.Net.Sockets.TcpClient]::new()
        try {
            $async = $client.ConnectAsync($Host, $Port)
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

    throw "Timed out waiting for TCP endpoint: ${Host}:${Port}"
}

switch ($Action) {
    "up" {
        & docker @ComposeArgs up -d @Services
        if (-not $NoWait) {
            Wait-TcpReady -Host "127.0.0.1" -Port 5432
            Wait-HttpReady -Uri "http://127.0.0.1:9000/minio/health/ready"
            Wait-TcpReady -Host "127.0.0.1" -Port 6379
            Wait-HttpReady -Uri "http://127.0.0.1:13133/"
            Wait-HttpReady -Uri "http://127.0.0.1:16686/"
            Wait-HttpReady -Uri "http://127.0.0.1:9090/-/ready"
            Wait-HttpReady -Uri "http://127.0.0.1:3000/api/health"
        }
    }
    "down" {
        & docker @ComposeArgs down --remove-orphans
    }
    "ps" {
        & docker @ComposeArgs ps
    }
    "logs" {
        if ($Follow) {
            & docker @ComposeArgs logs -f @Services
        } else {
            & docker @ComposeArgs logs @Services
        }
    }
    "restart" {
        & docker @ComposeArgs restart @Services
        if (-not $NoWait) {
            Wait-TcpReady -Host "127.0.0.1" -Port 5432
            Wait-HttpReady -Uri "http://127.0.0.1:9000/minio/health/ready"
            Wait-TcpReady -Host "127.0.0.1" -Port 6379
            Wait-HttpReady -Uri "http://127.0.0.1:13133/"
            Wait-HttpReady -Uri "http://127.0.0.1:16686/"
            Wait-HttpReady -Uri "http://127.0.0.1:9090/-/ready"
            Wait-HttpReady -Uri "http://127.0.0.1:3000/api/health"
        }
    }
}
