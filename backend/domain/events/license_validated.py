from datetime import datetime
from zoneinfo import ZoneInfo

from domain.events.domain_event import DomainEvent


class LicenseValidated(DomainEvent):
    def __init__(self, hwid: str, valid: bool) -> None:
        self.hwid = hwid
        self.valid = valid
        self.occurred_at = datetime.now(ZoneInfo("UTC"))
