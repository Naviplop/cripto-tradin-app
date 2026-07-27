# LAFM Crypto Trading Terminal
## Product Overview & Commercial Presentation

**Version:** 1.0.1  
**Date:** 2026-07-27  
**Company:** LAFM  
**Website:** [configure]  
**Contact:** [configure]

---

## Executive Summary

LAFM Crypto Trading Terminal is a **production-grade, desktop-native algorithmic trading workstation** for Binance. It combines institutional-style technical analysis with local Edge AI inference, wrapped in a polished Electron desktop experience.

Unlike cloud-based bots, LAFM runs **entirely on your machine**:
- **Zero cloud dependencies** for trading logic
- **Zero-knowledge security** — your API keys never leave your PC
- **One-time license** — no recurring subscriptions
- **Resilient by design** — automatic fallbacks for market data, model inference, and connectivity
- **Multi-asset ready** — BTC, ETH, SOL, BNB, XRP support
- **Advanced order types** — Market, Limit, Stop-Limit, OCO
- **Real-time risk management** — ATR-based TP/SL suggestions

**Target Market:** Crypto traders, quants, and small funds who want automated signal generation with full control over their infrastructure and data.

---

## Problem We Solve

| Pain Point | LAFM Solution |
|------------|---------------|
| Cloud bots steal API keys or leak data | Zero-knowledge local architecture. AES-256 encryption. Keys never transmitted. |
| Subscription fatigue ($50–500/mo per bot) | One-time perpetual license bound to your machine. |
| Black-box signals with no explanation | Transparent technical + AI fusion. Every signal is auditable. |
| Internet drop = missed trades / crashed bot | Exponential backoff reconnection + automatic simulation fallback. |
| GPU required for AI trading | ONNX Runtime on CPU. No NVIDIA needed. |
| Complex deployment across multiple machines | Simple license transfer workflow. HWID-bound keys. |

---

## Core Value Propositions

### 1. Edge AI Without the Cloud
- **ONNX Runtime** runs directly on your CPU.
- 13 engineered features per candle: OHLCV, RSI, MACD, Bollinger Bands, ATR, EMAs, Log Returns.
- Trained on real Binance historical data using GradientBoosting.
- Outputs a **0.0–1.0 confidence score** fused with technical analysis for STRONG_BUY / STRONG_SELL signals.
- **Graceful degradation:** heuristic fallback if model is missing. Never crashes.

### 2. Zero-Knowledge Security
- API keys encrypted with **AES-256**.
- Key derivation bound to your **Hardware ID (HWID)**.
- Stored in **local SQLite** (`%APPDATA%/LAFM/secure.db`).
- LAFM servers **never** receive, store, or transmit credentials.
- Binance permissions restricted to **Reading + Spot Trading** only. Withdrawal permanently disabled.

### 3. Resilience & Reliability
- **Dual market feed:** Live Binance WebSocket + REST cold-start fallback + internal simulation fallback.
- If WebSocket drops, the engine keeps running on simulated candles.
- Backend auto-restarts if the process dies.
- WebSocket client uses **exponential backoff + jitter** for reconnection.
- Frontend fetch requests have **10-second timeouts** with loading/error states.

### 4. Professional Desktop Experience
- **Electron wrapper** with native Windows installer (NSIS).
- Animated onboarding flow (Framer Motion).
- Real-time Lightweight Charts (TradingView-grade).
- Auto-updates via `electron-updater` + GitHub Releases.
- Branded installer with LAFM metadata.

---

## Feature Deep Dive

