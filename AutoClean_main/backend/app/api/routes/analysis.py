from fastapi import APIRouter

from backend.app.schemas.responses import AnalysisResponse, ErrorEnvelope
from backend.app.core.config import get_settings
from backend.app.models.interfaces import model_registry
from backend.app.services.file_service import find_upload
from backend.app.services.tabular_service import analyze_csv_path
from backend.app.services.file_service import read_upload_metadata
from backend.app.services.image_dataset_service import analyze_image_dataset

router = APIRouter(tags=["analysis"])


@router.get("/analysis/{file_id}", response_model=AnalysisResponse, responses={404: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}})
def get_analysis(file_id: str):
    model_registry.load_once(get_settings())
    path = find_upload(file_id)
    metadata = read_upload_metadata(file_id) or {}
    if metadata.get("data_type") == "image_dataset":
        return AnalysisResponse(
            file_id=file_id,
            data_type="image_dataset",
            status="profiled",
            summary=analyze_image_dataset(file_id),
            model_status=model_registry.models["image"].status,
            model_input_features=model_registry.models["image"].expected_input_features,
            message="Image defects were measured with deterministic quality metrics. Trained ADDA inference remains disabled because its feature pipeline is undocumented.",
        )
    model_name = "tabular" if path.suffix.lower() == ".csv" else "image"
    model = model_registry.models[model_name]
    if path.suffix.lower() == ".csv":
        return AnalysisResponse(
            file_id=file_id,
            data_type="tabular",
            status="profiled",
            summary=analyze_csv_path(path),
            model_status=model.status,
            model_input_features=model.expected_input_features,
            message=f"Deterministic CSV profiling is available. {model.message}",
        )
    return AnalysisResponse(
        file_id=file_id,
        data_type="image",
        status="model_not_available",
        summary={},
        model_status=model.status,
        model_input_features=model.expected_input_features,
        message=f"Image upload was validated, but quality classification is disabled. {model.message}",
    )
