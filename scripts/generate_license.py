#!/usr/bin/env python3
import json
import hashlib
import hmac
import base64
import os
import sys
import uuid
import platform
import subprocess
from datetime import datetime, timedelta, timezone


def find_dotenv() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in [
        os.path.join(here, "..", "backend", ".env"),
        os.path.join(here, "..", ".env"),
        os.path.join(here, ".env"),
    ]:
        if os.path.isfile(candidate):
            return os.path.abspath(candidate)
    raise FileNotFoundError(".env not found next to scripts/ or backend/")


def load_dotenv(path: str):
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if key and key not in os.environ:
                os.environ[key] = value


try:
    dotenv_path = find_dotenv()
    load_dotenv(dotenv_path)
except Exception as e:
    print(f"WARNING: cannot load .env ({e}).")
    print("Set LICENSE_SECRET manually in the environment before generating licenses.")

SECRET_KEY = os.environ.get("LICENSE_SECRET", "")
if not SECRET_KEY:
    print("ERROR: LICENSE_SECRET is not set.")
    sys.exit(1)


def get_hardware_id():
    components = []
    components.append(platform.node())
    components.append(platform.machine())
    components.append(platform.processor())
    components.append(str(uuid.getnode()))
    try:
        if platform.system() == "Windows":
            output = subprocess.check_output(
                ["wmic", "baseboard", "get", "serialnumber"],
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).strip().split("\n")[-1].strip()
            components.append(output)

            output = subprocess.check_output(
                ["wmic", "cpu", "get", "processorid"],
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            ).strip().split("\n")[-1].strip()
            components.append(output)
    except Exception as e:
        print(f"Warning: {e}")
    raw = "|".join(components)
    return hashlib.sha256(raw.encode()).hexdigest()


def generate_license(days_valid: int = 365, target_hwid: str = None, note: str = ""):
    hwid = target_hwid if target_hwid is not None else get_hardware_id()
    expiry = (datetime.now(timezone.utc) + timedelta(days=days_valid)).isoformat()
    message = f"{hwid}|{expiry}"
    sig = hmac.new(SECRET_KEY.encode(), message.encode(), hashlib.sha256).hexdigest()
    payload = {"hwid": hwid, "exp": expiry, "sig": sig}
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    chunk_size = 8
    chunks = [payload_b64[i : i + chunk_size] for i in range(0, len(payload_b64), chunk_size)]
    license_key = "LIC-" + "-".join(chunks)
    print(f"Hardware ID: {hwid}")
    print(f"License Key: {license_key}")
    print(f"Expiry: {expiry}")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "license.lic")
    with open(out, "w") as f:
        f.write(license_key)
    print(f"License saved to {out}")

    registry = {
        "licenses": [],
        "revoked": [],
    }
    registry_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend", "licenses_registry.json")
    if os.path.isfile(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except Exception:
            pass
    record = {
        "key": license_key,
        "hwid": hwid,
        "days_valid": days_valid,
        "note": note,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    registry.setdefault("licenses", []).append(record)
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    print(f"Registry updated at {registry_path}")


if __name__ == "__main__":
    args = sys.argv[1:]
    target_hwid = None
    note = ""
    if "--hwid" in args:
        idx = args.index("--hwid")
        target_hwid = args[idx + 1]
        del args[idx:idx + 2]
    if "--note" in args:
        idx = args.index("--note")
        note = args[idx + 1] if idx + 1 < len(args) else ""
        del args[idx:idx + 2]
    days = int(args[0]) if args else 365
    generate_license(days, target_hwid, note)
