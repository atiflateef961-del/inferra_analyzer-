param(
    [Parameter(Mandatory = $true)]
    [string]$Url,
    [int]$TimeoutSeconds = 180
)

function Open-SelectedBrowser {
    param([string]$TargetUrl)

    $chromeCandidates = @(
        (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
        (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
        (Join-Path $env:LOCALAPPDATA "Google\Chrome\Application\chrome.exe")
    )
    foreach ($chrome in $chromeCandidates) {
        if ($chrome -and (Test-Path $chrome)) {
            Start-Process -FilePath $chrome -ArgumentList $TargetUrl
            return
        }
    }

    try {
        Start-Process "chrome.exe" $TargetUrl
        return
    } catch {
    }

    Start-Process $TargetUrl
}

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
$curl = Get-Command curl.exe -ErrorAction SilentlyContinue
do {
    try {
        if ($curl) {
            $statusCode = & curl.exe -sS -o NUL -w "%{http_code}" --max-time 3 --connect-timeout 2 $Url 2>$null
            if ($statusCode -match "^\d+$") {
                $code = [int]$statusCode
                if ($code -ge 200 -and $code -lt 500) {
                    Open-SelectedBrowser $Url
                    exit 0
                }
            }
        } else {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Open-SelectedBrowser $Url
                exit 0
            }
        }
    } catch {
    }
    Start-Sleep -Milliseconds 400
} while ((Get-Date) -lt $deadline)

Write-Warning "Frontend did not become ready within $TimeoutSeconds seconds. Chrome was not opened. Open $Url after Next.js finishes compiling."
exit 1
