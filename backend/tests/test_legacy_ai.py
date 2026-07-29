from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from ai_engine import AIPredictor


def _write_artifacts(tmpdir: str) -> str:
    model_path = os.path.join(tmpdir, "model.onnx")
    names_path = os.path.join(tmpdir, "feature_names.json")
    scaler_path = os.path.join(tmpdir, "scaler_params.json")
    Path(model_path).write_bytes(b"fake-onnx")
    with open(names_path, "w", encoding="utf-8") as f:
        json.dump(["close", "volume", "rsi", "ema_fast", "ema_slow"], f)
    with open(scaler_path, "w", encoding="utf-8") as f:
        json.dump({"mean": [0.0] * 5, "scale": [1.0] * 5}, f)
    return model_path


def test_load_model_with_mock_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = _write_artifacts(tmpdir)
        predictor = AIPredictor(model_path)
        assert predictor.is_model_loaded() is False


def test_predict_with_loaded_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = _write_artifacts(tmpdir)
        predictor = AIPredictor(model_path)
        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "input"
        mock_output = MagicMock()
        mock_output.name = "output"
        mock_session.get_inputs.return_value = [mock_input]
        mock_session.get_outputs.return_value = [mock_output]
        mock_session.run.return_value = [np.array([[0.0, 0.0, 0.9]], dtype=np.float32)]
        predictor.session = mock_session
        predictor.input_name = "input"
        predictor.output_proba_name = "output"
        candles = [
            {"close": 100.0, "volume": 10.0, "rsi": 50.0, "ema_fast": 100.0, "ema_slow": 100.0},
            {"close": 101.0, "volume": 11.0, "rsi": 51.0, "ema_fast": 101.0, "ema_slow": 100.0},
        ]
        score = predictor.predict(candles)
        assert 0.0 <= score <= 1.0


def test_predict_proba_with_mock_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = _write_artifacts(tmpdir)
        predictor = AIPredictor(model_path)
        mock_session = MagicMock()
        mock_input = MagicMock()
        mock_input.name = "input"
        mock_output = MagicMock()
        mock_output.name = "output"
        mock_session.get_inputs.return_value = [mock_input]
        mock_session.get_outputs.return_value = [mock_output]
        mock_session.run.return_value = [np.array([[0.1, 0.2, 0.7]], dtype=np.float32)]
        predictor.session = mock_session
        predictor.input_name = "input"
        predictor.output_proba_name = "output"
        predictor.feature_names = ["close", "volume", "rsi", "ema_fast", "ema_slow"]
        predictor.scaler_mean = None
        predictor.scaler_scale = None
        candles = [{"close": 100.0, "volume": 10.0, "rsi": 50.0, "ema_fast": 100.0, "ema_slow": 100.0}] * 30
        proba = predictor.predict_proba(candles)
        assert proba is not None
        assert proba.shape == (3,)


def test_predict_falls_back_on_inference_error():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = _write_artifacts(tmpdir)
        predictor = AIPredictor(model_path)
        mock_session = MagicMock()
        mock_session.run.side_effect = RuntimeError("inference crash")
        predictor.session = mock_session
        predictor.input_name = "input"
        predictor.output_proba_name = "output"
        candles = [{"close": 100.0, "volume": 10.0, "rsi": 50.0, "ema_fast": 100.0, "ema_slow": 100.0}] * 30
        score = predictor.predict(candles)
        assert 0.0 <= score <= 1.0


def test_heuristic_predict_bearish_momentum():
    with tempfile.TemporaryDirectory() as tmpdir:
        predictor = AIPredictor(os.path.join(tmpdir, "missing.onnx"))
        candles = [
            {"close": 200.0, "rsi": 70.0, "ema_fast": 105.0, "ema_slow": 100.0},
            {"close": 190.0, "rsi": 30.0, "ema_fast": 95.0, "ema_slow": 100.0},
        ]
        score = predictor._heuristic_predict(candles)
        assert score < 0.5


def test_extract_features_without_feature_names_uses_defaults():
    with tempfile.TemporaryDirectory() as tmpdir:
        predictor = AIPredictor(os.path.join(tmpdir, "missing.onnx"))
        predictor.feature_names = []
        window = [{"close": 100.0, "volume": 10.0, "rsi": 50.0, "macd": 0.0, "macd_signal": 0.0, "macd_hist": 0.0, "ema_fast": 100.0, "ema_slow": 100.0}]
        features = predictor._extract_features(window)
        assert len(features) == 1
        assert len(features[0]) == 8


def test_apply_scaler_divides_by_zero_safely():
    with tempfile.TemporaryDirectory() as tmpdir:
        predictor = AIPredictor(os.path.join(tmpdir, "missing.onnx"))
        predictor.scaler_mean = np.array([0.0], dtype=np.float32)
        predictor.scaler_scale = np.array([0.0], dtype=np.float32)
        arr = np.array([[1.0]], dtype=np.float32)
        result = predictor._apply_scaler(arr)
        assert np.isfinite(result).all()


def test_shutdown_clears_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        predictor = AIPredictor(os.path.join(tmpdir, "missing.onnx"))
        predictor.session = MagicMock()
        predictor.shutdown()
        assert predictor.session is None
