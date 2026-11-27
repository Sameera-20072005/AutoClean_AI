from fastapi import APIRouter

from backend.app.schemas.responses import ErrorEnvelope, ValidationResponse
from backend.app.services.file_service import find_upload
from backend.app.services.repair_service import read_validation

router = APIRouter(tags=["validation"])


@router.get("/validation/{file_id}", response_model=ValidationResponse, responses={404: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}})
def get_validation(file_id: str):
    find_upload(file_id)
    result = read_validation(file_id)
    if result:
        return ValidationResponse(file_id=file_id, **result)
    return ValidationResponse(
        file_id=file_id,
        status="not_available",
        checks=[],
        message="No repair output exists for this file, so ARVA has not run.",
    )
