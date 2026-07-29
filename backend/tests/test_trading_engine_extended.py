from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from trading_engine import Candle, TradingEngine, OrderSide, OrderType


def _make_candles(n: int = 40):
    candles = []
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    price = 100.0
    for i in range(n):
        o = price
        c = price * (1 + np.random.uniform(-0.01, 0.01))
        h = max(o, c) + abs(np.random.uniform(0, 0.5))
        l = min(o, c) - abs(np.random.uniform(0, 0.5))
        v = float(np.random.uniform(100, 1000))
        candles.append(Candle(timestamp=base_time + timedelta(minutes=i), open=o, high=h, low=l, close=c, volume=v))
        price = c
    return candles


def test_generate_signals_with_enough_candles():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    engine.candles.extend(_make_candles(40))
    state, enriched = engine._generate_signals()
    assert "signal" in state
    assert "ma_fast" in state
    assert "ma_slow" in state
    assert enriched


def test_get_current_signals_populated():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    engine.candles.extend(_make_candles(40))
    engine._generate_signals()
    signal = engine.get_current_signals()
    assert signal["signal"] in ("BUY", "SELL", "NEUTRAL")
    assert "current_price" in signal
    assert "atr" in signal


def test_snapshot_account_updates_storage(tmp_path):
    db = str(tmp_path / "test.db")
    engine = TradingEngine(initial_balance=1000.0, db_path=db)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    engine.current_price = 100.0
    engine.place_order(OrderSide.BUY, OrderType.MARKET, 1.0)
    engine.snapshot_account()
    latest = engine._storage.get_latest_balance()
    assert latest is not None


def test_stop_limit_order_validation():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    with pytest.raises(ValueError):
        engine.place_order(OrderSide.BUY, OrderType.STOP_LIMIT, 1.0)


def test_oco_order_validation():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    with pytest.raises(ValueError):
        engine.place_order(OrderSide.BUY, OrderType.OCO, 1.0)


def test_limit_order_validation():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    with pytest.raises(ValueError):
        engine.place_order(OrderSide.BUY, OrderType.LIMIT, 1.0)


def test_negative_quantity_validation():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    with pytest.raises(ValueError):
        engine.place_order(OrderSide.BUY, OrderType.MARKET, -1.0)


def test_set_broadcaster():
    engine = TradingEngine(initial_balance=1000.0)
    market_calls = []
    account_calls = []

    def market_fn(candle, signals):
        market_calls.append(candle)

    def account_fn(data):
        account_calls.append(data)

    engine.set_broadcaster(market_fn, account_fn)
    assert engine.broadcast_market is market_fn
    assert engine.broadcast_account is account_fn


def test_generate_signals_buy_with_deterministic_candles():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    engine.candles.clear()
    price = 100.0
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    for i in range(40):
        close = price + i * 0.5
        candle = Candle(
            timestamp=base_time + timedelta(minutes=i),
            open=close - 0.1,
            high=close + 0.5,
            low=close - 0.5,
            close=close,
            volume=500.0,
        )
        engine.candles.append(candle)
    state, enriched = engine._generate_signals()
    assert state["signal"] in ("BUY", "SELL", "NEUTRAL")
    assert len(enriched) > 0
    assert "ema_fast" in enriched[-1]
    assert "ema_slow" in enriched[-1]
    assert "rsi" in enriched[-1]


@pytest.mark.asyncio
async def test_process_tick_populates_signals():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    for i in range(40):
        close = 100.0 + i * 0.5
        candle = Candle(
            timestamp=base_time + timedelta(minutes=i),
            open=close - 0.1,
            high=close + 0.5,
            low=close - 0.5,
            close=close,
            volume=500.0,
        )
        engine.candles.append(candle)
    tick = Candle(
        timestamp=base_time + timedelta(minutes=40),
        open=120.0,
        high=120.5,
        low=119.5,
        close=120.0,
        volume=600.0,
    )
    await engine._process_tick(tick)
    assert engine.current_price == 120.0
    assert "signal" in engine.signal_state
    assert "combined_signal" in engine.signal_state


def test_generate_signals_early_return_with_few_candles():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    engine.candles.extend(_make_candles(5))
    state, enriched = engine._generate_signals()
    assert state["signal"] == "NEUTRAL"
    assert enriched == []


def test_place_order_sets_order_status():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    engine.current_price = 100.0
    order = engine.place_order(OrderSide.BUY, OrderType.MARKET, 1.0)
    assert order["status"] == "FILLED"
    assert len(engine.orders) == 1


def test_generate_signals_buy_with_deterministic_candles():
    engine = TradingEngine(initial_balance=1000.0)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    engine.candles.clear()
    price = 100.0
    base_time = datetime(2023, 1, 1, tzinfo=timezone.utc)
    for i in range(40):
        close = price + i * 0.5
        candle = Candle(
            timestamp=base_time + timedelta(minutes=i),
            open=close - 0.1,
            high=close + 0.5,
            low=close - 0.5,
            close=close,
            volume=500.0,
        )
        engine.candles.append(candle)
    state, enriched = engine._generate_signals()
    assert state["signal"] in ("BUY", "SELL", "NEUTRAL")
    assert len(enriched) > 0
    assert "ema_fast" in enriched[-1]
    assert "ema_slow" in enriched[-1]
    assert "rsi" in enriched[-1]
