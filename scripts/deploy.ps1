<#
.SYNOPSIS
Pipeline de despliegue de release para Crypto Trading Terminal - LAFM.

.PARAMETER Version
Versión semántica a publicar (ej. 1.0.1). Si no se indica, calcula la siguiente versión desde package.json.

.PARAMETER SkipTrain
Omite el re-entrenamiento del modelo ONNX.

.PARAMETER Publish
Publica el instalador con electron-builder (--publish always). Por defecto, solo genera el instalador localmente.

.EXAMPLE
.\deploy.ps1 -Version 1.0.1 -Publish

.EXAMPLE
.\deploy.ps1 -SkipTrain
#>

param(
  [Parameter(Mandatory=$false)]
  [string]$Version,

  [Parameter(Mandatory=$false)]
  [switch]$SkipTrain,

  [Parameter(Mandatory=$false)]
  [switch]$Publish
)

$doPublish = $Publish.IsPresent

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $root
$backendDir = Join-Path $root 'backend'
$frontendDir = Join-Path $root 'frontend'
$scriptsDir = Join-Path $root 'scripts'
$distDir = Join-Path $root 'dist-electron'

$logDir = Join-Path $backendDir 'logs'
$logsArchive = Join-Path $backendDir 'logs_production_archive'

$versionInfoPath = Join-Path $backendDir 'version_info.txt'
$specPath = Join-Path $backendDir 'trading_app.spec'

$certThumbprint = $env:LAFM_SIGNING_CERT_THUMBPRINT
$timestampServer = 'http://timestamp.digicert.com'

if (-not (Test-Path $scriptsDir)) { New-Item -ItemType Directory -Path $scriptsDir -Force | Out-Null }
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Header($text) {
  Write-Host "`n=== $text ===" -ForegroundColor Cyan
}

function Write-OK($text) {
  Write-Host "[OK] $text" -ForegroundColor Green
}

function Write-Fail($text) {
  Write-Host "[FAIL] $text" -ForegroundColor Red
}

function Assert-Command($cmd) {
  $null = Get-Command $cmd -ErrorAction Stop
}

Write-Header 'Crypto Trading Terminal - LAFM | Deployment Pipeline'

# 0. Validaciones previas
Write-Header 'Step 0 | Validaciones previas'
Assert-Command 'node'
Assert-Command 'npm'
Assert-Command 'python'

$signtool = Get-Command signtool -ErrorAction SilentlyContinue
if (-not $signtool) {
  $candidates = @(
    "$env:ProgramFiles\Windows Kits\10\bin\$env:WINDOWSKITVER\x64\signtool.exe",
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin\$env:WINDOWSKITVER\x64\signtool.exe",
    "$env:ProgramFiles\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
    "${env:ProgramFiles(x86)}\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
    'C:\Program Files (x86)\Windows Kits\10\bin\x64\signtool.exe'
  )
  foreach ($p in $candidates) {
    if (Test-Path $p) {
      $signtool = Get-Item $p
      break
    }
  }
}
if (-not $signtool) {
  Write-Fail 'signtool no encontrado. Instala Windows SDK o define la variable WINDOWSKITVER.'
  exit 1
}
Write-OK "signtool encontrado en: $($signtool.FullName)"

$nodeVersion = node -v
$pythonVersion = python --version
Write-Host "Node: $nodeVersion"
Write-Host "Python: $pythonVersion"

if (-not (Test-Path $versionInfoPath)) {
  Write-Fail "No se encontró backend/version_info.txt"
  exit 1
}
Write-OK "version_info.txt presente"

if (-not (Test-Path $specPath)) {
  Write-Fail "No se encontró backend/trading_app.spec"
  exit 1
}
Write-OK "trading_app.spec presente"

# 0.1. Determinar versión
if (-not $Version) {
  $packageJson = Get-Content (Join-Path $root 'package.json') -Raw | ConvertFrom-Json
  $Version = $packageJson.version
  $parts = $Version -split '\.'
  if ($parts.Length -ne 3) {
    Write-Fail "Formato de versión inválido en package.json: $Version (esperado x.y.z)"
    exit 1
  }
  $parts[2] = [int]$parts[2] + 1
  $Version = ($parts -join '.')
  Write-Host "Versión detectada automáticamente: $Version"
} else {
  Write-Host "Versión solicitada: $Version"
}

# 1. Reentrenamiento ONNX
Write-Header 'Step 1 | Reentrenamiento ONNX'
if ($SkipTrain.IsPresent) {
  Write-Host 'SkipTrain activado. Se omite re-entrenamiento.'
  if (-not (Test-Path (Join-Path $backendDir 'models', 'trading_model.onnx'))) {
    Write-Fail 'No existe backend/models/trading_model.onnx y SkipTrain está activo.'
    exit 1
  }
  Write-OK 'Modelo ONNX existente conservado'
} else {
  Push-Location $scriptsDir
  try {
    python train_and_export_onnx.py
    Write-OK 'Modelo ONNX y artefactos regenerados'
  } finally {
    Pop-Location
  }
}

# 2. Build frontend
Write-Header 'Step 2 | Build Frontend'
Push-Location $frontendDir
try {
  npm run build
  Write-OK 'Frontend compilado'
} finally {
  Pop-Location
}

