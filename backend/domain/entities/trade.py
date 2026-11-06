from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from dataclasses import dataclass, field as dc_field

from domain.value_objects.money import Money
from domain.value_objects.order_side import OrderSide


def _utcnow() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


@dataclass
class Trade:
    id: str
    side: OrderSide
    entry_price: Money
    exit_price: Money
    quantity: float
    pnl: Money
    timestamp: datetime = dc_field(default_factory=_utcnow)
    fees: Money = dc_field(default_factory=lambda: Money(0, "USDT"))

    def net_pnl(self) -> Money:
        return self.pnl - self.fees
