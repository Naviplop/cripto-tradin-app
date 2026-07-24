# Checklist Operacional - Lanzamiento LAFM

## Pre-requisitos
- [ ] `assets/icon.png` presente (512x512, recomendado para branding).
- [ ] Backend `.env` actualizado con `LICENSE_SECRET` fuerte y único.
- [ ] `FRONTEND_ORIGIN` configurado al dominio de producción.
- [ ] Node.js 18+, Python 3.10+, pip instalados.
- [ ] Git configurado y rama `main` actualizada.

---

## Pipeline de Release

### Opción A: Automático (PowerShell)
```powershell
cd C:\Users\fijuarez\AppData\Local\Programs\Microsoft VS Code\crypto-trading-app
.\scripts\deploy.ps1 -Version 1.0.1 -Publish
```

### Opción B: Manual paso a paso
```powershell
# 1. Reentrenar modelo ONNX (opcional)
cd scripts
python train_ai_model.py

# 2. Bump de versión
cd ..
npm version 1.0.1 --no-git-tag-version

# 3. Build frontend
cd frontend
npm run build

# 4. Build backend + PyInstaller
cd ../backend
pip install -r requirements.txt
python -m PyInstaller trading_app.spec --clean --noconfirm

# 5. Firma Authenticode (opcional pero recomendado)
signtool sign /fd SHA256 /tr http://timestamp.digicert.com /td SHA256 /a dist/trading_app.exe

# 6. Build Electron installer
cd ../
npm run build:electron
```

---

## Verificación Post-Release

### Backend `.exe`
- [ ] `backend/dist/trading_app.exe` existe (~145 MB).
- [ ] Metadatos LAFM:
  ```powershell
  (Get-Item "backend/dist/trading_app.exe").VersionInfo | Select-Object CompanyName, ProductName, Publisher, LegalCopyright
  ```
  Esperado:
  - `CompanyName: LAFM`
  - `ProductName: Crypto Trading Terminal - LAFM`
  - `Publisher: LAFM`
  - `LegalCopyright: LAFM. All rights reserved.`
- [ ] Modelo ONNX empaquetado:
  ```powershell
  pyi-archive_viewer backend/dist/trading_app.exe
  ```
  Buscar: `models/trading_model.onnx`, `models/scaler_params.json`, `models/feature_names.json`
- [ ] Logs de carga (ejecutar `.exe`):
  - `ONNX model loaded successfully`
  - `Loaded 13 feature names`
  - `Loaded scaler params`
  - No debe aparecer `Using heuristic fallback`

### Instalador Electron
- [ ] `dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.0.exe` existe.
- [ ] Al instalar, el acceso directo se llama `LAFM Trading Terminal`.
- [ ] Al ejecutar:
  - [ ] Frontend carga desde `frontend/dist/`.
  - [ ] Backend inicia como proceso hijo (`trading_app.exe`).
  - [ ] Conecta a Binance WebSocket.
  - [ ] License gate funciona con clave generada por `scripts/generate_license.py`.

---

## Publicación

### GitHub Releases
1. Crear tag y push:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```
2. Adjuntar instalador a la release.
3. Verificar que `electron-updater` apunta al repo correcto.

### Canal de Actualización Automática
- Configurar `electron-updater` en `electron/main.js` con `owner` y `repo` reales.
- El cliente descargará parches automáticamente al iniciar.

---

## Rollback
- [ ] Conservar instalador anterior como backup.
- [ ] En caso de fallo, publicar release anterior como `latest` en GitHub.

---

## Contacto
- **Autor:** LAFM
- **Email/Repo:** [configurar en GitHub]
