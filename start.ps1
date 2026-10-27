#requires -Version 5.1
<#
.SYNOPSIS
  MatchIQ local launcher: FastAPI on :8000 + Vite dashboard on :5173.

.DESCRIPTION
  One command for the hackathon demo. Installs missing dependencies, frees the
  two dev ports, starts both processes hidden, waits until they answer, then
  opens the dashboard. Logs live in .run/.

.EXAMPLE
  .\start.ps1
  .\start.ps1 -NoInstall -NoBrowser
#>
[CmdletBinding()]
param(
    [switch]$NoInstall,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$RunDir = Join-Path $Root ".run"
$Dashboard = "http://localhost:5173/"
$Health = "http://127.0.0.1:8000/health"

New-Item -ItemType Directory -Force -Path $RunDir | Out-Null

function Assert-Command([string]$Name, [string]$Hint) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing '$Name'. $Hint"
    }
}

function Stop-Port([int]$Port) {
    $owners = @(
        Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
    foreach ($processId in $owners) {
        $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($proc) {
            Write-Host "  freeing port $Port (PID $processId, $($proc.ProcessName))" -ForegroundColor DarkYellow
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Wait-Http([string]$Url, [int]$Attempts = 80) {
    for ($i = 0; $i -lt $Attempts; $i++) {
        try {
            $res = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($res.StatusCode -ge 200 -and $res.StatusCode -lt 500) { return $true }
        }
        catch {
            # Not up yet.
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Show-LogTail([string]$Path, [string]$Label) {
    if (Test-Path $Path) {
        Write-Host ""
        Write-Host "--- $Label (last 20 lines) ---" -ForegroundColor DarkYellow
        Get-Content -Path $Path -Tail 20 | ForEach-Object { Write-Host "  $_" }
    }
}

Write-Host ""
Write-Host "  MatchIQ - live match intelligence" -ForegroundColor White
Write-Host "  ---------------------------------" -ForegroundColor DarkGray

Assert-Command "python" "Install Python 3.11+ and add it to PATH."
Assert-Command "npm" "Install Node.js 20+ and add it to PATH."

if (-not (Test-Path $Backend)) { throw "Backend folder not found: $Backend" }
if (-not (Test-Path $Frontend)) { throw "Frontend folder not found: $Frontend" }

if (-not $NoInstall) {
    $depsOk = $false
    try {
        & python -c "import fastapi, uvicorn" *> $null
        $depsOk = ($LASTEXITCODE -eq 0)
    }
    catch {
        $depsOk = $false
    }
    if (-not $depsOk) {
        Write-Host "  installing backend dependencies..." -ForegroundColor Cyan
        & python -m pip install -e "${Backend}[dev]"
        if ($LASTEXITCODE -ne 0) { throw "pip install failed." }
    }
    if (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
        Write-Host "  installing frontend dependencies..." -ForegroundColor Cyan
        & npm --prefix $Frontend install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed." }
    }
}

Write-Host "  preparing ports..." -ForegroundColor DarkGray
Stop-Port 8000
Stop-Port 5173

$backendLog = Join-Path $RunDir "backend.log"
$backendErr = Join-Path $RunDir "backend.err.log"
$frontendLog = Join-Path $RunDir "frontend.log"
$frontendErr = Join-Path $RunDir "frontend.err.log"

Write-Host "  starting FastAPI on :8000..." -ForegroundColor Cyan
$backendProc = Start-Process -FilePath "python" `
    -ArgumentList @("-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1") `
    -WorkingDirectory $Backend `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $backendLog `
    -RedirectStandardError $backendErr
Set-Content -Path (Join-Path $RunDir "backend.pid") -Value $backendProc.Id

Write-Host "  starting Vite on :5173..." -ForegroundColor Cyan
$frontendProc = Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/c", "npm", "run", "dev") `
    -WorkingDirectory $Frontend `
    -WindowStyle Hidden `
    -PassThru `
    -RedirectStandardOutput $frontendLog `
    -RedirectStandardError $frontendErr
Set-Content -Path (Join-Path $RunDir "frontend.pid") -Value $frontendProc.Id

Write-Host "  waiting for the backend..." -ForegroundColor DarkGray
if (-not (Wait-Http $Health)) {
    Show-LogTail $backendErr "backend error log"
    Show-LogTail $backendLog "backend log"
    throw "Backend did not answer on $Health. See .run/backend*.log"
}

Write-Host "  waiting for the dashboard..." -ForegroundColor DarkGray
if (-not (Wait-Http $Dashboard)) {
    Show-LogTail $frontendErr "frontend error log"
    Show-LogTail $frontendLog "frontend log"
    throw "Dashboard did not answer on $Dashboard. See .run/frontend*.log"
}

Write-Host ""
Write-Host "  MatchIQ is live" -ForegroundColor Green
Write-Host "  dashboard  $Dashboard" -ForegroundColor White
Write-Host "  api        http://127.0.0.1:8000" -ForegroundColor Gray
Write-Host "  docs       http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host "  logs       $RunDir" -ForegroundColor DarkGray
Write-Host "  stop       .\stop.ps1" -ForegroundColor DarkGray
Write-Host ""

if (-not $NoBrowser) {
    Start-Process $Dashboard | Out-Null
}
