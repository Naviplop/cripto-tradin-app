from __future__ import annotations

from pydantic import BaseModel, Field


class MoneyDTO(BaseModel):
    amount: float = Field(ge=0.0)
    currency: str = "USDT"


class OrderSideDTO(str):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatusDTO(str):
    PENDING = "PENDING"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
