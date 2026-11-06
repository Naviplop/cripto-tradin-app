from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from dataclasses import dataclass, field as dc_field

from domain.value_objects.money import Money


def _utcnow() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


@dataclass
class Account:
    balance: Money
    initial_balance: Money
    currency: str = "USDT"

    @property
    def unrealized_pnl(self) -> Money:
        return Money(0, self.currency)

    @property
    def total_equity(self) -> Money:
        return self.balance + self.unrealized_pnl

    def deposit(self, amount: Money) -> None:
        if amount.currency != self.currency:
            raise ValueError("Currency mismatch on deposit")
        self.balance += amount

    def withdraw(self, amount: Money) -> None:
        if amount.currency != self.currency:
            raise ValueError("Currency mismatch on withdrawal")
        if amount > self.balance:
            raise ValueError("Insufficient balance for withdrawal")
        self.balance -= amount

    def realize_pnl(self, pnl: Money) -> None:
        if pnl.currency != self.currency:
            raise ValueError("Currency mismatch on PnL")
        self.balance += pnl
