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
class Position:
    id: Optional[int]
    side: OrderSide
    entry_price: Money
    quantity: float
    unrealized_pnl: Money = dc_field(default_factory=lambda: Money(0, "USDT"))
    tp: Optional[Money] = None
    sl: Optional[Money] = None
    timestamp: datetime = dc_field(default_factory=_utcnow)
    closed_at: Optional[datetime] = None
    close_price: Optional[Money] = None
    realized_pnl: Optional[Money] = None

    def is_open(self) -> bool:
        return self.closed_at is None

    def close(self, exit_price: Money) -> Money:
        if not self.is_open():
            raise ValueError("Position is already closed")
        self.closed_at = _utcnow()
        self.close_price = exit_price
        if self.side == OrderSide.BUY:
            pnl = (exit_price - self.entry_price) * self.quantity
        else:
            pnl = (self.entry_price - exit_price) * self.quantity
        self.realized_pnl = pnl
        return pnl

    def update_unrealized_pnl(self, current_price: Money) -> Money:
        if not self.is_open():
            return self.realized_pnl or Money(0, "USDT")
        if self.side == OrderSide.BUY:
            pnl = (current_price - self.entry_price) * self.quantity
        else:
            pnl = (self.entry_price - current_price) * self.quantity
        self.unrealized_pnl = pnl
        return pnl