# 3. Bump de versión + build backend
Write-Header 'Step 3 | Bump versión y Build Backend'
$packageJsonPath = Join-Path $root 'package.json'
$packageJson = Get-Content $packageJsonPath -Raw | ConvertFrom-Json
$packageJson.version = $Version
$packageJson | ConvertTo-Json -Depth 10 | Set-Content $packageJsonPath -Encoding UTF8

$content = Get-Content $packageJsonPath -Raw
if ($content[0] -ne '{') {
  [System.IO.File]::WriteAllText($packageJsonPath, $content.TrimStart([char]0xFEFF), [System.Text.UTF8Encoding]::new($false))
}
Write-OK "package.json actualizado a versión $Version"

$versionInfoContent = Get-Content $versionInfoPath -Raw
$versionInfoContent = $versionInfoContent -replace 'filevers=\(\d+, \d+, \d+, \d+\)', "filevers=($($Version -replace '\.', ', '), 0)"
$versionInfoContent = $versionInfoContent -replace 'prodvers=\(\d+, \d+, \d+, \d+\)', "prodvers=($($Version -replace '\.', ', '), 0)"
$versionInfoContent = $versionInfoContent -replace "u'FileVersion', u'\d+\.\d+\.\d+\.\d+'", "u'FileVersion', u'$Version.0'"
$versionInfoContent = $versionInfoContent -replace "u'ProductVersion', u'\d+\.\d+\.\d+\.\d+'", "u'ProductVersion', u'$Version.0'"
Set-Content $versionInfoPath -Value $versionInfoContent -Encoding UTF8
Write-OK "version_info.txt actualizado a versión $Version"

Push-Location $backendDir
try {
  python -m PyInstaller $specPath --clean --noconfirm
  Write-OK 'Backend empaquetado con PyInstaller'
} finally {
  Pop-Location
}

$exePath = Join-Path (Join-Path $backendDir 'dist') 'trading_app.exe'
if (-not (Test-Path $exePath)) {
  Write-Fail "No se generó backend/dist/trading_app.exe"
  exit 1
}
Write-OK "trading_app.exe generado ($([math]::Round((Get-Item $exePath).Length / 1MB, 1)) MB)"

# 4. Firma Authenticode
Write-Header 'Step 4 | Firma Authenticode'
if (-not $certThumbprint) {
  Write-Host 'LAFM_SIGNING_CERT_THUMBPRINT no definido. Se intentará firma automática con /a.'
}
$signTool = $signtool.FullName
$signArgs = @('sign', '/fd', 'SHA256', '/tr', $timestampServer, '/td', 'SHA256', '/v', $exePath)
if ($certThumbprint) {
  $signArgs += @('/sha1', $certThumbprint)
} else {
  $signArgs += '/a'
}
$signProc = Start-Process -FilePath $signTool -ArgumentList $signArgs -NoNewWindow -Wait -PassThru
if ($signProc.ExitCode -eq 0) {
  Write-OK 'Firma Authenticode aplicada'
} else {
  Write-Fail "signtool falló con código $($signProc.ExitCode)"
  exit $signProc.ExitCode
}

# 5. Build Electron + publicación
Write-Header 'Step 5 | Build Electron + Publicación'
$extraArgs = @()
if ($Publish) {
  $extraArgs += '--publish', 'always'
  Write-Host 'Modo PUBLICACIÓN activado (--publish always)'
} else {
  Write-Host 'Modo local (sin publicación).'
}

Push-Location $root
try {
  if ($extraArgs.Count -gt 0) {
    npm run build:electron -- $extraArgs
  } else {
    npm run build:electron
  }
  Write-OK 'Instalador Electron generado'
} finally {
  Pop-Location
}

$installer = Get-ChildItem $distDir -Filter "*Setup*$Version*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $installer) {
  $installer = Get-ChildItem $distDir -Filter "*.exe" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
}
if ($installer) {
  Write-OK "Instalador: $($installer.FullName) ($([math]::Round($installer.Length / 1MB, 1)) MB)"
} else {
  Write-Fail 'No se encontró el instalador en dist-electron/'
  exit 1
}

# 6. Verificaciones finales
Write-Header 'Step 6 | Verificaciones finales'
$versionInfo = (Get-Item $exePath).VersionInfo
if ($versionInfo.ProductName -notmatch 'LAFM') {
  Write-Fail "ProductName no contiene LAFM: $($versionInfo.ProductName)"
  exit 1
}
Write-OK "ProductName: $($versionInfo.ProductName)"

if ($versionInfo.CompanyName -ne 'LAFM') {
  Write-Fail "CompanyName incorrecta: $($versionInfo.CompanyName)"
  exit 1
}
Write-OK "CompanyName: $($versionInfo.CompanyName)"

$archiveViewer = Join-Path (Join-Path $env:LOCALAPPDATA 'Programs\Microsoft VS Code\crypto-trading-app\backend') 'dist\trading_app.exe'
if (-not (Test-Path $archiveViewer)) {
  $archiveViewer = $exePath
}
Write-Host "Inspecciona manualmente con: pyi-archive_viewer `"$archiveViewer`""
Write-Host "Busca: models/trading_model.onnx, models/scaler_params.json, models/feature_names.json"

Write-Header 'Resumen de release'
Write-Host "Versión: $Version"
Write-Host "Backend: $exePath"
Write-Host "Instalador: $($installer.FullName)"
Write-Host "Metadatos LAFM: OK"
Write-Host "Firma Authenticode: OK"
Write-Host "`nPróximo paso: subir el instalador a GitHub Releases o canal de actualización."
