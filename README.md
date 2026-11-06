# Crypto Trading Terminal - LAFM

**Algorithmic Crypto Trading & Paper Trading Desktop Application for Binance BTC/USDT.**
**Author: LAFM**
**Version:** 1.0.1
**Updated:** 2026-07-28

> **Status:** Production-ready backend, license admin API, and Electron connectivity fixes landed.  
> **Last updated:** 2026-07-28

---

## 1. Resumen ejecutivo

Este proyecto combina tres capas:

- Backend en Python con FastAPI para lógica de trading, señales, licencias y almacenamiento local.
- Frontend en React + Vite + Tailwind para visualización de velas, panel de trading y onboarding.
- Escritorio con Electron para ejecutar el backend y mostrar la UI como aplicación local.

El sistema está pensado como una terminal local-first para operar con Binance, analizar precio, generar señales y simular posiciones en tiempo real sin depender de un backend externo. La intención es que el usuario tenga control local del flujo, la licencia, las claves y la IA.

> Contrato operativo obligatorio: [SYSTEM_MASTER_CONTRACT.md](SYSTEM_MASTER_CONTRACT.md). Todo cambio debe respetar las reglas de riesgo, auditoría y seguridad definidas en ese documento.

El nombre del repositorio tiene variaciones (cripto-tradin-app, crypto-trading-terminal, LAFM), pero el producto principal es Crypto Trading Terminal - LAFM.

---

## 2. Estado real del sistema

<<<<<<< HEAD
Se revisó la estructura del proyecto y su código fuente actual. El sistema presenta estas capacidades funcionales:
=======
```
crypto-trading-app/
├── backend/                    # Python FastAPI + Trading Engine
│   ├── main.py                 # API server + WebSocket + BinanceMarketFeed
│   ├── trading_engine.py       # Paper trading, signals, AI fusion, PnL
│   ├── ai_engine.py            # ONNX inference + heuristic fallback
│   ├── license_manager.py      # HWID + HMAC-SHA256 validation (.env secret)
│   ├── storage.py              # SQLite: trades, positions, snapshots, predictions
│   ├── market_feed.py          # Binance WS + backoff + fallback simulation
│   ├── logger.py               # Structured logging (loguru, 10MB rotation)
│   ├── .env                    # LICENSE_SECRET, FRONTEND_ORIGIN, ports
│   ├── requirements.txt        # onnxruntime, fastapi, pandas-ta, slowapi, loguru
│   └── trading_app.spec        # PyInstaller packaging
├── frontend/                   # React 18 + Vite + Tailwind + Lightweight Charts
│   ├── src/
│   │   ├── components/
│   │   │   ├── CandleChart.jsx       # TradingView-style candlestick chart + drawing tools
│   │   │   ├── HeaderBar.jsx         # Multi-pair selector, ticker, latency, mode toggle
│   │   │   ├── TradingPanel.jsx      # Market/Limit/Stop-Limit/OCO orders + ATR TP/SL
│   │   │   ├── OrderBookWidget.jsx   # Real-time depth chart and order book
│   │   │   ├── AlertsToast.jsx       # Floating notifications with animations
│   │   │   └── Onboarding.jsx        # 4-step animated wizard + API key validation
│   │   ├── App.jsx                   # Auto-login health check, bootstrap, license gate
│   │   ├── store.js                  # Zustand global state
│   │   └── main.jsx                  # React entrypoint
│   ├── .env                    # VITE_API_URL, VITE_WS_URL
│   ├── package.json
│   └── vite.config.js
├── electron/                   # Electron desktop wrapper
│   ├── main.js                 # Spawns backend, lifecycle, updater, hardened webPreferences
│   └── preload.js
├── scripts/
│   ├── generate_license.py     # License generator (HWID-bound)
│   ├── train_ai_model.py       # Train GradientBoosting + export ONNX
│   ├── deploy.ps1              # Automated build + sign + publish
│   └── sign.ps1                # Authenticode signing helper
├── .github/workflows/
│   └── security_audit.yml      # SAST, secret scanning, npm audit, tests gate
├── docs/
│   ├── USER_MANUAL.md          # End-user guide
│   ├── API_KEYS_SECURITY.md    # Zero-knowledge security docs
│   ├── AUTHENTICODE_SETUP.md   # Code signing guide
│   ├── LICENSE_DISTRIBUTION.md # License generation and validation
│   └── PRODUCT_OVERVIEW.md     # Commercial presentation
├── tests/
│   ├── test_trading_engine.py
│   ├── test_license_manager.py
│   └── test_ai_engine.py
├── assets/
│   └── icon.png                # LAFM branding
├── .gitignore
├── package.json                # Root workspace
├── electron-builder.json
├── README.md
├── HANDOFF.md
└── DEPLOYMENT_CHECKLIST.md
```

