# Handoff: Terminal de Trading Cripto — Guía de Continuación para IA

**Proyecto:** `crypto-trading-app`
**Ubicación:** `C:\Users\fijuarez\AppData\Local\Programs\Microsoft VS Code\crypto-trading-app\`
**Generado:** 2026-07-27
**Actualizado:** 2026-07-29
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
| **Empaquetado** | Funcional | Backend EXE `backend/dist/trading_app.exe` e instalador Electron `dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe` generados. |
| **Licencias owner** | Implementado | Admin API `/api/admin/*`, registry local `licenses_registry.json`, generación remota por HWID. |
| **CORS/SSL** | Corregido | Soporta origen `file://`/`null` y context SSL para empaquetado. |
| **Backtest (módulos)** | Parcial | Módulos de motor, métricas, optimización y router creados, pero **no integrados en `main.py`**. |
| **DDD/CQRS layout** | Parcial | Carpetas `domain/`, `application/`, `infrastructure/`, `presentation/`, `config/` creadas con código base, pero `main.py` sigue mixto y no cablea toda la nueva capa. |
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
| **Migración Clean Architecture completa** | `main.py` composition root mixto; routers nuevos no montados; repositorios SQLAlchemy 2.0 ausentes; CQRS parcial | Alta |
| **Backtesting integrado** | Router y motores creados, pero no cableados a API principal ni al dominio | Alta |
| **Cobertura pruebas >90%** | 16/16 básicos; backtest/IA/repositories sin coverage garantizada | Alta |
| **Documentación enterprise** | Faltan USER_MANUAL, SECURITY_AUDIT, ARCHITECTURE, BACKTEST_MANUAL, MLOPS, DEPLOYMENT_ENTERPRISE | Media |
| **Servidor licencias central** | `lafm-license-server` con JWT offline 30 días no implementado | Media |
| **Frontend TypeScript strict** | No migrado; falta arquitectura por capas y docking layout | Media |

---

## 2. Estado de Archivos Clave

### 2.1 Árbol Actual

```
crypto-trading-app/
├── backend/
│   ├── main.py                        # ✅ App FastAPI + WebSocket + BinanceMarketFeed integrado
│   ├── trading_engine.py              # ✅ Paper trading + AI predictor + heartbeat snapshots
│   ├── license_manager.py             # ✅ HWID + HMAC-SHA256 (secreto desde .env)
│   ├── storage.py                     # ✅ SQLite: trades, positions, snapshots, license_cache, predictions
│   ├── ai_engine.py                   # ✅ Motor de inferencia ONNX + fallback heurístico
│   ├── logger.py                      # ✅ Logging estructurado loguru (rotación 10MB, retención 30 días)
│   ├── market_feed.py                 # ✅ Binance WS + reconexión backoff + fallback simulación + SSL
│   ├── backtest/                      # ⚠️ Módulos avanzados creados, no integrados en main.py
│   ├── domain/                        # ⚠️ Entidades/VOs/events/repos ABC creados, imports/contratos incompletos
│   ├── application/                   # ⚠️ Commands/queries/services parciales
│   ├── infrastructure/                # ⚠️ IA/market/security avanzados; falta persistence SQLAlchemy
│   ├── presentation/                  # ⚠️ Routers y middlewares creados, no cableados todos
│   ├── config/                        # ⚠️ Settings y dependencies parciales
│   ├── .env                           # ✅ load_dotenv() en main.py; LICENSE_SECRET, FRONTEND_ORIGIN, etc.
│   ├── requirements.txt               # Dependencias (onnxruntime, numpy, pandas, pytest...)
│   └── trading_app.spec               # ✅ PyInstaller con collect_all(onnxruntime, sklearn, loguru)
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
│   ├── .env                           # ✅ VITE_API_URL, VITE_WS_URL
│   ├── package.json
│   └── vite.config.js
├── electron/
│   ├── main.js                       # ✅ Spawn trading_app.exe, lifecycle limpio, icono fallback
│   └── preload.js
├── scripts/
│   ├── generate_license.py           # ✅ Generador de licencias (LICENSE_SECRET desde .env)
│   ├── train_ai_model.py             # ✅ Entrenamiento y exportación ONNX (GradientBoosting)
│   └── check-assets.js               # ✅ Verifica assets/icon.png previo a build electron
├── build/
│   └── nsis-assets/                  # ✅ Recursos NSIS (vacío, listo para personalizar)
├── assets/
│   └── icon.png                      # ✅ Presente
├── tests/
│   ├── conftest.py                   # Configuración pytest (temp db, event loop)
│   ├── test_trading_engine.py        # 6 tests: PnL, TP/SL, limit orders, snapshots, signals
│   ├── test_license_manager.py       # 5 tests: HWID, valid, wrong HWID, expired, bad format
│   └── test_ai_engine.py             # 4 tests: fallback, bullish bias, bearish bias
├── .gitignore                        # ✅ Creado
├── package.json                      # Root workspace
├── electron-builder.json
├── README.md
├── HANDOFF.md                        # Este archivo
└── docs/
    ├── TECHNICAL_STATUS.md           # Estado técnico completo
    ├── USER_STATUS.md                # Estado para cualquier persona
    ├── PR_SUMMARY.md                 # Resumen de entregas
    ├── LICENSE_DISTRIBUTION.md       # Guía de licencias
    └── API_KEYS_SECURITY.md          # Seguridad y CORS
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

**REST (puerto 8765, CORS restringido a FRONTEND_ORIGIN + localhost + file://):**
- `GET  /api/health` — Incluye `license_valid` y `hwid`
- `POST /api/license/validate` — Valida licencia HWID-bound
- `GET  /api/account/balance` — Resumen de cuenta
- `GET  /api/account/positions` — Posiciones abiertas
- `GET  /api/account/history` — Trades cerrados (limit 1000)
- `POST /api/trading/order` — Colocar orden (MARKET/LIMIT + TP/SL)
- `GET  /api/trading/signals` — Señales técnicas + AI (`combined_signal`, `ai_probability`)
- `GET  /api/market/ticker` — Métricas 24h Binance
- `GET  /api/market/orderbook` — Depth de órdenes
- `GET  /api/market/klines` — Velas históricas por symbol/interval
- `POST /api/auth/verify-keys` — Validación de API keys
- `POST /api/model/update` — Descarga modelo ONNX
- `GET  /api/model/status` — Estado del modelo AI
- `POST /api/config/api-keys` — Guarda API keys
- `GET  /api/config/api-keys` — Lee API keys enmascaradas
- `DELETE /api/config/api-keys` — Elimina API keys
- `GET  /api/admin/licenses` — Lista licencias emitidas/revocadas
- `POST /api/admin/issue` — Emite nueva licencia
- `POST /api/admin/revoke` — Revoca licencia por HWID
- `DELETE /api/admin/licenses` — Limpia registry
- `POST /api/backtest/run` — ⚠️ Existe pero no integrado
- `GET  /api/backtest/result/{run_id}` — ⚠️ Existe pero no integrado
- `POST /api/backtest/optimize` — ⚠️ Existe pero no integrado
- `GET  /api/backtest/metrics/{run_id}` — ⚠️ Existe pero no integrado

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

## 3. Backtesting y Optimización Cuant

### 3.1 Estado actual
- Módulos creados en `backend/backtest/`: `engine.py`, `portfolio.py`, `metrics.py`, `optimization.py`, `data.py`, `api_routes.py`, `schemas.py`.
- Router FastAPI en `/api/backtest/*` existe pero **no está montado en `main.py`**.
- No integrado con dominio/riesgo ni ejecución real.
- Falta alinear contratos Pydantic v2 y corregir imports rotos.

### 3.2 Hace falta
- Integrar router en `main.py`.
- Reutilizar entidades de dominio (`Trade`, `Position`, `Candle`, `Money`).
- Tests unitarios y validación de métricas financieras.

---

## 4. Migración Clean Architecture / DDD / CQRS

### 4.1 Estado actual
- Carpetas base creadas: `backend/domain/`, `application/`, `infrastructure/`, `presentation/`, `config/`.
- Entidades, VOs, eventos, interfaces de repositorio y routers parcialmente implementados.
- `main.py` mantiene composición híbrida; no todos los routers nuevos están montados.
- No hay implementación SQLAlchemy 2.0 ni Unit of Work concreto.

### 4.2 Hace falta
- Convertir `main.py` en composition root limpio con lifespan events.
- Implementar `infrastructure/persistence/sqlalchemy/*` y cablear Unit of Work.
- Montar routers `/api/backtest/*` y completar CQRS handlers.
- Alcanzar cobertura > 90% con pytest.

---

## 5. Deuda Técnica y Problemas Conocidos

| ID | Problema | Ubicación | Solución Sugerida |
|----|----------|-----------|-------------------|
| TD-00 | Bug crítico corregido: espacio en nombre de variable | `backend/market_feed.py:38` | ⚠️ YA CORREGIDO |
| TD-01 | Secreto de licencia hardcodeado | `license_manager.py`, `generate_license.py` | ⚠️ YA CORREGIDO: lee `LICENSE_SECRET` desde `.env` |
| TD-02 | `market_feed.py` NO conectado a `main.py` | `backend/main.py` | ⚠️ YA CORREGIDO: `BinanceMarketFeed` iniciado en `startup_event()` |
| TD-03 | Snapshots de cuenta no se guardan periódicamente | `backend/trading_engine.py`, `backend/storage.py` | ⚠️ YA CORREGIDO |
| TD-04 | CORS abierto a cualquier origen | `backend/main.py` | ⚠️ YA CORREGIDO |
| TD-05 | fetch sin timeout ni estados de carga | `frontend/src/App.jsx` | ⚠️ YA CORREGIDO |
| TD-06 | Reconexión WS fija 3s | `frontend/src/App.jsx` | ⚠️ YA CORREGIDO |
| `datetime.utcnow()` deprecado | Varios archivos | Reemplazar por `datetime.now(timezone.utc)` |
| TD-14 | Faltan pruebas frontend para OrderBook y HeaderBar | `frontend/tests/` | Añadir tests con vitest |
| TD-08 | `start_simulation` sin interruptor de circuito | `backend/trading_engine.py` | Añadir máximo de errores consecutivos |
| TD-09 | Sin rate limiting en endpoints sensibles | `backend/main.py` | ⚠️ YA CORREGIDO |
| TD-10 | Logging estructurado con rotación | Backend | ⚠️ YA CORREGIDO |
| TD-11 | `assets/icon.png` ausente | `assets/icon.png` | ⚠️ YA CORREGIDO |
| TD-12 | Formato licencia corregido | `license_manager.py`, `generate_license.py` | ⚠️ YA CORREGIDO |
| TD-13 | `storage.py` ahora soporta `db_path` personalizado | `backend/storage.py` | ⚠️ YA CORREGIDO |
| ARQ-01 | Migración Clean Architecture incompleta | `backend/main.py`, `domain/**`, `infrastructure/**` | Convertir main.py en composition root + lifespan + SQLAlchemy 2.0 |
| ARQ-02 | Backtest no integrado en API principal | `backend/backtest/api_routes.py` | Montar router en `main.py` y alinear Pydantic v2 |
| ARQ-03 | Faltan tests para backtest, IA multi-modelo, repositories | `backend/tests/` | Ampliar suite para cobertura > 90% |

---

## 6. Lista de Verificación — Estado Real

### 6.1 Completado en esta sesión

| Tarea | Estado |
|-------|--------|
| Integrar `market_feed.py` en `main.py` | ✅ Hecho |
| Persistir snapshots periódicos + `unrealized_pnl` | ✅ Hecho |
| Mover secreto de licencia a `.env` | ✅ Hecho |
| Pruebas pytest básicas | ✅ 16/16 passing |
| CORS restringido + soporte `file://` | ✅ Hecho |
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
| Admin API + registry local licencias | ✅ Hecho |
| SSL context WebSocket para empaquetado | ✅ Hecho |
| Backtest engine + metrics + optimization módulos | ⚠️ Parcial: creados, no integrados |
| Clean Architecture carpetas base | ⚠️ Parcial: estructura creada, no cableada |

### 6.2 Pendiente para Producción Institucional

- [ ] Entrenar y colocar `models/trading_model.onnx` real
- [ ] Completar migración Clean Architecture: `main.py` composition root + lifespan + SQLAlchemy 2.0 + CQRS
- [ ] Integrar router `/api/backtest/*` en `main.py` y alinear Pydantic v2
- [ ] Firma Authenticode del `.exe` y del instalador
- [ ] Publicar release en GitHub Releases
- [ ] Diseño responsivo completo (móvil/tablet)
- [ ] Extender cobertura de tests backend > 90% y agregar tests frontend (vitest)
- [ ] Validar pipeline CI/CD en GitHub Actions
- [ ] Cambiar `ADMIN_API_KEY` en `.env` producción
- [ ]文档 `USER_MANUAL`, `SECURITY_AUDIT`, `ARCHITECTURE`, `BACKTEST_MANUAL`, `MLOPS`, `DEPLOYMENT_ENTERPRISE`
- [ ] Implementar `lafm-license-server` con JWT offline 30 días
- [ ] Migrar frontend a TypeScript strict Clean Architecture
- [ ] Habilitar `asar` en electron-builder

---

## 7. Configuración y Ejecución

### 7.1 Variables de Entorno

**`backend/.env`** (requerido):
```
SYMBOL=BTCUSDT
TIMEFRAME=1m
LICENSE_SECRET=<tu-secreto-compartido-entre-generador-y-validador>
PORT=8765
HOST=127.0.0.1
FRONTEND_ORIGIN=http://localhost:3000
ADMIN_API_KEY=<token-owner>
EXTRA_CORS_ORIGINS=
CORS_REGEX=^http://(localhost|127\.0\.0\.1)(:\d+)?$|^null$
BINANCE_WS_URL=wss://stream.binance.com:9443/ws/btcusdt@kline_1m
```

**`frontend/.env`**:
```
VITE_API_URL=http://127.0.0.1:8765
VITE_WS_URL=ws://127.0.0.1:8765/ws/market
```

### 7.2 Ejecutar en Desarrollo

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

### 7.3 Ejecutar Pruebas

```powershell
cd backend
python -m pytest tests/ -v
# Esperado: 16 passed
```

### 7.4 Construcción Producción (Windows)

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
# Output: backend/dist/trading_app.exe (~141 MB)

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
- `backend/dist/trading_app.exe` existe (~141 MB).
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

### 7.5 Entrenar Modelo ONNX (Recomendado)

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

## 8. Cambios Clave en esta Sesión

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
   - `backend/.env`: actualizado con `FRONTEND_ORIGIN`, `ADMIN_API_KEY`, `EXTRA_CORS_ORIGINS`, `CORS_REGEX`, `BINANCE_WS_URL`.
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

## 9. Guía de Ejecución y Pruebas Locales (Windows)

### 9.1 Compilar Backend (PyInstaller)
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

### 9.2 Compilar Frontend
```powershell
cd frontend
npm run build
```
Validación: `frontend/dist/index.html` existe.

### 9.3 Empaquetar Instalador Electron
```powershell
cd raiz-del-proyecto
npm run build:electron
```
Validaciones:
- `dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe` existe.
- Al instalar y ejecutar:
  1. Electron abre la ventana.
  2. `Task Manager` muestra `trading_app.exe` como proceso hijo de `Crypto Trading Terminal.exe`.
  3. La app carga el frontend compilado desde `frontend/dist/`.
  4. El backend expone `/api/health` en `127.0.0.1:8765`.
  5. License gate valida HWID local contra el secret de `.env`.
  6. WebSocket conecta a `wss://stream.binance.com:9443/ws/btcusdt@kline_1m` y muestra velas en el gráfico.

### 9.4 Verificación de Rutas en Ejecutable
- `get_base_path()` detecta `sys._MEIPASS` en runtime.
- `storage.py` crea `trading.db` en `_MEIPASS/trading_app.db`.
- `logger.py` escribe en `_MEIPASS/logs/app.log`.
- `ai_engine.py` carga `models/trading_model.onnx` desde `_MEIPASS/models/`.

### 9.5 Troubleshooting Común
| Síntoma | Causa probable | Solución |
|---------|----------------|----------|
| Backend no arranca en Electron | `.env` ausente en recursos | Asegurar que `.env` está copiado o variables embebidas |
| Faltan binarios ONNX/LLVM | `trading_app.spec` sin `collect_all` | Recompilar backend |
| Icono no aparece | `assets/icon.png` ausente | Añadir PNG 512x512 o aceptar default |
| Error `ECONNREFUSED` | Backend no inició | Verificar logs de backend en consola de Electron |

---

## 10. Próximos Pasos Recomendados

1. **Corto plazo (producción mínima)**
   - Integrar router backtest en `main.py`.
   - Cambiar `ADMIN_API_KEY` por uno seguro.
   - Entrenar y empaquetar `models/trading_model.onnx`.
   - Publicar release en GitHub y probar auto-update.
   - Firmar `.exe` con Authenticode.

2. **Mediano plazo (institucional)**
   - Completar migración Clean Architecture: composition root limpio, lifespan events, SQLAlchemy 2.0.
   - Alcanzar cobertura backend > 90%.
   - Migrar frontend a TypeScript strict y arquitectura por capas.
   - Documentar arquitectura y flujos.

3. **Largo plazo (escala)**
   - Implementar `lafm-license-server` central con JWT offline.
   - Agregar multi-asset scanner, UI docking, hexagonal widgets.
   - Evaluar modelo Transformer ligero ONNX.

---

## 11. Contacto / Contexto

- **Idioma del prompt original:** Español
- **Razón de stack:** React + Lightweight Charts (ecosistema TradingView). FastAPI (WebSocket asíncrono). ONNX Runtime para inferencia AI ultrarrápida en CPU. PyInstaller + Electron (distribución Windows sin exponer código Python).
- **Modelo de licencia:** Perpetua o con tiempo, vinculada a HWID. Para distribución comercial.
- **Próximo paso recomendado:** Entrenar y desplegar un modelo ONNX real para reemplazar el heurístico, o mejorar el heurístico con más indicadores.

---

*Fin del documento de handoff.*
