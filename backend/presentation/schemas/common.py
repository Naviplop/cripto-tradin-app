from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    license_valid: bool
    hwid: str


class OrderResponse(BaseModel):
    success: bool
    order: dict


class SignalsResponse(BaseModel):
    signals: dict


class AccountBalanceResponse(BaseModel):
    balance: float
    initial_balance: float
    unrealized_pnl: float
    total_equity: float
    positions_count: int


class PositionsResponse(BaseModel):
    positions: list[dict]


class HistoryResponse(BaseModel):
    history: list[dict]


class TickerResponse(BaseModel):
    symbol: str
    price: float
    priceChangePercent: float
    high: float
    low: float
    volume: float
    quoteVolume: float


class OrderbookResponse(BaseModel):
    bids: list[list[float]]
    asks: list[list[float]]


class KlinesResponse(BaseModel):
    klines: list[dict]
