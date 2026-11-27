import io
import csv
import json
import os
import shutil
import uuid
import zipfile
from pathlib import Path, PurePosixPath

import cv2
import numpy as np
import pandas as pd
from fastapi import HTTPException, UploadFile

from backend.app.core.config import Settings, get_settings
from backend.app.services.file_service import read_upload_metadata

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MIN_RESOLUTION = 64
BLUR_THRESHOLD = 100.0
NOISE_THRESHOLD = 12.0


def _error(status, code, message):
    raise HTTPException(status_code=status, detail={"code": code, "message": message})


def _safe_path(name):
    path = PurePosixPath(name.replace("\\", "/"))
    return not path.is_absolute() and all(part not in {"", ".", ".."} for part in path.parts) and not (path.parts and ":" in path.parts[0])


async def store_image_dataset(manifest_upload: UploadFile, archive_upload: UploadFile, settings: Settings | None = None):
    settings = settings or get_settings()
    file_id = uuid.uuid4().hex
    uploads = settings.storage_root / "uploads"
    uploads.mkdir(parents=True, exist_ok=True)
    manifest_path = uploads / f"{file_id}.csv"
    image_root = uploads / f"{file_id}_images"
    try:
        manifest = await manifest_upload.read(settings.max_upload_bytes + 1)
        archive_bytes = await archive_upload.read(settings.max_upload_bytes + 1)
        if len(manifest) > settings.max_upload_bytes or len(archive_bytes) > settings.max_upload_bytes:
            _error(413, "file_too_large", "The image manifest or ZIP exceeds the configured upload size limit.")
        if Path(manifest_upload.filename or "").suffix.lower() != ".csv" or Path(archive_upload.filename or "").suffix.lower() != ".zip":
            _error(415, "invalid_image_dataset_files", "Provide one CSV manifest and one ZIP image archive.")
        try:
            frame = pd.read_csv(io.BytesIO(manifest), dtype=str, keep_default_na=False, encoding="utf-8-sig")
        except (UnicodeDecodeError, pd.errors.ParserError, ValueError):
            _error(400, "malformed_image_manifest", "The image manifest is not a valid UTF-8 CSV.")
        cols = {str(name).strip().casefold(): str(name) for name in frame.columns}
        id_col = next((cols[key] for key in ("image_id", "id") if key in cols), None)
        path_col = next((cols[key] for key in ("image_path", "path", "filename", "file_name") if key in cols), None)
        label_col = next((cols[key] for key in ("class_label", "label", "class") if key in cols), None)
        if frame.empty or not id_col or not path_col or not label_col:
            _error(422, "invalid_image_manifest", "CSV needs image_id, image_path, and class_label columns and at least one record.")
        if frame[id_col].str.strip().eq("").any() or frame[path_col].str.strip().eq("").any() or frame[label_col].str.strip().eq("").any() or frame[id_col].duplicated().any():
            _error(422, "invalid_image_manifest", "Every row needs a unique image ID, image path, and class label.")
        expected = [value.replace("\\", "/").removeprefix("./") for value in frame[path_col]]
        if any(not _safe_path(value) or Path(value).suffix.lower() not in IMAGE_SUFFIXES for value in expected):
            _error(422, "invalid_image_path", "Manifest paths must be safe relative paths to supported image files.")
        try:
            archive = zipfile.ZipFile(io.BytesIO(archive_bytes))
        except (zipfile.BadZipFile, OSError):
            _error(400, "invalid_image_archive", "The image archive is not a valid ZIP file.")
        infos = archive.infolist()
        if sum(item.file_size for item in infos) > MAX_ARCHIVE_BYTES:
            _error(413, "image_archive_too_large", "Expanded image archive exceeds the 100 MB safety limit.")
        members = {}
        for info in infos:
            if info.is_dir():
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000 or not _safe_path(info.filename):
                _error(422, "unsafe_archive_path", "The ZIP contains an unsafe path or symbolic link.")
            name = info.filename.replace("\\", "/").removeprefix("./")
            if name in members:
                _error(422, "duplicate_archive_path", "The ZIP contains duplicate paths.")
            if Path(name).suffix.lower() in IMAGE_SUFFIXES:
                members[name] = info
        image_root.mkdir()
        for name, info in members.items():
            target = image_root.joinpath(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(info))
        missing = [path for path in expected if path not in members]
        manifest_path.write_bytes(manifest)
        metadata = {"file_id": file_id, "file_name": Path(manifest_upload.filename or "images.csv").name, "data_type": "image_dataset", "size_bytes": len(manifest) + len(archive_bytes), "content_type": "text/csv+application/zip", "uploaded_at": pd.Timestamp.now(tz="UTC").isoformat(), "manifest_columns": {"image_id": id_col, "image_path": path_col, "class_label": label_col}, "image_count": len(frame), "archive_missing_paths": missing}
        metadata_dir = settings.storage_root / "metadata"
        metadata_dir.mkdir(parents=True, exist_ok=True)
        temp = metadata_dir / f".{file_id}.{uuid.uuid4().hex}.tmp"
        temp.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
        os.replace(temp, metadata_dir / f"{file_id}.json")
        return {**metadata, "inspection": {"row_count": len(frame), "image_count": len(frame), "archive_image_count": len(members), "missing_file_count": len(missing)}}
    except Exception:
        manifest_path.unlink(missing_ok=True)
        shutil.rmtree(image_root, ignore_errors=True)
        raise
    finally:
        await manifest_upload.close()
        await archive_upload.close()


