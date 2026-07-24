# Crypto Trading Terminal - LAFM

**Algorithmic Crypto Trading & Paper Trading Desktop Application for Binance BTC/USDT.**
**Author: LAFM**

> **Status:** Production-ready backend & license system.  
> **Last updated:** 2026-07-24

---

## Why LAFM Crypto Trading Terminal?

LAFM is not just another trading bot. It is a **local-first, AI-augmented trading workstation** designed for traders who demand performance, security, and control.  
No cloud dependencies. No monthly subscriptions. No black boxes.

- **Edge AI Inference** — ONNX Runtime runs directly on your CPU for ultra-low latency predictions.
- **Zero-Knowledge Security** — Your API keys never leave your machine. AES-256 + HWID-bound encryption.
- **License Control** — HMAC-SHA256 signed licenses bound to hardware ID. Distribute with confidence.
- **Dual Market Feed** — Live Binance WebSocket with automatic simulation fallback. Never miss a tick.
- **Desktop-Grade UX** — Electron wrapper with animated onboarding, real-time charts, and seamless updates.

---

## Architecture Overview

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
│   │   │   ├── Chart.jsx       # TradingView-style candlestick chart
│   │   │   └── TradingPanel.jsx # Order entry + account summary
│   │   ├── App.jsx             # License gate + WS backoff + fetch timeout
│   │   └── main.jsx
│   ├── .env                    # VITE_API_URL, VITE_WS_URL
│   ├── package.json
│   └── vite.config.js
├── electron/                   # Electron desktop wrapper
│   ├── main.js                 # Spawns backend, lifecycle, updater
│   └── preload.js
├── scripts/
│   ├── generate_license.py     # License generator (HWID-bound)
│   ├── train_ai_model.py       # Train GradientBoosting + export ONNX
│   └── deploy.ps1              # Automated build + sign + publish
├── docs/
│   ├── USER_MANUAL.md          # End-user guide
│   ├── API_KEYS_SECURITY.md    # Zero-knowledge security docs
│   └── SYSTEM_FLOW.md          # Complete system flow diagrams
├── tests/
│   ├── test_trading_engine.py
│   ├── test_license_manager.py
│   └── test_ai_engine.py
├── assets/
│   └── icon.png                # ⚠️ Add 512x512 for production branding
├── .gitignore
├── package.json                # Root workspace
├── electron-builder.json
├── README.md
├── HANDOFF.md
└── DEPLOYMENT_CHECKLIST.md
```

---

## Technology Stack

- **Frontend:** React 18, Vite, Tailwind CSS 3, Lightweight Charts 4
- **Backend:** FastAPI, Uvicorn, WebSockets, Pandas, Pandas-TA, SQLite, ONNX Runtime
- **Desktop:** Electron 28, electron-builder, PyInstaller
- **Security:** HWID-based licensing with HMAC-SHA256 (secret from `.env`)
- **Testing:** pytest, pytest-asyncio, httpx
- **AI/ML:** onnxruntime for CPU inference (no GPU required)
- **Logging:** loguru with 10MB rotation + gzip compression

---

## Key Features

### Trading Engine
- **Paper Trading & Live Ready** — Start with $10,000 USDT simulation. Switch to live with one toggle.
- **Dual Market Feed** — Binance WebSocket for live ticks, automatic REST cold-start fallback, and simulation fallback for offline operation.
- **Technical Analysis** — EMA(10/30) crossover, RSI(14), MACD(12/26/9) fused into unified signals.
- **AI Enhancement** — ONNX model score (0.0–1.0) combined with technicals for STRONG_BUY / STRONG_SELL signals.
- **Risk Management** — Automatic Take-Profit and Stop-Loss on every position. Real-time unrealized PnL.
- **Trade History** — Complete ledger persisted in SQLite. Heartbeat snapshots every 60s.

### AI & ONNX
- **Local Inference** — `onnxruntime.InferenceSession` with `CPUExecutionProvider`. No cloud API calls.
- **Feature Engineering** — 13 features per candle: OHLCV, RSI, MACD, Bollinger Bands, ATR, EMAs, Log Returns.
- **Training Pipeline** — `scripts/train_ai_model.py` downloads Binance history, computes features, trains GradientBoosting, exports to ONNX.
- **Graceful Degradation** — Heuristic fallback if model file is missing. Never crashes.

### Security & Licensing
- **HWID Binding** — License keys bound to machine fingerprint ( motherboard + CPU + MAC + UUID ).
- **HMAC-SHA256** — Cryptographic signature prevents tampering. Secret loaded from `.env` only.
- **Local Storage** — API keys encrypted with AES-256. Stored in `%APPDATA%/LAFM/secure.db`. Never transmitted.
- **CORS Restricted** — Backend only accepts requests from configured `FRONTEND_ORIGIN`.
- **Rate Limiting** — `/api/license/validate` protected at 5 req/min/IP via `slowapi`.

### Frontend Experience
- **Animated Onboarding** — 4-step guided setup with Framer Motion animations.
- **Real-Time Charting** — Lightweight Charts with overlaid signals and AI probability.
- **Resilient Connectivity** — WebSocket reconnection with exponential backoff + jitter. Fetch requests timeout at 10s.
- **License Gate** — Clean activation screen. Paste key or load `.lic` file.
- **Paper Trading Toggle** — Switch between simulation and live in Settings.

### Desktop & Updates
- **Electron Wrapper** — Native Windows experience. Spawns backend process automatically.
- **Auto-Updates** — `electron-updater` checks GitHub Releases silently. Installs on restart.
- **Model Hot-Reload** — `POST /api/model/update` downloads new ONNX models to `%APPDATA%/LAFM/models/` without reinstall.

---

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.10+
- pip

### Backend
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8765
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Generate License
```powershell
cd scripts
python generate_license.py 365
```

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
# Output: dist-electron/Crypto Trading Terminal - LAFM Setup 1.0.0.exe
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
| POST | `/api/trading/order` | Place order (MARKET/LIMIT + TP/SL) |
| GET | `/api/trading/signals` | Current signals + AI probability |
| POST | `/api/model/update` | Download new ONNX model |
| WS | `/ws/market` | Real-time candles + signals |

---

## License Format

```
LIC-{base64_chunk_8}-{base64_chunk_8}-{...}
```

- Decodes to: `{"hwid": sha256, "exp": iso8601, "sig": hmac_sha256}`
- Bound to machine hardware ID
- Configurable expiration
- Generated via `scripts/generate_license.py`

---

## Testing

```powershell
cd backend
python -m pytest tests/ -v
# Expected: 16 passed
```

Coverage:
- TradingEngine PnL, TP/SL, limit orders, snapshots, signals
- LicenseManager HWID, validation, expiry, format
- AIPredictor fallback, bullish/bearish bias

---

## Configuration

### Backend `.env`
```
SYMBOL=BTCUSDT
TIMEFRAME=1m
LICENSE_SECRET=<your-shared-secret>
PORT=8765
HOST=127.0.0.1
FRONTEND_ORIGIN=http://localhost:3000
BINANCE_WS_URL=wss://stream.binance.com:9443/ws/btcusdt@kline_1m
```

### Frontend `.env`
```
VITE_API_URL=http://127.0.0.1:8765
VITE_WS_URL=ws://127.0.0.1:8765/ws/market
```

---

## Security Architecture

See [`docs/API_KEYS_SECURITY.md`](docs/API_KEYS_SECURITY.md) for:
- AES-256 local encryption keyed by HWID
- Binance permission restrictions (Reading + Spot Trading only)
- Zero-knowledge model: LAFM servers never touch credentials

See [`docs/USER_MANUAL.md`](docs/USER_MANUAL.md) for:
- Binance API key setup walkthrough
- Signal interpretation guide
- FAQ: privacy, connectivity, model updates

---

## Deployment

See [`DEPLOYMENT_CHECKLIST.md`](DEPLOYMENT_CHECKLIST.md) for:
- Automated pipeline (`scripts/deploy.ps1`)
- Code signing with Authenticode
- GitHub Releases publication
- Post-release verification checklist

See [`HANDOFF.md`](HANDOFF.md) for:
- Complete development handoff guide
- File tree and data flow
- Known issues and technical debt
- Troubleshooting

See [`SYSTEM_FLOW.md`](SYSTEM_FLOW.md) for:
- End-to-end flow diagrams
- License distribution workflow
- Runtime sequence diagrams

---

## Disclaimer

This is a **paper trading simulation** application. No real funds are used unless explicitly configured with live exchange credentials. For educational purposes only. Not financial advice.

---

## Contact

**LAFM**  
For enterprise licensing, custom model training, or support: contact LAFM.
