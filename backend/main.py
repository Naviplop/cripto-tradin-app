import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from collections import deque

from dotenv import load_dotenv


def load_env() -> None:
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.extend(
            [
                os.path.join(sys._MEIPASS, ".env"),
                os.path.join(sys._MEIPASS, "..", ".env"),
                os.path.join(os.path.dirname(sys.executable), ".env"),
            ]
        )
    for path in candidates:
        if os.path.isfile(path):
            load_dotenv(path, override=False)
            break


load_env()

import pandas as pd
import pandas_ta as ta
import requests
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from trading_engine import TradingEngine, OrderSide, OrderType, Candle
from license_manager import LicenseManager
from market_feed import BinanceMarketFeed
from secure_storage import save_api_keys, load_api_keys, clear_api_keys
from ai_engine import AIPredictor
from logger import logger


def get_base_path() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


BASE_PATH = get_base_path()
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
EXTRA_CORS_ORIGINS = [origin.strip() for origin in os.environ.get("EXTRA_CORS_ORIGINS", "").split(",") if origin.strip()]
DEV_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
CORS_ORIGINS = list({FRONTEND_ORIGIN, *DEV_ORIGINS, *EXTRA_CORS_ORIGINS})

trading_engine = TradingEngine(initial_balance=10000.0)
license_manager = LicenseManager()
market_feed_instance: Optional[BinanceMarketFeed] = None
active_connections: List[WebSocket] = []
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="Crypto Trading Engine")
app.state.limiter = limiter

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=600,
)
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception: {}", exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


class LicenseRequest(BaseModel):
    license_key: str


class ApiKeyRequest(BaseModel):
    api_key: str
    api_secret: str
    paper_mode: bool = True


class OrderRequest(BaseModel):
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    tp: Optional[float] = None
    sl: Optional[float] = None
    stop_price: Optional[float] = None
    limit_price: Optional[float] = None


class ModelUpdateRequest(BaseModel):
    download_url: str
    version: Optional[str] = None


@app.get("/api/market/ticker")
async def market_ticker():
    symbol = os.environ.get("SYMBOL", "BTCUSDT")
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {
        "symbol": data.get("symbol"),
        "price": float(data.get("lastPrice", 0)),
        "priceChangePercent": float(data.get("priceChangePercent", 0)),
        "high": float(data.get("highPrice", 0)),
        "low": float(data.get("lowPrice", 0)),
        "volume": float(data.get("volume", 0)),
        "quoteVolume": float(data.get("quoteVolume", 0)),
    }


@app.get("/api/market/orderbook")
async def market_orderbook(limit: int = 50):
    symbol = os.environ.get("SYMBOL", "BTCUSDT")
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit={limit}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


@app.get("/api/market/klines")
async def market_klines(symbol: str = "BTCUSDT", interval: str = "1m", limit: int = 200):
    return trading_engine.get_candles(symbol=symbol, interval=interval, limit=limit)


@app.get("/api/health")
async def health():
    return {"status": "ok", "license_valid": license_manager.is_valid()}


@app.options("/api/license/validate")
async def validate_license_options():
    return JSONResponse(content={"detail": "OK"}, status_code=200)


@app.post("/api/license/validate")
@limiter.limit("5/minute")
async def validate_license(request: Request, body: LicenseRequest):
    valid = license_manager.validate(body.license_key)
    return {"valid": valid, "message": "License valid" if valid else "Invalid or expired license"}


@app.get("/api/account/balance")
async def get_balance():
    return trading_engine.get_account_summary()


@app.get("/api/account/positions")
async def get_positions():
    return trading_engine.get_positions()


@app.get("/api/account/history")
async def get_history():
    return trading_engine.get_trade_history()


@app.post("/api/trading/order")
async def place_order(request: OrderRequest):
    try:
        order = trading_engine.place_order(
            side=OrderSide(request.side.upper()),
            order_type=OrderType(request.order_type.upper()),
            quantity=request.quantity,
            price=request.price,
            tp=request.tp,
            sl=request.sl,
            stop_price=request.stop_price,
            limit_price=request.limit_price,
        )
        return {"success": True, "order": order}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/trading/signals")
async def get_signals():
    signals = trading_engine.get_current_signals()
    return {"signals": signals}


@app.post("/api/auth/verify-keys")
async def verify_keys(body: ApiKeyRequest):
    try:
        save_api_keys(body.api_key, body.api_secret, body.paper_mode)
        return {"valid": True}
    except Exception as e:
        logger.error("verify_keys failed: %s", repr(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/config/api-keys")
async def save_keys(body: ApiKeyRequest):
    save_api_keys(body.api_key, body.api_secret, body.paper_mode)
    return {"status": "saved"}


@app.get("/api/config/api-keys")
async def get_keys():
    keys = load_api_keys()
    if not keys:
        return {"api_key": None, "api_secret": None, "paper_mode": True}
    return keys


@app.delete("/api/config/api-keys")
async def delete_keys():
    clear_api_keys()
    return {"status": "cleared"}


@app.get("/api/model/status")
async def model_status():
    return {
        "loaded": trading_engine.ai_predictor.is_model_loaded(),
        "features": getattr(trading_engine.ai_predictor, 'feature_names', []),
        "window_size": getattr(trading_engine.ai_predictor, 'window_size', 30),
    }


@app.post("/api/model/update")
async def update_model(body: ModelUpdateRequest):
    try:
        import requests
        resp = requests.get(body.download_url, timeout=30)
        resp.raise_for_status()
        user_models_dir = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'LAFM', 'models')
        os.makedirs(user_models_dir, exist_ok=True)
        model_path = os.path.join(user_models_dir, 'trading_model.onnx')
        with open(model_path, 'wb') as f:
            f.write(resp.content)
        trading_engine.ai_predictor._load_model()
        return {"status": "updated", "path": model_path, "loaded": trading_engine.ai_predictor.is_model_loaded()}
    except Exception as exc:
        logger.error("Model update failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            if message.get("type") == "ping":
                 await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


async def broadcast_market_data(candle: Candle, signals: dict):
    if not active_connections:
        return
    payload = {
        "type": "market_data",
        "candle": {
            "time": candle.timestamp.isoformat(),
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        },
        "signals": signals,
    }
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(payload)
        except Exception:
            disconnected.append(connection)
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


async def broadcast_account_update(account_data: dict):
    if not active_connections:
        return
    payload = {
        "type": "account_update",
        "data": account_data,
    }
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(payload)
        except Exception:
            disconnected.append(connection)
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


trading_engine.set_broadcaster(broadcast_market_data, broadcast_account_update)

market_feed: Optional[BinanceMarketFeed] = None

@app.on_event("startup")
async def startup_event():
    global market_feed
    logger.info("Starting Crypto Trading Engine...")
    if not license_manager.is_valid():
        logger.warning("No valid license found. Application may have limited functionality.")
    market_feed = BinanceMarketFeed(on_candle=trading_engine._process_tick)
    await market_feed.start()
    asyncio.create_task(snapshot_worker())


@app.on_event("shutdown")
async def shutdown_event():
    global market_feed
    if market_feed:
        await market_feed.stop()
    trading_engine.stop()
    logger.info("Trading Engine stopped.")


async def snapshot_worker():
    while True:
        await asyncio.sleep(60)
        try:
            trading_engine.snapshot_account()
        except Exception as exc:
            logger.error("Snapshot worker error: %s", exc)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8765)))
