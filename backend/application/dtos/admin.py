from pydantic import BaseModel


class AdminIssueRequestDTO(BaseModel):
    target_hwid: str
    days_valid: int = 365
    note: str = ""


class AdminRevokeRequestDTO(BaseModel):
    target_hwid: str
    reason: str = ""
