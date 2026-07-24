"""
train_and_export_onnx.py

Pipeline de entrenamiento y exportación ONNX para el Crypto Trading Terminal.

- Acepta datos OHLCV externos o genera datos sintéticos de prueba.
- Calculafeatures técnicas: RSI, MACD, Bandas de Bollinger, ATR, Retornos logarítmicos.
- Entrena RandomForest multiclase (0=Vender, 1=Mantener, 2=Comprar) con split temporal.
- Exporta a ONNX (input `float_input`, shape `[None, num_features]`, float32).
- Guarda `scaler_params.json` con media y escala del StandardScaler.
- Verifica que ONNX Runtime replique las probabilidades del modelo nativo.
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal, Optional, Tuple

import numpy as np
import pandas as pd
import pandas_ta as ta
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

try:
    import onnxruntime as ort
    HAS_ORT = True
except ImportError:
    HAS_ORT = False


# ---------------------------
# Configuración global
# ---------------------------
ROLLING_WINDOW: int = 30
FORECAST_HORIZON: int = 3
THRESHOLD_BUY: float = 0.005  # +0.5% → COMPRAR
THRESHOLD_SELL: float = -0.005  # -0.5% → VENDER
RANDOM_STATE: int = 42
TEST_SIZE: float = 0.2


# ---------------------------
# Datos
# ---------------------------
def generate_synthetic_data(
    n_rows: int = 5000,
    seed: int = 42,
) -> pd.DataFrame:
    """Genera velas sintéticas estables para pruebas."""
    rng = np.random.default_rng(seed)

    base_price = 100.0
    returns = rng.normal(0.0, 0.015, n_rows)
    returns = np.clip(returns, -0.05, 0.05)
    price = base_price * np.cumprod(1.0 + returns)
    price = np.clip(price, 1e-6, None)

    high = price * (1.0 + np.abs(rng.normal(0.0, 0.005, n_rows)))
    low = price * (1.0 - np.abs(rng.normal(0.0, 0.005, n_rows)))
    open_ = price + rng.normal(0.0, 0.002, n_rows)
    volume = rng.lognormal(mean=10.0, sigma=1.0, size=n_rows)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": price,
            "volume": volume,
        }
    )
    return df


def load_data(
    df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Acepta un DataFrame OHLCV externo o genera datos sintéticos.
    Columnas requeridas: open, high, low, close, volume.
    """
    if df is None or df.empty:
        print("No data provided. Generating synthetic OHLCV data...")
        df = generate_synthetic_data()
    required = {"open", "high", "low", "close", "volume"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing columns: {required - set(df.columns)}")
    return df.copy()


# ---------------------------
# Features
# ---------------------------
def _rename_by_prefix(df: pd.DataFrame, prefix: str, new_name: str) -> None:
    candidates = [c for c in df.columns if c.startswith(prefix)]
    if not candidates:
        raise ValueError(f"Missing feature '{prefix}'. Computed columns: {df.columns.tolist()}")
    df.rename(columns={candidates[0]: new_name}, inplace=True)


def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega indicadores técnicos y elimina valores nulos."""
    df = df.copy()
    df.ta.ema(length=10, append=True)
    df.ta.ema(length=30, append=True)
    df.ta.rsi(length=14, append=True)
    df.ta.macd(append=True)
    df.ta.bbands(length=20, append=True)
    df.ta.atr(length=14, append=True)

    df["log_return"] = np.log(df["close"] / df["close"].shift(1))
    df["ret_fwd"] = (df["close"].shift(-FORECAST_HORIZON) / df["close"]) - 1

    df.replace([np.inf, -np.inf], np.nan, inplace=True)
    df.dropna(inplace=True)

    _rename_by_prefix(df, "EMA_10", "ema_fast")
    _rename_by_prefix(df, "EMA_30", "ema_slow")
    _rename_by_prefix(df, "RSI_14", "rsi")
    _rename_by_prefix(df, "MACD_12_26_9", "macd")
    _rename_by_prefix(df, "MACDs_12_26_9", "macd_signal")
    _rename_by_prefix(df, "MACDh_12_26_9", "macd_hist")
    _rename_by_prefix(df, "BBL_", "bb_lower")
    _rename_by_prefix(df, "BBM_", "bb_mid")
    _rename_by_prefix(df, "BBU_", "bb_upper")
    _rename_by_prefix(df, "ATRr_", "atr")

    if not all(c in df.columns for c in FEATURE_COLS):
        missing = [c for c in FEATURE_COLS if c not in df.columns]
        raise ValueError(f"Missing expected features after computation: {missing}")

    return df


FEATURE_COLS = [
    "close",
    "volume",
    "rsi",
    "macd",
    "macd_signal",
    "macd_hist",
    "bb_upper",
    "bb_mid",
    "bb_lower",
    "atr",
    "log_return",
    "ema_fast",
    "ema_slow",
]


# ---------------------------
# Ventanas y target
# ---------------------------
def build_windows(
    df: pd.DataFrame,
    window: int = ROLLING_WINDOW,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Crea ventanas de `window` velas y target 3-clases según retorno futuro.
    Target: 0 = Vender, 1 = Mantener, 2 = Comprar.
    """
    data = df[FEATURE_COLS].values
    targets = df["ret_fwd"].values

    X, y = [], []
    for i in range(window, len(data)):
        x = data[i - window : i]
        ret = targets[i - 1]
        if ret > THRESHOLD_BUY:
            label = 2
        elif ret < THRESHOLD_SELL:
            label = 0
        else:
            label = 1
        X.append(x.flatten())
        y.append(label)
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.int64)


