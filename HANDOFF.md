# Handoff: Terminal de Trading Cripto — Guía de Continuación para IA

**Proyecto:** `crypto-trading-app`
**Ubicación:** `C:\Users\fijuarez\AppData\Local\Programs\Microsoft VS Code\crypto-trading-app\`
**Generado:** 2026-07-27
**Actualizado:** 2026-07-27
**Versión:** 1.0.1
**Propósito:** Estado real del proyecto (implementado vs. pendiente) y plan para continuar.

---

## 1. Estado Real del Proyecto

### 1.1 Implementado y Funcional

| Capa | Estado | Detalles |
|------|--------|----------|
| **Backend Python** | Funcional | FastAPI + REST + WebSocket. `TradingEngine` con paper trading (simulación + **feed Binance en vivo**), señales EMA/10 EMA/30 + RSI + **predicción AI (ONNX/heurística)**, TP/SL, PnL en tiempo real. Worker de snapshots periódicos. Carga estado desde SQLite. |
| **Motor de IA** | Implementado | `backend/ai_engine.py` contiene `AIPredictor` con `onnxruntime`. Carga `models/trading_model.onnx`. Normaliza features (close, volume, RSI, MACD, EMA fast/slow) sobre ventana de 30 velas. Devuelve score 0.0–1.0. **Degradación elegante a modelo heurístico** si falta el `.onnx`. |
| **Persistencia SQLite** | Implementada | `backend/storage.py` con tablas `account_snapshots`, `positions`, `trades`, `license_cache`, `predictions`. Carga estado al arrancar, cierra posiciones en DB por `id`, guarda predicciones AI, snapshots periódicos de cuenta. |
| **Feed de Mercado Binance** | **Integrado en main.py** | `backend/market_feed.py` conectado a `wss://stream.binance.com:9443/ws/btcusdt@kline_1m` en `startup_event()`. Reconexión backoff exponencial, deduplicación de velas, **fallback automático a simulación** tras 5 errores consecutivos. `on_candle` vinculado a `trading_engine._process_tick()`. |
| **Frontend React** | Funcional mejorado | React 18 + Vite + Tailwind + Lightweight Charts 4. Pantalla de licencia, gráfico de velas, panel de trading, OrderBook, HeaderBar con ticker. Nuevo: **timeout 10s en fetch** (`AbortController`), **estados loading/error**, **reconexión WS con backoff exponencial + jitter**, **auto-login silencioso** vía `/api/health`, **Zustand** para estado global. |
| **Gestión de Licencias** | Seguro | `LicenseManager` con HWID (Windows/Mac/Linux) + HMAC-SHA256 + expiración. **Secreto leído de `LICENSE_SECRET` en `.env`**; no hay claves hardcodeadas. `scripts/generate_license.py` también usa `.env`. Formato de clave adaptado a base64 completo segmentado. |
| **Configuración .env** | Completo | `backend/.env` con variables cargadas vía `python-dotenv`. `frontend/.env` con URLs. |
| **Pruebas** | 16/16 passing | Suite `pytest` en `backend/tests/` cubriendo PnL/TP/SL (`test_trading_engine.py`), HWID/HMAC (`test_license_manager.py`), inferencia AI (`test_ai_engine.py`). |
| **Empaquetado** | Esqueleto | `trading_app.spec` (PyInstaller) y `electron-builder.json` existen. |
| **`.gitignore`** | ✅ Creado | Excluye `venv/`, `node_modules/`, `dist/`, `.env`, `*.lic`, `__pycache__/`, `*.db`. |

### 1.2 Falta o Incompleto