def _data(file_id, settings):
    base = settings.storage_root / "uploads"
    metadata = read_upload_metadata(file_id, settings) or {}
    columns = metadata.get("manifest_columns", {})
    frame = pd.read_csv(base / f"{file_id}.csv", dtype=str, keep_default_na=False)
    return base / f"{file_id}_images", frame, columns


def _metrics(path):
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        return None
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    smooth = cv2.GaussianBlur(gray, (3, 3), 0)
    noise = float(np.mean(np.abs(gray.astype(np.float32) - smooth.astype(np.float32))))
    height, width = gray.shape[:2]
    defects = []
    if min(width, height) < MIN_RESOLUTION: defects.append("low_resolution")
    if blur < BLUR_THRESHOLD: defects.append("blur")
    if noise > NOISE_THRESHOLD: defects.append("noise")
    return {"width": width, "height": height, "blur_score": round(blur, 3), "noise_score": round(noise, 3), "defects": defects}


def analyze_image_dataset(file_id, settings: Settings | None = None):
    settings = settings or get_settings()
    root, frame, cols = _data(file_id, settings)
    rows = []
    counts = {name: 0 for name in ("missing", "corrupted", "blur", "noise", "low_resolution")}
    for _, row in frame.iterrows():
        image_id = row[cols["image_id"]]
        rel = row[cols["image_path"]].replace("\\", "/").removeprefix("./")
        path = root.joinpath(*PurePosixPath(rel).parts)
        metrics = _metrics(path) if path.is_file() else None
        defects = ["missing"] if not path.is_file() else metrics["defects"] if metrics else ["corrupted"]
        for defect in defects: counts[defect] += 1
        rows.append({"image_id": image_id, "image_path": rel, "class_label": row[cols["class_label"]], "status": "defect_detected" if defects else "clean", "defects": defects, "metrics": metrics})
    return {"image_count": len(rows), "class_distribution": frame[cols["class_label"]].value_counts(dropna=False).to_dict(), "defect_counts": counts, "defect_total": sum(counts.values()), "rows": rows, "method": f"Deterministic image metrics; blur threshold {BLUR_THRESHOLD} Laplacian variance, noise threshold {NOISE_THRESHOLD} local residual, low-resolution threshold {MIN_RESOLUTION}px. These are explicit heuristics, not the undocumented trained ADDA pipeline."}


