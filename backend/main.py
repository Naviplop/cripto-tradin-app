from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, List

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from uvicorn import Config, Server

from config.settings import get_settings
from domain.entities.candle import Candle
from domain.entities.order import OrderSide
from domain.events import OrderPlaced, PositionClosed
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
from infrastructure.ai.onnx_runtime import ONNXInferenceEngine
from infrastructure.market_data.binance_ws import BinanceMarketFeed
from infrastructure.security.hwid import get_hardware_id
from infrastructure.security.license_crypto import validate_license_key
from presentation.middlewares.exception_handlers import register_exception_handlers
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

logger = logging.getLogger(__name__)

settings = get_settings()

app_state: dict[str, Any] = {}


def _get_base_path() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = _get_base_path()
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
ALL_CORS_ORIGINS = [FRONTEND_ORIGIN] + EXTRA_CORS_ORIGINS + DEV_ORIGINS
TRADING_APP_DATA_DIR = settings.trading_app_data_dir or os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LAFM")
LICENSE_REGISTRY_PATH = os.path.join(TRADING_APP_DATA_DIR, "licenses_registry.json")
ADMIN_API_KEY = settings.admin_api_key
os.makedirs(TRADING_APP_DATA_DIR, exist_ok=True)

limiter = Limiter(key_func=get_remote_address)


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


class _SimpleEngine:
    def __init__(self) -> None:
        self.balance = 10000.0
        self.initial_balance = 10000.0
        self.positions: list = []
        self.orders: list = []
        self.trade_history: list = []
        self.candles: list = []
        self.running = False
        self.broadcast_market = None
        self.broadcast_account = None
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

    def get_account_summary(self) -> dict:
        total_unrealized = sum(p.get("unrealized_pnl", 0.0) for p in self.positions)
        return {
            "balance": self.balance,
            "initial_balance": self.initial_balance,
            "unrealized_pnl": total_unrealized,
            "total_equity": self.balance + total_unrealized,
            "positions_count": len(self.positions),
        }

    def get_positions(self) -> list:
        return self.positions

    def get_trade_history(self) -> list:
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

    def place_order(self, side, order_type, quantity, price=None, tp=None, sl=None, stop_price=None, limit_price=None) -> dict:
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if order_type == OrderType.LIMIT and price is None:
            raise ValueError("Limit orders require a price")
        if order_type == OrderType.STOP_LIMIT and (stop_price is None or limit_price is None):
            raise ValueError("Stop-Limit orders require stop_price and limit_price")
        if order_type == OrderType.OCO and (price is None or limit_price is None):
            raise ValueError("OCO orders require a price and limit_price")

        self.order_counter += 1
        order = {
            "id": f"ORD-{self.order_counter:06d}",
            "side": side.value,
            "order_type": order_type.value,
            "quantity": quantity,
            "price": price or limit_price,
            "tp": tp,
            "sl": sl,
            "stop_price": stop_price,
            "limit_price": limit_price,
            "status": "PENDING",
        }
        self.orders.append(order)

        if order_type == OrderType.MARKET:
            order["status"] = "FILLED"
            order["filled_price"] = self.current_price
            position = {
                "side": side.value,
                "entry_price": self.current_price,
                "quantity": quantity,
                "tp": tp,
                "sl": sl,
                "unrealized_pnl": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.positions.append(position)
            logger.info(f"Market order filled: {order['id']} at {self.current_price}")
        elif order_type == OrderType.LIMIT:
            order["status"] = "PENDING"
            logger.info(f"Limit order placed: {order['id']} at {price}")
        elif order_type == OrderType.STOP_LIMIT:
            order["status"] = "PENDING"
            logger.info(f"Stop-Limit order placed: {order['id']} stop={stop_price} limit={limit_price}")
        elif order_type == OrderType.OCO:
            order["status"] = "PENDING"
            logger.info(f"OCO order placed: {order['id']} price={price} limit={limit_price}")

        return order

    def close_position(self, position: dict) -> None:
        pnl = 0.0
        if position["side"] == "BUY":
            pnl = (self.current_price - position["entry_price"]) * position["quantity"]
        else:
            pnl = (position["entry_price"] - self.current_price) * position["quantity"]

        self.balance += pnl
        self.trade_counter += 1
        trade = Trade(
            id=f"TRD-{self.trade_counter:06d}",
            side=OrderSide(position["side"]),
            entry_price=Money(position["entry_price"]),
            exit_price=Money(self.current_price),
            quantity=position["quantity"],
            pnl=Money(pnl),
        )
        self.trade_history.append(trade)
        self.positions.remove(position)
        logger.info(f"Position closed: {trade.id} PnL: {pnl:.2f}")

    def update_positions(self) -> None:
        if not self.positions or self.current_price <= 0:
            return
        for position in list(self.positions):
            pnl = 0.0
            if position["side"] == "BUY":
                pnl = (self.current_price - position["entry_price"]) * position["quantity"]
                position["unrealized_pnl"] = pnl
                if position.get("tp") and self.current_price >= position["tp"]:
                    logger.info(f"Take-Profit hit at {self.current_price}")
                    self.close_position(position)
                elif position.get("sl") and self.current_price <= position["sl"]:
                    logger.info(f"Stop-Loss hit at {self.current_price}")
                    self.close_position(position)
            else:
                pnl = (position["entry_price"] - self.current_price) * position["quantity"]
                position["unrealized_pnl"] = pnl
                if position.get("tp") and self.current_price <= position["tp"]:
                    logger.info(f"Take-Profit hit at {self.current_price}")
                    self.close_position(position)
                elif position.get("sl") and self.current_price >= position["sl"]:
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

    def get_candles(self, symbol="BTCUSDT", interval="1m", limit=200) -> list:
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
        ai_prob = self.ai_predictor.predict(enriched)
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
        pass

    def _notify_account(self) -> None:
        if self.broadcast_account:
            try:
                import asyncio
                loop = asyncio.get_running_loop()
                loop.create_task(self.broadcast_account(self.get_account_summary()))
            except RuntimeError:
                pass


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


class _LicenseManager:
    def __init__(self) -> None:
        self.hwid = get_hardware_id()
        self.valid = False
        self.license_data = None

    def get_hardware_id(self) -> str:
        return self.hwid

    def validate(self, license_key: str) -> bool:
        if not license_key:
            return False
        valid = validate_license_key(license_key)
        if valid:
            self.valid = True
        return valid

    def is_valid(self) -> bool:
        return self.valid

    def get_license_info(self) -> dict | None:
        if not self.license_data:
            return None
        return {
            "hwid": self.license_data.get("hwid"),
            "expiry": self.license_data.get("exp"),
            "valid": self.valid,
        }


license_manager = _LicenseManager()


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


def _build_license(target_hwid: str, days_valid: int = 365) -> str:
    from infrastructure.security.license_crypto import build_license
    return build_license(target_hwid, days_valid)


def _check_admin_token(request: Request) -> None:
    token = request.headers.get("X-Admin-Token") or request.query_params.get("admin_token")
    if not ADMIN_API_KEY or token != ADMIN_API_KEY:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Forbidden")


trading_engine = _SimpleEngine()


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    app_state["market_feed"] = None
    app_state["market_connections"] = []
    yield
    if app_state.get("market_feed"):
        await app_state["market_feed"].stop()
    trading_engine.stop()
    logger.info("Trading Engine stopped.")


app = FastAPI(title="Crypto Trading Engine", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)

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