---

## Technology Stack

- **Frontend:** React 18, Vite, Tailwind CSS 3, Lightweight Charts 4, Framer Motion, Zustand
- **Backend:** FastAPI, Uvicorn, WebSockets, Pandas, Pandas-TA, SQLite, ONNX Runtime
- **Desktop:** Electron 28, electron-builder, PyInstaller
- **Security:** HWID-based licensing with HMAC-SHA256 (secret from `.env`)
- **Testing:** pytest, pytest-asyncio, vitest, testing-library
- **AI/ML:** onnxruntime for CPU inference (no GPU required)
- **Logging:** loguru with 10MB rotation + gzip compression
- **CI/CD:** GitHub Actions with security audit pipeline

---

## Key Features

### Trading Engine
- **Paper Trading & Live Ready** — Start with $10,000 USDT simulation. Switch to live with one toggle.
- **Dual Market Feed** — Binance WebSocket for live ticks, automatic REST cold-start fallback, and simulation fallback for offline operation.
- **Technical Analysis** — EMA(10/30) crossover, RSI(14), MACD(12/26/9), Bollinger Bands, ATR fused into unified signals.
- **AI Enhancement** — ONNX model score (0.0–1.0) combined with technicals for STRONG_BUY / STRONG_SELL signals.
- **Risk Management** — Automatic Take-Profit and Stop-Loss on every position. Real-time unrealized PnL.
- **Trade History** — Complete ledger persisted in SQLite. Heartbeat snapshots every 60s.

### AI & ONNX
- **Local Inference** — `onnxruntime.InferenceSession` with `CPUExecutionProvider`. No cloud API calls.
- **Feature Engineering** — 13 features per candle: OHLCV, RSI, MACD, Bollinger Bands, ATR, EMAs, Log Returns.
- **Training Pipeline** — `scripts/train_ai_model.py` downloads Binance history, computes features, trains GradientBoosting, exports to ONNX.
- **Graceful Degradation** — Heuristic fallback if model file is missing. Never crashes.

### Security & Licensing
- **HWID Binding** — License keys bound to machine fingerprint (motherboard + CPU + MAC + UUID).
- **HMAC-SHA256** — Cryptographic signature prevents tampering. Secret loaded from `.env` only.
- **Local Storage** — API keys encrypted with AES-256-GCM. Stored in `%APPDATA%/LAFM/secure.db`. Never transmitted.
- **Memory Hardening** — API secrets zeroized after decryption to minimize RAM exposure.
- **CORS Restricted** — Backend accepts localhost, Electron packaged origin, and loopback origins via regex.
- **Rate Limiting** — `/api/license/validate` protected at 5 req/min/IP via `slowapi`.
- **Admin API** — Owner can list, issue, revoke, and clear licenses remotely using `ADMIN_API_KEY`.
- **Electron Hardening** — `contextIsolation: true`, `nodeIntegration: false`, restricted navigation.

### Frontend Experience
- **Animated Onboarding** — 4-step guided setup with Framer Motion animations + API key validation.
- **Real-Time Charting** — Lightweight Charts with drawing tools, hotkeys, ATR-based TP/SL suggestions.
- **Order Book & Depth** — Live Binance order book with depth visualization.
- **Resilient Connectivity** — WebSocket reconnection with exponential backoff + jitter. Fetch requests timeout at 10s.
- **Auto-Login** — Silent health check on boot; skips license gate when backend confirms valid license.
- **Notifications** — Floating toast system for AI signals, volatility spikes, and order executions.

