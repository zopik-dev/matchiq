#requires -Version 5.1
<#
.SYNOPSIS
  Stop the local MatchIQ dev servers started by start.ps1.
#>
[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RunDir = Join-Path $Root ".run"

function Stop-Port([int]$Port) {
    $owners = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
    foreach ($processId in $owners) {
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  stopping port $Port (PID $processId, $($proc.ProcessName))" -ForegroundColor DarkYellow
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
}

foreach ($name in @("backend", "frontend")) {
    $pidFile = Join-Path $RunDir "$name.pid"
    if (Test-Path $pidFile) {
        $processId = Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($processId) {
            Stop-Process -Id ([int]$processId) -Force -ErrorAction SilentlyContinue
        }
        Remove-Item $pidFile -ErrorAction SilentlyContinue
    }
}

Stop-Port 8000
Stop-Port 5173

Write-Host "  MatchIQ dev servers stopped." -ForegroundColor Green
