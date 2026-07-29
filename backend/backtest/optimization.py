from __future__ import annotations

import copy
import hashlib
import itertools
import random
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from backtest.engine import BacktestEngine
from backtest.metrics import MetricsCalculator
from domain.entities.candle import Candle


class GridSearchOptimizer:
    def __init__(self, candles: List[Candle], param_grid: Dict[str, List[Any]]) -> None:
        self.candles = candles
        self.param_grid = param_grid
        self.results: List[Dict[str, Any]] = []

    def run(self, initial_balance: float = 10000.0, **kwargs: Any) -> List[Dict[str, Any]]:
        keys = list(self.param_grid.keys())
        values = list(self.param_grid.values())
        best: Optional[Dict[str, Any]] = None
        best_score = -float("inf")
        for combo in itertools.product(*values):
            params = dict(zip(keys, combo))
            engine = BacktestEngine(
                initial_balance=initial_balance, **{k: v for k, v in kwargs.items()
                                                   if k not in {"initial_balance", "strategy_fn"}}
            )
            engine.load_candles(self.candles)
            result = engine.run(strategy_params=params)
            metrics = MetricsCalculator.calculate(
                result.equity_curve, result.portfolio.trades, initial_balance
            )
            score = metrics.cumulative_roi
            rec = {
                "params": params,
                "metrics": {
                    "cumulative_roi": metrics.cumulative_roi,
                    "win_rate": metrics.win_rate,
                    "profit_factor": metrics.profit_factor,
                    "max_drawdown_pct": metrics.max_drawdown_pct,
                    "sharpe_ratio": metrics.sharpe_ratio,
                },
                "equity_curve": result.equity_curve,
                "run_id": result.run_id,
            }
            self.results.append(rec)
            if score > best_score:
                best_score = score
                best = rec
        return self.results, best


class WalkForwardAnalysis:
    def __init__(
        self,
        candles: List[Candle],
        param_grid: Dict[str, List[Any]],
        train_days: int = 30,
        test_days: int = 7,
        candle_minutes: int = 1,
    ) -> None:
        self.candles = candles
        self.param_grid = param_grid
        self.train_days = train_days
        self.test_days = test_days
        self.candle_minutes = candle_minutes
        self.results: List[Dict[str, Any]] = []

    def _block_bounds(self, df: pd.DataFrame, idx: int) -> Tuple[int, int]:
        train_minutes = self.train_days * 24 * 60
        test_minutes = self.test_days * 24 * 60
        block = train_minutes + test_minutes
        start = idx * block
        train_end = start + train_minutes
        test_end = train_end + test_minutes
        return start, train_end, test_end

    def run(self, initial_balance: float = 10000.0, **kwargs: Any) -> Dict[str, Any]:
        if not self.candles:
            return {"windows": [], "best_params": None, "aggregated_equity": []}
        df = pd.DataFrame(
            [{"timestamp": c.timestamp, "close": float(c.close.amount)} for c in self.candles]
        )
        if df.empty:
            return {"windows": [], "best_params": None, "aggregated_equity": []}
        df.set_index("timestamp", inplace=True)
        total_minutes = len(df)
        block = (self.train_days + self.test_days) * 24 * 60
        if block == 0:
            return {"windows": [], "best_params": None, "aggregated_equity": []}
        windows: List[Dict[str, Any]] = []
        aggregated_equity: List[Tuple[datetime, float]] = []
        keys = list(self.param_grid.keys())
        values = list(self.param_grid.values())
        idx = 0
        while True:
            train_start = idx * block
            train_end = train_start + self.train_days * 24 * 60
            test_end = train_end + self.test_days * 24 * 60
            if test_end > total_minutes:
                break
            train_df = df.iloc[train_start:train_end]
            test_df = df.iloc[train_end:test_end]
            if len(train_df) < 2 or len(test_df) < 2:
                idx += 1
                continue
            train_candles = []
            for ts, row in train_df.iterrows():
                train_candles.append(
                    Candle.from_raw(
                        timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                        open_price=0.0,
                        high_price=0.0,
                        low_price=0.0,
                        close_price=float(row["close"]),
                        volume=0.0,
                    )
                )
            best_params_win: Optional[Dict[str, Any]] = None
            best_score = -float("inf")
            for combo in itertools.product(*values):
                params = dict(zip(keys, combo))
                engine = BacktestEngine(initial_balance=initial_balance, **kwargs)
                engine.load_candles(train_candles)
                result = engine.run(strategy_params=params)
                m = MetricsCalculator.calculate(
                    result.equity_curve, result.portfolio.trades, initial_balance
                )
                if m.cumulative_roi > best_score:
                    best_score = m.cumulative_roi
                    best_params_win = params
            if best_params_win is not None and not test_df.empty:
                test_candles = []
                for ts, row in test_df.iterrows():
                    test_candles.append(
                        Candle.from_raw(
                            timestamp=ts.to_pydatetime() if hasattr(ts, "to_pydatetime") else ts,
                            open_price=0.0,
                            high_price=0.0,
                            low_price=0.0,
                            close_price=float(row["close"]),
                            volume=0.0,
                        )
                    )
                engine = BacktestEngine(initial_balance=initial_balance, **kwargs)
                engine.load_candles(test_candles)
                out = engine.run(strategy_params=best_params_win)
                win_m = MetricsCalculator.calculate(
                    out.equity_curve, out.portfolio.trades, initial_balance
                )
                windows.append(
                    {
                        "window": idx,
                        "train_start": train_df.index[0].isoformat(),
                        "train_end": train_df.index[-1].isoformat(),
                        "test_start": test_df.index[0].isoformat(),
                        "test_end": test_df.index[-1].isoformat(),
                        "best_params": best_params_win,
                        "metrics": {
                            "cumulative_roi": win_m.cumulative_roi,
                            "sharpe_ratio": win_m.sharpe_ratio,
                            "max_drawdown_pct": win_m.max_drawdown_pct,
                        },
                        "equity_curve": out.equity_curve,
                    }
                )
                aggregated_equity.extend(out.equity_curve)
            idx += 1
        agg = WalkForwardAnalysis._stitch_equity(aggregated_equity) if aggregated_equity else []
        best_overall = max(windows, key=lambda w: w["metrics"]["cumulative_roi"]) if windows else None
        future_windows = [w for w in windows if w["window"] > (idx - 2)] if idx > 0 else windows
        return {
            "windows": windows,
            "best_params": best_overall["best_params"] if best_overall else None,
            "aggregated_equity": agg,
            "future_predictions": future_windows,
        }

    @staticmethod
    def _stitch_equity(
        equity: List[Tuple[Any, float]],
    ) -> List[Tuple[Any, float]]:
        if not equity:
            return []
        out: List[Tuple[Any, float]] = []
        for ts, val in equity:
            if not out:
                out.append((ts, val))
            else:
                prev_ts, prev_val = out[-1]
                if ts > prev_ts:
                    out.append((ts, val))
                elif ts == prev_ts:
                    out[-1] = (ts, val)
        return out


