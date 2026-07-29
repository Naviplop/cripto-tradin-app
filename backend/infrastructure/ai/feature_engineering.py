from __future__ import annotations

import json
import math
import os
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


WINDOW_SIZE = 30
NUM_FEATURES = 17
FEATURE_NAMES = [
    "open", "high", "low", "close", "volume",
    "rsi", "macd", "macd_signal", "macd_hist",
    "bb_upper", "bb_mid", "bb_lower",
    "atr", "ema_fast", "ema_slow",
    "log_return", "realized_volatility",
]

SCALER_PARAMS_PATH = Path(
    os.environ.get("TRADING_APP_DATA_DIR", os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LAFM"))
) / "models" / "scaler_params.json"


class StreamingFeatureEngine:
    def __init__(self, window_size: int = WINDOW_SIZE) -> None:
        self.window_size = window_size
        self._buffer: deque = deque(maxlen=window_size + 30)
        self._scaler_mean: Optional[np.ndarray] = None
        self._scaler_scale: Optional[np.ndarray] = None

    def push(self, candle: Dict[str, float]) -> None:
        self._buffer.append(candle)

    def push_batch(self, candles: List[Dict[str, float]]) -> None:
        for c in candles:
            self._buffer.append(c)

    def clear(self) -> None:
        self._buffer.clear()

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def is_ready(self) -> bool:
        return len(self._buffer) >= self.window_size

    def compute_features(self, window: Optional[List[Dict[str, float]]] = None) -> np.ndarray:
        if window is None:
            if len(self._buffer) < self.window_size:
                raise ValueError(
                    f"Insufficient data: {len(self._buffer)} candles, need {self.window_size}"
                )
            window = list(self._buffer)[-self.window_size :]

        if len(window) < self.window_size:
            raise ValueError(
                f"Insufficient data: {len(window)} candles, need {self.window_size}"
            )

        closes = np.array([c["close"] for c in window], dtype=np.float64)
        highs = np.array([c["high"] for c in window], dtype=np.float64)
        lows = np.array([c["low"] for c in window], dtype=np.float64)
        volumes = np.array([c["volume"] for c in window], dtype=np.float64)
        opens = np.array([c["open"] for c in window], dtype=np.float64)

        features: List[np.ndarray] = []

        features.append(opens)
        features.append(highs)
        features.append(lows)
        features.append(closes)
        features.append(volumes)

        rsi = self._compute_rsi(closes, 14)
        features.append(rsi)

        macd_line, macd_signal, macd_hist = self._compute_macd(closes, 12, 26, 9)
        features.append(macd_line)
        features.append(macd_signal)
        features.append(macd_hist)

        bb_upper, bb_mid, bb_lower = self._compute_bollinger_bands(closes, 20, 2.0)
        features.append(bb_upper)
        features.append(bb_mid)
        features.append(bb_lower)

        atr = self._compute_atr(highs, lows, closes, 14)
        features.append(atr)

        ema_fast = self._compute_ema(closes, 10)
        features.append(ema_fast)

        ema_slow = self._compute_ema(closes, 30)
        features.append(ema_slow)

        log_return = self._compute_log_returns(closes)
        features.append(log_return)

        realized_vol = self._compute_realized_volatility(log_return, 20)
        features.append(realized_vol)

        matrix = np.column_stack(features).astype(np.float32)
        return matrix

    def compute_tensor(self, window: Optional[List[Dict[str, float]]] = None) -> np.ndarray:
        matrix = self.compute_features(window)
        if self._scaler_mean is not None and self._scaler_scale is not None:
            matrix = (matrix - self._scaler_mean) / np.where(
                self._scaler_scale == 0, 1.0, self._scaler_scale
            )
        return matrix.astype(np.float32)

    def get_normalized_tensor(self, candles: List[Dict[str, float]]) -> np.ndarray:
        matrix = self.compute_features(candles)
        if self._scaler_mean is not None and self._scaler_scale is not None:
            matrix = (matrix - self._scaler_mean) / np.where(
                self._scaler_scale == 0, 1.0, self._scaler_scale
            )
        return matrix.astype(np.float32)

    def normalize(self, matrix: np.ndarray) -> np.ndarray:
        if self._scaler_mean is not None and self._scaler_scale is not None:
            matrix = (matrix - self._scaler_mean) / np.where(
                self._scaler_scale == 0, 1.0, self._scaler_scale
            )
        return matrix.astype(np.float32)

    def set_scaler_params(self, mean: np.ndarray, scale: np.ndarray) -> None:
        self._scaler_mean = mean.astype(np.float32)
        self._scaler_scale = scale.astype(np.float32)

    def load_scaler_params(self, path: Optional[Path] = None) -> bool:
        target = path or SCALER_PARAMS_PATH
        if not target.exists():
            return False
        try:
            with open(target, "r", encoding="utf-8") as f:
                params = json.load(f)
            self._scaler_mean = np.array(params["mean"], dtype=np.float32)
            self._scaler_scale = np.array(params["scale"], dtype=np.float32)
            return True
        except Exception:
            return False

    def save_scaler_params(self, path: Optional[Path] = None) -> bool:
        target = path or SCALER_PARAMS_PATH
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            params = {
                "mean": self._scaler_mean.tolist() if self._scaler_mean is not None else [],
                "scale": self._scaler_scale.tolist() if self._scaler_scale is not None else [],
            }
            with open(target, "w", encoding="utf-8") as f:
                json.dump(params, f, indent=2)
            return True
        except Exception:
            return False

    def compute_and_normalize(self, candles: List[Dict[str, float]]) -> np.ndarray:
        matrix = self.compute_features(candles)
        if self._scaler_mean is not None and self._scaler_scale is not None:
            matrix = (matrix - self._scaler_mean) / np.where(
                self._scaler_scale == 0, 1.0, self._scaler_scale
            )
        return matrix.astype(np.float32)

    @staticmethod
    def _compute_rsi(closes: np.ndarray, period: int = 14) -> np.ndarray:
        deltas = np.diff(closes)
        seed = deltas[: period + 1]
        up = seed[seed >= 0].sum()
        down = -seed[seed < 0].sum()
        rs = up / down if down != 0 else 0.0
        rsi = np.zeros(len(closes), dtype=np.float64)
        rsi[:period] = 50.0
        if down == 0 and up == 0:
            rsi[period] = 50.0
        else:
            rsi[period] = 100.0 - 100.0 / (1.0 + rs)
        for i in range(period + 1, len(closes)):
            delta = deltas[i - 1]
            upval = delta if delta > 0 else 0.0
            downval = -delta if delta < 0 else 0.0
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            rs = up / down if down != 0 else 0.0
            rsi[i] = 100.0 - 100.0 / (1.0 + rs)
        return rsi

    @staticmethod
    def _compute_macd(
        closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        ema_fast = StreamingFeatureEngine._compute_ema(closes, fast)
        ema_slow = StreamingFeatureEngine._compute_ema(closes, slow)
        macd_line = ema_fast - ema_slow
        macd_signal = StreamingFeatureEngine._compute_ema(macd_line, signal)
        macd_hist = macd_line - macd_signal
        return macd_line, macd_signal, macd_hist

    @staticmethod
    def _compute_ema(values: np.ndarray, period: int) -> np.ndarray:
        ema = np.zeros(len(values), dtype=np.float64)
        if len(values) < period:
            return ema
        sma = np.mean(values[:period])
        ema[period - 1] = sma
        multiplier = 2.0 / (period + 1)
        for i in range(period, len(values)):
            ema[i] = (values[i] - ema[i - 1]) * multiplier + ema[i - 1]
        return ema

    @staticmethod
    def _compute_bollinger_bands(
        closes: np.ndarray, period: int = 20, num_std: float = 2.0
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        upper = np.zeros(len(closes), dtype=np.float64)
        mid = np.zeros(len(closes), dtype=np.float64)
        lower = np.zeros(len(closes), dtype=np.float64)
        if len(closes) < period:
            return upper, mid, lower
        for i in range(period - 1, len(closes)):
            window = closes[i - period + 1 : i + 1]
            mid[i] = np.mean(window)
            std = np.std(window)
            upper[i] = mid[i] + num_std * std
            lower[i] = mid[i] - num_std * std
        return upper, mid, lower

    @staticmethod
    def _compute_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> np.ndarray:
        atr = np.zeros(len(closes), dtype=np.float64)
        if len(closes) < period + 1:
            return atr
        tr_values = np.zeros(len(closes), dtype=np.float64)
        tr_values[0] = highs[0] - lows[0]
        for i in range(1, len(closes)):
            tr_values[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        atr[period - 1] = np.mean(tr_values[1 : period])
        for i in range(period, len(closes)):
            atr[i] = (atr[i - 1] * (period - 1) + tr_values[i]) / period
        return atr

    @staticmethod
    def _compute_log_returns(closes: np.ndarray) -> np.ndarray:
        returns = np.zeros(len(closes), dtype=np.float64)
        for i in range(1, len(closes)):
            if closes[i - 1] > 0:
                returns[i] = math.log(closes[i] / closes[i - 1])
        return returns

    @staticmethod
    def _compute_realized_volatility(log_returns: np.ndarray, window: int = 20) -> np.ndarray:
        vol = np.zeros(len(log_returns), dtype=np.float64)
        if len(log_returns) < window:
            return vol
        for i in range(window - 1, len(log_returns)):
            start = i - window + 1
            vol[i] = np.sqrt(np.sum(log_returns[start : i + 1] ** 2))
        return vol


def compute_features_sync(candles: List[Dict[str, float]], window_size: int = WINDOW_SIZE) -> np.ndarray:
    engine = StreamingFeatureEngine(window_size=window_size)
    engine.push_batch(candles)
    return engine.compute_features()


def compute_tensor_sync(
    candles: List[Dict[str, float]],
    window_size: int = WINDOW_SIZE,
    scaler_mean: Optional[np.ndarray] = None,
    scaler_scale: Optional[np.ndarray] = None,
) -> np.ndarray:
    engine = StreamingFeatureEngine(window_size=window_size)
    engine.push_batch(candles)
    matrix = engine.compute_features()
    if scaler_mean is not None and scaler_scale is not None:
        matrix = (matrix - scaler_mean) / np.where(scaler_scale == 0, 1.0, scaler_scale)
    return matrix.astype(np.float32)


def normalize_matrix(
    matrix: np.ndarray,
    scaler_mean: np.ndarray,
    scaler_scale: np.ndarray,
) -> np.ndarray:
    return ((matrix - scaler_mean) / np.where(scaler_scale == 0, 1.0, scaler_scale)).astype(np.float32)


def denormalize_matrix(
    matrix: np.ndarray,
    scaler_mean: np.ndarray,
    scaler_scale: np.ndarray,
) -> np.ndarray:
    return (matrix * scaler_scale + scaler_mean).astype(np.float32)


def get_feature_count() -> int:
    return NUM_FEATURES


def get_feature_names() -> List[str]:
    return list(FEATURE_NAMES)


def get_window_size() -> int:
    return WINDOW_SIZE