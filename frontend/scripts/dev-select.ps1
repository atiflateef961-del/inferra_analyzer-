$ErrorActionPreference = "Stop"

$networkAddress = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -and
        $_.IPAddress -ne "0.0.0.0" -and
        $_.IPAddress -notlike "127.*" -and
        $_.IPAddress -notlike "169.254.*" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -First 1 -ExpandProperty IPAddress
$networkUrl = if ($networkAddress) { "http://$networkAddress`:3000" } else { "unavailable" }

Write-Host "Select frontend access mode:"
Write-Host "[1] Local only      http://localhost:3000"
Write-Host "[2] Network access  $networkUrl"
Write-Host "Note: Next.js runs as one process. The browser URL is chosen by the selected mode."

$choice = Read-Host "Enter 1 or 2"
$mode = switch ($choice.Trim()) {
    "1" { "Local" }
    "2" { "Network" }
    default { Write-Error "Invalid choice. Enter 1 for Local or 2 for Network."; exit 1 }
}

& (Join-Path $PSScriptRoot "dev.ps1") -Mode $mode -OpenBrowser
exit $LASTEXITCODE