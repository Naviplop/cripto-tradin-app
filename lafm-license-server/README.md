# LAFM License Server

Centralized license lifecycle microservice for LAFM Crypto Trading Terminal.

## Architecture

- **Framework:** FastAPI
- **Database:** PostgreSQL (Supabase or self-hosted)
- **Auth:** HMAC-SHA256 JWT (PyJWT)
- **Payments:** Stripe & Gumroad webhooks

## Quick Start

```powershell
cd lafm-license-server
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Supabase DATABASE_URL and JWT_SECRET_KEY
uvicorn main:app --reload --host 0.0.0.0 --port 9000
```

## License Plans

| Plan | Code | Duration |
|------|------|----------|
| Free Trial | `FREE_TRIAL_7D` | 7 days |
| Subscription 3M | `SUBSCRIPTION_3M` | 90 days |
| Subscription 6M | `SUBSCRIPTION_6M` | 180 days |
| Annual 1Y | `ANNUAL_1Y` | 365 days |
| Lifetime | `LIFETIME` | No expiration |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/licenses/trial/claim` | Claim 7-day trial |
| POST | `/v1/licenses/activate` | Activate purchased license |
| POST | `/v1/licenses/reset-hwid` | Reset bound device |
| GET | `/v1/licenses/status/{license_key}` | Get license status |
| POST | `/v1/webhooks/stripe` | Stripe events |
| POST | `/v1/webhooks/gumroad` | Gumroad events |

## Client Integration

The desktop app encodes the JWT locally using `license_client.py`:
- Offline validation via PyJWT
- 3-day grace warning before expiry
- Blocks execution after expiry
- Supports HWID reset with remaining quota check
