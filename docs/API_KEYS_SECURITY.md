# API Keys & Security Architecture

## Zero-Knowledge Local Storage

Your API credentials are encrypted locally using AES-256 with a key derived from your machine's Hardware ID (HWID). Keys are stored in a secure SQLite database at `%APPDATA%/LAFM/secure.db`.

**LAFM servers never receive, store, or transmit your API credentials.**

### Encryption Details
- **Algorithm:** AES-256-CBC
- **Key Derivation:** HMAC-SHA256(HWID, "LAFM-SECURE-KEY")
- **Storage:** SQLite with encrypted blobs
- **Scope:** Local machine only

---

## Required Binance Permissions

When creating your API Key in Binance, enable **ONLY**:

- **Enable Reading**
- **Enable Spot & Margin Trading**

**NEVER enable:**
- **Withdrawal**
- **Spot & Margin Trading** without Reading

If Withdrawal permissions are enabled, your funds are at risk even if the application is compromised.

---

## Paper Trading Mode

The application ships with a default Paper Trading mode that does not require real API credentials.

- Simulated balance: $10,000 USDT
- Real-time ONNX inference
- Full technical signal generation and order simulation
- Live Binance market data without exchange credentials
- No trading fees or slippage simulation

Enable **Paper Trading** in Settings to test the Edge AI system before connecting live credentials.

---

## Network Security

The desktop application communicates exclusively with:
- `http://127.0.0.1:8765` (REST API)
- `ws://127.0.0.1:8765/ws/market` (WebSocket)

The bundled Python backend handles all exchange interactions locally.  
**No external LAFM servers are contacted during trading operations.**

### Backend CORS Policy
- Only origins listed in `FRONTEND_ORIGIN` are permitted.
- Credentials are allowed only from the configured frontend origin.
- Rate limiting applied to sensitive endpoints (`/api/license/validate`: 5 req/min/IP).

---

## Hardware ID (HWID)

The license system binds keys to a unique hardware fingerprint composed of:
- Hostname
- CPU architecture
- Processor name
- MAC address
- Motherboard serial number (Windows)
- CPU processor ID (Windows)

This fingerprint is hashed with SHA-256 and never transmitted in plaintext.

---

## License Signing

Licenses are signed using HMAC-SHA256:
- **Message:** `{hwid}|{expiry_iso8601}`
- **Secret:** Loaded from `LICENSE_SECRET` environment variable (`.env`)
- **Validation:** Constant-time comparison prevents timing attacks

---

## Logging & Auditing

- Structured logs via `loguru` with 10MB rotation and 30-day retention.
- All license validation attempts are logged.
- API key operations are logged with masked values.
- No sensitive data is written to logs.

---

## Incident Response

If you suspect credential exposure:
1. Immediately revoke the API key in Binance.
2. Delete `%APPDATA%/LAFM/secure.db`.
3. Restart the application and re-enter credentials.
4. Contact LAFM support if you need a new license for a different machine.
