from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from domain.events.domain_event import DomainEvent


class OrderFilled(DomainEvent):
    def __init__(self, order_id: str, filled_price: float, quantity: float) -> None:
        self.order_id = order_id
        self.filled_price = filled_price
        self.quantity = quantity
        self.occurred_at = datetime.now(ZoneInfo("UTC"))