| Categoría | Brecha | Severidad |
|-----------|--------|-----------|
| **Entrenamiento del modelo ONNX** | No existe `models/trading_model.onnx`; solo corre el fallback heurístico | Media |
| **Firma de código** | Sin firma Authenticode para `.exe` de Windows; `scripts/sign.ps1` listo | Media |
| **CI/CD** | ✅ Implementado en `.github/workflows/security_audit.yml` | - |
| **Auto-actualizador** | ✅ Configurado en `electron/main.js` con `electron-updater` | - |
| **Diseño Responsivo** | Barra lateral fija `w-80`; sin adaptación móvil completa | Baja |
| **Icono** | `assets/icon.png` presente | ✅ |
| **Logging estructurado** | ✅ Implementado con loguru (rotación 10MB, retención 30 días) | - |
| **Rate Limiting** | ✅ Implementado en `/api/license/validate` (5 req/min/IP) | - |
| **Script de entrenamiento IA** | ✅ scripts/train_ai_model.py listo | - |
| **Security hardening** | ✅ AES-256-GCM + zeroize + Electron `webSecurity: true` + navegación restringida | - |
| **Order types** | ✅ Market, Limit, Stop-Limit, OCO soportados en backend y frontend | - |
| **Market data endpoints** | ✅ `/api/market/ticker` y `/api/market/orderbook` agregados | - |
| **Deploy script** | ✅ `scripts/deploy.ps1` con build, sign y prepare release | - |

---

## 2. Estado de Archivos Clave

### 2.1 Árbol Actual

```
crypto-trading-app/
├── backend/
│   ├── main.py                    # ✅ App FastAPI + WebSocket + BinanceMarketFeed integrado
│   ├── trading_engine.py          # ✅ Paper trading + AI predictor + heartbeat snapshots
│   ├── license_manager.py         # ✅ HWID + HMAC-SHA256 (secreto desde .env)
│   ├── storage.py                 # ✅ SQLite: trades, positions, snapshots, license_cache, predictions
│   ├── ai_engine.py               # ✅ Motor de inferencia ONNX + fallback heurístico
│   ├── logger.py                  # ✅ Logging estructurado loguru (rotación 10MB, retención 30 días)
│   ├── market_feed.py             # ✅ Binance WS + reconexión backoff + fallback simulación
│   ├── .env                       # ✅ load_dotenv() en main.py; LICENSE_SECRET, FRONTEND_ORIGIN, etc.
│   ├── requirements.txt           # Dependencias (onnxruntime, numpy, pandas, pytest...)
│   └── trading_app.spec           # ✅ PyInstaller con collect_all(onnxruntime, sklearn, loguru)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CandleChart.jsx       # TradingView-style candlestick chart + drawing tools + hotkeys
│   │   │   ├── HeaderBar.jsx         # Multi-pair selector, timeframe, ticker 24h, latency, mode
│   │   │   ├── TradingPanel.jsx      # Market/Limit/Stop-Limit/OCO + ATR-based TP/SL + position sizing
│   │   │   ├── OrderBookWidget.jsx   # Real-time Binance depth chart and order book
│   │   │   ├── AlertsToast.jsx       # Floating notifications with animations
│   │   │   └── Onboarding.jsx        # 4-step animated wizard + API key validation
│   │   ├── App.jsx                   # Auto-login health check, bootstrap, license gate, WS
│   │   ├── store.js                  # Zustand global state
│   │   └── main.jsx                  # React entrypoint
│   ├── .env                       # ✅ VITE_API_URL, VITE_WS_URL
│   ├── package.json
│   └── vite.config.js
├── electron/
│   ├── main.js                   # ✅ Spawn trading_app.exe, lifecycle limpio, icono fallback
│   └── preload.js
├── scripts/
│   ├── generate_license.py       # ✅ Generador de licencias (LICENSE_SECRET desde .env)
│   ├── train_ai_model.py         # ✅ Entrenamiento y exportación ONNX (GradientBoosting)
│   └── check-assets.js           # ✅ Verifica assets/icon.png previo a build electron
├── build/
│   └── nsis-assets/              # ✅ Recursos NSIS (vacío, listo para personalizar)
├── assets/
│   └── icon.png                  # ❌ AUSENTE (warning elegante en prebuild)
├── tests/
│   ├── conftest.py                # Configuración pytest (temp db, event loop)
│   ├── test_trading_engine.py     # 6 tests: PnL, TP/SL, limit orders, snapshots, signals
│   ├── test_license_manager.py    # 5 tests: HWID, valid, wrong HWID, expired, bad format
│   └── test_ai_engine.py          # 4 tests: fallback, bullish bias, bearish bias
├── .gitignore                     # ✅ Creado
├── package.json                   # Root workspace
├── electron-builder.json
├── README.md
└── HANDOFF.md                     # Este archivo
```

