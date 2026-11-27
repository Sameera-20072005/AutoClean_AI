from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.app.core.config import get_settings
from backend.app.services.file_service import find_upload

router = APIRouter(tags=["outputs"])


@router.get("/outputs/{file_id}/{kind}")
def get_output(file_id: str, kind: str):
    find_upload(file_id)
    outputs = {
        "cleaned": (f"{file_id}_cleaned.csv", "text/csv"),
        "history": (f"{file_id}_repair_history.csv", "text/csv"),
        "quality-report": (f"{file_id}_quality.json", "application/json"),
        "validation-report": (f"{file_id}_validation.json", "application/json"),
        "repaired-images": (f"{file_id}_repaired_images.zip", "application/zip"),
        "image-history": (f"{file_id}_image_repair_history.csv", "text/csv"),
    }
    if kind not in outputs:
        raise HTTPException(status_code=404, detail={"code": "output_not_found", "message": "The requested repair output was not found."})
    name, media_type = outputs[kind]
    report_kind = kind in {"quality-report", "validation-report"}
    root = get_settings().storage_root / ("reports" if report_kind else "outputs")
    path = root / name
    try:
        safe_file = path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
    except OSError:
        safe_file = False
    if not safe_file:
        raise HTTPException(status_code=404, detail={"code": "output_not_found", "message": "The requested repair output was not found."})
    return FileResponse(path, media_type=media_type, filename=name)