### Desktop & Updates
- **Electron Wrapper** — Native Windows experience. Spawns backend process automatically.
- **Auto-Updates** — `electron-updater` checks GitHub Releases silently. Installs on restart.
- **Model Hot-Reload** — `POST /api/model/update` downloads new ONNX models to `%APPDATA%/LAFM/models/` without reinstall.
- **CI/CD Security Audit** — GitHub Actions pipeline with Bandit, Safety, Gitleaks, npm audit, and test gates.

---

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- pip
>>>>>>> origin/feature/v1.0.1-backtest-integration

### Backend
- API REST con FastAPI y CORS configurado.
- WebSocket para streaming de mercado en /ws/market.
- Motor de trading en memoria con soporte para órdenes MARKET, LIMIT, STOP_LIMIT y OCO.
- Cálculo de señales técnicas con EMA, RSI, MACD, bandas Bollinger y ATR.
- Integración de un predictor IA local basado en ONNX con fallback heurístico.
- Persistencia local en SQLite para snapshots, posiciones, historial y predicciones.
- Gestión de licencia por HWID con validación HMAC-SHA256.
- Almacenamiento seguro de claves API con AES-GCM usando identificador hardware como derivación de clave.
- Feed de mercado de Binance con reconexión y fallback a simulación.

### Frontend
- React con Zustand para estado global.
- Pantalla de splash, onboarding y validación de licencia.
- Panel principal con gráfico de velas, ticker, historial, posiciones y ordenes.
- Reconexion automática del WebSocket y polling periódico de candles.
- UI adaptada para mostrar estado de licencia y conexión.

### Electron
- Arranque del backend desde la app desktop.
- Carga de la UI en Vite o dist según modo de ejecución.
- Habilita bloqueo de navegación y ventana principal con parámetros de seguridad.
- Incluye soporte para updates con electron-updater.

---

## 3. Arquitectura del sistema

```text
repo/
├── backend/
│   ├── main.py                 # API REST + WebSocket + startup/shutdown
│   ├── trading_engine.py       # señales, órdenes, PnL, posiciones
│   ├── ai_engine.py            # predictor ONNX + fallback heurístico
│   ├── market_feed.py          # Binance WS + historic fetch + simulación
│   ├── license_manager.py      # HWID + firma HMAC-SHA256
│   ├── secure_storage.py       # AES-GCM para claves y token local
│   ├── storage.py              # SQLite para snapshots y trades
│   ├── logger.py               # logging del sistema
│   ├── requirements.txt        # dependencias Python
│   └── trading_app.spec        # PyInstaller
├── frontend/
│   ├── src/
│   │   ├── App.jsx             # bootstrap, conexión, UI principal
│   │   ├── store.js            # Zustand store
│   │   └── components/         # chart, panel, onboarding, etc.
│   ├── package.json
│   └── vite.config.js
├── electron/
│   ├── main.js                 # launcher desktop + backend lifecycle
│   └── preload.js
├── scripts/
│   ├── generate_license.py     # generación de licencia
│   ├── train_ai_model.py       # entrenamiento y export a ONNX
│   ├── deploy.ps1              # despliegue / publicación
│   └── check-assets.js         # validación de assets del instalador
├── docs/
│   ├── API_KEYS_SECURITY.md
│   ├── AUTHENTICODE_SETUP.md
│   ├── LICENSE_DISTRIBUTION.md
│   ├── PRODUCT_OVERVIEW.md
│   └── USER_MANUAL.md
├── assets/
│   └── icon.png
├── backend/tests/
│   ├── test_ai_engine.py
│   ├── test_license_manager.py
│   └── test_trading_engine.py
├── frontend/tests/
│   ├── App.test.jsx
│   └── packaging.test.js
├── package.json
├── electron-builder.json
├── DEPLOYMENT_CHECKLIST.md
├── HANDOFF.md
├── SYSTEM_FLOW.md
├── README.md
└── .gitignore
```

---

## 4. Flujo principal de funcionamiento

