from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from uvicorn import Config, Server

# Config
from config.settings import get_settings, Settings
from config.dependencies import (
    get_settings_dep,
    get_unit_of_work,
    get_trade_repository,
    get_position_repository,
    get_license_repository,
    get_market_data_repository,
    get_model_repository,
    get_account_repository,
    get_risk_engine,
)

# Domain
from domain.entities.candle import Candle
from domain.entities.order import Order, OrderSide, OrderType, OrderStatus
from domain.entities.position import Position
from domain.entities.trade import Trade
from domain.entities.account import Account
from domain.events import OrderPlaced, PositionClosed, MarketDataReceived
from domain.repositories.interfaces import (
    IAccountRepository,
    ILicenseRepository,
    IMarketDataRepository,
    IModelRepository,
    IPositionRepository,
    ITradeRepository,
)
from domain.services import RiskEngine
from domain.value_objects.money import Money

# Infrastructure
from infrastructure.ai.onnx_runtime import ONNXInferenceEngine
from infrastructure.market_data.binance_ws import BinanceMarketFeed
from infrastructure.security.hwid import get_hardware_id
from infrastructure.security.license_crypto import validate_license_key, build_license
from infrastructure.persistence.sqlalchemy import (
    Base,
    UnitOfWork,
)

# Presentation
from presentation.middlewares.exception_handlers import register_exception_handlers
from presentation.middlewares.rate_limit import setup_middlewares
from presentation.routers import (
    admin_router,
    auth_router,
    config_router,
    health_router,
    license_router,
    market_router,
    model_router,
    trading_commands_router,
    trading_queries_router,
)
from backtest.api_routes import router as backtest_router

# Legacy storage (for backward compatibility)
from storage import initialize_db

logger = logging.getLogger(__name__)

settings = get_settings()

app_state: dict[str, Any] = {}

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
    BASE_PATH = sys._MEIPASS

FRONTEND_ORIGIN = settings.frontend_origin
EXTRA_CORS_ORIGINS = [o.strip() for o in settings.extra_cors_origins.split(",") if o.strip()]
DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8765",
    "http://127.0.0.1:8765",
]
ALL_CORS_ORIGINS = list(set([FRONTEND_ORIGIN] + EXTRA_CORS_ORIGINS + DEV_ORIGINS))

TRADING_APP_DATA_DIR = settings.trading_app_data_dir or os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "LAFM"
)
LICENSE_REGISTRY_PATH = os.path.join(TRADING_APP_DATA_DIR, "licenses_registry.json")
ADMIN_API_KEY = settings.admin_api_key
os.makedirs(TRADING_APP_DATA_DIR, exist_ok=True)

DATABASE_URL = f"sqlite+aiosqlite:///{os.path.join(TRADING_APP_DATA_DIR, 'trading_app.db')}"

from infrastructure.persistence.sqlalchemy.unit_of_work import (
    UnitOfWork as SQLAlchemyUnitOfWork,
    create_session_factory,
)
uow_factory = create_session_factory(DATABASE_URL)


