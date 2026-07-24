import os
from pathlib import Path

import pytest

from ai_engine import AIPredictor


MODEL_DIR = Path(__file__).resolve().parents[1] / "models"


def _clean_artifacts():
    for name in ["trading_model.onnx", "scaler_params.json", "feature_names.json"]:
        p = MODEL_DIR / name
        if p.exists():
            p.unlink()


@pytest.fixture(autouse=True)
def clean_ai_artifacts():
    _clean_artifacts()
    yield
    _clean_artifacts()


@pytest.fixture
def predictor():
    return AIPredictor()


def test_fallback_without_model(predictor):
    assert predictor.is_model_loaded() is False
    score = predictor.predict([])
    assert 0.0 <= score <= 1.0


def test_fallback_with_candles(predictor):
    candles = [
        {"close": 100.0, "volume": 10, "rsi": 55.0, "macd": 0.1, "macd_signal": 0.0, "macd_hist": 0.1, "ema_fast": 101.0, "ema_slow": 99.0},
        {"close": 101.0, "volume": 12, "rsi": 58.0, "macd": 0.2, "macd_signal": 0.0, "macd_hist": 0.2, "ema_fast": 102.0, "ema_slow": 100.0},
    ]
    score = predictor.predict(candles)
    assert 0.0 <= score <= 1.0


def test_heuristic_bullish_bias(predictor):
    candles = []
    price = 100.0
    for _ in range(30):
        price += 1.0
        candles.append({
            "close": price,
            "volume": 10,
            "rsi": 55.0,
            "macd": 0.0,
            "macd_signal": 0.0,
            "macd_hist": 0.0,
            "ema_fast": price + 1.0,
            "ema_slow": price - 1.0,
        })
    score = predictor.predict(candles)
    assert score > 0.5


def test_heuristic_bearish_bias(predictor):
    candles = []
    price = 200.0
    for _ in range(30):
        price -= 1.0
        candles.append({
            "close": price,
            "volume": 10,
            "rsi": 45.0,
            "macd": 0.0,
            "macd_signal": 0.0,
            "macd_hist": 0.0,
            "ema_fast": price - 1.0,
            "ema_slow": price + 1.0,
        })
    score = predictor.predict(candles)
    assert score < 0.5
