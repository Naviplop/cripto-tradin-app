from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = Path(
    os.environ.get("TRADING_APP_DATA_DIR", os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LAFM"))
) / "models" / "trading_model.onnx"

LABELS = ["SELL", "HOLD", "BUY"]


@dataclass
class PredictionResult:
    label: str
    confidence: float
    probabilities: Dict[str, float] = field(default_factory=dict)
    model_loaded: bool = False
    fallback_used: bool = False


class ONNXInferenceEngine:
    def __init__(
        self,
        model_path: Optional[Path] = None,
        provider: str = "CPUExecutionProvider",
    ) -> None:
        self._model_path = model_path or DEFAULT_MODEL_PATH
        self._provider = provider
        self._session: Optional[Any] = None
        self._input_name: Optional[str] = None
        self._output_name: Optional[str] = None
        self._output_label_name: Optional[str] = None
        self._output_proba_name: Optional[str] = None
        self._scaler_mean: Optional[np.ndarray] = None
        self._scaler_scale: Optional[np.ndarray] = None
        self._feature_names: List[str] = []
        self._window_size: int = 30
        self._num_features: int = 7
        self._loaded: bool = False
        self._load_model()

    def _load_model(self) -> None:
        if not self._model_path.exists():
            logger.warning(
                "ONNX model not found at %s. Using heuristic fallback.",
                self._model_path,
            )
            return
        try:
            self._load_artifacts()
            import onnxruntime as ort

            self._session = ort.InferenceSession(
                str(self._model_path),
                providers=[self._provider],
            )
            inputs = self._session.get_inputs()
            outputs = self._session.get_outputs()
            if inputs:
                self._input_name = inputs[0].name
            if outputs:
                self._output_label_name = outputs[0].name
                self._output_proba_name = next(
                    (o.name for o in outputs if o.name != self._output_label_name),
                    self._output_label_name,
                )
            self._loaded = True
            logger.info(
                "ONNX model loaded from %s | input=%s | outputs=%s/%s",
                self._model_path,
                self._input_name,
                self._output_label_name,
                self._output_proba_name,
            )
        except Exception as exc:
            logger.error("Failed to load ONNX model: %s", exc)
            self._session = None
            self._loaded = False

    def _load_artifacts(self) -> None:
        feature_names_path = self._model_path.parent / "feature_names.json"
        if feature_names_path.exists():
            try:
                import json
                with open(feature_names_path, "r", encoding="utf-8") as f:
                    self._feature_names = json.load(f)
                self._num_features = len(self._feature_names)
            except Exception as exc:
                logger.warning("Could not load feature_names.json: %s", exc)

        scaler_path = self._model_path.parent / "scaler_params.json"
        if scaler_path.exists():
            try:
                import json
                with open(scaler_path, "r", encoding="utf-8") as f:
                    params = json.load(f)
                self._scaler_mean = np.array(params.get("mean", []), dtype=np.float32)
                self._scaler_scale = np.array(params.get("scale", []), dtype=np.float32)
            except Exception as exc:
                logger.warning("Could not load scaler_params.json: %s", exc)

    def reload(self) -> None:
        self._session = None
        self._loaded = False
        self._load_model()

    def predict(
        self,
        tensor: np.ndarray,
        candles: Optional[List[Dict[str, Any]]] = None,
    ) -> PredictionResult:
        if self._session is not None and self._validate_tensor(tensor):
            try:
                return self._run_inference(tensor)
            except Exception as exc:
                logger.error("ONNX inference failed: %s", exc)
                if candles is not None:
                    return self._heuristic_predict(candles)
                return PredictionResult(
                    label="HOLD",
                    confidence=0.5,
                    probabilities={"BUY": 0.33, "SELL": 0.33, "HOLD": 0.34},
                    model_loaded=True,
                    fallback_used=True,
                )
        if candles is not None:
            return self._heuristic_predict(candles)
        return PredictionResult(
            label="HOLD",
            confidence=0.5,
            probabilities={"BUY": 0.33, "SELL": 0.33, "HOLD": 0.34},
            model_loaded=False,
            fallback_used=True,
        )

    def _validate_tensor(self, tensor: np.ndarray) -> bool:
        if tensor is None or not isinstance(tensor, np.ndarray):
            return False
        if tensor.ndim == 3:
            if tensor.shape[0] != 1:
                return False
            if tensor.shape[2] != self._num_features:
                return False
            if tensor.shape[1] < 1:
                return False
        elif tensor.ndim == 2:
            if tensor.shape[0] != 1:
                return False
            if tensor.shape[1] != self._num_features:
                return False
        else:
            return False
        if not np.isfinite(tensor).all():
            return False
        return True

    def _run_inference(self, tensor: np.ndarray) -> PredictionResult:
        input_tensor = tensor.astype(np.float32)
        if input_tensor.ndim == 3:
            input_tensor = input_tensor.reshape(1, -1)
        if self._scaler_mean is not None and self._scaler_scale is not None:
            input_tensor = (input_tensor - self._scaler_mean) / np.where(
                self._scaler_scale == 0, 1.0, self._scaler_scale
            )
        outputs = self._session.run(
            [self._output_proba_name],
            {self._input_name: input_tensor},
        )
        raw = np.asarray(outputs[0], dtype=np.float32)
        if raw.ndim == 2 and raw.shape[1] == 3:
            probs = raw[0]
        elif raw.ndim == 1 and raw.shape[0] == 3:
            probs = raw
        else:
            probs = np.array([1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0], dtype=np.float32)

        exp_probs = np.exp(probs - np.max(probs))
        normalized = exp_probs / np.sum(exp_probs)

        buy_prob = float(normalized[2])
        sell_prob = float(normalized[0])
        hold_prob = float(normalized[1])

        max_prob = max(buy_prob, sell_prob, hold_prob)
        label = LABELS[np.argmax(normalized)]

        return PredictionResult(
            label=label,
            confidence=max_prob,
            probabilities={"BUY": buy_prob, "SELL": sell_prob, "HOLD": hold_prob},
            model_loaded=True,
            fallback_used=False,
        )

    def _heuristic_predict(
        self, candles: List[Dict[str, Any]]
    ) -> PredictionResult:
        if not candles:
            return PredictionResult(
                label="HOLD",
                confidence=0.5,
                probabilities={"BUY": 0.33, "SELL": 0.33, "HOLD": 0.34},
                model_loaded=False,
                fallback_used=True,
            )

        last = candles[-1]
        close = float(last.get("close", 0.0))
        rsi = float(last.get("rsi", 50.0))
        macd = float(last.get("macd", 0.0))
        macd_signal = float(last.get("macd_signal", 0.0))
        macd_hist = float(last.get("macd_hist", 0.0))
        ema_fast = float(last.get("ema_fast", 0.0))
        ema_slow = float(last.get("ema_slow", 0.0))
        bb_upper = float(last.get("bb_upper", 0.0))
        bb_lower = float(last.get("bb_lower", 0.0))
        atr = float(last.get("atr", 0.0))

        buy_score = 0.0
        sell_score = 0.0

        if rsi < 30:
            buy_score += 0.3
        elif rsi > 70:
            sell_score += 0.3

        if macd > macd_signal and macd_hist > 0:
            buy_score += 0.25
        elif macd < macd_signal and macd_hist < 0:
            sell_score += 0.25

        if ema_fast > ema_slow and close > ema_fast:
            buy_score += 0.2
        elif ema_fast < ema_slow and close < ema_fast:
            sell_score += 0.2

        if bb_upper > 0 and close > bb_upper:
            sell_score += 0.15
        elif bb_lower > 0 and close < bb_lower:
            buy_score += 0.15

        if len(candles) >= 2:
            prev_close = float(candles[-2].get("close", close))
            if prev_close > 0:
                momentum = (close - prev_close) / prev_close
                if momentum > 0.001:
                    buy_score += 0.1
                elif momentum < -0.001:
                    sell_score += 0.1

        total = buy_score + sell_score
        if total == 0:
            buy_prob = 0.33
            sell_prob = 0.33
            hold_prob = 0.34
            label = "HOLD"
            confidence = 0.5
        else:
            buy_prob = min(1.0, buy_score / total)
            sell_prob = min(1.0, sell_score / total)
            hold_prob = max(0.0, 1.0 - buy_prob - sell_prob)
            if buy_prob > sell_prob and buy_prob > hold_prob:
                label = "BUY"
                confidence = buy_prob
            elif sell_prob > buy_prob and sell_prob > hold_prob:
                label = "SELL"
                confidence = sell_prob
            else:
                label = "HOLD"
                confidence = hold_prob

        return PredictionResult(
            label=label,
            confidence=confidence,
            probabilities={"BUY": buy_prob, "SELL": sell_prob, "HOLD": hold_prob},
            model_loaded=False,
            fallback_used=True,
        )

    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def model_path(self) -> Path:
        return self._model_path

    @property
    def window_size(self) -> int:
        return self._window_size

    @property
    def num_features(self) -> int:
        return self._num_features

    def shutdown(self) -> None:
        self._session = None
        self._loaded = False


def run_inference(
    tensor: np.ndarray,
    model_path: Optional[Path] = None,
    candles: Optional[List[Dict[str, Any]]] = None,
) -> PredictionResult:
    engine = ONNXInferenceEngine(model_path=model_path)
    return engine.predict(tensor, candles=candles)