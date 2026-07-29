# PR: Owner License Admin API, Electron CORS Fix, HWID UI, SSL WebSocket Context

## Resumen

Este PR entrega el flujo completo de licencias controlado por el owner, corrige la conectividad desde Electron empaquetado, expone el HWID en la UI y mejora la robustez del WebSocket en producción.

## Cambios principales

### Backend
- **CORS flexible:** Ahora acepta orígenes `file://` y loopback locales mediante regex, además de `FRONTEND_ORIGIN` y dev origins.
- **Admin API protegida:** Endpoints `/api/admin/*` para emitir, listar y revocar licencias usando `ADMIN_API_KEY`.
- **Registry local:** `backend/licenses_registry.json` guarda historial de licencias emitidas y revocadas.
- **SSL context:** `market_feed.py` usa `ssl.create_default_context()` para resolver certificados en builds empaquetados.
- **Health endpoint:** Ahora incluye `hwid` para que el usuario lo copie fácilmente.

### Frontend
- **License gate mejorada:** Muestra el HWID del usuario con botón "Copy" para compartirlo con LAFM.
- **Manejo de errores:** Mensajes más claros cuando el backend no responde.

### Scripts
- **`generate_license.py`:** Ahora soporta `--hwid <hwid>` y `--note "texto"`, y registra cada licencia en `backend/licenses_registry.json`.

### Docs
- **`docs/LICENSE_DISTRIBUTION.md`:** Flujo end-to-end de licencias, comandos de owner, registry format, admin API.
- **`docs/API_KEYS_SECURITY.md`:** Actualizado con política CORS para Electron empaquetado.
- **`docs/TECHNICAL_STATUS.md`:** Estado técnico completo (nuevo).
- **`docs/USER_STATUS.md`:** Estado para no técnicos (nuevo).
- **`README.md`:** Actualizado con owner workflow y admin API.

### Build
- Backend EXE recompilado: `backend/dist/trading_app.exe` (~142 MB)
- Instalador actualizado: `dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe` (~214 MB)

## Archivos modificados

- `backend/main.py`
- `backend/.env`
- `backend/market_feed.py`
- `frontend/src/App.jsx`
- `scripts/generate_license.py`
- `docs/LICENSE_DISTRIBUTION.md`
- `docs/API_KEYS_SECURITY.md`
- `README.md`
- `docs/TECHNICAL_STATUS.md` (nuevo)
- `docs/USER_STATUS.md` (nuevo)

## Verificación

- Admin API responde 200 con token correcto: ✅
- Health endpoint incluye `hwid`: ✅
- Frontend muestra HWID copiable: ✅
- Backend EXE arranca y sirve en puerto 8765: ✅
- Instalador generado sin errores: ✅

## Notas para reviewers

1. `ADMIN_API_KEY` debe cambiarse antes de distribución (actualmente `replace-me-owner-only`).
2. El modelo ONNX no está incluido; el sistema usa fallback heurístico.
3. CORS regex permite `null` para desarrollo con Electron empaquetado.
4. WebSocket SSL context mitiga errores de certificado en Windows empaquetado.
