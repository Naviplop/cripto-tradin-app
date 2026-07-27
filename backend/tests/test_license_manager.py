import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from license_manager import LicenseManager


os.environ.setdefault("LICENSE_SECRET", "test-secret-key")


def test_hwid_is_consistent():
    mgr = LicenseManager()
    hwid1 = mgr.get_hardware_id()
    hwid2 = mgr.get_hardware_id()
    assert hwid1 == hwid2
    assert len(hwid1) == 64


def _build_license(hwid, days_valid=365):
    secret = os.environ.get("LICENSE_SECRET", "")
    expiry = (datetime.now(timezone.utc) + timedelta(days=days_valid)).isoformat()
    message = f"{hwid}|{expiry}"
    sig = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    payload = {"hwid": hwid, "exp": expiry, "sig": sig}
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    chunk_size = 8
    chunks = [payload_b64[i:i + chunk_size] for i in range(0, len(payload_b64), chunk_size)]
    return "LIC-" + "-".join(chunks)


def test_valid_license():
    mgr = LicenseManager()
    hwid = mgr.get_hardware_id()
    key = _build_license(hwid, days_valid=365)
    assert mgr.validate(key) is True
    assert mgr.is_valid() is True


def test_wrong_hwid_license():
    mgr = LicenseManager()
    fake_hwid = "0" * 64
    key = _build_license(fake_hwid, days_valid=365)
    assert mgr.validate(key) is False
    assert mgr.is_valid() is False


def test_expired_license():
    mgr = LicenseManager()
    hwid = mgr.get_hardware_id()
    key = _build_license(hwid, days_valid=-1)
    assert mgr.validate(key) is False


def test_invalid_format():
    mgr = LicenseManager()
    assert mgr.validate("BAD-KEY") is False
    assert mgr.validate("LIC-TOO-SHORT") is False
