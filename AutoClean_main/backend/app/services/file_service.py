import csv
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException, UploadFile

from backend.app.core.config import Settings, get_settings
from backend.app.services.image_service import ALLOWED_IMAGE_FORMATS, inspect_image
from backend.app.services.tabular_service import profile_csv_bytes

logger = logging.getLogger("autoclean.files")


def _safe_display_name(filename: str | None) -> str:
    return (filename or "upload").replace("\\", "/").split("/")[-1] or "upload"


async def store_upload(upload: UploadFile, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    filename = _safe_display_name(upload.filename)
    suffix = Path(filename).suffix.lower()
    if suffix != ".csv" and suffix not in ALLOWED_IMAGE_FORMATS:
        raise HTTPException(status_code=415, detail={"code": "unsupported_file_type", "message": "Supported files are CSV, PNG, JPG and JPEG."})

    file_id = uuid.uuid4().hex
    upload_dir = settings.storage_root / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_path = upload_dir / f"{file_id}{suffix}"
    chunks = []
    size = 0
    try:
        with stored_path.open("xb") as destination:
            while chunk := await upload.read(1024 * 1024):
                size += len(chunk)
                if size > settings.max_upload_bytes:
                    raise HTTPException(status_code=413, detail={"code": "file_too_large", "message": "File exceeds the configured upload size limit."})
                chunks.append(chunk)
                destination.write(chunk)
        content = b"".join(chunks)
        if suffix == ".csv":
            try:
                inspection = profile_csv_bytes(content, include_preview=True)
            except (UnicodeDecodeError, ValueError, csv.Error) as exc:
                logger.info("Rejected malformed CSV upload %s: %s", file_id, type(exc).__name__)
                raise HTTPException(status_code=400, detail={"code": "malformed_csv", "message": "CSV is malformed, inconsistent or not valid UTF-8."}) from None
            data_type = "tabular"
            content_type = "text/csv"
        else:
            inspection = inspect_image(content, suffix)
            data_type = "image"
            content_type = "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/png"
        metadata_dir = settings.storage_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = metadata_dir / f"{file_id}.json"
        temporary_metadata = metadata_path.with_name(f".{file_id}.{uuid.uuid4().hex}.tmp")
        try:
            with temporary_metadata.open("x", encoding="utf-8") as metadata_file:
                json.dump({
                    "file_id": file_id,
                    "file_name": filename,
                    "data_type": data_type,
                    "size_bytes": size,
                    "content_type": content_type,
                    "inspection": inspection,
                    "uploaded_at": datetime.now(timezone.utc).isoformat(),
                }, metadata_file, ensure_ascii=False)
                metadata_file.flush()
                os.fsync(metadata_file.fileno())
            os.replace(temporary_metadata, metadata_path)
        finally:
            temporary_metadata.unlink(missing_ok=True)
        return {
            "file_id": file_id,
            "file_name": filename,
            "data_type": data_type,
            "size_bytes": size,
            "content_type": content_type,
            "inspection": inspection,
            "_stored_path": stored_path,
        }
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def find_upload(file_id: str, settings: Settings | None = None) -> Path:
    if len(file_id) != 32 or any(character not in "0123456789abcdef" for character in file_id):
        raise HTTPException(status_code=404, detail={"code": "file_not_found", "message": "Uploaded file was not found."})
    upload_dir = (settings or get_settings()).storage_root / "uploads"
    matches = list(upload_dir.glob(f"{file_id}.*")) if upload_dir.exists() else []
    if len(matches) != 1 or not matches[0].is_file():
        raise HTTPException(status_code=404, detail={"code": "file_not_found", "message": "Uploaded file was not found."})
    return matches[0]


def read_upload_metadata(file_id: str, settings: Settings | None = None) -> dict | None:
    if len(file_id) != 32 or any(character not in "0123456789abcdef" for character in file_id):
        return None
    metadata_path = (settings or get_settings()).storage_root / "metadata" / f"{file_id}.json"
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return metadata if isinstance(metadata, dict) and metadata.get("file_id") == file_id else None
