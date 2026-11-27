# AutoClean AI API (Phase 4 integration status)

FastAPI provides real file validation, deterministic CSV profiling, and a narrowly scoped CSV repair path. Both exported Extra Trees artifacts are present and are loaded once when the installed scikit-learn version matches their serialized version. The root `AutoClean_AI.ipynb` notebook is present, but does not contain the feature builders, preprocessing, or semantic label mappings for these exported estimators. Model predictions and model-dependent repairs therefore remain disabled. The implemented repair method only fills missing feature values (numeric median, categorical most frequent value), preserves `diagnosis`, writes a separate cleaned CSV and history, then runs ARVA structural and preservation checks. The API never substitutes sample model results.

## Run on Windows

Run these commands from the repository root (`AutoClean-AI-Website`, the directory containing `backend`):

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example .env
python -m uvicorn backend.app.main:app --reload --port 8000
```

If Python 3.11 is not installed, replace `py -3.11` with `py`. The current development environment was verified with Python 3.11.6.

Open Swagger UI at `http://127.0.0.1:8000/docs`, ReDoc at `/redoc`, or the health endpoint at `http://127.0.0.1:8000/api/health`.

## Routes

All routes use the `/api` prefix. Upload uses `multipart/form-data` with a field named `file`. The upload limit defaults to 25 MiB. Files accepted: `.csv`, `.png`, `.jpg`, `.jpeg`; image bytes are verified with Pillow and image extension must match the detected format.

| Method and path | Behavior |
| --- | --- |
| `GET /api/health` | API status, artifact availability, load status, known input dimensions and numeric class IDs. Health never reports inference ready without preprocessing. |
| `GET /api/dashboard` | Aggregates real persisted uploads, source defects, repair-history entries and validation results. |
| `POST /api/upload` | Validates and stores a CSV or single image under a generated UUID. CSV response includes an initial local profile and five-row preview. |
| `POST /api/upload/image-dataset` | Accepts `manifest` CSV and `images_zip` ZIP fields. Requires `image_id`, `image_path`, and `class_label`; validates relative paths and extracts image members safely. Missing files remain analyzable defects. |
| `GET /api/analysis/{file_id}` | Computes deterministic CSV profiles or measured per-image dataset quality metrics and returns model integration status. |
| `POST /api/repair/{file_id}` | Repairs supported missing feature values or image quality defects; returns output references, repair history and ARVA checks. Unsupported/model-dependent tabular cases return a truthful 4xx/503 error. Original upload is unchanged. |
| `GET /api/validation/{file_id}` | Returns saved ARVA checks after repair; otherwise `not_available`. |
| `GET /api/reports/{file_id}` | Generates a quality report from the source profile; includes saved ARVA results only when they exist. Returns per-artifact availability and download URLs. |
| `GET /api/outputs/{file_id}/cleaned` | Downloads a generated cleaned CSV after successful repair. |
| `GET /api/outputs/{file_id}/history` | Downloads tabular repair history CSV. |
| `GET /api/outputs/{file_id}/image-history` | Downloads image repair/recovery status CSV, including manual-review records. |
| `GET /api/outputs/{file_id}/repaired-images` | Downloads the generated repaired-image ZIP. |
| `GET /api/outputs/{file_id}/quality-report` | Downloads the generated quality report JSON. |
| `GET /api/outputs/{file_id}/validation-report` | Downloads the generated validation report JSON after ARVA has run. |

Errors use `{ "error": { "code": "...", "message": "..." } }`. Upload response schemas and all endpoint models are visible in Swagger. CSV profiling returns row/column counts, dtypes, per-column missing counts and percentages, duplicate rows, numeric summary statistics, a limited mixed-numeric check, and any `diagnosis` target column under `protected_columns`. Repair fills missing numeric and categorical feature values only; it does not remove outliers or infer mixed numeric defects. A request requiring ADDA returns 503 while verified model preprocessing is unavailable. Files with no supported missing values return 422 without claiming success. Repair history uses zero-based data row indexes.

The React development origins `http://localhost:5173` and `http://127.0.0.1:5173` are enabled by default. Configure `AUTOCLEAN_CORS_ORIGINS` as a comma-separated list. Image quality measurements are explicit heuristics (blur uses Laplacian variance, noise uses local residual, and low resolution uses a 64-pixel shorter-edge threshold); they are not the undocumented trained ADDA pipeline. Repair uses OpenCV denoising, unsharp masking and cubic upscaling. Missing images are matched by exact image ID within the uploaded archive; no matching reference leads to a manual-review flag. Optional AI generation is not configured. Original upload names and inspection metadata are stored separately under `backend/storage/metadata`; generated reports are under `backend/storage/reports`. Other settings are shown in `.env.example`.

## Tests

From the repository root, run `python -m pytest backend/tests -q --basetemp=.pytest-tmp`. Tests use a temporary directory under the repository and synthetic CSV/image bytes; no Colab model files are needed.

## Model integration boundary and storage

Current model paths are `backend/app/models/models/adda_tabular_extra_trees.joblib` and `backend/app/models/models/adda_image_extra_trees.joblib`. Inspection found ExtraTreesClassifier artifacts serialized with scikit-learn 1.6.1. The tabular classifier expects 3 numeric inputs and has numeric classes `[0, 1, 2]`; the image classifier expects 8 inputs and has classes `[0, 1, 2, 3]`. These dimensions and numeric IDs do not identify feature order or semantic class names. Requirements pin scikit-learn to 1.6.1. The registry loads models once but leaves `preprocessing_available=false` and disables predictions until the missing training and inference pipeline is recovered and verified. The root notebook currently loads datasets but does not provide that pipeline. The missing-value repair policy is deterministic and does not claim to reproduce the unavailable original ADRA algorithm.

The existing `integrated_tabular_validation.json` report records `target_unchanged: false`; it is historical output, not a new validation run and not evidence of safe repair. Current generated repairs run fresh preservation checks against the produced CSV.

Uploaded files are stored under `backend/storage/uploads` using generated identifiers and are retained until manually removed. Do not expose this development server publicly or upload sensitive personal or medical data. Uploaded files are never executed; generated files and temporary inputs are excluded from Git.
