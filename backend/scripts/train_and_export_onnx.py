from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import pandas_ta as ta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

logger = logging.getLogger(__name__)

BINANCE_KLINE_URL = "https://api.binance.com/api/v3/klines"
DEFAULT_SYMBOL = "BTCUSDT"
DEFAULT_INTERVAL = "1m"
DEFAULT_LIMIT = 1000
WINDOW = 30


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def get_models_dir() -> Path:
    return get_project_root() / "backend" / "models"


def download_binance_klines(symbol: str, interval: str, limit: int = DEFAULT_LIMIT) -> pd.DataFrame:
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }
    logger.info("Downloading Binance klines: %s %s limit=%s", symbol, interval, limit)
    response = requests.get(BINANCE_KLINE_URL, params=params, timeout=60)
    response.raise_for_status()
    raw = response.json()
    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_volume", "trades",
        "taker_buy_base", "taker_buy_quote", "ignore",
    ])
    numeric_cols = ["open", "high", "low", "close", "volume", "quote_volume", "trades"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(subset=numeric_cols, inplace=True)
    df.sort_values("open_time", inplace=True)
    df.reset_index(drop=True, inplace=True)
    logger.info("Downloaded %s candles", len(df))
    return df


def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    feature_cols = [
        "close",
        "volume",
        "rsi",
        "atr",
        "ema_fast",
        "ema_slow",
        "log_return",
    ]
    df["rsi"] = df.ta.rsi(length=14, append=False)
    df["atr"] = df.ta.atr(length=14, append=False)
    df["ema_fast"] = df.ta.ema(length=10, append=False)
    df["ema_slow"] = df.ta.ema(length=30, append=False)
    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(subset=feature_cols, inplace=True)
    df.reset_index(drop=True, inplace=True)
    logger.info("Feature rows after dropna=%s", len(df))
    return df


def build_tensor(df: pd.DataFrame, window: int = WINDOW) -> tuple[np.ndarray, np.ndarray]:
    feature_cols = [
        "close",
        "volume",
        "rsi",
        "atr",
        "ema_fast",
        "ema_slow",
        "log_return",
    ]
    if len(df) <= window:
        raise ValueError(f"Not enough rows after feature engineering: {len(df)}")
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    tmp = df[feature_cols].apply(pd.to_numeric, errors="coerce")
    tmp = tmp.iloc[max(0, 40):].reset_index(drop=True)
    df = df.iloc[max(0, 40):].reset_index(drop=True)
    arr = tmp.to_numpy(dtype=float)
    finite_mask = np.isfinite(arr).all(axis=1)
    logger.info("Finite mask count=%s/%s", int(finite_mask.sum()), len(finite_mask))
    logger.info("Feature dtypes=%s", tmp.dtypes.astype(str).to_dict())
    logger.info("Feature nulls=%s", tmp.isna().sum().to_dict())
    if not finite_mask.any():
        bad = np.where(~finite_mask)[0][:5]
        raise ValueError(f"No finite rows. First invalid indices={bad.tolist()}")
    valid_idx = [i for i in range(window, len(tmp)) if finite_mask[i]]
    if not valid_idx:
        bad = np.where(~finite_mask)[0][:5]
        raise ValueError(f"No valid samples generated. First invalid indices={bad.tolist()}")
    X = np.array([tmp.iloc[i - window : i].to_numpy(dtype=float) for i in valid_idx], dtype=np.float32)
    y = []
    for i in valid_idx:
        future_return = (float(df.iloc[i]["close"]) - float(df.iloc[i - 1]["close"])) / float(df.iloc[i - 1]["close"])
        if future_return > 0.001:
            y.append(2)
        elif future_return < -0.001:
            y.append(0)
        else:
            y.append(1)
    logger.info("Valid windows=%s, samples=%s", len(valid_idx), len(X))
    return X, np.array(y, dtype=np.int64)


def train_model(X: np.ndarray, y: np.ndarray) -> Pipeline:
    n_samples = X.shape[0]
    n_features = X.shape[2]
    X_flat = X.reshape(n_samples, n_features * WINDOW)
    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", GradientBoostingClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8, random_state=42)),
    ])
    pipeline.fit(X_flat, y)
    logger.info("Model training complete. Classes=%s", dict(zip(*np.unique(y, return_counts=True))))
    return pipeline


def export_onnx(pipeline: Pipeline, n_features: int, model_path: Path) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    initial_types = [("float_input", FloatTensorType(shape=[1, WINDOW * n_features]))]
    onx = convert_sklearn(pipeline, initial_types=initial_types, target_opset=15)
    with open(model_path, "wb") as f:
        f.write(onx.SerializeToString())
    logger.info("ONNX model exported to %s", model_path)


def save_artifacts(pipeline: Pipeline, features: list[str], models_dir: Path) -> None:
    scaler = pipeline.named_steps["scaler"]
    models_dir.mkdir(parents=True, exist_ok=True)
    with open(models_dir / "feature_names.json", "w", encoding="utf-8") as f:
        json.dump(features, f, indent=2)
    with open(models_dir / "scaler_params.json", "w", encoding="utf-8") as f:
        json.dump({"mean": scaler.mean_.tolist(), "scale": scaler.scale_.tolist()}, f, indent=2)
    logger.info("Artifacts saved to %s", models_dir)


def compute_file_hash(path: Path) -> str:
    sha = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha.update(chunk)
    return sha.hexdigest()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    models_dir = get_models_dir()
    model_path = models_dir / "trading_model.onnx"
    if model_path.exists():
        backup = models_dir / f"trading_model.onnx.bak.{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}"
        model_path.rename(backup)
        logger.info("Backed up existing model to %s", backup)
    df = download_binance_klines(DEFAULT_SYMBOL, DEFAULT_INTERVAL, DEFAULT_LIMIT)
    df = compute_features(df)
    feature_cols = [
        "close",
        "volume",
        "rsi",
        "atr",
        "ema_fast",
        "ema_slow",
        "log_return",
    ]
    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing feature columns: {missing}")
    X, y = build_tensor(df, WINDOW)
    logger.info("Training tensor shape=%s y=%s", X.shape, y.shape)
    pipeline = train_model(X, y)
    export_onnx(pipeline, len(feature_cols), model_path)
    save_artifacts(pipeline, feature_cols, models_dir)
    logger.info("Model hash=%s", compute_file_hash(model_path))
    return 0


if __name__ == "__main__":
    if not Path(get_project_root() / "backend" / ".env").exists():
        logger.warning("backend/.env not found; Binance may apply stricter rate limits.")
    sys.exit(main())