### 4.1 Inicio de la aplicación
1. Electron ejecuta el backend en Python.
2. El backend carga variables de entorno, inicializa FastAPI y la instancia del motor de trading.
3. Se lanza el feed de mercado (Binance WS o simulación).
4. La UI React se conecta a la API REST y al WebSocket.
5. El frontend valida el estado de licencia y muestra bienvenida o onboarding.

### 4.2 Validación de licencia
- El backend calcula un HWID basado en hardware del equipo.
- La clave de licencia se valida con estructura LIC-... y firma HMAC-SHA256.
- Si coincide con el HWID y no está vencida, el sistema la considera válida.
- La validación queda protegida por rate limiting en /api/license/validate.

### 4.3 Feed de mercado
- El backend intenta conectar a Binance vía WebSocket para BTCUSDT.
- Si falla, intenta cargar candles históricos con API REST.
- Si persiste la falla, activa un fallback de simulación con candles artificiales.

### 4.4 Generación de señales
- Se construye un DataFrame con OHLCV y indicadores técnicos.
- Se calculan EMA 10/30, RSI, MACD, BBands y ATR.
- La señal técnica se combina con una predicción local del modelo ONNX.
- El resultado final se expresa como NEUTRAL, BUY, SELL, STRONG_BUY o STRONG_SELL.

### 4.5 Ordenes y contabilidad
- El motor de trading usa posiciones y órdenes en memoria.
- Las posiciones pueden cerrarse por TP/SL o por cross de precio.
- El balance, PnL y snapshots se persisten en SQLite.

---

## 5. Módulos principales

### Backend

#### trading_engine.py
Es el centro del motor. Tiene responsabilidades de:
- mantener balance inicial y balance actual,
- manejar posiciones y trades,
- registrar órdenes,
- calcular señales técnicas,
- fusionar con IA,
- enviar actualizaciones a la UI por WebSocket.

#### ai_engine.py
Implementa el predictor local. Su comportamiento:
- intenta cargar un modelo ONNX desde models/trading_model.onnx,
- usa un fallback heurístico si no existe el modelo o falla la inferencia,
- transforma features para pasar al modelo y normalizar con escalares.

#### market_feed.py
Provee la entrada de mercado en tiempo real desde Binance y tiene resiliencia ante desconexiones. El diseño incluye:
- kline stream por websocket,
- carga histórica por REST,
- fallback de simulación para continuidad del flujo.

#### license_manager.py
Valida la licencia con:
- hardware fingerprint (HWID),
- contenido encoded en base64 del payload,
- expiración y firma HMAC-SHA256.

#### secure_storage.py
Cifra la información sensible usando AES-GCM y una clave derivada del HWID. Esto protege:
- claves API de Binance,
- token de licencia,
- datos locales persistidos en sqlite.

#### storage.py
Base de datos SQLite para:
- snapshots del balance,
- posiciones abiertas,
- trades cerrados,
- historial de predicciones,
- cache de licencia.

### Frontend

#### App.jsx
Es la capa de orquestación de la UI. Realiza:
- salud check del backend,
- validación de licencia,
- conexión WebSocket,
- carga del ticker, mercado y historial,
- operaciones de compra/venta desde paneles de trading.

#### store.js
Mantiene el estado global de la aplicación con Zustand, incluyendo:
- estado de licencia,
- completitud del onboarding,
- conexión del WebSocket,
- errores locales.

#### Componentes principales
- CandleChart: visualización del mercado.
- TradingPanel: ordenes y configuraciones.
- Onboarding: flujo inicial para introducir claves y validarlas.
- HeaderBar: estado del símbolo, conexión y modo de operación.
- OrderBookWidget: profundidad del libro de órdenes.
- AlertsToast: notificaciones.

---

## 6. Seguridad y cumplimiento de principios básicos

El proyecto toma medidas razonables de seguridad local:

- Cifrado local de claves con AES-GCM.
- Licencia vinculada a hardware mediante HWID.
- Firma digital de la licencia con HMAC-SHA256.
- CORS restringido y origen permitido configurable.
- Rate limiting para validación de licencia.
- Electron con contexto aislado y sin Node integrado.

