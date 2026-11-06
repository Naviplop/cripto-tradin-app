from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

import numpy as np

from domain.entities.candle import Candle
from domain.entities.position import Position
from domain.entities.trade import Trade
from domain.value_objects.leverage import Leverage
from domain.value_objects.money import Money
from domain.value_objects.order_side import OrderSide


class ExecutionResult:
    def __init__(self, filled: bool, fill_price: float, fill_quantity: float,
                 fee: float, slippage: float, latency_ms: float, reason: str = "") -> None:
        self.filled = filled
        self.fill_price = fill_price
        self.fill_quantity = fill_quantity
        self.fee = fee
        self.slippage = slippage
        self.latency_ms = latency_ms
        self.reason = reason


class OrderBookSimulator:
    @staticmethod
    def estimate_slippage(
        side: OrderSide,
        order_price: float,
        order_size: float,
        candle: Candle,
        volume: float,
        bps_cap: float = 50.0,
    ) -> tuple[float, float]:
        close = float(candle.close.amount)
        high = float(candle.high.amount)
        low = float(candle.low.amount)
        cvol = max(float(candle.volume), 1e-9)
        depth_ratio = min(order_size / cvol, 1.0)
        range_pct = (high - low) / max(close, 1e-9) if close > 0 else 0
        base_impact = range_pct * 0.5 * depth_ratio
        if side == OrderSide.BUY:
            raw_slippage = base_impact + random.uniform(0, range_pct * 0.1)
        else:
            raw_slippage = -(base_impact + random.uniform(0, range_pct * 0.1))
        bps = raw_slippage * 10000
        bps = max(-bps_cap, min(bps_cap, bps))
        fill_price = order_price * (1 + bps / 10000.0)
        if side == OrderSide.BUY and fill_price > high:
            fill_price = high
        if side == OrderSide.SELL and fill_price < low:
            fill_price = low
        if fill_price <= 0:
            fill_price = close
        return fill_price, abs(bps)


