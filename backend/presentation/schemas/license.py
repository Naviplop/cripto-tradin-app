from pydantic import BaseModel


class LicenseRequest(BaseModel):
    license_key: str


class LicenseResponse(BaseModel):
    valid: bool
    message: str


class AdminIssueRequest(BaseModel):
    target_hwid: str
    days_valid: int = 365
    note: str = ""


class AdminRevokeRequest(BaseModel):
    target_hwid: str
    reason: str = ""