class MonteCarloSimulator:
    def __init__(
        self,
        candles: List[Candle],
        iterations: int = 1000,
        initial_balance: float = 10000.0,
    ) -> None:
        self.candles = candles
        self.iterations = iterations
        self.initial_balance = initial_balance

    def run(self, **kwargs: Any) -> dict:
        if not self.candles:
            return {
                "iterations": 0,
                "mean_final_equity": self.initial_balance,
                "std_final_equity": 0.0,
                "mean_cum_roi": 0.0,
                "5th_percentile_roi": 0.0,
                "95th_percentile_roi": 0.0,
                "probability_profit": 0.0,
                "max_drawdown_distribution": [],
                "equity_curves": [],
                "passed": True,
            }
        engine = BacktestEngine(initial_balance=self.initial_balance, **kwargs)
        engine.load_candles(self.candles)
        base = engine.run(**kwargs)
        base_eq = pd.Series([e[1] for e in base.equity_curve])
        base_returns = base_eq.pct_change().dropna().values
        n = len(base_returns)
        if n == 0:
            return {
                "iterations": self.iterations,
                "mean_final_equity": self.initial_balance,
                "std_final_equity": 0.0,
                "mean_cum_roi": 0.0,
                "5th_percentile_roi": 0.0,
                "95th_percentile_roi": 0.0,
                "probability_profit": 0.0,
                "max_drawdown_distribution": [0.0] * self.iterations,
                "equity_curves": [],
                "passed": True,
            }
        sampled = np.random.choice(base_returns, size=(self.iterations, n), replace=True)
        paths = np.cumprod(1 + sampled, axis=1)
        paths = self.initial_balance * paths
        final_eqs = paths[:, -1]
        cum_rois = (final_eqs - self.initial_balance) / self.initial_balance

        max_dds: List[float] = []
        for path in paths:
            peak = np.maximum.accumulate(path)
            dd = (peak - path) / np.where(peak == 0, 1e-12, peak)
            max_dds.append(float(np.max(dd)))

        prob_profit = float(np.mean(cum_rois > 0))
        curves = []
        for i in range(min(self.iterations, 100)):
            ts_vals = [self.candles[j].timestamp for j in range(n)]
            curves.append([(ts_vals[j], float(paths[i, j])) for j in range(n)])

        return {
            "iterations": self.iterations,
            "mean_final_equity": float(np.mean(final_eqs)),
            "std_final_equity": float(np.std(final_eqs)),
            "mean_cum_roi": float(np.mean(cum_rois)),
            "5th_percentile_roi": float(np.percentile(cum_rois, 5)),
            "95th_percentile_roi": float(np.percentile(cum_rois, 95)),
            "probability_profit": prob_profit,
            "max_drawdown_distribution": max_dds,
            "equity_curves": curves,
            "passed": bool(np.mean(max_dds) < 0.5),
        }