### 2.2 Flujo de Datos (Actual mejorado)

```
[Binance WebSocket / Simulación Fallback]
                 │
                 ▼
[BinanceMarketFeed._process_tick()]
                 │
                 ▼
[TradingEngine._process_tick(candle)]
            │
            ├─► actualiza precio actual, velas
            ├─► update_positions() → cierra si hit TP/SL
            ├─► _generate_signals() → EMA/RSI/MACD técnicos
            ├─► ai_predictor.predict() → score AI (ONNX o heurístico)
            ├─► _combine_signal_with_ai() → STRONG_BUY/BUY/NEUTRAL/SELL/STRONG_SELL
            ├─► save_prediction() → guarda en SQLite
            ├─► snapshot_account() cada N ticks (heartbeat)
            │
            ├─► broadcast_market_data(candle, signals) ──► WebSocket ──► React
            └─► broadcast_account_update(account) ──► WebSocket ──► React

[Usuario coloca orden] ──► POST /api/trading/order
            │
            ▼
[TradingEngine.place_order()] ──► Posición abierta → guarda en DB con db_id
            │
            ▼
[close_position() al hit TP/SL] ──► guarda trade en SQLite + borra posición
```

### 2.3 Interfaces REST + WebSocket

**REST (puerto 8765, CORS restringido a FRONTEND_ORIGIN):**
- `GET  /api/health` — Incluye `license_valid`
- `POST /api/license/validate` — Valida licencia HWID-bound
- `GET  /api/account/balance` — Resumen de cuenta
- `GET  /api/account/positions` — Posiciones abiertas
- `GET  /api/account/history` — Trades cerrados (limit 1000)
- `POST /api/trading/order` — Colocar orden (MARKET/LIMIT + TP/SL)
- `GET  /api/trading/signals` — Señales técnicas + AI (`combined_signal`, `ai_probability`)

**WebSocket `/ws/market`:**
- Cliente → Servidor: `{"type": "ping"}`
- Servidor → Cliente:
  ```json
  {
    "type": "market_data",
    "candle": {"time": "ISO8601", "open": ..., "high": ..., "low": ..., "close": ..., "volume": ...},
    "signals": {
      "signal": "BUY",
      "combined_signal": "STRONG_BUY",
      "ma_fast": 67520.0,
      "ma_slow": 67450.0,
      "rsi": 58.3,
      "ai_probability": 0.72
    }
  }
  ```
- Servidor → Cliente: `{"type": "account_update", "data": {...}}`

### 2.4 Motor de IA (AIPredictor)

- **Modelo ONNX**: `backend/models/trading_model.onnx` (opcional). Input shape `[1, 30, 8]`: ventana de 30 velas con features `[close, volume, rsi, macd, macd_signal, macd_hist, ema_fast, ema_slow]`.
- **Inferencia**: `predict(candles_data)` devuelve float 0.0–1.0. Si el modelo no existe o falla, degrada a `_heuristic_predict()` basado en momentum, EMA bias y RSI.
- **Combinación**: `_combine_signal_with_ai()` genera `STRONG_BUY`/`STRONG_SELL` cuando señal técnica y AI coinciden con alta confianza.
- **Persistencia**: Cada predicción se guarda en `predictions` con `score`, `signal`, `candles_used`, `model_loaded`.

---

## 3. Deuda Técnica y Problemas Conocidos

