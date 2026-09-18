param(
    [ValidateSet("Local", "Network")]
    [string]$Mode = "Local"
)

$ErrorActionPreference = "Stop"
$backendRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
Push-Location $backendRoot

$port = 8000
$localUrl = "http://localhost:$port"
$networkAddress = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -and
        $_.IPAddress -ne "0.0.0.0" -and
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -First 1 -ExpandProperty IPAddress
$networkUrl = if ($networkAddress) { "http://$networkAddress`:$port" } else { "unavailable" }
$hostname = if ($Mode -eq "Network") { "0.0.0.0" } else { "127.0.0.1" }
$corsOrigins = @("http://localhost:3000", "http://127.0.0.1:3000")
if ($networkAddress) {
    $corsOrigins += "http://$networkAddress`:3000"
}
$env:CORS_ORIGINS = $corsOrigins -join ","

function Get-ListeningPids {
    param([int]$Port)

    $pattern = "[:.]$Port\s+\S+\s+LISTENING\s+(\d+)"
    $pids = @()
    foreach ($line in (& netstat.exe -ano)) {
        if ($line -match $pattern) {
            $pids += [int]$Matches[1]
        }
    }
    return @($pids | Select-Object -Unique)
}

function Test-BackendWorkspace {
    try {
        $health = Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $docs = Invoke-WebRequest -Uri "http://127.0.0.1:$port/api/documents" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        return ($health.StatusCode -eq 200 -and $docs.StatusCode -eq 200)
    } catch {
        return $false
    }
}

$listeners = @(Get-ListeningPids -Port $port)
if ($listeners.Count -gt 0) {
    if (Test-BackendWorkspace) {
        Write-Host "FastAPI is already running with workspace routes."
        Write-Host "- Local:   $localUrl"
        Write-Host "- Network: $networkUrl"
        exit 0
    }

    Write-Host "Port $port is occupied by a stale or incomplete backend. Restarting it..."
    foreach ($processId in $listeners) {
        try {
            & taskkill.exe /PID $processId /T /F *> $null
        } catch {
        }
    }
    Start-Sleep -Seconds 1
}

Write-Output "FastAPI starting in $Mode mode..."
Write-Output "- Local:   $localUrl"
Write-Output "- Network: $networkUrl"

$backendPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
& $backendPython -m uvicorn app.main:app --host $hostname --port $port
$exitCode = $LASTEXITCODE
Pop-Location
exit $exitCode
