from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import numpy as np
import onnx
import onnx.helper as helper
import onnxruntime as ort
import pytest

from infrastructure.ai.feature_engineering import (
    StreamingFeatureEngine,
    compute_features_sync,
    compute_tensor_sync,
    get_feature_count,
    get_feature_names,
    get_window_size,
    normalize_matrix,
)
from infrastructure.ai.model_registry import ModelRecord, ModelRegistry
from infrastructure.ai.onnx_runtime import (
    ONNXInferenceEngine,
    PredictionResult,
    LABELS,
)
from infrastructure.ai.training_helpers import (
    compute_scaler_params,
    load_feature_names,
    load_model_metadata,
    load_scaler_from_disk,
    persist_scaler_to_disk,
    save_feature_names,
    save_model_metadata,
    serialize_scaler_params,
    scaler_params_from_json,
    validate_scaler_params,
)
from infrastructure.ai.pipeline import PredictionPipeline, predict_pipeline_sync


MODEL_DIR = Path(__file__).resolve().parents[1] / "models"
TEST_MODEL_PATH = MODEL_DIR / "test_model.onnx"
TEST_SCALER_PATH = MODEL_DIR / "scaler_params.json"
TEST_FEATURES_PATH = MODEL_DIR / "feature_names.json"


def _clean_test_artifacts():
    for p in [TEST_MODEL_PATH, TEST_SCALER_PATH, TEST_FEATURES_PATH]:
        if p.exists():
            p.unlink()


@pytest.fixture(autouse=True)
def clean_artifacts():
    _clean_test_artifacts()
    yield
    _clean_test_artifacts()


def _create_dummy_onnx_model(
    input_shape: tuple[int, int] = (1, 510),
    num_classes: int = 3,
    output_path: Path = TEST_MODEL_PATH,
) -> Path:
    X = helper.make_tensor_value_info("float_input", onnx.TensorProto.FLOAT, input_shape)
    proba = helper.make_tensor_value_info("probabilities", onnx.TensorProto.FLOAT, [1, num_classes])
    label = helper.make_tensor_value_info("label", onnx.TensorProto.INT64, [1])

    W_shape = [input_shape[1], num_classes]
    W_vals = np.random.randn(*W_shape).astype(np.float32) * 0.1
    W_tensor = helper.make_tensor(
        name="weight",
        data_type=onnx.TensorProto.FLOAT,
        dims=W_shape,
        vals=W_vals.flatten().tolist(),
    )
    b_shape = [num_classes]
    b_vals = np.zeros(b_shape, dtype=np.float32)
    b_tensor = helper.make_tensor(
        name="bias",
        data_type=onnx.TensorProto.FLOAT,
        dims=b_shape,
        vals=b_vals.tolist(),
    )

    matmul_node = helper.make_node(
        "MatMul",
        inputs=["float_input", "weight"],
        outputs=["matmul_out"],
    )
    add_node = helper.make_node(
        "Add",
        inputs=["matmul_out", "bias"],
        outputs=["add_out"],
    )
    softmax_node = helper.make_node(
        "Softmax",
        inputs=["add_out"],
        outputs=["probabilities"],
        axis=1,
    )
    argmax_node = helper.make_node(
        "ArgMax",
        inputs=["probabilities"],
        outputs=["label"],
        axis=1,
    )

    graph_def = helper.make_graph(
        [matmul_node, add_node, softmax_node, argmax_node],
        "test_graph",
        [X],
        [proba, label],
        [W_tensor, b_tensor],
    )
    model_def = helper.make_model(graph_def, opset_imports=[helper.make_opsetid("", 13)])
    onnx.checker.check_model(model_def)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(model_def.SerializeToString())
    return output_path


def _create_onnx_with_scaler(
    output_path: Path = TEST_MODEL_PATH,
) -> Path:
    model_path = _create_dummy_onnx_model(output_path=output_path)

    feature_names = get_feature_names()
    save_feature_names(feature_names, output_path=MODEL_DIR / "feature_names.json")

    return model_path


