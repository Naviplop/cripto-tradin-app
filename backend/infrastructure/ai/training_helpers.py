from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


DEFAULT_MODEL_DIR = Path(
    os.environ.get("TRADING_APP_DATA_DIR", os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LAFM"))
) / "models"


def serialize_scaler_params(
    mean: np.ndarray,
    scale: np.ndarray,
    var: Optional[np.ndarray] = None,
    n_features_in: Optional[int] = None,
    output_path: Optional[Path] = None,
) -> Path:
    target = output_path or DEFAULT_MODEL_DIR / "scaler_params.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    params: Dict[str, Any] = {
        "mean": mean.tolist(),
        "scale": scale.tolist(),
    }
    if var is not None:
        params["var"] = var.tolist()
    if n_features_in is not None:
        params["n_features_in"] = int(n_features_in)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(params, f, indent=2)
    return target


def deserialize_scaler_params(
    path: Optional[Path] = None,
) -> Dict[str, np.ndarray]:
    target = path or DEFAULT_MODEL_DIR / "scaler_params.json"
    if not target.exists():
        return {}
    with open(target, "r", encoding="utf-8") as f:
        data = json.load(f)
    result: Dict[str, np.ndarray] = {}
    if "mean" in data:
        result["mean"] = np.array(data["mean"], dtype=np.float32)
    if "scale" in data:
        result["scale"] = np.array(data["scale"], dtype=np.float32)
    if "var" in data:
        result["var"] = np.array(data["var"], dtype=np.float32)
    if "n_features_in" in data:
        result["n_features_in"] = np.array([data["n_features_in"]], dtype=np.int64)
    return result


def save_feature_names(
    feature_names: List[str],
    output_path: Optional[Path] = None,
) -> Path:
    target = output_path or DEFAULT_MODEL_DIR / "feature_names.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(feature_names, f, indent=2)
    return target


def load_feature_names(
    path: Optional[Path] = None,
) -> List[str]:
    target = path or DEFAULT_MODEL_DIR / "feature_names.json"
    if not target.exists():
        return []
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def save_model_metadata(
    metadata: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    target = output_path or DEFAULT_MODEL_DIR / "model_metadata.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    return target


def load_model_metadata(
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    target = path or DEFAULT_MODEL_DIR / "model_metadata.json"
    if not target.exists():
        return {}
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_scaler_params(
    mean: np.ndarray,
    scale: np.ndarray,
    num_features: int,
) -> bool:
    if mean.shape[0] != num_features:
        return False
    if scale.shape[0] != num_features:
        return False
    if np.any(scale == 0):
        return False
    if not np.all(np.isfinite(mean)):
        return False
    if not np.all(np.isfinite(scale)):
        return False
    if np.any(scale < 0):
        return False
    return True


def compute_scaler_params(
    X: np.ndarray,
) -> Dict[str, np.ndarray]:
    mean = np.mean(X, axis=0).astype(np.float32)
    scale = np.std(X, axis=0).astype(np.float32)
    scale = np.where(scale < 1e-9, 1.0, scale)
    var = np.var(X, axis=0).astype(np.float32)
    return {
        "mean": mean,
        "scale": scale,
        "var": var,
        "n_features_in": X.shape[1],
    }


def apply_scaler(
    X: np.ndarray,
    mean: np.ndarray,
    scale: np.ndarray,
) -> np.ndarray:
    return ((X - mean) / np.where(scale == 0, 1.0, scale)).astype(np.float32)


def inverse_scaler(
    X: np.ndarray,
    mean: np.ndarray,
    scale: np.ndarray,
) -> np.ndarray:
    return (X * scale + mean).astype(np.float32)


def scaler_params_to_json(
    mean: np.ndarray,
    scale: np.ndarray,
    var: Optional[np.ndarray] = None,
    n_features_in: Optional[int] = None,
) -> str:
    params: Dict[str, Any] = {
        "mean": mean.tolist(),
        "scale": scale.tolist(),
    }
    if var is not None:
        params["var"] = var.tolist()
    if n_features_in is not None:
        params["n_features_in"] = int(n_features_in)
    return json.dumps(params, indent=2)


def scaler_params_from_json(json_str: str) -> Dict[str, np.ndarray]:
    data = json.loads(json_str)
    result: Dict[str, np.ndarray] = {}
    if "mean" in data:
        result["mean"] = np.array(data["mean"], dtype=np.float32)
    if "scale" in data:
        result["scale"] = np.array(data["scale"], dtype=np.float32)
    if "var" in data:
        result["var"] = np.array(data["var"], dtype=np.float32)
    if "n_features_in" in data:
        result["n_features_in"] = np.array([data["n_features_in"]], dtype=np.int64)
    return result


def persist_scaler_to_disk(
    mean: np.ndarray,
    scale: np.ndarray,
    output_dir: Optional[Path] = None,
) -> Path:
    target_dir = output_dir or DEFAULT_MODEL_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / "scaler_params.json"
    return serialize_scaler_params(mean, scale, output_path=path)


def load_scaler_from_disk(
    input_dir: Optional[Path] = None,
) -> Dict[str, np.ndarray]:
    target_dir = input_dir or DEFAULT_MODEL_DIR
    return deserialize_scaler_params(target_dir / "scaler_params.json")