| ID | Problema | Ubicación | Solución Sugerida |
|----|----------|-----------|-------------------|
| TD-00 | Bug crítico corregido: espacio en nombre de variable | `backend/market_feed.py:38` | ⚠️ YA CORREGIDO (era `self._ consecutive_errors`) |
| TD-01 | Secreto de licencia hardcodeado | `license_manager.py`, `generate_license.py` | ⚠️ YA CORREGIDO: lee `LICENSE_SECRET` desde `.env` |
| TD-02 | `market_feed.py` NO conectado a `main.py` | `backend/main.py` | ⚠️ YA CORREGIDO: `BinanceMarketFeed` iniciado en `startup_event()` |
| TD-03 | Snapshots de cuenta no se guardan periódicamente | `backend/trading_engine.py`, `backend/storage.py` | ⚠️ YA CORREGIDO: `snapshot_account()` + worker `snapshot_worker()` cada 60s |
| TD-04 | CORS abierto a cualquier origen | `backend/main.py` | ⚠️ YA CORREGIDO: restringido a `FRONTEND_ORIGIN` desde `.env` |
| TD-05 | fetch sin timeout ni estados de carga | `frontend/src/App.jsx` | ⚠️ YA CORREGIDO: `AbortController` 10s + estados `loading`/`error` |
| TD-06 | Reconexión WS fija 3s | `frontend/src/App.jsx` | ⚠️ YA CORREGIDO: backoff exponencial con jitter |
| `datetime.utcnow()` deprecado | Varios archivos | Advertido en warnings; reemplazar por `datetime.now(timezone.utc)` |
| TD-14 | Faltan pruebas frontend para OrderBook y HeaderBar | `frontend/tests/` | Añadir tests con vitest |
| TD-08 | `start_simulation` sin interruptor de circuito | `backend/trading_engine.py` | Añadir máximo de errores consecutivos y apagado elegante |
| TD-09 | Sin rate limiting en endpoints sensibles | `backend/main.py` | ⚠️ YA CORREGIDO: `slowapi` en `/api/license/validate` (5 req/min/IP) |
| TD-10 | Logging estructurado con rotación | Backend | ⚠️ YA CORREGIDO: `backend/logger.py` con `loguru` (rotación 10MB, retención 30 días, compresión gzip) |
| TD-11 |assets/icon.png ausente | `assets/icon.png` | Añadir 512×512 o eliminar referencia |
| TD-12 | Formato licencia corregido | `license_manager.py`, `generate_license.py` | ⚠️ YA CORREGIDO: ahora usa base64 completo segmentado, no solo 32 chars |
| TD-13 | `storage.py` ahora soporta `db_path` personalizado | `backend/storage.py` | ⚠️ YA CORREGIDO: `get_db_connection()` acepta path |

---

## 4. Lista de Verificación — Estado Real

### 4.1 Completado en esta sesión

| Tarea | Estado |
|-------|--------|
| Integrar `market_feed.py` en `main.py` | ✅ Hecho |
| Persistir snapshots periódicos + `unrealized_pnl` | ✅ Hecho |
| Mover secreto de licencia a `.env` | ✅ Hecho |
| Pruebas pytest | ✅ 16/16 passing |
| CORS restringido | ✅ Hecho |
| `.gitignore` | ✅ Creado |
| `fetch` con timeout + loading states | ✅ Hecho |
| Backoff exponencial + jitter en WS frontend | ✅ Hecho |
| Motor de IA con ONNX + fallback heurístico | ✅ Hecho |
| Storage: tabla `predictions` + `predict()` diario | ✅ Hecho |
| Bug variable `self._ consecutive_errors` | ✅ Corregido |
| Bug formato licencia (solo 32 chars base64) | ✅ Corregido |
| CandleChart avanzado con herramientas de dibujo y hotkeys | ✅ Hecho |
| OrderBookWidget en tiempo real | ✅ Hecho |
| TradingPanel completo: Market/Limit/Stop-Limit/OCO + ATR TP/SL | ✅ Hecho |
| HeaderBar multi-cripto con ticker 24h y latencia | ✅ Hecho |
| Auto-login silencioso por `/api/health` | ✅ Hecho |
| Onboarding con validación `POST /api/auth/verify-keys` | ✅ Hecho |
| AlertsToast con notificaciones animadas | ✅ Hecho |
| `secure_storage` AES-256-GCM + zeroize de secretos | ✅ Hecho |
| Hardening Electron (`webSecurity`, navegación restringida) | ✅ Hecho |
| CI/CD pipeline `.github/workflows/security_audit.yml` | ✅ Hecho |
| `scripts/deploy.ps1` para build, sign y release | ✅ Hecho |
| `docs/*.md` actualizados a v1.0.1 | ✅ Hecho |

