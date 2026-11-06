from __future__ import annotations

from typing import List

from domain.entities.order import Order, OrderSide, OrderType
from domain.events.order_filled import OrderFilled
from domain.repositories.interfaces import IPositionRepository, ITradeRepository
from domain.services.risk_engine import RiskEngine
from domain.value_objects.money import Money


class CloseOrderCommand:
    def __init__(self, order_id: str) -> None:
        self.order_id = order_id
        self.canceled: bool = False
        self.error: str | None = None


class CloseOrderHandler:
    def __init__(self) -> None:
        self._orders: List[Order] = []

    async def handle(self, command: CloseOrderCommand) -> bool:
        for order in self._orders:
            if order.id == command.order_id and order.can_cancel():
                order.status = "CANCELED"
                command.canceled = True
                return True
        command.error = "Order not found or not cancelable"
        return False
