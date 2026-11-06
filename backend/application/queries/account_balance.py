from __future__ import annotations

from typing import List

from domain.entities.account import Account
from domain.events import MarketDataReceived
from domain.repositories.interfaces import (
    IAccountRepository,
    IMarketDataRepository,
    IPositionRepository,
    ITradeRepository,
)


class GetTickerQuery:
    def __init__(self, symbol: str = "BTCUSDT") -> None:
        self.symbol = symbol
        self.result: dict | None = None


class GetTickerHandler:
    def __init__(self, market_repo: IMarketDataRepository) -> None:
        self._market_repo = market_repo

    async def handle(self, query: GetTickerQuery) -> dict:
        query.result = self._market_repo.get_ticker(query.symbol)
        return query.result


class GetPositionsQuery:
    def __init__(self) -> None:
        self.result: list[dict] = []


class GetPositionsHandler:
    def __init__(self, position_repo: IPositionRepository) -> None:
        self._position_repo = position_repo

    async def handle(self, query: GetPositionsQuery) -> list[dict]:
        positions = self._position_repo.get_open()
        query.result = [
            {
                "id": p.id,
                "side": p.side.value,
                "entry_price": p.entry_price.to_float(),
                "quantity": p.quantity,
                "unrealized_pnl": p.unrealized_pnl.to_float(),
                "tp": p.tp.to_float() if p.tp else None,
                "sl": p.sl.to_float() if p.sl else None,
                "timestamp": p.timestamp.isoformat(),
            }
            for p in positions
        ]
        return query.result


class GetHistoryQuery:
    def __init__(self, limit: int = 100) -> None:
        self.limit = limit
        self.result: list[dict] = []


class GetHistoryHandler:
    def __init__(self, trade_repo: ITradeRepository) -> None:
        self._trade_repo = trade_repo

    async def handle(self, query: GetHistoryQuery) -> list[dict]:
        trades = self._trade_repo.list_recent(query.limit)
        query.result = [
            {
                "id": t.id,
                "side": t.side.value,
                "entry_price": t.entry_price.to_float(),
                "exit_price": t.exit_price.to_float(),
                "quantity": t.quantity,
                "pnl": t.pnl.to_float(),
                "timestamp": t.timestamp.isoformat(),
            }
            for t in trades
        ]
        return query.result


class GetSignalsQuery:
    def __init__(self) -> None:
        self.result: dict = {}


class GetSignalsHandler:
    def __init__(self, market_repo: IMarketDataRepository) -> None:
        self._market_repo = market_repo

    async def handle(self, query: GetSignalsQuery) -> dict:
        query.result = {}
        return query.result


class GetKlinesQuery:
    def __init__(self, symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 200) -> None:
        self.symbol = symbol
        self.interval = interval
        self.limit = limit
        self.result: list[dict] = []


class GetKlinesHandler:
    def __init__(self, market_repo: IMarketDataRepository) -> None:
        self._market_repo = market_repo

    async def handle(self, query: GetKlinesQuery) -> list[dict]:
        query.result = self._market_repo.get_candles(query.symbol, query.interval, query.limit)
        return query.result


class GetOrderbookQuery:
    def __init__(self, symbol: str = "BTCUSDT", limit: int = 50) -> None:
        self.symbol = symbol
        self.limit = limit
        self.result: dict = {}


class GetOrderbookHandler:
    def __init__(self, market_repo: IMarketDataRepository) -> None:
        self._market_repo = market_repo

    async def handle(self, query: GetOrderbookQuery) -> dict:
        query.result = self._market_repo.get_orderbook(query.symbol, query.limit)
        return query.result


class GetAccountBalanceQuery:
    def __init__(self) -> None:
        self.result: dict = {}