def _make_candles(n: int = 30) -> list[dict]:
    candles = []
    price = 100.0
    for i in range(n):
        price += np.random.randn() * 2.0
        candles.append(
            {
                "open": price + np.random.randn() * 0.5,
                "high": price + abs(np.random.randn()) * 1.0,
                "low": price - abs(np.random.randn()) * 1.0,
                "close": price,
                "volume": float(np.random.uniform(10, 100)),
            }
        )
    return candles


class TestFeatureEngineering:
    def test_feature_count(self):
        assert get_feature_count() == 17

    def test_feature_names_count(self):
        names = get_feature_names()
        assert len(names) == 17
        assert "close" in names
        assert "rsi" in names
        assert "macd" in names

    def test_window_size(self):
        assert get_window_size() == 30

    def test_compute_features_returns_correct_shape(self):
        candles = _make_candles(30)
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_features()
        assert matrix.shape == (30, 17)
        assert matrix.dtype == np.float32

    def test_compute_features_with_known_data(self):
        candles = []
        for i in range(30):
            candles.append(
                {
                    "open": 100.0 + i * 0.1,
                    "high": 101.0 + i * 0.1,
                    "low": 99.0 + i * 0.1,
                    "close": 100.0 + i * 0.1,
                    "volume": 50.0,
                }
            )
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_features()
        assert matrix.shape == (30, 17)
        assert np.all(np.isfinite(matrix))

    def test_compute_features_insufficient_data_raises(self):
        engine = StreamingFeatureEngine(window_size=30)
        candles = _make_candles(10)
        engine.push_batch(candles)
        with pytest.raises(ValueError, match="Insufficient data"):
            engine.compute_features()

    def test_compute_tensor_shape(self):
        candles = _make_candles(30)
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_tensor()
        assert matrix.shape == (30, 17)
        assert matrix.dtype == np.float32

    def test_normalize_matrix(self):
        matrix = np.random.randn(30, 17).astype(np.float32)
        mean = np.mean(matrix, axis=0).astype(np.float32)
        scale = np.std(matrix, axis=0).astype(np.float32)
        scale = np.where(scale < 1e-9, 1.0, scale)
        normalized = normalize_matrix(matrix, mean, scale)
        assert normalized.shape == matrix.shape
        assert np.allclose(np.mean(normalized, axis=0), 0.0, atol=1e-6)

    def test_compute_and_normalize(self):
        candles = _make_candles(30)
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        mean = np.random.randn(17).astype(np.float32) * 0.5
        scale = np.abs(np.random.randn(17).astype(np.float32)) + 0.1
        engine.set_scaler_params(mean, scale)
        matrix = engine.compute_and_normalize(candles)
        assert matrix.shape == (30, 17)

    def test_push_and_buffer_size(self):
        engine = StreamingFeatureEngine(window_size=30)
        for i in range(50):
            engine.push(
                {
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 50.0,
                }
            )
        assert engine.size == 50
        assert engine.is_ready is True

    def test_clear_buffer(self):
        engine = StreamingFeatureEngine(window_size=30)
        candles = _make_candles(30)
        engine.push_batch(candles)
        engine.clear()
        assert engine.size == 0
        assert engine.is_ready is False

    def test_compute_features_sync(self):
        candles = _make_candles(30)
        matrix = compute_features_sync(candles)
        assert matrix.shape == (30, 17)

    def test_compute_tensor_sync(self):
        candles = _make_candles(30)
        mean = np.random.randn(17).astype(np.float32) * 0.5
        scale = np.abs(np.random.randn(17).astype(np.float32)) + 0.1
        matrix = compute_tensor_sync(candles, scaler_mean=mean, scaler_scale=scale)
        assert matrix.shape == (30, 17)
        assert matrix.dtype == np.float32

    def test_rsi_computation(self):
        candles = []
        for i in range(30):
            candles.append(
                {
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0 + i * 0.5,
                    "volume": 50.0,
                }
            )
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_features()
        rsi_col = matrix[:, 5]
        assert np.all(np.isfinite(rsi_col))
        assert np.all(rsi_col >= 0.0) and np.all(rsi_col <= 100.0)

    def test_macd_computation(self):
        candles = _make_candles(30)
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_features()
        macd_col = matrix[:, 6]
        macd_signal_col = matrix[:, 7]
        macd_hist_col = matrix[:, 8]
        assert np.all(np.isfinite(macd_col))
        assert np.all(np.isfinite(macd_signal_col))
        assert np.all(np.isfinite(macd_hist_col))

    def test_bollinger_bands_computation(self):
        candles = _make_candles(30)
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_features()
        bb_upper = matrix[:, 9]
        bb_mid = matrix[:, 10]
        bb_lower = matrix[:, 11]
        assert np.all(bb_upper >= bb_mid)
        assert np.all(bb_mid >= bb_lower)

    def test_atr_computation(self):
        candles = _make_candles(30)
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_features()
        atr_col = matrix[:, 12]
        assert np.all(atr_col >= 0.0)

    def test_ema_computation(self):
        candles = _make_candles(30)
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_features()
        ema_fast = matrix[:, 13]
        ema_slow = matrix[:, 14]
        assert np.all(np.isfinite(ema_fast))
        assert np.all(np.isfinite(ema_slow))

    def test_log_return_computation(self):
        candles = _make_candles(30)
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_features()
        log_return_col = matrix[:, 15]
        assert np.all(np.isfinite(log_return_col))

    def test_realized_volatility_computation(self):
        candles = _make_candles(30)
        engine = StreamingFeatureEngine(window_size=30)
        engine.push_batch(candles)
        matrix = engine.compute_features()
        vol_col = matrix[:, 16]
        assert np.all(vol_col >= 0.0)
        assert np.all(np.isfinite(vol_col))


