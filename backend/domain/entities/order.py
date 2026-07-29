from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from dataclasses import dataclass, field as dc_field

from domain.value_objects.leverage import Leverage
from domain.value_objects.money import Money
from domain.value_objects.order_side import OrderSide
from domain.value_objects.order_status import OrderStatus
from domain.value_objects.order_type import OrderType
from domain.value_objects.time_in_force import TimeInForce


def _utcnow() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


@dataclass
class Order:
    id: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[Money] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_price: Optional[Money] = None
    timestamp: datetime = dc_field(default_factory=_utcnow)
    time_in_force: TimeInForce = TimeInForce.GTC
    leverage: Optional[Leverage] = None

    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    def can_cancel(self) -> bool:
        return self.status in (OrderStatus.PENDING, OrderStatus.PARTIALLY_FILLED)

    def mark_filled(self, filled_price: Money) -> None:
        if not self.can_cancel():
            raise ValueError("Cannot fill a terminal order")
        self.status = OrderStatus.FILLED
        self.filled_price = filled_price