# ---------------------------
# Entrenamiento
# ---------------------------
def train_model(
    X: np.ndarray,
    y: np.ndarray,
) -> Tuple[RandomForestClassifier, StandardScaler]:
    """Entrena RandomForest con split temporal y retorna modelo + scaler."""
    split = int(len(X) * (1 - TEST_SIZE))
    X_train, X_val = X[:split], X[split:]
    y_train, y_val = y[:split], y[split:]

    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_val_s = scaler.transform(X_val)

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=12,
        min_samples_split=10,
        min_samples_leaf=5,
        random_state=RANDOM_STATE,
        n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(X_train_s, y_train)

    print("=== Validation report ===")
    print(classification_report(y_val, model.predict(X_val_s)))
    return model, scaler


# ---------------------------
# Exportación ONNX
# ---------------------------
def export_onnx(
    model: RandomForestClassifier,
    num_features: int,
    output_path: str | Path,
) -> Path:
    """Exporta el modelo a ONNX con input `float_input` shape `[None, num_features]`."""
    initial_type = [("float_input", FloatTensorType([None, num_features]))]
    onnx_model = convert_sklearn(
        model,
        initial_types=initial_type,
        options={id(model): {"zipmap": False}},
    )
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(onnx_model.SerializeToString())
    print(f"ONNX model exported to: {out}")
    return out


def save_scaler_params(
    scaler: StandardScaler,
    output_path: str | Path,
) -> None:
    params = {
        "mean": scaler.mean_.tolist(),
        "scale": scaler.scale_.tolist(),
        "var": scaler.var_.tolist(),
        "n_features_in": int(scaler.n_features_in_),
    }
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(params, indent=2))
    print(f"Scaler params saved to: {out}")


def save_feature_names(
    feature_names: list[str],
    output_path: str | Path,
) -> None:
    out = Path(output_path)
    out.write_text(json.dumps(feature_names, indent=2))
    print(f"Feature names saved to: {out}")


# ---------------------------
# Verificación ONNX Runtime
# ---------------------------
def verify_onnx(
    onnx_path: str | Path,
    model: RandomForestClassifier,
    scaler: StandardScaler,
    X_val: np.ndarray,
    atol: float = 1e-4,
) -> bool:
    """Compara probabilidades del modelo nativo vs ONNX Runtime."""
    if not HAS_ORT:
        print("onnxruntime not available, skipping runtime verification.")
        return False

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    input_name = sess.get_inputs()[0].name

    X_val_s = scaler.transform(X_val).astype(np.float32)
    onnx_probs = sess.run(None, {input_name: X_val_s})[1]

    sk_probs = model.predict_proba(scaler.transform(X_val))

    max_diff = float(np.max(np.abs(sk_probs - onnx_probs)))
    print(f"Max probability diff (sklearn vs ONNX): {max_diff:.6f}")
    ok = max_diff <= atol
    print(f"Verification: {'PASS' if ok else 'FAIL'}")
    return ok


# ---------------------------
# Pipeline principal
# ---------------------------
def run_pipeline(
    external_df: Optional[pd.DataFrame] = None,
    output_dir: str | Path = None,
) -> Path:
    if output_dir is None:
        output_dir = Path(__file__).resolve().parents[2] / "backend" / "models"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df = load_data(external_df)
    df = add_features(df)

    if len(df) < ROLLING_WINDOW + FORECAST_HORIZON + 10:
        raise ValueError("Not enough data after feature engineering.")

    X, y = build_windows(df, window=ROLLING_WINDOW)
    num_features = X.shape[1]
    print(f"Dataset shape: X={X.shape}, y={y.shape}, classes={np.unique(y)}")

    model, scaler = train_model(X, y)

    onnx_path = output_dir / "trading_model.onnx"
    scaler_path = output_dir / "scaler_params.json"
    feature_names_path = output_dir / "feature_names.json"
    export_onnx(model, num_features, onnx_path)
    save_scaler_params(scaler, scaler_path)
    save_feature_names(FEATURE_COLS, feature_names_path)

    split = int(len(X) * (1 - TEST_SIZE))
    _, X_val = X[:split], X[split:]
    verify_onnx(onnx_path, model, scaler, X_val)

    return onnx_path


if __name__ == "__main__":
    try:
        run_pipeline()
    except Exception as e:
        print(f"Pipeline failed: {e}")
        sys.exit(1)
