from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from domain.events.domain_event import DomainEvent


class MarketDataReceived(DomainEvent):
    def __init__(self, symbol: str, timestamp: datetime, close: float, volume: float) -> None:
        self.symbol = symbol
        self.timestamp = timestamp
        self.close = close
        self.volume = volume
        self.occurred_at = datetime.now(ZoneInfo("UTC"))
