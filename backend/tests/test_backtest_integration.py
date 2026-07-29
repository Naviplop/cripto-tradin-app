from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from backtest.data import KlineDataLoader
from backtest.engine import BacktestEngine
from backtest.metrics import MetricsCalculator
from backtest.portfolio import BacktestPortfolio
from backtest.schemas import BacktestRequest
from domain.entities.candle import Candle
from domain.entities.trade import Trade
from domain.value_objects.money import Money
from domain.value_objects.order_side import OrderSide


def _make_candles(n=50, base_price=100.0, seed=42):
    rng = np.random.default_rng(seed)
    candles = []
    ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
    price = base_price
    for _ in range(n):
        o = price
        c = price * (1 + rng.normal(0, 0.01))
        h = max(o, c) * (1 + abs(rng.normal(0, 0.005)))
        l = min(o, c) * (1 - abs(rng.normal(0, 0.005)))
        v = float(rng.uniform(100, 1000))
        candles.append(Candle.from_raw(timestamp=ts, open_price=o, high_price=h, low_price=l, close_price=c, volume=v))
        ts += timedelta(minutes=1)
        price = c
    return candles


def test_event_driven_with_strategy_signals():
    candles = _make_candles(50, seed=1)
    engine = BacktestEngine(initial_balance=1000.0, execution_mode="event_driven", enable_slippage=False, enable_latency=False)
    engine.load_candles(candles)

    def strategy(candle, portfolio, params):
        if len(portfolio.positions) == 0:
            return [{"action": "buy", "quantity": 1.0}]
        return [{"action": "close"}]

    result = engine.run(strategy_fn=strategy)
    assert len(result.equity_curve) > 0
    assert result.run_id is not None


def test_vectorized_with_tuple_signals():
    candles = _make_candles(50, seed=2)
    engine = BacktestEngine(initial_balance=1000.0, execution_mode="vectorized", enable_slippage=False, enable_latency=False)
    engine.load_candles(candles)

    def strategy(df, params):
        if len(df) < 2:
            return None
        last = df.iloc[-1]
        prev = df.iloc[-2]
        if float(last["close"]) > float(prev["close"]):
            return {"action": "buy"}
        if float(last["close"]) < float(prev["close"]) and len(engine.portfolio.positions) > 0:
            return {"action": "close"}
        return None

    result = engine.run(strategy_fn=strategy)
    assert len(result.equity_curve) > 0


def test_empty_candles_vectorized():
    engine = BacktestEngine(initial_balance=1000.0, execution_mode="vectorized", enable_slippage=False, enable_latency=False)
    result = engine.run()
    assert len(result.equity_curve) == 0


def test_empty_candles_event_driven():
    engine = BacktestEngine(initial_balance=1000.0, execution_mode="event_driven", enable_slippage=False, enable_latency=False)
    result = engine.run()
    assert len(result.equity_curve) == 0


def test_portfolio_unrealized_pnl_long():
    port = BacktestPortfolio(initial_balance=5000.0, enable_slippage=False, enable_latency=False)
    port.execute_market(OrderSide.BUY, 1.0, Candle.from_raw(datetime(2023, 1, 1), 100, 101, 99, 100, 1000))
    pnl = port.unrealized_pnl(110.0)
    assert abs(pnl - 10.0) < 1e-9


def test_portfolio_unrealized_pnl_short():
    port = BacktestPortfolio(initial_balance=5000.0, enable_slippage=False, enable_latency=False)
    port.execute_market(OrderSide.SELL, 1.0, Candle.from_raw(datetime(2023, 1, 1), 100, 101, 99, 100, 1000))
    pnl = port.unrealized_pnl(90.0)
    assert abs(pnl - 10.0) < 1e-9


def test_portfolio_total_equity():
    port = BacktestPortfolio(initial_balance=5000.0, enable_slippage=False, enable_latency=False)
    port.execute_market(OrderSide.BUY, 1.0, Candle.from_raw(datetime(2023, 1, 1), 100, 101, 99, 100, 1000))
    equity = port.total_equity(100.0)
    assert equity >= 0.0


def test_metrics_calculate_with_trades():
    eq = [(datetime(2023, 1, 1), 1000.0), (datetime(2023, 1, 2), 1100.0)]
    trades = [
        Trade(id="1", side=OrderSide.BUY, entry_price=100.0, exit_price=110.0, quantity=1.0, pnl=Money(10.0))
    ]
    m = MetricsCalculator.calculate(eq, trades, 1000.0)
    assert m.total_trades == 1
    assert m.gross_profit == 10.0


def test_metrics_empty_trades():
    eq = [(datetime(2023, 1, 1), 1000.0)]
    m = MetricsCalculator.calculate(eq, [], 1000.0)
    assert m.total_trades == 0


def test_kline_data_loader_round_trip():
    candles = _make_candles(10, seed=7)
    df = KlineDataLoader.to_dataframe(candles)
    assert len(df) == 10
    assert set(df.columns) == {"open", "high", "low", "close", "volume"}


def test_kline_data_loader_from_dataframe():
    df = pd.DataFrame({
        "timestamp": pd.date_range("2023-01-01", periods=5, freq="1min"),
        "open": [100, 101, 102, 103, 104],
        "high": [105, 106, 107, 108, 109],
        "low": [95, 96, 97, 98, 99],
        "close": [101, 102, 103, 104, 105],
        "volume": [100, 200, 300, 400, 500],
    })
    candles = KlineDataLoader.from_dataframe(df)
    assert len(candles) == 5
    assert all(isinstance(c, Candle) for c in candles)


def test_backtest_request_defaults():
    req = BacktestRequest(pair="BTCUSDT", timeframe="1m", limit=100)
    assert req.pair == "BTCUSDT"
    assert req.fee_tier == "regular"
