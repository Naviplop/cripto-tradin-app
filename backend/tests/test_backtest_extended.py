from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from backtest.data import KlineDataLoader
from backtest.engine import BacktestEngine
from backtest.metrics import MetricsCalculator
from backtest.portfolio import BacktestPortfolio
from domain.entities.candle import Candle
from domain.entities.trade import Trade
from domain.value_objects.money import Money
from domain.value_objects.order_side import OrderSide


def _make_candles(n=60, base_price=100.0, seed=42):
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


def test_event_driven_multiple_trades():
    candles = _make_candles(60, seed=10)
    engine = BacktestEngine(initial_balance=1000.0, execution_mode="event_driven", enable_slippage=False, enable_latency=False)
    engine.load_candles(candles)

    def strategy(candle, portfolio, params):
        if len(portfolio.trades) >= 2:
            return [{"action": "close"}]
        if len(portfolio.positions) == 0:
            return [{"action": "buy", "quantity": 1.0}]
        return []

    result = engine.run(strategy_fn=strategy)
    assert len(result.equity_curve) > 0
    assert result.run_id is not None


def test_vectorized_strategy_with_buys():
    candles = _make_candles(60, seed=11)
    engine = BacktestEngine(initial_balance=1000.0, execution_mode="vectorized", enable_slippage=False, enable_latency=False)
    engine.load_candles(candles)

    def strategy(df, params):
        if len(df) < 2:
            return None
        last = df.iloc[-1]
        prev = df.iloc[-2]
        if float(last["close"]) > float(prev["close"]) and len(engine.portfolio.positions) == 0:
            return {"action": "buy", "quantity": 1.0}
        if float(last["close"]) < float(prev["close"]) and len(engine.portfolio.positions) > 0:
            return {"action": "close"}
        return None

    result = engine.run(strategy_fn=strategy)
    assert len(result.equity_curve) > 0


def test_portfolio_maker_fee():
    port = BacktestPortfolio(initial_balance=20000.0, maker_fee=0.0002, taker_fee=0.001, enable_slippage=False, enable_latency=False)
    c = Candle.from_raw(datetime(2023, 1, 1), 100, 101, 99, 100, 1000)
    res = port.execute_limit(OrderSide.BUY, 1.0, 100.0, c, is_taker=False)
    assert res.filled
    assert port.total_fees > 0.0


def test_portfolio_partial_close_quantity():
    port = BacktestPortfolio(initial_balance=5000.0, enable_slippage=False, enable_latency=False)
    c = Candle.from_raw(datetime(2023, 1, 1), 100, 101, 99, 100, 1000)
    port.execute_market(OrderSide.BUY, 2.0, c)
    pos = port.positions[0]
    close_res = port.close_position(pos, c, partial_quantity=0.5)
    assert close_res is not None
    assert pos.quantity < 2.0


def test_portfolio_close_position_updates_cash():
    port = BacktestPortfolio(initial_balance=5000.0, enable_slippage=False, enable_latency=False)
    buy_candle = Candle.from_raw(datetime(2023, 1, 1), 100, 101, 99, 100, 1000)
    sell_candle = Candle.from_raw(datetime(2023, 1, 1, minute=1), 105, 106, 104, 105, 1000)
    port.execute_market(OrderSide.BUY, 1.0, buy_candle)
    assert len(port.positions) == 1
    port.close_position(port.positions[0], sell_candle)
    assert len(port.positions) == 0
    assert len(port.trades) == 1


def test_metrics_with_all_losses():
    eq = [(datetime(2023, 1, 1), 1000.0), (datetime(2023, 1, 2), 900.0), (datetime(2023, 1, 3), 800.0)]
    trades = [
        Trade(id="1", side=OrderSide.BUY, entry_price=Money(100.0), exit_price=Money(90.0), quantity=1.0, pnl=Money(-100.0), fees=Money(10.0))
    ]
    m = MetricsCalculator.calculate(eq, trades, 1000.0)
    assert m.win_rate == 0.0
    assert m.gross_loss == 100.0
