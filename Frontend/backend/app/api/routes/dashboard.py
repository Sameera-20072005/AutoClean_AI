import csv
import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.services.file_service import read_upload_metadata
from backend.app.services.tabular_service import analyze_csv_path
from backend.app.services.image_dataset_service import analyze_image_dataset

router = APIRouter(tags=["dashboard"])


def _read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


@router.get("/dashboard")
def dashboard():
    """Summarize persisted uploads and artifacts; never fabricate empty jobs."""
    root = get_settings().storage_root
    metadata_dir = root / "metadata"
    uploads_dir = root / "uploads"
    outputs_dir = root / "outputs"
    reports_dir = root / "reports"
    jobs = []
    activity = Counter()
    validation_warnings = []
    repair_history = []
    total_files = total_defects = repaired_cells = completed_repairs = passed = failed = 0

    for metadata_path in metadata_dir.glob("*.json") if metadata_dir.exists() else ():
        file_id = metadata_path.stem
        metadata = read_upload_metadata(file_id)
        if not metadata:
            continue
        candidates = list(uploads_dir.glob(f"{file_id}.*")) if uploads_dir.exists() else []
        source = next((path for path in candidates if path.is_file() and not path.is_symlink()), None)
        if source is None:
            continue
        total_files += 1
        uploaded_at = metadata.get("uploaded_at")
        try:
            date = datetime.fromisoformat(uploaded_at.replace("Z", "+00:00")).astimezone(timezone.utc).date().isoformat()
        except (AttributeError, ValueError):
            date = "Unknown"
        activity[date] += 1

        defects = 0
        defect_summary = "Upload inspected"
        if metadata.get("data_type") == "tabular":
            try:
                profile = analyze_csv_path(source)
                defects = int(profile["missing_value_count"] + profile["duplicate_row_count"] + sum(item["invalid_count"] for item in profile["invalid_value_checks"]))
                defect_summary = f"{profile['row_count']} rows · {profile['column_count']} columns"
                if defects:
                    validation_warnings.append({"file_id": file_id, "file_name": metadata.get("file_name", source.name), "defects": defects, "message": f"{profile['missing_value_count']} missing values, {profile['duplicate_row_count']} duplicate rows, and {sum(item['invalid_count'] for item in profile['invalid_value_checks'])} mixed-type values."})
            except (OSError, ValueError, UnicodeDecodeError):
                defect_summary = "Source could not be profiled"
        elif metadata.get("data_type") == "image_dataset":
            try:
                profile = analyze_image_dataset(file_id)
                defects = int(profile["defect_total"])
                defect_summary = f"{profile['image_count']} images · {defects} measured defects"
                if defects:
                    validation_warnings.append({"file_id": file_id, "file_name": metadata.get("file_name", source.name), "defects": defects, "message": ", ".join(f"{name}: {count}" for name, count in profile["defect_counts"].items() if count)})
            except (OSError, ValueError, KeyError):
                defect_summary = "Image manifest could not be analyzed"
        total_defects += defects

        image_dataset = metadata.get("data_type") == "image_dataset"
        history_path = outputs_dir / (f"{file_id}_image_repair_history.csv" if image_dataset else f"{file_id}_repair_history.csv")
        file_repaired_cells = 0
        if history_path.is_file() and not history_path.is_symlink():
            try:
                with history_path.open(newline="", encoding="utf-8-sig") as stream:
                    entries = list(csv.DictReader(stream))
                file_repaired_cells = sum(entry.get("status") in {"repaired", "recovered_reference"} for entry in entries) if image_dataset else len(entries)
                repaired_cells += file_repaired_cells
                completed_repairs += 1
                repair_history.extend({"file_id": file_id, "file_name": metadata.get("file_name", source.name), **entry} for entry in entries[-10:])
                activity[date] += 0  # Ensure the upload date remains in the series.
            except (OSError, csv.Error):
                pass

        validation = _read_json(outputs_dir / f"{file_id}_validation.json")
        validation_status = validation.get("status") if validation else "not_run"
        if validation_status == "passed":
            passed += 1
        elif validation_status == "failed":
            failed += 1
            validation_warnings.append({"file_id": file_id, "file_name": metadata.get("file_name", source.name), "defects": 0, "message": validation.get("message", "Validation failed")})

        jobs.append({
            "file_id": file_id,
            "file_name": metadata.get("file_name", source.name),
            "data_type": metadata.get("data_type", "unknown"),
            "uploaded_at": uploaded_at,
            "status": "repaired" if file_repaired_cells else "analyzed",
            "defects_detected": defects,
            "records_repaired": file_repaired_cells,
            "validation_status": validation_status,
            "summary": defect_summary,
        })

    jobs.sort(key=lambda item: item.get("uploaded_at") or "", reverse=True)
    repair_history.sort(key=lambda item: (item.get("file_id", ""), item.get("row_index", "")), reverse=True)
    return {
        "datasets_processed": total_files,
        "files_analyzed": total_files,
        "defects_detected": total_defects,
        "repairs_completed": completed_repairs,
        "records_repaired": repaired_cells,
        "validation": {"passed": passed, "failed": failed, "not_run": max(total_files - passed - failed, 0)},
        "activity": [{"day": day, "uploads": count} for day, count in sorted(activity.items()) if day != "Unknown"],
        "jobs": jobs[:20],
        "warnings": validation_warnings[:20],
        "repair_history": repair_history[-50:],
    }
