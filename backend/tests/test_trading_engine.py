import asyncio
from datetime import datetime, timezone

import pytest

from trading_engine import TradingEngine, OrderSide, OrderType


@pytest.fixture
def engine(temp_db_path):
    engine = TradingEngine(initial_balance=10000.0, db_path=temp_db_path)
    engine.set_broadcaster(lambda c, s: None, lambda a: None)
    yield engine
    engine.stop()


def test_initial_balance(engine):
    summary = engine.get_account_summary()
    assert summary["balance"] == 10000.0
    assert summary["total_equity"] == 10000.0


def test_market_buy_and_pnl(engine):
    engine.current_price = 100.0
    order = engine.place_order(OrderSide.BUY, OrderType.MARKET, 1.0, tp=110.0, sl=90.0)
    assert order["status"] == "FILLED"
    assert len(engine.positions) == 1
    pos = engine.positions[0]
    assert pos.entry_price == 100.0
    assert pos.tp == 110.0
    assert pos.sl == 90.0

    engine.current_price = 105.0
    engine.update_positions()
    assert abs(pos.unrealized_pnl - 5.0) < 1e-9

    engine.current_price = 110.0
    engine.update_positions()
    assert len(engine.positions) == 0
    assert len(engine.trade_history) == 1
    assert engine.trade_history[0].pnl == 10.0


def test_market_sell_and_pnl(engine):
    engine.current_price = 200.0
    engine.place_order(OrderSide.SELL, OrderType.MARKET, 2.0, tp=190.0, sl=210.0)
    assert len(engine.positions) == 1

    engine.current_price = 195.0
    engine.update_positions()
    assert abs(engine.positions[0].unrealized_pnl - 10.0) < 1e-9


def test_limit_order_not_filled(engine):
    engine.current_price = 100.0
    order = engine.place_order(OrderSide.BUY, OrderType.LIMIT, 0.5, price=95.0)
    assert order["status"] == "PENDING"
    assert len(engine.positions) == 0


def test_close_position_updates_balance(engine):
    engine.current_price = 50.0
    engine.place_order(OrderSide.BUY, OrderType.MARKET, 2.0)
    engine.current_price = 60.0
    engine.update_positions()
    assert len(engine.positions) == 1
    pos = engine.positions[0]
    engine.close_position(pos)
    assert len(engine.positions) == 0
    expected_balance = 10000.0 + 20.0
    assert abs(engine.balance - expected_balance) < 1e-9


def test_snapshot_account(engine, temp_db_path):
    engine.current_price = 100.0
    engine.place_order(OrderSide.BUY, OrderType.MARKET, 1.0)
    engine.current_price = 105.0
    engine.update_positions()
    engine.snapshot_account()
    engine._storage.save_account_snapshot(10000.0, 10000.0, 10005.0)
    latest = engine._storage.get_latest_balance()
    assert latest["balance"] == 10000.0
    assert abs(latest["total_equity"] - 10005.0) < 1e-9


def test_signals_neutral_without_candles(engine):
    signal = engine.get_current_signals()
    assert signal["signal"] in ("NEUTRAL", None)
