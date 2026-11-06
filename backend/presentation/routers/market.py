from fastapi import APIRouter

from presentation.schemas.common import TickerResponse

router = APIRouter()


@router.get("/ticker", response_model=TickerResponse)
async def market_ticker() -> dict:
    return {
        "symbol": "BTCUSDT",
        "price": 0.0,
        "priceChangePercent": 0.0,
        "high": 0.0,
        "low": 0.0,
        "volume": 0.0,
        "quoteVolume": 0.0,
    }


@router.get("/orderbook")
async def market_orderbook(limit: int = 50) -> dict:
    return {"bids": [], "asks": []}


@router.get("/klines")
async def market_klines(symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 200) -> list[dict]:
    return []
