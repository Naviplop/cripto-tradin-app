<#
.SYNOPSIS
Script de validación local para Crypto Trading Terminal - LAFM.

.EXAMPLE
.\validate-local.ps1
#>

param(
  [switch]$RunBackend,
  [switch]$RunFrontend,
  [switch]$RunInstaller
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $root
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$installerDir = Join-Path $root 'dist-electron'

function Test-BackendPrerequisites {
  Write-Host "`n=== Backend Prerequisites ===" -ForegroundColor Cyan
  $pythonVersion = python --version 2>&1
  Write-Host "Python: $pythonVersion"
  $pipReq = Join-Path $backendDir 'requirements.txt'
  if (-not (Test-Path $pipReq)) { Write-Fail "requirements.txt missing"; exit 1 }
  Write-OK "requirements.txt present"
}

function Test-FrontendPrerequisites {
  Write-Host "`n=== Frontend Prerequisites ===" -ForegroundColor Cyan
  $nodeVersion = node -v
  Write-Host "Node: $nodeVersion"
  $pkg = Join-Path $frontendDir 'package.json'
  if (-not (Test-Path $pkg)) { Write-Fail "frontend/package.json missing"; exit 1 }
  Write-OK "frontend/package.json present"
}

function Test-BuildArtifacts {
  Write-Host "`n=== Build Artifacts ===" -ForegroundColor Cyan
  $distFrontend = Join-Path $frontendDir 'dist'
  if (-not (Test-Path $distFrontend)) { Write-Fail "frontend/dist missing. Run: npm run build:frontend"; exit 1 }
  Write-OK "frontend/dist present"
}

function Test-BackendTests {
  Write-Host "`n=== Backend Tests ===" -ForegroundColor Cyan
  Push-Location $backendDir
  try {
    python -m pytest tests/ -q --tb=short 2>&1 | Out-Host
  } finally {
    Pop-Location
  }
}

function Start-Backend {
  Write-Host "`n=== Starting Backend ===" -ForegroundColor Cyan
  $env:PYTHONPATH = $backendDir
  $proc = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8765" -WorkingDirectory $backendDir -PassThru -WindowStyle Normal
  Write-Host "Backend PID: $($proc.Id)"
  Write-Host "Waiting for server..."
  Start-Sleep -Seconds 3
  try {
    $health = Invoke-RestMethod -Uri "http://127.0.0.1:8765/api/health" -Method Get -TimeoutSec 5
    Write-OK "Backend health: $($health.status)"
  } catch {
    Write-Fail "Backend did not start correctly. Check logs."
    Write-Host $_
    exit 1
  }
  return $proc
}

function Start-FrontendDev {
  Write-Host "`n=== Starting Frontend Dev Server ===" -ForegroundColor Cyan
  $proc = Start-Process -FilePath "npm" -ArgumentList "run", "dev:frontend" -WorkingDirectory $root -PassThru -WindowStyle Normal
  Write-Host "Frontend PID: $($proc.Id)"
  Write-Host "Waiting for dev server..."
  Start-Sleep -Seconds 5
  try {
    $response = Invoke-WebRequest -Uri "http://localhost:3000" -Method Get -TimeoutSec 10 -UseBasicParsing
    if ($response.StatusCode -eq 200) { Write-OK "Frontend dev server running" }
  } catch {
    Write-Host "Frontend dev server may still be starting..."
  }
  return $proc
}

function Test-Installer {
  Write-Host "`n=== Installer Check ===" -ForegroundColor Cyan
  if (-not (Test-Path $installerDir)) {
    Write-Host "dist-electron directory not found. Run build first."
    return
  }
  $installers = Get-ChildItem $installerDir -Filter "*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 5
  if ($installers) {
    foreach ($inst in $installers) {
      Write-OK "$($inst.Name) ($([math]::Round($inst.Length / 1MB, 1)) MB)"
    }
  } else {
    Write-Host "No installers found. Run: npm run build:electron"
  }
}

function Write-OK($text) { Write-Host "[OK] $text" -ForegroundColor Green }
function Write-Fail($text) { Write-Host "[FAIL] $text" -ForegroundColor Red }

Test-BackendPrerequisites
Test-FrontendPrerequisites
Test-BuildArtifacts

if ($RunBackend -or $RunFrontend) {
  if ($RunBackend) { $backendProc = Start-Backend }
  if ($RunFrontend) { $frontendProc = Start-FrontendDev }
  
  Write-Host "`n=== Services Running ===" -ForegroundColor Cyan
  if ($RunBackend) { Write-Host "Backend: http://127.0.0.1:8765" }
  if ($RunFrontend) { Write-Host "Frontend: http://localhost:3000" }
  Write-Host "Press Ctrl+C to stop..."
  
  try {
    while ($true) { Start-Sleep -Seconds 1 }
  } catch {
    Write-Host "`nStopping services..."
    if ($backendProc) { Stop-Process -Id $backendProc.Id -Force }
    if ($frontendProc) { Stop-Process -Id $frontendProc.Id -Force }
  }
}

if ($RunInstaller) {
  Test-Installer
}

Write-Host "`n=== Manual Verification Checklist ===" -ForegroundColor Cyan
Write-Host "[ ] Backend: http://127.0.0.1:8765/api/health returns OK"
Write-Host "[ ] Frontend: http://localhost:3000 shows license screen"
Write-Host "[ ] After license validation, onboarding appears (first run)"
Write-Host "[ ] WebSocket connects and candlestick data streams"
Write-Host "[ ] Paper Trading mode works without API keys"
Write-Host "[ ] Installer generated in dist-electron/"
Write-Host "[ ] Update check triggers on app startup"
