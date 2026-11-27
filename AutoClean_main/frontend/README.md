# AutoClean AI

AutoClean AI is a phased data quality prototype. The frontend includes Home, Dashboard, Upload, Analysis, Repair, Validation, Reports and About routes. The dashboard reads actual uploads, analysis, repair history and validation artifacts. FastAPI validates CSV/single-image uploads and accepts image dataset manifests with ZIP archives. CSV repair fills supported missing feature values and runs structural ARVA checks. Image datasets receive explicit heuristic quality measurements and supported OpenCV repairs, with unresolved images flagged for manual review. Trained estimator inference remains disabled because the training notebook does not document its preprocessing or feature meanings.

## Requirements

- Node.js and npm
- Python 3.11.6 was used for the backend checks in this workspace

## Run locally

From `frontend/`, install frontend dependencies and start Vite:

```powershell
npm install
npm run dev
```

Open the URL printed by Vite (normally `http://localhost:5173`). The app can be used without the backend; its home page reports whether the FastAPI health endpoint is reachable.

In a second PowerShell window, change to the parent `AutoClean_main/` directory, then create a virtual environment and start FastAPI:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
```

Run backend and frontend checks with `python -m pytest backend\tests -q --basetemp=.pytest-tmp`, `npm test`, and `npm run build`.

If Python 3.11 is not installed, use `py -m venv .venv` with the available Python version. Open the API at `http://127.0.0.1:8000/docs`. The frontend health card reads `http://localhost:8000`; set `VITE_API_URL` in `frontend/.env` to use another backend URL.

## Model integration point

The exported estimators are in `backend/app/models/models/`. Requirements pin scikit-learn to their serialized version, 1.6.1. `AutoClean_AI.ipynb` is present at the workspace root, but it contains dataset setup/loading rather than training or inference code for these estimators. Exact feature builders, preprocessing, semantic label mappings, and the tabular reference strategy remain unverified. Model loading is reported by `/api/health`; predictions stay disabled until those pieces are recovered and verified. Image dataset measurements in this app are deterministic quality heuristics, not predictions from the trained image estimator.

## Image dataset upload

Choose **Image dataset** on Upload and provide a CSV with `image_id`, `image_path`, and `class_label` columns plus a ZIP containing relative image paths. Missing files are retained as defects. Quality checks report unreadable files, Laplacian blur scores, local residual noise scores, and dimensions. Supported repair uses OpenCV denoising, unsharp masking, cubic upscaling, and an exact image-ID match from another archive file for missing-image recovery. Unmatched images are flagged for manual review; AI generation is not configured.

## Storage and limitations

Uploads are stored under `backend/storage/uploads/` with generated server-side names and their original safe display names in `backend/storage/metadata/`. Generated reports and repair outputs are stored under `backend/storage/reports/` and `backend/storage/outputs/`. Uploaded and generated files are ignored by Git. Do not expose the development API publicly or upload sensitive personal or medical data to an unsecured prototype. For routes, schemas, configuration and test instructions, see [backend/README.md](backend/README.md).
