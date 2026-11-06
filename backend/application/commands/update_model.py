from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from infrastructure.ai.model_registry import ModelRegistry
from infrastructure.ai.onnx_runtime import ONNXInferenceEngine
from infrastructure.ai.training_helpers import (
    load_feature_names,
    load_scaler_from_disk,
    persist_scaler_to_disk,
    save_feature_names,
)

logger = logging.getLogger(__name__)

MODELS_DIR = Path(
    os.environ.get("TRADING_APP_DATA_DIR", os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "LAFM"))
) / "models"

REQUIRED_FEATURES = [
    "open", "high", "low", "close", "volume",
    "rsi", "macd", "macd_signal", "macd_hist",
    "bb_upper", "bb_mid", "bb_lower",
    "atr", "ema_fast", "ema_slow",
    "log_return", "realized_volatility",
]

MIN_MODEL_SIZE_BYTES = 1024


class ModelUpdateError(Exception):
    pass


class ModelValidator:
    @staticmethod
    def validate_model_file(path: Path) -> Dict[str, Any]:
        errors: list[str] = []
        warnings: list[str] = []

        if not path.exists():
            raise ModelUpdateError(f"Model file does not exist: {path}")

        if not path.is_file():
            raise ModelUpdateError(f"Model path is not a file: {path}")

        if path.stat().st_size < MIN_MODEL_SIZE_BYTES:
            errors.append(
                f"Model file too small ({path.stat().st_size} bytes), "
                f"minimum is {MIN_MODEL_SIZE_BYTES} bytes"
            )

        try:
            with open(path, "rb") as f:
                header = f.read(8)
            if len(header) < 8:
                errors.append("Model file too small to be valid")
        except IOError as exc:
            errors.append(f"Cannot read model file: {exc}")

        scaler_params = load_scaler_from_disk(path.parent)
        if not scaler_params:
            warnings.append("No scaler_params.json found; model may not be normalized")
        else:
            mean = scaler_params.get("mean")
            scale = scaler_params.get("scale")
            if mean is not None and scale is not None:
                from infrastructure.ai.training_helpers import validate_scaler_params
                if not validate_scaler_params(
                    mean, scale, len(REQUIRED_FEATURES)
                ):
                    warnings.append("Scaler params shape mismatch with expected features")

        feature_names = load_feature_names(path.parent)
        if not feature_names:
            warnings.append("No feature_names.json found")
        else:
            missing = [f for f in REQUIRED_FEATURES if f not in feature_names]
            if missing:
                warnings.append(f"Missing features in feature_names.json: {missing}")

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    @staticmethod
    def validate_onnx_compatibility(path: Path) -> Dict[str, Any]:
        try:
            import onnx
            model = onnx.load(str(path))
            onnx.checker.check_model(model)
            return {"compatible": True, "errors": []}
        except Exception as exc:
            return {"compatible": False, "errors": [str(exc)]}


def download_model(
    url: str,
    dest: Path,
    expected_hash: Optional[str] = None,
) -> Path:
    tmp_dir = dest.parent / "_tmp_download"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_file = tmp_dir / dest.name

    try:
        resp = requests.get(url, timeout=60, stream=True)
        resp.raise_for_status()
        with open(tmp_file, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        if expected_hash:
            file_hash = compute_file_hash(tmp_file)
            if file_hash != expected_hash:
                raise ModelUpdateError(
                    f"Hash mismatch: expected {expected_hash}, got {file_hash}"
                )

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(tmp_file), str(dest))
        return dest
    finally:
        if tmp_file.exists():
            tmp_file.unlink()
        try:
            tmp_dir.rmdir()
        except OSError:
            pass


def compute_file_hash(path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def execute_model_update(
    download_url: str,
    model_name: str = "trading_model",
    version: Optional[str] = None,
    expected_hash: Optional[str] = None,
    registry: Optional[ModelRegistry] = None,
) -> Dict[str, Any]:
    reg = registry or ModelRegistry()

    dest = MODELS_DIR / f"{model_name}.onnx"
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading model from %s", download_url)
    download_model(download_url, dest, expected_hash=expected_hash)

    validation = ModelValidator.validate_model_file(dest)
    if not validation["valid"]:
        dest.unlink(missing_ok=True)
        raise ModelUpdateError(
            f"Model validation failed: {validation['errors']}"
        )

    for warning in validation.get("warnings", []):
        logger.warning("Model validation warning: %s", warning)

    onnx_compat = ModelValidator.validate_onnx_compatibility(dest)
    if not onnx_compat["compatible"]:
        logger.warning("ONNX compatibility check failed: %s", onnx_compat["errors"])

    features = load_feature_names(dest.parent) or REQUIRED_FEATURES
    if not version:
        version = "1.0.0"

    record = reg.register(
        name=model_name,
        version=version,
        features=features,
        window_size=30,
        provider="CPUExecutionProvider",
        model_type="ONNX",
        path=str(dest),
    )

    engine = ONNXInferenceEngine(model_path=dest)
    loaded = engine.is_loaded()
    engine.shutdown()

    return {
        "status": "updated",
        "model_path": str(dest),
        "record": record.to_dict(),
        "loaded": loaded,
        "validation": validation,
        "onnx_compatible": onnx_compat["compatible"],
    }


def hot_update_model(
    download_url: str,
    version: Optional[str] = None,
    expected_hash: Optional[str] = None,
) -> Dict[str, Any]:
    return execute_model_update(
        download_url=download_url,
        version=version,
        expected_hash=expected_hash,
    )