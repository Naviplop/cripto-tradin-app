from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

MODELS_DIR = Path(
    os.environ.get("TRADING_APP_DATA_DIR", os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LAFM"))
) / "models"

REGISTRY_PATH = MODELS_DIR / "model_registry.json"

SUPPORTED_PROVIDERS = ["CPUExecutionProvider"]

SUPPORTED_MODEL_TYPES = [
    "RandomForest",
    "XGBoost",
    "LightGBM",
    "LSTM",
    "LightTransformer",
]


class ModelRecord:
    def __init__(
        self,
        name: str,
        version: str,
        features: List[str],
        window_size: int,
        provider: str = "CPUExecutionProvider",
        model_type: str = "RandomForest",
        path: str = "",
        last_updated: Optional[str] = None,
    ) -> None:
        self.name = name
        self.version = version
        self.features = features
        self.window_size = window_size
        self.provider = provider
        self.model_type = model_type
        self.path = path
        self.last_updated = last_updated or datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "features": self.features,
            "window_size": self.window_size,
            "provider": self.provider,
            "model_type": self.model_type,
            "path": self.path,
            "last_updated": self.last_updated,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ModelRecord:
        return cls(
            name=data["name"],
            version=data["version"],
            features=data.get("features", []),
            window_size=data.get("window_size", 30),
            provider=data.get("provider", "CPUExecutionProvider"),
            model_type=data.get("model_type", "RandomForest"),
            path=data.get("path", ""),
            last_updated=data.get("last_updated", ""),
        )


class ModelRegistry:
    def __init__(self, registry_path: Optional[Path] = None) -> None:
        self._registry_path = registry_path or REGISTRY_PATH
        self._models: Dict[str, ModelRecord] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        with self._lock:
            if not self._registry_path.exists():
                return
            try:
                with open(self._registry_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, record_data in data.items():
                    self._models[name] = ModelRecord.from_dict(record_data)
            except Exception:
                self._models = {}

    def _save(self) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        with self._lock:
            for name, record in self._models.items():
                data[name] = record.to_dict()
        with open(self._registry_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def register(
        self,
        name: str,
        version: str,
        features: List[str],
        window_size: int,
        provider: str = "CPUExecutionProvider",
        model_type: str = "RandomForest",
        path: str = "",
    ) -> ModelRecord:
        with self._lock:
            record = ModelRecord(
                name=name,
                version=version,
                features=features,
                window_size=window_size,
                provider=provider,
                model_type=model_type,
                path=path,
            )
            self._models[name] = record
            self._save()
            return record

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name in self._models:
                del self._models[name]
                self._save()
                return True
            return False

    def get(self, name: str) -> Optional[ModelRecord]:
        with self._lock:
            return self._models.get(name)

    def get_all(self) -> Dict[str, ModelRecord]:
        with self._lock:
            return dict(self._models)

    def update(self, name: str, **kwargs: Any) -> Optional[ModelRecord]:
        with self._lock:
            if name not in self._models:
                return None
            record = self._models[name]
            for key, value in kwargs.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            record.last_updated = datetime.now(timezone.utc).isoformat()
            self._save()
            return record

    def has_model(self, name: str) -> bool:
        with self._lock:
            if name not in self._models:
                return False
            record = self._models[name]
            return bool(record.path) and Path(record.path).exists()

    def get_active_model(self) -> Optional[ModelRecord]:
        with self._lock:
            if not self._models:
                return None
            latest = None
            latest_time = ""
            for record in self._models.values():
                if record.last_updated > latest_time:
                    latest_time = record.last_updated
                    latest = record
            return latest

    def clear(self) -> None:
        with self._lock:
            self._models.clear()
            self._save()

    def list_names(self) -> List[str]:
        with self._lock:
            return list(self._models.keys())


def get_default_registry() -> ModelRegistry:
    return ModelRegistry()