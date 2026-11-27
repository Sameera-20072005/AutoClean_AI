import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    storage_root: Path
    max_upload_bytes: int
    cors_origins: list[str]
    tabular_model_path: Path
    image_model_path: Path


def get_settings() -> Settings:
    default_storage = PROJECT_ROOT / "backend" / "storage"
    model_root = Path(os.getenv("AUTOCLEAN_MODEL_DIR", PROJECT_ROOT / "backend" / "app" / "models" / "models"))
    origins = os.getenv("AUTOCLEAN_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return Settings(
        storage_root=Path(os.getenv("AUTOCLEAN_STORAGE_DIR", default_storage)).resolve(),
        max_upload_bytes=int(os.getenv("AUTOCLEAN_MAX_UPLOAD_BYTES", 25 * 1024 * 1024)),
        cors_origins=[origin.strip() for origin in origins.split(",") if origin.strip()],
        tabular_model_path=Path(os.getenv("AUTOCLEAN_TABULAR_MODEL", model_root / "adda_tabular_extra_trees.joblib")).resolve(),
        image_model_path=Path(os.getenv("AUTOCLEAN_IMAGE_MODEL", model_root / "adda_image_extra_trees.joblib")).resolve(),
    )
