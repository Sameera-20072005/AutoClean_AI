# AutoClean AI

AutoClean AI is a web app for inspecting and improving tabular and image datasets. It combines a React interface with a FastAPI backend.

## What it does

- Uploads CSV files, individual images, or an image dataset manifest and ZIP archive.
- Profiles CSV columns, data types, missing values, duplicates, and summary statistics.
- Measures image dataset quality and flags missing or unreadable images.
- Repairs supported missing CSV values and image quality defects, then produces reports and validation results.
- Provides dashboard, analysis, repair, validation, and report pages.

The trained model predictions are currently disabled because the original model preprocessing and label mappings are not available. The app uses deterministic CSV profiling and documented image quality heuristics instead. Model files are not stored in Git.

## Project layout

- `frontend/` - Vite, React, and the browser app
- `backend/` - FastAPI routes, dataset processing, and storage
- `api/index.py` - Vercel entry point for FastAPI

## Requirements

- Node.js and npm
- Python 3.11 (recommended; the backend dependencies are listed in `backend/requirements.txt`)

## Run locally

Open two terminals in this directory (`AutoClean_main`).

### 1. Start the backend

In the first terminal, create and activate a Python environment, install the backend packages, and start FastAPI:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
Copy-Item backend\.env.example .env
python -m uvicorn backend.app.main:app --reload --port 8000
```

The API is available at `http://127.0.0.1:8000`. Its root URL and `/api/health` both return the health status. Open `http://127.0.0.1:8000/docs` for the interactive API documentation.

### 2. Start the frontend

In the second terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Open the local URL printed by Vite, usually `http://localhost:5173`. The frontend uses the local API at `http://localhost:8000` by default. Set `VITE_API_URL` in `frontend/.env` if the API is hosted elsewhere.

## Deploy to Vercel

Deploy the frontend and backend as two Vercel projects connected to this same GitHub repository. Set each project's **Root Directory** as shown below:

| Project | Root Directory | Framework |
| --- | --- | --- |
| Frontend | `AutoClean_main/frontend` | Vite |
| Backend | `AutoClean_main` | FastAPI |

Configure these environment variables in the Vercel project settings:

- Frontend: `VITE_API_URL` = the backend deployment URL, without a trailing slash.
- Backend: `AUTOCLEAN_CORS_ORIGINS` = the frontend deployment URL. A comma-separated list can include production and preview origins.
- Backend: `AUTOCLEAN_STORAGE_DIR` = `/tmp/autoclean-storage` to allow temporary writes in the serverless environment.

Set the frontend environment variable before building, then redeploy after changing it. Each Vercel project has its own deployment URL and settings.

Vercel's `/tmp` storage is temporary and cannot preserve uploads across instances or deployments. For durable uploads and generated files, connect an external storage service. See the [Vercel monorepo guide](https://vercel.com/docs/monorepos) for the two-project setup.

## Data and model limitations

Local uploads and generated artifacts are stored under `backend/storage/`. They are excluded from Git. The Vercel deployment needs persistent external storage if data must remain available after a request or instance restart. Predictions from trained estimators remain disabled until their preprocessing and label mappings can be verified.
