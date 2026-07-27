import hmac
import hashlib
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    jwt_secret_key: str = "change-me-super-secret-key"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 43200
    lafm_issuer: str = "LAFM-LICENSE-SERVER"
    allowed_hwid_resets: int = 3

    class Config:
        env_prefix = ""
        env_file = ".env"
        extra = "ignore"


settings = Settings()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_license_key(prefix: str, parts: int = 3, part_len: int = 4) -> str:
    alphabet = string.ascii_uppercase + string.digits
    segments = [prefix]
    for _ in range(parts):
        chunk = "".join(secrets.choice(alphabet) for _ in range(part_len))
        segments.append(chunk)
    return "-".join(segments)


def build_expiration(plan_type: str, starts_at: Optional[datetime] = None) -> datetime:
    base = starts_at if starts_at else _now_utc()
    mapping = {
        "FREE_TRIAL_7D": timedelta(days=7),
        "SUBSCRIPTION_3M": timedelta(days=90),
        "SUBSCRIPTION_6M": timedelta(days=180),
        "ANNUAL_1Y": timedelta(days=365),
        "LIFETIME": None,
    }
    delta = mapping.get(plan_type)
    if plan_type == "LIFETIME":
        return datetime.max.replace(tzinfo=timezone.utc)
    if delta is None:
        raise ValueError(f"Unsupported plan_type: {plan_type}")
    return base + delta


def sign_jwt(license_key: str, plan_type: str, hwid: str, expires_at: datetime) -> str:
    now = _now_utc()
    payload = {
        "iss": settings.lafm_issuer,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "sub": license_key,
        "plan_type": plan_type,
        "hwid": hwid,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def verify_jwt(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            issuer=settings.lafm_issuer,
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("License token expired")
    except jwt.InvalidIssuerError:
        raise ValueError("Invalid issuer")
    except jwt.InvalidSignatureError:
        raise ValueError("Invalid signature")
    except Exception as exc:
        raise ValueError(f"Invalid token: {exc}")


def mask_hwid(hwid: str) -> str:
    if not hwid or len(hwid) <= 8:
        return "****"
    return hwid[:4] + "****" + hwid[-4:]
