from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from domain.events.domain_event import DomainEvent


class PositionClosed(DomainEvent):
    def __init__(self, position_id: Optional[int], pnl: float, exit_price: float) -> None:
        self.position_id = position_id
        self.pnl = pnl
        self.exit_price = exit_price
        self.occurred_at = datetime.now(ZoneInfo("UTC"))
