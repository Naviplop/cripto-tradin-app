from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Optional


class Money:
    def __init__(self, amount: Decimal, currency: str = "USDT") -> None:
        if not isinstance(amount, Decimal):
            try:
                amount = Decimal(str(amount))
            except (InvalidOperation, ValueError) as exc:
                raise ValueError(f"Invalid money amount: {amount}") from exc
        self.amount = amount
        self.currency = currency

    def __add__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: Money) -> Money:
        self._assert_same_currency(other)
        return Money(self.amount - other.amount, self.currency)

    def __mul__(self, scalar: float) -> Money:
        return Money(self.amount * Decimal(str(scalar)), self.currency)

    def __rmul__(self, scalar: float) -> Money:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Money:
        return Money(self.amount / Decimal(str(scalar)), self.currency)

    def __repr__(self) -> str:
        return f"Money({self.amount} {self.currency})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

    def __gt__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount >= other.amount

    def __lt__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        self._assert_same_currency(other)
        return self.amount <= other.amount

    def __hash__(self) -> int:
        return hash((self.amount, self.currency))

    def _assert_same_currency(self, other: Money) -> None:
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")

    def is_positive(self) -> bool:
        return self.amount > 0

    def is_negative(self) -> bool:
        return self.amount < 0

    def to_float(self) -> float:
        return float(self.amount)
