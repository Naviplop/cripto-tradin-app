from pydantic import BaseModel


class TickerDTO(BaseModel):
    symbol: str
    price: float
    priceChangePercent: float
    high: float
    low: float
    volume: float
    quoteVolume: float


class OrderbookDTO(BaseModel):
    bids: list[list[float]]
    asks: list[list[float]]


class KlineDTO(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float
