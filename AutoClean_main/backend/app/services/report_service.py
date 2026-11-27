import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from backend.app.core.config import Settings, get_settings
from backend.app.services.file_service import read_upload_metadata
from backend.app.services.repair_service import read_validation
from backend.app.services.tabular_service import analyze_csv_path
from backend.app.services.image_dataset_service import analyze_image_dataset


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _artifact(path: Path, root: Path, url: str, ready_message: str, missing_message: str) -> dict:
    try:
        exists = path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root.resolve())
    except OSError:
        exists = False
    return {
        "status": "generated" if exists else "not_generated",
        "download_url": url if exists else None,
        "message": ready_message if exists else missing_message,
    }


def generate_reports(file_id: str, source_path: Path, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    metadata = read_upload_metadata(file_id, settings) or {}
    filename = metadata.get("file_name") or source_path.name
    is_csv = source_path.suffix.lower() == ".csv" and metadata.get("data_type") != "image_dataset"
    is_image_dataset = metadata.get("data_type") == "image_dataset"

    try:
        if is_csv:
            summary = analyze_csv_path(source_path)
            quality = {
                "report_type": "quality_report",
                "file_id": file_id,
                "file_name": filename,
                "data_type": "tabular",
                "analysis_timestamp": _timestamp(),
                **summary,
            }
        elif is_image_dataset:
            image_summary = analyze_image_dataset(file_id, settings)
            quality = {
                "report_type": "quality_report",
                "file_id": file_id,
                "file_name": filename,
                "data_type": "image_dataset",
                "analysis_timestamp": _timestamp(),
                **image_summary,
            }
        else:
            quality = {
                "report_type": "quality_report",
                "file_id": file_id,
                "file_name": filename,
                "data_type": "image",
                "analysis_timestamp": _timestamp(),
                "row_count": None,
                "column_count": None,
                "columns": [],
                "missing_value_count": None,
                "missing_by_column": {},
                "duplicate_row_count": None,
                "numeric_summary": {},
                "image_inspection": metadata.get("inspection"),
                "message": "Single-image integrity was checked at upload. Dataset metrics are available when a CSV manifest and ZIP are uploaded together.",
            }
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "quality_report_unavailable", "message": "The source file could not be analyzed to generate a quality report."}) from exc

    report_dir = settings.storage_root / "reports"
    quality_path = report_dir / f"{file_id}_quality.json"
    validation_path = report_dir / f"{file_id}_validation.json"
    try:
        _atomic_json(quality_path, quality)
    except (OSError, TypeError, ValueError):
        raise HTTPException(status_code=503, detail={"code": "quality_report_storage_unavailable", "message": "The quality report could not be stored."}) from None

    validation_result = read_validation(file_id, settings)
    if validation_result:
        validation_report = {
            "report_type": "validation_report",
            "file_id": file_id,
            "validation_status": validation_result["status"],
            "checks": validation_result.get("checks", []),
            "message": validation_result["message"],
            "generated_at": _timestamp(),
        }
        try:
            _atomic_json(validation_path, validation_report)
        except (OSError, TypeError, ValueError):
            raise HTTPException(status_code=503, detail={"code": "validation_report_storage_unavailable", "message": "The validation report could not be stored."}) from None
    else:
        validation_report = None

    output_dir = settings.storage_root / "outputs"
    cleaned = _artifact(output_dir / f"{file_id}_cleaned.csv", output_dir, f"/api/outputs/{file_id}/cleaned", "Cleaned CSV is ready.", "No cleaned CSV has been generated.")
    history_name = f"{file_id}_image_repair_history.csv" if is_image_dataset else f"{file_id}_repair_history.csv"
    history_kind = "image-history" if is_image_dataset else "history"
    history = _artifact(output_dir / history_name, output_dir, f"/api/outputs/{file_id}/{history_kind}", "Repair history is ready.", "No repair history has been generated.")
    quality_artifact = _artifact(quality_path, report_dir, f"/api/outputs/{file_id}/quality-report", "Quality report is ready.", "Quality report has not been generated.")
    validation_artifact = _artifact(validation_path, report_dir, f"/api/outputs/{file_id}/validation-report", "Validation report is ready.", "ARVA results are not available until repair validation has run.")
    image_name = f"{file_id}_repaired_images.zip"
    image_artifact = _artifact(output_dir / image_name, output_dir, f"/api/outputs/{file_id}/repaired-images", "Repaired image dataset ZIP is ready.", "No repaired image dataset has been generated.") if is_image_dataset else {"status": "not_generated", "download_url": None, "message": "Single-image repair is not implemented."}

    complete = quality_artifact["status"] == "generated" and validation_artifact["status"] == "generated" and (
        (is_image_dataset and image_artifact["status"] == "generated" and history["status"] == "generated")
        or (not is_image_dataset and (not is_csv or (cleaned["status"] == "generated" and history["status"] == "generated")))
    )
    any_generated = any(item["status"] == "generated" for item in (cleaned, history, quality_artifact, validation_artifact, image_artifact))
    return {
        "file_id": file_id,
        "status": "generated" if complete else "partial" if any_generated else "not_generated",
        "cleaned_csv": cleaned,
        "repair_history_csv": history,
        "quality_report": quality_artifact,
        "validation_report": validation_artifact,
        "repaired_image": image_artifact,
        "message": "Reports reflect the stored upload, analysis profile and saved ARVA results. An artifact is downloadable only when its file exists.",
    }
