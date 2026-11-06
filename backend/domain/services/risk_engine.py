from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from domain.entities.order import Order
from domain.entities.position import Position
from domain.value_objects.money import Money


class RiskEngine(ABC):
    @abstractmethod
    def validate_order(self, order: Order, positions: List[Position], balance: Money) -> List[str]:
        ...

    @abstractmethod
    def compute_position_size(self, balance: Money, entry_price: Money, risk_params: dict) -> float:
        ...

    @abstractmethod
    def check_drawdown(self, initial_balance: Money, current_balance: Money) -> bool:
        ...
