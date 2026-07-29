from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests


SYMBOL = os.environ.get("SYMBOL", "BTCUSDT")


def get_ticker(symbol: str = SYMBOL) -> dict[str, Any]:
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


def get_orderbook(symbol: str = SYMBOL, limit: int = 50) -> dict[str, Any]:
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit={limit}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_klines(symbol: str = SYMBOL, interval: str = "1m", limit: int = 200) -> list[dict[str, Any]]:
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    rows = resp.json()
    return [
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