class TestONNXInference:
    def test_dummy_model_prediction(self):
        _create_onnx_with_scaler()
        engine = ONNXInferenceEngine(model_path=TEST_MODEL_PATH)
        assert engine.is_loaded()
        candles = _make_candles(30)
        engine2 = StreamingFeatureEngine(window_size=30)
        engine2.push_batch(candles)
        tensor = engine2.compute_tensor()
        tensor_3d = tensor.reshape(1, 30, 17).astype(np.float32)
        result = engine.predict(tensor_3d, candles=candles)
        assert result.label in LABELS
        assert 0.0 <= result.confidence <= 1.0
        assert "BUY" in result.probabilities
        assert "SELL" in result.probabilities
        assert "HOLD" in result.probabilities
        assert result.model_loaded is True
        assert result.fallback_used is False
        engine.shutdown()

    def test_prediction_with_invalid_tensor_uses_fallback(self):
        _create_onnx_with_scaler()
        engine = ONNXInferenceEngine(model_path=TEST_MODEL_PATH)
        bad_tensor = np.zeros((1, 5, 17), dtype=np.float32)
        candles = _make_candles(30)
        result = engine.predict(bad_tensor, candles=candles)
        assert result.label in LABELS
        assert result.fallback_used is True
        engine.shutdown()

    def test_prediction_without_model_uses_fallback(self):
        engine = ONNXInferenceEngine(model_path=Path("/nonexistent/model.onnx"))
        assert not engine.is_loaded()
        candles = _make_candles(30)
        result = engine.predict(
            np.zeros((1, 30, 17), dtype=np.float32),
            candles=candles,
        )
        assert result.label in LABELS
        assert result.fallback_used is True
        assert result.model_loaded is False
        engine.shutdown()

    def test_prediction_empty_candles_uses_fallback(self):
        engine = ONNXInferenceEngine(model_path=Path("/nonexistent/model.onnx"))
        result = engine.predict(
            np.zeros((1, 30, 17), dtype=np.float32),
            candles=[],
        )
        assert result.label == "HOLD"
        assert result.confidence == 0.5
        assert result.fallback_used is True
        engine.shutdown()

    def test_tensor_validation_rejects_wrong_shape(self):
        _create_onnx_with_scaler()
        engine = ONNXInferenceEngine(model_path=TEST_MODEL_PATH)
        bad_tensor = np.zeros((1, 10, 17), dtype=np.float32)
        candles = _make_candles(30)
        result = engine.predict(bad_tensor, candles=candles)
        assert result.fallback_used is True
        engine.shutdown()

    def test_tensor_validation_rejects_nan(self):
        _create_onnx_with_scaler()
        engine = ONNXInferenceEngine(model_path=TEST_MODEL_PATH)
        bad_tensor = np.full((1, 30, 17), np.nan, dtype=np.float32)
        candles = _make_candles(30)
        result = engine.predict(bad_tensor, candles=candles)
        assert result.fallback_used is True
        engine.shutdown()

    def test_reload_model(self):
        _create_onnx_with_scaler()
        engine = ONNXInferenceEngine(model_path=TEST_MODEL_PATH)
        assert engine.is_loaded()
        engine.shutdown()
        assert not engine.is_loaded()
        engine.reload()
        assert engine.is_loaded()
        engine.shutdown()

    def test_run_inference_standalone(self):
        _create_onnx_with_scaler()
        candles = _make_candles(30)
        engine2 = StreamingFeatureEngine(window_size=30)
        engine2.push_batch(candles)
        tensor = engine2.compute_tensor()
        tensor_3d = tensor.reshape(1, 30, 17).astype(np.float32)
        result = ONNXInferenceEngine(model_path=TEST_MODEL_PATH).predict(
            tensor_3d, candles=candles
        )
        assert result.label in LABELS
        assert 0.0 <= result.confidence <= 1.0


