from __future__ import annotations

import hashlib
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backtest.data import KlineDataLoader
from backtest.engine import BacktestEngine
from backtest.metrics import MetricsCalculator
from backtest.optimization import GridSearchOptimizer, MonteCarloSimulator, WalkForwardAnalysis
from backtest.schemas import (
    BacktestRequest,
    BacktestResultResponse,
    MetricsResponse,
    OptimizationRequest,
    OptimizationResultResponse,
)
from domain.entities.candle import Candle

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/backtest", tags=["backtest"])

_BACKTEST_RUNS: Dict[str, Dict[str, Any]] = {}
_OPTIMIZATION_RUNS: Dict[str, Dict[str, Any]] = {}
_STORAGE_DIR = os.environ.get("BACKTEST_STORAGE_DIR", os.path.join(os.path.dirname(__file__), "..", "backtest_runs"))
os.makedirs(_STORAGE_DIR, exist_ok=True)


class RunResponse(BaseModel):
    run_id: str
    status: str
    message: str


def _load_candles_from_storage(pair: str, timeframe: str, start: Optional[datetime], end: Optional[datetime]) -> List[Candle]:
    csv_path = os.path.join(_STORAGE_DIR, f"{pair}_{timeframe}.csv")
    if os.path.exists(csv_path):
        try:
            return KlineDataLoader.load_csv(csv_path, pair=pair)
        except Exception as exc:
            logger.warning("Failed to load stored candles: %s", exc)
    df = pd.DataFrame()
    try:
        import requests
        url = "https://api.binance.com/api/v3/klines"
        limit = 1000
        params: Dict[str, Any] = {"symbol": pair, "interval": timeframe, "limit": limit}
        if start is not None:
            params["startTime"] = int(start.timestamp() * 1000)
        if end is not None:
            params["endTime"] = int(end.timestamp() * 1000)
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        rows = resp.json()
        records = []
        for r in rows:
            records.append({
                "timestamp": pd.Timestamp(int(r[0]), unit="ms"),
                "open": float(r[1]),
                "high": float(r[2]),
                "low": float(r[3]),
                "close": float(r[4]),
                "volume": float(r[5]),
            })
        df = pd.DataFrame(records)
        if not df.empty:
            df.to_csv(csv_path, index=False)
            return KlineDataLoader.load_csv(csv_path, pair=pair)
    except Exception as exc:
        logger.error("Failed to fetch remote klines: %s", exc)
    return []


@router.post("/run", response_model=RunResponse)
async def run_backtest(body: BacktestRequest):
    candles = _load_candles_from_storage(body.pair, body.timeframe, body.start_date, body.end_date)
    if not candles:
        raise HTTPException(status_code=400, detail="No candle data available for the selected pair/timeframe")
    try:
        engine = BacktestEngine(
            initial_balance=float(body.initial_balance),
            execution_mode=body.execution_mode.value,
            replay_speed=body.replay_speed,
            paper_trading=body.paper_trading,
            maker_fee=float(body.maker_fee or 0.0001),
            taker_fee=float(body.taker_fee or 0.0001),
            enable_slippage=body.enable_slippage,
            enable_latency=body.enable_latency,
        )
        engine.load_candles(candles)
        result = engine.run(strategy_params=body.strategy_data, candles=candles)
        metrics = MetricsCalculator.calculate(result.equity_curve, result.portfolio.trades, engine.initial_balance)
        final_balance = engine.portfolio.cash + engine.portfolio.unrealized_pnl(float(candles[-1].close.amount)) if candles else engine.portfolio.cash
        run_id = result.run_id
        record = {
            "run_id": run_id,
            "status": "completed",
            "requested_at": datetime.now(timezone.utc),
            "completed_at": datetime.now(timezone.utc),
            "pair": body.pair,
            "timeframe": body.timeframe,
            "execution_mode": body.execution_mode.value,
            "replay_speed": body.replay_speed,
            "initial_balance": str(body.initial_balance),
            "final_balance": str(final_balance),
            "total_return": str((final_balance - float(body.initial_balance)) / float(body.initial_balance)) if float(body.initial_balance) != 0 else "0",
            "total_fees": str(engine.portfolio.total_fees),
            "total_slippage": str(engine.portfolio.total_slippage),
            "total_trades": len(engine.portfolio.trades),
            "error": None,
            "candles_used": len(candles),
            "trades": engine.portfolio.trades,
            "metrics": metrics,
        }
        _BACKTEST_RUNS[run_id] = record
        return RunResponse(run_id=run_id, status="completed", message="Backtest completed successfully")
    except Exception as exc:
        logger.exception("Backtest run failed: %s", exc)
        run_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        _BACKTEST_RUNS[run_id] = {"run_id": run_id, "status": "failed", "error": str(exc)}
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/result/{run_id}", response_model=BacktestResultResponse)
async def get_result(run_id: str):
    rec = _BACKTEST_RUNS.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Run not found")
    return BacktestResultResponse(
        run_id=rec["run_id"],
        status=rec["status"],
        requested_at=rec["requested_at"],
        completed_at=rec.get("completed_at"),
        pair=rec["pair"],
        timeframe=rec["timeframe"],
        execution_mode=rec["execution_mode"],
        replay_speed=rec["replay_speed"],
        initial_balance=rec["initial_balance"],
        final_balance=rec.get("final_balance"),
        total_return=rec.get("total_return"),
        total_fees=rec.get("total_fees", "0"),
        total_slippage=rec.get("total_slippage", "0"),
        total_trades=rec.get("total_trades"),
        error=rec.get("error"),
    )


