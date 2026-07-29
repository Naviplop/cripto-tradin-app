from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone


def _get_secret() -> str:
    return os.environ.get("LICENSE_SECRET", "")


def build_license(target_hwid: str, days_valid: int = 365) -> str:
    secret = _get_secret()
    if not secret:
        raise ValueError("LICENSE_SECRET is not configured")
    expiry = (datetime.now(timezone.utc) + timedelta(days=days_valid)).isoformat()
    message = f"{target_hwid}|{expiry}"
    sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    payload = {"hwid": target_hwid, "exp": expiry, "sig": sig}
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    chunks = [payload_b64[i : i + 8] for i in range(0, len(payload_b64), 8)]
    return "LIC-" + "-".join(chunks)


def validate_license_key(license_key: str) -> bool:
    secret = _get_secret()
    if not secret:
        return False
    try:
        parts = license_key.split("-")
        if len(parts) < 4 or parts[0] != "LIC":
            return False
        payload_b64 = "".join(parts[1:])
        padding = (4 - len(payload_b64) % 4) % 4
        payload_b64 += "=" * padding
        payload_json = base64.b64decode(payload_b64).decode()
        payload = json.loads(payload_json)

        stored_hwid = payload.get("hwid", "")
        expiry_str = payload.get("exp", "")
        sig = payload.get("sig", "")

        from infrastructure.security.hwid import get_hardware_id

        if stored_hwid != get_hardware_id():
            return False

        expiry = datetime.fromisoformat(expiry_str)
        if datetime.now(timezone.utc) > expiry:
            return False

        message = f"{stored_hwid}|{expiry_str}"
        expected_sig = hmac.new(
            secret.encode(), message.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return False
        return True
    except Exception:
        return False
