# Architecture - Crypto Trading Terminal - LAFM v1.0.1

## System Overview

```text
[Electron/React UI]
      |
      | HTTP / WebSocket / REST
      v
[FastAPI Backend]
      |
      | WebSocket stream
      v
[Binance Public API]
```

## Main Components

### Frontend (Electron + React)
- Renderer: React 18 + TypeScript + Vite.
- Charts: TradingView Lightweight Charts v4.x (`CandlestickChart`, `DepthChart`).
- State: Zustand stores (`marketStore`, `tradeStore`, `modelStore`) with WebSocket/reducer hydration.
- IPC: Context bridge (`window.electronAPI`) exposing `startBot`, `updateApiKeys`, `getHwid`.

### Backend (FastAPI)
- `main.py` lifespan: initializes SQLite schema via `storage.initialize_db()`, starts/stops market feed and engine.
- Router groups:
  - `/api/market` - candlestick history, current signals.
  - `/api/trading` - market/limit/oco/stop-limit orders.
  - `/api/account` - balance, trade history, equity curve.
  - `/api/model` - ONNX model metadata, probabilities.
  - `/api/backtest` - backtest execution and metrics.
- Rate limiting: `slowapi` with `get_remote_address` on HTTP endpoints.

### Data Plane
- **Binance WebSocket**: `BinanceMarketFeed` maintains a connection, pushes `Candle` aggregates to `_SimpleEngine._process_tick`.
- **Candles**: persisted in-memory deque (300 ticks) and optionally snapshotted to SQLite via `Storage`.
- **Signals**: technical indicators + ONNX inference score, combined into `STRONG_BUY/BUY/SELL/STRONG_SELL/NEUTRAL`.

### Intelligence
- `ONNXInferenceEngine`: loads `models/trading_model.onnx` + `feature_names.json`.
- Input features: `close`, `volume`, `rsi`, `atr`, `ema_fast`, `ema_slow`, `log_return` (7 features).
- Fallback heuristic when model is missing: price momentum + EMA bias + RSI normalization.

### Persistence
- SQLite via `storage.py` with WAL mode and foreign keys enabled.
- Tables: `account_snapshots`, `positions`, `trade_history`, `market_cache`, `model_metadata`, `event_logs`.
- Connection pooling: `NullPool` in unit tests to avoid Windows file locks.

## Deployment Artifacts

```text
backend/dist/trading_app.exe        = FastAPI backend packed with PyInstaller
frontend/dist                       = Vite static build
dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.1.exe  = Electron installer
```

## Directory Contract

```text
backend/
  config/settings.py                = env vars, CORS, host/port
  domain/                           = entities, events, value objects pure
  infrastructure/                   = AI/ONNX, market data, security, persistence
  presentation/                     = routers, schemas, middlewares
  backtest/                         = data loader, engine, metrics, portfolio
  storage.py                        = raw SQLite repository
  main.py                           = lifespan + router composition root
frontend/
  src/
    application/                    = React contexts and services
    domain/                         = shared types/interfaces
    infrastructure/                 = API clients, WebSocket hooks
    lib/                            = reusable components (OrderBookWidget, etc.)
```

## Runtime Flow

1. Electron app starts FastAPI server via `startBackend()` (child process).
2. Frontend subscribes to `/ws/market`.
3. Backtest runs synchronously in-process using shared schemas.
4. ONNX model inference runs in-process when candle window >= 30.
