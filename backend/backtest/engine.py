from __future__ import annotations

import asyncio
import hashlib
import logging
import numpy as np
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Union

from backtest.data import KlineDataLoader
from backtest.metrics import MetricsCalculator
from backtest.portfolio import BacktestPortfolio
from domain.entities.candle import Candle
from domain.entities.trade import Trade
from domain.value_objects.money import Money
from domain.value_objects.order_side import OrderSide
from domain.value_objects.order_type import OrderType


logger = logging.getLogger(__name__)


class BacktestEngineResult:
    def __init__(self, run_id: str, portfolio: BacktestPortfolio, equity_curve: List) -> None:
        self.run_id = run_id
        self.portfolio = portfolio
        self.equity_curve = equity_curve


class BacktestEngine:
    def __init__(
        self,
        initial_balance: float = 10000.0,
        execution_mode: str = "event_driven",
        replay_speed: int = 1,
        paper_trading: bool = True,
        maker_fee: float = 0.0001,
        taker_fee: float = 0.0001,
        enable_slippage: bool = True,
        enable_latency: bool = True,
    ) -> None:
        self.initial_balance = initial_balance
        self.execution_mode = execution_mode
        self.replay_speed = replay_speed
        self.paper_trading = paper_trading
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.enable_slippage = enable_slippage
        self.enable_latency = enable_latency
        self.portfolio = BacktestPortfolio(
            initial_balance=initial_balance,
            maker_fee=maker_fee,
            taker_fee=taker_fee,
            enable_slippage=enable_slippage,
            enable_latency=enable_latency,
            paper_trading=paper_trading,
        )
        self.candles: List[Candle] = []
        self.equity_curve: List = []
        self.run_id = ""
        self.strategy_params: Dict[str, Any] = {}

    @property
    def trades(self) -> List[Trade]:
        return self.portfolio.trades

    @property
    def total_fees(self) -> float:
        return self.portfolio.total_fees

    @property
    def total_slippage(self) -> float:
        return self.portfolio.total_slippage

    def load_candles(self, candles: List[Candle]) -> None:
        self.candles = sorted(candles, key=lambda c: c.timestamp)
        self.portfolio.reset()

    def _run_event_driven(self, strategy_fn: Optional[Callable] = None) -> None:
        for candle in self.candles:
            price = float(candle.close.amount)
            self.portfolio.update_trailing_stops(candle)
            self.portfolio.check_tp_sl(candle)
            if strategy_fn is not None:
                signals = strategy_fn(candle, self.portfolio, self.strategy_params)
                if signals:
                    for sig in signals:
                        action = sig.get("action")
                        side = OrderSide.BUY if sig.get("side", "BUY") == "BUY" else OrderSide.SELL
                        qty = float(sig.get("quantity", 0))
                        if action == "buy" and qty > 0:
                            self.portfolio.execute_market(side, qty, candle)
                        elif action == "sell" and qty > 0:
                            self.portfolio.execute_market(side, qty, candle)
                        elif action == "close":
                            for pos in list(self.portfolio.positions):
                                self.portfolio.close_position(pos, candle, reason=sig.get("reason", "signal"))
                        elif action == "set_tp_sl" and sig.get("position_id") is not None:
                            for pos in self.portfolio.positions:
                                if pos.id == sig["position_id"]:
                                    if sig.get("tp") is not None:
                                        pos.tp = Money(float(sig["tp"]))
                                    if sig.get("sl") is not None:
                                        pos.sl = Money(float(sig["sl"]))
            self.portfolio._record_equity(candle.timestamp, price)
        self.equity_curve = list(self.portfolio.equity_curve)

    def _run_vectorized(self, strategy_fn: Optional[Callable] = None) -> None:
        df = KlineDataLoader.to_dataframe(self.candles)
        if df.empty:
            self.equity_curve = []
            return
        n = len(df)
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        volumes = df["volume"].values
        timestamps = df.index.to_pydatetime()
        equity = np.full(n, float(self.initial_balance))
        cash = float(self.initial_balance)
        position = 0.0
        entry_price = 0.0
        position_side = 0
        fees = 0.0
        slippage_acc = 0.0
        trade_pnls: List[float] = []
        best = 0.0
        worst = 0.0

        for i in range(n):
            price = closes[i]
            if strategy_fn is not None:
                sub = df.iloc[: i + 1]
                sig = strategy_fn(sub, self.strategy_params)
                if sig and sig.get("action") == "buy" and position == 0:
                    slip = max(highs[i] - price, lows[i] - price) * random.uniform(0, 1)
                    fill = price + abs(slip) if random.random() > 0.5 else price - abs(slip)
                    if fill <= 0:
                        fill = price
                    notional = fill * 1.0
                    fee = notional * self.taker_fee
                    if cash >= notional + fee:
                        cash -= notional + fee
                        fees += fee
                        slippage_acc += abs(slip)
                        position = 1.0
                        entry_price = fill
                        position_side = 1
                elif sig and sig.get("action") == "sell" and position == 0:
                    slip = max(highs[i] - price, lows[i] - price) * random.uniform(0, 1)
                    fill = price - abs(slip) if random.random() > 0.5 else price + abs(slip)
                    if fill <= 0:
                        fill = price
                    notional = fill * 1.0
                    fee = notional * self.taker_fee
                    if cash >= notional + fee:
                        cash -= notional + fee
                        fees += fee
                        slippage_acc += abs(slip)
                        position = 1.0
                        entry_price = fill
                        position_side = -1
                elif sig and sig.get("action") == "close" and position != 0:
                    slip = max(highs[i] - price, lows[i] - price) * random.uniform(0, 1)
                    fill = price + abs(slip) if position_side == -1 else price - abs(slip)
                    notional = fill * position
                    fee = notional * self.taker_fee
                    cash += notional - fee
                    fees += fee
                    slippage_acc += abs(slip)
                    pnl = (fill - entry_price) * position * position_side
                    trade_pnls.append(pnl)
                    if pnl > 0:
                        best = max(best, pnl)
                    else:
                        worst = min(worst, pnl)
                    position = 0.0
                    entry_price = 0.0
                    position_side = 0
            if position != 0:
                mtm = (price - entry_price) * position * position_side
                equity[i] = cash + mtm
            else:
                equity[i] = cash
        self.portfolio.cash = cash
        self.portfolio.total_fees = fees
        self.portfolio.total_slippage = slippage_acc
        self.portfolio.trade_counter = len(trade_pnls)
        self.equity_curve = [(timestamps[i], float(equity[i])) for i in range(n)]

    def run(
        self,
        strategy_fn: Optional[Callable] = None,
        strategy_params: Optional[Dict[str, Any]] = None,
        candles: Optional[List[Candle]] = None,
    ) -> BacktestEngineResult:
        if candles:
            self.load_candles(candles)
        if strategy_params:
            self.strategy_params = strategy_params
        self.run_id = hashlib.sha256(
            (str(self.candles) + str(strategy_params) + str(time.time())).encode()
        ).hexdigest()[:16]
        self.portfolio.reset()
        if self.execution_mode == "vectorized":
            self._run_vectorized(strategy_fn)
        else:
            self._run_event_driven(strategy_fn)
        if not self.equity_curve and self.candles:
            self.portfolio._record_equity(self.candles[0].timestamp, float(self.candles[0].close.amount))
            self.portfolio._record_equity(self.candles[-1].timestamp, float(self.candles[-1].close.amount))
            self.equity_curve = list(self.portfolio.equity_curve)
        return BacktestEngineResult(self.run_id, self.portfolio, self.equity_curve)