### Trading Engine
| Feature | Detail |
|---------|--------|
| **Modes** | Paper Trading ($10,000 USDT default) / Live Trading |
| **Order Types** | Market, Limit, Stop-Limit, OCO (One-Cancels-the-Other) |
| **Signals** | EMA(10/30) crossover + RSI(14) + MACD(12/26/9) + Bollinger Bands + ATR |
| **AI Fusion** | ONNX score (0.0–1.0) + technicals → STRONG_BUY/BUY/SELL/STRONG_SELL/NEUTRAL |
| **Risk** | Automatic TP/SL on every position. Realized + unrealized PnL tracking. ATR-based suggestions. |
| **Persistence** | SQLite: trades, positions, account snapshots, AI prediction history |
| **Heartbeat** | Account snapshot every 60s for state recovery |

### AI / Machine Learning
| Feature | Detail |
|---------|--------|
| **Model Format** | ONNX (portable, no Python dependency at runtime) |
| **Runtime** | onnxruntime with CPUExecutionProvider |
| **Features** | 13 per candle (OHLCV + RSI + MACD + Bollinger + ATR + EMAs + Log Returns) |
| **Window** | 30 candles → tensor `[1, 30, 8]` |
| **Training** | GradientBoostingClassifier trained on Binance historical klines |
| **Update Path** | `POST /api/model/update` downloads new model to `%APPDATA%/LAFM/models/` |
| **Fallback** | Heuristic momentum/EMA/RSI model if ONNX file is missing |

### Security & Licensing
| Feature | Detail |
|---------|--------|
| **License Binding** | HWID (motherboard + CPU + MAC + UUID) hashed with SHA-256 |
| **License Signing** | HMAC-SHA256 of `{hwid}|{expiry}` with secret from `.env` |
| **Key Storage** | AES-256-GCM encrypted local SQLite + memory zeroization |
| **CORS** | Restricted to `FRONTEND_ORIGIN` |
| **Rate Limiting** | `/api/license/validate` limited to 5 req/min/IP |
| **Electron Hardening** | `contextIsolation: true`, `nodeIntegration: false`, restricted navigation |
| **Distribution** | One-click license generation via `scripts/generate_license.py` |

### Frontend & UX
| Feature | Detail |
|---------|--------|
| **Framework** | React 18 + Vite + Tailwind CSS 3 |
| **Charting** | Lightweight Charts 4 (TradingView-style candles) + drawing tools + hotkeys |
| **Order Book** | Real-time Binance depth chart with liquidity walls |
| **Auto-Login** | Silent health check on boot; skips license gate when valid |
| **Onboarding** | 4-step animated wizard with API key validation (Framer Motion) |
| **Notifications** | Floating toast system for AI signals, volatility, and order executions |
| **Connectivity** | WebSocket with exponential backoff + jitter; fetch with 10s timeout |
| **States** | Loading / error / success states on all API calls |
| **Config** | URLs from `import.meta.env` (Vite) |

### CI/CD & Quality Gates
| Feature | Detail |
|---------|--------|
| **Security Audit** | GitHub Actions with Bandit (Python SAST), Safety (dependencies), Gitleaks (secret scanning) |
| **Frontend Audit** | npm audit, ESLint security rules |
| **Test Gate** | pytest 16/16 + vitest 6/6 as mandatory deployment condition |
| **Deploy Script** | `scripts/deploy.ps1` automates build, sign, and release preparation |

---

## System Architecture (Simplified)

