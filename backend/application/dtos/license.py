from pydantic import BaseModel


class LicenseRequestDTO(BaseModel):
    license_key: str


class LicenseResponseDTO(BaseModel):
    valid: bool
    message: str


class LicenseInfoDTO(BaseModel):
    status: str
    license_key: str | None = None
    plan_type: str | None = None
    hwid: str | None = None
    expires_at: str | None = None
    days_left: int | None = None
    message: str | None = None