class TradingEngine:
    """
    Main trading engine that orchestrates market data, signals, orders, and positions.
    Uses domain entities and infrastructure services.
    """
    def __init__(self) -> None:
        self.balance = 10000.0
        self.initial_balance = 10000.0
        self.positions: List[Position] = []
        self.orders: List[Order] = []
        self.trade_history: List[Trade] = []
        self.candles: List[Candle] = []
        self.running = False
        self.broadcast_market: Optional[Any] = None
        self.broadcast_account: Optional[Any] = None
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
        self.ai_predictor = ONNXInferenceEngine()
        self._load_state()

    def _load_state(self) -> None:
        try:
            from sqlalchemy import select
            from infrastructure.persistence.sqlalchemy.models import (
                AccountSnapshotORM, PositionORM, TradeORM
            )
            
            with engine.connect() as conn:
                latest_snapshot = conn.execute(
                    select(AccountSnapshotORM).order_by(AccountSnapshotORM.timestamp.desc()).limit(1)
                ).first()
                if latest_snapshot:
                    self.balance = latest_snapshot.balance
                    self.initial_balance = latest_snapshot.initial_balance

                open_positions = conn.execute(
                    select(PositionORM).where(PositionORM.closed_at.is_(None))
                ).all()
                for pos_orm in open_positions:
                    position = Position(
                        id=pos_orm.id,
                        side=OrderSide(pos_orm.side),
                        entry_price=Money(pos_orm.entry_price, "USDT"),
                        quantity=pos_orm.quantity,
                        tp=Money(pos_orm.tp, "USDT") if pos_orm.tp else None,
                        sl=Money(pos_orm.sl, "USDT") if pos_orm.sl else None,
                        unrealized_pnl=Money(pos_orm.unrealized_pnl, "USDT"),
                        timestamp=pos_orm.timestamp,
                    )
                    self.positions.append(position)

                trade_history = conn.execute(
                    select(TradeORM).order_by(TradeORM.timestamp.desc()).limit(1000)
                ).all()
                for trade_orm in trade_history:
                    trade = Trade(
                        id=f"TRD-{trade_orm.id:06d}",
                        side=OrderSide(trade_orm.side),
                        entry_price=Money(trade_orm.entry_price, "USDT"),
                        exit_price=Money(trade_orm.exit_price, "USDT"),
                        quantity=trade_orm.quantity,
                        pnl=Money(trade_orm.pnl, "USDT"),
                        timestamp=trade_orm.timestamp,
                    )
                    self.trade_history.append(trade)
                
                if self.trade_history:
                    self.trade_counter = max(int(t.id.split("-")[1]) for t in self.trade_history)

            logger.info("Loaded state: balance=%.2f, positions=%d, trades=%d", self.balance, len(self.positions), len(self.trade_history))
        except Exception as e:
            logger.error("Failed to load state from storage: %s", e)

    def get_account_summary(self) -> dict:
        total_unrealized = sum(p.unrealized_pnl.to_float() for p in self.positions)
        return {
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "unrealized_pnl": total_unrealized,
            "total_equity": self.balance + total_unrealized,
            "positions_count": len(self.positions),
        }

    def get_positions(self) -> List[dict]:
        return [
            {
                "id": p.id,
                "side": p.side.value,
                "entry_price": p.entry_price.to_float(),
                "quantity": p.quantity,
                "unrealized_pnl": p.unrealized_pnl.to_float(),
                "tp": p.tp.to_float() if p.tp else None,
                "sl": p.sl.to_float() if p.sl else None,
                "timestamp": p.timestamp.isoformat(),
            }
            for p in self.positions
        ]

    def get_trade_history(self) -> List[dict]:
        return [
            {
                "id": t.id,
                "side": t.side.value,
                "entry_price": t.entry_price.to_float(),
                "exit_price": t.exit_price.to_float(),
                "quantity": t.quantity,
                "pnl": t.pnl.to_float(),
                "timestamp": t.timestamp.isoformat(),
            }
            for t in self.trade_history
        ]

    def place_order(self, side: OrderSide, order_type: OrderType, quantity: float,
                    price: Optional[float] = None, tp: Optional[float] = None,
                    sl: Optional[float] = None, stop_price: Optional[float] = None,
                    limit_price: Optional[float] = None) -> dict:
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
            price=Money(price, "USDT") if price else None,
            tp=Money(tp, "USDT") if tp else None,
            sl=Money(sl, "USDT") if sl else None,
            stop_price=Money(stop_price, "USDT") if stop_price else None,
            limit_price=Money(limit_price, "USDT") if limit_price else None,
        )
        self.orders.append(order)

        if order_type == OrderType.MARKET:
            order.status = OrderStatus.FILLED
            order.filled_price = Money(self.current_price, "USDT")
            position = Position(
                id=None,
                side=side,
                entry_price=Money(self.current_price, "USDT"),
                quantity=quantity,
                tp=Money(tp, "USDT") if tp else None,
                sl=Money(sl, "USDT") if sl else None,
            )
            self.positions.append(position)
            self._save_position(position)
            logger.info(f"Market order filled: {order.id} at {self.current_price}")
        elif order_type == OrderType.LIMIT:
            order.status = OrderStatus.PENDING
            logger.info(f"Limit order placed: {order.id} at {price}")
        elif order_type == OrderType.STOP_LIMIT:
            order.status = OrderStatus.PENDING
            logger.info(f"Stop-Limit order placed: {order.id} stop={stop_price} limit={limit_price}")
        elif order_type == OrderType.OCO:
            order.status = OrderStatus.PENDING
            logger.info(f"OCO order placed: {order.id} price={price} limit={limit_price}")

        self._notify_account()
        return {
            "id": order.id,
            "status": order.status.value,
            "side": order.side.value,
            "order_type": order.order_type.value,
            "quantity": order.quantity,
            "price": order.filled_price.to_float() if order.filled_price else (order.price.to_float() if order.price else None),
            "tp": tp,
            "sl": sl,
            "stop_price": stop_price,
            "limit_price": limit_price,
        }

    def _save_position(self, position: Position) -> None:
        try:
            from sqlalchemy import insert
            from infrastructure.persistence.sqlalchemy.models import PositionORM
            
            with engine.connect() as conn:
                result = conn.execute(insert(PositionORM).values(
                    side=position.side.value,
                    entry_price=position.entry_price.to_float(),
                    quantity=position.quantity,
                    tp=position.tp.to_float() if position.tp else None,
                    sl=position.sl.to_float() if position.sl else None,
                    unrealized_pnl=position.unrealized_pnl.to_float(),
                    timestamp=position.timestamp,
                ))
                position.id = result.inserted_primary_key[0]
                conn.commit()
        except Exception as e:
            logger.error("Failed to save position: %s", e)

    def close_position(self, position: Position) -> None:
        pnl = Money(0, "USDT")
        if position.side == OrderSide.BUY:
            pnl = (Money(self.current_price, "USDT") - position.entry_price) * position.quantity
        else:
            pnl = (position.entry_price - Money(self.current_price, "USDT")) * position.quantity

        self.balance += pnl.to_float()
        self.trade_counter += 1
        trade = Trade(
            id=f"TRD-{self.trade_counter:06d}",
            side=position.side,
            entry_price=position.entry_price,
            exit_price=Money(self.current_price, "USDT"),
            quantity=position.quantity,
            pnl=pnl,
        )
        self.trade_history.append(trade)
        self._save_trade(trade)
        self._close_position_in_db(position.id)
        self.positions.remove(position)
        logger.info(f"Position closed: {trade.id} PnL: {pnl.to_float():.2f}")
        self._notify_account()

    def _save_trade(self, trade: Trade) -> None:
        try:
            from sqlalchemy import insert
            from infrastructure.persistence.sqlalchemy.models import TradeORM
            
            with engine.connect() as conn:
                conn.execute(insert(TradeORM).values(
                    side=trade.side.value,
                    entry_price=trade.entry_price.to_float(),
                    exit_price=trade.exit_price.to_float(),
                    quantity=trade.quantity,
                    pnl=trade.pnl.to_float(),
                    timestamp=trade.timestamp,
                ))
                conn.commit()
        except Exception as e:
            logger.error("Failed to save trade: %s", e)

    def _close_position_in_db(self, position_id: Optional[int]) -> None:
        if position_id is None:
            return
        try:
            from sqlalchemy import update
            from infrastructure.persistence.sqlalchemy.models import PositionORM
            
            with engine.connect() as conn:
                conn.execute(update(PositionORM).where(PositionORM.id == position_id).values(
                    closed_at=datetime.now(timezone.utc),
                    close_price=self.current_price,
                    realized_pnl=0.0,
                ))
                conn.commit()
        except Exception as e:
            logger.error("Failed to close position in DB: %s", e)

    def update_positions(self) -> None:
        if not self.positions or self.current_price <= 0:
            return
        for position in list(self.positions):
            if position.side == OrderSide.BUY:
                position.unrealized_pnl = (Money(self.current_price, "USDT") - position.entry_price) * position.quantity
                if position.tp and self.current_price >= position.tp.to_float():
                    logger.info(f"Take-Profit hit at {self.current_price}")
                    self.close_position(position)
                elif position.sl and self.current_price <= position.sl.to_float():
                    logger.info(f"Stop-Loss hit at {self.current_price}")
                    self.close_position(position)
            else:
                position.unrealized_pnl = (position.entry_price - Money(self.current_price, "USDT")) * position.quantity
                if position.tp and self.current_price <= position.tp.to_float():
                    logger.info(f"Take-Profit hit at {self.current_price}")
                    self.close_position(position)
                elif position.sl and self.current_price >= position.sl.to_float():
                    logger.info(f"Stop-Loss hit at {self.current_price}")
                    self.close_position(position)

    def _generate_signals(self) -> tuple:
        if len(self.candles) < 30:
            self.signal_state = {"signal": "NEUTRAL", "ma_fast": 0, "ma_slow": 0, "rsi": 50, "ai_probability": 0.5, "combined_signal": "NEUTRAL"}
            return self.signal_state, []

        df_rows = [
            {"time": c.timestamp, "open": c.open.to_float(), "high": c.high.to_float(), "low": c.low.to_float(), "close": c.close.to_float(), "volume": c.volume}
            for c in self.candles
        ]
        import pandas as pd
        import numpy as np
        import pandas_ta as ta

        df = pd.DataFrame(df_rows)
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
        prev = df.iloc[-2] if len(df) >= 2 else latest
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

    def get_current_signals(self) -> dict:
        state = dict(self.signal_state)
        state.setdefault("current_price", self.current_price)
        state.setdefault("atr", 0.0)
        return state

    def get_candles(self, symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 200) -> List[dict]:
        seen = set()
        unique = []
        for c in list(self.candles):
            key = c.timestamp.isoformat()
            if key not in seen:
                seen.add(key)
                unique.append(c)
        local_candles = unique[-limit:]
        return [
            {
                "time": c.timestamp.isoformat(),
                "open": c.open.to_float(),
                "high": c.high.to_float(),
                "low": c.low.to_float(),
                "close": c.close.to_float(),
                "volume": c.volume,
            }
            for c in local_candles
        ]

    async def _process_tick(self, candle: Candle) -> None:
        self.current_price = candle.close.to_float()
        if not self.candles or self.candles[-1].timestamp != candle.timestamp:
            self.candles.append(candle)
        else:
            self.candles[-1] = candle
        self.update_positions()
        signals, enriched = self._generate_signals()
        ai_result = self.ai_predictor.predict(enriched)
        ai_prob = 0.5
        if ai_result.label == "BUY":
            ai_prob = ai_result.confidence
        elif ai_result.label == "SELL":
            ai_prob = 1.0 - ai_result.confidence
        combined = _combine_signal_with_ai(signals.get("signal", "NEUTRAL"), ai_prob)
        signals["ai_probability"] = round(ai_prob, 4)
        signals["combined_signal"] = combined
        signals["current_price"] = self.current_price
        latest = enriched[-1] if enriched else {}
        signals["atr"] = latest.get("atr", 0.0)

        if self.broadcast_market:
            try:
                await self.broadcast_market(candle, signals)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    def stop(self) -> None:
        self.running = False

    def snapshot_account(self) -> None:
        try:
            from sqlalchemy import insert
            from infrastructure.persistence.sqlalchemy.models import AccountSnapshotORM
            
            total_unrealized = sum(p.unrealized_pnl.to_float() for p in self.positions)
            with engine.connect() as conn:
                conn.execute(insert(AccountSnapshotORM).values(
                    balance=self.balance,
                    initial_balance=self.initial_balance,
                    total_equity=self.balance + total_unrealized,
                    timestamp=datetime.now(timezone.utc),
                ))
                conn.commit()
        except Exception as e:
            logger.error("Snapshot account error: %s", e)

    def _notify_account(self) -> None:
        if self.broadcast_account:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.broadcast_account(self.get_account_summary()))
            except RuntimeError:
                pass


