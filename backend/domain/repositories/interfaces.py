from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from domain.entities.account import Account
from domain.entities.order import Order, OrderSide, OrderType
from domain.entities.position import Position
from domain.entities.trade import Trade
from domain.value_objects.money import Money


class ITradeRepository(ABC):
    @abstractmethod
    def save(self, trade: Trade) -> Trade:
        ...

    @abstractmethod
    def get_by_id(self, trade_id: str) -> Optional[Trade]:
        ...

    @abstractmethod
    def list_recent(self, limit: int = 100) -> List[Trade]:
        ...


class IPositionRepository(ABC):
    @abstractmethod
    def add(self, position: Position) -> Position:
        ...

    @abstractmethod
    def get_by_id(self, position_id: int) -> Optional[Position]:
        ...

    @abstractmethod
    def get_open(self) -> List[Position]:
        ...

    @abstractmethod
    def remove(self, position_id: int) -> None:
        ...

    @abstractmethod
    def update_unrealized_pnl(self, position_id: int, unrealized_pnl: Money) -> None:
        ...


class ILicenseRepository(ABC):
    @abstractmethod
    def get_cached_state(self, hwid: str) -> Optional[dict]:
        ...

    @abstractmethod
    def save_state(self, hwid: str, license_key: str, valid: bool, expiry: Optional[str]) -> None:
        ...


class IMarketDataRepository(ABC):
    @abstractmethod
    def get_candles(self, symbol: str, interval: str, limit: int) -> List[dict]:
        ...

    @abstractmethod
    def get_ticker(self, symbol: str) -> dict:
        ...

    @abstractmethod
    def get_orderbook(self, symbol: str, limit: int) -> dict:
        ...


class IModelRepository(ABC):
    @abstractmethod
    def save_prediction(self, score: float, signal: str, candles_used: int, model_loaded: bool) -> None:
        ...

    @abstractmethod
    def get_recent_predictions(self, limit: int = 100) -> List[dict]:
        ...


class IAccountRepository(ABC):
    @abstractmethod
    def save_snapshot(self, balance: Money, initial_balance: Money) -> None:
        ...

    @abstractmethod
    def get_latest_snapshot(self) -> Optional[dict]:
        ...
