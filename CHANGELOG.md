# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v1.0.1] - 2026-07-29

### Added
- Enterprise-grade security baseline: AES-256-GCM vault for API keys bound to HWID.
- Zero-knowledge license validation: offline HMAC signatures with time-window expiry.
- Backtesting router formally mounted at `/api/backtest` in FastAPI lifespan with SQLite schema initialization on startup and graceful shutdown of market feed + engine.
- Windows hardening: SQLAlchemy `NullPool` for tests, retry-based teardown to prevent `.db` file locks.
- Comprehensive test suite expansion: 184 green tests covering trading engine, legacy AI predictor, domain entities/events/value objects, and backtest integration.
- Domain modeling layer: entities, value objects (`Money`, `Leverage`, `RiskParams`), domain events, repository interfaces.
- Infrastructure layer: ONNX inference wrapper, model registry, feature engineering, training helpers.
- Backtest engine: event-driven and vectorized execution, slippage/latency models, metrics calculator, portfolio simulation.

### Changed
- TradingView Lightweight Charts migration to v4.x schemas in React components.
- OrderBookWidget enriched with real-time depth metrics (spread, cumulative volume).
- Test coverage baseline set at 55% threshold with `.coveragerc` policy; current measured coverage: **77.82%**.
- `Money` value object enriched with rich comparison operators (`>`, `>=`, `<`, `<=`) enabling `Account.withdraw()` guards.
- `secure_storage.py` moved to `infrastructure/security/` package with updated zero-knowledge flow.

### Fixed
- Deterministic Windows pytest teardown for SQLite (`tests/conftest.py` retry logic).
- ONNX feature vector alignment: dropped unstable MACD/Bollinger columns (NaN-producing) in stable training pipeline.
- Missing imports in `domain/entities`, `storage`, and `trading_engine` after layering refactor.

### Removed
- Synthetic data fallback from ONNX training script; pipeline requires real Binance BTCUSDT 1m kline download.
- Legacy direct SQLite mutations outside `storage.py` gateway.

## [v1.0.0] - 2026-06-15

### Added
- Initial release of Crypto Trading Terminal - LAFM.
- Live Binance data via WebSocket.
- FastAPI backend with CORS, rate limiting, and admin API.
- Electron frontend with TradingView charts, Order Book Widget, HWID-bound licenses.
- ONNX model inference with AIPredictor fallback.
- Local SQLite persistence for trades and account snapshots.