Sin embargo, este tipo de sistema sigue requiriendo control operativo adicional antes de considerarlo producción bancaria o institucional. Lo importante es que, en el repositorio actual, la seguridad base está implementada pero no reemplaza una revisión de seguridad formal.

---

## 7. Dependencias y stack técnico

### Python
- FastAPI
- Uvicorn
- Pandas / Pandas-TA
- NumPy
- ONNX Runtime
- scikit-learn
- PyInstaller
- requests
- slowapi
- python-dotenv
- PyJWT
- Crypto.Cipher (PyCryptodome)

### Frontend
- React 18
- Vite
- Tailwind CSS
- Framer Motion
- Zustand
- lightweight-charts

### Desktop
- Electron
- electron-builder
- electron-updater

---

## 8. Instalación y ejecución

### Requisitos previos
- **Node.js** 18+ (recomendado 20 LTS)
- **Python** 3.10+ (recomendado 3.11/3.12)
- **pip** (incluido con Python)
- **Git** (para clonar el repositorio)
- Acceso a internet (instalación de dependencias y datos de mercado Binance)

Verificación rápida:
```powershell
node --version   # v18+ / v20+
python --version # Python 3.10+
pip --version
```

### 8.1 Clonar e instalar dependencias

```powershell
# Clonar
git clone <URL_DEL_REPOSITORIO> cripto-tradin-app
cd cripto-tradin-app

# Instalar todo (frontend + backend) desde la raíz
npm install
```

`npm install` en la raíz ejecuta `postinstall` que instala dependencias de `frontend/` y `backend/requirements.txt`.

<<<<<<< HEAD
Si prefieres instalación manual por capa:
=======
---

## Production Build (Windows)

```powershell
# 1. Train ONNX model (optional)
cd scripts
python train_ai_model.py

# 2. Build frontend
cd ../frontend
npm run build

# 3. Build backend exe
cd ../backend
pip install -r requirements.txt
python -m PyInstaller trading_app.spec --clean --noconfirm
# Output: backend/dist/trading_app.exe (~145 MB)

# 4. Build Electron installer
cd ..
npm run build:electron
# Output: dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe
```

**Branding Verified:**
- Executable metadata: `CompanyName: LAFM`, `ProductName: Crypto Trading Terminal - LAFM`
- Installer shortcut: `LAFM Trading Terminal`
- ONNX model bundled and loaded automatically

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Health + license status |
| POST | `/api/license/validate` | Validate HWID-bound license |
| GET | `/api/account/balance` | Account summary |
| GET | `/api/account/positions` | Open positions |
| GET | `/api/account/history` | Trade history |
| POST | `/api/trading/order` | Place order (MARKET/LIMIT/STOP_LIMIT/OCO + TP/SL) |
| GET | `/api/trading/signals` | Current signals + AI probability + ATR |
| GET | `/api/market/ticker` | 24h ticker metrics |
| GET | `/api/market/orderbook` | Order book depth |
| POST | `/api/auth/verify-keys` | Validate Binance API keys |
| POST | `/api/model/update` | Download new ONNX model |
| WS | `/ws/market` | Real-time candles + signals |

---

## Order Types Supported

| Type | Description |
|------|-------------|
| MARKET | Immediate execution at current price |
| LIMIT | Execution at specified price or better |
| STOP_LIMIT | Triggered when stop price is hit, then limit order |
| OCO | One-Cancels-the-Other: TP + SL bracket |

---

## License Format

```
LIC-{base64_chunk_8}-{base64_chunk_8}-{...}
```

- Decodes to: `{"hwid": sha256, "exp": iso8601, "sig": hmac_sha256}`
- Bound to machine hardware ID
- Configurable expiration
- Generated via `scripts/generate_license.py`

### Owner Workflow

```powershell
# generate for current machine
cd scripts
python generate_license.py 365

# generate for a friend's machine
python generate_license.py --hwid <FRIEND_HWID> 365
python generate_license.py --hwid <FRIEND_HWID> 30 --note "trial"

# view registry
notepad ../backend/licenses_registry.json
```

### Admin Remote Control API

