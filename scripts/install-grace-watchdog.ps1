[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$watchdogPath = Join-Path $projectRoot "scripts\\watch-grace-servers.ps1"
$legacyTaskName = "G.R.A.C.E. Server Watchdog"
$startupTaskName = "G.R.A.C.E. Server Watchdog Startup"
$minuteTaskName = "G.R.A.C.E. Server Watchdog Minute Check"
$powershellPath = Join-Path $PSHOME "powershell.exe"
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$watchdogPath`""
$pythonPath = (& C:\Windows\py.exe -3.11 -c "import sys; print(sys.executable)").Trim()

if (-not (Test-Path $pythonPath)) {
    throw "Python 3.11 was not found. Install it before installing the watchdog."
}

Set-Content -Path (Join-Path $PSScriptRoot "grace-python-path.txt") -Value $pythonPath -NoNewline

foreach ($task in @(
    @{ Name = $startupTaskName; Schedule = @("/SC", "ONSTART") },
    @{ Name = $minuteTaskName; Schedule = @("/SC", "MINUTE", "/MO", "1") }
)) {
    & schtasks.exe /Create /TN $task.Name /TR "`"$powershellPath`" $arguments" @($task.Schedule) /RU SYSTEM /RL HIGHEST /F
    if ($LASTEXITCODE -ne 0) {
        throw "Could not create the scheduled task '$($task.Name)'."
    }
}
& schtasks.exe /Delete /TN $legacyTaskName /F 2>$null | Out-Null
& $powershellPath -NoProfile -ExecutionPolicy Bypass -File $watchdogPath
Write-Output "Installed startup and every-minute SYSTEM watchdog tasks."
