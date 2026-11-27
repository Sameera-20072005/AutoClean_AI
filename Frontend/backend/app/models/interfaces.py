import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import joblib
import pandas as pd
import sklearn
from sklearn.ensemble import ExtraTreesClassifier

from backend.app.core.config import Settings

logger = logging.getLogger("autoclean.models")
SERIALIZED_SKLEARN_VERSION = "1.6.1"


class TabularADDA(Protocol):
    """Adapter expected to wrap the Colab model and its original preprocessing."""

    def predict_cells(self, frame: pd.DataFrame) -> list[dict[str, Any]]: ...


class ImageADDA(Protocol):
    """Adapter expected to apply the original image preprocessing before inference."""

    def predict_quality(self, image: Any) -> dict[str, Any]: ...


@dataclass
class LoadedModel:
    status: str
    artifact_available: bool
    model_loaded: bool
    preprocessing_available: bool
    expected_input_features: int | None
    class_ids: list[int] | None
    message: str
    estimator: ExtraTreesClassifier | None = None

    def health_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "artifact_available": self.artifact_available,
            "model_loaded": self.model_loaded,
            "preprocessing_available": self.preprocessing_available,
            "expected_input_features": self.expected_input_features,
            "class_ids": self.class_ids,
            "message": self.message,
        }


def unavailable_model(message: str, artifact_available: bool = False) -> LoadedModel:
    return LoadedModel("unavailable" if artifact_available else "not_configured", artifact_available, False, False, None, None, message)


class ModelRegistry:
    """Loads each exported estimator once; prediction stays gated until preprocessing is verified."""

    def __init__(self):
        self.models: dict[str, LoadedModel] = {}
        self._configuration_key: tuple | None = None

    def load_once(self, settings: Settings) -> None:
        key = (
            str(settings.tabular_model_path),
            settings.tabular_model_path.stat().st_mtime_ns if settings.tabular_model_path.is_file() else None,
            str(settings.image_model_path),
            settings.image_model_path.stat().st_mtime_ns if settings.image_model_path.is_file() else None,
            sklearn.__version__,
        )
        if key == self._configuration_key:
            return
        self._configuration_key = key
        self.models = {
            "tabular": self._load("tabular", settings.tabular_model_path),
            "image": self._load("image", settings.image_model_path),
        }

    @staticmethod
    def _load(name: str, path: Path) -> LoadedModel:
        if not path.is_file():
            logger.info("%s ADDA artifact is not configured", name)
            return unavailable_model("Model artifact is missing. Export the trained model from Colab.")
        if sklearn.__version__ != SERIALIZED_SKLEARN_VERSION:
            message = f"Model was serialized with scikit-learn {SERIALIZED_SKLEARN_VERSION}; installed version {sklearn.__version__} is incompatible."
            logger.error("%s model load skipped: %s", name, message)
            return unavailable_model(message, artifact_available=True)
        try:
            estimator = joblib.load(path)
            if not isinstance(estimator, ExtraTreesClassifier):
                raise TypeError(f"Expected ExtraTreesClassifier, found {type(estimator).__name__}")
            feature_count = int(estimator.n_features_in_)
            class_ids = [int(label) for label in estimator.classes_]
            logger.info("Loaded %s ADDA ExtraTreesClassifier (%s input features, numeric labels %s)", name, feature_count, class_ids)
            return LoadedModel(
                status="loaded_preprocessing_unavailable",
                artifact_available=True,
                model_loaded=True,
                preprocessing_available=False,
                expected_input_features=feature_count,
                class_ids=class_ids,
                message="Estimator loaded. Notebook feature extraction and semantic class mapping are unavailable, so predictions are disabled.",
                estimator=estimator,
            )
        except Exception as exc:
            logger.exception("Failed to load %s ADDA model (%s)", name, type(exc).__name__)
            return unavailable_model("Model artifact could not be loaded; see backend logs for the technical reason.", artifact_available=True)


model_registry = ModelRegistry()