```
┌─────────────────────────────────────────────────────────────┐
│                     Electron Window                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                   React Frontend                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌───────────────┐ │  │
│  │  │   License   │  │   Chart &   │  │   Trading     │ │  │
│  │  │    Gate     │  │  Signals    │  │   Panel       │ │  │
│  │  └─────────────┘  └─────────────┘  └───────────────┘ │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ localhost
┌──────────────────────▼──────────────────────────────────────┐
│              FastAPI Backend (trading_app.exe)               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   License   │  │   Trading   │  │   Market Feed       │ │
│  │  Manager    │  │   Engine    │  │   (Binance WS)      │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │    AI       │  │   Secure    │  │   Storage           │ │
│  │  Predictor  │  │   Storage   │  │   (SQLite)          │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## Target Audience

| Segment | Use Case |
|---------|----------|
| **Crypto Retail Traders** | Automated signal generation with full control. No recurring fees. |
| **Quants & Hobbyists** | Local AI inference, reproducible models, transparent logic. |
| **Small Funds** | Multi-machine license distribution with HWID binding. |
| **Educational Use** | Paper trading with real market data and ONNX inference. |

---

## Competitive Differentiation

| Competitor Type | Typical Limitation | LAFM Advantage |
|-----------------|-------------------|----------------|
| Cloud SaaS bots | API keys sent to server | Zero-knowledge: keys never leave your PC |
| Open-source scripts | Hard to deploy, no UI | Electron desktop app + animated onboarding |
| Signal groups | Manual execution, no automation | Automated TP/SL + real-time PnL |
| AI APIs (OpenAI, etc.) | Recurring costs, latency | Local ONNX inference, one-time license |
| TradingView alerts | No auto-execution | Full order automation with risk guards |

---

## Pricing & Licensing Model

### License Tiers (Example)
| Tier | Price | Features |
|------|-------|----------|
| **Trial** | Free (7 days) | Full features, auto-expire |
| **Personal** | $XXX one-time | 1 machine, 1 year updates, email support |
| **Professional** | $XXX one-time | 3 machines, priority support, custom model training |
| **Enterprise** | Custom | Unlimited seats, white-label, dedicated engineering |

### License Generation Workflow
1. Client sends **HWID** to LAFM.
2. LAFM runs `scripts/generate_license.py` with shared secret.
3. Client receives `LIC-...` key.
4. Client activates in app → instant unlock.

---

## Roadmap

| Phase | ETA | Deliverable |
|-------|-----|-------------|
| **v1.0** | ✅ Done | Core trading engine, ONNX inference, licensing, Electron packaging |
| **v1.1** | Q3 2026 | Real ONNX model trained on 12 months Binance data |
| **v1.2** | Q4 2026 | Multi-asset support (ETH, SOL), portfolio-level risk, advanced charting |
| **v2.0** | 2027 | Strategy marketplace, social copy-trading, web dashboard |

---

## Technical Specifications

### Minimum Requirements
- **OS:** Windows 10/11 (64-bit)
- **CPU:** Dual-core 2.0 GHz (Intel/AMD)
- **RAM:** 4 GB minimum, 8 GB recommended
- **Storage:** 500 MB free space
- **Network:** Broadband for Binance WebSocket/REST

### Recommended Requirements
- **CPU:** Quad-core 3.0 GHz+
- **RAM:** 8 GB+
- **Storage:** SSD with 1 GB free
- **Network:** Stable low-latency connection

### Backend Dependencies
- Python 3.10+ (bundled in executable)
- onnxruntime, fastapi, uvicorn, pandas, pandas-ta, sqlite, loguru

### Frontend Dependencies
- Node.js 18+ (dev only; production served from packaged files)

---

## Security & Compliance

- **Data Residency:** All data stays on the client machine.
- **Encryption:** AES-256 for storage, TLS 1.2+ for Binance connectivity.
- **Auditability:** Full trade log and AI prediction history in SQLite.
- **Open Components:** Core inference engine is ONNX standard — portable and verifiable.

---

## Support & Maintenance

- **Email Support:** support@lafm [configure]
- **Documentation:** `docs/USER_MANUAL.md`, `docs/API_KEYS_SECURITY.md`, `docs/SYSTEM_FLOW.md`
- **Updates:** Automatic via `electron-updater`. Critical patches within 48h.
- **Model Updates:** Quarterly retraining on fresh Binance data available as hot-reload.

---

## Call to Action

**Ready to trade with an AI-native, zero-knowledge desktop terminal?**

- Request a **trial license** at [website/contact]
- Schedule a **demo** for institutional teams
- Download the **evaluation build** for 7-day unrestricted access

**LAFM — Edge AI Trading, Local-First.**
