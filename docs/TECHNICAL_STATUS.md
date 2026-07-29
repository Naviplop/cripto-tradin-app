# Estado Técnico Completo — LAFM Crypto Trading Terminal

**Versión:** 1.0.1  
**Fecha:** 2026-07-29  
**Repositorio:** https://github.com/Naviplop/cripto-tradin-app

---

## 1. Arquitectura General

```
┌─────────────────────────────────────────────┐
│              Electron 28 (Windows)           │
│  ┌───────────────────────────────────────┐  │
│  │   React 18 + Vite + Tailwind CSS     │  │
│  │   - License Gate                     │  │
│  │   - Lightweight Charts (candles)     │  │
│  │   - Order Book + Depth               │  │
│  │   - Trading Panel (Market/Limit/OCO) │  │
│  │   - Auto-login + WebSocket client    │  │
│  └───────────────────────────────────────┘  │
└──────────────────┬──────────────────────────┘
                   │ http://127.0.0.1:8765
                   │ ws://127.0.0.1:8765/ws/market
┌──────────────────▼──────────────────────────┐
│   FastAPI Backend (trading_app.exe)         │
│   - REST API + WebSocket                     │
│   - BinanceMarketFeed (WebSocket + REST)     │
│   - TradingEngine (paper/live)               │
│   - AIPredictor (ONNX/heurístico)            │
│   - LicenseManager (HWID + HMAC-SHA256)      │
│   - SecureStorage (AES-256-GCM)              │
│   - Admin API (/api/admin/*)                 │
│   - SQLite persistencia                       │
│   - Backtest router (/api/backtest/*)         │
└─────────────────────────────────────────────┘
```

**Nota:** Existe una migración parcial hacia Clean Architecture/DDD/CQRS en carpetas `backend/domain/`, `application/`, `infrastructure/`, `presentation/`, pero `main.py` sigue siendo composition root mixto y no toda la nueva capa está cableada aún.

---

## 2. Backend — Estado Detallado

### 2.1 Servidor API (`backend/main.py`)
- **Framework:** FastAPI + Uvicorn
- **Puerto:** 8765 (configurable por `.env`)
- **CORS:** Permite orígenes locales (`localhost`, `127.0.0.1`) y `file://` mediante regex. Incluye `FRONTEND_ORIGIN` y desarrollos Vite.
- **Rate limiting:** `/api/license/validate` limitado a 5 req/min/IP usando `slowapi`.
- **Excepciones:** Handler global para evitar leakage de información interna.
- **Compatibility:** Endpoints legacy preservados para no romper el frontend actual.

### 2.2 Capas nuevas (migración en progreso)
| Capa | Ruta | Estado |
|------|------|--------|
| Domain Entities | `backend/domain/entities/*.py` | Parcial: existen Order, Position, Candle, pero hay imports rotos y contratos incompletos |
| Value Objects | `backend/domain/value_objects/*.py` | Creado, pero sin validaciones exhaustivas |
| Events | `backend/domain/events/*.py` | Creado, no integrado en handlers |
| Repositories ABC | `backend/domain/repositories/interfaces.py` | Interfaces declaradas, sin implementación SQLAlchemy 2.0 |
| Commands | `backend/application/commands/*.py` | Placeholders funcionales limitados |
| Queries | `backend/application/queries/*.py` | Algunas queries creadas, sin cableado completo |
| Services | `backend/application/services/*.py` | Orchestration service parcial |
| Infrastructure | `backend/infrastructure/**/*.py` | IA, market data, security avanzados; falta persistence SQLAlchemy |
| Presentation routers | `backend/presentation/routers/*.py` | Routers creados, pero `main.py` no monta todos |
| Config | `backend/config/*.py` | Settings y dependencies parciales |

### 2.3 Endpoints REST

