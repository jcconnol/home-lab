[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$logDirectory = Join-Path $projectRoot "logs"

New-Item -ItemType Directory -Force -Path $logDirectory | Out-Null

function Test-ListeningPort {
    param([int]$Port)

    return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Start-GraceServer {
    param(
        [int]$Port,
        [string]$Name
    )

    if (Test-ListeningPort -Port $Port) {
        return
    }

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path (Join-Path $logDirectory "watchdog.log") -Value "$timestamp Starting $Name on port $Port."
    $runnerPath = Join-Path $PSScriptRoot "run-$Name.cmd"
    $processInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $processInfo.FileName = "$env:SystemRoot\\System32\\cmd.exe"
    $processInfo.Arguments = "/d /c `"`"$runnerPath`"`""
    $processInfo.WorkingDirectory = $projectRoot
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $true
    [System.Diagnostics.Process]::Start($processInfo) | Out-Null
}

Start-GraceServer -Port 8000 -Name "grace-http"

$certificateFiles = @(
    ".certs\\grace-server-key.pem",
    ".certs\\grace-server.crt"
)
if ($certificateFiles | ForEach-Object { Test-Path (Join-Path $projectRoot $_) } | Where-Object { -not $_ }) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path (Join-Path $logDirectory "watchdog.log") -Value "$timestamp HTTPS was not started because its certificate files are missing. Run .\\start-https.ps1 once to create them."
    exit 0
}

Start-GraceServer -Port 8443 -Name "grace-https"
