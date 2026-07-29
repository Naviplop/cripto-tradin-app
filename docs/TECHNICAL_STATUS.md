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
└─────────────────────────────────────────────┘
```

---

## 2. Backend — Estado Detallado

### 2.1 Servidor API (`backend/main.py`)
- **Framework:** FastAPI + Uvicorn
- **Puerto:** 8765 (configurable por `.env`)
- **CORS:** Permite orígenes locales (`localhost`, `127.0.0.1`) y `file://` mediante regex. Incluye `FRONTEND_ORIGIN` y desarrollos Vite.
- **Rate limiting:** `/api/license/validate` limitado a 5 req/min/IP usando `slowapi`.
- **Excepciones:** Handler global para evitar leakage de información interna.

### 2.2 Endpoints REST

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

### 2.3 WebSocket (`/ws/market`)
- **Estado:** ✅ Activo
- **Mensajes cliente → servidor:** `ping`
- **Mensajes servidor → cliente:** `market_data`, `account_update`, `pong`
- **Reconexión:** Backoff exponencial + jitter en frontend

### 2.4 Motor de Trading (`backend/trading_engine.py`)
- **Modos:** Paper Trading ($10,000 USDT) / Live Trading
- ** órdenes:** MARKET, LIMIT, STOP_LIMIT, OCO
- **Señales:** EMA(10/30), RSI(14), MACD(12/26/9), Bollinger Bands, ATR
- **AI Fusion:** ONNX + heurístico → STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL
- **Gestión de riesgo:** TP/SL automáticos, PnL realizado y no realizado
- **Persistencia:** SQLite (`account_snapshots`, `positions`, `trades`, `predictions`, `license_cache`)
- **Heartbeat:** Snapshots cada 60s

### 2.5 IA / Modelo (`backend/ai_engine.py`)
- **Modelo:** ONNX con `onnxruntime` (CPUExecutionProvider)
- **Features:** 13 por vela (OHLCV, RSI, MACD, Bollinger, ATR, EMAs, Log Returns)
- **Ventana:** 30 velas → tensor `[1, 30, 8]`
- **Fallback:** Heurístico si no existe `.onnx`
- **Estado actual:** No hay modelo preentrenado en repo; usa fallback heurístico

### 2.6 Feed de Mercado (`backend/market_feed.py`)
- **Fuente principal:** Binance WebSocket (`wss://stream.binance.com:9443/ws/{symbol}@kline_{timeframe}`)
- **Cold start:** REST historical klines (200 velas)
- **SSL:** Contexto SSL robusto para empaquetado
- **Fallback:** Simulación interna tras 5 errores consecutivos
- **Reconexión:** Backoff exponencial con max 30s

### 2.7 Licencias (`backend/license_manager.py`)
- **HWID:** SHA-256 de motherboard + CPU + MAC + hostname
- **Firma:** HMAC-SHA256 de `{hwid}|{expiry}`
- **Validación:** Local, 100% offline
- **Formato:** `LIC-{base64_chunk_8}-...`
- **Registro:** `backend/licenses_registry.json` (emitidas/revocadas)
- **Admin API:** Protegida por `ADMIN_API_KEY` (header o query param)

### 2.8 Seguridad (`backend/secure_storage.py`)
- **Cifrado:** AES-256-GCM
- **Derivación:** HWID-bound key material
- **Almacenamiento:** SQLite en `%APPDATA%/LAFM/secure.db`
- **Hardening:** Zeroización de secrets en memoria

### 2.9 Logging (`backend/logger.py`)
- **Framework:** loguru
- **Rotación:** 10 MB
- **Retención:** 30 días
- **Compresión:** gzip

### 2.10 Empaquetado
- **Backend EXE:** `backend/dist/trading_app.exe` (~142 MB)
- **Instalador:** `dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe` (~214 MB)
- **Builder:** PyInstaller + electron-builder (NSIS)
- **Icono:** `assets/icon.png` (256×256)

---

## 3. Frontend — Estado Detallado

### 3.1 Stack
- **Framework:** React 18 + Vite
- **Estilos:** Tailwind CSS 3
- **Charts:** Lightweight Charts 4
- **Animaciones:** Framer Motion (onboarding)
- **Estado global:** Zustand

### 3.2 Componentes

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

### 3.3 Estado de la UI
- **Onboarding:** ✅ Completo
- **License gate:** ✅ Muestra HWID copiable
- **Conexión WS:** ✅ Reconexión con backoff exponencial + jitter
- **Fetch timeout:** ✅ 10s con AbortController
- **Carga/Error states:** ✅ En todas las llamadas API

---

## 4. Electron Wrapper