@router.post("/optimize", response_model=RunResponse)
async def run_optimization(body: OptimizationRequest):
    candles = _load_candles_from_storage(body.pair, body.timeframe, body.start_date, body.end_date)
    if not candles:
        raise HTTPException(status_code=400, detail="No candle data available")
    try:
        run_id = hashlib.sha256(
            (str(candles) + body.method + str(time.time())).encode()
        ).hexdigest()[:16]
        if body.method == "grid":
            optimizer = GridSearchOptimizer(candles, body.param_grid or {})
            results, best = optimizer.run(
                initial_balance=float(body.initial_balance),
                maker_fee=float(body.maker_fee) if body.maker_fee else 0.0001,
                taker_fee=float(body.taker_fee) if body.taker_fee else 0.0001,
                enable_slippage=body.enable_slippage,
                enable_latency=body.enable_latency,
                paper_trading=body.paper_trading,
                execution_mode="event_driven",
            )
            record = {
                "run_id": run_id,
                "status": "completed",
                "method": body.method,
                "best_params": best["params"] if best else None,
                "best_metrics": best["metrics"] if best else None,
                "parameter_results": results,
                "equity_curves": {},
                "mc_statistics": {},
            }
        elif body.method == "walk_forward":
            wfa = WalkForwardAnalysis(
                candles, body.param_grid or {}, body.walk_forward_train_days, body.walk_forward_test_days
            )
            out = wfa.run(
                initial_balance=float(body.initial_balance),
                maker_fee=float(body.maker_fee) if body.maker_fee else 0.0001,
                taker_fee=float(body.taker_fee) if body.taker_fee else 0.0001,
                enable_slippage=body.enable_slippage,
                enable_latency=body.enable_latency,
                paper_trading=body.paper_trading,
                execution_mode="event_driven",
            )
            record = {
                "run_id": run_id,
                "status": "completed",
                "method": body.method,
                "best_params": out.get("best_params"),
                "best_metrics": None,
                "parameter_results": out.get("windows", []),
                "equity_curves": {
                    "aggregated": out.get("aggregated_equity", []),
                    "future": [w.get("equity_curve", []) for w in out.get("future_predictions", [])],
                },
                "mc_statistics": {},
            }
        elif body.method == "monte_carlo":
            sim = MonteCarloSimulator(
                candles, iterations=body.monte_carlo_iterations, initial_balance=float(body.initial_balance)
            )
            mc = sim.run(
                maker_fee=float(body.maker_fee) if body.maker_fee else 0.0001,
                taker_fee=float(body.taker_fee) if body.taker_fee else 0.0001,
                enable_slippage=body.enable_slippage,
                enable_latency=body.enable_latency,
                paper_trading=body.paper_trading,
                execution_mode="event_driven",
            )
            record = {
                "run_id": run_id,
                "status": "completed",
                "method": body.method,
                "best_params": None,
                "best_metrics": {
                    "mean_cum_roi": mc.get("mean_cum_roi", 0.0),
                    "median_cum_roi": mc.get("median_cum_roi", 0.0),
                    "5th_percentile_roi": mc.get("5th_percentile_roi", 0.0),
                    "95th_percentile_roi": mc.get("95th_percentile_roi", 0.0),
                    "probability_profit": mc.get("probability_profit", 0.0),
                },
                "parameter_results": [],
                "equity_curves": {},
                "mc_statistics": mc,
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported optimization method: {body.method}")
        _OPTIMIZATION_RUNS[run_id] = record
        return RunResponse(run_id=run_id, status="completed", message="Optimization completed")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Optimization run failed: %s", exc)
        run_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        _OPTIMIZATION_RUNS[run_id] = {"run_id": run_id, "status": "failed", "error": str(exc)}
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/metrics/{run_id}", response_model=MetricsResponse)
async def get_metrics(run_id: str):
    rec = _BACKTEST_RUNS.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail="Run not found")
    metrics: BacktestMetrics = rec["metrics"]
    return MetricsResponse(
        run_id=run_id,
        win_rate=metrics.win_rate,
        profit_factor=metrics.profit_factor,
        max_drawdown_abs=metrics.max_drawdown_abs,
        max_drawdown_pct=metrics.max_drawdown_pct,
        sharpe_ratio=metrics.sharpe_ratio,
        sortino_ratio=metrics.sortino_ratio,
        calmar_ratio=metrics.calmar_ratio,
        expectancy=metrics.expectancy,
        cumulative_roi=metrics.cumulative_roi,
        total_trades=metrics.total_trades,
        avg_trade_pnl=metrics.avg_trade_pnl,
        best_trade=metrics.best_trade,
        worst_trade=metrics.worst_trade,
        gross_profit=metrics.gross_profit,
        gross_loss=metrics.gross_loss,
        total_fees=metrics.total_fees,
        total_slippage=metrics.total_slippage,
        equity_curve=metrics.equity_curve,
    )
