from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from domain.events.domain_event import DomainEvent


class OrderPlaced(DomainEvent):
    def __init__(self, order_id: str, side: str, order_type: str, quantity: float, price: Optional[float] = None) -> None:
        self.order_id = order_id
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.occurred_at = datetime.now(ZoneInfo("UTC"))
