import json
import logging
import os
import sys
from typing import Any, Awaitable, Callable, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def get_base_path() -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


class AIPredictor:
    def __init__(self, model_path: Optional[str] = None) -> None:
        self.model_path = model_path or os.path.join(
            get_base_path(), "models", "trading_model.onnx"
        )
        self.feature_names_path = os.path.join(
            os.path.dirname(self.model_path), "feature_names.json"
        )
        self.scaler_params_path = os.path.join(
            os.path.dirname(self.model_path), "scaler_params.json"
        )
        self.session: Optional[Any] = None
        self.input_name: Optional[str] = None
        self.output_name: Optional[str] = None
        self.feature_names: list[str] = []
        self.scaler_mean: Optional[np.ndarray] = None
        self.scaler_scale: Optional[np.ndarray] = None
        self.window_size = 30
        self._load_model()

    def _load_model(self) -> None:
        if not os.path.exists(self.model_path):
            logger.warning("ONNX model not found at %s. Using heuristic fallback.", self.model_path)
            return
        try:
            self._load_artifacts()
            import onnxruntime as ort

            self.session = ort.InferenceSession(
                self.model_path, providers=["CPUExecutionProvider"]
            )
            outputs = self.session.get_outputs()
            self.input_name = self.session.get_inputs()[0].name
            self.output_label_name = outputs[0].name if outputs else None
            self.output_proba_name = next((o.name for o in outputs if o.name != self.output_label_name), self.output_label_name)
            logger.info("ONNX model loaded successfully from %s", self.model_path)
            logger.info("Input: %s | outputs: %s / %s", self.input_name, self.output_label_name, self.output_proba_name)
        except Exception as exc:
            logger.error("Failed to load ONNX model: %s. Falling back to heuristic.", exc)
            self.session = None

    def _load_artifacts(self):
        if os.path.exists(self.feature_names_path):
            try:
                with open(self.feature_names_path, "r", encoding="utf-8") as f:
                    self.feature_names = json.load(f)
                logger.info("Loaded %d feature names", len(self.feature_names))
            except Exception as exc:
                logger.warning("Could not load feature_names.json: %s", exc)

        if os.path.exists(self.scaler_params_path):
            try:
                with open(self.scaler_params_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
                self.scaler_mean = np.array(params["mean"], dtype=np.float32)
                self.scaler_scale = np.array(params["scale"], dtype=np.float32)
                logger.info("Loaded scaler params (mean/scale).")
            except Exception as exc:
                logger.warning("Could not load scaler_params.json: %s", exc)

    def predict(self, candles_data: List[Dict[str, Any]]) -> float:
        if self.session and len(candles_data) >= self.window_size:
            try:
                features = self._extract_features(candles_data[-self.window_size :])
                input_tensor = np.array(features, dtype=np.float32).reshape(1, -1)
                input_tensor = self._apply_scaler(input_tensor)
                outputs = self.session.run(
                    [self.output_proba_name], {self.input_name: input_tensor}
                )
                raw = np.asarray(outputs[0], dtype=np.float32)
                if raw.ndim == 2 and raw.shape[1] == 3:
                    score = float(raw[0][2])
                else:
                    score = float(raw.flat[0])
                return max(0.0, min(1.0, score))
            except Exception as exc:
                logger.error("ONNX inference failed: %s. Using heuristic.", exc)
                return self._heuristic_predict(candles_data)
        return self._heuristic_predict(candles_data)

    def predict_proba(self, candles_data: List[Dict[str, Any]]) -> Optional[np.ndarray]:
        if not (self.session and len(candles_data) >= self.window_size):
            return None
        try:
            features = self._extract_features(candles_data[-self.window_size :])
            input_tensor = np.array(features, dtype=np.float32).reshape(1, -1)
            input_tensor = self._apply_scaler(input_tensor)
            outputs = self.session.run(
                [self.output_proba_name], {self.input_name: input_tensor}
            )
            raw = np.asarray(outputs[0], dtype=np.float32)
            if raw.ndim == 2 and raw.shape[1] == 3:
                return raw[0]
            return np.asarray([raw.flat[0]], dtype=np.float32)
        except Exception as exc:
            logger.error("ONNX proba inference failed: %s", exc)
            return None

    def _extract_features(self, window: List[Dict[str, Any]]) -> List[List[float]]:
        if self.feature_names:
            features = []
            for c in window:
                row = []
                for name in self.feature_names:
                    val = c.get(name, 0.0)
                    try:
                        row.append(float(val))
                    except (TypeError, ValueError):
                        row.append(0.0)
                features.append(row)
            return features

        features = []
        for c in window:
            features.append(
                [
                    float(c.get("close", 0.0)),
                    float(c.get("volume", 0.0)),
                    float(c.get("rsi", 50.0)),
                    float(c.get("macd", 0.0)),
                    float(c.get("macd_signal", 0.0)),
                    float(c.get("macd_hist", 0.0)),
                    float(c.get("ema_fast", 0.0)),
                    float(c.get("ema_slow", 0.0)),
                ]
            )
        return features

    def _apply_scaler(self, X: np.ndarray) -> np.ndarray:
        if self.scaler_mean is None or self.scaler_scale is None:
            return X
        return (X - self.scaler_mean) / np.where(self.scaler_scale == 0, 1.0, self.scaler_scale)

    def _heuristic_predict(self, candles_data: List[Dict[str, Any]]) -> float:
        if not candles_data:
            return 0.5
        last = candles_data[-1]
        close = float(last.get("close", 0.0))
        rsi = float(last.get("rsi", 50.0))
        ema_fast = float(last.get("ema_fast", 0.0))
        ema_slow = float(last.get("ema_slow", 0.0))

        if len(candles_data) >= 2:
            prev_close = float(candles_data[-2].get("close", close))
            price_momentum = max(
                -1.0, min(1.0, (close - prev_close) / max(abs(prev_close), 1e-9) * 100)
            )
        else:
            price_momentum = 0.0

        ema_bias = 0.0
        if ema_fast > 0 and ema_slow > 0:
            ema_bias = max(
                -1.0, min(1.0, (ema_fast - ema_slow) / max(abs(ema_slow), 1e-9) * 10)
            )

        rsi_norm = (rsi - 50.0) / 50.0  # -1 to 1

        score = 0.5 + 0.3 * price_momentum + 0.4 * ema_bias + 0.2 * rsi_norm
        return max(0.0, min(1.0, score))

    def is_model_loaded(self) -> bool:
        return self.session is not None

    def shutdown(self) -> None:
        if self.session:
            try:
                del self.session
            except Exception:
                pass
            self.session = None
