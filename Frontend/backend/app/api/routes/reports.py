from fastapi import APIRouter

from backend.app.schemas.responses import ErrorEnvelope, ReportResponse
from backend.app.services.file_service import find_upload
from backend.app.services.report_service import generate_reports

router = APIRouter(tags=["reports"])


@router.get(
    "/reports/{file_id}",
    response_model=ReportResponse,
    responses={404: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 503: {"model": ErrorEnvelope}},
)
def get_report(file_id: str):
    source_path = find_upload(file_id)
    return generate_reports(file_id, source_path)
