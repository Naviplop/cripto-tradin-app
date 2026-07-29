from __future__ import annotations

from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from dataclasses import dataclass

from dataclasses import dataclass, field as dc_field

from domain.value_objects.money import Money


def _utcnow() -> datetime:
    return datetime.now(ZoneInfo("UTC"))


@dataclass
class Candle:
    timestamp: datetime
    open: Money
    high: Money
    low: Money
    close: Money
    volume: float

    @staticmethod
    def from_raw(
        timestamp: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: float,
    ) -> Candle:
        return Candle(
            timestamp=timestamp,
            open=Money(open_price),
            high=Money(high_price),
            low=Money(low_price),
            close=Money(close_price),
            volume=volume,
        )