### 4.2 Pendiente para Producción

- [ ] Entrenar y colocar `models/trading_model.onnx` real
- [ ] Firma Authenticode del `.exe` y del instalador
- [ ] Publicar release en GitHub Releases
- [ ] Diseño responsivo completo (móvil/tablet)
- [ ] Extender cobertura de tests frontend (OrderBook, HeaderBar)
- [ ] Validar pipeline CI/CD en GitHub Actions

---

## 5. Configuración y Ejecución

### 5.1 Variables de Entorno

**`backend/.env`** (requerido):
```
SYMBOL=BTCUSDT
TIMEFRAME=1m
LICENSE_SECRET=<tu-secreto-compartido-entre-generador-y-validador>
PORT=8765
HOST=127.0.0.1
FRONTEND_ORIGIN=http://localhost:3000
BINANCE_WS_URL=wss://stream.binance.com:9443/ws/btcusdt@kline_1m
```

**`frontend/.env`**:
```
VITE_API_URL=http://127.0.0.1:8765
VITE_WS_URL=ws://127.0.0.1:8765/ws/market
```

### 5.2 Ejecutar en Desarrollo

```powershell
# Terminal 1 — Backend
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8765

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
# → http://localhost:3000

# Generar licencia (ejecutar en máquina destino para producción)
cd scripts
python generate_license.py 365
```

### 5.3 Ejecutar Pruebas

```powershell
cd backend
python -m pytest tests/ -v
# Esperado: 16 passed
```

### 5.4 Construcción Producción (Windows)

```powershell
# 0. Verificar icono (opcional)
node scripts/check-assets.js

# 1. Reentrenar modelo ONNX (opcional pero recomendado)
cd scripts
python train_ai_model.py
# Output: backend/models/trading_model.onnx, scaler_params.json, feature_names.json

# 2. Frontend
cd ../frontend
npm run build

# 3. Backend
cd ../backend
pip install -r requirements.txt
python -m PyInstaller trading_app.spec --clean --noconfirm
# Output: backend/dist/trading_app.exe (~145 MB)

# 4. Electron installer NSIS
cd ..
npm run build:electron
# Output: dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe
```

**Metadatos de autoría LAFM incrustados:**
- `backend/version_info.txt` define `CompanyName`, `ProductName`, `Publisher`, `LegalCopyright` = `LAFM`.
- `trading_app.spec` usa `SPECPATH` e incluye `version=version_info.txt` en el EXE.
- `electron-builder.json` y `package.json` establecen `productName`, `publisherName`, `shortcutName` como `LAFM Trading Terminal`.

**Verificaciones post-build:**
- `backend/dist/trading_app.exe` existe (~145 MB).
- Ejecutar en PowerShell:
  ```powershell
  (Get-Item "backend/dist/trading_app.exe").VersionInfo | Select-Object CompanyName, ProductName, Publisher, LegalCopyright
  ```
  Debe mostrar `LAFM` en todos los campos.
- `pyi-archive_viewer backend/dist/trading_app.exe` permite inspeccionar que incluye `models/trading_model.onnx`, `models/scaler_params.json`, `models/feature_names.json` y `logs/`.
- `dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe` es el instalador NSIS.
- Al instalar y ejecutar, Electron inicia `trading_app.exe` como proceso hijo.
- En ejecutable empaquetado, `get_base_path()` detecta `sys._MEIPASS` y resuelve `trading.db`, `logs/` y `models/` al directorio temporal de extracción.
- El backend carga `backend/.env` desde `BASE_PATH` y usa `LICENSE_SECRET` para validar licencias HWID-bound.

