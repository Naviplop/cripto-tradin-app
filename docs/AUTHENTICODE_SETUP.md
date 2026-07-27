# Authenticode Code Signing Setup Guide — LAFM v1.0.1

## Overview

Windows SmartScreen and Defender SmartScreen warn users when running unsigned `.exe` files. For professional distribution, sign the executables with an Authenticode certificate.

## Prerequisites

- Windows 10/11
- **Code Signing Certificate**: either a self-signed test certificate or a commercial one from a CA (e.g., DigiCert, Sectigo)
- `signtool.exe` (included in Visual Studio Build Tools or Windows SDK)
- `openssl` (for PFX conversion if needed)

## Step 1: Obtain a Certificate

### Option A: Self-Signed (Testing Only)

```powershell
$cert = New-SelfSignedCertificate -Subject "CN=LAFM" -Type CodeSigningCert -CertStoreLocation Cert:\CurrentUser\My
Export-PfxCertificate -Cert $cert -FilePath .\lafm-test-cert.pfx -Password (ConvertTo-SecureString -String "YourPassword" -Force -AsPlainText)
```

### Option B: Commercial CA

Purchase a Code Signing certificate from:
- DigiCert
- Sectigo
- GlobalSign
- etc.

Download the `.pfx` or `.p12` file.

## Step 2: Sign the Backend EXE

```powershell
$cert = Get-PfxCertificate -FilePath .\lafm-test-cert.pfx
$exe = "backend\dist\trading_app.exe"
signtool.exe sign /sha1 $cert.Thumbprint /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $exe
```

## Step 3: Sign the Electron Installer

```powershell
$cert = Get-PfxCertificate -FilePath .\lafm-test-cert.pfx
$installer = "dist-electron\Crypto Trading Terminal - LAFM Setup 1.0.1.exe"
signtool.exe sign /sha1 $cert.Thumbprint /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 $installer
```

## Step 4: Associate `scripts/sign.ps1`

Create `scripts/sign.ps1`:

```powershell
param(
    [string]$CertThumbprint,
    [string]$PfxPath,
    [string]$TimestampServer = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

if (-not (Get-Command signtool.exe -ErrorAction SilentlyContinue)) {
    Write-Error "signtool.exe not found. Install Visual Studio Build Tools or Windows SDK."
}

$cert = Get-PfxCertificate -FilePath $PfxPath
if (-not $cert) {
    Write-Error "Certificate not found at $PfxPath"
}

$targets = @(
    "backend\dist\trading_app.exe",
    "dist-electron\Crypto Trading Terminal - LAFM Setup 1.0.1.exe"
)

foreach ($target in $targets) {
    if (-not (Test-Path $target)) {
        Write-Warning "Skipping missing file: $target"
        continue
    }
    Write-Host "Signing $target ..."
    signtool.exe sign /sha1 $cert.Thumbprint /fd SHA256 /tr $TimestampServer /td SHA256 $target
    Write-Host "Signed: $target"
}
```

Usage:
```powershell
.\scripts\sign.ps1 -PfxPath .\lafm-test-cert.pfx -CertThumbprint "ABCD1234..."
```

## Step 5: Automate in CI/CD

In `.github/workflows/release.yml`:

```yaml
- name: Sign executables
  run: |
    $pwd
    $env:PATH = "$env:PATH;C:\Program Files (x86)\Windows Kits\10\bin\${{matrix.arch}}\x64"
    .\scripts\sign.ps1 -PfxPath ${{ secrets.CODE_SIGNING_PFX }} -CertThumbprint ${{ secrets.CODE_SIGNING_THUMBPRINT }}
  env:
    CODE_SIGNING_PFX: ${{ secrets.CODE_SIGNING_PFX }}
    CODE_SIGNING_THUMBPRINT: ${{ secrets.CODE_SIGNING_THUMBPRINT }}
```

Upload the `.pfx` as a GitHub secret (`CODE_SIGNING_PFX`) in base64 or as a secure artifact.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `signtool.exe not found` | Windows SDK missing | Install VS Build Tools or Windows 10/11 SDK |
| `The specified certificate is not valid` | Wrong thumbprint or expired cert | Verify cert with `certmgr.msc` |
| `Timestamp server unavailable` | Network/firewall | Use alternative: `/tr http://timestamp.sectigo.com` |
| `Access denied` | File locked | Close all running instances of the app |

## Production Checklist

- [ ] Commercial certificate purchased and installed
- [ ] `signtool.exe` available in PATH
- [ ] Backend EXE signed
- [ ] Electron installer signed
- [ ] Timestamp verified
- [ ] Test on clean PC (no dev tools installed)