class BacktestPortfolio:
    def __init__(
        self,
        initial_balance: float,
        maker_fee: float = 0.0001,
        taker_fee: float = 0.0001,
        enable_slippage: bool = True,
        enable_latency: bool = True,
        paper_trading: bool = True,
    ) -> None:
        self.initial_balance = float(initial_balance)
        self.cash = float(initial_balance)
        self.maker_fee = float(maker_fee)
        self.taker_fee = float(taker_fee)
        self.enable_slippage = bool(enable_slippage)
        self.enable_latency = bool(enable_latency)
        self.paper_trading = bool(paper_trading)
        self.positions: List[Position] = []
        self.trades: List[Trade] = []
        self.total_fees: float = 0.0
        self.total_slippage: float = 0.0
        self.order_counter = 0
        self.equity_curve: List[tuple[datetime, float]] = []
        self.margin_used: float = 0.0
        self.position_counter = 0
        self.trade_counter = 0

    def _record_equity(self, timestamp: datetime, mark_price: float) -> None:
        unreal = self.unrealized_pnl(mark_price)
        equity = self.cash + unreal
        self.equity_curve.append((timestamp, equity))

    def _time_latency(self) -> float:
        if not self.enable_latency:
            return 0.0
        return random.uniform(20.0, 120.0)

    def execute_market(
        self,
        side: OrderSide,
        quantity: float,
        candle: Candle,
        leverage: Optional[Leverage] = None,
        is_taker: bool = True,
    ) -> ExecutionResult:
        if quantity <= 0:
            return ExecutionResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Invalid quantity")
        order_price = float(candle.close.amount)
        volume = max(float(candle.volume), 1e-9)
        if self.enable_slippage:
            fill_price, bps = OrderBookSimulator.estimate_slippage(
                side, order_price, quantity, candle, volume
            )
        else:
            fill_price, bps = order_price, 0.0
        slippage_abs = abs(fill_price - order_price) * quantity
        self.total_slippage += slippage_abs
        latency = self._time_latency()
        fee_rate = self.taker_fee if is_taker else self.maker_fee
        notional = fill_price * quantity
        fee = notional * fee_rate
        if self.cash < notional + fee:
            return ExecutionResult(False, 0.0, 0.0, 0.0, 0.0, latency, "Insufficient cash")
        self.cash -= notional + fee
        self.total_fees += fee
        self.position_counter += 1
        pos = Position(
            id=self.position_counter,
            side=side,
            entry_price=Money(fill_price),
            quantity=quantity,
        )
        pos.leverage = leverage
        self.positions.append(pos)
        self._record_equity(candle.timestamp, fill_price)
        return ExecutionResult(True, fill_price, quantity, fee, slippage_abs, latency)

    def execute_limit(
        self,
        side: OrderSide,
        quantity: float,
        limit_price: float,
        candle: Candle,
        leverage: Optional[Leverage] = None,
        is_taker: bool = False,
    ) -> ExecutionResult:
        if quantity <= 0:
            return ExecutionResult(False, 0.0, 0.0, 0.0, 0.0, 0.0, "Invalid quantity")
        close = float(candle.close.amount)
        high = float(candle.high.amount)
        low = float(candle.low.amount)
        filled = False
        fill_price = limit_price
        latency = self._time_latency()
        effective_low = low
        effective_high = high
        if self.enable_slippage and is_taker:
            volume = max(float(candle.volume), 1e-9)
            effective_fill, bps = OrderBookSimulator.estimate_slippage(
                side, limit_price, quantity, candle, volume, bps_cap=20.0
            )
            fill_price = effective_fill
            self.total_slippage += abs(fill_price - limit_price) * quantity
        elif side == OrderSide.BUY and limit_price >= low:
            fill_price = limit_price
            filled = True
        elif side == OrderSide.SELL and limit_price <= high:
            fill_price = limit_price
            filled = True
        if not filled:
            return ExecutionResult(False, 0.0, 0.0, 0.0, 0.0, latency,
                                  f"Limit not reached: {limit_price} vs {low}-{high}")
        fee_rate = self.taker_fee if is_taker else self.maker_fee
        notional = fill_price * quantity
        fee = notional * fee_rate
        if self.cash < notional + fee:
            return ExecutionResult(False, 0.0, 0.0, 0.0, 0.0, latency, "Insufficient cash")
        self.cash -= notional + fee
        self.total_fees += fee
        self.position_counter += 1
        pos = Position(
            id=self.position_counter,
            side=side,
            entry_price=Money(fill_price),
            quantity=quantity,
        )
        pos.leverage = leverage
        self.positions.append(pos)
        self._record_equity(candle.timestamp, fill_price)
        return ExecutionResult(True, fill_price, quantity, fee,
                               abs(fill_price - limit_price) * quantity, latency)

    def close_position(
        self,
        position: Position,
        candle: Candle,
        reason: str = "signal",
        partial_quantity: Optional[float] = None,
    ) -> Optional[ExecutionResult]:
        if position not in self.positions:
            return None
        side = position.side
        if partial_quantity is not None:
            qty = max(partial_quantity, 1e-12)
            qty = min(qty, position.quantity)
        else:
            qty = position.quantity
        close_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
        latency = self._time_latency()
        close_price, bps = OrderBookSimulator.estimate_slippage(
            close_side, float(candle.close.amount), qty, candle,
            max(float(candle.volume), 1e-9)
        )
        slippage_abs = abs(close_price - float(candle.close.amount)) * qty
        self.total_slippage += slippage_abs
        fee_rate = self.taker_fee
        notional = close_price * qty
        fee = notional * fee_rate
        self.total_fees += fee
        self.cash += notional - fee
        self.trade_counter += 1
        pnl = 0.0
        if side == OrderSide.BUY:
            pnl = (close_price - float(position.entry_price.amount)) * qty
        else:
            pnl = (float(position.entry_price.amount) - close_price) * qty
        trade = Trade(
            id=f"BT-{self.trade_counter:06d}",
            side=side,
            entry_price=Money(float(position.entry_price.amount)),
            exit_price=Money(close_price),
            quantity=qty,
            pnl=Money(pnl),
            timestamp=candle.timestamp,
            fees=Money(fee),
        )
        self.trades.append(trade)
        if partial_quantity is not None:
            position.quantity -= qty
            if position.quantity <= 1e-12:
                self.positions.remove(position)
        else:
            self.positions.remove(position)
        self._record_equity(candle.timestamp, close_price)
        return ExecutionResult(True, close_price, qty, fee, slippage_abs, latency, reason)

    def update_trailing_stops(self, candle: Candle, trail_pct: float = 0.02) -> None:
        if not self.positions or trail_pct <= 0:
            return
        price = float(candle.close.amount)
        for pos in list(self.positions):
            if pos.sl is None:
                continue
            current_sl = float(pos.sl.amount)
            if pos.side == OrderSide.BUY:
                new_sl = max(current_sl, price * (1 - trail_pct))
                if new_sl > current_sl:
                    pos.sl = Money(new_sl)
            else:
                new_sl = min(current_sl, price * (1 + trail_pct))
                if new_sl < current_sl:
                    pos.sl = Money(new_sl)

    def check_tp_sl(self, candle: Candle) -> List[ExecutionResult]:
        results: List[ExecutionResult] = []
        high = float(candle.high.amount)
        low = float(candle.low.amount)
        for pos in list(self.positions):
            if pos.tp is not None and pos.sl is not None:
                tp = float(pos.tp.amount)
                sl = float(pos.sl.amount)
                if pos.side == OrderSide.BUY:
                    if low <= sl <= high:
                        res = self.close_position(pos, candle, reason="stop_loss")
                        if res:
                            results.append(res)
                        continue
                    if low <= tp <= high:
                        res = self.close_position(pos, candle, reason="take_profit")
                        if res:
                            results.append(res)
                        continue
                else:
                    if low <= sl <= high:
                        res = self.close_position(pos, candle, reason="stop_loss")
                        if res:
                            results.append(res)
                        continue
                    if low <= tp <= high:
                        res = self.close_position(pos, candle, reason="take_profit")
                        if res:
                            results.append(res)
                        continue
            elif pos.tp is not None:
                tp = float(pos.tp.amount)
                if pos.side == OrderSide.BUY and low <= tp <= high:
                    res = self.close_position(pos, candle, reason="take_profit")
                    if res:
                        results.append(res)
                elif pos.side == OrderSide.SELL and low <= tp <= high:
                    res = self.close_position(pos, candle, reason="take_profit")
                    if res:
                        results.append(res)
            elif pos.sl is not None:
                sl = float(pos.sl.amount)
                if pos.side == OrderSide.BUY and low <= sl <= high:
                    res = self.close_position(pos, candle, reason="stop_loss")
                    if res:
                        results.append(res)
                elif pos.side == OrderSide.SELL and low <= sl <= high:
                    res = self.close_position(pos, candle, reason="stop_loss")
                    if res:
                        results.append(res)
        return results

    def unrealized_pnl(self, mark_price: float) -> float:
        total = 0.0
        for pos in self.positions:
            if pos.side == OrderSide.BUY:
                total += (mark_price - float(pos.entry_price.amount)) * pos.quantity
            else:
                total += (float(pos.entry_price.amount) - mark_price) * pos.quantity
        return total

    def total_equity(self, mark_price: float) -> float:
        return self.cash + self.unrealized_pnl(mark_price)

    def reset(self) -> None:
        self.cash = self.initial_balance
        self.positions = []
        self.trades = []
        self.total_fees = 0.0
        self.total_slippage = 0.0
        self.order_counter = 0
        self.position_counter = 0
        self.trade_counter = 0
        self.equity_curve = []
        self.margin_used = 0.0
