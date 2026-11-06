from __future__ import annotations

import random
import time
from datetime import datetime, timedelta, timezone
from typing import List

import numpy as np
import pandas as pd
import pytest

from backtest.data import KlineDataLoader
from backtest.engine import BacktestEngine
from backtest.metrics import MetricsCalculator
from backtest.optimization import GridSearchOptimizer, MonteCarloSimulator, WalkForwardAnalysis
from backtest.portfolio import BacktestPortfolio
from backtest.schemas import BacktestRequest
from domain.entities.candle import Candle
from domain.entities.trade import Trade
from domain.value_objects.money import Money
from domain.value_objects.order_side import OrderSide


def _make_candles(n: int = 200, base_price: float = 100.0, seed: int = 42) -> List[Candle]:
    rng = np.random.default_rng(seed)
    candles: List[Candle] = []
    ts = datetime(2023, 1, 1, tzinfo=timezone.utc)
    price = base_price
    for _ in range(n):
        o = price
        c = price * (1 + rng.normal(0, 0.01))
        h = max(o, c) * (1 + abs(rng.normal(0, 0.005)))
        l = min(o, c) * (1 - abs(rng.normal(0, 0.005)))
        v = float(rng.uniform(100, 1000))
        candles.append(Candle.from_raw(timestamp=ts, open_price=o, high_price=h,
                                       low_price=l, close_price=c, volume=v))
        ts += timedelta(minutes=1)
        price = c
    return candles


class TestEngineExecution:
    def test_event_driven_run_known_dataset(self):
        candles = _make_candles(200, seed=1)
        engine = BacktestEngine(initial_balance=1000.0, execution_mode="event_driven",
                                enable_slippage=False, enable_latency=False)
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
        assert isinstance(engine.trades, list)

    def test_vectorized_run_known_dataset(self):
        candles = _make_candles(200, seed=2)
        engine = BacktestEngine(initial_balance=1000.0, execution_mode="vectorized",
                                enable_slippage=False, enable_latency=False)
        engine.load_candles(candles)
        result = engine.run(strategy_params={"threshold": 0.0})
        assert len(result.equity_curve) > 0

    def test_replay_speed_attribute(self):
        candles = _make_candles(50)
        engine = BacktestEngine(initial_balance=500.0, replay_speed=10, execution_mode="event_driven",
                                enable_slippage=False, enable_latency=False)
        assert engine.replay_speed == 10
        engine.load_candles(candles)
        res = engine.run()
        assert res.run_id is not None

    def test_paper_trading_default(self):
        engine = BacktestEngine(initial_balance=1000.0)
        assert engine.paper_trading is True

    def test_partial_close(self):
        candles = _make_candles(100, seed=3)
        port = BacktestPortfolio(initial_balance=5000.0, enable_slippage=False, enable_latency=False)
        c = candles[50]
        res = port.execute_market(OrderSide.BUY, 2.0, c)
        assert res.filled
        assert len(port.positions) == 1
        pos = port.positions[0]
        close_res = port.close_position(pos, c, partial_quantity=0.5)
        assert close_res is not None
        assert close_res.filled
        assert pos.quantity < 2.0

    def test_trailing_stop(self):
        candles = _make_candles(200, base_price=100, seed=4)
        port = BacktestPortfolio(initial_balance=5000.0, enable_slippage=False, enable_latency=False)
        port.execute_market(OrderSide.BUY, 1.0, candles[0])
        port.positions[0].sl = Money(95.0)
        port.update_trailing_stops(candles[100], trail_pct=0.05)
        assert float(port.positions[0].sl.amount) >= 95.0


class TestMetricsAccuracy:
    def test_perfect_strategy(self):
        eq = [(datetime(2023, 1, 1), 1000.0), (datetime(2023, 1, 2), 1100.0)]
        trades = []
        m = MetricsCalculator.calculate(eq, trades, 1000.0)
        assert m.win_rate == 0.0
        assert m.max_drawdown_pct >= 0.0
        assert m.cumulative_roi == 0.1

    def test_all_losses(self):
        eq = [(datetime(2023, 1, 1), 1000.0), (datetime(2023, 1, 2), 900.0),
              (datetime(2023, 1, 3), 800.0)]
        trades = [Trade(id="1", side=OrderSide.BUY, entry_price=Money(100), exit_price=Money(90),
                       quantity=1, pnl=Money(-100), fees=Money(10))]
        m = MetricsCalculator.calculate(eq, trades, 1000.0)
        assert m.win_rate == 0.0
        assert m.gross_profit == 0.0
        assert m.gross_loss == 100.0
        assert m.profit_factor == 0.0

    def test_sharpe_sortino_calmar(self):
        eq = [(datetime(2023, 1, 1), 1000.0 + i*1.0) for i in range(30)]
        m = MetricsCalculator.calculate(eq, [], 1000.0)
        assert isinstance(m.sharpe_ratio, float)
        assert isinstance(m.sortino_ratio, float)
        assert isinstance(m.calmar_ratio, float)

    def test_expectancy(self):
        eq = [(datetime(2023, 1, 1), 1000.0), (datetime(2023, 1, 2), 1005.0)]
        trades = []
        m = MetricsCalculator.calculate(eq, trades, 1000.0)
        assert isinstance(m.expectancy, float)

    def test_empty_equity(self):
        m = MetricsCalculator.calculate([], [], 1000.0)
        assert m.total_trades == 0
        assert m.cumulative_roi == 0.0