class TestFallbackHeuristic:
    def test_fallback_bullish_bias(self):
        candles = []
        price = 100.0
        for _ in range(30):
            price += 1.0
            candles.append(
                {
                    "close": price,
                    "volume": 10.0,
                    "rsi": 55.0,
                    "macd": 0.1,
                    "macd_signal": 0.0,
                    "macd_hist": 0.1,
                    "ema_fast": price + 1.0,
                    "ema_slow": price - 1.0,
                    "bb_upper": price + 2.0,
                    "bb_mid": price,
                    "bb_lower": price - 2.0,
                    "atr": 1.0,
                    "log_return": 0.01,
                    "realized_volatility": 0.02,
                }
            )
        engine = ONNXInferenceEngine(model_path=Path("/nonexistent/model.onnx"))
        result = engine.predict(
            np.zeros((1, 30, 17), dtype=np.float32),
            candles=candles,
        )
        assert result.label in LABELS
        assert result.fallback_used is True
        assert result.model_loaded is False
        engine.shutdown()

    def test_fallback_bearish_bias(self):
        candles = []
        price = 200.0
        for _ in range(30):
            price -= 1.0
            candles.append(
                {
                    "close": price,
                    "volume": 10.0,
                    "rsi": 45.0,
                    "macd": -0.1,
                    "macd_signal": 0.0,
                    "macd_hist": -0.1,
                    "ema_fast": price - 1.0,
                    "ema_slow": price + 1.0,
                    "bb_upper": price + 2.0,
                    "bb_mid": price,
                    "bb_lower": price - 2.0,
                    "atr": 1.0,
                    "log_return": -0.01,
                    "realized_volatility": 0.02,
                }
            )
        engine = ONNXInferenceEngine(model_path=Path("/nonexistent/model.onnx"))
        result = engine.predict(
            np.zeros((1, 30, 17), dtype=np.float32),
            candles=candles,
        )
        assert result.label in LABELS
        assert result.fallback_used is True
        engine.shutdown()

    def test_fallback_probabilities_sum_to_one(self):
        candles = _make_candles(30)
        engine = ONNXInferenceEngine(model_path=Path("/nonexistent/model.onnx"))
        result = engine.predict(
            np.zeros((1, 30, 17), dtype=np.float32),
            candles=candles,
        )
        total = sum(result.probabilities.values())
        assert abs(total - 1.0) < 1e-6
        engine.shutdown()

    def test_fallback_confidence_in_range(self):
        candles = _make_candles(30)
        engine = ONNXInferenceEngine(model_path=Path("/nonexistent/model.onnx"))
        result = engine.predict(
            np.zeros((1, 30, 17), dtype=np.float32),
            candles=candles,
        )
        assert 0.0 <= result.confidence <= 1.0
        engine.shutdown()

    def test_fallback_with_empty_candles(self):
        engine = ONNXInferenceEngine(model_path=Path("/nonexistent/model.onnx"))
        result = engine.predict(
            np.zeros((1, 30, 17), dtype=np.float32),
            candles=[],
        )
        assert result.label == "HOLD"
        assert result.confidence == 0.5
        assert result.fallback_used is True
        engine.shutdown()


