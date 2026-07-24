import asyncio
import json
import logging
import os
from datetime import datetime
from typing import Awaitable, Callable, Optional

import websockets

from trading_engine import Candle

from logger import logger

BINANCE_WS_URL = os.environ.get(
    "BINANCE_WS_URL", "wss://stream.binance.com:9443/ws/btcusdt@kline_1m"
)
SYMBOL = os.environ.get("SYMBOL", "BTCUSDT")
TIMEFRAME = os.environ.get("TIMEFRAME", "1m")
RECONNECT_DELAY_BASE = 1
RECONNECT_DELAY_MAX = 30
SIM_FALLBACK_INTERVAL = 30


class BinanceMarketFeed:
    def __init__(
        self,
        on_candle: Callable[[Candle], Awaitable[None]],
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ):
        self.on_candle = on_candle
        self.symbol = (symbol or SYMBOL).lower()
        self.timeframe = timeframe or TIMEFRAME
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._sim_task: Optional[asyncio.Task] = None
        self._use_simulation = False
        self._consecutive_errors = 0
        self._last_real_candle_time: Optional[str] = None

    async def start(self):
        self.running = True
        await self._fetch_historical_candles()
        self._task = asyncio.create_task(self._run_websocket())
        logger.info("BinanceMarketFeed started for %s/%s", self.symbol, self.timeframe)

    async def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._sim_task:
            self._sim_task.cancel()
            try:
                await self._sim_task
            except asyncio.CancelledError:
                pass
        logger.info("BinanceMarketFeed stopped")

    async def _run_websocket(self):
        while self.running:
            try:
                await self._connect_and_listen()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._consecutive_errors += 1
                logger.error(
                    "WebSocket error (%d consecutive): %s",
                    self._consecutive_errors,
                    e,
                )
                if self._consecutive_errors >= 5:
                    logger.warning(
                        "Too many consecutive errors, switching to simulation fallback"
                    )
                    self._use_simulation = True
                    self._start_simulation_fallback()
                    return
                delay = min(
                    RECONNECT_DELAY_BASE * (2 ** (self._consecutive_errors - 1)),
                    RECONNECT_DELAY_MAX,
                )
                logger.info("Reconnecting in %d seconds...", delay)
                await asyncio.sleep(delay)

    async def _connect_and_listen(self):
        stream_name = f"{self.symbol}@kline_{self.timeframe}"
        ws_url = f"wss://stream.binance.com:9443/ws/{stream_name}"
        logger.info("Connecting to Binance WebSocket: %s", ws_url)

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
            self._consecutive_errors = 0
            self._use_simulation = False
            if self._sim_task:
                self._sim_task.cancel()
                self._sim_task = None
            logger.info("Connected to Binance WebSocket stream")

            async for raw_message in ws:
                if not self.running:
                    break
                try:
                    msg = json.loads(raw_message)
                    kline = msg.get("k", {})
                    if not kline:
                        continue

                    event_time = msg.get("E", 0)
                    is_closed = kline.get("x", False)

                    kline_start = kline.get("t", 0)

                    if self._last_real_candle_time == str(kline_start):
                        continue
                    self._last_real_candle_time = str(kline_start)

                    candle = Candle(
                        timestamp=datetime.utcfromtimestamp(kline_start / 1000),
                        open=float(kline.get("o", 0)),
                        high=float(kline.get("h", 0)),
                        low=float(kline.get("l", 0)),
                        close=float(kline.get("c", 0)),
                        volume=float(kline.get("v", 0)),
                    )
                    await self.on_candle(candle)

                    if not is_closed:
                        self._last_real_candle_time = None

                except json.JSONDecodeError:
                    logger.warning("Received non-JSON message from Binance")
                except Exception as e:
                    logger.error("Error processing market data: %s", e)

    async def _fetch_historical_candles(self):
        url = f"https://api.binance.com/api/v3/klines?symbol={self.symbol.upper()}&interval={self.timeframe}&limit=200"
        try:
            import requests
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            rows = resp.json()
            for r in rows:
                candle = Candle(
                    timestamp=datetime.utcfromtimestamp(r[0] / 1000),
                    open=float(r[1]),
                    high=float(r[2]),
                    low=float(r[3]),
                    close=float(r[4]),
                    volume=float(r[5]),
                )
                await self.on_candle(candle)
            logger.info("Cold start: loaded %d historical candles", len(rows))
        except Exception as exc:
            logger.warning("Cold start failed (%s). Proceeding with empty buffer.", exc)

    def _start_simulation_fallback(self):
        if self._sim_task and not self._sim_task.done():
            return
        logger.info("Starting simulation fallback for market data")
        self._sim_task = asyncio.create_task(self._run_simulation_fallback())

    async def _run_simulation_fallback(self):
        import random
        from datetime import timedelta

        logger.info("Simulation fallback active for market data")
        base_time = datetime.utcnow() - timedelta(minutes=30)
        base_price = 67500.0
        current_price = base_price

        for i in range(30):
            t = base_time + timedelta(minutes=i)
            o = current_price + random.uniform(-50, 50)
            c = o + random.uniform(-100, 100)
            h = max(o, c) + random.uniform(0, 50)
            l = min(o, c) - random.uniform(0, 50)
            v = random.uniform(10, 100)
            candle = Candle(
                timestamp=t,
                open=o,
                high=h,
                low=l,
                close=c,
                volume=v,
            )
            current_price = c
            try:
                await self.on_candle(candle)
            except Exception as e:
                logger.error("Simulation fallback candle error: %s", e)

        while self.running:
            await asyncio.sleep(60)
            last_close = current_price
            volatility = 30.0
            new_close = last_close + random.uniform(-volatility, volatility)
            new_high = max(last_close, new_close) + random.uniform(0, 15)
            new_low = min(last_close, new_close) - random.uniform(0, 15)
            new_volume = random.uniform(10, 100)

            candle = Candle(
                timestamp=datetime.utcnow(),
                open=last_close,
                high=new_high,
                low=new_low,
                close=new_close,
                volume=new_volume,
            )
            current_price = new_close
            try:
                await self.on_candle(candle)
            except Exception as e:
                logger.error("Simulation fallback candle error: %s", e)

    @property
    def is_using_simulation(self) -> bool:
        return self._use_simulation


async def create_feed(on_candle: Callable[[Candle], Awaitable[None]]) -> BinanceMarketFeed:
    feed = BinanceMarketFeed(on_candle=on_candle)
    await feed.start()
    return feed