import csv
import io
import math

import numpy as np
import pandas as pd


def _json_scalar(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return value if math.isfinite(value) else None
    if isinstance(value, np.bool_):
        return bool(value)
    return value.isoformat() if hasattr(value, "isoformat") else value


def _read_csv(content: bytes) -> pd.DataFrame:
    text = content.decode("utf-8-sig")
    if not text.strip():
        raise ValueError("empty CSV")
    if "\x00" in text:
        raise ValueError("null byte in CSV")
    rows = list(csv.reader(io.StringIO(text, newline=""), strict=True))
    if not rows or not any(cell.strip() for cell in rows[0]):
        raise ValueError("missing header")
    width = len(rows[0])
    if width == 0 or any(len(row) != width for row in rows[1:] if row):
        raise ValueError("inconsistent row width")
    try:
        return pd.read_csv(io.BytesIO(content), encoding="utf-8-sig", on_bad_lines="error")
    except pd.errors.ParserError as exc:
        raise ValueError("malformed CSV") from exc


def profile_csv_bytes(content: bytes, include_preview: bool = False) -> dict:
    frame = _read_csv(content)
    missing = frame.isna().sum()
    columns = []
    for name in frame.columns:
        count = int(missing[name])
        columns.append({
            "name": str(name),
            "dtype": str(frame[name].dtype),
            "missing_count": count,
            "missing_percent": round(count / len(frame) * 100, 2) if len(frame) else 0.0,
        })

    numeric_summary = {}
    for name in frame.select_dtypes(include=["number"]).columns:
        series = frame[name].replace([np.inf, -np.inf], np.nan).dropna()
        stats = series.describe(percentiles=[0.25, 0.5, 0.75]).to_dict()
        numeric_summary[str(name)] = {key: _json_scalar(value) for key, value in stats.items()}

    invalid_checks = []
    protected_columns = [str(name) for name in frame.columns if str(name).casefold() == "diagnosis"]
    for name in frame.select_dtypes(include=["object", "string"]).columns:
        if str(name).casefold() == "diagnosis":
            continue
        values = frame[name].dropna().astype(str).str.strip()
        if values.empty:
            continue
        numeric = pd.to_numeric(values, errors="coerce")
        numeric_like = int(numeric.notna().sum())
        if numeric_like and numeric_like < len(values):
            invalid_checks.append({
                "column": str(name),
                "check": "mixed_numeric_values",
                "invalid_count": int(numeric.isna().sum()),
                "message": "Some non-empty values are not numeric although other values in this column are numeric.",
            })

    result = {
        "row_count": int(len(frame)),
        "column_count": int(len(frame.columns)),
        "columns": columns,
        "missing_value_count": int(missing.sum()),
        "missing_by_column": {str(name): int(value) for name, value in missing.items()},
        "duplicate_row_count": int(frame.duplicated().sum()),
        "numeric_summary": numeric_summary,
        "invalid_value_checks": invalid_checks,
        "protected_columns": protected_columns,
    }
    if include_preview:
        result["preview"] = [
            {str(key): _json_scalar(value) for key, value in row.items()}
            for row in frame.head(5).to_dict(orient="records")
        ]
    return result


def analyze_csv_path(path) -> dict:
    return profile_csv_bytes(path.read_bytes())
