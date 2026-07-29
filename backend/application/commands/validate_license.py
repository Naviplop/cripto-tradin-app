from __future__ import annotations

from typing import List

from domain.events.license_validated import LicenseValidated
from domain.repositories.interfaces import ILicenseRepository


class ValidateLicenseCommand:
    def __init__(self, license_key: str) -> None:
        self.license_key = license_key
        self.valid: bool = False
        self.message: str = ""
        self.error: str | None = None
        self.events: List[LicenseValidated] = []


class ValidateLicenseHandler:
    def __init__(self, license_repo: ILicenseRepository) -> None:
        self._license_repo = license_repo

    async def handle(self, command: ValidateLicenseCommand) -> bool:
        from infrastructure.security.license_crypto import validate_license_key

        hwid = "unknown"
        valid = validate_license_key(command.license_key)
        if valid:
            command.valid = True
            command.message = "License valid"
        else:
            command.valid = False
            command.message = "Invalid or expired license"
        command.events.append(LicenseValidated(hwid, command.valid))
        self._license_repo.save_state(hwid, command.license_key, valid, None)
        return command.valid
