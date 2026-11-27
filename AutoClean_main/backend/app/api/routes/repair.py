from fastapi import APIRouter, HTTPException

from backend.app.core.config import get_settings
from backend.app.schemas.responses import ErrorEnvelope, RepairResponse
from backend.app.services.file_service import find_upload, read_upload_metadata
from backend.app.services.image_dataset_service import repair_image_dataset
from backend.app.services.repair_service import repair_csv

router = APIRouter(tags=["repair"])


@router.post(
    "/repair/{file_id}",
    response_model=RepairResponse,
    responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}},
)
def repair_file(file_id: str):
    path = find_upload(file_id)
    metadata = read_upload_metadata(file_id) or {}
    if metadata.get("data_type") == "image_dataset":
        return repair_image_dataset(file_id, get_settings())
    if path.suffix.lower() != ".csv":
        raise HTTPException(status_code=400, detail={"code": "unsupported_repair_input", "message": "Repair currently supports CSV files only."})
    return repair_csv(file_id, path, get_settings())
