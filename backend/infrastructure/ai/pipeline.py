from __future__ import annotations

import asyncio
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from infrastructure.ai.feature_engineering import StreamingFeatureEngine
from infrastructure.ai.model_registry import ModelRegistry, get_default_registry
from infrastructure.ai.onnx_runtime import ONNXInferenceEngine, PredictionResult

logger = logging.getLogger(__name__)


class PredictionPipeline:
    def __init__(
        self,
        model_registry: Optional[ModelRegistry] = None,
        model_path: Optional[Path] = None,
        window_size: int = 30,
        max_workers: int = 2,
    ) -> None:
        self._registry = model_registry or get_default_registry()
        self._model_path = model_path
        self._window_size = window_size
        self._engine = StreamingFeatureEngine(window_size=window_size)
        self._inference = ONNXInferenceEngine(model_path=model_path)
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers)

    def set_model_path(self, path: Path) -> None:
        with self._lock:
            self._model_path = path
            self._inference = ONNXInferenceEngine(model_path=path)

    async def predict_async(
        self,
        candles: List[Dict[str, Any]],
    ) -> PredictionResult:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            self._executor,
            self._predict_sync,
            candles,
        )

    def predict(
        self,
        candles: List[Dict[str, Any]],
    ) -> PredictionResult:
        return self._predict_sync(candles)

    def _predict_sync(
        self,
        candles: List[Dict[str, Any]],
    ) -> PredictionResult:
        with self._lock:
            self._engine.clear()
            self._engine.push_batch(candles)
            if not self._engine.is_ready:
                return self._inference.predict(
                    np.zeros((1, self._window_size, 17), dtype=np.float32),
                    candles=candles,
                )
            tensor = self._engine.compute_tensor()
            tensor_3d = tensor.reshape(1, self._window_size, self._engine.compute_features(
                candles[-self._window_size :]
            ).shape[1]).astype(np.float32)
            return self._inference.predict(tensor_3d, candles=candles)

    def predict_with_features(
        self,
        candles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        with self._lock:
            self._engine.clear()
            self._engine.push_batch(candles)
            features = self._engine.compute_features()
            tensor_3d = features.reshape(1, features.shape[0], features.shape[1]).astype(np.float32)
            result = self._inference.predict(tensor_3d, candles=candles)
            return {
                "prediction": result,
                "features_shape": features.shape,
                "features": features.tolist(),
                "model_loaded": result.model_loaded,
                "fallback_used": result.fallback_used,
            }

    def is_model_loaded(self) -> bool:
        return self._inference.is_loaded()

    def get_active_model_info(self) -> Optional[Dict[str, Any]]:
        record = self._registry.get_active_model()
        if record is None:
            return None
        return record.to_dict()

    def update_model(self, model_path: Path) -> None:
        with self._lock:
            self._model_path = model_path
            self._inference = ONNXInferenceEngine(model_path=model_path)

    def list_models(self) -> Dict[str, Any]:
        return self._registry.get_all()

    def compute_features(self, candles: List[Dict[str, Any]]) -> np.ndarray:
        with self._lock:
            self._engine.clear()
            self._engine.push_batch(candles)
            return self._engine.compute_features()

    def shutdown(self) -> None:
        self._inference.shutdown()
        self._executor.shutdown(wait=False)


async def predict_pipeline(
    candles: List[Dict[str, Any]],
    model_registry: Optional[ModelRegistry] = None,
    model_path: Optional[Path] = None,
) -> PredictionResult:
    pipeline = PredictionPipeline(
        model_registry=model_registry,
        model_path=model_path,
    )
    return await pipeline.predict_async(candles)


def predict_pipeline_sync(
    candles: List[Dict[str, Any]],
    model_registry: Optional[ModelRegistry] = None,
    model_path: Optional[Path] = None,
) -> PredictionResult:
    pipeline = PredictionPipeline(
        model_registry=model_registry,
        model_path=model_path,
    )
    return pipeline.predict(candles)