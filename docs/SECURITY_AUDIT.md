# Security Audit - Crypto Trading Terminal - LAFM v1.0.1

## Zero-Knowledge Architecture

All sensitive credentials and license state are deterministically derived from the Hardware ID (HWID). Nothing sensitive is stored in plaintext on disk or transmitted over the network.

- HWID source: Windows API + Python `uuid.getnode()` fallback (denylisted ff:ff:ff:ff:ff:ff).
- License validation: offline HMAC signature using a shared secret (`LICENSE_SECRET`) and HWID-bound expiry timestamp.
- Admin API: protected by `X-Admin-Token` header or query param; token loaded from environment.

## AES-256-GCM Encryption for API Keys

The UUID-based API key storage utilises AES-256-GCM through `cryptography.hazmat`.

- Encode/decode path: `backend/secure_storage.py` -> `_SecurityManager.secure()` / `unsecure()`.
- Keys tied to HWID: encryption context includes machine fingerprint.
- IV/nonce: 12 bytes generated per encrypt, stored alongside ciphertext.
- Zeroization: plaintext API key written once, then zeroed from memory (bytearray scrub).

## Rate Limiting

- `slowapi.Limiter` on FastAPI using `get_remote_address`.
- Limits HTTP request rate per client IP on all API routes.
- WebSocket `/ws/market` lacks rate limiting because it is event-driven; Lantern/IP restrictions required for production.

## Electron Hardening

- Context bridge enabled; Node.js integration disabled (preload only).
- CORS locked to primary frontend origin + extras from config.
- Web contents created without Node integration (`nodeIntegration: false`, `contextIsolation: true`).
- Sensitive paths are blocked in renderer.

## Data Sanitization

- SQLite inputs parameterized via `sqlite3` placeholders.
- HTML/WebSocket payloads do not execute scripts.
- IPC whitelist avoids arbitrary file system access.
- License registry files created only in `%APPDATA%\LAFM`, not executable dirs.

## Supply Chain

- `requirements.txt` pinned where possible.
- `package-lock.json` committed.
- PyInstaller and electron-builder used for packaging; no runtime network downloads.

## Compliance Notes

- No telemetry or analytics in v1.0.1.
- All private keys/API keys remain local unless user explicitly enables remote LLM features.
- Binance WebSocket only reads public market data.
