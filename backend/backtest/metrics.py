from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass
class BacktestMetrics:
    win_rate: float
    profit_factor: float
    max_drawdown_abs: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    expectancy: float
    cumulative_roi: float
    total_trades: int
    avg_trade_pnl: float
    best_trade: float
    worst_trade: float
    gross_profit: float
    gross_loss: float
    total_fees: float
    total_slippage: float
    equity_curve: List[Tuple[Any, float]] = field(default_factory=list)


class MetricsCalculator:
    @staticmethod
    def calculate(
        equity_curve: List[Tuple[Any, float]],
        trades: List,
        initial_balance: float,
        risk_free_rate: float = 0.02,
        trading_days_per_year: int = 365,
    ) -> BacktestMetrics:
        if not equity_curve or len(equity_curve) < 2:
            return BacktestMetrics(
                win_rate=0.0,
                profit_factor=0.0,
                max_drawdown_abs=0.0,
                max_drawdown_pct=0.0,
                sharpe_ratio=0.0,
                sortino_ratio=0.0,
                calmar_ratio=0.0,
                expectancy=0.0,
                cumulative_roi=0.0,
                total_trades=0,
                avg_trade_pnl=0.0,
                best_trade=0.0,
                worst_trade=0.0,
                gross_profit=0.0,
                gross_loss=0.0,
                total_fees=getattr(trades[0], "fees", 0.0) if trades else 0.0,
                total_slippage=0.0,
                equity_curve=equity_curve,
            )

        curve = pd.Series([e[1] for e in equity_curve])
        returns = curve.pct_change().dropna()
        cumulative = curve.iloc[-1] - curve.iloc[0]
        cumulative_roi = cumulative / initial_balance if initial_balance != 0 else 0.0

        peak = curve.expanding(min_periods=1).max()
        drawdown = (curve - peak) / peak.replace(0, np.nan)
        max_dd_pct = float(drawdown.min()) if not drawdown.empty else 0.0
        max_dd_abs = float((peak - curve).max()) if len(curve) > 0 else 0.0

        risk_free_daily = risk_free_rate / trading_days_per_year
        excess = returns - risk_free_daily
        sharpe = float(np.sqrt(252) * excess.mean() / (excess.std() + 1e-12)) if len(excess) > 1 else 0.0

        downside = returns[returns < 0]
        downside_std = downside.std() if len(downside) > 0 else 0.0
        sortino = float(np.sqrt(252) * (returns.mean() - risk_free_daily) / (downside_std + 1e-12)) if downside_std > 0 else 0.0

        calmar = float(cumulative_roi / (abs(max_dd_pct) + 1e-12)) if max_dd_pct != 0 else 0.0

        pnls = []
        wins = 0
        losses = 0
        gross_profit = 0.0
        gross_loss = 0.0
        best = 0.0
        worst = 0.0
        total_fees = 0.0
        total_slippage = 0.0

        for t in trades:
            pnl = float(getattr(t, "pnl", 0.0).amount)
            fees = float(getattr(t, "fees", 0.0).amount)
            pnls.append(pnl)
            if pnl > 0:
                wins += 1
                gross_profit += pnl
                best = max(best, pnl)
            elif pnl < 0:
                losses += 1
                gross_loss += abs(pnl)
                worst = min(worst, pnl)
            total_fees += fees

        total_trades = len(pnls)
        win_rate = wins / total_trades if total_trades > 0 else 0.0
        avg_pnl = float(np.mean(pnls)) if pnls else 0.0
        expectancy = avg_pnl
        pf = gross_profit / (gross_loss + 1e-12) if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

        return BacktestMetrics(
            win_rate=win_rate,
            profit_factor=float(pf),
            max_drawdown_abs=abs(max_dd_abs),
            max_drawdown_pct=abs(max_dd_pct),
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            calmar_ratio=calmar,
            expectancy=expectancy,
            cumulative_roi=cumulative_roi,
            total_trades=total_trades,
            avg_trade_pnl=avg_pnl,
            best_trade=best,
            worst_trade=worst,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            total_fees=total_fees,
            total_slippage=total_slippage,
            equity_curve=equity_curve,
        )

    @staticmethod
    def monte_carlo_sanity_check(
        base_equity_curve: List[Tuple[Any, float]],
        iterations: int = 1000,
        initial_balance: float = 10000.0,
    ) -> dict:
        if len(base_equity_curve) < 2:
            return {"mean_final_equity": initial_balance, "std_final_equity": 0.0,
                    "mean_max_dd": 0.0, "mean_cum_roi": 0.0, "median_cum_roi": 0.0,
                    "95pct_cum_roi": 0.0, "5pct_cum_roi": 0.0, "passed": True}

        values = pd.Series([e[1] for e in base_equity_curve])
        returns = values.pct_change().dropna().values
        n = len(returns)
        if n == 0:
            return {"mean_final_equity": initial_balance, "std_final_equity": 0.0,
                    "mean_max_dd": 0.0, "mean_cum_roi": 0.0, "median_cum_roi": 0.0,
                    "95pct_cum_roi": 0.0, "5pct_cum_roi": 0.0, "passed": True}

        sampled = np.random.choice(returns, size=(iterations, n), replace=True)
        paths = np.cumprod(1 + sampled, axis=1)
        paths = initial_balance * paths
        final_eqs = paths[:, -1]
        cum_rois = (final_eqs - initial_balance) / initial_balance

        max_dds = []
        for path in paths:
            peak = np.maximum.accumulate(path)
            dd = (peak - path) / np.where(peak == 0, 1e-12, peak)
            max_dds.append(float(np.max(dd)))

        peaks = np.maximum.accumulate(paths, axis=1)
        drawdowns = (peaks - paths) / np.where(peaks == 0, 1e-12, peaks)
        max_dd_per_path = np.max(drawdowns, axis=1)

        return {
            "mean_final_equity": float(np.mean(final_eqs)),
            "std_final_equity": float(np.std(final_eqs)),
            "mean_max_dd": float(np.mean(max_dd_per_path)),
            "mean_cum_roi": float(np.mean(cum_rois)),
            "median_cum_roi": float(np.median(cum_rois)),
            "95pct_cum_roi": float(np.percentile(cum_rois, 95)),
            "5pct_cum_roi": float(np.percentile(cum_rois, 5)),
            "passed": bool(np.mean(max_dd_per_path) < 0.5),
        }