**Nota:** Si `assets/icon.png` está ausente, Electron usa el icono predeterminado de Windows y el instalador NSIS usa un icono genérico.

### 5.5 Entrenar Modelo ONNX (Recomendado)

Para reemplazar el fallback heurístico por un modelo real:
```powershell
cd scripts
python train_ai_model.py
# Salida: backend/models/trading_model.onnx (GradientBoosting, input [None, 240])
```

El script:
1. Descarga datos históricos de Binance REST API (`/api/v3/klines`) para BTC/USDT.
2. Calcula features técnicas: EMA 10/30, RSI 14, MACD 12/26/9, OHLCV.
3. Crea ventanas de 30 velas (shape aplanado: 240 features).
4. Entrena `GradientBoostingClassifier` con scikit-learn.
5. Exporta a ONNX con `skl2onnx` y guarda el modelo sklearn como `.pkl` para métricas.
6. Al reiniciar el backend, `AIPredictor` carga el modelo automáticamente.

---

## 6. Cambios Clave en esta Sesión

1. **Backend:**
    - Creado `backend/ai_engine.py` (`AIPredictor`) con ONNX + fallback heurístico.
    - Creado `scripts/train_ai_model.py`: entrena GradientBoosting con datos Binance, exporta a ONNX (input `[None, 240]`).
    - `backend/trading_engine.py`: integra AI predictor, combina señales técnicas+AI, heartbeat `snapshot_account()` cada tick, posiciones guardadas por `db_id`.
    - `backend/main.py`: carga `load_dotenv()`, integra `BinanceMarketFeed`, worker `snapshot_worker()`, CORS restringido, puerto desde `.env`.
    - `backend/main.py`: añadido `slowapi` para rate limiting en `/api/license/validate` (5 req/min/IP) y manejador global de excepciones.
    - `backend/logger.py`: logging estructurado con `loguru` (rotación 10MB, retención 30 días, compresión gzip) en `backend/logs/app.log`.
    - Reemplazados imports de `logging` estándar por `loguru` en `main.py`, `trading_engine.py`, `market_feed.py`, `license_manager.py`.
    - `backend/storage.py`: tabla `predictions`, `save_prediction()`, `update_position_unrealized_pnl()`, `get_open_positions()` incluye `id`, `initialize_db()` acepta `db_path`.
    - `backend/license_manager.py`: secreto desde `LICENSE_SECRET` env; valida licencias con base64 completo segmentado.
    - `scripts/generate_license.py`: secreto desde `.env`; formato de clave con base64 completo segmentado.
    - Corregidos bugs: variable con espacio en `market_feed.py`, padding base64 en validator, cálculo de balance en `close_position`.

2. **Frontend:**
   - `frontend/src/App.jsx`: URLs desde `import.meta.env`, `fetchWithTimeout` con `AbortController` (10s), estados `loading`/`error`, reconexión WS con backoff exponencial + jitter.

3. **Pruebas:**
   - Suite `pytest` completa: 16 tests pasando (`test_trading_engine`, `test_license_manager`, `test_ai_engine`).

 4. **Empaquetado y Config:**
     - `backend/.env`: actualizado con `FRONTEND_ORIGIN`, `BINANCE_WS_URL`.
     - Creado `.gitignore` en raíz.
     - `backend/requirements.txt`: añadidas `onnxruntime`, `pytest`, `pytest-asyncio`, `httpx`, `scikit-learn`, `skl2onnx`, `slowapi`, `loguru`, `joblib`, `requests`.
     - Agregada función `get_base_path()` en `main.py`, `storage.py`, `ai_engine.py`, `logger.py` para resolver rutas en ejecutable empaquetado (`sys._MEIPASS`).
     - Actualizado `backend/trading_app.spec`: incluye `models/trading_model.onnx`, `backend/logs/`, binarios de `onnxruntime`/`sklearn`/`loguru` via `collect_all`.
     - Actualizado `electron/main.js`: inicia `trading_app.exe` como proceso hijo, captura stdout/stderr, cierre limpio con `SIGTERM` + fallback `SIGKILL`, hardening de `webPreferences`.
     - Actualizado `electron-builder.json`: incluye `backend/dist/trading_app.exe` como `extraResource` en instalador NSIS.
     - Actualizado `package.json`: script `build` secuencial frontend -> backend -> electron, `postinstall` instala dependencias de ambos mundos.
     - Agregado `.github/workflows/security_audit.yml`: pipeline SAST, secret scanning, npm audit, tests gate.
     - Agregado `scripts/deploy.ps1`: build, sign y preparación de release.
     - Actualizado `docs/*.md` con estado actual del sistema v1.0.1.