### 4.1 Main Process (`electron/main.js`)
- **Spawn backend:** Ejecuta `trading_app.exe` o `python main.py` según empaquetado
- **Lifecycle:** Limpia backend al cerrar ventana
- **Actualizaciones:** `electron-updater` apunta a GitHub Releases
- **Seguridad:** `contextIsolation: true`, `nodeIntegration: false`, navegación restringida

### 4.2 Preload (`electron/preload.js`)
- **Exposición segura:** IPC para seleccionar archivo de licencia

---

## 5. Licencias — Flujo Completo

### 5.1 Usuario Final
1. Instala app
2. Abre `http://127.0.0.1:8765/api/health` para obtener HWID
3. Comparte HWID con LAFM
4. Recibe clave `LIC-...`
5. Pega clave en app → valida backend localmente
6. App desbloqueada

### 5.2 Owner/LAFM
```powershell
cd scripts
python generate_license.py 365                          # propia máquina
python generate_license.py --hwid <HWID> 365            # máquina de amigo
python generate_license.py --hwid <HWID> 30 --note "trial"  # trial
```

### 5.3 Admin API (Owner)
```powershell
curl -H "X-Admin-Token: <token>" http://127.0.0.1:8765/api/admin/licenses
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: <token>" http://127.0.0.1:8765/api/admin/issue -d "{\"target_hwid\":\"<hwid>\",\"days_valid\":365}"
curl -X POST -H "Content-Type: application/json" -H "X-Admin-Token: <token>" http://127.0.0.1:8765/api/admin/revoke -d "{\"target_hwid\":\"<hwid>\",\"reason\":\"...\"}"
```

---

## 6. Tests

### 6.1 Backend (`pytest`)
- `test_trading_engine.py` — 6 tests: PnL, TP/SL, limit orders, snapshots, signals
- `test_license_manager.py` — 5 tests: HWID, validación, expiración, formato
- `test_ai_engine.py` — 4 tests: fallback, bullish/bearish bias
- **Total:** 16/16 passing

### 6.2 Frontend
- Sin tests automatizados actualmente

---

## 7. CI/CD

- **Pipeline:** `.github/workflows/security_audit.yml`
- **SAST:** Bandit (Python)
- **Dependencias:** Safety (Python)
- **Secret scanning:** Gitleaks
- **Frontend:** npm audit
- **Gate:** pytest + electron build
- **Auto-updates:** electron-updater configurado

---

## 8. Issues Conocidos

| ID | Descripción | Severidad | Estado |
|----|-------------|-----------|--------|
| ISS-01 | WebSocket SSL verify falla en algunas redes Windows | Media | ⚠️ Parcialmente mitigado con SSL context; puede requerir `REQUESTS_CA_BUNDLE` o instalación de certs |
| ISS-02 | No hay modelo ONNX preentrenado en repo | Media | ⚠️ Usa fallback heurístico; script de entrenamiento listo |
| ISS-03 | `datetime.utcnow()` deprecado | Baja | ⚠️ Advertido en warnings; reemplazar por `datetime.now(timezone.utc)` |
| ISS-04 | Faltan tests frontend | Baja | ⚠️ No bloqueaRelease |
| ISS-05 | Electron `asar` deshabilitado | Baja | ⚠️ Recomendado habilitar para producción |
| ISS-06 | Falta `ADMIN_API_KEY` en `.env` de producción | Media | ⚠️ Owner debe cambiarlo antes de distribuir |
| ISS-07 | Rate limiter usa IP interna en loopback | Baja | ⚠️ En producción remota funciona correctamente |
| ISS-08 | `ta` no es hidden import en PyInstaller | Baja | ⚠️ No crítico |
| ISS-09 | WebSocket usa `on_event` deprecated | Baja | ⚠️ Migrar a lifespan handlers |

---

## 9. Tareas Pendientes

| # | Tarea | Prioridad |
|---|-------|-----------|
| 1 | Entrenar modelo ONNX real con datos Binance | Alta |
| 2 | Habilitar `asar` en electron-builder | Media |
| 3 | Migrar `on_event` a lifespan handlers | Media |
| 4 | Reemplazar `datetime.utcnow()` por `datetime.now(timezone.utc)` | Baja |
| 5 | Agregar tests frontend (vitest) | Baja |
| 6 | Agregar `ADMIN_API_KEY` seguro en `.env` producción | Alta |
| 7 | Documentar proceso de actualización de modelo ONNX | Media |
| 8 | Agregar soporte multi-asset (ETH, SOL, BNB, XRP) | Media |
| 9 | Implementar circuito breaker en simulation fallback | Media |
| 10 | Agregar métricas y monitoreo (Prometheus/healthchecks) | Baja |
