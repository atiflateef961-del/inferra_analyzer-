
param(
    [ValidateSet("Local", "Network")]
    [string]$Mode = "Local",
    [switch]$OpenBrowser
)

$ErrorActionPreference = "Stop"
$frontendRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
Push-Location $frontendRoot

$port = 3000
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
$selectedUrl = if ($Mode -eq "Network" -and $networkAddress) { $networkUrl } else { $localUrl }
$env:FRONTEND_NETWORK_ADDRESS = $networkAddress
$backendPort = 8000
$backendHost = if ($Mode -eq "Network") { "0.0.0.0" } else { "127.0.0.1" }
$backendUrl = if ($Mode -eq "Network" -and $networkAddress) { "http://$networkAddress`:$backendPort" } else { "http://127.0.0.1`:$backendPort" }
$env:BACKEND_URL = $backendUrl
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

function Test-TcpPort {
    param(
        [string]$Target = "127.0.0.1",
        [int]$Port,
        [int]$TimeoutMs = 700
    )

    $client = $null
    try {
        $client = New-Object System.Net.Sockets.TcpClient
        $async = $client.BeginConnect($Target, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        if ($client) {
            $client.Close()
        }
    }
}

function Wait-ForEndpoint {
    param(
        [string]$Uri,
        [int]$TimeoutSeconds = 90,
        [int]$RequestTimeoutSeconds = 3,
        [int]$Port = 0
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    do {
        if ($Port -gt 0 -and -not (Test-TcpPort -Port $Port)) {
            Start-Sleep -Milliseconds 300
            continue
        }

        try {
            if ($curl) {
                $statusCode = & curl.exe -sS -o NUL -w "%{http_code}" --max-time $RequestTimeoutSeconds --connect-timeout 2 $Uri 2>$null
                if ($statusCode -match "^\d+$") {
                    $code = [int]$statusCode
                    if ($code -ge 200 -and $code -lt 500) {
                        return $true
                    }
                }
            } else {
                $response = Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec $RequestTimeoutSeconds -ErrorAction Stop
                if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                    return $true
                }
            }
        } catch {
        }

        Start-Sleep -Milliseconds 300
    } while ((Get-Date) -lt $deadline)

    return $false
}

function Open-SelectedBrowser {
    param([string]$Url)

    Write-Host "Opening browser automatically: $Url"
    $chromeCandidates = @(
        (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
        (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
    )
    foreach ($chrome in $chromeCandidates) {
        if ($chrome -and (Test-Path $chrome)) {
            Start-Process -FilePath $chrome -ArgumentList @("--new-window", $Url)
            return
        }
    }

    try {
        Start-Process "chrome.exe" -ArgumentList @("--new-window", $Url)
        return
    } catch {
    }

    Start-Process $Url
}

function Stop-PortListeners {
    param([int]$Port)

    foreach ($processId in (Get-ListeningPids -Port $Port)) {
        try {
            & taskkill.exe /PID $processId /T /F *> $null
        } catch {
        }
    }
    $deadline = (Get-Date).AddSeconds(8)
    while ((Get-Date) -lt $deadline -and (Get-ListeningPids -Port $Port).Count -gt 0) {
        Start-Sleep -Milliseconds 200
    }
}

function Test-BackendWorkspace {
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        $healthCode = & curl.exe -sS -o NUL -w "%{http_code}" --max-time 3 --connect-timeout 2 "http://127.0.0.1:$backendPort/api/health" 2>$null
        $docsCode = & curl.exe -sS -o NUL -w "%{http_code}" --max-time 3 --connect-timeout 2 "http://127.0.0.1:$backendPort/api/documents" 2>$null
        return ($healthCode -eq "200" -and $docsCode -eq "200")
    }
    try {
        $health = Invoke-WebRequest -Uri "http://127.0.0.1:$backendPort/api/health" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        $docs = Invoke-WebRequest -Uri "http://127.0.0.1:$backendPort/api/documents" -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        return ($health.StatusCode -eq 200 -and $docs.StatusCode -eq 200)
    } catch {
        return $false
    }
}

if ((Get-ListeningPids -Port $backendPort).Count -gt 0 -and -not (Test-BackendWorkspace)) {
    Write-Host "Stopping stale backend on port $backendPort so document, analytics, and agent routes can start..."
    Stop-PortListeners -Port $backendPort
}

if (-not (Test-TcpPort -Port $backendPort) -or -not (Test-BackendWorkspace)) {
    $backendRoot = Join-Path $PSScriptRoot "..\..\backend"
    $backendLauncher = Join-Path $backendRoot "scripts\dev.ps1"
    if (Test-Path $backendLauncher) {
        Write-Host "Starting backend with the project launcher..."
        Start-Process -FilePath "powershell.exe" -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            $backendLauncher,
            "-Mode",
            $Mode
        ) -WorkingDirectory $backendRoot -WindowStyle Hidden
    } else {
        Write-Warning "Backend launcher was not found at $backendLauncher. Start FastAPI manually on port 8000."
    }
}

$backendReady = Wait-ForEndpoint "http://127.0.0.1`:$backendPort/api/health" -TimeoutSeconds 25 -RequestTimeoutSeconds 3 -Port $backendPort
if (-not $backendReady -or -not (Test-BackendWorkspace)) {
    Write-Warning "Backend did not become ready with document routes. The frontend will still start, but API requests may fail until FastAPI is healthy."
}

if ((Get-ListeningPids -Port $port).Count -gt 0) {
    $healthy = $false
    try {
        $health = Invoke-WebRequest -Uri $localUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        $healthy = $health.StatusCode -ge 200 -and $health.StatusCode -lt 500
    } catch {
        $healthy = $false
    }

    if ($healthy) {
        Write-Host "Next.js is already running."
        Write-Host "- Local:   $localUrl"
        Write-Host "- Network: $networkUrl"
        Write-Host "- Selected: $selectedUrl"
        if ($OpenBrowser) {
            Open-SelectedBrowser $selectedUrl
        }
        exit 0
    }

    Write-Host "Stopping stale process on port $port..."
    Stop-PortListeners -Port $port
}

Write-Output "Next.js starting in $Mode mode..."
Write-Output "- Browser URL: $selectedUrl"
Write-Output "- Local:       $localUrl"
Write-Output "- Internal bind: $hostname`:$port (not a browser URL)"
Write-Output "- One server:  yes"

$node = (Get-Command node -ErrorAction Stop).Source
$nextBin = Join-Path $frontendRoot "node_modules\next\dist\bin\next"
if (-not (Test-Path $nextBin)) {
    throw "Next.js is not installed. Run npm install in the frontend folder."
}
$nextArguments = @($nextBin, "dev", "--hostname", $hostname, "--port", "$port")
$nextArguments[0] = '"' + $nextArguments[0] + '"'

$nextProcess = Start-Process -FilePath $node -ArgumentList $nextArguments -WorkingDirectory $frontendRoot -NoNewWindow -PassThru
$frontendReady = Wait-ForEndpoint "http://127.0.0.1`:$port" -TimeoutSeconds 120 -RequestTimeoutSeconds 3 -Port $port
if ($frontendReady) {
    if ($OpenBrowser) {
        Open-SelectedBrowser $selectedUrl
    }
} else {
    Write-Warning "Frontend did not become ready within 120 seconds. Chrome was not opened."
}
if ($nextProcess -and -not $nextProcess.HasExited) {
    Wait-Process -Id $nextProcess.Id
}
$exitCode = $nextProcess.ExitCode
Pop-Location
exit $exitCode
