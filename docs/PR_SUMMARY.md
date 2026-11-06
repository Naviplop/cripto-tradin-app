# PR: Owner License Admin API, Electron CORS Fix, HWID UI, SSL WebSocket Context, Backtest Modules, Clean Architecture Migration

## Resumen

Este PR entrega el flujo completo de licencias controlado por el owner, corrige la conectividad desde Electron empaquetado, expone el HWID en la UI, mejora la robustez del WebSocket en producción, agrega módulos de backtesting y avanza la migración hacia Clean Architecture/DDD/CQRS.

## Cambios principales

### Backend funcional
- **CORS flexible:** Ahora acepta orígenes `file://` y loopback locales mediante regex, además de `FRONTEND_ORIGIN` y dev origins.
- **Admin API protegida:** Endpoints `/api/admin/*` para emitir, listar y revocar licencias usando `ADMIN_API_KEY`.
- **Registry local:** `backend/licenses_registry.json` guarda historial de licencias emitidas y revocadas.
- **SSL context:** `market_feed.py` usa `ssl.create_default_context()` para resolver certificados en builds empaquetados.
- **Health endpoint:** Ahora incluye `hwid` para que el usuario lo copie fácilmente.

### Backtest (módulo avanzado)
- Motor de backtesting vectorizado + event-driven en `backend/backtest/`.
- Métricas financieras completas y optimizaciones Grid Search / Walk Forward / Monte Carlo.
- Endpoints `/api/backtest/*` creados, aún no integrados en `main.py`.

### Clean Architecture (migración en progreso)
- Estructura creada: `backend/domain/`, `application/`, `infrastructure/`, `presentation/`, `config/`.
- Entidades, value objects, eventos, interfaces de repositorio y routers preparados.
- `main.py` sigue como composition root mixto; requiere integración final.

### Docs
- `docs/TECHNICAL_STATUS.md`: estado técnico completo y honesto.
- `docs/USER_STATUS.md`: estado para no técnicos.
- `docs/PR_SUMMARY.md`: este archivo.
- `README.md` y `docs/LICENSE_DISTRIBUTION.md` actualizados.

### Build
- Backend EXE recompilado: `backend/dist/trading_app.exe`
- Instalador actualizado: `dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe`

## Archivos modificados/creados (principales)
- `backend/main.py`
- `backend/.env`
- `backend/market_feed.py`
- `frontend/src/App.jsx`
- `scripts/generate_license.py`
- `backend/backtest/*`
- `backend/domain/**`
- `backend/application/**`
- `backend/infrastructure/**`
- `backend/presentation/**`
- `backend/config/**`
- `docs/*.md`
- `README.md`

## Verificación
- Admin API responde 200 con token correcto: ✅
- Health endpoint incluye `hwid`: ✅
- Frontend muestra HWID copiable: ✅
- Backend EXE arranca y sirve en puerto 8765: ✅
- Instalador generado sin errores: ✅

## Notas para reviewers
1. `ADMIN_API_KEY` debe cambiarse antes de distribución (actualmente `replace-me-owner-only`).
2. El modelo ONNX no está incluido; el sistema usa fallback heurístico.
3. Backtesting está implementado pero **no montado** en `main.py`.
4. Migración a Clean Architecture está avanzada pero **incompleta**; `main.py` es híbrido.
5. CORS regex permite `null` para desarrollo con Electron empaquetado.
6. WebSocket SSL context mitiga errores de certificado en Windows empaquetado.
7. Hace falta documentación `USER_MANUAL`, `SECURITY_AUDIT`, `ARCHITECTURE`, `BACKTEST_MANUAL`, `MLOPS`, `DEPLOYMENT_ENTERPRISE`.