class LicenseManager:
    def __init__(self) -> None:
        self.hwid = get_hardware_id()
        self.valid = False
        self.license_data: Optional[dict] = None

    def get_hardware_id(self) -> str:
        return self.hwid

    def validate(self, license_key: str) -> bool:
        if not license_key:
            return False
        valid = validate_license_key(license_key)
        if valid:
            self.valid = True
            self.license_data = {"hwid": self.hwid, "key": license_key}
        return valid

    def is_valid(self) -> bool:
        return self.valid

    def get_license_info(self) -> Optional[dict]:
        if not self.license_data:
            return None
        return {
            "hwid": self.license_data.get("hwid"),
            "expiry": self.license_data.get("expiry"),
            "valid": self.valid,
        }

    def issue_license(self, target_hwid: str, days_valid: int = 365) -> str:
        return build_license(target_hwid, days_valid)


def _load_registry() -> dict:
    if os.path.isfile(LICENSE_REGISTRY_PATH):
        try:
            with open(LICENSE_REGISTRY_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"licenses": [], "revoked": []}


def _save_registry(data: dict) -> None:
    os.makedirs(os.path.dirname(LICENSE_REGISTRY_PATH), exist_ok=True)
    with open(LICENSE_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _check_admin_token(request: Request) -> None:
    token = request.headers.get("X-Admin-Token") or request.query_params.get("admin_token")
    if not ADMIN_API_KEY or token != ADMIN_API_KEY:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")


trading_engine = TradingEngine()
license_manager = LicenseManager()


async def _broadcast_market_data(candle: Candle, signals: dict) -> None:
    for ws in list(app_state.get("market_connections", [])):
        try:
            await ws.send_json({
                "type": "market_data",
                "candle": {
                    "time": candle.timestamp.isoformat(),
                    "open": candle.open.to_float(),
                    "high": candle.high.to_float(),
                    "low": candle.low.to_float(),
                    "close": candle.close.to_float(),
                    "volume": candle.volume,
                },
                "signals": signals,
            })
        except Exception:
            if ws in app_state.get("market_connections", []):
                app_state["market_connections"].remove(ws)


async def _broadcast_account_update(account_data: dict) -> None:
    for ws in list(app_state.get("market_connections", [])):
        try:
            await ws.send_json({
                "type": "account_update",
                "data": account_data,
            })
        except Exception:
            if ws in app_state.get("market_connections", []):
                app_state["market_connections"].remove(ws)


trading_engine.broadcast_market = _broadcast_market_data
trading_engine.broadcast_account = _broadcast_account_update


def _combine_signal_with_ai(tech_signal: str, ai_prob: float) -> str:
    if tech_signal == "BUY" and ai_prob > 0.65:
        return "STRONG_BUY"
    if tech_signal == "SELL" and ai_prob < 0.35:
        return "STRONG_SELL"
    if tech_signal == "BUY" and ai_prob > 0.55:
        return "BUY"
    if tech_signal == "SELL" and ai_prob < 0.45:
        return "SELL"
    return "NEUTRAL"


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    app_state["market_feed"] = None
    app_state["market_connections"] = []
    
    Base.metadata.create_all(engine)
    initialize_db()
    
    market_feed = BinanceMarketFeed(on_candle=trading_engine._process_tick)
    app_state["market_feed"] = market_feed
    await market_feed.start()
    
    logger.info("Trading Engine started with Binance Market Feed")
    
    asyncio.create_task(snapshot_worker())
    
    yield
    
    if app_state.get("market_feed"):
        await app_state["market_feed"].stop()
    trading_engine.stop()
    logger.info("Trading Engine stopped.")


app = FastAPI(title="Crypto Trading Engine", lifespan=lifespan)

setup_middlewares(app)
register_exception_handlers(app)

app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(market_router, prefix="/api/market", tags=["market"])
app.include_router(trading_commands_router, prefix="/api/trading", tags=["trading"])
app.include_router(trading_queries_router, prefix="/api/account", tags=["account"])
app.include_router(license_router, prefix="/api/license", tags=["license"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(config_router, prefix="/api/config", tags=["config"])
app.include_router(model_router, prefix="/api/model", tags=["model"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(backtest_router, prefix="/api/backtest", tags=["backtest"])


@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket) -> None:
    await websocket.accept()
    app_state["market_connections"].append(websocket)
    logger.info("WebSocket client connected")
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        if websocket in app_state["market_connections"]:
            app_state["market_connections"].remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in app_state["market_connections"]:
            app_state["market_connections"].remove(websocket)


async def snapshot_worker() -> None:
    while True:
        await asyncio.sleep(60)
        try:
            trading_engine.snapshot_account()
        except Exception as exc:
            logger.error("Snapshot worker error: %s", exc)


if __name__ == "__main__":
    uvicorn_config = Config(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info",
    )
    server = Server(uvicorn_config)
    asyncio.run(server.serve())