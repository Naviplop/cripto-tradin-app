from sqlalchemy import (
    Column,
    String,
    DateTime,
    Enum,
    Integer,
    func,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime
from database import Base


class LicenseStatus(str, enum.Enum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class PlanType(str, enum.Enum):
    FREE_TRIAL_7D = "FREE_TRIAL_7D"
    SUBSCRIPTION_3M = "SUBSCRIPTION_3M"
    SUBSCRIPTION_6M = "SUBSCRIPTION_6M"
    ANNUAL_1Y = "ANNUAL_1Y"
    LIFETIME = "LIFETIME"


class License(Base):
    __tablename__ = "licenses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    license_key = Column(String(64), unique=True, nullable=False, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    hwid = Column(String(255), nullable=True, index=True)
    hostname = Column(String(255), nullable=True)
    status = Column(Enum(LicenseStatus), nullable=False, default=LicenseStatus.TRIAL)
    plan_type = Column(Enum(PlanType), nullable=False, default=PlanType.FREE_TRIAL_7D)
    max_devices = Column(Integer, nullable=False, default=1)
    hwid_resets_left = Column(Integer, nullable=False, default=3)
    starts_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_revoked = Column(Boolean, nullable=False, default=False)
    revoked_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<License key={self.license_key} status={self.status} "
            f"plan={self.plan_type} expires_at={self.expires_at}>"
        )