Set `ADMIN_API_KEY` in `backend/.env`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/admin/licenses` | List issued/revoked licenses |
| POST | `/api/admin/issue` | Issue license for target HWID |
| POST | `/api/admin/revoke` | Revoke license by HWID |
| DELETE | `/api/admin/licenses` | Clear registry |

Headers:
- `X-Admin-Token: <ADMIN_API_KEY>`
- or query param `?admin_token=<ADMIN_API_KEY>`

---




## Testing
>>>>>>> origin/feature/v1.0.1-backtest-integration

```powershell
# Backend
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cd ..

# Frontend
cd frontend
npm install
cd ..
```

### 8.2 Configurar variables de entorno

**Backend** — crear `backend/.env` (no se versiona; ver variables soportadas):

```env
# Modo de operación: PAPER (default) | LIVE | BACKTEST | SIMULATION
TRADING_MODE=PAPER

# Mercado
SYMBOL=BTCUSDT
TIMEFRAME=1m

# Licencia (requerido para validación real; en dev puede omitirse)
LICENSE_SECRET=tu_clave_compartida_segura

# Servidor
PORT=8765
HOST=127.0.0.1

# CORS (orígenes permitidos)
FRONTEND_ORIGIN=http://localhost:3000
EXTRA_CORS_ORIGINS=

# Binance (opcional; defaults funcionan)
BINANCE_WS_URL=wss://stream.binance.com:9443/ws/btcusdt@kline_1m
BINANCE_REST_URL=https://api.binance.com
```

**Frontend** — crear `frontend/.env` si necesitas sobrescribir defaults:

```env
VITE_API_URL=http://127.0.0.1:8765
VITE_WS_URL=ws://127.0.0.1:8765/ws/market
```

> **Seguridad**: nunca commitear `.env` con secretos reales. `LICENSE_SECRET` debe ser una clave fuerte y única en producción.

### 8.3 Ejecutar en desarrollo

Opción A — todo junto desde la raíz (backend + frontend con concurrently):
```powershell
npm run dev
```

Opción B — por separado (útil para depurar):

```powershell
# Terminal 1: Backend
cd backend
.\.venv\Scripts\Activate.ps1   # si usaste venv
uvicorn main:app --reload --host 127.0.0.1 --port 8765

# Terminal 2: Frontend
cd frontend
npm run dev
```

URLs por defecto:
- Frontend (Vite): `http://localhost:3000` o `http://localhost:5173` (según configuración)
- Backend API: `http://127.0.0.1:8765`
- Health check: `http://127.0.0.1:8765/api/health`
- WebSocket mercado: `ws://127.0.0.1:8765/ws/market`

### 8.4 Ejecutar como app desktop (Electron)

```powershell
# Desde la raíz (asegura que frontend/backend deps estén instaladas)
npm install
npx electron .
```

Electron arranca el backend automáticamente (ver `electron/main.js`) y carga la UI.

### 8.5 Ejecutar tests (verificación del entorno)

```powershell
# Backend
cd backend
python -m pytest -q

# Frontend
cd frontend
npm test
```

### 8.6 Notas de operación
- **Modo por defecto es PAPER**. Para LIVE se requiere `TRADING_MODE=LIVE` y un modelo ONNX de producción válido (`backend/models/trading_model.onnx` + artefactos). Sin modelo, LIVE opera en NO_TRADE por seguridad (ver contratos).
- El sistema usa datos de Binance (REST/WS) para mercado; sin conexión puede caer en modos de fallback según configuración del market data layer.
- La licencia se valida por HWID; en desarrollo, el flujo de onboarding/licencia puede requerir generar una clave con `scripts/generate_license.py` (requiere `LICENSE_SECRET` configurado).

---

## 9. Variables de entorno

### Backend
```env
SYMBOL=BTCUSDT
TIMEFRAME=1m
LICENSE_SECRET=tu_clave_compartida
PORT=8765
HOST=127.0.0.1
FRONTEND_ORIGIN=http://localhost:3000
BINANCE_WS_URL=wss://stream.binance.com:9443/ws/btcusdt@kline_1m
EXTRA_CORS_ORIGINS=
```

### Frontend
```env
VITE_API_URL=http://127.0.0.1:8765
VITE_WS_URL=ws://127.0.0.1:8765/ws/market
```