class TestModelRegistry:
    def test_register_and_get(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry.json")
        record = registry.register(
            name="test_model",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        assert record.name == "test_model"
        assert record.version == "1.0.0"
        assert record.provider == "CPUExecutionProvider"
        retrieved = registry.get("test_model")
        assert retrieved is not None
        assert retrieved.name == "test_model"

    def test_unregister(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry2.json")
        registry.register(
            name="to_delete",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        assert registry.get("to_delete") is not None
        result = registry.unregister("to_delete")
        assert result is True
        assert registry.get("to_delete") is None

    def test_unregister_missing_returns_false(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry3.json")
        result = registry.unregister("nonexistent")
        assert result is False

    def test_get_all(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry4.json")
        registry.register(
            name="model_a",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        registry.register(
            name="model_b",
            version="2.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="XGBoost",
            path=str(TEST_MODEL_PATH),
        )
        all_models = registry.get_all()
        assert len(all_models) == 2
        assert "model_a" in all_models
        assert "model_b" in all_models

    def test_update_model_record(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry5.json")
        registry.register(
            name="update_me",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        updated = registry.update("update_me", version="2.0.0")
        assert updated is not None
        assert updated.version == "2.0.0"
        retrieved = registry.get("update_me")
        assert retrieved.version == "2.0.0"

    def test_update_missing_model_returns_none(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry6.json")
        result = registry.update("nonexistent", version="2.0.0")
        assert result is None

    def test_get_active_model(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry7.json")
        registry.register(
            name="old_model",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        import time
        time.sleep(0.01)
        registry.register(
            name="new_model",
            version="2.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="XGBoost",
            path=str(TEST_MODEL_PATH),
        )
        active = registry.get_active_model()
        assert active is not None
        assert active.name == "new_model"

    def test_has_model(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry8.json")
        registry.register(
            name="existing",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        assert registry.has_model("existing") is False

    def test_list_names(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry9.json")
        registry.register(
            name="model_x",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        names = registry.list_names()
        assert "model_x" in names

    def test_clear(self):
        registry = ModelRegistry(registry_path=MODEL_DIR / "test_registry10.json")
        registry.register(
            name="clear_me",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        assert len(registry.get_all()) == 1
        registry.clear()
        assert len(registry.get_all()) == 0

    def test_model_record_to_dict_and_from_dict(self):
        record = ModelRecord(
            name="roundtrip",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="LSTM",
            path="/some/path.onnx",
            last_updated="2026-01-01T00:00:00+00:00",
        )
        data = record.to_dict()
        restored = ModelRecord.from_dict(data)
        assert restored.name == record.name
        assert restored.version == record.version
        assert restored.features == record.features
        assert restored.window_size == record.window_size
        assert restored.provider == record.provider
        assert restored.model_type == record.model_type
        assert restored.path == record.path


class TestTrainingHelpers:
    def test_compute_scaler_params(self):
        X = np.random.randn(100, 17).astype(np.float32)
        params = compute_scaler_params(X)
        assert "mean" in params
        assert "scale" in params
        assert "var" in params
        assert params["n_features_in"] == 17
        assert params["mean"].shape == (17,)
        assert params["scale"].shape == (17,)

    def test_validate_scaler_params_valid(self):
        mean = np.random.randn(17).astype(np.float32)
        scale = np.abs(np.random.randn(17).astype(np.float32)) + 0.1
        assert validate_scaler_params(mean, scale, 17) is True

    def test_validate_scaler_params_wrong_size(self):
        mean = np.random.randn(10).astype(np.float32)
        scale = np.abs(np.random.randn(10).astype(np.float32)) + 0.1
        assert validate_scaler_params(mean, scale, 17) is False

    def test_validate_scaler_params_zero_scale(self):
        mean = np.random.randn(17).astype(np.float32)
        scale = np.zeros(17, dtype=np.float32)
        assert validate_scaler_params(mean, scale, 17) is False

    def test_serialize_descaler_params_json(self):
        mean = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        scale = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        path = serialize_scaler_params(mean, scale)
        with open(path, "r", encoding="utf-8") as f:
            parsed = json.load(f)
        assert "mean" in parsed
        assert "scale" in parsed
        assert parsed["mean"] == [1.0, 2.0, 3.0]

    def test_scaler_params_from_json(self):
        mean = np.array([1.0, 2.0, 3.0], dtype=np.float32)
        scale = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        path = serialize_scaler_params(mean, scale)
        with open(path, "r", encoding="utf-8") as f:
            json_str = f.read()
        result = scaler_params_from_json(json_str)
        assert np.allclose(result["mean"], mean)
        assert np.allclose(result["scale"], scale)

    def test_persist_and_load_scaler(self):
        mean = np.random.randn(17).astype(np.float32)
        scale = np.abs(np.random.randn(17).astype(np.float32)) + 0.1
        path = persist_scaler_to_disk(mean, scale)
        assert path.exists()
        loaded = load_scaler_from_disk()
        assert "mean" in loaded
        assert "scale" in loaded
        assert np.allclose(loaded["mean"], mean)
        assert np.allclose(loaded["scale"], scale)

    def test_save_and_load_feature_names(self):
        features = get_feature_names()
        path = save_feature_names(features, output_path=MODEL_DIR / "test_features.json")
        assert path.exists()
        loaded = load_feature_names(path)
        assert loaded == features

    def test_save_and_load_model_metadata(self):
        metadata = {
            "name": "test",
            "version": "1.0.0",
            "author": "test",
        }
        path = save_model_metadata(metadata, output_path=MODEL_DIR / "test_metadata.json")
        assert path.exists()
        loaded = load_model_metadata(path)
        assert loaded["name"] == "test"
        assert loaded["version"] == "1.0.0"

    def test_apply_and_inverse_scaler(self):
        X = np.random.randn(10, 17).astype(np.float32)
        mean = np.mean(X, axis=0).astype(np.float32)
        scale = np.std(X, axis=0).astype(np.float32)
        scale = np.where(scale < 1e-9, 1.0, scale)
        X_norm = normalize_matrix(X, mean, scale)
        X_inv = (X_norm * scale + mean).astype(np.float32)
        assert np.allclose(X, X_inv, atol=1e-5)


class TestPredictionPipeline:
    def test_pipeline_predict_with_dummy_model(self):
        _create_onnx_with_scaler()
        pipeline = PredictionPipeline(
            model_path=TEST_MODEL_PATH,
        )
        candles = _make_candles(30)
        result = pipeline.predict(candles)
        assert result.label in LABELS
        assert 0.0 <= result.confidence <= 1.0
        pipeline.shutdown()

    def test_pipeline_predict_async_with_dummy_model(self):
        import asyncio

        _create_onnx_with_scaler()
        pipeline = PredictionPipeline(
            model_path=TEST_MODEL_PATH,
        )
        candles = _make_candles(30)

        async def run():
            return await pipeline.predict_async(candles)

        result = asyncio.run(run())
        assert result.label in LABELS
        pipeline.shutdown()

    def test_pipeline_predict_with_fallback(self):
        pipeline = PredictionPipeline(
            model_path=Path("/nonexistent/model.onnx"),
        )
        candles = _make_candles(30)
        result = pipeline.predict(candles)
        assert result.fallback_used is True
        assert result.model_loaded is False
        pipeline.shutdown()

    def test_pipeline_predict_with_details(self):
        _create_onnx_with_scaler()
        pipeline = PredictionPipeline(
            model_path=TEST_MODEL_PATH,
        )
        candles = _make_candles(30)
        details = pipeline.predict_with_features(candles)
        assert "prediction" in details
        assert "features_shape" in details
        assert "features" in details
        assert details["prediction"].label in LABELS
        pipeline.shutdown()

    def test_pipeline_update_model(self):
        _create_onnx_with_scaler()
        pipeline = PredictionPipeline(
            model_path=Path("/nonexistent/model.onnx"),
        )
        assert not pipeline.is_model_loaded()
        pipeline.update_model(TEST_MODEL_PATH)
        assert pipeline.is_model_loaded()
        pipeline.shutdown()

    def test_pipeline_is_model_loaded(self):
        _create_onnx_with_scaler()
        pipeline = PredictionPipeline(
            model_path=TEST_MODEL_PATH,
        )
        assert pipeline.is_model_loaded()
        pipeline.shutdown()

    def test_predict_pipeline_sync_function(self):
        _create_onnx_with_scaler()
        candles = _make_candles(30)
        result = predict_pipeline_sync(candles, model_path=TEST_MODEL_PATH)
        assert result.label in LABELS

    def test_predict_pipeline_sync_function_fallback(self):
        candles = _make_candles(30)
        result = predict_pipeline_sync(candles, model_path=Path("/nonexistent/model.onnx"))
        assert result.fallback_used is True


class TestModelRecord:
    def test_model_record_defaults(self):
        record = ModelRecord(name="test", version="1.0.0", features=[], window_size=30)
        assert record.provider == "CPUExecutionProvider"
        assert record.model_type == "RandomForest"
        assert record.last_updated != ""

    def test_model_record_to_dict_roundtrip(self):
        record = ModelRecord(
            name="test",
            version="2.0.0",
            features=["close", "rsi"],
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="XGBoost",
            path="/path/to/model.onnx",
            last_updated="2026-01-01T00:00:00+00:00",
        )
        d = record.to_dict()
        restored = ModelRecord.from_dict(d)
        assert restored.name == "test"
        assert restored.version == "2.0.0"
        assert restored.features == ["close", "rsi"]
        assert restored.window_size == 30
        assert restored.provider == "CPUExecutionProvider"
        assert restored.model_type == "XGBoost"
        assert restored.path == "/path/to/model.onnx"


class TestIntegration:
    def test_full_pipeline_with_dummy_model(self):
        _create_onnx_with_scaler()
        reg = ModelRegistry()
        reg.register(
            name="integration_model",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        pipeline = PredictionPipeline(
            model_registry=reg,
            model_path=TEST_MODEL_PATH,
        )
        candles = _make_candles(30)
        result = pipeline.predict(candles)
        assert result.label in LABELS
        assert 0.0 <= result.confidence <= 1.0
        info = pipeline.get_active_model_info()
        assert info is not None
        assert info["name"] == "integration_model"
        pipeline.shutdown()

    def test_prediction_pipeline_with_fallback(self):
        reg = ModelRegistry()
        pipeline = PredictionPipeline(model_registry=reg)
        candles = _make_candles(30)
        result = pipeline.predict(candles)
        assert result.fallback_used is True
        assert result.label in LABELS
        pipeline.shutdown()

    def test_prediction_pipeline_register_and_list(self):
        reg = ModelRegistry()
        pipeline = PredictionPipeline(model_registry=reg)
        reg.register(
            name="pipeline_model",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="LSTM",
            path=str(TEST_MODEL_PATH),
        )
        models = pipeline.list_models()
        assert "pipeline_model" in models

    def test_prediction_pipeline_unregister(self):
        reg = ModelRegistry()
        pipeline = PredictionPipeline(model_registry=reg)
        reg.register(
            name="pipeline_remove",
            version="1.0.0",
            features=get_feature_names(),
            window_size=30,
            provider="CPUExecutionProvider",
            model_type="RandomForest",
            path=str(TEST_MODEL_PATH),
        )
        assert reg.unregister("pipeline_remove") is True
        assert reg.get("pipeline_remove") is None

    def test_prediction_pipeline_compute_features(self):
        reg = ModelRegistry()
        pipeline = PredictionPipeline(model_registry=reg)
        candles = _make_candles(30)
        features = pipeline.compute_features(candles)
        assert features.shape == (30, 17)

    def test_prediction_pipeline_predict_with_details(self):
        _create_onnx_with_scaler()
        reg = ModelRegistry()
        pipeline = PredictionPipeline(
            model_registry=reg,
            model_path=TEST_MODEL_PATH,
        )
        candles = _make_candles(30)
        details = pipeline.predict_with_features(candles)
        assert details["prediction"].label in LABELS
        assert details["model_loaded"] is True
        assert details["fallback_used"] is False
        pipeline.shutdown()