| Método | Ruta | Estado | Notas |
|--------|------|--------|-------|
| GET | `/api/health` | ✅ Activo | Devuelve `status`, `license_valid`, `hwid` |
| POST | `/api/license/validate` | ✅ Activo | Valida licencia HWID-bound |
| GET | `/api/account/balance` | ✅ Activo | Resumen de cuenta |
| GET | `/api/account/positions` | ✅ Activo | Posiciones abiertas |
| GET | `/api/account/history` | ✅ Activo | Trades cerrados |
| POST | `/api/trading/order` | ✅ Activo | MARKET/LIMIT/STOP_LIMIT/OCO + TP/SL |
| GET | `/api/trading/signals` | ✅ Activo | Señales técnicas + AI |
| GET | `/api/market/ticker` | ✅ Activo | Métricas 24h Binance |
| GET | `/api/market/orderbook` | ✅ Activo | Depth de órdenes |
| GET | `/api/market/klines` | ✅ Activo | Velas históricas por symbol/interval |
| POST | `/api/auth/verify-keys` | ✅ Activo | Validación de API keys |
| POST | `/api/model/update` | ✅ Activo | Descarga modelo ONNX |
| GET | `/api/model/status` | ✅ Activo | Estado del modelo AI |
| POST | `/api/config/api-keys` | ✅ Activo | Guarda API keys |
| GET | `/api/config/api-keys` | ✅ Activo | Lee API keys enmascaradas |
| DELETE | `/api/config/api-keys` | ✅ Activo | Elimina API keys |
| GET | `/api/admin/licenses` | ✅ Activo | Lista licencias emitidas/revocadas |
| POST | `/api/admin/issue` | ✅ Activo | Emite nueva licencia |
| POST | `/api/admin/revoke` | ✅ Activo | Revoca licencia por HWID |
| DELETE | `/api/admin/licenses` | ✅ Activo | Limpia registry |
| POST | `/api/backtest/run` | ⚠️ Parcial | Router existe, no integrado en `main.py` |
| GET | `/api/backtest/result/{run_id}` | ⚠️ Parcial | Router existe, no integrado en `main.py` |
| POST | `/api/backtest/optimize` | ⚠️ Parcial | Router existe, no integrado en `main.py` |
| GET | `/api/backtest/metrics/{run_id}` | ⚠️ Parcial | Router existe, no integrado en `main.py` |

### 2.4 WebSocket (`/ws/market`)
- **Estado:** ✅ Activo
- **Mensajes cliente → servidor:** `ping`
- **Mensajes servidor → cliente:** `market_data`, `account_update`, `pong`
- **Reconexión:** Backoff exponencial + jitter en frontend

### 2.5 Motor de Trading (`backend/trading_engine.py`)
- **Modos:** Paper Trading ($10,000 USDT) / Live Trading
- ** órdenes:** MARKET, LIMIT, STOP_LIMIT, OCO
- **Señales:** EMA(10/30), RSI(14), MACD(12/26/9), Bollinger Bands, ATR
- **AI Fusion:** ONNX + heurístico → STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL
- **Gestión de riesgo:** TP/SL automáticos, PnL realizado y no realizado
- **Persistencia:** SQLite (`account_snapshots`, `positions`, `trades`, `predictions`, `license_cache`)
- **Heartbeat:** Snapshots cada 60s

### 2.6 IA / Modelo (`backend/ai_engine.py` + `backend/infrastructure/ai/*.py`)
- **Modelo:** ONNX con `onnxruntime` (CPUExecutionProvider)
- **Features:** 13+ por vela (OHLCV, RSI, MACD, Bollinger, ATR, EMAs, Log Returns)
- **Ventana:** 30 velas → tensor `[1, 30, 8]`
- **Fallback:** Heurístico si no existe `.onnx`
- **Estado actual:** Motor multi-modelo avanzado en `infrastructure/ai/` existe, pero no integrado en risk/backtesting ni tests 90%.
- **Modelo ONNX real:** No incluido en repo.

---

## 3. Backtesting y Optimización Cuant

### 3.1 Estado actual
- Módulos creados en `backend/backtest/`: `engine.py`, `portfolio.py`, `metrics.py`, `optimization.py`, `data.py`, `api_routes.py`, `schemas.py`.
- Router FastAPI en `/api/backtest/*` existe pero **no está montado en `main.py`**.
- Sin tests unitarios/integración garantizados.
- No integrado con dominio/riesgo ni ejecución real.

### 3.2 Hace falta
- Integrar router en `main.py`.
- Alinear contratos Pydantic v2 y limpiar imports rotos (`BacktestMetrics`).
- Reutilizar entidades de dominio (`Trade`, `Position`, `Candle`, `Money`).
- Añadir tests y validar métricas estadísticas.

---

