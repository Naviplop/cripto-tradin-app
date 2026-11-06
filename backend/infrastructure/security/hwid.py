from __future__ import annotations

import hashlib
import platform
import subprocess
import uuid


def get_hardware_id() -> str:
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
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).strip().split("\n")[-1].strip()
            components.append(output)
            output = subprocess.check_output(
                ["wmic", "cpu", "get", "processorid"],
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            ).strip().split("\n")[-1].strip()
            components.append(output)
        elif platform.system() == "Darwin":
            output = subprocess.check_output(["ioreg", "-l"], text=True)
            components.append(output)
        elif platform.system() == "Linux":
            output = subprocess.check_output(["cat", "/etc/machine-id"], text=True).strip()
            components.append(output)
    except Exception as exc:
        import logging

        logging.getLogger(__name__).warning("Could not get full HWID: %s", exc)

    raw = "|".join(components)
    hwid_hash = hashlib.sha256(raw.encode()).hexdigest()
    return hwid_hash
