import hashlib
import hmac
import json
import os
import platform
import subprocess
import uuid
from datetime import datetime, timedelta
from typing import Optional

from logger import logger

LICENSE_SECRET = os.environ.get("LICENSE_SECRET", "")
if not LICENSE_SECRET:
    logger.warning("LICENSE_SECRET is not set in environment variables.")

class LicenseManager:
    def __init__(self):
        self.hwid = self._get_hardware_id()
        self.valid = False
        self.license_data = None

    def _get_hardware_id(self) -> str:
        components = []
        components.append(platform.node())
        components.append(platform.machine())
        components.append(platform.processor())
        components.append(str(uuid.getnode()))

        try:
            if platform.system() == "Windows":
                output = subprocess.check_output(
                    ["wmic", "baseboard", "get", "serialnumber"],
                    text=True, creationflags=subprocess.CREATE_NO_WINDOW
                ).strip().split("\n")[-1].strip()
                components.append(output)
                output = subprocess.check_output(
                    ["wmic", "cpu", "get", "processorid"],
                    text=True, creationflags=subprocess.CREATE_NO_WINDOW
                ).strip().split("\n")[-1].strip()
                components.append(output)
            elif platform.system() == "Darwin":
                output = subprocess.check_output(["ioreg", "-l"], text=True)
                components.append(output)
            elif platform.system() == "Linux":
                output = subprocess.check_output(["cat", "/etc/machine-id"], text=True).strip()
                components.append(output)
        except Exception as e:
            logger.warning(f"Could not get full HWID: {e}")

        raw = "|".join(components)
        hwid_hash = hashlib.sha256(raw.encode()).hexdigest()
        return hwid_hash

    def get_hardware_id(self) -> str:
        return self.hwid

    def validate(self, license_key: str) -> bool:
        try:
            parts = license_key.split("-")
            if len(parts) < 4 or parts[0] != "LIC":
                return False
            payload_b64 = "".join(parts[1:])
            padding = (4 - len(payload_b64) % 4) % 4
            payload_b64 += "=" * padding
            import base64
            payload_json = base64.b64decode(payload_b64).decode()
            payload = json.loads(payload_json)

            stored_hwid = payload.get("hwid", "")
            expiry_str = payload.get("exp", "")
            sig = payload.get("sig", "")

            if stored_hwid != self.hwid:
                logger.warning("License HWID mismatch")
                return False

            expiry = datetime.fromisoformat(expiry_str)
            if datetime.utcnow() > expiry:
                logger.warning("License expired")
                return False

            message = f"{stored_hwid}|{expiry_str}"
            expected_sig = hmac.new(
                LICENSE_SECRET.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()

            if not hmac.compare_digest(sig, expected_sig):
                logger.warning("Invalid license signature")
                return False

            self.valid = True
            self.license_data = payload
            logger.info("License validated successfully")
            return True
        except Exception as e:
            logger.error(f"License validation error: {e}")
            return False

    def is_valid(self) -> bool:
        return self.valid

    def get_license_info(self) -> Optional[dict]:
        if not self.license_data:
            return None
        return {
            "hwid": self.license_data.get("hwid"),
            "expiry": self.license_data.get("exp"),
            "valid": self.valid,
        }
