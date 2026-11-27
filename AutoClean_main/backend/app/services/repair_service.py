import csv
import io
import json
import math
import os
import uuid
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from fastapi import HTTPException

from backend.app.core.config import Settings, get_settings
from backend.app.models.interfaces import model_registry
from backend.app.services.tabular_service import _read_csv, profile_csv_bytes


def _json_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _write_csv(frame: pd.DataFrame) -> bytes:
    output = io.StringIO(newline="")
    frame.to_csv(output, index=False, lineterminator="\n")
    return output.getvalue().encode("utf-8")


def _validation(original: pd.DataFrame, repaired: pd.DataFrame, changed_columns: list[str]) -> dict:
    diagnosis_columns = [column for column in original.columns if str(column).casefold() == "diagnosis"]
    checks = [
        {"name": "columns_preserved", "passed": list(original.columns) == list(repaired.columns)},
        {"name": "row_count_preserved", "passed": len(original) == len(repaired)},
        {
            "name": "diagnosis_unchanged",
            "passed": all(original[column].equals(repaired[column]) for column in diagnosis_columns),
        },
        {
            "name": "observed_values_unchanged",
            "passed": original.where(original.notna()).equals(repaired.where(original.notna())),
        },
        {
            "name": "imputed_cells_filled",
            "passed": all(not repaired[column].isna().any() for column in changed_columns),
        },
    ]
    passed = all(check["passed"] for check in checks)
    return {
        "status": "passed" if passed else "failed",
        "checks": checks,
        "message": "ARVA structural and preservation checks passed." if passed else "ARVA detected a failed preservation or repair check.",
    }


def _atomic_write(path: Path, content: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def repair_csv(file_id: str, source_path: Path, settings: Settings | None = None) -> dict:
    settings = settings or get_settings()
    try:
        original_bytes = source_path.read_bytes()
        original = _read_csv(original_bytes)
    except (OSError, UnicodeDecodeError, ValueError, csv.Error, pd.errors.ParserError):
        raise HTTPException(status_code=422, detail={"code": "invalid_csv", "message": "The stored CSV is malformed or cannot be parsed safely."}) from None

    analysis = profile_csv_bytes(original_bytes)
    if analysis["invalid_value_checks"]:
        model_registry.load_once(settings)
        model = model_registry.models["tabular"]
        raise HTTPException(
            status_code=503,
            detail={
                "code": "adda_unavailable",
                "message": f"CSV contains mixed numeric values that require ADDA analysis, but its verified preprocessing is unavailable. {model.message}",
            },
        )

    diagnosis = next((column for column in original.columns if str(column).casefold() == "diagnosis"), None)
    candidates = [column for column in original.columns if column != diagnosis and original[column].isna().any()]
    if not candidates:
        raise HTTPException(status_code=422, detail={"code": "no_supported_repairs", "message": "No missing values in supported feature columns were found; no repair was performed."})

    repaired = original.copy(deep=True)
    history: list[dict[str, Any]] = []
    skipped: list[str] = []
    for column in candidates:
        series = repaired[column]
        observed = series.dropna()
        if observed.empty:
            skipped.append(str(column))
            continue
        if pd.api.types.is_numeric_dtype(series):
            replacement = observed.median()
            method = "median_imputation"
        else:
            modes = observed.mode(dropna=True)
            if modes.empty:
                skipped.append(str(column))
                continue
            replacement = modes.iloc[0]
            method = "most_frequent_imputation"
        for row_index in series.index[series.isna()].tolist():
            history.append({
                "row_index": int(row_index),
                "column": str(column),
                "method": method,
                "old_value": "",
                "new_value": _json_value(replacement),
            })
            repaired.at[row_index, column] = replacement

    if skipped:
        raise HTTPException(status_code=503, detail={"code": "repair_unavailable", "message": f"No safe imputation value can be derived for entirely empty columns: {', '.join(skipped)}. No output was written."})
    if not history:
        raise HTTPException(status_code=422, detail={"code": "no_supported_repairs", "message": "No supported repair operation was produced; no output was written."})

    cleaned_bytes = _write_csv(repaired)
    try:
        serialized_repair = _read_csv(cleaned_bytes)
    except (UnicodeDecodeError, ValueError, csv.Error, pd.errors.ParserError):
        raise HTTPException(status_code=422, detail={"code": "repaired_csv_invalid", "message": "The repaired CSV could not be parsed for ARVA validation; no output was written."}) from None
    validation = _validation(original, serialized_repair, candidates)
    if not validation["status"] == "passed":
        raise HTTPException(status_code=422, detail={"code": "arva_validation_failed", "message": validation["message"]})

    output_dir = settings.storage_root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{file_id}_cleaned.csv"
    history_path = output_dir / f"{file_id}_repair_history.csv"
    validation_path = output_dir / f"{file_id}_validation.json"
    history_stream = io.StringIO(newline="")
    writer = csv.DictWriter(history_stream, fieldnames=["row_index", "column", "method", "old_value", "new_value"], lineterminator="\n")
    writer.writeheader()
    writer.writerows(history)
    try:
        _atomic_write(csv_path, cleaned_bytes)
        _atomic_write(history_path, history_stream.getvalue().encode("utf-8"))
        _atomic_write(validation_path, json.dumps(validation, ensure_ascii=False, indent=2).encode("utf-8"))
    except OSError:
        for path in (csv_path, history_path, validation_path):
            path.unlink(missing_ok=True)
        raise HTTPException(status_code=503, detail={"code": "output_storage_unavailable", "message": "Repair outputs could not be stored; no successful repair was recorded."}) from None

    return {
        "file_id": file_id,
        "status": "completed",
        "outputs": {
            "cleaned_csv": f"/api/outputs/{file_id}/cleaned",
            "repair_history_csv": f"/api/outputs/{file_id}/history",
        },
        "repair_summary": {
            "method": "deterministic_missing_value_imputation",
            "cells_repaired": len(history),
            "columns_repaired": sorted({item["column"] for item in history}),
            "skipped_all_missing_columns": [],
            "diagnosis_preserved": True,
        },
        "validation": validation,
        "model_status": "not_required_for_supported_missing_value_repairs",
        "message": "Supported missing values were imputed in a separate output copy. ADDA predictions and model-dependent repairs were not used.",
    }


def read_validation(file_id: str, settings: Settings | None = None) -> dict | None:
    path = (settings or get_settings()).storage_root / "outputs" / f"{file_id}_validation.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
