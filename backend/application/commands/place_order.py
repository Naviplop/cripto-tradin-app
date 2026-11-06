from __future__ import annotations

from typing import List

from domain.entities.order import Order, OrderSide, OrderType
from domain.entities.position import Position
from domain.events.order_placed import OrderPlaced
from domain.repositories.interfaces import IPositionRepository, ITradeRepository
from domain.services.risk_engine import RiskEngine
from domain.value_objects.money import Money


class PlaceOrderCommand:
    def __init__(
        self,
        side: OrderSide,
        order_type: OrderType,
        quantity: float,
        price: float | None = None,
        tp: float | None = None,
        sl: float | None = None,
        stop_price: float | None = None,
        limit_price: float | None = None,
    ) -> None:
        self.side = side
        self.order_type = order_type
        self.quantity = quantity
        self.price = price
        self.tp = tp
        self.sl = sl
        self.stop_price = stop_price
        self.limit_price = limit_price
        self.result_order: Order | None = None
        self.error: str | None = None


class PlaceOrderHandler:
    def __init__(
        self,
        risk_engine: RiskEngine,
        position_repo: IPositionRepository,
        trade_repo: ITradeRepository,
    ) -> None:
        self._risk_engine = risk_engine
        self._position_repo = position_repo
        self._trade_repo = trade_repo
        self._events: List[OrderPlaced] = []

    async def handle(self, command: PlaceOrderCommand, balance: Money, positions: List[Position]) -> Order:
        if command.quantity <= 0:
            raise ValueError("Quantity must be positive")
        if command.order_type == OrderType.LIMIT and command.price is None:
            raise ValueError("Limit orders require a price")
        if command.order_type == OrderType.STOP_LIMIT and (command.stop_price is None or command.limit_price is None):
            raise ValueError("Stop-Limit orders require stop_price and limit_price")
        if command.order_type == OrderType.OCO and (command.price is None or command.limit_price is None):
            raise ValueError("OCO orders require a price and limit_price")

        order = Order(
            id="ORD-NEW",
            side=command.side,
            order_type=command.order_type,
            quantity=command.quantity,
            price=Money(command.price) if command.price else None,
            status="PENDING",
            timestamp=Order._utcnow.default_factory(),  # type: ignore[attr-defined]
        )

        violations = self._risk_engine.validate_order(order, positions, balance)
        if violations:
            raise ValueError(f"Risk violations: {', '.join(violations)}")

        if command.order_type == OrderType.MARKET:
            order.status = "FILLED"
            position = Position(
                id=None,
                side=command.side,
                entry_price=Money(command.price or 0.0),
                quantity=command.quantity,
                tp=Money(command.tp) if command.tp else None,
                sl=Money(command.sl) if command.sl else None,
            )
            self._position_repo.add(position)
            self._events.append(OrderPlaced(order.id, command.side.value, command.order_type.value, command.quantity, command.price))
        else:
            self._events.append(OrderPlaced(order.id, command.side.value, command.order_type.value, command.quantity, command.price))

        command.result_order = order
        return order

    @property
    def events(self) -> List[OrderPlaced]:
        return self._events
