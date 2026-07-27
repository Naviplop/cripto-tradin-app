param(
    [switch]$SkipSign,
    [string]$CertThumbprint,
    [string]$PfxPath
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$backendDist = Join-Path $root 'backend\dist\trading_app.exe'
$electronDist = Join-Path $root 'dist-electron'
$installerName = 'Crypto Trading Terminal - LAFM Setup 1.0.1.exe'
$installerPath = Join-Path $electronDist $installerName

Write-Host '=== LAFM Enterprise Deploy Script ===' -ForegroundColor Cyan

function Test-Command {
    param([string]$Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Write-Step($msg) {
    Write-Host "[DEPLOY] $msg" -ForegroundColor Green
}

function Write-Warn($msg) {
    Write-Host "[DEPLOY][WARN] $msg" -ForegroundColor Yellow
}

function Write-Fail($msg) {
    Write-Host "[DEPLOY][FAIL] $msg" -ForegroundColor Red
}

Write-Step 'Validating prerequisites...'
if (-not (Test-Command 'python')) {
    Write-Fail 'Python is required.'
    exit 1
}
if (-not (Test-Command 'node')) {
    Write-Fail 'Node.js is required.'
    exit 1
}
if (-not (Test-Command 'npm')) {
    Write-Fail 'npm is required.'
    exit 1
}

Write-Step 'Installing backend dependencies...'
Set-Location (Join-Path $root 'backend')
python -m pip install --upgrade pip
pip install -r requirements.txt

Write-Step 'Building frontend...'
Set-Location (Join-Path $root 'frontend')
npm ci
npm run build

Write-Step 'Packaging backend with PyInstaller...'
Set-Location (Join-Path $root 'backend')
python -m PyInstaller trading_app.spec --clean --noconfirm
if (-not (Test-Path $backendDist)) {
    Write-Fail "Backend build failed: $backendDist not found."
    exit 1
}
Write-Step "Backend built: $backendDist"

Write-Step 'Packaging Electron installer...'
Set-Location $root
$packageJson = Get-Content (Join-Path $root 'package.json') | ConvertFrom-Json
if ($packageJson.scripts.'build:electron') {
    npm run build:electron
} else {
    Write-Warn 'No build:electron script found, attempting npx electron-builder...'
    npx electron-builder --win nsis
}

if (-not (Test-Path $installerPath)) {
    Write-Fail "Electron installer not found at $installerPath"
    exit 1
}
Write-Step "Installer built: $installerPath"

if (-not $SkipSign) {
    Write-Step 'Signing executables...'
    if (-not (Test-Path (Join-Path $root 'scripts\sign.ps1'))) {
        Write-Warn 'scripts/sign.ps1 not found. Skipping code signing.'
    } else {
        if (-not $CertThumbprint -or -not $PfxPath) {
            Write-Warn 'Missing -CertThumbprint or -PfxPath. Skipping signing step.'
        } else {
            & (Join-Path $root 'scripts\sign.ps1') -PfxPath $PfxPath -CertThumbprint $CertThumbprint
        }
    }
} else {
    Write-Warn 'Skipping code signing due to -SkipSign.'
}

Write-Step 'Preparing auto-update artifacts...'
$githubOwner = 'Naviplop'
$githubRepo = 'cripto-tradin-app'
$latestYaml = Join-Path $electronDist 'latest.yml'
if (Test-Path $latestYaml) {
    Write-Step "latest.yml ready at $latestYaml"
} else {
    Write-Warn 'latest.yml not found. Auto-update metadata may be missing.'
}

Write-Step 'Deployment artifacts:'
Get-Item $backendDist | Format-Table Name, Length, LastWriteTime -AutoSize
Get-Item $installerPath | Format-Table Name, Length, LastWriteTime -AutoSize

Write-Host '=== Deployment completed successfully ===' -ForegroundColor Cyan
