import asyncio
import os
from datetime import datetime, timedelta, timezone, timezone
from collections import deque
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np
import pandas_ta as ta

from storage import Storage, get_storage
from ai_engine import AIPredictor
from logger import logger

class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LIMIT = "STOP_LIMIT"
    OCO = "OCO"

@dataclass
class Candle:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class Order:
    id: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    tp: Optional[float] = None
    sl: Optional[float] = None
    status: str = "PENDING"
    filled_price: Optional[float] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class Position:
    side: OrderSide
    entry_price: float
    quantity: float
    tp: Optional[float] = None
    sl: Optional[float] = None
    unrealized_pnl: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    db_id: Optional[int] = None


@dataclass
class Trade:
    id: str
    side: OrderSide
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
class TradingEngine:
    def __init__(self, initial_balance: float = 10000.0, db_path: Optional[str] = None):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions: List[Position] = []
        self.orders: List[Order] = []
        self.trade_history: List[Trade] = []
        self.candles: deque = deque(maxlen=300)
        self.running = False
        self.broadcast_market: Optional[Callable] = None
        self.broadcast_account: Optional[Callable] = None
        self.order_counter = 0
        self.trade_counter = 0
        self.current_price = 0.0
        self.signal_state = {
            "ma_fast": 0,
            "ma_slow": 0,
            "rsi": 50,
            "signal": "NEUTRAL",
            "current_price": 0.0,
            "atr": 0.0,
        }
        self._storage = get_storage() if db_path is None else Storage(db_path)
        self._load_state()
        self.ai_predictor = AIPredictor()

    def _load_state(self):
        try:
            snapshot = self._storage.get_latest_balance()
            if snapshot:
                self.balance = snapshot["balance"]
                self.initial_balance = snapshot["initial_balance"]
            open_positions = self._storage.get_open_positions()
            for pos_data in open_positions:
                position = Position(
                    side=OrderSide(pos_data["side"]),
                    entry_price=pos_data["entry_price"],
                    quantity=pos_data["quantity"],
                    tp=pos_data.get("tp"),
                    sl=pos_data.get("sl"),
                    unrealized_pnl=0.0,
                    timestamp=datetime.fromisoformat(pos_data["timestamp"]),
                    db_id=pos_data.get("id"),
                )
                self.positions.append(position)
            trade_history_data = self._storage.get_trade_history(limit=1000)
            for trade_data in trade_history_data:
                trade = Trade(
                    id=trade_data["id"],
                    side=OrderSide(trade_data["side"]),
                    entry_price=trade_data["entry_price"],
                    exit_price=trade_data["exit_price"],
                    quantity=trade_data["quantity"],
                    pnl=trade_data["pnl"],
                    timestamp=datetime.fromisoformat(trade_data["timestamp"]),
                )
                self.trade_history.append(trade)
            if self.trade_history:
                self.trade_counter = max(
                    int(t.id.split("-")[1]) for t in self.trade_history
                )
            logger.info(
                "Loaded state: balance={:.2f}, positions={}, trades={}",
                self.balance,
                len(self.positions),
                len(self.trade_history),
            )
        except Exception as e:
            logger.error("Failed to load state from storage: %s", e)

    def set_broadcaster(self, market_fn: Callable, account_fn: Callable):
        self.broadcast_market = market_fn
        self.broadcast_account = account_fn

    def get_account_summary(self) -> Dict[str, Any]:
        total_unrealized = sum(p.unrealized_pnl for p in self.positions)
        return {
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "unrealized_pnl": total_unrealized,
            "total_equity": self.balance + total_unrealized,
            "positions_count": len(self.positions),
        }

    def get_positions(self) -> List[Dict[str, Any]]:
        return [
            {
                "side": p.side.value,
                "entry_price": p.entry_price,
                "quantity": p.quantity,
                "unrealized_pnl": p.unrealized_pnl,
                "tp": p.tp,
                "sl": p.sl,
                "timestamp": p.timestamp.isoformat(),
            }
            for p in self.positions
        ]

    def get_trade_history(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": t.id,
                "side": t.side.value,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "pnl": t.pnl,
                "timestamp": t.timestamp.isoformat(),
            }
            for t in self.trade_history
        ]

    def place_order(self, side: OrderSide, order_type: OrderType, quantity: float,
                    price: Optional[float] = None, tp: Optional[float] = None,
                    sl: Optional[float] = None, stop_price: Optional[float] = None,
                    limit_price: Optional[float] = None) -> Dict[str, Any]:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Limit orders require a price")
        if order_type == OrderType.STOP_LIMIT and (stop_price is None or limit_price is None):
            raise ValueError("Stop-Limit orders require stop_price and limit_price")
        if order_type == OrderType.OCO and (price is None or limit_price is None):
            raise ValueError("OCO orders require a price and limit_price")

        self.order_counter += 1
        order = Order(
            id=f"ORD-{self.order_counter:06d}",
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price or limit_price,
            tp=tp,
            sl=sl,
        )
        self.orders.append(order)

        if order_type == OrderType.MARKET:
            order.status = "FILLED"
            order.filled_price = self.current_price
            position = Position(
                side=side,
                entry_price=self.current_price,
                quantity=quantity,
                tp=tp,
                sl=sl,
            )
            self.positions.append(position)
            position.db_id = self._storage.save_position(
                side=position.side.value,
                entry_price=position.entry_price,
                quantity=position.quantity,
                tp=position.tp,
                sl=position.sl,
            )
            logger.info(f"Market order filled: {order.id} at {self.current_price}")
        elif order_type == OrderType.LIMIT:
            order.status = "PENDING"
            logger.info(f"Limit order placed: {order.id} at {price}")
        elif order_type == OrderType.STOP_LIMIT:
            order.status = "PENDING"
            logger.info(f"Stop-Limit order placed: {order.id} stop={stop_price} limit={limit_price}")
        elif order_type == OrderType.OCO:
            order.status = "PENDING"
            logger.info(f"OCO order placed: {order.id} price={price} limit={limit_price}")

        self._notify_account()
        return {
            "id": order.id,
            "status": order.status,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "price": order.filled_price or order.price,
            "tp": order.tp,
            "sl": order.sl,
            "stop_price": stop_price,
            "limit_price": limit_price,
        }

    def close_position(self, position: Position):
        pnl = 0.0
        if position.side == OrderSide.BUY:
            pnl = (self.current_price - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - self.current_price) * position.quantity

        self.balance += pnl
        self.trade_counter += 1
        trade = Trade(
            id=f"TRD-{self.trade_counter:06d}",
            side=position.side,
            entry_price=position.entry_price,
            exit_price=self.current_price,
            quantity=position.quantity,
            pnl=pnl,
        )
        self.trade_history.append(trade)
        if hasattr(position, 'db_id') and position.db_id is not None:
            self._storage.delete_position(position.db_id)
        self._storage.save_trade(
            side=position.side.value,
            entry_price=position.entry_price,
            exit_price=self.current_price,
            quantity=position.quantity,
            pnl=pnl,
        )
        self.positions.remove(position)
        logger.info(f"Position closed: {trade.id} PnL: {pnl:.2f}")
        self._notify_account()

    def update_positions(self):
        if not self.positions or self.current_price <= 0:
            return
        for position in list(self.positions):
            if position.side == OrderSide.BUY:
                position.unrealized_pnl = (self.current_price - position.entry_price) * position.quantity
                if position.tp and self.current_price >= position.tp:
                    logger.info(f"Take-Profit hit at {self.current_price}")
                    self.close_position(position)
                elif position.sl and self.current_price <= position.sl:
                    logger.info(f"Stop-Loss hit at {self.current_price}")
                    self.close_position(position)
            else:
                position.unrealized_pnl = (position.entry_price - self.current_price) * position.quantity
                if position.tp and self.current_price <= position.tp:
                    logger.info(f"Take-Profit hit at {self.current_price}")
                    self.close_position(position)
                elif position.sl and self.current_price >= position.sl:
                    logger.info(f"Stop-Loss hit at {self.current_price}")
                    self.close_position(position)

    def _generate_signals(self):
        if len(self.candles) < 30:
            self.signal_state = {"signal": "NEUTRAL", "ma_fast": 0, "ma_slow": 0, "rsi": 50, "ai_probability": 0.5, "combined_signal": "NEUTRAL"}
            return self.signal_state, []

        df = pd.DataFrame([
            {"time": c.timestamp, "open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume}
            for c in self.candles
        ])
        df.set_index("time", inplace=True)
        if getattr(df.index, "tz", None) is not None:
            df.index = df.index.tz_convert("UTC").tz_localize(None)

        df.ta.ema(length=10, append=True)
        df.ta.ema(length=30, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.bbands(length=20, append=True)
        df.ta.atr(length=14, append=True)
        df["log_return"] = np.log(df["close"] / df["close"].shift(1))
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        df.dropna(inplace=True)

        def _rename(prefix, target):
            matches = [c for c in df.columns if str(c).startswith(prefix)]
            if matches:
                df.rename(columns={matches[0]: target}, inplace=True)

        _rename("EMA_10", "ema_fast")
        _rename("EMA_30", "ema_slow")
        _rename("RSI_14", "rsi")
        _rename("MACD_12_26_9", "macd")
        _rename("MACDs_12_26_9", "macd_signal")
        _rename("MACDh_12_26_9", "macd_hist")
        _rename("BBL_", "bb_lower")
        _rename("BBM_", "bb_mid")
        _rename("BBU_", "bb_upper")
        _rename("ATRr_", "atr")

        if df.empty or "ema_fast" not in df.columns or "ema_slow" not in df.columns or "rsi" not in df.columns:
            self.signal_state = {"signal": "NEUTRAL", "ma_fast": 0, "ma_slow": 0, "rsi": 50, "ai_probability": 0.5, "combined_signal": "NEUTRAL"}
            return self.signal_state, []

        latest = df.iloc[-1]
        if len(df) < 2:
            prev = latest
        else:
            prev = df.iloc[-2]
        ma_fast = float(latest["ema_fast"])
        ma_slow = float(latest["ema_slow"])
        rsi = float(latest["rsi"])

        signal = "NEUTRAL"
        if prev["ema_fast"] <= prev["ema_slow"] and latest["ema_fast"] > latest["ema_slow"] and rsi < 70:
            signal = "BUY"
        elif prev["ema_fast"] >= prev["ema_slow"] and latest["ema_fast"] < latest["ema_slow"] and rsi > 30:
            signal = "SELL"

        enriched = []
        for _, row in df.iterrows():
            enriched.append({
                "close": float(row["close"]),
                "volume": float(row["volume"]),
                "rsi": float(row.get("rsi", 50.0)),
                "macd": float(row.get("macd", 0.0)),
                "macd_signal": float(row.get("macd_signal", 0.0)),
                "macd_hist": float(row.get("macd_hist", 0.0)),
                "bb_upper": float(row.get("bb_upper", 0.0)),
                "bb_mid": float(row.get("bb_mid", 0.0)),
                "bb_lower": float(row.get("bb_lower", 0.0)),
                "atr": float(row.get("atr", 0.0)),
                "log_return": float(row.get("log_return", 0.0)),
                "ema_fast": float(row.get("ema_fast", 0.0)),
                "ema_slow": float(row.get("ema_slow", 0.0)),
            })

        self.signal_state = {
            "ma_fast": round(ma_fast, 2),
            "ma_slow": round(ma_slow, 2),
            "rsi": round(rsi, 2),
            "signal": signal,
        }
        return self.signal_state, enriched

    def get_current_signals(self) -> Dict[str, Any]:
        state = dict(self.signal_state)
        state.setdefault("current_price", self.current_price)
        state.setdefault("atr", 0.0)
        return state

    def get_candles(self, symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 200) -> List[Dict[str, Any]]:
        seen = set()
        unique = []
        for c in list(self.candles):
            key = c.timestamp.isoformat()
            if key not in seen:
                seen.add(key)
                unique.append(c)
        local_candles = unique[-limit:]

        try:
            import requests
            url = (
                "https://api.binance.com/api/v3/klines"
                f"?symbol={symbol}&interval={interval}&limit={limit}"
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            rows = resp.json()
            remote_candles = [
                {
                    "time": datetime.fromtimestamp(r[0] / 1000, tz=timezone.utc).isoformat(),
                    "open": float(r[1]),
                    "high": float(r[2]),
                    "low": float(r[3]),
                    "close": float(r[4]),
                    "volume": float(r[5]),
                }
                for r in rows
            ]
            return remote_candles
        except Exception:
            return [
                {
                    "time": c.timestamp.isoformat(),
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in local_candles
            ]

    async def _process_tick(self, candle: Candle):
        self.current_price = candle.close
        if not self.candles or self.candles[-1].timestamp != candle.timestamp:
            self.candles.append(candle)
        else:
            self.candles[-1] = candle
        self.update_positions()
        signals, enriched = self._generate_signals()
        ai_prob = self.ai_predictor.predict(enriched)
        combined = self._combine_signal_with_ai(signals.get("signal", "NEUTRAL"), ai_prob)
        signals["ai_probability"] = round(ai_prob, 4)
        signals["combined_signal"] = combined
        signals["current_price"] = self.current_price
        latest = enriched[-1] if enriched else {}
        signals["atr"] = latest.get("atr", 0.0)

        if enriched:
            self._storage.save_prediction(
                score=ai_prob,
                signal=signals.get("signal", "NEUTRAL"),
                candles_used=len(enriched),
                model_loaded=self.ai_predictor.is_model_loaded(),
            )

        if self.broadcast_market:
            try:
                await self.broadcast_market(candle, signals)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    def _combine_signal_with_ai(self, tech_signal: str, ai_prob: float) -> str:
        if tech_signal == "BUY" and ai_prob > 0.65:
            return "STRONG_BUY"
        if tech_signal == "SELL" and ai_prob < 0.35:
            return "STRONG_SELL"
        if tech_signal == "BUY" and ai_prob > 0.55:
            return "BUY"
        if tech_signal == "SELL" and ai_prob < 0.45:
            return "SELL"
        return "NEUTRAL"

    def snapshot_account(self):
        total_unrealized = sum(p.unrealized_pnl for p in self.positions)
        self._storage.save_account_snapshot(
            balance=self.balance,
            initial_balance=self.initial_balance,
            total_equity=self.balance + total_unrealized,
        )
        for pos in self.positions:
            if hasattr(pos, "db_id") and pos.db_id is not None:
                self._storage.update_position_unrealized_pnl(pos.db_id, pos.unrealized_pnl)

    async def start_simulation(self):
        self.running = True
        logger.info("Starting paper trading simulation...")
        base_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        base_price = 67500.0

        df = pd.DataFrame()
        for i in range(30):
            t = base_time + timedelta(minutes=i)
            o = base_price + np.random.uniform(-50, 50)
            c = o + np.random.uniform(-100, 100)
            h = max(o, c) + np.random.uniform(0, 50)
            l = min(o, c) - np.random.uniform(0, 50)
            v = np.random.uniform(10, 100)
            candle = Candle(timestamp=t, open=o, high=h, low=l, close=c, volume=v)
            self.candles.append(candle)
            self.current_price = c

        while self.running:
            last = self.candles[-1]
            volatility = 30.0
            new_close = last.close + np.random.uniform(-volatility, volatility)
            new_high = max(last.high, new_close) + np.random.uniform(0, 15)
            new_low = min(last.low, new_close) - np.random.uniform(0, 15)
            new_volume = np.random.uniform(10, 100)

            if (datetime.now(timezone.utc) - last.timestamp).total_seconds() >= 60:
                new_candle = Candle(
                    timestamp=last.timestamp + timedelta(minutes=1),
                    open=last.close,
                    high=new_high,
                    low=new_low,
                    close=new_close,
                    volume=new_volume,
                )
                await self._process_tick(new_candle)
            else:
                updated = Candle(
                    timestamp=last.timestamp,
                    open=last.open,
                    high=max(last.high, new_high),
                    low=min(last.low, new_low),
                    close=new_close,
                    volume=last.volume + new_volume,
                )
                self.candles[-1] = updated
                await self._process_tick(updated)

            await asyncio.sleep(1)

    def stop(self):
        self.running = False

    def _notify_account(self):
        if self.broadcast_account:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.broadcast_account(self.get_account_summary()))
            except RuntimeError:
                pass
