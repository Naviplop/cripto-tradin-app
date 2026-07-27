from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime
from typing import Optional
from models import LicenseStatus, PlanType


class LicenseTrialClaimRequest(BaseModel):
    user_email: EmailStr
    hwid: str = Field(min_length=32, max_length=255)
    hostname: Optional[str] = Field(default=None, max_length=255)


class LicenseActivateRequest(BaseModel):
    license_key: str = Field(min_length=16, max_length=64)
    hwid: str = Field(min_length=32, max_length=255)
    hostname: Optional[str] = Field(default=None, max_length=255)


class LicenseResetHWIDRequest(BaseModel):
    license_key: str = Field(min_length=16, max_length=64)
    hwid: str = Field(min_length=32, max_length=255)
    hostname: Optional[str] = Field(default=None, max_length=255)


class PaymentWebhookEvent(BaseModel):
    event_type: str
    payload: dict


class LicenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    license_key: str
    user_email: str
    status: LicenseStatus
    plan_type: PlanType
    max_devices: int
    hwid_resets_left: int
    starts_at: Optional[datetime] = None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime


class JWTResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    license: LicenseResponse


class ErrorResponse(BaseModel):
    detail: str