## 4. Estado de la Documentación y Documentos Pendientes

### 4.1 Documentación actualizada
- `docs/PR_SUMMARY.md` — resumen ejecutable de entregas.
- `docs/USER_STATUS.md` — estado para no técnicos.
- `docs/LICENSE_DISTRIBUTION.md` — flujo end-to-end de licencias.
- `docs/API_KEYS_SECURITY.md` — CORS y hardening.
- `README.md` — actualizado con owner workflow y admin API.

### 4.2 Documentación faltante (requerida para producción institucional)
- `docs/USER_MANUAL.md` — actualizar a nuevas pantallas y flujo HWID/Admin API.
- `docs/SECURITY_AUDIT.md` — detalle de defensas Zero Trust, zeroize, CORS, rate limiting.
- `docs/ARCHITECTURE.md` — diagramas C4/DDD/CQRS con Mermaid, flujos WS, ONNX, licencias.
- `docs/BACKTEST_MANUAL.md` — guía de uso del motor de backtesting y optimización.
- `docs/MLOPS.md` — pipeline de entrenamiento, versionado, hot-update, monitoreo.
- `docs/DEPLOYMENT_ENTERPRISE.md` — guía de release, Authenticode, canales Stable/Beta.

---

## 5. Frontend — Estado Detallado

### 5.1 Stack
- **Framework:** React 18 + Vite
- **Estilos:** Tailwind CSS 3
- **Charts:** Lightweight Charts 4
- **Animaciones:** Framer Motion (onboarding)
- **Estado global:** Zustand

### 5.2 Componentes

| Componente | Estado | Notas |
|------------|--------|-------|
| `App.jsx` | ✅ Activo | Bootstrap, health check, auto-login, license gate, WS reconnect |
| `HeaderBar.jsx` | ✅ Activo | Multi-pair selector, timeframe, ticker 24h, latency |
| `CandleChart.jsx` | ✅ Activo | Velas + drawing tools + hotkeys + timeframe change |
| `TradingPanel.jsx` | ✅ Activo | Formulario MARKET/LIMIT/STOP_LIMIT/OCO + TP/SL |
| `OrderBookWidget.jsx` | ✅ Activo | Depth chart + order book real-time |
| `AlertsToast.jsx` | ✅ Activo | Toasts animados para señales |
| `Onboarding.jsx` | ✅ Activo | Wizard 4 pasos + validación API keys |
| `SplashScreen.jsx` | ✅ Activo | Splash inicial animado |

### 5.3 Limitaciones actuales
- **TypeScript strict:** No migrado. Todo en `.jsx`/`.js` actualmente.
- **Arquitectura por capas:** No implementada; componentes en `components/` y estado global en `store.js` sin slices tipados.
- **HexagonFragmentWidget / Docking Layout:** No implementados.
- **Tests frontend:** No existen.

---

## 6. Electron Wrapper

### 6.1 Main Process (`electron/main.js`)
- **Spawn backend:** Ejecuta `trading_app.exe` o `python main.py` según empaquetado
- **Lifecycle:** Limpia backend al cerrar ventana
- **Actualizaciones:** `electron-updater` apunta a GitHub Releases
- **Seguridad:** `contextIsolation: true`, `nodeIntegration: false`, navegación restringida

### 6.2 Preload (`electron/preload.js`)
- **Exposición segura:** IPC para seleccionar archivo de licencia

---

## 7. Licencias — Flujo Completo

### 7.1 Usuario Final
1. Instala app
2. Abre `http://127.0.0.1:8765/api/health` para obtener HWID
3. Comparte HWID con LAFM
4. Recibe clave `LIC-...`
5. Pega clave en app → valida backend localmente
6. App desbloqueada

### 7.2 Owner/LAFM
```powershell
cd scripts
python generate_license.py 365                          # propia máquina
python generate_license.py --hwid <HWID> 365            # máquina de amigo
python generate_license.py --hwid <HWID> 30 --note "trial"  # trial
```

### 7.3 Admin API (Owner)
```powershell
curl -H "X-Admin-Token: <token>" http://127.0.0.1:8765/api/admin/licenses
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: <token>" http://127.0.0.1:8765/api/admin/issue -d "{\"target_hwid\":\"<hwid>\",\"days_valid\":365}"
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: <token>" http://127.0.0.1:8765/api/admin/revoke -d "{\"target_hwid\":\"<hwid>\",\"reason\":\"...\"}"
```

