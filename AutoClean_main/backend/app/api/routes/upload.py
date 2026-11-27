from fastapi import APIRouter, File, UploadFile

from backend.app.schemas.responses import ErrorEnvelope, UploadResponse
from backend.app.services.file_service import store_upload
from backend.app.services.image_dataset_service import store_image_dataset

router = APIRouter(tags=["files"])


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=201,
    responses={400: {"model": ErrorEnvelope}, 413: {"model": ErrorEnvelope}, 415: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}, 500: {"model": ErrorEnvelope}},
)
async def upload_file(file: UploadFile = File(..., description="A CSV, PNG, JPG or JPEG file.")):
    return await store_upload(file)


@router.post("/upload/image-dataset", response_model=UploadResponse, status_code=201, responses={400: {"model": ErrorEnvelope}, 413: {"model": ErrorEnvelope}, 415: {"model": ErrorEnvelope}, 422: {"model": ErrorEnvelope}})
async def upload_image_dataset(manifest: UploadFile = File(...), images_zip: UploadFile = File(...)):
    return await store_image_dataset(manifest, images_zip)