class TestSlippageAndFees:
    def test_slippage_positive(self):
        port = BacktestPortfolio(initial_balance=10000.0, enable_slippage=True, enable_latency=False)
        c = Candle.from_raw(datetime(2023, 1, 1), 100, 101, 99, 100, 1000)
        res = port.execute_market(OrderSide.BUY, 1.0, c)
        assert res.filled
        assert res.slippage >= 0.0

    def test_fee_accrual(self):
        port = BacktestPortfolio(initial_balance=20000.0, taker_fee=0.001, maker_fee=0.0005,
                                 enable_slippage=False, enable_latency=False)
        c = Candle.from_raw(datetime(2023, 1, 1), 100, 101, 99, 100, 1000)
        res = port.execute_market(OrderSide.BUY, 10.0, c)
        assert res.filled
        assert port.total_fees > 0.0
        expected = 10.0 * 100.0 * 0.001
        assert abs(port.total_fees - expected) < 1e-6

    def test_insufficient_cash(self):
        port = BacktestPortfolio(initial_balance=10.0, enable_slippage=False, enable_latency=False)
        c = Candle.from_raw(datetime(2023, 1, 1), 100, 101, 99, 100, 1000)
        res = port.execute_market(OrderSide.BUY, 1.0, c)
        assert not res.filled
        assert res.reason == "Insufficient cash"

    def test_maker_taker_difference(self):
        port = BacktestPortfolio(initial_balance=20000.0, taker_fee=0.001, maker_fee=0.0002,
                                 enable_slippage=False, enable_latency=False)
        c = Candle.from_raw(datetime(2023, 1, 1), 100, 100, 100, 100, 1000000)
        res = port.execute_limit(OrderSide.BUY, 1.0, 100.0, c, is_taker=False)
        assert res.filled
        assert port.total_fees > 0.0

    def test_limit_order_not_filled(self):
        port = BacktestPortfolio(initial_balance=20000.0, enable_slippage=False, enable_latency=False)
        c = Candle.from_raw(datetime(2023, 1, 1), 100, 100, 100, 100, 1000)
        res = port.execute_limit(OrderSide.BUY, 1.0, 90.0, c)
        assert not res.filled

    def test_binance_fee_tiers_schema(self):
        req = BacktestRequest(fee_tier="vip5")
        assert float(req.maker_fee) == 0.00005
        assert float(req.taker_fee) == 0.00006


class TestMonteCarloSanityCheck:
    def test_monte_carlo_runs(self):
        candles = _make_candles(200, seed=5)
        sim = MonteCarloSimulator(candles, iterations=100, initial_balance=1000.0)
        result = sim.run(enable_slippage=False, enable_latency=False, paper_trading=True,
                         execution_mode="event_driven")
        assert result["iterations"] == 100
        assert "mean_final_equity" in result
        assert "mean_cum_roi" in result
        assert "probability_profit" in result
        assert isinstance(result["passed"], bool)

    def test_monte_carlo_distribution_sanity(self):
        candles = _make_candles(200, seed=6)
        sim = MonteCarloSimulator(candles, iterations=100, initial_balance=1000.0)
        result = sim.run(enable_slippage=False, enable_latency=False, paper_trading=True,
                         execution_mode="event_driven")
        mean_roi = result["mean_cum_roi"]
        assert isinstance(mean_roi, float)
        lo = result["5th_percentile_roi"]
        hi = result["95th_percentile_roi"]
        assert lo <= hi

    def test_monte_carlo_empty_candles(self):
        sim = MonteCarloSimulator([], iterations=10, initial_balance=1000.0)
        result = sim.run()
        assert result["mean_final_equity"] == 1000.0
        assert result["iterations"] == 0


class TestDataLoading:
    def test_from_dataframe(self):
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

    def test_to_dataframe(self):
        candles = _make_candles(10, seed=7)
        df = KlineDataLoader.to_dataframe(candles)
        assert len(df) == 10
        assert set(df.columns) == {"open", "high", "low", "close", "volume"}

    def test_resample(self):
        candles = _make_candles(60, seed=8)
        resampled = KlineDataLoader.resample(candles, "1h")
        assert len(resampled) > 0
        for c in resampled:
            assert c.timestamp.minute == 0


class TestOptimization:
    def test_grid_search_smoke(self):
        candles = _make_candles(100, seed=9)
        grid = {"threshold": [0.0, 0.01]}
        opt = GridSearchOptimizer(candles, grid)
        results, best = opt.run(initial_balance=1000.0, enable_slippage=False, enable_latency=False)
        assert len(results) == 2
        assert best is not None
        assert "params" in best

    def test_walk_forward_smoke(self):
        candles = _make_candles(200, seed=10)
        grid = {"threshold": [0.0]}
        wfa = WalkForwardAnalysis(candles, grid, train_days=2, test_days=1, candle_minutes=1)
        out = wfa.run(initial_balance=1000.0, enable_slippage=False, enable_latency=False)
        assert "windows" in out

    def test_monte_carlo_optimizer_smoke(self):
        candles = _make_candles(100, seed=11)
        sim = MonteCarloSimulator(candles, iterations=50, initial_balance=1000.0)
        result = sim.run(enable_slippage=False, enable_latency=False)
        assert result["iterations"] == 50