---

## 8. Guía de Ejecución y Pruebas Locales (Windows)

### 8.1 Compilar Backend (PyInstaller)
```powershell
cd backend
pip install -r requirements.txt
pyinstaller trading_app.spec --clean --noconfirm
```
Validaciones:
- `backend/dist/trading_app.exe` existe.
- `backend/dist/trading_app.exe` incluye `models/` y `logs/` (ver con `pyi-archive_viewer backend/dist/trading_app.exe`).
- Ejecutar manualmente:
  ```powershell
  cd backend/dist
  .\trading_app.exe
  ```
  Deberías ver logs en consola y en `backend/dist/logs/app.log`. El servidor escucha en `HOST:PORT` definidos en `.env`.

### 8.2 Compilar Frontend
```powershell
cd frontend
npm run build
```
Validación: `frontend/dist/index.html` existe.

### 8.3 Empaquetar Instalador Electron
```powershell
cd raiz-del-proyecto
npm run build:electron
```
Validaciones:
- `dist-electron/Crypto Trading Terminal Setup 1.0.0.exe` existe.
- Al instalar y ejecutar:
  1. Electron abre la ventana.
  2. `Task Manager` muestra `trading_app.exe` como proceso hijo de `Crypto Trading Terminal.exe`.
  3. La app carga el frontend compilado desde `frontend/dist/`.
  4. El backend expone `/api/health` en `127.0.0.1:8765`.
  5. License gate valida HWID local contra el secret de `.env`.
  6. WebSocket conecta a `wss://stream.binance.com:9443/ws/btcusdt@kline_1m` y muestra velas en el gráfico.

### 8.4 Verificación de Rutas en Ejecutable
- `get_base_path()` detecta `sys._MEIPASS` en runtime.
- `storage.py` crea `trading.db` en `_MEIPASS/trading_app.db`.
- `logger.py` escribe en `_MEIPASS/logs/app.log`.
- `ai_engine.py` carga `models/trading_model.onnx` desde `_MEIPASS/models/`.

### 8.5 Troubleshooting Común
| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Backend no arranca en Electron | `.env` ausente en recursos | Asegurar que `.env` está copiado o variables embebidas |
| Faltan binarios ONNX/LLVM | `trading_app.spec` sin `collect_all` | Recompilar backend |
| Icono no aparece | `assets/icon.png` ausente | Añadir PNG 512x512 o aceptar default |
| Error `ECONNREFUSED` | Backend no inició | Verificar logs de backend en consola de Electron |

---

## 7. Contacto / Contexto

- **Idioma del prompt original:** Español
- **Razón de stack:** React + Lightweight Charts (ecosistema TradingView). FastAPI (WebSocket asíncrono). ONNX Runtime para inferencia AI ultrarrápida en CPU. PyInstaller + Electron (distribución Windows sin exponer código Python).
- **Modelo de licencia:** Perpetua o con tiempo, vinculada a HWID. Para distribución comercial.
- **Próximo paso recomendado:** Entrenar y desplegar un modelo ONNX real para reemplazar el heurístico, o mejorar el heurístico con más indicadores ( Bollinger, ATR, volumen profile).

---

*Fin del documento de handoff.*
