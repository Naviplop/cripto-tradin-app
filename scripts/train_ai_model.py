import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import requests
import pandas as pd
import pandas_ta as ta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import joblib

ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT / "backend"
MODEL_PATH = BACKEND_DIR / "models" / "trading_model.onnx"
MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

SYMBOL = os.environ.get("SYMBOL", "BTCUSDT")
TIMEFRAME = os.environ.get("TIMEFRAME", "1m")
LOOKBACK_DAYS = int(os.environ.get("TRAIN_LOOKBACK_DAYS", "30"))
WINDOW = 30
FEATURE_COLS = ["close", "volume", "rsi", "macd", "macd_signal", "macd_hist", "ema_fast", "ema_slow"]

BINANCE_BASE = "https://api.binance.com/api/v3/klines"


def download_klines(symbol: str, timeframe: str, days: int) -> pd.DataFrame:
    end = datetime.now(timezone.utc)
    # Binance historical klines endpoint returns up to 1000 candles per request.
    interval_ms = {
        "1m": 60_000,
        "5m": 300_000,
        "15m": 900_000,
        "1h": 3_600_000,
        "4h": 14_400_000,
        "1d": 86_400_000,
    }.get(timeframe, 60_000)

    limit = 1000
    needed = int((days * 24 * 60 * 60 * 1000) / interval_ms)
    rows = []
    current_end = int(end.timestamp() * 1000)

    while len(rows) < needed:
        start = current_end - limit * interval_ms
        params = {
            "symbol": symbol.upper(),
            "interval": timeframe,
            "limit": limit,
            "startTime": max(0, start),
            "endTime": current_end,
        }
        resp = requests.get(BINANCE_BASE, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        rows = data + rows
        current_end = int(data[0][0])
        if len(data) < limit:
            break

    df = pd.DataFrame(rows, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset", "trades", "taker_buy",
        "taker_sell", "ignore",
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df.set_index("open_time", inplace=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    return df.iloc[-needed:] if len(df) > needed else df


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    df.ta.ema(length=10, append=True)
    df.ta.ema(length=30, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)

    df.dropna(inplace=True)
    df["target"] = (df["close"].shift(-1) > df["close"]).astype(int)
    df = df.iloc[:-1]

    df.rename(columns={
        "EMA_10": "ema_fast",
        "EMA_30": "ema_slow",
        "RSI_14": "rsi",
        "MACD_12_26_9": "macd",
        "MACDs_12_26_9": "macd_signal",
        "MACDh_12_26_9": "macd_hist",
    }, inplace=True)
    return df


def make_windows(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    data = df[FEATURE_COLS].values
    targets = df["target"].values

    X, y = [], []
    for i in range(WINDOW, len(data)):
        window = data[i - WINDOW:i]
        X.append(window.flatten())
        y.append(targets[i - 1])
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


def main():
    print(f"Downloading {LOOKBACK_DAYS} days of {SYMBOL} {TIMEFRAME} klines...")
    df = download_klines(SYMBOL, TIMEFRAME, LOOKBACK_DAYS)
    print(f"Downloaded {len(df)} candles")

    df = build_features(df)
    print(f"Features built, rows: {len(df)}")

    X, y = make_windows(df)
    print(f"Windows created: X={X.shape}, y={y.shape}")

    if len(X) < 100:
        print("Not enough data to train. Increase TRAIN_LOOKBACK_DAYS.")
        sys.exit(1)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

    model = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        random_state=42,
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    print("\nClassification report:")
    print(classification_report(y_test, y_pred))

    initial_type = [("float_input", FloatTensorType([None, WINDOW * len(FEATURE_COLS)]))]
    onnx_model = convert_sklearn(model, initial_types=initial_type, options={id(model): {"zipmap": False}})

    MODEL_PATH.write_bytes(onnx_model.SerializeToString())
    print(f"ONNX model exported to: {MODEL_PATH}")

    joblib.dump(model, BACKEND_DIR / "models" / "trading_model_sklearn.pkl")
    print(f"Sklearn model saved to: {BACKEND_DIR / 'models' / 'trading_model_sklearn.pkl'}")


if __name__ == "__main__":
    main()
