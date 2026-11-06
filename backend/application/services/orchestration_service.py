from __future__ import annotations

from typing import TYPE_CHECKING

from domain.entities.order import Order, OrderSide, OrderType
from domain.entities.position import Position
from domain.events import OrderPlaced
from domain.value_objects.money import Money

if TYPE_CHECKING:
    from application.commands.place_order import PlaceOrderCommand, PlaceOrderHandler
    from application.queries.get_positions import GetPositionsHandler


class OrchestrationService:
    def __init__(
        self,
        place_order_handler: PlaceOrderHandler,
        get_positions_handler: GetPositionsHandler,
    ) -> None:
        self._place_order_handler = place_order_handler
        self._get_positions_handler = get_positions_handler

    async def place_market_order(self, side: OrderSide, quantity: float, tp: float | None = None, sl: float | None = None) -> dict:
        command = PlaceOrderCommand(side=side, order_type=OrderType.MARKET, quantity=quantity, tp=tp, sl=sl)
        order = await self._place_order_handler.handle(command)
        return {
            "success": True,
            "order": {
                "id": order.id,
                "status": order.status.value,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "price": order.filled_price.to_float() if order.filled_price else (order.price.to_float() if order.price else None),
                "tp": tp,
                "sl": sl,
            },
        }

    async def place_limit_order(self, side: OrderSide, quantity: float, price: float) -> dict:
        command = PlaceOrderCommand(side=side, order_type=OrderType.LIMIT, quantity=quantity, price=price)
        order = await self._place_order_handler.handle(command)
        return {
            "success": True,
            "order": {
                "id": order.id,
                "status": order.status.value,
                "side": order.side.value,
                "order_type": order.order_type.value,
                "quantity": order.quantity,
                "price": price,
            },
        }