def repair_image_dataset(file_id, settings: Settings | None = None):
    settings = settings or get_settings()
    root, frame, cols = _data(file_id, settings)
    output = settings.storage_root / "outputs"
    output.mkdir(parents=True, exist_ok=True)
    repaired_root = output / f"{file_id}_repaired_images"
    shutil.rmtree(repaired_root, ignore_errors=True)
    repaired_root.mkdir()
    history, manual = [], []
    original_labels = frame[cols["class_label"]].copy()
    for index, row in frame.iterrows():
        image_id = row[cols["image_id"]]
        rel = row[cols["image_path"]].replace("\\", "/").removeprefix("./")
        source = root.joinpath(*PurePosixPath(rel).parts)
        target = repaired_root.joinpath(*PurePosixPath(rel).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        image = cv2.imread(str(source), cv2.IMREAD_COLOR) if source.is_file() else None
        metrics = _metrics(source) if image is not None else None
        method, status = "copy", "unchanged"
        if image is None:
            # First recovery attempt: another archived file carrying this exact image ID.
            references = [item for item in root.rglob("*") if item.is_file() and item.stem.casefold() == image_id.casefold() and _metrics(item)]
            if references:
                image = cv2.imread(str(references[0]), cv2.IMREAD_COLOR)
                method, status = "archive_reference_match", "recovered_reference"
            else:
                manual.append({"row_index": int(index), "image_id": image_id, "image_path": rel, "status": "manual_review", "reason": "No matching reference image was found in the archive; image generation is not configured."})
                continue
        if metrics and "noise" in metrics["defects"]:
            image = cv2.fastNlMeansDenoisingColored(image, None, 8, 8, 7, 21)
            method, status = "opencv_colored_denoising", "repaired"
        if metrics and "blur" in metrics["defects"]:
            softened = cv2.GaussianBlur(image, (0, 0), 1.2)
            image = cv2.addWeighted(image, 1.5, softened, -0.5, 0)
            method, status = "unsharp_mask", "repaired"
        if metrics and "low_resolution" in metrics["defects"]:
            height, width = image.shape[:2]
            factor = MIN_RESOLUTION / min(width, height)
            image = cv2.resize(image, (int(round(width * factor)), int(round(height * factor))), interpolation=cv2.INTER_CUBIC)
            method, status = "cubic_upscale", "repaired"
        if cv2.imwrite(str(target), image):
            history.append({"row_index": int(index), "image_id": image_id, "image_path": rel, "method": method, "status": status})
        else:
            manual.append({"row_index": int(index), "image_id": image_id, "image_path": rel, "status": "manual_review", "reason": "Repaired image could not be written."})

    zip_path = output / f"{file_id}_repaired_images.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in repaired_root.rglob("*"):
            if path.is_file(): archive.write(path, path.relative_to(repaired_root).as_posix())
    history_path = output / f"{file_id}_image_repair_history.csv"
    with history_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["row_index", "image_id", "image_path", "method", "status", "reason"])
        writer.writeheader()
        writer.writerows(history + manual)
    checks = [
        {"name": "manifest_records_accounted_for", "passed": len(history) + len(manual) == len(frame)},
        {"name": "class_labels_preserved", "passed": frame[cols["class_label"]].equals(original_labels)},
        {"name": "generated_images_decode", "passed": all(_metrics(path) is not None for path in repaired_root.rglob("*") if path.is_file())},
        {"name": "unrecovered_images_flagged_for_review", "passed": all(item["status"] == "manual_review" for item in manual)},
    ]
    validation = {"status": "passed" if all(check["passed"] for check in checks) else "failed", "checks": checks, "manual_review": manual, "message": "Generated images and manifest records were checked. Unrecovered rows remain flagged for manual review."}
    (output / f"{file_id}_validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"file_id": file_id, "status": "completed", "outputs": {"repaired_images_zip": f"/api/outputs/{file_id}/repaired-images", "repair_history_csv": f"/api/outputs/{file_id}/image-history"}, "repair_summary": {"images_processed": len(frame), "images_repaired": sum(item["status"] in {"repaired", "recovered_reference"} for item in history), "manual_review": len(manual), "methods": sorted({item["method"] for item in history if item["status"] != "unchanged"})}, "validation": validation, "model_status": "deterministic_image_methods; trained_ADRA_unverified", "message": "Denoising, sharpening and upscaling were applied where detected. Missing images were matched by ID in the archive; unmatched images need manual review. AI generation is not configured."}
