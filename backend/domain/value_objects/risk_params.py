from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskParams:
    max_position_size_usdt: float
    max_drawdown_pct: float
    max_open_positions: int
    daily_loss_limit_usdt: float | None = None

    def __post_init__(self) -> None:
        if self.max_position_size_usdt <= 0:
            raise ValueError("max_position_size_usdt must be positive")
        if not (0.0 < self.max_drawdown_pct <= 1.0):
            raise ValueError("max_drawdown_pct must be in (0, 1]")
        if self.max_open_positions < 1:
            raise ValueError("max_open_positions must be >= 1")
