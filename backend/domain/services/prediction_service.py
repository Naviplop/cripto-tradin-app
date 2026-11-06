from __future__ import annotations

import logging
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

from infrastructure.ai.feature_engineering import StreamingFeatureEngine
from infrastructure.ai.model_registry import ModelRecord, ModelRegistry, get_default_registry
from infrastructure.ai.onnx_runtime import ONNXInferenceEngine, PredictionResult
from infrastructure.ai.pipeline import PredictionPipeline

logger = logging.getLogger(__name__)


class PredictionService:
    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        model_path: Optional[Path] = None,
        window_size: int = 30,
    ) -> None:
        self._registry = registry or get_default_registry()
        self._model_path = model_path
        self._window_size = window_size
        self._pipeline = PredictionPipeline(
            model_registry=self._registry,
            model_path=model_path,
            window_size=window_size,
        )
        self._lock = RLock()
        self._feature_engine = StreamingFeatureEngine(window_size=window_size)

    def predict(
        self,
        candles: List[Dict[str, Any]],
    ) -> PredictionResult:
        with self._lock:
            if len(candles) < self._window_size:
                logger.warning(
                    "Insufficient candles: %d provided, %d required",
                    len(candles),
                    self._window_size,
                )
            return self._pipeline.predict(candles)

    async def predict_async(
        self,
        candles: List[Dict[str, Any]],
    ) -> PredictionResult:
        return await self._pipeline.predict_async(candles)

    def predict_with_details(
        self,
        candles: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        with self._lock:
            return self._pipeline.predict_with_features(candles)

    def compute_features(
        self,
        candles: List[Dict[str, Any]],
    ) -> Any:
        with self._lock:
            self._feature_engine.clear()
            self._feature_engine.push_batch(candles)
            return self._feature_engine.compute_features()

    def get_model_info(self) -> Optional[Dict[str, Any]]:
        record = self._registry.get_active_model()
        if record is None:
            return None
        return {
            "name": record.name,
            "version": record.version,
            "features": record.features,
            "window_size": record.window_size,
            "provider": record.provider,
            "model_type": record.model_type,
            "last_updated": record.last_updated,
            "loaded": self._pipeline.is_model_loaded(),
        }

    def update_model(self, model_path: Path) -> PredictionResult:
        with self._lock:
            self._model_path = model_path
            self._pipeline.update_model(model_path)
            return self.predict([])

    def register_model(
        self,
        name: str,
        version: str,
        features: List[str],
        window_size: int,
        provider: str = "CPUExecutionProvider",
        model_type: str = "RandomForest",
        path: str = "",
    ) -> ModelRecord:
        return self._registry.register(
            name=name,
            version=version,
            features=features,
            window_size=window_size,
            provider=provider,
            model_type=model_type,
            path=path,
        )

    def unregister_model(self, name: str) -> bool:
        return self._registry.unregister(name)

    def get_model(self, name: str) -> Optional[ModelRecord]:
        return self._registry.get(name)

    def list_models(self) -> Dict[str, ModelRecord]:
        return self._registry.get_all()

    def is_model_loaded(self) -> bool:
        return self._pipeline.is_model_loaded()

    def shutdown(self) -> None:
        self._pipeline.shutdown()


def get_prediction_service(
    registry: Optional[ModelRegistry] = None,
    model_path: Optional[Path] = None,
) -> PredictionService:
    return PredictionService(
        registry=registry,
        model_path=model_path,
    )