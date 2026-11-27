from pathlib import Path

import sklearn

from backend.app.models.interfaces import ModelRegistry, SERIALIZED_SKLEARN_VERSION


def test_missing_model_artifact_is_not_configured(tmp_path):
    result = ModelRegistry._load("tabular", tmp_path / "missing.joblib")
    assert result.status == "not_configured"
    assert result.artifact_available is False
    assert result.model_loaded is False


def test_tabular_model_artifact_load_and_known_input_metadata():
    artifact = Path(__file__).parents[1] / "app" / "models" / "models" / "adda_tabular_extra_trees.joblib"
    assert artifact.is_file()
    if sklearn.__version__ == SERIALIZED_SKLEARN_VERSION:
        result = ModelRegistry._load("tabular", artifact)
        assert result.model_loaded is True
        assert result.expected_input_features == 3
        assert result.class_ids == [0, 1, 2]
        assert result.preprocessing_available is False
    else:
        result = ModelRegistry._load("tabular", artifact)
        assert result.status == "unavailable"
        assert result.artifact_available is True
        assert SERIALIZED_SKLEARN_VERSION in result.message


def test_image_model_artifact_load_and_known_input_metadata():
    artifact = Path(__file__).parents[1] / "app" / "models" / "models" / "adda_image_extra_trees.joblib"
    assert artifact.is_file()
    result = ModelRegistry._load("image", artifact)
    if sklearn.__version__ == SERIALIZED_SKLEARN_VERSION:
        assert result.model_loaded is True
        assert result.expected_input_features == 8
        assert result.class_ids == [0, 1, 2, 3]
        assert result.preprocessing_available is False
    else:
        assert result.status == "unavailable"
        assert result.artifact_available is True
