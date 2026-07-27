import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from secure_storage import save_license_token, load_license_token, clear_license_token
from logger import logger

try:
    import jwt
except ImportError:  # pragma: no cover - fallback for environments without PyJWT
    logger.warning("PyJWT not installed; license validation will use offline decoding fallback.")
    jwt = None  # type: ignore


LICENSE_STATUS_VALID = "VALID"
LICENSE_STATUS_WARNING = "WARNING"
LICENSE_STATUS_EXPIRED = "EXPIRED"
LICENSE_STATUS_BLOCKED = "BLOCKED"
LICENSE_STATUS_NONE = "NONE"


class LicenseValidationResult:
    def __init__(
        self,
        status: str,
        license_key: Optional[str] = None,
        plan_type: Optional[str] = None,
        hwid: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        days_left: Optional[int] = None,
        hwid_resets_left: Optional[int] = None,
        max_devices: Optional[int] = None,
        message: Optional[str] = None,
    ):
        self.status = status
        self.license_key = license_key
        self.plan_type = plan_type
        self.hwid = hwid
        self.expires_at = expires_at
        self.days_left = days_left
        self.hwid_resets_left = hwid_resets_left
        self.max_devices = max_devices
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "license_key": self.license_key,
            "plan_type": self.plan_type,
            "hwid": self.hwid,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "days_left": self.days_left,
            "hwid_resets_left": self.hwid_resets_left,
            "max_devices": self.max_devices,
            "message": self.message,
        }


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _get_jwt_secret() -> str:
    import os

    return os.getenv("JWT_SECRET_KEY", "")


def _decode_payload_offline(token: str) -> Dict[str, Any]:
    if jwt:
        try:
            secret = _get_jwt_secret()
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_exp": True},
            )
            return payload
        except Exception as exc:
            logger.error("Offline JWT decode failed: %s", exc)
            raise
    segments = token.split(".")
    if len(segments) != 3:
        raise ValueError("Invalid JWT structure")
    import base64

    try:
        payload_json = base64.urlsafe_b64decode(segments[1] + "==").decode("utf-8")
        payload = json.loads(payload_json)
        return payload
    except Exception as exc:
        logger.error("Offline JWT fallback decode failed: %s", exc)
        raise


def validate_license_token(token: str, grace_days: int = 3) -> LicenseValidationResult:
    if not token:
        return LicenseValidationResult(status=LICENSE_STATUS_NONE, message="License token missing")

    try:
        payload = _decode_payload_offline(token)
    except Exception as exc:
        return LicenseValidationResult(
            status=LICENSE_STATUS_BLOCKED,
            message=f"Invalid or unreadable license token: {exc}",
        )

    exp_ts = payload.get("exp")
    if not exp_ts:
        return LicenseValidationResult(
            status=LICENSE_STATUS_BLOCKED, message="License token missing expiration"
        )

    expires_at = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
    now = _now_utc()
    delta = expires_at - now
    days_left = delta.days

    if delta.total_seconds() <= 0:
        return LicenseValidationResult(
            status=LICENSE_STATUS_EXPIRED,
            license_key=payload.get("sub"),
            plan_type=payload.get("plan_type"),
            hwid=payload.get("hwid"),
            expires_at=expires_at,
            days_left=0,
            message="Subscription expired. Please renew to continue.",
        )

    if days_left <= grace_days:
        return LicenseValidationResult(
            status=LICENSE_STATUS_WARNING,
            license_key=payload.get("sub"),
            plan_type=payload.get("plan_type"),
            hwid=payload.get("hwid"),
            expires_at=expires_at,
            days_left=days_left,
            message=f"Tu suscripción vence en {days_left} día(s). Renueva para mantener las señales de IA activas.",
        )

    return LicenseValidationResult(
        status=LICENSE_STATUS_VALID,
        license_key=payload.get("sub"),
        plan_type=payload.get("plan_type"),
        hwid=payload.get("hwid"),
        expires_at=expires_at,
        days_left=days_left,
        message="License valid",
    )


def get_local_license_status(grace_days: int = 3) -> LicenseValidationResult:
    stored = load_license_token()
    if not stored:
        return LicenseValidationResult(
            status=LICENSE_STATUS_NONE, message="No local license token found"
        )
    return validate_license_token(stored, grace_days=grace_days)


def should_block_trading(grace_days: int = 3) -> bool:
    result = get_local_license_status(grace_days=grace_days)
    return result.status == LICENSE_STATUS_EXPIRED


def persist_license_token(token: str) -> None:
    save_license_token(token)


def clear_local_license() -> None:
    clear_license_token()


def get_copyable_hwid() -> Optional[str]:
    try:
        from license_manager import LicenseManager

        return LicenseManager().get_hardware_id()
    except Exception as exc:
        logger.error("Failed to get HWID for copy: %s", exc)
        return None
