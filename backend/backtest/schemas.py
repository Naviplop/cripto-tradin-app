from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class OrderSideEnum(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderTypeEnum(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    OCO = "OCO"


class ExecutionModeEnum(str, Enum):
    VECTORIZED = "vectorized"
    EVENT_DRIVEN = "event_driven"


class BacktestRequest(BaseModel):
    pair: str = Field(default="BTCUSDT", min_length=3)
    timeframe: str = Field(default="1m", min_length=1)
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
    initial_balance: Decimal = Field(default=Decimal("10000.00"), gt=0)
    execution_mode: ExecutionModeEnum = Field(default=ExecutionModeEnum.EVENT_DRIVEN)
    replay_speed: int = Field(default=1, ge=1, le=100)
    paper_trading: bool = Field(default=True)
    fee_tier: str = Field(default="regular")
    enable_slippage: bool = Field(default=True)
    enable_latency: bool = Field(default=True)
    maker_fee: Optional[Decimal] = Field(default=None)
    taker_fee: Optional[Decimal] = Field(default=None)
    slippage_bps: Optional[Decimal] = Field(default=None)
    latency_ms: Optional[int] = Field(default=None)
    strategy_data: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_dates(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                pass
        return v

    @model_validator(mode="after")
    def validate_dates(self) -> "BacktestRequest":
        if self.start_date is not None and self.end_date is not None:
            if self.end_date <= self.start_date:
                raise ValueError("end_date must be after start_date")
        return self

    @model_validator(mode="after")
    def set_fee_defaults(self) -> "BacktestRequest":
        if self.maker_fee is None and self.taker_fee is None:
            tier_fees = {
                "regular": (Decimal("0.000100"), Decimal("0.000100")),
                "vip1": (Decimal("0.000090"), Decimal("0.000090")),
                "vip2": (Decimal("0.000080"), Decimal("0.000082")),
                "vip3": (Decimal("0.000070"), Decimal("0.000077")),
                "vip4": (Decimal("0.000060"), Decimal("0.000070")),
                "vip5": (Decimal("0.000050"), Decimal("0.000060")),
                "vip6": (Decimal("0.000040"), Decimal("0.000050")),
                "vip7": (Decimal("0.000030"), Decimal("0.000040")),
                "vip8": (Decimal("0.000020"), Decimal("0.000030")),
                "vip9": (Decimal("0.000010"), Decimal("0.000020")),
            }
            m, t = tier_fees.get(self.fee_tier.lower(), tier_fees["regular"])
            self.maker_fee = m
            self.taker_fee = t
        return self


class BacktestResultResponse(BaseModel):
    run_id: str
    status: str
    requested_at: datetime
    completed_at: Optional[datetime] = None
    pair: str
    timeframe: str
    execution_mode: ExecutionModeEnum
    replay_speed: int
    initial_balance: Decimal
    final_balance: Optional[Decimal] = None
    total_return: Optional[Decimal] = None
    total_fees: Decimal = Field(default=Decimal("0.00"))
    total_slippage: Decimal = Field(default=Decimal("0.00"))
    total_trades: Optional[int] = None
    error: Optional[str] = None


class TradeRecord(BaseModel):
    trade_id: str
    side: OrderSideEnum
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: Decimal
    exit_price: Optional[Decimal] = None
    quantity: float
    pnl: Optional[Decimal] = None
    fees: Decimal = Field(default=Decimal("0.00"))
    slippage: Decimal = Field(default=Decimal("0.00"))
    reason: Optional[str] = None


class BacktestMetrics(BaseModel):
    win_rate: float
    profit_factor: float
    max_drawdown_abs: Decimal
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    expectancy: float
    cumulative_roi: float
    total_trades: int
    avg_trade_pnl: float
    best_trade: Decimal
    worst_trade: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    total_fees: Decimal
    total_slippage: Decimal
    equity_curve: List[tuple[datetime, Decimal]]


class MetricsResponse(BaseModel):
    run_id: str
    win_rate: float
    profit_factor: float
    max_drawdown_abs: Decimal
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    expectancy: float
    cumulative_roi: float
    total_trades: int
    avg_trade_pnl: float
    best_trade: Decimal
    worst_trade: Decimal
    gross_profit: Decimal
    gross_loss: Decimal
    total_fees: Decimal
    total_slippage: Decimal
    equity_curve: List[tuple[datetime, Decimal]]


class OptimizationRequest(BaseModel):
    pair: str = Field(default="BTCUSDT", min_length=3)
    timeframe: str = Field(default="1m", min_length=1)
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
    initial_balance: Decimal = Field(default=Decimal("10000.00"), gt=0)
    replay_speed: int = Field(default=10, ge=1, le=100)
    paper_trading: bool = Field(default=True)
    method: str = Field(default="grid", pattern="^(grid|walk_forward|monte_carlo)$")
    param_grid: Optional[Dict[str, List[Any]]] = Field(default_factory=dict)
    monte_carlo_iterations: int = Field(default=1000, ge=100, le=10000)
    walk_forward_train_days: int = Field(default=30, ge=1)
    walk_forward_test_days: int = Field(default=7, ge=1)
    fee_tier: str = Field(default="regular")
    enable_slippage: bool = Field(default=True)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_dates(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return datetime.fromisoformat(v)
            except ValueError:
                pass
        return v


class OptimizationResultResponse(BaseModel):
    run_id: str
    status: str
    method: str
    best_params: Optional[Dict[str, Any]] = None
    best_metrics: Optional[Dict[str, float]] = None
    parameter_results: List[Dict[str, Any]] = Field(default_factory=list)
    equity_curves: Optional[Dict[str, List[tuple[datetime, Decimal]]]] = Field(default_factory=dict)
    mc_statistics: Optional[Dict[str, Any]] = Field(default_factory=dict)