**Nota:** Persistencia de licencias avanzada con JWT offline 30 días requiere `lafm-license-server` completo; actualmente no implementado.

---

## 8. Tests

### 8.1 Backend (`pytest`)
- `test_trading_engine.py` — 6 tests: PnL, TP/SL, limit orders, snapshots, signals
- `test_license_manager.py` — 5 tests: HWID, validación, expiración, formato
- `test_ai_engine.py` — 4 tests: fallback, bullish/bearish bias
- `test_backtest.py` — presente pero sin ejecución garantizada
- **Cobertura actual:** < 90%. **Objetivo institucional:** > 90%.

### 8.2 Frontend
- Sin tests automatizados actualmente

---

## 9. CI/CD

- **Pipeline:** `.github/workflows/security_audit.yml`
- **SAST:** Bandit (Python)
- **Dependencias:** Safety (Python)
- **Secret scanning:** Gitleaks
- **Frontend:** npm audit
- **Gate:** pytest + electron build
- **Auto-updates:** electron-updater configurado

**Hace falta:** cobertura backend > 90%, tests frontend vitest, firma Authenticode, publicar releases.

---

## 10. Issues Conocidos

| ID | Descripción | Severidad | Estado |
|----|-------------|-----------|--------|
| ISS-01 | WebSocket SSL verify falla en algunas redes Windows | Media | ⚠️ Mitigado con SSL context; puede requerir certs |
| ISS-02 | No hay modelo ONNX preentrenado en repo | Media | ⚠️ Usa fallback heurístico |
| ISS-03 | `datetime.utcnow()` deprecado | Baja | ⚠️ Reemplazar por `datetime.now(timezone.utc)` |
| ISS-04 | Sin tests frontend | Baja | ⚠️ No bloquea release |
| ISS-05 | Electron `asar` deshabilitado | Baja | ⚠️ Habilitar para producción |
| ISS-06 | Falta `ADMIN_API_KEY` seguro en `.env` producción | Media | ⚠️ Owner debe cambiarlo |
| ISS-07 | Rate limiter usa IP interna en loopback | Baja | ⚠️ Producción remota funciona |
| ISS-08 | `ta` no es hidden import en PyInstaller | Baja | ⚠️ No crítico |
| ISS-09 | `on_event` deprecated → lifespan | Baja | ⚠️ Migrar |
| ISS-10 | Migración Clean Architecture incompleta | Alta | ⚠️ main.py mixto, routers no cableados |
| ISS-11 | Backtest no integrado en API principal | Alta | ⚠️ Router existe, no montado |
| ISS-12 | Repositorios SQLAlchemy 2.0 ausentes | Alta | ⚠️ Falta implementación concreta |
| ISS-13 | Faltan docs USER_MANUAL, SECURITY_AUDIT, ARCHITECTURE | Media | ⚠️ Bloquea release institucional |

---

## 11. Tareas Pendientes

| # | Tarea | Prioridad |
|---|-------|-----------|
| 1 | Entrenar modelo ONNX real con datos Binance | Alta |
| 2 | Completar migración Clean Architecture: main.py composition root + lifespan | Alta |
| 3 | Implementar repositorios SQLAlchemy 2.0 + unit of work | Alta |
| 4 | Integrar router `/api/backtest/*` en `main.py` y alinear Pydantic v2 | Alta |
| 5 | Alcanzar cobertura backend > 90% con pytest | Alta |
| 6 | Cambiar `ADMIN_API_KEY` en `.env` producción | Alta |
| 7 | Firmar ejecutable con Authenticode | Media |
| 8 | Migrar frontend a TypeScript strict Clean Architecture | Media |
| 9 | Habilitar `asar` en electron-builder | Media |
| 10 | Implementar `lafm-license-server` con JWT offline 30 días | Media |
| 11 | Agregar tests frontend (vitest) | Baja |
| 12 | Documentar pipeline MLOps y release enterprise | Baja |
| 13 | Soporte multi-asset (ETH, SOL, BNB, XRP) | Media |
| 14 | Implementar circuito breaker en simulation fallback | Baja |
| 15 | Agregar métricas y monitoreo | Baja |