---

## 10. Build, empaquetado y distribución

### Build de frontend
```powershell
cd frontend
npm run build
```

### Build del backend
```powershell
cd backend
pyinstaller trading_app.spec
```

### Build de Electron
```powershell
npm run build:electron
```

El proyecto incluye configuración para la generación de instaladores Windows con Electron Builder.

---

## 11. Estado de pruebas

Última verificación ejecutada:

```powershell
# Backend (235 tests)
cd backend
python -m pytest -q

# Frontend (6 tests)
cd frontend
npm test
```

Resultado verificado:
- **Backend**: `235 passed, 1 warning` (pandas_ta `copy_on_write` deprecation, no afecta funcionalidad)
- **Frontend**: `2 test files, 6 tests passed` (Vitest)

Cobertura por módulo (backend):
- `tests/test_market_data.py` — 128 tests (pipeline market data, providers, validación, dedup, gaps, health)
- `feature_engine/tests/` — 91 tests (indicadores, ventana rolling, validación, look-ahead, determinismo, paridad backtest, safety)
- `tests/test_trading_engine.py` — 7 tests (balance, órdenes, PnL, posiciones, señales)
- `tests/test_ai_engine.py` — tests del predictor IA
- `tests/test_license_manager.py` — tests de licencias HWID/HMAC

---

## 12. Fortalezas del sistema

- Arquitectura modular y clara.
- Separación de responsabilidades entre UI, backend y escritorio.
- Soporte de flujo en tiempo real con Binance.
- Integración local de IA con ONNX.
- Persistencia local de operación y historial.
- Base de licencias y seguridad orientada a usuario local.
- Preparación para entorno desktop Windows.

---

## 13. Limitaciones y riesgos

- **LIVE trading**: el modo LIVE está protegido por contratos (NO_TRADE sin modelo ONNX de producción READY y predicción válida). La ruta de ejecución autónoma completa hasta exchange (Risk Engine/Execution Guard/Order Executor según contratos) no está implementada en este repositorio; `place_order` actual opera en el motor local (paper/simulación).
- **Modelo ONNX**: opcional. Si no está presente en `backend/models/trading_model.onnx`, el predictor usa fallback heurístico y LIVE permanece bloqueado por seguridad.
- **Licencia**: vinculada a HWID; migraciones/reinstalaciones requieren regenerar licencias. `LICENSE_SECRET` debe mantenerse privado.
- **Entorno Windows/Electron**: revisar puertos, permisos y arranque del backend empaquetado en cada release.
- **Validación de producción**: las pruebas actuales cubren módulos clave; falta endurecimiento E2E y pruebas de contrato completas según `docs/TESTING_CONTRACT.md` para una release LIVE.

---

## 14. Recomendaciones de mejora

1. Instalar y dejar el entorno reproducible con requirements + lockfiles.
2. Ejecutar suite real de pruebas y dejar baseline documentado.
3. Revisar consistencia de nombres del proyecto para evitar confusión entre repositorio y producto.
4. Definir política clara de paper trading vs live trading.
5. Añadir validación real de integridad de modelos ONNX y de entorno de distribución.
6. Revisar seguridad operacional antes de usarlo con datos sensibles o claves reales.

---

## 15. Disclaimer

Este proyecto está orientado a análisis, simulación y aprendizaje de trading algorítmico. No debe entenderse como asesoramiento financiero ni como una recomendación para operar con dinero real sin validación adicional del usuario y del entorno técnico.

---

## 16. Conclusión

El repositorio es una terminal local de trading con base de arquitectura modular (FastAPI + React + Electron), pipeline de market data, feature engine, predictor IA con controles de seguridad para LIVE, y persistencia local. Las pruebas automatizadas verificadas (235 backend + 6 frontend) cubren los módulos implementados.

Para una release lista para usuarios finales se recomienda: completar el tutorial de instalación en un entorno limpio, entrenar/proveer un modelo ONNX validado si se usará IA en producción, y continuar con los contratos pendientes (Risk Engine, Execution Guard, auditoría E2E) antes de habilitar trading LIVE real.
